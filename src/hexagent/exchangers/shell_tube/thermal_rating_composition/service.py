"""TASK163 composition service.

The service consumes the accepted TASK162 result and producer replay evidence;
it never replays or recalculates TASK162 engineering semantics locally.
"""

from __future__ import annotations

from dataclasses import replace
from typing import cast

from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.shell_tube.thermal_performance_closure.models import (
    Task162Applicability,
    Task162Completeness,
    Task162EnergyBalanceEvidence,
    Task162Result,
    Task162SelectedMethodIdentity,
    Task162SuccessReplayEvidence,
    Task162SuccessVerificationFailureReason,
    Task162SuccessVerificationResult,
    Task162SuccessVerificationStatus,
    Task162TerminalClosureEvidence,
)
from hexagent.exchangers.shell_tube.thermal_performance_closure.service import (
    verify_task162_success,
)

from .canonical import (
    raw_blocked_hash,
    raw_blocked_id,
    raw_request_projection_hash,
    request_hash,
    result_id,
    success_hash_from_inputs,
    task162_result_identity_projection,
    task162_success_replay_evidence_identity_projection,
    typed_blocked_hash,
    typed_blocked_id,
)
from .errors import blocker, normalize_blockers
from .models import (
    TASK163_IMPLEMENTATION_SOFTWARE_VERSION,
    TASK163_RAW_BOUNDARY_SCHEMA_VERSION,
    TASK163_SCHEMA_VERSION,
    TASK163_SOURCE_DEFINITION_ID,
    TASK163_TYPED_BLOCKED_SCHEMA_VERSION,
    TASK163_VERSION,
    Task163Applicability,
    Task163ApplicabilityCheckName,
    Task163ApplicabilityStatus,
    Task163Blocker,
    Task163CheckStatus,
    Task163Completeness,
    Task163CompletenessField,
    Task163CompletenessStatus,
    Task163DeferredCapabilities,
    Task163DeferredCapability,
    Task163DeferredStatus,
    Task163FailureCode,
    Task163FailureStage,
    Task163HeatDutyProjection,
    Task163OutletTemperatureProjection,
    Task163PreResultIdentityInputs,
    Task163Provenance,
    Task163RatingPerformanceProjection,
    Task163RawBoundaryBlockedResult,
    Task163RawRequestProjection,
    Task163Request,
    Task163Result,
    Task163Task162Evidence,
    Task163TypedBlockedResult,
    Task163ValidationResult,
    Task163ValidationStatus,
)
from .provenance import (
    build_provenance_semantic_inputs,
    build_success_provenance,
    verify_provenance,
)
from .raw_projection import project_raw_request_with_diagnostics

TASK162_APPLICABILITY_CHECKS: tuple[str, ...] = (
    "TASK160_ACCEPTED",
    "TASK161_ACCEPTED",
    "TASK038_ACCEPTED",
    "SAME_CASE_BINDING_MATCHED",
    "CASE_BINDING_COMPLETE",
    "SOURCE_METHOD_APPLICABLE",
    "NUMERICAL_DOMAIN_VALID",
    "ENERGY_BALANCE_CLOSED",
    "TERMINAL_CLOSURE_POSITIVE",
)
TASK162_COMPLETENESS_FIELDS: tuple[str, ...] = (
    "ntu",
    "p_source",
    "epsilon",
    "q_max",
    "q_method",
    "hot_outlet_temperature",
    "cold_outlet_temperature",
    "q_hot",
    "q_cold",
    "energy_balance_evidence",
    "terminal_closure_evidence",
    "applicability",
    "provenance",
)
TASK163_APPLICABILITY_CHECKS: tuple[Task163ApplicabilityCheckName, ...] = tuple(
    Task163ApplicabilityCheckName
)
TASK163_COMPLETENESS_FIELDS: tuple[Task163CompletenessField, ...] = tuple(Task163CompletenessField)
TASK163_DEFERRED_CAPABILITIES: tuple[Task163DeferredCapability, ...] = tuple(
    Task163DeferredCapability
)


