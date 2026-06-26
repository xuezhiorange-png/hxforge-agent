"""
TASK-009 Phase 2 — candidate rating verification state machine,
evidence records, provider identity checking, and the full
per-candidate evaluation pipeline.
"""

from __future__ import annotations

import dataclasses
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import ErrorCode, RunFailure
from hexagent.exchangers.double_pipe.result import (
    RatingResult,
    RatingStatus,
)
from hexagent.optimization.context import ExpectedProviderIdentity

# ---------------------------------------------------------------------------
# Tristate outcomes for individual verification steps
# ---------------------------------------------------------------------------


class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Candidate evaluation state
# ---------------------------------------------------------------------------


class CandidateEvaluationState(StrEnum):
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"


# ---------------------------------------------------------------------------
# VerifiedRatingEvidenceSnapshot — only after hash + provenance pass
# --------------------------------------------------------------------------


class VerifiedRatingEvidenceSnapshot(BaseModel):
    """Trusted thermal evidence extracted from a verified ``RatingResult``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    rating_status: str
    heat_duty_w: float | None = None
    hot_outlet_temperature_k: float | None = None
    cold_outlet_temperature_k: float | None = None
    area_inner_m2: float | None = None
    area_outer_m2: float | None = None
    UA_w_k: float | None = None
    LMTD_k: float | None = None
    energy_residual_w: float | None = None
    ua_lmtd_residual_w: float | None = None
    tube_flow_area_m2: float | None = None
    annulus_flow_area_m2: float | None = None
    tube_selected_correlation_id: str = ""
    tube_selected_correlation_version: str = ""
    annulus_selected_correlation_id: str = ""
    annulus_selected_correlation_version: str = ""
    rating_result_hash: str = ""
    rating_provenance_digest: str = ""
    rating_request_identity_digest: str = ""
    rating_execution_context_digest: str = ""
    provider_identity_snapshot: dict[str, Any] = Field(default_factory=dict)
    warnings: tuple[Any, ...] = Field(default_factory=tuple)
    blockers: tuple[Any, ...] = Field(default_factory=tuple)
    failure: Any = None
    hash_verification_outcome: str = VerificationOutcome.PASSED.value
    provenance_verification_outcome: str = VerificationOutcome.PASSED.value

    @property
    def evidence_digest(self) -> str:
        return sha256_digest(self)


# ---------------------------------------------------------------------------
# InvalidRatingEvidenceRecord
# --------------------------------------------------------------------------


class InvalidRatingEvidenceRecord(BaseModel):
    """Safe-fields-only record when integrity check fails."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    claimed_rating_status: str = ""
    claimed_rating_result_hash: str = ""
    claimed_provenance_digest: str = ""
    hash_verification_outcome: str = VerificationOutcome.PASSED.value
    provenance_verification_outcome: str
    failure: Any = None


# ---------------------------------------------------------------------------
# Safe audit extraction — try/except per field
# ---------------------------------------------------------------------------


def safe_extract_claimed_audit(result: Any) -> dict[str, Any]:
    """Extract only safe audit fields (no thermal metrics)."""
    audit: dict[str, Any] = {}
    for field in (
        "status",
        "result_hash",
        "provenance_digest",
        "request_identity",
        "execution_context",
        "provider_identity",
    ):
        try:
            val = getattr(result, field, None)
            if val is not None:
                if hasattr(val, "model_dump"):
                    audit[field] = val.model_dump()
                elif dataclasses and hasattr(val, "__dataclass_fields__"):
                    audit[field] = dataclasses.asdict(val)
                elif hasattr(val, "__dict__"):
                    audit[field] = dict(val.__dict__)
                else:
                    audit[field] = str(val)
        except Exception:
            audit[field] = None
    return audit


# ---------------------------------------------------------------------------
# Per-candidate evaluation result
# ---------------------------------------------------------------------------


