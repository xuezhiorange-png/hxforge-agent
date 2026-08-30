"""Typed labeled-record canonicalization for TASK-037.

Every hash node is a fixed-order record.  The implementation deliberately
does not reuse an upstream producer's private canonicalizer: TASK037 owns its
own identity boundary while consuming only public upstream fields.
"""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Mapping, Sequence
from decimal import Decimal
from enum import Enum
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenRawProjection

from .schema import (
    FOULING_AUTHORITY_FIELDS,
    FROZEN_IDENTITY_FIELDS,
    FROZEN_IDENTITY_NAMESPACE,
    PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII,
    PRODUCER_AREA_PRECISION_POLICY_HASH,
    PROVENANCE_FIELDS,
    PROVENANCE_NAMESPACE,
    RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
    RAW_PROJECTION_NAMESPACE,
    REQUEST_FIELDS,
    REQUEST_HASH_NAMESPACE,
    SUCCESS_RESULT_FIELDS,
    SURFACE_TRANSFORM_FIELDS,
    SURFACE_TRANSFORM_NAMESPACE,
    TYPED_BLOCKED_RESULT_FIELDS,
    TYPED_BLOCKED_RESULT_HASH_NAMESPACE,
    UUID_NAME_PREFIX,
    UUID_NAMESPACE,
    WALL_RESISTANCE_FIELDS,
    WALL_RESISTANCE_NAMESPACE,
)

# Remove accidental aliases from static type checkers while retaining a small
# compatibility surface for callers that imported these names in early drafts.
PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in PROVENANCE_FIELDS if field != "provenance_hash"
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
    """Raised when a value cannot enter a TASK037 canonical projection."""


def _u32_be(value: int) -> bytes:
    if type(value) is not int or value < 0 or value > 0xFFFFFFFF:
        raise CanonicalizationError("u32 value out of range")
    return value.to_bytes(4, "big", signed=False)


def _u64_be(value: int) -> bytes:
    if type(value) is not int or value < 0 or value > 0xFFFFFFFFFFFFFFFF:
        raise CanonicalizationError("u64 value out of range")
    return value.to_bytes(8, "big", signed=False)


def frame_value(kind_tag_ascii: bytes | str, payload_bytes: bytes) -> bytes:
    """Encode a typed value using the frozen universal frame."""

    if type(kind_tag_ascii) is bytes:
        kind = kind_tag_ascii
    elif type(kind_tag_ascii) is str:
        try:
            kind = kind_tag_ascii.encode("ascii")
        except UnicodeEncodeError as exc:
            raise CanonicalizationError("kind tag must be ASCII") from exc
    else:
        raise CanonicalizationError("kind tag must be exact ASCII bytes or str")
    try:
        kind.decode("ascii")
    except UnicodeDecodeError as exc:
        raise CanonicalizationError("kind tag must be ASCII") from exc
    if type(payload_bytes) is not bytes:
        raise CanonicalizationError("frame payload must be exact bytes")
    payload = payload_bytes
    return _u32_be(len(kind)) + kind + _u64_be(len(payload)) + payload


def frame_string_tuple(items: Sequence[str]) -> bytes:
    """Encode STRING_TUPLE_PAYLOAD (raw length-delimited UTF-8 items)."""

    if not isinstance(items, (tuple, list)):
        raise CanonicalizationError("tuple projection requires tuple/list")
    out = bytearray(_u32_be(len(items)))
    for item in items:
        if type(item) is not str:
            raise CanonicalizationError("string tuple item must be exact str")
        raw = item.encode("utf-8")
        out.extend(_u32_be(len(raw)))
        out.extend(raw)
    return bytes(out)


