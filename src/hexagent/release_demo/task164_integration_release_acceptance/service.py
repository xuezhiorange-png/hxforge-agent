"""TASK164 integration, demonstration, and release-acceptance service."""

from __future__ import annotations

import hashlib
import os
from dataclasses import replace
from typing import Any

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task163ApplicabilityCheckName,
    Task163ApplicabilityStatus,
    Task163CompletenessField,
    Task163CompletenessStatus,
    Task163Request,
    Task163ValidationResult,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.service import (
    validate_request as validate_task163_request,
)
from hexagent.exchangers.shell_tube.tube_side.canonical import (
    KIND_BYTES,
    KIND_ENUM,
    KIND_INT,
    frame_record,
)

from .canonical import (
    determinism_evidence_bytes,
    evidence_package_bytes,
    main_delivery_payload_bytes,
    negative_demonstration_payload_bytes,
    positive_demonstration_payload_bytes,
    provenance_hash,
    python_parity_payload_bytes,
    raw_blocked_hash,
    raw_blocked_id,
    repeat_run_payload_bytes,
    request_hash,
    result_id,
    scenario_matrix_bytes,
    scope_fence_bytes,
    success_hash_from_inputs,
    task163_applicability_payload_bytes,
    task163_completeness_payload_bytes,
    task163_identity_payload_bytes,
    task163_provenance_payload_bytes,
    task163_replay_payload_bytes,
    task163_request_projection_bytes,
    task163_request_projection_hash,
    task163_validation_projection_bytes,
    terminal_capability_bytes,
    typed_blocked_hash,
    typed_blocked_id,
)
from .errors import blocker, normalize_blockers
from .models import (
    TASK164_ACCEPTANCE_CATEGORIES,
    TASK164_COMPLETENESS_ITEMS,
    TASK164_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK164_RAW_BOUNDARY_SCHEMA_VERSION,
    TASK164_SCENARIO_IDS,
    TASK164_SCENARIO_SOURCE_ORDER,
    TASK164_SCHEMA_VERSION,
    TASK164_SOURCE_DEFINITION_ID,
    TASK164_TYPED_BLOCKED_SCHEMA_VERSION,
    TASK164_VERSION,
    Task164AcceptanceCategory,
    Task164AcceptanceCategoryRecord,
    Task164AcceptanceCategoryStatus,
    Task164AcceptanceLedger,
    Task164AcceptanceLedgerStatus,
    Task164Applicability,
    Task164ApplicabilityCheck,
    Task164ApplicabilityRecord,
    Task164ApplicabilityStatus,
    Task164ArtifactRecord,
    Task164Blocker,
    Task164CaseBinding,
    Task164CommandIdentity,
    Task164Completeness,
    Task164CompletenessStatus,
    Task164ConstructionFamily,
    Task164CrossPythonParityInput,
    Task164DemonstrationCoverage,
    Task164DeterminismEvidence,
    Task164DualRuntimeObservation,
    Task164EvidenceAuthority,
    Task164EvidencePackage,
    Task164EvidencePackageClaim,
    Task164EvidencePayload,
    Task164EvidencePayloadKind,
    Task164EvidenceStatus,
    Task164FailureCode,
    Task164FailureStage,
    Task164ForbiddenCapabilityToken,
    Task164MethodAuthority,
    Task164PackageArtifactId,
    Task164PairingKey,
    Task164ParityStatus,
    Task164PreResultIdentityInputs,
    Task164Provenance,
    Task164PythonParityClaim,
    Task164PythonVersion,
    Task164RawBoundaryBlockedResult,
    Task164RepeatRunClaim,
    Task164RepeatRunObservation,
    Task164RepeatRunSurface,
    Task164Request,
    Task164Result,
    Task164RunnerIdentity,
    Task164RuntimeObservation,
    Task164ScenarioClaim,
    Task164ScenarioRecord,
    Task164ScopeFenceEvidence,
    Task164ScopeStatus,
    Task164SurfaceHashRecord,
    Task164Task163Branch,
    Task164Task163Evidence,
    Task164TerminalCapability,
    Task164TypedBlockedResult,
    Task164ValidationBranch,
    Task164ValidationResult,
)
from .provenance import build_provenance_semantic_inputs, build_success_provenance
from .raw_projection import project_raw_request_with_diagnostics
from .scenarios import execute_scenario, task163_request_raw
from .trusted_evidence import observe_dual_runtime, observe_main_delivery, observe_scope_fence

TASK163_APPLICABILITY_CHECKS = tuple(item.value for item in Task163ApplicabilityCheckName)
TASK163_COMPLETENESS_FIELDS = tuple(item.value for item in Task163CompletenessField)
_EXPECTED_REQUEST_KEYS = frozenset(
    {
        "schema_version",
        "task164_version",
        "source_definition_id",
        "original_task163_request",
        "claimed_task163_validation_result",
        "scenario_claims",
        "repeat_run_claim",
        "python_parity_claim",
        "evidence_package_claim",
        "request_metadata",
    }
)


def _metadata(value: object) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        raise ValueError("metadata must be an exact tuple")
    pairs: list[tuple[str, str]] = []
    for pair in value:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("metadata pair must be a two-tuple")
        key, item = pair
        if type(key) is not str or type(item) is not str:
            raise ValueError("metadata members must be exact strings")
        key.encode("utf-8", "strict")
        item.encode("utf-8", "strict")
        pairs.append((key, item))
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate metadata key")
    return tuple(sorted(pairs, key=lambda pair: (pair[0].encode("utf-8"), pair[1].encode("utf-8"))))


