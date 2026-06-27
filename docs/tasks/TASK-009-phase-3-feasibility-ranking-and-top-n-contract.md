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

class Phase3BatchFailureStage(StrEnum):
    TOP_LEVEL_PREPARATION_FAILURE = "top_level_preparation_failure"

# New ErrorCode string values (added to existing ErrorCode)
# PHASE3_MISSING_RATING_STATUS = "phase3_missing_rating_status"
# PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
# PHASE3_STRICT_STOP = "phase3_strict_stop"
# PHASE3_TRUSTED_EVIDENCE_INCOMPLETE = "phase3_trusted_evidence_incomplete"
```

All string values above are stable and frozen. No implementation-time naming changes.

---

## 3. Phase3MessageDescriptor and bindings

### 3.1 Phase3MessageDescriptor

```python
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
```

### 3.2 Phase3MessageDescriptorBinding (P1-1)

```python
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
            "owner_sort_key": list(self.owner_sort_key),
            "original_code": self.original_code,
            "message_payload_digest": self.message_payload_digest,
        })
        if self.descriptor_binding_digest != expected: raise ValueError("descriptor_binding_digest mismatch")
        return self

def phase3_message_descriptor_binding_payload_from_values(
    *,
    owner_sort_key: tuple[str, str, str, str, tuple[str, ...], str],
    original_code: str,
    message_payload_digest: str,
) -> dict[str, object]:
    return {
        "owner_sort_key": list(owner_sort_key),
        "original_code": original_code,
        "message_payload_digest": message_payload_digest,
    }

def build_phase3_message_descriptor_binding(
    descriptor: Phase3MessageDescriptor,
) -> Phase3MessageDescriptorBinding:
    payload = phase3_message_descriptor_binding_payload_from_values(
        owner_sort_key=descriptor.owner_sort_key,
        original_code=descriptor.original_code,
        message_payload_digest=descriptor.message_payload_digest,
    )
    digest = sha256_digest(payload)
    return Phase3MessageDescriptorBinding(
        owner_sort_key=descriptor.owner_sort_key,
        original_code=descriptor.original_code,
        message_payload_digest=descriptor.message_payload_digest,
        descriptor_binding_digest=digest,
    )
