"""
Virtual Patient Featurizer.
===========================

Transforms raw 5-minute simulated (or real) patient data into the exact feature
table used by `build()` in `src/features.py`, enabling existing models
(e.g., `models/xgb_spike_model.pkl`) and new Digital Twin models to score
simulated or real trajectories.
"""

from __future__ import annotations

from typing import Optional
import numpy as np
import pandas as pd

from src.sim.profile import VirtualPatient

# Glucose sensor column and temporal window constants (matching src/features.py)
GLU_COL = "libre"
STEP_MIN = 5
HORIZON_STEPS = 120 // STEP_MIN  # 24 rows = 2 hours ahead

# Macro caps matching src/features.py
MACRO_CAPS = {"carbs": 250.0, "protein": 150.0, "fat": 150.0, "fiber": 60.0}

# Standard feature sets
REAL_DYNAMIC_FEATURES = [
    "glu_now", "glu_chg_15m", "glu_chg_30m", "glu_chg_60m",
    "glu_mean_60m", "glu_std_60m", "glu_max_120m",
    "hr_mean_30m", "mets_mean_30m", "act_kcal_60m",
    "carbs_3h", "protein_3h", "fat_3h", "fiber_3h",
    "min_since_meal", "hour_sin", "hour_cos",
]

STATIC_FEATURES = ["age", "bmi", "hba1c", "fasting_glu", "male"]

TWIN_EXTRA_FEATURES = [
    "sleep_hours_last_night",
    "deep_pct_last_night",
    "steps_60m",
    "hrv_rmssd_30m",
    "genetic_risk_score",
]


