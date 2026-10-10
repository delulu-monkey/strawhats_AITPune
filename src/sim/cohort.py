"""
Virtual Patient Cohort Generator.
=================================

Generates a diverse virtual cohort of ~300 virtual patients (14 days each),
spanning:
- Ages 30–75
- HbA1c 5.0–10.0%
- Sleep habits (duration, variability, bedtime)
- Activity levels (2,000–14,000 steps/day)
- Genetic risk scores (10–95)
- Realistic diagnoses and medications

Saves timeseries and featurized datasets into `data/simulated/` (gitignored).
Includes `source="simulated"` on all records.
Deterministic with a fixed seed.
"""

from __future__ import annotations

import json
import os
import time
from typing import List, Tuple
import numpy as np
import pandas as pd

from src.sim.profile import VirtualPatient, GeneticMarkers, Lifestyle
from src.sim.simulator import simulate
from src.sim.featurize import featurize_patient


DEFAULT_COHORT_SIZE = 300
DEFAULT_DAYS = 14
DEFAULT_SEED = 42
DEFAULT_OUTPUT_DIR = "data/simulated"


def generate_cohort_profiles(
    n_patients: int = DEFAULT_COHORT_SIZE,
    seed: int = DEFAULT_SEED,
) -> List[VirtualPatient]:
    """
    Generate diverse VirtualPatient profiles spanning target clinical distributions.
    """
    rng = np.random.default_rng(seed)
    patients: List[VirtualPatient] = []

    for i in range(n_patients):
        p_seed = int(rng.integers(1, 100_000_000))
        p_rng = np.random.default_rng(p_seed)

        # Diverse clinical parameters across spectrum
        age = int(p_rng.integers(30, 76))
        sex = "M" if p_rng.random() < 0.50 else "F"

        # HbA1c: mix of healthy (5.0-5.6), prediabetes (5.7-6.4), and T2D (6.5-10.0)
        group_selector = p_rng.random()
        if group_selector < 0.30:  # Healthy ~30%
            hba1c = float(p_rng.uniform(5.0, 5.69))
            bmi = float(np.clip(p_rng.normal(26.0, 4.0), 19.0, 36.0))
            diag = []
            meds = []
            steps = int(np.clip(p_rng.normal(8000, 2500), 3000, 15000))
            sleep_h = float(np.clip(p_rng.normal(7.5, 0.8), 5.5, 9.0))
            grs = float(np.clip(p_rng.normal(35.0, 15.0), 10.0, 75.0))
            rhr = float(np.clip(p_rng.normal(74.0, 5.0), 58.0, 90.0))
        elif group_selector < 0.60:  # Prediabetes ~30%
            hba1c = float(p_rng.uniform(5.7, 6.49))
            bmi = float(np.clip(p_rng.normal(30.0, 5.0), 22.0, 42.0))
            diag = ["prediabetes"]
            meds = []
            steps = int(np.clip(p_rng.normal(6000, 2200), 2000, 12000))
            sleep_h = float(np.clip(p_rng.normal(7.0, 0.9), 5.0, 8.5))
            grs = float(np.clip(p_rng.normal(55.0, 15.0), 20.0, 85.0))
            rhr = float(np.clip(p_rng.normal(76.0, 5.0), 60.0, 92.0))
        else:  # T2D ~40%
            hba1c = float(p_rng.uniform(6.5, 10.0))
            bmi = float(np.clip(p_rng.normal(32.5, 5.5), 23.0, 48.0))
            diag = ["type 2 diabetes"]
            meds = ["metformin"] if p_rng.random() < 0.65 else []
            steps = int(np.clip(p_rng.normal(4500, 1800), 1500, 10000))
            sleep_h = float(np.clip(p_rng.normal(6.5, 1.1), 4.5, 8.5))
            grs = float(np.clip(p_rng.normal(72.0, 14.0), 35.0, 98.0))
            rhr = float(np.clip(p_rng.normal(78.0, 6.0), 62.0, 96.0))

        height = float(np.clip(p_rng.normal(168.0, 8.5), 148.0, 192.0))
        weight = float(bmi * ((height / 100.0) ** 2))

        # Bedtime and sleep variability (strictly within [0, 24))
        bedtime = float(np.clip(p_rng.normal(22.8, 0.8), 21.0, 23.8))
        sleep_var = float(np.clip(p_rng.normal(0.6, 0.2), 0.2, 1.5))

        patient = VirtualPatient(
            name=f"sim_{i+1:04d}",
            age=age,
            sex=sex,
            height_cm=round(height, 1),
            weight_kg=round(weight, 1),
            hba1c=round(hba1c, 2),
            fasting_glucose=100.0,  # derived via effective_fasting_glucose
            diagnoses=diag,
            medications=meds,
            genetic_markers=GeneticMarkers(genetic_risk_score=round(grs, 1)),
            lifestyle=Lifestyle(
                typical_sleep_hours=round(sleep_h, 1),
                sleep_variability_hours=round(sleep_var, 2),
                bedtime_hour=round(bedtime, 1),
                steps_per_day=steps,
                resting_heart_rate=round(rhr, 1),
            ),
            seed=p_seed,
        )
        patients.append(patient)

    return patients


