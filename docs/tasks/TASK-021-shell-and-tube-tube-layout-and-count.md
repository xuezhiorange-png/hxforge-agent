# TASK-021 — Shell-and-Tube Tube Layout and Tube Count Foundation

> Binding design contract for the second M3 shell-and-tube capability.
> TASK-021 consumes one valid TASK-020 configuration and produces one
> deterministic, authority-bound two-dimensional tube layout and tube count.

## 1. Authority and status

| Field | Value |
|---|---|
| Authorizing Issue | #137 |
| Allocation authorization | Issue #137 comment `4953356685` |
| One-file authoring authorization | Issue #137 comment `4953386614` |
| First review | PR #138 comment `4953451291` |
| Corrective re-review | PR #138 comment `4953517481` |
| Round-2 authorization | `AUTHORIZE_TASK021_DESIGN_CORRECTIVE_ROUND_2_PROVENANCE_BLOCKERS_PAIRING_METADATA` |
| Frozen allocation | `TASK-021 = Shell-and-Tube Tube Layout and Tube Count Foundation` |
| Design branch | `docs/task-021-tube-layout-count-design` |
| Design file | `docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md` |
| Authoring base | `9fd0969b8b512c6b631d122f60057df3062fc416` |
| Implementation | NOT AUTHORIZED |
| Ready | NOT AUTHORIZED |
| Merge | NOT AUTHORIZED |
| TASK-022 through TASK-039 | UNALLOCATED |

Shell diameter remains deferred and unallocated.

## 2. Exact scope

TASK-021 owns:

1. complete TASK-020 configuration consumption and identity verification;
2. approved tube-geometry and layout-rule snapshots;
3. deterministic square and triangular lattice enumeration;
4. one caller-supplied circular tube-center placement envelope;
5. explicit circular and axis-aligned rectangular exclusion zones;
6. tube-hole count and physical-tube count;
7. fixed-tubesheet, floating-head, and U-tube count semantics;
8. canonical serialization, hashing, UUIDv5 identity, warnings, blockers,
   provenance, and audit summaries.

TASK-021 does not calculate or infer:

- shell, bundle, or baffle diameter;
- shell-to-bundle clearance;
- pass membership, partition plates, nozzles, or flow paths;
- baffles, rating, Kern, Bell–Delaware, pressure drop, or thermal expansion;
- mechanical adequacy, materials, mass, cost, optimization, API, report, or
  engineering Golden values.

`tube_center_envelope_diameter_m` is a caller-supplied placement constraint. It
is not a shell, bundle, or baffle diameter result.

## 3. Source-of-truth and fail-closed boundary

Binding authority:

- TASK-020 design and implementation;
- TASK-012 source, approval, provenance, and license governance;
- TASK-016 design as a tube-record shape and governance reference only;
- `docs/MASTER_DEVELOPMENT_SPEC.md`;
- Issue #137 and PR #138 review history.

The deterministic core performs no filesystem scan, catalog lookup, database
query, network call, or hidden default substitution. Missing authority blocks.

TASK-019 Amendment 002-K remains separate M2 authority and is not imported.

## 4. Frozen design decisions

### 4.1 TASK-020 input

The request carries the complete valid TASK-020 `ShellAndTubeConfiguration`.
The core verifies:

- `equipment_family == SHELL_AND_TUBE`;
- no TASK-020 blockers;
- the complete canonical payload reproduces `configuration_hash`;
- the TASK-020 UUID helper reproduces `configuration_id`.

An ID, hash, or partial projection alone is insufficient.

### 4.2 Geometry and layout authority

The request carries:

- one `ApprovedTubeGeometrySnapshot`;
- one `LayoutRuleAuthoritySnapshot` with profile
  `hxforge.shell_tube.tube_layout.v1`.

A TASK-020 configuration rule is not implicitly a TASK-021 layout rule.

### 4.3 Closed pattern set

- `SQUARE`;
- `TRIANGULAR`.

These are generic mathematical lattices and make no standards or certification
claim. Rotated, radial, concentric-ring, custom, and vendor-proprietary patterns
are deferred.

### 4.4 Pass and construction semantics

TASK-021 does not assign tubes to passes. Explicit pass lanes may be represented
only as caller-supplied exclusion zones.

