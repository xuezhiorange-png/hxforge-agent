"""Immutable public models for TASK162 thermal-performance closure."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.flow_arrangement_performance_method_authority.models import (
    Task161Result,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    Task038SuccessResult,
)
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

TASK162_SCHEMA_VERSION = "task162.schema.v1"
TASK162_VERSION = "task162.v1"
TASK162_IMPLEMENTATION_SOFTWARE_VERSION = "task162.local-implementation.v1"
TASK162_SOURCE_DEFINITION_ID = "TASK162-SOURCE-DEFINITION-R1-ISSUE-229"
TASK162_RAW_PROJECTION_SCHEMA_VERSION = "task162.raw-projection.v1"
TASK162_RAW_BOUNDARY_SCHEMA_VERSION = "task162.raw-boundary-blocked.v1"
TASK162_TYPED_BLOCKED_SCHEMA_VERSION = "task162.typed-blocked.v1"
TASK162_SUCCESS_REPLAY_EVIDENCE_SCHEMA_VERSION = "task162.success-replay-evidence.v1"

TASK162_RAW_MAX_DEPTH = 16
TASK162_RAW_MAX_NODES = 512
TASK162_RAW_MAX_SCALAR_BYTES = 16_384
TASK162_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE = TASK162_RAW_MAX_SCALAR_BYTES + 1


class Task162ValidationStatus(StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class Task162SuccessVerificationStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class Task162SuccessVerificationFailureReason(StrEnum):
    TASK162_PRODUCER_VERIFICATION_FAILED = "TASK162_PRODUCER_VERIFICATION_FAILED"
    TASK162_IDENTITY_REPLAY_FAILED = "TASK162_IDENTITY_REPLAY_FAILED"
    TASK162_NOT_APPLICABLE = "TASK162_NOT_APPLICABLE"
    TASK162_NOT_COMPLETE = "TASK162_NOT_COMPLETE"
    TASK162_PROVENANCE_INVALID = "TASK162_PROVENANCE_INVALID"


class Task162FailureStage(StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    TYPED_VALIDATION = "TYPED_VALIDATION"
    TASK160_REPLAY = "TASK160_REPLAY"
    TASK161_REPLAY = "TASK161_REPLAY"
    TASK038_REPLAY = "TASK038_REPLAY"
    CROSS_PRODUCER_BINDING = "CROSS_PRODUCER_BINDING"
    CASE_BINDING = "CASE_BINDING"
    APPLICABILITY = "APPLICABILITY"
    NUMERICAL_EVALUATION = "NUMERICAL_EVALUATION"
    ENERGY_BALANCE = "ENERGY_BALANCE"
    TERMINAL_CLOSURE = "TERMINAL_CLOSURE"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


class Task162RawProjectionKind(StrEnum):
    NONE = "NONE"
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    ENUM_LITERAL = "ENUM_LITERAL"
    TASK160_RESULT_IDENTITY = "TASK160_RESULT_IDENTITY"
    TASK161_RESULT_IDENTITY = "TASK161_RESULT_IDENTITY"
    TASK038_RESULT_IDENTITY = "TASK038_RESULT_IDENTITY"
    CROSS_PRODUCER_BINDING_IDENTITY = "CROSS_PRODUCER_BINDING_IDENTITY"
    CASE_AUTHORITY_IDENTITY = "CASE_AUTHORITY_IDENTITY"
    SEQUENCE = "SEQUENCE"
    RECORD = "RECORD"
    UNSUPPORTED_OBJECT = "UNSUPPORTED_OBJECT"
    LIMIT_MARKER = "LIMIT_MARKER"


class Task162CapacitySideRelation(StrEnum):
    COLD_SIDE_IS_CMIN = "COLD_SIDE_IS_CMIN"
    HOT_SIDE_IS_CMIN = "HOT_SIDE_IS_CMIN"
    EQUAL_CAPACITY = "EQUAL_CAPACITY"


class Task162BindingStatus(StrEnum):
    MATCHED = "MATCHED"


class Task162CompatibilityDimension(StrEnum):
    RESULT_IDENTITY_BINDING = "RESULT_IDENTITY_BINDING"
    PHYSICAL_CASE_BINDING = "PHYSICAL_CASE_BINDING"
    TUBE_SIDE_SERVICE_BINDING = "TUBE_SIDE_SERVICE_BINDING"
    SHELL_SIDE_SERVICE_BINDING = "SHELL_SIDE_SERVICE_BINDING"


class Task162CompatibilityStatus(StrEnum):
    PROVEN = "PROVEN"


class Task162ShellType(StrEnum):
    TEMA_E = "TEMA_E"


class Task162FlowOrientation(StrEnum):
    COUNTER_FLOW = "COUNTER_FLOW"


class Task162TubeSideMixing(StrEnum):
    UNMIXED = "UNMIXED"


class Task162ShellSideMixingModel(StrEnum):
    MODEL_2 = "MODEL_2"


class Task162AmbientHeatLossAssumption(StrEnum):
    NEGLIGIBLE_AMBIENT_HEAT_LOSS = "NEGLIGIBLE_AMBIENT_HEAT_LOSS"


class Task162InternalSourceSinkAssumption(StrEnum):
    NO_INTERNAL_THERMAL_SOURCE_SINK = "NO_INTERNAL_THERMAL_SOURCE_SINK"


class Task162WallPropertyAssumption(StrEnum):
    CONSTANT_WALL_MATERIAL_PROPERTIES = "CONSTANT_WALL_MATERIAL_PROPERTIES"


class Task162HeatTransferCoefficientAssumption(StrEnum):
    CONSTANT_HEAT_TRANSFER_COEFFICIENT = "CONSTANT_HEAT_TRANSFER_COEFFICIENT"


class Task162AxialHeatTransferAssumption(StrEnum):
    NEGLIGIBLE_AXIAL_HEAT_TRANSFER = "NEGLIGIBLE_AXIAL_HEAT_TRANSFER"


class Task162LeakageAssumption(StrEnum):
    SOURCE_MODEL_ZERO_LEAKAGE_ASSUMPTION_ADOPTED = "SOURCE_MODEL_ZERO_LEAKAGE_ASSUMPTION_ADOPTED"


class Task162BypassAssumption(StrEnum):
    SOURCE_MODEL_ZERO_BYPASS_ASSUMPTION_ADOPTED = "SOURCE_MODEL_ZERO_BYPASS_ASSUMPTION_ADOPTED"


class Task162EnergyBalanceStatus(StrEnum):
    EXACT = "EXACT"
    DIRECTED_INTERVAL_ENCLOSED = "DIRECTED_INTERVAL_ENCLOSED"


@dataclass(frozen=True, slots=True)
class Task162Blocker:
    code: str
    stage: Task162FailureStage
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Task162Warning:
    code: str


@dataclass(frozen=True, slots=True)
class Task160ResultIdentityProjection:
    schema_version: str
    task160_version: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class Task161ResultIdentityProjection:
    schema_version: str
    task161_version: str
    source_definition_id: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class Task038ResultIdentityProjection:
    schema_version: str
    task038_version: str
    profile_id: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class Task162CompatibilityEvidence:
    dimension: Task162CompatibilityDimension
    status: Task162CompatibilityStatus
    evidence_refs: tuple[str, ...]
    failure_code_or_none: str | None = None


@dataclass(frozen=True, slots=True)
class Task162CrossProducerBindingAuthority:
    binding_authority_id: str
    task160_result_hash: str
    task160_result_id: str
    task161_result_hash: str
    task161_result_id: str
    task038_result_hash: str
    task038_result_id: str
    physical_exchanger_case_id: str
    binding_status: Task162BindingStatus
    evidence_refs: tuple[str, ...]
    compatibility_evidence: tuple[Task162CompatibilityEvidence, ...]


@dataclass(frozen=True, slots=True)
class Task162CaseAuthority:
    case_authority_id: str
    shell_type: Task162ShellType
    overall_flow_orientation: Task162FlowOrientation
    baffle_count: int
    physical_sthe_tube_side_mixing: Task162TubeSideMixing
    physical_sthe_shell_side_mixing_model: Task162ShellSideMixingModel
    steady_state: bool
    ambient_heat_loss_assumption: Task162AmbientHeatLossAssumption
    internal_source_sink_assumption: Task162InternalSourceSinkAssumption
    constant_wall_material_property: Task162WallPropertyAssumption
    constant_heat_transfer_coefficient: Task162HeatTransferCoefficientAssumption
    axial_heat_transfer_assumption: Task162AxialHeatTransferAssumption
    leakage_model_assumption: Task162LeakageAssumption
    bypass_model_assumption: Task162BypassAssumption
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task162SuccessReplayEvidence:
    evidence_schema_version: str
    task162_schema_version: str
    task162_version: str
    task162_implementation_software_version: str
    task162_source_definition_id: str
    task162_result_hash: str
    task162_result_id: UUID
    original_task160_result: Task160Result
    original_task161_result: Task161Result
    original_task038_success_result: Task038SuccessResult
    original_case_authority: Task162CaseAuthority
    request_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Task162SuccessVerificationResult:
    status: Task162SuccessVerificationStatus
    failure_reason_or_none: Task162SuccessVerificationFailureReason | None

    def __post_init__(self) -> None:
        if type(self.status) is not Task162SuccessVerificationStatus:
            raise ValueError("status must be exact Task162SuccessVerificationStatus")
        if self.status is Task162SuccessVerificationStatus.ACCEPTED:
            if self.failure_reason_or_none is not None:
                raise ValueError("ACCEPTED verification result must not contain a failure reason")
            return
        if self.status is Task162SuccessVerificationStatus.REJECTED:
            if type(self.failure_reason_or_none) is not Task162SuccessVerificationFailureReason:
                raise ValueError(
                    "REJECTED verification result requires exact frozen failure reason"
                )
            return
        raise ValueError("unsupported verification status")


@dataclass(frozen=True, slots=True)
class Task162NormalizedCaseBinding:
    physical_configuration_authority: str
    shell_pass_count_authority: int
    tube_pass_count_authority: int
    shell_type_authority: Task162ShellType
    overall_flow_orientation_authority: Task162FlowOrientation
    baffle_count_authority: int
    physical_sthe_tube_side_mixing_authority: Task162TubeSideMixing
    physical_sthe_shell_side_mixing_model_authority: Task162ShellSideMixingModel
    steady_state_authority: bool
    ambient_heat_loss_assumption_authority: Task162AmbientHeatLossAssumption
    internal_source_sink_assumption_authority: Task162InternalSourceSinkAssumption
    constant_wall_material_property_authority: Task162WallPropertyAssumption
    constant_heat_transfer_coefficient_authority: Task162HeatTransferCoefficientAssumption
    axial_heat_transfer_assumption_authority: Task162AxialHeatTransferAssumption
    leakage_model_assumption_authority: Task162LeakageAssumption
    bypass_model_assumption_authority: Task162BypassAssumption


@dataclass(frozen=True, slots=True)
class Task162Request:
    schema_version: str
    task162_version: str
    source_definition_id: str
    task160_result: Any
    task161_result: Any
    task038_result: Any
    cross_producer_binding_authority: Task162CrossProducerBindingAuthority
    case_authority: Task162CaseAuthority
    request_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class IntervalDecimal:
    lower: Decimal
    upper: Decimal


@dataclass(frozen=True, slots=True)
class Task162NumericalFoundation:
    ua_w_k: Decimal
    c_min_w_k: Decimal
    c_dot_hot_w_k: Decimal
    c_dot_cold_w_k: Decimal
    t_hot_in_k: Decimal
    t_cold_in_k: Decimal
    delta_t_in_k: Decimal
    q_max_w: Decimal


@dataclass(frozen=True, slots=True)
class Task162SelectedMethodIdentity:
    method_authority_id: str
    method_family: str
    flow_arrangement_catalog_id: str
    engineering_source_id: str
    relation_id: str
    selected_baffle_relation: str
    baffle_count: int


@dataclass(frozen=True, slots=True)
class Task162EnergyBalanceEvidence:
    policy_id: str
    q_method: Decimal
    q_cold_nominal: Decimal
    q_hot_nominal: Decimal
    cold_residual_nominal: Decimal
    hot_residual_nominal: Decimal
    cold_increment_interval: IntervalDecimal
    hot_decrement_interval: IntervalDecimal
    cold_outlet_interval: IntervalDecimal
    hot_outlet_interval: IntervalDecimal
    q_cold_interval: IntervalDecimal
    q_hot_interval: IntervalDecimal
    cold_residual_interval: IntervalDecimal
    hot_residual_interval: IntervalDecimal
    status: Task162EnergyBalanceStatus


@dataclass(frozen=True, slots=True)
class Task162TerminalClosureEvidence:
    delta_t_hot_in_cold_out: Decimal
    delta_t_hot_out_cold_in: Decimal


@dataclass(frozen=True, slots=True)
class Task162Applicability:
    status: str
    checks: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Task162Completeness:
    status: str
    required_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task162ProvenanceSemanticInputs:
    source_authority_payload_hash: str
    task160_result_evidence_payload_hash: str
    task161_result_evidence_payload_hash: str
    task161_method_catalog_payload_hash: str
    task038_result_evidence_payload_hash: str
    cross_producer_binding_payload_hash: str
    case_authority_payload_hash: str
    magazoni_source_payload_hash: str
    nasa_source_payload_hash: str
    calculation_run_payload_hash: str


@dataclass(frozen=True, slots=True)
class Task162Provenance:
    provenance_hash: str
    graph: ProvenanceGraph


@dataclass(frozen=True, slots=True)
class Task162PreResultIdentityInputs:
    schema_version: str
    task162_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task160_evidence: Task160ResultIdentityProjection
    task161_evidence: Task161ResultIdentityProjection
    task038_evidence: Task038ResultIdentityProjection
    cross_producer_binding_evidence: Task162CrossProducerBindingAuthority
    case_binding_evidence: Task162NormalizedCaseBinding
    numerical_foundation: Task162NumericalFoundation
    selected_method_identity: Task162SelectedMethodIdentity
    selected_baffle_relation: str
    ntu: Decimal
    r_source: Decimal
    p_source: Decimal
    epsilon: Decimal
    q_max: Decimal
    q_method: Decimal
    hot_outlet_temperature: Decimal
    cold_outlet_temperature: Decimal
    q_hot: Decimal
    q_cold: Decimal
    energy_balance_evidence: Task162EnergyBalanceEvidence
    terminal_closure_evidence: Task162TerminalClosureEvidence
    applicability: Task162Applicability
    completeness: Task162Completeness
    warnings_normalized: tuple[Task162Warning, ...]
    blockers_normalized: tuple[Task162Blocker, ...]
    provenance_semantic_inputs: Task162ProvenanceSemanticInputs


@dataclass(frozen=True, slots=True)
class Task162Result:
    schema_version: str
    task162_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task160_evidence: Task160ResultIdentityProjection
    task161_evidence: Task161ResultIdentityProjection
    task038_evidence: Task038ResultIdentityProjection
    cross_producer_binding_evidence: Task162CrossProducerBindingAuthority
    case_binding_evidence: Task162NormalizedCaseBinding
    numerical_foundation: Task162NumericalFoundation
    selected_method_identity: Task162SelectedMethodIdentity
    selected_baffle_relation: str
    ntu: Decimal
    r_source: Decimal
    p_source: Decimal
    epsilon: Decimal
    q_max: Decimal
    q_method: Decimal
    hot_outlet_temperature: Decimal
    cold_outlet_temperature: Decimal
    q_hot: Decimal
    q_cold: Decimal
    energy_balance_evidence: Task162EnergyBalanceEvidence
    terminal_closure_evidence: Task162TerminalClosureEvidence
    applicability: Task162Applicability
    completeness: Task162Completeness
    warnings: tuple[Task162Warning, ...]
    blockers: tuple[Task162Blocker, ...]
    provenance_semantic_inputs: Task162ProvenanceSemanticInputs
    provenance: Task162Provenance
    result_hash: str
    result_id: UUID


@dataclass(frozen=True, slots=True)
class Task162TypedBlockedResult:
    schema_version: str
    task162_version: str
    implementation_software_version: str
    failure_stage: Task162FailureStage
    request_hash: str
    task160_result_id_or_none: str | None
    blockers: tuple[Task162Blocker, ...]
    warnings: tuple[Task162Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task162RawProjectionNode:
    field_name: str
    kind: Task162RawProjectionKind
    type_identity: str | None
    scalar_payload: str | None
    children: tuple[Task162RawProjectionNode, ...]


@dataclass(frozen=True, slots=True)
class Task162RawRequestProjection:
    schema_version: str
    root: Task162RawProjectionNode


@dataclass(frozen=True, slots=True)
class Task162RawBoundaryBlockedResult:
    schema_version: str
    task162_version: str
    implementation_software_version: str
    failure_stage: Task162FailureStage
    raw_request_projection: Task162RawRequestProjection
    raw_request_projection_hash: str
    blockers: tuple[Task162Blocker, ...]
    warnings: tuple[Task162Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task162ValidationResult:
    status: Task162ValidationStatus
    raw_boundary_blocked: Task162RawBoundaryBlockedResult | None = None
    typed_blocked: Task162TypedBlockedResult | None = None
    valid: Task162Result | None = None

    def __post_init__(self) -> None:
        populated = sum(
            value is not None
            for value in (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        )
        if populated != 1:
            raise ValueError("exactly one Task162 validation branch must be populated")


# Short aliases make the typed contract convenient without creating a second schema.
ShellType = Task162ShellType
FlowOrientation = Task162FlowOrientation
TubeSideMixing = Task162TubeSideMixing
ShellSideMixingModel = Task162ShellSideMixingModel
