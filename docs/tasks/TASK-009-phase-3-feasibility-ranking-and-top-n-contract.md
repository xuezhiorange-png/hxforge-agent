# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
**Frozen Phase 1-2 SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc
**Phase 2 HEAD:** c77d723c51c4d8045cafa783f97fdc0d628a0e91

---

## 1. Scope

Phase 3 consumes `tuple[CandidateEvaluationRecord, ...]` via `Phase3EvaluationInput` and produces `OptimizationResult`. Non-goals: TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver, candidate generation, catalog changes, Phase 2 mutation, re-running TASK-008, recovering strict-stop.

---

## 2. Frozen enums and error codes

```python
class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"; INFEASIBLE = "infeasible"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    INTEGRITY_FAILED = "integrity_failed"; PROVENANCE_FAILED = "provenance_failed"
    RUNTIME_FAILED = "runtime_failed"; UNEVALUATED = "unevaluated"

class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"; PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"; RATING_FAILED = "rating_failed"
    DUTY_SHORTFALL = "duty_shortfall"
    TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
    INTEGRITY_FAILED = "integrity_failed"; PROVENANCE_FAILED = "provenance_failed"
    PHASE2_RUNTIME_FAILED = "phase2_runtime_failed"
    PHASE3_RUNTIME_FAILED = "phase3_runtime_failed"

class TerminationStatus(StrEnum):
    COMPLETE = "complete"; PARTIAL = "partial"

class FailureOrigin(StrEnum):
    NONE = "none"; PHASE2_EVALUATION = "phase2_evaluation"
    PHASE3_CLASSIFICATION = "phase3_classification"

class Phase3ProvenanceRelation(StrEnum):
    REGULATES = "regulates"; CONSUMED_BY = "consumed_by"; PRODUCED = "produced"
    EVALUATED = "evaluated"; RANKED = "ranked"; SELECTED_BY = "selected_by"
    SELECTED = "selected"; EXECUTED_BY = "executed_by"

class Phase3PreparationStatus(StrEnum):
    READY = "ready"; FAILED = "failed"

class Phase3PreparationFailureStage(StrEnum):
    WARNING_DESCRIPTOR = "warning_descriptor"
    BLOCKER_DESCRIPTOR = "blocker_descriptor"
    FAILURE_DESCRIPTOR = "failure_descriptor"
    EVIDENCE_DIGEST = "evidence_digest"
    SOURCE_BINDING = "source_binding"
    CLASSIFICATION_INPUT = "classification_input"

# New ErrorCode string values (added to existing ErrorCode)
PHASE3_MISSING_RATING_STATUS = "phase3_missing_rating_status"
PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
PHASE3_STRICT_STOP = "phase3_strict_stop"
PHASE3_TRUSTED_EVIDENCE_INCOMPLETE = "phase3_trusted_evidence_incomplete"
```

---

## 3. Phase 2 canonical descriptor types (P0-1, P0-2)

Phase 3 uses `CanonicalizedEngineeringMessageDescriptor` and `CanonicalizedRunFailureDescriptor` from Phase 2 production code. These are the authoritative types for all descriptor-based operations. No Phase 3-specific replacement types are used for the evidence payload computation.

### 3.1 Evidence digest via authoritative helper (P0-1)

```python
def compute_evidence_digest(
    evidence: VerifiedRatingEvidenceSnapshot | None,
    *,
    warning_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    blocker_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    failure_descriptor: CanonicalizedRunFailureDescriptor | None,
) -> str | None:
    """Computes evidence digest using the authoritative 26-field Phase 2 helper."""
    if evidence is None:
        return None
    payload = verified_rating_evidence_payload_from_descriptors(
        evidence,
        warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors,
        failure_descriptor=failure_descriptor,
    )
    return sha256_digest(payload)
```

Note: no `hash_verification_outcome` or `provenance_verification_outcome` parameters. The authoritive helper does not accept them.

### 3.2 RunFailure descriptor — success and failure states (P0-2)

```python
# CanonicalizedRunFailureDescriptor lives in Phase 2 production code.
# It supports both:
# success path: canonical_payload, payload_digest, original_code
# failure path: canonicalization_error, context_path_digest, safe_marker_digest, original_code

# Phase 3 wraps it for binding:
class Phase3RunFailureDescriptorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    descriptor_digest: str
    payload_digest: str | None
    original_code: str | None
    canonicalization_error_digest: str | None
    context_path_digest: str | None
    safe_marker_digest: str | None
    binding_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.descriptor_digest or not self.DIGEST_PATTERN.match(self.descriptor_digest):
            raise ValueError("invalid descriptor_digest")
        if self.payload_digest is not None and not self.DIGEST_PATTERN.match(self.payload_digest):
            raise ValueError("invalid payload_digest")
        expected = sha256_digest(run_failure_descriptor_binding_payload(self))
        if self.binding_digest != expected:
            raise ValueError("binding_digest mismatch")
        return self

def run_failure_descriptor_binding_payload(
    b: Phase3RunFailureDescriptorBinding,
) -> dict[str, object]:
    return {
        "descriptor_digest": b.descriptor_digest,
        "payload_digest": b.payload_digest,
        "original_code": b.original_code,
        "canonicalization_error_digest": b.canonicalization_error_digest,
        "context_path_digest": b.context_path_digest,
        "safe_marker_digest": b.safe_marker_digest,
    }

def run_failure_descriptor_binding_payload_from_values(
    *,
    descriptor_digest: str,
    payload_digest: str | None,
    original_code: str | None,
    canonicalization_error_digest: str | None,
    context_path_digest: str | None,
    safe_marker_digest: str | None,
) -> dict[str, object]:
    return {
        "descriptor_digest": descriptor_digest,
        "payload_digest": payload_digest,
        "original_code": original_code,
        "canonicalization_error_digest": canonicalization_error_digest,
        "context_path_digest": context_path_digest,
        "safe_marker_digest": safe_marker_digest,
    }

def build_phase3_run_failure_descriptor_binding(
    descriptor: CanonicalizedRunFailureDescriptor,
) -> Phase3RunFailureDescriptorBinding:
    descriptor_digest = descriptor.descriptor_digest if hasattr(descriptor, 'descriptor_digest') else sha256_digest({
        "payload_digest": descriptor.payload_digest if descriptor.canonicalization_error is None else None,
        "canonicalization_error_digest": sha256_digest({
            "failure_kind": descriptor.canonicalization_error.failure_kind.value,
            "context_key": descriptor.canonicalization_error.context_key,
        }) if descriptor.canonicalization_error is not None else None,
        "original_code": descriptor.original_code,
    })
    payload_digest = descriptor.payload_digest if descriptor.canonicalization_error is None else None
    ce_digest = sha256_digest({
        "failure_kind": descriptor.canonicalization_error.failure_kind.value,
        "context_key": descriptor.canonicalization_error.context_key,
    }) if descriptor.canonicalization_error is not None else None
    ctx_path_digest = sha256_digest({"context_path": list(descriptor.canonicalization_error.context_path)}) if descriptor.canonicalization_error is not None else None
    sm_digest = sha256_digest({
        "context_key": descriptor.canonicalization_error.context_key,
        "context_path": list(descriptor.canonicalization_error.context_path),
        "offending_type": descriptor.canonicalization_error.offending_type,
        "failure_kind": descriptor.canonicalization_error.failure_kind.value,
    }) if descriptor.canonicalization_error is not None else None
    payload = run_failure_descriptor_binding_payload_from_values(
        descriptor_digest=descriptor_digest,
        payload_digest=payload_digest,
        original_code=descriptor.original_code,
        canonicalization_error_digest=ce_digest,
        context_path_digest=ctx_path_digest,
        safe_marker_digest=sm_digest,
    )
    binding_digest = sha256_digest(payload)
    return Phase3RunFailureDescriptorBinding(
        descriptor_digest=descriptor_digest,
        payload_digest=payload_digest,
        original_code=descriptor.original_code,
        canonicalization_error_digest=ce_digest,
        context_path_digest=ctx_path_digest,
        safe_marker_digest=sm_digest,
        binding_digest=binding_digest,
    )
```

