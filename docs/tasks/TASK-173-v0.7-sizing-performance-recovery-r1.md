# TASK-173 v0.7 — Sizing performance recovery R1

**TASK_ID:** `V07_TASK173_SIZING_PERFORMANCE_RECOVERY_R1`  
**Baseline:** `84c5f38b74fd26eacefee260af7be26c12cb2e31`  
**Attempt 3:** terminated on Mac after 37h+ — **no final Sizing result** (not success evidence).

## Answers (audit)

1. **Hottest measured cost:** repeated CoolProp property work along the Task172/Task173 chain; per-mesh fresh `CoolPropProvider()` discarded LRU warmth (7× on `REVIEWED_MESH_SEQUENCE`). Full `_solve_outer_boundary(subdivisions=1)` exceeded 30s wall budget on Cursor Cloud (recorded `TIMEOUT`, not failure).
2. **Code changed:** shared mesh `CoolPropProvider` factory in `validate_request`; `TASK173_COOLPROP_CACHE_SIZE=2048` for default TASK173 providers; bounded benchmark + runner under `docs/tasks/evidence/`.
3. **Timing (proxy sample):** 7× `validate_request` per mesh-step pattern — baseline ~0.33s → optimized ~0.24s (~1.36×); cache hits 26 → 290 with identical Task172 `result_hash`.
4. **Hash parity:** `engineering_hash_match: true` on proxy sample; native shell replay `PASS`. Full Candidate B Rating replay **not** re-run here → `PRODUCTION_PARITY_PENDING`.
5. **Remaining for Sizing E2E:** bounded full-candidate Rating on capable host; hard-constraint filter + recommendation orchestration acceptance; observability/time limits for production Attempt 4.

**Raw JSON:** `docs/tasks/evidence/V07-TASK173-sizing-performance-recovery-r1-optimized-v2-20261011T232624Z.json`
