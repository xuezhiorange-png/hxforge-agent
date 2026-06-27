# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Milestone:** M2. Priority: P0
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> ⚠️ Design contract for review only. No implementation until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope

Phase 3 consumes `tuple[CandidateEvaluationRecord, ...]` via `Phase3EvaluationInput` and produces a deterministic `OptimizationResult` with typed disposition records, ranked records, hash, and provenance.

---

## 2. Non-goals

TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver, candidate generation, catalog schema changes, Phase 2 artifact mutation, re-running TASK-008, recovering strict-stop.

---

## 3. Phase3EvaluationInput (P0-1)

### 3.1 Model

```python
class Phase3EvaluationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: int = 1
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
def evaluation_record_descriptor_payload(
    record: CandidateEvaluationRecord,
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

Digest computation (no circularity):
```
evaluation_record_descriptor_digest(record) = sha256_digest(evaluation_record_descriptor_payload(record))
evaluation_input_digest(input)            = sha256_digest(evaluation_input_payload(input))
```

Neither payload contains its own digest field.

### 3.3 13-step verify_or_raise()

**Step 1 — Type verification:** Each field is exact expected type.
**Step 2 — materialization_result.verify_or_raise():** Delegate.
**Step 3 — Sizing identity digest:** Verify `sizing_request_identity_digest == identity.sizing_request_identity_digest`.
**Step 4 — candidate_set.verify_digest():** Must return True.
**Step 5 — sizing_gate.verify_digest():** Must return True.
**Step 6 — Candidate-set ↔ sizing binding:** `candidate_set.sizing_request_identity_digest == sizing_request_identity_digest`.
**Step 7 — Gate ↔ candidate-set binding:** `gate.gate_digest == candidate_set.passed_gate_digest`.
**Step 8 — Count parity:** `evaluation_record_count == len(records) == len(candidates) == len(descriptor_digests)`.
**Step 9 — Record ↔ candidate one-to-one binding:** For each `i`: `record.evaluation_order_index == i`, `candidate.evaluation_order_index == i`, `record.source_qualified_candidate_id == candidate.source_qualified_candidate_id == ordered_candidate_ids[i]`. No missing/extra/duplicate/displaced/skipped.
**Step 10 — Exhaustive state verification:** Every record field matches an exact production path (§4.1 matrix).
**Step 11 — Strict-stop invariant:** Verify `stop_index` rule (§5).
**Step 12 — Descriptor digest verification:** For each `i`, `sha256_digest(evaluation_record_descriptor_payload(record[i]))` matches `ordered_evaluation_record_descriptor_digests[i]`.
**Step 13 — evaluation_input_digest verification:** Recompute and compare.

All failures raise `ValueError` with fixed deterministic message. No `str(exc)`.

---

## 4. Exhaustive Phase 2 constructor matrix (P0-2)

Each row is a real production path from `evaluation.py`. Every field is frozen.

### 4.1 VERIFIED (1 path — lines 2634–2646)

```
state=VERIFIED, feasible=False,
feasibility_status=NOT_EVALUATED or PROVIDER_IDENTITY_MISMATCH,
identity=eval_identity, claimed_audit=None, verified_evidence=evidence,
invalid_evidence=None, provider_matches=bool, eval_failure=None,
rating_status=RatingStatus.value or None,
hash=PASSED, provenance=PASSED
```

Provider parity (VERIFIED only):
```python
provider_identity_matches == True  ⇔  feasibility_status == NOT_EVALUATED
provider_identity_matches == False ⇔  feasibility_status == PROVIDER_IDENTITY_MISMATCH
```

### 4.2 INTEGRITY_INVALID (2 paths)

| Field | Hash false (line 2333) | Provenance false (line 2388) |
|---|---|---|
| state | INTEGRITY_INVALID | INTEGRITY_INVALID |
| feasible | False | False |
| feasibility_status | NOT_EVALUATED | NOT_EVALUATED |
| identity | None | None |
| claimed_audit | present | present |
| verified_evidence | None | None |
| invalid_evidence | present | present |
| provider_matches | **False** | **True** (default) |
| eval_failure | None | None |
| rating_status | None | None |
| hash_outcome | **FAILED** | **PASSED** |
| provenance_outcome | **NOT_RUN** | **FAILED** |

### 4.3 RUNTIME_FAILED (10 paths)

| # | Source | hash | prov | audit | provider | eval_failure |
|---|---|---|---|---|---|---|
| 1 | Type mismatch (2277) | NOT_RUN | NOT_RUN | Yes | True (default) | Yes |
| 2 | verify_hash raised (2303) | ERROR | NOT_RUN | Yes | True (default) | Yes |
| 3 | verify_provenance raised (2358) | PASSED | ERROR | Yes | True (default) | Yes |
| 4 | Evidence extraction failed (2414) | PASSED | PASSED | Yes | True (default) | Yes |
| 5 | Context canonicalization (2478) | PASSED | PASSED | **None** | True (default) | Yes |
| 6 | Warning canonicalization (2511) | PASSED | PASSED | **None** | True (default) | Yes |
| 7 | Blocker canonicalization (2543) | PASSED | PASSED | **None** | True (default) | Yes |
| 8 | RunFailure canonicalization (2575) | PASSED | PASSED | **None** | True (default) | Yes |
| 9 | Identity construction failed (2611) | PASSED | PASSED | **None** | True (default) | Yes |
| 10 | Outer catch-all (2672) | PASSED | PASSED | **None** | True (default) | Yes |

All: identity=None, verified_evidence=None, invalid_evidence=None, rating_status=None, feasibility_status=NOT_EVALUATED.

### 4.4 UNEVALUATED

```
state=UNEVALUATED, feasible=False, feasibility_status=NOT_EVALUATED,
identity=None, claimed_audit=None, verified_evidence=None,
invalid_evidence=None, provider_matches=True (default), eval_failure=None,
rating_status=None, hash=NOT_RUN, provenance=NOT_RUN
```

---

## 5. Strict-stop

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. Invariant: indices < stop_index must be VERIFIED; index == stop_index is INTEGRITY_INVALID or RUNTIME_FAILED; indices > stop_index must be UNEVALUATED.

COMPLETE = no strict-stop. PARTIAL = strict-stop occurred.

---

## 6. Decimal canonicalization

```python
def to_canonical_decimal(value: float | int | Decimal) -> Decimal:
    if type(value) is bool:
        raise TypeError("bool is not a valid numeric value")
    if type(value) is Decimal:
        return canonical_decimal(value)
    if type(value) is int:
        return canonical_decimal(Decimal(value))
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"numeric value must be finite, got {value}")
        return canonical_decimal(Decimal(str(value)))
    raise TypeError(f"unsupported numeric type: {type(value).__name__}")