---

## 4. Phase3MessageDescriptor and binding

```python
class Phase3MessageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    owner_sort_key: tuple[str, str, str, str, tuple[str, ...], str]
    original_code: str
    message_payload_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.original_code: raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest): raise ValueError("invalid message_payload_digest")
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
        if not self.original_code: raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest): raise ValueError("invalid message_payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest): raise ValueError("invalid descriptor_binding_digest")
        expected = sha256_digest({
            "owner_sort_key": list(self.owner_sort_key), "original_code": self.original_code,
            "message_payload_digest": self.message_payload_digest,
        })
        if self.descriptor_binding_digest != expected: raise ValueError("descriptor_binding_digest mismatch")
        return self

def build_phase3_message_descriptor_binding(desc: Phase3MessageDescriptor) -> Phase3MessageDescriptorBinding:
    payload = {"owner_sort_key": list(desc.owner_sort_key), "original_code": desc.original_code, "message_payload_digest": desc.message_payload_digest}
    d = sha256_digest(payload)
    return Phase3MessageDescriptorBinding(owner_sort_key=desc.owner_sort_key, original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest, descriptor_binding_digest=d)
```

---

## 5. Phase2SourceRecordIdentitySnapshot (P0-8)

Always exists. Contains all fields that are available without requiring message canonicalization.

```python
class Phase2SourceRecordIdentitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool
    feasibility_status: Phase2FeasibilityStatus
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
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        for v, n in [(self.candidate_evaluation_identity_digest, "identity"),
                      (self.invalid_rating_evidence_digest, "invalid"),
                      (self.claimed_rating_result_audit_digest, "audit")]:
            if v is not None and not self.DIGEST_PATTERN.match(v): raise ValueError(f"invalid {n} digest")
        expected = sha256_digest(_identity_snapshot_payload(self))
        if self.identity_snapshot_digest != expected: raise ValueError("identity_snapshot_digest mismatch")
        return self

def _identity_snapshot_payload(s: Phase2SourceRecordIdentitySnapshot) -> dict[str, object]:
    return {
        "schema_version": s.schema_version, "source_qualified_candidate_id": s.source_qualified_candidate_id,
        "evaluation_order_index": s.evaluation_order_index, "candidate_evaluation_state": s.candidate_evaluation_state.value,
        "feasible": s.feasible, "feasibility_status": s.feasibility_status.value,
        "hash_verification_outcome": s.hash_verification_outcome.value, "provenance_verification_outcome": s.provenance_verification_outcome.value,
        "provider_identity_matches": s.provider_identity_matches, "rating_status": s.rating_status,
        "candidate_evaluation_identity_digest": s.candidate_evaluation_identity_digest,
        "invalid_rating_evidence_digest": s.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": s.claimed_rating_result_audit_digest,
    }

def build_identity_snapshot(rec: CandidateEvaluationRecord) -> Phase2SourceRecordIdentitySnapshot:
    identity_digest = rec.candidate_evaluation_identity.candidate_evaluation_identity_digest \
        if rec.candidate_evaluation_identity is not None else None
    invalid_digest = rec.invalid_rating_evidence.invalid_evidence_digest \
        if rec.invalid_rating_evidence is not None else None
    audit_digest = rec.claimed_rating_result_audit.audit_digest \
        if rec.claimed_rating_result_audit is not None else None
    payload = {"schema_version": 1, "source_qualified_candidate_id": rec.source_qualified_candidate_id,
        "evaluation_order_index": rec.evaluation_order_index, "candidate_evaluation_state": rec.candidate_evaluation_state.value,
        "feasible": rec.feasible, "feasibility_status": rec.feasibility_status.value,
        "hash_verification_outcome": rec.hash_verification_outcome.value, "provenance_verification_outcome": rec.provenance_verification_outcome.value,
        "provider_identity_matches": rec.provider_identity_matches, "rating_status": rec.rating_status,
        "candidate_evaluation_identity_digest": identity_digest,
        "invalid_rating_evidence_digest": invalid_digest, "claimed_rating_result_audit_digest": audit_digest}
    digest = sha256_digest(payload)
    return Phase2SourceRecordIdentitySnapshot(schema_version=1,
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        candidate_evaluation_state=rec.candidate_evaluation_state,
        feasible=rec.feasible, feasibility_status=rec.feasibility_status,
        hash_verification_outcome=rec.hash_verification_outcome,
        provenance_verification_outcome=rec.provenance_verification_outcome,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=identity_digest,
        invalid_rating_evidence_digest=invalid_digest,
        claimed_rating_result_audit_digest=audit_digest,
        identity_snapshot_digest=digest)
```

---

## 6. Phase2SourceRecordSnapshot (P0-4, P0-5, P0-6)