def _metadata(value: object) -> tuple[tuple[str, str], ...]:
    if type(value) is not tuple:
        raise ValueError("request_metadata must be a tuple")
    pairs: list[tuple[str, str]] = []
    for pair in value:
        if type(pair) is not tuple or len(pair) != 2:
            raise ValueError("request_metadata pair")
        key, item = pair
        if type(key) is not str or type(item) is not str:
            raise ValueError("request_metadata scalar")
        key.encode("utf-8", "strict")
        item.encode("utf-8", "strict")
        pairs.append((key, item))
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate request_metadata key")
    return tuple(sorted(pairs, key=lambda item: (item[0].encode("utf-8"), item[1].encode("utf-8"))))


def _raw_blocked(
    projection: Task163RawRequestProjection,
    projection_hash: str,
    reasons: tuple[Task163FailureCode, ...],
) -> Task163ValidationResult:
    blockers = normalize_blockers(
        blocker(reason, Task163FailureStage.RAW_BOUNDARY) for reason in reasons
    )
    if not blockers:
        blockers = (
            blocker(Task163FailureCode.UNSUPPORTED_RAW_VALUE, Task163FailureStage.RAW_BOUNDARY),
        )
    preliminary = Task163RawBoundaryBlockedResult(
        schema_version=TASK163_RAW_BOUNDARY_SCHEMA_VERSION,
        task163_version=TASK163_VERSION,
        implementation_software_version=TASK163_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=Task163FailureStage.RAW_BOUNDARY,
        raw_request_projection=projection,
        raw_request_projection_hash=projection_hash,
        blockers=blockers,
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=raw_blocked_id("0" * 64),
    )
    value = replace(
        preliminary,
        blocked_result_hash=raw_blocked_hash(preliminary),
    )
    return Task163ValidationResult(
        status=Task163ValidationStatus.RAW_BOUNDARY_BLOCKED,
        raw_boundary_blocked=replace(
            value, blocked_result_id=raw_blocked_id(value.blocked_result_hash)
        ),
    )


def _typed_blocked(
    request_hash_value: str,
    blockers: tuple[Task163Blocker, ...],
    *,
    stage: Task163FailureStage,
    task162_identity: object | None = None,
) -> Task163ValidationResult:
    identity = None
    if type(task162_identity) is Task162Result:
        try:
            identity = task162_result_identity_projection(task162_identity)
        except BaseException:
            identity = None
    preliminary = Task163TypedBlockedResult(
        schema_version=TASK163_TYPED_BLOCKED_SCHEMA_VERSION,
        task163_version=TASK163_VERSION,
        implementation_software_version=TASK163_IMPLEMENTATION_SOFTWARE_VERSION,
        failure_stage=stage,
        request_hash=request_hash_value,
        task162_result_identity_or_none=identity,
        blockers=normalize_blockers(blockers),
        warnings=(),
        blocked_result_hash="",
        blocked_result_id=typed_blocked_id("0" * 64),
    )
    value = replace(preliminary, blocked_result_hash=typed_blocked_hash(preliminary))
    return Task163ValidationResult(
        status=Task163ValidationStatus.TYPED_BLOCKED,
        typed_blocked=replace(value, blocked_result_id=typed_blocked_id(value.blocked_result_hash)),
    )


