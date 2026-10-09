import numpy as np, pandas as pd, joblib
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.dummy import DummyRegressor
from sklearn.metrics import mean_absolute_error, r2_score

CAPS = {"carbs": 250, "protein": 150, "fat": 150, "fiber": 60}
cgm = pd.read_csv("data/processed/cgmacros_all.csv.gz", parse_dates=["time"])
for col, cap in CAPS.items():
    cgm[col] = cgm[col].clip(upper=cap)

rows = []
for subj, d in cgm.groupby("subject"):
    d = d.sort_values("time").set_index("time")
    glu = d["libre"]
    meals = d[d.carbs.notna()]
    times = meals.index
    for i in range(len(times)):
        t, m = times[i], meals.iloc[i]
        prev_gap = (t - times[i - 1]).total_seconds() / 60 if i > 0 else 9999
        next_gap = (times[i + 1] - t).total_seconds() / 60 if i < len(times) - 1 else 9999
        if prev_gap < 120 or next_gap < 120:
            continue                       # overlapping meals would muddy the response
        w = glu[t: t + pd.Timedelta(minutes=120)]
        if len(w) < 110 or w.isna().any():
            continue
        rows.append({
            "subject": subj, "group": m["group"],
            "carbs": m["carbs"], "protein": m["protein"], "fat": m["fat"],
            "fiber": m["fiber"], "glu0": w.iloc[0],
            "hour": t.hour + t.minute / 60,
            "age": m["age"], "bmi": m["bmi"], "hba1c": m["hba1c"],
            "fasting_glu": m["fasting_glu"], "male": int(m["gender"] == "M"),
            "rise": w.max() - w.iloc[0],   # biggest increase within 2 hours
        })

df = pd.DataFrame(rows)
print(f"Usable meals: {len(df)} from {df.subject.nunique()} people "
      f"(T2D: {(df.group == 't2d').sum()})")
print("Average 2-hour rise (mg/dL) by group:")
print(df.groupby("group", observed=True).rise.mean().round(1))

FEATURES = ["carbs", "protein", "fat", "fiber", "glu0", "hour",
            "age", "bmi", "hba1c", "fasting_glu", "male"]
X, y, g = df[FEATURES], df["rise"], df["subject"]
t2d = (df.group == "t2d").values

models = {
    "Predict the average": DummyRegressor(strategy="mean"),
    "Ridge": make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=10)),
    "Random forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=10,
                                           random_state=0, n_jobs=-1),
}
oof = {k: np.zeros(len(df)) for k in models}
for tr, te in GroupKFold(n_splits=5).split(X, y, g):
    for k, m in models.items():
        m.fit(X.iloc[tr], y.iloc[tr])
        oof[k][te] = m.predict(X.iloc[te])

print("\nPredicting the 2-hour glucose rise for UNSEEN people:")
for k, p in oof.items():
    print(f"  {k:20s} all: MAE={mean_absolute_error(y, p):5.1f}  R2={r2_score(y, p):+.2f}"
          f" | T2D: MAE={mean_absolute_error(y[t2d], p[t2d]):5.1f}  R2={r2_score(y[t2d], p[t2d]):+.2f}")

# Final model (Ridge) and what a gram of each macro is worth, in plain units
ridge = models["Ridge"].fit(X, y)
scaler, lin = ridge[1], ridge[2]
per_unit = pd.Series(lin.coef_ / scaler.scale_, index=FEATURES)
print("\nRidge effect per 1 unit:", per_unit[["carbs", "protein", "fat", "fiber"]].round(2).to_dict())

# What-if sanity check on a typical T2D patient
base = X[t2d].median()
print("\nTypical T2D patient, predicted 2-hour rise (mg/dL):")
for carbs in (0, 30, 60, 100):
    r = base.copy(); r["carbs"] = carbs
    print(f"  {carbs:3d} g carbs -> {ridge.predict(pd.DataFrame([r])[FEATURES])[0]:.0f}")

joblib.dump({"model": ridge, "features": FEATURES}, "models/meal_response_ridge.pkl")

rf = models["Random forest"].fit(X, y)
print("\nRandom forest, same what-if (typical T2D patient):")
for carbs in (0, 30, 60, 100):
    r = base.copy(); r["carbs"] = carbs
    print(f"  {carbs:3d} g carbs -> {rf.predict(pd.DataFrame([r])[FEATURES])[0]:.0f}")
for fib in (0, 10, 20):
    r = base.copy(); r["carbs"] = 60; r["fiber"] = fib
    print(f"  60 g carbs + {fib:2d} g fiber -> {rf.predict(pd.DataFrame([r])[FEATURES])[0]:.0f}")
joblib.dump({"model": rf, "features": FEATURES}, "models/meal_response_rf.pkl")
