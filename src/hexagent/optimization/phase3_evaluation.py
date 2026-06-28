"""
TASK-009 Phase 3 — Evaluation input, candidate classification, preparation,
and candidate disposition record.

Sections 12-15 of the Phase 3 design contract.
"""

from __future__ import annotations

import re
import typing
from enum import StrEnum
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, model_validator

from hexagent.core.canonical import sha256_digest
from hexagent.optimization.context import SizingRequestIdentity
from hexagent.optimization.evaluation import (
    CandidateEvaluationRecord,
    CandidateEvaluationState,
    VerificationOutcome,
    VerifiedRatingEvidenceSnapshot,
)
from hexagent.optimization.identities import (
    ManufacturableCandidate,
    MaterializationResult,
)
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
    Phase3PreparationStatus,
    Phase3RunFailureDescriptorBinding,
    verify_canonical_decimal_string,
)

# ── Shorthand aliases for enum members used verbatim in contract code ──────

# CandidateEvaluationState
VERIFIED = CandidateEvaluationState.VERIFIED
INTEGRITY_INVALID = CandidateEvaluationState.INTEGRITY_INVALID
RUNTIME_FAILED = CandidateEvaluationState.RUNTIME_FAILED
UNEVALUATED = CandidateEvaluationState.UNEVALUATED

# VerificationOutcome
PASSED = VerificationOutcome.PASSED
FAILED = VerificationOutcome.FAILED
NOT_RUN = VerificationOutcome.NOT_RUN
ERROR = VerificationOutcome.ERROR

# Phase3Disposition
FEASIBLE = Phase3Disposition.FEASIBLE
INFEASIBLE = Phase3Disposition.INFEASIBLE
PROVIDER_IDENTITY_MISMATCH = Phase3Disposition.PROVIDER_IDENTITY_MISMATCH
PROVENANCE_FAILED = Phase3Disposition.PROVENANCE_FAILED  # noqa: F811 – shadows func below; use Phase3Disposition. prefix
PHASE2_RUNTIME_FAILED = (
    FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED
)  # from FeasibilityDiagnosticKey
PHASE3_RUNTIME_FAILED = FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED

# FeasibilityDiagnosticKey
NONE = FeasibilityDiagnosticKey.NONE
PROVIDER_IDENTITY_MISMATCH_DIAG = FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH
RATING_BLOCKED = FeasibilityDiagnosticKey.RATING_BLOCKED
RATING_FAILED = FeasibilityDiagnosticKey.RATING_FAILED
DUTY_SHORTFALL = FeasibilityDiagnosticKey.DUTY_SHORTFALL
TERMINAL_DELTA_T_INADEQUATE = FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE

# FailureOrigin
NONE_ORIGIN = FailureOrigin.NONE
PHASE2_EVALUATION = FailureOrigin.PHASE2_EVALUATION
PHASE3_CLASSIFICATION = FailureOrigin.PHASE3_CLASSIFICATION

# Phase3PreparationFailureStage
SOURCE_BINDING_FS = Phase3PreparationFailureStage.SOURCE_BINDING
CLASSIFICATION_INPUT_FS = Phase3PreparationFailureStage.CLASSIFICATION_INPUT

# Phase3Disposition (re-assign fully qualified for safety)
_INTEGRITY_FAILED = Phase3Disposition.INTEGRITY_FAILED
_PROVENANCE_FAILED = Phase3Disposition.PROVENANCE_FAILED
_RUNTIME_FAILED = Phase3Disposition.RUNTIME_FAILED
_UNEVALUATED = Phase3Disposition.UNEVALUATED


# ═══════════════════════════════════════════════════════════════════════════
# Section 12 — Phase3EvaluationInput
# ═══════════════════════════════════════════════════════════════════════════


def _evaluation_input_payload(ei: Phase3EvaluationInput) -> dict[str, object]:
    return {
        "schema_version": ei.schema_version,
        "sizing_request_identity_digest": ei.sizing_request_identity_digest,
        "candidate_set_digest": ei.candidate_set_digest,
        "gate_digest": ei.gate_digest,
        "evaluation_record_count": ei.evaluation_record_count,
        "ordered_identity_snapshot_digests": list(ei.ordered_identity_snapshot_digests),
        "ordered_phase2_source_snapshot_digests": list(ei.ordered_phase2_source_snapshot_digests),
        "ordered_phase2_source_record_descriptor_digests": list(
            ei.ordered_phase2_source_record_descriptor_digests
        ),
    }


class Phase3EvaluationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    materialization_result: MaterializationResult
    candidate_set_digest: str
    gate_digest: str
    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int
    identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...]
    complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...]
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...]
    ordered_phase2_source_record_descriptor_digests: tuple[str | None, ...]
    evaluation_input_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1:
            raise ValueError("version must be 1")
        N = self.evaluation_record_count
        if len(self.evaluation_records) != N:
            raise ValueError("count != len(records)")
        if len(self.identity_snapshots) != N:
            raise ValueError("identity_snapshots length != N")
        if len(self.complete_snapshots) != N:
            raise ValueError("complete_snapshots length != N")
        if len(self.ordered_identity_snapshot_digests) != N:
            raise ValueError("ordered_identity_snapshot_digests length != N")
        if len(self.ordered_phase2_source_snapshot_digests) != N:
            raise ValueError("ordered_phase2_source_snapshot_digests length != N")
        if len(self.ordered_phase2_source_record_descriptor_digests) != N:
            raise ValueError("source descriptor digests length != N")
        # Validate identity_snapshots against records
        for i, (rec, isnap) in enumerate(
            zip(self.evaluation_records, self.identity_snapshots, strict=False)
        ):
            if rec.source_qualified_candidate_id != isnap.source_qualified_candidate_id:
                raise ValueError(f"[{i}] identity_snapshot candidate_id mismatch")
            if rec.evaluation_order_index != isnap.evaluation_order_index:
                raise ValueError(f"[{i}] identity_snapshot index mismatch")
            if isnap.identity_snapshot_digest != self.ordered_identity_snapshot_digests[i]:
                raise ValueError(f"[{i}] identity_snapshot digest not in ordered digests")
        # Validate complete_snapshots nullable status matches Phase 2 state
        for i, (rec, cs) in enumerate(
            zip(self.evaluation_records, self.complete_snapshots, strict=False)
        ):
            if rec.candidate_evaluation_state == VERIFIED:
                if cs is None:
                    raise ValueError(f"[{i}] VERIFIED must have complete_snapshot")
                if self.ordered_phase2_source_snapshot_digests[i] is None:
                    raise ValueError(f"[{i}] VERIFIED must have non-None source snapshot digest")
                if self.ordered_phase2_source_snapshot_digests[i] != cs.snapshot_digest:
                    raise ValueError(
                        f"[{i}] source snapshot digest mismatch "
                        f"vs complete_snapshot.snapshot_digest"
                    )
            else:
                if cs is not None:
                    raise ValueError(f"[{i}] non-VERIFIED must have None snapshot")
                if self.ordered_phase2_source_snapshot_digests[i] is not None:
                    raise ValueError(f"[{i}] non-VERIFIED must have None source snapshot digest")
                if self.ordered_phase2_source_record_descriptor_digests[i] is not None:
                    raise ValueError(f"[{i}] non-VERIFIED must have None descriptor digest")
        # Check first strict-stop position
        for i, r in enumerate(self.evaluation_records):
            if r.candidate_evaluation_state in (INTEGRITY_INVALID, RUNTIME_FAILED):
                # After stop index, only UNEVALUATED is legal
                for j in range(i + 1, N):
                    if self.evaluation_records[j].candidate_evaluation_state != UNEVALUATED:
                        raise ValueError(
                            f"[{j}] after stop index: must be UNEVALUATED, "
                            f"got {self.evaluation_records[j].candidate_evaluation_state}"
                        )
                break
        expected = sha256_digest(_evaluation_input_payload(self))
        if self.evaluation_input_digest != expected:
            raise ValueError("evaluation_input_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        sizing_request: SizingRequest,
        candidates: tuple[ManufacturableCandidate, ...],
        source_records: tuple[CandidateEvaluationRecord, ...],
        phase2_source_record_descriptors: tuple[Phase2SourceRecordDescriptor | None, ...],
        warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
        blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
        source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
        evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    ) -> None:
        # 1) Length gates
        N = self.evaluation_record_count
        if len(candidates) != N:
            raise ValueError("candidates count != N")
        if len(source_records) != N:
            raise ValueError("source_records count != N")
        if len(self.identity_snapshots) != N:
            raise ValueError("identity_snapshots length != N")
        if len(self.complete_snapshots) != N:
            raise ValueError("complete_snapshots length != N")
        if len(self.ordered_phase2_source_snapshot_digests) != N:
            raise ValueError("ordered_phase2_source_snapshot_digests length != N")
        if len(phase2_source_record_descriptors) != N:
            raise ValueError("descriptors length != N")
        if len(warning_binding_tuples) != N:
            raise ValueError("warning_binding_tuples length != N")
        if len(blocker_binding_tuples) != N:
            raise ValueError("blocker_binding_tuples length != N")
        if len(source_failure_bindings) != N:
            raise ValueError("source_failure_bindings length != N")
        if len(evidence_failure_bindings) != N:
            raise ValueError("evidence_failure_bindings length != N")
        # 2) Materialization result replay
        m = self.materialization_result
        m.verify_or_raise()
        # 3) Sizing request identity
        if (
            self.sizing_request_identity_digest
            != self.sizing_request_identity.sizing_request_identity_digest
        ):
            raise ValueError("sizing_request_identity_digest mismatch")
        if (
            self.sizing_request_identity_digest
            != self.sizing_request_identity.sizing_request_identity_digest
        ):
            raise ValueError("sizing_request_identity stored digest mismatch")
        # 4) Candidate-set & gate digest
        if self.candidate_set_digest != m.candidate_set.candidate_set_digest:
            raise ValueError("candidate_set_digest mismatch")
        if self.gate_digest != m.sizing_gate.gate_digest:
            raise ValueError("gate_digest mismatch")
        # 5) Candidate ID/index alignment
        for i, (rec, cand) in enumerate(zip(self.evaluation_records, candidates, strict=False)):
            if rec.source_qualified_candidate_id != cand.source_qualified_candidate_id:
                raise ValueError(f"[{i}] candidate_id mismatch")
            if rec.evaluation_order_index != i:
                raise ValueError(f"[{i}] index mismatch")
        # 6) Identity snapshot — full field consistency via authoritative verifier
        for i, (rec, isnap) in enumerate(
            zip(self.evaluation_records, self.identity_snapshots, strict=False)
        ):
            isnap.verify_or_raise(source_record=rec)
            if isnap.identity_snapshot_digest != self.ordered_identity_snapshot_digests[i]:
                raise ValueError(f"[{i}] identity_snapshot_digest != ordered digest")
        # 7) Complete snapshot — verify via authoritative verifier
        for i, (_rec, cs) in enumerate(zip(source_records, self.complete_snapshots, strict=False)):
            if cs is None:
                if rec.candidate_evaluation_state == VERIFIED:
                    raise ValueError(f"[{i}] VERIFIED must have complete_snapshot")
                continue
            if rec.candidate_evaluation_state != VERIFIED:
                raise ValueError(f"[{i}] non-VERIFIED must not have complete_snapshot")
            desc_i = phase2_source_record_descriptors[i]
            if desc_i is None:
                raise ValueError(f"[{i}] VERIFIED must have source_record_descriptor")
            cs.verify_or_raise(
                source_record=rec,
                identity_snapshot=self.identity_snapshots[i],
                source_record_descriptor=desc_i,
                verified_evidence=rec.verified_rating_evidence,
                warning_descriptor_bindings=warning_binding_tuples[i],
                blocker_descriptor_bindings=blocker_binding_tuples[i],
                source_failure_binding=source_failure_bindings[i],
                evidence_failure_binding=evidence_failure_bindings[i],
            )
            # Validate ordered_phase2_source_snapshot_digests against complete_snapshot
            if cs.snapshot_digest != self.ordered_phase2_source_snapshot_digests[i]:
                raise ValueError(f"[{i}] source snapshot digest mismatch vs ordered digest")
        # Also validate non-VERIFIED indices have None digest
        for i, (_rec, cs) in enumerate(zip(source_records, self.complete_snapshots, strict=False)):
            if cs is None and self.ordered_phase2_source_snapshot_digests[i] is not None:
                raise ValueError(f"[{i}] non-VERIFIED must have None source snapshot digest")
        # 8) Ordered digest tuples vs actual artifacts
        for i, d in enumerate(phase2_source_record_descriptors):
            expected_desc_digest = self.ordered_phase2_source_record_descriptor_digests[i]
            if d is None:
                if expected_desc_digest is not None:
                    raise ValueError(
                        f"[{i}] expected None descriptor digest, got {expected_desc_digest}"
                    )
                continue
            if d.descriptor_digest != expected_desc_digest:
                raise ValueError(f"[{i}] descriptor artifact digest mismatch")
        # 9) Replay payload digest
        expected = sha256_digest(_evaluation_input_payload(self))
        if self.evaluation_input_digest != expected:
            raise ValueError("evaluation_input_digest mismatch")


