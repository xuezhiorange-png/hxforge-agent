"""Frozen identity projections for TASK-033 and upstream replay."""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, cast

from hexagent.exchangers.shell_tube.tube_layout.canonical import sha256_hex as shared_sha256_hex

from .models import (
    BLOCKED_RESULT_SCHEMA_VERSION,
    HEAT_TRANSFER_SURFACE,
    RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION,
    REQUEST_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    SUCCESS_RESULT_FIELDS,
    TYPED_BLOCKED_RESULT_FIELDS,
    BlockerEntry,
    ShellSideHeatTransferBlockedResult,
    ShellSideHeatTransferRawBoundaryBlockedResult,
    ShellSideHeatTransferRequest,
    ShellSideHeatTransferResult,
    Task032AcceptedFlowStateEvidence,
    Task032AcceptedRequestEvidence,
    WarningEntry,
)

REQUEST_HASH_NAMESPACE = b"task033.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE = b"task033.success-result.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE = b"task033.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE = b"task033.raw-boundary-blocked-result.v1"
PROVENANCE_HASH_NAMESPACE = b"task033.provenance.v1"
RAW_PROJECTION_HASH_NAMESPACE = b"task033.raw-projection.v1"

TASK032_REQUEST_HASH_NAMESPACE = "task032.request.v1"
TASK032_SUCCESS_RESULT_HASH_NAMESPACE = "task032.success-result.v1"
TASK032_RESULT_ID_NAMESPACE = uuid.UUID("96ab5cf6-204d-547a-9d27-8a5eff46f997")
TASK032_RESULT_ID_NAME_PREFIX = "task032-result-v1::"

RESULT_ID_NAMESPACE = uuid.UUID("6d4de79e-3e04-5160-93e4-725c3f308a22")
RESULT_ID_NAME_PREFIX = "task033-shell-side-heat-transfer-id.v1:"

NULL_KIND = b"n"
BOOL_KIND = b"b"
INTEGER_KIND = b"i"
STRING_KIND = b"s"
DECIMAL_KIND = b"d"
STRING_TUPLE_KIND = b"t"
STRING_MAPPING_KIND = b"m"
PROPERTY_SNAPSHOT_KIND = b"p"
MASS_FLOW_AUTHORITY_KIND = b"a"
TASK031_RESULT_KIND = b"h"
BLOCKER_TUPLE_KIND = b"k"
BLOCKER_ENTRY_KIND = b"c"
TASK032_FLOW_STATE_KIND = b"f"
TASK032_REQUEST_EVIDENCE_KIND = b"q"
PROVENANCE_KIND = b"v"

TASK032_PROVENANCE_HASH_FIELDS: tuple[str, ...] = (
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
)


def primitive(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, BlockerEntry):
        return {
            "code": value.code,
            "stage": value.stage,
            "field_path": value.field_path,
            "message_key": value.message_key,
            "details": [[key, item] for key, item in value.details],
        }
    if isinstance(value, WarningEntry):
        return {
            "code": value.code,
            "field_path": value.field_path,
            "message_key": value.message_key,
        }
    if is_dataclass(value):
        return primitive(asdict(cast(Any, value)))
    if isinstance(value, tuple):
        return [primitive(item) for item in value]
    if isinstance(value, list):
        return [primitive(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): primitive(item) for key, item in value.items()}
    return value


def canonical_bytes(namespace: bytes, projection: Any) -> bytes:
    payload = [namespace.decode("ascii"), primitive(projection)]
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def hash_projection(namespace: bytes, projection: Any) -> str:
    return hashlib.sha256(canonical_bytes(namespace, projection)).hexdigest()


def sha256_hex(value: Any) -> str:
    """Repository-compatible JSON identity primitive."""
    return shared_sha256_hex(primitive(value))


def _message(value: Any) -> Any:
    return primitive(value)


