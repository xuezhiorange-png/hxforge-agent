"""Canonical projections, hashes, and UUID identity for TASK-032."""

from __future__ import annotations

import enum
import uuid
from decimal import Decimal
from typing import Any

from hexagent.exchangers.shell_tube.tube_layout.canonical import (
    FrozenJsonArray,
    FrozenJsonObject,
    canonical_json,
    canonical_raw_json_or_none,
    internal_frozen_to_primitive,
    sha256_hex,
)

from .engineering_authority_snapshot import (
    ENGINEERING_AUTHORITY_HASH,
    ENGINEERING_AUTHORITY_ID,
)
from .models import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    DESIGN_CONTRACT_PATH,
    IMPLEMENTATION_SOFTWARE_VERSION,
    MASS_FLOW_AUTHORITY_FIELDS,
    PROFILE_ID,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SUCCESS_RESULT_FIELDS,
    BlockerEntry,
    ShellSideFlowState,
    ShellSideFlowStateRequest,
    ShellSideMassFlowAuthority,
    Task031GeometryBinding,
    Task031ResultBinding,
    WarningEntry,
)
from .raw_projection import FrozenRawProjection, projection_primitive

REQUEST_HASH_NAMESPACE = "task032.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE = "task032.success-result.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE = "task032.blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE = "task032.raw-boundary-blocked-result.v1"
PROVENANCE_NAMESPACE = "task032.provenance.v1"
SHELL_SIDE_MASS_FLOW_AUTHORITY_NAMESPACE = "task032.shell-side-mass-flow-authority.v1"
RESULT_ID_NAMESPACE = uuid.UUID("96ab5cf6-204d-547a-9d27-8a5eff46f997")
RESULT_ID_NAME_PREFIX = "task032-result-v1::"

SUCCESS_RESULT_HASH_FIELDS: tuple[str, ...] = tuple(
    field for field in SUCCESS_RESULT_FIELDS if field not in {"result_hash", "result_id"}
)
TYPED_BLOCKED_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "request_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)
RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "raw_request_projection",
    "blockers",
    "warnings",
    "deferred_capabilities",
)
PROVENANCE_FIELDS: tuple[str, ...] = (
    "task_id",
    "design_contract_path",
    "implementation_software_version",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "engineering_authority_id",
    "engineering_authority_hash",
    "formula_ids",
    "source_ids",
    "flow_model",
    "phase_region",
    "rheology_model",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "warnings",
    "deferred_capabilities",
    "evidence_refs",
    "engineering_source_formula_freeze_comment_id",
    "source_definition_issue",
    "provenance_hash",
)
PROVENANCE_HASH_FIELDS: tuple[str, ...] = tuple(
    field for field in PROVENANCE_FIELDS if field != "provenance_hash"
)


def primitive(value: Any) -> Any:
    if isinstance(value, (FrozenJsonArray, FrozenJsonObject)):
        return internal_frozen_to_primitive(value)
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, tuple):
        return [primitive(item) for item in value]
    if isinstance(value, list):
        return [primitive(item) for item in value]
    if isinstance(value, dict):
        return {str(key): primitive(item) for key, item in value.items()}
    return value


def _hash_projection(namespace: str, projection: Any) -> str:
    return sha256_hex([namespace, primitive(projection)])


def _message_primitive(entry: BlockerEntry | WarningEntry) -> dict[str, Any]:
    if isinstance(entry, BlockerEntry):
        return {
            "code": entry.code,
            "severity": entry.severity,
            "stage": entry.stage,
            "field_path": entry.field_path,
            "message_key": entry.message_key,
            "payload": [[key, value] for key, value in entry.payload],
            "evidence_refs": list(entry.evidence_refs),
        }
    return {
        "code": entry.code,
        "severity": entry.severity,
        "prerequisite_stage": entry.prerequisite_stage,
        "field_path": entry.field_path,
        "message_key": entry.message_key,
        "evidence_refs": list(entry.evidence_refs),
    }


def message_to_primitive(entry: BlockerEntry | WarningEntry) -> dict[str, Any]:
    return _message_primitive(entry)


def _task031_geometry_projection(geometry: Task031GeometryBinding) -> list[Any]:
    return [
        geometry.schema_version,
        geometry.geometry_id,
        geometry.geometry_hash,
        geometry.request_hash,
        geometry.task020_configuration_id,
        geometry.task020_configuration_hash,
        geometry.task021_layout_id,
        geometry.task021_layout_hash,
        geometry.task022_geometry_id,
        geometry.task022_geometry_hash,
        geometry.task024_geometry_id,
        geometry.task024_geometry_hash,
        geometry.engineering_authority_id,
        geometry.engineering_authority_hash,
        geometry.formula_a_id,
        geometry.formula_b_id,
        geometry.pattern_family,
        geometry.flow_region_identity,
        geometry.central_inter_baffle_spacing_m,
        geometry.central_crossflow_flow_area_m2,
        geometry.shell_side_equivalent_hydraulic_diameter_m,
        primitive(geometry.warnings),
        primitive(geometry.blockers),
        list(geometry.deferred_capabilities),
        primitive(geometry.provenance),
    ]


