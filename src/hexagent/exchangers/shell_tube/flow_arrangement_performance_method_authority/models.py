"""Immutable TASK161 flow-arrangement and method-authority models."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_stream_state.models import Task160Result

TASK161_SOURCE_DEFINITION_ID = "TASK161-SOURCE-DEFINITION-R8-ISSUE-225"
TASK161_SCHEMA_VERSION = "task161.schema.v1"
TASK161_VERSION = "task161.v1"
TASK161_IMPLEMENTATION_SOFTWARE_VERSION = "task161.local-implementation.v1"
TASK161_RAW_PROJECTION_SCHEMA_VERSION = "task161.raw-projection.v1"
TASK161_RAW_BOUNDARY_SCHEMA_VERSION = "task161.raw-boundary-blocked.v1"
TASK161_TYPED_BLOCKED_SCHEMA_VERSION = "task161.typed-blocked.v1"
TASK161_RESULT_ID_NAMESPACE = "a1610000-0000-5000-8000-000000000161"
TASK161_PROVENANCE_NAMESPACE = "a1610000-0000-5001-8000-000000000161"

TASK161_DECIMAL_PRECISION = 160
TASK161_DECIMAL_EMIN = -999999
TASK161_DECIMAL_EMAX = 999999
TASK161_DECIMAL_CAPITALS = 1
TASK161_DECIMAL_CLAMP = 0
TASK161_GUARD_DIGITS = 0

TASK161_RAW_MAX_DEPTH = 16
TASK161_RAW_MAX_NODES = 512
TASK161_RAW_MAX_SCALAR_BYTES = 16384
TASK161_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE = TASK161_RAW_MAX_SCALAR_BYTES + 1

TASK161_REQUIRED_CASE_INPUTS: tuple[str, ...] = (
    "physical_configuration_authority",
    "shell_pass_count_authority",
    "tube_pass_count_authority",
    "shell_type_authority",
    "overall_flow_orientation_authority",
    "baffle_count_authority",
    "physical_sthe_tube_side_mixing_authority",
    "physical_sthe_shell_side_mixing_model_authority",
    "steady_state_authority",
    "ambient_heat_loss_assumption_authority",
    "internal_source_sink_assumption_authority",
    "constant_wall_material_property_authority",
    "constant_heat_transfer_coefficient_authority",
    "axial_heat_transfer_assumption_authority",
    "leakage_model_assumption_authority",
    "bypass_model_assumption_authority",
)
TASK161_REQUIRED_RUNTIME_INPUTS: tuple[str, ...] = ("NTU", "R_source")


class Task161ValidationStatus(StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


ValidationStatus = Task161ValidationStatus


class Task161FailureStage(StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    STRICT_VALIDATION = "STRICT_VALIDATION"
    APPLICABILITY = "APPLICABILITY"
    COMPLETENESS = "COMPLETENESS"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


FailureStage = Task161FailureStage


class RawProjectionKind(StrEnum):
    NONE = "NONE"
    STRING = "STRING"
    INTEGER = "INTEGER"
    DECIMAL = "DECIMAL"
    BOOLEAN = "BOOLEAN"
    ENUM_LITERAL = "ENUM_LITERAL"
    TASK160_RESULT_IDENTITY = "TASK160_RESULT_IDENTITY"
    SEQUENCE = "SEQUENCE"
    RECORD = "RECORD"
    UNSUPPORTED_OBJECT = "UNSUPPORTED_OBJECT"
    LIMIT_MARKER = "LIMIT_MARKER"


class CapacitySideRelation(StrEnum):
    COLD_SIDE_IS_CMIN = "COLD_SIDE_IS_CMIN"
    HOT_SIDE_IS_CMIN = "HOT_SIDE_IS_CMIN"
    EQUAL_CAPACITY = "EQUAL_CAPACITY"


class AssumptionAuthorityClass(StrEnum):
    TASK160_INHERITED_AUTHORITY = "TASK160_INHERITED_AUTHORITY"
    PHYSICAL_CASE_AUTHORITY_REQUIRED = "PHYSICAL_CASE_AUTHORITY_REQUIRED"
    CATALOG_FIXED_SOURCE_SEMANTIC = "CATALOG_FIXED_SOURCE_SEMANTIC"
    DOWNSTREAM_RUNTIME_VALIDATION = "DOWNSTREAM_RUNTIME_VALIDATION"


class CatalogBindingState(StrEnum):
    UNBOUND = "UNBOUND"
    BOUND = "BOUND"
    INVALID = "INVALID"


class CatalogStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


LIMIT_MARKER_FIELD_NAME = "__TASK161_LIMIT_MARKER__"
LIMIT_MARKER_REASONS: tuple[str, ...] = (
    "DEPTH_LIMIT_EXCEEDED",
    "NODE_LIMIT_EXCEEDED",
    "SCALAR_BYTE_LIMIT_EXCEEDED",
    "UNICODE_ENCODING_FAILURE",
    "TYPE_IDENTITY_UNAVAILABLE",
)


def _require_text(value: object, name: str, *, allow_empty: bool = False) -> None:
    if type(value) is not str or (not allow_empty and not value):
        raise ValueError(f"{name} must be a {'non-empty ' if not allow_empty else ''}str")


def _require_hash(value: object, name: str) -> None:
    if (
        type(value) is not str
        or len(value) != 64
        or any(char not in "0123456789abcdef" for char in value)
    ):
        raise ValueError(f"{name} must be 64 lowercase hexadecimal characters")


def _require_strings(value: object, name: str, *, allow_empty: bool = True) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    if not allow_empty and not value:
        raise ValueError(f"{name} must not be empty")
    if any(type(item) is not str or not item for item in value):
        raise ValueError(f"{name} must contain non-empty strings")


def _require_pairs(value: object, name: str) -> None:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be a tuple")
    for pair in value:
        if (
            type(pair) is not tuple
            or len(pair) != 2
            or type(pair[0]) is not str
            or type(pair[1]) is not str
        ):
            raise ValueError(f"{name} must contain string pairs")


@dataclass(frozen=True)
class Task160ResultIdentityProjection:
    schema_version: str
    task160_version: str
    request_hash: str
    result_hash: str
    result_id: str
    provenance_hash: str

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        _require_text(self.task160_version, "task160_version")
        _require_hash(self.request_hash, "request_hash")
        _require_hash(self.result_hash, "result_hash")
        _require_text(self.result_id, "result_id")
        _require_text(self.provenance_hash, "provenance_hash")


@dataclass(frozen=True)
class RawProjectionNode:
    field_name: str
    kind: RawProjectionKind
    type_identity: str | None = None
    scalar_payload: str | None = None
    children: tuple[RawProjectionNode, ...] = ()

    _SCALAR_KINDS: ClassVar[frozenset[RawProjectionKind]] = frozenset(
        {
            RawProjectionKind.NONE,
            RawProjectionKind.STRING,
            RawProjectionKind.INTEGER,
            RawProjectionKind.DECIMAL,
            RawProjectionKind.BOOLEAN,
            RawProjectionKind.ENUM_LITERAL,
        }
    )

    def __post_init__(self) -> None:
        _require_text(self.field_name, "field_name")
        if not isinstance(self.kind, RawProjectionKind):
            raise ValueError("kind must be RawProjectionKind")
        if self.type_identity is not None and type(self.type_identity) is not str:
            raise ValueError("type_identity must be str or None")
        if self.scalar_payload is not None and type(self.scalar_payload) is not str:
            raise ValueError("scalar_payload must be str or None")
        if type(self.children) is not tuple or any(
            not isinstance(child, RawProjectionNode) for child in self.children
        ):
            raise ValueError("children must be a tuple of RawProjectionNode")
        if self.kind is RawProjectionKind.LIMIT_MARKER:
            if (
                self.field_name != LIMIT_MARKER_FIELD_NAME
                or self.type_identity is not None
                or self.scalar_payload not in LIMIT_MARKER_REASONS
                or self.children != ()
            ):
                raise ValueError("invalid LIMIT_MARKER representation")
            return
        if self.kind is RawProjectionKind.TASK160_RESULT_IDENTITY:
            if self.type_identity is not None or self.scalar_payload is not None:
                raise ValueError("Task160 identity node has no scalar payload")
            expected = (
                "schema_version",
                "task160_version",
                "request_hash",
                "result_hash",
                "result_id",
                "provenance_hash",
            )
            if tuple(child.field_name for child in self.children) != expected:
                raise ValueError("Task160 identity projection fields are not ordered")
            return
        if self.kind is RawProjectionKind.UNSUPPORTED_OBJECT:
            if (
                type(self.type_identity) is not str
                or not self.type_identity
                or self.scalar_payload is not None
                or self.children != ()
            ):
                raise ValueError("invalid unsupported-object representation")
            return
        if self.kind in self._SCALAR_KINDS:
            if self.children != ():
                raise ValueError("scalar node cannot have children")
            if self.kind is RawProjectionKind.NONE:
                if self.scalar_payload is not None or self.type_identity is not None:
                    raise ValueError("NONE node must have no payload")
            elif type(self.scalar_payload) is not str or self.type_identity is not None:
                raise ValueError("scalar node requires a scalar payload only")
            return
        if self.type_identity is not None or self.scalar_payload is not None:
            raise ValueError("container node cannot have scalar fields")
        if self.kind is RawProjectionKind.SEQUENCE:
            for index, child in enumerate(self.children):
                if child.kind is RawProjectionKind.LIMIT_MARKER:
                    continue
                if child.field_name != f"item-{index:06d}":
                    raise ValueError("sequence children must use canonical item names")


@dataclass(frozen=True)
class Task161RawRequestProjection:
    schema_version: str
    root: RawProjectionNode

    def __post_init__(self) -> None:
        if self.schema_version != TASK161_RAW_PROJECTION_SCHEMA_VERSION:
            raise ValueError("unsupported TASK161 raw projection schema")
        if not isinstance(self.root, RawProjectionNode):
            raise ValueError("root must be RawProjectionNode")


@dataclass(frozen=True)
class Task161Request:
    schema_version: str
    task161_version: str
    source_definition_id: str
    task160_result: Task160Result
    request_metadata: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        _require_text(self.schema_version, "schema_version")
        _require_text(self.task161_version, "task161_version")
        _require_text(self.source_definition_id, "source_definition_id")
        if type(self.task160_result) is not Task160Result:
            raise ValueError("task160_result must be an exact Task160Result")
        _require_pairs(self.request_metadata, "request_metadata")
        keys = tuple(pair[0] for pair in self.request_metadata)
        if len(keys) != len(set(keys)):
            raise ValueError("request_metadata keys must be unique")


@dataclass(frozen=True)
class Task161Blocker:
    code: str
    stage: Task161FailureStage
    field_path: str
    evidence_refs: tuple[str, ...] = ()
    details: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        if not isinstance(self.stage, Task161FailureStage):
            raise ValueError("stage must be Task161FailureStage")
        _require_text(self.field_path, "field_path", allow_empty=True)
        _require_strings(self.evidence_refs, "evidence_refs")
        _require_pairs(self.details, "details")


@dataclass(frozen=True)
class Task161Warning:
    code: str
    field_path: str = ""
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_text(self.code, "code")
        _require_text(self.field_path, "field_path", allow_empty=True)
        _require_strings(self.evidence_refs, "evidence_refs")


@dataclass(frozen=True)
class CapacityFoundation:
    c_dot_hot: Decimal
    c_dot_cold: Decimal
    c_min: Decimal
    c_max: Decimal
    c_r: Decimal
    r_source: Decimal
    capacity_side_relation: CapacitySideRelation

    def __post_init__(self) -> None:
        values = (
            self.c_dot_hot,
            self.c_dot_cold,
            self.c_min,
            self.c_max,
            self.c_r,
            self.r_source,
        )
        if any(type(value) is not Decimal or not value.is_finite() for value in values):
            raise ValueError("capacity foundation values must be finite Decimal")
        if not isinstance(self.capacity_side_relation, CapacitySideRelation):
            raise ValueError("capacity_side_relation has invalid type")
        if self.c_min <= 0 or self.c_max <= 0 or self.c_min > self.c_max:
            raise ValueError("capacity foundation ordering is invalid")
        if not Decimal(0) < self.c_r <= Decimal(1) or self.r_source <= Decimal(0):
            raise ValueError("capacity foundation ratios are invalid")


@dataclass(frozen=True)
class SourceAssumption:
    assumption_id: str
    semantic_name: str
    source_value: str
    source_status: str
    primary_authority_class: AssumptionAuthorityClass
    case_authority_required: bool
    runtime_validation_required: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in ("assumption_id", "semantic_name", "source_value", "source_status"):
            _require_text(getattr(self, name), name)
        if not isinstance(self.primary_authority_class, AssumptionAuthorityClass):
            raise ValueError("primary_authority_class has invalid type")
        if type(self.case_authority_required) is not bool:
            raise ValueError("case_authority_required must be bool")
        if type(self.runtime_validation_required) is not bool:
            raise ValueError("runtime_validation_required must be bool")
        _require_strings(self.evidence_refs, "evidence_refs")


@dataclass(frozen=True)
class PhysicalStheMixingAuthority:
    tube_side_mixing_assumption: str
    shell_side_mixing_assumption: str
    shell_side_mixing_model_id: str

    def __post_init__(self) -> None:
        for name in (
            "tube_side_mixing_assumption",
            "shell_side_mixing_assumption",
            "shell_side_mixing_model_id",
        ):
            _require_text(getattr(self, name), name)


@dataclass(frozen=True)
class CfheSurrogateMixingAuthority:
    external_fluid_identity: str
    internal_fluid_identity: str
    external_fluid_mixing_assumption: str
    internal_fluid_mixing_assumption: str

    def __post_init__(self) -> None:
        for name in (
            "external_fluid_identity",
            "internal_fluid_identity",
            "external_fluid_mixing_assumption",
            "internal_fluid_mixing_assumption",
        ):
            _require_text(getattr(self, name), name)


@dataclass(frozen=True)
class StheCfheIdentityMapping:
    sthe_tube_side_is_cfhe_external_fluid: bool
    sthe_shell_side_is_cfhe_internal_fluid: bool
    sthe_tube_side_is_cfhe_internal_fluid: bool
    sthe_shell_side_is_cfhe_external_fluid: bool

    def __post_init__(self) -> None:
        values = (
            self.sthe_tube_side_is_cfhe_external_fluid,
            self.sthe_shell_side_is_cfhe_internal_fluid,
            self.sthe_tube_side_is_cfhe_internal_fluid,
            self.sthe_shell_side_is_cfhe_external_fluid,
        )
        if any(type(value) is not bool for value in values):
            raise ValueError("STHE/CFHE identity mapping fields must be bool")
        if values != (True, True, False, False):
            raise ValueError("STHE/CFHE identity mapping invariant failed")


@dataclass(frozen=True)
class FlowArrangementCatalogAuthority:
    catalog_id: str
    source_shell_type: str
    source_shell_pass_count: int
    source_tube_pass_count: int
    overall_flow_orientation: str
    sectional_surrogate_model: str
    section_count_relation: str
    hxforge_construction_intersection: str
    limitations: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name in (
            "catalog_id",
            "source_shell_type",
            "overall_flow_orientation",
            "sectional_surrogate_model",
            "section_count_relation",
            "hxforge_construction_intersection",
        ):
            _require_text(getattr(self, name), name)
        if type(self.source_shell_pass_count) is not int or self.source_shell_pass_count != 1:
            raise ValueError("source_shell_pass_count must be one")
        if type(self.source_tube_pass_count) is not int or self.source_tube_pass_count != 1:
            raise ValueError("source_tube_pass_count must be one")
        _require_strings(self.limitations, "limitations")
        _require_strings(self.evidence_refs, "evidence_refs")


@dataclass(frozen=True)
class PerformanceMethodCatalogAuthority:
    method_authority_id: str
    method_family: str
    method_revision: str
    flow_arrangement_catalog_id: str
    engineering_source_id: str
    engineering_source_version: str
    engineering_source_location: str
    engineering_source_license: str
    relation_id: str
    source_variable_definitions: tuple[tuple[str, str], ...]
    hxforge_variable_mapping: tuple[tuple[str, str], ...]
    physical_configuration_scope: tuple[tuple[str, str], ...]
    model_scope: tuple[tuple[str, str], ...]
    required_case_inputs: tuple[str, ...]
    required_runtime_inputs: tuple[str, ...]
    output_variables: tuple[str, ...]
    parameter_authorities: tuple[tuple[str, str], ...]
    supported_baffle_count_domain: str
    supported_mixing_model_domain: tuple[str, ...]
    single_phase_requirement: bool
    constant_property_requirement: bool
    leakage_assumption: str
    bypass_assumption: str
    p_source_definition: str
    r_source_definition: str
    ntu_definition: str
    p_to_epsilon_mapping: str
    r_to_cr_mapping: str
    applicability: tuple[str, ...]
    limitations: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    provenance: tuple[str, ...]
    authority_hash: str

    def __post_init__(self) -> None:
        text_fields = (
            "method_authority_id",
            "method_family",
            "method_revision",
            "flow_arrangement_catalog_id",
            "engineering_source_id",
            "engineering_source_version",
            "engineering_source_location",
            "engineering_source_license",
            "relation_id",
            "supported_baffle_count_domain",
            "leakage_assumption",
            "bypass_assumption",
            "p_source_definition",
            "r_source_definition",
            "ntu_definition",
            "p_to_epsilon_mapping",
            "r_to_cr_mapping",
        )
        for name in text_fields:
            _require_text(getattr(self, name), name)
        for name in (
            "source_variable_definitions",
            "hxforge_variable_mapping",
            "physical_configuration_scope",
            "model_scope",
            "parameter_authorities",
        ):
            _require_pairs(getattr(self, name), name)
        for name in (
            "required_case_inputs",
            "required_runtime_inputs",
            "output_variables",
            "supported_mixing_model_domain",
            "applicability",
            "limitations",
            "evidence_refs",
            "provenance",
        ):
            _require_strings(getattr(self, name), name)
        if self.required_case_inputs != TASK161_REQUIRED_CASE_INPUTS:
            raise ValueError("required case-input contract is not frozen")
        if self.required_runtime_inputs != TASK161_REQUIRED_RUNTIME_INPUTS:
            raise ValueError("required runtime-input contract is not frozen")
        if type(self.single_phase_requirement) is not bool:
            raise ValueError("single_phase_requirement must be bool")
        if type(self.constant_property_requirement) is not bool:
            raise ValueError("constant_property_requirement must be bool")
        _require_hash(self.authority_hash, "authority_hash")


@dataclass(frozen=True)
class MethodOutputSemantics:
    direct_output: str
    direct_output_definition: str
    direct_output_is_generic_epsilon: bool
    direct_output_is_magazoni_p: bool
    p_to_epsilon_mapping: str

    def __post_init__(self) -> None:
        for name in ("direct_output", "direct_output_definition", "p_to_epsilon_mapping"):
            _require_text(getattr(self, name), name)
        if type(self.direct_output_is_generic_epsilon) is not bool:
            raise ValueError("direct_output_is_generic_epsilon must be bool")
        if type(self.direct_output_is_magazoni_p) is not bool:
            raise ValueError("direct_output_is_magazoni_p must be bool")
        if (self.direct_output_is_generic_epsilon, self.direct_output_is_magazoni_p) != (
            False,
            True,
        ):
            raise ValueError("Table 7 output semantics are invalid")


@dataclass(frozen=True)
class CaseBindingState:
    tema_e_binding: CatalogBindingState
    flow_arrangement_binding: CatalogBindingState
    method_selection: CatalogBindingState
    leakage_assumption_binding: CatalogBindingState
    bypass_assumption_binding: CatalogBindingState

    def __post_init__(self) -> None:
        values = (
            self.tema_e_binding,
            self.flow_arrangement_binding,
            self.method_selection,
            self.leakage_assumption_binding,
            self.bypass_assumption_binding,
        )
        if any(not isinstance(value, CatalogBindingState) for value in values):
            raise ValueError("case binding state contains invalid enum")


@dataclass(frozen=True)
class CatalogApplicability:
    status: CatalogStatus
    catalog_source_applicable: bool
    case_binding_applicability: str
    downstream_runtime_applicability: str
    required_scope: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.status is not CatalogStatus.COMPLETE:
            raise ValueError("TASK161 catalog applicability must be complete")
        if self.catalog_source_applicable is not True:
            raise ValueError("catalog source must be applicable")
        for name in ("case_binding_applicability", "downstream_runtime_applicability"):
            _require_text(getattr(self, name), name)
        _require_strings(self.required_scope, "required_scope", allow_empty=False)


@dataclass(frozen=True)
class CatalogCompleteness:
    status: CatalogStatus
    required_case_inputs_declared: bool
    required_runtime_inputs_declared: bool
    output_contract_declared: bool
    source_assumptions_declared: bool
    provenance_declared: bool

    def __post_init__(self) -> None:
        if self.status is not CatalogStatus.COMPLETE:
            raise ValueError("TASK161 catalog completeness must be complete")
        if not all(
            value is True
            for value in (
                self.required_case_inputs_declared,
                self.required_runtime_inputs_declared,
                self.output_contract_declared,
                self.source_assumptions_declared,
                self.provenance_declared,
            )
        ):
            raise ValueError("catalog completeness contract is incomplete")


@dataclass(frozen=True)
class Task161ProvenanceSemanticInputs:
    source_authority_payload_hash: str
    task160_result_evidence_payload_hash: str
    magazoni_source_payload_hash: str
    nasa_generic_definition_source_payload_hash: str
    method_catalog_payload_hash: str
    calculation_run_payload_hash: str

    def __post_init__(self) -> None:
        for name in (
            "source_authority_payload_hash",
            "task160_result_evidence_payload_hash",
            "magazoni_source_payload_hash",
            "nasa_generic_definition_source_payload_hash",
            "method_catalog_payload_hash",
            "calculation_run_payload_hash",
        ):
            _require_hash(getattr(self, name), name)


@dataclass(frozen=True)
class Task161Provenance:
    graph: ProvenanceGraph
    provenance_hash: str

    def __post_init__(self) -> None:
        if not isinstance(self.graph, ProvenanceGraph):
            raise ValueError("graph must be ProvenanceGraph")
        if type(self.provenance_hash) is not str or not self.provenance_hash.startswith("sha256:"):
            raise ValueError("provenance_hash must be sha256:<64hex>")
        if len(self.provenance_hash) != 71 or any(
            char not in "0123456789abcdef" for char in self.provenance_hash[7:]
        ):
            raise ValueError("provenance_hash must be sha256:<64hex>")
        if self.provenance_hash != self.graph.compute_hash():
            raise ValueError("provenance_hash must equal graph.compute_hash()")


@dataclass(frozen=True)
class Task161PreResultIdentityInputs:
    schema_version: str
    task161_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task160_evidence: Task160ResultIdentityProjection
    capacity_foundation: CapacityFoundation
    flow_arrangement_catalog: FlowArrangementCatalogAuthority
    performance_method_catalog: PerformanceMethodCatalogAuthority
    physical_sthe_mixing: PhysicalStheMixingAuthority
    cfhe_surrogate_mixing: CfheSurrogateMixingAuthority
    sthe_cfhe_identity_mapping: StheCfheIdentityMapping
    source_assumptions: tuple[SourceAssumption, ...]
    required_case_inputs: tuple[str, ...]
    required_runtime_inputs: tuple[str, ...]
    method_output_semantics: MethodOutputSemantics
    case_binding_state: CaseBindingState
    applicability: CatalogApplicability
    completeness: CatalogCompleteness
    warnings_normalized: tuple[Task161Warning, ...]
    blockers_normalized: tuple[Task161Blocker, ...]
    provenance_semantic_inputs: Task161ProvenanceSemanticInputs


@dataclass(frozen=True)
class Task161Result:
    schema_version: str
    task161_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    task160_evidence: Task160ResultIdentityProjection
    capacity_foundation: CapacityFoundation
    flow_arrangement_catalog: FlowArrangementCatalogAuthority
    performance_method_catalog: PerformanceMethodCatalogAuthority
    physical_sthe_mixing: PhysicalStheMixingAuthority
    cfhe_surrogate_mixing: CfheSurrogateMixingAuthority
    sthe_cfhe_identity_mapping: StheCfheIdentityMapping
    source_assumptions: tuple[SourceAssumption, ...]
    required_case_inputs: tuple[str, ...]
    required_runtime_inputs: tuple[str, ...]
    method_output_semantics: MethodOutputSemantics
    case_binding_state: CaseBindingState
    applicability: CatalogApplicability
    completeness: CatalogCompleteness
    warnings: tuple[Task161Warning, ...]
    blockers: tuple[Task161Blocker, ...]
    provenance_semantic_inputs: Task161ProvenanceSemanticInputs
    provenance: Task161Provenance
    result_hash: str
    result_id: UUID

    def __post_init__(self) -> None:
        _require_hash(self.request_hash, "request_hash")
        _require_hash(self.result_hash, "result_hash")
        if type(self.result_id) is not UUID:
            raise ValueError("result_id must be UUID")
        if self.blockers != ():
            raise ValueError("successful TASK161 result cannot contain blockers")
        if self.warnings != ():
            raise ValueError("successful TASK161 result has no warnings")
        if self.applicability.status is not CatalogStatus.COMPLETE:
            raise ValueError("successful TASK161 result must be applicable")
        if self.completeness.status is not CatalogStatus.COMPLETE:
            raise ValueError("successful TASK161 result must be complete")
        if self.required_case_inputs != TASK161_REQUIRED_CASE_INPUTS:
            raise ValueError("successful result case-input contract is not frozen")
        if self.required_runtime_inputs != TASK161_REQUIRED_RUNTIME_INPUTS:
            raise ValueError("successful result runtime-input contract is not frozen")


@dataclass(frozen=True)
class Task161BlockedResult:
    schema_version: str
    task161_version: str
    implementation_software_version: str
    failure_stage: Task161FailureStage
    request_hash: str
    task160_result_id_or_none: str | None
    blockers: tuple[Task161Blocker, ...]
    warnings: tuple[Task161Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID

    def __post_init__(self) -> None:
        if not self.blockers:
            raise ValueError("typed blocked result requires blockers")
        if not isinstance(self.failure_stage, Task161FailureStage):
            raise ValueError("failure_stage has invalid type")
        _require_hash(self.request_hash, "request_hash")
        if self.task160_result_id_or_none is not None:
            _require_text(self.task160_result_id_or_none, "task160_result_id_or_none")
        _require_hash(self.blocked_result_hash, "blocked_result_hash")
        if type(self.blocked_result_id) is not UUID:
            raise ValueError("blocked_result_id must be UUID")


@dataclass(frozen=True)
class Task161RawBoundaryBlockedResult:
    schema_version: str
    task161_version: str
    implementation_software_version: str
    failure_stage: Task161FailureStage
    raw_request_projection: Task161RawRequestProjection
    raw_request_projection_hash: str
    blockers: tuple[Task161Blocker, ...]
    warnings: tuple[Task161Warning, ...]
    blocked_result_hash: str
    blocked_result_id: UUID

    def __post_init__(self) -> None:
        if self.failure_stage is not Task161FailureStage.RAW_BOUNDARY:
            raise ValueError("raw blocked result must use RAW_BOUNDARY")
        if not self.blockers:
            raise ValueError("raw blocked result requires blockers")
        _require_hash(self.raw_request_projection_hash, "raw_request_projection_hash")
        _require_hash(self.blocked_result_hash, "blocked_result_hash")
        if type(self.blocked_result_id) is not UUID:
            raise ValueError("blocked_result_id must be UUID")


@dataclass(frozen=True)
class Task161ValidationResult:
    status: Task161ValidationStatus
    raw_boundary_blocked: Task161RawBoundaryBlockedResult | None
    typed_blocked: Task161BlockedResult | None
    valid: Task161Result | None

    def __post_init__(self) -> None:
        branches = (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        if sum(branch is not None for branch in branches) != 1:
            raise ValueError("exactly one TASK161 result branch must be populated")
        expected = {
            Task161ValidationStatus.RAW_BOUNDARY_BLOCKED: self.raw_boundary_blocked,
            Task161ValidationStatus.TYPED_BLOCKED: self.typed_blocked,
            Task161ValidationStatus.VALID: self.valid,
        }[self.status]
        if expected is None:
            raise ValueError("status does not match populated result branch")

    @property
    def result(self) -> Task161RawBoundaryBlockedResult | Task161BlockedResult | Task161Result:
        return self.raw_boundary_blocked or self.typed_blocked or self.valid  # type: ignore[return-value]

    @property
    def blockers(self) -> tuple[Task161Blocker, ...]:
        return self.result.blockers

    @property
    def warnings(self) -> tuple[Task161Warning, ...]:
        return self.result.warnings


__all__ = [name for name in globals() if not name.startswith("_")]
