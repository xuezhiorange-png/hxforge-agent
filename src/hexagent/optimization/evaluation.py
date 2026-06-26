"""
TASK-009 Phase 2 — candidate rating verification state machine,
evidence records, provider identity checking, cross-candidate
provider consistency, and the full per-candidate evaluation pipeline.

All verification is done with exact type checks (``type(x) is Y``).
No broad ``except Exception`` swallowing.  No ``Any`` field leaks.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.core.heat_balance import ExecutionContextSnapshot, ProviderIdentitySnapshot
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
    All required fields are non-optional; if any is missing or unreadable
    the verification path returns RUNTIME_FAILED.
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

    provider_identity: ProviderIdentitySnapshot
    tube_correlation: SelectedCorrelationSnapshot | None = None
    annulus_correlation: SelectedCorrelationSnapshot | None = None

    rating_result_hash: str
    rating_provenance_digest: str

    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome

    rating_request_identity: RatingRequestIdentity
    rating_request_identity_digest: str
    rating_execution_context: ExecutionContextSnapshot
    rating_execution_context_digest: str

    # ------------------------------------------------------------------
    # P0-7: Explicit digest from the frozen 26-field payload
    # ------------------------------------------------------------------

    def compute_explicit_evidence_digest(self) -> str:
        """Compute an explicit evidence digest from all canonical fields.

        This replaces the generic ``sha256_digest(self)`` with a
        deterministic payload that includes:
        - warning_digests / blocker_digests (individual digests)
        - failure_digest (digest of failure model_dump, or "")
        - provider / correlation identity digests
        - all scalar fields and verification outcomes
        """

        # Helper: get canonical dict for dataclasses vs Pydantic models
        def _canon(obj: object) -> dict[str, Any]:
            if isinstance(obj, BaseModel):
                return obj.model_dump()
            if dataclasses.is_dataclass(obj):
                return dataclasses.asdict(obj)  # type: ignore[arg-type]
            return {}  # fallback (should not happen for known types)

        payload = {
            "rating_status": self.rating_status.value
            if isinstance(self.rating_status, RatingStatus)
            else str(self.rating_status),
            "heat_duty_w": self.heat_duty_w,
            "hot_outlet_temperature_k": self.hot_outlet_temperature_k,
            "cold_outlet_temperature_k": self.cold_outlet_temperature_k,
            "area_inner_m2": self.area_inner_m2,
            "area_outer_m2": self.area_outer_m2,
            "UA_w_k": self.UA_w_k,
            "LMTD_k": self.LMTD_k,
            "energy_residual_w": self.energy_residual_w,
            "ua_lmtd_residual_w": self.ua_lmtd_residual_w,
            "tube_inlet_density_kg_m3": self.tube_inlet_density_kg_m3,
            "annulus_inlet_density_kg_m3": self.annulus_inlet_density_kg_m3,
            "tube_flow_area_m2": self.tube_flow_area_m2,
            "annulus_flow_area_m2": self.annulus_flow_area_m2,
            "warning_digests": tuple(sha256_digest(w) for w in self.warnings),
            "blocker_digests": tuple(sha256_digest(b) for b in self.blockers),
            "failure_digest": sha256_digest(_canon(self.failure))
            if self.failure is not None
            else "",
            "provider_identity_digest": sha256_digest(_canon(self.provider_identity)),
            "tube_correlation_digest": sha256_digest(_canon(self.tube_correlation))
            if self.tube_correlation is not None
            else "",
            "annulus_correlation_digest": sha256_digest(_canon(self.annulus_correlation))
            if self.annulus_correlation is not None
            else "",
            "rating_result_hash": self.rating_result_hash,
            "rating_provenance_digest": self.rating_provenance_digest,
            "hash_verification_outcome": self.hash_verification_outcome.value
            if isinstance(self.hash_verification_outcome, VerificationOutcome)
            else str(self.hash_verification_outcome),
            "provenance_verification_outcome": self.provenance_verification_outcome.value
            if isinstance(self.provenance_verification_outcome, VerificationOutcome)
            else str(self.provenance_verification_outcome),
            "rating_request_identity_digest": self.rating_request_identity_digest,
            "rating_execution_context_digest": self.rating_execution_context_digest,
        }
        return sha256_digest(payload)


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
        """Enforce state-field combination invariants — raise, not assert."""
        state = self.candidate_evaluation_state

        if state == CandidateEvaluationState.UNEVALUATED.value:
            if self.candidate_evaluation_identity is not None:
                raise ValueError("UNEVALUATED: candidate_evaluation_identity must be None")
            if self.verified_rating_evidence is not None:
                raise ValueError("UNEVALUATED: verified_rating_evidence must be None")
            if self.invalid_rating_evidence is not None:
                raise ValueError("UNEVALUATED: invalid_rating_evidence must be None")
            if self.evaluation_failure is not None:
                raise ValueError("UNEVALUATED: evaluation_failure must be None")

        elif state == CandidateEvaluationState.VERIFIED.value:
            if self.candidate_evaluation_identity is None:
                raise ValueError("VERIFIED: candidate_evaluation_identity required")
            if self.verified_rating_evidence is None:
                raise ValueError("VERIFIED: verified_rating_evidence required")
            if self.invalid_rating_evidence is not None:
                raise ValueError("VERIFIED: invalid_rating_evidence must be None")

        elif state == CandidateEvaluationState.INTEGRITY_INVALID.value:
            if self.candidate_evaluation_identity is not None:
                raise ValueError("INTEGRITY_INVALID: candidate_evaluation_identity must be None")
            if self.verified_rating_evidence is not None:
                raise ValueError("INTEGRITY_INVALID: verified_rating_evidence must be None")
            if self.invalid_rating_evidence is None:
                raise ValueError("INTEGRITY_INVALID: invalid_rating_evidence required")
            if self.evaluation_failure is not None:
                raise ValueError("INTEGRITY_INVALID: evaluation_failure must be None")
            if self.rating_status is not None:
                raise ValueError("INTEGRITY_INVALID: rating_status must be None")

        elif state == CandidateEvaluationState.RUNTIME_FAILED.value:
            if self.candidate_evaluation_identity is not None:
                raise ValueError("RUNTIME_FAILED: candidate_evaluation_identity must be None")
            if self.verified_rating_evidence is not None:
                raise ValueError("RUNTIME_FAILED: verified_rating_evidence must be None")
            if self.invalid_rating_evidence is not None:
                raise ValueError("RUNTIME_FAILED: invalid_rating_evidence must be None")
            if self.evaluation_failure is None:
                raise ValueError("RUNTIME_FAILED: evaluation_failure required")

        return self


# ---------------------------------------------------------------------------
# Exact-type safe extraction helpers (for audit path only)
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


# ---------------------------------------------------------------------------
# Build safe audit snapshot (only for exact RatingResult objects)
# ---------------------------------------------------------------------------

# P0-8: safely_readable_field_digests format changed.
# Each entry is (field_name, sha256_digest({"field_name": field_name,
#   "canonical_value": safe_value}))
# Identity digests use exact canonical payloads.


def _digest_safe_field(field_name: str, safe_value: str | None) -> tuple[str, str] | None:
    """Produce a (field_name, digest) entry for an audit field.

    Returns None when safe_value is None (field was not readable).
    Uses the P0-8 canonical payload format.
    """
    if safe_value is None:
        return None
    canonical_payload = {"field_name": field_name, "canonical_value": safe_value}
    return (field_name, sha256_digest(canonical_payload))


def _build_audit_snapshot(
    candidate_id: str,
    index: int,
    claim_state: str,
    hash_outcome: str,
    provenance_outcome: str,
    result: RatingResult,
) -> ClaimedRatingResultAuditSnapshot:
    """Build a safe audit snapshot — only 6 whitelisted fields.

    MUST only be called with an exact ``RatingResult``.  Each field
    is independently extracted and any error propagates (no suppression).
    Uses P0-8 canonical payloads for identity digests and
    safely_readable_field_digests format.
    """
    # Extract 6 whitelisted fields — errors propagate (fail-closed)
    status_str: str | None = None
    if type(result.status) is RatingStatus:
        status_str = result.status.value
    elif result.status is None:
        status_str = None
    else:
        status_str = str(result.status)

    result_hash_str: str | None = None
    if type(result.result_hash) is str:
        result_hash_str = result.result_hash
    elif result.result_hash is None:
        result_hash_str = None

    prov_digest: str | None = None
    if type(result.provenance_digest) is str:
        prov_digest = result.provenance_digest
    elif result.provenance_digest is None:
        prov_digest = None

    ri_digest: str | None = None
    if type(result.request_identity) is RatingRequestIdentity:
        ri_digest = sha256_digest(dataclasses.asdict(result.request_identity))

    ec_digest: str | None = None
    if (
        result.execution_context is not None
        and type(result.execution_context) is ExecutionContextSnapshot
    ):
        ec_digest = sha256_digest(result.execution_context.model_dump())

    pi_digest: str | None = None
    if type(result.provider_identity) is ProviderIdentitySnapshot:
        pi_digest = sha256_digest(dataclasses.asdict(result.provider_identity))

    # Build safely_readable_field_digests (P0-8 format)
    readable: list[tuple[str, str]] = []
    for key, val in [
        ("claimed_result_hash", result_hash_str),
        ("claimed_rating_status", status_str),
        ("claimed_provenance_digest", prov_digest),
        ("claimed_execution_context_digest", ec_digest),
        ("claimed_provider_identity_digest", pi_digest),
        ("claimed_request_identity_digest", ri_digest),
    ]:
        entry = _digest_safe_field(key, val)
        if entry is not None:
            readable.append(entry)
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
# Extract verified evidence (fail-closed) — P0-6: no suppression anywhere
# ---------------------------------------------------------------------------


def _extract_trusted_evidence(
    result: RatingResult,
    tube_in_hot: bool,
) -> VerifiedRatingEvidenceSnapshot:
    """Extract all trusted evidence fields from a verified RatingResult.

    Raises ``ValueError`` / ``TypeError`` on any required field failure.
    No broad try/except suppression — every extraction error propagates.
    Legitimate None values remain None where the frozen schema permits.
    """
    # --- Required identity types (fail-closed) ---
    pi = result.provider_identity
    if type(pi) is not ProviderIdentitySnapshot:
        raise TypeError(f"expected ProviderIdentitySnapshot, got {type(pi).__name__}")

    ri = result.request_identity
    if type(ri) is not RatingRequestIdentity:
        raise TypeError(f"expected RatingRequestIdentity, got {type(ri).__name__}")

    ec = result.execution_context
    if type(ec) is not ExecutionContextSnapshot:
        raise TypeError(f"expected ExecutionContextSnapshot, got {type(ec).__name__}")

    rs = result.status
    if type(rs) is not RatingStatus:
        raise TypeError(f"expected RatingStatus, got {type(rs).__name__}")

    # --- Digests (must be non-empty str) ---
    r_hash = result.result_hash
    if type(r_hash) is not str or not r_hash:
        raise ValueError("result_hash must be non-empty str")

    r_prov = result.provenance_digest
    if type(r_prov) is not str or not r_prov:
        raise ValueError("provenance_digest must be non-empty str")

    ri_digest = sha256_digest(dataclasses.asdict(ri))
    ec_digest = sha256_digest(ec.model_dump())

    # --- Thermal fields (fail closed for areas, optional for others) ---
    area_inner: float = 0.0
    try:
        area_inner = float(result.area_inner_m2)
    except (TypeError, ValueError, AttributeError):
        raise ValueError("area_inner_m2 required") from None

    area_outer: float = 0.0
    try:
        area_outer = float(result.area_outer_m2)
    except (TypeError, ValueError, AttributeError):
        raise ValueError("area_outer_m2 required") from None

    # Optional thermal fields — no suppression; errors propagate
    heat_duty: float | None = None
    raw_hd = result.heat_duty_w
    if raw_hd is not None:
        if not isinstance(raw_hd, (int, float)):
            raise TypeError(f"heat_duty_w must be float or None, got {type(raw_hd).__name__}")
        heat_duty = float(raw_hd)

    hot_outlet: float | None = None
    raw_ho = result.hot_outlet_temperature_k
    if raw_ho is not None:
        if not isinstance(raw_ho, (int, float)):
            raise TypeError(
                f"hot_outlet_temperature_k must be float or None, got {type(raw_ho).__name__}"
            )
        hot_outlet = float(raw_ho)

    cold_outlet: float | None = None
    raw_co = result.cold_outlet_temperature_k
    if raw_co is not None:
        if not isinstance(raw_co, (int, float)):
            raise TypeError(
                f"cold_outlet_temperature_k must be float or None, got {type(raw_co).__name__}"
            )
        cold_outlet = float(raw_co)

    ua_val: float | None = None
    raw_ua = result.UA_w_k
    if raw_ua is not None:
        if not isinstance(raw_ua, (int, float)):
            raise TypeError(f"UA_w_k must be float or None, got {type(raw_ua).__name__}")
        ua_val = float(raw_ua)

    lmtd_val: float | None = None
    raw_lmtd = result.LMTD_k
    if raw_lmtd is not None:
        if not isinstance(raw_lmtd, (int, float)):
            raise TypeError(f"LMTD_k must be float or None, got {type(raw_lmtd).__name__}")
        lmtd_val = float(raw_lmtd)

    energy_res: float | None = None
    raw_er = result.energy_residual_w
    if raw_er is not None:
        if not isinstance(raw_er, (int, float)):
            raise TypeError(f"energy_residual_w must be float or None, got {type(raw_er).__name__}")
        energy_res = float(raw_er)

    ua_lmtd_res: float | None = None
    raw_ulr = result.ua_lmtd_residual_w
    if raw_ulr is not None:
        if not isinstance(raw_ulr, (int, float)):
            raise TypeError(
                f"ua_lmtd_residual_w must be float or None, got {type(raw_ulr).__name__}"
            )
        ua_lmtd_res = float(raw_ulr)

    # --- Inlet densities (respect tube_in_hot) — errors propagate ---
    tube_density: float | None = None
    annulus_density: float | None = None
    hot_inlet = result.hot_inlet_state
    cold_inlet = result.cold_inlet_state
    hot_dens: float | None = None
    if hot_inlet is not None:
        hd = hot_inlet.density_kg_m3
        if hd is not None:
            if not isinstance(hd, (int, float)):
                raise TypeError(
                    f"hot_inlet density_kg_m3 must be float or None, got {type(hd).__name__}"
                )
            hot_dens = float(hd)
    cold_dens: float | None = None
    if cold_inlet is not None:
        cd = cold_inlet.density_kg_m3
        if cd is not None:
            if not isinstance(cd, (int, float)):
                raise TypeError(
                    f"cold_inlet density_kg_m3 must be float or None, got {type(cd).__name__}"
                )
            cold_dens = float(cd)

    if tube_in_hot:
        tube_density = hot_dens
        annulus_density = cold_dens
    else:
        tube_density = cold_dens
        annulus_density = hot_dens

    # --- Flow areas from geometry — errors propagate ---
    tube_area: float | None = None
    annulus_area: float | None = None
    geom_dict = ri.geometry
    if isinstance(geom_dict, dict):
        from math import pi as MATH_PI

        r_i: object = geom_dict.get("inner_tube_inner_diameter_m", 0)
        r_o: object = geom_dict.get("inner_tube_outer_diameter_m", 0)
        d_outer: object = geom_dict.get("outer_pipe_inner_diameter_m", 0)
        if r_i and r_o and d_outer:
            try:
                r_i_f = float(r_i)  # type: ignore[arg-type]
                r_o_f = float(r_o)  # type: ignore[arg-type]
                d_outer_f = float(d_outer)  # type: ignore[arg-type]
                tube_area = MATH_PI * (r_i_f / 2.0) ** 2
                annulus_area = MATH_PI * ((d_outer_f / 2.0) ** 2 - (r_o_f / 2.0) ** 2)
            except (TypeError, ValueError):
                raise ValueError("geometry dimensions must be convertible to float") from None

    # --- Warnings, blockers, failure — errors propagate ---
    warnings: tuple[EngineeringMessage, ...] = ()
    raw_warnings = result.warnings
    if raw_warnings is not None:
        if not isinstance(raw_warnings, (tuple, list)):
            raise TypeError(f"warnings must be a tuple, got {type(raw_warnings).__name__}")
        warnings = tuple(raw_warnings)

    blockers: tuple[EngineeringMessage, ...] = ()
    raw_blockers = result.blockers
    if raw_blockers is not None:
        if not isinstance(raw_blockers, (tuple, list)):
            raise TypeError(f"blockers must be a tuple, got {type(raw_blockers).__name__}")
        blockers = tuple(raw_blockers)

    failure: RunFailure | None = None
    failure = result.failure  # RunFailure | None — access propagates errors

    # --- Correlations — errors propagate ---
    tube_corr: SelectedCorrelationSnapshot | None = None
    raw_tc = result.tube_selected_correlation
    if raw_tc is not None and type(raw_tc) is not SelectedCorrelationSnapshot:
        raise TypeError(
            f"tube_selected_correlation must be SelectedCorrelationSnapshot or None, "
            f"got {type(raw_tc).__name__}"
        )
    tube_corr = raw_tc

    annulus_corr: SelectedCorrelationSnapshot | None = None
    raw_ac = result.annulus_selected_correlation
    if raw_ac is not None and type(raw_ac) is not SelectedCorrelationSnapshot:
        raise TypeError(
            f"annulus_selected_correlation must be SelectedCorrelationSnapshot or None, "
            f"got {type(raw_ac).__name__}"
        )
    annulus_corr = raw_ac

    # One-shot construction
    return VerifiedRatingEvidenceSnapshot(
        rating_status=rs,
        heat_duty_w=heat_duty,
        hot_outlet_temperature_k=hot_outlet,
        cold_outlet_temperature_k=cold_outlet,
        area_inner_m2=area_inner,
        area_outer_m2=area_outer,
        UA_w_k=ua_val,
        LMTD_k=lmtd_val,
        energy_residual_w=energy_res,
        ua_lmtd_residual_w=ua_lmtd_res,
        tube_inlet_density_kg_m3=tube_density,
        annulus_inlet_density_kg_m3=annulus_density,
        tube_flow_area_m2=tube_area,
        annulus_flow_area_m2=annulus_area,
        warnings=warnings,
        blockers=blockers,
        failure=failure,
        provider_identity=pi,
        tube_correlation=tube_corr,
        annulus_correlation=annulus_corr,
        rating_result_hash=r_hash,
        rating_provenance_digest=r_prov,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
        rating_request_identity=ri,
        rating_request_identity_digest=ri_digest,
        rating_execution_context=ec,
        rating_execution_context_digest=ec_digest,
    )


# ---------------------------------------------------------------------------
# Provider identity matching
# ---------------------------------------------------------------------------


def _check_provider_match(
    result: RatingResult,
    expected_provider: ExpectedProviderIdentity,
) -> bool:
    """Check provider identity from exact result.provider_identity.

    Raises ``TypeError`` if result.provider_identity is not an exact
    ``ProviderIdentitySnapshot`` (caller must handle).
    """
    pi = result.provider_identity
    if type(pi) is not ProviderIdentitySnapshot:
        raise TypeError(f"expected ProviderIdentitySnapshot, got {type(pi).__name__}")
    return expected_provider.matches(pi)


# ---------------------------------------------------------------------------
# Evaluate candidate evaluation identity (only for VERIFIED)
# ---------------------------------------------------------------------------


def _build_candidate_evaluation_identity(
    sizing_request_identity_digest: str,
    source_qualified_candidate_id: str,
    result: RatingResult,
    tube_in_hot: bool,
) -> CandidateEvaluationIdentity:
    """Build identity from trusted fields.

    Raises on type/access errors (caller handles).
    """
    ri = result.request_identity
    if type(ri) is not RatingRequestIdentity:
        raise TypeError(f"expected RatingRequestIdentity, got {type(ri).__name__}")
    ri_digest = sha256_digest(dataclasses.asdict(ri))

    pi = result.provider_identity
    if type(pi) is not ProviderIdentitySnapshot:
        raise TypeError(f"expected ProviderIdentitySnapshot, got {type(pi).__name__}")
    pi_digest = sha256_digest(dataclasses.asdict(pi))

    ec = result.execution_context
    if type(ec) is not ExecutionContextSnapshot:
        raise TypeError(f"expected ExecutionContextSnapshot, got {type(ec).__name__}")
    ec_digest = sha256_digest(ec.model_dump())

    r_hash = result.result_hash
    if type(r_hash) is not str:
        raise TypeError(f"expected str result_hash, got {type(r_hash).__name__}")

    r_prov = result.provenance_digest
    if type(r_prov) is not str:
        raise TypeError(f"expected str provenance_digest, got {type(r_prov).__name__}")

    return CandidateEvaluationIdentity(
        sizing_request_identity_digest=sizing_request_identity_digest,
        source_qualified_candidate_id=source_qualified_candidate_id,
        rating_request_identity_digest=ri_digest,
        rating_result_hash=r_hash,
        rating_provenance_digest=r_prov,
        rating_execution_context_digest=ec_digest,
        provider_identity_digest=pi_digest,
        tube_in_hot=tube_in_hot,
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

    When inconsistency is found, **all** VERIFIED candidates from the run
    are marked as provider_identity_matches=False and
    feasibility_status=provider_identity_mismatch.
    """
    if not records:
        return ()

    # Collect all distinct verified provider identities
    baseline_pi: ProviderIdentitySnapshot | None = None
    baseline_digest: str | None = None
    consistent = True

    for rec in records:
        if rec.candidate_evaluation_state != CandidateEvaluationState.VERIFIED.value:
            continue
        ev = rec.verified_rating_evidence
        if ev is None:
            continue
        pi = ev.provider_identity
        # Compute digest from canonical dump
        pi_digest = sha256_digest(dataclasses.asdict(pi))

        if baseline_pi is None:
            baseline_pi = pi
            baseline_digest = pi_digest
        elif pi_digest != baseline_digest:
            consistent = False
            break

    if baseline_pi is None:
        # No VERIFIED candidates — not applicable
        return records

    if consistent:
        # All identical
        return records

    # Inconsistent — mark ALL VERIFIED candidates as mismatched
    results: list[CandidateEvaluationRecord] = []
    for rec in records:
        if rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED.value:
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
# Build invalid evidence record (verification-failure path)
# ---------------------------------------------------------------------------


