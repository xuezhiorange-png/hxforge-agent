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

Deserialized from the Phase 2 cached descriptor's `owner_sort_key` tuple directly. No re-reading of `message.context`, `engineering_message_payload(message)`, or `safe_context_owner_marker(message.context)`.

### 3.2 Phase3MessageDescriptorBinding (P0-6, P1-1)

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
        if not self.original_code:
            raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest):
            raise ValueError("invalid message_payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest):
            raise ValueError("invalid descriptor_binding_digest")
        expected = sha256_digest({
            "owner_sort_key": list(self.owner_sort_key),
            "original_code": self.original_code,
            "message_payload_digest": self.message_payload_digest,
        })
        if self.descriptor_binding_digest != expected:
            raise ValueError("descriptor_binding_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        expected = sha256_digest({
            "owner_sort_key": list(self.owner_sort_key),
            "original_code": self.original_code,
            "message_payload_digest": self.message_payload_digest,
        })
        if self.descriptor_binding_digest != expected:
            raise ValueError("descriptor_binding_digest mismatch")

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

### 3.3 Phase3RunFailureDescriptorBinding (P0-5)

```python
class Phase3RunFailureDescriptorBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    payload_digest: str
    descriptor_binding_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.DIGEST_PATTERN.match(self.payload_digest):
            raise ValueError("invalid payload_digest")
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest):
            raise ValueError("invalid descriptor_binding_digest")
        expected = sha256_digest({"payload_digest": self.payload_digest})
        if self.descriptor_binding_digest != expected:
            raise ValueError("descriptor_binding_digest mismatch")
        return self

builder = build_phase3_run_failure_descriptor_binding(failure: RunFailure) -> Phase3RunFailureDescriptorBinding:
    payload_digest = sha256_digest(run_failure_payload(failure))
    return Phase3RunFailureDescriptorBinding(
        payload_digest=payload_digest,
        descriptor_binding_digest=sha256_digest({"payload_digest": payload_digest}),
    )
```

### 3.4 Descriptor verification helper

```python
def verify_phase3_message_descriptor_or_raise(
    descriptor: Phase3MessageDescriptor,
) -> None:
    if not descriptor.original_code:
        raise ValueError("descriptor original_code must be non-empty")
    if not descriptor.DIGEST_PATTERN.match(descriptor.message_payload_digest):
        raise ValueError("descriptor message_payload_digest invalid")
    if len(descriptor.owner_sort_key) != 6:
        raise ValueError("descriptor owner_sort_key length != 6")
    if descriptor.owner_sort_key[1] != descriptor.original_code:
        raise ValueError("descriptor owner_sort_key[1] != original_code")
```

---

## 4. Phase2SourceRecordSnapshot (P0-2, P0-3)

Constructed **before** `Phase3EvaluationInput`. Contains all Phase 2 source record data plus once-cached descriptor digests. Does not reference any Phase 3 artifact. The preparation function `prepare_phase2_source_record_snapshot` is responsible for computing warning/blocker descriptors, evidence digest, and failure digests exactly once.

```python
class Phase2SourceRecordSnapshotPreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    snapshot: Phase2SourceRecordSnapshot | None = None
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    failure_binding: Phase3RunFailureDescriptorBinding | None = None
    phase3_failure: RunFailure | None = None
    phase3_failure_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.status is Phase3PreparationStatus.READY:
            if self.snapshot is None: raise ValueError("READY requires snapshot")
            if self.phase3_failure is not None: raise ValueError("READY: no failure")
        else:
            if self.snapshot is not None: raise ValueError("FAILED: no snapshot")
            if self.phase3_failure is None: raise ValueError("FAILED requires failure")
            if self.phase3_failure_digest is None: raise ValueError("FAILED requires failure_digest")
            if self.failure_stage is None: raise ValueError("FAILED requires failure_stage")
        return self

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
    source_evaluation_failure_binding_digest: str | None
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
                      (self.source_evaluation_failure_binding_digest, "failure_binding")]:
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
        "source_evaluation_failure_binding_digest": s.source_evaluation_failure_binding_digest,
    }
```

### 4.1 Snapshot preparation (P0-2, P0-5)

Exactly-once context: each EngineeringMessage, each RunFailure source, and verification evidence are read **exactly once** to build cached descriptors.

```python
def prepare_phase2_source_record_snapshot(
    source_record: CandidateEvaluationRecord,
) -> Phase2SourceRecordSnapshotPreparationResult:
    candidate_id = source_record.source_qualified_candidate_id
    index = source_record.evaluation_order_index
    evidence = source_record.verified_rating_evidence

    # Warning descriptors (P0-2)
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...] = ()
    failure_binding: Phase3RunFailureDescriptorBinding | None = None

    if evidence is not None:
        w_result = canonicalize_phase3_messages_or_failure(
            evidence.warnings, "warning", candidate_id, index, "",
        )
        if isinstance(w_result, RunFailure):
            return _snapshot_preparation_failure(w_result, Phase3PreparationFailureStage.WARNING_DESCRIPTOR)
        b_result = canonicalize_phase3_messages_or_failure(
            evidence.blockers, "blocker", candidate_id, index, "",
        )
        if isinstance(b_result, RunFailure):
            return _snapshot_preparation_failure(b_result, Phase3PreparationFailureStage.BLOCKER_DESCRIPTOR)
        warning_bindings = tuple(build_phase3_message_descriptor_binding(d) for d in w_result)
        blocker_bindings = tuple(build_phase3_message_descriptor_binding(d) for d in b_result)
        if evidence.failure is not None:
            failure_binding = build_phase3_run_failure_descriptor_binding(evidence.failure)

    # Evidence digest using authoritative 26-field Phase 2 algorithm (P0-1)
    evidence_digest = _compute_evidence_digest(
        evidence=evidence,
        warning_bindings=warning_bindings,
        blocker_bindings=blocker_bindings,
        failure_binding=failure_binding,
        source_record=source_record,
    )

    # Source evaluation failure binding
    source_failure_binding_digest = None
    evaluation_failure_digest = None
    if source_record.evaluation_failure is not None:
        fb = build_phase3_run_failure_descriptor_binding(source_record.evaluation_failure)
        source_failure_binding_digest = fb.descriptor_binding_digest
        evaluation_failure_digest = fb.payload_digest

    # Phase 2 source-record descriptor digest
    # Compute using snapshot data
    candidate_evaluation_identity_digest = (
        source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if source_record.candidate_evaluation_identity is not None else None
    )
    invalid_evidence_digest = (
        source_record.invalid_rating_evidence.invalid_evidence_digest
        if source_record.invalid_rating_evidence is not None else None
    )
    claimed_audit_digest = (
        source_record.claimed_rating_result_audit.audit_digest
        if source_record.claimed_rating_result_audit is not None else None
    )

    phase2_source_record_descriptor_payload = {
        "source_qualified_candidate_id": candidate_id,
        "evaluation_order_index": index,
        "candidate_evaluation_state": source_record.candidate_evaluation_state.value,
        "feasible": source_record.feasible,
        "feasibility_status": source_record.feasibility_status.value,
        "hash_verification_outcome": source_record.hash_verification_outcome.value,
        "provenance_verification_outcome": source_record.provenance_verification_outcome.value,
        "provider_identity_matches": source_record.provider_identity_matches,
        "rating_status": source_record.rating_status,
        "candidate_evaluation_identity_digest": candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": evidence_digest,
        "invalid_rating_evidence_digest": invalid_evidence_digest,
        "claimed_rating_result_audit_digest": claimed_audit_digest,
        "evaluation_failure_digest": evaluation_failure_digest,
    }
    phase2_descriptor_digest = sha256_digest(phase2_source_record_descriptor_payload)

    snapshot = Phase2SourceRecordSnapshot(
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
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=evidence_digest,
        invalid_rating_evidence_digest=invalid_evidence_digest,
        claimed_rating_result_audit_digest=claimed_audit_digest,
        evaluation_failure_digest=evaluation_failure_digest,
        phase2_source_record_descriptor_digest=phase2_descriptor_digest,
        warning_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in warning_bindings),
        blocker_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in blocker_bindings),
        source_evaluation_failure_binding_digest=source_failure_binding_digest,
        snapshot_digest="",  # computed below
    )
    # Compute snapshot digest
    sd = sha256_digest(_snapshot_payload(snapshot))
    # Use object.__setattr__ only for snapshot_digest — the one field that cannot include itself
    object.__setattr__(snapshot, "snapshot_digest", sd)

    return Phase2SourceRecordSnapshotPreparationResult(
        status=Phase3PreparationStatus.READY,
        snapshot=snapshot,
        warning_bindings=warning_bindings,
        blocker_bindings=blocker_bindings,
        failure_binding=failure_binding,
    )

def _compute_evidence_digest(
    evidence: VerifiedRatingEvidenceSnapshot | None,
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    failure_binding: Phase3RunFailureDescriptorBinding | None,
    source_record: CandidateEvaluationRecord,
) -> str | None:
    """26-field evidence digest using the authoritative Phase 2 algorithm."""
    if evidence is None:
        return None
    payload = {
        "rating_status": evidence.rating_status,
        "heat_duty_w": evidence.heat_duty_w,
        "hot_outlet_temperature_k": evidence.hot_outlet_temperature_k,
        "cold_outlet_temperature_k": evidence.cold_outlet_temperature_k,
        "area_inner_m2": evidence.area_inner_m2,
        "area_outer_m2": evidence.area_outer_m2,
        "UA_w_k": evidence.UA_w_k,
        "LMTD_k": evidence.LMTD_k,
        "energy_residual_w": evidence.energy_residual_w,
        "ua_lmtd_residual_w": evidence.ua_lmtd_residual_w,
        "tube_side_density_kg_m3": evidence.tube_side_density_kg_m3,
        "annulus_side_density_kg_m3": evidence.annulus_side_density_kg_m3,
        "tube_side_flow_area_m2": evidence.tube_side_flow_area_m2,
        "annulus_side_flow_area_m2": evidence.annulus_side_flow_area_m2,
        "warning_digests": [b.descriptor_binding_digest for b in warning_bindings],
        "blocker_digests": [b.descriptor_binding_digest for b in blocker_bindings],
        "failure_digest": failure_binding.payload_digest if failure_binding is not None else None,
        "provider_identity_digest": evidence.provider_identity_digest,
        "tube_correlation_digest": evidence.tube_correlation_digest,
        "annulus_correlation_digest": evidence.annulus_correlation_digest,
        "rating_result_hash": evidence.rating_result_hash,
        "rating_provenance_digest": evidence.rating_provenance_digest,
        "hash_verification_outcome": source_record.hash_verification_outcome.value,
        "provenance_verification_outcome": source_record.provenance_verification_outcome.value,
        "rating_request_identity_digest": evidence.rating_request_identity_digest,
        "rating_execution_context_digest": evidence.rating_execution_context_digest,
    }
    return sha256_digest(payload)

def _snapshot_preparation_failure(
    failure: RunFailure,
    stage: Phase3PreparationFailureStage,
) -> Phase2SourceRecordSnapshotPreparationResult:
    failure_digest = sha256_digest(run_failure_payload(failure))
    return Phase2SourceRecordSnapshotPreparationResult(
        status=Phase3PreparationStatus.FAILED,
        phase3_failure=failure,
        phase3_failure_digest=failure_digest,
        failure_stage=stage,
    )
```

