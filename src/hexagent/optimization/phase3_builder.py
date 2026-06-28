"""
TASK-009 Phase 3 — Builder: builder helpers, classifier, ranked candidate records,
OptimizationResult, and the main build_optimization_result function.

Sections 16-19 of the Phase 3 design contract.
"""

from __future__ import annotations

import dataclasses
import re
import typing
import uuid
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import (
    EngineeringMessage,
    EngineeringMessageSeverity,
    ErrorCode,
    RunFailure,
)
from hexagent.domain.provenance import ProvenanceGraph
from hexagent.exchangers.double_pipe.result import RatingStatus
from hexagent.optimization.context import OptimizationObjective
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    _build_message_descriptor,
    _build_run_failure_descriptor,
    provider_identity_snapshot_payload,
    rating_request_identity_payload,
)
from hexagent.optimization.identities import ManufacturableCandidate
from hexagent.optimization.models import SizingRequest
from hexagent.optimization.phase3_core import (
    FailureOrigin,
    FeasibilityDiagnosticKey,
    Phase2SourceRecordDescriptor,
    Phase2SourceRecordIdentitySnapshot,
    Phase2SourceRecordSnapshot,
    Phase3Disposition,
    Phase3MessageDescriptor,
    Phase3MessageDescriptorBinding,
    Phase3PreparationFailureStage,
    Phase3RunFailureDescriptorBinding,
    TerminationStatus,
    _find_stop_index,
    build_phase3_run_failure_descriptor_binding,
    canonical_decimal_string,
    derive_termination_status,
    to_canonical_decimal,
    verify_canonical_decimal_string,
)
from hexagent.optimization.phase3_evaluation import (
    CandidateDispositionRecord,
    Phase3CandidateClassificationInput,
    Phase3CandidatePreparationResult,
    Phase3EvaluationInput,
    Phase3SourceRecordBinding,
    build_candidate_disposition_record,
    verify_phase3_index_artifact_matrix,
)
from hexagent.optimization.phase3_verifier import (
    Phase3AuthoritativeArtifacts,
    build_phase3_provenance_graph,
    build_result_message_digest_tuples,
    verify_phase3_result_semantics_or_raise,
)

# ── Shorthand aliases for enum members used verbatim in contract code ──────

# CandidateEvaluationState
VERIFIED = CandidateEvaluationState.VERIFIED
INTEGRITY_INVALID = CandidateEvaluationState.INTEGRITY_INVALID
RUNTIME_FAILED_CS = (
    CandidateEvaluationState.RUNTIME_FAILED
)  # "runtime_failed" from CandidateEvaluationState
UNEVALUATED_CS = CandidateEvaluationState.UNEVALUATED

# VerificationOutcome
PASSED = VerificationOutcome.PASSED
FAILED = VerificationOutcome.FAILED

# Phase3Disposition (re-assign for contract code that uses bare names)
FEASIBLE = Phase3Disposition.FEASIBLE
INFEASIBLE = Phase3Disposition.INFEASIBLE
PROVIDER_IDENTITY_MISMATCH = Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
INTEGRITY_FAILED = Phase3Disposition.INTEGRITY_FAILED
PROVENANCE_FAILED = Phase3Disposition.PROVENANCE_FAILED
RUNTIME_FAILED = Phase3Disposition.RUNTIME_FAILED
UNEVALUATED = Phase3Disposition.UNEVALUATED

# FeasibilityDiagnosticKey (used in contract code as bare names)
# NOTE: INTEGRITY_FAILED and PROVENANCE_FAILED share string values between
# Phase3Disposition and FeasibilityDiagnosticKey.
NONE = FeasibilityDiagnosticKey.NONE
_INTEGRITY_FAILED_DIAG = FeasibilityDiagnosticKey.INTEGRITY_FAILED
_PROVENANCE_FAILED_DIAG = FeasibilityDiagnosticKey.PROVENANCE_FAILED
PROVIDER_IDENTITY_MISMATCH_DIAG = FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH
RATING_BLOCKED = FeasibilityDiagnosticKey.RATING_BLOCKED
RATING_FAILED = FeasibilityDiagnosticKey.RATING_FAILED
DUTY_SHORTFALL = FeasibilityDiagnosticKey.DUTY_SHORTFALL
TERMINAL_DELTA_T_INADEQUATE = FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE
# INTEGRITY_FAILED and PROVENANCE_FAILED already defined above as Phase3Disposition
PHASE2_RUNTIME_FAILED = FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED
PHASE3_RUNTIME_FAILED = FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

# FailureOrigin
NONE_ORIGIN = FailureOrigin.NONE
PHASE2_EVALUATION = FailureOrigin.PHASE2_EVALUATION
PHASE3_CLASSIFICATION = FailureOrigin.PHASE3_CLASSIFICATION

# OptimizationObjective
MINIMUM_OUTER_HEAT_TRANSFER_AREA = OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA
MINIMUM_EFFECTIVE_LENGTH = OptimizationObjective.MINIMUM_EFFECTIVE_LENGTH

# Phase 3 error codes mapped to existing production ErrorCodes
PHASE3_MISSING_RATING_STATUS = ErrorCode.INPUT_INCONSISTENT
PHASE3_TRUSTED_EVIDENCE_INCOMPLETE = ErrorCode.INPUT_INCONSISTENT
PHASE3_MISSING_CLASSIFICATION_AUTHORITY = ErrorCode.INPUT_INCONSISTENT

# Phase 3 result namespace UUID
PHASE3_RESULT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

# ── Forward stubs for functions defined in later contract sections ─────────
# These will be replaced by actual imports once sections 20-22 are implemented.


def validate_blocked_evidence(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot | None,
    eb: Phase3SourceRecordBinding,
    *,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    warning_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> RunFailure | None:
    """Validate blocked evidence consistency with ALL independent authority artifacts.

    Returns RunFailure if any inconsistency is found, None if valid.

    Contract checks:
    1. evidence present, rating_status == BLOCKED; rec.rating_status == "blocked"
    2. candidate ID, evaluation index match source_record
    3. rating request identity matches candidate evaluation identity (recompute payload)
    4. provider identity matches rec.provider_identity_matches (recompute payload)
    5. hash/provenance outcomes both PASSED
    6. failure is None
    7. Thermal field matrix check (centralized)
    8. Warning/blocker descriptors match evidence messages (count/content/order via digest)
    9. Warning/blocker descriptor bindings match SourceRecordBinding digests
    10. evidence digest matches SourceRecordBinding.verified_rating_evidence_digest
    11. evidence_failure_binding is None for blocked
    """
    ctx = (("source_qualified_candidate_id", rec.source_qualified_candidate_id),)

    # 1) Evidence must be present with BLOCKED status
    if evidence is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence missing: expected VerifiedRatingEvidenceSnapshot",
            context=ctx,
        )
    if evidence.rating_status != RatingStatus.BLOCKED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence rating_status mismatch: "
                f"expected 'blocked', got '{evidence.rating_status.value}'"
            ),
            context=ctx,
        )
    if rec.rating_status != "blocked":
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: rec.rating_status mismatch: "
                f"expected 'blocked', got {rec.rating_status!r}"
            ),
            context=ctx,
        )

    # 2) Candidate ID and evaluation index match
    if eb.source_qualified_candidate_id != rec.source_qualified_candidate_id:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: candidate ID mismatch: "
                f"binding={eb.source_qualified_candidate_id!r} "
                f"vs record={rec.source_qualified_candidate_id!r}"
            ),
            context=ctx,
        )
    if eb.evaluation_order_index != rec.evaluation_order_index:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: evaluation index mismatch: "
                f"binding={eb.evaluation_order_index} vs record={rec.evaluation_order_index}"
            ),
            context=ctx,
        )

    # 3) Rating request identity digest — recompute from evidence payload and verify
    #    matches BOTH evidence.rating_request_identity_digest AND
    #    rec.candidate_evaluation_identity.rating_request_identity_digest
    if rec.candidate_evaluation_identity is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence: candidate_evaluation_identity is None",
            context=ctx,
        )
    recomputed_rri_digest = sha256_digest(
        rating_request_identity_payload(evidence.rating_request_identity)
    )
    if evidence.rating_request_identity_digest != recomputed_rri_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Blocked evidence: rating_request_identity_digest mismatch vs recomputed payload"
            ),
            context=ctx,
        )
    if rec.candidate_evaluation_identity.rating_request_identity_digest != recomputed_rri_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Blocked evidence: candidate_evaluation_identity.rating_request_identity_digest "
                "mismatch vs recomputed payload"
            ),
            context=ctx,
        )

    # 4) Provider identity — recompute from evidence payload and verify matches
    #    rec.candidate_evaluation_identity.provider_identity_digest.
    #    If provider_identity_matches==True but recomputed digest differs, FAIL CLOSED.
    recomputed_provider_digest = sha256_digest(
        provider_identity_snapshot_payload(evidence.provider_identity)
    )
    if rec.candidate_evaluation_identity.provider_identity_digest != recomputed_provider_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Blocked evidence: candidate_evaluation_identity.provider_identity_digest "
                "mismatch vs recomputed payload"
            ),
            context=ctx,
        )
    if rec.provider_identity_matches:
        # provider_identity_matches==True but recomputed digest vs CEI differs → FAIL CLOSED
        pass  # already checked above
    else:
        # provider_identity_matches==False should not reach this validator
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Blocked evidence: provider_identity_matches is False "
                "— should go to provider mismatch path"
            ),
            context=ctx,
        )

    # 5) Hash/provenance outcomes both PASSED
    if evidence.hash_verification_outcome != VerificationOutcome.PASSED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: hash_verification_outcome={evidence.hash_verification_outcome}"
            ),
            context=ctx,
        )
    if evidence.provenance_verification_outcome != VerificationOutcome.PASSED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: provenance_verification_outcome="
                f"{evidence.provenance_verification_outcome}"
            ),
            context=ctx,
        )

    # 6) Failure must be None
    if evidence.failure is not None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence must not have failure",
            context=ctx,
        )

    # 7) Thermal field matrix check (centralized P0-3)
    tf = _check_thermal_field_matrix(evidence, _BLOCKED_THERMAL_MATRIX, ctx)
    if tf is not None:
        return tf

    # 8) Warning/blocker descriptors match evidence messages (count, content, order via digest)
    if len(warning_descriptors) != len(evidence.warnings):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: warning descriptor count "
                f"{len(warning_descriptors)} != evidence warnings "
                f"{len(evidence.warnings)}"
            ),
            context=ctx,
        )
    for i, (wd, ew) in enumerate(zip(warning_descriptors, evidence.warnings, strict=False)):
        rebuilt = _build_message_descriptor(ew)
        if rebuilt.canonicalization_error is not None:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Blocked evidence: cannot canonicalize warning[{i}]",
                context=ctx,
            )
        if wd.message_payload_digest != rebuilt.message_payload_digest:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Blocked evidence: warning[{i}] message_payload_digest mismatch",
                context=ctx,
            )

    if len(blocker_descriptors) != len(evidence.blockers):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Blocked evidence: blocker descriptor count "
                f"{len(blocker_descriptors)} != evidence blockers "
                f"{len(evidence.blockers)}"
            ),
            context=ctx,
        )
    for i, (bd, eb_msg) in enumerate(zip(blocker_descriptors, evidence.blockers, strict=False)):
        rebuilt = _build_message_descriptor(eb_msg)
        if rebuilt.canonicalization_error is not None:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Blocked evidence: cannot canonicalize blocker[{i}]",
                context=ctx,
            )
        if bd.message_payload_digest != rebuilt.message_payload_digest:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Blocked evidence: blocker[{i}] message_payload_digest mismatch",
                context=ctx,
            )

    # 9) Warning/blocker descriptor bindings match SourceRecordBinding digests
    if len(warning_descriptor_bindings) != len(eb.warning_descriptor_binding_digests):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence: warning binding count mismatch vs SourceRecordBinding",
            context=ctx,
        )
    for i, (wb, ed) in enumerate(
        zip(warning_descriptor_bindings, eb.warning_descriptor_binding_digests, strict=False)
    ):
        if wb.descriptor_binding_digest != ed:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=(
                    f"Blocked evidence: warning_binding[{i}] digest mismatch vs SourceRecordBinding"
                ),
                context=ctx,
            )

    if len(blocker_descriptor_bindings) != len(eb.blocker_descriptor_binding_digests):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence: blocker binding count mismatch vs SourceRecordBinding",
            context=ctx,
        )
    for i, (bb, ed) in enumerate(
        zip(blocker_descriptor_bindings, eb.blocker_descriptor_binding_digests, strict=False)
    ):
        if bb.descriptor_binding_digest != ed:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=(
                    f"Blocked evidence: blocker_binding[{i}] digest mismatch vs SourceRecordBinding"
                ),
                context=ctx,
            )

    # 10) evidence digest matches SourceRecordBinding.verified_rating_evidence_digest
    expected_evidence_digest = evidence.compute_explicit_evidence_digest()
    if eb.verified_rating_evidence_digest != expected_evidence_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence digest mismatch vs binding",
            context=ctx,
        )

    # 11) evidence_failure_binding must be None for blocked
    if evidence_failure_binding is not None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Blocked evidence: evidence_failure_binding must be None",
            context=ctx,
        )

    return None


