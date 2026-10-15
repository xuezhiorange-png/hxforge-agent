"""Live multi-mesh experimental rating orchestrator."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.live_worker import (
    rehydrate_mesh_run_for_compare,
    run_live_mesh_worker,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.request_snapshot import (
    verify_request_identity,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import (
    write_stage_receipt,
)
from prototypes.v07_fast_solver_n4_mesh_convergence_r5.mesh_replay import (
    compare_mesh_pair,
    comparison_payload,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    EXPERIMENTAL_RATING_AUTHORITY_ID,
    ExperimentalRatingBlocked,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.verification import (
    verify_task174_binding,
)

LiveRatingStatus = Literal[
    "LIVE_RATING_IN_PROGRESS",
    "MESH_TERMINAL_ACCEPTED",
    "MESH_COMPARISON_PASS",
    "MESH_COMPARISON_FAIL",
    "MESH_CANDIDATE_IDENTIFIED",
    "HEADROOM_PASS",
    "LIVE_RATING_EXPERIMENTAL_COMPLETE",
    "BLOCKED",
    "TIMEOUT",
]

LIVE_RATING_ORCHESTRATOR_ID = "V07-FAST-SOLVER-LIVE-RATING-LADDER-R13"


@dataclass(frozen=True)
class LiveRatingOrchestratorOutcome:
    status: LiveRatingStatus
    rating_request_hash: str
    candidate_id: str
    numerical_authority_status: Literal["CANDIDATE"] = "CANDIDATE"
    production_integration: bool = False
    experimental_rating_authority_id: str = EXPERIMENTAL_RATING_AUTHORITY_ID
    mesh_stages: tuple[dict[str, Any], ...] = ()
    mesh_comparisons: tuple[dict[str, Any], ...] = ()
    stage_artifacts: tuple[dict[str, str], ...] = ()
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()
    total_wall_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "task173.experimental-live-rating-orchestrator-outcome.v1",
            "status": self.status,
            "rating_request_hash": self.rating_request_hash,
            "candidate_id": self.candidate_id,
            "numerical_authority_status": self.numerical_authority_status,
            "production_integration": self.production_integration,
            "experimental_rating_authority_id": self.experimental_rating_authority_id,
            "orchestrator_authority_id": LIVE_RATING_ORCHESTRATOR_ID,
            "mesh_stages": list(self.mesh_stages),
            "mesh_comparisons": list(self.mesh_comparisons),
            "stage_artifacts": list(self.stage_artifacts),
            "blocked_code": self.blocked_code,
            "blocked_diagnostics": list(self.blocked_diagnostics),
            "total_wall_seconds": self.total_wall_seconds,
        }


def _validate_live_request(request: CandidateRatingRequest) -> str:
    if not verify_task174_binding(request):
        raise ValueError("task174 binding failed")
    if request.task171_result.status != "VALIDATED":
        raise ValueError("task171 not VALIDATED")
    return candidate_rating_request_hash(request)


def experimental_rate_candidate_live(
    request: CandidateRatingRequest,
    *,
    mesh_levels: tuple[int, ...] = (1, 2, 4, 8, 16, 32, 64),
    headroom_n: int | None = None,
    stage_dir: Path | None = None,
    mesh_budgets_s: dict[int, float] | None = None,
    total_budget_s: float = 540.0,
) -> LiveRatingOrchestratorOutcome | ExperimentalRatingBlocked:
    try:
        request_hash = _validate_live_request(request)
        verify_request_identity(request)
    except ValueError as exc:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="LIVE_REQUEST_AUTHORITY_GATE_FAILED",
            blocked_diagnostics=(str(exc),),
            execution_mode="LIVE_NUMERICAL_SOLVE",
        )

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s
    budgets = mesh_budgets_s or {}
    stages: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    comparisons: list[dict[str, Any]] = []
    runs_for_compare: list[tuple[int, Any]] = []

    overall: LiveRatingStatus = "LIVE_RATING_IN_PROGRESS"

    for mesh_n in mesh_levels:
        if time.perf_counter() >= deadline:
            return LiveRatingOrchestratorOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code="TOTAL_BUDGET_EXCEEDED",
                blocked_diagnostics=(f"before_mesh_n={mesh_n}",),
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        budget = budgets.get(mesh_n, 180.0)
        receipt = run_live_mesh_worker(request, mesh_n, min(budget, deadline - time.perf_counter()))
        receipt["stage_status"] = (
            "MESH_TERMINAL_ACCEPTED"
            if receipt.get("worker_status") == "TERMINAL_ACCEPTED"
            and receipt.get("terminal_tolerance_pass")
            else receipt.get("worker_status", "BLOCKED")
        )
        stages.append(receipt)
        if stage_dir is not None:
            artifacts.append(write_stage_receipt(stage_dir, mesh_n, receipt))

        if receipt.get("worker_status") == "TIMEOUT":
            return LiveRatingOrchestratorOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code"),
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return LiveRatingOrchestratorOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        shooting = receipt.get("shooting_enthalpy_for_rehydrate")
        if shooting is None:
            return LiveRatingOrchestratorOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                blocked_code="MISSING_SHOOTING_ENTHALPY",
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        outer_iters = int(receipt.get("outer_iterations_for_rehydrate", 0))
        run = rehydrate_mesh_run_for_compare(request, shooting, mesh_n, outer_iters)
        if run.mesh_result_hash != receipt.get("mesh_result_hash"):
            return LiveRatingOrchestratorOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                blocked_code="MESH_HASH_REHYDRATE_MISMATCH",
                blocked_diagnostics=(
                    f"live={receipt.get('mesh_result_hash')}",
                    f"rehydrate={run.mesh_result_hash}",
                ),
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        runs_for_compare.append((mesh_n, run))
        if len(runs_for_compare) >= 2:
            coarse = runs_for_compare[-2][1]
            fine = runs_for_compare[-1][1]
            cmp_payload = comparison_payload(compare_mesh_pair(coarse, fine))
            comparisons.append(cmp_payload)
            if cmp_payload.get("overall_status") == "PASS":
                overall = "MESH_COMPARISON_PASS"
            else:
                overall = "MESH_COMPARISON_FAIL"
                return LiveRatingOrchestratorOutcome(
                    status=overall,
                    rating_request_hash=request_hash,
                    candidate_id=request.candidate_id,
                    mesh_stages=tuple(stages),
                    mesh_comparisons=tuple(comparisons),
                    stage_artifacts=tuple(artifacts),
                    blocked_code="MESH_COMPARISON_FAILED",
                    total_wall_seconds=time.perf_counter() - wall_t0,
                )

    # Full ladder completion (not claimed in R13 partial runs)
    if headroom_n is not None and mesh_levels and mesh_levels[-1] < headroom_n:
        overall = "LIVE_RATING_IN_PROGRESS"
    elif (
        len(mesh_levels) >= 2
        and comparisons
        and all(c.get("overall_status") == "PASS" for c in comparisons)
        and headroom_n is not None
        and mesh_levels[-1] >= headroom_n
    ):
        overall = "LIVE_RATING_EXPERIMENTAL_COMPLETE"
    elif comparisons:
        overall = "MESH_COMPARISON_PASS" if overall == "MESH_COMPARISON_PASS" else overall
    else:
        overall = "LIVE_RATING_IN_PROGRESS"

    return LiveRatingOrchestratorOutcome(
        status=overall,
        rating_request_hash=request_hash,
        candidate_id=request.candidate_id,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=tuple(artifacts),
        total_wall_seconds=time.perf_counter() - wall_t0,
    )
