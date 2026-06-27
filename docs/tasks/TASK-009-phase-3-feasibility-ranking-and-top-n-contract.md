# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> ⚠️ This document is a **design contract** for review only. No implementation is authorized until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope

Phase 3 completes the candidate optimization pipeline by consuming Phase 2 validated `CandidateEvaluationRecord` artifacts (`tuple[CandidateEvaluationRecord, ...]`) and producing a deterministic, provenance-tracked `OptimizationResult`.

Phase 3 is responsible for:

- Typed immutable input artifact construction and verification (`Phase3EvaluationInput`)
- Deterministic feasibility classification per the exact Phase 2 state matrix
- Deterministic ranking with explicit per-objective tie-breaking
- Deterministic Top-N result construction (feasible-only)
- Result-level integrity hash and provenance DAG
- Fail-closed semantics for all verification failures

Phase 3 does **not** re-execute candidate generation, materialization, or TASK-008 thermal rating.

---

## 2. Non-goals

The following are explicitly **out of scope** for Phase 3:

- ❌ TASK-010 (versioned API and traceable report)
- ❌ C4 (cost constraint)
- ❌ Pressure-drop calculation
- ❌ Pressure-drop constraint
- ❌ Velocity constraint
- ❌ Pump power estimation
- ❌ Economic / life-cycle / multi-objective Pareto optimization
- ❌ Stochastic or heuristic optimization (genetic algorithms, simulated annealing, random search)
- ❌ Machine-learning ranking or scoring
- ❌ New heat-transfer correlations
- ❌ New rating-solver logic
- ❌ Candidate-generation changes
- ❌ Catalog-schema changes
- ❌ Phase 2 artifact mutation
- ❌ Re-running TASK-008 `rate_double_pipe()` for any candidate
- ❌ Recovering, re-running, or reinterpreting Phase 2 strict-stop failures

---

## 3. Upstream frozen dependencies (P0-1: Phase 3 input artifact)

Phase 2 returns `tuple[CandidateEvaluationRecord, ...]` (not an `EvaluationBatch`). Phase 3 defines a single typed immutable artifact that bundles the real Phase 2 outputs:

```python
class Phase3EvaluationInput(BaseModel):
    """Complete typed input for Phase 3, constructed from real Phase 2 outputs.

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    schema_version: int  # 1

    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str

    materialization_result: MaterializationResult
    materialization_result_digest: str
    passed_gate_digest: str

    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int  # == len(evaluation_records)

    evaluation_input_digest: str  # SHA-256 of canonical payload (below)
```

### 3.1 Canonical payload for digest

The `evaluation_input_digest` is computed over the following deterministic payload:

| Field | Canonical form |
|---|---|
| `schema_version` | integer |
| `sizing_request_identity_digest` | string |
| `materialization_result_digest` | string |
| `passed_gate_digest` | string |
| `evaluation_record_count` | integer |
| `ordered_candidate_ids` | ordered string list (from materialization result) |
| `ordered_evaluation_identity_digests` | ordered string list (None → "null") |
| `ordered_evidence_digests` | ordered string list (None → "null") |

Serialise via `canonical_json` and compute `sha256(...).hexdigest()`.

### 3.2 Consumer-boundary verification

`Phase3EvaluationInput.verify_or_raise()` must verify at minimum:

1. `sizing_request_identity_digest == sha256(sizing_request_identity)`
2. `materialization_result_digest == sha256(materialization_result)` (using canonical serialisation)
3. `passed_gate_digest == sha256(materialization_result.sizing_gate)` (using canonical serialisation)
4. `evaluation_record_count == len(evaluation_records)`
5. Each `CandidateEvaluationRecord` identity: if present, `sha256(record) == record.candidate_evaluation_identity` (when non-None)
6. Each `VerifiedRatingEvidenceSnapshot` identity: if present, `sha256(snapshot) == snapshot.rating_result_hash`
7. No duplicate `source_qualified_candidate_id`
8. `evaluation_input_digest == recomputed digest`

Any failure raises with fixed deterministic error message (no `str(exc)`).

---

## 4. Phase 2 state alignment (P0-2, P0-4)

### 4.1 Real Phase 2 state enum

```python
class CandidateEvaluationState(StrEnum):
    UNEVALUATED = "unevaluated"
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"
```

### 4.2 Real Phase 2 verification outcome enum

```python
class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
```

### 4.3 Real Phase 2 feasibility_status enum

```python
class FeasibilityStatus(StrEnum):
    NOT_EVALUATED = "not_evaluated"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
```

### 4.4 Phase 2 → Phase 3 disposition mapping matrix

The complete mapping covers all observable `CandidateEvaluationRecord` state combinations:

