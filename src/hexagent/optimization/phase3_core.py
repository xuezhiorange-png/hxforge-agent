"""
TASK-009 Phase 3 — Core types: enums, descriptors, snapshots, bindings,
constructor matrix, decimal helpers, duty/delta-T equations, and count verifier.

Sections 2-11 of the Phase 3 design contract.
"""

from __future__ import annotations

import dataclasses
import math
import re
import typing
from decimal import Decimal
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.domain.messages import ErrorCode
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    CanonicalizedEngineeringMessageDescriptor,
    CanonicalizedRunFailureDescriptor,
    FeasibilityStatus,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
    verified_rating_evidence_payload_from_descriptors,
)

# ── Forward references for types defined in later sections ──────────────
# Phase3EvaluationInput is defined in Section 12 of the contract.
# OptimizationResult / disposition types are defined in later sections.
if typing.TYPE_CHECKING:
    pass  # Phase3EvaluationInput used via string annotation


# ═══════════════════════════════════════════════════════════════════════════
# Section 2 — Frozen enums
# ═══════════════════════════════════════════════════════════════════════════


class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    INTEGRITY_FAILED = "integrity_failed"
    PROVENANCE_FAILED = "provenance_failed"
    RUNTIME_FAILED = "runtime_failed"
    UNEVALUATED = "unevaluated"


class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"
    RATING_FAILED = "rating_failed"
    DUTY_SHORTFALL = "duty_shortfall"
    TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
    INTEGRITY_FAILED = "integrity_failed"
    PROVENANCE_FAILED = "provenance_failed"
    PHASE2_RUNTIME_FAILED = "phase2_runtime_failed"
    PHASE3_RUNTIME_FAILED = "phase3_runtime_failed"


class TerminationStatus(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"


class FailureOrigin(StrEnum):
    NONE = "none"
    PHASE2_EVALUATION = "phase2_evaluation"
    PHASE3_CLASSIFICATION = "phase3_classification"


class Phase3ProvenanceRelation(StrEnum):
    REGULATES = "regulates"
    CONSUMED_BY = "consumed_by"
    PRODUCED = "produced"
    EVALUATED = "evaluated"
    RANKED = "ranked"
    SELECTED_BY = "selected_by"
    SELECTED = "selected"
    EXECUTED_BY = "executed_by"


class Phase3PreparationStatus(StrEnum):
    READY = "ready"
    FAILED = "failed"


class Phase3PreparationFailureStage(StrEnum):
    WARNING_DESCRIPTOR = "warning_descriptor"
    BLOCKER_DESCRIPTOR = "blocker_descriptor"
    FAILURE_DESCRIPTOR = "failure_descriptor"
    EVIDENCE_DIGEST = "evidence_digest"
    SOURCE_BINDING = "source_binding"
    CLASSIFICATION_INPUT = "classification_input"
    CLASSIFICATION = "classification"


# ═══════════════════════════════════════════════════════════════════════════
# Section 3 — Evidence digest via authoritative Phase 2 helper
# ═══════════════════════════════════════════════════════════════════════════


def compute_evidence_digest_phase3(
    evidence: VerifiedRatingEvidenceSnapshot | None,
    *,
    warning_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    blocker_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    failure_descriptor: CanonicalizedRunFailureDescriptor | None,
) -> str | None:
    if evidence is None:
        return None
    payload = verified_rating_evidence_payload_from_descriptors(
        evidence,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        failure_descriptor=failure_descriptor,
    )
    return sha256_digest(payload)


# ═══════════════════════════════════════════════════════════════════════════
# Section 4 — Phase3MessageDescriptor and binding
# ═══════════════════════════════════════════════════════════════════════════


class Phase3MessageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    owner_sort_key: tuple[str, str, str, str, tuple[str, ...], str]
    original_code: str
    message_payload_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.original_code:
            raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest):
            raise ValueError("invalid message_payload_digest")
        return self


