# TASK173 fresh production-mesh re-execution after accepted-replay correction

## Closeout

```text
TASK_ID=STAGE3_TASK173_PRODUCTION_MESH_REEXECUTION_FROM_N1_AFTER_REPLAY_CORRECTION
MODE=FRESH_PRODUCTION_MESH_EXECUTION_ONLY
RESULT=PASS_TASK173_PRODUCTION_MESH_REEXECUTION_AFTER_REPLAY_CORRECTION
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
EXECUTION_SOURCE_HEAD=8a493be4b20e842f1d07051ba53a887ca763688c
FINAL_EVIDENCE_HEAD=BOUND_BY_THIS_EVIDENCE_COMMIT_AND_PR_CLOSEOUT
EVIDENCE_CANONICAL_HASH=cdabfa3e114b1e2a7ea7d02e32af1c80e7e2cfceecf576e9162a80202f11faf5
```

The authoritative run called the public `task173_integrated_rating.validate_request(...)` once in a fresh process with the canonical Stage-2 native request. Production completed the frozen mesh sequence from n=1 through n=64, selected n=32 as the earliest candidate after the required consecutive passing pairs, and used n=64 as passing headroom. The corrected `_build_success()` then replayed the entire accepted n=32 outer-boundary search from a fresh empty `_CellSearchStats`. Candidate and replay mesh hashes, face-ID vector hashes, and local TASK172 result-hash vector hashes matched exactly. The public return was a real `Task173SuccessResult(status=VALIDATED)` and its request/result identity replay passed.

One earlier observer-setup attempt completed n=1 but failed while the temporary observer formatted its capture (`KeyError: 'mesh_result_hash'`), returning `BLOCKED_TASK173_UNEXPECTED_RUNTIME_FAILURE`. It is retained as a discarded, non-authoritative harness attempt only; none of its result was reused. The authoritative run below independently started again from n=1 and completed once. No production logic was changed.

## Frozen lineage and execution

