# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Milestone:** M2. Priority: P0
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> ⚠️ This document is a **design contract** for review only. No implementation is authorized until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope

Phase 3 consumes `tuple[CandidateEvaluationRecord, ...]` via `Phase3EvaluationInput` and produces a deterministic `OptimizationResult` with typed disposition records, ranked records, hash, and provenance.

---

## 2. Non-goals

Out of scope: TASK-010, C4, pressure-drop, velocity, pump power, economic / Pareto / stochastic / heuristic / ML optimization, new correlations, rating solver, candidate generation, catalog schema changes, Phase 2 artifact mutation, re-running TASK-008, recovering strict-stop.

---

## 3. Phase3EvaluationInput (P1-1: 13-step verification)

### 3.1 Model

```python
class Phase3EvaluationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str       # identity.sizing_request_identity_digest
    materialization_result: MaterializationResult
    candidate_set_digest: str                 # result.candidate_set.candidate_set_digest
    gate_digest: str                          # result.sizing_gate.gate_digest
    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int
    ordered_evaluation_record_descriptor_digests: tuple[str, ...]
    evaluation_input_digest: str
```

### 3.2 Digest API

All digests use `sha256_digest()` from `hexagent.core.canonical`. `sha256_digest(payload)` receives a primitive-only dict/list/str and returns `"sha256:<hex>"`. The caller **never** serialises to JSON — `sha256_digest` handles canonical JSON internally.

Prohibited: `sha256(...)`, `hashlib.sha256(...)`, `sha256_digest(canonical_json(...))`, `sha256_digest(model_object)`, generic `model_dump` hashing.

### 3.3 13-step verify_or_raise()

**Step 1 — Type verification:** Each field is the exact expected Pydantic type.

**Step 2 — materialization_result.verify_or_raise():** Delegates to existing method.

**Step 3 — Sizing identity digest:** Verify `sizing_request_identity_digest == identity.sizing_request_identity_digest`.

**Step 4 — candidate_set.verify_digest():** Must return True.

**Step 5 — sizing_gate.verify_digest():** Must return True.

**Step 6 — Candidate-set ↔ sizing binding:** Verify `candidate_set.sizing_request_identity_digest == sizing_request_identity_digest`.

**Step 7 — Gate ↔ candidate-set binding:** Verify `gate.gate_digest == candidate_set.passed_gate_digest`.

**Step 8 — Count parity:** `evaluation_record_count == len(records) == len(candidates) == len(descriptor_digests)`.

**Step 9 — Record ↔ candidate one-to-one binding:** For each `i`: `record.evaluation_order_index == i`, `candidate.evaluation_order_index == i`, `record.source_qualified_candidate_id == candidate.source_qualified_candidate_id == ordered_candidate_ids[i]`. No missing, extra, duplicate, displaced, or skipped records.

**Step 10 — Exhaustive state field verification:** For every record, verify all fields match the production paths in §4.1–4.2. This includes state invariant validation, audit-presence-per-path, rating-status parity, and required-numeric validation (SUCCEEDED metrics finite/non-null). Any field combination not matching an exact production path is rejected.

**Step 11 — Strict-stop invariant:** Verify `stop_index` rule (§5.1).

**Step 12 — Descriptor digest verification:** For each `i`, compute `sha256_digest(evaluation_record_descriptor_payload(record[i]))` and verify it matches `ordered_evaluation_record_descriptor_digests[i]`.

**Step 13 — evaluation_input_digest verification:** Recompute and compare.

All failures raise `ValueError` with a fixed deterministic message. No `str(exc)`.

---

## 4. Phase 2 state matrix (P0-1)

### 4.1 Exhaustive production paths per constructor

Each row is an exact production path from `evaluation.py`. Every field is frozen.

#### VERIFIED (1 path)

