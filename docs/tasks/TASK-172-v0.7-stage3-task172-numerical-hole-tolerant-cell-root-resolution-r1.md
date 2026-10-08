# TASK172 Stage-3 cell-root contract resolution R2

**Task:** `TASK172_V0_7_STAGE3_INTEGRATED_RATING_CONTRACT_RESOLUTION_R2`
**Mode:** `STAGE3_TASK173_CONTRACT_REPAIR_ONLY`
**Predecessor:** `44033be35eddaf2d10b3c68c24aadccdd3126c35`
**PR:** #283 — remains Draft

## Resolution

R2 corrects two Stage-3 integration-contract defects without changing TASK172, R98, C_round, any engineering authority, or the production mesh policy. The historical n=2 q trial is now an environment characterization, not a portable invariant. The cell-root authority now uses local bounded searches and a budget proof compatible with the unchanged 512 TASK172-evaluation cap.

The production mesh sequence was **not** executed in R2. No mesh admission or TASK173 result identity is created here. The candidate remains pending exact-head CI and the owner's review before any production-mesh rerun.

## Historical n=2 classification

Historical input: `n=2`, physical interval `[4.8, 6.0] m`, subdivision `0`, `q=4436.3679921671355 W`.

`HISTORICAL_N2_CLASSIFICATION_PORTABLE=false`. The predecessor observations differ by environment: the local observation was `BLOCKED_RESIDUAL_ACCEPTANCE`; PR-head and merge-ref Linux Python 3.11 and 3.12 observed a valid `Task172LocalResult`. Neither outcome is a portable contract assertion. The regression now allows either classification and checks that the cell solver does not force a hole when TASK172 returns valid, while a blocked residual-acceptance result follows only the valid-point recovery path.

A separate injected contract test constructs a validly hashed `Task172BlockedResult(BLOCKED_RESIDUAL_ACCEPTANCE)`. The block produces no Stage-3 residual, sign, or physical result. Non-residual blockers and invalid blocked-result identities remain hard failures. The focused native characterization also confirms any successful cell result is a real validated `Task172LocalResult`.

## R2 cell-root authority

Authority candidate: `V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R2`.

- Equation unchanged: `F(q)=q-q_TASK172(q)`; closure tolerance `1e-6 W`.
- Method: `VALID_POINT_ONLY_LOCAL_DYADIC_BRACKET_REFINEMENT`.
- A numerical hole has no sign or residual and is never a result. Blocked diagnostics and `diagnostic_last_iterate` are never used.
- At most two local midpoint probes are made per level, approaching the hole from its valid left/right anchors; search depth is 12. No exponential full-bracket scan remains.
- Maximum hole-recovery brackets per cell: 15; maximum recovery probes per cell: 360. Root bisection is capped at 128 evaluations, with two endpoints and one conservative final-verification reserve.
- Worst-case authorization arithmetic: `2 + 128 + 360 + 1 = 491 <= 512`. The TASK172 evaluation cap remains 512 and every exceeded limit fails closed with `BLOCKED_CELL_ROOT_RESOURCE_EXHAUSTION`.
- Only exact, hash-replayed `Task172LocalResult` outputs contribute `F(q)`. The existing outer feasibility-boundary solver is unchanged.

Resource-blocker diagnostics retain mesh subdivisions, physical support and paired cell/wall IDs, outer iteration, shooting enthalpy, bracket endpoints and residuals, search level, total/valid/hole evaluation counts, hole codes, and last valid bracket width. Partial trajectories remain non-authoritative.

## Change and validation boundary

TASK172 production acceptance logic: unchanged. R98 `C_round=1.0`: unchanged. TASK171, TASK174, real-case mesh thresholds/cap, dependencies, lockfiles, and workflows: unchanged. TASK175 is not run; Ready and Merge remain unauthorized.

Validation performed before candidate commit: focused TASK173 tests, full shell-tube suite, Ruff, formatting, mypy, manifest D==M, lock check, pip-audit, duplicate-key audit, and `git diff --check`. The exact-final-head CI run is recorded in the closeout receipt for the committed candidate; predecessor run `36586943815` remains failure evidence only.

**R2 status:** contract repair candidate only; production mesh execution prohibited until this repair receives a successful exact-head CI result and owner review. `REAL_CASE_MESH_ADMISSIBLE=false`.
