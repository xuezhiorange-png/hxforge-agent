# TASK-021 — Shell-and-Tube Tube Layout and Tube Count Foundation

> Design contract for the second M3 shell-and-tube capability.
> TASK-021 consumes a valid TASK-020 shell-and-tube configuration and produces
> a deterministic, authority-bound two-dimensional tube layout and tube count.
> It does not calculate shell diameter, baffles, thermal rating, pressure drop,
> mechanical adequacy, materials, cost, optimization, API output, reports, or
> engineering Golden values.

## 1. Authority, status and authoring boundary

| Field | Value |
|---|---|
| Authorizing Issue | #137 — `[TASK-021][source-definition] Define tube-layout and tube-count foundation` |
| Allocation authorization | Issue #137 comment `4953356685` |
| One-file authoring authorization | Issue #137 comment `4953386614` |
| Frozen task allocation | `TASK-021 = Shell-and-Tube Tube Layout and Tube Count Foundation` |
| Explicit deferred boundary | Shell diameter remains deferred and unallocated |
| Design branch | `docs/task-021-tube-layout-count-design` |
| Design file | `docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md` |
| Allowed repository paths in this authoring round | This design file only |
| Authoring base | `main` at `9fd0969b8b512c6b631d122f60057df3062fc416` |
| Base CI evidence | main-push run `29214404112`, completed / success against the exact base SHA |
| Direct predecessor | TASK-020 — Shell-and-Tube Configuration Schema Foundation |
| Licensing authority | TASK-012 — Standards rule-pack and license boundary |
| Geometry-contract reference | TASK-016 — Approved Tube, Pipe and Hairpin Geometry Catalog Design Contract |
| Product authority | `docs/MASTER_DEVELOPMENT_SPEC.md`, especially §§2, 7, 8.2 and 9 |
| Design status | PROPOSED until this design PR is reviewed and merged |
| Implementation status | NOT AUTHORIZED |
| TASK-022 through TASK-039 | UNALLOCATED |

This authoring round may create one design commit and one Draft PR. It does not
authorize implementation, a Ready transition, merge, Issue closure, backlog
mutation, test or fixture mutation, CI-manifest mutation, workflow mutation,
review dismissal, review-thread resolution, branch deletion, or allocation of
any later M3 task.

## 2. Exact TASK-021 allocation

TASK-021 owns **Shell-and-Tube Tube Layout and Tube Count Foundation**.

The capability is deliberately narrower than a shell-and-tube geometry,
sizing, or rating engine. It owns:

1. consumption of one valid TASK-020 `ShellAndTubeConfiguration`;
2. consumption of explicit, immutable, approved geometry-authority snapshots;
3. deterministic enumeration of tube-center positions inside a caller-supplied
   placement envelope;
4. deterministic application of explicit exclusion zones;
5. deterministic tube-hole and physical-tube counting;
6. construction-family-specific count semantics for fixed-tubesheet, U-tube,
   and floating-head configurations;
7. canonical serialization, content hashing, deterministic identity, warnings,
   blockers, provenance and audit summaries;
8. explicit `NOT_COMPUTABLE` declarations for every later capability.

TASK-021 does not select a shell diameter, derive a shell diameter, infer a
shell-to-bundle clearance, or claim that the caller-supplied placement envelope
is a shell inside diameter. The field name frozen by this contract is
`tube_center_envelope_diameter_m`; the names `shell_diameter`,
`shell_inside_diameter`, `bundle_diameter` and `baffle_diameter` are not
TASK-021 outputs.

## 3. Source-of-truth inventory

### 3.1 Binding repository authority

TASK-021 is derived from the following committed authorities:

- `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md` and the current
  `hexagent.exchangers.shell_tube` implementation. TASK-020 supplies the
  validated configuration identity, construction family, orientation,
  shell-pass count, tube-pass count, authority binding and case authority.
- `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md`. Every external,
  derived, internal, user-provided or vendor-supplied layout rule remains bound
  by TASK-012 source-class, approval, provenance and license rules.
- `docs/tasks/TASK-016-approved-geometry-catalog.md`. TASK-016 defines approved
  tube-record semantics, SI dimensional authority, deterministic record hashes,
  source binding and approved-only consumption. TASK-021 treats that contract
  as a shape and governance reference only; it does not assume a TASK-016
  runtime implementation exists.
- `docs/MASTER_DEVELOPMENT_SPEC.md`. The product sequence requires candidate
  geometry generation before rating, and the shell-and-tube first phase names
  tube count and tube layout before later advanced methods.
- Issue #137 and its authorization comments, which freeze the task identity and
  the shell-diameter deferral.

### 3.2 Present runtime capability

The current repository contains a TASK-020 package that can produce a stable
`ShellAndTubeConfiguration` carrying:

- `configuration_id` and `configuration_hash`;
- `construction_family`;
- `orientation`;
- `shell_pass_count` and `tube_pass_count`;
- component tokens;
- case authority;
- configuration authority binding;
- warnings, blockers and deferred-capability declarations.

TASK-020 intentionally carries no tube diameter, pitch, tube coordinates,
shell diameter, baffle geometry or engineering-performance result.

### 3.3 Required capabilities currently absent

The following must not be simulated or silently invented:

- an approved runtime shell-and-tube geometry catalog;
- approved tube-layout rule-pack content;
- licensed external-standard layout tables or compatibility matrices;
- shell-diameter or bundle-to-shell-clearance methods;
- baffle geometry;
- tube-pass partition assignment algorithms;
- U-bend design geometry;
- thermal rating, Kern screening, Bell–Delaware, leakage or bypass corrections;
- pressure-drop decomposition;
- vibration, thermal expansion or mechanical checks;
- shell-and-tube material, mass, cost or optimization models;
- public API, report and engineering Golden integration.

TASK-021 resolves the missing-runtime-source problem by consuming immutable,
caller-supplied authority snapshots. It performs no filesystem walk, catalog
scan, database lookup, network lookup or hidden default substitution.

## 4. Frozen design decisions

### 4.1 Upstream configuration decision

The request must carry the complete valid TASK-020
`ShellAndTubeConfiguration`. A configuration ID or hash by itself is not a
sufficient input. TASK-021 performs no persistence lookup and does not rebuild
TASK-020 configuration semantics.

The future implementation must verify that:

- `equipment_family == SHELL_AND_TUBE`;
- the supplied object has no TASK-020 blockers;
- the complete configuration canonical payload reproduces the supplied
  `configuration_hash` under the TASK-020 canonical helper;
- the TASK-020 UUID helper reproduces `configuration_id` from that hash.

Any mismatch blocks the request. A partial projection must not be accepted as a
configuration authority substitute.

### 4.2 Geometry-source decision

TASK-021 accepts one `ApprovedTubeGeometrySnapshot`. The snapshot is a complete,
immutable projection of a TASK-016-conformant approved tube record and includes
its source binding and record hash. TASK-021 does not load a TASK-016 catalog at
runtime.

A future adapter may map a real TASK-016 runtime object into this snapshot only
after a separately authorized round verifies that the runtime contract exists.
Until then, the snapshot is supplied by the caller and is validated fail-closed.

### 4.3 Layout-rule decision

TASK-021 accepts one evaluated `LayoutRuleAuthoritySnapshot`. The snapshot is
not raw standard text and is not an unreviewed user preference. It is the exact
approved computation authority for the requested layout.

The frozen profile identifier is:

```text
hxforge.shell_tube.tube_layout.v1
```

A TASK-020 configuration rule is not implicitly a TASK-021 layout rule. A rule
must explicitly declare the TASK-021 profile identifier before its values may
be consumed by TASK-021.

### 4.4 No runtime lookup decision

The TASK-021 deterministic kernel must not:

- call the filesystem;
- scan a catalog directory;
- query a database;
- call a network service;
- choose a default tube geometry;
- infer a pitch from tube diameter;
- infer a pattern from a TEMA token;
- infer an exclusion lane from tube-pass count;
- infer U-tube pairings;
- infer shell diameter from the placement envelope.

All computation-authority values must be present in the request or in an
explicit approved snapshot.

### 4.5 Initial pattern-family decision

The closed v1 pattern set is:

- `SQUARE`;
- `TRIANGULAR`.

Rotated-square, rotated-triangular, concentric-ring, radial, vendor-proprietary
and arbitrary custom patterns are deferred. They require a separately
authorized TASK-021 design amendment or a later task allocation.

The names above describe generic mathematical lattices only. They make no TEMA,
API, ISO, vendor or legal-compliance claim.

### 4.6 Placement-envelope decision

TASK-021 v1 accepts one circular tube-center placement envelope. The envelope is
a caller-supplied finite geometric constraint. It is not calculated by
TASK-021 and is not a shell-diameter result.

A tube position is accepted only if the complete tube disk, plus the approved
edge clearance, lies inside the envelope.

### 4.7 Pass-partition decision

TASK-021 does not assign individual tubes to tube passes and does not design
partition plates, nozzles or flow paths. Explicit geometric lanes may be
reserved through exclusion zones. The TASK-020 `tube_pass_count` is preserved
in provenance and validated against the authority snapshot, but it is not used
to fabricate pass membership.

The output therefore carries:

```text
PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE
```

### 4.8 Construction-family decision

- `FIXED_TUBESHEET`: each accepted tube-hole position represents one straight
  physical tube.
- `FLOATING_HEAD`: each accepted tube-hole position represents one straight
  physical tube. No floating-head clearance or mechanical geometry is inferred.
- `U_TUBE`: each physical tube has two tubesheet-leg positions. A complete,
  explicit `UTubePairingPlan` is required. TASK-021 validates and counts the
  pairs but does not design the U-bend radius or bend shape.

A U-tube request without a complete valid pairing plan is blocked, not partially
returned.

### 4.9 No optimization decision

TASK-021 does not search origin choices, pattern choices, pitch values, envelope
sizes or exclusion-zone variants to maximize tube count. The caller supplies one
explicit request. `origin_mode` and `axis_orientation` are computation authority
and are included in the request hash.

## 5. Dependency contract

### 5.1 Direct dependencies

| Dependency | Use |
|---|---|
| TASK-002 SI discipline | all computation-authority dimensions use explicit SI field names and canonical decimal strings |
| TASK-004 structured errors and provenance | deterministic warning/blocker and provenance conventions |
| TASK-012 design and implementation | source-class, approval, license and rule-pack governance for layout-rule authority |
| TASK-014 | case authority is inherited through the complete TASK-020 configuration; TASK-021 performs no persistence lookup |
| TASK-015A | deterministic test and CI execution governance for a future implementation |
| TASK-020 design and implementation | complete validated shell-and-tube configuration and canonical identity |
| TASK-016 design contract | approved tube-record shape and source-binding reference only |

