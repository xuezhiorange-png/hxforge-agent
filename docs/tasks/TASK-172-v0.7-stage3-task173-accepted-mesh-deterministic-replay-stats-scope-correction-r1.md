# TASK173 accepted-mesh deterministic replay stats-scope correction R1

## Closeout

```text
TASK_ID=STAGE3_TASK173_ACCEPTED_MESH_DETERMINISTIC_REPLAY_STATS_SCOPE_CORRECTION_R1
MODE=NARROW_DETERMINISTIC_REPLAY_IMPLEMENTATION_CORRECTION
RESULT=PASS_TASK173_ACCEPTED_MESH_DETERMINISTIC_REPLAY_STATS_SCOPE_CORRECTION
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
SOURCE_HEAD=97d89acee2713acfd44b493ed1b5500667094227
FINAL_EVIDENCE_HEAD=LINKED_BY_EXACT_HEAD_CI_CLOSEOUT_RECEIPT
PREDECESSOR_BLOCKER=BLOCKED_TASK173_DETERMINISM_REPLAY_MISMATCH
EVIDENCE_CANONICAL_HASH=7ff11ea47df375479d0a7c4437999a7b255c69de92b2d62dcb2bc6c7e6333cc4
```

## Bounded root cause

The preceding fresh production-mesh execution completed n=1, 2, 4, 8, 16, 32, and 64, with candidate n=32 and n=64 headroom, then failed at accepted-mesh replay. Candidate `_run_mesh_sequence()` created one fresh `_CellSearchStats` per mesh level and passed it through the complete `_solve_outer_boundary()` search. Before this correction, `_build_success()` replay called `_solve_outer_boundary()` without stats; `_valid_trajectory()` consequently created trial-local counters. The hash-bound attempt/hole diagnostics therefore had different scopes although TASK172 request/result aggregates and physical observables matched.

```text
ROOT_CAUSE=ACCEPTED_MESH_REPLAY_USES_DIFFERENT_SEARCH_STATS_SCOPE_THAN_CANDIDATE
ROOT_CAUSE_CLASS=DETERMINISTIC_REPLAY_INSTRUMENTATION_SCOPE_MISMATCH
NEW_PHYSICAL_NUMERICAL_DEFECT=false
TASK172_DOGBOX_DEFECT=false
MESH_CONVERGENCE_DEFECT=false
```

## Correction and identity boundary

`_build_success()` now creates a fresh empty `_CellSearchStats` and passes that same object through the entire accepted-mesh outer-boundary replay. Candidate execution remains unchanged. The rating projection remains `task173.mesh-rating-run.v1`; attempt count, hole count/code map, hole neighborhoods, and outer-bisection iterations remain hash-bound. The exact mesh-hash, face-ID, and local TASK172 result-hash replay gates are unchanged and are not tolerance-based.

The two focused regressions verify (1) candidate and replay use distinct fresh stats objects, each spanning all outer trials, and (2) equal projections hash identically while changing hash-bound stats changes the hash.

## Targeted n=32 replay

One targeted replay used the canonical TASK173 request hash and current native Stage-2 authority chain; no other mesh level and no complete production mesh sequence were rerun. The accepted result exactly matches the prior n=32 candidate hash. The replay captured all 161 tube and 161 shell face IDs and all 160 local TASK172 result hashes. Their ordered result-hash aggregate matches the persisted n=32 candidate aggregate.

```text
TARGET_N=32
REFERENCE_CANDIDATE_MESH_RESULT_HASH=37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257
TARGETED_REPLAY_MESH_RESULT_HASH=37866f43f74502f76e2fe94f31b8ab6006e68ae9286a625c6d78dca4ed360257
TARGETED_N32_MESH_HASH_MATCH=true
TARGETED_N32_FACE_ID_REPLAY=PASS
TARGETED_N32_LOCAL_TASK172_HASH_REPLAY=PASS
TARGETED_REPLAY_TASK172_ATTEMPTS=149522
TARGETED_REPLAY_TASK172_HOLES=21
```

The machine evidence contains the complete ordered face-ID and local-result-hash lists, outer-trial observations, hash-bound hole-code map, and accepted physical observables. The previous full mesh execution receipt remains unchanged and remains `BLOCKED_PRODUCTION_MESH`; this correction closes only its deterministic replay blocker. Because production code changed after that full execution, `REAL_CASE_MESH_ADMISSIBLE=false` pending a fresh production execution from n=1.

## Validation and scope

Local validation passed focused correction tests, focused TASK173 and TASK172 suites, full shell-tube suite, HTTP/API regression, Ruff, format, CI-scope mypy, manifest D==M, pip-audit, `uv lock --check`, and `uv sync --locked --all-extras`. `uv.lock` and dependencies are unchanged. Final diff and changed-evidence duplicate-key checks are recorded in the machine evidence.

No TASK172, schema, authority, mesh policy, convergence threshold, fixture, dependency, lockfile, workflow, or TASK175 changes were made. No full production mesh was rerun.

```text
NEXT_GATE=STAGE3_TASK173_PRODUCTION_MESH_REEXECUTION_FROM_N1_AFTER_REPLAY_CORRECTION
NEXT_GATE_EXECUTED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
STOP=true
```