def canonical_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal:
        raise TypeError(...)
    if not value.is_finite():
        raise ValueError(...)
    n = value.normalize()
    return Decimal("0") if n.is_zero() else n

def canonical_decimal_string(value: Decimal) -> str:
    return format(canonical_decimal(value), "f")
```

---

## 7. FEASIBLE classifier (P0-3)

### 7.1 Typed classification input

```python
class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    source_record: CandidateEvaluationRecord
    source_record_descriptor_digest: str
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str
    required_duty_w: float | int | Decimal
    duty_absolute_tolerance_w: float | int | Decimal
    duty_relative_tolerance: float | int | Decimal
    minimum_terminal_delta_t_k: float | int | Decimal
    flow_arrangement: FlowArrangement
```

Data sources:
- `required_duty_w`, `duty_absolute_tolerance_w`, `duty_relative_tolerance`, `minimum_terminal_delta_t_k` → `SizingRequestIdentity`
- `heat_duty_w`, `area_outer_m2`, `hot_outlet_temperature_k`, `cold_outlet_temperature_k` → `VerifiedRatingEvidenceSnapshot` (from source_record)
- `hot_inlet_temperature_k`, `cold_inlet_temperature_k`, `flow_arrangement` → `SizingRequestIdentity`
- `effective_length_m_canonical` → `ManufacturableCandidate`

### 7.2 Classification function (produces CandidateDispositionRecord)

```python
def classify_candidate(
    input: Phase3CandidateClassificationInput,
) -> CandidateDispositionRecord:
    ...
```

Reads thermal metrics **only** when `input.source_record.rating_status == RatingStatus.SUCCEEDED.value`. BLOCKED/FAILED do not read successful-result metrics.

### 7.3 Exact FEASIBLE predicate

```python
is_feasible = (
    source.state == VERIFIED
    and provider_matches == True
    and rating_status == SUCCEEDED.value
    and duty_satisfied == True
    and terminal_delta_t_satisfied == True
)
```

### 7.4 Diagnostic precedence (single final diagnostic per candidate)

1. `PROVIDER_IDENTITY_MISMATCH` — provider_matches=False
2. `RATING_BLOCKED` — rating_status=BLOCKED (no thermal metrics read)
3. `RATING_FAILED` — rating_status=FAILED (no thermal metrics read)
4. `DUTY_SHORTFALL` — SUCCEEDED + duty not satisfied
5. `TERMINAL_DELTA_T_INADEQUATE` — SUCCEEDED + duty OK + delta-T not satisfied

---

## 8. Counts

```
Phase 3 disposition (disjoint, sum = total):
    total = feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated

Phase 2 state audit (from source records):
    phase2_verified = count(state==VERIFIED)
    phase2_integrity_invalid = count(state==INTEGRITY_INVALID)
    phase2_runtime_failed = count(state==RUNTIME_FAILED)
    phase2_unevaluated = count(state==UNEVALUATED)
    phase2_verified + phase2_integrity_invalid + phase2_runtime_failed + phase2_unevaluated = total

Cross-equations:
    runtime_failed = runtime_failed_from_phase2_verified + runtime_failed_from_phase2_runtime_failed
    phase2_verified = feasible + infeasible + provider_mismatch + runtime_failed_from_phase2_verified
    phase2_integrity_invalid = integrity_failed + provenance_failed
    phase2_runtime_failed = runtime_failed_from_phase2_runtime_failed
    phase2_unevaluated = unevaluated
