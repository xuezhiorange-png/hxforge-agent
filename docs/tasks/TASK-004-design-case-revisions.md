# TASK-004 — Immutable Design Case Revisions and Calculation Provenance

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #8
- Branch: `codex/task-004-design-case-revisions`
- PR: #9 (Draft)

## Scope

### In Scope

- Immutable `DesignCaseRevision` with content hash
- Canonical JSON serialization rules (tuple order preserved, SI-equivalent hashing)
- Parent-child revision relationships with chain integrity
- `RevisionDiff` with recursive field-level diffs and before/after values
- `CalculationRun` with state machine and terminal-state invariants
- Structured `EngineeringMessage` (BLOCKER/ERROR/WARNING/INFO) with severity-derived continuation
- `ErrorCode` StrEnum with extension mechanism
- `ProvenanceGraph` DAG with RESULT/WARNING/BLOCKER node types, payload_hash, canonical ordering
- Repository Protocol + in-memory implementation (deep-copy isolation)
- `RevisionService` + `RunService`
- 389 tests (unit + integration + review-item tests)
- Documentation

### Out of Scope

- PostgreSQL / SQLAlchemy / Alembic / Redis / Celery
- FastAPI write endpoints
- Heat balance / LMTD / ε-NTU / heat transfer / pressure drop
- Correlation registry / structural enums / costing / agent orchestration

## Acceptance Criteria

- [x] Revision is immutable after creation
- [x] Every case modification produces a new revision
- [x] Revision contains parent, number, snapshot, content hash
- [x] Same input → same canonical JSON → same hash
- [x] Field order does not affect hash
- [x] Numerical, enum, unit objects serialize stably
- [x] Quantity objects hash by SI value + dimension, not display unit (°C↔K equivalence)
- [x] CalculationRun references unique case revision
- [x] Warnings, blockers, failures are structured
- [x] Provenance graph serializable with node dependency validation
- [x] Repository Protocol + memory impl pass consistency tests
- [x] Ruff, mypy, pytest pass on Python 3.11/3.12
- [x] Tuple order preserved in canonical JSON (only set/frozenset sorted)
- [x] Deep immutability: repos return detached snapshots, nested mutation impossible
- [x] Revision chain: same-case parentage, consecutive numbering, no-op rejection
- [x] RevisionDiff: recursive paths, before/after values, deterministic ordering
- [x] CalculationRun: model_validator enforces terminal-state invariants at construction
- [x] Run repository: immutable identity fields protected, transition policy centralised
- [x] Provenance: RESULT/WARNING/BLOCKER node types, payload_hash, insertion-order-independent hash
- [x] Messages: BLOCKER severity, severity→continuation derived, stable ErrorCode enum
- [x] 389 tests all passing

## Engineering Decisions

- canonical JSON: UTF-8, sorted keys, compact separators
- hash: sha256:<64-hex-lowercase>
- revision immutability: frozen dataclass + deep-copy repository
- state transitions: centralised in `revisions.py`, enforced at model and repository level
- provenance graph: DAG with topological ordering, canonical node/edge sort for hashing
- unit-equivalent hashing: SI value + kind, display unit excluded from content identity
- message continuation: derived from severity (before-validator), not caller-supplied

## Test Summary

**389 tests** across 12 test files:

| Module | Tests | Coverage |
|---|---|---|
| `test_properties.py` | 100 | CoolProp property service |
| `test_review_items.py` | 62 | All 10 review items |
| `test_engineering_messages.py` | 40 | Message model, severity, codes |
| `test_calculation_runs.py` | 33 | Run state machine, invariants |
| `test_canonical_serialization.py` | 25 | Canonical JSON, hashing |
| `test_design_case_revisions.py` | 23 | Revision model, chain |
| `test_provenance_graph.py` | 22 | Graph DAG, node types |
| `test_api.py` | 21 | API integration |
| `test_revision_run_workflow.py` | 17 | End-to-end workflows |
| `test_units.py` | 16 | Unit system |
| `test_thermal.py` | 3 | Thermal stubs |
| `test_task002_round3.py` | 2 | TASK-002 roundtrip |

## CI Status

- Python 3.11: ✅ passed
- Python 3.12: ✅ passed

## Review Status

- Round 1: CHANGES REQUIRED — all 10 items addressed, re-review pending
