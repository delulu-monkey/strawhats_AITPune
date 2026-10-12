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

from app.sim_ui.theme import (
    BADGE_REAL_BG, BADGE_REAL_BORDER, BADGE_REAL_TEXT,
    BADGE_SIM_BG, BADGE_SIM_BORDER, BADGE_SIM_TEXT,
    BADGE_USER_BG, BADGE_USER_BORDER, BADGE_USER_TEXT,
    BADGE_NA_BG, BADGE_NA_BORDER, BADGE_NA_TEXT,
)

# Badge styles mapped from theme tokens
BADGE_STYLES = {
    "REAL": {
        "bg": BADGE_REAL_BG,
        "border": BADGE_REAL_BORDER,
        "text": BADGE_REAL_TEXT,
    },
    "SIMULATED": {
        "bg": BADGE_SIM_BG,
        "border": BADGE_SIM_BORDER,
        "text": BADGE_SIM_TEXT,
    },
    "USER-ENTERED": {
        "bg": BADGE_USER_BG,
        "border": BADGE_USER_BORDER,
        "text": BADGE_USER_TEXT,
    },
    "NOT AVAILABLE": {
        "bg": BADGE_NA_BG,
        "border": BADGE_NA_BORDER,
        "text": BADGE_NA_TEXT,
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
        f'font-size: 11px; '
        f'font-weight: 700; '
        f'letter-spacing: 0.03em; '
        f'padding: 1px 8px; '
        f'border-radius: 4px; '
        f'margin-left: 6px; '
        f'vertical-align: middle; '
        f'text-transform: uppercase;'
        f'">{norm}</span>'
    )


def render_banner() -> None:
    """Mandatory clinical disclaimer banner: single-line neutral strip."""
    st.markdown(
        """
        <div class="research-banner">
            <span class="banner-text">
                Research prototype. For simulated or anonymised patients only. Not a medical device.
            </span>
            <span class="banner-pill">RESEARCH PROTOTYPE</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def label_with_badge(label: str, provenance_tag: str) -> str:
    """Return markdown string with label and provenance HTML badge."""
    return f"{label} {badge_html(provenance_tag)}"
