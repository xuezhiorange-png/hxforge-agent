# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

---

## 1. Scope and non-goals

Phase 3 consumes `tuple[CandidateEvaluationRecord, ...]` via `Phase3EvaluationInput` and produces `OptimizationResult`.

Non-goals: TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver, candidate generation, catalog changes, Phase 2 mutation, re-running TASK-008, recovering strict-stop.

---

## 2. Frozen enums and error codes (P0-9)

```python
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
```

New ErrorCode values (added to existing `ErrorCode`):
```
PHASE3_MISSING_RATING_STATUS = "phase3_missing_rating_status"
PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
PHASE3_STRICT_STOP = "phase3_strict_stop"
PHASE3_TRUSTED_EVIDENCE_INCOMPLETE = "phase3_trusted_evidence_incomplete"
```

---

## 3. Phase3EvaluationInput

### 3.1 Model

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

### 3.2 Payload helpers

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
        "ordered_evaluation_record_descriptor_digests": list(
            input.ordered_evaluation_record_descriptor_digests
        ),
    }
```

### 3.3 13-step verify_or_raise()

Step 1: type verification. Step 2: `materialization_result.verify_or_raise()`. Step 3: sizing identity digest. Step 4: `candidate_set.verify_digest()`. Step 5: `sizing_gate.verify_digest()`. Step 6: candidate-set ↔ sizing binding. Step 7: gate ↔ candidate-set binding. Step 8: count parity. Step 9: one-to-one record↔candidate binding. Step 10: exhaustive state verification per §4 matrix. Step 11: strict-stop invariant. Step 12: descriptor digest verification. Step 13: `evaluation_input_digest` verification.

---

## 4. Phase 2 constructor matrix (P0-12)

### 4.1 VERIFIED (1 path)

state=VERIFIED, feasible=False, feasibility_status, identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None, provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None, hash=PASSED, provenance=PASSED.

Provider parity (VERIFIED only): `provider_matches == True ⇔ feasibility == NOT_EVALUATED`; `provider_matches == False ⇔ feasibility == PROVIDER_IDENTITY_MISMATCH`.

### 4.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false (L2333) | Provenance false (L2388) |
|---|---|---|
| hash | FAILED | PASSED |
| provenance | NOT_RUN | FAILED |
| invalid_evidence | present | present |
| claimed_audit | present, state=HASH_VERIFICATION_ERROR | present, state=PROVENANCE_VERIFICATION_ERROR |
| provider_matches | False | True(default) |

Common: state=INTEGRITY_INVALID, feasible=False, identity=None, verified_evidence=None, eval_failure=None, rating_status=None.

### 4.3 RUNTIME_FAILED (10 paths) — full RunFailure context

| # | Line | Hash | Prov | Audit | Failure code | Fixed message | Context shape |
|---|---|---|---|---|---|---|---|
| 1 | 2277 | NOT_RUN | NOT_RUN | present(U) | INVALID_STATE_TRANSITION | "Expected exact RatingResult, got ..." | (none passed) |
| 2 | 2303 | ERROR | NOT_RUN | present(HE) | HASH_MISMATCH | "Rating result hash verification raised." | (none) |
| 3 | 2358 | PASSED | ERROR | present(PE) | PROVENANCE_INCOMPLETE | "Rating result provenance verification raised." | (none) |
| 4 | 2414 | PASSED | PASSED | present(HE) | INVALID_STATE_TRANSITION | "Failed to extract trusted evidence" | (none) |
| 5 | 2478 | PASSED | PASSED | **None** | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." | Context: failure_stage, owner_kind, owner_id, context_key, context_path_digest, offending_type, failure_kind, safe_marker_digest |
| 6 | 2511 | PASSED | PASSED | **None** | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." | As path 5 + original_code |
| 7 | 2543 | PASSED | PASSED | **None** | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." | As path 6 |
| 8 | 2575 | PASSED | PASSED | **None** | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." | As path 6 |
| 9 | 2611 | PASSED | PASSED | **None** | INVALID_STATE_TRANSITION | "Failed to build candidate evaluation identity" | (none) |
| 10 | 2672 | PASSED | PASSED | **None** | PROVENANCE_INCOMPLETE | "Trusted rating verification failed." | Context: failure_stage, owner_kind, owner_id, offending_type, failure_kind, safe_marker_digest |

U=UNREADABLE, HE=HASH_VERIFICATION_ERROR, PE=PROVENANCE_VERIFICATION_ERROR.

For paths 5-8 (canonicalization failures):
```
context_path_digest = sha256_digest({"context_path": list(cce.context_path)})
safe_marker_digest = sha256_digest({
    "context_key": cce.context_key,
    "context_path": list(cce.context_path),
    "offending_type": cce.offending_type,
    "failure_kind": cce.failure_kind.value,
})
```

### 4.4 UNEVALUATED (1 path)

state=UNEVALUATED, feasible=False, identity=None, claimed_audit=None, verified=None, invalid=None, provider=True, eval_failure=None, rating=None, hash=NOT_RUN, provenance=NOT_RUN.

---

## 5. Strict-stop, Decimal, count equations

Identical to §5-6-8 of prior round. Count equations unchanged.

---

## 6. Phase3MessageDescriptor and evidence binding (P0-3)

```python
class Phase3MessageDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    owner_sort_key: str                # canonical JSON of full sort key
    original_code: str
    canonical_message_payload: dict[str, object]
    message_payload_digest: str

