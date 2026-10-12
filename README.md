# Type 2 Diabetes Digital Twin: 2-Hour Glucose Spike Warning

**Team:** strawhats | **College / incubator:** Army Institute of Technology, Pune
**Team leader:** Adarsh Singh Bhadauriya | **Members:** Prabhat Ranjan, Pawan Singh Kunwar, Sumit Kumar
**Video (unlisted YouTube):** LINK | **Slides:** `docs/presentation.pdf` | **Architecture:** `docs/architecture.pdf`

## Problem and use case
Type 2 diabetes is widespread in India, and glucose spikes after meals are invisible until a
check-up. This proof of concept builds a "digital twin" of a Type 2 diabetes patient that fuses
two data streams (static health record and wearable time series) to warn a doctor when
glucose is likely to exceed 180 mg/dL in the next 2 hours, and lets the doctor test what-if
meals using common Indian dishes.

## What it does
1. **Spike warning:** predicts whether glucose will exceed 180 mg/dL within 2 hours
   (Low / Watch / High, with plain-language reasons).
2. **Meal what-if:** choose Indian dishes and portions to see the predicted peak glucose
   with a typical-error range.
3. **Doctor dashboard** (Streamlit) combining the patient record, glucose timeline,
   risk level and what-if tool.

## Data (all public or synthetic; no private patient data)
- **CGMacros** (PhysioNet), 45 participants: 15 healthy, 16 prediabetes, 14 Type 2 diabetes
  (group by HbA1c). Continuous glucose (Libre), heart rate, activity, meals with macros,
  and a clinical profile (our EHR stream). License: CC BY-NC-SA 4.0. Not included in this repo;
  download from PhysioNet (see "How to run").
- **Indian Nutrient Databank (INDB)**, Vijayakumar et al., Current Developments in Nutrition, 2024:
  recipe-level nutrition for Indian dishes. License: LICENSE FROM THE PAPER. 17 dishes selected;
  deep-fried and rich dishes excluded because of implausible fat values.
- **Synthetic generator** (`src/generate_data.py`): simulated patients, used for early
  prototyping only. No reported results use synthetic data.

## Method
- Data fusion: 1-minute data resampled to 5 minutes. Dynamic features (current glucose,
  recent change, heart rate, activity, food eaten in the last 3 hours, time of day)
  plus static features (age, sex, BMI, HbA1c, fasting glucose).
- Target: glucose above 180 mg/dL at any point in the next 2 hours, using only moments
  where glucose is currently at or below 180 (new spikes).
- Models: logistic regression and XGBoost (risk), random forest (meal response).
- Validation: 5-fold split by person, so every test person is unseen in training.
  Confidence intervals come from resampling people, not rows.
- Per-meal values were capped (carbs 250 g, protein 150 g, fat 150 g, fiber 60 g) because
  the raw data contains impossible entries.

## Results (Type 2 diabetes participants, unseen people)
| Model | AUC (95% interval) | PR-AUC |
|---|---|---|
| Logistic regression | 0.800 (0.766-0.839) | 0.484 |
| XGBoost | 0.787 (0.744-0.830) | 0.465 |
| Simple rule "high and rising" | 0.733 (0.701-0.756) | n/a |

Spike base rate in this group: 15.9%.
- The models beat the simple rule (difference +0.031 to +0.111 for logistic).
- Logistic and XGBoost are statistically tied. XGBoost is used in the dashboard for explanations.
- Adding heart rate and activity: AUC 0.770 to 0.787, but the difference interval
  (-0.004 to +0.035) includes zero, so the benefit is not statistically clear.
- Per-person AUC (people with both outcomes): median 0.82, lowest 0.66 among Type 2 diabetes participants.
- Dashboard alert levels (XGBoost): WATCH catches about 52% of spikes with about 40% of
  alerts correct; HIGH catches about 27% with about 60% correct.
- Meal model (unseen people, Type 2 diabetes): error about 31 mg/dL vs 39 for predicting the average;
  carbs raise and fiber lowers the predicted peak.

