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
 CURRENT_MAIN_ANCESTRY=c911e14f9fee1513667a559094732b9ab12ad117
 CORRECTION_CHAIN_MERGED=true
 TEMPORARY_INTEGRATION_COMPOSITION=false
 MAIN_ANCESTRY_ACCEPTANCE=true
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

## v0.6 thermal-closure authority

The selected U-tube and floating-head observations use the independently
reviewed and merged PR #271 authority path now present in main:

```ini
TASK160_V06_AUTHORITY=A06_V06_SHELL_TUBE_THERMAL_ENVELOPE
TASK161_V06_PROFILE=V1_V06_SHELL_TUBE
TASK162_V06_PROFILE=V1_V06_SHELL_TUBE
SUPPORTED_CONSTRUCTION_FAMILIES=FIXED_TUBESHEET|U_TUBE|FLOATING_HEAD
SHELL_PASS_COUNT=1
TUBE_PASS_COUNT=1
FORMULA_CHANGE=false
PHYSICS_CHANGE=false
TOLERANCE_CHANGE=false
LEGACY_V05_CONTRACT_CHANGED=false
```

The v0.6 profiles only requalify the existing stream-state, flow-arrangement,
and thermal-closure relations for the three construction families.  Geometry,
Bell applicability, and construction-specific mechanical semantics remain
owned by their upstream authorities.  PR #271 is included in the current main
ancestry; Golden approval remains an independent review decision.

 ## Proposed cases

 | Golden | Real replay evidence | Current disposition | Review requirement |
 | --- | --- | --- | --- |
 | V06-G01 | Fixed-tubesheet/E-shell request reaches a complete candidate and runs the real TASK-168 chain through TASK-169 selection. | Ready for independent review; current candidate status is WARN. | Approve the source/evidence binding and numeric/identity expectation. |
| V06-G02 | The selected deterministic proposal uses `U_TUBE`, the literal hash-verified `UTubePairingPlan`, shell catalog member `0.16 m`, and `baffle_cut_fraction=0.25`; the complete main-ancestry stack passes TASK-020 through TASK-169 and produces a real WARN/EVALUATED candidate. | Ready for independent review; TASK-160/161/162 use the versioned v0.6 1x1 thermal-closure profiles from merged PR #271. | Review the literal geometry proposal and the v0.6 thermal-closure authority; no runtime geometry search or pair inference is used. |
| V06-G03 | Floating-head is materialized by TASK-020; the complete main-ancestry stack passes TASK-020 through TASK-169 and produces a real WARN/EVALUATED candidate, including TASK-167 fouling, cleanability, and configuration screens. | Ready for independent review; TASK-160/161/162 use the versioned v0.6 1x1 thermal-closure profiles from merged PR #271. | Review the main-ancestry replay and the v0.6 thermal-closure authority before any Golden approval. |
 | V06-G04 | One real two-member TASK-168 request has a complete WARN candidate and a candidate rejected by an authoritative shell-DP hard constraint; TASK-169 selects the feasible candidate. | Ready for independent review. | Approve the DP-constrained input/constraint authority and expected identity. |
 | V06-G05 | A real Bell-side blocked candidate is replayed and selection produces no recommendation. | Ready for independent review as a negative Golden. | Approve the negative fail-closed source and expected no-recommendation semantics. |

G02 and G03 are complete engineering replays in the current main ancestry,
not approved Goldens.  G02 uses the literal pairing proposal and the selected
`0.16 m` shell geometry; the smaller shell candidates remain auditable
Stage-14 intersection failures.  G03 uses an independently materialized
`FLOATING_HEAD` candidate and does not reuse the G02 pairing plan.  Both
replays reach TASK-167 and TASK-169; their WARN status is caused by the
existing unbound generic FIV/erosion screening limits, not by a thermal
closure or family-applicability blocker.  Merged PR #271 supplies the
versioned TASK-160/161/162 v0.6 authority; Golden approval remains
independent and is not granted by this replay.