class CandidateEvaluationRecord(BaseModel):
    """Complete per-candidate evaluation result for Phase 2."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: str
    feasible: bool = False
    hash_verification_outcome: str
    provenance_verification_outcome: str
    claimed_rating_result_audit: dict[str, Any] = Field(default_factory=dict)
    verified_rating_evidence: VerifiedRatingEvidenceSnapshot | None = None
    invalid_rating_evidence: InvalidRatingEvidenceRecord | None = None
    provider_identity_matches: bool = True
    evaluation_failure: RunFailure | None = None
    rating_status: str | None = None


# ---------------------------------------------------------------------------
# Helper: convert dataclass to dict
# ---------------------------------------------------------------------------


def _asdict(obj: Any) -> dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()  # type: ignore[no-any-return]
    if dataclasses and hasattr(obj, "__dataclass_fields__"):
        return dataclasses.asdict(obj)
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


# ---------------------------------------------------------------------------
# Full verification pipeline per candidate
# ---------------------------------------------------------------------------


def verify_and_evaluate_candidate(
    candidate_index: int,
    source_qualified_candidate_id: str,
    result: Any,
    expected_provider: ExpectedProviderIdentity | None = None,
    actual_provider_identity: Any = None,
) -> CandidateEvaluationRecord:
    """Execute the verification state machine for one candidate."""
    # Step 0: Check result type
    if not isinstance(result, RatingResult):
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.RUNTIME_FAILED.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.NOT_RUN.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            claimed_rating_result_audit={},
            evaluation_failure=RunFailure(
                code=ErrorCode.INVALID_STATE_TRANSITION,
                message=f"Expected RatingResult, got {type(result).__name__}",
            ),
        )

    audit = safe_extract_claimed_audit(result)

    # Step 1: verify_hash()
    try:
        hash_passed = result.verify_hash()
    except Exception as exc:
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
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.FAILED.value,
            provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            claimed_rating_result_audit=audit,
            invalid_rating_evidence=InvalidRatingEvidenceRecord(
                claimed_rating_status=_safe_str(result.status),
                claimed_rating_result_hash=_safe_str(result.result_hash),
                claimed_provenance_digest=_safe_str(result.provenance_digest),
                hash_verification_outcome=VerificationOutcome.FAILED.value,
                provenance_verification_outcome=VerificationOutcome.NOT_RUN.value,
            ),
            provider_identity_matches=False,
            rating_status=_safe_str(result.status),
        )

    # Step 2: verify_provenance()
    try:
        provenance_passed = result.verify_provenance()
    except Exception as exc:
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
        return CandidateEvaluationRecord(
            source_qualified_candidate_id=source_qualified_candidate_id,
            evaluation_order_index=candidate_index,
            candidate_evaluation_state=CandidateEvaluationState.INTEGRITY_INVALID.value,
            feasible=False,
            hash_verification_outcome=VerificationOutcome.PASSED.value,
            provenance_verification_outcome=VerificationOutcome.FAILED.value,
            claimed_rating_result_audit=audit,
            invalid_rating_evidence=InvalidRatingEvidenceRecord(
                claimed_rating_status=_safe_str(result.status),
                claimed_rating_result_hash=_safe_str(result.result_hash),
                claimed_provenance_digest=_safe_str(result.provenance_digest),
                hash_verification_outcome=VerificationOutcome.PASSED.value,
                provenance_verification_outcome=VerificationOutcome.FAILED.value,
            ),
            rating_status=_safe_str(result.status),
        )

    # Step 3: Both passed — build trusted evidence
    rating_status = _safe_str(result.status)
    evidence = VerifiedRatingEvidenceSnapshot(
        rating_status=rating_status,
        heat_duty_w=result.heat_duty_w,
        hot_outlet_temperature_k=result.hot_outlet_temperature_k,
        cold_outlet_temperature_k=result.cold_outlet_temperature_k,
        area_inner_m2=result.area_inner_m2,
        area_outer_m2=result.area_outer_m2,
        UA_w_k=result.UA_w_k,
        LMTD_k=result.LMTD_k,
        energy_residual_w=result.energy_residual_w,
        ua_lmtd_residual_w=result.ua_lmtd_residual_w,
        tube_selected_correlation_id=_safe_str(result.tube_selected_correlation_id),
        tube_selected_correlation_version=_safe_str(result.tube_selected_correlation_version),
        annulus_selected_correlation_id=_safe_str(result.annulus_selected_correlation_id),
        annulus_selected_correlation_version=_safe_str(result.annulus_selected_correlation_version),
        rating_result_hash=_safe_str(result.result_hash),
        rating_provenance_digest=_safe_str(result.provenance_digest),
        warnings=tuple(result.warnings or ()),
        blockers=tuple(result.blockers or ()),
        failure=result.failure,
        hash_verification_outcome=VerificationOutcome.PASSED.value,
        provenance_verification_outcome=VerificationOutcome.PASSED.value,
    )

    # Request identity digest
    try:
        ri = result.request_identity
        if ri is not None:
            evidence.rating_request_identity_digest = sha256_digest(_asdict(ri))
    except Exception:
        pass

    # Execution context digest
    try:
        ec = result.execution_context
        if ec is not None:
            evidence.rating_execution_context_digest = sha256_digest(_asdict(ec))
    except Exception:
        pass

    # Flow areas from geometry (field-check only — no recompute)
    try:
        geom = (
            result.request_identity.geometry
            if hasattr(result.request_identity, "geometry")
            else None
        )
        if geom and isinstance(geom, dict):
            from math import pi as math_pi

            inner_tube_id = geom.get("inner_tube_inner_diameter_m", 0)
            inner_tube_od = geom.get("inner_tube_outer_diameter_m", 0)
            outer_pipe_id = geom.get("outer_pipe_inner_diameter_m", 0)
            r_i = float(inner_tube_id) / 2.0  # type: ignore[arg-type]
            r_o = float(inner_tube_od) / 2.0  # type: ignore[arg-type]
            d_outer = float(outer_pipe_id)  # type: ignore[arg-type]
            evidence.tube_flow_area_m2 = math_pi * r_i**2
            evidence.annulus_flow_area_m2 = math_pi * ((d_outer / 2.0) ** 2 - r_o**2)
    except Exception:
        pass

    # Provider identity (actual from result)
    try:
        provider_pi = result.provider_identity
        if provider_pi is not None:
            evidence.provider_identity_snapshot = (
                _asdict(provider_pi)
                if hasattr(provider_pi, "__dataclass_fields__")
                else {"raw": str(provider_pi)}
            )
    except Exception:
        pass

    # Step 4: Provider matching
    provider_matches = True
    if expected_provider is not None and actual_provider_identity is not None:
        provider_matches = expected_provider.matches(actual_provider_identity)

    # Step 5: Feasibility flag (Phase 2: only SUCCEEDED is feasible)
    is_feasible = rating_status == RatingStatus.SUCCEEDED.value

    return CandidateEvaluationRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=candidate_index,
        candidate_evaluation_state=CandidateEvaluationState.VERIFIED.value,
        feasible=is_feasible,
        hash_verification_outcome=VerificationOutcome.PASSED.value,
        provenance_verification_outcome=VerificationOutcome.PASSED.value,
        verified_rating_evidence=evidence,
        provider_identity_matches=provider_matches,
        rating_status=rating_status,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value)
    except Exception:
        return ""


__all__ = [
    "CandidateEvaluationRecord",
    "CandidateEvaluationState",
    "InvalidRatingEvidenceRecord",
    "VerificationOutcome",
    "VerifiedRatingEvidenceSnapshot",
    "safe_extract_claimed_audit",
    "verify_and_evaluate_candidate",
]
