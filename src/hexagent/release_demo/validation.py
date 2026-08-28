"""Fail-closed validation helpers for the TASK036 release-demo boundary."""

from __future__ import annotations

import math
from collections.abc import Mapping
from decimal import Decimal
from enum import Enum
from typing import Any

from .canonical import (
    CanonicalizationError,
    demo_input_hash,
    raw_boundary_blocked_result_hash,
    result_id,
    success_result_hash,
    typed_blocked_result_hash,
)
from .models import (
    Task036DemoInput,
    Task036RawBoundaryBlockedResult,
)
from .schema import (
    CORRECTED_RUNTIME_STAGE_COUNT,
    DATAFLOW_EDGES,
    DEMO_INPUT_FIELDS,
    IDENTITY_NODES,
    RAW_BOUNDARY_BLOCKED_RESULT_FIELDS,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    SUCCESS_RESULT_FIELDS,
    TASK031_RAW_REQUEST_FIELDS,
    TASK032_MASS_FLOW_AUTHORITY_FIELDS,
    TASK032_PROPERTY_SNAPSHOT_FIELDS,
    TASK034_SHELL_TYPE_AUTHORITY_FIELDS,
    TASK034_WALL_PROPERTY_AUTHORITY_FIELDS,
    TYPED_BLOCKED_RESULT_FIELDS,
)

_RAW_MAX_DEPTH = 8
_RAW_MAX_ITEMS = 64
_RAW_TRUNCATION_TOKEN = "__task036_truncated__"
_RAW_UNSUPPORTED_TOKEN = "__task036_unsupported__"
_RAW_FLOAT_TOKEN = "__task036_float__"


def _blocker(code: str, stage: str, field_path: str | None, message: str) -> dict[str, Any]:
    return {
        "code": code,
        "stage": stage,
        "field_path": field_path,
        "message_key": message,
        "details": [],
    }


def _is_string_list(value: Any, *, require_sorted: bool = False) -> bool:
    if (
        type(value) is not list
        or not value
        or any(type(item) is not str or not item for item in value)
    ):
        return False
    if len(set(value)) != len(value):
        return False
    return not require_sorted or value == sorted(value)


def _closed_mapping(value: Any, fields: tuple[str, ...]) -> bool:
    return type(value) is dict and tuple(value) == fields


def _raw_type_name(value: Any) -> str:
    value_type = type(value)
    return f"{value_type.__module__}.{value_type.__qualname__}"


def _raw_projection_value(
    value: Any,
    *,
    depth: int,
    active: set[int],
) -> Any:
    """Project malformed boundary values without invoking user code."""

    if depth > _RAW_MAX_DEPTH:
        return {_RAW_TRUNCATION_TOKEN: {"type": _raw_type_name(value)}}
    if value is None or type(value) is bool or type(value) is int or type(value) is str:
        return value
    if isinstance(value, Decimal):
        if value.is_finite():
            return str(value)
        return {_RAW_UNSUPPORTED_TOKEN: _raw_type_name(value)}
    if isinstance(value, float):
        return {_RAW_FLOAT_TOKEN: type(value).__name__ if math.isfinite(value) else "non-finite"}
    if isinstance(value, (Enum, bytes, bytearray, memoryview, set, frozenset)):
        projection: dict[str, Any] = {_RAW_UNSUPPORTED_TOKEN: _raw_type_name(value)}
        if isinstance(value, (set, frozenset)):
            projection["count"] = len(value)
        return projection
    if type(value) not in (dict, list, tuple):
        return {_RAW_UNSUPPORTED_TOKEN: _raw_type_name(value)}

    identity = id(value)
    if identity in active:
        return {_RAW_UNSUPPORTED_TOKEN: "cycle"}
    active.add(identity)
    try:
        if type(value) is dict:
            projected: list[list[Any]] = []
            items = list(value.items())[:_RAW_MAX_ITEMS]
            for key, item in items:
                key_projection = (
                    key
                    if type(key) is str
                    else {_RAW_UNSUPPORTED_TOKEN: f"key:{_raw_type_name(key)}"}
                )
                projected.append(
                    [
                        key_projection,
                        _raw_projection_value(item, depth=depth + 1, active=active),
                    ]
                )
            if len(value) > _RAW_MAX_ITEMS:
                projected.append([_RAW_TRUNCATION_TOKEN, {"count": len(value)}])
            return projected
        items = list(value)[:_RAW_MAX_ITEMS]
        projected_sequence = [
            _raw_projection_value(item, depth=depth + 1, active=active) for item in items
        ]
        if len(value) > _RAW_MAX_ITEMS:
            projected_sequence.append({_RAW_TRUNCATION_TOKEN: {"count": len(value)}})
        return projected_sequence
    finally:
        active.remove(identity)