def validate_failed_evidence(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot | None,
    eb: Phase3SourceRecordBinding,
    *,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    warning_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> RunFailure | None:
    """Validate failed evidence consistency with ALL independent authority artifacts.

    Returns RunFailure if any inconsistency is found, None if valid.

    Contract checks:
    1. evidence present, rating_status == FAILED; rec.rating_status == "failed"
    2. CandidateEvaluationIdentity is not None
    3. Rating request identity recompute — must equal BOTH evidence digest AND cei digest
    4. Provider identity recompute — must equal cei.provider_identity_digest
    5. If provider_identity_matches==True but recomputed digest differs, FAIL CLOSED
    6. If provider_identity_matches==False, provider mismatch path (fail closed)
    7. Hash/provenance outcomes both PASSED
    8. Failure is present, failure descriptor can be rebuilt from evidence.failure
    9. Failure payload digest matches
    10. evidence_failure_binding exists and matches failure descriptor
    11. Failure binding's descriptor_binding_digest, payload_digest,
        canonicalization_error_digest all match
    12. Warning/blocker checks same as blocked
    13. Thermal field matrix check (centralized)
    14. Evidence digest matches
    """
    ctx = (("source_qualified_candidate_id", rec.source_qualified_candidate_id),)

    # 1) Evidence must be present with FAILED status
    if evidence is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence missing: expected VerifiedRatingEvidenceSnapshot",
            context=ctx,
        )
    if evidence.rating_status != RatingStatus.FAILED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence rating_status mismatch: "
                f"expected 'failed', got '{evidence.rating_status.value}'"
            ),
            context=ctx,
        )
    if rec.rating_status != "failed":
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: rec.rating_status mismatch: "
                f"expected 'failed', got {rec.rating_status!r}"
            ),
            context=ctx,
        )

    # 2) CandidateEvaluationIdentity must not be None
    if rec.candidate_evaluation_identity is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: candidate_evaluation_identity is None",
            context=ctx,
        )

    # 3) Candidate ID and evaluation index match vs source_record
    if eb.source_qualified_candidate_id != rec.source_qualified_candidate_id:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: candidate ID mismatch: "
                f"binding={eb.source_qualified_candidate_id!r} "
                f"vs record={rec.source_qualified_candidate_id!r}"
            ),
            context=ctx,
        )
    if eb.evaluation_order_index != rec.evaluation_order_index:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: evaluation index mismatch: "
                f"binding={eb.evaluation_order_index} vs record={rec.evaluation_order_index}"
            ),
            context=ctx,
        )

    # 4) Rating request identity — recompute from evidence payload and verify
    #    matches BOTH evidence.rating_request_identity_digest AND
    #    rec.candidate_evaluation_identity.rating_request_identity_digest
    recomputed_rri_digest = sha256_digest(
        rating_request_identity_payload(evidence.rating_request_identity)
    )
    if evidence.rating_request_identity_digest != recomputed_rri_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: rating_request_identity_digest mismatch vs recomputed payload"
            ),
            context=ctx,
        )
    if rec.candidate_evaluation_identity.rating_request_identity_digest != recomputed_rri_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: candidate_evaluation_identity."
                "rating_request_identity_digest mismatch vs recomputed payload"
            ),
            context=ctx,
        )

    # 5) Provider identity — recompute from evidence payload and verify matches
    #    rec.candidate_evaluation_identity.provider_identity_digest.
    #    If provider_identity_matches==True but recomputed digest differs, FAIL CLOSED.
    recomputed_provider_digest = sha256_digest(
        provider_identity_snapshot_payload(evidence.provider_identity)
    )
    if rec.candidate_evaluation_identity.provider_identity_digest != recomputed_provider_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: candidate_evaluation_identity.provider_identity_digest "
                "mismatch vs recomputed payload"
            ),
            context=ctx,
        )
    # 6) If provider_identity_matches==False, provider mismatch path (fail closed)
    if not rec.provider_identity_matches:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: provider_identity_matches is False "
                "— should go to provider mismatch path"
            ),
            context=ctx,
        )

    # 7) Hash/provenance outcomes both PASSED
    if evidence.hash_verification_outcome != VerificationOutcome.PASSED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: hash_verification_outcome={evidence.hash_verification_outcome}"
            ),
            context=ctx,
        )
    if evidence.provenance_verification_outcome != VerificationOutcome.PASSED:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: provenance_verification_outcome="
                f"{evidence.provenance_verification_outcome}"
            ),
            context=ctx,
        )

    # 8) Failure must be present; failure descriptor can be rebuilt from evidence.failure
    if evidence.failure is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence must have failure payload",
            context=ctx,
        )

    # Rebuild failure descriptor from evidence.failure to verify payload digest
    failure_desc = _build_run_failure_descriptor(evidence.failure)
    if failure_desc.canonicalization_error is not None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: cannot canonicalize failure descriptor",
            context=ctx,
        )

    # 9) Failure payload digest matches
    if failure_desc.payload_digest is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: rebuilt failure descriptor has no payload_digest",
            context=ctx,
        )

    # 10) evidence_failure_binding exists and matches failure descriptor
    if evidence_failure_binding is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: evidence_failure_binding is None but evidence has failure",
            context=ctx,
        )

    # 11) failure binding's descriptor_binding_digest, payload_digest,
    #     canonicalization_error_digest all match
    if evidence_failure_binding.payload_digest != failure_desc.payload_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: evidence_failure_binding payload_digest mismatch",
            context=ctx,
        )
    if evidence_failure_binding.canonicalization_error_digest is not None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: evidence_failure_binding "
                "has canonicalization_error (expected success binding)"
            ),
            context=ctx,
        )

    # Verify descriptor_binding_digest by recomputing
    rebuilt_binding = build_phase3_run_failure_descriptor_binding(failure_desc)
    if (
        evidence_failure_binding.descriptor_binding_digest
        != rebuilt_binding.descriptor_binding_digest
    ):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: evidence_failure_binding "
                "descriptor_binding_digest mismatch vs rebuilt"
            ),
            context=ctx,
        )

    # Check evidence_failure_binding matches SourceRecordBinding
    if eb.evidence_failure_binding_digest is None:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: SourceRecordBinding.evidence_failure_binding_digest is None",
            context=ctx,
        )
    if evidence_failure_binding.descriptor_binding_digest != eb.evidence_failure_binding_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                "Failed evidence: evidence_failure_binding "
                "descriptor_binding_digest mismatch vs "
                "SourceRecordBinding"
            ),
            context=ctx,
        )

    # 12) Warning/blocker checks — same as blocked
    if len(warning_descriptors) != len(evidence.warnings):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: warning descriptor count "
                f"{len(warning_descriptors)} != evidence warnings "
                f"{len(evidence.warnings)}"
            ),
            context=ctx,
        )
    for i, (wd, ew) in enumerate(zip(warning_descriptors, evidence.warnings, strict=False)):
        rebuilt_w = _build_message_descriptor(ew)
        if rebuilt_w.canonicalization_error is not None:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Failed evidence: cannot canonicalize warning[{i}]",
                context=ctx,
            )
        if wd.message_payload_digest != rebuilt_w.message_payload_digest:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Failed evidence: warning[{i}] message_payload_digest mismatch",
                context=ctx,
            )

    if len(blocker_descriptors) != len(evidence.blockers):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message=(
                f"Failed evidence: blocker descriptor count "
                f"{len(blocker_descriptors)} != evidence blockers "
                f"{len(evidence.blockers)}"
            ),
            context=ctx,
        )
    for i, (bd, eb_msg) in enumerate(zip(blocker_descriptors, evidence.blockers, strict=False)):
        rebuilt_b = _build_message_descriptor(eb_msg)
        if rebuilt_b.canonicalization_error is not None:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Failed evidence: cannot canonicalize blocker[{i}]",
                context=ctx,
            )
        if bd.message_payload_digest != rebuilt_b.message_payload_digest:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Failed evidence: blocker[{i}] message_payload_digest mismatch",
                context=ctx,
            )

    # Warning/blocker binding digests match SourceRecordBinding
    if len(warning_descriptor_bindings) != len(eb.warning_descriptor_binding_digests):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: warning binding count mismatch vs SourceRecordBinding",
            context=ctx,
        )
    for i, (wb, ed) in enumerate(
        zip(warning_descriptor_bindings, eb.warning_descriptor_binding_digests, strict=False)
    ):
        if wb.descriptor_binding_digest != ed:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=(
                    f"Failed evidence: warning_binding[{i}] digest mismatch vs SourceRecordBinding"
                ),
                context=ctx,
            )

    if len(blocker_descriptor_bindings) != len(eb.blocker_descriptor_binding_digests):
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence: blocker binding count mismatch vs SourceRecordBinding",
            context=ctx,
        )
    for i, (bb, ed) in enumerate(
        zip(blocker_descriptor_bindings, eb.blocker_descriptor_binding_digests, strict=False)
    ):
        if bb.descriptor_binding_digest != ed:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=(
                    f"Failed evidence: blocker_binding[{i}] digest mismatch vs SourceRecordBinding"
                ),
                context=ctx,
            )

    # 13) Thermal field matrix check (centralized P0-3)
    tf = _check_thermal_field_matrix(evidence, _FAILED_THERMAL_MATRIX, ctx)
    if tf is not None:
        return tf

    # 14) Evidence digest matches
    expected_evidence_digest = evidence.compute_explicit_evidence_digest()
    if eb.verified_rating_evidence_digest != expected_evidence_digest:
        return RunFailure(
            code=ErrorCode.INPUT_INCONSISTENT,
            message="Failed evidence digest mismatch vs binding",
            context=ctx,
        )

    return None