def _raw_admission_codes(raw: object) -> tuple[Task164FailureCode, ...]:
    codes: list[Task164FailureCode] = []

    def add(code: Task164FailureCode) -> None:
        if code not in codes:
            codes.append(code)

    if type(raw) is not dict:
        add(Task164FailureCode.INVALID_REQUEST_TYPE)
        return tuple(codes)
    try:
        keys = tuple(raw.keys())
        if any(type(key) is not str for key in keys) or frozenset(keys) != _EXPECTED_REQUEST_KEYS:
            add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
        for name in ("schema_version", "task164_version", "source_definition_id"):
            if type(raw.get(name)) is not str:
                add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
        if (
            type(raw.get("schema_version")) is str
            and raw["schema_version"] != TASK164_SCHEMA_VERSION
        ):
            add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
        if type(raw.get("task164_version")) is str and raw["task164_version"] != TASK164_VERSION:
            add(Task164FailureCode.UNSUPPORTED_TASK164_VERSION)
        if (
            type(raw.get("source_definition_id")) is str
            and raw["source_definition_id"] != TASK164_SOURCE_DEFINITION_ID
        ):
            add(Task164FailureCode.SOURCE_DEFINITION_ID_MISMATCH)
        metadata = raw.get("request_metadata")
        if type(metadata) is not tuple:
            add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
        else:
            seen: set[str] = set()
            for pair in metadata:
                if type(pair) is not tuple or len(pair) != 2:
                    add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
                    continue
                key, item = pair
                if type(key) is not str or type(item) is not str:
                    add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
                    continue
                try:
                    key.encode("utf-8", "strict")
                    item.encode("utf-8", "strict")
                except UnicodeEncodeError:
                    add(Task164FailureCode.RAW_UNICODE_ENCODING_FAILURE)
                if key in seen:
                    add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
                seen.add(key)
    except BaseException:
        add(Task164FailureCode.INVALID_REQUEST_SCHEMA)
    return tuple(codes)


def _raw_blocked(
    projection: object,
    projection_hash: str,
    codes: tuple[Task164FailureCode, ...],
) -> Task164ValidationResult:
    normalized_codes = tuple(dict.fromkeys(codes)) or (Task164FailureCode.UNSUPPORTED_RAW_VALUE,)
    blockers = normalize_blockers(
        blocker(code, Task164FailureStage.RAW_BOUNDARY) for code in normalized_codes
    )
    preliminary = Task164RawBoundaryBlockedResult(
        schema_version=TASK164_RAW_BOUNDARY_SCHEMA_VERSION,
        task164_version=TASK164_VERSION,
        implementation_software_version=TASK164_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=Task164FailureStage.RAW_BOUNDARY,
        raw_request_projection=projection,  # type: ignore[arg-type]
        raw_request_projection_hash=projection_hash,
        blockers=blockers,
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=raw_blocked_id("0" * 64),
    )
    value = replace(preliminary, blocked_result_hash=raw_blocked_hash(preliminary))
    return Task164ValidationResult(
        status=Task164ValidationBranch.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=replace(
            value, blocked_result_id=raw_blocked_id(value.blocked_result_hash)
        ),
    )


def _typed_blocked(
    request_hash_value: str,
    blockers: tuple[Task164Blocker, ...],
    stage: Task164FailureStage,
    raw_projection_hash: str | None,
) -> Task164ValidationResult:
    normalized = normalize_blockers(blockers)
    if not normalized:
        normalized = (blocker(Task164FailureCode.IDENTITY_REPLAY_FAILED, stage),)
    preliminary = Task164TypedBlockedResult(
        schema_version=TASK164_TYPED_BLOCKED_SCHEMA_VERSION,
        task164_version=TASK164_VERSION,
        implementation_software_version=TASK164_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash=request_hash_value,
        original_task163_request_projection_hash_or_none=raw_projection_hash,
        blockers=normalized,
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=typed_blocked_id("0" * 64),
    )
    value = replace(preliminary, blocked_result_hash=typed_blocked_hash(preliminary))
    return Task164ValidationResult(
        status=Task164ValidationBranch.TYPED_BLOCKED,
        typed_blocked=replace(value, blocked_result_id=typed_blocked_id(value.blocked_result_hash)),
    )


def _parse_request(raw: object) -> tuple[Task164Request | None, tuple[Task164Blocker, ...]]:
    stage = Task164FailureStage.TYPED_VALIDATION
    if type(raw) is not dict:
        return None, (blocker(Task164FailureCode.INVALID_REQUEST_TYPE, stage),)
    try:
        if frozenset(raw.keys()) != _EXPECTED_REQUEST_KEYS:
            return None, (blocker(Task164FailureCode.INVALID_REQUEST_SCHEMA, stage),)
        if (
            type(raw["schema_version"]) is not str
            or raw["schema_version"] != TASK164_SCHEMA_VERSION
        ):
            return None, (blocker(Task164FailureCode.INVALID_REQUEST_SCHEMA, stage),)
        if type(raw["task164_version"]) is not str or raw["task164_version"] != TASK164_VERSION:
            return None, (blocker(Task164FailureCode.UNSUPPORTED_TASK164_VERSION, stage),)
        if (
            type(raw["source_definition_id"]) is not str
            or raw["source_definition_id"] != TASK164_SOURCE_DEFINITION_ID
        ):
            return None, (blocker(Task164FailureCode.SOURCE_DEFINITION_ID_MISMATCH, stage),)
        if type(raw["original_task163_request"]) is not Task163Request:
            return None, (blocker(Task164FailureCode.TASK163_REQUEST_CONTEXT_MISSING, stage),)
        if type(raw["claimed_task163_validation_result"]) is not Task163ValidationResult:
            return None, (blocker(Task164FailureCode.INVALID_TASK163_VALIDATION_RESULT, stage),)
        claims = raw["scenario_claims"]
        if type(claims) is not tuple or any(
            type(item) is not Task164ScenarioClaim for item in claims
        ):
            return None, (blocker(Task164FailureCode.INVALID_SCENARIO_EVIDENCE, stage),)
        if type(raw["repeat_run_claim"]) is not Task164RepeatRunClaim:
            return None, (blocker(Task164FailureCode.INVALID_DETERMINISM_EVIDENCE, stage),)
        if type(raw["python_parity_claim"]) is not Task164PythonParityClaim:
            return None, (blocker(Task164FailureCode.INVALID_DETERMINISM_EVIDENCE, stage),)
        if type(raw["evidence_package_claim"]) is not Task164EvidencePackageClaim:
            return None, (blocker(Task164FailureCode.INVALID_EVIDENCE_PACKAGE, stage),)
        metadata = _metadata(raw["request_metadata"])
        return (
            Task164Request(
                schema_version=raw["schema_version"],
                task164_version=raw["task164_version"],
                source_definition_id=raw["source_definition_id"],
                original_task163_request=raw["original_task163_request"],
                claimed_task163_validation_result=raw["claimed_task163_validation_result"],
                scenario_claims=claims,
                repeat_run_claim=raw["repeat_run_claim"],
                python_parity_claim=raw["python_parity_claim"],
                evidence_package_claim=raw["evidence_package_claim"],
                request_metadata=metadata,
            ),
            (),
        )
    except BaseException:
        return None, (blocker(Task164FailureCode.INVALID_REQUEST_SCHEMA, stage),)


