# TASK172 Stage-3 endpoint-hole low-side classification R3 correction

Task ID: `TASK172_V0_7_STAGE3_ENDPOINT_HOLE_LOW_SIDE_CLASSIFICATION_AUTHORITY_AND_R3_CORRECTION`
Mode: `STAGE3_NARROW_PRODUCTION_CLASSIFICATION_CORRECTION`
Predecessor HEAD: `38ab8db4d08ca93000197edb3efacd55a54043ec`

## Decision

This narrowly adds a production classification for the already-adjudicated case where the physical upper heat-rate cap is shell-capacity-bound and TASK172 at that upper endpoint returns a replay-valid `BLOCKED_RESIDUAL_ACCEPTANCE` result. After the existing bounded 12-level endpoint recovery completes, TASK173 classifies the trajectory as `_LowSideDomainInfeasible` only when at least one recovered point is a real, hash-replayed `Task172LocalResult`, every such point has `F(q) < 0`, and no sign pair or eligible root was found.

The endpoint hole itself remains signless and nonphysical. Neither its diagnostic iterate nor the adjudicated one-sided extrapolated limit is consulted by the production decision. The low-side meaning remains owned by `_solve_cell()`, which has the shell/tube capacity context; the generic endpoint-search helper reports structured depth exhaustion only.

All other cases remain outside this authority: lower-endpoint holes, tube-capacity binding, no valid recovery point, mixed/nonnegative recovery residuals, an eligible root or sign pair, any non-residual TASK172 blocker, any identity/hash failure, or any prior low-side probe. These continue through their existing behavior and fail closed.

## Targeted replay

The authorized target was replayed at `n=16`, outer iteration `2`, shell shooting enthalpy `106853.814770607445 J/kg`, support `(3,16,0)`, interval `[3.600,3.675] m`. The production upper bound remained `111.3949198456 W`; shell capacity was binding (`111.39491984560 W` versus tube capacity `54254.85383735592 W`). The upper TASK172 result remained the same replay-valid residual-acceptance hole as in the predecessor evidence.

The classification changed from `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED` to `LOW_SIDE_DOMAIN_INFEASIBLE`. TASK173 returned no partial mesh. Before classification, the target made exactly 14 TASK172 calls: 13 valid local results and one endpoint hole. All 12 recovery levels ran in the existing order, with the same q values, request hashes, result hashes, and negative `F(q)` values as the predecessor adjudication. No extra production probe was added.

The replay uses the authoritative wall-interface identity ending `a0a32e…`; the previously adjudicated historical transcription defect is not reintroduced into any new support or result identity.

## Frozen boundaries

- Cell-root authority: `V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R3`.
- Classification authority: `V07-T173-SHELL-CAPACITY-ENDPOINT-HOLE-LOW-SIDE-CLASSIFICATION-R1`.
- Search method/order and limits remain R2: valid-point-only local dyadic refinement, 12 levels, 15 brackets/cell, 360 recovery probes/cell, 128 root iterations, and 512 TASK172 evaluations/cell. Worst-case authorized evaluations remain 491.
- TASK172 acceptance, R98, and `C_round=1.0` are unchanged.
- TASK171, TASK174, property domain, and production mesh policy are unchanged.
- Full production mesh was not run; no TASK173 production result was created; mesh admission remains false; TASK175 was not run.

## Validation and lifecycle

The machine-readable companion records the exact trigger/non-applicability conditions, target replay identities and call counts, test results, and the append-only registry extension. Exact-head CI is required after the one R3 candidate commit and will be recorded in the PR metadata without a follow-up repository commit. This candidate is not self-approved; Ready and Merge remain unauthorized.

Next gate after candidate validation and exact-head CI: `STAGE3_PRODUCTION_MESH_REEXECUTION_FROM_N1_AFTER_R3`.
