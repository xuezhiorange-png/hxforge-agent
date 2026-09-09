"""Deterministic TASK-167 canonical identity projections.

This module supplies TASK-167 domains and projections only.  The byte-level
framing primitives are the repository's TASK-025 implementation, imported
through the existing TASK-026 wrapper; no parallel framing algorithm is
introduced here.
"""

from __future__ import annotations

import enum
import uuid
from collections.abc import Mapping, Sequence
from dataclasses import fields, is_dataclass
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_side_thermal.canonical import (
    frame_record,
    frame_tuple,
    frame_value,
    sha256_hex_from_framed_bytes,
)

from .models import (
    ApplicabilityLedger,
    FIVScreen,
    NozzleGeometryAuthority,
    ScreeningPropertySnapshot,
    ScreeningRequirements,
    ScreenRecord,
    Task167BlockedResult,
    Task167RawBoundaryBlockedResult,
    Task167Request,
    Task167Result,
)

KIND_NONE = b"NONE"
KIND_BOOL = b"BOOL"
KIND_INT = b"INT"
KIND_DECIMAL = b"DECIMAL"
KIND_STRING = b"STRING"
KIND_ENUM = b"ENUM"
KIND_TUPLE = b"TUPLE"
KIND_RECORD = b"RECORD"

REQUEST_HASH_NAMESPACE = "task167.engineering-screening.request.v1"
RESULT_HASH_NAMESPACE = "task167.engineering-screening.result.v1"
BLOCKED_HASH_NAMESPACE = "task167.engineering-screening.typed-blocked.v1"
RAW_BLOCKED_HASH_NAMESPACE = "task167.engineering-screening.raw-boundary-blocked.v1"
PROVENANCE_HASH_NAMESPACE = "task167.engineering-screening.provenance.v1"

RESULT_ID_NAMESPACE = uuid.UUID("a1670000-0000-5000-8000-000000000167")
BLOCKED_ID_NAMESPACE = uuid.UUID("a1670000-0000-5000-8000-000000000168")
RAW_BLOCKED_ID_NAMESPACE = uuid.UUID("a1670000-0000-5000-8000-000000000169")
RESULT_ID_NAME_PREFIX = "task167-engineering-screening-result-v1::"
BLOCKED_ID_NAME_PREFIX = "task167-engineering-screening-blocked-v1::"
RAW_BLOCKED_ID_NAME_PREFIX = "task167-engineering-screening-raw-blocked-v1::"

SUCCESS_RESULT_FIELDS: tuple[str, ...] = tuple(
    name
    for name in (
        "schema_version",
        "task167_version",
        "implementation_software_version",
        "source_definition_id",
        "request_hash",
        "configuration_evidence",
        "task166_evidence",
        "tube_side_evidence",
        "screening_requirements_evidence",
        "screening_property_evidence",
        "nozzle_geometry_evidence",
        "velocity_screens",
        "erosion_screen",
        "fouling_cleanability_screen",
        "thermal_expansion_screen",
        "construction_family_suitability_screen",
        "fiv_screen",
        "aggregate_screening_status",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "applicability",
        "completeness",
        "provenance_semantic_inputs",
    )
)


def _string(value: str) -> bytes:
    return value.encode("utf-8", "strict")


def _enum_text(value: enum.Enum) -> str:
    raw = value.value
    if type(raw) is not str:
        raise ValueError("enum value must be exact str")
    return raw


