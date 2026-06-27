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

## 2. Frozen enums and error codes (P0-13)

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

# New ErrorCode string values (added to existing ErrorCode)
# PHASE3_MISSING_RATING_STATUS = "phase3_missing_rating_status"
# PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
# PHASE3_STRICT_STOP = "phase3_strict_stop"
# PHASE3_TRUSTED_EVIDENCE_INCOMPLETE = "phase3_trusted_evidence_incomplete"
```

All string values above are stable and frozen. No implementation-time naming changes.

---

## 3. Phase3MessageDescriptor

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

---

## 4. Phase3SourceRecordBinding (P0-2, P0-4)

Evidence digest is computed **once** during preparation. All other Phase 3 code reads from this binding.

```python
class Phase3SourceRecordBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_qualified_candidate_id: str
    evaluation_order_index: int
    source_record_descriptor_digest: str
    verified_rating_evidence_digest: str | None
    warning_descriptors: tuple[Phase3MessageDescriptor, ...]
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...]
    source_evaluation_failure_digest: str | None
    binding_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if self.evaluation_order_index < 0:
            raise ValueError("evaluation_index must be ≥ 0")
        if not self.DIGEST_PATTERN.match(self.source_record_descriptor_digest):
            raise ValueError("invalid source_record_descriptor_digest")
        if self.verified_rating_evidence_digest is not None and not self.DIGEST_PATTERN.match(self.verified_rating_evidence_digest):
            raise ValueError("invalid evidence digest")
        if self.source_evaluation_failure_digest is not None and not self.DIGEST_PATTERN.match(self.source_evaluation_failure_digest):
            raise ValueError("invalid source failure digest")
        for d in self.warning_descriptors:
            if not self.DIGEST_PATTERN.match(d.message_payload_digest):
                raise ValueError("invalid warning descriptor digest")
        for d in self.blocker_descriptors:
            if not self.DIGEST_PATTERN.match(d.message_payload_digest):
                raise ValueError("invalid blocker descriptor digest")
        expected = sha256_digest(phase3_source_record_binding_payload(self))
        if self.binding_digest != expected:
            raise ValueError("binding_digest mismatch")
        return self

    def verify_digest(self) -> bool:
        return self.binding_digest == sha256_digest(phase3_source_record_binding_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("binding_digest mismatch")

def phase3_source_record_binding_payload(b: Phase3SourceRecordBinding) -> dict[str, object]:
    return {
        "schema_version": b.schema_version,
        "source_qualified_candidate_id": b.source_qualified_candidate_id,
        "evaluation_order_index": b.evaluation_order_index,
        "source_record_descriptor_digest": b.source_record_descriptor_digest,
        "verified_rating_evidence_digest": b.verified_rating_evidence_digest,
        "warning_descriptor_digests": [d.message_payload_digest for d in b.warning_descriptors],
        "blocker_descriptor_digests": [d.message_payload_digest for d in b.blocker_descriptors],
        "source_evaluation_failure_digest": b.source_evaluation_failure_digest,
    }
```

---

## 5. Single-pass descriptor helpers (P0-3)

```python
def build_engineering_message_descriptor(
    message: EngineeringMessage,
) -> Phase3MessageDescriptor | RunFailure:
    try:
        desc = _build_message_descriptor(message)
    except (ContextCanonicalizationError, TypeError, ValueError) as exc:
        return _canonicalization_to_failure(error=exc, ...)
    if desc.canonicalization_error is not None:
        return _descriptor_error_to_failure(descriptor=desc, ...)
    if desc.message_payload_digest is None:
        return RunFailure(code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
                          message="Message descriptor has no payload digest.",
                          traceback=None, context=(("failure_stage", "descriptor"),
                          ("owner_kind", "build"), ("message_index", -1),),)
    # SUCCESS: use cached descriptor fields — never re-read message.context
    return Phase3MessageDescriptor(
        owner_sort_key=desc.owner_sort_key,
        original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest,
    )
```

No `except Exception` — only `ContextCanonicalizationError`, `TypeError`, `ValueError`. After descriptor construction, never access `message.context`, `engineering_message_payload(message)`, or `safe_context_owner_marker(message.context)`.

---

## 6. Phase3EvaluationInput

### 6.1 Model

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
    ordered_evaluation_record_descriptor_digests: tuple[str, ...]
    evaluation_input_digest: str
```

### 6.2 Helpers

```python
def evaluation_record_descriptor_payload(
    record: CandidateEvaluationRecord,
    binding: Phase3SourceRecordBinding,
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
        "candidate_evaluation_identity_digest": (
            record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if record.candidate_evaluation_identity is not None else None
        ),
        "verified_rating_evidence_digest": binding.verified_rating_evidence_digest,
        "invalid_rating_evidence_digest": (
            record.invalid_rating_evidence.invalid_evidence_digest
            if record.invalid_rating_evidence is not None else None
        ),
        "claimed_rating_result_audit_digest": (
            record.claimed_rating_result_audit.audit_digest
            if record.claimed_rating_result_audit is not None else None
        ),
        "evaluation_failure_digest": (
            sha256_digest(run_failure_payload(record.evaluation_failure))
            if record.evaluation_failure is not None else None
        ),
    }

def evaluation_input_payload(input: Phase3EvaluationInput) -> dict[str, object]:
    return {
        "schema_version": input.schema_version,
        "sizing_request_identity_digest": input.sizing_request_identity_digest,
        "candidate_set_digest": input.candidate_set_digest,
        "gate_digest": input.gate_digest,
        "evaluation_record_count": input.evaluation_record_count,
        "ordered_evaluation_record_descriptor_digests": list(input.ordered_evaluation_record_descriptor_digests),
    }
```

### 6.3 13-step verify_or_raise()

Step 1: types. Step 2: `materialization_result.verify_or_raise()`. Step 3: sizing digest. Step 4: `candidate_set.verify_digest()`. Step 5: `sizing_gate.verify_digest()`. Step 6: candidate-set↔sizing. Step 7: gate↔candidate-set. Step 8: count parity. Step 9: one-to-one record↔candidate. Step 10: exhaustive state per §7 matrix. Step 11: strict-stop invariant. Step 12: descriptor digest. Step 13: evaluation_input_digest.

---

## 7. Phase 2 constructor matrix

### 7.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity (VERIFIED only): `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 7.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false | Provenance false |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 7.3 RUNTIME_FAILED — executable path specs (10 paths, P0-8)

```python
@dataclass(frozen=True, slots=True)
class Phase2RuntimeFailurePathSpec:
    path_id: str
    hash_outcome: VerificationOutcome
    provenance_outcome: VerificationOutcome
    audit_required: bool
    failure_code: ErrorCode
    exact_message: str
    context_keys: tuple[str, ...]
    failure_stage: str | None
    owner_kind: str | None

PATH_SPECS = (
    Phase2RuntimeFailurePathSpec("P2-RF-1", NOT_RUN, NOT_RUN, True, ErrorCode.INVALID_STATE_TRANSITION,
        "Expected exact RatingResult", (), "evaluation", "evaluation"),
    Phase2RuntimeFailurePathSpec("P2-RF-2", ERROR, NOT_RUN, True, ErrorCode.HASH_MISMATCH,
        "Rating result hash verification raised.", (), "verification", "verification_runtime"),
    Phase2RuntimeFailurePathSpec("P2-RF-3", PASSED, ERROR, True, ErrorCode.PROVENANCE_INCOMPLETE,
        "Rating result provenance verification raised.", (), "verification", "verification_runtime"),
    Phase2RuntimeFailurePathSpec("P2-RF-4", PASSED, PASSED, True, ErrorCode.INVALID_STATE_TRANSITION,
        "Failed to extract trusted evidence", (), "verification", "verification_runtime"),
    Phase2RuntimeFailurePathSpec("P2-RF-5", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        "Trusted context canonicalization failed.",
        ("failure_stage","owner_kind","owner_id","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime"),
    Phase2RuntimeFailurePathSpec("P2-RF-6", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        "Trusted context canonicalization failed.",
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "warning"),
    Phase2RuntimeFailurePathSpec("P2-RF-7", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        "Trusted context canonicalization failed.",
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "blocker"),
    Phase2RuntimeFailurePathSpec("P2-RF-8", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        "Trusted context canonicalization failed.",
        ("failure_stage","owner_kind","owner_id","original_code","context_key","context_path_digest","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "run_failure"),
    Phase2RuntimeFailurePathSpec("P2-RF-9", PASSED, PASSED, False, ErrorCode.INVALID_STATE_TRANSITION,
        "Failed to build candidate evaluation identity", (), "verification", "verification_runtime"),
    Phase2RuntimeFailurePathSpec("P2-RF-10", PASSED, PASSED, False, ErrorCode.PROVENANCE_INCOMPLETE,
        "Trusted rating verification failed.",
        ("failure_stage","owner_kind","owner_id","offending_type","failure_kind","safe_marker_digest"),
        "rating_verification", "verification_runtime"),
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
        if record.evaluation_failure.message != spec.exact_message: continue
        if spec.context_keys:
            ctx_pairs = record.evaluation_failure.context
            ctx_keys = tuple(p[0] for p in ctx_pairs)
            if ctx_keys != spec.context_keys: continue
        matches.append(spec.path_id)
    if len(matches) == 0: raise ValueError("no matching path")
    if len(matches) > 1: raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

P2-RF-5 through P2-RF-8 are distinguished by `owner_kind` in the failure context (`verification_runtime`, `warning`, `blocker`, `run_failure`) and by the presence of `original_code`. All 10 paths are uniquely identifiable.

### 7.4 UNEVALUATED

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 8. Strict-stop

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. Indices < stop: must be VERIFIED. Index == stop: INTEGRITY_INVALID or RUNTIME_FAILED. Indices > stop: UNEVALUATED. COMPLETE = no strict-stop. PARTIAL = strict-stop.

```python
def _find_stop_index(ei: Phase3EvaluationInput) -> int | None:
    for i, r in enumerate(ei.evaluation_records):
        if r.candidate_evaluation_state in (CandidateEvaluationState.INTEGRITY_INVALID, CandidateEvaluationState.RUNTIME_FAILED):
            return i
    return None
```

---

## 9. Decimal and duty

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

## 10. Count equations

Phase 3 disposition (disjoint): `total = feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated`.

Phase 2 state audit: `phase2_verified + phase2_integrity_invalid + phase2_runtime_failed + phase2_unevaluated = total`.

Cross: `runtime_failed = rf_from_verified + rf_from_rf`; `phase2_verified = feasible + infeasible + provider_mismatch + rf_from_verified`; `phase2_integrity_invalid = integrity_failed + provenance_failed`; `phase2_runtime_failed = rf_from_rf`; `phase2_unevaluated = unevaluated`.

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

## 11. Phase3CandidateClassificationInput (P0-2)

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

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_index mismatch")
        expected_desc = sha256_digest(evaluation_record_descriptor_payload(self.source_record, self.evidence_binding))
        if self.source_record_descriptor_digest != expected_desc:
            raise ValueError("descriptor digest mismatch")
        # Evidence binding candidate identity must match source record
        if self.evidence_binding.source_qualified_candidate_id != self.source_record.source_qualified_candidate_id:
            raise ValueError("binding candidate_id mismatch")
        if self.evidence_binding.evaluation_order_index != self.source_record.evaluation_order_index:
            raise ValueError("binding index mismatch")
        if self.evidence_binding.source_record_descriptor_digest != self.source_record_descriptor_digest:
            raise ValueError("binding source_descriptor mismatch")
        # Do NOT recompute evidence digest here — already cached in binding
        return self
```

No call to `compute_explicit_evidence_digest()` in the validator. The evidence digest is computed exactly once during preparation and stored in the binding.

---

## 12. Preparation lifecycle (P0-6)

```python
class Phase3CandidatePreparationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    status: Phase3PreparationStatus
    classification_input: Phase3CandidateClassificationInput | None = None
    phase3_failure: RunFailure | None = None
    phase3_failure_digest: str | None = None

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.status is Phase3PreparationStatus.READY:
            if self.classification_input is None: raise ValueError("READY requires classification_input")
            if self.phase3_failure is not None: raise ValueError("READY must have no failure")
            if self.phase3_failure_digest is not None: raise ValueError("READY must have no failure digest")
        else:
            if self.classification_input is not None: raise ValueError("FAILED must have no classification_input")
            if self.phase3_failure is None: raise ValueError("FAILED requires failure")
            if self.phase3_failure_digest is None: raise ValueError("FAILED requires failure digest")
        return self

def prepare_phase3_candidate(
    evaluation_input: Phase3EvaluationInput,
    index: int,
) -> Phase3CandidatePreparationResult:
    """Build source binding and classification input."""
    rec = evaluation_input.evaluation_records[index]
    candidate = evaluation_input.materialization_result.candidates[index]
    sizing = evaluation_input.sizing_request_identity
    # Build evidence binding (evidence digest computed ONCE here)
    evidence = rec.verified_rating_evidence
    if evidence is not None:
        evidence_digest = evidence.compute_explicit_evidence_digest()  # ONLY SITE
        w_result = canonicalize_phase3_messages_or_failure(evidence.warnings, "warning",
            rec.source_qualified_candidate_id, index,
            evaluation_input.ordered_evaluation_record_descriptor_digests[index])
        if isinstance(w_result, RunFailure):
            return _preparation_failure(rec, candidate, w_result)
        b_result = canonicalize_phase3_messages_or_failure(evidence.blockers, "blocker",
            rec.source_qualified_candidate_id, index,
            evaluation_input.ordered_evaluation_record_descriptor_digests[index])
        if isinstance(b_result, RunFailure):
            return _preparation_failure(rec, candidate, b_result)
    else:
        evidence_digest = None
        w_result = ()
        b_result = ()
    source_failure_digest = (
        sha256_digest(run_failure_payload(rec.evaluation_failure))
        if rec.evaluation_failure is not None else None
    )
    binding = Phase3SourceRecordBinding(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=index,
        source_record_descriptor_digest=evaluation_input.ordered_evaluation_record_descriptor_digests[index],
        verified_rating_evidence_digest=evidence_digest,
        warning_descriptors=w_result,
        blocker_descriptors=b_result,
        source_evaluation_failure_digest=source_failure_digest,
    )
    cin = Phase3CandidateClassificationInput(
        source_record=rec,
        source_record_descriptor_digest=evaluation_input.ordered_evaluation_record_descriptor_digests[index],
        materialized_candidate=candidate,
        sizing_request_identity=sizing,
        sizing_request_identity_digest=evaluation_input.sizing_request_identity_digest,
        evidence_binding=binding,
    )
    return Phase3CandidatePreparationResult(
        status=Phase3PreparationStatus.READY,
        classification_input=cin,
    )

def disposition_from_preparation_failure(
    source_record: CandidateEvaluationRecord,
    candidate: ManufacturableCandidate,
    failure: RunFailure,
    failure_digest: str,
) -> CandidateDispositionRecord:
    return build_candidate_disposition_record(
        source_qualified_candidate_id=source_record.source_qualified_candidate_id,
        evaluation_order_index=source_record.evaluation_order_index,
        source_candidate_evaluation_state=source_record.candidate_evaluation_state,
        source_hash_verification_outcome=source_record.hash_verification_outcome,
        source_provenance_verification_outcome=source_record.provenance_verification_outcome,
        source_record_descriptor_digest=sha256_digest(evaluation_record_descriptor_payload(source_record, None)),
        disposition=Phase3Disposition.RUNTIME_FAILED,
        diagnostic=FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED,
        provider_identity_matches=source_record.provider_identity_matches,
        rating_status=source_record.rating_status,
        candidate_evaluation_identity_digest=(
            source_record.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if source_record.candidate_evaluation_identity else None
        ),
        verified_rating_evidence_digest=None,  # cannot compute — canonicalization failed
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        warning_descriptors=(),
        blocker_descriptors=(),
        source_evaluation_failure_digest=None,
        phase3_failure_digest=failure_digest,
        failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
    )
```

---

## 13. One-shot disposition factory (P0-1)

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
    }
