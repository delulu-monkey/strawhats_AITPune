import joblib, pandas as pd
b = joblib.load("models/xgb_spike_model.pkl")
m, F = b["model"], b["features"]
df = pd.read_csv("data/processed/features.csv.gz")
df = df[(df.glu_now <= 180) & (df.group == "t2d")].sample(4000, random_state=0)
print("Activity what-if on 4,000 T2D moments:")
for mult in (0, 0.5, 1, 2, 3):
    d = df[F].copy()
    d["act_kcal_60m"] *= mult
    d["mets_mean_30m"] *= mult
    p = m.predict_proba(d)[:, 1]
    print(f"  activity x{mult}: mean risk score {p.mean():.3f}, at WATCH or above: {(p >= 0.75).mean():.1%}")
