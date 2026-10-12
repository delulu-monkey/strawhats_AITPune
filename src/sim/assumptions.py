"""
All tunable constants for the virtual patient simulator.
=======================================================

EVERY constant below is an **assumption, not learned from data**.
The one-line comment explains the physiological rationale.

Change any value here and rerun the simulation; nothing else needs editing.
"""

# ---------------------------------------------------------------------------
# Overnight sensor baseline models (FreeStyle Libre-style interstitial sensor)
# ---------------------------------------------------------------------------

# Regression 2 (docs/real_glucose_reference.md):
# Overnight sensor baseline derived from entered laboratory venous fasting glucose:
# overnight_sensor = 4.57 + 0.77 * lab_fasting_glucose (R² = 0.685, residual SD = 15.79 mg/dL).
SENSOR_BASELINE_FROM_FASTING_INTERCEPT = 4.57  # mg/dL, empirically fitted from real CGMacros data — see docs/real_glucose_reference.md
SENSOR_BASELINE_FROM_FASTING_SLOPE = 0.77      # slope against venous plasma lab fasting glucose — see docs/real_glucose_reference.md

# Regression 3 (docs/real_glucose_reference.md):
# Overnight sensor baseline derived from HbA1c when no lab fasting glucose is entered:
# overnight_sensor = -43.30 + 22.99 * HbA1c (R² = 0.551, residual SD = 18.84 mg/dL).
SENSOR_BASELINE_FROM_HBA1C_INTERCEPT = -43.30  # mg/dL, empirically fitted from real CGMacros data — see docs/real_glucose_reference.md
SENSOR_BASELINE_FROM_HBA1C_SLOPE = 22.99       # mg/dL per % HbA1c — see docs/real_glucose_reference.md

# Regression 4 (docs/real_glucose_reference.md):
# Displayed venous lab fasting glucose derived from HbA1c when none is entered:
# lab_fasting_glu = -57.91 + 29.17 * HbA1c (R² = 0.768, residual SD = 14.57 mg/dL).
# Note: Used ONLY for deriving displayed lab fasting value in UI, NOT for simulator baseline!
LAB_FASTING_GLUCOSE_INTERCEPT = -57.91         # mg/dL, venous lab regression — see docs/real_glucose_reference.md
LAB_FASTING_GLUCOSE_HBA1C_SLOPE = 29.17        # mg/dL per % HbA1c — see docs/real_glucose_reference.md

# Aliases for backwards compatibility:
FASTING_GLUCOSE_INTERCEPT = SENSOR_BASELINE_FROM_HBA1C_INTERCEPT
FASTING_GLUCOSE_HBA1C_SLOPE = SENSOR_BASELINE_FROM_HBA1C_SLOPE

# IR adder: each unit of IR above 1.0 adds this many mg/dL to fasting.
# Keeps fasting glucose linear rather than explosive at high IR.
FASTING_GLUCOSE_IR_ADDER_PER_UNIT = 6.0  # mg/dL per IR unit above 1.0 — assumption, not learned from data

# ---------------------------------------------------------------------------
# Insulin resistance score  (dimensionless, 1.0 = normal sensitivity)
# ---------------------------------------------------------------------------

# Baseline IR is additive from HbA1c and BMI contributions.
# IR = 1.0 + hba1c_excess + bmi_excess + genetic + sleep_debt.
# HbA1c contribution: 0.15 per % above 5.0 — someone with 7 % gets +0.30.
IR_HBA1C_FACTOR_PER_PCT = 0.45  # per % above 5.0, calibrated for post-meal rise scaling across groups — assumption, not learned from data

# BMI contribution: 0.020 per kg/m² above 22 — BMI 30 → +0.16.
IR_BMI_FACTOR_PER_UNIT = 0.020  # per kg/m² above 22 — assumption, not learned from data

# ---------------------------------------------------------------------------
# Meal response curve (gamma-shaped)
# ---------------------------------------------------------------------------

# Peak glucose rise time after eating, in minutes.
MEAL_PEAK_MINUTES = 50.0  # 45–60 min is typical; mid-range — assumption, not learned from data

# Gamma shape parameter (controls steepness of rise and fall).
MEAL_GAMMA_SHAPE = 4.0  # shape > 1 gives a rise-then-fall curve — assumption, not learned from data

# How many mg/dL glucose rise per gram of carbohydrate at IR = 1.0.
MEAL_CARB_SENSITIVITY = 0.55  # mg/dL per g carb at IR=1.0, calibrated to match real 2-h post-meal rises — assumption, not learned from data

# Fiber blunts the glycemic response (each g fiber offsets some carb effect).
MEAL_FIBER_OFFSET_PER_G = 0.5  # g effective-carb reduction per g fiber — assumption, not learned from data