- `FIXED_TUBESHEET`: physical tube count equals accepted tube-hole count.
- `FLOATING_HEAD`: physical tube count equals accepted tube-hole count; no
  floating-head clearance is inferred.
- `U_TUBE`: physical tube count equals validated pair count. A complete explicit
  pairing plan is required; U-bend geometry is not designed.

### 4.5 No optimization

The caller supplies one pattern, pitch, origin mode, axis orientation, envelope,
and exclusion set. TASK-021 does not auto-rank alternatives.

## 5. Domain model

All objects are immutable and exact-shape. Unknown fields block. Raw types are
validated before coercion. Booleans are not accepted as integers.

### 5.1 Decimal discipline

Unit-bearing public values are canonical base-10 decimal strings:

- finite;
- no exponent notation;
- no leading plus sign;
- no surrounding whitespace;
- no binary floats.

Internal Decimal context:

- precision 50;
- `ROUND_HALF_EVEN`;
- coordinate quantum `0.000000000001` m;
- canonical zero `0`.

### 5.2 `ApprovedTubeGeometrySnapshot`

Exact fields:

| Field | Rule |
|---|---|
| `geometry_id` | non-empty string |
| `geometry_type` | exact `tube` |
| `revision` | non-empty string |
| `approval_state` | exact `approved` |
| `outer_diameter_m` | positive decimal string |
| `inner_diameter_m` | positive decimal string, `< outer_diameter_m` |
| `wall_thickness_m` | positive decimal string |
| `record_hash` | lowercase SHA-256 hex; upstream evidence |
| `snapshot_hash` | lowercase SHA-256 hex; recomputed by TASK-021 core |
| `source_binding` | complete `SourceBindingSnapshot` |

Invariant:

```text
wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2
```

The adapter verifies upstream `record_hash`. The core recomputes only
`snapshot_hash` over every other snapshot field.

### 5.3 `SourceBindingSnapshot`

Exact non-empty string fields:

- `source_id`;
- `source_type`;
- `source_revision`;
- `source_location`;
- `evidence_ref`;
- `approved_by`;
- `approved_at`.

### 5.4 `LayoutRuleAuthoritySnapshot`

Exact fields:

| Field | Rule |
|---|---|
| `profile_id` | exact `hxforge.shell_tube.tube_layout.v1` |
| `authority_mode` | `INTERNAL_GENERIC` or `APPROVED_RULE_PACK`; matches TASK-020 |
| `rule_id` | non-empty string |
| `rule_version` | non-empty string |
| `rule_artifact_canonical_hash` | lowercase SHA-256 hex; upstream evidence |
| `source_class` | recognized TASK-012 value |
| `license_evidence` | canonical JSON value |
| `approval_status` | exact `approved` |
| `provenance_edge_ids` | sorted, duplicate-free strings |
| `evidence_refs` | sorted, duplicate-free strings |
| `rule_pack_identity` | complete object or null |
| `pattern_family` | `SQUARE` or `TRIANGULAR` |
| `pitch_m` | positive decimal string, `>= outer_diameter_m` |
| `edge_clearance_m` | non-negative decimal string |
| `allowed_origin_modes` | non-empty closed subset |
| `allowed_axis_orientations` | non-empty closed subset |
| `allowed_exclusion_zone_types` | closed subset |
| `maximum_candidate_positions` | integer from 1 through 100000 |
| `snapshot_hash` | lowercase SHA-256 hex; recomputed by TASK-021 core |

For `INTERNAL_GENERIC`:

- `source_class == INTERNAL_ENGINEERING_RULE`;
- `rule_pack_identity == null`;
- output retains `NO_STANDARD_CLAIM` semantics.

For `APPROVED_RULE_PACK`, `rule_pack_identity` contains:

- `rule_pack_id`;
- `rule_pack_version`;
- `rule_pack_canonical_hash`.

The adapter verifies upstream rule and pack hashes. The core recomputes only
`snapshot_hash`.

### 5.5 Envelope and request

`CircularTubeCenterEnvelope` exact fields:

- `schema_version = task021.circular-envelope.v1`;
- positive `tube_center_envelope_diameter_m`;
- non-empty, sorted, duplicate-free `evidence_refs`.

`TubeLayoutRequest` exact fields:

