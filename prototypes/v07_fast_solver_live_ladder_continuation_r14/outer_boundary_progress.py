"""Incremental outer-boundary trial progress (append-only, survives hard timeout)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

TRIAL_LOG_ENTRY_SCHEMA = "task173.experimental-outer-boundary-trial-log-entry.v1"
OUTER_PROGRESS_SCHEMA_V2 = "task173.experimental-outer-boundary-progress.v2"


def append_trial_log_entry(log_path: Path, trial_record: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "schema_version": TRIAL_LOG_ENTRY_SCHEMA,
        **trial_record,
    }
    line = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def read_trial_log_entries(log_path: Path) -> list[dict[str, Any]]:
    if not log_path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        if payload.get("schema_version") != TRIAL_LOG_ENTRY_SCHEMA:
            raise ValueError("invalid trial log entry schema")
        entries.append(payload)
    return entries


def _atomic_write_json(path: Path, body: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as tmp:
        tmp.write(json.dumps(body, indent=2, sort_keys=True) + "\n")
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def materialize_progress_snapshot(
    *,
    progress_path: Path,
    trial_log_path: Path,
    mesh_n: int,
    worker_status: str,
    blocked_code: str | None = None,
    worker_wall_seconds: float | None = None,
) -> None:
    trials = read_trial_log_entries(trial_log_path)
    outer_trial_wall = sum(float(t.get("wall_seconds", 0.0)) for t in trials)
    mesh_march_wall = sum(float(t.get("mesh_march_seconds", 0.0)) for t in trials)
    last_valid = next(
        (t for t in reversed(trials) if t.get("classification") == "VALID_TRAJECTORY"),
        None,
    )
    body: dict[str, Any] = {
        "schema_version": OUTER_PROGRESS_SCHEMA_V2,
        "mesh_n": mesh_n,
        "worker_status": worker_status,
        "blocked_code": blocked_code,
        "outer_trial_count": len(trials),
        "mesh_march_count": sum(1 for t in trials if t.get("mesh_march_seconds")),
        "outer_trial_wall_seconds_sum": outer_trial_wall,
        "mesh_march_wall_seconds_sum": mesh_march_wall,
        "worker_wall_seconds": worker_wall_seconds,
        "trial_receipts": trials,
        "last_valid_trial": last_valid,
        "progress_kind": (
            "TERMINAL_ACCEPTED"
            if worker_status == "TERMINAL_ACCEPTED"
            else "PARTIAL_TRIAL_LOG_ONLY"
        ),
    }
    _atomic_write_json(progress_path, body)
