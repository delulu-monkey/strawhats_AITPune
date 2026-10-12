"""
Tests for virtual patient storage and provenance (Part 4).
==========================================================

Covers:
1. Preset persona verification (all 6 exist, validate, labelled simulated, one-line desc).
2. Preset simulation execution without errors (simulate() runs cleanly on each).
3. Preset read-only protection (PermissionError on save, overwrite, update, delete).
4. Custom patient CRUD lifecycle & round-trips with seed preservation.
5. Strict validation failures with clear error messages.
6. Clinical provenance mapping (SIMULATED, USER-ENTERED, NOT AVAILABLE).
"""

import copy
import json
from pathlib import Path
import pytest

from src.sim.profile import VirtualPatient, GeneticMarkers, Lifestyle
from src.sim.simulator import simulate
from src.sim.store import (
    list_presets,
    list_custom,
    list_patients,
    load_preset,
    load_custom,
    load_patient,
    load_patient_dict,
    save_patient,
    update_patient,
    delete_patient,
    get_provenance_map,
    ALL_PROVENANCE_FIELDS,
    REAL_DATASET_LACKING_FIELDS,
)


# ── 1. Presets Inspection & Integrity ────────────────────────────────────────

def test_presets_inventory():
    """Verify all 6 preset personas exist and have complete valid fields."""
    presets = list_presets()
    assert len(presets) == 6, f"Expected 6 presets, found {len(presets)}"

    expected_preset_ids = {
        "well_controlled_45",
        "poorly_controlled_55_sleep_deprived",
        "sedentary_night_shift_worker",
        "active_38_early_disease",
        "older_metformin_high_cholesterol",
        "lean_high_genetic_risk",
    }
    found_ids = {p["id"] for p in presets}
    assert expected_preset_ids.issubset(found_ids)

    for p_info in presets:
        pid = p_info["id"]
        # Load as VirtualPatient
        patient = load_preset(pid)
        assert isinstance(patient, VirtualPatient)
        patient.validate()

        # Check required metadata
        assert patient.source == "simulated"
        assert len(patient.description) > 0
        assert "\n" not in patient.description, f"Description for {pid} must be one-line"
        assert isinstance(patient.seed, int)
        assert 0 < patient.age <= 120
        assert patient.sex in ("M", "F")
        assert 3.0 <= patient.hba1c <= 20.0
        assert 10.0 <= patient.bmi <= 80.0


def test_presets_run_through_simulator():
    """Verify that all 6 presets run through simulate() without errors."""
    presets = list_presets()
    for p_info in presets:
        patient = load_preset(p_info["id"])
        # Simulate 1 day (288 5-min epochs)
        gdf, sdf = simulate(patient, days=1)
        assert not gdf.empty, f"Glucose DF empty for preset {patient.name}"
        assert len(gdf) == 288, f"Expected 288 epochs for 1 day, got {len(gdf)}"
        assert not sdf.empty, f"Sleep DF empty for preset {patient.name}"
        assert "libre" in gdf.columns
        assert "hr" in gdf.columns
        assert "hrv_rmssd" in gdf.columns
        assert "steps" in gdf.columns
        assert "sleep_stage" in gdf.columns


# ── 2. Preset Read-Only Protection ───────────────────────────────────────────

def test_preset_read_only_protection(tmp_path):
    """Presets must never be overwritten, updated, or deleted."""
    preset = load_preset("well_controlled_45")

    # 1. Overwriting preset via save_patient
    with pytest.raises(PermissionError, match="read-only"):
        save_patient(preset, overwrite=True)

    with pytest.raises(PermissionError, match="read-only"):
        save_patient(preset, patient_id="well_controlled_45", overwrite=True)

    # 2. Updating preset via update_patient
    with pytest.raises(PermissionError, match="read-only"):
        update_patient("well_controlled_45", {"age": 50})

    # 3. Deleting preset via delete_patient
    with pytest.raises(PermissionError, match="read-only"):
        delete_patient("well_controlled_45")


# ── 3. Custom Storage Lifecycle & Round-Trips ────────────────────────────────

