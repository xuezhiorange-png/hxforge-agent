# TASK-009 Phase 3 — Deterministic feasibility, ranking, and Top-N contract

**Status:** DRAFT — NOT AUTHORIZED FOR IMPLEMENTATION
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-008, TASK-009 Phase 2
**Design Review:** PENDING

---

## 1. Scope

Phase 3 completes the candidate optimization pipeline by consuming the Phase 2 validated `CandidateEvaluationRecord` / trusted evidence artifacts and producing a deterministic, provenance-tracked `OptimizationResult`.

Phase 3 is responsible for:

- Deterministic feasibility classification
- Deterministic ranking with explicit tie-breaking
- Deterministic Top-N result construction
- Result-level integrity and provenance
- Fail-closed semantics for all verification failures

Phase 3 does **not** re-execute candidate generation, materialization, or thermal rating.

---

## 2. Non-goals

The following are explicitly out of scope for Phase 3:

- TASK-010 (versioned API and traceable report)
- C4 (cost constraint)
- Pressure-drop calculation
- Pressure-drop constraint
- Velocity constraint
- Pump power estimation
- Economic optimization (life-cycle cost, operating cost)
- Multi-objective Pareto optimization
- Stochastic or heuristic optimization (genetic algorithms, simulated annealing, random search)
- Machine-learning ranking or scoring
- New heat-transfer correlations
- New rating solver logic
- Candidate generation changes
- Catalog schema changes
- Phase 2 artifact mutation
- Any TASK-010 concerns

---

## 3. Upstream frozen dependencies

Phase 3 accepts as input only artifacts that have completed Phase 2 validation. The following identities and digests must be available and verified before Phase 3 execution begins:

| Input Artifact | Type | Description |
|---|---|---|
| `sizing_request_identity_digest` | `str` (SHA-256 hex) | Identity of the original sizing request |
| `passed_sizing_gate_identity` | `str` (SHA-256 hex) | Identity of the gate that passed the sizing request |
| `materialized_candidate_set_digest` | `str` (SHA-256 hex) | Digest of the full materialized candidate set |
| `candidate_evaluation_identities` | `list[str]` | Per-candidate evaluation identity digests (order = source-qualified candidate ID order) |
| `verified_rating_evidence_digests` | `list[str]` | Per-candidate verified rating evidence digests (parallel to candidate IDs) |
| `evaluation_batch_digest` | `str` (SHA-256 hex) | Digest covering all candidate evaluation identities + evidence digests |
| `ordered_source_qualified_candidate_ids` | `list[str]` | Deterministically ordered candidate IDs (insertion-order independent) |
| `candidate_evaluation_states` | `list[EvaluationState]` | Per-candidate evaluation state: `EVALUATED`, `RUNTIME_FAILED`, `UNEVALUATED` |
| `hash_verification_outcomes` | `list[bool]` | Per-candidate hash verification outcome |
| `provenance_verification_outcomes` | `list[bool]` | Per-candidate provenance verification outcome |
| `complete_evaluation_record_count` | `int` | Total number of evaluation records |

No bare candidate or bare rating result may bypass Phase 2 verification.

---

## 4. Typed data model

### 4.1 `FeasibilityStatus` (enum)

```python
class FeasibilityStatus(str, enum.Enum):
    FEASIBLE = "feasible"
    INFEASIBLE = "infeasible"
    UNEVALUATED = "unevaluated"
    RUNTIME_FAILED = "runtime_failed"
    INTEGRITY_FAILED = "integrity_failed"
    PROVENANCE_FAILED = "provenance_failed"
```

### 4.2 `FeasibilitySummary` (frozen dataclass)

```python
@dataclass(frozen=True)
class FeasibilitySummary:
    status: FeasibilityStatus
    reason: str | None               # Human-readable reason if infeasible; None if feasible
    diagnostic_key: str | None       # Machine-readable diagnostic key if infeasible
    blocking_rating_warnings: tuple[str, ...]  # Warnings that blocked feasibility
    all_rating_warnings: tuple[str, ...]       # All warnings (informational even if feasible)
```

### 4.3 `RankedCandidateRecord` (frozen dataclass)

```python
@dataclass(frozen=True)
class RankedCandidateRecord:
    rank: int                                  # 1-based rank
    candidate_id: str                          # Source-qualified candidate ID
    candidate_evaluation_identity: str         # SHA-256 identity
    verified_rating_evidence_digest: str       # SHA-256 digest from Phase 2
    feasibility: FeasibilitySummary
    engineering_objective: Decimal | None      # None if infeasible/unavailable
    tie_break_fields: tuple[Decimal | None, ...]  # Secondary sort fields for determinism
```