```python
class Phase2SourceRecordSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool
    feasibility_status: Phase2FeasibilityStatus
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
    source_evaluation_failure_descriptor_digest: str | None
    evidence_failure_descriptor_digest: str | None
    snapshot_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        for f in ("phase2_source_record_descriptor_digest", "snapshot_digest"):
            if not self.DIGEST_PATTERN.match(getattr(self, f)): raise ValueError(f"invalid {f}")
        for v, n in [(self.candidate_evaluation_identity_digest, "identity"),
                      (self.verified_rating_evidence_digest, "evidence"),
                      (self.invalid_rating_evidence_digest, "invalid"),
                      (self.claimed_rating_result_audit_digest, "audit"),
                      (self.evaluation_failure_digest, "failure"),
                      (self.source_evaluation_failure_descriptor_digest, "source_failure_desc"),
                      (self.evidence_failure_descriptor_digest, "evidence_failure_desc")]:
            if v is not None and not self.DIGEST_PATTERN.match(v): raise ValueError(f"invalid {n} digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(_snapshot_payload(self))
        if self.snapshot_digest != expected: raise ValueError("snapshot_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        if self.snapshot_digest != sha256_digest(_snapshot_payload(self)):
            raise ValueError("snapshot_digest mismatch")

def _snapshot_payload(s: Phase2SourceRecordSnapshot) -> dict[str, object]:
    return {
        "schema_version": s.schema_version, "source_qualified_candidate_id": s.source_qualified_candidate_id,
        "evaluation_order_index": s.evaluation_order_index, "candidate_evaluation_state": s.candidate_evaluation_state.value,
        "feasible": s.feasible, "feasibility_status": s.feasibility_status.value,
        "hash_verification_outcome": s.hash_verification_outcome.value,
        "provenance_verification_outcome": s.provenance_verification_outcome.value,
        "provider_identity_matches": s.provider_identity_matches, "rating_status": s.rating_status,
        "candidate_evaluation_identity_digest": s.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": s.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": s.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": s.claimed_rating_result_audit_digest,
        "evaluation_failure_digest": s.evaluation_failure_digest,
        "phase2_source_record_descriptor_digest": s.phase2_source_record_descriptor_digest,
        "warning_descriptor_binding_digests": list(s.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(s.blocker_descriptor_binding_digests),
        "source_evaluation_failure_descriptor_digest": s.source_evaluation_failure_descriptor_digest,
        "evidence_failure_descriptor_digest": s.evidence_failure_descriptor_digest,
    }

def phase2_source_record_snapshot_payload_from_values(**fields) -> dict[str, object]:
    return _snapshot_payload(Phase2SourceRecordSnapshot(**fields, snapshot_digest=""))

def build_phase2_source_record_snapshot(**fields) -> Phase2SourceRecordSnapshot:
    payload = phase2_source_record_snapshot_payload_from_values(**fields)
    sd = sha256_digest(payload)
    return Phase2SourceRecordSnapshot(**fields, snapshot_digest=sd)
```

Note: `phase2_source_record_snapshot_payload_from_values` constructs a temporary model to compute the payload dict, but this temporary model never enters the artifact pipeline — it is immediately discarded after computing the payload dict, which is then hashed and the real model is constructed in one shot.

### 6.1 Snapshot verifier (P0-5, P0-6)

```python
def verify_phase2_source_record_snapshot_or_raise(
    snapshot: Phase2SourceRecordSnapshot,
    *,
    source_record: CandidateEvaluationRecord,
    warning_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    blocker_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...],
    evidence_failure_descriptor: CanonicalizedRunFailureDescriptor | None,
    source_failure_descriptor: CanonicalizedRunFailureDescriptor | None,
) -> None:
    if snapshot.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
        raise ValueError("snapshot candidate_id mismatch")
    if snapshot.evaluation_order_index != source_record.evaluation_order_index:
        raise ValueError("snapshot index mismatch")
    if snapshot.candidate_evaluation_state != source_record.candidate_evaluation_state:
        raise ValueError("snapshot state mismatch")
    if snapshot.feasible != source_record.feasible: raise ValueError("snapshot feasible mismatch")
    if snapshot.feasibility_status != source_record.feasibility_status: raise ValueError("snapshot feasibility_status mismatch")
    if snapshot.hash_verification_outcome != source_record.hash_verification_outcome: raise ValueError("snapshot hash mismatch")
    if snapshot.provenance_verification_outcome != source_record.provenance_verification_outcome: raise ValueError("snapshot provenance mismatch")
    if snapshot.provider_identity_matches != source_record.provider_identity_matches: raise ValueError("snapshot provider flag mismatch")
    if snapshot.rating_status != source_record.rating_status: raise ValueError("snapshot rating_status mismatch")
    eid = source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest \
        if source_record.candidate_evaluation_identity is not None else None
    if snapshot.candidate_evaluation_identity_digest != eid: raise ValueError("snapshot identity digest mismatch")
    iid = source_record.invalid_rating_evidence.invalid_evidence_digest \
        if source_record.invalid_rating_evidence is not None else None
    if snapshot.invalid_rating_evidence_digest != iid: raise ValueError("snapshot invalid digest mismatch")
    ad = source_record.claimed_rating_result_audit.audit_digest \
        if source_record.claimed_rating_result_audit is not None else None
    if snapshot.claimed_rating_result_audit_digest != ad: raise ValueError("snapshot audit digest mismatch")
    # Evidence digest (P0-5): recompute from authoritative helper
    evidence = source_record.verified_rating_evidence
    expected_evidence_digest = compute_evidence_digest(
        evidence, warning_descriptors=warning_descriptors,
        blocker_descriptors=blocker_descriptors, failure_descriptor=evidence_failure_descriptor)
    if snapshot.verified_rating_evidence_digest != expected_evidence_digest:
        raise ValueError("snapshot evidence digest mismatch")
    # Evaluation failure (P0-6): bind payload AND descriptor
    if source_failure_descriptor is not None:
        if source_failure_descriptor.canonicalization_error is None:
            if snapshot.evaluation_failure_digest != source_failure_descriptor.payload_digest:
                raise ValueError("snapshot evaluation failure payload digest mismatch")
        else:
            if snapshot.evaluation_failure_digest is not None:
                raise ValueError("snapshot evaluation failure should be None for canonicalization-error case")
        if snapshot.source_evaluation_failure_descriptor_digest != source_failure_descriptor.descriptor_digest:
            raise ValueError("snapshot source failure descriptor digest mismatch")
    else:
        if snapshot.source_evaluation_failure_descriptor_digest is not None:
            raise ValueError("snapshot source failure descriptor should be None")
    # Evidence failure descriptor
    if evidence_failure_descriptor is not None:
        if snapshot.evidence_failure_descriptor_digest != evidence_failure_descriptor.descriptor_digest:
            raise ValueError("snapshot evidence failure descriptor digest mismatch")
    else:
        if snapshot.evidence_failure_descriptor_digest is not None:
            raise ValueError("snapshot evidence failure descriptor should be None")
    # Warning/blocker
    if len(snapshot.warning_descriptor_binding_digests) != len(warning_descriptors):
        raise ValueError("snapshot warning bindings count mismatch")
    for i, d in enumerate(warning_descriptors):
        b = build_phase3_message_descriptor_binding(Phase3MessageDescriptor(
            owner_sort_key=d.owner_sort_key, original_code=d.original_code,
            message_payload_digest=d.message_payload_digest))
        if snapshot.warning_descriptor_binding_digests[i] != b.descriptor_binding_digest:
            raise ValueError(f"snapshot warning_binding[{i}] mismatch")
    if len(snapshot.blocker_descriptor_binding_digests) != len(blocker_descriptors):
        raise ValueError("snapshot blocker bindings count mismatch")
    for i, d in enumerate(blocker_descriptors):
        b = build_phase3_message_descriptor_binding(Phase3MessageDescriptor(
            owner_sort_key=d.owner_sort_key, original_code=d.original_code,
            message_payload_digest=d.message_payload_digest))
        if snapshot.blocker_descriptor_binding_digests[i] != b.descriptor_binding_digest:
            raise ValueError(f"snapshot blocker_binding[{i}] mismatch")
    snapshot.verify_or_raise()
```