# ═══════════════════════════════════════════════════════════════════════════
# Section 12.1 — Tamper test descriptions (reference only)
# ═══════════════════════════════════════════════════════════════════════════
#
# - TAMPER-12.1: Modify ordered_phase2_source_snapshot_digests[i] to a
#   different valid sha256 digest while keeping complete_snapshots[i]
#   unchanged → _validate() raises "source snapshot digest mismatch vs
#   complete_snapshot.snapshot_digest"
# - TAMPER-12.2: Set ordered_phase2_source_snapshot_digests[i] to None on a
#   VERIFIED index where complete_snapshots[i] is non-None → _validate()
#   raises "VERIFIED must have non-None source snapshot digest"
# - TAMPER-12.3: Set ordered_phase2_source_snapshot_digests[i] to a valid
#   sha256 digest on a non-VERIFIED index → _validate() raises "non-VERIFIED
#   must have None source snapshot digest"
# - TAMPER-12.4: Truncate ordered_phase2_source_snapshot_digests to length
#   N-1 → _validate() raises "ordered_phase2_source_snapshot_digests length
#   != N"
# - TAMPER-12.5: Modify _evaluation_input_payload() to exclude
#   ordered_phase2_source_snapshot_digests → evaluation_input_digest
#   mismatch on replay
# - TAMPER-12.6: In verify_or_raise(), pass
#   ordered_phase2_source_snapshot_digests with wrong length → raises
#   "ordered_phase2_source_snapshot_digests length != N"


# ═══════════════════════════════════════════════════════════════════════════
# Section 13 — Phase3SourceRecordBinding (P0-3)
# ═══════════════════════════════════════════════════════════════════════════


def phase3_source_record_binding_payload_from_values(
    *,
    schema_version: Literal[1] = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    phase2_source_record_descriptor_digest: str,
    verified_rating_evidence_digest: str | None,
    phase2_identity_snapshot_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_binding_digest: str | None,
    evidence_failure_binding_digest: str | None,
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "phase2_source_record_descriptor_digest": phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "phase2_identity_snapshot_digest": phase2_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": source_evaluation_failure_binding_digest,
        "evidence_failure_binding_digest": evidence_failure_binding_digest,
    }


def build_phase3_source_record_binding(
    *,
    schema_version: Literal[1] = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    phase2_source_record_descriptor_digest: str,
    verified_rating_evidence_digest: str | None,
    phase2_identity_snapshot_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_binding_digest: str | None,
    evidence_failure_binding_digest: str | None,
) -> Phase3SourceRecordBinding:
    payload = phase3_source_record_binding_payload_from_values(
        schema_version=schema_version,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        phase2_identity_snapshot_digest=phase2_identity_snapshot_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        evidence_failure_binding_digest=evidence_failure_binding_digest,
    )
    bd = sha256_digest(payload)
    return Phase3SourceRecordBinding(
        schema_version=schema_version,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        phase2_identity_snapshot_digest=phase2_identity_snapshot_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        evidence_failure_binding_digest=evidence_failure_binding_digest,
        binding_digest=bd,
    )


class Phase3SourceRecordBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    phase2_source_record_descriptor_digest: str
    verified_rating_evidence_digest: str | None
    phase2_identity_snapshot_digest: str
    warning_descriptor_binding_digests: tuple[str, ...]
    blocker_descriptor_binding_digests: tuple[str, ...]
    source_evaluation_failure_binding_digest: str | None
    evidence_failure_binding_digest: str | None
    binding_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.phase2_source_record_descriptor_digest):
            raise ValueError("invalid desc digest")
        if not self.DIGEST_PATTERN.match(self.phase2_identity_snapshot_digest):
            raise ValueError("invalid identity digest")
        if self.verified_rating_evidence_digest is not None and not self.DIGEST_PATTERN.match(
            self.verified_rating_evidence_digest
        ):
            raise ValueError("invalid evidence digest")
        if (
            self.source_evaluation_failure_binding_digest is not None
            and not self.DIGEST_PATTERN.match(self.source_evaluation_failure_binding_digest)
        ):
            raise ValueError("invalid source failure binding")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError("invalid warning binding")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError("invalid blocker binding")
        if self.evidence_failure_binding_digest is not None and not self.DIGEST_PATTERN.match(
            self.evidence_failure_binding_digest
        ):
            raise ValueError("invalid evidence failure binding digest")
        payload = phase3_source_record_binding_payload_from_values(
            schema_version=self.schema_version,
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest=self.phase2_identity_snapshot_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest,
        )
        if self.binding_digest != sha256_digest(payload):
            raise ValueError("binding_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        identity_snapshot: Phase2SourceRecordIdentitySnapshot,
        complete_snapshot: Phase2SourceRecordSnapshot,
        source_record_descriptor: Phase2SourceRecordDescriptor,
        verified_evidence: VerifiedRatingEvidenceSnapshot | None,
        warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
        blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
        source_failure_binding: Phase3RunFailureDescriptorBinding | None,
        evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
    ) -> None:
        # 0) Delegate to descriptor authority
        source_record_descriptor.verify_or_raise(
            source_record=source_record,
            identity_snapshot=identity_snapshot,
            verified_evidence=verified_evidence,
            source_failure_binding=source_failure_binding,
        )
        # 1) Candidate ID / index cross-validated with descriptor
        if (
            self.source_qualified_candidate_id
            != source_record_descriptor.source_qualified_candidate_id
        ):
            raise ValueError("candidate_id vs descriptor mismatch")
        if self.evaluation_order_index != source_record_descriptor.evaluation_order_index:
            raise ValueError("evaluation_index vs descriptor mismatch")
        if (
            self.phase2_source_record_descriptor_digest
            != source_record_descriptor.descriptor_digest
        ):
            raise ValueError("stored descriptor_digest != descriptor.descriptor_digest")
        # 2) Identity snapshot check
        if self.phase2_identity_snapshot_digest != identity_snapshot.identity_snapshot_digest:
            raise ValueError("identity_snapshot_digest mismatch")
        if self.source_qualified_candidate_id != identity_snapshot.source_qualified_candidate_id:
            raise ValueError("candidate_id vs identity_snapshot mismatch")
        # 3) Complete snapshot fields cross-check
        if self.source_qualified_candidate_id != complete_snapshot.source_qualified_candidate_id:
            raise ValueError("candidate_id vs complete_snapshot mismatch")
        if self.evaluation_order_index != complete_snapshot.evaluation_order_index:
            raise ValueError("evaluation_index vs complete_snapshot mismatch")
        # 4) Verified evidence digest cross-check
        expected_ve = (
            verified_evidence.compute_explicit_evidence_digest()
            if verified_evidence is not None
            else None
        )
        if self.verified_rating_evidence_digest != expected_ve:
            raise ValueError("verified_rating_evidence_digest mismatch")
        # 5) Warning/blocker bindings
        if len(self.warning_descriptor_binding_digests) != len(warning_bindings):
            raise ValueError("warning_binding_digests length mismatch")
        for actual_d, expected in zip(
            self.warning_descriptor_binding_digests, warning_bindings, strict=False
        ):
            if actual_d != expected.descriptor_binding_digest:
                raise ValueError("warning_binding_digest mismatch")
        if len(self.blocker_descriptor_binding_digests) != len(blocker_bindings):
            raise ValueError("blocker_binding_digests length mismatch")
        for actual_d, expected in zip(
            self.blocker_descriptor_binding_digests, blocker_bindings, strict=False
        ):
            if actual_d != expected.descriptor_binding_digest:
                raise ValueError("blocker_binding_digest mismatch")
        # 6) Failure bindings
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
        # 7) Self-hash integrity
        payload = phase3_source_record_binding_payload_from_values(
            schema_version=self.schema_version,
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest=self.phase2_identity_snapshot_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest,
        )
        if self.binding_digest != sha256_digest(payload):
            raise ValueError("binding_digest mismatch")


