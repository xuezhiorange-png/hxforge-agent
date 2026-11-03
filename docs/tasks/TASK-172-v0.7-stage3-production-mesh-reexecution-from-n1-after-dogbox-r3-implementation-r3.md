# TASK172 v0.7 Stage-3 production mesh re-execution from n=1 after dogbox R3 implementation

## Closeout

```text
TASK_ID=STAGE3_TASK173_PRODUCTION_MESH_REEXECUTION_FROM_N1
MODE=FRESH_PRODUCTION_MESH_EXECUTION_ONLY
RESULT=BLOCKED_PRODUCTION_MESH
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
EXECUTION_SOURCE_HEAD=f2b84ca67855bc07444f10ef89e9330ae8954bb6
FINAL_EVIDENCE_HEAD=LINKED_BY_EXACT_HEAD_PR_CLOSEOUT_RECEIPT
EVIDENCE_CANONICAL_HASH=9bdca85bcad6f897bb9de1f144082d34e2c2fe7c7883a4d9b8b9645983d12308
```

This receipt records one fresh-process call to the current production `task173_integrated_rating.validate_request(...)`, begun at n=1. All frozen mesh levels n=1, 2, 4, 8, 16, 32, and 64 completed as valid trajectories. The frozen candidate and headroom conditions were satisfied (candidate n=32; n=64 headroom). The production success builder then rejected the accepted n=32 result because its deterministic replay produced a different mesh result hash. This is a post-sequence accepted-mesh replay blocker, not a failed n=32 or n=64 mesh execution.

No production or test code was changed, no mesh result was promoted, and no additional mesh run was performed while preparing this receipt.

## Frozen lineage and preflight

