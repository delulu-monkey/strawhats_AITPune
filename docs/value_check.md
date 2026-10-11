# Virtual Patient Simulation Value Consistency Check

**Document:** `docs/value_check.md`  
**Date:** October 12, 2026  
**Scope:** Consistency analysis of laboratory inputs, simulated baselines, estimated average glucose (eAG), time in range (TIR), and hypoglycemia across all 6 virtual patient presets.

---

## 1. Summary Comparison Table

Estimated Average Glucose (eAG) is computed using the Nathan et al. (ADAG) consensus formula:
$$\text{eAG (mg/dL)} = 28.7 \times \text{HbA1c} - 46.7$$

| Preset ID | Preset Name | Age / Sex | BMI (kg/m²) | HbA1c (%) | Lab Value (entered) Fasting Glu (mg/dL) | Simulated Overnight Baseline (mg/dL) | eAG (mg/dL) | 24h Mean Glucose (mg/dL) | Diff vs eAG (mg/dL) | 24h TIR 70–180 (%) | 24h TBR <70 (%) | 7-day Mean Glu (mg/dL) | 7-day TIR (%) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `well_controlled_45` | **Well-Controlled 45yo** | 45 / M | 23.7 | 5.4 | 92.0 | 76.6 | 108.3 | 81.4 | **-26.8** | **78.5%** | **21.5%** | 84.0 | 81.8% |
| `active_38_early_disease` | **Active 38yo (Early Prediabetes)** | 38 / F | 24.2 | 5.9 | 104.0 | 89.5 | 122.6 | 98.3 | **-24.3** | 96.9% | 3.1% | 100.6 | 97.4% |
| `lean_high_genetic_risk` | **Lean Patient with High Genetic Risk** | 34 / F | 20.8 | 6.1 | 112.0 | 95.1 | 128.4 | 112.3 | **-16.1** | 94.8% | 0.3% | 107.1 | 98.7% |
| `older_metformin_high_cholesterol` | **Older Patient on Metformin** | 68 / M | 27.6 | 7.3 | 134.0 | 124.8 | 162.8 | 136.8 | **-26.0** | 96.5% | 0.0% | 139.9 | 95.0% |
| `poorly_controlled_55_sleep_deprived` | **Poorly-Controlled 55yo** | 55 / M | 32.0 | 8.8 | 168.0 | 162.6 | 205.9 | 204.7 | -1.2 | 46.9% | 0.0% | 197.3 | 40.0% |
| `sedentary_night_shift_worker` | **Sedentary Night-Shift Worker** | 42 / F | 28.7 | 6.4 | 118.0 | 102.6 | 137.0 | 119.2 | **-17.8** | 98.3% | 0.0% | 119.4 | 97.0% |

---

## 2. In-Depth Analysis: "Well-Controlled 45yo"

- **Profile Fasting Glucose (Lab Value Entered):** `92.0 mg/dL`
- **Simulator Fasting Baseline (`effective_fasting_glucose`):** `76.6 mg/dL` (exact: `76.556 mg/dL`)
- **24-Hour Mean Glucose:** `81.4 mg/dL` (7-day mean: `84.0 mg/dL`)
- **Time in Range (70–180 mg/dL):** `78.5%` (7-day TIR: `81.8%`)
- **% Time Below 70 mg/dL (Hypoglycemia / TBR):** `21.5%` (7-day TBR: `18.2%`)
- **Minimum Simulated Value:** `45.9 mg/dL` (severe level 2 hypoglycemia)
- **HbA1c:** `5.4%`
- **Estimated Average Glucose (eAG):** $28.7 \times 5.4 - 46.7 = 108.3\text{ mg/dL}$
- **Comparison to Simulated Mean:** Simulated 24h mean is **26.8 mg/dL lower than eAG** ($81.4 - 108.3 = -26.8$).