def _task163_branch(value: Task163ValidationResult) -> Task164Task163Branch:
    if value.valid is not None:
        return Task164Task163Branch.VALID
    if value.typed_blocked is not None:
        return Task164Task163Branch.TYPED_BLOCKED
    if value.raw_boundary_blocked is not None:
        return Task164Task163Branch.RAW_BOUNDARY_BLOCKED
    return Task164Task163Branch.NOT_APPLICABLE


def _replay_task163(
    request: Task163Request,
) -> tuple[Task163ValidationResult | None, tuple[Task164Blocker, ...]]:
    try:
        outcome = validate_task163_request(task163_request_raw(request))
    except BaseException:
        return None, (
            blocker(
                Task164FailureCode.TASK163_PRODUCER_EXCEPTION,
                Task164FailureStage.TASK163_REPLAY,
            ),
        )
    if type(outcome) is not Task163ValidationResult:
        return None, (
            blocker(
                Task164FailureCode.TASK163_PRODUCER_EXCEPTION,
                Task164FailureStage.TASK163_REPLAY,
            ),
        )
    return outcome, ()


def _compare_replay(
    claimed: Task163ValidationResult,
    replayed: Task163ValidationResult,
) -> tuple[Task164Blocker, ...]:
    stage = Task164FailureStage.TASK163_REPLAY
    try:
        if _task163_branch(claimed) is not _task163_branch(replayed):
            return (blocker(Task164FailureCode.TASK163_REPLAY_STATUS_MISMATCH, stage),)
        if claimed.valid is not None and replayed.valid is not None:
            if claimed.valid.result_hash != replayed.valid.result_hash:
                return (blocker(Task164FailureCode.TASK163_RESULT_HASH_MISMATCH, stage),)
            if claimed.valid.result_id != replayed.valid.result_id:
                return (blocker(Task164FailureCode.TASK163_RESULT_ID_MISMATCH, stage),)
            if (
                claimed.valid.provenance.provenance_hash
                != replayed.valid.provenance.provenance_hash
            ):
                return (blocker(Task164FailureCode.TASK163_PROVENANCE_MISMATCH, stage),)
        if task163_validation_projection_bytes(claimed) != task163_validation_projection_bytes(
            replayed
        ):
            return (blocker(Task164FailureCode.TASK163_RESULT_MISMATCH, stage),)
    except BaseException:
        return (blocker(Task164FailureCode.TASK163_RESULT_MISMATCH, stage),)
    return ()


def _task163_acceptance(value: Task163ValidationResult) -> tuple[Task164Blocker, ...]:
    if value.valid is None:
        return (
            blocker(Task164FailureCode.TASK163_REPLAY_BLOCKED, Task164FailureStage.TASK163_REPLAY),
        )
    result = value.valid
    failures: list[Task164Blocker] = []
    try:
        checks = tuple((name.value, status.value) for name, status in result.applicability.checks)
        expected = tuple((name, "PASS") for name in TASK163_APPLICABILITY_CHECKS)
        if (
            len(checks) != 6
            or checks != expected
            or result.applicability.status is not Task163ApplicabilityStatus.APPLICABLE
        ):
            failures.append(
                blocker(
                    Task164FailureCode.TASK163_APPLICABILITY_NOT_ACCEPTED,
                    Task164FailureStage.TASK163_ACCEPTANCE,
                )
            )
    except BaseException:
        failures.append(
            blocker(
                Task164FailureCode.TASK163_APPLICABILITY_NOT_ACCEPTED,
                Task164FailureStage.TASK163_ACCEPTANCE,
            )
        )
    try:
        fields = tuple(item.value for item in result.completeness.required_fields)
        if (
            len(fields) != 14
            or fields != TASK163_COMPLETENESS_FIELDS
            or result.completeness.status is not Task163CompletenessStatus.COMPLETE
        ):
            failures.append(
                blocker(
                    Task164FailureCode.TASK163_COMPLETENESS_NOT_ACCEPTED,
                    Task164FailureStage.TASK163_ACCEPTANCE,
                )
            )
    except BaseException:
        failures.append(
            blocker(
                Task164FailureCode.TASK163_COMPLETENESS_NOT_ACCEPTED,
                Task164FailureStage.TASK163_ACCEPTANCE,
            )
        )
    return tuple(failures)


def _terminal_capability() -> Task164TerminalCapability:
    from .models import Task164RatingOutputAuthority, Task164TerminalCapabilityId

    return Task164TerminalCapability(
        capability_id=Task164TerminalCapabilityId.TASK164_FIXED_TUBESHEET_RATING_OUTPUT_CAPABILITY,
        construction_family=Task164ConstructionFamily.FIXED_TUBESHEET,
        shell_pass_count=1,
        tube_pass_count=1,
        case_binding=Task164CaseBinding.TASK162_CURRENT_CASE_AUTHORITY,
        method_authority=Task164MethodAuthority.TASK161_CATALOG_AND_TASK162_SELECTED_RELATION,
        rating_output_authority=Task164RatingOutputAuthority.TASK162_AND_TASK163_PRODUCER_OUTPUTS_ONLY,
        status=Task164EvidenceStatus.PASS,
    )


def _scope_fence() -> Task164ScopeFenceEvidence:
    return observe_scope_fence()


