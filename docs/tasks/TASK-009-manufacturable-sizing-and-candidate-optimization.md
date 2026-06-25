# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** BLOCKED — Engineering design review changes required
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created
**Production implementation:** Not started

TASK-009 will return to READY only after Round 2 Engineering Design Review passes.

## Dependency Baseline

- TASK-008 PR #21: merged
- TASK-008 reviewed Head: `37eda3580ba7acced1beb4cec307343a9f5449ec`
- TASK-008 merge commit: `cef3f85402b1696b336347293afc7276bbf67545`
- TASK-008 Issue #20: closed
- C4 Issue #19: open; C4 remains deferred and unimplemented
- TASK-016: PLANNED; not a dependency for TASK-009 v0.1

## Objective

Generate only approved, manufacturable discrete double-pipe geometry candidates, evaluate each candidate through the public TASK-008 rating kernel, apply explicit feasibility contracts, and return a deterministic ranked result with complete hash, provenance, and JSON round-trip integrity.

---

## 1. Design Review Status

**Round 1 Review:** CHANGES REQUIRED
**Review Comment ID:** 4797079477

TASK-009 is BLOCKED pending design review resolution. The following frozen contracts resolve all Round 1 blockers.

---

## 2. Catalog Authority Boundary: TASK-009 vs TASK-016

### TASK-009 v0.1 Responsibility

TASK-009 receives caller-supplied, immutable, hash-verified **CompleteDoublePipeAssemblySnapshot** objects. Each assembly option already contains the full manufacturable combination:

- inner tube inside diameter
- inner tube outside diameter
- outer pipe inside diameter
- wall thermal conductivity
- tube roughness
- annulus roughness
- allowed effective lengths or a single `LengthGridSpec`
- assembly option ID
- catalog snapshot ID
- catalog version
- catalog content hash
- source identity
- manufacturing metadata

TASK-009 is responsible only for:

- schema validation of the snapshot
- hash verification
- deterministic ordering
- candidate generation
- manufacturability filtering
- TASK-008 rating evaluation
- feasibility evaluation
- deterministic ranking
- result hash and provenance

TASK-009 does **not** perform:

- declaring the catalog has organizational approval
- establishing an enterprise master-data catalog
- independent Cartesian combination of inner-tube and outer-pipe options
- inferring compatibility, net clearance, or standard-series matching
- auto-generating non-existent diameter and wall-thickness combinations

### TASK-016 Future Responsibility

TASK-016 is the future authority for:

- organization-approved master catalogs
- tube/pipe/hairpin source governance
- compatibility rules
- vendor/source approval
- catalog lifecycle and version governance

**Relationship:** TASK-009 v0.1 consumes caller-supplied complete assembly snapshots and does not claim source approval. TASK-016 may later supply compatible snapshots.

---

## 3. Candidate Identity: Physical vs Evaluation

### ManufacturableCandidateIdentity

Represents a stable physically manufacturable candidate. Contains **only**:

- catalog snapshot ID
- catalog version
- catalog content hash
- assembly option ID
- complete geometry fields (as validated by `DoublePipeGeometry`)
- exact effective length
- manufacturing option identity

Must **not** contain:

- fluid identities
- temperatures, pressures
- mass flow rates
- heat-duty target
- optimization objective
- tolerances
- Top-N
- flow arrangement
- tube/annulus side assignment
- TASK-008 result hash

The same physical exchanger under different operating conditions must produce the **same** `ManufacturableCandidateIdentity`.

Candidate deduplication is based on `ManufacturableCandidateIdentity`.

### CandidateEvaluationIdentity

Contains:

- `ManufacturableCandidateIdentity`
- `SizingRequestIdentity`
- TASK-008 rating request identity
- TASK-008 result hash
- TASK-008 provenance digest

The same physical candidate under different operating conditions produces **different** `CandidateEvaluationIdentity`.

---

## 4. Candidate Counts and Upper Limit

### Three Exact Counters

```text
raw_combination_count
unique_candidate_count
evaluated_candidate_count
```

**raw_combination_count:** Theoretical combination count before instantiation and deduplication. For v0.1 with complete assembly snapshots:

```text
sum(number of permitted effective lengths for each eligible assembly option)
```

**unique_candidate_count:** Candidates after deduplication by `ManufacturableCandidateIdentity`.

**evaluated_candidate_count:** Actual TASK-008 rating calls.

### Cap Rules

Hard upper limit:

```text
HARD_RAW_COMBINATION_CAP = 10_000
```

Request may set a lower limit:

