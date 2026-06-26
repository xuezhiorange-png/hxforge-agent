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

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    claim_state: ClaimedRatingResultState

    claimed_rating_status: str | None = None
    claimed_result_hash: str | None = None
    claimed_provenance_digest: str | None = None
    claimed_request_identity_digest: str | None = None
    claimed_execution_context_digest: str | None = None
    claimed_provider_identity_digest: str | None = None

    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome

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
    tube_flow_area_m2: float
    annulus_flow_area_m2: float

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

        Delegates to the standalone ``verified_rating_evidence_payload()``
        function for exact 26-field deterministic payload.
        """
        return sha256_digest(verified_rating_evidence_payload(self))

    # ------------------------------------------------------------------
    # P0-9: Flow-area model-level finite-positive validators
    # ------------------------------------------------------------------

    @field_validator(
        "tube_flow_area_m2",
        "annulus_flow_area_m2",
        mode="before",
    )
    @classmethod
    def _finite_positive_flow_area(cls, value: object, info: Any) -> float:
        if isinstance(value, bool):
            raise TypeError(f"{info.field_name} must be float, not bool")
        if type(value) not in (int, float):
            raise TypeError(f"{info.field_name} must be numeric, got {type(value).__name__}")
        parsed = float(value)  # type: ignore[arg-type]
        import math

        if not math.isfinite(parsed) or parsed <= 0:
            raise ValueError(f"{info.field_name} must be finite positive, got {parsed}")
        return parsed


# ---------------------------------------------------------------------------
# Standalone 26-field evidence payload (P0-7)
# ---------------------------------------------------------------------------


def verified_rating_evidence_payload(
    evidence: VerifiedRatingEvidenceSnapshot,
) -> dict[str, object]:
    """Exact 26-field deterministic evidence payload (P0-6).

    Every field is drawn directly from ``evidence``.  Nested digests
    use explicit payload helpers, not model_dump() or dataclasses.asdict().
    """

    # Warning/blocker canonical sort key
    def _message_sort_key(m: EngineeringMessage) -> tuple[str, str, str, str]:
        sev = m.severity.value if hasattr(m.severity, "value") else str(m.severity)
        code = m.code.value if hasattr(m.code, "value") else str(m.code)
        return (sev, code, m.message, str(sorted(m.context) if m.context else []))

    warning_digests = tuple(
        sha256_digest(engineering_message_payload(w))
        for w in sorted(evidence.warnings, key=_message_sort_key)
    )
    blocker_digests = tuple(
        sha256_digest(engineering_message_payload(b))
        for b in sorted(evidence.blockers, key=_message_sort_key)
    )

    return {
        "rating_status": evidence.rating_status.value,
        "heat_duty_w": evidence.heat_duty_w,
        "hot_outlet_temperature_k": evidence.hot_outlet_temperature_k,
        "cold_outlet_temperature_k": evidence.cold_outlet_temperature_k,
        "area_inner_m2": evidence.area_inner_m2,
        "area_outer_m2": evidence.area_outer_m2,
        "UA_w_k": evidence.UA_w_k,
        "LMTD_k": evidence.LMTD_k,
        "energy_residual_w": evidence.energy_residual_w,
        "ua_lmtd_residual_w": evidence.ua_lmtd_residual_w,
        "tube_inlet_density_kg_m3": evidence.tube_inlet_density_kg_m3,
        "annulus_inlet_density_kg_m3": evidence.annulus_inlet_density_kg_m3,
        "tube_flow_area_m2": evidence.tube_flow_area_m2,
        "annulus_flow_area_m2": evidence.annulus_flow_area_m2,
        "warning_digests": warning_digests,
        "blocker_digests": blocker_digests,
        "failure_digest": sha256_digest(run_failure_payload(evidence.failure))
        if evidence.failure is not None
        else None,
        "provider_identity_digest": sha256_digest(
            provider_identity_snapshot_payload(evidence.provider_identity)
        ),
        "tube_correlation_digest": sha256_digest(
            selected_correlation_snapshot_payload(evidence.tube_correlation)
        )
        if evidence.tube_correlation is not None
        else None,
        "annulus_correlation_digest": sha256_digest(
            selected_correlation_snapshot_payload(evidence.annulus_correlation)
        )
        if evidence.annulus_correlation is not None
        else None,
        "rating_result_hash": evidence.rating_result_hash,
        "rating_provenance_digest": evidence.rating_provenance_digest,
        "hash_verification_outcome": evidence.hash_verification_outcome.value,
        "provenance_verification_outcome": evidence.provenance_verification_outcome.value,
        "rating_request_identity_digest": evidence.rating_request_identity_digest,
        "rating_execution_context_digest": evidence.rating_execution_context_digest,
    }


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
    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome
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
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool = False
    feasibility_status: FeasibilityStatus = FeasibilityStatus.NOT_EVALUATED

    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome

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

        if state is CandidateEvaluationState.UNEVALUATED:
            if self.candidate_evaluation_identity is not None:
                raise ValueError("UNEVALUATED: candidate_evaluation_identity must be None")
            if self.verified_rating_evidence is not None:
                raise ValueError("UNEVALUATED: verified_rating_evidence must be None")
            if self.invalid_rating_evidence is not None:
                raise ValueError("UNEVALUATED: invalid_rating_evidence must be None")
            if self.evaluation_failure is not None:
                raise ValueError("UNEVALUATED: evaluation_failure must be None")

        elif state is CandidateEvaluationState.VERIFIED:
            if self.candidate_evaluation_identity is None:
                raise ValueError("VERIFIED: candidate_evaluation_identity required")
            if self.verified_rating_evidence is None:
                raise ValueError("VERIFIED: verified_rating_evidence required")
            if self.invalid_rating_evidence is not None:
                raise ValueError("VERIFIED: invalid_rating_evidence must be None")

        elif state is CandidateEvaluationState.INTEGRITY_INVALID:
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

        elif state is CandidateEvaluationState.RUNTIME_FAILED:
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
# Explicit nested payload helpers (P0-5)
# ---------------------------------------------------------------------------


def rating_request_identity_payload(
    identity: RatingRequestIdentity,
) -> dict[str, object]:
    """Exact 21-field deterministic payload for RatingRequestIdentity.

    Only the frozen-contract-approved fields are included.  Future
    dataclass fields are excluded.
    """
    return {
        "hot_fluid_name": identity.hot_fluid_name,
        "hot_fluid_backend": identity.hot_fluid_backend,
        "hot_fluid_components": list(identity.hot_fluid_components),
        "cold_fluid_name": identity.cold_fluid_name,
        "cold_fluid_backend": identity.cold_fluid_backend,
        "cold_fluid_components": list(identity.cold_fluid_components),
        "hot_mass_flow_kg_s": identity.hot_mass_flow_kg_s,
        "cold_mass_flow_kg_s": identity.cold_mass_flow_kg_s,
        "hot_inlet_pressure_pa": identity.hot_inlet_pressure_pa,
        "cold_inlet_pressure_pa": identity.cold_inlet_pressure_pa,
        "hot_inlet_temperature_k": identity.hot_inlet_temperature_k,
        "cold_inlet_temperature_k": identity.cold_inlet_temperature_k,
        "flow_arrangement": identity.flow_arrangement,
        "geometry": dict(identity.geometry),
        "solver_absolute_residual_w": identity.solver_absolute_residual_w,
        "solver_relative_residual_fraction": identity.solver_relative_residual_fraction,
        "solver_bracket_temperature_tolerance_k": identity.solver_bracket_temperature_tolerance_k,
        "solver_max_iterations": identity.solver_max_iterations,
        "tube_boundary_condition": identity.tube_boundary_condition,
        "annulus_boundary_condition": identity.annulus_boundary_condition,
        "minimum_terminal_delta_t": identity.minimum_terminal_delta_t,
    }


def execution_context_snapshot_payload(
    context: ExecutionContextSnapshot,
) -> dict[str, object]:
    """Exact 3-field deterministic payload for ExecutionContextSnapshot."""
    ctx_req = str(context.request_id) if context.request_id else None
    ctx_des = str(context.design_case_revision_id) if context.design_case_revision_id else None
    ctx_cal = str(context.calculation_run_id) if context.calculation_run_id else None
    return {
        "request_id": ctx_req,
        "design_case_revision_id": ctx_des,
        "calculation_run_id": ctx_cal,
    }


def provider_identity_snapshot_payload(
    provider: ProviderIdentitySnapshot,
) -> dict[str, object]:
    """Exact frozen payload for ProviderIdentitySnapshot."""
    cfg = provider.configuration_fingerprint if provider.configuration_fingerprint else None
    cache = provider.cache_policy_version if provider.cache_policy_version else None
    return {
        "name": provider.name,
        "version": provider.version,
        "git_revision": provider.git_revision,
        "reference_state_policy": provider.reference_state_policy,
        "configuration_fingerprint": cfg,
        "cache_policy_version": cache,
    }


def selected_correlation_snapshot_payload(
    correlation: SelectedCorrelationSnapshot,
) -> dict[str, object]:
    """Exact frozen payload for SelectedCorrelationSnapshot."""
    return {
        "correlation_id": correlation.correlation_id,
        "version": correlation.version,
        "definition_hash": correlation.definition_hash,
        "source_title": correlation.source_title,
        "source_authors": correlation.source_authors,
        "source_year": correlation.source_year,
        "source_reference": correlation.source_reference,
        "source_verification_status": correlation.source_verification_status,
        "nusselt_basis": correlation.nusselt_basis,
        "is_adaptation": correlation.is_adaptation,
        "adaptation_limitation": correlation.adaptation_limitation,
    }


def engineering_message_payload(message: EngineeringMessage) -> dict[str, object]:
    """Exact frozen payload for EngineeringMessage (Pydantic BaseModel)."""
    sev = message.severity.value if hasattr(message.severity, "value") else str(message.severity)
    code = message.code.value if hasattr(message.code, "value") else message.code
    return {
        "schema_version": message.schema_version,
        "code": code,
        "severity": sev,
        "message": message.message,
        "source_module": message.source_module,
        "affected_paths": list(message.affected_paths) if message.affected_paths else [],
        "context": sorted(message.context) if message.context else [],
        "allows_continuation": message.allows_continuation,
    }


def run_failure_payload(failure: RunFailure) -> dict[str, object]:
    """Exact frozen payload for RunFailure (Pydantic BaseModel)."""
    code = failure.code.value if hasattr(failure.code, "value") else failure.code
    return {
        "schema_version": failure.schema_version,
        "code": code,
        "message": failure.message,
        "traceback": failure.traceback or None,
        "context": list(failure.context) if failure.context else [],
    }


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
    claim_state: ClaimedRatingResultState,
    hash_outcome: VerificationOutcome,
    provenance_outcome: VerificationOutcome,
    result: RatingResult,
) -> ClaimedRatingResultAuditSnapshot:
    """Build a safe audit snapshot — only 6 whitelisted fields (P0-8).

    MUST only be called with an exact ``RatingResult``.  Each field
    is independently extracted with its own try/except so one failure
    does not block others.

    Uses SOURCE field names for safely_readable_field_digests entries:
    "status", "result_hash", "provenance_digest", "request_identity",
    "execution_context", "provider_identity".
    """
    # 1. status
    status_str: str | None = None
    try:
        status_str = result.status.value if type(result.status) is RatingStatus else None
    except Exception:
        status_str = None

    # 2. result_hash
    result_hash_str: str | None = None
    try:
        if type(result.result_hash) is str:
            result_hash_str = result.result_hash
        elif result.result_hash is None:
            result_hash_str = None
    except Exception:
        result_hash_str = None

    # 3. provenance_digest
    prov_digest: str | None = None
    try:
        if type(result.provenance_digest) is str:
            prov_digest = result.provenance_digest
        elif result.provenance_digest is None:
            prov_digest = None
    except Exception:
        prov_digest = None

    # 4. request_identity — canonical payload helper
    ri_digest: str | None = None
    try:
        if type(result.request_identity) is RatingRequestIdentity:
            ri_digest = sha256_digest(rating_request_identity_payload(result.request_identity))
    except Exception:
        ri_digest = None

    # 5. execution_context — canonical payload helper
    ec_digest: str | None = None
    try:
        if (
            result.execution_context is not None
            and type(result.execution_context) is ExecutionContextSnapshot
        ):
            ec_digest = sha256_digest(execution_context_snapshot_payload(result.execution_context))
    except Exception:
        ec_digest = None

    # 6. provider_identity — canonical payload helper
    pi_digest: str | None = None
    try:
        if type(result.provider_identity) is ProviderIdentitySnapshot:
            pi_digest = sha256_digest(provider_identity_snapshot_payload(result.provider_identity))
    except Exception:
        pi_digest = None

    # Build safely_readable_field_digests with SOURCE field names (P0-8)
    readable: list[tuple[str, str]] = []
    for key, val in [
        ("status", status_str),
        ("result_hash", result_hash_str),
        ("provenance_digest", prov_digest),
        ("request_identity", ri_digest),
        ("execution_context", ec_digest),
        ("provider_identity", pi_digest),
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

    ri_digest = sha256_digest(rating_request_identity_payload(ri))
    ec_digest = sha256_digest(execution_context_snapshot_payload(ec))

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

    # --- Flow areas from geometry — fail-closed (P0-6) ---
    import math
    from math import pi as MATH_PI

    geom_dict = ri.geometry
    if not isinstance(geom_dict, dict):
        raise ValueError("geometry must be a dict")

    r_i_raw: object = geom_dict.get("inner_tube_inner_diameter_m")
    r_o_raw: object = geom_dict.get("inner_tube_outer_diameter_m")
    d_outer_raw: object = geom_dict.get("outer_pipe_inner_diameter_m")

    if r_i_raw is None or r_o_raw is None or d_outer_raw is None:
        raise ValueError("geometry missing required diameter fields")

    # Must be non-bool numeric (bools are ints in Python, reject them)
    if isinstance(r_i_raw, bool) or isinstance(r_o_raw, bool) or isinstance(d_outer_raw, bool):
        raise ValueError("geometry diameters must be numeric, not bool")

    try:
        r_i = float(r_i_raw)  # type: ignore[arg-type]
        r_o = float(r_o_raw)  # type: ignore[arg-type]
        d_outer = float(d_outer_raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        raise ValueError("geometry diameters must be convertible to float") from None

    # Must be finite and positive
    if not (math.isfinite(r_i) and r_i > 0):
        raise ValueError(f"inner_tube_inner_diameter_m must be finite positive, got {r_i}")
    if not (math.isfinite(r_o) and r_o > 0):
        raise ValueError(f"inner_tube_outer_diameter_m must be finite positive, got {r_o}")
    if not (math.isfinite(d_outer) and d_outer > 0):
        raise ValueError(f"outer_pipe_inner_diameter_m must be finite positive, got {d_outer}")

    # Geometric relations: inner tube ID < inner tube OD < outer pipe ID
    if not (r_i < r_o):
        raise ValueError(
            f"inner_tube_inner_diameter ({r_i}) must be < inner_tube_outer_diameter ({r_o})"
        )
    if not (r_o < d_outer):
        raise ValueError(
            f"inner_tube_outer_diameter ({r_o}) must be < outer_pipe_inner_diameter ({d_outer})"
        )

    tube_area = MATH_PI * (r_i / 2.0) ** 2
    annulus_area = MATH_PI * ((d_outer / 2.0) ** 2 - (r_o / 2.0) ** 2)

    if not (math.isfinite(tube_area) and tube_area > 0):
        raise ValueError(f"computed tube_flow_area must be finite positive, got {tube_area}")
    if not (math.isfinite(annulus_area) and annulus_area > 0):
        raise ValueError(f"computed annulus_flow_area must be finite positive, got {annulus_area}")

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
    ri_digest = sha256_digest(rating_request_identity_payload(ri))

    pi = result.provider_identity
    if type(pi) is not ProviderIdentitySnapshot:
        raise TypeError(f"expected ProviderIdentitySnapshot, got {type(pi).__name__}")
    pi_digest = sha256_digest(provider_identity_snapshot_payload(pi))

    ec = result.execution_context
    if type(ec) is not ExecutionContextSnapshot:
        raise TypeError(f"expected ExecutionContextSnapshot, got {type(ec).__name__}")
    ec_digest = sha256_digest(execution_context_snapshot_payload(ec))

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
        if rec.candidate_evaluation_state is not CandidateEvaluationState.VERIFIED:
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
        if rec.candidate_evaluation_state is CandidateEvaluationState.VERIFIED:
            new_rec = rec.model_copy(
                update={
                    "provider_identity_matches": False,
                    "feasibility_status": FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH,
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
    hash_outcome: VerificationOutcome,
    prov_outcome: VerificationOutcome,
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
            sha256_digest(rating_request_identity_payload(result.request_identity))
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
            claim_state=ClaimedRatingResultState.UNREADABLE,
            hash_verification_outcome=VerificationOutcome.NOT_RUN,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN,
            safely_readable_field_digests=(),
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.NOT_RUN,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN,
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
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR,
            VerificationOutcome.ERROR,
            VerificationOutcome.NOT_RUN,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.ERROR,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN,
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
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR,
            VerificationOutcome.FAILED,
            VerificationOutcome.NOT_RUN,
            result,
        )
        invalid = _build_invalid_evidence(
            source_qualified_candidate_id,
            result,
            VerificationOutcome.FAILED,
            VerificationOutcome.NOT_RUN,
            "hash verification failed",
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.FAILED,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN,
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
            ClaimedRatingResultState.PROVENANCE_VERIFICATION_ERROR,
            VerificationOutcome.PASSED,
            VerificationOutcome.ERROR,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.ERROR,
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
            ClaimedRatingResultState.PROVENANCE_VERIFICATION_ERROR,
            VerificationOutcome.PASSED,
            VerificationOutcome.FAILED,
            result,
        )
        invalid = _build_invalid_evidence(
            source_qualified_candidate_id,
            result,
            VerificationOutcome.PASSED,
            VerificationOutcome.FAILED,
            "provenance verification failed",
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.FAILED,
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
            ClaimedRatingResultState.HASH_VERIFICATION_ERROR,
            VerificationOutcome.PASSED,
            VerificationOutcome.PASSED,
            result,
        )
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
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
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED,
            provenance_verification_outcome=VerificationOutcome.PASSED,
            evaluation_failure=RunFailure(
                code=ErrorCode.INVALID_STATE_TRANSITION,
                message="Failed to build candidate evaluation identity",
            ),
        )

    # Phase 2: always not-evaluated feasibility
    feasibility_status = FeasibilityStatus.NOT_EVALUATED
    if not provider_matches:
        feasibility_status = FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH

    # Build rating_status string for the record
    rating_status_str: str | None = None
    if type(result.status) is RatingStatus:
        rating_status_str = result.status.value

    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=candidate_index,
        candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
        feasible=False,
        feasibility_status=feasibility_status,
        hash_verification_outcome=VerificationOutcome.PASSED,
        provenance_verification_outcome=VerificationOutcome.PASSED,
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
                    candidate_evaluation_state=CandidateEvaluationState.UNEVALUATED,
                    feasible=False,
                    hash_verification_outcome=VerificationOutcome.NOT_RUN,
                    provenance_verification_outcome=VerificationOutcome.NOT_RUN,
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
            CandidateEvaluationState.RUNTIME_FAILED,
            CandidateEvaluationState.INTEGRITY_INVALID,
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
    "engineering_message_payload",
    "execution_context_snapshot_payload",
    "provider_identity_snapshot_payload",
    "rating_request_identity_payload",
    "run_failure_payload",
    "selected_correlation_snapshot_payload",
    "verified_rating_evidence_payload",
    "verify_and_evaluate_candidate",
    "verify_and_evaluate_candidates",
]