def _sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _surface_records(
    *,
    request_projection: bytes,
    evidence: Task164Task163Evidence,
    scenarios: tuple[Task164ScenarioRecord, ...],
    terminal: Task164TerminalCapability,
    scope: Task164ScopeFenceEvidence,
) -> tuple[Task164SurfaceHashRecord, ...]:
    pre_determinism = frame_record(
        "TASK164_PRE_DETERMINISM_PAYLOADS_V1",
        (
            ("request_projection", KIND_BYTES, request_projection),
            ("replay_evidence", KIND_BYTES, task163_replay_payload_bytes(evidence)),
            ("scenario_evidence", KIND_BYTES, scenario_matrix_bytes(scenarios)),
            ("terminal_capability", KIND_BYTES, terminal_capability_bytes(terminal)),
            ("scope_fence", KIND_BYTES, scope_fence_bytes(scope)),
        ),
    )
    payloads = (
        (Task164RepeatRunSurface.TASK164_TASK163_REQUEST_PROJECTION, request_projection),
        (
            Task164RepeatRunSurface.TASK164_TASK163_REPLAY_EVIDENCE,
            task163_replay_payload_bytes(evidence),
        ),
        (
            Task164RepeatRunSurface.TASK164_SCENARIO_EVIDENCE,
            scenario_matrix_bytes(scenarios),
        ),
        (
            Task164RepeatRunSurface.TASK164_TERMINAL_CAPABILITY,
            terminal_capability_bytes(terminal),
        ),
        (Task164RepeatRunSurface.TASK164_SCOPE_FENCE, scope_fence_bytes(scope)),
        (Task164RepeatRunSurface.TASK164_PRE_DETERMINISM_PAYLOADS, pre_determinism),
    )
    return tuple(
        Task164SurfaceHashRecord(
            surface=surface,
            sha256=_sha(payload),
            authority=Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
            evidence_ref=surface.value,
        )
        for surface, payload in payloads
    )


def _valid_scenario_set(
    claims: tuple[Task164ScenarioClaim, ...],
) -> tuple[dict[Any, Task164ScenarioClaim] | None, tuple[Task164Blocker, ...]]:
    stage = Task164FailureStage.DEMONSTRATION
    if len(claims) != len(TASK164_SCENARIO_IDS):
        return None, (blocker(Task164FailureCode.SCENARIO_SET_MISMATCH, stage),)
    by_id: dict[Any, Task164ScenarioClaim] = {}
    for claim in claims:
        if type(claim.scenario_id) is not type(TASK164_SCENARIO_IDS[0]):
            return None, (blocker(Task164FailureCode.SCENARIO_SET_MISMATCH, stage),)
        if claim.scenario_id in by_id:
            return None, (blocker(Task164FailureCode.SCENARIO_SET_MISMATCH, stage),)
        by_id[claim.scenario_id] = claim
    ordered = tuple(sorted(by_id, key=lambda item: TASK164_SCENARIO_SOURCE_ORDER.get(item, 999)))
    if ordered != TASK164_SCENARIO_IDS:
        return None, (blocker(Task164FailureCode.SCENARIO_SET_MISMATCH, stage),)
    return by_id, ()


def _applicability() -> Task164Applicability:
    records = tuple(
        Task164ApplicabilityRecord(
            check=check,
            status=Task164AcceptanceCategoryStatus.PASS,
            evidence_refs=(),
            failure_code_or_none=None,
        )
        for check in Task164ApplicabilityCheck
    )
    return Task164Applicability(records=records, status=Task164ApplicabilityStatus.APPLICABLE)


def _completeness() -> Task164Completeness:
    return Task164Completeness(
        required_items=TASK164_COMPLETENESS_ITEMS,
        status=Task164CompletenessStatus.COMPLETE,
    )


def _payload(
    kind: Task164EvidencePayloadKind,
    category: Task164AcceptanceCategory,
    authority: Task164EvidenceAuthority,
    content: bytes,
    refs: tuple[str, ...],
) -> Task164EvidencePayload:
    return Task164EvidencePayload(
        payload_kind=kind,
        category=category,
        authority=authority,
        payload_sha256=_sha(content),
        canonical_payload_bytes=content,
        evidence_refs=tuple(sorted(set(refs), key=lambda value: value.encode("utf-8"))),
    )


