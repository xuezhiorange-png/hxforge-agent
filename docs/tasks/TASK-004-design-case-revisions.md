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

- [x] Revision is immutable after creation
- [x] Every case modification produces a new revision
- [x] Revision contains parent, number, snapshot, content hash
- [x] Same input → same canonical JSON → same hash
- [x] Field order does not affect hash
- [x] Numerical, enum, unit objects serialize stably
- [x] CalculationRun references unique case revision
- [x] Warnings, blockers, failures are structured
- [x] Provenance graph serializable with node dependency validation
- [x] Repository Protocol + memory impl pass consistency tests
- [ ] Ruff, mypy, pytest, pip-audit pass on Python 3.11/3.12

## Engineering Decisions

- canonical JSON: UTF-8, sorted keys, compact separators
- hash: sha256:<64-hex-lowercase>
- revision immutability: frozen dataclass
- state transitions: encoded and tested
- provenance graph: DAG with topological ordering

## Tests

### Implemented

| Test | Module | What it verifies |
|---|---|---|
| `test_canonical_json_sorted_keys` | `tests/unit/test_canonical.py` | Dict key order does not affect output. |
| `test_canonical_json_nan_rejection` | `tests/unit/test_canonical.py` | NaN/Infinity raise `ValueError`. |
| `test_canonical_json_enum_serialization` | `tests/unit/test_canonical.py` | Enums serialize as `.value`. |
| `test_canonical_json_uuid_serialization` | `tests/unit/test_canonical.py` | UUIDs serialize as hyphenated strings. |
| `test_canonical_json_datetime_utc` | `tests/unit/test_canonical.py` | Timezone-naive datetimes are rejected; UTC is normalized. |
| `test_canonical_json_quantity` | `tests/unit/test_canonical.py` | Quantities serialize as `{value, unit, kind}`. |
| `test_canonical_json_tuple_sorted` | `tests/unit/test_canonical.py` | Tuples serialize as sorted lists. |
| `test_sha256_deterministic` | `tests/unit/test_canonical.py` | Same input produces same hash. |
| `test_sha256_format` | `tests/unit/test_canonical.py` | Hash has `sha256:` prefix and 64 hex chars. |
| `test_revision_immutable` | `tests/unit/test_revisions.py` | `DesignCaseRevision` is frozen. |
| `test_revision_parent_chain` | `tests/unit/test_revisions.py` | Parent linkage and revision_number progression. |
| `test_revision_hash_matches_payload` | `tests/unit/test_revisions.py` | content_hash matches recomputed hash. |
| `test_revision_diff_changed_fields` | `tests/unit/test_revisions.py` | `RevisionDiff` correctly identifies changed fields. |
| `test_run_state_machine` | `tests/unit/test_revisions.py` | All legal transitions; illegal transitions raise. |
| `test_provenance_graph_dag` | `tests/unit/test_provenance.py` | Cycles are rejected. |
| `test_provenance_graph_self_loop` | `tests/unit/test_provenance.py` | Self-loops are rejected. |
| `test_provenance_graph_requires_case_revision` | `tests/unit/test_provenance.py` | At least one CASE_REVISION node. |
| `test_provenance_graph_unique_ids` | `tests/unit/test_provenance.py` | Duplicate node IDs are rejected. |
| `test_revision_service_create_initial` | `tests/unit/test_revision_service.py` | Initial revision creation with hash. |
| `test_revision_service_create_from_parent` | `tests/unit/test_revision_service.py` | Child revision with incremented number. |
| `test_revision_service_integrity_check` | `tests/unit/test_revision_service.py` | Hash and parent verification. |
| `test_run_service_lifecycle` | `tests/unit/test_run_service.py` | Full lifecycle: create → start → succeed/fail/block/cancel. |
| `test_run_service_invalid_transition` | `tests/unit/test_run_service.py` | Illegal transitions raise `InvalidStateTransitionError`. |

### Pending

| Test | Description |
|---|---|
| `test_unit_equivalence_hash` | Verify same SI value from different display units produces the same hash. |
| `test_revision_history_ordering` | Verify `list_by_case` returns revisions in `revision_number` order. |
| `test_run_service_verify_integrity` | Verify `verify_run_integrity` catches hash mismatches. |

## CI Status

- (pending)

## Review Status

- Round 1: pending