### 5.2 Reference-only dependencies

TASK-007 through TASK-010 and TASK-017 through TASK-019 demonstrate deterministic
engineering, material, cost, report and Golden patterns but their double-pipe
results are not shell-and-tube computation authority. TASK-019 Amendment 002-K
remains an M2 cost-stack follow-up and must not be imported.

### 5.3 Explicit dependency prohibitions

TASK-021 must not:

- mutate TASK-001 through TASK-020 frozen contracts;
- import double-pipe geometry as shell-and-tube layout data;
- treat TASK-016 hairpin geometry as a shell-and-tube bundle;
- reuse TASK-017 material or mechanical conclusions;
- reuse TASK-018 cost results;
- consume TASK-019 fixture bridges or expected-output values;
- interpret the caller-supplied placement envelope as later shell geometry.

## 6. Domain model

All value objects are immutable and have exact field sets. Unknown fields are
blockers. Input validation occurs before coercion; strings, integers, arrays and
objects must not be silently converted from other types.

### 6.1 Decimal SI representation

Every unit-bearing request value is a canonical base-10 decimal string. Binary
floating-point values are forbidden at the public TASK-021 boundary.

Examples of valid lexical shapes:

```text
"0"
"0.01905"
"1.250000000000"
```

The value must be finite, must not use exponent notation, must not have a leading
plus sign, and must not contain leading or trailing whitespace. Negative zero
normalizes to `0` and is rejected when the field requires a positive value.

The frozen internal Decimal context is:

- precision: 50 decimal digits;
- rounding: `ROUND_HALF_EVEN`;
- coordinate quantum: `0.000000000001` m (`1e-12` m);
- canonical zero: `0`.

### 6.2 `ApprovedTubeGeometrySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `geometry_id` | string | non-empty stable TASK-016-style identity |
| `geometry_type` | string | exact value `tube` |
| `revision` | string | non-empty |
| `approval_state` | string | exact value `approved` |
| `outer_diameter_m` | decimal string | positive |
| `inner_diameter_m` | decimal string | positive and smaller than OD |
| `wall_thickness_m` | decimal string | positive and algebraically consistent |
| `record_hash` | string | lowercase 64-character SHA-256 hex |
| `source_binding` | object | complete §6.3 shape |

The snapshot carries no material grade, allowable stress, corrosion allowance,
pressure rating, fouling value, vendor availability, procurement state or cost.

The algebraic invariant is:

```text
wall_thickness_m = (outer_diameter_m - inner_diameter_m) / 2
```

The equality is evaluated after Decimal parsing and quantization to the frozen
coordinate quantum. A mismatch is a blocker.

### 6.3 `SourceBindingSnapshot`

Exact fields:

- `source_id: str`;
- `source_type: str`;
- `source_revision: str`;
- `source_location: str`;
- `evidence_ref: str`;
- `approved_by: str`;
- `approved_at: str`.

Every field is required and non-empty. `approved_at` is provenance metadata; it
is serialized as the supplied normalized string and is not parsed using host
locale or local timezone rules.

### 6.4 `LayoutRuleAuthoritySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `profile_id` | string | exact `hxforge.shell_tube.tube_layout.v1` |
| `authority_mode` | enum | `INTERNAL_GENERIC` or `APPROVED_RULE_PACK`; must match TASK-020 configuration mode |
| `rule_id` | string | non-empty |
| `rule_version` | string | non-empty |
| `rule_artifact_canonical_hash` | string | lowercase SHA-256 hex |
| `source_class` | TASK-012 enum string | recognized source class |
| `license_evidence` | JSON value | required, canonicalizable |
| `approval_status` | string | exact `approved` |
| `provenance_edge_ids` | array of strings | sorted and duplicate-free after validation |
| `evidence_refs` | array of strings | sorted and duplicate-free after validation |
| `rule_pack_identity` | object or null | required for `APPROVED_RULE_PACK`; null for `INTERNAL_GENERIC` |
| `pattern_family` | enum | `SQUARE` or `TRIANGULAR` |
| `pitch_m` | decimal string | positive and greater than or equal to tube OD |
| `edge_clearance_m` | decimal string | non-negative |
| `allowed_origin_modes` | array | non-empty closed subset of §6.8 |
| `allowed_axis_orientations` | array | non-empty closed subset of §6.9 |
| `allowed_exclusion_zone_types` | array | closed subset of §6.11 |
| `maximum_candidate_positions` | integer | `1 <= value <= 100000` |

For `INTERNAL_GENERIC`, `source_class` must be
`INTERNAL_ENGINEERING_RULE`, `rule_pack_identity` must be null, and the result
must retain `NO_STANDARD_CLAIM` semantics.

For `APPROVED_RULE_PACK`, `rule_pack_identity` must carry the exact TASK-012
identity triple and the selected rule must satisfy TASK-012 approval, license,
canonical-hash and provenance requirements. TASK-021 must not copy or expose the
body of a restricted standard.

### 6.5 `RulePackIdentitySnapshot`

Exact fields:

- `rule_pack_id: str`;
- `rule_pack_version: str`;
- `rule_pack_canonical_hash: lowercase SHA-256 hex`.

This object identifies the pack that produced the evaluated layout rule. It is
not permission to reinterpret TASK-020 configuration-rule values as layout
values.

### 6.6 `CircularTubeCenterEnvelope`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact `task021.circular-envelope.v1` |
| `tube_center_envelope_diameter_m` | decimal string | positive |
| `evidence_refs` | array of strings | required and non-empty |

The coordinate origin is fixed at `(0, 0)`. The envelope has no translated
center in v1. The diameter is an externally supplied layout constraint and is
not a TASK-021 shell or bundle result.

### 6.7 `TubeLayoutRequest`

Exact fields:

| Field | Type | Requirement |
|---|---|---|
| `schema_version` | string | exact `task021.tube-layout-request.v1` |
| `configuration` | complete TASK-020 `ShellAndTubeConfiguration` | required |
| `tube_geometry` | `ApprovedTubeGeometrySnapshot` | required |
| `layout_rule_authority` | `LayoutRuleAuthoritySnapshot` | required |
| `placement_envelope` | `CircularTubeCenterEnvelope` | required |
| `origin_mode` | enum | §6.8; must be allowed by authority snapshot |
| `axis_orientation` | enum | §6.9; must be allowed by authority snapshot |
| `exclusion_zones` | array of `ExclusionZone` | required; may be empty |
| `u_tube_pairing_plan` | `UTubePairingPlan` or null | required for U-tube; null otherwise |
| `evidence_refs` | array of strings | required; sorted, duplicate-free |

### 6.8 `OriginMode`

Closed set:

- `CENTER_ON_LATTICE_POINT`;
- `CENTER_ON_PRIMITIVE_CELL`.

TASK-021 does not test both modes and choose the larger count. The caller chooses
one authorized mode.

### 6.9 `AxisOrientation`

Closed set:

- `PRIMARY_AXIS_X`;
- `PRIMARY_AXIS_Y`.

This is a mathematical lattice orientation only. It is not equipment
orientation; equipment orientation remains the inherited TASK-020 field.

### 6.10 `LatticeIndex`

A lattice position is identified by two signed integers:

- `u: int`;
- `v: int`.

Integer indices are the pre-quantization identity of a candidate position.
Coordinates must not be used as the sole identity because canonical coordinate
quantization is a representation step.

### 6.11 `ExclusionZone`

Closed `zone_type` set:

- `AXIS_ALIGNED_RECTANGLE`;
- `CIRCLE`.

Common required fields:

- `zone_id: str` — unique after normalization;
- `zone_type: enum`;
- `center_x_m: decimal string`;
- `center_y_m: decimal string`;
- `clearance_m: non-negative decimal string`;
- `reason_code: str` — non-empty opaque audit code;
- `evidence_refs: array[str]` — required and non-empty.

Rectangle-only fields:

- `width_m: positive decimal string`;
- `height_m: positive decimal string`;
- `radius_m: null`.

Circle-only fields:

- `radius_m: positive decimal string`;
- `width_m: null`;
- `height_m: null`.

Arbitrary polygons, splines, rotated rectangles and vendor-proprietary zone
shapes are out of scope for v1.

### 6.12 `UTubePairingPlan`

Exact fields:

- `schema_version: str` — exact `task021.u-tube-pairing.v1`;
- `pairs: array[UTubePair]` — non-empty;
- `evidence_refs: array[str]` — required and non-empty;
- `pairing_plan_hash: lowercase SHA-256 hex`.

Each `UTubePair` contains:

- `pair_id: str`;
- `leg_a: LatticeIndex`;
- `leg_b: LatticeIndex`;
- `evidence_refs: array[str]`.

A pair must reference two distinct accepted positions. Every accepted position
must appear in exactly one pair. Pairing order and leg order are canonicalized;
no accepted position may be omitted or repeated.

TASK-021 does not compute U-bend radius, bend length, bend stress, minimum bend
spacing or fabrication feasibility.

## 7. Lattice construction

### 7.1 Mathematical constants

The layout kernel uses Decimal arithmetic. The only irrational constant required
by v1 is the internally derived mathematical constant:

```text
SQRT_3 = 1.7320508075688772935274463415058723669428052538104
```

This is a mathematical constant, not standards content. It is parsed under the
frozen Decimal context and is never read from an external rule pack.

### 7.2 Basis vectors

Let `p` be the approved `pitch_m`.

For `SQUARE` with `PRIMARY_AXIS_X`:

```text
a = (p, 0)
b = (0, p)
```

For `TRIANGULAR` with `PRIMARY_AXIS_X`:

```text
a = (p, 0)
b = (p / 2, p * SQRT_3 / 2)
```

For `PRIMARY_AXIS_Y`, the x and y components of both basis vectors are swapped.

### 7.3 Origin offset

For `CENTER_ON_LATTICE_POINT`:

```text
offset = (0, 0)
```

For `CENTER_ON_PRIMITIVE_CELL`:

```text
offset = (a + b) / 2
```

### 7.4 Candidate coordinate

For integer lattice index `(u, v)`:

```text
raw_coordinate = u * a + v * b + offset
```

Both coordinates are quantized to `1e-12 m` with `ROUND_HALF_EVEN`. The
canonical coordinate strings contain no exponent notation and no unnecessary
trailing zeros.

