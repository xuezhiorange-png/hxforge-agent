# TASK172 Stage-3 production mesh re-execution R2

Task: `TASK172_V0_7_STAGE3_PRODUCTION_MESH_REEXECUTION_FROM_N1_AFTER_R3_ZERO_Q_AND_SECURITY_CLOSURE_R2`
Mode: `STAGE3_PRODUCTION_MESH_EXECUTION_ONLY`
Result: **BLOCKED**
PR #283 remains OPEN/DRAFT. Execution source HEAD: `0fb5450cba5b5bb60cf9ca2fbba6ec7787aca576`.

## Outcome

A new execution began from n=1 using the frozen authorities and current corrected Stage-2 native chain. No R1 mesh result, fixture result, or cached TASK173 result was promoted. Levels n=1, 2, 4, 8, and 16 completed. The first blocker occurred at n=32:

`BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED` at the lower q endpoint after 12 authorized recovery levels. The returned result reports 11 valid recovery samples, no sign pair, and no eligible root. TASK172 counts contain 159 residual-acceptance numerical holes. This blocker is not the R3 shell-capacity upper-endpoint classification case.

The public blocked result did not expose the failed physical support, tube/shell cell, wall interface, outer iteration, shooting enthalpy, or q bracket. Those fields remain unavailable; none were reconstructed from historical evidence. n=64 was not run. No partial mesh is promoted.

## Fresh mesh-level results

| n | State | Cells (tube/shell/total/wall) | Duty W | Tube outlet K | Shell outlet K | Inner wall min/max K | Outer wall min/max K | Min approach K | TASK172 evals / holes | Outer iterations |
|---:|---|---:|---:|---:|---:|---|---|---:|---:|---:|
| 1 | COMPLETE | 5/5/10/5 | 52362.216168039979 | 298.9562992655684 | 298.7761641216321 | 298.5898027909208 / 299.2464365127666 | 298.5274103515744 / 299.1584862214705 | 0.8062992588553 | 4222 / 0 | 27 |
| 2 | COMPLETE | 10/10/20/10 | 52349.7395172012105 | 298.9565479431746 | 298.776014918398 | 298.55483886929727 / 299.2938706331475 | 298.4937819912769 / 299.20404449243773 | 0.8065479357611 | 8514 / 18 | 26 |
| 4 | COMPLETE | 20/20/40/20 | 52346.6228439931748 | 298.95661006281233 | 298.7759776414382 | 298.5378859955716 / 299.31837998257555 | 298.47747960204094 / 299.22758758524856 | 0.80661006084543 | 18586 / 34 | 28 |
| 8 | COMPLETE | 40/40/80/40 | 52345.8438142056468 | 298.95662559013135 | 298.7759683239742 | 298.5295376264141 / 299.3308395884031 | 298.46945231878885 / 299.2395566950424 | 0.80662558946540 | 37372 / 51 | 28 |
| 16 | COMPLETE | 80/80/160/80 | 52345.6490766926279 | 298.95662947138504 | 298.7759659946122 | 298.5253949540725 / 299.33712151906025 | 298.4654691704589 / 299.24559149866536 | 0.80662947130599 | 74798 / 100 | 28 |
| 32 | FAILED_BEFORE_MESH_COMPLETION | expected 160/160/320/160 (not completed) | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | 121654 / 159 | unavailable |

Full energy/terminal observables, shooting enthalpies, result hashes, per-level identity manifests, numerical-hole neighborhoods, and capture notes are in the machine-readable evidence.

## Frozen pairwise comparisons

| Pair | Duty metric (relative fraction) | Duty | Wall extrema | Overall |
|---|---:|---|---|---|
| 1→2 | 0.0002382758361244419736063372369 | PASS | FAIL | FAIL |
| 2→4 | 0.00005953560107040486025234071468 | PASS | FAIL | FAIL |
| 4→8 | 0.00001488214034073822616483620898 | PASS | FAIL | FAIL |
| 8→16 | 0.000003720209644725452219476434207 | PASS | PASS | PASS |

Only 8→16 passed overall: one passing pair is insufficient. There is no candidate, no later headroom result, and `REAL_CASE_MESH_ADMISSIBLE=false`.

## Boundary and validation

R3 endpoint classification, exact-zero state identity, R98/C_round=1.0, TASK172 acceptance, production mesh policy, and resource limits were not changed. The corrected TASK031/TASK032/TASK166/TASK174 identity chain and urllib3 2.8.0 / requests 2.34.2 lock state were used.

Local checks: focused TASK173 **PASS**; full shell-tube suite **PASS (3 skipped)**; HTTP/API regression **PASS (21 tests)**; Ruff, format, mypy CI scope, manifest, locked sync, lock check, and pip-audit **PASS**. The structured run capture emitted zero for some aggregate valid/bracket/probe counters despite nonzero residual-acceptance holes; reported counters are preserved and not silently repaired. See evidence notes.

No successful production TASK173 result was created. TASK175, Ready, and Merge were not performed.

Next gate: `STAGE3_N32_LOWER_ENDPOINT_VALID_POINT_BRACKET_UNRESOLVED_DIAGNOSTIC_AND_CORRECTION_REASSESSMENT`. Stop here.

Canonical evidence hash: `0c8a9ee9203e91c0fcd371d166bf26fd0477df1fd13c0048028f900697662ceb`.
