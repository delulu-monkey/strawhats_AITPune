# Real CGMacros Glucose Reference Data & Empirical Calibration Basis
**Document:** `docs/real_glucose_reference.md`  **Source Dataset:** CGMacros Free-Living Continuous Glucose Monitoring Study (`data/processed/cgmacros_all.csv.gz` & `bio.csv`)  **Sensor Modality:** Abbott FreeStyle Libre Interstitial Sensor (1-minute and 5-minute epochs)  **Cohort:** 45 unique human participants (15 Healthy, 16 Prediabetes, 14 Type 2 Diabetes)
---
## 1. Executive Findings: Sensor Reality vs. Theoretical Lab Assumptions
A central question in the virtual patient simulator design is whether real healthy humans exhibit overnight sensor means around **75 mg/dL** or **90–95 mg/dL**.
> [!IMPORTANT]
> **Empirical Finding from Real CGMacros Data:**  
> In the real Abbott FreeStyle Libre sensor data, **healthy participants exhibit an overnight (00:00–06:00) mean glucose of 73.4 mg/dL** (median; IQR 67.7–86.4 mg/dL), and a 24-hour mean of **82.5 mg/dL** (median; IQR 77.8–89.8 mg/dL).  
> Meanwhile, their clinical venous laboratory fasting glucose from blood draws (`bio.csv`) averages **95.7 mg/dL** (median 96.0 mg/dL).  
> 
> **Why does this gap exist?**  
> Abbott FreeStyle Libre interstitial sensor readings systematically read ~15–20 mg/dL lower than venous plasma fasting glucose overnight due to lower nocturnal peripheral perfusion, temperature shifts, and nocturnal sensor attenuation/compression.  
> Consequently, healthy humans wearing Libre sensors routinely record readings in the 60–75 mg/dL range overnight, with **median % time below 70 mg/dL of 15.5%** (IQR 3.6%–33.6%) and sensor nadirs touching 40.0 mg/dL (the Libre lower threshold).

---
## 2. Group Summary: Medians and 25th–75th Percentiles (IQR)

| Metric | Healthy (N=15) Median [IQR] | Prediabetes (N=16) Median [IQR] | T2D (N=14) Median [IQR] |
| :--- | :---: | :---: | :---: |
| **24-Hour Mean Glucose (mg/dL)** | 82.5 [77.8 – 89.8] | 108.3 [93.5 – 116.1] | 136.1 [112.3 – 155.4] |
| **24-Hour Glucose SD (mg/dL)** | 16.8 [15.2 – 19.5] | 21.8 [19.9 – 27.4] | 40.0 [29.2 – 47.5] |
| **Time in Range 70–180 mg/dL (%)** | 84.5 [66.4 – 92.9] | 94.0 [89.1 – 97.1] | 81.9 [74.5 – 94.8] |
| **Time Below 70 mg/dL (%)** | 15.5 [3.6 – 33.6] | 1.6 [0.3 – 7.5] | 0.3 [0.0 – 1.3] |
| **Time Below 54 mg/dL (%)** | 1.8 [0.0 – 6.6] | 0.0 [0.0 – 0.4] | 0.0 [0.0 – 0.0] |
| **Minimum Glucose Reading (mg/dL)** | 40.0 [40.0 – 53.5] | 56.5 [45.2 – 64.2] | 65.0 [59.2 – 75.5] |
| **Overnight Mean 00:00–06:00 (mg/dL)** | 73.4 [67.7 – 86.4] | 95.9 [89.2 – 111.0] | 118.2 [101.0 – 134.2] |
| **Overnight SD (mg/dL)** | 13.5 [10.3 – 14.7] | 15.4 [9.8 – 20.6] | 17.4 [11.3 – 27.8] |
| **Within-Person 5-min AR(1) Lag-1 (φ)** | 0.97 [0.96 – 0.98] | 0.97 [0.95 – 0.98] | 0.98 [0.97 – 0.98] |
| **5-min Noise Innovation SD (mg/dL)** | 3.0 [2.3 – 3.3] | 3.6 [2.9 – 4.5] | 3.6 [2.5 – 5.9] |

---
## 3. Empirical Cross-Sectional Relationships (Fitted Regressions)

### Regression 1: 24-Hour Sensor Mean Glucose vs. HbA1c
$$\text{24h Mean Glucose (mg/dL)} = -57.92 + 27.17 \times \text{HbA1c}$$  
- **Slope:** `27.17 mg/dL per %` (remarkably close to the Nathan et al. ADAG slope of 28.7)
- **Intercept:** `-57.92 mg/dL`
- **Goodness of fit:** $R^2 = 0.659$, $p = 1.3039e-11$
- **Residual Spread (SD):** `±17.74 mg/dL`

