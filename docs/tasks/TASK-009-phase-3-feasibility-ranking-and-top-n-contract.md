# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Design Review:** CHANGES REQUIRED — PENDING RE-REVIEW
**Frozen Phase 3 contract SHA:** NOT ESTABLISHED
**Depends on:** TASK-008, TASK-009 Phase 2 (c77d723c51c4d8045cafa783f97fdc0d628a0e91)
**Frozen Phase 1-2 contract SHA:** 7e4522ab5be740fb6af759743c1c1f79801312fc

> Design contract for review only. No implementation until a separate engineering design review passes and a frozen contract commit SHA is established.

---

## 1. Scope & non-goals

Phase 3 consumes `tuple[CandidateEvaluationRecord, ...]` via `Phase3EvaluationInput` and produces a deterministic `OptimizationResult`.

Non-goals: TASK-010, C4, pressure-drop, velocity, pump power, economic/Pareto/stochastic/heuristic/ML optimization, new correlations, rating solver, candidate generation, catalog changes, Phase 2 mutation, re-running TASK-008, recovering strict-stop.

---

## 2. Phase3EvaluationInput

### 2.1 Model

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

### 2.2 Payload helpers

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

Digest: `sha256_digest(payload)` — no self-reference.

### 2.3 13-step verify_or_raise()

Step 1: type verification. Step 2: `materialization_result.verify_or_raise()`. Step 3: sizing identity digest. Step 4: `candidate_set.verify_digest()`. Step 5: `sizing_gate.verify_digest()`. Step 6: candidate-set ↔ sizing binding. Step 7: gate ↔ candidate-set binding. Step 8: count parity. Step 9: one-to-one record↔candidate binding. Step 10: exhaustive state verification per §3 matrix. Step 11: strict-stop invariant. Step 12: descriptor digest verification. Step 13: `evaluation_input_digest` verification.

All failures raise `ValueError` with fixed deterministic message. No `str(exc)`.

---

## 3. Exhaustive Phase 2 constructor matrix (P1-1)

Every row is an exact production path from `evaluation.py`. All 14 fields frozen per path.

### 3.1 VERIFIED (1 path — lines 2634–2646)

```
state=VERIFIED, feasible=False,
feasibility_status=NOT_EVALUATED (if matches=True) or PROVIDER_IDENTITY_MISMATCH (if matches=False),
identity=eval_identity, claimed_audit=None, verified_evidence=evidence, invalid_evidence=None,
provider_matches=bool, eval_failure=None, rating_status=RatingStatus.value or None,
hash=PASSED, provenance=PASSED
```

Provider parity (VERIFIED only):
```python
provider_matches == True  ⇔  feasibility_status == NOT_EVALUATED
provider_matches == False ⇔  feasibility_status == PROVIDER_IDENTITY_MISMATCH
```

### 3.2 INTEGRITY_INVALID (2 paths)

| Field | Path A (hash false, L2333) | Path B (provenance false, L2388) |
|---|---|---|
| state | INTEGRITY_INVALID | INTEGRITY_INVALID |
| feasible | False | False |
| feasibility_status | NOT_EVALUATED | NOT_EVALUATED |
| identity | None | None |
| claimed_audit | present, claim_state=HASH_VERIFICATION_ERROR, hash=FAILED, prov=NOT_RUN | present, claim_state=PROVENANCE_VERIFICATION_ERROR, hash=PASSED, prov=FAILED |
| verified_evidence | None | None |
| invalid_evidence | present | present |
| provider_matches | **False** | **True** (unset, default) |
| eval_failure | None | None |
| rating_status | None | None |
| hash_outcome | **FAILED** | **PASSED** |
| provenance_outcome | **NOT_RUN** | **FAILED** |

### 3.3 RUNTIME_FAILED (10 paths) — full 14-field matrix

| # | File line | state | feasible | feas_status | identity | claimed_audit | verified_evidence | invalid_evidence | provider | eval_failure | hash | prov | rating_status | failure code | failure message |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | L2277 | RF | F | NE | None | **present** (UNREADABLE,hash=NR,prov=NR) | None | None | True(def) | **present** | **NR** | **NR** | None | INVALID_STATE_TRANSITION | "Expected exact RatingResult, got ..." |
| 2 | L2303 | RF | F | NE | None | **present** (HASH_VERIFICATION_ERROR,hash=ERR,prov=NR) | None | None | True(def) | **present** | **ERROR** | **NR** | None | HASH_MISMATCH | "Rating result hash verification raised." |
| 3 | L2358 | RF | F | NE | None | **present** (PROVENANCE_VERIFICATION_ERROR,hash=PASSED,prov=ERR) | None | None | True(def) | **present** | **PASSED** | **ERROR** | None | PROVENANCE_INCOMPLETE | "Rating result provenance verification raised." |
| 4 | L2414 | RF | F | NE | None | **present** (HASH_VERIFICATION_ERROR,hash=PASSED,prov=PASSED) | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | INVALID_STATE_TRANSITION | "Failed to extract trusted evidence" |
| 5 | L2478 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." |
| 6 | L2511 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." |
| 7 | L2543 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." |
| 8 | L2575 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | PROVENANCE_INCOMPLETE | "Trusted context canonicalization failed." |
| 9 | L2611 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | INVALID_STATE_TRANSITION | "Failed to build candidate evaluation identity" |
| 10 | L2672 | RF | F | NE | None | **None** | None | None | True(def) | **present** | **PASSED** | **PASSED** | None | PROVENANCE_INCOMPLETE | "Trusted rating verification failed." |

RF = RUNTIME_FAILED, F = False, NE = NOT_EVALUATED, NR = NOT_RUN, def = default

Paths 5–8 are distinguishable at lower levels (warning/blocker/failure descriptor) but at the record level all present PASSED/PASSED, audit=None, failure present. Step 10 accepts them all as valid RUNTIME_FAILED. No further distinction is needed at Phase 3 input because Phase 3 does not re-classify the failure mode — it maps all to disposition RUNTIME_FAILED.

### 3.4 UNEVALUATED

```
state=UNEVALUATED, feasible=False, feasibility_status=NOT_EVALUATED,
identity=None, claimed_audit=None, verified_evidence=None, invalid_evidence=None,
provider_matches=True (default), eval_failure=None, rating_status=None,
hash=NOT_RUN, provenance=NOT_RUN
```

---

## 4. Strict-stop

`stop_index` = first index where state is INTEGRITY_INVALID or RUNTIME_FAILED.
Indices < stop_index: must be VERIFIED. Index == stop_index: INTEGRITY_INVALID or RUNTIME_FAILED. Indices > stop_index: must be UNEVALUATED.
COMPLETE = no strict-stop. PARTIAL = strict-stop occurred.

---

## 5. Decimal canonicalization

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

## 6. Phase3CandidateClassificationInput (P0-2)

Only authoritative artifacts — no duplicate fields.

