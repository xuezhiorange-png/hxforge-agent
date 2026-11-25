"""Independent V08 engineering thermal rating kernel (not Task172/173)."""

# ruff: noqa: E501

from __future__ import annotations

import math
import time
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

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
from hexagent.properties.base import FluidIdentifier, PropertyProvider, ReferenceStatePolicy
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import CandidateRatingBindings
from prototypes.v08_thermal_rating.v08_kernel_rating_acceptance_v1 import (
    CONTRACT_ID,
    MAX_ITERATIONS_BUDGET,
    convergence_pass,
    kernel_contract_pass,
    negative_temperature_cross_blocked,
)
from prototypes.v08_thermal_rating.v08_task037_evaluate_binding_v08 import evaluate_binding_task037

KERNEL_AUTHORITY_ID = "V08-INDEPENDENT-ENGINEERING-RATING-KERNEL-V1"
FLOW_ARRANGEMENT = "SINGLE_SHELL_PASS_TEMA_LMTD_F_V1"

KernelStatus = Literal["RATING_SUCCESS", "RATING_BLOCKED", "NOT_APPLICABLE"]


@dataclass(frozen=True)
class ThermalResistanceBreakdown:
    r_tube_convection_m2_k_w: str
    r_shell_convection_m2_k_w: str
    r_wall_m2_k_w: str
    r_fouling_inside_m2_k_w: str
    r_fouling_outside_m2_k_w: str
    u_clean_outer_w_m2_k: str
    area_outer_m2: str
    area_inner_m2: str


@dataclass(frozen=True)
class KernelThermalRatingResult:
    authority_id: str
    contract_id: str
    status: KernelStatus
    blocked_code: str | None
    converged: bool
    iterations: int
    wall_time_s: float
    q_w: str | None
    q_target_w: str
    duty_meets_target: bool
    ntu: str | None
    effectiveness: str | None
    lmtd_k: str | None
    f_correction_factor: str | None
    approach_temperature_k: str | None
    resistance: ThermalResistanceBreakdown | None
    tube_htc_w_m2_k: str | None
    shell_htc_w_m2_k: str | None
    ua_w_per_k: str | None
    tube_inlet_t_k: str
    tube_outlet_t_k: str | None
    shell_inlet_t_k: str
    shell_outlet_t_k: str | None
    tube_inlet_h_j_kg: str
    tube_outlet_h_j_kg: str | None
    shell_inlet_h_j_kg: str
    shell_outlet_h_j_kg: str | None
    energy_balance_q_tube_w: str | None
    energy_balance_q_shell_w: str | None
    energy_balance_residual_w: str | None
    energy_balance_pass: bool
    property_iteration_residual_w: str | None
    correlation_applicability: str
    model_notes: tuple[str, ...]
    provenance: dict[str, str]


def _reference_state(provider: PropertyProvider) -> ReferenceStatePolicy:
    ref = getattr(provider, "reference_state_policy", ReferenceStatePolicy.DEF)
    if isinstance(ref, ReferenceStatePolicy):
        return ref
    return ReferenceStatePolicy.DEF


def _state_h(provider: PropertyProvider, h: float, p_pa: float) -> Any:
    return provider.state_ph(
        FluidIdentifier(name="Water"),
        p_pa,
        h,
        reference_state=_reference_state(provider),
    )


def _state_t(provider: PropertyProvider, t_k: float, p_pa: float) -> Any:
    return provider.state_tp(FluidIdentifier(name="Water"), t_k, p_pa)


def _f_factor_tema_v1(tube_pass_count: int) -> Decimal:
    """TEMA 1-shell-pass correction (v1 table — not ideal counterflow)."""
    if tube_pass_count <= 1:
        return Decimal("0.98")
    if tube_pass_count == 2:
        return Decimal("0.90")
    return Decimal("0.85")


def _lmtd_k(t_hi: Decimal, t_ho: Decimal, t_ci: Decimal, t_co: Decimal) -> Decimal | None:
    d1 = t_hi - t_co
    d2 = t_ho - t_ci
    if d1 <= 0 or d2 <= 0:
        return None
    if abs(d1 - d2) < Decimal("1e-12"):
        return d1
    return (d1 - d2) / Decimal(str(math.log(float(d1 / d2))))


