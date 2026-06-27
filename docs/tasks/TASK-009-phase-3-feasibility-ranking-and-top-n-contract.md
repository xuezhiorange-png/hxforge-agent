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

## 5. RunFailure descriptor binding

Production `CanonicalizedRunFailureDescriptor` has: `original_code`, `canonical_payload`, `payload_digest`, `canonicalization_error`, `context_path_digest`, `safe_marker_digest`. No `descriptor_digest`. Phase 3 computes its own binding identity from real fields.

```python
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
        if self.payload_digest is not None:
            if not self.DIGEST_PATTERN.match(self.payload_digest): raise ValueError("invalid payload_digest")
            if self.canonicalization_error_digest is not None: raise ValueError("SUCCESS: ce must be None")
            if self.context_path_digest is not None: raise ValueError("SUCCESS: ctx_path must be None")
            if self.safe_marker_digest is not None: raise ValueError("SUCCESS: safe_marker must be None")
        elif self.canonicalization_error_digest is not None:
            if self.payload_digest is not None: raise ValueError("FAILED: payload must be None")
            if not self.DIGEST_PATTERN.match(self.canonicalization_error_digest): raise ValueError("invalid ce_digest")
            if self.context_path_digest is None or not self.DIGEST_PATTERN.match(self.context_path_digest): raise ValueError("invalid ctx_path")
            if self.safe_marker_digest is None or not self.DIGEST_PATTERN.match(self.safe_marker_digest): raise ValueError("invalid safe_marker")
        else:
            raise ValueError("must be SUCCESS or CANONICALIZATION_FAILED")
        payload = {"original_code": self.original_code, "payload_digest": self.payload_digest,
            "canonicalization_error_digest": self.canonicalization_error_digest,
            "context_path_digest": self.context_path_digest, "safe_marker_digest": self.safe_marker_digest}
        if self.descriptor_binding_digest != sha256_digest(payload): raise ValueError("descriptor_binding_digest mismatch")
        return self

def build_phase3_run_failure_descriptor_binding(descriptor: CanonicalizedRunFailureDescriptor) -> Phase3RunFailureDescriptorBinding:
    ce = descriptor.canonicalization_error
    ce_digest = sha256_digest({"failure_kind": ce.failure_kind.value, "context_key": ce.context_key,
        "context_path": list(ce.context_path), "offending_type": ce.offending_type, "safe_marker_digest": ce.safe_marker_digest}) if ce is not None else None
    raw = {"original_code": descriptor.original_code,
        "payload_digest": descriptor.payload_digest if ce is None else None,
        "canonicalization_error_digest": ce_digest,
        "context_path_digest": ce.context_path_digest if ce is not None else None,
        "safe_marker_digest": ce.safe_marker_digest if ce is not None else None}
    bd = sha256_digest(raw)
    return Phase3RunFailureDescriptorBinding(original_code=descriptor.original_code,
        payload_digest=descriptor.payload_digest if ce is None else None,
        canonicalization_error_digest=ce_digest,
        context_path_digest=ce.context_path_digest if ce is not None else None,
        safe_marker_digest=ce.safe_marker_digest if ce is not None else None,
        descriptor_binding_digest=bd)
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

## 7. Phase2SourceRecordSnapshot

### 7.1 Primitive payload helper

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
    return {"schema_version": schema_version, "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index, "candidate_evaluation_state": candidate_evaluation_state.value,
        "feasible": feasible, "feasibility_status": feasibility_status.value,
        "hash_verification_outcome": hash_verification_outcome.value, "provenance_verification_outcome": provenance_verification_outcome.value,
        "provider_identity_matches": provider_identity_matches, "rating_status": rating_status,
        "candidate_evaluation_identity_digest": candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": invalid_rating_evidence_digest,
        "claimed_rating_result_audit_digest": claimed_rating_result_audit_digest,
        "evaluation_failure_digest": evaluation_failure_digest,
        "phase2_source_record_descriptor_digest": phase2_source_record_descriptor_digest,
        "warning_descriptor_binding_digests": list(warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": source_evaluation_failure_binding_digest,
        "evidence_failure_binding_digest": evidence_failure_binding_digest}

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
        for f in ("phase2_source_record_descriptor_digest","snapshot_digest"):
            if not self.DIGEST_PATTERN.match(getattr(self,f)): raise ValueError(f"invalid {f}")
        for v,n in [(self.candidate_evaluation_identity_digest,"identity"),(self.verified_rating_evidence_digest,"evidence"),
                     (self.invalid_rating_evidence_digest,"invalid"),(self.claimed_rating_result_audit_digest,"audit"),
                     (self.evaluation_failure_digest,"failure"),
                     (self.source_evaluation_failure_binding_digest,"source_failure_binding"),
                     (self.evidence_failure_binding_digest,"evidence_failure_binding")]:
            if v is not None and not self.DIGEST_PATTERN.match(v): raise ValueError(f"invalid {n} digest")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding digest")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding digest")
        # Recompute payload directly from primitive fields — no model_dump() (P0-2)
        payload = phase2_source_record_snapshot_payload_from_values(
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
            evidence_failure_binding_digest=self.evidence_failure_binding_digest)
        if self.snapshot_digest != sha256_digest(payload): raise ValueError("snapshot_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        payload = phase2_source_record_snapshot_payload_from_values(
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
            evidence_failure_binding_digest=self.evidence_failure_binding_digest)
        if self.snapshot_digest != sha256_digest(payload): raise ValueError("snapshot_digest mismatch")
```

---

## 8. Phase 2 constructor matrix

### 8.1 VERIFIED

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED. Provider parity: `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 8.2 INTEGRITY_INVALID

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 8.3 RUNTIME_FAILED — executable path specs

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
    Phase2RuntimeFailurePathSpec("P2-RF-1",NOT_RUN,NOT_RUN,True,ErrorCode.INVALID_STATE_TRANSITION,
        ("dynamic_type","Expected exact RatingResult, got "),(),"evaluation","evaluation",()),
    Phase2RuntimeFailurePathSpec("P2-RF-2",ERROR,NOT_RUN,True,ErrorCode.HASH_MISMATCH,
        ("exact","Rating result hash verification raised."),(),"verification","verification_runtime",()),
    Phase2RuntimeFailurePathSpec("P2-RF-3",PASSED,ERROR,True,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Rating result provenance verification raised."),(),"verification","verification_runtime",()),
    Phase2RuntimeFailurePathSpec("P2-RF-4",PASSED,PASSED,True,ErrorCode.INVALID_STATE_TRANSITION,
        ("exact","Failed to extract trusted evidence"),(),"verification","verification_runtime",()),
    Phase2RuntimeFailurePathSpec("P2-RF-5",PASSED,PASSED,False,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification","verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"),ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("context_key","any"),ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"),ContextValueRule("failure_kind","any"),ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-6",PASSED,PASSED,False,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification","warning",
        (ContextValueRule("failure_stage","literal","rating_verification"),ContextValueRule("owner_kind","literal","warning"),
         ContextValueRule("context_key","any"),ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"),ContextValueRule("failure_kind","any"),ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-7",PASSED,PASSED,False,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification","blocker",
        (ContextValueRule("failure_stage","literal","rating_verification"),ContextValueRule("owner_kind","literal","blocker"),
         ContextValueRule("context_key","any"),ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"),ContextValueRule("failure_kind","any"),ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-8",PASSED,PASSED,False,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Trusted context canonicalization failed."),
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification","run_failure",
        (ContextValueRule("failure_stage","literal","rating_verification"),ContextValueRule("owner_kind","literal","run_failure"),
         ContextValueRule("context_key","any"),ContextValueRule("context_path_digest","digest_format"),
         ContextValueRule("offending_type","any"),ContextValueRule("failure_kind","any"),ContextValueRule("safe_marker_digest","digest_format"))),
    Phase2RuntimeFailurePathSpec("P2-RF-9",PASSED,PASSED,False,ErrorCode.INVALID_STATE_TRANSITION,
        ("exact","Failed to build candidate evaluation identity"),(),"verification","verification_runtime",()),
    Phase2RuntimeFailurePathSpec("P2-RF-10",PASSED,PASSED,False,ErrorCode.PROVENANCE_INCOMPLETE,
        ("exact","Trusted rating verification failed."),
        ("failure_stage","owner_kind","owner_id","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification","verification_runtime",
        (ContextValueRule("failure_stage","literal","rating_verification"),ContextValueRule("owner_kind","literal","verification_runtime"),
         ContextValueRule("offending_type","any"),ContextValueRule("failure_kind","any"),ContextValueRule("safe_marker_digest","digest_format"))),
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
            if not suffix: continue
            if not re.match(r'^[A-Za-z_][A-Za-z0-9_.]*$', suffix): continue
        if spec.context_keys:
            ctx_keys = tuple(p[0] for p in record.evaluation_failure.context)
            if ctx_keys != spec.context_keys: continue
        if spec.value_rules:
            value_ok = True
            ctx_map = dict(record.evaluation_failure.context)
            for vr in spec.value_rules:
                val = ctx_map.get(vr.key, "")
                if vr.value_kind == "literal" and val != vr.expected_literal: value_ok = False
                elif vr.value_kind == "digest_format" and not re.fullmatch(r"^sha256:[0-9a-f]{64}$", str(val)): value_ok = False
            if not value_ok: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

### 8.4 UNEVALUATED

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 9. Decimal helpers

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

## 10. Duty, terminal delta-T, strict-stop

```python
# Duty
required = to_canonical_decimal(sizing.required_duty_w)
abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)
rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)
duty_tol = max(abs_tol, rel_tol * abs(required))
duty_satisfied = abs(heat - required) <= duty_tol

