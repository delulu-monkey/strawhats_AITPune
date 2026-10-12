"""
Scenario Sandbox UI Component (Part 6).
=======================================

Allows clinicians to run counterfactual what-if experiments:
- Pick a patient and start moment.
- Define up to 3 interventions (sleep duration, added meal, added walk, habitual steps).
- Compare baseline vs scenario glucose curves on one chart.
- Compare peak glucose, time > 180, mean glucose.
- Evaluate XGBoost spike risk before and after with SHAP explanations.
- Plain statement on simulator assumptions.
"""

from __future__ import annotations

import datetime
from datetime import datetime as dt, timedelta
from typing import Dict, Any, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

from src.sim.profile import VirtualPatient
from src.sim.store import list_patients, load_patient
from src.sim.scenarios import simulate_scenario, compare_metrics
from src.sim.featurize import featurize_patient
from app.sim_ui.common import load_models, load_indian_meals
from app.sim_ui.badges import badge_html
from app.sim_ui.theme import (
    PRIMARY, PRIMARY_DARK, TEXT_MAIN, CHART_LINE_MAIN, CHART_LINE_BASELINE,
    CHART_THRESHOLD, CHART_HYPO, CHART_RANGE_FILL, CHART_MEAL, CHART_STEPS,
    STATUS_OK, STATUS_WATCH, STATUS_HIGH,
)

THR = 180.0
WATCH = 0.75
HIGH = 0.91