```text
request_raw_combination_cap
```

Effective cap:

```text
effective_cap = min(request_raw_combination_cap, HARD_RAW_COMBINATION_CAP)
```

**The cap is checked against raw_combination_count before candidate instantiation, deduplication, and before any TASK-008 rating call.**

On cap exceeded:

```text
status = BLOCKED
raw_combination_count = computed value
unique_candidate_count = 0
evaluated_candidate_count = 0
selected_candidate = None
top_candidates = ()
```

No partial generation, partial evaluation, or silent truncation.

---

## 5. Duty Feasibility Formula

### Tolerance Fields

```text
duty_absolute_tolerance_w  (finite, >= 0)
duty_relative_tolerance    (finite, >= 0)
```

### Effective Tolerance

```text
effective_duty_tolerance_w = max(
    duty_absolute_tolerance_w,
    duty_relative_tolerance * max(required_duty_w, 1.0)
)
```

### Feasibility Condition

```text
rated_duty_w + effective_duty_tolerance_w >= required_duty_w
```

### Derived Fields

```text
duty_shortfall_w = max(required_duty_w - rated_duty_w, 0.0)
duty_overshoot_w = max(rated_duty_w - required_duty_w, 0.0)
```

All tolerance fields, formula version, and computed values enter request identity, result hash, and provenance.

---

## 6. Area Optimization Objective

Rename to eliminate ambiguity:

```text
MINIMUM_HEAT_TRANSFER_AREA  →  MINIMUM_OUTER_HEAT_TRANSFER_AREA
```

Area value must use TASK-008 `RatingResult.area_outer_m2`.

Rationale: TASK-008's overall U is frozen on the inner-tube outer-surface basis, and `area_outer_m2` is consistent with that basis.

Other objective:

```text
MINIMUM_EFFECTIVE_LENGTH
```

May **not** use:

- `area_inner_m2`
- `UA_w_k`
- `U_w_m2_k`
- custom equivalent area
- implicit area basis

Area basis must enter request identity, result identity, and provenance.

---

## 7. Request Cardinality

TASK-009 v0.1 permits exactly **one** per request:

- flow arrangement
- tube/annulus side assignment
- tube boundary condition
- annulus boundary condition

Remove or correct task-card language about:

```text
canonical side-assignment and flow-arrangement ordering when multiple values are allowed
```

v0.1 does **not** allow a single request to enumerate multiple flow arrangements, side assignments, or boundary-condition policies. The caller submits separate independent sizing requests for different configurations.

---

## 8. Length Source Model

Each `CompleteDoublePipeAssemblySnapshot` must use exactly one of:

### Mode A: Explicit Lengths

```text
allowed_effective_lengths_m: tuple[float, ...]
```

### Mode B: Length Grid

```text
LengthGridSpec
```

Fields:

```text
minimum_length_m
maximum_length_m
increment_m
endpoint_policy
decimal_quantization
```

Constraints:

- all three numeric fields must be finite
- `minimum_length_m > 0`
- `maximum_length_m >= minimum_length_m`
- `increment_m > 0`
- a snapshot must not provide both explicit lengths and a `LengthGridSpec`
- grid expansion must be deterministic
- use `Decimal` or equivalent canonicalization strategy
- endpoint inclusion must be explicitly stated
- generated values must be canonicalized before forming candidate identity

### Request Length Filtering

Request fields:

```text
minimum_effective_length_m
maximum_effective_length_m
```

These are used only for filtering or intersection with the approved set. They must **not** create an independent second length grid. The request must not supply an independent increment to re-generate catalog lengths.

---

## 9. RatingEvidenceSnapshot

v0.1 does **not** embed full `RatingResult` objects in the final sizing result.

### Snapshot Contents

```text
RatingEvidenceSnapshot
```

Must include at least:

- rating status
- heat_duty_w
- hot_outlet_temperature_k
- cold_outlet_temperature_k
- area_inner_m2
- area_outer_m2
- UA_w_k
- LMTD_k
- energy_residual_w
- ua_lmtd_residual_w
- tube inlet density
- annulus inlet density
- tube flow area
- annulus flow area
- warnings
- blockers
- failure
- provider identity
- selected correlation identities
- rating result hash
- rating provenance digest
- rating verify_hash result
- rating verify_provenance result
- rating request identity digest
- rating execution context identity

### Rules

- The snapshot is the audit evidence for the final sizing result.
- Each candidate evaluation must still first obtain a full TASK-008 `RatingResult`.
- The snapshot may only be constructed from a hash/provenance-verified `RatingResult`.
- A candidate whose `RatingResult` fails verification must not be treated as feasible.
- Full `RatingResult` is recoverable through deterministic replay.

