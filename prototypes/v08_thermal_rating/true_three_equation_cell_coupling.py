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
from hexagent.exchangers.shell_tube.task172_local_runtime.coupled_closure_kernel import (
    _temperatures_from_u,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalRequest,
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
    """Independent least_squares on (q,u1,u2). Residual path does NOT call Task172 _solve."""
    record: dict[str, Any] = {
        "task_id": "V08_03_TRUE_THREE_EQUATION_COUPLING",
        "nested_task172_solver_removed_from_residual": True,
    }
    if q_upper <= 0:
        record["status"] = "BLOCKED"
        record["reason"] = "non_positive_q_upper"
        return record

    def residual(vec: np.ndarray) -> np.ndarray:
        q = float(vec[0])
        u1 = float(vec[1])
        u2 = float(vec[2])
        if q < 0.0 or q > q_upper or not (0.0 <= u1 <= 1.0 and 0.0 <= u2 <= 1.0):
            return np.asarray([10.0, 10.0, 10.0], dtype=float)
        try:
            request, _, _ = build_task172_request_for_q(
                q,
                support=support,
                tube_upstream=tube_upstream,
                shell_physical_left=shell_physical_left,
                provider=provider,
                shell_authority=shell_authority,
            )
        except _LowSideDomainInfeasible:
            return np.asarray([8.0, 8.0, 8.0], dtype=float)
        tube_bulk_k = float(request.tube_bulk_state.temperature_k)
        shell_bulk_k = float(request.shell_bulk_state.temperature_k)
        if tube_bulk_k <= shell_bulk_k:
            return np.asarray([9.0, 9.0, 9.0], dtype=float)
        try:
            twi, two = _temperatures_from_u(
                u1, u2, tube_bulk_k=tube_bulk_k, shell_bulk_k=shell_bulk_k
            )
        except ValueError:
            return np.asarray([9.0, 9.0, 9.0], dtype=float)
        primitives = build_closure_primitives(request, provider)
        ev = evaluate_three_equation_residuals(
            q, twi, two, request=request, provider=provider, primitives=primitives
        )
        scale = max(abs(q), 1.0)
        return np.asarray(ev["residuals_w"], dtype=float) / scale

    q0 = min(max(q_seed if q_seed is not None else q_upper * 0.5, 0.0), q_upper)
    try:
        req0, _, _ = build_task172_request_for_q(
            q0,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        prim0 = build_closure_primitives(req0, provider)
        tube_k = float(req0.tube_bulk_state.temperature_k)
        shell_k = float(req0.shell_bulk_state.temperature_k)
        q_alg, twi_alg, two_alg = _algebraic_seed(tube_k, shell_k, prim0, support)
        u1_seed = (two_alg - shell_k) / max(tube_k - shell_k, 1e-9)
        u2_seed = (
            (twi_alg - two_alg) / max(tube_k - two_alg, 1e-9) if twi_alg > two_alg else 0.35
        )
        q_init = min(max(q_alg if math.isfinite(q_alg) else q0, 0.0), q_upper)
        x0 = np.asarray(
            [q_init, min(max(u1_seed, 0.05), 0.95), min(max(u2_seed, 0.05), 0.95)],
            dtype=float,
        )
    except (_LowSideDomainInfeasible, ValueError):
        x0 = np.asarray([min(q0, q_upper), 0.35, 0.35], dtype=float)

    opt = least_squares(
        residual,
        x0,
        bounds=([0.0, 0.0, 0.0], [q_upper, 1.0, 1.0]),
        method="trf",
        ftol=1e-10,
        xtol=1e-12,
        max_nfev=max_nfev,
    )
    q_final = float(opt.x[0])
    u1_f, u2_f = float(opt.x[1]), float(opt.x[2])
    try:
        request_f, tube_local, shell_local = build_task172_request_for_q(
            q_final,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
    except _LowSideDomainInfeasible:
        record.update(
            {
                "status": "BLOCKED_LOW_SIDE",
                "optimizer_success": bool(opt.success),
                "optimizer_nfev": int(opt.nfev),
                "q_final_w": q_final,
            }
        )
        return record

    tube_bulk_k = float(request_f.tube_bulk_state.temperature_k)
    shell_bulk_k = float(request_f.shell_bulk_state.temperature_k)
    twi_f, two_f = _temperatures_from_u(
        u1_f, u2_f, tube_bulk_k=tube_bulk_k, shell_bulk_k=shell_bulk_k
    )
    prim_f = build_closure_primitives(request_f, provider)
    gate = evaluate_three_equation_residuals(
        q_final, twi_f, two_f, request=request_f, provider=provider, primitives=prim_f
    )
    record.update(
        {
            "optimizer_success": bool(opt.success),
            "optimizer_nfev": int(opt.nfev),
            "optimizer_cost": float(opt.cost),
            "q_w": q_final,
            "twi_k": twi_f,
            "two_k": two_f,
            "tube_bulk_k": tube_bulk_k,
            "shell_bulk_k": shell_bulk_k,
            "residuals_w": gate["residuals_w"],
            "acceptance_bounds_w": gate["acceptance_bounds_w"],
            "residual_to_bound_ratios": gate["residual_to_bound_ratios"],
            "max_residual_ratio": gate["max_residual_ratio"],
            "original_residual_gate_pass": gate["passes_original_residual_gate"],
            "task172_request_hash": recompute_task172_request_hash(request_f),
        }
    )
    if gate["passes_original_residual_gate"]:
        record["status"] = "INDEPENDENT_LOCAL_SOLUTION"
    else:
        record["status"] = "NO_ACCEPTED_RESIDUAL_GATE"

    nested_outcome: Any = None
    if type(request_f) is CandidateTask172LocalRequest:
        nested_outcome = validate_candidate_request(request_f, provider)
    else:
        nested_outcome = validate_request(request_f, provider)
    record["nested_task172_replay_for_evidence_only"] = type(nested_outcome).__name__
    if hasattr(nested_outcome, "signed_q_hot_to_cold_w"):
        record["nested_signed_q_w"] = str(nested_outcome.signed_q_hot_to_cold_w)
    elif hasattr(nested_outcome, "failure_code"):
        record["nested_failure_code"] = nested_outcome.failure_code
    record["engineering_task172_pass"] = False
    record["tube_local_enthalpy_j_kg"] = str(tube_local.native.enthalpy_j_kg)
    record["shell_local_enthalpy_j_kg"] = str(shell_local.native.enthalpy_j_kg)
    return record


def task172_validation_dispatch(
    request: Task172Request,
    provider: Any,
) -> Any:
    if type(request) is CandidateTask172LocalRequest:
        return validate_candidate_request(request, provider)
    return validate_request(request, provider)