```

No `**kwargs`, no `object.__setattr__`, no backfill. `build_candidate_disposition_record` has an explicit typed signature.

---

## 14. CandidateDispositionRecord

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
            if self.primary_engineering_value is not None: raise ValueError("INFEASIBLE: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("INFEASIBLE: engineering must be None")
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
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("INTEGRITY_FAILED: origin must be NONE")
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
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("PROVENANCE_FAILED: origin must be NONE")
        # UNEVALUATED
        elif self.disposition is UNEVALUATED:
            if self.source_candidate_evaluation_state != UNEVALUATED: raise ValueError("UNEVALUATED: source must be UNEVALUATED")
            if self.diagnostic != FeasibilityDiagnosticKey.NONE: raise ValueError("UNEVALUATED: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is not None: raise ValueError("UNEVALUATED: identity must be None")
            if self.verified_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: evidence must be None")
            if self.invalid_rating_evidence_digest is not None: raise ValueError("UNEVALUATED: invalid must be None")
            if self.primary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if self.secondary_engineering_value is not None: raise ValueError("UNEVALUATED: engineering must be None")
            if len(self.warning_descriptors) != 0: raise ValueError("UNEVALUATED: warnings empty")
            if len(self.blocker_descriptors) != 0: raise ValueError("UNEVALUATED: blockers empty")
            if self.source_evaluation_failure_digest is not None: raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_digest is not None: raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE: raise ValueError("UNEVALUATED: origin must be NONE")
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
                if self.candidate_evaluation_identity_digest is None: raise ValueError("RF(P3): identity required (retained)")
                if self.verified_rating_evidence_digest is None: raise ValueError("RF(P3): evidence required (retained)")
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

## 15. Classifier (P0-9)

```python
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
        return _phase3_runtime(rec, eb, ErrorCode.PHASE3_MISSING_RATING_STATUS, "No rating status.")
    # 4. BLOCKED/FAILED
    if rec.rating_status == "blocked":
        _validate_blocked_evidence_or_failure(rec, evidence, eb)
        return _build_infeasible(rec, eb, RATING_BLOCKED)
    if rec.rating_status == "failed":
        _validate_failed_evidence_or_failure(rec, evidence, eb)
        return _build_infeasible(rec, eb, RATING_FAILED)
    # 5. SUCCEEDED — evidence matrix
    if evidence is None: return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "No evidence.")
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Missing thermal metrics.")
    if evidence.area_outer_m2 is None or evidence.area_outer_m2 <= 0 or evidence.area_inner_m2 is None or evidence.area_inner_m2 <= 0:
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-positive area.")
    if evidence.failure is not None: return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Has failure.")
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(rec, eb, PHASE3_TRUSTED_EVIDENCE_INCOMPLETE, "Non-finite metric.")
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

