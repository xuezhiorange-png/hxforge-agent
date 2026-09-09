# TASK-168 — Manufacturable Discrete Candidate Generation and Sizing

## Contract identity

```ini
TASK_ID=HXFORGE_V0_6_TASK168_MANUFACTURABLE_CANDIDATE_GENERATION_AND_SIZING
SOURCE_AUTHORITY=TASK168_AUTHORITY_ISSUE_263
TASK165_AUTHORITY=TASK165_AUTHORITY_ISSUE_253
TASK166_AUTHORITY=TASK166_AUTHORITY_ISSUE_255
TASK167_AUTHORITY=TASK167_AUTHORITY_ISSUE_261
TASK168_VERSION=task168.v1
TASK168_SOURCE_DEFINITION_ID=TASK168-SOURCE-DEFINITION-ISSUE-263
```

TASK-168 is the v0.6 manufacturable discrete candidate-generation and sizing
boundary.  It is an orchestration and authority-composition task.  It does
not replace the physics owned by TASK-021/022/024/026/029/037/038/162/166/167.

## Scope and non-scope

The accepted candidate families are `FIXED_TUBESHEET`, `U_TUBE`, and
`FLOATING_HEAD`, subject to the caller's source-bound requirement authority.
The selectable dimensions are discrete members of an approved catalog, an
approved rule-pack snapshot, a source-bound discrete snapshot, or an
explicitly authorized project-defined discrete set.  An optimizer may not
invent a continuous dimension, perturb a dimension after rating, or snap a
calculated dimension to a catalog record.

TASK-168 does not perform candidate ranking, scoring, optimization, winner or
Top-N selection, release acceptance, Golden integration, or TASK-169 work.  It
does not implement tube-side correlations, Bell–Delaware correlations,
overall-U/UA equations, thermal closure, pressure-drop equations, or
engineering-screening rules.  Those are consumed as producer-owned typed
results.  It does not implement `LMTD` or an `F` correction factor.

## Request boundary

The typed request has exactly these nine fields, in this order:

1. `schema_version`
2. `task168_version`
3. `source_definition_id`
4. `task020_configuration`
5. `requirement_authority`
6. `shell_geometry_catalog`
7. `discrete_candidate_set_authorities`
8. `evaluation_input_authority`
9. `request_metadata`

`task020_configuration` is the exact TASK-020 normalized configuration.
`shell_geometry_catalog` is the exact approved TASK-023 catalog.  The
`evaluation_input_authority` is an identity-bearing bundle of producer request
templates and base property/service authorities.  TASK-168 fills the selected
candidate dimensions into those templates, invokes TASK-021/022/024,
tube-side, TASK-166, TASK-037/038, TASK-162, tube-side pressure-drop
composition, and TASK-167, and records the producer-owned identities returned
by that live chain.  It may carry explicit TASK-160 and TASK-161 request
templates; TASK-168 binds the live TASK-026 result into TASK-160 and then
binds the newly issued TASK-160 result into TASK-161.  The caller does not
provide candidate-specific results, callbacks, or replacement UA, duty,
outlet-temperature, pressure-drop, or arbitrary geometry scalars.

`Task168RequirementAuthority` identities every hard constraint.  Required
duty, maximum tube-side DP, and maximum shell-side DP are optional only when
their source-bound authority is present; a bare caller number is invalid.

## Discrete authority and catalog binding

Every dimension authority has an identity, revision, source class, source ID,
approval status, evidence references, provenance references, a value sequence,
and a replayable canonical hash.  Required roles are:

```text
CONSTRUCTION_FAMILY
TUBE_OUTER_DIAMETER
TUBE_WALL_THICKNESS
TUBE_LENGTH
TUBE_PITCH
TUBE_LAYOUT
TUBE_PASS_COUNT
BAFFLE_TYPE
BAFFLE_CUT
BAFFLE_SPACING
BAFFLE_COUNT
```

An authority must be approved, evidenced, hash-replayable, non-empty, and
free of duplicate semantic members.  Decimal equality is semantic equality:
`Decimal("0.025")` and `Decimal("0.0250")` are not two candidate members.
Numeric values are ordered numerically; text and enum values are ordered by
UTF-8 bytes.  The resource limits are 32 values per role, 4,096 theoretical
Cartesian combinations, and 4,096 materialized candidates.  Exceeding a
limit blocks the request and never truncates it.

