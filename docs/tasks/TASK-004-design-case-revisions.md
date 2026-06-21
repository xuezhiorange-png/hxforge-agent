# TASK-004 — Immutable Design Case Revisions and Calculation Provenance

## Status: IN_PROGRESS

## Issue

- GitHub Issue: #8
- Branch: `codex/task-004-design-case-revisions`
- PR: #9 (Draft)

## Scope

### In Scope

- Immutable `DesignCaseRevision` with **deep-frozen** canonical payload
- Canonical JSON: tuple order preserved, set/frozenset sorted, SI-equivalent Quantity hashing
- Parent-child revision chain with repository-level enforcement
- `RevisionDiff` with **frozen** `FieldChange` dataclass entries (recursive paths, before/after)
- `CalculationRun` with terminal-state invariants, required `input_hash` and `git_commit`
- Structured `EngineeringMessage` (BLOCKER/ERROR/WARNING/INFO) with severity-derived continuation
- `ErrorCode` StrEnum with extension mechanism
- `ProvenanceGraph` with RESULT/WARNING/BLOCKER node types, mandatory `payload_hash`
- Repository Protocol + in-memory implementation (deep-copy, chain enforcement, PENDING-only add)
- `RevisionService` + `RunService`
- 456 tests (unit + integration + review-item + review03 tests)
- Documentation

### Out of Scope

- PostgreSQL / SQLAlchemy / Alembic / Redis / Celery
- FastAPI write endpoints
- Heat balance / LMTD / ε-NTU / heat transfer / pressure drop
- Correlation registry / structural enums / costing / agent orchestration

## Acceptance Criteria

- [x] Revision is immutable after creation (deep-frozen canonical_payload via MappingProxyType)
- [x] Every case modification produces a new revision
- [x] Revision contains parent, number, snapshot, content hash
- [x] Same input → same canonical JSON → same hash
- [x] Tuple order preserved; set/frozenset sorted
- [x] Quantity objects hash by SI value + dimension, not display unit
- [x] **Full DesignCase** unit-equivalent hashes (°C/K, bar/Pa, mm/m, kg/h/kg/s)
- [x] CalculationRun requires valid `input_hash` (sha256:<64-hex>) and `git_commit`
- [x] Warnings, blockers, failures are structured
- [x] Provenance graph: RESULT/WARNING/BLOCKER node types, mandatory payload_hash
- [x] Repository enforces same-case parentage and consecutive numbering
- [x] Repository add() only accepts PENDING for runs
- [x] Terminal states require non-empty graph with CASE_REVISION, CALCULATION_RUN, (RESULT for SUCCEEDED)
- [x] FieldChange is a frozen dataclass (not mutable dict)
- [x] contextlib.suppress removed — SI conversion fails closed
- [x] 419 tests all passing
- [x] Ruff, mypy, pip-audit clean

## Test Summary

**419 tests** across 13 test files.

## CI Status

- Latest CI: ✅ All 4 jobs passed

## Review Status

- Round 1: CHANGES REQUIRED — addressed
- Round 2: CHANGES REQUIRED — addressed, re-review pending
