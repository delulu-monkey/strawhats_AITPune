"""
Tests for the virtual patient simulator (Part 1).
==================================================
"""

import sys, os
# Ensure repo root is on the path so `src.sim` resolves.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.sim.profile import VirtualPatient, GeneticMarkers, Lifestyle
from src.sim.simulator import simulate


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def well_controlled() -> VirtualPatient:
    """Healthy / prediabetic with good control."""
    return VirtualPatient(
        name="WellControlled",
        age=40,
        sex="M",
        height_cm=170,
        weight_kg=70,
        hba1c=5.4,
        fasting_glucose=92,
        insulin=8,
        triglycerides=100,
        total_cholesterol=180,
        hdl=55,
        ldl=100,
        diagnoses=[],
        medications=[],
        genetic_markers=GeneticMarkers(genetic_risk_score=30),
        lifestyle=Lifestyle(
            typical_sleep_hours=7.5,
            steps_per_day=8000,
            resting_heart_rate=68,
        ),
        seed=100,
    )


@pytest.fixture
def poorly_controlled() -> VirtualPatient:
    """Uncontrolled T2D with high HbA1c, high BMI, poor sleep."""
    return VirtualPatient(
        name="PoorlyControlled",
        age=58,
        sex="F",
        height_cm=155,
        weight_kg=90,
        hba1c=9.2,
        fasting_glucose=180,
        insulin=25,
        triglycerides=250,
        total_cholesterol=240,
        hdl=35,
        ldl=155,
        diagnoses=["type 2 diabetes", "hypertension"],
        medications=[],
        genetic_markers=GeneticMarkers(genetic_risk_score=80),
        lifestyle=Lifestyle(
            typical_sleep_hours=5.5,
            sleep_variability_hours=1.0,
            steps_per_day=3000,
            resting_heart_rate=82,
        ),
        seed=200,
    )


# ── Determinism ───────────────────────────────────────────────────────────────

def test_determinism(well_controlled):
    """Two runs with the same seed must produce identical DataFrames."""
    df1, sl1 = simulate(well_controlled, days=3)
    df2, sl2 = simulate(well_controlled, days=3)
    pd.testing.assert_frame_equal(df1, df2)
    pd.testing.assert_frame_equal(sl1, sl2)


# ── Valid ranges ──────────────────────────────────────────────────────────────

def test_glucose_range(well_controlled):
    df, _ = simulate(well_controlled, days=5)
    assert df["libre"].min() >= 40, f"glucose too low: {df['libre'].min()}"
    assert df["libre"].max() <= 400, f"glucose too high: {df['libre'].max()}"


def test_hr_range(well_controlled):
    df, _ = simulate(well_controlled, days=5)
    assert df["hr"].min() >= 35, f"HR too low: {df['hr'].min()}"
    assert df["hr"].max() <= 200, f"HR too high: {df['hr'].max()}"


def test_valid_sleep_stages(well_controlled):
    df, _ = simulate(well_controlled, days=5)
    valid = {"awake", "light", "deep", "rem", "none"}
    actual = set(df["sleep_stage"].unique())
    assert actual.issubset(valid), f"unexpected stages: {actual - valid}"


# ── Correct columns ──────────────────────────────────────────────────────────

EXPECTED_COLUMNS = [
    "time", "patient_id", "source", "libre", "hr", "hrv_rmssd",
    "steps", "mets", "act_kcal", "sleep_stage",
    "carbs", "protein", "fat", "fiber", "meal_name",
]


def test_column_names(well_controlled):
    df, _ = simulate(well_controlled, days=1)
    for col in EXPECTED_COLUMNS:
        assert col in df.columns, f"missing column: {col}"


def test_source_column(well_controlled):
    df, _ = simulate(well_controlled, days=1)
    assert (df["source"] == "simulated").all()


# ── Sleep summary columns ────────────────────────────────────────────────────

def test_sleep_summary(well_controlled):
    _, sl = simulate(well_controlled, days=5)
    for col in ["night", "date", "total_sleep_hours", "deep_pct", "rem_pct", "efficiency_pct"]:
        assert col in sl.columns, f"missing sleep summary column: {col}"
    assert len(sl) == 5


# ── Clinical face validity ───────────────────────────────────────────────────

def test_poorly_controlled_higher_glucose(well_controlled, poorly_controlled):
    """A poorly controlled profile must have higher mean glucose."""
    df_good, _ = simulate(well_controlled, days=7)
    df_bad, _ = simulate(poorly_controlled, days=7)
    assert df_bad["libre"].mean() > df_good["libre"].mean(), (
        f"Expected poorly controlled ({df_bad['libre'].mean():.1f}) > "
        f"well controlled ({df_good['libre'].mean():.1f})"
    )


# ── Profile validation ───────────────────────────────────────────────────────

def test_profile_validation_rejects_bad_age():
    p = VirtualPatient(age=0)
    with pytest.raises(ValueError, match="age"):
        p.validate()


def test_profile_round_trip():
    p = VirtualPatient(name="Test", seed=7)
    d = p.to_dict()
    p2 = VirtualPatient.from_dict(d)
    assert p2.name == p.name
    assert p2.seed == p.seed
    assert p2.bmi == p.bmi


# ── Row count ─────────────────────────────────────────────────────────────────

def test_row_count(well_controlled):
    days = 3
    df, _ = simulate(well_controlled, days=days)
    expected = days * 24 * 12  # 5-min epochs
    assert len(df) == expected, f"expected {expected} rows, got {len(df)}"
