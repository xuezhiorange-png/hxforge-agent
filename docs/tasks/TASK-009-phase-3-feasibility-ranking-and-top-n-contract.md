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

Phase 3 consumes Phase 2's real output — `tuple[CandidateEvaluationRecord, ...]` — through a single typed input artifact (`Phase3EvaluationInput`), then produces a deterministic, provenance-tracked `OptimizationResult`.

---

## 2. Non-goals

Explicitly out of scope: TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver logic, candidate generation, catalog schema changes, Phase 2 artifact mutation, re-running TASK-008, recovering strict-stop.

---

## 3. Phase3EvaluationInput (P0-1)

### 3.1 Model

```python
class Phase3EvaluationInput(BaseModel):
    """Complete typed input for Phase 3.

    Constructed from real Phase 2 outputs using existing digest properties.
    No generic sha256(object) calls.

    model_config = ConfigDict(frozen=True, extra="forbid")
    """

    schema_version: int  # 1

    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str   # identity.property (no sha256(identity))

    materialization_result: MaterializationResult
    candidate_set_digest: str             # result.candidate_set.candidate_set_digest (field)
    gate_digest: str                      # result.sizing_gate.gate_digest (field)

    evaluation_records: tuple[CandidateEvaluationRecord, ...]
    evaluation_record_count: int          # len(evaluation_records)

    ordered_evaluation_record_descriptor_digests: tuple[str, ...]

    evaluation_input_digest: str
```

### 3.2 Existing digest bindings — no generic sha256

| Digest field in descriptor | Source |
|---|---|
| `candidate_evaluation_identity_digest` | `record.candidate_evaluation_identity.candidate_evaluation_identity_digest` (*property*, present only for VERIFIED) |
| `verified_rating_evidence_digest` | `record.verified_rating_evidence.compute_explicit_evidence_digest()` (*method*, present only for VERIFIED) |
| `invalid_rating_evidence_digest` | `record.invalid_rating_evidence.invalid_evidence_digest` (*property*, present only for INTEGRITY_INVALID) |
| `claimed_rating_result_audit_digest` | `record.claimed_rating_result_audit.audit_digest` (*property*, present when audit exists) |
| `evaluation_failure_digest` | `sha256(run_failure_payload(record.evaluation_failure))` using `run_failure_payload()` primitive-only dict, then `sha256` from `hexagent.core.canonical` |

Prohibited: `sha256(materialization_result)`, `sha256(sizing_gate)`, `sha256(record)`, `sha256(evidence_snapshot)`, `sha256(RunFailure)`.

### 3.3 Evaluation record descriptor payload

For each record, the deterministic descriptor payload (primitive-only, no model_dump):

```json
{
  "source_qualified_candidate_id": "<str>",
  "evaluation_order_index": <record.evaluation_order_index>,
  "candidate_evaluation_state": "<state.value>",
  "feasible": <bool>,
  "feasibility_status": "<status.value>",
  "hash_verification_outcome": "<outcome.value>",
  "provenance_verification_outcome": "<outcome.value>",
  "provider_identity_matches": <bool>,
  "rating_status": <str or null>,
  "candidate_evaluation_identity_digest": <str or null>,
  "verified_rating_evidence_digest": <str or null>,
  "invalid_rating_evidence_digest": <str or null>,
  "claimed_rating_result_audit_digest": <str or null>,
  "evaluation_failure_digest": <str or null>
}
```

`evaluation_failure_digest` is computed as `sha256(run_failure_payload(record.evaluation_failure))` when non-null. `run_failure_payload()` is the existing production function in `evaluation.py` that returns a deterministic primitive-only dict.

### 3.4 verification steps (11-step sequence)

Any step failure raises `ValueError` with a fixed deterministic message. No `str(exc)`.

**Step 1 — Type verification:** Verify each object is the exact expected Pydantic model type. `sizing_request_identity` is `SizingRequestIdentity`, `materialization_result` is `MaterializationResult`, each record is `CandidateEvaluationRecord`.

**Step 2 — materialization_result.verify_or_raise():** Delegate to existing `MaterializationResult.verify_or_raise()` (covers gate/candidate-set/catalog binding).

**Step 3 — Sizing identity digest:** Verify `sizing_request_identity_digest == sizing_request_identity.sizing_request_identity_digest`.

**Step 4 — candidate_set.verify_digest():** Verify `materialization_result.candidate_set.verify_digest()` is True.

**Step 5 — sizing_gate.verify_digest():** Verify `materialization_result.sizing_gate.verify_digest()` is True.

**Step 6 — candidate_set ↔ sizing identity binding:** Verify `materialization_result.candidate_set.sizing_request_identity_digest == sizing_request_identity_digest`.

**Step 7 — gate ↔ candidate_set binding:** Verify `materialization_result.sizing_gate.gate_digest == materialization_result.candidate_set.passed_gate_digest`.