- Authorized source HEAD: `8a493be4b20e842f1d07051ba53a887ca763688c`; PR #283 remained open and Draft at preflight, with the remote PR head matching this SHA.
- Predecessor replay correction evidence: `7ff11ea47df375479d0a7c4437999a7b255c69de92b2d62dcb2bc6c7e6333cc4`.
- TASK172 reviewed authority: `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, hash `9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b`.
- Cell-root authority: `V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R3`, hash `eafe8bc53769d1648ac2f918045cececfd3870d618ff6273c523fe185a6683ef`.
- Endpoint classification authority: `V07-T173-SHELL-CAPACITY-ENDPOINT-HOLE-LOW-SIDE-CLASSIFICATION-R1`, hash `60c8fe2957c5906704b796a779b88845ddb3e59934d8576c93e0589ea2084f74`.
- Zero-q state authority: `V07-T173-ZERO-Q-STATE-IDENTITY-PORTABILITY-R1`, hash `81903b49fcf6c9e41ff8f296da921e25ca116727b846e01f9e07e257dd4531fd`.
- Local-state reconstruction authority: `V07-T173-ENTHALPY-MIDPOINT-LOCAL-STATE-R2`, hash `9abef953ce251628b73370f08337efbe7938ed33509a2a99c878eade2bb8b366`.
- Mesh profile: `V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1`.
- Canonical request hash: `77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed`; Stage-2 evidence hash: `3ed4da6385097e1ee57196c5946d37943d073d4506e35149ef57ad9183cdd100`.
- Execution ID: `f95a668a-39fe-48a6-aa04-94184d83ecd9`.
- Start/completion: `2026-10-03T14:25:24.918782Z` / `2026-10-03T21:45:02.443193Z`; elapsed `26377.25805` seconds.
- Runtime: Python 3.14.5, macOS 27.2 arm64, SciPy 1.18.0, CoolProp 8.0.0, real `CoolPropProvider`.
- Freshness: `FRESH_RUN_FROM_N1=true`; prior production execution, fixtures, cached result, targeted n=32 replay, and mesh outputs were not reused or promoted.
- Observation wrapper: it forwarded each `_solve_outer_boundary` invocation's arguments unchanged to the original function and returned the original result/exception unchanged; observer errors were isolated. It did not monkeypatch TASK172 or alter production decisions.

The frozen mesh rules were unchanged: sequence 1, 2, 4, 8, 16, 32, 64; duty relative threshold 0.01; near-zero duty threshold 0.01 W; wall-extrema threshold 0.01 K; two consecutive passing pairs; one later headroom level; maximum subdivision 64; latest acceptable candidate 32.

## Fresh production mesh levels

All values below are from the authoritative fresh run. `accepted_shooting_enthalpy_j_kg` and `outer_bisection_iterations` are available from the final accepted n=32 result only; the public per-level mesh-observation capture did not expose them for other levels, so those entries are explicitly unavailable in the machine evidence. Per-level TASK172 request/result aggregate hashes were likewise not exposed by the retained public mesh observations. They are not inferred.

| n | cells tube/shell/total | walls | total duty W | tube/shell outlet K | inner wall min/max K | outer wall min/max K | min approach K | energy residual W | terminal residual K / J kg⁻¹ | TASK172 attempts / holes | mesh result hash | elapsed s |
|---:|---:|---:|---:|---|---|---|---:|---|---|---:|---|---:|
| 1 | 5/5/10 | 5 | 52362.216168039979 | 298.9562992655684 / 298.7761641216321 | 298.5898027909208 / 299.2464365127666 | 298.5274103515744 / 299.1584862214705 | 0.8062992588553 | 2.21E-10 | 6.7131E-9 / 0.00002814423 | 4222 / 0 | `8bab91b8d330ece6ec93d17a763c65564e2cddbcfaeb5fe65f01c61b58080f08` | 158.284573 |
| 2 | 10/10/20 | 10 | 52349.7395172012105 | 298.9565479431746 / 298.776014918398 | 298.55483886929727 / 299.2938706331475 | 298.4937819912769 / 299.20404449243773 | 0.8065479357611 | 5.6E-10 | 7.4135E-9 / 0.00003108429 | 8492 / 2 | `fc7350ad9230252886ae63af24f4ea5245c9108cf63c83ee92e8c3ced114cdcd` | 320.2865 |
| 4 | 20/20/40 | 20 | 52346.6228439931748 | 298.95661006281233 / 298.7759776414382 | 298.5378859955716 / 299.31837998257555 | 298.47747960204094 / 299.22758758524856 | 0.80661006084543 | 8E-11 | 1.9669E-9 / 0.00000819426 | 18533 / 2 | `7fba263f63e90bd2f67e544936a5fa14279d198f7678be6186106626423df873` | 726.088207 |
| 8 | 40/40/80 | 40 | 52345.8438142056468 | 298.95662559013135 / 298.7759683239742 | 298.5295376264141 / 299.3308395884031 | 298.46945231878885 / 299.2395566950424 | 0.80662558946540 | 9.6E-10 | 6.6595E-10 / 0.00000274963 | 37309 / 5 | `a5bd86c252627e134b0dfe037a800cdf398aa270bea988a97d480a7a2af8871b` | 1444.68472 |
| 16 | 80/80/160 | 80 | 52345.6490747340919 | 298.95662947157905 / 298.7759659946122 | 298.52539495403676 / 299.33712151906025 | 298.46546917043577 / 299.24559149866536 | 0.80662947147369 | 7.6E-10 | 1.0536E-10 / 4.8970E-7 | 74643 / 11 | `a00902ad4d7790b537bfd04a9bad4f3b3c56266ed6bccfe14180d9b39eba3603` | 2828.894678 |
| 32 | 160/160/320 | 160 | 52345.60023831155286 | 298.95663044480705 / 298.77596541594073 | 298.5233314384105 / 299.34027563230075 | 298.46348516472494 / 299.2486215741561 | 0.80663043958905 | 8.8E-10 | 5.218E-9 / 0.00002190958 | 149522 / 21 | `37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257` | 5885.998387 |
| 64 | 320/320/640 | 320 | 52345.58803689592587 | 298.9566306879901 / 298.77596527121517 | 298.5223016259143 / 299.34185598950273 | 298.46249504439083 / 299.2501397931521 | 0.80663068155397 | 1.72587E-9 | 6.43613E-9 / 0.00002688015 | 255742 / 35 | `9320ab18b5068c6bf7f2229463fbab12ed92d3e6f7aad89ccbbc080324e9b63f` | 9509.143383 |

All captured numerical holes were classified as `BLOCKED_RESIDUAL_ACCEPTANCE`. The n=32 and n=64 hole-code maps were respectively 21 and 35 such holes. Mesh-level identities are in the machine evidence.

Per-interval duties, W, in production interval order:

- n=1: `[12347.39656143347, 11324.9801301599, 10391.620296648718, 9538.905484893043, 8759.313694904848]`
- n=2: `[12343.5174057830685, 11321.901528796523, 10389.225784831995, 9537.094710898721, 8758.000086890903]`
- n=4: `[12342.5485361085202, 11321.1325457681776, 10388.6276130344277, 9536.6423070381951, 8757.6718420438542]`
- n=8: `[12342.3063724199345, 11320.9403367115289, 10388.4780961580391, 9536.5292234438463, 8757.5897854722980]`
- n=16: `[12342.2458371659644, 11320.8922872600734, 10388.4407181080308, 9536.5009575942335, 8757.5692746057898]`
- n=32: `[12342.23066696489061, 11320.88024294466808, 10388.43135405977491, 9536.49385951402181, 8757.56411482819745]`
- n=64: `[12342.22687892871697, 11320.87723192017434, 10388.42900528827170, 9536.49208777285083, 8757.56283298591203]`

## Production convergence and accepted replay

Pair classifications below are the production `_compare_meshes()` outputs, with duty metric in relative-fraction units and the frozen thresholds unchanged.

| pair | duty Δ W | duty metric | duty | inner min/max Δ K | outer min/max Δ K | wall | overall |
|---|---:|---:|---|---|---|---|---|
| 1→2 | 12.4766508387685 | 0.0002382758361244419736063372369 | PASS | 0.03496392162353 / 0.0474341203809 | 0.0336283602975 / 0.04555827096723 | FAIL | FAIL |
| 2→4 | 3.1166732080357 | 0.00005953560107040486025234071468 | PASS | 0.01695287372567 / 0.02450934942805 | 0.01630238923596 / 0.02354309281083 | FAIL | FAIL |
| 4→8 | 0.7790297875280 | 0.00001488214034073822616483620898 | PASS | 0.0083483691575 / 0.01245960582755 | 0.00802728325209 / 0.01196910979384 | FAIL | FAIL |
| 8→16 | 0.1947394715549 | 0.000003720247060035958084152438176 | PASS | 0.00414267237734 / 0.00628193065715 | 0.00398314835308 / 0.00603480362296 | PASS | PASS |
| 16→32 | 0.04883642253904 | 9.329604924626313223708135406E-7 | PASS | 0.00206351562626 / 0.00315411324050 | 0.00198400571083 / 0.00303007549074 | PASS | PASS |
| 32→64 | 0.01220141562699 | 2.330934323312970369937735576E-7 | PASS | 0.0010298124962 / 0.00158035720198 | 0.00099012033411 / 0.0015182189960 | PASS | PASS |

The earliest candidate satisfying two consecutive overall PASS pairs is n=32 (8→16 and 16→32); n=64 is the required later passing headroom. All six pair comparisons are retained in the JSON evidence.

```text
CANDIDATE_MESH_RESULT_HASH=37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257
REPLAY_MESH_RESULT_HASH=37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257
MESH_RESULT_HASH_MATCH=true
CANDIDATE_FACE_ID_VECTOR_HASH=031af19b9acbda84cf34697089130f5635d91c4e67369de2cdf08e3315ce4337
REPLAY_FACE_ID_VECTOR_HASH=031af19b9acbda84cf34697089130f5635d91c4e67369de2cdf08e3315ce4337
FACE_ID_MATCH=true
CANDIDATE_LOCAL_TASK172_RESULT_VECTOR_HASH=150f8a2dde9610969c1b38ee8ea8dcd7d170b1dc9cae9ffa7e8b24bc81f8c7a8
REPLAY_LOCAL_TASK172_RESULT_VECTOR_HASH=150f8a2dde9610969c1b38ee8ea8dcd7d170b1dc9cae9ffa7e8b24bc81f8c7a8
LOCAL_TASK172_RESULT_HASH_MATCH=true
CANDIDATE_TASK172_EVALUATION_COUNT=149522
REPLAY_TASK172_EVALUATION_COUNT=149522
CANDIDATE_TASK172_NUMERICAL_HOLE_COUNT=21
REPLAY_TASK172_NUMERICAL_HOLE_COUNT=21
REPLAY_STATS_INITIALIZATION=FRESH_EMPTY_CELL_SEARCH_STATS
REPLAY_STATS_SCOPE=FULL_ACCEPTED_MESH_OUTER_BOUNDARY_SEARCH
CANDIDATE_STATS_REUSED=false
HISTORICAL_COUNTERS_COPIED=false
```

## Validated Task173 rating result

```text
TASK173_REQUEST_HASH=77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed
TASK173_REQUEST_HASH_REPLAY=77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed
TASK173_REQUEST_HASH_REPLAY_STATUS=PASS
TASK173_RESULT_TYPE=Task173SuccessResult
TASK173_RESULT_STATUS=VALIDATED
TASK173_RESULT_HASH=fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
TASK173_RESULT_HASH_REPLAY=fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
TASK173_RESULT_HASH_REPLAY_STATUS=PASS
TASK173_RESULT_ID=urn:hxforge:task173:fddc9d68414a5650b3268bdb7c27e34cdd27f41144fbd8058a011053ebbba38b
TASK173_RESULT_ID_BINDS_HASH=true
PRODUCTION_MESH_IDENTITY=d71dd9e0214eae5cad868b459f08cb50e29395be21a322b3176181f5d39b4da9
REAL_CASE_MESH_ADMISSIBLE=true
TASK173_RATING_RESULT_AVAILABLE=true
```

Authoritative rating outputs: total duty `52345.60023831155286 W`; tube/shell outlet temperatures `298.95663044480705 K` / `298.77596541594073 K`; tube/shell outlet pressures `100888.042 Pa` / `100629.39120547583476682908903627157467930995314008 Pa`; inner wall min/max `298.5233314384105 K` / `299.34027563230075 K`; outer wall min/max `298.46348516472494 K` / `299.2486215741561 K`; minimum approach `0.80663043958905 K`; hot energy loss `52345.60023831072 W`; cold energy gain `52345.60023831160 W`; wall duty sum `52345.60023831155286 W`; energy balance residual `8.8E-10 W`; terminal boundary residual `5.218E-9 K` / `0.00002190958 J/kg`; shell-outlet shooting enthalpy `107537.39984309299651393808424472808837890625 J/kg`; outer bisection iterations `28`.

`SIZING_EXECUTION_STATUS=NOT_APPLICABLE_CURRENT_REFERENCE_CASE`. No sizing research or TASK175 release acceptance was performed.

## Scope, validation, and next state

```text
R94_CHANGED=false
R98_CHANGED=false
C_ROUND_CHANGED=false
TASK172_CODE_CHANGED=false
MESH_POLICY_CHANGED=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
FIXTURES_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILE_CHANGED=false
WORKFLOWS_CHANGED=false
AUTHORITY_CHANGED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE3_TASK173_FULL_RATING_AND_SIZING_SOLVER_CLOSEOUT
NEXT_GATE_EXECUTED=false
STOP=true
```

Local validation results are recorded in the companion JSON. Exact-head CI run/head/result, CI job counts, final runtime-budget gate, and final evidence HEAD are recorded in the PR closeout; the content-addressed receipt cannot include its own post-commit CI run identifier. Historical blocked receipts remain immutable. The pre-existing untracked handoff file is unchanged and excluded.
