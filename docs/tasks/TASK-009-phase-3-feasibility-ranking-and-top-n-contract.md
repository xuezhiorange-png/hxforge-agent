# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> ⚠️ This document is a **design contract** for review only. No implementation is authorized until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope

Phase 3 consumes Phase 2's real output — `tuple[CandidateEvaluationRecord, ...]` — through a single typed input artifact (`Phase3EvaluationInput`), then produces a deterministic, provenance-tracked `OptimizationResult`.

Phase 3 is responsible for:

- Typed immutable input artifact with real-existing digest bindings: `Phase3EvaluationInput`
- Complete 11-step input verification, including record↔candidate one-to-one binding
- Deterministic feasibility classification against the exact Phase 2 state invariants
- Deterministic ranking with per-objective complete ranking keys (two frozen objectives)
- Deterministic Top-N result construction from FEASIBLE candidates only
- Three-layer hash (core → provenance → envelope) with zero circular dependencies
- Executable provenance topology using `ProvenanceGraph` / `ProvenanceNode` / `ProvenanceEdge`
- Fail-closed semantics for all verification failures; typed error model compatible with `ErrorCode`

Phase 3 does **not** re-execute candidate generation, materialization, or TASK-008 `rate_double_pipe()`.

---

## 2. Non-goals

Explicitly out of scope:

- ❌ TASK-010 (versioned API)
- ❌ C4 (cost constraint)
- ❌ Pressure-drop calculation or constraint
- ❌ Velocity constraint
- ❌ Pump power estimation
- ❌ Economic / life-cycle / multi-objective Pareto optimization
- ❌ Stochastic or heuristic optimization
- ❌ ML ranking or scoring
- ❌ New heat-transfer correlations or rating solver logic
- ❌ Candidate generation or catalog schema changes
- ❌ Phase 2 artifact mutation
- ❌ Re-running TASK-008 for any candidate
- ❌ Recovering or reinterpreting Phase 2 strict-stop failures

---

## 3. Phase 3 input artifact: Phase3EvaluationInput (P0-1)

### 3.1 Model

```python
class Phase3EvaluationInput(BaseModel):
    """Complete typed input for Phase 3.

    Constructed from real Phase 2 outputs using existing digest properties
    — no generic sha256(object) calls.

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    schema_version: int  # 1

    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str  # identity property

    materialization_result: MaterializationResult
    candidate_set_digest: str            # materialization_result.candidate_set.candidate_set_digest
    gate_digest: str                     # materialization_result.sizing_gate.gate_digest

    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int  # == len(evaluation_records)

    evaluation_input_digest: str  # exact canonical payload below
```

### 3.2 Existing digest bindings — no generic sha256

| Field | Source |
|---|---|
| `sizing_request_identity_digest` | `sizing_request_identity.sizing_request_identity_digest` (property) |
| `candidate_set_digest` | `materialization_result.candidate_set.candidate_set_digest` (field) |
| `gate_digest` | `materialization_result.sizing_gate.gate_digest` (field) |
| `candidate_evaluation_identity_digest` | `record.candidate_evaluation_identity.candidate_evaluation_identity_digest` (property, if present) |
| `verified_rating_evidence_digest` | `verified_rating_evidence.compute_explicit_evidence_digest()` (method, if present) |
| `invalid_rating_evidence_digest` | `record.invalid_rating_evidence.invalid_evidence_digest` (property, if present) |
| `claimed_rating_result_audit_digest` | `record.claimed_rating_result_audit.audit_digest` (property, if present) |
| `evaluation_failure_digest` | `sha256(record.evaluation_failure)` via `canonical_json` (if present) |
| `candidate_set_digest` | `materialization_result.candidate_set.candidate_set_digest` |
| `gate_digest` | `materialization_result.sizing_gate.gate_digest` |

Prohibited: `sha256(materialization_result)`, `sha256(sizing_gate)`, `sha256(record)`, `sha256(evidence_snapshot)` — none of these are existing digest properties.

### 3.3 Evaluation record descriptor

For each record at index `i`, a deterministic `evaluation_record_descriptor` payload (primitive-only) is:

```
{
  "source_qualified_candidate_id": record.source_qualified_candidate_id,
  "evaluation_order_index": i,
  "candidate_evaluation_state": record.candidate_evaluation_state.value,
  "feasible": record.feasible,
  "feasibility_status": record.feasibility_status.value,
  "hash_verification_outcome": record.hash_verification_outcome.value,
  "provenance_verification_outcome": record.provenance_verification_outcome.value,
  "provider_identity_matches": record.provider_identity_matches,
  "rating_status": record.rating_status,
  "candidate_evaluation_identity_digest": <str or null>,
  "verified_rating_evidence_digest": <str or null>,
  "invalid_rating_evidence_digest": <str or null>,
  "claimed_rating_result_audit_digest": <str or null>,
  "evaluation_failure_digest": <str or null>,
}
```

Each `*_digest` field is obtained via the existing property/method listed in §3.2, or `null` when the corresponding Phase 2 field is `None`.

The `evaluation_record_descriptor_digest` for record `i` is `sha256(descriptor_payload)` using `canonical_json`.

### 3.4 evaluation_input_digest

```
evaluation_input_payload = {
  "schema_version": 1,
  "sizing_request_identity_digest": <str>,
  "candidate_set_digest": <str>,
  "gate_digest": <str>,
  "evaluation_record_count": N,
  "ordered_evaluation_record_descriptor_digests": [digest_0, digest_1, ..., digest_{N-1}],
}

evaluation_input_digest = sha256(canonical_json(evaluation_input_payload))
```

All payloads are **primitive-only** (str, int, list, null). No `model_dump`, no generic serializer, no `sha256(arbitrary_object)`.

### 3.5 verify_or_raise() — 11-step sequence

`Phase3EvaluationInput.verify_or_raise()` must execute the following checks in order. Any failure raises `ValueError` with a fixed deterministic message; no `str(exc)`.