### 7.5 Finite enumeration bound

Define:

- `R = tube_center_envelope_diameter_m / 2`;
- `r_tube = outer_diameter_m / 2`;
- `c_edge = edge_clearance_m`;
- `rho = R - r_tube - c_edge`.

If `rho <= 0`, the request is blocked before enumeration.

For the frozen v1 square and triangular bases, the minimum lattice spacing is
`pitch_m`. Let `offset_norm_upper = abs(offset_x) + abs(offset_y)` and:

```text
N = ceil((rho + offset_norm_upper) / pitch_m) + 2
```

The candidate index domain is the complete Cartesian product:

```text
u in [-N, N]
v in [-N, N]
```

Before generating coordinates, the kernel computes `(2N + 1)^2`. If that value
exceeds `maximum_candidate_positions`, the request is blocked. Truncating the
index domain or returning a partial result is forbidden.

### 7.6 Envelope acceptance

A tube disk fits the circular placement envelope when:

```text
x^2 + y^2 <= rho^2
```

All values in the comparison use unrounded Decimal working values under the
frozen context. Quantized coordinates are output representation only. Equality
is accepted.

### 7.7 Exclusion-zone intersection

A candidate that fits the envelope is rejected when its tube disk intersects
any exclusion zone after adding the zone's `clearance_m`.

For a circle zone, reject when:

```text
(x - zone_center_x)^2 + (y - zone_center_y)^2
<= (zone_radius + r_tube + zone_clearance)^2
```

For an axis-aligned rectangle, determine the closest point on the closed
rectangle to `(x, y)`. Reject when the squared distance to that closest point is
less than or equal to:

```text
(r_tube + zone_clearance)^2
```

A candidate rejected by multiple zones is counted once in the total rejection
count and once under every matching zone's audit count. Zone evaluation order
must not affect the accepted layout.

### 7.8 Duplicate-coordinate guard

After quantization, no two distinct lattice indices may produce the same
canonical coordinate pair. A collision blocks the complete request. The kernel
must not silently retain the first position or merge the candidates.

### 7.9 Position ordering

Accepted positions are sorted by the composite key:

```text
(y_m_decimal, x_m_decimal, u, v)
```

Decimal numerical order is used for the first two elements. String lexical order
must not be substituted for Decimal numerical order.

### 7.10 Position identity

The normalized request hash is calculated before position IDs. For each accepted
index:

```text
position_id = UUIDv5(
  UUID_NAMESPACE_URL,
  "urn:hxforge:task021:tube-position:v1:"
  + request_hash + ":" + signed_u + ":" + signed_v
)
```

No array position, object memory address, input order or coordinate-formatting
variant may enter the position ID.

## 8. Validation pipeline

The future implementation must execute the following stages in order and stop
at the end of a stage when blockers exist:

1. raw top-level mapping and exact-field validation;
2. raw type validation before any coercion;
3. schema-version validation;
4. complete TASK-020 configuration identity verification;
5. layout-authority mode, profile, approval, hash, license and provenance checks;
6. tube-geometry approval, source, hash and dimensional checks;
7. placement-envelope checks;
8. origin, axis and rule-authorization checks;
9. exclusion-zone exact-shape and duplicate-ID checks;
10. construction-family and U-tube-pairing prechecks;
11. finite enumeration-limit calculation;
12. lattice enumeration, envelope filtering and exclusion filtering;
13. duplicate-coordinate guard;
14. U-tube complete pairing validation, when applicable;
15. count calculation;
16. canonical warnings, audit summaries, provenance, hash and identity.

The implementation must preserve complete blocker objects. It must not reduce a
blocker to an incomplete lookup key and reconstruct it later.

## 9. Output contract

### 9.1 `TubePosition`

Exact fields:

- `position_id: UUID string`;
- `u: int`;
- `v: int`;
- `x_m: canonical decimal string`;
- `y_m: canonical decimal string`.

### 9.2 `ExclusionAudit`

Exact fields:

- `zone_id: str`;
- `rejected_position_count: int`;
- `reason_code: str`;
- `evidence_refs: sorted array[str]`.

The audit is sorted by `zone_id` in ascending Unicode code-point order.

### 9.3 `TubeLayout`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact `task021.tube-layout.v1` |
| `layout_id` | UUID string | §11 |
| `layout_hash` | lowercase SHA-256 hex | §11 |
| `request_hash` | lowercase SHA-256 hex | §11 |
| `task020_configuration_id` | string | copied from verified configuration |
| `task020_configuration_hash` | string | copied from verified configuration |
| `case_authority` | complete TASK-020 case authority | copied by reference |
| `construction_family` | enum | copied from verified configuration |
| `equipment_orientation` | enum | copied from verified configuration |
| `shell_pass_count` | integer | copied; no shell-pass geometry inferred |
| `tube_pass_count` | integer | copied; no pass membership inferred |
| `tube_geometry` | complete approved snapshot | canonicalized |
| `layout_rule_authority` | complete authority snapshot | canonicalized |
| `placement_envelope` | complete envelope | canonicalized |
| `origin_mode` | enum | normalized request value |
| `axis_orientation` | enum | normalized request value |
| `exclusion_zones` | canonical array | sorted by zone ID |
| `positions` | array of `TubePosition` | §7.9 order |
| `tube_hole_count` | integer | number of accepted positions |
| `physical_tube_count` | integer | straight count or U-tube pair count |
| `boundary_rejection_count` | integer | candidates outside envelope |
| `exclusion_rejection_count` | integer | unique candidates rejected by any zone |
| `exclusion_audit` | array | §9.2 order |
| `warnings` | array | complete five-field objects |
| `blockers` | array | empty for a valid layout |
| `deferred_capabilities` | array | closed §9.5 set |
| `provenance` | object | §12 |