class Phase3MessageDescriptorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    owner_sort_key: tuple[str, str, str, str, tuple[str, ...], str]
    original_code: str
    message_payload_digest: str
    descriptor_binding_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.original_code:
            raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest):
            raise ValueError("invalid message_payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest):
            raise ValueError("invalid descriptor_binding_digest")
        expected = sha256_digest(
            {
                "owner_sort_key": list(self.owner_sort_key),
                "original_code": self.original_code,
                "message_payload_digest": self.message_payload_digest,
            }
        )
        if self.descriptor_binding_digest != expected:
            raise ValueError("descriptor_binding_digest mismatch")
        return self


def build_phase3_message_descriptor_binding(
    desc: Phase3MessageDescriptor,
) -> Phase3MessageDescriptorBinding:
    payload = {
        "owner_sort_key": list(desc.owner_sort_key),
        "original_code": desc.original_code,
        "message_payload_digest": desc.message_payload_digest,
    }
    d = sha256_digest(payload)
    return Phase3MessageDescriptorBinding(
        owner_sort_key=desc.owner_sort_key,
        original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest,
        descriptor_binding_digest=d,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 5 — RunFailure descriptor binding and canonicalization
# ═══════════════════════════════════════════════════════════════════════════


class Phase3RunFailureDescriptorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    original_code: str | None
    payload_digest: str | None
    canonicalization_error_digest: str | None
    context_path_digest: str | None
    safe_marker_digest: str | None
    descriptor_binding_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest):
            raise ValueError("invalid descriptor_binding_digest")
        if self.payload_digest is not None:
            if not self.DIGEST_PATTERN.match(self.payload_digest):
                raise ValueError("invalid payload_digest")
            if self.canonicalization_error_digest is not None:
                raise ValueError("SUCCESS: ce must be None")
            if self.context_path_digest is not None:
                raise ValueError("SUCCESS: ctx_path must be None")
            if self.safe_marker_digest is not None:
                raise ValueError("SUCCESS: safe_marker must be None")
        elif self.canonicalization_error_digest is not None:
            if self.payload_digest is not None:
                raise ValueError("FAILED: payload must be None")
            if not self.DIGEST_PATTERN.match(self.canonicalization_error_digest):
                raise ValueError("invalid ce_digest")
            if self.context_path_digest is None or not self.DIGEST_PATTERN.match(
                self.context_path_digest
            ):
                raise ValueError("invalid ctx_path")
            if self.safe_marker_digest is None or not self.DIGEST_PATTERN.match(
                self.safe_marker_digest
            ):
                raise ValueError("invalid safe_marker")
        else:
            raise ValueError("must be SUCCESS or CANONICALIZATION_FAILED")
        payload = {
            "original_code": self.original_code,
            "payload_digest": self.payload_digest,
            "canonicalization_error_digest": self.canonicalization_error_digest,
            "context_path_digest": self.context_path_digest,
            "safe_marker_digest": self.safe_marker_digest,
        }
        if self.descriptor_binding_digest != sha256_digest(payload):
            raise ValueError("descriptor_binding_digest mismatch")
        return self


def build_phase3_run_failure_descriptor_binding(
    descriptor: CanonicalizedRunFailureDescriptor,
) -> Phase3RunFailureDescriptorBinding:
    ce = descriptor.canonicalization_error
    ce_digest = (
        sha256_digest(
            {
                "failure_kind": ce.failure_kind.value,
                "context_key": ce.context_key,
                "context_path": list(ce.context_path),
                "offending_type": ce.offending_type,
                "safe_marker_digest": descriptor.safe_marker_digest,
            }
        )
        if ce is not None
        else None
    )
    raw = {
        "original_code": descriptor.original_code,
        "payload_digest": descriptor.payload_digest if ce is None else None,
        "canonicalization_error_digest": ce_digest,
        "context_path_digest": descriptor.context_path_digest if ce is not None else None,
        "safe_marker_digest": descriptor.safe_marker_digest if ce is not None else None,
    }
    bd = sha256_digest(raw)
    return Phase3RunFailureDescriptorBinding(
        original_code=descriptor.original_code,
        payload_digest=descriptor.payload_digest if ce is None else None,
        canonicalization_error_digest=ce_digest,
        context_path_digest=descriptor.context_path_digest if ce is not None else None,
        safe_marker_digest=descriptor.safe_marker_digest if ce is not None else None,
        descriptor_binding_digest=bd,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 6 — Phase2SourceRecordIdentitySnapshot
# ═══════════════════════════════════════════════════════════════════════════


def _identity_snapshot_payload(
    s: Phase2SourceRecordIdentitySnapshot,
) -> dict[str, object]:
    return {
        "schema_version": s.schema_version,
        "source_qualified_candidate_id": s.source_qualified_candidate_id,
        "evaluation_order_index": s.evaluation_order_index,
        "candidate_evaluation_state": s.candidate_evaluation_state.value,
        "feasible": s.feasible,
        "feasibility_status": s.feasibility_status.value,
        "hash_verification_outcome": s.hash_verification_outcome.value,
        "provenance_verification_outcome": s.provenance_verification_outcome.value,
        "provider_identity_matches": s.provider_identity_matches,
        "rating_status": s.rating_status,
        "candidate_evaluation_identity_digest": s.candidate_evaluation_identity_digest,
        "invalid_rating_evidence_digest": s.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": s.claimed_rating_result_audit_digest,
    }


class Phase2SourceRecordIdentitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool
    feasibility_status: FeasibilityStatus
    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome
    provider_identity_matches: bool
    rating_status: str | None
    candidate_evaluation_identity_digest: str | None
    invalid_rating_evidence_digest: str | None
    claimed_rating_result_audit_digest: str | None
    identity_snapshot_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be ≥ 0")
        for v, n in [
            (self.candidate_evaluation_identity_digest, "identity"),
            (self.invalid_rating_evidence_digest, "invalid"),
            (self.claimed_rating_result_audit_digest, "audit"),
        ]:
            if v is not None and not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"invalid {n} digest")
        expected = sha256_digest(_identity_snapshot_payload(self))
        if self.identity_snapshot_digest != expected:
            raise ValueError("identity_snapshot_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
    ) -> None:
        """Authoritative verifier: validates source identity, digest fields, branch matrix,
        and self-hash."""
        if self.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        if self.candidate_evaluation_state != source_record.candidate_evaluation_state:
            raise ValueError("eval_state mismatch")
        if self.feasible != source_record.feasible:
            raise ValueError("feasible mismatch")
        if self.feasibility_status != source_record.feasibility_status:
            raise ValueError("feasibility_status mismatch")
        if self.hash_verification_outcome != source_record.hash_verification_outcome:
            raise ValueError("hash_outcome mismatch")
        if self.provenance_verification_outcome != source_record.provenance_verification_outcome:
            raise ValueError("provenance_outcome mismatch")
        if self.provider_identity_matches != source_record.provider_identity_matches:
            raise ValueError("provider_matches mismatch")
        if self.rating_status != source_record.rating_status:
            raise ValueError("rating_status mismatch")
        # Digest field validation
        expected_identity_digest = (
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity is not None
            else None
        )
        if self.candidate_evaluation_identity_digest != expected_identity_digest:
            raise ValueError("candidate_evaluation_identity_digest mismatch")
        expected_invalid_digest = (
            source_record.invalid_rating_evidence.invalid_evidence_digest
            if source_record.invalid_rating_evidence is not None
            else None
        )
        if self.invalid_rating_evidence_digest != expected_invalid_digest:
            raise ValueError("invalid_rating_evidence_digest mismatch")
        expected_audit_digest = (
            source_record.claimed_rating_result_audit.audit_digest
            if source_record.claimed_rating_result_audit is not None
            else None
        )
        if self.claimed_rating_result_audit_digest != expected_audit_digest:
            raise ValueError("claimed_rating_result_audit_digest mismatch")


def build_identity_snapshot(
    rec: CandidateEvaluationRecord,
) -> Phase2SourceRecordIdentitySnapshot:
    eid = (
        rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None
        else None
    )
    iid = (
        rec.invalid_rating_evidence.invalid_evidence_digest
        if rec.invalid_rating_evidence is not None
        else None
    )
    ad = (
        rec.claimed_rating_result_audit.audit_digest
        if rec.claimed_rating_result_audit is not None
        else None
    )
    payload = {
        "schema_version": 1,
        "source_qualified_candidate_id": rec.source_qualified_candidate_id,
        "evaluation_order_index": rec.evaluation_order_index,
        "candidate_evaluation_state": rec.candidate_evaluation_state.value,
        "feasible": rec.feasible,
        "feasibility_status": rec.feasibility_status.value,
        "hash_verification_outcome": rec.hash_verification_outcome.value,
        "provenance_verification_outcome": rec.provenance_verification_outcome.value,
        "provider_identity_matches": rec.provider_identity_matches,
        "rating_status": rec.rating_status,
        "candidate_evaluation_identity_digest": eid,
        "invalid_rating_evidence_digest": iid,
        "claimed_rating_result_audit_digest": ad,
    }
    digest = sha256_digest(payload)
    return Phase2SourceRecordIdentitySnapshot(
        schema_version=1,
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        candidate_evaluation_state=rec.candidate_evaluation_state,
        feasible=rec.feasible,
        feasibility_status=rec.feasibility_status,
        hash_verification_outcome=rec.hash_verification_outcome,
        provenance_verification_outcome=rec.provenance_verification_outcome,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=eid,
        invalid_rating_evidence_digest=iid,
        claimed_rating_result_audit_digest=ad,
        identity_snapshot_digest=digest,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 7 — Phase2SourceRecordSnapshot
# ═══════════════════════════════════════════════════════════════════════════


def phase2_source_record_snapshot_payload_from_values(
    *,
    schema_version: int = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    candidate_evaluation_state: CandidateEvaluationState,
    feasible: bool,
    feasibility_status: FeasibilityStatus,
    hash_verification_outcome: VerificationOutcome,
    provenance_verification_outcome: VerificationOutcome,
    provider_identity_matches: bool,
    rating_status: str | None,
    candidate_evaluation_identity_digest: str | None,
    verified_rating_evidence_digest: str | None,
    invalid_rating_evidence_digest: str | None,
    claimed_rating_result_audit_digest: str | None,
    evaluation_failure_digest: str | None,
    phase2_source_record_descriptor_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_binding_digest: str | None,
    evidence_failure_binding_digest: str | None,
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "candidate_evaluation_state": candidate_evaluation_state.value,
        "feasible": feasible,
        "feasibility_status": feasibility_status.value,
        "hash_verification_outcome": hash_verification_outcome.value,
        "provenance_verification_outcome": provenance_verification_outcome.value,
        "provider_identity_matches": provider_identity_matches,
        "rating_status": rating_status,
        "candidate_evaluation_identity_digest": candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": claimed_rating_result_audit_digest,
        "evaluation_failure_digest": evaluation_failure_digest,
        "phase2_source_record_descriptor_digest": phase2_source_record_descriptor_digest,
        "warning_descriptor_binding_digests": list(warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": source_evaluation_failure_binding_digest,
        "evidence_failure_binding_digest": evidence_failure_binding_digest,
    }


class Phase2SourceRecordSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool
    feasibility_status: FeasibilityStatus
    hash_verification_outcome: VerificationOutcome
    provenance_verification_outcome: VerificationOutcome
    provider_identity_matches: bool
    rating_status: str | None
    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    invalid_rating_evidence_digest: str | None
    claimed_rating_result_audit_digest: str | None
    evaluation_failure_digest: str | None
    phase2_source_record_descriptor_digest: str
    warning_descriptor_binding_digests: tuple[str, ...]
    blocker_descriptor_binding_digests: tuple[str, ...]
    source_evaluation_failure_binding_digest: str | None
    evidence_failure_binding_digest: str | None
    snapshot_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be ≥ 0")
        for f in ("phase2_source_record_descriptor_digest", "snapshot_digest"):
            if not self.DIGEST_PATTERN.match(getattr(self, f)):
                raise ValueError(f"invalid {f}")
        for v, n in [
            (self.candidate_evaluation_identity_digest, "identity"),
            (self.verified_rating_evidence_digest, "evidence"),
            (self.invalid_rating_evidence_digest, "invalid"),
            (self.claimed_rating_result_audit_digest, "audit"),
            (self.evaluation_failure_digest, "failure"),
            (self.source_evaluation_failure_binding_digest, "source_failure_binding"),
            (self.evidence_failure_binding_digest, "evidence_failure_binding"),
        ]:
            if v is not None and not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"invalid {n} digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError("invalid blocker binding digest")
        # Recompute payload directly from primitive fields — no model_dump()
        payload = phase2_source_record_snapshot_payload_from_values(
            schema_version=self.schema_version,
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            candidate_evaluation_state=self.candidate_evaluation_state,
            feasible=self.feasible,
            feasibility_status=self.feasibility_status,
            hash_verification_outcome=self.hash_verification_outcome,
            provenance_verification_outcome=self.provenance_verification_outcome,
            provider_identity_matches=self.provider_identity_matches,
            rating_status=self.rating_status,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            invalid_rating_evidence_digest=self.invalid_rating_evidence_digest,
            claimed_rating_result_audit_digest=self.claimed_rating_result_audit_digest,
            evaluation_failure_digest=self.evaluation_failure_digest,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest,
        )
        if self.snapshot_digest != sha256_digest(payload):
            raise ValueError("snapshot_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        identity_snapshot: Phase2SourceRecordIdentitySnapshot,
        source_record_descriptor: Phase2SourceRecordDescriptor,
        verified_evidence: VerifiedRatingEvidenceSnapshot | None,
        warning_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
        blocker_descriptor_bindings: tuple[Phase3MessageDescriptorBinding, ...],
        source_failure_binding: Phase3RunFailureDescriptorBinding | None,
        evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
    ) -> None:
        # 1) Delegate to upstream authority: identity snapshot verifier
        identity_snapshot.verify_or_raise(source_record=source_record)
        # 2) Delegate to upstream authority: source record descriptor verifier
        source_record_descriptor.verify_or_raise(
            source_record=source_record,
            identity_snapshot=identity_snapshot,
            verified_evidence=verified_evidence,
            source_failure_binding=source_failure_binding,
        )
        # 3) Field-level consistency with source_record
        if self.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        if self.candidate_evaluation_state != source_record.candidate_evaluation_state:
            raise ValueError("eval_state mismatch")
        if self.feasible != source_record.feasible:
            raise ValueError("feasible mismatch")
        if self.feasibility_status != source_record.feasibility_status:
            raise ValueError("feasibility_status mismatch")
        if self.hash_verification_outcome != source_record.hash_verification_outcome:
            raise ValueError("hash_verification_outcome mismatch")
        if self.provenance_verification_outcome != source_record.provenance_verification_outcome:
            raise ValueError("provenance_verification_outcome mismatch")
        if self.provider_identity_matches != source_record.provider_identity_matches:
            raise ValueError("provider_identity_matches mismatch")
        if self.rating_status != source_record.rating_status:
            raise ValueError("rating_status mismatch")
        # 4) Digest fields: use source_failure_binding.descriptor_binding_digest
        efd = (
            source_failure_binding.descriptor_binding_digest
            if source_failure_binding is not None and source_record.evaluation_failure is not None
            else None
        )
        if self.evaluation_failure_digest != efd:
            raise ValueError("evaluation_failure_digest mismatch")
        # 5) Digest fields: extract from source_record and compare
        expected_identity_digest = (
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity is not None
            else None
        )
        if self.candidate_evaluation_identity_digest != expected_identity_digest:
            raise ValueError("candidate_evaluation_identity_digest mismatch")
        expected_verified_digest = (
            verified_evidence.compute_explicit_evidence_digest()
            if verified_evidence is not None
            else None
        )
        if self.verified_rating_evidence_digest != expected_verified_digest:
            raise ValueError("verified_rating_evidence_digest mismatch")
        expected_invalid_digest = (
            source_record.invalid_rating_evidence.invalid_evidence_digest
            if source_record.invalid_rating_evidence is not None
            else None
        )
        if self.invalid_rating_evidence_digest != expected_invalid_digest:
            raise ValueError("invalid_rating_evidence_digest mismatch")
        expected_audit_digest = (
            source_record.claimed_rating_result_audit.audit_digest
            if source_record.claimed_rating_result_audit is not None
            else None
        )
        if self.claimed_rating_result_audit_digest != expected_audit_digest:
            raise ValueError("claimed_rating_result_audit_digest mismatch")
        # 6) Authoritative source record descriptor digest (from artifact)
        if (
            self.phase2_source_record_descriptor_digest
            != source_record_descriptor.descriptor_digest
        ):
            raise ValueError("phase2_source_record_descriptor_digest mismatch")
        # 7) Warning/blocker bindings
        if len(self.warning_descriptor_binding_digests) != len(warning_descriptor_bindings):
            raise ValueError("warning_binding_digests length mismatch")
        for actual_d, expected in zip(
            self.warning_descriptor_binding_digests, warning_descriptor_bindings, strict=True
        ):
            if actual_d != expected.descriptor_binding_digest:
                raise ValueError("warning_binding_digest mismatch")
        if len(self.blocker_descriptor_binding_digests) != len(blocker_descriptor_bindings):
            raise ValueError("blocker_binding_digests length mismatch")
        for actual_d, expected in zip(
            self.blocker_descriptor_binding_digests, blocker_descriptor_bindings, strict=True
        ):
            if actual_d != expected.descriptor_binding_digest:
                raise ValueError("blocker_binding_digest mismatch")
        # 8) Failure bindings
        sfbd = (
            source_failure_binding.descriptor_binding_digest
            if source_failure_binding is not None
            else None
        )
        if self.source_evaluation_failure_binding_digest != sfbd:
            raise ValueError("source_failure_binding_digest mismatch")
        efbd = (
            evidence_failure_binding.descriptor_binding_digest
            if evidence_failure_binding is not None
            else None
        )
        if self.evidence_failure_binding_digest != efbd:
            raise ValueError("evidence_failure_binding_digest mismatch")
        # 9) Self-hash replay as integrity check
        payload = phase2_source_record_snapshot_payload_from_values(
            schema_version=self.schema_version,
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            candidate_evaluation_state=self.candidate_evaluation_state,
            feasible=self.feasible,
            feasibility_status=self.feasibility_status,
            hash_verification_outcome=self.hash_verification_outcome,
            provenance_verification_outcome=self.provenance_verification_outcome,
            provider_identity_matches=self.provider_identity_matches,
            rating_status=self.rating_status,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            invalid_rating_evidence_digest=self.invalid_rating_evidence_digest,
            claimed_rating_result_audit_digest=self.claimed_rating_result_audit_digest,
            evaluation_failure_digest=self.evaluation_failure_digest,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest,
        )
        if self.snapshot_digest != sha256_digest(payload):
            raise ValueError("snapshot_digest mismatch")


def build_phase2_source_record_snapshot(
    *,
    schema_version: int = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    candidate_evaluation_state: CandidateEvaluationState,
    feasible: bool,
    feasibility_status: FeasibilityStatus,
    hash_verification_outcome: VerificationOutcome,
    provenance_verification_outcome: VerificationOutcome,
    provider_identity_matches: bool,
    rating_status: str | None,
    candidate_evaluation_identity_digest: str | None,
    verified_rating_evidence_digest: str | None,
    invalid_rating_evidence_digest: str | None,
    claimed_rating_result_audit_digest: str | None,
    evaluation_failure_digest: str | None,
    phase2_source_record_descriptor_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_binding_digest: str | None,
    evidence_failure_binding_digest: str | None,
) -> Phase2SourceRecordSnapshot:
    payload = phase2_source_record_snapshot_payload_from_values(
        schema_version=schema_version,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=candidate_evaluation_state,
        feasible=feasible,
        feasibility_status=feasibility_status,
        hash_verification_outcome=hash_verification_outcome,
        provenance_verification_outcome=provenance_verification_outcome,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        claimed_rating_result_audit_digest=claimed_rating_result_audit_digest,
        evaluation_failure_digest=evaluation_failure_digest,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        evidence_failure_binding_digest=evidence_failure_binding_digest,
    )
    sd = sha256_digest(payload)
    return Phase2SourceRecordSnapshot(
        schema_version=schema_version,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        candidate_evaluation_state=candidate_evaluation_state,
        feasible=feasible,
        feasibility_status=feasibility_status,
        hash_verification_outcome=hash_verification_outcome,
        provenance_verification_outcome=provenance_verification_outcome,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        claimed_rating_result_audit_digest=claimed_rating_result_audit_digest,
        evaluation_failure_digest=evaluation_failure_digest,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        evidence_failure_binding_digest=evidence_failure_binding_digest,
        snapshot_digest=sd,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 7b — Phase2SourceRecordDescriptor — independent authority artifact
# ═══════════════════════════════════════════════════════════════════════════


@dataclasses.dataclass(frozen=True, slots=True)
class Phase2SourceRecordDescriptor:
    """Independent authority artifact that binds source state to a deterministic digest.

    External verifier receives actual descriptors, not tuples of digests,
    preventing two jointly-forgeable Phase 3 artifacts from authenticating each other.
    """

    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    identity_snapshot_digest: str
    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    invalid_rating_evidence_digest: str | None
    claimed_rating_result_audit_digest: str | None
    evaluation_failure_digest: str | None
    descriptor_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        identity_snapshot: Phase2SourceRecordIdentitySnapshot,
        verified_evidence: VerifiedRatingEvidenceSnapshot | None,
        source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    ) -> None:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be >= 0")
        # Cross-validate against source_record
        if self.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        if self.candidate_evaluation_state != source_record.candidate_evaluation_state:
            raise ValueError("candidate_evaluation_state mismatch")
        if self.identity_snapshot_digest != identity_snapshot.identity_snapshot_digest:
            raise ValueError("identity_snapshot_digest mismatch")
        expected_cei = (
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity is not None
            else None
        )
        if self.candidate_evaluation_identity_digest != expected_cei:
            raise ValueError("candidate_evaluation_identity_digest mismatch")
        expected_evidence = (
            verified_evidence.compute_explicit_evidence_digest()
            if verified_evidence is not None
            else None
        )
        if self.verified_rating_evidence_digest != expected_evidence:
            raise ValueError("verified_rating_evidence_digest mismatch")
        expected_invalid = (
            source_record.invalid_rating_evidence.invalid_evidence_digest
            if source_record.invalid_rating_evidence is not None
            else None
        )
        if self.invalid_rating_evidence_digest != expected_invalid:
            raise ValueError("invalid_rating_evidence_digest mismatch")
        expected_audit = (
            source_record.claimed_rating_result_audit.audit_digest
            if source_record.claimed_rating_result_audit is not None
            else None
        )
        if self.claimed_rating_result_audit_digest != expected_audit:
            raise ValueError("claimed_rating_result_audit_digest mismatch")
        expected_failure = (
            source_failure_binding.descriptor_binding_digest
            if source_failure_binding is not None
            else None
        )
        if self.evaluation_failure_digest != expected_failure:
            raise ValueError("evaluation_failure_digest mismatch")
        # Self-hash integrity
        for v, n in [
            (self.identity_snapshot_digest, "identity"),
            (self.descriptor_digest, "descriptor"),
        ]:
            if not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"invalid {n} digest")
        for v, n in [
            (self.candidate_evaluation_identity_digest, "cei"),
            (self.verified_rating_evidence_digest, "evidence"),
            (self.invalid_rating_evidence_digest, "invalid"),
            (self.claimed_rating_result_audit_digest, "audit"),
            (self.evaluation_failure_digest, "failure"),
        ]:
            if v is not None and not self.DIGEST_PATTERN.match(v):
                raise ValueError(f"invalid {n} digest")
        payload = {
            "source_qualified_candidate_id": self.source_qualified_candidate_id,
            "evaluation_order_index": self.evaluation_order_index,
            "candidate_evaluation_state": self.candidate_evaluation_state.value,
            "identity_snapshot_digest": self.identity_snapshot_digest,
            "candidate_evaluation_identity_digest": self.candidate_evaluation_identity_digest,
            "verified_rating_evidence_digest": self.verified_rating_evidence_digest,
            "invalid_rating_evidence_digest": self.invalid_rating_evidence_digest,
            "claimed_rating_result_audit_digest": self.claimed_rating_result_audit_digest,
            "evaluation_failure_digest": self.evaluation_failure_digest,
        }
        expected = sha256_digest(payload)
        if self.descriptor_digest != expected:
            raise ValueError("descriptor_digest mismatch")


def build_phase2_source_record_descriptor(
    *,
    source_record: CandidateEvaluationRecord,
    identity_snapshot: Phase2SourceRecordIdentitySnapshot,
    verified_evidence: VerifiedRatingEvidenceSnapshot | None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> Phase2SourceRecordDescriptor:
    verified_evidence_digest = (
        verified_evidence.compute_explicit_evidence_digest()
        if verified_evidence is not None
        else None
    )
    evaluation_failure_digest = (
        source_failure_binding.descriptor_binding_digest
        if source_failure_binding is not None
        else None
    )
    payload = {
        "source_qualified_candidate_id": source_record.source_qualified_candidate_id,
        "evaluation_order_index": source_record.evaluation_order_index,
        "candidate_evaluation_state": source_record.candidate_evaluation_state.value,
        "identity_snapshot_digest": identity_snapshot.identity_snapshot_digest,
        "candidate_evaluation_identity_digest": (
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity is not None
            else None
        ),
        "verified_rating_evidence_digest": verified_evidence_digest,
        "invalid_rating_evidence_digest": (
            source_record.invalid_rating_evidence.invalid_evidence_digest
            if source_record.invalid_rating_evidence is not None
            else None
        ),
        "claimed_rating_result_audit_digest": source_record.claimed_rating_result_audit.audit_digest
        if source_record.claimed_rating_result_audit is not None
        else None,
        "evaluation_failure_digest": evaluation_failure_digest,
    }
    d = sha256_digest(payload)
    return Phase2SourceRecordDescriptor(
        source_qualified_candidate_id=source_record.source_qualified_candidate_id,
        evaluation_order_index=source_record.evaluation_order_index,
        candidate_evaluation_state=source_record.candidate_evaluation_state,
        identity_snapshot_digest=identity_snapshot.identity_snapshot_digest,
        candidate_evaluation_identity_digest=payload["candidate_evaluation_identity_digest"],
        verified_rating_evidence_digest=verified_evidence_digest,
        invalid_rating_evidence_digest=payload["invalid_rating_evidence_digest"],
        claimed_rating_result_audit_digest=payload["claimed_rating_result_audit_digest"],
        evaluation_failure_digest=evaluation_failure_digest,
        descriptor_digest=d,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 8 — Phase 2 constructor matrix
# ═══════════════════════════════════════════════════════════════════════════


@dataclasses.dataclass(frozen=True, slots=True)
class ContextValueRule:
    key: str
    value_kind: str
    expected_literal: object | None = None


@dataclasses.dataclass(frozen=True, slots=True)
class Phase2RuntimeFailurePathSpec:
    path_id: str
    hash_outcome: VerificationOutcome
    provenance_outcome: VerificationOutcome
    audit_required: bool
    failure_code: ErrorCode
    message_rule: tuple[str, ...]
    context_keys: tuple[str, ...]
    failure_stage: str | None
    owner_kind: str | None
    value_rules: tuple[ContextValueRule, ...]


# Shorthand aliases for PATH_SPECS construction
_NOT_RUN = VerificationOutcome.NOT_RUN
_PASSED = VerificationOutcome.PASSED
_ERROR = VerificationOutcome.ERROR

PATH_SPECS: tuple[Phase2RuntimeFailurePathSpec, ...] = (
    Phase2RuntimeFailurePathSpec(
        "P2-RF-1",
        _NOT_RUN,
        _NOT_RUN,
        True,
        ErrorCode.INVALID_STATE_TRANSITION,
        ("prefix", "Expected exact RatingResult, got "),
        (),
        "evaluation",
        "evaluation",
        (),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-2",
        _ERROR,
        _NOT_RUN,
        True,
        ErrorCode.HASH_MISMATCH,
        ("exact", "Rating result hash verification raised."),
        (),
        "verification",
        "verification_runtime",
        (),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-3",
        _PASSED,
        _ERROR,
        True,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Rating result provenance verification raised."),
        (),
        "verification",
        "verification_runtime",
        (),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-4",
        _PASSED,
        _PASSED,
        True,
        ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to extract trusted evidence"),
        (),
        "verification",
        "verification_runtime",
        (),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-5",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        (
            "failure_stage",
            "owner_kind",
            "owner_id",
            "context_key",
            "context_path_digest",
            "offending_type",
            "failure_kind",
            "safe_marker_digest",
        ),
        "rating_verification",
        "verification_runtime",
        (
            ContextValueRule("failure_stage", "literal", "rating_verification"),
            ContextValueRule("owner_kind", "literal", "verification_runtime"),
            ContextValueRule("context_key", "any"),
            ContextValueRule("context_path_digest", "digest_format"),
            ContextValueRule("offending_type", "any"),
            ContextValueRule("failure_kind", "any"),
            ContextValueRule("safe_marker_digest", "digest_format"),
        ),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-6",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        (
            "failure_stage",
            "owner_kind",
            "owner_id",
            "original_code",
            "context_key",
            "context_path_digest",
            "offending_type",
            "failure_kind",
            "safe_marker_digest",
        ),
        "rating_verification",
        "warning",
        (
            ContextValueRule("failure_stage", "literal", "rating_verification"),
            ContextValueRule("owner_kind", "literal", "warning"),
            ContextValueRule("context_key", "any"),
            ContextValueRule("context_path_digest", "digest_format"),
            ContextValueRule("offending_type", "any"),
            ContextValueRule("failure_kind", "any"),
            ContextValueRule("safe_marker_digest", "digest_format"),
        ),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-7",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        (
            "failure_stage",
            "owner_kind",
            "owner_id",
            "original_code",
            "context_key",
            "context_path_digest",
            "offending_type",
            "failure_kind",
            "safe_marker_digest",
        ),
        "rating_verification",
        "blocker",
        (
            ContextValueRule("failure_stage", "literal", "rating_verification"),
            ContextValueRule("owner_kind", "literal", "blocker"),
            ContextValueRule("context_key", "any"),
            ContextValueRule("context_path_digest", "digest_format"),
            ContextValueRule("offending_type", "any"),
            ContextValueRule("failure_kind", "any"),
            ContextValueRule("safe_marker_digest", "digest_format"),
        ),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-8",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        (
            "failure_stage",
            "owner_kind",
            "owner_id",
            "original_code",
            "context_key",
            "context_path_digest",
            "offending_type",
            "failure_kind",
            "safe_marker_digest",
        ),
        "rating_verification",
        "run_failure",
        (
            ContextValueRule("failure_stage", "literal", "rating_verification"),
            ContextValueRule("owner_kind", "literal", "run_failure"),
            ContextValueRule("context_key", "any"),
            ContextValueRule("context_path_digest", "digest_format"),
            ContextValueRule("offending_type", "any"),
            ContextValueRule("failure_kind", "any"),
            ContextValueRule("safe_marker_digest", "digest_format"),
        ),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-9",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to build candidate evaluation identity"),
        (),
        "verification",
        "verification_runtime",
        (),
    ),
    Phase2RuntimeFailurePathSpec(
        "P2-RF-10",
        _PASSED,
        _PASSED,
        False,
        ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted rating verification failed."),
        (
            "failure_stage",
            "owner_kind",
            "owner_id",
            "offending_type",
            "failure_kind",
            "safe_marker_digest",
        ),
        "rating_verification",
        "verification_runtime",
        (
            ContextValueRule("failure_stage", "literal", "rating_verification"),
            ContextValueRule("owner_kind", "literal", "verification_runtime"),
            ContextValueRule("offending_type", "any"),
            ContextValueRule("failure_kind", "any"),
            ContextValueRule("safe_marker_digest", "digest_format"),
        ),
    ),
)


