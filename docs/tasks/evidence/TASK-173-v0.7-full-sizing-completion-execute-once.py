"""Execute the frozen completion Sizing request once and capture its result."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_sizing import service as sizing_service

REPOSITORY_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPOSITORY_ROOT))
FREEZE_HEAD = "75a795f676e8cc3b1d2e7e0f89377684c3a78650"
RUNTIME_HEAD = "b1da0536d34ff174c825e9862d7e29cf2d087785"
REQUEST_EVIDENCE = Path(__file__).with_name("TASK-173-v0.7-full-sizing-completion-request-r1.json")
REPLAY_SCRIPT = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
START_MARKER = Path(__file__).with_name(
    "TASK-173-v0.7-full-sizing-completion-execution-start-r1.json"
)
RESULT_PATH = Path(__file__).with_name("TASK-173-v0.7-full-sizing-completion-execution-r1.json")


def _load_replay_module() -> Any:
    spec = importlib.util.spec_from_file_location("completion_request_replay", REPLAY_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load committed completion request replay module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    current_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPOSITORY_ROOT, text=True
    ).strip()
    if current_head != FREEZE_HEAD:
        raise RuntimeError(f"expected request freeze HEAD {FREEZE_HEAD}, got {current_head}")
    subprocess.run(
        ["git", "merge-base", "--is-ancestor", RUNTIME_HEAD, current_head],
        cwd=REPOSITORY_ROOT,
        check=True,
    )
    if START_MARKER.exists() or RESULT_PATH.exists():
        raise RuntimeError("completion public invocation already started; refusing a second call")

    evidence = json.loads(REQUEST_EVIDENCE.read_text(encoding="utf-8"))
    replay = _load_replay_module()
    request, facts = replay._build_request_and_projection()
    if replay._make_evidence(facts) != evidence:
        raise RuntimeError("frozen request evidence failed in-memory replay")
    if facts["completion_sizing_request_hash"] != evidence["completion_sizing_request_hash"]:
        raise RuntimeError("native completion request hash differs from frozen evidence")

    marker = {
        "schema_version": "task173.full-sizing-completion-execution-start.v1",
        "runtime_source_head": RUNTIME_HEAD,
        "request_freeze_head": FREEZE_HEAD,
        "completion_sizing_request_hash": facts["completion_sizing_request_hash"],
        "historical_r4_public_sizing_invocation_count": 2,
        "completion_request_public_sizing_invocation_count": 1,
        "total_recorded_task173_public_sizing_invocations": 3,
        "execution_status": "STARTED",
        "started_at_utc": datetime.now(UTC).isoformat(),
    }
    with START_MARKER.open("x", encoding="utf-8") as handle:
        json.dump(marker, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")

    print("COMPLETION_REQUEST_FROZEN=true", flush=True)
    print("PUBLIC_SIZING_EXECUTION_AUTHORIZED=true", flush=True)
    print("COMPLETION_REQUEST_PUBLIC_SIZING_INVOCATION_COUNT=1", flush=True)
    print("COMPLETION_SIZING_REQUEST_HASH=" + facts["completion_sizing_request_hash"], flush=True)
    try:
        outcome = sizing_service.validate_sizing_request(request)
        outcome_projection = outcome.model_dump(mode="json")
        result = {
            **marker,
            "execution_status": "RETURNED",
            "returned_at_utc": datetime.now(UTC).isoformat(),
            "sizing_result_type": type(outcome).__name__,
            "sizing_status": getattr(outcome, "status", None),
            "sizing_result_id": getattr(outcome, "result_id", None),
            "sizing_result_hash": getattr(outcome, "result_hash", None),
            "sizing_result_projection": outcome_projection,
        }
        RESULT_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print("SIZING_RESULT_TYPE=" + type(outcome).__name__, flush=True)
        print("SIZING_STATUS=" + str(getattr(outcome, "status", None)), flush=True)
        print("SIZING_RESULT_ID=" + str(getattr(outcome, "result_id", None)), flush=True)
        print("SIZING_RESULT_HASH=" + str(getattr(outcome, "result_hash", None)), flush=True)
        print("COMPLETION_REQUEST_PUBLIC_SIZING_INVOCATION_COUNT=1", flush=True)
        print("TOTAL_RECORDED_TASK173_PUBLIC_SIZING_INVOCATIONS=3", flush=True)
    except Exception as exc:
        result = {
            **marker,
            "execution_status": "RAISED",
            "raised_at_utc": datetime.now(UTC).isoformat(),
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
        }
        RESULT_PATH.write_text(
            json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        raise


if __name__ == "__main__":
    main()