```

### 3.3 Phase3RunFailureDescriptor and Binding (P0-3, P1-1)

```python
class Phase3RunFailureDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    payload_digest: str
    code: str
    message: str
    context_key_order: tuple[str, ...]
    descriptor_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.DIGEST_PATTERN.match(self.payload_digest): raise ValueError("invalid payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_digest): raise ValueError("invalid descriptor_digest")
        expected = sha256_digest({
            "payload_digest": self.payload_digest,
            "code": self.code,
            "message": self.message,
            "context_key_order": list(self.context_key_order),
        })
        if self.descriptor_digest != expected: raise ValueError("descriptor_digest mismatch")
        return self

class Phase3RunFailureDescriptorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    payload_digest: str
    descriptor_binding_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.DIGEST_PATTERN.match(self.payload_digest): raise ValueError("invalid payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest): raise ValueError("invalid descriptor_binding_digest")
        expected = sha256_digest({"payload_digest": self.payload_digest})
        if self.descriptor_binding_digest != expected: raise ValueError("descriptor_binding_digest mismatch")
        return self

def phase3_run_failure_descriptor_binding_payload_from_values(
    *,
    payload_digest: str,
    descriptor_digest: str,
) -> dict[str, object]:
    return {"payload_digest": payload_digest, "descriptor_digest": descriptor_digest}

def build_phase3_run_failure_descriptor(
    failure: RunFailure,
) -> Phase3RunFailureDescriptor:
    payload_digest = sha256_digest(run_failure_payload(failure))
    ctx_keys = tuple(p[0] for p in failure.context)
    desc_payload = {"payload_digest": payload_digest, "code": failure.code.value, "message": failure.message, "context_key_order": list(ctx_keys)}
    descriptor_digest = sha256_digest(desc_payload)
    return Phase3RunFailureDescriptor(
        payload_digest=payload_digest,
        code=failure.code.value,
        message=failure.message,
        context_key_order=ctx_keys,
        descriptor_digest=descriptor_digest,
    )

def build_phase3_run_failure_descriptor_binding(
    descriptor: Phase3RunFailureDescriptor,
) -> Phase3RunFailureDescriptorBinding:
    payload_digest = descriptor.payload_digest
    binding_payload = {"payload_digest": payload_digest}
    binding_digest = sha256_digest(binding_payload)
    return Phase3RunFailureDescriptorBinding(
        payload_digest=payload_digest,
        descriptor_binding_digest=binding_digest,
    )
```

### 3.4 Descriptor verification helper

```python
def verify_phase3_message_descriptor_or_raise(
    descriptor: Phase3MessageDescriptor,
) -> None:
    if not descriptor.original_code: raise ValueError("descriptor original_code must be non-empty")
    if not descriptor.DIGEST_PATTERN.match(descriptor.message_payload_digest):
        raise ValueError("descriptor message_payload_digest invalid")
    if len(descriptor.owner_sort_key) != 6: raise ValueError("descriptor owner_sort_key length != 6")
    if descriptor.owner_sort_key[1] != descriptor.original_code:
        raise ValueError("descriptor owner_sort_key[1] != original_code")
```

---

## 4. Phase2SourceRecordIdentitySnapshot (P0-7)

Minimal identity snapshot that always exists — even when message canonicalization fails. Constructed before any descriptors are computed.

```python
class Phase2SourceRecordIdentitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    source_record_base_digest: str
    identity_snapshot_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.source_record_base_digest): raise ValueError("invalid source_record_base_digest")
        if not self.DIGEST_PATTERN.match(self.identity_snapshot_digest): raise ValueError("invalid identity_snapshot_digest")
        expected = sha256_digest({
            "schema_version": self.schema_version,
            "source_qualified_candidate_id": self.source_qualified_candidate_id,
            "evaluation_order_index": self.evaluation_order_index,
            "source_record_base_digest": self.source_record_base_digest,
        })
        if self.identity_snapshot_digest != expected: raise ValueError("identity_snapshot_digest mismatch")
        return self

def phase2_source_record_identity_snapshot_payload_from_values(**kwargs) -> dict[str, object]:
    return {
        "schema_version": kwargs["schema_version"],
        "source_qualified_candidate_id": kwargs["source_qualified_candidate_id"],
        "evaluation_order_index": kwargs["evaluation_order_index"],
        "source_record_base_digest": kwargs["source_record_base_digest"],
    }

def build_phase2_source_record_identity_snapshot(
    *,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    source_record_base_digest: str,
) -> Phase2SourceRecordIdentitySnapshot:
    payload = phase2_source_record_identity_snapshot_payload_from_values(
        schema_version=1,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_record_base_digest=source_record_base_digest,
    )
    identity_snapshot_digest = sha256_digest(payload)
    return Phase2SourceRecordIdentitySnapshot(
        schema_version=1,
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_record_base_digest=source_record_base_digest,
        identity_snapshot_digest=identity_snapshot_digest,
    )
```

---

## 5. Phase2SourceRecordSnapshot (P0-1, P0-4, P0-5, P0-6)

### 5.1 Model

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

def _snapshot_payload(s: Phase2SourceRecordSnapshot) -> dict[str, object]:
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
```

### 5.2 One-shot factory (P0-1)

```python
def phase2_source_record_snapshot_payload_from_values(
    *,
    schema_version: int = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    candidate_evaluation_state: CandidateEvaluationState,
    feasible: bool,
    feasibility_status: Phase2FeasibilityStatus,
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
    source_evaluation_failure_descriptor_digest: str | None,
    evidence_failure_descriptor_digest: str | None,
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
        "source_evaluation_failure_descriptor_digest": source_evaluation_failure_descriptor_digest,
        "evidence_failure_descriptor_digest": evidence_failure_descriptor_digest,
    }

def build_phase2_source_record_snapshot(**fields) -> Phase2SourceRecordSnapshot:
    payload = phase2_source_record_snapshot_payload_from_values(**fields)
    snapshot_digest = sha256_digest(payload)
    return Phase2SourceRecordSnapshot(**fields, snapshot_digest=snapshot_digest)
```

### 5.3 Verification (P0-6)

```python
def verify_phase2_source_record_snapshot_or_raise(
    snapshot: Phase2SourceRecordSnapshot,
    *,
    source_record: CandidateEvaluationRecord,
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    evidence_failure_descriptor: Phase3RunFailureDescriptor | None,
    source_failure_descriptor: Phase3RunFailureDescriptor | None,
) -> None:
    if snapshot.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
        raise ValueError("snapshot candidate_id mismatch")
    if snapshot.evaluation_order_index != source_record.evaluation_order_index:
        raise ValueError("snapshot index mismatch")
    if snapshot.candidate_evaluation_state != source_record.candidate_evaluation_state:
        raise ValueError("snapshot state mismatch")
    if snapshot.feasible != source_record.feasible:
        raise ValueError("snapshot feasible mismatch")
    if snapshot.feasibility_status != source_record.feasibility_status:
        raise ValueError("snapshot feasibility_status mismatch")
    if snapshot.hash_verification_outcome != source_record.hash_verification_outcome:
        raise ValueError("snapshot hash outcome mismatch")
    if snapshot.provenance_verification_outcome != source_record.provenance_verification_outcome:
        raise ValueError("snapshot provenance outcome mismatch")
    if snapshot.provider_identity_matches != source_record.provider_identity_matches:
        raise ValueError("snapshot provider flag mismatch")
    if snapshot.rating_status != source_record.rating_status:
        raise ValueError("snapshot rating_status mismatch")
    expected_identity_digest = (
        source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if source_record.candidate_evaluation_identity is not None else None
    )
    if snapshot.candidate_evaluation_identity_digest != expected_identity_digest:
        raise ValueError("snapshot identity digest mismatch")
    expected_invalid_digest = (
        source_record.invalid_rating_evidence.invalid_evidence_digest
        if source_record.invalid_rating_evidence is not None else None
    )
    if snapshot.invalid_rating_evidence_digest != expected_invalid_digest:
        raise ValueError("snapshot invalid evidence digest mismatch")
    expected_audit_digest = (
        source_record.claimed_rating_result_audit.audit_digest
        if source_record.claimed_rating_result_audit is not None else None
    )
    if snapshot.claimed_rating_result_audit_digest != expected_audit_digest:
        raise ValueError("snapshot audit digest mismatch")
    # Failure digests: compare cached descriptor digests, not re-runs (P0-6)
    if source_failure_descriptor is not None:
        if snapshot.source_evaluation_failure_descriptor_digest != source_failure_descriptor.descriptor_digest:
            raise ValueError("snapshot source failure descriptor digest mismatch")
    else:
        if snapshot.source_evaluation_failure_descriptor_digest is not None:
            raise ValueError("snapshot source failure desciptor digest should be None")
    if evidence_failure_descriptor is not None:
        if snapshot.evidence_failure_descriptor_digest != evidence_failure_descriptor.descriptor_digest:
            raise ValueError("snapshot evidence failure descriptor digest mismatch")
    else:
        if snapshot.evidence_failure_descriptor_digest is not None:
            raise ValueError("snapshot evidence failure descriptor digest should be None")
    # Warning/blocker bindings
    if len(snapshot.warning_descriptor_binding_digests) != len(warning_bindings):
        raise ValueError("snapshot warning bindings count mismatch")
    for i, b in enumerate(warning_bindings):
        if snapshot.warning_descriptor_binding_digests[i] != b.descriptor_binding_digest:
            raise ValueError(f"snapshot warning_binding[{i}] mismatch")
    if len(snapshot.blocker_descriptor_binding_digests) != len(blocker_bindings):
        raise ValueError("snapshot blocker bindings count mismatch")
    for i, b in enumerate(blocker_bindings):
        if snapshot.blocker_descriptor_binding_digests[i] != b.descriptor_binding_digest:
            raise ValueError(f"snapshot blocker_binding[{i}] mismatch")
    snapshot.verify_or_raise()
```

---

## 6. Snapshot preparation (P0-4, P0-5, P0-7)

### 6.1 Preparation result

```python
class Phase2SourceRecordSnapshotPreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    identity_snapshot: Phase2SourceRecordIdentitySnapshot
    complete_snapshot: Phase2SourceRecordSnapshot | None = None
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    evidence_failure_descriptor: Phase3RunFailureDescriptor | None = None
    source_failure_descriptor: Phase3RunFailureDescriptor | None = None
    phase3_failure: RunFailure | None = None
    phase3_failure_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None
    result_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.status is Phase3PreparationStatus.READY:
            if self.complete_snapshot is None: raise ValueError("READY requires complete_snapshot")
            if self.phase3_failure is not None: raise ValueError("READY: no failure")
            if self.phase3_failure_digest is not None: raise ValueError("READY: no failure digest")
            if self.failure_stage is not None: raise ValueError("READY: no failure_stage")
        else:
            if self.complete_snapshot is not None: raise ValueError("FAILED: no complete_snapshot")
            if self.phase3_failure is None: raise ValueError("FAILED requires failure")
            if self.phase3_failure_digest is None: raise ValueError("FAILED requires failure_digest")
            if self.failure_stage is None: raise ValueError("FAILED requires failure_stage")
        return self
```

### 6.2 Identity-only helper (no-arg)

```python
def _source_record_base_digest(rec: CandidateEvaluationRecord) -> str:
    return sha256_digest({
        "source_qualified_candidate_id": rec.source_qualified_candidate_id,
        "evaluation_order_index": rec.evaluation_order_index,
        "candidate_evaluation_state": rec.candidate_evaluation_state.value,
    })
```

### 6.3 Authority Phase 2 evidence helper call (P0-4, P0-5)

```python
def _evidence_digest_from_descriptors(
    evidence: VerifiedRatingEvidenceSnapshot | None,
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    evidence_failure_descriptor: Phase3RunFailureDescriptor | None,
    hash_outcome: VerificationOutcome,
    provenance_outcome: VerificationOutcome,
) -> str | None:
    if evidence is None:
        return None
    payload = verified_rating_evidence_payload_from_descriptors(
        evidence,
        warning_descriptors=tuple(
            Phase3MessageDescriptor(
                owner_sort_key=b.owner_sort_key,
                original_code=b.original_code,
                message_payload_digest=b.message_payload_digest,
            )
            for b in warning_bindings
        ),
        blocker_descriptors=tuple(
            Phase3MessageDescriptor(
                owner_sort_key=b.owner_sort_key,
                original_code=b.original_code,
                message_payload_digest=b.message_payload_digest,
            )
            for b in blocker_bindings
        ),
        failure_descriptor=evidence_failure_descriptor,
        hash_verification_outcome=hash_outcome,
        provenance_verification_outcome=provenance_outcome,
    )
    return sha256_digest(payload)
```

### 6.4 Snapshot preparation function

```python
def prepare_phase2_source_record_snapshot(
    source_record: CandidateEvaluationRecord,
) -> Phase2SourceRecordSnapshotPreparationResult:
    candidate_id = source_record.source_qualified_candidate_id
    index = source_record.evaluation_order_index
    evidence = source_record.verified_rating_evidence
    base_digest = _source_record_base_digest(source_record)
    identity = build_phase2_source_record_identity_snapshot(
        source_qualified_candidate_id=candidate_id,
        evaluation_order_index=index,
        source_record_base_digest=base_digest,
    )

    # Canonicalize messages exactly once
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    evidence_failure_descriptor: Phase3RunFailureDescriptor | None = None
    source_failure_descriptor: Phase3RunFailureDescriptor | None = None

    if evidence is not None:
        w_result = canonicalize_phase3_messages_or_failure(evidence.warnings, "warning", candidate_id, index, "")
        if isinstance(w_result, RunFailure):
            return _snapshot_prep_failure(identity, w_result, Phase3PreparationFailureStage.WARNING_DESCRIPTOR)
        b_result = canonicalize_phase3_messages_or_failure(evidence.blockers, "blocker", candidate_id, index, "")
        if isinstance(b_result, RunFailure):
            return _snapshot_prep_failure(identity, b_result, Phase3PreparationFailureStage.BLOCKER_DESCRIPTOR)
        warning_bindings = tuple(build_phase3_message_descriptor_binding(d) for d in w_result)
        blocker_bindings = tuple(build_phase3_message_descriptor_binding(d) for d in b_result)
        if evidence.failure is not None:
            evidence_failure_descriptor = build_phase3_run_failure_descriptor(evidence.failure)

    # Source evaluation failure — exactly once cached descriptor
    if source_record.evaluation_failure is not None:
        source_failure_descriptor = build_phase3_run_failure_descriptor(source_record.evaluation_failure)

    # Evidence digest using authoritative Phase 2 helper (P0-4, P0-5)
    evidence_digest = _evidence_digest_from_descriptors(
        evidence=evidence,
        warning_bindings=warning_bindings,
        blocker_bindings=blocker_bindings,
        evidence_failure_descriptor=evidence_failure_descriptor,
        hash_outcome=source_record.hash_verification_outcome,
        provenance_outcome=source_record.provenance_verification_outcome,
    )

    # Phase 2 descriptor digest
    identity_digest = identity.identity_snapshot_digest
    candidate_eval_id = (
        source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if source_record.candidate_evaluation_identity is not None else None
    )
    invalid_digest = (
        source_record.invalid_rating_evidence.invalid_evidence_digest
        if source_record.invalid_rating_evidence is not None else None
    )
    claimed_digest = (
        source_record.claimed_rating_result_audit.audit_digest
        if source_record.claimed_rating_result_audit is not None else None
    )
    eval_failure_digest = source_failure_descriptor.payload_digest if source_failure_descriptor is not None else None

    p2_desc_payload = {
        "source_qualified_candidate_id": candidate_id,
        "evaluation_order_index": index,
        "candidate_evaluation_state": source_record.candidate_evaluation_state.value,
        "feasible": source_record.feasible,
        "feasibility_status": source_record.feasibility_status.value,
        "hash_verification_outcome": source_record.hash_verification_outcome.value,
        "provenance_verification_outcome": source_record.provenance_verification_outcome.value,
        "provider_identity_matches": source_record.provider_identity_matches,
        "rating_status": source_record.rating_status,
        "candidate_evaluation_identity_digest": candidate_eval_id,
        "verified_rating_evidence_digest": evidence_digest,
        "invalid_rating_evidence_digest": invalid_digest,
        "claimed_rating_result_audit_digest": claimed_digest,
        "evaluation_failure_digest": eval_failure_digest,
    }
    p2_descriptor_digest = sha256_digest(p2_desc_payload)

    snapshot = build_phase2_source_record_snapshot(
        schema_version=1,
        source_qualified_candidate_id=candidate_id,
        evaluation_order_index=index,
        candidate_evaluation_state=source_record.candidate_evaluation_state,
        feasible=source_record.feasible,
        feasibility_status=source_record.feasibility_status,
        hash_verification_outcome=source_record.hash_verification_outcome,
        provenance_verification_outcome=source_record.provenance_verification_outcome,
        provider_identity_matches=source_record.provider_identity_matches,
        rating_status=source_record.rating_status,
        candidate_evaluation_identity_digest=candidate_eval_id,
        verified_rating_evidence_digest=evidence_digest,
        invalid_rating_evidence_digest=invalid_digest,
        claimed_rating_result_audit_digest=claimed_digest,
        evaluation_failure_digest=eval_failure_digest,
        phase2_source_record_descriptor_digest=p2_descriptor_digest,
        warning_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in warning_bindings),
        blocker_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in blocker_bindings),
        source_evaluation_failure_descriptor_digest=source_failure_descriptor.descriptor_digest if source_failure_descriptor is not None else None,
        evidence_failure_descriptor_digest=evidence_failure_descriptor.descriptor_digest if evidence_failure_descriptor is not None else None,
    )

    return Phase2SourceRecordSnapshotPreparationResult(
        status=Phase3PreparationStatus.READY,
        identity_snapshot=identity,
        complete_snapshot=snapshot,
        warning_bindings=warning_bindings,
        blocker_bindings=blocker_bindings,
        evidence_failure_descriptor=evidence_failure_descriptor,
        source_failure_descriptor=source_failure_descriptor,
        result_digest=identity.identity_snapshot_digest,
    )

def _snapshot_prep_failure(
    identity: Phase2SourceRecordIdentitySnapshot,
    failure: RunFailure,
    stage: Phase3PreparationFailureStage,
) -> Phase2SourceRecordSnapshotPreparationResult:
    failure_digest = sha256_digest(run_failure_payload(failure))
    return Phase2SourceRecordSnapshotPreparationResult(
        status=Phase3PreparationStatus.FAILED,
        identity_snapshot=identity,
        phase3_failure=failure,
        phase3_failure_digest=failure_digest,
        failure_stage=stage,
        result_digest=identity.identity_snapshot_digest,
    )
```

---

## 7. Phase3EvaluationInput

### 7.1 Model

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
    ordered_phase2_source_record_descriptor_digests: tuple[str, ...]
    ordered_identity_snapshot_digests: tuple[str, ...]
    evaluation_input_digest: str
```

### 7.2 Helpers

```python
def evaluation_record_descriptor_payload(
    record: CandidateEvaluationRecord,
    snapshot: Phase2SourceRecordSnapshot,
) -> dict[str, object]:
    return {
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "evaluation_order_index": record.evaluation_order_index,
        "candidate_evaluation_state": record.candidate_evaluation_state.value,
        "feasible": record.feasible,
        "feasibility_status": record.feasibility_status.value,
        "hash_verification_outcome": record.hash_verification_outcome.value,
        "provenance_verification_outcome": record.provenance_verification_outcome.value,
        "provider_identity_matches": record.provider_identity_matches,
        "rating_status": record.rating_status,
        "candidate_evaluation_identity_digest": snapshot.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": snapshot.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": snapshot.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": snapshot.claimed_rating_result_audit_digest,
        "evaluation_failure_digest": snapshot.evaluation_failure_digest,
    }

def evaluation_input_payload(input: Phase3EvaluationInput) -> dict[str, object]:
    return {
        "schema_version": input.schema_version,
        "sizing_request_identity_digest": input.sizing_request_identity_digest,
        "candidate_set_digest": input.candidate_set_digest,
        "gate_digest": input.gate_digest,
        "evaluation_record_count": input.evaluation_record_count,
        "ordered_phase2_source_record_descriptor_digests": list(input.ordered_phase2_source_record_descriptor_digests),
        "ordered_identity_snapshot_digests": list(input.ordered_identity_snapshot_digests),
    }
```

### 7.3 13-step verify_or_raise()

Same as prior round with added identity snapshot digest check.

---

## 8. Phase 2 constructor matrix

### 8.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity (VERIFIED only): `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 8.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 8.3 RUNTIME_FAILED — executable path specs (10 paths, P0-16)

```python
@dataclass(frozen=True, slots=True)
class ContextValueRule:
    key: str
    value_kind: str
    expected_literal: object | None = None

@dataclass(frozen=True, slots=True)
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

def safe_runtime_type_name(value: object) -> str:
    return type(value).__name__

PATH_SPECS = (...unchanged...)

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
            # P0-16: exact message reconstruction
            claimed_value = record.claimed_rating_result_audit.rating_result if record.claimed_rating_result_audit is not None else None
            expected_msg = template + safe_runtime_type_name(claimed_value)
            if record.evaluation_failure.message != expected_msg: continue
        if spec.context_keys:
            ctx_pairs = record.evaluation_failure.context
            ctx_keys = tuple(p[0] for p in ctx_pairs)
            if ctx_keys != spec.context_keys: continue
        if spec.value_rules:
            value_ok = True
            ctx_map = dict(ctx_pairs)
            for vr in spec.value_rules:
                val = ctx_map.get(vr.key, "")
                if vr.value_kind == "literal":
                    if val != vr.expected_literal: value_ok = False
                elif vr.value_kind == "digest_format":
                    if not re.match(r"^sha256:[0-9a-f]{64}$", str(val)) and str(val) != "": value_ok = False
                elif vr.value_kind == "presence":
                    if not val: value_ok = False
            if not value_ok: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

---

## 9. Decimal, duty, counts, strict-stop

(Unchanged from prior rounds)

---

## 10. Phase3SourceRecordBinding (P0-2, P0-8)

### 10.1 Model

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

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.phase2_source_record_descriptor_digest): raise ValueError("invalid source desc digest")
        if not self.DIGEST_PATTERN.match(self.phase2_source_identity_snapshot_digest): raise ValueError("invalid identity snapshot digest")
        if self.verified_rating_evidence_digest is not None and not self.DIGEST_PATTERN.match(self.verified_rating_evidence_digest):
            raise ValueError("invalid evidence digest")
        if self.source_evaluation_failure_descriptor_digest is not None and not self.DIGEST_PATTERN.match(self.source_evaluation_failure_descriptor_digest):
            raise ValueError("invalid source failure desc digest")
        if self.evidence_failure_descriptor_digest is not None and not self.DIGEST_PATTERN.match(self.evidence_failure_descriptor_digest):
            raise ValueError("invalid evidence failure desc digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(_ph3_binding_payload(self))
        if self.binding_digest != expected: raise ValueError("binding_digest mismatch")
        return self

def _ph3_binding_payload(b: Phase3SourceRecordBinding) -> dict[str, object]:
    return {
        "schema_version": b.schema_version,
        "source_qualified_candidate_id": b.source_qualified_candidate_id,
        "evaluation_order_index": b.evaluation_order_index,
        "phase2_source_record_descriptor_digest": b.phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": b.verified_rating_evidence_digest,
        "phase2_source_identity_snapshot_digest": b.phase2_source_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(b.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(b.blocker_descriptor_binding_digests),
        "source_evaluation_failure_descriptor_digest": b.source_evaluation_failure_descriptor_digest,
        "evidence_failure_descriptor_digest": b.evidence_failure_descriptor_digest,
    }
```

### 10.2 One-shot factory (P0-2)

```python
def phase3_source_record_binding_payload_from_values(
    *,
    schema_version: int = 1,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    phase2_source_record_descriptor_digest: str,
    verified_rating_evidence_digest: str | None,
    phase2_source_identity_snapshot_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_descriptor_digest: str | None,
    evidence_failure_descriptor_digest: str | None,
) -> dict[str, object]:
    return {
        "schema_version": schema_version,
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "phase2_source_record_descriptor_digest": phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "phase2_source_identity_snapshot_digest": phase2_source_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(blocker_descriptor_binding_digests),
        "source_evaluation_failure_descriptor_digest": source_evaluation_failure_descriptor_digest,
        "evidence_failure_descriptor_digest": evidence_failure_descriptor_digest,
    }

def build_phase3_source_record_binding(**fields) -> Phase3SourceRecordBinding:
    payload = phase3_source_record_binding_payload_from_values(**fields)
    binding_digest = sha256_digest(payload)
    return Phase3SourceRecordBinding(**fields, binding_digest=binding_digest)
```

---

## 11. Phase3CandidateClassificationInput (P0-10)

```python
class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_record: CandidateEvaluationRecord
    source_record_descriptor_digest: str
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    evidence_binding: Phase3SourceRecordBinding
    phase2_identity_snapshot_digest: str
    phase3_source_binding_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        return self

def candidate_evaluation_record_binding_payload(
    record: CandidateEvaluationRecord,
    snapshot: Phase2SourceRecordSnapshot,
) -> dict[str, object]:
    return {
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "evaluation_order_index": record.evaluation_order_index,
        "candidate_evaluation_state": record.candidate_evaluation_state.value,
        "feasible": record.feasible,
        "feasibility_status": record.feasibility_status.value,
        "hash_verification_outcome": record.hash_verification_outcome.value,
        "provenance_verification_outcome": record.provenance_verification_outcome.value,
        "provider_identity_matches": record.provider_identity_matches,
        "rating_status": record.rating_status,
        "candidate_evaluation_identity_digest": snapshot.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": snapshot.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": snapshot.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": snapshot.claimed_rating_result_audit_digest,
        "evaluation_failure_digest": snapshot.evaluation_failure_digest,
        "warning_descriptor_binding_digests": list(snapshot.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(snapshot.blocker_descriptor_binding_digests),
    }

def verify_phase3_classification_input_or_raise(
    value: Phase3CandidateClassificationInput,
    *,
    source_record: CandidateEvaluationRecord,
    source_snapshot: Phase2SourceRecordSnapshot,
    source_binding: Phase3SourceRecordBinding,
    candidate: ManufacturableCandidate,
    sizing_identity: SizingRequestIdentity,
) -> None:
    if value.schema_version != 1: raise ValueError("cin schema_version must be 1")
    # Full source_record binding equality (P0-10)
    if value.source_record != source_record:
        # Serialization-safe: check all fields
        if value.source_record.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("cin source_record candidate_id mismatch")
        cr_binding = candidate_evaluation_record_binding_payload(value.source_record, source_snapshot)
        sr_binding = candidate_evaluation_record_binding_payload(source_record, source_snapshot)
        if cr_binding != sr_binding:
            raise ValueError("cin source_record full binding mismatch")
    if value.phase2_identity_snapshot_digest != source_snapshot.identity_snapshot_digest:
        raise ValueError("cin identity snapshot digest mismatch")
    if value.source_record_descriptor_digest != source_snapshot.phase2_source_record_descriptor_digest:
        raise ValueError("cin descriptor_digest mismatch")
    if value.evidence_binding.binding_digest != source_binding.binding_digest:
        raise ValueError("cin binding_digest mismatch")
    if value.phase3_source_binding_digest != source_binding.binding_digest:
        raise ValueError("cin ph3 binding digest mismatch")
    if value.materialized_candidate.source_qualified_candidate_id != candidate.source_qualified_candidate_id:
        raise ValueError("cin candidate_id mismatch")
    if value.materialized_candidate.evaluation_order_index != candidate.evaluation_order_index:
        raise ValueError("cin candidate index mismatch")
    if value.sizing_request_identity.sizing_request_identity_digest != sizing_identity.sizing_request_identity_digest:
        raise ValueError("cin sizing identity mismatch")
    if value.sizing_request_identity_digest != sizing_identity.sizing_request_identity_digest:
        raise ValueError("cin sizing digest mismatch")
```

---

## 12. Phase3CandidatePreparationResult (P0-11)

```python
class Phase3CandidatePreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    source_qualified_candidate_id: str
    evaluation_order_index: int
    phase2_identity_snapshot_digest: str
    phase3_source_binding_digest: str | None = None
    classification_input_digest: str | None = None
    phase3_failure_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None
    classification_input: Phase3CandidateClassificationInput | None = None
    phase3_failure: RunFailure | None = None
    preparation_result_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None: raise ValueError("READY: missing cin")
            if self.classification_input_digest is None: raise ValueError("READY: missing cin digest")
            if self.phase3_failure is not None: raise ValueError("READY: no failure")
            if self.phase3_failure_digest is not None: raise ValueError("READY: no failure digest")
            if self.failure_stage is not None: raise ValueError("READY: no failure_stage")
            if self.phase3_source_binding_digest is None: raise ValueError("READY: binding required")
        else:
            if self.classification_input is not None: raise ValueError("FAILED: no cin")
            if self.classification_input_digest is not None: raise ValueError("FAILED: no cin digest")
            if self.phase3_failure is None: raise ValueError("FAILED: failure required")
            if self.phase3_failure_digest is None: raise ValueError("FAILED: failure digest required")
            if self.failure_stage is None: raise ValueError("FAILED: failure_stage required")
            expected_digest = sha256_digest(run_failure_payload(self.phase3_failure))
            if self.phase3_failure_digest != expected_digest: raise ValueError("FAILED: phase3_failure_digest mismatch")
        expected_pr = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected_pr: raise ValueError("preparation_result_digest mismatch")
        return self

def _prep_result_payload(r: Phase3CandidatePreparationResult) -> dict[str, object]:
    return {
        "schema_version": r.schema_version,
        "status": r.status.value,
        "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "evaluation_order_index": r.evaluation_order_index,
        "phase2_identity_snapshot_digest": r.phase2_identity_snapshot_digest,
        "phase3_source_binding_digest": r.phase3_source_binding_digest,
        "classification_input_digest": r.classification_input_digest,
        "phase3_failure_digest": r.phase3_failure_digest,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None,
    }
```

---

## 13. Preparation lifecycle

### 13.1 build_candidate_disposition_record (P0-13, P0-14, P0-15)

```python
def build_candidate_disposition_record(
    *,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    source_candidate_evaluation_state: CandidateEvaluationState,
    source_hash_verification_outcome: VerificationOutcome,
    source_provenance_verification_outcome: VerificationOutcome,
    source_record_descriptor_digest: str,
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
    source_evaluation_failure_digest: str | None,
    phase3_failure_digest: str | None,
    failure_origin: FailureOrigin,
    failure_stage: Phase3PreparationFailureStage | None = None,
) -> CandidateDispositionRecord:
    warning_descriptor_digests = tuple(d.message_payload_digest for d in warning_descriptors)
    blocker_descriptor_digests = tuple(d.message_payload_digest for d in blocker_descriptors)
    payload = {
        "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "source_candidate_evaluation_state": source_candidate_evaluation_state.value,
        "source_hash_verification_outcome": source_hash_verification_outcome.value,
        "source_provenance_verification_outcome": source_provenance_verification_outcome.value,
        "source_record_descriptor_digest": source_record_descriptor_digest,
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
        "source_evaluation_failure_digest": source_evaluation_failure_digest,
        "phase3_failure_digest": phase3_failure_digest,
        "failure_origin": failure_origin.value,
        "failure_stage": failure_stage.value if failure_stage is not None else None,
    }
    digest = sha256_digest(payload)
    return CandidateDispositionRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_candidate_evaluation_state=source_candidate_evaluation_state,
        source_hash_verification_outcome=source_hash_verification_outcome,
        source_provenance_verification_outcome=source_provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
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
        source_evaluation_failure_digest=source_evaluation_failure_digest,
        phase3_failure_digest=phase3_failure_digest,
        failure_origin=failure_origin,
        failure_stage=failure_stage,
        feasibility_digest=digest,
    )

def candidate_disposition_payload(record: CandidateDispositionRecord) -> dict[str, object]:
    return {
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "evaluation_order_index": record.evaluation_order_index,
        "source_candidate_evaluation_state": record.source_candidate_evaluation_state.value,
        "source_hash_verification_outcome": record.source_hash_verification_outcome.value,
        "source_provenance_verification_outcome": record.source_provenance_verification_outcome.value,
        "source_record_descriptor_digest": record.source_record_descriptor_digest,
        "disposition": record.disposition.value,
        "diagnostic": record.diagnostic.value,
        "provider_identity_matches": record.provider_identity_matches,
        "rating_status": record.rating_status,
        "candidate_evaluation_identity_digest": record.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": record.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": record.invalid_rating_evidence_digest,
        "primary_engineering_value": record.primary_engineering_value,
        "secondary_engineering_value": record.secondary_engineering_value,
        "warning_descriptor_digests": list(d.message_payload_digest for d in record.warning_descriptors),
        "blocker_descriptor_digests": list(d.message_payload_digest for d in record.blocker_descriptors),
        "source_evaluation_failure_digest": record.source_evaluation_failure_digest,
        "phase3_failure_digest": record.phase3_failure_digest,
        "failure_origin": record.failure_origin.value,
        "failure_stage": record.failure_stage.value if record.failure_stage is not None else None,
    }
```

### 13.2 Builder helpers (P0-13, P0-14, P0-15)

All builders receive `source_record_descriptor_digest`, `warning_descriptors`, `blocker_descriptors`, and use **cached failure digests** (not raw RunFailure).

```python
def _map_non_verified(
    rec: CandidateEvaluationRecord,
    source_record_descriptor_digest: str,
) -> CandidateDispositionRecord:
    if rec.candidate_evaluation_state == INTEGRITY_INVALID:
        if rec.hash_verification_outcome == FAILED:
            diag = INTEGRITY_FAILED; disp = INTEGRITY_FAILED
        else:
            diag = PROVENANCE_FAILED; disp = PROVENANCE_FAILED
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            disposition=disp, diagnostic=diag, provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None,
            verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=rec.invalid_rating_evidence.invalid_evidence_digest
                if rec.invalid_rating_evidence is not None else None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_digest=None, phase3_failure_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
    elif rec.candidate_evaluation_state == RUNTIME_FAILED:
        return build_candidate_disposition_record(
            ..., disposition=RUNTIME_FAILED, diagnostic=PHASE2_RUNTIME_FAILED,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_evaluation_failure_digest=...,  # from cached failure descriptor
            failure_origin=PHASE2_EVALUATION, ...)
    elif rec.candidate_evaluation_state == UNEVALUATED:
        return build_candidate_disposition_record(
            ..., disposition=UNEVALUATED, diagnostic=NONE,
            source_record_descriptor_digest=source_record_descriptor_digest,
            failure_origin=NONE, ...)
    raise ValueError(f"unexpected state: {rec.candidate_evaluation_state}")

def _build_provider_mismatch(
    rec, evidence, eb, source_record_descriptor_digest: str,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        ..., disposition=PROVIDER_IDENTITY_MISMATCH,
        source_record_descriptor_digest=source_record_descriptor_digest,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors,
        failure_origin=NONE, ...)

def _build_infeasible(
    rec, eb, diagnostic, source_record_descriptor_digest: str,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        ..., disposition=INFEASIBLE, diagnostic=diagnostic,
        source_record_descriptor_digest=source_record_descriptor_digest,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors,
        failure_origin=NONE, ...)

def _build_feasible(
    rec, evidence, eb, source_record_descriptor_digest: str,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...] = (),
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        ..., disposition=FEASIBLE, diagnostic=NONE,
        source_record_descriptor_digest=source_record_descriptor_digest,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        primary_engineering_value=..., secondary_engineering_value=...,
        warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors,
        failure_origin=NONE, ...)

def _phase3_runtime(
    rec, eb, code, msg, failure_stage,
    source_record_descriptor_digest: str,
) -> CandidateDispositionRecord:
    # Create failure exactly once (P0-15)
    failure = RunFailure(code=code, message=msg, ...)
    failure_descriptor = build_phase3_run_failure_descriptor(failure)
    return build_candidate_disposition_record(
        ..., disposition=RUNTIME_FAILED, diagnostic=PHASE3_RUNTIME_FAILED,
        source_record_descriptor_digest=source_record_descriptor_digest,
        phase3_failure_digest=failure_descriptor.payload_digest,
        failure_origin=PHASE3_CLASSIFICATION, failure_stage=failure_stage, ...)

def _phase3_runtime_from_validation(
    rec, eb, validation_failure, source_record_descriptor_digest: str,
) -> CandidateDispositionRecord:
    failure_descriptor = build_phase3_run_failure_descriptor(validation_failure)
    return build_candidate_disposition_record(
        ..., disposition=RUNTIME_FAILED, diagnostic=PHASE3_RUNTIME_FAILED,
        source_record_descriptor_digest=source_record_descriptor_digest,
        phase3_failure_digest=failure_descriptor.payload_digest,
        failure_origin=PHASE3_CLASSIFICATION, ...)
```

(Full expansions omitted for brevity; each builder has exact typed signature with `source_record_descriptor_digest`, `warning_descriptors`, `blocker_descriptors`, and uses `failure_descriptor.payload_digest` instead of `run_failure_payload(original_failure)`.)

### 13.3 Classifier (unchanged logic, updated builders)

```python
def classify_candidate(input: Phase3CandidateClassificationInput) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence
    eb = input.evidence_binding
    p2_desc_digest = input.source_record_descriptor_digest
    if rec.candidate_evaluation_state != VERIFIED:
        return _map_non_verified(rec, source_record_descriptor_digest=p2_desc_digest)
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, eb, source_record_descriptor_digest=p2_desc_digest)
    if rec.rating_status is None:
        return _phase3_runtime(rec, eb, PHASE3_MISSING_RATING_STATUS, "No rating status.", None,
                               source_record_descriptor_digest=p2_desc_digest)
    if rec.rating_status == "blocked":
        vf = validate_blocked_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_record_descriptor_digest=p2_desc_digest)
        return _build_infeasible(rec, eb, RATING_BLOCKED, source_record_descriptor_digest=p2_desc_digest)
    if rec.rating_status == "failed":
        vf = validate_failed_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_record_descriptor_digest=p2_desc_digest)
        return _build_infeasible(rec, eb, RATING_FAILED, source_record_descriptor_digest=p2_desc_digest)
    # SUCCEEDED
    if evidence is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "No evidence.", None,
                               source_record_descriptor_digest=p2_desc_digest)
    ...
    return _build_feasible(rec, evidence, eb, source_record_descriptor_digest=p2_desc_digest)
```

---

## 14. CandidateDispositionRecord (P0-12)

Full model with validator (complete — no "same as prior round"):

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
        for d, n in [(self.source_record_descriptor_digest, "source"),
                      (self.feasibility_digest, "feasibility")]:
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
            if self.diagnostic != FeasibilityDiagnosticKey.NONE: raise ValueError("FEASIBLE: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is None: raise ValueError("FEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None: raise ValueError("FEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("FEASIBLE: invalid must be None")
            if self.primary_engineering_value is None: raise ValueError("FEASIBLE: primary required")
            if self.secondary_engineering_value is None: raise ValueError("FEASIBLE: secondary required")
            d1 = Decimal(self.primary_engineering_value)
            if canonical_decimal_string(d1) != self.primary_engineering_value: raise ValueError("FEASIBLE: primary not canonical")
            d2 = Decimal(self.secondary_engineering_value)
            if canonical_decimal_string(d2) != self.secondary_engineering_value: raise ValueError("FEASIBLE: secondary not canonical")
            if self.source_evaluation_failure_digest is not None: raise ValueError("FEASIBLE: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("FEASIBLE: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("FEASIBLE: origin must be NONE")
        # PROVIDER_IDENTITY_MISMATCH
        elif self.disposition is PROVIDER_IDENTITY_MISMATCH:
            if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("PROVIDER_MISMATCH: source must be VERIFIED")
            if self.source_hash_verification_outcome != PASSED: raise ValueError("PROVIDER_MISMATCH: hash must be PASSED")
            if self.source_provenance_verification_outcome != PASSED: raise ValueError("PROVIDER_MISMATCH: provenance must be PASSED")
            if self.provider_identity_matches: raise ValueError("PROVIDER_MISMATCH: provider must NOT match")
            if self.diagnostic != FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH: raise ValueError("PROVIDER_MISMATCH: diagnostic mismatch")
            if self.candidate_evaluation_identity_digest is None: raise ValueError("PROVIDER_MISMATCH: identity required")
            if self.verified_rating_evidence_digest is None: raise ValueError("PROVIDER_MISMATCH: evidence required")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("PROVIDER_MISMATCH: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("PROVIDER_MISMATCH: engineering must be None")
            if self.source_evaluation_failure_digest is not None: raise ValueError("PROVIDER_MISMATCH: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("PROVIDER_MISMATCH: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("PROVIDER_MISMATCH: origin must be NONE")
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
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("INFEASIBLE: origin must be NONE")
            if self.rating_status == "succeeded":
                if self.diagnostic not in (DUTY_SHORTFALL, TERMINAL_DELTA_T_INADEQUATE): raise ValueError("INFEASIBLE+SUCCEEDED: diagnostic mismatch")
            elif self.rating_status == "blocked":
                if self.diagnostic != RATING_BLOCKED: raise ValueError("INFEASIBLE+BLOCKED: diagnostic must be RATING_BLOCKED")
            elif self.rating_status == "failed":
                if self.diagnostic != RATING_FAILED: raise ValueError("INFEASIBLE+FAILED: diagnostic must be RATING_FAILED")
            else: raise ValueError(f"INFEASIBLE: unexpected rating_status {self.rating_status}")
        # INTEGRITY_FAILED
        elif self.disposition is INTEGRITY_FAILED:
            ...
        # PROVENANCE_FAILED
        elif self.disposition is PROVENANCE_FAILED:
            ...
        # UNEVALUATED
        elif self.disposition is UNEVALUATED:
            ...
        # RUNTIME_FAILED (with stage-specific evidence matrix)
        elif self.disposition is RUNTIME_FAILED:
            if self.primary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.failure_origin == PHASE2_EVALUATION:
                ...
            elif self.failure_origin == PHASE3_CLASSIFICATION:
                if self.phase3_failure_digest is None: raise ValueError("RF(P3): phase3 failure required")
                if self.source_evaluation_failure_digest is not None: raise ValueError("RF(P3): source failure must be None")
                if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("RF(P3): source must be VERIFIED")
                if self.source_hash_verification_outcome != PASSED: raise ValueError("RF(P3): hash must be PASSED")
                if self.source_provenance_verification_outcome != PASSED: raise ValueError("RF(P3): provenance must be PASSED")
                if self.diagnostic != PHASE3_RUNTIME_FAILED: raise ValueError("RF(P3): diagnostic must be PHASE3_RUNTIME_FAILED")
                # Stage-specific evidence (P0-9)
                stage = self.failure_stage
                if stage in (SOURCE_BINDING, CLASSIFICATION_INPUT):
                    if self.verified_rating_evidence_digest is None: raise ValueError("RF(P3): evidence required for stage")
                else:
                    if self.verified_rating_evidence_digest is not None: raise ValueError("RF(P3): evidence absent for stage")
                if stage in (CLASSIFICATION_INPUT,):
                    if len(self.warning_descriptors) == 0: raise ValueError("RF(P3): warnings expected for CLASSIFICATION_INPUT")
                if self.candidate_evaluation_identity_digest is None: raise ValueError("RF(P3): identity required (retained)")
                if self.invalid_rating_evidence_digest is not None: raise ValueError("RF(P3): invalid must be None")
            else: raise ValueError(f"RUNTIME_FAILED: unexpected origin {self.failure_origin}")
        else: raise ValueError(f"unknown disposition: {self.disposition}")
        return self

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))
    def verify_or_raise(self) -> None:
        if not self.verify_digest(): raise ValueError("feasibility_digest mismatch")
```

---

## 15. OptimizationResult (P0-9, P0-11)

Updated with `ordered_identity_snapshot_digests` and nullable source binding digests:

```python
class OptimizationResult(BaseModel):
    ...
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...]
    ordered_phase3_source_binding_digests: tuple[str | None, ...]
    ordered_phase3_preparation_result_digests: tuple[str, ...]
    ...

def result_core_payload(r: OptimizationResult) -> dict[str, object]:
    return {
        ...,
        "ordered_identity_snapshot_digests": list(r.ordered_identity_snapshot_digests),
        "ordered_phase2_source_snapshot_digests": list(r.ordered_phase2_source_snapshot_digests),
        "ordered_phase3_source_binding_digests": list(r.ordered_phase3_source_binding_digests),
        "ordered_phase3_preparation_result_digests": list(r.ordered_phase3_preparation_result_digests),
        ...
    }
```

---

## 16. External verifier (P0-8, P0-9)

```python
def verify_optimization_result_or_raise(
    result, *, ei,
    source_identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...],
    source_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    preparation_results: tuple[Phase3CandidatePreparationResult, ...],
    warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    dispositions, ranked, graph,
):
    N, F = result.total_candidate_count, result.feasible_candidate_count
    ...
    for i, rec in enumerate(ei.evaluation_records):
        id_snap = source_identity_snapshots[i]
        ss = source_snapshots[i]   # None if READY failed; always non-None if READY
        sb = source_bindings[i]    # None if prep failed before binding
        pr = preparation_results[i]
        dr = dispositions[i]
        # Identity snapshot always exists
        if id_snap.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(...)
        if id_snap.evaluation_order_index != i: raise ValueError(...)
        if result.ordered_identity_snapshot_digests[i] != id_snap.identity_snapshot_digest: raise ValueError(...)
        # Snapshot (may be None for FAILED prep)
        if ss is not None:
            verify_phase2_source_record_snapshot_or_raise(ss, source_record=rec, ...)
            if result.ordered_phase2_source_snapshot_digests[i] != ss.snapshot_digest: raise ValueError(...)
        else:
            if result.ordered_phase2_source_snapshot_digests[i] is not None: raise ValueError(...)
        # Binding (may be None for FAILED prep before binding)
        if sb is not None:
            sb.verify_or_raise()
            if result.ordered_phase3_source_binding_digests[i] != sb.binding_digest: raise ValueError(...)
        else:
            ...
        # Preparation result
        if pr.phase2_identity_snapshot_digest != id_snap.identity_snapshot_digest: raise ValueError(...)
        if result.ordered_phase3_preparation_result_digests[i] != pr.preparation_result_digest: raise ValueError(...)
        # Verify authoritative descriptor bindings (P0-9)
        wb = warning_binding_tuples[i]
        bb = blocker_binding_tuples[i]
        for j, d in enumerate(dr.warning_descriptors):
            verify_phase3_message_descriptor_or_raise(d)
            if j < len(wb):
                if d.owner_sort_key != wb[j].owner_sort_key: raise ValueError(f"[{i}] warning[{j}] sort_key mismatch")
                if d.original_code != wb[j].original_code: raise ValueError(f"[{i}] warning[{j}] code mismatch")
                if d.message_payload_digest != wb[j].message_payload_digest: raise ValueError(f"[{i}] warning[{j}] digest mismatch")
        ...
```

---

## 17. Provenance (P0-18)

### 17.1 DAG topology

```python
# Node order:
# 0. root (EXTERNAL)
# 1. sizing_request (INPUT_FILE)
# 2. passed_gate (CALCULATION_RUN)
# 3. candidate_set (CALCULATION_RUN)
# 4. source_snapshot_set (INTERMEDIATE) — aggregate identity snapshots
# 5. evaluation_input (INTERMEDIATE)
# 6. source_binding_set (INTERMEDIATE)
# 7. preparation_result_set (INTERMEDIATE)
# 8..8+N-1: disposition[i] (INTERMEDIATE)
# 8+N..8+N+F-1: ranked[i] (INTERMEDIATE)
# 8+N+F: top_n_selection (INTERMEDIATE)
# 9+N+F: result_core (RESULT)
# 10+N+F: optimizer (OPTIMIZER)
#
# Edge DAG (P0-18 — no cycles):
# root ──regulates──► sizing_request
# sizing_request ──consumed_by──► passed_gate
# passed_gate ──produced──► candidate_set
# candidate_set ──consumed_by──► source_snapshot_set
# source_snapshot_set ──produced──► evaluation_input
# evaluation_input ──consumed_by──► source_binding_set
# source_binding_set ──produced──► preparation_result_set
# preparation_result_set ──evaluated──► each disposition[i]
# disposition[feasible_i] ──ranked──► ranked[i]
# evaluation_input ──selected_by──► top_n_selection
# ranked[0..TN-1] ──selected──► top_n_selection
# top_n_selection ──produced──► result_core
# result_core ──executed_by──► optimizer
```

### 17.2 Expected node builders

```python
def expected_phase3_provenance_nodes(*, ei, dispositions, ranked, result):
    nodes = []
    root_p = sha256_digest({"artifact_kind": "phase3_evaluation_input", "evaluation_input_digest": ei.evaluation_input_digest})
    nodes.append(ExpectedPhase3ProvenanceNode("root", EXTERNAL, root_p))
    nodes.append(ExpectedPhase3ProvenanceNode("sizing_request", INPUT_FILE, ei.sizing_request_identity_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("passed_gate", CALCULATION_RUN, ei.gate_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("candidate_set", CALCULATION_RUN, ei.candidate_set_digest))
    ss_p = sha256_digest({"ordered_identity_snapshot_digests": list(result.ordered_identity_snapshot_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("source_snapshot_set", INTERMEDIATE, ss_p))
    nodes.append(ExpectedPhase3ProvenanceNode("evaluation_input", INTERMEDIATE, ei.evaluation_input_digest))
    sb_p = sha256_digest({"ordered_binding_digests": [d for d in result.ordered_phase3_source_binding_digests if d is not None]})
    nodes.append(ExpectedPhase3ProvenanceNode("source_binding_set", INTERMEDIATE, sb_p))
    pr_p = sha256_digest({"ordered_prep_result_digests": list(result.ordered_phase3_preparation_result_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("preparation_result_set", INTERMEDIATE, pr_p))
    for i, d in enumerate(dispositions):
        nodes.append(ExpectedPhase3ProvenanceNode(f"disposition[{i}]", INTERMEDIATE, d.feasibility_digest))
    for i, r in enumerate(ranked):
        nodes.append(ExpectedPhase3ProvenanceNode(f"ranked[{i}]", INTERMEDIATE, r.ranked_record_digest))
    tn_p = sha256_digest({"ordered_top_n_record_digests": list(result.ordered_top_n_record_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("top_n_selection", INTERMEDIATE, tn_p))
    nodes.append(ExpectedPhase3ProvenanceNode("result_core", RESULT, result.result_core_hash))
    opt_p = sha256_digest({"evaluation_input_digest": ei.evaluation_input_digest, ...})
    nodes.append(ExpectedPhase3ProvenanceNode("optimizer", OPTIMIZER, opt_p))
    return tuple(nodes)
```

Node count: 11 + N + F. All edges are DAG (verified by explicit cycle check in addition to reachability).

---

## 18. Single-pass descriptor helpers

(Unchanged: builds descriptors once, never re-reads context.)

---

## 19. Implementation boundary

New files: `phase3_input.py`, `feasibility.py`, `ranking.py`, `result.py`. Existing modified: `messages.py`, `evaluation.py` (export `verified_rating_evidence_payload_from_descriptors`).

---

## 20. Test matrix

snapshot one-shot construction succeeds; snapshot empty-digest construction impossible; source-binding one-shot construction succeeds; source-binding payload helper never instantiates final model; RunFailure descriptor builder valid Python; authoritative Phase 2 evidence helper exact parity; warning message payload digest vs binding digest distinction; thermal/provider/correlation tamper changes evidence digest; source evaluation failure context traversed once; snapshot preparation failure before EvaluationInput; minimal identity snapshot on canonicalization failure; optional source binding verifier branch; FAILED before binding verification; FAILED after binding verification; authoritative warning binding tuple verification; authoritative blocker binding tuple verification; descriptor owner_sort_key tamper rejected; descriptor original_code tamper rejected; full source_record thermal evidence tamper rejected; preparation READY nested cin digest changes prep digest; preparation FAILED failure digest changes prep digest; full CandidateDispositionRecord validator present; all builders receive valid source descriptor digest; source warnings retained in dispositions; source blockers retained in dispositions; no builder re-reads original RunFailure; P2-RF-1 arbitrary printable suffix rejected; no `object.__setattr__`; no empty final-model digest construction; provenance graph acyclic (verified by cycle detection); snapshot→EvaluationInput causal direction; FAILED None-binding provenance path; zero-F provenance graph.

---

## 21. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