# Terminal delta-T
if fa == "parallel":
    dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
else:
    dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
delta_t_satisfied = min(dt1, dt2) >= to_canonical_decimal(sizing.minimum_terminal_delta_t)

def _find_stop_index(ei: Phase3EvaluationInput) -> int | None:
    for i, r in enumerate(ei.evaluation_records):
        if r.candidate_evaluation_state in (INTEGRITY_INVALID, RUNTIME_FAILED):
            return i
    return None
```

---

## 11. Count equations

```python
def _verify_all_counts(result, ei, dispositions):
    recs = ei.evaluation_records
    p2_v = sum(1 for r in recs if r.candidate_evaluation_state == VERIFIED)
    p2_ii = sum(1 for r in recs if r.candidate_evaluation_state == INTEGRITY_INVALID)
    p2_rf = sum(1 for r in recs if r.candidate_evaluation_state == RUNTIME_FAILED)
    p2_u = sum(1 for r in recs if r.candidate_evaluation_state == UNEVALUATED)
    for n,a,e in [("p2_verified",result.phase2_verified_record_count,p2_v),("p2_integrity",result.phase2_integrity_invalid_record_count,p2_ii),
                  ("p2_runtime",result.phase2_runtime_failed_record_count,p2_rf),("p2_unevaluated",result.phase2_unevaluated_record_count,p2_u)]:
        if a != e: raise ValueError(f"{n}: {a} != {e}")
    f = sum(1 for d in dispositions if d.disposition is FEASIBLE)
    inf = sum(1 for d in dispositions if d.disposition is INFEASIBLE)
    pm = sum(1 for d in dispositions if d.disposition is PROVIDER_IDENTITY_MISMATCH)
    intf = sum(1 for d in dispositions if d.disposition is INTEGRITY_FAILED)
    pf = sum(1 for d in dispositions if d.disposition is PROVENANCE_FAILED)
    rf = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED)
    u = sum(1 for d in dispositions if d.disposition is UNEVALUATED)
    for n,a,e in [("feasible",result.feasible_candidate_count,f),("infeasible",result.infeasible_candidate_count,inf),
                  ("provider_mismatch",result.provider_mismatch_count,pm),("integrity_failed",result.integrity_failed_count,intf),
                  ("provenance_failed",result.provenance_failed_count,pf),("runtime_failed",result.runtime_failed_count,rf),
                  ("unevaluated",result.unevaluated_count,u)]:
        if a != e: raise ValueError(f"{n}: {a} != {e}")
    rf_v = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED and d.source_candidate_evaluation_state == VERIFIED)
    rf_rf = sum(1 for d in dispositions if d.disposition is RUNTIME_FAILED and d.source_candidate_evaluation_state == RUNTIME_FAILED)
    if result.runtime_failed_from_phase2_verified_count != rf_v: raise ValueError("rf_from_verified mismatch")
    if result.runtime_failed_from_phase2_runtime_failed_count != rf_rf: raise ValueError("rf_from_rf mismatch")
```

---

## 12. Phase3EvaluationInput

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
        N = self.evaluation_record_count
        if N != len(self.evaluation_records): raise ValueError("count != len(records)")
        if len(self.ordered_identity_snapshot_digests) != N: raise ValueError("identity snapshots length")
        if len(self.ordered_phase2_source_record_descriptor_digests) != N: raise ValueError("source descriptors length")
        expected = sha256_digest(_evaluation_input_payload(self))
        if self.evaluation_input_digest != expected: raise ValueError("evaluation_input_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        m = self.materialization_result
        m.verify_or_raise()
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing digest mismatch")
        if self.candidate_set_digest != m.candidate_set.candidate_set_digest:
            raise ValueError("candidate_set digest mismatch")
        if self.gate_digest != m.sizing_gate.gate_digest:
            raise ValueError("gate digest mismatch")
        N = self.evaluation_record_count
        if len(m.candidates) != N: raise ValueError("candidates count != N")
        for i, (rec, cand) in enumerate(zip(self.evaluation_records, m.candidates)):
            if rec.source_qualified_candidate_id != cand.source_qualified_candidate_id: raise ValueError(f"[{i}] candidate_id mismatch")
            if rec.evaluation_order_index != i: raise ValueError(f"[{i}] index mismatch")
        expected = sha256_digest(_evaluation_input_payload(self))
        if self.evaluation_input_digest != expected: raise ValueError("evaluation_input_digest mismatch")

def _evaluation_input_payload(ei: Phase3EvaluationInput) -> dict[str, object]:
    return {"schema_version": ei.schema_version, "sizing_request_identity_digest": ei.sizing_request_identity_digest,
        "candidate_set_digest": ei.candidate_set_digest, "gate_digest": ei.gate_digest,
        "evaluation_record_count": ei.evaluation_record_count,
        "ordered_identity_snapshot_digests": list(ei.ordered_identity_snapshot_digests),
        "ordered_phase2_source_record_descriptor_digests": list(ei.ordered_phase2_source_record_descriptor_digests)}
```

---

## 13. Phase3SourceRecordBinding (P0-3)

```python
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
    return {"schema_version": schema_version, "source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index, "phase2_source_record_descriptor_digest": phase2_source_record_descriptor_digest,
        "verified_rating_evidence_digest": verified_rating_evidence_digest,
        "phase2_identity_snapshot_digest": phase2_identity_snapshot_digest,
        "warning_descriptor_binding_digests": list(warning_descriptor_binding_digests),
        "blocker_descriptor_binding_digests": list(blocker_descriptor_binding_digests),
        "source_evaluation_failure_binding_digest": source_evaluation_failure_binding_digest,
        "evidence_failure_binding_digest": evidence_failure_binding_digest}

def build_phase3_source_record_binding(**fields) -> Phase3SourceRecordBinding:
    payload = phase3_source_record_binding_payload_from_values(**fields)
    bd = sha256_digest(payload)
    return Phase3SourceRecordBinding(**fields, binding_digest=bd)

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
            raise ValueError("invalid source failure binding")
        for d in self.warning_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid warning binding")
        for d in self.blocker_descriptor_binding_digests:
            if not self.DIGEST_PATTERN.match(d): raise ValueError("invalid blocker binding")
        payload = phase3_source_record_binding_payload_from_values(
            schema_version=self.schema_version, source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest=self.phase2_identity_snapshot_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest)
        if self.binding_digest != sha256_digest(payload): raise ValueError("binding_digest mismatch")
        return self

    def verify_or_raise(self) -> None:
        payload = phase3_source_record_binding_payload_from_values(
            schema_version=self.schema_version, source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            phase2_source_record_descriptor_digest=self.phase2_source_record_descriptor_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            phase2_identity_snapshot_digest=self.phase2_identity_snapshot_digest,
            warning_descriptor_binding_digests=self.warning_descriptor_binding_digests,
            blocker_descriptor_binding_digests=self.blocker_descriptor_binding_digests,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            evidence_failure_binding_digest=self.evidence_failure_binding_digest)
        if self.binding_digest != sha256_digest(payload): raise ValueError("binding_digest mismatch")
```

