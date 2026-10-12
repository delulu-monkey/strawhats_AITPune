"""
Shared models, caching utilities, and real data loaders.
========================================================
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple, Dict, Any, List

import joblib
import pandas as pd
import shap
import streamlit as st

from src.sim.profile import VirtualPatient
from src.sim.simulator import simulate
from src.sim.featurize import featurize_patient


@st.cache_resource
def load_models():
    """Load spike XGBoost classifier, meal RF regressor, and SHAP explainer."""
    risk_dict = joblib.load("models/xgb_spike_model.pkl")
    meal_dict = joblib.load("models/meal_response_rf.pkl")
    explainer = shap.TreeExplainer(risk_dict["model"])
    return risk_dict, meal_dict, explainer


@st.cache_data
def load_indian_meals() -> pd.DataFrame:
    """Load Indian dish nutrient catalogue."""
    return pd.read_csv("data/indian_meals.csv")


@st.cache_data
def load_real_bio_data() -> pd.DataFrame:
    """
    Load real labs and demographics from CGMacros bio.csv.
    Standardizes whitespace in column names and maps participant IDs.
    """
    bio_path = Path("data/raw/cgmacros/CGMacros/bio.csv")
    if not bio_path.exists():
        # Fallback search if path varies
        bio_matches = list(Path("data/raw/cgmacros").rglob("bio.csv"))
        if bio_matches:
            bio_path = bio_matches[0]
        else:
            raise FileNotFoundError("Real CGMacros bio.csv not found.")

    df = pd.read_csv(bio_path)
    df.columns = df.columns.str.strip()
    # Normalize key column names
    rename_map = {
        "Age": "age",
        "Gender": "gender",
        "BMI": "bmi",
        "Body weight": "weight_lbs",
        "Height": "height_in",
        "Self-identify": "ethnicity",
        "A1c PDL (Lab)": "hba1c",
        "Fasting GLU - PDL (Lab)": "fasting_glu",
        "Insulin": "insulin",
        "Triglycerides": "triglycerides",
        "Cholesterol": "cholesterol",
        "HDL": "hdl",
        "Non HDL": "non_hdl",
        "LDL (Cal)": "ldl",
        "VLDL (Cal)": "vldl",
        "Cho/HDL Ratio": "cho_hdl_ratio",
    }
    df = df.rename(columns=rename_map)
    if "bmi" in df.columns:
        df["bmi"] = df["bmi"].round(1)
    df["subject_str"] = df["subject"].apply(lambda s: f"CGMacros-{int(s):03d}")
    df["group"] = pd.cut(
        df["hba1c"],
        bins=[0, 5.7, 6.5, 20.0],
        labels=["healthy", "prediabetes", "t2d"],
        right=False,
    )
    return df


@st.cache_data(show_spinner="Simulating virtual patient dynamics...")
def run_simulation_cached(
    patient_json_str: str,
    days: int = 7,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Run deterministic simulator for a virtual patient, cached by patient JSON string and days.
    Returns:
        gdf: 5-minute continuous glucose & sensor dataframe
        sdf: nightly sleep stages summary dataframe
        feats: 27-column feature table for model evaluation
    """
    p_dict = json.loads(patient_json_str)
    patient = VirtualPatient.from_dict(p_dict)
    gdf, sdf = simulate(patient, days=days)
    feats = featurize_patient(gdf, patient)
    if "time" not in feats.columns:
        feats = feats.reset_index()
    return gdf, sdf, feats


# ─── Shared Human-Friendly Feature Names (Requirement 4) ──────────────────────
# Map raw ML feature names to readable labels and formatting specifications.
FEATURE_LABELS: Dict[str, Tuple[str, str]] = {
    "glu_now": ("Current glucose", "{:.0f} mg/dL"),
    "glu_chg_15m": ("Glucose change, last 15 min", "{:+.0f} mg/dL"),
    "glu_chg_30m": ("Glucose change, last 30 min", "{:+.0f} mg/dL"),
    "glu_chg_60m": ("Glucose change, last 60 min", "{:+.0f} mg/dL"),
    "glu_mean_60m": ("60-minute mean glucose", "{:.0f} mg/dL"),
    "glu_std_60m": ("60-minute glucose SD", "{:.1f} mg/dL"),
    "glu_max_120m": ("120-minute maximum glucose", "{:.0f} mg/dL"),
    "glu_mean_1h": ("1-hour mean glucose", "{:.0f} mg/dL"),
    "glu_mean_3h": ("3-hour mean glucose", "{:.0f} mg/dL"),
    "glu_mean_6h": ("6-hour mean glucose", "{:.0f} mg/dL"),
    "glu_chg_1h": ("Glucose change, last 1h", "{:+.0f} mg/dL"),
    "glu_sd_6h": ("6-hour glucose SD", "{:.1f} mg/dL"),
    "glu_min_6h": ("6-hour minimum glucose", "{:.0f} mg/dL"),
    "glu_max_6h": ("6-hour maximum glucose", "{:.0f} mg/dL"),
    "hr_mean_30m": ("Mean heart rate, last 30 min", "{:.0f} bpm"),
    "mets_mean_30m": ("Activity intensity, last 30 min", "{:.1f} METs"),
    "act_kcal_60m": ("Active calories, last 60 min", "{:.0f} kcal"),
    "carbs_3h": ("Carbohydrates, last 3 h", "{:.0f} g"),
    "protein_3h": ("Protein, last 3 h", "{:.0f} g"),
    "fat_3h": ("Fat, last 3 h", "{:.0f} g"),
    "fiber_3h": ("Fibre, last 3 h", "{:.1f} g"),
    "min_since_meal": ("Minutes since last meal", "{:.0f} min"),
    "steps_30m": ("Steps, last 30 min", "{:,.0f} steps"),
    "steps_1h": ("Steps, last 1h", "{:,.0f} steps"),
    "steps_3h": ("Steps, last 3h", "{:,.0f} steps"),
    "hba1c": ("HbA1c", "{:.1f}%"),
    "fasting_glu": ("Simulated overnight sensor baseline", "{:.0f} mg/dL"),
    "time_of_day": ("Circadian phase / time", "{:s}"),
    "hour_sin": ("Circadian cycle (sin)", "{:.2f}"),
    "hour_cos": ("Circadian cycle (cos)", "{:.2f}"),
    "age": ("Age", "{:.0f} yrs"),
    "bmi": ("Body mass index (BMI)", "{:.1f} kg/m²"),
    "male": ("Biological sex (male)", "{:.0f}"),
}


