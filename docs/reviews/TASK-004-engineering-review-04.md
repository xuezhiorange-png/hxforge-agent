# TASK-004 Engineering Review — Round 4

**PR:** #9
**Code head reviewed:** `bd77c2db5cc48057d2f4c8dd0b09356686eaa0c0`
**Decision:** CHANGES REQUIRED
**CI:** Run `27912604333` passed.

Three final gaps remain.

## 1. Strict recursive immutability

`deep_freeze()` returns an existing `MappingProxyType` without recursively checking its values. The message and provenance modules also use local helpers that return unknown values unchanged.

Required:
- recursively validate or rebuild mapping-proxy contents;
- use the shared strict freeze rules for message, failure and provenance metadata;
- test nested mutable containers, unsupported custom values and JSON round trips.

## 2. Required git identity

`CalculationRun.git_commit` still defaults to `no-git`, so callers may omit it.

Required:
- remove the default;
- require an explicit 7–40 character hexadecimal SHA or exact `no-git` sentinel;
- test omitted, invalid, normalized and round-trip cases.

## 3. Record synchronization

The PR body records an older head. The task card contains both 456-test and stale 419-test records and does not include the current review round.

Required:
- synchronize PR head, test total and CI run;
- make the task card internally consistent;
- mark Round 3 addressed and Round 4 pending.

Keep TASK-004 IN_PROGRESS and PR #9 Draft. Do not start TASK-005.
