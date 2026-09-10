"""TASK-169 deterministic candidate selection boundary."""

from __future__ import annotations

from dataclasses import replace
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    batch_result_hash as task168_batch_result_hash,
    result_id as task168_result_id,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.models import (
    ApplicabilityStatus,
    CandidateDisposition,
    CandidateRecord,
    CandidateStage,
    CandidateStatus,
    CompletenessStatus,
    Task168BatchResult,
)
from hexagent.exchangers.shell_tube.manufacturable_candidates.provenance import (
    verify_provenance_graph,
)

from .canonical import (
    blocked_hash,
    blocked_id,
    rank_record_hash,
    ranking_policy_hash,
    request_hash,
    result_hash,
    result_id,
)
from .models import (
    SUPPORTED_RANKING_METRICS,
    TASK169_BLOCKED_SCHEMA_VERSION,
    TASK169_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK169_RESULT_SCHEMA_VERSION,
    TASK169_SCHEMA_VERSION,
    TASK169_SOURCE_DEFINITION_ID,
    TASK169_VERSION,
    CandidateExclusionRecord,
    CandidateRankingRecord,
    RankingDirection,
    SelectionStatus,
    Task169RankingPolicy,
    Task169Request,
    Task169Result,
    Task169TypedBlockedResult,
    Task169ValidationResult,
    ValidationStatus,
)

_RANKING_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
_MAX_TOP_N = 25


def _blocked(request_hash_value: str, codes: tuple[str, ...]) -> Task169ValidationResult:
    provisional = Task169TypedBlockedResult(
        schema_version=TASK169_BLOCKED_SCHEMA_VERSION,
        task169_version=TASK169_VERSION,
        implementation_software_version=TASK169_IMPLEMENTATION_SOFTWARE_VERSION,
        request_hash=request_hash_value,
        blocker_codes=tuple(dict.fromkeys(codes)),
        result_hash="",
        result_id="",
    )
    digest = blocked_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=blocked_id(digest))
    return Task169ValidationResult(status=ValidationStatus.TYPED_BLOCKED, typed_blocked=result)


def _validate_policy(value: Task169RankingPolicy) -> tuple[str, ...]:
    failures: list[str] = []
    if not value.policy_id or not value.policy_version or not value.source_id:
        failures.append("RANKING_POLICY_IDENTITY_REQUIRED")
    if value.approval_status != "APPROVED":
        failures.append("RANKING_POLICY_NOT_APPROVED")
    if value.top_n < 1 or value.top_n > _MAX_TOP_N:
        failures.append("RANKING_TOP_N_OUT_OF_RANGE")
    if not value.objectives:
        failures.append("RANKING_OBJECTIVE_REQUIRED")
    seen: set[str] = set()
    positive_weight = False
    for objective in value.objectives:
        if objective.metric not in SUPPORTED_RANKING_METRICS:
            failures.append("UNSUPPORTED_RANKING_METRIC")
        if objective.metric in seen:
            failures.append("DUPLICATE_RANKING_METRIC")
        seen.add(objective.metric)
        if not objective.weight.is_finite() or objective.weight < 0:
            failures.append("RANKING_WEIGHT_INVALID")
        if objective.weight > 0:
            positive_weight = True
        if not objective.scale.is_finite() or objective.scale <= 0:
            failures.append("RANKING_SCALE_INVALID")
    if value.objectives and not positive_weight:
        failures.append("RANKING_POSITIVE_WEIGHT_REQUIRED")
    if not value.warning_penalty.is_finite() or value.warning_penalty < 0:
        failures.append("RANKING_WARNING_PENALTY_INVALID")
    try:
        expected = ranking_policy_hash(value)
    except (TypeError, ValueError, UnicodeError, ArithmeticError):
        failures.append("RANKING_POLICY_NOT_CANONICAL")
    else:
        if value.canonical_hash != expected:
            failures.append("RANKING_POLICY_HASH_MISMATCH")
    return tuple(dict.fromkeys(failures))


