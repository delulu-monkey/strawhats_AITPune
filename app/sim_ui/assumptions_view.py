"""
Simulation Assumptions Viewer Component (Part 6).
==================================================

Renders the complete set of simulator assumptions:
- Every constant with its rationale and calibrated value.
- Clear statement: 'assumption, not learned from data'.
- Full source code viewer for src/sim/assumptions.py for clinicians and judges.
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import streamlit as st

from app.sim_ui.badges import badge_html


ASSUMPTION_CATEGORIES = [
    {
        "category": "Fasting Glucose Model",
        "parameters": [
            ("FASTING_GLUCOSE_INTERCEPT", -43.0, "mg/dL", "Calibrated to match real overnight mean (~75 healthy, ~99 prediab, ~120 T2D)"),
            ("FASTING_GLUCOSE_HBA1C_SLOPE", 22.0, "mg/dL per %", "Calibrated for healthy vs T2D fasting baseline separation"),
            ("FASTING_GLUCOSE_IR_ADDER_PER_UNIT", 6.0, "mg/dL per IR unit", "Keeps fasting glucose linear rather than explosive at high IR"),
        ],
    },
    {
        "category": "Insulin Resistance (IR) Model",
        "parameters": [
            ("IR_HBA1C_FACTOR_PER_PCT", 0.45, "per % above 5.0", "Calibrated for post-meal rise scaling across healthy/prediab/T2D groups"),
            ("IR_BMI_FACTOR_PER_UNIT", 0.020, "per kg/m² above 22", "Models excess adiposity contribution to peripheral insulin resistance"),
            ("GENETIC_IR_MAX_BOOST", 0.25, "multiplier at score=100", "Maximum insulin resistance boost from polygenic risk variants"),
        ],
    },
    {
        "category": "Meal Response Curve (Gamma-Shaped)",
        "parameters": [
            ("MEAL_PEAK_MINUTES", 50.0, "minutes", "Peak glucose rise time after meal ingestion (mid-range 45–60 min)"),
            ("MEAL_GAMMA_SHAPE", 4.0, "dimensionless", "Gamma curve shape parameter governing postprandial rise and fall"),
            ("MEAL_CARB_SENSITIVITY", 0.55, "mg/dL per g carb", "Calibrated to match real 2-hour postprandial rises (~32 healthy, ~52 T2D)"),
            ("MEAL_FIBER_OFFSET_PER_G", 0.5, "g carb offset per g", "Fiber blunts the glycemic response and slows gastric emptying"),
            ("MEAL_PROTEIN_OFFSET_PER_G", 0.15, "g carb offset per g", "Protein slows gastric emptying; modest reduction in glycemic index"),
            ("MEAL_FAT_OFFSET_PER_G", 0.2, "g carb offset per g", "Dietary lipids slow gastric emptying and blunt acute absorption"),
            ("MEAL_FAT_PEAK_EXTENSION_PER_10G", 0.05, "fraction per 10g", "High fat extends the postprandial peak latency"),
            ("MEAL_RESPONSE_DURATION_MIN", 180.0, "minutes", "Total duration of active postprandial glycemic excursion"),
        ],
    },
    {
        "category": "Sleep Debt Effects",
        "parameters": [
            ("SLEEP_OPTIMAL_HOURS", 7.5, "hours", "Standard nocturnal sleep baseline requirement for adults"),
            ("SLEEP_DEBT_GLUCOSE_MG_PER_HOUR", 3.0, "mg/dL per hour deficit", "Each hour of sleep debt elevates morning fasting baseline"),
            ("SLEEP_DEBT_IR_FACTOR_PER_HOUR", 0.04, "fractional IR rise per h", "Each hour of sleep debt elevates peripheral insulin resistance"),
            ("SLEEP_CYCLE_MINUTES", 90.0, "minutes", "Ultradian sleep cycle period (Light → Deep → Light → REM)"),
        ],
    },
    {
        "category": "Physical Activity & Walking",
        "parameters": [
            ("ACTIVITY_GLUCOSE_DROP_PER_1000_STEPS", 2.0, "mg/dL per 1000 steps", "Skeletal muscle contraction drives GLUT4 glucose uptake"),
            ("ACTIVITY_MAX_DROP_PER_EPOCH", 5.0, "mg/dL per 5 min", "Ceiling capping glucose reduction in any single 5-min epoch"),
            ("ACTIVITY_METS_ACTIVE_THRESHOLD", 2.0, "METs", "Threshold defining active ambulation / brisk walking"),
        ],
    },
    {
        "category": "Dawn Effect and Circadian Rhythm",
        "parameters": [
            ("DAWN_EFFECT_START_HOUR", 4.0, "24h clock", "Circadian cortisol / growth hormone surge initiation"),
            ("DAWN_EFFECT_END_HOUR", 8.0, "24h clock", "Circadian dawn phenomenon conclusion"),
            ("DAWN_EFFECT_MAX_MG", 15.0, "mg/dL", "Maximum nocturnal hepatic glucose release peak"),
        ],
    },
    {
        "category": "Pharmacotherapy: Metformin",
        "parameters": [
            ("METFORMIN_FASTING_REDUCTION", 15.0, "mg/dL", "Hepatic gluconeogenesis reduction by metformin monotherapy"),
            ("METFORMIN_POSTMEAL_REDUCTION_FRAC", 0.15, "fractional blunting", "Modest postprandial glucose excursion blunting"),
        ],
    },
    {
        "category": "Sensor Noise and Behavioral Unlogged Snacks",
        "parameters": [
            ("SENSOR_AR1_PHI", 0.85, "autocorrelation", "Continuous sensor interstitial drift AR(1) coefficient"),
            ("SENSOR_NOISE_SD", 3.0, "mg/dL SD", "Stochastic noise standard deviation per 5-min epoch"),
            ("UNLOGGED_SNACK_PROB_PER_EPOCH", 0.02, "prob per 5 min", "Waking probability of consuming an unlogged snack"),
            ("UNLOGGED_SNACK_CARBS_MEAN", 15.0, "grams", "Mean carbohydrate mass of unlogged snacks"),
        ],
    },
]


def render_assumptions_view() -> None:
    """Main entry point for Section: Simulation Assumptions."""
    st.markdown("## Virtual Patient Simulation Assumptions")
    st.caption(
        "Complete physiological parameter specification. In strict adherence to **Honesty Rule 4**, "
        "every parameter is an **explicit assumption, not learned from data**."
    )

    st.info(
        "**Research Prototype Notice:** Simulated physiological outputs demonstrate mathematical twin pipelines, "
        "not certified clinical accuracy. All models and scenarios are research prototypes for simulated or "
        "anonymised patients only.\n\n"
        "**Transparency Guarantee for Judges and Clinicians:** Every constant below is defined in "
        "`src/sim/assumptions.py`. None of these effect sizes are hidden inside machine learning weights; "
        "each has an explicit physiological rationale and was set as documented assumptions; see sim_fidelity.md "
        "for the comparison with real data."
    )

    # Render Categorized Tables
    for cat in ASSUMPTION_CATEGORIES:
        st.markdown(f"#### {cat['category']} {badge_html('SIMULATED')}", unsafe_allow_html=True)
        table_rows = []
        for name, val, unit, rat in cat["parameters"]:
            table_rows.append({
                "Parameter Name": name,
                "Value": f"{val}",
                "Unit": unit,
                "Physiological Rationale (Assumption)": rat,
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
        st.write("")

    st.divider()

    # Raw Source File Inspector
    st.markdown("### Complete Source File (`src/sim/assumptions.py`)")
    assumptions_path = Path("src/sim/assumptions.py")
    if assumptions_path.exists():
        with open(assumptions_path, "r", encoding="utf-8") as fp:
            source_code = fp.read()
        st.code(source_code, language="python")
    else:
        st.error("src/sim/assumptions.py not found.")
