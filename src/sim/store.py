"""
Virtual patient storage & provenance manager.
=============================================

Manages persistence of virtual patient profiles:
- data/virtual_patients/presets/ (committed, strictly read-only)
- data/virtual_patients/custom/  (gitignored, read/write)

Enforces:
- Schema validation via VirtualPatient dataclass in src/sim/profile.py
- Preservation of deterministic seeds
- Mandatory source="simulated" tag
- Preset read-only protection (PermissionError on modify/overwrite/delete)
- Provenance tracking: 'SIMULATED', 'USER-ENTERED', 'NOT AVAILABLE'
"""

from __future__ import annotations

import copy
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Union

from src.sim.profile import VirtualPatient

# Standard storage directories
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_PRESETS_DIR = REPO_ROOT / "data" / "virtual_patients" / "presets"
DEFAULT_CUSTOM_DIR = REPO_ROOT / "data" / "virtual_patients" / "custom"

# Canonical patient fields tracked for clinical provenance
ALL_PROVENANCE_FIELDS = [
    "name",
    "age",
    "sex",
    "height_cm",
    "weight_kg",
    "bmi",
    "hba1c",
    "fasting_glucose",
    "insulin",
    "triglycerides",
    "total_cholesterol",
    "hdl",
    "ldl",
    "diagnoses",
    "medications",
    "genetic_markers",
    "genetic_risk_score",
    "variant_alleles",
    "typical_sleep_hours",
    "sleep_variability_hours",
    "bedtime_hour",
    "steps_per_day",
    "resting_heart_rate",
    "meal_times",
    "unlogged_snack_prob",
    "sleep_stages",
    "steps",
    "hrv",
    "hrv_rmssd",
    "cgm_glucose",
]

# Fields strictly absent in the real CGMacros free-living dataset (Rule 2)
REAL_DATASET_LACKING_FIELDS = {
    "typical_sleep_hours",
    "sleep_variability_hours",
    "bedtime_hour",
    "sleep_stages",
    "steps",
    "steps_per_day",
    "hrv",
    "hrv_rmssd",
    "genetic_markers",
    "genetic_risk_score",
    "variant_alleles",
    "diagnoses",
    "medications",
}


def _resolve_paths(
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
) -> tuple[Path, Path]:
    c_dir = Path(custom_dir) if custom_dir else DEFAULT_CUSTOM_DIR
    p_dir = Path(presets_dir) if presets_dir else DEFAULT_PRESETS_DIR
    return c_dir, p_dir


def _clean_id(raw_id: str) -> str:
    cleaned = raw_id.strip()
    if cleaned.endswith(".json"):
        cleaned = cleaned[:-5]
    return re.sub(r"[^a-zA-Z0-9_\-]", "_", cleaned)


# ── Listing ──────────────────────────────────────────────────────────────────

