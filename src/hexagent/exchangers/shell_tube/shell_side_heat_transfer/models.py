"""Immutable public and replay-envelope models for TASK-033."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any

TASK_ID = "TASK033"
REQUEST_SCHEMA_VERSION = "task033.shell-side-heat-transfer-request.v1"
RESULT_SCHEMA_VERSION = "task033.shell-side-heat-transfer.v1"
BLOCKED_RESULT_SCHEMA_VERSION = "task033.shell-side-heat-transfer-blocked.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION = (
    "task033.shell-side-heat-transfer-raw-boundary-blocked.v1"
)
PROFILE_ID = "hxforge.shell_tube.shell_side_heat_transfer.v1"
FIRST_SLICE_PROFILE_ID = (
    "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_OUTER_TUBE_SURFACE_HTC_SCREENING_V1"
)
IMPLEMENTATION_SOFTWARE_VERSION = "task033.shell-side-heat-transfer-impl-v1"
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md"
CORRELATION_ID = "TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1"
HEAT_TRANSFER_SURFACE = "OUTER_TUBE_SURFACE"

FLOW_STATE_EVIDENCE_FIELDS: tuple[str, ...] = (
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
FLOW_STATE_EVIDENCE_FIELD_COUNT = 29

REQUEST_EVIDENCE_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task031_result",
    "property_snapshot_hash",
    "property_snapshot",
    "mass_flow_authority",
    "evidence_refs",
)

REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task032_flow_state",
    "task032_request_evidence",
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
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "correlation_id",
    "engineering_source_authority_record_id",
    "heat_transfer_surface",
    "modeled_shell_side_heat_transfer_coefficient_w_m2_k",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "applicability_context",
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
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
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

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "SHELL_SIDE_FRICTION_FACTOR_NOT_COMPUTABLE",
    "LEAKAGE_CORRECTIONS_NOT_COMPUTABLE",
    "BYPASS_CORRECTIONS_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "WALL_TEMPERATURE_ITERATION_NOT_COMPUTABLE",
    "WALL_VISCOSITY_CORRECTION_NOT_COMPUTABLE",
    "AREA_BASIS_CONVERSION_NOT_COMPUTABLE",
    "OVERALL_U_NOT_COMPUTABLE",
    "UA_NOT_COMPUTABLE",
    "LMTD_NOT_COMPUTABLE",
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
class Task032AcceptedFlowStateEvidence:
    schema_version: Any
    profile_id: Any
    implementation_software_version: Any
    shell_side_case_id: Any
    shell_side_stream_id: Any
    shell_side_fluid_id: Any
    task020_configuration_id: Any
    task020_configuration_hash: Any
    task031_geometry_id: Any
    task031_geometry_hash: Any
    property_snapshot_hash: Any
    mass_flow_authority_hash: Any
    engineering_authority_id: Any
    engineering_authority_hash: Any
    flow_model: Any
    phase_region: Any
    rheology_model: Any
    shell_side_mass_flow_rate_kg_s: Any
    shell_side_mass_velocity_kg_m2_s: Any
    shell_side_bulk_velocity_m_s: Any
    shell_side_reynolds_number: Any
    shell_side_prandtl_number: Any
    request_hash: Any
    result_hash: Any
    result_id: Any
    warnings: Any
    blockers: Any
    deferred_capabilities: Any
    provenance: Any


@dataclass(frozen=True)
class Task032AcceptedRequestEvidence:
    schema_version: Any
    profile_id: Any
    task031_result: dict[str, Any]
    property_snapshot_hash: Any
    property_snapshot: dict[str, Any]
    mass_flow_authority: dict[str, Any]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ShellSideHeatTransferRequest:
    schema_version: str
    profile_id: str
    task032_flow_state: Task032AcceptedFlowStateEvidence
    task032_request_evidence: Task032AcceptedRequestEvidence
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ShellSideHeatTransferResult:
    schema_version: str
    profile_id: str
    first_slice_profile_id: str
    implementation_software_version: str
    shell_side_case_id: str
    shell_side_stream_id: str
    shell_side_fluid_id: str
    task020_configuration_id: str | None
    task020_configuration_hash: str | None
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    correlation_id: str
    engineering_source_authority_record_id: str
    heat_transfer_surface: str
    modeled_shell_side_heat_transfer_coefficient_w_m2_k: Decimal
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    applicability_context: tuple[tuple[str, Any], ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSideHeatTransferBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    failure_stage: str
    shell_side_case_id: str | None
    shell_side_stream_id: str | None
    shell_side_fluid_id: str | None
    task020_configuration_id: str | None
    task020_configuration_hash: str | None
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    task032_request_hash: str | None
    task032_result_hash: str | None
    task032_result_id: str | None
    request_hash: str | None
    blocked_result_hash: str
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSideHeatTransferRawBoundaryBlockedResult:
    schema_version: str
    profile_id: str
    request_hash: str | None
    blocked_result_hash: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]
    raw_projection: tuple[Any, ...]


@dataclass(frozen=True)
class ShellSideHeatTransferValidationResult:
    status: ValidationStatus
    heat_transfer: ShellSideHeatTransferResult | None
    blocked_result: ShellSideHeatTransferBlockedResult | None
    raw_boundary_blocked_result: ShellSideHeatTransferRawBoundaryBlockedResult | None

    @property
    def result(
        self,
    ) -> (
        ShellSideHeatTransferResult
        | ShellSideHeatTransferBlockedResult
        | ShellSideHeatTransferRawBoundaryBlockedResult
        | None
    ):
        return self.heat_transfer or self.blocked_result or self.raw_boundary_blocked_result

    @property
    def warnings(self) -> tuple[WarningEntry, ...]:
        result = self.result
        return () if result is None else result.warnings

    @property
    def blockers(self) -> tuple[BlockerEntry, ...]:
        result = self.result
        return () if result is None else result.blockers


__all__ = [
    "BLOCKED_RESULT_SCHEMA_VERSION",
    "BlockerEntry",
    "CORRELATION_ID",
    "DEFERRED_CAPABILITIES",
    "DESIGN_CONTRACT_PATH",
    "FIRST_SLICE_PROFILE_ID",
    "FLOW_STATE_EVIDENCE_FIELD_COUNT",
    "FLOW_STATE_EVIDENCE_FIELDS",
    "HEAT_TRANSFER_SURFACE",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "PROFILE_ID",
    "RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "REQUEST_EVIDENCE_FIELDS",
    "REQUEST_FIELDS",
    "REQUEST_SCHEMA_VERSION",
    "RESULT_SCHEMA_VERSION",
    "SUCCESS_RESULT_FIELDS",
    "TYPED_BLOCKED_RESULT_FIELDS",
    "Task032AcceptedFlowStateEvidence",
    "Task032AcceptedRequestEvidence",
    "ShellSideHeatTransferBlockedResult",
    "ShellSideHeatTransferRawBoundaryBlockedResult",
    "ShellSideHeatTransferRequest",
    "ShellSideHeatTransferResult",
    "ShellSideHeatTransferValidationResult",
    "ValidationStatus",
    "WarningEntry",
]
