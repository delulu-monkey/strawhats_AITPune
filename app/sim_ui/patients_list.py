"""
Patients Directory, Creator Form, and Editor UI.
================================================

Handles:
1. Listing preset and custom virtual patients with SIMULATED badges.
2. Search and filter across patients.
3. 'Add patient' form covering all VirtualPatient fields (demographics, labs,
   diagnoses, medications, genetic markers, lifestyle, seed).
4. Editing and deleting custom patients only (presets strictly protected).
"""

from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
import streamlit as st

from src.sim.profile import VirtualPatient
from src.sim.assumptions import T2D_VARIANTS, UNLOGGED_SNACK_PROB_PER_EPOCH
from src.sim.store import (
    list_patients,
    list_presets,
    list_custom,
    load_patient,
    save_patient,
    update_patient,
    delete_patient,
)
from app.sim_ui.badges import badge_html, label_with_badge
from app.sim_ui.theme import (
    PRIMARY, PRIMARY_DARK, PRIMARY_TINT, BORDER,
    TEXT_MAIN, TEXT_SECONDARY, STATUS_HIGH,
    BADGE_REAL_BG, BADGE_REAL_BORDER, BADGE_REAL_TEXT,
)


def render_patients_list() -> None:
    """Main entry point for Patients tab / directory."""
    st.markdown("## Virtual Patients Directory")
    st.caption(
        "Manage synthetic personas. Presets are read-only clinical benchmarks; "
        "custom patients can be created, edited, and deleted."
    )

    all_pts = list_patients(include_presets=True)
    presets_count = len(list_presets())
    customs_count = len(list_custom())

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Total Patients", len(all_pts))
    col_m2.metric("Preset Personas", presets_count)
    col_m3.metric("Custom Patients", customs_count)
    col_m4.markdown(
        f"<div style='padding-top: 14px;'>{badge_html('SIMULATED')} Synthetic cohort</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    # Search and Filter
    search_col, filter_col = st.columns([3, 1])
    search_query = search_col.text_input("Search patients by name, diagnosis, or description", "")
    filter_type = filter_col.selectbox("Filter Type", ["All", "Presets Only", "Custom Only"])

    # Add Patient Expander
    with st.expander("Add New Virtual Patient", expanded=st.session_state.get("show_add_form", False)):
        render_add_patient_form()

    # Edit Patient Expander (if triggered)
    edit_id = st.session_state.get("editing_patient_id")
    if edit_id:
        with st.expander(f"Edit Custom Patient: {edit_id}", expanded=True):
            render_edit_patient_form(edit_id)

    # Filter patient list
    filtered = all_pts
    if filter_type == "Presets Only":
        filtered = [p for p in filtered if p["type"] == "preset"]
    elif filter_type == "Custom Only":
        filtered = [p for p in filtered if p["type"] == "custom"]

    if search_query.strip():
        q = search_query.strip().lower()
        filtered = [
            p for p in filtered
            if q in p["name"].lower() or q in p.get("description", "").lower() or q in p["id"].lower()
        ]

    st.markdown(f"### Found {len(filtered)} Patient{'s' if len(filtered) != 1 else ''}")

    if not filtered:
        st.info("No matching virtual patients found. Create one above!")
        return

    # Render Patient Cards
    for pt in filtered:
        with st.container():
            c1, c2, c3, c4 = st.columns([3, 2, 2, 3])

            with c1:
                is_preset = pt["type"] == "preset"
                type_badge = (
                    f"<span style='background:{PRIMARY_TINT};color:{PRIMARY_DARK};"
                    f"font-size:11px;padding:1px 6px;border-radius:4px;border:1px solid {BORDER};'>PRESET</span>"
                    if is_preset
                    else f"<span style='background:{BADGE_REAL_BG};color:{BADGE_REAL_TEXT};"
                    f"font-size:11px;padding:1px 6px;border-radius:4px;border:1px solid {BADGE_REAL_BORDER};'>CUSTOM</span>"
                )
                st.markdown(
                    f"**{pt['name']}** {badge_html('SIMULATED')} {type_badge}",
                    unsafe_allow_html=True,
                )
                if pt.get("description"):
                    st.caption(pt["description"])

            with c2:
                age_str = f"Age {pt['age']}" if pt.get("age") else "Age --"
                sex_str = pt.get("sex", "--")
                bmi_str = f"BMI {pt['bmi']:.1f}" if pt.get("bmi") else "BMI --"
                st.write(f"{age_str} · {sex_str} · {bmi_str}")

            with c3:
                a1c_str = f"HbA1c {pt['hba1c']:.1f}%" if pt.get("hba1c") else "HbA1c --"
                seed_str = f"Seed: {pt.get('seed', '--')}"
                st.write(f"**{a1c_str}**")
                st.caption(seed_str)

            with c4:
                btn_cols = st.columns([2, 1, 1])
                if btn_cols[0].button("Inspect", key=f"inspect_{pt['id']}"):
                    st.session_state["selected_patient_id"] = pt["id"]
                    st.session_state["active_nav"] = "Patient view"
                    st.rerun()

                if not is_preset:
                    if btn_cols[1].button("Edit", key=f"edit_{pt['id']}", help="Edit patient"):
                        st.session_state["editing_patient_id"] = pt["id"]
                        st.rerun()

                    if btn_cols[2].button("Delete", key=f"del_{pt['id']}", help="Delete patient"):
                        try:
                            delete_patient(pt["id"])
                            st.success(f"Deleted {pt['name']}")
                            if st.session_state.get("selected_patient_id") == pt["id"]:
                                st.session_state["selected_patient_id"] = "well_controlled_45"
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                else:
                    btn_cols[1].markdown(
                        f"<span style='color:{TEXT_SECONDARY};font-size:12px;'>Protected</span>",
                        unsafe_allow_html=True,
                    )

            st.divider()


def render_add_patient_page() -> None:
    """Standalone page for 'Add patient' navigation."""
    st.markdown("## Add New Virtual Patient")
    st.caption("Create a synthetic patient twin with complete clinical, physiological, and behavioral parameters.")
    render_add_patient_form()


def render_add_patient_form() -> None:
    """Render comprehensive form with all VirtualPatient parameters."""
    with st.form("add_patient_form", clear_on_submit=False):
        # Section 1: Demographics
        st.markdown(f"#### 1. Demographics & Identifiers {badge_html('USER-ENTERED')}", unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        name = c1.text_input("Full Name *", "Custom Patient 1")
        age = c2.number_input("Age (years) *", min_value=1, max_value=120, value=48)
        sex = c3.selectbox("Sex *", ["M", "F"])
        seed = c4.number_input("Simulation Seed *", min_value=0, max_value=999999, value=42)

        c_h, c_w, c_bmi = st.columns([1, 1, 1])
        height_cm = c_h.number_input("Height (cm) *", min_value=50.0, max_value=250.0, value=172.0, step=0.5)
        weight_kg = c_w.number_input("Weight (kg) *", min_value=20.0, max_value=300.0, value=78.0, step=0.5)
        calc_bmi = round(weight_kg / ((height_cm / 100.0) ** 2), 1)
        c_bmi.metric("Calculated BMI", f"{calc_bmi} kg/m²")

        description = st.text_input("Clinical Profile Summary", "Custom profile created in simulation workspace.")

        st.markdown(f"#### 2. Glycemic and Lipid Laboratory Panel {badge_html('USER-ENTERED')}", unsafe_allow_html=True)
        l1, l2, l3, l4 = st.columns(4)
        hba1c = l1.number_input("HbA1c (%) *", min_value=3.0, max_value=20.0, value=6.2, step=0.1)
        fasting_glu = l2.number_input("Fasting Glucose (mg/dL) *", min_value=30.0, max_value=500.0, value=112.0, step=1.0)
        insulin = l3.number_input("Fasting Insulin (μU/mL)", min_value=0.0, max_value=300.0, value=12.0, step=0.5)
        triglycerides = l4.number_input("Triglycerides (mg/dL)", min_value=0.0, max_value=2000.0, value=150.0, step=1.0)

        l5, l6, l7 = st.columns(3)
        cholesterol = l5.number_input("Total Cholesterol (mg/dL)", min_value=50.0, max_value=500.0, value=195.0, step=1.0)
        hdl = l6.number_input("HDL (mg/dL)", min_value=10.0, max_value=150.0, value=50.0, step=1.0)
        ldl = l7.number_input("LDL (mg/dL)", min_value=10.0, max_value=400.0, value=115.0, step=1.0)

        st.markdown(f"#### 3. Clinical Diagnoses & Pharmacotherapy {badge_html('USER-ENTERED')}", unsafe_allow_html=True)
        cd1, cd2 = st.columns(2)
        diag_str = cd1.text_input("Diagnoses (comma-separated)", "Prediabetes, Mild Hypertension")
        med_str = cd2.text_input("Medications (comma-separated)", "Metformin 500mg")

        st.markdown(f"#### 4. Behavioral & Lifestyle Schedule {badge_html('USER-ENTERED')}", unsafe_allow_html=True)
        ls1, ls2, ls3 = st.columns(3)
        sleep_hours = ls1.number_input("Typical Sleep Duration (hours)", min_value=3.0, max_value=12.0, value=7.2, step=0.1)
        sleep_var = ls2.number_input("Sleep Variability SD (hours)", min_value=0.0, max_value=4.0, value=0.5, step=0.1)
        bedtime = ls3.number_input("Bedtime (24h clock, e.g. 23.0 for 11 PM)", min_value=0.0, max_value=23.9, value=22.5, step=0.5)

        ls4, ls5, ls6 = st.columns(3)
        steps_per_day = ls4.number_input("Steps Per Day (steps)", min_value=0, max_value=50000, value=7500, step=500)
        resting_hr = ls5.number_input("Resting Heart Rate (bpm)", min_value=30.0, max_value=120.0, value=68.0, step=1.0)
        snack_prob = ls6.number_input("Unlogged Snack Prob (per 5 min)", min_value=0.0, max_value=0.1, value=UNLOGGED_SNACK_PROB_PER_EPOCH, step=0.005, format="%.3f")

        st.markdown(f"#### 5. Genetic Markers & Polygenic Risk {badge_html('USER-ENTERED')}", unsafe_allow_html=True)
        g1, g2 = st.columns([1, 2])
        genetic_risk = g1.slider("Composite Genetic Risk Score (0–100)", min_value=0.0, max_value=100.0, value=50.0, step=1.0)

        st.caption("Risk Allele Counts (0 = non-carrier, 1 = heterozygous, 2 = homozygous):")
        var_cols = st.columns(len(T2D_VARIANTS))
        variant_alleles = {}
        for idx, v in enumerate(T2D_VARIANTS):
            variant_alleles[v] = var_cols[idx].selectbox(f"{v}", [0, 1, 2], index=0, key=f"add_var_{v}")

        st.divider()

        # Action Buttons: primary blue Save button and secondary Cancel button
        btn_c1, btn_c2 = st.columns([2, 1])
        submitted = btn_c1.form_submit_button("Save Virtual Patient", type="primary", use_container_width=True)
        cancelled = btn_c2.form_submit_button("Cancel", use_container_width=True)

        if cancelled:
            st.session_state["show_add_form"] = False
            st.session_state["active_nav"] = "Patient view"
            st.rerun()

        if submitted:
            diagnoses = [d.strip() for d in diag_str.split(",") if d.strip()]
            medications = [m.strip() for m in med_str.split(",") if m.strip()]

            # Build patient dictionary
            p_dict = {
                "name": name.strip(),
                "age": int(age),
                "sex": sex,
                "height_cm": float(height_cm),
                "weight_kg": float(weight_kg),
                "hba1c": float(hba1c),
                "fasting_glucose": float(fasting_glu),
                "insulin": float(insulin),
                "triglycerides": float(triglycerides),
                "total_cholesterol": float(cholesterol),
                "hdl": float(hdl),
                "ldl": float(ldl),
                "diagnoses": diagnoses,
                "medications": medications,
                "genetic_markers": {
                    "variant_alleles": variant_alleles,
                    "genetic_risk_score": float(genetic_risk),
                },
                "lifestyle": {
                    "typical_sleep_hours": float(sleep_hours),
                    "sleep_variability_hours": float(sleep_var),
                    "bedtime_hour": float(bedtime),
                    "steps_per_day": int(steps_per_day),
                    "resting_heart_rate": float(resting_hr),
                    "unlogged_snack_prob": float(snack_prob),
                },
                "seed": int(seed),
                "description": description.strip(),
                "source": "simulated",
            }

            try:
                vp = VirtualPatient.from_dict(p_dict)
                user_fields = [
                    "name", "age", "sex", "height_cm", "weight_kg", "hba1c",
                    "fasting_glucose", "insulin", "triglycerides", "total_cholesterol",
                    "hdl", "ldl", "diagnoses", "medications", "typical_sleep_hours", "steps_per_day"
                ]
                saved_path = save_patient(
                    vp,
                    description=description,
                    user_entered_fields=user_fields,
                    overwrite=False,
                )
                st.success(f"Successfully saved custom patient '{vp.name}' to {saved_path.name}!")
                st.session_state["selected_patient_id"] = vp.patient_id.lower()
                st.session_state["show_add_form"] = False
                st.session_state["active_nav"] = "Patient view"
                st.rerun()
            except Exception as e:
                st.error(f"Validation Error: {e}")


def render_edit_patient_form(patient_id: str) -> None:
    """Render edit form for a custom patient."""
    try:
        p = load_patient(patient_id)
    except Exception as e:
        st.error(f"Cannot load patient {patient_id}: {e}")
        return

    st.info(f"Editing custom patient: **{p.name}** (Seed: {p.seed})")

    with st.form(f"edit_patient_form_{patient_id}"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("Full Name *", p.name)
        age = c2.number_input("Age (years) *", min_value=1, max_value=120, value=int(p.age))
        sex = c3.selectbox("Sex *", ["M", "F"], index=0 if p.sex == "M" else 1)

        c_h, c_w = st.columns(2)
        height_cm = c_h.number_input("Height (cm) *", min_value=50.0, max_value=250.0, value=float(p.height_cm))
        weight_kg = c_w.number_input("Weight (kg) *", min_value=20.0, max_value=300.0, value=float(p.weight_kg))

        description = st.text_input("Clinical Description", p.description)

        l1, l2, l3 = st.columns(3)
        hba1c = l1.number_input("HbA1c (%) *", min_value=3.0, max_value=20.0, value=float(p.hba1c), step=0.1)
        fasting_glu = l2.number_input("Fasting Glucose (mg/dL) *", min_value=30.0, max_value=500.0, value=float(p.fasting_glucose), step=1.0)
        insulin = l3.number_input("Insulin (μU/mL)", min_value=0.0, max_value=300.0, value=float(p.insulin), step=0.5)

        cd1, cd2 = st.columns(2)
        diag_str = cd1.text_input("Diagnoses", ", ".join(p.diagnoses))
        med_str = cd2.text_input("Medications", ", ".join(p.medications))

        s1, s2 = st.columns(2)
        sleep_hours = s1.number_input("Sleep Duration (hours)", min_value=3.0, max_value=12.0, value=float(p.lifestyle.typical_sleep_hours), step=0.1)
        steps_per_day = s2.number_input("Steps per Day (steps)", min_value=0, max_value=50000, value=int(p.lifestyle.steps_per_day), step=500)

        b_sub, b_can = st.columns(2)
        save_btn = b_sub.form_submit_button("Update Patient", type="primary", use_container_width=True)
        cancel_btn = b_can.form_submit_button("Cancel", use_container_width=True)

        if cancel_btn:
            st.session_state["editing_patient_id"] = None
            st.rerun()

        if save_btn:
            updates = {
                "name": name.strip(),
                "age": int(age),
                "sex": sex,
                "height_cm": float(height_cm),
                "weight_kg": float(weight_kg),
                "hba1c": float(hba1c),
                "fasting_glucose": float(fasting_glu),
                "insulin": float(insulin),
                "diagnoses": [d.strip() for d in diag_str.split(",") if d.strip()],
                "medications": [m.strip() for m in med_str.split(",") if m.strip()],
                "lifestyle": {
                    "typical_sleep_hours": float(sleep_hours),
                    "steps_per_day": int(steps_per_day),
                },
            }
            try:
                update_patient(patient_id, updates, description=description)
                st.success(f"Updated {name}!")
                st.session_state["editing_patient_id"] = None
                st.rerun()
            except Exception as e:
                st.error(f"Error updating patient: {e}")