def _geometry_projection(geometry: Mapping[str, Any]) -> list[Any]:
    """TASK032 request nested geometry projection (keeps full provenance pairs)."""
    return _geometry_projection_for_task032(geometry)


def _geometry_projection_for_task032(geometry: Mapping[str, Any]) -> list[Any]:
    return [
        geometry.get("schema_version"),
        geometry.get("geometry_id"),
        geometry.get("geometry_hash"),
        geometry.get("request_hash"),
        geometry.get("task020_configuration_id"),
        geometry.get("task020_configuration_hash"),
        geometry.get("task021_layout_id"),
        geometry.get("task021_layout_hash"),
        geometry.get("task022_geometry_id"),
        geometry.get("task022_geometry_hash"),
        geometry.get("task024_geometry_id"),
        geometry.get("task024_geometry_hash"),
        geometry.get("engineering_authority_id"),
        geometry.get("engineering_authority_hash"),
        geometry.get("formula_a_id"),
        geometry.get("formula_b_id"),
        geometry.get("pattern_family"),
        geometry.get("flow_region_identity"),
        geometry.get("central_inter_baffle_spacing_m"),
        geometry.get("central_crossflow_flow_area_m2"),
        geometry.get("shell_side_equivalent_hydraulic_diameter_m"),
        primitive(geometry.get("warnings", [])),
        primitive(geometry.get("blockers", [])),
        list(geometry.get("deferred_capabilities", [])),
        primitive(geometry.get("provenance", [])),
    ]


def _pairs_to_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    result: dict[str, Any] = {}
    if isinstance(value, (list, tuple)):
        for item in value:
            if isinstance(item, (list, tuple)) and len(item) == 2 and isinstance(item[0], str):
                result[item[0]] = item[1]
    return result


def task031_result_projection(result: Mapping[str, Any]) -> list[Any]:
    geometry = result.get("geometry")
    return [
        result.get("status"),
        None if geometry is None else _geometry_projection(geometry),
        primitive(result.get("warnings", [])),
        primitive(result.get("blockers", [])),
        list(result.get("deferred_capabilities", [])),
        result.get("blocked_result_hash"),
    ]


def property_snapshot_projection(snapshot: Mapping[str, Any]) -> list[Any]:
    return [
        str(snapshot.get("density_kg_m3")),
        str(snapshot.get("dynamic_viscosity_pa_s")),
        str(snapshot.get("thermal_conductivity_w_m_k")),
        str(snapshot.get("specific_heat_capacity_j_kg_k")),
        str(snapshot.get("bulk_temperature_k")),
        str(snapshot.get("bulk_pressure_pa")),
        snapshot.get("phase_region"),
        snapshot.get("property_source_id"),
        snapshot.get("property_source_version"),
        snapshot.get("property_snapshot_hash"),
    ]


def mass_flow_authority_projection(
    authority: Mapping[str, Any], *, include_hash: bool = True
) -> list[Any]:
    values: list[Any] = [
        authority.get("schema_version"),
        authority.get("authority_profile_id"),
        authority.get("shell_side_case_id"),
        authority.get("shell_side_stream_id"),
        authority.get("shell_side_fluid_id"),
        authority.get("rheology_model"),
        authority.get("task020_configuration_id"),
        authority.get("task020_configuration_hash"),
        authority.get("task031_geometry_id"),
        authority.get("task031_geometry_hash"),
        authority.get("property_snapshot_hash"),
        authority.get("property_state_role"),
        str(authority.get("mass_flow_rate_kg_s")),
        authority.get("mass_flow_sign_convention"),
        authority.get("authority_source_id"),
        authority.get("authority_source_version"),
        sorted(authority.get("evidence_refs", [])),
    ]
    if include_hash:
        values.append(authority.get("authority_hash"))
    return values


def mass_flow_authority_hash(authority: Mapping[str, Any]) -> str:
    return sha256_hex(
        [
            "task032.shell-side-mass-flow-authority.v1",
            mass_flow_authority_projection(authority, include_hash=False),
        ]
    )


