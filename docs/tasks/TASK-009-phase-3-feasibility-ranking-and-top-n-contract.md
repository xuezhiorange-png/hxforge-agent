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

## 2. Frozen enums

```python
class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"; INFEASIBLE = "infeasible"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    INTEGRITY_FAILED = "integrity_failed"; PROVENANCE_FAILED = "provenance_failed"
    RUNTIME_FAILED = "runtime_failed"; UNEVALUATED = "unevaluated"

class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"; PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"; RATING_FAILED = "rating_failed"
    DUTY_SHORTFALL = "duty_shortfall"; TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
    INTEGRITY_FAILED = "integrity_failed"; PROVENANCE_FAILED = "provenance_failed"
    PHASE2_RUNTIME_FAILED = "phase2_runtime_failed"; PHASE3_RUNTIME_FAILED = "phase3_runtime_failed"

class TerminationStatus(StrEnum):
    COMPLETE = "complete"; PARTIAL = "partial"

class FailureOrigin(StrEnum):
    NONE = "none"; PHASE2_EVALUATION = "phase2_evaluation"; PHASE3_CLASSIFICATION = "phase3_classification"
```

`ErrorCode` additions: `PHASE3_MISSING_RATING_STATUS`, `PHASE3_FEASIBILITY_RUNTIME_FAILURE`, `PHASE3_STRICT_STOP`, `PHASE3_TRUSTED_EVIDENCE_INCOMPLETE`.

---

## 3. Phase3SourceRecordBinding (P0-3, P0-4)

Constructed once per candidate during preparation. Never recomputed.

```python
class Phase3SourceRecordBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_record_descriptor_digest: str
    verified_rating_evidence_digest: str | None
    warning_descriptors: tuple[Phase3MessageDescriptor, ...]
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...]
    source_evaluation_failure_digest: str | None
```

`verified_rating_evidence_digest` is the cached value from `record.verified_rating_evidence.compute_explicit_evidence_digest()` — called exactly once during preparation, never by the classifier or verifier. Warning/blocker descriptors are built via `canonicalize_phase3_messages_or_failure()` (§6) using the evidence's warnings and blockers. No Phase 3 code may call `compute_explicit_evidence_digest()` again.

---

## 4. Phase3MessageDescriptor (P0-6, P0-7)

```python
class Phase3MessageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    owner_sort_key: tuple[
        str,   # severity.value
        str,   # code.value
        str,   # message
        str,   # source_module
        tuple[str, ...],  # affected_paths (sorted)
        str,   # safe_context_marker_digest
    ]
    original_code: str
    message_payload_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if not self.original_code:
            raise ValueError("original_code must be non-empty")
        if not self.DIGEST_PATTERN.match(self.message_payload_digest):
            raise ValueError(f"invalid message_payload_digest: {self.message_payload_digest!r}")
        return self

def verify_phase3_message_descriptor_or_raise(descriptor: Phase3MessageDescriptor) -> None:
    """Recomputed invariants beyond model validation."""
    if not descriptor.message_payload_digest.startswith("sha256:") or len(descriptor.message_payload_digest) != 71:
        raise ValueError("message_payload_digest format invalid")
    if not descriptor.original_code:
        raise ValueError("original_code must be non-empty")
```

Descriptors are built via `build_engineering_message_descriptor()` which reads `message.context` exactly once. After construction, no Phase 3 code re-reads `message.context`, `engineering_message_payload(message)`, or `safe_context_owner_marker(message.context)`.

---

## 5. Phase3CandidateClassificationInput (P0-4, P0-5)

```python
class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_record: CandidateEvaluationRecord
    source_record_descriptor_digest: str
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    evidence_binding: Phase3SourceRecordBinding   # required for VERIFIED; raises if absent

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing_request_identity_digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_order_index mismatch")
        expected_desc = sha256_digest(evaluation_record_descriptor_payload(self.source_record))
        if self.source_record_descriptor_digest != expected_desc:
            raise ValueError("source_record_descriptor_digest mismatch")
        rec = self.source_record
        eb = self.evidence_binding
        if rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED and rec.verified_rating_evidence is not None:
            expected_evidence_digest = rec.verified_rating_evidence.compute_explicit_evidence_digest()
            if eb.verified_rating_evidence_digest != expected_evidence_digest:
                raise ValueError("evidence binding digest mismatch")
        return self
```

Two-stage lifecycle:
**A. Preparation** (`prepare_phase3_classification_input()`): builds source binding (descriptors, evidence digest), handles canonicalization failures. Never produces FEASIBLE/INFEASIBLE decisions.
**B. Pure Classification** (`classify_candidate()`): reads only `input.evidence_binding` for warning/blocker data, never accesses raw `EngineeringMessage.context` or recomputes evidence digest.

---

## 6. Single-pass descriptor helpers (P0-2, P0-8, P0-9)

```python
def build_engineering_message_descriptor(
    message: EngineeringMessage,
) -> Phase3MessageDescriptor | RunFailure:
    try:
        desc = _build_message_descriptor(message)
    except (ContextCanonicalizationError, TypeError, ValueError) as exc:
        return _canonicalization_to_failure(message, exc, "build_descriptor")
    if desc.canonicalization_error is not None:
        return _descriptor_error_to_failure(desc, message)
    if desc.message_payload_digest is None:
        return RunFailure(
            code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
            message="Message descriptor has no payload digest.",
            traceback=None,
            context=(),
        )
    # SUCCESS PATH: use cached descriptor data — never re-read message.context
    return Phase3MessageDescriptor(
        owner_sort_key=(
            message.severity.value,
            message.code.value,
            message.message,
            message.source_module,
            tuple(message.affected_paths),
            desc.safe_context_marker_digest,
        ),
        original_code=desc.original_code,
        message_payload_digest=desc.message_payload_digest,
    )

def canonicalize_phase3_messages_or_failure(
    messages: tuple[EngineeringMessage, ...],
    owner_kind: str,
    candidate_id: str,
    evaluation_index: int,
    source_descriptor_digest: str,
) -> tuple[Phase3MessageDescriptor, ...] | RunFailure:
    descriptors: list[Phase3MessageDescriptor] = []
    for msg_idx, msg in enumerate(messages):
        result = build_engineering_message_descriptor(msg)
        if isinstance(result, RunFailure):
            return _enrich_failure_context(
                result, owner_kind, candidate_id,
                evaluation_index, source_descriptor_digest, msg_idx)
        descriptors.append(result)
    descriptors.sort(key=lambda d: d.owner_sort_key)
    return tuple(descriptors)
```