**Step 8 — Count verification:** Verify `evaluation_record_count == len(evaluation_records)` and `evaluation_record_count == len(materialization_result.candidates)` and `len(ordered_evaluation_record_descriptor_digests) == evaluation_record_count`.

**Step 9 — Record ↔ candidate one-to-one binding:** For each index `i`:
- `record.evaluation_order_index == i`
- `candidate.evaluation_order_index == i`
- `record.source_qualified_candidate_id == candidate.source_qualified_candidate_id`
- `record.source_qualified_candidate_id == materialization_result.candidate_set.ordered_candidate_ids[i]`
- No missing record, no extra record, no duplicate ID, no displaced record, no skipped index, record order matches Phase 2 materialization order.

**Step 10 — State invariant validation:** For each record, verify field combinations against §4.4 valid matrix. Invalid combinations (VERIFIED+identity=None, VERIFIED+invalid_evidence present, INTEGRITY_INVALID+invalid_evidence=None, RUNTIME_FAILED+evaluation_failure=None, UNEVALUATED+identity present, etc.) raise.

**Step 10b — Rating-status parity (only for VERIFIED records):** Verify `record.rating_status == evidence.rating_status.value`. Any mismatch raises.

**Step 10c — Required numeric validation (only for VERIFIED+SUCCEEDED records):** Verify `heat_duty_w` is finite/non-null, `hot_outlet_temperature_k` finite/non-null, `cold_outlet_temperature_k` finite/non-null, `area_outer_m2` finite/non-null. Any missing or non-finite raises.

**Step 10d — Strict-stop invariant validation:** Define `stop_index` as first index where state is INTEGRITY_INVALID or RUNTIME_FAILED. If present: all indices < stop_index must not be UNEVALUATED/INTEGRITY_INVALID/RUNTIME_FAILED; indices > stop_index must be UNEVALUATED only. Violation raises.

**Step 11 — Descriptor digest verification:** For each index `i`, compute `evaluation_record_descriptor_digest` per §3.3 and verify it matches `ordered_evaluation_record_descriptor_digests[i]`. Any mismatch indicates tampered record fields, displaced record, or insertion-order violation.

**Step 12 — evaluation_input_digest verification:** Recompute `evaluation_input_digest` per §3.5 and verify match.

### 3.5 evaluation_input_digest

```
evaluation_input_payload = {
  "schema_version": 1,
  "sizing_request_identity_digest": <str>,
  "candidate_set_digest": <str>,
  "gate_digest": <str>,
  "evaluation_record_count": N,
  "ordered_evaluation_record_descriptor_digests": [digest_0, ..., digest_{N-1}],
}

evaluation_input_digest = sha256(canonical_json(evaluation_input_payload))
```

All payloads are primitive-only (str, int, list, null). No model_dump, no generic serializer.

---

## 4. Phase 2 state matrix (P0-2)

### 4.1 State enum

```python
class CandidateEvaluationState(StrEnum):
    UNEVALUATED = "unevaluated"
    VERIFIED = "verified"
    INTEGRITY_INVALID = "integrity_invalid"
    RUNTIME_FAILED = "runtime_failed"
```

### 4.2 Verification outcome enum

```python
class VerificationOutcome(StrEnum):
    NOT_RUN = "not_run"
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
```

### 4.3 Valid constructible Phase 2 records

Per the production code in `evaluation.py`:

#### RUNTIME_FAILED (4 real production paths)

| Path | hash outcome | provenance outcome | identity | verified evidence | invalid evidence | evaluation_failure |
|---|---|---|---|---|---|---|
| Type/execution failure before verification | NOT_RUN | NOT_RUN | None | None | None | present |
| `verify_hash()` raised Exception | ERROR | NOT_RUN | None | None | None | present |
| `verify_provenance()` raised Exception | PASSED | ERROR | None | None | None | present |
| Trusted evidence extraction/canonicalization failed | PASSED | PASSED | None | None | None | present |

#### INTEGRITY_INVALID (2 real production paths)

| Path | hash outcome | provenance outcome | identity | verified evidence | invalid evidence | evaluation_failure |
|---|---|---|---|---|---|---|
| `verify_hash()` returned False | FAILED | NOT_RUN | None | None | present | None |
| `verify_provenance()` returned False | PASSED | FAILED | None | None | present | None |

#### VERIFIED (1 real production path)

| Condition | hash outcome | provenance outcome | identity | verified evidence | invalid evidence |
|---|---|---|---|---|---|
| Both verify passed + evidence extracted | PASSED | PASSED | present | present | None |

#### UNEVALUATED (1 real production path)

| Condition | hash outcome | provenance outcome | identity | verified evidence | invalid evidence | evaluation_failure |
|---|---|---|---|---|---|---|
| Strict-stop: never reached | NOT_RUN | NOT_RUN | None | None | None | None |

### 4.4 Invalid cross-field combinations (rejected at Step 10)