def task032_request_projection(evidence: Task032AcceptedRequestEvidence) -> list[Any]:
    return [
        evidence.schema_version,
        evidence.profile_id,
        task031_result_projection(evidence.task031_result),
        evidence.property_snapshot_hash,
        property_snapshot_projection(evidence.property_snapshot),
        mass_flow_authority_projection(evidence.mass_flow_authority),
        list(evidence.evidence_refs),
    ]


def task032_request_hash(evidence: Task032AcceptedRequestEvidence) -> str:
    return sha256_hex([TASK032_REQUEST_HASH_NAMESPACE, task032_request_projection(evidence)])


def task033_request_hash(request: ShellSideHeatTransferRequest) -> str:
    return sha256_hex(
        [
            REQUEST_SCHEMA_VERSION,
            request.profile_id,
            primitive(request.task032_flow_state),
            primitive(request.task032_request_evidence),
            list(request.evidence_refs),
        ]
    )


def task032_success_projection(flow: Task032AcceptedFlowStateEvidence) -> list[Any]:
    provenance = _pairs_to_mapping(flow.provenance)
    values: dict[str, Any] = {
        "schema_version": flow.schema_version,
        "profile_id": flow.profile_id,
        "implementation_software_version": flow.implementation_software_version,
        "shell_side_case_id": flow.shell_side_case_id,
        "shell_side_stream_id": flow.shell_side_stream_id,
        "shell_side_fluid_id": flow.shell_side_fluid_id,
        "task020_configuration_id": flow.task020_configuration_id,
        "task020_configuration_hash": flow.task020_configuration_hash,
        "task031_geometry_id": flow.task031_geometry_id,
        "task031_geometry_hash": flow.task031_geometry_hash,
        "property_snapshot_hash": flow.property_snapshot_hash,
        "mass_flow_authority_hash": flow.mass_flow_authority_hash,
        "engineering_authority_id": flow.engineering_authority_id,
        "engineering_authority_hash": flow.engineering_authority_hash,
        "flow_model": flow.flow_model,
        "phase_region": flow.phase_region,
        "rheology_model": flow.rheology_model,
        "shell_side_mass_flow_rate_kg_s": str(flow.shell_side_mass_flow_rate_kg_s),
        "shell_side_mass_velocity_kg_m2_s": str(flow.shell_side_mass_velocity_kg_m2_s),
        "shell_side_bulk_velocity_m_s": str(flow.shell_side_bulk_velocity_m_s),
        "shell_side_reynolds_number": str(flow.shell_side_reynolds_number),
        "shell_side_prandtl_number": str(flow.shell_side_prandtl_number),
        "request_hash": flow.request_hash,
        "warnings": primitive(flow.warnings),
        "blockers": primitive(flow.blockers),
        "deferred_capabilities": list(flow.deferred_capabilities),
        "provenance": [primitive(provenance.get(key)) for key in TASK032_PROVENANCE_HASH_FIELDS],
    }
    fields = (
        "schema_version",
        "profile_id",
        "implementation_software_version",
        "shell_side_case_id",
        "shell_side_stream_id",
        "shell_side_fluid_id",
        "task020_configuration_id",
        "task020_configuration_hash",
        "task031_geometry_id",
        "task031_geometry_hash",
        "property_snapshot_hash",
        "mass_flow_authority_hash",
        "engineering_authority_id",
        "engineering_authority_hash",
        "flow_model",
        "phase_region",
        "rheology_model",
        "shell_side_mass_flow_rate_kg_s",
        "shell_side_mass_velocity_kg_m2_s",
        "shell_side_bulk_velocity_m_s",
        "shell_side_reynolds_number",
        "shell_side_prandtl_number",
        "request_hash",
        "warnings",
        "blockers",
        "deferred_capabilities",
        "provenance",
    )
    return [values[field] for field in fields]