def task031_result_projection(result: Task031ResultBinding) -> list[Any]:
    return [
        result.status,
        None if result.geometry is None else _task031_geometry_projection(result.geometry),
        primitive(result.warnings),
        primitive(result.blockers),
        list(result.deferred_capabilities),
        result.blocked_result_hash,
    ]


def property_snapshot_projection(snapshot: Any) -> list[Any]:
    phase = (
        snapshot.phase_region.value
        if isinstance(snapshot.phase_region, enum.Enum)
        else snapshot.phase_region
    )
    return [
        str(snapshot.density_kg_m3),
        str(snapshot.dynamic_viscosity_pa_s),
        str(snapshot.thermal_conductivity_w_m_k),
        str(snapshot.specific_heat_capacity_j_kg_k),
        str(snapshot.bulk_temperature_k),
        str(snapshot.bulk_pressure_pa),
        phase,
        snapshot.property_source_id,
        snapshot.property_source_version,
        snapshot.property_snapshot_hash,
    ]


def mass_flow_authority_projection(
    authority: ShellSideMassFlowAuthority,
    *,
    include_hash: bool = True,
) -> list[Any]:
    values: list[Any] = [
        authority.schema_version,
        authority.authority_profile_id,
        authority.shell_side_case_id,
        authority.shell_side_stream_id,
        authority.shell_side_fluid_id,
        authority.rheology_model,
        authority.task020_configuration_id,
        authority.task020_configuration_hash,
        authority.task031_geometry_id,
        authority.task031_geometry_hash,
        authority.property_snapshot_hash,
        authority.property_state_role,
        str(authority.mass_flow_rate_kg_s),
        authority.mass_flow_sign_convention,
        authority.authority_source_id,
        authority.authority_source_version,
        sorted(authority.evidence_refs),
    ]
    if include_hash:
        values.append(authority.authority_hash)
    return values


def mass_flow_authority_hash(authority: ShellSideMassFlowAuthority) -> str:
    return _hash_projection(
        SHELL_SIDE_MASS_FLOW_AUTHORITY_NAMESPACE,
        mass_flow_authority_projection(authority, include_hash=False),
    )


def request_canonical_projection(request: ShellSideFlowStateRequest) -> list[Any]:
    return [
        request.schema_version,
        request.profile_id,
        task031_result_projection(request.task031_result),
        request.property_snapshot_hash,
        property_snapshot_projection(request.property_snapshot),
        mass_flow_authority_projection(request.mass_flow_authority),
        list(request.evidence_refs),
    ]


def request_hash(request: ShellSideFlowStateRequest) -> str:
    return _hash_projection(REQUEST_HASH_NAMESPACE, request_canonical_projection(request))


def provenance_prehash_projection(provenance: Any) -> list[Any]:
    mapping = dict(provenance) if not isinstance(provenance, dict) else provenance
    return [primitive(mapping[field]) for field in PROVENANCE_HASH_FIELDS]


def final_provenance_tuple(prehash: dict[str, Any]) -> tuple[tuple[str, Any], ...]:
    prehash_projection = [prehash[field] for field in PROVENANCE_HASH_FIELDS]
    provenance_hash = _hash_projection(PROVENANCE_NAMESPACE, prehash_projection)
    complete = {**prehash, "provenance_hash": provenance_hash}
    return tuple((field, primitive(complete[field])) for field in PROVENANCE_FIELDS)


def success_result_canonical_projection(result: ShellSideFlowState) -> list[Any]:
    values: dict[str, Any] = {
        "schema_version": result.schema_version,
        "profile_id": result.profile_id,
        "implementation_software_version": result.implementation_software_version,
        "shell_side_case_id": result.shell_side_case_id,
        "shell_side_stream_id": result.shell_side_stream_id,
        "shell_side_fluid_id": result.shell_side_fluid_id,
        "task020_configuration_id": result.task020_configuration_id,
        "task020_configuration_hash": result.task020_configuration_hash,
        "task031_geometry_id": result.task031_geometry_id,
        "task031_geometry_hash": result.task031_geometry_hash,
        "property_snapshot_hash": result.property_snapshot_hash,
        "mass_flow_authority_hash": result.mass_flow_authority_hash,
        "engineering_authority_id": result.engineering_authority_id,
        "engineering_authority_hash": result.engineering_authority_hash,
        "flow_model": result.flow_model,
        "phase_region": result.phase_region,
        "rheology_model": result.rheology_model,
        "shell_side_mass_flow_rate_kg_s": str(result.shell_side_mass_flow_rate_kg_s),
        "shell_side_mass_velocity_kg_m2_s": str(result.shell_side_mass_velocity_kg_m2_s),
        "shell_side_bulk_velocity_m_s": str(result.shell_side_bulk_velocity_m_s),
        "shell_side_reynolds_number": str(result.shell_side_reynolds_number),
        "shell_side_prandtl_number": str(result.shell_side_prandtl_number),
        "request_hash": result.request_hash,
        "warnings": [_message_primitive(item) for item in result.warnings],
        "blockers": [_message_primitive(item) for item in result.blockers],
        "deferred_capabilities": list(result.deferred_capabilities),
        "provenance": provenance_prehash_projection(result.provenance),
    }
    return [primitive(values[field]) for field in SUCCESS_RESULT_HASH_FIELDS]


