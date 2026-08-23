"""TASK-032 immutable value models and frozen contract constants."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from .raw_projection import FrozenRawProjection

TASK_ID = "TASK-032"
REQUEST_SCHEMA_VERSION = "task032.shell-side-flow-state-request.v1"
RESULT_SCHEMA_VERSION = "task032.shell-side-flow-state.v1"
BLOCKED_RESULT_SCHEMA_VERSION = "task032.shell-side-flow-state-blocked.v1"
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION = "task032.shell-side-flow-state-raw-boundary-blocked.v1"
PROFILE_ID = "hxforge.shell_tube.shell_side_flow_state.v1"
FIRST_SLICE_PROFILE_ID = "SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1"
FLOW_MODEL = "SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING"
RHEOLOGY_MODEL = "NEWTONIAN"
PROPERTY_STATE_ROLE = "BULK_SHELL_SIDE_STATE"
MASS_FLOW_SIGN_CONVENTION = "POSITIVE_ALONG_DECLARED_SHELL_SIDE_FLOW_DIRECTION"
IMPLEMENTATION_SOFTWARE_VERSION = "task032.shell-side-flow-state-impl-v1"
DESIGN_CONTRACT_PATH = "docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md"
FLOW_REGION_IDENTITY = "CENTRAL_CROSSFLOW_SCREENING"

FORMULA_MASS_VELOCITY_ID = "TASK032_MASS_VELOCITY_KERN_SCREENING_INTCHOPN_EQ57_V1"
FORMULA_REYNOLDS_ID = "TASK032_REYNOLDS_KERN_SCREENING_INTCHOPN_EQ54_V1"
FORMULA_BULK_VELOCITY_ID = "TASK032_BULK_VELOCITY_CONTINUITY_NASA_GRC_V1"
FORMULA_PRANDTL_ID = "TASK032_PRANDTL_DIMENSIONLESS_INTCHOPN_EQ35_V1"
FORMULA_IDS: tuple[str, ...] = (
    FORMULA_MASS_VELOCITY_ID,
    FORMULA_REYNOLDS_ID,
    FORMULA_BULK_VELOCITY_ID,
    FORMULA_PRANDTL_ID,
)
SOURCE_IDS: tuple[str, ...] = (
    "SRC-INTECHOPEN-100450-KHARAJI-2021",
    "SRC-NASA-GRC-MASS-FLOW-RATE-EQUATIONS",
)

DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE",
    "NON_NEWTONIAN_RHEOLOGY_NOT_COMPUTABLE",
    "COMPRESSIBLE_PATH_INTEGRATION_NOT_COMPUTABLE",
    "PROPERTY_PATH_INTEGRATION_NOT_COMPUTABLE",
    "SHELL_SIDE_HEAT_TRANSFER_COEFFICIENT_NOT_COMPUTABLE",
    "SHELL_SIDE_NUSSELT_NUMBER_NOT_COMPUTABLE",
    "SHELL_SIDE_FRICTION_FACTOR_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "LEAKAGE_CORRECTIONS_NOT_COMPUTABLE",
    "BYPASS_CORRECTIONS_NOT_COMPUTABLE",
    "OVERALL_U_NOT_COMPUTABLE",
    "UA_NOT_COMPUTABLE",
    "LMTD_NOT_COMPUTABLE",
    "HEAT_DUTY_NOT_COMPUTABLE",
    "OUTLET_TEMPERATURES_NOT_COMPUTABLE",
    "FULL_EXCHANGER_RATING_NOT_COMPUTABLE",
)

REQUEST_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "task031_result",
    "property_snapshot_hash",
    "property_snapshot",
    "mass_flow_authority",
    "evidence_refs",
)

TASK031_RESULT_FIELDS: tuple[str, ...] = (
    "status",
    "geometry",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "blocked_result_hash",
)

TASK031_GEOMETRY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "geometry_id",
    "geometry_hash",
    "request_hash",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task021_layout_id",
    "task021_layout_hash",
    "task022_geometry_id",
    "task022_geometry_hash",
    "task024_geometry_id",
    "task024_geometry_hash",
    "engineering_authority_id",
    "engineering_authority_hash",
    "formula_a_id",
    "formula_b_id",
    "pattern_family",
    "flow_region_identity",
    "central_inter_baffle_spacing_m",
    "central_crossflow_flow_area_m2",
    "shell_side_equivalent_hydraulic_diameter_m",
    "warnings",
    "blockers",
    "deferred_capabilities",
    "provenance",
)

PROPERTY_SNAPSHOT_FIELDS: tuple[str, ...] = (
    "density_kg_m3",
    "dynamic_viscosity_pa_s",
    "thermal_conductivity_w_m_k",
    "specific_heat_capacity_j_kg_k",
    "bulk_temperature_k",
    "bulk_pressure_pa",
    "phase_region",
    "property_source_id",
    "property_source_version",
    "property_snapshot_hash",
)

MASS_FLOW_AUTHORITY_FIELDS: tuple[str, ...] = (
    "schema_version",
    "authority_profile_id",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "rheology_model",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "property_state_role",
    "mass_flow_rate_kg_s",
    "mass_flow_sign_convention",
    "authority_source_id",
    "authority_source_version",
    "evidence_refs",
    "authority_hash",
)

SUCCESS_RESULT_FIELDS: tuple[str, ...] = (
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

TYPED_BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "failure_stage",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "mass_flow_authority_hash",
    "request_hash",
    "result_hash",
    "result_id",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "provenance",
)

RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "raw_request_projection",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
)


class ValidationStatus(enum.StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


class BlockerCode(enum.StrEnum):
    SSFS_SCHEMA_VERSION_UNSUPPORTED = "SSFS_SCHEMA_VERSION_UNSUPPORTED"
    SSFS_PROFILE_ID_UNSUPPORTED = "SSFS_PROFILE_ID_UNSUPPORTED"
    SSFS_RAW_TYPE_INVALID = "SSFS_RAW_TYPE_INVALID"
    SSFS_UNKNOWN_FIELD = "SSFS_UNKNOWN_FIELD"
    SSFS_DECIMAL_LEXICAL_INVALID = "SSFS_DECIMAL_LEXICAL_INVALID"
    SSFS_EVIDENCE_REFS_INVALID = "SSFS_EVIDENCE_REFS_INVALID"
    SSFS_TASK031_RESULT_MISSING = "SSFS_TASK031_RESULT_MISSING"
    SSFS_TASK031_RESULT_INVALID = "SSFS_TASK031_RESULT_INVALID"
    SSFS_TASK031_RESULT_HAS_BLOCKERS = "SSFS_TASK031_RESULT_HAS_BLOCKERS"
    SSFS_TASK031_GEOMETRY_MISSING = "SSFS_TASK031_GEOMETRY_MISSING"
    SSFS_TASK031_IDENTITY_MISMATCH = "SSFS_TASK031_IDENTITY_MISMATCH"
    SSFS_PROPERTY_SNAPSHOT_MISSING = "SSFS_PROPERTY_SNAPSHOT_MISSING"
    SSFS_PROPERTY_SNAPSHOT_INVALID = "SSFS_PROPERTY_SNAPSHOT_INVALID"
    SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH = "SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH"
    SSFS_MASS_FLOW_AUTHORITY_MISSING = "SSFS_MASS_FLOW_AUTHORITY_MISSING"
    SSFS_MASS_FLOW_AUTHORITY_INVALID = "SSFS_MASS_FLOW_AUTHORITY_INVALID"
    SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH = "SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH"
    SSFS_SAME_CASE_BINDING_MISMATCH = "SSFS_SAME_CASE_BINDING_MISMATCH"
    SSFS_PHASE_UNSUPPORTED = "SSFS_PHASE_UNSUPPORTED"
    SSFS_RHEOLOGY_MODEL_UNSUPPORTED = "SSFS_RHEOLOGY_MODEL_UNSUPPORTED"
    SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED = "SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED"
    SSFS_MASS_FLOW_NON_POSITIVE = "SSFS_MASS_FLOW_NON_POSITIVE"
    SSFS_FLOW_MODEL_UNSUPPORTED = "SSFS_FLOW_MODEL_UNSUPPORTED"
    SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH = "SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH"
    SSFS_FORMULA_DOMAIN_VIOLATION = "SSFS_FORMULA_DOMAIN_VIOLATION"
    SSFS_FORMULA_CALCULATION_FAILED = "SSFS_FORMULA_CALCULATION_FAILED"
    SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION = (
        "SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION"
    )
    SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION = (
        "SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION"
    )
    SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION = "SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION"
    SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION = "SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION"
    SSFS_CANONICALIZATION_FAILED = "SSFS_CANONICALIZATION_FAILED"
    SSFS_RESULT_IDENTITY_FINALIZATION_FAILED = "SSFS_RESULT_IDENTITY_FINALIZATION_FAILED"
    SSFS_PARTIAL_RESULT_FORBIDDEN = "SSFS_PARTIAL_RESULT_FORBIDDEN"


BLOCKER_CODES: frozenset[str] = frozenset(code.value for code in BlockerCode)
REACHABLE_BLOCKER_CODES: tuple[str, ...] = tuple(
    code.value for code in BlockerCode if code is not BlockerCode.SSFS_PARTIAL_RESULT_FORBIDDEN
)
DEFENSIVE_BLOCKER_CODES: tuple[str, ...] = (BlockerCode.SSFS_PARTIAL_RESULT_FORBIDDEN.value,)


class WarningCode(enum.StrEnum):
    SSFS_SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY = (
        "SSFS_SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY"
    )
    SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED = "SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED"
    SSFS_NON_NEWTONIAN_DEFERRED = "SSFS_NON_NEWTONIAN_DEFERRED"
    SSFS_COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED = "SSFS_COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED"
    SSFS_HEAT_TRANSFER_PRESSURE_DROP_DEFERRED = "SSFS_HEAT_TRANSFER_PRESSURE_DROP_DEFERRED"
    SSFS_NO_FULL_EXCHANGER_RATING_CLAIM = "SSFS_NO_FULL_EXCHANGER_RATING_CLAIM"
    SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY = "SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY"


WARNING_CODES: frozenset[str] = frozenset(code.value for code in WarningCode)


@dataclass(frozen=True)
class BlockerEntry:
    code: str
    severity: str
    stage: str
    field_path: str | None
    message_key: str
    payload: tuple[tuple[str, str], ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class WarningEntry:
    code: str
    severity: str
    prerequisite_stage: str
    field_path: str | None
    message_key: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Task031GeometryBinding:
    schema_version: str
    geometry_id: str
    geometry_hash: str
    request_hash: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task021_layout_id: str
    task021_layout_hash: str
    task022_geometry_id: str
    task022_geometry_hash: str
    task024_geometry_id: str
    task024_geometry_hash: str
    engineering_authority_id: str
    engineering_authority_hash: str
    formula_a_id: str
    formula_b_id: str
    pattern_family: str
    flow_region_identity: str
    central_inter_baffle_spacing_m: str
    central_crossflow_flow_area_m2: str
    shell_side_equivalent_hydraulic_diameter_m: str
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class Task031ResultBinding:
    status: str
    geometry: Task031GeometryBinding | None
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    deferred_capabilities: tuple[str, ...]
    blocked_result_hash: str | None


@dataclass(frozen=True)
class ShellSideMassFlowAuthority:
    schema_version: str
    authority_profile_id: str
    shell_side_case_id: str
    shell_side_stream_id: str
    shell_side_fluid_id: str
    rheology_model: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task031_geometry_id: str
    task031_geometry_hash: str
    property_snapshot_hash: str
    property_state_role: str
    mass_flow_rate_kg_s: Any
    mass_flow_sign_convention: str
    authority_source_id: str
    authority_source_version: str
    evidence_refs: tuple[str, ...]
    authority_hash: str


@dataclass(frozen=True)
class ShellSideFlowStateRequest:
    schema_version: str
    profile_id: str
    task031_result: Task031ResultBinding
    property_snapshot_hash: str
    property_snapshot: Any
    mass_flow_authority: ShellSideMassFlowAuthority
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class ShellSideFlowState:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    shell_side_case_id: str
    shell_side_stream_id: str
    shell_side_fluid_id: str
    task020_configuration_id: str
    task020_configuration_hash: str
    task031_geometry_id: str
    task031_geometry_hash: str
    property_snapshot_hash: str
    mass_flow_authority_hash: str
    engineering_authority_id: str
    engineering_authority_hash: str
    flow_model: str
    phase_region: Any
    rheology_model: str
    shell_side_mass_flow_rate_kg_s: Any
    shell_side_mass_velocity_kg_m2_s: Any
    shell_side_bulk_velocity_m_s: Any
    shell_side_reynolds_number: Any
    shell_side_prandtl_number: Any
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[WarningEntry, ...]
    blockers: tuple[BlockerEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSideFlowStateBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    failure_stage: str
    task031_geometry_id: str | None
    task031_geometry_hash: str | None
    property_snapshot_hash: str | None
    mass_flow_authority_hash: str | None
    request_hash: str | None
    result_hash: str
    result_id: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]
    provenance: tuple[tuple[str, Any], ...]


@dataclass(frozen=True)
class ShellSideFlowStateRawBoundaryBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    raw_request_projection: FrozenRawProjection
    blocked_result_hash: str
    blockers: tuple[BlockerEntry, ...]
    warnings: tuple[WarningEntry, ...]
    deferred_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class ShellSideFlowStateValidationResult:
    status: ValidationStatus
    flow_state: ShellSideFlowState | None
    blocked_result: ShellSideFlowStateBlockedResult | None
    raw_boundary_blocked_result: ShellSideFlowStateRawBoundaryBlockedResult | None

    @property
    def result(
        self,
    ) -> (
        ShellSideFlowState
        | ShellSideFlowStateBlockedResult
        | ShellSideFlowStateRawBoundaryBlockedResult
        | None
    ):
        return self.flow_state or self.blocked_result or self.raw_boundary_blocked_result

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
    "BLOCKER_CODES",
    "BlockerCode",
    "BlockerEntry",
    "DEFERRED_CAPABILITIES",
    "DESIGN_CONTRACT_PATH",
    "FIRST_SLICE_PROFILE_ID",
    "FLOW_MODEL",
    "FLOW_REGION_IDENTITY",
    "FORMULA_BULK_VELOCITY_ID",
    "FORMULA_IDS",
    "FORMULA_MASS_VELOCITY_ID",
    "FORMULA_PRANDTL_ID",
    "FORMULA_REYNOLDS_ID",
    "IMPLEMENTATION_SOFTWARE_VERSION",
    "MASS_FLOW_AUTHORITY_FIELDS",
    "MASS_FLOW_SIGN_CONVENTION",
    "PROFILE_ID",
    "PROPERTY_SNAPSHOT_FIELDS",
    "PROPERTY_STATE_ROLE",
    "RAW_BOUNDARY_BLOCKED_RESULT_FIELDS",
    "RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION",
    "REQUEST_FIELDS",
    "REQUEST_SCHEMA_VERSION",
    "REACHABLE_BLOCKER_CODES",
    "RESULT_SCHEMA_VERSION",
    "RHEOLOGY_MODEL",
    "SOURCE_IDS",
    "SUCCESS_RESULT_FIELDS",
    "ShellSideFlowState",
    "ShellSideFlowStateBlockedResult",
    "ShellSideFlowStateRawBoundaryBlockedResult",
    "ShellSideFlowStateRequest",
    "ShellSideFlowStateValidationResult",
    "ShellSideMassFlowAuthority",
    "Task031GeometryBinding",
    "Task031ResultBinding",
    "TASK031_GEOMETRY_FIELDS",
    "TASK031_RESULT_FIELDS",
    "TYPED_BLOCKED_RESULT_FIELDS",
    "ValidationStatus",
    "WARNING_CODES",
    "WarningCode",
    "WarningEntry",
]
