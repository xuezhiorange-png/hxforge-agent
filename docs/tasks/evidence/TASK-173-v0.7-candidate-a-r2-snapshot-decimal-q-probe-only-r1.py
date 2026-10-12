#!/usr/bin/env python3
"""R3 bounded Decimal-q probes from the persisted Candidate A R2 snapshot.

This runner never reconstructs an n=32 mesh or invokes Candidate Rating,
public Sizing, or TASK175.  The only numerical solver call is the native local
Task172 validator, behind an explicit 140-unit ceiling.
"""

from __future__ import annotations

import argparse
import collections.abc
import contextlib
import hashlib
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
import types
import typing
from dataclasses import MISSING, fields, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from pydantic import BaseModel

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime import (
    service as task172_service,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172BlockedResult,
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
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    ReferencePlanePair,
    ReferencePlaneToken,
)
from hexagent.properties.coolprop_provider import CoolPropProvider

ROOT = Path(__file__).resolve().parents[3]
TASK_ID = "STAGE3_TASK173_CANDIDATE_A_R2_SNAPSHOT_DECIMAL_Q_PROBE_ONLY_RECOVERY_R1"
START_HEAD = "bfe4566229e7f70b234f6d1dcf9874cea4b1068f"
RUNTIME_HEAD = "21386a88f8290538172e9389ed46f50c3697a426"
RUNTIME_TREE = "ce61a818b82f908729d2bdf4553cc27012354952"
COMPLETION_REQUEST_HASH = "5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae"
TASK168_SPACE_HASH = "aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea"
CANDIDATE_ID = "adeab5b1-a339-5eb3-aa66-011ffe49bac0"
CANDIDATE_HASH = "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767"
RATING_REQUEST_HASH = "1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7"
R2A_AUTHORITY_HASH = "25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e"
TARGET_N = 32
TARGET_LEFT_Q = 268.4228547695099
TARGET_RIGHT_Q = 268.42285476950997
TARGET_SUPPORT_ID = (
    "urn:hxforge:task171:candidate:"
    "f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767:support:2"
)
EXPECTED_RAW = {
    "execution": {
        "path": (
            "docs/tasks/evidence/"
            "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2.json"
        ),
        "bytes": 471057121,
        "sha256": "59e4e8218f61551ae00421ebcc88cf4ea8870cadd5bbca22420caa9c8930c6fe",
    },
    "checkpoint": {
        "path": (
            "docs/tasks/evidence/"
            "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-execution/"
            "checkpoint.json"
        ),
        "bytes": 471036749,
        "sha256": "87f0391c4ae26008a6bfe93c6e7a1f1657e1925658550dbd0ca55da96e9f138f",
    },
    "trace": {
        "path": (
            "docs/tasks/evidence/"
            "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-execution/"
            "trace.jsonl"
        ),
        "bytes": 311208673,
        "sha256": "e8c719c48842ecb5369a63a375c5004af81152c260c07dbc96a218c9113d1618",
    },
}
EVIDENCE_ROOT = ROOT / "docs/tasks/evidence"
R2_SUMMARY_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-execution-summary.json"
)
R2_REPLAY_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-replay.py"
)
R2_PREFLIGHT_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r2-preflight.json"
)
R1_RUNNER_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-candidate-a-exact-cell-decimal-q-recovery-diagnostic-r1.py"
)
COMPLETION_REQUEST_REPLAY_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-full-sizing-completion-request-r1-replay.py"
)
CANDIDATE_RECEIPT_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json"
)
R2A_AUTHORITY_PATH = EVIDENCE_ROOT / (
    "TASK-173-v0.7-provider-quantization-transient-decision-enclosure-r2a.json"
)
STEM = "TASK-173-v0.7-candidate-a-r2-snapshot-decimal-q-probe-only-r1"
PREFLIGHT_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}-preflight-r3.json"
EVIDENCE_PATH = ROOT / "docs/tasks/evidence" / f"{STEM}.json"
OUTPUT_DIR = ROOT / "docs/tasks/evidence" / f"{STEM}-execution"
MAX_NEW_TASK172_VALIDATIONS = 140
ENDPOINT_IDENTITY_BUDGET_UNITS = 2
UNIFORM_INTERVALS = 64
ADAPTIVE_BISECTION_CAP = 64


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
            length += len(block)
    return digest.hexdigest(), length


def _git(*args: str, check: bool = True) -> str:
    result = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=False)
    if check and result.returncode:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load committed evidence module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


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


def _pair_from_projection(value: Any) -> ReferencePlanePair:
    if type(value) is ReferencePlanePair:
        return value
    if (
        isinstance(value, dict)
        and {"start", "end"} <= set(value)
        and set(value) <= {"__task173_type__", "start", "end", "kind"}
        and value.get("__task173_type__", "ReferencePlanePair") == "ReferencePlanePair"
    ):
        pair = ReferencePlanePair(
            start=ReferencePlaneToken(value["start"]),
            end=ReferencePlaneToken(value["end"]),
        )
        if "kind" in value and value["kind"] != pair.kind:
            raise ValueError("ReferencePlanePair kind does not match its tokens")
        return pair
    raise TypeError("malformed ReferencePlanePair projection")


def _rehydrate_typed(expected: Any, value: Any) -> Any:
    """Rebuild known native dataclasses/models without weakening their schemas."""
    if value is None:
        return None
    if expected is Any or expected is typing.Any:
        return _restore_pairs(value)
    if expected is ReferencePlanePair:
        return _pair_from_projection(value)

    origin = get_origin(expected)
    args = get_args(expected)
    if origin in (typing.Union, types.UnionType):
        failures: list[Exception] = []
        for option in args:
            if option is type(None):
                continue
            try:
                return _rehydrate_typed(option, value)
            except (TypeError, ValueError, KeyError) as exc:
                failures.append(exc)
        if type(None) in args:
            return None
        raise TypeError(f"cannot rehydrate union {expected}: {failures!r}")
    if origin is typing.Literal:
        if value not in args:
            raise ValueError(f"literal value {value!r} is outside {args!r}")
        return value
    if origin in (tuple, list, collections.abc.Sequence, collections.abc.MutableSequence):
        item_type = args[0] if args else Any
        values = [_rehydrate_typed(item_type, item) for item in value]
        return tuple(values) if origin is tuple else values
    if origin in (dict, collections.abc.Mapping, collections.abc.MutableMapping):
        key_type, value_type = args if args else (Any, Any)
        return {
            _rehydrate_typed(key_type, key): _rehydrate_typed(value_type, item)
            for key, item in value.items()
        }
    if expected is Decimal:
        return value if type(value) is Decimal else Decimal(str(value))
    if isinstance(expected, type) and issubclass(expected, Enum):
        return value if type(value) is expected else expected(value)
    if isinstance(expected, type) and issubclass(expected, BaseModel):
        if type(value) is expected:
            return expected.model_validate(value, strict=True)
        restored = _restore_pairs(value)
        return expected.model_validate(restored, strict=False)
    if isinstance(expected, type) and is_dataclass(expected):
        if type(value) is expected:
            return value
        hints = get_type_hints(expected)
        if not isinstance(value, dict):
            raise TypeError(f"expected mapping for {expected.__name__}")
        kwargs = {
            field.name: _rehydrate_typed(hints.get(field.name, field.type), value[field.name])
            for field in fields(expected)
            if field.name in value
        }
        missing = {field.name for field in fields(expected) if field.name not in kwargs}
        required_missing = {
            field.name
            for field in fields(expected)
            if field.name in missing
            and field.default is MISSING
            and field.default_factory is MISSING
        }
        if required_missing:
            raise ValueError(
                f"missing required {expected.__name__} fields: {sorted(required_missing)}"
            )
        return expected(**kwargs)
    if expected in (str, int, float, bool):
        return expected(value)
    return _restore_pairs(value)