| State | hash outcome | provenance outcome | provider matches | Phase 2 feasibility | rating_status | identity present | evidence present | Phase 3 Disposition |
|---|---|---|---|---|---|---|---|---|
| UNEVALUATED | NOT_RUN | NOT_RUN | true/false | NOT_EVALUATED | None | None | None | **UNEVALUATED** |
| VERIFIED | PASSED | PASSED | true | NOT_EVALUATED | SUCCEEDED | present | present | **FEASIBLE or INFEASIBLE** (by duty/constraint check) |
| VERIFIED | PASSED | PASSED | false | PROVIDER_IDENTITY_MISMATCH | SUCCEEDED/BLOCKED/FAILED | present | present | **PROVIDER_IDENTITY_MISMATCH** |
| VERIFIED | PASSED | FAILED | *any* | NOT_EVALUATED | any | present | present | **PROVENANCE_FAILED** |
| VERIFIED | PASSED | ERROR | *any* | NOT_EVALUATED | any | present | present | **PROVENANCE_FAILED** |
| VERIFIED | FAILED | NOT_RUN | *any* | NOT_EVALUATED | any | present | present | **INTEGRITY_FAILED** |
| VERIFIED | FAILED | FAILED | *any* | NOT_EVALUATED | any | present | present | **INTEGRITY_FAILED** |
| VERIFIED | ERROR | NOT_RUN | *any* | NOT_EVALUATED | any | present | present | **INTEGRITY_FAILED** |
| INTEGRITY_INVALID | FAILED | NOT_RUN | *any* | NOT_EVALUATED | None | None | present (invalid) | **INTEGRITY_FAILED** |
| RUNTIME_FAILED | NOT_RUN | NOT_RUN | *any* | NOT_EVALUATED | None/FAILED | None | None | **RUNTIME_FAILED** |

### 4.5 Phase 3 disposition enum (P0-4)

```python
class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"                      # Engineering-rank-eligible
    INFEASIBLE = "infeasible"                  # Trusted evidence, but engineering criteria not met
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"  # Not rank-eligible
    UNEVALUATED = "unevaluated"                # Strict-stop: never reached
    INTEGRITY_FAILED = "integrity_failed"      # Hash verification failed
    PROVENANCE_FAILED = "provenance_failed"    # Provenance verification failed
    RUNTIME_FAILED = "runtime_failed"          # TASK-008 runtime failure
```

### 4.6 Engineering-rank-eligibility invariant

A candidate is **engineering-rank-eligible** (may receive a numerical rank and enter Top-N) **only** when:

1. `disposition == FEASIBLE`

The following dispositions must **never** be engineering-rank-eligible or enter Top-N:

- `INFEASIBLE` — trusted evidence shows engineering constraints not met
- `PROVIDER_IDENTITY_MISMATCH` — mismatched provider, regardless of evidence quality
- `UNEVALUATED` — no TASK-008 call was attempted
- `INTEGRITY_FAILED` — evidence was tampered or hash verification failed
- `PROVENANCE_FAILED` — evidence provenance is untrusted
- `RUNTIME_FAILED` — TASK-008 raised or returned evaluation failure

---

## 5. Strict-stop semantics (P0-3)

Phase 3 must honour Phase 2 strict-stop behaviour exactly:

1. Phase 2 `UNEVALUATED` is the **final** evaluation state for all candidates after the first failure. Phase 3 must not re-order, re-run, or skip these records.
2. Candidates following a hash/provenance failure in Phase 2 are recorded as `UNEVALUATED` with `VerificationOutcome.NOT_RUN` — they are **not** eligible for any Phase 3 feasibility or ranking processing.
3. Phase 3 must not call TASK-008 `rate_double_pipe()` for any candidate, regardless of state.
4. A software exception (unexpected `Exception`) encountered during Phase 3 feasibility classification must be elevated to a structured runtime failure, **not** demoted to `INFEASIBLE`. If such an exception occurs at the per-candidate level, that specific candidate receives `RUNTIME_FAILED` disposition; if the exception prevents the entire Phase 3 pipeline from continuing, a global `FAILED` termination status applies.

---

## 6. Numeric type contract (P0-5)

### 6.1 Input boundary

Phase 2 verified evidence (`VerifiedRatingEvidenceSnapshot`) stores engineering metrics as **validated finite `float`** values:

| Field | Phase 2 type | Phase 3 consumption |
|---|---|---|
| `required_duty_w` | `float` (finite) | Consumed as `float` |
| `duty_absolute_tolerance_w` | `float` (finite) | Consumed as `float` |
| `duty_relative_tolerance` | `float` (finite) | Consumed as `float` |
| `minimum_terminal_delta_t` | `float` (finite) | Consumed as `float` |
| `heat_duty_w` | `float` (finite) | Consumed as `float` |
| `area_outer_m2` | `float` (finite) | Consumed as `float` |
| `energy_residual_w` | `float` (finite or None) | Consumed as `float` |
| `ua_lmtd_residual_w` | `float` (finite or None) | Consumed as `float` |

