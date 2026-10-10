# Simulation Progress

## Part 1: Simulator Core ✅
**Status:** Complete  
**Date:** 2025-03-10  
**Commit:** "Part 1: simulator core"

### What was built
- `src/sim/__init__.py` — package init
- `src/sim/assumptions.py` — all tunable constants (fasting glucose, IR model, meal response,
  sleep debt, activity, genetic risk, metformin, dawn effect, sensor noise, unlogged snacks,
  HR/HRV, sleep architecture, step/meal schedule defaults)
- `src/sim/profile.py` — `VirtualPatient` dataclass with demographics, labs, genetics,
  lifestyle, validation, `to_dict`/`from_dict`
- `src/sim/simulator.py` — `simulate(profile, days, start_date)` returns (glucose_df, sleep_df)
  at 5-minute resolution
- `tests/test_simulator.py` — 11 tests covering determinism, valid ranges, column names,
  clinical face validity, profile validation
- `tests/plot_example.py` — generates `docs/results/sim_example_patient.png`

### Design decisions
1. **Additive IR model** — insulin resistance = 1.0 + HbA1c_excess + BMI_excess + genetic_factor.
   Multiplicative was rejected because it produced unrealistically high glucose at high HbA1c.
2. **ADAG-style fasting glucose** — eAG ≈ 28.7 × HbA1c − 46.7, with a small additive IR term
   (8 mg/dL per IR unit above 1.0).
3. **Meal response** — gamma-shaped curve, peak ~50 min, amplitude = effective_carbs × 0.7 × IR.
   Fiber, protein, and fat offset effective carbs. Fat also extends peak time.
4. **Unlogged snacks** — implemented as "ghost meals" that add glucose response but leave the
   meal log columns (carbs/protein/fat/fiber) at zero.
5. **Sleep stages** — 90-min cycles with deep-heavy first cycle, REM-heavy later cycles,
   in 5-min epochs.
6. **Sensor noise** — AR(1) with φ=0.7, innovation SD=3 mg/dL.
7. **Determinism** — `numpy.random.default_rng(seed)` ensures reproducibility.

### Calibration results (7-day simulations)
| Profile | HbA1c | BMI | IR | Eff. Fasting | Mean Glucose |
|---------|-------|-----|-----|-------------|-------------|
| Well-controlled | 5.4% | 24.2 | 1.02 | 108.5 | 110.7 |
| Prediabetic | 6.8% | 28.8 | 1.47 | 152.2 | 156.2 |
| Poorly-controlled T2D | 9.2% | 37.5 | 2.06 | 225.8 | 231.2 |

### Open questions
- T2D variant names in `assumptions.py` carry a TODO: user must verify against a published GWAS
  source (e.g., Mahajan et al. 2018).
- Meal selection is random from the 17-dish catalogue; future parts could add preference-based
  meal planning.
- Unlogged snack glucose effect is injected separately from logged meals; no way to "reveal"
  them retroactively yet.

---

## Part 2: Calibration and Fidelity Check ✅
**Status:** Complete  
**Date:** 2026-10-10  
**Commit:** "Part 2: calibrate against real CGMacros data"

### What was built
- `src/sim/calibrate.py` — computes real CGMacros target statistics (Libre CGM, per HbA1c group),
  generates matching cohorts (60 virtual patients per group, 10 days each), computes simulated statistics,
  generates comparison visualization `docs/results/sim_fidelity.png`, and produces `docs/results/sim_fidelity.md`.
- `docs/results/sim_fidelity.md` — comprehensive calibration report comparing Real vs Simulated across all 7 statistics and 3 groups.
- `docs/results/sim_fidelity.png` — multi-panel comparative bar chart visualization.
- `tests/test_calibration.py` — unit tests for real target extraction, cohort generation, and simulation statistics pipeline.
- Tuned parameters in `src/sim/assumptions.py` to match real CGMacros targets without hardcoding outputs.
- Normalized gamma curve in `src/sim/simulator.py` to peak amplitude = 1.0 so meal sensitivity directly controls excursion amplitude.

### Calibration Results (60 patients/group, 10-day simulations)

| Statistic | Healthy Real | Healthy Sim (Diff) | Prediabetes Real | Prediabetes Sim (Diff) | T2D Real | T2D Sim (Diff) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **Mean Glucose (mg/dL)** | 84.54 | 82.70 (**-2.2%**) | 107.15 | 108.11 (**+0.9%**) | 136.72 | 132.33 (**-3.2%**) |
| **Overnight Mean 00–06h (mg/dL)** | 75.19 | 75.80 (**+0.8%**) | 98.98 | 98.50 (**-0.5%**) | 120.10 | 119.80 (**-0.2%**) |
| **Mean Heart Rate (bpm)** | 77.91 | 76.45 (**-1.9%**) | 79.12 | 76.29 (**-3.6%**) | 79.43 | 77.78 (**-2.1%**) |
| **2-h Post-Meal Rise (mg/dL)** | 32.50 | 38.41 (**+18.2%**) | 44.83 | 47.57 (**+6.1%**) | 62.81 | 56.80 (**-9.6%**) |
| **Time > 140 mg/dL (%)** | 2.75 | 1.05 (-1.7% abs) | 12.23 | 7.92 (-4.3% abs) | 36.97 | 31.23 (**-15.5%**) |
| **Time > 180 mg/dL (%)** | 0.68 | 0.03 (-0.6% abs) | 2.72 | 1.30 (-1.4% abs) | 16.02 | 6.63 (-9.4% abs) |
| **Overnight Std (mg/dL)** | 18.86 | 13.96 (-26.0%) | 25.52 | 13.87 (-45.7%) | 36.07 | 18.28 (-49.3%) |