def frame_record(
    namespace: str,
    fields: Sequence[tuple[str, bytes, bytes]],
) -> bytes:
    """Encode a fixed-order HASH_RECORD."""

    if type(namespace) is not str:
        raise CanonicalizationError("namespace must be exact str")
    namespace_bytes = namespace.encode("utf-8")
    out = bytearray(_u32_be(len(namespace_bytes)))
    out.extend(namespace_bytes)
    out.extend(_u32_be(len(fields)))
    for field_name, kind_tag, payload in fields:
        if type(field_name) is not str:
            raise CanonicalizationError("field name must be exact str")
        name_bytes = field_name.encode("utf-8")
        out.extend(_u32_be(len(name_bytes)))
        out.extend(name_bytes)
        out.extend(frame_value(kind_tag, payload))
    return bytes(out)


def sha256_hex(value: bytes) -> str:
    if type(value) is not bytes:
        raise TypeError("sha256_hex expects bytes")
    return hashlib.sha256(value).hexdigest()


def _attr_or_key(value: Any, field: str) -> Any:
    if isinstance(value, Mapping):
        return value[field]
    return getattr(value, field)


def _string(value: Any) -> bytes:
    if type(value) is not str:
        raise CanonicalizationError("STRING payload requires exact str")
    return value.encode("utf-8")


def _int(value: Any) -> bytes:
    if type(value) is not int:
        raise CanonicalizationError("INT payload requires exact int")
    # Integer lexical payload is the frozen ASCII decimal spelling.
    return str(value).encode("ascii")


def _decimal(value: Any) -> bytes:
    if type(value) is not Decimal or not value.is_finite():
        raise CanonicalizationError("DECIMAL payload requires finite Decimal")
    return str(value).encode("ascii")


def _enum_token(value: Any) -> bytes:
    token = value.value if isinstance(value, Enum) else value
    return _string(token)


def _bool(value: Any, expected: bool | None = None) -> tuple[bytes, bytes]:
    if type(value) is not bool:
        raise CanonicalizationError("BOOL payload requires exact bool")
    if expected is not None and value is not expected:
        raise CanonicalizationError("BOOL value does not match frozen kind")
    return (KIND_BOOL_TRUE if value else KIND_BOOL_FALSE, b"")


def _tuple(value: Any) -> bytes:
    if not isinstance(value, (tuple, list)):
        raise CanonicalizationError("TUPLE payload requires tuple/list")
    return frame_string_tuple(value)


def _message_record_bytes(value: Any, *, warning: bool = False) -> bytes:
    if isinstance(value, Mapping):
        get = value.get
    else:

        def get(name: str, default: Any = None) -> Any:
            return getattr(value, name, default)

    fields: list[tuple[str, bytes, bytes]] = [
        _field("code", KIND_STRING, _string(get("code"))),
    ]
    if not warning:
        fields.append(_field("stage", KIND_STRING, _string(get("stage"))))
    field_path = get("field_path")
    fields.append(
        _field(
            "field_path",
            KIND_NONE if field_path is None else KIND_STRING,
            b"" if field_path is None else _string(field_path),
        )
    )
    fields.append(_field("message_key", KIND_STRING, _string(get("message_key", ""))))
    if not warning:
        details = get("details", ())
        detail_items = tuple(f"{key}={value}" for key, value in details)
        fields.append(_field("details", KIND_TUPLE, frame_string_tuple(detail_items)))
    namespace = "task037.warning-entry.v1" if warning else "task037.blocker-entry.v1"
    return frame_record(namespace, tuple(fields))


def _message_tuple(value: Any, *, warning: bool = False) -> bytes:
    if not isinstance(value, (tuple, list)):
        raise CanonicalizationError("message tuple requires tuple/list")
    out = bytearray(_u32_be(len(value)))
    for item in value:
        out.extend(frame_value(KIND_RECORD, _message_record_bytes(item, warning=warning)))
    return bytes(out)


