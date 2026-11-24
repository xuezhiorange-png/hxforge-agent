"""Best-effort shard execution progress (diagnostic only).

Writes incremental progress snapshots while pytest runs. This artifact is
NOT counting authority: formal acceptance remains pytest-outcomes.json,
JUnit, and node-inventory cross-validation after a completed session.
"""

from __future__ import annotations

import json
import os
import resource
import time
from pathlib import Path
from typing import Any

import pytest

_SCHEMA_VERSION = "hxforge.shard-progress.v1"


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("hxforge-task-015a")
    group.addoption(
        "--hx-progress-output",
        default="",
        help="Path for diagnostic shard-execution-progress JSON (optional).",
    )


def _rss_kb() -> int:
    try:
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except (OSError, ValueError):
        return 0


class ShardProgressRecorder:
    __slots__ = (
        "_completed",
        "_last_flush",
        "_output",
        "_session_start",
        "_running",
    )

    def __init__(self, output_path: Path) -> None:
        self._output = output_path
        self._session_start = time.monotonic()
        self._completed: list[dict[str, Any]] = []
        self._running: str | None = None
        self._last_flush = 0.0
        self._flush(initial=True)

    def mark_running(self, node_id: str) -> None:
        self._running = node_id
        self._flush()

    def mark_finished(self, node_id: str, outcome: str) -> None:
        now = time.monotonic()
        self._completed.append(
            {
                "completed_at_monotonic_s": round(now - self._session_start, 3),
                "node_id": node_id,
                "outcome": outcome,
            }
        )
        self._running = None
        if now - self._last_flush >= 5.0 or len(self._completed) % 5 == 0:
            self._flush()

    def _flush(self, *, initial: bool = False) -> None:
        payload = {
            "completed_count": len(self._completed),
            "completed_tests": self._completed,
            "diagnostic_only": True,
            "last_running_node_id": self._running,
            "peak_rss_kb_snapshot": _rss_kb(),
            "schema_version": _SCHEMA_VERSION,
            "session_started_at_unix": time.time(),
            "wall_elapsed_s": round(time.monotonic() - self._session_start, 3),
        }
        if initial:
            payload["status"] = "started"
        else:
            payload["status"] = "in_progress"
        tmp = self._output.with_suffix(self._output.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        tmp.replace(self._output)
        self._last_flush = time.monotonic()

    def finalize(self, *, status: str, exitstatus: int) -> None:
        payload = {
            "completed_count": len(self._completed),
            "completed_tests": self._completed,
            "diagnostic_only": True,
            "exitstatus": exitstatus,
            "last_running_node_id": self._running,
            "peak_rss_kb_snapshot": _rss_kb(),
            "schema_version": _SCHEMA_VERSION,
            "session_started_at_unix": time.time(),
            "status": status,
            "wall_elapsed_s": round(time.monotonic() - self._session_start, 3),
        }
        text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
        self._output.write_text(text, encoding="utf-8")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item: pytest.Item) -> Any:  # pragma: no cover
    recorder: ShardProgressRecorder | None = getattr(item.config, "_hx_progress_recorder", None)
    if recorder is not None:
        recorder.mark_running(item.nodeid.replace("\\", "/"))
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(  # pragma: no cover
    item: pytest.Item, call: pytest.CallInfo[Any]
) -> Any:
    outcome = yield
    report = outcome.get_result()
    recorder: ShardProgressRecorder | None = getattr(item.config, "_hx_progress_recorder", None)
    if recorder is None or call.when != "call":
        return
    node_id = item.nodeid.replace("\\", "/")
    terminal = report.outcome
    if terminal == "passed":
        mapped = "passed"
    elif terminal in ("failed", "error"):
        mapped = "failed"
    elif terminal == "skipped":
        mapped = "skipped"
    else:
        mapped = terminal
    recorder.mark_finished(node_id, mapped)


def pytest_configure(config: pytest.Config) -> None:
    out_opt = config.getoption("--hx-progress-output", default="")
    env_out = os.environ.get("HX_SHARD_PROGRESS_PATH", "")
    path_str = out_opt or env_out
    if not path_str:
        return
    recorder = ShardProgressRecorder(Path(path_str))
    config._hx_progress_recorder = recorder  # type: ignore[attr-defined]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # pragma: no cover
    recorder: ShardProgressRecorder | None = getattr(session.config, "_hx_progress_recorder", None)
    if recorder is None:
        return
    status = "completed" if exitstatus == 0 else "finished_nonzero"
    recorder.finalize(status=status, exitstatus=exitstatus)