def _validate_blocked_evidence_or_failure(rec, evidence, eb):
    if rec.rating_status != "blocked": raise ValueError("not BLOCKED")
    if not eb.blocker_descriptors: raise ValueError("BLOCKED: blockers must be non-empty")
    if evidence and (evidence.area_outer_m2 is None or evidence.area_outer_m2 <= 0):
        raise ValueError("BLOCKED: area must be finite positive")
    if evidence and (evidence.area_inner_m2 is None or evidence.area_inner_m2 <= 0):
        raise ValueError("BLOCKED: inner area must be finite positive")

def _validate_failed_evidence_or_failure(rec, evidence, eb):
    if rec.rating_status != "failed": raise ValueError("not FAILED")
    if evidence and evidence.failure is None:
        raise ValueError("FAILED: failure must be present in evidence")
    if evidence and (evidence.area_outer_m2 is None or evidence.area_outer_m2 <= 0):
        raise ValueError("FAILED: area must be finite positive")
    if evidence and (evidence.area_inner_m2 is None or evidence.area_inner_m2 <= 0):
        raise ValueError("FAILED: inner area must be finite positive")
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

## 17. OptimizationResult

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
    termination_status: TerminationStatus
    ordered_warning_digests: tuple[str, ...]; ordered_blocker_digests: tuple[str, ...]
    result_core_hash: str; provenance_digest: str; result_hash: str
    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1: raise ValueError("version must be 1")
        if self.requested_top_n < 1: raise ValueError("top_n must be ≥ 1")
        for name in ["total","feasible","infeasible","provider_mismatch","integrity_failed","provenance_failed","runtime_failed","unevaluated","phase2_verified","phase2_integrity_invalid","phase2_runtime_failed","phase2_unevaluated","runtime_failed_from_phase2_verified","runtime_failed_from_phase2_runtime_failed"]:
            if getattr(self, name + "_count" if name.startswith("phase2") or name.startswith("runtime_failed") else name + "_candidate_count" if name not in ("total","feasible","infeasible","provider_mismatch","integrity_failed","provenance_failed","runtime_failed","unevaluated") else name + "_count", ...):
                pass
        # Simplified: check all counts individually
        for field in ["total_candidate_count","feasible_candidate_count","infeasible_candidate_count","provider_mismatch_count","integrity_failed_count","provenance_failed_count","runtime_failed_count","unevaluated_count","phase2_verified_record_count","phase2_integrity_invalid_record_count","phase2_runtime_failed_record_count","phase2_unevaluated_record_count","runtime_failed_from_phase2_verified_count","runtime_failed_from_phase2_runtime_failed_count"]:
            if getattr(self, field) < 0: raise ValueError(f"{field} < 0")
        d3 = self.feasible_candidate_count + self.infeasible_candidate_count + self.provider_mismatch_count + self.integrity_failed_count + self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count
        if d3 != self.total_candidate_count: raise ValueError("disposition sum ≠ total")
        p2 = self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count + self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count
        if p2 != self.total_candidate_count: raise ValueError("p2 sum ≠ total")
        if self.runtime_failed_count != self.runtime_failed_from_phase2_verified_count + self.runtime_failed_from_phase2_runtime_failed_count: raise ValueError("rf cross mismatch")
        if self.phase2_verified_record_count != self.feasible_candidate_count + self.infeasible_candidate_count + self.provider_mismatch_count + self.runtime_failed_from_phase2_verified_count: raise ValueError("p2_verified cross mismatch")
        if self.phase2_integrity_invalid_record_count != self.integrity_failed_count + self.provenance_failed_count: raise ValueError("p2_ii cross mismatch")
        if self.phase2_runtime_failed_record_count != self.runtime_failed_from_phase2_runtime_failed_count: raise ValueError("p2_rf cross mismatch")
        if self.phase2_unevaluated_record_count != self.unevaluated_count: raise ValueError("p2_u cross mismatch")
        N, F, TN = self.total_candidate_count, self.feasible_candidate_count, min(self.requested_top_n, self.feasible_candidate_count)
        if len(self.ordered_disposition_record_digests) != N: raise ValueError("disposition length ≠ N")
        if len(self.ordered_ranked_record_digests) != F: raise ValueError("ranked length ≠ F")
        if len(self.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length ≠ min")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix")
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
    return ([d.message_payload_digest for d in all_w], [d.message_payload_digest for d in all_b])
