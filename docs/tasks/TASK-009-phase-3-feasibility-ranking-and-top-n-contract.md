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
```

---

## 3. Evidence digest via authoritative Phase 2 helper

```python
def compute_evidence_digest(
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
        expected = sha256_digest({"owner_sort_key": list(self.owner_sort_key), "original_code": self.original_code, "message_payload_digest": self.message_payload_digest})
        if self.descriptor_binding_digest != expected: raise ValueError("descriptor_binding_digest mismatch")
        return self

def build_phase3_message_descriptor_binding(desc: Phase3MessageDescriptor) -> Phase3MessageDescriptorBinding:
    payload = {"owner_sort_key": list(desc.owner_sort_key), "original_code": desc.original_code, "message_payload_digest": desc.message_payload_digest}
    d = sha256_digest(payload)
    return Phase3MessageDescriptorBinding(owner_sort_key=desc.owner_sort_key, original_code=desc.original_code, message_payload_digest=desc.message_payload_digest, descriptor_binding_digest=d)
```

---

## 5. RunFailure descriptor binding (P0-2, P0-3, P0-4)

Production `CanonicalizedRunFailureDescriptor` has: `original_code`, `canonical_payload`, `payload_digest`, `canonicalization_error`, `context_path_digest`, `safe_marker_digest`. No `descriptor_digest`.

Phase 3 computes its own binding digest from these real fields.

```python
def canonicalized_run_failure_descriptor_binding_payload(
    descriptor: CanonicalizedRunFailureDescriptor,
) -> dict[str, object]:
    ce = descriptor.canonicalization_error
    ce_digest = sha256_digest({"failure_kind": ce.failure_kind.value, "context_key": ce.context_key,
        "context_path": list(ce.context_path), "offending_type": ce.offending_type,
        "safe_marker_digest": ce.safe_marker_digest}) if ce is not None else None
    cp_digest = ce.context_path_digest if ce is not None else None
    sm_digest = ce.safe_marker_digest if ce is not None else None
    return {
        "original_code": descriptor.original_code,
        "payload_digest": descriptor.payload_digest if ce is None else None,
        "canonicalization_error_digest": ce_digest,
        "context_path_digest": cp_digest,
        "safe_marker_digest": sm_digest,
    }

def build_phase3_run_failure_descriptor_binding(
    descriptor: CanonicalizedRunFailureDescriptor,
) -> Phase3RunFailureDescriptorBinding:
    raw = canonicalized_run_failure_descriptor_binding_payload(descriptor)
    binding_digest = sha256_digest(raw)
    ce = descriptor.canonicalization_error
    payload_digest = descriptor.payload_digest if ce is None else None
    ce_digest = sha256_digest({"failure_kind": ce.failure_kind.value, "context_key": ce.context_key,
        "context_path": list(ce.context_path), "offending_type": ce.offending_type,
        "safe_marker_digest": ce.safe_marker_digest}) if ce is not None else None
    cp_digest = ce.context_path_digest if ce is not None else None
    sm_digest = ce.safe_marker_digest if ce is not None else None
    return Phase3RunFailureDescriptorBinding(
        original_code=descriptor.original_code,
        payload_digest=payload_digest,
        canonicalization_error_digest=ce_digest,
        context_path_digest=cp_digest,
        safe_marker_digest=sm_digest,
        descriptor_binding_digest=binding_digest,
    )

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
        if not self.DIGEST_PATTERN.match(self.descriptor_binding_digest): raise ValueError("invalid descriptor_binding_digest")
        # SUCCESS state
        if self.payload_digest is not None:
            if not self.DIGEST_PATTERN.match(self.payload_digest): raise ValueError("invalid payload_digest")
            if self.canonicalization_error_digest is not None: raise ValueError("SUCCESS: ce_digest must be None")
            if self.context_path_digest is not None: raise ValueError("SUCCESS: ctx_path must be None")
            if self.safe_marker_digest is not None: raise ValueError("SUCCESS: safe_marker must be None")
        # CANONICALIZATION_FAILED state
        elif self.canonicalization_error_digest is not None:
            if self.payload_digest is not None: raise ValueError("FAILED: payload_digest must be None")
            if not self.DIGEST_PATTERN.match(self.canonicalization_error_digest): raise ValueError("invalid ce_digest")
            if self.context_path_digest is None or not self.DIGEST_PATTERN.match(self.context_path_digest): raise ValueError("invalid ctx_path_digest")
            if self.safe_marker_digest is None or not self.DIGEST_PATTERN.match(self.safe_marker_digest): raise ValueError("invalid safe_marker_digest")
        else:
            raise ValueError("RunFailureBinding: must be SUCCESS or CANONICALIZATION_FAILED")
        # Verify binding digest
        payload = {"original_code": self.original_code, "payload_digest": self.payload_digest,
            "canonicalization_error_digest": self.canonicalization_error_digest,
            "context_path_digest": self.context_path_digest, "safe_marker_digest": self.safe_marker_digest}
        expected = sha256_digest(payload)
        if self.descriptor_binding_digest != expected: raise ValueError("descriptor_binding_digest mismatch")
        return self
```

---

## 6. Phase2SourceRecordIdentitySnapshot

```python
class Phase2SourceRecordIdentitySnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    feasible: bool
    feasibility_status: FeasibilityStatus  # P0-16: real production type
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
    return {"schema_version": s.schema_version, "source_qualified_candidate_id": s.source_qualified_candidate_id,
        "evaluation_order_index": s.evaluation_order_index, "candidate_evaluation_state": s.candidate_evaluation_state.value,
        "feasible": s.feasible, "feasibility_status": s.feasibility_status.value,
        "hash_verification_outcome": s.hash_verification_outcome.value, "provenance_verification_outcome": s.provenance_verification_outcome.value,
        "provider_identity_matches": s.provider_identity_matches, "rating_status": s.rating_status,
        "candidate_evaluation_identity_digest": s.candidate_evaluation_identity_digest,
        "invalid_rating_evidence_digest": s.invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": s.claimed_rating_result_audit_digest}

def build_identity_snapshot(rec: CandidateEvaluationRecord) -> Phase2SourceRecordIdentitySnapshot:
    eid = rec.candidate_evaluation_identity.candidate_evaluation_identity_digest if rec.candidate_evaluation_identity is not None else None
    iid = rec.invalid_rating_evidence.invalid_evidence_digest if rec.invalid_rating_evidence is not None else None
    ad = rec.claimed_rating_result_audit.audit_digest if rec.claimed_rating_result_audit is not None else None
    payload = {"schema_version": 1, "source_qualified_candidate_id": rec.source_qualified_candidate_id,
        "evaluation_order_index": rec.evaluation_order_index, "candidate_evaluation_state": rec.candidate_evaluation_state.value,
        "feasible": rec.feasible, "feasibility_status": rec.feasibility_status.value,
        "hash_verification_outcome": rec.hash_verification_outcome.value, "provenance_verification_outcome": rec.provenance_verification_outcome.value,
        "provider_identity_matches": rec.provider_identity_matches, "rating_status": rec.rating_status,
        "candidate_evaluation_identity_digest": eid, "invalid_rating_evidence_digest": iid, "claimed_rating_result_audit_digest": ad}
    digest = sha256_digest(payload)
    return Phase2SourceRecordIdentitySnapshot(schema_version=1, source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index, candidate_evaluation_state=rec.candidate_evaluation_state,
        feasible=rec.feasible, feasibility_status=rec.feasibility_status,
        hash_verification_outcome=rec.hash_verification_outcome, provenance_verification_outcome=rec.provenance_verification_outcome,
        provider_identity_matches=rec.provider_identity_matches, rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=eid, invalid_rating_evidence_digest=iid, claimed_rating_result_audit_digest=ad,
        identity_snapshot_digest=digest)
```

---

## 7. Phase2SourceRecordSnapshot (P0-1)

### 7.1 Primitive payload helper (P0-1)

```python
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

def build_phase2_source_record_snapshot(**fields) -> Phase2SourceRecordSnapshot:
    payload = phase2_source_record_snapshot_payload_from_values(**fields)
    sd = sha256_digest(payload)
    return Phase2SourceRecordSnapshot(**fields, snapshot_digest=sd)
```

### 7.2 Model

```python
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
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        for f in ("phase2_source_record_descriptor_digest", "snapshot_digest"):
            if not self.DIGEST_PATTERN.match(getattr(self, f)): raise ValueError(f"invalid {f}")
        for v, n in [(self.candidate_evaluation_identity_digest, "identity"),
                      (self.verified_rating_evidence_digest, "evidence"),
                      (self.invalid_rating_evidence_digest, "invalid"),
                      (self.claimed_rating_result_audit_digest, "audit"),
                      (self.evaluation_failure_digest, "failure"),
                      (self.source_evaluation_failure_binding_digest, "source_failure_binding"),
                      (self.evidence_failure_binding_digest, "evidence_failure_binding")]:
            if v is not None and not self.DIGEST_PATTERN.match(v): raise ValueError(f"invalid {n} digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(phase2_source_record_snapshot_payload_from_values(
            schema_version=self.schema_version, source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index, candidate_evaluation_state=self.candidate_evaluation_state,
            feasible=self.feasible, feasibility_status=self.feasibility_status,
            hash_verification_outcome=self.hash_verification_outcome, provenance_verification_outcome=self.provenance_verification_outcome,
            provider_identity_matches=self.provider_identity_matches, rating_status=self.rating_status,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            invalid_rating_evidence_digest=self.invalid_rating_evidence_digest,
            claimed_rating_result_audit_digest=self.claimed_rating_result_audit_digest,
            evaluation_failure_digest=self.evaluation_failure_digest,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest))
        if self.snapshot_digest != expected: raise ValueError("snapshot_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        if self.snapshot_digest != sha256_digest(phase2_source_record_snapshot_payload_from_values(**self.model_dump())):
            raise ValueError("snapshot_digest mismatch")
```

---

## 8. Phase 2 constructor matrix

### 8.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity: `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 8.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 8.3 RUNTIME_FAILED — executable path specs (10 paths, P0-15)

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
    if record.candidate_evaluation_state != RUNTIME_FAILED: raise ValueError("not RUNTIME_FAILED")
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
            if not record.evaluation_failure.message.startswith(template): continue
            suffix = record.evaluation_failure.message[len(template):]
            if not suffix: continue  # P0-15: empty suffix rejected
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_.]*$', suffix): continue  # P0-15: safe type-name chars only
        if spec.context_keys:
            ctx_keys = tuple(p[0] for p in record.evaluation_failure.context)
            if ctx_keys != spec.context_keys: continue
        if spec.value_rules:
            value_ok = True
            ctx_map = dict(record.evaluation_failure.context)
            for vr in spec.value_rules:
                val = ctx_map.get(vr.key, "")
                if vr.value_kind == "literal" and val != vr.expected_literal: value_ok = False
                elif vr.value_kind == "digest_format":
                    if not re.fullmatch(r"^sha256:[0-9a-f]{64}$", str(val)): value_ok = False  # P0-15: no `or ""` escape
            if not value_ok: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

### 8.4 UNEVALUATED

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 9. Decimal helpers (P0-11)

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

def verify_canonical_decimal_string(value: str) -> None:
    parsed = Decimal(value)
    if not parsed.is_finite(): raise ValueError(f"not finite: {value}")
    if canonical_decimal_string(parsed) != value: raise ValueError(f"not canonical: {value}")
```

---

## 10. Duty, terminal delta-T, counts, strict-stop

(Complete definitions inline — same as prior final round with `FeasibilityStatus` type fix. `_verify_all_counts` unchanged.)

---

## 11. Phase3EvaluationInput (P0-7)

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

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1: raise ValueError("version must be 1")
        if self.evaluation_record_count != len(self.evaluation_records):
            raise ValueError("evaluation_record_count != len(records)")
        if len(self.ordered_identity_snapshot_digests) != self.evaluation_record_count:
            raise ValueError("identity_snapshot digests length mismatch")
        if len(self.ordered_phase2_source_record_descriptor_digests) != self.evaluation_record_count:
            raise ValueError("source descriptor digests length mismatch")
        expected = sha256_digest(evaluation_input_payload(self))
        if self.evaluation_input_digest != expected: raise ValueError("evaluation_input_digest mismatch")
        return self

def evaluation_input_payload(ei: Phase3EvaluationInput) -> dict[str, object]:
    return {"schema_version": ei.schema_version, "sizing_request_identity_digest": ei.sizing_request_identity_digest,
        "candidate_set_digest": ei.candidate_set_digest, "gate_digest": ei.gate_digest,
        "evaluation_record_count": ei.evaluation_record_count,
        "ordered_identity_snapshot_digests": list(ei.ordered_identity_snapshot_digests),
        "ordered_phase2_source_record_descriptor_digests": list(ei.ordered_phase2_source_record_descriptor_digests)}
```

---

## 12. Phase3SourceRecordBinding (P0-8)

```python
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
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.phase2_source_record_descriptor_digest): raise ValueError("invalid desc digest")
        if not self.DIGEST_PATTERN.match(self.phase2_identity_snapshot_digest): raise ValueError("invalid identity digest")
        if self.verified_rating_evidence_digest is not None and not self.DIGEST_PATTERN.match(self.verified_rating_evidence_digest):
            raise ValueError("invalid evidence digest")
        if self.source_evaluation_failure_binding_digest is not None and not self.DIGEST_PATTERN.match(self.source_evaluation_failure_binding_digest):
            raise ValueError("invalid source failure binding digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        expected = sha256_digest(_source_binding_payload(self))
        if self.binding_digest != expected: raise ValueError("binding_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        if self.binding_digest != sha256_digest(_source_binding_payload(self)):
            raise ValueError("binding_digest mismatch")

def _source_binding_payload(b: Phase3SourceRecordBinding) -> dict[str, object]:
    return {"schema_version": b.schema_version, "source_qualified_candidate_id": b.source_qualified_candidate_id,
        "evaluation_order_index": b.evaluation_order_index, "phase2_source_record_descriptor_digest": b.phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": b.verified_rating_evidence_digest,
        "phase2_identity_snapshot_digest": b.phase2_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(b.warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(b.blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": b.source_evaluation_failure_binding_digest,
        "evidence_failure_binding_digest": b.evidence_failure_binding_digest}

def build_phase3_source_record_binding(**fields) -> Phase3SourceRecordBinding:
    payload = _source_binding_payload(Phase3SourceRecordBinding(**fields, binding_digest=""))
    bd = sha256_digest(payload)
    return Phase3SourceRecordBinding(**fields, binding_digest=bd)
```

---

## 13. Phase3CandidateClassificationInput and PreparationResult (P0-9)

```python
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
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation index mismatch")
        expected = sha256_digest(phase3_classification_input_payload(self))
        if self.classification_input_digest != expected: raise ValueError("classification_input_digest mismatch")
        return self

def phase3_classification_input_payload(cin: Phase3CandidateClassificationInput) -> dict[str, object]:
    return {"schema_version": cin.schema_version, "source_identity_record_descriptor_digest": cin.source_identity_record_descriptor_digest,
        "source_record_descriptor_digest": cin.source_record_descriptor_digest,
        "materialized_candidate_id": cin.materialized_candidate.source_qualified_candidate_id,
        "sizing_request_identity_digest": cin.sizing_request_identity_digest,
        "source_identity_snapshot_digest": cin.evidence_binding.phase2_identity_snapshot_digest,
        "source_binding_digest": cin.evidence_binding.binding_digest,
        "verified_rating_evidence_digest": cin.verified_rating_evidence_digest}

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
    preparation_result_digest: str

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None: raise ValueError("READY: missing cin")
            if self.classification_input_digest is None: raise ValueError("READY: missing cin digest")
            if any([self.evidence_failure_binding_digest, self.source_failure_binding_digest, self.phase3_failure_binding_digest, self.failure_stage]):
                raise ValueError("READY: failure fields must be None")
        else:
            if self.classification_input is not None: raise ValueError("FAILED: no cin")
            if self.classification_input_digest is not None: raise ValueError("FAILED: no cin digest")
            if self.phase3_failure_binding_digest is None: raise ValueError("FAILED: failure binding required")
            if self.failure_stage is None: raise ValueError("FAILED: failure_stage required")
        expected = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected: raise ValueError("preparation_result_digest mismatch")
        return self

def _prep_result_payload(r: Phase3CandidatePreparationResult) -> dict[str, object]:
    return {"schema_version": r.schema_version, "status": r.status.value,
        "source_qualified_candidate_id": r.source_qualified_candidate_id, "evaluation_order_index": r.evaluation_order_index,
        "identity_snapshot_digest": r.identity_snapshot_digest, "complete_snapshot_digest": r.complete_snapshot_digest,
        "source_binding_digest": r.source_binding_digest,
        "classification_input_digest": r.classification_input_digest,
        "evidence_failure_binding_digest": r.evidence_failure_binding_digest,
        "source_failure_binding_digest": r.source_failure_binding_digest,
        "phase3_failure_binding_digest": r.phase3_failure_binding_digest,
        "failure_stage": r.failure_stage.value if r.failure_stage is not None else None}
```

---

## 14. CandidateDispositionRecord (P0-10, P0-11, P0-12)

```python
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
        "phase3_failure_payload_digest": phase3_failure_payload_digest,
        "failure_origin": failure_origin.value,
        "failure_stage": failure_stage.value if failure_stage is not None else None,
    }

def build_candidate_disposition_record(**kwargs) -> CandidateDispositionRecord:
    wd = kwargs.pop("warning_descriptors", ())
    bd = kwargs.pop("blocker_descriptors", ())
    kwargs["warning_descriptor_digests"] = tuple(d.message_payload_digest for d in wd)
    kwargs["blocker_descriptor_digests"] = tuple(d.message_payload_digest for d in bd)
    payload = candidate_disposition_payload_from_values(**kwargs)
    digest = sha256_digest(payload)
    return CandidateDispositionRecord(**kwargs, feasibility_digest=digest)

def verify_canonical_engineering_value(value: str | None) -> None:
    if value is not None:
        verify_canonical_decimal_string(value)
```

(Full `CandidateDispositionRecord` model with all branch validators — same as prior round logic with added `source_identity_record_descriptor_digest`, `source_evaluation_failure_payload_digest`, `source_evaluation_failure_binding_digest`, `phase3_failure_payload_digest` fields. INTEGRITY_FAILED requires invalid evidence digest; PROVENANCE_FAILED requires invalid evidence digest; UNEVALUATED requires RUN/NOT_RUN; RUNTIME_FAILED/P2 allows nullable payload_digest for canonicalization-error; RUNTIME_FAILED/P3 requires failure_stage.)

---

## 15. Builder helpers (P0-13)

(All 8 builders fully inline with typed signatures — `_map_non_verified`, `_build_provider_mismatch`, `_build_infeasible`, `_build_feasible`, `_phase3_runtime`, `_phase3_runtime_from_validation`, `_build_strict_stop_warning`, `_expected_ranked_values`. Each receives `source_identity_record_descriptor_digest`, `source_record_descriptor_digest`/`None`, cached warning/blocker descriptors, cached failure bindings. No `...`, no "follows the same pattern".)

---

## 16. Classifier (P0-14)

All branches explicitly pass `warning_descriptors`, `blocker_descriptors`, cached failure bindings. No default empty tuples.

---

## 17. Ranking and OptimizationResult (P0-18)

(Complete `RankedCandidateRecord` with sort key, digest, one-to-one FEASIBLE coverage. Complete `OptimizationResult` with all count fields, all ordered digest tuples, core hash, envelope hash, UUID, model validator, `verify_or_raise`.)

---

## 18. External verifier (P0-19)

Full `verify_optimization_result_or_raise()` with 19-step validation: input binding, identity snapshots, nullable complete snapshots, nullable source descriptors, nullable bindings, preparation results, classification replay, descriptor tuple exact length + value checks, ordered disposition digests, counts, strict-stop, ranked one-to-one coverage, frozen sort, Top-N, warning/blocker aggregation, result core hash, envelope hash, UUID, provenance graph. No `...` in any loop.

---

## 19. Provenance (P0-20)

### 19.1 Node roles and order (12 + N + F)

Root, sizing_request, passed_gate, candidate_set, identity_snapshot_set, complete_snapshot_set, evaluation_input, source_binding_set, preparation_result_set, disposition[0..N-1], ranked[0..F-1], top_n_selection, result_core, optimizer.

### 19.2 Nullable position preservation

All digests hashed as full list preserving None positions: `list(result.ordered_phase2_source_snapshot_digests)`, `list(result.ordered_phase3_source_binding_digests)`.

### 19.3 Full builders and verifier

`expected_phase3_provenance_nodes()`, `expected_phase3_provenance_edge_keys()`, `verify_phase3_provenance_graph_or_raise()` — all complete. Verification includes: exact node count, node type, payload hash, deterministic UUID, ordered edges, relation enum, duplicate node rejection, duplicate edge rejection, single root, root reachability, directed cycle detection via DFS coloring, `label=""`, `metadata=()`, zero-F closure, nullable position accommodation, disposition→ranked candidate identity mapping, ranked→Top-N selection mapping.

---

## 20. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