1. **Exact type verification:** Verify `sizing_request_identity` is `SizingRequestIdentity`, `materialization_result` is `MaterializationResult`, each record is `CandidateEvaluationRecord`. Type errors raise.

2. **materialization_result.verify_or_raise():** Delegate to the existing `MaterializationResult.verify_or_raise()` which verifies gate digest, candidate set digest, catalog ref binding, etc.

3. **Sizing identity digest verification:** Verify `sizing_request_identity_digest == sizing_request_identity.sizing_request_identity_digest`.

4. **candidate_set.verify_digest():** Verify `materialization_result.candidate_set.verify_digest()` returns `True`.

5. **sizing_gate.verify_digest():** Verify `materialization_result.sizing_gate.verify_digest()` returns `True`.

6. **candidate_set ↔ sizing identity binding:** Verify `materialization_result.candidate_set.sizing_request_identity_digest == sizing_request_identity_digest`.

7. **gate ↔ candidate_set binding:** Verify `materialization_result.sizing_gate.gate_digest == materialization_result.candidate_set.passed_gate_digest`.

8. **Evaluation records count verification:** Verify `evaluation_record_count == len(evaluation_records)` and `evaluation_record_count == len(materialization_result.candidates)`.

9. **Record ↔ candidate one-to-one binding:** For each index `i`:
   - `record.evaluation_order_index == i`
   - `candidate.evaluation_order_index == i`
   - `record.source_qualified_candidate_id == candidate.source_qualified_candidate_id`
   - `record.source_qualified_candidate_id == candidate_set.ordered_candidate_ids[i]`
   - No missing record, no extra record, no duplicate ID, no displaced record, no skipped index, no record whose order differs from Phase 2 materialization order.

10. **Complete ordered record descriptor verification:** For each index `i`, compute `evaluation_record_descriptor_digest` per §3.3. Verify the computed digest matches the expected ordered list. Any mismatch indicates tampered record fields, displaced record, or insertion-order violation.

11. **evaluation_input_digest verification:** Recompute `evaluation_input_digest` per §3.4 and verify it matches the stored field.

---

## 4. Phase 2 state invariants (P0-2)

### 4.1 Real Phase 2 state enum

```python
class CandidateEvaluationState(StrEnum):
    UNEVALUATED = "unevaluated"
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"
```

### 4.2 Real Phase 2 verification outcomes

```python
class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
```

### 4.3 Real Phase 2 verification outcomes on VerifiedRatingEvidenceSnapshot

The `VerifiedRatingEvidenceSnapshot` model itself requires:
```python
hash_verification_outcome == VerificationOutcome.PASSED
provenance_verification_outcome == VerificationOutcome.PASSED
```

Therefore a `VERIFIED` record **always** has hash=PASSED and provenance=PASSED at the evidence level.

### 4.4 Valid record state matrix

Only the following field combinations are **valid constructible Phase 2 records**:

| State | identity | verified evidence | invalid evidence | hash outcome | provenance outcome | rating_status | provider matches |
|---|---|---|---|---|---|---|---|
| UNEVALUATED | None | None | None | NOT_RUN | NOT_RUN | None | any |
| VERIFIED | present | present | None | PASSED | PASSED | SUCCEEDED/BLOCKED/FAILED | any |
| INTEGRITY_INVALID | None | None | present | FAILED/ERROR | NOT_RUN/FAILED/ERROR | None | any |
| RUNTIME_FAILED | None | None | None | NOT_RUN | NOT_RUN | None | any |

### 4.5 Invalid cross-field combinations rejected at Phase 3 input boundary

The following **cannot** occur in a Phase 2 record due to `CandidateEvaluationRecord._verify_state_invariants()`, but if they somehow reach Phase 3 (corrupted data, serialization error), `Phase3EvaluationInput.verify_or_raise()` must reject them:

| Invalid pattern | Rejection behaviour |
|---|---|
| VERIFIED + identity=None | Input verification failure |
| VERIFIED + evidence=None | Input verification failure |
| VERIFIED + invalid_evidence present | Input verification failure |
| VERIFIED + hash=PASSED + evidence.hash!=PASSED | Input verification failure |
| INTEGRITY_INVALID + invalid_evidence=None | Input verification failure |
| INTEGRITY_INVALID + identity present | Input verification failure |
| INTEGRITY_INVALID + evidence present | Input verification failure |
| RUNTIME_FAILED + evaluation_failure=None | Input verification failure |
| RUNTIME_FAILED + identity present | Input verification failure |
| UNEVALUATED + identity present | Input verification failure |
| UNEVALUATED + evidence present | Input verification failure |

These are invariant violations, not candidate dispositions. They represent data corruption or programming error and must prevent any Phase 3 processing.

### 4.6 Phase 2 → Phase 3 disposition mapping

For records passing the invariant checks above:

| Phase 2 state | Evidence hash | Evidence provenance | provider matches | Phase 3 Disposition |
|---|---|---|---|---|
| UNEVALUATED | NOT_RUN | NOT_RUN | any | **UNEVALUATED** |
| VERIFIED | PASSED | PASSED | True | **FEASIBLE or INFEASIBLE** (by feasibility check) |
| VERIFIED | PASSED | PASSED | False | **PROVIDER_IDENTITY_MISMATCH** |
| INTEGRITY_INVALID | FAILED/ERROR | NOT_RUN/FAILED/ERROR | any | **INTEGRITY_FAILED** (audit subtype from `invalid_evidence.hash/provenance`) |
| RUNTIME_FAILED | NOT_RUN | NOT_RUN | any | **RUNTIME_FAILED** |

### 4.7 Phase 3 disposition enum

```python
class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    UNEVALUATED = "unevaluated"
    INTEGRITY_FAILED = "integrity_failed"
    PROVENANCE_FAILED = "provenance_failed"   # Produced from INTEGRITY_INVALID records
                                              # where invalid_evidence.provenance_verification_outcome==FAILED/ERROR
    RUNTIME_FAILED = "runtime_failed"
```