All `float` inputs entering Phase 3 have already been validated as finite by the Phase 2 model validators. NaN, Inf, and -0.0 are rejected at the Phase 2 boundary.

### 6.2 Optional Decimal conversion adapter

Phase 3 may optionally convert these `float` values to `Decimal` for ranking comparison. If such a conversion is implemented, it must follow exactly:

1. **Conversion:** `Decimal(str(finite_float))` — round-trip exact via string representation
2. **Quantization:** Normalised to remove trailing zeros using `Decimal.normalize()`
3. **NaN/Inf rejection:** Already guaranteed by Phase 2; any unexpected NaN/Inf raises before ranking
4. **-0.0 handling:** Phase 2 model validators reject `-0.0`; no special handling needed
5. **Hash consistency:** If conversion is used, the `canonical_json` representation must use `Decimal(str(f))` with normalized form, **not** the raw float — ensuring Python 3.11/3.12 consistency
6. All comparisons use `Decimal` comparison operators, not `float` comparison (avoids precision surprises)
7. If no conversion is implemented, ranking uses float comparison with the understanding that Phase 2 metrics are deterministic finite floats produced by the same TASK-008 solver — determinism is guaranteed

---

## 7. Optimization objective registry (P0-6)

### 7.1 Typed enum

```python
class OptimizationObjective(StrEnum):
    MINIMUM_OUTER_HEAT_TRANSFER_AREA = "minimum_outer_heat_transfer_area"
    MINIMUM_EFFECTIVE_LENGTH = "minimum_effective_length"
```

These match the frozen Phase 2 `OptimizationObjective` in `context.py`.

### 7.2 Per-objective ranking registry

#### MINIMUM_OUTER_HEAT_TRANSFER_AREA

| Level | Field | Source | Unit | Direction | None handling |
|---|---|---|---|---|---|
| 1 | `area_outer_m2` | `VerifiedRatingEvidenceSnapshot.area_outer_m2` | m² | **Ascending** | None → last |
| 2 | `effective_length_m` | (derived from `MaterializationResult` candidate geometry) | m | **Ascending** | None → last |
| 3 | `source_qualified_candidate_id` | `CandidateEvaluationRecord.source_qualified_candidate_id` | ASCII | **Ascending** | Not nullable |

#### MINIMUM_EFFECTIVE_LENGTH

| Level | Field | Source | Unit | Direction | None handling |
|---|---|---|---|---|---|
| 1 | `effective_length_m` | (derived from `MaterializationResult` candidate geometry) | m | **Ascending** | None → last |
| 2 | `area_outer_m2` | `VerifiedRatingEvidenceSnapshot.area_outer_m2` | m² | **Ascending** | None → last |
| 3 | `source_qualified_candidate_id` | `CandidateEvaluationRecord.source_qualified_candidate_id` | ASCII | **Ascending** | Not nullable |

### 7.3 None handling details

- `None` values sort **after** all finite values of the same type
- This ensures candidates with missing engineering metrics are ranked below those with valid values, without silently discarding invalid data
- If `area_outer_m2` is `None` (should not happen for a `VERIFIED` record with `RatingStatus.SUCCEEDED`), such candidates cannot participate in ranking — they receive `INFEASIBLE` disposition

### 7.4 Non-finite value handling

- Already rejected at Phase 2 input boundary
- If a non-finite value (NaN, Inf) is detected during Phase 3 consumption, ranking raises `ValueError` with a fixed deterministic message

### 7.5 Final tie-break

The final tie-break (`source_qualified_candidate_id` ASCII ascending) guarantees deterministic ordering for every pair of candidates that have identical objective and tie-break values. This is the **only** tie-break that is independent of the optimization objective.

---

## 8. Top-N contract (P0-7)

### 8.1 Source field

`requested_top_n` is bound directly to `SizingRequestIdentity.top_n`.

```python
requested_top_n == sizing_request_identity.top_n
```

### 8.2 Validation

- `SizingRequestIdentity.top_n` is validated as `strict int >= 1` at the Phase 2 boundary
- If `requested_top_n < 1` is somehow received in Phase 3, `Phase3EvaluationInput.verify_or_raise()` must reject it — no branch returning an empty successful result

### 8.3 Selection rules