def _validate_task168_result(value: Task168BatchResult) -> tuple[str, ...]:
    failures: list[str] = []
    try:
        if task168_batch_result_hash(value) != value.result_hash:
            failures.append("TASK168_RESULT_HASH_MISMATCH")
        if task168_result_id(value.result_hash) != value.result_id:
            failures.append("TASK168_RESULT_ID_MISMATCH")
    except (TypeError, ValueError, UnicodeError, ArithmeticError):
        failures.append("TASK168_RESULT_NOT_CANONICAL")
    if not verify_provenance_graph(value.provenance):
        failures.append("TASK168_PROVENANCE_INVALID")
    if value.applicability.status is not ApplicabilityStatus.APPLICABLE:
        failures.append("TASK168_APPLICABILITY_BLOCKED")
    if value.completeness.status is not CompletenessStatus.COMPLETE:
        failures.append("TASK168_COMPLETENESS_INCOMPLETE")
    if value.total_enumerated_candidates != len(value.candidate_records):
        failures.append("TASK168_CANDIDATE_COUNT_MISMATCH")
    counts = {
        CandidateStatus.PASS: value.pass_count,
        CandidateStatus.WARN: value.warn_count,
        CandidateStatus.BLOCKED: value.blocked_count,
    }
    for status, expected in counts.items():
        observed = sum(record.status is status for record in value.candidate_records)
        if observed != expected:
            failures.append("TASK168_STATUS_COUNT_MISMATCH")
            break
    return tuple(dict.fromkeys(failures))


def _metric_map(record: CandidateRecord) -> dict[str, str]:
    return {key: value for key, value in record.metrics}


def _candidate_static_exclusion(record: CandidateRecord) -> str | None:
    if record.disposition is not CandidateDisposition.EVALUATED:
        return "TASK168_CANDIDATE_NOT_EVALUATED"
    if record.status not in {CandidateStatus.PASS, CandidateStatus.WARN}:
        return "TASK168_CANDIDATE_BLOCKED"
    if record.stage is not CandidateStage.COMPLETE:
        return "TASK168_CANDIDATE_NOT_COMPLETE"
    if record.blockers:
        return "TASK168_CANDIDATE_HAS_HARD_BLOCKER"
    return None


def _score_candidate(
    record: CandidateRecord,
    policy: Task169RankingPolicy,
) -> tuple[Decimal, tuple[tuple[str, str], ...]] | None:
    metrics = _metric_map(record)
    objective_values: list[tuple[str, str]] = []
    with localcontext(_RANKING_CONTEXT):
        score = Decimal(0)
        for objective in policy.objectives:
            raw = metrics.get(objective.metric)
            if raw is None:
                return None
            try:
                value = Decimal(raw)
            except (InvalidOperation, ValueError):
                return None
            if not value.is_finite():
                return None
            normalized = value / objective.scale
            signed = (
                normalized
                if objective.direction is RankingDirection.MINIMIZE
                else -normalized
            )
            score += objective.weight * signed
            objective_values.append((objective.metric, str(value)))
        if record.status is CandidateStatus.WARN:
            score += policy.warning_penalty
        return (+score, tuple(objective_values))


def _rank(
    records: tuple[CandidateRecord, ...],
    policy: Task169RankingPolicy,
) -> tuple[tuple[CandidateRankingRecord, ...], tuple[CandidateExclusionRecord, ...]]:
    scored: list[tuple[Decimal, bytes, CandidateRecord, tuple[tuple[str, str], ...]]] = []
    excluded: list[CandidateExclusionRecord] = []
    for record in records:
        reason = _candidate_static_exclusion(record)
        if reason is not None:
            excluded.append(
                CandidateExclusionRecord(
                    candidate_id=record.candidate_id,
                    candidate_hash=record.candidate_hash,
                    source_status=record.status.value,
                    reason_code=reason,
                    evidence_refs=tuple(item.code for item in record.blockers),
                )
            )
            continue
        scored_value = _score_candidate(record, policy)
        if scored_value is None:
            excluded.append(
                CandidateExclusionRecord(
                    candidate_id=record.candidate_id,
                    candidate_hash=record.candidate_hash,
                    source_status=record.status.value,
                    reason_code="RANKING_METRIC_MISSING_OR_INVALID",
                )
            )
            continue
        score, objective_values = scored_value
        scored.append((score, record.candidate_hash.encode("utf-8"), record, objective_values))

    scored.sort(key=lambda item: (item[0], item[1]))
    ranked: list[CandidateRankingRecord] = []
    for index, (score, _, record, objective_values) in enumerate(scored, start=1):
        provisional = CandidateRankingRecord(
            rank=index,
            candidate_id=record.candidate_id,
            candidate_hash=record.candidate_hash,
            source_status=record.status.value,
            composite_score=score,
            objective_values=objective_values,
            warning_count=len(record.warnings),
            record_hash="",
        )
        ranked.append(replace(provisional, record_hash=rank_record_hash(provisional)))
    excluded.sort(key=lambda item: item.candidate_hash.encode("utf-8"))
    return tuple(ranked), tuple(excluded)


