# TASK172 fail-only dogbox fallback R3 authority independent review

```ini
TASK_ID=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_R3_INDEPENDENT_REVIEW
MODE=FINAL_INDEPENDENT_AUTHORITY_REVIEW_WITH_SELF_CONTAINED_SOURCE_PACKET
RESULT=PASS_FAIL_ONLY_DOGBOX_FALLBACK_R3_AUTHORITY_INDEPENDENT_REVIEW
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
REVIEWED_HEAD=4e6b5c6e674c3630fe6adab3c53b9009019b04e1
REVIEW_SOURCE=Fresh-context Codex sub-agent reviewer Zeno (GPT-6); complete source packet supplied inline; no inherited conversation context
REVIEWER_AGENT_ID=01a0fcb1-f732-7982-b256-ab230e665f10
SELF_APPROVAL=false
CANDIDATE_AUTHOR_SELF_APPROVAL=false
REVIEW_PACKET_SHA256=1d0e6eb0d806c1132d3577af94f17746118d2ed9c20b9b24b8caa3177fb7a0ab
REVIEW_PACKET_SOURCE_COUNT=32
REVIEW_EVIDENCE_CANONICAL_HASH=2a6c9f398c9483d8a2e95bf10c91c540453b537b28969b602189dac3267bfc07
```

## Locked review object and lineage

The reviewer independently examined authority `V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3`, canonical hash `9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b`, and R3 evidence hash `e9677c64a5e7d0d32f3129228bcf4bf17098a73ea2339a442d030c9acd01ac5c`. The packet was mechanically built from Git blobs at the authorized source HEAD. It contained all requested authority/evidence files as full files and exact source excerpts with line ranges and source-file SHA-256 values; its manifest declared no source summarization or semantic modification.

The lineage distinguishes the R1 review (`NUMERICAL_OUTPUT_PORTABILITY_ENVELOPE_NOT_FROZEN`, evidence hash `1741d3883ed986bbc2a71e672118376395f68def1bc8e11c9997d162f821980e`), the R2 candidate and its R2 review receipt (`EXACT_ZERO_Q_PORTABILITY_STATUS_UNSPECIFIED`, receipt HEAD `6063149fc5fbecd448b7d6c04d5df02cde427a9c`, evidence hash `8a2943ab1db04e2551fd766f916dc3fd09981f6e37894fa8b61d6d013184f5ff`), and the R3 candidate. The reviewer found both prior findings closed by R3.

## Review disposition

The R3 exact-zero rule is internally consistent and fail-closed: exact zero is `Decimal("0")`; a zero/nonzero pair fails before the q numerical floor; two exact zeros pass q semantics; and the ordinary q envelope applies only when both values are nonzero. Twi and Two remain independently compared against their frozen absolute limits. The q projection is limited to signed duty and the two wall temperatures. Existing six-target and n=16 evidence passes; the 68-row evidence proves the numerical envelope only, while exact-zero rowwise coverage remains explicitly unavailable and is not inferred.

The reviewer confirmed consistency with the existing TASK173 exact-zero behavior without transferring that authority's scope. The fail-only dogbox candidate remains a narrow overlay on unchanged R94: primary TRF 6/24; fallback only for a replay-valid residual-acceptance blocker, from the original deterministic R94 seed, using dogbox 6/24; valid primary results and non-residual blockers bypass fallback; fallback fails closed and must independently satisfy original R98. Same-environment exact replay remains required, cross-platform exact result hash equality is not required, and the work budget is bounded. R94, R98, physics, property domain, and production behavior are unchanged; portability does not participate in solver stopping or residual acceptance.

The review was source-only. No numerical characterization, solver experiment, production correction, production mesh, or TASK175 work was performed. The packet SHA-256 and complete source manifest are recorded in the machine receipt.

```ini
R1_REVIEW_FINDING_CLOSED=true
R2_REVIEW_FINDING_CLOSED=true
EXACT_ZERO_STATUS_MATCH_REQUIRED=true
ZERO_NONZERO_PAIR_WITHIN_NUMERIC_FLOOR_ALLOWED=false
TARGET_FULL_PROJECTION_PASS=6/6
N16_PORTABILITY_ENVELOPE_PASS=true
CORPUS_NUMERICAL_ENVELOPE_PASS=68/68
CORPUS_EXACT_ZERO_STATUS_COUNT=UNAVAILABLE_NOT_PRESENT_IN_PERSISTED_AGGREGATE
NUMERICAL_EXPERIMENTS_PERFORMED=false
AUTHORITY_ID=V07-T172-R94-FAIL-ONLY-DOGBOX-FALLBACK-R3
AUTHORITY_CANONICAL_HASH=9a226f98de9dc40025fd4e26f83ce22f29df0b6ba10542ac282cc97f739b4b6b
AUTHORITY_LIFECYCLE=REVIEWED_AUTHORITY
AUTHORITY_ACCEPTED=true
CORRECTION_IMPLEMENTED=false
PRODUCTION_MESH_REEXECUTED=false
REAL_CASE_MESH_ADMISSIBLE=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
PRODUCTION_CODE_CHANGED=false
TESTS_CHANGED=false
FIXTURES_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILE_CHANGED=false
WORKFLOWS_CHANGED=false
REGISTRY_CHANGED=false
EXACT_HEAD_CI=TO_RUN_ON_REVIEW_RECEIPT_HEAD
CI_RUNTIME_BUDGET_GATE=TO_BE_RECORDED_FROM_EXACT_HEAD_CI
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE3_TASK172_FAIL_ONLY_DOGBOX_FALLBACK_NARROW_IMPLEMENTATION_R1
NEXT_GATE_EXECUTED=false
STOP=true
```
