"""Immutable public records for the TASK164 release-acceptance boundary.

The records in this module are intentionally boring: they are the closed
vocabulary and schema boundary for the release demonstration.  Engineering
values remain producer-owned (TASK162/TASK163); TASK164 only observes and
packages them.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task163ApplicabilityStatus,
    Task163CompletenessStatus,
    Task163Request,
    Task163ValidationResult,
)

TASK164_SCHEMA_VERSION = "task164.schema.v1"
TASK164_VERSION = "task164.v1"
TASK164_IMPLEMENTATION_SOFTWARE_VERSION = "task164.local-implementation.v1"
TASK164_SOURCE_DEFINITION_ID = "TASK164-SOURCE-DEFINITION-R1-ISSUE-243"
TASK164_DESIGN_REVISION = "R6"
TASK164_RAW_PROJECTION_SCHEMA_VERSION = "task164.raw-projection.v1"
TASK164_RAW_BOUNDARY_SCHEMA_VERSION = "task164.raw-boundary-blocked.v1"
TASK164_TYPED_BLOCKED_SCHEMA_VERSION = "task164.typed-blocked.v1"
TASK164_RAW_MAX_DEPTH = 16
TASK164_RAW_MAX_NODES = 512
TASK164_RAW_MAX_SCALAR_BYTES = 16_384
TASK164_RAW_TEXT_BYTE_COUNT_LIMIT_PLUS_ONE = TASK164_RAW_MAX_SCALAR_BYTES + 1


class Task164ValidationBranch(StrEnum):
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    VALID = "VALID"


class Task164FailureStage(StrEnum):
    RAW_BOUNDARY = "RAW_BOUNDARY"
    TYPED_VALIDATION = "TYPED_VALIDATION"
    TASK163_REPLAY = "TASK163_REPLAY"
    TASK163_ACCEPTANCE = "TASK163_ACCEPTANCE"
    TERMINAL_CAPABILITY = "TERMINAL_CAPABILITY"
    DEMONSTRATION = "DEMONSTRATION"
    DETERMINISM = "DETERMINISM"
    SCOPE_FENCE = "SCOPE_FENCE"
    EVIDENCE_PACKAGE = "EVIDENCE_PACKAGE"
    PROVENANCE = "PROVENANCE"
    IDENTITY = "IDENTITY"


class Task164Task163Branch(StrEnum):
    VALID = "VALID"
    TYPED_BLOCKED = "TYPED_BLOCKED"
    RAW_BOUNDARY_BLOCKED = "RAW_BOUNDARY_BLOCKED"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class Task164ScenarioClass(StrEnum):
    POSITIVE_PRODUCER = "POSITIVE_PRODUCER"
    NEGATIVE_PRODUCER = "NEGATIVE_PRODUCER"
    DETERMINISM = "DETERMINISM"
    SCOPE_FENCE = "SCOPE_FENCE"


class Task164ScenarioOutcome(StrEnum):
    PASS = "PASS"
    NEGATIVE_PASS = "NEGATIVE_PASS"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


class Task164ScenarioId(StrEnum):
    D164_P01_SUCCESS_BAFFLE_1 = "D164-P01_SUCCESS_BAFFLE_1"
    D164_P02_SUCCESS_BAFFLE_2 = "D164-P02_SUCCESS_BAFFLE_2"
    D164_P03_SUCCESS_BAFFLE_3 = "D164-P03_SUCCESS_BAFFLE_3"
    D164_P04_SUCCESS_BAFFLE_4 = "D164-P04_SUCCESS_BAFFLE_4"
    D164_P05_SUCCESS_BAFFLE_5 = "D164-P05_SUCCESS_BAFFLE_5"
    D164_N01_TASK163_TYPED_BLOCKED = "D164-N01_TASK163_TYPED_BLOCKED"
    D164_N02_TASK163_RAW_BOUNDARY_BLOCKED = "D164-N02_TASK163_RAW_BOUNDARY_BLOCKED"
    D164_N03_TASK162_PRODUCER_ACCEPTANCE_OR_REPLAY_REJECTION = (
        "D164-N03_TASK162_PRODUCER_ACCEPTANCE_OR_REPLAY_REJECTION"
    )
    D164_N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER = (
        "D164-N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER"
    )
    D164_D01_REPEAT_RUN_IDENTITY_AND_EVIDENCE_PARITY = (
        "D164-D01_REPEAT_RUN_IDENTITY_AND_EVIDENCE_PARITY"
    )
    D164_D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY = "D164-D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY"
    D164_S01_SCOPE_FENCE_NO_LMTD_OR_F_FACTOR = "D164-S01_SCOPE_FENCE_NO_LMTD_OR_F_FACTOR"


class Task164TamperTarget(StrEnum):
    RESULT_HASH = "RESULT_HASH"
    RESULT_ID = "RESULT_ID"
    PROVENANCE = "PROVENANCE"


class Task164ScenarioInputAuthority(StrEnum):
    TASK162_ACCEPTED_CASE_BAFFLE_1 = "TASK162_ACCEPTED_CASE_BAFFLE_1"
    TASK162_ACCEPTED_CASE_BAFFLE_2 = "TASK162_ACCEPTED_CASE_BAFFLE_2"
    TASK162_ACCEPTED_CASE_BAFFLE_3 = "TASK162_ACCEPTED_CASE_BAFFLE_3"
    TASK162_ACCEPTED_CASE_BAFFLE_4 = "TASK162_ACCEPTED_CASE_BAFFLE_4"
    TASK162_ACCEPTED_CASE_BAFFLE_5 = "TASK162_ACCEPTED_CASE_BAFFLE_5"
    TASK163_TYPED_BLOCKED_FIXTURE = "TASK163_TYPED_BLOCKED_FIXTURE"
    TASK163_RAW_BOUNDARY_FIXTURE = "TASK163_RAW_BOUNDARY_FIXTURE"
    TASK162_REPLAY_REJECTION_FIXTURE = "TASK162_REPLAY_REJECTION_FIXTURE"
    TASK163_CLAIM_TAMPER_FIXTURE = "TASK163_CLAIM_TAMPER_FIXTURE"
    IN_PROCESS_TASK163_REPEAT_RUN = "IN_PROCESS_TASK163_REPEAT_RUN"
    INTERNAL_DUAL_RUNTIME_PARITY_RUN = "INTERNAL_DUAL_RUNTIME_PARITY_RUN"
    STATIC_SCOPE_AUDIT = "STATIC_SCOPE_AUDIT"


class Task164EvidenceAuthority(StrEnum):
    TASK163_PRODUCER = "TASK163_PRODUCER"
    TASK164_INTERNAL_OBSERVATION = "TASK164_INTERNAL_OBSERVATION"
    FROZEN_AUTHORITY = "FROZEN_AUTHORITY"
    DERIVED_ONLY = "DERIVED_ONLY"


class Task164EvidenceStatus(StrEnum):
    PASS = "PASS"
    REJECTED = "REJECTED"
    NOT_RUN = "NOT_RUN"


class Task164AcceptanceCategoryStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


class Task164AcceptanceLedgerStatus(StrEnum):
    ACCEPTED = "ACCEPTED"
    BLOCKED = "BLOCKED"


class Task164ApplicabilityStatus(StrEnum):
    APPLICABLE = "APPLICABLE"
    BLOCKED = "BLOCKED"


class Task164CompletenessStatus(StrEnum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"


class Task164ScopeStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class Task164ClaimMatchStatus(StrEnum):
    MATCHED = "MATCHED"
    MISMATCHED = "MISMATCHED"
    NOT_RUN = "NOT_RUN"


class Task164ParityStatus(StrEnum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"
    NOT_RUN = "NOT_RUN"


class Task164PythonVersion(StrEnum):
    PYTHON_3_11 = "PYTHON_3_11"
    PYTHON_3_12 = "PYTHON_3_12"


def _runtime_identity_for_version(value: Task164PythonVersion) -> str:
    if value is Task164PythonVersion.PYTHON_3_11:
        return "cpython:3.11"
    if value is Task164PythonVersion.PYTHON_3_12:
        return "cpython:3.12"
    raise ValueError("unsupported TASK164 runtime version")


class Task164RunnerIdentity(StrEnum):
    TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1 = "TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1"


class Task164CommandIdentity(StrEnum):
    TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1 = (
        "TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1"
    )


class Task164PairingKey(StrEnum):
    TASK164_PYTHON_3_11__TASK164_PYTHON_3_12 = "TASK164_PYTHON_3_11__TASK164_PYTHON_3_12"


class Task164ConstructionFamily(StrEnum):
    FIXED_TUBESHEET = "FIXED_TUBESHEET"


class Task164CaseBinding(StrEnum):
    TASK162_CURRENT_CASE_AUTHORITY = "TASK162_CURRENT_CASE_AUTHORITY"


class Task164MethodAuthority(StrEnum):
    TASK161_CATALOG_AND_TASK162_SELECTED_RELATION = "TASK161_CATALOG_AND_TASK162_SELECTED_RELATION"


class Task164RatingOutputAuthority(StrEnum):
    TASK162_AND_TASK163_PRODUCER_OUTPUTS_ONLY = "TASK162_AND_TASK163_PRODUCER_OUTPUTS_ONLY"


class Task164TerminalCapabilityId(StrEnum):
    TASK164_FIXED_TUBESHEET_RATING_OUTPUT_CAPABILITY = (
        "TASK164_FIXED_TUBESHEET_RATING_OUTPUT_CAPABILITY"
    )


class Task164ApplicabilityCheck(StrEnum):
    TASK163_APPLICABILITY_ACCEPTANCE = "TASK163_APPLICABILITY_ACCEPTANCE"
    SUPPORTED_TERMINAL_CAPABILITY_COVERAGE = "SUPPORTED_TERMINAL_CAPABILITY_COVERAGE"
    POSITIVE_DEMONSTRATION_COVERAGE = "POSITIVE_DEMONSTRATION_COVERAGE"
    NEGATIVE_FAIL_CLOSED_COVERAGE = "NEGATIVE_FAIL_CLOSED_COVERAGE"
    REPEAT_RUN_DETERMINISM = "REPEAT_RUN_DETERMINISM"
    CROSS_PYTHON_DETERMINISM = "CROSS_PYTHON_DETERMINISM"
    SCOPE_FENCE_ACCEPTANCE = "SCOPE_FENCE_ACCEPTANCE"


class Task164RepeatRunSurface(StrEnum):
    TASK164_TASK163_REQUEST_PROJECTION = "TASK164_TASK163_REQUEST_PROJECTION"
    TASK164_TASK163_REPLAY_EVIDENCE = "TASK164_TASK163_REPLAY_EVIDENCE"
    TASK164_SCENARIO_EVIDENCE = "TASK164_SCENARIO_EVIDENCE"
    TASK164_TERMINAL_CAPABILITY = "TASK164_TERMINAL_CAPABILITY"
    TASK164_SCOPE_FENCE = "TASK164_SCOPE_FENCE"
    TASK164_PRE_DETERMINISM_PAYLOADS = "TASK164_PRE_DETERMINISM_PAYLOADS"


class Task164ParitySurface(StrEnum):
    TASK164_XPY_IDENTITY_PROJECTION_V1 = "TASK164_XPY_IDENTITY_PROJECTION_V1"
    TASK164_XPY_EVIDENCE_PROJECTION_V1 = "TASK164_XPY_EVIDENCE_PROJECTION_V1"


class Task164EvidencePayloadKind(StrEnum):
    AUTHORITY_CHAIN_PAYLOAD = "AUTHORITY_CHAIN_PAYLOAD"
    MAIN_DELIVERY_PAYLOAD = "MAIN_DELIVERY_PAYLOAD"
    TASK163_REPLAY_PAYLOAD = "TASK163_REPLAY_PAYLOAD"
    TASK163_IDENTITY_PAYLOAD = "TASK163_IDENTITY_PAYLOAD"
    TASK163_APPLICABILITY_PAYLOAD = "TASK163_APPLICABILITY_PAYLOAD"
    TASK163_COMPLETENESS_PAYLOAD = "TASK163_COMPLETENESS_PAYLOAD"
    TASK163_PROVENANCE_PAYLOAD = "TASK163_PROVENANCE_PAYLOAD"
    TERMINAL_CAPABILITY_PAYLOAD = "TERMINAL_CAPABILITY_PAYLOAD"
    POSITIVE_DEMONSTRATION_PAYLOAD = "POSITIVE_DEMONSTRATION_PAYLOAD"
    NEGATIVE_DEMONSTRATION_PAYLOAD = "NEGATIVE_DEMONSTRATION_PAYLOAD"
    REPEAT_RUN_PAYLOAD = "REPEAT_RUN_PAYLOAD"
    PYTHON_PARITY_PAYLOAD = "PYTHON_PARITY_PAYLOAD"
    SCOPE_FENCE_PAYLOAD = "SCOPE_FENCE_PAYLOAD"


class Task164AcceptanceCategory(StrEnum):
    AUTHORITY_CHAIN_INTEGRITY = "AUTHORITY_CHAIN_INTEGRITY"
    DELIVERED_MAIN_AND_PREDECESSOR_INTEGRITY = "DELIVERED_MAIN_AND_PREDECESSOR_INTEGRITY"
    TASK163_PUBLIC_BOUNDARY_ACCEPTANCE = "TASK163_PUBLIC_BOUNDARY_ACCEPTANCE"
    TASK163_RESULT_IDENTITY_ACCEPTANCE = "TASK163_RESULT_IDENTITY_ACCEPTANCE"
    TASK163_APPLICABILITY_ACCEPTANCE = "TASK163_APPLICABILITY_ACCEPTANCE"
    TASK163_COMPLETENESS_ACCEPTANCE = "TASK163_COMPLETENESS_ACCEPTANCE"
    TASK163_PROVENANCE_ACCEPTANCE = "TASK163_PROVENANCE_ACCEPTANCE"
    SUPPORTED_TERMINAL_CAPABILITY_COVERAGE = "SUPPORTED_TERMINAL_CAPABILITY_COVERAGE"
    POSITIVE_DEMONSTRATION_COVERAGE = "POSITIVE_DEMONSTRATION_COVERAGE"
    NEGATIVE_FAIL_CLOSED_COVERAGE = "NEGATIVE_FAIL_CLOSED_COVERAGE"
    REPEAT_RUN_DETERMINISM = "REPEAT_RUN_DETERMINISM"
    CROSS_PYTHON_DETERMINISM = "CROSS_PYTHON_DETERMINISM"
    SCOPE_FENCE_ACCEPTANCE = "SCOPE_FENCE_ACCEPTANCE"
    EVIDENCE_PACKAGE_INTEGRITY = "EVIDENCE_PACKAGE_INTEGRITY"


class Task164PackageArtifactId(StrEnum):
    TASK164_REQUEST_PROJECTION = "TASK164_REQUEST_PROJECTION"
    TASK163_REPLAY_EVIDENCE = "TASK163_REPLAY_EVIDENCE"
    TASK164_SCENARIO_EVIDENCE = "TASK164_SCENARIO_EVIDENCE"
    TASK164_DETERMINISM_EVIDENCE = "TASK164_DETERMINISM_EVIDENCE"
    TASK164_TERMINAL_CAPABILITY = "TASK164_TERMINAL_CAPABILITY"
    TASK164_SCOPE_FENCE = "TASK164_SCOPE_FENCE"


class Task164PostResultArtifactId(StrEnum):
    TASK164_ACCEPTANCE_LEDGER = "TASK164_ACCEPTANCE_LEDGER"
    TASK164_PROVENANCE_GRAPH = "TASK164_PROVENANCE_GRAPH"
    TASK164_RESULT = "TASK164_RESULT"
    TASK164_EVIDENCE_PACKAGE_PRESENTATION = "TASK164_EVIDENCE_PACKAGE_PRESENTATION"


class Task164CompletenessItem(StrEnum):
    AUTHORITY_CHAIN_EVIDENCE = "AUTHORITY_CHAIN_EVIDENCE"
    MAIN_DELIVERY_EVIDENCE = "MAIN_DELIVERY_EVIDENCE"
    TASK163_REPLAY_EVIDENCE = "TASK163_REPLAY_EVIDENCE"
    TASK163_IDENTITY_EVIDENCE = "TASK163_IDENTITY_EVIDENCE"
    TASK163_APPLICABILITY_EVIDENCE = "TASK163_APPLICABILITY_EVIDENCE"
    TASK163_COMPLETENESS_EVIDENCE = "TASK163_COMPLETENESS_EVIDENCE"
    TASK163_PROVENANCE_EVIDENCE = "TASK163_PROVENANCE_EVIDENCE"
    TERMINAL_CAPABILITY_EVIDENCE = "TERMINAL_CAPABILITY_EVIDENCE"
    POSITIVE_DEMONSTRATION_EVIDENCE = "POSITIVE_DEMONSTRATION_EVIDENCE"
    NEGATIVE_DEMONSTRATION_EVIDENCE = "NEGATIVE_DEMONSTRATION_EVIDENCE"
    REPEAT_RUN_EVIDENCE = "REPEAT_RUN_EVIDENCE"
    CROSS_PYTHON_EVIDENCE = "CROSS_PYTHON_EVIDENCE"
    SCOPE_FENCE_EVIDENCE = "SCOPE_FENCE_EVIDENCE"


class Task164MediaKind(StrEnum):
    CANONICAL_BYTES = "CANONICAL_BYTES"
    DIGEST_RECORD = "DIGEST_RECORD"
    SCENARIO_RECORD = "SCENARIO_RECORD"
    GRAPH_RECORD = "GRAPH_RECORD"


class Task164ForbiddenCapabilityToken(StrEnum):
    LMTD = "LMTD"
    LMTD_CORRECTION_FACTOR = "LMTD_CORRECTION_FACTOR"
    F_FACTOR = "F_FACTOR"
    NEW_NTU = "NEW_NTU"
    NEW_EFFECTIVENESS = "NEW_EFFECTIVENESS"
    NEW_HEAT_DUTY = "NEW_HEAT_DUTY"
    NEW_OUTLET_TEMPERATURE = "NEW_OUTLET_TEMPERATURE"
    NEW_ENERGY_BALANCE = "NEW_ENERGY_BALANCE"
    NEW_TERMINAL_TEMPERATURE = "NEW_TERMINAL_TEMPERATURE"
    TASK165 = "TASK165"


class Task164FailureCode(StrEnum):
    INVALID_REQUEST_TYPE = "INVALID_REQUEST_TYPE"
    INVALID_REQUEST_SCHEMA = "INVALID_REQUEST_SCHEMA"
    UNSUPPORTED_TASK164_VERSION = "UNSUPPORTED_TASK164_VERSION"
    SOURCE_DEFINITION_ID_MISMATCH = "SOURCE_DEFINITION_ID_MISMATCH"
    UNSUPPORTED_RAW_VALUE = "UNSUPPORTED_RAW_VALUE"
    RAW_UNICODE_ENCODING_FAILURE = "RAW_UNICODE_ENCODING_FAILURE"
    RAW_DEPTH_LIMIT_EXCEEDED = "RAW_DEPTH_LIMIT_EXCEEDED"
    RAW_NODE_LIMIT_EXCEEDED = "RAW_NODE_LIMIT_EXCEEDED"
    RAW_SCALAR_BYTE_LIMIT_EXCEEDED = "RAW_SCALAR_BYTE_LIMIT_EXCEEDED"
    TASK163_REQUEST_CONTEXT_MISSING = "TASK163_REQUEST_CONTEXT_MISSING"
    INVALID_TASK163_VALIDATION_RESULT = "INVALID_TASK163_VALIDATION_RESULT"
    INVALID_SCENARIO_EVIDENCE = "INVALID_SCENARIO_EVIDENCE"
    INVALID_DETERMINISM_EVIDENCE = "INVALID_DETERMINISM_EVIDENCE"
    INVALID_EVIDENCE_PACKAGE = "INVALID_EVIDENCE_PACKAGE"
    TASK163_RESULT_ALONE = "TASK163_RESULT_ALONE"
    TASK163_PRODUCER_EXCEPTION = "TASK163_PRODUCER_EXCEPTION"
    TASK163_REPLAY_BLOCKED = "TASK163_REPLAY_BLOCKED"
    TASK163_REPLAY_STATUS_MISMATCH = "TASK163_REPLAY_STATUS_MISMATCH"
    TASK163_RESULT_MISMATCH = "TASK163_RESULT_MISMATCH"
    TASK163_RESULT_HASH_MISMATCH = "TASK163_RESULT_HASH_MISMATCH"
    TASK163_RESULT_ID_MISMATCH = "TASK163_RESULT_ID_MISMATCH"
    TASK163_PROVENANCE_MISMATCH = "TASK163_PROVENANCE_MISMATCH"
    TASK163_APPLICABILITY_NOT_ACCEPTED = "TASK163_APPLICABILITY_NOT_ACCEPTED"
    TASK163_COMPLETENESS_NOT_ACCEPTED = "TASK163_COMPLETENESS_NOT_ACCEPTED"
    TERMINAL_CAPABILITY_UNSUPPORTED = "TERMINAL_CAPABILITY_UNSUPPORTED"
    SCENARIO_SET_MISMATCH = "SCENARIO_SET_MISMATCH"
    POSITIVE_DEMONSTRATION_FAILED = "POSITIVE_DEMONSTRATION_FAILED"
    NEGATIVE_FAIL_CLOSED_FAILED = "NEGATIVE_FAIL_CLOSED_FAILED"
    SCENARIO_EVIDENCE_INVALID = "SCENARIO_EVIDENCE_INVALID"
    REPEAT_RUN_PARITY_FAILED = "REPEAT_RUN_PARITY_FAILED"
    PYTHON_PARITY_FAILED = "PYTHON_PARITY_FAILED"
    UNSUPPORTED_PYTHON_VERSION = "UNSUPPORTED_PYTHON_VERSION"
    STALE_HEAD_PARITY_EVIDENCE = "STALE_HEAD_PARITY_EVIDENCE"
    WRONG_RUNTIME_PARITY_EVIDENCE = "WRONG_RUNTIME_PARITY_EVIDENCE"
    DUPLICATE_PARITY_PAIR = "DUPLICATE_PARITY_PAIR"
    MISSING_PARITY_PAIR = "MISSING_PARITY_PAIR"
    CONTRADICTORY_PARITY_EVIDENCE = "CONTRADICTORY_PARITY_EVIDENCE"
    SCOPE_FENCE_FAILED = "SCOPE_FENCE_FAILED"
    LMTD_OR_F_FACTOR_PRESENT = "LMTD_OR_F_FACTOR_PRESENT"
    UNAUTHORIZED_ENGINEERING_OUTPUT = "UNAUTHORIZED_ENGINEERING_OUTPUT"
    EVIDENCE_PACKAGE_INTEGRITY_FAILED = "EVIDENCE_PACKAGE_INTEGRITY_FAILED"
    ARTIFACT_DIGEST_MISMATCH = "ARTIFACT_DIGEST_MISMATCH"
    MAIN_DELIVERY_EVIDENCE_FAILED = "MAIN_DELIVERY_EVIDENCE_FAILED"
    EVIDENCE_CATEGORY_SUBSTITUTION = "EVIDENCE_CATEGORY_SUBSTITUTION"
    CALLER_EVIDENCE_SELF_AUTHORIZATION = "CALLER_EVIDENCE_SELF_AUTHORIZATION"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    PROVENANCE_CYCLE = "PROVENANCE_CYCLE"
    PROVENANCE_SELF_EDGE = "PROVENANCE_SELF_EDGE"
    IDENTITY_REPLAY_FAILED = "IDENTITY_REPLAY_FAILED"
    SUCCESS_HASH_MISMATCH = "SUCCESS_HASH_MISMATCH"
    RESULT_ID_MISMATCH = "RESULT_ID_MISMATCH"


TASK164_FAILURE_CODE_DECLARATION_ORDER: tuple[Task164FailureCode, ...] = tuple(Task164FailureCode)
TASK164_FAILURE_STAGE_ORDER: tuple[Task164FailureStage, ...] = tuple(Task164FailureStage)


@dataclass(frozen=True, slots=True)
class Task164ScenarioSetup:
    input_authority: Task164ScenarioInputAuthority
    baffle_count: int | None = None
    tamper_target: Task164TamperTarget | None = None
    python_pair_key: str | None = None


@dataclass(frozen=True, slots=True)
class Task164ScenarioClaim:
    scenario_id: Task164ScenarioId
    scenario_class: Task164ScenarioClass
    required_for_acceptance: bool
    input_setup: Task164ScenarioSetup
    original_task163_request: Task163Request | None
    claimed_task163_validation_result: Task163ValidationResult | None
    expected_task163_branch: Task164Task163Branch
    claimed_outcome: Task164ScenarioOutcome
    claimed_acceptance_categories: tuple[Task164AcceptanceCategory, ...]
    claimed_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164ObservedIdentity:
    result_hash: str
    result_id: str
    provenance_hash: str


@dataclass(frozen=True, slots=True)
class Task164Task163ReplayEvidence:
    scenario_id: Task164ScenarioId
    producer_invocation_count: int
    original_request_projection_hash: str
    claimed_validation_projection_hash: str | None
    replayed_validation_projection_hash: str
    replayed_branch: Task164Task163Branch
    replayed_result_hash_or_none: str | None
    replayed_result_id_or_none: str | None
    replayed_provenance_hash_or_none: str | None
    applicability_projection_hash_or_none: str | None
    completeness_projection_hash_or_none: str | None
    claim_match_status: Task164ClaimMatchStatus
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164ScenarioObservation:
    scenario_id: Task164ScenarioId
    real_task163_invoked: bool
    producer_invocation_count: int
    observed_task163_branch: Task164Task163Branch
    observed_task163_result_identity_or_none: Task164ObservedIdentity | None
    observed_task163_applicability_status_or_none: Task163ApplicabilityStatus | None
    observed_task163_completeness_status_or_none: Task163CompletenessStatus | None
    observed_outcome: Task164ScenarioOutcome
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164ScenarioRecord:
    scenario_id: Task164ScenarioId
    claim: Task164ScenarioClaim
    observation: Task164ScenarioObservation
    replay_evidence: Task164Task163ReplayEvidence
    acceptance_records: tuple[Task164AcceptanceCategoryRecord, ...]
    status: Task164EvidenceStatus


@dataclass(frozen=True, slots=True)
class Task164SurfaceHashRecord:
    surface: Task164RepeatRunSurface | Task164ParitySurface
    sha256: str
    authority: Task164EvidenceAuthority
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class Task164RepeatRunClaim:
    schema_version: str
    requested_run_count: int
    claimed_surface_records: tuple[Task164SurfaceHashRecord, ...]
    claimed_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164RepeatRunObservation:
    run_count: int
    surface_records: tuple[Task164SurfaceHashRecord, ...]
    observed_equal: bool
    status: Task164ParityStatus
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164PythonParityClaim:
    schema_version: str
    requested_pair: tuple[Task164PythonVersion, Task164PythonVersion]
    claimed_surface_records: tuple[Task164SurfaceHashRecord, ...]
    claimed_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164CrossPythonParityInput:
    schema_version: str
    original_task163_request_projection_hash: str
    task163_result_hash: str
    task163_result_id: str
    task163_provenance_hash: str
    applicability_projection_hash: str
    completeness_projection_hash: str
    scenario_matrix_projection_hash: str
    repeat_run_evidence_projection_hash: str
    terminal_capability_projection_hash: str
    scope_fence_projection_hash: str
    head_sha: str
    head_tree: str
    task164_design_version: str
    runtime_contract_version: str


@dataclass(frozen=True, slots=True)
class Task164RuntimeObservation:
    python_version: Task164PythonVersion
    head_sha: str
    head_tree: str
    runner_identity: Task164RunnerIdentity
    command_identity: Task164CommandIdentity
    surface_records: tuple[Task164SurfaceHashRecord, ...]
    child_output_sha256: str
    conclusion: Task164ParityStatus


@dataclass(frozen=True, slots=True)
class Task164DualRuntimeObservation:
    pairing_key: Task164PairingKey
    python311_observation: Task164RuntimeObservation
    python312_observation: Task164RuntimeObservation
    status: Task164ParityStatus
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164EvidencePayload:
    payload_kind: Task164EvidencePayloadKind
    category: Task164AcceptanceCategory
    authority: Task164EvidenceAuthority
    payload_sha256: str
    canonical_payload_bytes: bytes
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164ArtifactRecord:
    artifact_id: Task164PackageArtifactId
    media_kind: Task164MediaKind
    canonical_payload_hash: str
    authority: Task164EvidenceAuthority
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164EvidencePackageClaim:
    package_schema_version: str
    package_version: str
    claimed_category_payload_hashes: tuple[tuple[Task164AcceptanceCategory, str], ...]
    claimed_artifact_records: tuple[Task164ArtifactRecord, ...]
    claimed_package_hash: str | None
    claimed_evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Task164AcceptanceCategoryRecord:
    category: Task164AcceptanceCategory
    status: Task164AcceptanceCategoryStatus
    evidence_refs: tuple[str, ...]
    failure_code_or_none: Task164FailureCode | None


@dataclass(frozen=True, slots=True)
class Task164AcceptanceLedger:
    records: tuple[Task164AcceptanceCategoryRecord, ...]
    package_hash: str
    status: Task164AcceptanceLedgerStatus


@dataclass(frozen=True, slots=True)
class Task164EvidencePackage:
    package_schema_version: str
    package_version: str
    authority_evidence: Task164EvidencePayload
    main_delivery_evidence: Task164EvidencePayload
    task163_replay_evidence: Task164EvidencePayload
    task163_identity_evidence: Task164EvidencePayload
    task163_applicability_evidence: Task164EvidencePayload
    task163_completeness_evidence: Task164EvidencePayload
    task163_provenance_evidence: Task164EvidencePayload
    terminal_capability_evidence: Task164EvidencePayload
    positive_demo_evidence: Task164EvidencePayload
    negative_demo_evidence: Task164EvidencePayload
    repeat_run_evidence: Task164EvidencePayload
    cross_python_evidence: Task164EvidencePayload
    scope_fence_evidence: Task164EvidencePayload
    artifact_inventory: tuple[Task164ArtifactRecord, ...]


@dataclass(frozen=True, slots=True)
class Task164TerminalCapability:
    capability_id: Task164TerminalCapabilityId
    construction_family: Task164ConstructionFamily
    shell_pass_count: int
    tube_pass_count: int
    case_binding: Task164CaseBinding
    method_authority: Task164MethodAuthority
    rating_output_authority: Task164RatingOutputAuthority
    status: Task164EvidenceStatus


@dataclass(frozen=True, slots=True)
class Task164DemonstrationCoverage:
    required_scenario_ids: tuple[Task164ScenarioId, ...]
    scenario_records: tuple[Task164ScenarioRecord, ...]
    positive_count: int
    negative_count: int
    determinism_count: int
    scope_fence_count: int
    status: Task164EvidenceStatus


@dataclass(frozen=True, slots=True)
class Task164ApplicabilityRecord:
    check: Task164ApplicabilityCheck
    status: Task164AcceptanceCategoryStatus
    evidence_refs: tuple[str, ...]
    failure_code_or_none: Task164FailureCode | None


@dataclass(frozen=True, slots=True)
class Task164Applicability:
    records: tuple[Task164ApplicabilityRecord, ...]
    status: Task164ApplicabilityStatus


@dataclass(frozen=True, slots=True)
class Task164Completeness:
    required_items: tuple[Task164CompletenessItem, ...]
    status: Task164CompletenessStatus


@dataclass(frozen=True, slots=True)
class Task164ScopeFenceEvidence:
    forbidden_capability_tokens_absent: tuple[Task164ForbiddenCapabilityToken, ...]
    forbidden_formula_surface_absent: bool
    upstream_replay_absent: bool
    private_upstream_access_absent: bool
    task165_absent: bool
    status: Task164ScopeStatus


@dataclass(frozen=True, slots=True)
class Task164Task163Evidence:
    original_request_projection_hash: str
    replay_evidence: tuple[Task164Task163ReplayEvidence, ...]
    accepted_result_identities: tuple[Task164ObservedIdentity, ...]
    status: Task164EvidenceStatus


@dataclass(frozen=True, slots=True)
class Task164DeterminismEvidence:
    repeat_run_observation: Task164RepeatRunObservation
    dual_runtime_observation: Task164DualRuntimeObservation
    status: Task164ParityStatus


@dataclass(frozen=True, slots=True)
class Task164ProvenanceSemanticInputs:
    source_authority_payload_hash: str
    task163_evidence_payload_hash: str
    scenario_matrix_payload_hash: str
    determinism_payload_hash: str
    acceptance_ledger_payload_hash: str
    evidence_package_payload_hash: str


@dataclass(frozen=True, slots=True)
class Task164Provenance:
    provenance_hash: str
    graph: ProvenanceGraph


@dataclass(frozen=True, slots=True)
class Task164Blocker:
    stage: Task164FailureStage
    code: Task164FailureCode
    evidence_refs: tuple[str, ...] = ()


Task164Warnings = tuple[()]


@dataclass(frozen=True, slots=True)
class Task164Request:
    schema_version: str
    task164_version: str
    source_definition_id: str
    original_task163_request: Task163Request
    claimed_task163_validation_result: Task163ValidationResult
    scenario_claims: tuple[Task164ScenarioClaim, ...]
    repeat_run_claim: Task164RepeatRunClaim
    python_parity_claim: Task164PythonParityClaim
    evidence_package_claim: Task164EvidencePackageClaim
    request_metadata: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class Task164Result:
    schema_version: str
    task164_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    original_task163_request_projection: bytes
    task163_evidence: Task164Task163Evidence
    scenario_evidence: tuple[Task164ScenarioRecord, ...]
    determinism_evidence: Task164DeterminismEvidence
    terminal_capability: Task164TerminalCapability
    demonstration_coverage: Task164DemonstrationCoverage
    scope_fence_evidence: Task164ScopeFenceEvidence
    applicability: Task164Applicability
    completeness: Task164Completeness
    evidence_package: Task164EvidencePackage
    acceptance_ledger: Task164AcceptanceLedger
    warnings: Task164Warnings
    blockers: tuple[Task164Blocker, ...]
    provenance_semantic_inputs: Task164ProvenanceSemanticInputs
    provenance: Task164Provenance
    result_hash: str
    result_id: UUID


@dataclass(frozen=True, slots=True)
class Task164TypedBlockedResult:
    schema_version: str
    task164_version: str
    implementation_software_version: str
    failure_stage: Task164FailureStage
    request_hash: str
    original_task163_request_projection_hash_or_none: str | None
    blockers: tuple[Task164Blocker, ...]
    warnings: Task164Warnings
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task164RawProjectionNode:
    field_name: str
    kind: Task164RawProjectionKind
    type_identity: str | None
    scalar_payload: str | None
    children: tuple[Task164RawProjectionNode, ...]

    def __post_init__(self) -> None:
        if type(self.field_name) is not str:
            raise TypeError("field_name must be exact str")
        if type(self.kind) is not Task164RawProjectionKind:
            raise TypeError("kind must be exact Task164RawProjectionKind")
        if self.kind is Task164RawProjectionKind.LIMIT_MARKER:
            if (
                self.field_name != "__TASK164_LIMIT_MARKER__"
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
                raise ValueError("invalid TASK164 limit marker")
            return
        if type(self.type_identity) not in (str, type(None)):
            raise TypeError("type_identity must be str or None")
        if type(self.scalar_payload) not in (str, type(None)):
            raise TypeError("scalar_payload must be str or None")
        if type(self.children) is not tuple or any(
            type(child) is not Task164RawProjectionNode for child in self.children
        ):
            raise TypeError("children must be a tuple of exact raw nodes")


class Task164RawProjectionKind(StrEnum):
    RECORD = "RECORD"
    SEQUENCE = "SEQUENCE"
    STRING = "STRING"
    BYTES = "BYTES"
    INT = "INT"
    DECIMAL = "DECIMAL"
    ENUM = "ENUM"
    BOOL = "BOOL"
    NONE = "NONE"
    LIMIT_MARKER = "LIMIT_MARKER"


@dataclass(frozen=True, slots=True)
class Task164RawRequestProjection:
    schema_version: str
    root: Task164RawProjectionNode


@dataclass(frozen=True, slots=True)
class Task164RawBoundaryBlockedResult:
    schema_version: str
    task164_version: str
    implementation_software_version: str
    failure_stage: Task164FailureStage
    raw_request_projection: Task164RawRequestProjection
    raw_request_projection_hash: str
    blockers: tuple[Task164Blocker, ...]
    warnings: Task164Warnings
    blocked_result_hash: str
    blocked_result_id: UUID


@dataclass(frozen=True, slots=True)
class Task164ValidationResult:
    status: Task164ValidationBranch
    raw_boundary_blocked: Task164RawBoundaryBlockedResult | None = None
    typed_blocked: Task164TypedBlockedResult | None = None
    valid: Task164Result | None = None

    def __post_init__(self) -> None:
        branches = (self.raw_boundary_blocked, self.typed_blocked, self.valid)
        if sum(item is not None for item in branches) != 1:
            raise ValueError("exactly one TASK164 validation branch must be populated")
        expected = {
            Task164ValidationBranch.RAW_BOUNDARY_BLOCKED: self.raw_boundary_blocked,
            Task164ValidationBranch.TYPED_BLOCKED: self.typed_blocked,
            Task164ValidationBranch.VALID: self.valid,
        }[self.status]
        if expected is None:
            raise ValueError("status does not match populated TASK164 branch")


TASK164_SCENARIO_IDS: tuple[Task164ScenarioId, ...] = (
    Task164ScenarioId.D164_P01_SUCCESS_BAFFLE_1,
    Task164ScenarioId.D164_P02_SUCCESS_BAFFLE_2,
    Task164ScenarioId.D164_P03_SUCCESS_BAFFLE_3,
    Task164ScenarioId.D164_P04_SUCCESS_BAFFLE_4,
    Task164ScenarioId.D164_P05_SUCCESS_BAFFLE_5,
    Task164ScenarioId.D164_N01_TASK163_TYPED_BLOCKED,
    Task164ScenarioId.D164_N02_TASK163_RAW_BOUNDARY_BLOCKED,
    Task164ScenarioId.D164_N03_TASK162_PRODUCER_ACCEPTANCE_OR_REPLAY_REJECTION,
    Task164ScenarioId.D164_N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER,
    Task164ScenarioId.D164_D01_REPEAT_RUN_IDENTITY_AND_EVIDENCE_PARITY,
    Task164ScenarioId.D164_D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY,
    Task164ScenarioId.D164_S01_SCOPE_FENCE_NO_LMTD_OR_F_FACTOR,
)
TASK164_SCENARIO_SOURCE_ORDER: dict[Task164ScenarioId, int] = {
    value: index for index, value in enumerate(TASK164_SCENARIO_IDS)
}
TASK164_COMPLETENESS_ITEMS: tuple[Task164CompletenessItem, ...] = tuple(Task164CompletenessItem)
TASK164_ACCEPTANCE_CATEGORIES: tuple[Task164AcceptanceCategory, ...] = tuple(
    Task164AcceptanceCategory
)
TASK164_ACCEPTANCE_CATEGORY_TO_PAYLOAD: dict[
    Task164AcceptanceCategory, Task164EvidencePayloadKind | None
] = {
    category: payload
    for category, payload in zip(
        TASK164_ACCEPTANCE_CATEGORIES,
        (
            Task164EvidencePayloadKind.AUTHORITY_CHAIN_PAYLOAD,
            Task164EvidencePayloadKind.MAIN_DELIVERY_PAYLOAD,
            Task164EvidencePayloadKind.TASK163_REPLAY_PAYLOAD,
            Task164EvidencePayloadKind.TASK163_IDENTITY_PAYLOAD,
            Task164EvidencePayloadKind.TASK163_APPLICABILITY_PAYLOAD,
            Task164EvidencePayloadKind.TASK163_COMPLETENESS_PAYLOAD,
            Task164EvidencePayloadKind.TASK163_PROVENANCE_PAYLOAD,
            Task164EvidencePayloadKind.TERMINAL_CAPABILITY_PAYLOAD,
            Task164EvidencePayloadKind.POSITIVE_DEMONSTRATION_PAYLOAD,
            Task164EvidencePayloadKind.NEGATIVE_DEMONSTRATION_PAYLOAD,
            Task164EvidencePayloadKind.REPEAT_RUN_PAYLOAD,
            Task164EvidencePayloadKind.PYTHON_PARITY_PAYLOAD,
            Task164EvidencePayloadKind.SCOPE_FENCE_PAYLOAD,
            None,
        ),
        strict=True,
    )
}
TASK164_ALLOWLIST: tuple[str, ...] = (
    "src/hexagent/release_demo/task164_integration_release_acceptance/__init__.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/models.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/errors.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/canonical.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/raw_projection.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/provenance.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/scenarios.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/trusted_evidence.py",
    "src/hexagent/release_demo/task164_integration_release_acceptance/service.py",
    "tests/release_demo/test_task164_integration_release_acceptance.py",
    "ci-shard-manifest.yml",
    ".github/workflows/ci.yml",
)
TASK164_SUCCESS_PREIMAGE_FIELD_ORDER: tuple[str, ...] = (
    "schema_version",
    "task164_version",
    "implementation_software_version",
    "source_definition_id",
    "request_hash",
    "original_task163_request_projection",
    "task163_evidence",
    "scenario_evidence",
    "determinism_evidence",
    "terminal_capability",
    "demonstration_coverage",
    "scope_fence_evidence",
    "applicability",
    "completeness",
    "evidence_package",
    "acceptance_ledger",
    "warnings_normalized",
    "blockers_normalized",
    "provenance_semantic_inputs",
)


@dataclass(frozen=True, slots=True)
class Task164PreResultIdentityInputs:
    schema_version: str
    task164_version: str
    implementation_software_version: str
    source_definition_id: str
    request_hash: str
    original_task163_request_projection: bytes
    task163_evidence: Task164Task163Evidence
    scenario_evidence: tuple[Task164ScenarioRecord, ...]
    determinism_evidence: Task164DeterminismEvidence
    terminal_capability: Task164TerminalCapability
    demonstration_coverage: Task164DemonstrationCoverage
    scope_fence_evidence: Task164ScopeFenceEvidence
    applicability: Task164Applicability
    completeness: Task164Completeness
    evidence_package: Task164EvidencePackage
    acceptance_ledger: Task164AcceptanceLedger
    warnings_normalized: Task164Warnings
    blockers_normalized: tuple[Task164Blocker, ...]
    provenance_semantic_inputs: Task164ProvenanceSemanticInputs


__all__ = [name for name in globals() if name.startswith("TASK164_") or name.startswith("Task164")]