def _resistance_network(
    bindings: CandidateRatingBindings,
    t037: Task037SuccessResult,
    t166: Task166Result,
    t026: TubeSideThermalResult,
) -> tuple[Decimal, Decimal, Decimal, ThermalResistanceBreakdown]:
    h_o = t166.corrected_shell_side_heat_transfer_coefficient
    h_i = t026.tube_side_heat_transfer_coefficient_w_m2_k
    a_i = Decimal(bindings.bundle.bundle.task025_result.internal_heat_transfer_surface_area_m2)
    ratio = compute_outer_to_inner_area_ratio(
        Decimal(bindings.bundle.bundle.task025_result.hydraulic_diameter_m),
        Decimal(bindings.bundle.candidate.tube_outer_diameter_m),
    )
    a_o = a_i * ratio
    r_wall_o = t037.wall_resistance_outer_surface_m2_k_w
    r_fi = t037.inside_fouling_authority.fouling_resistance_m2_k_w * ratio
    r_fo = t037.outside_fouling_authority.fouling_resistance_m2_k_w
    r_i = ratio / h_i
    r_o = Decimal(1) / h_o
    denom = r_i + r_fi + r_wall_o + r_fo + r_o
    u_o = Decimal(0) if denom <= 0 else Decimal(1) / denom
    br = ThermalResistanceBreakdown(
        r_tube_convection_m2_k_w=format(r_i, "f"),
        r_shell_convection_m2_k_w=format(r_o, "f"),
        r_wall_m2_k_w=format(r_wall_o, "f"),
        r_fouling_inside_m2_k_w=format(r_fi, "f"),
        r_fouling_outside_m2_k_w=format(r_fo, "f"),
        u_clean_outer_w_m2_k=format(u_o, "f"),
        area_outer_m2=format(a_o, "f"),
        area_inner_m2=format(a_i, "f"),
    )
    return u_o, a_o, u_o * a_o, br


