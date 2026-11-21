"""Indicative thermal prescreen (Task166/026/171/037 chain) — not production Task173."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from hexagent.exchangers.shell_tube.bell_delaware.models import (
    ApplicabilityStatus,
    Task166BlockedResult,
    Task166Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_outer_to_inner_area_ratio,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
    Task037SuccessResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    TubeSideBlockedResult,
    TubeSideThermalResult,
)
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings

ThermalPrescreenStatus = Literal[
    "INDICATIVE_PASS", "INDICATIVE_FAIL", "NOT_EVALUATED"
]

CP_WATER_J_KG_K = Decimal("4180")
WALL_CONDUCTIVITY_FALLBACK_W_M_K = Decimal("14.0")


@dataclass(frozen=True)
class ThermalPrescreenResult:
    status: ThermalPrescreenStatus
    estimated_ua_w_per_k: str | None
    estimated_q_w: str | None
    task166_applicability: str
    shell_htc_w_m2_k: str | None
    tube_htc_w_m2_k: str | None
    notes: tuple[str, ...]


def _log_mean_delta_t(dt1: Decimal, dt2: Decimal) -> Decimal:
    if dt1 <= 0 or dt2 <= 0:
        return Decimal("0")
    if dt1 == dt2:
        return dt1
    ratio = float(dt1 / dt2)
    if ratio <= 0:
        return Decimal("0")
    return (dt1 - dt2) / Decimal(str(math.log(ratio)))


def _counterflow_lmtd_for_duty(
    normalized: NormalizedUserDesignCase,
) -> tuple[Decimal, tuple[str, ...]]:
    notes: list[str] = []
    q = normalized.target_duty_w
    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    m_t = normalized.tube_side.mass_flow_kg_s
    m_s = normalized.shell_side.mass_flow_kg_s
    cp = CP_WATER_J_KG_K
    if m_t <= 0 or m_s <= 0:
        notes.append("mass_flow_non_positive")
        return Decimal("0"), tuple(notes)
    t_to = t_ti - q / (m_t * cp)
    t_so = t_si + q / (m_s * cp)
    dt1 = t_ti - t_so
    dt2 = t_to - t_si
    lmtd = _log_mean_delta_t(dt1, dt2)
    notes.append("lmtd_from_target_duty_energy_balance_not_task173")
    return lmtd, tuple(notes)


def run_thermal_prescreen(
    bindings: CandidateRatingBindings,
    normalized: NormalizedUserDesignCase,
) -> ThermalPrescreenResult:
    raw = bindings.bundle.bundle
    t166 = raw.task166_result
    t026 = raw.task026_result
    t025 = raw.task025_result
    if isinstance(t166, Task166BlockedResult):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            estimated_ua_w_per_k=None,
            estimated_q_w=None,
            task166_applicability="BLOCKED",
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            notes=(f"task166_blocked:{t166.result_id}",),
        )
    if not isinstance(t166, Task166Result):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            estimated_ua_w_per_k=None,
            estimated_q_w=None,
            task166_applicability="NOT_EVALUATED",
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            notes=("task166_missing",),
        )
    applicability = "NOT_EVALUATED"
    if t166.applicability is not None:
        applicability = str(t166.applicability.status.value)
    if t166.applicability is None or t166.applicability.status != ApplicabilityStatus.APPLICABLE:
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            estimated_ua_w_per_k=None,
            estimated_q_w=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            notes=("task166_not_applicable",),
        )
    if isinstance(t026, TubeSideBlockedResult) or not isinstance(t026, TubeSideThermalResult):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            estimated_ua_w_per_k=None,
            estimated_q_w=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=str(t166.corrected_shell_side_heat_transfer_coefficient),
            tube_htc_w_m2_k=None,
            notes=("task026_blocked",),
        )

    h_o = t166.corrected_shell_side_heat_transfer_coefficient
    h_i = t026.tube_side_heat_transfer_coefficient_w_m2_k
    a_i = Decimal(t025.internal_heat_transfer_surface_area_m2)
    ratio = compute_outer_to_inner_area_ratio(
        Decimal(t025.hydraulic_diameter_m),
        Decimal(bindings.bundle.candidate.tube_outer_diameter_m),
    )
    a_o = a_i * ratio
    t037 = raw.task037_result
    if isinstance(t037, Task037SuccessResult):
        r_wall_o = t037.wall_resistance_outer_surface_m2_k_w
    else:
        inner = Decimal(t025.hydraulic_diameter_m)
        outer = Decimal(bindings.bundle.candidate.tube_outer_diameter_m)
        from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
            compute_wall_resistance,
        )

        r_wall_o = compute_wall_resistance(
            inner,
            outer,
            WALL_CONDUCTIVITY_FALLBACK_W_M_K,
            a_i,
        ).wall_resistance_outer_surface_m2_k_w

    denom = ratio / h_i + r_wall_o + Decimal(1) / h_o
    if denom <= 0 or a_o <= 0:
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            estimated_ua_w_per_k=None,
            estimated_q_w=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=str(h_o),
            tube_htc_w_m2_k=str(h_i),
            notes=("resistance_non_positive",),
        )
    u_o = Decimal(1) / denom
    ua = u_o * a_o
    lmtd, lmtd_notes = _counterflow_lmtd_for_duty(normalized)
    q_est = ua * lmtd if lmtd > 0 else Decimal("0")
    status: ThermalPrescreenStatus = (
        "INDICATIVE_PASS" if q_est >= normalized.target_duty_w else "INDICATIVE_FAIL"
    )
    return ThermalPrescreenResult(
        status=status,
        estimated_ua_w_per_k=format(ua.quantize(Decimal("0.01")), "f"),
        estimated_q_w=format(q_est.quantize(Decimal("0.1")), "f"),
        task166_applicability=applicability,
        shell_htc_w_m2_k=str(h_o),
        tube_htc_w_m2_k=str(h_i),
        notes=(*lmtd_notes, "THERMAL_PRESCREEN_ISOLATED_NOT_TASK173"),
    )


__all__ = ["ThermalPrescreenResult", "run_thermal_prescreen"]