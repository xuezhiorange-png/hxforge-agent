# TASK172 Stage-3 production mesh re-execution from n=1

**Task:** `TASK172_V0_7_STAGE3_PRODUCTION_MESH_REEXECUTION_FROM_N1_R1`
**Mode:** `STAGE3_PRODUCTION_MESH_EXECUTION_ONLY`
**Result:** `BLOCKED`
**PR:** #283, remains `OPEN_DRAFT`
**Execution HEAD:** `bdd6d5a023ae86bcd79bce5087e32ab51c61a587`

## Outcome

The frozen production sequence was restarted from n=1 using the reviewed Stage-2 native identity chain and the R2 cell-root authority. Levels n=1, 2, 4, and 8 completed. The n=16 solve stopped fail-closed at `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED` after its local hole search reached level 12. In accordance with the execution boundary, n=32 and n=64 were not run.

No candidate mesh exists. Each completed pairwise comparison passed the duty metric but failed at least one required wall-extrema comparison. No headroom was evaluated, no production mesh was admitted, and no successful/authoritative TASK173 result identity was issued. The blocked execution identity is diagnostic only.

The machine-readable record is [the production mesh execution evidence](evidence/TASK-172-stage3-production-mesh-reexecution-from-n1-r1.json). It contains the complete requested thermal and energy observables for each completed mesh, pairwise comparisons, execution counts, and the available n=16 blocker receipt.

## Completed mesh observations

| n | Total cells | Duty (W) | Tube outlet (K) | Shell outlet (K) | Inner wall extrema (K) | Outer wall extrema (K) | Minimum approach (K) | TASK172 evals / holes |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 10 | 52362.216168039979 | 298.9562992655684 | 298.7761641216321 | 298.5898027909208–299.2464365127666 | 298.5274103515744–299.1584862214705 | 0.8062992588553 | 4222 / 0 |
| 2 | 20 | 52349.7395172012105 | 298.9565479431746 | 298.776014918398 | 298.55483886929727–299.2938706331475 | 298.4937819912769–299.20404449243773 | 0.8065479357611 | 8514 / 18 |
| 4 | 40 | 52346.6228439931748 | 298.95661006281233 | 298.7759776414382 | 298.5378859955716–299.31837998257555 | 298.47747960204094–299.22758758524856 | 0.80661006084543 | 18586 / 34 |
| 8 | 80 | 52345.8438142056468 | 298.95662559013135 | 298.7759683239742 | 298.5295376264141–299.3308395884031 | 298.46945231878885–299.2395566950424 | 0.80662558946540 | 37372 / 51 |

All completed levels reported energy-balance residuals from `8E-11 W` to `9.6E-10 W`; see the evidence JSON for the exact hot-side loss, cold-side gain, wall-duty sum, terminal residuals, precision floors, mesh identities, and hashes.

## Frozen-policy comparisons

| Pair | Relative duty difference | Duty | Wall extrema | Overall |
|---|---:|---|---|---|
| 1→2 | 0.0002382758361244419736063372369 | PASS | FAIL (all four exceed 0.01 K) | FAIL |
| 2→4 | 0.00005953560107040486025234071468 | PASS | FAIL (all four exceed 0.01 K) | FAIL |
| 4→8 | 0.00001488214034073822616483620898 | PASS | FAIL (inner/outer maxima exceed 0.01 K) | FAIL |

The precision floors are included in the machine-readable comparison records. The failure is not a near-zero duty case; relative duty comparison was used. Since no pair passed, the required two consecutive passing pairs and later headroom condition cannot be met from the completed evidence.

## n=16 blocker

The first failed level is n=16. At outer iteration 2, the production solver reports one `BLOCKED_RESIDUAL_ACCEPTANCE` hole in the cell-root search, 13 valid evaluations, and recovery search level 12. It then returned `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED`. The per-cell count was 14, with one hole, one recovery bracket, and 12 probes. The R2 per-cell cap remained 512; this was not an evaluation-cap exhaustion.

The captured physical support, tube/shell cells, wall interface, and shooting enthalpy are recorded in the JSON. The blocked-result contract did not emit left/right valid q endpoints, residuals, or final bracket width; these are explicitly `null` with an unavailable reason, not inferred from blocked diagnostics. The raw diagnostic string `physical_interval=[0.0,111.3949198456]` is preserved without reinterpreting its field name.

## Evidence limitations

The completed n=2/n=4/n=8 execution capture does not provide a complete per-hole receipt for all 103 holes: n=2 emitted none, and n=4/n=8 emitted one sample each. The external tracing callback also used incorrect frame scoping for the maximum recovery-depth metric on successful n=2/n=4/n=8 runs; those values are therefore marked unavailable. n=1 had no holes, and n=16's failed-cell record directly reports level 12.

These capture limitations are disclosed; no missing support/q/hash data or depth values were fabricated. They do not alter the observed fail-closed n=16 blocker or the non-admission decision. Any future attempt that needs complete per-hole diagnostics requires a separately authorized implementation/capture correction before rerunning production execution.

**Next gate:** `STAGE3_VALID_POINT_BRACKET_UNRESOLVED_AND_HOLE_DIAGNOSTIC_CAPTURE_CORRECTION`.

## Change and lifecycle boundary

This execution changed no production code, tests, dependencies, workflows, TASK172 acceptance behavior, R98 policy, or mesh thresholds. It did not execute TASK175. `REAL_CASE_MESH_ADMISSIBLE=false`; `TASK173_RESULT_ID` and `TASK173_RESULT_HASH` remain unavailable. PR #283 remains Draft; Ready and Merge are unauthorized.

The registry update is append-only. The exact-final-head CI result is recorded in the final task receipt after the evidence-only commit and is tied to that commit's exact HEAD.
