# Minimal production hook integration (future — not implemented in baseline)

## Design principle

Inject an optional `TelemetryListener` protocol into TASK173 **orchestration only**. Default: `None`. Listener receives event copies; **return values ignored**. Wrap all listener calls in `try/except` so `OSError` / `TelemetryLogCapacityExceeded` never alters solver control flow.

```python
class TelemetryListener(Protocol):
    def on_progress(self, event: ProgressEvent) -> None: ...
```

Register via `ContextVar` (`_TASK173_TELEMETRY_LISTENER`), set only by CLI/wrapper — **never** by request models.

## Files to touch (minimal diff)

| File | Change |
|------|--------|
| `task173_integrated_rating/service.py` | After `_CellSearchStats.record_evaluation()`, call `listener.record_task172_evaluations(1, …)` (batched writer). Mesh / outer / cell boundaries: boundary events only. `validate_candidate_rating` entry/exit: `candidate_*`, `session_*`. |
| `task173_integrated_sizing/service.py` | Optional `candidate_started` before `validate_candidate_rating`. |
| `hexagent/cli/` or evidence runners | Attach `TelemetryWriter` + policy. |
| **No** changes to `task172_local_runtime`, hash functions, request schemas, search limits, R2A. |

## Production integration risks

| Risk | Mitigation |
|------|------------|
| Per-Task172 JSONL line → disk exhaustion | Use `record_task172_evaluations` batching; cap `max_jsonl_lines`. |
| Telemetry exception aborts solve | Catch all telemetry errors at hook boundary; never re-raise into kernel. |
| Listener mutates shared state read by solver | Listener is write-only side channel; no reads from solver. |
| Mistaking log recovery for checkpoint | Document + code comments; no resume API. |
| Hash drift if telemetry fields leak into models | Forbidden fields test; no telemetry in `model_dump` for requests/results. |

## Regression tests (production phase)

1. **Identity unchanged** — full existing TASK173/Task172 pytest with listener `None`.
2. **Candidate B SUCCESS** — frozen `candidate_rating_result_hash` **`1cecb402cc44ec2690918b3479cf6c7e4e1079eb290835122ad53ddfce657743`** (`FROZEN_IDENTITY_REFERENCES.md`); listener on/off triple-run equality.
3. **Blocked receipt (separate case)** — `fa9030a7…` only for cell-root adjudication blocked fixture, not success regression.
4. **Telemetry isolation** — sizing/rating hash tests unchanged when JSONL path set.
5. **Prototype tests** — `test_telemetry_prototype.py` in optional CI shard.

## Deterministic identity regression (post-hook)

1. **Reference Rating** — committed evidence replay; hash unchanged with telemetry enabled.
2. **Candidate B success** — `1cecb402…` per `TASK-173-v0.7-full-sizing-reference-plane-serialization-candidate-ratings-r1.json`.
3. **Telemetry** — schema/summary only; never in engineering golden files.

## External OS monitoring

Wrapper emits `os_sample` / `wrapper_abnormal_exit` with rate policy; independent of solver hooks.
