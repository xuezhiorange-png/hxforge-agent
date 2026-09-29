# TASK172 Stage-3 valid-point cell-root resolution

**Task:** `TASK172_V0_7_STAGE3_TASK172_NUMERICAL_HOLE_TOLERANT_CELL_ROOT_RESOLUTION_R1`
**Result:** `STAGE3_BLOCKED_INTEGRATED_RATING_CONTRACT`
**Predecessor:** `0e633ed555bc404ab7e43fe632234c0807eaf7a3`
**PR:** #283 — remains Draft

## Outcome

The Stage-3 cell solver now brackets and refines roots using only valid native TASK172 evaluations. The exact historical n=2 trial still returns `BLOCKED_RESIDUAL_ACCEPTANCE`; Stage-3 classifies that isolated intermediate evaluation as a numerical hole, excludes all of its diagnostics from root-sign decisions, and obtains a valid native TASK172 cell result through neighboring valid points. TASK172 acceptance and R98 remain unchanged (`C_round=1.0`).

The production sequence was restarted at n=1. Meshes n=1, 2, 4, and 8 completed. At n=16, one cell reached the authorized 512 TASK172-evaluation cap and returned `BLOCKED_CELL_ROOT_RESOURCE_EXHAUSTION`. The cap was not raised; n=32 and n=64 were not run. Consequently there is no completed convergence/headroom decision and no production-mesh admission.

## Numerical-hole contract

Authority candidate: `V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R1`.

- Method: `VALID_POINT_ONLY_DYADIC_BRACKET_REFINEMENT`.
- A valid point requires a hash-replayed `Task172LocalResult` and the ordinary physical/state guards.
- Only `BLOCKED_RESIDUAL_ACCEPTANCE`, after independent input preflight and blocked-result identity replay, is treated as `TASK172_NUMERICAL_HOLE`.
- A hole contributes no q value, residual, sign, wall state, or accepted result. Other TASK172 failures remain hard blockers.
- The finite limits are 12 dyadic hole-search levels and 512 native TASK172 evaluations per cell root.
- The prior Brent cell root and its ±1e-6 W neighborhood repair are removed. The outer feasibility-boundary bisection is unchanged.

The focused n=2 regression reproduces the trial at support `[4.8, 6.0] m`, subdivision 0, `q=4436.3679921671355 W`. TASK172 continues to reject that exact trial. Valid evaluations at `q=4436.357992167135 W` and `q=4436.377992167136 W` bracket the root with opposite signs; the final cell value is an actual valid `Task172LocalResult`. Their hashes and residuals are in the machine-readable evidence.

## Production mesh execution

The native case, Stage-2 identities, one-way pressure composition, property domain, mesh policy, and TASK172 authorities were not changed. Each level was solved independently from n=1. The first n=1→2 duty comparison passes its relative-duty threshold, but wall-extrema differences exceed 0.01 K; the mesh is therefore not admitted. The later required pair/headroom evidence is incomplete because the n=16 solve stopped at the cell evaluation cap.

Hole counts observed across all outer trajectories were n=1: 0, n=2: 18, n=4: 34, n=8: 51, and n=16 partial: 23; all observed holes were `BLOCKED_RESIDUAL_ACCEPTANCE`. The n=16 aggregate count is partial through the failing cell.

Some wall-extrema details for n=4 and n=8 were not emitted by the original blocked-result trace and are marked unavailable rather than inferred. An additional observables replay was stopped after n=2 to avoid repeating the full expensive production sequence; its n=1 and n=2 values matched the original run. This limitation does not change the fail-closed result.

Evidence canonical hash: `54f3986908f04c07524b7a079a709793bfa25de073ae9a0b48776eaea9629c57`.
Registry root canonical hash: `6145f12896e3e618ed7638aadd712beeb971be5ccb5acabcffaea88d282d7cdb`.

## Validation and lifecycle

TASK173 focused tests: 30 passed. Full shell-tube regression: passed (exit 0; three existing warnings). Ruff, format, mypy (448 source files), manifest D==M (259/259), lock check, and pip-audit passed. The local package `heat-exchanger-design-agent` was skipped by pip-audit because it is not available on PyPI. The duplicate-key audit found four repeated root-level `canonical_hash` keys already present at the authorized predecessor; they are preserved, and this append adds no duplicate keys. Exact-final-head CI remains required after the single candidate commit.

This is not a successful Stage-3 candidate and is not self-approved. `REAL_CASE_MESH_ADMISSIBLE=false`; TASK175 remains unexecuted; Ready and Merge remain unauthorized. The single remaining blocker is the authorized per-cell evaluation resource cap being exhausted at n=16 before completing the integrated rating sequence.
