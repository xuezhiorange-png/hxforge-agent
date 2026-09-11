# TASK-169 — Selection, Integration, Golden Validation and v0.6 Release Acceptance

## Contract identity

```ini
TASK_ID=HXFORGE_V0_6_TASK169_SELECTION_INTEGRATION_GOLDEN_RELEASE_ACCEPTANCE
AUTHORITY_ISSUE=265
BASE_MAIN_SHA=2e0f8642cbbacff67cdf97f0541d21360ce379f7
CURRENT_MAIN_ANCESTRY=c911e14f9fee1513667a559094732b9ab12ad117
CORRECTION_CHAIN_MERGED=true
MAIN_ANCESTRY_ACCEPTANCE=true
TASK165_AUTHORITY_ISSUE=253
TASK166_AUTHORITY_ISSUE=255
TASK167_AUTHORITY_ISSUE=261
TASK168_AUTHORITY_ISSUE=263
TASK169_VERSION=task169.v1
TASK169_SOURCE_DEFINITION_ID=TASK169-SOURCE-DEFINITION-ISSUE-265
TASK169_RELEASE_VERSION=task169.release.v2
TASK169_RELEASE_SCHEMA_VERSION=task169.release-acceptance-request.v2
```

TASK-169 is the terminal v0.6 orchestration boundary.  It consumes
authoritative TASK-168 requests and results, does not duplicate any
geometry, tube-side, Bell–Delaware, U/UA, thermal-closure, pressure-drop, or
engineering-screening physics, and does not start TASK-170 or a later scope.

## Selection boundary

A TASK-168 candidate is recommendable only when all of these are true:

```text
disposition=EVALUATED
status in {PASS, WARN}
stage=COMPLETE
blockers=()
```

Every other candidate is retained as an auditable exclusion.  A hard-blocked
candidate can never be selected merely because its numerical score would be
favorable.

Selection first verifies the TASK-168 result schema/version/source and
replays the result hash, result ID, applicability, completeness, provenance
graph, and PASS/WARN/BLOCKED counts.  It then applies one explicit ranking
policy.  Decimal arithmetic uses a fixed 50-digit HALF_EVEN context; equal
scores use canonical candidate-hash bytes as the tie-break.

The selection result includes the full ranking trace: objective values,
composite score, WARN penalty contribution, rank reason codes, recommendation
reason codes, alternative-candidate reason codes, and exclusion/blocker
reason codes.  These fields are part of the canonical result preimage.

## Release input and real TASK-168 replay

The release boundary is deliberately request-based.  Each
`Task169GoldenCase` carries:

- an authoritative typed `Task168Request`;
- the canonical TASK-168 request hash;
- expected TASK-168 result hash, result ID, and branch status;
- a versioned ranking-policy identity;
- Golden source, provenance, redistribution, and review metadata.

There is no caller-supplied `Task168BatchResult` field and no caller-supplied
runtime-parity evidence field.  The release validator invokes the delivered
TASK-168 public `validate_request` entry point for every case, validates the
native valid/typed-blocked/raw-boundary-blocked identity, and only then runs
TASK-169 selection for a valid batch.  A request, result, ID, provenance,
source/version, or replay mismatch fails closed.

The release result records the observed TASK-168 and TASK-169 identities for
each case.  A blocked TASK-168 case is never converted into a successful
selection result; it may be used by the negative Golden only to prove
no-recommendation behavior.

## Ranking authority

Ranking authority is explicit, versioned, and source-bound.  The release path
accepts only this formal production identity:

```ini
POLICY_ID=HXFORGE-V06-TASK169-RANKING-POLICY
POLICY_VERSION=v1
SOURCE_DEFINITION_ID=TASK169-PRODUCTION-RANKING-SOURCE-DEFINITION-V1
SOURCE_ID=TASK169-PRODUCTION-RANKING-AUTHORITY-V1
AUTHORITY_ORIGIN=TASK169_IMPLEMENTATION_AUTHORITY_ISSUE_265
APPROVAL_STATUS=APPROVED_FOR_IMPLEMENTATION
TOP_N=3
WARN_PENALTY=10
OBJECTIVE_01_METRIC=shell_dp_pa
OBJECTIVE_01_DIRECTION=MINIMIZE
OBJECTIVE_01_WEIGHT=1
OBJECTIVE_01_SCALE=100
TIE_BREAK_RULE=CANDIDATE_HASH_ASC_UTF8
CANONICAL_HASH=142d58764a886a658bc24d1734b2be900843baa62c28dba849926b10a1f2fdc8
```

The policy is an engineering implementation authority, not Golden fixture
approval.  Its evidence and provenance references bind TASK-165 ranking
semantics to the TASK-169 implementation authority.  The unit-test identity
`V06-RANKING-POLICY-TEST` / `TASK169-TEST-AUTHORITY` is deliberately separate
and is rejected by the release validator.  A caller cannot replace the
production policy with a test policy or a policy whose canonical hash does not
replay.