### Clinical Assessment for Well-Controlled 45yo
For a normoglycemic 45-year-old with HbA1c 5.4%:
1. Standard clinical targets for non-diabetic/healthy individuals mandate **TIR > 90%** (typically > 95%) and **TBR < 4%** (level 1 < 70 mg/dL) and **< 1%** (level 2 < 54 mg/dL).
2. The current simulation exhibits **21.5% TBR** with Nadir at **45.9 mg/dL**, representing non-physiological chronic hypoglycemia.
3. The 24-hour mean of 81.4 mg/dL is depressed by 26.8 mg/dL compared to clinical expectation (eAG = 108.3 mg/dL).

---

## 3. Discrepancy & Root Cause Analysis

### A. Presets with Simulated Mean > 15 mg/dL Below eAG
5 out of 6 presets have a simulated mean more than 15 mg/dL below eAG:
1. `well_controlled_45`: **-26.8 mg/dL** below eAG (-24.3 mg/dL over 7 days)
2. `active_38_early_disease`: **-24.3 mg/dL** below eAG (-22.0 mg/dL over 7 days)
3. `older_metformin_high_cholesterol`: **-26.0 mg/dL** below eAG (-22.9 mg/dL over 7 days)
4. `sedentary_night_shift_worker`: **-17.8 mg/dL** below eAG (-17.5 mg/dL over 7 days)
5. `lean_high_genetic_risk`: **-16.1 mg/dL** below eAG (-21.3 mg/dL over 7 days)

*(Only `poorly_controlled_55_sleep_deprived` matches closely at -1.2 mg/dL below eAG, because high insulin resistance and large postprandial excursions elevate the mean).*

### B. Healthy Preset with TIR < 90%
- `well_controlled_45` has TIR = **78.5%**, failing the healthy clinical threshold of $\ge 90\%$.

### C. Underlying Constants Responsible

The discrepancy is driven by a combination of baseline suppression and stochastic noise:

1. **Fasting Glucose Baseline Model (`src/sim/assumptions.py` & `src/sim/profile.py`):**
   - Constant: `FASTING_GLUCOSE_INTERCEPT = -43.0` (line 19)
   - Constant: `FASTING_GLUCOSE_HBA1C_SLOPE = 22.0` (line 22)
   - `effective_fasting_glucose` calculates:
     $$\text{Baseline} = -43.0 + (22.0 \times \text{HbA1c}) + [6.0 \times \max(0, \text{IR} - 1.0)]$$
   - For `well_controlled_45` (HbA1c 5.4, IR 1.126):
     $$\text{Baseline} = -43.0 + 118.8 + 0.756 = 76.56\text{ mg/dL}$$
   - This suppresses the resting baseline to ~76.6 mg/dL, even though the preset's laboratory profile specifies `fasting_glucose = 92.0 mg/dL`.
   - Because inter-meal glucose decays back to this baseline with half-life `GLUCOSE_RETURN_HALFLIFE_MIN = 25.0` min, the virtual patient spends the majority of 24 hours hovering around ~76–80 mg/dL.

2. **Sensor Noise Process (`src/sim/assumptions.py`):**
   - Constant: `SENSOR_NOISE_SD = 8.5` (line 145)
   - Constant: `SENSOR_AR1_PHI = 0.72` (line 142)
   - The stationary standard deviation of this AR(1) process is:
     $$\sigma = \frac{\text{SENSOR\_NOISE\_SD}}{\sqrt{1 - \phi^2}} = \frac{8.5}{\sqrt{1 - 0.72^2}} \approx 12.25\text{ mg/dL}$$
   - When the baseline is only 76.6 mg/dL, a standard 1-$\sigma$ downward fluctuation reaches $76.6 - 12.25 = 64.3\text{ mg/dL}$ (< 70 mg/dL), and a 2-$\sigma$ dip plunges to $52.1\text{ mg/dL}$.
   - Coupled with `ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS = 2.0` (lowering daytime glucose by up to 5 mg/dL during walking epochs), this causes frequent and prolonged dips into the hypoglycemic range (21.5% of the day).

3. **Decoupling between Profile Lab Test and Simulator Intercept:**
   - In `src/sim/simulator.py` (line 166):
     `fasting_base = profile.effective_fasting_glucose`
   - The simulator ignores the entered `patient.fasting_glucose` (e.g. 92.0 mg/dL) and instead generates a synthetic baseline from the `-43.0 + 22.0 * HbA1c` formula.

