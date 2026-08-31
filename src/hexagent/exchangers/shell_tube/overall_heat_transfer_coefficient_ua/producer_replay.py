"""Public-producer identity replay for TASK-038."""

from __future__ import annotations

import uuid
from typing import Any

from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition import (
    canonical as task035_canonical,
)
from hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.models import (
    Task035RawBoundaryBlockedResult,
    Task035SuccessResult,
    Task035TypedBlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side import (
    Task025BlockedResult,
    Task025ValidResult,
)
from hexagent.exchangers.shell_tube.tube_side import (
    result_hash as task025_result_hash,
)
from hexagent.exchangers.shell_tube.tube_side import (
    result_id as task025_result_id,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    RESULT_ID_NAME_PREFIX as TASK026_RESULT_ID_NAME_PREFIX,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    RESULT_ID_NAMESPACE as TASK026_RESULT_ID_NAMESPACE,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import canonical as task026_canonical
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    SUCCESS_RESULT_HASH_FIELDS as TASK026_SUCCESS_RESULT_HASH_FIELDS,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    SUCCESS_RESULT_HASH_KIND_TAGS as TASK026_SUCCESS_RESULT_HASH_KIND_TAGS,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    SUCCESS_RESULT_HASH_NAMESPACE as TASK026_SUCCESS_RESULT_HASH_NAMESPACE,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    RawBoundaryBlockedResult as Task026RawBoundaryBlockedResult,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.result import (
    TubeSideBlockedResult,
    TubeSideThermalResult,
)

from .models import ProducerIdentityEnvelope


def _hash(value: Any) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _uuid_text(value: Any) -> bool:
    return type(value) is str and len(value) == 36


def _task026_result_id(result_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.UUID(TASK026_RESULT_ID_NAMESPACE),
            TASK026_RESULT_ID_NAME_PREFIX + result_hash,
        )
    )


def _task026_tuple_strings(values: Any) -> bytes:
    return task026_canonical.frame_tuple([item.encode("utf-8") for item in values])


def _task026_blocker_bytes(value: Any) -> bytes:
    return task026_canonical.frame_record(
        "task026.blocker-entry.v1",
        (
            ("code", task026_canonical.KIND_STRING, value.code.encode("utf-8")),
            ("severity", task026_canonical.KIND_STRING, value.severity.encode("utf-8")),
            ("stage", task026_canonical.KIND_STRING, value.stage.encode("utf-8")),
            ("payload", task026_canonical.KIND_TUPLE, _task026_tuple_strings(value.payload)),
            (
                "message_template",
                task026_canonical.KIND_STRING,
                value.message_template.encode("utf-8"),
            ),
        ),
    )


def task026_raw_replay_hash(value: Task026RawBoundaryBlockedResult) -> str:
    """Replay TASK026's six-field producer-specific raw contract exactly."""

    raw_projection = bytes.fromhex(value.raw_request_projection.canonical_bytes_hex)
    blockers = task026_canonical.frame_tuple(
        [_task026_blocker_bytes(item) for item in value.blockers]
    )
    warnings = _task026_tuple_strings(value.warnings)
    deferred = _task026_tuple_strings(value.deferred_capabilities)
    fields = (
        ("raw_request_projection", task026_canonical.KIND_RAW_PROJECTION, raw_projection),
        ("blockers", task026_canonical.KIND_TUPLE, blockers),
        ("warnings", task026_canonical.KIND_TUPLE, warnings),
        ("deferred_capabilities", task026_canonical.KIND_TUPLE, deferred),
        ("schema_version", task026_canonical.KIND_STRING, value.schema_version.encode("utf-8")),
        (
            "implementation_software_version",
            task026_canonical.KIND_STRING,
            value.implementation_software_version.encode("utf-8"),
        ),
    )
    return task026_canonical.sha256_hex_from_framed_bytes(
        task026_canonical.frame_record("task026.raw-boundary-blocked-result.v1", fields)
    )


def _task026_provenance_bytes(value: Any) -> bytes:
    p = value
    return task026_canonical.frame_record(
        "task026.provenance.v1",
        (
            ("task_id", task026_canonical.KIND_STRING, p.task_id.encode("utf-8")),
            (
                "design_contract_path",
                task026_canonical.KIND_STRING,
                p.design_contract_path.encode("utf-8"),
            ),
            (
                "implementation_software_version",
                task026_canonical.KIND_STRING,
                p.implementation_software_version.encode("utf-8"),
            ),
            (
                "input_evidence_refs",
                task026_canonical.KIND_TUPLE,
                _task026_tuple_strings(p.input_evidence_refs),
            ),
            (
                "upstream_identity_hashes",
                task026_canonical.KIND_TUPLE,
                _task026_tuple_strings(p.upstream_identity_hashes),
            ),
        ),
    )


def _task026_success_hash(value: TubeSideThermalResult) -> str:
    decimal_fields = {
        "mass_flow_rate_kg_s",
        "bulk_velocity_m_s",
        "reynolds_number",
        "prandtl_number",
        "nusselt_number",
        "tube_side_heat_transfer_coefficient_w_m2_k",
    }
    enum_fields = {"thermal_boundary_condition", "phase_assertion", "flow_regime"}
    tuple_fields = {"warnings", "blockers", "deferred_capabilities"}
    fields = []
    for name, kind in zip(
        TASK026_SUCCESS_RESULT_HASH_FIELDS,
        TASK026_SUCCESS_RESULT_HASH_KIND_TAGS,
        strict=True,
    ):
        item = getattr(value, name)
        if name == "provenance":
            payload = _task026_provenance_bytes(item)
        elif name == "blockers":
            payload = task026_canonical.frame_tuple(
                [_task026_blocker_bytes(entry) for entry in item]
            )
        elif name in tuple_fields:
            payload = _task026_tuple_strings(item)
        elif name in decimal_fields:
            payload = str(item).encode("ascii")
        elif name in enum_fields:
            payload = item.value.encode("ascii")
        else:
            payload = item.encode("utf-8") if type(item) is str else str(item).encode("ascii")
        fields.append((name, kind, payload))
    return task026_canonical.composite_hash(TASK026_SUCCESS_RESULT_HASH_NAMESPACE, fields)


def replay_task025(result: Any) -> tuple[bool, str, str | None, str | None, str]:
    if type(result) is Task025BlockedResult:
        if not _hash(result.blocked_result_hash):
            return False, "TYPED_BLOCKED", None, None, "task025_blocked_hash_invalid"
        return True, "TYPED_BLOCKED", None, result.blocked_result_hash, result.blocked_result_hash
    if type(result) is not Task025ValidResult:
        return False, "TYPED_BLOCKED", None, None, "task025_type_invalid"
    try:
        digest = task025_result_hash(result)
        identity = task025_result_id(result.result_hash)
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return False, "TYPED_BLOCKED", None, None, "task025_identity_invalid"
    if digest != result.result_hash or identity != result.result_id:
        return False, "TYPED_BLOCKED", None, None, "task025_identity_mismatch"
    return True, "SUCCESS", result.result_id, result.result_hash, result.result_hash


def replay_task026(result: Any) -> tuple[bool, str, str | None, str | None, str]:
    if type(result) is Task026RawBoundaryBlockedResult:
        try:
            digest = task026_raw_replay_hash(result)
        except (AttributeError, TypeError, ValueError):
            return False, "RAW_BOUNDARY_BLOCKED", None, None, "task026_raw_replay_invalid"
        return True, "RAW_BOUNDARY_BLOCKED", None, None, digest
    if type(result) is TubeSideBlockedResult:
        if not _hash(result.result_hash) or not _uuid_text(result.result_id):
            return False, "TYPED_BLOCKED", None, None, "task026_blocked_identity_invalid"
        try:
            if _task026_result_id(result.result_hash) != result.result_id:
                return False, "TYPED_BLOCKED", None, None, "task026_blocked_identity_mismatch"
        except (TypeError, ValueError, ArithmeticError):
            return False, "TYPED_BLOCKED", None, None, "task026_blocked_identity_invalid"
        return True, "TYPED_BLOCKED", result.result_id, result.result_hash, result.result_hash
    if type(result) is not TubeSideThermalResult:
        return False, "TYPED_BLOCKED", None, None, "task026_type_invalid"
    try:
        digest = _task026_success_hash(result)
    except (AttributeError, TypeError, ValueError, ArithmeticError):
        return False, "TYPED_BLOCKED", None, None, "task026_identity_invalid"
    try:
        result_id_matches = _task026_result_id(result.result_hash) == result.result_id
    except (TypeError, ValueError, ArithmeticError):
        result_id_matches = False
    if digest != result.result_hash or not result_id_matches:
        return False, "TYPED_BLOCKED", None, None, "task026_identity_mismatch"
    return True, "SUCCESS", result.result_id, result.result_hash, result.result_hash


def replay_task035(result: Any) -> tuple[bool, str, str | None, str | None, str]:
    if type(result) is Task035SuccessResult:
        try:
            digest = task035_canonical.success_result_hash(result)
            identity = task035_canonical.result_id(result.result_hash)
        except (AttributeError, TypeError, ValueError):
            return False, "TYPED_BLOCKED", None, None, "task035_identity_invalid"
        if digest != result.result_hash or identity != result.result_id:
            return False, "TYPED_BLOCKED", None, None, "task035_identity_mismatch"
        return True, "SUCCESS", result.result_id, result.result_hash, result.result_hash
    if type(result) is Task035TypedBlockedResult:
        if not _hash(result.blocked_result_hash):
            return False, "TYPED_BLOCKED", None, None, "task035_blocked_hash_invalid"
        return (
            True,
            "TYPED_BLOCKED",
            result.result_id,
            result.blocked_result_hash,
            result.blocked_result_hash,
        )
    if type(result) is Task035RawBoundaryBlockedResult:
        if not _hash(result.blocked_result_hash):
            return False, "RAW_BOUNDARY_BLOCKED", None, None, "task035_raw_hash_invalid"
        return (
            True,
            "RAW_BOUNDARY_BLOCKED",
            None,
            result.blocked_result_hash,
            result.blocked_result_hash,
        )
    return False, "TYPED_BLOCKED", None, None, "task035_type_invalid"


def replay_task037(result: Any) -> tuple[bool, str, str | None, str | None, str]:
    from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.models import (
        Task037RawBoundaryBlockedResult,
        Task037SuccessResult,
        Task037TypedBlockedResult,
    )
    from hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validation import (
        verify_task037_success_identity,
    )

    if type(result) is Task037SuccessResult:
        try:
            verified = verify_task037_success_identity(result)
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            verified = False
        if not verified:
            return False, "TYPED_BLOCKED", None, None, "task037_identity_mismatch"
        return True, "SUCCESS", result.result_id, result.result_hash, result.result_hash
    if type(result) is Task037TypedBlockedResult:
        if not _hash(result.blocked_result_hash):
            return False, "TYPED_BLOCKED", None, None, "task037_blocked_hash_invalid"
        return True, "TYPED_BLOCKED", None, result.blocked_result_hash, result.blocked_result_hash
    if type(result) is Task037RawBoundaryBlockedResult:
        if not _hash(result.blocked_result_hash):
            return False, "RAW_BOUNDARY_BLOCKED", None, None, "task037_raw_hash_invalid"
        return (
            True,
            "RAW_BOUNDARY_BLOCKED",
            None,
            result.blocked_result_hash,
            result.blocked_result_hash,
        )
    return False, "TYPED_BLOCKED", None, None, "task037_type_invalid"


def producer_identity_envelope(result: Any) -> ProducerIdentityEnvelope:
    producers = (
        ("TASK025", replay_task025),
        ("TASK026", replay_task026),
        ("TASK035", replay_task035),
        ("TASK037", replay_task037),
    )
    for producer, replay in producers:
        try:
            ok, branch, native_id, native_hash, evidence_hash = replay(result)
        except (AttributeError, TypeError, ValueError, ArithmeticError):
            continue
        if ok:
            return ProducerIdentityEnvelope(producer, branch, native_id, native_hash, evidence_hash)
    raise ValueError(f"unsupported or invalid producer result: {type(result).__name__}")


def replay_result(result: Any) -> tuple[bool, ProducerIdentityEnvelope | None, str]:
    try:
        envelope = producer_identity_envelope(result)
    except ValueError as exc:
        return False, None, str(exc)
    return True, envelope, "PASS"


__all__ = [
    "producer_identity_envelope",
    "replay_result",
    "replay_task025",
    "replay_task026",
    "replay_task035",
    "replay_task037",
    "task026_raw_replay_hash",
]
