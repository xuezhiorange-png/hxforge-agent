# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> ⚠️ This document is a **design contract** for review only. No implementation is authorized until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope

Phase 3 consumes Phase 2's real output — `tuple[CandidateEvaluationRecord, ...]` — through `Phase3EvaluationInput`, then produces a deterministic `OptimizationResult` with typed disposition records, ranked records, hash, and provenance.

---

## 2. Non-goals

Explicitly out of scope: TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver, candidate generation, catalog schema changes, Phase 2 artifact mutation, re-running TASK-008, recovering strict-stop.

---

## 3. Phase3EvaluationInput (P0-1, P0-9)

### 3.1 Model

```python
class Phase3EvaluationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int  # 1

    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str       # identity.sizing_request_identity_digest

    materialization_result: MaterializationResult
    candidate_set_digest: str                 # result.candidate_set.candidate_set_digest
    gate_digest: str                          # result.sizing_gate.gate_digest

    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int              # len(evaluation_records)

    ordered_evaluation_record_descriptor_digests: tuple[str, ...]

    evaluation_input_digest: str              # sha256_digest(evaluation_input_payload)
```

### 3.2 Digest bindings — all via existing API

All digest computations use **`sha256_digest()`** from `hexagent.core.canonical`. `sha256_digest()` internally calls `canonical_json()` on the primitive-only payload and returns `"sha256:<hex>"`. The caller never serialises to JSON; it passes the primitive-only dict/list/str directly.

| Digest | Computation | Source |
|---|---|---|
| `evaluation_record_descriptor_digest` | `sha256_digest(evaluation_record_descriptor_payload(record))` | Descriptor payload (§3.3) |
| `evaluation_failure_digest` | `sha256_digest(run_failure_payload(record.evaluation_failure))` | `run_failure_payload()` from `evaluation.py` |
| `evaluation_input_digest` | `sha256_digest(evaluation_input_payload)` | Input payload (§3.5) |
| `feasibility_digest` | `sha256_digest(candidate_disposition_payload(record))` | Disposition payload (§9.2) |
| `ranked_record_digest` | `sha256_digest(ranked_candidate_record_payload(record))` | Ranked payload (§10.4) |
| `result_core_hash` | `sha256_digest(result_core_payload)` | Core payload (§11.2) |
| `result_hash` | `sha256_digest({"result_core_hash": core_hash, "provenance_digest": prov_digest})` | Envelope |

Prohibited: `sha256(...)`, `hashlib.sha256(...)`, `sha256_digest(canonical_json(...))`, `sha256_digest(model_object)`, generic `model_dump` hashing.

### 3.3 Evaluation record descriptor payload

For each record at index `i`:

```python
def evaluation_record_descriptor_payload(
    record: CandidateEvaluationRecord,
) -> dict[str, object]:
    return {
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "evaluation_order_index": record.evaluation_order_index,   # NOT loop variable i
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
```

### 3.4 evaluation_input_payload

