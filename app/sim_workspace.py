"""
Virtual Patient Simulation Workspace.
=====================================

Streamlit Entry Point:
- Left sidebar: navigation (Patient view, Scenario sandbox, Add patient),
  then patient list (preset and custom patients with active selection highlighted).
- Top bar: product name "Digital Twin Workspace", research prototype badge, patient search.
- All fields & charts carry explicit provenance badges (REAL, SIMULATED, USER-ENTERED, NOT AVAILABLE).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st

from app.sim_ui.badges import render_banner, badge_html
from app.sim_ui.theme import (
    apply_theme,
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_TINT,
    BORDER,
    TEXT_MAIN,
    TEXT_SECONDARY,
    BADGE_REAL_BG,
    BADGE_REAL_TEXT,
)
from app.sim_ui.patients_list import render_patients_list, render_add_patient_page
from app.sim_ui.patient_view import render_patient_view
from app.sim_ui.real_patients import render_real_patients
from app.sim_ui.scenario_sandbox import render_scenario_sandbox
from app.sim_ui.assumptions_view import render_assumptions_view
from src.sim.store import list_patients, list_presets, list_custom

st.set_page_config(
    page_title="Digital Twin Workspace",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    # Clinical white & blue theme
    apply_theme()

    # Load patient list for sidebar selection
    all_patients = list_patients(include_presets=True)
    patient_ids = [p["id"] for p in all_patients]
    default_id = st.session_state.get("selected_patient_id", "well_controlled_45")
    if default_id not in patient_ids and patient_ids:
        default_id = patient_ids[0]
        st.session_state["selected_patient_id"] = default_id

    # ─── Sidebar: Header & Product Name ──────────────────────────────────────
    st.sidebar.markdown(
        f"""
        <div style="padding: 4px 0 12px 0; border-bottom: 1px solid {BORDER}; margin-bottom: 12px;">
            <div style="font-size: 18px; font-weight: 700; color: {PRIMARY_DARK}; letter-spacing: -0.01em;">
                Digital Twin Workspace
            </div>
            <div style="font-size: 11px; color: {TEXT_SECONDARY}; font-weight: 500; margin-top: 2px;">
                Research prototype, simulated patients
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ─── Sidebar: Navigation ─────────────────────────────────────────────────
    nav_options = [
        "👥 Patients Directory",
        "🔬 Patient View & Risk",
        "🧪 Scenario Sandbox",
        "➕ Add Patient",
        "📋 Real Reference Patients",
        "⚙️ Simulation Assumptions",
    ]

    def clean_nav_label(opt: str) -> str:
        clean_map = {
            "👥 Patients Directory": "Patients Directory",
            "🔬 Patient View & Risk": "Patient View",
            "🧪 Scenario Sandbox": "Scenario Sandbox",
            "➕ Add Patient": "Add Patient",
            "📋 Real Reference Patients": "Real Reference Patients",
            "⚙️ Simulation Assumptions": "Simulation Assumptions",
        }
        return clean_map.get(opt, opt)

    active_nav = st.session_state.get("active_nav")
    default_nav_idx = 0
    if active_nav:
        for idx, opt in enumerate(nav_options):
            if active_nav.lower() == opt.lower() or active_nav.lower() == clean_nav_label(opt).lower():
                default_nav_idx = idx
                break

    chosen_nav = st.sidebar.radio(
        "Navigation",
        nav_options,
        index=default_nav_idx,
        format_func=clean_nav_label,
        key="main_nav_radio",
        label_visibility="collapsed",
    )
    st.session_state["active_nav"] = clean_nav_label(chosen_nav)

    st.sidebar.divider()

    # ─── Sidebar: Patient List (Preset, Custom, or Real Reference) ───────────
    st.sidebar.markdown(
        f"""
        <div style="font-size: 12px; font-weight: 600; color: {PRIMARY_DARK}; margin-bottom: 6px;">
            Patients
        </div>
        """,
        unsafe_allow_html=True,
    )

    if "Real Reference" in chosen_nav:
        from app.sim_ui.common import load_real_bio_data
        bio_df = load_real_bio_data()
        real_subjects = bio_df["subject"].tolist()
        cur_real = st.session_state.get("selected_real_subject", 3)
        if cur_real not in real_subjects:
            default_t2d = bio_df[bio_df["group"] == "t2d"]["subject"].tolist()
            cur_real = default_t2d[0] if default_t2d else real_subjects[0]
            st.session_state["selected_real_subject"] = cur_real

        def format_real_label(s_num: int) -> str:
            grp = bio_df.loc[bio_df["subject"] == s_num, "group"].iloc[0]
            return f"CGMacros-{s_num:03d} ({grp.upper()})"

        sel_real_idx = real_subjects.index(cur_real) if cur_real in real_subjects else 0
        selected_real = st.sidebar.selectbox(
            "Select Real Participant",
            real_subjects,
            index=sel_real_idx,
            format_func=format_real_label,
            key="sidebar_real_participant_selector",
            label_visibility="collapsed",
        )
        if selected_real != st.session_state.get("selected_real_subject"):
            st.session_state["selected_real_subject"] = selected_real
            st.rerun()

        row_real = bio_df[bio_df["subject"] == cur_real].iloc[0]
        st.sidebar.markdown(
            f"""
            <div style="background-color: {PRIMARY_TINT}; border: 1px solid {PRIMARY};
                        border-radius: 6px; padding: 8px 10px; margin-top: 6px;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-size: 12px; font-weight: 700; color: {PRIMARY_DARK};">CGMacros-{cur_real:03d}</span>
                    <span style='background:{BADGE_REAL_BG}; color:{BADGE_REAL_TEXT}; font-size:10px;
                                font-weight:700; padding:1px 5px; border-radius:3px; border:1px solid {BORDER};'>REAL</span>
                </div>
                <div style="font-size: 11px; color: {TEXT_SECONDARY}; margin-top: 3px;">
                    Age {row_real.get('age', '--')} · HbA1c {row_real.get('hba1c', '--')}% · BMI {row_real.get('bmi', '--')} ({row_real.get('group', '').upper()})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        def format_patient_label(pid: str) -> str:
            for p in all_patients:
                if p["id"] == pid:
                    tag = "PRESET" if p["type"] == "preset" else "CUSTOM"
                    return f"{p['name']} ({tag})"
            return pid

        cur_idx = patient_ids.index(default_id) if default_id in patient_ids else 0
        selected_sidebar_pid = st.sidebar.selectbox(
            "Select Patient",
            patient_ids,
            index=cur_idx,
            format_func=format_patient_label,
            key="sidebar_patient_selector",
            label_visibility="collapsed",
        )
        if selected_sidebar_pid != st.session_state.get("selected_patient_id"):
            st.session_state["selected_patient_id"] = selected_sidebar_pid
            st.rerun()

        # Visual highlight of selected patient info
        cur_p = next((p for p in all_patients if p["id"] == st.session_state.get("selected_patient_id")), None)
        if cur_p:
            is_preset = cur_p["type"] == "preset"
            badge_type = (
                f"<span style='background:{PRIMARY_TINT}; color:{PRIMARY_DARK}; font-size:10px; "
                f"font-weight:700; padding:1px 5px; border-radius:3px;'>PRESET</span>"
                if is_preset
                else f"<span style='background:{BADGE_REAL_BG}; color:{BADGE_REAL_TEXT}; font-size:10px; "
                f"font-weight:700; padding:1px 5px; border-radius:3px;'>CUSTOM</span>"
            )
            st.sidebar.markdown(
                f"""
                <div style="background-color: {PRIMARY_TINT}; border: 1px solid {PRIMARY};
                            border-radius: 6px; padding: 8px 10px; margin-top: 6px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size: 12px; font-weight: 700; color: {PRIMARY_DARK};">{cur_p['name']}</span>
                        {badge_type}
                    </div>
                    <div style="font-size: 11px; color: {TEXT_SECONDARY}; margin-top: 3px;">
                        Age {cur_p.get('age', '--')} · HbA1c {cur_p.get('hba1c', '--')}% · BMI {cur_p.get('bmi', '--')}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.sidebar.divider()

    # ─── Sidebar: Provenance Key ─────────────────────────────────────────────
    st.sidebar.markdown(
        f"""
        <div style="font-size: 12px; font-weight: 600; color: {PRIMARY_DARK}; margin-bottom: 6px;">
            Provenance Key
        </div>
        <div class="prov-key">
            <div>{badge_html('REAL')} Observed study data</div>
            <div>{badge_html('SIMULATED')} Synthetic model trace</div>
            <div>{badge_html('USER-ENTERED')} Clinician typed</div>
            <div>{badge_html('NOT AVAILABLE')} Modality not in study</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        "Happiest Health Digital Twin prototype. Simulated outputs demonstrate "
        "twin pipelines, not clinical evidence."
    )

    # ─── Top Bar: Product Name & Prototype Label ─────────────────────────────
    st.markdown(
        f"""
        <div style="display: flex; align-items: baseline; gap: 12px; padding: 0 0 10px 0;">
            <span style="font-size: 20px; font-weight: 700; color: {PRIMARY_DARK};">
                Digital Twin Workspace
            </span>
            <span style="background: {PRIMARY_TINT}; color: {PRIMARY_DARK}; font-size: 11px;
                         font-weight: 600; padding: 2px 8px; border-radius: 4px; border: 1px solid {BORDER};">
                Research prototype, simulated patients
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Mandatory Research Disclaimer Banner
    render_banner()

    # ─── Main View Routing ───────────────────────────────────────────────────
    if "Patients Directory" in chosen_nav:
        render_patients_list()
    elif "Patient View" in chosen_nav:
        render_patient_view()
    elif "Scenario Sandbox" in chosen_nav:
        render_scenario_sandbox()
    elif "Add Patient" in chosen_nav:
        render_add_patient_page()
    elif "Real Reference" in chosen_nav:
        render_real_patients()
    elif "Assumptions" in chosen_nav:
        render_assumptions_view()


if __name__ == "__main__":
    main()
