# Independent Audit of Data Honesty, Calculations, and Provenance

**Date:** 13 October 2026  
**Auditor:** Independent Automated Compliance Audit (Antigravity Agent)  
**Scope:** `src/sim/`, `app/`, `docs/`, `models/`, `data/`  
**Governing Standard:** `docs/SIM_BRIEF.md` (Honesty Rules 1–7) & Git Safety Rules  
**Branch:** `feature/virtual-patients`  

---

## Executive Summary

An exhaustive independent code and calculation audit was conducted across the simulation workspace, models, UI layers, and documentation.

### Core Audit Verdict
1. **No Data Leakage / Contamination:** Real CGMacros time-series or individual rows are **never** copied, cloned, or resampled into simulated virtual patients or the synthetic cohort.
2. **Train/Test Integrity:** Real-data models (`xgb_spike_model`, `logistic`, `meal_response_rf`, `meal_response_ridge`) strictly enforce subject-level `GroupKFold` cross-validation with zero patient overlap across folds. Sim-to-real evaluations clearly separate synthetic-training metrics from real-patient evaluations.
3. **Calculations Verified:** Lipid panels across all 6 presets satisfy the Friedewald equation ($LDL = Total - HDL - TG/5$) with $0.0\text{ mg/dL}$ residual. BMI values accurately reflect height and weight.
4. **Key Finding / Defect Identified:** On the **Real Reference Patients** page, the heart rate metric card displays a hard-coded static string (`"78 bpm"`) labeled with a `REAL` provenance badge ([`app/sim_ui/theme.py:192-196`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L192-L196)) instead of extracting the participant's actual observed heart rate from `data/processed/cgmacros_all.csv.gz`.
5. **Display Ambiguity Identified:** In **Patient View**, the summary card subtitle (`Mean 84 · TIR 83%`) displays the **7-day aggregate** simulation mean and TIR directly adjacent to a single **24-hour** date picker and trajectory chart without an explicit time-window descriptor.

---

## 1. Data Provenance Audit

We inspected every read operation and data source across all simulator core modules:

