"""SVG diagrams derived from computed design_specification (no fixed clipart)."""

# ruff: noqa: E501

from __future__ import annotations

import math
from decimal import Decimal
from typing import Any


def _d(value: str | float | int, default: float = 0.0) -> float:
    try:
        return float(Decimal(str(value)))
    except Exception:
        return default


def shell_cross_section_svg(design_spec: dict[str, Any]) -> str:
    g = design_spec["geometry"]
    d_shell = _d(g["shell_inside_diameter_m"], 0.5)
    n_tubes = int(g["physical_tube_count"])
    pitch = _d(g["tube_pitch_m"], 0.025)
    d_tube = _d(g["tube_outer_diameter_m"], 0.019)
    scale = 180 / max(d_shell, 0.3)
    R = d_shell * scale / 2
    cx, cy = 200, 160
    cols = max(1, int(math.sqrt(n_tubes * 1.2)))
    rows = max(1, math.ceil(n_tubes / cols))
    tube_r = max(2, d_tube * scale / 2)
    step = pitch * scale
    tubes: list[str] = []
    placed = 0
    for row in range(rows):
        for col in range(cols):
            if placed >= n_tubes:
                break
            ox = (col - (cols - 1) / 2) * step + (step / 4 if row % 2 else 0)
            oy = (row - (rows - 1) / 2) * step * 0.866
            if math.hypot(ox, oy) > R - tube_r - 4:
                continue
            tubes.append(
                f'<circle cx="{cx + ox:.1f}" cy="{cy + oy:.1f}" r="{tube_r:.1f}" '
                f'fill="#4fd1c5" stroke="#0d9488" stroke-width="0.6"/>'
            )
            placed += 1
    baffles = int(g["baffle_count"])
    baffle_lines = ""
    spacing_px = min(28, 140 / max(baffles, 1))
    for i in range(baffles):
        x = 80 + i * spacing_px
        baffle_lines += (
            f'<line x1="{x:.0f}" y1="{cy - R:.0f}" x2="{x:.0f}" y2="{cy + R:.0f}" '
            f'stroke="#94a3b8" stroke-width="2" stroke-dasharray="4 3"/>'
        )
    label = (
        f"Shell ID {g['shell_inside_diameter_m']} m · {n_tubes} tubes · "
        f"{g['baffle_count']} baffles @ {g['baffle_spacing_m']} m"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 320" role="img" aria-label="Shell cross-section">
  <rect width="100%" height="100%" fill="#0f172a"/>
  <text x="200" y="24" fill="#e2e8f0" font-size="12" text-anchor="middle" font-family="system-ui">{label}</text>
  {baffle_lines}
  <circle cx="{cx}" cy="{cy}" r="{R:.1f}" fill="#1e293b" stroke="#64748b" stroke-width="2"/>
  {"".join(tubes)}
  <text x="200" y="300" fill="#94a3b8" font-size="10" text-anchor="middle" font-family="monospace">
    Computed layout · pitch {g["tube_pitch_m"]} m · {g["tube_layout_pattern"]}
  </text>
</svg>"""


def tube_bundle_plan_svg(design_spec: dict[str, Any]) -> str:
    g = design_spec["geometry"]
    n_tubes = int(g["physical_tube_count"])
    pitch = _d(g["tube_pitch_m"])
    d_tube = _d(g["tube_outer_diameter_m"])
    cols = max(1, int(math.sqrt(n_tubes)))
    rows = max(1, math.ceil(n_tubes / cols))
    margin = 40
    step = 14
    tr = max(3, d_tube / pitch * step * 0.45)
    w = margin * 2 + cols * step
    h = margin * 2 + rows * step * 0.866
    els: list[str] = []
    k = 0
    for r in range(rows):
        for c in range(cols):
            if k >= n_tubes:
                break
            x = margin + c * step + (step / 3 if r % 2 else 0)
            y = margin + r * step * 0.866
            els.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{tr:.1f}" fill="#38bdf8" stroke="#0369a1"/>'
            )
            k += 1
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w:.0f} {h:.0f}" role="img" aria-label="Tube sheet pattern">
  <rect width="100%" height="100%" fill="#020617"/>
  <text x="{w / 2:.0f}" y="18" fill="#cbd5e1" font-size="11" text-anchor="middle" font-family="system-ui">
    Tube sheet ({n_tubes} tubes, triangular pitch {g["tube_pitch_m"]} m)
  </text>
  {"".join(els)}
</svg>"""


def diagrams_for_report(report_dict: dict[str, Any]) -> dict[str, str]:
    spec = report_dict.get("design_specification")
    if not spec:
        return {}
    return {
        "shell_cross_section_svg": shell_cross_section_svg(spec),
        "tube_bundle_plan_svg": tube_bundle_plan_svg(spec),
    }