def rate_candidate_engineering_kernel_v1(
    bindings: CandidateRatingBindings,
    normalized: NormalizedUserDesignCase,
    *,
    provider: PropertyProvider,
) -> KernelThermalRatingResult:
    """Scalar-Q LMTD–F loop with independent enthalpy energy audit."""
    t0 = time.perf_counter()
    raw = bindings.bundle.bundle
    p_t = float(normalized.tube_side.inlet_pressure_pa)
    p_s = float(normalized.shell_side.inlet_pressure_pa)
    mdot_t = float(normalized.tube_side.mass_flow_kg_s)
    mdot_s = float(normalized.shell_side.mass_flow_kg_s)
    target = normalized.target_duty_w
    notes: list[str] = [FLOW_ARRANGEMENT, "NOT_TASK173_RATING"]

    t166 = raw.task166_result
    t026 = raw.task026_result
    if isinstance(t166, Task166BlockedResult) or not isinstance(t166, Task166Result):
        return _blocked(
            "CORRELATION_NOT_APPLICABLE",
            target,
            normalized,
            notes=("task166_blocked",),
            elapsed=time.perf_counter() - t0,
        )
    if t166.applicability is None or t166.applicability.status != ApplicabilityStatus.APPLICABLE:
        return _blocked(
            "CORRELATION_NOT_APPLICABLE",
            target,
            normalized,
            notes=(f"task166:{t166.applicability}",),
            elapsed=time.perf_counter() - t0,
        )
    if isinstance(t026, TubeSideBlockedResult) or not isinstance(t026, TubeSideThermalResult):
        return _blocked(
            "CORRELATION_NOT_APPLICABLE",
            target,
            normalized,
            notes=("task026_blocked",),
            elapsed=time.perf_counter() - t0,
        )
    t037_eval = evaluate_binding_task037(bindings, fouling_scenario="CLEAN")
    if t037_eval.status != "SUCCESS" or t037_eval.raw is None:
        return _blocked(
            "CORRELATION_NOT_APPLICABLE",
            target,
            normalized,
            notes=("task037_blocked",),
            elapsed=time.perf_counter() - t0,
        )
    t037 = t037_eval.raw

    u_o, a_o, ua0, resistance = _resistance_network(bindings, t037, t166, t026)
    if ua0 <= 0:
        return _blocked(
            "UA_NON_POSITIVE",
            target,
            normalized,
            notes=notes,
            elapsed=time.perf_counter() - t0,
        )

    st_in = _state_t(provider, float(normalized.tube_side.inlet_temperature_k), p_t)
    ss_in = _state_t(provider, float(normalized.shell_side.inlet_temperature_k), p_s)
    h_ti = float(st_in.enthalpy_j_kg)
    h_si = float(ss_in.enthalpy_j_kg)
    t_ti = float(st_in.temperature_k)
    t_si = float(ss_in.temperature_k)
    if t_ti <= t_si:
        return _blocked(
            "NO_THERMODYNAMIC_DRIVING_FORCE",
            target,
            normalized,
            notes=notes + ("tube_not_hotter_than_shell",),
            elapsed=time.perf_counter() - t0,
        )

    n_pass = int(bindings.bundle.candidate.tube_pass_count)
    f_fac = _f_factor_tema_v1(n_pass)
    q = float(target)
    q_prev = -1.0
    q_model = q
    t_to = t_ti
    t_so = t_si
    converged = False
    iterations = 0
    eff = Decimal(0)
    ntu = Decimal(0)
    lmtd: Decimal | None = None

    for _iterations in range(1, MAX_ITERATIONS_BUDGET + 1):
        q = max(0.0, min(q, mdot_t * (h_ti - h_si) * 0.999, mdot_s * 1e6))
        h_to = h_ti - q / mdot_t
        h_so = h_si + q / mdot_s
        try:
            st_o = _state_h(provider, h_to, p_t)
            ss_o = _state_h(provider, h_so, p_s)
        except Exception as exc:
            return _blocked(
                "PROPERTY_STATE_OUT_OF_RANGE",
                target,
                normalized,
                notes=(*notes, type(exc).__name__),
                elapsed=time.perf_counter() - t0,
            )
        t_to = float(st_o.temperature_k)
        t_so = float(ss_o.temperature_k)
        cross = negative_temperature_cross_blocked(
            t_tube_in=Decimal(str(t_ti)),
            t_shell_in=Decimal(str(t_si)),
            t_tube_out=Decimal(str(t_to)),
            t_shell_out=Decimal(str(t_so)),
        )
        if cross:
            return _blocked(
                "TEMPERATURE_CROSS_OR_INVALID_OUTLET",
                target,
                normalized,
                notes=notes,
                elapsed=time.perf_counter() - t0,
                partial_q=q,
                t_to=t_to,
                t_so=t_so,
                h_to=h_to,
                h_so=h_so,
            )
        lmtd = _lmtd_k(
            Decimal(str(t_ti)),
            Decimal(str(t_to)),
            Decimal(str(t_si)),
            Decimal(str(t_so)),
        )
        if lmtd is None or lmtd <= 0:
            return _blocked(
                "LMTD_NOT_COMPUTABLE",
                target,
                normalized,
                notes=notes,
                elapsed=time.perf_counter() - t0,
            )
        q_model = float(ua0 * f_fac * lmtd)
        c_t = mdot_t * float(
            _state_t(provider, (t_ti + t_to) / 2, p_t).cp_j_kg_k
        )
        c_s = mdot_s * float(
            _state_t(provider, (t_si + t_so) / 2, p_s).cp_j_kg_k
        )
        c_min = min(c_t, c_s)
        c_min_d = Decimal(str(c_min))
        ntu = ua0 / c_min_d if c_min_d > 0 else Decimal(0)
        q_max = float(c_min_d) * (t_ti - t_si)
        eff = Decimal(str(q / q_max)) if q_max > 0 else Decimal(0)
        q_next = 0.65 * q + 0.35 * q_model
        res_q = Decimal(str(abs(q_next - q)))
        if convergence_pass(
            q_residual_w=res_q,
            q_mag_w=Decimal(str(max(q, 1.0))),
            energy_residual_w=Decimal(str(abs(mdot_t * (h_ti - h_to) - mdot_s * (h_so - h_si)))),
            energy_mag_w=Decimal(str(max(q, 1.0))),
        ):
            converged = True
            q = q_next
            break
        if abs(q_next - q_prev) < 1e-9:
            break
        q_prev = q
        q = q_next

    q_tube = mdot_t * (h_ti - h_to)
    q_shell = mdot_s * (h_so - h_si)
    e_res = abs(q_tube - q_shell)
    e_pass = e_res <= max(10.0, 1e-4 * max(q, 1.0))
    approach = min(t_to - t_so, t_ti - t_si)
    duty_ok = Decimal(str(q)) >= target
    contract = kernel_contract_pass(
        converged=converged,
        energy_balance_pass=e_pass,
        temperature_cross=False,
        iterations=iterations,
    )
    status: KernelStatus = "RATING_SUCCESS" if contract == "PASS" and duty_ok else "RATING_BLOCKED"
    blocked = None if status == "RATING_SUCCESS" else (
        "ITERATION_OR_ENERGY_OR_DUTY" if contract == "BLOCKED" else "DUTY_BELOW_TARGET"
    )
    elapsed = time.perf_counter() - t0
    return KernelThermalRatingResult(
        authority_id=KERNEL_AUTHORITY_ID,
        contract_id=CONTRACT_ID,
        status=status,
        blocked_code=blocked,
        converged=converged,
        iterations=iterations,
        wall_time_s=round(elapsed, 4),
        q_w=format(Decimal(str(q)), "f"),
        q_target_w=str(target),
        duty_meets_target=duty_ok,
        ntu=format(ntu, "f"),
        effectiveness=format(eff, "f"),
        lmtd_k=format(lmtd, "f") if lmtd else None,
        f_correction_factor=format(f_fac, "f"),
        approach_temperature_k=format(Decimal(str(approach)), "f"),
        resistance=resistance,
        tube_htc_w_m2_k=str(t026.tube_side_heat_transfer_coefficient_w_m2_k),
        shell_htc_w_m2_k=str(t166.corrected_shell_side_heat_transfer_coefficient),
        ua_w_per_k=format(ua0, "f"),
        tube_inlet_t_k=str(t_ti),
        tube_outlet_t_k=str(t_to),
        shell_inlet_t_k=str(t_si),
        shell_outlet_t_k=str(t_so),
        tube_inlet_h_j_kg=str(h_ti),
        tube_outlet_h_j_kg=str(h_to),
        shell_inlet_h_j_kg=str(h_si),
        shell_outlet_h_j_kg=str(h_so),
        energy_balance_q_tube_w=format(Decimal(str(q_tube)), "f"),
        energy_balance_q_shell_w=format(Decimal(str(q_shell)), "f"),
        energy_balance_residual_w=format(Decimal(str(e_res)), "f"),
        energy_balance_pass=e_pass,
        property_iteration_residual_w=format(Decimal(str(abs(q - q_model))), "f"),
        correlation_applicability="APPLICABLE",
        model_notes=tuple(notes),
        provenance={
            "task166_hash": t166.result_hash,
            "task026_hash": t026.result_hash,
            "task037_hash": t037.result_hash,
            "candidate_id": bindings.rating_request.candidate_id,
            "geometry_projection_hash": bindings.geometry_projection_hash,
        },
    )