# Protein slows gastric emptying; each g protein offsets a small carb equiv.
MEAL_PROTEIN_OFFSET_PER_G = 0.15  # g carb-equivalent offset per g protein — assumption, not learned from data

# Fat slows gastric emptying similarly but also extends the tail.
MEAL_FAT_OFFSET_PER_G = 0.2  # g carb-equivalent offset per g fat — assumption, not learned from data

# Fat extends the peak time by this factor per 10 g of fat.
MEAL_FAT_PEAK_EXTENSION_PER_10G = 0.05  # fraction of peak time — assumption, not learned from data

# Total meal response duration (minutes after meal start).
MEAL_RESPONSE_DURATION_MIN = 180  # 3 hours — assumption, not learned from data

# ---------------------------------------------------------------------------
# Sleep-debt effect
# ---------------------------------------------------------------------------

# Adults need about 7–8 h of sleep; deficit accumulates effects.
SLEEP_OPTIMAL_HOURS = 7.5  # assumption, not learned from data

# Each hour of sleep debt raises fasting glucose next morning by this much.
SLEEP_DEBT_GLUCOSE_MG_PER_HOUR = 3.0  # mg/dL per hour short — assumption, not learned from data

# Each hour of sleep debt multiplies IR by (1 + this value).
SLEEP_DEBT_IR_FACTOR_PER_HOUR = 0.04  # fractional IR rise per hour — assumption, not learned from data

# ---------------------------------------------------------------------------
# Activity / walking effect
# ---------------------------------------------------------------------------

# Walking lowers glucose by consuming circulating glucose in skeletal muscle.
ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS = 2.0  # mg/dL per 1000 steps — assumption, not learned from data

# Steps are distributed across 5-min bins during active hours; this caps
# the glucose reduction in any single 5-min epoch.
ACTIVITY_MAX_DROP_PER_EPOCH = 5.0  # mg/dL — assumption, not learned from data

# METs threshold above which someone is considered "active" (walking).
ACTIVITY_METS_ACTIVE_THRESHOLD = 2.0  # assumption, not learned from data

# ---------------------------------------------------------------------------
# Genetic risk effect
# ---------------------------------------------------------------------------

# Genetic risk score (0–100) raises IR.  At score = 50 (median), effect = 0.
# At score = 100 (high risk), IR is multiplied by (1 + GENETIC_IR_MAX_BOOST).
GENETIC_IR_MAX_BOOST = 0.20  # +20 % IR at max genetic risk — assumption, not learned from data

# ---------------------------------------------------------------------------
# Illustrative T2D-associated variants
# ---------------------------------------------------------------------------
# TODO: the user must verify these variant names against a published source
# (e.g., Mahajan et al. 2018, Nature Genetics).  The risk-allele counts
# (0/1/2) are for illustration only.
T2D_VARIANTS = [
    "TCF7L2_rs7903146",   # strongest common T2D risk locus
    "SLC30A8_rs13266634",  # zinc transporter, beta-cell function
    "KCNJ11_rs5219",       # potassium channel, insulin secretion
    "PPARG_rs1801282",     # adipocyte differentiation
    "FTO_rs9939609",       # obesity-associated, indirect T2D risk
]

# ---------------------------------------------------------------------------
# Metformin effect
# ---------------------------------------------------------------------------

# Metformin lowers fasting glucose by a modest flat amount (mg/dL) —
# represents average chronic effect, not acute PK.
METFORMIN_FASTING_REDUCTION = 15.0  # mg/dL — assumption, not learned from data

# Metformin also mildly reduces post-meal excursions.
METFORMIN_POSTMEAL_REDUCTION_FRAC = 0.05  # 5 % post-meal reduction — assumption, not learned from data

# ---------------------------------------------------------------------------
# Dawn phenomenon
# ---------------------------------------------------------------------------

# Between ~4 AM and ~8 AM, hepatic glucose output rises due to cortisol/GH.
DAWN_EFFECT_START_HOUR = 4.0   # assumption, not learned from data
DAWN_EFFECT_END_HOUR = 8.0     # assumption, not learned from data
DAWN_EFFECT_MAX_MG = 9.0       # peak mg/dL rise at mid-point, calibrated to nocturnal curve — assumption, not learned from data

# ---------------------------------------------------------------------------
# CGM / sensor noise  (AR(1) process)
# ---------------------------------------------------------------------------

# Auto-regressive coefficient (0 = white noise, 0.97 = realistic interstitial sensor lag).
# Calibrated to real 5-min CGMacros Libre within-person lag-1 correlation (median phi = 0.97, IQR 0.96-0.98; see docs/real_glucose_reference.md).
SENSOR_AR1_PHI = 0.97  # calibrated to match real CGMacros 5-min Libre autocorrelation — see docs/real_glucose_reference.md