---

## 7. Phase2SourceRecordSnapshot preparation (P0-7)

```python
class Phase2SourceRecordSnapshotPreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    identity_snapshot: Phase2SourceRecordIdentitySnapshot
    identity_snapshot_digest: str
    complete_snapshot: Phase2SourceRecordSnapshot | None = None
    complete_snapshot_digest: str | None = None
    warning_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...] = ()
    blocker_descriptors: tuple[CanonicalizedEngineeringMessageDescriptor, ...] = ()
    evidence_failure_descriptor: CanonicalizedRunFailureDescriptor | None = None
    source_failure_descriptor: CanonicalizedRunFailureDescriptor | None = None
    phase3_failure: RunFailure | None = None
    phase3_failure_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None
    result_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.status is Phase3PreparationStatus.READY:
            if self.complete_snapshot is None: raise ValueError("READY requires complete_snapshot")
            if self.complete_snapshot_digest is None: raise ValueError("READY requires complete_snapshot_digest")
            if self.phase3_failure is not None: raise ValueError("READY: no failure")
            if self.phase3_failure_digest is not None: raise ValueError("READY: no failure digest")
        else:
            if self.complete_snapshot is not None: raise ValueError("FAILED: no complete_snapshot")
            if self.complete_snapshot_digest is not None: raise ValueError("FAILED: no complete_snapshot_digest")
            if self.phase3_failure is None: raise ValueError("FAILED requires failure")
            if self.phase3_failure_digest is None: raise ValueError("FAILED requires failure_digest")
        expected = sha256_digest(_snapshot_prep_result_payload(self))
        if self.result_digest != expected: raise ValueError("result_digest mismatch")
        return self

def _snapshot_prep_result_payload(r: Phase2SourceRecordSnapshotPreparationResult) -> dict[str, object]:
    return {
        "schema_version": r.schema_version, "status": r.status.value,
        "identity_snapshot_digest": r.identity_snapshot_digest,
        "complete_snapshot_digest": r.complete_snapshot_digest,
        "warning_descriptor_digests": [d.message_payload_digest for d in r.warning_descriptors],
        "blocker_descriptor_digests": [d.message_payload_digest for d in r.blocker_descriptors],
        "evidence_failure_descriptor_digest": r.evidence_failure_descriptor.descriptor_digest
            if r.evidence_failure_descriptor is not None else None,
        "source_failure_descriptor_digest": r.source_failure_descriptor.descriptor_digest
            if r.source_failure_descriptor is not None else None,
        "phase3_failure_digest": r.phase3_failure_digest,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None,
    }
```

---

## 8. Decimal, duty, count equations

### 8.1 Decimal helpers

```python
def canonical_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal: raise TypeError("must be Decimal")
    if not value.is_finite(): raise ValueError("must be finite")
    n = value.normalize()
    return Decimal("0") if n.is_zero() else n

def canonical_decimal_string(value: Decimal) -> str:
    return format(canonical_decimal(value), "f")

def to_canonical_decimal(value: float | int | Decimal) -> Decimal:
    if type(value) is bool: raise TypeError("bool not allowed")
    if type(value) is Decimal: return canonical_decimal(value)
    if type(value) is int: return canonical_decimal(Decimal(value))
    if type(value) is float:
        if not math.isfinite(value): raise ValueError("must be finite")
        return canonical_decimal(Decimal(str(value)))
    raise TypeError(f"unsupported type: {type(value).__name__}")
```

### 8.2 Duty

Duty: `required = to_canonical_decimal(sizing.required_duty_w)`; `abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)`; `rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)`; `duty_tol = max(abs_tol, rel_tol * abs(required))`; `duty_satisfied = abs(heat - required) <= duty_tol`.

### 8.3 Terminal delta-T

For `PARALLEL`: `dt1 = hot_in - cold_in; dt2 = hot_out - cold_out`. For `COUNTERFLOW`: `dt1 = hot_in - cold_out; dt2 = hot_out - cold_in`. `satisfied = min(dt1_decimal, dt2_decimal) >= to_canonical_decimal(minimum_terminal_delta_t)`.

### 8.4 Count equations

```python
def _verify_all_counts(result, ei, dispositions):
    recs = ei.evaluation_records
    p2_v = sum(1 for r in recs if r.candidate_evaluation_state == VERIFIED)
    p2_ii = sum(1 for r in recs if r.candidate_evaluation_state == INTEGRITY_INVALID)
    p2_rf = sum(1 for r in recs if r.candidate_evaluation_state == RUNTIME_FAILED)
    p2_u = sum(1 for r in recs if r.candidate_evaluation_state == UNEVALUATED)
    for name, actual, expected in [("p2_verified", result.phase2_verified_record_count, p2_v),
        ("p2_integrity", result.phase2_integrity_invalid_record_count, p2_ii),
        ("p2_runtime", result.phase2_runtime_failed_record_count, p2_rf),
        ("p2_unevaluated", result.phase2_unevaluated_record_count, p2_u)]:
        if actual != expected: raise ValueError(f"{name}: {actual} != {expected}")
    f = sum(1 for d in dispositions if d.disposition is FEASIBLE)
    inf = sum(1 for d in dispositions if d.disposition is INFEASIBLE)
    pm = sum(1 for d in dispositions if d.disposition is PROVIDER_IDENTITY_MISMATCH)
    intf = sum(1 for d in dispositions if d.disposition is INTEGRITY_FAILED)
    pf = sum(1 for d in dispositions if d.disposition is PROVENANCE_FAILED)
    rf = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED)
    u = sum(1 for d in dispositions if d.disposition is UNEVALUATED)
    for name, actual, expected in [("feasible", result.feasible_candidate_count, f),
        ("infeasible", result.infeasible_candidate_count, inf),
        ("provider_mismatch", result.provider_mismatch_count, pm),
        ("integrity_failed", result.integrity_failed_count, intf),
        ("provenance_failed", result.provenance_failed_count, pf),
        ("runtime_failed", result.runtime_failed_count, rf),
        ("unevaluated", result.unevaluated_count, u)]:
        if actual != expected: raise ValueError(f"count mismatch: {name}: {actual} != {expected}")
    rf_v = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED and d.source_candidate_evaluation_state == VERIFIED)
    rf_rf = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED and d.source_candidate_evaluation_state == RUNTIME_FAILED)
    if result.runtime_failed_from_phase2_verified_count != rf_v: raise ValueError("rf_from_verified mismatch")
    if result.runtime_failed_from_phase2_runtime_failed_count != rf_rf: raise ValueError("rf_from_rf mismatch")
```