- TASK172 reviewed authority: `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, canonical hash `9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b`.
- TASK172 implementation evidence hash: `47f179ccb335158568e22ae2582b2ec48cd6237ceb18427b7c1275460f11556f`.
- Cell-root authority: `V07-T173-VALID-POINT-CELL-ROOT-BRACKETING-R3`, hash `eafe8bc53769d1648ac2f918045cececfd3870d618ff6273c523fe185a6683ef`.
- Endpoint classification authority: `V07-T173-SHELL-CAPACITY-ENDPOINT-HOLE-LOW-SIDE-CLASSIFICATION-R1`, hash `60c8fe2957c5906704b796a779b88845ddb3e59934d8576c93e0589ea2084f74`.
- Exact-zero state authority: `V07-T173-ZERO-Q-STATE-IDENTITY-PORTABILITY-R1`, hash `81903b49fcf6c9e41ff8f296da921e25ca116727b846e01f9e07e257dd4531fd`.
- Local state reconstruction authority: `V07-T173-ENTHALPY-MIDPOINT-LOCAL-STATE-R2`, hash `9abef953ce251628b73370f08337efbe7938ed33509a2a99c878eade2bb8b366`.
- Production mesh profile: `V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1`.
- Request hash: `77fd429c0a10223a3fb5c26501599281568e2887b17c88e4ad5c76314279e9ed`.
- PR was Open/Draft at preflight; checkout HEAD matched the authorized execution source. The tracked worktree was clean. The pre-existing untracked handoff file was left untouched and excluded.

The run used a fresh process and fresh property-provider instances. It did not reuse R1/R2 mesh values, cached TASK173 results, fixtures, or historical numerical outputs for admission. The only historical use was lineage identification; all admission decisions below come from this run.

## Frozen profile and execution environment

The unchanged profile required sequence 1, 2, 4, 8, 16, 32, 64; relative duty threshold 0.01; near-zero absolute duty threshold 0.01 W; wall-extrema absolute threshold 0.01 K; two consecutive passing pairs; one later headroom level; maximum subdivision 64; latest acceptable candidate 32. The production earliest-candidate/headroom logic was used without changing thresholds or rounding observations before comparison.

- Execution ID: `78496014-1dac-4374-b883-1e8bcc6a9057`.
- Start: `2026-10-03T03:27:51.838244Z`.
- Completion: `2026-10-03T10:56:22.213279Z`.
- Runtime: 7 h 28 min 30.375 s.
- Runtime: Python 3.14.5; macOS 27.2 arm64; CoolProp 8.0.0; requests 2.34.2; urllib3 2.8.0.
- Real CoolProp provider; eight provider instances were created over the production mesh calls.
- `FRESH_RUN_FROM_N1=true`; `PRIOR_MESH_RESULTS_REUSED=false`; `CACHED_TASK173_RESULT_PROMOTED=false`; `FIXTURE_RESULT_PROMOTED=false`.

## Completed mesh levels

Counts below are from this execution. `valid_evaluations` is the observed attempt count minus the observed residual-acceptance numerical-hole count; every hole in these level captures was classified as `BLOCKED_RESIDUAL_ACCEPTANCE`. Axial duty interval arrays are ordered as emitted by the production mesh projection. Temperatures and pressures are only reported where retained in this execution receipt; no missing pressure value is reconstructed.

| n | cells (tube/shell/total) | wall interfaces | mesh identity | total duty W | tube/shell outlet K | inner wall min/max K | outer wall min/max K | min approach K | hot loss / cold gain / wall sum W | energy residual W | shooting enthalpy J/kg | outer iterations | TASK172 attempts / valid / holes | mesh result hash | elapsed s |
|---:|---:|---:|---|---:|---|---|---|---:|---|---:|---:|---:|---|---|---:|
| 1 | 5/5/10 | 5 | `ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607` | 52362.216168039979 | 298.9562992655684 / 298.7761641216321 | 298.5898027909208 / 299.2464365127666 | 298.5274103515744 / 299.1584862214705 | 0.8062992588553 | 52362.21616804008 / 52362.21616804020 / 52362.216168039979 | 2.21E-10 | 107538.2306458140842204885184764862060546875 | 27 | 4222 / 4222 / 0 | `8bab91b8d330ece6ec93d17a763c65564e2cddbcfaeb5fe65f01c61b58080f08` | 161.8965 |
| 2 | 10/10/20 | 10 | `0310082d4d83365d229317dbcfd17ee90e2158abd5bc99da5db7743ad9925645` | 52349.7395172012105 | 298.9565479431746 / 298.776014918398 | 298.55483886929727 / 299.2938706331475 | 298.4937819912769 / 299.20404449243773 | 0.8065479357611 | 52349.73951720156 / 52349.73951720100 / 52349.7395172012105 | 5.6E-10 | 107537.606816212185394600927829742431640625 | 26 | 8492 / 8490 / 2 | `fc7350ad9230252886ae63af24f4ea5245c9108cf63c83ee92e8c3ced114cdcd` | 333.865 |
| 4 | 20/20/40 | 20 | `20383fc1b28648da59f32e74d2f5164d27a3da2b2fc4d03a4c08dcc5a4ad9be5` | 52346.6228439931748 | 298.95661006281233 / 298.7759776414382 | 298.5378859955716 / 299.31837998257555 | 298.47747960204094 / 299.22758758524856 | 0.80661006084543 | 52346.62284399312 / 52346.62284399320 / 52346.6228439931748 | 8E-11 | 107537.45095966176180341266095638275146484375 | 28 | 18533 / 18531 / 2 | `7fba263f63e90bd2f67e544936a5fa14279d198f7678be6186106626423df873` | 736.7996 |
| 8 | 40/40/80 | 40 | `dc15334e9c99c47871438e6b341c61252e8f273dac1fede35de30e7911539458` | 52345.8438142056468 | 298.95662559013135 / 298.7759683239742 | 298.5295376264141 / 299.3308395884031 | 298.46945231878885 / 299.2395566950424 | 0.80662558946540 | 52345.84381420596 / 52345.84381420500 / 52345.8438142056468 | 9.6E-10 | 107537.41200272773098527871072292327880859375 | 28 | 37309 / 37304 / 5 | `a5bd86c252627e134b0dfe037a800cdf398aa270bea988a97d480a7a2af8871b` | 1441.8529 |
| 16 | 80/80/160 | 80 | `c7cf7f75ccc837e8d375ff78242e6a7e51c74d463be0d0be51488c99ecbfa44a` | 52345.6490747340919 | 298.95662947157905 / 298.7759659946122 | 298.52539495403676 / 299.33712151906025 | 298.46546917043577 / 299.24559149866536 | 0.80662947147369 | 52345.64907473436 / 52345.64907473360 / 52345.6490747340919 | 7.6E-10 | 107537.40226349422328074522316455841064453125 | 28 | 74643 / 74632 / 11 | `a00902ad4d7790b537bfd04a9bad4f3b3c56266ed6bccfe14180d9b39eba3603` | 3080.807 |
| 32 | 160/160/320 | 160 | `d71dd9e0214eae5cad868b459f08cb50e29395be21a322b3176181f5d39b4da9` | 52345.60023831155286 | 298.95663044480705 / 298.77596541594073 | 298.5233314384105 / 299.34027563230075 | 298.46348516472494 / 299.2486215741561 | 0.80663043958905 | 52345.60023831072 / 52345.60023831160 / 52345.60023831155286 | 8.8E-10 | 107537.39984309299651393808424472808837890625 | 28 | 149522 / 149501 / 21 | `37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257` | 5701.133 |
| 64 | 320/320/640 | 320 | `00ee59d23349132c2d5eed7ef867308cf104735377f7866c5a6bdc5623b90a14` | 52345.58803689592587 | 298.9566306879901 / 298.77596527121517 | 298.5223016259143 / 299.34185598950273 | 298.46249504439083 / 299.2501397931521 | 0.80663068155397 | 52345.58803689492 / 52345.58803689420 / 52345.58803689592587 | 1.72587E-9 | 107537.3992379926898222362995147705078125 | 24 | 255742 / 255707 / 35 | `9320ab18b5068c6bf7f2229463fbab12ed92d3e6f7aad89ccbbc080324e9b63f` | 9564.8046 |

Per-interval duties (W):

- n=1: `[12347.39656143347, 11324.9801301599, 10391.620296648718, 9538.905484893043, 8759.313694904848]`
- n=2: `[12343.5174057830685, 11321.901528796523, 10389.225784831995, 9537.094710898721, 8758.000086890903]`
- n=4: `[12342.5485361085202, 11321.1325457681776, 10388.6276130344277, 9536.6423070381951, 8757.6718420438542]`
- n=8: `[12342.3063724199345, 11320.9403367115289, 10388.4780961580391, 9536.5292234438463, 8757.5897854722980]`
- n=16: `[12342.2458371659644, 11320.8922872600734, 10388.4407181080308, 9536.5009575942335, 8757.5692746057898]`
- n=32: `[12342.23066696489061, 11320.88024294466808, 10388.43135405977491, 9536.49385951402181, 8757.56411482819745]`
- n=64: `[12342.22687892871697, 11320.87723192017434, 10388.42900528827170, 9536.49208777285083, 8757.56283298591203]`

TASK172 request/result aggregate hashes by level:

| n | request aggregate hash | result aggregate hash |
|---:|---|---|
| 1 | `4d434edf333308f5128497d011f9a724ce1e9f670748ef08e44dde3100da4699` | `60f8155e309e2ff74ddc65c057acff4ca25eb3ca7240deb86d5cad8f100c1c50` |
| 2 | `146bd40523c90f32ff52248c3d38c8cfe4882539eef5b29d3eff064201895349` | `6918b4e2de3ae2a1b7bb3c73fd684fe4ae8493a1aaacfbebfd50e08064176c82` |
| 4 | `bbb1b3707f660e220c521cb3ea7a2c13a24f2ad762c130331e671282e1466fa2` | `bdbd413edf8de134d4a54a7a7099fc9c8c8a1e13b7a5467a83e6849c785b1120` |
| 8 | `4cb6f1d26e65e9f525601c63e0a1e71769494bf281de142eaa2c05de5638adc5` | `b51ffe9fcb8a034325f3c5b2c761c2841cc0800ad270b5b11bab2e8cc0b0df20` |
| 16 | `9cb41fe9a910106f07578e3fcc918a1bb69281ccd938881f0f9be5412ef4c495` | `c0b623fa85d336739d12a5237857ebec8a6bf58efa9173c435b1383faf5aab4b` |
| 32 | `a0a056a028c013c19f6f50c63c66b4ae529f66c6b529b97866f48ae13e3d11a6` | `150f8a2dde9610969c1b38ee8ea8dcd7d170b1dc9cae9ffa7e8b24bc81f8c7a8` |
| 64 | `6aa54b4929caa00efc56e594a6e3d27889ecd3bf61f578212c9329a134e77d95` | `c355caeeea913dd53acdfc3d58d5eb174438a6cb0c019aa3ea16b5d9adef8aec` |

N32 TASK172 numerical holes were 21, all `BLOCKED_RESIDUAL_ACCEPTANCE`. The two captured q-space neighborhoods were:

- hole at q=279.5358803376674 W; valid left anchor q=275.952087000005 W, F=-5.38902424953916 W, result hash `df3c…`; valid right anchor q=283.11967367532975 W, F=1.78809801548192 W, result hash `44f9…`.
- hole at q=281.3417761992238 W; valid left anchor q=281.33477660286115 W, F=0.00082633515965 W, result hash `5d06…`; valid right anchor q=281.3487757955864 W, F=0.0148441274972 W, result hash `dcd4…`.

N64 had 35 `BLOCKED_RESIDUAL_ACCEPTANCE` holes. One captured neighborhood was q=139.27564781854846 W; valid left anchor q=139.26378649613162 W, F=-0.00688382840263 W, result hash `737b…`; valid right anchor q=139.2875091409653 W, F=0.01685463833506 W, result hash `9177…`. Truncated hash prefixes above are deliberately labeled as prefixes, not complete identities.

## Pairwise production comparisons

Duty metric was the production relative comparison metric (dimensionless); threshold was 0.01. Wall comparison used the frozen 0.01 K absolute extrema threshold. Values below are observed absolute differences; production comparison classification was retained. The per-pair duty precision-floor values were not separately retained by the execution receipt and are marked unavailable in machine evidence; they were not reconstructed from another run.

| coarse→fine | duty difference W | duty metric | duty | inner min/max ΔK | outer min/max ΔK | wall | overall |
|---|---:|---:|---|---|---|---|---|
| 1→2 | 12.4766508387685 | 0.0002382758361244419736063372369 | PASS | 0.03496392162353 / 0.0474341203809 | 0.0336283602975 / 0.04555827096723 | FAIL | FAIL |
| 2→4 | 3.1166732080357 | 0.00005953560107040486025234071468 | PASS | 0.01695287372567 / 0.02450934942805 | 0.01630238923596 / 0.02354309281083 | FAIL | FAIL |
| 4→8 | 0.7790297875280 | 0.00001488214034073822616483620898 | PASS | 0.0083483691575 / 0.01245960582755 | 0.00802728325209 / 0.01196910979384 | FAIL | FAIL |
| 8→16 | 0.1947394715549 | 0.000003720247060035958084152438176 | PASS | 0.00414267237734 / 0.00628193065715 | 0.00398314835308 / 0.00603480362296 | PASS | PASS |
| 16→32 | 0.04883642253904 | 9.329604924626313223708135406E-7 | PASS | 0.00206351562626 / 0.00315411324050 | 0.00198400571083 / 0.00303007549074 | PASS | PASS |
| 32→64 | 0.01220141562699 | 2.330934323312970369937735576E-7 | PASS | 0.0010298124962 / 0.00158035720198 | 0.00099012033411 / 0.0015182189960 | PASS | PASS |

The candidate was n=32 (the earliest level with the required two consecutive passing pairs, 8→16 and 16→32). n=64 completed and the 32→64 headroom comparison passed. Therefore `DUTY_CONVERGENCE_PASS=true`, `WALL_EXTREMA_CONVERGENCE_PASS=true`, `CONSECUTIVE_PAIR_RULE_PASS=true`, and `HEADROOM_RULE_PASS=true`. These mesh-policy passes do not override the final replay blocker.

## First authoritative blocker: accepted-mesh deterministic replay

`_build_success` replayed the accepted n=32 mesh. Replay failed closed with:

```text
FIRST_BLOCKER_STAGE=ACCEPTED_MESH_DETERMINISTIC_REPLAY
FIRST_BLOCKER_CODE=BLOCKED_TASK173_DETERMINISM_REPLAY_MISMATCH
CANDIDATE_N=32
N32_EXECUTION_STATE=COMPLETE
N64_EXECUTION_STATE=COMPLETE
CANDIDATE_MESH_RESULT_HASH=37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257
REPLAY_MESH_RESULT_HASH=146c8e5113369f6d0538482cde08e2e84edecbe7b2a68f6634515beac18e26c8
MESH_RESULT_HASH_MATCH=false
LOCAL_TASK172_REQUEST_AGGREGATE_MATCH=true
LOCAL_TASK172_RESULT_AGGREGATE_MATCH=true
CANDIDATE_TASK172_ATTEMPTS=149522
CANDIDATE_TASK172_HOLES=21
REPLAY_TASK172_ATTEMPTS=5441
REPLAY_TASK172_HOLES=2
FACE_ID_MATCH=UNAVAILABLE_FROM_FINAL_BLOCKED_RESULT
SAME_N32_PHYSICAL_OBSERVABLES=true
```

The production gate's mesh-hash mismatch is sufficient to trigger the blocker. The captured TASK172 aggregate request/result identities match; the captured attempt/hole counts differ. This receipt does not assert a root cause for that divergence. Face-ID equality was not separately exposed in the final blocked result and is therefore unavailable, not inferred.

The blocked Task173 receipt itself replays its own blocker hash and has a result ID bound to that hash. This is not a successful Task173 production result:

```text
TASK173_BLOCKED_RESULT_HASH=9152d974fd032279ba0f94ac7863ca8024d4a06d716b04cdb48aecfe44b9f937
TASK173_BLOCKED_RESULT_HASH_REPLAY=9152d974fd032279ba0f94ac7863ca8024d4a06d716b04cdb48aecfe44b9f937
TASK173_BLOCKED_RESULT_ID=urn:hxforge:task173:blocked:9152d974fd032279ba0f94ac7863ca8024d4a06d716b04cdb48aecfe44b9f937
TASK173_BLOCKED_RESULT_HASH_REPLAY_PASS=true
TASK173_RESULT_ID=UNAVAILABLE
TASK173_RESULT_HASH=UNAVAILABLE
```

The prior R2 mesh blocker `BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED` was not reproduced. The new hard blocker is the accepted-mesh replay mismatch. No later mesh level remained to run; the full frozen sequence had already completed.

## Final disposition and boundaries

```text
MESH_LEVELS_ATTEMPTED=1,2,4,8,16,32,64
MESH_LEVELS_COMPLETED=1,2,4,8,16,32,64
MESH_LEVELS_FAILED=none
CANDIDATE_SUBDIVISIONS_PER_INTERVAL=32
HEADROOM_SUBDIVISIONS_PER_INTERVAL=64
REAL_CASE_MESH_ADMISSIBLE=false
TASK173_RATING_RESULT_AVAILABLE=false
OLD_R2_BLOCKER_REPRODUCED=false
NEW_HARD_BLOCKER=true
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=OWNER_DIRECTION_REQUIRED_AFTER_PRODUCTION_MESH_BLOCKER
NEXT_GATE_EXECUTED=false
STOP=true
```

Changes are limited to this Markdown receipt and its machine-readable evidence. No source, tests, fixtures, dependency, lockfile, workflow, frozen authority, TASK172 acceptance policy, R98/C_round, or production mesh policy was changed. The existing untracked handoff file remains untouched and is not included in the evidence commit.

## Validation and exact-head CI

Validation results and lockfile identity are recorded in the companion JSON. The exact-head CI run/head, final gate, and runtime-budget status are recorded in the PR closeout after this evidence-only commit so the committed evidence is not rewritten after CI. The PR remains Open/Draft. No Ready, Merge, production-mesh rerun, or TASK175 action is authorized by this closeout.