- `schema_version = task021.tube-layout-request.v1`;
- complete TASK-020 `configuration`;
- `tube_geometry`;
- `layout_rule_authority`;
- `placement_envelope`;
- `origin_mode`;
- `axis_orientation`;
- `exclusion_zones`;
- `u_tube_pairing_plan` or null;
- sorted, duplicate-free `evidence_refs`.

Closed `OriginMode`:

- `CENTER_ON_LATTICE_POINT`;
- `CENTER_ON_PRIMITIVE_CELL`.

Closed `AxisOrientation`:

- `PRIMARY_AXIS_X`;
- `PRIMARY_AXIS_Y`.

### 5.6 Exclusion zones

Closed `zone_type`:

- `AXIS_ALIGNED_RECTANGLE`;
- `CIRCLE`.

Common exact fields:

- unique non-empty `zone_id`;
- `zone_type`;
- decimal `center_x_m`, `center_y_m`;
- non-negative `clearance_m`;
- non-empty `reason_code`;
- non-empty, sorted, duplicate-free `evidence_refs`.

Rectangle fields: positive `width_m`, positive `height_m`, `radius_m = null`.
Circle fields: positive `radius_m`, `width_m = null`, `height_m = null`.

### 5.7 U-tube pairing plan

`UTubePairingPlan` exact fields:

- `schema_version = task021.u-tube-pairing.v1`;
- non-empty `pairs`;
- non-empty `evidence_refs`;
- lowercase SHA-256 `pairing_plan_hash`.

Each pair contains exactly:

- non-empty `pair_id`;
- `leg_a = {u: int, v: int}`;
- `leg_b = {u: int, v: int}`;
- `evidence_refs`.

Every accepted U-tube leg appears in exactly one pair.

## 6. Lattice construction

### 6.1 Basis

```text
SQRT_3 = 1.7320508075688772935274463415058723669428052538104
```

For pitch `p`, `PRIMARY_AXIS_X`:

```text
SQUARE:
  a = (p, 0)
  b = (0, p)

TRIANGULAR:
  a = (p, 0)
  b = (p / 2, p * SQRT_3 / 2)
```

For `PRIMARY_AXIS_Y`, swap x/y components before forming the basis matrix.

Origin offset:

```text
CENTER_ON_LATTICE_POINT  -> (0, 0)
CENTER_ON_PRIMITIVE_CELL -> (a + b) / 2
```

Candidate coordinate:

```text
raw_coordinate = u * a + v * b + offset
```

### 6.2 Complete inverse-basis bound

Define:

```text
R = tube_center_envelope_diameter_m / 2
r_tube = outer_diameter_m / 2
rho = R - r_tube - edge_clearance_m
```

If `rho <= 0`, block.

```text
A = [[a_x, b_x],
     [a_y, b_y]]

det = a_x * b_y - a_y * b_x
```

If `det == 0`, raise `STL_BASIS_NON_INVERTIBLE`.

Let `B = inverse(A)` and:

```text
d_x = rho + abs(offset_x)
d_y = rho + abs(offset_y)

U = ceil(abs(B_00) * d_x + abs(B_01) * d_y) + 1
V = ceil(abs(B_10) * d_x + abs(B_11) * d_y) + 1

u in [-U, U]
v in [-V, V]
candidate_count = (2 * U + 1) * (2 * V + 1)
```

If candidate count exceeds `maximum_candidate_positions`, raise
`STL_ENUMERATION_LIMIT_EXCEEDED` before coordinate generation. Truncation and
partial results are forbidden.

Synthetic regression:

```text
pattern = TRIANGULAR
axis = PRIMARY_AXIS_X
pitch = 1
rho = 100
offset = (0, 0)
u = -57
v = 115
x = 0.5
y = 115 * SQRT_3 / 2
x^2 + y^2 = 9919 < 10000 = rho^2
```

The candidate must be enumerated. This is mathematical, not an engineering
Golden or standards value.

### 6.3 Acceptance and ordering

Envelope acceptance:

```text
x^2 + y^2 <= rho^2
```

Circle exclusion rejection:

```text
(x - center_x)^2 + (y - center_y)^2
<= (radius + r_tube + clearance)^2
```