def _parse_request(raw: object) -> tuple[Task163Request | None, tuple[Task163Blocker, ...]]:
    stage = Task163FailureStage.TYPED_VALIDATION
    if type(raw) is not dict:
        return None, (blocker(Task163FailureCode.INVALID_REQUEST_TYPE, stage),)
    expected = {
        "schema_version",
        "task163_version",
        "source_definition_id",
        "task162_result",
        "task162_success_replay_evidence",
        "request_metadata",
    }
    blockers: list[Task163Blocker] = []
    keys = set(raw)
    if keys != expected:
        blockers.append(blocker(Task163FailureCode.INVALID_REQUEST_SCHEMA, stage))
    schema = raw.get("schema_version")
    version = raw.get("task163_version")
    source = raw.get("source_definition_id")
    if type(schema) is not str or type(version) is not str or type(source) is not str:
        blockers.append(blocker(Task163FailureCode.INVALID_REQUEST_SCHEMA, stage))
    if type(version) is str and version != TASK163_VERSION:
        blockers.append(blocker(Task163FailureCode.UNSUPPORTED_TASK163_VERSION, stage))
    if type(source) is str and source != TASK163_SOURCE_DEFINITION_ID:
        blockers.append(blocker(Task163FailureCode.SOURCE_DEFINITION_ID_MISMATCH, stage))
    task162 = raw.get("task162_result")
    evidence = raw.get("task162_success_replay_evidence")
    if type(task162) is not Task162Result:
        blockers.append(blocker(Task163FailureCode.INVALID_TASK162_RESULT, stage))
    if type(evidence) is not Task162SuccessReplayEvidence:
        blockers.append(blocker(Task163FailureCode.INVALID_TASK162_REPLAY_EVIDENCE, stage))
    metadata = raw.get("request_metadata")
    try:
        normalized_metadata = _metadata(metadata)
    except BaseException:
        blockers.append(blocker(Task163FailureCode.INVALID_REQUEST_SCHEMA, stage))
        normalized_metadata = ()
    normalized = normalize_blockers(blockers)
    if normalized:
        return None, normalized
    return (
        Task163Request(
            schema_version=cast(str, schema),
            task163_version=cast(str, version),
            source_definition_id=cast(str, source),
            task162_result=cast(Task162Result, task162),
            task162_success_replay_evidence=cast(Task162SuccessReplayEvidence, evidence),
            request_metadata=normalized_metadata,
        ),
        (),
    )


def _verification_blockers(
    result: object,
) -> tuple[Task163Blocker, ...]:
    stage = Task163FailureStage.TASK162_REPLAY
    if type(result) is not Task162SuccessVerificationResult:
        return (blocker(Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED, stage),)
    if result.status is Task162SuccessVerificationStatus.ACCEPTED:
        if result.failure_reason_or_none is not None:
            return (blocker(Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED, stage),)
        return ()
    if result.status is not Task162SuccessVerificationStatus.REJECTED:
        return (blocker(Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED, stage),)
    reason = result.failure_reason_or_none
    if type(reason) is not Task162SuccessVerificationFailureReason:
        return (blocker(Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED, stage),)
    mapping = dict(
        [
            (
                Task162SuccessVerificationFailureReason.TASK162_PRODUCER_VERIFICATION_FAILED,
                Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED,
            ),
            (
                Task162SuccessVerificationFailureReason.TASK162_IDENTITY_REPLAY_FAILED,
                Task163FailureCode.TASK162_IDENTITY_REPLAY_FAILED,
            ),
            (
                Task162SuccessVerificationFailureReason.TASK162_NOT_APPLICABLE,
                Task163FailureCode.TASK162_NOT_APPLICABLE,
            ),
            (
                Task162SuccessVerificationFailureReason.TASK162_NOT_COMPLETE,
                Task163FailureCode.TASK162_NOT_COMPLETE,
            ),
            (
                Task162SuccessVerificationFailureReason.TASK162_PROVENANCE_INVALID,
                Task163FailureCode.TASK162_PROVENANCE_INVALID,
            ),
        ]
    )
    code = mapping.get(reason, Task163FailureCode.TASK162_PRODUCER_VERIFICATION_FAILED)
    return (blocker(code, stage),)


