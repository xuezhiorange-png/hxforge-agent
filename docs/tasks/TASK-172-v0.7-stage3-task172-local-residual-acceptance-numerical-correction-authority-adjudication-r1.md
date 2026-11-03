# TASK172 local residual-acceptance numerical correction authority adjudication R1

**Task:** `STAGE3_TASK172_LOCAL_RESIDUAL_ACCEPTANCE_NUMERICAL_CORRECTION_AUTHORITY_ADJUDICATION_R1`
**Mode:** numerical-profile diagnostic and authority adjudication only
**Result:** `BLOCKED_ADDITIONAL_NUMERICAL_OBSERVABILITY_REQUIRED`
**Source head:** `adcc4c6f4fbf0ba335d80f7a1322ae6515b0fb0b`
**PR:** #283, OPEN / Draft

## Decision

No solver-control correction is authorized by this evidence. The exact n=32 request reproduces under frozen R94 and R98, and a diagnostic dogbox solution can satisfy the unchanged R98 bounds. But the requested fail-only TRF polishing path recovers only five of six residual-acceptance holes; the global dogbox profile recovers all six locally but causes one of thirteen baseline-valid requests in the targeted n=16 preservation corpus to fail R98. Neither architecture has Linux Python 3.11/3.12 candidate-profile evidence, a representative n=8 plus accepted n=16 corpus, or a production-bounded work authority.

Accordingly, this is not a finding that no numerical solution exists. It is a finding that no safe, portable, bounded numerical authority candidate has been established. R98 remains the acceptance authority; TASK172 correctly fails closed when its result misses an R98 operation bound.

## Frozen profile and exact baseline replay

The request is an ordinary nonzero-temperature-difference constitutive solve. TASK173's trial value is `q=0 W`, but TASK172 sees bulk temperatures 299.10292032837447 K and 298.23776708036274 K (`ΔT=0.86515324801173 K`) and solves an internal constitutive heat rate near 281.708252911 W. The TASK172 exact-zero-duty branch is not triggered.

The independently replayed request hash is `3ffebffa5aaf4957cd4d743e8530885795831d29328b5a2fc63e55287d08720d`; the blocked result hash is `779109c08d8885c7e85b1ece0bdd0b7fb7e9f5d00a7818e5b95c8b282e2402e5`. Both match the supplied target. SciPy returned `success=true`, status 3, after `nfev=4`, `njev=4`, and 16 residual callbacks. The observed termination was `xtol`, not `ftol` or `max_nfev`.

At that iterate, the inner-film residual is 7.713651939411648e-11 W against its original R98 bound 6.892011134130622e-11 W: an excess of about 8.2164e-12 W and a ratio of about 1.1192164. Wall and outer-film residuals pass. The solver's normal tolerance-based success therefore does not imply R98 acceptance; no R98 threshold, ULP formula, or `C_round=1.0` was changed.

## Replayed n=32 outer-trial holes

A fresh targeted replay of n=32, outer iteration 23, reproduced the same lower-endpoint unresolved-bracket blocker and the 12-level recovery behavior. Instrumentation wrapped the existing validator only to capture request/result objects; it did not add or reorder production probes. It recorded 4,617 TASK172 calls: 4,611 `Task172LocalResult` evaluations and six `BLOCKED_RESIDUAL_ACCEPTANCE` holes, with no other non-valid TASK172 outcomes. The existing production recovery had eleven valid samples, no eligible root, and no sign pair.

The six request hashes, blocked-result hashes, trial-q values, and physical supports are preserved in the adjacent JSON evidence. In particular, the additional interior hole at `q=1834.90115580185 W` remains part of the same failed outer trial and was not omitted from the solver comparison.

## Numerical profile matrix

The same six captured requests were tested with the same constitutive equations, provider, and original R98 bound calculation. Counts were identical under macOS Python 3.11.15, 3.12.13, and 3.14.5; this is local Python-version characterization, not Linux portability evidence.

