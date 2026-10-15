# Candidate A exact-cell Decimal-q recovery diagnostic R2

## Disposition

The low-cost preflight passed and the single authorized n=32 reconstruction ran once. It reproduced Candidate A's frozen accepted-trajectory failure at support 2. Offline replay subsequently verified all 749 captured target-cell Task172 request/result identities and both frozen endpoints.

No Decimal-q probe ran. The diagnostic stopped before its first Decimal/provider call because the runner attempted to rehydrate a saved JSON request projection using strict native-object Pydantic validation. This is an evidence-runner defect, not a production numerical result. The runner's replay hydration was corrected after the execution, and the captured evidence now replays without another solve. Per the execution authorization, no probes or reconstruction were retried.

`POINT_ROOT_RECOVERED=NOT_TESTED`; finite probes were not executed, so this receipt does not establish whether another q inside the frozen interval satisfies the unchanged `abs(F) <= 1e-6 W` rule.

## Frozen target and reconstruction

- Start/reconstruction head: `2348b977e71d8f88f4107fceab35392962f8aa92`
- Runtime source: `21386a88f8290538172e9389ed46f50c3697a426`, tree `ce61a818b82f908729d2bdf4553cc27012354952`
- Candidate A: `adeab5b1-a339-5eb3-aa66-011ffe49bac0`, hash `f272f9b04087d400d8fc554619d34e9193fc77c481f995addf3cf4b7a7bf4767`
- Candidate Rating request: `1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7`
- Completion request: `5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae`
- Native TASK168 space: `aeb350ec6759c388122fd9a00c5d8cc962768ddcc46162e6af3bff38c11b74ea`
- Mesh `n=32`; support URI ends `:support:2`; subdivision index `21`, interval `[3.1875, 3.2250] m`
- Cell IDs: tube `urn:hxforge:task173:candidate-cell:tube:e9548de1732d080e5843b5f1c8ef85bd85e73efd593ed68cdbfe21b75deb2b07`; shell `urn:hxforge:task173:candidate-cell:shell:42c2126675fde297b6f4474e16add0f8200d308d1ce2b600c0ca620a69b02fae`; wall `urn:hxforge:task173:candidate-wall-interface:a22cf4ea8e56f7eeb5f05bd1e118fc78574b639aac96e687642841b8a242f519`
- Failed accepted trajectory: outer iteration `24`, shooting enthalpy `107518.9165931962933844840526580810546875 J/kg`
- N=32 outcome and frozen blocked-result diagnostics matched; Task172 evaluations/calls `144217`; numerical holes `27` (`BLOCKED_RESIDUAL_ACCEPTANCE`); target-cell trials `749`

The failed-cell upstream tube and physical-left shell state hashes match both endpoint trial records exactly: tube `b335dae1d8e93a7216e89a4ff58b605c757bbb09132a0153b830daaa3463ba11`; shell `5c494d381d97fa46f5da7f25d356a54f6eae1d9529328deeff6ce452b69212a1`.

The exact failed-cell state, support/cell identities, upstream tube and shell states, all target trials, and both endpoint Task172 preimages are in the machine summary. The original R2 raw evidence, checkpoint, and trace were left untouched in the R2 execution directory.

## Frozen endpoint replay

Both q values are adjacent binary64 numbers (`0x1.0c6c4035ce00bp+8` and `0x1.0c6c4035ce00cp+8`). Native Task172 results were `VALIDATED`; the complete endpoint requests/results and provider snapshots replayed by identity.

| Side | q (W) | Native-context F (W) | Exact binary64 F (W) | Task172 request hash | Task172 result hash | Task172 q (W) |
|---|---:|---:|---:|---|---|---:|
| Left | 268.4228547695099 | -0.0000053178744 | -0.00000531787438903399226255714893341064453125 | `4fa675e1a36bd49c67957d2ed0a9dbef808529ffef7f2bdc6b51153da421c754` | `748819390174c8a2fa88f980b5073366817cce9d158c8bf9c56c52dd66e07ee9` | 268.4228600873843 |
| Right | 268.42285476950997 | +0.00001519025227 | +0.000015190252267809426598250865936279296875 | `b2472ec62e4a9e53517cdb5cc3a3f6c8d70106cd2cf34663ed2191bdaa9ce072` | `ea8869a56cdd300ba42631aa967958aa01daa7e462ed7e5134b10d3d19893573` | 268.4228395792577 |

Neither frozen endpoint meets the ordinary root tolerance. The endpoint-pair minimum absolute residual is `0.00000531787438903399226255714893341064453125 W`; this is not a minimum over Decimal probes, because no Decimal probes ran.

At these endpoints, three of four provider PH enthalpy float inputs and their output snapshot hashes are identical. The tube-midpoint PH input differs by one binary64 step and its output snapshot hash differs. This confirms partial endpoint-coordinate collapse, not a complete provider-state plateau. Task172's returned q differs by `-0.0000205081266 W` across the endpoint pair. The captured evidence does not establish whether this change is due solely to provider state quantization or includes local Task172 solver sensitivity.

## Why probing stopped

After the n=32 solver returned the frozen blocked outcome, `_check_capture_replay()` tried to rebuild `CandidateTask172LocalRequest` from `model_dump(mode="json")` data with `strict=True`. That JSON projection contains Decimal strings, lists, and Python-native nested dataclasses; it is not the strict native runtime input contract. Pydantic raised a 31-field `ValidationError` before the runner entered `_run_decimal_probes()`.

The original execution receipt therefore records `DECIMAL_Q_PROBE_COUNT=0`. The runner replay path now hydrates stored JSON projections with `strict=False` and then verifies the native request/result hashes. Offline replay passed for all 749 target-cell calls and both endpoints. This post-execution evidence correction did not call a provider or solver and did not resume the diagnostic.

## Preflight, replay, and scope

Pre-execution preflight passed: valid-result observer, blocked-result observer, Decimal-probe blocked-result branch, unknown-type fail-closed, observer-exception recovery, checkpoint-exception recovery, and frozen R1 identity preservation. The blocked Task172 path uses its real `request_hash`, `blocked_result_hash`, `failure_code`, and `field_path`; it does not invent `result_id`.

Post-execution replay passed:

- R2 raw evidence canonical hash and trace sequence
- all 749 captured target-cell Task172 request/result identities
- both exact endpoint request/result hashes and F values
- provider snapshot hashes and frozen binary64 adjacency
- compact summary and trial-ledger canonical hashes

The checkpoint and trace preserve evidence; they do **not** support solver continuation or restart. The large original raw files are retained locally and identified by SHA-256 in the compact machine summary; they are not copied into the commit. The committed summary carries the complete failed-cell preimage, both complete endpoint request/result/provider preimages, and a compact identity/F/provider-coordinate ledger for all target-cell trials.

No production, TASK172 contract, R2A authority, or numerical tolerance changed. No Candidate Full Rating, public Sizing, or TASK175 execution occurred. PR #283 remains Draft; Ready and Merge are unauthorized.

## Next action

Require owner direction before any additional numerical probe. The narrow next step is to keep the corrected evidence-only hydration/replay path and, if explicitly authorized, run a separate Decimal-probe-only diagnostic from the captured failed-cell state with request/result/upstream identity gates. Do not repeat the 144,217-call n=32 reconstruction unless owner direction makes that necessary.