---

## 14. Phase3CandidateClassificationInput and PreparationResult

### 14.1 ClassificationInput

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
        expected = sha256_digest(_classification_input_payload(self))
        if self.classification_input_digest != expected: raise ValueError("classification_input_digest mismatch")
        return self

def _classification_input_payload(cin: Phase3CandidateClassificationInput) -> dict[str, object]:
    return {"schema_version": cin.schema_version, "source_identity_record_descriptor_digest": cin.source_identity_record_descriptor_digest,
        "source_record_descriptor_digest": cin.source_record_descriptor_digest,
        "materialized_candidate_id": cin.materialized_candidate.source_qualified_candidate_id,
        "sizing_request_identity_digest": cin.sizing_request_identity_digest,
        "identity_snapshot_digest": cin.evidence_binding.phase2_identity_snapshot_digest,
        "source_binding_digest": cin.evidence_binding.binding_digest,
        "verified_rating_evidence_digest": cin.verified_rating_evidence_digest}
```

### 14.2 PreparationResult

```python
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
    phase3_failure_binding: Phase3RunFailureDescriptorBinding | None = None
    preparation_result_digest: str
    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None: raise ValueError("READY: cin required")
            if self.complete_snapshot is None: raise ValueError("READY: complete_snapshot required")
            if self.source_binding is None: raise ValueError("READY: source_binding required")
            if self.identity_snapshot is None: raise ValueError("READY: identity_snapshot required")
            if self.identity_snapshot_digest != self.identity_snapshot.identity_snapshot_digest: raise ValueError("READY: identity digest mismatch")
            if self.complete_snapshot_digest != self.complete_snapshot.snapshot_digest: raise ValueError("READY: snapshot digest mismatch")
            if self.source_binding_digest != self.source_binding.binding_digest: raise ValueError("READY: binding digest mismatch")
            if self.classification_input_digest != self.classification_input.classification_input_digest: raise ValueError("READY: cin digest mismatch")
            if self.evidence_failure_binding_digest is not None: raise ValueError("READY: no evidence failure")
            if self.source_failure_binding_digest is not None: raise ValueError("READY: no source failure")
            if self.phase3_failure_binding_digest is not None: raise ValueError("READY: no phase3 failure")
            if self.failure_stage is not None: raise ValueError("READY: no failure_stage")
        else:
            if self.phase3_failure_binding is None: raise ValueError("FAILED: failure_binding required")
            if self.failure_stage is None: raise ValueError("FAILED: failure_stage required")
            if self.classification_input is not None: raise ValueError("FAILED: no cin")
            self.phase3_failure_binding_digest = self.phase3_failure_binding.descriptor_binding_digest
        expected = sha256_digest(_prep_result_payload(self))
        if self.preparation_result_digest != expected: raise ValueError("preparation_result_digest mismatch")
        return self

def _prep_result_payload(r: Phase3CandidatePreparationResult) -> dict[str, object]:
    return {"schema_version": r.schema_version, "status": r.status.value,
        "source_qualified_candidate_id": r.source_qualified_candidate_id, "evaluation_order_index": r.evaluation_order_index,
        "identity_snapshot_digest": r.identity_snapshot_digest, "complete_snapshot_digest": r.complete_snapshot_digest,
        "source_binding_digest": r.source_binding_digest, "classification_input_digest": r.classification_input_digest,
        "evidence_failure_binding_digest": r.evidence_failure_binding_digest,
        "source_failure_binding_digest": r.source_failure_binding_digest,
        "phase3_failure_binding_digest": r.phase3_failure_binding_digest, "failure_stage": r.failure_stage.value if r.failure_stage is not None else None}
```

---

## 15. CandidateDispositionRecord (P0-6)

### 15.1 Payload helper

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
    return {"source_qualified_candidate_id": source_qualified_candidate_id,
        "evaluation_order_index": evaluation_order_index,
        "source_candidate_evaluation_state": source_candidate_evaluation_state.value,
        "source_hash_verification_outcome": source_hash_verification_outcome.value,
        "source_provenance_verification_outcome": source_provenance_verification_outcome.value,
        "source_record_descriptor_digest": source_record_descriptor_digest,
        "source_identity_record_descriptor_digest": source_identity_record_descriptor_digest,
        "disposition": disposition.value, "diagnostic": diagnostic.value,
        "provider_identity_matches": provider_identity_matches, "rating_status": rating_status,
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
        "failure_stage": failure_stage.value if failure_stage is not None else None}

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
) -> CandidateDispositionRecord:
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
        disposition=disposition, diagnostic=diagnostic,
        provider_identity_matches=provider_identity_matches, rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        primary_engineering_value=primary_engineering_value,
        secondary_engineering_value=secondary_engineering_value,
        warning_descriptor_digests=wdd, blocker_descriptor_digests=bdd,
        source_evaluation_failure_payload_digest=source_evaluation_failure_payload_digest,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        failure_origin=failure_origin, failure_stage=failure_stage)
    digest = sha256_digest(payload)
    return CandidateDispositionRecord(
        source_qualified_candidate_id=source_qualified_candidate_id,
        evaluation_order_index=evaluation_order_index,
        source_candidate_evaluation_state=source_candidate_evaluation_state,
        source_hash_verification_outcome=source_hash_verification_outcome,
        source_provenance_verification_outcome=source_provenance_verification_outcome,
        source_record_descriptor_digest=source_record_descriptor_digest,
        source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
        disposition=disposition, diagnostic=diagnostic,
        provider_identity_matches=provider_identity_matches, rating_status=rating_status,
        candidate_evaluation_identity_digest=candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=verified_rating_evidence_digest,
        invalid_rating_evidence_digest=invalid_rating_evidence_digest,
        primary_engineering_value=primary_engineering_value,
        secondary_engineering_value=secondary_engineering_value,
        warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors,
        source_evaluation_failure_payload_digest=source_evaluation_failure_payload_digest,
        source_evaluation_failure_binding_digest=source_evaluation_failure_binding_digest,
        phase3_failure_payload_digest=phase3_failure_payload_digest,
        failure_origin=failure_origin, failure_stage=failure_stage,
        feasibility_digest=digest)
```

### 15.2 Model