def _blocked(
    code: str,
    target: Decimal,
    normalized: NormalizedUserDesignCase,
    *,
    notes: tuple[str, ...],
    elapsed: float,
    **partial: Any,
) -> KernelThermalRatingResult:
    return KernelThermalRatingResult(
        authority_id=KERNEL_AUTHORITY_ID,
        contract_id=CONTRACT_ID,
        status="RATING_BLOCKED",
        blocked_code=code,
        converged=False,
        iterations=0,
        wall_time_s=round(elapsed, 4),
        q_w=str(partial.get("partial_q")) if partial.get("partial_q") else None,
        q_target_w=str(target),
        duty_meets_target=False,
        ntu=None,
        effectiveness=None,
        lmtd_k=None,
        f_correction_factor=None,
        approach_temperature_k=None,
        resistance=None,
        tube_htc_w_m2_k=None,
        shell_htc_w_m2_k=None,
        ua_w_per_k=None,
        tube_inlet_t_k=str(normalized.tube_side.inlet_temperature_k),
        tube_outlet_t_k=str(partial.get("t_to")) if partial.get("t_to") else None,
        shell_inlet_t_k=str(normalized.shell_side.inlet_temperature_k),
        shell_outlet_t_k=str(partial.get("t_so")) if partial.get("t_so") else None,
        tube_inlet_h_j_kg="",
        tube_outlet_h_j_kg=None,
        shell_inlet_h_j_kg="",
        shell_outlet_h_j_kg=None,
        energy_balance_q_tube_w=None,
        energy_balance_q_shell_w=None,
        energy_balance_residual_w=None,
        energy_balance_pass=False,
        property_iteration_residual_w=None,
        correlation_applicability="BLOCKED",
        model_notes=notes,
        provenance={},
    )


__all__ = [
    "KERNEL_AUTHORITY_ID",
    "KernelThermalRatingResult",
    "rate_candidate_engineering_kernel_v1",
]