# ═══════════════════════════════════════════════════════════════════════════
# Section 14 — Phase3CandidateClassificationInput and PreparationResult
# ═══════════════════════════════════════════════════════════════════════════


def _classification_input_payload(cin: Phase3CandidateClassificationInput) -> dict[str, object]:
    return {
        "schema_version": cin.schema_version,
        "source_identity_record_descriptor_digest": cin.source_identity_record_descriptor_digest,
        "source_record_descriptor_digest": cin.source_record_descriptor_digest,
        "materialized_candidate_digest": cin.materialized_candidate.source_qualified_candidate_id,
        "sizing_request_identity_digest": cin.sizing_request_identity_digest,
        "identity_snapshot_digest": cin.evidence_binding.phase2_identity_snapshot_digest,
        "source_binding_digest": cin.evidence_binding.binding_digest,
        "verified_rating_evidence_digest": cin.verified_rating_evidence_digest,
    }


class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_record: CandidateEvaluationRecord
    source_identity_record_descriptor_digest: str
    source_record_descriptor_digest: str | None
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    evidence_binding: Phase3SourceRecordBinding
    verified_rating_evidence_digest: str | None
    classification_input_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if (
            self.sizing_request_identity_digest
            != self.sizing_request_identity.sizing_request_identity_digest
        ):
            raise ValueError("sizing digest mismatch")
        if (
            self.source_record.source_qualified_candidate_id
            != self.materialized_candidate.source_qualified_candidate_id
        ):
            raise ValueError("candidate_id mismatch")
        if (
            self.source_record.evaluation_order_index
            != self.materialized_candidate.evaluation_order_index
        ):
            raise ValueError("evaluation index mismatch")
        expected = sha256_digest(_classification_input_payload(self))
        if self.classification_input_digest != expected:
            raise ValueError("classification_input_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        identity_snapshot: Phase2SourceRecordIdentitySnapshot,
        complete_snapshot: Phase2SourceRecordSnapshot,
        source_record_descriptor: Phase2SourceRecordDescriptor,
        source_binding: Phase3SourceRecordBinding,
        sizing_request: SizingRequest,
        candidate: ManufacturableCandidate,
    ) -> None:
        """Authoritative verifier with independent authority params."""
        # 1) Source record full-equality cross-validation — all frozen fields,
        #    not just ID/index/state. Covers rating_status, provider outcomes,
        #    verified/invalid evidence, failure, and strict-stop state.
        if self.source_record != source_record:
            raise ValueError("source_record full equality mismatch")
        # 2) Identity snapshot digest cross-check
        if (
            self.source_identity_record_descriptor_digest
            != identity_snapshot.identity_snapshot_digest
        ):
            raise ValueError(
                "source_identity_record_descriptor_digest mismatch vs identity_snapshot"
            )
        # 3) Source record descriptor digest cross-check vs complete_snapshot
        expected_srd = complete_snapshot.phase2_source_record_descriptor_digest
        if self.source_record_descriptor_digest != expected_srd:
            raise ValueError("source_record_descriptor_digest mismatch vs complete_snapshot")
        # 3b) Source record descriptor digest cross-check vs source_record_descriptor
        if self.source_record_descriptor_digest != source_record_descriptor.descriptor_digest:
            raise ValueError(
                "source_record_descriptor_digest mismatch vs "
                "source_record_descriptor.descriptor_digest"
            )
        # 4) Sizing request identity
        if (
            self.sizing_request_identity_digest
            != self.sizing_request_identity.sizing_request_identity_digest
        ):
            raise ValueError("sizing_request_identity_digest mismatch")
        if (
            self.sizing_request_identity_digest
            != self.sizing_request_identity.sizing_request_identity_digest
        ):
            raise ValueError("sizing_request_identity stored digest mismatch")
        # 5) Evidence binding cross-check
        if self.evidence_binding.binding_digest != source_binding.binding_digest:
            raise ValueError("evidence_binding binding_digest mismatch vs source_binding")
        if (
            self.evidence_binding.phase2_identity_snapshot_digest
            != identity_snapshot.identity_snapshot_digest
        ):
            raise ValueError("evidence_binding identity_snapshot_digest mismatch")
        # 6) Verified rating evidence digest
        expected_ve = (
            source_record.verified_rating_evidence.compute_explicit_evidence_digest()
            if source_record.verified_rating_evidence is not None
            else None
        )
        if self.verified_rating_evidence_digest != expected_ve:
            raise ValueError("verified_rating_evidence_digest mismatch")
        # 7) Materialized candidate full-equality cross-validation — all frozen
        #    fields (geometry, material, catalog identity, effective length, etc.),
        #    not just ID/index. Must match the authoritative candidate from EvaluationInput.
        if self.materialized_candidate != candidate:
            raise ValueError("materialized_candidate full equality mismatch")
        # 8) Self-hash
        expected = sha256_digest(_classification_input_payload(self))
        if self.classification_input_digest != expected:
            raise ValueError("classification_input_digest mismatch")


# ═══════════════════════════════════════════════════════════════════════════
# Section 14.2 — StageFieldRequirement and PREPARATION_STAGE_MATRIX
# ═══════════════════════════════════════════════════════════════════════════


class StageFieldRequirement(StrEnum):
    REQUIRED = "required"
    FORBIDDEN = "forbidden"
    OPTIONAL_AUTHENTICATED = "optional_authenticated"


PREPARATION_STAGE_MATRIX: dict[Phase3PreparationFailureStage, dict[str, StageFieldRequirement]] = {
    Phase3PreparationFailureStage.WARNING_DESCRIPTOR: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.FORBIDDEN,
        "classification_input": StageFieldRequirement.FORBIDDEN,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.BLOCKER_DESCRIPTOR: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.FORBIDDEN,
        "classification_input": StageFieldRequirement.FORBIDDEN,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.FAILURE_DESCRIPTOR: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.FORBIDDEN,
        "classification_input": StageFieldRequirement.FORBIDDEN,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.EVIDENCE_DIGEST: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.FORBIDDEN,
        "classification_input": StageFieldRequirement.FORBIDDEN,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.SOURCE_BINDING: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.REQUIRED,
        "classification_input": StageFieldRequirement.FORBIDDEN,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.CLASSIFICATION_INPUT: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.REQUIRED,
        "classification_input": StageFieldRequirement.REQUIRED,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
    Phase3PreparationFailureStage.CLASSIFICATION: {
        "identity_snapshot": StageFieldRequirement.REQUIRED,
        "complete_snapshot": StageFieldRequirement.REQUIRED,
        "source_binding": StageFieldRequirement.REQUIRED,
        "classification_input": StageFieldRequirement.REQUIRED,
        "evidence_failure_binding": StageFieldRequirement.REQUIRED,
        "source_failure_binding": StageFieldRequirement.FORBIDDEN,
        "phase3_failure_binding": StageFieldRequirement.REQUIRED,
    },
}


# ═══════════════════════════════════════════════════════════════════════════
# Section 14.2a — verify_preparation_stage_matrix
# ═══════════════════════════════════════════════════════════════════════════


def verify_preparation_stage_matrix(
    *,
    status: Phase3PreparationStatus,
    failure_stage: Phase3PreparationFailureStage | None,
    artifacts: dict[str, object | None],
    source_candidate_evaluation_state: CandidateEvaluationState,
) -> None:
    """Enforce PREPARATION_STAGE_MATRIX rules on the given artifacts.

    source_candidate_evaluation_state MUST be provided as independent authority.
    READY is only valid for VERIFIED source records.
    FAILED preparation is only valid for VERIFIED source records.
    Non-VERIFIED records (INTEGRITY_INVALID, RUNTIME_FAILED, UNEVALUATED) MUST
    NOT enter the preparation pipeline.
    """
    if source_candidate_evaluation_state is not VERIFIED:
        raise ValueError(
            f"Preparation only valid for VERIFIED source, got {source_candidate_evaluation_state}"
        )
    if status is Phase3PreparationStatus.READY:
        required_ready = [
            "identity_snapshot",
            "complete_snapshot",
            "source_binding",
            "classification_input",
        ]
        forbidden_ready = [
            "evidence_failure_binding",
            "source_failure_binding",
            "phase3_failure_binding",
        ]
        for name in required_ready:
            if artifacts.get(name) is None:
                raise ValueError(f"READY: {name} required")
        for name in forbidden_ready:
            if artifacts.get(name) is not None:
                raise ValueError(f"READY: {name} must be None")
        return
    # FAILED: use matrix
    if failure_stage is None:
        raise ValueError("FAILED: failure_stage required")
    if failure_stage not in PREPARATION_STAGE_MATRIX:
        raise ValueError(f"Unknown failure_stage: {failure_stage}")
    rules = PREPARATION_STAGE_MATRIX[failure_stage]
    for name, rule in rules.items():
        val = artifacts.get(name)
        if rule is StageFieldRequirement.REQUIRED:
            if val is None:
                raise ValueError(f"FAILED/{failure_stage.value}: {name} required")
        elif rule is StageFieldRequirement.FORBIDDEN and val is not None:
            raise ValueError(f"FAILED/{failure_stage.value}: {name} must be None")
        # OPTIONAL_AUTHENTICATED: allow None but validate if present


# ═══════════════════════════════════════════════════════════════════════════
# Section 14.2b — verify_phase3_index_artifact_matrix
# ═══════════════════════════════════════════════════════════════════════════