```

---

## 9. CandidateDispositionRecord (P0-4)

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

    ordered_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]
    failure_digest: str | None

    feasibility_digest: str

    DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

    def _check_digest(self, d: str | None, name: str) -> None:
        if d is not None and not self.DIGEST.match(d):
            raise ValueError(f"{name}: invalid digest {d!r}")

    def _check_canonical(self, v: str, name: str) -> None:
        d = Decimal(v)
        if not d.is_finite():
            raise ValueError(f"{name}: not finite, got {v!r}")
        exp = canonical_decimal_string(d)
        if v != exp:
            raise ValueError(f"{name}: not canonical, got {v!r}, expected {exp!r}")

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if self.evaluation_order_index < 0:
            raise ValueError("evaluation_order_index must be ≥ 0")

        for d, n in [(self.source_record_descriptor_digest, "source"),
                      (self.feasibility_digest, "feasibility")]:
            if not self.DIGEST.match(d):
                raise ValueError(f"{n}: invalid digest {d!r}")
        for d in self.ordered_warning_digests:
            self._check_digest(d, "warning")
        for d in self.ordered_blocker_digests:
            self._check_digest(d, "blocker")
        self._check_digest(self.failure_digest, "failure")
        self._check_digest(self.candidate_evaluation_identity_digest, "identity")
        self._check_digest(self.verified_rating_evidence_digest, "verified_evidence")
        self._check_digest(self.invalid_rating_evidence_digest, "invalid_evidence")

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
                raise ValueError(f"FEASIBLE: rating_status must be SUCCEEDED, got {self.rating_status!r}")
            if self.diagnostic != FeasibilityDiagnosticKey.NONE:
                raise ValueError(f"FEASIBLE: diagnostic must be NONE, got {self.diagnostic}")
            if self.candidate_evaluation_identity_digest is None:
                raise ValueError("FEASIBLE: identity digest required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("FEASIBLE: evidence digest required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("FEASIBLE: invalid evidence must be None")
            if self.primary_engineering_value is None:
                raise ValueError("FEASIBLE: primary value required")
            if self.secondary_engineering_value is None:
                raise ValueError("FEASIBLE: secondary value required")
            self._check_canonical(self.primary_engineering_value, "primary")
            self._check_canonical(self.secondary_engineering_value, "secondary")
            if self.failure_digest is not None:
                raise ValueError("FEASIBLE: failure must be None")

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
                raise ValueError("INFEASIBLE: identity digest required")
            if self.verified_rating_evidence_digest is None:
                raise ValueError("INFEASIBLE: evidence digest required")
            if self.invalid_rating_evidence_digest is not None:
                raise ValueError("INFEASIBLE: invalid evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("INFEASIBLE: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("INFEASIBLE: engineering values must be None")
            if self.failure_digest is not None:
                raise ValueError("INFEASIBLE: failure must be None")
            if self.diagnostic == FeasibilityDiagnosticKey.NONE:
                raise ValueError("INFEASIBLE: diagnostic must be non-NONE")
            if self.rating_status == RatingStatus.SUCCEEDED.value:
                if self.diagnostic not in (FeasibilityDiagnosticKey.DUTY_SHORTFALL,
                                           FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE):
                    raise ValueError("INFEASIBLE+SUCCEEDED: diagnostic must be DUTY_SHORTFALL or TERMINAL_DELTA_T_INADEQUATE")
            elif self.rating_status == RatingStatus.BLOCKED.value:
                if self.diagnostic != FeasibilityDiagnosticKey.RATING_BLOCKED:
                    raise ValueError("INFEASIBLE+BLOCKED: diagnostic must be RATING_BLOCKED")
            elif self.rating_status == RatingStatus.FAILED.value:
                if self.diagnostic != FeasibilityDiagnosticKey.RATING_FAILED:
                    raise ValueError("INFEASIBLE+FAILED: diagnostic must be RATING_FAILED")
            else:
                raise ValueError(f"INFEASIBLE: unexpected rating_status {self.rating_status!r}")

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
            if self.primary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("PROVIDER_MISMATCH: engineering values must be None")
            if self.failure_digest is not None:
                raise ValueError("PROVIDER_MISMATCH: failure must be None")

        # INTEGRITY_FAILED
        elif self.disposition is Phase3Disposition.INTEGRITY_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("INTEGRITY_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != VerificationOutcome.FAILED:
                raise ValueError("INTEGRITY_FAILED: hash must be FAILED")
            if self.source_provenance_verification_outcome != VerificationOutcome.NOT_RUN:
                raise ValueError("INTEGRITY_FAILED: provenance must be NOT_RUN")
            if self.invalid_rating_evidence_digest is None:
                raise ValueError("INTEGRITY_FAILED: invalid evidence required")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("INTEGRITY_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("INTEGRITY_FAILED: verified evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("INTEGRITY_FAILED: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("INTEGRITY_FAILED: engineering values must be None")
            if self.failure_digest is not None:
                raise ValueError("INTEGRITY_FAILED: failure must be None")

        # PROVENANCE_FAILED
        elif self.disposition is Phase3Disposition.PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("PROVENANCE_FAILED: source must be INTEGRITY_INVALID")
            if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                raise ValueError("PROVENANCE_FAILED: hash must be PASSED")
            if self.source_provenance_verification_outcome != VerificationOutcome.FAILED:
                raise ValueError("PROVENANCE_FAILED: provenance must be FAILED")
            if self.invalid_rating_evidence_digest is None:
                raise ValueError("PROVENANCE_FAILED: invalid evidence required")
            if self.candidate_evaluation_identity_digest is not None:
                raise ValueError("PROVENANCE_FAILED: identity must be None")
            if self.verified_rating_evidence_digest is not None:
                raise ValueError("PROVENANCE_FAILED: verified evidence must be None")
            if self.primary_engineering_value is not None:
                raise ValueError("PROVENANCE_FAILED: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("PROVENANCE_FAILED: engineering values must be None")
            if self.failure_digest is not None:
                raise ValueError("PROVENANCE_FAILED: failure must be None")

        # UNEVALUATED
        elif self.disposition is Phase3Disposition.UNEVALUATED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.UNEVALUATED:
                raise ValueError("UNEVALUATED: source must be UNEVALUATED")
            if self.source_hash_verification_outcome != VerificationOutcome.NOT_RUN:
                raise ValueError("UNEVALUATED: hash must be NOT_RUN")
            if self.source_provenance_verification_outcome != VerificationOutcome.NOT_RUN:
                raise ValueError("UNEVALUATED: provenance must be NOT_RUN")
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
            if self.failure_digest is not None:
                raise ValueError("UNEVALUATED: failure must be None")

        # RUNTIME_FAILED
        elif self.disposition is Phase3Disposition.RUNTIME_FAILED:
            if self.failure_digest is None:
                raise ValueError("RUNTIME_FAILED: failure_digest required")
            if self.primary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering values must be None")
            if self.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED:
                if self.source_hash_verification_outcome != VerificationOutcome.PASSED:
                    raise ValueError("RUNTIME_FAILED from VERIFIED: hash must be PASSED")
                if self.source_provenance_verification_outcome != VerificationOutcome.PASSED:
                    raise ValueError("RUNTIME_FAILED from VERIFIED: provenance must be PASSED")
                # Identity/evidence digests: retained to bind trusted input that failed during Phase 3
            elif self.source_candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED:
                valid_outcomes = [
                    (VerificationOutcome.NOT_RUN, VerificationOutcome.NOT_RUN),
                    (VerificationOutcome.ERROR, VerificationOutcome.NOT_RUN),
                    (VerificationOutcome.PASSED, VerificationOutcome.ERROR),
                    (VerificationOutcome.PASSED, VerificationOutcome.PASSED),
                ]
                if (self.source_hash_verification_outcome, self.source_provenance_verification_outcome) not in valid_outcomes:
                    raise ValueError(f"RUNTIME_FAILED from RUNTIME_FAILED: invalid outcomes ({self.source_hash_verification_outcome}/{self.source_provenance_verification_outcome})")
                if self.candidate_evaluation_identity_digest is not None:
                    raise ValueError("RUNTIME_FAILED (Phase 2): identity must be None")
                if self.verified_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED (Phase 2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED (Phase 2): invalid evidence must be None")
            else:
                raise ValueError(f"RUNTIME_FAILED: invalid source state {self.source_candidate_evaluation_state}")
        else:
            raise ValueError(f"unknown disposition: {self.disposition}")

        return Self

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
        "ordered_warning_digests": list(record.ordered_warning_digests),
        "ordered_blocker_digests": list(record.ordered_blocker_digests),
        "failure_digest": record.failure_digest,
    }
```

