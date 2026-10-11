# Log recovery ≠ solver checkpoint resume

## What this prototype provides

- **Telemetry log recovery:** Re-read JSONL + optional `.recovery.json` to rebuild **observability summaries** (`aggregate_events`, `recover_from_log`) after a wrapper crash or partial write.
- **Purpose:** Operator visibility (counts, last sequence, abnormal flag). **Not** engineering state.

## What is explicitly NOT supported

- **No breakpoint resume** of TASK173 outer boundary, cell root, mesh sequence, or Task172 evaluations.
- **No** restoration of shooting enthalpy, `trials` maps, R2A certificates, or `CandidateLedgerEntry` from telemetry files.
- **No** claim that Cursor Cloud cross-session **solver** continuity is enabled by this R1 prototype.

Solver checkpointing was **paused** per program decision; telemetry R1 must not be described as a substitute.

## Production wording (required)

Use: *"telemetry log recovery for progress display only"*.  
Avoid: *"checkpoint resume"*, *"断点续算"*, *"recoverable solve"* unless a future authorized solver-state authority exists.
