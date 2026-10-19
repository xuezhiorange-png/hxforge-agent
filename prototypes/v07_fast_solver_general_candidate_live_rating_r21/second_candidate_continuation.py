"""Second-candidate ladder continuation using frozen snapshot (no snapshot regeneration)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_comparison_persistence as scp,
)
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

ORCHESTRATOR_R21B = "V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21B"
ORCHESTRATOR_R21C = "V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21C"
ORCHESTRATOR_R21D = "V07-FAST-SOLVER-GENERAL-CANDIDATE-CONTINUATION-R21D"


@dataclass(frozen=True)
class ComparePairResult:
    comparison: dict[str, Any]
    headroom_blocked: bool
    blocked_code: str | None
    blocked_diagnostics: tuple[str, ...]


class ComparePairFailure(Exception):
    def __init__(
        self,
        status: str,
        blocked_code: str | None,
        *diagnostics: str,
    ) -> None:
        self.status = status
        self.blocked_code = blocked_code
        self.diagnostics = diagnostics
        super().__init__(blocked_code or status)


def _blocked(code: str, *diag: str) -> ExperimentalRatingBlocked:
    return ExperimentalRatingBlocked(
        status="BLOCKED",
        blocked_code=code,
        blocked_diagnostics=diag,
        execution_mode="LIVE_NUMERICAL_SOLVE",
        experimental_rating_authority_id=GENERAL_LIVE_RATING_R21_AUTHORITY_ID,
    )


def _ledger_outcome(
    *,
    status: str,
    request_hash: str,
    candidate_id: str,
    stages: list[dict[str, Any]],
    comparisons: list[dict[str, Any]],
    artifacts: list[dict[str, str]],
    rolling: RollingMeshState,
    wall_t0: float,
    snapshot_file_sha256: str,
    orchestrator_authority_id: str,
    blocked_code: str | None = None,
    blocked_diagnostics: tuple[str, ...] = (),
) -> LiveContinuationOutcome:
    merged_artifacts = tuple(artifacts)
    return LiveContinuationOutcome(
        status=status,
        rating_request_hash=request_hash,
        candidate_id=candidate_id,
        mesh_stages=tuple(stages),
        mesh_comparisons=tuple(comparisons),
        stage_artifacts=merged_artifacts,
        blocked_code=blocked_code,
        blocked_diagnostics=blocked_diagnostics,
        ladder_continuation_status=rolling.ladder_status,
        total_wall_seconds=time.perf_counter() - wall_t0,
        request_snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
        request_snapshot_rel_path=scsa.SNAPSHOT_REL,
        request_snapshot_file_sha256=snapshot_file_sha256,
        orchestrator_authority_id=orchestrator_authority_id,
    )


def compare_admitted_stage_pair(
    snapshot_path: Path,
    coarse_receipt: dict[str, Any],
    fine_receipt: dict[str, Any],
    request_hash: str,
    candidate_id: str,
    rolling: RollingMeshState,
    *,
    compare_budget_s: float,
) -> ComparePairResult:
    """Bounded compare between two admitted stages."""
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
        budget_s=compare_budget_s,
    )
    if worker.get("status") == "TIMEOUT":
        rolling.budget_exhausted()
        raise ComparePairFailure(
            "TIMEOUT",
            rolling.blocked_code or "COMPARE_WORKER_TIMEOUT",
        )
    if worker.get("status") != "OK":
        raise ComparePairFailure(
            "BLOCKED",
            worker.get("blocked_code") or "COMPARE_WORKER_FAILED",
            *tuple(worker.get("blocked_diagnostics") or ()),
        )
    validate_adjacent_mesh_pair(coarse_n, fine_n)
    cmp_payload = worker["comparison"]
    rolling.record_comparison(cmp_payload)
    headroom_blocked = rolling.after_comparison_recorded(fine_n)
    return ComparePairResult(
        comparison=cmp_payload,
        headroom_blocked=headroom_blocked,
        blocked_code=rolling.blocked_code if headroom_blocked else None,
        blocked_diagnostics=rolling.blocked_diagnostics if headroom_blocked else (),
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
    comparison_artifacts: list[dict[str, str]],
    output_comparison_dir: Path,
    compare_budget_s: float,
    remaining: float,
    wall_t0: float,
    stages: list[dict[str, Any]],
    stage_artifacts: list[dict[str, str]],
    snapshot_file_sha256: str,
    orchestrator_authority_id: str,
) -> LiveContinuationOutcome | None:
    try:
        result = compare_admitted_stage_pair(
            snapshot_path,
            coarse_receipt,
            fine_receipt,
            request_hash,
            candidate_id,
            rolling,
            compare_budget_s=min(compare_budget_s, remaining),
        )
    except ComparePairFailure as exc:
        return _ledger_outcome(
            status=exc.status,
            request_hash=request_hash,
            candidate_id=candidate_id,
            stages=stages,
            comparisons=comparisons,
            artifacts=stage_artifacts,
            rolling=rolling,
            wall_t0=wall_t0,
            snapshot_file_sha256=snapshot_file_sha256,
            orchestrator_authority_id=orchestrator_authority_id,
            blocked_code=exc.blocked_code,
            blocked_diagnostics=exc.diagnostics,
        )
    comparisons.append(result.comparison)
    coarse_n = int(coarse_receipt["mesh_n"])
    fine_n = int(fine_receipt["mesh_n"])
    comparison_artifacts.append(
        scp.write_comparison_receipt(
            output_comparison_dir,
            coarse_n,
            fine_n,
            result.comparison,
            repo_root=root,
        )
    )
    if result.headroom_blocked:
        return _ledger_outcome(
            status="BLOCKED",
            request_hash=request_hash,
            candidate_id=candidate_id,
            stages=stages,
            comparisons=comparisons,
            artifacts=stage_artifacts,
            rolling=rolling,
            wall_t0=wall_t0,
            snapshot_file_sha256=snapshot_file_sha256,
            orchestrator_authority_id=orchestrator_authority_id,
            blocked_code=result.blocked_code,
            blocked_diagnostics=result.blocked_diagnostics,
        )
    return None


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
    output_comparison_dir = output_stage_dir.parent / "comparisons"

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s
    stages: list[dict[str, Any]] = []
    comparisons: list[dict[str, Any]] = []
    stage_artifacts: list[dict[str, str]] = []
    comparison_artifacts: list[dict[str, str]] = []
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
                comparison_artifacts,
                output_comparison_dir,
                compare_budget_s,
                _remaining(),
                wall_t0,
                stages,
                stage_artifacts,
                frozen.snapshot_file_sha256,
                ORCHESTRATOR_R21B,
            )
            if outcome is not None:
                return outcome

    for mesh_n in live_mesh_levels:
        if _remaining() <= 0:
            rolling.budget_exhausted()
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21B,
                blocked_code=rolling.blocked_code or "TOTAL_BUDGET_EXCEEDED",
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
        stage_artifacts.append(
            write_stage_receipt(output_stage_dir, mesh_n, receipt, repo_root=root)
        )
        if receipt.get("worker_status") == "TIMEOUT":
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21B,
                blocked_code=receipt.get("blocked_code"),
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return _ledger_outcome(
                status="BLOCKED",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21B,
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
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
                comparison_artifacts,
                output_comparison_dir,
                compare_budget_s,
                _remaining(),
                wall_t0,
                stages,
                stage_artifacts,
                frozen.snapshot_file_sha256,
                ORCHESTRATOR_R21B,
            )
            if outcome is not None:
                return outcome

    return _ledger_outcome(
        status="LIVE_RATING_IN_PROGRESS",
        request_hash=request_hash,
        candidate_id=candidate_id,
        stages=stages,
        comparisons=comparisons,
        artifacts=stage_artifacts,
        rolling=rolling,
        wall_t0=wall_t0,
        snapshot_file_sha256=frozen.snapshot_file_sha256,
        orchestrator_authority_id=ORCHESTRATOR_R21B,
    )


def continue_second_candidate_cross_task(
    root: Path,
    *,
    output_stage_dir: Path,
    output_comparison_dir: Path,
    live_mesh_levels: tuple[int, ...],
    mesh_budgets_s: dict[int, float],
    total_budget_s: float,
    compare_budget_s: float = 180.0,
    outer_progress_dir: Path | None = None,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    """Resume from admitted n=1..8 evidence; live-solve only requested mesh levels."""
    scsa.verify_n4_timeout_receipt_preserved(root)
    scsa.verify_n16_timeout_receipt_preserved(root)
    frozen = scsa.admit_frozen_second_candidate_snapshot(root)
    request_hash = frozen.rating_request_hash
    candidate_id = frozen.request.candidate_id
    snapshot_path = root / scsa.SNAPSHOT_REL

    stages_by_mesh: dict[int, dict[str, Any]] = {}
    for pin in scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(root, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        if run.mesh_result_hash != receipt["mesh_result_hash"]:
            return _blocked("PRIOR_MESH_REPLAY_HASH_MISMATCH", f"mesh_n={pin.mesh_n}")
        stages_by_mesh[pin.mesh_n] = receipt

    from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
        second_candidate_historical_comparisons as schc,
    )

    comparisons, comparison_artifacts, rolling = schc.rebuild_historical_comparison_chain(
        root,
        stages_by_mesh=stages_by_mesh,
        output_comparison_dir=output_comparison_dir,
        request_hash=request_hash,
        candidate_id=candidate_id,
        snapshot_path=snapshot_path,
        compare_budget_s=compare_budget_s,
    )
    stages = [stages_by_mesh[n] for n in (1, 2, 4, 8)]
    stage_artifacts: list[dict[str, str]] = []

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s

    def _remaining() -> float:
        return max(0.0, deadline - time.perf_counter())

    for mesh_n in live_mesh_levels:
        if _remaining() <= 0:
            rolling.budget_exhausted()
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21C,
                blocked_code=rolling.blocked_code or "TOTAL_BUDGET_EXCEEDED",
            )
        budget = min(mesh_budgets_s.get(mesh_n, 450.0), _remaining())
        progress_path = None
        if outer_progress_dir is not None:
            outer_progress_dir.mkdir(parents=True, exist_ok=True)
            progress_path = outer_progress_dir / f"outer-progress-n{mesh_n}.json"
        receipt = run_live_mesh_worker_from_snapshot(
            snapshot_path,
            snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
            rating_request_hash=request_hash,
            mesh_n=mesh_n,
            budget_s=budget,
            outer_progress_path=progress_path,
        )
        receipt["stage_status"] = (
            "MESH_TERMINAL_ACCEPTED"
            if receipt.get("worker_status") == "TERMINAL_ACCEPTED"
            and receipt.get("terminal_tolerance_pass")
            else receipt.get("worker_status", "BLOCKED")
        )
        stages.append(receipt)
        stage_artifacts.append(
            write_stage_receipt(output_stage_dir, mesh_n, receipt, repo_root=root)
        )
        if receipt.get("worker_status") == "TIMEOUT":
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21C,
                blocked_code=receipt.get("blocked_code"),
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return _ledger_outcome(
                status="BLOCKED",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21C,
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
            )
        rolling.record_mesh_accepted(mesh_n)
        outcome = _compare_pair(
            root,
            snapshot_path,
            stages[-2],
            stages[-1],
            request_hash,
            candidate_id,
            rolling,
            comparisons,
            comparison_artifacts,
            output_comparison_dir,
            compare_budget_s,
            _remaining(),
            wall_t0,
            stages,
            stage_artifacts,
            frozen.snapshot_file_sha256,
            ORCHESTRATOR_R21C,
        )
        if outcome is not None:
            return outcome

    return _ledger_outcome(
        status="LIVE_RATING_IN_PROGRESS",
        request_hash=request_hash,
        candidate_id=candidate_id,
        stages=stages,
        comparisons=comparisons,
        artifacts=stage_artifacts,
        rolling=rolling,
        wall_t0=wall_t0,
        snapshot_file_sha256=frozen.snapshot_file_sha256,
        orchestrator_authority_id=ORCHESTRATOR_R21C,
    )


def continue_second_candidate_r21d(
    root: Path,
    *,
    output_stage_dir: Path,
    output_comparison_dir: Path,
    live_mesh_levels: tuple[int, ...],
    mesh_budgets_s: dict[int, float],
    total_budget_s: float,
    compare_budget_s: float = 180.0,
    outer_progress_dir: Path | None = None,
) -> LiveContinuationOutcome | ExperimentalRatingBlocked:
    """Resume from admitted n=1..16 and pinned R21C comparisons; live-solve n=32+."""
    from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
        second_candidate_comparison_admission as scca,
    )

    scsa.verify_n4_timeout_receipt_preserved(root)
    scsa.verify_n16_timeout_receipt_preserved(root)
    scsa.verify_n32_timeout_receipt_preserved(root)
    frozen = scsa.admit_frozen_second_candidate_snapshot(root)
    request_hash = frozen.rating_request_hash
    candidate_id = frozen.request.candidate_id
    snapshot_path = root / scsa.SNAPSHOT_REL

    stages_by_mesh: dict[int, dict[str, Any]] = {}
    for pin in scsa.SECOND_CANDIDATE_R21D_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(root, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        if run.mesh_result_hash != receipt["mesh_result_hash"]:
            return _blocked("PRIOR_MESH_REPLAY_HASH_MISMATCH", f"mesh_n={pin.mesh_n}")
        stages_by_mesh[pin.mesh_n] = receipt

    comparisons, rolling = scca.admit_r21c_historical_comparisons(
        root,
        stages_by_mesh=stages_by_mesh,
    )
    stages = [stages_by_mesh[n] for n in (1, 2, 4, 8, 16)]
    stage_artifacts: list[dict[str, str]] = []
    comparison_artifacts: list[dict[str, str]] = []

    wall_t0 = time.perf_counter()
    deadline = wall_t0 + total_budget_s

    def _remaining() -> float:
        return max(0.0, deadline - time.perf_counter())

    for mesh_n in live_mesh_levels:
        if _remaining() <= 0:
            rolling.budget_exhausted()
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21D,
                blocked_code=rolling.blocked_code or "TOTAL_BUDGET_EXCEEDED",
            )
        budget = min(mesh_budgets_s.get(mesh_n, 450.0), _remaining())
        progress_path = None
        trial_log_path = None
        if outer_progress_dir is not None:
            outer_progress_dir.mkdir(parents=True, exist_ok=True)
            progress_path = outer_progress_dir / f"outer-progress-n{mesh_n}.json"
            trial_log_path = outer_progress_dir / f"outer-progress-n{mesh_n}-trials.jsonl"
        receipt = run_live_mesh_worker_from_snapshot(
            snapshot_path,
            snapshot_sha256=scsa.SNAPSHOT_CONTENT_SHA256,
            rating_request_hash=request_hash,
            mesh_n=mesh_n,
            budget_s=budget,
            outer_progress_path=progress_path,
            outer_progress_trial_log_path=trial_log_path,
        )
        receipt["stage_status"] = (
            "MESH_TERMINAL_ACCEPTED"
            if receipt.get("worker_status") == "TERMINAL_ACCEPTED"
            and receipt.get("terminal_tolerance_pass")
            else receipt.get("worker_status", "BLOCKED")
        )
        stages.append(receipt)
        stage_artifacts.append(
            write_stage_receipt(output_stage_dir, mesh_n, receipt, repo_root=root)
        )
        if receipt.get("worker_status") == "TIMEOUT":
            return _ledger_outcome(
                status="TIMEOUT",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21D,
                blocked_code=receipt.get("blocked_code"),
            )
        if receipt.get("worker_status") != "TERMINAL_ACCEPTED":
            return _ledger_outcome(
                status="BLOCKED",
                request_hash=request_hash,
                candidate_id=candidate_id,
                stages=stages,
                comparisons=comparisons,
                artifacts=stage_artifacts,
                rolling=rolling,
                wall_t0=wall_t0,
                snapshot_file_sha256=frozen.snapshot_file_sha256,
                orchestrator_authority_id=ORCHESTRATOR_R21D,
                blocked_code=receipt.get("blocked_code") or "MESH_NOT_TERMINAL_ACCEPTED",
                blocked_diagnostics=tuple(receipt.get("blocked_diagnostics") or ()),
            )
        rolling.record_mesh_accepted(mesh_n)
        outcome = _compare_pair(
            root,
            snapshot_path,
            stages[-2],
            stages[-1],
            request_hash,
            candidate_id,
            rolling,
            comparisons,
            comparison_artifacts,
            output_comparison_dir,
            compare_budget_s,
            _remaining(),
            wall_t0,
            stages,
            stage_artifacts,
            frozen.snapshot_file_sha256,
            ORCHESTRATOR_R21D,
        )
        if outcome is not None:
            return outcome

    return _ledger_outcome(
        status="LIVE_RATING_IN_PROGRESS",
        request_hash=request_hash,
        candidate_id=candidate_id,
        stages=stages,
        comparisons=comparisons,
        artifacts=stage_artifacts,
        rolling=rolling,
        wall_t0=wall_t0,
        snapshot_file_sha256=frozen.snapshot_file_sha256,
        orchestrator_authority_id=ORCHESTRATOR_R21D,
    )
