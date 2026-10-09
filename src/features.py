import numpy as np
import pandas as pd

GLU = "libre"          # glucose sensor to use
STEP = 5               # minutes per row after resampling
H = 120 // STEP        # 24 rows = 2 hours ahead

cgm = pd.read_csv("data/processed/cgmacros_all.csv.gz", parse_dates=["time"])
# Cap implausible per-meal values (the raw data has errors, e.g. 2,830 g fiber)
CAPS = {"carbs": 250, "protein": 150, "fat": 150, "fiber": 60}
for col, cap in CAPS.items():
    cgm[col] = cgm[col].clip(upper=cap)


def build(g):
    g = g.set_index("time").sort_index()
    r = pd.DataFrame({
        "glu": g[GLU].resample("5min").mean(),
        "hr": g["hr"].resample("5min").mean(),
        "mets": g["mets"].resample("5min").mean(),
        "act_kcal": g["act_kcal"].resample("5min").sum(min_count=1),
        "carbs": g["carbs"].resample("5min").sum(),
        "protein": g["protein"].resample("5min").sum(),
        "fat": g["fat"].resample("5min").sum(),
        "fiber": g["fiber"].resample("5min").sum(),
    })
    r["glu"] = r["glu"].interpolate(limit=6)      # fill gaps up to 30 min
    r["hr"] = r["hr"].interpolate(limit=6)
    glu = r["glu"]

    f = pd.DataFrame(index=r.index)
    # --- Dynamic features: what the patient looked like up to now ---
    f["glu_now"] = glu
    for m in (15, 30, 60):
        f[f"glu_chg_{m}m"] = glu - glu.shift(m // STEP)   # how fast it is rising
    f["glu_mean_60m"] = glu.rolling(12).mean()
    f["glu_std_60m"] = glu.rolling(12).std()
    f["glu_max_120m"] = glu.rolling(24).max()
    f["hr_mean_30m"] = r["hr"].rolling(6).mean()
    f["mets_mean_30m"] = r["mets"].rolling(6).mean()
    f["act_kcal_60m"] = r["act_kcal"].rolling(12).sum()
    for c in ("carbs", "protein", "fat", "fiber"):
        f[f"{c}_3h"] = r[c].rolling(36, min_periods=1).sum()   # eaten in last 3h

    t = r.index.to_series()
    last_meal = t.where((r.carbs + r.protein + r.fat) > 0).ffill()
    f["min_since_meal"] = ((t - last_meal).dt.total_seconds() / 60).fillna(600).clip(upper=600)
    hour = r.index.hour + r.index.minute / 60
    f["hour_sin"] = np.sin(2 * np.pi * hour / 24)
    f["hour_cos"] = np.cos(2 * np.pi * hour / 24)

    # --- Target: highest glucose in the NEXT 2 hours ---
    f["future_max"] = glu[::-1].rolling(H).max()[::-1].shift(-1)
    return f


parts = []
for subj, g in cgm.groupby("subject"):
    parts.append(build(g).assign(subject=subj))
feats = pd.concat(parts).rename_axis("time").reset_index()

# --- Static features (the EHR) ---
static = (cgm.groupby("subject")[["age", "gender", "bmi", "hba1c", "fasting_glu", "group"]]
          .first().reset_index())
feats = feats.merge(static, on="subject")
feats["male"] = (feats.gender == "M").astype(int)
# Only glucose is required. Missing wearable values stay empty (NaN).
core = ["glu_now", "glu_chg_15m", "glu_chg_30m", "glu_chg_60m",
        "glu_mean_60m", "glu_std_60m", "glu_max_120m", "future_max"]
feats = feats.drop(columns="gender").dropna(subset=core)

feats.to_csv("data/processed/features.csv.gz", index=False)
print("Rows:", len(feats), "| participants:", feats.subject.nunique())

# --- Which threshold gives enough examples to learn from? ---
# We only count rows where glucose is NOT already above the threshold,
# because predicting "still high" is trivial; we want to predict a NEW spike.
for thr in (140, 160, 180):
    sub = feats[feats.glu_now <= thr]
    rate = (sub.future_max > thr).groupby(sub.group, observed=True).agg(["mean", "sum"])
    print(f"\nThreshold {thr}: share and number of rows with a spike in next 2h")
    print(rate.round(3))