def featurize_patient(
    df: pd.DataFrame,
    profile: Optional[VirtualPatient] = None,
    sleep_summary: Optional[pd.DataFrame] = None,
    include_twin_features: bool = False,
    include_target: bool = True,
) -> pd.DataFrame:
    """
    Construct model features from a patient's timeseries DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Must have `time`, `libre` (or `glu`), `hr`, `mets`, `act_kcal`,
        `carbs`, `protein`, `fat`, `fiber`.
    profile : VirtualPatient, optional
        Supplies static demographics and genetics when featurizing simulated patients.
    sleep_summary : pd.DataFrame, optional
        Nightly summary from simulator (`simulate()`).
    include_twin_features : bool, default False
        Whether to compute the additional simulated twin features (sleep, steps_60m, HRV, GRS).
    include_target : bool, default True
        Whether to compute `future_max` (max glucose in next 2 hours).

    Returns
    -------
    pd.DataFrame with 5-minute index and computed features.
    """
    g = df.copy()

    # Apply macro caps
    for col, cap in MACRO_CAPS.items():
        if col in g.columns:
            g[col] = g[col].clip(upper=cap)

    # Ensure datetime index
    if "time" in g.columns:
        g = g.set_index("time").sort_index()
    elif not isinstance(g.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must contain a 'time' column or DatetimeIndex.")

    # Identify glucose column
    glu_name = GLU_COL if GLU_COL in g.columns else ("glu" if "glu" in g.columns else None)
    if glu_name is None:
        raise ValueError(f"Neither '{GLU_COL}' nor 'glu' found in columns: {g.columns.tolist()}")

    # Resample to 5-minute grid (matching build() in src/features.py)
    r = pd.DataFrame(index=pd.date_range(g.index.min(), g.index.max(), freq="5min", name="time"))
    r["glu"] = g[glu_name].resample("5min").mean()
    r["hr"] = g["hr"].resample("5min").mean() if "hr" in g.columns else np.nan
    r["mets"] = g["mets"].resample("5min").mean() if "mets" in g.columns else 1.0
    r["act_kcal"] = g["act_kcal"].resample("5min").sum(min_count=1) if "act_kcal" in g.columns else 0.0

    for c in ("carbs", "protein", "fat", "fiber"):
        r[c] = g[c].resample("5min").sum() if c in g.columns else 0.0

    # Fill small gaps
    r["glu"] = r["glu"].interpolate(limit=6)
    r["hr"] = r["hr"].interpolate(limit=6)
    glu = r["glu"]

    f = pd.DataFrame(index=r.index)

    # --- Dynamic features ---
    f["glu_now"] = glu
    for m in (15, 30, 60):
        f[f"glu_chg_{m}m"] = glu - glu.shift(m // STEP_MIN)
    f["glu_mean_60m"] = glu.rolling(12).mean()
    f["glu_std_60m"] = glu.rolling(12).std()
    f["glu_max_120m"] = glu.rolling(24).max()
    f["hr_mean_30m"] = r["hr"].rolling(6).mean()
    f["mets_mean_30m"] = r["mets"].rolling(6).mean()
    f["act_kcal_60m"] = r["act_kcal"].rolling(12).sum()
    for c in ("carbs", "protein", "fat", "fiber"):
        f[f"{c}_3h"] = r[c].rolling(36, min_periods=1).sum()

    t = r.index.to_series()
    last_meal = t.where((r.carbs + r.protein + r.fat) > 0).ffill()
    f["min_since_meal"] = ((t - last_meal).dt.total_seconds() / 60.0).fillna(600.0).clip(upper=600.0)
    hour = r.index.hour + r.index.minute / 60.0
    f["hour_sin"] = np.sin(2 * np.pi * hour / 24.0)
    f["hour_cos"] = np.cos(2 * np.pi * hour / 24.0)

    # --- Target: highest glucose in the NEXT 2 hours ---
    if include_target:
        f["future_max"] = glu[::-1].rolling(HORIZON_STEPS).max()[::-1].shift(-1)

    # --- Static EHR features ---
    # Attach from profile if available, else from input columns if present
    if profile is not None:
        f["age"] = profile.age
        f["bmi"] = profile.bmi
        f["hba1c"] = profile.hba1c
        f["fasting_glu"] = profile.effective_fasting_glucose
        f["male"] = 1 if profile.sex.upper() == "M" else 0
    else:
        for col in ["age", "bmi", "hba1c", "fasting_glu"]:
            if col in g.columns:
                f[col] = g[col].iloc[0]
        if "male" in g.columns:
            f["male"] = g["male"].iloc[0]
        elif "gender" in g.columns:
            f["male"] = int(g["gender"].iloc[0] == "M")

    # --- Extra Twin Features ---
    if include_twin_features:
        # 1. Sleep features from sleep_summary
        dates = pd.Series(f.index.date, index=f.index)
        if sleep_summary is not None and len(sleep_summary) > 0:
            sl_map = sleep_summary.set_index("date")
            # Map each epoch to previous night's sleep (or current date's morning sleep)
            prev_dates = dates - pd.Timedelta(days=1)
            f["sleep_hours_last_night"] = prev_dates.map(sl_map["total_sleep_hours"]).fillna(
                profile.lifestyle.typical_sleep_hours if profile else 7.0
            )
            f["deep_pct_last_night"] = prev_dates.map(sl_map["deep_pct"]).fillna(
                20.0
            )
        elif profile is not None:
            f["sleep_hours_last_night"] = profile.lifestyle.typical_sleep_hours
            f["deep_pct_last_night"] = 20.0
        else:
            f["sleep_hours_last_night"] = 7.0
            f["deep_pct_last_night"] = 20.0

        # 2. Steps in the last hour
        if "steps" in g.columns:
            steps_5m = g["steps"].resample("5min").sum()
            f["steps_60m"] = steps_5m.rolling(12, min_periods=1).sum().reindex(f.index, fill_value=0.0)
        else:
            f["steps_60m"] = 0.0

        # 3. HRV in last 30 minutes
        if "hrv_rmssd" in g.columns:
            hrv_5m = g["hrv_rmssd"].resample("5min").mean().interpolate(limit=6)
            f["hrv_rmssd_30m"] = hrv_5m.rolling(6, min_periods=1).mean().reindex(f.index).fillna(35.0)
        else:
            f["hrv_rmssd_30m"] = 35.0

        # 4. Genetic risk score
        if profile is not None:
            f["genetic_risk_score"] = profile.genetic_markers.genetic_risk_score
        else:
            f["genetic_risk_score"] = 50.0

    return f


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Direct alias matching build() from src/features.py for testing and compatibility.
    """
    return featurize_patient(df, include_twin_features=False, include_target=True)