def render_scenario_sandbox() -> None:
    """Main entry point for Section: Scenario Sandbox."""
    st.markdown("## Counterfactual Scenario Sandbox")
    st.caption(
        "Define hypothetical behavioral interventions and simulate the next 24 hours. "
        "Baseline and scenario run with the **exact same random seed** so only the intervention differs."
    )

    # Mandatory Plain Statement
    st.warning(
        "**Clinical Notice:** Scenario effects come from simulator assumptions "
        "(see assumptions file), not from patterns learned in real data."
    )

    all_patients = list_patients(include_presets=True)
    if not all_patients:
        st.warning("No virtual patients available. Please create one in the Patients directory.")
        return

    patient_ids = [p["id"] for p in all_patients]
    default_id = st.session_state.get("selected_patient_id", "well_controlled_45")
    if default_id not in patient_ids:
        default_id = patient_ids[0]

    # Patient & Moment Selection
    col_pt, col_date, col_time = st.columns([2, 1, 1])
    chosen_id = col_pt.selectbox(
        "Select Patient",
        patient_ids,
        index=patient_ids.index(default_id),
        format_func=lambda pid: next((f"{p['name']} ({p['type'].upper()})" for p in all_patients if p["id"] == pid), pid),
    )
    patient = load_patient(chosen_id)

    eval_date = col_date.date_input("Start Date", datetime.date(2025, 1, 1))
    eval_time = col_time.time_input("Start Time", datetime.time(8, 0))
    start_moment = dt.combine(eval_date, eval_time)

    st.markdown(
        f"""
        <div style="font-size: 13.5px; color: {TEXT_MAIN}; margin: 4px 0 8px 0;">
            <strong>Patient Baseline:</strong> {patient.name} · Age {patient.age} · HbA1c {patient.hba1c:.1f}% · 
            BMI {patient.bmi:.1f} · Usual Sleep: {patient.lifestyle.typical_sleep_hours:.1f}h · 
            Habitual Steps: {patient.lifestyle.steps_per_day:,} · Seed: {patient.seed} {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.divider()

    # Define Up to Three Changes
    st.markdown("### Define Interventions (Choose up to 3)")
    food_catalogue = load_indian_meals()

    c_box1, c_box2, c_box3, c_box4 = st.columns(4)
    mod_sleep = c_box1.checkbox("1. Adjust Sleep Tonight", False)
    mod_meal = c_box2.checkbox("2. Add Food Challenge", True)
    mod_walk = c_box3.checkbox("3. Add Post-Meal Walk", True)
    mod_steps = c_box4.checkbox("4. Change Habitual Steps", False)

    num_active = sum([mod_sleep, mod_meal, mod_walk, mod_steps])
    if num_active > 3:
        st.error("Please select a maximum of three simultaneous interventions.")
        return

    scenario_params: Dict[str, Any] = {}

    col_interv1, col_interv2 = st.columns(2)

    # 1. Sleep modification
    if mod_sleep:
        with col_interv1:
            st.markdown("##### Sleep Modification")
            cur_sleep = patient.lifestyle.typical_sleep_hours
            target_sleep = st.slider(
                "Tonight's Sleep Duration (hours)",
                min_value=3.0,
                max_value=12.0,
                value=float(min(cur_sleep - 2.5, 4.5)),
                step=0.5,
                help=f"Usual duration is {cur_sleep:.1f} hours. Shorter sleep accumulates debt and elevates morning insulin resistance.",
            )
            scenario_params["sleep_hours"] = target_sleep

    # 2. Meal modification
    if mod_meal:
        with col_interv2:
            st.markdown("##### Added Meal / Food Challenge")
            meal_dish = st.selectbox("Select Dish", food_catalogue["dish"].tolist(), index=8)  # Boiled rice
            m_portions = st.slider("Portion Size", 0.5, 3.0, 1.5, 0.5)
            meal_offset_h = st.slider("Meal Timing (hours from start)", 0.5, 12.0, 2.0, 0.5)
            meal_time = start_moment + timedelta(hours=meal_offset_h)
            st.caption(f"Will be consumed at: **{meal_time.strftime('%H:%M')}**")

            scenario_params["added_meal"] = {
                "dish": meal_dish,
                "portions": m_portions,
                "time": meal_time,
            }

    # 3. Walk modification
    if mod_walk:
        with col_interv1:
            st.markdown("##### Added Walk / Exercise")
            walk_dur = st.slider("Walk Duration (minutes)", 15, 60, 30, 5)
            # Default timing: 30 minutes after the meal if meal added, otherwise 3h from start
            default_walk_offset = (scenario_params.get("added_meal", {}).get("time", start_moment + timedelta(hours=2)) - start_moment).total_seconds() / 3600.0 + 0.5 if mod_meal else 3.0
            walk_offset_h = st.slider("Walk Timing (hours from start)", 0.5, 14.0, float(default_walk_offset), 0.5)
            walk_time = start_moment + timedelta(hours=walk_offset_h)
            st.caption(f"Walk session starts at: **{walk_time.strftime('%H:%M')}** (~3.5 METs)")

            scenario_params["added_walk"] = {
                "time": walk_time,
                "duration_minutes": walk_dur,
                "steps_per_min": 100,
            }

    # 4. Habitual steps modification
    if mod_steps:
        with col_interv2:
            st.markdown("##### Habitual Daily Activity")
            target_steps = st.slider(
                "New Habitual Daily Steps",
                min_value=2000,
                max_value=25000,
                value=int(patient.lifestyle.steps_per_day * 1.5),
                step=1000,
            )
            scenario_params["habitual_steps"] = target_steps

    st.divider()

    # Run Scenario Simulation
    if st.button("Run Counterfactual Scenario", type="primary", use_container_width=True):
        with st.spinner("Simulating counterfactual 24-hour trajectories..."):
            baseline_df, scenario_df = simulate_scenario(patient, start_moment, scenario_params)
            metrics = compare_metrics(baseline_df, scenario_df)

        st.markdown(
            f"""
            <div style="font-size: 16px; font-weight: 700; color: {PRIMARY_DARK}; margin: 12px 0 8px 0;">
                Simulation Results: Baseline vs Scenario {badge_html('SIMULATED')}
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Metrics cards
        m1, m2, m3, m4 = st.columns(4)
        m1.metric(
            "Peak Glucose",
            f"{metrics['scenario_peak']:.1f} mg/dL",
            f"{metrics['peak_delta']:+.1f} mg/dL",
            delta_color="inverse",
        )
        m2.metric(
            "Time > 180 mg/dL",
            f"{metrics['scenario_time_above_180']:.1f}%",
            f"{metrics['time_above_180_delta']:+.1f}%",
            delta_color="inverse",
        )
        m3.metric(
            "24h Mean Glucose",
            f"{metrics['scenario_mean']:.1f} mg/dL",
            f"{metrics['mean_delta']:+.1f} mg/dL",
            delta_color="inverse",
        )
        m4.metric(
            "Baseline Peak",
            f"{metrics['baseline_peak']:.1f} mg/dL",
        )

        st.divider()

        # Comparison Plot — baseline in grey, scenario in blue
        st.markdown("##### Glucose Trajectory Comparison (24 Hours)")
        fig_cmp, ax_cmp = plt.subplots(figsize=(11, 4.2))

        ax_cmp.plot(
            baseline_df["time"],
            baseline_df["libre"],
            color=CHART_LINE_BASELINE,
            lw=1.8,
            ls="--",
            label="Baseline (Normal Schedule)",
        )
        ax_cmp.plot(
            scenario_df["time"],
            scenario_df["libre"],
            color=CHART_LINE_MAIN,
            lw=2.0,
            label="Counterfactual Scenario",
        )

        ax_cmp.axhline(180, color=CHART_THRESHOLD, ls=":", lw=1.2, label="Spike Threshold (180)")
        ax_cmp.axhline(70, color=CHART_HYPO, ls=":", lw=1.0, label="Hypo Threshold (70)")
        ax_cmp.axhspan(70, 180, color=CHART_RANGE_FILL, alpha=0.04)

        # Plot intervention markers
        if mod_meal and "added_meal" in scenario_params:
            m_t = scenario_params["added_meal"]["time"]
            ax_cmp.axvline(m_t, color=CHART_MEAL, ls="-.", lw=1.5)
            ax_cmp.scatter([m_t], [scenario_df.loc[(scenario_df["time"] - m_t).abs().argmin(), "libre"]],
                           color=CHART_MEAL, s=40, zorder=6, label="Added Meal")

        if mod_walk and "added_walk" in scenario_params:
            w_t = scenario_params["added_walk"]["time"]
            w_dur = scenario_params["added_walk"]["duration_minutes"]
            ax_cmp.axvspan(w_t, w_t + timedelta(minutes=w_dur), color=CHART_STEPS, alpha=0.12, label="Added Walk")

        ax_cmp.set_ylabel("Glucose (mg/dL)", fontsize=9)
        ax_cmp.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4, fontsize=8, frameon=False)
        fig_cmp.autofmt_xdate()
        st.pyplot(fig_cmp)
        plt.close(fig_cmp)

        # Disclaimer note
        st.caption(
            "The effects shown come from simulator assumptions and are not treatment advice. "
            "See the Simulation Assumptions page for all parameter values and rationale."
        )

        st.divider()

        # Risk Model Evaluation Before vs After with SHAP
        st.markdown("##### XGBoost Spike Warning Risk Evaluation: Before vs After")
        risk_dict, _, explainer = load_models()
        feats_base = featurize_patient(baseline_df, patient)
        feats_scen = featurize_patient(scenario_df, patient)

        if "time" not in feats_base.columns:
            feats_base = feats_base.reset_index()
        if "time" not in feats_scen.columns:
            feats_scen = feats_scen.reset_index()

        risk_feats = risk_dict["features"]

        # Evaluate at peak post-intervention moment
        peak_idx = scenario_df["libre"].argmax()
        eval_t = scenario_df.iloc[peak_idx]["time"]

        # Locate closest row in featurized tables
        pos_b = (feats_base["time"] - eval_t).abs().argmin()
        pos_s = (feats_scen["time"] - eval_t).abs().argmin()

        row_b = feats_base.iloc[pos_b]
        row_s = feats_scen.iloc[pos_s]

        x_b = feats_base.iloc[[pos_b]][risk_feats].astype(float)
        x_s = feats_scen.iloc[[pos_s]][risk_feats].astype(float)

        prob_b = float(risk_dict["model"].predict_proba(x_b)[0, 1])
        prob_s = float(risk_dict["model"].predict_proba(x_s)[0, 1])

        def get_level(p):
            return "HIGH" if p >= HIGH else "WATCH" if p >= WATCH else "LOW"

        r_col_b, r_col_s = st.columns(2)

        with r_col_b:
            st.markdown(f"###### Baseline Risk (at {eval_t.strftime('%H:%M')})")
            lv_b = get_level(prob_b)
            if lv_b == "HIGH":
                st.error(f"**HIGH RISK** ({prob_b:.1%})")
            elif lv_b == "WATCH":
                st.warning(f"**WATCH** ({prob_b:.1%})")
            else:
                st.success(f"**LOW RISK** ({prob_b:.1%})")
            st.write(f"Glucose: {row_b['glu_now']:.0f} mg/dL")

        with r_col_s:
            st.markdown(f"###### Scenario Risk (at {eval_t.strftime('%H:%M')})")
            lv_s = get_level(prob_s)
            if lv_s == "HIGH":
                st.error(f"**HIGH RISK** ({prob_s:.1%})")
            elif lv_s == "WATCH":
                st.warning(f"**WATCH** ({prob_s:.1%})")
            else:
                st.success(f"**LOW RISK** ({prob_s:.1%})")
            st.write(f"Glucose: {row_s['glu_now']:.0f} mg/dL")

        # Comparison table
        st.markdown("###### Metric Comparison")
        comp_data = {
            "Metric": ["Peak Glucose (mg/dL)", "Time > 180 (%)", "Mean Glucose (mg/dL)"],
            "Baseline": [
                f"{metrics['baseline_peak']:.1f}",
                f"{metrics['baseline_time_above_180']:.1f}",
                f"{metrics['baseline_mean']:.1f}",
            ],
            "Scenario": [
                f"{metrics['scenario_peak']:.1f}",
                f"{metrics['scenario_time_above_180']:.1f}",
                f"{metrics['scenario_mean']:.1f}",
            ],
            "Change": [
                f"{metrics['peak_delta']:+.1f}",
                f"{metrics['time_above_180_delta']:+.1f}",
                f"{metrics['mean_delta']:+.1f}",
            ],
        }
        st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

        st.markdown("###### Top SHAP Drivers of Risk Divergence")
        sv_b = explainer.shap_values(x_b)
        sv_s = explainer.shap_values(x_s)
        sv_b = sv_b[1] if isinstance(sv_b, list) else sv_b
        sv_s = sv_s[1] if isinstance(sv_s, list) else sv_s

        groups = {f: f for f in risk_feats}
        groups["hour_sin"] = groups["hour_cos"] = "time_of_day"

        contrib_b = pd.Series(sv_b[0], index=risk_feats).groupby(groups).sum()
        contrib_s = pd.Series(sv_s[0], index=risk_feats).groupby(groups).sum()
        diff_contrib = (contrib_s - contrib_b).drop(["age", "bmi", "male"], errors="ignore").sort_values()

        top_inc = diff_contrib[diff_contrib > 0].tail(3)[::-1]
        top_dec = diff_contrib[diff_contrib < 0].head(2)

        if not top_inc.empty:
            for feat, val in top_inc.items():
                st.write(f"**Increased risk in scenario:** `{feat}` (SHAP change: +{val:.3f})")
        if not top_dec.empty:
            for feat, val in top_dec.items():
                st.write(f"**Mitigated risk in scenario:** `{feat}` (SHAP change: {val:.3f})")
        if top_inc.empty and top_dec.empty:
            st.info("No significant SHAP divergence at this moment.")
