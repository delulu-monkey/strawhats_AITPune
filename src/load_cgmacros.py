from pathlib import Path
import pandas as pd

root = Path("data/raw/cgmacros")
Path("data/processed").mkdir(parents=True, exist_ok=True)

# ---- Profiles (EHR) ----
bio = pd.read_csv(next(root.rglob("bio.csv")))
bio.columns = bio.columns.str.strip()
bio = bio.rename(columns={"Age": "age", "Gender": "gender", "BMI": "bmi",
                          "A1c PDL (Lab)": "hba1c",
                          "Fasting GLU - PDL (Lab)": "fasting_glu"})
bio = bio[["subject", "age", "gender", "bmi", "hba1c", "fasting_glu"]]
bio["group"] = pd.cut(bio.hba1c, [0, 5.7, 6.5, 20],
                      labels=["healthy", "prediabetes", "t2d"], right=False)

# ---- Sensor + meal data, one file per participant ----
frames = []
for f in sorted(root.rglob("CGMacros-0*.csv")):
    d = pd.read_csv(f, parse_dates=["Timestamp"])
    d.columns = d.columns.str.strip()
    d = d.drop(columns=["Unnamed: 0", "Image path"], errors="ignore")
    d.insert(0, "subject", int(f.stem.split("-")[1]))
    frames.append(d)

cgm = pd.concat(frames, ignore_index=True).rename(columns={
    "Timestamp": "time", "Libre GL": "libre", "Dexcom GL": "dexcom",
    "HR": "hr", "Calories (Activity)": "act_kcal", "METs": "mets",
    "Meal Type": "meal_type", "Calories": "kcal", "Carbs": "carbs",
    "Protein": "protein", "Fat": "fat", "Fiber": "fiber",
    "Amount Consumed": "amount_consumed"})
cgm = cgm.merge(bio, on="subject", how="left")
cgm.to_csv("data/processed/cgmacros_all.csv.gz", index=False)

# ---- Summary ----
print("Participants per group:")
print(cgm.groupby("group", observed=True).subject.nunique(), "\n")

print("Missing share per sensor (average over people):")
print(cgm.groupby("subject")[["libre", "dexcom", "hr"]]
         .agg(lambda s: s.isna().mean()).mean().round(3), "\n")

for sensor in ("libre", "dexcom"):
    for thr in (140, 180):
        share = (cgm[sensor] > thr).groupby(cgm["group"], observed=True).mean()
        print(f"Share of time {sensor} > {thr}:\n{share.round(3)}\n")