The TASK-023 shell catalog is enumerated first.  A shell diameter is valid
only as the exact `ShellGeometryRecord` selected from that catalog, retaining
catalog ID/version/hash, geometry ID, and record hash.  Bundle-fit failure is
an auditable blocked candidate; it is not repaired by choosing a nearby shell.

## Generation and deterministic identity

The canonical dimension order is:

```text
CONSTRUCTION_FAMILY
SHELL_GEOMETRY_ID
TUBE_OUTER_DIAMETER
TUBE_WALL_THICKNESS
TUBE_LENGTH
TUBE_PITCH
TUBE_LAYOUT
TUBE_PASS_COUNT
BAFFLE_TYPE
BAFFLE_CUT
BAFFLE_SPACING
BAFFLE_COUNT
```

The Cartesian product is generated in that order.  Mapping insertion order,
set iteration, filesystem order, process hash, clock, randomness, and thread
completion order are not identity inputs.  Candidate identity includes every
selected dimension plus every authority identity and the TASK-020 case
authority.  The candidate-space identity includes the requirement authority,
TASK-023 catalog identity, and every discrete-set authority hash.

No quality-based pruning is allowed.  Each enumerated candidate is retained
as either `EVALUATED` or `BLOCKED`.  A blocked candidate records its candidate
identity, stage, dimensions, authority evidence, and blocker.  No downstream
result is populated after an upstream stage fails.

## Exact evaluation state machine

The candidate stages are frozen as:

```text
CANDIDATE_AUTHORITY
CONFIGURATION
TUBE_LAYOUT
SHELL_BUNDLE_GEOMETRY
BAFFLE_GEOMETRY
TUBE_SIDE
SHELL_SIDE_BELL
OVERALL_RESISTANCE
UA
THERMAL_CLOSURE
TUBE_DP
SHELL_DP
ENGINEERING_SCREENING
CONSTRAINT_EVALUATION
COMPLETE
```

The producer-owned chain is consumed in this order:

```text
Candidate
 -> TASK-021 tube layout / exact physical tube count
 -> TASK-022 shell-bundle geometry
 -> TASK-024 baffle geometry
 -> tube-side thermal and hydraulic results
 -> TASK-166 Bell–Delaware result
 -> TASK-037 / TASK-038 overall resistance and U/UA
 -> TASK-162 thermal closure
 -> tube-side DP and shell-side DP
 -> TASK-167 preliminary screening
 -> exact hard-constraint evaluation
 -> PASS / WARN / BLOCKED
```

For each generated candidate, TASK-168 materializes the actual producer
request from candidate dimensions plus the evaluation-input authority and
invokes the existing producer boundary before constructing the next request.
TASK-029 receives a composition authority rebuilt from the live TASK-027 and
TASK-028 results.  TASK-168 replays producer identities and same-case joins;
it does not rerun a producer's engineering equations.  A missing or blocked
producer result is a candidate blocker, never a Kern fallback or a synthetic
success.

## Tube count and psi_n

TASK-168 prefers exact TASK-021 layout enumeration.  When the accepted layout
contains `physical_tube_count`, `tube_hole_count`, and its exclusion audit,
`TUBE_COUNT_SOURCE=TASK021_EXACT_LAYOUT_ENUMERATION` and `PSI_N_USED=false`;
the inaccessible Wiley `psi_n` table is not a TASK-168 prerequisite.
`psi_n` remains deferred to TASK-168 only if a future sizing path genuinely
needs the published tube-count estimate and its source is complete.  TASK-168
does not guess `psi_n`.

## Status semantics

Candidate status is exactly `PASS`, `WARN`, or `BLOCKED`:

* `PASS` means producer replay, case binding, hard constraints, and screening
  completed without warning.
* `WARN` means the candidate is evaluable and no hard constraint failed, but
  TASK-167 returned a warning-level screen.
* `BLOCKED` means a required authority, identity, geometry, producer stage,
  or hard constraint failed.

The batch retains all candidate records and reports exact PASS/WARN/BLOCKED
counts.  It contains no ranking field, score, recommendation, winner, or
Top-N operation.  Enumeration order is not an engineering ranking.

## Canonical identity and provenance