def build_engineering_message_descriptor(message: EngineeringMessage) -> Phase3MessageDescriptor | RunFailure:
    try:
        desc = _build_message_descriptor(message)
    except Exception:
        return RunFailure(code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
                          message="Message descriptor construction failed.", ...)
    if desc.canonicalization_error is not None:
        return RunFailure(
            code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
            message="Trusted context canonicalization failed during feasibility classification.",
            traceback=None,
            context=(
                ("failure_kind", desc.canonicalization_error.failure_kind.value),
                ("context_key", desc.canonicalization_error.context_key),
                ("offending_type", desc.canonicalization_error.offending_type),
            ),
        )
    if desc.message_payload_digest is None:
        return RunFailure(
            code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
            message="Missing message payload digest.",
            traceback=None,
            context=(),
        )
    return Phase3MessageDescriptor(
        owner_sort_key=canonical_json(desc.owner_sort_key),
        original_code=desc.original_code,
        canonical_message_payload=engineering_message_payload(message),
        message_payload_digest=desc.message_payload_digest,
    )

def canonicalize_phase3_messages_or_failure(
    messages: tuple[EngineeringMessage, ...],
    owner_kind: str,
    source_cid: str,
    eval_idx: int,
    source_desc_digest: str,
) -> tuple[Phase3MessageDescriptor, ...] | RunFailure:
    descriptors: list[Phase3MessageDescriptor] = []
    for msg in messages:
        result = build_engineering_message_descriptor(msg)
        if isinstance(result, RunFailure):
            return result
        descriptors.append(result)
    # Sort by owner_sort_key (stable, preserves duplicates)
    descriptors.sort(key=lambda d: d.owner_sort_key)
    return tuple(descriptors)
```

**Evidence binding** — computed once, never recomputed:

```python
class Phase3VerifiedEvidenceBinding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    verified_rating_evidence_digest: str
    warning_descriptors: tuple[Phase3MessageDescriptor, ...]
    blocker_descriptors: tuple[Phase3MessageDescriptor, ...]
    failure_descriptor_digest: str | None
```

The evidence binding is constructed once in the classifier and reused by the external verifier. The verifier never calls `compute_explicit_evidence_digest()` or `engineering_message_payload()` on already-descriptorized messages.

---

## 7. Phase3CandidateClassificationInput

```python
class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal[1] = 1
    source_record: CandidateEvaluationRecord
    source_record_descriptor_digest: str
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    evidence_binding: Phase3VerifiedEvidenceBinding | None = None

    @model_validator(mode="after")
    def _validate(self) -> typing.Self:
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing_request_identity_digest mismatch")
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_order_index mismatch")
        expected = sha256_digest(evaluation_record_descriptor_payload(self.source_record))
        if self.source_record_descriptor_digest != expected:
            raise ValueError("source_record_descriptor_digest mismatch")
        return self
```

---

## 8. One-shot frozen disposition factory (P0-1)

```python
def candidate_disposition_payload_from_values(
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
) -> tuple[dict[str, object], str]:
    """Return (payload_dict, feasibility_digest). Neither contains the other."""
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
        "warning_descriptor_sort_keys": [d.owner_sort_key for d in warning_descriptors],
        "warning_descriptor_digests": [d.message_payload_digest for d in warning_descriptors],
        "blocker_descriptor_sort_keys": [d.owner_sort_key for d in blocker_descriptors],
        "blocker_descriptor_digests": [d.message_payload_digest for d in blocker_descriptors],
        "source_evaluation_failure_digest": source_evaluation_failure_digest,
        "phase3_failure_digest": phase3_failure_digest,
        "failure_origin": failure_origin.value,
    }
    digest = sha256_digest(payload)
    return payload, digest

def build_candidate_disposition_record(
    *args, **kwargs,
) -> CandidateDispositionRecord:
    payload, digest = candidate_disposition_payload_from_values(**kwargs)
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

No `object.__setattr__`, no post-construction modification, no empty/placeholder digest.

---

## 9. CandidateDispositionRecord (P0-6, P0-11)

