"""Tests for non-intrusive telemetry prototype (no solver imports)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

_PROTOTYPE_DIR = Path(__file__).resolve().parent
if str(_PROTOTYPE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTOTYPE_DIR))

from mock_runner import simulate_rating_like_run
from telemetry import (
    MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
    MockComputeReceipt,
    SCHEMA_VERSION,
    TelemetryRunContext,
    TelemetryWritePolicy,
    TelemetryWriter,
    aggregate_events,
    load_events,
    load_events_tolerant,
    recover_from_log,
)


def test_jsonl_append_and_monotonic_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        t0 = time.monotonic()
        ctx = TelemetryRunContext.create(artifact, "84c5f38", t0)
        writer = TelemetryWriter(ctx, time.monotonic)
        writer.emit(source="solver_internal", event_type="session_start", payload={})
        writer.emit(source="solver_internal", event_type="task172_evaluation_recorded", payload={})
        writer.close()
        events = load_events(ctx.log_path)
        assert len(events) == 2
        assert events[0]["sequence"] == 1
        assert events[1]["sequence"] == 2
        assert events[1]["payload"]["cumulative_task172"] == 1


def test_task172_batching_reduces_lines() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        ctx = TelemetryRunContext.create(artifact, "84c5f38", time.monotonic())
        policy = TelemetryWritePolicy(task172_detail_every_n=10, recovery_every_n_events=1000)
        writer = TelemetryWriter(ctx, time.monotonic, policy)
        writer.emit(source="solver_internal", event_type="session_start", payload={})
        writer.record_task172_evaluations(25)
        writer.flush_task172_progress()
        writer.close()
        events = load_events(ctx.log_path)
        batch_events = [e for e in events if e["event_type"] == "task172_batch_progress"]
        assert len(batch_events) == 3
        assert ctx.cumulative_task172 == 25
        assert batch_events[-1]["payload"]["cumulative_task172"] == 25


def test_aggregate_counts() -> None:
    events = [
        {
            "schema_version": SCHEMA_VERSION,
            "telemetry_run_id": "run-1",
            "event_type": "candidate_started",
            "elapsed_monotonic_s": 1.0,
            "mesh_subdivisions": None,
            "outer_iteration": None,
            "payload": {},
        },
        {
            "schema_version": SCHEMA_VERSION,
            "telemetry_run_id": "run-1",
            "event_type": "task172_batch_progress",
            "elapsed_monotonic_s": 3.0,
            "payload": {"cumulative_task172": 10},
        },
    ]
    summary = aggregate_events(events)
    assert summary["candidates_started"] == 1
    assert summary["cumulative_task172_max"] == 10


def test_recovery_matches_log() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        result = simulate_rating_like_run(artifact, abort_mid_candidate=False)
        assert result["mock_compute_result_hash"] == MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH
        log_path = Path(result["log_path"])
        recovery_path = Path(result["recovery_path"])
        recovered = recover_from_log(log_path, recovery_path)
        assert recovered["cumulative_task172_max"] == 294
        assert recovered["recovery_file_cumulative_task172"] == recovered["cumulative_task172_max"]


def test_abnormal_exit_flagged() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        result = simulate_rating_like_run(artifact, abort_mid_candidate=True)
        assert result["mock_compute_result_hash"] == MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH
        recovered = result["recovered"]
        assert recovered["abnormal_termination"] is True
        assert recovered["candidates_finished"] == 0


def test_telemetry_not_in_engineering_hash_scope() -> None:
    from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
        Task173SizingRequest,
    )

    projection_keys = set(Task173SizingRequest.model_fields.keys())
    forbidden = {"telemetry_run_id", "progress_events", "task173_telemetry_path"}
    assert forbidden.isdisjoint(projection_keys)


def test_mock_runner_writes_summary_with_batch_events() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        result = simulate_rating_like_run(artifact)
        summary = json.loads(Path(result["summary_path"]).read_text())
        assert summary["counts_by_event_type"].get("task172_batch_progress", 0) >= 1


def test_jsonl_write_failure_does_not_change_mock_receipt() -> None:
    receipt = MockComputeReceipt()
    with tempfile.TemporaryDirectory() as tmp:
        ctx = TelemetryRunContext.create(Path(tmp), "84c5f38", time.monotonic())
        writer = TelemetryWriter(ctx, time.monotonic)
        with patch.object(Path, "open", side_effect=OSError("simulated disk full")):
            try:
                writer.emit(source="solver_internal", event_type="session_start", payload={})
            except OSError:
                pass
    assert receipt.result_hash == MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH


def test_tolerant_load_skips_corrupt_and_dedupes_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "t.jsonl"
        log.write_text(
            '{"schema_version":"task173.telemetry.progress-event.v1","sequence":1,'
            '"event_type":"session_start","elapsed_monotonic_s":0,"payload":{}}\n'
            "not json\n"
            '{"schema_version":"task173.telemetry.progress-event.v1","sequence":2,'
            '"event_type":"task172_batch_progress","elapsed_monotonic_s":1,'
            '"payload":{"cumulative_task172":5}}\n'
            '{"schema_version":"task173.telemetry.progress-event.v1","sequence":2,'
            '"event_type":"task172_batch_progress","elapsed_monotonic_s":2,'
            '"payload":{"cumulative_task172":9}}\n',
            encoding="utf-8",
        )
        events, warnings = load_events_tolerant(log)
        assert len(events) == 2
        assert "skip_corrupt_line:2" in warnings
        assert "duplicate_sequence:2" in warnings
        assert events[-1]["payload"]["cumulative_task172"] == 9
