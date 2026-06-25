"""Thermal resistance network, LMTD, and ε-NTU for double-pipe exchangers.

All functions are pure — no I/O, no property calls.  They operate on
numeric values produced by the caller.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Flow arrangement
# ---------------------------------------------------------------------------


class FlowArrangement(StrEnum):
    """Heat-exchanger flow arrangement."""

    COUNTERFLOW = "counterflow"
    PARALLEL = "parallel"


# ---------------------------------------------------------------------------
# Thermal resistance breakdown
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThermalResistanceBreakdown:
    """Complete thermal resistance breakdown for a double-pipe exchanger.

    All resistances are in [K/W].  ``1/UA = sum(components)``.
    """

    r_conv_inner: float
    """Inner-side convective resistance [K/W]."""
    r_foul_inner: float
    """Inner-side fouling resistance [K/W]."""
    r_wall: float
    """Cylindrical wall conduction resistance [K/W]."""
    r_foul_outer: float
    """Outer-side fouling resistance [K/W]."""
    r_conv_outer: float
    """Outer-side convective resistance [K/W]."""

    def __post_init__(self) -> None:
        for name in (
            "r_conv_inner",
            "r_foul_inner",
            "r_wall",
            "r_foul_outer",
            "r_conv_outer",
        ):
            val = getattr(self, name)
            if not math.isfinite(val) or val < 0:
                raise ValueError(f"{name} must be finite and >= 0, got {val}")

    @property
    def total_resistance_kw(self) -> float:
        """Total thermal resistance [K/W]."""
        return (
            self.r_conv_inner
            + self.r_foul_inner
            + self.r_wall
            + self.r_foul_outer
            + self.r_conv_outer
        )

    @property
    def ua_w_k(self) -> float:
        """Overall heat-transfer coefficient × area [W/K]."""
        r_total = self.total_resistance_kw
        if r_total <= 0:
            raise ValueError("Total resistance must be > 0 for UA computation")
        return 1.0 / r_total

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "r_conv_inner": self.r_conv_inner,
            "r_foul_inner": self.r_foul_inner,
            "r_wall": self.r_wall,
            "r_foul_outer": self.r_foul_outer,
            "r_conv_outer": self.r_conv_outer,
            "total_resistance": self.total_resistance_kw,
            "ua_w_k": self.ua_w_k,
        }


# ---------------------------------------------------------------------------
# Thermal resistance computation
# ---------------------------------------------------------------------------


def compute_wall_resistance(
    d_inner_m: float,
    d_outer_m: float,
    length_m: float,
    wall_conductivity_w_m_k: float,
) -> float:
    """Cylindrical wall conduction resistance [K/W].

    R_wall = ln(D_o / D_i) / (2π·k·L)
    """
    if d_outer_m <= d_inner_m:
        raise ValueError(f"outer diameter ({d_outer_m}) must exceed inner diameter ({d_inner_m})")
    if length_m <= 0:
        raise ValueError(f"length must be > 0, got {length_m}")
    if wall_conductivity_w_m_k <= 0:
        raise ValueError(f"wall conductivity must be > 0, got {wall_conductivity_w_m_k}")
    return math.log(d_outer_m / d_inner_m) / (2.0 * math.pi * wall_conductivity_w_m_k * length_m)


def compute_convective_resistance(
    h: float,
    area_m2: float,
) -> float:
    """Convective resistance [K/W].

    R_conv = 1 / (h · A)
    """
    if h <= 0:
        raise ValueError(f"h must be > 0, got {h}")
    if area_m2 <= 0:
        raise ValueError(f"area must be > 0, got {area_m2}")
    return 1.0 / (h * area_m2)


def compute_fouling_resistance(
    fouling_m2k_w: float,
    area_m2: float,
) -> float:
    """Fouling resistance on a surface [K/W].

    R_foul = Rf / A

    Parameters
    ----------
    fouling_m2k_w :
        Fouling factor in m²·K/W.
    area_m2 :
        Surface area of the fouled surface [m²].
    """
    if fouling_m2k_w < 0:
        raise ValueError(f"fouling must be >= 0, got {fouling_m2k_w}")
    if area_m2 <= 0:
        raise ValueError(f"area must be > 0, got {area_m2}")
    if fouling_m2k_w == 0:
        return 0.0
    return fouling_m2k_w / area_m2


def build_thermal_resistance(
    h_inner: float,
    h_outer: float,
    area_inner_m2: float,
    area_outer_m2: float,
    wall_resistance_kw: float,
    fouling_inner_m2k_w: float = 0.0,
    fouling_outer_m2k_w: float = 0.0,
) -> ThermalResistanceBreakdown:
    """Build the complete thermal resistance network.

    Parameters
    ----------
    h_inner :
        Inner-side convective coefficient [W/(m²·K)].
    h_outer :
        Outer-side convective coefficient [W/(m²·K)].
    area_inner_m2 :
        Inner surface area [m²].
    area_outer_m2 :
        Outer surface area [m²].
    wall_resistance_kw :
        Pre-computed cylindrical wall resistance [K/W].
    fouling_inner_m2k_w :
        Inner-side fouling factor [m²·K/W].
    fouling_outer_m2k_w :
        Outer-side fouling factor [m²·K/W].
    """
    return ThermalResistanceBreakdown(
        r_conv_inner=compute_convective_resistance(h_inner, area_inner_m2),
        r_foul_inner=compute_fouling_resistance(fouling_inner_m2k_w, area_inner_m2),
        r_wall=wall_resistance_kw,
        r_foul_outer=compute_fouling_resistance(fouling_outer_m2k_w, area_outer_m2),
        r_conv_outer=compute_convective_resistance(h_outer, area_outer_m2),
    )


# ---------------------------------------------------------------------------
# LMTD
# ---------------------------------------------------------------------------


def lmtd_counterflow(
    th_in: float,
    th_out: float,
    tc_in: float,
    tc_out: float,
    *,
    temp_tolerance: float = 1e-10,
) -> float:
    """Log-mean temperature difference for counter-flow.

    ΔT₁ = T_h,in − T_c,out
    ΔT₂ = T_h,out − T_c,in

    Returns LMTD = (ΔT₁ − ΔT₂) / ln(ΔT₁ / ΔT₂) when ΔT₁ ≠ ΔT₂.
    Returns arithmetic mean when ΔT₁ ≈ ΔT₂.
    Returns NaN when any terminal ΔT ≤ 0 (temperature crossing).

    Parameters
    ----------
    temp_tolerance :
        Below this, terminal ΔT is treated as zero.
    """
    dt1 = th_in - tc_out
    dt2 = th_out - tc_in
    return _compute_lmtd(dt1, dt2, temp_tolerance)


def lmtd_parallel(
    th_in: float,
    th_out: float,
    tc_in: float,
    tc_out: float,
    *,
    temp_tolerance: float = 1e-10,
) -> float:
    """Log-mean temperature difference for parallel-flow.

    ΔT₁ = T_h,in − T_c,in
    ΔT₂ = T_h,out − T_c,out
    """
    dt1 = th_in - tc_in
    dt2 = th_out - tc_out
    return _compute_lmtd(dt1, dt2, temp_tolerance)


def _compute_lmtd(dt1: float, dt2: float, temp_tolerance: float) -> float:
    """Core LMTD computation with stable limit."""
    if dt1 <= temp_tolerance or dt2 <= temp_tolerance:
        return float("nan")
    if abs(dt1 - dt2) < temp_tolerance:
        return (dt1 + dt2) / 2.0
    return (dt1 - dt2) / math.log(dt1 / dt2)


# ---------------------------------------------------------------------------
# ε-NTU
# ---------------------------------------------------------------------------


def effectiveness_counterflow(
    ntu: float,
    capacity_ratio: float,
) -> float:
    """Effectiveness for counter-flow heat exchanger.

    ε = (1 − exp(−NTU·(1 − C_r))) / (1 − C_r·exp(−NTU·(1 − C_r)))

    Special case C_r = 1: ε = NTU / (1 + NTU)
    """
    if capacity_ratio < 0 or capacity_ratio > 1:
        raise ValueError(f"capacity_ratio must be in [0, 1], got {capacity_ratio}")
    if ntu < 0:
        raise ValueError(f"NTU must be >= 0, got {ntu}")

    if abs(capacity_ratio - 1.0) < 1e-12:
        return ntu / (1.0 + ntu)

    exp_arg = -ntu * (1.0 - capacity_ratio)
    exp_val = math.exp(exp_arg)
    return (1.0 - exp_val) / (1.0 - capacity_ratio * exp_val)


def effectiveness_parallel(
    ntu: float,
    capacity_ratio: float,
) -> float:
    """Effectiveness for parallel-flow heat exchanger.

    ε = (1 − exp(−NTU·(1 + C_r))) / (1 + C_r)
    """
    if capacity_ratio < 0 or capacity_ratio > 1:
        raise ValueError(f"capacity_ratio must be in [0, 1], got {capacity_ratio}")
    if ntu < 0:
        raise ValueError(f"NTU must be >= 0, got {ntu}")

    exp_arg = -ntu * (1.0 + capacity_ratio)
    exp_val = math.exp(exp_arg)
    return (1.0 - exp_val) / (1.0 + capacity_ratio)


def duty_from_effectiveness(
    effectiveness: float,
    c_min: float,
    th_in: float,
    tc_in: float,
) -> float:
    """Compute duty from effectiveness.

    Q = ε · C_min · (T_h,in − T_c,in)
    """
    return effectiveness * c_min * (th_in - tc_in)
