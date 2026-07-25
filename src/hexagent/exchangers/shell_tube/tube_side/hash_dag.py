"""TASK-025 product identity graph.

# mypy: ignore-errors

§10 — Eight product hash nodes with the universal labeled-record framing.
§10.2 — Frozen topological order.
"""




from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.tube_side.owned_enums import (
    HydraulicAuthorityMode,
    ReferencePlanePair,
)
from hexagent.exchangers.shell_tube.tube_side.provenance import FrozenIdentity
from hexagent.exchangers.shell_tube.tube_side.raw_projection import (
    project_raw_value,
)

# §10.1 — Universal framing node namespaces.
_NS_INTERNAL_FLOW_LENGTH: Final[bytes] = b"task025.internal-flow-length-authority.v1"
_NS_HEAT_TRANSFER_LENGTH: Final[bytes] = b"task025.heat-transfer-length-authority.v1"
_NS_LAYOUT_HASH: Final[bytes] = b"task021.layout-hash.passthrough.v1"
_NS_HYDRAULIC_AUTHORITY: Final[bytes] = b"task025.hydraulic-participation-authority.v1"
_NS_REQUEST: Final[bytes] = b"task025.request.v1"
_NS_VALID_RESULT: Final[bytes] = b"task025.valid-result.v1"
_NS_BLOCKED_RESULT: Final[bytes] = b"task025.blocked-result.v1"

# §10.9 — UUID namespace and result_id logical name bytes.
_RESULT_ID_NAMESPACE: Final[str] = "a0250000-0000-5000-8000-000000000002"
_RESULT_ID_NAME_BYTES: Final[bytes] = b"task025-result-v1"


# -----------------------------------------------------------------------
# Frame builder.
# -----------------------------------------------------------------------


def _u32_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFF:
        raise ValueError("u32_be out of range")
    return n.to_bytes(4, "big", signed=False)


def _u64_be(n: int) -> bytes:
    if n < 0 or n > 0xFFFFFFFFFFFFFFFF:
        raise ValueError("u64_be out of range")
    return n.to_bytes(8, "big", signed=False)


def _frame_value(kind_tag: bytes, payload: bytes) -> bytes:
    return _u32_be(len(kind_tag)) + kind_tag + _u64_be(len(payload)) + payload


def _frame_record(
    namespace: bytes,
    fields: tuple[tuple[str, bytes, bytes], ...],
) -> bytes:
    out = _u32_be(len(namespace)) + namespace + _u32_be(len(fields))
    for name, kind_tag, payload in fields:
        out += _u32_be(len(name)) + name.encode("utf-8") + _frame_value(kind_tag, payload)
    return out


# -----------------------------------------------------------------------
# §10.3 — internal_flow_authority.length_hash (Node 1)
# §10.4 — heat_transfer_authority.length_hash (Node 2)
# -----------------------------------------------------------------------


def internal_flow_authority_length_hash(
    length_m: Decimal,
    start_plane_pair: ReferencePlanePair,
    end_plane_pair: ReferencePlanePair,
    authority_mode: HydraulicAuthorityMode,
) -> str:
    fields = (
        ("length_m", b"DECIMAL", str(length_m).encode("ascii")),
        ("start_plane", b"RECORD", _frame_reference_plane_pair(start_plane_pair)),
        ("end_plane", b"RECORD", _frame_reference_plane_pair(end_plane_pair)),
        ("authority_mode", b"ENUM", authority_mode.name.encode("ascii")),
    )
    framed = _frame_record(_NS_INTERNAL_FLOW_LENGTH, fields)
    return sha256_hex_from_framed_bytes(framed)


def heat_transfer_authority_length_hash(
    length_m: Decimal,
    start_plane_pair: ReferencePlanePair,
    end_plane_pair: ReferencePlanePair,
    authority_mode: HydraulicAuthorityMode,
) -> str:
    fields = (
        ("length_m", b"DECIMAL", str(length_m).encode("ascii")),
        ("start_plane", b"RECORD", _frame_reference_plane_pair(start_plane_pair)),
        ("end_plane", b"RECORD", _frame_reference_plane_pair(end_plane_pair)),
        ("authority_mode", b"ENUM", authority_mode.name.encode("ascii")),
    )
    framed = _frame_record(_NS_HEAT_TRANSFER_LENGTH, fields)
    return sha256_hex_from_framed_bytes(framed)