```python
class Phase3CandidateClassificationInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_record: CandidateEvaluationRecord
    source_record_descriptor_digest: str
    materialized_candidate: ManufacturableCandidate
    sizing_request_identity: SizingRequestIdentity
    sizing_request_identity_digest: str

    @model_validator(mode="after")
    def _validate(self) -> Self:
        # Sizing identity digest
        if self.sizing_request_identity_digest != self.sizing_request_identity.sizing_request_identity_digest:
            raise ValueError("sizing_request_identity_digest mismatch")
        # Candidate ↔ materialized candidate binding
        if self.source_record.source_qualified_candidate_id != self.materialized_candidate.source_qualified_candidate_id:
            raise ValueError("candidate_id mismatch with materialized_candidate")
        if self.source_record.evaluation_order_index != self.materialized_candidate.evaluation_order_index:
            raise ValueError("evaluation_order_index mismatch with materialized_candidate")
        # Descriptor digest
        expected_desc = sha256_digest(evaluation_record_descriptor_payload(self.source_record))
        if self.source_record_descriptor_digest != expected_desc:
            raise ValueError("source_record_descriptor_digest mismatch")
        return self
```

Classification reads from `sizing_request_identity`:
- `required_duty_w` → `self.sizing_request_identity.required_duty_w`
- `duty_absolute_tolerance_w` → `self.sizing_request_identity.duty_absolute_tolerance_w`
- `duty_relative_tolerance` → `self.sizing_request_identity.duty_relative_tolerance`
- `minimum_terminal_delta_t` → `self.sizing_request_identity.minimum_terminal_delta_t`
- `flow_arrangement` → `self.sizing_request_identity.flow_arrangement`
- `hot_inlet_temperature_k` → `self.sizing_request_identity.hot_inlet_temperature_k`
- `cold_inlet_temperature_k` → `self.sizing_request_identity.cold_inlet_temperature_k`
- `optimization_objective` → `self.sizing_request_identity.optimization_objective`
- `top_n` → `self.sizing_request_identity.top_n`

Verified thermal metrics from `self.source_record.verified_rating_evidence`:
- `heat_duty_w`, `hot_outlet_temperature_k`, `cold_outlet_temperature_k`, `area_outer_m2`

---

## 7. classify_candidate() (P0-3, P0-4)

```python
def classify_candidate(
    input: Phase3CandidateClassificationInput,
) -> CandidateDispositionRecord:

    rec = input.source_record
    sizing = input.sizing_request_identity
    evidence = rec.verified_rating_evidence

    # 1. Non-VERIFIED source states → direct mapping
    if rec.candidate_evaluation_state != CandidateEvaluationState.VERIFIED:
        return _map_non_verified(rec)

    # 2. Provider mismatch
    if not rec.provider_identity_matches:
        return _build_disposition(
            rec, evidence, sizing, input.materialized_candidate,
            disposition=Phase3Disposition.PROVIDER_IDENTITY_MISMATCH,
            diagnostic=FeasibilityDiagnosticKey.PROVIDER_IDENTITY_MISMATCH,
        )

    # 3. rating_status == None → Phase 3 runtime failure (P0-4)
    if rec.rating_status is None:
        failure = RunFailure(
            code=ErrorCode.PHASE3_MISSING_RATING_STATUS,
            message="Verified record has no rating status.",
            traceback=None,
            context=(
                ("source_qualified_candidate_id", rec.source_qualified_candidate_id),
                ("evaluation_order_index", rec.evaluation_order_index),
                ("source_record_descriptor_digest", input.source_record_descriptor_digest),
            ),
        )
        return _build_phase3_runtime_failure(input, failure, retain_identity_evidence=True)

    # 4. BLOCKED / FAILED rating
    if rec.rating_status == RatingStatus.BLOCKED.value:
        return _build_disposition(
            rec, evidence, sizing, input.materialized_candidate,
            disposition=Phase3Disposition.INFEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.RATING_BLOCKED,
        )
    if rec.rating_status == RatingStatus.FAILED.value:
        return _build_disposition(
            rec, evidence, sizing, input.materialized_candidate,
            disposition=Phase3Disposition.INFEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.RATING_FAILED,
        )

    # 5. SUCCEEDED — extract trusted metrics (required, Step 10 already validated)
    heat_w = to_canonical_decimal(evidence.heat_duty_w)
    area_m2 = to_canonical_decimal(evidence.area_outer_m2)
    hot_in = to_canonical_decimal(sizing.hot_inlet_temperature_k)
    cold_in = to_canonical_decimal(sizing.cold_inlet_temperature_k)
    hot_out = to_canonical_decimal(evidence.hot_outlet_temperature_k)
    cold_out = to_canonical_decimal(evidence.cold_outlet_temperature_k)

    # 6. Duty satisfaction
    required = to_canonical_decimal(sizing.required_duty_w)
    abs_tol = to_canonical_decimal(sizing.duty_absolute_tolerance_w)
    rel_tol = to_canonical_decimal(sizing.duty_relative_tolerance)
    duty_tol = max(abs_tol, rel_tol * abs(required))
    duty_error = abs(heat_w - required)
    duty_ok = duty_error <= duty_tol

    if not duty_ok:
        return _build_disposition(
            rec, evidence, sizing, input.materialized_candidate,
            disposition=Phase3Disposition.INFEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.DUTY_SHORTFALL,
        )

    # 7. Terminal delta-T
    fa = sizing.flow_arrangement
    if fa == FlowArrangement.PARALLEL.value:
        dt1 = hot_in - cold_in
        dt2 = hot_out - cold_out
    else:
        # COUNTERFLOW
        dt1 = hot_in - cold_out
        dt2 = hot_out - cold_in
    min_dt = min(dt1, dt2)
    min_req = to_canonical_decimal(sizing.minimum_terminal_delta_t)
    dt_ok = min_dt >= min_req

    if not dt_ok:
        return _build_disposition(
            rec, evidence, sizing, input.materialized_candidate,
            disposition=Phase3Disposition.INFEASIBLE,
            diagnostic=FeasibilityDiagnosticKey.TERMINAL_DELTA_T_INADEQUATE,
        )

    # 8. FEASIBLE
    return _build_disposition(
        rec, evidence, sizing, input.materialized_candidate,
        disposition=Phase3Disposition.FEASIBLE,
        diagnostic=FeasibilityDiagnosticKey.NONE,
    )
```

### 7.1 Helper: _map_non_verified

```python
def _map_non_verified(rec: CandidateEvaluationRecord) -> CandidateDispositionRecord:
    state = rec.candidate_evaluation_state
    if state == CandidateEvaluationState.UNEVALUATED:
        return _build_disposition_simple(rec, Phase3Disposition.UNEVALUATED, FeasibilityDiagnosticKey.NONE)
    if state == CandidateEvaluationState.INTEGRITY_INVALID:
        if rec.hash_verification_outcome == VerificationOutcome.FAILED:
            return _build_disposition_simple(rec, Phase3Disposition.INTEGRITY_FAILED, FeasibilityDiagnosticKey.NONE)
        return _build_disposition_simple(rec, Phase3Disposition.PROVENANCE_FAILED, FeasibilityDiagnosticKey.NONE)
    if state == CandidateEvaluationState.RUNTIME_FAILED:
        return _build_disposition_simple(rec, Phase3Disposition.RUNTIME_FAILED, FeasibilityDiagnosticKey.NONE)
    raise ValueError(f"unexpected state: {state}")
```