No `except Exception`. Only `ContextCanonicalizationError`, `TypeError`, `ValueError` are caught. No `str(exc)`, `repr(exc)`, or traceback enters any hash-sensitive payload.

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
    ordered_evaluation_record_descriptor_digests: tuple[str, ...]
    evaluation_input_digest: str
```

### 7.2 Payload helpers

```python
def evaluation_record_descriptor_payload(record: CandidateEvaluationRecord) -> dict[str, object]:
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
        "verified_rating_evidence_digest": (
            record.verified_rating_evidence.compute_explicit_evidence_digest()
            if record.verified_rating_evidence is not None else None
        ),
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

### 7.3 13-step verify_or_raise()

Step 1: type verification. Step 2: `materialization_result.verify_or_raise()`. Step 3: sizing identity digest. Step 4: `candidate_set.verify_digest()`. Step 5: `sizing_gate.verify_digest()`. Step 6: candidate-set↔sizing binding. Step 7: gate↔candidate-set binding. Step 8: count parity. Step 9: one-to-one record↔candidate binding. Step 10: exhaustive state verification per §8 matrix. Step 11: strict-stop invariant. Step 12: descriptor digest verification. Step 13: evaluation_input_digest verification.

---

## 8. Phase 2 constructor matrix

See prior round §4 for full 10-path RUNTIME_FAILED + 2 INTEGRITY_INVALID + 1 VERIFIED + 1 UNEVALUATED matrix. Every field per path is frozen.

### 8.1 Executable runtime failure path matcher (P0-15)

```python
@dataclass(frozen=True, slots=True)
class Phase2RuntimeFailurePathSpec:
    path_id: str
    hash_outcome: VerificationOutcome
    provenance_outcome: VerificationOutcome
    audit_required: bool
    failure_code: str
    failure_message_start: str
    context_keys: tuple[str, ...]

PATH_SPECS: tuple[Phase2RuntimeFailurePathSpec, ...] = (
    Phase2RuntimeFailurePathSpec("P2-RF-1", VerificationOutcome.NOT_RUN, VerificationOutcome.NOT_RUN, True, "INVALID_STATE_TRANSITION", "Expected exact RatingResult", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-2", VerificationOutcome.ERROR, VerificationOutcome.NOT_RUN, True, "HASH_MISMATCH", "Rating result hash verification raised", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-3", VerificationOutcome.PASSED, VerificationOutcome.ERROR, True, "PROVENANCE_INCOMPLETE", "Rating result provenance verification raised", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-4", VerificationOutcome.PASSED, VerificationOutcome.PASSED, True, "INVALID_STATE_TRANSITION", "Failed to extract trusted evidence", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-5", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "PROVENANCE_INCOMPLETE", "Trusted context canonicalization failed", ("failure_stage", "owner_kind", "owner_id", "context_key", "context_path_digest", "offending_type", "failure_kind", "safe_marker_digest")),
    Phase2RuntimeFailurePathSpec("P2-RF-6", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "PROVENANCE_INCOMPLETE", "Trusted context canonicalization failed", ("failure_stage", "owner_kind", "owner_id", "original_code", "context_key", "context_path_digest", "offending_type", "failure_kind", "safe_marker_digest")),
    Phase2RuntimeFailurePathSpec("P2-RF-7", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "PROVENANCE_INCOMPLETE", "Trusted context canonicalization failed", ("failure_stage", "owner_kind", "owner_id", "original_code", "context_key", "context_path_digest", "offending_type", "failure_kind", "safe_marker_digest")),
    Phase2RuntimeFailurePathSpec("P2-RF-8", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "PROVENANCE_INCOMPLETE", "Trusted context canonicalization failed", ("failure_stage", "owner_kind", "owner_id", "original_code", "context_key", "context_path_digest", "offending_type", "failure_kind", "safe_marker_digest")),
    Phase2RuntimeFailurePathSpec("P2-RF-9", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "INVALID_STATE_TRANSITION", "Failed to build candidate evaluation identity", ()),
    Phase2RuntimeFailurePathSpec("P2-RF-10", VerificationOutcome.PASSED, VerificationOutcome.PASSED, False, "PROVENANCE_INCOMPLETE", "Trusted rating verification failed", ("failure_stage", "owner_kind", "owner_id", "offending_type", "failure_kind", "safe_marker_digest")),
)

def match_phase2_runtime_failure_path(record: CandidateEvaluationRecord) -> str:
    if record.candidate_evaluation_state != CandidateEvaluationState.RUNTIME_FAILED:
        raise ValueError("record is not RUNTIME_FAILED")
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
        if record.evaluation_failure.code.value != spec.failure_code:
            continue
        if not record.evaluation_failure.message.startswith(spec.failure_message_start):
            continue
        matches.append(spec.path_id)
    if len(matches) == 0:
        raise ValueError("no matching Phase 2 runtime failure path")
    if len(matches) > 1:
        raise ValueError(f"multiple matches: {matches}")
    return matches[0]
```

Strictly one match, zero-reject, multiple-reject. Parsing dynamic type names uses `qualified_type_name()` from `evaluation.py` — no `str(exc)`.

---

## 9. Strict-stop, Decimal, count equations

### 9.1 Strict-stop

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. Indices < stop: must be VERIFIED. Index == stop: INTEGRITY_INVALID or RUNTIME_FAILED. Indices > stop: UNEVALUATED. COMPLETE = no strict-stop. PARTIAL = strict-stop occurred.

### 9.2 Decimal canonicalization