- Top-N candidates are selected **only** from candidates with `Phase3Disposition.FEASIBLE`
- Selection occurs **after** full deterministic sort — all FEASIBLE candidates are sorted, then the first `N` are taken
- If feasible count < `N`: all feasible candidates are returned (no padding with inferior candidates)
- If feasible count == 0: empty `ordered_top_n_record_digests`, `feasible_candidate_count == 0`
- Top-N selection does **not** alter candidate identity, hash, evaluation record, or disposition
- Full ranked ordered list is preserved in `ordered_ranked_record_digests`; Top-N is a strict subset
- Top-N selection itself is recorded as a provenance node

---

## 9. Executable feasibility formulas (P0-8)

### 9.1 RatingStatus mapping

`VerifiedRatingEvidenceSnapshot.rating_status` maps to Phase 3 disposition as:

| Phase 2 `rating_status` | Phase 3 outcome |
|---|---|
| `RatingStatus.SUCCEEDED` | Continues to feasibility checks |
| `RatingStatus.BLOCKED` | **INFEASIBLE** — diagnostic: `RATING_BLOCKED` |
| `RatingStatus.FAILED` | **INFEASIBLE** — diagnostic: `RATING_FAILED` |
| `None` (UNEVALUATED/RUNTIME_FAILED/INTEGRITY_INVALID) | Per state mapping in §4.4 |

### 9.2 Duty satisfaction

```
duty_tolerance_w = max(
    duty_absolute_tolerance_w,
    duty_relative_tolerance * abs(required_duty_w),
)

duty_error_w = abs(verified_heat_duty_w - required_duty_w)

duty_satisfied = duty_error_w <= duty_tolerance_w
```

Where:
- `verified_heat_duty_w` = `VerifiedRatingEvidenceSnapshot.heat_duty_w` (finite float, verified Phase 2)
- `required_duty_w` = `SizingRequestIdentity.required_duty_w`
- `duty_absolute_tolerance_w` = `SizingRequestIdentity.duty_absolute_tolerance_w`
- `duty_relative_tolerance` = `SizingRequestIdentity.duty_relative_tolerance`

**Heat duty sign convention:** TASK-008 returns `heat_duty_w` as positive for cooling duty (consistent with `required_duty_w`). The absolute value comparison ensures the magnitude check is sign-independent.

### 9.3 Terminal delta-T

Define two flow arrangement formulas:

**Co-current:**
```
delta_t_1 = hot_inlet_temperature_k - cold_inlet_temperature_k
delta_t_2 = hot_outlet_temperature_k - cold_outlet_temperature_k
```

**Counter-current:**
```
delta_t_1 = hot_inlet_temperature_k - cold_outlet_temperature_k
delta_t_2 = hot_outlet_temperature_k - cold_inlet_temperature_k
```

Then:
```
minimum_actual_terminal_delta_t = min(delta_t_1, delta_t_2)
terminal_delta_t_satisfied = minimum_actual_terminal_delta_t >= minimum_terminal_delta_t
```

Where:
- `hot_inlet_temperature_k` = `SizingRequestIdentity.hot_inlet_temperature_k`
- `hot_outlet_temperature_k` = `VerifiedRatingEvidenceSnapshot.hot_outlet_temperature_k`
- `cold_inlet_temperature_k` = `SizingRequestIdentity.cold_inlet_temperature_k`
- `cold_outlet_temperature_k` = `VerifiedRatingEvidenceSnapshot.cold_outlet_temperature_k`
- `minimum_terminal_delta_t` = `SizingRequestIdentity.minimum_terminal_delta_t`

If outlet temperatures are `None` (rating_status != SUCCEEDED), the terminal delta-T check is skipped (feasibility dictated by rating status alone).

### 9.4 Energy closure

**Option A (preferred): Trust Phase 2 verdict**

`VerifiedRatingEvidenceSnapshot` is only constructed after Phase 2 hash + provenance verification passed. The energy balance was already accepted by TASK-008's internal convergence criteria when `RatingStatus.SUCCEEDED` was set. Phase 3 trusts this verdict and does **not** re-check energy closure for SUCCEEDED ratings.

This avoids re-implementing an energy-balance criterion that TASK-008 already enforced.

### 9.5 UA-LMTD closure

**Option A (preferred): Trust Phase 2 verdict**

Same reasoning as energy closure: TASK-008's successful convergence implies `UA` × `LMTD` ≈ `Q`. Phase 3 trusts this for `RatingStatus.SUCCEEDED`.

### 9.6 Diagnostic precedence

When multiple feasibility conditions fail simultaneously, the deterministic precedence is:

| Priority | Diagnostic key | Condition |
|---|---|---|
| 1 | `PROVIDER_IDENTITY_MISMATCH` | `provider_identity_matches == False` |
| 2 | `RATING_BLOCKED` | `rating_status == BLOCKED` |
| 3 | `RATING_FAILED` | `rating_status == FAILED` |
| 4 | `MISSING_TRUSTED_METRIC` | `area_outer_m2 is None` or `heat_duty_w is None` (despite VERIFIED + SUCCEEDED — invariant violation) |
| 5 | `DUTY_SHORTFALL` | `duty_satisfied == False` |
| 6 | `TERMINAL_DELTA_T_INADEQUATE` | `terminal_delta_t_satisfied == False` |