## Limitations (please read)
- Only 14 Type 2 diabetes participants with about 10 days each. This is a proof of concept.
- Mostly US participants and US meals. Not validated on Indian patients; Indian dish
  nutrition values are database estimates and portions are approximate.
- Unlogged snacks and drinks are invisible to the model.
- No step count or sleep data in the real dataset (heart rate and activity are used).
- Metrics are per 5-minute row. Episode-level evaluation is not done.
- The activity what-if was tested and removed because the model learned the wrong direction.
  The meal what-if is an association-based estimate with about 30 mg/dL typical error and
  little data above about 100 g of carbs.
- The model predicts high glucose only, not low glucose.
- The dashboard patients were part of training; reported accuracy comes from held-out tests.
- Research prototype, not a medical device.

## How to run
```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt
# 1. download CGMacros from PhysioNet into data/raw/cgmacros/ and unzip
# 2. download INDB into data/raw/indb/
python src/load_cgmacros.py && python src/features.py
python src/train.py && python src/train_meal.py && python src/indian_meals.py
python src/evaluate.py
streamlit run app/dashboard.py
```

## Tech stack
Python 3.12, pandas, NumPy, scikit-learn, XGBoost, SHAP, Streamlit, Matplotlib.

## License
Code: MIT (see `LICENSE`). Datasets keep their original licenses (see Data).

## References
- CGMacros dataset, PhysioNet. CITATION FROM THE PHYSIONET PAGE.
- Vijayakumar A, Dubasi HB, Awasthi A, Jaacks LM. Development of an Indian Food
  Composition Database. Current Developments in Nutrition, 2024.

---

## Simulation workspace

### Purpose
The Simulation Workspace provides an interactive, physiological digital twin sandbox for clinicians, researchers, and challenge evaluators. While the core project evaluates 2-hour postprandial glucose spike prediction on real clinical data, the simulation workspace allows clinicians to:
- Instantiate multi-modal virtual patients with complete physiological streams (continuous CGM glucose, sleep stages, pedometer steps, continuous heart rate, nocturnal HRV, meal logs, clinical laboratory panels, diagnoses, medications, and polygenic risk scores).
- Run deterministic multi-day physiological simulations calibrated against real clinical targets.
- Explore counterfactual what-if interventions in a sandbox (sleep restriction, food challenges with Indian meals, brisk walking, habitual activity changes) to observe 24-hour glycemic divergence.
- Inspect the 45 real CGMacros human participants alongside virtual personas under strict clinical honesty standards.