Rectangle rejection uses closest-point distance to the closed rectangle and
rejects at distance `<= r_tube + clearance`.

Distinct indices must not quantize to the same coordinate pair.

Accepted positions sort by:

```text
(y_decimal, x_decimal, u, v)
```

Position ID:

```text
UUIDv5(
  UUID_NAMESPACE_URL,
  "urn:hxforge:task021:tube-position:v1:"
  + request_hash + ":" + signed_u + ":" + signed_v
)
```

## 7. Validation pipeline

Run in this exact order:

1. raw top-level mapping and exact fields;
2. raw types before coercion;
3. schema versions;
4. TASK-020 configuration identity;
5. layout-rule mode, profile, approval, snapshot hash, license, provenance;
6. tube-geometry approval, source, snapshot hash, dimensions;
7. envelope;
8. origin, axis, and rule authorization;
9. exclusion-zone shape and duplicate IDs;
10. construction family and U-tube prechecks;
11. inverse-basis bound and capacity;
12. enumeration and geometric filtering;
13. quantization-collision guard;
14. U-tube pairing validation;
15. counts;
16. deterministic warnings;
17. provenance pre-hash, hashes, IDs, and final output.

Stop at the end of a stage when blockers exist. Preserve complete blocker
objects; incomplete-key reconstruction is forbidden.

## 8. Output contract

`TubePosition` exact fields:

- `position_id`;
- `u`;
- `v`;
- canonical decimal `x_m`;
- canonical decimal `y_m`.

`ExclusionAudit` exact fields:

- `zone_id`;
- `rejected_position_count`;
- `reason_code`;
- sorted `evidence_refs`.

`TubeLayout` exact fields:

- `schema_version = task021.tube-layout.v1`;
- `layout_id`;
- `layout_hash`;
- `request_hash`;
- TASK-020 configuration ID/hash and complete case authority;
- construction family, equipment orientation, shell-pass count, tube-pass count;
- complete geometry and layout-rule snapshots;
- envelope, origin, axis, exclusion zones;
- ordered positions;
- tube-hole and physical-tube counts;
- boundary and exclusion rejection counts;
- exclusion audit;
- warnings;
- empty blockers;
- deferred capabilities;
- provenance.

`TubeLayoutValidationResult` exact fields:

- `status: VALID | BLOCKED`;
- `layout: TubeLayout | null`;
- warnings;
- blockers;
- deferred capabilities;
- `blocked_result_hash | null`.

Blocked results contain no partial layout.

Closed deferred set:

- `SHELL_DIAMETER_NOT_COMPUTABLE`;
- `BAFFLE_DESIGN_NOT_COMPUTABLE`;
- `PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE`;
- `THERMAL_RATING_NOT_COMPUTABLE`;
- `KERN_SCREENING_NOT_COMPUTABLE`;
- `BELL_DELAWARE_NOT_COMPUTABLE`;
- `PRESSURE_DROP_NOT_COMPUTABLE`;
- `THERMAL_EXPANSION_NOT_COMPUTABLE`;
- `MECHANICAL_BOUNDARY_NOT_COMPUTABLE`;
- `MATERIAL_SELECTION_NOT_COMPUTABLE`;
- `MASS_NOT_COMPUTABLE`;
- `COST_NOT_COMPUTABLE`;
- `OPTIMIZATION_NOT_COMPUTABLE`;
- `API_NOT_COMPUTABLE`;
- `REPORT_NOT_COMPUTABLE`;
- `GOLDEN_VALIDATION_NOT_COMPUTABLE`.

## 9. Warning and blocker contract

Every warning or blocker has exactly:

- `code`;
- `field_path` or null;
- `message_key`;
- sorted `evidence_refs`;
- canonical JSON `details` or null.

### 9.1 Normative closed blocker set