def match_phase2_runtime_failure_path(record: CandidateEvaluationRecord) -> str:
    if record.candidate_evaluation_state != CandidateEvaluationState.RUNTIME_FAILED:
        raise ValueError("not RUNTIME_FAILED")
    matches = []
    for spec in PATH_SPECS:
        if record.hash_verification_outcome != spec.hash_outcome:
            continue
        if record.provenance_verification_outcome != spec.provenance_outcome:
            continue
        has_audit = record.claimed_rating_result_audit is not None
        if has_audit != spec.audit_required:
            continue
        if record.evaluation_failure is None:
            continue
        if record.evaluation_failure.code != spec.failure_code:
            continue
        kind, template = spec.message_rule
        if kind == "exact":
            if record.evaluation_failure.message != template:
                continue
        elif kind == "prefix" and not record.evaluation_failure.message.startswith(template):
            continue
        if spec.context_keys:
            ctx_keys = tuple(p[0] for p in record.evaluation_failure.context)
            if ctx_keys != spec.context_keys:
                continue
        if spec.value_rules:
            value_ok = True
            ctx_map = dict(record.evaluation_failure.context)
            for vr in spec.value_rules:
                val = ctx_map.get(vr.key, "")
                if (vr.value_kind == "literal" and val != vr.expected_literal) or (
                    vr.value_kind == "digest_format"
                    and not re.fullmatch(r"^sha256:[0-9a-f]{64}$", str(val))
                ):
                    value_ok = False
            if not value_ok:
                continue
        matches.append(spec.path_id)
    if len(matches) == 0:
        raise ValueError("no matching path")
    if len(matches) > 1:
        raise ValueError(f"multiple matches: {matches}")
    return matches[0]


