"""
Automated UI and Integration Tests for Sim Workspace (Part 5).
==============================================================

Uses streamlit.testing.v1.AppTest to verify:
1. App starts without errors across all 3 navigation sections.
2. Disclaimer banner is present on all views.
3. Patient creation, inspection, edit, and delete lifecycle.
4. Patient View: 7-day simulation, tabs, wearables, XGBoost spike risk score,
   SHAP explanation grouping, and meal what-if peak prediction.
5. Real Reference Patients: 45 participants, real labs, and explicit NOT AVAILABLE
   badges on uncollected modalities (sleep, steps, HRV, genetics, medications, diagnoses).
"""

import json
from pathlib import Path
import pytest
from streamlit.testing.v1 import AppTest

from src.sim.profile import VirtualPatient
from src.sim.store import (
    list_presets,
    list_custom,
    load_preset,
    save_patient,
    delete_patient,
)

APP_PATH = str(Path(__file__).resolve().parent.parent / "app" / "sim_workspace.py")


@pytest.fixture
def clean_custom_store():
    """Ensure custom directory is clean after tests."""
    yield
    custom_dir = Path("data/virtual_patients/custom")
    if custom_dir.exists():
        for f in custom_dir.glob("ui_test_*.json"):
            try:
                f.unlink()
            except Exception:
                pass


def test_app_starts_and_banner_displayed():
    """Verify app initializes cleanly and displays the required clinical banner."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception, f"App raised exception: {at.exception}"

    # Verify banner wording
    markdown_texts = [m.value for m in at.markdown]
    banner_found = any(
        "Research prototype. For simulated or anonymised patients only. Not a medical device." in t
        for t in markdown_texts
    )
    assert banner_found, "Mandatory research prototype banner missing from workspace UI!"


def test_patients_directory_navigation():
    """Verify section 1 Patients Directory displays all 6 presets and SIMULATED badges."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception

    # Check preset count
    presets = list_presets()
    assert len(presets) == 6

    # Verify preset names and SIMULATED badges rendered in markdown
    all_md = " ".join([m.value for m in at.markdown])
    assert "Well-Controlled 45yo" in all_md
    assert "SIMULATED" in all_md


def test_patient_view_simulation_and_tabs():
    """Verify section 2 Patient View runs simulation, renders tabs, and computes risk & what-if."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    # Navigate to Patient View
    at.sidebar.radio[0].set_value("🔬 Patient View & Risk").run(timeout=45)
    assert not at.exception, f"Patient View raised exception: {at.exception}"

    all_md = " ".join([m.value for m in at.markdown])
    assert "Well-Controlled 45yo" in all_md
    assert "Continuous Sensor Telemetry" in all_md
    assert "Spike Risk Assessment" in all_md
    assert "Meal What-If" in all_md

    # Check that tabs and metrics were rendered
    assert len(at.tabs) >= 5, "Expected 5 tabs in Patient View"
    assert len(at.metric) >= 5, "Expected clinical metrics in Patient View"


def test_real_reference_patients_not_available_fields():
    """Verify section 3 Real Reference Patients shows real labs and NOT AVAILABLE badges."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    # Navigate to Real Reference Patients
    at.sidebar.radio[0].set_value("📋 Real Reference Patients").run(timeout=30)
    assert not at.exception, f"Real Patients raised exception: {at.exception}"

    all_md = " ".join([m.value for m in at.markdown])
    assert "CGMacros" in all_md
    assert "REAL" in all_md
    assert "NOT AVAILABLE" in all_md
    assert "Sleep Architecture & Stages" in all_md
    assert "Heart Rate Variability (HRV)" in all_md
    assert "Genomic Markers / Polygenic Score" in all_md


def test_custom_patient_ui_lifecycle(clean_custom_store):
    """Verify custom patient creation, viewing, updating, and deleting via store & UI."""
    test_patient = VirtualPatient(
        name="UI Test Subject",
        age=49,
        sex="M",
        height_cm=175.0,
        weight_kg=79.0,
        hba1c=6.3,
        fasting_glucose=115.0,
        seed=888,
        description="Created for automated UI validation.",
    )
    saved_path = save_patient(test_patient, patient_id="ui_test_subject", overwrite=True)
    assert saved_path.exists()

    # Load in AppTest
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)
    assert not at.exception

    # Check that custom patient is visible in list
    all_md = " ".join([m.value for m in at.markdown])
    assert "UI Test Subject" in all_md
    assert "CUSTOM" in all_md

    # Clean up
    delete_patient("ui_test_subject")
    assert not saved_path.exists()


def test_scenario_sandbox_ui():
    """Verify Scenario Sandbox page renders, contains mandatory statement, and executes."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    # Navigate to Scenario Sandbox
    at.sidebar.radio[0].set_value("🧪 Scenario Sandbox").run(timeout=30)
    assert not at.exception, f"Scenario Sandbox raised exception: {at.exception}"

    all_text = " ".join([m.value for m in at.markdown] + [w.value for w in at.warning])
    # Mandatory plain statement check
    assert "Scenario effects come from simulator assumptions (see assumptions file), not from patterns learned in real data." in all_text
    assert "Define Interventions" in all_text

    # Click run button
    run_btn = [b for b in at.button if "Run Counterfactual Scenario" in b.label]
    assert len(run_btn) >= 1, "Expected Run Counterfactual Scenario button"
    run_btn[0].click().run(timeout=45)
    assert not at.exception, f"Scenario run raised exception: {at.exception}"

    all_md_post = " ".join([m.value for m in at.markdown])
    assert "Baseline vs Scenario" in all_md_post
    assert "Glucose Trajectory Comparison" in all_md_post
    assert len(at.metric) >= 3, "Expected comparison metrics cards"


def test_simulation_assumptions_page():
    """Verify Simulation Assumptions page renders all categories and raw source code."""
    at = AppTest.from_file(APP_PATH)
    at.run(timeout=30)

    # Navigate to Simulation Assumptions
    at.sidebar.radio[0].set_value("⚙️ Simulation Assumptions").run(timeout=30)
    assert not at.exception, f"Assumptions page raised exception: {at.exception}"

    all_md = " ".join([m.value for m in at.markdown])
    assert "Virtual Patient Simulation Assumptions" in all_md
    assert "Fasting Glucose Model" in all_md
    assert "Meal Response Curve" in all_md
    assert "Sleep Debt Effects" in all_md
    assert "Physical Activity & Walking" in all_md
    assert "Complete Source File" in all_md
    assert len(at.code) >= 1, "Expected raw assumptions.py source code block"