```python
def evaluation_input_payload(
    input: Phase3EvaluationInput,
) -> dict[str, object]:
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

### 3.5 12-step verify_or_raise() (P1-1)

**Step 1 — Type verification:** Each field is the exact expected Pydantic model type.

**Step 2 — materialization_result.verify_or_raise():** Existing method.

**Step 3 — Sizing identity digest:** Verify `sizing_request_identity_digest == identity.sizing_request_identity_digest`.

**Step 4 — candidate_set.verify_digest():** True check.

**Step 5 — sizing_gate.verify_digest():** True check.

**Step 6 — candidate_set ↔ sizing identity binding:** `candidate_set.sizing_request_identity_digest == sizing_request_identity_digest`.

**Step 7 — gate ↔ candidate_set binding:** `gate.gate_digest == candidate_set.passed_gate_digest`.

**Step 8 — Count verification:** `evaluation_record_count == len(records) == len(materialization_result.candidates) == len(ordered_descriptor_digests)`.

**Step 9 — Record ↔ candidate one-to-one binding:** For each `i`: `record.evaluation_order_index == i`, `candidate.evaluation_order_index == i`, `record.source_qualified_candidate_id == candidate.source_qualified_candidate_id == ordered_candidate_ids[i]`. No missing/extra/duplicate/displaced/skipped records.

**Step 10 — State field invariant verification:** For each record, verify every field matches the exhaustive matrix in §4.4. This includes state invariant validation, rating-status parity, required-numeric validation (SUCCEEDED metrics finite/non-null).

**Step 11 — Strict-stop invariant:** Verify stop index rule (§5.1).

**Step 12 — Descriptor digest verification:** For each `i`, compute `sha256_digest(evaluation_record_descriptor_payload(record[i]))` and verify it matches `ordered_evaluation_record_descriptor_digests[i]`.

**Step 13 — evaluation_input_digest verification:** Recompute and compare.

All failures raise `ValueError` with a fixed deterministic message. No `str(exc)`.

---

## 4. Phase 2 state matrix (P0-2, P0-11)

### 4.1 Exhaustive field matrix

For each `CandidateEvaluationState`, every field is frozen:

| Field | UNEVALUATED | VERIFIED | INTEGRITY_INVALID | RUNTIME_FAILED |
|---|---|---|---|---|
| `feasible` | `False` | `False` | `False` | `False` |
| `feasibility_status` | `NOT_EVALUATED` | `NOT_EVALUATED` or `PROVIDER_IDENTITY_MISMATCH` | `NOT_EVALUATED` | `NOT_EVALUATED` |
| `candidate_evaluation_identity` | `None` | `present` (`CandidateEvaluationIdentity`) | `None` | `None` |
| `verified_rating_evidence` | `None` | `present` (`VerifiedRatingEvidenceSnapshot`) | `None` | `None` |
| `invalid_rating_evidence` | `None` | `None` | `present` (`InvalidRatingEvidenceRecord`) | `None` |
| `evaluation_failure` | `None` | `None` | `None` | `present` (`RunFailure`) |
| `rating_status` | `None` | `str` (`RatingStatus.value`, must equal `evidence.rating_status.value`) | `None` | `None` |
| `claimed_rating_result_audit` | `None` | `present` (always built during Phase 2 verification) | `present` | `present` (always built, path-dependent) |
| `hash_verification_outcome` | `NOT_RUN` | `PASSED` | `FAILED` (hash false) or `PASSED` (provenance false) | `NOT_RUN`, `ERROR`, `PASSED`, or `PASSED` |
| `provenance_verification_outcome` | `NOT_RUN` | `PASSED` | `NOT_RUN` (hash false) or `FAILED` (provenance false) | `NOT_RUN`, `NOT_RUN`, `ERROR`, or `PASSED` |
| `provider_identity_matches` | `True` or `False` | `True` or `False` | `True` or `False` (typically `False`) | `True` or `False` |

### 4.2 Valid outcome combinations per state

#### VERIFIED — one valid combination

```
hash=PASSED, provenance=PASSED, evidence hash=PASSED, evidence provenance=PASSED
identity present, verified_evidence present, invalid_evidence=None
evaluation_failure=None, rating_status=evidence.rating_status.value
```

#### INTEGRITY_INVALID — two valid combinations (production evaluation.py lines)

| Hash outcome | Provenance outcome | Meaning |
|---|---|---|
| `FAILED` | `NOT_RUN` | `verify_hash()` returned False |
| `PASSED` | `FAILED` | `verify_provenance()` returned False |

Both: `invalid_evidence present`, `identity=None`, `verified_evidence=None`, `evaluation_failure=None`, `rating_status=None`.

#### RUNTIME_FAILED — four valid production paths

| Hash | Provenance | Phase 2 path in evaluation.py |
|---|---|---|
| `NOT_RUN` | `NOT_RUN` | Result type mismatch / execution failure before verification |
| `ERROR` | `NOT_RUN` | `verify_hash()` raised `Exception` |
| `PASSED` | `ERROR` | `verify_provenance()` raised `Exception` |
| `PASSED` | `PASSED` | Trusted evidence extraction/canonicalization failed |

All: `identity=None`, `verified_evidence=None`, `invalid_evidence=None`, `evaluation_failure present`.

#### UNEVALUATED — one valid combination

```
hash=NOT_RUN, provenance=NOT_RUN
identity=None, verified_evidence=None, invalid_evidence=None
evaluation_failure=None, rating_status=None
```

### 4.3 Invalid cross-field combinations

All combinations not listed in §4.2 are invalid. Key rejections (verified by Step 10):

| Pattern | Rejection reason |
|---|---|
| VERIFIED + identity=None | invariance violation |
| VERIFIED + invalid_evidence present | invariance violation |
| VERIFIED + evidence hash != PASSED | evidence verification conflict |
| INTEGRITY_INVALID + invalid_evidence=None | invariance violation |
| INTEGRITY_INVALID + identity present | invariance violation |
| INTEGRITY_INVALID + evidence present | invariance violation |
| INTEGRITY_INVALID + hash=PASSED+provenance=PASSED | contradictory — both passed but state is invalid |
| RUNTIME_FAILED + evaluation_failure=None | invariance violation |
| RUNTIME_FAILED + identity present | invariance violation |
| RUNTIME_FAILED + evidence present | invariance violation |
| UNEVALUATED + identity present | invariance violation |
| UNEVALUATED + evidence present | invariance violation |

### 4.4 Phase 2 → Phase 3 disposition

| Phase 2 state | provider matches | Phase 3 Disposition |
|---|---|---|
| UNEVALUATED | any | UNEVALUATED |
| VERIFIED | True | FEASIBLE or INFEASIBLE (by feasibility check) |
| VERIFIED | False | PROVIDER_IDENTITY_MISMATCH |
| INTEGRITY_INVALID (FAILED/NOT_RUN) | any | INTEGRITY_FAILED |
| INTEGRITY_INVALID (PASSED/FAILED) | any | PROVENANCE_FAILED |
| RUNTIME_FAILED | any | RUNTIME_FAILED |
| VERIFIED + Phase 3 feasibility exception | any | RUNTIME_FAILED (Phase 3 disposition; source state VERIFIED preserved) |

---

## 5. Strict-stop (P0-3)

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. If present: indices < stop_index must be VERIFIED; index == stop_index is INTEGRITY_INVALID or RUNTIME_FAILED; indices > stop_index must be UNEVALUATED.

`TerminationStatus.COMPLETE` = no strict-stop. `PARTIAL` = strict-stop occurred.

---

## 6. Decimal canonicalization (P0-5)

### 6.1 Canonical helpers

```python
from decimal import Decimal, InvalidOperation

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
    """Return canonical string — no exponent, no leading/trailing zeros, no +, -0→0."""
    normalized = canonical_decimal(value)
    return format(normalized, "f")
