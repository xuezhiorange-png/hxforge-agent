"""TASK-169 Golden replay and v0.6 release-acceptance boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace

from hexagent.exchangers.shell_tube.manufacturable_candidates import (
    validate_request as validate_task168_request,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    batch_result_hash as task168_batch_result_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    raw_blocked_hash,
    raw_blocked_id,
    typed_blocked_hash,
    typed_blocked_id,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    request_hash as task168_request_hash,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    result_id as task168_result_id,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    TASK168_BLOCKED_SCHEMA_VERSION,
    TASK168_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK168_RAW_BLOCKED_SCHEMA_VERSION,
    TASK168_RESULT_SCHEMA_VERSION,
    TASK168_SOURCE_DEFINITION_ID,
    TASK168_VERSION,
    ApplicabilityStatus,
    CandidateRecord,
    CandidateStage,
    CandidateStatus,
    CompletenessStatus,
    Task168BatchResult,
    Task168RawBoundaryBlockedResult,
    Task168Request,
    Task168TypedBlockedResult,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    ValidationStatus as Task168ValidationStatus,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.provenance import (
    verify_provenance_graph,
)
from hexagent.exchangers.shell_tube.selection_release.authority import (
    TASK169_PRODUCTION_RANKING_POLICY,
)
from hexagent.exchangers.shell_tube.selection_release.models import (
    TASK169_FROZEN_TOLERANCE_LEDGER,
    SelectionStatus,
    Task169Request,
    Task169Result,
)
from hexagent.exchangers.shell_tube.selection_release.models import (
    ValidationStatus as SelectionValidationStatus,
)
from hexagent.exchangers.shell_tube.selection_release.service import (
    validate_request as validate_selection_request,
)

from .approved_golden_registry import (
    APPROVED_GOLDEN_AUTHORITY_IDS,
    approved_golden_authority,
)
from .canonical import (
    blocked_hash,
    blocked_id,
    result_hash,
    result_id,
)
from .canonical import (
    request_hash as release_request_hash,
)
from .golden_fixtures import (
    G05_EXPECTED_BLOCKER_CODE,
    G05_EXPECTED_BLOCKER_FIELD,
    G05_EXPECTED_BLOCKER_OWNER,
    G05_NEGATIVE_CLASS,
    G05_NO_RECOMMENDATION_REQUIRED,
)
from .models import (
    TASK169_GOLDEN_TOLERANCE_CLASS,
    TASK169_PROPOSED_IDENTITY_STATUS,
    TASK169_RELEASE_RESULT_SCHEMA_VERSION,
    TASK169_RELEASE_SCHEMA_VERSION,
    TASK169_RELEASE_SOFTWARE_VERSION,
    TASK169_RELEASE_SOURCE_DEFINITION_ID,
    TASK169_RELEASE_VERSION,
    AcceptanceGateRecord,
    AcceptanceStatus,
    GoldenAcceptanceRecord,
    GoldenCaseId,
    Task169GoldenCase,
    Task169ReleaseBlockedResult,
    Task169ReleaseRequest,
    Task169ReleaseResult,
    Task169ReleaseValidationResult,
)
from .trusted_evidence import (
    Task169DualRuntimeObservation,
    Task169ParityInput,
    observe_dual_runtime,
    repository_identity,
)

FROZEN_TOLERANCE_LEDGER = TASK169_FROZEN_TOLERANCE_LEDGER

_APPROVED_GOLDEN_AUTHORITY_IDS = APPROVED_GOLDEN_AUTHORITY_IDS
_GOLDEN_ORDER = (
    GoldenCaseId.V06_G01,
    GoldenCaseId.V06_G02,
    GoldenCaseId.V06_G03,
    GoldenCaseId.V06_G04,
    GoldenCaseId.V06_G05,
)
_TASK168_EXPECTED_STATUSES = frozenset(item.value for item in Task168ValidationStatus)
_GATE_ORDER = (
    "SHELL_TUBE_FIXED_GEOMETRY_RATING",
    "BELL_DELAWARE_HEAT_TRANSFER",
    "BELL_DELAWARE_PRESSURE_DROP",
    "BELL_DELAWARE_PROVENANCE_COMPLETE",
    "SHELL_TUBE_ENGINEERING_SCREENING",
    "THERMAL_EXPANSION_SCREENING",
    "VIBRATION_SCREENING",
    "SHELL_TUBE_CANDIDATE_GENERATION",
    "SHELL_TUBE_SIZING",
    "SHELL_TUBE_MULTI_CANDIDATE_RANKING",
    "TUBE_DP_CONSTRAINT_CLOSURE",
    "SHELL_DP_CONSTRAINT_CLOSURE",
    "THERMAL_DUTY_CLOSURE",
    "DETERMINISTIC_REPLAY",
    "PROVENANCE_COMPLETE",
    "PY311_PY312_PARITY",
    "GOLDEN_V06_G01",
    "GOLDEN_V06_G02",
    "GOLDEN_V06_G03",
    "GOLDEN_V06_G04",
    "GOLDEN_V06_G05",
    "END_TO_END_RELEASE_DEMO",
)


@dataclass(frozen=True, slots=True)
class _Task168Replay:
    expected_status: str
    result_hash: str
    result_id: str
    batch: Task168BatchResult | None
    raw_blocked: Task168RawBoundaryBlockedResult | None
    typed_blocked: Task168TypedBlockedResult | None
    selection: Task169Result | None
    selection_blockers: tuple[str, ...]
    failures: tuple[str, ...]


def _blocked(request_hash_value: str, codes: tuple[str, ...]) -> Task169ReleaseValidationResult:
    provisional = Task169ReleaseBlockedResult(
        schema_version=TASK169_RELEASE_RESULT_SCHEMA_VERSION,
        release_version=TASK169_RELEASE_VERSION,
        implementation_software_version=TASK169_RELEASE_SOFTWARE_VERSION,
        request_hash=request_hash_value,
        blocker_codes=tuple(dict.fromkeys(codes)),
        result_hash="",
        result_id="",
    )
    digest = blocked_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=blocked_id(digest))
    return Task169ReleaseValidationResult(blocked=result)


def _hex_digest(value: str) -> bool:
    return len(value) == 64 and all(character in "0123456789abcdef" for character in value)


def _metadata_failures(
    case: Task169GoldenCase, computed_task168_request_hash: str
) -> tuple[str, ...]:
    failures: list[str] = []
    if case.ranking_policy != TASK169_PRODUCTION_RANKING_POLICY:
        if (
            case.ranking_policy.policy_id == "V06-RANKING-POLICY-TEST"
            or case.ranking_policy.source_id == "TASK169-TEST-AUTHORITY"
        ):
            failures.append("TEST_RANKING_AUTHORITY_FORBIDDEN")
        else:
            failures.append("PRODUCTION_RANKING_AUTHORITY_MISMATCH")
    if not case.source_id or not case.source_location or not case.source_class:
        failures.append("GOLDEN_SOURCE_IDENTITY_REQUIRED")
    if not case.redistribution_status:
        failures.append("GOLDEN_REDISTRIBUTION_STATUS_REQUIRED")
    if not case.normalized_input_identity:
        failures.append("GOLDEN_NORMALIZED_INPUT_IDENTITY_REQUIRED")
    if case.normalized_input_identity != computed_task168_request_hash:
        failures.append("GOLDEN_NORMALIZED_INPUT_IDENTITY_MISMATCH")
    if not case.task168_request_hash or not _hex_digest(case.task168_request_hash):
        failures.append("TASK168_REQUEST_HASH_AUTHORITY_REQUIRED")
    elif case.task168_request_hash != computed_task168_request_hash:
        failures.append("TASK168_REQUEST_HASH_MISMATCH")
    if not case.expected_task168_result_hash or not _hex_digest(case.expected_task168_result_hash):
        failures.append("TASK168_EXPECTED_RESULT_HASH_AUTHORITY_REQUIRED")
    if not case.expected_task168_result_id:
        failures.append("TASK168_EXPECTED_RESULT_ID_AUTHORITY_REQUIRED")
    if case.expected_task168_result_status not in _TASK168_EXPECTED_STATUSES:
        failures.append("TASK168_EXPECTED_STATUS_INVALID")
    if case.expected_task169_result_hash is None and not case.approved_numeric_expectations:
        failures.append("GOLDEN_EXPECTATION_AUTHORITY_REQUIRED")
    if case.expected_task169_result_hash is not None and not _hex_digest(
        case.expected_task169_result_hash
    ):
        failures.append("TASK169_EXPECTED_RESULT_HASH_INVALID")
    if not case.tolerance_class:
        failures.append("GOLDEN_TOLERANCE_CLASS_REQUIRED")
    elif case.tolerance_class != TASK169_GOLDEN_TOLERANCE_CLASS:
        failures.append("GOLDEN_TOLERANCE_CLASS_MISMATCH")
    if not case.reviewer_evidence_refs:
        failures.append("GOLDEN_REVIEW_EVIDENCE_REQUIRED")
    if not case.provenance_source_hash or not _hex_digest(case.provenance_source_hash):
        failures.append("GOLDEN_PROVENANCE_SOURCE_HASH_REQUIRED")
    approved_authority = approved_golden_authority(case.golden_id)
    if case.review_status == "PROPOSED":
        failures.append("V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING")
    elif case.review_status == "APPROVED":
        if case.golden_id not in _APPROVED_GOLDEN_AUTHORITY_IDS:
            failures.append("GOLDEN_APPROVAL_NOT_REGISTERED")
        if not case.approved_by or not case.approval_evidence:
            failures.append("GOLDEN_APPROVAL_EVIDENCE_REQUIRED")
        if approved_authority is None:
            failures.append("GOLDEN_APPROVAL_NOT_REGISTERED")
        else:
            approved_fields = (
                ("source_id", case.source_id, approved_authority.source_id),
                ("source_location", case.source_location, approved_authority.source_location),
                ("source_class", case.source_class, approved_authority.source_class),
                (
                    "redistribution_status",
                    case.redistribution_status,
                    approved_authority.redistribution_status,
                ),
                (
                    "task168_request_hash",
                    case.task168_request_hash,
                    approved_authority.task168_request_hash,
                ),
                (
                    "expected_task168_result_hash",
                    case.expected_task168_result_hash,
                    approved_authority.task168_result_hash,
                ),
                (
                    "expected_task168_result_id",
                    case.expected_task168_result_id,
                    approved_authority.task168_result_id,
                ),
                (
                    "expected_task168_result_status",
                    case.expected_task168_result_status,
                    approved_authority.task168_result_status,
                ),
                (
                    "ranking_policy_hash",
                    case.ranking_policy.canonical_hash,
                    approved_authority.ranking_policy_hash,
                ),
                (
                    "expected_task169_result_hash",
                    case.expected_task169_result_hash,
                    approved_authority.task169_result_hash,
                ),
                (
                    "expected_task169_result_id",
                    case.expected_task169_result_id,
                    approved_authority.task169_result_id,
                ),
                ("tolerance_class", case.tolerance_class, approved_authority.tolerance_class),
                (
                    "provenance_source_hash",
                    case.provenance_source_hash,
                    approved_authority.provenance_source_hash,
                ),
                (
                    "reviewer_evidence_refs",
                    case.reviewer_evidence_refs,
                    approved_authority.reviewer_evidence_refs,
                ),
                ("approved_by", case.approved_by, approved_authority.approved_by),
                (
                    "approval_evidence",
                    case.approval_evidence,
                    approved_authority.approval_evidence,
                ),
                (
                    "expected_identity_status",
                    case.expected_identity_status,
                    approved_authority.expected_identity_status,
                ),
                ("negative_class", case.negative_class, approved_authority.negative_class),
                (
                    "expected_blocker_code",
                    case.expected_blocker_code,
                    approved_authority.expected_blocker_code,
                ),
                (
                    "expected_blocker_owner",
                    case.expected_blocker_owner,
                    approved_authority.expected_blocker_owner,
                ),
                (
                    "no_recommendation_required",
                    case.no_recommendation_required,
                    approved_authority.no_recommendation_required,
                ),
            )
            failures.extend(
                "GOLDEN_APPROVED_AUTHORITY_" + name.upper() + "_MISMATCH"
                for name, observed, expected in approved_fields
                if observed != expected
            )
    else:
        failures.append("GOLDEN_REVIEW_STATUS_INVALID")
    expected_identity_status = (
        approved_authority.expected_identity_status
        if case.review_status == "APPROVED" and approved_authority is not None
        else TASK169_PROPOSED_IDENTITY_STATUS
    )
    if case.expected_identity_status != expected_identity_status:
        failures.append("GOLDEN_EXPECTED_IDENTITY_STATUS_INVALID")
    return tuple(dict.fromkeys(failures))


def _validate_task168_batch(
    value: Task168BatchResult, expected_request_hash: str
) -> tuple[str, ...]:
    failures: list[str] = []
    if value.schema_version != TASK168_RESULT_SCHEMA_VERSION:
        failures.append("TASK168_RESULT_SCHEMA_VERSION_MISMATCH")
    if value.task168_version != TASK168_VERSION:
        failures.append("TASK168_VERSION_MISMATCH")
    if value.source_definition_id != TASK168_SOURCE_DEFINITION_ID:
        failures.append("TASK168_SOURCE_DEFINITION_ID_MISMATCH")
    if value.implementation_software_version != TASK168_IMPLEMENTATION_SOFTWARE_VERSION:
        failures.append("TASK168_IMPLEMENTATION_SOFTWARE_VERSION_MISMATCH")
    if value.request_hash != expected_request_hash:
        failures.append("TASK168_REQUEST_BINDING_MISMATCH")
    try:
        if task168_batch_result_hash(value) != value.result_hash:
            failures.append("TASK168_RESULT_HASH_MISMATCH")
        if task168_result_id(value.result_hash) != value.result_id:
            failures.append("TASK168_RESULT_ID_MISMATCH")
    except (ArithmeticError, TypeError, UnicodeError, ValueError):
        failures.append("TASK168_RESULT_NOT_CANONICAL")
    if not verify_provenance_graph(value.provenance):
        failures.append("TASK168_PROVENANCE_INVALID")
    if value.applicability.status is not ApplicabilityStatus.APPLICABLE:
        failures.append("TASK168_APPLICABILITY_BLOCKED")
    if value.completeness.status is not CompletenessStatus.COMPLETE:
        failures.append("TASK168_COMPLETENESS_INCOMPLETE")
    if value.total_enumerated_candidates != len(value.candidate_records):
        failures.append("TASK168_CANDIDATE_COUNT_MISMATCH")
    expected_counts = {
        CandidateStatus.PASS: value.pass_count,
        CandidateStatus.WARN: value.warn_count,
        CandidateStatus.BLOCKED: value.blocked_count,
    }
    if any(
        sum(record.status is status for record in value.candidate_records) != expected
        for status, expected in expected_counts.items()
    ):
        failures.append("TASK168_STATUS_COUNT_MISMATCH")
    return tuple(dict.fromkeys(failures))


def _validate_task168_blocked(
    value: Task168RawBoundaryBlockedResult | Task168TypedBlockedResult,
    raw: bool,
    expected_request_hash: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    expected_schema = TASK168_RAW_BLOCKED_SCHEMA_VERSION if raw else TASK168_BLOCKED_SCHEMA_VERSION
    if value.schema_version != expected_schema:
        failures.append("TASK168_BLOCKED_SCHEMA_VERSION_MISMATCH")
    if value.task168_version != TASK168_VERSION:
        failures.append("TASK168_BLOCKED_VERSION_MISMATCH")
    if value.implementation_software_version != TASK168_IMPLEMENTATION_SOFTWARE_VERSION:
        failures.append("TASK168_BLOCKED_IMPLEMENTATION_SOFTWARE_VERSION_MISMATCH")
    try:
        if raw:
            if not isinstance(value, Task168RawBoundaryBlockedResult):
                return ("TASK168_BLOCKED_BRANCH_TYPE_MISMATCH",)
            if raw_blocked_hash(value) != value.result_hash:
                failures.append("TASK168_BLOCKED_RESULT_HASH_MISMATCH")
            if raw_blocked_id(value.result_hash) != value.result_id:
                failures.append("TASK168_BLOCKED_RESULT_ID_MISMATCH")
            if value.raw_request_projection_hash != expected_request_hash:
                failures.append("TASK168_REQUEST_BINDING_MISMATCH")
        else:
            if not isinstance(value, Task168TypedBlockedResult):
                return ("TASK168_BLOCKED_BRANCH_TYPE_MISMATCH",)
            if typed_blocked_hash(value) != value.result_hash:
                failures.append("TASK168_BLOCKED_RESULT_HASH_MISMATCH")
            if typed_blocked_id(value.result_hash) != value.result_id:
                failures.append("TASK168_BLOCKED_RESULT_ID_MISMATCH")
            if value.request_hash != expected_request_hash:
                failures.append("TASK168_REQUEST_BINDING_MISMATCH")
    except (ArithmeticError, TypeError, UnicodeError, ValueError):
        failures.append("TASK168_BLOCKED_RESULT_NOT_CANONICAL")
    return tuple(dict.fromkeys(failures))


def _selection_for_batch(
    case: Task169GoldenCase, batch: Task168BatchResult
) -> tuple[Task169Result | None, tuple[str, ...]]:
    selection_request = Task169Request(
        schema_version="task169.selection-request.v1",
        task169_version="task169.v1",
        source_definition_id="TASK169-SOURCE-DEFINITION-ISSUE-265",
        task168_result=batch,
        ranking_policy=case.ranking_policy,
        request_metadata=(("golden_id", case.golden_id.value),),
    )
    try:
        outcome = validate_selection_request(selection_request)
    except BaseException:
        return None, ("TASK169_SELECTION_EXCEPTION",)
    if outcome.status is SelectionValidationStatus.VALID and outcome.valid is not None:
        try:
            replay = validate_selection_request(selection_request)
        except BaseException:
            return None, ("TASK169_SELECTION_REPLAY_EXCEPTION",)
        if (
            replay.status is not SelectionValidationStatus.VALID
            or replay.valid is None
            or replay.valid.result_hash != outcome.valid.result_hash
            or replay.valid.result_id != outcome.valid.result_id
        ):
            return None, ("TASK169_SELECTION_IDENTITY_REPLAY_FAILED",)
        return outcome.valid, ()
    if outcome.typed_blocked is not None:
        return None, tuple(outcome.typed_blocked.blocker_codes)
    return None, ("TASK169_SELECTION_NO_RESULT",)


def _replay_task168(case: Task169GoldenCase) -> _Task168Replay:
    failures: list[str] = []
    raw_blocked: Task168RawBoundaryBlockedResult | None = None
    typed_blocked: Task168TypedBlockedResult | None = None
    try:
        computed_request_hash = task168_request_hash(case.task168_request)
    except (ArithmeticError, TypeError, UnicodeError, ValueError):
        return _Task168Replay(
            expected_status=case.expected_task168_result_status,
            result_hash="",
            result_id="",
            batch=None,
            raw_blocked=None,
            typed_blocked=None,
            selection=None,
            selection_blockers=(),
            failures=("TASK168_REQUEST_NOT_CANONICAL",),
        )
    if case.task168_request_hash != computed_request_hash:
        failures.append("TASK168_REQUEST_HASH_MISMATCH")
    if case.normalized_input_identity != computed_request_hash:
        failures.append("TASK168_NORMALIZED_REQUEST_HASH_MISMATCH")
    if type(case.task168_request) is not Task168Request:
        failures.append("TASK168_REQUEST_TYPE_INVALID")
    if failures:
        return _Task168Replay(
            expected_status=case.expected_task168_result_status,
            result_hash="",
            result_id="",
            batch=None,
            raw_blocked=None,
            typed_blocked=None,
            selection=None,
            selection_blockers=(),
            failures=tuple(dict.fromkeys(failures)),
        )
    try:
        outcome = validate_task168_request(case.task168_request)
    except BaseException:
        return _Task168Replay(
            expected_status=case.expected_task168_result_status,
            result_hash="",
            result_id="",
            batch=None,
            raw_blocked=None,
            typed_blocked=None,
            selection=None,
            selection_blockers=(),
            failures=("TASK168_REPLAY_EXCEPTION",),
        )

    if outcome.status is Task168ValidationStatus.VALID and outcome.valid is not None:
        batch = outcome.valid
        failures.extend(_validate_task168_batch(batch, computed_request_hash))
        result_hash_value = batch.result_hash
        result_id_value = batch.result_id
        selection: Task169Result | None = None
        selection_blockers: tuple[str, ...] = ()
        if not failures:
            selection, selection_blockers = _selection_for_batch(case, batch)
            failures.extend(selection_blockers)
        if case.expected_task168_result_status != Task168ValidationStatus.VALID.value:
            failures.append("TASK168_EXPECTED_STATUS_MISMATCH")
        if case.expected_task168_result_hash != result_hash_value:
            failures.append("TASK168_EXPECTED_RESULT_HASH_MISMATCH")
        if case.expected_task168_result_id != result_id_value:
            failures.append("TASK168_EXPECTED_RESULT_ID_MISMATCH")
        return _Task168Replay(
            expected_status=case.expected_task168_result_status,
            result_hash=result_hash_value,
            result_id=result_id_value,
            batch=batch,
            raw_blocked=None,
            typed_blocked=None,
            selection=selection,
            selection_blockers=selection_blockers,
            failures=tuple(dict.fromkeys(failures)),
        )

    if (
        outcome.status is Task168ValidationStatus.RAW_BOUNDARY_BLOCKED
        and outcome.raw_boundary_blocked is not None
    ):
        raw_value = outcome.raw_boundary_blocked
        failures.extend(
            _validate_task168_blocked(
                raw_value,
                raw=True,
                expected_request_hash=computed_request_hash,
            )
        )
        result_hash_value = raw_value.result_hash
        result_id_value = raw_value.result_id
        actual_status = Task168ValidationStatus.RAW_BOUNDARY_BLOCKED.value
        raw_blocked = raw_value
    elif (
        outcome.status is Task168ValidationStatus.TYPED_BLOCKED
        and outcome.typed_blocked is not None
    ):
        typed_value = outcome.typed_blocked
        failures.extend(
            _validate_task168_blocked(
                typed_value,
                raw=False,
                expected_request_hash=computed_request_hash,
            )
        )
        result_hash_value = typed_value.result_hash
        result_id_value = typed_value.result_id
        actual_status = Task168ValidationStatus.TYPED_BLOCKED.value
        typed_blocked = typed_value
    else:
        return _Task168Replay(
            expected_status=case.expected_task168_result_status,
            result_hash="",
            result_id="",
            batch=None,
            raw_blocked=None,
            typed_blocked=None,
            selection=None,
            selection_blockers=(),
            failures=("TASK168_REPLAY_RESULT_BRANCH_INVALID",),
        )
    if case.expected_task168_result_status != actual_status:
        failures.append("TASK168_EXPECTED_STATUS_MISMATCH")
    if case.expected_task168_result_hash != result_hash_value:
        failures.append("TASK168_EXPECTED_RESULT_HASH_MISMATCH")
    if case.expected_task168_result_id != result_id_value:
        failures.append("TASK168_EXPECTED_RESULT_ID_MISMATCH")
    return _Task168Replay(
        expected_status=case.expected_task168_result_status,
        result_hash=result_hash_value,
        result_id=result_id_value,
        batch=None,
        raw_blocked=raw_blocked,
        typed_blocked=typed_blocked,
        selection=None,
        selection_blockers=(),
        failures=tuple(dict.fromkeys(failures)),
    )


def _candidate_for_result(
    replay: _Task168Replay, result: Task169Result | None
) -> CandidateRecord | None:
    if replay.batch is None or result is None or result.recommended_candidate is None:
        return None
    candidate_id = result.recommended_candidate.candidate_id
    return next(
        (
            record
            for record in replay.batch.candidate_records
            if record.candidate_id == candidate_id
        ),
        None,
    )


def _full_chain_evidence(record: CandidateRecord | None) -> bool:
    if record is None:
        return False
    evidence_groups = (
        record.configuration_evidence,
        record.geometry_evidence,
        record.tube_layout_evidence,
        record.tube_side_evidence,
        record.bell_evidence,
        record.overall_u_ua_evidence,
        record.thermal_closure_evidence,
        record.tube_dp_evidence,
        record.shell_dp_evidence,
        record.screening_evidence,
    )
    return all(evidence_groups)


def _constraint(record: CandidateRecord | None, key: str) -> str | None:
    if record is None:
        return None
    return dict(record.constraint_evaluations).get(key)


def _exclusion_reasons(
    result: Task169Result | None,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if result is None:
        return ()
    return tuple(
        (
            item.candidate_id,
            tuple(dict.fromkeys((item.reason_code, *item.evidence_refs))),
        )
        for item in result.excluded_candidates
    )


def _golden_record(case: Task169GoldenCase, replay: _Task168Replay) -> GoldenAcceptanceRecord:
    try:
        task168_request_hash_value = task168_request_hash(case.task168_request)
    except (ArithmeticError, TypeError, UnicodeError, ValueError):
        task168_request_hash_value = ""
    reasons = list(_metadata_failures(case, task168_request_hash_value))
    reasons.extend(replay.failures)
    result = replay.selection
    candidate = _candidate_for_result(replay, result)
    if case.expected_task169_result_hash is not None:
        if result is None or result.result_hash != case.expected_task169_result_hash:
            reasons.append("GOLDEN_EXPECTED_TASK169_RESULT_HASH_MISMATCH")
        if result is None or result.result_id != case.expected_task169_result_id:
            reasons.append("GOLDEN_EXPECTED_TASK169_RESULT_ID_MISMATCH")

    if case.golden_id is GoldenCaseId.V06_G01:
        if result is None or result.selection_status is not SelectionStatus.SELECTED:
            reasons.append("G01_RECOMMENDATION_REQUIRED")
        if candidate is None or candidate.candidate.construction_family.value != "FIXED_TUBESHEET":
            reasons.append("G01_FIXED_TUBESHEET_REQUIRED")
        if not _full_chain_evidence(candidate):
            reasons.append("G01_FULL_CHAIN_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G02:
        if result is None or result.selection_status is not SelectionStatus.SELECTED:
            reasons.append("G02_RECOMMENDATION_REQUIRED")
        if candidate is None or candidate.candidate.construction_family.value != "U_TUBE":
            reasons.append("G02_U_TUBE_REQUIRED")
        if candidate is None or not candidate.screening_evidence:
            reasons.append("G02_SCREENING_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G03:
        if result is None or result.selection_status is not SelectionStatus.SELECTED:
            reasons.append("G03_RECOMMENDATION_REQUIRED")
        if candidate is None or candidate.candidate.construction_family.value != "FLOATING_HEAD":
            reasons.append("G03_FLOATING_HEAD_REQUIRED")
        if candidate is None or not candidate.screening_evidence:
            reasons.append("G03_SCREENING_EVIDENCE_REQUIRED")
    elif case.golden_id is GoldenCaseId.V06_G04:
        records = replay.batch.candidate_records if replay.batch is not None else ()
        hard_dp_rejection = any(
            record.status is CandidateStatus.BLOCKED
            and any(
                blocker.code == "HARD_CONSTRAINT_UNSATISFIED"
                and blocker.field_path in {"max_tube_dp_pa", "max_shell_dp_pa"}
                for blocker in record.blockers
            )
            for record in records
        )
        if result is None or result.selection_status is not SelectionStatus.SELECTED:
            reasons.append("G04_FEASIBLE_RECOMMENDATION_REQUIRED")
        if len(records) < 2:
            reasons.append("G04_MULTI_CANDIDATE_REQUIRED")
        if not hard_dp_rejection:
            reasons.append("G04_DP_CONSTRAINED_REJECTION_REQUIRED")
    else:
        if (
            case.negative_class != G05_NEGATIVE_CLASS
            or case.expected_blocker_code != G05_EXPECTED_BLOCKER_CODE
            or case.expected_blocker_owner != G05_EXPECTED_BLOCKER_OWNER
            or not case.no_recommendation_required
        ):
            reasons.append("G05_FROZEN_NEGATIVE_CLASS_REQUIRED")
        if replay.batch is not None:
            matching_blocker = any(
                record.status is CandidateStatus.BLOCKED
                and any(
                    blocker.code == G05_EXPECTED_BLOCKER_CODE
                    and blocker.stage is CandidateStage.SHELL_SIDE_BELL
                    and blocker.field_path == G05_EXPECTED_BLOCKER_FIELD
                    for blocker in record.blockers
                )
                for record in replay.batch.candidate_records
            )
            if not matching_blocker:
                reasons.append("G05_FROZEN_NEGATIVE_CLASS_REQUIRED")
            if result is None or (
                result.selection_status is not SelectionStatus.NO_RECOMMENDABLE_CANDIDATE
                or result.recommended_candidate is not None
            ):
                reasons.append("G05_NO_RECOMMENDATION_REQUIRED")
        elif not (replay.raw_blocked or replay.typed_blocked):
            reasons.append("G05_FAIL_CLOSED_RESULT_REQUIRED")
        elif result is not None and G05_NO_RECOMMENDATION_REQUIRED:
            reasons.append("G05_NO_RECOMMENDATION_REQUIRED")

    recommendation_hash = (
        result.recommended_candidate.candidate_hash
        if result is not None and result.recommended_candidate is not None
        else None
    )
    return GoldenAcceptanceRecord(
        golden_id=case.golden_id,
        status=AcceptanceStatus.PASS if not reasons else AcceptanceStatus.BLOCKED,
        task168_result_hash=replay.result_hash or None,
        task168_result_id=replay.result_id or None,
        selection_result_hash=result.result_hash if result is not None else None,
        selection_result_id=result.result_id if result is not None else None,
        recommended_candidate_id=(
            result.recommended_candidate.candidate_id
            if result is not None and result.recommended_candidate is not None
            else None
        ),
        recommended_candidate_hash=recommendation_hash,
        reason_codes=tuple(dict.fromkeys(reasons)),
        alternative_reason_codes=(result.alternative_reason_codes if result is not None else ()),
        exclusion_reason_codes=_exclusion_reasons(result),
    )


def _gate(status: bool, gate_id: str, *refs: str) -> AcceptanceGateRecord:
    return AcceptanceGateRecord(
        gate_id=gate_id,
        status=AcceptanceStatus.PASS if status else AcceptanceStatus.BLOCKED,
        evidence_refs=tuple(refs),
    )


def _parity_input(
    request_hash_value: str,
    request: Task169ReleaseRequest,
    replays: tuple[_Task168Replay, ...],
) -> Task169ParityInput | None:
    identity = repository_identity()
    if identity is None:
        return None
    head_sha, head_tree = identity
    return Task169ParityInput(
        release_request_hash=request_hash_value,
        task168_request_hashes=tuple(
            (case.golden_id.value, case.task168_request_hash) for case in request.golden_cases
        ),
        task168_result_hashes=tuple(
            (case.golden_id.value, replay.result_hash)
            for case, replay in zip(request.golden_cases, replays, strict=True)
        ),
        task169_result_hashes=tuple(
            (
                case.golden_id.value,
                replay.selection.result_hash if replay.selection is not None else "",
            )
            for case, replay in zip(request.golden_cases, replays, strict=True)
        ),
        task169_result_ids=tuple(
            (
                case.golden_id.value,
                replay.selection.result_id if replay.selection is not None else "",
            )
            for case, replay in zip(request.golden_cases, replays, strict=True)
        ),
        head_sha=head_sha,
        head_tree=head_tree,
        software_version=TASK169_RELEASE_SOFTWARE_VERSION,
    )


def _runtime_observation(
    request_hash_value: str,
    request: Task169ReleaseRequest,
    replays: tuple[_Task168Replay, ...],
) -> Task169DualRuntimeObservation:
    parity = _parity_input(request_hash_value, request, replays)
    if parity is None:
        from .trusted_evidence import _blocked_observation

        return Task169DualRuntimeObservation(
            python311=_blocked_observation("PYTHON_3_11"),
            python312=_blocked_observation("PYTHON_3_12"),
            status="BLOCKED",
            observation_hash="0" * 64,
            evidence_refs=("TASK169_DUAL_RUNTIME_INTERNAL_OBSERVATION",),
        )
    return observe_dual_runtime(input_value=parity)


def validate_request(raw: object) -> Task169ReleaseValidationResult:
    """Replay frozen TASK-168 requests and evaluate TASK-165 release gates."""

    if type(raw) is not Task169ReleaseRequest:
        return _blocked("", ("INVALID_RELEASE_REQUEST_TYPE",))
    request = raw
    failures: list[str] = []
    if request.schema_version != TASK169_RELEASE_SCHEMA_VERSION:
        failures.append("RELEASE_SCHEMA_VERSION_MISMATCH")
    if request.release_version != TASK169_RELEASE_VERSION:
        failures.append("RELEASE_VERSION_MISMATCH")
    if request.source_definition_id != TASK169_RELEASE_SOURCE_DEFINITION_ID:
        failures.append("RELEASE_SOURCE_DEFINITION_MISMATCH")
    if tuple(case.golden_id for case in request.golden_cases) != _GOLDEN_ORDER:
        failures.append("GOLDEN_CASE_SET_OR_ORDER_MISMATCH")
    if request.frozen_tolerance_ledger != FROZEN_TOLERANCE_LEDGER:
        failures.append("FROZEN_TOLERANCE_AUTHORITY_MISMATCH")
    try:
        request_hash_value = release_request_hash(request)
    except (ArithmeticError, TypeError, UnicodeError, ValueError):
        request_hash_value = ""
        failures.append("RELEASE_REQUEST_NOT_CANONICAL")
    if failures:
        return _blocked(request_hash_value, tuple(dict.fromkeys(failures)))

    replays = tuple(_replay_task168(case) for case in request.golden_cases)
    golden_records = tuple(
        _golden_record(case, replay)
        for case, replay in zip(request.golden_cases, replays, strict=True)
    )
    golden_ok = {
        record.golden_id: record.status is AcceptanceStatus.PASS for record in golden_records
    }
    positive_replays = replays[:4]
    positive_results = tuple(replay.selection for replay in positive_replays)
    positive_candidates = tuple(
        _candidate_for_result(replay, result)
        for replay, result in zip(positive_replays, positive_results, strict=True)
    )
    g01, g02, g03, g04 = positive_candidates
    candidate_generation_ok = all(
        replay.batch is not None and replay.batch.total_enumerated_candidates > 0
        for replay in positive_replays
    )
    task168_replay_ok = all(not replay.failures for replay in replays)
    selection_replay_ok = all(
        replay.selection is not None
        or replay.expected_status != Task168ValidationStatus.VALID.value
        for replay in replays
    )
    g04_records = replays[3].batch.candidate_records if replays[3].batch is not None else ()
    g04_dp_rejection = any(
        record.status is CandidateStatus.BLOCKED
        and any(
            blocker.code == "HARD_CONSTRAINT_UNSATISFIED"
            and blocker.field_path in {"max_tube_dp_pa", "max_shell_dp_pa"}
            for blocker in record.blockers
        )
        for record in g04_records
    )
    tube_dp_ok = _constraint(g04, "max_tube_dp_pa") == "PASS" and g04_dp_rejection
    shell_dp_ok = _constraint(g04, "max_shell_dp_pa") == "PASS" and g04_dp_rejection
    duty_ok = all(
        _constraint(candidate, "required_duty_w") == "PASS" for candidate in (g01, g02, g03, g04)
    )
    full_chain_ok = all(_full_chain_evidence(candidate) for candidate in (g01, g02, g03, g04))
    runtime = _runtime_observation(request_hash_value, request, replays)
    parity_ok = runtime.status == "PASS"
    provenance_ok = all(
        replay.selection is not None and bool(replay.selection.provenance_semantic_inputs)
        for replay in replays
    )

    gates = [
        _gate(
            golden_ok[GoldenCaseId.V06_G01] and _full_chain_evidence(g01),
            _GATE_ORDER[0],
        ),
        _gate(full_chain_ok, _GATE_ORDER[1]),
        _gate(full_chain_ok, _GATE_ORDER[2]),
        _gate(full_chain_ok, _GATE_ORDER[3]),
        _gate(
            all(
                candidate is not None and candidate.screening_evidence
                for candidate in positive_candidates
            ),
            _GATE_ORDER[4],
        ),
        _gate(
            golden_ok[GoldenCaseId.V06_G02] and g02 is not None and bool(g02.screening_evidence),
            _GATE_ORDER[5],
        ),
        _gate(
            golden_ok[GoldenCaseId.V06_G02] and g02 is not None and bool(g02.screening_evidence),
            _GATE_ORDER[6],
        ),
        _gate(candidate_generation_ok, _GATE_ORDER[7]),
        _gate(
            candidate_generation_ok and all(result is not None for result in positive_results),
            _GATE_ORDER[8],
        ),
        _gate(golden_ok[GoldenCaseId.V06_G04], _GATE_ORDER[9]),
        _gate(tube_dp_ok, _GATE_ORDER[10]),
        _gate(shell_dp_ok, _GATE_ORDER[11]),
        _gate(duty_ok, _GATE_ORDER[12]),
        _gate(task168_replay_ok and selection_replay_ok, _GATE_ORDER[13]),
        _gate(provenance_ok, _GATE_ORDER[14]),
        _gate(parity_ok, _GATE_ORDER[15]),
    ]
    gates.extend(
        _gate(golden_ok[golden_id], f"GOLDEN_{golden_id.value.replace('-', '_')}")
        for golden_id in _GOLDEN_ORDER
    )
    gates.append(
        _gate(
            all(gate.status is AcceptanceStatus.PASS for gate in gates),
            _GATE_ORDER[-1],
        )
    )
    gates_tuple = tuple(gates)
    if tuple(gate.gate_id for gate in gates_tuple) != _GATE_ORDER:
        return _blocked(request_hash_value, ("RELEASE_GATE_ORDER_INTERNAL_ERROR",))

    blocker_codes = tuple(
        dict.fromkeys(
            code
            for record in golden_records
            for code in record.reason_codes
            if code.endswith("PENDING") or code.endswith("REQUIRED") or code.endswith("MISMATCH")
        )
    )
    if not parity_ok:
        blocker_codes = (*blocker_codes, "TRUSTED_DUAL_RUNTIME_PARITY_FAILED")
    if not blocker_codes and any(gate.status is AcceptanceStatus.BLOCKED for gate in gates_tuple):
        blocker_codes = ("RELEASE_ACCEPTANCE_GATE_BLOCKED",)
    overall = (
        AcceptanceStatus.PASS
        if all(gate.status is AcceptanceStatus.PASS for gate in gates_tuple)
        else AcceptanceStatus.BLOCKED
    )
    provisional = Task169ReleaseResult(
        schema_version=TASK169_RELEASE_RESULT_SCHEMA_VERSION,
        release_version=TASK169_RELEASE_VERSION,
        implementation_software_version=TASK169_RELEASE_SOFTWARE_VERSION,
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        frozen_tolerance_ledger=FROZEN_TOLERANCE_LEDGER,
        golden_records=golden_records,
        acceptance_gates=gates_tuple,
        trusted_runtime_observation_hash=runtime.observation_hash,
        trusted_runtime_status=(
            AcceptanceStatus.PASS if runtime.status == "PASS" else AcceptanceStatus.BLOCKED
        ),
        overall_status=overall,
        blocker_codes=blocker_codes,
        result_hash="",
        result_id="",
    )
    digest = result_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=result_id(digest))
    if (
        result_hash(result) != result.result_hash
        or result_id(result.result_hash) != result.result_id
    ):
        return _blocked(request_hash_value, ("RELEASE_IDENTITY_REPLAY_FAILED",))
    return Task169ReleaseValidationResult(valid=result)


__all__ = ["FROZEN_TOLERANCE_LEDGER", "validate_request"]
