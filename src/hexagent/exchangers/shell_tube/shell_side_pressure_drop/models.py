"""Public models and frozen field contracts for TASK-034."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

TASK_ID = "TASK034"
REQUEST_SCHEMA_VERSION = "task034.shell-side-pressure-drop-request.v1"
RESULT_SCHEMA_VERSION = "task034.shell-side-pressure-drop-success.v1"
BLOCKED_RESULT_SCHEMA_VERSION = "task034.shell-side-pressure-drop-blocked.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION = (
    "task034.shell-side-pressure-drop-raw-boundary-blocked.v1"
)
IMPLEMENTATION_SOFTWARE_VERSION = "task034.shell-side-pressure-drop-impl-v1"
PROFILE_ID = "hxforge.shell_tube.shell_side_pressure_drop.v1"
FIRST_SLICE_PROFILE_ID = (
    "TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1"
)
CORRELATION_ID = FIRST_SLICE_PROFILE_ID
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-034-shell-and-tube-shell-side-modeled-pressure-drop.md"
SOURCE_DEFINITION_ISSUE = "199"
ENGINEERING_SOURCE_AUTHORITY_RECORD_ID = "5387111841"
SOURCE_ID = "SRC-MDPI-ENERGIES-2017-1156-BAYRAM-SEVILGEN"
SOURCE_VERSION = "2018-01-10_UPDATED_VERSION_OF_RECORD"
SOURCE_LOCATION = "Section_2.1.1_Equations_15_16_17_pages_3_4"
SOURCE_DOI = "10.3390/en1101156"
PUBLIC_QUANTITY = "modeled_shell_side_pressure_drop_pa"
PUBLIC_QUANTUM = Decimal("0.001")

REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task033_upstream_evidence",
    "task031_request_evidence",
    "task031_request_hash",
    "shell_inside_diameter_m",
    "baffle_count",
    "uniform_spacing_sequence_m",
    "tube_pitch_m",
    "tube_outer_diameter_m",
    "pattern_family",
    "shell_side_wall_dynamic_viscosity_pa_s",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_evidence_refs",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    "correlation_id",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_request_hash",
    "task032_result_id",
    "task032_result_hash",
    "task033_request_hash",
    "task033_result_id",
    "task033_result_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "evidence_refs",
)

SUCCESS_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "first_slice_profile_id",
    "implementation_software_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "correlation_id",
    "engineering_source_authority_record_id",
    "source_id",
    "source_version",
    "source_location",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    PUBLIC_QUANTITY,
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "applicability_context",
    "physical_boundary_context",
    "provenance",
)

TYPED_BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "wall_property_schema_version",
    "wall_property_source_id",
    "wall_property_source_version",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
    "request_hash",
    "blocked_result_hash",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "request_hash",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "raw_projection",
)

TASK032_FLOW_STATE_EVIDENCE_FIELDS: tuple[str, ...] = (
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
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)
TASK032_REQUEST_EVIDENCE_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task031_result",
    "property_snapshot_hash",
    "property_snapshot",
    "mass_flow_authority",
    "evidence_refs",
)
TASK031_REQUEST_EVIDENCE_FIELDS: tuple[str, ...] = (
    "schema_version",
    "tube_layout",
    "baffle_geometry_result",
    "engineering_authority",
    "evidence_refs",
)

REQUEST_FIELD_COUNT = 35
SUCCESS_FIELD_COUNT = 40
TYPED_BLOCKED_FIELD_COUNT = 31
RAW_BOUNDARY_BLOCKED_FIELD_COUNT = 8
TASK032_FLOW_STATE_EVIDENCE_FIELD_COUNT = 29
TASK032_REQUEST_EVIDENCE_FIELD_COUNT = 7
TASK031_REQUEST_EVIDENCE_FIELD_COUNT = 5

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "SINGLE_PHASE_GAS_NOT_COMPUTABLE",
    "CONSTRUCTION_FAMILY_RESTRICTION_NOT_COMPUTABLE",
    "NOZZLE_PRESSURE_DROP_NOT_COMPUTABLE",
    "STATIC_HEAD_NOT_COMPUTABLE",
    "ACCELERATION_PRESSURE_DROP_NOT_COMPUTABLE",
    "LEAKAGE_CORRECTIONS_NOT_COMPUTABLE",
    "BYPASS_CORRECTIONS_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "UNEQUAL_BAFFLE_SPACING_NOT_COMPUTABLE",
    "TOTAL_SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "OVERALL_U_NOT_COMPUTABLE",
    "UA_NOT_COMPUTABLE",
    "HEAT_DUTY_NOT_COMPUTABLE",
    "OUTLET_TEMPERATURES_NOT_COMPUTABLE",
    "FULL_EXCHANGER_RATING_NOT_COMPUTABLE",
    "THERMAL_SIZING_NOT_COMPUTABLE",
)


class ValidationStatus(StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class BlockerEntry:
    code: str
    stage: str
    field_path: str | None = None
    message_key: str = ""
    details: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class WarningEntry:
    code: str
    field_path: str | None = None
    message_key: str = ""


@dataclass(frozen=True)
class Task034Request:
    schema_version: Any
    profile_id: Any
    task033_upstream_evidence: Any
    task031_request_evidence: Any
    task031_request_hash: Any
    shell_inside_diameter_m: Any
    baffle_count: Any
    uniform_spacing_sequence_m: Any
    tube_pitch_m: Any
    tube_outer_diameter_m: Any
    pattern_family: Any
    shell_side_wall_dynamic_viscosity_pa_s: Any
    wall_property_schema_version: Any
    wall_property_source_id: Any
    wall_property_source_version: Any
    wall_property_evidence_refs: Any
    wall_property_snapshot_hash: Any
    wall_property_authority_hash: Any
    correlation_id: Any
    shell_side_case_id: Any
    shell_side_stream_id: Any
    shell_side_fluid_id: Any
    task020_configuration_id: Any
    task020_configuration_hash: Any
    task031_geometry_id: Any
    task031_geometry_hash: Any
    task032_request_hash: Any
    task032_result_id: Any
    task032_result_hash: Any
    task033_request_hash: Any
    task033_result_id: Any
    task033_result_hash: Any
    property_snapshot_hash: Any
    mass_flow_authority_hash: Any
    evidence_refs: Any


@dataclass(frozen=True)
class ShellSidePressureDropResult:
    schema_version: str
    profile_id: str
    first_slice_profile_id: str
    implementation_software_version: str
    shell_side_case_id: str | None
    shell_side_stream_id: str | None
    shell_side_fluid_id: str | None
    task020_configuration_id: str | None
    task020_configuration_hash: str | None
    task031_request_hash: str | None
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    task033_request_hash: str | None
    task033_result_hash: str | None
    task033_result_id: str | None
    correlation_id: str
    engineering_source_authority_record_id: str
    source_id: str
    source_version: str
    source_location: str
    wall_property_schema_version: str | None
    wall_property_source_id: str | None
    wall_property_source_version: str | None
    wall_property_snapshot_hash: str | None
    wall_property_authority_hash: str | None
    modeled_shell_side_pressure_drop_pa: Decimal
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    applicability_context: tuple[tuple[str, Any], ...]
    physical_boundary_context: tuple[tuple[str, Any], ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSidePressureDropBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    failure_stage: str
    shell_side_case_id: str | None
    shell_side_stream_id: str | None
    shell_side_fluid_id: str | None
    task020_configuration_id: str | None
    task020_configuration_hash: str | None
    task031_request_hash: str | None
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    task033_request_hash: str | None
    task033_result_hash: str | None
    task033_result_id: str | None
    wall_property_schema_version: str | None
    wall_property_source_id: str | None
    wall_property_source_version: str | None
    wall_property_snapshot_hash: str | None
    wall_property_authority_hash: str | None
    request_hash: str | None
    blocked_result_hash: str
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSidePressureDropRawBoundaryBlockedResult:
    schema_version: str
    profile_id: str
    request_hash: str | None
    blocked_result_hash: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]
    raw_projection: tuple[Any, ...]


@dataclass(frozen=True)
class ShellSidePressureDropValidationResult:
    status: ValidationStatus
    pressure_drop: ShellSidePressureDropResult | None
    blocked_result: ShellSidePressureDropBlockedResult | None
    raw_boundary_blocked_result: ShellSidePressureDropRawBoundaryBlockedResult | None

    @property
    def result(self) -> Any:
        return self.pressure_drop or self.blocked_result or self.raw_boundary_blocked_result

    @property
    def blockers(self) -> tuple[BlockerEntry, ...]:
        result = self.result
        return () if result is None else result.blockers

    @property
    def warnings(self) -> tuple[WarningEntry, ...]:
        result = self.result
        return () if result is None else result.warnings


__all__ = [name for name in globals() if not name.startswith("__")]