### 4.8 Engineering-rank-eligibility

A candidate is **engineering-rank-eligible** only when:
- disposition == `FEASIBLE`
- `provider_identity_matches == True`
- All numerical fields required for ranking are finite and non-null

The following dispositions are **never** engineering-rank-eligible:
- `INFEASIBLE` — engineering constraints not met
- `PROVIDER_IDENTITY_MISMATCH` — mismatched provider
- `UNEVALUATED` — no TASK-008 call was attempted
- `INTEGRITY_FAILED` — evidence hash or integrity verification failed
- `PROVENANCE_FAILED` — evidence provenance verification failed
- `RUNTIME_FAILED` — TASK-008 raised or returned evaluation failure

---

## 5. Strict-stop invariants (P0-3)

### 5.1 Exact strict-stop detection

Define `stop_index` as the first index `s` where `record.candidate_evaluation_state` is:

```
CandidateEvaluationState.INTEGRITY_INVALID
CandidateEvaluationState.RUNTIME_FAILED
```

If no such index exists, `stop_index = None` (no strict-stop occurred).

### 5.2 Invariant

If `stop_index` is not `None`:

```
all indices < stop_index:
    state may be VERIFIED only (UNEVALUATED/INTEGRITY_INVALID/RUNTIME_FAILED not allowed before stop)

index == stop_index:
    state == INTEGRITY_INVALID or RUNTIME_FAILED

all indices > stop_index:
    state == UNEVALUATED
    no VERIFIED/INTEGRITY_INVALID/RUNTIME_FAILED after stop_index
```

If this invariant is violated, `Phase3EvaluationInput.verify_or_raise()` must reject the input.

### 5.3 Covered scenarios

| Scenario | stop_index | Earlier records | Later records |
|---|---|---|---|
| No strict-stop | None | All VERIFIED (or mixed VERIFIED/BLOCKED/FAILED) | N/A |
| First candidate fails | 0 | None | All UNEVALUATED |
| Middle candidate fails | k (0 < k < N-1) | k VERIFIED records | N-k-1 UNEVALUATED |
| Last candidate fails | N-1 | N-1 VERIFIED records | 0 UNEVALUATED |
| Failure with earlier FEASIBLE | k | Some VERIFIED+FEASIBLE before k | UNEVALUATED |
| Failure with no earlier FEASIBLE | k | All VERIFIED but INFEASIBLE before k | UNEVALUATED |

### 5.4 Phase 3 honouring strict-stop

- UNEVALUATED records are not evaluated for feasibility
- UNEVALUATED records do not receive an engineering rank
- UNEVALUATED records are counted in `unevaluated_count`
- Phase 3 must not re-run any TASK-008 call
- Phase 3 must not skip, reorder, or recover UNEVALUATED records
- Feasibility classification encountering an unexpected `Exception` for a specific candidate → that candidate receives runtime failure, not INFEASIBLE
- Feasibility exception that prevents continuation of the entire batch → `TerminationStatus.FAILED`

---

## 6. Numeric canonicalization (P0-4)

### 6.1 Mandatory Decimal conversion

All numeric values participating in feasibility comparison or ranking **must** be converted to `Decimal` as follows:

```
Decimal(str(finite_float)).normalize()
```

`normalize()` strips trailing zeros, so `Decimal("1.0")` and `Decimal("1")` both yield `Decimal("1")`, ensuring deterministic comparison.

### 6.2 Per-field conversion

| Field | Type in Phase 2 | Decimal conversion |
|---|---|---|
| `area_outer_m2` | `float` (finite) | `Decimal(str(area_outer_m2)).normalize()` |
| `heat_duty_w` | `float` (finite) | `Decimal(str(heat_duty_w)).normalize()` |
| `required_duty_w` | `float` (finite) | `Decimal(str(required_duty_w)).normalize()` |
| `energy_residual_w` | `float` (finite or None) | `Decimal(str(v)).normalize()` if not None |
| `ua_lmtd_residual_w` | `float` (finite or None) | `Decimal(str(v)).normalize()` if not None |
| `effective_length_m_canonical` | `str` (Decimal string) | `Decimal(effective_length_m_canonical).normalize()` |

### 6.3 Finite check

Every numeric value consumed from Phase 2 **must** pass `math.isfinite()` at the Phase 3 consumer boundary before Decimal conversion. If a non-finite value (NaN, Inf, -Inf) is detected, raise `ValueError` with a fixed deterministic message. This is required because the review explicitly requires Phase 3 to re-validate, not trust Phase 2 implicitly.

### 6.4 Rejected types

- `bool` is rejected: `raise TypeError("bool is not a valid numeric type")` — never auto-convert `True`→1 or `False`→0
- `-0.0`: `Decimal(str(-0.0))` produces `Decimal("-0")` and `normalize()` produces `Decimal("-0")`. Phase 3 must treat `-0` and `0` as equal: use `normalize()` + `abs()` for comparisons, or rely on `Decimal("0") == Decimal("-0")` being `True` (Python Decimal equality already treats `-0 == 0` as True).

### 6.5 Canonical string representation

For hash/provenance, the canonical representation of each numeric value is `str(decimal.normalize())` (stripped of trailing zeros, no exponent unless necessary).

Canonical zero: `Decimal("0")` → string `"0"`.

### 6.6 Python 3.11/3.12 consistency

`Decimal(str(finite_float)).normalize()` produces identical results across Python 3.11 and 3.12, as verified by the existing `Decimal` specification.

---

## 7. Ranking registry (P0-5)

### 7.1 Source fields

`effective_length_m_canonical` comes from `ManufacturableCandidate.effective_length_m_canonical` (a `str`). The record↔candidate binding (step 9 of `verify_or_raise()`) must be completed **before** reading this field. The `ManufacturableCandidate` at index `i` in `materialization_result.candidates` corresponds to `evaluation_records[i]`.

`area_outer_m2` comes from `VerifiedRatingEvidenceSnapshot.area_outer_m2` (a finite `float`).

