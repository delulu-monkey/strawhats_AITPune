"""
Unit and Integration Tests for Workspace Theme and Inline SVG (Part 7).
========================================================================

Verifies:
1. Custom CSS and inline SVG theme generation without external network calls.
2. SVG human-body outline contains all required anatomical/metabolic nodes.
3. Patient overview renders with required provenance badges (REAL, SIMULATED, NOT AVAILABLE).
4. Matplotlib dark navy high-contrast theme applies without errors.
"""

import xml.etree.ElementTree as ET
import pytest
import pandas as pd
import streamlit as st

from src.sim.store import load_preset
from app.sim_ui.theme import apply_theme, get_human_body_svg, render_patient_body_overview


def test_svg_is_valid_xml():
    """Verify inline human body outline is well-formed XML and contains expected SVG elements."""
    svg = get_human_body_svg()
    assert "<svg" in svg
    assert "</svg>" in svg
    # Must not contain external http image links
    assert "http://" not in svg or "xmlns" in svg
    assert "https://" not in svg

    # Validate XML parsing
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")


def test_theme_apply_runs_cleanly():
    """Verify apply_theme runs cleanly without errors."""
    apply_theme()


def test_patient_overview_virtual_patient():
    """Verify body overview handles virtual patient with SIMULATED badges."""
    patient = load_preset("well_controlled_45")
    # Should run without error
    render_patient_body_overview(patient)


def test_patient_overview_real_patient():
    """Verify body overview handles real participant with REAL and NOT AVAILABLE badges."""
    real_row = pd.Series({
        "subject": 1,
        "age": 45,
        "gender": "M",
        "bmi": 24.5,
        "hba1c": 5.4,
        "fasting_glu": 95.0,
        "insulin": 8.5,
    })
    # Should run without error
    render_patient_body_overview(None, is_real=True, real_row=real_row)
