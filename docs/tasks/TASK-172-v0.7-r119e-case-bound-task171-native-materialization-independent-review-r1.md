# TASK172 v0.7 — R119-E Case-Bound TASK171 Native Materialization Independent Review

```ini
TASK_ID=TASK172_V0_7_R119E_CASE_BOUND_TASK171_NATIVE_MATERIALIZATION_INDEPENDENT_REVIEW_R1
MODE=RECORD_USER_SUPPLIED_EXTERNAL_INDEPENDENT_REVIEW_DECISION
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
REVIEWED_PREVIOUS_HEAD_SHA=3df4df347933688e38a27861916f15845ede0bbe
REVIEWED_FINAL_HEAD_SHA=dcac4c6c9f66d866670caade37b4948499aa33ef
RESULT=R119D_NATIVE_TASK171_MATERIALIZATION_INDEPENDENT_REVIEW_RECORDED
R119D_REVIEW_RESULT=PASS
REVIEW_SOURCE=USER_SUPPLIED_EXTERNAL_INDEPENDENT_REVIEW_DECISION
SELF_APPROVAL=false
CODEX_SELF_APPROVAL_CLAIMED=false
```

## Review record and scope

R119-E records the project-owner-supplied external independent review decision for the R119-D materialization at the exact reviewed final HEAD. This document is not a Codex self-review, does not rerun TASK171, and does not modify or replace R119-D evidence. The external decision is attributed to its supplied source without inventing a reviewer identity.

The decision accepts the effective R119-C selection, Variant A (`TUBE_HOT_SHELL_COLD`), and the R119-D native TASK171 execution as `VALIDATED`. It accepts that two clean independent runs used the same native request and reproduced the same native engineering identities and outputs. The topology is materially bound by the native result and its effective Definition.

## Accepted native materialization

```ini
THERMAL_ROLE_SELECTION_AUTHORITY_ID=V07-T172-R119C-THERMAL-ROLE-SELECTION-R1
SELECTED_VARIANT=TUBE_HOT_SHELL_COLD
TUBE_SIDE_ROLE=HOT
SHELL_SIDE_ROLE=COLD
TASK171_STATUS=VALIDATED
TOPOLOGY_ID=urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7
TASK171_RESULT_HASH=98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7
TASK171_MESH_IDENTITY=ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607
TASK171_PHYSICAL_OWNERSHIP_HASH=63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe
TOPOLOGY_MATERIALLY_BOUND=true
REVIEWED_TOPOLOGY_AUTHORITY_PRESENT_IN_DEFINITION=true
TOPOLOGY_AUTHORITY_ID_NATIVE_SCALAR=NOT_NATIVE_OUTPUT
```

The review accepts the existing reviewed Definition authorities and their R119-A/R119-B lifecycle without promoting a synthetic scalar `topology_authority_id`. The Definition carries the reviewed authority IDs; the native result does not emit a separate scalar under that name.

## Explicitly retained boundaries

```ini
GEOMETRY_ID=UNBOUND
GEOMETRY_ID_UNBOUND_REASON=NO_REVIEWED_NATIVE_AGGREGATE_CASE_GEOMETRY_ID_CONTRACT
FLUID_IDENTITY_BOUND=false
PROPERTY_PROFILE_AUTHORITY_ID=UNBOUND
PRODUCTION_MESH_PROFILE_AUTHORITY_ID=UNBOUND
REAL_CASE_MESH_ADMISSIBLE=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
```

The materialized TASK171 structural `mesh_identity` is not a production mesh profile or production-mesh admission. No aggregate geometry identity, fluid/property binding, TASK172 implementation, or downstream solve is accepted or implied by this review.

## Replay and source verification

At the reviewed final HEAD, the R119-D evidence canonical hash replays to `7a76c7cc118c88a5ef7d1e40add66915e6b93190bfae15a31aee4687ab01e1af`; its registry extension canonical hash is `6d46819673b2948a74a10a39623fab4c0cb311cf31c0a92543201941d5a4b261`; and its registry root is `87ccdf23451be87b4fd3142e7181d4a602ff9611ef1f8824d5b19d2b0a827d44`. The R119-D evidence file and R119-D extension agree with the supplied native IDs, selected variant, run count, and boundary states.

The supplied exact-head CI run `36378456878` was checked against the reviewed HEAD using the complete job collection: completed/success, 50 jobs, 45 success, 5 skipped, 0 failed, 0 cancelled, final-gate success. This check corroborates the supplied CI facts; it does not convert the externally supplied R119-D review into a Codex review.

No TASK171 producer was invoked for R119-E. R119-A, R119-B, R119-C, and R119-D artifacts are unchanged. The PR remains OPEN + Draft; Ready and Merge remain unauthorized.

```ini
TASK171_NATIVE_PRODUCER_INVOCATION_COUNT=0
R119A_ARTIFACTS_REWRITTEN=false
R119B_ARTIFACTS_REWRITTEN=false
R119C_ARTIFACTS_REWRITTEN=false
R119D_ARTIFACTS_REWRITTEN=false
PRODUCTION_CODE_CHANGED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
STOP=true
```
