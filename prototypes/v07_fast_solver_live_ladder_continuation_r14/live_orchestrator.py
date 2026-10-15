"""R14 live rating continuation: prior stages + rolling mesh + snapshot worker."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.live_worker import (
    rehydrate_mesh_run_for_compare,
    run_live_mesh_worker_from_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.physics_gate import (
    evaluate_live_physics_gate,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    build_request_snapshot,
    write_request_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    DEFAULT_PRIOR_PINS,
    admit_prior_stage,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import write_stage_receipt
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
    "MESH_COMPARISON_FAIL_CONTINUE",
    "MESH_CANDIDATE_IDENTIFIED",
    "HEADROOM_PASS",
    "LIVE_RATING_EXPERIMENTAL_COMPLETE",
    "BLOCKED",
    "TIMEOUT",
]

LIVE_RATING_ORCHESTRATOR_ID = "V07-FAST-SOLVER-LIVE-LADDER-CONTINUATION-R14"


@dataclass(frozen=True)
class LiveContinuationOutcome:
    status: LiveRatingStatus
    rating_request_hash: str
    candidate_id: str
    numerical_authority_status: Literal["CANDIDATE"] = "CANDIDATE"
    production_integration: bool = False
    experimental_rating_authority_id: str = EXPERIMENTAL_RATING_AUTHORITY_ID
    mesh_stages: tuple[dict[str, Any], ...] = ()
    mesh_comparisons: tuple[dict[str, Any], ...] = ()
    stage_artifacts: tuple[dict[str, str], ...] = ()
    ladder_continuation_status: str = "LIVE_RATING_IN_PROGRESS"
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()
    total_wall_seconds: float = 0.0
    request_snapshot_sha256: str | None = None
    request_snapshot_rel_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "task173.experimental-live-rating-continuation-outcome.v1",
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
            "ladder_continuation_status": self.ladder_continuation_status,
            "blocked_code": self.blocked_code,
            "blocked_diagnostics": list(self.blocked_diagnostics),
            "total_wall_seconds": self.total_wall_seconds,
            "request_snapshot_sha256": self.request_snapshot_sha256,
            "request_snapshot_rel_path": self.request_snapshot_rel_path,
        }


def _validate_live_request(request: CandidateRatingRequest) -> str:
    if not verify_task174_binding(request):
        raise ValueError("task174 binding failed")
    if request.task171_result.status != "VALIDATED":
        raise ValueError("task171 not VALIDATED")
    return candidate_rating_request_hash(request)


def _blocked(
    code: str,
    request_hash: str,
    candidate_id: str,
    *,
    diagnostics: tuple[str, ...] = (),
    stages: tuple[dict[str, Any], ...] = (),
    comparisons: tuple[dict[str, Any], ...] = (),
    artifacts: tuple[dict[str, str], ...] = (),
    wall: float = 0.0,
) -> LiveContinuationOutcome:
    return LiveContinuationOutcome(
        status="BLOCKED",
        rating_request_hash=request_hash,
        candidate_id=candidate_id,
        mesh_stages=stages,
        mesh_comparisons=comparisons,
        stage_artifacts=artifacts,
        blocked_code=code,
        blocked_diagnostics=diagnostics,
        total_wall_seconds=wall,
    )


def experimental_rate_candidate_live_continuation(
    request: CandidateRatingRequest,
    *,
    root: Path,
    source_commit: str,
    snapshot_dir: Path,
    stage_dir: Path | None = None,
    live_mesh_levels: tuple[int, ...] = (4,),
    prior_pins: tuple[Any, ...] = DEFAULT_PRIOR_PINS,
    mesh_budgets_s: dict[int, float] | None = None,
    total_budget_s: float = 600.0,
    rehydrate_budget_s: float = 120.0,
    compare_budget_s: float = 60.0,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    try:
        request_hash = _validate_live_request(request)
    except ValueError as exc:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="LIVE_REQUEST_AUTHORITY_GATE_FAILED",
            blocked_diagnostics=(str(exc),),
            execution_mode="LIVE_NUMERICAL_SOLVE",
        )

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s
    budgets = mesh_budgets_s or {4: 450.0}

    snapshot = build_request_snapshot(request, source_commit=source_commit)
    snapshot_path = snapshot_dir / "candidate-b-live-request-snapshot.json"
    write_request_snapshot(snapshot_path, snapshot)
    snapshot_sha = snapshot["snapshot_sha256"]
    snapshot_rel = str(snapshot_path.relative_to(root))

    stages: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    comparisons: list[dict[str, Any]] = []
    runs_for_compare: list[tuple[int, Any]] = []
    rolling = RollingMeshState()

    for pin in prior_pins:
        try:
            receipt = admit_prior_stage(
                root,
                pin,
                expected_request_hash=request_hash,
                expected_candidate_id=request.candidate_id,
            )
        except (FileNotFoundError, ValueError) as exc:
            code = (
                "EVIDENCE_HASH_MISMATCH"
                if "EVIDENCE_HASH_MISMATCH" in str(exc)
                else "PRIOR_STAGE_ADMISSION_FAILED"
            )
            return _blocked(
                code,
                request_hash,
                request.candidate_id,
                diagnostics=(str(exc),),
                wall=time.perf_counter() - wall_t0,
            )
        stages.append(receipt)
        rolling.record_mesh_accepted(pin.mesh_n)
        shooting = receipt.get("shooting_enthalpy_for_rehydrate")
        if shooting is None:
            return _blocked(
                "MISSING_SHOOTING_ENTHALPY",
                request_hash,
                request.candidate_id,
                stages=tuple(stages),
                wall=time.perf_counter() - wall_t0,
            )
        outer_iters = int(receipt.get("outer_iterations_for_rehydrate", 0))
        try:
            run = rehydrate_mesh_run_for_compare(
                request,
                shooting,
                pin.mesh_n,
                outer_iters,
                budget_s=rehydrate_budget_s,
            )
        except TimeoutError:
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                blocked_code="MESH_REHYDRATE_TIMEOUT",
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
            )
        ok, gate_code, gate_diag = evaluate_live_physics_gate(
            receipt,
            request,
            run,
            expected_request_hash=request_hash,
        )
        if not ok:
            return _blocked(
                gate_code or "LIVE_PHYSICS_GATE_FAILED",
                request_hash,
                request.candidate_id,
                diagnostics=gate_diag,
                stages=tuple(stages),
                wall=time.perf_counter() - wall_t0,
            )
        runs_for_compare.append((pin.mesh_n, run))
        if len(runs_for_compare) >= 2:
            cmp_t0 = time.perf_counter()
            coarse = runs_for_compare[-2][1]
            fine = runs_for_compare[-1][1]
            cmp_payload = comparison_payload(compare_mesh_pair(coarse, fine))
            if time.perf_counter() - cmp_t0 > compare_budget_s:
                return LiveContinuationOutcome(
                    status="TIMEOUT",
                    rating_request_hash=request_hash,
                    candidate_id=request.candidate_id,
                    mesh_stages=tuple(stages),
                    mesh_comparisons=tuple(comparisons),
                    blocked_code="MESH_COMPARE_BUDGET_EXCEEDED",
                    total_wall_seconds=time.perf_counter() - wall_t0,
                    request_snapshot_sha256=snapshot_sha,
                    request_snapshot_rel_path=snapshot_rel,
                )
            comparisons.append(cmp_payload)
            rolling.record_comparison(cmp_payload)

    for mesh_n in live_mesh_levels:
        if time.perf_counter() >= deadline:
            rolling.budget_exhausted()
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                ladder_continuation_status=rolling.ladder_status,
                blocked_code=rolling.blocked_code,
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
            )
        budget = min(budgets.get(mesh_n, 450.0), deadline - time.perf_counter())
        receipt = run_live_mesh_worker_from_snapshot(
            snapshot_path,
            snapshot_sha256=snapshot_sha,
            rating_request_hash=request_hash,
            mesh_n=mesh_n,
            budget_s=budget,
        )
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
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code"),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return _blocked(
                receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                request_hash,
                request.candidate_id,
                diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
                stages=tuple(stages),
                artifacts=tuple(artifacts),
                wall=time.perf_counter() - wall_t0,
            )
        shooting = receipt.get("shooting_enthalpy_for_rehydrate")
        if shooting is None:
            return _blocked(
                "MISSING_SHOOTING_ENTHALPY",
                request_hash,
                request.candidate_id,
                stages=tuple(stages),
                artifacts=tuple(artifacts),
                wall=time.perf_counter() - wall_t0,
            )
        outer_iters = int(receipt.get("outer_iterations_for_rehydrate", 0))
        try:
            run = rehydrate_mesh_run_for_compare(
                request,
                shooting,
                mesh_n,
                outer_iters,
                budget_s=rehydrate_budget_s,
            )
        except TimeoutError:
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                stage_artifacts=tuple(artifacts),
                blocked_code="MESH_REHYDRATE_TIMEOUT",
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
            )
        ok, gate_code, gate_diag = evaluate_live_physics_gate(
            receipt,
            request,
            run,
            expected_request_hash=request_hash,
        )
        if not ok:
            return _blocked(
                gate_code or "LIVE_PHYSICS_GATE_FAILED",
                request_hash,
                request.candidate_id,
                diagnostics=gate_diag,
                stages=tuple(stages),
                artifacts=tuple(artifacts),
                wall=time.perf_counter() - wall_t0,
            )
        runs_for_compare.append((mesh_n, run))
        rolling.record_mesh_accepted(mesh_n)
        if len(runs_for_compare) >= 2:
            cmp_t0 = time.perf_counter()
            coarse = runs_for_compare[-2][1]
            fine = runs_for_compare[-1][1]
            cmp_payload = comparison_payload(compare_mesh_pair(coarse, fine))
            if time.perf_counter() - cmp_t0 > compare_budget_s:
                return LiveContinuationOutcome(
                    status="TIMEOUT",
                    rating_request_hash=request_hash,
                    candidate_id=request.candidate_id,
                    mesh_stages=tuple(stages),
                    mesh_comparisons=tuple(comparisons),
                    stage_artifacts=tuple(artifacts),
                    blocked_code="MESH_COMPARE_BUDGET_EXCEEDED",
                    total_wall_seconds=time.perf_counter() - wall_t0,
                    request_snapshot_sha256=snapshot_sha,
                    request_snapshot_rel_path=snapshot_rel,
                )
            comparisons.append(cmp_payload)
            rolling.record_comparison(cmp_payload)

    overall: LiveRatingStatus = rolling.ladder_status  # type: ignore[assignment]
    if (
        rolling.ladder_status == "MESH_COMPARISON_FAIL_CONTINUE"
        or rolling.ladder_status in ("MESH_COMPARISON_PASS", "MESH_CANDIDATE_IDENTIFIED")
        or rolling.ladder_status == "HEADROOM_PASS"
    ):
        overall = "LIVE_RATING_IN_PROGRESS"
    elif rolling.ladder_status == "BLOCKED":
        overall = "BLOCKED"
    elif rolling.ladder_status == "TIMEOUT":
        overall = "TIMEOUT"
    else:
        overall = "LIVE_RATING_IN_PROGRESS"

    return LiveContinuationOutcome(
        status=overall,
        rating_request_hash=request_hash,
        candidate_id=request.candidate_id,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=tuple(artifacts),
        ladder_continuation_status=rolling.ladder_status,
        blocked_code=rolling.blocked_code,
        blocked_diagnostics=rolling.blocked_diagnostics,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=snapshot_sha,
        request_snapshot_rel_path=snapshot_rel,
    )
