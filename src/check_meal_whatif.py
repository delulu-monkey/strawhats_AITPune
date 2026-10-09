import joblib, pandas as pd
b = joblib.load("models/meal_response_rf.pkl")
m, F = b["model"], b["features"]
f = pd.read_csv("data/processed/features.csv.gz", parse_dates=["time"])
f = f[f.group == "t2d"].sample(3000, random_state=0)

base = pd.DataFrame({
    "protein": 15.0, "fat": 10.0, "fiber": 4.0,
    "glu0": f.glu_now.values,
    "hour": f.time.dt.hour.values + f.time.dt.minute.values / 60,
    "age": f.age.values, "bmi": f.bmi.values, "hba1c": f.hba1c.values,
    "fasting_glu": f.fasting_glu.values, "male": f.male.values})

res = {}
for carbs in (0, 20, 50, 100, 150):
    d = base.copy(); d["carbs"] = carbs
    res[carbs] = m.predict(d[F])
    print(f"{carbs:3d} g carbs: mean predicted rise {res[carbs].mean():5.1f}, "
          f"mean peak {(base.glu0 + res[carbs]).mean():5.1f}")

print("\nShare of moments where 100 g gives a higher peak than 20 g:",
      round(float((res[100] > res[20]).mean()), 3))

print("\nPredicted rise for a 50 g meal, by starting glucose:")
d = base.copy(); d["carbs"] = 50
d["rise"] = m.predict(d[F])
d["start"] = pd.cut(d.glu0, [0, 80, 110, 150, 400])
print(d.groupby("start", observed=True).rise.agg(["mean", "count"]).round(1))