```

Rules:
- Only `format(d, "f")` — prohibits scientific notation
- `"-0"`, `"-0.0"`, `"0E-10"` → all become `"0"` (via `canonical_decimal`)
- Positive numbers never prefixed with `"+"`
- No leading zeros (`"01"` → rejected)
- No trailing zeros (`"1.00"` → rejected)
- No exponent notation (`"1E+0"` → rejected)
- Negative non-zero values keep their sign (e.g. `"-1.25"`)
- `bool` rejected with `TypeError`
- NaN, Inf, -Inf rejected with `ValueError`

### 6.2 Model validation

```python
parsed = Decimal(raw_value)
expected = canonical_decimal_string(parsed)
if raw_value != expected:
    raise ValueError(f"value is not canonical: got {raw_value!r}, expected {expected!r}")
```

Accepted: `"0"`, `"1"`, `"1.25"`, `"-1.25"`.
Rejected: `"1.00"`, `"+1"`, `"01"`, `"1E+0"`, `"-0"`.

### 6.3 Duty arithmetic (Decimal-only)

```python
required = to_canonical_decimal(required_duty_w)
abs_tol = to_canonical_decimal(duty_absolute_tolerance_w)
rel_tol = to_canonical_decimal(duty_relative_tolerance)
heat = to_canonical_decimal(heat_duty_w)
duty_tolerance = max(abs_tol, rel_tol * abs(required))
duty_error = abs(heat - required)
duty_satisfied = duty_error <= duty_tolerance
```

All arithmetic in Decimal. No float multiplication before conversion.

---

## 7. Count equations (P0-2, P0-3)

### 7.1 Phase 3 disposition counts (mutually exclusive, sum = total)

```
total == feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated
```

### 7.2 Phase 2 state audit counts (direct from source records)

```
phase2_verified              = count(state == VERIFIED)
phase2_integrity_invalid     = count(state == INTEGRITY_INVALID)
phase2_runtime_failed        = count(state == RUNTIME_FAILED)
phase2_unevaluated           = count(state == UNEVALUATED)

phase2_verified + phase2_integrity_invalid + phase2_runtime_failed + phase2_unevaluated == total
```

### 7.3 Cross-equations

```
runtime_failed = runtime_failed_from_phase2_verified + runtime_failed_from_phase2_runtime_failed

phase2_verified = feasible + infeasible + provider_mismatch + runtime_failed_from_phase2_verified

phase2_integrity_invalid = integrity_failed + provenance_failed

phase2_runtime_failed = runtime_failed_from_phase2_runtime_failed

