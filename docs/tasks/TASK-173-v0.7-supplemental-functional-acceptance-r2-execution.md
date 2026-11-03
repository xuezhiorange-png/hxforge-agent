# TASK173 v0.7 Supplemental Functional Acceptance R2 — Execution Disposition

```text
TASK_ID=V07_TASK173_SUPPLEMENTAL_CONTROLLED_EXECUTION_R1
SUPPLEMENTAL_ACCEPTANCE_ID=V07-T173-SUPPLEMENTAL-FUNCTIONAL-ACCEPTANCE-R2
EXECUTION_HEAD=7d9b98ebd5aab3108b7637a63c32000c27ce6697
EXECUTION_TREE=ec83f926e71ba33839f6fbdb197fe6091d5cf4ce
PUBLIC_SIZING_INVOCATION_COUNT=1
OUTCOME=BLOCKED
FAILURE_STAGE=RUNTIME
FAILURE_CODE=BLOCKED_SIZING_RUNTIME_FAILURE
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
TASK175_EXECUTED=false
GOLDEN_G05_ACCEPTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

## Frozen inputs and pre-execution gate

The pre-execution correction was committed as `7d9b98ebd5aab3108b7637a63c32000c27ce6697`, whose parent is the requested baseline `fd725fafb005014e82bcd24526524fb0bc58a315`. The supplemental request, requirement and candidate-space identities were not changed. The committed frozen-input replay passed before the one public call and was rerun as a non-solving check after the call.

| Item | Frozen identity |
| --- | --- |
| Sizing request | `e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e` |
| TASK168 candidate space | `480e3249300d4b4a0668815cd18ebb7ed6fb5cf507c073449c9a509526eea668` |
| Requirement authority | `8dd46475acbdfd46caf3e6a6bddc89a74ba707beb21735f713d482e7bd19696e` |
| Sizing authority package R2 | `750c1f76953f46b63de90f2c21302160746e890cf4c61227538397e69b8501a9` |
| Numerical authority R2A | `25bb3c27ca0610e217f29581d28d86cbae560a868b35bd031276355603b4733e` |

The frozen candidates were H1 (`0.225`, `68a99368-a518-5482-b9df-4bc3357edea9`, `bd0da145a592652e55a6fc8cd325a98d6f1cf349ed74b98e811d1343ce62ed54`), H2 (`0.275`, `aa70248a-9f76-542d-bc77-1e935b9c32d4`, `a30d1b0c01dcd0607bdd46e720a3a278e6b90b265b6bd4f109eb2c1cae58d8c5`) and H3 (`0.350`, `f3e14759-e05b-5088-bfb5-b6e16e918267`, `b5bcf9258ff1cd455eab071a55cbdce7d8708391d1737e44d3dae2bccdaedb7e`). No outcome-based reselection occurred.

P0 exact-head CI passed before execution on run `37777056627`, head `7d9b98ebd5aab3108b7637a63c32000c27ce6697`: 45 jobs succeeded, 5 were skipped, none failed or were cancelled. The longest PR-head shard was 486 s (the longest merge-ref shard was 504 s); both are below the separate 540 s shard budget. P0 also included the narrow Ruff import-order correction to the frozen-input replay and an additive erratum for the malformed R2 authority hash in the earlier review receipt; the historical receipt itself was not overwritten.

## One controlled public execution

Exactly one `validate_sizing_request` call was made with the reconstructed native frozen request. There was no direct Candidate Rating call, no retry and no second public Sizing call. The full returned blocked-result preimage is preserved in `docs/tasks/evidence/TASK-173-v0.7-supplemental-functional-acceptance-r2-execution.json`.

The result was `Task173SizingBlockedResult`, status `BLOCKED`, stage `RUNTIME`, code `BLOCKED_SIZING_RUNTIME_FAILURE`. The blocker was a Pydantic serialization failure for the Python-native `ReferencePlanePair` while processing candidate Rating provenance. Request hash was `e5b085d238b2b1d9d7bcf23873c3ef04650135785fa4e6be1598aed3b8a9ab1e`; result hash was `d170e8abddb9ce3322ec02e9f6f04d97b8604fd0095ae00ea1f5badace00547b`; result ID was `urn:hxforge:task173-sizing:blocked:d170e8abddb9ce3322ec02e9f6f04d97b8604fd0095ae00ea1f5badace00547b`. Elapsed runtime recorded by the execution evidence was 30,728.228776708012 s.

The top-level blocked result did not return per-candidate Rating result projections, mesh ledgers or hard-constraint ledgers. Accordingly, H1/H2/H3 Full Rating statuses and Duty/Tube DP/Shell DP constraints are `NOT_RETURNED`; constraint evaluation, Ranking, Recommendation, Alternatives, candidate exclusions and their provenance were not reached in the returned result. No candidate is classified as passing or failing a numerical or engineering constraint by this receipt. These missing observations mean the supplemental functional acceptance is blocked/partial and TASK173 Sizing is not complete. This is not Golden G05 acceptance.

## Replay and scope

The companion `TASK-173-v0.7-supplemental-functional-acceptance-r2-execution-replay.py` reconstructs the committed frozen request without calling Rating or Sizing, verifies the three frozen candidate identities, binds the execution to its exact source commit/tree, validates the blocked-result schema projection, and recomputes the canonical result hash and result ID.

Completion R1 and its Candidate A/B identities/results remain unchanged. R2 and R2A authorities, tolerances, mesh policy and candidate space remain unchanged. No production code or tests were changed for this execution closeout. TASK175 was not run; PR #283 remains Draft; no Ready or Merge action was taken.

```text
FROZEN_INPUT_REPLAY=PASS
BLOCKED_RESULT_PREIMAGE_REPLAY=PASS
BLOCKED_RESULT_HASH_AND_ID_REPLAY=PASS
CANDIDATE_RATING_RESULTS=NOT_RETURNED_BY_BLOCKED_SIZING_RESULT
HARD_CONSTRAINTS_RANKING_RECOMMENDATION=NOT_REACHED
TASK173_SIZING_COMPLETE=false
TASK173_COMPLETE=false
```