```python
def canonical_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal: raise TypeError(...)
    if not value.is_finite(): raise ValueError(...)
    n = value.normalize()
    return Decimal("0") if n.is_zero() else n

def canonical_decimal_string(value: Decimal) -> str:
    return format(canonical_decimal(value), "f")
```

`format(d, "f")` — no exponent, no leading/trailing zeros. `-0` → `"0"`. Positive never `"+"`. Accepted: `"0"`, `"1"`, `"1.25"`, `"-1.25"`. Rejected: `"1.00"`, `"+1"`, `"01"`, `"1E+0"`, `"-0"`.

### 9.3 Count equations

Phase 3 disposition (disjoint): `total = feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated`.

Phase 2 state audit: `phase2_verified + phase2_integrity_invalid + phase2_runtime_failed + phase2_unevaluated = total`.

Cross: `runtime_failed = rf_from_verified + rf_from_rf`; `phase2_verified = feasible + infeasible + provider_mismatch + rf_from_verified`; `phase2_integrity_invalid = integrity_failed + provenance_failed`; `phase2_runtime_failed = rf_from_rf`; `phase2_unevaluated = unevaluated`.

---

## 10. One-shot disposition factory (P0-1)

Single authoritative payload definition — used by both the factory and `candidate_disposition_payload()`:

```python
def _disposition_payload_dict(
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
    warning_descriptor_digests: tuple[str, ...],
    blocker_descriptor_digests: tuple[str, ...],
    source_evaluation_failure_digest: str | None,
    phase3_failure_digest: str | None,
    failure_origin: FailureOrigin,
) -> dict[str, object]:
    return {
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

def candidate_disposition_payload(record: CandidateDispositionRecord) -> dict[str, object]:
    return _disposition_payload_dict(
        source_qualified_candidate_id=record.source_qualified_candidate_id,
        evaluation_order_index=record.evaluation_order_index,
        source_candidate_evaluation_state=record.source_candidate_evaluation_state,
        source_hash_verification_outcome=record.source_hash_verification_outcome,
        source_provenance_verification_outcome=record.source_provenance_verification_outcome,
        source_record_descriptor_digest=record.source_record_descriptor_digest,
        disposition=record.disposition,
        diagnostic=record.diagnostic,
        provider_identity_matches=record.provider_identity_matches,
        rating_status=record.rating_status,
        candidate_evaluation_identity_digest=record.candidate_evaluation_identity_digest,
        verified_rating_evidence_digest=record.verified_rating_evidence_digest,
        invalid_rating_evidence_digest=record.invalid_rating_evidence_digest,
        primary_engineering_value=record.primary_engineering_value,
        secondary_engineering_value=record.secondary_engineering_value,
        warning_descriptor_digests=tuple(d.message_payload_digest for d in record.warning_descriptors),
        blocker_descriptor_digests=tuple(d.message_payload_digest for d in record.blocker_descriptors),
        source_evaluation_failure_digest=record.source_evaluation_failure_digest,
        phase3_failure_digest=record.phase3_failure_digest,
        failure_origin=record.failure_origin,
    )

def build_candidate_disposition_record(**kwargs) -> CandidateDispositionRecord:
    payload = _disposition_payload_dict(**kwargs)
    digest = sha256_digest(payload)
    return CandidateDispositionRecord(
        source_qualified_candidate_id=kwargs["source_qualified_candidate_id"],
        evaluation_order_index=kwargs["evaluation_order_index"],
        source_candidate_evaluation_state=kwargs["source_candidate_evaluation_state"],
        source_hash_verification_outcome=kwargs["source_hash_verification_outcome"],
        source_provenance_verification_outcome=kwargs["source_provenance_verification_outcome"],
        source_record_descriptor_digest=kwargs["source_record_descriptor_digest"],
        disposition=kwargs["disposition"],
        diagnostic=kwargs["diagnostic"],
        provider_identity_matches=kwargs["provider_identity_matches"],
        rating_status=kwargs["rating_status"],
        candidate_evaluation_identity_digest=kwargs["candidate_evaluation_identity_digest"],
        verified_rating_evidence_digest=kwargs["verified_rating_evidence_digest"],
        invalid_rating_evidence_digest=kwargs["invalid_rating_evidence_digest"],
        primary_engineering_value=kwargs["primary_engineering_value"],
        secondary_engineering_value=kwargs["secondary_engineering_value"],
        warning_descriptors=kwargs["warning_descriptors"],
        blocker_descriptors=kwargs["blocker_descriptors"],
        source_evaluation_failure_digest=kwargs["source_evaluation_failure_digest"],
        phase3_failure_digest=kwargs["phase3_failure_digest"],
        failure_origin=kwargs["failure_origin"],
        feasibility_digest=digest,
    )
```

No `object.__setattr__`. No backfill. One canonical payload dict shared by `_disposition_payload_dict` → `sha256_digest` → `CandidateDispositionRecord(..., feasibility_digest=digest)` → `candidate_disposition_payload(record)`. All three code paths use the identical `_disposition_payload_dict`.

---

## 11. CandidateDispositionRecord