| Pattern | Rejection reason |
|---|---|
| VERIFIED + identity=None | invariance violation |
| VERIFIED + evidence=None | invariance violation |
| VERIFIED + invalid_evidence present | invariance violation |
| VERIFIED + hash=PASSED + evidence.hash != PASSED | evidence-level verification conflict |
| INTEGRITY_INVALID + invalid_evidence=None | invariance violation |
| INTEGRITY_INVALID + identity present | invariance violation |
| INTEGRITY_INVALID + verified_evidence present | invariance violation |
| RUNTIME_FAILED + evaluation_failure=None | invariance violation |
| RUNTIME_FAILED + identity present | invariance violation |
| RUNTIME_FAILED + verified_evidence present | invariance violation |
| UNEVALUATED + identity present | invariance violation |
| UNEVALUATED + evidence present | invariance violation |
| RUNTIME_FAILED (hash=ERROR) + provenance=ERROR | cannot have both verification failures for one record |
| Any state + verification outcome mismatch with evidence state | evidence-level assertion failed |

### 4.5 Phase 2 → Phase 3 disposition mapping

```python
class Phase3Disposition(StrEnum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    UNEVALUATED = "unevaluated"
    INTEGRITY_FAILED = "integrity_failed"
    PROVENANCE_FAILED = "provenance_failed"
    RUNTIME_FAILED = "runtime_failed"
```

| Phase 2 state | evidence hash | evidence provenance | provider matches | Phase 3 Disposition |
|---|---|---|---|---|
| UNEVALUATED | NOT_RUN | NOT_RUN | any | **UNEVALUATED** |
| VERIFIED | PASSED | PASSED | True | **FEASIBLE** or **INFEASIBLE** (by feasibility check) |
| VERIFIED | PASSED | PASSED | False | **PROVIDER_IDENTITY_MISMATCH** |
| INTEGRITY_INVALID | FAILED | NOT_RUN | any | **INTEGRITY_FAILED** (hash failure) |
| INTEGRITY_INVALID | PASSED | FAILED | any | **PROVENANCE_FAILED** (provenance failure) |
| RUNTIME_FAILED | NOT_RUN/ERROR/PASSED | NOT_RUN/ERROR/PASSED | any | **RUNTIME_FAILED** |
| Phase 3 feasibility exception for VERIFIED candidate | — | — | any | **RUNTIME_FAILED** (Phase 3 disposition; Phase 2 state remains VERIFIED) |

### 4.6 Engineering-rank-eligibility

A candidate is engineering-rank-eligible **only** when `Phase3Disposition.FEASIBLE` AND `provider_identity_matches == True` AND all required numerical fields are finite and non-null.

---

## 5. Strict-stop (P0-3)

### 5.1 Exact stop_index invariant

Define `stop_index` as first index `s` where `record.candidate_evaluation_state` is INTEGRITY_INVALID or RUNTIME_FAILED.

If `stop_index` is not None:

```
all indices < stop_index:  state must be VERIFIED
index == stop_index:        state is INTEGRITY_INVALID or RUNTIME_FAILED
all indices > stop_index:   state must be UNEVALUATED
```

Step 10d verifies this invariant. Violation raises input verification failure.

### 5.2 Termination status

```python
class TerminationStatus(StrEnum):
    COMPLETE = "complete"     # stop_index is None (no strict-stop)
    PARTIAL = "partial"       # stop_index is not None
```

`OptimizationResult.termination_status` is always COMPLETE or PARTIAL. There is no FAILED status in OptimizationResult — see §7.

---

## 6. Numeric canonicalization (P0-5)

### 6.1 Canonical helper

```python
def canonical_decimal(value: Decimal) -> Decimal:
    """Return normalized Decimal; -0 and 0 both become Decimal('0')."""
    if not isinstance(value, Decimal):
        raise TypeError(f"Expected Decimal, got {type(value).__name__}")
    normalized = value.normalize()
    if normalized.is_zero():
        return Decimal("0")   # -0 → 0
    return normalized


def to_canonical_decimal(value: float) -> Decimal:
    """Convert a finite float to canonical Decimal."""
    if isinstance(value, bool):
        raise TypeError("bool is not a valid numeric type")
    if not math.isfinite(value):
        raise ValueError(f"Non-finite float: {value}")
    return canonical_decimal(Decimal(str(value)))
```

### 6.2 Serialization

`str(canonical_decimal(x))` — produces `"0"` for zero (never `"-0"`), no exponent for integers, minimal representation. Python 3.11 and 3.12 produce identical output.

### 6.3 Duty arithmetic — Decimal-only

```python
required = to_canonical_decimal(required_duty_w)
absolute_tolerance = to_canonical_decimal(duty_absolute_tolerance_w)
relative_tolerance = to_canonical_decimal(duty_relative_tolerance)
heat = to_canonical_decimal(heat_duty_w)

duty_tolerance = max(
    absolute_tolerance,
    relative_tolerance * abs(required),
)
duty_error = abs(heat - required)
duty_satisfied = duty_error <= duty_tolerance
```

