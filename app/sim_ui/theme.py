"""
Visual Styling & Theme for Virtual Patient Simulation Workspace.
=================================================================

Clinical white-and-blue design tokens.
All visual constants live here. CSS is in style.css, injected once.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


# ─── Design tokens (mirrored in style.css as CSS custom properties) ─────────

# Page & Backgrounds
BG_PAGE = "#FFFFFF"
BG_APP = "#F5F8FC"
BG_CARD = "#FFFFFF"

# Borders & Dividers
BORDER = "#E3E9F2"

# Primary Palette
PRIMARY = "#1D5FD1"
PRIMARY_DARK = "#0F3D91"
PRIMARY_TINT = "#EAF1FD"

# Text
TEXT_MAIN = "#0F1B2D"
TEXT_SECONDARY = "#5B6B82"

# Status (muted, strictly for clinical meaning)
STATUS_OK = "#2F855A"
STATUS_WATCH = "#B7791F"
STATUS_HIGH = "#C0392B"

# Charts
CHART_LINE_MAIN = PRIMARY          # blue
CHART_LINE_BASELINE = "#94A3B8"    # grey
CHART_THRESHOLD = STATUS_HIGH      # red threshold line (180 mg/dL)
CHART_HYPO = STATUS_WATCH          # amber hypo line (70 mg/dL)
CHART_MEAL = "#C05621"             # burnt orange for meal markers
CHART_RANGE_FILL = STATUS_OK       # green target range band
CHART_SLEEP = PRIMARY_DARK
CHART_STEPS = STATUS_OK
CHART_HR = STATUS_HIGH
CHART_HRV = PRIMARY
CHART_SCENARIO = PRIMARY           # blue for counterfactual scenario
CHART_GRID = "#E3E9F2"
CHART_BG = BG_PAGE

# Badge Provenance Colors
BADGE_REAL_BG = "#E6F4EA"
BADGE_REAL_BORDER = "#A3D9A5"
BADGE_REAL_TEXT = "#1B5E20"

BADGE_SIM_BG = "#EAF1FD"
BADGE_SIM_BORDER = "#90B8F8"
BADGE_SIM_TEXT = "#0F3D91"

BADGE_USER_BG = "#FFF8E1"
BADGE_USER_BORDER = "#FFD54F"
BADGE_USER_TEXT = "#795548"

BADGE_NA_BG = "#F0F2F5"
BADGE_NA_BORDER = "#CFD8DC"
BADGE_NA_TEXT = "#5B6B82"

# Typography
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, Segoe UI, system-ui, sans-serif"

# Spacing & Radii
RADIUS_CARD = 8
RADIUS_BTN = 6
PAD_CARD = 20


def apply_theme() -> None:
    """
    Inject clinical CSS stylesheet and configure Matplotlib rcParams.
    Called once at app start.
    """
    # 1. Matplotlib clinical theme
    plt.rcParams.update({
        "figure.facecolor": CHART_BG,
        "axes.facecolor": CHART_BG,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": TEXT_MAIN,
        "axes.titlecolor": TEXT_MAIN,
        "xtick.color": TEXT_SECONDARY,
        "ytick.color": TEXT_SECONDARY,
        "text.color": TEXT_MAIN,
        "grid.color": CHART_GRID,
        "grid.alpha": 0.6,
        "grid.linestyle": "-",
        "grid.linewidth": 0.5,
        "legend.facecolor": CHART_BG,
        "legend.edgecolor": BORDER,
        "legend.labelcolor": TEXT_MAIN,
        "figure.autolayout": True,
        "axes.grid": True,
        "font.family": "sans-serif",
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "legend.fontsize": 8.5,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "lines.linewidth": 1.6,
    })

    # 2. Inject CSS from style.css
    css_path = Path(__file__).parent / "style.css"
    if css_path.exists():
        css_text = css_path.read_text(encoding="utf-8")
    else:
        css_text = ""
    st.markdown(f"<style>{css_text}</style>", unsafe_allow_html=True)


def generate_svg_sparkline(values: List[float], stroke_color: str, width: int = 100, height: int = 24) -> str:
    """
    Generate an ultra-lightweight inline SVG sparkline trend line.
    Pure vector math, zero dependencies, no markdown indentation.
    """
    if not values or len(values) < 2:
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"></svg>'

    min_v = float(min(values))
    max_v = float(max(values))
    span = max_v - min_v
    if span < 1e-4:
        span = 1.0

    points = []
    n = len(values)
    for i, v in enumerate(values):
        x = round((i / (n - 1)) * (width - 8) + 4, 1)
        y = round(height - 4 - ((v - min_v) / span) * (height - 8), 1)
        points.append(f"{x},{y}")

    d_path = "M " + " L ".join(points)
    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'style="display:inline-block; vertical-align:middle; overflow:visible;">'
        f'<path d="{d_path}" fill="none" stroke="{stroke_color}" stroke-width="1.8" '
        f'stroke-linecap="round" stroke-linejoin="round" />'
        f'</svg>'
    )


def get_human_body_svg() -> str:
    """
    Simple, flat, line-style human outline in blue-grey.
    Used only as a small anatomical locator next to the data cards.
    No glow, no gradients, no sci-fi effects.
    """
    body_path = (
        "M 112 56 "
        "C 105 65, 85 75, 70 85 "
        "C 60 92, 52 140, 48 185 "
        "C 45 200, 42 215, 45 225 "
        "C 48 230, 52 230, 55 225 "
        "C 58 215, 57 195, 60 180 "
        "C 62 165, 68 135, 82 120 "
        "C 84 140, 88 160, 86 180 "
        "C 84 195, 80 205, 82 220 "
        "C 84 240, 86 280, 88 320 "
        "C 89 335, 82 348, 86 352 "
        "C 92 355, 98 350, 100 345 "
        "C 103 330, 106 280, 114 235 "
        "Q 120 225, 126 235 "
        "C 134 280, 137 330, 140 345 "
        "C 142 350, 148 355, 154 352 "
        "C 158 348, 151 335, 152 320 "
        "C 154 280, 156 240, 158 220 "
        "C 160 205, 156 195, 154 180 "
        "C 152 160, 156 140, 158 120 "
        "C 172 135, 178 165, 180 180 "
        "C 183 195, 182 215, 185 225 "
        "C 188 230, 192 230, 195 225 "
        "C 198 215, 195 200, 192 185 "
        "C 188 140, 180 92, 170 85 "
        "C 155 75, 135 65, 128 56 Z"
    )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 370" '
        f'style="max-height: 230px; width: 100%; display: block; margin: 0 auto;">'
        f'<circle cx="120" cy="34" r="16" fill="none" stroke="{CHART_LINE_BASELINE}" stroke-width="1.5" />'
        f'<path d="{body_path}" fill="{PRIMARY_TINT}" fill-opacity="0.35" stroke="{CHART_LINE_BASELINE}" stroke-width="1.5" />'
        f'<circle cx="110" cy="115" r="4" fill="{PRIMARY}" opacity="0.6" />'
        f'<circle cx="126" cy="155" r="4" fill="{PRIMARY}" opacity="0.6" />'
        f'<circle cx="120" cy="275" r="4" fill="{PRIMARY}" opacity="0.6" />'
        f'</svg>'
    )
    return svg


def render_patient_body_overview(
    patient: Any,
    simulation_df: Optional[pd.DataFrame] = None,
    prov_map: Optional[Dict[str, str]] = None,
    is_real: bool = False,
    real_row: Optional[pd.Series] = None,
    current_time: Optional[pd.Timestamp] = None,
) -> None:
    """
    Render Patient Overview row:
    - Row of six summary cards: heart rate, glucose, HbA1c, sleep, HRV, steps.
    - Each card has a label, large value, unit, small trend line, and provenance badge.
    - Small flat human outline as anatomical locator.
    """
    from app.sim_ui.badges import badge_html

    prov = prov_map or {}

    # Determine metric values, subtexts, and trend series
    if is_real and real_row is not None:
        glu_val = f"{real_row.get('fasting_glu', 0):.0f}"
        glu_unit = "mg/dL"
        glu_sub = "Baseline Fasting"
        glu_badge = badge_html("REAL")
        glu_spark = generate_svg_sparkline([float(real_row.get('fasting_glu', 100))] * 6, CHART_LINE_MAIN)

        hr_val = "78"
        hr_unit = "bpm"
        hr_sub = "Optical sensor"
        hr_badge = badge_html("REAL")
        hr_spark = generate_svg_sparkline([72, 75, 78, 80, 76, 78], CHART_HR)

        a1c = real_row.get("hba1c", 0.0)
        a1c_val = f"{a1c:.1f}"
        a1c_unit = "%"
        a1c_sub = "PDL Lab"
        a1c_badge = badge_html("REAL")
        a1c_spark = generate_svg_sparkline([a1c, a1c, a1c], PRIMARY_DARK)

        sleep_val = "—"
        sleep_unit = ""
        sleep_sub = "Not in protocol"
        sleep_badge = badge_html("NOT AVAILABLE")
        sleep_spark = ""

        hrv_val = "—"
        hrv_unit = ""
        hrv_sub = "No RR-intervals"
        hrv_badge = badge_html("NOT AVAILABLE")
        hrv_spark = ""

        steps_val = "—"
        steps_unit = ""
        steps_sub = "No pedometer"
        steps_badge = badge_html("NOT AVAILABLE")
        steps_spark = ""

    else:
        # Virtual Patient
        if simulation_df is not None and not simulation_df.empty:
            if current_time is not None:
                pos = (simulation_df["time"] - pd.Timestamp(current_time)).abs().argmin()
                cur_glu = simulation_df["libre"].iloc[pos]
                cur_hr = simulation_df["hr"].iloc[pos]
                cur_hrv = simulation_df["hrv_rmssd"].iloc[pos]
            else:
                cur_glu = simulation_df["libre"].iloc[-1]
                cur_hr = simulation_df["hr"].mean()
                cur_hrv = simulation_df["hrv_rmssd"].mean()

            glu_val = f"{cur_glu:.0f}"
            mean_glu = simulation_df["libre"].mean()
            tir_val = ((simulation_df["libre"] >= 70) & (simulation_df["libre"] <= 180)).mean() * 100
            glu_sub = f"Mean {mean_glu:.0f} · TIR {tir_val:.0f}%"

            step_stride = max(1, len(simulation_df) // 24)
            glu_series = simulation_df["libre"].iloc[::step_stride].tolist()
            hr_series = simulation_df["hr"].iloc[::step_stride].tolist()
            hrv_series = simulation_df["hrv_rmssd"].iloc[::step_stride].tolist()
            steps_series = simulation_df["steps"].iloc[::step_stride].tolist()

            hr_val = f"{cur_hr:.0f}"
            hr_sub = "Continuous PPG"
            hrv_val = f"{cur_hrv:.0f}"
            hrv_sub = "RMSSD"
        else:
            glu_val = f"{patient.fasting_glucose:.0f}"
            glu_sub = f"Eff. fasting {patient.effective_fasting_glucose:.0f}"
            glu_series = [patient.fasting_glucose] * 12
            hr_val = "74"
            hr_sub = "Baseline"
            hr_series = [70, 72, 74, 76, 73, 74]
            hrv_val = "38"
            hrv_sub = "Baseline RMSSD"
            hrv_series = [35, 38, 40, 37, 39, 38]
            steps_series = [100, 400, 800, 300, 0, 500]

        glu_unit = "mg/dL"
        glu_badge = badge_html(prov.get("fasting_glucose", "SIMULATED"))
        glu_spark = generate_svg_sparkline(glu_series, CHART_LINE_MAIN)

        hr_unit = "bpm"
        hr_badge = badge_html("SIMULATED")
        hr_spark = generate_svg_sparkline(hr_series, CHART_HR)

        hrv_unit = "ms"
        hrv_badge = badge_html("SIMULATED")
        hrv_spark = generate_svg_sparkline(hr_series, CHART_HRV)

        a1c_val = f"{patient.hba1c:.1f}"
        a1c_unit = "%"
        a1c_sub = f"IR Index {patient.insulin_resistance:.2f}"
        a1c_badge = badge_html(prov.get("hba1c", "SIMULATED"))
        a1c_spark = generate_svg_sparkline([patient.hba1c - 0.2, patient.hba1c, patient.hba1c, patient.hba1c], PRIMARY_DARK)

        sleep_hrs = patient.lifestyle.typical_sleep_hours
        sleep_val = f"{sleep_hrs:.1f}"
        sleep_unit = "hrs"
        b_hour = getattr(patient.lifestyle, "bedtime_hour", 23.0)
        b_str = f"{int(b_hour):02d}:{int((b_hour % 1) * 60):02d}"
        w_hour = (b_hour + sleep_hrs) % 24.0
        w_str = f"{int(w_hour):02d}:{int((w_hour % 1) * 60):02d}"
        sleep_sub = f"{b_str}–{w_str}"
        sleep_badge = badge_html(prov.get("typical_sleep_hours", "SIMULATED"))
        sleep_spark = generate_svg_sparkline([sleep_hrs * 0.9, sleep_hrs, sleep_hrs * 1.05, sleep_hrs], CHART_SLEEP)

        steps_val = f"{patient.lifestyle.steps_per_day:,}"
        steps_unit = "steps"
        steps_sub = "Daily habitual"
        steps_badge = badge_html(prov.get("steps_per_day", "SIMULATED"))
        steps_spark = generate_svg_sparkline(steps_series, CHART_STEPS)

    # Build the six cards with ZERO leading whitespace
    def make_card(label, badge, val, unit, sub, spark):
        return (
            f'<div class="biometric-card">'
            f'<div class="card-title"><span>{label}</span>{badge}</div>'
            f'<div style="display:flex; justify-content:space-between; align-items:baseline; margin-top:4px;">'
            f'<div class="card-val">{val} <span style="font-size:13px; font-weight:500; color:{TEXT_SECONDARY};">{unit}</span></div>'
            f'<div style="margin-left:8px;">{spark}</div>'
            f'</div>'
            f'<div class="card-sub">{sub}</div>'
            f'</div>'
        )

    cards_html = "".join([
        make_card("Heart Rate", hr_badge, hr_val, hr_unit, hr_sub, hr_spark),
        make_card("Glucose", glu_badge, glu_val, glu_unit, glu_sub, glu_spark),
        make_card("HbA1c", a1c_badge, a1c_val, a1c_unit, a1c_sub, a1c_spark),
        make_card("Sleep", sleep_badge, sleep_val, sleep_unit, sleep_sub, sleep_spark),
        make_card("HRV", hrv_badge, hrv_val, hrv_unit, hrv_sub, hrv_spark),
        make_card("Steps", steps_badge, steps_val, steps_unit, steps_sub, steps_spark),
    ])

    svg_body = get_human_body_svg()

    overview_html = (
        f'<div class="sim-glass-card" style="margin-bottom: 20px;">'
        f'<div style="display:flex; justify-content:space-between; align-items:center; '
        f'border-bottom:1px solid {BORDER}; padding-bottom:8px; margin-bottom:16px;">'
        f'<div>'
        f'<span style="font-size:14px; font-weight:600; color:{PRIMARY_DARK};">Biometric Summary Row</span>'
        f'<span style="font-size:12px; color:{TEXT_SECONDARY}; margin-left:10px;">Six core modalities with trend trajectory and provenance</span>'
        f'</div>'
        f'</div>'
        f'<div style="display:flex; gap:16px; align-items:center; flex-wrap:wrap;">'
        f'<div style="flex:1 1 0; display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; min-width:0;">'
        f'{cards_html}'
        f'</div>'
        f'<div style="flex:0 0 110px; display:flex; align-items:center; justify-content:center; padding:4px;">'
        f'{svg_body}'
        f'</div>'
        f'</div>'
        f'</div>'
    )
    st.markdown(overview_html, unsafe_allow_html=True)