### 4.2 Snapshot verifier (P0-3)

```python
def verify_phase2_source_record_snapshot_or_raise(
    snapshot: Phase2SourceRecordSnapshot,
    *,
    source_record: CandidateEvaluationRecord,
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    failure_binding: Phase3RunFailureDescriptorBinding | None,
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
    # Digest fields
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
    expected_eval_failure_digest = (
        sha256_digest(run_failure_payload(source_record.evaluation_failure))
        if source_record.evaluation_failure is not None else None
    )
    if snapshot.evaluation_failure_digest != expected_eval_failure_digest:
        raise ValueError("snapshot evaluation failure digest mismatch")
    # Warning/blocker/failure bindings
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
    # Phase 2 source-record descriptor digest
    evidence = source_record.verified_rating_evidence
    expected_evidence_digest = _compute_evidence_digest(
        evidence=evidence,
        warning_bindings=warning_bindings,
        blocker_bindings=blocker_bindings,
        failure_binding=failure_binding,
        source_record=source_record,
    )
    if snapshot.verified_rating_evidence_digest != expected_evidence_digest:
        raise ValueError("snapshot evidence digest mismatch")
    expected_descriptor_digest = sha256_digest({
        "source_qualified_candidate_id": snapshot.source_qualified_candidate_id,
        "evaluation_order_index": snapshot.evaluation_order_index,
        "candidate_evaluation_state": snapshot.candidate_evaluation_state.value,
        "feasible": snapshot.feasible,
        "feasibility_status": snapshot.feasibility_status.value,
        "hash_verification_outcome": snapshot.hash_verification_outcome.value,
        "provenance_verification_outcome": snapshot.provenance_verification_outcome.value,
        "provider_identity_matches": snapshot.provider_identity_matches,
        "rating_status": snapshot.rating_status,
        "candidate_evaluation_identity_digest": snapshot.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": snapshot.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": snapshot.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": snapshot.claimed_rating_result_audit_digest,
        "evaluation_failure_digest": snapshot.evaluation_failure_digest,
    })
    if snapshot.phase2_source_record_descriptor_digest != expected_descriptor_digest:
        raise ValueError("snapshot phase2 descriptor digest mismatch")
    # Own digest
    snapshot.verify_or_raise()
```

---

## 5. Phase3EvaluationInput

### 5.1 Model

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
    evaluation_input_digest: str
```

Uses `ordered_phase2_source_record_descriptor_digests` (referencing `Phase2SourceRecordSnapshot`) — no Phase 3 binding digest in this artifact.

### 5.2 Helpers (P0-4)

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
    }
```

No call to `compute_explicit_evidence_digest()`. The snapshot holds the once-computed digest.

### 5.3 13-step verify_or_raise()

Step 1: types. Step 2: `materialization_result.verify_or_raise()`. Step 3: sizing digest. Step 4: `candidate_set.verify_digest()`. Step 5: `sizing_gate.verify_digest()`. Step 6: candidate-set↔sizing. Step 7: gate↔candidate-set. Step 8: count parity. Step 9: one-to-one record↔candidate. Step 10: exhaustive state per §6 matrix. Step 11: strict-stop invariant. Step 12: Phase 2 source descriptor digest. Step 13: evaluation_input_digest.

---

## 6. Phase 2 constructor matrix

### 6.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity (VERIFIED only): `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 6.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 6.3 RUNTIME_FAILED — executable path specs (10 paths, P0-14, P0-15)

```python
@dataclass(frozen=True, slots=True)
class ContextValueRule:
    key: str
    value_kind: str  # "literal", "digest_format", "presence", "any"
    expected_literal: object | None = None

@dataclass(frozen=True, slots=True)
class Phase2RuntimeFailurePathSpec:
    path_id: str
    hash_outcome: VerificationOutcome
    provenance_outcome: VerificationOutcome
    audit_required: bool
    failure_code: ErrorCode
    message_rule: tuple[str, ...]  # ("exact", msg) or ("dynamic_type", template)
    context_keys: tuple[str, ...]
    failure_stage: str | None
    owner_kind: str | None
    value_rules: tuple[ContextValueRule, ...]

def safe_runtime_type_name(value: object) -> str:
    return type(value).__name__  # P0-15: __name__ not __qualname__

PATH_SPECS = (
    Phase2RuntimeFailurePathSpec("P2-RF-1", NOT_RUN, NOT_RUN, True, ErrorCode.INVALID_STATE_TRANSITION,
        ("dynamic_type", "Expected exact RatingResult, got "),
        (), "evaluation", "evaluation",
        ()),
    Phase2RuntimeFailurePathSpec("P2-RF-2", ERROR, NOT_RUN, True, ErrorCode.HASH_MISMATCH,
        ("exact", "Rating result hash verification raised."),
        (), "verification", "verification_runtime",
        ()),
    Phase2RuntimeFailurePathSpec("P2-RF-3", PASSED, ERROR, True, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Rating result provenance verification raised."),
        (), "verification", "verification_runtime",
        ()),
    Phase2RuntimeFailurePathSpec("P2-RF-4", PASSED, PASSED, True, ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to extract trusted evidence"),
        (), "verification", "verification_runtime",
        ()),
    Phase2RuntimeFailurePathSpec("P2-RF-5", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"),
         ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"),
         ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-6", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "warning",
        (ContextValueRule("failure_stage","literal","rating_verification"),
         ContextValueRule("owner_kind","literal","warning"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"),
         ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-7", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "blocker",
        (ContextValueRule("failure_stage","literal","rating_verification"),
         ContextValueRule("owner_kind","literal","blocker"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"),
         ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-8", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "run_failure",
        (ContextValueRule("failure_stage","literal","rating_verification"),
         ContextValueRule("owner_kind","literal","run_failure"),
         ContextValueRule("context_key","any"), ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"),
         ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-9", PASSED, PASSED, False, ErrorCode.INVALID_STATE_TRANSITION,
        ("exact", "Failed to build candidate evaluation identity"),
        (), "verification", "verification_runtime",
        ()),
    Phase2RuntimeFailurePathSpec("P2-RF-10", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact", "Trusted rating verification failed."),
        ("failure_stage","owner_kind","owner_id","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"),
         ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("offending_type","any"), ContextValueRule("failure_kind","any"),
         ContextValueRule("safe_marker_digest","digest_format"))),
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
        # Message rule
        kind, template = spec.message_rule
        if kind == "exact":
            if record.evaluation_failure.message != template: continue
        elif kind == "dynamic_type":
            if not record.evaluation_failure.message.startswith(template): continue
            rest = record.evaluation_failure.message[len(template):]
            if not rest or not rest.isprintable(): continue
        # Context key order
        if spec.context_keys:
            ctx_pairs = record.evaluation_failure.context
            ctx_keys = tuple(p[0] for p in ctx_pairs)
            if ctx_keys != spec.context_keys: continue
        # Value rules (P0-14)
        value_ok = True
        ctx_map = dict(ctx_pairs)
        for vr in spec.value_rules:
            val = ctx_map.get(vr.key, "")
            if vr.value_kind == "literal":
                if val != vr.expected_literal:
                    value_ok = False
            elif vr.value_kind == "digest_format":
                if not re.match(r"^sha256:[0-9a-f]{64}$", str(val)) and str(val) != "":
                    value_ok = False
            elif vr.value_kind == "presence":
                if not val:
                    value_ok = False
        if not value_ok: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

`safe_runtime_type_name` uses `type(value).__name__` to match the exact production message format. P2-RF-5 through P2-RF-8 have distinct `owner_kind` literals (`verification_runtime`, `warning`, `blocker`, `run_failure`). All context literals are verified with exact expected values.

### 6.4 UNEVALUATED

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 7. Strict-stop

```python
def _find_stop_index(ei: Phase3EvaluationInput) -> int | None:
    for i, r in enumerate(ei.evaluation_records):
        if r.candidate_evaluation_state in (CandidateEvaluationState.INTEGRITY_INVALID, CandidateEvaluationState.RUNTIME_FAILED):
            return i
    return None