def _record(value: Any, namespace: str, fields: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    del value  # kept in the signature to make call sites visibly typed
    return frame_record(namespace, fields)


def _authority_record_bytes(value: Any, namespace: str, fields: Sequence[str]) -> bytes:
    projected: list[tuple[str, bytes, bytes]] = []
    decimal_names = {
        "thermal_conductivity_w_m_k",
        "evaluation_temperature_k",
        "fouling_resistance_m2_k_w",
    }
    tuple_names = {"evidence_refs"}
    for name in fields:
        item = _attr_or_key(value, name)
        if name in decimal_names:
            kind, payload = KIND_DECIMAL, _decimal(item)
        elif name in tuple_names:
            kind, payload = KIND_TUPLE, _tuple(item)
        else:
            kind, payload = KIND_STRING, _string(item)
        projected.append(_field(name, kind, payload))
    return frame_record(namespace, tuple(projected))


def _field(name: str, kind: bytes, payload: bytes) -> tuple[str, bytes, bytes]:
    return name, kind, payload


def identity_bytes(identity: Any) -> bytes:
    fields = (
        _field("identity_type", KIND_STRING, _string(_attr_or_key(identity, "identity_type"))),
        _field("identity_id", KIND_STRING, _string(_attr_or_key(identity, "identity_id"))),
        _field("identity_hash", KIND_STRING, _string(_attr_or_key(identity, "identity_hash"))),
    )
    return frame_record(FROZEN_IDENTITY_NAMESPACE, fields)


def identity_projection(identity: Any) -> bytes:
    return identity_bytes(identity)


def fouling_authority_bytes(authority: Any) -> bytes:
    """Encode the 12-field nested R7 fouling identity record."""

    values = {field: _attr_or_key(authority, field) for field in FOULING_AUTHORITY_FIELDS}
    fields: list[tuple[str, bytes, bytes]] = [
        _field("authority_id", KIND_STRING, _string(values["authority_id"])),
        _field("reference_surface", KIND_ENUM, _enum_token(values["reference_surface"])),
        _field(
            "resistance_value_m2_k_w",
            KIND_DECIMAL,
            _decimal(values["resistance_value_m2_k_w"]),
        ),
        _field("resistance_units", KIND_STRING, _string(values["resistance_units"])),
        _field("fluid_service_id", KIND_STRING, _string(values["fluid_service_id"])),
        _field("source_id", KIND_STRING, _string(values["source_id"])),
        _field("source_version", KIND_STRING, _string(values["source_version"])),
        _field("source_location", KIND_STRING, _string(values["source_location"])),
        _field("permission_status", KIND_ENUM, _enum_token(values["permission_status"])),
        _field("approval_status", KIND_ENUM, _enum_token(values["approval_status"])),
        _field("applicability", KIND_ENUM, _enum_token(values["applicability"])),
        _field("authority_hash", KIND_STRING, _string(values["authority_hash"])),
    ]
    return frame_record("task037.fouling-authority.v1", fields)


def _surface_values(source: Any) -> dict[str, Any]:
    return {field: _attr_or_key(source, field) for field in SURFACE_TRANSFORM_FIELDS}


def surface_transform_authority_bytes(source: Any) -> bytes:
    values = _surface_values(source)
    fields: list[tuple[str, bytes, bytes]] = []
    for field in SURFACE_TRANSFORM_FIELDS:
        value = values[field]
        if field in {
            "task021_layout_hash",
            "task025_result_hash",
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "engineering_source_id",
        }:
            kind, payload = KIND_STRING, _string(value)
        elif field in {
            "tube_inner_diameter_m",
            "tube_outer_diameter_m",
            "outer_to_inner_area_ratio",
        }:
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in {"tube_side_film_reference_surface", "overall_u_reference_surface"}:
            kind, payload = KIND_ENUM, _enum_token(value)
        elif field == "engineering_source_locations":
            kind, payload = KIND_TUPLE, _tuple(value)
        else:  # pragma: no cover - fields are frozen above
            raise CanonicalizationError(f"unknown surface field {field!r}")
        fields.append(_field(field, kind, payload))
    return frame_record(SURFACE_TRANSFORM_NAMESPACE, fields)


def surface_transform_authority_hash(source: Any) -> str:
    return sha256_hex(surface_transform_authority_bytes(source))


def surface_hash(source: Any) -> str:
    return surface_transform_authority_hash(source)


def request_bytes(request: Any) -> bytes:
    material_fields = (
        "authority_id",
        "material_id",
        "material_grade",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
        "evidence_refs",
        "authority_hash",
    )
    conductivity_fields = (
        "authority_id",
        "material_id",
        "thermal_conductivity_w_m_k",
        "evaluation_temperature_k",
        "evaluation_context_id",
        "evaluation_basis",
        "applicability_authority_hash",
        "source_id",
        "source_version",
        "source_location",
        "source_class",
        "permission_status",
        "approval_status",
        "evidence_refs",
        "authority_hash",
    )
    fields: list[tuple[str, bytes, bytes]] = []
    for name in REQUEST_FIELDS:
        value = _attr_or_key(request, name)
        if name in {"schema_version", "task037_version", "implementation_software_version"}:
            fields.append(_field(name, KIND_STRING, _string(value)))
        elif name == "wall_material_authority":
            fields.append(
                _field(
                    name,
                    KIND_RECORD,
                    _authority_record_bytes(
                        value, "task037.wall-material-authority.v1", material_fields
                    ),
                )
            )
        elif name == "wall_thermal_conductivity_authority":
            fields.append(
                _field(
                    name,
                    KIND_RECORD,
                    _authority_record_bytes(
                        value, "task037.wall-conductivity-authority.v1", conductivity_fields
                    ),
                )
            )
        elif name in {"inside_fouling_authority", "outside_fouling_authority"}:
            fields.append(_field(name, KIND_RECORD, fouling_authority_bytes(value)))
        elif name == "evidence_refs":
            fields.append(_field(name, KIND_TUPLE, _tuple(value)))
        else:  # pragma: no cover - REQUEST_FIELDS is frozen
            raise CanonicalizationError(f"unknown request field {name!r}")
    return frame_record(REQUEST_HASH_NAMESPACE, tuple(fields))


def request_hash(source: Any) -> str:
    return sha256_hex(request_bytes(source))


def producer_area_precision_policy_bytes() -> bytes:
    return PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII.encode("ascii")


def producer_area_precision_policy_hash() -> str:
    return sha256_hex(producer_area_precision_policy_bytes())


def _wall_values(source: Any) -> dict[str, Any]:
    return {field: _attr_or_key(source, field) for field in WALL_RESISTANCE_FIELDS}


def wall_resistance_authority_bytes(source: Any) -> bytes:
    values = _wall_values(source)
    fields: list[tuple[str, bytes, bytes]] = []
    decimal_fields = {
        "task025_internal_heat_transfer_surface_area_m2",
        "task025_area_quantum_m2",
        "wall_bundle_conduction_resistance_k_w",
        "wall_resistance_outer_surface_m2_k_w",
    }
    enum_fields = {"task025_area_rounding_mode"}
    bool_fields = {
        "producer_precision_limitation_disclosed",
        "producer_precision_threshold_defined",
        "thin_wall_approximation_used",
    }
    for field in WALL_RESISTANCE_FIELDS:
        value = values[field]
        if field in decimal_fields:
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in enum_fields:
            kind, payload = KIND_STRING, _string(value)
        elif field in bool_fields:
            kind, payload = _bool(value)
        else:
            kind, payload = KIND_STRING, _string(value)
        fields.append(_field(field, kind, payload))
    return frame_record(WALL_RESISTANCE_NAMESPACE, fields)


def wall_resistance_authority_hash(source: Any) -> str:
    return sha256_hex(wall_resistance_authority_bytes(source))


def _tuple_field(name: str, values: Any) -> tuple[str, bytes, bytes]:
    return _field(name, KIND_TUPLE, _tuple(values))


def _provenance_value(source: Any, field: str, default: Any = None) -> Any:
    if isinstance(source, Mapping):
        return source.get(field, default)
    return getattr(source, field, default)


def _provenance_fields(source: Any, include_terminal: bool) -> tuple[tuple[str, bytes, bytes], ...]:
    fields: list[tuple[str, bytes, bytes]] = []
    int_fields = {
        "source_definition_issue",
        "source_definition_review_audit_comment",
        "design_issue",
    }
    decimal_fields = {
        "task025_internal_heat_transfer_surface_area_m2",
        "task025_area_quantum_m2",
    }
    bool_fields = {
        "producer_precision_limitation_disclosed",
        "producer_precision_threshold_defined",
    }
    tuple_fields = {
        "source_identity_hashes",
        "producer_edges",
        "evidence_refs",
        "deferred_capabilities",
    }
    for field in PROVENANCE_FIELDS:
        if field == "provenance_hash" and not include_terminal:
            continue
        value = _provenance_value(source, field)
        if field in int_fields:
            kind, payload = KIND_INT, _int(value)
        elif field in decimal_fields:
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in bool_fields:
            kind, payload = _bool(value)
        elif field in tuple_fields:
            kind, payload = KIND_TUPLE, _tuple(value)
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


def _result_value(source: Any, field: str) -> Any:
    return _attr_or_key(source, field)


def _result_fields(source: Any) -> tuple[tuple[str, bytes, bytes], ...]:
    fields: list[tuple[str, bytes, bytes]] = []
    string_fields = {
        "request_hash",
        "task025_hydraulic_authority_hash",
        "tube_geometry_snapshot_hash",
        "heat_transfer_length_hash",
        "surface_transform_authority_hash",
        "wall_material_authority_hash",
        "wall_conductivity_authority_hash",
    }
    enum_fields = {"tube_side_film_reference_surface", "overall_u_reference_surface"}
    decimal_fields = {
        "outer_to_inner_area_ratio",
        "wall_bundle_conduction_resistance_k_w",
        "wall_resistance_outer_surface_m2_k_w",
    }
    record_fields = {
        "task021_identity": identity_bytes,
        "task025_identity": identity_bytes,
        "inside_fouling_authority": fouling_authority_bytes,
        "outside_fouling_authority": fouling_authority_bytes,
        "provenance": provenance_bytes,
    }
    tuple_fields = {
        "fouling_authority_ledger",
        "applicability_ledger",
        "completeness_ledger",
        "warnings",
        "blockers",
        "deferred_capabilities",
    }
    for field in SUCCESS_RESULT_FIELDS:
        value = _result_value(source, field)
        if field in string_fields:
            kind, payload = KIND_STRING, _string(value)
        elif field in enum_fields:
            kind, payload = KIND_ENUM, _enum_token(value)
        elif field in decimal_fields:
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in record_fields:
            kind, payload = KIND_RECORD, record_fields[field](value)
        elif field == "wall_bundle_conduction_resistance_k_w":
            kind, payload = KIND_DECIMAL, _decimal(value)
        elif field in tuple_fields:
            kind, payload = KIND_TUPLE, _tuple(value)
        else:  # wall field names are intentionally explicit
            raise CanonicalizationError(f"unknown result field {field!r}")
        fields.append(_field(field, kind, payload))
    return tuple(fields)


def success_result_bytes(source: Any) -> bytes:
    return frame_record("task037.success-result.v1", _result_fields(source))


def success_result_hash(source: Any) -> str:
    return sha256_hex(success_result_bytes(source))


def result_hash(source: Any) -> str:
    return success_result_hash(source)


def result_id_from_hash(result_hash_value: str) -> str:
    if type(result_hash_value) is not str or len(result_hash_value) != 64:
        raise CanonicalizationError("result_hash must be 64-character lowercase hex")
    if any(char not in "0123456789abcdef" for char in result_hash_value):
        raise CanonicalizationError("result_hash must be lowercase hex")
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, UUID_NAME_PREFIX + result_hash_value))