---

## 4. Proposed Fixes (Report Only — Not Yet Applied)

To eliminate the artificial hypoglycemia and align simulated means with eAG and clinical targets, three potential options are available:

### Option A: Direct Alignment with Profile Fasting Glucose (Recommended)
- **Change:** In `src/sim/simulator.py`, update `fasting_base`:
  ```python
  fasting_base = profile.fasting_glucose
  ```
  *(or anchor `profile.effective_fasting_glucose` to `self.fasting_glucose` plus minor adjustments for acute sleep debt and medications).*
- **Impact on `well_controlled_45`:**
  - Baseline shifts from 76.6 mg/dL to 92.0 mg/dL.
  - 1-$\sigma$ sensor noise lower bound becomes $92.0 - 12.25 = 79.75\text{ mg/dL}$ (safely above 70 mg/dL).
  - 24h Mean glucose increases to ~98–101 mg/dL (within 7–10 mg/dL of eAG 108.3 mg/dL).
  - **TIR increases to > 98%**, and **TBR drops to < 1.0%**, perfectly matching clinical norms.

### Option B: Recalibrate `assumptions.py` Linear Fasting Model
- **Change:** Adjust linear parameters in `src/sim/assumptions.py`:
  - `FASTING_GLUCOSE_INTERCEPT`: change from `-43.0` to `-28.0` mg/dL.
  - `FASTING_GLUCOSE_HBA1C_SLOPE`: change from `22.0` to `21.0` mg/dL per %.
- **Impact:**
  - For HbA1c 5.4%: $-28.0 + 21.0 \times 5.4 = 85.4\text{ mg/dL}$ (with IR adder: ~86.2 mg/dL).
  - For HbA1c 7.3%: $-28.0 + 21.0 \times 7.3 = 125.3\text{ mg/dL}$.
  - Reduces the eAG gap across all presets while keeping healthy TIR $\ge 92\%$.

### Option C: Calibrate Sensor Noise SD
- **Change:** Reduce `SENSOR_NOISE_SD` from `8.5` to `5.5` or `6.0` mg/dL.
- **Impact:**
  - Narrows the stationary noise spread from $\pm 12.25\text{ mg/dL}$ to $\pm 8.0\text{ mg/dL}$, significantly blunting spurious nocturnal dips below 70 mg/dL while preserving physiological CGM noise characteristics.

---

## 5. UI Adaptations Completed

1. **Clear Distinctions for Fasting Glucose:**
   - In `app/sim_ui/patient_view.py` and `app/sim_ui/theme.py`, the two values are explicitly separated and labeled:
     - **"Lab Value (entered)"**: `patient.fasting_glucose` (e.g., 92 mg/dL) — the static clinical lab panel result.
     - **"Simulated Overnight Baseline"**: `patient.effective_fasting_glucose` (e.g., 77 mg/dL) — the modeled baseline used by the simulator differential equations.
2. **BMI Rounding to 1 Decimal Place Everywhere:**
   - Sidebar patient card for simulated/preset patients: `BMI {bmi:.1f}`.
   - Sidebar patient card for real reference participants: `BMI {bmi:.1f}` (formerly displayed raw floats like `26.94868993`).
   - `load_real_bio_data()` in `app/sim_ui/common.py`: rounds `df["bmi"]` to 1 decimal place upon ingestion.

---

## 6. Before vs. After Calibration: All 6 Virtual Patient Presets

Following Step 2 implementation:
1. Overnight baseline is anchored to the patient's entered laboratory fasting glucose (`patient.fasting_glucose`) plus documented physiological adders (insulin resistance excess, sleep debt, medication). When no fasting glucose is entered, it derives from HbA1c via the fitted real-data regression: $-57.91 + 29.17 \times \text{HbA1c}$ (derived from `bio.csv`, $R^2 = 0.768$).
2. Interstitial sensor noise is calibrated to real within-person 5-minute FreeStyle Libre dynamics: `SENSOR_AR1_PHI = 0.97` (real median: 0.97) and `SENSOR_NOISE_SD = 3.3 mg/dL` (real median: 3.31 mg/dL), replacing the previous arbitrary jump parameters ($0.72$ and $8.5\text{ mg/dL}$).