```

---

## 19. External verifier (P0-5, P0-11, P0-12)

```python
def verify_optimization_result_or_raise(result, *, ei, source_bindings, classification_inputs,
                                         dispositions, ranked, graph):
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
    # 3. Verify bindings and dispositions per index
    if len(source_bindings) != N: raise ValueError("source_bindings count mismatch")
    if len(classification_inputs) != N: raise ValueError("classification_inputs count mismatch")
    if len(dispositions) != N: raise ValueError("dispositions count mismatch")
    for i, (rec, cand) in enumerate(zip(ei.evaluation_records, ei.materialization_result.candidates)):
        sb = source_bindings[i]; cin = classification_inputs[i]; dr = dispositions[i]
        # Source binding
        if sb.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] binding candidate_id mismatch")
        if sb.evaluation_order_index != i: raise ValueError(f"[{i}] binding index mismatch")
        if sb.source_record_descriptor_digest != ei.ordered_evaluation_record_descriptor_digests[i]: raise ValueError(f"[{i}] binding descriptor mismatch")
        sb.verify_or_raise()
        # Classification input
        if cin.source_record is not rec: raise ValueError(f"[{i}] cin rec reference mismatch")
        if cin.materialized_candidate is not cand: raise ValueError(f"[{i}] cin candidate reference mismatch")
        if cin.sizing_request_identity is not ei.sizing_request_identity: raise ValueError(f"[{i}] cin sizing ref mismatch")
        if cin.sizing_request_identity_digest != ei.sizing_request_identity_digest: raise ValueError(f"[{i}] cin sizing digest mismatch")
        if cin.evidence_binding is not sb: raise ValueError(f"[{i}] cin binding ref mismatch")
        cin.verify_or_raise()
        # Disposition binding
        if dr.evaluation_order_index != i: raise ValueError(f"[{i}] dr index mismatch")
        if dr.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}] dr candidate_id mismatch")
        if dr.source_candidate_evaluation_state != rec.candidate_evaluation_state: raise ValueError(f"[{i}] dr state mismatch")
        if dr.source_hash_verification_outcome != rec.hash_verification_outcome: raise ValueError(f"[{i}] dr hash mismatch")
        if dr.source_provenance_verification_outcome != rec.provenance_verification_outcome: raise ValueError(f"[{i}] dr provenance mismatch")
        if dr.source_record_descriptor_digest != ei.ordered_evaluation_record_descriptor_digests[i]: raise ValueError(f"[{i}] dr descriptor mismatch")
        if dr.provider_identity_matches != rec.provider_identity_matches: raise ValueError(f"[{i}] dr provider mismatch")
        if dr.rating_status != rec.rating_status: raise ValueError(f"[{i}] dr rating mismatch")
        # Re-classify using cached bindings (no context re-read)
        expected = classify_candidate(cin)
        if candidate_disposition_payload(dr) != candidate_disposition_payload(expected): raise ValueError(f"[{i}] disposition payload mismatch")
        dr.verify_or_raise()
        for d in dr.warning_descriptors: verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors: verify_phase3_message_descriptor_or_raise(d)
    # 4. Ordered disposition digests (P0-11)
    expected_disp_digests = tuple(dr.feasibility_digest for dr in dispositions)
    if result.ordered_disposition_record_digests != expected_disp_digests: raise ValueError("ordered disposition digests mismatch")
    # 5. Counts
    _verify_all_counts(result, ei, dispositions)
    # 6. Ranked records (P0-12)
    if len(ranked) != F: raise ValueError(f"ranked count {len(ranked)} != {F}")
    feasible_disps = [d for d in dispositions if d.disposition is FEASIBLE]
    if len(feasible_disps) != F: raise ValueError("FEASIBLE count != F")
    # Build expected ranked order by frozen sort key
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
    expected_ranked = ranked_keyed  # ordered by sort key
    if len(ranked) != len(expected_ranked): raise ValueError("ranked count mismatch with FEASIBLE count")
    for ri, (_, disp, ci) in enumerate(expected_ranked):
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
    if list(result.ordered_warning_digests) != expected_w: raise ValueError("warning digests mismatch")
    if list(result.ordered_blocker_digests) != expected_b: raise ValueError("blocker digests mismatch")
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
    # 11. Uniqueness + format
    for field in ["sizing_request_identity_digest","passed_gate_digest","candidate_set_digest","evaluation_input_digest","result_core_hash","provenance_digest","result_hash"]:
        if not re.match(r"^sha256:[0-9a-f]{64}$", getattr(result, field)): raise ValueError(f"invalid {field}")
    for lst, name in [(result.ordered_disposition_record_digests, "disposition"),
                       (result.ordered_ranked_record_digests, "ranked"),
                       (result.ordered_top_n_record_digests, "top_n")]:
        if len(set(lst)) != len(lst): raise ValueError(f"{name} digests not unique")
