import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, roc_curve, precision_recall_curve
from xgboost import XGBClassifier

THR = 180
OUT = Path("docs/results"); OUT.mkdir(parents=True, exist_ok=True)

df = pd.read_csv("data/processed/features.csv.gz", parse_dates=["time"])
df = df[df.glu_now <= THR].reset_index(drop=True)
df["y"] = (df.future_max > THR).astype(int)
DROP = ("time", "subject", "group", "future_max", "y")
FEATURES = [c for c in df.columns if c not in DROP]
WEARABLE = ["hr_mean_30m", "mets_mean_30m", "act_kcal_60m"]
NO_WEAR = [f for f in FEATURES if f not in WEARABLE]
X, y, g = df[FEATURES], df.y, df.subject
spw = (y == 0).sum() / (y == 1).sum()
t2d = (df.group == "t2d").values


def xgb():
    return XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                         eval_metric="logloss", n_jobs=-1)


def logit():
    return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                         LogisticRegression(max_iter=1000, class_weight="balanced"))


# name: (model factory, columns used)
specs = {"Logistic": (logit, FEATURES), "XGBoost": (xgb, FEATURES),
         "XGBoost (no wearable)": (xgb, NO_WEAR)}
oof = {k: np.zeros(len(df)) for k in specs}
for tr, te in GroupKFold(n_splits=5).split(X, y, g):
    for k, (make, cols) in specs.items():
        m = make().fit(X.iloc[tr][cols], y.iloc[tr])
        oof[k][te] = m.predict_proba(X.iloc[te][cols])[:, 1]
oof["Rule: high & rising"] = (df.glu_now + 2 * df.glu_chg_30m).values

yv = y.values
# ---- 1. ROC and precision-recall curves, T2D patients only ----
fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
for k in ("Logistic", "XGBoost", "Rule: high & rising"):
    fpr, tpr, _ = roc_curve(yv[t2d], oof[k][t2d])
    ax[0].plot(fpr, tpr, label=f"{k} (AUC {roc_auc_score(yv[t2d], oof[k][t2d]):.2f})")
    p, r, _ = precision_recall_curve(yv[t2d], oof[k][t2d])
    ax[1].plot(r, p, label=k)
ax[0].plot([0, 1], [0, 1], "--", c="gray")
ax[0].set(title="ROC, T2D patients (unseen)", xlabel="False alarm rate", ylabel="Spikes caught")
ax[1].axhline(yv[t2d].mean(), ls="--", c="gray", label="Random guess")
ax[1].set(title="Precision vs recall, T2D", xlabel="Recall", ylabel="Precision")
ax[0].legend(); ax[1].legend(); plt.tight_layout()
plt.savefig(OUT / "roc_pr_t2d.png", dpi=150); plt.close()

# ---- 2. AUC for every individual person ----
rows = []
for s, d in df.groupby("subject"):
    if d.y.nunique() == 2:
        rows.append((s, d.group.iloc[0], roc_auc_score(d.y, oof["Logistic"][d.index])))
pp = pd.DataFrame(rows, columns=["subject", "group", "auc"]).sort_values("auc")
colors = {"healthy": "tab:green", "prediabetes": "tab:orange", "t2d": "tab:red"}
plt.figure(figsize=(10, 4))
plt.bar(range(len(pp)), pp.auc, color=pp.group.map(colors))
plt.axhline(0.5, ls="--", c="gray")
plt.xticks(range(len(pp)), pp.subject, fontsize=7)
plt.title("AUC per person (red = T2D, orange = prediabetes, green = healthy)")
plt.ylabel("AUC"); plt.tight_layout(); plt.savefig(OUT / "auc_per_person.png", dpi=150); plt.close()
print("Per-person AUC, T2D median:", round(pp[pp.group == "t2d"].auc.median(), 3),
      "| worst T2D:", round(pp[pp.group == "t2d"].auc.min(), 3))

# ---- 3. What cutoff gives what trade-off (T2D) ----
print("\nThreshold trade-off on T2D patients:")
for k in ("Logistic", "XGBoost"):
    p, r, t = precision_recall_curve(yv[t2d], oof[k][t2d])
    for target in (0.4, 0.5, 0.6):
        ok = np.where(p[:-1] >= target)[0]
        if len(ok):
            i = ok[np.argmax(r[:-1][ok])]
            print(f"  {k:9s} precision >= {target:.0%}: recall {r[i]:.2f} (cutoff {t[i]:.2f})")
        else:
            print(f"  {k:9s} precision >= {target:.0%}: not reachable")

# ---- 4. Confidence intervals: resample PEOPLE, not rows ----
rng = np.random.default_rng(0)
ids = df.loc[t2d, "subject"].unique()
idx = {s: np.where(df.subject.values == s)[0] for s in ids}


def boot(f, n=300):
    out = []
    for _ in range(n):
        ii = np.concatenate([idx[s] for s in rng.choice(ids, len(ids))])
        if len(np.unique(yv[ii])) == 2:
            out.append(f(ii))
    return np.percentile(out, [2.5, 97.5])


auc = lambda k: (lambda ii: roc_auc_score(yv[ii], oof[k][ii]))
print("\nT2D AUC with 95% interval (resampling the 14 people):")
for k in ("Logistic", "XGBoost", "Rule: high & rising"):
    lo, hi = boot(auc(k))
    print(f"  {k:20s} {roc_auc_score(yv[t2d], oof[k][t2d]):.3f}  [{lo:.3f}, {hi:.3f}]")
for a, b in (("XGBoost", "XGBoost (no wearable)"), ("Logistic", "Rule: high & rising")):
    lo, hi = boot(lambda ii: roc_auc_score(yv[ii], oof[a][ii]) - roc_auc_score(yv[ii], oof[b][ii]))
    print(f"  Difference {a} minus {b}: [{lo:+.3f}, {hi:+.3f}]")
print("(If a difference interval includes 0, it is not clearly real.)")
