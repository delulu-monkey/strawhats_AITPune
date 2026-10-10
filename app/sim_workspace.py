"""
Virtual Patient Simulation Workspace.
=====================================

Streamlit Entry Point:
- Sidebar navigation: Patients Directory, Patient View & Risk, Real Reference Patients.
- Mandatory research prototype banner.
- All fields & charts carry explicit provenance badges (REAL, SIMULATED, USER-ENTERED, NOT AVAILABLE).
"""

from __future__ import annotations

import streamlit as st

from app.sim_ui.badges import render_banner
from app.sim_ui.patients_list import render_patients_list
from app.sim_ui.patient_view import render_patient_view
from app.sim_ui.real_patients import render_real_patients

st.set_page_config(
    page_title="Virtual Patient Simulation Workspace",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main() -> None:
    # Mandatory Research Disclaimer Banner at top of page
    render_banner()

    # Sidebar Navigation
    st.sidebar.title("🩺 Sim Workspace")
    st.sidebar.caption("Virtual Patient Twin & Scenario Explorer")

    nav_options = [
        "👥 Patients Directory",
        "🔬 Patient View & Risk",
        "📋 Real Reference Patients",
    ]

    # Map session state navigation if set from inspect buttons
    active_nav = st.session_state.get("active_nav")
    default_idx = 0
    if active_nav == "Patient View":
        default_idx = 1
    elif active_nav == "Real Patients":
        default_idx = 2

    chosen_nav = st.sidebar.radio(
        "Navigation",
        nav_options,
        index=default_idx,
        key="main_nav_radio",
    )

    # Reset active_nav state
    if "active_nav" in st.session_state:
        st.session_state["active_nav"] = None

    st.sidebar.divider()
    st.sidebar.markdown(
        """
        **Honesty Badges:**
        - <span style='background:#064e3b;color:#6ee7b7;padding:1px 6px;border-radius:3px;font-size:0.75rem;'>REAL</span> Observed study data
        - <span style='background:#4c1d95;color:#ddd6fe;padding:1px 6px;border-radius:3px;font-size:0.75rem;'>SIMULATED</span> Synthetic model data
        - <span style='background:#78350f;color:#fde68a;padding:1px 6px;border-radius:3px;font-size:0.75rem;'>USER-ENTERED</span> Clinician typed
        - <span style='background:#1f2937;color:#9ca3af;padding:1px 6px;border-radius:3px;font-size:0.75rem;'>NOT AVAILABLE</span> Modality not in study
        """,
        unsafe_allow_html=True,
    )
    st.sidebar.caption(
        "Built for Happiest Health Digital Twin challenge. "
        "Simulated outputs are pipeline demonstrations, not clinical evidence."
    )

    # Route to selected page
    if chosen_nav == "👥 Patients Directory":
        render_patients_list()
    elif chosen_nav == "🔬 Patient View & Risk":
        render_patient_view()
    elif chosen_nav == "📋 Real Reference Patients":
        render_real_patients()


if __name__ == "__main__":
    main()