All arithmetic in Decimal. No float multiplication before conversion.

### 6.4 Signed-zero, sign preservation

- `-0` and `0` both serialize as `"0"` (via `canonical_decimal`)
- Legitimate negative values (e.g. negative temperature difference) keep their sign
- `abs()` is used only where semantically correct (duty error magnitude), not as a general canonicalization tool

### 6.5 Rejected at consumer boundary

- `bool` → `TypeError`
- NaN, Inf, -Inf → `ValueError`
- `-0.0` is accepted as `Decimal("-0.0")` → normalized to `Decimal("0")` by `canonical_decimal()`

---

## 7. Result artifact and failure model (P0-4)

### 7.1 No FAILED in OptimizationResult

There is **one** result artifact type:

```python
class OptimizationResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: int
    optimization_result_id: str           # canonical UUID string
    sizing_request_identity_digest: str
    passed_gate_digest: str
    candidate_set_digest: str
    evaluation_input_digest: str
    optimization_objective: OptimizationObjective
    requested_top_n: int

    # Phase 3 disposition counts (each candidate counted once)
    total_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    provider_mismatch_count: int
    integrity_failed_count: int
    provenance_failed_count: int
    runtime_failed_count: int
    unevaluated_count: int

    # Phase 2 state audit counts (additional, non-overlapping)
    phase2_verified_record_count: int
    phase2_integrity_invalid_record_count: int
    phase2_runtime_failed_record_count: int
    phase2_unevaluated_record_count: int

    ordered_disposition_record_digests: tuple[str, ...]
    ordered_ranked_record_digests: tuple[str, ...]
    ordered_top_n_record_digests: tuple[str, ...]

    termination_status: TerminationStatus   # COMPLETE or PARTIAL only

    warnings: tuple[EngineeringMessage, ...]
    blockers: tuple[EngineeringMessage, ...]
    failure: RunFailure | None

    result_core_hash: str
    provenance_digest: str
    result_hash: str
```

**optimization_result_id** is a canonical UUID string: `str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))`.

### 7.2 Count equations

```
total = feasible + infeasible + provider_mismatch + integrity_failed + provenance_failed + runtime_failed + unevaluated

phase2_verified == feasible + infeasible + provider_mismatch + provenance_failed     # (Phase 2 state=VERIFIED)
phase2_integrity_invalid == integrity_failed                                          # (Phase 2 state=INTEGRITY_INVALID)
phase2_runtime_failed == runtime_failed - exception_count_from_verified               # (Phase 2 state=RUNTIME_FAILED)
phase2_unevaluated == unevaluated                                                     # (Phase 2 state=UNEVALUATED)
```

Each candidate is counted **exactly once** in the Phase 3 disposition counts.

### 7.3 Failure semantics

| Scenario | Behaviour |
|---|---|
| `Phase3EvaluationInput.verify_or_raise()` fails (Step 1-12) | `ValueError` propagates upward. No `OptimizationResult`. Caller sees exception. |
| Per-candidate feasibility check raises `Exception` (not `BaseException`) | Candidate disposition = `RUNTIME_FAILED`; other candidates continue |
| Global Phase 3 exception after successful input verification | Direct `ValueError` propagate upward. No artifact produced. |
| `BaseException` | Never caught. Propagates. |

There is **no** `FailedOptimizationResult`, no partial artifact after global failure. If the input passed verification but a global exception occurs, an exception propagates to the caller. If input verification itself failed, an exception propagates.

---

## 8. Feasibility (P0-6)

### 8.1 Single rule: trust TASK-008

`RatingStatus.SUCCEEDED` means TASK-008 accepted solver convergence, energy closure, final-state consistency, and UA-LMTD closure. Phase 3 does not recompute these.

### 8.2 Missing trusted metric = input verification failure (Step 10c)

For `VERIFIED + rating_status == SUCCEEDED`, the following must be finite and non-null:
- `heat_duty_w`
- `hot_outlet_temperature_k`
- `cold_outlet_temperature_k`
- `area_outer_m2`

If any is null or non-finite, Step 10c raises input verification failure. There is **no** normal engineering infeasibility path for missing metrics.

Therefore `FeasibilityDiagnosticKey` does **not** include `MISSING_TRUSTED_METRIC`.

### 8.3 Diagnostic precedence

| Priority | DiagnosticKey | Condition |
|---|---|---|
| 1 | `PROVIDER_IDENTITY_MISMATCH` | `provider_identity_matches == False` |
| 2 | `RATING_BLOCKED` | `rating_status == BLOCKED` |
| 3 | `RATING_FAILED` | `rating_status == FAILED` |
| 4 | `DUTY_SHORTFALL` | `duty_satisfied == False` |
| 5 | `TERMINAL_DELTA_T_INADEQUATE` | `terminal_delta_t_satisfied == False` |