### 9.4 `TubeLayoutValidationResult`

Exact fields:

- `status: VALID | BLOCKED`;
- `layout: TubeLayout | null`;
- `warnings: array[ErrorEntry]`;
- `blockers: array[ErrorEntry]`;
- `deferred_capabilities: array[str]`;
- `blocked_result_hash: lowercase SHA-256 hex | null`.

A blocked result carries no partial layout and no partial coordinate list.

### 9.5 Closed deferred-capability set

A valid TASK-021 result carries the following stable declarations:

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

These are capability declarations. No numeric placeholder or fabricated fallback
may accompany them.

## 10. Warning and blocker model

Every warning or blocker uses the complete TASK-004/TASK-020-compatible
five-field shape:

- `code: str`;
- `field_path: str | null`;
- `message_key: str`;
- `evidence_refs: sorted array[str]`;
- `details: canonical JSON object | null`.

`details` accepts only JSON null, booleans, integers, finite decimal strings,
strings, arrays of valid JSON values and objects with string keys. Unsupported
Python objects, sets, bytes, datetimes, Decimal objects at the serialization
boundary, NaN and Infinity are canonicalization blockers.

### 10.1 Closed blocker-code set

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
- `STL_LAYOUT_RULE_HASH_MISMATCH`;
- `STL_LAYOUT_RULE_LICENSE_BLOCKED`;
- `STL_LAYOUT_RULE_PROVENANCE_INCOMPLETE`;
- `STL_RULE_PACK_IDENTITY_MISSING`;
- `STL_RULE_PACK_IDENTITY_NOT_EXPECTED`;
- `STL_TUBE_GEOMETRY_MISSING`;
- `STL_TUBE_GEOMETRY_TYPE_INVALID`;
- `STL_TUBE_GEOMETRY_UNAPPROVED`;
- `STL_TUBE_GEOMETRY_SOURCE_INCOMPLETE`;
- `STL_TUBE_GEOMETRY_HASH_MISMATCH`;
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
- `STL_ENUMERATION_LIMIT_EXCEEDED`;
- `STL_COORDINATE_QUANTIZATION_COLLISION`;
- `STL_NO_TUBE_POSITIONS`;
- `STL_UTUBE_PAIRING_REQUIRED`;
- `STL_UTUBE_PAIRING_NOT_EXPECTED`;
- `STL_UTUBE_PAIRING_HASH_MISMATCH`;
- `STL_UTUBE_PAIRING_INVALID`;
- `STL_CANONICALIZATION_FAILED`.

No blocker in this set may be downgraded to a warning when the requested layout
cannot be reproduced safely.

### 10.2 Closed warning-code set

- `STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM`;
- `STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER`;
- `STL_PASS_PARTITION_ASSIGNMENT_DEFERRED`;
- `STL_UTUBE_BEND_GEOMETRY_DEFERRED`.

Warnings are deterministically sorted by the TASK-020 composite ordering rule:
`(code, field_path or "", message_key, canonical_details_hash)`.

## 11. Canonicalization, hashing and identity

### 11.1 Canonical JSON

Canonical JSON uses:

- UTF-8;
- lexicographically sorted object keys by Unicode code point;
- no insignificant whitespace;
- stable array order as frozen by this contract;
- canonical decimal strings, never binary floats;
- no NaN or Infinity;
- no host, locale, filesystem, process, timestamp-now or random values.

### 11.2 Normalized request hash

The request hash covers the complete normalized request, including:

- complete verified TASK-020 configuration authority and identity;
- complete tube-geometry snapshot;
- complete layout-rule authority snapshot;
- complete placement envelope;
- origin mode and axis orientation;
- canonical exclusion zones;
- complete U-tube pairing plan when present;
- sorted request evidence references;
- request schema version.

It excludes no computation-authority field.

### 11.3 Layout hash

The layout hash covers:

- output schema version;
- request hash;
- all accepted positions in canonical order, including position IDs and lattice
  indices;
- tube-hole and physical-tube counts;
- boundary and exclusion rejection counts;
- complete exclusion audit;
- complete warnings and empty blockers;
- complete deferred-capability set;
- complete provenance.

`layout_id` is:

```text
UUIDv5(
  UUID_NAMESPACE_URL,
  "urn:hxforge:task021:tube-layout:v1:" + layout_hash
)
```

### 11.4 Blocked-result identity

A blocked result hash covers the complete normalized context available at the
point of failure:

- raw request schema version;
- complete supplied TASK-020 configuration or its canonical raw mapping;
- complete supplied geometry and authority snapshots;
- complete envelope, zones and pairing plan;
- complete canonical blocker objects;
- output schema version.

It must not be derived from a three-field blocker key or a partial projection.

## 12. Provenance contract

The valid result provenance object contains:

- `task_id: "TASK-021"`;
- `design_contract_path`;
- `task020_configuration_id`;
- `task020_configuration_hash`;
- complete TASK-020 case authority;
- tube geometry ID, revision, record hash and source binding;
- layout rule profile, rule identity, rule artifact hash, source class, approval
  status, rule-pack identity when present, provenance edge IDs and evidence refs;
- envelope evidence refs;
- exclusion-zone evidence refs;
- U-tube pairing evidence refs when present;
- `software_version`;
- `git_commit` supplied by the calling application;
- `request_hash`;
- `layout_hash`;
- warnings and deferred-capability declarations.

TASK-021 does not generate a new source claim. It records the supplied approved
sources and the deterministic transformation it performed.

## 13. Standards and licensing boundary

TASK-021 inherits TASK-012 without modification.

The repository and public artifacts must not contain:

- copied TEMA, API, ASME, ISO or vendor tables;
- copied compatibility matrices;
- copied clause text, figures or formula images;
- restricted pitch-ratio or clearance tables without permitted source posture;
- a claim that a layout is certified, code-compliant or vendor-approved merely
  because the deterministic kernel accepted it.

Allowed authority forms are limited to TASK-012-governed artifacts and snapshots.
A restricted standard may be represented by bibliographic metadata and evidence
pointers. Computation values derived from restricted content must enter through a
permitted TASK-012 source class with approval and license evidence; TASK-021 core
must not contain the external body.

For `INTERNAL_GENERIC`, the output must state that no external-standard claim is
made. For `APPROVED_RULE_PACK`, the output may state only that the selected
layout rule was validated under its approved rule-pack authority; it must not
state legal compliance or certification.

## 14. Implementation architecture contract

A future implementation, if separately authorized, must live under:

```text
src/hexagent/exchangers/shell_tube/tube_layout/
```

The deterministic core remains pure and performs no I/O. Suggested module
separation, frozen as the maximum initial architecture, is:

- `models.py` — immutable exact-shape value objects and enums;
- `schema.py` — raw exact-field/type/decimal validation;
- `authority.py` — TASK-020 identity and authority-snapshot checks;
- `enumeration.py` — pure square/triangular lattice enumeration;
- `geometry.py` — pure envelope and exclusion intersection predicates;
- `pairing.py` — pure U-tube pairing validation;
- `canonical.py` — canonical JSON, hashes, UUIDv5 and ordering;
- `validation.py` — ordered fail-closed orchestration;
- `__init__.py` — explicit public exports only.

A later adapter slice may add:

- `rule_pack_adapter.py` — map a TASK-012-validated TASK-021 profile into a
  `LayoutRuleAuthoritySnapshot`;
- `geometry_adapter.py` — map an implemented TASK-016 approved tube record into
  an `ApprovedTubeGeometrySnapshot`.

Those adapters must not be authored until their exact upstream runtime contracts
are verified in the separately authorized implementation round.

## 15. Implementation slicing

### 15.1 Slice A — deterministic core

A future Slice A may implement:

- immutable models and closed enums;
- raw schema and Decimal validation;
- complete TASK-020 configuration identity verification;
- caller-supplied geometry and rule snapshot validation;
- square and triangular lattice generation;
- circular-envelope and exclusion-zone predicates;
- fixed-tubesheet and floating-head count semantics;
- U-tube pairing validation and count semantics;
- canonicalization, hashes, IDs, blockers, warnings and provenance;
- unit and property tests using synthetic mathematical fixtures.

Slice A must perform no filesystem, rule-pack or catalog loading.

### 15.2 Slice B — approved-source adapters

A future Slice B may be proposed only after Slice A is merged and after the round
re-verifies TASK-012 and TASK-016 runtime reality. It may implement the dedicated
TASK-021 rule-pack adapter and the optional approved tube-geometry adapter.

Slice A authorization does not authorize Slice B.

### 15.3 Deferred implementation slices

The following are not TASK-021 slices and require later task allocation or a
separate Charles-authorized amendment:

- shell-diameter calculation;
- pass membership and flow-path assignment;
- baffle geometry;
- rotated or custom layout families;
- U-bend geometry design;
- thermal/hydraulic rating;
- mechanical, material, cost, optimization, API, report or Golden integration.

## 16. Maximum future implementation allowlist

This design does not authorize implementation. A later implementation authority
must name its exact subset of the following maximum allowlist:

```text
src/hexagent/exchangers/shell_tube/tube_layout/__init__.py
src/hexagent/exchangers/shell_tube/tube_layout/models.py
src/hexagent/exchangers/shell_tube/tube_layout/schema.py
src/hexagent/exchangers/shell_tube/tube_layout/authority.py
src/hexagent/exchangers/shell_tube/tube_layout/enumeration.py
src/hexagent/exchangers/shell_tube/tube_layout/geometry.py
src/hexagent/exchangers/shell_tube/tube_layout/pairing.py
src/hexagent/exchangers/shell_tube/tube_layout/canonical.py
src/hexagent/exchangers/shell_tube/tube_layout/validation.py
src/hexagent/exchangers/shell_tube/tube_layout/rule_pack_adapter.py
src/hexagent/exchangers/shell_tube/tube_layout/geometry_adapter.py
tests/exchangers/shell_tube/tube_layout/**
tests/fixtures/task021/**
ci-shard-manifest.yml
```

