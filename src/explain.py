import numpy as np, pandas as pd, joblib, shap
import matplotlib.pyplot as plt
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
from xgboost import XGBClassifier

THR = 180
OUT = Path("docs/results"); OUT.mkdir(parents=True, exist_ok=True)
df = pd.read_csv("data/processed/features.csv.gz", parse_dates=["time"])
df = df[df.glu_now <= THR].reset_index(drop=True)
df["y"] = (df.future_max > THR).astype(int)
DROP = ("time", "subject", "group", "future_max", "y")
FEATURES = [c for c in df.columns if c not in DROP]
X, y = df[FEATURES], df.y

# --- Final dashboard model: logistic regression on all data ---
logit = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                      LogisticRegression(max_iter=1000, class_weight="balanced"))
logit.fit(X, y)
joblib.dump({"model": logit, "features": FEATURES}, "models/logistic_spike_model.pkl")

# --- Chart 1: what pushes risk up or down (weights per feature) ---
coef = pd.Series(logit[-1].coef_[0], index=FEATURES).sort_values()
plt.figure(figsize=(8, 7))
coef.plot.barh(color=np.where(coef > 0, "tab:red", "tab:blue"))
plt.title("Logistic model: red raises spike risk, blue lowers it")
plt.xlabel("Weight (per 1 standard deviation of the feature)")
plt.tight_layout(); plt.savefig(OUT / "logistic_weights.png", dpi=150); plt.close()
print(coef.round(2).to_string())

# --- Chart 2: SHAP summary for XGBoost (nice for slides) ---
xgbm = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                     subsample=0.8, colsample_bytree=0.8,
                     scale_pos_weight=(y == 0).sum() / (y == 1).sum(),
                     eval_metric="logloss", n_jobs=-1).fit(X, y)
sample = X.sample(5000, random_state=0)
sv = shap.TreeExplainer(xgbm).shap_values(sample)
shap.summary_plot(sv, sample, show=False)
plt.savefig(OUT / "shap_xgboost.png", dpi=150, bbox_inches="tight"); plt.close()


# --- What-if sanity check on a typical T2D moment ---
def risk(row):
    return logit.predict_proba(pd.DataFrame([row])[FEATURES])[0, 1]

base = X[df.group == "t2d"].median()
print("\nTypical T2D moment, risk score:", round(risk(base), 2))
for carbs in (0, 30, 60, 100):
    r = base.copy()
    r["carbs_3h"] = carbs
    r["min_since_meal"] = 15 if carbs else 300
    print(f"  a meal with {carbs:3d} g carbs just eaten -> risk {risk(r):.2f}")
for mult in (0, 1, 3):
    r = base.copy()
    r["act_kcal_60m"] = base["act_kcal_60m"] * mult
    r["mets_mean_30m"] = base["mets_mean_30m"] * max(mult, 0.5)
    print(f"  activity x{mult} -> risk {risk(r):.2f}")