```python
class FeasibilityDiagnosticKey(StrEnum):
    NONE = "none"
    PROVIDER_IDENTITY_MISMATCH = "provider_identity_mismatch"
    RATING_BLOCKED = "rating_blocked"
    RATING_FAILED = "rating_failed"
    DUTY_SHORTFALL = "duty_shortfall"
    TERMINAL_DELTA_T_INADEQUATE = "terminal_delta_t_inadequate"
```

### 8.4 Terminal delta-T

```
parallel:
    delta_t_1 = hot_inlet - cold_inlet
    delta_t_2 = hot_outlet - cold_outlet
counterflow:
    delta_t_1 = hot_inlet - cold_outlet
    delta_t_2 = hot_outlet - cold_inlet

minimum_actual_terminal_delta_t = min(delta_t_1, delta_t_2)
satisfied = minimum_actual_terminal_delta_t >= to_canonical_decimal(minimum_terminal_delta_t)
```

All values via `to_canonical_decimal()`. Sign: positive heat transfer hot→cold.

---

## 9. Ranking (P0-5)

### 9.1 Source field

`effective_length_m_canonical` from `ManufacturableCandidate.effective_length_m_canonical` (str). Record↔candidate binding (Step 9) is completed before reading.

### 9.2 Sort keys

```
MINIMUM_OUTER_HEAT_TRANSFER_AREA:
    sort_key = (
        to_canonical_decimal(area_outer_m2),
        canonical_decimal(Decimal(effective_length_m_canonical)),
        source_qualified_candidate_id,
    )

MINIMUM_EFFECTIVE_LENGTH:
    sort_key = (
        canonical_decimal(Decimal(effective_length_m_canonical)),
        to_canonical_decimal(area_outer_m2),
        source_qualified_candidate_id,
    )
```

All fields non-null for FEASIBLE candidates.

### 9.3 RankedCandidateRecord

```python
class RankedCandidateRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    rank: int                                                # ≥ 1
    source_qualified_candidate_id: str                       # non-empty
    optimization_objective: OptimizationObjective
    primary_objective_value: str                             # canonical_decimal → str; non-empty; valid finite Decimal
    primary_objective_field: str                             # must be "area_outer_m2" or "effective_length_m_canonical"
    secondary_tie_break_value: str                           # same invariants as primary
    secondary_tie_break_field: str                           # must be the other field from primary
    candidate_evaluation_identity_digest: str                # non-empty, valid "sha256:..." format
    verified_rating_evidence_digest: str                     # same
    feasibility_digest: str                                  # same
    ranked_record_digest: str                                # same

    @model_validator(mode="after")
    def _validate_field_consistency(self) -> Self:
        # rank ≥ 1
        if self.rank < 1:
            raise ValueError("rank must be ≥ 1")
        # values parse as finite Decimal
        for val, field_name in [
            (self.primary_objective_value, "primary_objective_value"),
            (self.secondary_tie_break_value, "secondary_tie_break_value"),
        ]:
            d = Decimal(val)
            if not d.is_finite():
                raise ValueError(f"{field_name}: value must be finite, got {val!r}")
            if d.is_zero() and val != "0":
                raise ValueError(f"{field_name}: zero must be '0', got {val!r}")
        # field identifiers match objective
        if self.optimization_objective == OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            expected_primary = "area_outer_m2"
            expected_secondary = "effective_length_m_canonical"
        else:
            expected_primary = "effective_length_m_canonical"
            expected_secondary = "area_outer_m2"
        if self.primary_objective_field != expected_primary:
            raise ValueError(f"primary_objective_field mismatch: got {self.primary_objective_field!r}, expected {expected_primary!r}")
        if self.secondary_tie_break_field != expected_secondary:
            raise ValueError(f"secondary_tie_break_field mismatch: got {self.secondary_tie_break_field!r}, expected {expected_secondary!r}")
        # all digests valid repository format
        for digest, name in [
            (self.candidate_evaluation_identity_digest, "candidate_evaluation_identity_digest"),
            (self.verified_rating_evidence_digest, "verified_rating_evidence_digest"),
            (self.feasibility_digest, "feasibility_digest"),
            (self.ranked_record_digest, "ranked_record_digest"),
        ]:
            if not digest.startswith("sha256:"):
                raise ValueError(f"{name}: must start with 'sha256:', got {digest!r}")
            hex_part = digest[7:]
            if len(hex_part) != 64:
                raise ValueError(f"{name}: hex part must be 64 chars, got {len(hex_part)}")
            int(hex_part, 16)  # validates hex
        return self
```

---

## 10. Top-N

`requested_top_n = SizingRequestIdentity.top_n` (validated ≥1 at Phase 2). Top-N is selected from FEASIBLE candidates only, after full deterministic sort. Feasible count < N → all returned. Feasible count = 0 → empty.

---

## 11. Three-layer hash (P0-7)

### 11.1 Construction order