Only the highest-priority failing diagnostic is recorded as the `infeasibility_diagnostic` for that candidate.

### 9.7 Feasibility diagnostic key enum

```python
class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"                              # FEASIBLE — no infeasibility reason
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"
    RATING_FAILED = "rating_failed"
    MISSING_TRUSTED_METRIC = "missing_trusted_metric"
    DUTY_SHORTFALL = "duty_shortfall"
    TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
```

---

## 10. Data model (P0-9, P0-10)

### 10.1 `CandidateDispositionRecord` (complete audit)

```python
class CandidateDispositionRecord(BaseModel):
    """Complete audit/disposition for every Phase 2 record — one per candidate.

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    source_qualified_candidate_id: str
    evaluation_order_index: int

    candidate_evaluation_state: CandidateEvaluationState
    disposition: Phase3Disposition
    infeasibility_diagnostic: FeasibilityDiagnosticKey  # NONE if FEASIBLE or non-engineering

    candidate_evaluation_identity_digest: str | None     # None for non-VERIFIED
    verified_rating_evidence_digest: str | None           # None for non-VERIFIED

    engineering_objective_value: float | None             # area_outer_m2 or effective_length; None if non-rank-eligible
    objective_tie_break_value: float | None               # secondary field; None if non-rank-eligible

    feasibility_digest: str                               # SHA-256 of canonical disposition payload

    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None
```

### 10.2 `RankedCandidateRecord` (engineering-rank-eligible only)

```python
class RankedCandidateRecord(BaseModel):
    """Only created for engineering-rank-eligible candidates (FEASIBLE disposition).

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    rank: int                                               # 1-based, assigned after full sort
    source_qualified_candidate_id: str
    candidate_evaluation_identity_digest: str
    verified_rating_evidence_digest: str
    disposition: Phase3Disposition                          # Always FEASIBLE
    feasibility_digest: str                                 # Link to CandidateDispositionRecord
    engineering_objective_value: float | None               # Primary objective
    ranked_record_digest: str                               # SHA-256 of canonical payload
```

### 10.3 `TerminationStatus` (P0-13)

```python
class TerminationStatus(StrEnum):
    COMPLETE = "complete"       # All processing finished without unrecoverable error
    PARTIAL = "partial"         # Phase 2 strict-stop occurred; earlier results still valid
    FAILED = "failed"           # Unrecoverable error: artifact verification failed or Phase 3 exception
```

### 10.4 `OptimizationResult` (P0-10)

```python
class OptimizationResult(BaseModel):
    """Complete typed result of Phase 3 optimization.

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    schema_version: int

    # Upstream bindings
    sizing_request_identity_digest: str
    passed_gate_digest: str
    materialized_candidate_set_digest: str
    evaluation_input_digest: str

    # Objective
    optimization_objective: OptimizationObjective
    requested_top_n: int

    # Counts (non-overlapping, sum-invariant)
    total_candidate_count: int
    verified_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int
    provenance_failed_count: int

    # Record digests (ordered)
    ordered_disposition_record_digests: tuple[str, ...]        # All candidates, Phase 2 order
    ordered_ranked_record_digests: tuple[str, ...]             # FEASIBLE only, ranking order
    ordered_top_n_record_digests: tuple[str, ...]              # Top-N subset of ranked

    # Termination
    termination_status: TerminationStatus

    # Messages (typed, not free-form)
    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None

    # Integrity
    result_hash: str                                           # SHA-256 of canonical payload (excludes derived fields)
    provenance_digest: str                                     # Root digest of provenance DAG
```

### 10.5 Count equations (P0-10)

```
total_candidate_count == evaluation_record_count
                         == len(ordered_disposition_record_digests)

verified_candidate_count == feasible_candidate_count
                           + infeasible_candidate_count
                           + provider_mismatch_count
                           + provenance_failed_count

total_candidate_count == verified_candidate_count
                        + integrity_failed_count
                        + runtime_failed_count
                        + unevaluated_count
```

Each quadrant:
- `verified_candidate_count` = candidates with `CandidateEvaluationState.VERIFIED`
- `integrity_failed_count` = candidates with `CandidateEvaluationState.INTEGRITY_INVALID`
- `runtime_failed_count` = candidates with `CandidateEvaluationState.RUNTIME_FAILED`
- `unevaluated_count` = candidates with `CandidateEvaluationState.UNEVALUATED`

