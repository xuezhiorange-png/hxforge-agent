# Design Case Revisions

Immutable, content-addressed snapshots of a `DesignCase` with deterministic
hashing, structured diffs and a parent-chain audit trail.

## Why revisions are immutable

Every engineering decision must be traceable. Once a `DesignCaseRevision` is
created it is never modified — the dataclass is frozen (`frozen=True`).

| Property | Benefit |
|---|---|
| **Audit trail** | Any revision can be retrieved by `revision_id` and its content hash verified independently. |
| **Reproducibility** | Two engineers running the same calculation against the same `revision_id` receive identical results. |
| **Regression detection** | A change in `content_hash` for the same design input immediately signals a tool or data change. |
| **Concurrency safety** | No locks or optimistic-version fields are needed; a revision is a value object. |

## Identifiers: `revision_id` vs `case_id`

| Field | Lifetime | Format | Purpose |
|---|---|---|---|
| `case_id` | Stable across all revisions of one design | `UUID` | Groups revisions belonging to the same engineering case. |
| `revision_id` | Unique per snapshot; never reused | `UUID` | Addresses a single, immutable content snapshot. |

A single `case_id` may have many `revision_id` values; each `revision_id`
belongs to exactly one `case_id`.

## Parent chain and `revision_number`

Revisions form a linear chain:

```
rev-1 (revision_number=1, parent=None)
  └─ rev-2 (revision_number=2, parent=rev-1)
       └─ rev-3 (revision_number=3, parent=rev-2)
```

**Invariants enforced at construction:**

1. `revision_number ≥ 1`.
2. First revision (`revision_number == 1`) must have `parent_revision_id is None`.
3. Subsequent revisions (`revision_number > 1`) must have a non-None
   `parent_revision_id` pointing to an existing revision of the same `case_id`.
4. `revision_number` is monotonically increasing and unique per `case_id`.

## Canonical JSON rules

The content hash is computed over the canonical JSON representation of the
design case payload. The rules are:

| Rule | Detail |
|---|---|
| **Encoding** | UTF-8. |
| **Key ordering** | Sorted recursively (`sort_keys=True`). |
| **Separators** | Compact: `","` and `":"` (no spaces). |
| **NaN / Infinity** | Rejected with `ValueError`. Not representable. |
| **Enum** | Serialised as `.value` (the string literal). |
| **UUID** | Serialised as the 36-character hyphenated string. |
| **datetime** | Converted to UTC, then formatted as `%Y-%m-%dT%H:%M:%S.%fZ`. Timezone-naive datetimes are rejected. |
| **Quantity objects** | Serialised as `{"value": <float>, "unit": <str>, "kind": <str or null>}`. The SI value is always used for hashing. |
| **tuple / frozenset / set** | Converted to a sorted list (sorted by their canonical JSON representation). |
| **Pydantic models** | Converted via `model_dump()` then recursively pre-processed. |
| **Nested dicts** | Keys are sorted recursively at every level. |
| **Nested lists** | Elements are recursively pre-processed; order is preserved. |

### Unit equivalence

A quantity's hash is based on its **SI value**, not its display unit.

```
Quantity(value=100.0, unit="°C")   →  {"value": 373.15, "unit": "K", "kind": "temperature"}
Quantity(value=373.15, unit="K")   →  {"value": 373.15, "unit": "K", "kind": "temperature"}
```

Both produce the same canonical JSON and therefore the same content hash,
regardless of the original display unit.

## Hash scope

The hash covers **design content only** — the fields that define the
engineering problem. The following metadata is explicitly **excluded** from the
hash:

- `revision_id`
- `case_id`
- `revision_number`
- `parent_revision_id`
- `created_at`
- `created_by`
- `change_summary`
- `changed_fields`
- `schema_version`

This ensures that re-hashing the same design content (e.g. after a system
migration that assigns new revision IDs) produces the same hash.

## Hash format

```
sha256:<64-char lowercase hex>
```

Example:

```
sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

The prefix `sha256:` allows future migration to a different hash algorithm
without breaking existing consumers.

## `RevisionDiff` — field-level comparison

A `RevisionDiff` records what changed between two consecutive revisions:

| Field | Type | Description |
|---|---|---|
| `from_revision_id` | `UUID` | Source revision. |
| `to_revision_id` | `UUID` | Target revision. |
| `changed_fields` | `tuple[str, ...]` | Dot-separated paths of fields that differ. |
| `content_hash_before` | `str` | Hash of the source revision's canonical payload. |
| `content_hash_after` | `str` | Hash of the target revision's canonical payload. |

### Path format

Changed fields use dot-separated paths that match the canonical JSON
structure:

```
hot_stream.inlet_state.temperature
cold_stream.fouling_resistance.value
constraints.design_pressure_hot
```

### `is_identical` property

Returns `True` if `content_hash_before == content_hash_after` — useful for
detecting no-op revisions (same content, different metadata).

## Repository protocol

`DesignCaseRevisionRepository` defines the persistence contract:

```python
class DesignCaseRevisionRepository(Protocol):
    def add(self, revision: DesignCaseRevision) -> None: ...
    def get(self, revision_id: UUID) -> DesignCaseRevision: ...
    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]: ...
```

The in-memory implementation (`MemoryDesignCaseRevisionRepository`) provides
a reference implementation suitable for testing. A PostgreSQL / SQLAlchemy
implementation is planned for the database integration phase.

## Future database integration path

The current in-memory repository will be replaced by a persistent store:

1. **Schema**: A `design_case_revisions` table with `revision_id` (PK),
   `case_id` (indexed), `revision_number`, `canonical_payload` (JSONB),
   `content_hash` (indexed), and metadata columns.
2. **Uniqueness**: A unique constraint on `(case_id, revision_number)`.
3. **Hash index**: A B-tree index on `content_hash` for fast lookups by
   content.
4. **Audit**: Append-only; rows are never updated or deleted. Soft-deletion
   is not used.
5. **Migration**: Alembic-managed; the frozen dataclass and Pydantic schemas
   serve as the source of truth for column types.

## Related

- `src/hexagent/domain/revisions.py` — `DesignCaseRevision`, `RevisionDiff`,
  `CalculationRun`, error classes.
- `src/hexagent/core/canonical.py` — `canonical_json`, `sha256_digest`,
  `canonicalize_design_case`.
- `src/hexagent/application/revision_service.py` — `RevisionService` with
  `create_initial_revision`, `create_revision_from_parent`,
  `verify_revision_integrity`.
- `src/hexagent/repositories/base.py` — Repository protocols.
- `src/hexagent/repositories/memory.py` — In-memory implementations.
