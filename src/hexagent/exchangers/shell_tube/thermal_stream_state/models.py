"""Immutable TASK160 thermal-stream state models.

The module is deliberately task-local.  It owns the two-stream authority
records used by TASK160 and does not import a property provider or any
downstream exchanger-performance model.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from re import fullmatch
from typing import Any, ClassVar
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph

TASK160_SOURCE_DEFINITION_ID = "TASK160-SOURCE-DEFINITION-R1-ISSUE-221"
TASK160_RESULT_ID_NAMESPACE = "a1600000-0000-5000-8000-000000000160"
TASK160_SCHEMA_VERSION = "task160.schema.v1"
TASK160_VERSION = "task160.v1"
TASK160_IMPLEMENTATION_SOFTWARE_VERSION = "task160.local-implementation.v1"
RAW_PROJECTION_SCHEMA_VERSION = "task160.raw-projection.v1"

TASK160_DECIMAL_PRECISION = 160
TASK160_DECIMAL_MAX_INPUT_SIGNIFICANT_DIGITS = 79
TASK160_DECIMAL_MIN_ADJUSTED_EXPONENT = -499000
TASK160_DECIMAL_MAX_ADJUSTED_EXPONENT = 499000

TASK160_DEFERRED_CAPABILITIES: tuple[str, ...] = (
    "TASK161_PERFORMANCE_METHOD",
    "TASK162_THERMAL_CLOSURE",
    "TASK163_COMPOSITION",
)


class SideBinding(StrEnum):
    TUBE_SIDE = "TUBE_SIDE"
    SHELL_SIDE = "SHELL_SIDE"


class Task160PhaseAssertion(StrEnum):
    SINGLE_PHASE_LIQUID = "SINGLE_PHASE_LIQUID"
    SINGLE_PHASE_GAS = "SINGLE_PHASE_GAS"


class ThermalRole(StrEnum):
    HOT = "HOT"
    COLD = "COLD"


class PropertyEvaluationBasis(StrEnum):
    RECORDED_PROPERTY_SNAPSHOT = "RECORDED_PROPERTY_SNAPSHOT"


class PropertyEvaluationQueryType(StrEnum):
    TEMPERATURE_ONLY = "TEMPERATURE_ONLY"
    TEMPERATURE_AND_PRESSURE = "TEMPERATURE_AND_PRESSURE"


class ConstructionFamily(StrEnum):
    FIXED_TUBESHEET = "FIXED_TUBESHEET"


class PropertySnapshotIdentityScheme(StrEnum):
    SHA256_HEX = "SHA256_HEX"
    OPAQUE_REPRODUCIBLE = "OPAQUE_REPRODUCIBLE"


class ValidationStatus(StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class FailureStage(StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    STRICT_VALIDATION = "STRICT_VALIDATION"
    APPLICABILITY = "APPLICABILITY"
    COMPLETENESS = "COMPLETENESS"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


class CalculationRunScope(StrEnum):
    SUCCESS = "SUCCESS"
    TYPED_BLOCKED = "TYPED_BLOCKED"


class SourceAuthorityStatus(StrEnum):
    FROZEN = "FROZEN"


class RawProjectionKind(StrEnum):
    NONE = "NONE"
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    INVALID_NUMERIC_LITERAL = "INVALID_NUMERIC_LITERAL"
    ENUM_LITERAL = "ENUM_LITERAL"
    SEQUENCE = "SEQUENCE"
    RECORD = "RECORD"


class ApplicabilityStatus(StrEnum):
    APPLICABLE = "APPLICABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class CompletenessStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class ApplicabilityCheckId(StrEnum):
    A01_TWO_STREAMS = "A01"
    A02_EXACTLY_ONE_TUBE_SIDE = "A02"
    A03_EXACTLY_ONE_SHELL_SIDE = "A03"
    A04_SINGLE_PHASE_AUTHORITY = "A04"
    A05_CONSTANT_PROPERTY_SNAPSHOT = "A05"
    A06_FIXED_GEOMETRY_V05_ENVELOPE = "A06"
    A07_FINITE_VALID_INLET_STATE = "A07"
    A08_POSITIVE_MASS_FLOW = "A08"
    A09_POSITIVE_CP = "A09"
    A10_APPROVED_PROPERTY_AUTHORITY = "A10"
    A11_COMPLETE_PROVENANCE = "A11"


class CompletenessCheckId(StrEnum):
    C01_STREAM_RECORD_COUNT = "C01"
    C02_SIDE_BINDINGS = "C02"
    C03_STREAM_IDENTITIES = "C03"
    C04_FLUID_SERVICE_IDENTITIES = "C04"
    C05_PHASE_ASSERTIONS = "C05"
    C06_RATING_INLET_TEMPERATURES = "C06"
    C07_MASS_FLOW_AUTHORITIES = "C07"
    C08_CP_AUTHORITIES = "C08"
    C09_HEAT_CAPACITY_RATES = "C09"
    C10_CONDITIONAL_PRESSURE_CONTEXTS = "C10"
    C11_PROPERTY_SOURCE_IDENTITIES = "C11"
    C12_PROPERTY_SOURCE_VERSIONS = "C12"
    C13_PROPERTY_SNAPSHOT_IDENTITIES = "C13"
    C14_PROPERTY_EVALUATION_CONTEXTS = "C14"
    C15_PROVENANCE = "C15"
    C16_DETERMINISTIC_NON_COMPLETENESS_IDENTITY_INPUT_READINESS = "C16"


def _is_finite_decimal(value: object) -> bool:
    return isinstance(value, Decimal) and value.is_finite()


def _require_nonempty(value: object, name: str) -> None:
    if type(value) is not str or not value:
        raise ValueError(f"{name} must be a non-empty string")


def _require_decimal(value: object, name: str, *, positive: bool = False) -> None:
    if not _is_finite_decimal(value):
        raise ValueError(f"{name} must be a finite Decimal")
    assert isinstance(value, Decimal)
    if len(value.as_tuple().digits) > TASK160_DECIMAL_MAX_INPUT_SIGNIFICANT_DIGITS:
        raise ValueError(f"{name} exceeds TASK160 significant-digit limit")
    if not (
        TASK160_DECIMAL_MIN_ADJUSTED_EXPONENT
        <= value.adjusted()
        <= TASK160_DECIMAL_MAX_ADJUSTED_EXPONENT
    ):
        raise ValueError(f"{name} adjusted exponent is outside TASK160 domain")
    if positive and value <= Decimal(0):
        raise ValueError(f"{name} must be strictly positive")


def _require_hash(value: object, name: str) -> None:
    if type(value) is not str or fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _require_tuple_strings(
    values: object,
    name: str,
    *,
    nonempty: bool = False,
    sorted_required: bool = True,
) -> None:
    if not isinstance(values, tuple) or any(type(item) is not str or not item for item in values):
        raise ValueError(f"{name} must be a tuple of non-empty strings")
    if nonempty and not values:
        raise ValueError(f"{name} must not be empty")
    if len(values) != len(set(values)):
        raise ValueError(f"{name} must not contain duplicates")
    if sorted_required and values != tuple(sorted(values)):
        raise ValueError(f"{name} must be lexically sorted")


@dataclass(frozen=True)
class Task160RawPropertyEvaluationContext:
    evaluation_basis: Any = None
    query_type: Any = None
    evaluation_temperature_K: Any = None
    evaluation_pressure_Pa_absolute: Any = None
    context_identity: Any = None


@dataclass(frozen=True)
class Task160RawPropertySnapshotIdentity:
    scheme: Any = None
    value: Any = None


@dataclass(frozen=True)
class Task160RawPropertySnapshotInput:
    specific_heat_J_kg_K: Any = None
    property_source_identity: Any = None
    property_source_version: Any = None
    property_snapshot_identity: Any = None
    property_evaluation_context: Any = None


@dataclass(frozen=True)
class Task160RawProvenance:
    producer_identity: Any = None
    upstream_identity_hashes: Any = None
    source_evidence_refs: Any = None
    adapter_evidence_refs: Any = None


@dataclass(frozen=True)
class Task160RawAdapterEvidence:
    adapter_id: Any = None
    source_task_id: Any = None
    source_result_identity: Any = None
    admitted_fields: Any = None
    rejected_fields: Any = None
    source_evidence_refs: Any = None
    evidence_hash: Any = None


@dataclass(frozen=True)
class Task160RawStreamInput:
    stream_id: Any = None
    side_binding: Any = None
    fluid_or_service_identity: Any = None
    phase_assertion: Any = None
    inlet_temperature_K: Any = None
    inlet_pressure_Pa_absolute: Any = None
    mass_flow_kg_s: Any = None
    property_snapshot: Any = None
    provenance: Any = None


@dataclass(frozen=True)
class Task160RawEnvelopeAuthority:
    construction_family: Any = None
    shell_pass_count: Any = None
    tube_pass_count: Any = None
    authority_source_identity: Any = None
    authority_source_version: Any = None
    authority_identity: Any = None
    evidence_refs: Any = None


@dataclass(frozen=True)
class Task160RawRequest:
    schema_version: Any = None
    task160_version: Any = None
    implementation_software_version: Any = None
    stream_records: Any = None
    envelope_authority: Any = None
    adapter_evidence: Any = None
    deferred_capabilities: Any = None
    provenance: Any = None


@dataclass(frozen=True)
class RawProjectionNode:
    field_name: str
    kind: RawProjectionKind
    scalar_payload: str | None
    children: tuple[RawProjectionNode, ...]

    _SCALAR_KINDS: ClassVar[frozenset[RawProjectionKind]] = frozenset(
        {
            RawProjectionKind.NONE,
            RawProjectionKind.STRING,
            RawProjectionKind.INTEGER,
            RawProjectionKind.DECIMAL,
            RawProjectionKind.INVALID_NUMERIC_LITERAL,
            RawProjectionKind.ENUM_LITERAL,
        }
    )

    def __post_init__(self) -> None:
        if type(self.field_name) is not str or not self.field_name:
            raise ValueError("field_name must be non-empty str")
        if not isinstance(self.kind, RawProjectionKind):
            raise ValueError("kind must be RawProjectionKind")
        if type(self.children) is not tuple or any(
            not isinstance(item, RawProjectionNode) for item in self.children
        ):
            raise ValueError("children must be a tuple of RawProjectionNode")
        if self.kind in self._SCALAR_KINDS:
            if self.children != ():
                raise ValueError("scalar raw projection nodes cannot have children")
            if self.kind is RawProjectionKind.NONE and self.scalar_payload is not None:
                raise ValueError("NONE raw projection nodes have no scalar payload")
            if self.kind is not RawProjectionKind.NONE and type(self.scalar_payload) is not str:
                raise ValueError("scalar raw projection nodes require a string payload")
        else:
            if self.scalar_payload is not None:
                raise ValueError("container raw projection nodes have no scalar payload")
            if self.kind is RawProjectionKind.SEQUENCE:
                expected_names = tuple(f"item-{index:06d}" for index in range(len(self.children)))
                if tuple(item.field_name for item in self.children) != expected_names:
                    raise ValueError("sequence children must use canonical item names")
            elif len({item.field_name for item in self.children}) != len(self.children):
                raise ValueError("record children must have unique field names")


@dataclass(frozen=True)
class Task160RawRequestProjection:
    schema_version: str
    root: RawProjectionNode

    def __post_init__(self) -> None:
        if self.schema_version != RAW_PROJECTION_SCHEMA_VERSION:
            raise ValueError("unsupported raw projection schema version")


@dataclass(frozen=True)
class PropertySnapshotIdentity:
    scheme: PropertySnapshotIdentityScheme
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.scheme, PropertySnapshotIdentityScheme):
            raise ValueError("scheme must be PropertySnapshotIdentityScheme")
        _require_nonempty(self.value, "value")
        if self.scheme is PropertySnapshotIdentityScheme.SHA256_HEX:
            _require_hash(self.value, "value")


@dataclass(frozen=True)
class PropertyEvaluationContext:
    evaluation_basis: PropertyEvaluationBasis
    query_type: PropertyEvaluationQueryType
    evaluation_temperature_K: Decimal
    evaluation_pressure_Pa_absolute: Decimal | None
    context_identity: str

    def __post_init__(self) -> None:
        if self.evaluation_basis is not PropertyEvaluationBasis.RECORDED_PROPERTY_SNAPSHOT:
            raise ValueError("only recorded property snapshots are supported")
        _require_decimal(self.evaluation_temperature_K, "evaluation_temperature_K", positive=True)
        _require_nonempty(self.context_identity, "context_identity")
        pressure = self.evaluation_pressure_Pa_absolute
        if self.query_type is PropertyEvaluationQueryType.TEMPERATURE_ONLY:
            if pressure is not None:
                raise ValueError("temperature-only context cannot contain pressure")
        elif self.query_type is PropertyEvaluationQueryType.TEMPERATURE_AND_PRESSURE:
            _require_decimal(pressure, "evaluation_pressure_Pa_absolute", positive=True)
        else:
            raise ValueError("unsupported property evaluation query type")


@dataclass(frozen=True)
class Task160PropertySnapshot:
    specific_heat_J_kg_K: Decimal
    property_source_identity: str
    property_source_version: str
    property_snapshot_identity: PropertySnapshotIdentity
    property_evaluation_context: PropertyEvaluationContext

    def __post_init__(self) -> None:
        _require_decimal(self.specific_heat_J_kg_K, "specific_heat_J_kg_K", positive=True)
        _require_nonempty(self.property_source_identity, "property_source_identity")
        _require_nonempty(self.property_source_version, "property_source_version")
        if not isinstance(self.property_snapshot_identity, PropertySnapshotIdentity):
            raise ValueError("property_snapshot_identity has invalid type")
        if not isinstance(self.property_evaluation_context, PropertyEvaluationContext):
            raise ValueError("property_evaluation_context has invalid type")


@dataclass(frozen=True)
class Task160EnvelopeAuthority:
    construction_family: ConstructionFamily
    shell_pass_count: int
    tube_pass_count: int
    authority_source_identity: str
    authority_source_version: str
    authority_identity: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.construction_family is not ConstructionFamily.FIXED_TUBESHEET:
            raise ValueError("unsupported construction family")
        if type(self.shell_pass_count) is not int or type(self.tube_pass_count) is not int:
            raise ValueError("pass counts must be int")
        if self.shell_pass_count != 1 or self.tube_pass_count != 1:
            raise ValueError("TASK160 v0.5 supports only a fixed tubesheet 1x1 envelope")
        _require_nonempty(self.authority_source_identity, "authority_source_identity")
        _require_nonempty(self.authority_source_version, "authority_source_version")
        _require_nonempty(self.authority_identity, "authority_identity")
        _require_tuple_strings(self.evidence_refs, "evidence_refs", nonempty=True)


@dataclass(frozen=True)
class Task160ProvenanceInputs:
    producer_identity: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]
    source_evidence_refs: tuple[str, ...]
    adapter_evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        _require_tuple_strings(self.producer_identity, "producer_identity")
        _require_tuple_strings(self.upstream_identity_hashes, "upstream_identity_hashes")
        for value in self.upstream_identity_hashes:
            _require_hash(value, "upstream_identity_hash")
        _require_tuple_strings(self.source_evidence_refs, "source_evidence_refs")
        _require_tuple_strings(self.adapter_evidence_refs, "adapter_evidence_refs")


@dataclass(frozen=True)
class RatingStreamInput:
    stream_id: str
    side_binding: SideBinding
    fluid_or_service_identity: str
    phase_assertion: Task160PhaseAssertion
    inlet_temperature_K: Decimal
    inlet_pressure_Pa_absolute: Decimal | None
    mass_flow_kg_s: Decimal
    property_snapshot: Task160PropertySnapshot
    provenance_inputs: Task160ProvenanceInputs

    def __post_init__(self) -> None:
        _require_nonempty(self.stream_id, "stream_id")
        if not isinstance(self.side_binding, SideBinding):
            raise ValueError("side_binding has invalid type")
        _require_nonempty(self.fluid_or_service_identity, "fluid_or_service_identity")
        if not isinstance(self.phase_assertion, Task160PhaseAssertion):
            raise ValueError("phase_assertion has invalid type")
        _require_decimal(self.inlet_temperature_K, "inlet_temperature_K", positive=True)
        if self.inlet_pressure_Pa_absolute is not None:
            _require_decimal(
                self.inlet_pressure_Pa_absolute, "inlet_pressure_Pa_absolute", positive=True
            )
        _require_decimal(self.mass_flow_kg_s, "mass_flow_kg_s", positive=True)
        if not isinstance(self.property_snapshot, Task160PropertySnapshot):
            raise ValueError("property_snapshot has invalid type")
        if not isinstance(self.provenance_inputs, Task160ProvenanceInputs):
            raise ValueError("provenance_inputs has invalid type")
        if (
            self.property_snapshot.property_evaluation_context.query_type
            is PropertyEvaluationQueryType.TEMPERATURE_AND_PRESSURE
            and self.inlet_pressure_Pa_absolute is None
        ):
            raise ValueError("inlet pressure is required by the property evaluation context")


@dataclass(frozen=True)
class ValidatedRatingStreamState:
    input: RatingStreamInput

    def __post_init__(self) -> None:
        if not isinstance(self.input, RatingStreamInput):
            raise ValueError("input must be RatingStreamInput")

    @property
    def stream_id(self) -> str:
        return self.input.stream_id

    @property
    def side_binding(self) -> SideBinding:
        return self.input.side_binding

    @property
    def inlet_temperature_K(self) -> Decimal:
        return self.input.inlet_temperature_K


@dataclass(frozen=True)
class RoleResolvedRatingStream:
    input_state: ValidatedRatingStreamState
    thermal_role: ThermalRole

    def __post_init__(self) -> None:
        if not isinstance(self.input_state, ValidatedRatingStreamState):
            raise ValueError("input_state must be ValidatedRatingStreamState")
        if not isinstance(self.thermal_role, ThermalRole):
            raise ValueError("thermal_role has invalid type")


@dataclass(frozen=True)
class CapacityRatedStream:
    role_resolved_stream: RoleResolvedRatingStream
    heat_capacity_rate_W_K: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.role_resolved_stream, RoleResolvedRatingStream):
            raise ValueError("role_resolved_stream has invalid type")
        _require_decimal(self.heat_capacity_rate_W_K, "heat_capacity_rate_W_K", positive=True)

    @property
    def input_state(self) -> ValidatedRatingStreamState:
        return self.role_resolved_stream.input_state

    @property
    def thermal_role(self) -> ThermalRole:
        return self.role_resolved_stream.thermal_role

    @property
    def stream_id(self) -> str:
        return self.input_state.stream_id

    @property
    def side_binding(self) -> SideBinding:
        return self.input_state.side_binding


@dataclass(frozen=True)
class Task160AdapterEvidence:
    adapter_id: str
    source_task_id: str
    source_result_identity: str | None
    admitted_fields: tuple[str, ...]
    rejected_fields: tuple[str, ...]
    source_evidence_refs: tuple[str, ...]
    evidence_hash: str

    def __post_init__(self) -> None:
        _require_nonempty(self.adapter_id, "adapter_id")
        _require_nonempty(self.source_task_id, "source_task_id")
        if self.source_result_identity is not None:
            _require_nonempty(self.source_result_identity, "source_result_identity")
        # These two tuples are an exact adapter vocabulary, not set-like
        # collections.  Their schema order is part of the canonical record.
        _require_tuple_strings(
            self.admitted_fields, "admitted_fields", nonempty=True, sorted_required=False
        )
        _require_tuple_strings(
            self.rejected_fields, "rejected_fields", nonempty=True, sorted_required=False
        )
        _require_tuple_strings(self.source_evidence_refs, "source_evidence_refs", nonempty=True)
        _require_hash(self.evidence_hash, "evidence_hash")


@dataclass(frozen=True)
class Task160Request:
    schema_version: str
    task160_version: str
    implementation_software_version: str
    stream_records: tuple[RatingStreamInput, RatingStreamInput]
    envelope_authority: Task160EnvelopeAuthority
    adapter_evidence: tuple[Task160AdapterEvidence, ...]
    deferred_capabilities: tuple[str, ...]
    provenance_inputs: Task160ProvenanceInputs

    def __post_init__(self) -> None:
        _require_nonempty(self.schema_version, "schema_version")
        _require_nonempty(self.task160_version, "task160_version")
        _require_nonempty(self.implementation_software_version, "implementation_software_version")
        if not isinstance(self.stream_records, tuple) or len(self.stream_records) != 2:
            raise ValueError("stream_records must contain exactly two records")
        if any(not isinstance(item, RatingStreamInput) for item in self.stream_records):
            raise ValueError("stream_records have invalid type")
        if not isinstance(self.envelope_authority, Task160EnvelopeAuthority):
            raise ValueError("envelope_authority has invalid type")
        if not isinstance(self.adapter_evidence, tuple):
            raise ValueError("adapter_evidence must be tuple")
        if any(not isinstance(item, Task160AdapterEvidence) for item in self.adapter_evidence):
            raise ValueError("adapter_evidence has invalid type")
        if not isinstance(self.deferred_capabilities, tuple):
            raise ValueError("deferred_capabilities must be tuple")
        _require_tuple_strings(self.deferred_capabilities, "deferred_capabilities", nonempty=True)
        if not isinstance(self.provenance_inputs, Task160ProvenanceInputs):
            raise ValueError("provenance_inputs has invalid type")


@dataclass(frozen=True)
class Task160Blocker:
    code: str
    stage: FailureStage
    field_path: str
    evidence_refs: tuple[str, ...]
    details: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_nonempty(self.code, "code")
        if not isinstance(self.stage, FailureStage):
            raise ValueError("stage has invalid type")
        if type(self.field_path) is not str:
            raise ValueError("field_path must be str")
        _require_tuple_strings(self.evidence_refs, "evidence_refs")
        if not isinstance(self.details, tuple):
            raise ValueError("details must be tuple")
        for pair in self.details:
            if (
                not isinstance(pair, tuple)
                or len(pair) != 2
                or any(type(x) is not str for x in pair)
            ):
                raise ValueError("details must contain string pairs")


@dataclass(frozen=True)
class Task160Warning:
    """Compatibility value object; TASK160 emits no warnings in v1."""

    code: str
    field_path: str = ""
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApplicabilityCheck:
    check_id: ApplicabilityCheckId
    passed: bool
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    details: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ApplicabilityLedger:
    status: ApplicabilityStatus
    checks: tuple[ApplicabilityCheck, ...]
    blockers: tuple[Task160Blocker, ...]


@dataclass(frozen=True)
class CompletenessCheck:
    check_id: CompletenessCheckId
    passed: bool
    blocker_codes: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    details: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CompletenessLedger:
    status: CompletenessStatus
    checks: tuple[CompletenessCheck, ...]
    blockers: tuple[Task160Blocker, ...]


@dataclass(frozen=True)
class Task160PreResultIdentityInputs:
    request_hash: str
    stream_records: tuple[CapacityRatedStream, CapacityRatedStream]
    envelope_authority: Task160EnvelopeAuthority
    adapter_evidence: tuple[Task160AdapterEvidence, ...]
    deferred_capabilities: tuple[str, ...]
    c_dot_hot_W_K: Decimal
    c_dot_cold_W_K: Decimal
    applicability: ApplicabilityLedger
    warnings: tuple[Task160Warning, ...]
    provenance_inputs: Task160ProvenanceInputs
    source_definition_id: str


@dataclass(frozen=True)
class Task160Provenance:
    producer_identity: tuple[str, ...]
    upstream_identity_hashes: tuple[str, ...]
    source_evidence_refs: tuple[str, ...]
    adapter_evidence_refs: tuple[str, ...]
    graph: ProvenanceGraph
    provenance_hash: str

    def __post_init__(self) -> None:
        _require_tuple_strings(self.producer_identity, "producer_identity", nonempty=True)
        _require_tuple_strings(
            self.upstream_identity_hashes, "upstream_identity_hashes", nonempty=True
        )
        for value in self.upstream_identity_hashes:
            _require_hash(value, "upstream_identity_hash")
        _require_tuple_strings(self.source_evidence_refs, "source_evidence_refs", nonempty=True)
        _require_tuple_strings(self.adapter_evidence_refs, "adapter_evidence_refs", nonempty=True)
        if not isinstance(self.graph, ProvenanceGraph):
            raise ValueError("graph has invalid type")
        if (
            not self.provenance_hash.startswith("sha256:")
            or len(self.provenance_hash) != 71
            or any(char not in "0123456789abcdef" for char in self.provenance_hash[7:])
        ):
            raise ValueError("provenance_hash must be sha256:<64hex>")


@dataclass(frozen=True)
class Task160Result:
    schema_version: str
    task160_version: str
    implementation_software_version: str
    request_hash: str
    stream_records: tuple[CapacityRatedStream, CapacityRatedStream]
    envelope_authority: Task160EnvelopeAuthority
    adapter_evidence: tuple[Task160AdapterEvidence, ...]
    deferred_capabilities: tuple[str, ...]
    c_dot_hot_W_K: Decimal
    c_dot_cold_W_K: Decimal
    applicability: ApplicabilityLedger
    completeness: CompletenessLedger
    warnings: tuple[Task160Warning, ...]
    blockers: tuple[Task160Blocker, ...]
    provenance: Task160Provenance
    result_hash: str
    result_id: UUID

    def __post_init__(self) -> None:
        _require_hash(self.request_hash, "request_hash")
        _require_hash(self.result_hash, "result_hash")
        if type(self.result_id) is not UUID:
            raise ValueError("result_id must be UUID")
        if len(self.stream_records) != 2:
            raise ValueError("result must contain exactly two stream records")
        if self.blockers != ():
            raise ValueError("successful result cannot contain blockers")
        if self.warnings != ():
            raise ValueError("TASK160 warnings are always empty")
        if self.applicability.status is not ApplicabilityStatus.APPLICABLE:
            raise ValueError("successful result must be applicable")
        if self.completeness.status is not CompletenessStatus.COMPLETE:
            raise ValueError("successful result must be complete")

    @property
    def producer_identity(self) -> tuple[str, ...]:
        return self.provenance.producer_identity


@dataclass(frozen=True)
class Task160BlockedResult:
    schema_version: str
    task160_version: str
    implementation_software_version: str
    failure_stage: FailureStage
    request_hash: str
    blockers: tuple[Task160Blocker, ...]
    warnings: tuple[Task160Warning, ...]
    deferred_capabilities: tuple[str, ...]
    producer_identity: tuple[str, ...]
    provenance: Task160Provenance
    blocked_result_hash: str
    blocked_result_id: UUID

    def __post_init__(self) -> None:
        if not self.blockers:
            raise ValueError("typed blocked result requires blockers")
        _require_hash(self.request_hash, "request_hash")
        _require_hash(self.blocked_result_hash, "blocked_result_hash")
        if type(self.blocked_result_id) is not UUID:
            raise ValueError("blocked_result_id must be UUID")
        if self.warnings != ():
            raise ValueError("TASK160 warnings are always empty")


@dataclass(frozen=True)
class Task160RawBoundaryBlockedResult:
    schema_version: str
    task160_version: str
    implementation_software_version: str
    failure_stage: FailureStage
    raw_request_projection: Task160RawRequestProjection
    raw_request_projection_hash: str
    blockers: tuple[Task160Blocker, ...]
    warnings: tuple[Task160Warning, ...]
    deferred_capabilities: tuple[str, ...]
    blocked_result_hash: str
    blocked_result_id: UUID

    def __post_init__(self) -> None:
        if self.failure_stage is not FailureStage.RAW_BOUNDARY:
            raise ValueError("raw-boundary result must use RAW_BOUNDARY stage")
        if not self.blockers:
            raise ValueError("raw-boundary blocked result requires blockers")
        _require_hash(self.raw_request_projection_hash, "raw_request_projection_hash")
        _require_hash(self.blocked_result_hash, "blocked_result_hash")
        if type(self.blocked_result_id) is not UUID:
            raise ValueError("blocked_result_id must be UUID")
        if self.warnings != ():
            raise ValueError("TASK160 warnings are always empty")


@dataclass(frozen=True)
class Task160ValidationResult:
    status: ValidationStatus
    raw_boundary_blocked: Task160RawBoundaryBlockedResult | None
    typed_blocked: Task160BlockedResult | None
    valid: Task160Result | None

    def __post_init__(self) -> None:
        values = (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        if sum(item is not None for item in values) != 1:
            raise ValueError("exactly one TASK160 result branch must be populated")
        expected = {
            ValidationStatus.RAW_BOUNDARY_BLOCKED: self.raw_boundary_blocked,
            ValidationStatus.TYPED_BLOCKED: self.typed_blocked,
            ValidationStatus.VALID: self.valid,
        }[self.status]
        if expected is None:
            raise ValueError("status does not match populated result branch")

    @property
    def result(self) -> Task160RawBoundaryBlockedResult | Task160BlockedResult | Task160Result:
        return self.raw_boundary_blocked or self.typed_blocked or self.valid  # type: ignore[return-value]

    @property
    def blockers(self) -> tuple[Task160Blocker, ...]:
        return self.result.blockers

    @property
    def warnings(self) -> tuple[Task160Warning, ...]:
        return self.result.warnings


__all__ = [name for name in globals() if not name.startswith("_")]