| Source File | Real Data Read? | Exact Path & Line | Purpose & Usage | Integrity Flag |
|:---|:---:|:---|:---|:---:|
| [`src/sim/assumptions.py`](file:///home/luffy/strawhats_AITPune/src/sim/assumptions.py) | **No** | None | Pure constant definitions with clinical rationales | ✅ Clean |
| [`src/sim/simulator.py`](file:///home/luffy/strawhats_AITPune/src/sim/simulator.py) | **No** | Line 70: `data/indian_meals.csv` | Reads public macro catalogue for Indian dishes | ✅ Clean |
| [`src/sim/calibrate.py`](file:///home/luffy/strawhats_AITPune/src/sim/calibrate.py) | **Yes** | Line 56: `data/processed/cgmacros_all.csv.gz` | Strictly calculates cohort-level aggregate summary statistics (medians, IQRs) for validation reporting | ✅ Compliant (Aggregate only) |
| [`src/sim/cohort.py`](file:///home/luffy/strawhats_AITPune/src/sim/cohort.py) | **No** | None | Generates parametric synthetic virtual patients from random seeds; marks `source="simulated"` | ✅ Clean |
| [`src/sim/profile.py`](file:///home/luffy/strawhats_AITPune/src/sim/profile.py) | **No** | None | Dataclass definitions and regression property evaluations | ✅ Clean |
| [`src/sim/store.py`](file:///home/luffy/strawhats_AITPune/src/sim/store.py) | **No** | None | Manages JSON persistence in `data/virtual_patients/` | ✅ Clean |
| [`src/sim/scenarios.py`](file:///home/luffy/strawhats_AITPune/src/sim/scenarios.py) | **No** | Line 84: `data/indian_meals.csv` | Reads Indian meal catalogue for meal intervention | ✅ Clean |

### Copying / Resampling Check
- **Zero Real Rows Copied:** No real rows or time series from `cgmacros_all.csv.gz` or `bio.csv` are copied into `data/simulated/` or `data/virtual_patients/`.
- **Synthetic Cohort Generation:** Synthetic patient generation in `src/sim/cohort.py` and `src/sim/calibrate.py` draws solely from independent Gaussian/uniform distributions seeded deterministically (`np.random.default_rng`).

---

## 2. Hard-Coded Values in UI vs Computed Values

We audited all numerical values appearing across the UI to distinguish hard-coded constants from computed outputs:

| UI Location / Element | Displayed Value / String | Origin / Source | Classification |
|:---|:---|:---|:---|
| **Real Patient HR Card** ([`theme.py:192`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L192)) | `"78 bpm"` | Hard-coded string `"78"` in `render_patient_body_overview` | ⚠️ **Hard-Coded** (Flagged: Labeled `REAL`) |
| **Virtual Patient HR Fallback** ([`theme.py:255`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L255)) | `"74 bpm"`, `[70, 72, 74...]` | Hard-coded fallback in `theme.py` when `simulation_df is None` | ℹ️ **Hard-Coded Fallback** (Inactive in normal runs) |
| **Virtual Patient HRV Fallback** ([`theme.py:258`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L258)) | `"38 ms"`, `[35, 38, 40...]` | Hard-coded fallback in `theme.py` when `simulation_df is None` | ℹ️ **Hard-Coded Fallback** (Inactive in normal runs) |
| **Glucose Summary Subtitle** ([`theme.py:239`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L239)) | E.g. `"Mean 84 · TIR 83%"` | Computed dynamically: `simulation_df["libre"].mean()` and `((libre >= 70) & (libre <= 180)).mean() * 100` | ✅ **Computed** (Note: 7-day aggregate) |
| **Spike Risk Thresholds** ([`common.py`](file:///home/luffy/strawhats_AITPune/app/sim_ui/common.py), [`patient_view.py`](file:///home/luffy/strawhats_AITPune/app/sim_ui/patient_view.py)) | `WATCH = 0.75`, `HIGH = 0.91` | Derived from empirical precision targets on held-out T2D cohort (`dashboard.py`, `evaluate.py`) | ✅ **Tuned Model Constants** |
| **Out-of-Domain Threshold** ([`patient_view.py`](file:///home/luffy/strawhats_AITPune/app/sim_ui/patient_view.py)) | `180 mg/dL` | Clinical hyperglycemic excursion threshold defining spike model training boundary | ✅ **Domain Boundary Constant** |
| **Modelled IR Index** ([`profile.py:146`](file:///home/luffy/strawhats_AITPune/src/sim/profile.py#L146)) | E.g. `1.15`, `3.00` | Computed from HbA1c, BMI, and genetics: $1.0 + 0.45(A1c - 5) + 0.02(BMI - 22) + 0.20\frac{GRS - 50}{50}$ | ✅ **Computed Property** |
| **Preset Laboratory Values** | E.g. Fasting insulin, lipids | Stored in JSON files (`data/virtual_patients/presets/*.json`) | ℹ️ **Preset Profile Specifications** |
| **Lab Reference Ranges** ([`patient_view.py:448-457`](file:///home/luffy/strawhats_AITPune/app/sim_ui/patient_view.py#L448-L457)) | E.g. `"Target: 18.5–24.9"`, `"Normal < 150"` | Standard clinical reference boundaries embedded in table notes | ℹ️ **Clinical Reference Ranges** |

---

## 3. Independent Recomputation from Raw Simulator Output

We executed raw headless simulations (`simulate(patient, days=7)`) for all 6 virtual patient presets without touching any UI code and compared every recomputed parameter against the UI outputs:

### Recomputation Comparison Table

| Preset ID | Preset Name | Raw BMI | Profile BMI | TC | HDL | TG | LDL | Friedewald LDL | Lipid $\Delta$ | UI Card Subtitle | Sim 7d Mean | Sim 7d TIR | Sim 7d TBR (<70) | Sim 7d TAR (>180) | Sim Day 1 (24h) Mean / TIR | Sim Day 2 (24h) Mean / TIR |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `active_38_early_disease` | Active 38yo (Early Prediabetes) | 24.24 | 24.2 | 185.0 | 54.0 | 130.0 | 105.0 | 105.0 | 0.0 | Mean 99 · TIR 94% | 98.9 | 94.5% | 4.8% | 0.7% | 103.6 / 100.0% | 95.8 / 100.0% |
| `lean_high_genetic_risk` | Lean Patient with High Genetic Risk | 20.76 | 20.8 | 180.0 | 58.0 | 105.0 | 101.0 | 101.0 | 0.0 | Mean 106 · TIR 98% | 105.7 | 98.0% | 1.1% | 0.9% | 108.2 / 99.3% | 98.2 / 97.9% |
| `older_metformin_high_cholesterol` | Older Patient on Metformin (High Cholesterol) | 27.64 | 27.6 | 260.0 | 40.0 | 220.0 | 176.0 | 176.0 | 0.0 | Mean 131 · TIR 98% | 130.7 | 97.8% | 0.0% | 2.2% | 125.7 / 100.0% | 136.6 / 89.2% |
| `poorly_controlled_55_sleep_deprived` | Poorly-Controlled 55yo (Short Sleep) | 32.01 | 32.0 | 235.0 | 38.0 | 240.0 | 149.0 | 149.0 | 0.0 | Mean 180 · TIR 64% | 180.3 | 64.0% | 0.0% | 36.0% | 192.6 / 46.9% | 177.1 / 61.5% |
| `sedentary_night_shift_worker` | Sedentary Night-Shift Worker | 28.73 | 28.7 | 215.0 | 42.0 | 195.0 | 134.0 | 134.0 | 0.0 | Mean 115 · TIR 96% | 114.9 | 96.3% | 1.4% | 2.3% | 112.8 / 99.7% | 115.4 / 93.1% |
| `well_controlled_45` | Well-Controlled 45yo | 23.66 | 23.7 | 175.0 | 55.0 | 110.0 | 98.0 | 98.0 | 0.0 | Mean 84 · TIR 83% | 83.8 | 83.2% | 16.8% | 0.0% | 90.8 / 95.8% | 84.8 / 93.4% |

### Analysis of Numerical Differences
1. **Friedewald Equation ($TC - HDL - TG / 5 = LDL$):** Across all 6 presets, the residual difference is **exactly $0.0\text{ mg/dL}$**. The lipid panels are chemically consistent.
2. **BMI Consistency:** Weight divided by height squared matches profile BMI within standard 1-decimal rounding ($|\text{raw} - \text{profile}| \le 0.06$).
3. **UI Metric Card vs 24-Hour Reality:**
   - The UI card displays `Mean 84 · TIR 83%` for `well_controlled_45`. This matches the 7-day raw simulator mean ($83.8\text{ mg/dL}$) and 7-day TIR ($83.2\%$).
   - However, on Day 1 (first 24h), the 24h mean is $90.8\text{ mg/dL}$ with a TIR of $95.8\%$. On Day 2 (Jan 02, the selected evaluation date in the UI), the 24h mean is $84.8\text{ mg/dL}$ with a TIR of $93.4\%$.
   - **Finding:** The UI card is an accurate representation of the **7-day simulation**, but because the UI does not label it as "7-Day Mean", users viewing the 24-hour daily trajectory may notice a discrepancy between daily TIR ($93.4\%$) and displayed card TIR ($83\%$).

---

## 4. Train / Test Leakage and Model Validation

### A. Real-Data Model Validation (`src/train.py`, `src/train_meal.py`, `src/evaluate.py`)
- **Validation Scheme:** Strictly 5-fold `GroupKFold` grouped by `subject`.
- **Leakage Check:** Confirmed that every fold trains on 36 participants and tests on 9 distinct unseen participants. Zero participants appear in both train and test partitions.
- **Bootstrapping Integrity:** In `src/evaluate.py` lines 91–105, confidence interval bootstrapping resamples **people** (`ids = df.loc[t2d, "subject"].unique()`), never individual 5-minute time rows.
- **Cohort Results (Held-Out Unseen T2D Participants):**
  - Logistic Regression: ROC-AUC = $0.800$ (95% CI: 0.766–0.838), PR-AUC = $0.484$
  - XGBoost Spike Model: ROC-AUC = $0.787$ (95% CI: 0.744–0.830), PR-AUC = $0.465$
  - Heuristic Rule (`glu_now + 2 * glu_chg_30m`): ROC-AUC = $0.733$ (95% CI: 0.701–0.756)

### B. Twin Model & Sim-to-Real Transfer (`src/sim/train_twin.py`)
- **Sim-Trained Twin Model Evaluation:**
  - Evaluated on simulated data strictly as a **pipeline demonstration** using `GroupKFold` across 300 synthetic subjects.
  - Documented explicitly in `docs/results/twin_model_report.md` line 214: *"Results on simulated data are a pipeline demonstration, not clinical evidence. The twin model's dependence on sleep and genetics reflects assumptions built into the simulator."*
- **Datasets Used:**
  - Synthetic training dataset: `data/simulated/cohort_features.parquet` (300 subjects, 14 days)
  - Real transfer evaluation dataset: `data/processed/features.csv.gz` (45 real CGMacros participants, 128,006 5-minute epochs)
- **Separation of Metrics (Twin Report Table 2):**
  - **Sim Model on Real (ALL):** ROC-AUC = $0.850$, PR-AUC = $0.446$, Precision = $0.183$, Recall = $0.771$
  - **Sim Model on Real (T2D Only):** ROC-AUC = $0.755$, PR-AUC = $0.613$, Precision = $0.279$, Recall = $0.934$
  - **Sim Model on Simulated CV:** ROC-AUC = $0.887$, PR-AUC = $0.627$
  - **Integrity Verdict:** Sim-to-real transfer results are reported separately from simulation cross-validation. Simulation performance is never passed off as clinical evidence.

---

## 5. Provenance Labels Audit

We surveyed all fields and charts across the workspace to verify adherence to Rule 1 & Rule 2:

| UI Page | Field / Component | Applied Provenance Badge | Ground Truth Classification | Status / Flag |
|:---|:---|:---:|:---:|:---:|
| **Patient View** | Profile Header & Demographics | `SIMULATED` | Simulated Virtual Preset | ✅ Correct |
| **Patient View** | Glucose & HR Summary Cards | `SIMULATED` | Simulated Continuous Sensor Trace | ✅ Correct |
| **Patient View** | 2-Hour Spike Risk Assessment | `SIMULATED` | XGBoost Scored on Simulated State | ✅ Correct |
| **Patient View** | 24-Hour Glucose Trajectory | `SIMULATED` | Simulated CGM Trace | ✅ Correct |
| **Patient View** | Hypnogram & Activity Charts | `SIMULATED` | Simulated Sensor Telemetry | ✅ Correct |
| **Patient View** | Complete Laboratory Panel | `SIMULATED` | Preset Lab Panel | ✅ Correct |
| **Scenario Sandbox** | Baseline & Scenario Cards | `SIMULATED` | Counterfactual Simulation Engine | ✅ Correct |
| **Scenario Sandbox** | 24h Spike Risk Timeline | `SIMULATED` | Model Scored on Counterfactual Trace | ✅ Correct |
| **Real Reference** | Demographic Panel | `REAL` | Real Observed Demographics (`bio.csv`) | ✅ Correct |
| **Real Reference** | Glycemic & Lipid Lab Panel | `REAL` | Real Observed Labs (`bio.csv`) | ✅ Correct |
| **Real Reference** | Continuous Glucose CGM | `REAL` | Real Libre Sensor Trace (`cgmacros_all.csv.gz`) | ✅ Correct |
| **Real Reference** | Sleep Stages, HRV, Steps | `NOT AVAILABLE` | Protocol Gaps (Lacking in CGMacros) | ✅ Correct |
| **Real Reference** | **Heart Rate Summary Card** | `REAL` | **Hard-coded static string "78"** | ❌ **MISMATCH: Hard-coded constant labeled REAL** |
| **Add Patient** | Demographic & Lab Input Sections | `USER-ENTERED` | Clinician / Doctor Form Inputs | ✅ Correct |
| **Storage Helper** | `get_provenance_map(..., is_real=True)` | `USER-ENTERED` | Real dataset fields | ⚠️ **Inconsistency:** Emits `USER-ENTERED` instead of `REAL` at helper level |

---

## 6. Claims & Supporting Evidence

We reviewed all assertions of calibration, fidelity, and accuracy across documentation and UI strings:

| File & Line | Claimed Sentence | Repo Evidence / Supporting File | Verdict |
|:---|:---|:---|:---:|
| [`docs/sim_fidelity.md:16`](file:///home/luffy/strawhats_AITPune/docs/sim_fidelity.md#L16) | *"24h Mean Glucose (mg/dL) Real Target: 84.54 [77.75–89.84], Simulated: 87.50, Inside IQR"* | Computed in `src/sim/calibrate.py:91-94`; target matches `data/processed/cgmacros_all.csv.gz` | ✅ Supported |
| [`docs/sim_fidelity.md:56`](file:///home/luffy/strawhats_AITPune/docs/sim_fidelity.md#L56) | *"Short-term interstitial noise parameters match real CGMacros 5-minute dynamics (SENSOR_AR1_PHI = 0.97, SENSOR_NOISE_SD = 3.3 mg/dL)"* | Regressions fitted in `docs/real_glucose_reference.md` (median $\phi=0.97$, innovation $SD=3.3$) | ✅ Supported |
| [`docs/sim_fidelity.md:57`](file:///home/luffy/strawhats_AITPune/docs/sim_fidelity.md#L57) | *"Overnight Sensor Baseline: Anchored to real CGMacros Libre sensor regressions: 4.57 + 0.77 * fasting_glucose"* | Directly matches Regression 2 in `docs/real_glucose_reference.md` and `src/sim/assumptions.py:18` | ✅ Supported |
| [`docs/findings.md:10`](file:///home/luffy/strawhats_AITPune/docs/findings.md#L10) | *"Rows: 128,006, spike rate 6.8% (15.9% in T2D). 22 features, 5-minute resolution."* | Directly verified on `data/processed/features.csv.gz` via `src/train.py` | ✅ Supported |
| [`docs/findings.md:18-19`](file:///home/luffy/strawhats_AITPune/docs/findings.md#L18-L19) | *"Logistic regression AUC 0.800 (0.766-0.838), PR-AUC 0.484; XGBoost 0.787 (0.744-0.830)"* | Generated by `src/evaluate.py` using subject-level `GroupKFold` | ✅ Supported |
| [`docs/findings.md:57-58`](file:///home/luffy/strawhats_AITPune/docs/findings.md#L57-L58) | *"Average 2-hour rise: healthy 33, prediabetes 45, T2D 62 mg/dL. Random forest MAE 31.5 (R2 +0.30)"* | Generated by `src/train_meal.py` on 1,246 isolated meals from `data/processed/cgmacros_all.csv.gz` | ✅ Supported |
| [`app/sim_ui/assumptions_view.py:113`](file:///home/luffy/strawhats_AITPune/app/sim_ui/assumptions_view.py#L113) | *"Every parameter is an explicit assumption, not learned from data unless empirically calibrated as noted."* | Fully enumerated in `src/sim/assumptions.py` with rationales | ✅ Supported |
| [`app/sim_ui/patient_view.py:358`](file:///home/luffy/strawhats_AITPune/app/sim_ui/patient_view.py#L358) | *"Simplified simulated sleep stages. The real CGMacros data has no sleep-stage recordings, so this is not validated against real data."* | Confirmed in `docs/SIM_BRIEF.md` and `src/sim/store.py` (Rule 2) | ✅ Supported |
| [`app/sim_ui/theme.py:192-195`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L192-L195) | *"hr_val = '78', hr_sub = 'Optical sensor', hr_badge = 'REAL'"* | Hardcoded string in Python code; not extracted from participant's HR time-series | ❌ **Unsupported Claim** |

---

## 7. Automated Consistency Test Suite

To enable reproducible verification, we created [`tests/test_consistency.py`](file:///home/luffy/strawhats_AITPune/tests/test_consistency.py) containing 10 automated test cases:
1. `test_preset_simulator_recomputation_and_lipid_check[active_38_early_disease]`: PASS
2. `test_preset_simulator_recomputation_and_lipid_check[lean_high_genetic_risk]`: PASS
3. `test_preset_simulator_recomputation_and_lipid_check[older_metformin_high_cholesterol]`: PASS
4. `test_preset_simulator_recomputation_and_lipid_check[poorly_controlled_55_sleep_deprived]`: PASS
5. `test_preset_simulator_recomputation_and_lipid_check[sedentary_night_shift_worker]`: PASS
6. `test_preset_simulator_recomputation_and_lipid_check[well_controlled_45]`: PASS
7. `test_provenance_labels_virtual_presets`: PASS
8. `test_provenance_labels_custom_patient`: PASS
9. `test_provenance_labels_real_patient_lacking_fields`: PASS
10. `test_audit_real_patient_heart_rate_card_flag`: PASS

**Test Execution:** Run via `.venv/bin/pytest tests/test_consistency.py` ($10\text{ passed in }0.71\text{s}$).

---

## 8. Ranked List of Problems Found

Ranked from highest to lowest severity:

### Priority 1: High Severity — Hard-Coded Heart Rate Labeled REAL
- **File & Line:** [`app/sim_ui/theme.py:192-196`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L192-L196)
- **Problem:** For all 45 human study participants on the Real Reference Patients page, the heart rate summary card renders `hr_val = "78"`, `hr_sub = "Optical sensor"`, and `hr_badge = badge_html("REAL")`.
- **Impact:** Violates Honesty Rule 1 and Rule 2. Clinicians and reviewers are shown an identical static number (78 bpm) labeled as verified real physiological data rather than the participant's actual mean heart rate or an unmeasured placeholder.
- **Proposed Remedy (when authorized):** Read the actual mean heart rate from `cgm_df["hr"].mean()` for the participant, or if CGM telemetry is not loaded, display `"NOT AVAILABLE"`.

### Priority 2: Medium Severity — Provenance Helper Default Inconsistency
- **File & Line:** [`src/sim/store.py:521`](file:///home/luffy/strawhats_AITPune/src/sim/store.py#L521)
- **Problem:** In `get_provenance_map()`, when `is_real=True`, non-lacking fields default to `"USER-ENTERED"` (`prov[f] = "USER-ENTERED" if f in user_set else "USER-ENTERED"`) instead of `"REAL"`.
- **Impact:** Any programmatic consumer calling `get_provenance_map` for real participants receives inaccurate provenance tags, though page-level UI code currently overrides this directly.
- **Proposed Remedy (when authorized):** Set `prov[f] = "REAL"` when `is_real=True` and `f not in REAL_DATASET_LACKING_FIELDS`.

### Priority 3: Medium Severity — 7-Day vs 24-Hour Metric Card Label Ambiguity
- **File & Line:** [`app/sim_ui/theme.py:237-239`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L237-L239) and [`app/sim_ui/patient_view.py:101`](file:///home/luffy/strawhats_AITPune/app/sim_ui/patient_view.py#L101)
- **Problem:** The summary card renders `glu_sub = f"Mean {mean_glu:.0f} · TIR {tir_val:.0f}%"`, which averages the entire 7-day simulation. Directly below, the page features a 24-hour evaluation date picker and 24-hour trajectory charts.
- **Impact:** For Well-Controlled 45yo, the 7-day TIR is $83.2\%$, while the displayed day's 24-hour TIR is $93.4\%$ (and Day 1 is $95.8\%$). Users assume the card reflects the selected day.
- **Proposed Remedy (when authorized):** Label the subtitle explicitly as `"7-Day Mean 84 · 7-Day TIR 83%"` or compute it for the active 24-hour window.

### Priority 4: Low Severity — Fallback Hard-Coded Placeholders
- **File & Line:** [`app/sim_ui/theme.py:255-261`](file:///home/luffy/strawhats_AITPune/app/sim_ui/theme.py#L255-L261)
- **Problem:** Hard-coded static fallback numbers (`"74"` HR, `"38"` HRV, static array sparklines) exist if `simulation_df is None`.
- **Impact:** Dormant under standard application flow (since simulations are cached and present), but represents unreachable dead fallback constants.
- **Proposed Remedy (when authorized):** Replace static arrays with dynamic calculations or clean `"—"` empty states.
