"""Experimental outer boundary: production bisection + R2 fast mesh trials."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    TERMINAL_TOLERANCE_K,
)
from hexagent.properties.base import PropertyProvider
from hexagent.properties.coolprop_provider import CoolPropProvider

from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory

OUTER_BOUNDARY_AUTHORITY_ID = "V07-FAST-SOLVER-OUTER-BOUNDARY-R3"


@dataclass
class OuterTrialReceipt:
    trial_index: int
    shooting_enthalpy_j_kg: str
    classification: str
    wall_seconds: float
    mesh_march_seconds: float
    terminal_residual_k: str | None
    terminal_residual_j_kg: str | None
    experimental_mesh_result_hash: str | None
    experimental_task172_calls: int | None
    experimental_eval_trial_calls: int | None
    coupled_fallback_count: int | None
    failure_code: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trial_index": self.trial_index,
            "shooting_enthalpy_j_kg": self.shooting_enthalpy_j_kg,
            "classification": self.classification,
            "wall_seconds": self.wall_seconds,
            "mesh_march_seconds": self.mesh_march_seconds,
            "terminal_residual_k": self.terminal_residual_k,
            "terminal_residual_j_kg": self.terminal_residual_j_kg,
            "experimental_mesh_result_hash": self.experimental_mesh_result_hash,
            "experimental_task172_calls": self.experimental_task172_calls,
            "experimental_eval_trial_calls": self.experimental_eval_trial_calls,
            "coupled_fallback_count": self.coupled_fallback_count,
            "failure_code": self.failure_code,
        }


@dataclass
class FastOuterBoundaryStats:
    authority_id: str = OUTER_BOUNDARY_AUTHORITY_ID
    outer_trial_count: int = 0
    mesh_march_count: int = 0
    total_eval_trial_calls: int = 0
    experimental_total_production_task172_calls: int = 0
    total_wall_seconds: float = 0.0
    trial_receipts: list[OuterTrialReceipt] = field(default_factory=list)
    bisection_iterations: int = 0


@dataclass
class FastOuterBoundaryResult:
    status: Literal[
        "TERMINAL_ACCEPTED",
        "BLOCKED",
        "TIMEOUT",
        "PRECISION_FLOOR_UNRESOLVED",
        "RESOURCE_EXHAUSTION",
    ]
    shooting_enthalpy_j_kg: str | None
    mesh_run: Any | None
    mesh_stats_last: Any | None
    stats: FastOuterBoundaryStats
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()


def _classify_fast_trial(
    subdivisions: int,
    enthalpy_j_kg: Decimal,
    provider: PropertyProvider,
    shell_authority: Any,
    iteration: int,
    boundary_stats: FastOuterBoundaryStats,
) -> t173._OuterTrial:
    t0 = time.perf_counter()
    boundary_stats.outer_trial_count += 1
    trial_index = boundary_stats.outer_trial_count
    receipt = OuterTrialReceipt(
        trial_index=trial_index,
        shooting_enthalpy_j_kg=str(enthalpy_j_kg),
        classification="PENDING",
        wall_seconds=0.0,
        mesh_march_seconds=0.0,
        terminal_residual_k=None,
        terminal_residual_j_kg=None,
        experimental_mesh_result_hash=None,
        experimental_task172_calls=None,
        experimental_eval_trial_calls=None,
        coupled_fallback_count=None,
    )
    try:
        run, mesh_stats = fast_valid_trajectory(
            subdivisions,
            enthalpy_j_kg,
            provider,
            shell_authority,
            iteration,
            cell_solver="r2",
        )
        boundary_stats.mesh_march_count += 1
        boundary_stats.total_eval_trial_calls += mesh_stats.total_eval_trial_calls
        boundary_stats.experimental_total_production_task172_calls += (
            mesh_stats.experimental_total_production_task172_calls
        )
        receipt.mesh_march_seconds = mesh_stats.wall_seconds
        obs = run.observables
        receipt.terminal_residual_k = str(obs.terminal_boundary_residual_k)
        receipt.terminal_residual_j_kg = str(obs.terminal_boundary_residual_j_kg)
        receipt.experimental_mesh_result_hash = run.mesh_result_hash
        receipt.experimental_task172_calls = mesh_stats.experimental_total_production_task172_calls
        receipt.experimental_eval_trial_calls = mesh_stats.total_eval_trial_calls
        receipt.coupled_fallback_count = mesh_stats.coupled_fallback_count
        if (
            obs.terminal_boundary_residual_j_kg < 0
            or obs.terminal_boundary_residual_k < 0
        ):
            receipt.classification = "HARD_BLOCKER"
            receipt.failure_code = "BLOCKED_NEGATIVE_TERMINAL_RESIDUAL"
            trial = t173._OuterTrial(
                "HARD_BLOCKER",
                enthalpy_j_kg,
                diagnostics=("BLOCKED_NEGATIVE_TERMINAL_RESIDUAL",),
            )
        else:
            receipt.classification = "VALID_TRAJECTORY"
            trial = t173._OuterTrial("VALID_TRAJECTORY", enthalpy_j_kg, mesh_run=run)
        return trial
    except t173._LowSideDomainInfeasible:
        receipt.classification = "LOW_SIDE_DOMAIN_INFEASIBLE"
        return t173._OuterTrial("LOW_SIDE_DOMAIN_INFEASIBLE", enthalpy_j_kg)
    except t173._Stage3Failure as exc:
        receipt.classification = "HARD_BLOCKER"
        receipt.failure_code = exc.code if exc.args else "BLOCKED_STAGE3_FAILURE"
        return t173._OuterTrial(
            "HARD_BLOCKER",
            enthalpy_j_kg,
            diagnostics=(receipt.failure_code, *exc.diagnostics),
        )
    except Exception as exc:
        receipt.classification = "HARD_BLOCKER"
        receipt.failure_code = f"UNEXPECTED_{type(exc).__name__}"
        return t173._OuterTrial(
            "HARD_BLOCKER",
            enthalpy_j_kg,
            diagnostics=(receipt.failure_code, str(exc)),
        )
    finally:
        receipt.wall_seconds = time.perf_counter() - t0
        boundary_stats.trial_receipts.append(receipt)
        boundary_stats.total_wall_seconds += receipt.wall_seconds


def solve_fast_outer_boundary(
    subdivisions: int,
    provider: PropertyProvider,
    shell_authority: Any,
) -> FastOuterBoundaryResult:
    """Run production outer bisection with R2 mesh trials (experimental authority)."""
    stats = FastOuterBoundaryStats()

    def trial_at(enthalpy: Decimal, iteration: int) -> t173._OuterTrial:
        trial = _classify_fast_trial(
            subdivisions,
            enthalpy,
            provider,
            shell_authority,
            iteration,
            stats,
        )
        stats.bisection_iterations = max(stats.bisection_iterations, iteration)
        return trial

    t0 = time.perf_counter()
    try:
        run = t173._solve_outer_boundary_from_trial(trial_at)
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
        stats.total_wall_seconds += time.perf_counter() - t0
        return FastOuterBoundaryResult(
            status=status,
            shooting_enthalpy_j_kg=None,
            mesh_run=None,
            mesh_stats_last=last_mesh_stats,
            stats=stats,
            blocked_code=code,
            blocked_diagnostics=exc.diagnostics,
        )

    stats.total_wall_seconds += time.perf_counter() - t0
    accepted = t173._terminal_tolerance_pass(run)
    return FastOuterBoundaryResult(
        status="TERMINAL_ACCEPTED" if accepted else "BLOCKED",
        shooting_enthalpy_j_kg=str(run.shooting_enthalpy),
        mesh_run=run,
        mesh_stats_last=last_mesh_stats,
        stats=stats,
        blocked_code=None if accepted else "BLOCKED_COUNTERCURRENT_TERMINAL_BOUNDARY_TOLERANCE",
    )


def observables_summary(run: Any) -> dict[str, str]:
    obs = run.observables
    return {
        "duty_w": str(obs.total_duty_w),
        "tube_outlet_temperature_k": str(obs.tube_outlet_temperature_k),
        "shell_outlet_temperature_k": str(obs.shell_outlet_temperature_k),
        "energy_balance_residual_w": str(obs.energy_balance_residual_w),
        "terminal_boundary_residual_k": str(obs.terminal_boundary_residual_k),
        "terminal_boundary_residual_j_kg": str(obs.terminal_boundary_residual_j_kg),
        "experimental_mesh_result_hash": run.mesh_result_hash,
        "terminal_tolerance_k": str(TERMINAL_TOLERANCE_K),
        "terminal_tolerance_pass": str(t173._terminal_tolerance_pass(run)),
    }