```

---

## 20. Provenance

### 20.1 Namespace and node ID

```python
PHASE3_RESULT_NS = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NS = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

def expected_phase3_node_id(role: str, node_type: ProvenanceNodeType, payload_hash: str) -> UUID:
    return uuid.uuid5(PHASE3_PROVENANCE_NS, f"{role}:{node_type.value}:{payload_hash}")
```

### 20.2 Expected nodes

Fixed set: root (EXTERNAL), sizing_request (INPUT_FILE), passed_gate (CALCULATION_RUN), candidate_set (CALCULATION_RUN), evaluation_input (INTERMEDIATE), N×disposition[N] (INTERMEDIATE), F×ranked[F] (INTERMEDIATE), top_n_selection (INTERMEDIATE), result_core (RESULT), optimizer (OPTIMIZER). Node count = 8 + N + F.

Root payload: `sha256_digest({"artifact_kind": "phase3_evaluation_input", "evaluation_input_digest": ei.evaluation_input_digest})`. Optimizer payload: `sha256_digest({"schema_version":1, "evaluation_input_digest": ei.evaluation_input_digest, "optimization_objective": result.optimization_objective.value, "requested_top_n": result.requested_top_n, "termination_status": result.termination_status.value, "result_core_hash": result.result_core_hash, "phase3_algorithm_version": "task009-phase3-v1"})`.

### 20.3 Edge topology

Root ──regulates──► Sizing Request ──consumed_by──► Passed Sizing Gate ──produced──► Candidate Set ──consumed_by──► Evaluation Input ──evaluated──► each Disposition. FEASIBLE disposition ──ranked──► corresponding Ranked Record. Evaluation Input ──selected_by──► Top-N Selection (always). Selected Ranked Records ──selected──► Top-N Selection. Top-N ──produced──► Result Core ──executed_by──► Optimizer.

Disposition→Ranked binding uses `(candidate_id, feasibility_digest)` key, not sequential index. Only FEASIBLE dispositions connect to ranked nodes. Only selected (first N) ranked records connect to Top-N.

### 20.4 Semantic verifier

`verify_phase3_provenance_graph_or_raise(graph, *, ei, dispositions, ranked, result)`:
- Computes expected nodes, verifies count = 8+N+F, node count in graph matches.
- For each expected node: verifies UUID matches `expected_phase3_node_id(role, type, payload)`, type, payload_hash, label=""`, metadata=()`.
- Rejects extra nodes. Verifies no duplicate expected IDs.
- Computes expected edges via `_build_expected_edge_keys`, compares to actual edges (sorted tuple).
- Rejects duplicate edges. Verifies all edge metadata=()`.
- Reachability: BFS from root ID, must visit all nodes.
- All relation values use `Phase3ProvenanceRelation.RELATION.value` (not bare strings).

