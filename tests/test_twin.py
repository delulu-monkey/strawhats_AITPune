"""
Tests for cohort generator and twin model pipeline (Part 3).
============================================================
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import joblib
import numpy as np
import pandas as pd
import pytest

from src.sim.cohort import generate_cohort_profiles
from src.sim.train_twin import ALL_TWIN_FEATURES, SHARED_FEATURES, TWIN_EXTRA_FEATURES


def test_generate_cohort_profiles():
    """Verify that cohort generator produces valid profiles within requested bounds."""
    profiles = generate_cohort_profiles(n_patients=15, seed=123)
    assert len(profiles) == 15

    for p in profiles:
        p.validate()
        assert 30 <= p.age <= 75
        assert 5.0 <= p.hba1c <= 10.0
        assert 10.0 <= p.genetic_markers.genetic_risk_score <= 100.0
        assert 1000 <= p.lifestyle.steps_per_day <= 20000
        assert 0.0 <= p.lifestyle.bedtime_hour < 24.0


def test_twin_model_file():
    """Verify models/twin_model.pkl structure and scoring."""
    assert os.path.exists("models/twin_model.pkl"), "models/twin_model.pkl does not exist"
    model_dict = joblib.load("models/twin_model.pkl")
    assert "model" in model_dict
    assert "features" in model_dict
    assert model_dict["features"] == ALL_TWIN_FEATURES
    assert len(model_dict["features"]) == 27

    # Create dummy sample row
    dummy = pd.DataFrame([{f: 1.0 for f in ALL_TWIN_FEATURES}])
    dummy["glu_now"] = 110.0
    dummy["hba1c"] = 6.5
    dummy["hour_sin"] = 0.5
    dummy["hour_cos"] = 0.5

    prob = model_dict["model"].predict_proba(dummy)[:, 1]
    assert 0.0 <= prob[0] <= 1.0
