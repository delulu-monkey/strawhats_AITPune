"""
Tests for simulator calibration and fidelity pipeline (Part 2).
==============================================================
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from src.sim.calibrate import compute_real_targets, generate_cohort, simulate_cohort_statistics


def test_real_targets_structure():
    """Real targets must contain all three groups and no NaN statistics."""
    df = compute_real_targets()
    assert len(df) == 3
    assert set(df["group"]) == {"healthy", "prediabetes", "t2d"}
    for col in ["mean_glucose", "pct_above_140", "pct_above_180", "meal_rise", "overnight_mean", "overnight_std", "mean_hr"]:
        assert col in df.columns
        assert not df[col].isna().any(), f"NaN found in column {col}"


def test_generate_cohort():
    """Cohorts must be valid VirtualPatients with monotonically increasing mean HbA1c."""
    cohort_h = generate_cohort("healthy", n=5, seed=1)
    cohort_p = generate_cohort("prediabetes", n=5, seed=2)
    cohort_t = generate_cohort("t2d", n=5, seed=3)

    assert len(cohort_h) == 5
    assert len(cohort_p) == 5
    assert len(cohort_t) == 5

    for p in cohort_h + cohort_p + cohort_t:
        p.validate()

    mean_a1c_h = np.mean([p.hba1c for p in cohort_h])
    mean_a1c_p = np.mean([p.hba1c for p in cohort_p])
    mean_a1c_t = np.mean([p.hba1c for p in cohort_t])

    assert mean_a1c_h < mean_a1c_p < mean_a1c_t


def test_simulate_cohort_statistics_fast():
    """Fast simulation check (2 patients per group, 2 days)."""
    cohorts = {
        "healthy": generate_cohort("healthy", n=2, seed=10),
        "prediabetes": generate_cohort("prediabetes", n=2, seed=20),
        "t2d": generate_cohort("t2d", n=2, seed=30),
    }
    stats = simulate_cohort_statistics(cohorts, days=2)
    assert len(stats) == 3
    assert (stats["mean_glucose"] > 60).all()
    assert (stats["mean_glucose"] < 250).all()
    # T2D mean glucose should exceed healthy mean glucose
    h_glu = stats.loc[stats["group"] == "healthy", "mean_glucose"].values[0]
    t_glu = stats.loc[stats["group"] == "t2d", "mean_glucose"].values[0]
    assert t_glu > h_glu