def task032_success_hash(flow: Task032AcceptedFlowStateEvidence) -> str:
    return sha256_hex([TASK032_SUCCESS_RESULT_HASH_NAMESPACE, task032_success_projection(flow)])


def task032_result_id(result_hash: str) -> str:
    return str(uuid.uuid5(TASK032_RESULT_ID_NAMESPACE, TASK032_RESULT_ID_NAME_PREFIX + result_hash))


def property_snapshot_hash(snapshot: Mapping[str, Any]) -> str:
    from hexagent.exchangers.shell_tube.tube_side_thermal import PhaseRegion, PropertySnapshot
    from hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot import (
        recompute_property_snapshot_hash,
    )

    phase = PhaseRegion(str(snapshot["phase_region"]))
    typed = PropertySnapshot(
        density_kg_m3=Decimal(str(snapshot["density_kg_m3"])),
        dynamic_viscosity_pa_s=Decimal(str(snapshot["dynamic_viscosity_pa_s"])),
        thermal_conductivity_w_m_k=Decimal(str(snapshot["thermal_conductivity_w_m_k"])),
        specific_heat_capacity_j_kg_k=Decimal(str(snapshot["specific_heat_capacity_j_kg_k"])),
        bulk_temperature_k=Decimal(str(snapshot["bulk_temperature_k"])),
        bulk_pressure_pa=Decimal(str(snapshot["bulk_pressure_pa"])),
        phase_region=phase,
        property_source_id=str(snapshot["property_source_id"]),
        property_source_version=str(snapshot["property_source_version"]),
        property_snapshot_hash=str(snapshot.get("property_snapshot_hash", "0" * 64)),
    )
    return recompute_property_snapshot_hash(typed)


def task031_geometry_hash(geometry: Mapping[str, Any]) -> str:
    provenance = _pairs_to_mapping(geometry.get("provenance", ()))
    prehash = [
        primitive(provenance.get(key))
        for key in (
            "task_id",
            "design_contract_path",
            "task020_configuration_id",
            "task020_configuration_hash",
            "task021_layout_id",
            "task021_layout_hash",
            "task022_geometry_id",
            "task022_geometry_hash",
            "task024_geometry_id",
            "task024_geometry_hash",
            "engineering_authority_profile_id",
            "engineering_authority_hash",
            "formula_a_id",
            "formula_b_id",
            "source_authority_freeze_comment_id"
            if "source_authority_freeze_comment_id" in provenance
            else "freeze_comment_id",
            "source_ids",
            "pattern_family",
            "flow_region_identity",
            "software_version",
            "git_commit",
            "request_hash",
            "warnings",
            "deferred_capabilities",
        )
    ]
    projection = [
        geometry.get("schema_version"),
        geometry.get("request_hash"),
        geometry.get("task020_configuration_id"),
        geometry.get("task020_configuration_hash"),
        geometry.get("task021_layout_id"),
        geometry.get("task021_layout_hash"),
        geometry.get("task022_geometry_id"),
        geometry.get("task022_geometry_hash"),
        geometry.get("task024_geometry_id"),
        geometry.get("task024_geometry_hash"),
        geometry.get("pattern_family"),
        geometry.get("central_inter_baffle_spacing_m"),
        geometry.get("central_crossflow_flow_area_m2"),
        geometry.get("shell_side_equivalent_hydraulic_diameter_m"),
        geometry.get("flow_region_identity"),
        geometry.get("engineering_authority_id"),
        geometry.get("engineering_authority_hash"),
        geometry.get("formula_a_id"),
        geometry.get("formula_b_id"),
        primitive(geometry.get("warnings", [])),
        list(geometry.get("deferred_capabilities", [])),
        prehash,
    ]
    return sha256_hex(projection)


def task031_geometry_id(geometry_hash: str) -> str:
    return str(
        uuid.uuid5(
            uuid.NAMESPACE_URL,
            "urn:hxforge:task031:shell-side-hydraulic-geometry:v1:" + geometry_hash,
        )
    )