### 7.2 Non-null invariant for FEASIBLE candidates

For any candidate with `Phase3Disposition.FEASIBLE`, all fields participating in ranking **must** be non-null and finite:

- `area_outer_m2`: must be non-null (verified evidence has non-null `area_outer_m2`)
- `effective_length_m_canonical`: must be non-null (every `ManufacturableCandidate` has it)
- `heat_duty_w`: required for duty feasibility check
- `hot_outlet_temperature_k`: required for terminal delta-T (if SUCCEEDED)
- `cold_outlet_temperature_k`: required for terminal delta-T (if SUCCEEDED)

If any required field is null or non-finite for a VERIFIED+SUCCEEDED record, this is an artifact invariant failure — the record does not receive FEASIBLE and the Phase 3 implementation must raise or block at the input verification boundary (step 10), not silently skip.

### 7.3 RankedCandidateRecord non-null fields

`RankedCandidateRecord` is only created for FEASIBLE candidates. Therefore:

- `primary_objective_value`: non-null `Decimal` (normalized)
- `secondary_tie_break_value`: non-null `Decimal` (normalized)
- `source_qualified_candidate_id`: non-null `str`
- All digests: non-null `str`

### 7.4 Optimization objective enum

```python
class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"
```

### 7.5 Per-objective complete sort keys

#### MINIMUM_OUTER_HEAT_TRANSFER_AREA

```
sort_key = (
    Decimal(str(area_outer_m2)).normalize(),
    Decimal(effective_length_m_canonical).normalize(),
    source_qualified_candidate_id,   # ASCII ascending, final tie-break
)
```

| Level | Field | Decimal source | Direction | Non-null? |
|---|---|---|---|---|
| 1 | `area_outer_m2` | `Decimal(str(area_outer_m2)).normalize()` | Ascending | Yes (FEASIBLE invariant) |
| 2 | `effective_length_m_canonical` | `Decimal(effective_length_m_canonical).normalize()` | Ascending | Yes (FEASIBLE invariant) |
| 3 | `source_qualified_candidate_id` | — | ASCII ascending | Yes |

#### MINIMUM_EFFECTIVE_LENGTH

```
sort_key = (
    Decimal(effective_length_m_canonical).normalize(),
    Decimal(str(area_outer_m2)).normalize(),
    source_qualified_candidate_id,   # ASCII ascending, final tie-break
)
```

| Level | Field | Decimal source | Direction | Non-null? |
|---|---|---|---|---|
| 1 | `effective_length_m_canonical` | `Decimal(effective_length_m_canonical).normalize()` | Ascending | Yes (FEASIBLE invariant) |
| 2 | `area_outer_m2` | `Decimal(str(area_outer_m2)).normalize()` | Ascending | Yes (FEASIBLE invariant) |
| 3 | `source_qualified_candidate_id` | — | ASCII ascending | Yes |

### 7.6 RankedCandidateRecord payload

```python
class RankedCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int                                              # 1-based rank
    source_qualified_candidate_id: str
    optimization_objective: OptimizationObjective          # typed enum, not string
    primary_objective_value: str                           # Decimal.normalize() canonical string
    primary_objective_field: str                           # e.g. "area_outer_m2"
    secondary_tie_break_value: str                         # Decimal canonical string
    secondary_tie_break_field: str                         # e.g. "effective_length_m_canonical"
    candidate_evaluation_identity_digest: str
    verified_rating_evidence_digest: str
    feasibility_digest: str                                # SHA-256 of CandidateDispositionRecord payload
    ranked_record_digest: str                              # SHA-256 of this record's canonical payload
```

All `*_value` fields for FEASIBLE candidates are non-null. Non-null invariant is enforced at ranking entry, not at the model level.

---

## 8. Executable feasibility (P0-6)

### 8.1 Single normative rule: trust TASK-008 verdict

`RatingStatus.SUCCEEDED` means TASK-008 accepted solver convergence, energy closure, final-state consistency, and UA-LMTD closure. Phase 3 **trusts** this verdict and does **not** recompute those closures.

This is the **single normative rule**. There is no "Option B".

### 8.2 RatingStatus → disposition

| `rating_status` value | Phase 3 disposition |
|---|---|
| `RatingStatus.SUCCEEDED` | Continues to duty / delta-T feasibility checks |
| `RatingStatus.BLOCKED` | **INFEASIBLE** — diagnostic: `RATING_BLOCKED` |
| `RatingStatus.FAILED` | **INFEASIBLE** — diagnostic: `RATING_FAILED` |
| `None` | As per state mapping (§4.6) |

Phase 3 verifies: `record.rating_status == evidence.rating_status.value`. Any mismatch is an input verification failure (step 10).

### 8.3 Required fields for SUCCEEDED

For `VERIFIED + rating_status == SUCCEEDED`, the following must be non-null and finite:

- `heat_duty_w`
- `hot_outlet_temperature_k`
- `cold_outlet_temperature_k`
- `area_outer_m2`

If any is null or non-finite, this is an artifact invariant failure — raise at step 10 of `verify_or_raise()`. Do not "skip terminal delta-T check".

### 8.4 Duty satisfaction

```
duty_tolerance_w = max(
    duty_absolute_tolerance_w,                                          # float from SizingRequestIdentity
    duty_relative_tolerance * abs(required_duty_w),                     # relative fraction
)

duty_tolerance_decimal = Decimal(str(duty_tolerance_w)).normalize()
duty_error_decimal = abs(Decimal(str(heat_duty_w)).normalize() - Decimal(str(required_duty_w)).normalize())

duty_satisfied = duty_error_decimal <= duty_tolerance_decimal
```

Where:
- `heat_duty_w` from `VerifiedRatingEvidenceSnapshot.heat_duty_w` (finite float, TASK-008 output)
- `required_duty_w`, `duty_absolute_tolerance_w`, `duty_relative_tolerance` from `SizingRequestIdentity`

**Sign convention:** positive heat transfer from hot side to cold side. The absolute value ensures magnitude check is sign-independent.