phase2_unevaluated = unevaluated
```

`runtime_failed_from_phase2_verified` is the count of VERIFIED records that became RUNTIME_FAILED during Phase 3 feasibility classification. `runtime_failed_from_phase2_runtime_failed` is the count of records already in Phase 2 RUNTIME_FAILED state.

---

## 8. Feasibility

### 8.1 Single rule: trust TASK-008

`RatingStatus.SUCCEEDED` implies TASK-008 accepted convergence, energy closure, UA-LMTD closure. Phase 3 does not recompute.

### 8.2 Missing SUCCEEDED metric = Step 10 failure

`heat_duty_w`, `hot_outlet_temperature_k`, `cold_outlet_temperature_k`, `area_outer_m2` must be finite and non-null for VERIFIED+SUCCEEDED. Missing → input verification failure (Step 10).

### 8.3 Terminal delta-T

```
parallel:            delta_t_1 = hot_inlet - cold_inlet;  delta_t_2 = hot_outlet - cold_outlet
counterflow:         delta_t_1 = hot_inlet - cold_outlet;  delta_t_2 = hot_outlet - cold_inlet
min_terminal = min(delta_t_1_decimal, delta_t_2_decimal)
satisfied = min_terminal >= to_canonical_decimal(minimum_terminal_delta_t)
```

### 8.4 Diagnostic precedence

| Priority | DiagnosticKey |
|---|---|
| 1 | PROVIDER_IDENTITY_MISMATCH |
| 2 | RATING_BLOCKED |
| 3 | RATING_FAILED |
| 4 | DUTY_SHORTFALL |
| 5 | TERMINAL_DELTA_T_INADEQUATE |

---

## 9. CandidateDispositionRecord (P0-3)

### 9.1 Model

```python
class CandidateDispositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_qualified_candidate_id: str
    evaluation_order_index: int
    source_candidate_evaluation_state: CandidateEvaluationState
    source_record_descriptor_digest: str

    disposition: Phase3Disposition
    diagnostic: FeasibilityDiagnosticKey

    provider_identity_matches: bool
    rating_status: str | None

    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    invalid_rating_evidence_digest: str | None

    primary_engineering_value: str | None       # Canonical Decimal string; non-None only for FEASIBLE
    secondary_engineering_value: str | None     # Canonical Decimal string; non-None only for FEASIBLE

    ordered_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]
    failure_digest: str | None

    feasibility_digest: str                     # sha256_digest(candidate_disposition_payload(self))

    @model_validator(mode="after")
    def _validate_invariants(self) -> Self:
        # FEASIBLE must come from Phase 2 VERIFIED
        if self.disposition is Phase3Disposition.FEASIBLE:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
                raise ValueError("FEASIBLE requires source VERIFIED")
            if not self.candidate_evaluation_identity_digest:
                raise ValueError("FEASIBLE requires candidate_evaluation_identity_digest")
            if not self.verified_rating_evidence_digest:
                raise ValueError("FEASIBLE requires verified_rating_evidence_digest")
            if self.primary_engineering_value is None:
                raise ValueError("FEASIBLE requires primary_engineering_value")
            if self.secondary_engineering_value is None:
                raise ValueError("FEASIBLE requires secondary_engineering_value")

        # INTEGRITY_FAILED must come from Phase 2 INTEGRITY_INVALID with hash failure
        if self.disposition is Phase3Disposition.INTEGRITY_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("INTEGRITY_FAILED requires source INTEGRITY_INVALID")

        # PROVENANCE_FAILED must come from Phase 2 INTEGRITY_INVALID with provenance failure
        if self.disposition is Phase3Disposition.PROVENANCE_FAILED:
            if self.source_candidate_evaluation_state != CandidateEvaluationState.INTEGRITY_INVALID:
                raise ValueError("PROVENANCE_FAILED requires source INTEGRITY_INVALID")

        # RUNTIME_FAILED with source VERIFIED (Phase 3 feasibility exception)
        if self.disposition is Phase3Disposition.RUNTIME_FAILED:
            if self.source_candidate_evaluation_state not in (
                CandidateEvaluationState.VERIFIED,
                CandidateEvaluationState.RUNTIME_FAILED,
            ):
                raise ValueError("RUNTIME_FAILED source must be VERIFIED or RUNTIME_FAILED")

        # Non-FEASIBLE must not have engineering values
        if self.disposition is not Phase3Disposition.FEASIBLE:
            if self.primary_engineering_value is not None:
                raise ValueError("Non-FEASIBLE must not have engineering values")

        # failure_digest only for runtime failure dispositions
        if self.disposition in (Phase3Disposition.RUNTIME_FAILED,):
            if self.failure_digest is None:
                raise ValueError("RUNTIME_FAILED requires failure_digest")
        else:
            if self.failure_digest is not None:
                raise ValueError("Non-RUNTIME_FAILED must not have failure_digest")

        # diagnostic consistency
        if self.disposition is Phase3Disposition.FEASIBLE:
            if self.diagnostic != FeasibilityDiagnosticKey.NONE:
                raise ValueError("FEASIBLE must have diagnostic=NONE")

        # digest excludes itself
        return self

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("feasibility_digest mismatch")
```

### 9.2 Candidate disposition payload

```python
def candidate_disposition_payload(
    record: CandidateDispositionRecord,
) -> dict[str, object]:
    """Explicit payload — does NOT include feasibility_digest."""
    return {
        "source_qualified_candidate_id": record.source_qualified_candidate_id,
        "evaluation_order_index": record.evaluation_order_index,
        "source_candidate_evaluation_state": record.source_candidate_evaluation_state.value,
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

## 10. RankedCandidateRecord (P0-4)

### 10.1 Model

```python
class RankedCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int                                           # ≥ 1, contiguous
    source_qualified_candidate_id: str
    optimization_objective: OptimizationObjective

    primary_objective_value: str                        # canonical Decimal string
    primary_objective_field: str                        # "area_outer_m2" or "effective_length_m_canonical"
    secondary_tie_break_value: str                      # canonical Decimal string
    secondary_tie_break_field: str                      # the complementary field

    candidate_evaluation_identity_digest: str
    verified_rating_evidence_digest: str
    feasibility_digest: str

    ranked_record_digest: str                           # sha256_digest(ranked_candidate_record_payload(self))

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.rank < 1:
            raise ValueError("rank must be ≥ 1")
        # Canonical Decimal validation (see §6.2)
        for val, fname in [
            (self.primary_objective_value, "primary"),
            (self.secondary_tie_break_value, "secondary"),
        ]:
            d = Decimal(val)
            if not d.is_finite():
                raise ValueError(f"{fname}: must be finite, got {val!r}")
            expected = canonical_decimal_string(d)
            if val != expected:
                raise ValueError(f"{fname}: not canonical: {val!r} != {expected!r}")
        # Field/objective match
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
        # Digests format
        for dgst, name in [
            (self.candidate_evaluation_identity_digest, "candidate_eval_id"),
            (self.verified_rating_evidence_digest, "evidence_digest"),
            (self.feasibility_digest, "feasibility_digest"),
            (self.ranked_record_digest, "ranked_record_digest"),
        ]:
            if not dgst.startswith("sha256:") or len(dgst) != 71:
                raise ValueError(f"{name}: invalid digest format: {dgst!r}")
        return self
```

### 10.2 Field/objective binding

```
MINIMUM_OUTER_HEAT_TRANSFER_AREA:
    primary = "area_outer_m2"
    secondary = "effective_length_m_canonical"
MINIMUM_EFFECTIVE_LENGTH:
    primary = "effective_length_m_canonical"
    secondary = "area_outer_m2"
```

### 10.3 Sort keys

```
MIN_OA:  (canonical_decimal(area_outer_m2), canonical_decimal(Decimal(effective_length_m_canonical)), source_qualified_candidate_id)
MIN_LEN: (canonical_decimal(Decimal(effective_length_m_canonical)), canonical_decimal(area_outer_m2), source_qualified_candidate_id)
```

### 10.4 Ranked candidate record payload (non-self-referencing)

```python
def ranked_candidate_record_payload(
    record: RankedCandidateRecord,
) -> dict[str, object]:
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
    # Does NOT include ranked_record_digest
```

---

## 11. OptimizationResult (P0-6, P0-7)

### 11.1 Model

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int  # 1

    optimization_result_id: str             # canonical UUID string: str(uuid.uuid5(PHASE3_NS, result_hash))

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

    termination_status: TerminationStatus   # COMPLETE or PARTIAL only

    ordere_warning_digests: tuple[str, ...]
    ordered_blocker_digests: tuple[str, ...]

    result_core_hash: str
    provenance_digest: str
    result_hash: str

    top_level_failure: None  # Always None — per-candidate failures only in disposition records
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
        "ordered_warning_digests": list(result.ordere_warning_digests),
        "ordered_blocker_digests": list(result.ordered_blocker_digests),
    }
    # Does NOT include: optimization_result_id, result_core_hash, provenance_digest, result_hash
    # top_level_failure is excluded (always None)
