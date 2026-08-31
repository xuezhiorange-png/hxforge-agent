"""Canonical byte contracts for TASK-038.

All TASK-038 identities use the fixed-width frame/record codec from the R4
Design.  This module intentionally accepts only explicitly typed projections;
ordinary mapping order never contributes to an identity.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import Enum
from typing import Any, Final

from .models import ProducerIdentityEnvelope
from .raw_projection import FrozenRawProjection
from .schema import (
    APPLICABILITY_LEDGER_ROW_NAMESPACE,
    BLOCKER_ENTRY_NAMESPACE,
    COMPLETENESS_LEDGER_ROW_NAMESPACE,
    CROSS_PRODUCER_COMPATIBILITY_FIELDS,
    CROSS_PRODUCER_COMPATIBILITY_NAMESPACE,
    ENGINEERING_SOURCE_IDENTITY_FIELDS,
    ENGINEERING_SOURCE_IDENTITY_NAMESPACE,
    OUTER_AREA_PROJECTION_AUTHORITY_NAMESPACE,
    OUTER_AREA_PROJECTION_FIELDS,
    PRODUCER_ENVELOPE_IDENTITY_NAMESPACE,
    PROVENANCE_FIELDS,
    PROVENANCE_NAMESPACE,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
    RAW_PROJECTION_NAMESPACE,
    REQUEST_HASH_NAMESPACE,
    RESISTANCE_COMPOSITION_AUTHORITY_NAMESPACE,
    RESISTANCE_COMPOSITION_FIELDS,
    SERVICE_BINDING_NAMESPACE,
    SERVICE_BINDING_PREHASH_FIELDS,
    SUCCESS_RESULT_NAMESPACE,
    SUCCESS_RESULT_PREHASH_FIELDS,
    THERMAL_RESISTANCE_LEDGER_ROW_FIELDS,
    THERMAL_RESISTANCE_LEDGER_ROW_NAMESPACE,
    TYPED_BLOCKED_RESULT_HASH_NAMESPACE,
    TYPED_BLOCKED_RESULT_PREHASH_FIELDS,
    UA_COMPOSITION_AUTHORITY_NAMESPACE,
    UA_COMPOSITION_FIELDS,
    UUID_NAME_PREFIX,
    UUID_NAMESPACE,
    WARNING_ENTRY_NAMESPACE,
)

KIND_NONE: Final[bytes] = b"NONE"
KIND_BOOL_TRUE: Final[bytes] = b"BOOL_TRUE"
KIND_BOOL_FALSE: Final[bytes] = b"BOOL_FALSE"
KIND_INT: Final[bytes] = b"INT"
KIND_STRING: Final[bytes] = b"STRING"
KIND_BYTES: Final[bytes] = b"BYTES"
KIND_DECIMAL: Final[bytes] = b"DECIMAL"
KIND_ENUM: Final[bytes] = b"ENUM"
KIND_TUPLE: Final[bytes] = b"TUPLE"
KIND_RECORD: Final[bytes] = b"RECORD"
KIND_RAW_PROJECTION: Final[bytes] = b"RAW_PROJECTION"

HASH_ALGORITHM: Final[str] = "SHA-256"
RESULT_ID_NAMESPACE: Final[uuid.UUID] = uuid.UUID(UUID_NAMESPACE)


class CanonicalizationError(ValueError):
    """Raised when a value is outside the frozen canonical domain."""


def _u32(value: int) -> bytes:
    if type(value) is not int or value < 0 or value > 0xFFFFFFFF:
        raise CanonicalizationError("u32 value out of range")
    return value.to_bytes(4, "big")


def _u64(value: int) -> bytes:
    if type(value) is not int or value < 0 or value > 0xFFFFFFFFFFFFFFFF:
        raise CanonicalizationError("u64 value out of range")
    return value.to_bytes(8, "big")


def frame_value(kind: bytes | str, payload: bytes) -> bytes:
    if type(kind) is str:
        try:
            kind_bytes = kind.encode("ascii")
        except UnicodeEncodeError as exc:
            raise CanonicalizationError("kind must be ASCII") from exc
    elif type(kind) is bytes:
        kind_bytes = kind
    else:
        raise CanonicalizationError("kind must be bytes or str")
    if type(payload) is not bytes:
        raise CanonicalizationError("frame payload must be bytes")
    return _u32(len(kind_bytes)) + kind_bytes + _u64(len(payload)) + payload


def frame_tuple(items: Sequence[tuple[bytes | str, bytes]]) -> bytes:
    """Encode a native TASK038 typed tuple payload."""

    if type(items) not in {tuple, list}:
        raise CanonicalizationError("tuple items must be tuple/list")
    return _u32(len(items)) + b"".join(frame_value(kind, payload) for kind, payload in items)


def frame_string_tuple(items: Sequence[str]) -> bytes:
    if type(items) not in {tuple, list}:
        raise CanonicalizationError("string tuple must be tuple/list")
    return frame_tuple(tuple((KIND_STRING, _string(item)) for item in items))


def frame_record(namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    if type(namespace) is not str:
        raise CanonicalizationError("namespace must be str")
    namespace_bytes = namespace.encode("utf-8")
    encoded = bytearray(_u32(len(namespace_bytes)))
    encoded.extend(namespace_bytes)
    encoded.extend(_u32(len(fields)))
    for name, kind, payload in fields:
        if type(name) is not str:
            raise CanonicalizationError("field name must be str")
        name_bytes = name.encode("utf-8")
        encoded.extend(_u32(len(name_bytes)))
        encoded.extend(name_bytes)
        encoded.extend(frame_value(kind, payload))
    return bytes(encoded)


def sha256_hex(value: bytes) -> str:
    if type(value) is not bytes:
        raise TypeError("sha256_hex expects bytes")
    return hashlib.sha256(value).hexdigest()


def _value(source: Any, field: str) -> Any:
    if isinstance(source, Mapping):
        return source[field]
    return getattr(source, field)


def _optional_value(source: Any, field: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field, default)
    return getattr(source, field, default)


def _string(value: Any) -> bytes:
    if type(value) is not str:
        raise CanonicalizationError("STRING requires exact str")
    return value.encode("utf-8")


def _enum(value: Any) -> bytes:
    token = value.value if isinstance(value, Enum) else value
    return _string(token)


def _int(value: Any) -> bytes:
    if type(value) is not int:
        raise CanonicalizationError("INT requires exact int")
    return str(value).encode("ascii")


def _decimal(value: Any) -> bytes:
    if type(value) is not Decimal or not value.is_finite():
        raise CanonicalizationError("DECIMAL requires finite Decimal")
    return str(value).encode("ascii")


def _bool(value: Any) -> tuple[bytes, bytes]:
    if type(value) is not bool:
        raise CanonicalizationError("BOOL requires exact bool")
    return (KIND_BOOL_TRUE if value else KIND_BOOL_FALSE, b"")


def _none_or_string(value: Any) -> tuple[bytes, bytes]:
    return (KIND_NONE, b"") if value is None else (KIND_STRING, _string(value))


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def _record_tuple(records: Sequence[bytes]) -> bytes:
    if type(records) not in {tuple, list}:
        raise CanonicalizationError("record tuple must be tuple/list")
    return frame_tuple(tuple((KIND_RECORD, record) for record in records))


def _string_tuple(items: Sequence[str]) -> bytes:
    return frame_string_tuple(items)


def _record_field(name: str, record: bytes) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_RECORD, record)


def _tuple_field(name: str, items: Sequence[str]) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_TUPLE, _string_tuple(items))


def producer_envelope_bytes(source: Any) -> bytes:
    fields = (
        _field("producer_task_id", KIND_STRING, _string(_value(source, "producer_task_id"))),
        _field("branch", KIND_ENUM, _enum(_value(source, "branch"))),
        _field("native_result_id", *_none_or_string(_value(source, "native_result_id"))),
        _field("native_result_hash", *_none_or_string(_value(source, "native_result_hash"))),
        _field(
            "producer_evidence_hash", KIND_STRING, _string(_value(source, "producer_evidence_hash"))
        ),
    )
    return frame_record(PRODUCER_ENVELOPE_IDENTITY_NAMESPACE, fields)


def producer_envelope_hash(source: Any) -> str:
    return sha256_hex(producer_envelope_bytes(source))


def service_binding_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    enum_fields = {"source_class", "permission_status", "approval_status"}
    for field in SERVICE_BINDING_PREHASH_FIELDS:
        value = _value(source, field)
        if field == "evidence_refs":
            fields.append(_tuple_field(field, value))
        elif field in enum_fields:
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        else:
            fields.append(_field(field, KIND_STRING, _string(value)))
    return frame_record(SERVICE_BINDING_NAMESPACE, fields)


def service_binding_hash(source: Any) -> str:
    return sha256_hex(service_binding_bytes(source))


def engineering_source_identity_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field in ENGINEERING_SOURCE_IDENTITY_FIELDS:
        value = _value(source, field)
        if field == "source_locations":
            fields.append(_tuple_field(field, value))
        elif field in {"source_class", "permission_status"}:
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        else:
            fields.append(_field(field, KIND_STRING, _string(value)))
    return frame_record(ENGINEERING_SOURCE_IDENTITY_NAMESPACE, fields)


def engineering_source_identity_hash(source: Any) -> str:
    return sha256_hex(engineering_source_identity_bytes(source))


def request_identity_bytes(source: Any) -> bytes:
    return producer_envelope_bytes(source)


def _producer_identity_for_request(result: Any) -> ProducerIdentityEnvelope:
    if type(result) is ProducerIdentityEnvelope:
        return result
    from .producer_replay import producer_identity_envelope

    return producer_identity_envelope(result)


def request_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = [
        _field("schema_version", KIND_STRING, _string(_value(source, "schema_version"))),
        _field("profile_id", KIND_STRING, _string(_value(source, "profile_id"))),
    ]
    for request_field, identity_field in (
        ("task025_result", "task025_result_identity"),
        ("task026_result", "task026_result_identity"),
        ("task035_result", "task035_result_identity"),
        ("task037_result", "task037_result_identity"),
    ):
        fields.append(
            _record_field(
                identity_field,
                request_identity_bytes(
                    _producer_identity_for_request(_value(source, request_field))
                ),
            )
        )
    binding = _value(source, "tube_side_service_binding_authority")
    binding_hash = _value(binding, "authority_hash")
    fields.append(
        _field("tube_side_service_binding_authority_hash", KIND_STRING, _string(binding_hash))
    )
    fields.append(_tuple_field("evidence_refs", _value(source, "evidence_refs")))
    return frame_record(REQUEST_HASH_NAMESPACE, fields)


def request_hash(source: Any) -> str:
    return sha256_hex(request_bytes(source))


def _cross_kind(field: str, value: Any) -> tuple[bytes, bytes]:
    if field.endswith("surface"):
        return KIND_ENUM, _enum(value)
    return KIND_STRING, _string(value)


def cross_producer_compatibility_bytes(source: Any) -> bytes:
    fields = []
    for field in CROSS_PRODUCER_COMPATIBILITY_FIELDS:
        kind, payload = _cross_kind(field, _value(source, field))
        fields.append(_field(field, kind, payload))
    return frame_record(CROSS_PRODUCER_COMPATIBILITY_NAMESPACE, fields)


def cross_producer_compatibility_hash(source: Any) -> str:
    return sha256_hex(cross_producer_compatibility_bytes(source))


def resistance_composition_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field in RESISTANCE_COMPOSITION_FIELDS:
        value = _value(source, field)
        if field == "engineering_source_identity_hashes":
            fields.append(_tuple_field(field, value))
        elif field in {"overall_u_reference_surface", "rounding_mode"}:
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        else:
            fields.append(
                _field(
                    field,
                    KIND_DECIMAL,
                    _decimal(value)
                    if field not in {"cross_producer_compatibility_hash"}
                    else _string(value),
                )
            )
            if field == "cross_producer_compatibility_hash":
                fields[-1] = _field(field, KIND_STRING, _string(value))
    return frame_record(RESISTANCE_COMPOSITION_AUTHORITY_NAMESPACE, fields)


def resistance_composition_hash(source: Any) -> str:
    return sha256_hex(resistance_composition_bytes(source))


def outer_area_projection_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    decimal_fields = {
        "task025_internal_heat_transfer_surface_area_m2",
        "outer_to_inner_area_ratio",
        "task025_area_quantum_m2",
        "outer_area_quantum_m2",
    }
    enum_fields = {"task025_area_rounding_mode", "rounding_mode"}
    bool_fields = {
        "producer_precision_limitation_disclosed",
        "producer_precision_threshold_defined",
    }
    for field in OUTER_AREA_PROJECTION_FIELDS:
        value = _value(source, field)
        if field in decimal_fields:
            fields.append(_field(field, KIND_DECIMAL, _decimal(value)))
        elif field in enum_fields:
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        elif field in bool_fields:
            fields.append(_field(field, *_bool(value)))
        else:
            fields.append(_field(field, KIND_STRING, _string(value)))
    return frame_record(OUTER_AREA_PROJECTION_AUTHORITY_NAMESPACE, fields)


def outer_area_projection_hash(source: Any) -> str:
    return sha256_hex(outer_area_projection_bytes(source))


def ua_composition_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    decimal_fields = {
        "modeled_overall_heat_transfer_coefficient_w_m2_k",
        "outer_tube_surface_effective_area_m2",
        "ua_quantum_w_k",
    }
    for field in UA_COMPOSITION_FIELDS:
        value = _value(source, field)
        if field in decimal_fields:
            fields.append(_field(field, KIND_DECIMAL, _decimal(value)))
        elif field == "rounding_mode":
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        else:
            fields.append(_field(field, KIND_STRING, _string(value)))
    return frame_record(UA_COMPOSITION_AUTHORITY_NAMESPACE, fields)


def ua_composition_hash(source: Any) -> str:
    return sha256_hex(ua_composition_bytes(source))


def thermal_resistance_ledger_row_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field in THERMAL_RESISTANCE_LEDGER_ROW_FIELDS:
        value = _value(source, field)
        if field == "transformation_authority_hash_or_none":
            fields.append(_field(field, *_none_or_string(value)))
        elif field == "source_field_or_projection":
            fields.append(_field(field, KIND_STRING, _string(value)))
        elif field == "value_m2_k_w":
            fields.append(_field(field, KIND_DECIMAL, _decimal(value)))
        else:
            fields.append(_field(field, KIND_ENUM, _enum(value)))
    return frame_record(THERMAL_RESISTANCE_LEDGER_ROW_NAMESPACE, fields)


def thermal_resistance_ledger_row_hash(source: Any) -> str:
    return sha256_hex(thermal_resistance_ledger_row_bytes(source))


def ledger_row_bytes(source: Any, *, completeness: bool = False) -> bytes:
    namespace = (
        COMPLETENESS_LEDGER_ROW_NAMESPACE if completeness else APPLICABILITY_LEDGER_ROW_NAMESPACE
    )
    return frame_record(
        namespace,
        (
            _field("row_id", KIND_ENUM, _enum(_value(source, "row_id"))),
            _field("status", KIND_ENUM, _enum(_value(source, "status"))),
        ),
    )


def blocker_detail_bytes(key: str, value: str) -> bytes:
    return frame_record(
        "task038.blocker-detail.v1",
        (
            _field("key", KIND_STRING, _string(key)),
            _field("value", KIND_STRING, _string(value)),
        ),
    )


def blocker_entry_bytes(source: Any) -> bytes:
    details = tuple(blocker_detail_bytes(key, value) for key, value in _value(source, "details"))
    return frame_record(
        BLOCKER_ENTRY_NAMESPACE,
        (
            _field("code", KIND_ENUM, _enum(_value(source, "code"))),
            _field("stage", KIND_ENUM, _enum(_value(source, "stage"))),
            _field("field_path", *_none_or_string(_value(source, "field_path"))),
            _field("message_key", KIND_STRING, _string(_value(source, "message_key"))),
            _field(
                "details", KIND_TUPLE, frame_tuple(tuple((KIND_RECORD, item) for item in details))
            ),
        ),
    )


def warning_entry_bytes(source: Any) -> bytes:
    return frame_record(
        WARNING_ENTRY_NAMESPACE,
        (
            _field("code", KIND_ENUM, _enum(_value(source, "code"))),
            _field("field_path", *_none_or_string(_value(source, "field_path"))),
            _field("message_key", KIND_STRING, _string(_value(source, "message_key"))),
        ),
    )


def _message_tuple(items: Sequence[Any], *, warning: bool) -> bytes:
    record_fn = warning_entry_bytes if warning else blocker_entry_bytes
    return frame_tuple(tuple((KIND_RECORD, record_fn(item)) for item in items))


def raw_projection_bytes(source: Any) -> bytes:
    if type(source) is FrozenRawProjection:
        value = source
    elif isinstance(source, Mapping):
        value = FrozenRawProjection(source["projection_kind"], source["canonical_bytes_hex"])
    else:
        raise CanonicalizationError("raw projection has wrong type")
    return frame_record(
        RAW_PROJECTION_NAMESPACE,
        (
            _field("projection_kind", KIND_ENUM, _enum(value.projection_kind)),
            _field("canonical_bytes_hex", KIND_STRING, _string(value.canonical_bytes_hex)),
        ),
    )


def raw_projection_child_bytes(source: Any) -> bytes:
    if type(source) is FrozenRawProjection:
        return source.child_bytes
    return raw_projection_bytes(source)


def _provenance_fields(
    source: Any, *, include_terminal: bool
) -> tuple[tuple[str, bytes, bytes], ...]:
    int_fields = {"source_definition_issue", "design_issue"}
    decimal_fields = {
        "task037_task025_area_quantum_m2",
        "modeled_overall_heat_transfer_coefficient_w_m2_k",
        "outer_tube_surface_effective_area_m2",
        "modeled_ua_w_k",
    }
    bool_fields = {
        "task037_producer_precision_limitation_disclosed",
        "task037_producer_precision_threshold_defined",
    }
    enum_fields = {"task037_task025_area_rounding_mode", "overall_u_reference_surface"}
    tuple_fields = {"engineering_source_identity_hashes", "evidence_refs", "deferred_capabilities"}
    fields: list[tuple[str, bytes, bytes]] = []
    for field in PROVENANCE_FIELDS:
        if field == "provenance_hash" and not include_terminal:
            continue
        value = _value(source, field)
        if field in int_fields:
            kind, payload = KIND_INT, _int(value)
        elif field in decimal_fields:
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in bool_fields:
            kind, payload = _bool(value)
        elif field in enum_fields:
            kind, payload = KIND_ENUM, _enum(value)
        elif field in tuple_fields:
            kind, payload = KIND_TUPLE, _string_tuple(value)
        else:
            kind, payload = KIND_STRING, _string(value)
        fields.append(_field(field, kind, payload))
    return tuple(fields)


def provenance_preimage_bytes(source: Any) -> bytes:
    return frame_record(PROVENANCE_NAMESPACE, _provenance_fields(source, include_terminal=False))


def provenance_hash(source: Any) -> str:
    return sha256_hex(provenance_preimage_bytes(source))


def provenance_bytes(source: Any) -> bytes:
    return frame_record(PROVENANCE_NAMESPACE, _provenance_fields(source, include_terminal=True))


def _success_field(source: Any, field: str) -> Any:
    return _value(source, field)


def success_result_bytes(source: Any) -> bytes:
    fields: list[tuple[str, bytes, bytes]] = []
    for field in SUCCESS_RESULT_PREHASH_FIELDS:
        value = _success_field(source, field)
        if field in {
            "full_thermal_resistance_composition_ledger",
            "applicability_ledger",
            "completeness_ledger",
            "warnings",
            "blockers",
            "deferred_capabilities",
        }:
            if field == "full_thermal_resistance_composition_ledger":
                payload = _record_tuple(
                    tuple(thermal_resistance_ledger_row_bytes(item) for item in value)
                )
            elif field == "applicability_ledger":
                payload = _record_tuple(tuple(ledger_row_bytes(item) for item in value))
            elif field == "completeness_ledger":
                payload = _record_tuple(
                    tuple(ledger_row_bytes(item, completeness=True) for item in value)
                )
            elif field == "warnings":
                payload = _message_tuple(value, warning=True)
            elif field == "blockers":
                payload = _message_tuple(value, warning=False)
            else:
                payload = _string_tuple(value)
            fields.append(_field(field, KIND_TUPLE, payload))
        elif field == "provenance":
            fields.append(_record_field(field, provenance_bytes(value)))
        elif field == "overall_u_reference_surface":
            fields.append(_field(field, KIND_ENUM, _enum(value)))
        elif field in {
            "modeled_overall_heat_transfer_coefficient_w_m2_k",
            "outer_tube_surface_effective_area_m2",
            "modeled_ua_w_k",
        }:
            fields.append(_field(field, KIND_DECIMAL, _decimal(value)))
        else:
            fields.append(_field(field, KIND_STRING, _string(value)))
    return frame_record(SUCCESS_RESULT_NAMESPACE, tuple(fields))


def success_result_hash(source: Any) -> str:
    return sha256_hex(success_result_bytes(source))


def result_hash(source: Any) -> str:
    return success_result_hash(source)


def result_id_from_hash(result_hash_value: str) -> str:
    if type(result_hash_value) is not str or len(result_hash_value) != 64:
        raise CanonicalizationError("result hash must be lowercase 64-hex")
    if any(char not in "0123456789abcdef" for char in result_hash_value):
        raise CanonicalizationError("result hash must be lowercase 64-hex")
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, UUID_NAME_PREFIX + result_hash_value))


def result_id(source: Any) -> str:
    return result_id_from_hash(source if type(source) is str else _value(source, "result_hash"))


def _blocked_fields(source: Any, fields: Sequence[str], namespace: str) -> str:
    projected: list[tuple[str, bytes, bytes]] = []
    for field in fields:
        value = _value(source, field)
        if field == "producer_result_identities":
            payload = _record_tuple(tuple(producer_envelope_bytes(item) for item in value))
            projected.append(_field(field, KIND_TUPLE, payload))
        elif field == "blockers":
            projected.append(_field(field, KIND_TUPLE, _message_tuple(value, warning=False)))
        elif field == "warnings":
            projected.append(_field(field, KIND_TUPLE, _message_tuple(value, warning=True)))
        elif field == "deferred_capabilities":
            projected.append(_field(field, KIND_TUPLE, _string_tuple(value)))
        elif field == "provenance_or_none":
            if value is None:
                projected.append(_field(field, KIND_NONE, b""))
            else:
                projected.append(_record_field(field, provenance_bytes(value)))
        elif field == "raw_request_projection":
            if type(value) is FrozenRawProjection:
                child = value.child_bytes
            else:
                child = raw_projection_child_bytes(value)
            projected.append(_field(field, KIND_RAW_PROJECTION, child))
        else:
            kind, payload = _none_or_string(value)
            projected.append(_field(field, kind, payload))
    return sha256_hex(frame_record(namespace, tuple(projected)))


def typed_blocked_result_hash(source: Any) -> str:
    return _blocked_fields(
        source, TYPED_BLOCKED_RESULT_PREHASH_FIELDS, TYPED_BLOCKED_RESULT_HASH_NAMESPACE
    )


def raw_boundary_blocked_result_hash(source: Any) -> str:
    return _blocked_fields(
        source,
        (
            "schema_version",
            "task038_version",
            "implementation_software_version",
            "raw_request_projection",
            "blockers",
            "warnings",
            "deferred_capabilities",
        ),
        RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
    )


__all__ = [
    "CanonicalizationError",
    "HASH_ALGORITHM",
    "KIND_BOOL_FALSE",
    "KIND_BOOL_TRUE",
    "KIND_BYTES",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_INT",
    "KIND_NONE",
    "KIND_RAW_PROJECTION",
    "KIND_RECORD",
    "KIND_STRING",
    "KIND_TUPLE",
    "frame_record",
    "frame_string_tuple",
    "frame_tuple",
    "frame_value",
    "sha256_hex",
    "producer_envelope_bytes",
    "producer_envelope_hash",
    "service_binding_bytes",
    "service_binding_hash",
    "engineering_source_identity_bytes",
    "engineering_source_identity_hash",
    "request_identity_bytes",
    "request_bytes",
    "request_hash",
    "cross_producer_compatibility_bytes",
    "cross_producer_compatibility_hash",
    "resistance_composition_bytes",
    "resistance_composition_hash",
    "outer_area_projection_bytes",
    "outer_area_projection_hash",
    "ua_composition_bytes",
    "ua_composition_hash",
    "thermal_resistance_ledger_row_bytes",
    "thermal_resistance_ledger_row_hash",
    "ledger_row_bytes",
    "blocker_entry_bytes",
    "warning_entry_bytes",
    "raw_projection_bytes",
    "raw_projection_child_bytes",
    "provenance_bytes",
    "provenance_hash",
    "provenance_preimage_bytes",
    "success_result_bytes",
    "success_result_hash",
    "result_hash",
    "result_id",
    "result_id_from_hash",
    "typed_blocked_result_hash",
    "raw_boundary_blocked_result_hash",
]
