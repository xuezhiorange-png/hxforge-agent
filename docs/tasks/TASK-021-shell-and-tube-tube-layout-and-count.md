# TASK-021 — Shell-and-Tube Tube Layout and Tube Count Foundation

> Binding design contract for the second M3 shell-and-tube capability.
> TASK-021 consumes one valid TASK-020 shell-and-tube configuration and produces
> one deterministic, authority-bound two-dimensional tube layout and tube count.
> It does not calculate shell diameter, baffles, thermal rating, pressure drop,
> mechanical adequacy, materials, cost, optimization, API output, reports, or
> engineering Golden values.

## 1. Authority, status and authoring boundary

| Field | Value |
|---|---|
| Authorizing Issue | #137 — `[TASK-021][source-definition] Define tube-layout and tube-count foundation` |
| Allocation authorization | Issue #137 comment `4953356685` |
| One-file authoring authorization | Issue #137 comment `4953386614` |
| First design review | PR #138 comment `4953451291` |
| Corrective re-review | PR #138 comment `4953517481` |
| Final design re-review | PR #138 comment `4953630921` |
| Round-2 authorization | `AUTHORIZE_TASK021_DESIGN_CORRECTIVE_ROUND_2_PROVENANCE_BLOCKERS_PAIRING_METADATA` |
| Round-3 authorization | Charles message `AUTHORIZE_TASK021_DESIGN_CORRECT`, interpreted only as the immediately preceding Round-3 exact-contract restoration gate |
| Frozen task allocation | `TASK-021 = Shell-and-Tube Tube Layout and Tube Count Foundation` |
| Explicit deferred boundary | Shell diameter remains deferred and unallocated |
| Design branch | `docs/task-021-tube-layout-count-design` |
| Design file | `docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md` |
| Allowed repository path | This design file only |
| Authoring base | `main` at `9fd0969b8b512c6b631d122f60057df3062fc416` |
| Direct predecessor | TASK-020 — Shell-and-Tube Configuration Schema Foundation |
| Licensing authority | TASK-012 — Standards rule-pack and license boundary |
| Geometry-contract reference | TASK-016 — Approved Tube, Pipe and Hairpin Geometry Catalog Design Contract |
| Product authority | `docs/MASTER_DEVELOPMENT_SPEC.md`, especially §§2, 7, 8.2 and 9 |
| Design status | PROPOSED until this design PR is reviewed and merged |
| Implementation status | NOT AUTHORIZED |
| Ready status | NOT AUTHORIZED |
| Merge status | NOT AUTHORIZED |
| TASK-022 through TASK-039 | UNALLOCATED |

This contract restores the exact deterministic clauses present at reviewed head
`7e05a107688d47f64d4690ccb48d205ce90278a9` and applies the approved Round-2
corrections without retaining the Round-2 consolidation regressions.

This round does not authorize implementation, a Ready transition, merge, Issue
closure, backlog mutation, test or fixture mutation, CI-manifest mutation,
workflow mutation, review dismissal, review-thread resolution, branch deletion,
or allocation of any later M3 task.

## 2. Exact TASK-021 allocation

TASK-021 owns **Shell-and-Tube Tube Layout and Tube Count Foundation**.

The capability is deliberately narrower than a shell-and-tube sizing or rating
engine. It owns:

1. consumption of one complete valid TASK-020 `ShellAndTubeConfiguration`;
2. consumption of explicit immutable approved geometry-authority snapshots;
3. consumption of explicit immutable approved layout-rule snapshots;
4. deterministic enumeration of tube-center positions inside one caller-supplied
   circular placement envelope;
5. deterministic application of explicit circular and axis-aligned rectangular
   exclusion zones;
6. deterministic tube-hole and physical-tube counting;
7. construction-family-specific count semantics for fixed-tubesheet, U-tube and
   floating-head configurations;
8. canonical serialization, content hashing, deterministic identity, warnings,
   blockers, provenance and audit summaries;
9. explicit `NOT_COMPUTABLE` declarations for every later capability.

TASK-021 does not select or derive a shell diameter, bundle diameter, baffle
diameter or shell-to-bundle clearance. The field
`tube_center_envelope_diameter_m` is a caller-supplied tube-center placement
constraint. It is not a shell inside diameter and must never be renamed or
reported as one.

## 3. Source-of-truth inventory

### 3.1 Binding repository authority

TASK-021 is derived from:

- `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md` and the current
  `hexagent.exchangers.shell_tube` implementation;
- `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md`;
- `docs/tasks/TASK-016-approved-geometry-catalog.md` as a shape and governance
  reference only;
- `docs/MASTER_DEVELOPMENT_SPEC.md`;
- Issue #137 and the authorization comments listed in §1;
- PR #138 review history listed in §1.

TASK-020 supplies validated configuration identity, construction family,
equipment orientation, shell-pass count, tube-pass count, component tokens,
case authority, authority binding, warnings, blockers and deferred-capability
declarations. TASK-020 intentionally supplies no tube diameter, pitch, tube
coordinates, shell diameter, baffle geometry or engineering-performance result.

### 3.2 Required capabilities currently absent

The following must not be simulated or silently invented:

- a runtime shell-and-tube geometry catalog;
- approved tube-layout rule-pack content not carried by the request;
- licensed external-standard tables or compatibility matrices;
- shell-diameter or bundle-to-shell-clearance methods;
- baffle geometry;
- tube-pass partition assignment algorithms;
- U-bend design geometry;
- thermal rating, Kern screening, Bell–Delaware, leakage or bypass corrections;
- pressure-drop decomposition;
- vibration, thermal-expansion or mechanical checks;
- shell-and-tube material, mass, cost or optimization models;
- public API, report and engineering Golden integration.

TASK-021 consumes caller-supplied immutable authority snapshots. The deterministic
core performs no filesystem walk, catalog scan, database lookup, network lookup
or hidden default substitution.

## 4. Frozen design decisions

### 4.1 TASK-020 configuration input

The request carries the complete valid TASK-020
`ShellAndTubeConfiguration`. An ID, hash or partial projection is insufficient.
The core verifies:

- `equipment_family == SHELL_AND_TUBE`;
- the supplied configuration has no TASK-020 blockers;
- the complete TASK-020 canonical payload reproduces `configuration_hash`;
- the TASK-020 UUID helper reproduces `configuration_id` from that hash.

