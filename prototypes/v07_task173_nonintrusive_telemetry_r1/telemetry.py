"""Non-intrusive TASK173 progress telemetry (prototype — not wired to production solvers)."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final, Literal, TextIO

SCHEMA_VERSION: Final = "task173.telemetry.progress-event.v1"
EventSource = Literal["external_os", "solver_internal"]
SessionStatus = Literal["completed", "aborted", "failed"]

# Engineering-agnostic mock result used only to prove telemetry cannot alter compute receipts.
MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH: Final = (
    "1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743"
)


@dataclass
class TelemetryWritePolicy:
    """Limits disk churn; counters remain exact in memory regardless of log sampling."""

    recovery_every_n_events: int = 25
    task172_detail_every_n: int = 50
    max_jsonl_lines: int = 2_000_000
    os_sample_min_interval_s: float = 5.0

    def __post_init__(self) -> None:
        if self.recovery_every_n_events < 1:
            raise ValueError("recovery_every_n_events must be >= 1")
        if self.task172_detail_every_n < 1:
            raise ValueError("task172_detail_every_n must be >= 1")
        if self.max_jsonl_lines < 1:
            raise ValueError("max_jsonl_lines must be >= 1")
        if self.os_sample_min_interval_s < 0:
            raise ValueError("os_sample_min_interval_s must be >= 0")


LogIntegrityStatus = Literal["COMPLETE", "INCOMPLETE", "CORRUPT", "EMPTY"]


@dataclass(frozen=True)
class LogIntegrityReport:
    status: LogIntegrityStatus
    suitable_for_compute_evidence: bool
    telemetry_run_ids: tuple[str, ...]
    mixed_telemetry_run_ids: bool
    missing_sequence_gaps: tuple[int, ...]
    conflicting_duplicate_sequences: tuple[int, ...]
    harmless_duplicate_sequences: tuple[int, ...]
    warnings: tuple[str, ...]
    event_count: int
    max_sequence: int


@dataclass
class MockComputeReceipt:
    """Standalone mock 'result' — never read or written by telemetry helpers."""

    result_hash: str = MOCK_CANDIDATE_B_SUCCESS_RESULT_HASH
    outcome: Literal["success", "blocked"] = "success"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class TelemetryRunContext:
    """Side-channel context; must not be referenced from engineering hash paths."""

    telemetry_run_id: str
    artifact_dir: Path
    baseline_git: str
    monotonic_start: float
    sequence: int = 0
    cumulative_task172: int = 0
    _log_path: Path | None = field(default=None, repr=False)
    _recovery_path: Path | None = field(default=None, repr=False)

    @classmethod
    def create(cls, artifact_dir: Path, baseline_git: str, monotonic_start: float) -> TelemetryRunContext:
        run_id = str(uuid.uuid4())
        ctx = cls(
            telemetry_run_id=run_id,
            artifact_dir=artifact_dir,
            baseline_git=baseline_git,
            monotonic_start=monotonic_start,
        )
        ctx._log_path = artifact_dir / f"task173_telemetry_{run_id}.jsonl"
        ctx._recovery_path = artifact_dir / f"task173_telemetry_{run_id}.recovery.json"
        return ctx

    @property
    def log_path(self) -> Path:
        if self._log_path is None:
            raise RuntimeError("telemetry context not initialized")
        return self._log_path

    @property
    def recovery_path(self) -> Path:
        if self._recovery_path is None:
            raise RuntimeError("telemetry context not initialized")
        return self._recovery_path

    def summary_path(self) -> Path:
        return self.artifact_dir / f"task173_telemetry_{self.telemetry_run_id}.summary.json"


@dataclass(frozen=True)
class ProgressEvent:
    schema_version: str
    telemetry_run_id: str
    sequence: int
    emitted_at_utc: str
    source: EventSource
    event_type: str
    elapsed_monotonic_s: float
    payload: dict[str, Any]
    sizing_request_hash: str | None = None
    candidate_id: str | None = None
    candidate_hash: str | None = None
    mesh_subdivisions: int | None = None
    outer_iteration: int | None = None
    physical_support_id: str | None = None
    cell_root_phase: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        body: dict[str, Any] = {
            "schema_version": self.schema_version,
            "telemetry_run_id": self.telemetry_run_id,
            "sequence": self.sequence,
            "emitted_at_utc": self.emitted_at_utc,
            "source": self.source,
            "event_type": self.event_type,
            "elapsed_monotonic_s": self.elapsed_monotonic_s,
            "payload": self.payload,
        }
        for key in (
            "sizing_request_hash",
            "candidate_id",
            "candidate_hash",
            "mesh_subdivisions",
            "outer_iteration",
            "physical_support_id",
            "cell_root_phase",
        ):
            value = getattr(self, key)
            if value is not None:
                body[key] = value
        return body


class TelemetryWriter:
    """Append-only JSONL writer with durable recovery pointer."""

    def __init__(
        self,
        ctx: TelemetryRunContext,
        monotonic_fn: Any,
        policy: TelemetryWritePolicy | None = None,
    ) -> None:
        self._ctx = ctx
        self._monotonic = monotonic_fn
        resolved = policy or TelemetryWritePolicy()
        self._policy = resolved
        self._log_handle: TextIO | None = None
        self._lines_written = 0
        self._task172_since_last_detail = 0
        self._last_os_sample_monotonic = -1.0
        ctx.artifact_dir.mkdir(parents=True, exist_ok=True)

    def close(self) -> None:
        if self._log_handle is not None:
            self._log_handle.flush()
            self._log_handle.close()
            self._log_handle = None

    def _log_file(self) -> TextIO:
        if self._log_handle is None:
            self._log_handle = self._ctx.log_path.open("a", encoding="utf-8")
        return self._log_handle

    def _elapsed(self) -> float:
        return round(self._monotonic() - self._ctx.monotonic_start, 6)

    def flush_task172_progress(self, **correlation: Any) -> None:
        if self._task172_since_last_detail <= 0:
            return
        batch = self._task172_since_last_detail
        self._task172_since_last_detail = 0
        self.emit(
            source="solver_internal",
            event_type="task172_batch_progress",
            payload={
                "evaluations_in_batch": batch,
                "cumulative_task172": self._ctx.cumulative_task172,
            },
            **correlation,
        )

    def record_task172_evaluations(
        self,
        count: int = 1,
        **correlation: Any,
    ) -> None:
        """Increment counters; emit detail lines only per policy (production default path)."""
        if count <= 0:
            return
        for _ in range(count):
            self._ctx.cumulative_task172 += 1
            self._task172_since_last_detail += 1
            if self._task172_since_last_detail >= self._policy.task172_detail_every_n:
                batch = self._task172_since_last_detail
                self._task172_since_last_detail = 0
                self.emit(
                    source="solver_internal",
                    event_type="task172_batch_progress",
                    payload={
                        "evaluations_in_batch": batch,
                        "cumulative_task172": self._ctx.cumulative_task172,
                    },
                    **correlation,
                )

    def emit(
        self,
        *,
        source: EventSource,
        event_type: str,
        payload: dict[str, Any],
        sizing_request_hash: str | None = None,
        candidate_id: str | None = None,
        candidate_hash: str | None = None,
        mesh_subdivisions: int | None = None,
        outer_iteration: int | None = None,
        physical_support_id: str | None = None,
        cell_root_phase: str | None = None,
        fsync: bool = False,
    ) -> ProgressEvent | None:
        if (
            event_type == "os_sample"
            and self._last_os_sample_monotonic >= 0
            and (self._elapsed() - self._last_os_sample_monotonic)
            < self._policy.os_sample_min_interval_s
        ):
            return None

        if self._lines_written >= self._policy.max_jsonl_lines:
            raise TelemetryLogCapacityExceeded(
                f"max_jsonl_lines={self._policy.max_jsonl_lines}"
            )

        self._ctx.sequence += 1
        if event_type == "task172_evaluation_recorded":
            increment = int(payload.get("increment", 1))
            self._ctx.cumulative_task172 += increment
            payload = {**payload, "cumulative_task172": self._ctx.cumulative_task172}
        if event_type == "os_sample":
            self._last_os_sample_monotonic = self._elapsed()
        event = ProgressEvent(
            schema_version=SCHEMA_VERSION,
            telemetry_run_id=self._ctx.telemetry_run_id,
            sequence=self._ctx.sequence,
            emitted_at_utc=_utc_now(),
            source=source,
            event_type=event_type,
            elapsed_monotonic_s=self._elapsed(),
            payload=payload,
            sizing_request_hash=sizing_request_hash,
            candidate_id=candidate_id,
            candidate_hash=candidate_hash,
            mesh_subdivisions=mesh_subdivisions,
            outer_iteration=outer_iteration,
            physical_support_id=physical_support_id,
            cell_root_phase=cell_root_phase,
        )
        line = json.dumps(event.to_json_dict(), sort_keys=True, ensure_ascii=False)
        try:
            handle = self._log_file()
            handle.write(line + "\n")
            handle.flush()
            if fsync:
                import os

                os.fsync(handle.fileno())
            self._lines_written += 1
        except OSError:
            raise
        if (
            event.sequence % self._policy.recovery_every_n_events == 0
            or event_type in ("session_end", "wrapper_abnormal_exit")
        ):
            self._write_recovery(event.sequence)
        return event

    def _write_recovery(self, sequence: int) -> None:
        recovery = {
            "schema_version": SCHEMA_VERSION,
            "telemetry_run_id": self._ctx.telemetry_run_id,
            "last_durable_sequence": sequence,
            "cumulative_task172": self._ctx.cumulative_task172,
            "updated_at_utc": _utc_now(),
        }
        body = json.dumps(recovery, indent=2, sort_keys=True)
        path = self._ctx.recovery_path
        try:
            path.write_text(body, encoding="utf-8")
        except OSError:
            pass


class TelemetryLogCapacityExceeded(Exception):
    """Telemetry-only failure; must not propagate into engineering solvers."""


def load_events(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line_no, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at line {line_no}") from exc
    return events


def _event_fingerprint(event: dict[str, Any]) -> str:
    return json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def analyze_log_integrity(
    events: list[dict[str, Any]],
    *,
    warnings: list[str] | None = None,
) -> LogIntegrityReport:
    """Classify telemetry log completeness; never implies solver correctness."""
    warn = list(warnings or [])
    if not events:
        return LogIntegrityReport(
            status="EMPTY",
            suitable_for_compute_evidence=False,
            telemetry_run_ids=(),
            mixed_telemetry_run_ids=False,
            missing_sequence_gaps=(),
            conflicting_duplicate_sequences=(),
            harmless_duplicate_sequences=(),
            warnings=tuple(warn),
            event_count=0,
            max_sequence=0,
        )

    run_ids: set[str] = set()
    sequences: list[int] = []
    corrupt = False
    for event in events:
        if event.get("schema_version") != SCHEMA_VERSION:
            corrupt = True
            warn.append("unsupported_schema_version")
            continue
        rid = event.get("telemetry_run_id")
        if type(rid) is str:
            run_ids.add(rid)
        seq = event.get("sequence")
        if type(seq) is not int or seq < 1:
            corrupt = True
            warn.append("invalid_sequence_value")
            continue
        sequences.append(seq)

    mixed = len(run_ids) > 1
    if mixed:
        warn.append("mixed_telemetry_run_id")

    missing_gaps: list[int] = []
    if sequences:
        seq_set = set(sequences)
        max_seq = max(sequences)
        for expected in range(1, max_seq + 1):
            if expected not in seq_set:
                missing_gaps.append(expected)

    conflicting: list[int] = []
    harmless_dup: list[int] = []
    by_seq: dict[int, list[str]] = {}
    for event in events:
        seq = event.get("sequence")
        if type(seq) is not int:
            continue
        fp = _event_fingerprint(event)
        by_seq.setdefault(seq, []).append(fp)
    for seq, fingerprints in by_seq.items():
        if len(fingerprints) < 2:
            continue
        if len(set(fingerprints)) > 1:
            if seq not in conflicting:
                conflicting.append(seq)
            warn.append(f"conflicting_duplicate_sequence:{seq}")
        else:
            harmless_dup.append(seq)
            warn.append(f"harmless_duplicate_sequence:{seq}")

    for w in warn:
        if w.startswith("skip_corrupt_line:"):
            corrupt = True
        elif w.startswith("conflicting_duplicate_sequence:"):
            try:
                seq_num = int(w.rsplit(":", 1)[-1])
            except ValueError:
                continue
            if seq_num not in conflicting:
                conflicting.append(seq_num)

    if corrupt:
        status: LogIntegrityStatus = "CORRUPT"
    elif missing_gaps or conflicting or mixed:
        status = "INCOMPLETE"
    else:
        status = "COMPLETE"

    # Sequence / record integrity only — not solver session completion (see _apply_compute_evidence_gate).
    log_sequence_complete = status == "COMPLETE" and not warn
    return LogIntegrityReport(
        status=status,
        suitable_for_compute_evidence=log_sequence_complete,
        telemetry_run_ids=tuple(sorted(run_ids)),
        mixed_telemetry_run_ids=mixed,
        missing_sequence_gaps=tuple(missing_gaps),
        conflicting_duplicate_sequences=tuple(conflicting),
        harmless_duplicate_sequences=tuple(harmless_dup),
        warnings=tuple(warn),
        event_count=len(events),
        max_sequence=max(sequences) if sequences else 0,
    )


def load_events_tolerant(
    log_path: Path,
) -> tuple[list[dict[str, Any]], list[str], LogIntegrityReport]:
    """Load JSONL skipping blank/corrupt lines; dedupe by sequence (keep last)."""
    if not log_path.is_file():
        empty = analyze_log_integrity([], warnings=["log_file_missing"])
        return [], ["log_file_missing"], empty
    warnings: list[str] = []
    raw_by_sequence: dict[int, list[dict[str, Any]]] = {}
    for line_no, line in enumerate(log_path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            warnings.append(f"skip_corrupt_line:{line_no}")
            continue
        seq = event.get("sequence")
        if type(seq) is not int:
            warnings.append(f"skip_missing_sequence:{line_no}")
            continue
        raw_by_sequence.setdefault(seq, []).append(event)

    by_sequence: dict[int, dict[str, Any]] = {}
    for seq, versions in raw_by_sequence.items():
        fingerprints = {_event_fingerprint(item) for item in versions}
        if len(fingerprints) > 1:
            warnings.append(f"conflicting_duplicate_sequence:{seq}")
        by_sequence[seq] = versions[-1]

    events = [by_sequence[k] for k in sorted(by_sequence)]
    integrity = analyze_log_integrity(events, warnings=warnings)
    return events, warnings, integrity


def _session_end_completed(events: list[dict[str, Any]]) -> bool:
    for event in events:
        if event.get("event_type") != "session_end":
            continue
        if event.get("payload", {}).get("status") == "completed":
            return True
    return False


def _apply_compute_evidence_gate(summary: dict[str, Any]) -> None:
    """Requires intact JSONL sequence, normal session end, and no abnormal termination."""
    log_ok = bool(summary.get("log_sequence_complete"))
    session_ok = bool(summary.get("session_end_completed"))
    abnormal = bool(summary.get("abnormal_termination"))
    summary["suitable_for_compute_evidence"] = log_ok and session_ok and not abnormal


def _integrity_projection(report: LogIntegrityReport) -> dict[str, Any]:
    log_sequence_complete = report.suitable_for_compute_evidence
    return {
        "log_integrity_status": report.status,
        "log_sequence_complete": log_sequence_complete,
        "suitable_for_compute_evidence": False,
        "mixed_telemetry_run_ids": report.mixed_telemetry_run_ids,
        "telemetry_run_ids": list(report.telemetry_run_ids),
        "missing_sequence_gaps": list(report.missing_sequence_gaps),
        "conflicting_duplicate_sequences": list(report.conflicting_duplicate_sequences),
        "harmless_duplicate_sequences": list(report.harmless_duplicate_sequences),
        "integrity_warnings": list(report.warnings),
    }


def recover_from_log(log_path: Path, recovery_path: Path | None = None) -> dict[str, Any]:
    """Strict rebuild from JSONL (raises on corrupt JSON)."""
    events = load_events(log_path)
    integrity = analyze_log_integrity(events)
    summary = aggregate_events(events)
    summary["session_end_completed"] = _session_end_completed(events)
    summary.update(_integrity_projection(integrity))
    if recovery_path is not None and recovery_path.is_file():
        recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
        summary["recovered_from_sequence"] = recovery.get("last_durable_sequence")
        summary["recovery_file_cumulative_task172"] = recovery.get("cumulative_task172")
    else:
        summary["recovered_from_sequence"] = events[-1]["sequence"] if events else 0
    _apply_compute_evidence_gate(summary)
    return summary


def recover_from_log_tolerant(log_path: Path, recovery_path: Path | None = None) -> dict[str, Any]:
    """Best-effort rebuild; marks incomplete logs as unsuitable for compute evidence."""
    events, _load_warnings, integrity = load_events_tolerant(log_path)
    summary = aggregate_events(events) if events else {
        "schema_version": SCHEMA_VERSION,
        "telemetry_run_id": None,
        "counts_by_event_type": {},
        "candidates_started": 0,
        "candidates_finished": 0,
        "mesh_levels_observed": [],
        "outer_iterations_observed": [],
        "cumulative_task172_max": 0,
        "wall_elapsed_s": 0.0,
        "abnormal_termination": False,
        "session_end_completed": False,
    }
    summary["session_end_completed"] = _session_end_completed(events)
    summary.update(_integrity_projection(integrity))
    if recovery_path is not None and recovery_path.is_file():
        recovery = json.loads(recovery_path.read_text(encoding="utf-8"))
        summary["recovered_from_sequence"] = recovery.get("last_durable_sequence")
        summary["recovery_file_cumulative_task172"] = recovery.get("cumulative_task172")
    else:
        summary["recovered_from_sequence"] = integrity.max_sequence
    _apply_compute_evidence_gate(summary)
    return summary


def aggregate_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    mesh_levels: set[int] = set()
    outer_iters: set[int] = set()
    candidates_started = 0
    candidates_finished = 0
    cumulative_task172_max = 0
    abnormal = False
    wall_elapsed = 0.0
    run_id = None
    for event in events:
        if event.get("schema_version") != SCHEMA_VERSION:
            raise ValueError("unsupported telemetry schema")
        run_id = event.get("telemetry_run_id")
        et = event["event_type"]
        counts[et] = counts.get(et, 0) + 1
        wall_elapsed = max(wall_elapsed, float(event.get("elapsed_monotonic_s", 0)))
        if et == "candidate_started":
            candidates_started += 1
        if et == "candidate_finished":
            candidates_finished += 1
        if et == "mesh_started" and event.get("mesh_subdivisions") is not None:
            mesh_levels.add(int(event["mesh_subdivisions"]))
        if et == "outer_iteration_started" and event.get("outer_iteration") is not None:
            outer_iters.add(int(event["outer_iteration"]))
        if et in ("task172_evaluation_recorded", "task172_batch_progress"):
            cumulative_task172_max = max(
                cumulative_task172_max, int(event["payload"].get("cumulative_task172", 0))
            )
        if et in ("wrapper_abnormal_exit", "session_end") and event.get("payload", {}).get(
            "status"
        ) in ("aborted", "failed"):
            abnormal = True
        if et == "wrapper_abnormal_exit":
            abnormal = True
    return {
        "schema_version": SCHEMA_VERSION,
        "telemetry_run_id": run_id,
        "counts_by_event_type": counts,
        "candidates_started": candidates_started,
        "candidates_finished": candidates_finished,
        "mesh_levels_observed": sorted(mesh_levels),
        "outer_iterations_observed": sorted(outer_iters),
        "cumulative_task172_max": cumulative_task172_max,
        "wall_elapsed_s": wall_elapsed,
        "abnormal_termination": abnormal,
        "session_end_completed": _session_end_completed(events),
    }


def write_summary(ctx: TelemetryRunContext, events: list[dict[str, Any]]) -> Path:
    integrity = analyze_log_integrity(events)
    summary = aggregate_events(events)
    summary["recovered_from_sequence"] = events[-1]["sequence"] if events else 0
    summary.update(_integrity_projection(integrity))
    _apply_compute_evidence_gate(summary)
    path = ctx.summary_path()
    path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_summary_safe(ctx: TelemetryRunContext, events: list[dict[str, Any]]) -> Path | None:
    """Telemetry-only; failures must not affect solver control flow."""
    try:
        return write_summary(ctx, events)
    except (OSError, TypeError, ValueError):
        return None


def emit_telemetry_safe(writer: TelemetryWriter | None, **kwargs: Any) -> None:
    """Never let telemetry failures alter caller control flow (not BaseException)."""
    if writer is None:
        return
    try:
        writer.emit(**kwargs)
    except (OSError, TelemetryLogCapacityExceeded, ValueError, TypeError):
        return
