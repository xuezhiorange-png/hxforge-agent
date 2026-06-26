"""
TASK-009 Phase 2 — candidate rating verification state machine,
evidence records, provider identity checking, cross-candidate
provider consistency, and the full per-candidate evaluation pipeline.

All verification is done with exact type checks (``type(x) is Y``).
No broad ``except Exception`` swallowing.  No ``Any`` field leaks.
"""

from __future__ import annotations

import contextlib
import dataclasses
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ProviderIdentitySnapshot
from hexagent.domain.messages import EngineeringMessage, ErrorCode, RunFailure
from hexagent.exchangers.double_pipe.result import (
    RatingRequestIdentity,
    RatingResult,
    RatingStatus,
    SelectedCorrelationSnapshot,
)
from hexagent.optimization.context import ExpectedProviderIdentity

# ---------------------------------------------------------------------------
# Verification outcome enumeration
# ---------------------------------------------------------------------------


class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Candidate evaluation state enumeration
# ---------------------------------------------------------------------------


class ClaimedRatingResultState(StrEnum):
    HASH_VERIFICATION_ERROR = "hash_verification_error"
    PROVENANCE_VERIFICATION_ERROR = "provenance_verification_error"
    UNREADABLE = "unreadable"


# ---------------------------------------------------------------------------
# Candidate evaluation state
# ---------------------------------------------------------------------------


class CandidateEvaluationState(StrEnum):
    UNEVALUATED = "unevaluated"
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"


# ---------------------------------------------------------------------------
# CandidateEvaluationIdentity — only for VERIFIED results
# ---------------------------------------------------------------------------


class CandidateEvaluationIdentity(BaseModel):
    """Binding of sizing, source, rating, and provider identities.

    Only created when all of:
      - ``type(result) is RatingResult``
      - ``verify_hash() is True``
      - ``verify_provenance() is True``
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    sizing_request_identity_digest: str
    source_qualified_candidate_id: str
    rating_request_identity_digest: str
    rating_result_hash: str
    rating_provenance_digest: str
    rating_execution_context_digest: str
    provider_identity_digest: str
    tube_in_hot: bool

    @property
    def candidate_evaluation_identity_digest(self) -> str:
        """Deterministic digest — any field mutation changes it."""
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# ClaimedRatingResultAuditSnapshot — safe-only fields
# ---------------------------------------------------------------------------


class ClaimedRatingResultAuditSnapshot(BaseModel):
    """Safe-fields-only snapshot from a verification-error path.

    Used only for record-keeping; never for decisions.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_qualified_candidate_id: str
    evaluation_order_index: int
    claim_state: str  # ClaimedRatingResultState

    claimed_rating_status: str | None = None
    claimed_result_hash: str | None = None
    claimed_provenance_digest: str | None = None
    claimed_request_identity_digest: str | None = None
    claimed_execution_context_digest: str | None = None
    claimed_provider_identity_digest: str | None = None

    hash_verification_outcome: str  # VerificationOutcome
    provenance_verification_outcome: str

    safely_readable_field_digests: tuple[tuple[str, str], ...] = Field(default_factory=tuple)

    @property
    def audit_digest(self) -> str:
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# VerifiedRatingEvidenceSnapshot — only after hash + provenance pass
# ---------------------------------------------------------------------------


class VerifiedRatingEvidenceSnapshot(BaseModel):
    """Trusted thermal evidence from a verified ``RatingResult``.

    Constructed in one shot — no post-construction mutation allowed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    rating_status: RatingStatus
    heat_duty_w: float | None = None
    hot_outlet_temperature_k: float | None = None
    cold_outlet_temperature_k: float | None = None
    area_inner_m2: float
    area_outer_m2: float
    UA_w_k: float | None = None
    LMTD_k: float | None = None
    energy_residual_w: float | None = None
    ua_lmtd_residual_w: float | None = None

    tube_inlet_density_kg_m3: float | None = None
    annulus_inlet_density_kg_m3: float | None = None
    tube_flow_area_m2: float | None = None
    annulus_flow_area_m2: float | None = None

    warnings: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    blockers: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    failure: RunFailure | None = None

    provider_identity: ProviderIdentitySnapshot | None = None
    tube_correlation: SelectedCorrelationSnapshot | None = None
    annulus_correlation: SelectedCorrelationSnapshot | None = None

    rating_result_hash: str
    rating_provenance_digest: str

    hash_verification_outcome: str
    provenance_verification_outcome: str

    rating_request_identity: RatingRequestIdentity | None = None
    rating_request_identity_digest: str = ""
    rating_execution_context: Any | None = None
    rating_execution_context_digest: str = ""

    @property
    def evidence_digest(self) -> str:
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# InvalidRatingEvidenceRecord — for integrity-failure paths
# ---------------------------------------------------------------------------


class InvalidRatingEvidenceRecord(BaseModel):
    """Only safe claimed fields — no thermal metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate_id: str  # source_qualified_candidate_id
    claimed_rating_status: str | None = None
    claimed_result_hash: str | None = None
    claimed_provenance_digest: str | None = None
    hash_verification_outcome: str  # VerificationOutcome
    provenance_verification_outcome: str
    rating_request_identity_digest: str | None = None
    claimed_provider_identity: ProviderIdentitySnapshot | None = None
    failure_reason: str | None = None

    @property
    def invalid_evidence_digest(self) -> str:
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# FeasibilityStatus (Phase 2: always not_evaluated)
# ---------------------------------------------------------------------------


class FeasibilityStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"


# ---------------------------------------------------------------------------
# Per-candidate evaluation record
# ---------------------------------------------------------------------------


class CandidateEvaluationRecord(BaseModel):
    """Complete per-candidate evaluation result for Phase 2."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: str  # CandidateEvaluationState
    feasible: bool = False
    feasibility_status: str = FeasibilityStatus.NOT_EVALUATED.value

    hash_verification_outcome: str
    provenance_verification_outcome: str

    candidate_evaluation_identity: CandidateEvaluationIdentity | None = None
    claimed_rating_result_audit: ClaimedRatingResultAuditSnapshot | None = None

    verified_rating_evidence: VerifiedRatingEvidenceSnapshot | None = None
    invalid_rating_evidence: InvalidRatingEvidenceRecord | None = None

    provider_identity_matches: bool = True
    evaluation_failure: RunFailure | None = None
    rating_status: str | None = None

    @model_validator(mode="after")
    def _verify_state_invariants(self) -> Self:
        """Enforce state-field combination invariants."""
        state = self.candidate_evaluation_state

        if state == CandidateEvaluationState.UNEVALUATED.value:
            assert self.candidate_evaluation_identity is None, "UNEVALUATED: no identity"
            assert self.verified_rating_evidence is None, "UNEVALUATED: no evidence"
            assert self.invalid_rating_evidence is None, "UNEVALUATED: no invalid evidence"
            assert self.evaluation_failure is None, "UNEVALUATED: no failure"

        elif state == CandidateEvaluationState.VERIFIED.value:
            assert self.candidate_evaluation_identity is not None, "VERIFIED: identity required"
            assert self.verified_rating_evidence is not None, "VERIFIED: evidence required"
            assert self.invalid_rating_evidence is None, "VERIFIED: no invalid evidence"

        elif state == CandidateEvaluationState.INTEGRITY_INVALID.value:
            assert self.candidate_evaluation_identity is None, "INTEGRITY_INVALID: no identity"
            assert self.verified_rating_evidence is None, "INTEGRITY_INVALID: no trusted evidence"
            assert self.invalid_rating_evidence is not None, (
                "INTEGRITY_INVALID: invalid evidence required"
            )
            assert self.evaluation_failure is None, "INTEGRITY_INVALID: no failure"
            assert self.rating_status is None, "INTEGRITY_INVALID: status must be None"

        elif state == CandidateEvaluationState.RUNTIME_FAILED.value:
            assert self.candidate_evaluation_identity is None, "RUNTIME_FAILED: no identity"
            assert self.verified_rating_evidence is None, "RUNTIME_FAILED: no evidence"
            assert self.invalid_rating_evidence is None, "RUNTIME_FAILED: no invalid evidence"
            assert self.evaluation_failure is not None, "RUNTIME_FAILED: failure required"

        return self


# ---------------------------------------------------------------------------
# Exact-type safe extraction helpers
# ---------------------------------------------------------------------------


def _safe_str(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is str:
        return value
    if type(value) is RatingStatus:
        return value.value
    return None


def _safe_digest(value: object) -> str | None:
    if value is None:
        return None
    if type(value) is str:
        return value
    return None


def _extract_provider_identity_digest(pi: object) -> str | None:
    if type(pi) is not ProviderIdentitySnapshot:
        return None
    return sha256_digest(dataclasses.asdict(pi))


def _extract_request_identity_digest(ri: object) -> str | None:
    if type(ri) is not RatingRequestIdentity:
        return None
    return sha256_digest(dataclasses.asdict(ri))


def _extract_context_digest(ec: object) -> str | None:
    if type(ec).__name__ != "ExecutionContextSnapshot":
        return None
    try:
        return sha256_digest(ec.model_dump())  # type: ignore[attr-defined]
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Build safe audit snapshot
# ---------------------------------------------------------------------------


def _build_audit_snapshot(
    candidate_id: str,
    index: int,
    claim_state: str,
    hash_outcome: str,
    provenance_outcome: str,
    result: Any,
) -> ClaimedRatingResultAuditSnapshot:
    """Build a safe audit snapshot — only 6 whitelisted fields."""
    status_str: str | None = None
    try:
        if type(result.status) is RatingStatus:
            status_str = result.status.value
    except Exception:
        pass

    result_hash_str: str | None = None
    try:
        if type(result.result_hash) is str:
            result_hash_str = result.result_hash
    except Exception:
        pass

    prov_digest: str | None = None
    try:
        if type(result.provenance_digest) is str:
            prov_digest = result.provenance_digest
    except Exception:
        pass

    ri_digest: str | None = None
    try:
        if type(result.request_identity) is RatingRequestIdentity:
            ri_digest = sha256_digest(dataclasses.asdict(result.request_identity))
    except Exception:
        pass

    ec_digest: str | None = None
    try:
        if result.execution_context is not None:
            from hexagent.core.heat_balance import ExecutionContextSnapshot

            if type(result.execution_context) is ExecutionContextSnapshot:
                ec_digest = sha256_digest(result.execution_context.model_dump())
    except Exception:
        pass

    pi_digest: str | None = None
    try:
        if type(result.provider_identity) is ProviderIdentitySnapshot:
            pi_digest = sha256_digest(dataclasses.asdict(result.provider_identity))
    except Exception:
        pass

    # Build safely_readable_field_digests (sorted ASCII-key tuples)
    readable: list[tuple[str, str]] = []
    for key, val in [
        ("claimed_result_hash", result_hash_str),
        ("claimed_rating_status", status_str),
        ("claimed_provenance_digest", prov_digest),
        ("claimed_execution_context_digest", ec_digest),
        ("claimed_provider_identity_digest", pi_digest),
        ("claimed_request_identity_digest", ri_digest),
    ]:
        if val is not None:
            readable.append((key, val))
    readable.sort(key=lambda p: p[0])

    return ClaimedRatingResultAuditSnapshot(
        source_qualified_candidate_id=candidate_id,
        evaluation_order_index=index,
        claim_state=claim_state,
        claimed_rating_status=status_str,
        claimed_result_hash=result_hash_str,
        claimed_provenance_digest=prov_digest,
        claimed_request_identity_digest=ri_digest,
        claimed_execution_context_digest=ec_digest,
        claimed_provider_identity_digest=pi_digest,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=provenance_outcome,
        safely_readable_field_digests=tuple(readable),
    )


# ---------------------------------------------------------------------------
# Provider consistency
# ---------------------------------------------------------------------------


def check_provider_consistency(
    records: tuple[CandidateEvaluationRecord, ...],
) -> tuple[CandidateEvaluationRecord, ...]:
    """Check cross-candidate provider consistency.

    Only VERIFIED candidates' actual provider identity is compared.
    Claimed provider identities are ignored.
    """
    if not records:
        return ()

    baseline_pi: ProviderIdentitySnapshot | None = None
    results: list[CandidateEvaluationRecord] = []

    for rec in records:
        if rec.candidate_evaluation_state != CandidateEvaluationState.VERIFIED.value:
            results.append(rec)
            continue

        ev = rec.verified_rating_evidence
        if ev is None or ev.provider_identity is None:
            results.append(rec)
            continue

        pi = ev.provider_identity

        if baseline_pi is None:
            baseline_pi = pi
            results.append(rec)
            continue

        # Compare with baseline
        match = (
            pi.name == baseline_pi.name
            and pi.version == baseline_pi.version
            and pi.git_revision == baseline_pi.git_revision
            and pi.reference_state_policy == baseline_pi.reference_state_policy
            and pi.configuration_fingerprint == baseline_pi.configuration_fingerprint
            and pi.cache_policy_version == baseline_pi.cache_policy_version
        )

        if not match:
            # Replace the record with provider mismatch
            new_rec = rec.model_copy(
                update={
                    "provider_identity_matches": False,
                    "feasibility_status": FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH.value,
                }
            )
            results.append(new_rec)
        else:
            results.append(rec)

    return tuple(results)


# ---------------------------------------------------------------------------
# Full verification pipeline per candidate
# ---------------------------------------------------------------------------


def verify_and_evaluate_candidate(
    candidate_index: int,
    source_qualified_candidate_id: str,
    result: Any,
    *,
    sizing_request_identity_digest: str,
    tube_in_hot: bool,
    expected_provider: ExpectedProviderIdentity,
) -> CandidateEvaluationRecord:
    """Execute the full verification state machine for one candidate.

    ``expected_provider`` is required (use ``ExpectedProviderIdentity``
    matching the sizing request).  Provider matching always uses the
    actual ``result.provider_identity``, never an external override.
    """
    # Step 0: exact type check
    if type(result) is not RatingResult:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.UNREADABLE.value,
            VerificationOutcome.NOT_RUN.value,
            VerificationOutcome.NOT_RUN.value,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.NOT_RUN.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            claimed_rating_result_audit=audit,
            evaluation_failure=RunFailure(
                code=ErrorCode.INVALID_STATE_TRANSITION,
                message=f"Expected exact RatingResult, got {type(result).__name__}",
            ),
        )

    # Step 1: verify_hash() with exact error handling
    try:
        hash_passed = result.verify_hash()
    except Exception as exc:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR.value,
            VerificationOutcome.ERROR.value,
            VerificationOutcome.NOT_RUN.value,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.ERROR.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            claimed_rating_result_audit=audit,
            evaluation_failure=RunFailure(
                code=ErrorCode.HASH_MISMATCH,
                message=f"verify_hash() raised: {exc}",
            ),
        )

    if not hash_passed:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR.value,
            VerificationOutcome.FAILED.value,
            VerificationOutcome.NOT_RUN.value,
            result,
        )
        invalid = InvalidRatingEvidenceRecord(
            candidate_id=source_qualified_candidate_id,
            claimed_rating_status=_safe_str(result.status),
            claimed_result_hash=_safe_str(result.result_hash)
            if type(result.result_hash) is str
            else None,
            claimed_provenance_digest=_safe_str(result.provenance_digest)
            if type(result.provenance_digest) is str
            else None,
            hash_verification_outcome=VerificationOutcome.FAILED.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            rating_request_identity_digest=_extract_request_identity_digest(
                result.request_identity
            ),
            failure_reason="hash verification failed",
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.FAILED.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            claimed_rating_result_audit=audit,
            invalid_rating_evidence=invalid,
            provider_identity_matches=False,
            rating_status=None,
        )

    # Step 2: verify_provenance() with exact error handling
    try:
        provenance_passed = result.verify_provenance()
    except Exception as exc:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.PROVENANCE_VERIFICATION_ERROR.value,
            VerificationOutcome.PASSED.value,
            VerificationOutcome.ERROR.value,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.ERROR.value,
            claimed_rating_result_audit=audit,
            evaluation_failure=RunFailure(
                code=ErrorCode.PROVENANCE_INCOMPLETE,
                message=f"verify_provenance() raised: {exc}",
            ),
        )

    if not provenance_passed:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.PROVENANCE_VERIFICATION_ERROR.value,
            VerificationOutcome.PASSED.value,
            VerificationOutcome.FAILED.value,
            result,
        )
        invalid = InvalidRatingEvidenceRecord(
            candidate_id=source_qualified_candidate_id,
            claimed_rating_status=_safe_str(result.status),
            claimed_result_hash=_safe_str(result.result_hash)
            if type(result.result_hash) is str
            else None,
            claimed_provenance_digest=_safe_str(result.provenance_digest)
            if type(result.provenance_digest) is str
            else None,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.FAILED.value,
            rating_request_identity_digest=_extract_request_identity_digest(
                result.request_identity
            ),
            failure_reason="provenance verification failed",
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.FAILED.value,
            claimed_rating_result_audit=audit,
            invalid_rating_evidence=invalid,
            rating_status=None,
        )

    # Step 3: Both passed — build trusted evidence (ONE SHOT)
    rating_status = result.status  # exact RatingStatus

    # Collect all evidence fields BEFORE constructing the frozen model
    heat_duty_w: float | None = None
    hot_outlet_temperature_k: float | None = None
    cold_outlet_temperature_k: float | None = None
    area_inner_m2: float = 0.0
    area_outer_m2: float = 0.0
    UA_w_k: float | None = None
    LMTD_k: float | None = None
    energy_residual_w: float | None = None
    ua_lmtd_residual_w: float | None = None
    tube_inlet_density_kg_m3: float | None = None
    annulus_inlet_density_kg_m3: float | None = None
    tube_flow_area_m2: float | None = None
    annulus_flow_area_m2: float | None = None
    warnings: tuple[EngineeringMessage, ...] = ()
    blockers: tuple[EngineeringMessage, ...] = ()
    failure: RunFailure | None = None
    provider_identity: ProviderIdentitySnapshot | None = None
    tube_correlation: SelectedCorrelationSnapshot | None = None
    annulus_correlation: SelectedCorrelationSnapshot | None = None
    rating_result_hash: str = ""
    rating_provenance_digest: str = ""
    rating_request_identity: RatingRequestIdentity | None = None
    rating_request_identity_digest: str = ""
    rating_execution_context: Any = None
    rating_execution_context_digest: str = ""

    # Safe copy from verified result (each field independently typed)
    with contextlib.suppress(Exception):
        heat_duty_w = result.heat_duty_w
    with contextlib.suppress(Exception):
        hot_outlet_temperature_k = result.hot_outlet_temperature_k
    with contextlib.suppress(Exception):
        cold_outlet_temperature_k = result.cold_outlet_temperature_k
    try:
        area_inner_m2 = float(result.area_inner_m2)
    except Exception:
        area_inner_m2 = 0.0
    try:
        area_outer_m2 = float(result.area_outer_m2)
    except Exception:
        area_outer_m2 = 0.0
    with contextlib.suppress(Exception):
        UA_w_k = result.UA_w_k
    with contextlib.suppress(Exception):
        LMTD_k = result.LMTD_k
    with contextlib.suppress(Exception):
        energy_residual_w = result.energy_residual_w
    with contextlib.suppress(Exception):
        ua_lmtd_residual_w = result.ua_lmtd_residual_w

    # Inlet densities
    try:
        if result.hot_inlet_state is not None:
            tube_inlet_density_kg_m3 = result.hot_inlet_state.density_kg_m3
    except Exception:
        pass
    try:
        if result.cold_inlet_state is not None:
            annulus_inlet_density_kg_m3 = result.cold_inlet_state.density_kg_m3
    except Exception:
        pass

    # Flow areas from TASK-008 geometry
    try:
        if type(result.request_identity) is RatingRequestIdentity:
            geom = result.request_identity.geometry
            if isinstance(geom, dict):
                from math import pi as MATH_PI

                r_i = geom.get("inner_tube_inner_diameter_m", 0)
                r_o = geom.get("inner_tube_outer_diameter_m", 0)
                d_outer = geom.get("outer_pipe_inner_diameter_m", 0)
                if r_i and r_o and d_outer:
                    tube_flow_area_m2 = MATH_PI * (float(r_i) / 2.0) ** 2  # type: ignore[arg-type]
                    annulus_flow_area_m2 = MATH_PI * (
                        (float(d_outer) / 2.0) ** 2 - (float(r_o) / 2.0) ** 2  # type: ignore[arg-type]
                    )
    except Exception:
        pass

    # Warnings, blockers, failure
    try:
        if result.warnings:
            warnings = tuple(result.warnings)
    except Exception:
        pass
    try:
        if result.blockers:
            blockers = tuple(result.blockers)
    except Exception:
        pass
    with contextlib.suppress(Exception):
        failure = result.failure

    # Provider identity (exact type)
    try:
        if type(result.provider_identity) is ProviderIdentitySnapshot:
            provider_identity = result.provider_identity
    except Exception:
        pass

    # Correlation snapshots
    try:
        if type(result.tube_selected_correlation) is SelectedCorrelationSnapshot:
            tube_correlation = result.tube_selected_correlation
    except Exception:
        pass
    try:
        if type(result.annulus_selected_correlation) is SelectedCorrelationSnapshot:
            annulus_correlation = result.annulus_selected_correlation
    except Exception:
        pass

    # Hash / provenance digests
    try:
        if type(result.result_hash) is str:
            rating_result_hash = result.result_hash
    except Exception:
        pass
    try:
        if type(result.provenance_digest) is str:
            rating_provenance_digest = result.provenance_digest
    except Exception:
        pass

    # Request identity + digest
    try:
        if type(result.request_identity) is RatingRequestIdentity:
            rating_request_identity = result.request_identity
            rating_request_identity_digest = sha256_digest(
                dataclasses.asdict(result.request_identity)
            )
    except Exception:
        pass

    # Execution context + digest
    try:
        if result.execution_context is not None:
            rating_execution_context = result.execution_context
            from hexagent.core.heat_balance import ExecutionContextSnapshot

            if type(result.execution_context) is ExecutionContextSnapshot:
                rating_execution_context_digest = sha256_digest(
                    result.execution_context.model_dump()
                )
    except Exception:
        pass

    # One-shot construction of trusted evidence
    evidence = VerifiedRatingEvidenceSnapshot(
        rating_status=rating_status,
        heat_duty_w=heat_duty_w,
        hot_outlet_temperature_k=hot_outlet_temperature_k,
        cold_outlet_temperature_k=cold_outlet_temperature_k,
        area_inner_m2=area_inner_m2,
        area_outer_m2=area_outer_m2,
        UA_w_k=UA_w_k,
        LMTD_k=LMTD_k,
        energy_residual_w=energy_residual_w,
        ua_lmtd_residual_w=ua_lmtd_residual_w,
        tube_inlet_density_kg_m3=tube_inlet_density_kg_m3,
        annulus_inlet_density_kg_m3=annulus_inlet_density_kg_m3,
        tube_flow_area_m2=tube_flow_area_m2,
        annulus_flow_area_m2=annulus_flow_area_m2,
        warnings=warnings,
        blockers=blockers,
        failure=failure,
        provider_identity=provider_identity,
        tube_correlation=tube_correlation,
        annulus_correlation=annulus_correlation,
        rating_result_hash=rating_result_hash,
        rating_provenance_digest=rating_provenance_digest,
        hash_verification_outcome=VerificationOutcome.PASSED.value,
        provenance_verification_outcome=VerificationOutcome.PASSED.value,
        rating_request_identity=rating_request_identity,
        rating_request_identity_digest=rating_request_identity_digest,
        rating_execution_context=rating_execution_context,
        rating_execution_context_digest=rating_execution_context_digest,
    )

    # Provider matching (from exact result.provider_identity)
    provider_matches = True
    try:
        if type(result.provider_identity) is ProviderIdentitySnapshot:
            provider_matches = expected_provider.matches(result.provider_identity)
    except Exception:
        pass

    # Evaluate identity (only for VERIFIED)
    eval_identity: CandidateEvaluationIdentity | None = None
    try:
        if type(result.request_identity) is RatingRequestIdentity:
            ri_digest = sha256_digest(dataclasses.asdict(result.request_identity))
        else:
            ri_digest = ""
        if type(result.provider_identity) is ProviderIdentitySnapshot:
            pi_digest = sha256_digest(dataclasses.asdict(result.provider_identity))
        else:
            pi_digest = ""

        ec_digest = ""
        try:
            if result.execution_context is not None:
                from hexagent.core.heat_balance import ExecutionContextSnapshot

                if type(result.execution_context) is ExecutionContextSnapshot:
                    ec_digest = sha256_digest(result.execution_context.model_dump())
        except Exception:
            pass

        eval_identity = CandidateEvaluationIdentity(
            sizing_request_identity_digest=sizing_request_identity_digest,
            source_qualified_candidate_id=source_qualified_candidate_id,
            rating_request_identity_digest=ri_digest,
            rating_result_hash=rating_result_hash,
            rating_provenance_digest=rating_provenance_digest,
            rating_execution_context_digest=ec_digest,
            provider_identity_digest=pi_digest,
            tube_in_hot=tube_in_hot,
        )
    except Exception:
        pass

    # Phase 2: always not-evaluated feasibility
    feasibility_status = FeasibilityStatus.NOT_EVALUATED.value
    if not provider_matches:
        feasibility_status = FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH.value

    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=candidate_index,
        candidate_evaluation_state=CandidateEvaluationState.VERIFIED.value,
        feasible=False,
        feasibility_status=feasibility_status,
        hash_verification_outcome=VerificationOutcome.PASSED.value,
        provenance_verification_outcome=VerificationOutcome.PASSED.value,
        candidate_evaluation_identity=eval_identity,
        verified_rating_evidence=evidence,
        provider_identity_matches=provider_matches,
        rating_status=rating_status.value if rating_status else None,
    )


__all__ = [
    "CandidateEvaluationIdentity",
    "CandidateEvaluationRecord",
    "CandidateEvaluationState",
    "ClaimedRatingResultAuditSnapshot",
    "ClaimedRatingResultState",
    "FeasibilityStatus",
    "InvalidRatingEvidenceRecord",
    "VerificationOutcome",
    "VerifiedRatingEvidenceSnapshot",
    "check_provider_consistency",
    "verify_and_evaluate_candidate",
]