def verify_phase3_index_artifact_matrix(
    *,
    source_record: CandidateEvaluationRecord,
    identity_snapshot: Phase2SourceRecordIdentitySnapshot | None,
    complete_snapshot: Phase2SourceRecordSnapshot | None,
    source_record_descriptor: Phase2SourceRecordDescriptor | None,
    source_binding: Phase3SourceRecordBinding | None,
    classification_input: Phase3CandidateClassificationInput | None,
    preparation_result: Phase3CandidatePreparationResult | None,
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    phase3_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> None:
    """Full per-index authority gate for source-state artifact matrix.

    Enforced BEFORE any nested verifier calls in both
    build_optimization_result() and verify_optimization_result_or_raise().
    Rejects any forbidden artifact on non-VERIFIED indices.

    For VERIFIED source, delegates to PREPARATION_STAGE_MATRIX via
    preparation_result.status and failure_stage — does NOT unconditionally
    require complete_snapshot (early failure stages have it FORBIDDEN).
    """
    state = source_record.candidate_evaluation_state

    # === VERIFIED ===
    if state == VERIFIED:
        if preparation_result is None:
            raise ValueError("VERIFIED: preparation_result REQUIRED")
        if source_record_descriptor is None:
            raise ValueError("VERIFIED: source_record_descriptor REQUIRED")
        if source_failure_binding is not None:
            raise ValueError("VERIFIED: source_failure_binding FORBIDDEN")
        # Build artifact dict and delegate to authoritative preparation-stage matrix
        artifacts: dict[str, object | None] = {
            "identity_snapshot": identity_snapshot,
            "complete_snapshot": complete_snapshot,
            "source_binding": source_binding,
            "classification_input": classification_input,
            "evidence_failure_binding": evidence_failure_binding,
            "source_failure_binding": source_failure_binding,
            "phase3_failure_binding": phase3_failure_binding,
        }
        verify_preparation_stage_matrix(
            status=preparation_result.status,
            failure_stage=preparation_result.failure_stage,
            artifacts=artifacts,
            source_candidate_evaluation_state=state,
        )
        return

    # === INTEGRITY_INVALID === (maps to INTEGRITY_FAILED or PROVENANCE_FAILED)
    if state == INTEGRITY_INVALID:
        if complete_snapshot is not None:
            raise ValueError("INTEGRITY_INVALID: complete_snapshot FORBIDDEN")
        if source_record_descriptor is not None:
            raise ValueError("INTEGRITY_INVALID: source_record_descriptor FORBIDDEN")
        if source_binding is not None:
            raise ValueError("INTEGRITY_INVALID: source_binding FORBIDDEN")
        if classification_input is not None:
            raise ValueError("INTEGRITY_INVALID: classification_input FORBIDDEN")
        if preparation_result is not None:
            raise ValueError("INTEGRITY_INVALID: preparation_result FORBIDDEN")
        if evidence_failure_binding is not None:
            raise ValueError("INTEGRITY_INVALID: evidence_failure_binding FORBIDDEN")
        if source_failure_binding is not None:
            raise ValueError("INTEGRITY_INVALID: source_failure_binding FORBIDDEN")
        if phase3_failure_binding is not None:
            raise ValueError("INTEGRITY_INVALID: phase3_failure_binding FORBIDDEN")
        return

    # === RUNTIME_FAILED ===
    if state == RUNTIME_FAILED:
        if complete_snapshot is not None:
            raise ValueError("RUNTIME_FAILED: complete_snapshot FORBIDDEN")
        if source_record_descriptor is not None:
            raise ValueError("RUNTIME_FAILED: source_record_descriptor FORBIDDEN")
        if source_binding is not None:
            raise ValueError("RUNTIME_FAILED: source_binding FORBIDDEN")
        if classification_input is not None:
            raise ValueError("RUNTIME_FAILED: classification_input FORBIDDEN")
        if preparation_result is not None:
            raise ValueError("RUNTIME_FAILED: preparation_result FORBIDDEN")
        if evidence_failure_binding is not None:
            raise ValueError("RUNTIME_FAILED: evidence_failure_binding FORBIDDEN")
        if source_failure_binding is None:
            raise ValueError("RUNTIME_FAILED: source_failure_binding REQUIRED")
        if phase3_failure_binding is not None:
            raise ValueError("RUNTIME_FAILED: phase3_failure_binding FORBIDDEN")
        return

    # === UNEVALUATED ===
    if state == UNEVALUATED:
        if complete_snapshot is not None:
            raise ValueError("UNEVALUATED: complete_snapshot FORBIDDEN")
        if source_record_descriptor is not None:
            raise ValueError("UNEVALUATED: source_record_descriptor FORBIDDEN")
        if source_binding is not None:
            raise ValueError("UNEVALUATED: source_binding FORBIDDEN")
        if classification_input is not None:
            raise ValueError("UNEVALUATED: classification_input FORBIDDEN")
        if preparation_result is not None:
            raise ValueError("UNEVALUATED: preparation_result FORBIDDEN")
        if evidence_failure_binding is not None:
            raise ValueError("UNEVALUATED: evidence_failure_binding FORBIDDEN")
        if source_failure_binding is not None:
            raise ValueError("UNEVALUATED: source_failure_binding FORBIDDEN")
        if phase3_failure_binding is not None:
            raise ValueError("UNEVALUATED: phase3_failure_binding FORBIDDEN")
        return

    raise ValueError(f"Unknown source state: {state}")


# ═══════════════════════════════════════════════════════════════════════════
# Section 14.3 — Phase3CandidatePreparationResult
# ═══════════════════════════════════════════════════════════════════════════


def _prep_result_payload(r: Phase3CandidatePreparationResult) -> dict[str, object]:
    return {
        "schema_version": r.schema_version,
        "status": r.status.value,
        "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "evaluation_order_index": r.evaluation_order_index,
        "identity_snapshot_digest": r.identity_snapshot_digest,
        "complete_snapshot_digest": r.complete_snapshot_digest,
        "source_binding_digest": r.source_binding_digest,
        "classification_input_digest": r.classification_input_digest,
        "evidence_failure_binding_digest": r.evidence_failure_binding_digest,
        "source_failure_binding_digest": r.source_failure_binding_digest,
        "phase3_failure_binding_digest": r.phase3_failure_binding_digest,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None,
    }


class Phase3CandidatePreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    source_qualified_candidate_id: str
    evaluation_order_index: int
    identity_snapshot_digest: str
    complete_snapshot_digest: str | None = None
    source_binding_digest: str | None = None
    classification_input_digest: str | None = None
    evidence_failure_binding_digest: str | None = None
    source_failure_binding_digest: str | None = None
    phase3_failure_binding_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None
    classification_input: Phase3CandidateClassificationInput | None = None
    identity_snapshot: Phase2SourceRecordIdentitySnapshot | None = None
    complete_snapshot: Phase2SourceRecordSnapshot | None = None
    source_binding: Phase3SourceRecordBinding | None = None
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None = None
    source_failure_binding: Phase3RunFailureDescriptorBinding | None = None
    phase3_failure_binding: Phase3RunFailureDescriptorBinding | None = None
    preparation_result_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be ≥ 0")
        # 0) Preparation gate: only VERIFIED source records enter preparation
        if (
            self.identity_snapshot is not None
            and self.identity_snapshot.candidate_evaluation_state is not VERIFIED
        ):
            raise ValueError(
                f"Preparation only valid for VERIFIED source, "
                f"got {self.identity_snapshot.candidate_evaluation_state}"
            )
        # 1) Matrix enforcement
        artifacts: dict[str, object | None] = {
            "identity_snapshot": self.identity_snapshot,
            "complete_snapshot": self.complete_snapshot,
            "source_binding": self.source_binding,
            "classification_input": self.classification_input,
            "evidence_failure_binding": self.evidence_failure_binding,
            "source_failure_binding": self.source_failure_binding,
            "phase3_failure_binding": self.phase3_failure_binding,
        }
        source_eval_state = (
            self.identity_snapshot.candidate_evaluation_state
            if self.identity_snapshot is not None
            else None
        )
        if source_eval_state is None:
            raise ValueError("identity_snapshot required for preparation result")
        verify_preparation_stage_matrix(
            status=self.status,
            failure_stage=self.failure_stage,
            artifacts=artifacts,
            source_candidate_evaluation_state=source_eval_state,
        )
        # 2) Validate digest fields against nested artifacts (compare, don't assign — frozen model)
        expected_id_digest = (
            self.identity_snapshot.identity_snapshot_digest
            if self.identity_snapshot is not None
            else None
        )
        if self.identity_snapshot_digest != expected_id_digest:
            raise ValueError("identity_snapshot_digest mismatch")
        expected_cs_digest = (
            self.complete_snapshot.snapshot_digest if self.complete_snapshot is not None else None
        )
        if self.complete_snapshot_digest != expected_cs_digest:
            raise ValueError("complete_snapshot_digest mismatch")
        expected_sb_digest = (
            self.source_binding.binding_digest if self.source_binding is not None else None
        )
        if self.source_binding_digest != expected_sb_digest:
            raise ValueError("source_binding_digest mismatch")
        expected_cin_digest = (
            self.classification_input.classification_input_digest
            if self.classification_input is not None
            else None
        )
        if self.classification_input_digest != expected_cin_digest:
            raise ValueError("classification_input_digest mismatch")
        expected_efb_digest = (
            self.evidence_failure_binding.descriptor_binding_digest
            if self.evidence_failure_binding is not None
            else None
        )
        if self.evidence_failure_binding_digest != expected_efb_digest:
            raise ValueError("evidence_failure_binding_digest mismatch")
        expected_sfb_digest = (
            self.source_failure_binding.descriptor_binding_digest
            if self.source_failure_binding is not None
            else None
        )
        if self.source_failure_binding_digest != expected_sfb_digest:
            raise ValueError("source_failure_binding_digest mismatch")
        expected_p3fb_digest = (
            self.phase3_failure_binding.descriptor_binding_digest
            if self.phase3_failure_binding is not None
            else None
        )
        if self.phase3_failure_binding_digest != expected_p3fb_digest:
            raise ValueError("phase3_failure_binding_digest mismatch")
        # 3) Status-specific checks
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None:
                raise ValueError("READY: cin required")
            if self.complete_snapshot is None:
                raise ValueError("READY: complete_snapshot required")
            if self.source_binding is None:
                raise ValueError("READY: source_binding required")
            if self.identity_snapshot is None:
                raise ValueError("READY: identity_snapshot required")
            if self.evidence_failure_binding_digest is not None:
                raise ValueError("READY: no evidence failure")
            if self.source_failure_binding_digest is not None:
                raise ValueError("READY: no source failure")
            if self.phase3_failure_binding_digest is not None:
                raise ValueError("READY: no phase3 failure")
            if self.failure_stage is not None:
                raise ValueError("READY: no failure_stage")
        else:
            if self.phase3_failure_binding is None:
                raise ValueError("FAILED: failure_binding required")
            if self.failure_stage is None:
                raise ValueError("FAILED: failure_stage required")
            # classification_input presence controlled by PREPARATION_STAGE_MATRIX
            if self.phase3_failure_binding_digest is None:
                raise ValueError("FAILED: failure_binding_digest required")
        expected = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected:
            raise ValueError("preparation_result_digest mismatch")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        identity_snapshot: Phase2SourceRecordIdentitySnapshot,
        complete_snapshot: Phase2SourceRecordSnapshot | None,
        source_binding: Phase3SourceRecordBinding | None,
        classification_input: Phase3CandidateClassificationInput | None,
        evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
        source_failure_binding: Phase3RunFailureDescriptorBinding | None,
        phase3_failure_binding: Phase3RunFailureDescriptorBinding | None,
    ) -> None:
        """Authoritative verifier: validates artifact matrix,
        nested digest consistency, and self-hash."""
        # 0) Source-state gate: preparation only for VERIFIED source records
        if source_record.candidate_evaluation_state is not VERIFIED:
            raise ValueError(
                f"Preparation only valid for VERIFIED source, "
                f"got {source_record.candidate_evaluation_state}"
            )
        # 1) Candidate/index identity
        if self.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        # 2) Matrix enforcement using independent authority
        artifacts: dict[str, object | None] = {
            "identity_snapshot": identity_snapshot,
            "complete_snapshot": complete_snapshot,
            "source_binding": source_binding,
            "classification_input": classification_input,
            "evidence_failure_binding": evidence_failure_binding,
            "source_failure_binding": source_failure_binding,
            "phase3_failure_binding": phase3_failure_binding,
        }
        verify_preparation_stage_matrix(
            status=self.status,
            failure_stage=self.failure_stage,
            artifacts=artifacts,
            source_candidate_evaluation_state=source_record.candidate_evaluation_state,
        )
        # 3) Nested digest consistency — compare stored digests against independent authority
        if (
            identity_snapshot is not None
            and self.identity_snapshot_digest != identity_snapshot.identity_snapshot_digest
        ):
            raise ValueError("identity_snapshot_digest mismatch")
        if (
            complete_snapshot is not None
            and self.complete_snapshot_digest != complete_snapshot.snapshot_digest
        ):
            raise ValueError("complete_snapshot_digest mismatch")
        if (
            source_binding is not None
            and self.source_binding_digest != source_binding.binding_digest
        ):
            raise ValueError("source_binding_digest mismatch")
        if (
            classification_input is not None
            and self.classification_input_digest is not None
            and self.classification_input_digest != classification_input.classification_input_digest
        ):
            raise ValueError("classification_input_digest mismatch")
        if evidence_failure_binding is not None and (
            self.evidence_failure_binding_digest
            != evidence_failure_binding.descriptor_binding_digest
        ):
            raise ValueError("evidence_failure_binding_digest mismatch")
        if source_failure_binding is not None and (
            self.source_failure_binding_digest != source_failure_binding.descriptor_binding_digest
        ):
            raise ValueError("source_failure_binding_digest mismatch")
        if (
            phase3_failure_binding is not None
            and self.phase3_failure_binding_digest is not None
            and self.phase3_failure_binding_digest
            != phase3_failure_binding.descriptor_binding_digest
        ):
            raise ValueError("phase3_failure_binding_digest mismatch")
        # 4) Self-hash
        expected = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected:
            raise ValueError("preparation_result_digest mismatch")