```python
# evaluation.py lines 2634–2646
CandidateEvaluationRecord(
    source_qualified_candidate_id=...,
    evaluation_order_index=...,
    candidate_evaluation_state=CandidateEvaluationState.VERIFIED,
    feasible=False,
    feasibility_status=feasibility_status,          # NOT_EVALUATED if provider_matches=True
                                                    # PROVIDER_IDENTITY_MISMATCH if provider_matches=False
    candidate_evaluation_identity=eval_identity,
    claimed_rating_result_audit=None,               # NOT written for VERIFIED
    verified_rating_evidence=evidence,
    invalid_rating_evidence=None,
    provider_identity_matches=provider_matches,      # True or False
    evaluation_failure=None,
    rating_status=rating_status_str,                 # RatingStatus.value or None
    hash_verification_outcome=VerificationOutcome.PASSED,
    provenance_verification_outcome=VerificationOutcome.PASSED,
)
```

#### INTEGRITY_INVALID (2 paths)

| Field | Path A: hash false (line 2333) | Path B: provenance false (line 2388) |
|---|---|---|
| `hash_verification_outcome` | FAILED | PASSED |
| `provenance_verification_outcome` | NOT_RUN | FAILED |
| `invalid_rating_evidence` | present | present |
| `claimed_rating_result_audit` | present | present |
| `candidate_evaluation_identity` | None | None |
| `verified_rating_evidence` | None | None |
| `evaluation_failure` | None | None |
| `rating_status` | None | None |
| `provider_identity_matches` | False (line 2342) | (omitted, default True) |

#### RUNTIME_FAILED (10 paths)

| # | Source | hash | provenance | audit present | evaluation_failure present |
|---|---|---|---|---|---|
| 1 | Type mismatch (line 2277) | NOT_RUN | NOT_RUN | Yes | Yes |
| 2 | verify_hash raised (line 2303) | ERROR | NOT_RUN | Yes | Yes |
| 3 | verify_provenance raised (line 2358) | PASSED | ERROR | Yes | Yes |
| 4 | Evidence extraction failed (line 2414) | PASSED | PASSED | Yes | Yes |
| 5 | Context canonicalization (line 2478) | PASSED | PASSED | **None** | Yes |
| 6 | Warning canonicalization error (line 2511) | PASSED | PASSED | **None** | Yes |
| 7 | Blocker canonicalization error (line 2543) | PASSED | PASSED | **None** | Yes |
| 8 | RunFailure canonicalization (line 2575) | PASSED | PASSED | **None** | Yes |
| 9 | Identity construction failed (line 2611) | PASSED | PASSED | **None** | Yes |
| 10 | Outer catch-all (line 2672) | PASSED | PASSED | **None** | Yes |

All RUNTIME_FAILED paths: `identity=None`, `verified_evidence=None`, `invalid_evidence=None`, `rating_status=None`.

#### UNEVALUATED (1 path)

```
hash=NOT_RUN, provenance=NOT_RUN, identity=None, verified_evidence=None,
invalid_evidence=None, evaluation_failure=None, rating_status=None,
claimed_rating_result_audit=None
```

### 4.2 Invalid cross-field combinations

Any combination not matching an exact production path in §4.1 is invalid and rejected at Step 10. Key rejections: VERIFIED + identity=None, VERIFIED + invalid_evidence present, INTEGRITY_INVALID + invalid_evidence=None, RUNTIME_FAILED + evaluation_failure=None, RUNTIME_FAILED + identity present, UNEVALUATED + identity present.

### 4.3 Provider flag and feasibility_status parity

```python
provider_identity_matches == True   ⇔   feasibility_status == FeasibilityStatus.NOT_EVALUATED
provider_identity_matches == False  ⇔   feasibility_status == FeasibilityStatus.PROVIDER_IDENTITY_MISMATCH
```

### 4.4 Phase 2 → Phase 3 disposition

| Phase 2 state | provider matches | Phase 3 Disposition |
|---|---|---|
| UNEVALUATED | any | UNEVALUATED |
| VERIFIED | True | FEASIBLE or INFEASIBLE (by §8 classifier) |
| VERIFIED | False | PROVIDER_IDENTITY_MISMATCH |
| INTEGRITY_INVALID (FAILED/NOT_RUN) | any | INTEGRITY_FAILED |
| INTEGRITY_INVALID (PASSED/FAILED) | any | PROVENANCE_FAILED |
| RUNTIME_FAILED | any | RUNTIME_FAILED |
| VERIFIED + Phase 3 feasibility exception | any | RUNTIME_FAILED (source state VERIFIED preserved) |