```

### 11.3 Three-layer hash

```
result_core_hash = sha256_digest(result_core_payload(result))
provenance_digest = ProvenanceGraph.compute_hash()          # existing method
result_hash = sha256_digest({"result_core_hash": result_core_hash, "provenance_digest": provenance_digest})
optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))
```

`PHASE3_RESULT_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")`

### 11.4 Model-level invariants (P0-7)

```python
@model_validator(mode="after")
def _validate(self) -> Self:
    # schema_version
    if self.schema_version != 1:
        raise ValueError("schema_version must be 1")
    if self.requested_top_n < 1:
        raise ValueError("requested_top_n must be ≥ 1")
    # all counts ≥ 0
    for name, val in [
        ("total", self.total_candidate_count),
        ("feasible", self.feasible_candidate_count),
        # ... all counts
    ]:
        if val < 0:
            raise ValueError(f"{name}_count must be ≥ 0, got {val}")
    # Phase 3 disposition counts sum to total
    disp_sum = (
        self.feasible_candidate_count + self.infeasible_candidate_count
        + self.provider_mismatch_count + self.integrity_failed_count
        + self.provenance_failed_count + self.runtime_failed_count
        + self.unevaluated_count
    )
    if disp_sum != self.total_candidate_count:
        raise ValueError(f"disposition counts ({disp_sum}) != total ({self.total_candidate_count})")
    # Phase 2 state counts sum to total
    p2_sum = (
        self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count
        + self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count
    )
    if p2_sum != self.total_candidate_count:
        raise ValueError(f"Phase 2 state counts ({p2_sum}) != total ({self.total_candidate_count})")
    # Runtime failure cross-counts
    if self.runtime_failed_count != (
        self.runtime_failed_from_phase2_verified_count
        + self.runtime_failed_from_phase2_runtime_failed_count
    ):
        raise ValueError("runtime_failed cross-count mismatch")
    # Length invariants
    N = self.total_candidate_count
    if len(self.ordered_disposition_record_digests) != N:
        raise ValueError("disposition digests length != total")
    F = self.feasible_candidate_count
    if len(self.ordered_ranked_record_digests) != F:
        raise ValueError("ranked digests length != feasible count")
    TN = min(self.requested_top_n, F)
    if len(self.ordered_top_n_record_digests) != TN:
        raise ValueError("Top-N digests length != min(requested, feasible)")
    # Top-N = prefix of ranked
    if self.ordered_top_n_record_digests != self.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N digests must be exact prefix of ranked digests")
    # All digests format
    for name, dgst in self._all_digest_fields():
        if not dgst.startswith("sha256:") or len(dgst) != 71:
            raise ValueError(f"{name}: invalid digest: {dgst!r}")
    # optimization_result_id is canonical UUID
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, self.result_hash))
    if self.optimization_result_id != expected_id:
        raise ValueError("optimization_result_id mismatch")
    return self
```

