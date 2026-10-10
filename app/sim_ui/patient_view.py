"""
Patient View: Simulation, Multi-Tab Exploration, Risk & What-If.
================================================================

Tabs:
1. Profile and labs
2. Diagnoses, medications and genetics
3. Wearables (glucose + meals, sleep hypnogram, steps, HR, HRV)
4. Meal log
5. Spike Risk & Meal What-If (with time slider, XGBoost spike model, SHAP, dish what-if)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import streamlit as st

from src.sim.profile import VirtualPatient
from src.sim.store import list_patients, load_patient, get_provenance_map
from app.sim_ui.common import (
    load_models,
    load_indian_meals,
    run_simulation_cached,
)
from app.sim_ui.badges import badge_html, label_with_badge
from app.sim_ui.theme import render_patient_body_overview

# Model thresholds and caps
THR = 180.0
WATCH = 0.75
HIGH = 0.91
MEAL_ERR = 30.0
CAPS = {"carbs": 250.0, "protein": 150.0, "fat": 150.0, "fiber": 60.0}

FEATURE_LABELS = {
    "glu_now": ("Current glucose", "{:.0f} mg/dL"),
    "glu_chg_15m": ("Glucose change, last 15 min", "{:+.0f} mg/dL"),
    "glu_chg_30m": ("Glucose change, last 30 min", "{:+.0f} mg/dL"),
    "glu_chg_60m": ("Glucose change, last hour", "{:+.0f} mg/dL"),
    "glu_mean_60m": ("Average glucose, last hour", "{:.0f} mg/dL"),
    "glu_std_60m": ("Glucose variability, last hour", "{:.0f} mg/dL"),
    "glu_max_120m": ("Highest glucose, last 2 hours", "{:.0f} mg/dL"),
    "hr_mean_30m": ("Heart rate, last 30 min", "{:.0f} bpm"),
    "mets_mean_30m": ("Activity intensity, last 30 min", "{:.1f} METs"),
    "act_kcal_60m": ("Activity energy, last hour", "{:.0f} kcal"),
    "carbs_3h": ("Carbs eaten, last 3 hours", "{:.0f} g"),
    "protein_3h": ("Protein eaten, last 3 hours", "{:.0f} g"),
    "fat_3h": ("Fat eaten, last 3 hours", "{:.0f} g"),
    "fiber_3h": ("Fiber eaten, last 3 hours", "{:.0f} g"),
    "min_since_meal": ("Time since last meal", "{:.0f} min"),
    "time_of_day": ("Circadian phase / time", None),
    "fasting_glu": ("Fasting glucose baseline", "{:.0f} mg/dL"),
    "hba1c": ("HbA1c baseline", "{:.1f}%"),
}


def render_patient_view() -> None:
    """Main entry point for Section 2: Patient View."""
    all_patients = list_patients(include_presets=True)
    if not all_patients:
        st.warning("No virtual patients available. Please create one in the Patients directory.")
        return

    patient_ids = [p["id"] for p in all_patients]
    default_id = st.session_state.get("selected_patient_id", "well_controlled_45")
    if default_id not in patient_ids:
        default_id = patient_ids[0]

    # Header controls
    sel_col, dur_col = st.columns([3, 1])
    selected_id = sel_col.selectbox(
        "Select Virtual Patient",
        patient_ids,
        index=patient_ids.index(default_id),
        format_func=lambda pid: next((f"{p['name']} ({p['type'].upper()})" for p in all_patients if p["id"] == pid), pid),
        key="patient_view_selector",
    )
    st.session_state["selected_patient_id"] = selected_id

    days_sim = dur_col.slider("Simulation Horizon (days)", min_value=1, max_value=14, value=7)

    # Load patient dataclass
    patient = load_patient(selected_id)
    prov_map = get_provenance_map(patient.to_dict())

    # Patient Header Banner
    with st.container():
        st.markdown(
            f"### 🔬 {patient.name} {badge_html('SIMULATED')}"
        )
        if patient.description:
            st.caption(f"**Clinical profile:** {patient.description}")
        st.markdown(
            f"**Demographics:** Age {patient.age} • {patient.sex} • Height {patient.height_cm} cm • "
            f"Weight {patient.weight_kg} kg • **BMI {patient.bmi:.1f} kg/m²** • "
            f"**HbA1c {patient.hba1c:.1f}%** • Seed: `{patient.seed}`"
        )

    # Run / Retrieve Cached Simulation
    p_json = json.dumps(patient.to_dict())
    gdf, sdf, feats = run_simulation_cached(p_json, days=days_sim)

    # Stylised Human Body Biometric Overview Card (Part 7)
    render_patient_body_overview(patient, simulation_df=gdf, prov_map=prov_map)

    st.divider()

    # Tabs
    tab_profile, tab_clinical, tab_wearables, tab_meals, tab_risk = st.tabs([
        "📋 Profile & Labs",
        "🧬 Clinical & Genetics",
        "⌚ Wearables & Sensors",
        "🍽️ Meal Log",
        "⚡ Spike Risk & What-If",
    ])

    # ── TAB 1: Profile & Labs ────────────────────────────────────────────────
    with tab_profile:
        st.markdown(f"#### Demographics & Laboratory Panel {badge_html('SIMULATED')}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Age", f"{patient.age} yrs")
        c2.metric("Sex", "Male" if patient.sex == "M" else "Female")
        c3.metric("Height / Weight", f"{patient.height_cm:.0f} cm / {patient.weight_kg:.1f} kg")
        c4.metric("Body Mass Index (BMI)", f"{patient.bmi:.1f} kg/m²")

        st.divider()
        st.markdown("##### Glycemic & Metabolic Biomarkers")
        g1, g2, g3, g4 = st.columns(4)
        g1.metric("HbA1c", f"{patient.hba1c:.1f}%", help="Glycated hemoglobin")
        g2.metric("Fasting Glucose", f"{patient.fasting_glucose:.0f} mg/dL")
        g3.metric("Effective Fasting Glucose", f"{patient.effective_fasting_glucose:.0f} mg/dL", help="Calculated with insulin resistance & medications")
        g4.metric("Fasting Insulin", f"{patient.insulin:.1f} μU/mL")

        st.divider()
        st.markdown("##### Lipid Panel")
        l1, l2, l3, l4 = st.columns(4)
        l1.metric("Triglycerides", f"{patient.triglycerides:.0f} mg/dL")
        l2.metric("Total Cholesterol", f"{patient.total_cholesterol:.0f} mg/dL")
        l3.metric("HDL Cholesterol", f"{patient.hdl:.0f} mg/dL")
        l4.metric("LDL Cholesterol", f"{patient.ldl:.0f} mg/dL")

        st.divider()
        st.markdown("##### Insulin Resistance (IR) Model")
        ir_col1, ir_col2 = st.columns([1, 2])
        ir_col1.metric("Modelled IR Index", f"{patient.insulin_resistance:.2f}", help="1.0 = baseline healthy sensitivity")
        ir_col2.caption(
            "Insulin resistance is derived additively from excess HbA1c, excess BMI (>22), "
            "and polygenic risk variance. (Assumption, not learned from data)."
        )

    # ── TAB 2: Diagnoses, Medications & Genetics ─────────────────────────────
    with tab_clinical:
        st.markdown(f"#### Clinical Record & Genetics {badge_html('SIMULATED')}")
        
        col_diag, col_med = st.columns(2)
        with col_diag:
            st.markdown(f"##### Diagnoses {badge_html(prov_map.get('diagnoses', 'SIMULATED'))}")
            if patient.diagnoses:
                for d in patient.diagnoses:
                    st.markdown(f"- 🩺 **{d}**")
            else:
                st.info("No recorded chronic diagnoses.")

        with col_med:
            st.markdown(f"##### Medications {badge_html(prov_map.get('medications', 'SIMULATED'))}")
            if patient.medications:
                for m in patient.medications:
                    st.markdown(f"- 💊 **{m}**")
            else:
                st.info("No active medications.")

        st.divider()
        st.markdown(f"##### Genetic Markers & Polygenic Risk {badge_html('SIMULATED')}")
        
        gen_m1, gen_m2 = st.columns([1, 2])
        gen_m1.metric("Genetic Risk Score", f"{patient.genetic_markers.genetic_risk_score:.1f} / 100")
        gen_m2.progress(patient.genetic_markers.genetic_risk_score / 100.0)

        st.markdown("**Variant Allele Counts (T2D Risk Variants):**")
        v_rows = []
        variant_descriptions = {
            "TCF7L2": "Transcription factor 7-like 2 (Beta-cell function & GLP-1 secretion)",
            "PPARG": "Peroxisome proliferator-activated receptor gamma (Adipocyte insulin sensitivity)",
            "KCNJ11": "Potassium inwardly-rectifying channel (ATP-sensitive K+ channel in beta cells)",
            "CDKAL1": "CDK5 regulatory subunit associated protein 1-like 1 (Proinsulin conversion)",
            "SLC30A8": "Solute carrier family 30 member 8 (Zinc transporter 8 in secretory vesicles)",
        }
        for v, count in patient.genetic_markers.variant_alleles.items():
            v_rows.append({
                "Gene Variant": v,
                "Risk Alleles (0/1/2)": count,
                "Biological Function": variant_descriptions.get(v, "T2D associated locus"),
                "Provenance": "SIMULATED",
            })
        st.dataframe(pd.DataFrame(v_rows), use_container_width=True, hide_index=True)

    # ── TAB 3: Wearables & Sensors ───────────────────────────────────────────
    with tab_wearables:
        st.markdown(f"#### Continuous Sensor Telemetry ({days_sim} Days) {badge_html('SIMULATED')}")
        
        # 1. Glucose Timeline with Meal Markers
        st.markdown(f"##### 1. Continuous Glucose Monitoring (CGM) {badge_html('SIMULATED')}")
        tir_good = ((gdf["libre"] >= 70) & (gdf["libre"] <= 180)).mean() * 100
        tir_high = (gdf["libre"] > 180).mean() * 100
        tir_low = (gdf["libre"] < 70).mean() * 100
        
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Mean Glucose", f"{gdf['libre'].mean():.1f} mg/dL")
        q2.metric("Time in Range (70–180)", f"{tir_good:.1f}%")
        q3.metric("Time > 180 mg/dL", f"{tir_high:.1f}%")
        q4.metric("Glucose SD", f"{gdf['libre'].std():.1f} mg/dL")

        fig_cgm, ax_cgm = plt.subplots(figsize=(11, 3.8))
        ax_cgm.plot(gdf["time"], gdf["libre"], color="#38bdf8", lw=1.5, label="Libre Glucose")
        ax_cgm.axhline(180, color="#ef4444", ls="--", lw=1.2, label="Spike Threshold (180)")
        ax_cgm.axhline(70, color="#f59e0b", ls="--", lw=1.0, label="Hypo Threshold (70)")
        ax_cgm.axhspan(70, 180, color="#10b981", alpha=0.08, label="Target Range")

        # Meal indicators
        meal_pts = gdf[gdf["carbs"] > 0]
        if not meal_pts.empty:
            for _, mrow in meal_pts.iterrows():
                ax_cgm.axvline(mrow["time"], color="#f97316", alpha=0.4, ls=":", lw=1)
            ax_cgm.scatter(meal_pts["time"], meal_pts["libre"], color="#f97316", s=18, zorder=5, label="Meal Logged")

        ax_cgm.set_ylabel("Glucose (mg/dL)", fontsize=9)
        ax_cgm.legend(loc="upper right", fontsize=8)
        fig_cgm.autofmt_xdate()
        st.pyplot(fig_cgm)
        plt.close(fig_cgm)

        st.divider()

        # 2. Sleep Hypnogram
        st.markdown(f"##### 2. Sleep Architecture & Hypnogram {badge_html('SIMULATED')}")
        stage_map = {"awake": 3, "rem": 2, "light": 1, "deep": 0}
        gdf["stage_num"] = gdf["sleep_stage"].map(stage_map)
        
        fig_sleep, ax_sleep = plt.subplots(figsize=(11, 2.5))
        ax_sleep.step(gdf["time"], gdf["stage_num"], where="post", color="#a855f7", lw=1.2)
        ax_sleep.set_yticks([0, 1, 2, 3])
        ax_sleep.set_yticklabels(["Deep", "Light", "REM", "Awake"], fontsize=8)
        ax_sleep.set_ylabel("Sleep Stage", fontsize=9)
        fig_sleep.autofmt_xdate()
        st.pyplot(fig_sleep)
        plt.close(fig_sleep)

        st.divider()

        # 3. Steps & Physical Activity
        st.markdown(f"##### 3. Physical Activity & Steps {badge_html('SIMULATED')}")
        fig_act, (ax_steps, ax_hr) = plt.subplots(2, 1, figsize=(11, 4.5), sharex=True)
        ax_steps.bar(gdf["time"], gdf["steps"], width=0.003, color="#10b981", alpha=0.7)
        ax_steps.set_ylabel("Steps / 5m", fontsize=9)

        ax_hr.plot(gdf["time"], gdf["hr"], color="#ec4899", lw=1.2, label="Heart Rate (bpm)")
        ax_hr.plot(gdf["time"], gdf["hrv_rmssd"], color="#6366f1", lw=1.2, ls="--", label="HRV RMSSD (ms)")
        ax_hr.set_ylabel("HR / HRV", fontsize=9)
        ax_hr.legend(loc="upper right", fontsize=8)
        fig_act.autofmt_xdate()
        st.pyplot(fig_act)
        plt.close(fig_act)

    # ── TAB 4: Meal Log ──────────────────────────────────────────────────────
    with tab_meals:
        st.markdown(f"#### Logged Meals & Nutritional Intake {badge_html('SIMULATED')}")
        
        meals_df = gdf[gdf["carbs"] > 0][["time", "meal_name", "carbs", "protein", "fat", "fiber", "act_kcal"]].copy()
        if not meals_df.empty:
            meals_df["time"] = meals_df["time"].dt.strftime("%Y-%m-%d %H:%M")
            meals_df = meals_df.rename(columns={
                "time": "Time",
                "meal_name": "Dish / Item",
                "carbs": "Carbs (g)",
                "protein": "Protein (g)",
                "fat": "Fat (g)",
                "fiber": "Fiber (g)",
                "act_kcal": "Energy (kcal)",
            })
            st.dataframe(meals_df, use_container_width=True, hide_index=True)
            
            tot_carbs = meals_df["Carbs (g)"].sum()
            avg_carbs = tot_carbs / max(days_sim, 1)
            st.caption(f"Total simulated carbohydrate intake: {tot_carbs:.0f} g across {len(meals_df)} meals (~{avg_carbs:.0f} g/day).")
        else:
            st.info("No meals were logged during this simulated window.")

    # ── TAB 5: Risk & What-If ────────────────────────────────────────────────
    with tab_risk:
        st.markdown(f"#### ⚡ 2-Hour Postprandial Glucose Spike Risk Assessment {badge_html('SIMULATED')}")
        st.caption("Evaluates glucose excursion above 180 mg/dL within the next 2 hours using the XGBoost spike classifier.")

        # Load models
        risk_model, meal_model, explainer = load_models()
        food_catalogue = load_indian_meals()
        risk_feats = risk_model["features"]

        # Date & Moment Selection Slider
        unique_dates = sorted(feats["time"].dt.date.unique())
        c_day, c_empty = st.columns([2, 2])
        chosen_date = c_day.selectbox("Choose Day to Assess", unique_dates, index=min(1, len(unique_dates)-1))
        
        day_feats = feats[feats["time"].dt.date == chosen_date]
        if day_feats.empty:
            st.warning("No data for chosen day.")
            return

        tmin = day_feats["time"].min().to_pydatetime()
        tmax = day_feats["time"].max().to_pydatetime()
        default_val = tmin + (tmax - tmin) / 2

        chosen_time = st.slider(
            "Select Evaluation Moment (Time Slider)",
            min_value=tmin,
            max_value=tmax,
            value=default_val,
            step=timedelta(minutes=5),
            format="HH:mm",
        )

        # Locate closest epoch
        pos = (day_feats["time"] - pd.Timestamp(chosen_time)).abs().argmin()
        eval_row = day_feats.iloc[pos]
        t0 = eval_row["time"]
        x_eval = day_feats.iloc[[pos]][risk_feats].astype(float)

        st.divider()

        # Risk Score Section
        left_col, right_col = st.columns([3, 2])

        with left_col:
            st.markdown(f"##### Local Glucose Window Around {t0.strftime('%a %d %b, %H:%M')}")
            win_df = feats[(feats["time"] >= t0 - timedelta(hours=6)) & (feats["time"] <= t0 + timedelta(hours=2))]
            
            fig_win, ax_win = plt.subplots(figsize=(7.5, 3.4))
            past_df = win_df[win_df["time"] <= t0]
            future_df = win_df[win_df["time"] >= t0]
            
            ax_win.plot(past_df["time"], past_df["glu_now"], color="#38bdf8", lw=2, label="Glucose so far")
            ax_win.plot(future_df["time"], future_df["glu_now"], color="#38bdf8", ls="--", alpha=0.5, label="Next 2h outcome")
            ax_win.axhline(THR, color="#ef4444", ls="--", lw=1, label="Threshold (180)")
            ax_win.axvline(t0, color="#94a3b8", lw=1.2, label="Evaluation Point (t0)")

            # Mark meals in window
            m_win = gdf[(gdf["time"] >= win_df["time"].min()) & (gdf["time"] <= win_df["time"].max()) & (gdf["carbs"] > 0)]
            for mt in m_win["time"]:
                ax_win.axvline(mt, color="#f97316", alpha=0.7, lw=1.2)
            if not m_win.empty:
                ax_win.plot([], [], color="#f97316", label="Meal Logged")

            ax_win.set_ylabel("mg/dL", fontsize=8)
            ax_win.legend(loc="upper left", fontsize=7)
            fig_win.autofmt_xdate()
            st.pyplot(fig_win)
            plt.close(fig_win)

        with right_col:
            st.markdown("##### Spike Risk Prediction")
            
            glu_val = eval_row["glu_now"]
            if glu_val < 70:
                st.warning("⚠️ Hypoglycemia Alert: Glucose is below 70 mg/dL. This tool predicts spikes only.")
            
            if glu_val > THR:
                st.info(f"ℹ️ Current glucose is already {glu_val:.0f} mg/dL (above {THR}). Model evaluates transitions into spikes.")
            else:
                prob = float(risk_model["model"].predict_proba(x_eval)[0, 1])
                
                # Low / Watch / High thresholds (0.75 and 0.91)
                if prob >= HIGH:
                    st.error(f"🚨 **HIGH RISK** ({prob:.1%})\n\nSignificant probability of glucose spike > 180 mg/dL in next 2 hours.")
                elif prob >= WATCH:
                    st.warning(f"⚠️ **WATCH** ({prob:.1%})\n\nModerate risk of spike. Continuous monitoring recommended.")
                else:
                    st.success(f"✅ **LOW RISK** ({prob:.1%})\n\nGlucose expected to stay at or below 180 mg/dL.")

                # SHAP Explanation Grouped as in dashboard.py
                st.markdown("###### Top Reasons (SHAP Contributions)")
                sv = explainer.shap_values(x_eval)
                sv = sv[1] if isinstance(sv, list) else sv
                
                groups = {f: f for f in risk_feats}
                groups["hour_sin"] = groups["hour_cos"] = "time_of_day"
                contrib = pd.Series(sv[0], index=risk_feats).groupby(groups).sum().sort_values()
                # Exclude static age/bmi/male
                contrib = contrib.drop(["age", "bmi", "male"], errors="ignore")

                def describe_feature(f_name):
                    label, fmt = FEATURE_LABELS.get(f_name, (f_name, "{:.1f}"))
                    if f_name == "time_of_day":
                        return f"{label}: {t0.strftime('%H:%M')}"
                    val = eval_row.get(f_name, 0.0)
                    return f"{label}: {fmt.format(val)}"

                top_positive = contrib[contrib > 0].tail(3)[::-1]
                top_negative = contrib[contrib < 0].head(2)

                for f in top_positive.index:
                    st.write(f"▲ **Raises risk:** {describe_feature(f)}")
                for f in top_negative.index:
                    st.write(f"▼ **Lowers risk:** {describe_feature(f)}")

        st.divider()

        # Meal What-If Sandbox
        st.markdown(f"#### 🍛 Meal What-If: Postprandial Response Simulation {badge_html('SIMULATED')}")
        st.caption("Predicts peak glucose excursion within 2 hours if the patient consumes a specific meal right now.")

        chosen_dishes = st.multiselect("Select Dishes from Catalogue", food_catalogue["dish"].tolist())
        totals = {"carbs": 0.0, "protein": 0.0, "fat": 0.0, "fiber": 0.0}

        if chosen_dishes:
            portion_cols = st.columns(min(len(chosen_dishes), 4))
            for i, dish in enumerate(chosen_dishes):
                col_idx = i % len(portion_cols)
                p_num = portion_cols[col_idx].number_input(f"{dish} (portions)", 0.5, 4.0, 1.0, 0.5, key=f"whatif_{dish}")
                dish_row = food_catalogue[food_catalogue["dish"] == dish].iloc[0]
                for macro in totals:
                    totals[macro] += p_num * dish_row[macro]

            # Caps
            capped = {k: min(v, CAPS[k]) for k, v in totals.items()}
            st.markdown(
                f"**Total Meal Nutrition:** {totals['carbs']:.0f}g Carbs • {totals['protein']:.0f}g Protein • "
                f"{totals['fat']:.0f}g Fat • {totals['fiber']:.0f}g Fiber"
            )

            # Build prediction row for Random Forest meal response
            m_row = pd.DataFrame([{
                **capped,
                "glu0": eval_row["glu_now"],
                "hour": t0.hour + t0.minute / 60.0,
                "age": eval_row["age"],
                "bmi": eval_row["bmi"],
                "hba1c": eval_row["hba1c"],
                "fasting_glu": eval_row["fasting_glu"],
                "male": eval_row["male"],
            }])[meal_model["features"]]

            predicted_rise = float(meal_model["model"].predict(m_row)[0])
            predicted_peak = eval_row["glu_now"] + predicted_rise

            r_col1, r_col2 = st.columns([1, 2])
            r_col1.metric(
                "Predicted Peak Glucose",
                f"{predicted_peak:.0f} mg/dL",
                f"Range: {predicted_peak - MEAL_ERR:.0f} – {predicted_peak + MEAL_ERR:.0f} mg/dL",
                delta_color="off",
            )
            with r_col2:
                if predicted_peak - MEAL_ERR > THR:
                    st.error(f"Likely to exceed spike threshold ({THR} mg/dL).")
                elif predicted_peak + MEAL_ERR > THR:
                    st.warning(f"Could exceed spike threshold ({THR} mg/dL).")
                else:
                    st.success(f"Unlikely to exceed spike threshold ({THR} mg/dL).")
                st.caption(
                    "Model trained on 44 CGMacros clinical meal records. "
                    "Database dish nutritional values are estimated."
                )