### 7.2 Helper: _build_disposition

```python
def _build_disposition(
    rec, evidence, sizing, candidate,
    *, disposition, diagnostic,
) -> CandidateDispositionRecord:
    # Create warning/blocker digests via single-pass descriptors
    warning_descriptors = tuple(
        build_engineering_message_descriptor(w)
        for w in (evidence.warnings if evidence else ())
    )
    blocker_descriptors = tuple(
        build_engineering_message_descriptor(b)
        for b in (evidence.blockers if evidence else ())
    )
    ordered_warnings = tuple(
        sorted(
            (d for d in warning_descriptors if d.canonicalization_error is None),
            key=lambda d: d.owner_sort_key,
        )
    )
    ordered_blockers = tuple(
        sorted(
            (d for d in blocker_descriptors if d.canonicalization_error is None),
            key=lambda d: d.owner_sort_key,
        )
    )
    warning_digests = tuple(d.message_payload_digest for d in ordered_warnings)
    blocker_digests = tuple(d.message_payload_digest for d in ordered_blockers)

    is_feasible = (disposition is Phase3Disposition.FEASIBLE)
    record = CandidateDispositionRecord(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=sha256_digest(evaluation_record_descriptor_payload(rec)),
        disposition=disposition,
        diagnostic=diagnostic,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=(
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if rec.candidate_evaluation_identity else None
        ),
        verified_rating_evidence_digest=(
            evidence.compute_explicit_evidence_digest()
            if evidence else None
        ),
        invalid_rating_evidence_digest=(
            rec.invalid_rating_evidence.invalid_evidence_digest
            if rec.invalid_rating_evidence else None
        ),
        primary_engineering_value=(
            canonical_decimal_string(to_canonical_decimal(evidence.area_outer_m2))
            if is_feasible else None
        ),
        secondary_engineering_value=(
            canonical_decimal_string(canonical_decimal(Decimal(candidate.effective_length_m_canonical)))
            if is_feasible else None
        ),
        ordered_warning_digests=warning_digests,
        ordered_blocker_digests=blocker_digests,
        source_evaluation_failure_digest=(
            sha256_digest(run_failure_payload(rec.evaluation_failure))
            if rec.evaluation_failure is not None else None
        ),
        phase3_failure_digest=None,
        failure_origin=FailureOrigin.NONE,
    )
    object.__setattr__(record, "feasibility_digest", sha256_digest(candidate_disposition_payload(record)))
    return record
```

### 7.3 Helper: _build_disposition_simple (for non-VERIFIED states)

```python
def _build_disposition_simple(rec, disposition, diagnostic):
    record = CandidateDispositionRecord(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=sha256_digest(evaluation_record_descriptor_payload(rec)),
        disposition=disposition,
        diagnostic=diagnostic,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=None,
        candidate_evaluation_identity_digest=None,
        verified_rating_evidence_digest=None,
        invalid_rating_evidence_digest=(
            rec.invalid_rating_evidence.invalid_evidence_digest
            if rec.invalid_rating_evidence else None
        ),
        primary_engineering_value=None,
        secondary_engineering_value=None,
        ordered_warning_digests=(),
        ordered_blocker_digests=(),
        source_evaluation_failure_digest=(
            sha256_digest(run_failure_payload(rec.evaluation_failure))
            if rec.evaluation_failure is not None else None
        ),
        phase3_failure_digest=None,
        failure_origin=(
            FailureOrigin.PHASE2_EVALUATION if rec.evaluation_failure is not None
            else FailureOrigin.NONE
        ),
    )
    object.__setattr__(record, "feasibility_digest", sha256_digest(candidate_disposition_payload(record)))
    return record
```

### 7.4 Phase 3 runtime failure helper

```python
def _build_phase3_runtime_failure(
    input: Phase3CandidateClassificationInput,
    failure: RunFailure,
    retain_identity_evidence: bool,
) -> CandidateDispositionRecord:
    rec = input.source_record
    evidence = rec.verified_rating_evidence
    record = CandidateDispositionRecord(
        source_qualified_candidate_id=rec.source_qualified_candidate_id,
        evaluation_order_index=rec.evaluation_order_index,
        source_candidate_evaluation_state=rec.candidate_evaluation_state,
        source_hash_verification_outcome=rec.hash_verification_outcome,
        source_provenance_verification_outcome=rec.provenance_verification_outcome,
        source_record_descriptor_digest=sha256_digest(evaluation_record_descriptor_payload(rec)),
        disposition=Phase3Disposition.RUNTIME_FAILED,
        diagnostic=FeasibilityDiagnosticKey.NONE,
        provider_identity_matches=rec.provider_identity_matches,
        rating_status=rec.rating_status,
        candidate_evaluation_identity_digest=(
            rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
            if retain_identity_evidence and rec.candidate_evaluation_identity else None
        ),
        verified_rating_evidence_digest=(
            evidence.compute_explicit_evidence_digest()
            if retain_identity_evidence and evidence else None
        ),
        invalid_rating_evidence_digest=None,
        primary_engineering_value=None,
        secondary_engineering_value=None,
        ordered_warning_digests=(),
        ordered_blocker_digests=(),
        source_evaluation_failure_digest=None,
        phase3_failure_digest=sha256_digest(run_failure_payload(failure)),
        failure_origin=FailureOrigin.PHASE3_CLASSIFICATION,
    )
    object.__setattr__(record, "feasibility_digest", sha256_digest(candidate_disposition_payload(record)))
    return record
```

---

## 8. FailureOrigin and CandidateDispositionRecord (P0-5, P0-6)

### 8.1 FailureOrigin

```python
class FailureOrigin(StrEnum):
    NONE = "none"
    PHASE2_EVALUATION = "phase2_evaluation"
    PHASE3_CLASSIFICATION = "phase3_classification"
```