The companion JSON now records the `.16 m` G02 and current G03 replay
identities as observed proposal evidence.  `EXPECTED_IDENTITY_STATUS` remains
`PROPOSED_FOR_REVIEW`; no observed identity is promoted or self-approved.

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

## Final main-ancestry replay addendum

The correction chain is now merged into the verified main ancestry at
`c911e14f9fee1513667a559094732b9ab12ad117`.  The identities below are the
observations from that ancestry, not identities from the earlier temporary
composition.  They remain proposed expectations until an independent
reviewer approves the fixture authority.

| Golden | TASK-168 request hash | TASK-168 result hash / ID | TASK-169 result hash / ID | observed status |
| --- | --- | --- | --- | --- |
| V06-G01 | `b4e959204e09f784b9c698b97170357d68310218077c41dd6363390083a36ea2` | `48f74fa55a69033f7af13777f0098293f325138e2bc61d46cb50ce2557c16562` / `3455efc1-e4ad-5571-aab7-4612780b82b8` | `625b4fd3694504c3757e11758c7aaa6f4e4b6bdf6eb7143f9a4c19862b5f3717` / `7e736888-2736-5da8-8887-582daadb288e` | WARN / recommendable |
| V06-G02 | `f99f9d37b535201c2952b6652e6c84c912ac2d3ad9428362ffcb397d6fea80fb` | `5abf3df51b532d8ceb14cecfb5f30b1234dc79b2e4efed077255806ea3896cf0` / `05f20f03-a486-51cc-b47d-c61e6e3b02a9` | `1e1f3e9155e2cdf8fb7ebbc28a11afd199c54d43d4575f12ff19023b0fd68637` / `a2fd6ad6-08c2-5d8d-b9d7-6768483ed464` | WARN / recommendable |
| V06-G03 | `81dcec220d87ec412789fa83d5d1d6d56a5ff23cffaf7a0f7bb55d06ce31f210` | `3b763508f555bb5053a2050fc7477edd43ddf9553a6b3fd9381bb3390c229777` / `ee016f4d-542d-5e0b-a95c-e90fcad7497f` | `e79b4f254f03f53c51c06f557cb3e7558ae379c4e7b729fa31fa759a99db5a24` / `d6361e86-e089-5e75-8789-f5679d8b344f` | WARN / recommendable |
| V06-G04 | `ffb7dc72a82395a8493e636897a2a9430b9a4c9c78e79c84d0f5f6273a9fd6a9` | `c7cb67c9c6a7fc7af3f5ba1f30639d18e3b3c010f566756c97e306d3fcb93a87` / `0333664d-a67b-5aeb-b520-f77bb8fa7ebc` | `901dcb049c8a833d987ea1de03e2ad177ba7f9966d4fbe38b9ce0f60ad536d6a` / `55abcd89-fab4-5b29-88ea-60d0ef077b83` | WARN / recommendable; one hard-blocked alternative excluded |
| V06-G05 | `57e2b9e8a268b66c33027b9efdf16d4888a83beb89acbc15b5c20415ec3ca533` | `212fb93cdd05204c469259f79ba3862f37050b34bcd45bd90899e3bdd0bf3e16` / `290787cf-0051-59f7-95a1-3ebde75351e4` | `36fdc728a69770b17fbf9cfe680f407bf4b56426b551f595a21bd951e2898b05` / `e25e4be1-1b22-5596-a555-9f4ce8fcae6e` | BLOCKED / no recommendation |

The main-ancestry technical replay passed the non-Golden producer,
provenance, deterministic replay, ranking, and trusted dual-runtime gates.
The five Golden gates remain review-pending because the immutable approved
Golden registry is intentionally empty.  Therefore the release status remains
`BLOCKED` with reason `V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING`; this
proposal does not self-approve any fixture.
