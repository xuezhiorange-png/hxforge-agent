"""Coupled (q, Twi, Two) cell closure — one NL solve per cell instead of bracket × Task172."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal, localcontext
from typing import Any

import numpy as np
from scipy.optimize import least_squares

from hexagent.exchangers.shell_tube.task172_local_runtime import service as t172
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalRequest,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import PropertyProvider

FAST_CELL_AUTHORITY_ID = "V07-FAST-SOLVER-COUPLED-CELL-R1"
_CALLBACK_CAP = 32


@dataclass
class CoupledCellStats:
    trial_invocations: int = 0
    eval_trial_calls: int = 0
    least_squares_nfev: int = 0
    residual_callback_count: int = 0
    fallback_to_production_cell_root: bool = False
    solver_status: str = ""
    converged_q_w: float | None = None


def _d(value: Decimal | float | int) -> Decimal:
    return t173._d(value)


def _local_states_for_q(
    q_w: float,
    *,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: PropertyProvider,
) -> tuple[Any, Any, Any, Any]:
    """Return tube_local, shell_local, tube_downstream, shell_next (or reuse for q=0)."""
    q = _d(q_w)
    if q == Decimal(0):
        tube_downstream = t173._reuse_authority_valid_thermo_state(tube_upstream)
        tube_local = tube_downstream
        shell_next = t173._reuse_authority_valid_thermo_state(shell_physical_left)
        shell_local = shell_next
        return tube_local, shell_local, tube_downstream, shell_next
    with localcontext() as context:
        context.prec = 70
        tube_downstream_h = _d(tube_upstream.native.enthalpy_j_kg) - q / t173.TUBE_MASS_FLOW_KG_S
        shell_next_h = _d(shell_physical_left.native.enthalpy_j_kg) - q / t173.SHELL_MASS_FLOW_KG_S
        tube_mid_h = (_d(tube_upstream.native.enthalpy_j_kg) + tube_downstream_h) / Decimal(2)
        shell_mid_h = (_d(shell_physical_left.native.enthalpy_j_kg) + shell_next_h) / Decimal(2)
    if tube_downstream_h < t173.H_MIN_J_KG or tube_downstream_h > t173.H_MAX_J_KG:
        raise t173._Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            "tube downstream face enthalpy outside admitted domain",
            str(tube_downstream_h),
        )
    if shell_next_h < t173.H_MIN_J_KG:
        raise t173._LowSideDomainInfeasible
    if shell_next_h > t173.H_MAX_J_KG:
        raise t173._Stage3Failure(
            "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT",
            "shell next face enthalpy outside admitted domain",
            str(shell_next_h),
        )
    tube_downstream = t173._state_from_enthalpy(provider, tube_downstream_h)
    shell_next = t173._state_from_enthalpy(provider, shell_next_h, shell_search_state=True)
    tube_local = t173._state_from_enthalpy(provider, tube_mid_h)
    shell_local = t173._state_from_enthalpy(provider, shell_mid_h)
    return tube_local, shell_local, tube_downstream, shell_next


def _task172_preamble(
    request: CandidateTask172LocalRequest | Task172LocalRequest,
    provider: PropertyProvider,
) -> tuple[Any, ...]:
    """Mirror production _solve_once property / HTC preamble."""
    support = request.support
    tube_bulk_snapshot, _, _ = t172._snapshot(
        provider,
        request,
        "TUBE",
        f"{support.tube_cell_id}:CELL_MEAN",
        request.tube_bulk_state.temperature_k,
        request.tube_bulk_state.pressure_pa,
    )
    shell_bulk_snapshot, _, _ = t172._snapshot(
        provider,
        request,
        "SHELL",
        f"{support.shell_cell_id}:CELL_MEAN",
        request.shell_bulk_state.temperature_k,
        request.shell_bulk_state.pressure_pa,
    )
    tube_h_base, _, _, _, _ = t172._tube_base_htc(
        request, tube_bulk_snapshot, request.tube_mass_flow_kg_s
    )
    shell_h_base, _, _, _ = t172._shell_base_htc(
        request, shell_bulk_snapshot, request.shell_mass_flow_kg_s
    )
    if type(request) is CandidateTask172LocalRequest:
        tube_inner_diameter = request.candidate_binding.task025_result.hydraulic_diameter_m
        bell_geometry = request.candidate_binding.task166_result.bell_geometry
        if bell_geometry is None:
            raise ValueError("candidate TASK166 Bell geometry is missing")
        tube_outer_diameter = bell_geometry.tube_outer_diameter_m
    else:
        tube_inner_diameter = t172.TUBE_ID_M
        tube_outer_diameter = t172.TUBE_OD_M
    wall_resistance_result = t172.compute_wall_resistance(
        tube_inner_diameter,
        tube_outer_diameter,
        t172.WALL_CONDUCTIVITY_W_M_K,
        support.inside_area_m2,
    )
    wall_resistance = wall_resistance_result.wall_bundle_conduction_resistance_k_w
    return (
        tube_bulk_snapshot,
        shell_bulk_snapshot,
        tube_h_base,
        shell_h_base,
        wall_resistance,
    )


def solve_coupled_cell(
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: PropertyProvider,
    shell_authority: Any,
    stats: CoupledCellStats | None = None,
) -> Any:
    """Return production ``_CellEvaluation`` using coupled constitutive + enthalpy closure."""
    cell_stats = stats if stats is not None else CoupledCellStats()
    try:
        return _solve_coupled_cell_inner(
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
            cell_stats=cell_stats,
        )
    except (t173._Stage3Failure, t173._LowSideDomainInfeasible, t173._Task172NumericalHole):
        cell_stats.fallback_to_production_cell_root = True
        return t173._solve_cell(
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )


def _solve_coupled_cell_inner(
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: PropertyProvider,
    shell_authority: Any,
    cell_stats: CoupledCellStats,
) -> Any:
    delta_t = float(
        Decimal(str(tube_upstream.native.temperature_k))
        - Decimal(str(shell_physical_left.native.temperature_k))
    )
    tube_local_seed, shell_local_seed, _, _ = _local_states_for_q(
        0.0,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
    )
    request_seed = t173._task172_request(
        support, tube_local_seed, shell_local_seed, shell_authority
    )
    (
        _tb,
        _sb,
        tube_h_base,
        shell_h_base,
        wall_resistance,
    ) = _task172_preamble(request_seed, provider)
    tube_g = float(tube_h_base * support.inside_area_m2)
    shell_g = float(shell_h_base * support.outside_area_m2)
    if delta_t == 0.0:
        evaluation = t173._cell_evaluation(
            0.0,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=shell_authority,
        )
        cell_stats.converged_q_w = 0.0
        cell_stats.solver_status = "ZERO_DELTA_T_BRANCH"
        return evaluation
    q_seed = delta_t / (1.0 / tube_g + float(wall_resistance) + 1.0 / shell_g)
    wall_inner_seed = float(tube_upstream.native.temperature_k) - q_seed / tube_g
    wall_outer_seed = float(shell_physical_left.native.temperature_k) + q_seed / shell_g
    if not all(math.isfinite(v) for v in (q_seed, wall_inner_seed, wall_outer_seed)):
        raise t173._Stage3Failure("BLOCKED_INITIALIZATION_FAILURE", "coupled.seed")

    callback_count = 0

    def residual(values: np.ndarray) -> np.ndarray:
        nonlocal callback_count
        callback_count += 1
        cell_stats.residual_callback_count = callback_count
        if callback_count > _CALLBACK_CAP:
            raise t173._Stage3Failure("BLOCKED_SOLVER_RESOURCE_EXHAUSTION", "coupled.callback_cap")
        q, twi, two = (float(v) for v in values)
        cell_stats.trial_invocations += 1
        tube_local, shell_local, _, _ = _local_states_for_q(
            q,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
        )
        request = t173._task172_request(support, tube_local, shell_local, shell_authority)
        t173._preflight_task172_trial(
            q,
            support=support,
            tube_local=tube_local,
            shell_local=shell_local,
            shell_authority=shell_authority,
            request=request,
        )
        (
            tube_bulk_snapshot,
            shell_bulk_snapshot,
            tube_h,
            shell_h,
            wall_r,
        ) = _task172_preamble(request, provider)
        cell_stats.eval_trial_calls += 1
        evaluated = t172._eval_trial(
            request,
            provider,
            tube_bulk_snapshot,
            shell_bulk_snapshot,
            tube_h,
            shell_h,
            wall_r,
            q,
            twi,
            two,
        )
        return np.asarray(evaluated["residuals"], dtype=float) / abs(q_seed)

    try:
        solver = least_squares(
            residual,
            np.asarray([q_seed, wall_inner_seed, wall_outer_seed], dtype=float),
            method="trf",
            loss="linear",
            ftol=1e-6,
            xtol=1e-12,
            gtol=1e-12,
            jac="2-point",
            diff_step=1e-5,
            x_scale=[abs(q_seed), abs(delta_t), abs(delta_t)],
            max_nfev=8,
            bounds=(
                np.asarray([-np.inf, float(t172._T_MIN), float(t172._T_MIN)], dtype=float),
                np.asarray([np.inf, float(t172._T_MAX), float(t172._T_MAX)], dtype=float),
            ),
            tr_solver="exact",
            f_scale=1.0,
        )
    except Exception as exc:
        raise t173._Stage3Failure("BLOCKED_COUPLED_SOLVER_FAILURE", str(exc)) from exc

    cell_stats.least_squares_nfev = int(solver.nfev)
    cell_stats.solver_status = f"COUPLED_TRF_STATUS_{solver.status}"
    if not solver.success:
        raise t173._Stage3Failure("BLOCKED_COUPLED_NONCONVERGENCE", cell_stats.solver_status)
    q_star = float(solver.x[0])
    cell_stats.converged_q_w = q_star
    evaluation = t173._cell_evaluation(
        q_star,
        support=support,
        tube_upstream=tube_upstream,
        shell_physical_left=shell_physical_left,
        provider=provider,
        shell_authority=shell_authority,
    )
    residual_w = _d(q_star) - evaluation.task172_result.signed_q_hot_to_cold_w
    if abs(residual_w) > Decimal("1e-6"):
        raise t173._Stage3Failure(
            "BLOCKED_COUPLED_CELL_ROOT_MISMATCH",
            f"residual_w={residual_w}",
        )
    return evaluation