def _task162_acceptance_blockers(value: Task162Result) -> list[Task163Blocker]:
    blockers: list[Task163Blocker] = []
    try:
        applicability = value.applicability
        actual_checks = tuple((name, status) for name, status in applicability.checks)
        applicability_invalid = type(applicability) is not Task162Applicability or (
            applicability.status != "APPLICABLE"
            or tuple(name for name, _ in actual_checks) != TASK162_APPLICABILITY_CHECKS
            or any(status != "PASS" for _, status in actual_checks)
        )
    except BaseException:
        applicability_invalid = True
    if applicability_invalid:
        blockers.append(
            blocker(Task163FailureCode.TASK162_NOT_APPLICABLE, Task163FailureStage.TASK162_REPLAY)
        )
    try:
        completeness = value.completeness
        completeness_invalid = type(completeness) is not Task162Completeness or (
            completeness.status != "COMPLETE"
            or completeness.required_fields != TASK162_COMPLETENESS_FIELDS
        )
    except BaseException:
        completeness_invalid = True
    if completeness_invalid:
        blockers.append(
            blocker(Task163FailureCode.TASK162_NOT_COMPLETE, Task163FailureStage.TASK162_REPLAY)
        )
    return blockers


def _composition(
    value: Task162Result,
) -> tuple[
    Task163RatingPerformanceProjection | None,
    Task163HeatDutyProjection | None,
    Task163OutletTemperatureProjection | None,
    Task162EnergyBalanceEvidence | None,
    Task162TerminalClosureEvidence | None,
    tuple[Task163Blocker, ...],
]:
    stage = Task163FailureStage.RATING_COMPOSITION
    blockers: list[Task163Blocker] = []
    method = value.selected_method_identity
    energy = value.energy_balance_evidence
    terminal = value.terminal_closure_evidence
    if type(method) is not Task162SelectedMethodIdentity:
        blockers.append(
            blocker(
                Task163FailureCode.RATING_COMPOSITION_INCOMPLETE, stage, "selected_method_identity"
            )
        )
    if type(energy) is not Task162EnergyBalanceEvidence:
        blockers.append(
            blocker(
                Task163FailureCode.RATING_COMPOSITION_INCOMPLETE, stage, "energy_balance_evidence"
            )
        )
    if type(terminal) is not Task162TerminalClosureEvidence:
        blockers.append(
            blocker(
                Task163FailureCode.RATING_COMPOSITION_INCOMPLETE,
                stage,
                "terminal_temperature_evidence",
            )
        )
    if blockers:
        return None, None, None, None, None, normalize_blockers(blockers)
    assert type(method) is Task162SelectedMethodIdentity
    assert type(energy) is Task162EnergyBalanceEvidence
    assert type(terminal) is Task162TerminalClosureEvidence
    checks = (
        method.selected_baffle_relation == value.selected_baffle_relation,
        value.q_method == energy.q_method,
        value.q_hot == energy.q_hot_nominal,
        value.q_cold == energy.q_cold_nominal,
    )
    if not all(checks):
        blockers.append(
            blocker(
                Task163FailureCode.RATING_COMPOSITION_INCOMPLETE,
                stage,
                "producer-owned-semantic-join",
            )
        )
        return None, None, None, None, None, normalize_blockers(blockers)
    performance = Task163RatingPerformanceProjection(
        selected_method_identity=method,
        selected_baffle_relation=value.selected_baffle_relation,
        ntu=value.ntu,
        r_source=value.r_source,
        p_source=value.p_source,
        epsilon=value.epsilon,
    )
    duty = Task163HeatDutyProjection(
        q_max=value.q_max,
        q_method=value.q_method,
        q_hot=value.q_hot,
        q_cold=value.q_cold,
    )
    outlet = Task163OutletTemperatureProjection(
        hot_outlet_temperature=value.hot_outlet_temperature,
        cold_outlet_temperature=value.cold_outlet_temperature,
    )
    return performance, duty, outlet, energy, terminal, ()