Any mismatch blocks the request. TASK-021 performs no persistence lookup and
does not rebuild TASK-020 semantics.

### 4.2 Geometry-source decision

TASK-021 accepts one `ApprovedTubeGeometrySnapshot`. It is a complete immutable
projection of a TASK-016-conformant approved tube record and includes source
binding, upstream record identity and a TASK-021-recomputable snapshot identity.
TASK-021 does not load a TASK-016 catalog at runtime.

A future adapter may construct this snapshot only after loading and validating
the upstream object and verifying its upstream hash. The deterministic core
recomputes only the TASK-021 snapshot hash.

### 4.3 Layout-rule decision

TASK-021 accepts one evaluated `LayoutRuleAuthoritySnapshot`. It is not raw
standard text and is not an unreviewed user preference. The frozen profile is:

```text
hxforge.shell_tube.tube_layout.v1
```

A TASK-020 configuration rule is not implicitly a TASK-021 layout rule. The
layout snapshot must explicitly declare this profile.

### 4.4 No runtime lookup or hidden inference

The deterministic core must not:

- call the filesystem;
- scan a catalog directory;
- query a database;
- call a network service;
- choose a default tube geometry;
- infer pitch from tube diameter;
- infer a pattern from a TEMA token;
- infer an exclusion lane from tube-pass count;
- infer U-tube pairings;
- infer shell diameter from the placement envelope;
- test alternatives and silently choose the maximum tube count.

### 4.5 Closed pattern set

The closed v1 set is:

- `SQUARE`;
- `TRIANGULAR`.

These names describe generic mathematical lattices only and make no TEMA, API,
ISO, vendor, certification or legal-compliance claim. Rotated, radial,
concentric-ring, arbitrary custom and vendor-proprietary patterns are deferred.

### 4.6 Placement envelope

TASK-021 accepts one circular tube-center placement envelope centered at `(0,0)`.
The complete tube disk plus approved edge clearance must lie inside the envelope.
The envelope is supplied, not calculated.

### 4.7 Pass-partition boundary

TASK-021 does not assign individual tubes to passes and does not design partition
plates, nozzles or flow paths. Explicit geometric lanes may be reserved only
through caller-supplied exclusion zones. `tube_pass_count` is preserved and
validated but is not used to fabricate pass membership.

Every valid result therefore carries:

```text
PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE
```

### 4.8 Construction-family count semantics

- `FIXED_TUBESHEET`: each accepted tube-hole position represents one straight
  physical tube.
- `FLOATING_HEAD`: each accepted tube-hole position represents one straight
  physical tube; no floating-head clearance or mechanical geometry is inferred.
- `U_TUBE`: each physical tube has two tubesheet-leg positions; a complete
  explicit `UTubePairingPlan` is required. TASK-021 validates and counts pairs
  but does not design U-bend radius, bend shape or fabrication feasibility.

A U-tube request without a complete valid pairing plan is blocked and returns no
partial layout.

### 4.9 No optimization

The caller supplies one pattern, pitch, origin mode, axis orientation, envelope
and exclusion set. TASK-021 does not rank or optimize variants.

## 5. Dependency contract

### 5.1 Direct dependencies

| Dependency | Use |
|---|---|
| TASK-002 | SI discipline and explicit base-unit field names |
| TASK-004 | complete structured warning, blocker and provenance conventions |
| TASK-012 | source class, approval, license and rule-pack governance |
| TASK-014 | case authority inherited through the complete TASK-020 configuration |
| TASK-015A | deterministic test and CI governance for future implementation |
| TASK-020 | complete validated shell-and-tube configuration and identity helpers |
| TASK-016 | approved tube-record shape and source-binding reference only |

### 5.2 Reference-only dependencies

TASK-007 through TASK-010 and TASK-017 through TASK-019 demonstrate deterministic
engineering, material, cost, report and Golden patterns but their double-pipe
results are not shell-and-tube computation authority. TASK-019 Amendment 002-K
remains an M2 cost-stack follow-up and must not be imported.

### 5.3 Explicit prohibitions

TASK-021 must not:

- mutate TASK-001 through TASK-020 frozen contracts;
- import double-pipe geometry as shell-and-tube layout data;
- treat TASK-016 hairpin geometry as a shell-and-tube bundle;
- reuse TASK-017 material or mechanical conclusions;
- reuse TASK-018 cost results;
- consume TASK-019 fixture bridges or expected-output values;
- interpret the placement envelope as later shell geometry.

## 6. Common exact-shape and canonical-value rules

All value objects are immutable and have exact field sets. Unknown fields block.
Raw types are validated before coercion. Booleans are not accepted as integers.
Strings, integers, arrays and mappings are never silently converted from another
type.

### 6.1 Canonical JSON value domain

At every public serialization or hash boundary, a JSON value may contain only:

- `null`;
- booleans;
- integers;
- canonical finite decimal strings;
- strings;
- arrays of permitted JSON values;
- objects with string keys and permitted JSON values.

The following are forbidden and block canonicalization:

- binary floating-point values;
- `Decimal` objects at the serialization boundary;
- NaN or Infinity;
- bytes;
- sets or tuples used as implicit arrays;
- datetime objects;
- host-locale values;
- process, filesystem or runtime-now metadata;
- arbitrary Python objects.

`license_evidence`, warning/blocker `details`, provenance fragments and all hash
payloads use this exact domain.

### 6.2 Array normalization and duplicate handling

For every array declared **sorted and duplicate-free**:

1. raw element types are validated;
2. duplicate equality is evaluated on the canonical element representation;
3. duplicates block with `STL_RAW_TYPE_INVALID` and message key
   `duplicate_array_item`;
4. the validated unique elements are sorted by the ordering declared for that
   field;
5. the implementation must not silently discard duplicates.

Arrays with contract-defined semantic order, such as canonical positions,
canonical pairs, warnings, blockers and deferred capabilities, use their own
frozen ordering and are not re-sorted by generic string representation.

### 6.3 Decimal SI representation

Every unit-bearing public request value is a canonical base-10 decimal string.
It must be finite, must not use exponent notation, must not have a leading plus
sign and must not contain surrounding whitespace. Negative zero normalizes to
`0` and is rejected where a positive value is required.