- `STL_SCHEMA_VERSION_UNSUPPORTED`;
- `STL_UNKNOWN_FIELD`;
- `STL_RAW_TYPE_INVALID`;
- `STL_TASK020_CONFIGURATION_MISSING`;
- `STL_TASK020_CONFIGURATION_INVALID`;
- `STL_TASK020_CONFIGURATION_IDENTITY_MISMATCH`;
- `STL_AUTHORITY_MODE_MISMATCH`;
- `STL_LAYOUT_RULE_AUTHORITY_MISSING`;
- `STL_LAYOUT_RULE_PROFILE_UNSUPPORTED`;
- `STL_LAYOUT_RULE_UNAPPROVED`;
- `STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH`;
- `STL_LAYOUT_RULE_LICENSE_BLOCKED`;
- `STL_LAYOUT_RULE_PROVENANCE_INCOMPLETE`;
- `STL_RULE_PACK_IDENTITY_MISSING`;
- `STL_RULE_PACK_IDENTITY_NOT_EXPECTED`;
- `STL_TUBE_GEOMETRY_MISSING`;
- `STL_TUBE_GEOMETRY_TYPE_INVALID`;
- `STL_TUBE_GEOMETRY_UNAPPROVED`;
- `STL_TUBE_GEOMETRY_SOURCE_INCOMPLETE`;
- `STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH`;
- `STL_TUBE_DIMENSION_INVALID`;
- `STL_TUBE_DIMENSION_INCONSISTENT`;
- `STL_DECIMAL_LEXICAL_INVALID`;
- `STL_PITCH_INVALID`;
- `STL_PITCH_BELOW_TUBE_OD`;
- `STL_EDGE_CLEARANCE_INVALID`;
- `STL_ENVELOPE_INVALID`;
- `STL_ORIGIN_MODE_NOT_AUTHORIZED`;
- `STL_AXIS_ORIENTATION_NOT_AUTHORIZED`;
- `STL_EXCLUSION_ZONE_TYPE_NOT_AUTHORIZED`;
- `STL_EXCLUSION_ZONE_INVALID`;
- `STL_EXCLUSION_ZONE_DUPLICATE_ID`;
- `STL_BASIS_NON_INVERTIBLE`;
- `STL_ENUMERATION_LIMIT_EXCEEDED`;
- `STL_COORDINATE_QUANTIZATION_COLLISION`;
- `STL_NO_TUBE_POSITIONS`;
- `STL_UTUBE_PAIRING_REQUIRED`;
- `STL_UTUBE_PAIRING_NOT_EXPECTED`;
- `STL_UTUBE_PAIRING_HASH_MISMATCH`;
- `STL_UTUBE_PAIRING_INVALID`;
- `STL_CANONICALIZATION_FAILED`.

Historical names `STL_LAYOUT_RULE_HASH_MISMATCH` and
`STL_TUBE_GEOMETRY_HASH_MISMATCH` are non-normative aliases and must not be
emitted by the v1 core.

### 9.2 Deterministic warnings

`STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM`:

- trigger: verified `authority_mode == INTERNAL_GENERIC` only;
- field path: `layout_rule_authority.authority_mode`;
- message key: `internal_generic_no_standard_claim`;
- evidence: layout-rule evidence refs;
- details: authority mode and `NO_STANDARD_CLAIM`.

`STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER`:

- trigger: every VALID result;
- field path: `placement_envelope.tube_center_envelope_diameter_m`;
- message key: `caller_supplied_envelope_not_shell_diameter`;
- evidence: envelope evidence refs;
- details: placement-constraint role and shell diameter `NOT_COMPUTABLE`.

`STL_PASS_PARTITION_ASSIGNMENT_DEFERRED`:

- trigger: every VALID result;
- field path: `configuration.tube_pass_count`;
- message key: `pass_partition_assignment_deferred`;
- evidence: request evidence refs;
- details: verified tube-pass count and assignment `NOT_COMPUTABLE`.

`STL_UTUBE_BEND_GEOMETRY_DEFERRED`:

- trigger: verified `construction_family == U_TUBE` only;
- field path: `u_tube_pairing_plan`;
- message key: `u_tube_bend_geometry_deferred`;
- evidence: pairing-plan evidence refs;
- details: U-tube construction and bend geometry `NOT_COMPUTABLE`.

Warnings are emitted before layout hashing and sorted by:

```text
(code, field_path or "", message_key, canonical_details_hash)
```

## 10. Canonicalization, hashing, and provenance

Canonical JSON uses UTF-8, Unicode code-point key order, stable arrays, no
insignificant whitespace, canonical decimal strings, no NaN/Infinity, and no
runtime-now, host, process, filesystem, or random values.

### 10.1 Snapshot hashes