# ═══════════════════════════════════════════════════════════════════════════
# P0-3: Centralized thermal-state field matrix for blocked/failed validators
# ═══════════════════════════════════════════════════════════════════════════


class _ThermalFieldRule(StrEnum):
    MUST_BE_NONE = "must_be_none"
    REQUIRED_AND_BOUND = "required_and_bound"


_BLOCKED_THERMAL_MATRIX: dict[str, _ThermalFieldRule] = {
    "energy_residual_w": _ThermalFieldRule.MUST_BE_NONE,
    "ua_lmtd_residual_w": _ThermalFieldRule.MUST_BE_NONE,
    "heat_duty_w": _ThermalFieldRule.MUST_BE_NONE,
    "hot_outlet_temperature_k": _ThermalFieldRule.MUST_BE_NONE,
    "cold_outlet_temperature_k": _ThermalFieldRule.MUST_BE_NONE,
    "UA_w_k": _ThermalFieldRule.MUST_BE_NONE,
    "LMTD_k": _ThermalFieldRule.MUST_BE_NONE,
    "area_inner_m2": _ThermalFieldRule.REQUIRED_AND_BOUND,
    "area_outer_m2": _ThermalFieldRule.REQUIRED_AND_BOUND,
    "tube_flow_area_m2": _ThermalFieldRule.REQUIRED_AND_BOUND,
    "annulus_flow_area_m2": _ThermalFieldRule.REQUIRED_AND_BOUND,
    "tube_inlet_density_kg_m3": _ThermalFieldRule.MUST_BE_NONE,
    "annulus_inlet_density_kg_m3": _ThermalFieldRule.MUST_BE_NONE,
    "tube_correlation": _ThermalFieldRule.MUST_BE_NONE,
    "annulus_correlation": _ThermalFieldRule.MUST_BE_NONE,
}

_FAILED_THERMAL_MATRIX: dict[str, _ThermalFieldRule] = dict(_BLOCKED_THERMAL_MATRIX)


def _check_thermal_field_matrix(
    evidence: VerifiedRatingEvidenceSnapshot,
    matrix: dict[str, _ThermalFieldRule],
    ctx: tuple[tuple[str, object], ...],
) -> RunFailure | None:
    """Validate all evidence fields against the given thermal field matrix.

    Returns RunFailure on the first violation, None if all fields pass.
    """
    field_values: dict[str, object | None] = {
        "energy_residual_w": evidence.energy_residual_w,
        "ua_lmtd_residual_w": evidence.ua_lmtd_residual_w,
        "heat_duty_w": evidence.heat_duty_w,
        "hot_outlet_temperature_k": evidence.hot_outlet_temperature_k,
        "cold_outlet_temperature_k": evidence.cold_outlet_temperature_k,
        "UA_w_k": evidence.UA_w_k,
        "LMTD_k": evidence.LMTD_k,
        "area_inner_m2": evidence.area_inner_m2,
        "area_outer_m2": evidence.area_outer_m2,
        "tube_flow_area_m2": evidence.tube_flow_area_m2,
        "annulus_flow_area_m2": evidence.annulus_flow_area_m2,
        "tube_inlet_density_kg_m3": evidence.tube_inlet_density_kg_m3,
        "annulus_inlet_density_kg_m3": evidence.annulus_inlet_density_kg_m3,
        "tube_correlation": evidence.tube_correlation,
        "annulus_correlation": evidence.annulus_correlation,
    }
    for field_name, rule in matrix.items():
        val = field_values[field_name]
        if rule is _ThermalFieldRule.MUST_BE_NONE:
            if val is not None:
                return RunFailure(
                    code=ErrorCode.INPUT_INCONSISTENT,
                    message=f"Blocked/failed evidence: {field_name} must be None",
                    context=ctx,
                )
        elif rule is _ThermalFieldRule.REQUIRED_AND_BOUND and val is None:
            return RunFailure(
                code=ErrorCode.INPUT_INCONSISTENT,
                message=f"Blocked/failed evidence: {field_name} must be present",
                context=ctx,
            )
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Section 16 — Builder helpers (P0-7)
# ═══════════════════════════════════════════════════════════════════════════

# === 16.1 _map_non_verified ===


def _map_non_verified(
    rec: CandidateEvaluationRecord,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> CandidateDispositionRecord:
    """map_non_verified: all params required — no defaults."""
    if rec.candidate_evaluation_state == INTEGRITY_INVALID:
        if rec.hash_verification_outcome == FAILED:
            diag = _INTEGRITY_FAILED_DIAG
            disp = INTEGRITY_FAILED
        else:
            diag = _PROVENANCE_FAILED_DIAG
            disp = PROVENANCE_FAILED
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=disp,
            diagnostic=diag,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None,
            verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=rec.invalid_rating_evidence.invalid_evidence_digest
            if rec.invalid_rating_evidence is not None
            else None,
            primary_engineering_value=None,
            secondary_engineering_value=None,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=NONE_ORIGIN,
        )
    elif rec.candidate_evaluation_state == RUNTIME_FAILED_CS:
        sf_payload = (
            source_failure_binding.payload_digest if source_failure_binding is not None else None
        )
        sf_binding = (
            source_failure_binding.descriptor_binding_digest
            if source_failure_binding is not None
            else None
        )
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=RUNTIME_FAILED,
            diagnostic=PHASE2_RUNTIME_FAILED,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None,
            verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None,
            secondary_engineering_value=None,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_evaluation_failure_payload_digest=sf_payload,
            source_evaluation_failure_binding_digest=sf_binding,
            phase3_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=PHASE2_EVALUATION,
        )
    elif rec.candidate_evaluation_state == UNEVALUATED_CS:
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=UNEVALUATED,
            diagnostic=NONE,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None,
            verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None,
            secondary_engineering_value=None,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_binding_digest=None,
            phase3_failure_payload_digest=None,
            failure_origin=NONE_ORIGIN,
        )
    raise ValueError(f"unexpected state: {rec.candidate_evaluation_state}")


# === 16.2 _build_provider_mismatch ===


def _build_provider_mismatch(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot | None,
    eb: Phase3SourceRecordBinding,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=PROVIDER_IDENTITY_MISMATCH,
        diagnostic=PROVIDER_IDENTITY_MISMATCH_DIAG,
        provider_identity_matches=False,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=None,
        failure_origin=NONE_ORIGIN,
    )


# === 16.3 _build_infeasible ===