---

## 10. RankedCandidateRecord

### 10.1 Model

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

    DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> Self:
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
            if not self.DIGEST.match(dgst):
                raise ValueError(f"{name}: invalid digest {dgst!r}")
        return Self

    def verify_digest(self) -> bool:
        return self.ranked_record_digest == sha256_digest(ranked_candidate_record_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("ranked_record_digest mismatch")
```

### 10.2 Payload (excludes ranked_record_digest)

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

## 11. OptimizationResult

### 11.1 Model

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: int = 1
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
```

### 11.2 Core payload (explicit every field)

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

Excluded: `optimization_result_id`, `result_core_hash`, `provenance_digest`, `result_hash`.

### 11.3 Three-layer hash

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace

result_core_hash = sha256_digest(result_core_payload(result))
provenance_digest = ProvenanceGraph.compute_hash()
result_hash = sha256_digest({"result_core_hash": result_core_hash, "provenance_digest": provenance_digest})
optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))
```

The namespaces are distinct: `PHASE3_RESULT_NAMESPACE` for `optimization_result_id`, `PHASE3_PROVENANCE_NAMESPACE` for provenance node UUIDs.

### 11.4 Lightweight model validator

```python
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

@model_validator(mode="after")
def _validate(self) -> Self:
    if self.schema_version != 1:
        raise ValueError("schema_version must be 1")
    if self.requested_top_n < 1:
        raise ValueError("requested_top_n must be ≥ 1")
    # All counts non-negative
    for name in ["total_candidate_count", "feasible_candidate_count", "infeasible_candidate_count",
                  "provider_mismatch_count", "integrity_failed_count", "provenance_failed_count",
                  "runtime_failed_count", "unevaluated_count", "phase2_verified_record_count",
                  "phase2_integrity_invalid_record_count", "phase2_runtime_failed_record_count",
                  "phase2_unevaluated_record_count", "runtime_failed_from_phase2_verified_count",
                  "runtime_failed_from_phase2_runtime_failed_count"]:
        if getattr(self, name) < 0:
            raise ValueError(f"{name} must be ≥ 0")
    # Phase 3 disposition sum to total
    d3 = (self.feasible_candidate_count + self.infeasible_candidate_count +
          self.provider_mismatch_count + self.integrity_failed_count +
          self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count)
    if d3 != self.total_candidate_count:
        raise ValueError("Phase 3 disposition counts != total")
    # Phase 2 state sum to total
    p2 = (self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count +
          self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count)
    if p2 != self.total_candidate_count:
        raise ValueError("Phase 2 state counts != total")
    # Cross-equations
    if self.runtime_failed_count != (self.runtime_failed_from_phase2_verified_count +
                                      self.runtime_failed_from_phase2_runtime_failed_count):
        raise ValueError("runtime_failed cross-count mismatch")
    # Length invariants
    N = self.total_candidate_count
    F = self.feasible_candidate_count
    TN = min(self.requested_top_n, F)
    if len(self.ordered_disposition_record_digests) != N:
        raise ValueError("disposition digests length != total")
    if len(self.ordered_ranked_record_digests) != F:
        raise ValueError("ranked digests length != feasible")
    if len(self.ordered_top_n_record_digests) != TN:
        raise ValueError("Top-N digests length != min(req, feasible)")
    if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N must be exact prefix of ranked")
    # UUID5
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, self.result_hash))
    if self.optimization_result_id != expected_id:
        raise ValueError("optimization_result_id mismatch")
    return Self