def _payload(value: Any) -> tuple[bytes, bytes]:
    """Return a kind tag and payload for trusted canonical values."""
    if value is None:
        return KIND_NONE, b""
    if type(value) is bool:
        return KIND_BOOL, b"1" if value else b"0"
    if type(value) is int:
        return KIND_INT, str(value).encode("ascii")
    if type(value) is Decimal:
        if not value.is_finite():
            raise ValueError("non-finite Decimal")
        return KIND_DECIMAL, str(value).encode("ascii")
    if type(value) is str:
        return KIND_STRING, _string(value)
    if isinstance(value, enum.Enum):
        return KIND_ENUM, _string(_enum_text(value))
    if type(value) in (tuple, list):
        return KIND_TUPLE, frame_tuple([_value_bytes(item) for item in value])
    if isinstance(value, Mapping):
        items: list[bytes] = []
        keys: list[tuple[bytes, str]] = []
        for key in value:
            if type(key) is not str:
                raise ValueError("mapping keys must be exact str")
            key_bytes = _string(key)
            keys.append((key_bytes, key))
        for _key_bytes, key in sorted(keys, key=lambda item: item[0]):
            items.append(
                _record_bytes(
                    "task167.mapping.item.v1",
                    (
                        ("key", KIND_STRING, _string(key)),
                        ("value", *_payload(value[key])),
                    ),
                )
            )
        return KIND_RECORD, frame_tuple(items)
    if is_dataclass(value) and not isinstance(value, type):
        entries = []
        for item in fields(value):
            kind, payload = _payload(getattr(value, item.name))
            entries.append((item.name, kind, payload))
        return KIND_RECORD, _record_bytes(type(value).__qualname__, tuple(entries))
    raise ValueError(f"unsupported canonical value type {type(value).__name__}")


def _value_bytes(value: Any) -> bytes:
    kind, payload = _payload(value)
    return frame_value(kind, payload)


def _record_bytes(namespace: str, values: Sequence[tuple[str, bytes, bytes]]) -> bytes:
    return frame_record(namespace, tuple(values))


def _record_hash(namespace: str, values: Sequence[tuple[str, bytes, bytes]]) -> str:
    return sha256_hex_from_framed_bytes(_record_bytes(namespace, values))


def sha256_domain_hex(domain: str, value: Any) -> str:
    return _record_hash(
        domain,
        (("value", *_payload(value)),),
    )


def _pairs_payload(value: tuple[tuple[str, str], ...]) -> tuple[bytes, bytes]:
    return KIND_TUPLE, frame_tuple(
        [
            _record_bytes(
                "task167.key-value.v1",
                (("key", KIND_STRING, _string(key)), ("value", KIND_STRING, _string(item))),
            )
            for key, item in value
        ]
    )


def _identity_pairs(pairs: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(pairs, key=lambda item: (_string(item[0]), _string(item[1]))))


def configuration_projection(configuration: Any) -> tuple[tuple[str, Any], ...]:
    binding = configuration.authority_binding
    return (
        ("schema_version", configuration.schema_version),
        ("configuration_id", configuration.configuration_id),
        ("configuration_hash", configuration.configuration_hash),
        ("equipment_family", configuration.equipment_family),
        ("authority_mode", configuration.authority_mode),
        ("standard_claim_status", configuration.standard_claim_status),
        ("construction_family", configuration.construction_family),
        ("orientation", configuration.orientation),
        ("shell_pass_count", configuration.shell_pass_count),
        ("tube_pass_count", configuration.tube_pass_count),
        ("case_revision_id", configuration.case_authority.revision_id),
        ("case_payload_hash", configuration.case_authority.payload_hash),
        ("case_domain_snapshot_hash", configuration.case_authority.domain_snapshot_hash),
        ("binding_authority_mode", binding.authority_mode),
        ("standard_system_id", binding.standard_system_id),
        ("deferred_capabilities", configuration.deferred_capabilities),
    )


def task166_identity_projection(result: Any) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", result.schema_version),
        ("task166_version", result.task166_version),
        ("source_definition_id", result.source_definition_id),
        ("request_hash", result.request_hash),
        ("result_hash", result.result_hash),
        ("result_id", result.result_id),
        ("applicability", None if result.applicability is None else result.applicability.status),
        ("completeness", None if result.completeness is None else result.completeness.status),
        ("case_evidence", result.task020_evidence),
        ("flow_evidence", result.shell_side_flow_evidence),
    )


