"""TASK-029 authority identity: member, exclusion, composition, and request hash.

I03: member, exclusion, composition canonicalize + hash.
Slice 7A: request hash semantic projection primitive.
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from enum import StrEnum

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.canonical import (
    COMPOSITION_AUTHORITY_HASH_NAMESPACE,
    EXCLUSION_AUTHORITY_HASH_NAMESPACE,
    KIND_ENUM,
    KIND_INTEGER,
    KIND_RECORD,
    KIND_STRING,
    KIND_TUPLE,
    MEMBER_AUTHORITY_HASH_NAMESPACE,
    REQUEST_HASH_KIND_TAGS,
    REQUEST_HASH_NAMESPACE,
    REQUEST_HASH_SEMANTIC_FIELDS,
    frame_record,
    frame_value,
    sort_evidence_refs,
    task029_tuple_payload,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    TubeSidePressurePathCompositionAuthority,
    TubeSidePressurePathExclusionAuthority,
    TubeSidePressurePathMemberAuthority,
)


def _sha256_hex(framed_bytes: bytes) -> str:
    return hashlib.sha256(framed_bytes).hexdigest()


def _encode_integer_lexical(value: int) -> bytes:
    if value < 0:
        raise ValueError("INTEGER must be non-negative")
    if value == 0:
        return b"0"
    text = str(value)
    if len(text) > 1 and text[0] == "0":
        raise ValueError("INTEGER must not use leading zeros")
    return text.encode("ascii")


def _enum_value(value: StrEnum | str) -> str:
    if isinstance(value, StrEnum):
        return value.value
    return value


def _encode_string_tuple(refs: tuple[str, ...]) -> bytes:
    sorted_refs = sort_evidence_refs(refs)
    child_frames = [frame_value(KIND_STRING, ref.encode("utf-8")) for ref in sorted_refs]
    return task029_tuple_payload(child_frames)


def _wrap_record_child(record_bytes: bytes) -> bytes:
    return frame_value(KIND_RECORD, record_bytes)


def _member_authority_field_values(
    authority: TubeSidePressurePathMemberAuthority,
    *,
    include_authority_hash: bool,
) -> list[tuple[str, bytes, bytes]]:
    fields: list[tuple[str, bytes, bytes]] = [
        ("schema_version", KIND_STRING, authority.schema_version.encode("utf-8")),
        ("member_id", KIND_STRING, authority.member_id.encode("utf-8")),
        (
            "global_path_sequence_index",
            KIND_INTEGER,
            _encode_integer_lexical(authority.global_path_sequence_index),
        ),
        ("producer_task", KIND_ENUM, _enum_value(authority.producer_task).encode("ascii")),
        (
            "producer_member_kind",
            KIND_ENUM,
            _enum_value(authority.producer_member_kind).encode("ascii"),
        ),
        (
            "producer_component_identity",
            KIND_STRING,
            authority.producer_component_identity.encode("utf-8"),
        ),
        (
            "expected_producer_component_type",
            KIND_ENUM,
            authority.expected_producer_component_type.encode("ascii"),
        ),
        (
            "expected_producer_authority_hash",
            KIND_STRING,
            authority.expected_producer_authority_hash.encode("utf-8"),
        ),
        (
            "expected_upstream_reference_plane",
            KIND_STRING,
            authority.expected_upstream_reference_plane.encode("utf-8"),
        ),
        (
            "expected_downstream_reference_plane",
            KIND_STRING,
            authority.expected_downstream_reference_plane.encode("utf-8"),
        ),
        (
            "expected_multiplicity",
            KIND_INTEGER,
            _encode_integer_lexical(authority.expected_multiplicity),
        ),
        (
            "geometry_evidence_refs",
            KIND_TUPLE,
            _encode_string_tuple(authority.geometry_evidence_refs),
        ),
    ]
    if include_authority_hash:
        fields.append(
            (
                "member_authority_hash",
                KIND_STRING,
                authority.member_authority_hash.encode("utf-8"),
            )
        )
    return fields


def canonicalize_member_authority(authority: TubeSidePressurePathMemberAuthority) -> bytes:
    """Canonicalize member authority hash projection (fields 1–12 only)."""
    fields = _member_authority_field_values(authority, include_authority_hash=False)
    return frame_record(MEMBER_AUTHORITY_HASH_NAMESPACE, fields)


def compute_member_authority_hash(authority: TubeSidePressurePathMemberAuthority) -> str:
    """Compute lowercase SHA-256 hex for member authority fields 1–12."""
    return _sha256_hex(canonicalize_member_authority(authority))


def _canonicalize_member_authority_full_record(
    authority: TubeSidePressurePathMemberAuthority,
) -> bytes:
    """Canonicalize full 13-field member authority record for composition nesting."""
    fields = _member_authority_field_values(authority, include_authority_hash=True)
    return frame_record(MEMBER_AUTHORITY_HASH_NAMESPACE, fields)


def _exclusion_authority_field_values(
    authority: TubeSidePressurePathExclusionAuthority,
    *,
    include_authority_hash: bool,
) -> list[tuple[str, bytes, bytes]]:
    fields: list[tuple[str, bytes, bytes]] = [
        ("schema_version", KIND_STRING, authority.schema_version.encode("utf-8")),
        ("exclusion_id", KIND_STRING, authority.exclusion_id.encode("utf-8")),
        (
            "excluded_item_identity",
            KIND_STRING,
            authority.excluded_item_identity.encode("utf-8"),
        ),
        (
            "exclusion_reason",
            KIND_ENUM,
            _enum_value(authority.exclusion_reason).encode("ascii"),
        ),
        ("evidence_refs", KIND_TUPLE, _encode_string_tuple(authority.evidence_refs)),
    ]
    if include_authority_hash:
        fields.append(
            (
                "exclusion_authority_hash",
                KIND_STRING,
                authority.exclusion_authority_hash.encode("utf-8"),
            )
        )
    return fields


def canonicalize_exclusion_authority(
    authority: TubeSidePressurePathExclusionAuthority,
) -> bytes:
    """Canonicalize exclusion authority hash projection (fields 1–5 only)."""
    fields = _exclusion_authority_field_values(authority, include_authority_hash=False)
    return frame_record(EXCLUSION_AUTHORITY_HASH_NAMESPACE, fields)


def compute_exclusion_authority_hash(
    authority: TubeSidePressurePathExclusionAuthority,
) -> str:
    """Compute lowercase SHA-256 hex for exclusion authority fields 1–5."""
    return _sha256_hex(canonicalize_exclusion_authority(authority))


def _canonicalize_exclusion_authority_full_record(
    authority: TubeSidePressurePathExclusionAuthority,
) -> bytes:
    """Canonicalize full 6-field exclusion authority record for composition nesting."""
    fields = _exclusion_authority_field_values(authority, include_authority_hash=True)
    return frame_record(EXCLUSION_AUTHORITY_HASH_NAMESPACE, fields)


def _encode_member_authorities_tuple(
    member_authorities: Sequence[TubeSidePressurePathMemberAuthority],
) -> bytes:
    sorted_members = sorted(
        member_authorities,
        key=lambda member: member.global_path_sequence_index,
    )
    child_frames = [
        _wrap_record_child(_canonicalize_member_authority_full_record(member))
        for member in sorted_members
    ]
    return task029_tuple_payload(child_frames)


def _encode_exclusion_authorities_tuple(
    exclusion_authorities: Sequence[TubeSidePressurePathExclusionAuthority],
) -> bytes:
    sorted_exclusions = sorted(
        exclusion_authorities,
        key=lambda exclusion: exclusion.exclusion_id.encode("utf-8"),
    )
    child_frames = [
        _wrap_record_child(_canonicalize_exclusion_authority_full_record(exclusion))
        for exclusion in sorted_exclusions
    ]
    return task029_tuple_payload(child_frames)


def canonicalize_composition_authority(
    authority: TubeSidePressurePathCompositionAuthority,
) -> bytes:
    """Canonicalize composition authority hash projection (fields 1–8 only)."""
    fields: list[tuple[str, bytes, bytes]] = [
        ("schema_version", KIND_STRING, authority.schema_version.encode("utf-8")),
        ("modeled_path_id", KIND_STRING, authority.modeled_path_id.encode("utf-8")),
        (
            "flow_direction_assertion",
            KIND_ENUM,
            _enum_value(authority.flow_direction_assertion).encode("ascii"),
        ),
        (
            "start_reference_plane",
            KIND_STRING,
            authority.start_reference_plane.encode("utf-8"),
        ),
        (
            "end_reference_plane",
            KIND_STRING,
            authority.end_reference_plane.encode("utf-8"),
        ),
        (
            "member_authorities",
            KIND_TUPLE,
            _encode_member_authorities_tuple(authority.member_authorities),
        ),
        (
            "exclusion_authorities",
            KIND_TUPLE,
            _encode_exclusion_authorities_tuple(authority.exclusion_authorities),
        ),
        (
            "geometry_evidence_refs",
            KIND_TUPLE,
            _encode_string_tuple(authority.geometry_evidence_refs),
        ),
    ]
    return frame_record(COMPOSITION_AUTHORITY_HASH_NAMESPACE, fields)


def compute_composition_authority_hash(
    authority: TubeSidePressurePathCompositionAuthority,
) -> str:
    """Compute lowercase SHA-256 hex for composition authority fields 1–8."""
    return _sha256_hex(canonicalize_composition_authority(authority))


_REQUEST_HASH_KIND_TAG_BYTES: dict[str, bytes] = {
    "STRING": KIND_STRING,
}


def _request_hash_kind_tag_bytes(kind_tag: str) -> bytes:
    try:
        return _REQUEST_HASH_KIND_TAG_BYTES[kind_tag]
    except KeyError as exc:
        raise ValueError(f"unsupported request hash kind tag: {kind_tag!r}") from exc


def canonicalize_request_projection(
    schema_version: str,
    profile_id: str,
    task027_result_hash: str,
    task028_result_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    composition_authority_hash: str,
) -> bytes:
    """Canonicalize request hash semantic projection (9 STRING fields)."""
    values_by_field: dict[str, str] = {
        "schema_version": schema_version,
        "profile_id": profile_id,
        "task027_result_hash": task027_result_hash,
        "task028_result_hash": task028_result_hash,
        "task025_hydraulic_authority_hash": task025_hydraulic_authority_hash,
        "task025_result_hash": task025_result_hash,
        "task026_result_hash": task026_result_hash,
        "property_snapshot_hash": property_snapshot_hash,
        "composition_authority_hash": composition_authority_hash,
    }
    fields: list[tuple[str, bytes, bytes]] = []
    for field_name, kind_tag in zip(
        REQUEST_HASH_SEMANTIC_FIELDS,
        REQUEST_HASH_KIND_TAGS,
        strict=True,
    ):
        fields.append(
            (
                field_name,
                _request_hash_kind_tag_bytes(kind_tag),
                values_by_field[field_name].encode("utf-8"),
            )
        )
    return frame_record(REQUEST_HASH_NAMESPACE, fields)


def compute_request_hash(
    schema_version: str,
    profile_id: str,
    task027_result_hash: str,
    task028_result_hash: str,
    task025_hydraulic_authority_hash: str,
    task025_result_hash: str,
    task026_result_hash: str,
    property_snapshot_hash: str,
    composition_authority_hash: str,
) -> str:
    """Compute lowercase SHA-256 hex for the 9-field request hash projection."""
    return _sha256_hex(
        canonicalize_request_projection(
            schema_version=schema_version,
            profile_id=profile_id,
            task027_result_hash=task027_result_hash,
            task028_result_hash=task028_result_hash,
            task025_hydraulic_authority_hash=task025_hydraulic_authority_hash,
            task025_result_hash=task025_result_hash,
            task026_result_hash=task026_result_hash,
            property_snapshot_hash=property_snapshot_hash,
            composition_authority_hash=composition_authority_hash,
        )
    )


__all__ = [
    "canonicalize_member_authority",
    "compute_member_authority_hash",
    "canonicalize_exclusion_authority",
    "compute_exclusion_authority_hash",
    "canonicalize_composition_authority",
    "compute_composition_authority_hash",
    "canonicalize_request_projection",
    "compute_request_hash",
]