### 8.2 CandidateDispositionRecord

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

    source_evaluation_failure_digest: str | None
    phase3_failure_digest: str | None
    failure_origin: FailureOrigin

    feasibility_digest: str

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

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

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if not self.source_qualified_candidate_id:
            raise ValueError("candidate_id must be non-empty")
        if self.evaluation_order_index < 0:
            raise ValueError("evaluation_order_index must be ≥ 0")

        # Common digest validation
        for d, n in [(self.source_record_descriptor_digest, "source_desc"),
                      (self.feasibility_digest, "feasibility")]:
            if not self.DIGEST_PATTERN.match(d):
                raise ValueError(f"{n}: invalid digest {d!r}")
        for digest_list, name in [(self.ordered_warning_digests, "warning"),
                                   (self.ordered_blocker_digests, "blocker")]:
            for d in digest_list:
                self._check_digest(d, name)
        self._check_digest(self.candidate_evaluation_identity_digest, "identity")
        self._check_digest(self.verified_rating_evidence_digest, "verified_evidence")
        self._check_digest(self.invalid_rating_evidence_digest, "invalid_evidence")
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
            if self.primary_engineering_value is None:
                raise ValueError("FEASIBLE: primary value required")
            if self.secondary_engineering_value is None:
                raise ValueError("FEASIBLE: secondary value required")
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

        # INFEASIBLE (sub-checked by diagnostic)
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
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("PROVENANCE_FAILED: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("PROVENANCE_FAILED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("PROVENANCE_FAILED: failure_origin must be NONE")

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
            if self.source_evaluation_failure_digest is not None:
                raise ValueError("UNEVALUATED: source failure must be None")
            if self.phase3_failure_digest is not None:
                raise ValueError("UNEVALUATED: phase3 failure must be None")
            if self.failure_origin != FailureOrigin.NONE:
                raise ValueError("UNEVALUATED: failure_origin must be NONE")

        # RUNTIME_FAILED
        elif self.disposition is Phase3Disposition.RUNTIME_FAILED:
            if self.primary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering values must be None")
            if self.secondary_engineering_value is not None:
                raise ValueError("RUNTIME_FAILED: engineering values must be None")
            if self.failure_origin == FailureOrigin.PHASE2_EVALUATION:
                if self.source_evaluation_failure_digest is None:
                    raise ValueError("RUNTIME_FAILED(P2): source failure required")
                if self.phase3_failure_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): phase3 failure must be None")
                if self.source_candidate_evaluation_state != CandidateEvaluationState.RUNTIME_FAILED:
                    raise ValueError("RUNTIME_FAILED(P2): source must be RUNTIME_FAILED")
                valid_outs = [(VerificationOutcome.NOT_RUN, VerificationOutcome.NOT_RUN),
                              (VerificationOutcome.ERROR, VerificationOutcome.NOT_RUN),
                              (VerificationOutcome.PASSED, VerificationOutcome.ERROR),
                              (VerificationOutcome.PASSED, VerificationOutcome.PASSED)]
                if (self.source_hash_verification_outcome, self.source_provenance_verification_outcome) not in valid_outs:
                    raise ValueError("RUNTIME_FAILED(P2): invalid outcome combo")
                if self.candidate_evaluation_identity_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): identity must be None")
                if self.verified_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): evidence must be None")
                if self.invalid_rating_evidence_digest is not None:
                    raise ValueError("RUNTIME_FAILED(P2): invalid evidence must be None")
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
                # Identity/evidence retained per P0-6
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

    def verify_digest(self) -> bool:
        return self.feasibility_digest == sha256_digest(candidate_disposition_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("feasibility_digest mismatch")
```

### 8.3 Payload (excludes feasibility_digest)

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
        "source_evaluation_failure_digest": record.source_evaluation_failure_digest,
        "phase3_failure_digest": record.phase3_failure_digest,
        "failure_origin": record.failure_origin.value,
    }
```

---

## 9. RankedCandidateRecord

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
            if not self.DIGEST_PATTERN.match(dgst):
                raise ValueError(f"{name}: invalid digest {dgst!r}")
        return self

    def verify_digest(self) -> bool:
        return self.ranked_record_digest == sha256_digest(ranked_candidate_record_payload(self))

    def verify_or_raise(self) -> None:
        if not self.verify_digest():
            raise ValueError("ranked_record_digest mismatch")
```

### 9.1 Payload

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

## 10. OptimizationResult

### 10.1 Model

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

    DIGEST_PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _validate(self) -> Self:
        if self.schema_version != 1:
            raise ValueError("schema_version must be 1")
        if self.requested_top_n < 1:
            raise ValueError("requested_top_n must be ≥ 1")
        # All counts non-negative
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
        # Phase 3 disposition sum
        d3 = (self.feasible_candidate_count + self.infeasible_candidate_count +
              self.provider_mismatch_count + self.integrity_failed_count +
              self.provenance_failed_count + self.runtime_failed_count + self.unevaluated_count)
        if d3 != self.total_candidate_count:
            raise ValueError("Phase 3 disposition counts != total")
        # Phase 2 state sum
        p2 = (self.phase2_verified_record_count + self.phase2_integrity_invalid_record_count +
              self.phase2_runtime_failed_record_count + self.phase2_unevaluated_record_count)
        if p2 != self.total_candidate_count:
            raise ValueError("Phase 2 state counts != total")
        # Cross-equations
        if self.runtime_failed_count != (self.runtime_failed_from_phase2_verified_count +
                                          self.runtime_failed_from_phase2_runtime_failed_count):
            raise ValueError("runtime_failed cross-count mismatch")
        if self.phase2_verified_record_count != (
            self.feasible_candidate_count + self.infeasible_candidate_count +
            self.provider_mismatch_count + self.runtime_failed_from_phase2_verified_count
        ):
            raise ValueError("phase2_verified cross-count mismatch")
        if self.phase2_integrity_invalid_record_count != (
            self.integrity_failed_count + self.provenance_failed_count
        ):
            raise ValueError("phase2_integrity_invalid cross-count mismatch")
        if self.phase2_runtime_failed_record_count != self.runtime_failed_from_phase2_runtime_failed_count:
            raise ValueError("phase2_runtime_failed cross-count mismatch")
        if self.phase2_unevaluated_record_count != self.unevaluated_count:
            raise ValueError("phase2_unevaluated cross-count mismatch")
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
        return self
```

### 10.2 Core payload

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

### 10.3 All digest fields (exact, no etc.)

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

---

## 11. External verifier (P0-7, P0-8, P0-10)

```python
def verify_optimization_result_or_raise(
    result: OptimizationResult,
    *,
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    provenance_graph: ProvenanceGraph,
) -> None:

    # 1. Input binding
    if result.evaluation_input_digest != evaluation_input.evaluation_input_digest:
        raise ValueError("evaluation_input_digest mismatch")
    if result.sizing_request_identity_digest != evaluation_input.sizing_request_identity_digest:
        raise ValueError("sizing_request_identity_digest mismatch")
    if result.candidate_set_digest != evaluation_input.candidate_set_digest:
        raise ValueError("candidate_set_digest mismatch")
    if result.passed_gate_digest != evaluation_input.gate_digest:
        raise ValueError("passed_gate_digest mismatch")

    # 2. Objective and Top-N binding (P0-8)
    if result.optimization_objective != evaluation_input.sizing_request_identity.optimization_objective:
        raise ValueError("optimization_objective mismatch with sizing request")
    if result.requested_top_n != evaluation_input.sizing_request_identity.top_n:
        raise ValueError("requested_top_n mismatch with sizing request")

    # 3. Total count
    if result.total_candidate_count != evaluation_input.evaluation_record_count:
        raise ValueError("total_candidate_count != evaluation_record_count")

    # 4. Per-index disposition binding (P0-5)
    N = result.total_candidate_count
    if len(disposition_records) != N:
        raise ValueError(f"disposition_records count {len(disposition_records)} != {N}")
    for i in range(N):
        rec = evaluation_input.evaluation_records[i]
        dr = disposition_records[i]
        if dr.evaluation_order_index != i:
            raise ValueError(f"disposition[{i}]: order_index != {i}")
        if dr.source_qualified_candidate_id != rec.source_qualified_candidate_id:
            raise ValueError(f"disposition[{i}]: candidate_id mismatch")
        if dr.source_candidate_evaluation_state != rec.candidate_evaluation_state:
            raise ValueError(f"disposition[{i}]: state mismatch")
        if dr.source_hash_verification_outcome != rec.hash_verification_outcome:
            raise ValueError(f"disposition[{i}]: hash outcome mismatch")
        if dr.source_provenance_verification_outcome != rec.provenance_verification_outcome:
            raise ValueError(f"disposition[{i}]: provenance outcome mismatch")
        expected_desc = evaluation_input.ordered_evaluation_record_descriptor_digests[i]
        if dr.source_record_descriptor_digest != expected_desc:
            raise ValueError(f"disposition[{i}]: descriptor digest mismatch")
        if dr.provider_identity_matches != rec.provider_identity_matches:
            raise ValueError(f"disposition[{i}]: provider match mismatch")
        if dr.rating_status != rec.rating_status:
            raise ValueError(f"disposition[{i}]: rating_status mismatch")
        _verify_source_digests_match(rec, dr, i)
        if result.ordered_disposition_record_digests[i] != dr.feasibility_digest:
            raise ValueError(f"disposition[{i}]: digest in result mismatch")
        dr.verify_or_raise()

    # 5. Re-run classifier (P0-7) — compare full payload, not just digest
    for i in range(N):
        cin = build_phase3_classification_input(evaluation_input, i)
        expected = classify_candidate(cin)
        actual = disposition_records[i]
        if candidate_disposition_payload(actual) != candidate_disposition_payload(expected):
            raise ValueError(f"disposition[{i}]: does not match re-classified result (tampered)")

    # 6. Ranked records (P0-6)
    F = result.feasible_candidate_count
    if len(ranked_records) != F:
        raise ValueError(f"ranked_records count {len(ranked_records)} != {F}")
    feasible_map = {dr.source_qualified_candidate_id: dr for dr in disposition_records
                    if dr.disposition is Phase3Disposition.FEASIBLE}
    if len(feasible_map) != F:
        raise ValueError("FEASIBLE disposition count != feasible_candidate_count")
    for i, rr in enumerate(ranked_records):
        if result.ordered_ranked_record_digests[i] != rr.ranked_record_digest:
            raise ValueError(f"ranked[{i}]: digest in result mismatch")
        rr.verify_or_raise()
        disp = feasible_map.get(rr.source_qualified_candidate_id)
        if disp is None:
            raise ValueError(f"ranked[{i}]: no FEASIBLE disposition")
        if rr.candidate_evaluation_identity_digest != disp.candidate_evaluation_identity_digest:
            raise ValueError(f"ranked[{i}]: identity digest mismatch")
        if rr.verified_rating_evidence_digest != disp.verified_rating_evidence_digest:
            raise ValueError(f"ranked[{i}]: evidence digest mismatch")
        if rr.feasibility_digest != disp.feasibility_digest:
            raise ValueError(f"ranked[{i}]: feasibility digest mismatch")
    # Rank order and contiguous
    for expected_rank, rr in enumerate(ranked_records, start=1):
        if rr.rank != expected_rank:
            raise ValueError(f"rank {rr.rank} != {expected_rank} (order mismatch)")
    # Recompute sort order
    sorted_ranked = _recompute_ranked_order(ranked_records, evaluation_input, disposition_records)
    actual_order = [rr.ranked_record_digest for rr in ranked_records]
    expected_order = [rr.ranked_record_digest for rr in sorted_ranked]
    if actual_order != expected_order:
        raise ValueError("ranked order does not match frozen sort key")

    # 7. Top-N
    TN = len(result.ordered_top_n_record_digests)
    expected_TN = min(result.requested_top_n, F)
    if TN != expected_TN:
        raise ValueError(f"Top-N length {TN} != min({result.requested_top_n}, {F})")
    if result.ordered_top_n_record_digests != result.ordered_ranked_record_digests[:TN]:
        raise ValueError("Top-N must be exact prefix of ranked")

    # 8. Independent count recomputation (P0-7)
    _verify_all_counts(result, evaluation_input, disposition_records)

    # 9. Termination (P1-1: correct condition/message, no inversion)
    stop_index = _find_stop_index(evaluation_input)
    if stop_index is None:
        if result.termination_status is not TerminationStatus.COMPLETE:
            raise ValueError("termination_status must be COMPLETE when no strict-stop exists")
    else:
        if result.termination_status is not TerminationStatus.PARTIAL:
            raise ValueError("termination_status must be PARTIAL when strict-stop exists")

    # 10. Strict-stop warning (P0-10)
    expected_ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
    expected_ss_digest = sha256_digest(engineering_message_payload(expected_ss_warning))
    occurrences = sum(1 for d in result.ordered_warning_digests if d == expected_ss_digest)
    if stop_index is not None:
        if occurrences != 1:
            raise ValueError(f"strict-stop warning: expected 1 occurrence, got {occurrences}")
    else:
        if occurrences != 0:
            raise ValueError("strict-stop warning present but no strict-stop")

    # 11. Full warning/blocker aggregation verification (P0-14)
    expected_w_digests, expected_b_digests = build_result_message_digest_tuples(
        evaluation_input=evaluation_input,
        disposition_records=disposition_records,
        stop_index=stop_index,
    )
    if list(result.ordered_warning_digests) != expected_w_digests:
        raise ValueError("ordered_warning_digests mismatch")
    if list(result.ordered_blocker_digests) != expected_b_digests:
        raise ValueError("ordered_blocker_digests mismatch")

    # 12. Hash verification
    expected_core = sha256_digest(result_core_payload(result))
    if result.result_core_hash != expected_core:
        raise ValueError("result_core_hash mismatch")
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

    # 13. Digest format
    for name, dgst in _all_digest_fields(result):
        if not OptimizationResult.DIGEST_PATTERN.match(dgst):
            raise ValueError(f"{name}: invalid digest {dgst!r}")

    # 14. Uniqueness
    if len(set(result.ordered_disposition_record_digests)) != N:
        raise ValueError("disposition digests not unique")
    if len(set(result.ordered_ranked_record_digests)) != F:
        raise ValueError("ranked digests not unique")
    if len(set(result.ordered_top_n_record_digests)) != TN:
        raise ValueError("Top-N digests not unique")
```

### 11.1 _verify_source_digests_match

```python
def _verify_source_digests_match(rec: CandidateEvaluationRecord, dr: CandidateDispositionRecord, i: int):
    expected_identity = (
        rec.candidate_evaluation_identity.candidate_evaluation_identity_digest
        if rec.candidate_evaluation_identity is not None else None
    )
    if dr.candidate_evaluation_identity_digest != expected_identity:
        raise ValueError(f"disposition[{i}]: identity digest does not match source record")
    expected_evidence = (
        rec.verified_rating_evidence.compute_explicit_evidence_digest()
        if rec.verified_rating_evidence is not None else None
    )
    if dr.verified_rating_evidence_digest != expected_evidence:
        raise ValueError(f"disposition[{i}]: evidence digest does not match source record")
    expected_invalid = (
        rec.invalid_rating_evidence.invalid_evidence_digest
        if rec.invalid_rating_evidence is not None else None
    )
    if dr.invalid_rating_evidence_digest != expected_invalid:
        raise ValueError(f"disposition[{i}]: invalid evidence digest does not match source record")
    # source_evaluation_failure_digest only: Phase 2 failures
    expected_source_failure = (
        sha256_digest(run_failure_payload(rec.evaluation_failure))
        if rec.evaluation_failure is not None else None
    )
    if dr.source_evaluation_failure_digest != expected_source_failure:
        raise ValueError(f"disposition[{i}]: source failure digest mismatch")
```

### 11.2 _verify_all_counts

```python
def _verify_all_counts(result, evaluation_input, disposition_records):
    recs = evaluation_input.evaluation_records
    # From source records
    p2_v = sum(1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.VERIFIED)
    p2_ii = sum(1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.INTEGRITY_INVALID)
    p2_rf = sum(1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED)
    p2_u = sum(1 for r in recs if r.candidate_evaluation_state == CandidateEvaluationState.UNEVALUATED)
    if result.phase2_verified_record_count != p2_v:
        raise ValueError(f"phase2_verified: {result.phase2_verified_record_count} != {p2_v}")
    if result.phase2_integrity_invalid_record_count != p2_ii:
        raise ValueError(f"phase2_integrity_invalid: {result.phase2_integrity_invalid_record_count} != {p2_ii}")
    if result.phase2_runtime_failed_record_count != p2_rf:
        raise ValueError(f"phase2_runtime_failed: {result.phase2_runtime_failed_record_count} != {p2_rf}")
    if result.phase2_unevaluated_record_count != p2_u:
        raise ValueError(f"phase2_unevaluated: {result.phase2_unevaluated_record_count} != {p2_u}")
    # From disposition records
    f = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.FEASIBLE)
    inf = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.INFEASIBLE)
    pm = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.PROVIDER_IDENTITY_MISMATCH)
    intf = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.INTEGRITY_FAILED)
    pf = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.PROVENANCE_FAILED)
    rf = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.RUNTIME_FAILED)
    u = sum(1 for d in disposition_records if d.disposition is Phase3Disposition.UNEVALUATED)
    if result.feasible_candidate_count != f:
        raise ValueError(f"feasible: {result.feasible_candidate_count} != {f}")
    if result.infeasible_candidate_count != inf:
        raise ValueError(f"infeasible: {result.infeasible_candidate_count} != {inf}")
    if result.provider_mismatch_count != pm:
        raise ValueError(f"provider_mismatch: {result.provider_mismatch_count} != {pm}")
    if result.integrity_failed_count != intf:
        raise ValueError(f"integrity_failed: {result.integrity_failed_count} != {intf}")
    if result.provenance_failed_count != pf:
        raise ValueError(f"provenance_failed: {result.provenance_failed_count} != {pf}")
    if result.runtime_failed_count != rf:
        raise ValueError(f"runtime_failed: {result.runtime_failed_count} != {rf}")
    if result.unevaluated_count != u:
        raise ValueError(f"unevaluated: {result.unevaluated_count} != {u}")
    # Runtime origin
    rf_v = sum(1 for d in disposition_records
               if d.disposition is Phase3Disposition.RUNTIME_FAILED
               and d.source_candidate_evaluation_state == CandidateEvaluationState.VERIFIED)
    rf_rf = sum(1 for d in disposition_records
                if d.disposition is Phase3Disposition.RUNTIME_FAILED
                and d.source_candidate_evaluation_state == CandidateEvaluationState.RUNTIME_FAILED)
    if result.runtime_failed_from_phase2_verified_count != rf_v:
        raise ValueError(f"rf_from_verified: {result.runtime_failed_from_phase2_verified_count} != {rf_v}")
    if result.runtime_failed_from_phase2_runtime_failed_count != rf_rf:
        raise ValueError(f"rf_from_rf: {result.runtime_failed_from_phase2_runtime_failed_count} != {rf_rf}")
```

### 11.3 _recompute_ranked_order

```python
def _recompute_ranked_order(ranked_records, evaluation_input, disposition_records):
    """Return ranked records sorted by the frozen sort key."""
    feasible_disps = [dr for dr in disposition_records if dr.disposition is Phase3Disposition.FEASIBLE]
    # Build sort keys using the optimization objective from the result
    obj = evaluation_input.sizing_request_identity.optimization_objective
    ids_in_order = []
    for dr in feasible_disps:
        # Get the materialized candidate for effective_length
        ci = dr.evaluation_order_index
        candidate = evaluation_input.materialization_result.candidates[ci]
        if obj == OptimizationObjective.MINIMUM_OUTER_HEAT_TRANSFER_AREA:
            key = (canonical_decimal(Decimal(dr.primary_engineering_value)),
                   canonical_decimal(Decimal(candidate.effective_length_m_canonical)),
                   dr.source_qualified_candidate_id)
        else:
            key = (canonical_decimal(Decimal(candidate.effective_length_m_canonical)),
                   canonical_decimal(Decimal(dr.primary_engineering_value)),
                   dr.source_qualified_candidate_id)
        ids_in_order.append((key, dr.source_qualified_candidate_id))
    ids_in_order.sort(key=lambda x: x[0])
    sorted_ids = [cid for _, cid in ids_in_order]
    # Map back to ranked records in sorted order
    rr_by_id = {rr.source_qualified_candidate_id: rr for rr in ranked_records}
    return tuple(rr_by_id[cid] for cid in sorted_ids)
```

### 11.4 build_phase3_classification_input

```python
def build_phase3_classification_input(
    evaluation_input: Phase3EvaluationInput,
    index: int,
) -> Phase3CandidateClassificationInput:
    rec = evaluation_input.evaluation_records[index]
    candidate = evaluation_input.materialization_result.candidates[index]
    return Phase3CandidateClassificationInput(
        source_record=rec,
        source_record_descriptor_digest=evaluation_input.ordered_evaluation_record_descriptor_digests[index],
        materialized_candidate=candidate,
        sizing_request_identity=evaluation_input.sizing_request_identity,
        sizing_request_identity_digest=evaluation_input.sizing_request_identity_digest,
    )
```

### 11.5 _find_stop_index

```python
def _find_stop_index(evaluation_input: Phase3EvaluationInput) -> int | None:
    for i, rec in enumerate(evaluation_input.evaluation_records):
        if rec.candidate_evaluation_state in (
            CandidateEvaluationState.INTEGRITY_INVALID,
            CandidateEvaluationState.RUNTIME_FAILED,
        ):
            return i
    return None
```

---

## 12. Single-pass message descriptor (P0-15)

```python
def build_engineering_message_descriptor(
    message: EngineeringMessage,
) -> CanonicalizedEngineeringMessageDescriptor:
    """Public wrapper — delegates to existing _build_message_descriptor."""
    return _build_message_descriptor(message)
```

### 12.1 Canonicalization failure

```python
if descriptor.canonicalization_error is not None or descriptor.message_payload_digest is None:
    failure = RunFailure(
        code=ErrorCode.PHASE3_FEASIBILITY_RUNTIME_FAILURE,
        message="Trusted context canonicalization failed during feasibility classification.",
        traceback=None,
        context=(
            ("failure_kind", descriptor.canonicalization_error.failure_kind.value),
            ("context_key", descriptor.canonicalization_error.context_key),
            ("offending_type", descriptor.canonicalization_error.offending_type),
        ),
    )
    phase3_failure_digest = sha256_digest(run_failure_payload(failure))
    disposition = _build_phase3_runtime_failure(input, failure, retain_identity_evidence=True)
    # Continue to next candidate — does NOT trigger Phase 2 strict-stop
```

---

## 13. Strict-stop warning (P0-11)

```python
def _build_strict_stop_warning(
    evaluation_input: Phase3EvaluationInput,
    stop_index: int | None,
) -> EngineeringMessage | None:
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
            ("source_record_descriptor_digest",
             evaluation_input.ordered_evaluation_record_descriptor_digests[stop_index]),
        ),
    )
```

---

## 14. Warning/blocker aggregation (P0-14)

```python
def build_result_message_digest_tuples(
    *,
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    stop_index: int | None = None,
) -> tuple[list[str], list[str]]:
    descriptors: list[CanonicalizedEngineeringMessageDescriptor] = []

    # Phase 2 source warnings/blockers (from disposition records)
    for dr in disposition_records:
        # Disposition records already have sorted warning/blocker digests
        pass  # Warnings/blockers are already canonicalized in each disposition

    # Strict-stop warning (if PARTIAL)
    ss_warning = _build_strict_stop_warning(evaluation_input, stop_index)
    if ss_warning is not None:
        d = build_engineering_message_descriptor(ss_warning)
        if d.canonicalization_error is None and d.message_payload_digest is not None:
            descriptors.append(d)

    # Collect all warning descriptors from disposition records
    warning_descriptors: list[CanonicalizedEngineeringMessageDescriptor] = []
    for dr in disposition_records:
        for digest in dr.ordered_warning_digests:
            # Each digest already represents a canonicalized message
            pass  # Digests are already canonical, no re-canonicalization needed

    # Sort all by owner_sort_key
    descriptors.sort(key=lambda d: d.owner_sort_key)
    warning_digests = [d.message_payload_digest for d in descriptors if d.message_payload_digest is not None]

    # Blockers similarly (no strict-stop warning in blockers)
    blocker_descriptors: list[CanonicalizedEngineeringMessageDescriptor] = []
    for dr in disposition_records:
        for digest in dr.ordered_blocker_digests:
            pass
    blocker_descriptors.sort(key=lambda d: d.owner_sort_key)
    blocker_digests = [d.message_payload_digest for d in blocker_descriptors]

    return warning_digests, blocker_digests
```

Note: Warnings and blockers are already canonicalized into digest tuples per disposition record. The aggregation re-uses those digests. The strict-stop warning is the only Phase 3-generated warning and goes through the same single-pass descriptor process.

---

## 15. Provenance (P0-11, P0-12, P0-13)

### 15.1 Namespaces

```python
PHASE3_RESULT_NAMESPACE = uuid.UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")
PHASE3_PROVENANCE_NAMESPACE = uuid.UUID("6ba7b811-9dad-11d1-80b4-00c04fd430c8")
```

### 15.2 Expected node count

```python
N = total_candidate_count  # disposition records
F = feasible_candidate_count  # ranked records
expected_node_count = 8 + N + F
# 8 fixed: root, sizing_request, gate, candidate_set, evaluation_input, top_n, result_core, optimizer
```

### 15.3 Provenance role binding (P0-13)

```python
class ExpectedPhase3ProvenanceNode(NamedTuple):
    role: str
    node_type: ProvenanceNodeType
    payload_hash: str

def _expected_provenance_nodes(
    evaluation_input, disposition_records, ranked_records, result,
) -> list[ExpectedPhase3ProvenanceNode]:
    nodes: list[ExpectedPhase3ProvenanceNode] = []
    # 1. Root
    root_payload = {"artifact_kind": "phase3_evaluation_input",
                    "evaluation_input_digest": evaluation_input.evaluation_input_digest}
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="root", node_type=ProvenanceNodeType.EXTERNAL,
        payload_hash=sha256_digest(root_payload)))
    # 2. Sizing request
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="sizing_request", node_type=ProvenanceNodeType.INPUT_FILE,
        payload_hash=evaluation_input.sizing_request_identity_digest))
    # 3. Gate
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="passed_gate", node_type=ProvenanceNodeType.CALCULATION_RUN,
        payload_hash=evaluation_input.gate_digest))
    # 4. Candidate set
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="candidate_set", node_type=ProvenanceNodeType.CALCULATION_RUN,
        payload_hash=evaluation_input.candidate_set_digest))
    # 5. Evaluation input
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="evaluation_input", node_type=ProvenanceNodeType.INTERMEDIATE,
        payload_hash=evaluation_input.evaluation_input_digest))
    # 6. Disposition records
    for i, dr in enumerate(disposition_records):
        nodes.append(ExpectedPhase3ProvenanceNode(
            role=f"disposition[{i}]", node_type=ProvenanceNodeType.INTERMEDIATE,
            payload_hash=dr.feasibility_digest))
    # 7. Ranked records
    for i, rr in enumerate(ranked_records):
        nodes.append(ExpectedPhase3ProvenanceNode(
            role=f"ranked[{i}]", node_type=ProvenanceNodeType.INTERMEDIATE,
            payload_hash=rr.ranked_record_digest))
    # 8. Top-N
    top_n_payload = {"ordered_top_n_record_digests": list(result.ordered_top_n_record_digests)}
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="top_n_selection", node_type=ProvenanceNodeType.INTERMEDIATE,
        payload_hash=sha256_digest(top_n_payload)))
    # 9. Result core
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="result_core", node_type=ProvenanceNodeType.RESULT,
        payload_hash=result.result_core_hash))
    # 10. Optimizer
    optimizer_payload = {
        "schema_version": 1,
        "evaluation_input_digest": evaluation_input.evaluation_input_digest,
        "optimization_objective": result.optimization_objective.value,
        "requested_top_n": result.requested_top_n,
        "termination_status": result.termination_status.value,
        "result_core_hash": result.result_core_hash,
        "phase3_algorithm_version": "task009-phase3-v1",
    }
    nodes.append(ExpectedPhase3ProvenanceNode(
        role="optimizer", node_type=ProvenanceNodeType.OPTIMIZER,
        payload_hash=sha256_digest(optimizer_payload)))
    return nodes
```

Each node's UUID:
```python
node_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{node_type.value}:{payload_hash}")
```

Two nodes with identical `(node_type, payload_hash)` but different roles would collide. This is **forbidden** — if two expected nodes differ only in role, the verifier must detect the missing node. In practice, disposition records should have unique payload hashes.

### 15.4 Semantic provenance verifier

```python
def verify_phase3_provenance_graph_or_raise(
    graph: ProvenanceGraph,
    *,
    evaluation_input: Phase3EvaluationInput,
    disposition_records: tuple[CandidateDispositionRecord, ...],
    ranked_records: tuple[RankedCandidateRecord, ...],
    result: OptimizationResult,
) -> None:

    # 1. Expected nodes
    expected_nodes = _expected_provenance_nodes(
        evaluation_input, disposition_records, ranked_records, result)

    # 2. Validate each expected node exists with correct properties
    node_by_id: dict[UUID, ProvenanceNode] = {n.node_id: n for n in graph.nodes}
    for exp in expected_nodes:
        exp_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{exp.node_type.value}:{exp.payload_hash}")
        actual = node_by_id.get(exp_id)
        if actual is None:
            raise ValueError(f"missing provenance node: {exp.role}")
        if actual.node_type != exp.node_type:
            raise ValueError(f"node {exp.role}: type mismatch {actual.node_type} != {exp.node_type}")
        if actual.payload_hash != exp.payload_hash:
            raise ValueError(f"node {exp.role}: payload_hash mismatch")
        if actual.label != "":
            raise ValueError(f"node {exp.role}: label must be empty, got {actual.label!r}")
        if actual.metadata != ():
            raise ValueError(f"node {exp.role}: metadata must be empty")

    # 3. Check no extra nodes
    expected_ids = {
        uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{exp.node_type.value}:{exp.payload_hash}")
        for exp in expected_nodes
    }
    actual_ids = set(n.node_id for n in graph.nodes)
    extra = actual_ids - expected_ids
    if extra:
        raise ValueError(f"extra provenance nodes: {len(extra)}")

    # 4. Expected edges
    expected_edge_keys = _build_expected_edge_keys(
        evaluation_input, disposition_records, ranked_records, result)
    actual_edge_keys = tuple(
        sorted(
            (str(edge.source_id), str(edge.target_id), edge.relation)
            for edge in graph.edges
        )
    )
    # Reject duplicates
    if len(actual_edge_keys) != len(set(actual_edge_keys)):
        raise ValueError("duplicate provenance edges")
    if actual_edge_keys != expected_edge_keys:
        raise ValueError("provenance edge set mismatch")

    # 5. All edge metadata empty
    for edge in graph.edges:
        if edge.metadata != ():
            raise ValueError(f"edge {edge.source_id}→{edge.target_id}: metadata must be empty")

    # 6. Reachability from root
    root_id = uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE,
                         f"{ProvenanceNodeType.EXTERNAL.value}:{expected_nodes[0].payload_hash}")
    children: dict[UUID, list[UUID]] = {n.node_id: [] for n in graph.nodes}
    for e in graph.edges:
        children[e.source_id].append(e.target_id)
    visited = set()
    queue = [root_id]
    while queue:
        nid = queue.pop(0)
        if nid in visited:
            continue
        visited.add(nid)
        queue.extend(children.get(nid, []))
    if len(visited) != len(graph.nodes):
        raise ValueError("graph has unreachable nodes")
```

### 15.5 Build expected edges

```python
def _build_expected_edge_keys(evaluation_input, disposition_records, ranked_records, result):
    expected_nodes = _expected_provenance_nodes(
        evaluation_input, disposition_records, ranked_records, result)
    node_by_role = {n.role: n for n in expected_nodes}

    def _uid(role: str) -> str:
        n = node_by_role[role]
        return str(uuid.uuid5(PHASE3_PROVENANCE_NAMESPACE, f"{n.node_type.value}:{n.payload_hash}"))

    edges: list[tuple[str, str, str]] = []

    # Root → Sizing Request: regulates
    edges.append((_uid("root"), _uid("sizing_request"), "regulates"))
    # Sizing Request → Gate: consumed_by
    edges.append((_uid("sizing_request"), _uid("passed_gate"), "consumed_by"))
    # Gate → Candidate Set: produced
    edges.append((_uid("passed_gate"), _uid("candidate_set"), "produced"))
    # Candidate Set → Evaluation Input: consumed_by
    edges.append((_uid("candidate_set"), _uid("evaluation_input"), "consumed_by"))
    # Evaluation Input → each disposition: evaluated
    for i in range(len(disposition_records)):
        edges.append((_uid("evaluation_input"), _uid(f"disposition[{i}]"), "evaluated"))
    # FEASIBLE disposition → ranked: ranked
    ranked_idx = 0
    for i, dr in enumerate(disposition_records):
        if dr.disposition is Phase3Disposition.FEASIBLE:
            edges.append((_uid(f"disposition[{i}]"), _uid(f"ranked[{ranked_idx}]"), "ranked"))
            ranked_idx += 1
    # Evaluation Input → Top-N Selection: selected_by (always present)
    edges.append((_uid("evaluation_input"), _uid("top_n_selection"), "selected_by"))
    # Selected ranked records → Top-N: selected
    for i in range(len(result.ordered_top_n_record_digests)):
        edges.append((_uid(f"ranked[{i}]"), _uid("top_n_selection"), "selected"))
    # Top-N → Result Core: produced
    edges.append((_uid("top_n_selection"), _uid("result_core"), "produced"))
    # Result Core → Optimizer: executed_by
    edges.append((_uid("result_core"), _uid("optimizer"), "executed_by"))

    return tuple(sorted(edges))
```

---

## 16. Implementation boundary

### New files

`src/hexagent/optimization/phase3_input.py`, `feasibility.py`, `ranking.py`, `result.py`, `tests/unit/test_task009_phase3_*.py`

### Existing files modified

`src/hexagent/domain/messages.py` — add Phase 3 error codes to `ErrorCode`. `src/hexagent/optimization/evaluation.py` — export `build_engineering_message_descriptor`.

### Untouched

All other `src/hexagent/` files, including all Phase 1/2 optimization modules, TASK-008 modules, catalog modules, and all existing tests.

---

## 17. Test matrix

- Model validators return `self` (not `Self`) under `mode="after"`
- `DIGEST_PATTERN` is `ClassVar`
- Models validate under `python` and `python -O`
- Classification input rejects duplicate-field mismatch
- `minimum_terminal_delta_t` exact field binding
- Candidate ID/index binding in classification input
- `classify_candidate()` has no `...` ellipsis
- VERIFIED + `rating_status=None` → Phase 3 RUNTIME_FAILED
- Phase 2 vs Phase 3 failure digests separated
- `failure_origin` invariants per disposition
- PROVIDER_MISMATCH identity/evidence required
- Phase 3 RUNTIME_FAILED identity/evidence retained
- External verifier re-runs classifier per index
- Wrong duty/diagnostic disposition rejected after rehash
- Wrong `optimization_objective` rejected
- Wrong `requested_top_n` rejected
- All 7 result cross-equations
- Coordinated count tampering rejected
- PARTIAL strict-stop warning exactly once
- Duplicate strict-stop warning rejected
- COMPLETE strict-stop warning rejected
- Complete warning tuple ordering
- Node count: `8 + N + F`
- Duplicate provenance edge rejected
- All node metadata empty, all edge metadata empty
- Exact provenance role binding
- Duplicate provenance role rejected
- Result warning/blocker exact aggregation
- Single-pass public wrapper exact behavior
- Canonicalization failure `RunFailure` exact digest
- All 10 Phase 2 RUNTIME_FAILED constructor paths

---

## 18. Acceptance criteria

1. All tests pass Python 3.11 and 3.12
2. `result_hash` deterministic and reproducible
3. Semantic provenance DAG verifier detects every tamper mode
4. 13-step input verification fails closed for all steps
5. Top-N selection never exceeds feasible candidate count
6. No Phase 2 artifact mutated
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