---

## 5. Strict-stop

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. If present: indices < stop_index must be VERIFIED; index == stop_index is INTEGRITY_INVALID or RUNTIME_FAILED; indices > stop_index must be UNEVALUATED.

`TerminationStatus.COMPLETE` = no strict-stop. `PARTIAL` = strict-stop occurred.

---

## 6. Decimal canonicalization (P0-2)

### 6.1 to_canonical_decimal()

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
```

Allowed exact types: `float`, `int`, `Decimal`.
Prohibited exactly: `bool`, `str`, `None`, `Fraction`, `numpy.float64` (caller must convert to native float first).

### 6.2 canonical_decimal() and canonical_decimal_string()

```python
def canonical_decimal(value: Decimal) -> Decimal:
    if type(value) is not Decimal:
        raise TypeError(f"value must be exact Decimal, got {type(value).__name__}")
    if not value.is_finite():
        raise ValueError(f"value must be finite, got {value}")
    normalized = value.normalize()
    if normalized.is_zero():
        return Decimal("0")
    return normalized

def canonical_decimal_string(value: Decimal) -> str:
    normalized = canonical_decimal(value)
    return format(normalized, "f")
```

Rules: `format(d, "f")` — no exponent; `"-0"` → `"0"`; positive never `"+"`; no leading/trailing zeros.

Accepted: `"0"`, `"1"`, `"1.25"`, `"-1.25"`. Rejected: `"1.00"`, `"+1"`, `"01"`, `"1E+0"`, `"-0"`.

### 6.3 Model validation

```python
parsed = Decimal(raw_value)
expected = canonical_decimal_string(parsed)
if raw_value != expected:
    raise ValueError(f"value not canonical: {raw_value!r} != {expected!r}")
```

---

## 7. Exact FEASIBLE classifier (P0-2)

### 7.1 Predicate

```python
def is_feasible(record: CandidateDispositionRecord) -> bool:
    return (
        record.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED
        and record.provider_identity_matches == True
        and record.rating_status == RatingStatus.SUCCEEDED.value
        and _duty_satisfied(record)
        and _terminal_delta_t_satisfied(record)
    )
```

`rating_status` is only read as `SUCCEEDED` for VERIFIED records. `BLOCKED`/`FAILED` rating records do not have successful-result thermal metrics and are never tested for duty/delta-T satisfaction — they become INFEASIBLE with diagnostic `RATING_BLOCKED` or `RATING_FAILED`.

### 7.2 Duty arithmetic (Decimal-only)

```python
required = to_canonical_decimal(required_duty_w)
abs_tol = to_canonical_decimal(duty_absolute_tolerance_w)
rel_tol = to_canonical_decimal(duty_relative_tolerance)
heat = to_canonical_decimal(heat_duty_w)
duty_tolerance = max(abs_tol, rel_tol * abs(required))
duty_satisfied = abs(heat - required) <= duty_tolerance
```

### 7.3 Terminal delta-T

```
parallel:       delta_t_1 = hot_inlet - cold_inlet;  delta_t_2 = hot_outlet - cold_outlet
counterflow:    delta_t_1 = hot_inlet - cold_outlet;  delta_t_2 = hot_outlet - cold_inlet
satisfied = min(delta_t_1_decimal, delta_t_2_decimal) >= to_canonical_decimal(minimum_terminal_delta_t)
```

### 7.4 Diagnostic precedence (single final diagnostic per candidate)

| Priority | DiagnosticKey | Condition |
|---|---|---|
| 1 | PROVIDER_IDENTITY_MISMATCH | `provider_identity_matches == False` |
| 2 | RATING_BLOCKED | `rating_status == BLOCKED` |
| 3 | RATING_FAILED | `rating_status == FAILED` |
| 4 | DUTY_SHORTFALL | `duty_satisfied == False` (only for SUCCEEDED) |
| 5 | TERMINAL_DELTA_T_INADEQUATE | `terminal_delta_t_satisfied == False` (only for SUCCEEDED) |

Each candidate receives exactly one diagnostic key — the highest-priority failing condition. `FEASIBLE` diagnostic = `NONE`.

---

## 8. Counts (P0-2)

### 8.1 Phase 3 disposition counts (disjoint, sum = total)

```
total == feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated
```

### 8.2 Phase 2 state audit counts (direct from source records)

```
phase2_verified              = count(state == VERIFIED)
phase2_integrity_invalid     = count(state == INTEGRITY_INVALID)
phase2_runtime_failed        = count(state == RUNTIME_FAILED)
phase2_unevaluated           = count(state == UNEVALUATED)