### Honesty Rules (Non-Negotiable)
1. **Explicit Provenance Labelling:** Everything produced by the simulator is explicitly marked as `SIMULATED` (with a `source="simulated"` column in files and high-visibility UI badges).
2. **Never Mix Data Streams:** Never attach simulated or synthetic values to real CGMacros human participants. Modalities not collected in the clinical study (sleep architecture, pedometer steps, HRV, genetic variants, diagnoses, medications) strictly display `NOT AVAILABLE`.
3. **Partitioned Model Training:** Never mix simulated rows into real-data model training or real-data evaluation. The real-data headline performance (AUC ~0.80 on unseen T2D patients) remains completely untainted.
4. **Transparent Assumptions:** Every physiological mechanism lives in ONE centralized file ([`src/sim/assumptions.py`](file:///home/luffy/strawhats_AITPune/src/sim/assumptions.py)), with a documented rationale noting that effect sizes are assumptions, not learned from data.
5. **Pipeline Demonstration Only:** Results on simulated cohorts demonstrate digital twin pipeline capability, never clinical proof or treatment efficacy.
6. **Safety Banner:** Prominent research prototype disclaimers state that the workspace is intended strictly for educational, research, or anonymised demonstrations, not as a diagnostic medical device.
7. **Original Visuals:** All graphics and icons are 100% original, generated via code (CSS and inline SVG), with zero copied or downloaded images.

### Provenance Badges Explained
- `REAL`: Directly observed empirical measurements from the clinical study (CGMacros Libre CGM, demographics, lab blood panels).
- `SIMULATED`: Synthetic or model-generated physiological data produced by the mathematical simulator engine.
- `USER-ENTERED`: Parameters configured or typed in by the clinician in patient creation or sandbox forms.
- `NOT AVAILABLE`: Modalities that were not collected in the clinical study protocol (e.g., polysomnography, steps, HRV, genotyping).

### Real vs. Simulated Data Comparison
| Modality / Feature | Real Data (CGMacros) | Simulated Virtual Patients | Notes & Status |
|---|:---:|:---:|---|
| **Continuous Glucose (CGM)** | Libre 1-min & Dexcom G6 | Calibrated 5-min AR(1) sensor noise | Calibrated to real mean glucose, night baseline & meal rise |
| **Heart Rate** | Apple Watch optical HR (1-min) | Circadian sinusoidal baseline + activity rise | Matches real resting HR (~76–78 bpm) |
| **Heart Rate Variability (HRV)** | ❌ NOT AVAILABLE | Nocturnal RMSSD (30–65 ms) with sleep modulation | Derived from sleep stage & autonomic tone assumptions |
| **Sleep Architecture** | ❌ NOT AVAILABLE | 5-min stages (Deep, Light, REM, Awake) in 90-min cycles | Calibrated sleep architecture with sleep debt dynamics |
| **Pedometer Steps** | ❌ NOT AVAILABLE (only METs/kcal) | 5-min step counts (habitual schedule + walks) | Walking activates non-insulin GLUT4 glucose uptake |
| **Meal Intake & Macros** | Photo logs + nutritional estimation | 17 Indian dishes (INDB catalogue) + unlogged ghost snacks | Scaled to ~50–55g carbs/meal matching CGMacros logs |
| **Laboratory Blood Panel** | Venous labs (HbA1c, fasting glu, insulin, lipids) | Comprehensive panel derived from ADAG & IR models | Fully customizable per patient profile |
| **Medical Diagnoses** | Only HbA1c classification (Healthy / Pre / T2D) | Structured chronic condition tags (HTN, Dyslipidemia, etc.) | Informational clinical context |
| **Medications** | Study intake did not log exact doses | Active pharmacological agents (e.g. Metformin) | Metformin applies modest fasting reduction assumption |
| **Genomics / Polygenic** | ❌ NOT AVAILABLE | Polygenic risk score (0–100) & 5 T2D risk allele counts | Contributes to additive insulin resistance index |

### Calibration & Twin Model Reports
- **Simulator Fidelity Report:** See [`docs/results/sim_fidelity.md`](file:///home/luffy/strawhats_AITPune/docs/results/sim_fidelity.md) for calibration results against real CGMacros cohorts across 7 clinical statistics and 3 HbA1c groups, alongside the comparison plot `docs/results/sim_fidelity.png`.
- **Digital Twin Model Report:** See [`docs/results/twin_model_report.md`](file:///home/luffy/strawhats_AITPune/docs/results/twin_model_report.md) for benchmark comparison between the real-data model and the twin model trained on a 300-patient simulated cohort, feature importances (SHAP), and domain-transfer gap analysis.

### How to Run the Simulation Workspace
```bash
# Activate the virtual environment
source .venv/bin/activate

# Run the complete test suite (39 automated unit & UI integration tests)
pytest tests/

# Launch the Simulation Workspace
streamlit run app/sim_workspace.py
```

### Limitations of Simulated Data
- **Model Assumptions, Not Clinical Truth:** Simulated outputs reflect mathematical assumptions encoded in `src/sim/assumptions.py`, not real biological complexity.
- **Simplified Physiology:** Complex hormonal feedback (glucagon, amylin, incretins/GLP-1, hepatic glycogenolysis kinetics) is approximated by lumped mathematical functions (gamma curves and exponential return rates).
- **Lower Nocturnal Variability:** As documented in the fidelity report, real diabetic patients exhibit unpredictable nocturnal glucose swings that stationary AR(1) noise cannot fully capture (-45% to -49% std dev).
- **Not a Diagnostic Tool:** All scenario interventions and spike predictions are intended solely for exploration, teaching, and system stress-testing.