# ═══════════════════════════════════════════════════════════════════════════
# Section 9 — Decimal helpers
# ═══════════════════════════════════════════════════════════════════════════


def canonical_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal:
        raise TypeError("must be Decimal")
    if not value.is_finite():
        raise ValueError("must be finite")
    n = value.normalize()
    return Decimal("0") if n.is_zero() else n


def canonical_decimal_string(value: Decimal) -> str:
    return format(canonical_decimal(value), "f")


def to_canonical_decimal(value: float | int | Decimal) -> Decimal:
    if type(value) is bool:
        raise TypeError("bool not allowed")
    if type(value) is Decimal:
        return canonical_decimal(value)
    if type(value) is int:
        return canonical_decimal(Decimal(value))
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError("must be finite")
        return canonical_decimal(Decimal(str(value)))
    raise TypeError(f"unsupported type: {type(value).__name__}")


def verify_canonical_decimal_string(value: str) -> None:
    parsed = Decimal(value)
    if not parsed.is_finite():
        raise ValueError(f"not finite: {value}")
    if canonical_decimal_string(parsed) != value:
        raise ValueError(f"not canonical: {value}")


# ═══════════════════════════════════════════════════════════════════════════
# Section 10 — Duty, terminal delta-T, strict-stop
# ═══════════════════════════════════════════════════════════════════════════

