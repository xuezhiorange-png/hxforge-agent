"""Second-candidate ladder continuation using frozen snapshot (no snapshot regeneration)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21.general_live_result_hash import (
    GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.bounded_workers import (
    run_bounded_compare,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.continuation_engine import (
    LiveContinuationOutcome,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.live_worker import (
    run_live_mesh_worker_from_snapshot,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)
from prototypes.v07_fast_solver_live_rating_ladder_r13.stage_persistence import (
    write_stage_receipt,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)


def _blocked(code: str, *diag: str) -> ExperimentalRatingBlocked:
    return ExperimentalRatingBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
        execution_mode="LIVE_NUMERICAL_SOLVE",
        experimental_rating_authority_id=GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    )


def continue_second_candidate_ladder(
    root: Path,
    *,
    output_stage_dir: Path,
    live_mesh_levels: tuple[int, ...],
    mesh_budgets_s: dict[int, float],
    total_budget_s: float,
    rehydrate_budget_s: float = 120.0,
    compare_budget_s: float = 120.0,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    scsa.verify_n4_timeout_receipt_preserved(root)
    frozen = scsa.admit_frozen_second_candidate_snapshot(root)
    request_hash = frozen.rating_request_hash
    candidate_id = frozen.request.candidate_id
    snapshot_path = root / scsa.SNAPSHOT_REL

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s
    stages: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    artifacts: list[dict[str, str]] = []
    rolling = RollingMeshState()

    def _remaining() -> float:
        return max(0.0, deadline - time.perf_counter())

    for pin in scsa.SECOND_CANDIDATE_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(root, pin)
        stages.append(receipt)
        rolling.record_mesh_accepted(pin.mesh_n)
        if len(stages) >= 2:
            outcome = _compare_pair(
                root,
                snapshot_path,
                stages[-2],
                stages[-1],
                request_hash,
                candidate_id,
                rolling,
                comparisons,
                artifacts,
                output_stage_dir,
                rehydrate_budget_s,
                compare_budget_s,
                _remaining(),
                wall_t0,
            )
            if outcome is not None:
                return outcome

    for mesh_n in live_mesh_levels:
        if _remaining() <= 0:
            return _timeout_outcome(
                request_hash,
                candidate_id,
                stages,
                comparisons,
                artifacts,
                rolling,
                wall_t0,
            )
        budget = min(mesh_budgets_s.get(mesh_n, 450.0), _remaining())
        receipt = run_live_mesh_worker_from_snapshot(
            snapshot_path,
            snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
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
        artifacts.append(
            write_stage_receipt(output_stage_dir, mesh_n, receipt, repo_root=root)
        )
        if receipt.get("worker_status") == "TIMEOUT":
            return LiveContinuationOutcome(
                status="TIMEOUT",
                rating_request_hash=request_hash,
                candidate_id=candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code"),
                ladder_continuation_status=rolling.ladder_status,
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
                request_snapshot_rel_path=scsa.SNAPSHOT_REL,
                request_snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return LiveContinuationOutcome(
                status="BLOCKED",
                rating_request_hash=request_hash,
                candidate_id=candidate_id,
                mesh_stages=tuple(stages),
                mesh_comparisons=tuple(comparisons),
                stage_artifacts=tuple(artifacts),
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
                ladder_continuation_status=rolling.ladder_status,
                total_wall_seconds=time.perf_counter() - wall_t0,
                request_snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
                request_snapshot_rel_path=scsa.SNAPSHOT_REL,
                request_snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
            )
        rolling.record_mesh_accepted(mesh_n)
        if len(stages) >= 2:
            outcome = _compare_pair(
                root,
                snapshot_path,
                stages[-2],
                stages[-1],
                request_hash,
                candidate_id,
                rolling,
                comparisons,
                artifacts,
                output_stage_dir,
                rehydrate_budget_s,
                compare_budget_s,
                _remaining(),
                wall_t0,
            )
            if outcome is not None:
                return outcome

    return LiveContinuationOutcome(
        status="LIVE_RATING_IN_PROGRESS",
        rating_request_hash=request_hash,
        candidate_id=candidate_id,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=tuple(artifacts),
        ladder_continuation_status=rolling.ladder_status,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
        request_snapshot_rel_path=scsa.SNAPSHOT_REL,
        request_snapshot_file_sha256=frozen.snapshot_file_sha256,
        orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
    )


def _timeout_outcome(
    request_hash: str,
    candidate_id: str,
    stages: list,
    comparisons: list,
    artifacts: list,
    rolling: RollingMeshState,
    wall_t0: float,
) -> LiveContinuationOutcome:
    rolling.budget_exhausted()
    return LiveContinuationOutcome(
        status="TIMEOUT",
        rating_request_hash=request_hash,
        candidate_id=candidate_id,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=tuple(artifacts),
        blocked_code=rolling.blocked_code or "TOTAL_BUDGET_EXCEEDED",
        ladder_continuation_status=rolling.ladder_status,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
        request_snapshot_rel_path=scsa.SNAPSHOT_REL,
        orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
    )


def _compare_pair(
    root: Path,
    snapshot_path: Path,
    coarse_receipt: dict[str, Any],
    fine_receipt: dict[str, Any],
    request_hash: str,
    candidate_id: str,
    rolling: RollingMeshState,
    comparisons: list[dict[str, Any]],
    artifacts: list[dict[str, str]],
    output_stage_dir: Path,
    rehydrate_budget_s: float,
    compare_budget_s: float,
    remaining: float,
    wall_t0: float,
) -> LiveContinuationOutcome | None:
    from prototypes.v07_fast_solver_live_ladder_continuation_r14.mesh_sequence import (
        validate_adjacent_mesh_pair,
    )

    coarse_n = int(coarse_receipt["mesh_n"])
    fine_n = int(fine_receipt["mesh_n"])
    worker = run_bounded_compare(
        snapshot_path,
        coarse={
            "mesh_n": coarse_n,
            "shooting_enthalpy_j_kg": coarse_receipt["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(coarse_receipt.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": coarse_receipt.get("mesh_result_hash"),
            "terminal_tolerance_pass": coarse_receipt.get("terminal_tolerance_pass"),
            "cell_closure_pass": coarse_receipt.get("cell_closure_pass"),
            "energy_balance_pass": coarse_receipt.get("energy_balance_pass"),
        },
        fine={
            "mesh_n": fine_n,
            "shooting_enthalpy_j_kg": fine_receipt["shooting_enthalpy_for_rehydrate"],
            "outer_iterations": int(fine_receipt.get("outer_iterations_for_rehydrate", 0)),
            "expected_mesh_hash": fine_receipt.get("mesh_result_hash"),
            "terminal_tolerance_pass": fine_receipt.get("terminal_tolerance_pass"),
            "cell_closure_pass": fine_receipt.get("cell_closure_pass"),
            "energy_balance_pass": fine_receipt.get("energy_balance_pass"),
        },
        expected_request_hash=request_hash,
        expected_candidate_id=candidate_id,
        budget_s=min(compare_budget_s, remaining),
    )
    if worker.get("status") == "TIMEOUT":
        return _timeout_outcome(
            request_hash,
            candidate_id,
            [],
            comparisons,
            artifacts,
            rolling,
            wall_t0,
        )
    if worker.get("status") != "OK":
        return LiveContinuationOutcome(
            status="BLOCKED",
            rating_request_hash=request_hash,
            candidate_id=candidate_id,
            blocked_code=worker.get("blocked_code") or "COMPARE_WORKER_FAILED",
            blocked_diagnostics=tuple(worker.get("blocked_diagnostics") or ()),
            total_wall_seconds=time.perf_counter() - wall_t0,
            request_snapshot_rel_path=scsa.SNAPSHOT_REL,
            orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
        )
    validate_adjacent_mesh_pair(coarse_n, fine_n)
    cmp_payload = worker["comparison"]
    comparisons.append(cmp_payload)
    rolling.record_comparison(cmp_payload)
    if rolling.after_comparison_recorded(fine_n):
        return LiveContinuationOutcome(
            status="BLOCKED",
            rating_request_hash=request_hash,
            candidate_id=candidate_id,
            mesh_comparisons=tuple(comparisons),
            blocked_code=rolling.blocked_code,
            blocked_diagnostics=rolling.blocked_diagnostics,
            ladder_continuation_status=rolling.ladder_status,
            total_wall_seconds=time.perf_counter() - wall_t0,
            request_snapshot_rel_path=scsa.SNAPSHOT_REL,
            orchestrator_authority_id="V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B",
        )
    return None