phase2_verified + phase2_integrity_invalid + phase2_runtime_failed + phase2_unevaluated == total
```

### 8.3 Cross-equations

```
runtime_failed = runtime_failed_from_phase2_verified + runtime_failed_from_phase2_runtime_failed

phase2_verified = feasible + infeasible + provider_mismatch + runtime_failed_from_phase2_verified
phase2_integrity_invalid = integrity_failed + provenance_failed
phase2_runtime_failed = runtime_failed_from_phase2_runtime_failed
phase2_unevaluated = unevaluated
```

---

## 9. CandidateDispositionRecord (P0-3)

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

    @model_validator(mode="after")
    def _validate(self) -> Self:
        DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

        # Common invariants
        if not self.source_qualified_candidate_id:
            raise ValueError("source_qualified_candidate_id must be non-empty")
        if self.evaluation_order_index < 0:
            raise ValueError("evaluation_order_index must be ≥ 0")
        if not DIGEST_PATTERN.match(self.source_record_descriptor_digest):
            raise ValueError("invalid source_record_descriptor_digest")
        if not DIGEST_PATTERN.match(self.feasibility_digest):
            raise ValueError("invalid feasibility_digest")
        for d in self.ordered_warning_digests:
            if not DIGEST_PATTERN.match(d):
                raise ValueError("invalid warning digest")
        for d in self.ordered_blocker_digests:
            if not DIGEST_PATTERN.match(d):
                raise ValueError("invalid blocker digest")
        if self.failure_digest is not None and not DIGEST_PATTERN.match(self.failure_digest):
            raise ValueError("invalid failure_digest")
        for d in [self.candidate_evaluation_identity_digest, self.verified_rating_evidence_digest,
                  self.invalid_rating_evidence_digest]:
            if d is not None and not DIGEST_PATTERN.match(d):
                raise ValueError(f"invalid digest: {d!r}")

        # Disposition-specific invariants
        if self.disposition is Phase3Disposition.FEASIBLE:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED
            assert self.provider_identity_matches == True
            assert self.rating_status == RatingStatus.SUCCEEDED.value
            assert self.diagnostic == FeasibilityDiagnosticKey.NONE
            assert self.candidate_evaluation_identity_digest is not None
            assert self.verified_rating_evidence_digest is not None
            assert self.invalid_rating_evidence_digest is None
            assert self.primary_engineering_value is not None
            assert self.secondary_engineering_value is not None
            assert canonical_decimal_string(Decimal(self.primary_engineering_value)) == self.primary_engineering_value
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.INFEASIBLE:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED
            assert self.provider_identity_matches == True
            assert self.diagnostic in (FeasibilityDiagnosticKey.RATING_BLOCKED,
                                       FeasibilityDiagnosticKey.RATING_FAILED,
                                       FeasibilityDiagnosticKey.DUTY_SHORTFALL,
                                       FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE)
            assert self.candidate_evaluation_identity_digest is not None
            assert self.verified_rating_evidence_digest is not None
            assert self.invalid_rating_evidence_digest is None
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.PROVIDER_IDENTITY_MISMATCH:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED
            assert self.provider_identity_matches == False
            assert self.diagnostic == FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.INTEGRITY_FAILED:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID
            assert self.source_hash_verification_outcome == VerificationOutcome.FAILED
            assert self.source_provenance_verification_outcome == VerificationOutcome.NOT_RUN
            assert self.invalid_rating_evidence_digest is not None
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.PROVENANCE_FAILED:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID
            assert self.source_hash_verification_outcome == VerificationOutcome.PASSED
            assert self.source_provenance_verification_outcome == VerificationOutcome.FAILED
            assert self.invalid_rating_evidence_digest is not None
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.UNEVALUATED:
            assert self.source_candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED
            assert self.diagnostic == FeasibilityDiagnosticKey.NONE
            assert self.candidate_evaluation_identity_digest is None
            assert self.verified_rating_evidence_digest is None
            assert self.invalid_rating_evidence_digest is None
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None
            assert self.failure_digest is None

        elif self.disposition is Phase3Disposition.RUNTIME_FAILED:
            assert self.source_candidate_evaluation_state in (
                CandidateEvaluationState.VERIFIED,
                CandidateEvaluationState.RUNTIME_FAILED,
            )
            assert self.failure_digest is not None
            assert self.primary_engineering_value is None
            assert self.secondary_engineering_value is None

        return self

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("feasibility_digest mismatch")
```