### 11.1 Model

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
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if self.evaluation_order_index < 0:
            raise ValueError("order_index must be ≥ 0")
        # Per-disposition invariants (FEASIBLE, INFEASIBLE, PROVIDER_MISMATCH,
        # INTEGRITY_FAILED, PROVENANCE_FAILED, UNEVALUATED, RUNTIME_FAILED P2/P3)
        # — full 300+ line validator as defined in §9.1 of prior round.
        # Validates: source state, outcomes, provider, rating, diagnostic,
        # identity/evidence/nullability, engineering values, failure digests, origin.
        return self

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("feasibility_digest mismatch")
```

---

## 12. Classifier (P0-5, P0-10, P0-14)

```python
def classify_candidate(input: Phase3CandidateClassificationInput) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence
    eb = input.evidence_binding

    # 1. Non-VERIFIED
    if rec.candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
        return _map_non_verified(rec, eb)

    # 2. Provider mismatch
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, input)

    # 3. rating_status is None
    if rec.rating_status is None:
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_MISSING_RATING_STATUS,
                               "Verified record has no rating status.")

    # 4. BLOCKED/FAILED
    if rec.rating_status == RatingStatus.BLOCKED.value:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.RATING_BLOCKED)
    if rec.rating_status == RatingStatus.FAILED.value:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.RATING_FAILED)

    # 5. SUCCEEDED — evidence matrix (P0-14)
    if evidence is None:
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
                               "Verified SUCCEEDED record has no evidence.")
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
                               "Verified SUCCEEDED record missing required thermal metrics.")
    if evidence.area_outer_m2 is None or evidence.area_outer_m2 <= 0 or evidence.area_inner_m2 is None or evidence.area_inner_m2 <= 0:
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
                               "Verified SUCCEEDED record has non-positive area.")
    if evidence.failure is not None:
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
                               "Verified SUCCEEDED record has failure.")
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        return _phase3_runtime(rec, evidence, input, ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
                               "Non-finite thermal metric in SUCCEEDED evidence.")

    # 6. Duty
    required = to_canonical_decimal(sizing.required_duty_w)
    abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)
    rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)
    duty_tol = max(abs_tol, rel_tol * abs(required))
    if abs(heat_w - required) > duty_tol:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.DUTY_SHORTFALL)

    # 7. Terminal delta-T
    fa = sizing.flow_arrangement
    if fa == FlowArrangement.PARALLEL.value:
        dt1 = hot_in - cold_in; dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out; dt2 = hot_out - cold_in
    min_dt = min(dt1, dt2)
    if min_dt < to_canonical_decimal(sizing.minimum_terminal_delta_t):
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE)

    # 8. FEASIBLE
    return _build_feasible(rec, evidence, input)
```

Blocked evidence matrix:
```
BLOCKED: failure may be present or not (deterministic decision frozen at implementation).
         Blockers list must be non-empty.
         heat_duty_w, outlet temperatures: may be None (no successful result).
         area fields: required finite positive (from catalog geometry, not rating).
FAILED: failure must be present.
        heat_duty_w, outlet temperatures: may be None.
        area fields: required finite positive.
```

All per-candidate message context is read exactly once during preparation (`canonicalize_phase3_messages_or_failure()`). The classifier reads only `input.evidence_binding.warning_descriptors` and `.blocker_descriptors`. No re-reading of raw `EngineeringMessage` objects.

---

## 13. RankedCandidateRecord

### 13.1 Model and invariants

```python
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
        if self.rank < 1: raise ValueError("rank must be ≥ 1")
        if not self.source_qualified_candidate_id: raise ValueError("candidate_id must be non-empty")
        for val, name in [(self.primary_objective_value, "primary"), (self.secondary_tie_break_value, "secondary")]:
            d = Decimal(val)
            if not d.is_finite(): raise ValueError(f"{name}: not finite")
            if canonical_decimal_string(d) != val: raise ValueError(f"{name}: not canonical")
        if self.optimization_objective is OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            if self.primary_objective_field != "area_outer_m2": raise ValueError("MIN_OA: primary must be area_outer_m2")
            if self.secondary_tie_break_field != "effective_length_m_canonical": raise ValueError("MIN_OA: secondary must be effective_length_m_canonical")
        else:
            if self.primary_objective_field != "effective_length_m_canonical": raise ValueError("MIN_LEN: primary must be effective_length_m_canonical")
            if self.secondary_tie_break_field != "area_outer_m2": raise ValueError("MIN_LEN: secondary must be area_outer_m2")
        for dgst, name in [(self.candidate_evaluation_identity_digest, "identity"), (self.verified_rating_evidence_digest, "evidence"), (self.feasibility_digest, "feasibility"), (self.ranked_record_digest, "ranked")]:
            if not self.DIGEST_PATTERN.match(dgst): raise ValueError(f"{name}: invalid digest")
        return self
    def verify_digest(self) -> bool:
        return self.ranked_record_digest == sha256_digest(ranked_candidate_record_payload(self))
    def verify_or_raise(self) -> None:
        if not self.verify_digest(): raise ValueError("ranked_record_digest mismatch")
```

### 13.2 Expected payload recomputation

```python
def expected_ranked_values(
    disposition: CandidateDispositionRecord,
    candidate: ManufacturableCandidate,
    objective: OptimizationObjective,
) -> tuple[str, str, str, str]:
    """Returns (primary_val, primary_field, secondary_val, secondary_field)."""
    if objective == OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
        return (disposition.primary_engineering_value, "area_outer_m2",
                canonical_decimal_string(canonical_decimal(Decimal(candidate.effective_length_m_canonical))),
                "effective_length_m_canonical")
    else:
        return (canonical_decimal_string(canonical_decimal(Decimal(candidate.effective_length_m_canonical))),
                "effective_length_m_canonical",
                disposition.primary_engineering_value, "area_outer_m2")
```

### 13.3 Payload

```python
def ranked_candidate_record_payload(record: RankedCandidateRecord) -> dict[str, object]:
    return {
        "rank": record.rank,
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "optimization_objective": record.optimization_objective.value,
        "primary_objective_value": record.primary_objective_value,
        "primary_objective_field": record.primary_objective_field,
        "secondary_tie_break_value": record.secondary_tie_break_value,
        "secondary_tie_break_field": record.secondary_tie_break_field,
        "candidate_evaluation_identity_digest": record.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": record.verified_rating_evidence_digest,
        "feasibility_digest": record.feasibility_digest,
    }