def _applicability() -> Task163Applicability:
    return Task163Applicability(
        status=Task163ApplicabilityStatus.APPLICABLE,
        checks=tuple((name, Task163CheckStatus.PASS) for name in TASK163_APPLICABILITY_CHECKS),
    )


def _completeness() -> Task163Completeness:
    return Task163Completeness(
        status=Task163CompletenessStatus.COMPLETE,
        required_fields=TASK163_COMPLETENESS_FIELDS,
    )


def _deferred() -> Task163DeferredCapabilities:
    return Task163DeferredCapabilities(
        status=Task163DeferredStatus.DECLARED,
        capabilities=TASK163_DEFERRED_CAPABILITIES,
    )


def _result(
    request: Task163Request,
    request_hash_value: str,
    task162_evidence: Task163Task162Evidence,
    performance: Task163RatingPerformanceProjection,
    duty: Task163HeatDutyProjection,
    outlet: Task163OutletTemperatureProjection,
    energy: Task162EnergyBalanceEvidence,
    terminal: Task162TerminalClosureEvidence,
) -> Task163Result | None:
    applicability = _applicability()
    completeness = _completeness()
    deferred = _deferred()
    semantic_inputs = build_provenance_semantic_inputs(
        task162_evidence=task162_evidence,
        performance=performance,
        duty=duty,
        outlet=outlet,
        energy=energy,
        terminal=terminal,
        deferred=deferred,
        applicability=applicability,
        completeness=completeness,
    )
    preimage = Task163PreResultIdentityInputs(
        schema_version=TASK163_SCHEMA_VERSION,
        task163_version=TASK163_VERSION,
        implementation_software_version=TASK163_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK163_SOURCE_DEFINITION_ID,
        request_hash=request_hash_value,
        task162_evidence=task162_evidence,
        rating_performance_projection=performance,
        heat_duty_projection=duty,
        outlet_temperature_projection=outlet,
        energy_balance_evidence=energy,
        terminal_temperature_evidence=terminal,
        applicability=applicability,
        completeness=completeness,
        deferred_capabilities=deferred,
        warnings_normalized=(),
        blockers_normalized=(),
        provenance_semantic_inputs=semantic_inputs,
    )
    result_hash_value = success_hash_from_inputs(preimage)
    result_id_value = result_id(result_hash_value)
    provisional = Task163Result(
        schema_version=TASK163_SCHEMA_VERSION,
        task163_version=TASK163_VERSION,
        implementation_software_version=TASK163_IMPLEMENTATION_SOFTWARE_VERSION,
        source_definition_id=TASK163_SOURCE_DEFINITION_ID,
        request_hash=request_hash_value,
        task162_evidence=task162_evidence,
        rating_performance_projection=performance,
        heat_duty_projection=duty,
        outlet_temperature_projection=outlet,
        energy_balance_evidence=energy,
        terminal_temperature_evidence=terminal,
        applicability=applicability,
        completeness=completeness,
        deferred_capabilities=deferred,
        warnings=(),
        blockers=(),
        provenance_semantic_inputs=semantic_inputs,
        provenance=Task163Provenance(provenance_hash="", graph=ProvenanceGraph()),
        result_hash=result_hash_value,
        result_id=result_id_value,
    )
    provenance = build_success_provenance(semantic_inputs=semantic_inputs, result=provisional)
    result_value = replace(provisional, provenance=provenance)
    if not verify_provenance(result_value.provenance):
        return None
    replay_preimage = replace(preimage)
    if success_hash_from_inputs(replay_preimage) != result_value.result_hash:
        return None
    if result_id(result_value.result_hash) != result_value.result_id:
        return None
    return result_value