### 8.5 Terminal delta-T

Flow arrangement tokens (from `FlowArrangement` StrEnum):

```
parallel:          # FlowArrangement.PARALLEL = "parallel"
    delta_t_1 = hot_inlet - cold_inlet
    delta_t_2 = hot_outlet - cold_outlet

counterflow:       # FlowArrangement.COUNTERFLOW = "counterflow"
    delta_t_1 = hot_inlet - cold_outlet
    delta_t_2 = hot_outlet - cold_inlet
```

Where:
- `hot_inlet` = `SizingRequestIdentity.hot_inlet_temperature_k`
- `cold_inlet` = `SizingRequestIdentity.cold_inlet_temperature_k`
- `hot_outlet` = `VerifiedRatingEvidenceSnapshot.hot_outlet_temperature_k` (SUCCEEDED: non-null)
- `cold_outlet` = `VerifiedRatingEvidenceSnapshot.cold_outlet_temperature_k` (SUCCEEDED: non-null)

```
minimum_actual_terminal_delta_t = min(delta_t_1_decimal, delta_t_2_decimal)
terminal_delta_t_satisfied = minimum_actual_terminal_delta_t >= Decimal(str(minimum_terminal_delta_t)).normalize()
```

All temperatures are `Decimal(str(float)).normalize()`.

### 8.6 Energy closure and UA-LMTD closure

**Trusted:** `RatingStatus.SUCCEEDED` implies TASK-008 accepted energy balance and UA-LMTD consistency. Phase 3 does not recompute these.

### 8.7 Diagnostic precedence

Multiple infeasibility conditions → single deterministic diagnostic:

| Priority | DiagnosticKey | Condition |
|---|---|---|
| 1 | `PROVIDER_IDENTITY_MISMATCH` | `record.provider_identity_matches == False` |
| 2 | `RATING_BLOCKED` | `rating_status == BLOCKED` |
| 3 | `RATING_FAILED` | `rating_status == FAILED` |
| 4 | `MISSING_TRUSTED_METRIC` | Required SUCCEEDED field is null/non-finite |
| 5 | `DUTY_SHORTFALL` | `duty_satisfied == False` |
| 6 | `TERMINAL_DELTA_T_INADEQUATE` | `terminal_delta_t_satisfied == False` |

```python
class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"
    RATING_FAILED = "rating_failed"
    MISSING_TRUSTED_METRIC = "missing_trusted_metric"
    DUTY_SHORTFALL = "duty_shortfall"
    TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
```

### 8.8 Exception boundaries

| Exception scope | Behaviour |
|---|---|
| Per-candidate feasibility check raises `Exception` (not `BaseException`) | Candidate receives `RUNTIME_FAILED` disposition; batch continues |
| Entire feasibility phase raises unexpected `Exception` | Batch terminates; `TerminationStatus.FAILED` |
| Input verification raises (step 1-11) | No `OptimizationResult` produced; exception propagates upward |
| `BaseException` | Never caught; propagates. `KeyboardInterrupt`, `SystemExit`, `GeneratorExit` are not silenced |

There is no "per-candidate unless prevents continuation" — the exact rules above replace that.

---

## 9. Top-N (P0-7)

### 9.1 Source and validation

`requested_top_n` = `SizingRequestIdentity.top_n` (validated as `strict int >= 1` at Phase 2 boundary).

If `requested_top_n < 1` at Phase 3 input, `verify_or_raise()` rejects.

### 9.2 Selection

- Top-N is selected **only** from FEASIBLE candidates
- Selection occurs **after** full deterministic sort of all FEASIBLE candidates
- If feasible count < N: all feasible candidates returned (no padding)
- If feasible count == 0: empty `ordered_top_n_record_digests`
- Top-N does not alter candidate identity, hash, evaluation record, or disposition
- Full ranked list preserved in `ordered_ranked_record_digests`; Top-N is a strict subset

---

## 10. Termination invariants (P0-3)

### 10.1 Typed enum

```python
class TerminationStatus(StrEnum):
    COMPLETE = "complete"    # No strict-stop. All records processed for feasibility/ranking.
    PARTIAL = "partial"      # Strict-stop occurred (stop_index is not None).
                              # Records before stop_index processed normally.
                              # Top-N from indices < stop_index only.
    FAILED = "failed"        # Unrecoverable: input verification failed or global Phase 3 exception.
```

### 10.2 Exact predicates

| Status | Condition | Has ranked records? | Has Top-N? | Has result_hash? | Has provenance? |
|---|---|---|---|---|---|
| **COMPLETE** | `stop_index is None` (no strict-stop) | Yes (may be empty if 0 FEASIBLE) | Yes (may be empty) | Yes | Yes |
| **PARTIAL** | `stop_index is not None` | Yes (from indices < stop_index only) | Yes (from FEASIBLE with index < stop_index only) | Yes | Yes; strict-stop warning included in `warnings` |
| **FAILED** | Input verification failure (step 1-11) or global Phase 3 exception | No | No | No (if input verify failed); Yes (if global exception after successful input verify) | Conditional on having result |

### 10.3 Failed + Top-N rules

If `TerminationStatus.PARTIAL`, Top-N may be selected from FEASIBLE candidates with index `< stop_index`. The result hash covers those records, and a strict-stop warning must be included.

If `TerminationStatus.FAILED` due to global exception after input verification succeeded, the `OptimizationResult` carries the partial components but `Top-N` is empty and `ordered_ranked_record_digests` contains whatever was computed before the failure.

---

## 11. Data models (P0-9)

### 11.1 CandidateDispositionRecord

```python
class CandidateDispositionRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_qualified_candidate_id: str
    evaluation_order_index: int
    candidate_evaluation_state: CandidateEvaluationState
    disposition: Phase3Disposition
    infeasibility_diagnostic: FeasibilityDiagnosticKey  # NONE if FEASIBLE or non-rank-eligible
    candidate_evaluation_identity_digest: str | None
    verified_rating_evidence_digest: str | None
    engineering_objective_value: str | None  # Decimal canonical string; non-null only for FEASIBLE
    tie_break_value: str | None              # Decimal canonical string; non-null only for FEASIBLE
    feasibility_digest: str                  # SHA-256 of canonical disposition payload
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
```