### Table 6.1: Metric Comparison (Before vs. After, 7-Day Simulation)

| Preset ID | Metric | Before Calibration | After Calibration | Delta | Clinical / Physiological Interpretation |
| :--- | :--- | :---: | :---: | :---: | :--- |
| `well_controlled_45`<br>(HbA1c 5.4%, Lab FG 92.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 76.6 mg/dL<br>~76 mg/dL<br>84.0 mg/dL<br>81.8%<br>18.2%<br>0.0%<br>45.9 mg/dL | **92.8 mg/dL**<br>**97.7 mg/dL**<br>**100.4 mg/dL**<br>**99.6%**<br>**0.45%**<br>**0.00%**<br>**62.8 mg/dL** | +16.2 mg/dL<br>+21.7 mg/dL<br>+16.4 mg/dL<br>+17.8%<br>-17.75%<br>0.0%<br>+16.9 mg/dL | Baseline elevated to entered lab level (92 mg/dL). Severe hypoglycemia (TBR 18.2%, nadir 45.9 mg/dL) completely eliminated. TIR normalized to 99.6%. |
| `active_38_early_disease`<br>(HbA1c 5.9%, Lab FG 104.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 89.5 mg/dL<br>~89 mg/dL<br>100.6 mg/dL<br>97.4%<br>2.6%<br>0.0%<br>52.8 mg/dL | **106.7 mg/dL**<br>**105.7 mg/dL**<br>**118.2 mg/dL**<br>**97.7%**<br>**0.00%**<br>**0.00%**<br>**75.1 mg/dL** | +17.2 mg/dL<br>+16.7 mg/dL<br>+17.6 mg/dL<br>+0.3%<br>-2.6%<br>0.0%<br>+22.3 mg/dL | Anchored to entered fasting glucose (104 mg/dL). Postprandial peaks shift mean upward. Overnight mean matches real prediabetes reference IQR. |
| `lean_high_genetic_risk`<br>(HbA1c 6.1%, Lab FG 112.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 95.1 mg/dL<br>~95 mg/dL<br>107.1 mg/dL<br>98.7%<br>0.3%<br>0.0%<br>61.2 mg/dL | **115.9 mg/dL**<br>**118.8 mg/dL**<br>**126.8 mg/dL**<br>**97.5%**<br>**0.00%**<br>**0.00%**<br>**85.0 mg/dL** | +20.8 mg/dL<br>+23.8 mg/dL<br>+19.7 mg/dL<br>-1.2%<br>-0.3%<br>0.0%<br>+23.8 mg/dL | Elevated fasting baseline reflects genetic IR and entered 112 mg/dL lab test. No hypoglycemia. |
| `older_metformin_high_cholesterol`<br>(HbA1c 7.3%, Lab FG 134.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 124.8 mg/dL<br>~125 mg/dL<br>139.9 mg/dL<br>95.0%<br>0.0%<br>0.0%<br>88.4 mg/dL | **141.2 mg/dL**<br>**143.4 mg/dL**<br>**157.0 mg/dL**<br>**87.2%**<br>**0.00%**<br>**0.00%**<br>**106.8 mg/dL** | +16.4 mg/dL<br>+18.4 mg/dL<br>+17.1 mg/dL<br>-7.8%<br>0.0%<br>0.0%<br>+18.4 mg/dL | Reflects entered 134 mg/dL lab fasting value minus metformin reduction, with elevated postprandial excursions. |
| `poorly_controlled_55_sleep_deprived`<br>(HbA1c 8.8%, Lab FG 168.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 162.6 mg/dL<br>~163 mg/dL<br>197.3 mg/dL<br>40.0%<br>0.0%<br>0.0%<br>132.5 mg/dL | **180.0 mg/dL**<br>**188.5 mg/dL**<br>**214.4 mg/dL**<br>**12.9%**<br>**0.00%**<br>**0.00%**<br>**158.6 mg/dL** | +17.4 mg/dL<br>+25.5 mg/dL<br>+17.1 mg/dL<br>-27.1%<br>0.0%<br>0.0%<br>+26.1 mg/dL | Severe hyperglycemia driven by HbA1c 8.8%, entered FG 168 mg/dL, and chronic sleep deficit (+7.5 mg/dL morning adder, +10% IR). |
| `sedentary_night_shift_worker`<br>(HbA1c 6.4%, Lab FG 118.0) | **Overnight Baseline**<br>**Overnight Mean**<br>**7-Day Mean Glucose**<br>**TIR 70–180 mg/dL**<br>**TBR < 70 mg/dL**<br>**TBR < 54 mg/dL**<br>**Min Glucose** | 102.6 mg/dL<br>~103 mg/dL<br>119.4 mg/dL<br>97.0%<br>0.0%<br>0.0%<br>74.1 mg/dL | **122.8 mg/dL**<br>**146.0 mg/dL**<br>**137.5 mg/dL**<br>**94.9%**<br>**0.00%**<br>**0.00%**<br>**76.0 mg/dL** | +20.2 mg/dL<br>+43.0 mg/dL<br>+18.1 mg/dL<br>-2.1%<br>0.0%<br>0.0%<br>+1.9 mg/dL | Inverted sleep-wake window and severe sleep debt (5.0h sleep) shifts nocturnal glucose. TIR remains well within clinical prediabetic ranges. |

---

## 7. Acceptance Criteria Evaluation (Step 3: Real CGMacros IQR Benchmarking)

As specified in STEP 3, presets are mapped to real reference groups by HbA1c:
- **Healthy:** $\text{HbA1c} < 5.7\%$
- **Prediabetes:** $5.7\% \le \text{HbA1c} \le 6.4\%$
- **Type 2 Diabetes (T2D):** $\text{HbA1c} \ge 6.5\%$

Acceptance Rule: Simulated 7-day mean, TIR 70–180, % below 70, and overnight mean must fall within the real 25th–75th percentile of the matching cohort from `docs/real_glucose_reference.md`.

### Reference Target Bands (Real CGMacros Libre Sensors):
- **Healthy (N=15):** 24h Mean `[77.8 – 89.8]`, TIR `[66.4 – 92.9]%`, TBR<70 `[3.6 – 33.6]%`, Overnight Mean `[67.7 – 86.4]` mg/dL
- **Prediabetes (N=16):** 24h Mean `[93.5 – 116.1]`, TIR `[89.1 – 97.1]%`, TBR<70 `[0.3 – 7.5]%`, Overnight Mean `[89.2 – 111.0]` mg/dL
- **T2D (N=14):** 24h Mean `[112.3 – 155.4]`, TIR `[74.5 – 94.8]%`, TBR<70 `[0.0 – 1.3]%`, Overnight Mean `[101.0 – 134.2]` mg/dL

### Preset Evaluation Summary Table:

| Preset Name | Group (by HbA1c) | 24h Mean (Target IQR) | TIR 70–180 (Target IQR) | TBR < 70 (Target IQR) | Overnight Mean (Target IQR) | Overall Acceptance Result | Primary Reason for Non-Pass |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Well-Controlled 45yo** | Healthy<br>(5.4%) | **100.4**<br>[77.8 – 89.8]<br>❌ Fail | **99.6%**<br>[66.4 – 92.9]%<br>❌ Fail | **0.45%**<br>[3.6 – 33.6]%<br>❌ Fail | **97.7**<br>[67.7 – 86.4]<br>❌ Fail | ❌ **FAIL** | Entered lab fasting glucose is 92.0 mg/dL (venous blood draw). Real FreeStyle Libre sensors read 73.4 mg/dL overnight in healthy subjects. Anchoring to entered lab glucose places baseline ~15–20 mg/dL above real interstitial sensor levels. |
| **Active 38yo** | Prediabetes<br>(5.9%) | **118.2**<br>[93.5 – 116.1]<br>❌ Fail | **97.7%**<br>[89.1 – 97.1]%<br>❌ Fail | **0.00%**<br>[0.3 – 7.5]%<br>❌ Fail | **105.7**<br>[89.2 – 111.0]<br>✅ **PASS** | ❌ **FAIL** | Overnight mean passes IQR! 24h mean (118.2) is slightly above 75th percentile (116.1) due to normal meal rises. Zero hypoglycemia because baseline is anchored to 104 mg/dL venous lab. |
| **Lean High Genetic Risk** | Prediabetes<br>(6.1%) | **126.8**<br>[93.5 – 116.1]<br>❌ Fail | **97.5%**<br>[89.1 – 97.1]%<br>❌ Fail | **0.00%**<br>[0.3 – 7.5]%<br>❌ Fail | **118.8**<br>[89.2 – 111.0]<br>❌ Fail | ❌ **FAIL** | Entered lab fasting glucose is 112 mg/dL plus high polygenic risk score, shifting both overnight (118.8) and 24h mean (126.8) above the 75th percentile of the mild prediabetes cohort. |
| **Sedentary Night-Shift** | Prediabetes<br>(6.4%) | **137.5**<br>[93.5 – 116.1]<br>❌ Fail | **94.9%**<br>[89.1 – 97.1]%<br>✅ **PASS** | **0.00%**<br>[0.3 – 7.5]%<br>❌ Fail | **146.0**<br>[89.2 – 111.0]<br>❌ Fail | ❌ **FAIL** | TIR passes IQR cleanly! Overnight mean is elevated because patient works night shifts and has chronic sleep debt (typical sleep 5.0h), adding morning glucose and nocturnal wake activity. |
| **Older Metformin** | T2D<br>(7.3%) | **157.0**<br>[112.3 – 155.4]<br>❌ Fail | **87.2%**<br>[74.5 – 94.8]%<br>✅ **PASS** | **0.00%**<br>[0.0 – 1.3]%<br>✅ **PASS** | **143.4**<br>[101.0 – 134.2]<br>❌ Fail | ❌ **FAIL** | TIR and TBR both PASS! 24h mean (157.0) is just 1.6 mg/dL above the 75th percentile (155.4) of the CGMacros T2D group. |
| **Poorly-Controlled 55yo** | T2D<br>(8.8%) | **214.4**<br>[112.3 – 155.4]<br>❌ Fail | **12.9%**<br>[74.5 – 94.8]%<br>❌ Fail | **0.00%**<br>[0.0 – 1.3]%<br>✅ **PASS** | **188.5**<br>[101.0 – 134.2]<br>❌ Fail | ❌ **FAIL** | TBR passes! 24h mean (214.4) and overnight mean (188.5) exceed the CGMacros study 75th percentile because this patient's HbA1c is 8.8% with entered FG 168 mg/dL, whereas the real CGMacros T2D study cohort median HbA1c was only 7.1% (study maximum was 8.5%). |

### Honest Scientific Reporting Summary
- In strict adherence to **SIM_BRIEF Honesty Rules** and the prompt's instruction (*"If a preset cannot meet this, report which one and why. Do not tune to force a pass without reporting it"*), no constants were artificially altered to force presets into population IQRs.
- The root discrepancy is that presets represent specific clinical personas whose **entered fasting glucose is a venous plasma laboratory measurement** (e.g. 92.0 mg/dL for healthy, 168.0 mg/dL for poorly controlled T2D), whereas the target IQRs from Step 1 are derived from **interstitial Abbott FreeStyle Libre sensors**, which exhibit nocturnal interstitial attenuation, sensor compression, and perfusion lag (~15–20 mg/dL lower overnight).
- Furthermore, extreme phenotypes like `poorly_controlled_55_sleep_deprived` (HbA1c 8.8%) clinically lie in severe sustained hyperglycemia, which naturally falls outside the middle 50% of the mildly diabetic CGMacros cohort.