def _build_infeasible(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    diagnostic: FeasibilityDiagnosticKey,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=INFEASIBLE,
        diagnostic=diagnostic,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=None,
        failure_origin=NONE_ORIGIN,
    )


# === 16.4 _build_feasible ===


def _build_feasible(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot,
    eb: Phase3SourceRecordBinding,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
) -> CandidateDispositionRecord:
    _area = evidence.area_outer_m2
    _heat = evidence.heat_duty_w
    assert _area is not None, "area_outer_m2 must be non-None for feasible"
    assert _heat is not None, "heat_duty_w must be non-None for feasible"
    area_m2 = canonical_decimal_string(to_canonical_decimal(_area))
    heat_w = canonical_decimal_string(to_canonical_decimal(_heat))
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=FEASIBLE,
        diagnostic=NONE,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=area_m2,
        secondary_engineering_value=heat_w,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=None,
        failure_origin=NONE_ORIGIN,
    )


# === 16.5 _phase3_runtime ===


def _phase3_runtime(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    code: ErrorCode,
    msg: str,
    failure_stage: Phase3PreparationFailureStage,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> CandidateDispositionRecord:
    failure = RunFailure(
        code=code,
        message=msg,
        traceback=None,
        context=(
            ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
            ("evaluation_order_index", rec.evaluation_order_index),
        ),
    )
    binding = build_phase3_run_failure_descriptor_binding(_build_run_failure_descriptor(failure))
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=RUNTIME_FAILED,
        diagnostic=PHASE3_RUNTIME_FAILED,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None,
        verified_rating_evidence_digest=(
            eb.verified_rating_evidence_digest
            if failure_stage
            in (
                Phase3PreparationFailureStage.SOURCE_BINDING,
                Phase3PreparationFailureStage.CLASSIFICATION_INPUT,
            )
            else None
        ),
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=binding.payload_digest,
        phase3_failure_binding_digest=binding.descriptor_binding_digest,
        failure_origin=PHASE3_CLASSIFICATION,
        failure_stage=failure_stage,
    )


# === 16.6 _phase3_runtime_from_validation ===


def _phase3_runtime_from_validation(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    validation_failure: RunFailure,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    failure_stage: Phase3PreparationFailureStage = Phase3PreparationFailureStage.CLASSIFICATION,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
) -> CandidateDispositionRecord:
    binding = build_phase3_run_failure_descriptor_binding(
        _build_run_failure_descriptor(validation_failure)
    )
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=RUNTIME_FAILED,
        diagnostic=PHASE3_RUNTIME_FAILED,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=binding.payload_digest,
        phase3_failure_binding_digest=binding.descriptor_binding_digest,
        failure_origin=PHASE3_CLASSIFICATION,
        failure_stage=failure_stage,
    )


# === 16.7 _build_strict_stop_warning ===


def _build_strict_stop_warning(
    ei: Phase3EvaluationInput, stop_index: int
) -> EngineeringMessage | None:
    if stop_index >= len(ei.evaluation_records):
        return None
    rec = ei.evaluation_records[stop_index]
    return EngineeringMessage(
        code=ErrorCode.CALCULATION_BLOCKED,
        severity=EngineeringMessageSeverity.WARNING,
        message=(
            f"Candidate {rec.source_qualified_candidate_id} at index {stop_index} "
            f"has state {rec.candidate_evaluation_state.value}. Strict stop."
        ),
        source_module="hexagent.optimization.feasibility",
        context=(
            ("owner_sort_key", ("phase3", "strict_stop", "phase3", "strict_stop", (), "")),
            ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
            ("evaluation_order_index", stop_index),
            ("candidate_evaluation_state", rec.candidate_evaluation_state.value),
        ),
    )


# === 16.8 _expected_ranked_values ===