def _build_payloads(
    *,
    main_delivery: Any,
    task163_evidence: Task164Task163Evidence,
    scenarios: tuple[Task164ScenarioRecord, ...],
    determinism: Task164DeterminismEvidence,
    terminal: Task164TerminalCapability,
    scope: Task164ScopeFenceEvidence,
    producer_applicability: object,
    producer_completeness: object,
    original_projection: bytes,
) -> tuple[Task164EvidencePackage, Task164AcceptanceLedger]:
    authority = _payload(
        Task164EvidencePayloadKind.AUTHORITY_CHAIN_PAYLOAD,
        Task164AcceptanceCategory.AUTHORITY_CHAIN_INTEGRITY,
        Task164EvidenceAuthority.FROZEN_AUTHORITY,
        _authority_bytes(),
        ("#243", "#245"),
    )
    delivery = _payload(
        Task164EvidencePayloadKind.MAIN_DELIVERY_PAYLOAD,
        Task164AcceptanceCategory.DELIVERED_MAIN_AND_PREDECESSOR_INTEGRITY,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        main_delivery_payload_bytes(main_delivery),
        ("LOCAL_GIT_READONLY_V1",),
    )
    replay = _payload(
        Task164EvidencePayloadKind.TASK163_REPLAY_PAYLOAD,
        Task164AcceptanceCategory.TASK163_PUBLIC_BOUNDARY_ACCEPTANCE,
        Task164EvidenceAuthority.TASK163_PRODUCER,
        task163_replay_payload_bytes(task163_evidence),
        ("TASK163_PRODUCER",),
    )
    identity = _payload(
        Task164EvidencePayloadKind.TASK163_IDENTITY_PAYLOAD,
        Task164AcceptanceCategory.TASK163_RESULT_IDENTITY_ACCEPTANCE,
        Task164EvidenceAuthority.TASK163_PRODUCER,
        task163_identity_payload_bytes(task163_evidence),
        ("TASK163_PRODUCER",),
    )
    app = _payload(
        Task164EvidencePayloadKind.TASK163_APPLICABILITY_PAYLOAD,
        Task164AcceptanceCategory.TASK163_APPLICABILITY_ACCEPTANCE,
        Task164EvidenceAuthority.TASK163_PRODUCER,
        task163_applicability_payload_bytes(producer_applicability),  # type: ignore[arg-type]
        ("TASK163_PRODUCER",),
    )
    comp = _payload(
        Task164EvidencePayloadKind.TASK163_COMPLETENESS_PAYLOAD,
        Task164AcceptanceCategory.TASK163_COMPLETENESS_ACCEPTANCE,
        Task164EvidenceAuthority.TASK163_PRODUCER,
        task163_completeness_payload_bytes(producer_completeness),  # type: ignore[arg-type]
        ("TASK163_PRODUCER",),
    )
    prov = _payload(
        Task164EvidencePayloadKind.TASK163_PROVENANCE_PAYLOAD,
        Task164AcceptanceCategory.TASK163_PROVENANCE_ACCEPTANCE,
        Task164EvidenceAuthority.TASK163_PRODUCER,
        task163_provenance_payload_bytes(task163_evidence),
        ("TASK163_PRODUCER",),
    )
    terminal_payload = _payload(
        Task164EvidencePayloadKind.TERMINAL_CAPABILITY_PAYLOAD,
        Task164AcceptanceCategory.SUPPORTED_TERMINAL_CAPABILITY_COVERAGE,
        Task164EvidenceAuthority.FROZEN_AUTHORITY,
        terminal_capability_bytes(terminal),
        ("TASK164_TERMINAL_CAPABILITY",),
    )
    positive = _payload(
        Task164EvidencePayloadKind.POSITIVE_DEMONSTRATION_PAYLOAD,
        Task164AcceptanceCategory.POSITIVE_DEMONSTRATION_COVERAGE,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        positive_demonstration_payload_bytes(scenarios),
        ("TASK164_SCENARIO_MATRIX",),
    )
    negative = _payload(
        Task164EvidencePayloadKind.NEGATIVE_DEMONSTRATION_PAYLOAD,
        Task164AcceptanceCategory.NEGATIVE_FAIL_CLOSED_COVERAGE,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        negative_demonstration_payload_bytes(scenarios),
        ("TASK164_SCENARIO_MATRIX",),
    )
    repeat = _payload(
        Task164EvidencePayloadKind.REPEAT_RUN_PAYLOAD,
        Task164AcceptanceCategory.REPEAT_RUN_DETERMINISM,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        repeat_run_payload_bytes(determinism),
        ("TASK164_REPEAT_RUN",),
    )
    python = _payload(
        Task164EvidencePayloadKind.PYTHON_PARITY_PAYLOAD,
        Task164AcceptanceCategory.CROSS_PYTHON_DETERMINISM,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        python_parity_payload_bytes(determinism),
        ("TASK164_DUAL_RUNTIME",),
    )
    scope_payload = _payload(
        Task164EvidencePayloadKind.SCOPE_FENCE_PAYLOAD,
        Task164AcceptanceCategory.SCOPE_FENCE_ACCEPTANCE,
        Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        scope_fence_bytes(scope),
        ("TASK164_SCOPE_FENCE",),
    )
    from .models import Task164MediaKind

    artifact_contents = (
        (
            Task164PackageArtifactId.TASK164_REQUEST_PROJECTION,
            Task164MediaKind.CANONICAL_BYTES,
            original_projection,
            Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        ),
        (
            Task164PackageArtifactId.TASK163_REPLAY_EVIDENCE,
            Task164MediaKind.SCENARIO_RECORD,
            task163_replay_payload_bytes(task163_evidence),
            Task164EvidenceAuthority.TASK163_PRODUCER,
        ),
        (
            Task164PackageArtifactId.TASK164_SCENARIO_EVIDENCE,
            Task164MediaKind.SCENARIO_RECORD,
            scenario_matrix_bytes(scenarios),
            Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        ),
        (
            Task164PackageArtifactId.TASK164_DETERMINISM_EVIDENCE,
            Task164MediaKind.DIGEST_RECORD,
            determinism_evidence_bytes(determinism),
            Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        ),
        (
            Task164PackageArtifactId.TASK164_TERMINAL_CAPABILITY,
            Task164MediaKind.CANONICAL_BYTES,
            terminal_capability_bytes(terminal),
            Task164EvidenceAuthority.FROZEN_AUTHORITY,
        ),
        (
            Task164PackageArtifactId.TASK164_SCOPE_FENCE,
            Task164MediaKind.CANONICAL_BYTES,
            scope_fence_bytes(scope),
            Task164EvidenceAuthority.TASK164_INTERNAL_OBSERVATION,
        ),
    )
    artifacts = tuple(
        Task164ArtifactRecord(
            artifact_id=artifact_id,
            media_kind=media_kind,
            canonical_payload_hash=_sha(content),
            authority=authority_value,
            evidence_refs=(),
        )
        for artifact_id, media_kind, content, authority_value in artifact_contents
    )
    package = Task164EvidencePackage(
        package_schema_version="task164.evidence-package.schema.v1",
        package_version="task164.evidence-package.v1",
        authority_evidence=authority,
        main_delivery_evidence=delivery,
        task163_replay_evidence=replay,
        task163_identity_evidence=identity,
        task163_applicability_evidence=app,
        task163_completeness_evidence=comp,
        task163_provenance_evidence=prov,
        terminal_capability_evidence=terminal_payload,
        positive_demo_evidence=positive,
        negative_demo_evidence=negative,
        repeat_run_evidence=repeat,
        cross_python_evidence=python,
        scope_fence_evidence=scope_payload,
        artifact_inventory=artifacts,
    )
    ledger = Task164AcceptanceLedger(
        records=tuple(
            Task164AcceptanceCategoryRecord(
                category=category,
                status=Task164AcceptanceCategoryStatus.PASS,
                evidence_refs=(),
                failure_code_or_none=None,
            )
            for category in TASK164_ACCEPTANCE_CATEGORIES
        ),
        package_hash=_sha(evidence_package_bytes(package)),
        status=Task164AcceptanceLedgerStatus.ACCEPTED,
    )
    return package, ledger