```
Step 1: result_core_payload   (excludes optimization_result_id, result_core_hash, provenance_digest, result_hash)
Step 2: result_core_hash = sha256(canonical_json(result_core_payload))
Step 3: provenance graph built; result-core node payload_hash = result_core_hash (already "sha256:..." format)
Step 4: provenance_digest = ProvenanceGraph.compute_hash()  # returns "sha256:..."
Step 5: result_hash = sha256(canonical_json({"result_core_hash": result_core_hash, "provenance_digest": provenance_digest}))
Step 6: optimization_result_id = str(uuid.uuid5(PHASE3_RESULT_NAMESPACE, result_hash))
```

No circular dependency: provenance graph is built from `result_core_hash` (which is computed before the graph), not from `result_hash` or `provenance_digest`.

### 11.2 Namespace

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
```

---

## 12. Provenance topology (P0-7, P0-8, P0-9)

### 12.1 Node types and payload_hash rules

Each node's `payload_hash` is either:
- An existing repository digest (already `"sha256:<hex>"`) — use directly
- A primitive-only payload hashed via `sha256_digest()` — produces `"sha256:<hex>"`

**No double-prefixing.** If the source value is already `"sha256:<hex>"`, assign it as-is — never write `"sha256:" + "sha256:<hex>"`.

| Node role | `ProvenanceNodeType` | payload_hash |
|---|---|---|
| Root (with design case) | `CASE_REVISION` | `sha256_digest({"design_case_revision_id": str(id)})` |
| Root (without design case) | `EXTERNAL` | `sha256_digest({"sizing_request_digest": sizing_request_identity_digest})` |
| Sizing request | `INPUT_FILE` | `sizing_request_identity_digest` (already `"sha256:..."`) |
| Passed sizing gate | `CALCULATION_RUN` | `gate_digest` (already `"sha256:..."`) |
| Materialized candidate set | `CALCULATION_RUN` | `candidate_set_digest` (already `"sha256:..."`) |
| Evaluation input | `INTERMEDIATE` | `evaluation_input_digest` (already `"sha256:..."`) |
| Each disposition record | `INTERMEDIATE` | disposition record `feasibility_digest` (already `"sha256:..."`) |
| Each ranked record | `INTERMEDIATE` | ranked record `ranked_record_digest` (already `"sha256:..."`) |
| Top-N selection | `INTERMEDIATE` | `sha256_digest({"ordered_top_n_record_digests": list})` |
| Result core | `RESULT` | `result_core_hash` (already `"sha256:..."`) |
| Optimizer | `OPTIMIZER` | `sha256_digest(optimizer_payload)` — payload defined in §12.3 |

### 12.2 Unified UUID5 for all nodes

```python
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")

node_id = uuid.uuid5(
    PHASE3_PROVENANCE_NAMESPACE,
    f"{node_type.value}:{payload_hash}",
)
```

Every node uses this same algorithm — root, sizing request, gate, candidate set, records, Top-N, result core, optimizer. No special case for root.

`payload_hash` must be validated as a valid repository digest (`"sha256:" + 64 hex chars`) before being used in the UUID5 name.

### 12.3 Optimizer payload (no post-provenance fields)

Constructed before the provenance graph:

```json
{
  "schema_version": 1,
  "evaluation_input_digest": "<sha256:...>",
  "optimization_objective": "<objective.value>",
  "requested_top_n": <int>,
  "termination_status": "<status.value>",
  "result_core_hash": "<sha256:...>",
  "phase3_policy_version": "1",
  "software_version": "<from runtime>"
}
```

The optimizer payload does **not** include `provenance_digest`, `result_hash`, `optimization_result_id`, or the full `OptimizationResult`.

### 12.4 Edge topology

```
Root ──regulates──► Sizing Request
                         │
                         │ consumed_by
                         ▼
                 Passed Sizing Gate (CALCULATION_RUN)
                         │
                         │ produced
                         ▼
               Materialized Candidate Set (CALCULATION_RUN)
                         │
                         │ consumed_by
                         ▼
                  Evaluation Input (INTERMEDIATE)
                         │
                         │ evaluated
                         ▼
                  Disposition Records (INTERMEDIATE)
                         │
                         │ ranked (only FEASIBLE)
                         ▼
                   Ranked Records (INTERMEDIATE)
                         │
                         │ selected (only first N FEASIBLE)
                         ▼
                   Top-N Selection (INTERMEDIATE)
                         │
                         │ produced
                         ▼
                    Result Core (RESULT)
                         │
                         │ executed_by
                         ▼
                    Optimizer (OPTIMIZER)