| Diagnostic profile | Six holes satisfying original R98 | Observation |
|---|---:|---|
| Frozen R94 baseline | 0/6 | Exact residual-acceptance failures reproduced |
| More work only (`max_nfev=128`, callback cap 512) | 0/6 | Still terminates by the existing `xtol`/`gtol` conditions; no improvement |
| Disable `ftol`, more work | 0/6 | Same result; `ftol` was not the observed termination cause |
| 3-point finite difference | 3/6 | Does not recover q=0 or two other holes |
| Smaller finite-difference step (`1e-6`) | 4/6 | Two holes remain; changing differencing alone is insufficient |
| Fail-only TRF residual polish from baseline final iterate | 5/6 | q=0 remains blocked under unchanged R98 |
| Fail-only dogbox polish from baseline final iterate, default tolerances | 4/6 | Two holes remain |
| Fail-only dogbox polish from baseline final iterate, stricter tolerances | 5/6 | q=0 remains blocked |
| Global dogbox reference profile | 6/6 | All six diagnostic vectors meet original R98 locally |
| High-convergence 3-point reference | 5/6 | q=0 remains blocked |

The dogbox reference solution for the q=0 request is numerically adjacent to the baseline iterate (maximum six-hole deltas: 3.9563e-11 W in q and 5.6844e-14 K in either wall temperature) and its diagnostic residual vector is within all three original R98 bounds. The harness did not emit a production `Task172LocalResult`; this establishes a locally observed numerical point, not a production acceptance or identity.

## Preservation and historical n=16 effect

The fresh n=16 outer-iteration-2 targeted replay captured thirteen baseline-valid native TASK172 requests at the historical upper-endpoint support. A global dogbox solve passed R98 for twelve of those thirteen. For request `fd9287e7200cc1fa723ecfeef31067d907a484bf18558b05a8488e5ed6e90cb9`, baseline R94 passes all three R98 operations, while global dogbox's inner residual is 2.2737367544323206e-10 W against a 1.3824186390852612e-10 W bound. This is a newly introduced blocker under global profile substitution. Fail-only polishing does not re-enter those thirteen valid requests, so it preserves them by construction, but it still misses the n=32 q=0 hole.

For the historical n=16 upper endpoint, the frozen baseline remains a residual-acceptance hole. Diagnostic strict dogbox and global dogbox produce R98-valid numerical vectors with `q_TASK172≈703.6847988974 W`, so `F(q)=q_trial-q_TASK172≈-592.289879 W`. If such a candidate were materialized as a valid result, the existing valid-upper shell-capacity path would classify it low-side; the R3 endpoint-hole trigger would simply not apply. The R3 authority itself was not changed. The diagnostic extrapolation or internal blocked iterate was not used as a physical result.

The targeted thirteen-request preservation corpus is not a substitute for the required broader corpus: valid requests from the n=8 convergence path and accepted n=16 convergence path were not captured in this adjudication.

## Authority and next step

R94 is a reviewed solver-profile authority, so changing its method, finite-difference settings, tolerances, evaluation ceilings, or adding a polishing stage would require a new numerical-profile authority. R98 stays independent and unchanged. No production work cap was approved from these diagnostics.

The narrow next *diagnostic/adjudication* gate is `STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_PORTABILITY_AND_VALIDITY_ADJUDICATION_R1`: test an explicitly bounded failure-only alternate-solver fallback (distinct from the tested baseline-final-iterate TRF polish), materialize/replay actual Task172 results, expand the baseline-valid corpus with n=8 and accepted n=16 samples, and obtain Linux Python 3.11/3.12 candidate-profile evidence. This document does not authorize implementing that gate.

## Change boundary and validation

No production source, tests, workflows, dependencies, lockfile, registry, mesh policy, R94, R98, TASK173 root equation, or R3 rule changed. No production mesh, TASK173 production result, or TASK175 acceptance was executed. The repository remains Draft; Ready and Merge are unauthorized.

Local validation: the focused TASK172/TASK173 files passed (66 tests); the full shell-tube suite passed (2,252 passed, 2 skipped; 2,254 collected). HTTP/API regression passed (21 tests). Ruff, formatting, mypy CI scope, manifest D==M, pip-audit, lock check, and locked all-extras sync passed. The evidence JSON duplicate-key audit found none. `uv.lock` SHA-256 remains `4783f2a07cd28b5a5c46402101f0570d3060f464fe850c63fc7ad5e069e68464`; locked versions remain urllib3 2.8.0 and requests 2.34.2. Exact-head CI is pending the evidence-only commit.

Machine-readable observations, diagnostic-output checksums, and validation results are in [`TASK-172-stage3-task172-local-residual-acceptance-numerical-correction-authority-adjudication-r1.json`](evidence/TASK-172-stage3-task172-local-residual-acceptance-numerical-correction-authority-adjudication-r1.json).