def result_id(source: Any) -> str:
    if type(source) is str:
        return result_id_from_hash(source)
    return result_id_from_hash(_result_value(source, "result_hash"))


def _hash_blocked_source(source: Any, namespace: str, fields: tuple[str, ...]) -> str:
    projected: list[tuple[str, bytes, bytes]] = []
    for field in fields:
        value = _result_value(source, field)
        if field == "blockers":
            projected.append(_field(field, KIND_TUPLE, _message_tuple(value)))
        elif field == "warnings":
            projected.append(_field(field, KIND_TUPLE, _message_tuple(value, warning=True)))
        elif field == "deferred_capabilities":
            projected.append(_tuple_field(field, value))
        elif field == "raw_request_projection":
            if type(value) is bytes:
                raw = value
            elif type(value) is FrozenRawProjection:
                raw = bytes.fromhex(value.canonical_bytes_hex)
            else:
                raw = raw_projection_bytes(value)
            projected.append(_field(field, KIND_RAW_PROJECTION, raw))
        elif field in {"task021_identity", "task025_identity"} and value is not None:
            projected.append(_field(field, KIND_RECORD, identity_bytes(value)))
        elif field in {
            "request_hash",
            "task025_hydraulic_authority_hash",
            "tube_geometry_snapshot_hash",
            "heat_transfer_length_hash",
        }:
            if value is None:
                projected.append(_field(field, KIND_NONE, b""))
            else:
                projected.append(_field(field, KIND_STRING, _string(value)))
        elif field == "provenance":
            if value is None:
                projected.append(_field(field, KIND_NONE, b""))
            else:
                projected.append(_field(field, KIND_RECORD, provenance_bytes(value)))
        else:
            if value is None:
                projected.append(_field(field, KIND_NONE, b""))
            elif type(value) is str:
                projected.append(_field(field, KIND_STRING, _string(value)))
            else:
                raise CanonicalizationError(f"unsupported blocked field {field!r}")
    return sha256_hex(frame_record(namespace, tuple(projected)))