def _raw_projection(raw_request: Any) -> dict[str, Any]:
    return {
        "projection_kind": "TASK036_RAW_DEMO_INPUT",
        "projection": _raw_projection_value(raw_request, depth=0, active=set()),
    }


def validate_demo_input(
    raw_request: Any,
) -> tuple[Task036DemoInput | None, str | None, tuple[dict[str, Any], ...]]:
    """Validate and normalize the nine-field caller-owned input record."""

    if type(raw_request) is not dict:
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID", "S00", "demo_input", "raw_type_invalid"
        )
        return None, None, (blocker,)
    if tuple(raw_request) != DEMO_INPUT_FIELDS:
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID", "S00", "demo_input", "closed_fields_invalid"
        )
        return None, None, (blocker,)

    mapping_fields = (0, 1, 2, 5, 6)
    for index in mapping_fields:
        if type(raw_request[DEMO_INPUT_FIELDS[index]]) is not dict:
            blocker = _blocker(
                "ST036_DEMO_INPUT_SCHEMA_INVALID",
                "S00",
                DEMO_INPUT_FIELDS[index],
                "mapping_required",
            )
            return None, None, (blocker,)
    if tuple(raw_request["TASK031_RAW_REQUEST_RECORD"]) != TASK031_RAW_REQUEST_FIELDS:
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK031_RAW_REQUEST_RECORD",
            "closed_upstream_mapping_required",
        )
        return None, None, (blocker,)
    for field, expected_fields in (
        (
            "TASK032_PROPERTY_SNAPSHOT_RECORD",
            TASK032_PROPERTY_SNAPSHOT_FIELDS,
        ),
        (
            "TASK032_MASS_FLOW_AUTHORITY_RECORD",
            TASK032_MASS_FLOW_AUTHORITY_FIELDS,
        ),
    ):
        if tuple(raw_request[field]) != expected_fields:
            blocker = _blocker(
                "ST036_DEMO_INPUT_SCHEMA_INVALID",
                "S01",
                field,
                "closed_upstream_mapping_required",
            )
            return None, None, (blocker,)
    if (
        tuple(raw_request["TASK034_SHELL_TYPE_AUTHORITY_RECORD"])
        != TASK034_SHELL_TYPE_AUTHORITY_FIELDS
    ):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK034_SHELL_TYPE_AUTHORITY_RECORD",
            "closed_authority_mapping_required",
        )
        return None, None, (blocker,)
    if (
        tuple(raw_request["TASK034_WALL_PROPERTY_AUTHORITY_RECORD"])
        != TASK034_WALL_PROPERTY_AUTHORITY_FIELDS
    ):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK034_WALL_PROPERTY_AUTHORITY_RECORD",
            "closed_authority_mapping_required",
        )
        return None, None, (blocker,)

    if not _is_string_list(raw_request["TASK032_REQUEST_EVIDENCE_REFS"], require_sorted=False):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S00",
            "TASK032_REQUEST_EVIDENCE_REFS",
            "list_required",
        )
        return None, None, (blocker,)
    if not _is_string_list(raw_request["TASK033_REQUEST_EVIDENCE_REFS"], require_sorted=False):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S00",
            "TASK033_REQUEST_EVIDENCE_REFS",
            "list_required",
        )
        return None, None, (blocker,)
    if type(raw_request["TASK034_REQUEST_EVIDENCE_REFS"]) not in (list, tuple):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S00",
            "TASK034_REQUEST_EVIDENCE_REFS",
            "sequence_required",
        )
        return None, None, (blocker,)
    task034_refs = list(raw_request["TASK034_REQUEST_EVIDENCE_REFS"])
    if not task034_refs or any(type(item) is not str or not item for item in task034_refs):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S00",
            "TASK034_REQUEST_EVIDENCE_REFS",
            "string_sequence_required",
        )
        return None, None, (blocker,)
    if not _is_string_list(raw_request["TASK035_EVIDENCE_REFS"], require_sorted=False):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID", "S00", "TASK035_EVIDENCE_REFS", "list_required"
        )
        return None, None, (blocker,)

    normalized = {
        "TASK031_RAW_REQUEST_RECORD": raw_request["TASK031_RAW_REQUEST_RECORD"],
        "TASK032_PROPERTY_SNAPSHOT_RECORD": raw_request["TASK032_PROPERTY_SNAPSHOT_RECORD"],
        "TASK032_MASS_FLOW_AUTHORITY_RECORD": raw_request["TASK032_MASS_FLOW_AUTHORITY_RECORD"],
        "TASK032_REQUEST_EVIDENCE_REFS": tuple(
            sorted(raw_request["TASK032_REQUEST_EVIDENCE_REFS"])
        ),
        "TASK033_REQUEST_EVIDENCE_REFS": tuple(
            sorted(raw_request["TASK033_REQUEST_EVIDENCE_REFS"])
        ),
        "TASK034_SHELL_TYPE_AUTHORITY_RECORD": raw_request["TASK034_SHELL_TYPE_AUTHORITY_RECORD"],
        "TASK034_WALL_PROPERTY_AUTHORITY_RECORD": raw_request[
            "TASK034_WALL_PROPERTY_AUTHORITY_RECORD"
        ],
        "TASK034_REQUEST_EVIDENCE_REFS": tuple(task034_refs),
        "TASK035_EVIDENCE_REFS": tuple(raw_request["TASK035_EVIDENCE_REFS"]),
    }
    if normalized["TASK035_EVIDENCE_REFS"] != ("task035-real-public-chain",):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK035_EVIDENCE_REFS",
            "success_singleton_required",
        )
        return None, None, (blocker,)
    if (
        normalized["TASK031_RAW_REQUEST_RECORD"].get("schema_version")
        != "task031.shell-side-hydraulic-geometry-request.v1"
    ):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK031_RAW_REQUEST_RECORD.schema_version",
            "schema_version_invalid",
        )
        return None, None, (blocker,)
    if (
        normalized["TASK034_SHELL_TYPE_AUTHORITY_RECORD"].get("schema_version")
        != "task034.shell-type-authority.v2"
    ):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK034_SHELL_TYPE_AUTHORITY_RECORD.schema_version",
            "schema_version_invalid",
        )
        return None, None, (blocker,)
    if (
        normalized["TASK034_WALL_PROPERTY_AUTHORITY_RECORD"].get("schema_version")
        != "task034.wall-property.v2"
    ):
        blocker = _blocker(
            "ST036_DEMO_INPUT_SCHEMA_INVALID",
            "S01",
            "TASK034_WALL_PROPERTY_AUTHORITY_RECORD.schema_version",
            "schema_version_invalid",
        )
        return None, None, (blocker,)

    try:
        request_hash = demo_input_hash(normalized)
    except (CanonicalizationError, TypeError, ValueError) as exc:
        blocker = _blocker(
            "ST036_DEMO_INPUT_CANONICALIZATION_FAILED", "S01", "demo_input", str(exc)
        )
        return None, None, (blocker,)
    parsed = Task036DemoInput(**normalized)
    return parsed, request_hash, ()