```

### 11.5 All digest fields helper

```python
def _all_digest_fields(result: OptimizationResult) -> tuple[tuple[str, str], ...]:
    fields: list[tuple[str, str]] = [
        ("sizing_request_identity_digest", result.sizing_request_identity_digest),
        ("passed_gate_digest", result.passed_gate_digest),
        ("candidate_set_digest", result.candidate_set_digest),
        ("evaluation_input_digest", result.evaluation_input_digest),
        ("result_core_hash", result.result_core_hash),
        ("provenance_digest", result.provenance_digest),
        ("result_hash", result.result_hash),
    ]
    for i, d in enumerate(result.ordered_disposition_record_digests):
        fields.append((f"disposition[{i}]", d))
    for i, d in enumerate(result.ordered_ranked_record_digests):
        fields.append((f"ranked[{i}]", d))
    for i, d in enumerate(result.ordered_top_n_record_digests):
        fields.append((f"top_n[{i}]", d))
    for i, d in enumerate(result.ordered_warning_digests):
        fields.append((f"warning[{i}]", d))
    for i, d in enumerate(result.ordered_blocker_digests):
        fields.append((f"blocker[{i}]", d))
    return tuple(fields)
```

### 11.6 External verifier (P0-5, P0-7)

```python
def verify_optimization_result_or_raise(
    result: OptimizationResult,
    *,
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    provenance_graph: ProvenanceGraph,
) -> None:
    DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

    # 1. Input binding
    if result.evaluation_input_digest != evaluation_input.evaluation_input_digest:
        raise ValueError("evaluation_input_digest mismatch")
    if result.sizing_request_identity_digest != evaluation_input.sizing_request_identity_digest:
        raise ValueError("sizing_request_identity_digest mismatch")
    if result.candidate_set_digest != evaluation_input.candidate_set_digest:
        raise ValueError("candidate_set_digest mismatch")
    if result.passed_gate_digest != evaluation_input.gate_digest:
        raise ValueError("passed_gate_digest mismatch")

    # 2. Total count matches
    if result.total_candidate_count != evaluation_input.evaluation_record_count:
        raise ValueError("total_candidate_count != evaluation_record_count")

    # 3. Per-index disposition binding (P0-5)
    N = result.total_candidate_count
    if len(disposition_records) != N:
        raise ValueError(f"disposition_records count {len(disposition_records)} != {N}")
    for i, (rec, dr) in enumerate(zip(evaluation_input.evaluation_records, disposition_records)):
        # Index binding
        if dr.evaluation_order_index != rec.evaluation_order_index:
            raise ValueError(f"disposition[{i}]: evaluation_order_index mismatch")
        if dr.evaluation_order_index != i:
            raise ValueError(f"disposition[{i}]: order_index != {i}")
        if dr.source_qualified_candidate_id != rec.source_qualified_candidate_id:
            raise ValueError(f"disposition[{i}]: candidate_id mismatch")
        # Source state binding
        if dr.source_candidate_evaluation_state != rec.candidate_evaluation_state:
            raise ValueError(f"disposition[{i}]: source state mismatch")
        if dr.source_hash_verification_outcome != rec.hash_verification_outcome:
            raise ValueError(f"disposition[{i}]: source hash outcome mismatch")
        if dr.source_provenance_verification_outcome != rec.provenance_verification_outcome:
            raise ValueError(f"disposition[{i}]: source provenance outcome mismatch")
        # Descriptor digest binding
        expected_desc_digest = evaluation_input.ordered_evaluation_record_descriptor_digests[i]
        if dr.source_record_descriptor_digest != expected_desc_digest:
            raise ValueError(f"disposition[{i}]: source descriptor digest mismatch")
        # Provider and rating
        if dr.provider_identity_matches != rec.provider_identity_matches:
            raise ValueError(f"disposition[{i}]: provider_identity_matches mismatch")
        if dr.rating_status != rec.rating_status:
            raise ValueError(f"disposition[{i}]: rating_status mismatch")
        # Recompute source digests
        _verify_source_digests_match(rec, dr, i)

        # Check digest
        if result.ordered_disposition_record_digests[i] != dr.feasibility_digest:
            raise ValueError(f"disposition[{i}]: feasibility_digest in result mismatch")
        dr.verify_or_raise()

    # 4. Ranked records binding
    F = result.feasible_candidate_count
    if len(ranked_records) != F:
        raise ValueError(f"ranked_records count {len(ranked_records)} != {F}")
    # Build FEASIBLE disposition lookup
    feasible_disp_by_id: dict[str, CandidateDispositionRecord] = {}
    for dr in disposition_records:
        if dr.disposition is Phase3Disposition.FEASIBLE:
            feasible_disp_by_id[dr.source_qualified_candidate_id] = dr
    if len(feasible_disp_by_id) != F:
        raise ValueError("FEASIBLE disposition count != feasible_candidate_count")
    for i, rr in enumerate(ranked_records):
        if result.ordered_ranked_record_digests[i] != rr.ranked_record_digest:
            raise ValueError(f"ranked[{i}]: digest in result mismatch")
        rr.verify_or_raise()
        # Resolve to FEASIBLE disposition
        disp = feasible_disp_by_id.get(rr.source_qualified_candidate_id)
        if disp is None:
            raise ValueError(f"ranked[{i}]: no FEASIBLE disposition for {rr.source_qualified_candidate_id!r}")
        if rr.candidate_evaluation_identity_digest != disp.candidate_evaluation_identity_digest:
            raise ValueError(f"ranked[{i}]: identity digest mismatch with disposition")
        if rr.verified_rating_evidence_digest != disp.verified_rating_evidence_digest:
            raise ValueError(f"ranked[{i}]: evidence digest mismatch with disposition")
        if rr.feasibility_digest != disp.feasibility_digest:
            raise ValueError(f"ranked[{i}]: feasibility_digest mismatch with disposition")
    # Rank order: must match tuple order AND be contiguous from 1
    for expected_rank, rr in enumerate(ranked_records, start=1):
        if rr.rank != expected_rank:
            raise ValueError(f"ranked record rank {rr.rank} != expected {expected_rank} (order mismatch)")
    # Recompute sort order
    sorted_ranked = _recompute_ranked_order(ranked_records, evaluation_input, disposition_records)
    if [rr.ranked_record_digest for rr in ranked_records] != [rr.ranked_record_digest for rr in sorted_ranked]:
        raise ValueError("ranked order does not match frozen sort key")

    # 5. Top-N
    TN = len(result.ordered_top_n_record_digests)
    expected_TN = min(result.requested_top_n, F)
    if TN != expected_TN:
        raise ValueError(f"Top-N length {TN} != min({result.requested_top_n}, {F})")
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N must be exact prefix of ranked")
    # Top-N digests must match selected ranked records
    # (already covered by prefix check + ranked digest verification)

    # 6. Independent count recomputation (P0-7)
    _verify_all_counts(result, evaluation_input, disposition_records)

    # 7. Termination
    stop_index = _find_stop_index(evaluation_input)
    if stop_index is None:
        if result.termination_status is not TerminationStatus.COMPLETE:
            raise ValueError("termination_status must be COMPLETE when no strict-stop exists")
    else:
        if result.termination_status is not TerminationStatus.PARTIAL:
            raise ValueError("termination_status must be PARTIAL when strict-stop exists")
    # Strict-stop warning verification (P0-11)
    if stop_index is not None:
        ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
        ss_warning_digest = sha256_digest(engineering_message_payload(ss_warning))
        if ss_warning_digest not in result.ordered_warning_digests:
            raise ValueError("strict-stop warning not found in ordered_warning_digests")
    else:
        for d in result.ordered_warning_digests:
            # Any strict-stop warning digest must not appear
            pass  # See P0-11 for exact rejection rule

    # 8. Hash verification
    expected_core = sha256_digest(result_core_payload(result))
    if result.result_core_hash != expected_core:
        raise ValueError("result_core_hash mismatch")
    # Semantic provenance graph verification (P0-9)
    verify_phase3_provenance_graph_or_raise(
        provenance_graph,
        evaluation_input=evaluation_input,
        disposition_records=disposition_records,
        ranked_records=ranked_records,
        result=result,
    )
    expected_prov = provenance_graph.compute_hash()
    if result.provenance_digest != expected_prov:
        raise ValueError("provenance_digest mismatch")
    expected_hash = sha256_digest({"result_core_hash": result.result_core_hash,
                                   "provenance_digest": result.provenance_digest})
    if result.result_hash != expected_hash:
        raise ValueError("result_hash mismatch")
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result.result_hash))
    if result.optimization_result_id != expected_id:
        raise ValueError("optimization_result_id mismatch")

    # 9. Digest format (all fields)
    for name, dgst in _all_digest_fields(result):
        if not DIGEST_PATTERN.match(dgst):
            raise ValueError(f"{name}: invalid digest {dgst!r}")

    # 10. Uniqueness
    if len(set(result.ordered_disposition_record_digests)) != N:
        raise ValueError("disposition digests not unique")
    if len(set(result.ordered_ranked_record_digests)) != F:
        raise ValueError("ranked digests not unique")
    if len(set(result.ordered_top_n_record_digests)) != TN:
        raise ValueError("Top-N digests not unique")
