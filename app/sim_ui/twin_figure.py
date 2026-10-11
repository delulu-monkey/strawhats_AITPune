"""
Original Patient & Digital Twin Anatomical Illustration
======================================================
Generated programmatically as responsive inline SVG.
Renders two anatomically proportioned human silhouettes side by side:
- Left: "Patient" (solid light blue-grey silhouette in #DCE6F5)
- Right: "Digital twin" (thin #1D5FD1 outline, #EAF1FD fill, internal cross-section contour scan lines,
  joint/organ node dots, and fine circuit telemetry traces).
Functional markers on the twin figure indicate the 6 core metrics, dynamically colored
by data provenance (REAL = green, SIMULATED/USER-ENTERED = blue, NOT AVAILABLE = hollow grey).
"""

from __future__ import annotations

from typing import Dict, Optional
from app.sim_ui.theme import (
    PRIMARY,
    PRIMARY_DARK,
    PRIMARY_TINT,
    TEXT_MAIN,
    TEXT_SECONDARY,
    BORDER,
    BADGE_REAL_TEXT,
)

# Patient silhouette solid color
PATIENT_SILHOUETTE = "#DCE6F5"
# Grey for unavailable data
UNAVAILABLE_GREY = "#9AA0A6"


def _make_body_path(cx: float) -> str:
    """
    Generate smooth, anatomically proportioned Bezier path for a standing human silhouette
    front view, centered horizontally at cx.
    """
    head = (
        f"M {cx} 44 "
        f"C {cx + 8.5} 44 {cx + 14} 51 {cx + 14} 60.5 "
        f"C {cx + 14} 70.5 {cx + 8.5} 77.5 {cx} 77.5 "
        f"C {cx - 8.5} 77.5 {cx - 14} 70.5 {cx - 14} 60.5 "
        f"C {cx - 14} 51 {cx - 8.5} 44 {cx} 44 Z "
    )
    body = (
        f"M {cx - 6} 79.5 "
        f"C {cx - 14} 83.5 {cx - 22} 89 {cx - 27} 97 "
        f"C {cx - 31} 103 {cx - 32} 116 {cx - 32} 130 "
        f"C {cx - 32} 150 {cx - 31} 175 {cx - 29} 205 "
        f"C {cx - 28} 218 {cx - 27} 227 {cx - 25} 231 "
        f"C {cx - 23} 232 {cx - 21} 231 {cx - 21} 227 "
        f"C {cx - 22} 219 {cx - 23} 204 {cx - 24} 190 "
        f"C {cx - 25} 165 {cx - 25} 145 {cx - 20} 124 "
        f"C {cx - 18} 136 {cx - 16} 148 {cx - 15} 158 "
        f"C {cx - 14} 168 {cx - 17} 178 {cx - 19} 188 "
        f"C {cx - 20} 202 {cx - 19} 220 {cx - 17} 242 "
        f"C {cx - 16} 255 {cx - 15} 272 {cx - 13} 290 "
        f"C {cx - 12} 300 {cx - 13} 305 {cx - 13} 308 "
        f"C {cx - 13} 310 {cx - 7} 310 {cx - 5} 310 "
        f"C {cx - 4} 306 {cx - 5} 298 {cx - 5} 288 "
        f"C {cx - 5} 265 {cx - 4} 248 {cx - 4} 235 "
        f"C {cx - 4} 218 {cx - 3} 202 {cx} 192 "
        f"C {cx + 3} 202 {cx + 4} 218 {cx + 4} 235 "
        f"C {cx + 4} 248 {cx + 5} 265 {cx + 5} 288 "
        f"C {cx + 5} 298 {cx + 4} 306 {cx + 5} 310 "
        f"C {cx + 7} 310 {cx + 13} 310 {cx + 13} 308 "
        f"C {cx + 13} 305 {cx + 12} 300 {cx + 13} 290 "
        f"C {cx + 15} 272 {cx + 16} 255 {cx + 17} 242 "
        f"C {cx + 19} 220 {cx + 20} 202 {cx + 19} 188 "
        f"C {cx + 17} 178 {cx + 14} 168 {cx + 15} 158 "
        f"C {cx + 16} 148 {cx + 18} 136 {cx + 20} 124 "
        f"C {cx + 25} 145 {cx + 25} 165 {cx + 24} 190 "
        f"C {cx + 23} 204 {cx + 22} 219 {cx + 21} 227 "
        f"C {cx + 21} 231 {cx + 23} 232 {cx + 25} 231 "
        f"C {cx + 27} 227 {cx + 28} 218 {cx + 29} 205 "
        f"C {cx + 31} 175 {cx + 32} 150 {cx + 32} 130 "
        f"C {cx + 32} 116 {cx + 31} 103 {cx + 27} 97 "
        f"C {cx + 22} 89 {cx + 14} 83 {cx + 6} 79.5 Z"
    )
    return head + body