def success_result_hash(result: ShellSideFlowState) -> str:
    return _hash_projection(
        SUCCESS_RESULT_HASH_NAMESPACE, success_result_canonical_projection(result)
    )


def result_id(result_hash: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + result_hash))


def typed_blocked_result_canonical_projection(result: Any) -> list[Any]:
    values = {
        "schema_version": result.schema_version,
        "profile_id": result.profile_id,
        "implementation_software_version": result.implementation_software_version,
        "failure_stage": result.failure_stage,
        "task031_geometry_id": result.task031_geometry_id,
        "task031_geometry_hash": result.task031_geometry_hash,
        "property_snapshot_hash": result.property_snapshot_hash,
        "mass_flow_authority_hash": result.mass_flow_authority_hash,
        "request_hash": result.request_hash,
        "blockers": [_message_primitive(item) for item in result.blockers],
        "warnings": [_message_primitive(item) for item in result.warnings],
        "deferred_capabilities": list(result.deferred_capabilities),
        "provenance": provenance_prehash_projection(result.provenance),
    }
    return [primitive(values[field]) for field in TYPED_BLOCKED_RESULT_HASH_FIELDS]


def typed_blocked_result_hash(result: Any) -> str:
    return _hash_projection(
        TYPED_BLOCKED_RESULT_HASH_NAMESPACE, typed_blocked_result_canonical_projection(result)
    )


def raw_boundary_blocked_result_canonical_projection(
    *,
    schema_version: str,
    profile_id: str,
    implementation_software_version: str,
    raw_request_projection: FrozenRawProjection,
    blockers: tuple[BlockerEntry, ...],
    warnings: tuple[WarningEntry, ...],
    deferred_capabilities: tuple[str, ...],
) -> list[Any]:
    values = {
        "schema_version": schema_version,
        "profile_id": profile_id,
        "implementation_software_version": implementation_software_version,
        "raw_request_projection": projection_primitive(raw_request_projection),
        "blockers": [_message_primitive(item) for item in blockers],
        "warnings": [_message_primitive(item) for item in warnings],
        "deferred_capabilities": list(deferred_capabilities),
    }
    return [primitive(values[field]) for field in RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS]


def raw_boundary_blocked_result_hash(**kwargs: Any) -> str:
    return _hash_projection(
        RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE,
        raw_boundary_blocked_result_canonical_projection(**kwargs),
    )


__all__ = [
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "DESIGN_CONTRACT_PATH",
    "ENGINEERING_AUTHORITY_HASH",
    "ENGINEERING_AUTHORITY_ID",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "MASS_FLOW_AUTHORITY_FIELDS",
    "PROFILE_ID",
    "PROVENANCE_FIELDS",
    "PROVENANCE_HASH_FIELDS",
    "PROVENANCE_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "REQUEST_HASH_NAMESPACE",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_ID_NAME_PREFIX",
    "RESULT_ID_NAMESPACE",
    "RESULT_SCHEMA_VERSION",
    "SHELL_SIDE_MASS_FLOW_AUTHORITY_NAMESPACE",
    "SUCCESS_RESULT_HASH_FIELDS",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "TYPED_BLOCKED_RESULT_HASH_FIELDS",
    "TYPED_BLOCKED_RESULT_HASH_NAMESPACE",
    "canonical_json",
    "canonical_raw_json_or_none",
    "final_provenance_tuple",
    "mass_flow_authority_hash",
    "mass_flow_authority_projection",
    "message_to_primitive",
    "primitive",
    "property_snapshot_projection",
    "provenance_prehash_projection",
    "raw_boundary_blocked_result_canonical_projection",
    "raw_boundary_blocked_result_hash",
    "request_canonical_projection",
    "request_hash",
    "result_id",
    "sha256_hex",
    "success_result_canonical_projection",
    "success_result_hash",
    "task031_result_projection",
    "typed_blocked_result_canonical_projection",
    "typed_blocked_result_hash",
]
