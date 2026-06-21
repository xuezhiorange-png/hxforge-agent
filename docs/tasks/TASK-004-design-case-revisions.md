# TASK-004 — Immutable Design Case Revisions and Calculation Provenance

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #8
- Branch: `codex/task-004-design-case-revisions`
- PR: (Draft)

## Scope

### In Scope

- Immutable `DesignCaseRevision` with content hash
- Canonical JSON serialization rules
- Parent-child revision relationships
- `RevisionDiff` for field-level changes
- `CalculationRun` with state machine
- Structured `EngineeringMessage` (warning/blocker/error)
- `ProvenanceGraph` DAG
- Repository Protocol + in-memory implementation
- `RevisionService` + `RunService`
- Unit tests + integration tests
- Documentation

### Out of Scope

- PostgreSQL / SQLAlchemy / Alembic / Redis / Celery
- FastAPI write endpoints
- Heat balance / LMTD / ε-NTU / heat transfer / pressure drop
- Correlation registry / structural enums / costing / agent orchestration

## Acceptance Criteria

- [ ] Revision is immutable after creation
- [ ] Every case modification produces a new revision
- [ ] Revision contains parent, number, snapshot, content hash
- [ ] Same input → same canonical JSON → same hash
- [ ] Field order does not affect hash
- [ ] Numerical, enum, unit objects serialize stably
- [ ] CalculationRun references unique case revision
- [ ] Warnings, blockers, failures are structured
- [ ] Provenance graph serializable with node dependency validation
- [ ] Repository Protocol + memory impl pass consistency tests
- [ ] Ruff, mypy, pytest, pip-audit pass on Python 3.11/3.12

## Engineering Decisions

- canonical JSON: UTF-8, sorted keys, compact separators
- hash: sha256:<64-hex-lowercase>
- revision immutability: frozen dataclass
- state transitions: encoded and tested
- provenance graph: DAG with topological ordering

## Tests

- (to be filled after implementation)

## CI Status

- (pending)

## Review Status

- Round 1: pending