A later round may narrow this list but must not expand it without a TASK-021
design amendment. Existing TASK-020 production and test files are not in the
allowlist and must not be mutated merely to make TASK-021 convenient.

## 17. Frozen test expectations

A future implementation must include tests that prove at least:

1. the exact raw request field set is enforced before coercion;
2. binary floats, exponent strings, NaN, Infinity and unsupported canonical
   values fail closed;
3. a valid complete TASK-020 configuration is accepted;
4. configuration hash or ID mismatch blocks the request;
5. a partial TASK-020 projection is rejected;
6. missing, unapproved, malformed or hash-mismatched tube geometry blocks;
7. TASK-016 source binding is complete and preserved;
8. TASK-020 and TASK-021 authority modes must match;
9. internal generic mode retains no-standard-claim behavior;
10. a TASK-020 configuration rule cannot be silently reused as a layout rule;
11. missing or invalid rule-pack identity blocks approved-rule-pack mode;
12. square-lattice enumeration is deterministic;
13. triangular-lattice enumeration is deterministic;
14. both origin modes are deterministic and are not auto-ranked;
15. both axis orientations are deterministic;
16. exact boundary equality is accepted;
17. a tube disk crossing the envelope boundary is rejected;
18. circle exclusion intersection is correct at strict and equality boundaries;
19. rectangle exclusion intersection is correct at strict and equality boundaries;
20. exclusion-zone input order does not affect the accepted layout or hash;
21. duplicate zone IDs block;
22. enumeration-limit overflow blocks before partial generation;
23. coordinate quantization collisions block;
24. zero accepted positions block;
25. fixed-tubesheet physical count equals tube-hole count;
26. floating-head physical count equals tube-hole count without inferring
    floating-head clearance;
27. U-tube pairing is required;
28. U-tube pairings must cover every accepted position exactly once;
29. U-tube leg reuse, omission, self-pairing or unknown index blocks;
30. U-tube physical count equals pairing count;
31. canonical position ordering is independent of generation order;
32. request, position, layout and blocked-result identities are stable;
33. any computation-authority change changes the appropriate hash;
34. non-semantic mapping-key order does not change a hash;
35. a valid output contains no shell-diameter field or value;
36. pass membership remains explicitly `NOT_COMPUTABLE`;
37. no filesystem, database or network call occurs in the core;
38. TASK-019 Amendment 002-K assets are not imported or mutated;
39. TASK-022 through TASK-039 remain unallocated;
40. frozen design boundaries are represented in architecture tests.

Synthetic mathematical fixtures may use small, internally authored Decimal
values. They are not engineering Golden values and must not claim external
standard authority.

## 18. CI expectations for a future implementation

A separately authorized implementation PR must pass:

- Ruff check and format validation;
- mypy for the new package and tests;
- all focused TASK-021 tests;
- existing TASK-020 tests unchanged;
- architecture/import-boundary tests;
- global test collection and the repository shard manifest verifier;
- complete repository CI at the exact PR head.

Any `ci-shard-manifest.yml` mutation requires explicit inclusion in that later
implementation authorization and must contain only TASK-021 test nodes needed by
the repository's deterministic sharding contract.

## 19. Explicit non-actions

This design contract does not authorize:

- production code, tests, fixtures, workflows, CI manifest, dependencies or
  lockfile mutation;
- a TASK-021 implementation Issue, branch, commit or PR;
- shell-diameter, bundle-diameter or baffle-diameter calculation;
- pass membership, partition-plate or nozzle design;
- TEMA, Kern, Bell–Delaware, pressure-drop or thermal-expansion methods;
- U-bend geometry or fabrication checks;
- material selection, mass, mechanical checks, cost or optimization;
- API, persistence, CLI, report or engineering Golden integration;
- copied or reconstructed restricted standards or vendor content;
- runtime catalog scans, filesystem fallbacks or database/network lookup;
- mutation of TASK-001 through TASK-020 frozen contracts;
- import of TASK-019 Amendment 002-K cost-stack scope;
- TASK-022 through TASK-039 allocation;
- Ready, merge, Issue close, review dismissal, thread resolution or branch
  deletion without separate Charles authorization.

## 20. Design review acceptance criteria

The TASK-021 design PR is eligible for personal review when:

- the PR changes exactly this one design file;
- the branch is based on the recorded authoring base or any drift is explicitly
  reviewed before additional mutation;
- the task allocation and shell-diameter deferral match Issue #137;
- all source gaps are fail-closed rather than filled with assumptions;
- no restricted standard content or unsupported numerical table is embedded;
- input, output, authority, construction-family, enumeration, identity,
  blocker, provenance, implementation-slice and test contracts are complete;
- TASK-019 Amendment 002-K remains separate M2 authority;
- TASK-022 through TASK-039 remain unallocated;
- the PR remains Draft until separately authorized Ready transition.

The design becomes frozen only after separate personal review, separate Ready
authorization, separate merge authorization and successful post-merge main CI.
No step implies the next.

## 21. Closeout rule

Issue #137 remains open while the design PR is Draft or unmerged. After the
design PR is merged and its exact merge SHA has successful main-push CI, Issue
#137 may close only under separate Charles authorization.

Implementation remains unauthorized after design merge until Charles separately
opens and authorizes the exact implementation slice and allowed-file subset.
