"""Verified narrow-bracket outer boundary (no full-domain rescan)."""

from __future__ import annotations

import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.base import PropertyProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import (
    FastOuterBoundaryResult,
    FastOuterBoundaryStats,
    OuterBudgetExceeded,
    _classify_fast_trial,
)
from prototypes.v07_fast_solver_outer_continuation_n16_r7.outer_continuation import (
    _solve_bisection_on_bracket,
)

OUTER_VERIFIED_BRACKET_AUTHORITY_ID = "V07-FAST-SOLVER-N16-VERIFIED-BRACKET-R8"
OUTER_N32_CONVERGENCE_AUTHORITY_ID = "V07-FAST-SOLVER-N32-CONVERGENCE-R9"


class BracketRevalidationFailed(Exception):
    """Archived bracket could not be revalidated in the current run."""


def solve_verified_narrow_bracket_outer_boundary(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
    *,
    h_low_j_kg: str,
    h_high_j_kg: str,
    authority_id: str = OUTER_VERIFIED_BRACKET_AUTHORITY_ID,
    deadline_monotonic: float | None = None,
    on_trial_receipt: Callable[..., None] | None = None,
) -> tuple[FastOuterBoundaryResult, dict[str, Any]]:
    stats = FastOuterBoundaryStats(authority_id=authority_id)
    revalidation: dict[str, Any] = {
        "low_endpoint_revalidated": False,
        "high_endpoint_revalidated": False,
        "true_narrow_bracket_used": False,
    }

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

    h_low = Decimal(h_low_j_kg)
    h_high = Decimal(h_high_j_kg)
    if h_low >= h_high:
        raise BracketRevalidationFailed("candidate bracket not ordered")

    t0 = time.perf_counter()
    try:
        low_trial = trial_at(h_low, 0)
        if low_trial.classification == "HARD_BLOCKER":
            code = low_trial.diagnostics[0] if low_trial.diagnostics else "HARD_BLOCKER"
            raise BracketRevalidationFailed(code)
        if low_trial.classification != "LOW_SIDE_DOMAIN_INFEASIBLE":
            raise BracketRevalidationFailed(
                f"low endpoint classification={low_trial.classification}"
            )
        revalidation["low_endpoint_revalidated"] = True

        high_trial = trial_at(h_high, 0)
        if high_trial.classification == "HARD_BLOCKER":
            raise BracketRevalidationFailed(
                high_trial.diagnostics[0] if high_trial.diagnostics else "HARD_BLOCKER"
            )
        if high_trial.classification != "VALID_TRAJECTORY" or high_trial.mesh_run is None:
            raise BracketRevalidationFailed(
                f"high endpoint classification={high_trial.classification}"
            )
        high_run = high_trial.mesh_run
        if (
            high_run.observables.terminal_boundary_residual_j_kg < 0
            or high_run.observables.terminal_boundary_residual_k < 0
        ):
            raise BracketRevalidationFailed("high endpoint negative terminal residual")
        revalidation["high_endpoint_revalidated"] = True
        revalidation["true_narrow_bracket_used"] = True

        run = _solve_bisection_on_bracket(trial_at, h_low, h_high, high_run)
    except OuterBudgetExceeded:
        stats.worker_wall_seconds = time.perf_counter() - t0
        return (
            FastOuterBoundaryResult(
                status="TIMEOUT",
                shooting_enthalpy_j_kg=stats.last_accepted_shooting_enthalpy_j_kg,
                mesh_run=stats.last_accepted_mesh_run,
                mesh_stats_last=None,
                stats=stats,
                blocked_code="OUTER_BOUNDARY_WALL_CLOCK_EXCEEDED",
                blocked_diagnostics=("partial_last_valid_trial_preserved",),
            ),
            revalidation,
        )
    except BracketRevalidationFailed:
        stats.worker_wall_seconds = time.perf_counter() - t0
        return (
            FastOuterBoundaryResult(
                status="BLOCKED",
                shooting_enthalpy_j_kg=stats.last_accepted_shooting_enthalpy_j_kg,
                mesh_run=stats.last_accepted_mesh_run,
                mesh_stats_last=None,
                stats=stats,
                blocked_code="BRACKET_REVALIDATION_FAILED",
                blocked_diagnostics=("no_full_domain_fallback",),
            ),
            revalidation,
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
        return (
            FastOuterBoundaryResult(
                status=status,
                shooting_enthalpy_j_kg=stats.last_accepted_shooting_enthalpy_j_kg,
                mesh_run=stats.last_accepted_mesh_run,
                mesh_stats_last=None,
                stats=stats,
                blocked_code=code,
                blocked_diagnostics=exc.diagnostics,
            ),
            revalidation,
        )

    stats.worker_wall_seconds = time.perf_counter() - t0
    accepted = t173._terminal_tolerance_pass(run)
    return (
        FastOuterBoundaryResult(
            status="TERMINAL_ACCEPTED" if accepted else "BLOCKED",
            shooting_enthalpy_j_kg=str(run.shooting_enthalpy),
            mesh_run=run,
            mesh_stats_last=None,
            stats=stats,
            blocked_code=None if accepted else "BLOCKED_COUNTERCURRENT_TERMINAL_BOUNDARY_TOLERANCE",
        ),
        revalidation,
    )
