"""Safeguarded coarse-to-fine outer boundary bracketing (experimental authority)."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from decimal import Decimal, localcontext
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MAX_J_KG,
    H_MIN_J_KG,
    MAX_OUTER_BISECTION_ITERATIONS,
    TERMINAL_TOLERANCE_K,
)
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    FastOuterBoundaryResult,
    FastOuterBoundaryStats,
    OuterBudgetExceeded,
    _classify_fast_trial,
)

OUTER_CONTINUATION_AUTHORITY_ID = "V07-FAST-SOLVER-OUTER-CONTINUATION-N16-R7"
def _solve_bisection_on_bracket(
    trial_at: Callable[[Decimal, int], t173._OuterTrial],
    h_low: Decimal,
    h_high: Decimal,
    high_run: t173._MeshRun,
    *,
    first_mid_hint: Decimal | None = None,
) -> t173._MeshRun:
    if t173._terminal_tolerance_pass(high_run):
        return high_run

    iterations = 0
    used_hint = False
    while iterations < MAX_OUTER_BISECTION_ITERATIONS:
        with localcontext() as context:
            context.prec = 80
            if (
                not used_hint
                and first_mid_hint is not None
                and h_low < first_mid_hint < h_high
            ):
                h_mid = first_mid_hint
                used_hint = True
            else:
                h_mid = (h_low + h_high) / Decimal(2)
        if h_mid in (h_low, h_high) or float(h_mid) in (float(h_low), float(h_high)):
            residual_k = high_run.observables.terminal_boundary_residual_k
            temp_floor = Decimal(str(math.ulp(float(residual_k + t173.T_MIN_K))))
            if t173._terminal_tolerance_pass(high_run):
                return high_run
            if (
                high_run.observables.terminal_boundary_residual_k - temp_floor
                > TERMINAL_TOLERANCE_K
            ):
                raise t173._Stage3Failure(
                    "BLOCKED_OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                    f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
                )
            raise t173._Stage3Failure(
                "PRECISION_FLOOR_UNRESOLVED",
                "OUTER_BOUNDARY_PRECISION_FLOOR_REACHED",
                f"terminal_residual_k={high_run.observables.terminal_boundary_residual_k}",
            )
        iterations += 1
        trial = trial_at(h_mid, iterations)
        if trial.classification == "HARD_BLOCKER":
            raise t173._Stage3Failure(*trial.diagnostics)
        if trial.classification == "LOW_SIDE_DOMAIN_INFEASIBLE":
            h_low = h_mid
            continue
        if trial.classification != "VALID_TRAJECTORY" or trial.mesh_run is None:
            raise t173._Stage3Failure("BLOCKED_OUTER_TRIAL_CLASSIFICATION_INVALID")
        if (
            trial.mesh_run.observables.terminal_boundary_residual_j_kg < 0
            or trial.mesh_run.observables.terminal_boundary_residual_k < 0
        ):
            raise t173._Stage3Failure("BLOCKED_VALID_TRAJECTORY_NEGATIVE_RESIDUAL")
        h_high = h_mid
        high_run = trial.mesh_run
        if t173._terminal_tolerance_pass(high_run):
            return high_run
    raise t173._Stage3Failure(
        "BLOCKED_OUTER_BOUNDARY_RESOURCE_EXHAUSTION",
        f"maximum_iterations={MAX_OUTER_BISECTION_ITERATIONS}",
    )


def solve_continuation_outer_boundary(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    enthalpy_hints_j_kg: tuple[str, ...] = (),
    deadline_monotonic: float | None = None,
    on_trial_receipt: Callable[..., None] | None = None,
) -> FastOuterBoundaryResult:
    """Production safeguards + optional coarse-to-fine bracket tightening."""
    stats = FastOuterBoundaryStats(authority_id=OUTER_CONTINUATION_AUTHORITY_ID)

    def trial_at(enthalpy: Decimal, iteration: int) -> t173._OuterTrial:
        if deadline_monotonic is not None and time.perf_counter() >= deadline_monotonic:
            raise OuterBudgetExceeded("outer_boundary_deadline")
        trial = _classify_fast_trial(
            subdivisions,
            enthalpy,
            provider,
            shell_authority,
            iteration,
            stats,
            on_trial_receipt=on_trial_receipt,
        )
        stats.bisection_iterations = max(stats.bisection_iterations, iteration)
        return trial

    t0 = time.perf_counter()
    try:
        low_trial = trial_at(H_MIN_J_KG, 0)
        if low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
            if low_trial.classification == "HARD_BLOCKER":
                raise t173._Stage3Failure(*low_trial.diagnostics)
            raise t173._Stage3Failure("BLOCKED_OUTER_LOW_ENDPOINT_NOT_INFEASIBLE")
        high_trial = trial_at(H_MAX_J_KG, 0)
        if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
            if high_trial.classification == "HARD_BLOCKER":
                raise t173._Stage3Failure(*high_trial.diagnostics)
            raise t173._Stage3Failure("BLOCKED_OUTER_FEASIBLE_UPPER_ENDPOINT_NOT_FOUND")
        high_run = high_trial.mesh_run
        if (
            high_run.observables.terminal_boundary_residual_j_kg < 0
            or high_run.observables.terminal_boundary_residual_k < 0
        ):
            raise t173._Stage3Failure("BLOCKED_OUTER_HIGH_ENDPOINT_RESIDUAL_NEGATIVE")

        h_low = H_MIN_J_KG
        h_high = H_MAX_J_KG
        first_hint: Decimal | None = None
        if enthalpy_hints_j_kg:
            first_hint = Decimal(enthalpy_hints_j_kg[-1])
        run = _solve_bisection_on_bracket(
            trial_at,
            h_low,
            h_high,
            high_run,
            first_mid_hint=first_hint,
        )
    except OuterBudgetExceeded:
        stats.worker_wall_seconds = time.perf_counter() - t0
        return FastOuterBoundaryResult(
            status="TIMEOUT",
            shooting_enthalpy_j_kg=stats.last_accepted_shooting_enthalpy_j_kg,
            mesh_run=stats.last_accepted_mesh_run,
            mesh_stats_last=None,
            stats=stats,
            blocked_code="OUTER_BOUNDARY_WALL_CLOCK_EXCEEDED",
            blocked_diagnostics=("partial_last_valid_trial_preserved",),
        )
    except t173._Stage3Failure as exc:
        code = exc.code if exc.args else "BLOCKED_STAGE3_FAILURE"
        status: Literal[
            "TERMINAL_ACCEPTED",
            "BLOCKED",
            "TIMEOUT",
            "PRECISION_FLOOR_UNRESOLVED",
            "RESOURCE_EXHAUSTION",
        ]
        if code == "PRECISION_FLOOR_UNRESOLVED":
            status = "PRECISION_FLOOR_UNRESOLVED"
        elif code == "BLOCKED_OUTER_BOUNDARY_RESOURCE_EXHAUSTION":
            status = "RESOURCE_EXHAUSTION"
        else:
            status = "BLOCKED"
        stats.worker_wall_seconds = time.perf_counter() - t0
        return FastOuterBoundaryResult(
            status=status,
            shooting_enthalpy_j_kg=stats.last_accepted_shooting_enthalpy_j_kg,
            mesh_run=stats.last_accepted_mesh_run,
            mesh_stats_last=None,
            stats=stats,
            blocked_code=code,
            blocked_diagnostics=exc.diagnostics,
        )

    stats.worker_wall_seconds = time.perf_counter() - t0
    accepted = t173._terminal_tolerance_pass(run)
    return FastOuterBoundaryResult(
        status="TERMINAL_ACCEPTED" if accepted else "BLOCKED",
        shooting_enthalpy_j_kg=str(run.shooting_enthalpy),
        mesh_run=run,
        mesh_stats_last=None,
        stats=stats,
        blocked_code=None if accepted else "BLOCKED_COUNTERCURRENT_TERMINAL_BOUNDARY_TOLERANCE",
    )
