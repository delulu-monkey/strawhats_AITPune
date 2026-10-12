"""
Real Reference Patients (CGMacros Study Cohort).
================================================

Honesty Rules Enforcement:
- Displays all 45 real human participants from data/raw/cgmacros/CGMacros/bio.csv.
- Real observed fields are clearly labelled with the REAL badge.
- Fields the study protocol did not collect (sleep stages, steps, HRV, genetics,
  diagnoses, medications) are strictly labelled with the NOT AVAILABLE badge.
- Never attaches simulated values or synthetic estimates to real participants.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from app.sim_ui.common import load_real_bio_data
from app.sim_ui.badges import badge_html, label_with_badge
from app.sim_ui.theme import (
    render_patient_body_overview,
    CHART_LINE_MAIN, CHART_THRESHOLD, CHART_HYPO, CHART_MEAL,
    TEXT_MAIN, TEXT_SECONDARY,
)


@st.cache_data
def load_real_cgm_participant(subject_num: int) -> pd.DataFrame:
    """Load real CGM and meal time-series for a specific CGMacros participant."""
    cgm_path = Path("data/processed/cgmacros_all.csv.gz")
    if not cgm_path.exists():
        return pd.DataFrame()
    df = pd.read_csv(
        cgm_path,
        parse_dates=["time"],
        usecols=["subject", "time", "libre", "hr", "carbs", "meal_type"],
    )
    return df[df["subject"] == subject_num]


def render_real_patients() -> None:
    """Main entry point for Section 3: Real Reference Patients."""
    st.markdown("## Real Reference Patients (CGMacros Cohort)")
    st.caption(
        "Read-only clinical records for the 45 human participants from the CGMacros "
        "continuous glucose monitoring study. Under **Honesty Rule 2**, variables "
        "not collected in the original protocol are explicitly marked **NOT AVAILABLE**."
    )

    bio_df = load_real_bio_data()

    # Overview Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Participants", len(bio_df))
    healthy_cnt = (bio_df["group"] == "healthy").sum()
    prediab_cnt = (bio_df["group"] == "prediabetes").sum()
    t2d_cnt = (bio_df["group"] == "t2d").sum()
    c2.markdown(
        f"""
        <div class="biometric-card" style="padding: 10px 14px; min-height: 82px;">
            <div style="font-size: 12px; font-weight: 600; color: {TEXT_SECONDARY};">Cohort Breakdown</div>
            <div style="font-size: 14px; font-weight: 700; color: {TEXT_MAIN}; margin-top: 4px; line-height: 1.4; word-break: break-word;">
                {healthy_cnt} healthy, {prediab_cnt} prediabetes, {t2d_cnt} T2D
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c3.markdown(
        f"<div style='padding-top: 14px;'>{badge_html('REAL')} Ground truth EHR</div>",
        unsafe_allow_html=True,
    )
    c4.markdown(
        f"<div style='padding-top: 14px;'>{badge_html('NOT AVAILABLE')} Missing sensors</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Participant Selector
    subjects = bio_df["subject"].tolist()
    subj_labels = {
        s: f"{bio_df[bio_df['subject'] == s]['subject_str'].iloc[0]} ({bio_df[bio_df['subject'] == s]['group'].iloc[0].upper()}, Age {bio_df[bio_df['subject'] == s]['age'].iloc[0]}, A1c {bio_df[bio_df['subject'] == s]['hba1c'].iloc[0]:.1f}%)"
        for s in subjects
    }
    
    current_real = st.session_state.get("selected_real_subject", 3)
    if current_real not in subjects:
        default_subjs = bio_df[bio_df["group"] == "t2d"]["subject"].tolist()
        current_real = default_subjs[0] if default_subjs else subjects[0]
        st.session_state["selected_real_subject"] = current_real

    def _on_page_real_change():
        val = st.session_state.get("page_real_patient_selector")
        if val is not None:
            st.session_state["selected_real_subject"] = val
            st.session_state["sidebar_real_participant_selector"] = val

    cur_idx = subjects.index(current_real) if ("page_real_patient_selector" not in st.session_state and current_real in subjects) else None
    chosen_s = st.selectbox(
        "Select Real CGMacros Participant",
        subjects,
        index=cur_idx,
        format_func=lambda s: subj_labels[s],
        key="page_real_patient_selector",
        on_change=_on_page_real_change,
    )

    row = bio_df[bio_df["subject"] == chosen_s].iloc[0]

    # Participant Header
    st.markdown(
        f"### {row['subject_str']} {badge_html('REAL')} "
        f"<span style='font-size:14px;color:{TEXT_SECONDARY};'>({row['group'].upper()})</span>",
        unsafe_allow_html=True,
    )

    # Patient Biometric Overview Card
    render_patient_body_overview(None, is_real=True, real_row=row)

    # Tabs
    tab_bio, tab_missing, tab_cgm = st.tabs([
        "Real Profile and Labs",
        "Lacking Fields (Not Available)",
        "Real CGM Telemetry",
    ])

    # ── TAB 1: Real Profile & Labs ───────────────────────────────────────────
    with tab_bio:
        st.markdown(f"#### Observed Participant Demographics {badge_html('REAL')}", unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Age", f"{row['age']:.0f} yrs")
        d2.metric("Gender", "Male" if row['gender'] == "M" else "Female")
        d3.metric("BMI", f"{row['bmi']:.1f} kg/m²")
        eth = row.get("ethnicity", "Not specified")
        d4.metric("Ethnicity", str(eth) if pd.notna(eth) else "Unrecorded")

        st.divider()
        st.markdown(f"#### Observed Glycemic and Lipid Laboratory Panel {badge_html('REAL')}", unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        g1.metric("HbA1c (PDL Lab)", f"{row['hba1c']:.1f}%")
        g2.metric("Fasting Glucose", f"{row['fasting_glu']:.0f} mg/dL")
        ins = row.get("insulin")
        g3.metric("Fasting Insulin", f"{ins:.1f} μU/mL" if pd.notna(ins) else "N/A")

        l1, l2, l3, l4 = st.columns(4)
        trig = row.get("triglycerides")
        l1.metric("Triglycerides", f"{trig:.0f} mg/dL" if pd.notna(trig) else "N/A")
        chol = row.get("cholesterol")
        l2.metric("Total Cholesterol", f"{chol:.0f} mg/dL" if pd.notna(chol) else "N/A")
        hdl = row.get("hdl")
        l3.metric("HDL Cholesterol", f"{hdl:.0f} mg/dL" if pd.notna(hdl) else "N/A")
        ldl = row.get("ldl")
        l4.metric("LDL Cholesterol", f"{ldl:.0f} mg/dL" if pd.notna(ldl) else "N/A")

    # ── TAB 2: Missing Fields ────────────────────────────────────────────────
    with tab_missing:
        st.markdown(f"#### Protocol Gaps: Fields Not Collected in CGMacros {badge_html('NOT AVAILABLE')}", unsafe_allow_html=True)
        st.info(
            "Under **Honesty Rule 2**, we never attach simulated values to real study participants. "
            "The following modalities were not collected during the clinical study and are displayed as NOT AVAILABLE."
        )

        missing_data = [
            {"Modality": "Sleep Architecture & Stages", "Status": "NOT AVAILABLE", "Reason": "Polysomnography or actigraphy sleep scoring was not in protocol"},
            {"Modality": "Pedometer / Step Counts", "Status": "NOT AVAILABLE", "Reason": "Only METs and caloric expenditure estimates were recorded"},
            {"Modality": "Heart Rate Variability (HRV)", "Status": "NOT AVAILABLE", "Reason": "Apple Watch recorded instantaneous heart rate, not RR-intervals/RMSSD"},
            {"Modality": "Genomic Markers / Polygenic Score", "Status": "NOT AVAILABLE", "Reason": "No blood genotyping was performed in study"},
            {"Modality": "Medical Diagnoses / Comorbidities", "Status": "NOT AVAILABLE", "Reason": "Participants were classified only by laboratory HbA1c"},
            {"Modality": "Prescription Medications", "Status": "NOT AVAILABLE", "Reason": "Study intake did not log specific medication dosages"},
        ]
        
        for item in missing_data:
            c_name, c_badge, c_desc = st.columns([2, 1, 4])
            c_name.markdown(f"**{item['Modality']}**")
            c_badge.markdown(badge_html("NOT AVAILABLE"), unsafe_allow_html=True)
            c_desc.caption(item["Reason"])
            st.divider()

    # ── TAB 3: Real CGM Telemetry ────────────────────────────────────────────
    with tab_cgm:
        st.markdown(f"#### Real Continuous Glucose Monitoring (Libre) {badge_html('REAL')}", unsafe_allow_html=True)
        cgm_df = load_real_cgm_participant(int(chosen_s))
        
        if cgm_df.empty:
            st.warning("No CGM records found for this participant.")
        else:
            cgm_clean = cgm_df.dropna(subset=["libre"])
            
            m1, m2, m3 = st.columns(3)
            m1.metric("CGM Observations", f"{len(cgm_clean):,} 1-min epochs")
            m2.metric("Mean Glucose", f"{cgm_clean['libre'].mean():.1f} mg/dL")
            m3.metric("Spike Share (>180)", f"{(cgm_clean['libre'] > 180).mean():.1%}")

            fig, ax = plt.subplots(figsize=(11, 3.8))
            ax.plot(cgm_clean["time"], cgm_clean["libre"], color=CHART_LINE_MAIN, lw=1.2, label="Real Libre Glucose")
            ax.axhline(180, color=CHART_THRESHOLD, ls="--", lw=1, label="Spike Threshold (180)")
            ax.axhline(70, color=CHART_HYPO, ls="--", lw=1, label="Hypo Threshold (70)")
            
            real_meals = cgm_df[cgm_df["carbs"] > 0]
            if not real_meals.empty:
                for mt in real_meals["time"]:
                    ax.axvline(mt, color=CHART_MEAL, alpha=0.35, ls=":", lw=1)
                ax.plot([], [], color=CHART_MEAL, label="Real Meal Logged")

            ax.set_ylabel("Glucose (mg/dL)", fontsize=9)
            ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.02), ncol=4, fontsize=8, frameon=False)
            fig.autofmt_xdate()
            st.pyplot(fig)
            plt.close(fig)