### 4.4 `OptimizationResult` (frozen dataclass)

```python
@dataclass(frozen=True)
class OptimizationResult:
    schema_version: int
    optimization_result_id: str                # SHA-256 of payload
    sizing_request_identity_digest: str
    materialized_candidate_set_digest: str
    evaluation_batch_digest: str
    optimization_objective: str                # e.g. "MINIMUM_OUTER_HEAT_TRANSFER_AREA"
    requested_top_n: int
    total_candidate_count: int
    verified_candidate_count: int
    feasible_candidate_count: int
    infeasible_candidate_count: int
    failed_candidate_count: int
    ordered_ranked_candidate_identities: tuple[str, ...]  # All ranked candidate IDs
    ordered_top_n_candidate_identities: tuple[str, ...]   # Top-N candidate IDs (feasible only)
    termination_status: str                    # "COMPLETE", "PARTIAL", "FAILED"
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]
    failure: str | None                        # None if no failure
    result_hash: str                           # SHA-256 of canonical serialization
    provenance_digest: str                     # DAG root digest
```

---

## 5. State machine

```
 ┌─────────────┐
 │  INPUT      │  Verify all input artifact digests
 │  VERIFY     │  Fail closed on any mismatch
 └──────┬──────┘
        │ OK
        ▼
 ┌─────────────┐
 │ FEASIBILITY │  Classify each candidate → FeasibilityStatus
 │ CLASSIFY    │   - UNEVALUATED / RUNTIME_FAILED → directly mapped
 └──────┬──────┘   - INTEGRITY_FAILED / PROVENANCE_FAILED → from Phase 2 outcome
        │          - FEASIBLE / INFEASIBLE → by duty/constraint rules
        ▼
 ┌─────────────┐
 │ RANKING     │  Sort all candidates by:
 │             │   1. Feasibility (FEASIBLE first)
 │             │   2. Primary engineering objective (asc/desc)
 └──────┬──────┘   3. Tie-break fields
        │          4. Source-qualified candidate ID (final tie-break)
        ▼
 ┌─────────────┐
 │  TOP-N      │  Select first N from FEASIBLE candidates
 │  SELECT     │  After deterministic sort
 └──────┬──────┘
        │
        ▼
 ┌─────────────┐
 │  RESULT     │  Build OptimizationResult
 │  BUILD      │  Compute result_hash + provenance_digest
 └──────┬──────┘
        │
        ▼
 ┌─────────────┐
 │  VERIFY     │  Verify result hash, provenance DAG
 │  FINAL      │  Fail closed on mismatch
 └─────────────┘
```

---

## 6. Feasibility rules

### 6.1 Phase 2 state → Phase 3 feasibility mapping

| Phase 2 State | Phase 3 Feasibility | Condition |
|---|---|---|
| `UNEVALUATED` | `UNEVALUATED` | Always |
| `RUNTIME_FAILED` | `RUNTIME_FAILED` | Always |
| Integrity failure detected | `INTEGRITY_FAILED` | When hash verification fails |
| Provenance failure detected | `PROVENANCE_FAILED` | When provenance verification fails |
| `EVALUATED` + hash OK + provenance OK | `FEASIBLE` or `INFEASIBLE` | By duty/constraint rules below |

### 6.2 FEASIBLE / INFEASIBLE determination

A candidate with `EVALUATED` state and passing hash/provenance verification is:

- **FEASIBLE** if: required duty is satisfied within tolerance AND terminal delta-T ≥ minimum AND energy closure satisfied AND UA-LMTD closure satisfied
- **INFEASIBLE** otherwise, with a diagnostic key explaining why

### 6.3 Tolerance rules

- All tolerances have explicit typed values from the frozen sizing request
- No tolerance may be a bare float; all use `Quantity` or `Decimal` with defined units
- Default tolerance = 0 (exact satisfaction required, no slack)

### 6.4 Warning impact

- Warnings from Phase 2 rating do **not** affect feasibility classification
- Warnings are carried through to the `FeasibilitySummary.all_rating_warnings` and `RankedCandidateRecord`
- Blockers from Phase 2 make the candidate **infeasible**

### 6.5 Explicit exclusions