### 11.2 RankedCandidateRecord

Only created for FEASIBLE candidates (see §7.6).

### 11.3 OptimizationResult

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int

    # Upstream bindings
    sizing_request_identity_digest: str
    passed_gate_digest: str
    candidate_set_digest: str
    evaluation_input_digest: str

    # Objective
    optimization_objective: OptimizationObjective   # typed enum
    requested_top_n: int

    # Counts (disjoint, sum = total)
    total_candidate_count: int
    verified_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int
    provenance_failed_count: int

    # Ordered record digests
    ordered_disposition_record_digests: tuple[str, ...]   # Full Phase 2 order
    ordered_ranked_record_digests: tuple[str, ...]         # FEASIBLE only, ranking order
    ordered_top_n_record_digests: tuple[str, ...]          # Top-N subset of ranked

    termination_status: TerminationStatus

    # Typed messages (not free-form strings)
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None

    # Identifiers (non-circular — see §12)
    optimization_result_id: str                 # UUID5(PHASE3_NAMESPACE, result_hash)
    result_core_hash: str                       # SHA-256 of core payload (excludes derived fields)
    provenance_digest: str                      # SHA-256 of provenance graph
    result_hash: str                            # SHA-256 of {core_hash, provenance_digest}
```

### 11.4 Count equations

```
total = verified + integrity_failed + runtime_failed + unevaluated

verified = feasible + infeasible + provider_mismatch + provenance_failed
```

No overlap: each candidate is counted exactly once in `total`. Within `verified`, each candidate is counted exactly once in one of the four sub-categories.

---

## 12. Three-layer hash scheme (P0-7)

### 12.1 Construction order (no cycles)

```
Step 1: result_core_payload (excludes optimization_result_id, result_core_hash, provenance_digest, result_hash)
Step 2: result_core_hash = sha256(canonical_json(result_core_payload))

Step 3: provenance graph built; each node's payload_hash uses result_core_hash for the result node
Step 4: provenance_digest = ProvenanceGraph.compute_hash()  # uses existing method

Step 5: result_hash = sha256(canonical_json({
            "result_core_hash": result_core_hash,
            "provenance_digest": provenance_digest,
        }))

Step 6: optimization_result_id = uuid5(PHASE3_RESULT_NAMESPACE, result_hash)
```

### 12.2 Namespace UUID

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")  # DNS namespace
```

The UUID5 name is the `result_hash` string. `optimization_result_id = uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash)`.

### 12.3 result_core_payload

The `result_core_payload` is the canonical dict of:

```
schema_version
sizing_request_identity_digest
passed_gate_digest
candidate_set_digest
evaluation_input_digest
optimization_objective.value
requested_top_n
total_candidate_count
verified_candidate_count
feasible_candidate_count
infeasible_candidate_count
provider_mismatch_count
integrity_failed_count
runtime_failed_count
unevaluated_count
provenance_failed_count
ordered_disposition_record_digests     (ordered string list)
ordered_ranked_record_digests          (ordered string list)
ordered_top_n_record_digests           (ordered string list)
termination_status.value
warnings                                (ordered canonical warning digests)
blockers                                (ordered canonical blocker digests)
failure                                 (canonical failure digest or null)
```

### 12.4 What each hash binds

| Hash | Binds |
|---|---|
| `result_core_hash` | All upstream digests, all counts, all disposition/ranked/Top-N digests, termination status, messages. Does **not** include `provenance_digest`. |
| `provenance_digest` | Full provenance graph including a node whose payload_hash = `"sha256:" + result_core_hash`. |
| `result_hash` | Both `result_core_hash` and `provenance_digest`. |

### 12.5 Verification order

1. Recompute `result_core_payload` → `result_core_hash`' (compare to stored)
2. Rebuild provenance graph → `provenance_digest`' (compare to stored)
3. Recompute `result_hash`' (compare to stored, includes both digests)
4. Recompute `optimization_result_id` (compare to stored)

The result provenance node's payload uses `result_core_hash` (not `result_hash`), so that the provenance graph can be verified independently of the outer envelope.

---

## 13. Executable provenance topology (P0-8)

### 13.1 Node types (exact `ProvenanceNodeType` values)

| Node role | `ProvenanceNodeType` | payload_hash content |
|---|---|---|
| Root (with design case) | `CASE_REVISION` | `sha256:{design_case_revision_id}` |
| Root (without design case) | `EXTERNAL` | `sha256:{sizing_request_identity_digest}` |
| Sizing request | `INPUT_FILE` | `sha256:{sizing_request_identity_digest}` |
| Passed sizing gate | `CALCULATION_RUN` | `sha256:{gate_digest}` |
| Materialized candidate set | `CALCULATION_RUN` | `sha256:{candidate_set_digest}` |
| Evaluation input | `INTERMEDIATE` | `sha256:{evaluation_input_digest}` |
| Each disposition record | `INTERMEDIATE` | `sha256:{feasibility_digest}` |
| Each ranked record | `INTERMEDIATE` | `sha256:{ranked_record_digest}` |
| Top-N selection | `INTERMEDIATE` | `sha256:{ordered_top_n_digests_list}` |
| Result core | `RESULT` | `"sha256:" + result_core_hash` |
| Calculation run / optimizer | `OPTIMIZER` | `sha256:{full_optimization_result_metadata}` |

### 13.2 UUID5 for node_id

Every node uses a deterministic UUID5:
```python
node_id = uuid5(PROVENANCE_NAMESPACE, node_type.value + ":" + payload_hash)
```
Where `PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")` (DNS namespace).

This ensures reprodcibility: identical inputs produce identical provenance graph.

### 13.3 Edge topology

