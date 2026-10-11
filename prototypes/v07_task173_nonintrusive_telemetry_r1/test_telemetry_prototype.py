"""Tests for non-intrusive telemetry prototype (no solver imports)."""

from __future__ import annotations

import json
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

_PROTOTYPE_DIR = Path(__file__).resolve().parent
if str(_PROTOTYPE_DIR) not in sys.path:
    sys.path.insert(0, str(_PROTOTYPE_DIR))

from mock_runner import compute_mock_candidate_rating, simulate_rating_like_run
from mock_runner import MockSolveInputs
from telemetry import (
    MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH,
    SCHEMA_VERSION,
    TelemetryLogCapacityExceeded,
    TelemetryRunContext,
    TelemetryWritePolicy,
    TelemetryWriter,
    aggregate_events,
    analyze_log_integrity,
    load_events,
    load_events_tolerant,
    recover_from_log,
    recover_from_log_tolerant,
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
        integrity = analyze_log_integrity(events)
        assert integrity.status == "COMPLETE"
        assert integrity.suitable_for_compute_evidence is True


def test_task172_batching_reduces_lines() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        t0 = time.monotonic()
        ctx = TelemetryRunContext.create(artifact, "84c5f38", t0)
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


def test_policy_validation_rejects_invalid_config() -> None:
    with pytest.raises(ValueError):
        TelemetryWritePolicy(recovery_every_n_events=0)
    with pytest.raises(ValueError):
        TelemetryWritePolicy(task172_detail_every_n=0)
    with pytest.raises(ValueError):
        TelemetryWritePolicy(max_jsonl_lines=0)
    with pytest.raises(ValueError):
        TelemetryWritePolicy(os_sample_min_interval_s=-1.0)


def test_log_integrity_detects_gaps_and_mixed_run_ids() -> None:
    events, warnings, integrity = load_events_tolerant(Path("/nonexistent"))
    assert integrity.status == "EMPTY"
    assert integrity.suitable_for_compute_evidence is False

    events = [
        {
            "schema_version": SCHEMA_VERSION,
            "telemetry_run_id": "run-a",
            "sequence": 1,
            "event_type": "session_start",
            "elapsed_monotonic_s": 0.0,
            "payload": {},
        },
        {
            "schema_version": SCHEMA_VERSION,
            "telemetry_run_id": "run-b",
            "sequence": 3,
            "event_type": "session_end",
            "elapsed_monotonic_s": 1.0,
            "payload": {"status": "completed"},
        },
    ]
    integrity = analyze_log_integrity(events)
    assert integrity.status == "INCOMPLETE"
    assert integrity.mixed_telemetry_run_ids is True
    assert integrity.missing_sequence_gaps == (2,)
    assert integrity.suitable_for_compute_evidence is False


def test_tolerant_recovery_marks_incomplete_unsuitable() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "t.jsonl"
        log.write_text(
            '{"schema_version":"task173.telemetry.progress-event.v1","telemetry_run_id":"r1",'
            '"sequence":1,"event_type":"session_start","elapsed_monotonic_s":0,"payload":{}}\n'
            "not-json\n"
            '{"schema_version":"task173.telemetry.progress-event.v1","telemetry_run_id":"r1",'
            '"sequence":2,"event_type":"task172_batch_progress","elapsed_monotonic_s":1,'
            '"payload":{"cumulative_task172":5}}\n',
            encoding="utf-8",
        )
        summary = recover_from_log_tolerant(log)
        assert summary["log_integrity_status"] in ("INCOMPLETE", "CORRUPT")
        assert summary["suitable_for_compute_evidence"] is False


def test_recovery_matches_log() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        result = simulate_rating_like_run(artifact, abort_mid_candidate=False)
        assert result["mock_solve_matches_expected"] is True
        assert result["mock_compute_result_hash"] == MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH
        recovered = recover_from_log(Path(result["log_path"]), Path(result["recovery_path"]))
        assert recovered["cumulative_task172_max"] == 294
        assert recovered["log_integrity_status"] == "COMPLETE"
        assert recovered["suitable_for_compute_evidence"] is True


def test_abnormal_exit_flagged() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        artifact = Path(tmp)
        result = simulate_rating_like_run(artifact, abort_mid_candidate=True)
        assert result["mock_solve_matches_expected"] is True
        recovered = result["recovered"]
        assert recovered["abnormal_termination"] is True
        assert recovered["suitable_for_compute_evidence"] is False


def test_mock_solve_unchanged_when_oserror_on_emit() -> None:
    baseline = compute_mock_candidate_rating(
        MockSolveInputs((1, 2, 4), 7, 2, 3, False)
    )

    def broken_factory(ctx: TelemetryRunContext) -> TelemetryWriter:
        writer = TelemetryWriter(ctx, time.monotonic)

        def boom(*args, **kwargs):  # type: ignore[no-untyped-def]
            raise OSError("simulated disk full")

        writer._log_file = boom  # type: ignore[method-assign]
        return writer

    with tempfile.TemporaryDirectory() as tmp:
        result = simulate_rating_like_run(Path(tmp), writer_factory=broken_factory)
    assert result["mock_solve_matches_expected"] is True
    assert result["mock_compute_result_hash"] == baseline.candidate_rating_result_hash


def test_mock_solve_unchanged_when_capacity_exceeded() -> None:
    def tiny_factory(ctx: TelemetryRunContext) -> TelemetryWriter:
        policy = TelemetryWritePolicy(max_jsonl_lines=2)
        return TelemetryWriter(ctx, time.monotonic, policy)

    with tempfile.TemporaryDirectory() as tmp:
        result = simulate_rating_like_run(Path(tmp), writer_factory=tiny_factory)
    assert result["mock_solve_matches_expected"] is True
    assert result["mode"] == "completed"


def test_mock_solve_unchanged_with_invalid_policy_factory() -> None:
    def bad_factory(ctx: TelemetryRunContext) -> TelemetryWriter | None:
        try:
            TelemetryWritePolicy(recovery_every_n_events=0)
        except ValueError:
            return None
        return TelemetryWriter(ctx, time.monotonic)

    with tempfile.TemporaryDirectory() as tmp:
        result = simulate_rating_like_run(Path(tmp), writer_factory=bad_factory)
    assert result["mock_solve_matches_expected"] is True


def test_telemetry_not_in_engineering_hash_scope() -> None:
    from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import (
        Task173SizingRequest,
    )

    projection_keys = set(Task173SizingRequest.model_fields.keys())
    forbidden = {"telemetry_run_id", "progress_events", "task173_telemetry_path"}
    assert forbidden.isdisjoint(projection_keys)


def test_conflicting_duplicate_sequence() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "t.jsonl"
        log.write_text(
            '{"schema_version":"task173.telemetry.progress-event.v1","telemetry_run_id":"r",'
            '"sequence":1,"event_type":"session_start","elapsed_monotonic_s":0,"payload":{"a":1}}\n'
            '{"schema_version":"task173.telemetry.progress-event.v1","telemetry_run_id":"r",'
            '"sequence":1,"event_type":"session_start","elapsed_monotonic_s":0,"payload":{"a":2}}\n',
            encoding="utf-8",
        )
        _, _, integrity = load_events_tolerant(log)
        assert integrity.conflicting_duplicate_sequences == (1,)
        assert integrity.suitable_for_compute_evidence is False