def build_raw_boundary_blocked(
    raw_request: Any, blockers: tuple[dict[str, Any], ...]
) -> Task036RawBoundaryBlockedResult:
    payload: dict[str, Any] = {
        "schema_version": RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
        "profile_id": "hxforge.release_demo.task020_to_task035.v0_3",
        "implementation_software_version": "task036-release-demo-impl-v1",
        "raw_request_projection": _raw_projection(raw_request),
        "blocked_result_hash": "",
        "blockers": list(blockers),
        "warnings": (),
        "deferred_capabilities": (),
    }
    payload["blocked_result_hash"] = raw_boundary_blocked_result_hash(payload)
    return Task036RawBoundaryBlockedResult(
        schema_version=payload["schema_version"],
        profile_id=payload["profile_id"],
        implementation_software_version=payload["implementation_software_version"],
        raw_request_projection=payload["raw_request_projection"],
        blocked_result_hash=payload["blocked_result_hash"],
        blockers=tuple(payload["blockers"]),
        warnings=(),
        deferred_capabilities=(),
    )


def exact_result_fields(record: Mapping[str, Any], fields: tuple[str, ...]) -> bool:
    return tuple(record) == fields and all(type(key) is str for key in record)


def verify_success_identity(record: Mapping[str, Any]) -> bool:
    if not exact_result_fields(record, SUCCESS_RESULT_FIELDS):
        return False
    expected_hash = success_result_hash(record)
    expected_id = result_id(expected_hash)
    return record.get("result_hash") == expected_hash and record.get("result_id") == expected_id


