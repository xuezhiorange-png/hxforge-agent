# Design Case Revisions

Immutable, content-addressed snapshots of a `DesignCase` with deterministic
hashing, structured diffs and a parent-chain audit trail.

## Why revisions are immutable

Every engineering decision must be traceable. Once a `DesignCaseRevision` is
created it is never modified — the dataclass is frozen (`frozen=True`) and
repositories return deep copies.

| Property | Benefit |
|---|---|
| **Audit trail** | Any revision can be retrieved by `revision_id` and its content hash verified independently. |
| **Reproducibility** | Two engineers running the same calculation against the same `revision_id` receive identical results. |
| **Regression detection** | A change in `content_hash` for the same design input immediately signals a tool or data change. |
| **Concurrency safety** | No locks or optimistic-version fields are needed; a revision is a value object. |
| **Deep immutability** | Repositories store and return deep copies. Callers cannot mutate repository state through retrieved objects. |

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

**Invariants enforced at construction and repository level:**

1. `revision_number ≥ 1`.
2. First revision (`revision_number == 1`) must have `parent_revision_id is None`.
3. Subsequent revisions (`revision_number > 1`) must have a non-None
   `parent_revision_id` pointing to an existing revision of the **same** `case_id`.
4. `revision_number` is monotonically increasing and unique per `case_id`.
5. No-op revisions (identical content to parent) are rejected.
6. `created_by` is required for every revision (never copied from parent).
7. `changed_fields` is computed internally by recursive diff, not supplied by caller.

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
| **Quantity objects** | Serialised as `{"si_value": <float>, "kind": <str or null>}`. Only the SI value and dimension kind are included — display units are excluded from content identity. |
| **tuple** | Order is **preserved** (converted to ordered list). |
| **frozenset / set** | Converted to a **sorted** list (sorted by canonical JSON representation). |
| **Pydantic models** | Converted via `model_dump()` then recursively pre-processed. |
| **Nested dicts** | Keys are sorted recursively at every level. |
| **Nested lists** | Elements are recursively pre-processed; order is preserved. |

### Unit equivalence

A quantity's hash is based on its **SI value** and **dimension kind**, not
its display unit. The display unit is excluded from the content hash.

```python
# These produce the same canonical JSON and hash:
AbsoluteTemperature(value=100.0, unit="degC")   → {"si_value": 373.15, "kind": "absolute_temperature"}
AbsoluteTemperature(value=373.15, unit="K")     → {"si_value": 373.15, "kind": "absolute_temperature"}
```

This ensures that the same physical condition expressed in different units
produces the same design content hash.

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

A `RevisionDiff` records what changed between two revisions using recursive,
path-level diffs with before/after values:

| Field | Type | Description |
|---|---|---|
| `from_revision_id` | `UUID` | Source revision. |
| `to_revision_id` | `UUID` | Target revision. |
| `content_hash_before` | `str` | Hash of the source revision's canonical payload. |
| `content_hash_after` | `str` | Hash of the target revision's canonical payload. |
| `field_changes` | `tuple[dict, ...]` | Sorted change records with `path`, `before`, `after`. |

### Change record format

Each entry in `field_changes` is a dict:

```python
{"path": "hot_stream.inlet_temperature", "before": 353.15, "after": 363.15}
{"path": "cold_stream", "before": "__MISSING__", "after": {...}}
```

- `path`: dot-separated path matching the canonical JSON structure
- `before`: canonical value from old revision (or `"__MISSING__"` for additions)
- `after`: canonical value from new revision (or `"__MISSING__"` for removals)

### `changed_paths` property

Returns a sorted tuple of just the path strings — useful for quick inspection.

### `is_identical` property

Returns `True` if `content_hash_before == content_hash_after` — useful for
detecting no-op revisions (same content, different metadata).

## CalculationRun invariants

The `CalculationRun` Pydantic model enforces status-dependent invariants
at construction time via `model_validator`:

| Status | Required fields | Prohibited fields |
|---|---|---|
| `SUCCEEDED` | `result_hash` (valid `sha256:<64-hex>`) | `failure` |
| `FAILED` | `failure` | — |
| `BLOCKED` | `blockers` (≥ 1) | — |
| Terminal (`SUCCEEDED/FAILED/BLOCKED/CANCELLED`) | `completed_at` > `started_at` | — |
| Non-terminal (`PENDING/RUNNING`) | — | `completed_at` must be `None` |

### `result_hash` format

Must match `sha256:<64 lowercase hex>` when present. `None` for non-SUCCEEDED
runs. No zero-sentinel placeholder.

### `schema_version`

Typed as `Literal["1.0"]` — only `"1.0"` is accepted.

## Repository deep-copy policy

All in-memory repositories store and return **deep copies**:

- `add()` stores a `copy.deepcopy()` of the entity.
- `get()` returns a `copy.deepcopy()` of the stored entity.
- `list_by_case()` / `list_by_revision()` return tuples of deep copies.

This guarantees callers cannot mutate repository state through retrieved objects.

## Repository identity-field protection

The `CalculationRun` repository `update()` rejects changes to immutable
identity fields:

- `case_id`, `case_revision_id`, `run_type`, `input_hash`
- `git_commit`, `software_version`, `schema_version`

Only mutable fields (`status`, `result_hash`, `failure`, `blockers`,
`completed_at`, `warnings`, `provenance_graph`) may change during updates.

## Repository protocol

```python
class DesignCaseRevisionRepository(Protocol):
    def add(self, revision: DesignCaseRevision) -> None: ...
    def get(self, revision_id: UUID) -> DesignCaseRevision: ...
    def latest(self, case_id: UUID) -> DesignCaseRevision | None: ...
    def list_by_case(self, case_id: UUID) -> tuple[DesignCaseRevision, ...]: ...

class CalculationRunRepository(Protocol):
    def add(self, run: CalculationRun) -> None: ...
    def get(self, run_id: UUID) -> CalculationRun: ...
    def update(self, run: CalculationRun) -> None: ...
    def list_by_revision(self, revision_id: UUID) -> tuple[CalculationRun, ...]: ...
```

## Related

- `src/hexagent/domain/revisions.py` — `DesignCaseRevision`, `RevisionDiff`,
  `CalculationRun`, error classes.
- `src/hexagent/domain/provenance.py` — `ProvenanceGraph`, `ProvenanceNode`,
  `ProvenanceNodeType` (includes RESULT, WARNING, BLOCKER).
- `src/hexagent/domain/messages.py` — `EngineeringMessage`, `ErrorCode` (StrEnum),
  `RunFailure`.
- `src/hexagent/core/canonical.py` — `canonical_json`, `sha256_digest`.
- `src/hexagent/application/revision_service.py` — `RevisionService`.
- `src/hexagent/application/run_service.py` — `RunService`.
- `src/hexagent/repositories/base.py` — Repository protocols.
- `src/hexagent/repositories/memory.py` — In-memory implementations.