### 9.1 Model

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
        # Common digest validation
        for d, n in [(self.source_record_descriptor_digest, "source_desc"),
                      (self.feasibility_digest, "feasibility")]:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError(f"{n}: invalid digest")
        self._check_digest(self.candidate_evaluation_identity_digest, "identity")
        self._check_digest(self.verified_rating_evidence_digest, "evidence")
        self._check_digest(self.invalid_rating_evidence_digest, "invalid")
        self._check_digest(self.source_evaluation_failure_digest, "source_failure")
        self._check_digest(self.phase3_failure_digest, "phase3_failure")

        # FEASIBLE
        if self.disposition is Phase3Disposition.FEASIBLE:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
                raise ValueError("FEASIBLE: source must be VERIFIED")
            if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("FEASIBLE: hash must be PASSED")
            if self.source_provenance_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("FEASIBLE: provenance must be PASSED")
            if not self.provider_identity_matches:
                raise ValueError("FEASIBLE: provider must match")
            if self.rating_status != RatingStatus.SUCCEEDED.value:
                raise ValueError("FEASIBLE: rating must be SUCCEEDED")
            if self.diagnostic != FeasibilityDiagnosticKey.NONE:
                raise ValueError("FEASIBLE: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("FEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("FEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("FEASIBLE: invalid evidence must be None")
            if self.primary_engineering_value is None or self.secondary_engineering_value is None:
                raise ValueError("FEASIBLE: engineering values required")
            self._check_canonical(self.primary_engineering_value, "primary")
            self._check_canonical(self.secondary_engineering_value, "secondary")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("FEASIBLE: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("FEASIBLE: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("FEASIBLE: failure_origin must be NONE")

        # PROVIDER_IDENTITY_MISMATCH
        elif self.disposition is Phase3Disposition.PROVIDER_IDENTITY_MISMATCH:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
                raise ValueError("PROVIDER_MISMATCH: source must be VERIFIED")
            if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("PROVIDER_MISMATCH: hash must be PASSED")
            if self.source_provenance_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("PROVIDER_MISMATCH: provenance must be PASSED")
            if self.provider_identity_matches:
                raise ValueError("PROVIDER_MISMATCH: provider must NOT match")
            if self.diagnostic != FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH:
                raise ValueError("PROVIDER_MISMATCH: diagnostic mismatch")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("PROVIDER_MISMATCH: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("PROVIDER_MISMATCH: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: invalid evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering values must be None")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("PROVIDER_MISMATCH: failure_origin must be NONE")

        # INFEASIBLE
        elif self.disposition is Phase3Disposition.INFEASIBLE:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
                raise ValueError("INFEASIBLE: source must be VERIFIED")
            if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("INFEASIBLE: hash must be PASSED")
            if self.source_provenance_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("INFEASIBLE: provenance must be PASSED")
            if not self.provider_identity_matches:
                raise ValueError("INFEASIBLE: provider must match")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("INFEASIBLE: identity required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("INFEASIBLE: evidence required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("INFEASIBLE: invalid evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("INFEASIBLE: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("INFEASIBLE: engineering values must be None")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("INFEASIBLE: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("INFEASIBLE: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("INFEASIBLE: failure_origin must be NONE")
            if self.rating_status == RatingStatus.SUCCEEDED.value:
                if self.diagnostic not in (FeasibilityDiagnosticKey.DUTY_SHORTFALL,
                                           FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE):
                    raise ValueError("INFEASIBLE+SUCCEEDED: diagnostic mismatch")
            elif self.rating_status == RatingStatus.BLOCKED.value:
                if self.diagnostic != FeasibilityDiagnosticKey.RATING_BLOCKED:
                    raise ValueError("INFEASIBLE+BLOCKED: diagnostic must be RATING_BLOCKED")
            elif self.rating_status == RatingStatus.FAILED.value:
                if self.diagnostic != FeasibilityDiagnosticKey.RATING_FAILED:
                    raise ValueError("INFEASIBLE+FAILED: diagnostic must be RATING_FAILED")
            else:
                raise ValueError(f"INFEASIBLE: unexpected rating_status {self.rating_status!r}")

        # INTEGRITY_FAILED
        elif self.disposition is Phase3Disposition.INTEGRITY_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("INTEGRITY_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != VerificationOutcome.FAILED:
                raise ValueError("INTEGRITY_FAILED: hash must be FAILED")
            if self.source_provenance_verification_outcome != VerificationOutcome.NOT_RUN:
                raise ValueError("INTEGRITY_FAILED: provenance must be NOT_RUN")
            if self.diagnostic != FeasibilityDiagnosticKey.INTEGRITY_FAILED:
                raise ValueError("INTEGRITY_FAILED: diagnostic must be INTEGRITY_FAILED")
            if self.provider_identity_matches != False:
                raise ValueError("INTEGRITY_FAILED: provider must match source (False)")
            if self.rating_status is not None:
                raise ValueError("INTEGRITY_FAILED: rating_status must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("INTEGRITY_FAILED: warnings must be empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("INTEGRITY_FAILED: blockers must be empty")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("INTEGRITY_FAILED: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("INTEGRITY_FAILED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("INTEGRITY_FAILED: failure_origin must be NONE")

        # PROVENANCE_FAILED
        elif self.disposition is Phase3Disposition.PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("PROVENANCE_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("PROVENANCE_FAILED: hash must be PASSED")
            if self.source_provenance_verification_outcome != VerificationOutcome.FAILED:
                raise ValueError("PROVENANCE_FAILED: provenance must be FAILED")
            if self.diagnostic != FeasibilityDiagnosticKey.PROVENANCE_FAILED:
                raise ValueError("PROVENANCE_FAILED: diagnostic must be PROVENANCE_FAILED")
            if self.rating_status is not None:
                raise ValueError("PROVENANCE_FAILED: rating_status must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("PROVENANCE_FAILED: warnings must be empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("PROVENANCE_FAILED: blockers must be empty")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("PROVENANCE_FAILED: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("PROVENANCE_FAILED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("PROVENANCE_FAILED: failure_origin must be NONE")

        # UNEVALUATED
        elif self.disposition is Phase3Disposition.UNEVALUATED:
            if self.diagnostic != FeasibilityDiagnosticKey.NONE:
                raise ValueError("UNEVALUATED: diagnostic must be NONE")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("UNEVALUATED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("UNEVALUATED: evidence must be None")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("UNEVALUATED: invalid evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("UNEVALUATED: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("UNEVALUATED: engineering values must be None")
            if len(self.warning_descriptors) != 0:
                raise ValueError("UNEVALUATED: warnings must be empty")
            if len(self.blocker_descriptors) != 0:
                raise ValueError("UNEVALUATED: blockers must be empty")
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("UNEVALUATED: failure_origin must be NONE")

        # RUNTIME_FAILED
        elif self.disposition is Phase3Disposition.RUNTIME_FAILED:
            if self.primary_engineering_value is not None or self.secondary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering values must be None")
            if self.failure_origin == FailureOrigin.PHASE2_EVALUATION:
                if self.source_evaluation_failure_digest is None:
                    raise ValueError("RUNTIME_FAILED(P2): source failure required")
                if self.phase3_failure_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): phase3 failure must be None")
                if self.source_candidate_evaluation_state != CandidateEvaluationState.RUNTIME_FAILED:
                    raise ValueError("RUNTIME_FAILED(P2): source must be RUNTIME_FAILED")
                if self.diagnostic != FeasibilityDiagnosticKey.PHASE2_RUNTIME_FAILED:
                    raise ValueError("RUNTIME_FAILED(P2): diagnostic must be PHASE2_RUNTIME_FAILED")
                valid = [(VerificationOutcome.NOT_RUN, VerificationOutcome.NOT_RUN),
                         (VerificationOutcome.ERROR, VerificationOutcome.NOT_RUN),
                         (VerificationOutcome.PASSED, VerificationOutcome.ERROR),
                         (VerificationOutcome.PASSED, VerificationOutcome.PASSED)]
                if (self.source_hash_verification_outcome, self.source_provenance_verification_outcome) not in valid:
                    raise ValueError("RUNTIME_FAILED(P2): invalid outcomes")
                if self.candidate_evaluation_identity_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): identity must be None")
                if self.verified_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): invalid evidence must be None")
                if len(self.warning_descriptors) != 0:
                    raise ValueError("RUNTIME_FAILED(P2): warnings must be empty")
                if len(self.blocker_descriptors) != 0:
                    raise ValueError("RUNTIME_FAILED(P2): blockers must be empty")
            elif self.failure_origin == FailureOrigin.PHASE3_CLASSIFICATION:
                if self.phase3_failure_digest is None:
                    raise ValueError("RUNTIME_FAILED(P3): phase3 failure required")
                if self.source_evaluation_failure_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P3): source failure must be None")
                if self.source_candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
                    raise ValueError("RUNTIME_FAILED(P3): source must be VERIFIED")
                if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                    raise ValueError("RUNTIME_FAILED(P3): hash must be PASSED")
                if self.source_provenance_verification_outcome != VerificationOutcome.PASSED:
                    raise ValueError("RUNTIME_FAILED(P3): provenance must be PASSED")
                if self.diagnostic != FeasibilityDiagnosticKey.PHASE3_RUNTIME_FAILED:
                    raise ValueError("RUNTIME_FAILED(P3): diagnostic must be PHASE3_RUNTIME_FAILED")
                if self.candidate_evaluation_identity_digest is None:
                    raise ValueError("RUNTIME_FAILED(P3): identity required (retained)")
                if self.verified_rating_evidence_digest is None:
                    raise ValueError("RUNTIME_FAILED(P3): evidence required (retained)")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P3): invalid evidence must be None")
            else:
                raise ValueError(f"RUNTIME_FAILED: unexpected failure_origin {self.failure_origin}")
        else:
            raise ValueError(f"unknown disposition: {self.disposition}")
        return self

    def _check_digest(self, d: str | None, name: str) -> None:
        if d is not None and not self.DIGEST_PATTERN.match(d):
            raise ValueError(f"{name}: invalid digest {d!r}")

    def _check_canonical(self, v: str, name: str) -> None:
        d = Decimal(v)
        if not d.is_finite():
            raise ValueError(f"{name}: not finite, got {v!r}")
        exp = canonical_decimal_string(d)
        if v != exp:
            raise ValueError(f"{name}: not canonical, got {v!r}, expected {exp!r}")

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("feasibility_digest mismatch")
```

### 9.2 Payload (excludes feasibility_digest)

```python
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
        "warning_descriptor_digests": [d.message_payload_digest for d in record.warning_descriptors],
        "blocker_descriptor_digests": [d.message_payload_digest for d in record.blocker_descriptors],
        "source_evaluation_failure_digest": record.source_evaluation_failure_digest,
        "phase3_failure_digest": record.phase3_failure_digest,
        "failure_origin": record.failure_origin.value,
    }
```

---

## 10. classify_candidate() (P0-2)

```python
def classify_candidate(input: Phase3CandidateClassificationInput) -> CandidateDispositionRecord:
    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence

    # 1. Non-VERIFIED → direct mapping
    if rec.candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
        return _map_non_verified(rec)

    # 2. Provider mismatch
    if not rec.provider_identity_matches:
        return _build_provider_mismatch(rec, evidence, input)

    # 3. rating_status is None → Phase 3 runtime failure
    if rec.rating_status is None:
        failure = RunFailure(
            code=ErrorCode.PHASE3_MISSING_RATING_STATUS,
            message="Verified record has no rating status.",
            traceback=None,
            context=(
                ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                ("evaluation_order_index", rec.evaluation_order_index),
            ),
        )
        return _build_phase3_runtime(rec, evidence, input, failure)

    # 4. BLOCKED / FAILED
    if rec.rating_status == RatingStatus.BLOCKED.value:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.RATING_BLOCKED)
    if rec.rating_status == RatingStatus.FAILED.value:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.RATING_FAILED)

    # 5. SUCCEEDED — trusted metrics required (P0-10)
    if evidence is None:
        failure = RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="Verified SUCCEEDED record has no evidence.",
            traceback=None, context=(),
        )
        return _build_phase3_runtime(rec, evidence, input, failure)
    if evidence.heat_duty_w is None or evidence.hot_outlet_temperature_k is None or evidence.cold_outlet_temperature_k is None:
        failure = RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="Verified SUCCEEDED record missing required thermal metrics.",
            traceback=None, context=(),
        )
        return _build_phase3_runtime(rec, evidence, input, failure)
    try:
        heat_w = to_canonical_decimal(evidence.heat_duty_w)
        area_m2 = to_canonical_decimal(evidence.area_outer_m2)
        hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
        cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
        hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
        cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)
    except (ValueError, TypeError):
        failure = RunFailure(
            code=ErrorCode.PHASE3_TRUSTED_EVIDENCE_INCOMPLETE,
            message="Non-finite or invalid thermal metric in SUCCEEDED evidence.",
            traceback=None, context=(),
        )
        return _build_phase3_runtime(rec, evidence, input, failure)

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
        dt1 = hot_in - cold_in
        dt2 = hot_out - cold_out
    else:
        dt1 = hot_in - cold_out
        dt2 = hot_out - cold_in
    min_dt = min(dt1, dt2)
    min_req = to_canonical_decimal(sizing.minimum_terminal_delta_t)
    if min_dt < min_req:
        return _build_infeasible(rec, evidence, input, FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE)

    # 8. FEASIBLE
    return _build_feasible(rec, evidence, input)
```

### Message canonicalization in builder helpers

Each builder calls `canonicalize_phase3_messages_or_failure()` for warnings and blockers. If it returns a `RunFailure`, the candidate becomes Phase 3 RUNTIME_FAILED (not silently filtered):

```python
def _canonicalize_or_fail(
    warnings: tuple[EngineeringMessage, ...],
    blockers: tuple[EngineeringMessage, ...],
    rec: CandidateEvaluationRecord,
    input: Phase3CandidateClassificationInput,
) -> tuple[tuple[Phase3MessageDescriptor, ...], tuple[Phase3MessageDescriptor, ...], CandidateDispositionRecord | None]:
    w_result = canonicalize_phase3_messages_or_failure(
        warnings, "warning", rec.source_qualified_candidate_id,
        rec.evaluation_order_index, input.source_record_descriptor_digest)
    if isinstance(w_result, RunFailure):
        return (), (), _build_phase3_runtime(rec, rec.verified_rating_evidence, input, w_result)
    b_result = canonicalize_phase3_messages_or_failure(
        blockers, "blocker", rec.source_qualified_candidate_id,
        rec.evaluation_order_index, input.source_record_descriptor_digest)
    if isinstance(b_result, RunFailure):
        return (), (), _build_phase3_runtime(rec, rec.verified_rating_evidence, input, b_result)
    return w_result, b_result, None
```

---

## 11. RankedCandidateRecord (P0-6)

### 11.1 Model

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
        if self.rank < 1:
            raise ValueError("rank must be ≥ 1")
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id must be non-empty")
        for val, name in [(self.primary_objective_value, "primary"),
                          (self.secondary_tie_break_value, "secondary")]:
            d = Decimal(val)
            if not d.is_finite():
                raise ValueError(f"{name}: not finite, got {val!r}")
            if canonical_decimal_string(d) != val:
                raise ValueError(f"{name}: not canonical, got {val!r}")
        if self.optimization_objective is OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            if self.primary_objective_field != "area_outer_m2":
                raise ValueError("MIN_OA: primary must be area_outer_m2")
            if self.secondary_tie_break_field != "effective_length_m_canonical":
                raise ValueError("MIN_OA: secondary must be effective_length_m_canonical")
        else:
            if self.primary_objective_field != "effective_length_m_canonical":
                raise ValueError("MIN_LEN: primary must be effective_length_m_canonical")
            if self.secondary_tie_break_field != "area_outer_m2":
                raise ValueError("MIN_LEN: secondary must be area_outer_m2")
        for dgst, name in [(self.candidate_evaluation_identity_digest, "identity"),
                           (self.verified_rating_evidence_digest, "evidence"),
                           (self.feasibility_digest, "feasibility"),
                           (self.ranked_record_digest, "ranked")]:
            if not self.DIGEST_PATTERN.match(dgst):
                raise ValueError(f"{name}: invalid digest {dgst!r}")
        return self

    def verify_digest(self) -> bool:
        return self.ranked_record_digest == sha256_digest(ranked_candidate_record_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("ranked_record_digest mismatch")
```

### 11.2 Expected payload

```python
def expected_ranked_candidate_record_payload(
    rank: int,
    disposition: CandidateDispositionRecord,
    candidate: ManufacturableCandidate,
    optimization_objective: OptimizationObjective,
) -> dict[str, object]:
    if optimization_objective == OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
        primary_val = disposition.primary_engineering_value
        primary_field = "area_outer_m2"
        secondary_val = canonical_decimal_string(canonical_decimal(Decimal(candidate.effective_length_m_canonical)))
        secondary_field = "effective_length_m_canonical"
    else:
        primary_val = canonical_decimal_string(canonical_decimal(Decimal(candidate.effective_length_m_canonical)))
        primary_field = "effective_length_m_canonical"
        secondary_val = disposition.primary_engineering_value
        secondary_field = "area_outer_m2"
    return {
        "rank": rank,
        "source_qualified_candidate_id": disposition.source_qualified_candidate_id,
        "optimization_objective": optimization_objective.value,
        "primary_objective_value": primary_val,
        "primary_objective_field": primary_field,
        "secondary_tie_break_value": secondary_val,
        "secondary_tie_break_field": secondary_field,
        "candidate_evaluation_identity_digest": disposition.candidate_evaluation_identity_digest,
        "verified_rating_evidence_digest": disposition.verified_rating_evidence_digest,
        "feasibility_digest": disposition.feasibility_digest,
    }
```

### 11.3 Payload (excludes ranked_record_digest)

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

---

## 12. OptimizationResult

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
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if self.requested_top_n < 1:
            raise ValueError("requested_top_n must be ≥ 1")
        for name in ["total_candidate_count", "feasible_candidate_count",
                      "infeasible_candidate_count", "provider_mismatch_count",
                      "integrity_failed_count", "provenance_failed_count",
                      "runtime_failed_count", "unevaluated_count",
                      "phase2_verified_record_count", "phase2_integrity_invalid_record_count",
                      "phase2_runtime_failed_record_count", "phase2_unevaluated_record_count",
                      "runtime_failed_from_phase2_verified_count",
                      "runtime_failed_from_phase2_runtime_failed_count"]:
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be ≥ 0")
        d3 = (self.feasible_candidate_count + self.infeasible_candidate_count +
              self.provider_mismatch_count + self.integrity_failed_count +
              self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count)
        if d3 != self.total_candidate_count:
            raise ValueError("Phase 3 disposition counts != total")
        p2 = (self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count +
              self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count)
        if p2 != self.total_candidate_count:
            raise ValueError("Phase 2 state counts != total")
        if self.runtime_failed_count != (self.runtime_failed_from_phase2_verified_count +
                                          self.runtime_failed_from_phase2_runtime_failed_count):
            raise ValueError("runtime_failed cross-count mismatch")
        if self.phase2_verified_record_count != (self.feasible_candidate_count + self.infeasible_candidate_count +
                                                  self.provider_mismatch_count + self.runtime_failed_from_phase2_verified_count):
            raise ValueError("phase2_verified cross-count mismatch")
        if self.phase2_integrity_invalid_record_count != (self.integrity_failed_count + self.provenance_failed_count):
            raise ValueError("phase2_integrity_invalid cross-count mismatch")
        if self.phase2_runtime_failed_record_count != self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("phase2_runtime_failed cross-count mismatch")
        if self.phase2_unevaluated_record_count != self.unevaluated_count:
            raise ValueError("phase2_unevaluated cross-count mismatch")
        N, F, TN = self.total_candidate_count, self.feasible_candidate_count, min(self.requested_top_n, self.feasible_candidate_count)
        if len(self.ordered_disposition_record_digests) != N:
            raise ValueError("disposition digests length != total")
        if len(self.ordered_ranked_record_digests) != F:
            raise ValueError("ranked digests length != feasible")
        if len(self.ordered_top_n_record_digests) != TN:
            raise ValueError("Top-N digests length != min(req, feasible)")
        if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]:
            raise ValueError("Top-N must be exact prefix of ranked")
        expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, self.result_hash))
        if self.optimization_result_id != expected_id:
            raise ValueError("optimization_result_id mismatch")
        return self

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

Three-layer hash: `result_core_hash = sha256_digest(result_core_payload(result))`; `provenance_digest = graph.compute_hash()`; `result_hash = sha256_digest({"result_core_hash": ..., "provenance_digest": ...})`; `optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))`.

---

## 13. Result warning/blocker aggregation (P0-4)

```python
def build_result_message_digest_tuples(
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    stop_index: int | None,
) -> tuple[list[str], list[str]]:
    # Collect all warning descriptors from dispositions
    all_warning_descriptors: list[Phase3MessageDescriptor] = []
    for dr in disposition_records:
        all_warning_descriptors.extend(dr.warning_descriptors)

    # Strict-stop warning (if PARTIAL)
    if stop_index is not None:
        ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
        if ss_warning is None:
            raise RuntimeError("strict-stop warning builder returned None for PARTIAL input")
        ss_result = build_engineering_message_descriptor(ss_warning)
        if isinstance(ss_result, RunFailure):
            raise RuntimeError("strict-stop warning descriptor construction failed")
        all_warning_descriptors.append(ss_result)

    # Sort all warnings by owner_sort_key (stable)
    all_warning_descriptors.sort(key=lambda d: d.owner_sort_key)
    warning_digests = [d.message_payload_digest for d in all_warning_descriptors]

    # Blockers similarly (no strict-stop in blockers)
    all_blocker_descriptors: list[Phase3MessageDescriptor] = []
    for dr in disposition_records:
        all_blocker_descriptors.extend(dr.blocker_descriptors)
    all_blocker_descriptors.sort(key=lambda d: d.owner_sort_key)
    blocker_digests = [d.message_payload_digest for d in all_blocker_descriptors]

    return (warning_digests, blocker_digests)
```

No `pass` statements, no `...` ellipsis.

---

## 14. Strict-stop warning (P0-5)

```python
def _build_strict_stop_warning(evaluation_input, stop_index):
    if stop_index is None:
        return None
    record = evaluation_input.evaluation_records[stop_index]
    return EngineeringMessage(
        code=ErrorCode.PHASE3_STRICT_STOP,
        severity=EngineeringMessageSeverity.WARNING,
        message="Phase 2 strict-stop occurred; records after index are UNEVALUATED.",
        source_module="hexagent.optimization.phase3_input",
        affected_paths=(),
        context=(
            ("stop_index", stop_index),
            ("source_qualified_candidate_id", record.source_qualified_candidate_id),
            ("source_state", record.candidate_evaluation_state.value),
        ),
    )
```

External verifier check:

```python
stop_index = _find_stop_index(evaluation_input)
if stop_index is None:
    expected_strict_stop_digest = None
    occurrences = 0
else:
    ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
    if ss_warning is None:
        raise RuntimeError("strict-stop warning builder returned None for PARTIAL input")
    ss_desc = build_engineering_message_descriptor(ss_warning)
    if isinstance(ss_desc, RunFailure):
        raise RuntimeError("strict-stop descriptor construction failed")
    expected_strict_stop_digest = ss_desc.message_payload_digest
    occurrences = sum(1 for d in result.ordered_warning_digests if d == expected_strict_stop_digest)
if stop_index is None:
    if occurrences != 0:
        raise ValueError("strict-stop warning present but no strict-stop exists")
else:
    if occurrences != 1:
        raise ValueError(f"strict-stop warning: expected 1 occurrence, got {occurrences}")
```

---

## 15. External verifier

Key sections (full verifier defined in full contract):

- Input binding check
- Objective/Top-N binding (§11)
- Per-index disposition binding with source digest verification
- **Re-run classifier** — compare full `candidate_disposition_payload()` per index
- Ranked record verification with `expected_ranked_candidate_record_payload()` recomputation
- Sort key recomputation
- Top-N exact prefix
- **Independent count recomputation** (`_verify_all_counts`)
- Termination status (correct condition/message)
- **Full warning/blocker aggregation** (`build_result_message_digest_tuples`)
- Hash verification (core → provenance → envelope → UUID5)
- Digest format and uniqueness checks

---

## 16. Provenance (P0-7, P0-8)

### 16.1 Role-qualified UUID

```python
def expected_phase3_node_id(expected: ExpectedPhase3ProvenanceNode) -> UUID:
    name = f"{expected.role}:{expected.node_type.value}:{expected.payload_hash}"
    return uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, name)
```

### 16.2 Node count verification

```python
N = len(disposition_records)
F = len(ranked_records)
expected_node_count = 8 + N + F
if len(graph.nodes) != expected_node_count:
    raise ValueError(f"provenance node count {len(graph.nodes)} != {expected_node_count}")
```

### 16.3 Disposition→Ranked by candidate identity (P0-7)

```python
feasible_disposition_by_key: dict[tuple[str, str], str] = {}
for i, dr in enumerate(disposition_records):
    if dr.disposition is Phase3Disposition.FEASIBLE:
        key = (dr.source_qualified_candidate_id, dr.feasibility_digest)
        feasible_disposition_by_key[key] = f"disposition[{i}]"

edges: list[tuple[str, str, str]] = []
for rank_idx, rr in enumerate(ranked_records):
    key = (rr.source_qualified_candidate_id, rr.feasibility_digest)
    disp_role = feasible_disposition_by_key.get(key)
    if disp_role is None:
        raise ValueError(f"ranked record {rank_idx}: no matching FEASIBLE disposition")
    edges.append((_uid(disp_role), _uid(f"ranked[{rank_idx}]"), Phase3ProvenanceRelation.RANKED.value))
```

---

## 17. Implementation boundary

New files: `phase3_input.py`, `feasibility.py`, `ranking.py`, `result.py`, test files.
Modified: `messages.py` (add error codes), `evaluation.py` (export descriptor builder).
Untouched: all Phase 1/2 modules, TASK-008, catalog.

---

## 18. Test matrix

- One-shot factory: `missing feasibility_digest never constructed`; `no object.__setattr__ digest backfill`
- Warning canonicalization failure → P3 RUNTIME_FAILED (not silently filtered)
- Blockercanonicalization failure → P3 RUNTIME_FAILED
- `message_payload_digest is None` → P3 RUNTIME_FAILED (deterministically)
- Each original message context traversed exactly once
- External verifier reuses evidence binding; does not re-canonicalize context
- Result warning aggregation contains all candidate warnings; duplicates preserved
- Global `owner_sort_key` ordering executable
- COMPLETE does not hash `None` warning
- PARTIAL strict-stop warning exactly once
- Full ranked payload `expected_ranked_candidate_record_payload()` recomputation
- Tampered ranked primary/secondary value or field name rejected
- Provenance disposition→ranked mapping survives rank reorder
- Node count exactly `8+N+F`
- Duplicate expected provenance node ID rejected
- Role-qualified UUID deterministic
- All `Phase3Disposition`, `FeasibilityDiagnosticKey`, `TerminationStatus`, `FailureOrigin`, `Phase3ProvenanceRelation` enum values exact
- All new `ErrorCode` values exact
- SUCCEEDED missing `heat_duty_w`/`hot_outlet_temperature_k`/`cold_outlet_temperature_k` → Phase 3 RUNTIME_FAILED with `PHASE3_TRUSTED_EVIDENCE_INCOMPLETE`
- SUCCEEDED non-finite metrics → Phase 3 RUNTIME_FAILED
- Exact diagnostic per disposition branch (`INTEGRITY_FAILED`, `PROVENANCE_FAILED`, `PHASE2_RUNTIME_FAILED`, `PHASE3_RUNTIME_FAILED`)
- Phase 2 runtime failure context tampering rejected (full `run_failure_payload()` verification)
- `Phase3EvaluationInput.schema_version=2` rejected
- No `pass`, no `...`, no `object.__setattr__` in normative helpers

---

## 19. Acceptance criteria and authorization

Acceptance criteria unchanged from prior round. Design review: **CHANGES REQUIRED — PENDING RE-REVIEW**. Frozen SHA: **NOT ESTABLISHED**. Implementation: **NOT AUTHORIZED**.
