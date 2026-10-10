"""
VirtualPatient profile dataclass.
=================================

Holds demographics, labs, diagnoses, medications, genetic markers,
lifestyle details, and a seed for deterministic simulation.
"""

from __future__ import annotations

import copy
import math
from dataclasses import dataclass, field, asdict, fields
from typing import Dict, List, Optional

from src.sim.assumptions import (
    T2D_VARIANTS,
    UNLOGGED_SNACK_PROB_PER_EPOCH,
    DEFAULT_MEAL_TIMES,
    FASTING_GLUCOSE_INTERCEPT,
    FASTING_GLUCOSE_HBA1C_SLOPE,
    FASTING_GLUCOSE_IR_ADDER_PER_UNIT,
    IR_HBA1C_FACTOR_PER_PCT,
    IR_BMI_FACTOR_PER_UNIT,
    GENETIC_IR_MAX_BOOST,
    METFORMIN_FASTING_REDUCTION,
)


# ── Genetic markers ──────────────────────────────────────────────────────────

@dataclass
class GeneticMarkers:
    """Illustrative T2D-associated variant allele counts and a risk score."""

    # Risk-allele counts (0 / 1 / 2) keyed by variant name from assumptions.
    variant_alleles: Dict[str, int] = field(default_factory=lambda: {v: 0 for v in T2D_VARIANTS})

    # Composite genetic risk score, 0 (low) to 100 (high).
    genetic_risk_score: float = 50.0

    def validate(self) -> None:
        for v, count in self.variant_alleles.items():
            if count not in (0, 1, 2):
                raise ValueError(f"Variant {v} allele count must be 0, 1, or 2; got {count}")
        if not 0 <= self.genetic_risk_score <= 100:
            raise ValueError(f"genetic_risk_score must be 0–100; got {self.genetic_risk_score}")


# ── Lifestyle ────────────────────────────────────────────────────────────────

@dataclass
class Lifestyle:
    """Day-to-day behavioural and lifestyle parameters."""

    typical_sleep_hours: float = 7.0
    sleep_variability_hours: float = 0.5      # SD of nightly sleep duration
    bedtime_hour: float = 23.0                # 24-h clock
    steps_per_day: int = 6000
    resting_heart_rate: float = 72.0          # bpm

    # Meal habits: mapping of meal name → (hour, minute).
    meal_times: Dict[str, tuple] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_MEAL_TIMES)
    )

    # Probability per 5-min epoch of an unlogged snack during waking hours.
    unlogged_snack_prob: float = UNLOGGED_SNACK_PROB_PER_EPOCH

    def validate(self) -> None:
        if not 3 <= self.typical_sleep_hours <= 12:
            raise ValueError(f"typical_sleep_hours must be 3–12; got {self.typical_sleep_hours}")
        if self.sleep_variability_hours < 0:
            raise ValueError("sleep_variability_hours must be >= 0")
        if not 0 <= self.bedtime_hour < 24:
            raise ValueError(f"bedtime_hour must be 0–24; got {self.bedtime_hour}")
        if not 0 <= self.steps_per_day <= 50_000:
            raise ValueError(f"steps_per_day must be 0–50 000; got {self.steps_per_day}")
        if not 30 <= self.resting_heart_rate <= 120:
            raise ValueError(f"resting_heart_rate must be 30–120; got {self.resting_heart_rate}")
        if not 0 <= self.unlogged_snack_prob <= 0.1:
            raise ValueError(f"unlogged_snack_prob must be 0–0.1; got {self.unlogged_snack_prob}")


# ── VirtualPatient ───────────────────────────────────────────────────────────