def build_phase3_candidate_preparation_result(
    *,
    schema_version: Literal[1] = 1,
    status: Phase3PreparationStatus,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    identity_snapshot: Phase2SourceRecordIdentitySnapshot,
    complete_snapshot: Phase2SourceRecordSnapshot | None = None,
    source_binding: Phase3SourceRecordBinding | None = None,
    classification_input: Phase3CandidateClassificationInput | None = None,
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None = None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None = None,
    phase3_failure_binding: Phase3RunFailureDescriptorBinding | None = None,
    failure_stage: Phase3PreparationFailureStage | None = None,
) -> Phase3CandidatePreparationResult:
    # 1) Matrix enforcement before computing digests
    artifacts: dict[str, object | None] = {
        "identity_snapshot": identity_snapshot,
        "complete_snapshot": complete_snapshot,
        "source_binding": source_binding,
        "classification_input": classification_input,
        "evidence_failure_binding": evidence_failure_binding,
        "source_failure_binding": source_failure_binding,
        "phase3_failure_binding": phase3_failure_binding,
    }
    verify_preparation_stage_matrix(
        status=status,
        failure_stage=failure_stage,
        artifacts=artifacts,
        source_candidate_evaluation_state=identity_snapshot.candidate_evaluation_state,
    )
    isnap_d = identity_snapshot.identity_snapshot_digest
    cs_d = complete_snapshot.snapshot_digest if complete_snapshot is not None else None
    sb_d = source_binding.binding_digest if source_binding is not None else None
    cin_d = (
        classification_input.classification_input_digest
        if classification_input is not None
        else None
    )
    efb_d = (
        evidence_failure_binding.descriptor_binding_digest
        if evidence_failure_binding is not None
        else None
    )
    sfb_d = (
        source_failure_binding.descriptor_binding_digest
        if source_failure_binding is not None
        else None
    )
    p3fb_d = (
        phase3_failure_binding.descriptor_binding_digest
        if phase3_failure_binding is not None
        else None
    )
    payload = {
        "schema_version": schema_version,
        "status": status.value,
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "identity_snapshot_digest": isnap_d,
        "complete_snapshot_digest": cs_d,
        "source_binding_digest": sb_d,
        "classification_input_digest": cin_d,
        "evidence_failure_binding_digest": efb_d,
        "source_failure_binding_digest": sfb_d,
        "phase3_failure_binding_digest": p3fb_d,
        "failure_stage": failure_stage.value if failure_stage is not None else None,
    }
    prep_d = sha256_digest(payload)
    return Phase3CandidatePreparationResult(
        schema_version=schema_version,
        status=status,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        identity_snapshot_digest=isnap_d,
        complete_snapshot_digest=cs_d,
        source_binding_digest=sb_d,
        classification_input_digest=cin_d,
        evidence_failure_binding_digest=efb_d,
        source_failure_binding_digest=sfb_d,
        phase3_failure_binding_digest=p3fb_d,
        failure_stage=failure_stage,
        classification_input=classification_input,
        identity_snapshot=identity_snapshot,
        complete_snapshot=complete_snapshot,
        source_binding=source_binding,
        evidence_failure_binding=evidence_failure_binding,
        source_failure_binding=source_failure_binding,
        phase3_failure_binding=phase3_failure_binding,
        preparation_result_digest=prep_d,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Section 15 — CandidateDispositionRecord (P0-6)
# ═══════════════════════════════════════════════════════════════════════════


def verify_candidate_disposition_failure_matrix(
    *,
    disposition: Phase3Disposition,
    failure_origin: FailureOrigin,
    failure_stage: Phase3PreparationFailureStage | None,
    source_failure_binding_digest: str | None,
    source_failure_payload_digest: str | None,
    phase3_failure_binding_digest: str | None,
    phase3_failure_payload_digest: str | None,
    source_identity_record_descriptor_digest: str,
) -> None:
    """Unified failure matrix for CandidateDispositionRecord.

    Non-failure dispositions: all failure fields = None, origin = NONE.
    P2 runtime: source failure required, P3 failure = None.
    P3 runtime: P3 failure required, source failure = None.
    """

    # source_identity_record_descriptor_digest must be valid SHA-256
    if not re.fullmatch(r"^sha256:[0-9a-f]{64}$", source_identity_record_descriptor_digest):
        raise ValueError("source_identity_record_descriptor_digest must be ^sha256:[0-9a-f]{64}$")

    if disposition in (
        FEASIBLE,
        INFEASIBLE,
        PROVIDER_IDENTITY_MISMATCH,
        _INTEGRITY_FAILED,
        _PROVENANCE_FAILED,
        _UNEVALUATED,
    ):
        # Non-failure: nothing allowed
        if source_failure_binding_digest is not None:
            raise ValueError(f"{disposition}: source_failure_binding_digest must be None")
        if source_failure_payload_digest is not None:
            raise ValueError(f"{disposition}: source_failure_payload_digest must be None")
        if phase3_failure_binding_digest is not None:
            raise ValueError(f"{disposition}: phase3_failure_binding_digest must be None")
        if phase3_failure_payload_digest is not None:
            raise ValueError(f"{disposition}: phase3_failure_payload_digest must be None")
        if failure_origin is not NONE_ORIGIN:
            raise ValueError(f"{disposition}: failure_origin must be NONE, got {failure_origin}")
        if failure_stage is not None:
            raise ValueError(f"{disposition}: failure_stage must be None")
    elif disposition is _RUNTIME_FAILED:
        if failure_origin == PHASE2_EVALUATION:
            if source_failure_binding_digest is None:
                raise ValueError("RF(P2): source_failure_binding_digest required")
            if phase3_failure_binding_digest is not None:
                raise ValueError("RF(P2): phase3_failure_binding_digest must be None")
            if phase3_failure_payload_digest is not None:
                raise ValueError("RF(P2): phase3_failure_payload_digest must be None")
            if failure_stage is not None:
                raise ValueError("RF(P2): failure_stage must be None")
        elif failure_origin == PHASE3_CLASSIFICATION:
            if source_failure_binding_digest is not None:
                raise ValueError("RF(P3): source_failure_binding_digest must be None")
            if source_failure_payload_digest is not None:
                raise ValueError("RF(P3): source_failure_payload_digest must be None")
            if phase3_failure_binding_digest is None:
                raise ValueError("RF(P3): phase3_failure_binding_digest required")
            if failure_stage is None:
                raise ValueError("RF(P3): failure_stage required")
        else:
            raise ValueError(f"unknown failure_origin: {failure_origin}")
    else:
        raise ValueError(f"unknown disposition: {disposition}")


def candidate_disposition_payload_from_values(
    *,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    source_candidate_evaluation_state: CandidateEvaluationState,
    source_hash_verification_outcome: VerificationOutcome,
    source_provenance_verification_outcome: VerificationOutcome,
    source_record_descriptor_digest: str | None,
    source_identity_record_descriptor_digest: str,
    disposition: Phase3Disposition,
    diagnostic: FeasibilityDiagnosticKey,
    provider_identity_matches: bool,
    rating_status: str | None,
    candidate_evaluation_identity_digest: str | None,
    verified_rating_evidence_digest: str | None,
    invalid_rating_evidence_digest: str | None,
    primary_engineering_value: str | None,
    secondary_engineering_value: str | None,
    warning_descriptor_digests: tuple[str, ...],
    blocker_descriptor_digests: tuple[str, ...],
    source_evaluation_failure_payload_digest: str | None,
    source_evaluation_failure_binding_digest: str | None,
    phase3_failure_binding_digest: str | None = None,
    phase3_failure_payload_digest: str | None,
    failure_origin: FailureOrigin,
    failure_stage: Phase3PreparationFailureStage | None = None,
) -> dict[str, object]:
    return {
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "source_candidate_evaluation_state": source_candidate_evaluation_state.value,
        "source_hash_verification_outcome": source_hash_verification_outcome.value,
        "source_provenance_verification_outcome": source_provenance_verification_outcome.value,
        "source_record_descriptor_digest": source_record_descriptor_digest,
        "source_identity_record_descriptor_digest": source_identity_record_descriptor_digest,
        "disposition": disposition.value,
        "diagnostic": diagnostic.value,
        "provider_identity_matches": provider_identity_matches,
        "rating_status": rating_status,
        "candidate_evaluation_identity_digest": candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": invalid_rating_evidence_digest,
        "primary_engineering_value": primary_engineering_value,
        "secondary_engineering_value": secondary_engineering_value,
        "warning_descriptor_digests": list(warning_descriptor_digests),
        "blocker_descriptor_digests": list(blocker_descriptor_digests),
        "source_evaluation_failure_payload_digest": source_evaluation_failure_payload_digest,
        "source_evaluation_failure_binding_digest": source_evaluation_failure_binding_digest,
        "phase3_failure_binding_digest": phase3_failure_binding_digest,
        "phase3_failure_payload_digest": phase3_failure_payload_digest,
        "failure_origin": failure_origin.value,
        "failure_stage": failure_stage.value if failure_stage is not None else None,
    }


def build_candidate_disposition_record(
    *,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    source_candidate_evaluation_state: CandidateEvaluationState,
    source_hash_verification_outcome: VerificationOutcome,
    source_provenance_verification_outcome: VerificationOutcome,
    source_record_descriptor_digest: str | None,
    source_identity_record_descriptor_digest: str,
    disposition: Phase3Disposition,
    diagnostic: FeasibilityDiagnosticKey,
    provider_identity_matches: bool,
    rating_status: str | None,
    candidate_evaluation_identity_digest: str | None,
    verified_rating_evidence_digest: str | None,
    invalid_rating_evidence_digest: str | None,
    primary_engineering_value: str | None,
    secondary_engineering_value: str | None,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    source_evaluation_failure_payload_digest: str | None,
    source_evaluation_failure_binding_digest: str | None,
    phase3_failure_payload_digest: str | None,
    failure_origin: FailureOrigin,
    failure_stage: Phase3PreparationFailureStage | None = None,
    phase3_failure_binding_digest: str | None = None,
) -> CandidateDispositionRecord:
    # 0) Failure matrix enforcement — single authority for all three layers
    verify_candidate_disposition_failure_matrix(
        disposition=disposition,
        failure_origin=failure_origin,
        failure_stage=failure_stage,
        source_failure_binding_digest=source_evaluation_failure_binding_digest,
        source_failure_payload_digest=source_evaluation_failure_payload_digest,
        phase3_failure_binding_digest=phase3_failure_binding_digest,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
    )
    wdd = tuple(d.message_payload_digest for d in warning_descriptors)
    bdd = tuple(d.message_payload_digest for d in blocker_descriptors)
    payload = candidate_disposition_payload_from_values(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_candidate_evaluation_state=source_candidate_evaluation_state,
        source_hash_verification_outcome=source_hash_verification_outcome,
        source_provenance_verification_outcome=source_provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=disposition,
        diagnostic=diagnostic,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        primary_engineering_value=primary_engineering_value,
        secondary_engineering_value=secondary_engineering_value,
        warning_descriptor_digests=wdd,
        blocker_descriptor_digests=bdd,
        source_evaluation_failure_payload_digest=source_evaluation_failure_payload_digest,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        phase3_failure_binding_digest=phase3_failure_binding_digest,
        failure_origin=failure_origin,
        failure_stage=failure_stage,
    )
    digest = sha256_digest(payload)
    return CandidateDispositionRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_candidate_evaluation_state=source_candidate_evaluation_state,
        source_hash_verification_outcome=source_hash_verification_outcome,
        source_provenance_verification_outcome=source_provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=disposition,
        diagnostic=diagnostic,
        provider_identity_matches=provider_identity_matches,
        rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        primary_engineering_value=primary_engineering_value,
        secondary_engineering_value=secondary_engineering_value,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=source_evaluation_failure_payload_digest,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        phase3_failure_binding_digest=phase3_failure_binding_digest,
        failure_origin=failure_origin,
        failure_stage=failure_stage,
        feasibility_digest=digest,
    )