---

## 9. Phase 2 constructor matrix

### 9.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity (VERIFIED only): `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 9.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 9.3 RUNTIME_FAILED — executable path specs (10 paths, P0-13)

```python
@dataclass(frozen=True, slots=True)
class ContextValueRule:
    key: str; value_kind: str; expected_literal: object | None = None

@dataclass(frozen=True, slots=True)
class Phase2RuntimeFailurePathSpec:
    path_id: str; hash_outcome: VerificationOutcome; provenance_outcome: VerificationOutcome
    audit_required: bool; failure_code: ErrorCode; message_rule: tuple[str, ...]
    context_keys: tuple[str, ...]; failure_stage: str | None; owner_kind: str | None
    value_rules: tuple[ContextValueRule, ...]

def safe_runtime_type_name(value: object) -> str:
    return type(value).__name__

PATH_SPECS = (
    Phase2RuntimeFailurePathSpec("P2-RF-1", NOT_RUN, NOT_RUN, True, ErrorCode.INVALID_STATE_TRANSITION,
        ("dynamic_type", "Expected exact RatingResult, got "), (), "evaluation", "evaluation", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-2", ERROR, NOT_RUN, True, ErrorCode.HASH_MISMATCH,
        ("exact", "Rating result hash verification raised."), (), "verification", "verification_runtime", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-3", PASSED, ERROR, True, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Rating result provenance verification raised."), (), "verification", "verification_runtime", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-4", PASSED, PASSED, True, ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to extract trusted evidence"), (), "verification", "verification_runtime", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-5", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"), ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"), ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-6", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "warning",
        (ContextValueRule("failure_stage","literal","rating_verification"), ContextValueRule("owner_kind","literal","warning"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"), ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-7", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "blocker",
        (ContextValueRule("failure_stage","literal","rating_verification"), ContextValueRule("owner_kind","literal","blocker"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"), ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-8", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "run_failure",
        (ContextValueRule("failure_stage","literal","rating_verification"), ContextValueRule("owner_kind","literal","run_failure"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"), ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-9", PASSED, PASSED, False, ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to build candidate evaluation identity"), (), "verification", "verification_runtime", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-10", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted rating verification failed."),
        ("failure_stage","owner_kind","owner_id","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"), ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"), ContextValueRule("safe_marker_digest","digest_format"))),
)

def match_phase2_runtime_failure_path(record: CandidateEvaluationRecord) -> str:
    if record.candidate_evaluation_state != RUNTIME_FAILED:
        raise ValueError("not RUNTIME_FAILED")
    matches = []
    for spec in PATH_SPECS:
        if record.hash_verification_outcome != spec.hash_outcome: continue
        if record.provenance_verification_outcome != spec.provenance_outcome: continue
        has_audit = record.claimed_rating_result_audit is not None
        if has_audit != spec.audit_required: continue
        if record.evaluation_failure is None: continue
        if record.evaluation_failure.code != spec.failure_code: continue
        kind, template = spec.message_rule
        if kind == "exact":
            if record.evaluation_failure.message != template: continue
        elif kind == "dynamic_type":
            # P0-13: match prefix-only, acknowledge we cannot reconstruct original type name
            if not record.evaluation_failure.message.startswith(template): continue
        if spec.context_keys:
            ctx_keys = tuple(p[0] for p in record.evaluation_failure.context)
            if ctx_keys != spec.context_keys: continue
        value_ok = True
        if spec.value_rules:
            ctx_map = dict(record.evaluation_failure.context)
            for vr in spec.value_rules:
                val = ctx_map.get(vr.key, "")
                if vr.value_kind == "literal" and val != vr.expected_literal: value_ok = False
                elif vr.value_kind == "digest_format" and not re.match(r"^sha256:[0-9a-f]{64}$", str(val)) and str(val) != "": value_ok = False
            if not value_ok: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

### 9.4 UNEVALUATED

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 10. Strict-stop

```python
def _find_stop_index(ei: Phase3EvaluationInput) -> int | None:
    for i, r in enumerate(ei.evaluation_records):
        if r.candidate_evaluation_state in (INTEGRITY_INVALID, RUNTIME_FAILED):
            return i
    return None
```

---

## 11. Phase3EvaluationInput (P0-9)

```python
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
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_record_descriptor_digests: tuple[str | None, ...]
    evaluation_input_digest: str
