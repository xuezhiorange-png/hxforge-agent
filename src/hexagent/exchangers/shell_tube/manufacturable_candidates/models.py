"""Typed TASK-168 manufacturable candidate generation models.

TASK-168 is an orchestration boundary.  The models in this module carry
discrete authority and producer-owned result references; they intentionally
do not contain a second thermal or hydraulic implementation.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, fields
from decimal import Decimal
from typing import Any, cast

from hexagent.exchangers.shell_tube.models import ConstructionFamily, ShellAndTubeConfiguration
from hexagent.shell_geometry_catalogs.models import ShellGeometryCatalog

TASK168_SCHEMA_VERSION = "task168.manufacturable-candidates-request.v1"
TASK168_VERSION = "task168.v1"
TASK168_RESULT_SCHEMA_VERSION = "task168.manufacturable-candidates-result.v1"
TASK168_BLOCKED_SCHEMA_VERSION = "task168.manufacturable-candidates-blocked.v1"
TASK168_RAW_BLOCKED_SCHEMA_VERSION = "task168.manufacturable-candidates-raw-boundary-blocked.v1"
TASK168_SOURCE_DEFINITION_ID = "TASK168-SOURCE-DEFINITION-ISSUE-263"
TASK168_IMPLEMENTATION_SOFTWARE_VERSION = "task168.manufacturable-candidates-impl-v1"
TASK168_DESIGN_CONTRACT_PATH = (
    "docs/tasks/TASK-168-manufacturable-candidate-generation-and-sizing.md"
)

RAW_MAX_DEPTH = 16
RAW_MAX_NODES = 512
RAW_MAX_SCALAR_BYTES = 16_384
MAX_DISCRETE_VALUES_PER_DIMENSION = 32
MAX_RAW_COMBINATION_COUNT = 4_096
MAX_MATERIALIZED_CANDIDATE_COUNT = 4_096

REQUEST_FIELDS = (
    "schema_version",
    "task168_version",
    "source_definition_id",
    "task020_configuration",
    "requirement_authority",
    "shell_geometry_catalog",
    "discrete_candidate_set_authorities",
    "evaluation_input_authority",
    "request_metadata",
)

# TASK-168 owns candidate generation, geometry materialisation, and producer
# orchestration.  These are contract markers, not additional public business
# entry points.
TASK168_GENERATES_CANDIDATES = True
TASK168_MATERIALIZES_CANDIDATE_GEOMETRY = True
TASK168_ORCHESTRATES_EVALUATION_CHAIN = True
CALLER_PRECOMPUTED_CANDIDATE_RESULTS_REQUIRED = False
CANDIDATE_SPECIFIC_TASK020_CONFIGURATION = True
BASE_TASK020_CONFIGURATION_USED_AS_FIXED_FINAL_CONFIG = False

DIMENSION_ORDER = (
    "CONSTRUCTION_FAMILY",
    "SHELL_GEOMETRY_ID",
    "TUBE_OUTER_DIAMETER",
    "TUBE_WALL_THICKNESS",
    "TUBE_LENGTH",
    "TUBE_PITCH",
    "TUBE_LAYOUT",
    "TUBE_PASS_COUNT",
    "BAFFLE_TYPE",
    "BAFFLE_CUT",
    "BAFFLE_SPACING",
    "BAFFLE_COUNT",
)

REQUIRED_DISCRETE_ROLES = (
    "CONSTRUCTION_FAMILY",
    "TUBE_OUTER_DIAMETER",
    "TUBE_WALL_THICKNESS",
    "TUBE_LENGTH",
    "TUBE_PITCH",
    "TUBE_LAYOUT",
    "TUBE_PASS_COUNT",
    "BAFFLE_TYPE",
    "BAFFLE_CUT",
    "BAFFLE_SPACING",
    "BAFFLE_COUNT",
)


class ValidationStatus(enum.StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class DiscreteDimensionRole(enum.StrEnum):
    CONSTRUCTION_FAMILY = "CONSTRUCTION_FAMILY"
    TUBE_OUTER_DIAMETER = "TUBE_OUTER_DIAMETER"
    TUBE_WALL_THICKNESS = "TUBE_WALL_THICKNESS"
    TUBE_LENGTH = "TUBE_LENGTH"
    TUBE_PITCH = "TUBE_PITCH"
    TUBE_LAYOUT = "TUBE_LAYOUT"
    TUBE_PASS_COUNT = "TUBE_PASS_COUNT"
    BAFFLE_TYPE = "BAFFLE_TYPE"
    BAFFLE_CUT = "BAFFLE_CUT"
    BAFFLE_SPACING = "BAFFLE_SPACING"
    BAFFLE_COUNT = "BAFFLE_COUNT"


class DiscreteAuthoritySource(enum.StrEnum):
    APPROVED_CATALOG = "APPROVED_CATALOG"
    APPROVED_RULE_PACK = "APPROVED_RULE_PACK"
    SOURCE_BOUND_DISCRETE_SNAPSHOT = "SOURCE_BOUND_DISCRETE_SNAPSHOT"
    AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET = "AUTHORIZED_PROJECT_DEFINED_DISCRETE_SET"


class CandidateDisposition(enum.StrEnum):
    EVALUATED = "EVALUATED"
    BLOCKED = "BLOCKED"


class CandidateStatus(enum.StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    BLOCKED = "BLOCKED"


class CandidateStage(enum.StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    TYPED_VALIDATION = "TYPED_VALIDATION"
    CANDIDATE_AUTHORITY = "CANDIDATE_AUTHORITY"
    CONFIGURATION = "CONFIGURATION"
    TUBE_LAYOUT = "TUBE_LAYOUT"
    SHELL_BUNDLE_GEOMETRY = "SHELL_BUNDLE_GEOMETRY"
    BAFFLE_GEOMETRY = "BAFFLE_GEOMETRY"
    TUBE_SIDE = "TUBE_SIDE"
    SHELL_SIDE_BELL = "SHELL_SIDE_BELL"
    OVERALL_RESISTANCE = "OVERALL_RESISTANCE"
    UA = "UA"
    THERMAL_CLOSURE = "THERMAL_CLOSURE"
    TUBE_DP = "TUBE_DP"
    SHELL_DP = "SHELL_DP"
    ENGINEERING_SCREENING = "ENGINEERING_SCREENING"
    CONSTRAINT_EVALUATION = "CONSTRAINT_EVALUATION"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"
    COMPLETE = "COMPLETE"


class ApplicabilityStatus(enum.StrEnum):
    APPLICABLE = "APPLICABLE"
    BLOCKED = "BLOCKED"


class CompletenessStatus(enum.StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True, slots=True)
class Task168Blocker:
    code: str
    stage: CandidateStage
    field_path: str | None = None
    message: str = ""
    evidence_refs: tuple[str, ...] = ()

    def sort_key(self) -> tuple[int, str, str, tuple[bytes, ...]]:
        stage_rank = {item.value: index for index, item in enumerate(CandidateStage)}
        return (
            stage_rank.get(self.stage.value, len(stage_rank)),
            self.code,
            self.field_path or "",
            tuple(item.encode("utf-8", "strict") for item in self.evidence_refs),
        )


@dataclass(frozen=True, slots=True)
class Task168Warning:
    code: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DiscreteCandidateSetAuthority:
    """One closed, source-bound discrete set for exactly one dimension."""

    authority_id: str
    authority_version: str
    dimension_role: DiscreteDimensionRole
    source_class: DiscreteAuthoritySource
    source_id: str
    source_revision: str
    approval_status: str
    values: tuple[Any, ...]
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    canonical_hash: str

    def __post_init__(self) -> None:
        if type(self.values) is not tuple:
            object.__setattr__(self, "values", tuple(self.values))
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            tuple(sorted(self.provenance_refs, key=lambda item: item.encode("utf-8"))),
        )


@dataclass(frozen=True, slots=True)
class CandidateDimensionAuthorityBinding:
    """The exact authority member selected for one candidate dimension.

    A candidate dimension is not authorized by the value alone.  This
    binding carries the complete identity of the discrete set that supplied
    the value so materialized producer requests can be audited without
    attributing the value to a structural request template.
    """

    dimension_role: DiscreteDimensionRole
    authority_id: str
    authority_version: str
    canonical_hash: str
    source_class: DiscreteAuthoritySource
    source_id: str
    source_revision: str
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    selected_member: Any

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            tuple(sorted(self.provenance_refs, key=lambda item: item.encode("utf-8"))),
        )


@dataclass(frozen=True, slots=True)
class Task168RequirementAuthority:
    """Identity-bearing constraints; numbers without this object are invalid."""

    requirement_id: str
    authority_version: str
    source_class: str
    source_id: str
    approval_status: str
    allowed_construction_families: tuple[ConstructionFamily, ...]
    required_duty_w: Decimal | None = None
    max_tube_dp_pa: Decimal | None = None
    max_shell_dp_pa: Decimal | None = None
    evidence_refs: tuple[str, ...] = ()
    provenance_refs: tuple[str, ...] = ()
    canonical_hash: str = ""

    def __post_init__(self) -> None:
        if type(self.allowed_construction_families) is not tuple:
            object.__setattr__(
                self,
                "allowed_construction_families",
                tuple(self.allowed_construction_families),
            )
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            tuple(sorted(self.provenance_refs, key=lambda item: item.encode("utf-8"))),
        )


@dataclass(frozen=True, slots=True)
class Task168EvaluationInputAuthority:
    """Base authority from which TASK-168 builds producer requests.

    The record carries request templates and upstream base authorities only.
    It deliberately contains no candidate-specific producer result and no
    callback or executable factory.  TASK-168 fills candidate dimensions into
    these templates, invokes the existing producer boundaries, and records
    their identities in the candidate audit.
    """

    authority_id: str
    authority_version: str
    source_class: str
    source_id: str
    source_revision: str
    approval_status: str
    evidence_refs: tuple[str, ...]
    provenance_refs: tuple[str, ...]
    task021_request_template: object | None = None
    task022_request_template: object | None = None
    task024_request_template: object | None = None
    task025_request_template: object | None = None
    task026_request: object | None = None
    task027_property_snapshot: object | None = None
    task027_roughness_authority: object | None = None
    task027_constant_density_assertion: object | None = None
    task027_zero_net_elevation_assertion: object | None = None
    task027_flow_direction_assertion: object | None = None
    task028_request_template: object | None = None
    task029_request_template: object | None = None
    task031_request_template: object | None = None
    task032_request_template: object | None = None
    task032_property_snapshot: object | None = None
    task032_mass_flow_authority: object | None = None
    task033_request_template: object | None = None
    task034_request_template: object | None = None
    task035_request_template: object | None = None
    task037_request: object | None = None
    task038_service_binding_authority: object | None = None
    task166_request_template: object | None = None
    task160_request_template: object | None = None
    task161_request_template: object | None = None
    task162_case_authority: object | None = None
    task162_binding_authority: object | None = None
    task162_request_metadata: tuple[tuple[str, str], ...] = ()
    task167_screening_requirements: object | None = None
    task167_screening_property_snapshot: object | None = None
    task167_nozzle_geometry: object | None = None
    task167_approved_rule_pack_authority: object | None = None
    task167_request_metadata: tuple[tuple[str, str], ...] = ()
    canonical_hash: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "evidence_refs",
            tuple(sorted(self.evidence_refs, key=lambda item: item.encode("utf-8"))),
        )
        object.__setattr__(
            self,
            "provenance_refs",
            tuple(sorted(self.provenance_refs, key=lambda item: item.encode("utf-8"))),
        )


@dataclass(frozen=True, slots=True)
class Task168Request:
    schema_version: str
    task168_version: str
    source_definition_id: str
    task020_configuration: ShellAndTubeConfiguration
    requirement_authority: Task168RequirementAuthority
    shell_geometry_catalog: ShellGeometryCatalog
    discrete_candidate_set_authorities: tuple[DiscreteCandidateSetAuthority, ...]
    evaluation_input_authority: Task168EvaluationInputAuthority
    request_metadata: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class CandidateSpec:
    candidate_id: str
    candidate_hash: str
    case_authority_id: str
    construction_family: ConstructionFamily
    shell_geometry_id: str
    shell_record_hash: str
    shell_inside_diameter_m: Decimal
    tube_outer_diameter_m: Decimal
    tube_wall_thickness_m: Decimal
    tube_length_m: Decimal
    tube_pitch_m: Decimal
    tube_layout: str
    tube_pass_count: int
    baffle_type: str
    baffle_cut_fraction: Decimal
    baffle_spacing_m: Decimal
    baffle_count: int
    authority_bindings: tuple[tuple[str, str], ...]
    dimension_authority_bindings: tuple[CandidateDimensionAuthorityBinding, ...]


@dataclass(frozen=True, slots=True)
class Task168Applicability:
    status: ApplicabilityStatus
    checks: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Task168Completeness:
    required_fields: tuple[str, ...]
    present_fields: tuple[str, ...]
    status: CompletenessStatus


@dataclass(frozen=True, slots=True)
class CandidateRecord:
    candidate_id: str
    candidate_hash: str
    candidate: CandidateSpec
    disposition: CandidateDisposition
    status: CandidateStatus
    stage: CandidateStage
    last_successful_stage: CandidateStage | None
    configuration_evidence: tuple[tuple[str, str], ...] = ()
    geometry_evidence: tuple[tuple[str, str], ...] = ()
    tube_layout_evidence: tuple[tuple[str, str], ...] = ()
    tube_side_evidence: tuple[tuple[str, str], ...] = ()
    bell_evidence: tuple[tuple[str, str], ...] = ()
    overall_u_ua_evidence: tuple[tuple[str, str], ...] = ()
    thermal_closure_evidence: tuple[tuple[str, str], ...] = ()
    tube_dp_evidence: tuple[tuple[str, str], ...] = ()
    shell_dp_evidence: tuple[tuple[str, str], ...] = ()
    screening_evidence: tuple[tuple[str, str], ...] = ()
    constraint_evaluations: tuple[tuple[str, str], ...] = ()
    metrics: tuple[tuple[str, str], ...] = ()
    warnings: tuple[Task168Warning, ...] = ()
    blockers: tuple[Task168Blocker, ...] = ()


@dataclass(frozen=True, slots=True)
class ProvenanceNode:
    node_id: str
    payload_hash: str


@dataclass(frozen=True, slots=True)
class ProvenanceEdge:
    source_node_id: str
    relation: str
    target_node_id: str


@dataclass(frozen=True, slots=True)
class ProvenanceGraph:
    nodes: tuple[ProvenanceNode, ...]
    edges: tuple[ProvenanceEdge, ...]
    graph_hash: str
    self_edge_count: int = 0
    cycle_count: int = 0


TASK168_COMPLETENESS_FIELDS = (
    "generation_request",
    "candidate_space_authority",
    "enumeration_summary",
    "candidate_records",
    "blocked_candidate_audit",
    "geometry_evidence",
    "tube_side_evidence",
    "bell_evidence",
    "overall_u_ua_evidence",
    "thermal_closure_evidence",
    "tube_dp_evidence",
    "shell_dp_evidence",
    "screening_evidence",
    "provenance",
)


@dataclass(frozen=True, slots=True)
class Task168BatchResult:
    schema_version: str
    task168_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    candidate_space_id: str
    candidate_space_hash: str
    total_theoretical_combinations: int
    total_enumerated_candidates: int
    pass_count: int
    warn_count: int
    blocked_count: int
    candidate_records: tuple[CandidateRecord, ...]
    warnings: tuple[Task168Warning, ...]
    blockers: tuple[Task168Blocker, ...]
    applicability: Task168Applicability
    completeness: Task168Completeness
    provenance_semantic_inputs: tuple[tuple[str, str], ...]
    provenance: ProvenanceGraph
    result_hash: str
    result_id: str


@dataclass(frozen=True, slots=True)
class Task168TypedBlockedResult:
    schema_version: str
    task168_version: str
    implementation_software_version: str
    request_hash: str
    blockers: tuple[Task168Blocker, ...]
    warnings: tuple[Task168Warning, ...]
    result_hash: str
    result_id: str
    provenance: None = None


@dataclass(frozen=True, slots=True)
class Task168RawBoundaryBlockedResult:
    schema_version: str
    task168_version: str
    implementation_software_version: str
    raw_request_projection_hash: str
    blockers: tuple[Task168Blocker, ...]
    warnings: tuple[Task168Warning, ...]
    result_hash: str
    result_id: str
    provenance: None = None


@dataclass(frozen=True, slots=True)
class Task168ValidationResult:
    status: ValidationStatus
    raw_boundary_blocked: Task168RawBoundaryBlockedResult | None = None
    typed_blocked: Task168TypedBlockedResult | None = None
    valid: Task168BatchResult | None = None

    def __post_init__(self) -> None:
        populated = sum(
            value is not None
            for value in (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        )
        if populated != 1:
            raise ValueError("TASK-168 validation result must populate exactly one branch")
        expected = {
            ValidationStatus.RAW_BOUNDARY_BLOCKED: self.raw_boundary_blocked,
            ValidationStatus.TYPED_BLOCKED: self.typed_blocked,
            ValidationStatus.VALID: self.valid,
        }[self.status]
        if expected is None:
            raise ValueError("TASK-168 validation status and branch do not agree")


def dataclass_field_names(value: object) -> tuple[str, ...]:
    """Small local helper used by tests and canonical projections."""

    return tuple(item.name for item in fields(cast(Any, value)))


__all__ = [
    "ApplicabilityStatus",
    "CALLER_PRECOMPUTED_CANDIDATE_RESULTS_REQUIRED",
    "CANDIDATE_SPECIFIC_TASK020_CONFIGURATION",
    "BASE_TASK020_CONFIGURATION_USED_AS_FIXED_FINAL_CONFIG",
    "CandidateDisposition",
    "CandidateDimensionAuthorityBinding",
    "CandidateRecord",
    "CandidateSpec",
    "CandidateStage",
    "CandidateStatus",
    "CompletenessStatus",
    "DIMENSION_ORDER",
    "DiscreteAuthoritySource",
    "DiscreteCandidateSetAuthority",
    "DiscreteDimensionRole",
    "MAX_DISCRETE_VALUES_PER_DIMENSION",
    "MAX_MATERIALIZED_CANDIDATE_COUNT",
    "MAX_RAW_COMBINATION_COUNT",
    "RAW_MAX_DEPTH",
    "RAW_MAX_NODES",
    "RAW_MAX_SCALAR_BYTES",
    "REQUIRED_DISCRETE_ROLES",
    "REQUEST_FIELDS",
    "ProvenanceEdge",
    "ProvenanceGraph",
    "ProvenanceNode",
    "TASK168_BLOCKED_SCHEMA_VERSION",
    "TASK168_DESIGN_CONTRACT_PATH",
    "TASK168_IMPLEMENTATION_SOFTWARE_VERSION",
    "TASK168_RAW_BLOCKED_SCHEMA_VERSION",
    "TASK168_RESULT_SCHEMA_VERSION",
    "TASK168_SCHEMA_VERSION",
    "TASK168_SOURCE_DEFINITION_ID",
    "TASK168_VERSION",
    "TASK168_COMPLETENESS_FIELDS",
    "TASK168_GENERATES_CANDIDATES",
    "TASK168_MATERIALIZES_CANDIDATE_GEOMETRY",
    "TASK168_ORCHESTRATES_EVALUATION_CHAIN",
    "Task168Applicability",
    "Task168BatchResult",
    "Task168Blocker",
    "Task168EvaluationInputAuthority",
    "Task168Completeness",
    "Task168RawBoundaryBlockedResult",
    "Task168Request",
    "Task168RequirementAuthority",
    "Task168TypedBlockedResult",
    "Task168ValidationResult",
    "Task168Warning",
    "ValidationStatus",
]
