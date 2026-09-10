# TASK-169 — Selection, Integration, Golden Validation and v0.6 Release Acceptance

## Contract identity

```ini
TASK_ID=HXFORGE_V0_6_TASK169_SELECTION_INTEGRATION_GOLDEN_RELEASE_ACCEPTANCE
AUTHORITY_ISSUE=265
BASE_MAIN_SHA=2e0f8642cbbacff67cdf97f0541d21360ce379f7
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

TASK-165 freezes Golden class purpose, not final fixture approval.  This PR
adds the versioned proposal payload at
`docs/tasks/TASK-169-v06-golden-authority-proposal.json` and its review
explanation at `docs/tasks/TASK-169-v06-golden-authority-proposal.md`.

All five cases are represented and replayed through real TASK-168 requests:

- `V06-G01` uses the real fixed-tubesheet/E-shell chain and reaches a real
  complete WARN candidate in the current producer chain.  Its expected
  TASK-168 identity is recorded as a proposal binding.
- `V06-G02` uses a real candidate-specific U-tube request with the literal,
  hash-verified pairing proposal in the release fixture.  The deterministic
  `0.16 m` shell proposal passes TASK-021, TASK-022, TASK-024, TASK-031,
  TASK-034, and TASK-166 in temporary composition; the candidate then blocks
  at the source-bound TASK-160 fixed-tubesheet 1x1 envelope.  Smaller shell
  members remain auditable TASK-024 Stage-14 intersection failures.
  `V06-G03` uses the real floating-head materialization attempt and passes the
  TASK-024/TASK-025/TASK-031 family corrections in temporary composition, but
  also blocks at TASK-160.  Neither case is claimed as a success.
- `V06-G04` uses a real two-member TASK-168 space.  One candidate is complete
  and recommendable and one is rejected by the authoritative shell-DP
  constraint; the selection output records the alternative and exclusion
  trace.
- `V06-G05` uses a real Bell-side blocked candidate and produces no
  recommendation.

The payload records source ID/location/class, redistribution status,
normalized input hash, TASK-168 request/result identities, proposed TASK-169
observation identities, frozen tolerance class, provenance source hash, and
review metadata.  It is metadata-only: protected source material is not
copied.  `REVIEW_STATUS=PROPOSED`,
`EXPECTED_IDENTITY_STATUS=PROPOSED_FOR_REVIEW`, and empty approval fields are
required.  No current run is promoted to an approved Golden authority.

The implementation has an empty immutable approved-Golden registry.  Even a
caller changing a proposal record to `APPROVED` cannot pass release acceptance
without an independently registered authority and approval evidence.

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
Golden gate or provide reviewer approval.  With the proposal metadata still
pending independent review, the correct current result is:

```ini
TASK168_AUTHORITATIVE_REQUEST_BOUND=true
TASK168_REAL_REPLAY=PASS
TRUSTED_PARITY=CI_PROVISIONED_RUNTIME_OBSERVATION
RELEASE_ACCEPTANCE=BLOCKED
BLOCK_REASON=V06_GOLDEN_FIXTURE_REVIEW_APPROVAL_PENDING
```

```ini
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
V0_7_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```
