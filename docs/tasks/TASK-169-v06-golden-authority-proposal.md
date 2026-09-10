# TASK-169 v0.6 Golden Authority Proposal

 ```ini
 TASK=HXFORGE_V0_6_TASK169_GOLDEN_AUTHORITY_PROPOSAL
 AUTHORITY_ISSUE=265
 TASK165_AUTHORITY_ISSUE=253
 TASK166_AUTHORITY_ISSUE=255
 TASK167_AUTHORITY_ISSUE=261
 TASK168_AUTHORITY_ISSUE=263
 STATUS=PROPOSED
 REVIEW_STATUS=PROPOSED
 EXPECTED_IDENTITY_STATUS=PROPOSED_FOR_REVIEW
 GOLDEN_SELF_APPROVAL=false
 ```

 This file is a review packet, not a release authority.  The companion
 JSON payload contains normalized inputs and observed replay identities so an
 independent reviewer can reproduce and approve (or reject) each fixture.
 No current run is promoted to an approved Golden by this change.

 ## Authority and evidence boundary

 Each case is bound to a typed `Task168Request`, its canonical request hash,
 the expected/proposed TASK-168 result identity, and the versioned TASK-169
 ranking policy.  The release service calls the public TASK-168 validator
 itself; a caller-supplied `Task168BatchResult` is not an execution input.
 The result and provenance identities are checked before selection.

 The current observations use the real producer-chain integration builder in
 `tests/exchangers/shell_tube/test_task168_manufacturable_candidates.py` and
 the production TASK-168 validator.  They are intentionally labelled
 proposal observations.  An observed hash is not an approved expected hash
 merely because it was produced by the current implementation.

 Protected source material is not redistributed in this repository.  The
 `source_location` fields identify the public/repository evidence location
 needed for independent review, and `provenance_source_hash` identifies the
 proposal evidence descriptor rather than claiming a protected source copy.

 ## Production ranking authority

 The proposal now binds the formal production ranking authority rather than a
 test policy:

 ```ini
 POLICY_ID=HXFORGE-V06-TASK169-RANKING-POLICY
 POLICY_VERSION=v1
 SOURCE_DEFINITION_ID=TASK169-PRODUCTION-RANKING-SOURCE-DEFINITION-V1
 SOURCE_ID=TASK169-PRODUCTION-RANKING-AUTHORITY-V1
 AUTHORITY_ORIGIN=TASK169_IMPLEMENTATION_AUTHORITY_ISSUE_265
 APPROVAL_STATUS=APPROVED_FOR_IMPLEMENTATION
 CANONICAL_HASH=142d58764a886a658bc24d1734b2be900843baa62c28dba849926b10a1f2fdc8
 ```

 `V06-RANKING-POLICY-TEST` / `TASK169-TEST-AUTHORITY` remains unit-test
 authority only and is rejected by the release boundary.  This policy
 establishment does not approve any Golden fixture.

 ## Proposed cases

 | Golden | Real replay evidence | Current disposition | Review requirement |
 | --- | --- | --- | --- |
 | V06-G01 | Fixed-tubesheet/E-shell request reaches a complete candidate and runs the real TASK-168 chain through TASK-169 selection. | Ready for independent review; current candidate status is WARN. | Approve the source/evidence binding and numeric/identity expectation. |
| V06-G02 | The selected deterministic proposal uses `U_TUBE`, the literal hash-verified `UTubePairingPlan`, shell catalog member `0.16 m`, and `baffle_cut_fraction=0.25`; TASK-021, TASK-022, TASK-024, TASK-031, TASK-034, and TASK-166 pass in the temporary correction composition. | The smaller shell members are rejected by the TASK-024 Stage-14 cut-boundary intersection rule; the selected candidate then reaches the source-bound TASK-160 fixed-tubesheet 1x1 envelope and is blocked with `B022`. | Review the literal geometry proposal and the independent TASK-160 applicability boundary; no runtime geometry search or pair inference is used. |
| V06-G03 | Floating-head is materialized by TASK-020; TASK-021, TASK-022, TASK-024, TASK-025, TASK-031, TASK-034, and TASK-166 pass in the temporary correction composition. | The candidate reaches the source-bound TASK-160 fixed-tubesheet 1x1 envelope and is blocked with `B022`; the TASK-166 construction-family correction is PR #270 and is not in the TASK-169 base ancestry. | Review the temporary composition and the independent TASK-160 applicability boundary before any Golden approval. |
 | V06-G04 | One real two-member TASK-168 request has a complete WARN candidate and a candidate rejected by an authoritative shell-DP hard constraint; TASK-169 selects the feasible candidate. | Ready for independent review. | Approve the DP-constrained input/constraint authority and expected identity. |
 | V06-G05 | A real Bell-side blocked candidate is replayed and selection produces no recommendation. | Ready for independent review as a negative Golden. | Approve the negative fail-closed source and expected no-recommendation semantics. |