def get_friendly_feature_name(feat_name: str) -> str:
    """Return human-readable friendly label for a feature name."""
    return FEATURE_LABELS.get(feat_name, (feat_name.replace("_", " ").title(), ""))[0]


# ─── Genetics Polygenic Risk Variant Weights (Requirement 6) ──────────────────
# Documented weights summing to 100 for 10 risk alleles (assumption, not fitted to data):
# - TCF7L2 (OR ~1.37): 14 pts/allele (max 28)
# - SLC30A8, KCNJ11, PPARG, FTO: 9 pts/allele each (max 18 each)
# Total max: 28 + 18 + 18 + 18 + 18 = 100.
VARIANT_WEIGHTS: Dict[str, float] = {
    "TCF7L2_rs7903146": 14.0,
    "SLC30A8_rs13266634": 9.0,
    "KCNJ11_rs5219": 9.0,
    "PPARG_rs1801282": 9.0,
    "FTO_rs9939609": 9.0,
}

VARIANT_RISK_ALLELES: Dict[str, Dict[str, str]] = {
    "TCF7L2_rs7903146": {
        "gene": "TCF7L2",
        "risk_allele": "T",
        "protective_allele": "C",
        "citation": "Grant et al. 2006 (Nat Genet 38:320); Mahajan et al. 2018 (Nat Genet 50:1505)",
        "role": "Wnt signaling effector; strongest common T2D susceptibility locus (OR ~1.37)",
    },
    "SLC30A8_rs13266634": {
        "gene": "SLC30A8",
        "risk_allele": "C (Arg325)",
        "protective_allele": "T (Trp325)",
        "citation": "Sladek et al. 2007 (Nature 445:881); Mahajan et al. 2018",
        "role": "Zinc transporter ZnT8; insulin secretory granule crystallization (OR ~1.12)",
    },
    "KCNJ11_rs5219": {
        "gene": "KCNJ11",
        "risk_allele": "T (Lys23)",
        "protective_allele": "C (Glu23)",
        "citation": "Gloyn et al. 2003 (Diabetes 52:568); Florez et al. 2004 (N Engl J Med 351:1517)",
        "role": "Kir6.2 subunit of ATP-sensitive K+ channel; regulates beta-cell depolarization (OR ~1.14)",
    },
    "PPARG_rs1801282": {
        "gene": "PPARG",
        "risk_allele": "C (Pro12; common allele)",
        "protective_allele": "G (Ala12; minor allele)",
        "citation": "Altshuler et al. 2000 (Nat Genet 26:76); Deeb et al. 1998 (Nat Genet 20:284)",
        "role": "Nuclear receptor regulating adipogenesis; note: the common Pro allele is the risk allele, minor Ala is protective (OR ~1.14)",
    },
    "FTO_rs9939609": {
        "gene": "FTO",
        "risk_allele": "A",
        "protective_allele": "T",
        "citation": "Frayling et al. 2007 (Science 316:889); Scott et al. 2007 (Science 316:1341)",
        "role": "m6A RNA demethylase; predisposes to increased BMI and adiposity-driven insulin resistance (OR ~1.15)",
    },
}


def compute_genetic_risk_score(variant_alleles: Dict[str, int]) -> float:
    """Compute 0–100 composite genetic risk score from allele counts using documented weights."""
    score = 0.0
    for v, weight in VARIANT_WEIGHTS.items():
        count = variant_alleles.get(v, 0)
        score += count * weight
    return min(100.0, max(0.0, round(score, 1)))

