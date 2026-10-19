# TASK172 Stage-2 TASK166 Native Replay Divergence Adjudication R1

## Disposition

**Result:** `STAGE2_NATIVE_REPLAY_CORRECTION_CANDIDATE_PENDING_SINGLE_INDEPENDENT_REVIEW`

This is a traceability/native-replay correction, not an engineering redesign. The Stage-3 TASK173 draft remains uncommitted and unchanged. TASK173 and mesh convergence were not executed. No self-approval is claimed.

## Finding

The accepted Stage-2 TASK166 identity `ed3c9b1d-b303-5b50-9faf-ba1a1fd927df` / `3b639d0523b799f92bdf59ebee415dc263dac5164ab816cb5fb7df5b3ed37cb7` appears only as a summary identity in the Stage-2 closeout evidence. A search of the committed Stage-2 evidence, source, tests, Git history/hash occurrences, and retained replay material found no native TASK166 request/preimage. Consequently, the historical request-field comparison and the first differing field are **unresolvable**; no absent preimage is inferred.

Two clean independent native producer chains were reconstructed from the accepted R118-C R9 native inputs and R118-D reviewed evidence. Both chains produced byte-identical public TASK031, TASK032, and TASK166 results:

| Producer | Native result identity | Request hash |
|---|---|---|
| TASK031 | `82b051f6-d8f6-5bbb-b46f-76609b9f8cca` / `1dc32d501ee1ba283e4d2bb5eab2f2f5ffc81e464fd6f254ff13b02ceb01519e` | `688c13a7d9022338fba1787be6a0a0867bd3e37e1bac2528fcae101cb66adb58` |
| TASK032 | `8a43b528-acca-5388-8f82-cd85e53b820e` / `58e47124f94d14ece0f1c93a0bb5510b7dda52bfbc60b9f650fbf72c1eb232d2` | `942c339c85a585d51be5a6431b17ae3f4064d2ae9d6166a51cdf4651e444e13e` |
| TASK166 | `ad4745b7-fa18-519f-99c2-e76b12bb23dc` / `a42aee19a2fbb77d1666e4b7170b86e3a9e036f992ef8030a9c2ecf1928c151d` | `1083b8fbaef93ef2370b63364b3fd9e40f2ba0e98d2c8dd1b852f2da158967c2` |

The replay used the accepted TASK020/TASK021/TASK022/TASK024 identities and the reviewed R2 case inputs. The current TASK166 request consumes the public, quantized TASK032 flow result. Whether the historical Stage-2 execution used those quantized values cannot be determined without its request preimage: `TASK032_QUANTIZATION_PATH_DIFFERENCE=UNRESOLVABLE`.

## Engineering and output comparison

No project engineering input divergence was found (`ENGINEERING_INPUT_DIVERGENCE_COUNT=0`). The R9 geometry and R2 operating point are unchanged. The corrected native total is `695.60879452416523317091096372842532069004685992373 Pa`; Stage 2 recorded `695.60879452416523317091096373830961547685621804079 Pa`. The absolute difference is `9.88429478680935811706E-27 Pa` (approximately `1.420956E-29` relative). This small numerical difference does not waive the canonical identity mismatch.

The persisted central-crossflow, window, and both end-zone contribution values also differ in final Decimal digits; each is classified `NUMERIC_DIFFERENCE`. Other Bell geometry, coefficient, factor, and parameter-row details are unavailable in the Stage-2 summary evidence.

The conditional owner-authorized disposition is met: retain the old identity as `SUPERSEDED_NONREPLAYABLE_STAGE2_IDENTITY`, and supersede it with the deterministic replayable native identity `a42aee19…`. Historical Stage-2 artifacts are not rewritten.

## Historical TASK172 R2 replay source

The historical TASK172 request/result hashes (`14f5496a…` / `59cfd30e…`) were reproduced using `tests/exchangers/shell_tube/test_task172_local_runtime.py::_native_shell_flow_authority()`. That helper is expressly a test fixture: it includes `native-test-fixture`, a test freeze comment, placeholder TASK031/TASK166 request and provenance hashes, and manually constructs `Task166Result`.

Therefore:

- `STAGE2_TASK172_R2_REPLAY_SOURCE=TEST_FIXTURE_CHAIN`
- `TASK172_RUNTIME_TEST_FIXTURE_REPLAY=PASS`
- `TASK172_REAL_CASE_REPLAY_CLAIM_VALID=false`
- `TASK172_RUNTIME_IMPLEMENTATION_VALIDITY_UNCHANGED=true`
- The original Stage-2 real-case native shell-flow replay was `NOT_PERFORMED`.

Using the recovered native TASK031 geometry and corrected native TASK166 result, TASK172 was then run twice with a real `ShellFlowAuthority`; the results were identical and valid. The real native result is request `58c6d63be2ceb8dec0e0b912828068c19368cd920bc3a8af259e2b3a93daba9e`, result ID/hash `urn:hxforge:task172:14feaec9190e5e00be79f638db8e5e572adf83788a628b56b4ba1d9b20036e63` / `14feaec9190e5e00be79f638db8e5e572adf83788a628b56b4ba1d9b20036e63`, with signed heat rate `19432.067821726272 W`.

## Corrected hydraulic binding

The corrected native TASK174 orchestration was replayed against the corrected TASK166 result and a newly replayed TASK029 native result. TASK174 returned `VALIDATED`, result ID/hash `urn:hxforge:task174:ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419` / `ccb62cd76c6089840291cc37bf2f32dcad44d6e0ba3a0616792963b04233f419`. The shell outlet pressure is `100629.39120547583476682908903627157467930995314008 Pa`; tube outlet pressure is `100888.042 Pa`. The 19-event Bell allocation and native decomposition validation remain intact. This new TASK174 identity does not rewrite its historical predecessor.

## Boundaries and evidence

- `STAGE3_DRAFT_PRESERVED=true`; its two modified TASK172 helper files and untracked TASK173 draft package remain uncommitted.
- `TASK173_SOLVE_PERFORMED=false`; `MESH_LEVELS_EXECUTED=0`.
- No production code or tests changed for this adjudication.
- Historical Stage-2 evidence and registry extensions remain unchanged; the correction is appended.
- The full native request/result projections for both runs are stored once under the shared payload and referenced by both run receipts, since the independently produced public payloads are byte-identical.

Evidence:
- [Replay correction evidence](evidence/TASK-172-stage2-native-shell-flow-replay-correction-r1.json)
- Evidence file SHA-256: `d8ecebcd891b9646826cd362069d0859aafeae0c01c6baa8b3a0dd4917955d92`
- Evidence canonical hash: `3ed4da6385097e1ee57196c5946d37943d073d4506e35149ef57ad9183cdd100`

Next gate: `STAGE2_NATIVE_REPLAY_CORRECTION_SINGLE_INDEPENDENT_REVIEW`

`STOP=true`