- No pressure-drop check
- No velocity constraint check
- No C4 constraint
- No TASK-010 concerns

---

## 7. Ranking key

Sorting is performed as a single deterministic pass with the following key (ascending/descending as noted):

| Level | Field | Direction | Notes |
|---|---|---|---|
| 1 | Feasibility | FEASIBLE first | FEASIBLE < INFEASIBLE < UNEVALUATED < RUNTIME_FAILED < INTEGRITY_FAILED < PROVENANCE_FAILED |
| 2 | Engineering objective | Ascending | MINIMUM_OUTER_HEAT_TRANSFER_AREA: smaller is better (ascending); `None` sorts last |
| 3 | First tie-break field | Ascending | As defined by optimization objective registry |
| 4 | Second tie-break field | Ascending | As defined by optimization objective registry |
| 5 | Source-qualified candidate ID | Ascending | Lexicographic; final deterministic tie-break |

### 7.1 None handling
- `None` values sort after all finite values
- This ensures candidates with missing objective values are ranked below those with valid values

### 7.2 NaN / infinity handling
- `NaN` and `inf` are rejected at the input gate, before ranking begins
- If `NaN` or `inf` somehow bypasses the gate, ranking raises an explicit `ValueError`
- This ensures no silent propagation of invalid numerical states

### 7.3 Decimal / float canonicalization
- All objective values are `Decimal` with explicit precision
- Float values are rejected at the input boundary
- Canonical form: `Decimal` with trailing zeros stripped, using `normalize()`

---

## 8. Optimization objective

Phase 3 consumes exactly one optimization objective from the sizing request:

- **MINIMUM_OUTER_HEAT_TRANSFER_AREA** — ascending (smallest area is best)

Future objectives must be added through a typed enum and explicit registry, not through string branching scattered across the codebase.

No new objective may be added during Phase 3 implementation.

---

## 9. Top-N rules

- Top-N candidates are selected **only** from candidates classified as `FEASIBLE`
- N comes from the frozen sizing request (field: `requested_top_n`)
- If N ≤ 0: no candidates are returned (empty result, with a warning)
- If feasible count < N: all feasible candidates are returned (no padding)
- If no feasible candidates: empty Top-N list, `feasible_candidate_count = 0`
- Truncation occurs **after** full deterministic sort — all candidates are sorted, then the first N feasible are taken
- Top-N selection does **not** alter candidate identity, hash, or evaluation record
- The full ranked candidate list is preserved in `ordered_ranked_candidate_identities`; Top-N is a strict subset

---

## 10. Hash contract

### 10.1 Canonical serialization format

| Field | Canonical type |
|---|---|
| `schema_version` | integer |
| `optimization_result_id` | string |
| `sizing_request_identity_digest` | string |
| `materialized_candidate_set_digest` | string |
| `evaluation_batch_digest` | string |
| `optimization_objective` | string |
| `requested_top_n` | integer |
| `total_candidate_count` | integer |
| `verified_candidate_count` | integer |
| `feasible_candidate_count` | integer |
| `infeasible_candidate_count` | integer |
| `failed_candidate_count` | integer |
| `ordered_ranked_candidate_identities` | ordered string list |
| `ordered_top_n_candidate_identities` | ordered string list |
| `termination_status` | string |
| `warnings` | ordered string list |
| `blockers` | ordered string list |
| `failure` | string or null |

### 10.2 Hash computation
1. Serialize fields in the order listed above using `canonical_json`
2. Compute `sha256(canonical_json).hexdigest()`
3. The result is `result_hash`

### 10.3 Verification
- During verification, recompute the hash and compare
- Any mismatch → fail closed (`PROVENANCE_INCOMPLETE` + fixed error message)

---

## 11. Provenance contract

### 11.1 Provenance DAG nodes

| Node | Content digest |
|---|---|
| `sizing_request` | `sizing_request_identity_digest` |
| `sizing_gate` | `passed_sizing_gate_identity` |
| `candidate_set` | `materialized_candidate_set_digest` |
| `evaluation_batch` | `evaluation_batch_digest` |
| `result_payload` | `result_hash` |
| `result_provenance_root` | SHA-256 of concatenated child digests |

### 11.2 DAG edges

```
sizing_request ──→ sizing_gate ──→ candidate_set ──→ evaluation_batch ──→ result_payload
                                                                               │
                                                                               ▼
                                                                       result_provenance_root
                                                                       (all node digests bound)
```