def test_custom_patient_crud_roundtrip(tmp_path):
    """Test full CRUD lifecycle in custom store with seed preservation."""
    custom_dir = tmp_path / "custom"
    presets_dir = tmp_path / "presets"
    custom_dir.mkdir()
    presets_dir.mkdir()

    # Create a virtual patient
    p = VirtualPatient(
        name="Elena Rostova",
        age=52,
        sex="F",
        height_cm=165.0,
        weight_kg=72.0,
        hba1c=6.8,
        fasting_glucose=122.0,
        insulin=14.0,
        triglycerides=160.0,
        total_cholesterol=210.0,
        hdl=48.0,
        ldl=130.0,
        diagnoses=["Prediabetes", "Mild Dyslipidemia"],
        medications=[],
        seed=1337,
        description="A 52-year-old female with prediabetes and evening walks.",
    )

    # 1. Save
    saved_path = save_patient(
        p,
        custom_dir=custom_dir,
        presets_dir=presets_dir,
        user_entered_fields=["age", "sex", "hba1c", "height_cm", "weight_kg"],
    )
    assert saved_path.exists()
    assert saved_path.suffix == ".json"

    # 2. List
    custom_list = list_custom(custom_dir=custom_dir)
    assert len(custom_list) == 1
    assert custom_list[0]["id"] == "elena_rostova"
    assert custom_list[0]["name"] == "Elena Rostova"
    assert custom_list[0]["source"] == "simulated"
    assert custom_list[0]["seed"] == 1337

    # 3. Load & verify exact round-trip fidelity
    loaded = load_custom("elena_rostova", custom_dir=custom_dir)
    assert loaded.name == p.name
    assert loaded.age == p.age
    assert loaded.sex == p.sex
    assert loaded.height_cm == p.height_cm
    assert loaded.weight_kg == p.weight_kg
    assert loaded.bmi == p.bmi
    assert loaded.hba1c == p.hba1c
    assert loaded.seed == 1337
    assert loaded.source == "simulated"
    assert loaded.description == p.description
    assert loaded.diagnoses == p.diagnoses

    # 4. Check raw dict and provenance
    raw_dict = load_patient_dict("elena_rostova", custom_dir=custom_dir)
    assert raw_dict["source"] == "simulated"
    assert "provenance" in raw_dict
    assert raw_dict["provenance"]["age"] == "USER-ENTERED"
    assert raw_dict["provenance"]["hba1c"] == "USER-ENTERED"
    assert raw_dict["provenance"]["steps_per_day"] == "SIMULATED"

    # 5. Prevent accidental overwrite without overwrite=True
    with pytest.raises(FileExistsError):
        save_patient(p, custom_dir=custom_dir, presets_dir=presets_dir, overwrite=False)

    # 6. Update patient
    updated = update_patient(
        "elena_rostova",
        {"weight_kg": 70.0, "hba1c": 6.5},
        description="Updated weight and HbA1c after 3 months lifestyle change.",
        custom_dir=custom_dir,
        presets_dir=presets_dir,
    )
    assert updated.weight_kg == 70.0
    assert updated.hba1c == 6.5
    assert updated.seed == 1337  # seed strictly preserved!
    assert updated.description == "Updated weight and HbA1c after 3 months lifestyle change."

    reloaded = load_custom("elena_rostova", custom_dir=custom_dir)
    assert reloaded.weight_kg == 70.0
    assert reloaded.hba1c == 6.5
    assert reloaded.seed == 1337

    # 7. Delete patient
    res = delete_patient("elena_rostova", custom_dir=custom_dir, presets_dir=presets_dir)
    assert res is True
    assert len(list_custom(custom_dir=custom_dir)) == 0

    with pytest.raises(FileNotFoundError):
        load_custom("elena_rostova", custom_dir=custom_dir)


# ── 4. Validation Failures ───────────────────────────────────────────────────

def test_validation_failures(tmp_path):
    """Store must reject invalid profiles with clear error messages."""
    custom_dir = tmp_path / "custom"
    presets_dir = tmp_path / "presets"
    custom_dir.mkdir()
    presets_dir.mkdir()

    base_dict = {
        "name": "Invalid Patient",
        "age": 45,
        "sex": "M",
        "height_cm": 170.0,
        "weight_kg": 75.0,
        "hba1c": 5.7,
        "fasting_glucose": 100.0,
        "source": "simulated",
        "seed": 42,
    }

    # 1. Invalid age
    d = copy.deepcopy(base_dict)
    d["age"] = 150
    with pytest.raises(ValueError, match="age must be 1–120"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)

    # 2. Invalid sex
    d = copy.deepcopy(base_dict)
    d["sex"] = "NonBinary"
    with pytest.raises(ValueError, match="sex must be 'M' or 'F'"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)

    # 3. Invalid HbA1c
    d = copy.deepcopy(base_dict)
    d["hba1c"] = 25.0
    with pytest.raises(ValueError, match="hba1c must be 3.0–20.0"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)

    # 4. Invalid source (Honesty rule: must be simulated)
    d = copy.deepcopy(base_dict)
    d["source"] = "real"
    with pytest.raises(ValueError, match="source must be 'simulated'"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)

    # 5. Invalid lifestyle sleep hours
    d = copy.deepcopy(base_dict)
    d["lifestyle"] = {"typical_sleep_hours": 1.5}
    with pytest.raises(ValueError, match="typical_sleep_hours must be 3–12"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)

    # 6. Invalid genetic risk score
    d = copy.deepcopy(base_dict)
    d["genetic_markers"] = {"genetic_risk_score": 150.0}
    with pytest.raises(ValueError, match="genetic_risk_score must be 0–100"):
        save_patient(d, custom_dir=custom_dir, presets_dir=presets_dir)


# ── 5. Provenance Mapping ────────────────────────────────────────────────────

def test_provenance_mapping():
    """Verify clinical provenance helper mappings."""
    p = load_preset("well_controlled_45")

    # 1. Preset persona: all fields must be 'SIMULATED'
    prov_sim = get_provenance_map(p)
    assert set(prov_sim.keys()) == set(ALL_PROVENANCE_FIELDS)
    assert all(val == "SIMULATED" for val in prov_sim.values())

    # 2. Custom patient with doctor entered inputs
    doctor_fields = ["age", "sex", "height_cm", "weight_kg", "hba1c", "fasting_glucose", "diagnoses"]
    prov_custom = get_provenance_map(p, user_entered_fields=doctor_fields)
    for f in doctor_fields:
        assert prov_custom[f] == "USER-ENTERED"
    # Inferred / unmeasured fields remain SIMULATED
    assert prov_custom["typical_sleep_hours"] == "SIMULATED"
    assert prov_custom["genetic_risk_score"] == "SIMULATED"
    assert prov_custom["steps_per_day"] == "SIMULATED"

    # 3. Real participant: missing fields must be 'NOT AVAILABLE'
    prov_real = get_provenance_map(p, is_real=True)
    for f in REAL_DATASET_LACKING_FIELDS:
        assert prov_real[f] == "NOT AVAILABLE", f"Field {f} must be NOT AVAILABLE for real data"