def validate_request(raw: object) -> Task169ValidationResult:
    """Verify one TASK-168 batch and deterministically select recommendable candidates."""

    if type(raw) is not Task169Request:
        return _blocked("", ("INVALID_REQUEST_TYPE",))
    request = raw
    failures: list[str] = []
    if request.schema_version != TASK169_SCHEMA_VERSION:
        failures.append("SCHEMA_VERSION_MISMATCH")
    if request.task169_version != TASK169_VERSION:
        failures.append("TASK169_VERSION_MISMATCH")
    if request.source_definition_id != TASK169_SOURCE_DEFINITION_ID:
        failures.append("SOURCE_DEFINITION_ID_MISMATCH")
    failures.extend(_validate_policy(request.ranking_policy))
    failures.extend(_validate_task168_result(request.task168_result))
    try:
        request_hash_value = request_hash(request)
    except (TypeError, ValueError, UnicodeError, ArithmeticError):
        request_hash_value = ""
        failures.append("REQUEST_NOT_CANONICAL")
    if failures:
        return _blocked(request_hash_value, tuple(dict.fromkeys(failures)))

    ranked, excluded = _rank(request.task168_result.candidate_records, request.ranking_policy)
    top = ranked[: request.ranking_policy.top_n]
    recommended = top[0] if top else None
    alternatives = top[1:] if len(top) > 1 else ()
    selection_status = (
        SelectionStatus.SELECTED
        if recommended is not None
        else SelectionStatus.NO_RECOMMENDABLE_CANDIDATE
    )
    semantic_inputs = (
        ("TASK168_RESULT_HASH", request.task168_result.result_hash),
        ("TASK168_RESULT_ID", request.task168_result.result_id),
        ("TASK168_PROVENANCE_HASH", request.task168_result.provenance.graph_hash),
        ("TASK169_RANKING_POLICY_HASH", request.ranking_policy.canonical_hash),
    )
    provisional = Task169Result(
        schema_version=TASK169_RESULT_SCHEMA_VERSION,
        task169_version=TASK169_VERSION,
        implementation_software_version=TASK169_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=request.source_definition_id,
        request_hash=request_hash_value,
        source_task168_result_hash=request.task168_result.result_hash,
        source_task168_result_id=request.task168_result.result_id,
        source_task168_provenance_hash=request.task168_result.provenance.graph_hash,
        ranking_policy_hash=request.ranking_policy.canonical_hash,
        selection_status=selection_status,
        recommendable_candidate_count=len(ranked),
        excluded_candidate_count=len(excluded),
        ranked_candidates=ranked,
        recommended_candidate=recommended,
        alternatives=alternatives,
        excluded_candidates=excluded,
        provenance_semantic_inputs=semantic_inputs,
        result_hash="",
        result_id="",
    )
    digest = result_hash(provisional)
    result = replace(provisional, result_hash=digest, result_id=result_id(digest))
    if (
        result_hash(result) != result.result_hash
        or result_id(result.result_hash) != result.result_id
    ):
        return _blocked(request_hash_value, ("TASK169_IDENTITY_REPLAY_FAILED",))
    return Task169ValidationResult(status=ValidationStatus.VALID, valid=result)


__all__ = ["validate_request"]