The frozen internal Decimal context is:

- precision: 50 decimal digits;
- rounding: `ROUND_HALF_EVEN`;
- coordinate quantum: `0.000000000001` m;
- canonical zero: `0`.

## 7. Domain model

### 7.1 `ApprovedTubeGeometrySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `geometry_id` | string | non-empty stable identity |
| `geometry_type` | string | exact `tube` |
| `revision` | string | non-empty |
| `approval_state` | string | exact `approved` |
| `outer_diameter_m` | decimal string | positive |
| `inner_diameter_m` | decimal string | positive and smaller than OD |
| `wall_thickness_m` | decimal string | positive and algebraically consistent |
| `record_hash` | string | lowercase 64-character SHA-256 hex; upstream evidence |
| `snapshot_hash` | string | lowercase 64-character SHA-256 hex; recomputed by core |
| `source_binding` | object | complete `SourceBindingSnapshot` |

The invariant is:

```text
wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2
```

It is evaluated with Decimal arithmetic under §6.3. A mismatch blocks.

`record_hash` is verified by the upstream adapter against the upstream record
body. The core does not own that body and does not rederive `record_hash`.

`snapshot_hash` is the SHA-256 hash of canonical JSON containing every other
snapshot field, including `record_hash` and complete `source_binding`, with
`snapshot_hash` itself excluded. A mismatch emits
`STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH`.

The snapshot carries no material grade, allowable stress, corrosion allowance,
pressure rating, fouling value, vendor availability, procurement state or cost.

### 7.2 `SourceBindingSnapshot`

Exact required non-empty string fields:

- `source_id`;
- `source_type`;
- `source_revision`;
- `source_location`;
- `evidence_ref`;
- `approved_by`;
- `approved_at`.

`approved_at` is serialized as the supplied normalized string and is not parsed
using host locale or local timezone rules.

### 7.3 `RulePackIdentitySnapshot`

Exact fields:

- `rule_pack_id`: non-empty string;
- `rule_pack_version`: non-empty string;
- `rule_pack_canonical_hash`: lowercase 64-character SHA-256 hex.

The rule-pack hash is upstream evidence verified by the adapter, not rederived by
the TASK-021 core.

### 7.4 `LayoutRuleAuthoritySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `profile_id` | string | exact `hxforge.shell_tube.tube_layout.v1` |
| `authority_mode` | enum | `INTERNAL_GENERIC` or `APPROVED_RULE_PACK`; must match TASK-020 |
| `rule_id` | string | non-empty |
| `rule_version` | string | non-empty |
| `rule_artifact_canonical_hash` | string | lowercase SHA-256 hex; upstream evidence |
| `source_class` | TASK-012 enum string | recognized value |
| `license_evidence` | canonical JSON value | required |
| `approval_status` | string | exact `approved` |
| `provenance_edge_ids` | array[string] | sorted Unicode code-point order, duplicate-free |
| `evidence_refs` | array[string] | sorted Unicode code-point order, duplicate-free |
| `rule_pack_identity` | object or null | required for rule-pack mode, null for internal mode |
| `pattern_family` | enum | `SQUARE` or `TRIANGULAR` |
| `pitch_m` | decimal string | positive and `>= outer_diameter_m` |
| `edge_clearance_m` | decimal string | non-negative |
| `allowed_origin_modes` | array[enum] | non-empty canonical enum order, duplicate-free |
| `allowed_axis_orientations` | array[enum] | non-empty canonical enum order, duplicate-free |
| `allowed_exclusion_zone_types` | array[enum] | canonical enum order, duplicate-free |
| `maximum_candidate_positions` | integer | `1 <= value <= 100000` |
| `snapshot_hash` | string | lowercase SHA-256 hex; recomputed by core |

`rule_artifact_canonical_hash` and any rule-pack hash are upstream evidence. The
adapter verifies them before snapshot construction. The core recomputes only
`snapshot_hash` over canonical JSON of every other field, excluding
`snapshot_hash` itself. A mismatch emits
`STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH`.

For `INTERNAL_GENERIC`:

- `source_class == INTERNAL_ENGINEERING_RULE`;
- `rule_pack_identity == null`;
- the result retains `NO_STANDARD_CLAIM` semantics.

For `APPROVED_RULE_PACK`:

- `rule_pack_identity` is complete;
- TASK-012 approval, license, canonical-hash and provenance requirements are
  satisfied;
- no restricted source body is copied into the snapshot.

### 7.5 `CircularTubeCenterEnvelope`

Exact fields:

- `schema_version`: exact `task021.circular-envelope.v1`;
- `tube_center_envelope_diameter_m`: positive decimal string;
- `evidence_refs`: non-empty sorted Unicode code-point array, duplicate-free.

The coordinate origin is fixed at `(0,0)`.

### 7.6 `OriginMode`

Closed ordered set:

1. `CENTER_ON_LATTICE_POINT`;
2. `CENTER_ON_PRIMITIVE_CELL`.

### 7.7 `AxisOrientation`

Closed ordered set:

1. `PRIMARY_AXIS_X`;
2. `PRIMARY_AXIS_Y`.

This is mathematical lattice orientation, not equipment orientation.

### 7.8 `LatticeIndex`

Exact fields:

- `u`: signed integer, boolean forbidden;
- `v`: signed integer, boolean forbidden.

Integer indices are the pre-quantization identity of a candidate position.

### 7.9 `ExclusionZone`

Closed `zone_type` set and order:

1. `AXIS_ALIGNED_RECTANGLE`;
2. `CIRCLE`.

Common exact fields:

- `zone_id`: non-empty string, globally unique after validation;
- `zone_type`;
- `center_x_m`: decimal string;
- `center_y_m`: decimal string;
- `clearance_m`: non-negative decimal string;
- `reason_code`: non-empty opaque audit code;
- `evidence_refs`: non-empty sorted Unicode code-point array, duplicate-free;
- `width_m`;
- `height_m`;
- `radius_m`.

Rectangle form:

- `width_m`: positive decimal string;
- `height_m`: positive decimal string;
- `radius_m`: null.

Circle form:

- `radius_m`: positive decimal string;
- `width_m`: null;
- `height_m`: null.