The verified sub-counts:
- `feasible_candidate_count` = FEASIBLE disposition
- `infeasible_candidate_count` = INFEASIBLE disposition
- `provider_mismatch_count` = PROVIDER_IDENTITY_MISMATCH disposition
- `provenance_failed_count` = PROVENANCE_FAILED disposition

These sets are disjoint and their sum equals `verified_candidate_count`.

### 10.6 Termination status invariants (P0-13)

| Status | Condition | Has ranked records? | Has Top-N? | Has result_hash? | Has provenance? | blockers/failure? |
|---|---|---|---|---|---|---|
| **COMPLETE** | No Phase 2 strict-stop; no Phase 3 unrecoverable error | Yes (may be empty if 0 FEASIBLE) | Yes (may be empty) | Yes | Yes | May be present (individual disposition warnings/blockers) |
| **PARTIAL** | Phase 2 strict-stop occurred (some UNEVALUATED); earlier VERIFIED records processed normally | Yes (from earlier candidates only) | Yes (from earlier FEASIBLE candidates only) | Yes | Yes | Must include strict-stop warning |
| **FAILED** | Input artifact verification failed before feasibility; or global Phase 3 exception | No | No | Yes (if artifact verification succeeded but later fail) | Yes (partial if possible) | Must include a failure |

**PARTIAL + Top-N:** For a Phase 2 strict-stop batch where one or more earlier candidates are VERIFIED and FEASIBLE, Top-N may be selected from those FEASIBLE candidates. The `PARTIAL` termination status indicates that not all candidates were evaluated, but the available FEASIBLE results are valid.

**FAILED + no hash:** If `Phase3EvaluationInput.verify_or_raise()` fails, no `OptimizationResult` is produced — the exception propagates upward.

---

## 11. Hash contract (P0-11)

### 11.1 Non-circular canonical payload

The `optimization_result_id` and `result_hash` are **excluded** from the canonical payload used for hash computation:

```
CanonicalPayload:
  schema_version
  sizing_request_identity_digest
  passed_gate_digest
  materialized_candidate_set_digest
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
  ordered_disposition_record_digests (ordered string list)
  ordered_ranked_record_digests (ordered string list)
  ordered_top_n_record_digests (ordered string list)
  termination_status.value
  warnings (ordered list of canonical warning digests)
  blockers (ordered list of canonical blocker digests)
  failure (canonical failure digest, or "null")
  provenance_digest
```

### 11.2 Derived fields

```
result_hash = sha256(canonical_payload_json).hexdigest()
optimization_result_id = result_hash  # or deterministic UUID5 from result_hash
provenance_digest = <root digest of provenance DAG>
```

### 11.3 Digest binding

The `result_hash` binds:

| Digest | Source |
|---|---|
| Each `CandidateDispositionRecord` | `feasibility_digest` |
| Each `RankedCandidateRecord` | `ranked_record_digest` |
| Top-N membership | Through `ordered_top_n_record_digests` |
| Feasibility/disposition | Through disposition record digests |
| Objective/tie-break values | Through ranked record digests |
| Rank | Through ranked record digests |
| Warnings/blockers/failure | Through canonical message digests |
| All counts | Direct integer fields |
| Termination status | Direct string field |
| Upstream artifact digests | `sizing_request_identity_digest`, `passed_gate_digest`, `materialized_candidate_set_digest`, `evaluation_input_digest` |

### 11.4 Digest distinction

| Concept | Identifier |
|---|---|
| Source-qualified candidate ID | `CandidateEvaluationRecord.source_qualified_candidate_id` → `str` |
| Candidate evaluation identity | `CandidateEvaluationRecord.candidate_evaluation_identity` → `str \| None` |
| Candidate disposition digest | `CandidateDispositionRecord.feasibility_digest` → `str` |
| Ranked record digest | `RankedCandidateRecord.ranked_record_digest` → `str` |

---

## 12. Provenance contract (P0-12)

Phase 3 reuses the repository's existing `ProvenanceGraph`, `ProvenanceNode`, and `ProvenanceEdge` from `hexagent.domain.provenance`.

### 12.1 Node types

| Node type | `ProvenanceNodeType` | Payload |
|---|---|---|
| Sizing request | `PROVENANCE_NODE_TYPE` (e.g. `INPUT_FILE` or `RESULT`) | `sizing_request_identity_digest` |
| Passed sizing gate | `PROVENANCE_NODE_TYPE` (e.g. `CALCULATION_RUN`) | `passed_gate_digest` |
| Materialization result | `PROVENANCE_NODE_TYPE` (e.g. `CALCULATION_RUN`) | `materialized_candidate_set_digest` |
| Evaluation input | `INTERMEDIATE` | `evaluation_input_digest` |
| Each disposition record | `INTERMEDIATE` | `feasibility_digest` |
| Each ranked record | `INTERMEDIATE` | `ranked_record_digest` |
| Top-N selection | `INTERMEDIATE` | Ordered Top-N ID list digest |
| Result payload | `RESULT` | `result_hash` |
| Result context | `OPTIMIZER` | Full `OptimizationResult` metadata |

