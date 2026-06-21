# Calculation Provenance

Structured traceability for every engineering calculation, linking inputs,
software versions, correlations, intermediate values and results in a
validatable directed acyclic graph.

## `CalculationRun` model

A `CalculationRun` is a frozen Pydantic model that records the execution of
one calculation against a specific design case revision.

### Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Schema version (`"1.0"`). |
| `run_id` | `UUID` | Unique run identifier. |
| `case_id` | `UUID` | Stable design case identifier. |
| `case_revision_id` | `UUID` | The immutable revision snapshot used as input. |
| `run_type` | `CalculationRunType` | One of: `VALIDATE`, `PROPERTIES`, `SCREEN`, `SIZE`, `RATE`, `OPTIMIZE`, `REPORT`. |
| `status` | `CalculationRunStatus` | Current state (see state machine below). |
| `started_at` | `datetime` | Timestamp when the run was created/started (UTC). |
| `completed_at` | `datetime \| None` | Timestamp when the run reached a terminal state (UTC). |
| `software_version` | `str` | Semantic version of the engine (e.g. `"0.1.0"`). |
| `git_commit` | `str` | Git commit hash at the time of execution. |
| `input_hash` | `str` | Content hash of the input revision (`sha256:...`). |
| `result_hash` | `str` | Content hash of the result payload (set on success). |
| `property_backend` | `dict[str, Any] \| None` | Which property provider was used (e.g. `{"provider": "coolprop", "version": "6.6.0"}`). |
| `correlation_records` | `tuple[dict, ...]` | Correlation IDs and versions consumed during the run. |
| `warnings` | `tuple[EngineeringMessage, ...]` | Non-fatal warnings that did not stop execution. |
| `blockers` | `tuple[EngineeringMessage, ...]` | Fatal blocking messages that prevented a result. |
| `failure` | `RunFailure \| None` | Structured failure record (set on `FAILED`). |
| `provenance_graph` | `ProvenanceGraph` | DAG linking all inputs, intermediates and outputs. |

### Immutability

Like `DesignCaseRevision`, `CalculationRun` is frozen (`frozen=True`).
State transitions return a **new** instance via `model_copy(update=...)`.
The previous state is never mutated.

## State machine

```
                 ┌──────────────────────────────────────────┐
                 │                                          ▼
              ┌──────┐    start    ┌─────────┐    ┌──────────────┐
              │PENDING│──────────▶│ RUNNING │───▶│   SUCCEEDED   │
              └──┬───┘            └────┬────┘    └──────────────┘
                 │                     │
                 │          ┌──────────┼──────────┐
                 │          ▼          ▼          ▼
                 │     ┌────────┐ ┌────────┐ ┌──────────┐
                 │     │ FAILED │ │BLOCKED │ │CANCELLED │
                 │     └────────┘ └────────┘ └──────────┘
                 │                     ▲
                 └─────────────────────┘
                   cancel (from PENDING)
```

### Legal transitions

| From | To | Trigger |
|---|---|---|
| `PENDING` | `RUNNING` | Execution begins. |
| `PENDING` | `CANCELLED` | Run cancelled before start. |
| `RUNNING` | `SUCCEEDED` | Calculation completes with valid result. |
| `RUNNING` | `FAILED` | Unrecoverable error during execution. |
| `RUNNING` | `BLOCKED` | Engineering blocker prevents a result. |
| `RUNNING` | `CANCELLED` | Execution cancelled mid-run. |

All other transitions are illegal and raise `InvalidStateTransitionError`.

## `EngineeringMessage`

Structured messages attached to a `CalculationRun`. Each message carries a
severity and a continuation policy.

### Severity levels

| Severity | `allows_continuation` | Effect |
|---|---|---|
| `INFO` | `true` | Informational; logged but does not affect flow. |
| `WARNING` | `true` | Non-fatal; run continues, warning is recorded. |
| `ERROR` | `false` | Fatal; run transitions to `FAILED`. |
| `CRITICAL` | `false` | Fatal; run transitions to `FAILED`. |

