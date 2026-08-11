"""TASK-028 canonical framing: authority, request hash, result hash, kind constants, tuple payload.

§24 — Canonical serialization.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Final

from hexagent.exchangers.shell_tube.tube_side.canonical import (
    _u32_be,
    _u64_be,
    frame_record,
    frame_value,
    sha256_hex_from_framed_bytes,
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
    return task028_tuple_payload(
        [frame_value(KIND_STRING, item.encode("utf-8")) for item in items]
    )


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
    if hasattr(projection, "projection_kind") and hasattr(projection, "canonical_bytes_hex"):
        fields = [
            ("projection_kind", KIND_STRING, projection.projection_kind.encode("utf-8")),
            ("canonical_bytes_hex", KIND_STRING, projection.canonical_bytes_hex.encode("utf-8")),
        ]
    else:
        fields = [
            ("projection_kind", KIND_STRING, b"unknown"),
            ("canonical_bytes_hex", KIND_STRING, str(projection).encode("utf-8")),
        ]
    return frame_record(RAW_PROJECTION_NAMESPACE, fields)


def _encode_provenance_canonical(provenance: Any) -> bytes:
    """Encode provenance as frozen canonical nested record."""
    if provenance is None:
        return b""
    if hasattr(provenance, "task_id"):
        fields = [
            ("task_id", KIND_STRING, provenance.task_id.encode("utf-8")),
            ("design_contract_path", KIND_STRING, provenance.design_contract_path.encode("utf-8")),
            (
                "implementation_software_version",
                KIND_STRING,
                provenance.implementation_software_version.encode("utf-8"),
            ),
            ("input_evidence_refs", KIND_TUPLE, _encode_string_tuple(provenance.input_evidence_refs)),
            (
                "upstream_identity_hashes",
                KIND_TUPLE,
                _encode_string_tuple(provenance.upstream_identity_hashes),
            ),
        ]
    else:
        fields = [
            ("task_id", KIND_STRING, b"unknown"),
            ("design_contract_path", KIND_STRING, b"unknown"),
            ("implementation_software_version", KIND_STRING, b"unknown"),
            ("input_evidence_refs", KIND_TUPLE, _encode_string_tuple(())),
            ("upstream_identity_hashes", KIND_TUPLE, _encode_string_tuple(())),
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
    loss_coefficient: str,
    loss_coefficient_convention: str,
    reference_flow_area_m2: str,
    multiplicity: int,
    geometry_evidence_refs: tuple[str, ...],
    coefficient_source_id: str,
    coefficient_source_version: str,
    coefficient_source_location: str,
    coefficient_permission_status: str,
) -> tuple[bytes, str]:
    """§24 — Canonical 16-field authority framing → (framed_bytes, sha256_hex).

    Fields 1–16 of the 17-field authority (excludes authority_hash itself).
    """
    fields = [
        ("schema_version", KIND_STRING, schema_version.encode("utf-8")),
        ("component_id", KIND_STRING, component_id.encode("utf-8")),
        ("component_type", KIND_ENUM, component_type.encode("ascii")),
        ("path_sequence_index", KIND_INTEGER, str(path_sequence_index).encode("utf-8")),
        ("upstream_reference_plane", KIND_STRING, upstream_reference_plane.encode("utf-8")),
        ("downstream_reference_plane", KIND_STRING, downstream_reference_plane.encode("utf-8")),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        ("loss_coefficient", KIND_DECIMAL, loss_coefficient.encode("utf-8")),
        ("loss_coefficient_convention", KIND_ENUM, loss_coefficient_convention.encode("ascii")),
        ("reference_flow_area_m2", KIND_DECIMAL, reference_flow_area_m2.encode("utf-8")),
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
        ("component_authority_hashes", KIND_TUPLE, _encode_string_tuple(component_authority_hashes)),
    ]
    framed = frame_record(REQUEST_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


def canonicalize_component_result(
    component_id: str,
    component_type: str,
    path_sequence_index: int,
    upstream_reference_plane: str,
    downstream_reference_plane: str,
    flow_direction_assertion: str,
    authority_hash: str,
    reference_flow_area_m2: str,
    reference_velocity_m_s: str,
    loss_coefficient: str,
    loss_coefficient_convention: str,
    multiplicity: int,
    single_occurrence_irreversible_pressure_loss_pa: str,
    component_irreversible_pressure_loss_pa: str,
) -> str:
    """§24 — Canonical component result hash (13 fields, excludes component_result_hash)."""
    fields = [
        ("component_id", KIND_STRING, component_id.encode("utf-8")),
        ("component_type", KIND_ENUM, component_type.encode("ascii")),
        ("path_sequence_index", KIND_INTEGER, str(path_sequence_index).encode("utf-8")),
        ("upstream_reference_plane", KIND_STRING, upstream_reference_plane.encode("utf-8")),
        ("downstream_reference_plane", KIND_STRING, downstream_reference_plane.encode("utf-8")),
        ("flow_direction_assertion", KIND_ENUM, flow_direction_assertion.encode("ascii")),
        ("authority_hash", KIND_STRING, authority_hash.encode("utf-8")),
        ("reference_flow_area_m2", KIND_DECIMAL, reference_flow_area_m2.encode("utf-8")),
        ("reference_velocity_m_s", KIND_DECIMAL, reference_velocity_m_s.encode("utf-8")),
        ("loss_coefficient", KIND_DECIMAL, loss_coefficient.encode("utf-8")),
        ("loss_coefficient_convention", KIND_ENUM, loss_coefficient_convention.encode("ascii")),
        ("multiplicity", KIND_INTEGER, str(multiplicity).encode("utf-8")),
        (
            "single_occurrence_irreversible_pressure_loss_pa",
            KIND_DECIMAL,
            single_occurrence_irreversible_pressure_loss_pa.encode("utf-8"),
        ),
        (
            "component_irreversible_pressure_loss_pa",
            KIND_DECIMAL,
            component_irreversible_pressure_loss_pa.encode("utf-8"),
        ),
    ]
    framed = frame_record(COMPONENT_RESULT_HASH_NAMESPACE, fields)
    return sha256_hex_from_framed_bytes(framed)


def canonicalize_success_result_hash(
    schema_version: str,
    profile_id: str,
    request_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    component_result_hashes: tuple[str, ...],
    warnings: tuple[str, ...],
    blockers: tuple[Any, ...],
    deferred_capabilities: tuple[str, ...],
    provenance: Any,
) -> str:
    """§15 — Canonical success result hash (self-excludes result_hash, result_id).

    14-field success result → hash projection excludes result_hash and result_id.
    """
    # Component results: each child is a framed RECORD wrapping the canonical hash bytes
    component_child_frames = (
        [frame_value(KIND_RECORD, bytes.fromhex(h)) for h in component_result_hashes]
        if component_result_hashes
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
    "SUPPORTED_PROFILE_IDS",
    "TASK028_REQUEST_FIELDS",
    "_encode_string_tuple",
    "_encode_bytes_tuple",
    "_encode_blocker_entry",
    "_encode_raw_projection_canonical",
    "_encode_provenance_canonical",
]