def typed_blocked_result_hash(source: Any) -> str:
    fields = tuple(field for field in TYPED_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash")
    return _hash_blocked_source(source, TYPED_BLOCKED_RESULT_HASH_NAMESPACE, fields)


def raw_boundary_blocked_result_hash(source: Any) -> str:
    fields = (
        "schema_version",
        "task037_version",
        "implementation_software_version",
        "raw_request_projection",
        "blockers",
        "warnings",
        "deferred_capabilities",
    )
    return _hash_blocked_source(source, RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE, fields)


def raw_projection_bytes(value: Any) -> bytes:
    if type(value) is bytes:
        return value
    if type(value) is str:
        return frame_value(KIND_STRING, value.encode("utf-8"))
    return frame_record(
        RAW_PROJECTION_NAMESPACE,
        (_field("type", KIND_STRING, type(value).__name__.encode("utf-8")),),
    )


__all__ = [
    "CanonicalizationError",
    "FROZEN_IDENTITY_FIELDS",
    "FOULING_AUTHORITY_FIELDS",
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
    "PRODUCER_AREA_PRECISION_POLICY_HASH",
    "PRODUCER_AREA_PRECISION_POLICY_CANONICAL_ASCII",
    "PROVENANCE_FIELDS",
    "PROVENANCE_PREHASH_FIELDS",
    "RESULT_ID_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "SUCCESS_RESULT_FIELDS",
    "WALL_RESISTANCE_FIELDS",
    "frame_record",
    "frame_string_tuple",
    "frame_value",
    "fouling_authority_bytes",
    "identity_bytes",
    "producer_area_precision_policy_bytes",
    "producer_area_precision_policy_hash",
    "provenance_bytes",
    "provenance_hash",
    "provenance_preimage_bytes",
    "raw_boundary_blocked_result_hash",
    "raw_projection_bytes",
    "result_hash",
    "result_id",
    "result_id_from_hash",
    "sha256_hex",
    "success_result_bytes",
    "success_result_hash",
    "surface_hash",
    "surface_transform_authority_bytes",
    "surface_transform_authority_hash",
    "typed_blocked_result_hash",
    "wall_resistance_authority_bytes",
    "wall_resistance_authority_hash",
]