```python
class CandidateDispositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_qualified_candidate_id: str; evaluation_order_index: int
    source_candidate_evaluation_state: CandidateEvaluationState
    source_hash_verification_outcome: VerificationOutcome
    source_provenance_verification_outcome: VerificationOutcome
    source_record_descriptor_digest: str | None
    source_identity_record_descriptor_digest: str
    disposition: Phase3Disposition; diagnostic: FeasibilityDiagnosticKey
    provider_identity_matches: bool; rating_status: str | None
    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    invalid_rating_evidence_digest: str | None
    primary_engineering_value: str | None; secondary_engineering_value: str | None
    warning_descriptors: tuple[Phase3MessageDescriptor, ...]
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...]
    source_evaluation_failure_payload_digest: str | None
    source_evaluation_failure_binding_digest: str | None
    phase3_failure_payload_digest: str | None
    failure_origin: FailureOrigin; failure_stage: Phase3PreparationFailureStage | None = None
    feasibility_digest: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")
    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id required")
        if self.evaluation_order_index < 0: raise ValueError("index must be ≥ 0")
        if not self.source_identity_record_descriptor_digest: raise ValueError("identity descriptor required")
        for d,n in [(self.source_record_descriptor_digest,"source"),(self.feasibility_digest,"feasibility")]:
            if d is not None and not self.DIGEST_PATTERN.match(d): raise ValueError(f"invalid {n} digest")
        for d,n in [(self.candidate_evaluation_identity_digest,"identity"),(self.verified_rating_evidence_digest,"evidence"),
                     (self.invalid_rating_evidence_digest,"invalid"),
                     (self.source_evaluation_failure_payload_digest,"source_failure_payload"),
                     (self.source_evaluation_failure_binding_digest,"source_failure_binding"),
                     (self.phase3_failure_payload_digest,"phase3_failure")]:
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
            verify_canonical_decimal_string(self.primary_engineering_value)
            verify_canonical_decimal_string(self.secondary_engineering_value)
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("FEASIBLE: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("FEASIBLE: phase3 failure must be None")
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
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("PROVIDER_MISMATCH: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("PROVIDER_MISMATCH: phase3 failure must be None")
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
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("INFEASIBLE: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("INFEASIBLE: phase3 failure must be None")
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
            if self.diagnostic != INTEGRITY_FAILED: raise ValueError("INTEGRITY_FAILED: diagnostic mismatch")
            if self.provider_identity_matches: raise ValueError("INTEGRITY_FAILED: provider must be False")
            if self.rating_status is not None: raise ValueError("INTEGRITY_FAILED: rating must be None")
            if self.candidate_evaluation_identity_digest is not None: raise ValueError("INTEGRITY_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None: raise ValueError("INTEGRITY_FAILED: evidence must be None")
            if self.invalid_rating_evidence_digest is None: raise ValueError("INTEGRITY_FAILED: invalid evidence required")
            if self.primary_engineering_value is not None: raise ValueError("INTEGRITY_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("INTEGRITY_FAILED: engineering must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("INTEGRITY_FAILED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("INTEGRITY_FAILED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("INTEGRITY_FAILED: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("INTEGRITY_FAILED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("INTEGRITY_FAILED: origin must be NONE")
        # PROVENANCE_FAILED
        elif self.disposition is PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != INTEGRITY_INVALID: raise ValueError("PROVENANCE_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != PASSED: raise ValueError("PROVENANCE_FAILED: hash must be PASSED")
            if self.source_provenance_verification_outcome != FAILED: raise ValueError("PROVENANCE_FAILED: provenance must be FAILED")
            if self.diagnostic != PROVENANCE_FAILED: raise ValueError("PROVENANCE_FAILED: diagnostic mismatch")
            if self.rating_status is not None: raise ValueError("PROVENANCE_FAILED: rating must be None")
            if self.candidate_evaluation_identity_digest is not None: raise ValueError("PROVENANCE_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None: raise ValueError("PROVENANCE_FAILED: evidence must be None")
            if self.invalid_rating_evidence_digest is None: raise ValueError("PROVENANCE_FAILED: invalid evidence required")
            if self.primary_engineering_value is not None: raise ValueError("PROVENANCE_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("PROVENANCE_FAILED: engineering must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("PROVENANCE_FAILED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("PROVENANCE_FAILED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("PROVENANCE_FAILED: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("PROVENANCE_FAILED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("PROVENANCE_FAILED: origin must be NONE")
        # UNEVALUATED
        elif self.disposition is UNEVALUATED:
            if self.source_candidate_evaluation_state != UNEVALUATED: raise ValueError("UNEVALUATED: source must be UNEVALUATED")
            if self.source_hash_verification_outcome != NOT_RUN: raise ValueError("UNEVALUATED: hash must be NOT_RUN")
            if self.source_provenance_verification_outcome != NOT_RUN: raise ValueError("UNEVALUATED: provenance must be NOT_RUN")
            if self.diagnostic != NONE: raise ValueError("UNEVALUATED: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is not None: raise ValueError("UNEVALUATED: identity must be None")
            if self.verified_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: evidence must be None")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("UNEVALUATED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("UNEVALUATED: blockers empty")
            if self.source_evaluation_failure_payload_digest is not None: raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_payload_digest is not None: raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin != NONE: raise ValueError("UNEVALUATED: origin must be NONE")
        # RUNTIME_FAILED
        elif self.disposition is RUNTIME_FAILED:
            if self.primary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("RUNTIME_FAILED: engineering must be None")
            if self.failure_origin == PHASE2_EVALUATION:
                if self.source_candidate_evaluation_state != RUNTIME_FAILED: raise ValueError("RF(P2): source must be RF")
                if self.diagnostic != PHASE2_RUNTIME_FAILED: raise ValueError("RF(P2): diagnostic must be PHASE2_RUNTIME_FAILED")
                valid = [(NOT_RUN,NOT_RUN),(ERROR,NOT_RUN),(PASSED,ERROR),(PASSED,PASSED)]
                if (self.source_hash_verification_outcome,self.source_provenance_verification_outcome) not in valid:
                    raise ValueError("RF(P2): invalid outcome combo")
                if self.candidate_evaluation_identity_digest is not None: raise ValueError("RF(P2): identity must be None")
                if self.verified_rating_evidence_digest is not None: raise ValueError("RF(P2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None: raise ValueError("RF(P2): invalid must be None")
                if len(self.warning_descriptors) != 0: raise ValueError("RF(P2): warnings empty")
                if len(self.blocker_descriptors) != 0: raise ValueError("RF(P2): blockers empty")
                if self.source_evaluation_failure_binding_digest is None: raise ValueError("RF(P2): failure binding required")
                # payload_digest may be None for canonicalization-error descriptors (P0-17)
            elif self.failure_origin == PHASE3_CLASSIFICATION:
                if self.phase3_failure_payload_digest is None: raise ValueError("RF(P3): phase3 failure required")
                if self.source_evaluation_failure_payload_digest is not None: raise ValueError("RF(P3): source failure must be None")
                if self.source_candidate_evaluation_state != VERIFIED: raise ValueError("RF(P3): source must be VERIFIED")
                if self.source_hash_verification_outcome != PASSED: raise ValueError("RF(P3): hash must be PASSED")
                if self.source_provenance_verification_outcome != PASSED: raise ValueError("RF(P3): provenance must be PASSED")
                if self.diagnostic != PHASE3_RUNTIME_FAILED: raise ValueError("RF(P3): diagnostic must be PHASE3_RUNTIME_FAILED")
                if self.candidate_evaluation_identity_digest is None: raise ValueError("RF(P3): identity required")
                if self.failure_stage is None: raise ValueError("RF(P3): failure_stage required")
                if self.failure_stage in (SOURCE_BINDING, CLASSIFICATION_INPUT):
                    if self.verified_rating_evidence_digest is None: raise ValueError("RF(P3): evidence required for stage")
                else:
                    if self.verified_rating_evidence_digest is not None: raise ValueError("RF(P3): evidence absent for stage")
                if self.invalid_rating_evidence_digest is not None: raise ValueError("RF(P3): invalid must be None")
            else: raise ValueError(f"unexpected failure_origin: {self.failure_origin}")
        else: raise ValueError(f"unknown disposition: {self.disposition}")
        return self

    def verify_or_raise(self) -> None:
        payload = candidate_disposition_payload_from_values(
            source_qualified_candidate_id=self.source_qualified_candidate_id,
            evaluation_order_index=self.evaluation_order_index,
            source_candidate_evaluation_state=self.source_candidate_evaluation_state,
            source_hash_verification_outcome=self.source_hash_verification_outcome,
            source_provenance_verification_outcome=self.source_provenance_verification_outcome,
            source_record_descriptor_digest=self.source_record_descriptor_digest,
            source_identity_record_descriptor_digest=self.source_identity_record_descriptor_digest,
            disposition=self.disposition, diagnostic=self.diagnostic,
            provider_identity_matches=self.provider_identity_matches, rating_status=self.rating_status,
            candidate_evaluation_identity_digest=self.candidate_evaluation_identity_digest,
            verified_rating_evidence_digest=self.verified_rating_evidence_digest,
            invalid_rating_evidence_digest=self.invalid_rating_evidence_digest,
            primary_engineering_value=self.primary_engineering_value,
            secondary_engineering_value=self.secondary_engineering_value,
            warning_descriptor_digests=tuple(d.message_payload_digest for d in self.warning_descriptors),
            blocker_descriptor_digests=tuple(d.message_payload_digest for d in self.blocker_descriptors),
            source_evaluation_failure_payload_digest=self.source_evaluation_failure_payload_digest,
            source_evaluation_failure_binding_digest=self.source_evaluation_failure_binding_digest,
            phase3_failure_payload_digest=self.phase3_failure_payload_digest,
            failure_origin=self.failure_origin, failure_stage=self.failure_stage)
        if self.feasibility_digest != sha256_digest(payload): raise ValueError("feasibility_digest mismatch")
```