### 11.3 Verification

- Provenance verification recomputes the DAG from root downward
- All source artifact bindings are checked by digest
- Any mismatch → fail closed

---

## 12. Failure semantics (strict-stop)

| Scenario | Behaviour |
|---|---|
| Input artifact verification fails | Do not begin feasibility classification |
| Any global identity mismatch (sizing request, gate, candidate set, evaluation batch) | Do not begin ranking |
| Individual candidate hash/provenance mismatch | Candidate is classified INTEGRITY_FAILED or PROVENANCE_FAILED; other candidates continue |
| Individual candidate evaluation runtime failure | Candidate is classified RUNTIME_FAILED; other candidates continue |
| Feasibility logic encounters unexpected exception | Specific candidate is marked INFEASIBLE with diagnostic; other candidates continue |
| Ranking encounters unexpected exception | Fail entire batch — no partial ranking |
| Result construction encounters unexpected exception | Fail entirely — no partial Top-N returned |
| `BaseException` | Not caught; propagates upward |

### 12.1 Error message rules

All error messages that enter the hash, provenance, or user-visible artifact must use **fixed deterministic strings**. Prohibited:

- `str(exc)`
- `repr(exc)`
- `traceback.format_exc()`
- Memory addresses
- Runtime-specific object representations

---

## 13. Test matrix

Phase 3 implementation must cover at least the following tests:

| Test | Description |
|---|---|
| Input permutation invariance | Different input orderings produce identical result |
| Candidate record permutation invariance | Different candidate record orderings produce identical ranking |
| Tie-break determinism | Identical objective values → secondary fields decide |
| Equal objective values | Three candidates with identical objective → deterministic by tie-break |
| Zero feasible candidates | No candidate passes feasibility → empty Top-N |
| Fewer than N feasible | feasible_count = 2, N = 5 → all 2 returned |
| Exactly N feasible | feasible_count = 5, N = 5 → all 5 returned |
| More than N feasible | feasible_count = 10, N = 5 → exactly 5 returned |
| Tampered Phase 2 identity | Input digest mismatch → fail closed |
| Tampered evidence digest | Evidence digest mismatch → fail closed |
| Missing candidate record | Record count mismatch → fail closed |
| Duplicate candidate ID | Same ID twice → fail closed |
| NaN / infinity rejection | Input with NaN/inf → `ValueError` |
| Hash verification failure | Tampered hash → fail closed |
| Provenance verification failure | Tampered provenance → fail closed |
| Result replay equality | Same Phase 2 inputs → identical result hash |
| Python 3.11 / 3.12 consistency | Identical result across Python versions |
| Registry order independence | Optimization objective registry order does not affect ranking |
| Feasibility status transition | Each Phase 2 state maps to correct Phase 3 status |
| Top-N does not mutate candidates | Candidate identities unchanged after Top-N selection |
| Ranking preserves non-feasible ordering | Infeasible/unevaluated candidates are deterministically ordered |

---

## 14. Acceptance criteria

1. All 30+ Phase 3 tests pass on Python 3.11 and 3.12
2. Result hash is deterministic and reproducible from identical Phase 2 inputs
3. Provenance DAG verification detects any tampered node
4. Input verification fail-closed works for all failure modes
5. Top-N selection never exceeds feasible count
6. No Phase 2 artifact is mutated
7. Ruff check, format check, mypy strict, coverage all pass
8. Pip-audit passes
9. Design review passes before implementation is authorized

---

## 15. Implementation boundary

Phase 3 implementation (when authorized) is limited to:

- `src/hexagent/optimization/feasibility.py` — feasibility classification
- `src/hexagent/optimization/ranking.py` — deterministic ranking + tie-breaking
- `src/hexagent/optimization/result.py` — result construction + hash + provenance
- `tests/unit/test_task009_phase3*.py` — Phase 3 tests

Phase 3 implementation does **not** modify:

- `src/hexagent/optimization/evaluation.py`
- `src/hexagent/optimization/identities.py`
- `src/hexagent/optimization/catalog.py`
- `src/hexagent/optimization/gate.py`
- `src/hexagent/optimization/materialization.py`
- Any other `src/hexagent/optimization/` module from Phase 1 or Phase 2
- Any TASK-008 modules
- Any catalog schema modules

---

## 16. Review and authorization

This document is **DRAFT** until a separate engineering design review has passed and a frozen contract commit SHA is established. Implementation must not begin until authorized.