def _get_marker_style(provenance: Optional[str]) -> Dict[str, str]:
    """
    Format SVG marker circle attributes based on data provenance.
    - REAL / OBSERVED: filled green
    - SIMULATED / USER-ENTERED: filled blue
    - NOT AVAILABLE: hollow grey with dashed stroke
    """
    prov_str = (provenance or "SIMULATED").upper()
    if prov_str in ("REAL", "OBSERVED"):
        return {
            "fill": BADGE_REAL_TEXT,
            "stroke": BADGE_REAL_TEXT,
            "dash": "none",
            "text_color": TEXT_MAIN,
            "line_color": BADGE_REAL_TEXT,
        }
    elif prov_str in ("SIMULATED", "USER-ENTERED"):
        return {
            "fill": PRIMARY,
            "stroke": PRIMARY,
            "dash": "none",
            "text_color": TEXT_MAIN,
            "line_color": PRIMARY,
        }
    else:  # NOT AVAILABLE
        return {
            "fill": "#FFFFFF",
            "stroke": UNAVAILABLE_GREY,
            "dash": "2.5 2",
            "text_color": TEXT_SECONDARY,
            "line_color": UNAVAILABLE_GREY,
        }


def get_patient_and_twin_svg(prov_map: Optional[Dict[str, str]] = None) -> str:
    """
    Generate original Patient and Digital Twin illustration as inline SVG.

    Parameters
    ----------
    prov_map : dict, optional
        Mapping of metric names to provenance strings:
        - "sleep": provenance for Sleep marker
        - "hr": provenance for Heart rate & HRV marker
        - "glucose": provenance for Glucose marker
        - "hba1c": provenance for HbA1c marker
        - "steps": provenance for Steps marker
    """
    prov = prov_map or {}

    # Coordinate anchors
    patient_cx = 64.0
    twin_cx = 186.0

    patient_path = _make_body_path(patient_cx)
    twin_path = _make_body_path(twin_cx)

    # Styles for functional markers
    s_sleep = _get_marker_style(prov.get("sleep", prov.get("typical_sleep_hours", "SIMULATED")))
    s_hr = _get_marker_style(prov.get("hr", prov.get("heart_rate", "SIMULATED")))
    s_glu = _get_marker_style(prov.get("glucose", prov.get("fasting_glucose", "SIMULATED")))
    s_a1c = _get_marker_style(prov.get("hba1c", "SIMULATED"))
    s_steps = _get_marker_style(prov.get("steps", prov.get("steps_per_day", "SIMULATED")))

    # Contour cross-section scan lines inside twin silhouette (11% opacity)
    scan_lines = []
    for y in range(48, 308, 12):
        scan_lines.append(
            f'<line x1="150" y1="{y}" x2="222" y2="{y}" stroke="{PRIMARY}" stroke-width="0.8" stroke-opacity="0.11" />'
        )
    scan_lines_svg = "\n        ".join(scan_lines)

    # Circuit traces flowing from twin toward right edge (25% opacity)
    circuit_traces = f"""
        <!-- Circuit-style traces -->
        <g stroke="{PRIMARY}" stroke-width="0.8" stroke-opacity="0.25" fill="none">
            <path d="M 212 98 L 228 98 L 235 90 L 248 90" />
            <circle cx="248" cy="90" r="1.5" fill="{PRIMARY}" fill-opacity="0.35" stroke="none" />

            <path d="M 210 136 L 224 136 L 232 144 L 250 144" />
            <circle cx="250" cy="144" r="1.5" fill="{PRIMARY}" fill-opacity="0.35" stroke="none" />

            <path d="M 205 184 L 220 184 L 228 194 L 246 194" />
            <circle cx="246" cy="194" r="1.5" fill="{PRIMARY}" fill-opacity="0.35" stroke="none" />

            <path d="M 202 228 L 216 228 L 222 220 L 242 220" />
            <circle cx="242" cy="220" r="1.5" fill="{PRIMARY}" fill-opacity="0.35" stroke="none" />
        </g>
    """

    # Anatomical node dots at key joints and organ locations on twin
    node_dots = f"""
        <!-- Anatomical node dots -->
        <g fill="{PRIMARY}" opacity="0.65">
            <!-- Shoulders -->
            <circle cx="164" cy="98" r="2" />
            <circle cx="208" cy="98" r="2" />
            <!-- Elbows -->
            <circle cx="160" cy="154" r="1.8" />
            <circle cx="212" cy="154" r="1.8" />
            <!-- Wrists -->
            <circle cx="161" cy="204" r="1.5" />
            <circle cx="211" cy="204" r="1.5" />
            <!-- Hips -->
            <circle cx="174" cy="186" r="2" />
            <circle cx="198" cy="186" r="2" />
            <!-- Knees -->
            <circle cx="174" cy="244" r="2" />
            <circle cx="198" cy="244" r="2" />
            <!-- Ankles -->
            <circle cx="176" cy="294" r="1.8" />
            <circle cx="196" cy="294" r="1.8" />
        </g>
    """

    # Functional Marker helper
    def render_marker(mx, my, lx2, ly2, tx, ty, label, style, anchor="start"):
        return f"""
        <g>
            <line x1="{mx}" y1="{my}" x2="{lx2}" y2="{ly2}" stroke="{style['line_color']}" stroke-width="0.8" stroke-dasharray="2 1.5" stroke-opacity="0.75" />
            <circle cx="{mx}" cy="{my}" r="4" fill="{style['fill']}" stroke="{style['stroke']}" stroke-width="1.5" stroke-dasharray="{style['dash']}" />
            <text x="{tx}" y="{ty}" text-anchor="{anchor}" font-family="Inter, system-ui, sans-serif" font-size="10.5" font-weight="600" fill="{style['text_color']}">{label}</text>
        </g>
        """

    # Marker 1: Head = Sleep (leader right to x=232)
    m_sleep = render_marker(186, 58, 230, 58, 234, 61.5, "Sleep", s_sleep)
    # Marker 2: Chest = Heart rate and HRV (leader right to x=232)
    m_hr = render_marker(183, 116, 230, 116, 234, 119.5, "HR / HRV", s_hr)
    # Marker 3: Abdomen = Glucose (leader right to x=232)
    m_glu = render_marker(186, 156, 230, 156, 234, 159.5, "Glucose", s_glu)
    # Marker 4: Near abdomen = HbA1c (lab) (leader left into inter-figure space or right)
    m_a1c = render_marker(178, 172, 142, 172, 138, 175.5, "HbA1c (lab)", s_a1c, anchor="end")
    # Marker 5: Legs = Steps (leader right to x=232)
    m_steps = render_marker(186, 264, 230, 264, 234, 267.5, "Steps", s_steps)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 420" width="100%" height="auto" style="max-width: 300px; display: block; margin: 0 auto; user-select: none;">
    <defs>
        <!-- Soft light-blue glow filter behind twin (8-10% opacity) -->
        <filter id="twin-glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="6" />
        </filter>
        <!-- Clip path to constrain scan lines cleanly inside twin body -->
        <clipPath id="twin-clip-body">
            <path d="{twin_path}" />
        </clipPath>
        <!-- Directional interaction arrows -->
        <marker id="arrow-left" viewBox="0 0 6 6" refX="1" refY="3" markerWidth="4" markerHeight="4" orient="auto-start-reverse">
            <path d="M 6 0 L 0 3 L 6 6 z" fill="{PRIMARY}" />
        </marker>
        <marker id="arrow-right" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="4" markerHeight="4" orient="auto">
            <path d="M 0 0 L 6 3 L 0 6 z" fill="{PRIMARY}" />
        </marker>
    </defs>

    <!-- Twin soft glow -->
    <path d="{twin_path}" fill="{PRIMARY}" fill-opacity="0.09" filter="url(#twin-glow)" />

    <!-- Left figure: Patient silhouette in plain solid light blue-grey -->
    <path d="{patient_path}" fill="{PATIENT_SILHOUETTE}" stroke="none" />

    <!-- Right figure: Digital twin with thin blue outline and very light blue fill -->
    <path d="{twin_path}" fill="{PRIMARY_TINT}" stroke="{PRIMARY}" stroke-width="1.5" />

    <!-- Horizontal contour/scan lines inside twin body -->
    <g clip-path="url(#twin-clip-body)">
        {scan_lines_svg}
    </g>

    {circuit_traces}
    {node_dots}

    <!-- Interaction bridge between Patient and Digital Twin -->
    <line x1="96" y1="126" x2="152" y2="126" stroke="{PRIMARY}" stroke-width="1" stroke-dasharray="2 3" marker-start="url(#arrow-left)" marker-end="url(#arrow-right)" />
    <text x="124" y="119" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="8.5" font-weight="600" fill="{TEXT_SECONDARY}">Simulated twin</text>

    <!-- Figure labels under silhouettes -->
    <text x="64" y="332" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{TEXT_SECONDARY}">Patient</text>
    <text x="186" y="332" text-anchor="middle" font-family="Inter, system-ui, sans-serif" font-size="12" font-weight="600" fill="{PRIMARY}">Digital twin</text>

    <!-- Functional metric markers with leader lines -->
    {m_sleep}
    {m_hr}
    {m_glu}
    {m_a1c}
    {m_steps}

    <!-- Provenance Legend below illustration -->
    <g transform="translate(48, 382)">
        <circle cx="6" cy="6" r="3.5" fill="{PRIMARY}" stroke="{PRIMARY}" stroke-width="1.2" />
        <text x="16" y="9.5" font-family="Inter, system-ui, sans-serif" font-size="10.5" font-weight="500" fill="{TEXT_SECONDARY}">data present</text>
        <circle cx="118" cy="6" r="3.5" fill="#FFFFFF" stroke="{UNAVAILABLE_GREY}" stroke-width="1.2" stroke-dasharray="2 1.5" />
        <text x="128" y="9.5" font-family="Inter, system-ui, sans-serif" font-size="10.5" font-weight="500" fill="{TEXT_SECONDARY}">not available</text>
    </g>
</svg>"""
    import re
    clean_svg = re.sub(r">\s+<", "><", svg).replace("\n", " ").strip()
    return clean_svg
