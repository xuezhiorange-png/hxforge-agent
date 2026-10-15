"""Live ladder continuation engine (injectable deps for orchestrator regression)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
    candidate_rating_request_hash,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.bounded_workers import (
    run_bounded_compare,
    run_bounded_rehydrate,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.mesh_sequence import (
    validate_adjacent_mesh_pair,
    validate_run_sequence,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.request_snapshot import (
    build_request_snapshot,
    snapshot_filename,
    write_request_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    PriorStagePin,
    admit_prior_stage,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import write_stage_receipt
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
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


@dataclass(frozen=True)
class LiveContinuationOutcome:
    status: LiveRatingStatus
    rating_request_hash: str
    candidate_id: str
    mesh_stages: tuple[dict[str, Any], ...] = ()
    mesh_comparisons: tuple[dict[str, Any], ...] = ()
    stage_artifacts: tuple[dict[str, str], ...] = ()
    ladder_continuation_status: str = "LIVE_RATING_IN_PROGRESS"
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()
    total_wall_seconds: float = 0.0
    request_snapshot_sha256: str | None = None
    request_snapshot_rel_path: str | None = None
    request_snapshot_file_sha256: str | None = None
    orchestrator_authority_id: str = "V07-FAST-SOLVER-LIVE-N8-CONTINUATION-R15"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "task173.experimental-live-rating-continuation-outcome.v1",
            "status": self.status,
            "rating_request_hash": self.rating_request_hash,
            "candidate_id": self.candidate_id,
            "numerical_authority_status": "CANDIDATE",
            "production_integration": False,
            "orchestrator_authority_id": self.orchestrator_authority_id,
            "mesh_stages": list(self.mesh_stages),
            "mesh_comparisons": list(self.mesh_comparisons),
            "stage_artifacts": list(self.stage_artifacts),
            "ladder_continuation_status": self.ladder_continuation_status,
            "blocked_code": self.blocked_code,
            "blocked_diagnostics": list(self.blocked_diagnostics),
            "total_wall_seconds": self.total_wall_seconds,
            "request_snapshot_sha256": self.request_snapshot_sha256,
            "request_snapshot_rel_path": self.request_snapshot_rel_path,
            "request_snapshot_file_sha256": self.request_snapshot_file_sha256,
        }


@dataclass
class LadderContinuationDeps:
    run_live_worker: Callable[..., dict[str, Any]]
    bounded_rehydrate: Callable[..., dict[str, Any]] = run_bounded_rehydrate
    bounded_compare: Callable[..., dict[str, Any]] = run_bounded_compare
    admit_prior: Callable[..., dict[str, Any]] = admit_prior_stage


def _validate_live_request(request: CandidateRatingRequest) -> str:
    if not verify_task174_binding(request):
        raise ValueError("task174 binding failed")
    if request.task171_result.status != "VALIDATED":
        raise ValueError("task171 not VALIDATED")
    return candidate_rating_request_hash(request)


def _outcome_status(rolling: RollingMeshState) -> LiveRatingStatus:
    if rolling.ladder_status == "BLOCKED":
        return "BLOCKED"
    if rolling.ladder_status == "TIMEOUT":
        return "TIMEOUT"
    if rolling.ladder_status == "HEADROOM_PASS":
        return "LIVE_RATING_IN_PROGRESS"
    return "LIVE_RATING_IN_PROGRESS"


def _process_comparison(
    *,
    rolling: RollingMeshState,
    comparisons: list[dict[str, Any]],
    coarse_n: int,
    fine_n: int,
    cmp_payload: dict[str, Any],
) -> tuple[bool, str | None, tuple[str, ...]]:
    validate_adjacent_mesh_pair(coarse_n, fine_n)
    comparisons.append(cmp_payload)
    rolling.record_comparison(cmp_payload)
    if rolling.after_comparison_recorded(fine_n):
        return True, rolling.blocked_code, rolling.blocked_diagnostics
    return False, None, ()


def run_live_ladder_continuation(
    request: CandidateRatingRequest,
    *,
    root: Path,
    source_commit: str,
    snapshot_dir: Path,
    stage_dir: Path | None,
    prior_pins: tuple[PriorStagePin, ...],
    live_mesh_levels: tuple[int, ...],
    mesh_budgets_s: dict[int, float],
    total_budget_s: float,
    rehydrate_budget_s: float,
    compare_budget_s: float,
    deps: LadderContinuationDeps | None = None,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    active_deps = deps or LadderContinuationDeps(
        run_live_worker=__import__(
            "prototypes.v07_fast_solver_live_ladder_continuation_r14.live_worker",
            fromlist=["run_live_mesh_worker_from_snapshot"],
        ).run_live_mesh_worker_from_snapshot
    )
    try:
        request_hash = _validate_live_request(request)
    except ValueError as exc:
        return ExperimentalRatingBlocked(
            status="BLOCKED",
            blocked_code="LIVE_REQUEST_AUTHORITY_GATE_FAILED",
            blocked_diagnostics=(str(exc),),
            execution_mode="LIVE_NUMERICAL_SOLVE",
        )

    ladder_levels = tuple(pin.mesh_n for pin in prior_pins) + live_mesh_levels
    try:
        validate_run_sequence(ladder_levels)
    except ValueError as exc:
        return LiveContinuationOutcome(
            status="BLOCKED",
            rating_request_hash=request_hash,
            candidate_id=request.candidate_id,
            blocked_code="MESH_SEQUENCE_INVALID",
            blocked_diagnostics=(str(exc),),
        )

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s

    snapshot = build_request_snapshot(request, source_commit=source_commit)
    snapshot_path = snapshot_dir / snapshot_filename(request.candidate_id, request_hash)
    file_digest = write_request_snapshot(snapshot_path, snapshot)
    snapshot_sha = snapshot["snapshot_sha256"]
    snapshot_rel = str(snapshot_path.relative_to(root))

    stages: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    comparisons: list[dict[str, Any]] = []
    mesh_chain: list[int] = []
    rolling = RollingMeshState()

    def _remaining() -> float:
        return max(0.0, deadline - time.perf_counter())

    def _rehydrate_stage(receipt: dict[str, Any], mesh_n: int) -> LiveContinuationOutcome | None:
        shooting = receipt.get("shooting_enthalpy_for_rehydrate")
        if shooting is None:
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code="MISSING_SHOOTING_ENTHALPY",
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        budget = min(rehydrate_budget_s, _remaining())
        worker = active_deps.bounded_rehydrate(
            snapshot_path,
            shooting_enthalpy_j_kg=str(shooting),
            mesh_n=mesh_n,
            outer_iterations=int(receipt.get("outer_iterations_for_rehydrate", 0)),
            expected_mesh_hash=receipt.get("mesh_result_hash"),
            rating_request_hash=request_hash,
            budget_s=budget,
        )
        if worker.get("status") == "TIMEOUT":
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=worker.get("blocked_code"),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        if worker.get("status") != "OK":
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=worker.get("blocked_code") or "REHYDRATE_GATE_FAILED",
                blocked_diagnostics=tuple(worker.get("blocked_diagnostics") or ()),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        return None

    def _compare_stages(coarse_receipt: dict[str, Any], fine_receipt: dict[str, Any]) -> Any:
        coarse_n = int(coarse_receipt["mesh_n"])
        fine_n = int(fine_receipt["mesh_n"])
        budget = min(compare_budget_s, _remaining())
        worker = active_deps.bounded_compare(
            snapshot_path,
            coarse={
                "mesh_n": coarse_n,
                "shooting_enthalpy_j_kg": coarse_receipt["shooting_enthalpy_for_rehydrate"],
                "outer_iterations": int(coarse_receipt.get("outer_iterations_for_rehydrate", 0)),
            },
            fine={
                "mesh_n": fine_n,
                "shooting_enthalpy_j_kg": fine_receipt["shooting_enthalpy_for_rehydrate"],
                "outer_iterations": int(fine_receipt.get("outer_iterations_for_rehydrate", 0)),
            },
            budget_s=budget,
        )
        if worker.get("status") == "TIMEOUT":
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=worker.get("blocked_code"),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        if worker.get("status") != "OK":
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=worker.get("blocked_code") or "COMPARE_WORKER_FAILED",
                blocked_diagnostics=tuple(worker.get("blocked_diagnostics") or ()),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        cmp_payload = worker["comparison"]
        blocked, code, diag = _process_comparison(
            rolling=rolling,
            comparisons=comparisons,
            coarse_n=coarse_n,
            fine_n=fine_n,
            cmp_payload=cmp_payload,
        )
        if blocked:
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                ladder_continuation_status=rolling.ladder_status,
                blocked_code=code,
                blocked_diagnostics=diag,
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        return None

    for pin in prior_pins:
        if _remaining() <= 0:
            rolling.budget_exhausted()
            break
        try:
            receipt = active_deps.admit_prior(
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
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                blocked_code=code,
                blocked_diagnostics=(str(exc),),
                total_wall_seconds=time.perf_counter() - wall_t0,
            )
        stages.append(receipt)
        rolling.record_mesh_accepted(pin.mesh_n)
        mesh_chain.append(pin.mesh_n)
        blocked = _rehydrate_stage(receipt, pin.mesh_n)
        if blocked is not None:
            return blocked
        if len(stages) >= 2:
            outcome = _compare_stages(stages[-2], stages[-1])
            if outcome is not None:
                return outcome

    for mesh_n in live_mesh_levels:
        if _remaining() <= 0:
            rolling.budget_exhausted()
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                ladder_continuation_status=rolling.ladder_status,
                blocked_code=rolling.blocked_code or "TOTAL_BUDGET_EXCEEDED",
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        budget = min(mesh_budgets_s.get(mesh_n, 450.0), _remaining())
        receipt = active_deps.run_live_worker(
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
        mesh_chain.append(mesh_n)
        rolling.record_mesh_accepted(mesh_n)
        if stage_dir is not None:
            artifacts.append(
                write_stage_receipt(stage_dir, mesh_n, receipt, repo_root=root)
            )
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
                request_snapshot_file_sha256=file_digest,
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=request.candidate_id,
                mesh_stages=tuple(stages),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=snapshot_sha,
                request_snapshot_rel_path=snapshot_rel,
                request_snapshot_file_sha256=file_digest,
            )
        blocked = _rehydrate_stage(receipt, mesh_n)
        if blocked is not None:
            return blocked
        if len(stages) >= 2:
            outcome = _compare_stages(stages[-2], stages[-1])
            if outcome is not None:
                return outcome

    return LiveContinuationOutcome(
        status=_outcome_status(rolling),
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
        request_snapshot_file_sha256=file_digest,
    )