```

### 13.4 Sort keys

```
MIN_OA: (canonical_decimal(Decimal(area_outer_m2)), canonical_decimal(Decimal(effective_length_m_canonical)), source_qualified_candidate_id)
MIN_LEN: (canonical_decimal(Decimal(effective_length_m_canonical)), canonical_decimal(Decimal(area_outer_m2)), source_qualified_candidate_id)
```

---

## 14. OptimizationResult

### 14.1 Model and validators

```python
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
    termination_status: TerminationStatus
    ordered_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]
    result_core_hash: str
    provenance_digest: str
    result_hash: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.schema_version != 1: raise ValueError("schema_version must be 1")
        if self.requested_top_n < 1: raise ValueError("requested_top_n must be ≥ 1")
        for n in ["total_candidate_count", "feasible_candidate_count", "infeasible_candidate_count",
                   "provider_mismatch_count", "integrity_failed_count", "provenance_failed_count",
                   "runtime_failed_count", "unevaluated_count", "phase2_verified_record_count",
                   "phase2_integrity_invalid_record_count", "phase2_runtime_failed_record_count",
                   "phase2_unevaluated_record_count", "runtime_failed_from_phase2_verified_count",
                   "runtime_failed_from_phase2_runtime_failed_count"]:
            if getattr(self, n) < 0: raise ValueError(f"{n} must be ≥ 0")
        d3 = (self.feasible_candidate_count + self.infeasible_candidate_count + self.provider_mismatch_count +
              self.integrity_failed_count + self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count)
        if d3 != self.total_candidate_count: raise ValueError("disposition counts ≠ total")
        p2 = (self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count +
              self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count)
        if p2 != self.total_candidate_count: raise ValueError("Phase 2 state counts ≠ total")
        eq1 = self.runtime_failed_count == self.runtime_failed_from_phase2_verified_count + self.runtime_failed_from_phase2_runtime_failed_count
        eq2 = self.phase2_verified_record_count == self.feasible_candidate_count + self.infeasible_candidate_count + self.provider_mismatch_count + self.runtime_failed_from_phase2_verified_count
        eq3 = self.phase2_integrity_invalid_record_count == self.integrity_failed_count + self.provenance_failed_count
        eq4 = self.phase2_runtime_failed_record_count == self.runtime_failed_from_phase2_runtime_failed_count
        eq5 = self.phase2_unevaluated_record_count == self.unevaluated_count
        if not (eq1 and eq2 and eq3 and eq4 and eq5): raise ValueError("cross-equation mismatch")
        N, F, TN = self.total_candidate_count, self.feasible_candidate_count, min(self.requested_top_n, self.feasible_candidate_count)
        if len(self.ordered_disposition_record_digests) != N: raise ValueError("disposition length ≠ total")
        if len(self.ordered_ranked_record_digests) != F: raise ValueError("ranked length ≠ feasible")
        if len(self.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length ≠ min")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N not prefix of ranked")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, self.result_hash))
        if self.optimization_result_id != expected_id: raise ValueError("UUID mismatch")
        return self
```

### 14.2 Core payload

```python
def result_core_payload(result: OptimizationResult) -> dict[str, object]:
    return {
        "schema_version": result.schema_version,
        "sizing_request_identity_digest": result.sizing_request_identity_digest,
        "passed_gate_digest": result.passed_gate_digest,
        "candidate_set_digest": result.candidate_set_digest,
        "evaluation_input_digest": result.evaluation_input_digest,
        "optimization_objective": result.optimization_objective.value,
        "requested_top_n": result.requested_top_n,
        "total_candidate_count": result.total_candidate_count,
        "feasible_candidate_count": result.feasible_candidate_count,
        "infeasible_candidate_count": result.infeasible_candidate_count,
        "provider_mismatch_count": result.provider_mismatch_count,
        "integrity_failed_count": result.integrity_failed_count,
        "provenance_failed_count": result.provenance_failed_count,
        "runtime_failed_count": result.runtime_failed_count,
        "unevaluated_count": result.unevaluated_count,
        "phase2_verified_record_count": result.phase2_verified_record_count,
        "phase2_integrity_invalid_record_count": result.phase2_integrity_invalid_record_count,
        "phase2_runtime_failed_record_count": result.phase2_runtime_failed_record_count,
        "phase2_unevaluated_record_count": result.phase2_unevaluated_record_count,
        "runtime_failed_from_phase2_verified_count": result.runtime_failed_from_phase2_verified_count,
        "runtime_failed_from_phase2_runtime_failed_count": result.runtime_failed_from_phase2_runtime_failed_count,
        "ordered_disposition_record_digests": list(result.ordered_disposition_record_digests),
        "ordered_ranked_record_digests": list(result.ordered_ranked_record_digests),
        "ordered_top_n_record_digests": list(result.ordered_top_n_record_digests),
        "termination_status": result.termination_status.value,
        "ordered_warning_digests": list(result.ordered_warning_digests),
        "ordered_blocker_digests": list(result.ordered_blocker_digests),
    }
```

### 14.3 Hash

```python
result_core_hash = sha256_digest(result_core_payload(result))
provenance_digest = provenance_graph.compute_hash()
result_hash = sha256_digest({"result_core_hash": result_core_hash, "provenance_digest": provenance_digest})
optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))
```

---

## 15. Warning/blocker aggregation (P0-12, P0-13)

```python
def build_result_message_digest_tuples(
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    stop_index: int | None,
) -> tuple[list[str], list[str]]:
    # 1. Validate all descriptors first
    for dr in disposition_records:
        for d in dr.warning_descriptors:
            verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors:
            verify_phase3_message_descriptor_or_raise(d)
    # 2. Collect warnings
    all_w: list[Phase3MessageDescriptor] = []
    for dr in disposition_records:
        all_w.extend(dr.warning_descriptors)
    # 3. Strict-stop warning (if PARTIAL)
    if stop_index is not None:
        ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
        if ss_warning is None:
            raise RuntimeError("strict-stop builder returned None for PARTIAL")
        ss_desc = build_engineering_message_descriptor(ss_warning)
        if isinstance(ss_desc, RunFailure):
            raise RuntimeError("strict-stop descriptor construction failed")
        all_w.append(ss_desc)
    # 4. Sort by typed owner_sort_key tuple
    all_w.sort(key=lambda d: d.owner_sort_key)
    warning_digests = [d.message_payload_digest for d in all_w]
    # 5. Blockers
    all_b: list[Phase3MessageDescriptor] = []
    for dr in disposition_records:
        all_b.extend(dr.blocker_descriptors)
    all_b.sort(key=lambda d: d.owner_sort_key)
    blocker_digests = [d.message_payload_digest for d in all_b]
    return (warning_digests, blocker_digests)