def list_presets(presets_dir: Optional[Union[Path, str]] = None) -> List[Dict[str, Any]]:
    """List all read-only preset virtual patients."""
    _, p_dir = _resolve_paths(presets_dir=presets_dir)
    if not p_dir.exists():
        return []

    results = []
    for f in sorted(p_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            patient_id = f.stem
            results.append({
                "id": patient_id,
                "name": data.get("name", patient_id),
                "description": data.get("description", ""),
                "age": data.get("age"),
                "sex": data.get("sex"),
                "hba1c": data.get("hba1c"),
                "bmi": round(data["weight_kg"] / ((data["height_cm"] / 100.0) ** 2), 1)
                if "weight_kg" in data and "height_cm" in data
                else None,
                "seed": data.get("seed"),
                "type": "preset",
                "source": data.get("source", "simulated"),
                "path": str(f),
            })
        except Exception:
            continue
    return results


def list_custom(custom_dir: Optional[Union[Path, str]] = None) -> List[Dict[str, Any]]:
    """List all user-created custom virtual patients."""
    c_dir, _ = _resolve_paths(custom_dir=custom_dir)
    if not c_dir.exists():
        return []

    results = []
    for f in sorted(c_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            patient_id = f.stem
            results.append({
                "id": patient_id,
                "name": data.get("name", patient_id),
                "description": data.get("description", ""),
                "age": data.get("age"),
                "sex": data.get("sex"),
                "hba1c": data.get("hba1c"),
                "bmi": round(data["weight_kg"] / ((data["height_cm"] / 100.0) ** 2), 1)
                if "weight_kg" in data and "height_cm" in data
                else None,
                "seed": data.get("seed"),
                "type": "custom",
                "source": data.get("source", "simulated"),
                "path": str(f),
            })
        except Exception:
            continue
    return results


def list_patients(
    include_presets: bool = True,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
) -> List[Dict[str, Any]]:
    """List both custom patients and presets (if include_presets=True)."""
    customs = list_custom(custom_dir=custom_dir)
    if not include_presets:
        return customs
    presets = list_presets(presets_dir=presets_dir)
    return presets + customs


# ── Loading ──────────────────────────────────────────────────────────────────

def load_preset(
    preset_id: str,
    presets_dir: Optional[Union[Path, str]] = None,
) -> VirtualPatient:
    """Load a validated preset VirtualPatient by ID."""
    _, p_dir = _resolve_paths(presets_dir=presets_dir)
    cleaned_id = _clean_id(preset_id)
    preset_file = p_dir / f"{cleaned_id}.json"

    if not preset_file.exists():
        raise FileNotFoundError(f"Preset virtual patient '{cleaned_id}' not found at {preset_file}")

    with open(preset_file, "r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in preset '{cleaned_id}': {e}") from e

    try:
        patient = VirtualPatient.from_dict(data)
    except Exception as e:
        raise ValueError(f"Validation failed for preset '{cleaned_id}': {e}") from e

    return patient


def load_custom(
    patient_id: str,
    custom_dir: Optional[Union[Path, str]] = None,
) -> VirtualPatient:
    """Load a validated custom VirtualPatient by ID."""
    c_dir, _ = _resolve_paths(custom_dir=custom_dir)
    cleaned_id = _clean_id(patient_id)
    custom_file = c_dir / f"{cleaned_id}.json"

    if not custom_file.exists():
        raise FileNotFoundError(f"Custom virtual patient '{cleaned_id}' not found at {custom_file}")

    with open(custom_file, "r", encoding="utf-8") as fp:
        try:
            data = json.load(fp)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed JSON in custom patient '{cleaned_id}': {e}") from e

    try:
        patient = VirtualPatient.from_dict(data)
    except Exception as e:
        raise ValueError(f"Validation failed for custom patient '{cleaned_id}': {e}") from e

    return patient


def load_patient(
    patient_id: str,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
) -> VirtualPatient:
    """
    Load a VirtualPatient from custom storage first, then presets.
    Raises FileNotFoundError if not found in either.
    """
    c_dir, p_dir = _resolve_paths(custom_dir=custom_dir, presets_dir=presets_dir)
    cleaned_id = _clean_id(patient_id)

    # Check custom first
    if (c_dir / f"{cleaned_id}.json").exists():
        return load_custom(cleaned_id, custom_dir=c_dir)

    # Check presets
    if (p_dir / f"{cleaned_id}.json").exists():
        return load_preset(cleaned_id, presets_dir=p_dir)

    raise FileNotFoundError(
        f"Virtual patient '{cleaned_id}' not found in custom ({c_dir}) or preset ({p_dir}) stores."
    )


def load_patient_dict(
    patient_id: str,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
) -> Dict[str, Any]:
    """Load the raw JSON dictionary (including provenance, description, etc.)."""
    c_dir, p_dir = _resolve_paths(custom_dir=custom_dir, presets_dir=presets_dir)
    cleaned_id = _clean_id(patient_id)

    target_file = None
    if (c_dir / f"{cleaned_id}.json").exists():
        target_file = c_dir / f"{cleaned_id}.json"
    elif (p_dir / f"{cleaned_id}.json").exists():
        target_file = p_dir / f"{cleaned_id}.json"

    if target_file is None:
        raise FileNotFoundError(f"Virtual patient '{cleaned_id}' not found.")

    with open(target_file, "r", encoding="utf-8") as fp:
        return json.load(fp)


# ── Saving & Modifying ────────────────────────────────────────────────────────

def save_patient(
    patient: Union[VirtualPatient, dict],
    patient_id: Optional[str] = None,
    description: str = "",
    overwrite: bool = False,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
    provenance: Optional[Dict[str, str]] = None,
    user_entered_fields: Optional[Iterable[str]] = None,
) -> Path:
    """
    Save a virtual patient as a JSON file in data/virtual_patients/custom/.

    Guarantees:
    - Strictly preserves patient seed.
    - Presets cannot be overwritten (PermissionError).
    - Source is always 'simulated'.
    - Validates against VirtualPatient dataclass, returning clear error messages.
    """
    c_dir, p_dir = _resolve_paths(custom_dir=custom_dir, presets_dir=presets_dir)
    c_dir.mkdir(parents=True, exist_ok=True)

    # Convert to dict or validate VirtualPatient
    if isinstance(patient, dict):
        d = copy.deepcopy(patient)
        if "source" in d and d["source"] != "simulated":
            raise ValueError(f"Cannot save patient; validation error: source must be 'simulated'; got {d['source']!r}")
        d.setdefault("source", "simulated")
        if description and not d.get("description"):
            d["description"] = description
        try:
            vp = VirtualPatient.from_dict(d)
        except Exception as e:
            raise ValueError(f"Cannot save patient; validation error: {e}") from e
    elif isinstance(patient, VirtualPatient):
        vp = patient
        if vp.source != "simulated":
            raise ValueError(f"Cannot save patient; validation error: source must be 'simulated'; got {vp.source!r}")
        if description:
            vp.description = description
        try:
            vp.validate()
        except Exception as e:
            raise ValueError(f"Cannot save patient; validation error: {e}") from e
    else:
        raise TypeError(f"patient must be a VirtualPatient or dict; got {type(patient)}")

    if patient_id is None:
        target_id = _clean_id(vp.patient_id.lower())
    else:
        target_id = _clean_id(patient_id)

    # PRESET READ-ONLY GUARD
    # 1. Direct ID / stem match
    if (p_dir / f"{target_id}.json").exists():
        raise PermissionError(
            f"Preset virtual patient '{target_id}' is read-only and cannot be overwritten."
        )
    # 2. Check if target_id or patient name matches any existing preset file or preset name
    for pf in p_dir.glob("*.json"):
        if pf.stem.lower() == target_id.lower():
            raise PermissionError(
                f"Preset virtual patient '{target_id}' is read-only and cannot be overwritten."
            )
        try:
            with open(pf, "r", encoding="utf-8") as fp:
                preset_data = json.load(fp)
        except Exception:
            continue

        p_name = preset_data.get("name", "").strip().lower()
        if p_name and p_name == vp.name.strip().lower():
            raise PermissionError(
                f"Preset virtual patient '{vp.name}' is read-only and cannot be overwritten."
            )

    target_file = c_dir / f"{target_id}.json"
    if target_file.exists() and not overwrite:
        raise FileExistsError(
            f"Custom patient '{target_id}' already exists at {target_file}. "
            f"Pass overwrite=True to update."
        )

    # Build final payload
    payload = vp.to_dict()
    payload["source"] = "simulated"
    if vp.description:
        payload["description"] = vp.description
    elif description:
        payload["description"] = description

    # Attach provenance mapping
    prov_map = get_provenance_map(
        payload,
        user_entered_fields=user_entered_fields,
        is_real=False,
    )
    if provenance:
        prov_map.update(provenance)
    payload["provenance"] = prov_map

    with open(target_file, "w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)

    return target_file


def update_patient(
    patient_id: str,
    updates: Union[dict, VirtualPatient],
    description: Optional[str] = None,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
    provenance: Optional[Dict[str, str]] = None,
    user_entered_fields: Optional[Iterable[str]] = None,
) -> VirtualPatient:
    """
    Update an existing custom virtual patient.
    Raises PermissionError if patient_id refers to a preset.
    """
    c_dir, p_dir = _resolve_paths(custom_dir=custom_dir, presets_dir=presets_dir)
    cleaned_id = _clean_id(patient_id)

    # PRESET READ-ONLY GUARD
    if (p_dir / f"{cleaned_id}.json").exists():
        raise PermissionError(
            f"Preset virtual patient '{cleaned_id}' is read-only and cannot be updated."
        )

    existing_file = c_dir / f"{cleaned_id}.json"
    if not existing_file.exists():
        raise FileNotFoundError(f"Custom patient '{cleaned_id}' not found at {existing_file}")

    with open(existing_file, "r", encoding="utf-8") as fp:
        current_data = json.load(fp)

    if isinstance(updates, VirtualPatient):
        new_data = updates.to_dict()
    elif isinstance(updates, dict):
        new_data = copy.deepcopy(current_data)
        # Deep merge updates
        for k, v in updates.items():
            if isinstance(v, dict) and k in new_data and isinstance(new_data[k], dict):
                new_data[k].update(v)
            else:
                new_data[k] = v
    else:
        raise TypeError(f"updates must be dict or VirtualPatient; got {type(updates)}")

    if description is not None:
        new_data["description"] = description
    new_data["source"] = "simulated"

    # Seed preservation: keep current seed unless explicitly altered in updates
    if "seed" not in updates if isinstance(updates, dict) else False:
        new_data["seed"] = current_data.get("seed", 42)

    # Validate
    try:
        updated_patient = VirtualPatient.from_dict(new_data)
    except Exception as e:
        raise ValueError(f"Update failed for patient '{cleaned_id}': {e}") from e

    save_patient(
        updated_patient,
        patient_id=cleaned_id,
        description=new_data.get("description", ""),
        overwrite=True,
        custom_dir=c_dir,
        presets_dir=p_dir,
        provenance=provenance,
        user_entered_fields=user_entered_fields,
    )
    return updated_patient


def delete_patient(
    patient_id: str,
    custom_dir: Optional[Union[Path, str]] = None,
    presets_dir: Optional[Union[Path, str]] = None,
) -> bool:
    """
    Delete a custom virtual patient.
    Raises PermissionError if patient_id refers to a preset.
    """
    c_dir, p_dir = _resolve_paths(custom_dir=custom_dir, presets_dir=presets_dir)
    cleaned_id = _clean_id(patient_id)

    # PRESET READ-ONLY GUARD
    if (p_dir / f"{cleaned_id}.json").exists():
        raise PermissionError(
            f"Preset virtual patient '{cleaned_id}' is read-only and cannot be deleted."
        )

    target_file = c_dir / f"{cleaned_id}.json"
    if not target_file.exists():
        raise FileNotFoundError(f"Custom patient '{cleaned_id}' not found at {target_file}")

    target_file.unlink()
    return True


# ── Provenance Helper ────────────────────────────────────────────────────────

def get_provenance_map(
    patient: Union[VirtualPatient, dict],
    user_entered_fields: Optional[Iterable[str]] = None,
    is_real: bool = False,
) -> Dict[str, str]:
    """
    Return a clinical provenance dictionary for all canonical fields.
    Each field is mapped to exactly one of:
    - 'SIMULATED'
    - 'USER-ENTERED'
    - 'NOT AVAILABLE'

    Honesty Rules:
    - Real CGMacros participants: missing fields (sleep stages, steps, HRV,
      genetics, diagnoses, medications) are strictly marked 'NOT AVAILABLE'.
    - Virtual / simulated patients: explicitly provided doctor inputs are
      marked 'USER-ENTERED', while synthetic/inferred/modelled inputs are 'SIMULATED'.
    - Preset personas (no doctor inputs): all fields are 'SIMULATED'.
    """
    user_set = set(user_entered_fields or [])

    # If patient is dict and contains stored provenance, check for existing tags
    stored_prov = {}
    if isinstance(patient, dict) and "provenance" in patient and isinstance(patient["provenance"], dict):
        stored_prov = patient["provenance"]

    prov: Dict[str, str] = {}

    for f in ALL_PROVENANCE_FIELDS:
        if is_real:
            # Rule 2: real participants lack these sensors/fields
            if f in REAL_DATASET_LACKING_FIELDS:
                prov[f] = "NOT AVAILABLE"
            else:
                prov[f] = "USER-ENTERED" if f in user_set else "USER-ENTERED"
        else:
            # Virtual / simulated patient
            if f in stored_prov:
                prov[f] = stored_prov[f]
            elif f in user_set:
                prov[f] = "USER-ENTERED"
            else:
                prov[f] = "SIMULATED"

    return prov


# Alias for intuitive importing
get_provenance = get_provenance_map
