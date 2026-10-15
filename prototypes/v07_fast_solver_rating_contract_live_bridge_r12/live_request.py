"""Live numerical solve entry for experimental Candidate Rating (n=1 sample)."""

from __future__ import annotations

import time
from decimal import Decimal
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_outer_boundary_r3.outer_boundary import solve_fast_outer_boundary
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    EXPERIMENTAL_RATING_AUTHORITY_ID,
    ExecutionMode,
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_cell_closure,
    verify_energy_balance,
    verify_task174_binding,
)

LIVE_OUTER_AUTHORITY_ID = "V07-FAST-SOLVER-OUTER-BOUNDARY-R3"


class ExperimentalLiveMeshOutcome:
    """Lightweight live mesh outcome (not a full rating ladder)."""

    def __init__(
        self,
        *,
        status: Literal["TERMINAL_ACCEPTED", "BLOCKED", "TIMEOUT"],
        execution_mode: ExecutionMode,
        candidate_id: str,
        rating_request_hash: str,
        mesh_n: int,
        shooting_enthalpy_j_kg: str | None,
        mesh_result_hash: str | None,
        terminal_boundary_residual_k: Decimal | None,
        worker_wall_seconds: float,
        outer_boundary_authority_id: str,
        blocked_code: str | None = None,
        blocked_diagnostics: tuple[str, ...] = (),
    ) -> None:
        self.status = status
        self.execution_mode = execution_mode
        self.candidate_id = candidate_id
        self.rating_request_hash = rating_request_hash
        self.mesh_n = mesh_n
        self.shooting_enthalpy_j_kg = shooting_enthalpy_j_kg
        self.mesh_result_hash = mesh_result_hash
        self.terminal_boundary_residual_k = terminal_boundary_residual_k
        self.worker_wall_seconds = worker_wall_seconds
        self.outer_boundary_authority_id = outer_boundary_authority_id
        self.blocked_code = blocked_code
        self.blocked_diagnostics = blocked_diagnostics

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "task173.experimental-live-mesh-outcome.v1",
            "status": self.status,
            "execution_mode": self.execution_mode,
            "experimental_rating_authority_id": EXPERIMENTAL_RATING_AUTHORITY_ID,
            "candidate_id": self.candidate_id,
            "rating_request_hash": self.rating_request_hash,
            "mesh_n": self.mesh_n,
            "shooting_enthalpy_j_kg": self.shooting_enthalpy_j_kg,
            "mesh_result_hash": self.mesh_result_hash,
            "terminal_boundary_residual_k": (
                str(self.terminal_boundary_residual_k)
                if self.terminal_boundary_residual_k is not None
                else None
            ),
            "worker_wall_seconds": self.worker_wall_seconds,
            "outer_boundary_authority_id": self.outer_boundary_authority_id,
            "blocked_code": self.blocked_code,
            "blocked_diagnostics": list(self.blocked_diagnostics),
            "numerical_authority_status": "CANDIDATE",
            "production_integration": False,
        }


def experimental_rate_candidate_request(
    request: CandidateRatingRequest,
    *,
    execution_mode: ExecutionMode = "LIVE_NUMERICAL_SOLVE",
    provider: CoolPropProvider | None = None,
    live_mesh_n: int = 1,
    wall_clock_budget_s: float = 180.0,
) -> ExperimentalLiveMeshOutcome | ExperimentalRatingBlocked:
    if execution_mode != "LIVE_NUMERICAL_SOLVE":
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="UNSUPPORTED_EXECUTION_MODE",
            blocked_diagnostics=(f"mode={execution_mode}",),
            execution_mode=execution_mode,
        )
    if live_mesh_n != 1:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="LIVE_MESH_N_NOT_IN_SCOPE",
            blocked_diagnostics=("R12 only admits live_mesh_n=1",),
            execution_mode=execution_mode,
        )
    try:
        if not verify_task174_binding(request):
            raise ValueError("task174 binding or hash verification failed")
        request_hash = candidate_rating_request_hash(request)
    except (ValueError, TypeError) as exc:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="REQUEST_VALIDATION_FAILED",
            blocked_diagnostics=(str(exc),),
            execution_mode=execution_mode,
        )

    context = t173._candidate_context(request)
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    active_provider = provider or CoolPropProvider(cache_size=2048)
    deadline = time.perf_counter() + wall_clock_budget_s
    try:
        outer = solve_fast_outer_boundary(
            live_mesh_n,
            active_provider,
            context.shell_authority,
            deadline_monotonic=deadline,
        )
        run = outer.mesh_run
        terminal_k: Decimal | None = None
        mesh_hash: str | None = None
        if run is not None:
            terminal_k = run.observables.terminal_boundary_residual_k
            mesh_hash = run.mesh_result_hash

        if outer.status == "TIMEOUT":
            return ExperimentalLiveMeshOutcome(
                status="TIMEOUT",
                execution_mode=execution_mode,
                candidate_id=request.candidate_id,
                rating_request_hash=request_hash,
                mesh_n=live_mesh_n,
                shooting_enthalpy_j_kg=outer.shooting_enthalpy_j_kg,
                mesh_result_hash=mesh_hash,
                terminal_boundary_residual_k=terminal_k,
                worker_wall_seconds=outer.stats.worker_wall_seconds,
                outer_boundary_authority_id=LIVE_OUTER_AUTHORITY_ID,
                blocked_code=outer.blocked_code,
                blocked_diagnostics=outer.blocked_diagnostics,
            )
        if outer.status != "TERMINAL_ACCEPTED" or run is None:
            return ExperimentalLiveMeshOutcome(
                status="BLOCKED",
                execution_mode=execution_mode,
                candidate_id=request.candidate_id,
                rating_request_hash=request_hash,
                mesh_n=live_mesh_n,
                shooting_enthalpy_j_kg=outer.shooting_enthalpy_j_kg,
                mesh_result_hash=mesh_hash,
                terminal_boundary_residual_k=terminal_k,
                worker_wall_seconds=outer.stats.worker_wall_seconds,
                outer_boundary_authority_id=LIVE_OUTER_AUTHORITY_ID,
                blocked_code=outer.blocked_code or "LIVE_OUTER_BOUNDARY_NOT_ACCEPTED",
                blocked_diagnostics=outer.blocked_diagnostics,
            )
        if not verify_cell_closure(run) or not verify_energy_balance(run):
            return ExperimentalLiveMeshOutcome(
                status="BLOCKED",
                execution_mode=execution_mode,
                candidate_id=request.candidate_id,
                rating_request_hash=request_hash,
                mesh_n=live_mesh_n,
                shooting_enthalpy_j_kg=outer.shooting_enthalpy_j_kg,
                mesh_result_hash=mesh_hash,
                terminal_boundary_residual_k=terminal_k,
                worker_wall_seconds=outer.stats.worker_wall_seconds,
                outer_boundary_authority_id=LIVE_OUTER_AUTHORITY_ID,
                blocked_code="LIVE_CELL_OR_ENERGY_VERIFICATION_FAILED",
            )
        return ExperimentalLiveMeshOutcome(
            status="TERMINAL_ACCEPTED",
            execution_mode=execution_mode,
            candidate_id=request.candidate_id,
            rating_request_hash=request_hash,
            mesh_n=live_mesh_n,
            shooting_enthalpy_j_kg=outer.shooting_enthalpy_j_kg,
            mesh_result_hash=mesh_hash,
            terminal_boundary_residual_k=terminal_k,
            worker_wall_seconds=outer.stats.worker_wall_seconds,
            outer_boundary_authority_id=LIVE_OUTER_AUTHORITY_ID,
        )
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
