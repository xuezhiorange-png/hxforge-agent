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
```

TASK-169 is the terminal v0.6 orchestration boundary.  It consumes the
authoritative TASK-168 batch and does not duplicate any geometry, tube-side,
Bell–Delaware, U/UA, thermal-closure, pressure-drop, or engineering-screening
physics.

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

TASK-169 first replays the TASK-168 batch hash/result ID and verifies its
provenance graph, applicability, completeness and PASS/WARN/BLOCKED counts.
Selection does not proceed on an unverifiable upstream batch.

## Ranking policy

Ranking authority is explicit and versioned.  There is no ambient or hidden
default.  A policy contains:

- policy ID/version/source and APPROVED status;
- deterministic Top-N;
- one or more metric objectives;
- direction per objective (MINIMIZE/MAXIMIZE);
- Decimal weight and Decimal scale per objective;
- explicit WARN penalty;
- evidence/provenance references;
- canonical policy hash.

Supported TASK-168 metrics in R1 are:

```text
modeled_ua_w_k
q_method_w
shell_dp_pa
tube_dp_pa
physical_tube_count
tube_hole_count
```

For each objective, TASK-169 computes a dimensionless contribution
`weight * metric / scale`; MAXIMIZE objectives negate that contribution.
The explicit WARN penalty is then added for WARN candidates. Lower total score
ranks first. Equal scores are broken by canonical candidate hash bytes, never
by input iteration order, clock, randomness, or process hash.

All arithmetic uses a fixed 50-digit Decimal context with HALF_EVEN rounding.

## Output and traceability

The successful selection result exposes:

- source TASK-168 result hash and ID;
- source TASK-168 provenance hash;
- ranking-policy hash;
- full ranked recommendable set;
- one recommended candidate;
- deterministic Top-N alternatives;
- every excluded candidate with reason;
- per-candidate objective values and composite score;
- deterministic result hash and UUIDv5 identity.

TASK-169 does not silently repair geometry or rerun a producer equation.

## Golden and release-acceptance continuation

The same TASK-169 primary PR owns the remaining frozen TASK-165 terminal
acceptance work.  It must not be split into new formula-sized tasks.

The frozen Golden classes remain:

- `V06-G01` — fixed-tubesheet E-shell single-phase success;
- `V06-G02` — U-tube success exercising thermal-expansion/configuration screening;
- `V06-G03` — floating-head success exercising fouling/cleanability/configuration screening;
- `V06-G04` — DP-constrained multi-candidate case with deterministic feasible selection;
- `V06-G05` — negative fail-closed case with no recommendation.

The TASK-165 tolerance table is unchanged.  Golden fixture payloads, dual
Python 3.11/3.12 parity evidence and the final end-to-end v0.6 release
acceptance ledger are subsequent commits on this same TASK-169 branch/PR.

```text
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
V0_7_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```