def _expected_ranked_values(
    disp: CandidateDispositionRecord,
    candidate: ManufacturableCandidate,
    optimization_objective: OptimizationObjective,
) -> tuple[str, str, str, str]:
    disp_area = disp.primary_engineering_value
    cand_len = candidate.effective_length_m_canonical
    assert disp_area is not None, "primary_engineering_value must be non-None for ranked"
    if optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA:
        return (
            disp_area,
            "area_outer_m2",
            canonical_decimal_string(Decimal(cand_len)),
            "effective_length_m_canonical",
        )
    return (
        canonical_decimal_string(Decimal(cand_len)),
        "effective_length_m_canonical",
        disp_area,
        "area_outer_m2",
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 17 — Classifier (P0-7)
# ═══════════════════════════════════════════════════════════════════════════


def classify_candidate(
    input: Phase3CandidateClassificationInput,
    *,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    warning_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
    identity_snapshot: Phase2SourceRecordIdentitySnapshot | None,
    complete_snapshot: Phase2SourceRecordSnapshot | None,
    source_record_descriptor: Phase2SourceRecordDescriptor | None,
) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence
    eb = input.evidence_binding
    sid = input.source_identity_record_descriptor_digest
    scd = input.source_record_descriptor_digest
    if rec.candidate_evaluation_state != VERIFIED:
        return _map_non_verified(
            rec,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            source_failure_binding=source_failure_binding,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            evidence_failure_binding=evidence_failure_binding,
        )
    # All VERIFIED branches share the same mandatory authority replay.
    # Must fail closed if any authority artifact is missing.
    if identity_snapshot is None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_MISSING_CLASSIFICATION_AUTHORITY,
            "VERIFIED: identity_snapshot required.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if complete_snapshot is None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_MISSING_CLASSIFICATION_AUTHORITY,
            "VERIFIED: complete_snapshot required.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if source_record_descriptor is None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_MISSING_CLASSIFICATION_AUTHORITY,
            "VERIFIED: source_record_descriptor required.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    # Mandatory SourceRecordBinding authority replay — must precede
    # provider_identity_matches so tampered bindings are caught before
    # any VERIFIED branch returns.
    try:
        eb.verify_or_raise(
            source_record=rec,
            identity_snapshot=identity_snapshot,
            complete_snapshot=complete_snapshot,
            source_record_descriptor=source_record_descriptor,
            verified_evidence=evidence,
            warning_bindings=warning_descriptor_bindings,
            blocker_bindings=blocker_descriptor_bindings,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    except ValueError as exc:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            f"SourceRecordBinding authority replay failed: {exc}",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(
            rec,
            evidence,
            eb,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
        )
    if rec.rating_status is None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_MISSING_RATING_STATUS,
            "No rating status.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if rec.rating_status == "blocked":
        vf = validate_blocked_evidence(
            rec,
            evidence,
            eb,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            warning_descriptor_bindings=warning_descriptor_bindings,
            blocker_descriptor_bindings=blocker_descriptor_bindings,
            evidence_failure_binding=evidence_failure_binding,
        )
        if vf is not None:
            return _phase3_runtime_from_validation(
                rec,
                eb,
                vf,
                source_identity_record_descriptor_digest=sid,
                source_record_descriptor_digest=scd,
                warning_descriptors=warning_descriptors,
                blocker_descriptors=blocker_descriptors,
            )
        return _build_infeasible(
            rec,
            eb,
            RATING_BLOCKED,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
        )
    if rec.rating_status == "failed":
        vf = validate_failed_evidence(
            rec,
            evidence,
            eb,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            warning_descriptor_bindings=warning_descriptor_bindings,
            blocker_descriptor_bindings=blocker_descriptor_bindings,
            evidence_failure_binding=evidence_failure_binding,
        )
        if vf is not None:
            return _phase3_runtime_from_validation(
                rec,
                eb,
                vf,
                source_identity_record_descriptor_digest=sid,
                source_record_descriptor_digest=scd,
                warning_descriptors=warning_descriptors,
                blocker_descriptors=blocker_descriptors,
            )
        return _build_infeasible(
            rec,
            eb,
            RATING_FAILED,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
        )
    if evidence is None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            "No evidence.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if (
        evidence.heat_duty_w is None
        or evidence.hot_outlet_temperature_k is None
        or evidence.cold_outlet_temperature_k is None
    ):
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            "Missing thermal metrics.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if (
        evidence.area_outer_m2 is None
        or not (evidence.area_outer_m2 > 0)
        or evidence.area_inner_m2 is None
        or not (evidence.area_inner_m2 > 0)
    ):
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            "Non-positive area.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    if evidence.failure is not None:
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            "Has failure.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(
            rec,
            eb,
            PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            "Non-finite metric.",
            failure_stage=Phase3PreparationFailureStage.CLASSIFICATION,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
            source_failure_binding=source_failure_binding,
            evidence_failure_binding=evidence_failure_binding,
        )
    required = to_canonical_decimal(sizing.required_duty_w)
    duty_tol = max(
        to_canonical_decimal(sizing.duty_absolute_tolerance_w),
        to_canonical_decimal(sizing.duty_relative_tolerance) * abs(required),
    )
    if abs(heat_w - required) > duty_tol:
        return _build_infeasible(
            rec,
            eb,
            DUTY_SHORTFALL,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
        )
    fa = sizing.flow_arrangement
    if fa == "parallel":
        dt1 = hot_in - cold_in
        dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out
        dt2 = hot_out - cold_in
    if min(dt1, dt2) < to_canonical_decimal(sizing.minimum_terminal_delta_t):
        return _build_infeasible(
            rec,
            eb,
            TERMINAL_DELTA_T_INADEQUATE,
            source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd,
            warning_descriptors=warning_descriptors,
            blocker_descriptors=blocker_descriptors,
        )
    return _build_feasible(
        rec,
        evidence,
        eb,
        source_identity_record_descriptor_digest=sid,
        source_record_descriptor_digest=scd,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 18 — RankedCandidateRecord (P0-9)
# ═══════════════════════════════════════════════════════════════════════════


class RankedCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rank: int
    source_qualified_candidate_id: str
    optimization_objective: OptimizationObjective
    primary_objective_value: str
    primary_objective_field: str
    secondary_tie_break_value: str
    secondary_tie_break_field: str
    candidate_evaluation_identity_digest: str
    verified_rating_evidence_digest: str
    feasibility_digest: str
    ranked_record_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.rank < 1:
            raise ValueError("rank must be ≥ 1")
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        verify_canonical_decimal_string(self.primary_objective_value)
        verify_canonical_decimal_string(self.secondary_tie_break_value)
        if self.optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            if self.primary_objective_field != "area_outer_m2":
                raise ValueError("MIN_OA: primary must be area_outer_m2")
            if self.secondary_tie_break_field != "effective_length_m_canonical":
                raise ValueError("MIN_OA: secondary must be length")
        else:
            if self.primary_objective_field != "effective_length_m_canonical":
                raise ValueError("MIN_LEN: primary must be length")
            if self.secondary_tie_break_field != "area_outer_m2":
                raise ValueError("MIN_LEN: secondary must be area")
        for d, n in [
            (self.candidate_evaluation_identity_digest, "identity"),
            (self.verified_rating_evidence_digest, "evidence"),
            (self.feasibility_digest, "feasibility"),
            (self.ranked_record_digest, "ranked"),
        ]:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError(f"invalid {n} digest")
        expected = sha256_digest(
            ranked_candidate_payload_from_values(
                rank=self.rank,
                source_qualified_candidate_id=self.source_qualified_candidate_id,
                optimization_objective=self.optimization_objective,
                primary_objective_value=self.primary_objective_value,
                primary_objective_field=self.primary_objective_field,
                secondary_tie_break_value=self.secondary_tie_break_value,
                secondary_tie_break_field=self.secondary_tie_break_field,
                candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
                verified_rating_evidence_digest=self.verified_rating_evidence_digest,
                feasibility_digest=self.feasibility_digest,
            )
        )
        if self.ranked_record_digest != expected:
            raise ValueError("ranked_record_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        disposition: CandidateDispositionRecord,
    ) -> None:
        if disposition.disposition != FEASIBLE:
            raise ValueError("ranked record must correspond to FEASIBLE disposition")
        if self.source_qualified_candidate_id != disposition.source_qualified_candidate_id:
            raise ValueError("candidate_id vs disposition mismatch")
        if (
            self.candidate_evaluation_identity_digest
            != disposition.candidate_evaluation_identity_digest
        ):
            raise ValueError("identity_digest vs disposition mismatch")
        if self.verified_rating_evidence_digest != disposition.verified_rating_evidence_digest:
            raise ValueError("evidence_digest vs disposition mismatch")
        if self.feasibility_digest != disposition.feasibility_digest:
            raise ValueError("feasibility_digest vs disposition mismatch")
        payload = ranked_candidate_payload_from_values(
            rank=self.rank,
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            optimization_objective=self.optimization_objective,
            primary_objective_value=self.primary_objective_value,
            primary_objective_field=self.primary_objective_field,
            secondary_tie_break_value=self.secondary_tie_break_value,
            secondary_tie_break_field=self.secondary_tie_break_field,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            feasibility_digest=self.feasibility_digest,
        )
        if self.ranked_record_digest != sha256_digest(payload):
            raise ValueError("ranked_record_digest mismatch")


def ranked_payload(r: RankedCandidateRecord) -> dict[str, object]:
    return {
        "rank": r.rank,
        "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "optimization_objective": r.optimization_objective.value,
        "primary_objective_value": r.primary_objective_value,
        "primary_objective_field": r.primary_objective_field,
        "secondary_tie_break_value": r.secondary_tie_break_value,
        "secondary_tie_break_field": r.secondary_tie_break_field,
        "candidate_evaluation_identity_digest": r.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": r.verified_rating_evidence_digest,
        "feasibility_digest": r.feasibility_digest,
    }


def ranked_candidate_payload_from_values(
    *,
    rank: int,
    source_qualified_candidate_id: str,
    optimization_objective: OptimizationObjective,
    primary_objective_value: str,
    primary_objective_field: str,
    secondary_tie_break_value: str,
    secondary_tie_break_field: str,
    candidate_evaluation_identity_digest: str,
    verified_rating_evidence_digest: str,
    feasibility_digest: str,
) -> dict[str, object]:
    return {
        "rank": rank,
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "optimization_objective": optimization_objective.value,
        "primary_objective_value": primary_objective_value,
        "primary_objective_field": primary_objective_field,
        "secondary_tie_break_value": secondary_tie_break_value,
        "secondary_tie_break_field": secondary_tie_break_field,
        "candidate_evaluation_identity_digest": candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "feasibility_digest": feasibility_digest,
    }


def build_ranked_candidate_record(
    *,
    rank: int,
    source_qualified_candidate_id: str,
    optimization_objective: OptimizationObjective,
    primary_objective_value: str,
    primary_objective_field: str,
    secondary_tie_break_value: str,
    secondary_tie_break_field: str,
    candidate_evaluation_identity_digest: str,
    verified_rating_evidence_digest: str,
    feasibility_digest: str,
) -> RankedCandidateRecord:
    payload = ranked_candidate_payload_from_values(
        rank=rank,
        source_qualified_candidate_id=source_qualified_candidate_id,
        optimization_objective=optimization_objective,
        primary_objective_value=primary_objective_value,
        primary_objective_field=primary_objective_field,
        secondary_tie_break_value=secondary_tie_break_value,
        secondary_tie_break_field=secondary_tie_break_field,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        feasibility_digest=feasibility_digest,
    )
    rrd = sha256_digest(payload)
    return RankedCandidateRecord(
        rank=rank,
        source_qualified_candidate_id=source_qualified_candidate_id,
        optimization_objective=optimization_objective,
        primary_objective_value=primary_objective_value,
        primary_objective_field=primary_objective_field,
        secondary_tie_break_value=secondary_tie_break_value,
        secondary_tie_break_field=secondary_tie_break_field,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        feasibility_digest=feasibility_digest,
        ranked_record_digest=rrd,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 19 — OptimizationResult (P0-10)
# ═══════════════════════════════════════════════════════════════════════════

# === 19.0 OptimizationResultCoreValues ===


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class OptimizationResultCoreValues:
    """Frozen core values containing all result fields except envelope/provenance.

    Provenance builders receive this instead of the final OptimizationResult,
    eliminating the result/provenance dependency cycle.
    """

    schema_version: Literal[1]
    sizing_request_identity_digest: str
    passed_gate_digest: str
    candidate_set_digest: str
    evaluation_input_digest: str
    optimization_objective: OptimizationObjective
    requested_top_n: int
    total_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    provenance_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int
    phase2_verified_record_count: int
    phase2_integrity_invalid_record_count: int
    phase2_runtime_failed_record_count: int
    phase2_unevaluated_record_count: int
    runtime_failed_from_phase2_verified_count: int
    runtime_failed_from_phase2_runtime_failed_count: int
    ordered_disposition_record_digests: tuple[str, ...]
    ordered_ranked_record_digests: tuple[str, ...]
    ordered_top_n_record_digests: tuple[str, ...]
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...]
    ordered_phase3_source_binding_digests: tuple[str | None, ...]
    ordered_phase3_preparation_result_digests: tuple[str | None, ...]
    termination_status: TerminationStatus
    ordered_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate cardinality invariants — all counts must be self-consistent."""
        total = self.total_candidate_count
        if (
            self.feasible_candidate_count
            + self.infeasible_candidate_count
            + self.provider_mismatch_count
            + self.integrity_failed_count
            + self.provenance_failed_count
            + self.runtime_failed_count
            + self.unevaluated_count
            != total
        ):
            raise ValueError("CoreValues: disposition counts don't sum to total")
        if (
            self.phase2_verified_record_count
            + self.phase2_integrity_invalid_record_count
            + self.phase2_runtime_failed_record_count
            + self.phase2_unevaluated_record_count
            != total
        ):
            raise ValueError("CoreValues: Phase 2 counts don't sum to total")
        if len(self.ordered_disposition_record_digests) != total:
            raise ValueError("CoreValues: disposition digest count != total")
        if len(self.ordered_ranked_record_digests) != self.feasible_candidate_count:
            raise ValueError("CoreValues: ranked digest count != feasible")
        if len(self.ordered_top_n_record_digests) != min(
            self.requested_top_n, self.feasible_candidate_count
        ):
            raise ValueError("CoreValues: top-n digest count != min(N, F)")
        if (
            tuple(self.ordered_top_n_record_digests)
            != self.ordered_ranked_record_digests[: len(self.ordered_top_n_record_digests)]
        ):
            raise ValueError("CoreValues: top-n not prefix of ranked")
        if len(self.ordered_identity_snapshot_digests) != total:
            raise ValueError("CoreValues: identity snapshot digest count != total")
        if len(self.ordered_phase2_source_snapshot_digests) != total:
            raise ValueError("CoreValues: source snapshot digest count != total")
        if len(self.ordered_phase3_source_binding_digests) != total:
            raise ValueError("CoreValues: source binding digest count != total")
        if len(self.ordered_phase3_preparation_result_digests) != total:
            raise ValueError("CoreValues: preparation result digest count != total")

    def compute_hash(self) -> str:
        """Compute result core hash via canonical payload — no asdict() dependency."""
        return sha256_digest(
            result_core_payload_from_values(
                schema_version=self.schema_version,
                sizing_request_identity_digest=self.sizing_request_identity_digest,
                passed_gate_digest=self.passed_gate_digest,
                candidate_set_digest=self.candidate_set_digest,
                evaluation_input_digest=self.evaluation_input_digest,
                optimization_objective=self.optimization_objective,
                requested_top_n=self.requested_top_n,
                total_candidate_count=self.total_candidate_count,
                feasible_candidate_count=self.feasible_candidate_count,
                infeasible_candidate_count=self.infeasible_candidate_count,
                provider_mismatch_count=self.provider_mismatch_count,
                integrity_failed_count=self.integrity_failed_count,
                provenance_failed_count=self.provenance_failed_count,
                runtime_failed_count=self.runtime_failed_count,
                unevaluated_count=self.unevaluated_count,
                phase2_verified_record_count=self.phase2_verified_record_count,
                phase2_integrity_invalid_record_count=self.phase2_integrity_invalid_record_count,
                phase2_runtime_failed_record_count=self.phase2_runtime_failed_record_count,
                phase2_unevaluated_record_count=self.phase2_unevaluated_record_count,
                runtime_failed_from_phase2_verified_count=self.runtime_failed_from_phase2_verified_count,
                runtime_failed_from_phase2_runtime_failed_count=self.runtime_failed_from_phase2_runtime_failed_count,
                ordered_disposition_record_digests=self.ordered_disposition_record_digests,
                ordered_ranked_record_digests=self.ordered_ranked_record_digests,
                ordered_top_n_record_digests=self.ordered_top_n_record_digests,
                ordered_identity_snapshot_digests=self.ordered_identity_snapshot_digests,
                ordered_phase2_source_snapshot_digests=self.ordered_phase2_source_snapshot_digests,
                ordered_phase3_source_binding_digests=self.ordered_phase3_source_binding_digests,
                ordered_phase3_preparation_result_digests=self.ordered_phase3_preparation_result_digests,
                termination_status=self.termination_status,
                ordered_warning_digests=self.ordered_warning_digests,
                ordered_blocker_digests=self.ordered_blocker_digests,
            )
        )


# === 19.0b Core values independent derivation helper ===


def derive_optimization_result_core_values(
    *,
    evaluation_input: Phase3EvaluationInput,
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...],
) -> OptimizationResultCoreValues:
    N = evaluation_input.evaluation_record_count
    # 0) Cardinality gates — reject invalid tuples before any derivation
    if len(dispositions) != N:
        raise ValueError("core_derivation: dispositions count != N")
    if len(source_bindings) != N:
        raise ValueError("core_derivation: source_bindings count != N")
    if len(preparation_results) != N:
        raise ValueError("core_derivation: preparation_results count != N")
    # Derive Phase 2 counts from evaluation records
    recs = evaluation_input.evaluation_records
    p2_v = sum(1 for r in recs if r.candidate_evaluation_state == VERIFIED)
    p2_ii = sum(1 for r in recs if r.candidate_evaluation_state == INTEGRITY_INVALID)
    p2_rf = sum(1 for r in recs if r.candidate_evaluation_state == RUNTIME_FAILED_CS)
    p2_u = sum(1 for r in recs if r.candidate_evaluation_state == UNEVALUATED_CS)
    # Derive disposition counts
    vs = [d.disposition for d in dispositions]
    f_c = vs.count(FEASIBLE)
    if f_c != len(ranked_records):
        raise ValueError("core_derivation: ranked_records count != FEASIBLE")
    inf_c = vs.count(INFEASIBLE)
    pm_c = vs.count(PROVIDER_IDENTITY_MISMATCH)
    int_c = vs.count(INTEGRITY_FAILED)
    pf_c = vs.count(PROVENANCE_FAILED)
    rf_c = vs.count(RUNTIME_FAILED)
    u_c = vs.count(UNEVALUATED)
    rf_v = sum(
        1
        for d in dispositions
        if d.disposition is RUNTIME_FAILED and d.source_candidate_evaluation_state == VERIFIED
    )
    rf_rf = sum(
        1
        for d in dispositions
        if d.disposition is RUNTIME_FAILED
        and d.source_candidate_evaluation_state == RUNTIME_FAILED_CS
    )
    # Termination status from independent derivation
    ts = derive_termination_status(evaluation_input)
    # Warning/blocker aggregation
    stop_index = _find_stop_index(evaluation_input)
    w_digests, b_digests = build_result_message_digest_tuples(
        evaluation_input, dispositions, stop_index
    )
    # Ordered digest tuples
    F = f_c
    dd = tuple(d.feasibility_digest for d in dispositions)
    rd = tuple(r.ranked_record_digest for r in ranked_records)
    tn = rd[: min(evaluation_input.sizing_request_identity.top_n, F)]
    isd = tuple(evaluation_input.ordered_identity_snapshot_digests)
    ssd = tuple(
        cs.snapshot_digest if cs is not None else None for cs in evaluation_input.complete_snapshots
    )
    sbd = tuple(sb.binding_digest if sb is not None else None for sb in source_bindings)
    prd = tuple(p.preparation_result_digest if p is not None else None for p in preparation_results)
    return OptimizationResultCoreValues(
        schema_version=1,
        sizing_request_identity_digest=evaluation_input.sizing_request_identity_digest,
        passed_gate_digest=evaluation_input.gate_digest,
        candidate_set_digest=evaluation_input.candidate_set_digest,
        evaluation_input_digest=evaluation_input.evaluation_input_digest,
        optimization_objective=evaluation_input.sizing_request_identity.optimization_objective,
        requested_top_n=evaluation_input.sizing_request_identity.top_n,
        total_candidate_count=N,
        feasible_candidate_count=f_c,
        infeasible_candidate_count=inf_c,
        provider_mismatch_count=pm_c,
        integrity_failed_count=int_c,
        provenance_failed_count=pf_c,
        runtime_failed_count=rf_c,
        unevaluated_count=u_c,
        phase2_verified_record_count=p2_v,
        phase2_integrity_invalid_record_count=p2_ii,
        phase2_runtime_failed_record_count=p2_rf,
        phase2_unevaluated_record_count=p2_u,
        runtime_failed_from_phase2_verified_count=rf_v,
        runtime_failed_from_phase2_runtime_failed_count=rf_rf,
        ordered_disposition_record_digests=dd,
        ordered_ranked_record_digests=rd,
        ordered_top_n_record_digests=tn,
        ordered_identity_snapshot_digests=isd,
        ordered_phase2_source_snapshot_digests=ssd,
        ordered_phase3_source_binding_digests=sbd,
        ordered_phase3_preparation_result_digests=prd,
        termination_status=ts,
        ordered_warning_digests=w_digests,
        ordered_blocker_digests=b_digests,
    )


# === 19.1 Factory ===


def build_optimization_result(
    *,
    evaluation_input: Phase3EvaluationInput,
    sizing_request: SizingRequest,
    candidates: tuple[ManufacturableCandidate, ...],
    phase2_source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...],
    preparation_results: tuple[Phase3CandidatePreparationResult | None, ...],
    dispositions: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    classification_inputs: tuple[Phase3CandidateClassificationInput | None, ...],
    warning_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...],
    blocker_descriptor_tuples: tuple[tuple[Phase3MessageDescriptor, ...], ...],
    warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    phase3_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
) -> tuple[OptimizationResult, ProvenanceGraph]:
    # 0) Length gates — exact, no fallback
    N = evaluation_input.evaluation_record_count
    if len(dispositions) != N:
        raise ValueError("dispositions count != N")
    if len(preparation_results) != N:
        raise ValueError("preparation_results count != N")
    if len(phase2_source_record_descriptors) != N:
        raise ValueError("descriptors count != N")
    if len(evaluation_input.identity_snapshots) != N:
        raise ValueError("identity_snapshots count != N")
    if len(evaluation_input.complete_snapshots) != N:
        raise ValueError("complete_snapshots count != N")
    if len(source_bindings) != N:
        raise ValueError("source_bindings count != N")
    if len(classification_inputs) != N:
        raise ValueError("classification_inputs count != N")
    if len(evidence_failure_bindings) != N:
        raise ValueError("evidence_failure_bindings count != N")
    if len(source_failure_bindings) != N:
        raise ValueError("source_failure_bindings count != N")
    if len(phase3_failure_bindings) != N:
        raise ValueError("phase3_failure_bindings count != N")
    if len(warning_descriptor_tuples) != N:
        raise ValueError("warning_descriptor_tuples count != N")
    if len(blocker_descriptor_tuples) != N:
        raise ValueError("blocker_descriptor_tuples count != N")
    if len(warning_binding_tuples) != N:
        raise ValueError("warning_binding_tuples count != N")
    if len(blocker_binding_tuples) != N:
        raise ValueError("blocker_binding_tuples count != N")
    F = sum(1 for d in dispositions if d.disposition is FEASIBLE)
    if len(ranked_records) != F:
        raise ValueError("ranked_records count != F")
    # 0b) Full per-index authority gate — shared between builder and external verifier
    # Must reject any forbidden artifact on non-VERIFIED indices BEFORE nested verifier calls
    for i in range(N):
        rec_i = evaluation_input.evaluation_records[i]
        pr = preparation_results[i]
        desc_i = phase2_source_record_descriptors[i]
        cs_i = evaluation_input.complete_snapshots[i]
        sb_i = source_bindings[i]
        cin_i = classification_inputs[i]
        efb_i = evidence_failure_bindings[i]
        sfb_i = source_failure_bindings[i]
        p3fb_i = phase3_failure_bindings[i]
        verify_phase3_index_artifact_matrix(
            source_record=rec_i,
            identity_snapshot=evaluation_input.identity_snapshots[i],
            complete_snapshot=cs_i,
            source_record_descriptor=desc_i,
            source_binding=sb_i,
            classification_input=cin_i,
            preparation_result=pr,
            evidence_failure_binding=efb_i,
            source_failure_binding=sfb_i,
            phase3_failure_binding=p3fb_i,
        )
    # Build core values via single normative helper
    core_values = derive_optimization_result_core_values(
        evaluation_input=evaluation_input,
        dispositions=dispositions,
        ranked_records=ranked_records,
        source_bindings=source_bindings,
        preparation_results=preparation_results,
    )
    result_core_hash = core_values.compute_hash()
    # Extract fields needed for provenance graph and OptimizationResult constructor
    f_c = core_values.feasible_candidate_count
    inf_c = core_values.infeasible_candidate_count
    pm_c = core_values.provider_mismatch_count
    int_c = core_values.integrity_failed_count
    pf_c = core_values.provenance_failed_count
    rf_c = core_values.runtime_failed_count
    u_c = core_values.unevaluated_count
    p2_v = core_values.phase2_verified_record_count
    p2_ii = core_values.phase2_integrity_invalid_record_count
    p2_rf = core_values.phase2_runtime_failed_record_count
    p2_u = core_values.phase2_unevaluated_record_count
    rf_v = core_values.runtime_failed_from_phase2_verified_count
    rf_rf = core_values.runtime_failed_from_phase2_runtime_failed_count
    dd = core_values.ordered_disposition_record_digests
    rd = core_values.ordered_ranked_record_digests
    isd = core_values.ordered_identity_snapshot_digests
    ssd = core_values.ordered_phase2_source_snapshot_digests
    sbd = core_values.ordered_phase3_source_binding_digests
    prd = core_values.ordered_phase3_preparation_result_digests
    tn = core_values.ordered_top_n_record_digests
    ts = core_values.termination_status
    w_digests = core_values.ordered_warning_digests
    b_digests = core_values.ordered_blocker_digests
    # Build provenance
    graph = build_phase3_provenance_graph(
        ei=evaluation_input,
        dispositions=dispositions,
        ranked=ranked_records,
        total_candidate_count=N,
        feasible_candidate_count=f_c,
        requested_top_n=evaluation_input.sizing_request_identity.top_n,
        ordered_identity_snapshot_digests=isd,
        ordered_phase2_source_snapshot_digests=ssd,
        ordered_phase3_source_binding_digests=sbd,
        ordered_phase3_preparation_result_digests=prd,
        ordered_ranked_record_digests=rd,
        ordered_top_n_record_digests=tn,
        result_core_hash=result_core_hash,
        termination_status=ts,
        optimization_objective=evaluation_input.sizing_request_identity.optimization_objective,
        evaluation_input_digest=evaluation_input.evaluation_input_digest,
    )
    provenance_digest = graph.compute_hash()
    # Envelope
    env_payload = {"result_core_hash": result_core_hash, "provenance_digest": provenance_digest}
    result_hash = sha256_digest(env_payload)
    result_id = str(uuid.uuid5(PHASE3_RESULT_NS, result_hash))
    result = OptimizationResult(
        schema_version=1,
        optimization_result_id=result_id,
        sizing_request_identity_digest=evaluation_input.sizing_request_identity_digest,
        passed_gate_digest=evaluation_input.gate_digest,
        candidate_set_digest=evaluation_input.candidate_set_digest,
        evaluation_input_digest=evaluation_input.evaluation_input_digest,
        optimization_objective=evaluation_input.sizing_request_identity.optimization_objective,
        requested_top_n=evaluation_input.sizing_request_identity.top_n,
        total_candidate_count=N,
        feasible_candidate_count=f_c,
        infeasible_candidate_count=inf_c,
        provider_mismatch_count=pm_c,
        integrity_failed_count=int_c,
        provenance_failed_count=pf_c,
        runtime_failed_count=rf_c,
        unevaluated_count=u_c,
        phase2_verified_record_count=p2_v,
        phase2_integrity_invalid_record_count=p2_ii,
        phase2_runtime_failed_record_count=p2_rf,
        phase2_unevaluated_record_count=p2_u,
        runtime_failed_from_phase2_verified_count=rf_v,
        runtime_failed_from_phase2_runtime_failed_count=rf_rf,
        ordered_disposition_record_digests=dd,
        ordered_ranked_record_digests=rd,
        ordered_top_n_record_digests=tn,
        ordered_identity_snapshot_digests=isd,
        ordered_phase2_source_snapshot_digests=ssd,
        ordered_phase3_source_binding_digests=sbd,
        ordered_phase3_preparation_result_digests=prd,
        termination_status=ts,
        ordered_warning_digests=w_digests,
        ordered_blocker_digests=b_digests,
        result_core_hash=result_core_hash,
        provenance_digest=provenance_digest,
        result_hash=result_hash,
    )
    # Build authoritative artifacts container and delegate to shared semantic verifier
    artifacts = Phase3AuthoritativeArtifacts(
        sizing_request=sizing_request,
        phase2_source_record_descriptors=phase2_source_record_descriptors,
        source_bindings=source_bindings,
        classification_inputs=classification_inputs,
        preparation_results=preparation_results,
        warning_descriptor_tuples=warning_descriptor_tuples,
        blocker_descriptor_tuples=blocker_descriptor_tuples,
        warning_binding_tuples=warning_binding_tuples,
        blocker_binding_tuples=blocker_binding_tuples,
        evidence_failure_bindings=evidence_failure_bindings,
        source_failure_bindings=source_failure_bindings,
        phase3_failure_bindings=phase3_failure_bindings,
    )
    verify_phase3_result_semantics_or_raise(
        result=result,
        graph=graph,
        evaluation_input=evaluation_input,
        artifacts=artifacts,
        dispositions=dispositions,
        ranked_records=ranked_records,
    )
    return result, graph


def result_core_payload_from_values(
    *,
    schema_version: Literal[1] = 1,
    sizing_request_identity_digest: str,
    passed_gate_digest: str,
    candidate_set_digest: str,
    evaluation_input_digest: str,
    optimization_objective: OptimizationObjective,
    requested_top_n: int,
    total_candidate_count: int,
    feasible_candidate_count: int,
    infeasible_candidate_count: int,
    provider_mismatch_count: int,
    integrity_failed_count: int,
    provenance_failed_count: int,
    runtime_failed_count: int,
    unevaluated_count: int,
    phase2_verified_record_count: int,
    phase2_integrity_invalid_record_count: int,
    phase2_runtime_failed_record_count: int,
    phase2_unevaluated_record_count: int,
    runtime_failed_from_phase2_verified_count: int,
    runtime_failed_from_phase2_runtime_failed_count: int,
    ordered_disposition_record_digests: tuple[str, ...],
    ordered_ranked_record_digests: tuple[str, ...],
    ordered_top_n_record_digests: tuple[str, ...],
    ordered_identity_snapshot_digests: tuple[str, ...],
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...],
    ordered_phase3_source_binding_digests: tuple[str | None, ...],
    ordered_phase3_preparation_result_digests: tuple[str | None, ...],
    termination_status: TerminationStatus,
    ordered_warning_digests: tuple[str, ...],
    ordered_blocker_digests: tuple[str, ...],
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "sizing_request_identity_digest": sizing_request_identity_digest,
        "passed_gate_digest": passed_gate_digest,
        "candidate_set_digest": candidate_set_digest,
        "evaluation_input_digest": evaluation_input_digest,
        "optimization_objective": optimization_objective.value,
        "requested_top_n": requested_top_n,
        "total_candidate_count": total_candidate_count,
        "feasible_candidate_count": feasible_candidate_count,
        "infeasible_candidate_count": infeasible_candidate_count,
        "provider_mismatch_count": provider_mismatch_count,
        "integrity_failed_count": integrity_failed_count,
        "provenance_failed_count": provenance_failed_count,
        "runtime_failed_count": runtime_failed_count,
        "unevaluated_count": unevaluated_count,
        "phase2_verified_record_count": phase2_verified_record_count,
        "phase2_integrity_invalid_record_count": phase2_integrity_invalid_record_count,
        "phase2_runtime_failed_record_count": phase2_runtime_failed_record_count,
        "phase2_unevaluated_record_count": phase2_unevaluated_record_count,
        "runtime_failed_from_phase2_verified_count": runtime_failed_from_phase2_verified_count,
        "runtime_failed_from_phase2_runtime_failed_count": (
            runtime_failed_from_phase2_runtime_failed_count
        ),
        "ordered_disposition_record_digests": list(ordered_disposition_record_digests),
        "ordered_ranked_record_digests": list(ordered_ranked_record_digests),
        "ordered_top_n_record_digests": list(ordered_top_n_record_digests),
        "ordered_identity_snapshot_digests": list(ordered_identity_snapshot_digests),
        "ordered_phase2_source_snapshot_digests": list(ordered_phase2_source_snapshot_digests),
        "ordered_phase3_source_binding_digests": list(ordered_phase3_source_binding_digests),
        "ordered_phase3_preparation_result_digests": list(
            ordered_phase3_preparation_result_digests
        ),
        "termination_status": termination_status.value,
        "ordered_warning_digests": list(ordered_warning_digests),
        "ordered_blocker_digests": list(ordered_blocker_digests),
    }


# === 19.2 Model ===


class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    optimization_result_id: str
    sizing_request_identity_digest: str
    passed_gate_digest: str
    candidate_set_digest: str
    evaluation_input_digest: str
    optimization_objective: OptimizationObjective
    requested_top_n: int
    total_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    provenance_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int
    phase2_verified_record_count: int
    phase2_integrity_invalid_record_count: int
    phase2_runtime_failed_record_count: int
    phase2_unevaluated_record_count: int
    runtime_failed_from_phase2_verified_count: int
    runtime_failed_from_phase2_runtime_failed_count: int
    ordered_disposition_record_digests: tuple[str, ...]
    ordered_ranked_record_digests: tuple[str, ...]
    ordered_top_n_record_digests: tuple[str, ...]
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...]
    ordered_phase3_source_binding_digests: tuple[str | None, ...]
    ordered_phase3_preparation_result_digests: tuple[str | None, ...]
    termination_status: TerminationStatus
    ordered_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]
    result_core_hash: str
    provenance_digest: str
    result_hash: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1:
            raise ValueError("version must be 1")
        if self.requested_top_n < 1:
            raise ValueError("top_n must be ≥ 1")
        for f in [
            "total_candidate_count",
            "feasible_candidate_count",
            "infeasible_candidate_count",
            "provider_mismatch_count",
            "integrity_failed_count",
            "provenance_failed_count",
            "runtime_failed_count",
            "unevaluated_count",
            "phase2_verified_record_count",
            "phase2_integrity_invalid_record_count",
            "phase2_runtime_failed_record_count",
            "phase2_unevaluated_record_count",
            "runtime_failed_from_phase2_verified_count",
            "runtime_failed_from_phase2_runtime_failed_count",
        ]:
            if getattr(self, f) < 0:
                raise ValueError(f"{f} < 0")
        d3 = (
            self.feasible_candidate_count
            + self.infeasible_candidate_count
            + self.provider_mismatch_count
            + self.integrity_failed_count
            + self.provenance_failed_count
            + self.runtime_failed_count
            + self.unevaluated_count
        )
        if d3 != self.total_candidate_count:
            raise ValueError("disposition sum ≠ total")
        p2 = (
            self.phase2_verified_record_count
            + self.phase2_integrity_invalid_record_count
            + self.phase2_runtime_failed_record_count
            + self.phase2_unevaluated_record_count
        )
        if p2 != self.total_candidate_count:
            raise ValueError("p2 sum ≠ total")
        if (
            self.runtime_failed_count
            != self.runtime_failed_from_phase2_verified_count
            + self.runtime_failed_from_phase2_runtime_failed_count
        ):
            raise ValueError("rf cross")
        if (
            self.phase2_verified_record_count
            != self.feasible_candidate_count
            + self.infeasible_candidate_count
            + self.provider_mismatch_count
            + self.runtime_failed_from_phase2_verified_count
        ):
            raise ValueError("p2_v cross")
        if (
            self.phase2_integrity_invalid_record_count
            != self.integrity_failed_count + self.provenance_failed_count
        ):
            raise ValueError("p2_ii cross")
        if (
            self.phase2_runtime_failed_record_count
            != self.runtime_failed_from_phase2_runtime_failed_count
        ):
            raise ValueError("p2_rf cross")
        if self.phase2_unevaluated_record_count != self.unevaluated_count:
            raise ValueError("p2_u cross")
        N, F, TN = (
            self.total_candidate_count,
            self.feasible_candidate_count,
            min(self.requested_top_n, self.feasible_candidate_count),
        )
        if len(self.ordered_disposition_record_digests) != N:
            raise ValueError("disposition length ≠ N")
        if len(self.ordered_ranked_record_digests) != F:
            raise ValueError("ranked length ≠ F")
        if len(self.ordered_top_n_record_digests) != TN:
            raise ValueError("Top-N length ≠ min")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]:
            raise ValueError("Top-N not prefix")
        if len(self.ordered_identity_snapshot_digests) != N:
            raise ValueError("identity snapshots length ≠ N")
        if len(self.ordered_phase2_source_snapshot_digests) != N:
            raise ValueError("source snapshots length ≠ N")
        if len(self.ordered_phase3_source_binding_digests) != N:
            raise ValueError("bindings length ≠ N")
        if len(self.ordered_phase3_preparation_result_digests) != N:
            raise ValueError("prep results length ≠ N")
        # Per-index preparation digest validation: all entries must be sha256:* or None
        for i, v in enumerate(self.ordered_phase3_preparation_result_digests):
            if v is None:
                continue
            if not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"preparation_result_digest[{i}] invalid format")
        # Per-index source binding digest validation
        for i, v in enumerate(self.ordered_phase3_source_binding_digests):
            if v is None:
                continue
            if not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"source_binding_digest[{i}] invalid format")
        if self.result_core_hash != sha256_digest(result_core_payload(self)):
            raise ValueError("core hash mismatch")
        expected_env = sha256_digest(
            {"result_core_hash": self.result_core_hash, "provenance_digest": self.provenance_digest}
        )
        if self.result_hash != expected_env:
            raise ValueError("envelope hash mismatch")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, self.result_hash))
        if self.optimization_result_id != expected_id:
            raise ValueError("UUID mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        dispositions: tuple[CandidateDispositionRecord, ...],
        ranked_records: tuple[RankedCandidateRecord, ...],
        source_records: tuple[CandidateEvaluationRecord, ...],
        preparation_results: tuple[Phase3CandidatePreparationResult | None, ...],
        source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    ) -> None:
        N, F = self.total_candidate_count, self.feasible_candidate_count
        if len(dispositions) != N:
            raise ValueError("dispositions length != N")
        if len(ranked_records) != F:
            raise ValueError("ranked_records length != F")
        if len(source_records) != N:
            raise ValueError("source_records length != N")
        if len(preparation_results) != N:
            raise ValueError("preparation_results length != N")
        if len(source_bindings) != N:
            raise ValueError("source_bindings length != N")
        # Verify ordered digests match actual artifacts
        for i, d in enumerate(dispositions):
            if self.ordered_disposition_record_digests[i] != d.feasibility_digest:
                raise ValueError(f"disposition[{i}] digest mismatch")
        for i, r in enumerate(ranked_records):
            if self.ordered_ranked_record_digests[i] != r.ranked_record_digest:
                raise ValueError(f"ranked[{i}] digest mismatch")
        TN = min(self.requested_top_n, F)
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]:
            raise ValueError("Top-N not prefix of ranked")
        # Per-index preparation digest validation against independent authority
        for i in range(N):
            rec = source_records[i]
            pr = preparation_results[i]
            prep_digest = self.ordered_phase3_preparation_result_digests[i]
            if rec.candidate_evaluation_state == VERIFIED:
                if prep_digest is None:
                    raise ValueError(f"prep[{i}] VERIFIED must have non-None digest")
                if not self.DIGEST_PATTERN.match(prep_digest):
                    raise ValueError(f"prep[{i}] invalid digest format")
                if pr is None:
                    raise ValueError(f"prep[{i}] VERIFIED requires preparation_result")
                if prep_digest != pr.preparation_result_digest:
                    raise ValueError(f"prep[{i}] digest mismatch vs preparation_result")
            else:
                if prep_digest is not None:
                    raise ValueError(f"prep[{i}] non-VERIFIED must have None digest")
                if pr is not None:
                    raise ValueError(f"prep[{i}] non-VERIFIED must have None preparation_result")
            # Source binding digest validation against independent authority
            sb = source_bindings[i]
            sb_digest = self.ordered_phase3_source_binding_digests[i]
            expected_sb = sb.binding_digest if sb is not None else None
            if sb_digest != expected_sb:
                raise ValueError(f"source_binding[{i}] digest mismatch")
        # PARTIAL allows feasible_candidate_count < requested_top_n;
        # Top-N returns min(requested_top_n, feasible_candidate_count) records
        # COMPLETE with feasible < requested_top_n also returns only available records
        # Both cases: Top-N must be the prefix of ranked records
        # Self-hash integrity
        if self.result_core_hash != sha256_digest(result_core_payload(self)):
            raise ValueError("core hash mismatch")
        expected_env = sha256_digest(
            {"result_core_hash": self.result_core_hash, "provenance_digest": self.provenance_digest}
        )
        if self.result_hash != expected_env:
            raise ValueError("envelope hash mismatch")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, self.result_hash))
        if self.optimization_result_id != expected_id:
            raise ValueError("UUID mismatch")


def result_core_payload(r: OptimizationResult) -> dict[str, object]:
    return {
        "schema_version": r.schema_version,
        "sizing_request_identity_digest": r.sizing_request_identity_digest,
        "passed_gate_digest": r.passed_gate_digest,
        "candidate_set_digest": r.candidate_set_digest,
        "evaluation_input_digest": r.evaluation_input_digest,
        "optimization_objective": r.optimization_objective.value,
        "requested_top_n": r.requested_top_n,
        "total_candidate_count": r.total_candidate_count,
        "feasible_candidate_count": r.feasible_candidate_count,
        "infeasible_candidate_count": r.infeasible_candidate_count,
        "provider_mismatch_count": r.provider_mismatch_count,
        "integrity_failed_count": r.integrity_failed_count,
        "provenance_failed_count": r.provenance_failed_count,
        "runtime_failed_count": r.runtime_failed_count,
        "unevaluated_count": r.unevaluated_count,
        "phase2_verified_record_count": r.phase2_verified_record_count,
        "phase2_integrity_invalid_record_count": r.phase2_integrity_invalid_record_count,
        "phase2_runtime_failed_record_count": r.phase2_runtime_failed_record_count,
        "phase2_unevaluated_record_count": r.phase2_unevaluated_record_count,
        "runtime_failed_from_phase2_verified_count": r.runtime_failed_from_phase2_verified_count,
        "runtime_failed_from_phase2_runtime_failed_count": (
            r.runtime_failed_from_phase2_runtime_failed_count
        ),
        "ordered_disposition_record_digests": list(r.ordered_disposition_record_digests),
        "ordered_ranked_record_digests": list(r.ordered_ranked_record_digests),
        "ordered_top_n_record_digests": list(r.ordered_top_n_record_digests),
        "ordered_identity_snapshot_digests": list(r.ordered_identity_snapshot_digests),
        "ordered_phase2_source_snapshot_digests": list(r.ordered_phase2_source_snapshot_digests),
        "ordered_phase3_source_binding_digests": list(r.ordered_phase3_source_binding_digests),
        "ordered_phase3_preparation_result_digests": list(
            r.ordered_phase3_preparation_result_digests
        ),
        "termination_status": r.termination_status.value,
        "ordered_warning_digests": list(r.ordered_warning_digests),
        "ordered_blocker_digests": list(r.ordered_blocker_digests),
    }