# Standard deviation of the innovation noise (mg/dL).
# Calibrated to real 5-min CGMacros Libre within-person innovation SD (median = 3.3 mg/dL, IQR 2.5-4.1; see docs/real_glucose_reference.md).
SENSOR_NOISE_SD = 3.3  # calibrated to match real CGMacros 5-min within-person innovation SD (mg/dL) — see docs/real_glucose_reference.md

# ---------------------------------------------------------------------------
# Unlogged snacks
# ---------------------------------------------------------------------------

# Probability that an unlogged snack occurs in each 5-min epoch during
# waking hours (set per-profile; this is the default).
UNLOGGED_SNACK_PROB_PER_EPOCH = 0.001  # ~0.1 % per 5-min ≈ 1-2 snacks/day — assumption, not learned from data

# When an unlogged snack happens, its effective carb content (g).
UNLOGGED_SNACK_CARBS_MEAN = 12.0  # g — assumption, not learned from data
UNLOGGED_SNACK_CARBS_SD = 4.0     # g — assumption, not learned from data

# ---------------------------------------------------------------------------
# Heart-rate / HRV model
# ---------------------------------------------------------------------------

# Resting HR varies by age; this is a simple linear model.
HR_BASE_AGE_INTERCEPT = 85.0  # bpm at age 0, calibrated to match real CGMacros HR ~78 bpm — assumption, not learned from data
HR_BASE_AGE_SLOPE = -0.08      # bpm per year of age — assumption, not learned from data

# Activity adds HR on top of resting.
HR_ACTIVITY_PER_MET = 8.0  # bpm per MET above 1 — assumption, not learned from data

# During sleep, HR drops by this fraction.
HR_SLEEP_REDUCTION_FRAC = 0.15  # 15 % lower — assumption, not learned from data

# HRV (RMSSD) baseline for a young adult at rest (ms).
HRV_RMSSD_BASE = 45.0  # ms — assumption, not learned from data

# HRV declines with age.
HRV_AGE_DECLINE_PER_YEAR = 0.3  # ms per year from age 20 — assumption, not learned from data

# HRV rises during deep sleep.
HRV_DEEP_SLEEP_BOOST = 15.0  # ms — assumption, not learned from data

# HRV drops during activity.
HRV_ACTIVITY_DROP_PER_MET = 3.0  # ms per MET above 1 — assumption, not learned from data

# Sleep debt lowers HRV.
HRV_SLEEP_DEBT_DROP_PER_HOUR = 2.0  # ms per hour of debt — assumption, not learned from data

# ---------------------------------------------------------------------------
# Sleep architecture
# ---------------------------------------------------------------------------

# Approximate cycle length.
SLEEP_CYCLE_MINUTES = 90  # assumption, not learned from data

# Deep-sleep fraction declines across cycles (early-loaded).
SLEEP_DEEP_FRAC_CYCLE_1 = 0.25  # assumption, not learned from data
SLEEP_DEEP_FRAC_LATER = 0.10    # assumption, not learned from data

# REM fraction increases across cycles (late-loaded).
SLEEP_REM_FRAC_CYCLE_1 = 0.10   # assumption, not learned from data
SLEEP_REM_FRAC_LATER = 0.25     # assumption, not learned from data

# Light sleep fills the remainder.

# ---------------------------------------------------------------------------
# Glucose return-to-baseline
# ---------------------------------------------------------------------------

# Between meals, glucose drifts back toward fasting with this exponential
# half-life (minutes).
GLUCOSE_RETURN_HALFLIFE_MIN = 25.0  # calibrated post-meal clearance half-life — assumption, not learned from data

# ---------------------------------------------------------------------------
# Step generation
# ---------------------------------------------------------------------------

# Steps per day are distributed across waking hours with a peak around
# commute/exercise windows.  The profile supplies total daily steps.
STEP_ACTIVE_HOURS = (7, 22)  # assumption, not learned from data

# ---------------------------------------------------------------------------
# Meal schedule defaults
# ---------------------------------------------------------------------------

DEFAULT_MEAL_TIMES = {
    "breakfast": (7, 30),   # (hour, minute) — assumption, not learned from data
    "lunch":     (12, 30),
    "snack":     (16, 0),
    "dinner":    (20, 0),
}

# Portion multiplier ranges for each meal type.
# Calibrated so meal carbohydrate content matches real CGMacros (~50–55 g per meal).
PORTION_MULTIPLIER_RANGE = {
    "breakfast": (1.4, 2.0),  # assumption, not learned from data
    "lunch":     (1.6, 2.4),
    "snack":     (0.8, 1.4),
    "dinner":    (1.6, 2.4),
}
