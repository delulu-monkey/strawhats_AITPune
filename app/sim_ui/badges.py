"""
Provenance Badges & Clinical Banners for Sim Workspace.
======================================================

Honesty rules enforcement:
- REAL: observed ground truth from clinical dataset.
- SIMULATED: synthetic or model-generated inputs/traces.
- USER-ENTERED: clinician-entered parameters from forms.
- NOT AVAILABLE: variables completely missing from the clinical dataset.
"""

from __future__ import annotations
import streamlit as st


BADGE_STYLES = {
    "REAL": {
        "bg": "#064e3b",
        "border": "#059669",
        "text": "#6ee7b7",
    },
    "SIMULATED": {
        "bg": "#4c1d95",
        "border": "#7c3aed",
        "text": "#ddd6fe",
    },
    "USER-ENTERED": {
        "bg": "#78350f",
        "border": "#d97706",
        "text": "#fde68a",
    },
    "NOT AVAILABLE": {
        "bg": "#1f2937",
        "border": "#4b5563",
        "text": "#9ca3af",
    },
}


def badge_html(tag: str) -> str:
    """Return inline HTML pill badge for a given provenance status."""
    norm = tag.upper().strip()
    style = BADGE_STYLES.get(norm, BADGE_STYLES["SIMULATED"])
    return (
        f'<span style="'
        f'display: inline-block; '
        f'background-color: {style["bg"]}; '
        f'border: 1px solid {style["border"]}; '
        f'color: {style["text"]}; '
        f'font-size: 0.72rem; '
        f'font-weight: 700; '
        f'letter-spacing: 0.04em; '
        f'padding: 1px 7px; '
        f'border-radius: 4px; '
        f'margin-left: 6px; '
        f'vertical-align: middle;'
        f'">{norm}</span>'
    )


def render_banner() -> None:
    """Mandatory clinical disclaimer banner."""
    st.markdown(
        """
        <div style="
            background: linear-gradient(90deg, #1e1b4b 0%, #311042 100%);
            border-left: 5px solid #a855f7;
            padding: 10px 16px;
            border-radius: 6px;
            margin-bottom: 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        ">
            <div>
                <span style="font-weight: 700; color: #f3e8ff; font-size: 0.95rem;">
                    ⚠️ Research prototype. For simulated or anonymised patients only. Not a medical device.
                </span>
                <span style="display: block; color: #c084fc; font-size: 0.8rem; margin-top: 2px;">
                    Simulated physiological outputs demonstrate mathematical twin pipelines, not certified clinical accuracy.
                </span>
            </div>
            <div>
                <span style="
                    background: #581c87;
                    border: 1px solid #c084fc;
                    color: #f5d0fe;
                    font-size: 0.75rem;
                    font-weight: 700;
                    padding: 4px 10px;
                    border-radius: 9999px;
                ">SIMULATION WORKSPACE</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def label_with_badge(label: str, provenance_tag: str) -> str:
    """Return markdown string with label and provenance HTML badge."""
    return f"{label} {badge_html(provenance_tag)}"