# Duty and terminal delta-T equations (reference code for the classifier):
#
#   required = to_canonical_decimal(sizing.required_duty_w)
#   abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)
#   rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)
#   duty_tol = max(abs_tol, rel_tol * abs(required))
#   duty_satisfied = abs(heat - required) <= duty_tol
#
#   if fa == "parallel":
#       dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
#   else:
#       dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
#   delta_t_satisfied = min(dt1, dt2) >= to_canonical_decimal(sizing.minimum_terminal_delta_t)


def _find_stop_index(ei: Phase3EvaluationInput) -> int | None:  # noqa: F821
    for i, r in enumerate(ei.evaluation_records):
        if r.candidate_evaluation_state in (
            CandidateEvaluationState.INTEGRITY_INVALID,
            CandidateEvaluationState.RUNTIME_FAILED,
        ):
            return i
    return None


def derive_termination_status(
    evaluation_input: Phase3EvaluationInput,  # noqa: F821
) -> TerminationStatus:
    stop_index = _find_stop_index(evaluation_input)
    return TerminationStatus.PARTIAL if stop_index is not None else TerminationStatus.COMPLETE


# ═══════════════════════════════════════════════════════════════════════════
# Section 11 — Count equations
# ═══════════════════════════════════════════════════════════════════════════