```

---

## 8. Decimal and duty

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

Duty: `required = to_canonical_decimal(sizing.required_duty_w)`; `abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)`; `rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)`; `duty_tol = max(abs_tol, rel_tol * abs(required))`; `duty_satisfied = abs(heat - required) <= duty_tol`.

Terminal delta-T: for `PARALLEL`: `dt1 = hot_in - cold_in; dt2 = hot_out - cold_out`. For `COUNTERFLOW`: `dt1 = hot_in - cold_out; dt2 = hot_out - cold_in`. `satisfied = min(dt1_decimal, dt2_decimal) >= to_canonical_decimal(minimum_terminal_delta_t)`.

---

## 9. Count equations

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

## 10. Phase3SourceRecordBinding (P0-7)

Constructed **after** `Phase2SourceRecordSnapshot` and `Phase3EvaluationInput`. Uses the snapshot's descriptor digests.

```python
class Phase3SourceRecordBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    phase2_source_record_descriptor_digest: str
    verified_rating_evidence_digest: str | None
    phase2_source_snapshot_digest: str
    warning_descriptor_binding_digests: tuple[str, ...]
    blocker_descriptor_binding_digests: tuple[str, ...]
    source_evaluation_failure_binding_digest: str | None
    binding_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.phase2_source_record_descriptor_digest):
            raise ValueError("invalid source descriptor digest")
        if not self.DIGEST_PATTERN.match(self.phase2_source_snapshot_digest):
            raise ValueError("invalid snapshot digest")
        if self.verified_rating_evidence_digest is not None and not self.DIGEST_PATTERN.match(self.verified_rating_evidence_digest):
            raise ValueError("invalid evidence digest")
        if self.source_evaluation_failure_binding_digest is not None and not self.DIGEST_PATTERN.match(self.source_evaluation_failure_binding_digest):
            raise ValueError("invalid failure binding digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(_ph3_binding_payload(self))
        if self.binding_digest != expected: raise ValueError("binding_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        if self.binding_digest != sha256_digest(_ph3_binding_payload(self)):
            raise ValueError("binding_digest mismatch")

def _ph3_binding_payload(b: Phase3SourceRecordBinding) -> dict[str, object]:
    return {
        "schema_version": b.schema_version,
        "source_qualified_candidate_id": b.source_qualified_candidate_id,
        "evaluation_order_index": b.evaluation_order_index,
        "phase2_source_record_descriptor_digest": b.phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": b.verified_rating_evidence_digest,
        "phase2_source_snapshot_digest": b.phase2_source_snapshot_digest,
        "warning_descriptor_binding_digests": list(b.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(b.blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": b.source_evaluation_failure_binding_digest,
    }
```

### 10.1 One-shot factory

```python
def build_phase3_source_record_binding(
    *,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    phase2_source_record_descriptor_digest: str,
    verified_rating_evidence_digest: str | None,
    phase2_source_snapshot_digest: str,
    warning_descriptor_binding_digests: tuple[str, ...],
    blocker_descriptor_binding_digests: tuple[str, ...],
    source_evaluation_failure_binding_digest: str | None,
) -> Phase3SourceRecordBinding:
    payload = _ph3_binding_payload_from_values(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        phase2_source_snapshot_digest=phase2_source_snapshot_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
    )
    binding_digest = sha256_digest(payload)
    return Phase3SourceRecordBinding(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        phase2_source_record_descriptor_digest=phase2_source_record_descriptor_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        phase2_source_snapshot_digest=phase2_source_snapshot_digest,
        warning_descriptor_binding_digests=warning_descriptor_binding_digests,
        blocker_descriptor_binding_digests=blocker_descriptor_binding_digests,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        binding_digest=binding_digest,
    )

def _ph3_binding_payload_from_values(**kwargs) -> dict[str, object]:
    return _ph3_binding_payload(Phase3SourceRecordBinding(**kwargs, binding_digest=""))
```

---

## 11. Phase3CandidateClassificationInput (P0-4, P0-13)

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
    phase2_source_snapshot_digest: str
    phase3_source_binding_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        # Local format checks only — complete binding is in verify_or_raise
        return self
```

### 11.1 Standalone verifier (P0-4, P0-13)

Uses snapshot for source descriptor (not binding). Verifies full source_record binding.

```python
def verify_phase3_classification_input_or_raise(
    value: Phase3CandidateClassificationInput,
    *,
    source_record: CandidateEvaluationRecord,
    source_snapshot: Phase2SourceRecordSnapshot,
    source_binding: Phase3SourceRecordBinding,
    candidate: ManufacturableCandidate,
    sizing_identity: SizingRequestIdentity,
) -> None:
    if value.schema_version != 1:
        raise ValueError("classification_input schema_version must be 1")
    # Source record full binding (P0-13)
    if value.source_record is not source_record:
        # When serialization breaks identity, verify full typed equality
        if value.source_record.source_qualified_candidate_id != source_record.source_qualified_candidate_id:
            raise ValueError("cin source_record candidate_id mismatch")
        if value.source_record.evaluation_order_index != source_record.evaluation_order_index:
            raise ValueError("cin source_record index mismatch")
        if value.source_record.candidate_evaluation_state != source_record.candidate_evaluation_state:
            raise ValueError("cin source_record state mismatch")
        if value.source_record.hash_verification_outcome != source_record.hash_verification_outcome:
            raise ValueError("cin source_record hash outcome mismatch")
        if value.source_record.provenance_verification_outcome != source_record.provenance_verification_outcome:
            raise ValueError("cin source_record provenance outcome mismatch")
        if value.source_record.provider_identity_matches != source_record.provider_identity_matches:
            raise ValueError("cin source_record provider flag mismatch")
        if value.source_record.rating_status != source_record.rating_status:
            raise ValueError("cin source_record rating_status mismatch")
    # Snapshot binding (P0-4: uses snapshot, not binding)
    if value.phase2_source_snapshot_digest != source_snapshot.snapshot_digest:
        raise ValueError("cin snapshot_digest mismatch")
    if value.source_record_descriptor_digest != source_snapshot.phase2_source_record_descriptor_digest:
        raise ValueError("cin source_record_descriptor_digest != snapshot descriptor")
    if value.evidence_binding.binding_digest != source_binding.binding_digest:
        raise ValueError("cin binding_digest mismatch")
    if value.phase3_source_binding_digest != source_binding.binding_digest:
        raise ValueError("cin phase3_source_binding_digest mismatch")
    # Candidate binding
    if value.materialized_candidate.source_qualified_candidate_id != candidate.source_qualified_candidate_id:
        raise ValueError("cin candidate_id mismatch")
    if value.materialized_candidate.evaluation_order_index != candidate.evaluation_order_index:
        raise ValueError("cin candidate index mismatch")
    # Sizing identity
    if value.sizing_request_identity.sizing_request_identity_digest != sizing_identity.sizing_request_identity_digest:
        raise ValueError("cin sizing identity mismatch")
    if value.sizing_request_identity_digest != sizing_identity.sizing_request_identity_digest:
        raise ValueError("cin sizing digest mismatch")
```

---

## 12. Preparation lifecycle (P0-7, P0-8, P0-9, P0-12)

### 12.1 Phase3CandidatePreparationResult (P0-12)

```python
class Phase3CandidatePreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    source_qualified_candidate_id: str
    evaluation_order_index: int
    phase2_source_snapshot_digest: str
    phase3_source_binding_digest: str | None = None
    failure_stage: Phase3PreparationFailureStage | None = None
    classification_input: Phase3CandidateClassificationInput | None = None
    phase3_failure: RunFailure | None = None
    phase3_failure_digest: str | None = None
    preparation_result_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None: raise ValueError("READY: missing cin")
            if self.phase3_failure is not None: raise ValueError("READY: no failure")
            if self.phase3_failure_digest is not None: raise ValueError("READY: no failure digest")
            if self.failure_stage is not None: raise ValueError("READY: no failure_stage")
            if self.phase3_source_binding_digest is None: raise ValueError("READY: binding required")
        else:
            if self.classification_input is not None: raise ValueError("FAILED: no cin")
            if self.phase3_failure is None: raise ValueError("FAILED: failure required")
            if self.phase3_failure_digest is None: raise ValueError("FAILED: failure digest required")
            if self.failure_stage is None: raise ValueError("FAILED: failure_stage required")
            # Verify failure digest
            expected_digest = sha256_digest(run_failure_payload(self.phase3_failure))
            if self.phase3_failure_digest != expected_digest:
                raise ValueError("FAILED: phase3_failure_digest mismatch")
        # Verify own digest
        expected_pr = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected_pr:
            raise ValueError("preparation_result_digest mismatch")
        return self

def _prep_result_payload(r: Phase3CandidatePreparationResult) -> dict[str, object]:
    return {
        "schema_version": r.schema_version,
        "status": r.status.value,
        "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "evaluation_order_index": r.evaluation_order_index,
        "phase2_source_snapshot_digest": r.phase2_source_snapshot_digest,
        "phase3_source_binding_digest": r.phase3_source_binding_digest,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None,
    }
```

### 12.2 Preparation function (P0-7)

```python
def prepare_phase3_candidate(
    *,
    evaluation_input: Phase3EvaluationInput,
    index: int,
    source_snapshot: Phase2SourceRecordSnapshot,
    warning_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    blocker_bindings: tuple[Phase3MessageDescriptorBinding, ...],
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> Phase3CandidatePreparationResult:
    rec = evaluation_input.evaluation_records[index]
    candidate = evaluation_input.materialization_result.candidates[index]
    sizing = evaluation_input.sizing_request_identity
    p2_descriptor_digest = evaluation_input.ordered_phase2_source_record_descriptor_digests[index]

    # Build source binding from snapshot data
    binding = build_phase3_source_record_binding(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=index,
        phase2_source_record_descriptor_digest=p2_descriptor_digest,
        verified_rating_evidence_digest=source_snapshot.verified_rating_evidence_digest,
        phase2_source_snapshot_digest=source_snapshot.snapshot_digest,
        warning_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in warning_bindings),
        blocker_descriptor_binding_digests=tuple(b.descriptor_binding_digest for b in blocker_bindings),
        source_evaluation_failure_binding_digest=source_snapshot.source_evaluation_failure_binding_digest,
    )

    cin = Phase3CandidateClassificationInput(
        source_record=rec,
        source_record_descriptor_digest=p2_descriptor_digest,
        materialized_candidate=candidate,
        sizing_request_identity=sizing,
        sizing_request_identity_digest=evaluation_input.sizing_request_identity_digest,
        evidence_binding=binding,
        phase2_source_snapshot_digest=source_snapshot.snapshot_digest,
        phase3_source_binding_digest=binding.binding_digest,
    )

    prep_payload = {
        "schema_version": 1,
        "status": Phase3PreparationStatus.READY.value,
        "source_qualified_candidate_id": rec.source_qualified_candidate_id,
        "evaluation_order_index": index,
        "phase2_source_snapshot_digest": source_snapshot.snapshot_digest,
        "phase3_source_binding_digest": binding.binding_digest,
        "failure_stage": None,
    }
    pr_digest = sha256_digest(prep_payload)

    return Phase3CandidatePreparationResult(
        schema_version=1,
        status=Phase3PreparationStatus.READY,
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=index,
        phase2_source_snapshot_digest=source_snapshot.snapshot_digest,
        phase3_source_binding_digest=binding.binding_digest,
        classification_input=cin,
        preparation_result_digest=pr_digest,
    )
```

### 12.3 Preparation failure disposition builder (P0-8, P0-9, P0-10)

```python
def disposition_from_preparation_failure(
    *,
    source_record: CandidateEvaluationRecord,
    source_snapshot: Phase2SourceRecordSnapshot,
    candidate: ManufacturableCandidate,
    preparation_result: Phase3CandidatePreparationResult,
) -> CandidateDispositionRecord:
    failure = preparation_result.phase3_failure
    failure_digest = preparation_result.phase3_failure_digest
    stage = preparation_result.failure_stage

    # Field availability matrix (P0-9):
    # WARNING_DESCRIPTOR:         identity OK, evidence NO,  warnings partial, blockers NO
    # BLOCKER_DESCRIPTOR:         identity OK, evidence NO,  warnings YES,   blockers partial
    # FAILURE_DESCRIPTOR:         identity OK, evidence NO,  warnings YES,   blockers YES
    # EVIDENCE_DIGEST:            identity OK, evidence NO,  warnings YES,   blockers YES
    # SOURCE_BINDING:             identity OK, evidence YES, warnings YES,   blockers YES
    # CLASSIFICATION_INPUT:       identity OK, evidence YES, warnings YES,   blockers YES
    identity_digest = source_snapshot.candidate_evaluation_identity_digest

    # evidence digest: only available if failure stage is SOURCE_BINDING or later (P0-9)
    evidence_digest = (
        source_snapshot.verified_rating_evidence_digest
        if stage in (Phase3PreparationFailureStage.SOURCE_BINDING,
                     Phase3PreparationFailureStage.CLASSIFICATION_INPUT)
        else None
    )

    return build_candidate_disposition_record(
        source_qualified_candidate_id=source_record.source_qualified_candidate_id,
        evaluation_order_index=source_record.evaluation_order_index,
        source_candidate_evaluation_state=source_record.candidate_evaluation_state,
        source_hash_verification_outcome=source_record.hash_verification_outcome,
        source_provenance_verification_outcome=source_record.provenance_verification_outcome,
        source_record_descriptor_digest=source_snapshot.phase2_source_record_descriptor_digest,
        disposition=Phase3Disposition.RUNTIME_FAILED,
        diagnostic=FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED,
        provider_identity_matches=source_record.provider_identity_matches,
        rating_status=source_record.rating_status,
        candidate_evaluation_identity_digest=identity_digest,
        verified_rating_evidence_digest=evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=(),
        blocker_descriptors=(),
        source_evaluation_failure_digest=None,
        phase3_failure_digest=failure_digest,
        failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
        failure_stage=stage,
    )
```

---

## 13. One-shot disposition factory (P0-10)

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
    warning_digests = tuple(d.message_payload_digest for d in record.warning_descriptors)
    blocker_digests = tuple(d.message_payload_digest for d in record.blocker_descriptors)
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
        "warning_descriptor_digests": list(warning_digests),
        "blocker_descriptor_digests": list(blocker_digests),
        "source_evaluation_failure_digest": record.source_evaluation_failure_digest,
        "phase3_failure_digest": record.phase3_failure_digest,
        "failure_origin": record.failure_origin.value,
        "failure_stage": record.failure_stage.value if record.failure_stage is not None else None,
    }
```

No `**kwargs`, no `object.__setattr__`, no backfill. `failure_stage` is included in the payload and enters the `feasibility_digest`.

---

## 14. CandidateDispositionRecord

Full model definition includes `failure_stage: Phase3PreparationFailureStage | None = None` field. The validator enforces stage-specific evidence availability (P0-9). See full code in `build_candidate_disposition_record` and disposition validator (same as prior round with added `failure_stage` field and stage-aware RUNTIME_FAILED checks).

---

## 15. Classifier (P0-11)

```python
def validate_blocked_evidence(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot,
    eb: Phase3SourceRecordBinding,
) -> RunFailure | None:
    """Returns None = proceed, RunFailure = fail-closed to P3 RUNTIME_FAILED."""
    if rec.rating_status != "blocked":
        raise ValueError("not BLOCKED")
    if not eb.warning_descriptor_binding_digests and not eb.blocker_descriptor_binding_digests:
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="BLOCKED: evidence blockers must be non-empty",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "BLOCKED_EMPTY_BLOCKERS"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence is None:
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="BLOCKED: evidence is None",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "BLOCKED_MISSING_EVIDENCE"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence.area_outer_m2 is None or not (evidence.area_outer_m2 > 0):
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="BLOCKED: non-positive area_outer_m2",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "BLOCKED_BAD_AREA"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence.area_inner_m2 is None or not (evidence.area_inner_m2 > 0):
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="BLOCKED: non-positive area_inner_m2",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "BLOCKED_BAD_AREA"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    return None

def validate_failed_evidence(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot,
    eb: Phase3SourceRecordBinding,
) -> RunFailure | None:
    """Returns None = proceed, RunFailure = fail-closed to P3 RUNTIME_FAILED."""
    if rec.rating_status != "failed":
        raise ValueError("not FAILED")
    if evidence is None:
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="FAILED: evidence is None",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "FAILED_MISSING_EVIDENCE"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence.failure is None:
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="FAILED: failure must be present in evidence",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "FAILED_MISSING_FAILURE"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence.area_outer_m2 is None or not (evidence.area_outer_m2 > 0):
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="FAILED: non-positive area_outer_m2",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "FAILED_BAD_AREA"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    if evidence.area_inner_m2 is None or not (evidence.area_inner_m2 > 0):
        return RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="FAILED: non-positive area_inner_m2",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(("failure_stage", "evidence_validation"), ("diagnostic", "FAILED_BAD_AREA"),
                     ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                     ("evaluation_order_index", rec.evaluation_order_index)),
        )
    return None

def classify_candidate(input: Phase3CandidateClassificationInput) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence
    eb = input.evidence_binding
    # 1. Non-VERIFIED
    if rec.candidate_evaluation_state != VERIFIED:
        return _map_non_verified(rec)
    # 2. Provider mismatch
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, eb)
    # 3. rating_status None
    if rec.rating_status is None:
        return _phase3_runtime(rec, eb, ErrorCode.PHASE3_MISSING_RATING_STATUS, "No rating status.", None)
    # 4. BLOCKED/FAILED with fail-closed
    if rec.rating_status == "blocked":
        vf = validate_blocked_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf)
        return _build_infeasible(rec, eb, RATING_BLOCKED)
    if rec.rating_status == "failed":
        vf = validate_failed_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf)
        return _build_infeasible(rec, eb, RATING_FAILED)
    # 5. SUCCEEDED — evidence matrix
    if evidence is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "No evidence.", None)
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Missing thermal metrics.", None)
    if evidence.area_outer_m2 is None or not (evidence.area_outer_m2 > 0) or evidence.area_inner_m2 is None or not (evidence.area_inner_m2 > 0):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-positive area.", None)
    if evidence.failure is not None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Has failure.", None)
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-finite metric.", None)
    required = to_canonical_decimal(sizing.required_duty_w)
    duty_tol = max(to_canonical_decimal(sizing.duty_absolute_tolerance_w),
                   to_canonical_decimal(sizing.duty_relative_tolerance) * abs(required))
    if abs(heat_w - required) > duty_tol:
        return _build_infeasible(rec, eb, DUTY_SHORTFALL)
    fa = sizing.flow_arrangement
    if fa == "parallel":
        dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
    if min(dt1, dt2) < to_canonical_decimal(sizing.minimum_terminal_delta_t):
        return _build_infeasible(rec, eb, TERMINAL_DELTA_T_INADEQUATE)
    return _build_feasible(rec, evidence, eb)