def _build_invalid_evidence(
    candidate_id: str,
    result: RatingResult,
    hash_outcome: str,
    prov_outcome: str,
    failure_reason: str,
) -> InvalidRatingEvidenceRecord:
    """Build invalid evidence from safe fields only."""
    return InvalidRatingEvidenceRecord(
        candidate_id=candidate_id,
        claimed_rating_status=_safe_str(result.status),
        claimed_result_hash=_safe_digest(result.result_hash),
        claimed_provenance_digest=_safe_digest(result.provenance_digest),
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=prov_outcome,
        rating_request_identity_digest=(
            sha256_digest(dataclasses.asdict(result.request_identity))
            if type(result.request_identity) is RatingRequestIdentity
            else None
        ),
        failure_reason=failure_reason,
    )


# ---------------------------------------------------------------------------
# Per-candidate verification state machine
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
    # Step 0: exact type check — non-exact objects NEVER enter audit
    # P0-9: Non-exact RatingResult → UNREADABLE audit snapshot
    if type(result) is not RatingResult:
        audit = ClaimedRatingResultAuditSnapshot(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            claim_state=ClaimedRatingResultState.UNREADABLE.value,
            hash_verification_outcome=VerificationOutcome.NOT_RUN.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            safely_readable_field_digests=(),
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
        invalid = _build_invalid_evidence(
            source_qualified_candidate_id,
            result,
            VerificationOutcome.FAILED.value,
            VerificationOutcome.NOT_RUN.value,
            "hash verification failed",
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
        invalid = _build_invalid_evidence(
            source_qualified_candidate_id,
            result,
            VerificationOutcome.PASSED.value,
            VerificationOutcome.FAILED.value,
            "provenance verification failed",
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

    # Step 3: Both passed — build trusted evidence (fail-closed)
    try:
        evidence = _extract_trusted_evidence(result, tube_in_hot)
    except (TypeError, ValueError, RuntimeError, AttributeError) as exc:
        audit = _build_audit_snapshot(
            source_qualified_candidate_id,
            candidate_index,
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR.value,
            VerificationOutcome.PASSED.value,
            VerificationOutcome.PASSED.value,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.PASSED.value,
            claimed_rating_result_audit=audit,
            evaluation_failure=RunFailure(
                code=ErrorCode.INVALID_STATE_TRANSITION,
                message=f"Failed to extract trusted evidence: {exc}",
            ),
        )

    # Provider matching (from exact result.provider_identity)
    try:
        provider_matches = _check_provider_match(result, expected_provider)
    except (TypeError, AttributeError):
        provider_matches = False

    # Evaluate identity (only for VERIFIED)
    try:
        eval_identity = _build_candidate_evaluation_identity(
            sizing_request_identity_digest,
            source_qualified_candidate_id,
            result,
            tube_in_hot,
        )
    except (TypeError, ValueError, RuntimeError):
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.PASSED.value,
            evaluation_failure=RunFailure(
                code=ErrorCode.INVALID_STATE_TRANSITION,
                message="Failed to build candidate evaluation identity",
            ),
        )

    # Phase 2: always not-evaluated feasibility
    feasibility_status = FeasibilityStatus.NOT_EVALUATED.value
    if not provider_matches:
        feasibility_status = FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH.value

    # Build rating_status string for the record
    rating_status_str: str | None = None
    if type(result.status) is RatingStatus:
        rating_status_str = result.status.value

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
        rating_status=rating_status_str,
    )


# ---------------------------------------------------------------------------
# P0-10: Batch evaluation with strict stop policy
# ---------------------------------------------------------------------------


def verify_and_evaluate_candidates(
    candidates: tuple[tuple[int, str, Any], ...],
    *,
    sizing_request_identity_digest: str,
    tube_in_hot: bool,
    expected_provider: ExpectedProviderIdentity,
) -> tuple[CandidateEvaluationRecord, ...]:
    """Evaluate multiple candidates with strict-stop policy.

    Each candidate is a ``(evaluation_order_index, source_qualified_candidate_id, result)``
    tuple, provided in canonical order.

    Strict-stop rules (P0-10):
    - When hash verification returns ``False`` or raises, or provenance
      returns ``False`` or raises, all later candidates are emitted as
      ``UNEVALUATED``.
    - The failing candidate is still recorded as attempted (its evaluation
      state is ``INTEGRITY_INVALID`` or ``RUNTIME_FAILED`` appropriately).
    - For non-exact ``RatingResult`` (adapter-level exception equivalent),
      the same strict-stop policy applies: that candidate is
      ``RUNTIME_FAILED`` and all later candidates are ``UNEVALUATED``.

    Returns one record per input candidate in input order.
    """
    results: list[CandidateEvaluationRecord] = []
    strict_stop = False

    for index, candidate_id, result in candidates:
        if strict_stop:
            results.append(
                CandidateEvaluationRecord(
                    source_qualified_candidate_id=candidate_id,
                    evaluation_order_index=index,
                    candidate_evaluation_state=CandidateEvaluationState.UNEVALUATED.value,
                    feasible=False,
                    hash_verification_outcome=VerificationOutcome.NOT_RUN.value,
                    provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
                )
            )
            continue

        rec = verify_and_evaluate_candidate(
            index,
            candidate_id,
            result,
            sizing_request_identity_digest=sizing_request_identity_digest,
            tube_in_hot=tube_in_hot,
            expected_provider=expected_provider,
        )

        # Activate strict stop when verification fails
        if rec.candidate_evaluation_state in (
            CandidateEvaluationState.RUNTIME_FAILED.value,
            CandidateEvaluationState.INTEGRITY_INVALID.value,
        ):
            strict_stop = True

        results.append(rec)

    return tuple(results)


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
    "verify_and_evaluate_candidates",
]