### 9.2 Payload

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
    # Does NOT include feasibility_digest
```

---

## 10. RankedCandidateRecord (P0-4)

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

    DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")

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
                raise ValueError(f"{name}: must be finite, got {val!r}")
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
        for dgst, name in [(self.candidate_evaluation_identity_digest, "candidate_eval"),
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

## 11. OptimizationResult (P0-5, P0-6, P0-7)

### 11.1 Model

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int = 1
    optimization_result_id: str   # str(uuid.uuid5(PHASE3_NS, result_hash))

    sizing_request_identity_digest: str
    passed_gate_digest: str
    candidate_set_digest: str
    evaluation_input_digest: str

    optimization_objective: OptimizationObjective
    requested_top_n: int

    # Phase 3 disposition counts
    total_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    provenance_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int

    # Phase 2 state audit counts
    phase2_verified_record_count: int
    phase2_integrity_invalid_record_count: int
    phase2_runtime_failed_record_count: int
    phase2_unevaluated_record_count: int

    # Runtime-failure cross-counts
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

### 11.2 Result core payload (explicit every field)

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
result_core_hash = sha256_digest(result_core_payload(result))
provenance_digest = ProvenanceGraph.compute_hash()
result_hash = sha256_digest({"result_core_hash": result_core_hash, "provenance_digest": provenance_digest})
optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))
```

### 11.4 External verifier (P0-5 — chosen architecture)

`OptimizationResult` is a digest-only summary artifact. It does not carry child records. Verification is performed by an external function:

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

    # 2. Disposition records
    N = result.total_candidate_count
    if len(disposition_records) != N:
        raise ValueError(f"disposition_records count {len(disposition_records)} != {N}")
    for i, dr in enumerate(disposition_records):
        if result.ordered_disposition_record_digests[i] != dr.feasibility_digest:
            raise ValueError(f"disposition digest mismatch at index {i}")
        dr.verify_or_raise()

    # 3. Ranked records
    F = result.feasible_candidate_count
    if len(ranked_records) != F:
        raise ValueError(f"ranked_records count {len(ranked_records)} != {F}")
    for i, rr in enumerate(ranked_records):
        if result.ordered_ranked_record_digests[i] != rr.ranked_record_digest:
            raise ValueError(f"ranked digest mismatch at index {i}")
        rr.verify_or_raise()
        # Ranked records must resolve to FEASIBLE disposition
        matched = any(
            dr.feasibility_digest == rr.feasibility_digest
            and dr.disposition is Phase3Disposition.FEASIBLE
            for dr in disposition_records
        )
        if not matched:
            raise ValueError(f"ranked record {i} does not resolve to FEASIBLE disposition")
    # Ranks contiguous 1..F
    expected_ranks = set(range(1, F + 1))
    actual_ranks = set(rr.rank for rr in ranked_records)
    if actual_ranks != expected_ranks:
        raise ValueError(f"ranked ranks {actual_ranks} != contiguous 1..{F}")
    # Ranked candidate IDs unique
    ranked_ids = [rr.source_qualified_candidate_id for rr in ranked_records]
    if len(set(ranked_ids)) != len(ranked_ids):
        raise ValueError("duplicate ranked candidate IDs")

    # 4. Top-N
    TN = len(result.ordered_top_n_record_digests)
    expected_TN = min(result.requested_top_n, F)
    if TN != expected_TN:
        raise ValueError(f"Top-N length {TN} != min({result.requested_top_n}, {F})")
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N must be exact prefix of ranked")

    # 5. Termination
    stop_index = _find_stop_index(evaluation_input)
    if stop_index is None:
        if result.termination_status != TerminationStatus.COMPLETE:
            raise ValueError("expected COMPLETE but strict-stop found")
    else:
        if result.termination_status != TerminationStatus.PARTIAL:
            raise ValueError("expected PARTIAL but no strict-stop indicator")

    # 6. Hash verification
    expected_core = sha256_digest(result_core_payload(result))
    if result.result_core_hash != expected_core:
        raise ValueError("result_core_hash mismatch")
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

    # 7. Digest format (all fields)
    for name, dgst in _all_digest_fields(result):
        if not DIGEST_PATTERN.match(dgst):
            raise ValueError(f"{name}: invalid digest {dgst!r}")

    # 8. Disposition digests unique
    if len(set(result.ordered_disposition_record_digests)) != N:
        raise ValueError("disposition digests not unique")
    # Ranked digests unique
    if len(set(result.ordered_ranked_record_digests)) != F:
        raise ValueError("ranked digests not unique")
    # Top-N digests unique
    if len(set(result.ordered_top_n_record_digests)) != TN:
        raise ValueError("Top-N digests not unique")