For each TASK-021 snapshot:

```text
snapshot_hash = SHA-256(canonical_json(all fields except snapshot_hash))
```

The core recomputes snapshot hashes. Upstream artifact hashes are adapter-verified
evidence and are not rederived by the core.

### 10.2 Request and position identities

`request_hash` covers every normalized request field, including complete TASK-020
configuration, both complete snapshots, upstream hashes, snapshot hashes,
envelope, origin, axis, exclusions, pairing plan, evidence refs, and schema.

Position IDs use the formula in §6.3.

### 10.3 `ProvenancePreHashProjection`

`provenance_pre_hash` contains every final deterministic provenance field except
`layout_hash` and `layout_id`:

- task ID and design path;
- TASK-020 configuration ID/hash and complete case authority;
- geometry ID, revision, upstream `record_hash`, TASK-021
  `tube_geometry_snapshot_hash`, and complete source binding;
- layout-rule profile, ID, version, upstream artifact hash, TASK-021
  `layout_rule_snapshot_hash`, source class, approval status, provenance edges,
  evidence refs, and rule-pack identity when present;
- envelope evidence refs;
- exclusion-zone evidence refs;
- U-tube pairing evidence refs when present;
- software version;
- caller-supplied git commit;
- request hash;
- complete canonical warnings;
- complete closed deferred-capability set.

It contains no layout ID, layout hash, or runtime-now metadata.

### 10.4 Layout hash pipeline

`layout_hash_payload` contains exactly:

- output schema version;
- request hash;
- canonical positions including position IDs, indices, and coordinates;
- tube-hole and physical-tube counts;
- boundary and exclusion rejection counts;
- canonical exclusion audit;
- canonical warnings;
- empty blockers;
- deferred capabilities;
- exact `provenance_pre_hash`.

It excludes `layout_id`, `layout_hash`, and any final provenance layout-hash
entry.

Build order:

1. build `provenance_pre_hash`;
2. build `layout_hash_payload`;
3. compute `layout_hash = SHA-256(canonical_json(layout_hash_payload))`;
4. compute `layout_id = UUIDv5(UUID_NAMESPACE_URL,
   "urn:hxforge:task021:tube-layout:v1:" + layout_hash)`;
5. construct final provenance as exactly `provenance_pre_hash` plus one field,
   `layout_hash`;
6. construct final `TubeLayout`.

### 10.5 Blocked result

The blocked-result hash covers the complete normalized context available at the
failure point, complete canonical blockers, and output schema version. It must
not use partial blocker keys.

### 10.6 Pairing plan hash and disjoint defects

Canonical leg is exactly `{u: int, v: int}`. Within a pair, legs sort by numeric
`(u, v)`. Pair order is:

```text
(leg_a.u, leg_a.v, leg_b.u, leg_b.v, pair_id)
```

`pairing_plan_hash_payload` contains exactly:

- schema version;
- canonical pairs;
- sorted, duplicate-free plan evidence refs.

It excludes `pairing_plan_hash` itself.

```text
pairing_plan_hash = SHA-256(canonical_json(pairing_plan_hash_payload))
```

Defect mapping is mutually exclusive:

- `u_tube_pair_unknown_leg`: referenced leg is not accepted;
- `u_tube_pair_leg_reused`: accepted leg occurrence count is greater than 1;
- `u_tube_pair_missing_coverage`: accepted leg occurrence count is exactly 0;
- `u_tube_pair_duplicate_id`: duplicate pair ID;
- `u_tube_pair_self`: both legs are equal.

A missing leg must never also be labeled reused.

Validation order: raw shape, leg normalization, defect checks, canonical order,
payload assembly, hash recomputation, hash comparison.

## 11. Standards and licensing

TASK-021 inherits TASK-012. The repository must not contain copied restricted
standards tables, compatibility matrices, clauses, figures, or formula images.
Evidence pointers and permitted approved artifacts are allowed. TASK-021
acceptance is not certification or legal compliance.

## 12. Future implementation architecture

A separately authorized implementation may use:

```text
src/hexagent/exchangers/shell_tube/tube_layout/
```

Maximum initial modules:

- `models.py`;
- `schema.py`;
- `authority.py`;
- `enumeration.py`;
- `geometry.py`;
- `pairing.py`;
- `canonical.py`;
- `validation.py`;
- `__init__.py`.