def _authority_bytes() -> bytes:
    return frame_record(
        "TASK164_AUTHORITY_CHAIN_PAYLOAD_V1",
        (
            ("namespace_issue", KIND_INT, b"219"),
            ("allocation_issue", KIND_INT, b"220"),
            ("source_issue", KIND_INT, b"243"),
            ("design_issue", KIND_INT, b"245"),
            ("lifecycle_issue", KIND_INT, b"242"),
            ("source_status", KIND_ENUM, b"FROZEN"),
            ("design_status", KIND_ENUM, b"R6_FROZEN"),
        ),
    )


def _compare_package_claim(
    claim: Task164EvidencePackageClaim,
    package: Task164EvidencePackage,
) -> bool:
    if claim.package_schema_version != package.package_schema_version:
        return False
    if claim.package_version != package.package_version:
        return False
    payloads = (
        package.authority_evidence,
        package.main_delivery_evidence,
        package.task163_replay_evidence,
        package.task163_identity_evidence,
        package.task163_applicability_evidence,
        package.task163_completeness_evidence,
        package.task163_provenance_evidence,
        package.terminal_capability_evidence,
        package.positive_demo_evidence,
        package.negative_demo_evidence,
        package.repeat_run_evidence,
        package.cross_python_evidence,
        package.scope_fence_evidence,
    )
    expected = {payload.category: payload.payload_sha256 for payload in payloads}
    expected[Task164AcceptanceCategory.EVIDENCE_PACKAGE_INTEGRITY] = _sha(
        evidence_package_bytes(package)
    )
    actual = dict(claim.claimed_category_payload_hashes)
    if len(actual) != len(claim.claimed_category_payload_hashes) or actual != expected:
        return False
    if tuple(claim.claimed_artifact_records) != tuple(package.artifact_inventory):
        return False
    return claim.claimed_package_hash == _sha(evidence_package_bytes(package))


def _make_repeat_observation(
    *,
    request_projection: bytes,
    first_evidence: Task164Task163Evidence,
    second_evidence: Task164Task163Evidence,
    first_scenarios: tuple[Task164ScenarioRecord, ...],
    second_scenarios: tuple[Task164ScenarioRecord, ...],
    first_terminal: Task164TerminalCapability,
    second_terminal: Task164TerminalCapability,
    first_scope: Task164ScopeFenceEvidence,
    second_scope: Task164ScopeFenceEvidence,
) -> Task164RepeatRunObservation:
    first_surfaces = _surface_records(
        request_projection=request_projection,
        evidence=first_evidence,
        scenarios=first_scenarios,
        terminal=first_terminal,
        scope=first_scope,
    )
    second_surfaces = _surface_records(
        request_projection=request_projection,
        evidence=second_evidence,
        scenarios=second_scenarios,
        terminal=second_terminal,
        scope=second_scope,
    )
    equal = first_surfaces == second_surfaces
    return Task164RepeatRunObservation(
        run_count=2,
        surface_records=first_surfaces,
        observed_equal=equal,
        status=Task164ParityStatus.PASS if equal else Task164ParityStatus.BLOCKED,
        evidence_refs=("TASK164_REPEAT_RUN_INTERNAL",),
        second_run_surface_records=second_surfaces,
    )


def _make_dual_runtime(
    *,
    request: Task164Request,
    task163: Task163ValidationResult,
    scenarios: tuple[Task164ScenarioRecord, ...],
    repeat: Task164RepeatRunObservation,
    terminal: Task164TerminalCapability,
    scope: Task164ScopeFenceEvidence,
    head_sha: str,
    head_tree: str,
) -> Task164DualRuntimeObservation:
    if task163.valid is None:
        raise ValueError("dual runtime requires a valid producer result")
    placeholder = Task164RuntimeObservation(
        python_version=Task164PythonVersion.PYTHON_3_11,
        head_sha=head_sha,
        head_tree=head_tree,
        runner_identity=Task164RunnerIdentity.TASK164_INTERNAL_DUAL_RUNTIME_RUNNER_V1,
        command_identity=Task164CommandIdentity.TASK164_INTERNAL_DUAL_RUNTIME_PARITY_CAPTURE_V1,
        surface_records=(),
        child_output_sha256="0" * 64,
        conclusion=Task164ParityStatus.PASS,
    )
    input_value = Task164CrossPythonParityInput(
        schema_version="task164.cross-python-input.v1",
        original_task163_request_projection_hash=task163_request_projection_hash(
            request.original_task163_request
        ),
        task163_result_hash=task163.valid.result_hash,
        task163_result_id=str(task163.valid.result_id).lower(),
        task163_provenance_hash=task163.valid.provenance.provenance_hash,
        applicability_projection_hash=_sha(
            task163_applicability_payload_bytes(task163.valid.applicability)
        ),
        completeness_projection_hash=_sha(
            task163_completeness_payload_bytes(task163.valid.completeness)
        ),
        scenario_matrix_projection_hash=_sha(scenario_matrix_bytes(scenarios)),
        repeat_run_evidence_projection_hash=_sha(
            repeat_run_payload_bytes(
                Task164DeterminismEvidence(
                    repeat_run_observation=repeat,
                    dual_runtime_observation=Task164DualRuntimeObservation(
                        pairing_key=Task164PairingKey.TASK164_PYTHON_3_11__TASK164_PYTHON_3_12,
                        python311_observation=placeholder,
                        python312_observation=replace(
                            placeholder, python_version=Task164PythonVersion.PYTHON_3_12
                        ),
                        status=Task164ParityStatus.PASS,
                        evidence_refs=(),
                    ),
                    status=Task164ParityStatus.PASS,
                )
            )
        ),
        terminal_capability_projection_hash=_sha(terminal_capability_bytes(terminal)),
        scope_fence_projection_hash=_sha(scope_fence_bytes(scope)),
        head_sha=head_sha,
        head_tree=head_tree,
        task164_design_version="R6",
        runtime_contract_version="TASK164_RUNTIME_CONTRACT_V1",
    )
    return observe_dual_runtime(
        input_value=input_value,
        head_sha=head_sha,
        head_tree=head_tree,
        py311=os.environ.get("TASK164_PY311_EXECUTABLE"),
        py312=os.environ.get("TASK164_PY312_EXECUTABLE"),
    )


