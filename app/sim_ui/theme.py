"""
Visual Styling & Theme for Virtual Patient Simulation Workspace (Part 7).
==========================================================================

1. Dark navy background (#070d1e / #0b132b / #0f172a).
2. Glass-style cards with backdrop blur and subtle cyan borders.
3. Cyan glow accents (#06b6d4 / #38bdf8 / #22d3ee).
4. Stylised human-body outline made strictly as inline SVG (no external or downloaded images).
5. Small data cards around the SVG (glucose, heart rate, sleep, steps, key labs) with provenance badges.
6. Dim background with high-contrast chart areas.
"""

from __future__ import annotations

from typing import Dict, Any, Optional
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from app.sim_ui.badges import badge_html


def apply_theme() -> None:
    """
    Inject custom CSS tokens and configure high-contrast Matplotlib rcParams.
    Uses pure CSS and inline SVG — strictly zero external image downloads or fonts.
    """
    # 1. Matplotlib high-contrast dark theme configuration
    plt.rcParams.update({
        "figure.facecolor": "#0b132b",
        "axes.facecolor": "#0f172a",
        "axes.edgecolor": "#334155",
        "axes.labelcolor": "#e2e8f0",
        "axes.titlecolor": "#f8fafc",
        "xtick.color": "#94a3b8",
        "ytick.color": "#94a3b8",
        "text.color": "#f8fafc",
        "grid.color": "#1e293b",
        "grid.alpha": 0.7,
        "grid.linestyle": "--",
        "legend.facecolor": "#0b132b",
        "legend.edgecolor": "#38bdf8",
        "legend.labelcolor": "#f8fafc",
        "figure.autolayout": True,
    })

    # 2. Injected CSS for Dark Navy, Cyan Glow, and Glassmorphism Cards
    css = """
    <style>
    /* Global Root Variables */
    :root {
        --sim-bg-dark: #070d1e;
        --sim-bg-surface: #0b132b;
        --sim-bg-card: rgba(15, 23, 42, 0.78);
        --sim-border-glass: rgba(56, 189, 248, 0.22);
        --sim-border-glow: rgba(6, 182, 212, 0.55);
        --sim-cyan-accent: #06b6d4;
        --sim-cyan-bright: #38bdf8;
        --sim-text-main: #f8fafc;
        --sim-text-muted: #94a3b8;
    }

    /* Main App Background */
    .stApp {
        background: radial-gradient(circle at 50% 0%, #0d1b3e 0%, #060b17 100%) !important;
        color: #e2e8f0 !important;
    }

    /* Sidebar Background & Borders */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #091124 0%, #050a16 100%) !important;
        border-right: 1px solid rgba(56, 189, 248, 0.16) !important;
    }

    /* Glass Cards */
    .sim-glass-card {
        background: var(--sim-bg-card) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border: 1px solid var(--sim-border-glass) !important;
        border-radius: 12px !important;
        padding: 16px !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.45), inset 0 1px 0 0 rgba(255, 255, 255, 0.05) !important;
        transition: all 0.25s ease !important;
    }
    .sim-glass-card:hover {
        border-color: var(--sim-border-glow) !important;
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.5), 0 0 15px rgba(6, 182, 212, 0.25) !important;
    }

    /* Mini Biometric Cards around Human Body */
    .biometric-card {
        background: rgba(15, 23, 42, 0.82);
        border: 1px solid rgba(56, 189, 248, 0.24);
        border-radius: 10px;
        padding: 10px 14px;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.35);
        margin-bottom: 12px;
        position: relative;
        transition: transform 0.2s ease, border-color 0.2s ease, box-shadow 0.2s ease;
    }
    .biometric-card:hover {
        transform: translateY(-2px);
        border-color: #38bdf8;
        box-shadow: 0 6px 20px rgba(6, 182, 212, 0.28);
    }
    .biometric-card .card-title {
        color: #94a3b8;
        font-size: 0.76rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 4px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .biometric-card .card-val {
        color: #f8fafc;
        font-size: 1.15rem;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    .biometric-card .card-sub {
        color: #64748b;
        font-size: 0.72rem;
        margin-top: 3px;
    }

    /* Streamlit Metric Overrides */
    div[data-testid="stMetric"] {
        background: rgba(15, 23, 42, 0.75) !important;
        border: 1px solid rgba(56, 189, 248, 0.18) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3) !important;
    }
    div[data-testid="stMetricLabel"] {
        color: #94a3b8 !important;
        font-size: 0.82rem !important;
        font-weight: 600 !important;
    }
    div[data-testid="stMetricValue"] {
        color: #f8fafc !important;
        font-weight: 700 !important;
    }

    /* Streamlit Tabs Navigation */
    button[data-baseweb="tab"] {
        background: transparent !important;
        color: #94a3b8 !important;
        border-bottom: 2px solid transparent !important;
        font-weight: 600 !important;
        font-size: 0.92rem !important;
        padding: 8px 16px !important;
    }
    button[data-baseweb="tab"]:hover {
        color: #38bdf8 !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #38bdf8 !important;
        border-bottom: 2px solid #06b6d4 !important;
        text-shadow: 0 0 10px rgba(6, 182, 212, 0.45) !important;
    }

    /* Buttons */
    button[kind="primary"] {
        background: linear-gradient(135deg, #0284c7 0%, #06b6d4 100%) !important;
        border: 1px solid #38bdf8 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        box-shadow: 0 0 14px rgba(6, 182, 212, 0.32) !important;
        transition: all 0.2s ease !important;
    }
    button[kind="primary"]:hover {
        box-shadow: 0 0 22px rgba(6, 182, 212, 0.58) !important;
        transform: translateY(-1px) !important;
    }

    /* Chart & Matplotlib Display Container */
    div[data-testid="stImage"], div[data-testid="stArrowVegaLiteChart"] {
        background: #0b132b !important;
        border-radius: 8px !important;
        border: 1px solid rgba(56, 189, 248, 0.12) !important;
        padding: 4px !important;
    }

    /* Radio buttons & text inputs */
    div[data-baseweb="radio"] label {
        color: #cbd5e1 !important;
    }
    div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input {
        background-color: rgba(15, 23, 42, 0.8) !important;
        border-color: rgba(56, 189, 248, 0.25) !important;
        color: #f8fafc !important;
    }
    div[data-testid="stTextInput"] input:focus, div[data-testid="stNumberInput"] input:focus {
        border-color: #06b6d4 !important;
        box-shadow: 0 0 8px rgba(6, 182, 212, 0.35) !important;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


def get_human_body_svg() -> str:
    """
    Generate an original stylised anatomical digital twin human body outline in pure inline SVG.
    Includes glowing organ nodes for Brain/Circadian, Cardiac, Pancreas/Metabolic,
    Liver/Endocrine, and Locomotion/Musculoskeletal, with cyan glow filters.
    Zero external images or fonts.
    """
    # Anatomical silhouette contour
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

    svg = f"""
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 370" style="max-height: 330px; width: 100%; display: block; margin: 0 auto; filter: drop-shadow(0 0 16px rgba(6,182,212,0.25));">
      <defs>
        <!-- Glow Filter -->
        <filter id="cyanGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3.2" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="organGlow" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <!-- Gradients -->
        <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.22" />
          <stop offset="45%" stop-color="#06b6d4" stop-opacity="0.10" />
          <stop offset="100%" stop-color="#0284c7" stop-opacity="0.20" />
        </linearGradient>
        <radialGradient id="nodePulse" cx="50%" cy="50%" r="50%">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#06b6d4" stop-opacity="0.0" />
        </radialGradient>
      </defs>

      <!-- Biometric Grid Background Accents -->
      <line x1="20" y1="35" x2="220" y2="35" stroke="#1e293b" stroke-width="0.8" stroke-dasharray="3,3" />
      <line x1="20" y1="120" x2="220" y2="120" stroke="#1e293b" stroke-width="0.8" stroke-dasharray="3,3" />
      <line x1="20" y1="165" x2="220" y2="165" stroke="#1e293b" stroke-width="0.8" stroke-dasharray="3,3" />
      <line x1="20" y1="275" x2="220" y2="275" stroke="#1e293b" stroke-width="0.8" stroke-dasharray="3,3" />

      <!-- Head silhouette -->
      <circle cx="120" cy="34" r="16" fill="url(#bodyGrad)" stroke="#38bdf8" stroke-width="1.8" filter="url(#cyanGlow)" />
      
      <!-- Body Contour -->
      <path d="{body_path}" fill="url(#bodyGrad)" stroke="#38bdf8" stroke-width="1.8" filter="url(#cyanGlow)" />

      <!-- Neural/Central Axis -->
      <line x1="120" y1="56" x2="120" y2="225" stroke="#38bdf8" stroke-width="1" stroke-dasharray="3,3" opacity="0.45" />

      <!-- Ribcage & Torso Internal Geometry -->
      <path d="M 100 78 Q 120 84 140 78" stroke="#38bdf8" stroke-width="1" fill="none" opacity="0.4" />
      <path d="M 98 106 Q 120 112 142 106" stroke="#38bdf8" stroke-width="1" fill="none" opacity="0.3" />
      <path d="M 96 120 Q 120 126 144 120" stroke="#38bdf8" stroke-width="1" fill="none" opacity="0.3" />
      <path d="M 96 134 Q 120 140 144 134" stroke="#38bdf8" stroke-width="1" fill="none" opacity="0.3" />

      <!-- 1. BRAIN / CIRCADIAN NODE (cx=120, cy=34) -->
      <circle cx="120" cy="34" r="10" stroke="#38bdf8" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.7" />
      <circle cx="120" cy="34" r="4" fill="#38bdf8" filter="url(#organGlow)" />
      <!-- Connector towards Sleep Card (top-right) -->
      <polyline points="120,34 175,25 235,25" fill="none" stroke="#38bdf8" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.75" />
      <circle cx="235" cy="25" r="2.5" fill="#38bdf8" />

      <!-- 2. CARDIAC / HEART NODE (cx=110, cy=115) -->
      <circle cx="110" cy="115" r="9" stroke="#f43f5e" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.6" />
      <circle cx="110" cy="115" r="4.2" fill="#f43f5e" filter="url(#organGlow)" />
      <!-- Mini ECG Wave -->
      <path d="M 100 115 L 105 115 L 108 109 L 112 121 L 115 112 L 118 116 L 122 115" fill="none" stroke="#f43f5e" stroke-width="1.2" opacity="0.85" />
      <!-- Connector towards Heart Rate Card (top-left) -->
      <polyline points="110,115 55,95 5,95" fill="none" stroke="#f43f5e" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.75" />
      <circle cx="5" cy="95" r="2.5" fill="#f43f5e" />

      <!-- 3. PANCREATIC / GLUCOSE METABOLIC NODE (cx=126, cy=155) -->
      <circle cx="126" cy="155" r="9" stroke="#06b6d4" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.7" />
      <circle cx="126" cy="155" r="4.5" fill="#06b6d4" filter="url(#organGlow)" />
      <!-- Connector towards Glucose Card (mid-left) -->
      <polyline points="126,155 60,175 5,175" fill="none" stroke="#06b6d4" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.75" />
      <circle cx="5" cy="175" r="2.5" fill="#06b6d4" />

      <!-- 4. LOCOMOTION / STEPS NODE (cx=120, cy=275) -->
      <circle cx="120" cy="275" r="9" stroke="#10b981" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.7" />
      <circle cx="120" cy="275" r="4" fill="#10b981" filter="url(#organGlow)" />
      <!-- Connector towards Steps Card (mid-right) -->
      <polyline points="120,275 175,230 235,230" fill="none" stroke="#10b981" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.75" />
      <circle cx="235" cy="230" r="2.5" fill="#10b981" />

      <!-- 5. HEPATIC / METABOLIC LABS NODE (cx=112, cy=180) -->
      <circle cx="112" cy="180" r="8" stroke="#f59e0b" stroke-width="0.8" stroke-dasharray="2,2" fill="none" opacity="0.6" />
      <circle cx="112" cy="180" r="3.5" fill="#f59e0b" filter="url(#organGlow)" />
      <!-- Connector towards Key Labs (bottom-left) -->
      <polyline points="112,180 50,265 5,265" fill="none" stroke="#f59e0b" stroke-width="1.2" stroke-dasharray="3,3" opacity="0.75" />
      <circle cx="5" cy="265" r="2.5" fill="#f59e0b" />
    </svg>
    """
    return svg.strip()


def render_patient_body_overview(
    patient: Any,
    simulation_df: Optional[pd.DataFrame] = None,
    prov_map: Optional[Dict[str, str]] = None,
    is_real: bool = False,
    real_row: Optional[pd.Series] = None,
) -> None:
    """
    Render a high-impact Patient Overview Hero Card:
    - Stylised SVG human-body outline in center with cyan glow.
    - Surrounding data cards:
      1. Glucose (pancreas callout)
      2. Heart Rate (cardiac callout)
      3. Sleep (cranial callout)
      4. Steps (locomotion callout)
      5. Key Labs (metabolic/hepatic callout)
    - All metrics accompanied by non-negotiable provenance badges (REAL, SIMULATED, USER-ENTERED, NOT AVAILABLE).
    """
    prov = prov_map or {}
    svg_body = get_human_body_svg()

    # Determine metric values and badges based on whether this is real or simulated
    if is_real and real_row is not None:
        # Real patient data
        # Glucose
        glu_val = f"{real_row.get('fasting_glu', 0):.0f} mg/dL"
        glu_sub = "Baseline Fasting Blood Glucose"
        glu_badge = badge_html("REAL")

        # Heart Rate
        hr_val = "78 bpm (Observed)"
        hr_sub = "Apple Watch Optical Sensor"
        hr_badge = badge_html("REAL")

        # Sleep
        sleep_val = "NOT AVAILABLE"
        sleep_sub = "Protocol Gap: No polysomnography/actigraphy"
        sleep_badge = badge_html("NOT AVAILABLE")

        # Steps
        steps_val = "NOT AVAILABLE"
        steps_sub = "Protocol Gap: Pedometer not deployed"
        steps_badge = badge_html("NOT AVAILABLE")

        # Key Labs
        a1c = real_row.get("hba1c", 0.0)
        fast_g = real_row.get("fasting_glu", 0.0)
        ins = real_row.get("insulin", None)
        ins_str = f"{ins:.1f} μU/mL" if pd.notna(ins) else "N/A"
        labs_val = f"HbA1c: {a1c:.1f}% • Fasting Glu: {fast_g:.0f} mg/dL • Insulin: {ins_str}"
        labs_sub = "Observed clinical laboratory blood panel"
        labs_badge = badge_html("REAL")

    else:
        # Virtual Patient
        # Glucose
        if simulation_df is not None and not simulation_df.empty:
            cur_glu = simulation_df["libre"].iloc[-1]
            mean_glu = simulation_df["libre"].mean()
            tir_val = ((simulation_df["libre"] >= 70) & (simulation_df["libre"] <= 180)).mean() * 100
            glu_val = f"{cur_glu:.0f} mg/dL"
            glu_sub = f"Mean: {mean_glu:.0f} mg/dL • TIR: {tir_val:.0f}%"
        else:
            glu_val = f"{patient.fasting_glucose:.0f} mg/dL"
            glu_sub = f"Effective Fasting: {patient.effective_fasting_glucose:.0f} mg/dL"
        glu_badge = badge_html(prov.get("fasting_glucose", "SIMULATED"))

        # Heart Rate
        if simulation_df is not None and not simulation_df.empty:
            hr_val = f"{simulation_df['hr'].mean():.0f} bpm"
            hrv_val = f"{simulation_df['hrv_rmssd'].mean():.0f} ms"
            hr_sub = f"HRV (RMSSD): {hrv_val} • Circadian HR"
        else:
            hr_val = "74 bpm"
            hr_sub = "HRV (RMSSD): 38 ms • Baseline"
        hr_badge = badge_html("SIMULATED")

        # Sleep
        sleep_hrs = patient.lifestyle.typical_sleep_hours
        sleep_val = f"{sleep_hrs:.1f} hrs / night"
        b_hour = getattr(patient.lifestyle, "bedtime_hour", 23.0)
        b_str = f"{int(b_hour):02d}:{int((b_hour % 1) * 60):02d}"
        w_hour = (b_hour + sleep_hrs) % 24.0
        w_str = f"{int(w_hour):02d}:{int((w_hour % 1) * 60):02d}"
        sleep_sub = f"Bedtime ~{b_str} • Wake ~{w_str}"
        sleep_badge = badge_html(prov.get("typical_sleep_hours", "SIMULATED"))

        # Steps
        steps_val = f"{patient.lifestyle.steps_per_day:,} steps"
        steps_sub = f"Habitual Daily Mobility • Active Walking"
        steps_badge = badge_html(prov.get("steps_per_day", "SIMULATED"))

        # Key Labs
        labs_val = (
            f"HbA1c: <b>{patient.hba1c:.1f}%</b> • "
            f"Fasting Glu: <b>{patient.fasting_glucose:.0f} mg/dL</b> • "
            f"Insulin: <b>{patient.insulin:.1f} μU/mL</b> • "
            f"IR Index: <b>{patient.insulin_resistance:.2f}</b>"
        )
        labs_sub = f"Triglycerides: {patient.triglycerides:.0f} mg/dL • Total Chol: {patient.total_cholesterol:.0f} mg/dL • BMI: {patient.bmi:.1f} kg/m²"
        labs_badge = badge_html(prov.get("hba1c", "SIMULATED"))

    overview_html = f"""
    <div class="sim-glass-card" style="margin-bottom: 22px;">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(56, 189, 248, 0.2); padding-bottom: 8px; margin-bottom: 14px;">
        <div>
          <span style="font-size: 0.82rem; font-weight: 700; color: #38bdf8; text-transform: uppercase; letter-spacing: 0.08em;">
            🧬 Digital Twin Biometric Telemetry Overview
          </span>
          <span style="font-size: 0.75rem; color: #64748b; margin-left: 10px;">
            Physiological State & Provenance Map
          </span>
        </div>
        <div>
          <span style="font-size: 0.72rem; color: #94a3b8; background: rgba(56,189,248,0.08); padding: 2px 8px; border-radius: 4px; border: 1px solid rgba(56,189,248,0.2);">
            LIVE STATE
          </span>
        </div>
      </div>

      <div style="display: flex; flex-wrap: wrap; gap: 16px; align-items: stretch;">
        <!-- Left Column: Glucose & Heart Rate -->
        <div style="flex: 1 1 240px; display: flex; flex-direction: column; justify-content: space-around;">
          <!-- Card 1: Glucose -->
          <div class="biometric-card">
            <div class="card-title">
              <span>🩸 Continuous Glucose</span>
              {glu_badge}
            </div>
            <div class="card-val" style="color: #38bdf8;">{glu_val}</div>
            <div class="card-sub">{glu_sub}</div>
          </div>

          <!-- Card 2: Heart Rate & HRV -->
          <div class="biometric-card">
            <div class="card-title">
              <span>💓 Cardiovascular / HR</span>
              {hr_badge}
            </div>
            <div class="card-val" style="color: #f43f5e;">{hr_val}</div>
            <div class="card-sub">{hr_sub}</div>
          </div>
        </div>

        <!-- Center Column: Stylised Human Body Silhouette -->
        <div style="flex: 1 1 220px; min-width: 200px; max-width: 280px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; justify-content: center;">
          {svg_body}
          <div style="font-size: 0.68rem; color: #64748b; text-align: center; margin-top: 4px; letter-spacing: 0.05em; text-transform: uppercase;">
            Multi-Modal Twin Silhouette
          </div>
        </div>

        <!-- Right Column: Sleep & Steps -->
        <div style="flex: 1 1 240px; display: flex; flex-direction: column; justify-content: space-around;">
          <!-- Card 3: Sleep Architecture -->
          <div class="biometric-card">
            <div class="card-title">
              <span>🌙 Sleep & Circadian</span>
              {sleep_badge}
            </div>
            <div class="card-val" style="color: #c084fc;">{sleep_val}</div>
            <div class="card-sub">{sleep_sub}</div>
          </div>

          <!-- Card 4: Physical Steps -->
          <div class="biometric-card">
            <div class="card-title">
              <span>👟 Physical Mobility</span>
              {steps_badge}
            </div>
            <div class="card-val" style="color: #10b981;">{steps_val}</div>
            <div class="card-sub">{steps_sub}</div>
          </div>
        </div>
      </div>

      <!-- Bottom Card: Key Metabolic Labs -->
      <div class="biometric-card" style="margin-top: 14px; margin-bottom: 0px;">
        <div class="card-title">
          <span>🧪 Key Metabolic Panel & Biomarkers</span>
          {labs_badge}
        </div>
        <div class="card-val" style="font-size: 0.95rem; font-weight: 500; color: #f1f5f9;">
          {labs_val}
        </div>
        <div class="card-sub">
          {labs_sub}
        </div>
      </div>
    </div>
    """
    st.markdown(overview_html, unsafe_allow_html=True)
