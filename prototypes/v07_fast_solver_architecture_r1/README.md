# V07 Task172/173 Fast Solver Architecture R1

Coupled per-cell nonlinear solve (Route A/B hybrid): eliminates outer cell-root
bracketing when the coupled TRF closure succeeds.

## Run

```bash
.venv/bin/python prototypes/v07_fast_solver_architecture_r1/benchmark.py \
  --output docs/tasks/evidence/V07-TASK172-TASK173-fast-solver-architecture-r1-<UTC>.json
```

Budget: 120s per mesh case, subdivisions 1/2/4, frozen Candidate B context with
shooting enthalpy at 50% of `[H_MIN, H_MAX]`.

## Authority

See `AUTHORITY_CANDIDATE.md`. Production Task172/173 unchanged.