### Fields

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Schema version. |
| `code` | `str` | Stable error code (e.g. `"property_out_of_range"`). |
| `severity` | `EngineeringMessageSeverity` | `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. |
| `message` | `str` | Human-readable description. |
| `source_module` | `str` | Module that generated the message. |
| `affected_paths` | `tuple[str, ...]` | Dot-separated paths of affected fields. |
| `context` | `dict[str, Any]` | Arbitrary structured context. |
| `allows_continuation` | `bool` | Whether execution may proceed. |

### Semantic distinction: warning vs blocker vs error

- **Warning** (`allows_continuation=True`): the calculation produced a
  useful result but flagged an applicability concern, extrapolation or
  soft limit. The run still succeeds.
- **Blocker** (`allows_continuation=False`, severity `WARNING` or `ERROR`):
  engineering constraints prevent a valid result. The run transitions to
  `BLOCKED`. Example: missing required input, applicability envelope
  violated.
- **Error** (`allows_continuation=False`, severity `ERROR` or `CRITICAL`):
  an unrecoverable failure during execution (exception, convergence
  failure). The run transitions to `FAILED` and a `RunFailure` record is
  attached.

## `RunFailure`

Attached to a `CalculationRun` when the run reaches the `FAILED` state.

| Field | Type | Description |
|---|---|---|
| `schema_version` | `str` | Schema version. |
| `code` | `str` | Stable error code (e.g. `"calculation_not_converged"`). |
| `message` | `str` | Human-readable failure description. |
| `traceback` | `str \| None` | Optional Python traceback (stripped of sensitive paths). |
| `context` | `dict[str, Any]` | Structured context (e.g. iteration count, residual). |

## `ProvenanceGraph` — DAG structure

The provenance graph is a directed acyclic graph (DAG) that links every
input, intermediate computation, correlation, property call, result,
warning and blocker involved in a calculation run.

### Node types

| `ProvenanceNodeType` | Description |
|---|---|
| `CASE_REVISION` | Input design case revision snapshot. |
| `INPUT_FILE` | External input file or data source. |
| `CALCULATION_RUN` | The run itself (top-level node). |
| `CORRELATION` | A registered correlation used in the calculation. |
| `PROPERTY_CALL` | A fluid-property provider call. |
| `EXCHANGER_SERVICE` | An exchanger sizing/rating service invocation. |
| `OPTIMIZER` | An optimization loop invocation. |
| `REPORT` | A generated report artifact. |
| `EXTERNAL` | An external dependency or third-party call. |

### Node structure

| Field | Type | Description |
|---|---|---|
| `node_id` | `UUID` | Unique node identifier. |
| `node_type` | `ProvenanceNodeType` | Category of provenance node. |
| `label` | `str` | Human-readable label. |
| `metadata` | `dict[str, Any]` | Arbitrary structured metadata. |

### Edge structure

| Field | Type | Description |
|---|---|---|
| `source_id` | `UUID` | Source node (upstream). |
| `target_id` | `UUID` | Target node (downstream). |
| `relation` | `str` | Edge label (e.g. `"used_by"`, `"produced_by"`). |
| `metadata` | `dict[str, Any]` | Arbitrary structured metadata. |

### Direction convention

Edges point from **upstream** to **downstream**:

```
CASE_REVISION ──used_by──▶ CALCULATION_RUN ──produced_by──▶ RESULT
     │                          │
     │                     used_by
     │                          │
     │                          ▼
     │                     CORRELATION
     │
     └────used_by──▶ PROPERTY_CALL
