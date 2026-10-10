"""
Tests for featurizer parity with real pipeline (Part 3).
========================================================
"""

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
import pandas as pd
import pytest

from src.features import build, CAPS
from src.sim.featurize import build_features, featurize_patient
from src.sim.profile import VirtualPatient
from src.sim.simulator import simulate


def test_featurizer_parity_with_real_build():
    """
    Takes one real participant's 5-minute data, runs both the real pipeline
    build() and the new featurizer build_features(), and asserts the shared
    features are numerically identical.
    """
    cgm = pd.read_csv("data/processed/cgmacros_all.csv.gz", parse_dates=["time"], nrows=25000)
    for col, cap in CAPS.items():
        cgm[col] = cgm[col].clip(upper=cap)

    subj = cgm["subject"].unique()[0]
    g = cgm[cgm["subject"] == subj].copy()

    # Resample to 5-minute resolution
    g_5m = g.set_index("time").resample("5min").first().dropna(how="all").reset_index()

    f_real = build(g_5m)
    f_sim = build_features(g_5m)

    # Shared features
    shared = [c for c in f_real.columns if c in f_sim.columns]
    assert len(shared) == 18, f"Expected 18 shared features, got {len(shared)}: {shared}"

    pd.testing.assert_frame_equal(f_real[shared], f_sim[shared], check_dtype=False, atol=1e-7)


def test_simulated_patient_featurization():
    """Verify that simulated patient DataFrame can be scored by existing xgb_spike_model."""
    import joblib
    model_dict = joblib.load("models/xgb_spike_model.pkl")
    features_needed = model_dict["features"]

    p = VirtualPatient(name="TestPatient", seed=42)
    df, sl = simulate(p, days=3)

    feat_df = featurize_patient(df, profile=p, sleep_summary=sl, include_twin_features=True)

    for feat in features_needed:
        assert feat in feat_df.columns, f"Missing feature needed by spike model: {feat}"

    # Drop NaNs that naturally occur in rolling history windows
    ready = feat_df[features_needed].dropna()
    assert len(ready) > 0

    probs = model_dict["model"].predict_proba(ready)[:, 1]
    assert (probs >= 0.0).all() and (probs <= 1.0).all()