Supported TASK-168 metrics are:

```text
modeled_ua_w_k
q_method_w
shell_dp_pa
tube_dp_pa
physical_tube_count
tube_hole_count
```

Presentation text, input order, clock, random state, unordered iteration, or
process-local hashing cannot affect ranking.  WARN remains WARN and any WARN
penalty is explicit in the policy and trace.  TASK-169 performs no score,
ranking, recommendation, or Top-N operation for a BLOCKED candidate.

## Trusted Python 3.11/3.12 parity

Parity is an internal observation, not a caller assertion.  The release
validator builds one canonical parity input from the replayed request/result
surfaces, then the trusted runner invokes the actual provisioned Python 3.11
and Python 3.12 executables with isolated environment settings.  Each child
verifies:

- its assigned interpreter major/minor and executable identity;
- the current checkout HEAD and tree;
- the exact framed canonical input bytes;
- TASK-169 result hashes and IDs;
- the internal runner and command identities.

Missing, duplicate, swapped, stale, wrong-version, failed, or mismatching
runtime observations are `BLOCKED`.  The caller cannot turn a pair of hash
tuples into parity evidence.  CI provisioning supplies the two isolated
executables through the existing TASK-164 runtime pattern.

## Frozen tolerance authority

The release request must carry this exact immutable ledger; caller overrides
are rejected before replay:

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

## Golden Authority Proposal boundary

TASK-165 freezes Golden class purpose.  This PR adds the versioned authority
payload at
`docs/tasks/TASK-169-v06-golden-authority-proposal.json` and its review
explanation at `docs/tasks/TASK-169-v06-golden-authority-proposal.md`, together
with the immutable production registry at
`src/hexagent/release_demo/task169_integration_release_acceptance/approved_golden_registry.py`.

All five cases are represented and replayed through real TASK-168 requests:

- `V06-G01` uses the real fixed-tubesheet/E-shell chain and reaches a real
  complete WARN candidate in the current producer chain.  Its expected
  TASK-168 and TASK-169 identities are bound to the independent review record.
- `V06-G02` uses a real candidate-specific U-tube request with the literal,
  hash-verified pairing proposal in the release fixture.  The deterministic
  `0.16 m` shell proposal passes the complete TASK-020 through TASK-169
  current main-ancestry replay after the merged versioned TASK-160/161/162
  v0.6 authority correction.  It reaches TASK-167 as WARN/EVALUATED and is
  recommendable under the production ranking policy.  Smaller shell members
  remain auditable TASK-024 Stage-14 intersection failures.
- `V06-G03` uses the real floating-head materialization attempt and passes the
  complete TASK-020 through TASK-169 main-ancestry replay, including real
  TASK-167 fouling, cleanability, and configuration screens.  It reaches
  TASK-167 as WARN/EVALUATED and is recommendable.  The v0.6 thermal-closure
  authority is supplied by merged PR #271; the Golden approval is represented
  only by the independent-review registry.
- `V06-G04` uses a real two-member TASK-168 space.  One candidate is complete
  and recommendable and one is rejected by the authoritative shell-DP
  constraint; the selection output records the alternative and exclusion
  trace.
- `V06-G05` uses a real Bell-side blocked candidate caused by the missing
  mandatory TASK-166 request authority and produces no recommendation.

The payload records source ID/location/class, redistribution status,
normalized input hash, TASK-168 request/result identities, reviewed TASK-169
expected identities, frozen tolerance class, provenance source hash, and
review metadata.  It is metadata-only: protected source material is not
copied.  The JSON record and immutable registry retain the explicit
independent-review evidence; no caller-supplied approval fields can register a
new Golden.

The implementation has an immutable approved-Golden registry containing all
five reviewed identities.  A caller changing a proposal record to `APPROVED`
or changing any expected identity cannot pass release acceptance unless it
matches that registry exactly.

## Release gate semantics

The complete TASK-165 gate set remains mandatory:

```text
SHELL_TUBE_FIXED_GEOMETRY_RATING
BELL_DELAWARE_HEAT_TRANSFER
BELL_DELAWARE_PRESSURE_DROP
BELL_DELAWARE_PROVENANCE_COMPLETE
SHELL_TUBE_ENGINEERING_SCREENING
THERMAL_EXPANSION_SCREENING
VIBRATION_SCREENING
SHELL_TUBE_CANDIDATE_GENERATION
SHELL_TUBE_SIZING
SHELL_TUBE_MULTI_CANDIDATE_RANKING
TUBE_DP_CONSTRAINT_CLOSURE
SHELL_DP_CONSTRAINT_CLOSURE
THERMAL_DUTY_CLOSURE
DETERMINISTIC_REPLAY
PROVENANCE_COMPLETE
PY311_PY312_PARITY
GOLDEN_V06_G01
GOLDEN_V06_G02
GOLDEN_V06_G03
GOLDEN_V06_G04
GOLDEN_V06_G05
END_TO_END_RELEASE_DEMO
```