def tube_side_identity_projection(result: Any) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", result.schema_version),
        ("task026_version", result.task026_version),
        ("implementation_software_version", result.implementation_software_version),
        ("upstream_geometry_hash", result.upstream_geometry_hash),
        ("property_snapshot_hash", result.property_snapshot_hash),
        ("phase_assertion", result.phase_assertion),
        ("mass_flow_rate_kg_s", result.mass_flow_rate_kg_s),
        ("bulk_velocity_m_s", result.bulk_velocity_m_s),
        ("reynolds_number", result.reynolds_number),
        ("prandtl_number", result.prandtl_number),
        ("flow_regime", result.flow_regime),
        ("correlation_id", result.correlation_id),
        ("correlation_version", result.correlation_version),
        ("nusselt_number", result.nusselt_number),
        (
            "tube_side_heat_transfer_coefficient_w_m2_k",
            result.tube_side_heat_transfer_coefficient_w_m2_k,
        ),
        ("request_hash", result.request_hash),
        ("result_hash", result.result_hash),
        ("result_id", result.result_id),
        ("warnings", result.warnings),
        ("deferred_capabilities", result.deferred_capabilities),
    )


def requirements_projection(value: ScreeningRequirements) -> tuple[tuple[str, Any], ...]:
    return tuple((item.name, getattr(value, item.name)) for item in fields(value))


def property_snapshot_projection(value: ScreeningPropertySnapshot) -> tuple[tuple[str, Any], ...]:
    return tuple((item.name, getattr(value, item.name)) for item in fields(value))


def nozzle_projection(value: NozzleGeometryAuthority | None) -> tuple[tuple[str, Any], ...] | None:
    return (
        None
        if value is None
        else tuple((item.name, getattr(value, item.name)) for item in fields(value))
    )


def screen_projection(value: ScreenRecord | None) -> Any:
    if value is None:
        return None
    return tuple((item.name, getattr(value, item.name)) for item in fields(value))


def fiv_projection(value: FIVScreen | None) -> Any:
    if value is None:
        return None
    return tuple((item.name, getattr(value, item.name)) for item in fields(value))


def applicability_projection(value: ApplicabilityLedger | None) -> Any:
    if value is None:
        return None
    return (
        (
            "checks",
            tuple((item.check_id, item.status, item.evidence_refs) for item in value.checks),
        ),
        ("status", value.status),
    )


def request_projection(request: Task167Request) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", request.schema_version),
        ("task167_version", request.task167_version),
        ("source_definition_id", request.source_definition_id),
        ("task020_configuration", configuration_projection(request.task020_configuration)),
        ("task166_result", task166_identity_projection(request.task166_result)),
        ("tube_side_result", tube_side_identity_projection(request.tube_side_result)),
        ("screening_requirements", requirements_projection(request.screening_requirements)),
        (
            "screening_property_snapshot",
            property_snapshot_projection(request.screening_property_snapshot),
        ),
        ("nozzle_geometry", nozzle_projection(request.nozzle_geometry)),
        ("approved_rule_pack_authority", request.approved_rule_pack_authority),
        ("request_metadata", _identity_pairs(request.request_metadata)),
    )


def request_hash(request: Task167Request) -> str:
    return sha256_domain_hex(REQUEST_HASH_NAMESPACE, request_projection(request))


def result_projection(result: Task167Result) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", result.schema_version),
        ("task167_version", result.task167_version),
        ("implementation_software_version", result.implementation_software_version),
        ("source_definition_id", result.source_definition_id),
        ("request_hash", result.request_hash),
        ("configuration_evidence", result.configuration_evidence),
        ("task166_evidence", result.task166_evidence),
        ("tube_side_evidence", result.tube_side_evidence),
        ("screening_requirements_evidence", result.screening_requirements_evidence),
        ("screening_property_evidence", result.screening_property_evidence),
        ("nozzle_geometry_evidence", result.nozzle_geometry_evidence),
        ("velocity_screens", result.velocity_screens),
        ("erosion_screen", screen_projection(result.erosion_screen)),
        ("fouling_cleanability_screen", screen_projection(result.fouling_cleanability_screen)),
        ("thermal_expansion_screen", screen_projection(result.thermal_expansion_screen)),
        (
            "construction_family_suitability_screen",
            screen_projection(result.construction_family_suitability_screen),
        ),
        ("fiv_screen", fiv_projection(result.fiv_screen)),
        ("aggregate_screening_status", result.aggregate_screening_status),
        ("warnings", result.warnings),
        ("blockers", result.blockers),
        ("deferred_capabilities", result.deferred_capabilities),
        ("applicability", applicability_projection(result.applicability)),
        (
            "completeness",
            None
            if result.completeness is None
            else (
                result.completeness.required_fields,
                result.completeness.present_fields,
                result.completeness.status,
            ),
        ),
        ("provenance_semantic_inputs", result.provenance_semantic_inputs),
    )