@dataclass
class VirtualPatient:
    """Complete virtual patient profile for the simulator."""

    # Demographics
    name: str = "Patient_A"
    age: int = 45
    sex: str = "M"            # "M" or "F"
    height_cm: float = 170.0
    weight_kg: float = 75.0

    # Labs
    hba1c: float = 5.7
    fasting_glucose: float = 100.0  # mg/dL — if not set, derived from hba1c
    insulin: float = 10.0           # μU/mL
    triglycerides: float = 130.0    # mg/dL
    total_cholesterol: float = 200.0
    hdl: float = 50.0
    ldl: float = 120.0

    # Clinical
    diagnoses: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)

    # Genetics
    genetic_markers: GeneticMarkers = field(default_factory=GeneticMarkers)

    # Lifestyle
    lifestyle: Lifestyle = field(default_factory=Lifestyle)

    # Determinism
    seed: int = 42

    # Metadata & Provenance
    description: str = ""
    source: str = "simulated"

    # ── Derived properties ────────────────────────────────────────────────

    @property
    def bmi(self) -> float:
        """Body-mass index (kg / m²)."""
        height_m = self.height_cm / 100.0
        return round(self.weight_kg / (height_m ** 2), 1)

    @property
    def patient_id(self) -> str:
        """Short identifier for DataFrame columns."""
        return self.name.replace(" ", "_")

    @property
    def insulin_resistance(self) -> float:
        """
        Dimensionless insulin-resistance score (1.0 = normal).
        Additive model: IR = 1.0 + HbA1c_excess + BMI_excess + genetic.
        """
        ir = 1.0
        ir += IR_HBA1C_FACTOR_PER_PCT * max(0, self.hba1c - 5.0)
        ir += IR_BMI_FACTOR_PER_UNIT * max(0, self.bmi - 22.0)
        # Genetic contribution
        g = self.genetic_markers.genetic_risk_score
        ir += GENETIC_IR_MAX_BOOST * (g - 50) / 50.0
        return max(ir, 0.5)  # floor to avoid negative/zero

    @property
    def effective_fasting_glucose(self) -> float:
        """
        Estimated fasting glucose (mg/dL) from HbA1c (ADAG) plus
        an additive IR adjustment, with optional metformin reduction.
        """
        fg = FASTING_GLUCOSE_INTERCEPT + FASTING_GLUCOSE_HBA1C_SLOPE * self.hba1c
        fg += FASTING_GLUCOSE_IR_ADDER_PER_UNIT * max(0, self.insulin_resistance - 1.0)
        if "metformin" in [m.lower() for m in self.medications]:
            fg -= METFORMIN_FASTING_REDUCTION
        return max(fg, 50.0)

    # ── Validation ────────────────────────────────────────────────────────

    def validate(self) -> None:
        """Raise ValueError if any field is outside plausible ranges."""
        if not 0 < self.age <= 120:
            raise ValueError(f"age must be 1–120; got {self.age}")
        if self.sex not in ("M", "F"):
            raise ValueError(f"sex must be 'M' or 'F'; got {self.sex!r}")
        if not 50 <= self.height_cm <= 250:
            raise ValueError(f"height_cm must be 50–250; got {self.height_cm}")
        if not 20 <= self.weight_kg <= 300:
            raise ValueError(f"weight_kg must be 20–300; got {self.weight_kg}")
        if not 3.0 <= self.hba1c <= 20.0:
            raise ValueError(f"hba1c must be 3.0–20.0; got {self.hba1c}")
        if not 30 <= self.fasting_glucose <= 500:
            raise ValueError(f"fasting_glucose must be 30–500; got {self.fasting_glucose}")
        if not 0 <= self.insulin <= 300:
            raise ValueError(f"insulin must be 0–300; got {self.insulin}")
        if not 0 <= self.triglycerides <= 2000:
            raise ValueError(f"triglycerides must be 0–2000; got {self.triglycerides}")
        if not 50 <= self.total_cholesterol <= 500:
            raise ValueError(f"total_cholesterol must be 50–500; got {self.total_cholesterol}")
        if not 10 <= self.hdl <= 150:
            raise ValueError(f"hdl must be 10–150; got {self.hdl}")
        if not 10 <= self.ldl <= 400:
            raise ValueError(f"ldl must be 10–400; got {self.ldl}")
        if self.source != "simulated":
            raise ValueError(f"source must be 'simulated'; got {self.source!r}")
        bmi = self.bmi
        if not 10 <= bmi <= 80:
            raise ValueError(f"Derived BMI must be 10–80; got {bmi}")
        self.genetic_markers.validate()
        self.lifestyle.validate()

    # ── Serialization ─────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Convert to a plain dict (JSON-safe)."""
        d = asdict(self)
        # meal_times contains tuples → convert to lists for JSON
        if "lifestyle" in d and "meal_times" in d["lifestyle"]:
            d["lifestyle"]["meal_times"] = {
                k: list(v) for k, v in d["lifestyle"]["meal_times"].items()
            }
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "VirtualPatient":
        """Reconstruct a VirtualPatient from a dict (e.g. loaded JSON)."""
        d = copy.deepcopy(d)
        # Reconstruct nested dataclasses
        if "genetic_markers" in d and isinstance(d["genetic_markers"], dict):
            d["genetic_markers"] = GeneticMarkers(**d["genetic_markers"])
        if "lifestyle" in d and isinstance(d["lifestyle"], dict):
            ls = d["lifestyle"]
            if "meal_times" in ls:
                ls["meal_times"] = {k: tuple(v) for k, v in ls["meal_times"].items()}
            d["lifestyle"] = Lifestyle(**ls)
        # Filter to declared dataclass fields so extra JSON keys don't error
        valid_fields = {f.name for f in fields(cls)}
        cleaned = {k: v for k, v in d.items() if k in valid_fields}
        patient = cls(**cleaned)
        patient.validate()
        return patient
