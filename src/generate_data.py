import numpy as np
import pandas as pd
from pathlib import Path

rng = np.random.default_rng(42)
STEP_MIN = 15                      # one reading every 15 minutes
PER_DAY = 24 * 60 // STEP_MIN      # 96 readings per day

# (meal name, approx carbs in grams) - illustrative values
BREAKFAST = [("idli_sambar", 45), ("poha", 50), ("paratha", 55), ("dosa", 50)]
LUNCH     = [("dal_rice", 90), ("roti_sabzi", 60), ("rajma_rice", 100), ("biryani", 110)]
SNACK     = [("chai_biscuit", 25), ("samosa", 30), ("fruit", 20), ("sweets", 40)]
DINNER    = [("roti_sabzi", 60), ("dal_rice", 85), ("khichdi", 65), ("biryani", 110)]
SLOTS = [(8.0, BREAKFAST), (13.0, LUNCH), (17.0, SNACK), (20.5, DINNER)]


def meal_curve(minutes_since, tau=60):
    """Glucose bump after a meal: rises, peaks near tau minutes, then falls."""
    x = np.clip(minutes_since, 0, None) / tau
    return np.where(minutes_since >= 0, x * np.exp(1 - x), 0.0)


def simulate_patient(pid, days=14, start="2026-01-01"):
    n = days * PER_DAY
    t = pd.date_range(start, periods=n, freq=f"{STEP_MIN}min")
    minutes = np.arange(n) * STEP_MIN

    # ---- Static data (the simulated EHR) ----
    hba1c = rng.uniform(6.5, 9.5)
    ehr = {
        "patient_id": pid,
        "age": int(np.clip(rng.normal(52, 10), 30, 75)),
        "sex": rng.choice(["M", "F"]),
        "bmi": round(float(np.clip(rng.normal(26.5, 3.5), 18, 40)), 1),
        "hba1c": round(hba1c, 1),
        "years_since_diagnosis": int(rng.integers(1, 15)),
        "on_metformin": int(rng.random() < 0.8),
    }
    fasting = 95 + (hba1c - 6.5) * 18          # resting glucose, roughly 95-149
    k = rng.uniform(0.3, 0.8) * hba1c / 7      # meal response strength

    glucose = np.full(n, fasting, dtype=float)
    steps = np.zeros(n)
    meals, sleeps = [], []
    hours = (np.arange(PER_DAY) * STEP_MIN) / 60

    for d in range(days):
        s = d * PER_DAY
        # Sleep (night before this day). Less sleep -> higher glucose that day.
        sleep_h = float(np.clip(rng.normal(6.5, 1.0), 4, 9))
        sleeps.append({"patient_id": pid, "date": t[s].date(),
                       "sleep_hours": round(sleep_h, 2)})
        glucose[s:s + PER_DAY] += max(0, 7 - sleep_h) * 6

        # Baseline steps: active in daytime, almost none at night
        day_mask = (hours >= 7) & (hours < 22)
        steps[s:s + PER_DAY] = np.where(day_mask,
                                        rng.poisson(40, PER_DAY),
                                        rng.poisson(2, PER_DAY))

        # Meals
        for hour, options in SLOTS:
            m_min = d * 1440 + int(rng.normal(hour * 60, 30))
            name, carbs = options[rng.integers(len(options))]
            idx = min(max(m_min // STEP_MIN, 0), n - 1)
            glucose += k * carbs * meal_curve(minutes - m_min)
            meals.append({"patient_id": pid, "timestamp": t[idx],
                          "meal": name, "carbs_g": carbs})
            # 40% chance of a short walk after the meal
            if rng.random() < 0.4:
                w = idx + 2
                steps[w:w + 4] += rng.poisson(600, len(steps[w:w + 4]))

    # Walking lowers glucose; add smooth random noise
    activity = pd.Series(steps).rolling(4, min_periods=1).mean().values
    glucose -= 0.02 * activity
    noise = np.zeros(n)
    for i in range(1, n):
        noise[i] = 0.9 * noise[i - 1] + rng.normal(0, 3)
    glucose = np.clip(glucose + noise, 50, 400)

    # Heart rate
    resting = rng.uniform(62, 82)
    night = (np.tile(hours, days) < 6)
    hr = resting + 0.03 * steps - 5 * night + rng.normal(0, 3, n)

    wearable = pd.DataFrame({"patient_id": pid, "timestamp": t,
                             "glucose": glucose.round(1),
                             "heart_rate": hr.round(0),
                             "steps": steps.astype(int)})
    return ehr, wearable, pd.DataFrame(meals), pd.DataFrame(sleeps)


if __name__ == "__main__":
    out = Path("data/raw")
    out.mkdir(parents=True, exist_ok=True)
    ehrs, wears, meals, sleeps = [], [], [], []
    for pid in range(1, 151):                 # 150 synthetic patients
        e, w, m, s = simulate_patient(pid)
        ehrs.append(e); wears.append(w); meals.append(m); sleeps.append(s)
    pd.DataFrame(ehrs).to_csv(out / "ehr.csv", index=False)
    pd.concat(wears).to_csv(out / "wearable.csv", index=False)
    pd.concat(meals).to_csv(out / "meals.csv", index=False)
    pd.concat(sleeps).to_csv(out / "sleep.csv", index=False)
    print("Done: 150 patients written to data/raw/")