```

`_find_stop_index()` is a pure helper that scans `evaluation_input.evaluation_records` for the first INTEGRITY_INVALID or RUNTIME_FAILED. `_all_digest_fields()` returns `(name, digest)` pairs for every digest field in the result.

`OptimizationResult` itself has a lightweight `@model_validator` that verifies count equations, digest format, and UUID5 — but the full cross-artifact verification is handled by `verify_optimization_result_or_raise()`.

---

## 12. Warning/blocker canonicalization (P0-10)

### 12.1 Single-pass descriptor approach

Phase 3 uses single-pass message descriptors to avoid reading `message.context` twice:

```python
descriptors = tuple(
    build_engineering_message_descriptor(message)
    for message in messages
)
ordered_descriptors = tuple(
    sorted(descriptors, key=lambda d: d.owner_sort_key)
)
message_digests = tuple(
    d.message_payload_digest for d in ordered_descriptors
)
```

`build_engineering_message_descriptor()` returns a `CanonicalizedEngineeringMessageDescriptor` with:
- `owner_sort_key` — deterministic sort key
- `message_payload_digest` — `sha256_digest(engineering_message_payload(message))` computed once
- Canonicalization error data (if context fails)

Warnings and blockers are processed separately. Duplicates preserved. No post-sort re-access of message.context or `engineering_message_payload()`.

### 12.2 Implementation boundary

If `build_engineering_message_descriptor` currently exists as an internal helper, Phase 3 implementation may either:
- Import it as an internal helper from `evaluation.py` (preferred, minimal change)
- Rename/re-export it as a public API

No new context-marker or digest algorithms. Existing `engineering_message_payload()` and `run_failure_payload()` are reused unchanged.

---

## 13. Provenance (P0-8, P0-9)

### 13.1 Root: always EXTERNAL

```python
root_payload = {
    "artifact_kind": "phase3_evaluation_input",
    "evaluation_input_digest": evaluation_input.evaluation_input_digest,
}
root_payload_hash = sha256_digest(root_payload)
```

### 13.2 Labels and metadata

Every Phase 3 `ProvenanceNode`: `label=""`, `metadata=()`.
Every Phase 3 `ProvenanceEdge`: `metadata=()`.

### 13.3 Algorithm version (P0-9)

```python
PHASE3_ALGORITHM_VERSION = "task009-phase3-v1"
```

This is a fixed string constant, not derived from runtime metadata. The optimizer payload uses this constant, not a `<runtime>` placeholder.

```python
optimizer_payload = {
    "schema_version": 1,
    "evaluation_input_digest": evaluation_input.evaluation_input_digest,
    "optimization_objective": optimization_objective.value,
    "requested_top_n": requested_top_n,
    "termination_status": termination_status.value,
    "result_core_hash": result_core_hash,
    "phase3_algorithm_version": PHASE3_ALGORITHM_VERSION,
}
```

No `software_version`, no runtime placeholder, no package-version metadata that could differ between builds.

### 13.4 Zero-FEASIBLE connectivity

To keep the provenance graph connected even when no candidate is FEASIBLE:

- Always add edge: `Evaluation Input ──selected_by──► Top-N Selection`
- Then for each selected ranked record (if any): `Ranked Record ──selected──► Top-N Selection`

This ensures the chain `Root → ... → Evaluation Input → Top-N Selection → Result Core → Optimizer` is always connected regardless of FEASIBLE count.

### 13.5 Graph-level verifier

```python
def verify_provenance_graph(graph: ProvenanceGraph, evaluation_input: Phase3EvaluationInput) -> None:
    # Exactly one zero-in-degree root
    roots = [n for n in graph.nodes if not any(e.target_id == n.node_id for e in graph.edges)]
    if len(roots) != 1:
        raise ValueError(f"expected 1 root, got {len(roots)}")
    root = roots[0]
    if root.node_type not in (ProvenanceNodeType.EXTERNAL, ProvenanceNodeType.CASE_REVISION):
        raise ValueError(f"root type must be EXTERNAL or CASE_REVISION, got {root.node_type}")
    # Reachability via BFS from root
    children: dict[UUID, list[UUID]] = {n.node_id: [] for n in graph.nodes}
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
        unreachable = set(n.node_id for n in graph.nodes) - visited
        raise ValueError(f"unreachable nodes: {unreachable}")
    # Specific nodes reachable — implicit in BFS
    # CALCULATION_RUN exists — checked by ProvenanceGraph.validate_graph()