```

Not all ranked records connect to Top-N — only the selected N FEASIBLE candidates.

### 12.5 Edge relations

| Source | Target | `relation` |
|---|---|---|
| Root | Sizing Request | `"regulates"` |
| Sizing Request | Passed Sizing Gate | `"consumed_by"` |
| Passed Sizing Gate | Materialized Candidate Set | `"produced"` |
| Materialized Candidate Set | Evaluation Input | `"consumed_by"` |
| Evaluation Input | each Disposition Record | `"evaluated"` |
| each Disposition Record (FEASIBLE) | its Ranked Record | `"ranked"` |
| each Ranked Record (selected only) | Top-N Selection | `"selected"` |
| Top-N Selection | Result Core | `"produced"` |
| Result Core | Optimizer | `"executed_by"` |

### 12.6 Graph constraints

- Uses existing `ProvenanceGraph.validate_graph()` — unique node IDs, all edges reference existing nodes, no self-loops, acyclic
- Must contain a `CASE_REVISION` or `EXTERNAL` root node AND at least one `CALCULATION_RUN` node
- Canonical node/edge ordering via `_canonical_node_key` and `_canonical_edge_key`
- `provenance_digest = ProvenanceGraph.compute_hash()` (existing method)

---

## 13. Warning/blocker canonicalization (P0-10)

### 13.1 Sort key

Warnings and blockers are sorted by a deterministic multi-field key before any digest or payload:

```
sort_key = (
    message.severity.value,      # e.g. "warning", "blocker"
    message.code.value,          # e.g. "hash_mismatch", "provenance_incomplete"
    message.message,             # fixed deterministic string
    message.source_module,       # source module identifier
    tuple(sorted(message.affected_paths)),  # sorted path list
    canonical_context_marker_digest,        # sha256 of canonical context entries
)
```

The `canonical_context_marker_digest` is `sha256(canonical_json(build_canonical_context_entries(message.context)))` using the existing context-to-payload helper.

### 13.2 Duplicate preservation

Duplicates are **preserved** — identical messages at identical positions in the original list remain as separate entries. If sorting produces adjacent identical entries, they are kept as-is. The sort key is stable (same messages always produce the same order), so the presence of duplicates does not introduce non-determinism.

### 13.3 Message digest

Each `EngineeringMessage` is converted to a canonical primitive-only payload via `engineering_message_payload()` (existing production function in `evaluation.py`), then hashed to produce a `message_digest`.

### 13.4 Failure digest

`RunFailure` is converted to a canonical primitive-only payload via `run_failure_payload()`, then `sha256` to produce a `failure_digest`.

### 13.5 Warnings/blockers in result core payload

The `result_core_payload` contains `ordered_warning_digests` and `ordered_blocker_digests` — sorted by the key in §13.1.

---

## 14. Error model (P0-9)

### 14.1 Choice: extend existing ErrorCode

Phase 3 error codes are added to `ErrorCode` in `src/hexagent/domain/messages.py`:

```python
PHASE3_INPUT_VERIFICATION_FAILED = "phase3_input_verification_failed"
PHASE3_NON_FINITE_NUMERIC = "phase3_non_finite_numeric"
PHASE3_FEASIBILITY_RUNTIME_FAILURE = "phase3_feasibility_runtime_failure"
PHASE3_RANKING_RUNTIME_FAILURE = "phase3_ranking_runtime_failure"
PHASE3_RESULT_CONSTRUCTION_FAILED = "phase3_result_construction_failed"
PHASE3_HASH_VERIFICATION_FAILED = "phase3_hash_verification_failed"
PHASE3_PROVENANCE_VERIFICATION_FAILED = "phase3_provenance_verification_failed"
```

### 14.2 Fixed messages

All messages entering hash, provenance, or user-visible artifact use fixed strings. Prohibited: `str(exc)`, `repr(exc)`, `traceback`, addresses, runtime object representations.

---

## 15. Implementation boundary

### Existing files modified

| Path | Change |
|---|---|
| `src/hexagent/domain/messages.py` | Add 7 Phase 3 error codes to `ErrorCode` enum |

### New files

| Path | Contents |
|---|---|
| `src/hexagent/optimization/phase3_input.py` | `Phase3EvaluationInput` + `verify_or_raise()` |
| `src/hexagent/optimization/feasibility.py` | Feasibility classification + `CandidateDispositionRecord` |
| `src/hexagent/optimization/ranking.py` | Deterministic ranking + `RankedCandidateRecord` |
| `src/hexagent/optimization/result.py` | `OptimizationResult` + hash + provenance |
| `tests/unit/test_task009_phase3_*.py` | Tests |

### Untouched

All other `src/hexagent/` files, including all Phase 1/2 optimization modules, TASK-008 modules, catalog modules, and all existing tests.

---

## 16. Test matrix

### 16.1 Phase 2 state combinations

- [ ] Each real RUNTIME_FAILED path (NOT_RUN/NOT_RUN, ERROR/NOT_RUN, PASSED/ERROR, PASSED/PASSED) accepted
- [ ] Each real INTEGRITY_INVALID path (FAILED/NOT_RUN, PASSED/FAILED) accepted
- [ ] VERIFIED (PASSED/PASSED) accepted
- [ ] UNEVALUATED (NOT_RUN/NOT_RUN) accepted

### 16.2 Invalid state combinations rejected at Step 10

- [ ] VERIFIED + identity=None
- [ ] VERIFIED + invalid_evidence present
- [ ] INTEGRITY_INVALID + invalid_evidence=None
- [ ] INTEGRITY_INVALID + identity present
- [ ] RUNTIME_FAILED + evaluation_failure=None
- [ ] RUNTIME_FAILED + identity present
- [ ] UNEVALUATED + identity present

### 16.3 Input verification

- [ ] Descriptor digest list stored and independently verified (Step 11)
- [ ] `record.evaluation_order_index` mutation changes descriptor digest
- [ ] `RunFailure` uses `run_failure_payload()` — not `sha256(failure)`
- [ ] Record↔candidate one-to-one binding
- [ ] Displaced/missing/extra/duplicate record rejected
- [ ] Invalid cross-field combinations rejected

### 16.4 Strict-stop

- [ ] Stop on first candidate
- [ ] Stop on middle candidate
- [ ] Stop on last candidate
- [ ] Earlier FEASIBLE with stop → PARTIAL + Top-N from earlier
- [ ] No FEASIBLE before stop
- [ ] No strict-stop → COMPLETE
- [ ] VERIFIED after stop index rejected
- [ ] Phase 3 does not call TASK-008

### 16.5 Counts

- [ ] Phase 3 disposition counts are disjoint and sum to total
- [ ] Phase 2 state counts and Phase 3 disposition counts separated
- [ ] Phase 3 per-candidate exception counted once in `runtime_failed_count`

### 16.6 Failure semantics

- [ ] Input verification failure creates no `OptimizationResult` (exception propagates)
- [ ] Post-input global exception propagates (no artifact)
- [ ] Per-candidate feasibility exception → that candidate = RUNTIME_FAILED, others continue

### 16.7 Decimal

- [ ] All duty tolerance arithmetic uses Decimal (no float multiplication before conversion)
- [ ] `-0` serializes as `"0"`
- [ ] Negative non-zero value keeps its sign
- [ ] `bool` rejected
- [ ] NaN/Inf rejected at consumer boundary

### 16.8 Missing SUCCEEDED metric

- [ ] Missing `heat_duty_w` on SUCCEEDED → input verification failure (Step 10c)
- [ ] Missing `hot_outlet_temperature_k` → input verification failure
- [ ] Missing `area_outer_m2` → input verification failure

### 16.9 Ranking and Top-N

- [ ] Both objective sort keys produce correct ordering
- [ ] Non-null invariant enforced for FEASIBLE
- [ ] Top-N feasible-only
- [ ] Fewer/exact/more than N
- [ ] Zero feasible → empty Top-N

### 16.10 Provenance

- [ ] Existing repository digest not double-prefixed (e.g. `gate_digest` used directly)
- [ ] UUID/list provenance payloads use `sha256_digest()` once
- [ ] Optimizer node has no post-provenance fields (`provenance_digest`, `result_hash` absent)
- [ ] All nodes use one UUID5 algorithm (including root)
- [ ] Only selected ranked records connect to Top-N node
- [ ] Graph validates: acyclic, root, CALCULATION_RUN

### 16.11 Hash

- [ ] Three-layer construction has no circular dependency
- [ ] `result_core_hash` excludes `provenance_digest` and `result_hash`
- [ ] `result_hash` changes when `provenance_digest` changes
- [ ] `result_core_hash` is insensitive to `provenance_digest` changes
- [ ] `optimization_result_id` is canonical UUID string (consistent type)
- [ ] Python 3.11/3.12 hash equality

### 16.12 Warning/blocker sorting

- [ ] Duplicates preserved, not deduplicated
- [ ] Sort key includes severity, code, message, source_module, affected_paths, context digest
- [ ] Stable sort: same input order → same sorted output

### 16.13 RankedCandidateRecord invariants

- [ ] Non-canonical Decimal strings rejected
- [ ] Invalid field/objective combinations rejected (primary != expected field for objective)
- [ ] Invalid digest format rejected
- [ ] rank < 1 rejected

### 16.14 DONE vocabulary

- [ ] All status references use `DONE` consistently (not `COMPLETE`)

---

## 17. Acceptance criteria

1. All tests pass on Python 3.11 and 3.12
2. `result_hash` is deterministic and reproducible
3. Provenance DAG verification detects tampered nodes or edges
4. Input verification fails closed for all 12 steps
5. Top-N selection never exceeds feasible candidate count
6. No Phase 2 artifact is mutated
7. PROVIDER_IDENTITY_MISMATCH candidates never enter ranking or Top-N
8. UNEVALUATED candidates never enter feasibility analysis
9. Ruff check, format check, mypy strict, coverage pass
10. Pip-audit passes
11. Design review passes before implementation is authorized

---

## 18. Review and authorization

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED

Implementation must not begin until a separate engineering design review passes and a frozen contract commit SHA is established.