Arbitrary polygons, splines and rotated rectangles are out of scope.

The canonical `exclusion_zones` array is sorted by `zone_id` in ascending Unicode
code-point order. Input order never affects request or layout identity.

### 7.10 `UTubePairingPlan`

Exact fields:

- `schema_version`: exact `task021.u-tube-pairing.v1`;
- `pairs`: non-empty array of `UTubePair`;
- `evidence_refs`: non-empty sorted Unicode code-point array, duplicate-free;
- `pairing_plan_hash`: lowercase 64-character SHA-256 hex.

Each `UTubePair` contains exactly:

- `pair_id`: non-empty string;
- `leg_a`: exact `LatticeIndex`;
- `leg_b`: exact `LatticeIndex`;
- `evidence_refs`: sorted Unicode code-point array, duplicate-free.

Every accepted U-tube leg appears in exactly one pair. TASK-021 does not compute
U-bend radius, bend length, bend stress, minimum spacing or fabrication
feasibility.

### 7.11 `TubeLayoutRequest`

Exact fields:

| Field | Type | Requirement |
|---|---|---|
| `schema_version` | string | exact `task021.tube-layout-request.v1` |
| `configuration` | complete TASK-020 object | required |
| `tube_geometry` | `ApprovedTubeGeometrySnapshot` | required |
| `layout_rule_authority` | `LayoutRuleAuthoritySnapshot` | required |
| `placement_envelope` | `CircularTubeCenterEnvelope` | required |
| `origin_mode` | enum | allowed by authority snapshot |
| `axis_orientation` | enum | allowed by authority snapshot |
| `exclusion_zones` | array | required, may be empty, canonical order §7.9 |
| `u_tube_pairing_plan` | object or null | required for U-tube, null otherwise |
| `evidence_refs` | array[string] | sorted Unicode code-point order, duplicate-free |

## 8. Lattice construction and geometry

### 8.1 Mathematical constant

```text
SQRT_3 = 1.7320508075688772935274463415058723669428052538104
```

It is parsed under the frozen Decimal context and is not standards content.

### 8.2 Basis vectors

Let `p = pitch_m`.

For `PRIMARY_AXIS_X`:

```text
SQUARE:
  a = (p, 0)
  b = (0, p)

TRIANGULAR:
  a = (p, 0)
  b = (p / 2, p * SQRT_3 / 2)
```

For `PRIMARY_AXIS_Y`, swap the x and y components of both vectors before forming
the basis matrix.

### 8.3 Origin offset

```text
CENTER_ON_LATTICE_POINT  -> (0, 0)
CENTER_ON_PRIMITIVE_CELL -> (a + b) / 2
```

Candidate work coordinates are:

```text
raw_coordinate = u * a + v * b + offset
```

All acceptance tests use unquantized Decimal work coordinates. Quantization is
an output representation step only.

### 8.4 Complete inverse-basis enumeration bound

Define:

```text
R = tube_center_envelope_diameter_m / 2
r_tube = outer_diameter_m / 2
rho = R - r_tube - edge_clearance_m
```

If `rho <= 0`, block with `STL_ENVELOPE_INVALID`.

```text
A = [[a_x, b_x],
     [a_y, b_y]]

det = a_x * b_y - a_y * b_x
```

If `det == 0`, block with `STL_BASIS_NON_INVERTIBLE`.

Let `B = inverse(A)` under the same Decimal context and basis values used for
coordinate generation:

```text
d_x = rho + abs(offset_x)
d_y = rho + abs(offset_y)

U = ceil(abs(B_00) * d_x + abs(B_01) * d_y) + 1
V = ceil(abs(B_10) * d_x + abs(B_11) * d_y) + 1

u in [-U, U]
v in [-V, V]

candidate_count = (2 * U + 1) * (2 * V + 1)
```

The `+1` terms are frozen conservative guards. Before generating any coordinate,
compare `candidate_count` with `maximum_candidate_positions`. If it exceeds the
limit, block with `STL_ENUMERATION_LIMIT_EXCEEDED`. Truncation and partial
results are forbidden.

Synthetic completeness regression:

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

The candidate must be enumerated. This is a mathematical regression, not an
engineering Golden or standards value.

### 8.5 Envelope acceptance

A candidate is inside the placement envelope exactly when:

```text
x^2 + y^2 <= rho^2
```

Equality is accepted.

`boundary_rejection_count` counts every generated candidate that fails this test
before exclusion-zone evaluation.

### 8.6 Circle exclusion

A candidate is rejected by a circle when:

```text
(x - center_x)^2 + (y - center_y)^2
<= (radius + r_tube + clearance)^2
```

Equality is rejected.

### 8.7 Rectangle exclusion

For an axis-aligned closed rectangle, compute the closest point on the rectangle
to the candidate center. Reject when the closest-point distance is:

```text
<= r_tube + clearance
```

Equality is rejected.

### 8.8 Multi-zone overlap accounting

Exclusion zones are evaluated in canonical `zone_id` order, but acceptance is
set-based and independent of order.

For a candidate matching multiple zones:

- the candidate contributes exactly `1` to `exclusion_rejection_count`;
- it contributes exactly `1` to the `rejected_position_count` of every matching
  zone;
- it appears in no accepted-position array;
- no first-match or short-circuit rule may hide later zone audit matches.

A zone matching no candidates still produces one `ExclusionAudit` entry with
`rejected_position_count = 0`.

### 8.9 Quantization and collision guard

After acceptance and exclusion filtering, quantize x and y to the coordinate
quantum under `ROUND_HALF_EVEN`. If two distinct `(u,v)` indices quantize to the
same canonical `(x_m,y_m)` pair, block with
`STL_COORDINATE_QUANTIZATION_COLLISION`. Coordinates must never replace indices
as identity.

### 8.10 Canonical position ordering and identity

Accepted positions sort by:

```text
(y_decimal, x_decimal, u, v)
```

Position ID is:

```text
UUIDv5(
  UUID_NAMESPACE_URL,
  "urn:hxforge:task021:tube-position:v1:"
  + request_hash + ":" + signed_u + ":" + signed_v
)
```

`signed_u` and `signed_v` are canonical base-10 signed integer strings with no
leading plus sign or leading zeroes except `0`.

## 9. Validation pipeline

The future validator runs these stages in exact order:

1. raw top-level mapping and exact field-set validation;
2. raw value types before coercion;
3. schema versions;
4. TASK-020 configuration completeness and identity;
5. authority-mode match;
6. layout-rule profile, approval, TASK-021 snapshot hash, license, provenance and
   rule-pack identity;
7. tube-geometry approval, source binding, TASK-021 snapshot hash and dimensions;
8. envelope shape and positive effective radius;
9. origin and axis authorization;
10. exclusion-zone exact shapes, evidence arrays and duplicate zone IDs;
11. construction-family and U-tube presence/null prechecks;
12. inverse-basis construction, invertibility and candidate capacity;
13. enumeration and envelope filtering;
14. complete multi-zone exclusion evaluation and audit accumulation;
15. coordinate quantization and collision guard;
16. U-tube pairing validation and hash verification;
17. tube-hole and physical-tube counts;
18. deterministic warning emission;
19. provenance pre-hash projection;
20. request, layout and output identity construction;
21. final output assembly.

At the end of a stage, if one or more blockers exist, later stages do not run.
All blockers produced by that stage are retained as complete objects and sorted
by §11.3. A blocked result carries no partial layout or partial coordinate list.

## 10. Output contract

### 10.1 `TubePosition`

Exact fields:

- `position_id`: UUID string;
- `u`: signed integer;
- `v`: signed integer;
- `x_m`: canonical decimal string;
- `y_m`: canonical decimal string.

### 10.2 `ExclusionAudit`

Exact fields:

- `zone_id`: string;
- `rejected_position_count`: non-negative integer;
- `reason_code`: string copied from the zone;
- `evidence_refs`: sorted Unicode code-point array, duplicate-free.

The audit array contains exactly one entry for every exclusion zone and is sorted
by `zone_id` in ascending Unicode code-point order.

### 10.3 `TubeLayout`

Exact fields:

| Field | Rule |
|---|---|
| `schema_version` | exact `task021.tube-layout.v1` |
| `layout_id` | deterministic UUIDv5 §12.7 |
| `layout_hash` | lowercase SHA-256 hex §12.7 |
| `request_hash` | lowercase SHA-256 hex §12.4 |
| `task020_configuration_id` | copied from verified configuration |
| `task020_configuration_hash` | copied from verified configuration |
| `case_authority` | complete TASK-020 case authority |
| `construction_family` | copied from verified configuration |
| `equipment_orientation` | copied from verified configuration |
| `shell_pass_count` | copied; no shell geometry inferred |
| `tube_pass_count` | copied; no pass membership inferred |
| `tube_geometry` | complete canonical approved snapshot |
| `layout_rule_authority` | complete canonical authority snapshot |
| `placement_envelope` | complete canonical envelope |
| `origin_mode` | normalized request value |
| `axis_orientation` | normalized request value |
| `exclusion_zones` | canonical zone-ID order |
| `positions` | §8.10 order |
| `tube_hole_count` | number of accepted positions |
| `physical_tube_count` | straight count or validated U-tube pair count |
| `boundary_rejection_count` | §8.5 count |
| `exclusion_rejection_count` | unique rejected candidates §8.8 |
| `exclusion_audit` | zone-ID order §10.2 |
| `warnings` | complete five-field objects in §11.4 order |
| `blockers` | exact empty array for valid layout |
| `deferred_capabilities` | exact §10.5 ordered array |
| `provenance` | exact §12.6 final object |

### 10.4 `TubeLayoutValidationResult`

Exact fields:

- `status`: `VALID` or `BLOCKED`;
- `layout`: complete `TubeLayout` or null;
- `warnings`: canonical warning array;
- `blockers`: canonical blocker array;
- `deferred_capabilities`: exact ordered array;
- `blocked_result_hash`: lowercase SHA-256 hex or null.

For `VALID`:

- `layout` is non-null;
- `blockers` is empty;
- `blocked_result_hash` is null.

For `BLOCKED`:

- `layout` is null;
- `blockers` is non-empty;
- `blocked_result_hash` is non-null;
- no partial position, audit or count result is returned.

### 10.5 Closed ordered deferred-capability array

Every valid result carries this exact order:

1. `SHELL_DIAMETER_NOT_COMPUTABLE`;
2. `BAFFLE_DESIGN_NOT_COMPUTABLE`;
3. `PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE`;
4. `THERMAL_RATING_NOT_COMPUTABLE`;
5. `KERN_SCREENING_NOT_COMPUTABLE`;
6. `BELL_DELAWARE_NOT_COMPUTABLE`;
7. `PRESSURE_DROP_NOT_COMPUTABLE`;
8. `THERMAL_EXPANSION_NOT_COMPUTABLE`;
9. `MECHANICAL_BOUNDARY_NOT_COMPUTABLE`;
10. `MATERIAL_SELECTION_NOT_COMPUTABLE`;
11. `MASS_NOT_COMPUTABLE`;
12. `COST_NOT_COMPUTABLE`;
13. `OPTIMIZATION_NOT_COMPUTABLE`;
14. `API_NOT_COMPUTABLE`;
15. `REPORT_NOT_COMPUTABLE`;
16. `GOLDEN_VALIDATION_NOT_COMPUTABLE`.

These are capability declarations. No numeric placeholder or fabricated fallback
may accompany them. A blocked result carries the same ordered array for the
capability boundary; the array is not dependent on the failure stage.

## 11. Warning and blocker contract

Every warning or blocker has exactly:

- `code`: string;
- `field_path`: string or null;
- `message_key`: string;
- `evidence_refs`: sorted Unicode code-point array, duplicate-free;
- `details`: canonical JSON object or null under §6.1.

Unknown fields are forbidden.

### 11.1 Normative closed blocker-code set

The v1 core may emit only:

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
`STL_TUBE_GEOMETRY_HASH_MISMATCH` are non-normative migration aliases only. They
are not members of the closed set and must never be emitted by the v1 core.

### 11.2 Blocker stage aggregation

A validation stage may emit multiple blockers. The implementation must retain all
complete blockers discovered within that stage before stopping. It must not
reconstruct blockers from `(code, field_path, message_key)` or discard `details`
or evidence.

### 11.3 Canonical blocker ordering

