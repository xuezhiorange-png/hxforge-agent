"""Immutable TASK163 thermal-rating composition models.

TASK163 deliberately contains no thermal calculation primitives.  Its models
only represent producer evidence, deterministic projections, and the
composition result described by the frozen TASK163 design authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162EnergyBalanceEvidence,
    Task162Result,
    Task162SelectedMethodIdentity,
    Task162SuccessReplayEvidence,
    Task162TerminalClosureEvidence,
)

TASK163_SCHEMA_VERSION = "task163.schema.v1"
TASK163_VERSION = "task163.v1"
TASK163_IMPLEMENTATION_SOFTWARE_VERSION = "task163.local-implementation.v1"
TASK163_SOURCE_DEFINITION_ID = "TASK163-SOURCE-DEFINITION-R6-ISSUE-234"
TASK163_RAW_PROJECTION_SCHEMA_VERSION = "task163.raw-projection.v1"
TASK163_RAW_BOUNDARY_SCHEMA_VERSION = "task163.raw-boundary-blocked.v1"
TASK163_TYPED_BLOCKED_SCHEMA_VERSION = "task163.typed-blocked.v1"
TASK163_RAW_MAX_DEPTH = 16
TASK163_RAW_MAX_NODES = 512
TASK163_RAW_MAX_SCALAR_BYTES = 16_384
TASK163_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE = TASK163_RAW_MAX_SCALAR_BYTES + 1


class Task163ValidationStatus(StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class Task163FailureStage(StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    TYPED_VALIDATION = "TYPED_VALIDATION"
    TASK162_REPLAY = "TASK162_REPLAY"
    RATING_COMPOSITION = "RATING_COMPOSITION"
    RATING_APPLICABILITY = "RATING_APPLICABILITY"
    RATING_COMPLETENESS = "RATING_COMPLETENESS"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


class Task163FailureCode(StrEnum):
    INVALID_REQUEST_TYPE = "INVALID_REQUEST_TYPE"
    INVALID_REQUEST_SCHEMA = "INVALID_REQUEST_SCHEMA"
    UNSUPPORTED_TASK163_VERSION = "UNSUPPORTED_TASK163_VERSION"
    SOURCE_DEFINITION_ID_MISMATCH = "SOURCE_DEFINITION_ID_MISMATCH"
    UNSUPPORTED_RAW_VALUE = "UNSUPPORTED_RAW_VALUE"
    RAW_UNICODE_ENCODING_FAILURE = "RAW_UNICODE_ENCODING_FAILURE"
    RAW_DEPTH_LIMIT_EXCEEDED = "RAW_DEPTH_LIMIT_EXCEEDED"
    RAW_NODE_LIMIT_EXCEEDED = "RAW_NODE_LIMIT_EXCEEDED"
    RAW_SCALAR_BYTE_LIMIT_EXCEEDED = "RAW_SCALAR_BYTE_LIMIT_EXCEEDED"
    INVALID_TASK162_RESULT = "INVALID_TASK162_RESULT"
    INVALID_TASK162_REPLAY_EVIDENCE = "INVALID_TASK162_REPLAY_EVIDENCE"
    TASK162_PRODUCER_VERIFICATION_FAILED = "TASK162_PRODUCER_VERIFICATION_FAILED"
    TASK162_IDENTITY_REPLAY_FAILED = "TASK162_IDENTITY_REPLAY_FAILED"
    TASK162_NOT_APPLICABLE = "TASK162_NOT_APPLICABLE"
    TASK162_NOT_COMPLETE = "TASK162_NOT_COMPLETE"
    TASK162_PROVENANCE_INVALID = "TASK162_PROVENANCE_INVALID"
    RATING_COMPOSITION_INCOMPLETE = "RATING_COMPOSITION_INCOMPLETE"
    RATING_APPLICABILITY_FAILED = "RATING_APPLICABILITY_FAILED"
    RATING_COMPLETENESS_FAILED = "RATING_COMPLETENESS_FAILED"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    IDENTITY_REPLAY_FAILED = "IDENTITY_REPLAY_FAILED"


class Task163RawProjectionKind(StrEnum):
    NONE = "NONE"
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    ENUM_LITERAL = "ENUM_LITERAL"
    TASK162_RESULT_IDENTITY = "TASK162_RESULT_IDENTITY"
    TASK162_REPLAY_EVIDENCE_IDENTITY = "TASK162_REPLAY_EVIDENCE_IDENTITY"
    TASK160_RESULT_IDENTITY = "TASK160_RESULT_IDENTITY"
    TASK161_RESULT_IDENTITY = "TASK161_RESULT_IDENTITY"
    TASK038_RESULT_IDENTITY = "TASK038_RESULT_IDENTITY"
    CROSS_PRODUCER_BINDING_IDENTITY = "CROSS_PRODUCER_BINDING_IDENTITY"
    CASE_AUTHORITY_IDENTITY = "CASE_AUTHORITY_IDENTITY"
    SEQUENCE = "SEQUENCE"
    RECORD = "RECORD"
    UNSUPPORTED_OBJECT = "UNSUPPORTED_OBJECT"
    LIMIT_MARKER = "LIMIT_MARKER"


class Task163ApplicabilityStatus(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Task163ApplicabilityCheckName(StrEnum):
    TASK162_SUCCESS_ACCEPTED = "TASK162_SUCCESS_ACCEPTED"
    TASK162_APPLICABILITY_ACCEPTED = "TASK162_APPLICABILITY_ACCEPTED"
    TASK162_COMPLETENESS_ACCEPTED = "TASK162_COMPLETENESS_ACCEPTED"
    TASK162_IDENTITY_ACCEPTED = "TASK162_IDENTITY_ACCEPTED"
    TASK162_PROVENANCE_ACCEPTED = "TASK162_PROVENANCE_ACCEPTED"
    RATING_COMPOSITION_BINDING_COMPLETE = "RATING_COMPOSITION_BINDING_COMPLETE"


class Task163CheckStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"


class Task163CompletenessStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class Task163CompletenessField(StrEnum):
    ACCEPTED_TASK162_EVIDENCE = "ACCEPTED_TASK162_EVIDENCE"
    TASK162_IDENTITY_REPLAY_COMPLETE = "TASK162_IDENTITY_REPLAY_COMPLETE"
    TASK162_PROVENANCE_REPLAY_COMPLETE = "TASK162_PROVENANCE_REPLAY_COMPLETE"
    RATING_PERFORMANCE_PROJECTION = "RATING_PERFORMANCE_PROJECTION"
    HEAT_DUTY_PROJECTION = "HEAT_DUTY_PROJECTION"
    HOT_OUTLET_PROJECTION = "HOT_OUTLET_PROJECTION"
    COLD_OUTLET_PROJECTION = "COLD_OUTLET_PROJECTION"
    ENERGY_BALANCE_EVIDENCE = "ENERGY_BALANCE_EVIDENCE"
    TERMINAL_TEMPERATURE_EVIDENCE = "TERMINAL_TEMPERATURE_EVIDENCE"
    RATING_APPLICABILITY_LEDGER = "RATING_APPLICABILITY_LEDGER"
    RATING_COMPLETENESS_EVIDENCE = "RATING_COMPLETENESS_EVIDENCE"
    DEFERRED_CAPABILITY_DECLARATION = "DEFERRED_CAPABILITY_DECLARATION"
    TASK163_PROVENANCE = "TASK163_PROVENANCE"
    TASK163_RESULT_IDENTITY = "TASK163_RESULT_IDENTITY"


class Task163DeferredStatus(StrEnum):
    DECLARED = "DECLARED"


class Task163DeferredCapability(StrEnum):
    LMTD = "LMTD"
    LMTD_CORRECTION_FACTOR = "LMTD_CORRECTION_FACTOR"
    NEW_HEAT_TRANSFER_CORRELATIONS = "NEW_HEAT_TRANSFER_CORRELATIONS"
    NEW_PRESSURE_DROP_CORRELATIONS = "NEW_PRESSURE_DROP_CORRELATIONS"
    NEW_OVERALL_U_UA = "NEW_OVERALL_U_UA"
    NEW_NTU_RELATION = "NEW_NTU_RELATION"
    NEW_P_EFFECTIVENESS_RELATION = "NEW_P_EFFECTIVENESS_RELATION"
    NEW_HEAT_DUTY_FORMULA = "NEW_HEAT_DUTY_FORMULA"
    NEW_OUTLET_TEMPERATURE_FORMULA = "NEW_OUTLET_TEMPERATURE_FORMULA"
    NEW_ENERGY_BALANCE_FORMULA = "NEW_ENERGY_BALANCE_FORMULA"
    NEW_TERMINAL_TEMPERATURE_FORMULA = "NEW_TERMINAL_TEMPERATURE_FORMULA"
    VARIABLE_PROPERTY_ITERATION = "VARIABLE_PROPERTY_ITERATION"
    TWO_PHASE_BEHAVIOR = "TWO_PHASE_BEHAVIOR"
    WALL_TEMPERATURE_ITERATION = "WALL_TEMPERATURE_ITERATION"
    THERMAL_SIZING = "THERMAL_SIZING"
    GEOMETRY_OPTIMIZATION = "GEOMETRY_OPTIMIZATION"
    MECHANICAL_DESIGN = "MECHANICAL_DESIGN"
    COST_OPTIMIZATION = "COST_OPTIMIZATION"
    PERSISTENCE = "PERSISTENCE"
    UI_REPORTING = "UI_REPORTING"
    TASK164_RELEASE_ACCEPTANCE = "TASK164_RELEASE_ACCEPTANCE"


@dataclass(frozen=True, slots=True)
class Task163Request:
    schema_version: str
    task163_version: str
    source_definition_id: str
    task162_result: Task162Result
    task162_success_replay_evidence: Task162SuccessReplayEvidence
    request_metadata: tuple[tuple[str, str], ...]


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
class Task162ResultIdentityProjection:
    schema_version: str
    task162_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class Task162SuccessReplayEvidenceIdentityProjection:
    evidence_schema_version: str
    task162_schema_version: str
    task162_version: str
    task162_implementation_software_version: str
    task162_source_definition_id: str
    task162_result_hash: str
    task162_result_id: str
    task160_result_identity_projection: Task160ResultIdentityProjection
    task161_result_identity_projection: Task161ResultIdentityProjection
    task038_result_identity_projection: Task038ResultIdentityProjection
    original_case_authority_identity: str
    original_task162_request_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Task163Task162Evidence:
    task162_result_identity_projection: Task162ResultIdentityProjection
    task162_success_replay_evidence_identity_projection: (
        Task162SuccessReplayEvidenceIdentityProjection
    )


@dataclass(frozen=True, slots=True)
class Task163RatingPerformanceProjection:
    selected_method_identity: Task162SelectedMethodIdentity
    selected_baffle_relation: str
    ntu: Decimal
    r_source: Decimal
    p_source: Decimal
    epsilon: Decimal


@dataclass(frozen=True, slots=True)
class Task163HeatDutyProjection:
    q_max: Decimal
    q_method: Decimal
    q_hot: Decimal
    q_cold: Decimal


@dataclass(frozen=True, slots=True)
class Task163OutletTemperatureProjection:
    hot_outlet_temperature: Decimal
    cold_outlet_temperature: Decimal


@dataclass(frozen=True, slots=True)
class Task163Applicability:
    status: Task163ApplicabilityStatus
    checks: tuple[tuple[Task163ApplicabilityCheckName, Task163CheckStatus], ...]


@dataclass(frozen=True, slots=True)
class Task163Completeness:
    status: Task163CompletenessStatus
    required_fields: tuple[Task163CompletenessField, ...]


@dataclass(frozen=True, slots=True)
class Task163DeferredCapabilities:
    status: Task163DeferredStatus
    capabilities: tuple[Task163DeferredCapability, ...]


@dataclass(frozen=True, slots=True)
class Task163Blocker:
    code: Task163FailureCode
    stage: Task163FailureStage
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Task163Warning:
    code: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class Task163ProvenanceSemanticInputs:
    source_authority_payload_hash: str
    task162_result_evidence_payload_hash: str
    rating_composition_payload_hash: str
    applicability_payload_hash: str
    completeness_payload_hash: str


@dataclass(frozen=True, slots=True)
class Task163Provenance:
    provenance_hash: str
    graph: ProvenanceGraph


@dataclass(frozen=True, slots=True)
class Task163PreResultIdentityInputs:
    schema_version: str
    task163_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task162_evidence: Task163Task162Evidence
    rating_performance_projection: Task163RatingPerformanceProjection
    heat_duty_projection: Task163HeatDutyProjection
    outlet_temperature_projection: Task163OutletTemperatureProjection
    energy_balance_evidence: Task162EnergyBalanceEvidence
    terminal_temperature_evidence: Task162TerminalClosureEvidence
    applicability: Task163Applicability
    completeness: Task163Completeness
    deferred_capabilities: Task163DeferredCapabilities
    warnings_normalized: tuple[Task163Warning, ...]
    blockers_normalized: tuple[Task163Blocker, ...]
    provenance_semantic_inputs: Task163ProvenanceSemanticInputs


@dataclass(frozen=True, slots=True)
class Task163Result:
    schema_version: str
    task163_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task162_evidence: Task163Task162Evidence
    rating_performance_projection: Task163RatingPerformanceProjection
    heat_duty_projection: Task163HeatDutyProjection
    outlet_temperature_projection: Task163OutletTemperatureProjection
    energy_balance_evidence: Task162EnergyBalanceEvidence
    terminal_temperature_evidence: Task162TerminalClosureEvidence
    applicability: Task163Applicability
    completeness: Task163Completeness
    deferred_capabilities: Task163DeferredCapabilities
    warnings: tuple[Task163Warning, ...]
    blockers: tuple[Task163Blocker, ...]
    provenance_semantic_inputs: Task163ProvenanceSemanticInputs
    provenance: Task163Provenance
    result_hash: str
    result_id: UUID


@dataclass(frozen=True, slots=True)
class Task163TypedBlockedResult:
    schema_version: str
    task163_version: str
    implementation_software_version: str
    failure_stage: Task163FailureStage
    request_hash: str
    task162_result_identity_or_none: Task162ResultIdentityProjection | None
    blockers: tuple[Task163Blocker, ...]
    warnings: tuple[Task163Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task163RawProjectionNode:
    field_name: str
    kind: Task163RawProjectionKind
    type_identity: str | None
    scalar_payload: str | None
    children: tuple[Task163RawProjectionNode, ...]

    def __post_init__(self) -> None:
        if type(self.field_name) is not str:
            raise TypeError("field_name must be exact str")
        if type(self.kind) is not Task163RawProjectionKind:
            raise TypeError("kind must be exact Task163RawProjectionKind")
        if self.kind is Task163RawProjectionKind.LIMIT_MARKER:
            if (
                self.field_name != "__TASK163_LIMIT_MARKER__"
                or self.type_identity is not None
                or self.scalar_payload
                not in {
                    "RAW_UNICODE_ENCODING_FAILURE",
                    "RAW_DEPTH_LIMIT_EXCEEDED",
                    "RAW_NODE_LIMIT_EXCEEDED",
                    "RAW_SCALAR_BYTE_LIMIT_EXCEEDED",
                    "UNSUPPORTED_RAW_VALUE",
                }
                or self.children != ()
            ):
                raise ValueError("invalid TASK163 limit marker")
            return
        if type(self.type_identity) not in (str, type(None)):
            raise TypeError("type_identity must be str or None")
        if type(self.scalar_payload) not in (str, type(None)):
            raise TypeError("scalar_payload must be str or None")
        if type(self.children) is not tuple or any(
            type(child) is not Task163RawProjectionNode for child in self.children
        ):
            raise TypeError("children must be a tuple of exact raw nodes")


@dataclass(frozen=True, slots=True)
class Task163RawRequestProjection:
    schema_version: str
    root: Task163RawProjectionNode


@dataclass(frozen=True, slots=True)
class Task163RawBoundaryBlockedResult:
    schema_version: str
    task163_version: str
    implementation_software_version: str
    failure_stage: Task163FailureStage
    raw_request_projection: Task163RawRequestProjection
    raw_request_projection_hash: str
    blockers: tuple[Task163Blocker, ...]
    warnings: tuple[Task163Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task163ValidationResult:
    status: Task163ValidationStatus
    raw_boundary_blocked: Task163RawBoundaryBlockedResult | None = None
    typed_blocked: Task163TypedBlockedResult | None = None
    valid: Task163Result | None = None

    def __post_init__(self) -> None:
        values = (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        if sum(value is not None for value in values) != 1:
            raise ValueError("exactly one TASK163 result branch must be populated")
        expected = {
            Task163ValidationStatus.RAW_BOUNDARY_BLOCKED: self.raw_boundary_blocked,
            Task163ValidationStatus.TYPED_BLOCKED: self.typed_blocked,
            Task163ValidationStatus.VALID: self.valid,
        }[self.status]
        if expected is None:
            raise ValueError("status does not match populated TASK163 branch")


__all__ = [name for name in globals() if name.startswith("TASK163_") or name.startswith("Task163")]
