"""Minimal regression for shard progress + timeout telemetry classification."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_shard_progress_mark_running_persists_node(tmp_path: Path) -> None:
    from tests.ci.shard_progress_plugin import ShardProgressRecorder

    progress = tmp_path / "shard-execution-progress.json"
    rec = ShardProgressRecorder(progress)
    rec.mark_running("tests/ci/dummy.py::test_alpha")
    payload = json.loads(progress.read_text(encoding="utf-8"))
    assert payload["last_running_node_id"] == "tests/ci/dummy.py::test_alpha"
    assert payload["status"] in ("started", "in_progress")


def test_run_test_shard_timeout_not_collection_error(tmp_path: Path) -> None:
    from tests.ci.run_test_shard import run_pytest

    slow = tmp_path / "test_slow.py"
    slow.write_text(
        "import time\ndef test_hangs():\n    time.sleep(30)\n",
        encoding="utf-8",
    )
    progress = tmp_path / "shard-execution-progress.json"
    exit_code = run_pytest(
        [str(slow), f"--junitxml={tmp_path / 'junit.xml'}"],
        env={"PYTHONPATH": str(REPO_ROOT), "HX_SHARD_PROGRESS_PATH": str(progress)},
        timeout=2,
        junit_path=str(tmp_path / "junit.xml"),
        telemetry_path=str(tmp_path / "telemetry.json"),
        stdout_path=str(tmp_path / "stdout.txt"),
        stderr_path=str(tmp_path / "stderr.txt"),
        outcomes_path=str(tmp_path / "pytest-outcomes.json"),
        track="pr-head",
        commit_sha="abc",
        run_id="1",
        run_attempt=1,
        python_version="3.12",
        shard="diag-timeout",
    )
    telemetry = json.loads((tmp_path / "telemetry.json").read_text(encoding="utf-8"))
    assert exit_code != 0
    assert telemetry["execution_status"] == "timeout"
    assert "pytest_exit_code=-9" in telemetry["producer_authority_failures"]