def verify_typed_blocked_identity(record: Mapping[str, Any]) -> bool:
    if not exact_result_fields(record, TYPED_BLOCKED_RESULT_FIELDS):
        return False
    expected_hash = typed_blocked_result_hash(record)
    expected_id = result_id(expected_hash, "TASK036_TYPED_BLOCKED_RESULT")
    return (
        record.get("blocked_result_hash") == expected_hash
        and record.get("result_id") == expected_id
    )


def verify_raw_boundary_identity(record: Mapping[str, Any]) -> bool:
    if not exact_result_fields(record, RAW_BOUNDARY_BLOCKED_RESULT_FIELDS):
        return False
    return record.get("blocked_result_hash") == raw_boundary_blocked_result_hash(record)


def verify_stage_contract() -> dict[str, int | bool]:
    node_order = {node: index for index, node in enumerate(IDENTITY_NODES)}
    backward = sum(1 for left, right in DATAFLOW_EDGES if node_order[left] >= node_order[right])
    undefined = sum(
        1 for left, right in DATAFLOW_EDGES if left not in node_order or right not in node_order
    )
    return {
        "stage_count": CORRECTED_RUNTIME_STAGE_COUNT,
        "edge_count": len(DATAFLOW_EDGES),
        "backward_edge_count": backward,
        "undefined_edge_count": undefined,
        "executable": backward == 0 and undefined == 0,
    }


def producer_status(result: Any) -> str:
    status = getattr(result, "status", None)
    return str(getattr(status, "value", status))


def public_payload(value: Any) -> Any:
    """Convert upstream dataclasses to their public ordered mapping."""

    import dataclasses
    from decimal import Decimal
    from enum import Enum

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: public_payload(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): public_payload(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [public_payload(item) for item in value]
    return value


__all__ = [
    "build_raw_boundary_blocked",
    "exact_result_fields",
    "producer_status",
    "public_payload",
    "validate_demo_input",
    "verify_raw_boundary_identity",
    "verify_stage_contract",
    "verify_success_identity",
    "verify_typed_blocked_identity",
]