```

### Validation rules

The `ProvenanceGraph` validates on construction (Pydantic `model_validator`):

1. **Unique node IDs**: no two nodes may share a `node_id`.
2. **Edge endpoint existence**: every `source_id` and `target_id` must
   reference an existing node.
3. **No self-loops**: an edge may not connect a node to itself.
4. **Acyclic (DAG)**: verified via Kahn's topological sort. If any node is
   not visited, the graph contains a cycle and validation fails.
5. **At least one `CASE_REVISION`**: when the graph contains any nodes, at
   least one must be of type `CASE_REVISION`. This ensures every
   provenance trace is anchored to a concrete input.

## Git commit and software version tracking

Every `CalculationRun` records:

- **`software_version`**: the semantic version of the calculation engine
  at the time of execution (e.g. `"0.1.0"`). This is read from the
  package metadata or a version file.
- **`git_commit`**: the full 40-character SHA-1 commit hash (or short hash)
  of the repository at build time.

Together these ensure that a run can be reproduced by checking out the
exact code version that produced it.

## Property backend and correlation usage placeholders

The `CalculationRun` model includes two fields for tracking which external
dependencies were used:

### `property_backend`

```python
property_backend: dict[str, Any] | None = None
# Example:
# {"provider": "coolprop", "version": "6.6.0", "fluid": "water"}
```

Records which property provider was active and its version. This is a
placeholder for future structured property-backend provenance.

### `correlation_records`

```python
correlation_records: tuple[dict[str, Any], ...] = ()
# Example:
# ({"correlation_id": "HTC-DP-001", "version": "1.2", "applicability": "VALID"},)
```

Records which registered correlations were consumed during the run. Each
entry includes the correlation's stable ID, version and applicability
verdict. This is a placeholder for the full correlation registry
integration (see `TASK-004-correlation-registry`).

## Result hash for successful runs

When a run succeeds (`status == SUCCEEDED`), the `result_hash` field is
set to the SHA-256 content hash of the serialised result payload:

```
sha256:<64-char lowercase hex>
```

This allows:

- **Diff detection**: compare two runs by their `result_hash` to detect
  whether the output changed.
- **Reproducibility verification**: re-run the calculation and confirm
  the same `result_hash` is produced.
- **Tamper detection**: any post-hoc modification to stored results
  is detectable.

The default value (`sha256:000...000`) is a sentinel indicating "no result
yet". The `RunService.verify_run_integrity` method rejects this sentinel
for `SUCCEEDED` runs.

## Audit and reporting use cases

### Audit trail

1. List all revisions for a case → `repo.list_by_case(case_id)`.
2. For each revision, recompute `content_hash` and compare to stored value.
3. List all runs for a revision → `repo.list_by_revision(revision_id)`.
4. Verify each run's `input_hash` matches the revision's `content_hash`.
5. Walk the `ProvenanceGraph` to confirm all nodes and edges are valid.

### Reporting

- Attach `CalculationRun.to_json()` to any engineering report.
- Render `ProvenanceGraph` as a visual DAG (e.g. via Graphviz or Mermaid).
- Include `software_version` and `git_commit` in report headers for
  reproducibility metadata.

### Compliance

- Immutable revisions satisfy audit-trail requirements for quality
  management systems (ISO 9001, ASME BPVC).
- `EngineeringMessage` severity and continuation flags provide a structured
  record of engineering judgment.
- `RunFailure` captures failure context without leaking sensitive data.

## Related

- `src/hexagent/domain/revisions.py` — `CalculationRun`, `CalculationRunStatus`,
  `CalculationRunType`, `DesignCaseRevision`, `RevisionDiff`.
- `src/hexagent/domain/provenance.py` — `ProvenanceGraph`, `ProvenanceNode`,
  `ProvenanceEdge`, `ProvenanceNodeType`.
- `src/hexagent/domain/messages.py` — `EngineeringMessage`, `RunFailure`,
  `ErrorCode`.
- `src/hexagent/application/run_service.py` — `RunService` with lifecycle
  management.
- `docs/DESIGN_CASE_REVISIONS.md` — Design case revision design document.