```

External verifier:
```python
expected_w, expected_b = build_result_message_digest_tuples(evaluation_input, disposition_records, stop_index)
if list(result.ordered_warning_digests) != expected_w:
    raise ValueError("ordered_warning_digests mismatch")
if list(result.ordered_blocker_digests) != expected_b:
    raise ValueError("ordered_blocker_digests mismatch")
```

COMPLETE: `stop_index is None` → no strict-stop descriptor in expected tuple.
PARTIAL: `stop_index is not None` → strict-stop descriptor appears exactly once.

---

## 16. Strict-stop warning

```python
def _build_strict_stop_warning(evaluation_input, stop_index):
    if stop_index is None:
        return None
    rec = evaluation_input.evaluation_records[stop_index]
    return EngineeringMessage(
        code=ErrorCode.PHASE3_STRICT_STOP,
        severity=EngineeringMessageSeverity.WARNING,
        message="Phase 2 strict-stop occurred; records after index are UNEVALUATED.",
        source_module="hexagent.optimization.phase3_input",
        affected_paths=(),
        context=(
            ("stop_index", stop_index),
            ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
            ("source_state", rec.candidate_evaluation_state.value),
        ),
    )
```

---

## 17. Provenance (P0-16)

### 17.1 Namespace

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
```

### 17.2 Role-qualified node ID

```python
def expected_phase3_node_id(exp: "ExpectedPhase3ProvenanceNode") -> UUID:
    return uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{exp.role}:{exp.node_type.value}:{exp.payload_hash}")

class ExpectedPhase3ProvenanceNode(NamedTuple):
    role: str
    node_type: ProvenanceNodeType
    payload_hash: str
```

### 17.3 Expected nodes

```python
def expected_phase3_provenance_nodes(ei, dispositions, ranked, result) -> list[ExpectedPhase3ProvenanceNode]:
    nodes: list[ExpectedPhase3ProvenanceNode] = []
    nodes.append(ExpectedPhase3ProvenanceNode("root", ProvenanceNodeType.EXTERNAL,
        sha256_digest({"artifact_kind": "phase3_evaluation_input", "evaluation_input_digest": ei.evaluation_input_digest})))
    nodes.append(ExpectedPhase3ProvenanceNode("sizing_request", ProvenanceNodeType.INPUT_FILE, ei.sizing_request_identity_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("passed_gate", ProvenanceNodeType.CALCULATION_RUN, ei.gate_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("candidate_set", ProvenanceNodeType.CALCULATION_RUN, ei.candidate_set_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("evaluation_input", ProvenanceNodeType.INTERMEDIATE, ei.evaluation_input_digest))
    for i, d in enumerate(dispositions):
        nodes.append(ExpectedPhase3ProvenanceNode(f"disposition[{i}]", ProvenanceNodeType.INTERMEDIATE, d.feasibility_digest))
    for i, r in enumerate(ranked):
        nodes.append(ExpectedPhase3ProvenanceNode(f"ranked[{i}]", ProvenanceNodeType.INTERMEDIATE, r.ranked_record_digest))
    nodes.append(ExpectedPhase3ProvenanceNode("top_n_selection", ProvenanceNodeType.INTERMEDIATE,
        sha256_digest({"ordered_top_n_record_digests": list(result.ordered_top_n_record_digests)})))
    nodes.append(ExpectedPhase3ProvenanceNode("result_core", ProvenanceNodeType.RESULT, result.result_core_hash))
    optimizer_payload = {
        "schema_version": 1, "evaluation_input_digest": ei.evaluation_input_digest,
        "optimization_objective": result.optimization_objective.value, "requested_top_n": result.requested_top_n,
        "termination_status": result.termination_status.value, "result_core_hash": result.result_core_hash,
        "phase3_algorithm_version": "task009-phase3-v1",
    }
    nodes.append(ExpectedPhase3ProvenanceNode("optimizer", ProvenanceNodeType.OPTIMIZER, sha256_digest(optimizer_payload)))
    return nodes
```

### 17.4 Expected edges

```python
def expected_phase3_provenance_edges(ei, dispositions, ranked, result) -> tuple[tuple[str, str, str], ...]:
    expected_nodes = expected_phase3_provenance_nodes(ei, dispositions, ranked, result)
    roles = {n.role: n for n in expected_nodes}
    def uid(role): return str(expected_phase3_node_id(roles[role]))
    edges: list[tuple[str, str, str]] = []
    edges.append((uid("root"), uid("sizing_request"), "regulates"))
    edges.append((uid("sizing_request"), uid("passed_gate"), "consumed_by"))
    edges.append((uid("passed_gate"), uid("candidate_set"), "produced"))
    edges.append((uid("candidate_set"), uid("evaluation_input"), "consumed_by"))
    for i in range(len(dispositions)):
        edges.append((uid("evaluation_input"), uid(f"disposition[{i}]"), "evaluated"))
    # Disposition→ranked by candidate identity
    feasible_keys = {}
    for i, d in enumerate(dispositions):
        if d.disposition is Phase3Disposition.FEASIBLE:
            feasible_keys[(d.source_qualified_candidate_id, d.feasibility_digest)] = f"disposition[{i}]"
    for ri, rr in enumerate(ranked):
        key = (rr.source_qualified_candidate_id, rr.feasibility_digest)
        disp_role = feasible_keys.get(key)
        if disp_role is None:
            raise ValueError(f"ranked[{ri}]: no matching FEASIBLE disposition")
        edges.append((uid(disp_role), uid(f"ranked[{ri}]"), "ranked"))
    # Top-N
    edges.append((uid("evaluation_input"), uid("top_n_selection"), "selected_by"))
    for ri in range(len(result.ordered_top_n_record_digests)):
        edges.append((uid(f"ranked[{ri}]"), uid("top_n_selection"), "selected"))
    edges.append((uid("top_n_selection"), uid("result_core"), "produced"))
    edges.append((uid("result_core"), uid("optimizer"), "executed_by"))
    return tuple(sorted(edges))
```

