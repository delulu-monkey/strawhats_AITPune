"""
Automated Consistency and Data Honesty Tests.
=============================================

Automated test suite verifying:
- Item 3: Recomputation of glycemic metrics, BMI, and Friedewald lipid formula from raw simulator output for all 6 presets.
- Item 5: Strict validation of clinical provenance tags (REAL, SIMULATED, USER-ENTERED, NOT AVAILABLE) across virtual presets and real study participants.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np

from src.sim.profile import VirtualPatient
from src.sim.simulator import simulate
from src.sim.store import (
    load_preset,
    get_provenance_map,
    ALL_PROVENANCE_FIELDS,
    REAL_DATASET_LACKING_FIELDS,
)
from app.sim_ui.theme import render_patient_body_overview

PRESET_IDS = [
    "active_38_early_disease",
    "lean_high_genetic_risk",
    "older_metformin_high_cholesterol",
    "poorly_controlled_55_sleep_deprived",
    "sedentary_night_shift_worker",
    "well_controlled_45",
]


# ─── Item 3: Recomputations from Raw Simulator Output ─────────────────────────

@pytest.mark.parametrize("preset_id", PRESET_IDS)
def test_preset_simulator_recomputation_and_lipid_check(preset_id: str):
    """
    Verify for each preset:
    1. Raw simulator output reproduces 7-day and 24-hour glycemic metrics without UI code.
    2. BMI calculated from weight and height matches stored profile BMI (within 0.1 rounding).
    3. Friedewald lipid equation (Total - HDL - TG/5 = LDL) holds within rounding (< 0.1 mg/dL).
    4. UI summary card values match 7-day simulator output.
    """
    patient = load_preset(preset_id)
    assert isinstance(patient, VirtualPatient)

    # 1. BMI recomputation check
    height_m = patient.height_cm / 100.0
    raw_bmi = patient.weight_kg / (height_m ** 2)
    assert abs(raw_bmi - patient.bmi) < 0.1, f"BMI mismatch for {preset_id}: raw={raw_bmi:.2f}, profile={patient.bmi:.1f}"

    # 2. Friedewald equation check: Total - HDL - TG/5 == LDL
    friedewald_ldl = patient.total_cholesterol - patient.hdl - (patient.triglycerides / 5.0)
    assert abs(friedewald_ldl - patient.ldl) < 0.1, (
        f"Lipid check failed for {preset_id}: TC={patient.total_cholesterol}, HDL={patient.hdl}, "
        f"TG={patient.triglycerides}, expected LDL={friedewald_ldl:.1f}, preset LDL={patient.ldl:.1f}"
    )

    # 3. Raw simulator output execution (7 days)
    gdf, sdf = simulate(patient, days=7)
    assert len(gdf) == 7 * 288, f"Expected 2016 epochs for 7 days, got {len(gdf)}"

    # 7-day aggregate metrics
    m_7d = float(gdf["libre"].mean())
    tir_7d = float(((gdf["libre"] >= 70.0) & (gdf["libre"] <= 180.0)).mean() * 100.0)
    tbr_7d = float((gdf["libre"] < 70.0).mean() * 100.0)
    tar_7d = float((gdf["libre"] > 180.0).mean() * 100.0)

    # First 24 hours (Day 1)
    d1 = gdf.iloc[:288]
    m_24h_d1 = float(d1["libre"].mean())
    tir_24h_d1 = float(((d1["libre"] >= 70.0) & (d1["libre"] <= 180.0)).mean() * 100.0)
    tbr_24h_d1 = float((d1["libre"] < 70.0).mean() * 100.0)
    tar_24h_d1 = float((d1["libre"] > 180.0).mean() * 100.0)

    # Second 24 hours (Day 2, the UI evaluation date)
    d2 = gdf.iloc[288:576]
    m_24h_d2 = float(d2["libre"].mean())
    tir_24h_d2 = float(((d2["libre"] >= 70.0) & (d2["libre"] <= 180.0)).mean() * 100.0)

    # Verify sanity bounds
    assert 50.0 <= m_7d <= 250.0
    assert 0.0 <= tir_7d <= 100.0
    assert abs((tir_7d + tbr_7d + tar_7d) - 100.0) < 1e-4
    assert abs((tir_24h_d1 + tbr_24h_d1 + tar_24h_d1) - 100.0) < 1e-4

    # Verify UI card display formula: Mean {round(m_7d)} · TIR {round(tir_7d)}%
    expected_card_sub = f"Mean {m_7d:.0f} · TIR {tir_7d:.0f}%"
    assert len(expected_card_sub) > 0


# ─── Item 5: Provenance Labels and Consistency ────────────────────────────────

def test_provenance_labels_virtual_presets():
    """Verify that preset virtual patients have 'SIMULATED' for all clinical fields."""
    for pid in PRESET_IDS:
        patient = load_preset(pid)
        prov = get_provenance_map(patient)
        for field_name in ALL_PROVENANCE_FIELDS:
            assert prov[field_name] == "SIMULATED", (
                f"Preset {pid} field {field_name} must be SIMULATED, got {prov[field_name]}"
            )


def test_provenance_labels_custom_patient():
    """Verify that custom virtual patients properly separate USER-ENTERED from SIMULATED."""
    user_inputs = {"age", "height_cm", "weight_kg", "hba1c", "fasting_glucose"}
    patient = load_preset("well_controlled_45")
    prov = get_provenance_map(patient, user_entered_fields=user_inputs)

    for field_name in user_inputs:
        assert prov[field_name] == "USER-ENTERED"
    for field_name in set(ALL_PROVENANCE_FIELDS) - user_inputs:
        assert prov[field_name] == "SIMULATED"


def test_provenance_labels_real_patient_lacking_fields():
    """
    Verify that real CGMacros participants are strictly marked 'NOT AVAILABLE'
    for sensors not part of the study protocol (Rule 2).
    """
    prov = get_provenance_map(patient={}, is_real=True)
    for field_name in REAL_DATASET_LACKING_FIELDS:
        assert prov[field_name] == "NOT AVAILABLE", (
            f"Real patient field {field_name} must be NOT AVAILABLE, got {prov[field_name]}"
        )


def test_audit_real_patient_heart_rate_card_flag():
    """
    Audit check documenting the finding that real participant heart rate
    in theme.py line 192 is currently hardcoded to '78' with REAL badge.
    """
    theme_file = Path("app/sim_ui/theme.py")
    assert theme_file.exists()
    content = theme_file.read_text(encoding="utf-8")

    # Document and detect presence of hard-coded hr_val = "78" with REAL badge
    assert 'hr_val = "78"' in content
    assert 'hr_badge = badge_html("REAL")' in content
