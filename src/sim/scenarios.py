"""
Counterfactual Scenario Sandbox Simulator.
==========================================

simulate_scenario(patient, start_moment, scenario) -> (baseline_df, scenario_df)

Re-simulates the next 24 hours under a specified counterfactual scenario:
- change tonight's sleep duration (hours)
- add an extra meal from data/indian_meals.csv with portions and time
- add a walk with duration (minutes) and time
- change habitual daily steps

Both baseline and scenario use the EXACT same random seed so that the only
divergence between the two curves is the clinical scenario intervention.
All effects reflect documented simulator assumptions, not learned real-data patterns.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from src.sim.assumptions import (
    # Fasting / IR
    FASTING_GLUCOSE_INTERCEPT,
    FASTING_GLUCOSE_HBA1C_SLOPE,
    METFORMIN_FASTING_REDUCTION,
    METFORMIN_POSTMEAL_REDUCTION_FRAC,
    # Meal response
    MEAL_PEAK_MINUTES,
    MEAL_GAMMA_SHAPE,
    MEAL_CARB_SENSITIVITY,
    MEAL_FIBER_OFFSET_PER_G,
    MEAL_PROTEIN_OFFSET_PER_G,
    MEAL_FAT_OFFSET_PER_G,
    MEAL_FAT_PEAK_EXTENSION_PER_10G,
    MEAL_RESPONSE_DURATION_MIN,
    # Sleep
    SLEEP_OPTIMAL_HOURS,
    SLEEP_DEBT_GLUCOSE_MG_PER_HOUR,
    SLEEP_DEBT_IR_FACTOR_PER_HOUR,
    SLEEP_CYCLE_MINUTES,
    SLEEP_DEEP_FRAC_CYCLE_1,
    SLEEP_DEEP_FRAC_LATER,
    SLEEP_REM_FRAC_CYCLE_1,
    SLEEP_REM_FRAC_LATER,
    # Activity
    ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS,
    ACTIVITY_MAX_DROP_PER_EPOCH,
    ACTIVITY_METS_ACTIVE_THRESHOLD,
    # Dawn effect
    DAWN_EFFECT_START_HOUR,
    DAWN_EFFECT_END_HOUR,
    DAWN_EFFECT_MAX_MG,
    # Sensor noise
    SENSOR_AR1_PHI,
    SENSOR_NOISE_SD,
    # Snacks
    UNLOGGED_SNACK_CARBS_MEAN,
    UNLOGGED_SNACK_CARBS_SD,
    # Heart rate & HRV
    HR_BASE_AGE_INTERCEPT,
    HR_BASE_AGE_SLOPE,
    HR_ACTIVITY_PER_MET,
    HR_SLEEP_REDUCTION_FRAC,
    HRV_RMSSD_BASE,
    HRV_AGE_DECLINE_PER_YEAR,
    HRV_DEEP_SLEEP_BOOST,
    HRV_ACTIVITY_DROP_PER_MET,
    HRV_SLEEP_DEBT_DROP_PER_HOUR,
    # Dynamics
    STEP_ACTIVE_HOURS,
    PORTION_MULTIPLIER_RANGE,
    GLUCOSE_RETURN_HALFLIFE_MIN,
)
from src.sim.profile import VirtualPatient
from src.sim.simulator import EPOCH_MIN, EPOCHS_PER_HOUR, EPOCHS_PER_DAY, _gamma_curve, _load_meal_catalogue

HOURS_24_EPOCHS = 288


@dataclass
class Scenario:
    """Intervention parameters for counterfactual 24-hour simulation."""

    name: str = "Counterfactual Scenario"
    sleep_hours: Optional[float] = None
    added_meal: Optional[Dict[str, Any]] = None   # {"dish": str, "portions": float, "time": datetime | str}
    added_walk: Optional[Dict[str, Any]] = None   # {"time": datetime | str, "duration_minutes": int, "steps_per_min": int}
    habitual_steps: Optional[int] = None


def _inject_meal_curve(
    glucose_arr: np.ndarray,
    start_epoch: int,
    total_epochs: int,
    effective_carbs: float,
    fat_g: float,
    ir: float,
    on_metformin: bool,
) -> None:
    """Inject gamma-shaped postprandial glucose excursion."""
    if effective_carbs <= 0:
        return

    peak_min = MEAL_PEAK_MINUTES * (1.0 + MEAL_FAT_PEAK_EXTENSION_PER_10G * (fat_g / 10.0))
    peak_epoch = peak_min / EPOCH_MIN
    n_epochs = int(MEAL_RESPONSE_DURATION_MIN / EPOCH_MIN)

    curve = _gamma_curve(n_epochs, MEAL_GAMMA_SHAPE, peak_epoch)
    total_rise = effective_carbs * MEAL_CARB_SENSITIVITY * ir
    if on_metformin:
        total_rise *= (1.0 - METFORMIN_POSTMEAL_REDUCTION_FRAC)

    for i in range(n_epochs):
        ep = start_epoch + i
        if ep < total_epochs:
            glucose_arr[ep] += curve[i] * total_rise


def _run_single_24h(
    patient: VirtualPatient,
    start_dt: datetime,
    scenario: Optional[Union[Scenario, dict]] = None,
) -> pd.DataFrame:
    """Run a single 24-hour simulation starting at start_dt with exact patient seed."""
    patient.validate()
    rng = np.random.default_rng(patient.seed)
    catalogue = _load_meal_catalogue()

    # Normalize scenario parameters
    scen_dict = scenario if isinstance(scenario, dict) else (scenario.__dict__ if scenario else {})
    sleep_override = scen_dict.get("sleep_hours")
    added_meal = scen_dict.get("added_meal")
    added_walk = scen_dict.get("added_walk")
    steps_override = scen_dict.get("habitual_steps")

    times = pd.date_range(start_dt, periods=HOURS_24_EPOCHS, freq="5min")

    # Baselines
    ir_base = patient.insulin_resistance
    fasting_base = patient.effective_fasting_glucose
    on_metformin = "metformin" in [m.lower() for m in patient.medications]

    # Pre-allocate arrays
    glucose = np.full(HOURS_24_EPOCHS, fasting_base, dtype=float)
    hr = np.zeros(HOURS_24_EPOCHS, dtype=float)
    hrv = np.zeros(HOURS_24_EPOCHS, dtype=float)
    steps = np.zeros(HOURS_24_EPOCHS, dtype=int)
    mets = np.ones(HOURS_24_EPOCHS, dtype=float)
    act_kcal = np.zeros(HOURS_24_EPOCHS, dtype=float)
    sleep_stage = np.array(["none"] * HOURS_24_EPOCHS, dtype=object)
    carbs_arr = np.zeros(HOURS_24_EPOCHS, dtype=float)
    protein_arr = np.zeros(HOURS_24_EPOCHS, dtype=float)
    fat_arr = np.zeros(HOURS_24_EPOCHS, dtype=float)
    fiber_arr = np.zeros(HOURS_24_EPOCHS, dtype=float)
    meal_name_arr = np.array([""] * HOURS_24_EPOCHS, dtype=object)

    # 1. Sleep Schedule
    if sleep_override is not None:
        sleep_dur_hours = float(np.clip(sleep_override, 3.0, 12.0))
    else:
        sleep_dur_hours = float(np.clip(
            patient.lifestyle.typical_sleep_hours + rng.normal(0, patient.lifestyle.sleep_variability_hours * 0.5),
            3.0, 12.0
        ))

    sleep_debt = max(0.0, SLEEP_OPTIMAL_HOURS - sleep_dur_hours)
    bedtime_hour = patient.lifestyle.bedtime_hour

    # Mark sleep epochs across the 24h timeline
    sleep_epochs_count = int(round(sleep_dur_hours * EPOCHS_PER_HOUR))
    for ep in range(HOURS_24_EPOCHS):
        cur_t = times[ep]
        cur_hour = cur_t.hour + cur_t.minute / 60.0
        
        # Bedtime window check
        is_sleeping = False
        if bedtime_hour + sleep_dur_hours < 24.0:
            if bedtime_hour <= cur_hour < (bedtime_hour + sleep_dur_hours):
                is_sleeping = True
        else:
            # Wraps midnight
            wake_hour = (bedtime_hour + sleep_dur_hours) - 24.0
            if cur_hour >= bedtime_hour or cur_hour < wake_hour:
                is_sleeping = True

        if is_sleeping:
            # Deterministic stage distribution
            stage_r = rng.random()
            if stage_r < 0.20:
                sleep_stage[ep] = "deep"
            elif stage_r < 0.45:
                sleep_stage[ep] = "rem"
            else:
                sleep_stage[ep] = "light"

    # 2. Habitual Daily Steps
    daily_steps = int(steps_override if steps_override is not None else patient.lifestyle.steps_per_day)
    active_start, active_end = STEP_ACTIVE_HOURS
    waking_epochs = [
        ep for ep in range(HOURS_24_EPOCHS)
        if sleep_stage[ep] == "none" and active_start <= (times[ep].hour + times[ep].minute / 60.0) < active_end
    ]

    if waking_epochs and daily_steps > 0:
        n_act = len(waking_epochs)
        w = np.ones(n_act)
        for idx, ep in enumerate(waking_epochs):
            h = times[ep].hour + times[ep].minute / 60.0
            if 7.0 <= h <= 9.0 or 17.0 <= h <= 19.0:
                w[idx] = 2.5
            elif 12.0 <= h <= 13.5:
                w[idx] = 1.5
        w /= w.sum()
        dist_steps = rng.multinomial(daily_steps, w)
        for idx, ep in enumerate(waking_epochs):
            steps[ep] = dist_steps[idx]

    # 3. Apply Scenario Added Walk
    if added_walk:
        w_time_raw = added_walk.get("time")
        if isinstance(w_time_raw, str):
            walk_time = pd.to_datetime(w_time_raw)
        elif isinstance(w_time_raw, (datetime, pd.Timestamp)):
            walk_time = pd.Timestamp(w_time_raw)
        else:
            walk_time = start_dt + timedelta(hours=2)

        walk_dur = int(added_walk.get("duration_minutes", 30))
        steps_per_min = int(added_walk.get("steps_per_min", 100))
        walk_epochs = int(np.ceil(walk_dur / EPOCH_MIN))

        walk_start_ep = int(np.clip(
            (walk_time - start_dt).total_seconds() / (EPOCH_MIN * 60),
            0, HOURS_24_EPOCHS - 1
        ))

        for i in range(walk_epochs):
            ep = walk_start_ep + i
            if ep < HOURS_24_EPOCHS:
                walk_steps_epoch = steps_per_min * EPOCH_MIN
                steps[ep] += walk_steps_epoch
                sleep_stage[ep] = "none"

    # 4. Compute METs and Activity Calories
    for ep in range(HOURS_24_EPOCHS):
        if sleep_stage[ep] != "none":
            mets[ep] = 0.9
            act_kcal[ep] = 0.0
        elif steps[ep] > 0:
            spm = steps[ep] / EPOCH_MIN
            m = 1.0 + spm / 40.0
            mets[ep] = min(m, 8.0)
            act_kcal[ep] = mets[ep] * patient.weight_kg * (EPOCH_MIN / 60.0) * 1.05
        else:
            mets[ep] = 1.0
            act_kcal[ep] = 0.0

    # 5. Background Scheduled Meals
    meal_times = patient.lifestyle.meal_times or {}
    for meal_key, (mh, mm) in meal_times.items():
        # Find epoch within the 24h window matching this hour and minute
        for ep in range(HOURS_24_EPOCHS):
            t = times[ep]
            if t.hour == mh and (mm - 2 <= t.minute <= mm + 2):
                dish_idx = rng.integers(0, len(catalogue))
                dish = catalogue.iloc[dish_idx]
                lo, hi = PORTION_MULTIPLIER_RANGE.get(meal_key, (0.8, 1.2))
                portion = rng.uniform(lo, hi)

                carbs_arr[ep] = dish["carbs"] * portion
                protein_arr[ep] = dish["protein"] * portion
                fat_arr[ep] = dish["fat"] * portion
                fiber_arr[ep] = dish["fiber"] * portion
                meal_name_arr[ep] = dish["dish"]
                break

    # 6. Apply Scenario Added Meal
    if added_meal:
        m_time_raw = added_meal.get("time")
        if isinstance(m_time_raw, str):
            meal_time = pd.to_datetime(m_time_raw)
        elif isinstance(m_time_raw, (datetime, pd.Timestamp)):
            meal_time = pd.Timestamp(m_time_raw)
        else:
            meal_time = start_dt + timedelta(hours=1)

        m_dish_name = added_meal.get("dish", "Aloo Paratha")
        m_portions = float(added_meal.get("portions", 1.0))

        m_lower = m_dish_name.lower().strip()
        match_dish = catalogue[catalogue["dish"].str.lower() == m_lower]
        if match_dish.empty:
            match_dish = catalogue[catalogue["dish"].str.lower().str.contains(m_lower, regex=False)]
        if not match_dish.empty:
            d_row = match_dish.iloc[0]
        else:
            d_row = catalogue.iloc[0]

        meal_start_ep = int(np.clip(
            (meal_time - start_dt).total_seconds() / (EPOCH_MIN * 60),
            0, HOURS_24_EPOCHS - 1
        ))

        carbs_arr[meal_start_ep] += d_row["carbs"] * m_portions
        protein_arr[meal_start_ep] += d_row["protein"] * m_portions
        fat_arr[meal_start_ep] += d_row["fat"] * m_portions
        fiber_arr[meal_start_ep] += d_row["fiber"] * m_portions
        meal_name_arr[meal_start_ep] = f"{d_row['dish']} (Scenario)"

    # 7. Unlogged Ghost Snacks (Deterministic)
    ir_effective = ir_base * (1.0 + SLEEP_DEBT_IR_FACTOR_PER_HOUR * sleep_debt)
    for ep in range(HOURS_24_EPOCHS):
        if sleep_stage[ep] == "none":
            if rng.random() < patient.lifestyle.unlogged_snack_prob:
                snack_carbs = max(0.0, rng.normal(UNLOGGED_SNACK_CARBS_MEAN, UNLOGGED_SNACK_CARBS_SD))
                _inject_meal_curve(
                    glucose, ep, HOURS_24_EPOCHS,
                    effective_carbs=snack_carbs,
                    fat_g=2.0,
                    ir=ir_effective,
                    on_metformin=on_metformin,
                )

    # 8. Inject All Logged Meals
    for ep in range(HOURS_24_EPOCHS):
        if carbs_arr[ep] > 0 or protein_arr[ep] > 0 or fat_arr[ep] > 0:
            c = carbs_arr[ep]
            p = protein_arr[ep]
            f = fat_arr[ep]
            fb = fiber_arr[ep]
            eff_c = max(0.0, c - MEAL_FIBER_OFFSET_PER_G * fb - MEAL_PROTEIN_OFFSET_PER_G * p - MEAL_FAT_OFFSET_PER_G * f)
            _inject_meal_curve(
                glucose, ep, HOURS_24_EPOCHS,
                effective_carbs=eff_c,
                fat_g=f,
                ir=ir_effective,
                on_metformin=on_metformin,
            )

    # 9. Dawn Phenomenon
    for ep in range(HOURS_24_EPOCHS):
        h = times[ep].hour + times[ep].minute / 60.0
        if DAWN_EFFECT_START_HOUR <= h <= DAWN_EFFECT_END_HOUR:
            mid = (DAWN_EFFECT_START_HOUR + DAWN_EFFECT_END_HOUR) / 2.0
            half_span = (DAWN_EFFECT_END_HOUR - DAWN_EFFECT_START_HOUR) / 2.0
            dawn_frac = 1.0 - abs(h - mid) / half_span
            dawn_mg = DAWN_EFFECT_MAX_MG * dawn_frac * (ir_base / 1.0)
            glucose[ep] += dawn_mg

    # 10. Sleep Debt Glucose Elevation (Morning hours 06:00 to 11:00)
    if sleep_debt > 0:
        for ep in range(HOURS_24_EPOCHS):
            h = times[ep].hour + times[ep].minute / 60.0
            if 6.0 <= h < 11.0:
                glucose[ep] += SLEEP_DEBT_GLUCOSE_MG_PER_HOUR * sleep_debt

    # 11. Activity Lowers Glucose
    for ep in range(HOURS_24_EPOCHS):
        if steps[ep] > 0:
            drop = min(ACTIVITY_MAX_DROP_PER_EPOCH, ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS * (steps[ep] / 1000.0))
            glucose[ep] -= drop

    # 12. Return to Fasting Baseline Dynamics
    decay = math.exp(-math.log(2) * EPOCH_MIN / GLUCOSE_RETURN_HALFLIFE_MIN)
    smoothed = np.copy(glucose)
    for ep in range(1, HOURS_24_EPOCHS):
        diff = smoothed[ep] - fasting_base
        smoothed[ep] = fasting_base + decay * (smoothed[ep - 1] - fasting_base) + (1.0 - decay) * diff
    glucose = smoothed

    # 13. Deterministic AR(1) Sensor Noise
    sensor_noise = 0.0
    for ep in range(HOURS_24_EPOCHS):
        sensor_noise = SENSOR_AR1_PHI * sensor_noise + rng.normal(0, SENSOR_NOISE_SD)
        glucose[ep] += sensor_noise

    glucose = np.clip(glucose, 40.0, 400.0)

    # 14. Heart Rate & HRV
    resting_hr = patient.lifestyle.resting_heart_rate
    base_hrv = max(5.0, HRV_RMSSD_BASE - HRV_AGE_DECLINE_PER_YEAR * max(0, patient.age - 20))

    for ep in range(HOURS_24_EPOCHS):
        stage = sleep_stage[ep]
        met = mets[ep]
        h = resting_hr + HR_ACTIVITY_PER_MET * max(0, met - 1.0)
        if stage != "none":
            h *= (1.0 - HR_SLEEP_REDUCTION_FRAC)
        hr[ep] = h + rng.normal(0, 2.0)

        hv = base_hrv
        if stage == "deep":
            hv += HRV_DEEP_SLEEP_BOOST
        elif stage == "rem":
            hv += HRV_DEEP_SLEEP_BOOST * 0.3
        elif stage == "light":
            hv += HRV_DEEP_SLEEP_BOOST * 0.5
        hv -= HRV_ACTIVITY_DROP_PER_MET * max(0, met - 1.0)
        hv -= HRV_SLEEP_DEBT_DROP_PER_HOUR * sleep_debt
        hrv[ep] = max(5.0, hv + rng.normal(0, 3.0))

    hr = np.clip(hr, 35.0, 200.0)

    return pd.DataFrame({
        "time": times,
        "patient_id": patient.patient_id,
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


def simulate_scenario(
    patient: VirtualPatient,
    start_moment: Union[datetime, str, pd.Timestamp],
    scenario: Optional[Union[Scenario, dict]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run 24-hour baseline and counterfactual scenario simulations.

    Parameters
    ----------
    patient : VirtualPatient
        Patient profile with seed.
    start_moment : datetime, str, or pd.Timestamp
        Start moment for the 24-hour evaluation.
    scenario : Scenario or dict, optional
        Counterfactual intervention modifications.

    Returns
    -------
    baseline_df : pd.DataFrame
        24-hour 5-min resolution baseline simulation.
    scenario_df : pd.DataFrame
        24-hour 5-min resolution counterfactual simulation with SAME random seed.
    """
    start_dt = pd.to_datetime(start_moment).floor("5min").to_pydatetime()

    baseline_df = _run_single_24h(patient, start_dt, scenario=None)
    scenario_df = _run_single_24h(patient, start_dt, scenario=scenario)

    return baseline_df, scenario_df


def compare_metrics(baseline_df: pd.DataFrame, scenario_df: pd.DataFrame) -> Dict[str, Any]:
    """Compute comparative clinical glycemic metrics between baseline and scenario."""
    b_glu = baseline_df["libre"]
    s_glu = scenario_df["libre"]

    return {
        "baseline_peak": float(b_glu.max()),
        "scenario_peak": float(s_glu.max()),
        "peak_delta": float(s_glu.max() - b_glu.max()),
        "baseline_time_above_180": float((b_glu > 180.0).mean() * 100.0),
        "scenario_time_above_180": float((s_glu > 180.0).mean() * 100.0),
        "time_above_180_delta": float(((s_glu > 180.0).mean() - (b_glu > 180.0).mean()) * 100.0),
        "baseline_mean": float(b_glu.mean()),
        "scenario_mean": float(s_glu.mean()),
        "mean_delta": float(s_glu.mean() - b_glu.mean()),
    }