```
Root──regulates──►Sizing Request──consumed_by──►Passed Sizing Gate
                                                      │
                                                      │ produced
                                                      ▼
                                              Materialized Candidate Set
                                                      │
                                                      │ consumed_by
                                                      ▼
                                              Evaluation Input
                                                      │
                                                      │ evaluated
                                                      ▼
                                              Disposition Records (one per candidate)
                                                      │
                                                      │ ranked (only FEASIBLE)
                                                      ▼
                                              Ranked Records
                                                      │
                                                      │ selected (only first N FEASIBLE)
                                                      ▼
                                              Top-N Selection──produced──►Result Core
                                                                              │
                                                                              │ executed_by
                                                                              ▼
                                                                      OPTIMIZER node
```

### 13.4 Edge relations

| Source | Target | `relation` |
|---|---|---|
| Root | Sizing Request | `"regulates"` |
| Sizing Request | Passed Sizing Gate | `"consumed_by"` |
| Passed Sizing Gate | Materialized Candidate Set | `"produced"` |
| Materialized Candidate Set | Evaluation Input | `"consumed_by"` |
| Evaluation Input | each Disposition Record | `"evaluated"` |
| each Disposition Record | corresponding Ranked Record (if FEASIBLE) | `"ranked"` |
| each Ranked Record (only selected ones) | Top-N Selection | `"selected"` |
| Top-N Selection | Result Core | `"produced"` |
| Result Core | OPTIMIZER node | `"executed_by"` |

Not all ranked records connect to Top-N — only the selected N FEASIBLE candidates.

### 13.5 Canonical node/edge ordering

Use `ProvenanceGraph._canonical_node_key` and `_canonical_edge_key` for deterministic sorting.

### 13.6 Graph hash

Use `ProvenanceGraph.compute_hash()` directly. This ensures the graph's hash includes all node payloads, edges, and structure in a deterministic manner.

### 13.7 Root rule

- If `design_case_revision_id is not None`: root is `CASE_REVISION` with `node_id = uuid5(NS, "CASE_REVISION:" + str(design_case_revision_id))`
- If `design_case_revision_id is None`: root is `EXTERNAL` with `node_id = uuid5(NS, "EXTERNAL:" + sizing_request_identity_digest)`

---

## 14. Error model (P0-9)

### 14.1 Choice: Option A — extend existing ErrorCode

Phase 3 extends the existing `ErrorCode` enum in `src/hexagent/domain/messages.py` with Phase 3-specific error codes. This ensures full compatibility with existing `EngineeringMessage` and `RunFailure` models.

Implementation boundary is updated to allow adding codes to `messages.py`.

```python
# Added to ErrorCode:
PHASE3_INPUT_VERIFICATION_FAILED = "phase3_input_verification_failed"
PHASE3_NON_FINITE_NUMERIC = "phase3_non_finite_numeric"
PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
PHASE3_RANKING_RUNTIME_FAILURE = "phase3_ranking_runtime_failure"
PHASE3_RESULT_CONSTRUCTION_FAILED = "phase3_result_construction_failed"
PHASE3_HASH_VERIFICATION_FAILED = "phase3_hash_verification_failed"
PHASE3_PROVENANCE_VERIFICATION_FAILED = "phase3_provenance_verification_failed"
```

### 14.2 Fixed error messages

| ErrorCode | Fixed message |
|---|---|
| `PHASE3_INPUT_VERIFICATION_FAILED` | "Phase 3 input artifact verification failed." |
| `PHASE3_NON_FINITE_NUMERIC` | "Non-finite numeric value detected in Phase 3 input." |
| `PHASE3_FEASIBILITY_RUNTIME_FAILURE` | "Runtime failure during feasibility classification." |
| `PHASE3_RANKING_RUNTIME_FAILURE` | "Runtime failure during ranking." |
| `PHASE3_RESULT_CONSTRUCTION_FAILED` | "Runtime failure during result construction." |
| `PHASE3_HASH_VERIFICATION_FAILED` | "Result hash verification failed." |
| `PHASE3_PROVENANCE_VERIFICATION_FAILED` | "Result provenance verification failed." |

### 14.3 Prohibited in hash/provenance/artifact

- `str(exc)`
- `repr(exc)`
- `traceback.format_exc()`
- Memory addresses
- Runtime-specific object representations

---

## 15. Implementation boundary

### Modified existing files

| Path | Change |
|---|---|
| `src/hexagent/domain/messages.py` | Add 7 `PHASE3_*` error codes to `ErrorCode` enum |

