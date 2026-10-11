#!/usr/bin/env python3
"""Simulate TASK173 telemetry without invoking Rating/Sizing solvers."""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from telemetry import (
    MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
    TelemetryLogCapacityExceeded,
    TelemetryRunContext,
    TelemetryWritePolicy,
    TelemetryWriter,
    emit_telemetry_safe,
    load_events,
    recover_from_log,
    recover_from_log_tolerant,
    write_summary_safe,
)

BASELINE_GIT = "84c5f38b74fd26eacefee260af7be26c12cb2e31"
MOCK_SIZING_REQUEST_HASH = (
    "e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e"
)
MOCK_CANDIDATE_B = {
    "candidate_id": "e152cca9-fd5d-59ca-9b46-1df574eee841",
    "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
}


@dataclass(frozen=True)
class MockSolveInputs:
    mesh_sequence: tuple[int, ...]
    task172_per_cell: int
    intervals: int
    outer_iters: int
    aborted: bool


@dataclass(frozen=True)
class MockSolveOutcome:
    candidate_rating_result_hash: str
    outcome: str
    total_task172_evaluations: int


def compute_mock_candidate_rating(inputs: MockSolveInputs) -> MockSolveOutcome:
    """Deterministic mock 'solve' — independent of telemetry I/O."""
    total_cells = 0
    for subdivisions in inputs.mesh_sequence:
        if inputs.aborted and subdivisions == 2:
            break
        total_cells += inputs.outer_iters * inputs.intervals * subdivisions
    total_task172 = total_cells * inputs.task172_per_cell
    if inputs.aborted:
        return MockSolveOutcome(
            candidate_rating_result_hash="aborted-mock-no-rating-result",
            outcome="aborted",
            total_task172_evaluations=total_task172,
        )
    return MockSolveOutcome(
        candidate_rating_result_hash=MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
        outcome="success",
        total_task172_evaluations=total_task172,
    )