Before entering `TubeLayoutValidationResult` or `blocked_result_hash`, blockers
sort by this exact composite key:

```text
(
  code,
  field_path or "",
  message_key,
  canonical_details_hash,
  canonical_evidence_refs_hash
)
```

Where:

```text
canonical_details_hash = SHA-256(canonical_json(details))
canonical_evidence_refs_hash = SHA-256(canonical_json(evidence_refs))
```

`details == null` hashes the canonical JSON bytes for `null`. This ordering is
used even when only one blocker exists.

### 11.4 Canonical warning ordering

Warnings sort by the same composite key as blockers. Warnings are generated
before `layout_hash` computation and enter the layout hash in this order.

### 11.5 `STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM`

Emit only when verified
`layout_rule_authority.authority_mode == INTERNAL_GENERIC`.

Exact object fields:

```text
code = "STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM"
field_path = "layout_rule_authority.authority_mode"
message_key = "internal_generic_no_standard_claim"
evidence_refs = layout_rule_authority.evidence_refs
```

Exact `details` key set and values:

```json
{
  "authority_mode": "INTERNAL_GENERIC",
  "standard_claim_status": "NO_STANDARD_CLAIM"
}
```

Do not emit for `APPROVED_RULE_PACK`. On a blocked result, emit only if authority
mode, approval and evidence refs were all verified before the failing stage.

### 11.6 `STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER`

Emit on every valid result.

```text
code = "STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER"
field_path = "placement_envelope.tube_center_envelope_diameter_m"
message_key = "caller_supplied_envelope_not_shell_diameter"
evidence_refs = placement_envelope.evidence_refs
```

Exact `details`:

```json
{
  "semantic_role": "tube_center_placement_constraint",
  "shell_diameter_status": "NOT_COMPUTABLE"
}
```

For a blocked result, emit only if the envelope and its evidence refs were fully
verified before failure. Do not fabricate it when validation stops earlier.

### 11.7 `STL_PASS_PARTITION_ASSIGNMENT_DEFERRED`

Emit on every valid result.

```text
code = "STL_PASS_PARTITION_ASSIGNMENT_DEFERRED"
field_path = "configuration.tube_pass_count"
message_key = "pass_partition_assignment_deferred"
evidence_refs = request.evidence_refs
```

Exact `details`:

```json
{
  "assignment_status": "NOT_COMPUTABLE",
  "tube_pass_count": "<verified integer value>"
}
```

The actual value is a JSON integer, not a string. Do not emit on a blocked result
unless `tube_pass_count` and request evidence refs were fully verified.

### 11.8 `STL_UTUBE_BEND_GEOMETRY_DEFERRED`

Emit only when verified `construction_family == U_TUBE`.

```text
code = "STL_UTUBE_BEND_GEOMETRY_DEFERRED"
field_path = "u_tube_pairing_plan"
message_key = "u_tube_bend_geometry_deferred"
evidence_refs = u_tube_pairing_plan.evidence_refs
```

Exact `details`:

```json
{
  "bend_geometry_status": "NOT_COMPUTABLE",
  "construction_family": "U_TUBE"
}
```

Do not emit for fixed-tubesheet or floating-head. For a blocked U-tube result,
emit only after the pairing plan and its evidence refs have been fully verified.

No implementation may add, omit or alter a warning whose exact trigger is
satisfied.

## 12. Canonicalization, hashing and identity

### 12.1 Canonical JSON

Canonical JSON uses:

- UTF-8;
- object keys sorted lexicographically by Unicode code point;
- no insignificant whitespace;
- the exact array ordering frozen by this contract;
- canonical decimal strings, never binary floats;
- canonical JSON values only under §6.1;
- no host, locale, filesystem, process, runtime-now or random values.

### 12.2 Snapshot hashes

For each TASK-021 snapshot:

```text
snapshot_hash = SHA-256(canonical_json(all exact fields except snapshot_hash))
```

Upstream record, artifact and rule-pack hashes remain present inside the payload
as evidence. The deterministic core does not rederive those upstream hashes.

### 12.3 Canonical request projections

Before hashing:

- exclusion zones use §7.9 zone-ID order;
- all evidence-ref arrays use sorted Unicode order and are duplicate-free;
- allowed enum arrays use their closed enum order;
- the pairing plan uses §12.9 canonical pair order and exact pair payload;
- no input array order remains as implicit authority.

### 12.4 Request hash

`request_hash` is SHA-256 over canonical JSON of every normalized request field:

- request schema version;
- complete verified TASK-020 configuration;
- complete geometry snapshot including both hashes;
- complete layout-rule snapshot including all upstream and snapshot hashes;
- complete placement envelope;
- origin mode;
- axis orientation;
- canonical exclusion zones;
- complete canonical U-tube pairing plan when present;
- sorted request evidence refs.

No computation-authority field is excluded.

### 12.5 Position identity

Position IDs use §8.10 and therefore depend on `request_hash` and canonical
indices, not coordinates alone.

### 12.6 `ProvenancePreHashProjection`

`provenance_pre_hash` contains every final deterministic provenance field except
`layout_hash` and `layout_id`:

- `task_id = TASK-021`;
- design-contract path;
- TASK-020 configuration ID and hash;
- complete TASK-020 case authority;
- geometry ID and revision;
- upstream geometry `record_hash`;
- TASK-021 `tube_geometry_snapshot_hash`;
- complete geometry source binding;
- layout-rule profile, ID and version;
- upstream `rule_artifact_canonical_hash`;
- TASK-021 `layout_rule_snapshot_hash`;
- source class and approval status;
- complete provenance edge IDs;
- complete layout-rule evidence refs;
- complete rule-pack identity when present;
- envelope evidence refs;
- exclusion-zone evidence refs in zone-ID order;
- U-tube pairing evidence refs when present;
- software version;
- caller-supplied git commit;
- request hash;
- complete canonical warnings in §11.4 order;
- complete ordered deferred-capability array in §10.5 order.

It contains no layout ID, layout hash, runtime-now timestamp or host metadata.

### 12.7 Layout hash and ID pipeline

`layout_hash_payload` contains exactly:

- output schema version;
- request hash;
- canonical positions including IDs, indices and coordinates;
- tube-hole count;
- physical-tube count;
- boundary rejection count;
- exclusion rejection count;
- canonical exclusion audit in zone-ID order;
- canonical warnings in §11.4 order;
- canonical empty blockers array;
- ordered deferred capabilities;
- exact `provenance_pre_hash`.

It excludes:

- `layout_id`;
- `layout_hash`;
- any field embedding final `provenance.layout_hash`.

Build order is exact:

1. build `provenance_pre_hash`;
2. build `layout_hash_payload`;
3. compute `layout_hash = SHA-256(canonical_json(layout_hash_payload))`;
4. compute:

   ```text
   layout_id = UUIDv5(
     UUID_NAMESPACE_URL,
     "urn:hxforge:task021:tube-layout:v1:" + layout_hash
   )
   ```

5. construct final provenance as exactly `provenance_pre_hash` plus one new field,
   `layout_hash`;
6. construct final `TubeLayout`.

The kernel refuses to advance if any required field for the current step is
missing. This pipeline contains no self-reference.

### 12.8 Blocked-result identity

`blocked_result_hash` is SHA-256 over canonical JSON containing:

- output schema version;
- exact failure-stage ordinal from §9;
- complete normalized context available at that stage;
- canonical raw JSON for a failing field that could not be normalized, when
  canonical raw JSON exists;
- warnings eligible under §§11.5–11.8 in canonical warning order;
- complete blockers in §11.3 order;
- ordered deferred-capability array.

It must not be derived from a partial blocker key. It contains no partial layout,
position array, audit array or count result.

### 12.9 `UTubePairingPlan.pairing_plan_hash`

#### 12.9.1 Canonical leg

Each leg is exactly:

```json
{"u": "<canonical integer>", "v": "<canonical integer>"}
```

The actual JSON values are integers, not strings. Booleans and extra fields are
forbidden.

Within a pair, legs sort by numeric tuple `(u,v)`. The smaller tuple becomes
canonical `leg_a`; the larger becomes canonical `leg_b`. Equal legs block with
`STL_UTUBE_PAIRING_INVALID` and message key `u_tube_pair_self`.

#### 12.9.2 Exact canonical pair payload

Each canonical pair contains exactly:

- `pair_id`: non-empty string;
- `leg_a`: canonical leg;
- `leg_b`: canonical leg;
- `evidence_refs`: pair-level sorted Unicode array, duplicate-free.

No other pair field enters the hash. Pair IDs must be globally unique.

Canonical pairs sort by:

```text
(
  leg_a.u,
  leg_a.v,
  leg_b.u,
  leg_b.v,
  pair_id
)
```

Numeric fields use integer order and `pair_id` uses Unicode code-point order.
Input pair order and input leg order never affect the hash.

#### 12.9.3 Exact plan payload

`pairing_plan_hash_payload` contains exactly:

- `schema_version`: exact `task021.u-tube-pairing.v1`;
- `pairs`: canonical pair array;
- `plan_evidence_refs`: plan-level sorted Unicode array, duplicate-free.

It excludes `pairing_plan_hash` itself and excludes every field not listed above.

```text
pairing_plan_hash = SHA-256(canonical_json(pairing_plan_hash_payload))
```

#### 12.9.4 Mutually exclusive defect mapping

All structural defects use `STL_UTUBE_PAIRING_INVALID` with one exact message key:

- `u_tube_pair_raw_shape_invalid`: raw plan/pair field shape or type invalid;
- `u_tube_pair_leg_normalization_invalid`: a leg cannot normalize to exact `{u,v}`;
- `u_tube_pair_duplicate_id`: pair ID occurs more than once;
- `u_tube_pair_self`: the two normalized legs are equal;
- `u_tube_pair_unknown_leg`: a referenced leg is not an accepted position;
- `u_tube_pair_leg_reused`: accepted-leg occurrence count is greater than `1`;
- `u_tube_pair_missing_coverage`: accepted-leg occurrence count is exactly `0`.

A missing leg is never labeled reused. If several disjoint defects exist in the
same pairing-validation stage, retain all complete blockers in §11.3 order.

Hash mismatch after structurally valid normalization uses
`STL_UTUBE_PAIRING_HASH_MISMATCH`.

#### 12.9.5 Binding validation order

1. raw plan and pair shape/type validation;
2. leg normalization;
3. duplicate-ID and self-pair checks;
4. unknown-leg checks;
5. occurrence-count calculation;
6. reused-leg checks (`count > 1`);
7. missing-coverage checks (`count == 0`);
8. canonical leg and pair construction;
9. canonical pair ordering;
10. exact payload assembly;
11. hash recomputation;
12. supplied-vs-recomputed hash comparison.

Only after all stages succeed does the complete normalized pairing plan,
including `pairing_plan_hash`, enter `request_hash`.

## 13. Provenance contract

The final valid provenance object is the exact §12.6 projection plus only
`layout_hash`. It records both upstream artifact hashes and TASK-021 snapshot
hashes as distinct, non-substitutable identities.

TASK-021 creates no new source claim. It records approved supplied sources and
the deterministic transformation performed.

## 14. Standards and licensing boundary

TASK-021 inherits TASK-012 without modification. The repository and public
artifacts must not contain copied restricted standards tables, compatibility
matrices, clauses, figures, formula images or vendor-proprietary data.

Permitted content is limited to:

- source pointers;
- approved evidence references;
- permitted evaluated rule artifacts;
- internal generic mathematical lattice rules carrying `NO_STANDARD_CLAIM`.

TASK-021 acceptance is not certification or legal compliance.

## 15. Future implementation architecture

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

Later approved adapters may add:

- `rule_pack_adapter.py`;
- `geometry_adapter.py`.

The deterministic core remains pure and performs no I/O.

## 16. Implementation slicing

### 16.1 Slice A — deterministic core

A future Slice A may implement only:

- exact immutable models and schemas;
- TASK-020 identity verification;
- snapshot validation and TASK-021 snapshot hashes;
- Decimal lattice enumeration and geometric predicates;
- exclusion audit and overlap semantics;
- straight and U-tube count semantics;
- U-tube pairing validation and hash;
- canonical request, position, layout and blocked identities;
- deterministic warnings, blockers, provenance and deferred capabilities;
- synthetic mathematical tests.

### 16.2 Slice B — source adapters

A future Slice B may implement approved source adapters only after Slice A merge
and runtime authority reverification.