### New files

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + `verify_or_raise()` |
| `src/hexagent/optimization/feasibility.py` | Feasibility classification + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Deterministic ranking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` construction + three-layer hash + provenance |
| `tests/unit/test_task009_phase3_*.py` | Phase 3 tests |

### Untouched files

- `src/hexagent/optimization/evaluation.py`
- `src/hexagent/optimization/identities.py`
- `src/hexagent/optimization/catalog.py`
- `src/hexagent/optimization/gate.py`
- `src/hexagent/optimization/materialization.py`
- `src/hexagent/optimization/context.py`
- `src/hexagent/optimization/models.py`
- `src/hexagent/optimization/length.py`
- `src/hexagent/optimization/_quantum.py`
- `src/hexagent/optimization/errors.py`
- Any TASK-008 modules
- Any catalog schema modules
- Phase 1 or Phase 2 tests

---

## 16. Test matrix

### 16.1 Valid constructible Phase 2 records

- [ ] Each valid record combination from §4.4 produces correct `Phase3Disposition`
- [ ] `VERIFIED + provider_matches=False` → `PROVIDER_IDENTITY_MISMATCH`
- [ ] `VERIFIED + SUCCEEDED` → FEASIBLE or INFEASIBLE (by feasibility check)
- [ ] `VERIFIED + BLOCKED` → INFEASIBLE (RATING_BLOCKED)
- [ ] `VERIFIED + FAILED` → INFEASIBLE (RATING_FAILED)
- [ ] `INTEGRITY_INVALID` → INTEGRITY_FAILED
- [ ] `RUNTIME_FAILED` → RUNTIME_FAILED
- [ ] `UNEVALUATED` → UNEVALUATED

### 16.2 Invalid cross-field combinations rejected

- [ ] VERIFIED + identity=None → input verification failure
- [ ] VERIFIED + evidence=None → input verification failure
- [ ] VERIFIED + invalid_evidence present → input verification failure
- [ ] INTEGRITY_INVALID + invalid_evidence=None → input verification failure
- [ ] INTEGRITY_INVALID + identity present → input verification failure
- [ ] RUNTIME_FAILED + evaluation_failure=None → input verification failure
- [ ] UNEVALUATED + identity present → input verification failure
- [ ] record.rating_status != evidence.rating_status.value → input verification failure

### 16.3 Strict-stop

- [ ] Strict-stop on first candidate (index 0) → PARTIAL, all later UNEVALUATED
- [ ] Strict-stop on middle candidate → earlier records VERIFIED, later UNEVALUATED
- [ ] Strict-stop on last candidate → earlier records VERIFIED, 0 UNEVALUATED after
- [ ] No strict-stop → COMPLETE
- [ ] VERIFIED record after stop index → input rejected
- [ ] Phase 3 does not call TASK-008 for any candidate
- [ ] Phase 3 does not modify any Phase 2 artifact
- [ ] Stop invariant verification rejects invalid phase-2 record ordering

### 16.4 Ranking and objectives

- [ ] `MINIMUM_OUTER_HEAT_TRANSFER_AREA` complete sort key (area → length → ID)
- [ ] `MINIMUM_EFFECTIVE_LENGTH` complete sort key (length → area → ID)
- [ ] Objective ties → resolved by secondary field
- [ ] Final ASCII candidate ID tie-break
- [ ] Non-finite numeric → `ValueError` at consumer boundary
- [ ] -0.0 normalized to 0

### 16.5 Top-N

- [ ] Zero FEASIBLE → empty Top-N
- [ ] Fewer FEASIBLE than N → all FEASIBLE returned
- [ ] Exactly N FEASIBLE → all returned
- [ ] More than N FEASIBLE → first N returned
- [ ] Top-N does not mutate candidate identity/hash/evaluation record
- [ ] Top-N order = ranking order

### 16.6 Input verification

- [ ] Record↔candidate one-to-one binding passes for valid input
- [ ] Displaced record → input verification failure
- [ ] Missing record → input verification failure
- [ ] Extra record → input verification failure
- [ ] Duplicate source_qualified_candidate_id → input verification failure
- [ ] `evaluation_order_index` mismatch → input verification failure
- [ ] Every `evaluation_record_descriptor` field mutation changes `evaluation_input_digest`
- [ ] Tampered `candidate_set_digest` → input verification failure
- [ ] Tampered `gate_digest` → input verification failure

### 16.7 Three-layer hash

- [ ] `result_core_hash` does not include `provenance_digest` or `result_hash`
- [ ] `result_hash` changes when `provenance_digest` changes
- [ ] `result_core_hash` is insensitive to `provenance_digest` changes
- [ ] `optimization_result_id` is deterministic UUID5 from `result_hash`
- [ ] Python 3.11/3.12 hash equality for all three hash layers
- [ ] `result_core_payload` mutation (any digest field) changes `result_core_hash`
- [ ] Derived/excluded fields (`optimization_result_id`, `provenance_digest`, `result_hash`) do not participate in `result_core_hash`

### 16.8 Provenance

- [ ] Each node uses correct `ProvenanceNodeType` from §13.1
- [ ] Node IDs deterministically reproducible (UUID5)
- [ ] Root: CASE_REVISION when design_case_revision_id present; EXTERNAL when absent
- [ ] CALCULATION_RUN node present
- [ ] Graph is acyclic (validates on construction)
- [ ] Only selected FEASIBLE records connect to Top-N node
- [ ] Not all ranked records connect to Top-N (when count > N)
- [ ] Tampered node payload_hash → root digest mismatch
- [ ] Tampered edge → root digest mismatch
- [ ] Provenance verification: fail closed

### 16.9 Termination invariants

- [ ] COMPLETE: counts sum correctly, ranked/Top-N present
- [ ] PARTIAL: strict-stop warning, Top-N from indices < stop_index only
- [ ] FAILED: input verification failure → no OptimizationResult
- [ ] Count equation invariants (§11.4) hold for all scenarios

### 16.10 Error model

- [ ] Feasibility exception → RUNTIME_FAILED per candidate, batch continues
- [ ] Global exception → FAILED termination
- [ ] All error messages in hash/provenance/artifact are fixed deterministic strings
- [ ] Phase 3 ErrorCode values are valid members of `ErrorCode`
- [ ] EngineeringMessage/RunFailure accept Phase 3 error codes
- [ ] No `str(exc)`, `repr(exc)`, traceback, or memory address in any output

### 16.11 Warning/blocker permutation

- [ ] Warnings/blockers are canonicalized (sorted by stable key) before digesting
- [ ] Sort key: `(severity.value, code.value, message)` — deterministic
- [ ] Duplicate identical warnings: deduplicated or preserved — exact rule frozen at implementation
- [ ] Digests change only when canonicalized warning/blocker content changes

---

## 17. Acceptance criteria

1. All tests pass on Python 3.11 and 3.12
2. `result_hash` is deterministic and reproducible from identical Phase 2 inputs
3. Provenance DAG verification detects tampered nodes or edges
4. Input verification fails closed for all 11 steps
5. Top-N selection never exceeds feasible candidate count
6. No Phase 2 artifact is mutated
7. `PROVIDER_IDENTITY_MISMATCH` candidates never enter ranking or Top-N
8. `UNEVALUATED` candidates never enter feasibility analysis
9. Ruff check, format check, mypy strict, coverage pass
10. `pip-audit` passes
11. Design review passes before implementation is authorized

---

## 18. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED

Implementation must not begin until a separate engineering design review passes and a frozen contract commit SHA is established.