### 12.2 Node payload rules

- Each `ProvenanceNode.node_id` is a deterministic `UUID5` derived from the content digest
- Each `ProvenanceNode.payload_hash` is `"sha256:" + content_digest`
- `label` = node type description (e.g. `"Phase 3 evaluation input"`, `"Disposition record for {candidate_id}"`)

### 12.3 Edge structure

| Edge | From | To | Relation |
|---|---|---|---|
| Sizing request → Gate | sizing request node | gate node | `"validated_by"` |
| Gate → Materialization | gate node | materialization node | `"produced"` |
| Materialization → Eval input | materialization node | evaluation input node | `"consumed_by"` |
| Eval input → Disposition records | evaluation input node | each disposition node | `"evaluated"` |
| Disposition → Ranked records | each disposition node | its ranked record (if any) | `"ranked"` |
| Ranked records → Top-N | each ranked record node | Top-N selection node | `"selected"` |
| Top-N → Result | Top-N selection node | result payload node | `"produced"` |
| Result → Provenance root | result payload node | provenance root (aggregate) | `"provenance_of"` |

### 12.4 Verification algorithm

1. Recompute each node's `payload_hash` from its content
2. Recompute each edge's endpoint node IDs
3. Build a `ProvenanceGraph` from nodes + edges
4. Validate DAG (acyclic, unique node IDs, all edges reference existing nodes)
5. Compute `root_digest` as `sha256(canonical(nodes) + canonical(edges))`
6. Compare `root_digest` against `OptimizationResult.provenance_digest`
7. Any mismatch → fail closed

---

## 13. Error model (P0-14)

### 13.1 Typed diagnostics

All feasibility diagnostics use `FeasibilityDiagnosticKey` enum (§9.7).

All errors use existing `ErrorCode` from `hexagent.domain.messages`, or Phase 3-specific additions:

```python
class Phase3ErrorCode(StrEnum):
    INPUT_VERIFICATION_FAILED = "phase3_input_verification_failed"
    NON_FINITE_NUMERIC_DETECTED = "phase3_non_finite_numeric_detected"
    FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
    RANKING_RUNTIME_FAILURE = "phase3_ranking_runtime_failure"
    RESULT_CONSTRUCTION_FAILED = "phase3_result_construction_failed"
    HASH_VERIFICATION_FAILED = "phase3_hash_verification_failed"
    PROVENANCE_VERIFICATION_FAILED = "phase3_provenance_verification_failed"
```

### 13.2 Fixed error messages

All messages entering hash, provenance, or user-visible artifact must be deterministic fixed strings:

| ErrorCode | Fixed message |
|---|---|
| `INPUT_VERIFICATION_FAILED` | "Phase 3 input artifact verification failed." |
| `NON_FINITE_NUMERIC_DETECTED` | "Non-finite numeric value detected in ranking." |
| `FEASIBILITY_RUNTIME_FAILURE` | "Runtime failure during feasibility classification." |
| `RANKING_RUNTIME_FAILURE` | "Runtime failure during ranking." |
| `RESULT_CONSTRUCTION_FAILED` | "Runtime failure during result construction." |
| `HASH_VERIFICATION_FAILED` | "Result hash verification failed." |
| `PROVENANCE_VERIFICATION_FAILED` | "Result provenance verification failed." |

Prohibited in any hash/provenance/artifact field:
- `str(exc)`
- `repr(exc)`
- `traceback.format_exc()`
- Memory addresses
- Runtime-specific object representations

---

## 14. Implementation boundary

