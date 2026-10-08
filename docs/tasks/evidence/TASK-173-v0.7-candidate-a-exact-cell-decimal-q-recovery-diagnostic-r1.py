"""Isolated exact-cell Decimal-q feasibility diagnostic for Candidate A.

The expensive path is opt-in and calls only the private n=32 outer-boundary
entrypoint.  The default mode replays committed evidence and never invokes a
rating or sizing solver.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import runpy
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping
from dataclasses import fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal, getcontext, localcontext
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Any

import CoolProp.CoolProp as CP

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.manufacturable_candidates import service as task168
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
    Task172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    candidate_rating_request_hash,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating import (
    service as rating,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.candidate_models import (
    CandidateRatingRequest,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.candidate_materialization import (
    materialize_candidate_task171,
)
from hexagent.exchangers.shell_tube.task173_integrated_sizing.service import (
    _candidate_rating_request,
    _candidate_request_for_task174,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    Task174NativeOutputs,
)
from hexagent.exchangers.shell_tube.task174_hydraulic_orchestration import (
    validate_candidate_request as validate_task174_candidate,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.properties.base import PhaseRegion
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "STAGE3_TASK173_CANDIDATE_A_EXACT_CELL_DECIMAL_Q_RECOVERY_DIAGNOSTIC_R1"
R2_TASK_ID = "STAGE3_TASK173_DECIMAL_DIAGNOSTIC_RUNNER_HARDENING_AND_CONDITIONAL_R2_EXECUTION"
START_HEAD = "b3df78adf32b5469bdac5f6f41a50f2f0e94e8da"
R2_EXECUTION_START_HEAD = "2348b977e71d8f88f4107fceab35392962f8aa92"
RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
COMPLETION_REQUEST_HASH = "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
CANDIDATE_ID = "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
CANDIDATE_HASH = "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767"
RATING_REQUEST_HASH = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
TARGET_N = 32
TARGET_SUPPORT_ID = (
    "urn:hxforge:task171:candidate:"
    "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2"
)
TARGET_LEFT_Q = 268.4228547695099
TARGET_RIGHT_Q = 268.42285476950997
EXPECTED_N32_EVALUATIONS = 144217
EXPECTED_N32_HOLES = 27
EXPECTED_BLOCKED_RESULT_HASH = "daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c"
EXPECTED_CANDIDATE_RECEIPT_SHA256 = (
    "80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42"
)
EXPECTED_R1_DIAGNOSTIC_EVIDENCE_SHA256 = (
    "c82affab1b16d11c7e8af07e183b70125b1adefba056a9ad4ca9f1ef73504237"
)
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
R2_ARTIFACT_STEM = "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2"
R2_OUTPUT_DIR = ROOT / "docs/tasks/evidence" / f"{R2_ARTIFACT_STEM}-execution"
R2_CHECKPOINT_PATH = R2_OUTPUT_DIR / "checkpoint.json"
R2_TRACE_PATH = R2_OUTPUT_DIR / "trace.jsonl"
R2_EXECUTION_EVIDENCE_PATH = ROOT / "docs/tasks/evidence" / f"{R2_ARTIFACT_STEM}.json"
R2_PREFLIGHT_EVIDENCE_PATH = ROOT / "docs/tasks/evidence" / f"{R2_ARTIFACT_STEM}-preflight.json"
PRODUCTION_PATHS = (
    "src/hexagent/exchangers/shell_tube/manufacturable_candidates",
    "src/hexagent/exchangers/shell_tube/task172_local_runtime",
    "src/hexagent/exchangers/shell_tube/task173_integrated_rating",
    "src/hexagent/exchangers/shell_tube/task173_integrated_sizing",
    "src/hexagent/exchangers/shell_tube/task174_hydraulic_orchestration",
    "src/hexagent/exchangers/shell_tube/bell_delaware/pressure_drop.py",
    "tests/exchangers/shell_tube/test_task173_integrated_rating.py",
    "tests/exchangers/shell_tube/test_task173_integrated_sizing.py",
    "tests/exchangers/shell_tube/test_task174_hydraulic_orchestration.py",
    "uv.lock",
)
REQUEST_REPLAY = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
CANDIDATE_RUNNER = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-full-sizing-q13-correction-candidate-rating-run-r1.py"
)
CANDIDATE_RECEIPT = ROOT / (
    "docs/tasks/evidence/"
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
EVIDENCE_PATH = ROOT / (
    "docs/tasks/evidence/TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.json"
)
LIVE_CAPTURE: dict[str, Any] | None = None


class DiagnosticCheckpointStore:
    """Append-only event trace plus atomically replaced diagnostic checkpoint."""

    def __init__(self, root: Path, *, replace_fn: Any = os.replace) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path = self.root / "checkpoint.json"
        self.trace_path = self.root / "trace.jsonl"
        self.replace_fn = replace_fn
        self.event_count = 0

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        sequence = self.event_count + 1
        event = {
            "sequence": sequence,
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.event_count = sequence

    def write_checkpoint(
        self,
        capture: dict[str, Any],
        *,
        runtime_identity: dict[str, Any],
        request_identity: dict[str, Any],
    ) -> str:
        serializable_capture = {
            key: value for key, value in capture.items() if not key.startswith("_")
        }
        payload = {
            "schema_version": "task173.exact-cell-diagnostic-checkpoint.v1",
            "checkpointed_at_utc": datetime.now(UTC).isoformat(),
            "runtime_identity": runtime_identity,
            "request_identity": request_identity,
            "task172_call_count": capture.get("task172_validator_call_count", 0),
            "execution_phase": capture.get("execution_phase"),
            "current_mesh_subdivisions": capture.get("current_mesh_subdivisions"),
            "current_target_cell": capture.get("current_target_cell"),
            "last_exception": capture.get("last_exception"),
            "capture": serializable_capture,
        }
        encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
            "utf-8"
        )
        temporary_path = self.root / (f".checkpoint.{os.getpid()}.{time.monotonic_ns()}.tmp")
        try:
            with temporary_path.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            self.replace_fn(temporary_path, self.checkpoint_path)
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temporary_path.unlink(missing_ok=True)
        return _sha256(encoded)


def _task172_result_identity(
    native_request: CandidateTask172LocalRequest | Task172LocalRequest,
    native_result: Any,
) -> dict[str, Any]:
    if type(native_request) not in (CandidateTask172LocalRequest, Task172LocalRequest):
        raise TypeError(f"unsupported Task172 request type: {type(native_request).__name__}")
    if type(native_result) not in (Task172LocalResult, Task172BlockedResult):
        raise TypeError(f"unsupported Task172 result type: {type(native_result).__name__}")
    request_projection = _model_json(native_request)
    request_hash = rating.recompute_task172_request_hash(native_request)
    common = {
        "request_projection": request_projection,
        "request_hash": request_hash,
        "request_hash_replay": False,
        "result_type": type(native_result).__name__,
        "result_projection": _model_json(native_result),
    }
    if type(native_result) is Task172LocalResult:
        result_hash = rating.recompute_task172_result_hash(native_result)
        common.update(
            {
                "status": native_result.status,
                "request_hash_replay": native_result.request_hash == request_hash,
                "result_hash": result_hash,
                "result_id": native_result.result_id,
                "result_hash_replay": result_hash == native_result.result_hash,
            }
        )
        return common
    if type(native_result) is Task172BlockedResult:
        result_hash = rating.recompute_task172_blocked_result_hash(native_result)
        common.update(
            {
                "status": native_result.status,
                "request_hash_replay": native_result.request_hash == request_hash,
                "result_hash": result_hash,
                "failure_code": native_result.failure_code,
                "field_path": native_result.field_path,
                "blocked_result_hash": native_result.blocked_result_hash,
                "result_hash_replay": result_hash == native_result.blocked_result_hash,
            }
        )
        return common
    raise TypeError(f"unsupported Task172 result type: {type(native_result).__name__}")


def _record_observed_task172(
    native_request: CandidateTask172LocalRequest | Task172LocalRequest,
    native_result: Any,
    *,
    capture: dict[str, Any],
    active_target_trial: dict[str, Any] | None,
    store: DiagnosticCheckpointStore | None,
    injection_after_capture: Any = None,
) -> Any:
    """Observe an already-returned native result without replacing that result."""
    phase = capture.get("execution_phase", "UNKNOWN")
    try:
        identity = _task172_result_identity(native_request, native_result)
        if active_target_trial is not None:
            active_target_trial["task172_call"] = identity
            capture["current_target_cell"] = active_target_trial
            capture.setdefault("target_task172_calls", []).append(identity)
            if store is not None:
                try:
                    store.append_event("TARGET_TASK172_RESULT", active_target_trial.copy())
                except Exception as exc:
                    _note_diagnostic_exception(capture, "append_target_task172_trace", exc)
                try:
                    store.write_checkpoint(
                        capture,
                        runtime_identity=capture["runtime_identity"],
                        request_identity=capture["request_identity"],
                    )
                except Exception as exc:
                    _note_diagnostic_exception(capture, "target_task172_checkpoint", exc)
        if injection_after_capture is not None:
            injection_after_capture(identity)
        if not identity["request_hash_replay"] or not identity["result_hash_replay"]:
            capture["observer_identity_replay_failed"] = True
            capture["observer_fail_closed"] = True
    except Exception as exc:
        _note_diagnostic_exception(capture, phase, exc)
        capture["observer_fail_closed"] = True
        if active_target_trial is not None:
            active_target_trial["observer_capture_error"] = capture["last_exception"]
        if store is not None:
            try:
                store.append_event("OBSERVER_EXCEPTION", capture["last_exception"])
            except Exception as trace_exc:
                _note_diagnostic_exception(capture, "observer_exception_trace", trace_exc)
            try:
                store.write_checkpoint(
                    capture,
                    runtime_identity=capture["runtime_identity"],
                    request_identity=capture["request_identity"],
                )
            except Exception as checkpoint_exc:
                _note_diagnostic_exception(capture, "observer_exception_checkpoint", checkpoint_exc)
    return native_result


def _note_diagnostic_exception(capture: dict[str, Any], phase: str, exception: Exception) -> None:
    record = {
        "phase": phase,
        "type": type(exception).__name__,
        "text": str(exception),
    }
    capture["last_exception"] = record
    capture.setdefault("diagnostic_exceptions", []).append(record)


def _persist_event_and_checkpoint(
    capture: dict[str, Any],
    store: DiagnosticCheckpointStore | None,
    *,
    event_type: str,
    payload: dict[str, Any],
    checkpoint: bool,
) -> None:
    if store is None:
        return
    try:
        store.append_event(event_type, payload)
    except Exception as exc:
        _note_diagnostic_exception(capture, f"append_trace:{event_type}", exc)
    if checkpoint:
        try:
            store.write_checkpoint(
                capture,
                runtime_identity=capture["runtime_identity"],
                request_identity=capture["request_identity"],
            )
            capture["last_successful_checkpoint_call_count"] = capture.get(
                "task172_validator_call_count", 0
            )
        except Exception as exc:
            _note_diagnostic_exception(capture, f"checkpoint:{event_type}", exc)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode(
        "utf-8"
    )
    temporary_path = path.parent / f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    try:
        with temporary_path.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary_path.unlink(missing_ok=True)
    return _sha256(encoded)


def _iter_mappings(value: Any):
    if isinstance(value, dict):
        yield value
        for item in value.values():
            yield from _iter_mappings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_mappings(item)


def _load_saved_task172_fixture() -> tuple[Task172LocalRequest, Task172LocalResult]:
    evidence_path = ROOT / (
        "docs/tasks/evidence/"
        "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
    )
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    saved_result_projection = next(
        (
            event["endpoint_result_projection_left"]
            for event in _iter_mappings(evidence)
            if "endpoint_result_projection_left" in event
        ),
        None,
    )
    if saved_result_projection is None:
        raise RuntimeError("saved R2A Task172 result fixture is unavailable")
    test_module = runpy.run_path(
        str(ROOT / "tests/exchangers/shell_tube/test_task172_local_runtime.py")
    )
    request = test_module["_request"]()
    if type(request) is not Task172LocalRequest:
        raise TypeError("Task172 preflight factory did not return the exact native request")
    request_hash = rating.recompute_task172_request_hash(request)
    saved_result = Task172LocalResult.model_validate(
        _restore_pairs(saved_result_projection), strict=False
    )
    pending_result = saved_result.model_copy(
        update={
            "request_hash": request_hash,
            "result_hash": "0" * 64,
            "result_id": "urn:hxforge:task172:preflight-pending",
        }
    )
    result_hash = rating.recompute_task172_result_hash(pending_result)
    result = pending_result.model_copy(
        update={
            "result_hash": result_hash,
            "result_id": f"urn:hxforge:task172:{result_hash}",
        }
    )
    if (
        type(result) is not Task172LocalResult
        or rating.recompute_task172_result_hash(result) != result.result_hash
        or result.request_hash != request_hash
    ):
        raise RuntimeError("synthetic Pydantic Task172 valid fixture identity failed")
    return request, result


def _preflight_frozen_identities() -> dict[str, Any]:
    r1_raw = EVIDENCE_PATH.read_bytes()
    receipt_raw = CANDIDATE_RECEIPT.read_bytes()
    if _sha256(r1_raw) != EXPECTED_R1_DIAGNOSTIC_EVIDENCE_SHA256:
        raise RuntimeError("R1 diagnostic evidence raw identity changed")
    if _sha256(receipt_raw) != EXPECTED_CANDIDATE_RECEIPT_SHA256:
        raise RuntimeError("frozen Candidate A receipt raw identity changed")
    receipt = json.loads(receipt_raw)
    frozen_candidate = receipt["candidates"][CANDIDATE_ID]
    if (
        receipt["completion_request_hash"] != COMPLETION_REQUEST_HASH
        or receipt["task168_candidate_space_hash"] != TASK168_SPACE_HASH
        or frozen_candidate["candidate_rating_request_hash"] != RATING_REQUEST_HASH
        or frozen_candidate["result_hash"] != EXPECTED_BLOCKED_RESULT_HASH
    ):
        raise RuntimeError("R1 frozen Candidate A identities changed")
    replay = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--replay-only"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if replay.returncode or "DIAGNOSTIC_ATTEMPT_RECEIPT_HASH_REPLAY=PASS" not in replay.stdout:
        raise RuntimeError(f"R1 evidence replay failed: {replay.stderr.strip()}")
    if "EXACT_TARGET_CELL_EVIDENCE_REPLAY=NOT_ESTABLISHED" not in replay.stdout:
        raise RuntimeError("R1 historical failure status was not preserved")
    request_replay = subprocess.run(
        [sys.executable, str(REQUEST_REPLAY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if request_replay.returncode or "ALL_COMPLETION_REQUEST_REPLAY_PASS=true" not in (
        request_replay.stdout
    ):
        raise RuntimeError(f"frozen completion request replay failed: {request_replay.stderr}")
    runtime_binding = _assert_runtime_binding(execution=False)
    r2a = json.loads(
        (
            ROOT
            / "docs/tasks/evidence/"
            / "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
        ).read_text(encoding="utf-8")
    )
    if r2a["authority_candidate"]["canonical_hash"] != R2A_AUTHORITY_HASH:
        raise RuntimeError("reviewed R2A authority frozen identity changed")
    return {
        "r1_diagnostic_evidence_sha256": _sha256(r1_raw),
        "candidate_receipt_sha256": _sha256(receipt_raw),
        "completion_request_hash": receipt["completion_request_hash"],
        "candidate_rating_request_hash": frozen_candidate["candidate_rating_request_hash"],
        "blocked_result_hash": frozen_candidate["result_hash"],
        "task168_candidate_space_hash": receipt["task168_candidate_space_hash"],
        "reviewed_r2a_authority_hash": R2A_AUTHORITY_HASH,
        "legacy_r1_failure_replay": replay.stdout.strip().splitlines(),
        "completion_request_replay": request_replay.stdout.strip().splitlines(),
        "runtime_binding": runtime_binding,
    }


def _run_preflight() -> dict[str, Any]:
    """Exercise native Task172 observer/probe/checkpoint paths without solving."""
    checks: dict[str, Any] = {}
    frozen_facts = _preflight_frozen_identities()
    fixture_request, fixture_valid = _load_saved_task172_fixture()
    request_hash = rating.recompute_task172_request_hash(fixture_request)
    valid_identity = _task172_result_identity(fixture_request, fixture_valid)
    if (
        fixture_valid.status != "VALIDATED"
        or not valid_identity["request_hash_replay"]
        or not valid_identity["result_hash_replay"]
        or valid_identity["result_hash"] != fixture_valid.result_hash
    ):
        raise RuntimeError("saved valid Task172 fixture identity replay failed")

    capture: dict[str, Any] = {
        "runtime_identity": {"head": R2_EXECUTION_START_HEAD},
        "request_identity": {"request_hash": RATING_REQUEST_HASH},
        "execution_phase": "PREFLIGHT_OBSERVER_VALID_RESULT",
        "task172_validator_call_count": 0,
    }
    returned = _record_observed_task172(
        fixture_request,
        fixture_valid,
        capture=capture,
        active_target_trial={},
        store=None,
    )
    if returned is not fixture_valid:
        raise RuntimeError("valid-result observer replaced the native result")
    valid_observation = capture["target_task172_calls"][0]
    if (
        valid_observation["result_id"] != fixture_valid.result_id
        or not valid_observation["request_hash_replay"]
        or not valid_observation["result_hash_replay"]
    ):
        raise RuntimeError("valid-result observer identity replay failed")
    checks["OBSERVER_VALID_RESULT_TEST"] = "PASS"

    blocked_unhashed = Task172BlockedResult(
        status="BLOCKED",
        failure_code="PREFLIGHT_BLOCKED_FIXTURE",
        field_path="diagnostic.preflight",
        request_hash=request_hash,
        diagnostic_last_iterate=("synthetic preflight only",),
        blockers=("PREFLIGHT_BLOCKED_FIXTURE",),
        blocked_result_hash="0" * 64,
    )
    fixture_blocked = blocked_unhashed.model_copy(
        update={
            "blocked_result_hash": rating.recompute_task172_blocked_result_hash(blocked_unhashed)
        }
    )
    blocked_capture: dict[str, Any] = {
        "runtime_identity": {"head": R2_EXECUTION_START_HEAD},
        "request_identity": {"request_hash": RATING_REQUEST_HASH},
        "execution_phase": "PREFLIGHT_OBSERVER_BLOCKED_RESULT",
        "task172_validator_call_count": 0,
    }
    blocked_returned = _record_observed_task172(
        fixture_request,
        fixture_blocked,
        capture=blocked_capture,
        active_target_trial={},
        store=None,
    )
    blocked_observation = blocked_capture["target_task172_calls"][0]
    if (
        blocked_returned is not fixture_blocked
        or "result_id" in blocked_observation
        or blocked_observation["failure_code"] != fixture_blocked.failure_code
        or blocked_observation["field_path"] != fixture_blocked.field_path
        or blocked_observation["blocked_result_hash"] != fixture_blocked.blocked_result_hash
        or not blocked_observation["request_hash_replay"]
        or not blocked_observation["result_hash_replay"]
    ):
        raise RuntimeError("blocked-result observer identity replay failed")
    checks["OBSERVER_BLOCKED_RESULT_TEST"] = "PASS"

    probe_capture: dict[str, Any] = {"decimal_q_probe_in_progress": {}}
    captured_probe_return = _capture_decimal_probe_result(
        probe_capture,
        _task172_result_identity(fixture_request, fixture_blocked),
        fixture_blocked,
    )
    probe_record: dict[str, Any] = {
        "task172_request_hash": request_hash,
        "task172_support_hash": rating.recompute_task172_support_id(fixture_request),
    }
    _record_probe_task172_result(
        probe_record,
        fixture_request,
        fixture_blocked,
        Decimal("1.0000000000000000000000000001"),
    )
    if (
        "task172_result_id" in probe_record
        or "result_id" in captured_probe_return
        or captured_probe_return["failure_code"] != fixture_blocked.failure_code
        or captured_probe_return["field_path"] != fixture_blocked.field_path
        or captured_probe_return["blocked_result_hash"] != fixture_blocked.blocked_result_hash
        or probe_capture["decimal_q_probe_in_progress"]["native_result_returned"]
        != captured_probe_return
        or probe_record.get("task172_failure_code") != fixture_blocked.failure_code
        or probe_record.get("task172_field_path") != fixture_blocked.field_path
        or probe_record.get("task172_result_hash") != fixture_blocked.blocked_result_hash
        or not probe_record.get("task172_request_hash_replay")
        or not probe_record.get("task172_result_hash_replay")
    ):
        raise RuntimeError("Decimal probe blocked-result processing path failed")
    checks["DECIMAL_PROBE_BLOCKED_RESULT_TEST"] = "PASS"

    unknown_capture: dict[str, Any] = {
        "runtime_identity": {"head": R2_EXECUTION_START_HEAD},
        "request_identity": {"request_hash": RATING_REQUEST_HASH},
        "execution_phase": "PREFLIGHT_UNKNOWN_RESULT",
    }
    unknown = object()
    unknown_returned = _record_observed_task172(
        fixture_request,
        unknown,
        capture=unknown_capture,
        active_target_trial={},
        store=None,
    )
    try:
        _record_probe_task172_result(
            {"task172_request_hash": request_hash},
            fixture_request,
            unknown,
            Decimal("1"),
        )
    except TypeError:
        probe_unknown_failed_closed = True
    else:
        probe_unknown_failed_closed = False
    if (
        unknown_returned is not unknown
        or unknown_capture.get("observer_fail_closed") is not True
        or unknown_capture.get("last_exception", {}).get("type") != "TypeError"
        or not probe_unknown_failed_closed
    ):
        raise RuntimeError("unknown Task172 result type did not fail closed")
    checks["UNKNOWN_TYPE_FAIL_CLOSED"] = "PASS"

    exception_capture: dict[str, Any] = {
        "runtime_identity": {"head": R2_EXECUTION_START_HEAD},
        "request_identity": {"request_hash": RATING_REQUEST_HASH},
        "execution_phase": "PREFLIGHT_OBSERVER_EXCEPTION",
    }

    def inject_observer_exception(_: dict[str, Any]) -> None:
        raise RuntimeError("injected observer-only exception")

    exception_returned = _record_observed_task172(
        fixture_request,
        fixture_valid,
        capture=exception_capture,
        active_target_trial={},
        store=None,
        injection_after_capture=inject_observer_exception,
    )
    if (
        exception_returned is not fixture_valid
        or len(exception_capture.get("target_task172_calls", [])) != 1
        or exception_capture.get("last_exception", {}).get("type") != "RuntimeError"
    ):
        raise RuntimeError("observer exception lost partial evidence or changed result")
    checks["OBSERVER_EXCEPTION_RECOVERY"] = "PASS"

    with tempfile.TemporaryDirectory(prefix="task173-r2-checkpoint-preflight-") as temp_dir:
        preflight_store = DiagnosticCheckpointStore(Path(temp_dir))
        checkpoint_capture: dict[str, Any] = {
            "runtime_identity": {"head": R2_EXECUTION_START_HEAD},
            "request_identity": {"request_hash": RATING_REQUEST_HASH},
            "execution_phase": "PREFLIGHT_CHECKPOINT_INTERRUPTION",
            "task172_validator_call_count": 1,
        }
        preflight_store.write_checkpoint(
            checkpoint_capture,
            runtime_identity=checkpoint_capture["runtime_identity"],
            request_identity=checkpoint_capture["request_identity"],
        )
        old_checkpoint = preflight_store.checkpoint_path.read_bytes()
        original_replace = preflight_store.replace_fn
        one_shot_failure = {"remaining": 1}

        def fail_one_checkpoint(source: Path, destination: Path) -> None:
            if one_shot_failure["remaining"]:
                one_shot_failure["remaining"] -= 1
                raise OSError("injected checkpoint replace interruption")
            original_replace(source, destination)

        preflight_store.replace_fn = fail_one_checkpoint
        checkpoint_returned = _record_observed_task172(
            fixture_request,
            fixture_valid,
            capture=checkpoint_capture,
            active_target_trial={},
            store=preflight_store,
        )
        checkpoint_preserved = (
            preflight_store.checkpoint_path.read_bytes() == old_checkpoint
            and checkpoint_capture.get("last_exception", {}).get("type") == "OSError"
            and len(checkpoint_capture.get("target_task172_calls", [])) == 1
            and checkpoint_returned is fixture_valid
        )
        preflight_store.replace_fn = original_replace
        preflight_store.write_checkpoint(
            checkpoint_capture,
            runtime_identity=checkpoint_capture["runtime_identity"],
            request_identity=checkpoint_capture["request_identity"],
        )
        recovered_checkpoint = json.loads(
            preflight_store.checkpoint_path.read_text(encoding="utf-8")
        )
        if not checkpoint_preserved or not recovered_checkpoint["capture"].get(
            "target_task172_calls"
        ):
            raise RuntimeError("checkpoint exception did not preserve/recover partial evidence")
    checks["CHECKPOINT_EXCEPTION_RECOVERY"] = "PASS"

    checks["R1_FROZEN_IDENTITIES_PRESERVED"] = "PASS"
    checks["PRODUCTION_CODE_CHANGED"] = "false"
    return {
        "schema_version": "task173.decimal-q-diagnostic-r2-preflight.v1",
        "task_id": R2_TASK_ID,
        "execution_start_head": R2_EXECUTION_START_HEAD,
        "preflight_only": True,
        "numeric_solver_invoked": False,
        "full_candidate_rating_invoked": False,
        "public_sizing_invoked": False,
        "frozen_identity_facts": frozen_facts,
        "fixture_request_hash": request_hash,
        "fixture_result_hash": fixture_valid.result_hash,
        "blocked_fixture_hash": fixture_blocked.blocked_result_hash,
        "preflight_fixture_provenance": {
            "valid_request_factory": (
                "tests.exchangers.shell_tube.test_task172_local_runtime._request"
            ),
            "valid_result_source": (
                "committed R2A Task172 result projection; rebound only to the test-native "
                "request hash and rehashed with the native Task172 result hash function"
            ),
            "valid_result_status": fixture_valid.status,
            "valid_result_model_type": type(fixture_valid).__name__,
            "blocked_result_fixture": "native Task172BlockedResult constructed without solver",
            "numeric_solver_invoked": False,
        },
        "checks": checks,
        "preflight_result": "PASS",
    }


def _record_probe_task172_result(
    record: dict[str, Any],
    native_request: CandidateTask172LocalRequest | Task172LocalRequest,
    native_result: Any,
    q: Decimal,
) -> None:
    identity = _task172_result_identity(native_request, native_result)
    if record.get("task172_request_hash") != identity["request_hash"]:
        raise RuntimeError("native Task172 probe request hash differs from captured request")
    record.update(
        {
            "task172_result_type": identity["result_type"],
            "task172_result_projection": identity["result_projection"],
            "task172_status": identity["status"],
            "task172_request_hash_replay": identity["request_hash_replay"],
            "task172_result_hash": identity["result_hash"],
            "task172_result_hash_replay": identity["result_hash_replay"],
        }
    )
    if not identity["request_hash_replay"] or not identity["result_hash_replay"]:
        raise RuntimeError("native Task172 probe request/result hash replay failed")
    if type(native_result) is Task172LocalResult:
        if (
            native_result.status != "VALIDATED"
            or native_result.physical_support_id != record["task172_support_hash"]
            or native_result.physical_segment_id != native_request.support.physical_segment_id
            or native_result.tube_cell_id != native_request.support.tube_cell_id
            or native_result.shell_cell_id != native_request.support.shell_cell_id
            or native_result.wall_interface_id != native_request.support.wall_interface_id
        ):
            raise RuntimeError("native Task172 valid probe identity/preflight mismatch")
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            exact_f = q - native_result.signed_q_hot_to_cold_w
        record.update(
            {
                "task172_result_id": native_result.result_id,
                "task172_signed_q_hot_to_cold_w": str(native_result.signed_q_hot_to_cold_w),
                "F_decimal_high_precision": str(exact_f),
                "F_native_contract_context": str(exact_f),
                "ordinary_point_root_tolerance_pass": abs(exact_f) <= Decimal("1e-6"),
            }
        )
        return
    if type(native_result) is Task172BlockedResult:
        record.update(
            {
                "task172_failure_code": native_result.failure_code,
                "task172_field_path": native_result.field_path,
                "task172_blocked_result_hash": native_result.blocked_result_hash,
            }
        )
        return
    raise TypeError(f"unsupported Task172 probe result: {type(native_result).__name__}")


def _capture_decimal_probe_result(
    capture: dict[str, Any], identity: dict[str, Any], native_result: Any
) -> dict[str, Any]:
    """Capture the exact Decimal-probe return branch with strict native typing."""
    common = {
        "result_type": identity["result_type"],
        "result_projection": identity["result_projection"],
        "result_hash": identity["result_hash"],
        "request_hash_replay": identity["request_hash_replay"],
        "result_hash_replay": identity["result_hash_replay"],
    }
    if type(native_result) is Task172BlockedResult:
        common.update(
            {
                "failure_code": native_result.failure_code,
                "field_path": native_result.field_path,
                "blocked_result_hash": native_result.blocked_result_hash,
            }
        )
    elif type(native_result) is Task172LocalResult:
        common["result_id"] = native_result.result_id
    else:
        raise TypeError(f"unsupported Task172 probe result: {type(native_result).__name__}")
    capture["decimal_q_probe_in_progress"]["native_result_returned"] = common
    return common


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _native_projection(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if type(value) is ReferencePlanePair:
        return {"start": value.start.value, "end": value.end.value, "kind": value.kind}
    model_fields = getattr(type(value), "model_fields", None)
    if model_fields is not None:
        return {name: _native_projection(getattr(value, name)) for name in model_fields}
    if is_dataclass(value):
        return {
            field.name: _native_projection(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): _native_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_native_projection(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported native diagnostic value: {type(value).__name__}")


def _model_json(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", fallback=rating._candidate_json_fallback)


def _assert_runtime_binding(*, execution: bool) -> dict[str, Any]:
    head = _git("rev-parse", "HEAD")
    if execution and head != R2_EXECUTION_START_HEAD:
        raise RuntimeError(f"R2 execution requires exact start HEAD: {head}")
    _git("merge-base", "--is-ancestor", RUNTIME_HEAD, head)
    actual_tree = _git("rev-parse", f"{RUNTIME_HEAD}^{{tree}}")
    if actual_tree != RUNTIME_TREE:
        raise RuntimeError("frozen production runtime tree mismatch")
    diff = subprocess.run(
        ["git", "diff", "--quiet", RUNTIME_HEAD, head, "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    if diff.returncode:
        raise RuntimeError("runtime paths differ between frozen source and current HEAD")
    dirty = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--", *PRODUCTION_PATHS],
        cwd=ROOT,
        check=False,
    )
    if dirty.returncode or staged.returncode:
        raise RuntimeError("bound runtime paths are dirty")
    return {
        "current_head": head,
        "current_tree": _git("rev-parse", "HEAD^{tree}"),
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": actual_tree,
        "runtime_paths_byte_identical": True,
        "bound_runtime_worktree_clean": True,
    }


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load evidence helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _reconstruct_candidate_a() -> tuple[CandidateRatingRequest, dict[str, Any]]:
    started_wall = time.monotonic()
    started_cpu = time.process_time()
    request_replay = _load_module("task173_completion_request_replay", REQUEST_REPLAY)
    sizing_request, request_facts = request_replay._build_request_and_projection()
    if (
        request_facts["completion_sizing_request_hash"] != COMPLETION_REQUEST_HASH
        or request_facts["candidate_space_hash"] != TASK168_SPACE_HASH
    ):
        raise RuntimeError("frozen completion request or TASK168 space mismatch")
    task168_request = sizing_request.task168_candidate_request
    authority_map = task168._authority_map(task168_request)
    dimensions = tuple(
        task168._sort_values(authority_map[role].values)
        for role in task168.DIMENSION_ORDER
        if role != "SHELL_GEOMETRY_ID"
    )
    candidate = None
    bundle = None
    selected_combination: tuple[Any, ...] | None = None
    for combination in product(task168_request.shell_geometry_catalog.records, *dimensions):
        candidate_trial = task168._candidate(
            task168_request, authority_map, combination[0], tuple(combination[1:])
        )
        if candidate_trial.candidate_id == CANDIDATE_ID:
            candidate = candidate_trial
            selected_combination = combination
            bundle, stage_failure, _ = task168._execute_candidate_chain(
                task168_request,
                candidate,
                combination[0],
                include_legacy_task162=False,
                include_legacy_task168_rating_dependencies=False,
                preserve_baffle_orientation_sequence=True,
            )
            if stage_failure is not None:
                raise RuntimeError(f"Candidate A upstream chain blocked: {stage_failure!r}")
            break
    if candidate is None or bundle is None or selected_combination is None:
        raise RuntimeError("frozen Candidate A not found in reconstructed TASK168 space")
    if candidate.candidate_hash != CANDIDATE_HASH:
        raise RuntimeError("Candidate A identity mismatch")
    topology = materialize_candidate_task171(
        candidate=candidate,
        configuration=bundle.task020_configuration,
        layout=bundle.task021_layout,
        bundle_geometry=bundle.task022_geometry,
        baffle_geometry=bundle.task024_geometry,
        task025_result=bundle.task025_result,
        task024_request=bundle.task024_request,
        task025_request=bundle.task025_request,
    )
    task174_request = _candidate_request_for_task174(candidate, bundle, topology)
    task174 = validate_task174_candidate(
        task174_request,
        Task174NativeOutputs(
            task029=bundle.task029_result,
            task034=None,
            task166=bundle.task166_result,
        ),
    )
    if task174.status != "VALIDATED":
        raise RuntimeError("Candidate A TASK174 is not VALIDATED")
    request = _candidate_rating_request(
        candidate,
        TASK168_SPACE_HASH,
        bundle,
        topology,
        task174,
        COMPLETION_REQUEST_HASH,
    )
    actual_hash = candidate_rating_request_hash(request)
    if actual_hash != RATING_REQUEST_HASH:
        raise RuntimeError(f"Candidate A rating request mismatch: {actual_hash}")
    return request, {
        "candidate_id": candidate.candidate_id,
        "candidate_hash": candidate.candidate_hash,
        "rating_request_hash": actual_hash,
        "candidate_rating_request_projection_sha256": _sha256(
            json.dumps(
                _native_projection(request),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8")
        ),
        "upstream_candidate_chain_count": 1,
        "task174_candidate_validation_count": 1,
        "candidate_b_materialized": False,
        "candidate_a_upstream_preparation_wall_seconds": time.monotonic() - started_wall,
        "candidate_a_upstream_preparation_cpu_seconds": time.process_time() - started_cpu,
    }


def _context_snapshot(provider: CoolPropProvider | None = None) -> dict[str, Any]:
    decimal_context = getcontext()
    return {
        "captured_at_utc": datetime.now(UTC).isoformat(),
        "python_version": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "decimal_context": {
            "prec": decimal_context.prec,
            "rounding": decimal_context.rounding,
            "Emax": decimal_context.Emax,
            "Emin": decimal_context.Emin,
            "clamp": decimal_context.clamp,
            "capitals": decimal_context.capitals,
            "traps": {item.__name__: bool(value) for item, value in decimal_context.traps.items()},
            "flags": {item.__name__: bool(value) for item, value in decimal_context.flags.items()},
        },
        "environment": {
            name: os.environ.get(name) for name in ("PYTHONHASHSEED", "TZ", "LC_ALL", "LANG")
        },
        "coolprop": {
            "package_version": (
                str(CP.get_global_param_string("version")) if provider is None else provider.version
            ),
            "git_revision": (
                str(CP.get_global_param_string("gitrevision"))
                if provider is None
                else provider.git_revision
            ),
            "backend": "HEOS::Water",
            "reference_state": "DEF",
            "provider_name": "CoolProp",
            "allow_unvalidated_fluids": (
                None if provider is None else provider.allow_unvalidated_fluids
            ),
            "near_saturation_relative_tolerance": (
                None if provider is None else provider.near_saturation_relative_tolerance
            ),
            "cache_size": None if provider is None else provider.cache_size,
            "configuration_fingerprint": (
                None if provider is None else provider._construction_fingerprint
            ),
        },
        "runtime_head": _git("rev-parse", "HEAD"),
        "runtime_tree": _git("rev-parse", "HEAD^{tree}"),
    }


def _capture_state(state: Any) -> dict[str, Any]:
    return {
        "native": _native_projection(state.native),
        "property_snapshot": state.snapshot.model_dump(mode="json"),
        "property_snapshot_hash": state.snapshot_hash,
    }


def _run_exact_n32(
    request: CandidateRatingRequest,
    provider: CoolPropProvider,
    *,
    store: DiagnosticCheckpointStore,
    runtime_identity: dict[str, Any],
    request_identity: dict[str, Any],
) -> dict[str, Any]:
    global LIVE_CAPTURE
    expected_result = json.loads(CANDIDATE_RECEIPT.read_text(encoding="utf-8"))["candidates"][
        CANDIDATE_ID
    ]["result_projection"]
    if expected_result["result_hash"] != EXPECTED_BLOCKED_RESULT_HASH:
        raise RuntimeError("frozen Candidate A blocked receipt mismatch")
    context = rating._candidate_context(request)
    stats = rating._CellSearchStats()
    capture: dict[str, Any] = {
        "target_cell_trials": [],
        "transient_events": [],
        "failure": None,
        "task172_validator_call_count": 0,
        "provider_state_ph_call_count": 0,
        "target_support_seen": False,
        "execution_phase": "N32_ACCEPTED_TRAJECTORY_RECONSTRUCTION",
        "current_mesh_subdivisions": TARGET_N,
        "runtime_identity": runtime_identity,
        "request_identity": request_identity,
        "diagnostic_exceptions": [],
    }
    LIVE_CAPTURE = capture
    _persist_event_and_checkpoint(
        capture,
        store,
        event_type="N32_RECONSTRUCTION_STARTED",
        payload={
            "candidate_id": CANDIDATE_ID,
            "candidate_hash": CANDIDATE_HASH,
            "rating_request_hash": RATING_REQUEST_HASH,
            "mesh_subdivisions": TARGET_N,
            "target_support_id": TARGET_SUPPORT_ID,
        },
        checkpoint=True,
    )
    active_target_trial: dict[str, Any] | None = None
    native_target_objects: dict[str, Any] = {}
    original_solve_cell = rating._solve_cell
    original_cell_evaluation = rating._cell_evaluation
    original_task172_candidate = rating.task172_validate_candidate
    original_event = rating._candidate_provider_enclosure_event

    def observed_task172(
        native_request: CandidateTask172LocalRequest | Task172LocalRequest,
        active_provider: Any,
    ) -> Any:
        capture["task172_validator_call_count"] += 1
        if capture["task172_validator_call_count"] % 10000 == 0:
            print(
                f"ISOLATED_N32_TASK172_CALLS={capture['task172_validator_call_count']}",
                flush=True,
            )
        capture["execution_phase"] = "N32_TASK172_VALIDATION"
        try:
            result = original_task172_candidate(native_request, active_provider)
        except Exception as exc:
            _note_diagnostic_exception(capture, "native_task172_validation", exc)
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="TASK172_VALIDATION_EXCEPTION",
                payload=capture["last_exception"],
                checkpoint=True,
            )
            raise
        if active_target_trial is not None:
            _record_observed_task172(
                native_request,
                result,
                capture=capture,
                active_target_trial=active_target_trial,
                store=store,
            )
        elif capture["task172_validator_call_count"] % 10000 == 0:
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="TASK172_PROGRESS",
                payload={
                    "task172_call_count": capture["task172_validator_call_count"],
                    "phase": capture.get("execution_phase"),
                },
                checkpoint=True,
            )
        return result

    def observed_event(*args: Any, **kwargs: Any) -> Any:
        result = original_event(*args, **kwargs)
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        if result is not None:
            try:
                event_record = {
                    "event_hash": result.get("event_hash"),
                    "mode": control.mode if control is not None else None,
                    "mesh_subdivisions": (
                        control.mesh_subdivisions if control is not None else None
                    ),
                    "outer_iteration": control.outer_iteration if control is not None else None,
                    "shooting_enthalpy_j_kg": (
                        str(control.shooting_enthalpy) if control is not None else None
                    ),
                    "physical_support_id": result.get("physical_support_id"),
                }
                capture["transient_events"].append(event_record)
                _persist_event_and_checkpoint(
                    capture,
                    store,
                    event_type="R2A_TRANSIENT_EVENT",
                    payload=event_record,
                    checkpoint=True,
                )
            except Exception as exc:
                _note_diagnostic_exception(capture, "observe_r2a_event", exc)
        return result

    original_canonical_sha256 = rating.canonical_sha256

    def observed_canonical_sha256(value: Any) -> str:
        digest = original_canonical_sha256(value)
        if (
            isinstance(value, dict)
            and value.get("schema_version")
            == "task173.r2a.production-outer-decision-certificate.v1"
        ):
            try:
                capture.setdefault("transient_outer_decision_certificates", []).append(
                    {
                        "projection": json.loads(json.dumps(value)),
                        "certificate_hash": digest,
                    }
                )
            except Exception as exc:
                _note_diagnostic_exception(capture, "observe_outer_certificate", exc)
        return digest

    def observed_cell_evaluation(q_w: float, **kwargs: Any) -> Any:
        nonlocal active_target_trial
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        support = kwargs["support"]
        is_target = (
            control is not None
            and control.mode == "DISABLED"
            and control.mesh_subdivisions == TARGET_N
            and support.physical_segment_id == TARGET_SUPPORT_ID
        )
        if not is_target:
            return original_cell_evaluation(q_w, **kwargs)
        capture["target_support_seen"] = True
        trial: dict[str, Any] = {
            "q_w_repr": repr(q_w),
            "q_w_binary64_hex": float(q_w).hex(),
            "production_q_decimal": str(rating._d(q_w)),
            "exact_binary64_decimal": str(Decimal.from_float(float(q_w))),
            "control_mode": control.mode,
            "mesh_subdivisions": control.mesh_subdivisions,
            "outer_iteration": kwargs.get("outer_iteration"),
            "shooting_enthalpy_j_kg": str(kwargs.get("shooting_enthalpy")),
            "support_projection": _native_projection(support),
            "tube_upstream_state": _capture_state(kwargs["tube_upstream"]),
            "shell_physical_left_state": _capture_state(kwargs["shell_physical_left"]),
            "provider_ph_calls": [],
        }
        native_target_objects.update(
            {
                "support": support,
                "tube_upstream": kwargs["tube_upstream"],
                "shell_physical_left": kwargs["shell_physical_left"],
            }
        )
        active_target_trial = trial
        capture["current_target_cell"] = trial
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="TARGET_CELL_TRIAL_STARTED",
            payload=trial,
            checkpoint=True,
        )
        original_state_from_enthalpy = rating._state_from_enthalpy

        def observed_state_from_enthalpy(
            state_provider: Any, enthalpy: Decimal, **state_kwargs: Any
        ) -> Any:
            state = original_state_from_enthalpy(state_provider, enthalpy, **state_kwargs)
            try:
                provider_float = float(enthalpy)
                input_record = {
                    "enthalpy_decimal_before_float": str(enthalpy),
                    "provider_enthalpy_float": provider_float,
                    "provider_enthalpy_float_hex": provider_float.hex(),
                    "decimal_from_provider_float": str(Decimal.from_float(provider_float)),
                    "shell_search_state": state_kwargs.get("shell_search_state", False),
                    "state_after_provider": _capture_state(state),
                }
                trial["provider_ph_calls"].append(input_record)
                capture["provider_state_ph_call_count"] += 1
            except Exception as exc:
                capture["observer_fail_closed"] = True
                trial["provider_capture_error"] = {
                    "type": type(exc).__name__,
                    "text": str(exc),
                }
                _note_diagnostic_exception(capture, "observe_provider_ph_state", exc)
            return state

        try:
            rating._state_from_enthalpy = observed_state_from_enthalpy
            result = original_cell_evaluation(q_w, **kwargs)
        except rating._Task172NumericalHole as exc:
            trial["cell_evaluation_status"] = "TASK172_NUMERICAL_HOLE"
            try:
                trial["task172_hole"] = {
                    "request_hash": exc.request_hash,
                    "blocked_result_hash": exc.blocked_result_hash,
                    "request_hash_replay_passed": exc.request_hash_replay_passed,
                    "blocked_result_hash_replay_passed": exc.blocked_result_hash_replay_passed,
                    "exact_blocked_result_type": exc.exact_blocked_result_type,
                }
            except Exception as capture_exc:
                _note_diagnostic_exception(capture, "observe_task172_hole", capture_exc)
            raise
        except BaseException as exc:
            trial["cell_evaluation_status"] = "RAISED"
            try:
                trial["exception_type"] = type(exc).__name__
                trial["exception_text"] = str(exc)
            except Exception as capture_exc:
                _note_diagnostic_exception(capture, "observe_cell_exception", capture_exc)
            raise
        else:
            trial["cell_evaluation_status"] = "VALIDATED"
            try:
                trial["task172_status"] = result.task172_result.status
                trial["task172_signed_q_hot_to_cold_w"] = str(
                    result.task172_result.signed_q_hot_to_cold_w
                )
                trial["f_production_decimal_context"] = str(
                    rating._d(q_w) - result.task172_result.signed_q_hot_to_cold_w
                )
                with localcontext() as decimal_context:
                    decimal_context.prec = 100
                    trial["f_exact_binary64_endpoint"] = str(
                        Decimal.from_float(float(q_w))
                        - result.task172_result.signed_q_hot_to_cold_w
                    )
                trial["task172_request_hash"] = rating.recompute_task172_request_hash(
                    result.task172_request
                )
                trial["task172_result_hash"] = result.task172_result.result_hash
                trial["task172_request_projection"] = _model_json(result.task172_request)
                trial["task172_result_projection"] = _model_json(result.task172_result)
                trial["cell_states"] = {
                    "tube_downstream": _capture_state(result.tube_downstream),
                    "shell_next_physical": _capture_state(result.shell_next_physical),
                    "tube_local": _capture_state(result.tube_local),
                    "shell_local": _capture_state(result.shell_local),
                }
            except Exception as exc:
                capture["observer_fail_closed"] = True
                trial["observer_capture_error"] = {
                    "type": type(exc).__name__,
                    "text": str(exc),
                }
                _note_diagnostic_exception(capture, "observe_validated_cell", exc)
            return result
        finally:
            rating._state_from_enthalpy = original_state_from_enthalpy
            active_target_trial = None
            capture["target_cell_trial_count"] = len(capture["target_cell_trials"]) + 1
            capture["target_cell_trials"].append(trial)
            capture["current_target_cell"] = None
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="TARGET_CELL_TRIAL_COMPLETED",
                payload=trial,
                checkpoint=True,
            )
            capture["execution_phase"] = "N32_ACCEPTED_TRAJECTORY_RECONSTRUCTION"

    def observed_solve_cell(**kwargs: Any) -> Any:
        support = kwargs.get("support")
        control = rating._CANDIDATE_TRANSIENT_CONTROL.get()
        target_disabled = (
            support is not None
            and support.physical_segment_id == TARGET_SUPPORT_ID
            and kwargs.get("mesh_subdivisions") == TARGET_N
            and control is not None
            and control.mode == "DISABLED"
        )
        try:
            return original_solve_cell(**kwargs)
        except rating._Stage3Failure as exc:
            if target_disabled:
                try:
                    capture["failure"] = {
                        "code": exc.code,
                        "diagnostics": list(exc.diagnostics),
                        "mesh_subdivisions": kwargs.get("mesh_subdivisions"),
                        "support_id": support.physical_segment_id,
                        "tube_cell_id": support.tube_cell_id,
                        "shell_cell_id": support.shell_cell_id,
                        "wall_interface_id": support.wall_interface_id,
                        "outer_iteration": kwargs.get("outer_iteration"),
                        "shooting_enthalpy_j_kg": str(kwargs.get("shooting_enthalpy")),
                        "tube_upstream_state": _capture_state(kwargs["tube_upstream"]),
                        "shell_physical_left_state": _capture_state(kwargs["shell_physical_left"]),
                    }
                except Exception as observer_exc:
                    capture["observer_fail_closed"] = True
                    _note_diagnostic_exception(capture, "observe_cell_failure", observer_exc)
            raise

    original_boundary = rating._candidate_transient_outer_boundary
    context_token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    start_wall = time.monotonic()
    start_cpu = time.process_time()
    rating._solve_cell = observed_solve_cell
    rating._cell_evaluation = observed_cell_evaluation
    rating.task172_validate_candidate = observed_task172
    rating._candidate_provider_enclosure_event = observed_event
    rating.canonical_sha256 = observed_canonical_sha256
    try:
        try:
            mesh_run = original_boundary(TARGET_N, provider, context.shell_authority, stats)
            capture["n32_boundary_outcome"] = "RETURNED_ACCEPTED_MESH"
            capture["n32_mesh_result_hash"] = mesh_run.mesh_result_hash
            capture["n32_shooting_enthalpy_j_kg"] = str(mesh_run.shooting_enthalpy)
            capture["n32_outer_iteration_count"] = mesh_run.bisection_iterations
        except rating._Stage3Failure as exc:
            capture["n32_boundary_outcome"] = "BLOCKED"
            capture["n32_boundary_failure"] = {
                "code": exc.code,
                "diagnostics": list(exc.diagnostics),
            }
        except BaseException as exc:
            capture["n32_boundary_outcome"] = "RAISED"
            _note_diagnostic_exception(capture, "n32_outer_boundary", exc)
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="N32_BOUNDARY_EXCEPTION",
                payload=capture["last_exception"],
                checkpoint=True,
            )
            raise
        finally:
            capture["wall_seconds"] = time.monotonic() - start_wall
            capture["process_cpu_seconds"] = time.process_time() - start_cpu
            capture["task172_local_evaluation_count_from_stats"] = (
                stats.task172_local_evaluation_count
            )
            capture["task172_numerical_hole_count_from_stats"] = stats.task172_numerical_hole_count
            capture["task172_hole_counts_by_code"] = dict(
                stats.task172_numerical_hole_counts_by_code
            )
            capture["task172_validator_call_count"] = capture["task172_validator_call_count"]
            capture["target_trial_count"] = len(capture["target_cell_trials"])
            capture["transient_event_count"] = len(capture["transient_events"])
            capture["_native_target_objects"] = native_target_objects
            capture["_native_provider"] = provider
            capture["execution_phase"] = "N32_RECONSTRUCTION_FINISHED"
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="N32_RECONSTRUCTION_FINISHED",
                payload={
                    "outcome": capture.get("n32_boundary_outcome"),
                    "task172_validator_call_count": capture["task172_validator_call_count"],
                    "task172_local_evaluation_count": stats.task172_local_evaluation_count,
                    "task172_numerical_hole_count": stats.task172_numerical_hole_count,
                    "wall_seconds": capture["wall_seconds"],
                },
                checkpoint=True,
            )
    finally:
        rating._solve_cell = original_solve_cell
        rating._cell_evaluation = original_cell_evaluation
        rating.task172_validate_candidate = original_task172_candidate
        rating._candidate_provider_enclosure_event = original_event
        rating.canonical_sha256 = original_canonical_sha256
        rating._CANDIDATE_RATING_CONTEXT.reset(context_token)
    return capture


def _probe_decimal_q(
    q: Decimal,
    *,
    support: Any,
    tube_upstream: Any,
    shell_physical_left: Any,
    provider: CoolPropProvider,
    shell_authority: Any,
    context: Any,
    ordinal: int,
    store: DiagnosticCheckpointStore | None = None,
    capture: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if type(q) is not Decimal or not q.is_finite() or q < 0:
        raise ValueError("diagnostic Decimal q must be finite and non-negative")
    if capture is not None:
        capture["execution_phase"] = "DECIMAL_Q_PROVIDER_PH_EVALUATION"
        capture["decimal_q_probe_in_progress"] = {
            "probe_index": ordinal,
            "q_decimal_exact": str(q),
            "provider_ph_partial": [],
            "task172_call_count_before": capture.get("task172_validator_call_count", 0),
        }
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="DECIMAL_Q_PROBE_STARTED",
            payload=capture["decimal_q_probe_in_progress"],
            checkpoint=True,
        )
    with localcontext() as decimal_context:
        decimal_context.prec = 70
        tube_upstream_h = rating._d(tube_upstream.native.enthalpy_j_kg)
        shell_left_h = rating._d(shell_physical_left.native.enthalpy_j_kg)
        tube_downstream_h = tube_upstream_h - q / rating.TUBE_MASS_FLOW_KG_S
        shell_next_h = shell_left_h - q / rating.SHELL_MASS_FLOW_KG_S
        tube_mid_h = (tube_upstream_h + tube_downstream_h) / Decimal(2)
        shell_mid_h = (shell_left_h + shell_next_h) / Decimal(2)
    enthalpies = {
        "tube_downstream": tube_downstream_h,
        "shell_next_physical": shell_next_h,
        "tube_midpoint": tube_mid_h,
        "shell_midpoint": shell_mid_h,
    }
    states: dict[str, Any] = {}
    provider_ph: list[dict[str, Any]] = []
    for label, enthalpy in enthalpies.items():
        provider_float = float(enthalpy)
        provider_call_record = {
            "state_role": label,
            "enthalpy_decimal_before_float": str(enthalpy),
            "provider_enthalpy_float": provider_float,
            "provider_enthalpy_float_hex": provider_float.hex(),
            "decimal_from_provider_float": str(Decimal.from_float(provider_float)),
            "provider_call_status": "IN_PROGRESS",
        }
        if capture is not None:
            capture["decimal_q_probe_in_progress"]["provider_ph_partial"].append(
                provider_call_record
            )
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="DECIMAL_Q_PROVIDER_PH_STARTED",
                payload=provider_call_record,
                checkpoint=True,
            )
        try:
            state = rating._state_from_enthalpy(
                provider,
                enthalpy,
                shell_search_state=label == "shell_next_physical",
            )
        except Exception as exc:
            if capture is not None:
                _note_diagnostic_exception(capture, f"decimal_q_provider_ph:{label}", exc)
                provider_call_record["provider_call_status"] = "RAISED"
                provider_call_record["exception"] = capture["last_exception"]
                _persist_event_and_checkpoint(
                    capture,
                    store,
                    event_type="DECIMAL_Q_PROVIDER_PH_EXCEPTION",
                    payload=provider_call_record,
                    checkpoint=True,
                )
            raise
        states[label] = state
        try:
            provider_record = {
                **provider_call_record,
                "provider_call_status": "RETURNED",
                "provider_input_snapshot": state.snapshot.model_dump(mode="json"),
                "provider_input_snapshot_hash": state.snapshot_hash,
                "provider_output_native": _native_projection(state.native),
                "provider_output_enthalpy_j_kg": str(state.native.enthalpy_j_kg),
            }
            provider_ph.append(provider_record)
            provider_call_record.update(
                {
                    "provider_call_status": "RETURNED",
                    "provider_input_snapshot": provider_record["provider_input_snapshot"],
                    "provider_input_snapshot_hash": state.snapshot_hash,
                    "provider_output_native": provider_record["provider_output_native"],
                    "provider_output_enthalpy_j_kg": provider_record[
                        "provider_output_enthalpy_j_kg"
                    ],
                }
            )
        except Exception as exc:
            if capture is not None:
                _note_diagnostic_exception(capture, f"capture_decimal_provider_ph:{label}", exc)
                provider_call_record["provider_call_status"] = "CAPTURE_FAILED"
                provider_call_record["exception"] = capture["last_exception"]
                _persist_event_and_checkpoint(
                    capture,
                    store,
                    event_type="DECIMAL_Q_PROVIDER_PH_CAPTURE_EXCEPTION",
                    payload=provider_call_record,
                    checkpoint=True,
                )
            raise
        if capture is not None:
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="DECIMAL_Q_PROVIDER_PH_COMPLETED",
                payload=provider_call_record,
                checkpoint=True,
            )
    request = rating._task172_request(
        support, states["tube_midpoint"], states["shell_midpoint"], shell_authority
    )
    if type(request) is not CandidateTask172LocalRequest:
        raise RuntimeError("decimal probe did not produce candidate-native TASK172 request")
    support_hash = rating.recompute_task172_support_id(request)
    if (
        request.case_id != context.request.candidate_id
        or request.case_revision_id != context.request.candidate_id
        or request.topology.topology_id != context.topology_id
        or request.topology.task171_result_hash != context.task171_result_hash
        or request.topology.physical_ownership_hash != context.physical_ownership_hash
        or request.support != support
        or len(support_hash) != 64
        or request.topology.tube_role != "HOT"
        or request.topology.shell_role != "COLD"
    ):
        raise RuntimeError("decimal probe candidate/support preflight failed")
    if states["tube_midpoint"].native.temperature_k < states["shell_midpoint"].native.temperature_k:
        raise RuntimeError("decimal probe violates the native hot/cold preflight")
    for state in (states["tube_midpoint"], states["shell_midpoint"]):
        native = state.native
        if (
            native.phase.value != PhaseRegion.LIQUID.value
            or native.pressure_pa != float(rating.REFERENCE_PRESSURE_PA)
            or state.snapshot.backend != "HEOS::Water"
            or state.snapshot.provider != "CoolProp"
            or state.snapshot.provider_version != "8.0.0"
            or state.snapshot.reference_state != "DEF"
        ):
            raise RuntimeError("decimal probe property-profile preflight failed")
    native_request_hash = rating.recompute_task172_request_hash(request)
    request_projection = _model_json(request)
    if capture is not None:
        capture["execution_phase"] = "DECIMAL_Q_PROBE_TASK172_VALIDATION"
        capture["decimal_q_probe_in_progress"] = {
            "probe_index": ordinal,
            "q_decimal_exact": str(q),
            "task172_request_hash": native_request_hash,
            "provider_ph_partial": provider_ph,
            "task172_call_count_before": capture.get("task172_validator_call_count", 0),
        }
        capture["task172_validator_call_count"] = capture.get("task172_validator_call_count", 0) + 1
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="DECIMAL_Q_PROBE_STARTED",
            payload=capture["decimal_q_probe_in_progress"],
            checkpoint=True,
        )
    try:
        native_result = rating.task172_validate_candidate(request, provider)
    except Exception as exc:
        if capture is not None:
            _note_diagnostic_exception(capture, "decimal_q_probe_task172_validation", exc)
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="DECIMAL_Q_PROBE_EXCEPTION",
                payload=capture["last_exception"],
                checkpoint=True,
            )
        raise
    record: dict[str, Any] = {
        "probe_index": ordinal,
        "q_decimal_exact": str(q),
        "q_python_type": type(q).__name__,
        "intermediate_enthalpy_decimal_inputs": {
            name: str(value) for name, value in enthalpies.items()
        },
        "provider_ph_inputs_outputs": provider_ph,
        "task172_request_projection": request_projection,
        "task172_request_hash": native_request_hash,
        "task172_support_hash": support_hash,
        "task172_request_hash_replay": False,
        "task172_result_type": type(native_result).__name__,
        "task172_result_hash_replay": False,
        "F_decimal_high_precision": None,
        "F_native_contract_context": None,
        "ordinary_point_root_tolerance_pass": False,
    }
    try:
        native_identity = _task172_result_identity(request, native_result)
    except Exception as exc:
        if capture is not None:
            _note_diagnostic_exception(capture, "decimal_q_probe_result_projection", exc)
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="DECIMAL_Q_PROBE_RESULT_CAPTURE_EXCEPTION",
                payload=capture["last_exception"],
                checkpoint=True,
            )
        raise
    if capture is not None:
        captured_return = _capture_decimal_probe_result(
            capture,
            native_identity,
            native_result,
        )
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="DECIMAL_Q_PROBE_NATIVE_RESULT_RETURNED",
            payload=captured_return,
            checkpoint=True,
        )
    try:
        _record_probe_task172_result(record, request, native_result, q)
    except Exception as exc:
        if capture is not None:
            _note_diagnostic_exception(capture, "decimal_q_probe_result_replay", exc)
            capture["decimal_q_probe_in_progress"]["result_validation_error"] = capture[
                "last_exception"
            ]
            _persist_event_and_checkpoint(
                capture,
                store,
                event_type="DECIMAL_Q_PROBE_RESULT_REPLAY_EXCEPTION",
                payload=capture["last_exception"],
                checkpoint=True,
            )
        raise
    record["provider_state_output_hashes"] = [state.snapshot_hash for state in states.values()]
    record["q_binary64_conversion_after_native_evaluation_and_F_only"] = float(q)
    record["q_binary64_conversion_hex_after_native_evaluation_and_F_only"] = float(q).hex()
    if capture is not None:
        capture.setdefault("decimal_q_probes", []).append(record)
        capture["decimal_q_probe_in_progress"] = None
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="DECIMAL_Q_PROBE_COMPLETED",
            payload=record,
            checkpoint=True,
        )
    return record


def _run_decimal_probes(
    capture: dict[str, Any],
    request: CandidateRatingRequest,
    *,
    store: DiagnosticCheckpointStore | None = None,
    uniform_intervals: int = 64,
    adaptive_bisection_cap: int = 64,
) -> dict[str, Any]:
    target_trials = capture["target_cell_trials"]
    endpoint_by_q = {
        item["q_w_repr"]: item
        for item in target_trials
        if item.get("cell_evaluation_status") == "VALIDATED"
    }
    if repr(TARGET_LEFT_Q) not in endpoint_by_q or repr(TARGET_RIGHT_Q) not in endpoint_by_q:
        raise RuntimeError("exact original binary64 endpoint evaluations were not captured")
    failure = capture.get("failure")
    if failure is None:
        raise RuntimeError("target accepted-cell failure record is missing")
    if (
        capture.get("n32_boundary_outcome") != "BLOCKED"
        or failure["code"] != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        or failure["support_id"] != TARGET_SUPPORT_ID
        or failure["mesh_subdivisions"] != TARGET_N
    ):
        raise RuntimeError("isolated n32 reconstruction did not reproduce frozen target failure")
    frozen_diagnostics = capture["frozen_blocked_result_projection"]["diagnostics"]
    cell_failure_diagnostics = failure.get("diagnostics", [])
    if frozen_diagnostics[: len(cell_failure_diagnostics)] != cell_failure_diagnostics:
        raise RuntimeError("reconstructed exact-cell failure diagnostics differ from frozen result")
    if (
        capture["task172_local_evaluation_count_from_stats"] != EXPECTED_N32_EVALUATIONS
        or capture["task172_numerical_hole_count_from_stats"] != EXPECTED_N32_HOLES
        or capture["task172_validator_call_count"] != EXPECTED_N32_EVALUATIONS
    ):
        raise RuntimeError("isolated n32 Task172 call counts differ from frozen receipt")
    if not capture["target_support_seen"]:
        raise RuntimeError("isolated accepted trajectory did not reach exact target support")

    left_q = Decimal.from_float(TARGET_LEFT_Q)
    right_q = Decimal.from_float(TARGET_RIGHT_Q)
    if not left_q < right_q:
        raise RuntimeError("binary64 endpoints do not define an increasing Decimal interval")
    context = rating._candidate_context(request)
    failure_capture = capture["failure"]
    support_projection = next(
        item["support_projection"]
        for item in target_trials
        if item["q_w_repr"] == repr(TARGET_LEFT_Q)
    )
    # The reconstructed accepted-cell arguments are bound in each target trial.
    # Rehydrate the actual objects from the deterministic n=32 reconstruction by
    # running no solver again: the capture stores full provider snapshots, while
    # the original native objects are intentionally retained in this process.
    objects = capture.get("_native_target_objects")
    if objects is None:
        raise RuntimeError("native target objects were not retained for Decimal probes")
    provider = capture.get("_native_provider")
    if provider is None:
        raise RuntimeError("native provider was not retained for Decimal probes")

    probe_results: list[dict[str, Any]] = []
    by_q: dict[Decimal, dict[str, Any]] = {}

    def run_one(q: Decimal) -> dict[str, Any]:
        if q in by_q:
            return by_q[q]
        result = _probe_decimal_q(
            q,
            support=objects["support"],
            tube_upstream=objects["tube_upstream"],
            shell_physical_left=objects["shell_physical_left"],
            provider=provider,
            shell_authority=context.shell_authority,
            context=context,
            ordinal=len(probe_results) + 1,
            store=store,
            capture=capture,
        )
        by_q[q] = result
        probe_results.append(result)
        return result

    with localcontext() as decimal_context:
        decimal_context.prec = 100
        width = right_q - left_q
        for index in range(uniform_intervals + 1):
            run_one(left_q + width * Decimal(index) / Decimal(uniform_intervals))

    for endpoint in (endpoint_by_q[repr(TARGET_LEFT_Q)], endpoint_by_q[repr(TARGET_RIGHT_Q)]):
        task_result = endpoint["task172_result_projection"]
        proposed = Decimal(task_result["signed_q_hot_to_cold_w"])
        if left_q <= proposed <= right_q:
            run_one(proposed)

    adaptive_calls = 0
    while adaptive_calls < adaptive_bisection_cap and not any(
        item["ordinary_point_root_tolerance_pass"] for item in probe_results
    ):
        ordered = sorted(by_q.items(), key=lambda item: item[0])
        eligible_bracket: tuple[Decimal, Decimal] | None = None
        for (q_left, left_record), (q_right, right_record) in zip(
            ordered, ordered[1:], strict=False
        ):
            if (
                left_record["task172_status"] == "VALIDATED"
                and right_record["task172_status"] == "VALIDATED"
                and not left_record["ordinary_point_root_tolerance_pass"]
                and not right_record["ordinary_point_root_tolerance_pass"]
                and Decimal(left_record["F_decimal_high_precision"])
                * Decimal(right_record["F_decimal_high_precision"])
                < 0
            ):
                eligible_bracket = (q_left, q_right)
                break
        if eligible_bracket is None:
            break
        q_left, q_right = eligible_bracket
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            midpoint = (q_left + q_right) / Decimal(2)
        if midpoint in by_q or midpoint in {q_left, q_right}:
            break
        run_one(midpoint)
        adaptive_calls += 1
        if probe_results[-1]["ordinary_point_root_tolerance_pass"]:
            break

    validated = [item for item in probe_results if item["task172_status"] == "VALIDATED"]
    min_abs_f = min(
        (abs(Decimal(item["F_decimal_high_precision"])) for item in validated),
        default=None,
    )
    passing = [item for item in validated if item["ordinary_point_root_tolerance_pass"]]
    probe_signatures = []
    for item in probe_results:
        input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in item["provider_ph_inputs_outputs"]
        )
        output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in item["provider_ph_inputs_outputs"]
        )
        probe_signatures.append((input_signature, output_signature))
    unique_provider_input_signatures = {item[0] for item in probe_signatures}
    unique_provider_output_signatures = {item[1] for item in probe_signatures}

    ordered_uniform = sorted(
        (item for item in probe_results if item["probe_index"] <= uniform_intervals + 1),
        key=lambda item: Decimal(item["q_decimal_exact"]),
    )
    adjacent_steps: list[dict[str, Any]] = []
    provider_plateau_pairs: list[dict[str, Any]] = []
    task172_same_request_output_changes: list[dict[str, Any]] = []
    for left, right in zip(ordered_uniform, ordered_uniform[1:], strict=False):
        if left["task172_status"] != "VALIDATED" or right["task172_status"] != "VALIDATED":
            continue
        left_task_q = Decimal(left["task172_signed_q_hot_to_cold_w"])
        right_task_q = Decimal(right["task172_signed_q_hot_to_cold_w"])
        delta_input = Decimal(right["q_decimal_exact"]) - Decimal(left["q_decimal_exact"])
        delta_task = right_task_q - left_task_q
        left_input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in left["provider_ph_inputs_outputs"]
        )
        right_input_signature = tuple(
            call["provider_enthalpy_float_hex"] for call in right["provider_ph_inputs_outputs"]
        )
        left_output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in left["provider_ph_inputs_outputs"]
        )
        right_output_signature = tuple(
            call["provider_input_snapshot_hash"] for call in right["provider_ph_inputs_outputs"]
        )
        if (
            left_input_signature == right_input_signature
            and left_output_signature == right_output_signature
            and left["task172_request_hash"] == right["task172_request_hash"]
            and left["task172_result_hash"] == right["task172_result_hash"]
        ):
            provider_plateau_pairs.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "left_q_decimal": left["q_decimal_exact"],
                    "right_q_decimal": right["q_decimal_exact"],
                    "provider_ph_input_signature": list(left_input_signature),
                    "provider_ph_output_snapshot_hashes": list(left_output_signature),
                    "task172_request_hash": left["task172_request_hash"],
                    "task172_result_hash": left["task172_result_hash"],
                    "left_F_w": left["F_decimal_high_precision"],
                    "right_F_w": right["F_decimal_high_precision"],
                }
            )
        if (
            left_input_signature == right_input_signature
            and left_output_signature == right_output_signature
            and left["task172_request_hash"] == right["task172_request_hash"]
            and (
                left["task172_result_hash"] != right["task172_result_hash"]
                or left_task_q != right_task_q
            )
        ):
            task172_same_request_output_changes.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "provider_ph_input_signature": list(left_input_signature),
                    "provider_ph_output_snapshot_hashes": list(left_output_signature),
                    "task172_request_hash": left["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                    "left_task172_q_w": str(left_task_q),
                    "right_task172_q_w": str(right_task_q),
                }
            )
        if delta_task != 0:
            adjacent_steps.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "left_q_decimal": left["q_decimal_exact"],
                    "right_q_decimal": right["q_decimal_exact"],
                    "delta_q_w": str(delta_input),
                    "left_task172_q_w": str(left_task_q),
                    "right_task172_q_w": str(right_task_q),
                    "delta_task172_q_w": str(delta_task),
                    "left_request_hash": left["task172_request_hash"],
                    "right_request_hash": right["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                    "provider_input_signature_changed": (
                        left_input_signature != right_input_signature
                    ),
                    "provider_output_signature_changed": (
                        left_output_signature != right_output_signature
                    ),
                    "task172_request_identity_changed": (
                        left["task172_request_hash"] != right["task172_request_hash"]
                    ),
                    "classification": (
                        "PROVIDER_STATE_STEP"
                        if left_input_signature != right_input_signature
                        or left_output_signature != right_output_signature
                        else "TASK172_RESULT_STEP_WITH_IDENTICAL_PROVIDER_STATE"
                    ),
                }
            )
    root_recovered = bool(passing)
    return {
        "decimal_probe_plan": {
            "uniform_intervals": uniform_intervals,
            "uniform_probe_count_expected": uniform_intervals + 1,
            "endpoint_task172_heat_rate_points_added_if_inside": True,
            "adaptive_sign_bracket_bisection_cap": adaptive_bisection_cap,
            "adaptive_bisection_calls_used": adaptive_calls,
            "original_left_q_exact_decimal_from_float": str(left_q),
            "original_right_q_exact_decimal_from_float": str(right_q),
            "q_float_conversion_before_enthalpy_or_F": False,
        },
        "decimal_q_probe_count": len(probe_results),
        "validated_task172_probe_count": len(validated),
        "blocked_task172_probe_count": len(probe_results) - len(validated),
        "min_abs_f_w": str(min_abs_f) if min_abs_f is not None else None,
        "point_root_recovered": root_recovered,
        "point_root_probe_indices": [item["probe_index"] for item in passing],
        "provider_ph_plateau_confirmed": bool(provider_plateau_pairs),
        "provider_ph_plateau_adjacent_pair_count": len(provider_plateau_pairs),
        "provider_ph_plateau_adjacent_pairs": provider_plateau_pairs,
        "provider_ph_unique_input_signature_count": len(unique_provider_input_signatures),
        "provider_ph_unique_output_signature_count": len(unique_provider_output_signatures),
        "provider_state_changes_observed_between_adjacent_probes": any(
            item["provider_input_signature_changed"] or item["provider_output_signature_changed"]
            for item in adjacent_steps
        ),
        "task172_discontinuity_observed": bool(task172_same_request_output_changes),
        "task172_same_request_output_changes": task172_same_request_output_changes,
        "adjacent_native_task172_output_steps": adjacent_steps,
        "probes": probe_results,
        "target_failure_reference": {
            "code": failure_capture["code"],
            "support_id": failure_capture["support_id"],
            "mesh_subdivisions": failure_capture["mesh_subdivisions"],
            "outer_iteration": failure_capture["outer_iteration"],
            "shooting_enthalpy_j_kg": failure_capture["shooting_enthalpy_j_kg"],
            "support_projection": support_projection,
        },
    }


def _check_capture_replay(capture: dict[str, Any]) -> dict[str, Any]:
    target_trials = capture.get("target_cell_trials", [])
    endpoint_map = {item.get("q_w_repr"): item for item in target_trials}
    left = endpoint_map.get(repr(TARGET_LEFT_Q))
    right = endpoint_map.get(repr(TARGET_RIGHT_Q))
    if left is None or right is None:
        raise RuntimeError("original bracket endpoint trace missing")
    if (
        left.get("cell_evaluation_status") != "VALIDATED"
        or right.get("cell_evaluation_status") != "VALIDATED"
    ):
        raise RuntimeError("frozen endpoint evaluations were not both native VALIDATED")
    if left["task172_request_hash"] != left["task172_result_projection"]["request_hash"]:
        raise RuntimeError("left endpoint Task172 request hash mismatch")
    if right["task172_request_hash"] != right["task172_result_projection"]["request_hash"]:
        raise RuntimeError("right endpoint Task172 request hash mismatch")
    if (
        not left["task172_result_hash"] == left["task172_result_projection"]["result_hash"]
        or not right["task172_result_hash"] == right["task172_result_projection"]["result_hash"]
    ):
        raise RuntimeError("endpoint Task172 result hash mismatch")
    endpoint_identity_replays: list[dict[str, str]] = []
    target_trial_identity_replay_count = 0
    for trial in target_trials:
        for state_capture in trial.get("provider_ph_calls", []):
            state = state_capture["state_after_provider"]
            if canonical_sha256(state["property_snapshot"]) != state["property_snapshot_hash"]:
                raise RuntimeError("target-trial provider snapshot hash replay failed")
        native_call = trial.get("task172_call")
        if native_call is None:
            continue
        # Captured JSON projections contain JSON-native strings/lists.  Restore
        # the domain values, then rely on the native identity hash below to
        # prove the projection still denotes the exact request.  Strict native
        # validation applies to live runtime objects, not their JSON evidence.
        native_request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(native_call["request_projection"]), strict=False
        )
        replayed_request_hash = rating.recompute_task172_request_hash(native_request)
        if replayed_request_hash != native_call["request_hash"]:
            raise RuntimeError("target-trial Task172 request hash replay failed")
        if native_call["result_type"] == "Task172LocalResult":
            native_result = Task172LocalResult.model_validate(
                _restore_pairs(native_call["result_projection"]), strict=False
            )
            replayed_result_hash = rating.recompute_task172_result_hash(native_result)
            expected_result_hash = native_result.result_hash
        else:
            native_result = rating.Task172BlockedResult.model_validate(
                _restore_pairs(native_call["result_projection"]), strict=False
            )
            replayed_result_hash = rating.recompute_task172_blocked_result_hash(native_result)
            expected_result_hash = native_result.blocked_result_hash
        if (
            replayed_result_hash != expected_result_hash
            or replayed_result_hash != native_call["result_hash"]
        ):
            raise RuntimeError("target-trial Task172 result hash replay failed")
        target_trial_identity_replay_count += 1
    for label, endpoint in (("LEFT", left), ("RIGHT", right)):
        native_request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(endpoint["task172_request_projection"]), strict=False
        )
        native_result = Task172LocalResult.model_validate(
            _restore_pairs(endpoint["task172_result_projection"]), strict=False
        )
        replayed_request_hash = rating.recompute_task172_request_hash(native_request)
        replayed_result_hash = rating.recompute_task172_result_hash(native_result)
        if (
            replayed_request_hash != endpoint["task172_request_hash"]
            or replayed_result_hash != endpoint["task172_result_hash"]
            or native_request.support.physical_segment_id != TARGET_SUPPORT_ID
            or native_result.status != "VALIDATED"
        ):
            raise RuntimeError(f"{label} endpoint native Task172 identity replay failed")
        replayed_f = rating._d(float(endpoint["q_w_repr"])) - native_result.signed_q_hot_to_cold_w
        if str(replayed_f) != endpoint["f_production_decimal_context"]:
            raise RuntimeError(f"{label} endpoint production F replay failed")
        exact_binary_f = Decimal.from_float(float(endpoint["q_w_repr"]))
        with localcontext() as decimal_context:
            decimal_context.prec = 100
            exact_binary_f -= native_result.signed_q_hot_to_cold_w
        if str(exact_binary_f) != endpoint["f_exact_binary64_endpoint"]:
            raise RuntimeError(f"{label} endpoint exact binary64 F replay failed")
        for state_capture in endpoint["provider_ph_calls"]:
            state = state_capture["state_after_provider"]
            if canonical_sha256(state["property_snapshot"]) != state["property_snapshot_hash"]:
                raise RuntimeError(f"{label} endpoint provider snapshot hash replay failed")
        endpoint_identity_replays.append(
            {
                "side": label,
                "request_hash": replayed_request_hash,
                "result_hash": replayed_result_hash,
            }
        )
    if (
        Decimal(left["f_production_decimal_context"]) >= 0
        or Decimal(right["f_production_decimal_context"]) <= 0
    ):
        raise RuntimeError("original cell bracket no longer has the frozen sign orientation")
    if Decimal(left["f_production_decimal_context"]).copy_abs() <= Decimal("1e-6") or Decimal(
        right["f_production_decimal_context"]
    ).copy_abs() <= Decimal("1e-6"):
        raise RuntimeError("one frozen binary64 endpoint already satisfies point-root tolerance")
    if capture["failure"].get("shooting_enthalpy_j_kg") is None:
        raise RuntimeError("selected accepted shooting enthalpy was not captured")
    if capture["failure"].get("outer_iteration") is None:
        raise RuntimeError("accepted outer iteration was not captured")
    if (
        capture["failure"].get("tube_cell_id") is None
        or capture["failure"].get("shell_cell_id") is None
        or capture["failure"].get("wall_interface_id") is None
    ):
        raise RuntimeError("target cell physical identity capture is incomplete")
    certificate_replays = 0
    for certificate in capture.get("transient_outer_decision_certificates", []):
        if canonical_sha256(certificate["projection"]) != certificate["certificate_hash"]:
            raise RuntimeError("transient outer decision certificate hash replay failed")
        certificate_replays += 1
    return {
        "endpoint_request_result_identity_replay": "PASS",
        "left_f_production_decimal_context": left["f_production_decimal_context"],
        "right_f_production_decimal_context": right["f_production_decimal_context"],
        "left_task172_request_hash": left["task172_request_hash"],
        "right_task172_request_hash": right["task172_request_hash"],
        "left_task172_result_hash": left["task172_result_hash"],
        "right_task172_result_hash": right["task172_result_hash"],
        "endpoint_native_identity_replays": endpoint_identity_replays,
        "target_cell_trial_task172_identity_replay_count": target_trial_identity_replay_count,
        "transient_outer_decision_certificate_hash_replay_count": certificate_replays,
    }


def _execute() -> dict[str, Any]:
    runtime_binding = _assert_runtime_binding(execution=True)
    if R2_CHECKPOINT_PATH.exists() or R2_TRACE_PATH.exists() or R2_EXECUTION_EVIDENCE_PATH.exists():
        raise RuntimeError("R2 execution artifacts already exist; refusing a second reconstruction")
    receipt_raw = CANDIDATE_RECEIPT.read_bytes()
    if _sha256(receipt_raw) != EXPECTED_CANDIDATE_RECEIPT_SHA256:
        raise RuntimeError("frozen Candidate A receipt raw SHA mismatch")
    receipt = json.loads(receipt_raw)
    frozen = receipt["candidates"][CANDIDATE_ID]
    frozen_result = frozen["result_projection"]
    if (
        receipt["completion_request_hash"] != COMPLETION_REQUEST_HASH
        or receipt["task168_candidate_space_hash"] != TASK168_SPACE_HASH
        or frozen["candidate_rating_request_hash"] != RATING_REQUEST_HASH
        or frozen["result_hash"] != EXPECTED_BLOCKED_RESULT_HASH
        or frozen["failed_mesh_subdivisions"] != TARGET_N
        or canonical_sha256(
            {
                key: frozen_result[key]
                for key in (
                    "schema_version",
                    "status",
                    "failure_code",
                    "failed_mesh_subdivisions",
                    "request_hash",
                    "diagnostics",
                )
            }
        )
        != EXPECTED_BLOCKED_RESULT_HASH
    ):
        raise RuntimeError("frozen target request/result binding mismatch")
    frozen_result_projection = {
        key: frozen_result[key]
        for key in (
            "schema_version",
            "status",
            "failure_code",
            "failed_mesh_subdivisions",
            "request_hash",
            "diagnostics",
            "result_hash",
            "result_id",
        )
    }
    request_identity = {
        "completion_sizing_request_hash": COMPLETION_REQUEST_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "candidate_id": CANDIDATE_ID,
        "candidate_hash": CANDIDATE_HASH,
        "candidate_rating_request_hash": RATING_REQUEST_HASH,
        "frozen_blocked_result_hash": EXPECTED_BLOCKED_RESULT_HASH,
        "candidate_receipt_sha256": _sha256(receipt_raw),
        "frozen_blocked_result_projection": frozen_result_projection,
    }
    runtime_identity = {
        **runtime_binding,
        "execution_start_head": R2_EXECUTION_START_HEAD,
        "execution_start_tree": _git("rev-parse", "HEAD^{tree}"),
        "diagnostic_runner_sha256": _sha256(Path(__file__).read_bytes()),
    }
    started = time.monotonic()
    cpu_started = time.process_time()
    request_replay_started = time.monotonic()
    request_replay = subprocess.run(
        [sys.executable, str(REQUEST_REPLAY)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    request_replay_wall = time.monotonic() - request_replay_started
    if request_replay.returncode or "ALL_COMPLETION_REQUEST_REPLAY_PASS=true" not in (
        request_replay.stdout
    ):
        raise RuntimeError(
            f"committed completion request replay failed: {request_replay.stderr.strip()}"
        )
    request, request_facts = _reconstruct_candidate_a()
    if candidate_rating_request_hash(request) != RATING_REQUEST_HASH:
        raise RuntimeError("exact Candidate A request did not replay")
    ambient_before_provider = _context_snapshot()
    provider = CoolPropProvider()
    ambient_before_reconstruction = _context_snapshot(provider)
    provider_call_counts = {"state_ph": 0, "state_tp": 0}
    original_provider_state_ph = provider.state_ph
    original_provider_state_tp = provider.state_tp

    def counted_state_ph(*args: Any, **kwargs: Any) -> Any:
        provider_call_counts["state_ph"] += 1
        return original_provider_state_ph(*args, **kwargs)

    def counted_state_tp(*args: Any, **kwargs: Any) -> Any:
        provider_call_counts["state_tp"] += 1
        return original_provider_state_tp(*args, **kwargs)

    provider.state_ph = counted_state_ph
    provider.state_tp = counted_state_tp
    try:
        store = DiagnosticCheckpointStore(R2_OUTPUT_DIR)
        capture = _run_exact_n32(
            request,
            provider,
            store=store,
            runtime_identity=runtime_identity,
            request_identity=request_identity,
        )
        capture["frozen_blocked_result_projection"] = frozen_result_projection
        actual_cell_failure = capture.get("failure", {})
        frozen_diagnostics = frozen_result["diagnostics"]
        actual_cell_diagnostics = actual_cell_failure.get("diagnostics", [])
        capture["frozen_failure_diagnostics_match"] = (
            actual_cell_failure.get("code") == frozen_result["failure_code"]
            and actual_cell_failure.get("mesh_subdivisions")
            == frozen_result["failed_mesh_subdivisions"]
            and actual_cell_failure.get("support_id") == TARGET_SUPPORT_ID
            and frozen_diagnostics[: len(actual_cell_diagnostics)] == actual_cell_diagnostics
            and frozen_diagnostics[-1] == f"mesh_subdivisions={TARGET_N}"
            and capture.get("n32_boundary_failure", {}).get("code") == frozen_result["failure_code"]
        )
        ambient_after_reconstruction = _context_snapshot(provider)
        capture["provider_state_ph_call_count_total"] = provider_call_counts["state_ph"]
        capture["provider_state_tp_call_count_total"] = provider_call_counts["state_tp"]
        capture["completion_request_replay"] = {
            "status": "PASS",
            "stdout": request_replay.stdout.strip().splitlines(),
            "wall_seconds": request_replay_wall,
        }
        capture["candidate_a_request_reconstruction"] = request_facts
        capture["runtime_binding"] = runtime_binding
        capture["ambient_before_provider_construction"] = ambient_before_provider
        capture["ambient_before_n32_reconstruction"] = ambient_before_reconstruction
        capture["ambient_after_n32_reconstruction"] = ambient_after_reconstruction
        capture["total_wall_seconds_including_candidate_preparation"] = time.monotonic() - started
        capture["total_process_cpu_seconds_including_candidate_preparation"] = (
            time.process_time() - cpu_started
        )
        capture["original_frozen_blocked_result_hash"] = EXPECTED_BLOCKED_RESULT_HASH
        capture["frozen_receipt_n32_evaluation_count"] = EXPECTED_N32_EVALUATIONS
        capture["frozen_receipt_n32_hole_count"] = EXPECTED_N32_HOLES
        capture["full_rating_invocation_performed"] = False
        capture["public_sizing_invocation_performed"] = False
        capture["public_sizing_invocation_performed_by_this_gate"] = False
        capture["r2a_authority_changed"] = False
        capture["task172_contract_changed"] = False
        capture["numerical_tolerance_changed"] = False
        capture["production_code_changed"] = False
        capture["preflight_result"] = "PASS"
        if (
            capture.get("task172_local_evaluation_count_from_stats") != EXPECTED_N32_EVALUATIONS
            or capture.get("task172_numerical_hole_count_from_stats") != EXPECTED_N32_HOLES
            or capture.get("failure", {}).get("code")
            != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
            or capture.get("failure", {}).get("support_id") != TARGET_SUPPORT_ID
            or not capture["frozen_failure_diagnostics_match"]
        ):
            capture["exact_target_cell_reconstructed"] = False
            capture["decimal_probe_count"] = 0
            capture["stop_reason"] = "ISOLATED_N32_FAILURE_SIGNATURE_DID_NOT_MATCH_FROZEN_TARGET"
            capture.pop("_native_target_objects", None)
            capture.pop("_native_provider", None)
            return capture
        capture["exact_target_cell_reconstructed"] = True
        if (
            capture.get("observer_fail_closed")
            or capture.get("observer_identity_replay_failed")
            or capture.get("diagnostic_exceptions")
        ):
            capture["decimal_probe_count"] = 0
            capture["stop_reason"] = "DIAGNOSTIC_OBSERVER_OR_CHECKPOINT_ERROR"
            capture["exact_target_cell_reconstructed"] = False
            capture.pop("_native_target_objects", None)
            capture.pop("_native_provider", None)
            return capture
        replay = _check_capture_replay(capture)
        capture["original_endpoint_identity_replay"] = replay
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="EXACT_TARGET_CELL_RECONSTRUCTED",
            payload={
                "endpoint_request_result_identity_replay": replay,
                "failure": capture["failure"],
                "target_trial_count": capture["target_trial_count"],
            },
            checkpoint=True,
        )
        capture["execution_phase"] = "DECIMAL_Q_PROBES"
        probe_wall_start = time.monotonic()
        probe_cpu_start = time.process_time()
        probes = _run_decimal_probes(capture, request, store=store)
        capture["decimal_probe_wall_seconds"] = time.monotonic() - probe_wall_start
        capture["decimal_probe_cpu_seconds"] = time.process_time() - probe_cpu_start
        capture["decimal_probe_experiment"] = probes
        capture["decimal_probe_count"] = probes["decimal_q_probe_count"]
        capture["decimal_probe_task172_invocation_count"] = probes["decimal_q_probe_count"]
        capture["total_solver_work"] = {
            "candidate_a_upstream_chain_count": 1,
            "candidate_a_task174_validation_count": 1,
            "isolated_n32_task172_validations": capture[
                "task172_local_evaluation_count_from_stats"
            ],
            "decimal_probe_native_task172_validations": probes["decimal_q_probe_count"],
            "task172_validations_total_in_gate": (
                capture["task172_local_evaluation_count_from_stats"]
                + probes["decimal_q_probe_count"]
            ),
            "public_candidate_rating_calls": 0,
            "public_sizing_calls": 0,
            "public_candidate_full_rating_reexecuted": False,
            "provider_state_ph_calls_total": provider_call_counts["state_ph"],
            "provider_state_tp_calls_total": provider_call_counts["state_tp"],
        }
        capture["accepted_trajectory_r2a_event_count"] = 0
        capture["accepted_trajectory_decision_certificate_hashes"] = []
        if any(event["mode"] == "DISABLED" for event in capture["transient_events"]):
            raise RuntimeError("an R2A event was incorrectly captured in accepted mode")
        capture.pop("_native_target_objects", None)
        capture.pop("_native_provider", None)
        capture["execution_phase"] = "R2_DIAGNOSTIC_COMPLETE"
        _persist_event_and_checkpoint(
            capture,
            store,
            event_type="R2_DIAGNOSTIC_COMPLETE",
            payload={
                "exact_target_cell_reconstructed": capture.get("exact_target_cell_reconstructed"),
                "decimal_probe_count": capture.get("decimal_probe_count", 0),
                "point_root_recovered": capture.get("decimal_probe_experiment", {}).get(
                    "point_root_recovered"
                ),
                "task172_validator_call_count": capture.get("task172_validator_call_count"),
            },
            checkpoint=True,
        )
    finally:
        if "state_ph" in provider.__dict__:
            del provider.__dict__["state_ph"]
        if "state_tp" in provider.__dict__:
            del provider.__dict__["state_tp"]
    return capture


def _replay() -> None:
    _assert_runtime_binding(execution=False)
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    if evidence["task_id"] != TASK_ID:
        raise RuntimeError("diagnostic evidence task identity mismatch")
    recorded_evidence_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded_evidence_hash:
        raise RuntimeError("diagnostic evidence canonical hash replay failed")
    if evidence["runtime_binding"]["runtime_source_head"] != RUNTIME_HEAD:
        raise RuntimeError("diagnostic runtime head binding mismatch")
    capture = evidence["diagnostic_execution"]
    if not capture.get("exact_target_cell_reconstructed"):
        fatal = capture.get("fatal_exception", {})
        if (
            evidence.get("result") == "BLOCKED_DIAGNOSTIC_RUNNER_OBSERVER_FAILURE"
            and fatal.get("type") == "AttributeError"
            and "Task172BlockedResult" in fatal.get("text", "")
            and capture.get("decimal_probe_count") == 0
        ):
            print("DIAGNOSTIC_ATTEMPT_RECEIPT_HASH_REPLAY=PASS")
            print("EXACT_TARGET_CELL_EVIDENCE_REPLAY=NOT_ESTABLISHED")
            print("DECIMAL_Q_PROBE_COUNT=0")
            return
        raise RuntimeError("committed evidence does not establish exact target cell")
    _check_capture_replay(capture)
    probes = capture["decimal_probe_experiment"]
    for probe in probes["probes"]:
        request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(probe["task172_request_projection"]), strict=True
        )
        if rating.recompute_task172_request_hash(request) != probe["task172_request_hash"]:
            raise RuntimeError(f"probe request hash mismatch: {probe['probe_index']}")
        result = (
            Task172LocalResult.model_validate(
                _restore_pairs(probe["task172_result_projection"]), strict=True
            )
            if probe["task172_status"] == "VALIDATED"
            else None
        )
        if result is None:
            blocked_type = rating.Task172BlockedResult
            blocked = blocked_type.model_validate(
                _restore_pairs(probe["task172_result_projection"]), strict=True
            )
            result_hash = rating.recompute_task172_blocked_result_hash(blocked)
            if result_hash != probe["task172_result_hash"]:
                raise RuntimeError(f"probe blocked result hash mismatch: {probe['probe_index']}")
        else:
            result_hash = rating.recompute_task172_result_hash(result)
            if result_hash != probe["task172_result_hash"]:
                raise RuntimeError(f"probe result hash mismatch: {probe['probe_index']}")
            with localcontext() as decimal_context:
                decimal_context.prec = 100
                replayed_f = Decimal(probe["q_decimal_exact"]) - result.signed_q_hot_to_cold_w
            if str(replayed_f) != probe["F_decimal_high_precision"]:
                raise RuntimeError(f"probe F replay mismatch: {probe['probe_index']}")
        for state in probe["provider_ph_inputs_outputs"]:
            if (
                canonical_sha256(state["provider_input_snapshot"])
                != state["provider_input_snapshot_hash"]
            ):
                raise RuntimeError(f"provider input snapshot hash mismatch: {probe['probe_index']}")
    print("EXACT_TARGET_CELL_EVIDENCE_REPLAY=PASS")
    print("TASK172_REQUEST_RESULT_IDENTITY_REPLAY=PASS")
    print("PROVIDER_SNAPSHOT_IDENTITY_REPLAY=PASS")
    print(f"DECIMAL_Q_PROBE_COUNT={probes['decimal_q_probe_count']}")
    print(f"MIN_ABS_F_W={probes['min_abs_f_w']}")
    print(f"POINT_ROOT_RECOVERED={str(probes['point_root_recovered']).lower()}")


def _restore_pairs(value: Any) -> Any:
    if isinstance(value, dict):
        if value.get("__task173_type__") == "ReferencePlanePair":
            return ReferencePlanePair(
                start=ReferencePlaneToken(value["start"]),
                end=ReferencePlaneToken(value["end"]),
            )
        return {key: _restore_pairs(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_restore_pairs(item) for item in value]
    return value


def _replay_r2() -> None:
    if not R2_EXECUTION_EVIDENCE_PATH.is_file():
        raise RuntimeError("R2 execution evidence is unavailable")
    evidence = json.loads(R2_EXECUTION_EVIDENCE_PATH.read_text(encoding="utf-8"))
    recorded_hash = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded_hash:
        raise RuntimeError("R2 execution evidence canonical hash mismatch")
    if evidence.get("execution_start_head") != R2_EXECUTION_START_HEAD:
        raise RuntimeError("R2 execution start HEAD mismatch")
    if evidence.get("preflight", {}).get("preflight_result") != "PASS":
        raise RuntimeError("R2 execution lacks passing preflight")
    capture = evidence.get("diagnostic_execution", {})
    frozen = capture.get("frozen_blocked_result_projection", {})
    failure = capture.get("failure", {})
    exact_n32_signature = (
        capture.get("n32_boundary_outcome") == "BLOCKED"
        and failure.get("code") == "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        and failure.get("mesh_subdivisions") == TARGET_N
        and failure.get("support_id") == TARGET_SUPPORT_ID
        and capture.get("frozen_failure_diagnostics_match") is True
        and capture.get("task172_local_evaluation_count_from_stats") == EXPECTED_N32_EVALUATIONS
        and capture.get("task172_numerical_hole_count_from_stats") == EXPECTED_N32_HOLES
        and capture.get("task172_validator_call_count") == EXPECTED_N32_EVALUATIONS
        and capture.get("target_support_seen") is True
        and frozen.get("result_hash") == EXPECTED_BLOCKED_RESULT_HASH
        and frozen.get("request_hash") == RATING_REQUEST_HASH
    )
    if not (capture.get("exact_target_cell_reconstructed") or exact_n32_signature):
        raise RuntimeError("R2 evidence does not establish the frozen n32 failure signature")
    replay = _check_capture_replay(capture)
    endpoint_map = {trial.get("q_w_repr"): trial for trial in capture.get("target_cell_trials", [])}
    for q in (repr(TARGET_LEFT_Q), repr(TARGET_RIGHT_Q)):
        endpoint = endpoint_map.get(q)
        if endpoint is None or endpoint.get("cell_evaluation_status") != "VALIDATED":
            raise RuntimeError(f"R2 evidence missing native VALIDATED endpoint: {q}")
    capture["offline_n32_replay"] = replay
    probes = capture.get("decimal_probe_experiment", {}).get("probes", [])
    for probe in probes:
        probe_request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(probe["task172_request_projection"]), strict=True
        )
        if rating.recompute_task172_request_hash(probe_request) != probe["task172_request_hash"]:
            raise RuntimeError(f"R2 Decimal probe request replay failed: {probe['probe_index']}")
        result_projection = _restore_pairs(probe["task172_result_projection"])
        if probe["task172_result_type"] == "Task172LocalResult":
            probe_result = Task172LocalResult.model_validate(result_projection, strict=True)
            result_hash = rating.recompute_task172_result_hash(probe_result)
            if (
                str(Decimal(probe["q_decimal_exact"]) - probe_result.signed_q_hot_to_cold_w)
                != probe["F_decimal_high_precision"]
            ):
                raise RuntimeError(f"R2 Decimal probe F replay failed: {probe['probe_index']}")
        elif probe["task172_result_type"] == "Task172BlockedResult":
            probe_result = Task172BlockedResult.model_validate(result_projection, strict=True)
            result_hash = rating.recompute_task172_blocked_result_hash(probe_result)
            if (
                probe_result.failure_code != probe["task172_failure_code"]
                or probe_result.field_path != probe["task172_field_path"]
                or probe_result.request_hash != probe["task172_request_hash"]
            ):
                raise RuntimeError(
                    f"R2 blocked Decimal probe identity mismatch: {probe['probe_index']}"
                )
        else:
            raise RuntimeError(
                f"R2 evidence has unknown Task172 result type: {probe['task172_result_type']}"
            )
        expected_result_hash = (
            probe_result.result_hash
            if type(probe_result) is Task172LocalResult
            else probe_result.blocked_result_hash
        )
        if result_hash != expected_result_hash or result_hash != probe["task172_result_hash"]:
            raise RuntimeError(f"R2 Decimal probe result replay failed: {probe['probe_index']}")
        for provider_record in probe["provider_ph_inputs_outputs"]:
            if (
                canonical_sha256(provider_record["provider_input_snapshot"])
                != provider_record["provider_input_snapshot_hash"]
            ):
                raise RuntimeError(f"R2 provider snapshot replay failed: {probe['probe_index']}")
    trace_events = []
    if R2_TRACE_PATH.is_file():
        with R2_TRACE_PATH.open(encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                event = json.loads(line)
                if event.get("sequence") != line_number:
                    raise RuntimeError(f"R2 trace sequence mismatch at {line_number}")
                trace_events.append(event)
    print("R2_EXECUTION_EVIDENCE_HASH_REPLAY=PASS")
    print(f"R2_TRACE_EVENT_COUNT={len(trace_events)}")
    print("N32_RECONSTRUCTION_IDENTITY_REPLAY=PASS")
    print(
        "EXACT_TARGET_CELL_REPLAY=PASS"
        if exact_n32_signature or capture.get("exact_target_cell_reconstructed")
        else "EXACT_TARGET_CELL_REPLAY=NOT_ESTABLISHED"
    )
    print(
        f"ENDPOINT_NATIVE_IDENTITY_REPLAY_COUNT={len(replay['endpoint_native_identity_replays'])}"
    )
    print(
        "TARGET_TRIAL_NATIVE_IDENTITY_REPLAY_COUNT="
        f"{replay['target_cell_trial_task172_identity_replay_count']}"
    )
    print(f"DECIMAL_Q_PROBE_COUNT={len(probes)}")
    fatal = capture.get("fatal_exception")
    if fatal:
        print(f"DECIMAL_PROBE_STOP_BEFORE_NATIVE_CALL={fatal['type']}")


def main() -> None:
    global LIVE_CAPTURE
    parser = argparse.ArgumentParser()
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--execute-r2-exact-n32", action="store_true")
    parser.add_argument("--replay-r2", action="store_true")
    parser.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    selected = sum(
        (
            args.preflight_only,
            args.execute_r2_exact_n32,
            args.replay_r2,
            args.replay_only,
        )
    )
    if selected != 1:
        raise SystemExit(
            "select exactly one of --preflight-only, --execute-r2-exact-n32, "
            "--replay-r2, or --replay-only"
        )
    if args.replay_only:
        _replay()
        return
    if args.replay_r2:
        _replay_r2()
        return
    if args.preflight_only:
        try:
            preflight = _run_preflight()
        except Exception as exc:
            preflight = {
                "schema_version": "task173.decimal-q-diagnostic-r2-preflight.v1",
                "task_id": R2_TASK_ID,
                "execution_start_head": R2_EXECUTION_START_HEAD,
                "preflight_only": True,
                "numeric_solver_invoked": False,
                "full_candidate_rating_invoked": False,
                "public_sizing_invoked": False,
                "checks": {},
                "preflight_result": "FAIL",
                "preflight_exception": {
                    "type": type(exc).__name__,
                    "text": str(exc),
                },
            }
        preflight["canonical_evidence_hash"] = canonical_sha256(preflight)
        digest = _write_json_atomic(R2_PREFLIGHT_EVIDENCE_PATH, preflight)
        for name, value in preflight.get("checks", {}).items():
            print(f"{name}={value}")
        print(f"PREFLIGHT_RESULT={preflight['preflight_result']}")
        print(f"PREFLIGHT_EVIDENCE_SHA256={digest}")
        print(f"PREFLIGHT_EVIDENCE_PATH={R2_PREFLIGHT_EVIDENCE_PATH.relative_to(ROOT)}")
        if preflight["preflight_result"] != "PASS":
            raise SystemExit(1)
        return
    if R2_CHECKPOINT_PATH.exists() or R2_TRACE_PATH.exists() or R2_EXECUTION_EVIDENCE_PATH.exists():
        raise SystemExit("R2 execution artifacts already exist; refusing another reconstruction")
    preflight = _run_preflight()
    required_checks = (
        "OBSERVER_VALID_RESULT_TEST",
        "OBSERVER_BLOCKED_RESULT_TEST",
        "DECIMAL_PROBE_BLOCKED_RESULT_TEST",
        "UNKNOWN_TYPE_FAIL_CLOSED",
        "OBSERVER_EXCEPTION_RECOVERY",
        "CHECKPOINT_EXCEPTION_RECOVERY",
        "R1_FROZEN_IDENTITIES_PRESERVED",
    )
    checks_pass = all(preflight["checks"].get(name) == "PASS" for name in required_checks)
    checks_pass = checks_pass and preflight["checks"].get("PRODUCTION_CODE_CHANGED") == "false"
    if not checks_pass or _git("rev-parse", "HEAD") != R2_EXECUTION_START_HEAD:
        raise SystemExit("R2 preflight or exact execution-start HEAD gate failed")
    preflight["canonical_evidence_hash"] = canonical_sha256(preflight)
    _write_json_atomic(R2_PREFLIGHT_EVIDENCE_PATH, preflight)
    started = time.monotonic()
    try:
        capture = _execute()
    except BaseException as exc:
        capture = (
            {key: value for key, value in LIVE_CAPTURE.items() if not key.startswith("_")}
            if LIVE_CAPTURE is not None
            else {}
        )
        capture.update(
            {
                "task_id": R2_TASK_ID,
                "execution_start_head": R2_EXECUTION_START_HEAD,
                "runtime_source_head": RUNTIME_HEAD,
                "fatal_exception": {
                    "type": type(exc).__name__,
                    "text": str(exc),
                },
                "decimal_probe_count": 0,
                "exact_target_cell_reconstructed": False,
                "elapsed_wall_seconds": time.monotonic() - started,
            }
        )
    finally:
        LIVE_CAPTURE = None
    payload: dict[str, Any] = {
        "schema_version": "task173.candidate-a-exact-cell-decimal-q-diagnostic-r2.v1",
        "task_id": R2_TASK_ID,
        "repository": "xuezhiorange-png/hxforge-agent",
        "pr_number": 283,
        "pr_state_required": "OPEN_DRAFT",
        "execution_start_head": R2_EXECUTION_START_HEAD,
        "final_evidence_head_at_capture": _git("rev-parse", "HEAD"),
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "completion_sizing_request_hash": COMPLETION_REQUEST_HASH,
        "candidate_rating_request_hash": RATING_REQUEST_HASH,
        "candidate_id": CANDIDATE_ID,
        "candidate_hash": CANDIDATE_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "reviewed_r2a_authority_hash": R2A_AUTHORITY_HASH,
        "target": {
            "mesh_subdivisions": TARGET_N,
            "physical_support_id": TARGET_SUPPORT_ID,
            "left_q_w": repr(TARGET_LEFT_Q),
            "right_q_w": repr(TARGET_RIGHT_Q),
        },
        "production_code_changed": False,
        "r2a_authority_changed": False,
        "task172_contract_changed": False,
        "numerical_tolerance_changed": False,
        "public_candidate_full_rating_reexecuted": False,
        "public_sizing_reexecuted": False,
        "public_sizing_invocation_performed_by_this_gate": False,
        "task175_executed": False,
        "preflight": preflight,
        "checkpoint_path": str(R2_CHECKPOINT_PATH.relative_to(ROOT)),
        "trace_path": str(R2_TRACE_PATH.relative_to(ROOT)),
        "diagnostic_execution": capture,
    }
    if capture.get("fatal_exception"):
        payload["result"] = "DIAGNOSTIC_EXECUTION_STOPPED_WITH_EXCEPTION"
    elif capture.get("exact_target_cell_reconstructed") and capture.get(
        "decimal_probe_experiment", {}
    ).get("point_root_recovered"):
        payload["result"] = "EXACT_TARGET_CELL_POINT_ROOT_RECOVERED"
    elif capture.get("exact_target_cell_reconstructed"):
        payload["result"] = "DIAGNOSTIC_COMPLETED_POINT_ROOT_NOT_FOUND_IN_FINITE_PROBES"
    else:
        payload["result"] = "EXACT_TARGET_CELL_RECONSTRUCTION_NOT_ESTABLISHED"
    payload["canonical_evidence_hash"] = canonical_sha256(payload)
    digest = _write_json_atomic(R2_EXECUTION_EVIDENCE_PATH, payload)
    print(f"R2_EVIDENCE_PATH={R2_EXECUTION_EVIDENCE_PATH.relative_to(ROOT)}")
    print(f"R2_EVIDENCE_SHA256={digest}")
    print(f"EXACT_TARGET_CELL_RECONSTRUCTED={capture.get('exact_target_cell_reconstructed')}")
    print(f"DECIMAL_Q_PROBE_COUNT={capture.get('decimal_probe_count', 0)}")
    print(f"TASK172_TOTAL_CALLS={capture.get('task172_validator_call_count', 0)}")
    if capture.get("decimal_probe_experiment"):
        probes = capture["decimal_probe_experiment"]
        print(f"MIN_ABS_F_W={probes.get('min_abs_f_w')}")
        print(f"POINT_ROOT_RECOVERED={probes.get('point_root_recovered')}")
        print(f"PROVIDER_PH_PLATEAU_CONFIRMED={probes.get('provider_ph_plateau_confirmed')}")
        print(f"TASK172_DISCONTINUITY_OBSERVED={probes.get('task172_discontinuity_observed')}")
    if capture.get("fatal_exception"):
        print(f"FATAL={capture['fatal_exception']['type']}:{capture['fatal_exception']['text']}")


if __name__ == "__main__":
    main()