def candidate_disposition_payload(record: CandidateDispositionRecord) -> dict[str, object]:
    """Explicit field-to-payload mapping for disposition digest verification."""
    return candidate_disposition_payload_from_values(
        source_qualified_candidate_id=record.source_qualified_candidate_id,
        evaluation_order_index=record.evaluation_order_index,
        source_candidate_evaluation_state=record.source_candidate_evaluation_state,
        source_hash_verification_outcome=record.source_hash_verification_outcome,
        source_provenance_verification_outcome=record.source_provenance_verification_outcome,
        source_record_descriptor_digest=record.source_record_descriptor_digest,
        source_identity_record_descriptor_digest=record.source_identity_record_descriptor_digest,
        disposition=record.disposition,
        diagnostic=record.diagnostic,
        provider_identity_matches=record.provider_identity_matches,
        rating_status=record.rating_status,
        candidate_evaluation_identity_digest=record.candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=record.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=record.invalid_rating_evidence_digest,
        primary_engineering_value=record.primary_engineering_value,
        secondary_engineering_value=record.secondary_engineering_value,
        warning_descriptor_digests=tuple(
            d.message_payload_digest for d in record.warning_descriptors
        ),
        blocker_descriptor_digests=tuple(
            d.message_payload_digest for d in record.blocker_descriptors
        ),
        source_evaluation_failure_payload_digest=record.source_evaluation_failure_payload_digest,
        source_evaluation_failure_binding_digest=record.source_evaluation_failure_binding_digest,
        phase3_failure_payload_digest=record.phase3_failure_payload_digest,
        phase3_failure_binding_digest=record.phase3_failure_binding_digest,
        failure_origin=record.failure_origin,
        failure_stage=record.failure_stage,
    )