def _result_values(result: Any, fields: tuple[str, ...]) -> list[Any]:
    return [primitive(getattr(result, field)) for field in fields]


def success_result_hash(result: ShellSideHeatTransferResult) -> str:
    fields = tuple(
        field for field in SUCCESS_RESULT_FIELDS if field not in {"result_hash", "result_id"}
    )
    return sha256_hex([RESULT_SCHEMA_VERSION, _result_values(result, fields)])


def result_id(result_hash: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + result_hash))


def typed_blocked_result_hash(result: ShellSideHeatTransferBlockedResult) -> str:
    fields = tuple(field for field in TYPED_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash")
    return sha256_hex([BLOCKED_RESULT_SCHEMA_VERSION, _result_values(result, fields)])


def raw_boundary_blocked_result_hash(
    result: ShellSideHeatTransferRawBoundaryBlockedResult,
) -> str:
    fields = tuple(
        field
        for field in (
            "schema_version",
            "profile_id",
            "request_hash",
            "blockers",
            "warnings",
            "deferred_capabilities",
            "raw_projection",
        )
    )
    return sha256_hex([RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION, _result_values(result, fields)])


PROVENANCE_FIELDS: tuple[str, ...] = (
    "task_id",
    "design_contract_path",
    "implementation_software_version",
    "request_hash",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "correlation_id",
    "engineering_source_authority_record_id",
    "source_id",
    "source_doi",
    "source_location",
    "heat_transfer_surface",
    "value_authority_replay_model",
    "fractional_power_algorithm",
    "warnings",
    "deferred_capabilities",
    "evidence_refs",
    "source_definition_issue",
    "engineering_source_correlation_freeze_comment_id",
    "provenance_hash",
)


def provenance_hash(prehash: Mapping[str, Any]) -> str:
    values = [
        primitive(prehash.get(field)) for field in PROVENANCE_FIELDS if field != "provenance_hash"
    ]
    return sha256_hex([PROVENANCE_HASH_NAMESPACE.decode("ascii"), values])


__all__ = [
    "BLOCKER_ENTRY_KIND",
    "BOOL_KIND",
    "DECIMAL_KIND",
    "HEAT_TRANSFER_SURFACE",
    "INTEGER_KIND",
    "MASS_FLOW_AUTHORITY_KIND",
    "NULL_KIND",
    "PROPERTY_SNAPSHOT_KIND",
    "PROVENANCE_FIELDS",
    "PROVENANCE_HASH_NAMESPACE",
    "RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE",
    "RAW_PROJECTION_HASH_NAMESPACE",
    "REQUEST_HASH_NAMESPACE",
    "RESULT_ID_NAME_PREFIX",
    "RESULT_ID_NAMESPACE",
    "STRING_KIND",
    "STRING_MAPPING_KIND",
    "STRING_TUPLE_KIND",
    "SUCCESS_RESULT_HASH_NAMESPACE",
    "TASK031_RESULT_KIND",
    "TASK032_FLOW_STATE_KIND",
    "TASK032_REQUEST_EVIDENCE_KIND",
    "TYPED_BLOCKED_RESULT_HASH_NAMESPACE",
    "canonical_bytes",
    "hash_projection",
    "mass_flow_authority_hash",
    "mass_flow_authority_projection",
    "primitive",
    "property_snapshot_hash",
    "property_snapshot_projection",
    "provenance_hash",
    "raw_boundary_blocked_result_hash",
    "result_id",
    "sha256_hex",
    "success_result_hash",
    "task031_geometry_hash",
    "task031_geometry_id",
    "task031_result_projection",
    "task032_request_hash",
    "task032_request_projection",
    "task032_result_id",
    "task032_success_hash",
    "task032_success_projection",
    "task033_request_hash",
    "typed_blocked_result_hash",
]
