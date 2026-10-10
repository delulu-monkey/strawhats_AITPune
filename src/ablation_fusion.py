import numpy as np, pandas as pd
from sklearn.model_selection import GroupKFold
from sklearn.metrics import roc_auc_score
from xgboost import XGBClassifier

THR = 180
df = pd.read_csv("data/processed/features.csv.gz")
df = df[df.glu_now <= THR].reset_index(drop=True)
df["y"] = (df.future_max > THR).astype(int)

GLU = ["glu_now", "glu_chg_15m", "glu_chg_30m", "glu_chg_60m",
       "glu_mean_60m", "glu_std_60m", "glu_max_120m"]
TIME = ["hour_sin", "hour_cos"]
MEAL = ["carbs_3h", "protein_3h", "fat_3h", "fiber_3h", "min_since_meal"]
WEAR = ["hr_mean_30m", "mets_mean_30m", "act_kcal_60m"]
STATIC = ["age", "male", "bmi", "hba1c", "fasting_glu"]
sets = {
    "Static EHR only": STATIC,
    "CGM only": GLU + TIME,
    "All dynamic (CGM + meals + wearable)": GLU + TIME + MEAL + WEAR,
    "FUSION: EHR + all dynamic": STATIC + GLU + TIME + MEAL + WEAR,
}
y, g = df.y, df.subject
t2d = (df.group == "t2d").values
spw = (y == 0).sum() / (y == 1).sum()
for name, cols in sets.items():
    p = np.zeros(len(df))
    for tr, te in GroupKFold(n_splits=5).split(df, y, g):
        m = XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05,
                          subsample=0.8, colsample_bytree=0.8, scale_pos_weight=spw,
                          eval_metric="logloss", n_jobs=-1)
        m.fit(df.iloc[tr][cols], y.iloc[tr])
        p[te] = m.predict_proba(df.iloc[te][cols])[:, 1]
    print(f"{name:40s} all AUC={roc_auc_score(y, p):.3f}  t2d AUC={roc_auc_score(y[t2d], p[t2d]):.3f}")