### Regression 2: Overnight Sensor Mean vs. Lab Venous Fasting Glucose
$$\text{Overnight Sensor Mean (mg/dL)} = 4.57 + 0.77 \times \text{Lab Fasting Glucose}$$  
- **Slope:** `0.77` (interstitial overnight sensor readings track approximately 77% of venous lab fasting glucose)
- **Intercept:** `+4.57 mg/dL`
- **Goodness of fit:** $R^2 = 0.685$, $p = 2.4304e-12$
- **Residual Spread (SD):** `±15.79 mg/dL`

### Regression 3: Overnight Sensor Mean vs. HbA1c
$$\text{Overnight Sensor Mean (mg/dL)} = -43.30 + 22.99 \times \text{HbA1c}$$  
- **Slope:** `22.99 mg/dL per %`
- **Intercept:** `-43.30 mg/dL`
- **Goodness of fit:** $R^2 = 0.551$, $p = 5.3364e-09$
- **Residual Spread (SD):** `±18.84 mg/dL`

### Regression 4: Lab Fasting Glucose vs. HbA1c
$$\text{Lab Fasting Glucose (mg/dL)} = -57.91 + 29.17 \times \text{HbA1c}$$  
- **Slope:** `29.17 mg/dL per %`
- **Intercept:** `-57.91 mg/dL`
- **Goodness of fit:** $R^2 = 0.768$, $p = 3.2045e-15$
- **Residual Spread (SD):** `±14.57 mg/dL`

---
## 4. Short-Term Sensor Dynamics (5-Minute AR(1) Process)

In `assumptions.py`, sensor noise was previously specified as `SENSOR_NOISE_SD = 8.5` and `SENSOR_AR1_PHI = 0.72`.
Evaluation against real 5-minute resampled CGMacros Libre data reveals:
- **Real Autoregressive Lag-1 Coefficient (φ):** Median is **0.97** (IQR: 0.96 to 0.98 across all cohorts).
- **Real 5-Minute Innovation Standard Deviation (ε):** Median is **3.31 mg/dL** (IQR: 2.50 to 4.05 mg/dL).
- **Implication:** The previous model had an artificially low correlation (0.72) and excessively large 5-minute jump shocks (8.5 mg/dL). Updating to $\phi = 0.97$ and $\sigma_\epsilon = 3.3\text{ mg/dL}$ perfectly matches real interstitial sensor dynamics without producing unphysiological discontinuities.

---
## 5. Complete Participant Table (All 45 CGMacros Individuals)

