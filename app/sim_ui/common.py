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