```

`_verify_source_digests_match` recomputes identity/evidence/invalid-evidence/failure digests from the source record and compares to disposition fields. `_verify_all_counts` independently counts from `evaluation_input.evaluation_records` and `disposition_records`. `_recompute_ranked_order` re-applies the frozen sort key.

---

## 12. Single-pass message descriptor (P0-10)

```python
def build_engineering_message_descriptor(
    message: EngineeringMessage,
) -> CanonicalizedEngineeringMessageDescriptor:
    """Public API — reads message.context exactly once."""
    ...

descriptors = tuple(
    build_engineering_message_descriptor(m)
    for m in messages
)
ordered = tuple(
    sorted(descriptors, key=lambda d: d.owner_sort_key)
)
message_digests = tuple(
    d.message_payload_digest for d in ordered
)
```

### 12.1 Canonicalization failure branch

If `descriptor.canonicalization_error is not None` or `descriptor.message_payload_digest is None`:

- Candidate disposition = `RUNTIME_FAILED`
- Source state remains VERIFIED (Phase 3 exception)
- Source outcomes = PASSED/PASSED
- `candidate_evaluation_identity_digest` and `verified_rating_evidence_digest` are **retained** to bind the trusted input that failed during Phase 3
- `failure_digest` is present
- `engineering_value` fields = None
- ErrorCode: `PHASE3_FEASIBILITY_RUNTIME_FAILURE`
- Fixed message: "Trusted context canonicalization failed during feasibility classification."
- Source module: `hexagent.optimization.feasibility`
- Affected paths: `()`
- Context payload includes `offending_type`, `failure_kind`, `context_key`

**Continuation policy:** Per-candidate canonicalization failure does NOT trigger Phase 2 strict-stop. Phase 3 continues classifying remaining VERIFIED candidates. The Phase 3 RUNTIME_FAILED count accumulates these failures.

---

## 13. Strict-stop warning (P0-11)

```python
def _build_strict_stop_warning(
    evaluation_input: Phase3EvaluationInput,
    stop_index: int,
) -> EngineeringMessage:
    record = evaluation_input.evaluation_records[stop_index]
    return EngineeringMessage(
        code=ErrorCode.PHASE3_STRICT_STOP,  # to be added to ErrorCode
        severity=EngineeringMessageSeverity.WARNING,
        message="Phase 2 strict-stop occurred; records after index are UNEVALUATED.",
        source_module="hexagent.optimization.phase3_input",
        affected_paths=(),
        context=(
            ("stop_index", stop_index),
            ("source_qualified_candidate_id", record.source_qualified_candidate_id),
            ("source_state", record.candidate_evaluation_state.value),
            ("source_record_descriptor_digest",
             evaluation_input.ordered_evaluation_record_descriptor_digests[stop_index]),
        ),
    )