def _verify_all_counts(
    result: object,
    ei: Phase3EvaluationInput,  # noqa: F821, UP037
    dispositions: tuple,
) -> None:
    """Verify all Phase 2 and Phase 3 counts against source records and dispositions.

    *result* is an OptimizationResult-like object with count fields.
    *ei* is the Phase3EvaluationInput.
    *dispositions* is a tuple of disposition objects (each with .disposition
    and .source_candidate_evaluation_state attributes).
    """
    recs = ei.evaluation_records
    p2_v = sum(1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.VERIFIED)
    p2_ii = sum(
        1
        for r in recs
        if r.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID
    )
    p2_rf = sum(
        1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
    )
    p2_u = sum(
        1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED
    )
    for n, a, e in [
        ("p2_verified", result.phase2_verified_record_count, p2_v),
        ("p2_integrity", result.phase2_integrity_invalid_record_count, p2_ii),
        ("p2_runtime", result.phase2_runtime_failed_record_count, p2_rf),
        ("p2_unevaluated", result.phase2_unevaluated_record_count, p2_u),
    ]:
        if a != e:
            raise ValueError(f"{n}: {a} != {e}")
    f = sum(1 for d in dispositions if d.disposition is Phase3Disposition.FEASIBLE)
    inf = sum(1 for d in dispositions if d.disposition is Phase3Disposition.INFEASIBLE)
    pm = sum(
        1 for d in dispositions if d.disposition is Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
    )
    intf = sum(1 for d in dispositions if d.disposition is Phase3Disposition.INTEGRITY_FAILED)
    pf = sum(1 for d in dispositions if d.disposition is Phase3Disposition.PROVENANCE_FAILED)
    rf = sum(1 for d in dispositions if d.disposition is Phase3Disposition.RUNTIME_FAILED)
    u = sum(1 for d in dispositions if d.disposition is Phase3Disposition.UNEVALUATED)
    for n, a, e in [
        ("feasible", result.feasible_candidate_count, f),
        ("infeasible", result.infeasible_candidate_count, inf),
        ("provider_mismatch", result.provider_mismatch_count, pm),
        ("integrity_failed", result.integrity_failed_count, intf),
        ("provenance_failed", result.provenance_failed_count, pf),
        ("runtime_failed", result.runtime_failed_count, rf),
        ("unevaluated", result.unevaluated_count, u),
    ]:
        if a != e:
            raise ValueError(f"{n}: {a} != {e}")
    rf_v = sum(
        1
        for d in dispositions
        if d.disposition is Phase3Disposition.RUNTIME_FAILED
        and d.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED
    )
    rf_rf = sum(
        1
        for d in dispositions
        if d.disposition is Phase3Disposition.RUNTIME_FAILED
        and d.source_candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED
    )
    if result.runtime_failed_from_phase2_verified_count != rf_v:
        raise ValueError("rf_from_verified mismatch")
    if result.runtime_failed_from_phase2_runtime_failed_count != rf_rf:
        raise ValueError("rf_from_rf mismatch")