---

## 10. SizingStatus and Invariants

```text
class SizingStatus:
    SUCCEEDED
    BLOCKED
    FAILED
```

### SUCCEEDED

Must satisfy all of:

- at least one feasible candidate
- `selected_candidate is not None`
- `selected_candidate.feasible is True`
- `top_candidates` is non-empty
- `blockers` is empty
- `failure` is empty
- `verify_hash()` is True
- `verify_provenance()` is True

### BLOCKED

Used for deterministic engineering non-executability or no feasible solution. Includes:

- invalid request
- invalid catalog
- cap exceeded
- no manufacturable candidate
- no feasible candidate
- unsupported constraint
- rating integrity failure

Must satisfy:

- at least one blocker
- `selected_candidate is None`
- `failure` is empty
- result hash and provenance remain valid

### FAILED

Used only for unexpected runtime failures.

Must satisfy:

- `failure` is not None
- `selected_candidate is None`
- result hash and provenance remain valid

**Clarification:** `NO_FEASIBLE_CANDIDATE` => `SizingStatus.BLOCKED`. Not FAILED.

---

## 11. Top-N Contract

Rules:

```text
top_n must be integer
top_n >= 1
```

`top_candidates` contains only feasible candidates.

When `top_n <= feasible_candidate_count`: return exactly the top `top_n` candidates.

When `top_n > feasible_candidate_count > 0`: return all feasible candidates and add a structured warning:

```text
TOP_N_REDUCED_TO_FEASIBLE_COUNT
```

Do not block, do not pad with non-feasible candidates.

When `feasible_candidate_count == 0`:

```text
status = BLOCKED
selected_candidate = None
top_candidates = ()
blocker = NO_FEASIBLE_CANDIDATE
```

---

## 12. Non-Feasible Candidate Ordering

Non-feasible candidates appear only in audit output, **not** in `top_candidates`.

### Feasibility Status Severity

```text
INFEASIBLE < RATING_BLOCKED < RATING_FAILED < INTEGRITY_INVALID
```

### Rating Status Rank

```text
SUCCEEDED < BLOCKED < FAILED
```

Candidates that SUCCEED in TASK-008 but do not meet sizing feasibility must be classified as `CandidateFeasibilityStatus.INFEASIBLE` — not misclassified as TASK-008 BLOCKED.

### Non-Feasible Sort Key

```text
(
    feasibility_status_rank,
    rating_status_rank,
    primary_message_code,
    manufacturable_candidate_id
)
```

### Primary Message Selection

From blockers or failure, determine deterministic primary message by:

1. Severity rank: `BLOCKER < ERROR < WARNING < INFO`
2. `ErrorCode` string ascending
3. `source_module` ascending
4. `affected_paths` canonical tuple ascending
5. message string ascending

Must not rely on original insertion order.

---

## 13. Velocity Constraint

Velocity envelope constraint is **deferred / out of scope for TASK-009 v0.1**.

Removed from feasibility and ranking criteria.

If enabled in a future version:

- must undergo separate design review
- may only use TASK-008's verified inlet-state snapshot density
- must not call `PropertyProvider` independently
- must not compute velocity from unfrozen density sources

---

## 14. Frozen ErrorCode Values

### Reused Existing Codes

```text
INPUT_MISSING
INPUT_INCONSISTENT
UNIT_INVALID
HASH_MISMATCH
PROVENANCE_INCOMPLETE
UNSUPPORTED_SERVICE
CALCULATION_BLOCKED
CORRELATION_IMPLEMENTATION_UNAVAILABLE  (propagated from C4, unchanged)
```

### New TASK-009 ErrorCode Values

```text
INVALID_SIZING_REQUEST = "invalid_sizing_request"
CATALOG_MISSING = "catalog_missing"
CATALOG_INVALID = "catalog_invalid"
CATALOG_IDENTITY_MISMATCH = "catalog_identity_mismatch"
NO_MANUFACTURABLE_CANDIDATE = "no_manufacturable_candidate"
CANDIDATE_COUNT_LIMIT_EXCEEDED = "candidate_count_limit_exceeded"
INVALID_OPTIMIZATION_OBJECTIVE = "invalid_optimization_objective"
INVALID_TOP_N = "invalid_top_n"
UNSUPPORTED_SIZING_CONSTRAINT = "unsupported_sizing_constraint"
RATING_RESULT_INTEGRITY_FAILED = "rating_result_integrity_failed"
NO_FEASIBLE_CANDIDATE = "no_feasible_candidate"
TOP_N_REDUCED_TO_FEASIBLE_COUNT = "top_n_reduced_to_feasible_count"
```