```

Rules:
- `termination_status == PARTIAL` → exact strict-stop warning must appear exactly once in `ordered_warning_digests`
- `termination_status == COMPLETE` → no strict-stop warning digest may appear
- The warning is sorted among other warnings using `engineering_message_sort_key`

---

## 14. Provenance (P0-8, P0-9)

### 14.1 Namespaces

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
```

Distinct namespaces: result artifact IDs vs provenance node UUIDs.

### 14.2 Semantic provenance verifier

```python
def verify_phase3_provenance_graph_or_raise(
    graph: ProvenanceGraph,
    *,
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    result: OptimizationResult,
) -> None:
    # 1. Exactly one zero-in-degree root
    roots = [n for n in graph.nodes if not any(e.target_id == n.node_id for e in graph.edges)]
    if len(roots) != 1:
        raise ValueError(f"expected 1 root, got {len(roots)}")
    root = roots[0]
    if root.node_type != ProvenanceNodeType.EXTERNAL:
        raise ValueError("root type must be EXTERNAL")
    # Root payload
    expected_root_payload = {
        "artifact_kind": "phase3_evaluation_input",
        "evaluation_input_digest": evaluation_input.evaluation_input_digest,
    }
    expected_root_payload_hash = sha256_digest(expected_root_payload)
    if root.payload_hash != expected_root_payload_hash:
        raise ValueError("root payload_hash mismatch")
    expected_root_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"EXTERNAL:{expected_root_payload_hash}")
    if root.node_id != expected_root_id:
        raise ValueError("root node_id mismatch")
    if root.label != "":
        raise ValueError("root label must be empty")
    if root.metadata != ():
        raise ValueError("root metadata must be empty")

    # 2. Exact node set count
    N = result.total_candidate_count
    F = result.feasible_candidate_count
    expected_node_count = 10 + N + F  # 1 root + 1 sizing + 1 gate + 1 cset + 1 einput + N disp + F ranked + 1 topn + 1 result + 1 optimizer
    if len(graph.nodes) != expected_node_count:
        raise ValueError(f"expected {expected_node_count} nodes, got {len(graph.nodes)}")

    # 3. Node payload verification
    PAYLOAD_MAP = {
        "INPUT_FILE": evaluation_input.sizing_request_identity_digest,
        "CALCULATION_RUN": [evaluation_input.gate_digest, evaluation_input.candidate_set_digest],
        "INTERMEDIATE": [
            evaluation_input.evaluation_input_digest,
        ] + [dr.feasibility_digest for dr in disposition_records]
          + [rr.ranked_record_digest for rr in ranked_records]
          + [sha256_digest({"ordered_top_n_record_digests": list(result.ordered_top_n_record_digests)})],
        "RESULT": result.result_core_hash,
        "OPTIMIZER": sha256_digest({
            "schema_version": 1,
            "evaluation_input_digest": evaluation_input.evaluation_input_digest,
            "optimization_objective": result.optimization_objective.value,
            "requested_top_n": result.requested_top_n,
            "termination_status": result.termination_status.value,
            "result_core_hash": result.result_core_hash,
            "phase3_algorithm_version": "task009-phase3-v1",
        }),
    }
    _verify_node_payloads(graph, PAYLOAD_MAP, PHASE3_PROVENANCE_NAMESPACE)

    # 4. Exact edge set
    expected_edges = _build_expected_edges(evaluation_input, disposition_records, ranked_records, result)
    actual_edges = {(e.source_id, e.target_id, e.relation) for e in graph.edges}
    if actual_edges != expected_edges:
        raise ValueError(f"edge set mismatch: {len(actual_edges)} != {len(expected_edges)}")
    # All edges metadata empty
    for e in graph.edges:
        if e.metadata != ():
            raise ValueError(f"edge {e.source_id}→{e.target_id}: metadata must be empty")

    # 5. Labels
    for n in graph.nodes:
        if n.label != "":
            raise ValueError(f"node {n.node_id}: label must be empty")

    # 6. Reachability (via BFS from root)
    children = {n.node_id: [] for n in graph.nodes}
    for e in graph.edges:
        children[e.source_id].append(e.target_id)
    visited = set()
    queue = [root.node_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        queue.extend(children.get(nid, []))
    if len(visited) != len(graph.nodes):
        raise ValueError("graph has unreachable nodes")
```

`_verify_node_payloads` checks each node's payload_hash matches the authoritative source. `_build_expected_edges` constructs the exact edge set from §14.3.

### 14.3 Edge topology

```
Root ──regulates──► Sizing Request ──consumed_by──► Passed Sizing Gate
                                                         │ produced
                                                         ▼
                                                 Materialized Candidate Set
                                                         │ consumed_by
                                                         ▼
                                                 Evaluation Input ──evaluated──► Disposition Records
                                                         │
                                                         │ selected_by
                                                         ▼
                                                  Top-N Selection ◄──selected── (only selected Ranked Records)
                                                         │ produced
                                                         ▼
                                                  Result Core ──executed_by──► Optimizer
```