G02 and G03 are not represented as successes.  G02 has a literal pairing
proposal and a deterministic `0.16 m` shell geometry proposal that passes the
reviewed TASK-024/TASK-031/TASK-034/Bell gates in temporary composition, but
the candidate is still blocked by the source-bound TASK-160 fixed-tubesheet
1x1 envelope.  The smaller shell candidates remain auditable Stage-14
intersection failures.  G03 passes the construction-family corrections in
temporary composition but reaches the same TASK-160 envelope blocker.  PR
#270 contains the independent TASK-166 applicability correction and is not
part of TASK-169 base ancestry until separately reviewed and merged.  G05
similarly proves only the negative path.

The companion JSON retains the earlier `.12 m` G02/G03 proposal observations
as historical, proposal-only evidence; the `.16 m` G02 search result is a
separately recorded candidate-space sweep in
`TASK-169-v06-full-chain-blocker-ledger.md`.  It is not silently substituted
into the frozen JSON Golden payload and is not approved by this change.

## G02 literal pairing proposal

The G02 pairing proposal is committed in
`src/hexagent/release_demo/task169_integration_release_acceptance/golden_fixtures.py`
as `G02_UTUBE_PAIRING_PLAN_RAW`.  It is project-defined proposal authority,
not an approved Golden:

```ini
PAIRING_AUTHORITY_ID=HXFORGE-V06-G02-UTUBE-PAIRING
PAIRING_AUTHORITY_VERSION=v1
SOURCE_CLASS=AUTHORIZED_PROJECT_DEFINED_PAIRING_PROPOSAL
SOURCE_ID=TASK169-G02-PAIRING-PROPOSAL
SOURCE_REVISION=v1
APPROVAL_STATUS=PROPOSED
EVIDENCE_REF=TASK169-V06-G02-PAIRING-REVIEW
SCHEMA_VERSION=task021.u-tube-pairing.v1
TASK021_ORIGIN_MODE=CENTER_ON_PRIMITIVE_CELL
PAIRING_PLAN_HASH=e7fe05b5ebd5e55107545f9a8f9b32908301d3bd12d4602b0ca0b3b8598eb4b0
PAIR_COUNT=5
ACCEPTED_LEG_COUNT=10
RUNTIME_PAIR_INFERENCE=false
PAIRING_HASH_REPLAY=PASS
PAIRING_COVERAGE=PASS
```

The pair list is literal and covers every accepted TASK-021 lattice leg once.
TASK-021 remains responsible for validating the plan; neither production
runtime nor Golden runtime derives pairs from accepted coordinates.

 ## Expected identity policy

 The JSON payload records the current replay identities in fields explicitly
 marked `observed_*`.  `expected_task169_result_hash` and
 `expected_task169_result_id` remain null because no reviewer-approved
 TASK-169 expected identity exists yet.  All records have:

 ```ini
 REVIEW_STATUS=PROPOSED
 EXPECTED_IDENTITY_STATUS=PROPOSED_FOR_REVIEW
 APPROVED_BY=
 APPROVAL_EVIDENCE=[]
 ```

 The production release validator has no mutable caller approval path and an
 empty immutable approved-Golden registry.  Consequently the release result
 remains `BLOCKED` with
 `V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING` until an independent authority
 registers approval.

 ## Frozen acceptance policy

 The proposal uses the TASK-165 tolerance class without accepting caller
 overrides:

 ```ini
 ENERGY_BALANCE_RELATIVE_ERROR_MAX=0.001
 THERMAL_DUTY_CLOSURE_RELATIVE_ERROR_MAX=0.001
 DIRECT_PUBLISHED_EQUATION_REPRODUCTION_RELATIVE_ERROR_MAX=0.005
 PUBLISHED_REFERENCE_SHELL_H_RELATIVE_ERROR_MAX=0.02
 PUBLISHED_REFERENCE_SHELL_DP_RELATIVE_ERROR_MAX=0.02
 MANUFACTURABLE_CATALOG_MEMBERSHIP=EXACT
 HARD_CONSTRAINT_STATUS=EXACT
 RANKING_ORDER=EXACT
 CANONICAL_IDENTITY_REPLAY=EXACT
 PY311_PY312_CANONICAL_PARITY=EXACT
 ```

 The full TASK-165 gate set remains mandatory.  A proposal packet cannot make
 `RELEASE_ACCEPTANCE=PASS`; the correct pre-approval state is:

 ```ini
 RELEASE_ACCEPTANCE=BLOCKED
 BLOCK_REASON=V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING
 READY_AUTHORIZED=false
 MERGE_AUTHORIZED=false
 ```