def validate_request(raw: object) -> Task163ValidationResult:
    """Validate and compose a TASK163 request through the frozen stage order."""
    outcome = project_raw_request_with_diagnostics(raw)
    projection_hash = raw_request_projection_hash(outcome.projection)
    if outcome.reasons:
        return _raw_blocked(outcome.projection, projection_hash, outcome.reasons)

    request, typed_errors = _parse_request(raw)
    if typed_errors or request is None:
        return _typed_blocked(
            projection_hash, typed_errors, stage=Task163FailureStage.TYPED_VALIDATION
        )

    try:
        request_hash_value = request_hash(request)
    except BaseException:
        return _typed_blocked(
            projection_hash,
            (blocker(Task163FailureCode.IDENTITY_REPLAY_FAILED, Task163FailureStage.IDENTITY),),
            stage=Task163FailureStage.IDENTITY,
            task162_identity=request.task162_result,
        )

    try:
        verification = verify_task162_success(
            request.task162_result,
            request.task162_success_replay_evidence,
        )
    except BaseException:
        verification = None
    replay_blockers = list(_verification_blockers(verification))
    replay_blockers.extend(_task162_acceptance_blockers(request.task162_result))
    if replay_blockers:
        return _typed_blocked(
            request_hash_value,
            tuple(replay_blockers),
            stage=Task163FailureStage.TASK162_REPLAY,
            task162_identity=request.task162_result,
        )

    try:
        task162_evidence = Task163Task162Evidence(
            task162_result_identity_projection=task162_result_identity_projection(
                request.task162_result
            ),
            task162_success_replay_evidence_identity_projection=(
                task162_success_replay_evidence_identity_projection(
                    request.task162_success_replay_evidence
                )
            ),
        )
        performance, duty, outlet, energy, terminal, composition_blockers = _composition(
            request.task162_result
        )
    except BaseException:
        performance = duty = outlet = energy = terminal = None
        composition_blockers = (
            blocker(
                Task163FailureCode.RATING_COMPOSITION_INCOMPLETE,
                Task163FailureStage.RATING_COMPOSITION,
            ),
        )
        task162_evidence = None
    if (
        composition_blockers
        or task162_evidence is None
        or performance is None
        or duty is None
        or outlet is None
        or energy is None
        or terminal is None
    ):
        return _typed_blocked(
            request_hash_value,
            composition_blockers,
            stage=Task163FailureStage.RATING_COMPOSITION,
            task162_identity=request.task162_result,
        )

    applicability = _applicability()
    if applicability.status is not Task163ApplicabilityStatus.APPLICABLE or any(
        status is not Task163CheckStatus.PASS for _, status in applicability.checks
    ):
        return _typed_blocked(
            request_hash_value,
            (
                blocker(
                    Task163FailureCode.RATING_APPLICABILITY_FAILED,
                    Task163FailureStage.RATING_APPLICABILITY,
                ),
            ),
            stage=Task163FailureStage.RATING_APPLICABILITY,
            task162_identity=request.task162_result,
        )
    completeness = _completeness()
    if (
        completeness.status is not Task163CompletenessStatus.COMPLETE
        or completeness.required_fields != TASK163_COMPLETENESS_FIELDS
    ):
        return _typed_blocked(
            request_hash_value,
            (
                blocker(
                    Task163FailureCode.RATING_COMPLETENESS_FAILED,
                    Task163FailureStage.RATING_COMPLETENESS,
                ),
            ),
            stage=Task163FailureStage.RATING_COMPLETENESS,
            task162_identity=request.task162_result,
        )

    result_value = _result(
        request,
        request_hash_value,
        task162_evidence,
        performance,
        duty,
        outlet,
        energy,
        terminal,
    )
    if result_value is None:
        return _typed_blocked(
            request_hash_value,
            (blocker(Task163FailureCode.PROVENANCE_INVALID, Task163FailureStage.PROVENANCE),),
            stage=Task163FailureStage.PROVENANCE,
            task162_identity=request.task162_result,
        )
    return Task163ValidationResult(status=Task163ValidationStatus.VALID, valid=result_value)


__all__ = ["validate_request"]