For each FEASIBLE disposition: disposition → `ranked` → ranked record.
For each selected (first N) ranked record: ranked record → `selected` → Top-N Selection.
For non-FEASIBLE dispositions: no ranked edge. For non-selected ranked records: no selected edge.
Always: Evaluation Input → `selected_by` → Top-N Selection (even when 0 FEASIBLE).

### 14.4 Algorithm version

`phase3_algorithm_version = "task009-phase3-v1"` — fixed string constant, no runtime placeholder.

---

## 15. Error model

Phase 3 error codes added to `ErrorCode` in `messages.py`. All messages entering hash/provenance/artifact use fixed deterministic strings. Prohibited: `str(exc)`, `repr(exc)`, `traceback`, addresses, runtime object representations.

---

## 16. Implementation boundary

### Existing files modified

| Path | Change |
|---|---|
| `src/hexagent/domain/messages.py` | Add Phase 3 error codes to `ErrorCode` |
| `src/hexagent/optimization/evaluation.py` | Export `build_engineering_message_descriptor` as public name for internal `_build_message_descriptor` |

### New files

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + 13-step verify + payload helpers |
| `src/hexagent/optimization/feasibility.py` | `Phase3CandidateClassificationInput` + `classify_candidate()` + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Ranking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` + hash + external verifier + provenance verifier |
| `tests/unit/test_task009_phase3_*.py` | Tests |

---

## 17. Test matrix

### 17.1 Descriptor payloads
- [ ] `evaluation_record_descriptor_payload` exact field sensitivity
- [ ] `evaluation_input_payload` exact field sensitivity
- [ ] Descriptor digest excludes itself
- [ ] Input digest excludes itself

### 17.2 Provider parity
- [ ] Provider=Matches=False ⇔ feasibility=PROVIDER_IDENTITY_MISMATCH applies only to VERIFIED
- [ ] INTEGRITY_INVALID hash-false: provider=False but feasibility=NOT_EVALUATED accepted
- [ ] INTEGRITY_INVALID provenance-false: provider=True (default) accepted

### 17.3 Typed classifier
- [ ] `Phase3CandidateClassificationInput` receives all authoritative fields
- [ ] Classifier does not consume `CandidateDispositionRecord` as input
- [ ] BLOCKED/FAILED rating candidates not tested for thermal metrics
- [ ] SUCCEEDED rating required for duty/delta-T check

### 17.4 Disposition invariants (no assert)
- [ ] All validators work under `python -O` (no `assert`)
- [ ] FEASIBLE validates both canonical engineering values
- [ ] INFEASIBLE diagnostic matches rating_status
- [ ] Each disposition variant validates exact outcomes/nullability
- [ ] RUNTIME_FAILED from VERIFIED retains identity/evidence digests

### 17.5 Per-index binding
- [ ] Disposition record binds to source input at same index
- [ ] Tampered source state/outcome/candidate ID rejected
- [ ] Tampered source descriptor binding rejected
- [ ] Recalculated source digests match disposition

### 17.6 Ranked records
- [ ] Ranked record fully binds to FEASIBLE disposition (3 digest fields + candidate ID)
- [ ] Rank tuple order `[2, 1]` rejected (contiguous from 1 required)
- [ ] Ranked order verified against frozen sort key

### 17.7 Counts
- [ ] All counts independently recomputed from authoritative artifacts
- [ ] Coordinated count tampering rejected
- [ ] `_all_digest_fields` exact coverage (no `etc.`)

### 17.8 Namespaces
- [ ] `PHASE3_RESULT_NAMESPACE` exact UUID
- [ ] Wrong result namespace → verification failure
- [ ] Same result_hash → same result UUID5
- [ ] Different result_hash → different result UUID5

### 17.9 Provenance
- [ ] Exact root type, payload, node ID
- [ ] Exact node set count verified
- [ ] Exact edge set verified (all relations)
- [ ] Extra/missing/wrong edge rejected
- [ ] CASE_REVISION root rejected (EXTERNAL required)
- [ ] Non-FEASIBLE ranked edge rejected
- [ ] Unselected ranked→Top-N edge rejected
- [ ] Zero-FEASIBLE graph connected

### 17.10 Single-pass descriptor
- [ ] Message context read exactly once
- [ ] `message_payload_digest` is valid digest (not None)
- [ ] Canonicalization failure → correct disposition policy
- [ ] Phase 3 canonicalization failure continues other candidates

### 17.11 Strict-stop warning
- [ ] PARTIAL: exact warning appears exactly once
- [ ] COMPLETE: strict-stop warning rejected
- [ ] Warning sorted by `engineering_message_sort_key`

### 17.12 Termination messages
- [ ] COMPLETE check: correct condition/message (no inversion)
- [ ] PARTIAL check: correct condition/message
- [ ] All error messages fixed literal
- [ ] Provenance verifier error messages use canonical sorted sets

---

## 18. Acceptance criteria

1. All tests pass Python 3.11 and 3.12
2. `result_hash` deterministic and reproducible
3. Semantic provenance DAG verifier detects every tamper mode
4. 13-step input verification fails closed for all steps
5. Top-N selection never exceeds feasible count
6. No Phase 2 artifact mutated
7. PROVIDER_IDENTITY_MISMATCH never enters ranking or Top-N
8. UNEVALUATED never enters feasibility
9. Ruff, format, mypy strict, coverage pass
10. Pip-audit passes
11. Design review passes before implementation authorized

---

## 19. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED

Implementation must not begin until a separate engineering design review passes and a frozen contract commit SHA is established.
