# TASK-009 — Manufacturable sizing and deterministic candidate optimization

**Status:** READY
**Milestone:** M2
**Priority:** P0
**Depends on:** TASK-005, TASK-008
**GitHub Issue:** #23
**Implementation branch:** Not created
**Draft PR:** Not created

## Implementation Gate

TASK-009 contracts must complete engineering review before any production implementation branch or Draft PR is created.

Dependency baseline:

- TASK-008 PR #21: merged
- TASK-008 reviewed Head: `37eda3580ba7acced1beb4cec307343a9f5449ec`
- TASK-008 merge commit: `cef3f85402b1696b336347293afc7276bbf67545`
- TASK-008 Issue #20: closed / completed
- C4 Issue #19: open; C4 remains deferred and unimplemented

## Objective

Generate only approved, manufacturable discrete double-pipe geometry candidates, evaluate each candidate through the public TASK-008 rating kernel, apply explicit feasibility contracts, and return a deterministic ranked result with complete hash, provenance, and JSON round-trip integrity.

## Frozen Engineering Contracts

### 1. Thermal evaluator boundary

TASK-008 is the only thermal rating evaluator.

TASK-009 must not reimplement or bypass:

- heat balance;
- Q_max;
- outlet enthalpy inversion;
- LMTD;
- ε-NTU;
- thermal resistance or UA;
- TASK-007 correlation selection;
- TASK-008 blockers, warnings, hashes, or provenance.

Every candidate evaluation must retain the corresponding TASK-008 `RatingResult` identity and verify both result hash and provenance.

### 2. Sizing request

The request must explicitly provide:

- hot and cold fluid identities;
- inlet temperatures and pressures;
- hot and cold mass flow rates;
- flow arrangement;
- tube/annulus side assignment;
- tube and annulus thermal boundary conditions;
- minimum terminal temperature difference;
- minimum required heat duty in watts;
- approved catalog snapshot identities;
- optimization objective;
- duty feasibility tolerance;
- Top-N count;
- request candidate-count cap.

There is no silent default optimization objective.

The initial supported thermal target is minimum required heat duty only. Outlet-temperature or multi-specification targets require a reviewed scope extension.

### 3. Approved catalog snapshots

Candidates must come only from approved immutable catalog snapshots.

Each catalog snapshot must bind:

- catalog ID;
- catalog version;
- canonical catalog content hash;
- source identity;
- geometry option identities;
- inner-tube ID and OD;
- outer-pipe ID;
- wall thermal conductivity;
- tube and annulus roughness values;
- approved effective lengths or a discrete reviewed length grid;
- any manufacturing metadata used for filtering.

No arbitrary continuous diameter, wall thickness, or length may be synthesized.

Geometry validation must reuse `DoublePipeGeometry` from TASK-008.

### 4. Candidate generation

Generation must be deterministic and insertion-order independent.

Required rules:

- canonical catalog ordering;
- canonical geometry-option ordering;
- canonical effective-length ordering;
- canonical side-assignment and flow-arrangement ordering when multiple values are allowed;
- exact duplicate elimination using canonical candidate identity;
- deterministic candidate IDs;
- no random search;
- no stochastic optimization;
- no heuristic sampling;
- no silent truncation.

The initial hard safety cap is **10,000 generated candidates**. The request may set a lower cap only. Exceeding either cap must return a structured blocker before any rating call.

### 5. Candidate feasibility

A candidate is feasible only when:

- TASK-008 status is `SUCCEEDED`;
- TASK-008 `verify_hash()` is true;
- TASK-008 `verify_provenance()` is true;
- rated duty meets or exceeds the required duty within the frozen tolerance;
- TASK-008 minimum terminal-temperature and engineering contracts are satisfied;
- geometry and catalog constraints are satisfied;
- all explicitly supported optional request constraints are satisfied.

Initial optional manufacturability constraints may include:

- minimum effective length;
- maximum effective length;
- allowed length grid/increment;
- maximum outside envelope diameter;
- optional tube-side and annulus-side inlet velocity envelopes derived from inlet density and flow area.

Blocked and failed candidates remain in the audit result and must not be silently discarded.

### 6. Pressure-drop boundary

Pressure drop is out of scope for the initial TASK-009 implementation.

No pressure-drop limit, correlation, score, or optimization term may be added until a separate source-verified engineering contract is approved. No empirical placeholder formula is permitted.

### 7. Optimization objectives

The request must select one explicit objective enum:

- `MINIMUM_HEAT_TRANSFER_AREA`;
- `MINIMUM_EFFECTIVE_LENGTH`.

No weighted composite score is permitted in the initial implementation.

Feasible ranking:

1. primary objective value ascending;
2. absolute duty overshoot above requirement ascending;
3. secondary geometry measure ascending:
   - length for area objective;
   - area for length objective;
4. canonical candidate ID ascending.

Non-feasible ranking:

1. rating-status severity;
2. primary blocker or failure error code;
3. canonical candidate ID ascending.

Feasible candidates rank before all non-feasible candidates.

### 8. Required models

Define immutable, typed, JSON-round-trip-capable models for at least:

- `CatalogIdentitySnapshot`;
- `CatalogGeometryOption`;
- `SizingRequestIdentity`;
- `CandidateIdentity`;
- `CandidateEvaluation`;
- `CandidateRankingRecord`;
- `SizingOptimizationResult`.

The final result must record:

- status;
- request identity;
- catalog snapshots;
- generated candidate count;
- evaluated candidate count;
- feasible candidate count;
- all audited candidate evaluations or a complete immutable representation;
- selected candidate;
- Top-N candidates;
- objective and tie-break policy;
- deterministic termination reason;
- warnings and blockers;
- result hash;
- provenance graph and digest.

### 9. Hash identity

Candidate and result identities use canonical SHA-256 payloads.

Candidate identity must include every engineering input that distinguishes geometry, length, arrangement, side assignment, catalog source, and rating request.

Sizing result identity must include:

- complete request identity;
- catalog identities and content hashes;
- all generated candidate IDs;
- evaluation order;
- every retained TASK-008 result hash and provenance digest;
- feasibility decisions;
- ranking records;
- selected candidate;
- Top-N ordering;
- termination reason;
- warnings and blockers.

Changing catalog content, objective, tolerance, target duty, rating input, candidate set, or ranking order must change the appropriate digest.

### 10. Provenance graph

Required node concepts:

- EXTERNAL or CASE_REVISION root;
- SIZING_RUN;
- CATALOG snapshot;
- CANDIDATE;
- TASK-008 RATING_RESULT;
- WARNING;
- BLOCKER;
- SIZING_RESULT.

The graph must bind the exact candidate generation, evaluation, feasibility, and ranking process.

`verify_hash()` and `verify_provenance()` must pass before and after JSON round-trip and fail after independent payload, node, edge, ranking, catalog, or TASK-008 digest tampering.

### 11. Determinism and replay

The same canonical request and catalog content must produce identical:

- candidate set;
- candidate IDs;
- candidate evaluation order;
- retained rating result identities;
- feasibility decisions;
- ranking order;
- selected candidate;
- Top-N result;
- result hash;
- provenance digest.

Input insertion order must not affect any output identity.

## Structured Failure Paths

Add or reuse machine-readable error codes for:

- invalid sizing request;
- missing catalog;
- invalid catalog;
- catalog version/hash mismatch;
- no manufacturable candidate;
- candidate-count cap exceeded;
- invalid optimization objective;
- invalid Top-N request;
- unsupported constraint;
- TASK-008 rating integrity failure;
- no feasible candidate;
- C4 implementation unavailable propagated from TASK-008.

No synonymous duplicate error code may be introduced when an existing code is suitable.

## Required Test Matrix

1. Hand-enumerated four-candidate catalog with independent expected candidate IDs and ordering.
2. Catalog insertion-order independence.
3. Geometry-option insertion-order independence.
4. Duplicate candidate elimination.
5. Candidate-count cap blocks before the first rating call.
6. All candidates feasible under minimum-area objective.
7. All candidates feasible under minimum-length objective.
8. Objectives select different candidates in a controlled Golden case.
9. Mixed SUCCEEDED/BLOCKED/FAILED candidates remain audited.
10. No feasible candidate result remains hash/provenance valid.
11. Exact objective tie resolved by canonical candidate ID.
12. Top-N = 1.
13. Top-N equals feasible count.
14. Invalid Top-N values block deterministically.
15. TASK-008 result hash verification failure propagation.
16. TASK-008 provenance verification failure propagation.
17. C4 unavailable propagation without fallback.
18. Catalog identity/content change changes result and provenance digests.
19. Objective or tolerance change changes result identity.
20. Deterministic repeated run.
21. JSON round-trip.
22. Request, candidate, ranking, catalog, node, edge, digest, and selected-candidate tamper detection.
23. Golden case with one uniquely feasible smallest-area candidate.
24. Golden case with one uniquely feasible shortest-length candidate.

## Performance Contract

- Initial execution is deterministic and single-process.
- Concurrency is not required.
- No silent pruning, sampling, or approximation.
- Generated and evaluated counts must be exact.
- Performance tests use controlled rating doubles rather than large CoolProp candidate sets.

## Exclusions

- pressure-drop formulas or constraints;
- continuous nonlinear optimization;
- stochastic, genetic, Bayesian, or ML optimization;
- cost and life-cycle economics;
- material selection;
- mechanical strength or code compliance;
- API endpoints;
- reports;
- UI;
- C4 numerical implementation;
- two-phase, shell-and-tube, plate, or air-cooled exchanger sizing.

## Delivery Sequence

1. Review and freeze Issue #23 and this task card.
2. Create the implementation branch only after engineering contract approval.
3. Implement catalog and identity models.
4. Implement deterministic candidate generation and deduplication.
5. Integrate TASK-008 rating evaluation.
6. Implement feasibility and ranking.
7. Implement result hash, provenance, JSON round-trip, and tamper verification.
8. Add direct, Golden, and integration tests.
9. Open a Draft PR and keep it Draft through engineering review.

## Acceptance Criteria

- [ ] Issue #23 and this task card are consistent and reviewed.
- [ ] No implementation branch is created before contract approval.
- [ ] Only approved discrete catalog candidates are generated.
- [ ] TASK-008 is the sole thermal evaluator.
- [ ] Candidate generation and ranking are insertion-order independent.
- [ ] Objective is explicit and typed.
- [ ] No weighted score or silent default objective exists.
- [ ] No pressure-drop model is introduced.
- [ ] Blocked and failed candidates remain auditable.
- [ ] Candidate and result hashes are deterministic.
- [ ] Provenance topology and payload identity are complete.
- [ ] JSON round-trip and tamper detection pass.
- [ ] Required independent Golden cases pass.
- [ ] Ruff, format check, mypy, pytest with coverage, and pip-audit pass on Python 3.11 and 3.12.
- [ ] Engineering review passes before Ready or merge.