### 11.5 verify_or_raise()

```python
def verify_or_raise(self) -> None:
    # 1. result_core_hash
    expected_core = sha256_digest(result_core_payload(self))
    if self.result_core_hash != expected_core:
        raise ValueError("result_core_hash mismatch")
    # 2. provenance_digest — recompute graph and compare
    # (provenance reconstruction delegated to provenance module)
    # 3. result_hash
    expected_hash = sha256_digest({"result_core_hash": self.result_core_hash, "provenance_digest": self.provenance_digest})
    if self.result_hash != expected_hash:
        raise ValueError("result_hash mismatch")
    # 4. optimization_result_id
    expected_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, self.result_hash))
    if self.optimization_result_id != expected_id:
        raise ValueError("optimization_result_id mismatch")
```

---

## 12. Provenance topology (P0-8, P0-9)

### 12.1 Root: always EXTERNAL

Phase 3 always uses `ProvenanceNodeType.EXTERNAL` as the root. No CASE_REVISION — the design case is not a Phase 3 input artifact.

Root payload:
```python
root_payload_hash = sha256_digest({
    "artifact_kind": "phase3_evaluation_input",
    "evaluation_input_digest": evaluation_input.evaluation_input_digest,
})
```

### 12.2 Label and metadata normative rule

Every Phase 3 `ProvenanceNode`:
- `label = ""` (empty string)
- `metadata = ()` (empty tuple)