def _frame_reference_plane_pair(pair: ReferencePlanePair) -> bytes:
    """§10.3 / §10.4 — frame a ReferencePlanePair for the hash field."""
    fields = (
        ("start", b"ENUM", pair.start.name.encode("ascii")),
        ("end", b"ENUM", pair.end.name.encode("ascii")),
    )
    return _frame_record(b"task025.reference-plane-pair.v1", fields)


# -----------------------------------------------------------------------
# §10.5 — layout_hash (Node 3) passthrough
# -----------------------------------------------------------------------


def layout_hash_passthrough(task021_layout_hash: str) -> str:
    """§10.5 — Validate 64-lowercase-hex; pass through byte-for-byte."""
    _validate_64hex(task021_layout_hash, "layout_hash")
    return task021_layout_hash


def _validate_64hex(value: str, field_path: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")
    return value


# -----------------------------------------------------------------------
# §10.6 — hydraulic_authority_hash (Node 4)
# -----------------------------------------------------------------------


def hydraulic_authority_hash(
    task020_configuration_id: str,
    task021_layout_id: str,
    internal_flow_length_hash_value: str,
    heat_transfer_length_hash_value: str,
    all_layout_position_ids: tuple[str, ...],
    active_position_ids: tuple[str, ...],
    inactive_position_ids: tuple[str, ...],
    hydraulic_authority_mode: HydraulicAuthorityMode,
    participation_evidence_refs: tuple[str, ...],
) -> str:
    fields = (
        ("task020_configuration_id", b"STRING", task020_configuration_id.encode("utf-8")),
        ("task021_layout_id", b"STRING", task021_layout_id.encode("utf-8")),
        (
            "internal_flow_length_hash",
            b"STRING",
            internal_flow_length_hash_value.encode("ascii"),
        ),
        (
            "heat_transfer_length_hash",
            b"STRING",
            heat_transfer_length_hash_value.encode("ascii"),
        ),
        ("all_layout_position_ids", b"TUPLE", _frame_string_tuple(all_layout_position_ids)),
        ("active_position_ids", b"TUPLE", _frame_string_tuple(active_position_ids)),
        ("inactive_position_ids", b"TUPLE", _frame_string_tuple(inactive_position_ids)),
        ("hydraulic_authority_mode", b"ENUM", hydraulic_authority_mode.name.encode("ascii")),
        ("evidence_refs", b"TUPLE", _frame_string_tuple(participation_evidence_refs)),
    )
    framed = _frame_record(_NS_HYDRAULIC_AUTHORITY, fields)
    return sha256_hex_from_framed_bytes(framed)


def _frame_string_tuple(items: tuple[str, ...]) -> bytes:
    out = _u32_be(len(items))
    for item in items:
        item_bytes = item.encode("utf-8")
        out += _u32_be(len(item_bytes)) + item_bytes
    return out


# -----------------------------------------------------------------------
# §10.7 — request_hash (Node 5)
# -----------------------------------------------------------------------


def request_hash(
    request: Any,
    precomputed_field_bytes: dict[str, bytes] | None = None,
) -> str:
    """§10.7 — Project exactly the 10 TASK025_REQUEST_FIELDS and hash.

    ``precomputed_field_bytes`` lets the scheduler supply already-projected
    bytes for upstream objects (length authorities, layout, configuration)
    to avoid double projection.
    """
    from hexagent.exchangers.shell_tube.tube_side.request import (
        TASK025_REQUEST_FIELDS,
    )

    fields: list[tuple[str, bytes, bytes]] = []
    pre = precomputed_field_bytes or {}
    for field_name in TASK025_REQUEST_FIELDS:
        if field_name in pre:
            # Use the caller-supplied framed bytes for the value.
            kind_tag_p, payload_p = pre[field_name]
            kind_tag = kind_tag_p if isinstance(kind_tag_p, bytes) else bytes(kind_tag_p)
            payload = payload_p if isinstance(payload_p, bytes) else bytes(payload_p)
            fields.append((field_name, kind_tag, payload))
            continue
        field_value = getattr(request, field_name)
        kind_tag, payload = _project_for_request_field(field_name, field_value)
        fields.append((field_name, kind_tag, payload))
    framed = _frame_record(_NS_REQUEST, tuple(fields))
    return sha256_hex_from_framed_bytes(framed)


def _project_for_request_field(field_name: str, field_value: Any) -> tuple[bytes, bytes]:
    """Return the (kind_tag, framed_payload) for a request field."""

    if field_name == "schema_version":
        return b"STRING", field_value.encode("utf-8")
    if field_name == "profile_id":
        return b"STRING", field_value.encode("utf-8")
    if field_name == "task020_configuration":
        return b"RECORD", project_raw_value(field_value)
    if field_name == "task021_layout":
        return b"RECORD", project_raw_value(field_value)
    if field_name in ("internal_flow_authority", "heat_transfer_authority"):
        return b"RECORD", project_raw_value(field_value)
    if field_name == "hydraulic_participation_authority":
        return b"RECORD", project_raw_value(field_value)
    if field_name in ("flow_path_mode", "hydraulic_authority_mode"):
        return b"ENUM", field_value.name.encode("ascii")
    if field_name == "evidence_refs":
        return b"TUPLE", _frame_string_tuple(tuple(field_value))
    raise ValueError(f"unknown request field {field_name!r}")


# -----------------------------------------------------------------------
# §10.8 — result_hash (Node 6)
# -----------------------------------------------------------------------


def result_hash(result: Any) -> str:
    """§10.8 — Project the 21 RESULT_HASH_FIELDS and hash."""
    fields: list[tuple[str, bytes, bytes]] = []
    for field_name in (
        "request_hash",
        "layout_hash",
        "hydraulic_authority_hash",
        "single_tube_flow_area_m2",
        "total_parallel_flow_area_m2",
        "flow_cross_section_wetted_perimeter_m",
        "total_flow_cross_section_wetted_perimeter_m",
        "hydraulic_diameter_m",
        "internal_volume_m3",
        "internal_heat_transfer_surface_area_m2",
        "future_pressure_drop_length_m",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "stage_rank",
        "schema_version",
        "profile_id",
        "implementation_software_version",
        "task020_identity",
        "task021_identity",
    ):
        field_value = getattr(result, field_name)
        kind_tag, payload = _project_for_result_field(field_name, field_value)
        fields.append((field_name, kind_tag, payload))
    framed = _frame_record(_NS_VALID_RESULT, tuple(fields))
    return sha256_hex_from_framed_bytes(framed)


def _project_for_result_field(field_name: str, field_value: Any) -> tuple[bytes, bytes]:
    if field_name in (
        "request_hash",
        "layout_hash",
        "hydraulic_authority_hash",
    ):
        return b"STRING", field_value.encode("ascii")
    if field_name in (
        "single_tube_flow_area_m2",
        "total_parallel_flow_area_m2",
        "flow_cross_section_wetted_perimeter_m",
        "total_flow_cross_section_wetted_perimeter_m",
        "hydraulic_diameter_m",
        "internal_volume_m3",
        "internal_heat_transfer_surface_area_m2",
    ):
        return b"DECIMAL", str(field_value).encode("ascii")
    if field_name == "future_pressure_drop_length_m":
        if field_value is None:
            return b"NONE", b""
        return b"DECIMAL", str(field_value).encode("ascii")
    if field_name in ("warnings", "blockers", "deferred_capabilities"):
        return b"TUPLE", _frame_string_tuple(tuple(str(x) for x in field_value))
    if field_name == "stage_rank":
        return b"INT", str(field_value).encode("ascii")
    if field_name in ("schema_version", "profile_id", "implementation_software_version"):
        return b"STRING", field_value.encode("utf-8")
    if field_name in ("task020_identity", "task021_identity"):
        # FrozenIdentity projected as identity_type + identity_id + identity_hash.
        fi: FrozenIdentity = field_value
        sub = (
            ("identity_type", b"STRING", fi.identity_type.encode("utf-8")),
            ("identity_id", b"STRING", fi.identity_id.encode("utf-8")),
            ("identity_hash", b"STRING", fi.identity_hash.encode("ascii")),
        )
        ns = b"hexagent.frozen-identity.v1"
        return b"RECORD", _frame_record(ns, sub)
    raise ValueError(f"unknown result field {field_name!r}")


# -----------------------------------------------------------------------
# §10.9 — result_id (Node 7)
# -----------------------------------------------------------------------


def result_id(result_hash_hex: str) -> str:
    """§10.9 — UUIDv5 with the frozen namespace and lowercase-hex name bytes."""
    _validate_64hex(result_hash_hex, "result_hash")
    ns_uuid = uuid.UUID(_RESULT_ID_NAMESPACE)
    return str(uuid.uuid5(ns_uuid, result_hash_hex.lower().encode("utf-8")))


# -----------------------------------------------------------------------
# §10.10 — blocked_result_hash (Node 8)
# -----------------------------------------------------------------------


def blocked_result_hash(blocked: Any) -> str:
    """§10.10 — Project BLOCKED_RESULT_HASH_FIELDS and hash."""
    from hexagent.exchangers.shell_tube.tube_side.blocked_result import (
        BLOCKED_RESULT_HASH_FIELDS,
    )

    fields: list[tuple[str, bytes, bytes]] = []
    for field_name in BLOCKED_RESULT_HASH_FIELDS:
        field_value = getattr(blocked, field_name)
        kind_tag, payload = _project_for_blocked_field(field_name, field_value)
        fields.append((field_name, kind_tag, payload))
    framed = _frame_record(_NS_BLOCKED_RESULT, tuple(fields))
    return sha256_hex_from_framed_bytes(framed)


def _project_for_blocked_field(field_name: str, field_value: Any) -> tuple[bytes, bytes]:
    if field_name in ("schema_version", "implementation_software_version"):
        return b"STRING", field_value.encode("utf-8")
    if field_name == "resolved_profile_id":
        if field_value is None:
            return b"NONE", b""
        return b"STRING", field_value.encode("utf-8")
    if field_name in ("raw_profile_id_projection", "raw_request_projection"):
        # FrozenRawProjection projection: projection_kind + canonical_bytes_hex.
        sub = (
            ("projection_kind", b"STRING", field_value.projection_kind.encode("utf-8")),
            ("canonical_bytes_hex", b"STRING", field_value.canonical_bytes_hex.encode("ascii")),
        )
        return b"RECORD", _frame_record(b"hexagent.frozen-raw-projection.v1", sub)
    if field_name == "request_hash":
        if field_value is None:
            return b"NONE", b""
        return b"STRING", field_value.encode("ascii")
    if field_name == "blockers":
        return b"TUPLE", _frame_string_tuple(tuple(e.code.value for e in field_value))
    if field_name in ("warnings", "deferred_capabilities"):
        return b"TUPLE", _frame_string_tuple(tuple(str(x) for x in field_value))
    if field_name == "stage_rank":
        return b"INT", str(field_value).encode("ascii")
    if field_name in ("task020_identity", "task021_identity"):
        if field_value is None:
            return b"NONE", b""
        fi: FrozenIdentity = field_value
        sub = (
            ("identity_type", b"STRING", fi.identity_type.encode("utf-8")),
            ("identity_id", b"STRING", fi.identity_id.encode("utf-8")),
            ("identity_hash", b"STRING", fi.identity_hash.encode("ascii")),
        )
        return b"RECORD", _frame_record(b"hexagent.frozen-identity.v1", sub)
    raise ValueError(f"unknown blocked field {field_name!r}")


__all__ = [
    "internal_flow_authority_length_hash",
    "heat_transfer_authority_length_hash",
    "layout_hash_passthrough",
    "hydraulic_authority_hash",
    "request_hash",
    "result_hash",
    "result_id",
    "blocked_result_hash",
    "_RESULT_ID_NAMESPACE",
    "_RESULT_ID_NAME_BYTES",
]