---

## 16. Builder helpers (P0-7)

### 16.1 _map_non_verified

```python
def _map_non_verified(
    rec: CandidateEvaluationRecord,
    *,
    source_identity_record_descriptor_digest: str,
    source_record_descriptor_digest: str | None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
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
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=disp, diagnostic=diag,
            provider_identity_matches=rec.provider_identity_matches, rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None, verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=rec.invalid_rating_evidence.invalid_evidence_digest
                if rec.invalid_rating_evidence is not None else None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None, failure_origin=NONE)
    elif rec.candidate_evaluation_state == RUNTIME_FAILED:
        sf_payload = source_failure_binding.payload_digest if source_failure_binding is not None else None
        sf_binding = source_failure_binding.descriptor_binding_digest if source_failure_binding is not None else None
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=RUNTIME_FAILED, diagnostic=PHASE2_RUNTIME_FAILED,
            provider_identity_matches=rec.provider_identity_matches, rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None, verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_payload_digest=sf_payload,
            source_evaluation_failure_binding_digest=sf_binding,
            phase3_failure_payload_digest=None, failure_origin=PHASE2_EVALUATION)
    elif rec.candidate_evaluation_state == UNEVALUATED:
        return build_candidate_disposition_record(
            source_qualified_candidate_id=rec.source_qualified_candidate_id,
            evaluation_order_index=rec.evaluation_order_index,
            source_candidate_evaluation_state=rec.candidate_evaluation_state,
            source_hash_verification_outcome=rec.hash_verification_outcome,
            source_provenance_verification_outcome=rec.provenance_verification_outcome,
            source_record_descriptor_digest=source_record_descriptor_digest,
            source_identity_record_descriptor_digest=source_identity_record_descriptor_digest,
            disposition=UNEVALUATED, diagnostic=NONE,
            provider_identity_matches=rec.provider_identity_matches, rating_status=rec.rating_status,
            candidate_evaluation_identity_digest=None, verified_rating_evidence_digest=None,
            invalid_rating_evidence_digest=None,
            primary_engineering_value=None, secondary_engineering_value=None,
            warning_descriptors=(), blocker_descriptors=(),
            source_evaluation_failure_payload_digest=None,
            source_evaluation_failure_binding_digest=None,
            phase3_failure_payload_digest=None, failure_origin=NONE)
    raise ValueError(f"unexpected state: {rec.candidate_evaluation_state}")
```

### 16.2 _build_provider_mismatch, _build_infeasible, _build_feasible, _phase3_runtime, _phase3_runtime_from_validation, _build_strict_stop_warning, _expected_ranked_values

(Each follows the exact same pattern as 16.1: explicit typed signature, all cached descriptors passed explicitly, no `**kwargs`, no re-read of original context. Each returns `build_candidate_disposition_record(...)` with full typed args.)

---

## 17. Classifier (P0-7)

```python
def classify_candidate(
    input: Phase3CandidateClassificationInput,
    *,
    warning_descriptors: tuple[Phase3MessageDescriptor, ...],
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...],
    evidence_failure_binding: Phase3RunFailureDescriptorBinding | None,
    source_failure_binding: Phase3RunFailureDescriptorBinding | None,
) -> CandidateDispositionRecord:
    rec = input.source_record; sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence; eb = input.evidence_binding
    sid = input.source_identity_record_descriptor_digest
    scd = input.source_record_descriptor_digest
    if rec.candidate_evaluation_state != VERIFIED:
        return _map_non_verified(rec, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, source_failure_binding=source_failure_binding)
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, eb, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if rec.rating_status is None:
        return _phase3_runtime(rec, eb, PHASE3_MISSING_RATING_STATUS, "No rating status.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    if rec.rating_status == "blocked":
        vf = validate_blocked_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_identity_record_descriptor_digest=sid,
                source_record_descriptor_digest=scd)
        return _build_infeasible(rec, eb, RATING_BLOCKED, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if rec.rating_status == "failed":
        vf = validate_failed_evidence(rec, evidence, eb)
        if vf is not None:
            return _phase3_runtime_from_validation(rec, eb, vf, source_identity_record_descriptor_digest=sid,
                source_record_descriptor_digest=scd)
        return _build_infeasible(rec, eb, RATING_FAILED, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    if evidence is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "No evidence.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Missing thermal metrics.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    if evidence.area_outer_m2 is None or not (evidence.area_outer_m2 > 0) or evidence.area_inner_m2 is None or not (evidence.area_inner_m2 > 0):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-positive area.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    if evidence.failure is not None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Has failure.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-finite metric.", None,
            source_identity_record_descriptor_digest=sid, source_record_descriptor_digest=scd)
    required = to_canonical_decimal(sizing.required_duty_w)
    duty_tol = max(to_canonical_decimal(sizing.duty_absolute_tolerance_w),
                   to_canonical_decimal(sizing.duty_relative_tolerance) * abs(required))
    if abs(heat_w - required) > duty_tol:
        return _build_infeasible(rec, eb, DUTY_SHORTFALL, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    fa = sizing.flow_arrangement
    if fa == "parallel":
        dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
    if min(dt1, dt2) < to_canonical_decimal(sizing.minimum_terminal_delta_t):
        return _build_infeasible(rec, eb, TERMINAL_DELTA_T_INADEQUATE, source_identity_record_descriptor_digest=sid,
            source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
    return _build_feasible(rec, evidence, eb, source_identity_record_descriptor_digest=sid,
        source_record_descriptor_digest=scd, warning_descriptors=warning_descriptors, blocker_descriptors=blocker_descriptors)
```

---

## 18. RankedCandidateRecord (P0-9)

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
        verify_canonical_decimal_string(self.primary_objective_value)
        verify_canonical_decimal_string(self.secondary_tie_break_value)
        if self.optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            if self.primary_objective_field != "area_outer_m2": raise ValueError("MIN_OA: primary must be area_outer_m2")
            if self.secondary_tie_break_field != "effective_length_m_canonical": raise ValueError("MIN_OA: secondary must be length")
        else:
            if self.primary_objective_field != "effective_length_m_canonical": raise ValueError("MIN_LEN: primary must be length")
            if self.secondary_tie_break_field != "area_outer_m2": raise ValueError("MIN_LEN: secondary must be area")
        for d,n in [(self.candidate_evaluation_identity_digest,"identity"),(self.verified_rating_evidence_digest,"evidence"),
                     (self.feasibility_digest,"feasibility"),(self.ranked_record_digest,"ranked")]:
            if not self.DIGEST_PATTERN.match(d): raise ValueError(f"invalid {n} digest")
        expected = sha256_digest(ranked_payload(self))
        if self.ranked_record_digest != expected: raise ValueError("ranked_record_digest mismatch")
        return self

