# Candidate A exact-cell Decimal-q recovery diagnostic R1

## Disposition

`BLOCKED_DIAGNOSTIC_RUNNER_OBSERVER_FAILURE`. This attempt does not establish whether an ordinary point root exists, whether provider PH states plateau, or whether a new numerical authority is needed. The isolated reconstruction failed inside the evidence observer before it persisted the target cell trace; no Decimal probes were run.

## Frozen identity and execution boundary

- Start head: `b3df78adf32b5469bdac5f6f41a50f2f0e94e8da`.
- Runtime source: `21386a88f8290538172e9389ed46f50c3697a426`, tree `ce61a818b82f908729d2bdf4553cc27012354952`.
- Runtime-bound paths were byte-identical and clean at the start head.
- Candidate A request hash reconstructed from the committed completion request and candidate-native upstream chain: `1c1c98cb0ce304957479e31d3a9f7adb38e41c2b6bb7240e37a9face758171d7`.
- Frozen completion request: `5cd05f7d390718e11e2209d83f8eef0e35bc6f33afe9217e5d8a425b1c17daae`.
- Frozen failure receipt hash: `daf0f61109676d50e9dac2c1d5ceb9afb206b232bc039fc0253f5b1ecdba774c`.
- Target was limited to n=32 and Candidate A support 2; no other candidate or mesh was substituted.

The runner called the private n=32 transient/accepted-trajectory boundary entrypoint once. It did not call `validate_candidate_rating`, public Sizing, or TASK175. This is a partial isolated reconstruction, not a complete Candidate Rating execution.

## What happened

The native Task172 call returned a `Task172BlockedResult`. The diagnostic observer assumed that every Task172 result has `result_id`; that field exists on `Task172LocalResult`, but not on `Task172BlockedResult` (which carries `blocked_result_hash`). Accessing `result.result_id` raised `AttributeError` after the native call and interrupted the diagnostic path. Because the first runner version did not checkpoint its in-memory capture on an unexpected observer exception, endpoint preimages, exact cell states, and final Task172 call counters were not persisted.

The process ran for `7145.600296166958` wall seconds. Its last emitted progress marker was 140,000 Task172 validations; the exact count was not persisted, so the only defensible count is a lower bound of 140,001. The frozen comparison target was 144,217 validations and 27 numerical holes, but those totals were not independently established by this interrupted run.

The diagnostic runner has been corrected locally to represent `result_id` as optional for blocked Task172 results, preserve `blocked_result_hash`/failure details, and retain partial capture on observer exceptions. The correction has not been solver-executed. Replay of the committed failed-attempt receipt verifies its canonical envelope only; it explicitly reports that exact cell evidence was not established.

## Validation performed

- Completion request replay: PASS.
- Failed diagnostic-attempt canonical receipt replay: PASS; reports `EXACT_TARGET_CELL_EVIDENCE_REPLAY=NOT_ESTABLISHED` and zero probes.
- Focused Q13 / event / accepted-projection regressions: 12 passed.
- Task172 local runtime identity test file: 33 passed.
- R2A and H2 evidence replays at their original evidence head `6a3b0c47d1af2e16f9e0a8d225b6d8265a6ffe3a`: PASS (16 events, 57 endpoint request/result identities, 16 continuations, 8 certificates, 5 trajectories; H2 addendum had 3 identity replays).
- Running those historical replay entrypoints at `b3df78…` correctly fails their frozen runtime-path byte-identity guard because later production commits changed paths bound to the old R2A runtime. This is distinct from the original-head replay, which passed.
- Exact-head CI is run after this evidence-only commit and reported separately from the 540-second runtime budget.

## Numerical findings

| Item | Result |
|---|---|
| Exact target cell reconstructed | No |
| Exact LEFT/RIGHT Task172 request/result preimages | Not persisted |
| Exact F values | Not available |
| Decimal q probes | 0 |
| Validated Decimal probes | 0 |
| Minimum absolute F | Not established |
| Ordinary point-root recovered | No; not tested |
| Provider PH plateau | Not established |
| Task172 discontinuity | Not established |
| Production fix scope | Undetermined; no production change proposed |
| New numerical authority required | Undetermined |

In particular, the two rounded q endpoints alone do not establish a provider plateau or a failure of the frozen `abs(F) <= 1e-6 W` criterion. This attempt supplies no root-existence or root-nonexistence evidence.

## Boundary and next step

`PRODUCTION_CODE_CHANGED=false`, `R2A_AUTHORITY_CHANGED=false`, `PUBLIC_CANDIDATE_FULL_RATING_REEXECUTED=false`, `PUBLIC_SIZING_REEXECUTED=false`, and `TASK175_EXECUTED=false`. Candidate space, completion request, Task172 contract, provider policy, and tolerances remain unchanged.

The minimum instrumentation correction is the optional Task172 blocked-result identity handling described above, with durable partial-capture preservation. Repeating the same isolated n=32 reconstruction would be another approximately two-hour computation. No repeat is started under this receipt; explicit owner direction is required before running it again. A future successful reconstruction must still match the frozen failure, n32 evaluation/hole counts, target support, endpoints, and native endpoint identities before any Decimal probe is permitted.

PR #283 remains Draft. `READY_AUTHORIZED=false`, `MERGE_AUTHORIZED=false`, `TASK173_SIZING_COMPLETE=false`, and `TASK173_COMPLETE=false`.
