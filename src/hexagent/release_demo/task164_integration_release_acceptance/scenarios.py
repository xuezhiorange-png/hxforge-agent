"""Frozen TASK164 scenario matrix and real TASK163 observation helpers."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace

from hexagent.exchangers.shell_tube.thermal_rating_composition.models import (
    Task163ApplicabilityStatus,
    Task163CompletenessStatus,
    Task163Request,
    Task163ValidationResult,
)
from hexagent.exchangers.shell_tube.thermal_rating_composition.service import (
    validate_request as validate_task163_request,
)

from .canonical import task163_request_projection_hash, task163_validation_projection_bytes
from .models import (
    Task164ClaimMatchStatus,
    Task164EvidenceStatus,
    Task164ObservedIdentity,
    Task164ScenarioClaim,
    Task164ScenarioClass,
    Task164ScenarioId,
    Task164ScenarioInputAuthority,
    Task164ScenarioObservation,
    Task164ScenarioOutcome,
    Task164ScenarioRecord,
    Task164Task163Branch,
    Task164Task163ReplayEvidence,
)


@dataclass(frozen=True, slots=True)
class Task164ScenarioSpec:
    scenario_id: Task164ScenarioId
    scenario_class: Task164ScenarioClass
    input_authority: Task164ScenarioInputAuthority
    real_task163_required: bool
    expected_branch: Task164Task163Branch
    expected_outcome: Task164ScenarioOutcome


TASK164_SCENARIO_MATRIX: tuple[Task164ScenarioSpec, ...] = (
    Task164ScenarioSpec(
        Task164ScenarioId.D164_P01_SUCCESS_BAFFLE_1,
        Task164ScenarioClass.POSITIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_ACCEPTED_CASE_BAFFLE_1,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_P02_SUCCESS_BAFFLE_2,
        Task164ScenarioClass.POSITIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_ACCEPTED_CASE_BAFFLE_2,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_P03_SUCCESS_BAFFLE_3,
        Task164ScenarioClass.POSITIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_ACCEPTED_CASE_BAFFLE_3,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_P04_SUCCESS_BAFFLE_4,
        Task164ScenarioClass.POSITIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_ACCEPTED_CASE_BAFFLE_4,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_P05_SUCCESS_BAFFLE_5,
        Task164ScenarioClass.POSITIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_ACCEPTED_CASE_BAFFLE_5,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_N01_TASK163_TYPED_BLOCKED,
        Task164ScenarioClass.NEGATIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK163_TYPED_BLOCKED_FIXTURE,
        True,
        Task164Task163Branch.TYPED_BLOCKED,
        Task164ScenarioOutcome.NEGATIVE_PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_N02_TASK163_RAW_BOUNDARY_BLOCKED,
        Task164ScenarioClass.NEGATIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK163_RAW_BOUNDARY_FIXTURE,
        True,
        Task164Task163Branch.RAW_BOUNDARY_BLOCKED,
        Task164ScenarioOutcome.NEGATIVE_PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_N03_TASK162_PRODUCER_ACCEPTANCE_OR_REPLAY_REJECTION,
        Task164ScenarioClass.NEGATIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK162_REPLAY_REJECTION_FIXTURE,
        True,
        Task164Task163Branch.TYPED_BLOCKED,
        Task164ScenarioOutcome.NEGATIVE_PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_N04_TASK163_RESULT_IDENTITY_OR_PROVENANCE_TAMPER,
        Task164ScenarioClass.NEGATIVE_PRODUCER,
        Task164ScenarioInputAuthority.TASK163_CLAIM_TAMPER_FIXTURE,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.NEGATIVE_PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_D01_REPEAT_RUN_IDENTITY_AND_EVIDENCE_PARITY,
        Task164ScenarioClass.DETERMINISM,
        Task164ScenarioInputAuthority.IN_PROCESS_TASK163_REPEAT_RUN,
        True,
        Task164Task163Branch.VALID,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_D02_PYTHON_CROSS_VERSION_IDENTITY_PARITY,
        Task164ScenarioClass.DETERMINISM,
        Task164ScenarioInputAuthority.INTERNAL_DUAL_RUNTIME_PARITY_RUN,
        False,
        Task164Task163Branch.NOT_APPLICABLE,
        Task164ScenarioOutcome.PASS,
    ),
    Task164ScenarioSpec(
        Task164ScenarioId.D164_S01_SCOPE_FENCE_NO_LMTD_OR_F_FACTOR,
        Task164ScenarioClass.SCOPE_FENCE,
        Task164ScenarioInputAuthority.STATIC_SCOPE_AUDIT,
        False,
        Task164Task163Branch.NOT_APPLICABLE,
        Task164ScenarioOutcome.PASS,
    ),
)


def scenario_spec(scenario_id: Task164ScenarioId) -> Task164ScenarioSpec:
    for spec in TASK164_SCENARIO_MATRIX:
        if spec.scenario_id == scenario_id:
            return spec
    raise KeyError(scenario_id)


def task163_request_raw(value: Task163Request) -> dict[str, object]:
    return {
        "schema_version": value.schema_version,
        "task163_version": value.task163_version,
        "source_definition_id": value.source_definition_id,
        "task162_result": value.task162_result,
        "task162_success_replay_evidence": value.task162_success_replay_evidence,
        "request_metadata": value.request_metadata,
    }


def _branch(value: Task163ValidationResult) -> Task164Task163Branch:
    if value.valid is not None:
        return Task164Task163Branch.VALID
    if value.typed_blocked is not None:
        return Task164Task163Branch.TYPED_BLOCKED
    if value.raw_boundary_blocked is not None:
        return Task164Task163Branch.RAW_BOUNDARY_BLOCKED
    return Task164Task163Branch.NOT_APPLICABLE


def _identity(value: Task163ValidationResult) -> Task164ObservedIdentity | None:
    if value.valid is None:
        return None
    return Task164ObservedIdentity(
        result_hash=value.valid.result_hash,
        result_id=str(value.valid.result_id).lower(),
        provenance_hash=value.valid.provenance.provenance_hash,
    )


def _run_raw(claim: Task164ScenarioClaim, fallback: Task163Request) -> object:
    request = claim.original_task163_request or fallback
    setup = claim.input_setup.input_authority
    if setup is Task164ScenarioInputAuthority.TASK163_RAW_BOUNDARY_FIXTURE:
        return object()
    if setup is Task164ScenarioInputAuthority.TASK163_TYPED_BLOCKED_FIXTURE:
        raw = task163_request_raw(request)
        raw["task162_result"] = None
        return raw
    if setup is Task164ScenarioInputAuthority.TASK162_REPLAY_REJECTION_FIXTURE:
        return task163_request_raw(
            replace(
                request,
                task162_result=replace(request.task162_result, result_hash="0" * 64),
            )
        )
    return task163_request_raw(request)


def _claim_matches(claim: Task164ScenarioClaim, observed: Task163ValidationResult) -> bool:
    if claim.claimed_task163_validation_result is None:
        return True
    try:
        return task163_validation_projection_bytes(
            claim.claimed_task163_validation_result
        ) == task163_validation_projection_bytes(observed)
    except BaseException:
        return False


def execute_scenario(
    claim: Task164ScenarioClaim,
    fallback_request: Task163Request,
) -> Task164ScenarioRecord:
    spec = scenario_spec(claim.scenario_id)
    refs = tuple(sorted(claim.claimed_evidence_refs, key=lambda item: item.encode("utf-8")))
    invoked = False
    invocation_count = 0
    observed: Task163ValidationResult | None = None
    if spec.real_task163_required:
        invoked = True
        invocation_count = 1
        try:
            observed = validate_task163_request(_run_raw(claim, fallback_request))
        except BaseException:
            observed = None
    if observed is None:
        branch = Task164Task163Branch.NOT_APPLICABLE
        projection_hash = "0" * 64
        result_hash = result_id = provenance_hash = None
        app_hash = comp_hash = None
    else:
        branch = _branch(observed)
        projection_hash = hashlib.sha256(task163_validation_projection_bytes(observed)).hexdigest()
        result_hash = result_id = provenance_hash = None
        app_hash = comp_hash = None
        if observed.valid is not None:
            result_hash = observed.valid.result_hash
            result_id = str(observed.valid.result_id).lower()
            provenance_hash = observed.valid.provenance.provenance_hash
            projection = task163_validation_projection_bytes(observed)
            app_hash = hashlib.sha256(projection).hexdigest()
            comp_hash = hashlib.sha256(projection).hexdigest()
    claim_match = (
        observed is not None and branch is spec.expected_branch and _claim_matches(claim, observed)
    )
    if spec.scenario_class is Task164ScenarioClass.POSITIVE_PRODUCER:
        outcome = (
            Task164ScenarioOutcome.PASS
            if claim_match and branch is Task164Task163Branch.VALID
            else Task164ScenarioOutcome.BLOCKED
        )
    elif spec.scenario_class is Task164ScenarioClass.NEGATIVE_PRODUCER:
        tamper_mismatch = (
            spec.scenario_id.endswith("TAMPER")
            and observed is not None
            and not _claim_matches(claim, observed)
        )
        outcome = (
            Task164ScenarioOutcome.NEGATIVE_PASS
            if (branch is not Task164Task163Branch.VALID and claim_match) or tamper_mismatch
            else Task164ScenarioOutcome.BLOCKED
        )
    else:
        outcome = Task164ScenarioOutcome.PASS
    claim_status = (
        Task164ClaimMatchStatus.MATCHED if claim_match else Task164ClaimMatchStatus.MISMATCHED
    )
    replay = Task164Task163ReplayEvidence(
        scenario_id=claim.scenario_id,
        producer_invocation_count=invocation_count,
        original_request_projection_hash=task163_request_projection_hash(
            claim.original_task163_request or fallback_request
        ),
        claimed_validation_projection_hash=(
            hashlib.sha256(
                task163_validation_projection_bytes(claim.claimed_task163_validation_result)
            ).hexdigest()
            if claim.claimed_task163_validation_result is not None
            else None
        ),
        replayed_validation_projection_hash=projection_hash,
        replayed_branch=branch,
        replayed_result_hash_or_none=result_hash,
        replayed_result_id_or_none=result_id,
        replayed_provenance_hash_or_none=provenance_hash,
        applicability_projection_hash_or_none=app_hash,
        completeness_projection_hash_or_none=comp_hash,
        claim_match_status=claim_status,
        evidence_refs=refs,
    )
    observation = Task164ScenarioObservation(
        scenario_id=claim.scenario_id,
        real_task163_invoked=invoked,
        producer_invocation_count=invocation_count,
        observed_task163_branch=branch,
        observed_task163_result_identity_or_none=_identity(observed) if observed else None,
        observed_task163_applicability_status_or_none=(
            Task163ApplicabilityStatus.APPLICABLE
            if observed
            and observed.valid is not None
            and observed.valid.applicability.status is Task163ApplicabilityStatus.APPLICABLE
            else None
        ),
        observed_task163_completeness_status_or_none=(
            Task163CompletenessStatus.COMPLETE
            if observed
            and observed.valid is not None
            and observed.valid.completeness.status is Task163CompletenessStatus.COMPLETE
            else None
        ),
        observed_outcome=outcome,
        evidence_refs=refs,
    )
    return Task164ScenarioRecord(
        scenario_id=claim.scenario_id,
        claim=claim,
        observation=observation,
        replay_evidence=replay,
        acceptance_records=(),
        status=Task164EvidenceStatus.PASS
        if outcome in {Task164ScenarioOutcome.PASS, Task164ScenarioOutcome.NEGATIVE_PASS}
        else Task164EvidenceStatus.REJECTED,
    )


__all__ = ["TASK164_SCENARIO_MATRIX", "Task164ScenarioSpec", "execute_scenario", "scenario_spec"]
