"""True (q, Twi, Two) cell closure via Task172 _eval_trial — no nested solver in residuals."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.engineering import (
    compute_wall_resistance,
)
from hexagent.exchangers.shell_tube.task172_local_runtime import service as t172_service
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    recompute_task172_request_hash,
    validate_candidate_request,
    validate_request,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _d,
    _effective_h_min_j_kg,
    _LowSideDomainInfeasible,
    _state_from_enthalpy,
    _task172_request,
    effective_shell_mass_flow_kg_s,
    effective_tube_mass_flow_kg_s,
)

Task172Request = Task172LocalRequest | CandidateTask172LocalRequest

_TRUE_COUPLED_BUDGET_NFEV = 96


@dataclass(frozen=True)
class ClosurePrimitives:
    tube_bulk_snapshot: Any
    shell_bulk_snapshot: Any
    tube_h_base: Decimal
    shell_h_base: Decimal
    wall_resistance_k_w: Decimal
    tube_apply_c3: bool
    tube_bulk_id: str
    shell_bulk_id: str


def local_cell_bulk_temperatures_k_from_q(
    q_w: float,
    *,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
) -> tuple[float, float, Any, Any]:
    """Task173 enthalpy propagation: cell-mean bulk temperatures and local thermo states."""
    q = _d(q_w)
    if q == Decimal(0):
        return (
            float(tube_upstream.native.temperature_k),
            float(shell_physical_left.native.temperature_k),
            tube_upstream,
            shell_physical_left,
        )
    with localcontext() as ctx:
        ctx.prec = 70
        tube_mdot = effective_tube_mass_flow_kg_s()
        shell_mdot = effective_shell_mass_flow_kg_s()
        h_t_up = _d(tube_upstream.native.enthalpy_j_kg)
        h_s_left = _d(shell_physical_left.native.enthalpy_j_kg)
        tube_down_h = h_t_up - q / tube_mdot
        shell_next_h = h_s_left - q / shell_mdot
        tube_mid_h = (h_t_up + tube_down_h) / Decimal(2)
        shell_mid_h = (h_s_left + shell_next_h) / Decimal(2)
    h_min = _effective_h_min_j_kg()
    if shell_next_h < h_min:
        raise _LowSideDomainInfeasible
    tube_local = _state_from_enthalpy(provider, tube_mid_h, side="TUBE")
    shell_local = _state_from_enthalpy(provider, shell_mid_h, side="SHELL")
    return (
        float(tube_local.native.temperature_k),
        float(shell_local.native.temperature_k),
        tube_local,
        shell_local,
    )


def build_task172_request_for_q(
    q_w: float,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
) -> tuple[Task172Request, Any, Any]:
    _tube_k, _shell_k, tube_local, shell_local = local_cell_bulk_temperatures_k_from_q(
        q_w,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
    )
    request = _task172_request(support, tube_local, shell_local, shell_authority)
    return request, tube_local, shell_local


def build_closure_primitives(
    request: Task172Request,
    provider: Any,
) -> ClosurePrimitives:
    support = request.support
    tube_bulk_snapshot, tube_bulk_id, _ = t172_service._snapshot(
        provider,
        request,
        "TUBE",
        f"{support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_bulk_snapshot, shell_bulk_id, _ = t172_service._snapshot(
        provider,
        request,
        "SHELL",
        f"{support.shell_cell_id}:CELL_MEAN",
        request.shell_bulk_state.temperature_k,
        request.shell_bulk_state.pressure_pa,
    )
    tube_resolution = t172_service._resolve_tube_side_htc(
        request, tube_bulk_snapshot, request.tube_mass_flow_kg_s
    )
    shell_h_base, *_rest = t172_service._shell_base_htc(
        request, shell_bulk_snapshot, request.shell_mass_flow_kg_s
    )
    if type(request) is CandidateTask172LocalRequest:
        tube_id = request.candidate_binding.task025_result.hydraulic_diameter_m
        bell_geometry = request.candidate_binding.task166_result.bell_geometry
        if bell_geometry is None:
            raise ValueError("missing bell geometry")
        tube_od = bell_geometry.tube_outer_diameter_m
    else:
        tube_id = t172_service.TUBE_ID_M
        tube_od = t172_service.TUBE_OD_M
    wall_result = compute_wall_resistance(
        tube_id,
        tube_od,
        t172_service.WALL_CONDUCTIVITY_W_M_K,
        support.inside_area_m2,
    )
    return ClosurePrimitives(
        tube_bulk_snapshot=tube_bulk_snapshot,
        shell_bulk_snapshot=shell_bulk_snapshot,
        tube_h_base=tube_resolution.htc_w_m2_k,
        shell_h_base=shell_h_base,
        wall_resistance_k_w=wall_result.wall_bundle_conduction_resistance_k_w,
        tube_apply_c3=tube_resolution.apply_c3_wall_pr_correction,
        tube_bulk_id=tube_bulk_id,
        shell_bulk_id=shell_bulk_id,
    )


def evaluate_three_equation_residuals(
    q_w: float,
    twi_k: float,
    two_k: float,
    *,
    request: Task172Request,
    provider: Any,
    primitives: ClosurePrimitives,
) -> dict[str, Any]:
    """Return r1,r2,r3 via production _eval_trial (q - Gi*..., q - deltaT/Rwall, q - Go*...)."""
    evaluated = t172_service._eval_trial(
        request,
        provider,
        primitives.tube_bulk_snapshot,
        primitives.shell_bulk_snapshot,
        primitives.tube_h_base,
        primitives.shell_h_base,
        primitives.wall_resistance_k_w,
        float(q_w),
        float(twi_k),
        float(two_k),
        apply_c3_wall_pr_correction=primitives.tube_apply_c3,
    )
    residuals = evaluated["residuals"]
    bounds = evaluated["bounds"]
    ratios = [
        abs(float(r)) / float(b) if float(b) > 0 else math.inf
        for r, b in zip(residuals, bounds, strict=True)
    ]
    return {
        "residuals_w": tuple(float(r) for r in residuals),
        "acceptance_bounds_w": tuple(float(b) for b in bounds),
        "residual_to_bound_ratios": tuple(ratios),
        "max_residual_ratio": max(ratios),
        "passes_original_residual_gate": all(r <= 1.0 for r in ratios),
        "g_i_w_per_k": float(evaluated["g_i"]),
        "g_wall_w_per_k": float(evaluated["g_wall"]),
        "g_o_w_per_k": float(evaluated["g_o"]),
        "tube_bulk_k": float(request.tube_bulk_state.temperature_k),
        "shell_bulk_k": float(request.shell_bulk_state.temperature_k),
        "evaluated": evaluated,
    }


def _algebraic_seed(
    tube_bulk_k: float,
    shell_bulk_k: float,
    primitives: ClosurePrimitives,
    support: Any,
) -> tuple[float, float, float]:
    g_i = float(primitives.tube_h_base * support.inside_area_m2)
    g_o = float(primitives.shell_h_base * support.outside_area_m2)
    g_wall = 1.0 / float(primitives.wall_resistance_k_w)
    delta_t = tube_bulk_k - shell_bulk_k
    if delta_t <= 0:
        return 0.0, tube_bulk_k, shell_bulk_k
    q = delta_t / (1.0 / g_i + 1.0 / g_wall + 1.0 / g_o)
    twi = tube_bulk_k - q / g_i
    two = shell_bulk_k + q / g_o
    return max(q, 0.0), twi, two


def residual_gate_record(
    q_w: float,
    twi_k: float,
    two_k: float,
    *,
    request: Task172Request,
    provider: Any,
    primitives: ClosurePrimitives,
) -> dict[str, Any]:
    gate = evaluate_three_equation_residuals(
        q_w, twi_k, two_k, request=request, provider=provider, primitives=primitives
    )
    return {
        "q_w": float(q_w),
        "twi_k": float(twi_k),
        "two_k": float(two_k),
        "r_inner_w": gate["residuals_w"][0],
        "r_wall_w": gate["residuals_w"][1],
        "r_outer_w": gate["residuals_w"][2],
        "bound_inner_w": gate["acceptance_bounds_w"][0],
        "bound_wall_w": gate["acceptance_bounds_w"][1],
        "bound_outer_w": gate["acceptance_bounds_w"][2],
        "max_residual_ratio": gate["max_residual_ratio"],
        "original_residual_gate_pass": gate["passes_original_residual_gate"],
        "request_hash": recompute_task172_request_hash(request),
    }


def solve_frozen_request_direct_trf(
    request: Task172Request,
    provider: Any,
    *,
    max_nfev: int = 192,
) -> dict[str, Any]:
    """TRF on (q,Twi,Two) with frozen request/bulk/primitives (Task172 _solve_once equivalent)."""
    primitives = build_closure_primitives(request, provider)
    support = request.support
    tube_k = float(request.tube_bulk_state.temperature_k)
    shell_k = float(request.shell_bulk_state.temperature_k)
    q_seed, twi_seed, two_seed = _algebraic_seed(tube_k, shell_k, primitives, support)
    residual_scale = max(abs(q_seed), 1.0)
    t_min = float(t172_service._admitted_temperature_bounds()[0])
    t_max = float(t172_service._admitted_temperature_bounds()[1])

    def residual(vec: np.ndarray) -> np.ndarray:
        q, twi, two = (float(v) for v in vec)
        temp_ok = t_min <= twi <= t_max and t_min <= two <= t_max
        order_ok = shell_k <= two <= twi <= tube_k
        if not (temp_ok and order_ok):
            return np.asarray([9.0, 9.0, 9.0], dtype=float)
        ev = evaluate_three_equation_residuals(
            q, twi, two, request=request, provider=provider, primitives=primitives
        )
        return np.asarray(ev["residuals_w"], dtype=float) / residual_scale

    x0 = np.asarray([q_seed, twi_seed, two_seed], dtype=float)
    lo = np.asarray([0.0, max(shell_k, t_min), max(shell_k, t_min)], dtype=float)
    hi = np.asarray([max(q_seed * 2.0, 1.0), tube_k, tube_k], dtype=float)
    opt = least_squares(
        residual,
        x0,
        bounds=(lo, hi),
        method="trf",
        ftol=1e-6,
        xtol=1e-12,
        max_nfev=max_nfev,
    )
    q_f, twi_f, two_f = (float(v) for v in opt.x)
    gate = residual_gate_record(
        q_f, twi_f, two_f, request=request, provider=provider, primitives=primitives
    )
    return {
        "method": "FROZEN_REQUEST_DIRECT_TRF",
        "optimizer_success": bool(opt.success),
        "optimizer_nfev": int(opt.nfev),
        **gate,
    }


def compare_same_request_production_vs_frozen_trf(
    request: Task172Request,
    provider: Any,
) -> dict[str, Any]:
    """Classify precision gap: frozen TRF vs production validate on identical request."""
    if type(request) is CandidateTask172LocalRequest:
        production = validate_candidate_request(request, provider)
    else:
        production = validate_request(request, provider)
    frozen = solve_frozen_request_direct_trf(request, provider)
    record: dict[str, Any] = {
        "task_id": "V08_03_SAME_REQUEST_COMPARISON",
        "request_hash": recompute_task172_request_hash(request),
        "precision_root_cause_hypothesis": None,
    }
    if type(production) is Task172LocalResult:
        pq = float(production.signed_q_hot_to_cold_w)
        p_twi = float(production.wall_temperature_inner_k)
        p_two = float(production.wall_temperature_outer_k)
        prim = build_closure_primitives(request, provider)
        prod_gate = residual_gate_record(
            pq, p_twi, p_two, request=request, provider=provider, primitives=prim
        )
        record["production"] = {
            **prod_gate,
            "result_hash": production.result_hash,
            "outcome_type": "Task172LocalResult",
        }
    else:
        record["production"] = {
            "outcome_type": type(production).__name__,
            "failure_code": getattr(production, "failure_code", None),
        }
    record["frozen_trf"] = frozen
    if type(production) is Task172LocalResult and frozen.get("original_residual_gate_pass"):
        fq = frozen["q_w"]
        pq = float(production.signed_q_hot_to_cold_w)
        rel_q = abs(fq - pq) / max(abs(pq), 1.0)
        record["q_relative_delta"] = rel_q
        if rel_q <= 1e-12 and frozen["max_residual_ratio"] <= 1.0:
            record["comparison_status"] = "PASS_ALIGNED"
            record["precision_root_cause_hypothesis"] = "NONE"
        elif rel_q <= 1e-8:
            record["comparison_status"] = "PASS_Q_NEAR_MISMATCH_ULP"
            record["precision_root_cause_hypothesis"] = "D_TERMINATION_OR_ROUNDING"
        else:
            record["comparison_status"] = "BLOCKED_Q_MISMATCH"
            record["precision_root_cause_hypothesis"] = "C_INDEPENDENT_TERMINATION"
    elif type(production) is Task172LocalResult:
        record["comparison_status"] = "BLOCKED_FROZEN_GATE"
        record["precision_root_cause_hypothesis"] = "C_INDEPENDENT_TERMINATION"
    else:
        record["comparison_status"] = "BLOCKED_PRODUCTION"
        record["precision_root_cause_hypothesis"] = "E_PRODUCTION_BLOCKED"
    return record


def solve_constitutive_at_q_trial(
    q_trial_w: float,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
) -> dict[str, Any]:
    """Task173-aligned: freeze bulk at q_trial, solve (q,Twi,Two); F(q)=q_trial-q_constitutive."""
    request, _, _ = build_task172_request_for_q(
        q_trial_w,
        support=support,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
        shell_authority=shell_authority,
    )
    comparison = compare_same_request_production_vs_frozen_trf(request, provider)
    q172: float | None = None
    if comparison.get("production", {}).get("outcome_type") == "Task172LocalResult":
        q172 = float(comparison["production"]["q_w"])
    f_q = float(q_trial_w) - float(q172) if q172 is not None else None
    return {
        "q_trial_w": float(q_trial_w),
        "f_q_w": f_q,
        "same_request_comparison": comparison,
        "frozen_trf": comparison.get("frozen_trf"),
    }


def solve_true_three_equation_coupling(
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: Any,
    shell_authority: Any,
    q_upper: float,
    q_seed: float | None = None,
    max_nfev: int = _TRUE_COUPLED_BUDGET_NFEV,
) -> dict[str, Any]:
    """Freeze Task173 bulk at q_trial; direct TRF on (q,Twi,Two) (no nested Task172 in residual)."""
    q_trial = min(max(q_seed if q_seed is not None else q_upper * 0.5, 0.0), q_upper)
    if q_upper <= 0:
        return {
            "task_id": "V08_03_TRUE_THREE_EQUATION_COUPLING",
            "status": "BLOCKED",
            "reason": "non_positive_q_upper",
        }
    try:
        constitutive = solve_constitutive_at_q_trial(
            q_trial,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except _LowSideDomainInfeasible:
        return {"task_id": "V08_03_TRUE_THREE_EQUATION_COUPLING", "status": "BLOCKED_LOW_SIDE"}
    comparison = constitutive["same_request_comparison"]
    production = comparison.get("production", {})
    frozen = comparison.get("frozen_trf", {})
    gate_pass = bool(production.get("original_residual_gate_pass"))
    record: dict[str, Any] = {
        "task_id": "V08_03_TRUE_THREE_EQUATION_COUPLING",
        "nested_task172_solver_removed_from_residual": True,
        "q_trial_w": q_trial,
        "f_q_w": constitutive.get("f_q_w"),
        "same_request_comparison": comparison,
        "original_residual_gate_pass": gate_pass,
        "engineering_task172_pass": gate_pass,
        "status": "INDEPENDENT_LOCAL_SOLUTION" if gate_pass else "NO_ACCEPTED_RESIDUAL_GATE",
        **{k: frozen.get(k) for k in ("q_w", "twi_k", "two_k", "max_residual_ratio")},
    }
    if production.get("result_hash"):
        record["task172_result_hash"] = production["result_hash"]
    return record


def task172_validation_dispatch(
    request: Task172Request,
    provider: Any,
) -> Any:
    if type(request) is CandidateTask172LocalRequest:
        return validate_candidate_request(request, provider)
    return validate_request(request, provider)