```

---

## 16. RankedCandidateRecord

```python
class RankedCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    rank: int; source_qualified_candidate_id: str
    optimization_objective: OptimizationObjective
    primary_objective_value: str; primary_objective_field: str
    secondary_tie_break_value: str; secondary_tie_break_field: str
    candidate_evaluation_identity_digest: str
    verified_rating_evidence_digest: str; feasibility_digest: str
    ranked_record_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")
    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.rank < 1: raise ValueError("rank must be ≥ 1")
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        for v, n in [(self.primary_objective_value, "primary"), (self.secondary_tie_break_value, "secondary")]:
            d = Decimal(v)
            if not d.is_finite(): raise ValueError(f"{n}: not finite")
            if canonical_decimal_string(d) != v: raise ValueError(f"{n}: not canonical")
        if self.optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            if self.primary_objective_field != "area_outer_m2": raise ValueError("MIN_OA: primary must be area_outer_m2")
            if self.secondary_tie_break_field != "effective_length_m_canonical": raise ValueError("MIN_OA: secondary must be length")
        else:
            if self.primary_objective_field != "effective_length_m_canonical": raise ValueError("MIN_LEN: primary must be length")
            if self.secondary_tie_break_field != "area_outer_m2": raise ValueError("MIN_LEN: secondary must be area")
        for d, n in [(self.candidate_evaluation_identity_digest, "identity"),
                      (self.verified_rating_evidence_digest, "evidence"),
                      (self.feasibility_digest, "feasibility"),
                      (self.ranked_record_digest, "ranked")]:
            if not self.DIGEST_PATTERN.match(d): raise ValueError(f"invalid {n} digest")
        return self
    def verify_digest(self) -> bool:
        return self.ranked_record_digest == sha256_digest(ranked_payload(self))
    def verify_or_raise(self) -> None:
        if not self.verify_digest(): raise ValueError("ranked_record_digest mismatch")