```

### 13.6 Unified UUID5 for all nodes

```python
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
node_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{node_type.value}:{payload_hash}")
```

Every node uses this algorithm. No special cases.

### 13.7 Node types

| Role | `ProvenanceNodeType` | payload_hash |
|---|---|---|
| Root | `EXTERNAL` | `sha256_digest(root_payload)` |
| Sizing request | `INPUT_FILE` | `sizing_request_identity_digest` (direct) |
| Passed sizing gate | `CALCULATION_RUN` | `gate_digest` (direct) |
| Materialized candidate set | `CALCULATION_RUN` | `candidate_set_digest` (direct) |
| Evaluation input | `INTERMEDIATE` | `evaluation_input_digest` (direct) |
| Disposition records | `INTERMEDIATE` | `feasibility_digest` (direct) |
| Ranked records | `INTERMEDIATE` | `ranked_record_digest` (direct) |
| Top-N selection | `INTERMEDIATE` | `sha256_digest({"ordered_top_n_record_digests": list(...)})` |
| Result core | `RESULT` | `result_core_hash` (direct) |
| Optimizer | `OPTIMIZER` | `sha256_digest(optimizer_payload)` |

---

## 14. Error model

Phase 3 error codes added to existing `ErrorCode` enum. All messages entering hash/provenance/artifact use fixed deterministic strings. Prohibited: `str(exc)`, `repr(exc)`, `traceback`, addresses, runtime object representations.

---

## 15. Implementation boundary

### Existing files modified

| Path | Change |
|---|---|
| `src/hexagent/domain/messages.py` | Add Phase 3 error codes to `ErrorCode` |
| `src/hexagent/optimization/evaluation.py` | Export `build_engineering_message_descriptor` or import from internal |

### New files

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + 13-step verify |
| `src/hexagent/optimization/feasibility.py` | Feasibility + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Ranking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` + hash + external verifier |
| `tests/unit/test_task009_phase3_*.py` | Tests |

---

## 16. Test matrix

### 16.1 Phase 2 state paths

- [ ] Real VERIFIED record with `claimed_audit=None` accepted (Step 10)
- [ ] Each of the 10 RUNTIME_FAILED production paths accepted with correct audit presence
- [ ] Each of the 2 INTEGRITY_INVALID paths accepted
- [ ] UNEVALUATED path accepted
- [ ] Invalid audit presence by path rejected

### 16.2 Provider flag

- [ ] `provider_identity_matches == True` ⇔ `feasibility_status == NOT_EVALUATED`
- [ ] `provider_identity_matches == False` ⇔ `feasibility_status == PROVIDER_IDENTITY_MISMATCH`