No synonymous duplicate codes.

---

## 15. Canonical Source of Truth

The normative engineering contract is:

```text
docs/tasks/TASK-009-manufacturable-sizing-and-candidate-optimization.md
```

Issue #23 retains the objective, scope, and acceptance summary. It references the task card path and frozen commit SHA as the canonical source.

---

## 16. Required Test Matrix

### Identity and Catalog

1. Complete assembly snapshot acceptance — no independent tube/pipe Cartesian combination.
2. `ManufacturableCandidateIdentity` stability across different operating conditions.
3. `CandidateEvaluationIdentity` changes when operating conditions change.

### Candidate Counts and Cap

4. `raw_combination_count` computed before instantiation and rating.
5. Cap exceeded blocks before any candidate instantiation and rating.
6. Accurate `raw_combination_count`, `unique_candidate_count`, `evaluated_candidate_count`.

### Duty Feasibility

7. `duty_absolute_tolerance_w` applied correctly.
8. `duty_relative_tolerance` applied correctly.
9. Both tolerances simultaneously (effective = max of both).

### Optimization Objective

10. `MINIMUM_OUTER_HEAT_TRANSFER_AREA` using `area_outer_m2`.
11. `MINIMUM_EFFECTIVE_LENGTH` using effective length.

### Length Models

12. Explicit `allowed_effective_lengths_m`.
13. `LengthGridSpec` with endpoint/quantization rules.
14. Request `minimum_effective_length_m` and `maximum_effective_length_m` filtering.

### Status and Top-N

15. No feasible candidate => `BLOCKED` with `NO_FEASIBLE_CANDIDATE`.
16. `top_n > feasible_candidate_count > 0` => reduced with `TOP_N_REDUCED_TO_FEASIBLE_COUNT` warning.
17. `top_n = 1`, `top_n = exact feasible count`, `top_n > feasible count`.
18. Invalid `top_n` value => `INVALID_TOP_N` blocker.

### Non-Feasible Ordering

19. Non-feasible deterministic ordering by feasibility status, rating status, error code, and candidate ID.
20. Deterministic primary blocker selection from multiple blockers.

### Rating Evidence

21. `RatingEvidenceSnapshot` contains all required fields.
22. Snapshot can only be constructed from hash/provenance-verified `RatingResult`.
23. Replay identity integrity.

### ErrorCodes

24. Exact new `ErrorCode` values match frozen list.
25. No synonymous duplicate codes.

### Documentation Alignment

26. Issue #23 references task card and frozen commit as canonical source.

---

## 17. Thermal Evaluator Boundary

TASK-008 is the only thermal rating evaluator. TASK-009 must not reimplement or bypass:

- heat balance
- Q_max
- outlet enthalpy inversion
- LMTD
- ε-NTU
- thermal resistance or UA
- TASK-007 correlation selection
- TASK-008 blockers, warnings, hashes, or provenance

---

## 18. Sizing Request

The request must explicitly provide:

- hot and cold fluid identities
- inlet temperatures and pressures
- hot and cold mass flow rates
- flow arrangement (exactly one)
- tube/annulus side assignment (exactly one)
- tube and annulus thermal boundary conditions (exactly one each)
- minimum terminal temperature difference
- minimum required heat duty in watts
- approved catalog snapshot identities
- duty_absolute_tolerance_w
- duty_relative_tolerance
- optimization objective (explicit, no silent default)
- Top-N count (`top_n >= 1`)
- request_raw_combination_cap (optional; defaults to `HARD_RAW_COMBINATION_CAP`)

No silent default optimization objective.

Initial supported thermal target: minimum required heat duty only. Outlet-temperature or multi-specification targets require a reviewed scope extension.

---

## 19. Candidate Generation

Generation must be deterministic and insertion-order independent.

Required rules:

- canonical catalog ordering
- canonical geometry-option ordering
- canonical effective-length ordering
- exact duplicate elimination using `ManufacturableCandidateIdentity`
- deterministic candidate IDs
- no random search
- no stochastic optimization
- no heuristic sampling
- no silent truncation

---

## 20. Candidate Feasibility

A candidate is feasible only when:

- TASK-008 status is `SUCCEEDED`
- TASK-008 `verify_hash()` is true
- TASK-008 `verify_provenance()` is true
- `rated_duty_w + effective_duty_tolerance_w >= required_duty_w`
- TASK-008 minimum terminal-temperature and engineering contracts are satisfied
- geometry and catalog constraints are satisfied
- all explicitly supported request constraints are satisfied

Blocked and failed candidates remain in the audit result and must not be silently discarded.

---

## 21. Hash Identity

Candidate and result identities use canonical SHA-256 payloads.

`ManufacturableCandidateIdentity` includes: catalog snapshot ID, catalog version, catalog content hash, assembly option ID, complete geometry fields, exact effective length, manufacturing option identity.

`SizingResultIdentity` includes:

- complete request identity
- catalog identities and content hashes
- all generated candidate IDs
- evaluation order
- every retained TASK-008 result hash and provenance digest
- feasibility decisions
- ranking records
- selected candidate
- Top-N ordering
- termination reason
- warnings and blockers

Changing catalog content, objective, tolerance, target duty, rating input, candidate set, or ranking order must change the appropriate digest.

---

## 22. Provenance Graph

Required node concepts:

- EXTERNAL or CASE_REVISION root
- SIZING_RUN
- CATALOG snapshot
- CANDIDATE
- TASK-008 RATING_RESULT
- WARNING
- BLOCKER
- SIZING_RESULT

`verify_hash()` and `verify_provenance()` must pass before and after JSON round-trip and fail after independent payload, node, edge, ranking, catalog, or TASK-008 digest tampering.

---

## 23. Determinism and Replay

The same canonical request and catalog content must produce identical:

- candidate set
- candidate IDs
- candidate evaluation order
- retained rating result identities
- feasibility decisions
- ranking order
- selected candidate
- Top-N result
- result hash
- provenance digest

Input insertion order must not affect any output identity.

---

## 24. Pressure-Drop Boundary

Pressure drop is out of scope for TASK-009 v0.1. No pressure-drop limit, correlation, score, or optimization term may be added until a separate source-verified engineering contract is approved.

---

## 25. Performance Contract

- Initial execution is deterministic and single-process.
- Concurrency is not required.
- No silent pruning, sampling, or approximation.
- Generated and evaluated counts must be exact.
- Performance tests use controlled rating doubles rather than large CoolProp candidate sets.

---

## 26. Exclusions

- pressure-drop formulas or constraints
- continuous nonlinear optimization
- stochastic, genetic, Bayesian, or ML optimization
- velocity envelope constraints (deferred)
- cost and life-cycle economics
- material selection
- mechanical strength or code compliance
- API endpoints
- reports
- UI
- C4 numerical implementation
- two-phase, shell-and-tube, plate, or air-cooled exchanger sizing

---

## 27. Delivery Sequence

1. Complete Round 2 Engineering Design Review.
2. Only after review passes: create implementation branch and Draft PR.
3. Implement catalog and identity models (before optimizer).
4. Implement deterministic candidate generation and deduplication.
5. Integrate TASK-008 rating evaluation.
6. Implement feasibility and ranking.
7. Implement result hash, provenance, JSON round-trip, and tamper verification.
8. Add direct, Golden, and integration tests.
9. Keep PR Draft through engineering review and CI pass.

---

## Acceptance Criteria

- [ ] Round 2 Design Review passes before implementation starts.
- [ ] Only discrete approved catalog candidates are generated.
- [ ] Candidate identity is based on `ManufacturableCandidateIdentity`.
- [ ] TASK-008 is the sole thermal evaluator.
- [ ] Candidate generation and ranking are insertion-order independent.
- [ ] Objective is explicit and typed; no weighted score or silent default.
- [ ] `NO_FEASIBLE_CANDIDATE` is `BLOCKED`, not `FAILED`.
- [ ] Top-N contains feasible candidates only, with deterministic truncation warning.
- [ ] Non-feasible ordering and primary message selection are deterministic.
- [ ] `RatingEvidenceSnapshot` is the audit record; full `RatingResult` is recoverable via replay.
- [ ] Exact frozen `ErrorCode` values are used; no synonymous duplicates.
- [ ] No pressure-drop or velocity constraint is introduced.
- [ ] Blocked and failed candidates remain auditable.
- [ ] Candidate and result hashes are deterministic.
- [ ] Provenance topology and payload identity are complete.
- [ ] JSON round-trip and tamper detection pass.
- [ ] Required independent Golden cases pass.
- [ ] Ruff, format check, mypy, pytest with coverage, and pip-audit pass on Python 3.11 and 3.12.
- [ ] Engineering review passes before Ready or merge.