TASK-168 uses the existing TASK-021 canonical JSON/hash framework.  Decimal
values are serialized as exact Decimal text; binary floats, random values,
clock values, unordered mappings, and process-local hashes are forbidden.
The success preimage includes request identity, candidate-space identity,
ordered candidate records, status counts, applicability, completeness, and
semantic provenance inputs.  It excludes the final provenance graph, result
hash, and result ID, so no result/provenance cycle can occur.

The final graph contains source, requirement, TASK-023 catalog,
candidate-space, candidate, producer-evidence, calculation-run, and result
nodes.  Edges point toward the calculation run and then to the result.  The
graph is sorted, replayable, self-edge-free, and acyclic.

## Raw boundary and failures

Raw admission is bounded at depth 16, 512 nodes, and 16,384 scalar UTF-8
bytes.  Only safe built-in containers/scalars and trusted `hexagent` typed
dataclasses/enums are admitted.  `repr`, arbitrary `str`, `id`, `hash`, memory
addresses, user-code hooks, and arbitrary object state are not used.  Raw
failure returns the raw-boundary blocked branch; typed parsing is not used as
a fallback after raw failure.  Typed failures use a deterministic identity
and never create a provenance graph.

## Validation and test contract

The implementation tests cover authority hash replay, approved catalog
membership, duplicate semantics, deterministic Cartesian order, resource
limits, structural geometry blockers, no silent repair, exact TASK-021 tube
count, live TASK-021/022/024 and producer orchestration, TASK-029
candidate-specific path binding, producer replay/case joins,
blocked-candidate retention, PASS/WARN/BLOCKED aggregation, hard-constraint
equality and over-limit behavior, canonical replay under ambient Decimal-
context changes, raw totality, and provenance cycle count zero.  The real
full-chain fixture reaches an evaluated WARN candidate; a separate structural
candidate is retained as BLOCKED.  Regression tests prove TASK-033/TASK-034,
TASK-162, TASK-166, and TASK-167 semantics are consumed rather than modified.

Python 3.11 and 3.12 are the supported identity-parity runtimes.  TASK-169
owns ranking, recommendation, Golden integration, and release acceptance;
TASK-168 stops before those capabilities.

## R3 authority-preserving materialization correction

TASK-168 retains the exact native TASK-021 `TubeLayout` and TASK-022
`ShellBundleGeometry` success objects throughout the live chain.  It does
not discard warnings, reconstruct a replacement `layout_id`/`layout_hash` or
`geometry_id`/`geometry_hash`, or store a TASK-024-specific substitute as the
authoritative upstream result.  TASK-024 admission may use a private
representation adapter only to project the native frozen warning/provenance
fragments into the already-authorized TASK-024 replay shape; the native IDs,
hashes, warning semantics, and provenance semantics remain unchanged.

Every selected member of `CONSTRUCTION_FAMILY`, `TUBE_OUTER_DIAMETER`,
`TUBE_WALL_THICKNESS`, `TUBE_LENGTH`, `TUBE_PITCH`, `TUBE_LAYOUT`,
`TUBE_PASS_COUNT`, `BAFFLE_TYPE`, `BAFFLE_CUT`, `BAFFLE_SPACING`, and
`BAFFLE_COUNT` is carried by a complete `CandidateDimensionAuthorityBinding`:
authority ID/version, canonical hash, source class/ID/revision, evidence
references, provenance references, and the selected canonical member.  The
binding is part of candidate identity and is exposed through deterministic
`TASK168_DISCRETE_AUTHORITY::<role>::<canonical_hash>` evidence bridges in
candidate-specific TASK-021/TASK-022/TASK-024 request materialization.

The TASK-021 tube geometry snapshot is itself rebuilt as a candidate-specific
derived authority from the structural template, selected OD/wall bindings,
and their exact values.  Its geometry ID, source binding, record hash, and
snapshot hash are recomputed together; the structural template's source
record identity is never retained for a different tube dimension.  TASK-021
layout-rule provenance and TASK-024 axial/design authority evidence carry the
corresponding pitch/layout/pass, length/spacing/count, and baffle-type/cut
selection bridges.  These changes are identity/provenance materialization
only; upstream geometry equations, authority rules, and result replay
contracts are unchanged.

Request templates authorize structure only.  Candidate values are rebound
from the selected discrete authorities before each producer request is
validated; stale template evidence cannot claim ownership of a changed
candidate dimension.  The final provenance graph contains explicit
discrete-authority, candidate-specific materialization, native-producer, and
candidate-record edges, with no source discontinuity or provenance cycle.