Phase 3 implementation (when authorized) is limited to:

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + `verify_or_raise()` |
| `src/hexagent/optimization/feasibility.py` | Feasibility classification + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Deterministic ranking + tie-breaking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` construction + hash + provenance |
| `tests/unit/test_task009_phase3_*.py` | Phase 3 tests |

Phase 3 implementation does **not** modify:

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
- Any catalog-schema modules
- Phase 1 or Phase 2 tests

---

## 15. Test matrix

The following test scenarios must be covered when implementation is authorized:

### 15.1 State/outcome combinations

- [ ] Every `CandidateEvaluationState` × `VerificationOutcome` × provider match combination in §4.4
- [ ] `VerificationOutcome.ERROR` for both hash and provenance
- [ ] Each of the 7 `Phase3Disposition` values produced correctly
- [ ] `PROVIDER_IDENTITY_MISMATCH` never receives engineering rank
- [ ] `PROVIDER_IDENTITY_MISMATCH` never enters Top-N

### 15.2 Strict-stop

- [ ] `UNEVALUATED` disposition for candidates after strict-stop
- [ ] Phase 3 does not call TASK-008 for any candidate
- [ ] Phase 3 does not modify any Phase 2 artifact
- [ ] Subsequent records after strict-stop remain `UNEVALUATED` in disposition

### 15.3 Optimization objective ranking

- [ ] `MINIMUM_OUTER_HEAT_TRANSFER_AREA` — primary field `area_outer_m2` ascending
- [ ] `MINIMUM_EFFECTIVE_LENGTH` — primary field `effective_length_m` ascending
- [ ] Objective ties resolved by secondary field
- [ ] Final ASCII `source_qualified_candidate_id` tie-break
- [ ] Non-finite numeric value → `ValueError`

### 15.4 Top-N

- [ ] Zero feasible → empty Top-N
- [ ] Fewer feasible than N → all feasible returned
- [ ] Exactly N feasible → all returned
- [ ] More than N feasible → only first N returned
- [ ] Top-N does not mutate candidate identity/hash/evaluation record
- [ ] Top-N order = ranking order (strict subset)

### 15.5 Input permutations

- [ ] Input artifact with different `CandidateEvaluationRecord` orders (Phase 2 order preserved)
- [ ] Warning/blocker permutations produce identical result hash
- [ ] Duplicate `source_qualified_candidate_id` → input verification failure
- [ ] Missing record count mismatch → input verification failure

### 15.6 Tampering

- [ ] Tampered `sizing_request_identity_digest` → fail closed
- [ ] Tampered `passed_gate_digest` → fail closed
- [ ] Tampered `materialized_result_digest` → fail closed
- [ ] Tampered `evaluation_input_digest` → fail closed
- [ ] Tampered `CandidateEvaluationRecord` identity → fail closed
- [ ] Tampered `VerifiedRatingEvidenceSnapshot` hash → fail closed
- [ ] Extra/displaced/count-mismatched record → fail closed
- [ ] `CandidateDispositionRecord` feasibility_digest mutation → result hash mismatch
- [ ] `RankedCandidateRecord` ranked_record_digest mutation → result hash mismatch

### 15.7 Result and hash

- [ ] Result replay equality — identical Phase 2 inputs → identical `result_hash`
- [ ] `result_hash` changes when any digest field changes
- [ ] `result_hash` does not change when derived fields (`optimization_result_id`, `provenance_digest`) are excluded
- [ ] Python 3.11 / 3.12 hash equality
- [ ] Every field of `OptimizationResult` produces different hash when mutated

### 15.8 Provenance

- [ ] Each provenance node payload_hash is correct
- [ ] Edge structure matches §12.3
- [ ] DAG is acyclic
- [ ] Tampered provenance node → root digest mismatch
- [ ] Tampered provenance edge → root digest mismatch
- [ ] Missing provenance node → root digest mismatch
- [ ] Provenance verification: fail closed

### 15.9 Termination invariants

- [ ] `COMPLETE`: all candidates processed, counts sum correctly
- [ ] `PARTIAL`: strict-stop with UNEVALUATED; earlier FEASIBLE may be top-N'ed
- [ ] `FAILED`: artifact verification failure → no `OptimizationResult`
- [ ] Count equation invariants (§10.5) hold for all scenarios
- [ ] Count equations do not overlap: each candidate counted exactly once

### 15.10 Error model

- [ ] Feasibility software exception → runtime failure, not engineering INFEASIBLE
- [ ] Global exception → FAILED termination
- [ ] All error messages in hash/provenance/artifact are fixed deterministic strings
- [ ] No `str(exc)`, `repr(exc)`, traceback, or memory address in any output

---

## 16. Acceptance criteria

1. All Phase 3 tests pass on Python 3.11 and 3.12
2. `result_hash` is deterministic and reproducible from identical Phase 2 inputs
3. Provenance DAG verification detects any tampered node or edge
4. Input verification fails closed for all failure modes
5. Top-N selection never exceeds feasible candidate count
6. No Phase 2 artifact is mutated
7. `PROVIDER_IDENTITY_MISMATCH` candidates never enter ranking or Top-N
8. `UNEVALUATED` candidates (strict-stop) never enter feasibility analysis
9. Ruff check, format check, mypy strict, coverage all pass
10. Pip-audit passes
11. Design review passes before implementation is authorized

---

## 17. Review and authorization

This document is **DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION**.

- Current design review: **CHANGES REQUIRED**
- Frozen Phase 3 contract SHA: **NOT ESTABLISHED**
- Implementation must not begin until a separate engineering design review passes and a frozen contract commit SHA is established

> ⚠️ Until then, all Phase 3 content in this file is subject to change by design review findings.