Synthetic/unit fixtures remain contract tests only.  They cannot satisfy a
Golden gate or provide reviewer approval.  The approved registry still does
not bypass exact replay or trusted runtime evidence.  The pre-closeout local
observation with four blocked gates was superseded by the final 22-gate
closeout recorded in `docs/tasks/TASK-169-v06-release-acceptance-final.md`.

```ini
TASK168_AUTHORITATIVE_REQUEST_BOUND=true
TASK168_REAL_REPLAY=PASS
TRUSTED_PARITY=CI_PROVISIONED_RUNTIME_OBSERVATION
RELEASE_ACCEPTANCE=PASS
RELEASE_GATE_PASS_COUNT=22
RELEASE_GATE_FAIL_COUNT=0
RELEASE_GATE_REVIEW_PENDING_COUNT=0
```

```ini
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
V0_7_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## Final main-ancestry acceptance addendum

The merged correction chain is now part of main at
`c911e14f9fee1513667a559094732b9ab12ad117`.  The following identities are
from the main-ancestry replay, not from the earlier temporary composition.

| Golden | TASK-168 result | TASK-169 result | technical disposition |
| --- | --- | --- | --- |
| V06-G01 | `48f74fa55a69033f7af13777f0098293f325138e2bc61d46cb50ce2557c16562` / `3455efc1-e4ad-5571-aab7-4612780b82b8` | `625b4fd3694504c3757e11758c7aaa6f4e4b6bdf6eb7143f9a4c19862b5f3717` / `7e736888-2736-5da8-8887-582daadb288e` | WARN, recommendable |
| V06-G02 | `5abf3df51b532d8ceb14cecfb5f30b1234dc79b2e4efed077255806ea3896cf0` / `05f20f03-a486-51cc-b47d-c61e6e3b02a9` | `1e1f3e9155e2cdf8fb7ebbc28a11afd199c54d43d4575f12ff19023b0fd68637` / `a2fd6ad6-08c2-5d8d-b9d7-6768483ed464` | WARN, recommendable |
| V06-G03 | `3b763508f555bb5053a2050fc7477edd43ddf9553a6b3fd9381bb3390c229777` / `ee016f4d-542d-5e0b-a95c-e90fcad7497f` | `e79b4f254f03f53c51c06f557cb3e7558ae379c4e7b729fa31fa759a99db5a24` / `d6361e86-e089-5e75-8789-f5679d8b344f` | WARN, recommendable |
| V06-G04 | `c7cb67c9c6a7fc7af3f5ba1f30639d18e3b3c010f566756c97e306d3fcb93a87` / `0333664d-a67b-5aeb-b520-f77bb8fa7ebc` | `901dcb049c8a833d987ea1de03e2ad177ba7f9966d4fbe38b9ce0f60ad536d6a` / `55abcd89-fab4-5b29-88ea-60d0ef077b83` | WARN, recommendable; hard-blocked alternative excluded |
| V06-G05 | `a0521d00137833f0bd3763c440e0684fa993ba36917b824951a43a234ef3a17e` / `1cf76875-a201-5a14-a9c7-960912156a1d` | `b2f86665b182deab959af4eb1e0617a7939341d67b5eb81c2b94aa9a0a66c197` / `4019e286-8f41-5d94-a996-f825aa39094b` | BLOCKED, no recommendation; frozen missing TASK-166 authority |

The final 22-gate closeout is satisfied by the real replay, including trusted
Python 3.11/3.12 parity and deterministic identity reconciliation.  The five
Golden identities are bound to the independent review decisions in the
approved registry.  This is an authority binding, not a self-approval, and it
does not alter Ready/Merge authorization.  The DP gates use native TASK-168
DP evidence plus the approved G04 shell-DP hard-constraint rejection; the
thermal-duty gate uses native TASK-162 thermal-closure evidence.

```ini
CURRENT_MAIN_ANCESTRY=c911e14f9fee1513667a559094732b9ab12ad117
CORRECTION_CHAIN_MERGED=true
TEMPORARY_INTEGRATION_COMPOSITION=false
RELEASE_GATE_TECHNICAL_PASS_COUNT=17
RELEASE_GATE_GOLDEN_REVIEW_PENDING_COUNT=0
RELEASE_GATE_TECHNICAL_FAILURE_COUNT=0
TRUSTED_PY311_RUNTIME=PASS
TRUSTED_PY312_RUNTIME=PASS
PY311_PY312_PARITY=PASS
GOLDEN_SELF_APPROVAL=false
RELEASE_ACCEPTANCE=PASS
BLOCK_REASON=NONE
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```