### 16.3 Decimal

- [ ] `to_canonical_decimal()` accepts float, int, Decimal
- [ ] `to_canonical_decimal()` rejects bool, str, None
- [ ] `to_canonical_decimal()` rejects NaN, Inf
- [ ] `"1.00"`, `"+1"`, `"01"`, `"1E+0"`, `"-0"` rejected
- [ ] `"0"`, `"1"`, `"1.25"`, `"-1.25"` accepted

### 16.4 FEASIBLE classifier

- [ ] Exact FEASIBLE predicate (all conditions must hold)
- [ ] Exact diagnostic precedence (highest-priority failing condition)
- [ ] `SUCCEEDED` rating required to read thermal metrics
- [ ] `BLOCKED`/`FAILED` → INFEASIBLE, no duty/delta-T check

### 16.5 Disposition records

- [ ] INTEGRITY_FAILED source outcomes: FAILED/NOT_RUN
- [ ] PROVENANCE_FAILED source outcomes: PASSED/FAILED
- [ ] Non-FEASIBLE secondary engineering value rejected
- [ ] All disposition digests match strict regex
- [ ] FEASIBLE invariant: identity+evidence non-null, engineering values canonical
- [ ] Runtime failure from Phase 3 preserves source VERIFIED state
- [ ] RUNTIME_FAILED identity/evidence digest freeze

### 16.6 Ranked records

- [ ] `verify_digest()` passes for valid record
- [ ] `verify_digest()` fails when ranked_record_digest corrupted
- [ ] Rank values contiguous 1..F
- [ ] Ranked records must resolve to FEASIBLE disposition
- [ ] Ranked candidate IDs unique

### 16.7 Result external verifier

- [ ] Receives all authoritative artifacts (input, dispositions, ranked, graph)
- [ ] Input digest binding verified
- [ ] Disposition count/order/digests verified
- [ ] Ranked count/order/digests verified
- [ ] Top-N exact prefix verified
- [ ] Termination status agrees with input stop_index
- [ ] All 4 hash layers verified (core, provenance, envelope, UUID5)

### 16.8 Count equations

- [ ] All result counts non-negative
- [ ] Cross-equations verified: `phase2_verified == feasible + infeasible + provider_mismatch + runtime_failed_from_phase2_verified`
- [ ] Both count families sum to total

### 16.9 Digest format and uniqueness

- [ ] `sizing_request_identity_digest`, `passed_gate_digest`, `candidate_set_digest`, `evaluation_input_digest` all valid
- [ ] All disposition digests unique
- [ ] All ranked digests unique
- [ ] All Top-N digests unique

### 16.10 Warning/blocker

- [ ] Message context read exactly once (single-pass descriptors)
- [ ] Duplicate messages preserved
- [ ] `build_engineering_message_descriptor` reused

### 16.11 Provenance

- [ ] Zero-FEASIBLE graph connected (Evaluation Input → Top-N Selection → Result Core)
- [ ] All nodes reachable from unique root
- [ ] Algorithm version is exact fixed source `"task009-phase3-v1"`
- [ ] No runtime placeholder in optimizer payload
- [ ] Labels empty, metadata empty
- [ ] Every node reachable via graph-level verifier

### 16.12 Vocabulary

- [ ] `ordered_warning_digests` (correct spelling, not `ordere_warning_digests`)
- [ ] 13-step wording consistency

---

## 17. Acceptance criteria

1. All tests pass Python 3.11 and 3.12
2. `result_hash` deterministic and reproducible
3. Provenance DAG detects tampered nodes/edges
4. 13-step input verification fails closed for all steps
5. Top-N selection never exceeds feasible candidate count
6. No Phase 2 artifact mutated
7. PROVIDER_IDENTITY_MISMATCH never enters ranking/Top-N
8. UNEVALUATED never enters feasibility
9. Ruff, format, mypy strict, coverage pass
10. Pip-audit passes
11. Design review passes before implementation authorized

---

## 18. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED

Implementation must not begin until a separate engineering design review passes and a frozen contract commit SHA is established.
