"""
Tests for counterfactual scenario sandbox (Part 6).
===================================================

Verifies:
1. Same seed gives identical baseline and identical scenario when unchanged.
2. A high-carbohydrate meal raises peak glucose.
3. Adding a walk lowers glucose excursion.
4. Shorter sleep duration raises mean glucose the next morning.
"""

from datetime import datetime, timedelta
import numpy as np
import pytest

from src.sim.store import load_preset
from src.sim.scenarios import simulate_scenario, compare_metrics, Scenario


@pytest.fixture
def test_patient():
    return load_preset("well_controlled_45")


def test_same_seed_gives_identical_baseline(test_patient):
    """Running simulation twice with same seed produces bitwise identical traces."""
    start_dt = datetime(2025, 1, 1, 8, 0)

    b1, s1 = simulate_scenario(test_patient, start_dt, scenario=None)
    b2, s2 = simulate_scenario(test_patient, start_dt, scenario=Scenario())

    assert len(b1) == 288
    assert len(s1) == 288
    assert np.allclose(b1["libre"], b2["libre"]), "Baselines with same seed must be identical"
    assert np.allclose(b1["libre"], s1["libre"]), "Empty scenario must match baseline"
    assert np.allclose(b1["hr"], b2["hr"])
    assert np.allclose(b1["steps"], b2["steps"])


def test_high_carb_meal_raises_peak_glucose(test_patient):
    """Adding a high-carbohydrate meal raises peak glucose in the next 24 hours."""
    start_dt = datetime(2025, 1, 1, 8, 0)
    meal_time = start_dt + timedelta(hours=2)

    scenario = {
        "added_meal": {
            "dish": "Boiled rice (plate)",
            "portions": 2.0,
            "time": meal_time,
        }
    }

    baseline_df, scenario_df = simulate_scenario(test_patient, start_dt, scenario)
    metrics = compare_metrics(baseline_df, scenario_df)

    assert scenario_df["libre"].max() > baseline_df["libre"].max()
    assert metrics["peak_delta"] > 15.0, f"Expected significant peak rise, got {metrics['peak_delta']} mg/dL"

    # Verify meal appears in scenario dataframe
    meal_rows = scenario_df[scenario_df["carbs"] > 50.0]
    assert not meal_rows.empty


def test_walk_lowers_glucose(test_patient):
    """Adding a brisk walk lowers glucose in the post-walk window."""
    start_dt = datetime(2025, 1, 1, 8, 0)
    walk_time = start_dt + timedelta(hours=3)

    scenario = {
        "added_walk": {
            "time": walk_time,
            "duration_minutes": 45,
            "steps_per_min": 120,
        }
    }

    baseline_df, scenario_df = simulate_scenario(test_patient, start_dt, scenario)

    # During and immediately after the walk
    walk_start = walk_time
    walk_end = walk_start + timedelta(minutes=60)
    mask = (baseline_df["time"] >= walk_start) & (baseline_df["time"] <= walk_end)

    b_mean = baseline_df.loc[mask, "libre"].mean()
    s_mean = scenario_df.loc[mask, "libre"].mean()

    assert s_mean < b_mean, f"Walk should lower glucose (baseline={b_mean:.1f}, scenario={s_mean:.1f})"
    assert scenario_df.loc[mask, "steps"].sum() > baseline_df.loc[mask, "steps"].sum()


def test_shorter_sleep_raises_morning_glucose(test_patient):
    """Restricting sleep to 4 hours raises next-morning glucose due to sleep debt."""
    start_dt = datetime(2025, 1, 1, 8, 0)

    # 4 hours sleep vs default 7.5 hours
    baseline_df, scenario_df = simulate_scenario(
        test_patient,
        start_dt,
        scenario={"sleep_hours": 4.0},
    )

    # Check morning hours (06:00 to 10:00)
    morning_mask = (baseline_df["time"].dt.hour >= 6) & (baseline_df["time"].dt.hour <= 10)

    b_morning_mean = baseline_df.loc[morning_mask, "libre"].mean()
    s_morning_mean = scenario_df.loc[morning_mask, "libre"].mean()

    assert s_morning_mean > b_morning_mean, (
        f"Sleep debt must elevate morning glucose (baseline={b_morning_mean:.1f}, scenario={s_morning_mean:.1f})"
    )