def disposition_from_preparation_failure(
    *,
    source_record: CandidateEvaluationRecord,
    source_snapshot: Phase2SourceRecordSnapshot | None,
    identity_snapshot_digest: str,
    candidate: ManufacturableCandidate,
    preparation_result: Phase3CandidatePreparationResult,
    phase3_failure_binding: Phase3RunFailureDescriptorBinding,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> CandidateDispositionRecord:
    """Construct a Phase 3 RUNTIME_FAILED disposition from a failed preparation.

    Receives an independent phase3_failure_binding artifact and validates
    it against the preparation_result's stored binding identity.
    """
    # Validate external binding artifact against stored preparation identity
    if preparation_result.phase3_failure_binding is None:
        raise ValueError("disposition_from_preparation_failure: no stored failure binding")
    if (
        preparation_result.phase3_failure_binding_digest
        != phase3_failure_binding.descriptor_binding_digest
    ):
        raise ValueError(
            "disposition_from_preparation_failure: external binding digest != stored binding digest"
        )
    # Validate canonical fields match
    if (
        preparation_result.phase3_failure_binding.original_code
        != phase3_failure_binding.original_code
    ):
        raise ValueError("disposition_from_preparation_failure: original_code mismatch")
    if (
        preparation_result.phase3_failure_binding.payload_digest
        != phase3_failure_binding.payload_digest
    ):
        raise ValueError("disposition_from_preparation_failure: payload_digest mismatch")
    if (
        preparation_result.phase3_failure_binding.canonicalization_error_digest
        != phase3_failure_binding.canonicalization_error_digest
    ):
        raise ValueError("disposition_from_preparation_failure: ce_digest mismatch")
    phase3_failure_binding_digest = phase3_failure_binding.descriptor_binding_digest
    phase3_failure_payload_digest = phase3_failure_binding.payload_digest
    # Canonicalization success: both digests present
    # Canonicalization failure: binding digest present, payload digest None
    if phase3_failure_binding_digest is None:
        raise ValueError(
            "disposition_from_preparation_failure: no binding digest (canonicalization broken)"
        )
    stage = preparation_result.failure_stage
    if stage is None:
        raise ValueError("disposition_from_preparation_failure: no failure_stage")
    identity_digest = (
        source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if source_record.candidate_evaluation_identity is not None
        else None
    )
    evidence_digest = (
        source_snapshot.verified_rating_evidence_digest
        if source_snapshot is not None
        and stage
        in (
            Phase3PreparationFailureStage.SOURCE_BINDING,
            Phase3PreparationFailureStage.CLASSIFICATION_INPUT,
        )
        else None
    )
    src_desc_digest = (
        source_snapshot.phase2_source_record_descriptor_digest
        if source_snapshot is not None
        else None
    )
    return build_candidate_disposition_record(
        source_qualified_candidate_id=source_record.source_qualified_candidate_id,
        evaluation_order_index=source_record.evaluation_order_index,
        source_candidate_evaluation_state=source_record.candidate_evaluation_state,
        source_hash_verification_outcome=source_record.hash_verification_outcome,
        source_provenance_verification_outcome=source_record.provenance_verification_outcome,
        source_record_descriptor_digest=src_desc_digest,
        source_identity_record_descriptor_digest=identity_snapshot_digest,
        disposition=_RUNTIME_FAILED,
        diagnostic=PHASE3_RUNTIME_FAILED,
        provider_identity_matches=source_record.provider_identity_matches,
        rating_status=source_record.rating_status,
        candidate_evaluation_identity_digest=identity_digest,
        verified_rating_evidence_digest=evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=None,
        source_evaluation_failure_binding_digest=None,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        phase3_failure_binding_digest=phase3_failure_binding_digest,
        failure_origin=PHASE3_CLASSIFICATION,
        failure_stage=stage,
    )


class CandidateDispositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_qualified_candidate_id: str
    evaluation_order_index: int
    source_candidate_evaluation_state: CandidateEvaluationState
    source_hash_verification_outcome: VerificationOutcome
    source_provenance_verification_outcome: VerificationOutcome
    source_record_descriptor_digest: str | None
    source_identity_record_descriptor_digest: str
    disposition: Phase3Disposition
    diagnostic: FeasibilityDiagnosticKey
    provider_identity_matches: bool
    rating_status: str | None
    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    invalid_rating_evidence_digest: str | None
    primary_engineering_value: str | None
    secondary_engineering_value: str | None
    warning_descriptors: tuple[Phase3MessageDescriptor, ...]
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...]
    source_evaluation_failure_payload_digest: str | None
    source_evaluation_failure_binding_digest: str | None
    phase3_failure_binding_digest: str | None
    phase3_failure_payload_digest: str | None
    failure_origin: FailureOrigin
    failure_stage: Phase3PreparationFailureStage | None = None
    feasibility_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0:
            raise ValueError("index must be ≥ 0")
        if not self.source_identity_record_descriptor_digest:
            raise ValueError("identity descriptor required")
        # 0) Failure matrix — single authority shared with factory and verifier
        verify_candidate_disposition_failure_matrix(
            disposition=self.disposition,
            failure_origin=self.failure_origin,
            failure_stage=self.failure_stage,
            source_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            source_failure_payload_digest=self.source_evaluation_failure_payload_digest,
            phase3_failure_binding_digest=self.phase3_failure_binding_digest,
            phase3_failure_payload_digest=self.phase3_failure_payload_digest,
            source_identity_record_descriptor_digest=self.source_identity_record_descriptor_digest,
        )
        for d, n in [
            (self.source_record_descriptor_digest, "source"),
            (self.feasibility_digest, "feasibility"),
        ]:
            if d is not None and not self.DIGEST_PATTERN.match(d):
                raise ValueError(f"invalid {n} digest")
        for d, n in [
            (self.candidate_evaluation_identity_digest, "identity"),
            (self.verified_rating_evidence_digest, "evidence"),
            (self.invalid_rating_evidence_digest, "invalid"),
            (self.source_evaluation_failure_payload_digest, "source_failure_payload"),
            (self.source_evaluation_failure_binding_digest, "source_failure_binding"),
            (self.phase3_failure_binding_digest, "phase3_failure_binding"),
            (self.phase3_failure_payload_digest, "phase3_failure"),
        ]:
            if d is not None and not self.DIGEST_PATTERN.match(d):
                raise ValueError(f"invalid {n} digest")
        # FEASIBLE
        if self.disposition is FEASIBLE:
            if self.source_candidate_evaluation_state != VERIFIED:
                raise ValueError("FEASIBLE: source must be VERIFIED")
            if self.source_hash_verification_outcome != PASSED:
                raise ValueError("FEASIBLE: hash must be PASSED")
            if self.source_provenance_verification_outcome != PASSED:
                raise ValueError("FEASIBLE: provenance must be PASSED")
            if not self.provider_identity_matches:
                raise ValueError("FEASIBLE: provider must match")
            if self.rating_status != "succeeded":
                raise ValueError("FEASIBLE: rating must be SUCCEEDED")
            if self.diagnostic != NONE:
                raise ValueError("FEASIBLE: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("FEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("FEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("FEASIBLE: invalid must be None")
            if self.primary_engineering_value is None:
                raise ValueError("FEASIBLE: primary required")
            if self.secondary_engineering_value is None:
                raise ValueError("FEASIBLE: secondary required")
            verify_canonical_decimal_string(self.primary_engineering_value)
            verify_canonical_decimal_string(self.secondary_engineering_value)
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("FEASIBLE: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("FEASIBLE: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("FEASIBLE: origin must be NONE")
        # PROVIDER_IDENTITY_MISMATCH
        elif self.disposition is PROVIDER_IDENTITY_MISMATCH:
            if self.source_candidate_evaluation_state != VERIFIED:
                raise ValueError("PROVIDER_MISMATCH: source must be VERIFIED")
            if self.source_hash_verification_outcome != PASSED:
                raise ValueError("PROVIDER_MISMATCH: hash must be PASSED")
            if self.source_provenance_verification_outcome != PASSED:
                raise ValueError("PROVIDER_MISMATCH: provenance must be PASSED")
            if self.provider_identity_matches:
                raise ValueError("PROVIDER_MISMATCH: provider must NOT match")
            if self.diagnostic != PROVIDER_IDENTITY_MISMATCH_DIAG:
                raise ValueError("PROVIDER_MISMATCH: diagnostic mismatch")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("PROVIDER_MISMATCH: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("PROVIDER_MISMATCH: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: invalid must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("PROVIDER_MISMATCH: origin must be NONE")
        # INFEASIBLE
        elif self.disposition is INFEASIBLE:
            if self.source_candidate_evaluation_state != VERIFIED:
                raise ValueError("INFEASIBLE: source must be VERIFIED")
            if not self.provider_identity_matches:
                raise ValueError("INFEASIBLE: provider must match")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("INFEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("INFEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("INFEASIBLE: invalid must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("INFEASIBLE: primary must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("INFEASIBLE: secondary must be None")
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("INFEASIBLE: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("INFEASIBLE: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("INFEASIBLE: origin must be NONE")
            if self.rating_status == "succeeded":
                if self.diagnostic not in (DUTY_SHORTFALL, TERMINAL_DELTA_T_INADEQUATE):
                    raise ValueError("INFEASIBLE+SUCCEEDED: diagnostic mismatch")
            elif self.rating_status == "blocked":
                if self.diagnostic != RATING_BLOCKED:
                    raise ValueError("INFEASIBLE+BLOCKED: diagnostic must be RATING_BLOCKED")
            elif self.rating_status == "failed":
                if self.diagnostic != RATING_FAILED:
                    raise ValueError("INFEASIBLE+FAILED: diagnostic must be RATING_FAILED")
            else:
                raise ValueError(f"INFEASIBLE: unexpected rating_status {self.rating_status}")
        # INTEGRITY_FAILED
        elif self.disposition is _INTEGRITY_FAILED:
            if self.source_candidate_evaluation_state != INTEGRITY_INVALID:
                raise ValueError("INTEGRITY_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != FAILED:
                raise ValueError("INTEGRITY_FAILED: hash must be FAILED")
            if self.source_provenance_verification_outcome != NOT_RUN:
                raise ValueError("INTEGRITY_FAILED: provenance must be NOT_RUN")
            if self.diagnostic != FeasibilityDiagnosticKey.INTEGRITY_FAILED:
                raise ValueError("INTEGRITY_FAILED: diagnostic mismatch")
            if self.provider_identity_matches:
                raise ValueError("INTEGRITY_FAILED: provider must be False")
            if self.rating_status is not None:
                raise ValueError("INTEGRITY_FAILED: rating must be None")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("INTEGRITY_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("INTEGRITY_FAILED: evidence must be None")
            if self.invalid_rating_evidence_digest is None:
                raise ValueError("INTEGRITY_FAILED: invalid evidence required")
            if self.primary_engineering_value is not None:
                raise ValueError("INTEGRITY_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("INTEGRITY_FAILED: engineering must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("INTEGRITY_FAILED: warnings empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("INTEGRITY_FAILED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("INTEGRITY_FAILED: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("INTEGRITY_FAILED: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("INTEGRITY_FAILED: origin must be NONE")
        # PROVENANCE_FAILED
        elif self.disposition is _PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != INTEGRITY_INVALID:
                raise ValueError("PROVENANCE_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != PASSED:
                raise ValueError("PROVENANCE_FAILED: hash must be PASSED")
            if self.source_provenance_verification_outcome != FAILED:
                raise ValueError("PROVENANCE_FAILED: provenance must be FAILED")
            if self.diagnostic != FeasibilityDiagnosticKey.PROVENANCE_FAILED:
                raise ValueError("PROVENANCE_FAILED: diagnostic mismatch")
            if self.rating_status is not None:
                raise ValueError("PROVENANCE_FAILED: rating must be None")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("PROVENANCE_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("PROVENANCE_FAILED: evidence must be None")
            if self.invalid_rating_evidence_digest is None:
                raise ValueError("PROVENANCE_FAILED: invalid evidence required")
            if self.primary_engineering_value is not None:
                raise ValueError("PROVENANCE_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("PROVENANCE_FAILED: engineering must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("PROVENANCE_FAILED: warnings empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("PROVENANCE_FAILED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("PROVENANCE_FAILED: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("PROVENANCE_FAILED: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("PROVENANCE_FAILED: origin must be NONE")
        # UNEVALUATED
        elif self.disposition is _UNEVALUATED:
            if self.source_candidate_evaluation_state != UNEVALUATED:
                raise ValueError("UNEVALUATED: source must be UNEVALUATED")
            if self.source_hash_verification_outcome != NOT_RUN:
                raise ValueError("UNEVALUATED: hash must be NOT_RUN")
            if self.source_provenance_verification_outcome != NOT_RUN:
                raise ValueError("UNEVALUATED: provenance must be NOT_RUN")
            if self.diagnostic != NONE:
                raise ValueError("UNEVALUATED: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("UNEVALUATED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("UNEVALUATED: evidence must be None")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("UNEVALUATED: invalid must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("UNEVALUATED: engineering must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("UNEVALUATED: engineering must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("UNEVALUATED: warnings empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("UNEVALUATED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None:
                raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_payload_digest is not None:
                raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin is not NONE_ORIGIN:
                raise ValueError("UNEVALUATED: origin must be NONE")
        # RUNTIME_FAILED
        elif self.disposition is _RUNTIME_FAILED:
            if self.primary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.failure_origin == PHASE2_EVALUATION:
                if self.source_candidate_evaluation_state != RUNTIME_FAILED:
                    raise ValueError("RF(P2): source must be RF")
                if self.diagnostic != PHASE2_RUNTIME_FAILED:
                    raise ValueError("RF(P2): diagnostic must be PHASE2_RUNTIME_FAILED")
                valid = [(NOT_RUN, NOT_RUN), (ERROR, NOT_RUN), (PASSED, ERROR), (PASSED, PASSED)]
                if (
                    self.source_hash_verification_outcome,
                    self.source_provenance_verification_outcome,
                ) not in valid:
                    raise ValueError("RF(P2): invalid outcome combo")
                if self.candidate_evaluation_identity_digest is not None:
                    raise ValueError("RF(P2): identity must be None")
                if self.verified_rating_evidence_digest is not None:
                    raise ValueError("RF(P2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RF(P2): invalid must be None")
                if len(self.warning_descriptors) != 0:
                    raise ValueError("RF(P2): warnings empty")
                if len(self.blocker_descriptors) != 0:
                    raise ValueError("RF(P2): blockers empty")
                if self.source_evaluation_failure_binding_digest is None:
                    raise ValueError("RF(P2): failure binding required")
                # payload_digest may be None for canonicalization-error descriptors (P0-17)
            elif self.failure_origin == PHASE3_CLASSIFICATION:
                # phase3_failure_binding_digest = REQUIRED (stable identity)
                # phase3_failure_payload_digest = OPTIONAL (None on canonicalization failure)
                if self.phase3_failure_binding_digest is None:
                    raise ValueError("RF(P3): phase3 failure binding required")
                # payload present iff canonicalization succeeded; binding always present
                if self.phase3_failure_payload_digest is None:
                    # canonicalization failure: binding required, payload absent
                    pass
                elif not self.DIGEST_PATTERN.match(self.phase3_failure_payload_digest):
                    raise ValueError("RF(P3): invalid phase3 failure payload digest")
                if self.source_evaluation_failure_payload_digest is not None:
                    raise ValueError("RF(P3): source failure must be None")
                if self.source_candidate_evaluation_state != VERIFIED:
                    raise ValueError("RF(P3): source must be VERIFIED")
                if self.source_hash_verification_outcome != PASSED:
                    raise ValueError("RF(P3): hash must be PASSED")
                if self.source_provenance_verification_outcome != PASSED:
                    raise ValueError("RF(P3): provenance must be PASSED")
                if self.diagnostic != PHASE3_RUNTIME_FAILED:
                    raise ValueError("RF(P3): diagnostic must be PHASE3_RUNTIME_FAILED")
                if self.candidate_evaluation_identity_digest is None:
                    raise ValueError("RF(P3): identity required")
                if self.failure_stage is None:
                    raise ValueError("RF(P3): failure_stage required")
                if self.failure_stage in (
                    Phase3PreparationFailureStage.SOURCE_BINDING,
                    Phase3PreparationFailureStage.CLASSIFICATION_INPUT,
                ):
                    if self.verified_rating_evidence_digest is None:
                        raise ValueError("RF(P3): evidence required for stage")
                else:
                    if self.verified_rating_evidence_digest is not None:
                        raise ValueError("RF(P3): evidence absent for stage")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RF(P3): invalid must be None")
            else:
                raise ValueError(f"unexpected failure_origin: {self.failure_origin}")
        else:
            raise ValueError(f"unknown disposition: {self.disposition}")
        return self

    def verify_or_raise(
        self,
        *,
        source_record: CandidateEvaluationRecord,
        source_failure_binding: Phase3RunFailureDescriptorBinding | None,
        phase3_failure_binding: Phase3RunFailureDescriptorBinding | None,
    ) -> None:
        """Authoritative verifier: validates source identity, digest fields,
        independent failure authority, branch matrix, and self-hash."""
        # 0) Validate independent source failure binding
        if self.failure_origin == PHASE2_EVALUATION:
            if source_failure_binding is None:
                raise ValueError("RUNTIME_FAILED(P2): source_failure_binding required")
            if (
                self.source_evaluation_failure_binding_digest
                != source_failure_binding.descriptor_binding_digest
            ):
                raise ValueError(
                    "source_evaluation_failure_binding_digest vs "
                    "binding.descriptor_binding_digest mismatch"
                )
            expected_payload = source_failure_binding.payload_digest
            if self.source_evaluation_failure_payload_digest != expected_payload:
                raise ValueError(
                    "source_evaluation_failure_payload_digest vs binding.payload_digest mismatch"
                )
            if phase3_failure_binding is not None:
                raise ValueError("RUNTIME_FAILED(P2): phase3_failure_binding must be None")
        elif self.failure_origin == PHASE3_CLASSIFICATION:
            if phase3_failure_binding is None:
                raise ValueError("RUNTIME_FAILED(P3): phase3_failure_binding required")
            if (
                self.phase3_failure_binding_digest
                != phase3_failure_binding.descriptor_binding_digest
            ):
                raise ValueError(
                    "phase3_failure_binding_digest vs binding.descriptor_binding_digest mismatch"
                )
            expected_payload = phase3_failure_binding.payload_digest
            if self.phase3_failure_payload_digest != expected_payload:
                raise ValueError("phase3_failure_payload_digest vs binding.payload_digest mismatch")
            if source_failure_binding is not None:
                raise ValueError("RUNTIME_FAILED(P3): source_failure_binding must be None")
        else:
            if source_failure_binding is not None:
                raise ValueError(f"{self.disposition}: source_failure_binding must be None")
            if phase3_failure_binding is not None:
                raise ValueError(f"{self.disposition}: phase3_failure_binding must be None")
        # 1) Unified failure matrix — single authority shared with factory and model validator
        verify_candidate_disposition_failure_matrix(
            disposition=self.disposition,
            failure_origin=self.failure_origin,
            failure_stage=self.failure_stage,
            source_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            source_failure_payload_digest=self.source_evaluation_failure_payload_digest,
            phase3_failure_binding_digest=self.phase3_failure_binding_digest,
            phase3_failure_payload_digest=self.phase3_failure_payload_digest,
            source_identity_record_descriptor_digest=self.source_identity_record_descriptor_digest,
        )
        # 2) Source record cross-check
        if self.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        if self.source_candidate_evaluation_state != source_record.candidate_evaluation_state:
            raise ValueError("eval_state mismatch")
        if self.source_hash_verification_outcome != source_record.hash_verification_outcome:
            raise ValueError("hash_outcome mismatch")
        if (
            self.source_provenance_verification_outcome
            != source_record.provenance_verification_outcome
        ):
            raise ValueError("provenance_outcome mismatch")
        if self.provider_identity_matches != source_record.provider_identity_matches:
            raise ValueError("provider_matches mismatch")
        if self.rating_status != source_record.rating_status:
            raise ValueError("rating_status mismatch")
        # 3) Digest field cross-check with source_record
        expected_identity_digest = (
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity is not None
            else None
        )
        if self.candidate_evaluation_identity_digest != expected_identity_digest:
            raise ValueError("candidate_evaluation_identity_digest mismatch")
        expected_evidence_digest = (
            source_record.verified_rating_evidence.compute_explicit_evidence_digest()
            if source_record.verified_rating_evidence is not None
            else None
        )
        if self.verified_rating_evidence_digest != expected_evidence_digest:
            raise ValueError("verified_rating_evidence_digest mismatch")
        expected_invalid_digest = (
            source_record.invalid_rating_evidence.invalid_evidence_digest
            if source_record.invalid_rating_evidence is not None
            else None
        )
        if self.invalid_rating_evidence_digest != expected_invalid_digest:
            raise ValueError("invalid_rating_evidence_digest mismatch")
        # 4) Self-hash integrity
        payload = candidate_disposition_payload_from_values(
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            source_candidate_evaluation_state=self.source_candidate_evaluation_state,
            source_hash_verification_outcome=self.source_hash_verification_outcome,
            source_provenance_verification_outcome=self.source_provenance_verification_outcome,
            source_record_descriptor_digest=self.source_record_descriptor_digest,
            source_identity_record_descriptor_digest=self.source_identity_record_descriptor_digest,
            disposition=self.disposition,
            diagnostic=self.diagnostic,
            provider_identity_matches=self.provider_identity_matches,
            rating_status=self.rating_status,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            invalid_rating_evidence_digest=self.invalid_rating_evidence_digest,
            primary_engineering_value=self.primary_engineering_value,
            secondary_engineering_value=self.secondary_engineering_value,
            warning_descriptor_digests=tuple(
                d.message_payload_digest for d in self.warning_descriptors
            ),
            blocker_descriptor_digests=tuple(
                d.message_payload_digest for d in self.blocker_descriptors
            ),
            source_evaluation_failure_payload_digest=self.source_evaluation_failure_payload_digest,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            phase3_failure_payload_digest=self.phase3_failure_payload_digest,
            phase3_failure_binding_digest=self.phase3_failure_binding_digest,
            failure_origin=self.failure_origin,
            failure_stage=self.failure_stage,
        )
        if self.feasibility_digest != sha256_digest(payload):
            raise ValueError("feasibility_digest mismatch")