def ranked_payload(r: RankedCandidateRecord) -> dict[str, object]:
    return {"rank": r.rank, "source_qualified_candidate_id": r.source_qualified_candidate_id,
        "optimization_objective": r.optimization_objective.value, "primary_objective_value": r.primary_objective_value,
        "primary_objective_field": r.primary_objective_field, "secondary_tie_break_value": r.secondary_tie_break_value,
        "secondary_tie_break_field": r.secondary_tie_break_field,
        "candidate_evaluation_identity_digest": r.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": r.verified_rating_evidence_digest, "feasibility_digest": r.feasibility_digest}
```

Sort keys: `MIN_OA: (canonical_decimal(Decimal(area_m2)), canonical_decimal(Decimal(effective_length_m_canonical)), source_cid)`. `MIN_LEN: (canonical_decimal(Decimal(effective_length_m_canonical)), canonical_decimal(Decimal(area_m2)), source_cid)`.

---

## 19. OptimizationResult (P0-10)

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
    ordered_identity_snapshot_digests: tuple[str, ...]
    ordered_phase2_source_snapshot_digests: tuple[str | None, ...]
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
        for f in ["total_candidate_count","feasible_candidate_count","infeasible_candidate_count",
                   "provider_mismatch_count","integrity_failed_count","provenance_failed_count",
                   "runtime_failed_count","unevaluated_count",
                   "phase2_verified_record_count","phase2_integrity_invalid_record_count",
                   "phase2_runtime_failed_record_count","phase2_unevaluated_record_count",
                   "runtime_failed_from_phase2_verified_count","runtime_failed_from_phase2_runtime_failed_count"]:
            if getattr(self,f) < 0: raise ValueError(f"{f} < 0")
        d3 = self.feasible_candidate_count+self.infeasible_candidate_count+self.provider_mismatch_count+self.integrity_failed_count+self.provenance_failed_count+self.runtime_failed_count+self.unevaluated_count
        if d3 != self.total_candidate_count: raise ValueError("disposition sum ≠ total")
        p2 = self.phase2_verified_record_count+self.phase2_integrity_invalid_record_count+self.phase2_runtime_failed_record_count+self.phase2_unevaluated_record_count
        if p2 != self.total_candidate_count: raise ValueError("p2 sum ≠ total")
        if self.runtime_failed_count != self.runtime_failed_from_phase2_verified_count+self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("rf cross")
        if self.phase2_verified_record_count != self.feasible_candidate_count+self.infeasible_candidate_count+self.provider_mismatch_count+self.runtime_failed_from_phase2_verified_count:
            raise ValueError("p2_v cross")
        if self.phase2_integrity_invalid_record_count != self.integrity_failed_count+self.provenance_failed_count:
            raise ValueError("p2_ii cross")
        if self.phase2_runtime_failed_record_count != self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("p2_rf cross")
        if self.phase2_unevaluated_record_count != self.unevaluated_count: raise ValueError("p2_u cross")
        N,F,TN = self.total_candidate_count, self.feasible_candidate_count, min(self.requested_top_n, self.feasible_candidate_count)
        if len(self.ordered_disposition_record_digests) != N: raise ValueError("disposition length ≠ N")
        if len(self.ordered_ranked_record_digests) != F: raise ValueError("ranked length ≠ F")
        if len(self.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length ≠ min")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix")
        if len(self.ordered_identity_snapshot_digests) != N: raise ValueError("identity snapshots length ≠ N")
        if len(self.ordered_phase2_source_snapshot_digests) != N: raise ValueError("source snapshots length ≠ N")
        if len(self.ordered_phase3_source_binding_digests) != N: raise ValueError("bindings length ≠ N")
        if len(self.ordered_phase3_preparation_result_digests) != N: raise ValueError("prep results length ≠ N")
        if self.result_core_hash != sha256_digest(result_core_payload(self)): raise ValueError("core hash mismatch")
        expected_env = sha256_digest({"result_core_hash": self.result_core_hash, "provenance_digest": self.provenance_digest})
        if self.result_hash != expected_env: raise ValueError("envelope hash mismatch")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, self.result_hash))
        if self.optimization_result_id != expected_id: raise ValueError("UUID mismatch")
        return self

PHASE3_RESULT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

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
        "ordered_identity_snapshot_digests": list(r.ordered_identity_snapshot_digests),
        "ordered_phase2_source_snapshot_digests": list(r.ordered_phase2_source_snapshot_digests),
        "ordered_phase3_source_binding_digests": list(r.ordered_phase3_source_binding_digests),
        "ordered_phase3_preparation_result_digests": list(r.ordered_phase3_preparation_result_digests),
        "termination_status": r.termination_status.value,
        "ordered_warning_digests": list(r.ordered_warning_digests),
        "ordered_blocker_digests": list(r.ordered_blocker_digests)}
```

---

## 20. Warning/blocker aggregation

```python
def verify_phase3_message_descriptor_or_raise(d: Phase3MessageDescriptor) -> None:
    if not d.original_code: raise ValueError("descriptor original_code must be non-empty")
    if not d.DIGEST_PATTERN.match(d.message_payload_digest): raise ValueError("invalid message_payload_digest")
    if len(d.owner_sort_key) != 6: raise ValueError("owner_sort_key length != 6")
    if d.owner_sort_key[1] != d.original_code: raise ValueError("owner_sort_key[1] != original_code")

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
    return (tuple(d.message_payload_digest for d in all_w), tuple(d.message_payload_digest for d in all_b))
```

---

## 21. External verifier (P0-11)

```python
def verify_optimization_result_or_raise(
    result, *, ei,
    identity_snapshots: tuple[Phase2SourceRecordIdentitySnapshot, ...],
    complete_snapshots: tuple[Phase2SourceRecordSnapshot | None, ...],
    source_bindings: tuple[Phase3SourceRecordBinding | None, ...],
    preparation_results: tuple[Phase3CandidatePreparationResult, ...],
    warning_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    blocker_binding_tuples: tuple[tuple[Phase3MessageDescriptorBinding, ...], ...],
    evidence_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    source_failure_bindings: tuple[Phase3RunFailureDescriptorBinding | None, ...],
    dispositions, ranked, graph,
):
    N,F = result.total_candidate_count, result.feasible_candidate_count
    # 1. Input binding
    if result.evaluation_input_digest != ei.evaluation_input_digest: raise ValueError("input digest mismatch")
    if result.sizing_request_identity_digest != ei.sizing_request_identity_digest: raise ValueError("sizing digest mismatch")
    if result.candidate_set_digest != ei.candidate_set_digest: raise ValueError("cset digest mismatch")
    if result.passed_gate_digest != ei.gate_digest: raise ValueError("gate digest mismatch")
    if result.total_candidate_count != ei.evaluation_record_count: raise ValueError("total count mismatch")
    # 2. Objective/Top-N
    if result.optimization_objective != ei.sizing_request_identity.optimization_objective: raise ValueError("objective mismatch")
    if result.requested_top_n != ei.sizing_request_identity.top_n: raise ValueError("top_n mismatch")
    # 3. Length checks
    if len(identity_snapshots) != N: raise ValueError("identity_snapshots count mismatch")
    if len(complete_snapshots) != N: raise ValueError("complete_snapshots count mismatch")
    if len(source_bindings) != N: raise ValueError("source_bindings count mismatch")
    if len(preparation_results) != N: raise ValueError("preparation_results count mismatch")
    if len(dispositions) != N: raise ValueError("dispositions count mismatch")
    if len(warning_binding_tuples) != N: raise ValueError("warning_binding_tuples count mismatch")
    if len(blocker_binding_tuples) != N: raise ValueError("blocker_binding_tuples count mismatch")
    if len(evidence_failure_bindings) != N: raise ValueError("evidence_failure_bindings count mismatch")
    if len(source_failure_bindings) != N: raise ValueError("source_failure_bindings count mismatch")
    # 4-13. Per-index verification
    for i, (rec, cand) in enumerate(zip(ei.evaluation_records, ei.materialization_result.candidates)):
        ids = identity_snapshots[i]; cs = complete_snapshots[i]; sb = source_bindings[i]
        pr = preparation_results[i]; dr = dispositions[i]
        wbt = warning_binding_tuples[i]; bbt = blocker_binding_tuples[i]
        efb = evidence_failure_bindings[i]; sfb = source_failure_bindings[i]
        # Identity snapshot
        if ids.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] ids candidate_id")
        if ids.evaluation_order_index != i: raise ValueError(f"[{i}] ids index")
        if result.ordered_identity_snapshot_digests[i] != ids.identity_snapshot_digest: raise ValueError(f"[{i}] result identity digest")
        # Complete snapshot (nullable)
        if cs is not None:
            verify_phase2_source_record_snapshot_or_raise(cs, source_record=rec, ...)
            if result.ordered_phase2_source_snapshot_digests[i] != cs.snapshot_digest: raise ValueError(f"[{i}] result snapshot digest")
        else:
            if result.ordered_phase2_source_snapshot_digests[i] is not None: raise ValueError(f"[{i}] result snapshot should be None")
        # Source binding (nullable)
        if sb is not None:
            sb.verify_or_raise()
            if result.ordered_phase3_source_binding_digests[i] != sb.binding_digest: raise ValueError(f"[{i}] result binding digest")
        else:
            if result.ordered_phase3_source_binding_digests[i] is not None: raise ValueError(f"[{i}] result binding should be None")
        # Preparation result
        if pr.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] pr candidate_id")
        if pr.evaluation_order_index != i: raise ValueError(f"[{i}] pr index")
        if pr.identity_snapshot_digest != ids.identity_snapshot_digest: raise ValueError(f"[{i}] pr identity digest")
        if result.ordered_phase3_preparation_result_digests[i] != pr.preparation_result_digest: raise ValueError(f"[{i}] result prep digest")
        if pr.status is Phase3PreparationStatus.READY:
            if sb is None: raise ValueError(f"[{i}] READY needs binding")
            if cs is None: raise ValueError(f"[{i}] READY needs snapshot")
            cin = pr.classification_input
            if cin is None: raise ValueError(f"[{i}] READY needs cin")
            verify_phase3_classification_input_or_raise(cin, ...)
            expected = classify_candidate(cin, warning_descriptors=wbt, blocker_descriptors=bbt,
                evidence_failure_binding=efb, source_failure_binding=sfb)
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected): raise ValueError(f"[{i}] disposition mismatch")
        else:
            if pr.phase3_failure_binding is None: raise ValueError(f"[{i}] FAILED needs failure binding")
            expected = disposition_from_preparation_failure(source_record=rec, source_snapshot=cs, ...)
            if candidate_disposition_payload(dr) != candidate_disposition_payload(expected): raise ValueError(f"[{i}] prep-failure mismatch")
        # Descriptor tuple exact length and value
        if len(dr.warning_descriptors) != len(wbt): raise ValueError(f"[{i}] warning count {len(dr.warning_descriptors)} != {len(wbt)}")
        for j,d in enumerate(dr.warning_descriptors):
            b = wbt[j]
            if d.owner_sort_key != b.owner_sort_key: raise ValueError(f"[{i}] warn[{j}] sort_key")
            if d.original_code != b.original_code: raise ValueError(f"[{i}] warn[{j}] code")
            if d.message_payload_digest != b.message_payload_digest: raise ValueError(f"[{i}] warn[{j}] digest")
        if len(dr.blocker_descriptors) != len(bbt): raise ValueError(f"[{i}] blocker count mismatch")
        for j,d in enumerate(dr.blocker_descriptors):
            b = bbt[j]
            if d.owner_sort_key != b.owner_sort_key: raise ValueError(f"[{i}] block[{j}] sort_key")
            if d.original_code != b.original_code: raise ValueError(f"[{i}] block[{j}] code")
            if d.message_payload_digest != b.message_payload_digest: raise ValueError(f"[{i}] block[{j}] digest")
    # 14. Ordered disposition digests
    expected_dd = tuple(dr.feasibility_digest for dr in dispositions)
    if result.ordered_disposition_record_digests != expected_dd: raise ValueError("ordered disposition digests mismatch")
    # 15. Counts
    _verify_all_counts(result, ei, dispositions)
    # 16. Strict-stop
    stop_index = _find_stop_index(ei)
    if stop_index is None:
        if result.termination_status is not COMPLETE: raise ValueError("must be COMPLETE")
    else:
        if result.termination_status is not PARTIAL: raise ValueError("must be PARTIAL")
    # 17. Ranked one-to-one + frozen sort + Top-N
    feasible_disps = [d for d in dispositions if d.disposition is FEASIBLE]
    if len(feasible_disps) != F: raise ValueError("FEASIBLE count != F")
    if len(ranked) != F: raise ValueError("ranked count != F")
    ranked_keyed = []
    for d in feasible_disps:
        ci = d.evaluation_order_index; cand = ei.materialization_result.candidates[ci]
        el = canonical_decimal(Decimal(cand.effective_length_m_canonical))
        a = canonical_decimal(Decimal(d.primary_engineering_value))
        key = (a, el, d.source_qualified_candidate_id) if result.optimization_objective is MINIMUM_OUTER_HEAT_TRANSFER_AREA else (el, a, d.source_qualified_candidate_id)
        ranked_keyed.append((key, d, ci))
    ranked_keyed.sort(key=lambda x: x[0])
    for ri,(_,disp,ci) in enumerate(ranked_keyed):
        rr = ranked[ri]; cand = ei.materialization_result.candidates[ci]
        pv,pf,sv,sf = _expected_ranked_values(disp, cand, result.optimization_objective)
        if rr.rank != ri+1: raise ValueError(f"ranked[{ri}]: rank mismatch")
        if rr.source_qualified_candidate_id != disp.source_qualified_candidate_id: raise ValueError(f"ranked[{ri}]: candidate_id")
        if rr.feasibility_digest != disp.feasibility_digest: raise ValueError(f"ranked[{ri}]: feasibility digest")
        if rr.primary_objective_value != pv or rr.primary_objective_field != pf: raise ValueError(f"ranked[{ri}]: primary")
        if rr.secondary_tie_break_value != sv or rr.secondary_tie_break_field != sf: raise ValueError(f"ranked[{ri}]: secondary")
        rr.verify_or_raise()
        if result.ordered_ranked_record_digests[ri] != rr.ranked_record_digest: raise ValueError(f"ranked[{ri}]: result digest")
    TN = min(result.requested_top_n, F)
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix")
    # 18. Warning/blocker aggregation
    expected_w, expected_b = build_result_message_digest_tuples(ei, dispositions, stop_index)
    if tuple(result.ordered_warning_digests) != expected_w: raise ValueError("warning digests mismatch")
    if tuple(result.ordered_blocker_digests) != expected_b: raise ValueError("blocker digests mismatch")
    # 19. Core hash
    if result.result_core_hash != sha256_digest(result_core_payload(result)): raise ValueError("core hash mismatch")
    # 20. Provenance
    verify_phase3_provenance_graph_or_raise(graph, ei=ei, dispositions=dispositions, ranked=ranked, result=result)
    if result.provenance_digest != graph.compute_hash(): raise ValueError("provenance digest mismatch")
    # 21. Envelope hash + UUID
    expected_env = sha256_digest({"result_core_hash": result.result_core_hash, "provenance_digest": result.provenance_digest})
    if result.result_hash != expected_env: raise ValueError("envelope hash mismatch")
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NS, result.result_hash))
    if result.optimization_result_id != expected_id: raise ValueError("UUID mismatch")
```

---

## 22. Provenance (P0-12)

### 22.1 Constants

```python
PHASE3_PROVENANCE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

@dataclass(frozen=True, slots=True)
class ExpectedPhase3ProvenanceNode:
    role: str; node_type: ProvenanceNodeType; payload_hash: str

def expected_phase3_node_id(role: str, nt: ProvenanceNodeType, ph: str) -> UUID:
    return uuid.uuid5(PHASE3_PROVENANCE_NS, f"{role}:{nt.value}:{ph}")
```

### 22.2 Expected nodes

Roles and order (12 + N + F): root, sizing_request, passed_gate, candidate_set, identity_snapshot_set, complete_snapshot_set, evaluation_input, source_binding_set, preparation_result_set, disposition[0..N-1], ranked[0..F-1], top_n_selection, result_core, optimizer.

```python
def expected_phase3_provenance_nodes(*, ei, dispositions, ranked, result):
    nodes = []
    root_p = sha256_digest({"artifact_kind":"phase3_evaluation_input","evaluation_input_digest":ei.evaluation_input_digest})
    nodes.append(ExpectedPhase3ProvenanceNode("root", EXTERNAL, root_p))
    nodes.append(ExpectedPhase3ProvenanceNode("sizing_request", INPUT_FILE, ei.sizing_request_identity_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("passed_gate", CALCULATION_RUN, ei.gate_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("candidate_set", CALCULATION_RUN, ei.candidate_set_digest))
    is_p = sha256_digest({"ordered_identity_snapshot_digests":list(result.ordered_identity_snapshot_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("identity_snapshot_set", INTERMEDIATE, is_p))
    css_p = sha256_digest({"ordered_complete_snapshot_digests":list(result.ordered_phase2_source_snapshot_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("complete_snapshot_set", INTERMEDIATE, css_p))
    nodes.append(ExpectedPhase3ProvenanceNode("evaluation_input", INTERMEDIATE, ei.evaluation_input_digest))
    sb_p = sha256_digest({"ordered_binding_digests":list(result.ordered_phase3_source_binding_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("source_binding_set", INTERMEDIATE, sb_p))
    pr_p = sha256_digest({"ordered_prep_result_digests":list(result.ordered_phase3_preparation_result_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("preparation_result_set", INTERMEDIATE, pr_p))
    for i,d in enumerate(dispositions):
        nodes.append(ExpectedPhase3ProvenanceNode(f"disposition[{i}]", INTERMEDIATE, d.feasibility_digest))
    for i,r in enumerate(ranked):
        nodes.append(ExpectedPhase3ProvenanceNode(f"ranked[{i}]", INTERMEDIATE, r.ranked_record_digest))
    tn_p = sha256_digest({"ordered_top_n_record_digests":list(result.ordered_top_n_record_digests)})
    nodes.append(ExpectedPhase3ProvenanceNode("top_n_selection", INTERMEDIATE, tn_p))
    nodes.append(ExpectedPhase3ProvenanceNode("result_core", RESULT, result.result_core_hash))
    opt_p = sha256_digest({"evaluation_input_digest":ei.evaluation_input_digest,"optimization_objective":result.optimization_objective.value,
        "requested_top_n":result.requested_top_n,"termination_status":result.termination_status.value,
        "result_core_hash":result.result_core_hash,"phase3_algorithm_version":"task009-phase3-v1"})
    nodes.append(ExpectedPhase3ProvenanceNode("optimizer", OPTIMIZER, opt_p))
    return tuple(nodes)
```

### 22.3 Expected edges

```python
def expected_phase3_provenance_edge_keys(*, expected_nodes, dispositions, ranked, result):
    edges = []
    uid_map = {n.role: str(expected_phase3_node_id(n.role,n.node_type,n.payload_hash)) for n in expected_nodes}
    def uid(r): return uid_map[r]
    edges.append((uid("root"),uid("sizing_request"),Phase3ProvenanceRelation.REGULATES.value))
    edges.append((uid("sizing_request"),uid("passed_gate"),Phase3ProvenanceRelation.CONSUMED_BY.value))
    edges.append((uid("passed_gate"),uid("candidate_set"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("candidate_set"),uid("identity_snapshot_set"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("identity_snapshot_set"),uid("complete_snapshot_set"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("complete_snapshot_set"),uid("evaluation_input"),Phase3ProvenanceRelation.CONSUMED_BY.value))
    edges.append((uid("evaluation_input"),uid("source_binding_set"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("source_binding_set"),uid("preparation_result_set"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("preparation_result_set"),uid("evaluation_input"),Phase3ProvenanceRelation.CONSUMED_BY.value))
    for i,_ in enumerate(dispositions):
        edges.append((uid("evaluation_input"),uid(f"disposition[{i}]"),Phase3ProvenanceRelation.EVALUATED.value))
    feasible_mask = {(d.source_qualified_candidate_id,d.feasibility_digest):i for i,d in enumerate(dispositions) if d.disposition is FEASIBLE}
    for ri,r in enumerate(ranked):
        key = (r.source_qualified_candidate_id,r.feasibility_digest)
        di = feasible_mask.get(key)
        if di is None: raise ValueError(f"ranked[{ri}]: no matching FEASIBLE disposition")
        edges.append((uid(f"disposition[{di}]"),uid(f"ranked[{ri}]"),Phase3ProvenanceRelation.RANKED.value))
    edges.append((uid("evaluation_input"),uid("top_n_selection"),Phase3ProvenanceRelation.SELECTED_BY.value))
    for ri in range(min(result.requested_top_n,len(ranked))):
        edges.append((uid(f"ranked[{ri}]"),uid("top_n_selection"),Phase3ProvenanceRelation.SELECTED.value))
    edges.append((uid("top_n_selection"),uid("result_core"),Phase3ProvenanceRelation.PRODUCED.value))
    edges.append((uid("result_core"),uid("optimizer"),Phase3ProvenanceRelation.EXECUTED_BY.value))
    return tuple(sorted(edges))
```

### 22.4 Semantic verifier

```python
def verify_phase3_provenance_graph_or_raise(graph, *, ei, dispositions, ranked, result):
    expected_nodes = expected_phase3_provenance_nodes(ei=ei,dispositions=dispositions,ranked=ranked,result=result)
    expected_count = 12 + len(dispositions) + len(ranked)
    if len(expected_nodes) != expected_count: raise ValueError(f"expected node count {len(expected_nodes)} != {expected_count}")
    if len(graph.nodes) != expected_count: raise ValueError(f"graph node count {len(graph.nodes)} != {expected_count}")
    expected_ids = {}
    for n in expected_nodes:
        eid = expected_phase3_node_id(n.role,n.node_type,n.payload_hash)
        if eid in expected_ids: raise ValueError(f"duplicate expected ID for role {n.role}")
        expected_ids[eid] = n
    actual_by_id = {}
    for n in graph.nodes:
        aid = n.node_id
        if aid in actual_by_id: raise ValueError(f"duplicate actual node ID")
        actual_by_id[aid] = n
    for eid,exp in expected_ids.items():
        actual = actual_by_id.get(eid)
        if actual is None: raise ValueError(f"missing node: {exp.role}")
        if actual.node_type != exp.node_type: raise ValueError(f"{exp.role}: type mismatch")
        if actual.payload_hash != exp.payload_hash: raise ValueError(f"{exp.role}: payload hash mismatch")
        if actual.label != "": raise ValueError(f"{exp.role}: label not empty")
        if actual.metadata != (): raise ValueError(f"{exp.role}: metadata not empty")
    extra = set(actual_by_id) - set(expected_ids)
    if extra: raise ValueError(f"extra nodes: {len(extra)}")
    expected_edges = expected_phase3_provenance_edge_keys(expected_nodes=expected_nodes,dispositions=dispositions,ranked=ranked,result=result)
    actual_edges = tuple(sorted((str(e.source_id),str(e.target_id),e.relation) for e in graph.edges))
    if len(actual_edges) != len(set(actual_edges)): raise ValueError("duplicate edges")
    if actual_edges != expected_edges: raise ValueError("edge set mismatch")
    for e in graph.edges:
        if e.metadata != (): raise ValueError("edge metadata not empty")
    root_id = expected_phase3_node_id(expected_nodes[0].role,expected_nodes[0].node_type,expected_nodes[0].payload_hash)
    children = {n.node_id:[] for n in graph.nodes}
    for e in graph.edges: children[e.source_id].append(e.target_id)
    visited,queue = set(),[root_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited: continue
        visited.add(nid); queue.extend(children.get(nid,[]))
    if len(visited) != len(graph.nodes): raise ValueError("unreachable nodes")
    # Cycle detection: DFS coloring
    WHITE,GRAY,BLACK = 0,1,2
    color = {n.node_id:WHITE for n in graph.nodes}
    def dfs(u):
        color[u] = GRAY
        for v in children.get(u,[]):
            if color.get(v) == GRAY: return True
            if color.get(v) == WHITE and dfs(v): return True
        color[u] = BLACK
        return False
    for nid in list(color):
        if color[nid] == WHITE and dfs(nid): raise ValueError("cycle detected")
```

---

## 23. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
