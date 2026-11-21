"""Indicative thermal prescreen (Task166/026/037 + CoolProp ε-NTU) — not production Task173."""

# ruff: noqa: E501

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
from hexagent.properties.base import FluidIdentifier, PropertyProvider
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings

ThermalPrescreenStatus = Literal[
    "INDICATIVE_PASS", "INDICATIVE_FAIL", "NOT_EVALUATED"
]


@dataclass(frozen=True)
class ThermalPrescreenResult:
    status: ThermalPrescreenStatus
    ua_w_per_k: str | None
    epsilon_ntu_q_w: str | None
    target_duty_gap_w: str | None
    predicted_tube_outlet_k: str | None
    predicted_shell_outlet_k: str | None
    task166_applicability: str
    shell_htc_w_m2_k: str | None
    tube_htc_w_m2_k: str | None
    property_basis: str
    wall_resistance_source: str | None
    area_basis_m2: str | None
    notes: tuple[str, ...]


def _cp_kg_s(_provider: PropertyProvider, *, _fluid: str, t_k: Decimal, p_pa: Decimal) -> Decimal:
    state = _provider.state_tp(FluidIdentifier(name="Water"), float(t_k), float(p_pa))
    return Decimal(str(state.cp_j_kg_k))


def _epsilon_ntu_counterflow(
    *,
    ua: Decimal,
    c_hot: Decimal,
    c_cold: Decimal,
    t_hot_in: Decimal,
    t_cold_in: Decimal,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    c_min = min(c_hot, c_cold)
    c_max = max(c_hot, c_cold)
    if c_min <= 0 or c_max <= 0:
        return Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0")
    cr = c_min / c_max
    ntu = ua / c_min
    if ntu <= 0:
        return Decimal("0"), t_hot_in, t_cold_in, Decimal("0")
    if cr >= Decimal("1"):
        eff = ntu / (Decimal("1") + ntu)
    else:
        expo = Decimal(str(math.exp(float(-ntu * (Decimal("1") - cr)))))
        num = Decimal("1") - expo
        den = Decimal("1") - cr * expo
        if den == 0:
            eff = Decimal("0")
        else:
            eff = num / den
    q_max = c_min * (t_hot_in - t_cold_in)
    q = eff * q_max
    t_ho = t_hot_in - q / c_hot
    t_co = t_cold_in + q / c_cold
    return q, t_ho, t_co, eff


def run_thermal_prescreen(
    bindings: CandidateRatingBindings,
    normalized: NormalizedUserDesignCase,
    *,
    provider: PropertyProvider,
) -> ThermalPrescreenResult:
    raw = bindings.bundle.bundle
    t166 = raw.task166_result
    t026 = raw.task026_result
    t025 = raw.task025_result
    prop_basis = (
        f"CoolProp tube={normalized.tube_side.fluid} shell={normalized.shell_side.fluid} "
        f"at_case_inlet_T_P"
    )
    if isinstance(t166, Task166BlockedResult):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability="BLOCKED",
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            property_basis=prop_basis,
            wall_resistance_source=None,
            area_basis_m2=None,
            notes=(f"task166_blocked:{t166.result_id}",),
        )
    if not isinstance(t166, Task166Result):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability="NOT_EVALUATED",
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            property_basis=prop_basis,
            wall_resistance_source=None,
            area_basis_m2=None,
            notes=("task166_missing",),
        )
    applicability = "NOT_EVALUATED"
    if t166.applicability is not None:
        applicability = str(t166.applicability.status.value)
    if t166.applicability is None or t166.applicability.status != ApplicabilityStatus.APPLICABLE:
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=None,
            tube_htc_w_m2_k=None,
            property_basis=prop_basis,
            wall_resistance_source=None,
            area_basis_m2=None,
            notes=("task166_not_applicable",),
        )
    if isinstance(t026, TubeSideBlockedResult) or not isinstance(t026, TubeSideThermalResult):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=str(t166.corrected_shell_side_heat_transfer_coefficient),
            tube_htc_w_m2_k=None,
            property_basis=prop_basis,
            wall_resistance_source=None,
            area_basis_m2=None,
            notes=("task026_blocked",),
        )

    t037 = raw.task037_result
    if not isinstance(t037, Task037SuccessResult):
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=str(t166.corrected_shell_side_heat_transfer_coefficient),
            tube_htc_w_m2_k=str(t026.tube_side_heat_transfer_coefficient_w_m2_k),
            property_basis=prop_basis,
            wall_resistance_source=None,
            area_basis_m2=str(t025.internal_heat_transfer_surface_area_m2),
            notes=(
                "task037_wall_authority_required_for_indicative_pass",
                "no_silent_default_wall_conductivity",
            ),
        )

    h_o = t166.corrected_shell_side_heat_transfer_coefficient
    h_i = t026.tube_side_heat_transfer_coefficient_w_m2_k
    a_i = Decimal(t025.internal_heat_transfer_surface_area_m2)
    ratio = compute_outer_to_inner_area_ratio(
        Decimal(t025.hydraulic_diameter_m),
        Decimal(bindings.bundle.candidate.tube_outer_diameter_m),
    )
    a_o = a_i * ratio
    r_wall_o = t037.wall_resistance_outer_surface_m2_k_w
    wall_src = f"task037:{t037.wall_material_authority_hash}/{t037.wall_conductivity_authority_hash}"

    denom = ratio / h_i + r_wall_o + Decimal(1) / h_o
    if denom <= 0 or a_o <= 0:
        return ThermalPrescreenResult(
            status="NOT_EVALUATED",
            ua_w_per_k=None,
            epsilon_ntu_q_w=None,
            target_duty_gap_w=None,
            predicted_tube_outlet_k=None,
            predicted_shell_outlet_k=None,
            task166_applicability=applicability,
            shell_htc_w_m2_k=str(h_o),
            tube_htc_w_m2_k=str(h_i),
            property_basis=prop_basis,
            wall_resistance_source=wall_src,
            area_basis_m2=str(a_o),
            notes=("resistance_non_positive",),
        )
    u_o = Decimal(1) / denom
    ua = u_o * a_o

    t_ti = Decimal(str(normalized.tube_side.inlet_temperature_k))
    t_si = Decimal(str(normalized.shell_side.inlet_temperature_k))
    p_t = Decimal(str(normalized.tube_side.inlet_pressure_pa))
    p_s = Decimal(str(normalized.shell_side.inlet_pressure_pa))
    c_t = _cp_kg_s(provider, fluid=normalized.tube_side.fluid, t_k=t_ti, p_pa=p_t) * normalized.tube_side.mass_flow_kg_s
    c_s = _cp_kg_s(provider, fluid=normalized.shell_side.fluid, t_k=t_si, p_pa=p_s) * normalized.shell_side.mass_flow_kg_s

    q_ntu, t_to, t_so, _eff = _epsilon_ntu_counterflow(
        ua=ua,
        c_hot=c_t,
        c_cold=c_s,
        t_hot_in=t_ti,
        t_cold_in=t_si,
    )
    gap = q_ntu - normalized.target_duty_w
    status: ThermalPrescreenStatus = (
        "INDICATIVE_PASS" if q_ntu >= normalized.target_duty_w else "INDICATIVE_FAIL"
    )
    return ThermalPrescreenResult(
        status=status,
        ua_w_per_k=format(ua.quantize(Decimal("0.01")), "f"),
        epsilon_ntu_q_w=format(q_ntu.quantize(Decimal("0.1")), "f"),
        target_duty_gap_w=format(gap.quantize(Decimal("0.1")), "f"),
        predicted_tube_outlet_k=format(t_to.quantize(Decimal("0.001")), "f"),
        predicted_shell_outlet_k=format(t_so.quantize(Decimal("0.001")), "f"),
        task166_applicability=applicability,
        shell_htc_w_m2_k=str(h_o),
        tube_htc_w_m2_k=str(h_i),
        property_basis=prop_basis,
        wall_resistance_source=wall_src,
        area_basis_m2=str(a_o),
        notes=(
            "epsilon_ntu_counterflow_indicative_only",
            "THERMAL_PRESCREEN_ISOLATED_NOT_TASK173",
        ),
    )


__all__ = ["ThermalPrescreenResult", "run_thermal_prescreen"]