"""TASK-028 canonical framing: authority, request hash, result hash, kind constants, tuple payload.

§24 — Canonical serialization.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    _u32_be,
    _u64_be,
    frame_record,
    frame_value,
    sha256_hex_from_framed_bytes,
)
from hexagent.exchangers.shell_tube.tube_side_local_loss.decimal_identity import (
    LOSS_COEFFICIENT_QUANTUM,
    PRESSURE_LOSS_QUANTUM,
    REFERENCE_FLOW_AREA_QUANTUM,
    REFERENCE_VELOCITY_QUANTUM,
    quantize_task028_decimal,
    task028_decimal_payload,
)

# -----------------------------------------------------------------------
# §10.3 — TASK-028 Kind Constants (NOT reusing TASK-025 KIND_INT).
# -----------------------------------------------------------------------

KIND_NONE: Final[bytes] = b"NONE"
KIND_STRING: Final[bytes] = b"STRING"
KIND_DECIMAL: Final[bytes] = b"DECIMAL"
KIND_ENUM: Final[bytes] = b"ENUM"
KIND_INTEGER: Final[bytes] = b"INTEGER"
KIND_TUPLE: Final[bytes] = b"TUPLE"
KIND_RECORD: Final[bytes] = b"RECORD"
KIND_RAW_PROJECTION: Final[bytes] = b"RAW_PROJECTION"

# -----------------------------------------------------------------------
# §10.4 — TASK-028 Tuple Payload (U64 child-length framing)
# -----------------------------------------------------------------------


def task028_tuple_payload(item_frames: Sequence[bytes]) -> bytes:
    """§10.4 — TASK-028 frozen tuple payload with U64 child-length framing.

    TUPLE_PAYLOAD =
      U32_BE(item_count)
      || for each child in semantic order:
            U64_BE(len(child_frame))
            || child_frame
    """
    out = _u32_be(len(item_frames))
    for frame in item_frames:
        out += _u64_be(len(frame)) + frame
    return out


# -----------------------------------------------------------------------
# §24 — Canonical framing helpers
# -----------------------------------------------------------------------

# Canonical namespaces
REQUEST_HASH_NAMESPACE: Final[str] = "task028.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE: Final[str] = "task028.success-result.v1"
BLOCKED_RESULT_HASH_NAMESPACE: Final[str] = "task028.blocked-result.v1"
RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE: Final[str] = "task028.raw-boundary-blocked-result.v1"
RAW_PROJECTION_NAMESPACE: Final[str] = "task028.raw-projection.v1"
PROVENANCE_NAMESPACE: Final[str] = "task028.provenance.v1"
COMPONENT_RESULT_HASH_NAMESPACE: Final[str] = "task028.component-result.v1"
AUTHORITY_HASH_NAMESPACE: Final[str] = "task028.local-loss-component-authority.v1"

# §15.2 — Frozen UUID Constants
RESULT_ID_NAMESPACE: Final[str] = "a0280000-0000-5000-8000-000000000001"
RESULT_ID_NAME_PREFIX: Final[str] = "task028-result-v1::"

# §11 — Schema and software version
TASK028_REQUEST_SCHEMA_VERSION: Final[str] = "task028.request.v1"
TASK028_SUCCESS_RESULT_SCHEMA_VERSION: Final[str] = "task028.success-result.v1"
TASK028_BLOCKED_RESULT_SCHEMA_VERSION: Final[str] = "task028.blocked-result.v1"
TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION: Final[str] = "task028.raw-boundary-blocked-result.v1"
TASK028_AUTHORITY_SCHEMA_VERSION: Final[str] = "task028.local-loss-component-authority.v1"
IMPLEMENTATION_SOFTWARE_VERSION: Final[str] = "0.1.0"
SUPPORTED_PROFILE_IDS: Final[tuple[str, ...]] = ("profile-001",)

# §5.3 — Fixed deferred capabilities
TASK028_DEFERRED_CAPABILITIES_V1: Final[tuple[str, ...]] = (
    "MODELED_TOTAL_PRESSURE_DROP_NOT_COMPUTED",
    "REFERENCE_PLANE_CONTINUITY_NOT_VALIDATED",
    "PRESSURE_PATH_COMPLETENESS_NOT_VALIDATED",
)

# §11 — Request fields
TASK028_REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "task025_valid_result",
    "task026_success_result",
    "property_snapshot",
    "property_snapshot_hash",
    "constant_density_path_assertion",
    "zero_net_elevation_change_assertion",
    "flow_direction_assertion",
    "component_authorities",
    "request_hash",
)

REQUEST_HASH_FIELD_COUNT: Final[int] = 10


def _encode_string_tuple(items: tuple[str, ...]) -> bytes:
    """Encode a tuple of strings using frozen framed children."""
    return task028_tuple_payload([frame_value(KIND_STRING, item.encode("utf-8")) for item in items])


def _encode_bytes_tuple(items: tuple[bytes, ...]) -> bytes:
    """Encode a tuple of raw bytes using frozen framed children."""
    return task028_tuple_payload(list(items))


def _encode_blocker_entry(entry: Any) -> bytes:
    """Frame a single Task028BlockerEntry as a canonical RECORD."""
    fields = [
        ("code", KIND_STRING, entry.code.value.encode("utf-8")),
        ("field_path", KIND_TUPLE, _encode_string_tuple(entry.field_path)),
        ("message_key", KIND_STRING, entry.message_key.encode("utf-8")),
        ("evidence_refs", KIND_TUPLE, _encode_string_tuple(entry.evidence_refs)),
    ]
    return frame_record("task028.blocker-entry.v1", fields)


def _encode_raw_projection_canonical(projection: Any) -> bytes:
    """Encode a raw projection as frozen canonical nested record."""
    if projection is None:
        return b""
    fields = [
        ("projection_kind", KIND_STRING, projection.projection_kind.encode("utf-8")),
        ("canonical_bytes_hex", KIND_STRING, projection.canonical_bytes_hex.encode("utf-8")),
    ]
    return frame_record(RAW_PROJECTION_NAMESPACE, fields)


def _encode_provenance_canonical(provenance: Any) -> bytes:
    """Encode provenance as frozen canonical nested record."""
    if provenance is None:
        return b""
    fields = [
        ("task_id", KIND_STRING, provenance.task_id.encode("utf-8")),
        ("design_contract_path", KIND_STRING, provenance.design_contract_path.encode("utf-8")),
        (
            "implementation_software_version",
            KIND_STRING,
            provenance.implementation_software_version.encode("utf-8"),
        ),
        (
            "input_evidence_refs",
            KIND_TUPLE,
            _encode_string_tuple(provenance.input_evidence_refs),
        ),
        (
            "upstream_identity_hashes",
            KIND_TUPLE,
            _encode_string_tuple(provenance.upstream_identity_hashes),
        ),
    ]
    return frame_record(PROVENANCE_NAMESPACE, fields)


def canonicalize_authority(
    schema_version: str,
    component_id: str,
    component_type: str,
    path_sequence_index: int,
    upstream_reference_plane: str,
    downstream_reference_plane: str,
    flow_direction_assertion: str,
    loss_coefficient: Decimal,
    loss_coefficient_convention: str,
    reference_flow_area_m2: Decimal,
    multiplicity: int,
    geometry_evidence_refs: tuple[str, ...],
    coefficient_source_id: str,
    coefficient_source_version: str,
    coefficient_source_location: str,
    coefficient_permission_status: str,
) -> tuple[bytes, str]:
    """§24 — Canonical 16-field authority framing → (framed_bytes, sha256_hex).

    Fields 1–16 of the 17-field authority (excludes authority_hash itself).
    loss_coefficient and reference_flow_area_m2 are Decimal, quantized before encoding.
    """
    q_lc = quantize_task028_decimal(loss_coefficient, LOSS_COEFFICIENT_QUANTUM)
    q_rfa = quantize_task028_decimal(reference_flow_area_m2, REFERENCE_FLOW_AREA_QUANTUM)

    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("component_id", KIND_STRING, component_id.encode("utf-8")),
        ("component_type", KIND_ENUM, component_type.encode("ascii")),
        ("path_sequence_index", KIND_INTEGER, str(path_sequence_index).encode("utf-8")),
        ("upstream_reference_plane", KIND_STRING, upstream_reference_plane.encode("utf-8")),
        ("downstream_reference_plane", KIND_STRING, downstream_reference_plane.encode("utf-8")),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        ("loss_coefficient", KIND_DECIMAL, task028_decimal_payload(q_lc, LOSS_COEFFICIENT_QUANTUM)),
        ("loss_coefficient_convention", KIND_ENUM, loss_coefficient_convention.encode("ascii")),
        (
            "reference_flow_area_m2",
            KIND_DECIMAL,
            task028_decimal_payload(q_rfa, REFERENCE_FLOW_AREA_QUANTUM),
        ),
        ("multiplicity", KIND_INTEGER, str(multiplicity).encode("utf-8")),
        ("geometry_evidence_refs", KIND_TUPLE, _encode_string_tuple(geometry_evidence_refs)),
        ("coefficient_source_id", KIND_STRING, coefficient_source_id.encode("utf-8")),
        ("coefficient_source_version", KIND_STRING, coefficient_source_version.encode("utf-8")),
        ("coefficient_source_location", KIND_STRING, coefficient_source_location.encode("utf-8")),
        ("coefficient_permission_status", KIND_ENUM, coefficient_permission_status.encode("ascii")),
    ]
    framed = frame_record(AUTHORITY_HASH_NAMESPACE, fields)
    return framed, sha256_hex_from_framed_bytes(framed)


def canonicalize_request_hash(
    schema_version: str,
    profile_id: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    constant_density_assertion: str,
    zero_elevation_assertion: str,
    flow_direction_assertion: str,
    component_authority_hashes: tuple[str, ...],
) -> str:
    """§14.2 — Compute request hash from 10 semantic fields (namespace task028.request.v1)."""
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            task025_hydraulic_authority_hash.encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, task025_result_hash.encode("utf-8")),
        ("task026_result_hash", KIND_STRING, task026_result_hash.encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, property_snapshot_hash.encode("utf-8")),
        ("constant_density_path_assertion", KIND_ENUM, constant_density_assertion.encode("ascii")),
        (
            "zero_net_elevation_change_assertion",
            KIND_ENUM,
            zero_elevation_assertion.encode("ascii"),
        ),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        (
            "component_authority_hashes",
            KIND_TUPLE,
            _encode_string_tuple(component_authority_hashes),
        ),
    ]
    framed = frame_record(REQUEST_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


def _canonical_component_result_record(record_bytes: bytes) -> bytes:
    """Wrap a canonical component result record in KIND_RECORD framing."""
    return frame_value(KIND_RECORD, record_bytes)


def canonicalize_component_result(
    component_id: str,
    component_type: str,
    path_sequence_index: int,
    upstream_reference_plane: str,
    downstream_reference_plane: str,
    flow_direction_assertion: str,
    authority_hash: str,
    reference_flow_area_m2: Decimal,
    reference_velocity_m_s: Decimal,
    loss_coefficient: Decimal,
    loss_coefficient_convention: str,
    multiplicity: int,
    single_occurrence_irreversible_pressure_loss_pa: Decimal,
    component_irreversible_pressure_loss_pa: Decimal,
) -> tuple[bytes, str]:
    """§24 — Canonical component result hash (14 fields, excludes component_result_hash).

    Returns (record_bytes, sha256_hex). Decimal fields are quantized before encoding.
    """
    q_rfa = quantize_task028_decimal(reference_flow_area_m2, REFERENCE_FLOW_AREA_QUANTUM)
    q_vref = quantize_task028_decimal(reference_velocity_m_s, REFERENCE_VELOCITY_QUANTUM)
    q_lc = quantize_task028_decimal(loss_coefficient, LOSS_COEFFICIENT_QUANTUM)
    q_single = quantize_task028_decimal(
        single_occurrence_irreversible_pressure_loss_pa, PRESSURE_LOSS_QUANTUM
    )
    q_comp = quantize_task028_decimal(
        component_irreversible_pressure_loss_pa, PRESSURE_LOSS_QUANTUM
    )

    fields = [
        ("component_id", KIND_STRING, component_id.encode("utf-8")),
        ("component_type", KIND_ENUM, component_type.encode("ascii")),
        ("path_sequence_index", KIND_INTEGER, str(path_sequence_index).encode("utf-8")),
        ("upstream_reference_plane", KIND_STRING, upstream_reference_plane.encode("utf-8")),
        ("downstream_reference_plane", KIND_STRING, downstream_reference_plane.encode("utf-8")),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        ("authority_hash", KIND_STRING, authority_hash.encode("utf-8")),
        (
            "reference_flow_area_m2",
            KIND_DECIMAL,
            task028_decimal_payload(q_rfa, REFERENCE_FLOW_AREA_QUANTUM),
        ),
        (
            "reference_velocity_m_s",
            KIND_DECIMAL,
            task028_decimal_payload(q_vref, REFERENCE_VELOCITY_QUANTUM),
        ),
        ("loss_coefficient", KIND_DECIMAL, task028_decimal_payload(q_lc, LOSS_COEFFICIENT_QUANTUM)),
        ("loss_coefficient_convention", KIND_ENUM, loss_coefficient_convention.encode("ascii")),
        ("multiplicity", KIND_INTEGER, str(multiplicity).encode("utf-8")),
        (
            "single_occurrence_irreversible_pressure_loss_pa",
            KIND_DECIMAL,
            task028_decimal_payload(q_single, PRESSURE_LOSS_QUANTUM),
        ),
        (
            "component_irreversible_pressure_loss_pa",
            KIND_DECIMAL,
            task028_decimal_payload(q_comp, PRESSURE_LOSS_QUANTUM),
        ),
    ]
    framed = frame_record(COMPONENT_RESULT_HASH_NAMESPACE, fields)
    return framed, sha256_hex_from_framed_bytes(framed)


def canonicalize_success_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    component_result_records: tuple[bytes, ...],
    warnings: tuple[str, ...],
    blockers: tuple[Any, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Any,
) -> str:
    """§15 — Canonical success result hash (self-excludes result_hash, result_id).

    14-field success result → hash projection excludes result_hash and result_id.
    component_result_records are the canonical record bytes for each component.
    """
    # Component results: each child is a framed RECORD wrapping the canonical record bytes
    component_child_frames = (
        [_canonical_component_result_record(rec) for rec in component_result_records]
        if component_result_records
        else []
    )
    component_results_payload = task028_tuple_payload(component_child_frames)
    # Blockers: each child is a framed RECORD wrapping the blocker entry record
    blocker_child_frames = [frame_value(KIND_RECORD, _encode_blocker_entry(b)) for b in blockers]
    blockers_payload = task028_tuple_payload(blocker_child_frames)
    fields: list[tuple[str, bytes, bytes]] = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("request_hash", KIND_STRING, request_hash.encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            task025_hydraulic_authority_hash.encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, task025_result_hash.encode("utf-8")),
        ("task026_result_hash", KIND_STRING, task026_result_hash.encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, property_snapshot_hash.encode("utf-8")),
        ("component_results", KIND_TUPLE, component_results_payload),
        ("warnings", KIND_TUPLE, _encode_string_tuple(warnings)),
        ("blockers", KIND_TUPLE, blockers_payload),
        ("deferred_capabilities", KIND_TUPLE, _encode_string_tuple(deferred_capabilities)),
        (
            "provenance",
            KIND_RECORD if provenance is not None else KIND_NONE,
            b"" if provenance is None else _encode_provenance_canonical(provenance),
        ),
    ]
    framed = frame_record(SUCCESS_RESULT_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


def canonicalize_blocked_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    raw_request_projection: Any,
    raw_upstream_blocked_projection: Any,
    warnings: tuple[str, ...],
    blockers: tuple[Any, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Any,
) -> str:
    """§15 — Canonical blocked result hash (self-excludes result_hash, result_id)."""
    # Blockers: each child is a framed RECORD wrapping the blocker entry record
    blocker_child_frames = [frame_value(KIND_RECORD, _encode_blocker_entry(b)) for b in blockers]
    blockers_payload = task028_tuple_payload(blocker_child_frames)
    fields: list[tuple[str, bytes, bytes]] = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("profile_id", KIND_STRING, profile_id.encode("utf-8")),
        ("request_hash", KIND_STRING, (request_hash or "").encode("utf-8")),
        (
            "task025_hydraulic_authority_hash",
            KIND_STRING,
            (task025_hydraulic_authority_hash or "").encode("utf-8"),
        ),
        ("task025_result_hash", KIND_STRING, (task025_result_hash or "").encode("utf-8")),
        ("task026_result_hash", KIND_STRING, (task026_result_hash or "").encode("utf-8")),
        ("property_snapshot_hash", KIND_STRING, (property_snapshot_hash or "").encode("utf-8")),
        (
            "raw_request_projection",
            KIND_NONE if raw_request_projection is None else KIND_RAW_PROJECTION,
            b""
            if raw_request_projection is None
            else _encode_raw_projection_canonical(raw_request_projection),
        ),
        (
            "raw_upstream_blocked_projection",
            KIND_NONE if raw_upstream_blocked_projection is None else KIND_RAW_PROJECTION,
            b""
            if raw_upstream_blocked_projection is None
            else _encode_raw_projection_canonical(raw_upstream_blocked_projection),
        ),
        ("warnings", KIND_TUPLE, _encode_string_tuple(warnings)),
        ("blockers", KIND_TUPLE, blockers_payload),
        ("deferred_capabilities", KIND_TUPLE, _encode_string_tuple(deferred_capabilities)),
        (
            "provenance",
            KIND_NONE if provenance is None else KIND_RECORD,
            b"" if provenance is None else _encode_provenance_canonical(provenance),
        ),
    ]
    framed = frame_record(BLOCKED_RESULT_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


def canonicalize_raw_boundary_blocked_hash(
    raw_request_projection: Any,
    blockers: tuple[Any, ...],
    warnings: tuple[str, ...],
    deferred_capabilities: tuple[str, ...],
    schema_version: str,
    implementation_software_version: str,
) -> str:
    """§16 — Canonical raw boundary blocked hash (6 fields)."""
    # Blockers: each child is a framed RECORD wrapping the blocker entry record
    blocker_child_frames = [frame_value(KIND_RECORD, _encode_blocker_entry(b)) for b in blockers]
    blockers_payload = task028_tuple_payload(blocker_child_frames)
    fields: list[tuple[str, bytes, bytes]] = [
        (
            "raw_request_projection",
            KIND_RAW_PROJECTION,
            _encode_raw_projection_canonical(raw_request_projection),
        ),
        ("blockers", KIND_TUPLE, blockers_payload),
        ("warnings", KIND_TUPLE, _encode_string_tuple(warnings)),
        ("deferred_capabilities", KIND_TUPLE, _encode_string_tuple(deferred_capabilities)),
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        (
            "implementation_software_version",
            KIND_STRING,
            implementation_software_version.encode("utf-8"),
        ),
    ]
    framed = frame_record(RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


__all__ = [
    "KIND_NONE",
    "KIND_STRING",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_INTEGER",
    "KIND_TUPLE",
    "KIND_RECORD",
    "KIND_RAW_PROJECTION",
    "task028_tuple_payload",
    "canonicalize_authority",
    "canonicalize_request_hash",
    "canonicalize_component_result",
    "canonicalize_success_result_hash",
    "canonicalize_blocked_result_hash",
    "canonicalize_raw_boundary_blocked_hash",
    "_canonical_component_result_record",
    "REQUEST_HASH_NAMESPACE",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_HASH_NAMESPACE",
    "RAW_PROJECTION_NAMESPACE",
    "PROVENANCE_NAMESPACE",
    "COMPONENT_RESULT_HASH_NAMESPACE",
    "AUTHORITY_HASH_NAMESPACE",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "TASK028_REQUEST_SCHEMA_VERSION",
    "TASK028_SUCCESS_RESULT_SCHEMA_VERSION",
    "TASK028_BLOCKED_RESULT_SCHEMA_VERSION",
    "TASK028_RAW_BOUNDARY_BLOCKED_SCHEMA_VERSION",
    "TASK028_AUTHORITY_SCHEMA_VERSION",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "TASK028_DEFERRED_CAPABILITIES_V1",
    "SUPPORTED_PROFILE_IDS",
    "TASK028_REQUEST_FIELDS",
    "_encode_string_tuple",
    "_encode_bytes_tuple",
    "_encode_blocker_entry",
    "_encode_raw_projection_canonical",
    "_encode_provenance_canonical",
]