Every Phase 3 `ProvenanceEdge`:
- `metadata = ()` (empty tuple)

No runtime-specific data, free text, or post-provenance fields enter metadata or labels.

Labels may only be non-empty if a specific frozen label string is defined per node role (none are required here).

### 12.3 Node types and payload_hash

Each `payload_hash` is either:
- An existing `"sha256:<hex>"` digest — used directly
- `sha256_digest(primitive_only_payload)` — produces `"sha256:<hex>"`

No double-prefixing. If source is already `"sha256:<hex>"`, assign as-is.

| Node role | `ProvenanceNodeType` | payload_hash |
|---|---|---|
| Root | `EXTERNAL` | `sha256_digest({"artifact_kind": "phase3_evaluation_input", "evaluation_input_digest": ...})` |
| Sizing request | `INPUT_FILE` | `sizing_request_identity_digest` (direct) |
| Passed sizing gate | `CALCULATION_RUN` | `gate_digest` (direct) |
| Materialized candidate set | `CALCULATION_RUN` | `candidate_set_digest` (direct) |
| Evaluation input | `INTERMEDIATE` | `evaluation_input_digest` (direct) |
| Each disposition record | `INTERMEDIATE` | disposition `feasibility_digest` (direct) |
| Each ranked record | `INTERMEDIATE` | ranked `ranked_record_digest` (direct) |
| Top-N selection | `INTERMEDIATE` | `sha256_digest({"ordered_top_n_record_digests": list(...)})` |
| Result core | `RESULT` | `result_core_hash` (direct) |
| Optimizer | `OPTIMIZER` | `sha256_digest(optimizer_payload)` — no post-provenance fields |

### 12.4 Unified UUID5 for all nodes

```python
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

node_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{node_type.value}:{payload_hash}")
```

Every node uses the same algorithm — root, sizing request, gate, records, Top-N, result, optimizer. No special cases.

### 12.5 Optimizer payload (no post-provenance fields)

```python
optimizer_payload = {
    "schema_version": 1,
    "evaluation_input_digest": evaluation_input.evaluation_input_digest,
    "optimization_objective": optimization_objective.value,
    "requested_top_n": requested_top_n,
    "termination_status": termination_status.value,
    "result_core_hash": result_core_hash,
    "phase3_policy_version": "1",
    "software_version": "<runtime>",
}
# Does NOT include: provenance_digest, result_hash, optimization_result_id, full OptimizationResult
```

### 12.6 Edge topology

```
Root ──regulates──► Sizing Request ──consumed_by──► Passed Sizing Gate
                                                         │ produced
                                                         ▼
                                                 Materialized Candidate Set
                                                         │ consumed_by
                                                         ▼
                                                 Evaluation Input
                                                         │ evaluated
                                                         ▼
                                                 Disposition Records
                                                         │ ranked (FEASIBLE only)
                                                         ▼
                                                 Ranked Records
                                                         │ selected (first N FEASIBLE)
                                                         ▼
                                                 Top-N Selection ──produced──► Result Core ──executed_by──► Optimizer
```

### 12.7 Graph verification

Uses existing `ProvenanceGraph.validate_graph()` — unique node IDs, edges reference existing nodes, no self-loops, acyclic, contains EXTERNAL or CASE_REVISION root, contains CALCULATION_RUN node.

`provenance_digest = ProvenanceGraph.compute_hash()`.

---

## 13. Warning/blocker canonicalization (P0-10)

### 13.1 Existing functions

Phase 3 reuses the existing production functions without modification:

- `engineering_message_sort_key()` from `evaluation.py` — imported as internal helper
- `engineering_message_payload()` from `evaluation.py` — already public
- `run_failure_payload()` from `evaluation.py` — already public

### 13.2 Sorting

```python
sorted_warnings = tuple(sorted(evidence.warnings, key=engineering_message_sort_key))
sorted_blockers = tuple(sorted(evidence.blockers, key=engineering_message_sort_key))
```

Warnings and blockers sorted separately. Duplicates preserved.

### 13.3 Message digests

```python
warning_digests = tuple(
    sha256_digest(engineering_message_payload(w))
    for w in sorted_warnings
)
blocker_digests = tuple(
    sha256_digest(engineering_message_payload(b))
    for b in sorted_blockers
)
```

No new context marker algorithm. No custom digest computation.

### 13.4 Failure digest

```python
failure_digest = (
    sha256_digest(run_failure_payload(evidence.failure))
    if evidence.failure is not None else None
)
```

---

## 14. Error model

