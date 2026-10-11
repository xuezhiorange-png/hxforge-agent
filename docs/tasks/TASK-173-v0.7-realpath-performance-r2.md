# TASK-173 v0.7 — Realpath performance R2

**TASK_ID:** `V07_TASK173_REALPATH_PERFORMANCE_R2`  
**Parent:** `bdd6d16` (R1)

## Findings (verified)

| Question | Answer |
|----------|--------|
| R1 Reference vs Candidate | **Reference** `validate_request`: R1 fixes per-mesh fresh `CoolPropProvider`. **Candidate** `validate_candidate_rating`: already shared one provider; R1 only raised default cache to 2048. |
| Cache stats | R1 benchmark corrected to **cumulative** `cache_info` over all provider instances per scenario. |
| Realpath hotspot (Candidate B, n=1, 60s TIMEOUT) | **Task172** dominates: 630× `task172_validate_candidate`, 344 counted evaluations, 37× `_solve_cell`, 11× `_outer_trial`. CoolProp cache saturated at 2048 entries under load. |
| Cache 256 vs 2048 (25s partial) | Throughput ~5.88 vs ~5.60 Task172 eval/s (not a clear win); 2048 held 2048 entries vs 256 capped; 256 run hit `BLOCKED_TASK172_LOCAL_CONSTITUTIVE_CLOSURE` (different partial trajectory — not parity comparison). |
| Code optimization | **None shipped** — hotspot is Task172 constitutive closure volume; no safe execution-only change identified without touching Task172/R2A. |
| Rating PASS | **Never claimed** — all runs `rating_solve_completed=false`; TIMEOUT is budget exhaustion only. |

**Raw JSON:** `docs/tasks/evidence/V07-TASK173-realpath-performance-r2-20261011T234200Z.json`