def ranked_payload(r: RankedCandidateRecord) -> dict[str, object]:
    return {"rank": r.rank, "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "optimization_objective": r.optimization_objective.value,
        "primary_objective_value": r.primary_objective_value, "primary_objective_field": r.primary_objective_field,
        "secondary_tie_break_value": r.secondary_tie_break_value, "secondary_tie_break_field": r.secondary_tie_break_field,
        "candidate_evaluation_identity_digest": r.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": r.verified_rating_evidence_digest, "feasibility_digest": r.feasibility_digest}
```

Sort keys: `MIN_OA: (canonical_decimal(Decimal(area_m2)), canonical_decimal(Decimal(effective_length_m_canonical)), source_cid)`; `MIN_LEN: (canonical_decimal(Decimal(effective_length_m_canonical)), canonical_decimal(Decimal(area_m2)), source_cid)`.

---

## 17. OptimizationResult (P0-17)

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    optimization_result_id: str; sizing_request_identity_digest: str
    passed_gate_digest: str; candidate_set_digest: str; evaluation_input_digest: str
    optimization_objective: OptimizationObjective; requested_top_n: int
    total_candidate_count: int; feasible_candidate_count: int; infeasible_candidate_count: int
    provider_mismatch_count: int; integrity_failed_count: int; provenance_failed_count: int
    runtime_failed_count: int; unevaluated_count: int
    phase2_verified_record_count: int; phase2_integrity_invalid_record_count: int
    phase2_runtime_failed_record_count: int; phase2_unevaluated_record_count: int
    runtime_failed_from_phase2_verified_count: int; runtime_failed_from_phase2_runtime_failed_count: int
    ordered_disposition_record_digests: tuple[str, ...]
    ordered_ranked_record_digests: tuple[str, ...]
    ordered_top_n_record_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str, ...]
    ordered_phase3_source_binding_digests: tuple[str | None, ...]
    ordered_phase3_preparation_result_digests: tuple[str, ...]
    termination_status: TerminationStatus
    ordered_warning_digests: tuple[str, ...]; ordered_blocker_digests: tuple[str, ...]
    result_core_hash: str; provenance_digest: str; result_hash: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1: raise ValueError("version must be 1")
        if self.requested_top_n < 1: raise ValueError("top_n must be ≥ 1")
        for field in ["total_candidate_count","feasible_candidate_count","infeasible_candidate_count",
                       "provider_mismatch_count","integrity_failed_count","provenance_failed_count",
                       "runtime_failed_count","unevaluated_count",
                       "phase2_verified_record_count","phase2_integrity_invalid_record_count",
                       "phase2_runtime_failed_record_count","phase2_unevaluated_record_count",
                       "runtime_failed_from_phase2_verified_count","runtime_failed_from_phase2_runtime_failed_count"]:
            if getattr(self, field) < 0: raise ValueError(f"{field} < 0")
        d3 = self.feasible_candidate_count + self.infeasible_candidate_count \
             + self.provider_mismatch_count + self.integrity_failed_count \
             + self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count
        if d3 != self.total_candidate_count: raise ValueError("disposition sum ≠ total")
        p2 = self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count \
             + self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count
        if p2 != self.total_candidate_count: raise ValueError("p2 sum ≠ total")
        if self.runtime_failed_count != self.runtime_failed_from_phase2_verified_count + self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("rf cross mismatch")
        if self.phase2_verified_record_count != self.feasible_candidate_count + self.infeasible_candidate_count + self.provider_mismatch_count + self.runtime_failed_from_phase2_verified_count:
            raise ValueError("p2_verified cross mismatch")
        if self.phase2_integrity_invalid_record_count != self.integrity_failed_count + self.provenance_failed_count:
            raise ValueError("p2_ii cross mismatch")
        if self.phase2_runtime_failed_record_count != self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("p2_rf cross mismatch")
        if self.phase2_unevaluated_record_count != self.unevaluated_count:
            raise ValueError("p2_u cross mismatch")
        N, F, TN = self.total_candidate_count, self.feasible_candidate_count, min(self.requested_top_n, self.feasible_candidate_count)
        if len(self.ordered_disposition_record_digests) != N: raise ValueError("disposition length ≠ N")
        if len(self.ordered_ranked_record_digests) != F: raise ValueError("ranked length ≠ F")
        if len(self.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length ≠ min")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix")
        if len(self.ordered_phase2_source_snapshot_digests) != N: raise ValueError("snapshot digests length ≠ N")
        if len(self.ordered_phase3_source_binding_digests) != N: raise ValueError("binding digests length ≠ N")
        if len(self.ordered_phase3_preparation_result_digests) != N: raise ValueError("prep result digests length ≠ N")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, self.result_hash))
        if self.optimization_result_id != expected_id: raise ValueError("UUID mismatch")
        return self

def result_core_payload(r: OptimizationResult) -> dict[str, object]:
    return {"schema_version": r.schema_version, "sizing_request_identity_digest": r.sizing_request_identity_digest,
        "passed_gate_digest": r.passed_gate_digest, "candidate_set_digest": r.candidate_set_digest,
        "evaluation_input_digest": r.evaluation_input_digest, "optimization_objective": r.optimization_objective.value,
        "requested_top_n": r.requested_top_n, "total_candidate_count": r.total_candidate_count,
        "feasible_candidate_count": r.feasible_candidate_count, "infeasible_candidate_count": r.infeasible_candidate_count,
        "provider_mismatch_count": r.provider_mismatch_count, "integrity_failed_count": r.integrity_failed_count,
        "provenance_failed_count": r.provenance_failed_count, "runtime_failed_count": r.runtime_failed_count,
        "unevaluated_count": r.unevaluated_count,
        "phase2_verified_record_count": r.phase2_verified_record_count,
        "phase2_integrity_invalid_record_count": r.phase2_integrity_invalid_record_count,
        "phase2_runtime_failed_record_count": r.phase2_runtime_failed_record_count,
        "phase2_unevaluated_record_count": r.phase2_unevaluated_record_count,
        "runtime_failed_from_phase2_verified_count": r.runtime_failed_from_phase2_verified_count,
        "runtime_failed_from_phase2_runtime_failed_count": r.runtime_failed_from_phase2_runtime_failed_count,
        "ordered_disposition_record_digests": list(r.ordered_disposition_record_digests),
        "ordered_ranked_record_digests": list(r.ordered_ranked_record_digests),
        "ordered_top_n_record_digests": list(r.ordered_top_n_record_digests),
        "ordered_phase2_source_snapshot_digests": list(r.ordered_phase2_source_snapshot_digests),
        "ordered_phase3_source_binding_digests": list(r.ordered_phase3_source_binding_digests),
        "ordered_phase3_preparation_result_digests": list(r.ordered_phase3_preparation_result_digests),
        "termination_status": r.termination_status.value,
        "ordered_warning_digests": list(r.ordered_warning_digests),
        "ordered_blocker_digests": list(r.ordered_blocker_digests)}
```

---

## 18. Warning/blocker aggregation

```python
def build_result_message_digest_tuples(ei, dispositions, stop_index):
    for dr in dispositions:
        for d in dr.warning_descriptors: verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors: verify_phase3_message_descriptor_or_raise(d)
    all_w = [d for dr in dispositions for d in dr.warning_descriptors]
    if stop_index is not None:
        ss = _build_strict_stop_warning(ei, stop_index)
        if ss is None: raise RuntimeError("strict-stop None for PARTIAL")
        ssd = build_engineering_message_descriptor(ss)
        if isinstance(ssd, RunFailure): raise RuntimeError("strict-stop descriptor failed")
        all_w.append(ssd)
    all_w.sort(key=lambda d: d.owner_sort_key)
    all_b = [d for dr in dispositions for d in dr.blocker_descriptors]
    all_b.sort(key=lambda d: d.owner_sort_key)
    return (
        tuple(d.message_payload_digest for d in all_w),
        tuple(d.message_payload_digest for d in all_b),
    )
```

---

## 19. External verifier (P0-3, P0-4, P0-11, P0-17)

```python
def verify_optimization_result_or_raise(
    result, *, ei, source_snapshots, source_bindings,
    preparation_results, dispositions, ranked, graph,
):
    N, F = result.total_candidate_count, result.feasible_candidate_count
    # 1. Input binding
    if result.evaluation_input_digest != ei.evaluation_input_digest: raise ValueError("input digest mismatch")
    if result.sizing_request_identity_digest != ei.sizing_request_identity_digest: raise ValueError("sizing digest mismatch")
    if result.candidate_set_digest != ei.candidate_set_digest: raise ValueError("cset digest mismatch")
    if result.passed_gate_digest != ei.gate_digest: raise ValueError("gate digest mismatch")
    if result.total_candidate_count != ei.evaluation_record_count: raise ValueError("total count mismatch")
    # 2. Objective/Top-N
    if result.optimization_objective != ei.sizing_request_identity.optimization_objective: raise ValueError("objective mismatch")
    if result.requested_top_n != ei.sizing_request_identity.top_n: raise ValueError("top_n mismatch")
    # 3. Verify per-index
    if len(source_snapshots) != N: raise ValueError("snapshots count mismatch")
    if len(source_bindings) != N: raise ValueError("bindings count mismatch")
    if len(preparation_results) != N: raise ValueError("preparation_results count mismatch")
    if len(dispositions) != N: raise ValueError("dispositions count mismatch")
    for i, (rec, cand) in enumerate(zip(ei.evaluation_records, ei.materialization_result.candidates)):
        ss = source_snapshots[i]; sb = source_bindings[i]; pr = preparation_results[i]; dr = dispositions[i]
        # Source snapshot (P0-3)
        if ss.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] ss candidate_id mismatch")
        if ss.evaluation_order_index != i: raise ValueError(f"[{i}] ss index mismatch")
        if ss.phase2_source_record_descriptor_digest != ei.ordered_phase2_source_record_descriptor_digests[i]:
            raise ValueError(f"[{i}] ss descriptor mismatch")
        ss.verify_or_raise()
        # Binding
        if sb.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] sb candidate_id mismatch")
        if sb.evaluation_order_index != i: raise ValueError(f"[{i}] sb index mismatch")
        if sb.phase2_source_record_descriptor_digest != ei.ordered_phase2_source_record_descriptor_digests[i]:
            raise ValueError(f"[{i}] sb descriptor mismatch")
        if sb.phase2_source_snapshot_digest != ss.snapshot_digest:
            raise ValueError(f"[{i}] sb snapshot_digest mismatch")
        sb.verify_or_raise()
        # Preparation result (P0-12)
        if pr.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] pr candidate_id mismatch")
        if pr.evaluation_order_index != i: raise ValueError(f"[{i}] pr index mismatch")
        if pr.phase2_source_snapshot_digest != ss.snapshot_digest: raise ValueError(f"[{i}] pr snapshot digest mismatch")
        # Preparation digest in result core (P0-17)
        if result.ordered_phase2_source_snapshot_digests[i] != ss.snapshot_digest:
            raise ValueError(f"[{i}] result snapshot digest mismatch")
        if result.ordered_phase3_preparation_result_digests[i] != pr.preparation_result_digest:
            raise ValueError(f"[{i}] result prep result digest mismatch")
        if pr.status is Phase3PreparationStatus.READY:
            if pr.classification_input is None: raise ValueError(f"[{i}] READY missing cin")
            if pr.phase3_source_binding_digest != sb.binding_digest: raise ValueError(f"[{i}] READY binding digest mismatch")
            if result.ordered_phase3_source_binding_digests[i] != sb.binding_digest:
                raise ValueError(f"[{i}] result binding digest mismatch")
            verify_phase3_classification_input_or_raise(
                pr.classification_input,
                source_record=rec, source_snapshot=ss, source_binding=sb,
                candidate=cand, sizing_identity=ei.sizing_request_identity,
            )
            # Re-classify using cached bindings
            expected = classify_candidate(pr.classification_input)
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected):
                raise ValueError(f"[{i}] disposition payload mismatch")
        else:
            if pr.classification_input is not None: raise ValueError(f"[{i}] FAILED has cin")
            if pr.phase3_failure is None: raise ValueError(f"[{i}] FAILED missing failure")
            if pr.phase3_failure_digest is None: raise ValueError(f"[{i}] FAILED missing failure digest")
            if pr.failure_stage is None: raise ValueError(f"[{i}] FAILED missing failure_stage")
            # Verify expected disposition from preparation failure (P0-11)
            expected = disposition_from_preparation_failure(
                source_record=rec, source_snapshot=ss,
                candidate=cand, preparation_result=pr,
            )
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected):
                raise ValueError(f"[{i}] prep-failure disposition mismatch")
        # Disposition binding
        if dr.evaluation_order_index != i: raise ValueError(f"[{i}] dr index mismatch")
        if dr.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] dr candidate_id mismatch")
        if dr.source_record_descriptor_digest != ei.ordered_phase2_source_record_descriptor_digests[i]:
            raise ValueError(f"[{i}] dr descriptor mismatch")
        # Verify descriptor bindings (P0-6)
        for d in dr.warning_descriptors: verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors: verify_phase3_message_descriptor_or_raise(d)
    # 4. Ordered disposition digests
    expected_disp_digests = tuple(dr.feasibility_digest for dr in dispositions)
    if result.ordered_disposition_record_digests != expected_disp_digests: raise ValueError("ordered disposition digests mismatch")
    # 5. Counts
    _verify_all_counts(result, ei, dispositions)
    # 6. Ranked records
    if len(ranked) != F: raise ValueError(f"ranked count {len(ranked)} != {F}")
    feasible_disps = [d for d in dispositions if d.disposition is FEASIBLE]
    if len(feasible_disps) != F: raise ValueError("FEASIBLE count != F")
    ranked_keyed = []
    for d in feasible_disps:
        ci = d.evaluation_order_index
        candidate = ei.materialization_result.candidates[ci]
        effective_len = canonical_decimal(Decimal(candidate.effective_length_m_canonical))
        area = canonical_decimal(Decimal(d.primary_engineering_value))
        if result.optimization_objective == MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            key = (area, effective_len, d.source_qualified_candidate_id)
        else:
            key = (effective_len, area, d.source_qualified_candidate_id)
        ranked_keyed.append((key, d, ci))
    ranked_keyed.sort(key=lambda x: x[0])
    for ri, (_, disp, ci) in enumerate(ranked_keyed):
        rr = ranked[ri]
        candidate = ei.materialization_result.candidates[ci]
        pv, pf, sv, sf = expected_ranked_values(disp, candidate, result.optimization_objective)
        if rr.rank != ri + 1: raise ValueError(f"ranked[{ri}]: rank {rr.rank} != {ri+1}")
        if rr.source_qualified_candidate_id != disp.source_qualified_candidate_id: raise ValueError(f"ranked[{ri}]: candidate_id mismatch")
        if rr.feasibility_digest != disp.feasibility_digest: raise ValueError(f"ranked[{ri}]: feasibility digest mismatch")
        if rr.candidate_evaluation_identity_digest != disp.candidate_evaluation_identity_digest: raise ValueError(f"ranked[{ri}]: identity digest mismatch")
        if rr.verified_rating_evidence_digest != disp.verified_rating_evidence_digest: raise ValueError(f"ranked[{ri}]: evidence digest mismatch")
        if rr.primary_objective_value != pv or rr.primary_objective_field != pf: raise ValueError(f"ranked[{ri}]: primary mismatch")
        if rr.secondary_tie_break_value != sv or rr.secondary_tie_break_field != sf: raise ValueError(f"ranked[{ri}]: secondary mismatch")
        rr.verify_or_raise()
        if result.ordered_ranked_record_digests[ri] != rr.ranked_record_digest: raise ValueError(f"ranked[{ri}]: result digest mismatch")
    # 7. Top-N
    TN = min(result.requested_top_n, F)
    if len(result.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length mismatch")
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix")
    # 8. Warning/blocker aggregation
    stop_index = _find_stop_index(ei)
    expected_w, expected_b = build_result_message_digest_tuples(ei, dispositions, stop_index)
    if tuple(result.ordered_warning_digests) != expected_w: raise ValueError("warning digests mismatch")
    if tuple(result.ordered_blocker_digests) != expected_b: raise ValueError("blocker digests mismatch")
    # 9. Termination
    si = _find_stop_index(ei)
    if si is None:
        if result.termination_status is not COMPLETE: raise ValueError("must be COMPLETE")
    else:
        if result.termination_status is not PARTIAL: raise ValueError("must be PARTIAL")
    # 10. Hash
    expected_core = sha256_digest(result_core_payload(result))
    if result.result_core_hash != expected_core: raise ValueError("core hash mismatch")
    verify_phase3_provenance_graph_or_raise(graph, ei=ei, dispositions=dispositions, ranked=ranked, result=result)
    if result.provenance_digest != graph.compute_hash(): raise ValueError("provenance digest mismatch")
    expected_env = sha256_digest({"result_core_hash": result.result_core_hash, "provenance_digest": result.provenance_digest})
    if result.result_hash != expected_env: raise ValueError("envelope hash mismatch")
    expected_uuid = str(uuid.uuid5(PHASE3_RESULT_NS, result.result_hash))
    if result.optimization_result_id != expected_uuid: raise ValueError("UUID mismatch")
    # 11. Format
    for field in ["sizing_request_identity_digest","passed_gate_digest","candidate_set_digest","evaluation_input_digest","result_core_hash","provenance_digest","result_hash"]:
        if not re.match(r"^sha256:[0-9a-f]{64}$", getattr(result, field)): raise ValueError(f"invalid {field}")
    for lst, name in [(result.ordered_disposition_record_digests, "disposition"),
                       (result.ordered_ranked_record_digests, "ranked"),
                       (result.ordered_top_n_record_digests, "top_n")]:
        if len(set(lst)) != len(lst): raise ValueError(f"{name} digests not unique")
```

---

## 20. Provenance (P0-17)

### 20.1 Namespace and node ID

```python
PHASE3_RESULT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

@dataclass(frozen=True, slots=True)
class ExpectedPhase3ProvenanceNode:
    role: str
    node_type: ProvenanceNodeType
    payload_hash: str

def expected_phase3_node_id(role: str, node_type: ProvenanceNodeType, payload_hash: str) -> UUID:
    return uuid.uuid5(PHASE3_PROVENANCE_NS, f"{role}:{node_type.value}:{payload_hash}")

def expected_phase3_provenance_nodes(*, ei, dispositions, ranked, result):
    nodes = []
    # Root
    root_payload = sha256_digest({"artifact_kind": "phase3_evaluation_input", "evaluation_input_digest": ei.evaluation_input_digest})
    nodes.append(ExpectedPhase3ProvenanceNode("root", ProvenanceNodeType.EXTERNAL, root_payload))
    # Sizing request
    nodes.append(ExpectedPhase3ProvenanceNode("sizing_request", ProvenanceNodeType.INPUT_FILE, ei.sizing_request_identity_digest))
    # Passed gate
    nodes.append(ExpectedPhase3ProvenanceNode("passed_gate", ProvenanceNodeType.CALCULATION_RUN, ei.gate_digest))
    # Candidate set
    nodes.append(ExpectedPhase3ProvenanceNode("candidate_set", ProvenanceNodeType.CALCULATION_RUN, ei.candidate_set_digest))
    # Evaluation input
    nodes.append(ExpectedPhase3ProvenanceNode("evaluation_input", ProvenanceNodeType.INTERMEDIATE, ei.evaluation_input_digest))
    # Source snapshot set (P0-17)
    agg_snapshot_payload = sha256_digest({"ordered_phase2_source_snapshot_digests": list(result.ordered_phase2_source_snapshot_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("source_snapshot_set", ProvenanceNodeType.INTERMEDIATE, agg_snapshot_payload))
    # Source binding set (P0-17)
    agg_binding_payload = sha256_digest({"ordered_phase3_source_binding_digests": list(result.ordered_phase3_source_binding_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("source_binding_set", ProvenanceNodeType.INTERMEDIATE, agg_binding_payload))
    # Preparation result set (P0-17)
    agg_prep_payload = sha256_digest({"ordered_phase3_preparation_result_digests": list(result.ordered_phase3_preparation_result_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("preparation_result_set", ProvenanceNodeType.INTERMEDIATE, agg_prep_payload))
    # Dispositions
    for i, d in enumerate(dispositions):
        nodes.append(ExpectedPhase3ProvenanceNode(f"disposition[{i}]", ProvenanceNodeType.INTERMEDIATE, d.feasibility_digest))
    # Ranked
    for i, r in enumerate(ranked):
        nodes.append(ExpectedPhase3ProvenanceNode(f"ranked[{i}]", ProvenanceNodeType.INTERMEDIATE, r.ranked_record_digest))
    # Top-N selection
    top_n_digest = sha256_digest({"ordered_top_n_record_digests": list(result.ordered_top_n_record_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("top_n_selection", ProvenanceNodeType.INTERMEDIATE, top_n_digest))
    # Result core
    nodes.append(ExpectedPhase3ProvenanceNode("result_core", ProvenanceNodeType.RESULT, result.result_core_hash))
    # Optimizer
    optimizer_payload = sha256_digest({
        "schema_version": 1, "evaluation_input_digest": ei.evaluation_input_digest,
        "optimization_objective": result.optimization_objective.value,
        "requested_top_n": result.requested_top_n, "termination_status": result.termination_status.value,
        "result_core_hash": result.result_core_hash, "phase3_algorithm_version": "task009-phase3-v1",
    })
    nodes.append(ExpectedPhase3ProvenanceNode("optimizer", ProvenanceNodeType.OPTIMIZER, optimizer_payload))
    return tuple(nodes)

def expected_phase3_provenance_edge_keys(*, expected_nodes, dispositions, ranked, result):
    edges = []
    uid_map = {n.role: expected_phase3_node_id(n.role, n.node_type, n.payload_hash) for n in expected_nodes}
    def uid(role: str) -> str: return str(uid_map[role])

    edges.append((uid("root"), uid("sizing_request"), Phase3ProvenanceRelation.REGULATES.value))
    edges.append((uid("sizing_request"), uid("passed_gate"), Phase3ProvenanceRelation.CONSUMED_BY.value))
    edges.append((uid("passed_gate"), uid("candidate_set"), Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("candidate_set"), uid("evaluation_input"), Phase3ProvenanceRelation.CONSUMED_BY.value))
    # Evaluation input -> snapshot set -> binding set -> preparation result set -> disposition chain
    edges.append((uid("evaluation_input"), uid("source_snapshot_set"), Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("source_snapshot_set"), uid("source_binding_set"), Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("source_binding_set"), uid("preparation_result_set"), Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("preparation_result_set"), uid("evaluation_input"), Phase3ProvenanceRelation.CONSUMED_BY.value))
    # Evaluation input -> dispositions
    for i, d in enumerate(dispositions):
        edges.append((uid("evaluation_input"), uid(f"disposition[{i}]"), Phase3ProvenanceRelation.EVALUATED.value))
    # FEASIBLE disposition -> ranked
    feasible_mask = {}
    for i, d in enumerate(dispositions):
        if d.disposition is FEASIBLE:
            feasible_mask[(d.source_qualified_candidate_id, d.feasibility_digest)] = i
    for ri, r in enumerate(ranked):
        key = (r.source_qualified_candidate_id, r.feasibility_digest)
        di = feasible_mask.get(key)
        if di is None: raise ValueError(f"ranked[{ri}]: no matching FEASIBLE disposition")
        edges.append((uid(f"disposition[{di}]"), uid(f"ranked[{ri}]"), Phase3ProvenanceRelation.RANKED.value))
    # Top-N
    edges.append((uid("evaluation_input"), uid("top_n_selection"), Phase3ProvenanceRelation.SELECTED_BY.value))
    TN = min(result.requested_top_n, len(ranked))
    for ri in range(TN):
        edges.append((uid(f"ranked[{ri}]"), uid("top_n_selection"), Phase3ProvenanceRelation.SELECTED.value))
    edges.append((uid("top_n_selection"), uid("result_core"), Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("result_core"), uid("optimizer"), Phase3ProvenanceRelation.EXECUTED_BY.value))
    return tuple(sorted(edges))
```

Node count: 11 + N + F (5 baseline + 3 agg sets + root + sizing + gate + candidate_set + evaluation_input + N dispositions + F ranked + top_n_selection + result_core + optimizer = 11 + N + F).

### 20.2 Semantic verifier

```python
def verify_phase3_provenance_graph_or_raise(graph, *, ei, dispositions, ranked, result):
    expected_nodes = expected_phase3_provenance_nodes(ei=ei, dispositions=dispositions, ranked=ranked, result=result)
    expected_count = 11 + len(dispositions) + len(ranked)
    if len(expected_nodes) != expected_count: raise ValueError(f"expected node count {len(expected_nodes)} != {expected_count}")
    if len(graph.nodes) != expected_count: raise ValueError(f"graph node count {len(graph.nodes)} != {expected_count}")
    expected_ids = {}
    for n in expected_nodes:
        eid = expected_phase3_node_id(n.role, n.node_type, n.payload_hash)
        if eid in expected_ids: raise ValueError(f"duplicate expected ID for role {n.role}")
        expected_ids[eid] = n
    actual_by_id = {}
    for n in graph.nodes:
        aid = n.node_id
        if aid in actual_by_id: raise ValueError(f"duplicate actual node ID {aid}")
        actual_by_id[aid] = n
    for eid, exp in expected_ids.items():
        actual = actual_by_id.get(eid)
        if actual is None: raise ValueError(f"missing node: {exp.role}")
        if actual.node_type != exp.node_type: raise ValueError(f"{exp.role}: type mismatch")
        if actual.payload_hash != exp.payload_hash: raise ValueError(f"{exp.role}: payload hash mismatch")
        if actual.label != "": raise ValueError(f"{exp.role}: label not empty")
        if actual.metadata != (): raise ValueError(f"{exp.role}: metadata not empty")
    extra = set(actual_by_id) - set(expected_ids)
    if extra: raise ValueError(f"extra nodes: {len(extra)}")
    expected_edges = expected_phase3_provenance_edge_keys(
        expected_nodes=expected_nodes, dispositions=dispositions, ranked=ranked, result=result)
    actual_edges = tuple(sorted((str(e.source_id), str(e.target_id), e.relation) for e in graph.edges))
    if len(actual_edges) != len(set(actual_edges)): raise ValueError("duplicate edges")
    if actual_edges != expected_edges: raise ValueError("edge set mismatch")
    for e in graph.edges:
        if e.metadata != (): raise ValueError("edge metadata not empty")
    root_id = expected_phase3_node_id(expected_nodes[0].role, expected_nodes[0].node_type, expected_nodes[0].payload_hash)
    children = {n.node_id: [] for n in graph.nodes}
    for e in graph.edges: children[e.source_id].append(e.target_id)
    visited, queue = set(), [root_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited: continue
        visited.add(nid); queue.extend(children.get(nid, []))
    if len(visited) != len(graph.nodes): raise ValueError("unreachable nodes")
```

---

## 21. Single-pass descriptor helpers

```python
def build_engineering_message_descriptor(
    message: EngineeringMessage,
) -> Phase3MessageDescriptor | RunFailure:
    try:
        desc = _build_message_descriptor(message)
    except ContextCanonicalizationError as exc:
        return _canonicalization_to_failure(exc, "build", "", -1, "", -1, "")
    except TypeError as exc:
        return _descriptor_build_failure(exc, "build", "", -1, "", -1, "")
    except ValueError as exc:
        return _descriptor_build_failure(exc, "build", "", -1, "", -1, "")
    if desc.canonicalization_error is not None:
        return _descriptor_error_to_failure(desc, "build", "", -1, "", -1)
    if desc.message_payload_digest is None:
        return RunFailure(
            code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
            message="Message descriptor has no payload digest.",
            source_module="hexagent.optimization.feasibility",
            affected_paths=(),
            context=(
                ("failure_stage", "descriptor"), ("owner_kind", "build"),
                ("source_qualified_candidate_id", ""), ("evaluation_order_index", -1),
                ("source_record_descriptor_digest", ""), ("message_index", -1),
                ("original_code", ""), ("context_key", ""), ("context_path_digest", ""),
                ("offending_type", ""), ("failure_kind", "missing_message_payload_digest"),
                ("safe_marker_digest", ""),
            ),
        )
    return Phase3MessageDescriptor(
        owner_sort_key=desc.owner_sort_key,
        original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest,
    )

def canonicalize_phase3_messages_or_failure(
    messages: tuple[EngineeringMessage, ...],
    owner_kind: str,
    source_qualified_candidate_id: str,
    evaluation_order_index: int,
    source_record_descriptor_digest: str,
) -> tuple[Phase3MessageDescriptor, ...] | RunFailure:
    descriptors = []
    for mi, msg in enumerate(messages):
        desc = build_engineering_message_descriptor(msg)
        if isinstance(desc, RunFailure):
            # Read original_code from the message when available (P0-16)
            orig_code = str(msg.code) if hasattr(msg, 'code') and msg.code is not None else ""
            return _enrich_failure_context(
                desc,
                owner_kind=owner_kind,
                candidate_id=source_qualified_candidate_id,
                evaluation_index=evaluation_order_index,
                source_descriptor_digest=source_record_descriptor_digest,
                message_index=mi,
                original_code=orig_code,
            )
        descriptors.append(desc)
    descriptors.sort(key=lambda d: d.owner_sort_key)
    return tuple(descriptors)

def _enrich_failure_context(
    failure: RunFailure,
    *,
    owner_kind: str,
    candidate_id: str,
    evaluation_index: int,
    source_descriptor_digest: str,
    message_index: int,
    original_code: str,
) -> RunFailure:
    existing = dict(failure.context)
    # Preserve non-empty original_code from the failure descriptor (P0-16)
    resolved_code = existing.get("original_code") if existing.get("original_code") else original_code
    existing.update({
        "owner_kind": owner_kind,
        "source_qualified_candidate_id": candidate_id,
        "evaluation_order_index": evaluation_index,
        "source_record_descriptor_digest": source_descriptor_digest,
        "message_index": message_index,
        "original_code": resolved_code,
    })
    return RunFailure(
        code=failure.code, message=failure.message,
        source_module=failure.source_module, affected_paths=failure.affected_paths,
        context=tuple(existing.items()),
    )
```

Note: P0-16 resolved — `original_code` from the source descriptor is preserved via `_descriptor_error_to_failure()` which already sets it. Empty string fallback only used when neither source nor caller provides a real code.

---

## 22. Single-pass wrapper descriptor helpers

```python
def _canonicalization_to_failure(
    error: ContextCanonicalizationError,
    owner_kind: str, candidate_id: str, evaluation_index: int,
    source_descriptor_digest: str, message_index: int, original_code: str,
) -> RunFailure:
    return RunFailure(
        code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
        message="Trusted context canonicalization failed during feasibility classification.",
        source_module="hexagent.optimization.feasibility",
        affected_paths=(),
        context=(
            ("failure_stage", "canonicalization"), ("owner_kind", owner_kind),
            ("source_qualified_candidate_id", candidate_id), ("evaluation_order_index", evaluation_index),
            ("source_record_descriptor_digest", source_descriptor_digest), ("message_index", message_index),
            ("original_code", original_code),
            ("context_key", error.context_key),
            ("context_path_digest", sha256_digest({"context_path": list(error.context_path)})),
            ("offending_type", error.offending_type),
            ("failure_kind", error.failure_kind.value),
            ("safe_marker_digest", sha256_digest({
                "context_key": error.context_key, "context_path": list(error.context_path),
                "offending_type": error.offending_type, "failure_kind": error.failure_kind.value,
            })),
        ),
    )

def _descriptor_build_failure(
    exc: Exception, owner_kind: str, candidate_id: str, evaluation_index: int,
    source_descriptor_digest: str, message_index: int, original_code: str,
) -> RunFailure:
    return RunFailure(
        code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
        message="Descriptor build raised exception during feasibility classification.",
        source_module="hexagent.optimization.feasibility",
        affected_paths=(),
        context=(
            ("failure_stage", "build"), ("owner_kind", owner_kind),
            ("source_qualified_candidate_id", candidate_id), ("evaluation_order_index", evaluation_index),
            ("source_record_descriptor_digest", source_descriptor_digest), ("message_index", message_index),
            ("original_code", original_code), ("context_key", ""), ("context_path_digest", ""),
            ("offending_type", type(exc).__qualname__), ("failure_kind", "build_exception"),
            ("safe_marker_digest", ""),
        ),
    )

def _descriptor_error_to_failure(
    descriptor, owner_kind: str, candidate_id: str, evaluation_index: int,
    source_descriptor_digest: str, message_index: int,
) -> RunFailure:
    err = descriptor.canonicalization_error
    return RunFailure(
        code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
        message="Trusted context canonicalization failed during feasibility classification.",
        source_module="hexagent.optimization.feasibility",
        affected_paths=(),
        context=(
            ("failure_stage", "descriptor"), ("owner_kind", owner_kind),
            ("source_qualified_candidate_id", candidate_id), ("evaluation_order_index", evaluation_index),
            ("source_record_descriptor_digest", source_descriptor_digest), ("message_index", message_index),
            ("original_code", descriptor.original_code),
            ("context_key", err.context_key),
            ("context_path_digest", sha256_digest({"context_path": list(err.context_path)})),
            ("offending_type", err.offending_type),
            ("failure_kind", err.failure_kind.value),
            ("safe_marker_digest", sha256_digest({
                "context_key": err.context_key, "context_path": list(err.context_path),
                "offending_type": err.offending_type, "failure_kind": err.failure_kind.value,
            })),
        ),
    )
```

No `str(exc)`, `repr(exc)`, `traceback`, or `memory address` in any hash-sensitive payload.

---

## 23. Complete builder helpers (P0-18)

```python
def _map_non_verified(rec: CandidateEvaluationRecord) -> CandidateDispositionRecord:
    """Maps INTEGRITY_INVALID → INTEGRITY_FAILED/PROVENANCE_FAILED, RUNTIME_FAILED → RUNTIME_FAILED(P2), UNEVALUATED → UNEVALUATED."""
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
            source_record_descriptor_digest="",  # filled by caller
            disposition=disp, diagnostic=diag,
            provider_identity_matches=rec.provider_identity_matches,
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
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest="",
            disposition=Phase3Disposition.RUNTIME_FAILED,
            diagnostic=FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None, verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_digest=sha256_digest(run_failure_payload(rec.evaluation_failure))
                if rec.evaluation_failure is not None else None,
            phase3_failure_digest=None, failure_origin=FailureOrigin.PHASE2_EVALUATION,
        )
    elif rec.candidate_evaluation_state == UNEVALUATED:
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest="",
            disposition=Phase3Disposition.UNEVALUATED, diagnostic=FeasibilityDiagnosticKey.NONE,
            provider_identity_matches=rec.provider_identity_matches,
            rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None, verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_digest=None, phase3_failure_digest=None,
            failure_origin=FailureOrigin.NONE,
        )
    raise ValueError(f"unexpected state: {rec.candidate_evaluation_state}")

def _build_provider_mismatch(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot | None,
    eb: Phase3SourceRecordBinding,
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest="",
        disposition=Phase3Disposition.PROVIDER_IDENTITY_MISMATCH,
        diagnostic=FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH,
        provider_identity_matches=False,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None, secondary_engineering_value=None,
        warning_descriptors=(), blocker_descriptors=(),
        source_evaluation_failure_digest=None, phase3_failure_digest=None,
        failure_origin=FailureOrigin.NONE,
    )

def _build_infeasible(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    diagnostic: FeasibilityDiagnosticKey,
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest="",
        disposition=Phase3Disposition.INFEASIBLE, diagnostic=diagnostic,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None, secondary_engineering_value=None,
        warning_descriptors=(), blocker_descriptors=(),
        source_evaluation_failure_digest=None, phase3_failure_digest=None,
        failure_origin=FailureOrigin.NONE,
    )

def _build_feasible(
    rec: CandidateEvaluationRecord,
    evidence: VerifiedRatingEvidenceSnapshot,
    eb: Phase3SourceRecordBinding,
) -> CandidateDispositionRecord:
    heat_w = canonical_decimal_string(to_canonical_decimal(evidence.heat_duty_w))
    area_m2 = canonical_decimal_string(to_canonical_decimal(evidence.area_outer_m2))
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest="",
        disposition=Phase3Disposition.FEASIBLE, diagnostic=FeasibilityDiagnosticKey.NONE,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=area_m2, secondary_engineering_value=heat_w,
        warning_descriptors=(), blocker_descriptors=(),
        source_evaluation_failure_digest=None, phase3_failure_digest=None,
        failure_origin=FailureOrigin.NONE,
    )

def _phase3_runtime(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    code: ErrorCode,
    msg: str,
    failure_stage: Phase3PreparationFailureStage | None,
) -> CandidateDispositionRecord:
    failure = RunFailure(
        code=code, message=msg, source_module="hexagent.optimization.feasibility",
        affected_paths=(),
        context=(("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                 ("evaluation_order_index", rec.evaluation_order_index)),
    )
    failure_digest = sha256_digest(run_failure_payload(failure))
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest="",
        disposition=Phase3Disposition.RUNTIME_FAILED,
        diagnostic=FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None, secondary_engineering_value=None,
        warning_descriptors=(), blocker_descriptors=(),
        source_evaluation_failure_digest=None,
        phase3_failure_digest=failure_digest,
        failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
        failure_stage=failure_stage,
    )

def _phase3_runtime_from_validation(
    rec: CandidateEvaluationRecord,
    eb: Phase3SourceRecordBinding,
    validation_failure: RunFailure,
) -> CandidateDispositionRecord:
    failure_digest = sha256_digest(run_failure_payload(validation_failure))
    return build_candidate_disposition_record(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest="",
        disposition=Phase3Disposition.RUNTIME_FAILED,
        diagnostic=FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity is not None else None,
        verified_rating_evidence_digest=eb.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None, secondary_engineering_value=None,
        warning_descriptors=(), blocker_descriptors=(),
        source_evaluation_failure_digest=None,
        phase3_failure_digest=failure_digest,
        failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
        failure_stage=None,
    )

def _build_strict_stop_warning(ei: Phase3EvaluationInput, stop_index: int) -> EngineeringMessage | None:
    """Builds strict-stop EngineeringMessage from the stopping candidate."""
    if stop_index >= len(ei.evaluation_records):
        return None
    rec = ei.evaluation_records[stop_index]
    return EngineeringMessage(
        code=ErrorCode.PHASE3_STRICT_STOP,
        message=f"Candidate {rec.source_qualified_candidate_id} at index {stop_index} "
                f"has state {rec.candidate_evaluation_state.value}. Strict stop.",
        source_module="hexagent.optimization.feasibility",
        context=(
            ("owner_sort_key", ("phase3", "strict_stop", "phase3", "strict_stop", (), "")),
            ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
            ("evaluation_order_index", stop_index),
            ("candidate_evaluation_state", rec.candidate_evaluation_state.value),
        ),
    )

def expected_ranked_values(
    disp: CandidateDispositionRecord,
    candidate: ManufacturableCandidate,
    optimization_objective: OptimizationObjective,
) -> tuple[str, str, str, str]:
    """Returns (primary_value, primary_field, secondary_value, secondary_field)."""
    disp_area = disp.primary_engineering_value
    candidate_len = candidate.effective_length_m_canonical
    if optimization_objective == MINIMUM_OUTER_HEAT_TRANSFER_AREA:
        return disp_area, "area_outer_m2", canonical_decimal_string(Decimal(candidate_len)), "effective_length_m_canonical"
    else:
        return canonical_decimal_string(Decimal(candidate_len)), "effective_length_m_canonical", disp_area, "area_outer_m2"
```

All 8 builders have explicit typed signatures, exact field assignments, and no placeholder `...` or `pass`.

---

## 24. Implementation boundary

New files: `phase3_input.py`, `feasibility.py` (preparation + classification), `ranking.py`, `result.py`. Existing modified: `messages.py` (add error codes), `evaluation.py` (export descriptor builder `verified_rating_evidence_payload_from_descriptors`). Untouched: all Phase 1/2 modules, TASK-008, catalog, existing tests.

---

## 25. Test matrix

Complete 26-field descriptor-based evidence digest; thermal metric tamper changes evidence digest; provider identity tamper changes evidence digest; correlation digest tamper changes evidence digest; snapshot one-shot factory; snapshot constructed before EvaluationInput; snapshot state-field tamper rejected; snapshot evidence digest tamper rejected; classification input uses snapshot (not binding) for source descriptor; verify_phase2_source_record_snapshot_or_raise executes; warning context traversed exactly once; blocker context traversed exactly once; evidence failure context traversed exactly once; source evaluation failure context traversed exactly once; Phase3MessageDescriptorBinding artifact constructed and persisted; build_phase3_message_descriptor_binding factory digest parity; owner_sort_key tamper rejected by authoritative binding; early preparation failure without full source binding (READY/FAILED both covered); READY preparation with full source binding; failure-stage evidence availability matrix under P0-9; failure_stage participates in feasibility_digest; FAILED preparation failure digest tamper rejected; FAILED preparation candidate swap rejected; FAILED preparation expected disposition replay via disposition_from_preparation_failure; classification source record full verified (thermal tamper rejected); P2-RF-6 exact warning owner_kind literal; P2-RF-7 exact blocker owner_kind literal; P2-RF-8 exact run_failure owner_kind literal; P2-RF-5 exact verification_runtime owner_kind literal; P2-RF-1 exact `__name__` message validation; canonicalization original_code retained (P0-16); snapshot/binding/preparation digests in result core (P0-17); snapshot/binding/preparation provenance binding (P0-17); zero binding provenance for FAILED candidates; all 8 disposition builders fully specified (no "each calls") (P0-18); message descriptor binding factory digest parity; `verified_rating_evidence_payload_from_descriptors` called in snapshot preparation; no `compute_explicit_evidence_digest` in Phase 3; no `run_failure_payload(evidence.failure)` re-read; no single-arg `evaluation_record_descriptor_payload(rec)`; no `original_code=""` override.

---

## 26. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