def _native_projection(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if type(value) is ReferencePlanePair:
        return {
            "__task173_type__": "ReferencePlanePair",
            "start": value.start.value,
            "end": value.end.value,
        }
    if isinstance(value, BaseModel):
        return {name: _native_projection(getattr(value, name)) for name in type(value).model_fields}
    if is_dataclass(value):
        return {
            field.name: _native_projection(getattr(value, field.name)) for field in fields(value)
        }
    if isinstance(value, collections.abc.Mapping):
        return {str(key): _native_projection(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_native_projection(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    raise TypeError(f"unsupported native evidence type: {type(value).__name__}")


def _model_json(value: Any) -> dict[str, Any]:
    return value.model_dump(mode="json", fallback=rating._candidate_json_fallback)


def _candidate_request_from_projection(projection: dict[str, Any]) -> CandidateRatingRequest:
    from hexagent.exchangers.shell_tube.tube_side.valid_result import Task025ValidResult
    from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
        Task029SuccessResult,
    )

    restored = dict(projection)
    restored["task025_result"] = _rehydrate_typed(Task025ValidResult, restored["task025_result"])
    restored["task029_result"] = _rehydrate_typed(Task029SuccessResult, restored["task029_result"])
    request = CandidateRatingRequest.model_validate(restored, strict=False)
    request = CandidateRatingRequest.model_validate(request, strict=True)
    if type(request) is not CandidateRatingRequest:
        raise TypeError("candidate Rating request did not rehydrate to exact native model")
    return request


def _load_r2_basis() -> tuple[dict[str, Any], dict[str, Any]]:
    replay = _load_module("r2_snapshot_replay_for_r3", R2_REPLAY_PATH)
    regenerated = replay._validate_raw_capture()
    committed_summary = json.loads(R2_SUMMARY_PATH.read_text(encoding="utf-8"))
    committed_hash = committed_summary.get("canonical_summary_hash")
    summary_without_hash = dict(committed_summary)
    summary_without_hash.pop("canonical_summary_hash", None)
    if canonical_sha256(summary_without_hash) != committed_hash:
        raise RuntimeError("committed R2 summary canonical hash mismatch")
    if regenerated.get("canonical_summary_hash") != committed_hash:
        raise RuntimeError("raw R2 files do not regenerate the committed summary")
    replay._replay()
    return regenerated, committed_summary


def _replay_completion_request() -> str:
    replay = _load_module("frozen_completion_request_replay_for_r3", COMPLETION_REQUEST_REPLAY_PATH)
    request_evidence = json.loads(replay.EVIDENCE_PATH.read_text(encoding="utf-8"))
    replay._replay(request_evidence)
    if request_evidence.get("completion_sizing_request_hash") != COMPLETION_REQUEST_HASH:
        raise RuntimeError("frozen completion request hash differs from R3 authorization")
    if request_evidence.get("task168_candidate_space_hash") != TASK168_SPACE_HASH:
        raise RuntimeError("frozen completion request candidate-space identity mismatch")
    return _sha256_bytes(COMPLETION_REQUEST_REPLAY_PATH.read_bytes())


def _raw_artifact_receipts() -> dict[str, dict[str, Any]]:
    receipts: dict[str, dict[str, Any]] = {}
    for label, expected in EXPECTED_RAW.items():
        path = ROOT / expected["path"]
        digest, length = _sha256_file(path)
        if digest != expected["sha256"] or length != expected["bytes"]:
            raise RuntimeError(f"R2 raw {label} artifact identity mismatch")
        receipts[label] = {
            "path": expected["path"],
            "raw_bytes": length,
            "sha256": digest,
            "preserved_read_only": True,
        }
    return receipts


def _endpoint_native(endpoint: dict[str, Any], label: str) -> tuple[Any, Any, dict[str, Any]]:
    req_projection = endpoint["task172_request_projection"]
    result_projection = endpoint["task172_result_projection"]
    req = CandidateTask172LocalRequest.model_validate(_restore_pairs(req_projection), strict=False)
    result = Task172LocalResult.model_validate(_restore_pairs(result_projection), strict=False)
    req = CandidateTask172LocalRequest.model_validate(req, strict=True)
    result = Task172LocalResult.model_validate(result, strict=True)
    req_hash = rating.recompute_task172_request_hash(req)
    result_hash = rating.recompute_task172_result_hash(result)
    if (
        req_hash != endpoint["task172_request_hash"]
        or result_hash != endpoint["task172_result_hash"]
        or req_hash != endpoint["task172_call"]["request_hash"]
        or result_hash != endpoint["task172_call"]["result_hash"]
    ):
        raise RuntimeError(f"{label} endpoint native hash replay failed")
    if (
        result.status != "VALIDATED"
        or result.request_hash != req_hash
        or req.case_id != CANDIDATE_ID
        or req.case_revision_id != CANDIDATE_ID
        or req.support.physical_segment_id != TARGET_SUPPORT_ID
        or result.physical_segment_id != TARGET_SUPPORT_ID
        or result.physical_support_id != rating.recompute_task172_support_id(req)
        or req.topology.mesh_identity
        != endpoint["task172_request_projection"]["topology"]["mesh_identity"]
        or req.support.tube_cell_id != endpoint["support_projection"]["tube_cell_id"]
        or req.support.shell_cell_id != endpoint["support_projection"]["shell_cell_id"]
        or req.support.wall_interface_id != endpoint["support_projection"]["wall_interface_id"]
    ):
        raise RuntimeError(f"{label} endpoint native binding mismatch")
    projected_request = _model_json(req)
    projected_result = _model_json(result)
    if projected_request != req_projection or projected_result != result_projection:
        raise RuntimeError(f"{label} endpoint projection changed during rehydration")
    q_float = float(endpoint["q_w_repr"])
    q_binary = Decimal.from_float(q_float)
    with localcontext() as context:
        context.prec = 100
        f_exact = q_binary - result.signed_q_hot_to_cold_w
    if (
        str(f_exact) != endpoint["f_exact_binary64_endpoint"]
        or str(rating._d(q_float) - result.signed_q_hot_to_cold_w)
        != endpoint["f_production_decimal_context"]
    ):
        raise RuntimeError(f"{label} endpoint F replay failed")
    facts = {
        "label": label,
        "q_w_repr": endpoint["q_w_repr"],
        "q_binary64_hex": endpoint["q_w_binary64_hex"],
        "status": result.status,
        "task172_request_hash": req_hash,
        "task172_result_hash": result_hash,
        "task172_signed_q_hot_to_cold_w": str(result.signed_q_hot_to_cold_w),
        "F_native_decimal_context_w": endpoint["f_production_decimal_context"],
        "F_exact_binary64_w": str(f_exact),
        "request_projection": req_projection,
        "result_projection": result_projection,
        "provider_ph_calls": endpoint["provider_ph_calls"],
    }
    return req, result, facts


def _provider_signature(q: Decimal, tube_h: Decimal, shell_h: Decimal) -> dict[str, Any]:
    with localcontext() as context:
        context.prec = 70
        tube_downstream_h = tube_h - q / rating.TUBE_MASS_FLOW_KG_S
        shell_next_h = shell_h - q / rating.SHELL_MASS_FLOW_KG_S
        tube_mid_h = (tube_h + tube_downstream_h) / Decimal(2)
        shell_mid_h = (shell_h + shell_next_h) / Decimal(2)
    enthalpies = {
        "tube_downstream_h": tube_downstream_h,
        "shell_next_face_h": shell_next_h,
        "tube_midpoint_h": tube_mid_h,
        "shell_midpoint_h": shell_mid_h,
    }
    provider_inputs = {
        name: {"decimal": str(value), "binary64_hex": float(value).hex()}
        for name, value in enthalpies.items()
    }
    return {
        "q_decimal": str(q),
        "enthalpies": {name: str(value) for name, value in enthalpies.items()},
        "provider_ph_input_signature": tuple(
            provider_inputs[name]["binary64_hex"] for name in enthalpies
        ),
        "provider_inputs": provider_inputs,
    }


def _provider_snapshot(state: Any) -> dict[str, Any]:
    return {
        "native": _native_projection(state.native),
        "property_snapshot": state.snapshot.model_dump(mode="json"),
        "property_snapshot_hash": state.snapshot_hash,
    }


def _probe_projection_replay(record: dict[str, Any]) -> dict[str, Any]:
    result_type = record.get("task172_result_type")
    if result_type not in {"Task172LocalResult", "Task172BlockedResult"}:
        raise TypeError(f"unknown Task172 result type in probe: {result_type!r}")
    request = CandidateTask172LocalRequest.model_validate(
        _restore_pairs(record["task172_request_projection"]), strict=False
    )
    request = CandidateTask172LocalRequest.model_validate(request, strict=True)
    request_hash = rating.recompute_task172_request_hash(request)
    if request_hash != record["task172_request_hash"]:
        raise RuntimeError("Decimal probe Task172 request hash replay failed")
    result_projection = _restore_pairs(record["task172_result_projection"])
    if result_type == "Task172LocalResult":
        result = Task172LocalResult.model_validate(result_projection, strict=False)
        result = Task172LocalResult.model_validate(result, strict=True)
        result_hash = rating.recompute_task172_result_hash(result)
        if result.request_hash != request_hash or result.status != "VALIDATED":
            raise RuntimeError("Decimal probe valid result is not bound to its request")
        with localcontext() as context:
            context.prec = 100
            exact_f = Decimal(record["q_decimal_exact"]) - result.signed_q_hot_to_cold_w
        if str(exact_f) != record["F_decimal_high_precision"]:
            raise RuntimeError("Decimal probe F replay failed")
        point_pass = abs(exact_f) <= Decimal("1e-6")
        if point_pass != record["ordinary_point_root_tolerance_pass"]:
            raise RuntimeError("Decimal probe ordinary-root decision replay failed")
        result_id = result.result_id
        status = result.status
    else:
        result = Task172BlockedResult.model_validate(result_projection, strict=False)
        result = Task172BlockedResult.model_validate(result, strict=True)
        result_hash = rating.recompute_task172_blocked_result_hash(result)
        if result.request_hash != request_hash:
            raise RuntimeError("Decimal probe blocked result is not bound to its request")
        if result.failure_code != record.get("task172_failure_code"):
            raise RuntimeError("Decimal probe blocked failure code replay failed")
        if result.field_path != record.get("task172_field_path"):
            raise RuntimeError("Decimal probe blocked field path replay failed")
        if result_hash != record.get("task172_blocked_result_hash", result.blocked_result_hash):
            raise RuntimeError("Decimal probe blocked hash replay failed")
        result_id = None
        status = result.status
    expected_hash = (
        result.result_hash if type(result) is Task172LocalResult else result.blocked_result_hash
    )
    if result_hash != expected_hash or result_hash != record["task172_result_hash"]:
        raise RuntimeError("Decimal probe Task172 result hash replay failed")
    provider_replays = 0
    for provider_item in record["provider_ph_inputs_outputs"]:
        snapshot = provider_item["provider_input_snapshot"]
        snapshot_hash = canonical_sha256(snapshot)
        if snapshot_hash != provider_item["provider_input_snapshot_hash"]:
            raise RuntimeError("Decimal probe provider snapshot hash replay failed")
        provider_h = float(provider_item["provider_enthalpy_float"])
        if provider_h.hex() != provider_item["provider_enthalpy_float_hex"] or snapshot.get(
            "inputs", {}
        ).get("enthalpy_j_kg") != str(provider_h):
            raise RuntimeError("Decimal probe provider PH input replay failed")
        provider_replays += 1
    if provider_replays != 4:
        raise RuntimeError("Decimal probe did not preserve all four provider PH states")
    return {
        "request_hash": request_hash,
        "result_hash": result_hash,
        "result_id": result_id,
        "status": status,
        "provider_snapshot_replay_count": provider_replays,
    }


def _fixture_probe(
    request: CandidateTask172LocalRequest,
    result: Task172LocalResult | Task172BlockedResult,
    endpoint: dict[str, Any],
) -> dict[str, Any]:
    identity = rating.recompute_task172_request_hash(request)
    result_type = type(result).__name__
    result_hash = (
        rating.recompute_task172_result_hash(result)
        if type(result) is Task172LocalResult
        else rating.recompute_task172_blocked_result_hash(result)
    )
    provider_records = []
    for item in endpoint["provider_ph_calls"]:
        state = item["state_after_provider"]
        provider_records.append(
            {
                "provider_enthalpy_float": item["provider_enthalpy_float"],
                "provider_enthalpy_float_hex": item["provider_enthalpy_float_hex"],
                "provider_input_snapshot": state["property_snapshot"],
                "provider_input_snapshot_hash": state["property_snapshot_hash"],
            }
        )
    record: dict[str, Any] = {
        "probe_index": 0,
        "q_decimal_exact": str(Decimal.from_float(float(endpoint["q_w_repr"]))),
        "task172_request_projection": _model_json(request),
        "task172_request_hash": identity,
        "task172_result_type": result_type,
        "task172_result_projection": _model_json(result),
        "task172_result_hash": result_hash,
        "provider_ph_inputs_outputs": provider_records,
        "task172_status": result.status,
    }
    if type(result) is Task172LocalResult:
        with localcontext() as context:
            context.prec = 100
            f_value = Decimal(record["q_decimal_exact"]) - result.signed_q_hot_to_cold_w
        record.update(
            {
                "task172_signed_q_hot_to_cold_w": str(result.signed_q_hot_to_cold_w),
                "F_decimal_high_precision": str(f_value),
                "ordinary_point_root_tolerance_pass": abs(f_value) <= Decimal("1e-6"),
            }
        )
    else:
        record.update(
            {
                "task172_failure_code": result.failure_code,
                "task172_field_path": result.field_path,
                "task172_blocked_result_hash": result.blocked_result_hash,
                "ordinary_point_root_tolerance_pass": False,
            }
        )
    return record


class R3CheckpointStore:
    """Append-only event log plus compact atomic checkpoint for R3 probes."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=False)
        self.trace_path = root / "trace.jsonl"
        self.checkpoint_path = root / "checkpoint.json"
        self.event_count = 0
        self.last_event: dict[str, Any] | None = None

    def append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        event = {
            "sequence": self.event_count + 1,
            "captured_at_utc": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": payload,
        }
        encoded = json.dumps(event, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        with self.trace_path.open("a", encoding="utf-8") as stream:
            stream.write(encoded + "\n")
            stream.flush()
            os.fsync(stream.fileno())
        self.event_count += 1
        self.last_event = event

    def write_checkpoint(
        self,
        capture: dict[str, Any],
        *,
        runtime_identity: dict[str, Any],
        request_identity: dict[str, Any],
    ) -> str:
        latest_completed = capture.get("decimal_q_probes", [])
        payload = {
            "schema_version": "task173.candidate-a-r2-snapshot-probe-checkpoint.v1",
            "checkpointed_at_utc": datetime.now(UTC).isoformat(),
            "runtime_identity": runtime_identity,
            "request_identity": request_identity,
            "task172_validator_call_count": capture.get("task172_validator_call_count", 0),
            "provider_ph_coordinate_sweep": capture.get("provider_ph_coordinate_sweep"),
            "current_mesh_subdivisions": TARGET_N,
            "current_target_cell": capture.get("current_target_cell"),
            "execution_phase": capture.get("execution_phase"),
            "decimal_q_probe_in_progress": capture.get("decimal_q_probe_in_progress"),
            "latest_completed_probe": latest_completed[-1] if latest_completed else None,
            "last_exception": capture.get("last_exception"),
            "last_event_sequence": self.event_count,
            "last_event_type": None if self.last_event is None else self.last_event["event_type"],
        }
        encoded = (
            json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        ).encode()
        temp = self.root / f".checkpoint.{os.getpid()}.{time.monotonic_ns()}.tmp"
        try:
            with temp.open("xb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, self.checkpoint_path)
            directory_fd = os.open(self.root, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            temp.unlink(missing_ok=True)
        return _sha256_bytes(encoded)


def _strict_persist(
    capture: dict[str, Any],
    store: R3CheckpointStore | None,
    event_type: str,
    payload: dict[str, Any],
    *,
    checkpoint: bool,
) -> None:
    if store is None:
        return
    store.append_event(event_type, payload)
    if checkpoint:
        store.write_checkpoint(
            capture,
            runtime_identity=capture["runtime_identity"],
            request_identity=capture["request_identity"],
        )
        capture["last_successful_checkpoint_call_count"] = capture.get(
            "task172_validator_call_count", 0
        )


def _raw_receipts_match(receipts: dict[str, Any]) -> bool:
    for name, expected in EXPECTED_RAW.items():
        path = ROOT / expected["path"]
        digest, length = _sha256_file(path)
        if (
            digest != receipts[name]["sha256"]
            or length != receipts[name]["raw_bytes"]
            or digest != expected["sha256"]
            or length != expected["bytes"]
        ):
            return False
    return True


def _provider_restore_state(provider: CoolPropProvider, saved: dict[str, Any]) -> Any:
    enthalpy = Decimal(str(saved["native"]["enthalpy_j_kg"]))
    state = rating._state_from_enthalpy(provider, enthalpy)
    if _provider_snapshot(state) != saved:
        raise RuntimeError("provider rehydrated upstream state differs from R2 snapshot")
    return state


def _load_preflight_basis(preflight: dict[str, Any]) -> tuple[Any, Any, Any, Any, Any, Any]:
    basis = preflight["rehydration_basis"]
    candidate_request = _candidate_request_from_projection(
        basis["candidate_rating_request_projection"]
    )
    if candidate_rating_request_hash(candidate_request) != RATING_REQUEST_HASH:
        raise RuntimeError("candidate Rating request identity changed after preflight")
    context = rating._candidate_context(candidate_request)
    left_endpoint = basis["left_endpoint"]
    right_endpoint = basis["right_endpoint"]
    left_request, left_result, _ = _endpoint_native(left_endpoint, "LEFT")
    right_request, right_result, _ = _endpoint_native(right_endpoint, "RIGHT")
    if left_request.support != right_request.support:
        raise RuntimeError("left/right saved endpoint support identities differ")
    support = left_request.support
    provider = CoolPropProvider()
    tube_upstream = _provider_restore_state(provider, basis["tube_upstream_state"])
    shell_physical_left = _provider_restore_state(provider, basis["shell_physical_left_state"])
    if (
        provider._construction_fingerprint != basis["provider_configuration_fingerprint"]
        or _native_projection(support) != basis["support_projection"]
    ):
        raise RuntimeError("provider/support identity differs from frozen R2 snapshot")
    return (
        candidate_request,
        context,
        support,
        provider,
        tube_upstream,
        shell_physical_left,
    )


def _build_preflight() -> dict[str, Any]:
    current_head = _git("rev-parse", "HEAD")
    if current_head != START_HEAD:
        raise RuntimeError(f"preflight requires exact start HEAD {START_HEAD}; got {current_head}")
    r1 = _load_module("r1_decimal_probe_helpers_for_r3", R1_RUNNER_PATH)
    runtime_binding = r1._assert_runtime_binding(execution=False)
    completion_request_replay_sha256 = _replay_completion_request()
    raw_receipts = _raw_artifact_receipts()
    regenerated_summary, committed_summary = _load_r2_basis()
    if regenerated_summary["raw_artifacts"]["raw_artifacts_included_in_commit"] is not False:
        raise RuntimeError("R2 raw artifacts were unexpectedly claimed as committed")
    if (
        regenerated_summary["execution"]["task172_total_calls"] != 144217
        or regenerated_summary["execution"]["task172_numerical_hole_count"] != 27
        or regenerated_summary["execution"]["target_cell_trial_count"] != 749
        or regenerated_summary["execution"]["target_trial_identity_replay_count"] != 749
        or regenerated_summary["execution"]["target_endpoint_identity_replay"] != "PASS"
    ):
        raise RuntimeError("R2 call/hole/target identity counts do not match frozen receipt")
    if committed_summary["execution"]["decimal_q_probe_count"] != 0:
        raise RuntimeError("R2 receipt unexpectedly includes previous Decimal probes")

    candidate_receipt_bytes = CANDIDATE_RECEIPT_PATH.read_bytes()
    candidate_receipt_sha = _sha256_bytes(candidate_receipt_bytes)
    if candidate_receipt_sha != "80e4648a91d1da2798dc608252a1a67111f1248711b8595343ab8c0739705b42":
        raise RuntimeError("frozen candidate Rating receipt SHA-256 mismatch")
    candidate_receipt = json.loads(candidate_receipt_bytes)
    candidate_entry = candidate_receipt["candidates"][CANDIDATE_ID]
    candidate_request_projection = candidate_entry["candidate_rating_request_projection"]
    candidate_request = _candidate_request_from_projection(candidate_request_projection)
    if (
        candidate_rating_request_hash(candidate_request) != RATING_REQUEST_HASH
        or candidate_entry["candidate_hash"] != CANDIDATE_HASH
        or candidate_entry["candidate_rating_request_hash"] != RATING_REQUEST_HASH
        or candidate_request.candidate_space_hash != TASK168_SPACE_HASH
        or candidate_request.candidate_id != CANDIDATE_ID
        or candidate_request.candidate_hash != CANDIDATE_HASH
    ):
        raise RuntimeError("frozen Candidate A Rating request identity mismatch")
    rating_context = rating._candidate_context(candidate_request)

    failure = regenerated_summary["execution"]["failure"]
    if (
        regenerated_summary["failed_cell"]["mesh_subdivisions"] != TARGET_N
        or failure["mesh_subdivisions"] != TARGET_N
        or failure["support_id"] != TARGET_SUPPORT_ID
        or failure["code"] != "BLOCKED_ACCEPTED_TRAJECTORY_PROVIDER_QUANTIZATION_UNRESOLVED"
        or failure["shooting_enthalpy_j_kg"] != "107518.9165931962933844840526580810546875"
    ):
        raise RuntimeError("R2 failed-cell identity differs from requested target")
    left_endpoint = regenerated_summary["failed_cell"]["left_endpoint"]
    right_endpoint = regenerated_summary["failed_cell"]["right_endpoint"]
    left_request, left_result, left_facts = _endpoint_native(left_endpoint, "LEFT")
    right_request, right_result, right_facts = _endpoint_native(right_endpoint, "RIGHT")
    if (
        left_facts["task172_request_hash"]
        != "4fa675e1a36bd49c67957d2ed0a9dbef808529ffef7f2bdc6b51153da421c754"
        or left_facts["task172_result_hash"]
        != "748819390174c8a2fa88f980b5073366817cce9d158c8bf9c56c52dd66e07ee9"
        or right_facts["task172_request_hash"]
        != "b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072"
        or right_facts["task172_result_hash"]
        != "ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573"
        or math.nextafter(float(left_endpoint["q_w_repr"]), math.inf)
        != float(right_endpoint["q_w_repr"])
    ):
        raise RuntimeError("frozen original endpoint identities or adjacency mismatch")
    if left_request.support != right_request.support:
        raise RuntimeError("frozen original endpoint support mismatch")
    if (
        left_request.support.physical_segment_id != TARGET_SUPPORT_ID
        or left_request.support.subdivisions_per_physical_interval_per_side != TARGET_N
        or left_request.support.subdivision_index != 21
        or left_request.support.tube_cell_id != failure["tube_cell_id"]
        or left_request.support.shell_cell_id != failure["shell_cell_id"]
        or left_request.support.wall_interface_id != failure["wall_interface_id"]
    ):
        raise RuntimeError("saved endpoint support/cell/wall binding differs from failure")
    if (
        left_request.topology.task171_result_hash != rating_context.task171_result_hash
        or right_request.topology.task171_result_hash != rating_context.task171_result_hash
        or left_request.topology.mesh_identity != rating_context.mesh_identity
        or right_request.topology.mesh_identity != rating_context.mesh_identity
        or left_request.topology.physical_ownership_hash != rating_context.physical_ownership_hash
        or right_request.topology.physical_ownership_hash != rating_context.physical_ownership_hash
    ):
        raise RuntimeError("saved endpoint topology/Task171 identity differs from Candidate A")

    authority = json.loads(R2A_AUTHORITY_PATH.read_text(encoding="utf-8"))
    authority_candidate = authority["authority_candidate"]
    authority_hash = canonical_sha256(authority_candidate["projection"])
    if authority_hash != authority_candidate["canonical_hash"]:
        raise RuntimeError("reviewed R2A authority receipt hash is internally inconsistent")
    if authority_hash != R2A_AUTHORITY_HASH:
        raise RuntimeError("reviewed R2A authority canonical hash mismatch")

    provider = CoolPropProvider()
    tube_upstream = rating._state_from_enthalpy(
        provider, Decimal(str(failure["tube_upstream_state"]["native"]["enthalpy_j_kg"]))
    )
    shell_physical_left = rating._state_from_enthalpy(
        provider, Decimal(str(failure["shell_physical_left_state"]["native"]["enthalpy_j_kg"]))
    )
    tube_state_capture = r1._capture_state(tube_upstream)
    shell_state_capture = r1._capture_state(shell_physical_left)
    if (
        tube_state_capture != failure["tube_upstream_state"]
        or shell_state_capture != failure["shell_physical_left_state"]
    ):
        raise RuntimeError("R2 upstream physical states failed exact provider rehydration")
    if provider._construction_fingerprint != "8d37dea32044ee8d":
        raise RuntimeError("CoolProp provider configuration fingerprint mismatch")

    # Non-empty real/synthetic Task172 valid and blocked probe projection replay.
    valid_fixture = _fixture_probe(left_request, left_result, left_endpoint)
    blocked_result = task172_service._blocked(
        "BLOCKED_RESIDUAL_ACCEPTANCE",
        "diagnostic.preflight.synthetic_probe",
        rating.recompute_task172_request_hash(left_request),
        ("synthetic preflight blocked projection; no solver call",),
    )
    blocked_fixture = _fixture_probe(left_request, blocked_result, left_endpoint)
    valid_fixture_replay = _probe_projection_replay(valid_fixture)
    blocked_fixture_replay = _probe_projection_replay(blocked_fixture)
    unknown_type_failed_closed = False
    try:
        unknown = dict(valid_fixture)
        unknown["task172_result_type"] = "UnsupportedResult"
        _probe_projection_replay(unknown)
    except TypeError:
        unknown_type_failed_closed = True
    if not unknown_type_failed_closed:
        raise RuntimeError("unknown Task172 probe result type did not fail closed")

    left_q = float(left_endpoint["q_w_repr"])
    right_q = float(right_endpoint["q_w_repr"])
    left_exact_decimal = Decimal.from_float(left_q)
    right_exact_decimal = Decimal.from_float(right_q)
    left_decimal_str = Decimal(str(left_q))
    right_decimal_str = Decimal(str(right_q))
    left_coordinate_exact = _provider_signature(
        left_exact_decimal,
        Decimal(str(tube_state_capture["native"]["enthalpy_j_kg"])),
        Decimal(str(shell_state_capture["native"]["enthalpy_j_kg"])),
    )
    left_coordinate_str = _provider_signature(
        left_decimal_str,
        Decimal(str(tube_state_capture["native"]["enthalpy_j_kg"])),
        Decimal(str(shell_state_capture["native"]["enthalpy_j_kg"])),
    )
    right_coordinate_exact = _provider_signature(
        right_exact_decimal,
        Decimal(str(tube_state_capture["native"]["enthalpy_j_kg"])),
        Decimal(str(shell_state_capture["native"]["enthalpy_j_kg"])),
    )
    right_coordinate_str = _provider_signature(
        right_decimal_str,
        Decimal(str(tube_state_capture["native"]["enthalpy_j_kg"])),
        Decimal(str(shell_state_capture["native"]["enthalpy_j_kg"])),
    )

    with localcontext() as context:
        context.prec = 100
        left_representation_difference = left_exact_decimal - left_decimal_str
        right_representation_difference = right_exact_decimal - right_decimal_str

    checks = {
        "R2_RAW_EXECUTION_CHECKPOINT_TRACE_IDENTITY": "PASS",
        "FROZEN_COMPLETION_REQUEST_IDENTITY": "PASS",
        "R2_144217_VALIDATIONS_27_HOLES_749_TARGET_IDENTITIES": "PASS",
        "JSON_REQUEST_REHYDRATION": "PASS",
        "JSON_VALID_RESULT_REHYDRATION": "PASS",
        "JSON_BLOCKED_RESULT_REHYDRATION": "PASS",
        "REFERENCE_PLANE_PAIR_REPLAY": "PASS",
        "FROZEN_ENDPOINT_IDENTITIES": "PASS",
        "UPSTREAM_STATE_IDENTITY": "PASS",
        "SUPPORT_AND_TOPOLOGY_IDENTITY": "PASS",
        "DECIMAL_PROBE_RESULT_REPLAY_FIXTURE": "PASS",
        "UNKNOWN_TYPE_FAIL_CLOSED": "PASS",
    }
    basis = {
        "candidate_rating_request_projection": candidate_request_projection,
        "candidate_rating_request_hash": RATING_REQUEST_HASH,
        "candidate_rating_request_projection_source": str(CANDIDATE_RECEIPT_PATH.relative_to(ROOT)),
        "candidate_receipt_sha256": candidate_receipt_sha,
        "candidate_space_hash": TASK168_SPACE_HASH,
        "failure": failure,
        "support_projection": _native_projection(left_request.support),
        "tube_upstream_state": tube_state_capture,
        "shell_physical_left_state": shell_state_capture,
        "left_endpoint": left_endpoint,
        "right_endpoint": right_endpoint,
        "endpoint_identity_replay": [left_facts, right_facts],
        "endpoint_identity_replay_count": 2,
        "provider_configuration_fingerprint": provider._construction_fingerprint,
        "provider_identity": {
            "provider": "CoolProp",
            "version": "8.0.0",
            "git_revision": "ae81610e7d23efc57f9d051c8e70a4d66e87537f",
            "backend": "HEOS::Water",
            "reference_state": "DEF",
        },
        "decimal_from_float_vs_decimal_str": {
            "left": {
                "decimal_from_float": str(left_exact_decimal),
                "decimal_str_float": str(left_decimal_str),
                "difference": str(left_representation_difference),
                "from_float_provider_input_signature": left_coordinate_exact[
                    "provider_ph_input_signature"
                ],
                "decimal_str_provider_input_signature": left_coordinate_str[
                    "provider_ph_input_signature"
                ],
                "signature_changed": left_coordinate_exact["provider_ph_input_signature"]
                != left_coordinate_str["provider_ph_input_signature"],
            },
            "right": {
                "decimal_from_float": str(right_exact_decimal),
                "decimal_str_float": str(right_decimal_str),
                "difference": str(right_representation_difference),
                "from_float_provider_input_signature": right_coordinate_exact[
                    "provider_ph_input_signature"
                ],
                "decimal_str_provider_input_signature": right_coordinate_str[
                    "provider_ph_input_signature"
                ],
                "signature_changed": right_coordinate_exact["provider_ph_input_signature"]
                != right_coordinate_str["provider_ph_input_signature"],
            },
        },
        "nonempty_probe_replay_fixtures": {
            "validated": valid_fixture,
            "validated_replay": valid_fixture_replay,
            "blocked": blocked_fixture,
            "blocked_replay": blocked_fixture_replay,
            "unknown_type_fail_closed": unknown_type_failed_closed,
        },
    }
    result = {
        "schema_version": "task173.r2-snapshot-decimal-q-probe-preflight.v1",
        "task_id": TASK_ID,
        "required_start_head": START_HEAD,
        "captured_head": current_head,
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "runtime_binding": runtime_binding,
        "completion_request_hash": COMPLETION_REQUEST_HASH,
        "completion_request_replay_artifact_sha256": completion_request_replay_sha256,
        "candidate_id": CANDIDATE_ID,
        "candidate_hash": CANDIDATE_HASH,
        "candidate_rating_request_hash": RATING_REQUEST_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "r2a_authority_hash": R2A_AUTHORITY_HASH,
        "raw_artifacts": raw_receipts,
        "r2_summary_canonical_hash": committed_summary["canonical_summary_hash"],
        "r2_summary_regenerated_hash": regenerated_summary["canonical_summary_hash"],
        "r2_preflight_raw_sha256": committed_summary["preflight"]["preflight_raw_sha256"],
        "r2_preflight_canonical_hash": committed_summary["preflight"]["preflight_canonical_hash"],
        "r2_task172_validation_count": 144217,
        "r2_task172_numerical_hole_count": 27,
        "r2_target_task172_identity_replay_count": 749,
        "r2_trace_event_count": committed_summary["raw_artifacts"]["trace_event_count"],
        "r2_transient_outer_decision_certificate_hashes": committed_summary["execution"][
            "transient_outer_decision_certificate_hashes"
        ],
        "r2_decimal_probe_count": 0,
        "probe_native_task172_calls_before_execution": 0,
        "checks": checks,
        "rehydration_basis": basis,
        "preflight_result": "PASS" if all(value == "PASS" for value in checks.values()) else "FAIL",
    }
    result["canonical_preflight_hash"] = canonical_sha256(result)
    return result


def _load_preflight(path: Path = PREFLIGHT_PATH) -> dict[str, Any]:
    preflight = json.loads(path.read_text(encoding="utf-8"))
    recorded = preflight.pop("canonical_preflight_hash", None)
    if canonical_sha256(preflight) != recorded:
        raise RuntimeError("R3 preflight canonical hash mismatch")
    preflight["canonical_preflight_hash"] = recorded
    if preflight.get("preflight_result") != "PASS" or any(
        value != "PASS" for value in preflight.get("checks", {}).values()
    ):
        raise RuntimeError("R3 preflight is not all-PASS")
    if preflight.get("captured_head") != START_HEAD:
        raise RuntimeError("R3 preflight was not captured at required starting head")
    if not _raw_receipts_match(preflight["raw_artifacts"]):
        raise RuntimeError("R2 raw source artifacts changed after preflight")
    if _replay_completion_request() != preflight["completion_request_replay_artifact_sha256"]:
        raise RuntimeError("frozen completion request replay artifact changed after preflight")
    return preflight


def _uniform_provider_signature_sweep(
    left_q: Decimal,
    right_q: Decimal,
    tube_h: Decimal,
    shell_h: Decimal,
    intervals: int,
) -> dict[str, Any]:
    signatures: list[dict[str, Any]] = []
    with localcontext() as context:
        context.prec = 100
        width = right_q - left_q
        for index in range(intervals + 1):
            q = left_q + width * Decimal(index) / Decimal(intervals)
            signatures.append(_provider_signature(q, tube_h, shell_h))
    unique = sorted({tuple(item["provider_ph_input_signature"]) for item in signatures})
    transitions = []
    for index, (left, right) in enumerate(zip(signatures, signatures[1:], strict=False), start=1):
        if left["provider_ph_input_signature"] != right["provider_ph_input_signature"]:
            transitions.append(
                {
                    "left_sample_index": index - 1,
                    "right_sample_index": index,
                    "left_q_decimal": left["q_decimal"],
                    "right_q_decimal": right["q_decimal"],
                    "left_signature": list(left["provider_ph_input_signature"]),
                    "right_signature": list(right["provider_ph_input_signature"]),
                }
            )
    return {
        "uniform_intervals": intervals,
        "coordinate_sample_count": len(signatures),
        "unique_provider_ph_input_signature_count": len(unique),
        "signatures": signatures,
        "transitions": transitions,
    }


def _execute_probes(preflight: dict[str, Any]) -> dict[str, Any]:
    if EVIDENCE_PATH.exists() or OUTPUT_DIR.exists():
        raise RuntimeError("R3 execution artifacts already exist; refusing a second probe run")
    r1 = _load_module("r1_decimal_probe_helpers_for_r3_execution", R1_RUNNER_PATH)
    (
        candidate_request,
        context,
        support,
        provider,
        tube_upstream,
        shell_physical_left,
    ) = _load_preflight_basis(preflight)
    basis = preflight["rehydration_basis"]
    left_q = Decimal.from_float(TARGET_LEFT_Q)
    right_q = Decimal.from_float(TARGET_RIGHT_Q)
    if left_q >= right_q:
        raise RuntimeError("frozen target interval is not ordered")
    coordinate_sweep = _uniform_provider_signature_sweep(
        left_q,
        right_q,
        Decimal(str(tube_upstream.native.enthalpy_j_kg)),
        Decimal(str(shell_physical_left.native.enthalpy_j_kg)),
        UNIFORM_INTERVALS,
    )
    store = R3CheckpointStore(OUTPUT_DIR)
    runtime_identity = {
        "head": _git("rev-parse", "HEAD"),
        "tree": _git("rev-parse", "HEAD^{tree}"),
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "runtime_paths_byte_identical": True,
        "production_code_changed": False,
        "r2a_authority_hash": R2A_AUTHORITY_HASH,
    }
    request_identity = {
        "candidate_id": CANDIDATE_ID,
        "candidate_hash": CANDIDATE_HASH,
        "candidate_rating_request_hash": candidate_rating_request_hash(candidate_request),
        "completion_request_hash": COMPLETION_REQUEST_HASH,
        "task168_candidate_space_hash": TASK168_SPACE_HASH,
        "mesh_subdivisions": TARGET_N,
        "support_id": TARGET_SUPPORT_ID,
        "left_original_request_hash": basis["left_endpoint"]["task172_request_hash"],
        "right_original_request_hash": basis["right_endpoint"]["task172_request_hash"],
    }
    capture: dict[str, Any] = {
        "runtime_identity": runtime_identity,
        "request_identity": request_identity,
        "execution_phase": "R3_DECIMAL_Q_PROBE_ONLY",
        "current_mesh_subdivisions": TARGET_N,
        "provider_ph_coordinate_sweep": coordinate_sweep,
        "current_target_cell": {
            "support_id": TARGET_SUPPORT_ID,
            "tube_cell_id": support.tube_cell_id,
            "shell_cell_id": support.shell_cell_id,
            "wall_interface_id": support.wall_interface_id,
            "outer_iteration": basis["failure"]["outer_iteration"],
            "shooting_enthalpy_j_kg": basis["failure"]["shooting_enthalpy_j_kg"],
            "tube_upstream_state": _provider_snapshot(tube_upstream),
            "shell_physical_left_state": _provider_snapshot(shell_physical_left),
        },
        "task172_validator_call_count": 0,
        "endpoint_identity_budget_units": ENDPOINT_IDENTITY_BUDGET_UNITS,
        "decimal_q_probes": [],
        "last_exception": None,
    }
    _strict_persist(
        capture,
        store,
        "R3_PROBE_EXECUTION_STARTED",
        {
            "candidate_id": CANDIDATE_ID,
            "candidate_rating_request_hash": RATING_REQUEST_HASH,
            "target_n": TARGET_N,
            "support_id": TARGET_SUPPORT_ID,
            "provider_ph_coordinate_signature_count": coordinate_sweep[
                "unique_provider_ph_input_signature_count"
            ],
            "coordinate_sweep": coordinate_sweep,
        },
        checkpoint=True,
    )

    original_validator = rating.task172_validate_candidate
    original_persist = r1._persist_event_and_checkpoint
    native_calls = 0
    native_call_seconds: list[float] = []

    def strict_persist(
        active_capture: dict[str, Any],
        active_store: R3CheckpointStore | None,
        *,
        event_type: str,
        payload: dict[str, Any],
        checkpoint: bool,
    ) -> None:
        _strict_persist(
            active_capture,
            active_store,
            event_type,
            payload,
            checkpoint=checkpoint,
        )

    def counted_validator(request: Any, active_provider: Any) -> Any:
        nonlocal native_calls
        budget_used = ENDPOINT_IDENTITY_BUDGET_UNITS + native_calls
        if budget_used >= MAX_NEW_TASK172_VALIDATIONS:
            raise RuntimeError("MAX_NEW_TASK172_VALIDATIONS reached before native call")
        if type(request) is not CandidateTask172LocalRequest:
            raise TypeError("probe attempted a non-candidate-native Task172 request")
        native_calls += 1
        if capture.get("task172_validator_call_count") != native_calls:
            raise RuntimeError("probe capture/native Task172 call counters diverged")
        req_projection = _model_json(request)
        req_hash = rating.recompute_task172_request_hash(request)
        call_started = time.monotonic()
        capture["decimal_q_probe_in_progress"]["native_request_projection"] = req_projection
        capture["decimal_q_probe_in_progress"]["native_request_hash"] = req_hash
        capture["decimal_q_probe_in_progress"]["native_call_ordinal"] = native_calls
        budget_units = ENDPOINT_IDENTITY_BUDGET_UNITS + native_calls
        _strict_persist(
            capture,
            store,
            "TASK172_NATIVE_VALIDATION_STARTED",
            {
                "call_ordinal": native_calls,
                "budget_used_including_two_endpoint_identity_replays": budget_units,
                "request_hash": req_hash,
                "request_projection": req_projection,
                "q_decimal_exact": capture["decimal_q_probe_in_progress"]["q_decimal_exact"],
            },
            checkpoint=True,
        )
        try:
            result = original_validator(request, active_provider)
        except BaseException as exc:
            capture["last_exception"] = {
                "phase": "TASK172_NATIVE_VALIDATION",
                "call_ordinal": native_calls,
                "type": type(exc).__name__,
                "text": str(exc),
            }
            _strict_persist(
                capture,
                store,
                "TASK172_NATIVE_VALIDATION_EXCEPTION",
                capture["last_exception"],
                checkpoint=True,
            )
            raise
        elapsed = time.monotonic() - call_started
        native_call_seconds.append(elapsed)
        identity = r1._task172_result_identity(request, result)
        result_record = {
            "call_ordinal": native_calls,
            "request_hash": req_hash,
            "request_hash_replay": identity["request_hash_replay"],
            "result_type": identity["result_type"],
            "result_status": identity["status"],
            "result_hash": identity["result_hash"],
            "result_hash_replay": identity["result_hash_replay"],
            "result_id": identity.get("result_id"),
            "failure_code": identity.get("failure_code"),
            "field_path": identity.get("field_path"),
            "result_projection": identity["result_projection"],
            "elapsed_seconds": elapsed,
        }
        capture["decimal_q_probe_in_progress"]["native_result_returned"] = result_record
        _strict_persist(
            capture,
            store,
            "TASK172_NATIVE_VALIDATION_RETURNED",
            result_record,
            checkpoint=True,
        )
        return result

    token = rating._CANDIDATE_RATING_CONTEXT.set(context)
    rating.task172_validate_candidate = counted_validator
    r1._persist_event_and_checkpoint = strict_persist
    probe_results: list[dict[str, Any]] = []
    by_q: dict[Decimal, dict[str, Any]] = {}

    def run_one(q: Decimal, *, deterministic_repeat_of: int | None = None) -> dict[str, Any]:
        if q in by_q and deterministic_repeat_of is None:
            return by_q[q]
        if ENDPOINT_IDENTITY_BUDGET_UNITS + native_calls >= MAX_NEW_TASK172_VALIDATIONS:
            raise RuntimeError("native Task172 validation call ceiling would be exceeded")
        record = r1._probe_decimal_q(
            q,
            support=support,
            tube_upstream=tube_upstream,
            shell_physical_left=shell_physical_left,
            provider=provider,
            shell_authority=context.shell_authority,
            context=context,
            ordinal=len(probe_results) + 1,
            store=store,
            capture=capture,
        )
        record["elapsed_native_task172_seconds"] = native_call_seconds[-1]
        record["budget_used_including_endpoint_identity_replays"] = (
            ENDPOINT_IDENTITY_BUDGET_UNITS + native_calls
        )
        record["deterministic_repeat_of_probe_index"] = deterministic_repeat_of
        probe_results.append(record)
        if deterministic_repeat_of is None:
            by_q[q] = record
        return record

    probes_completed = False
    try:
        with localcontext() as context_decimal:
            context_decimal.prec = 100
            width = right_q - left_q
            for index in range(UNIFORM_INTERVALS + 1):
                run_one(left_q + width * Decimal(index) / Decimal(UNIFORM_INTERVALS))

        adaptive_calls = 0
        recovered_probe: dict[str, Any] | None = None
        while adaptive_calls < ADAPTIVE_BISECTION_CAP:
            passing = next(
                (
                    record
                    for record in probe_results
                    if record.get("ordinary_point_root_tolerance_pass") is True
                    and record.get("task172_status") == "VALIDATED"
                ),
                None,
            )
            if passing is not None:
                recovered_probe = passing
                break
            ordered = sorted(by_q.items(), key=lambda item: item[0])
            bracket: tuple[Decimal, Decimal] | None = None
            for (q_left, left_record), (q_right_local, right_record) in zip(
                ordered, ordered[1:], strict=False
            ):
                if (
                    left_record.get("task172_status") == "VALIDATED"
                    and right_record.get("task172_status") == "VALIDATED"
                    and Decimal(left_record["F_decimal_high_precision"])
                    * Decimal(right_record["F_decimal_high_precision"])
                    < 0
                ):
                    bracket = (q_left, q_right_local)
                    break
            if bracket is None:
                break
            with localcontext() as context_decimal:
                context_decimal.prec = 100
                midpoint = (bracket[0] + bracket[1]) / Decimal(2)
            if midpoint in by_q or midpoint in bracket:
                break
            run_one(midpoint)
            adaptive_calls += 1

        if recovered_probe is None:
            recovered_probe = next(
                (
                    record
                    for record in probe_results
                    if record.get("ordinary_point_root_tolerance_pass") is True
                    and record.get("task172_status") == "VALIDATED"
                ),
                None,
            )
        if recovered_probe is not None:
            q_repeat = Decimal(recovered_probe["q_decimal_exact"])
            repeated = run_one(
                q_repeat,
                deterministic_repeat_of=recovered_probe["probe_index"],
            )
            if (
                repeated["task172_request_hash"] != recovered_probe["task172_request_hash"]
                or repeated["task172_result_hash"] != recovered_probe["task172_result_hash"]
                or repeated["task172_result_projection"]
                != recovered_probe["task172_result_projection"]
                or repeated["F_decimal_high_precision"]
                != recovered_probe["F_decimal_high_precision"]
            ):
                raise RuntimeError("deterministic native Task172 root replay identity mismatch")
        probes_completed = True
    except BaseException as exc:
        capture["last_exception"] = {
            "phase": capture.get("execution_phase"),
            "type": type(exc).__name__,
            "text": str(exc),
            "task172_calls_completed": native_calls,
        }
        with contextlib.suppress(Exception):
            _strict_persist(
                capture,
                store,
                "R3_PROBE_EXECUTION_EXCEPTION",
                capture["last_exception"],
                checkpoint=True,
            )
        raise
    finally:
        rating.task172_validate_candidate = original_validator
        r1._persist_event_and_checkpoint = original_persist
        rating._CANDIDATE_RATING_CONTEXT.reset(token)

    validated = [item for item in probe_results if item.get("task172_status") == "VALIDATED"]
    min_abs_f = min(
        (abs(Decimal(item["F_decimal_high_precision"])) for item in validated),
        default=None,
    )
    root_candidates = [
        item for item in validated if item.get("ordinary_point_root_tolerance_pass") is True
    ]
    first_samples = sorted(
        (item for item in probe_results if item["probe_index"] <= UNIFORM_INTERVALS + 1),
        key=lambda item: Decimal(item["q_decimal_exact"]),
    )
    observed_transitions = []
    same_request_result_changes = []
    for _index, (left, right) in enumerate(zip(first_samples, first_samples[1:], strict=False)):
        left_sig = tuple(
            item["provider_enthalpy_float_hex"] for item in left["provider_ph_inputs_outputs"]
        )
        right_sig = tuple(
            item["provider_enthalpy_float_hex"] for item in right["provider_ph_inputs_outputs"]
        )
        if left_sig != right_sig:
            observed_transitions.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "provider_input_signature_changed": True,
                    "left_request_hash": left["task172_request_hash"],
                    "right_request_hash": right["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                    "left_F": left.get("F_decimal_high_precision"),
                    "right_F": right.get("F_decimal_high_precision"),
                }
            )
        if (
            left["task172_request_hash"] == right["task172_request_hash"]
            and left["task172_result_hash"] != right["task172_result_hash"]
        ):
            same_request_result_changes.append(
                {
                    "left_probe_index": left["probe_index"],
                    "right_probe_index": right["probe_index"],
                    "request_hash": left["task172_request_hash"],
                    "left_result_hash": left["task172_result_hash"],
                    "right_result_hash": right["task172_result_hash"],
                }
            )
    all_probe_replays = [_probe_projection_replay(record) for record in probe_results]
    status_counts: dict[str, int] = {}
    for item in probe_results:
        status_counts[item["task172_status"]] = status_counts.get(item["task172_status"], 0) + 1
    store.append_event(
        "R3_PROBE_EXECUTION_FINISHED",
        {
            "native_task172_validation_count": native_calls,
            "budget_units_including_endpoint_identity_replays": ENDPOINT_IDENTITY_BUDGET_UNITS
            + native_calls,
            "decimal_q_probe_count": len(probe_results),
            "point_root_recovered": bool(root_candidates),
            "min_abs_f_w": None if min_abs_f is None else str(min_abs_f),
            "probe_replay_count": len(all_probe_replays),
        },
    )
    capture["execution_phase"] = "R3_PROBE_EXECUTION_FINISHED"
    capture["task172_validator_call_count"] = native_calls
    capture["decimal_q_probes"] = probe_results
    capture["last_exception"] = None
    store.write_checkpoint(
        capture, runtime_identity=runtime_identity, request_identity=request_identity
    )
    trace_hash, trace_bytes = _sha256_file(store.trace_path)
    checkpoint_hash, checkpoint_bytes = _sha256_file(store.checkpoint_path)
    provider_signature_count = coordinate_sweep["unique_provider_ph_input_signature_count"]
    provider_plateau_class = (
        "SINGLE_PH_INPUT_SIGNATURE_ACROSS_BOUNDED_GRID"
        if provider_signature_count == 1
        else "MULTIPLE_PH_INPUT_SIGNATURES_OBSERVED"
    )
    if same_request_result_changes:
        task172_discontinuity = "SAME_REQUEST_DIFFERENT_RESULT_IDENTITY"
    elif observed_transitions:
        task172_discontinuity = "REQUEST_BOUND_RESULT_TRANSITION_OBSERVED"
    else:
        task172_discontinuity = "NO_TASK172_RESULT_DISCONTINUITY_OBSERVED_IN_BOUNDED_PROBES"
    evidence = {
        "schema_version": "task173.r2-snapshot-decimal-q-probe-evidence.v1",
        "task_id": TASK_ID,
        "start_head": START_HEAD,
        "execution_head": _git("rev-parse", "HEAD"),
        "runtime_source_head": RUNTIME_HEAD,
        "runtime_source_tree": RUNTIME_TREE,
        "production_code_changed": False,
        "task172_contract_changed": False,
        "r2a_authority_changed": False,
        "numerical_tolerance_changed": False,
        "candidate_space_changed": False,
        "frozen_completion_request_changed": False,
        "full_n32_reconstruction_executed": False,
        "public_full_rating_reexecuted": False,
        "public_sizing_reexecuted": False,
        "task175_executed": False,
        "preflight_canonical_hash": preflight["canonical_preflight_hash"],
        "preflight": preflight,
        "execution": {
            "execution_phase_complete": probes_completed,
            "task172_validation_count": native_calls,
            "max_new_task172_validations": MAX_NEW_TASK172_VALIDATIONS,
            "budget_endpoint_identity_units": ENDPOINT_IDENTITY_BUDGET_UNITS,
            "budget_units_used": ENDPOINT_IDENTITY_BUDGET_UNITS + native_calls,
            "decimal_q_probe_count": len(probe_results),
            "validated_decimal_q_probe_count": len(validated),
            "blocked_decimal_q_probe_count": status_counts.get("BLOCKED", 0),
            "task172_status_counts": status_counts,
            "uniform_intervals": UNIFORM_INTERVALS,
            "adaptive_bisection_cap": ADAPTIVE_BISECTION_CAP,
            "provider_ph_coordinate_sweep": coordinate_sweep,
            "provider_ph_signature_count": provider_signature_count,
            "provider_plateau_classification": provider_plateau_class,
            "task172_result_discontinuity_classification": task172_discontinuity,
            "observed_provider_or_task172_transitions": observed_transitions,
            "same_request_result_identity_changes": same_request_result_changes,
            "min_abs_f_w": None if min_abs_f is None else str(min_abs_f),
            "point_root_recovered": bool(root_candidates),
            "root_probe_index": None if not root_candidates else root_candidates[0]["probe_index"],
            "deterministic_root_replay": (
                "PASS"
                if root_candidates
                and len(
                    [
                        item
                        for item in probe_results
                        if item.get("deterministic_repeat_of_probe_index")
                        == root_candidates[0]["probe_index"]
                    ]
                )
                == 1
                else "NOT_APPLICABLE_NO_ROOT"
            ),
            "probes": probe_results,
            "probe_identity_replay_count": len(all_probe_replays),
            "raw_execution_checkpoint_trace_receipts": preflight["raw_artifacts"],
            "new_checkpoint": {
                "path": str(store.checkpoint_path.relative_to(ROOT)),
                "raw_bytes": checkpoint_bytes,
                "sha256": checkpoint_hash,
            },
            "new_trace": {
                "path": str(store.trace_path.relative_to(ROOT)),
                "raw_bytes": trace_bytes,
                "sha256": trace_hash,
                "event_count": store.event_count,
            },
        },
        "result": "RECOVERED" if root_candidates else "NOT_FOUND_IN_BOUNDED_PROBES",
    }
    evidence["canonical_evidence_hash"] = canonical_sha256(evidence)
    if EVIDENCE_PATH.exists():
        raise RuntimeError("R3 evidence path already exists; refusing overwrite")
    _write_json_once(EVIDENCE_PATH, evidence)
    return evidence


def _write_json_once(path: Path, payload: dict[str, Any]) -> None:
    if path.exists():
        raise RuntimeError(f"refusing to overwrite evidence: {path}")
    encoded = (json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()
    temp = path.parent / f".{path.name}.{os.getpid()}.{time.monotonic_ns()}.tmp"
    try:
        with temp.open("xb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temp.unlink(missing_ok=True)


def replay_final_evidence() -> None:
    evidence = json.loads(EVIDENCE_PATH.read_text(encoding="utf-8"))
    recorded = evidence.pop("canonical_evidence_hash", None)
    if canonical_sha256(evidence) != recorded:
        raise RuntimeError("R3 evidence canonical hash replay failed")
    evidence["canonical_evidence_hash"] = recorded
    preflight = evidence["preflight"]
    recorded_preflight_hash = preflight.pop("canonical_preflight_hash", None)
    if canonical_sha256(preflight) != recorded_preflight_hash:
        raise RuntimeError("embedded R3 preflight canonical hash replay failed")
    preflight["canonical_preflight_hash"] = recorded_preflight_hash
    if evidence["preflight_canonical_hash"] != recorded_preflight_hash:
        raise RuntimeError("R3 execution is not bound to its preflight")
    if any(value != "PASS" for value in preflight.get("checks", {}).values()):
        raise RuntimeError("embedded R3 preflight contains a non-PASS gate")
    if not _raw_receipts_match(preflight["raw_artifacts"]):
        raise RuntimeError("R2 raw execution/checkpoint/trace identity replay failed")
    regenerated_r2, committed_r2 = _load_r2_basis()
    if (
        committed_r2["canonical_summary_hash"] != preflight["r2_summary_canonical_hash"]
        or regenerated_r2["canonical_summary_hash"] != preflight["r2_summary_regenerated_hash"]
    ):
        raise RuntimeError("R2 raw evidence no longer regenerates the frozen preflight basis")
    if _replay_completion_request() != preflight["completion_request_replay_artifact_sha256"]:
        raise RuntimeError("frozen completion request identity replay failed")
    _load_preflight_basis(preflight)
    if evidence["execution"]["task172_validation_count"] > MAX_NEW_TASK172_VALIDATIONS:
        raise RuntimeError("R3 evidence exceeds the native Task172 call limit")
    if (
        evidence["execution"]["budget_units_used"]
        != evidence["execution"]["task172_validation_count"] + ENDPOINT_IDENTITY_BUDGET_UNITS
        or evidence["execution"]["budget_units_used"] > MAX_NEW_TASK172_VALIDATIONS
    ):
        raise RuntimeError("R3 validation budget accounting mismatch")
    basis = preflight["rehydration_basis"]
    candidate = _candidate_request_from_projection(basis["candidate_rating_request_projection"])
    if candidate_rating_request_hash(candidate) != RATING_REQUEST_HASH:
        raise RuntimeError("candidate Rating request replay failed")
    if canonical_sha256(basis["support_projection"]) != canonical_sha256(
        basis["left_endpoint"]["support_projection"]
    ):
        raise RuntimeError("R3 support projection does not match the saved endpoint")
    endpoint_pairs = []
    for label, endpoint in (
        ("LEFT", basis["left_endpoint"]),
        ("RIGHT", basis["right_endpoint"]),
    ):
        request = CandidateTask172LocalRequest.model_validate(
            _restore_pairs(endpoint["task172_request_projection"]), strict=False
        )
        result = Task172LocalResult.model_validate(
            _restore_pairs(endpoint["task172_result_projection"]), strict=False
        )
        request = CandidateTask172LocalRequest.model_validate(request, strict=True)
        result = Task172LocalResult.model_validate(result, strict=True)
        request_hash = rating.recompute_task172_request_hash(request)
        result_hash = rating.recompute_task172_result_hash(result)
        if (
            request_hash != endpoint["task172_request_hash"]
            or result_hash != endpoint["task172_result_hash"]
            or result.physical_support_id != rating.recompute_task172_support_id(request)
        ):
            raise RuntimeError(f"{label} original endpoint identity replay failed")
        for provider_call in endpoint["provider_ph_calls"]:
            snapshot = provider_call["state_after_provider"]["property_snapshot"]
            if (
                canonical_sha256(snapshot)
                != provider_call["state_after_provider"]["property_snapshot_hash"]
            ):
                raise RuntimeError(f"{label} saved provider snapshot replay failed")
        endpoint_pairs.append((request_hash, result_hash))
    if len(endpoint_pairs) != 2:
        raise RuntimeError("R3 endpoint identity replay count mismatch")
    probes = evidence["execution"]["probes"]
    if len(probes) != evidence["execution"]["decimal_q_probe_count"]:
        raise RuntimeError("R3 probe count does not match stored probe preimages")
    probe_replays = [_probe_projection_replay(record) for record in probes]
    if len(probe_replays) != evidence["execution"]["probe_identity_replay_count"]:
        raise RuntimeError("R3 Task172 request/result replay count mismatch")
    trace_path = ROOT / evidence["execution"]["new_trace"]["path"]
    checkpoint_path = ROOT / evidence["execution"]["new_checkpoint"]["path"]
    for label, path, receipt in (
        ("trace", trace_path, evidence["execution"]["new_trace"]),
        ("checkpoint", checkpoint_path, evidence["execution"]["new_checkpoint"]),
    ):
        digest, length = _sha256_file(path)
        if digest != receipt["sha256"] or length != receipt["raw_bytes"]:
            raise RuntimeError(f"R3 {label} byte identity mismatch")
    trace_count = 0
    with trace_path.open(encoding="utf-8") as stream:
        for trace_count, line in enumerate(stream, start=1):
            event = json.loads(line)
            if event.get("sequence") != trace_count:
                raise RuntimeError(f"R3 trace sequence mismatch at event {trace_count}")
    if trace_count != evidence["execution"]["new_trace"]["event_count"]:
        raise RuntimeError("R3 trace event count mismatch")
    if evidence["execution"]["point_root_recovered"]:
        repeat_ids = [item.get("deterministic_repeat_of_probe_index") for item in probes]
        root_index = evidence["execution"]["root_probe_index"]
        if repeat_ids.count(root_index) != 1:
            raise RuntimeError("recovered root lacks exactly one deterministic replay")
    elif evidence["result"] != "NOT_FOUND_IN_BOUNDED_PROBES":
        raise RuntimeError("no-root result is not bounded-probe disposition")
    print("R3_EVIDENCE_CANONICAL_HASH_REPLAY=PASS")
    print("R2_SNAPSHOT_ENDPOINT_IDENTITY_REPLAY=PASS")
    print("CANDIDATE_RATING_REQUEST_HASH_REPLAY=PASS")
    print(f"DECIMAL_Q_PROBE_COUNT={len(probes)}")
    print(f"TASK172_REQUEST_RESULT_REPLAY_COUNT={len(probe_replays)}")
    print("PROVIDER_SNAPSHOT_HASH_REPLAY=PASS")
    print("R3_CHECKPOINT_TRACE_IDENTITY_REPLAY=PASS")
    print("ALL_R3_PROBE_EVIDENCE_REPLAY_PASS=true")


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-probes", action="store_true")
    mode.add_argument("--replay-only", action="store_true")
    args = parser.parse_args()
    if args.preflight_only:
        preflight = _build_preflight()
        _write_json_once(PREFLIGHT_PATH, preflight)
        for name, result in preflight["checks"].items():
            print(f"{name}={result}")
        print(f"R2_SNAPSHOT_REHYDRATION={preflight['preflight_result']}")
        print(f"PREFLIGHT_PATH={PREFLIGHT_PATH.relative_to(ROOT)}")
        print(f"PREFLIGHT_CANONICAL_HASH={preflight['canonical_preflight_hash']}")
        if preflight["preflight_result"] != "PASS":
            raise SystemExit(2)
        return
    if args.execute_probes:
        preflight = _load_preflight()
        evidence = _execute_probes(preflight)
        print(f"R2_SNAPSHOT_REHYDRATION={preflight['preflight_result']}")
        print(f"NEW_TASK172_VALIDATION_COUNT={evidence['execution']['task172_validation_count']}")
        print(f"DECIMAL_Q_PROBE_COUNT={evidence['execution']['decimal_q_probe_count']}")
        print(
            f"VALIDATED_DECIMAL_Q_PROBE_COUNT={evidence['execution']['validated_decimal_q_probe_count']}"
        )
        print(f"MIN_ABS_F_W={evidence['execution']['min_abs_f_w']}")
        print(f"POINT_ROOT_RECOVERED={str(evidence['execution']['point_root_recovered']).lower()}")
        print(f"PROVIDER_PH_SIGNATURE_COUNT={evidence['execution']['provider_ph_signature_count']}")
        print(
            f"PROVIDER_PLATEAU_CLASSIFICATION={evidence['execution']['provider_plateau_classification']}"
        )
        print(
            "TASK172_RESULT_DISCONTINUITY_CLASSIFICATION="
            f"{evidence['execution']['task172_result_discontinuity_classification']}"
        )
        print(f"R3_EVIDENCE_PATH={EVIDENCE_PATH.relative_to(ROOT)}")
        return
    replay_final_evidence()


if __name__ == "__main__":
    main()