```

`ordered_identity_snapshot_digests` — always non-null length N. `ordered_phase2_source_record_descriptor_digests` — nullable; None when preparation failed before full snapshot construction.

---

## 12. Phase3SourceRecordBinding

```python
class Phase3SourceRecordBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    phase2_source_record_descriptor_digest: str
    verified_rating_evidence_digest: str | None
    phase2_source_identity_snapshot_digest: str
    warning_descriptor_binding_digests: tuple[str, ...]
    blocker_descriptor_binding_digests: tuple[str, ...]
    source_evaluation_failure_descriptor_digest: str | None
    evidence_failure_descriptor_digest: str | None
    binding_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.DIGEST_PATTERN.match(self.phase2_source_record_descriptor_digest): raise ValueError("invalid desc digest")
        if not self.DIGEST_PATTERN.match(self.phase2_source_identity_snapshot_digest): raise ValueError("invalid identity digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(_binding_payload(self))
        if self.binding_digest != expected: raise ValueError("binding_digest mismatch")
        return self

def _binding_payload(b: Phase3SourceRecordBinding) -> dict[str, object]:
    return {"schema_version": b.schema_version, "source_qualified_candidate_id": b.source_qualified_candidate_id,
        "evaluation_order_index": b.evaluation_order_index, "phase2_source_record_descriptor_digest": b.phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": b.verified_rating_evidence_digest,
        "phase2_source_identity_snapshot_digest": b.phase2_source_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(b.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(b.blocker_descriptor_binding_digests),
        "source_evaluation_failure_descriptor_digest": b.source_evaluation_failure_descriptor_digest,
        "evidence_failure_descriptor_digest": b.evidence_failure_descriptor_digest}
```

---

## 13. CandidateDispositionRecord (P0-17)

Full model with all validator branches (no `...`).

```python
class CandidateDispositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_qualified_candidate_id: str
    evaluation_order_index: int
    source_candidate_evaluation_state: CandidateEvaluationState
    source_hash_verification_outcome: VerificationOutcome
    source_provenance_verification_outcome: VerificationOutcome
    source_record_descriptor_digest: str
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
    source_evaluation_failure_digest: str | None
    phase3_failure_digest: str | None
    failure_origin: FailureOrigin
    failure_stage: Phase3PreparationFailureStage | None = None
    feasibility_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        for d, n in [(self.source_record_descriptor_digest, "source"), (self.feasibility_digest, "feasibility")]:
            if not self.DIGEST_PATTERN.match(d): raise ValueError(f"invalid {n} digest")
        for d, n in [(self.candidate_evaluation_identity_digest, "identity"),
                      (self.verified_rating_evidence_digest, "evidence"),
                      (self.invalid_rating_evidence_digest, "invalid"),
                      (self.source_evaluation_failure_digest, "source_failure"),
                      (self.phase3_failure_digest, "phase3")]:
            if d is not None and not self.DIGEST_PATTERN.match(d): raise ValueError(f"invalid {n} digest")
        # FEASIBLE
        if self.disposition is FEASIBLE:
            if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("FEASIBLE: source must be VERIFIED")
            if self.source_hash_verification_outcome != PASSED: raise ValueError("FEASIBLE: hash must be PASSED")
            if self.source_provenance_verification_outcome != PASSED: raise ValueError("FEASIBLE: provenance must be PASSED")
            if not self.provider_identity_matches: raise ValueError("FEASIBLE: provider must match")
            if self.rating_status != "succeeded": raise ValueError("FEASIBLE: rating must be SUCCEEDED")
            if self.diagnostic != NONE: raise ValueError("FEASIBLE: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is None: raise ValueError("FEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None: raise ValueError("FEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("FEASIBLE: invalid must be None")
            if self.primary_engineering_value is None: raise ValueError("FEASIBLE: primary required")
            if self.secondary_engineering_value is None: raise ValueError("FEASIBLE: secondary required")
            if not self.DIGEST_PATTERN.match(self.primary_engineering_value) and not all(c.isdigit() or c in ".-" for c in self.primary_engineering_value):
                raise ValueError("FEASIBLE: primary must be canonical decimal string")
            if self.source_evaluation_failure_digest is not None: raise ValueError("FEASIBLE: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("FEASIBLE: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("FEASIBLE: origin must be NONE")
        # PROVIDER_IDENTITY_MISMATCH
        elif self.disposition is PROVIDER_IDENTITY_MISMATCH:
            if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("PROVIDER_MISMATCH: source must be VERIFIED")
            if self.source_hash_verification_outcome != PASSED: raise ValueError("PROVIDER_MISMATCH: hash must be PASSED")
            if self.source_provenance_verification_outcome != PASSED: raise ValueError("PROVIDER_MISMATCH: provenance must be PASSED")
            if self.provider_identity_matches: raise ValueError("PROVIDER_MISMATCH: provider must NOT match")
            if self.diagnostic != PROVIDER_IDENTITY_MISMATCH: raise ValueError("PROVIDER_MISMATCH: diagnostic mismatch")
            if self.candidate_evaluation_identity_digest is None: raise ValueError("PROVIDER_MISMATCH: identity required")
            if self.verified_rating_evidence_digest is None: raise ValueError("PROVIDER_MISMATCH: evidence required")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("PROVIDER_MISMATCH: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.source_evaluation_failure_digest is not None: raise ValueError("PROVIDER_MISMATCH: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("PROVIDER_MISMATCH: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("PROVIDER_MISMATCH: origin must be NONE")
        # INFEASIBLE
        elif self.disposition is INFEASIBLE:
            if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("INFEASIBLE: source must be VERIFIED")
            if not self.provider_identity_matches: raise ValueError("INFEASIBLE: provider must match")
            if self.candidate_evaluation_identity_digest is None: raise ValueError("INFEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None: raise ValueError("INFEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("INFEASIBLE: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("INFEASIBLE: primary must be None")
            if self.secondary_engineering_value is not None: raise ValueError("INFEASIBLE: secondary must be None")
            if self.source_evaluation_failure_digest is not None: raise ValueError("INFEASIBLE: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("INFEASIBLE: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("INFEASIBLE: origin must be NONE")
            if self.rating_status == "succeeded":
                if self.diagnostic not in (DUTY_SHORTFALL, TERMINAL_DELTA_T_INADEQUATE): raise ValueError("INFEASIBLE+SUCCEEDED: diagnostic mismatch")
            elif self.rating_status == "blocked":
                if self.diagnostic != RATING_BLOCKED: raise ValueError("INFEASIBLE+BLOCKED: diagnostic must be RATING_BLOCKED")
            elif self.rating_status == "failed":
                if self.diagnostic != RATING_FAILED: raise ValueError("INFEASIBLE+FAILED: diagnostic must be RATING_FAILED")
            else: raise ValueError(f"INFEASIBLE: unexpected rating_status {self.rating_status}")
        # INTEGRITY_FAILED
        elif self.disposition is INTEGRITY_FAILED:
            if self.source_candidate_evaluation_state != INTEGRITY_INVALID: raise ValueError("INTEGRITY_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != FAILED: raise ValueError("INTEGRITY_FAILED: hash must be FAILED")
            if self.source_provenance_verification_outcome != NOT_RUN: raise ValueError("INTEGRITY_FAILED: provenance must be NOT_RUN")
            if self.diagnostic != INTEGRITY_FAILED: raise ValueError("INTEGRITY_FAILED: diagnostic must be INTEGRITY_FAILED")
            if self.provider_identity_matches: raise ValueError("INTEGRITY_FAILED: provider must be False")
            if self.rating_status is not None: raise ValueError("INTEGRITY_FAILED: rating must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("INTEGRITY_FAILED: warnings must be empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("INTEGRITY_FAILED: blockers must be empty")
            if self.source_evaluation_failure_digest is not None: raise ValueError("INTEGRITY_FAILED: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("INTEGRITY_FAILED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("INTEGRITY_FAILED: origin must be NONE")
        # PROVENANCE_FAILED
        elif self.disposition is PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != INTEGRITY_INVALID: raise ValueError("PROVENANCE_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != PASSED: raise ValueError("PROVENANCE_FAILED: hash must be PASSED")
            if self.source_provenance_verification_outcome != FAILED: raise ValueError("PROVENANCE_FAILED: provenance must be FAILED")
            if self.diagnostic != PROVENANCE_FAILED: raise ValueError("PROVENANCE_FAILED: diagnostic must be PROVENANCE_FAILED")
            if self.rating_status is not None: raise ValueError("PROVENANCE_FAILED: rating must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("PROVENANCE_FAILED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("PROVENANCE_FAILED: blockers empty")
            if self.source_evaluation_failure_digest is not None: raise ValueError("PROVENANCE_FAILED: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("PROVENANCE_FAILED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("PROVENANCE_FAILED: origin must be NONE")
        # UNEVALUATED
        elif self.disposition is UNEVALUATED:
            if self.source_candidate_evaluation_state != UNEVALUATED: raise ValueError("UNEVALUATED: source must be UNEVALUATED")
            if self.diagnostic != NONE: raise ValueError("UNEVALUATED: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is not None: raise ValueError("UNEVALUATED: identity must be None")
            if self.verified_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: evidence must be None")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("UNEVALUATED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("UNEVALUATED: blockers empty")
            if self.source_evaluation_failure_digest is not None: raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("UNEVALUATED: origin must be NONE")
        # RUNTIME_FAILED
        elif self.disposition is RUNTIME_FAILED:
            if self.primary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.failure_origin == PHASE2_EVALUATION:
                if self.source_evaluation_failure_digest is None: raise ValueError("RF(P2): source failure required")
                if self.phase3_failure_digest is not None: raise ValueError("RF(P2): phase3 failure must be None")
                if self.source_candidate_evaluation_state != RUNTIME_FAILED: raise ValueError("RF(P2): source must be RF")
                if self.diagnostic != PHASE2_RUNTIME_FAILED: raise ValueError("RF(P2): diagnostic must be PHASE2_RUNTIME_FAILED")
                valid = [(NOT_RUN,NOT_RUN),(ERROR,NOT_RUN),(PASSED,ERROR),(PASSED,PASSED)]
                if (self.source_hash_verification_outcome, self.source_provenance_verification_outcome) not in valid:
                    raise ValueError("RF(P2): invalid outcome combo")
                if self.candidate_evaluation_identity_digest is not None: raise ValueError("RF(P2): identity must be None")
                if self.verified_rating_evidence_digest is not None: raise ValueError("RF(P2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None: raise ValueError("RF(P2): invalid must be None")
                if len(self.warning_descriptors) != 0: raise ValueError("RF(P2): warnings empty")
                if len(self.blocker_descriptors) != 0: raise ValueError("RF(P2): blockers empty")
            elif self.failure_origin == PHASE3_CLASSIFICATION:
                if self.phase3_failure_digest is None: raise ValueError("RF(P3): phase3 failure required")
                if self.source_evaluation_failure_digest is not None: raise ValueError("RF(P3): source failure must be None")
                if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("RF(P3): source must be VERIFIED")
                if self.source_hash_verification_outcome != PASSED: raise ValueError("RF(P3): hash must be PASSED")
                if self.source_provenance_verification_outcome != PASSED: raise ValueError("RF(P3): provenance must be PASSED")
                if self.diagnostic != PHASE3_RUNTIME_FAILED: raise ValueError("RF(P3): diagnostic must be PHASE3_RUNTIME_FAILED")
                stage = self.failure_stage
                if stage in (SOURCE_BINDING, CLASSIFICATION_INPUT):
                    if self.verified_rating_evidence_digest is None: raise ValueError("RF(P3): evidence required for stage")
                else:
                    if self.verified_rating_evidence_digest is not None: raise ValueError("RF(P3): evidence absent for stage")
                if self.candidate_evaluation_identity_digest is None: raise ValueError("RF(P3): identity required (retained)")
                if self.invalid_rating_evidence_digest is not None: raise ValueError("RF(P3): invalid must be None")
            else: raise ValueError(f"unexpected failure_origin: {self.failure_origin}")
        else: raise ValueError(f"unknown disposition: {self.disposition}")
        return self

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest(): raise ValueError("feasibility_digest mismatch")

def candidate_disposition_payload(r: CandidateDispositionRecord) -> dict[str, object]:
    return {"source_qualified_candidate_id": r.source_qualified_candidate_id,
        "evaluation_order_index": r.evaluation_order_index,
        "source_candidate_evaluation_state": r.source_candidate_evaluation_state.value,
        "source_hash_verification_outcome": r.source_hash_verification_outcome.value,
        "source_provenance_verification_outcome": r.source_provenance_verification_outcome.value,
        "source_record_descriptor_digest": r.source_record_descriptor_digest,
        "disposition": r.disposition.value, "diagnostic": r.diagnostic.value,
        "provider_identity_matches": r.provider_identity_matches, "rating_status": r.rating_status,
        "candidate_evaluation_identity_digest": r.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": r.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": r.invalid_rating_evidence_digest,
        "primary_engineering_value": r.primary_engineering_value,
        "secondary_engineering_value": r.secondary_engineering_value,
        "warning_descriptor_digests": [d.message_payload_digest for d in r.warning_descriptors],
        "blocker_descriptor_digests": [d.message_payload_digest for d in r.blocker_descriptors],
        "source_evaluation_failure_digest": r.source_evaluation_failure_digest,
        "phase3_failure_digest": r.phase3_failure_digest,
        "failure_origin": r.failure_origin.value,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None}
```

---

## 14. Builder helpers (P0-15, P0-16)

All builders receive `source_record_descriptor_digest`, cached warning/blocker descriptors, and cached failure descriptor. None re-reads original RunFailure context.

```python
def build_candidate_disposition_record(**kwargs) -> CandidateDispositionRecord:
    payload = {k: v.value if hasattr(v, 'value') and isinstance(v, StrEnum) else v
               for k, v in kwargs.items() if k != "warning_descriptors" and k != "blocker_descriptors"}
    payload["warning_descriptor_digests"] = [d.message_payload_digest for d in kwargs.get("warning_descriptors", ())]
    payload["blocker_descriptor_digests"] = [d.message_payload_digest for d in kwargs.get("blocker_descriptors", ())]
    feasibility_digest = sha256_digest(payload)
    return CandidateDispositionRecord(**kwargs, feasibility_digest=feasibility_digest)

def _map_non_verified(rec, *, source_record_descriptor_digest: str,
                      source_failure_descriptor: CanonicalizedRunFailureDescriptor | None,
                      warning_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
                      blocker_descriptors: tuple[Phase3MessageDescriptor, ...] = ()):
    if rec.candidate_evaluation_state == INTEGRITY_INVALID:
        diag = INTEGRITY_FAILED if rec.hash_verification_outcome == FAILED else PROVENANCE_FAILED
        disp = INTEGRITY_FAILED if rec.hash_verification_outcome == FAILED else PROVENANCE_FAILED
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            disposition=disp, diagnostic=diag, provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status, candidate_evaluation_identity_digest=None,
            verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=rec.invalid_rating_evidence.invalid_evidence_digest
                if rec.invalid_rating_evidence is not None else None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(), source_evaluation_failure_digest=None,
            phase3_failure_digest=None, failure_origin=NONE)
    elif rec.candidate_evaluation_state == RUNTIME_FAILED:
        sf_digest = source_failure_descriptor.payload_digest if source_failure_descriptor is not None and source_failure_descriptor.canonicalization_error is None else None
        return build_candidate_disposition_record(
            ..., source_record_descriptor_digest=source_record_descriptor_digest,
            disposition=RUNTIME_FAILED, diagnostic=PHASE2_RUNTIME_FAILED,
            source_evaluation_failure_digest=sf_digest, failure_origin=PHASE2_EVALUATION, ...)
    elif rec.candidate_evaluation_state == UNEVALUATED:
        return build_candidate_disposition_record(
            ..., source_record_descriptor_digest=source_record_descriptor_digest,
            disposition=UNEVALUATED, diagnostic=NONE, failure_origin=NONE, ...)
    raise ValueError(f"unexpected state: {rec.candidate_evaluation_state}")
```

(Remaining builders follow the same pattern: `source_record_descriptor_digest`, `warning_descriptors`, `blocker_descriptors`, cached `source_evaluation_failure_digest` / `phase3_failure_digest`.)

---

## 15. Classifier (P0-15)

```python
def classify_candidate(input: Phase3CandidateClassificationInput,
                       warning_descriptors: tuple[Phase3MessageDescriptor, ...],
                       blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
                       source_failure_descriptor: CanonicalizedRunFailureDescriptor | None,
                       ) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence
    eb = input.evidence_binding
    p2d = input.source_record_descriptor_digest
    if rec.candidate_evaluation_state != VERIFIED:
        return _map_non_verified(rec, source_record_descriptor_digest=p2d,
            source_failure_descriptor=source_failure_descriptor)
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, eb, source_record_descriptor_digest=p2d,
            warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if rec.rating_status is None:
        return _phase3_runtime(rec, eb, PHASE3_MISSING_RATING_STATUS, "No rating status.", None,
            source_record_descriptor_digest=p2d)
    if rec.rating_status == "blocked":
        vf = validate_blocked_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_record_descriptor_digest=p2d)
        return _build_infeasible(rec, eb, RATING_BLOCKED, source_record_descriptor_digest=p2d,
            warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if rec.rating_status == "failed":
        vf = validate_failed_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_record_descriptor_digest=p2d)
        return _build_infeasible(rec, eb, RATING_FAILED, source_record_descriptor_digest=p2d,
            warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if evidence is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "No evidence.", None,
            source_record_descriptor_digest=p2d)
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Missing thermal metrics.", None,
            source_record_descriptor_digest=p2d)
    if evidence.area_outer_m2 is None or not (evidence.area_outer_m2 > 0) or evidence.area_inner_m2 is None or not (evidence.area_inner_m2 > 0):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-positive area.", None,
            source_record_descriptor_digest=p2d)
    if evidence.failure is not None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Has failure.", None,
            source_record_descriptor_digest=p2d)
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-finite metric.", None,
            source_record_descriptor_digest=p2d)
    required = to_canonical_decimal(sizing.required_duty_w)
    duty_tol = max(to_canonical_decimal(sizing.duty_absolute_tolerance_w),
                   to_canonical_decimal(sizing.duty_relative_tolerance) * abs(required))
    if abs(heat_w - required) > duty_tol:
        return _build_infeasible(rec, eb, DUTY_SHORTFALL, source_record_descriptor_digest=p2d,
            warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    fa = sizing.flow_arrangement
    if fa == "parallel":
        dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
    if min(dt1, dt2) < to_canonical_decimal(sizing.minimum_terminal_delta_t):
        return _build_infeasible(rec, eb, TERMINAL_DELTA_T_INADEQUATE, source_record_descriptor_digest=p2d,
            warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    return _build_feasible(rec, evidence, eb, source_record_descriptor_digest=p2d,
        warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
```

---

## 16. Ranking, OptimizationResult

(Full definitions — same as prior final round with `ordered_identity_snapshot_digests` and nullable `ordered_phase2_source_record_descriptor_digests`.)

---

## 17. External verifier (P0-18, P0-19)

Verifies: input binding, identity snapshots, nullable snapshots, nullable bindings, preparation results, classification replay, descriptor binding tuple lengths and full equality, ordered disposition digests, counts, ranked one-to-one coverage, frozen sort key, Top-N, warning/blocker aggregation, strict-stop, result core hash, provenance, envelope hash, UUID.

Key excerpt for descriptor tuple checks:

```python
if len(dr.warning_descriptors) != len(warning_bindings[i]):
    raise ValueError(f"[{i}] warning descriptor count {len(dr.warning_descriptors)} != {len(warning_bindings[i])}")
for j, d in enumerate(dr.warning_descriptors):
    verify_phase3_message_descriptor_or_raise(d)
    b = warning_bindings[i][j]
    if d.owner_sort_key != b.owner_sort_key: raise ValueError(f"[{i}] warning[{j}] sort_key mismatch")
    if d.original_code != b.original_code: raise ValueError(f"[{i}] warning[{j}] code mismatch")
    if d.message_payload_digest != b.message_payload_digest: raise ValueError(f"[{i}] warning[{j}] digest mismatch")
if len(dr.blocker_descriptors) != len(blocker_bindings[i]):
    raise ValueError(f"[{i}] blocker descriptor count mismatch")
for j, d in enumerate(dr.blocker_descriptors):
    ...
```

---

## 18. Provenance (P0-20, P0-21)

### 18.1 DAG topology

Node roles and order: root, sizing_request, passed_gate, candidate_set, identity_snapshot_set, source_snapshot_set, evaluation_input, source_binding_set, preparation_result_set, disposition[0..N-1], ranked[0..F-1], top_n_selection, result_core, optimizer.

Edges preserve nullable positions — no `[d for d in list if d is not None]`:

```python
identity_snapshot_payload = sha256_digest({
    "ordered_identity_snapshot_digests": list(result.ordered_identity_snapshot_digests)})
source_snapshot_payload = sha256_digest({
    "ordered_source_snapshot_digests": list(result.ordered_phase2_source_snapshot_digests)})
source_binding_payload = sha256_digest({
    "ordered_source_binding_digests": list(result.ordered_phase3_source_binding_digests)})
```

### 18.2 Cycle detection

```python
def _has_cycle(edges: tuple[tuple[str, str, str], ...]) -> bool:
    adj = {}
    for s, t, _ in edges:
        adj.setdefault(s, []).append(t)
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for s, t, _ in edges for n in (s, t)}
    def dfs(u):
        color[u] = GRAY
        for v in adj.get(u, []):
            if color.get(v) == GRAY: return True
            if color.get(v) == WHITE and dfs(v): return True
        color[u] = BLACK
        return False
    for u in list(color):
        if color[u] == WHITE and dfs(u): return True
    return False
```

---

## 19. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
