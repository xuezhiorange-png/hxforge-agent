#!/usr/bin/env python3
"""Simulate TASK173 telemetry without invoking Rating/Sizing solvers."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from telemetry import (
    MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
    MockComputeReceipt,
    TelemetryRunContext,
    TelemetryWritePolicy,
    TelemetryWriter,
    aggregate_events,
    load_events,
    recover_from_log,
    write_summary,
)

BASELINE_GIT = "84c5f38b74fd26eacefee260af7be26c12cb2e31"
MOCK_SIZING_REQUEST_HASH = (
    "e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e"
)
MOCK_CANDIDATE_B = {
    "candidate_id": "e152cca9-fd5d-59ca-9b46-1df574eee841",
    "candidate_hash": "53e0d9af366a51c915a9a369a74f7563560359dc2b562e413f4674dcb520c489",
}


def simulate_rating_like_run(
    artifact_dir: Path,
    *,
    abort_mid_candidate: bool = False,
) -> dict[str, object]:
    receipt = MockComputeReceipt()
    t0 = time.monotonic()
    ctx = TelemetryRunContext.create(artifact_dir, BASELINE_GIT, t0)
    policy = TelemetryWritePolicy(recovery_every_n_events=25, task172_detail_every_n=25)
    writer = TelemetryWriter(ctx, time.monotonic, policy)

    writer.emit(
        source="solver_internal",
        event_type="session_start",
        payload={"host": "cursor-cloud-mock", "baseline_git": BASELINE_GIT},
    )
    writer.emit(
        source="external_os",
        event_type="os_sample",
        payload={"cpu_percent": 12.5, "memory_rss_mb": 1024, "memory_available_mb": 4096},
    )

    mesh_sequence = (1, 2, 4)
    task172_per_cell = 7
    intervals = 2
    outer_iters = 3

    for cand_index, candidate in enumerate((MOCK_CANDIDATE_B,)):
        writer.emit(
            source="solver_internal",
            event_type="candidate_started",
            payload={"candidate_index": cand_index},
            sizing_request_hash=MOCK_SIZING_REQUEST_HASH,
            candidate_id=candidate["candidate_id"],
            candidate_hash=candidate["candidate_hash"],
        )
        for mesh_index, subdivisions in enumerate(mesh_sequence):
            writer.emit(
                source="solver_internal",
                event_type="mesh_started",
                payload={"mesh_index": mesh_index},
                mesh_subdivisions=subdivisions,
                candidate_id=candidate["candidate_id"],
            )
            mesh_task172 = 0
            for outer in range(outer_iters):
                writer.emit(
                    source="solver_internal",
                    event_type="outer_iteration_started",
                    payload={"shooting_enthalpy_j_kg": "125400.0"},
                    mesh_subdivisions=subdivisions,
                    outer_iteration=outer,
                    candidate_id=candidate["candidate_id"],
                )
                for interval in range(intervals):
                    for sub in range(subdivisions):
                        support_id = f"{candidate['candidate_id']}:seg:{interval}:{sub}"
                        writer.emit(
                            source="solver_internal",
                            event_type="cell_root_started",
                            payload={"interval_index": interval, "subdivision_index": sub},
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            cell_root_phase="PHYSICAL_ENDPOINT_EVALUATION",
                            candidate_id=candidate["candidate_id"],
                        )
                        writer.record_task172_evaluations(
                            task172_per_cell,
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            candidate_id=candidate["candidate_id"],
                        )
                        mesh_task172 += task172_per_cell
                        writer.emit(
                            source="solver_internal",
                            event_type="cell_root_finished",
                            payload={
                                "task172_evaluations_this_cell": task172_per_cell,
                                "closure_mode": "EXACT_VALID_POINT_ROOT",
                            },
                            mesh_subdivisions=subdivisions,
                            outer_iteration=outer,
                            physical_support_id=support_id,
                            candidate_id=candidate["candidate_id"],
                        )
                writer.emit(
                    source="solver_internal",
                    event_type="outer_iteration_finished",
                    payload={"classification": "VALID_TRAJECTORY"},
                    mesh_subdivisions=subdivisions,
                    outer_iteration=outer,
                    candidate_id=candidate["candidate_id"],
                )
            writer.flush_task172_progress(
                mesh_subdivisions=subdivisions,
                candidate_id=candidate["candidate_id"],
            )
            writer.emit(
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
                writer.emit(
                    source="external_os",
                    event_type="wrapper_abnormal_exit",
                    payload={"reason": "simulated_agent_session_timeout"},
                    fsync=True,
                )
                writer.emit(
                    source="solver_internal",
                    event_type="session_end",
                    payload={"status": "aborted"},
                    fsync=True,
                )
                writer.close()
                events = load_events(ctx.log_path)
                write_summary(ctx, events)
                recovered = recover_from_log(ctx.log_path, ctx.recovery_path)
                return {
                    "mode": "aborted",
                    "mock_compute_result_hash": receipt.result_hash,
                    "log_path": str(ctx.log_path),
                    "summary_path": str(ctx.summary_path()),
                    "recovery_path": str(ctx.recovery_path),
                    "recovered": recovered,
                }

        writer.emit(
            source="solver_internal",
            event_type="candidate_finished",
            payload={
                "outcome": receipt.outcome,
                "candidate_rating_result_hash": receipt.result_hash,
            },
            candidate_id=candidate["candidate_id"],
            candidate_hash=candidate["candidate_hash"],
        )

    writer.emit(
        source="solver_internal",
        event_type="session_end",
        payload={"status": "completed"},
        fsync=True,
    )
    writer.close()
    events = load_events(ctx.log_path)
    summary_path = write_summary(ctx, events)
    recovered = recover_from_log(ctx.log_path, ctx.recovery_path)
    return {
        "mode": "completed",
        "mock_compute_result_hash": receipt.result_hash,
        "expected_frozen_success_hash": MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
        "log_path": str(ctx.log_path),
        "summary_path": str(summary_path),
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