### 20.5 Semantic graph verifier

```python
def verify_phase3_provenance_graph_or_raise(graph, *, ei, dispositions, ranked, result):
    from collections import Counter
    expected_nodes = _expected_nodes(ei, dispositions, ranked, result)
    if len(graph.nodes) != len(expected_nodes):
        raise ValueError(f"node count {len(graph.nodes)} != {len(expected_nodes)}")
    expected_ids = {expected_phase3_node_id(*n): n for n in expected_nodes}
    actual_by_id = {n.node_id: n for n in graph.nodes}
    for eid, (role, ntype, phash) in expected_ids.items():
        actual = actual_by_id.get(eid)
        if actual is None: raise ValueError(f"missing node: {role}")
        if actual.node_type != ntype: raise ValueError(f"{role}: type {actual.node_type} != {ntype}")
        if actual.payload_hash != phash: raise ValueError(f"{role}: payload hash mismatch")
        if actual.label != "": raise ValueError(f"{role}: label not empty")
        if actual.metadata != (): raise ValueError(f"{role}: metadata not empty")
    extra = set(actual_by_id) - set(expected_ids)
    if extra: raise ValueError(f"extra nodes: {len(extra)}")
    expected_edges = _expected_edge_keys(ei, dispositions, ranked, result, expected_nodes)
    actual_edges = tuple(sorted((str(e.source_id), str(e.target_id), e.relation) for e in graph.edges))
    if len(actual_edges) != len(set(actual_edges)): raise ValueError("duplicate edges")
    if actual_edges != expected_edges: raise ValueError("edge set mismatch")
    for e in graph.edges:
        if e.metadata != (): raise ValueError("edge metadata not empty")
    root_id = expected_phase3_node_id(*expected_nodes[0])
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

## 21. Factory and builder helpers

All helpers have explicit typed signatures and are fully defined:
- `_map_non_verified(rec)`, `_build_provider_mismatch(rec, evidence, eb)`, `_build_infeasible(rec, eb, diagnostic)`, `_build_feasible(rec, evidence, eb)`, `_phase3_runtime(rec, eb, code, msg)` — each calls `build_candidate_disposition_record(...)` with explicit typed args.
- `_build_strict_stop_warning(ei, stop_index)` — returns `EngineeringMessage` or `None`.
- `expected_ranked_values(disp, candidate, obj)` — returns `(pv, pf, sv, sf)`.
- `_canonicalization_to_failure`, `_descriptor_error_to_failure`, `_enrich_failure_context` — return `RunFailure` with exact context pairs.

---

## 22. Implementation boundary

New files: `phase3_input.py`, `feasibility.py` (preparation + classification), `ranking.py`, `result.py`. Existing modified: `messages.py` (add error codes), `evaluation.py` (export descriptor builder). Untouched: all Phase 1/2 modules, TASK-008, catalog, existing tests.

---

## 23. Test matrix

One-shot factory explicit signature; descriptor→digest internal derivation; evidence digest computed once in preparation only; classification_input validator never recomputes evidence digest; record descriptor helper reads from binding; source binding candidate swap/index swap/digest tamper rejected; external verifier consumes all source_bindings; cin evidence_binding identity vs sb rejected; preparation READY/FAILED artifacts; preparation failure → P3 RUNTIME_FAILED; descriptor source binding tamper rejected; P2-RF-5..8 exact one-match (context key order + owner_kind); BLOCKED blockers-empty rejected; BLOCKED exact failure policy; FAILED missing failure rejected; FAILED metric policy; contract self-contained (0 prior-round refs); all invoked helpers defined; ordered disposition digest exact equality; ranked identity/evidence digest exact match; duplicate FEASIBLE ranked rejected; omitted FEASIBLE ranked rejected; independent ranking order recomputation; exact ErrorCode strings; exact provenance relation strings; canonicalization failure exact context order; `schema_version=2` rejected.

---

## 24. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
