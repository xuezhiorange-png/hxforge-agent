# V07_TASK173_NONINTRUSIVE_TELEMETRY_R1 — Progress Event Contract

**Status:** Prototype only (non-production).  
**Baseline:** `84c5f38b74fd26eacefee260af7be26c12cb2e31`

## Non-goals (hard boundary)

Telemetry records are **observability only**. They must **never** be read by:

- `Task173SizingRequest` / `CandidateRatingRequest` validation or hashing
- outer/cell root convergence or acceptance
- `candidate_rating_result_hash`, `recompute_task173_result_hash`, `sizing_request_hash`, or any Task172 identity hash
- provenance nodes attached to engineering results

If a future hook writes telemetry, it must use a **side channel** (contextvar / injected listener) with **no return value** consumed by solvers.

## Event envelope (every line)

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schema_version` | string | yes | `task173.telemetry.progress-event.v1` |
| `telemetry_run_id` | string | yes | UUID; not tied to `request_hash` |
| `sequence` | int | yes | Monotonic per run; used for recovery |
| `emitted_at_utc` | string | yes | ISO-8601 UTC |
| `source` | string | yes | `external_os` or `solver_internal` |
| `event_type` | string | yes | See below |
| `elapsed_monotonic_s` | number | yes | Seconds since run `session_start` |
| `payload` | object | yes | Type-specific; never mixed into canonical JSON |

Optional correlation (informational only):

| Field | Type | Notes |
|-------|------|-------|
| `sizing_request_hash` | string | Copy for log correlation; **not** an input to telemetry validation |
| `candidate_id` | string | |
| `candidate_hash` | string | |
| `mesh_subdivisions` | int | |
| `outer_iteration` | int | |
| `physical_support_id` | string | Cell / support identity for humans |
| `cell_root_phase` | string | e.g. `PHYSICAL_ENDPOINT_EVALUATION`, `CELL_ROOT_BISECTION_MIDPOINT` |

## `source` semantics

### `external_os`

Collected **outside** the engineering kernel (agent wrapper, shell, `/proc`, `psutil`, cgroup readers). Examples:

- `os_sample` — CPU%, RSS, disk free, load average
- `session_heartbeat` — wrapper alive tick
- `wrapper_abnormal_exit` — SIGTERM, OOM killer, agent timeout (inferred)

No access to `_CellSearchStats`, shooting enthalpy, or Task172 requests.

### `solver_internal`

Collected **inside** TASK173 orchestration hooks (future production). Examples:

- `candidate_started` / `candidate_finished`
- `mesh_started` / `mesh_finished`
- `outer_iteration_started` / `outer_iteration_finished`
- `cell_root_started` / `cell_root_finished`
- `task172_evaluation_recorded` — increments official counter mirror

Must be emitted **after** the numerical step completes (or fails), never altering control flow.

## `event_type` catalog (solver_internal)

| event_type | payload highlights |
|------------|-------------------|
| `session_start` | `host`, `python_version`, `baseline_git` |
| `session_end` | `status`: `completed` \| `aborted` \| `failed` |
| `candidate_started` | `candidate_index`, `candidate_id`, `candidate_hash` |
| `candidate_finished` | `outcome`: `success` \| `blocked` \| `error`, `candidate_rating_result_hash` (if known) |
| `mesh_started` | `mesh_index`, `mesh_subdivisions` |
| `mesh_finished` | `task172_local_evaluation_count`, `task172_numerical_hole_count` |
| `outer_iteration_started` | `outer_iteration`, `shooting_enthalpy_j_kg` (string decimal) |
| `outer_iteration_finished` | `classification` |
| `cell_root_started` | `physical_support_id`, `mesh_subdivisions`, `outer_iteration` |
| `cell_root_finished` | `task172_evaluations_this_cell`, `closure_mode` |
| `task172_evaluation_recorded` | `increment`: 1, `cumulative_task172` (prefer batched mode in production) |
| `task172_batch_progress` | `evaluations_in_batch`, `cumulative_task172` (default high-frequency path) |

## Write-rate policy (disk safety)

`TelemetryWritePolicy` (prototype defaults):

- `task172_detail_every_n`: emit `task172_batch_progress` at most every N evaluations (in-memory counter stays exact).
- `recovery_every_n_events`: rewrite `.recovery.json` every N persisted lines (plus session end).
- `os_sample_min_interval_s`: suppress redundant `external_os` samples.
- `max_jsonl_lines`: hard cap; raises `TelemetryLogCapacityExceeded` (**telemetry only** — must be caught by wrapper).

**Log recovery** rebuilds observability summaries from JSONL; it is **not** solver checkpoint resume (see `LOG_RECOVERY_NOT_CHECKPOINT.md`).

## `event_type` catalog (external_os)

| event_type | payload highlights |
|------------|-------------------|
| `os_sample` | `cpu_percent`, `memory_rss_mb`, `memory_available_mb`, `disk_free_gb` |
| `session_heartbeat` | `wrapper_tick` |
| `wrapper_abnormal_exit` | `reason`, `last_sequence_recovered` |

## JSONL storage

- One JSON object per line, UTF-8, `sort_keys=True` on write (stable for diffing).
- Path convention: `{artifact_dir}/task173_telemetry_{telemetry_run_id}.jsonl`
- Summary: `{artifact_dir}/task173_telemetry_{telemetry_run_id}.summary.json`
- Recovery checkpoint: `{artifact_dir}/task173_telemetry_{telemetry_run_id}.recovery.json` (last durable `sequence`)

## Aggregation summary (derived only)

`summary.json` fields:

- `telemetry_run_id`, `schema_version`, `recovered_from_sequence`
- `counts_by_event_type`, `cumulative_task172_max`
- `candidates_started`, `candidates_finished`
- `mesh_levels_observed`, `outer_iterations_observed`
- `wall_elapsed_s`, `abnormal_termination`: bool

Summaries are **never** hashed into engineering results.