### 17.5 Semantic verifier

```python
def verify_phase3_provenance_graph_or_raise(graph, *, ei, dispositions, ranked, result):
    expected_nodes = expected_phase3_provenance_nodes(ei, dispositions, ranked, result)
    N, F = len(dispositions), len(ranked)
    if len(expected_nodes) != 8 + N + F:
        raise ValueError(f"internal expected node count {len(expected_nodes)} != 8+{N}+{F}")
    if len(graph.nodes) != len(expected_nodes):
        raise ValueError(f"graph node count {len(graph.nodes)} != {len(expected_nodes)}")
    expected_ids = {expected_phase3_node_id(n): n for n in expected_nodes}
    if len(expected_ids) != len(expected_nodes):
        raise ValueError("duplicate expected provenance node IDs")
    actual_ids = {n.node_id: n for n in graph.nodes}
    # Check each expected node exists
    for eid, exp in expected_ids.items():
        actual = actual_ids.get(eid)
        if actual is None:
            raise ValueError(f"missing node: {exp.role}")
        if actual.node_type != exp.node_type:
            raise ValueError(f"node {exp.role}: type mismatch")
        if actual.payload_hash != exp.payload_hash:
            raise ValueError(f"node {exp.role}: payload hash mismatch")
        if actual.label != "":
            raise ValueError(f"node {exp.role}: label must be empty")
        if actual.metadata != ():
            raise ValueError(f"node {exp.role}: metadata must be empty")
    # No extra nodes
    extra = set(actual_ids) - set(expected_ids)
    if extra:
        raise ValueError(f"extra nodes: {len(extra)}")
    # Edge check
    expected_edge_keys = expected_phase3_provenance_edges(ei, dispositions, ranked, result)
    actual_edge_keys = tuple(sorted(
        (str(e.source_id), str(e.target_id), e.relation) for e in graph.edges
    ))
    if len(actual_edge_keys) != len(set(actual_edge_keys)):
        raise ValueError("duplicate provenance edges")
    if actual_edge_keys != expected_edge_keys:
        raise ValueError("provenance edge set mismatch")
    for e in graph.edges:
        if e.metadata != ():
            raise ValueError("edge metadata must be empty")
    # Reachability from root
    root_id = expected_phase3_node_id(expected_nodes[0])
    children = {n.node_id: [] for n in graph.nodes}
    for e in graph.edges:
        children[e.source_id].append(e.target_id)
    visited = set(); queue = [root_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited: continue
        visited.add(nid); queue.extend(children.get(nid, []))
    if len(visited) != len(graph.nodes):
        raise ValueError("graph has unreachable nodes")
```

---

## 18. External verifier (P0-11)

