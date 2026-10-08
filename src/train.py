import numpy as np
import pandas as pd
import joblib
from sklearn.model_selection import GroupKFold
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.metrics import roc_auc_score, average_precision_score, precision_score, recall_score
from xgboost import XGBClassifier
from sklearn.impute import SimpleImputer

THR = 180
df = pd.read_csv("data/processed/features.csv.gz", parse_dates=["time"])
df = df[df.glu_now <= THR].copy()              # predict NEW spikes only
df["y"] = (df.future_max > THR).astype(int)

DROP = ("time", "subject", "group", "future_max", "y")
FEATURES = [c for c in df.columns if c not in DROP]
X, y, g = df[FEATURES], df["y"], df["subject"]
print(f"Rows: {len(df)} | spike rate: {y.mean():.3f} | features: {len(FEATURES)}")

models = {
    "logistic": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(),
                          LogisticRegression(max_iter=1000, class_weight="balanced")),
    "xgboost": XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                             subsample=0.8, colsample_bytree=0.8,
                             scale_pos_weight=(y == 0).sum() / (y == 1).sum(),
                             eval_metric="logloss", n_jobs=-1),
}

# Split by PERSON: every test person is unseen during training
oof = {name: np.zeros(len(df)) for name in models}
for tr, te in GroupKFold(n_splits=5).split(X, y, g):
    for name, m in models.items():
        m.fit(X.iloc[tr], y.iloc[tr])
        oof[name][te] = m.predict_proba(X.iloc[te])[:, 1]


def report(name, mask, label):
    yt, p = y[mask], oof[name][mask]
    pred = p >= 0.5
    print(f"{name:9s} {label:4s} AUC={roc_auc_score(yt, p):.3f}  "
          f"PR-AUC={average_precision_score(yt, p):.3f}  "
          f"precision={precision_score(yt, pred, zero_division=0):.3f}  "
          f"recall={recall_score(yt, pred):.3f}  (base rate {yt.mean():.3f})")


all_mask = np.ones(len(df), dtype=bool)
t2d_mask = (df.group == "t2d").values
for name in models:
    report(name, all_mask, "all")
    report(name, t2d_mask, "t2d")

# A simple rule the ML models must beat: "high and rising"
rule = (df.glu_now + 2 * df.glu_chg_30m).values
print(f"\nSimple rule  all AUC={roc_auc_score(y, rule):.3f}  "
      f"t2d AUC={roc_auc_score(y[t2d_mask], rule[t2d_mask]):.3f}")

# Final model on all data, saved for the dashboard
models["xgboost"].fit(X, y)
joblib.dump({"model": models["xgboost"], "features": FEATURES}, "models/xgb_spike_model.pkl")
print("Saved models/xgb_spike_model.pkl")

WEARABLE = ["hr_mean_30m", "mets_mean_30m", "act_kcal_60m"]
sets = {
    "glucose + EHR + meals": [f for f in FEATURES if f not in WEARABLE],
    "+ wearable (HR, activity)": FEATURES,
}
print("\nDoes the wearable help? (XGBoost, unseen people)")
for label, cols in sets.items():
    p = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=5).split(X, y, g):
        m = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8,
                          scale_pos_weight=(y == 0).sum() / (y == 1).sum(),
                          eval_metric="logloss", n_jobs=-1)
        m.fit(X.iloc[tr][cols], y.iloc[tr])
        p[te] = m.predict_proba(X.iloc[te][cols])[:, 1]
    print(f"{label:28s} all AUC={roc_auc_score(y, p):.3f}  "
          f"t2d AUC={roc_auc_score(y[t2d_mask], p[t2d_mask]):.3f}")