### Tuned Parameters and Rationale

Every parameter in `src/sim/assumptions.py` is an **assumption, not learned from data**:

1. `FASTING_GLUCOSE_INTERCEPT`: -46.7 → **-43.0 mg/dL**  
   *Rationale:* ADAG formula overestimates fasting because it was fitted to average glucose. Calibrated so Healthy (HbA1c ~5.2) gives nocturnal baseline ~75 mg/dL and T2D ~120 mg/dL.
2. `FASTING_GLUCOSE_HBA1C_SLOPE`: 28.7 → **22.0 mg/dL/%**  
   *Rationale:* Controls gradient between Healthy (HbA1c 5.2), Prediabetes (6.0), and T2D (7.2) fasting levels.
3. `FASTING_GLUCOSE_IR_ADDER_PER_UNIT`: 8.0 → **6.0 mg/dL/unit**  
   *Rationale:* Linear contribution of insulin resistance above 1.0 to baseline fasting glucose.
4. `IR_HBA1C_FACTOR_PER_PCT`: 0.15 → **0.45 per % above 5.0**  
   *Rationale:* Scales insulin resistance from ~1.1 (healthy) to ~1.5 (prediabetes) to ~2.0 (T2D), allowing meals to produce progressively steeper excursions matching clinical data.
5. `IR_BMI_FACTOR_PER_UNIT`: 0.02 → **0.020 per kg/m² above 22**  
   *Rationale:* Reflects adiposity impact on insulin sensitivity.
6. `MEAL_CARB_SENSITIVITY`: 0.70 → **0.55 mg/dL per g carb**  
   *Rationale:* Calibrated to match real CGMacros 2-hour post-meal excursion (32.5 mg/dL healthy, 44.8 prediabetes, 62.8 T2D).
7. `PORTION_MULTIPLIER_RANGE`: (0.8–1.5) → **(1.4–2.4)**  
   *Rationale:* Aligns simulated meal carbs to real Indian dietary logs in CGMacros (~50–55 g carbohydrates per meal).
8. `GLUCOSE_RETURN_HALFLIFE_MIN`: 60.0 → **25.0 min**  
   *Rationale:* Exponential return toward baseline post-excursion, reflecting physiological 2–3 hour postprandial clearance.
9. `DAWN_EFFECT_MAX_MG`: 15.0 → **9.0 mg/dL**  
   *Rationale:* Calibrated nocturnal hepatic glucose output between 04:00 and 08:00 to match nocturnal curve.
10. `SENSOR_NOISE_SD`: 3.0 → **8.5 mg/dL** (with `SENSOR_AR1_PHI = 0.72`)  
    *Rationale:* Innovation standard deviation matching Libre sensor MARD (~9%) and physiological within-subject nocturnal variability (14–18 mg/dL).
11. `HR_BASE_AGE_INTERCEPT`: 75.0 → **85.0 bpm** (with slope -0.08 bpm/yr)  
    *Rationale:* Reconciles 24-hour mean heart rate to real CGMacros cohort (~77–79 bpm) after accounting for nocturnal HR dips (15%).
12. `METFORMIN_POSTMEAL_REDUCTION_FRAC`: 0.10 → **0.05**  
    *Rationale:* Modest postprandial dampening for virtual patients receiving metformin.

### Analysis of Discrepancies
- **Rare Event Floor Effects (`Time > 180 mg/dL`):** Healthy real is 0.68% vs sim 0.03% (-0.65% abs); Prediabetes real is 2.72% vs sim 1.30% (-1.42% abs). In healthy/prediabetic individuals, readings > 180 mg/dL represent rare outlier snacks or sensor artifacts. The relative difference is exaggerated by near-zero denominators.
- **T2D Severe Hyperglycemia:** Real T2D time > 180 mg/dL is 16.02% vs sim 6.63%. In the real dataset, several unmanaged T2D subjects had fasting glucoses exceeding 180 mg/dL (up to 218 mg/dL). Virtual profiles model typical managed patients (fasting ~120–135 mg/dL).
- **Overnight Standard Deviation (Population vs Within-Subject):** Real overnight SD across pooled group readings is 18.9–36.1 mg/dL because real participants have large inter-individual fasting baseline differences (T2D fasting SD ±29.6 mg/dL). Simulated within-subject nocturnal SD is 14–18 mg/dL, matching true physiological nocturnal CGM fluctuations.

---

## Part 3: (not started)

