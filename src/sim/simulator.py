"""
Virtual patient simulator.
==========================

simulate(profile, days, start_date) → (glucose_df, sleep_df)

Produces 5-minute resolution data that mirrors the real CGMacros schema:
libre (glucose), hr, hrv_rmssd, steps, mets, act_kcal,
sleep_stage, carbs, protein, fat, fiber, meal_name.

Deterministic given the profile seed.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta, date
from typing import Tuple, List, Optional

import numpy as np
import pandas as pd

from src.sim.assumptions import (
    # Fasting / IR
    FASTING_GLUCOSE_INTERCEPT, FASTING_GLUCOSE_HBA1C_SLOPE,
    METFORMIN_FASTING_REDUCTION, METFORMIN_POSTMEAL_REDUCTION_FRAC,
    # Meal
    MEAL_PEAK_MINUTES, MEAL_GAMMA_SHAPE, MEAL_CARB_SENSITIVITY,
    MEAL_FIBER_OFFSET_PER_G, MEAL_PROTEIN_OFFSET_PER_G,
    MEAL_FAT_OFFSET_PER_G, MEAL_FAT_PEAK_EXTENSION_PER_10G,
    MEAL_RESPONSE_DURATION_MIN,
    # Sleep
    SLEEP_OPTIMAL_HOURS, SLEEP_DEBT_GLUCOSE_MG_PER_HOUR,
    SLEEP_DEBT_IR_FACTOR_PER_HOUR,
    SLEEP_CYCLE_MINUTES, SLEEP_DEEP_FRAC_CYCLE_1, SLEEP_DEEP_FRAC_LATER,
    SLEEP_REM_FRAC_CYCLE_1, SLEEP_REM_FRAC_LATER,
    # Activity
    ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS, ACTIVITY_MAX_DROP_PER_EPOCH,
    ACTIVITY_METS_ACTIVE_THRESHOLD,
    # Dawn
    DAWN_EFFECT_START_HOUR, DAWN_EFFECT_END_HOUR, DAWN_EFFECT_MAX_MG,
    # Sensor
    SENSOR_AR1_PHI, SENSOR_NOISE_SD,
    # Snacks
    UNLOGGED_SNACK_CARBS_MEAN, UNLOGGED_SNACK_CARBS_SD,
    # HR / HRV
    HR_BASE_AGE_INTERCEPT, HR_BASE_AGE_SLOPE, HR_ACTIVITY_PER_MET,
    HR_SLEEP_REDUCTION_FRAC,
    HRV_RMSSD_BASE, HRV_AGE_DECLINE_PER_YEAR, HRV_DEEP_SLEEP_BOOST,
    HRV_ACTIVITY_DROP_PER_MET, HRV_SLEEP_DEBT_DROP_PER_HOUR,
    # Steps / schedule
    STEP_ACTIVE_HOURS, PORTION_MULTIPLIER_RANGE,
    GLUCOSE_RETURN_HALFLIFE_MIN,
)
from src.sim.profile import VirtualPatient

# Epochs per hour / per day
EPOCH_MIN = 5
EPOCHS_PER_HOUR = 60 // EPOCH_MIN      # 12
EPOCHS_PER_DAY = 24 * EPOCHS_PER_HOUR  # 288

# ── Meal catalogue ───────────────────────────────────────────────────────────

_MEAL_CATALOGUE: Optional[pd.DataFrame] = None


def _load_meal_catalogue() -> pd.DataFrame:
    global _MEAL_CATALOGUE
    if _MEAL_CATALOGUE is None:
        _MEAL_CATALOGUE = pd.read_csv("data/indian_meals.csv")
    return _MEAL_CATALOGUE


# ── Helper: gamma-shaped meal curve ──────────────────────────────────────────

def _gamma_curve(n_epochs: int, shape: float, peak_epoch: float) -> np.ndarray:
    """Return a normalised gamma-shaped curve over *n_epochs* 5-min bins."""
    # rate = shape / peak  so mode = (shape-1)/rate = peak  (for shape>=1)
    rate = (shape - 1) / max(peak_epoch, 1)
    t = np.arange(1, n_epochs + 1).astype(float)
    y = t ** (shape - 1) * np.exp(-rate * t)
    total = y.sum()
    if total > 0:
        y /= total
    return y


# ── Sleep stage generator ────────────────────────────────────────────────────

def _generate_sleep_stages(
    n_epochs: int,
    rng: np.random.Generator,
) -> List[str]:
    """
    Produce a list of sleep stages for *n_epochs* 5-min bins.

    Rough model: repeat 90-min cycles.
    Cycle 1 is deep-heavy; later cycles are REM-heavy.
    """
    stages: List[str] = []
    epochs_per_cycle = SLEEP_CYCLE_MINUTES // EPOCH_MIN  # 18
    cycle_idx = 0
    while len(stages) < n_epochs:
        remaining = min(epochs_per_cycle, n_epochs - len(stages))
        if cycle_idx == 0:
            deep_frac = SLEEP_DEEP_FRAC_CYCLE_1
            rem_frac = SLEEP_REM_FRAC_CYCLE_1
        else:
            deep_frac = SLEEP_DEEP_FRAC_LATER
            rem_frac = SLEEP_REM_FRAC_LATER
        light_frac = 1.0 - deep_frac - rem_frac

        n_deep = max(1, int(round(remaining * deep_frac)))
        n_rem = max(1, int(round(remaining * rem_frac)))
        n_light = remaining - n_deep - n_rem
        if n_light < 0:
            n_light = 0
            n_deep = remaining - n_rem

        # Within a cycle: light → deep → light → REM
        half_light = n_light // 2
        cycle_stages = (
            ["light"] * half_light
            + ["deep"] * n_deep
            + ["light"] * (n_light - half_light)
            + ["rem"] * n_rem
        )
        stages.extend(cycle_stages[:remaining])
        cycle_idx += 1

    return stages[:n_epochs]


# ── Main simulate function ───────────────────────────────────────────────────

def simulate(
    profile: VirtualPatient,
    days: int = 7,
    start_date: Optional[date] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run the virtual patient simulation.

    Returns
    -------
    df : pd.DataFrame
        5-minute resolution data with columns matching real CGMacros where
        they overlap.
    sleep_summary : pd.DataFrame
        One row per night with sleep metrics.
    """
    profile.validate()
    if start_date is None:
        start_date = date(2025, 1, 1)

    rng = np.random.default_rng(profile.seed)
    total_epochs = days * EPOCHS_PER_DAY
    catalogue = _load_meal_catalogue()

    # Time index
    start_dt = datetime(start_date.year, start_date.month, start_date.day)
    times = pd.date_range(start_dt, periods=total_epochs, freq="5min")

    # ── Pre-compute per-day parameters ────────────────────────────────────
    ir_base = profile.insulin_resistance
    fasting_base = profile.effective_fasting_glucose

    # ── Allocate arrays ───────────────────────────────────────────────────
    glucose = np.full(total_epochs, fasting_base, dtype=float)
    hr = np.zeros(total_epochs, dtype=float)
    hrv = np.zeros(total_epochs, dtype=float)
    steps = np.zeros(total_epochs, dtype=int)
    mets = np.ones(total_epochs, dtype=float)  # resting = 1.0
    act_kcal = np.zeros(total_epochs, dtype=float)
    sleep_stage = np.array(["none"] * total_epochs, dtype=object)
    carbs_arr = np.zeros(total_epochs, dtype=float)
    protein_arr = np.zeros(total_epochs, dtype=float)
    fat_arr = np.zeros(total_epochs, dtype=float)
    fiber_arr = np.zeros(total_epochs, dtype=float)
    meal_name_arr = np.array([""] * total_epochs, dtype=object)

    # Sensor noise state (AR(1))
    sensor_noise = 0.0

    # ── Sleep schedule ────────────────────────────────────────────────────
    # For each day, determine sleep onset and duration
    sleep_records = []  # for nightly summary
    sleep_debt_today = 0.0

    for day in range(days):
        day_start_epoch = day * EPOCHS_PER_DAY

        # --- Sleep (previous night continues into this morning) ---
        bedtime_hour = profile.lifestyle.bedtime_hour
        sleep_dur_hours = max(
            3.0,
            profile.lifestyle.typical_sleep_hours
            + rng.normal(0, profile.lifestyle.sleep_variability_hours),
        )
        sleep_dur_hours = min(sleep_dur_hours, 12.0)
        sleep_debt_today = max(0, SLEEP_OPTIMAL_HOURS - sleep_dur_hours)

        # Bedtime in epochs from day start.  If bedtime >= 24, wrap.
        if bedtime_hour >= 24:
            bedtime_hour -= 24
        # Sleep starts the evening before (day-1) and extends into this day's
        # early morning, OR starts late at night and wraps.
        # Simplification: sleep occupies bedtime_hour to bedtime_hour+dur.
        bed_epoch_in_day = int(bedtime_hour * EPOCHS_PER_HOUR)
        sleep_n_epochs = int(round(sleep_dur_hours * EPOCHS_PER_HOUR))

        # Handle wrap-around: bedtime at 23:00 → epochs 276..288 + 0..N
        stages = _generate_sleep_stages(sleep_n_epochs, rng)
        for i, stg in enumerate(stages):
            ep = day_start_epoch + bed_epoch_in_day + i
            if ep < 0:
                continue
            if ep >= total_epochs:
                break
            sleep_stage[ep] = stg

        # Sleep summary
        n_deep = stages.count("deep")
        n_rem = stages.count("rem")
        n_light = stages.count("light")
        total_sleep = len(stages)
        efficiency = min(1.0, total_sleep / max(1, sleep_n_epochs + 2))  # +2 for onset
        sleep_records.append({
            "night": day,
            "date": start_date + timedelta(days=day),
            "total_sleep_hours": round(total_sleep * EPOCH_MIN / 60.0, 2),
            "deep_pct": round(100 * n_deep / max(1, total_sleep), 1),
            "rem_pct": round(100 * n_rem / max(1, total_sleep), 1),
            "efficiency_pct": round(100 * efficiency, 1),
        })

        # --- Generate steps across the day ---
        daily_steps = profile.lifestyle.steps_per_day
        active_start, active_end = STEP_ACTIVE_HOURS
        active_epochs_in_day = []
        for e in range(EPOCHS_PER_DAY):
            hour = (e * EPOCH_MIN) / 60
            if active_start <= hour < active_end and sleep_stage[day_start_epoch + e] == "none":
                active_epochs_in_day.append(e)

        if active_epochs_in_day and daily_steps > 0:
            # Distribute steps with a slight peak at morning and evening
            n_active = len(active_epochs_in_day)
            weights = np.ones(n_active)
            for idx, e in enumerate(active_epochs_in_day):
                hour = (e * EPOCH_MIN) / 60
                if 7 <= hour <= 9 or 17 <= hour <= 19:
                    weights[idx] = 2.5  # commute / exercise bump
                elif 12 <= hour <= 13:
                    weights[idx] = 1.5  # lunch walk
            weights /= weights.sum()
            epoch_steps = rng.multinomial(daily_steps, weights)
            for idx, e in enumerate(active_epochs_in_day):
                ep = day_start_epoch + e
                if ep < total_epochs:
                    steps[ep] = epoch_steps[idx]

        # --- METs and activity kcal ---
        for e in range(EPOCHS_PER_DAY):
            ep = day_start_epoch + e
            if ep >= total_epochs:
                break
            if sleep_stage[ep] != "none":
                mets[ep] = 0.9  # sleeping
                act_kcal[ep] = 0.0
            elif steps[ep] > 0:
                # ~100 steps/min = brisk walk = ~3.5 METs
                steps_per_min = steps[ep] / EPOCH_MIN
                m = 1.0 + steps_per_min / 40.0  # rough scaling
                mets[ep] = min(m, 8.0)
                # act_kcal ≈ METs * weight * duration(h) * 1.05
                act_kcal[ep] = mets[ep] * profile.weight_kg * (EPOCH_MIN / 60.0) * 1.05
            else:
                mets[ep] = 1.0
                act_kcal[ep] = 0.0

        # --- Meals ---
        on_metformin = "metformin" in [m.lower() for m in profile.medications]
        meal_times = profile.lifestyle.meal_times or {}
        for meal_key, (mh, mm) in meal_times.items():
            meal_epoch_in_day = int(mh * EPOCHS_PER_HOUR + mm / EPOCH_MIN)
            ep = day_start_epoch + meal_epoch_in_day
            if ep >= total_epochs:
                continue

            # Pick a dish from the catalogue appropriate to the meal
            dish_idx = rng.integers(0, len(catalogue))
            dish = catalogue.iloc[dish_idx]

            # Portion multiplier
            lo, hi = PORTION_MULTIPLIER_RANGE.get(meal_key, (0.8, 1.2))
            portion = rng.uniform(lo, hi)

            carbs_arr[ep] = dish["carbs"] * portion
            protein_arr[ep] = dish["protein"] * portion
            fat_arr[ep] = dish["fat"] * portion
            fiber_arr[ep] = dish["fiber"] * portion
            meal_name_arr[ep] = dish["dish"]

        # --- Unlogged snacks ---
        for e in range(EPOCHS_PER_DAY):
            ep = day_start_epoch + e
            if ep >= total_epochs:
                break
            if sleep_stage[ep] == "none":
                if rng.random() < profile.lifestyle.unlogged_snack_prob:
                    # Ghost snack: adds carbs to glucose model but NOT to the
                    # logged carbs columns (they stay 0 so it looks unlogged).
                    snack_carbs = max(
                        0, rng.normal(UNLOGGED_SNACK_CARBS_MEAN, UNLOGGED_SNACK_CARBS_SD)
                    )
                    # We inject the meal response directly into glucose below
                    # via a synthetic "ghost meal" marker.  Store in a
                    # separate tracker.
                    _inject_meal_response(
                        glucose, ep, total_epochs,
                        effective_carbs=snack_carbs,
                        fat_g=2.0,  # small
                        ir=ir_base * (1 + SLEEP_DEBT_IR_FACTOR_PER_HOUR * sleep_debt_today),
                        on_metformin=on_metformin,
                    )

        # --- Meal glucose responses (logged meals) ---
        for e in range(EPOCHS_PER_DAY):
            ep = day_start_epoch + e
            if ep >= total_epochs:
                break
            if carbs_arr[ep] > 0 or protein_arr[ep] > 0 or fat_arr[ep] > 0:
                c = carbs_arr[ep]
                p = protein_arr[ep]
                f = fat_arr[ep]
                fb = fiber_arr[ep]
                effective_carbs = max(
                    0,
                    c
                    - MEAL_FIBER_OFFSET_PER_G * fb
                    - MEAL_PROTEIN_OFFSET_PER_G * p
                    - MEAL_FAT_OFFSET_PER_G * f,
                )
                ir_now = ir_base * (1 + SLEEP_DEBT_IR_FACTOR_PER_HOUR * sleep_debt_today)
                _inject_meal_response(
                    glucose, ep, total_epochs,
                    effective_carbs=effective_carbs,
                    fat_g=f,
                    ir=ir_now,
                    on_metformin=on_metformin,
                )

        # --- Dawn phenomenon ---
        for e in range(EPOCHS_PER_DAY):
            ep = day_start_epoch + e
            if ep >= total_epochs:
                break
            hour = (e * EPOCH_MIN) / 60.0
            if DAWN_EFFECT_START_HOUR <= hour <= DAWN_EFFECT_END_HOUR:
                mid = (DAWN_EFFECT_START_HOUR + DAWN_EFFECT_END_HOUR) / 2
                half_span = (DAWN_EFFECT_END_HOUR - DAWN_EFFECT_START_HOUR) / 2
                dawn_frac = 1.0 - abs(hour - mid) / half_span
                dawn_mg = DAWN_EFFECT_MAX_MG * dawn_frac * (ir_base / 1.0)
                glucose[ep] += dawn_mg

        # --- Sleep debt raises fasting glucose in the early morning ---
        if sleep_debt_today > 0:
            for e in range(EPOCHS_PER_DAY):
                ep = day_start_epoch + e
                if ep >= total_epochs:
                    break
                hour = (e * EPOCH_MIN) / 60.0
                if 0 <= hour < 10:
                    glucose[ep] += SLEEP_DEBT_GLUCOSE_MG_PER_HOUR * sleep_debt_today

        # --- Activity lowers glucose ---
        for e in range(EPOCHS_PER_DAY):
            ep = day_start_epoch + e
            if ep >= total_epochs:
                break
            if steps[ep] > 0:
                drop = min(
                    ACTIVITY_MAX_DROP_PER_EPOCH,
                    ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS * steps[ep] / 1000.0,
                )
                glucose[ep] -= drop

    # ── Glucose dynamics: return-to-fasting + smoothing ───────────────────
    # Apply exponential return toward fasting between meals and smooth.
    decay = math.exp(-math.log(2) * EPOCH_MIN / GLUCOSE_RETURN_HALFLIFE_MIN)
    smoothed = np.copy(glucose)
    for i in range(1, total_epochs):
        diff = smoothed[i] - fasting_base
        smoothed[i] = fasting_base + decay * (smoothed[i - 1] - fasting_base) + (1 - decay) * diff
    glucose = smoothed

    # ── Sensor noise (AR(1)) ──────────────────────────────────────────────
    noise = np.zeros(total_epochs)
    for i in range(total_epochs):
        sensor_noise = SENSOR_AR1_PHI * sensor_noise + rng.normal(0, SENSOR_NOISE_SD)
        noise[i] = sensor_noise
    glucose = glucose + noise

    # Clamp to physiological range
    glucose = np.clip(glucose, 40, 400)

    # ── Heart rate and HRV ────────────────────────────────────────────────
    resting_hr = profile.lifestyle.resting_heart_rate
    base_hrv = max(5, HRV_RMSSD_BASE - HRV_AGE_DECLINE_PER_YEAR * max(0, profile.age - 20))

    for i in range(total_epochs):
        stage = sleep_stage[i]
        met = mets[i]

        # HR
        h = resting_hr + HR_ACTIVITY_PER_MET * max(0, met - 1.0)
        if stage != "none":
            h *= (1.0 - HR_SLEEP_REDUCTION_FRAC)
        hr[i] = h + rng.normal(0, 2.0)  # small jitter

        # HRV
        hv = base_hrv
        if stage == "deep":
            hv += HRV_DEEP_SLEEP_BOOST
        elif stage == "rem":
            hv += HRV_DEEP_SLEEP_BOOST * 0.3
        elif stage in ("light",):
            hv += HRV_DEEP_SLEEP_BOOST * 0.5
        hv -= HRV_ACTIVITY_DROP_PER_MET * max(0, met - 1.0)
        # Sleep debt
        # Use a rough running debt (recomputed per day above, applied here)
        # For simplicity, we use the last day's debt for all epochs.
        hv -= HRV_SLEEP_DEBT_DROP_PER_HOUR * max(0, SLEEP_OPTIMAL_HOURS - profile.lifestyle.typical_sleep_hours)
        hrv[i] = max(5, hv + rng.normal(0, 3.0))

    hr = np.clip(hr, 35, 200)

    # ── Assemble DataFrame ────────────────────────────────────────────────
    df = pd.DataFrame({
        "time": times,
        "patient_id": profile.patient_id,
        "source": "simulated",
        "libre": np.round(glucose, 1),
        "hr": np.round(hr, 1),
        "hrv_rmssd": np.round(hrv, 1),
        "steps": steps,
        "mets": np.round(mets, 2),
        "act_kcal": np.round(act_kcal, 1),
        "sleep_stage": sleep_stage,
        "carbs": np.round(carbs_arr, 1),
        "protein": np.round(protein_arr, 1),
        "fat": np.round(fat_arr, 1),
        "fiber": np.round(fiber_arr, 1),
        "meal_name": meal_name_arr,
    })

    # ── Sleep summary ─────────────────────────────────────────────────────
    sleep_summary = pd.DataFrame(sleep_records)

    return df, sleep_summary


# ── Helpers ───────────────────────────────────────────────────────────────────

def _inject_meal_response(
    glucose: np.ndarray,
    start_epoch: int,
    total_epochs: int,
    effective_carbs: float,
    fat_g: float,
    ir: float,
    on_metformin: bool,
) -> None:
    """Add a gamma-shaped glucose excursion to the glucose array in-place."""
    if effective_carbs <= 0:
        return
    n_response = MEAL_RESPONSE_DURATION_MIN // EPOCH_MIN  # 36 epochs

    # Adjust peak for fat content
    peak_min = MEAL_PEAK_MINUTES + MEAL_FAT_PEAK_EXTENSION_PER_10G * (fat_g / 10.0) * MEAL_PEAK_MINUTES
    peak_epoch = peak_min / EPOCH_MIN

    curve = _gamma_curve(n_response, MEAL_GAMMA_SHAPE, peak_epoch)
    amplitude = effective_carbs * MEAL_CARB_SENSITIVITY * ir

    if on_metformin:
        amplitude *= (1.0 - METFORMIN_POSTMEAL_REDUCTION_FRAC)

    for j in range(n_response):
        ep = start_epoch + j
        if ep >= total_epochs:
            break
        glucose[ep] += amplitude * curve[j]