Phase 3 error codes added to existing `ErrorCode` in `src/hexagent/domain/messages.py`. All messages entering hash/provenance/artifact use fixed deterministic strings. Prohibited: `str(exc)`, `repr(exc)`, `traceback`, addresses, runtime object representations.

---

## 15. Implementation boundary

### Existing files modified

| Path | Change |
|---|---|
| `src/hexagent/domain/messages.py` | Add Phase 3 error codes to `ErrorCode` |
| `src/hexagent/optimization/evaluation.py` | Export `engineering_message_sort_key` as public (add to `__all__`) |

### New files

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + `verify_or_raise()` |
| `src/hexagent/optimization/feasibility.py` | Feasibility + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Ranking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` + hash + provenance |
| `tests/unit/test_task009_phase3_*.py` | Tests |

---

## 16. Test matrix

### 16.1 Digest API

- [ ] `sha256_digest` receives primitive payload, not `canonical_json` string
- [ ] `sha256_digest` from `hexagent.core.canonical` used exclusively
- [ ] No `sha256(...)`, no `hashlib.sha256(...)` for Phase 3 artifacts

### 16.2 Phase 2 state counts

- [ ] All Phase 2 state audit counts computed directly from source record states
- [ ] `provenance_failed` counted under Phase 2 INTEGRITY_INVALID
- [ ] Runtime failure cross-count equations verified
- [ ] Both count families sum to total

### 16.3 Disposition records

- [ ] `CandidateDispositionRecord` payload excludes `feasibility_digest`
- [ ] `CandidateDispositionRecord` digest verifies
- [ ] Phase 3 runtime exception preserves source Phase 2 VERIFIED state
- [ ] FEASIBLE invariant (identity+evidence non-null)
- [ ] Non-FEASIBLE engineering values are None
- [ ] Provider mismatch mapped correctly

### 16.4 Ranked records

- [ ] `RankedCandidateRecord` payload excludes `ranked_record_digest`
- [ ] `RankedCandidateRecord` digest verifies
- [ ] Canonical Decimal accepted/rejected cases
- [ ] Field/objective binding validation

### 16.5 Decimal

- [ ] `"1.00"`, `"+1"`, `"01"`, `"1E+0"`, `"-0"` rejected
- [ ] `"0"`, `"1"`, `"1.25"`, `"-1.25"` accepted
- [ ] `bool` → TypeError
- [ ] NaN/Inf → ValueError

### 16.6 Result hash

- [ ] Full `result_core_payload` field sensitivity
- [ ] Excluded derived fields do not affect `result_core_hash`
- [ ] `result_hash` changes when `provenance_digest` changes
- [ ] Three-layer hash has no circular dependency
- [ ] Python 3.11/3.12 consistency

### 16.7 OptimizationResult invariants

- [ ] All counts non-negative
- [ ] Both count families sum to total
- [ ] Disposition/ranked/Top-N length equations
- [ ] Top-N is exact prefix of ranked
- [ ] Rank values contiguous 1..feasible_count
- [ ] All digest values match `sha256:[0-9a-f]{64}` format
- [ ] `optimization_result_id` is canonical UUID5

### 16.8 Termination

- [ ] COMPLETE iff `stop_index is None`
- [ ] PARTIAL iff `stop_index is not None`
- [ ] PARTIAL contains strict-stop warning

### 16.9 Provenance

- [ ] Labels are empty strings
- [ ] Node metadata is empty tuple
- [ ] Edge metadata is empty tuple
- [ ] EXTERNAL root with exact payload and ID
- [ ] All nodes use unique UUID5 algorithm
- [ ] No double-prefixing of existing digests
- [ ] Optimizer node has no post-provenance fields
- [ ] Only selected ranked records connect to Top-N

### 16.10 Warning/blocker

- [ ] Existing `engineering_message_sort_key` reused
- [ ] Existing `engineering_message_payload` reused
- [ ] Duplicate messages preserved
- [ ] RunFailure uses `run_failure_payload()`

### 16.11 State matrix

- [ ] Exhaustive Phase 2 record state fields per §4.1
- [ ] Each valid production path constructible
- [ ] Each invalid combination rejected

### 16.12 Vocabulary

- [ ] PR body DONE vocabulary consistent

---

## 17. Acceptance criteria

1. All tests pass on Python 3.11 and 3.12
2. `result_hash` deterministic and reproducible
3. Provenance DAG detects tampered nodes/edges
4. 12-step input verification fails closed for all steps
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
