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

## Part 2: (not started)
## Part 3: (not started)