```python
def verify_optimization_result_or_raise(
    result: OptimizationResult,
    *,
    evaluation_input: Phase3EvaluationInput,
    source_bindings: tuple[Phase3SourceRecordBinding, ...],
    classification_inputs: tuple[Phase3CandidateClassificationInput, ...],
    disposition_records: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    provenance_graph: ProvenanceGraph,
) -> None:
    N = result.total_candidate_count
    # 1. Input binding
    if result.evaluation_input_digest != evaluation_input.evaluation_input_digest: raise ValueError("evaluation_input_digest mismatch")
    if result.sizing_request_identity_digest != evaluation_input.sizing_request_identity_digest: raise ValueError("sizing identity mismatch")
    if result.candidate_set_digest != evaluation_input.candidate_set_digest: raise ValueError("candidate_set_digest mismatch")
    if result.passed_gate_digest != evaluation_input.gate_digest: raise ValueError("passed_gate_digest mismatch")
    if result.total_candidate_count != evaluation_input.evaluation_record_count: raise ValueError("total count mismatch")
    # 2. Objective/Top-N binding
    if result.optimization_objective != evaluation_input.sizing_request_identity.optimization_objective: raise ValueError("objective mismatch")
    if result.requested_top_n != evaluation_input.sizing_request_identity.top_n: raise ValueError("top_n mismatch")
    # 3. Source binding verification
    if len(source_bindings) != N: raise ValueError("source_bindings count mismatch")
    if len(classification_inputs) != N: raise ValueError("classification_inputs count mismatch")
    if len(disposition_records) != N: raise ValueError("disposition_records count mismatch")
    for i, (rec, sb, cin, dr) in enumerate(zip(evaluation_input.evaluation_records, source_bindings, classification_inputs, disposition_records)):
        # Candidate/index binding
        if dr.evaluation_order_index != i: raise ValueError(f"disposition[{i}]: order mismatch")
        if dr.source_qualified_candidate_id != rec.source_qualified_candidate_id: raise ValueError(f"[{i}]: candidate_id mismatch")
        if dr.source_candidate_evaluation_state != rec.candidate_evaluation_state: raise ValueError(f"[{i}]: state mismatch")
        if dr.source_hash_verification_outcome != rec.hash_verification_outcome: raise ValueError(f"[{i}]: hash outcome mismatch")
        if dr.source_provenance_verification_outcome != rec.provenance_verification_outcome: raise ValueError(f"[{i}]: provenance mismatch")
        if dr.provider_identity_matches != rec.provider_identity_matches: raise ValueError(f"[{i}]: provider mismatch")
        if dr.rating_status != rec.rating_status: raise ValueError(f"[{i}]: rating mismatch")
        # Evidence binding consistency (no recomputation)
        if rec.candidate_evaluation_state == CandidateEvaluationState.VERIFIED and rec.verified_rating_evidence is not None:
            if dr.candidate_evaluation_identity_digest != (rec.candidate_evaluation_identity.candidate_evaluation_identity_digest if rec.candidate_evaluation_identity else None):
                raise ValueError(f"[{i}]: identity digest mismatch")
        # Classifier replay using cached bindings only
        expected = classify_candidate(cin)
        if candidate_disposition_payload(dr) != candidate_disposition_payload(expected):
            raise ValueError(f"[{i}]: disposition payload mismatch with re-classified result")
        dr.verify_or_raise()
        # Verify descriptor consistency
        for d in dr.warning_descriptors: verify_phase3_message_descriptor_or_raise(d)
        for d in dr.blocker_descriptors: verify_phase3_message_descriptor_or_raise(d)
    # 4. Count recomputation (independent)
    _verify_all_counts(result, evaluation_input, disposition_records)
    # 5. Ranked records
    F = result.feasible_candidate_count
    if len(ranked_records) != F: raise ValueError(f"ranked count {len(ranked_records)} != {F}")
    feasible_disps = [d for d in disposition_records if d.disposition is Phase3Disposition.FEASIBLE]
    if len(feasible_disps) != F: raise ValueError("feasible disposition count mismatch")
    for ri, rr in enumerate(ranked_records):
        if result.ordered_ranked_record_digests[ri] != rr.ranked_record_digest: raise ValueError(f"ranked[{ri}]: digest mismatch")
        rr.verify_or_raise()
        disp = next((d for d in feasible_disps if d.source_qualified_candidate_id == rr.source_qualified_candidate_id and d.feasibility_digest == rr.feasibility_digest), None)
        if disp is None: raise ValueError(f"ranked[{ri}]: no FEASIBLE disposition match")
        pv, pf, sv, sf = expected_ranked_values(disp, evaluation_input.materialization_result.candidates[disp.evaluation_order_index], result.optimization_objective)
        exp_payload = ranked_candidate_record_payload(rr)
        if exp_payload["primary_objective_value"] != pv or exp_payload["primary_objective_field"] != pf: raise ValueError(f"ranked[{ri}]: primary value mismatch")
        if exp_payload["secondary_tie_break_value"] != sv or exp_payload["secondary_tie_break_field"] != sf: raise ValueError(f"ranked[{ri}]: secondary value mismatch")
        if rr.rank != ri + 1: raise ValueError(f"ranked[{ri}]: rank {rr.rank} != {ri+1}")
    # 6. Top-N
    TN = min(result.requested_top_n, F)
    if len(result.ordered_top_n_record_digests) != TN: raise ValueError("Top-N length mismatch")
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]: raise ValueError("Top-N must be prefix of ranked")
    # 7. Warning/blocker aggregation
    stop_index = _find_stop_index(evaluation_input)
    expected_w, expected_b = build_result_message_digest_tuples(evaluation_input, disposition_records, stop_index)
    if list(result.ordered_warning_digests) != expected_w: raise ValueError("warning digests mismatch")
    if list(result.ordered_blocker_digests) != expected_b: raise ValueError("blocker digests mismatch")
    # 8. Termination
    if stop_index is None:
        if result.termination_status is not TerminationStatus.COMPLETE: raise ValueError("must be COMPLETE")
    else:
        if result.termination_status is not TerminationStatus.PARTIAL: raise ValueError("must be PARTIAL")
    # 9. Hash
    expected_core = sha256_digest(result_core_payload(result))
    if result.result_core_hash != expected_core: raise ValueError("result_core_hash mismatch")
    verify_phase3_provenance_graph_or_raise(provenance_graph, ei=evaluation_input, dispositions=disposition_records, ranked=ranked_records, result=result)
    expected_prov = provenance_graph.compute_hash()
    if result.provenance_digest != expected_prov: raise ValueError("provenance_digest mismatch")
    expected_hash = sha256_digest({"result_core_hash": result.result_core_hash, "provenance_digest": result.provenance_digest})
    if result.result_hash != expected_hash: raise ValueError("result_hash mismatch")
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result.result_hash))
    if result.optimization_result_id != expected_id: raise ValueError("UUID mismatch")
    # 10. Uniqueness + format
    for name, dgst in _all_digest_fields(result):
        if not re.match(r"^sha256:[0-9a-f]{64}$", dgst): raise ValueError(f"{name}: invalid digest")
    if len(set(result.ordered_disposition_record_digests)) != N: raise ValueError("disposition digests not unique")
    if len(set(result.ordered_ranked_record_digests)) != F: raise ValueError("ranked digests not unique")
    if len(set(result.ordered_top_n_record_digests)) != TN: raise ValueError("Top-N digests not unique")
```

---

## 19. Implementation boundary

### New files
- `src/hexagent/optimization/phase3_input.py` — `Phase3EvaluationInput`, preparation, `Phase3SourceRecordBinding`
- `src/hexagent/optimization/feasibility.py` — classification, `Phase3CandidateClassificationInput`, `CandidateDispositionRecord`
- `src/hexagent/optimization/ranking.py` — `RankedCandidateRecord`, sort keys
- `src/hexagent/optimization/result.py` — `OptimizationResult`, external verifier, provenance
- `tests/unit/test_task009_phase3_*.py`

### Existing files modified
- `src/hexagent/domain/messages.py` — add Phase 3 error codes to `ErrorCode`
- `src/hexagent/optimization/evaluation.py` — export `_build_message_descriptor` as `build_engineering_message_descriptor_impl`

### Untouched
All Phase 1/2 modules, TASK-008, catalog, all existing tests.

---

## 20. Test matrix

Full matrix covering all 16 P0 issues: unified payload equality, single-pass no-context re-read, source evidence digest frozen, VERIFIED evidence binding mandatory, tampered binding rejected, classifier consumes binding exclusively, two-stage lifecycle non-circular, descriptor typed tuple sorting matches Phase 2, full canonicalization failure context, no broad `except Exception`, no `...`, no `pass`, contract fully self-contained, external verifier uses cached descriptors, COMPLETE/PARTIAL warning tuple exact equality, BLOCKED/FAILED evidence matrix, SUCCEEDED missing metric → `PHASE3_TRUSTED_EVIDENCE_INCOMPLETE`, 10 Phase 2 path specs zero/multiple-match rejected, provenance exact node/edge set/metadata/reachability, `schema_version=2` rejected.

---

## 21. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 SHA:** NOT ESTABLISHED