### 16.3 Excluded slices

Shell diameter, pass assignment, baffles, U-bend geometry, rating, pressure drop,
mechanical checks, materials, mass, cost, optimization, API, report and Golden
integration are not TASK-021 slices.

## 17. Maximum future allowlist

A later implementation authorization may name an exact subset of:

```text
src/hexagent/exchangers/shell_tube/tube_layout/**
tests/exchangers/shell_tube/tube_layout/**
tests/fixtures/task021/**
ci-shard-manifest.yml
```

Existing TASK-020 production and test files are not included unless a later
explicit amendment names exact files and source authority.

## 18. Frozen future test expectations

A future implementation must prove at least:

1. exact top-level and nested field sets;
2. raw types before coercion and boolean rejection for integer fields;
3. canonical JSON value-domain rejection;
4. duplicate-free arrays block rather than silently deduplicate;
5. complete TASK-020 configuration identity verification;
6. geometry snapshot hash recomputation;
7. layout-rule snapshot hash recomputation;
8. upstream hashes are preserved but not recomputed by the core;
9. authority-mode match and rule-pack identity requirements;
10. internal-generic `NO_STANDARD_CLAIM` behavior;
11. deterministic square enumeration;
12. deterministic triangular enumeration;
13. inverse-basis regression candidate `u=-57,v=115` is included;
14. non-invertible basis blocks;
15. candidate-capacity overflow blocks before generation;
16. origin and axis modes are deterministic and not auto-ranked;
17. envelope boundary equality is accepted;
18. circle exclusion equality is rejected;
19. rectangle closest-distance equality is rejected;
20. exclusion-zone input order does not affect request/layout hash;
21. exclusion audit is sorted by zone ID;
22. multi-zone overlap counts once globally and once per matching zone;
23. zero-hit zones remain in the audit;
24. duplicate zone IDs block;
25. quantization collisions block;
26. position ordering and UUID identity are stable;
27. fixed-tubesheet count equals hole count;
28. floating-head count equals hole count;
29. U-tube plan is required only for U-tube;
30. every accepted U-tube leg is covered exactly once;
31. reused and missing coverage message keys are mutually exclusive;
32. canonical pair payload includes pair-level evidence refs;
33. pair and plan input ordering does not affect pairing hash;
34. pairing-plan hash excludes itself;
35. warning triggers, negative triggers and exact five-field payloads are stable;
36. blocked-result warning suppression follows validation stage;
37. warning ordering is stable;
38. blocker ordering is stable for multiple blockers;
39. blocker details and evidence are retained in blocked-result hash;
40. deferred-capability order is exact;
41. request hash covers every computation-authority field;
42. `provenance_pre_hash` includes both snapshot hashes and canonical warnings;
43. `provenance_pre_hash` excludes layout ID and layout hash;
44. layout hash payload excludes layout ID and layout hash;
45. final provenance equals pre-hash projection plus only layout hash;
46. layout identity is stable across host, locale and process changes;
47. blocked identity is stable across input ordering differences;
48. valid layout has empty blockers and null blocked hash;
49. blocked result has no partial layout;
50. legacy upstream-hash mismatch aliases are never emitted;
51. no shell-diameter output exists;
52. placement envelope is never labeled shell/bundle/baffle diameter;
53. no filesystem, database or network call occurs in the core;
54. restricted standard content is absent;
55. TASK-019 Amendment 002-K remains separate;
56. TASK-022 through TASK-039 remain unallocated.

Synthetic mathematical fixtures are not engineering Goldens.

## 19. CI expectations

A future implementation PR must pass:

- Ruff lint;
- Ruff format check;
- mypy;
- focused TASK-021 tests;
- existing TASK-020 tests unchanged;
- architecture tests;
- global collection for supported Python versions;
- merge-ref collection;
- manifest verification;
- complete exact-head CI.

This design PR itself must preserve exactly one changed repository file and pass
its exact-head CI before any Ready authorization can be considered.

## 20. Explicit non-actions

This design does not authorize:

- production code, tests, fixtures, workflows, dependencies, lockfiles or CI
  manifest mutation;
- implementation Issue, branch, commit or PR;
- shell, bundle or baffle diameter calculation;
- shell-to-bundle clearance;
- pass membership or flow-path design;
- rating, Kern, Bell–Delaware or pressure-drop methods;
- mechanical, material, mass, cost or optimization work;
- API, persistence, CLI, report or Golden integration;
- copied restricted standards content;
- mutation of TASK-001 through TASK-020;
- import of TASK-019 Amendment 002-K scope;
- allocation of TASK-022 through TASK-039;
- Ready, merge, Issue close, review dismissal, thread resolution or branch
  deletion without separate Charles authorization.

## 21. Review acceptance

The design is eligible for personal Ready review only when:

- exactly this file is changed;
- the PR remains Draft until separately authorized;
- exact-head CI is completed / success;
- shell diameter remains deferred and unallocated;
- every source gap fails closed;
- exact field sets, array order and duplicate behavior are frozen;
- exclusion overlap and audit semantics are deterministic;
- warning and blocker payloads and order are deterministic;
- the blocker closed set has no duplicate or contradictory active codes;
- final provenance is constructible from the frozen hash pipeline;
- U-tube pair payload and defect mapping are unambiguous;
- TASK-019 Amendment 002-K remains separate;
- TASK-022 through TASK-039 remain unallocated.

CI success alone does not authorize Ready or merge.

## 22. Closeout

Issue #137 remains open while this design PR is Draft or unmerged. After merge
and successful exact-merge-SHA main CI, Issue #137 may close only under separate
Charles authorization.

Implementation remains unauthorized after design merge until an exact slice and
exact file subset are separately authorized.

```text
TASK021_DESIGN_CORRECTIVE_ROUND_3_EXACT_CONTRACT_RESTORED
EXACT_ONE_FILE_BOUNDARY
SHELL_DIAMETER_DEFERRED_UNALLOCATED
TASK019_AMENDMENT_002K_AUTHORITY_PRESERVED
TASK022_THROUGH_TASK039_UNALLOCATED
IMPLEMENTATION_NOT_AUTHORIZED
READY_NOT_AUTHORIZED
MERGE_NOT_AUTHORIZED
```