def result_hash(result: Task167Result) -> str:
    return sha256_domain_hex(RESULT_HASH_NAMESPACE, result_projection(result))


def result_id(hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + hash_value))


def blocked_projection(result: Task167BlockedResult) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", result.schema_version),
        ("task167_version", result.task167_version),
        ("implementation_software_version", result.implementation_software_version),
        ("failure_stage", result.failure_stage),
        ("request_hash", result.request_hash),
        ("blockers", result.blockers),
        ("warnings", result.warnings),
        ("deferred_capabilities", result.deferred_capabilities),
    )


def blocked_hash(result: Task167BlockedResult) -> str:
    return sha256_domain_hex(BLOCKED_HASH_NAMESPACE, blocked_projection(result))


def blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(BLOCKED_ID_NAMESPACE, BLOCKED_ID_NAME_PREFIX + hash_value))


def raw_blocked_projection(result: Task167RawBoundaryBlockedResult) -> tuple[tuple[str, Any], ...]:
    return (
        ("schema_version", result.schema_version),
        ("task167_version", result.task167_version),
        ("implementation_software_version", result.implementation_software_version),
        ("raw_request_projection_hash", result.raw_request_projection_hash),
        ("blockers", result.blockers),
        ("warnings", result.warnings),
        ("deferred_capabilities", result.deferred_capabilities),
    )


def raw_blocked_hash(result: Task167RawBoundaryBlockedResult) -> str:
    return sha256_domain_hex(RAW_BLOCKED_HASH_NAMESPACE, raw_blocked_projection(result))


def raw_blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(RAW_BLOCKED_ID_NAMESPACE, RAW_BLOCKED_ID_NAME_PREFIX + hash_value))


def provenance_hash(value: Any) -> str:
    return sha256_domain_hex(PROVENANCE_HASH_NAMESPACE, value)


__all__ = [
    "BLOCKED_ID_NAMESPACE",
    "BLOCKED_ID_NAME_PREFIX",
    "BLOCKED_HASH_NAMESPACE",
    "KIND_BOOL",
    "KIND_DECIMAL",
    "KIND_ENUM",
    "KIND_INT",
    "KIND_NONE",
    "KIND_RECORD",
    "KIND_STRING",
    "KIND_TUPLE",
    "PROVENANCE_HASH_NAMESPACE",
    "RAW_BLOCKED_ID_NAMESPACE",
    "RAW_BLOCKED_ID_NAME_PREFIX",
    "RAW_BLOCKED_HASH_NAMESPACE",
    "REQUEST_HASH_NAMESPACE",
    "RESULT_HASH_NAMESPACE",
    "RESULT_ID_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "SUCCESS_RESULT_FIELDS",
    "blocked_hash",
    "blocked_id",
    "configuration_projection",
    "fiv_projection",
    "frame_record",
    "frame_tuple",
    "frame_value",
    "nozzle_projection",
    "provenance_hash",
    "property_snapshot_projection",
    "raw_blocked_hash",
    "raw_blocked_id",
    "request_hash",
    "request_projection",
    "result_hash",
    "result_id",
    "result_projection",
    "screen_projection",
    "sha256_domain_hex",
    "task166_identity_projection",
    "tube_side_identity_projection",
]