def simulate_rating_like_run(
    artifact_dir: Path,
    *,
    abort_mid_candidate: bool = False,
    writer_factory: Callable[[TelemetryRunContext], TelemetryWriter | None] | None = None,
) -> dict[str, object]:
    solve_inputs = MockSolveInputs(
        mesh_sequence=(1, 2, 4),
        task172_per_cell=7,
        intervals=2,
        outer_iters=3,
        aborted=abort_mid_candidate,
    )
    expected_solve = compute_mock_candidate_rating(solve_inputs)

    t0 = time.monotonic()
    ctx = TelemetryRunContext.create(artifact_dir, BASELINE_GIT, t0)
    default_policy = TelemetryWritePolicy(recovery_every_n_events=25, task172_detail_every_n=25)
    if writer_factory is None:
        writer: TelemetryWriter | None = TelemetryWriter(ctx, time.monotonic, default_policy)
    else:
        writer = writer_factory(ctx)

    def emit(**kwargs: Any) -> None:
        emit_telemetry_safe(writer, **kwargs)

    def record_task172(count: int, **correlation: Any) -> None:
        if writer is None:
            return
        try:
            writer.record_task172_evaluations(count, **correlation)
        except (OSError, TelemetryLogCapacityExceeded, ValueError, TypeError):
            return

    def flush_task172(**correlation: Any) -> None:
        if writer is None:
            return
        try:
            writer.flush_task172_progress(**correlation)
        except (OSError, TelemetryLogCapacityExceeded, ValueError, TypeError):
            return

    emit(
        source="solver_internal",
        event_type="session_start",
        payload={"host": "cursor-cloud-mock", "baseline_git": BASELINE_GIT},
    )
    emit(
        source="external_os",
        event_type="os_sample",
        payload={"cpu_percent": 12.5, "memory_rss_mb": 1024, "memory_available_mb": 4096},
    )

    mesh_sequence = solve_inputs.mesh_sequence
    for cand_index, candidate in enumerate((MOCK_CANDIDATE_B,)):
        emit(
            source="solver_internal",
            event_type="candidate_started",
            payload={"candidate_index": cand_index},
            sizing_request_hash=MOCK_SIZING_REQUEST_HASH,
            candidate_id=candidate["candidate_id"],
            candidate_hash=candidate["candidate_hash"],
        )
        for mesh_index, subdivisions in enumerate(mesh_sequence):
            emit(
                source="solver_internal",
                event_type="mesh_started",
                payload={"mesh_index": mesh_index},
                mesh_subdivisions=subdivisions,
                candidate_id=candidate["candidate_id"],
            )
            mesh_task172 = 0
            for outer in range(solve_inputs.outer_iters):
                emit(
                    source="solver_internal",
                    event_type="outer_iteration_started",
                    payload={"shooting_enthalpy_j_kg": "125400.0"},
                    mesh_subdivisions=subdivisions,
                    outer_iteration=outer,
                    candidate_id=candidate["candidate_id"],
                )
                for interval in range(solve_inputs.intervals):
                    for sub in range(subdivisions):
                        support_id = f"{candidate['candidate_id']}:seg:{interval}:{sub}"
                        emit(
                            source="solver_internal",
                            event_type="cell_root_started",
                            payload={"interval_index": interval, "subdivision_index": sub},
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            cell_root_phase="PHYSICAL_ENDPOINT_EVALUATION",
                            candidate_id=candidate["candidate_id"],
                        )
                        record_task172(
                            solve_inputs.task172_per_cell,
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            candidate_id=candidate["candidate_id"],
                        )
                        mesh_task172 += solve_inputs.task172_per_cell
                        emit(
                            source="solver_internal",
                            event_type="cell_root_finished",
                            payload={
                                "task172_evaluations_this_cell": solve_inputs.task172_per_cell,
                                "closure_mode": "EXACT_VALID_POINT_ROOT",
                            },
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            candidate_id=candidate["candidate_id"],
                        )
                emit(
                    source="solver_internal",
                    event_type="outer_iteration_finished",
                    payload={"classification": "VALID_TRAJECTORY"},
                    mesh_subdivisions=subdivisions,
                    outer_iteration=outer,
                    candidate_id=candidate["candidate_id"],
                )
            flush_task172(
                mesh_subdivisions=subdivisions,
                candidate_id=candidate["candidate_id"],
            )
            emit(
                source="solver_internal",
                event_type="mesh_finished",
                payload={
                    "task172_local_evaluation_count": mesh_task172,
                    "task172_numerical_hole_count": 0,
                },
                mesh_subdivisions=subdivisions,
                candidate_id=candidate["candidate_id"],
            )
            if abort_mid_candidate and subdivisions == 2:
                emit(
                    source="external_os",
                    event_type="wrapper_abnormal_exit",
                    payload={"reason": "simulated_agent_session_timeout"},
                    fsync=True,
                )
                emit(
                    source="solver_internal",
                    event_type="session_end",
                    payload={"status": "aborted"},
                    fsync=True,
                )
                if writer is not None:
                    writer.close()
                actual_solve = compute_mock_candidate_rating(solve_inputs)
                events = load_events(ctx.log_path) if ctx.log_path.is_file() else []
                if events:
                    write_summary_safe(ctx, events)
                recovered = recover_from_log_tolerant(ctx.log_path, ctx.recovery_path)
                return {
                    "mode": "aborted",
                    "mock_compute_result_hash": actual_solve.candidate_rating_result_hash,
                    "expected_mock_compute_result_hash": expected_solve.candidate_rating_result_hash,
                    "mock_solve_matches_expected": (
                        actual_solve == expected_solve
                    ),
                    "log_path": str(ctx.log_path),
                    "summary_path": str(ctx.summary_path()),
                    "recovery_path": str(ctx.recovery_path),
                    "recovered": recovered,
                }

        emit(
            source="solver_internal",
            event_type="candidate_finished",
            payload={
                "outcome": expected_solve.outcome,
                "candidate_rating_result_hash": expected_solve.candidate_rating_result_hash,
            },
            candidate_id=candidate["candidate_id"],
            candidate_hash=candidate["candidate_hash"],
        )

    emit(
        source="solver_internal",
        event_type="session_end",
        payload={"status": "completed"},
        fsync=True,
    )
    if writer is not None:
        writer.close()
    actual_solve = compute_mock_candidate_rating(solve_inputs)
    events = load_events(ctx.log_path)
    summary_path = write_summary_safe(ctx, events)
    recovered = recover_from_log(ctx.log_path, ctx.recovery_path)
    return {
        "mode": "completed",
        "mock_compute_result_hash": actual_solve.candidate_rating_result_hash,
        "expected_mock_compute_result_hash": expected_solve.candidate_rating_result_hash,
        "mock_solve_matches_expected": actual_solve == expected_solve,
        "expected_frozen_success_hash": MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
        "log_path": str(ctx.log_path),
        "summary_path": str(summary_path) if summary_path is not None else str(ctx.summary_path()),
        "recovery_path": str(ctx.recovery_path),
        "event_count": len(events),
        "recovered": recovered,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path("/opt/cursor/artifacts/task173_telemetry_r1"),
    )
    parser.add_argument("--abort-mid-candidate", action="store_true")
    args = parser.parse_args()
    result = simulate_rating_like_run(args.artifact_dir, abort_mid_candidate=args.abort_mid_candidate)
    out = args.artifact_dir / "mock_run_report.json"
    args.artifact_dir.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