Later approved adapters may add `rule_pack_adapter.py` and
`geometry_adapter.py`. Core remains pure and performs no I/O.

## 13. Implementation slicing

Slice A may later implement deterministic core models, validation, enumeration,
geometry predicates, count semantics, pairing, canonicalization, warnings,
blockers, provenance, and synthetic mathematical tests.

Slice B may later implement approved-source adapters only after Slice A merge and
runtime authority reverification.

Shell diameter, pass assignment, baffles, U-bend geometry, rating, pressure
drop, mechanical, material, mass, cost, optimization, API, report, and Golden
integration are not TASK-021 slices.

## 14. Maximum future allowlist

A later implementation authorization may name an exact subset of:

```text
src/hexagent/exchangers/shell_tube/tube_layout/**
tests/exchangers/shell_tube/tube_layout/**
tests/fixtures/task021/**
ci-shard-manifest.yml
```

Existing TASK-020 production and test files are not included.

## 15. Frozen future tests

A future implementation must prove at least:

1. exact fields and raw types before coercion;
2. complete TASK-020 identity verification;
3. geometry and layout-rule snapshot hash recomputation;
4. upstream hashes preserved but not recomputed by core;
5. authority-mode matching;
6. deterministic square and triangular enumeration;
7. inverse-basis regression candidate `u=-57, v=115` is included;
8. non-invertible basis blocks;
9. capacity overflow blocks before partial generation;
10. origin and axis modes are deterministic and not auto-ranked;
11. boundary equality is accepted;
12. circle and rectangle exclusions handle strict/equality boundaries;
13. exclusion order does not affect layout or hash;
14. duplicate zones and quantization collisions block;
15. fixed and floating-head counts equal hole count;
16. U-tube pairings cover every accepted leg exactly once;
17. reused and missing-leg message keys are mutually exclusive;
18. pairing hash is input-order independent;
19. request, position, layout, and blocked identities are stable;
20. `provenance_pre_hash` contains both snapshot hashes and warnings;
21. layout hash payload contains no layout hash or layout ID;
22. final provenance equals pre-hash projection plus only layout hash;
23. warning triggers and five-field payloads are exact;
24. legacy upstream-hash mismatch aliases are never emitted;
25. no shell-diameter output exists;
26. no filesystem, database, or network call occurs in core;
27. TASK-019 Amendment 002-K remains separate;
28. TASK-022 through TASK-039 remain unallocated.

Synthetic mathematical fixtures are not engineering Goldens.

## 16. CI expectations

A future implementation PR must pass Ruff, formatting, mypy, focused tests,
existing TASK-020 tests unchanged, architecture tests, global collection,
manifest verification, and complete exact-head CI.

## 17. Explicit non-actions

This design does not authorize:

- production code, tests, fixtures, workflows, dependencies, lockfiles, or CI
  manifest mutation;
- implementation Issue, branch, commit, or PR;
- shell, bundle, or baffle diameter calculation;
- pass membership or flow-path design;
- rating, pressure drop, mechanical, material, mass, cost, or optimization;
- API, persistence, CLI, report, or Golden integration;
- copied restricted standards content;
- mutation of TASK-001 through TASK-020;
- import of TASK-019 Amendment 002-K scope;
- TASK-022 through TASK-039 allocation;
- Ready, merge, Issue close, review dismissal, thread resolution, or branch
  deletion without separate Charles authorization.

## 18. Review acceptance

The design is eligible for personal review only when:

- exactly this file is changed;
- shell diameter remains deferred;
- all source gaps fail closed;
- the blocker set has no duplicates or contradictory semantics;
- final provenance is constructible from the frozen hash pipeline;
- U-tube defect message keys are mutually exclusive;
- TASK-019 Amendment 002-K remains separate;
- TASK-022 through TASK-039 remain unallocated;
- the PR remains Draft until separately authorized Ready transition.

## 19. Closeout

Issue #137 remains open while the design PR is Draft or unmerged. After merge and
successful exact-merge-SHA main CI, Issue #137 may close only under separate
Charles authorization.

Implementation remains unauthorized after design merge until an exact slice and
exact file subset are separately authorized.
