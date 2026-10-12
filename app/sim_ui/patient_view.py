"""
Patient View: Simulation, Biometrics, Spike Risk & What-If.
============================================================

Layout (in strict adherence to clinical workspace specification):
1. Patient header: name, age, sex, diagnosis summary, time-of-day slider.
2. Row of six summary cards: heart rate, glucose, HbA1c, sleep, HRV, steps with trend lines.
3. Risk panel: risk level (LOW/WATCH/HIGH), top reasons (SHAP), explanation.
4. 24-hour glucose chart with meals, 180 mg/dL line, and 2-hour prediction window.
5. Sensor telemetry grid: sleep hypnogram, steps, HR & HRV.
6. Clinical records: profile & labs table, diagnoses, medications, genetics, meal log & what-if.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, time, date
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
from app.sim_ui.theme import (
    render_patient_body_overview,
    BG_APP,
    PRIMARY, PRIMARY_DARK, PRIMARY_TINT, BORDER,
    TEXT_MAIN, TEXT_SECONDARY,
    CHART_LINE_MAIN, CHART_LINE_BASELINE, CHART_THRESHOLD,
    CHART_HYPO, CHART_MEAL, CHART_RANGE_FILL,
    CHART_SLEEP, CHART_STEPS, CHART_HR, CHART_HRV,
    STATUS_OK, STATUS_WATCH, STATUS_HIGH,
    BADGE_REAL_BG, BADGE_REAL_BORDER, BADGE_REAL_TEXT,
)

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
    "fasting_glu": ("Simulated overnight sensor baseline", "{:.0f} mg/dL"),
    "hba1c": ("HbA1c baseline", "{:.1f}%"),
}


def render_patient_view() -> None:
    """Main entry point for Section: Patient View."""
    all_patients = list_patients(include_presets=True)
    if not all_patients:
        st.warning("No virtual patients available. Please create one in the Patients directory.")
        return

    patient_ids = [p["id"] for p in all_patients]
    selected_id = st.session_state.get("selected_patient_id", "well_controlled_45")
    if selected_id not in patient_ids:
        selected_id = patient_ids[0]
        st.session_state["selected_patient_id"] = selected_id

    # Load patient dataclass
    patient = load_patient(selected_id)
    prov_map = get_provenance_map(patient.to_dict())

    # Run / retrieve cached simulation (7-day standard horizon)
    p_json = json.dumps(patient.to_dict())
    gdf, sdf, feats = run_simulation_cached(p_json, days=7)

    # Available dates in simulation
    unique_dates = sorted(feats["time"].dt.date.unique())
    chosen_day_idx = min(1, len(unique_dates) - 1)

    # ─── 1. Patient Header with Demographics and Time Slider ────────────────
    st.markdown(
        f"""
        <div class="patient-header">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
                <div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px; font-weight: 700; color: {PRIMARY_DARK};">
                            {patient.name}
                        </span>
                        {badge_html('SIMULATED')}
                    </div>
                    <div style="font-size: 13px; color: {TEXT_SECONDARY}; margin-top: 4px;">
                        Age {patient.age} · {'Male' if patient.sex == 'M' else 'Female'} ·
                        Height {patient.height_cm:.0f} cm · Weight {patient.weight_kg:.1f} kg ·
                        <strong>BMI {patient.bmi:.1f} kg/m²</strong> ·
                        <strong>HbA1c {patient.hba1c:.1f}%</strong> ·
                        Fasting Glu {patient.displayed_fasting_glucose:.0f} mg/dL · Seed: <span style="color: {TEXT_SECONDARY};">{patient.seed}</span>
                    </div>
                    <div style="font-size: 12px; color: {TEXT_MAIN}; margin-top: 4px; font-weight: 500;">
                        Clinical summary: {patient.description or 'Synthetic patient persona.'}
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Date and Time-of-Day Slider Row
    slider_c1, slider_c2 = st.columns([1.35, 2.65])
    with slider_c1:
        chosen_date = st.selectbox(
            "Evaluation Date",
            unique_dates,
            index=chosen_day_idx,
            format_func=lambda d: d.strftime("%A, %d %b"),
            key="pv_eval_date",
        )

    day_feats = feats[feats["time"].dt.date == chosen_date]
    if day_feats.empty:
        day_feats = feats.iloc[:288]

    tmin = day_feats["time"].min().to_pydatetime()
    tmax = day_feats["time"].max().to_pydatetime()
    default_val = tmin + timedelta(hours=12)
    if default_val > tmax:
        default_val = tmin + (tmax - tmin) / 2

    with slider_c2:
        chosen_time = st.slider(
            "Time-of-Day Slider (Evaluation Moment t0)",
            min_value=tmin,
            max_value=tmax,
            value=default_val,
            step=timedelta(minutes=5),
            format="HH:mm",
            key="pv_eval_time_slider",
            help="Select instantaneous moment to inspect spike risk and continuous sensor telemetry.",
        )

    # Locate closest 5-minute epoch
    pos = (day_feats["time"] - pd.Timestamp(chosen_time)).abs().argmin()
    eval_row = day_feats.iloc[pos]
    t0 = eval_row["time"]

    # ─── 2. Row of Six Summary Cards with Trend Lines ───────────────────────
    render_patient_body_overview(
        patient,
        simulation_df=gdf,
        prov_map=prov_map,
        current_time=t0,
    )

    # ─── 3. Risk Panel: Spike Risk Assessment at t0 ─────────────────────────
    risk_model, meal_model, explainer = load_models()
    risk_feats = risk_model["features"]
    x_eval = day_feats.iloc[[pos]][risk_feats].astype(float)
    glu_val = eval_row["glu_now"]

    st.markdown(
        f"""
        <div style="font-size: 15px; font-weight: 700; color: {PRIMARY_DARK}; margin: 8px 0 6px 0;">
            2-Hour Glucose Spike Risk Assessment at {t0.strftime('%H:%M')} {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    prob = float(risk_model["model"].predict_proba(x_eval)[0, 1])

    if glu_val > THR:
        risk_class = "risk-high"
        level_str = "CURRENTLY EXCEEDING THRESHOLD"
        badge_color = STATUS_HIGH
        desc_str = f"Current glucose is already {glu_val:.0f} mg/dL (above {THR} mg/dL threshold)."
    elif prob >= HIGH:
        risk_class = "risk-high"
        level_str = f"HIGH RISK ({prob:.1%})"
        badge_color = STATUS_HIGH
        desc_str = "High statistical likelihood of glucose excursion exceeding 180 mg/dL within the next 2 hours."
    elif prob >= WATCH:
        risk_class = "risk-watch"
        level_str = f"WATCH ({prob:.1%})"
        badge_color = STATUS_WATCH
        desc_str = "Moderate spike probability. Close glycemic surveillance advised."
    else:
        risk_class = "risk-ok"
        level_str = f"LOW RISK ({prob:.1%})"
        badge_color = STATUS_OK
        desc_str = "Glucose expected to remain safely below the 180 mg/dL threshold over the next 2 hours."

    # Compute SHAP top positive and negative reasons
    sv = explainer.shap_values(x_eval)
    sv = sv[1] if isinstance(sv, list) else sv
    groups = {f: f for f in risk_feats}
    groups["hour_sin"] = groups["hour_cos"] = "time_of_day"
    contrib = pd.Series(sv[0], index=risk_feats).groupby(groups).sum().sort_values()
    contrib = contrib.drop(["age", "bmi", "male"], errors="ignore")

    def describe_feature(f_name: str) -> str:
        label, fmt = FEATURE_LABELS.get(f_name, (f_name, "{:.1f}"))
        if f_name == "time_of_day":
            return f"{label}: {t0.strftime('%H:%M')}"
        val = eval_row.get(f_name, 0.0)
        return f"{label}: {fmt.format(val)}"

    top_pos = contrib[contrib > 0].tail(2)[::-1]
    top_neg = contrib[contrib < 0].head(2)

    pos_reasons_html = "".join([f"<div>• <strong>Raises risk:</strong> {describe_feature(f)}</div>" for f in top_pos.index])
    neg_reasons_html = "".join([f"<div>• <strong>Lowers risk:</strong> {describe_feature(f)}</div>" for f in top_neg.index])

    risk_panel_html = f"""
    <div class="risk-panel {risk_class}">
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px;">
            <div style="font-size: 16px; font-weight: 700; color: {badge_color};">
                {level_str}
            </div>
            <div style="font-size: 12px; color: {TEXT_SECONDARY};">
                Evaluation moment: {t0.strftime('%a %d %b %H:%M')} · Interstitial Glucose: {glu_val:.0f} mg/dL
            </div>
        </div>
        <div style="font-size: 13px; color: {TEXT_MAIN}; margin: 6px 0 10px 0;">
            {desc_str}
        </div>
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 12px; color: {TEXT_MAIN};
                    background-color: {BG_APP}; border: 1px solid {BORDER}; border-radius: 6px; padding: 10px 14px;">
            <div>{pos_reasons_html if pos_reasons_html else '<div>• No acute risk-raising triggers</div>'}</div>
            <div>{neg_reasons_html if neg_reasons_html else '<div>• No protective mitigators active</div>'}</div>
        </div>
        <div style="font-size: 11px; color: {TEXT_SECONDARY}; margin-top: 8px;">
            Spike probability represents the calibrated likelihood of exceeding 180 mg/dL in the subsequent 120-minute window.
            Trained on CGMacros clinical dataset features.
        </div>
    </div>
    """
    st.markdown(risk_panel_html, unsafe_allow_html=True)

    # ─── 4. 24-Hour Glucose Chart with Prediction Window ────────────────────
    st.markdown(
        f"""
        <div style="font-size: 15px; font-weight: 700; color: {PRIMARY_DARK}; margin: 12px 0 4px 0;">
            24-Hour Continuous Glucose Trajectory & 2-Hour Prediction Window {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Filter 24h of simulation around chosen date
    day_start = pd.Timestamp(chosen_date)
    day_end = day_start + timedelta(days=1)
    day_cgm = gdf[(gdf["time"] >= day_start) & (gdf["time"] < day_end)].copy()
    if day_cgm.empty:
        day_cgm = gdf.iloc[:288].copy()

    fig_cgm, ax_cgm = plt.subplots(figsize=(11, 3.4))
    ax_cgm.plot(day_cgm["time"], day_cgm["libre"], color=CHART_LINE_MAIN, lw=1.8, label="Libre CGM")
    ax_cgm.axhline(THR, color=CHART_THRESHOLD, ls="--", lw=1.2, label="Spike Threshold (180 mg/dL)")
    ax_cgm.axhline(70, color=CHART_HYPO, ls=":", lw=1.0, label="Hypo Threshold (70 mg/dL)")
    ax_cgm.axhspan(70, 180, color=CHART_RANGE_FILL, alpha=0.05, label="Target Range (70–180)")

    # 2-Hour Prediction Window highlight
    win_end = min(t0 + timedelta(hours=2), day_end)
    ax_cgm.axvspan(t0, win_end, color=PRIMARY, alpha=0.10, label="2h Prediction Window")
    ax_cgm.axvline(t0, color=PRIMARY_DARK, lw=1.5, ls="-", label=f"Evaluation t0 ({t0.strftime('%H:%M')})")

    # Logged meals in the 24h window
    day_meals = day_cgm[day_cgm["carbs"] > 0]
    if not day_meals.empty:
        for _, mrow in day_meals.iterrows():
            ax_cgm.axvline(mrow["time"], color=CHART_MEAL, alpha=0.5, ls="--", lw=1)
        ax_cgm.scatter(
            day_meals["time"],
            day_meals["libre"],
            color=CHART_MEAL,
            s=28,
            zorder=6,
            label="Logged Meal",
        )

    ax_cgm.set_ylabel("Glucose (mg/dL)", fontsize=9)
    ax_cgm.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4, fontsize=8, frameon=False)
    ax_cgm.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig_cgm.autofmt_xdate()
    st.pyplot(fig_cgm)
    plt.close(fig_cgm)
    st.caption("Simulated values mimic a FreeStyle Libre-type sensor, which reads lower than a venous lab test overnight, as in the real CGMacros data.")

    st.divider()

    # ─── 5. Sensor Telemetry Grid (Sleep, Steps, HR, HRV) ───────────────────
    st.markdown(
        f"""
        <div style="font-size: 15px; font-weight: 700; color: {PRIMARY_DARK}; margin: 8px 0 6px 0;">
            Continuous Sensor Telemetry Grid (24-Hour Sensor Alignment) {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    grid_c1, grid_c2 = st.columns(2)

    # Left: Sleep Stage Hypnogram
    with grid_c1:
        st.markdown(
            f"""
            <div style="font-size: 13.5px; font-weight: 600; color: {PRIMARY_DARK}; margin-bottom: 6px;">
                Sleep Architecture (Hypnogram) {badge_html('SIMULATED')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        stage_map = {"awake": 3, "rem": 2, "light": 1, "deep": 0}
        day_cgm["stage_num"] = day_cgm["sleep_stage"].map(stage_map)

        fig_sl, ax_sl = plt.subplots(figsize=(6, 2.5))
        ax_sl.step(day_cgm["time"], day_cgm["stage_num"], where="post", color=CHART_SLEEP, lw=1.5)
        ax_sl.set_yticks([0, 1, 2, 3])
        ax_sl.set_yticklabels(["Deep", "Light", "REM", "Awake"], fontsize=8)
        ax_sl.set_ylabel("Stage", fontsize=8)
        ax_sl.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig_sl.autofmt_xdate()
        st.pyplot(fig_sl)
        plt.close(fig_sl)

    # Right: Steps & Physical Activity
    with grid_c2:
        st.markdown(
            f"""
            <div style="font-size: 13.5px; font-weight: 600; color: {PRIMARY_DARK}; margin-bottom: 6px;">
                Physical Activity & Steps {badge_html('SIMULATED')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_st, ax_st = plt.subplots(figsize=(6, 2.5))
        ax_st.bar(day_cgm["time"], day_cgm["steps"], width=0.003, color=CHART_STEPS, alpha=0.8)
        ax_st.set_ylabel("Steps / 5m", fontsize=8)
        ax_st.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        fig_st.autofmt_xdate()
        st.pyplot(fig_st)
        plt.close(fig_st)

    # Heart Rate & HRV Telemetry
    st.markdown(
        f"""
        <div style="font-size: 13.5px; font-weight: 600; color: {PRIMARY_DARK}; margin: 10px 0 6px 0;">
            Heart Rate & HRV Continuous Telemetry {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )
    fig_hr, ax_hr = plt.subplots(figsize=(11, 2.3))
    ax_hr.plot(day_cgm["time"], day_cgm["hr"], color=CHART_HR, lw=1.3, label="Heart Rate (bpm)")
    ax_hr.plot(day_cgm["time"], day_cgm["hrv_rmssd"], color=CHART_HRV, lw=1.3, ls="--", label="HRV RMSSD (ms)")
    ax_hr.axvline(t0, color=PRIMARY_DARK, lw=1.2, ls=":", label="t0")
    ax_hr.set_ylabel("BPM / ms", fontsize=8)
    ax_hr.legend(loc="upper right", fontsize=8)
    ax_hr.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    fig_hr.autofmt_xdate()
    st.pyplot(fig_hr)
    plt.close(fig_hr)

    st.divider()

    # ─── 6. Profile & Labs Table, Diagnoses, Medications, Genetics, Meals ───
    st.markdown(
        f"""
        <div style="font-size: 15px; font-weight: 700; color: {PRIMARY_DARK}; margin: 8px 0 6px 0;">
            Clinical Profile, Genetic Markers & Dietary Logs {badge_html('SIMULATED')}
        </div>
        """,
        unsafe_allow_html=True,
    )

    t_prof, t_meds, t_gen, t_meals, t_whatif = st.tabs([
        "Profile & Labs Table",
        "Diagnoses & Medications",
        "Genetic Markers",
        "Meal Log",
        "Meal What-If Sandbox",
    ])

    with t_prof:
        st.markdown(
            f"""
            <div style="font-size: 15px; font-weight: 700; color: {PRIMARY_DARK}; margin: 8px 0 6px 0;">
                Demographics and Laboratory Panel {badge_html('SIMULATED')}
            </div>
            """,
            unsafe_allow_html=True,
        )
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Age", f"{patient.age} yrs")
        c2.metric("Sex", "Male" if patient.sex == "M" else "Female")
        c3.metric("Height / Weight", f"{patient.height_cm:.0f} cm / {patient.weight_kg:.1f} kg")
        c4.metric("Body Mass Index (BMI)", f"{patient.bmi:.1f} kg/m²")

        g1, g2, g3, g4 = st.columns(4)
        g1.metric("HbA1c", f"{patient.hba1c:.1f}%")
        g2.metric("Lab fasting glucose (venous, entered)", f"{patient.displayed_fasting_glucose:.0f} mg/dL")
        g3.metric("Simulated overnight sensor baseline", f"{patient.effective_fasting_glucose:.0f} mg/dL")
        g4.metric("Fasting Insulin", f"{patient.insulin:.1f} μU/mL")

        st.divider()
        st.markdown("##### Complete Laboratory Panel Table")
        labs_data = [
            {"Parameter": "Age", "Value": f"{patient.age}", "Unit": "years", "Provenance": "SIMULATED", "Notes": "Demographic baseline"},
            {"Parameter": "Sex", "Value": "Male" if patient.sex == "M" else "Female", "Unit": "", "Provenance": "SIMULATED", "Notes": "Biological sex"},
            {"Parameter": "Height", "Value": f"{patient.height_cm:.0f}", "Unit": "cm", "Provenance": "SIMULATED", "Notes": "Physical measurement"},
            {"Parameter": "Weight", "Value": f"{patient.weight_kg:.1f}", "Unit": "kg", "Provenance": "SIMULATED", "Notes": "Physical measurement"},
            {"Parameter": "Body Mass Index (BMI)", "Value": f"{patient.bmi:.1f}", "Unit": "kg/m²", "Provenance": "SIMULATED", "Notes": f"Target: 18.5–24.9"},
            {"Parameter": "HbA1c", "Value": f"{patient.hba1c:.1f}", "Unit": "%", "Provenance": "SIMULATED", "Notes": "Glycated hemoglobin (PDL standard)"},
            {"Parameter": "Lab fasting glucose (venous, entered)", "Value": f"{patient.displayed_fasting_glucose:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "Entered laboratory fasting glucose (or derived from HbA1c)"},
            {"Parameter": "Simulated overnight sensor baseline", "Value": f"{patient.effective_fasting_glucose:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "Simulator overnight sensor baseline (Libre-style, modeled with IR & medications)"},
            {"Parameter": "Fasting Insulin", "Value": f"{patient.insulin:.1f}", "Unit": "μU/mL", "Provenance": "SIMULATED", "Notes": "Endogenous insulin concentration"},
            {"Parameter": "Modelled IR Index", "Value": f"{patient.insulin_resistance:.2f}", "Unit": "ratio", "Provenance": "SIMULATED", "Notes": "1.0 = healthy baseline sensitivity"},
            {"Parameter": "Triglycerides", "Value": f"{patient.triglycerides:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "Lipid profile (Normal < 150)"},
            {"Parameter": "Total Cholesterol", "Value": f"{patient.total_cholesterol:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "Lipid profile (Normal < 200)"},
            {"Parameter": "HDL Cholesterol", "Value": f"{patient.hdl:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "High-density lipoprotein (> 40 M, > 50 F)"},
            {"Parameter": "LDL Cholesterol", "Value": f"{patient.ldl:.0f}", "Unit": "mg/dL", "Provenance": "SIMULATED", "Notes": "Low-density lipoprotein (Optimal < 100)"},
        ]
        st.table(pd.DataFrame(labs_data))

    with t_meds:
        col_d, col_m = st.columns(2)
        with col_d:
            st.markdown(f"##### Chronic Diagnoses {badge_html(prov_map.get('diagnoses', 'SIMULATED'))}", unsafe_allow_html=True)
            if patient.diagnoses:
                for d in patient.diagnoses:
                    st.markdown(f"- **{d}**")
            else:
                st.info("No recorded diagnoses.")
        with col_m:
            st.markdown(f"##### Active Pharmacotherapy {badge_html(prov_map.get('medications', 'SIMULATED'))}", unsafe_allow_html=True)
            if patient.medications:
                for m in patient.medications:
                    st.markdown(f"- **{m}**")
            else:
                st.info("No active medications.")

    with t_gen:
        st.markdown(f"##### Genetic Markers & Polygenic Risk {badge_html('SIMULATED')}", unsafe_allow_html=True)
        gm1, gm2 = st.columns([1, 2])
        gm1.metric("Composite Risk Score", f"{patient.genetic_markers.genetic_risk_score:.1f} / 100")
        gm2.progress(patient.genetic_markers.genetic_risk_score / 100.0)

        v_rows = []
        variant_desc = {
            "TCF7L2": "Transcription factor 7-like 2 (Beta-cell function & GLP-1 secretion)",
            "PPARG": "Peroxisome proliferator-activated receptor gamma (Adipocyte insulin sensitivity)",
            "KCNJ11": "Potassium inwardly-rectifying channel (ATP-sensitive K+ channel in beta cells)",
            "CDKAL1": "CDK5 regulatory subunit associated protein 1-like 1 (Proinsulin conversion)",
            "SLC30A8": "Solute carrier family 30 member 8 (Zinc transporter 8 in secretory vesicles)",
        }
        for v, cnt in patient.genetic_markers.variant_alleles.items():
            v_rows.append({
                "Gene Variant": v,
                "Risk Alleles (0/1/2)": cnt,
                "Biological Mechanism": variant_desc.get(v, "T2D associated locus"),
                "Provenance": "SIMULATED",
            })
        st.dataframe(pd.DataFrame(v_rows), use_container_width=True, hide_index=True)

    with t_meals:
        st.markdown(f"##### Logged Dietary Intake (7 Days) {badge_html('SIMULATED')}", unsafe_allow_html=True)
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
            st.caption(f"Total simulated meals: {len(meals_df)} across 7 days (~{meals_df['Carbs (g)'].sum() / 7:.0f} g carbs/day).")
        else:
            st.info("No meals recorded.")

    with t_whatif:
        st.markdown(f"##### Meal What-If: Postprandial Response Simulation {badge_html('SIMULATED')}", unsafe_allow_html=True)
        st.caption("Predicts peak glucose excursion within 2 hours if this meal is ingested at the current evaluation moment.")
        food_catalogue = load_indian_meals()
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

            capped = {k: min(v, CAPS[k]) for k, v in totals.items()}
            st.markdown(
                f"**Meal Nutrition:** {totals['carbs']:.0f}g Carbs · {totals['protein']:.0f}g Protein · "
                f"{totals['fat']:.0f}g Fat · {totals['fiber']:.0f}g Fiber"
            )

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
                    st.error(f"High risk of exceeding spike threshold ({THR} mg/dL).")
                elif predicted_peak + MEAL_ERR > THR:
                    st.warning(f"Borderline: could exceed spike threshold ({THR} mg/dL).")
                else:
                    st.success(f"Favorable: unlikely to exceed spike threshold ({THR} mg/dL).")
                st.caption("Random Forest meal response model calibrated on CGMacros clinical meal records.")