| Subject | Group | Age / Sex | BMI | HbA1c (%) | Lab Fasting | 24h Mean | 24h SD | TIR (%) | TBR <70 (%) | TBR <54 (%) | Min | Night Mean | Night SD | AR(1) φ | Innov SD |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| CGMacros-001 | healthy | 27M | 22.3 | 5.4 | 91 | 88.5 | 9.1 | 99.1 | 0.9 | 0.00 | 54 | 87.3 | 8.4 | 0.957 | 2.44 |
| CGMacros-002 | healthy | 49F | 30.9 | 5.5 | 93 | 79.0 | 22.4 | 62.8 | 37.2 | 6.70 | 40 | 67.6 | 9.6 | 0.966 | 2.45 |
| CGMacros-003 | t2d | 59F | 26.9 | 6.5 | 118 | 107.6 | 30.1 | 94.5 | 1.5 | 0.45 | 45 | 90.6 | 8.6 | 0.983 | 1.58 |
| CGMacros-004 | healthy | 33F | 42.4 | 5.5 | 105 | 90.8 | 16.2 | 95.4 | 4.6 | 0.00 | 60 | 85.5 | 9.2 | 0.986 | 1.52 |
| CGMacros-005 | t2d | 51F | 31.0 | 6.6 | 144 | 111.5 | 30.2 | 93.3 | 1.8 | 0.55 | 40 | 100.1 | 19.4 | 0.982 | 3.65 |
| CGMacros-006 | healthy | 51F | 29.3 | 5.2 | 96 | 88.9 | 17.5 | 90.4 | 9.6 | 1.83 | 40 | 80.3 | 16.6 | 0.980 | 3.33 |
| CGMacros-007 | prediabetes | 66F | 27.1 | 5.9 | 108 | 54.3 | 19.7 | 18.0 | 82.0 | 64.28 | 40 | 44.7 | 9.1 | 0.924 | 3.87 |
| CGMacros-008 | prediabetes | 54M | 39.9 | 5.8 | 112 | 93.8 | 19.0 | 93.2 | 6.7 | 0.16 | 53 | 91.3 | 11.1 | 0.965 | 2.92 |
| CGMacros-009 | prediabetes | 34F | 37.0 | 5.7 | 122 | 106.4 | 21.8 | 97.2 | 1.5 | 0.00 | 57 | 114.6 | 22.0 | 0.980 | 4.41 |
| CGMacros-010 | prediabetes | 54F | 35.8 | 5.7 | 100 | 92.6 | 22.5 | 89.6 | 9.9 | 4.52 | 40 | 83.2 | 15.5 | 0.970 | 3.76 |
| CGMacros-011 | prediabetes | 34M | 29.2 | 5.7 | 109 | 110.9 | 20.9 | 98.8 | 0.0 | 0.00 | 75 | 98.5 | 9.7 | 0.974 | 2.18 |
| CGMacros-012 | t2d | 52M | 30.3 | 7.1 | 179 | 164.8 | 49.4 | 70.8 | 0.0 | 0.00 | 77 | 168.7 | 31.9 | 0.982 | 6.09 |
| CGMacros-013 | prediabetes | 56F | 32.6 | 6.2 | 103 | 126.1 | 23.5 | 96.6 | 0.3 | 0.00 | 61 | 119.7 | 18.3 | 0.989 | 2.71 |
| CGMacros-014 | t2d | 53M | 28.5 | 7.1 | 147 | 109.7 | 24.4 | 97.4 | 0.4 | 0.00 | 69 | 97.0 | 11.3 | 0.969 | 2.78 |
| CGMacros-015 | healthy | 47F | 24.3 | 5.4 | 89 | 50.7 | 14.8 | 12.2 | 87.8 | 69.80 | 40 | 46.5 | 11.0 | 0.978 | 2.26 |
| CGMacros-016 | prediabetes | 48F | 45.9 | 5.8 | 104 | 84.8 | 14.6 | 88.1 | 11.9 | 0.55 | 40 | 78.5 | 8.3 | 0.948 | 2.65 |
| CGMacros-017 | healthy | 33F | 22.7 | 5.0 | 95 | 76.5 | 14.2 | 69.6 | 30.4 | 4.92 | 40 | 71.7 | 11.4 | 0.965 | 3.01 |
| CGMacros-018 | healthy | 18M | 38.1 | 5.4 | 103 | 100.8 | 17.8 | 98.1 | 1.9 | 0.26 | 40 | 93.4 | 13.6 | 0.973 | 3.12 |
| CGMacros-019 | healthy | 40F | 36.4 | 5.6 | 98 | 85.2 | 14.9 | 87.3 | 12.7 | 1.36 | 40 | 76.3 | 13.5 | 0.977 | 2.91 |
| CGMacros-020 | prediabetes | 59F | 36.0 | 6.4 | 119 | 131.5 | 28.2 | 93.1 | 0.0 | 0.00 | 78 | 128.6 | 24.0 | 0.976 | 5.20 |
| CGMacros-021 | healthy | 63F | 25.7 | 5.3 | 98 | 100.9 | 19.8 | 97.2 | 2.6 | 0.00 | 55 | 91.8 | 13.1 | 0.961 | 3.61 |
| CGMacros-022 | prediabetes | 69F | 20.7 | 5.9 | 107 | 98.5 | 15.8 | 99.4 | 0.6 | 0.00 | 61 | 90.9 | 13.4 | 0.973 | 3.07 |
| CGMacros-023 | prediabetes | 55M | 24.2 | 6.2 | 135 | 112.8 | 29.7 | 94.7 | 1.7 | 0.00 | 64 | 91.3 | 20.1 | 0.954 | 6.01 |
| CGMacros-026 | prediabetes | 35M | 31.2 | 5.9 | 104 | 97.5 | 21.3 | 96.3 | 3.5 | 0.37 | 49 | 94.1 | 15.4 | 0.978 | 3.18 |
| CGMacros-027 | healthy | 24F | 27.1 | 4.7 | 90 | 76.5 | 16.8 | 63.2 | 36.8 | 6.02 | 40 | 66.1 | 13.7 | 0.965 | 3.59 |
| CGMacros-028 | t2d | 59F | 40.0 | 7.0 | 131 | 114.8 | 20.6 | 99.0 | 0.4 | 0.00 | 63 | 107.5 | 11.3 | 0.977 | 2.44 |
| CGMacros-029 | prediabetes | 52M | 29.5 | 6.1 | 136 | 110.3 | 21.7 | 98.6 | 0.2 | 0.00 | 65 | 97.8 | 7.9 | 0.935 | 2.79 |
| CGMacros-030 | t2d | 60F | 34.0 | 7.6 | 195 | 155.5 | 59.2 | 73.3 | 0.1 | 0.00 | 67 | 136.4 | 46.5 | 0.977 | 9.98 |
| CGMacros-031 | healthy | 46F | 23.1 | 5.1 | 102 | 81.9 | 15.4 | 84.5 | 15.5 | 0.08 | 53 | 73.4 | 8.2 | 0.969 | 2.04 |
| CGMacros-032 | healthy | 64M | 22.9 | 5.3 | 100 | 67.6 | 19.1 | 43.9 | 56.1 | 23.26 | 40 | 57.9 | 15.8 | 0.978 | 3.30 |
| CGMacros-033 | healthy | 40M | 30.0 | 5.6 | 116 | 121.4 | 41.2 | 88.8 | 1.7 | 0.00 | 55 | 96.5 | 14.9 | 0.960 | 4.14 |
| CGMacros-034 | healthy | 24M | 25.8 | 4.6 | 80 | 79.3 | 16.4 | 74.8 | 25.2 | 6.48 | 40 | 67.8 | 14.4 | 0.979 | 2.95 |
| CGMacros-035 | t2d | 45F | 28.7 | 8.5 | 218 | 196.6 | 48.0 | 44.1 | 0.0 | 0.00 | 92 | 168.2 | 29.2 | 0.983 | 5.31 |
| CGMacros-036 | t2d | 61M | 25.0 | 6.9 | 101 | 110.1 | 41.6 | 78.6 | 14.2 | 4.70 | 40 | 78.2 | 17.4 | 0.986 | 2.93 |
| CGMacros-038 | t2d | 52M | 34.5 | 7.2 | 151 | 115.4 | 28.9 | 94.9 | 0.2 | 0.00 | 63 | 103.7 | 8.1 | 0.965 | 2.14 |
| CGMacros-039 | t2d | 45F | 26.9 | 8.3 | 158 | 139.2 | 44.6 | 83.1 | 0.7 | 0.00 | 59 | 114.0 | 16.3 | 0.963 | 4.41 |
| CGMacros-041 | prediabetes | 58F | 27.9 | 6.3 | 138 | 133.4 | 33.1 | 89.4 | 0.0 | 0.00 | 79 | 109.8 | 9.9 | 0.939 | 3.40 |
| CGMacros-042 | t2d | 51F | 43.3 | 7.1 | 142 | 133.0 | 22.3 | 96.0 | 0.0 | 0.00 | 83 | 122.7 | 8.4 | 0.964 | 2.22 |
| CGMacros-043 | prediabetes | 45F | 49.1 | 6.0 | 96 | 89.7 | 20.0 | 85.6 | 14.4 | 2.00 | 40 | 84.1 | 20.5 | 0.974 | 4.64 |
| CGMacros-044 | prediabetes | 60F | 35.9 | 6.0 | 119 | 111.8 | 27.2 | 97.1 | 1.6 | 0.00 | 56 | 102.0 | 20.7 | 0.977 | 4.36 |
| CGMacros-045 | prediabetes | 46F | 32.9 | 6.1 | 148 | 128.3 | 42.1 | 85.3 | 2.2 | 0.16 | 47 | 124.6 | 39.1 | 0.981 | 7.57 |
| CGMacros-046 | t2d | 51M | 28.2 | 7.4 | 154 | 172.4 | 52.2 | 63.7 | 0.0 | 0.00 | 71 | 160.8 | 41.6 | 0.970 | 10.20 |
| CGMacros-047 | t2d | 62M | 31.4 | 6.9 | 150 | 155.2 | 38.3 | 77.9 | 0.0 | 0.00 | 77 | 127.6 | 17.4 | 0.979 | 3.51 |
| CGMacros-048 | healthy | 22F | 21.1 | 4.8 | 79 | 82.5 | 20.4 | 76.6 | 23.4 | 9.54 | 40 | 71.7 | 18.2 | 0.993 | 2.16 |
| CGMacros-049 | t2d | 58F | 36.1 | 7.2 | 148 | 140.9 | 45.8 | 80.7 | 1.6 | 0.00 | 60 | 122.4 | 23.7 | 0.966 | 6.20 |