def validate_request(raw: object) -> Task164ValidationResult:
    """Validate TASK164 through the frozen admission and evidence stages."""

    raw_outcome = project_raw_request_with_diagnostics(raw)
    from .canonical import raw_request_projection_hash

    projection_hash = raw_request_projection_hash(raw_outcome.projection)
    raw_codes = list(raw_outcome.reasons)
    for code in _raw_admission_codes(raw):
        if code not in raw_codes:
            raw_codes.append(code)
    if raw_codes:
        return _raw_blocked(raw_outcome.projection, projection_hash, tuple(raw_codes))

    request, typed_errors = _parse_request(raw)
    if typed_errors or request is None:
        return _typed_blocked(
            projection_hash,
            typed_errors,
            Task164FailureStage.TYPED_VALIDATION,
            projection_hash,
        )
    try:
        request_hash_value = request_hash(request)
        original_projection = task163_request_projection_bytes(request.original_task163_request)
    except BaseException:
        return _typed_blocked(
            projection_hash,
            (
                blocker(
                    Task164FailureCode.INVALID_REQUEST_SCHEMA, Task164FailureStage.TYPED_VALIDATION
                ),
            ),
            Task164FailureStage.TYPED_VALIDATION,
            projection_hash,
        )

    replayed, replay_errors = _replay_task163(request.original_task163_request)
    if replay_errors:
        return _typed_blocked(
            request_hash_value, replay_errors, Task164FailureStage.TASK163_REPLAY, projection_hash
        )
    assert replayed is not None
    replay_mismatch = _compare_replay(request.claimed_task163_validation_result, replayed)
    if replay_mismatch:
        return _typed_blocked(
            request_hash_value,
            replay_mismatch,
            Task164FailureStage.TASK163_REPLAY,
            projection_hash,
        )
    acceptance_errors = _task163_acceptance(replayed)
    if acceptance_errors:
        return _typed_blocked(
            request_hash_value,
            acceptance_errors,
            Task164FailureStage.TASK163_ACCEPTANCE,
            projection_hash,
        )

    by_id, scenario_errors = _valid_scenario_set(request.scenario_claims)
    if scenario_errors or by_id is None:
        return _typed_blocked(
            request_hash_value,
            scenario_errors,
            Task164FailureStage.DEMONSTRATION,
            projection_hash,
        )
    scenario_records = tuple(
        execute_scenario(by_id[scenario_id], request.original_task163_request)
        for scenario_id in TASK164_SCENARIO_IDS
    )
    failed_scenarios = tuple(
        blocker(
            Task164FailureCode.SCENARIO_EVIDENCE_INVALID,
            Task164FailureStage.DEMONSTRATION,
            record.scenario_id.value,
        )
        for record in scenario_records
        if record.status is not Task164EvidenceStatus.PASS
    )
    if failed_scenarios:
        return _typed_blocked(
            request_hash_value,
            failed_scenarios,
            Task164FailureStage.DEMONSTRATION,
            projection_hash,
        )
    second_scenario_records = tuple(
        execute_scenario(by_id[scenario_id], request.original_task163_request)
        for scenario_id in TASK164_SCENARIO_IDS
    )
    second_failed_scenarios = tuple(
        blocker(
            Task164FailureCode.SCENARIO_EVIDENCE_INVALID,
            Task164FailureStage.DEMONSTRATION,
            record.scenario_id.value,
        )
        for record in second_scenario_records
        if record.status is not Task164EvidenceStatus.PASS
    )
    if second_failed_scenarios:
        return _typed_blocked(
            request_hash_value,
            second_failed_scenarios,
            Task164FailureStage.DEMONSTRATION,
            projection_hash,
        )

    def evidence_for(records: tuple[Task164ScenarioRecord, ...]) -> Task164Task163Evidence:
        return Task164Task163Evidence(
            original_request_projection_hash=task163_request_projection_hash(
                request.original_task163_request
            ),
            replay_evidence=tuple(record.replay_evidence for record in records),
            accepted_result_identities=tuple(
                record.observation.observed_task163_result_identity_or_none
                for record in records[:5]
                if record.observation.observed_task163_result_identity_or_none is not None
            ),
            status=Task164EvidenceStatus.PASS,
        )

    task163_evidence = evidence_for(scenario_records)
    second_task163_evidence = evidence_for(second_scenario_records)
    terminal = _terminal_capability()
    second_terminal = _terminal_capability()
    scope = _scope_fence()
    second_scope = _scope_fence()
    if scope.status is not Task164ScopeStatus.PASS or second_scope.status is not Task164ScopeStatus.PASS:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task164FailureCode.SCOPE_FENCE_FAILED, Task164FailureStage.SCOPE_FENCE),),
            Task164FailureStage.SCOPE_FENCE,
            projection_hash,
        )
    repeat = _make_repeat_observation(
        request_projection=original_projection,
        first_evidence=task163_evidence,
        second_evidence=second_task163_evidence,
        first_scenarios=scenario_records,
        second_scenarios=second_scenario_records,
        first_terminal=terminal,
        second_terminal=second_terminal,
        first_scope=scope,
        second_scope=second_scope,
    )
    if repeat.status is not Task164ParityStatus.PASS:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task164FailureCode.REPEAT_RUN_PARITY_FAILED, Task164FailureStage.DETERMINISM),),
            Task164FailureStage.DETERMINISM,
            projection_hash,
        )
    main_delivery = observe_main_delivery()
    if main_delivery.status is not Task164ParityStatus.PASS:
        return _typed_blocked(
            request_hash_value,
            (
                blocker(
                    Task164FailureCode.MAIN_DELIVERY_EVIDENCE_FAILED,
                    Task164FailureStage.EVIDENCE_PACKAGE,
                ),
            ),
            Task164FailureStage.EVIDENCE_PACKAGE,
            projection_hash,
        )
    try:
        dual = _make_dual_runtime(
            request=request,
            task163=replayed,
            scenarios=scenario_records,
            repeat=repeat,
            terminal=terminal,
            scope=scope,
            head_sha=main_delivery.observed_head_sha,
            head_tree=main_delivery.observed_head_tree,
        )
    except BaseException:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task164FailureCode.PYTHON_PARITY_FAILED, Task164FailureStage.DETERMINISM),),
            Task164FailureStage.DETERMINISM,
            projection_hash,
        )
    if dual.status is not Task164ParityStatus.PASS:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task164FailureCode.PYTHON_PARITY_FAILED, Task164FailureStage.DETERMINISM),),
            Task164FailureStage.DETERMINISM,
            projection_hash,
        )
    determinism = Task164DeterminismEvidence(
        repeat_run_observation=repeat,
        dual_runtime_observation=dual,
        status=Task164ParityStatus.PASS,
    )
    assert replayed.valid is not None
    producer_applicability = replayed.valid.applicability
    producer_completeness = replayed.valid.completeness
    applicability = _applicability()
    completeness = _completeness()
    package, ledger = _build_payloads(
        main_delivery=main_delivery,
        task163_evidence=task163_evidence,
        scenarios=scenario_records,
        determinism=determinism,
        terminal=terminal,
        scope=scope,
        producer_applicability=producer_applicability,
        producer_completeness=producer_completeness,
        original_projection=original_projection,
    )
    if not _compare_package_claim(request.evidence_package_claim, package):
        return _typed_blocked(
            request_hash_value,
            (
                blocker(
                    Task164FailureCode.EVIDENCE_PACKAGE_INTEGRITY_FAILED,
                    Task164FailureStage.EVIDENCE_PACKAGE,
                ),
            ),
            Task164FailureStage.EVIDENCE_PACKAGE,
            projection_hash,
        )
    demonstration = Task164DemonstrationCoverage(
        required_scenario_ids=TASK164_SCENARIO_IDS,
        scenario_records=scenario_records,
        positive_count=5,
        negative_count=4,
        determinism_count=2,
        scope_fence_count=1,
        status=Task164EvidenceStatus.PASS,
    )
    applicability_records = tuple(
        Task164ApplicabilityRecord(
            check=check,
            status=Task164AcceptanceCategoryStatus.PASS,
            evidence_refs=(),
            failure_code_or_none=None,
        )
        for check in Task164ApplicabilityCheck
    )
    applicability = Task164Applicability(
        records=applicability_records,
        status=Task164ApplicabilityStatus.APPLICABLE,
    )
    semantic = build_provenance_semantic_inputs(
        task163_evidence=task163_evidence,
        scenario_matrix=scenario_records,
        determinism_evidence=determinism,
        acceptance_ledger=ledger,
        evidence_package=package,
        applicability=producer_applicability,
        completeness=producer_completeness,
    )
    pre = Task164PreResultIdentityInputs(
        schema_version=TASK164_SCHEMA_VERSION,
        task164_version=TASK164_VERSION,
        implementation_software_version=TASK164_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK164_SOURCE_DEFINITION_ID,
        request_hash=request_hash_value,
        original_task163_request_projection=original_projection,
        task163_evidence=task163_evidence,
        scenario_evidence=scenario_records,
        determinism_evidence=determinism,
        terminal_capability=terminal,
        demonstration_coverage=demonstration,
        scope_fence_evidence=scope,
        applicability=applicability,
        completeness=completeness,
        evidence_package=package,
        acceptance_ledger=ledger,
        warnings_normalized=(),
        blockers_normalized=(),
        provenance_semantic_inputs=semantic,
    )
    try:
        result_hash_value = success_hash_from_inputs(pre)
        provisional = Task164Result(
            schema_version=pre.schema_version,
            task164_version=pre.task164_version,
            implementation_software_version=pre.implementation_software_version,
            source_definition_id=pre.source_definition_id,
            request_hash=pre.request_hash,
            original_task163_request_projection=pre.original_task163_request_projection,
            task163_evidence=pre.task163_evidence,
            scenario_evidence=pre.scenario_evidence,
            determinism_evidence=pre.determinism_evidence,
            terminal_capability=pre.terminal_capability,
            demonstration_coverage=pre.demonstration_coverage,
            scope_fence_evidence=pre.scope_fence_evidence,
            applicability=pre.applicability,
            completeness=pre.completeness,
            evidence_package=pre.evidence_package,
            acceptance_ledger=pre.acceptance_ledger,
            warnings=(),
            blockers=(),
            provenance_semantic_inputs=pre.provenance_semantic_inputs,
            provenance=Task164Provenance(provenance_hash="", graph=ProvenanceGraph()),
            result_hash=result_hash_value,
            result_id=result_id(result_hash_value),
        )
        provenance_value = build_success_provenance(
            semantic_inputs=semantic,
            result=provisional,
        )
        result_value = replace(provisional, provenance=provenance_value)
        if success_hash_from_inputs(pre) != result_value.result_hash:
            raise ValueError("success hash replay mismatch")
        if result_id(result_value.result_hash) != result_value.result_id:
            raise ValueError("result id replay mismatch")
        if provenance_value.provenance_hash != provenance_hash(provenance_value.graph):
            raise ValueError("provenance replay mismatch")
    except BaseException:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task164FailureCode.IDENTITY_REPLAY_FAILED, Task164FailureStage.IDENTITY),),
            Task164FailureStage.IDENTITY,
            projection_hash,
        )
    return Task164ValidationResult(status=Task164ValidationBranch.VALID, valid=result_value)


__all__ = ["validate_request"]