def build_cohort_dataset(
    n_patients: int = DEFAULT_COHORT_SIZE,
    days: int = DEFAULT_DAYS,
    seed: int = DEFAULT_SEED,
    output_dir: str = DEFAULT_OUTPUT_DIR,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Run cohort simulation and feature extraction, saving artifacts to output_dir.

    Returns
    -------
    (timeseries_df, features_df)
    """
    os.makedirs(output_dir, exist_ok=True)
    profiles = generate_cohort_profiles(n_patients=n_patients, seed=seed)

    print(f"Simulating {len(profiles)} virtual patients for {days} days each (seed={seed})...")
    timeseries_parts: List[pd.DataFrame] = []
    feature_parts: List[pd.DataFrame] = []

    for idx, p in enumerate(profiles):
        df, sl = simulate(p, days=days)
        # Ensure source="simulated"
        df["source"] = "simulated"
        timeseries_parts.append(df)

        # Featurize with twin inputs and target
        f_df = featurize_patient(df, profile=p, sleep_summary=sl, include_twin_features=True, include_target=True)
        f_df["subject"] = p.patient_id
        f_df["source"] = "simulated"
        feature_parts.append(f_df)

        if (idx + 1) % 50 == 0 or (idx + 1) == len(profiles):
            print(f"  Processed {idx + 1}/{len(profiles)} patients...")

    all_timeseries = pd.concat(timeseries_parts, ignore_index=True)
    all_features = pd.concat(feature_parts).rename_axis("time").reset_index()

    # Save profiles JSON
    profiles_path = os.path.join(output_dir, "cohort_profiles.json")
    with open(profiles_path, "w") as f:
        json.dump([p.to_dict() for p in profiles], f, indent=2)

    # Save Parquet timeseries & features
    ts_path = os.path.join(output_dir, "cohort_timeseries.parquet")
    feats_path = os.path.join(output_dir, "cohort_features.parquet")
    all_timeseries.to_parquet(ts_path, index=False)
    all_features.to_parquet(feats_path, index=False)

    print(f"\nCohort saved successfully to {output_dir}:")
    print(f"  - {ts_path}: {len(all_timeseries):,} rows, {len(all_timeseries.columns)} cols")
    print(f"  - {feats_path}: {len(all_features):,} rows, {len(all_features.columns)} cols")
    print(f"  - {profiles_path}: {len(profiles)} patient profiles")

    return all_timeseries, all_features


def main() -> None:
    t0 = time.time()
    print("=" * 60)
    print("GENERATING VIRTUAL PATIENT COHORT (PART 3)")
    print("=" * 60)
    build_cohort_dataset()
    elapsed = time.time() - t0
    print(f"\nCohort generation completed in {elapsed:.1f} seconds.")
    print("=" * 60)


if __name__ == "__main__":
    main()
