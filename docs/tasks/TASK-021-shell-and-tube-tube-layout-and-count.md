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
| `record_hash` | string | lowercase 64-character SHA-256 hex; **upstream artifact hash** — TASK-021 core does **not** recalculate this value because the core does not own the upstream record body |
| `snapshot_hash` | lowercase 64-character SHA-256 hex | TASK-021-recalculable self-identity over the canonical payload of every other field (excluding `snapshot_hash` itself) |
| `source_binding` | object | complete §6.3 shape |

The `record_hash` field is **upstream evidence** — it is supplied by
the snapshot adapter and is the record-level identity of the upstream
approved geometry artifact. TASK-021's deterministic core does not own
the original upstream record body and therefore does **not** claim to
re-compute `record_hash`. A future adapter is responsible for:

1. loading the upstream validated geometry object;
2. verifying the upstream canonical `record_hash` against the supplied
   value;
3. refusing to construct `ApprovedTubeGeometrySnapshot` on a mismatch;
4. constructing a TASK-021 snapshot whose `snapshot_hash` is then
   verified by the core.

The `snapshot_hash` field is a separate, **TASK-021-recalculable**
self-identity that the deterministic core MUST recompute and verify
end-to-end. Its canonical payload is the JSON serialization of every
other field of the snapshot, with the rules in §11.1 applied
(Unicode code-point order, canonical decimal strings, no NaN / Infinity
/ runtime metadata), and the `snapshot_hash` field itself excluded
from the payload. A mismatch on `snapshot_hash` is a
`STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH` blocker.

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
| `rule_artifact_canonical_hash` | string | lowercase SHA-256 hex; **upstream artifact hash** — TASK-021 core does **not** recalculate this value because the core does not own the upstream rule body |
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
| `snapshot_hash` | lowercase 64-character SHA-256 hex | TASK-021-recalculable self-identity (same rule as §6.2) |

The `rule_artifact_canonical_hash` field is **upstream evidence** —
it is supplied by the authority adapter and is the canonical-hash
identity of the upstream evaluated layout-rule artifact. TASK-021's
deterministic core does not own the original upstream rule body and
therefore does **not** claim to re-compute `rule_artifact_canonical_hash`.
A future adapter is responsible for:

1. loading the upstream validated rule object;
2. verifying the upstream canonical `rule_artifact_canonical_hash`
   against the supplied value;
3. refusing to construct `LayoutRuleAuthoritySnapshot` on a mismatch;
4. constructing a TASK-021 snapshot whose `snapshot_hash` is then
   verified by the core.

The `snapshot_hash` field is the **TASK-021-recalculable** self-identity
that the deterministic core MUST recompute and verify end-to-end. Its
canonical payload is the JSON serialization of every other field of the
snapshot, with the rules in §11.1 applied (Unicode code-point order,
canonical decimal strings, no NaN / Infinity / runtime metadata), and
the `snapshot_hash` field itself excluded from the payload. A mismatch
on `snapshot_hash` is a `STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH`
blocker. For `INTERNAL_GENERIC`, `rule_artifact_canonical_hash` is
still required (the rules kernel fills it with a fully deterministic
internal digest over the internal canonical rule body) and remains
**upstream evidence** that the core does not re-derive.

In **both** modes, the core recomputes only `snapshot_hash`. The
core never recomputes `rule_artifact_canonical_hash` or any other
upstream artifact body digest, even though the values are stored in
the same snapshot. The provenance contract (§12) records **both**
the upstream record/artifact hash and the TASK-021 `snapshot_hash`
as separate, non-substitutable entries.

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

The `rule_pack_canonical_hash` here is the canonical hash of the
upstream TASK-012 rule-pack artifact. Like `record_hash` and
`rule_artifact_canonical_hash`, it is **upstream evidence** carried
into the TASk-021 runtime; the TASK-021 core does not re-derive it
because the core does not own the upstream pack body.

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

### 7.5 Finite enumeration bound (provably complete via inverse-basis method)

Define:

- `R = tube_center_envelope_diameter_m / 2`;
- `r_tube = outer_diameter_m / 2`;
- `c_edge = edge_clearance_m`;
- `rho = R - r_tube - c_edge`.

If `rho <= 0`, the request is blocked before enumeration.

#### 7.5.1 Inverse-basis bound (canonical lattice enumeration, proof-complete)

The candidate enumeration bound MUST be derived from the **inverse** of
the lattice basis matrix. Let the 2D basis matrix be:

```text
A = [[a_x, b_x],
     [a_y, b_y]]
```

Compute the inverse exactly under the same frozen Decimal context that
generates coordinates:

```text
det = a_x * b_y - a_y * b_x
```

If `det == 0` (the chosen `A` is non-invertible), the kernel MUST raise
`STL_BASIS_NON_INVERTIBLE` and **fail closed** before enumeration —
returning a truncated or partial result is forbidden.

When `det != 0`:

```text
B = inverse(A) = [[ B_00, B_01],
                   [ B_10, B_11 ]]
```

so that `B · A = I` (verified under Decimal).

Define the conservative offset-aware envelope half-extents under the
frozen Decimal context:

```text
d_x = rho + abs(offset_x)
d_y = rho + abs(offset_y)
```

The conservative index bounding box is:

```text
U = ceil(abs(B_00) * d_x + abs(B_01) * d_y) + 1
V = ceil(abs(B_10) * d_x + abs(B_11) * d_y) + 1
```

The `+ 1` is an **explicit conservative slack** to guarantee that no
legal envelope interior lattice point can fall outside the box. The
inverse computation, the multiplication, the `abs` and the `ceil` all
use the frozen Decimal context with no independent rounding shortcuts.

The complete candidate index domain is the **full Cartesian product**:

```text
u in [-U, U]
v in [-V, V]
candidate_count = (2 * U + 1) * (2 * V + 1)
```

Before generating coordinates the kernel MUST compare:

```text
candidate_count <= maximum_candidate_positions
```

If the comparison fails (candidate_count exceeds the
`maximum_candidate_positions` capacity ceiling from the authority
snapshot), the kernel MUST raise `STL_ENUMERATION_LIMIT_EXCEEDED` and
**fail closed**. Truncating the index domain, returning a partial
result, or "best-effort" early termination is forbidden.

**Deterministic independence from output quantization**: the index
bound is derived strictly from the inverse-basis working values, the
envelope radius `rho`, the conservative `d_x`/`d_y`, and the offset.
The bound MUST NOT be reduced or widened by quantized output
coordinates. Acceptance still uses unrounded Decimal working values
under the frozen context.

**Axis orientation handling**: for `PRIMARY_AXIS_X`, `A` is constructed
from `§7.2` directly. For `PRIMARY_AXIS_Y`, the `x`/`y` components of
both basis vectors are swapped before forming `A`. The whole pipeline
(index bound, enumeration, envelope test) applies the same swap
uniformly.

#### 7.5.2 Synthetic mathematical regression vector (proves enumerator completeness)

A synthetic mathematical regression vector exercises the inverse-basis
bound on a triangular lattice where the simpler "N" formula would
have **proven incomplete**:

| Input field | Value |
| --- | --- |
| pattern | `TRIANGULAR` |
| axis | `PRIMARY_AXIS_X` |
| pitch | `1` |
| rho | `100` |
| offset | `(0, 0)` |
| lattice index | `u = -57`, `v = 115` |

Working coordinates:

- `x = u * pitch + v * (pitch / 2) = -57 * 1 + 115 * (1 / 2) = -57 + 57.5 = 0.5`
- `y = v * (pitch * SQRT_3 / 2) = 115 * SQRT_3 / 2`

so

- `x^2 + y^2 = 0.25 + (115^2 * 3 / 4) = 0.25 + (13225 * 3 / 4) = 0.25 + 9918.75 = 9919`
- `rho^2 = 10000`

Therefore `x^2 + y^2 = 9919 < rho^2 = 10000`, the candidate is
**strictly inside the envelope**, and the kernel MUST accept it.

A **historically simpler bound** (a single scalar `N` derived by
dividing a radius-aware envelope bound by `pitch_m` and adding a small
constant) cannot account for the rotated basis vectors of a
non-orthogonal lattice. On the regression vector above, the single
scalar bound caps both `|u|` and `|v|` at the same magnitude and
**wrongly rejects the `v = 115` index** even though its working
coordinate lies inside the envelope. The new inverse-basis bound
(with `U`, `V`) covers the same candidate and hence proves itself
strictly more complete for the triangular basis.

This regression vector is a **synthetic mathematical fixture**. It is
not an engineering Golden value. It must not be cited as TEMA, ASME,
API, vendor, ISO or any other standard content. It exists only to
prove enumeration completeness on the triangular lattice.

#### 7.5.3 Capacity ceiling comparison (binding)

After the inverse-basis bound is computed, the kernel MUST run:

```text
candidate_count = (2 * U + 1) * (2 * V + 1)
test: candidate_count <= maximum_candidate_positions
fail_closed_on_exceed: STL_ENUMERATION_LIMIT_EXCEEDED
```

No truncation of `u in [-U, U]` or `v in [-V, V]` is permitted at
any point in the pipeline.

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
11. finite enumeration-limit calculation: inverse-basis bound
    (`det != 0`, `U`, `V`, `candidate_count`) and the
    `maximum_candidate_positions` capacity check; a non-invertible
    basis blocks under `STL_BASIS_NON_INVERTIBLE` here;
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
- `STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH` — the `snapshot_hash` field
  of `ApprovedTubeGeometrySnapshot` does not match the
  TASK-021-recalculated canonical hash over the rest of the snapshot.
- `STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH` — the `snapshot_hash` field
  of `LayoutRuleAuthoritySnapshot` does not match the
  TASK-021-recalculated canonical hash over the rest of the snapshot.
- `STL_LAYOUT_RULE_LICENSE_BLOCKED`;
- `STL_BASIS_NON_INVERTIBLE` — the basis matrix `A` derived from the
  verified `pattern_family` / `axis_orientation` carries `det == 0`; the
  enumeration must fail closed.
- `STL_LAYOUT_RULE_HASH_MISMATCH` *(removed from canonical role; the upstream
  rule body canonical hash is verified by the adapter, not by the core, and any
  core-level re-derivation must use the new `STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH`
  code; legacy uses of `STL_LAYOUT_RULE_HASH_MISMATCH` are not generated by the v1
  core)*.
- `STL_TUBE_GEOMETRY_HASH_MISMATCH` *(removed from canonical role; rationale as
  above for `STL_LAYOUT_RULE_HASH_MISMATCH`)*.
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

### 10.2 Closed warning-code set (deterministic emission, full five-field content)

For every warning emitted by TASK-021 the kernel MUST populate the
**complete five-field shape**, the **field_path**, the **message_key**,
the sorted-duplicate-free **evidence_refs** and the canonical **details**
object specified below. The kernel MUST NOT emit a warning whose trigger
condition, field_path, message_key, evidence_refs or details are not
fully specified by this sub-section, and MUST NOT silently omit a
warning whose trigger condition is satisfied. Warnings MUST be
generated **before** `layout_hash` is computed, so that the
`layout_hash_payload` (§11.3) carries the frozen warning set. Warning
evidence_refs MUST be sorted and duplicate-free before canonicalization.

A blocked result may carry only those warnings whose trigger condition
and upstream evidence were already determined **before** the failing
stage. The kernel MUST NOT synthesize warnings for `BLOCKED` results
that depend on inputs which the failing stage never successfully
validated.

#### 10.2.1 `STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM`

- **Trigger condition** (single): emitted when the verified request's
  `layout_rule_authority.authority_mode == INTERNAL_GENERIC`. The
  warning is **not** emitted for `APPROVED_RULE_PACK`.
- `code`: exact string `STL_INTERNAL_GENERIC_NO_STANDARD_CLAIM`.
- `field_path`: exact string
  `layout_rule_authority.authority_mode`.
- `message_key`: exact string `internal_generic_no_standard_claim`.
- `evidence_refs`: the sorted-duplicate-free array copied from
  `layout_rule_authority.evidence_refs`.
- `details` (canonical JSON object, exact key set and order):
  - `authority_mode`: exact string `INTERNAL_GENERIC`.
  - `standard_claim_status`: exact string `NO_STANDARD_CLAIM`.

#### 10.2.2 `STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER`

- **Trigger condition**: emitted on **every** valid (`status == VALID`)
  result. The v1 envelope is always supplied by the caller; the
  envelope radius is therefore not a shell or bundle diameter produced
  by TASK-021, and the result must say so.
- `code`: exact string `STL_CALLER_SUPPLIED_ENVELOPE_NOT_SHELL_DIAMETER`.
- `field_path`: exact string
  `placement_envelope.tube_center_envelope_diameter_m`.
- `message_key`: exact string `caller_supplied_envelope_not_shell_diameter`.
- `evidence_refs`: the sorted-duplicate-free array copied from
  `placement_envelope.evidence_refs`.
- `details` (canonical JSON object, exact key set and order):
  - `semantic_role`: exact string `tube_center_placement_constraint`.
  - `shell_diameter_status`: exact string `NOT_COMPUTABLE`.

The warning is suppressed only on a `BLOCKED` result whose failing
stage is reached before the envelope is verified.

#### 10.2.3 `STL_PASS_PARTITION_ASSIGNMENT_DEFERRED`

- **Trigger condition**: emitted on **every** valid (`status == VALID`)
  result. Pass partition / pass membership is explicitly out of TASK-021
  v1 scope (§15.3), and the result must state so.
- `code`: exact string `STL_PASS_PARTITION_ASSIGNMENT_DEFERRED`.
- `field_path`: exact string
  `configuration.tube_pass_count`.
- `message_key`: exact string `pass_partition_assignment_deferred`.
- `evidence_refs`: the sorted-duplicate-free array copied from
  `request.evidence_refs`.
- `details` (canonical JSON object, exact key set and order):
  - `tube_pass_count`: the **verified integer** copied from the
    validated TASK-020 `configuration.tube_pass_count` (after type
    and lexical validation).
  - `assignment_status`: exact string `NOT_COMPUTABLE`.

The warning is suppressed only on a `BLOCKED` result whose failing
stage is reached before `tube_pass_count` is fully verified.

#### 10.2.4 `STL_UTUBE_BEND_GEOMETRY_DEFERRED`

- **Trigger condition** (single): emitted when the verified
  configuration's `construction_family == U_TUBE` (and only then).
  The warning is **not** emitted for fixed-tubesheet, floating-head or
  kettle configurations.
- `code`: exact string `STL_UTUBE_BEND_GEOMETRY_DEFERRED`.
- `field_path`: exact string `u_tube_pairing_plan`.
- `message_key`: exact string `u_tube_bend_geometry_deferred`.
- `evidence_refs`: the sorted-duplicate-free array copied from
  `u_tube_pairing_plan.evidence_refs`.
- `details` (canonical JSON object, exact key set and order):
  - `construction_family`: exact string `U_TUBE`.
  - `bend_geometry_status`: exact string `NOT_COMPUTABLE`.

The warning is suppressed only on a `BLOCKED` result whose failing
stage is reached before `u_tube_pairing_plan` is verified.

#### 10.2.5 Deterministic ordering and identity of warnings

The warnings array is deterministically sorted by the TASK-020
composite ordering rule `(code, field_path or "", message_key,
canonical_details_hash)` BEFORE it enters `layout_hash_payload`.
The `canonical_details_hash` is `SHA-256` over the canonical JSON of
the warning's `details` object (§11.1). Two warnings differing only
in their `canonical_details_hash` will sort stably, so the array order
is reproducible.

Forward-references: `internal_generic_no_standard_claim` (10.2.1),
`caller_supplied_envelope_not_shell_diameter` (10.2.2),
`pass_partition_assignment_deferred` (10.2.3),
`u_tube_bend_geometry_deferred` (10.2.4).

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

### 11.3 Layout hash (no self-reference, ordered build pipeline)

The layout hash pipeline MUST run in the **exact** order below. No
`layout_hash` value may be computed before the corresponding
`layout_hash_payload` is finalized; no `layout_id` may be computed
before `layout_hash` exists; no final `provenance` may be constructed
before `layout_hash` exists; no final `TubeLayout` may be assembled
before both `layout_id` and the final `provenance` exist.

#### 11.3.1 `ProvenancePreHashProjection`

The deterministic core builds a **provenance projection that
explicitly excludes everything that depends on `layout_hash` or
`layout_id`**. The projection's exact field set is:

- `task_id`: exact string `TASK-021`;
- `design_contract_path`: the relative path of this design contract;
- `task020_configuration_id`: copied from the verified configuration;
- `task020_configuration_hash`: copied from the verified configuration;
- the complete TASK-020 case authority (by reference / exact fields);
- `tube_geometry_id`, `tube_geometry_revision`, `tube_geometry_record_hash`,
  and the complete `tube_geometry.source_binding`;
- `layout_rule_profile_id`, `layout_rule_rule_id`, `layout_rule_rule_version`,
  `layout_rule_rule_artifact_canonical_hash`, `layout_rule_source_class`,
  `layout_rule_approval_status`, the complete
  `layout_rule_provenance_edge_ids`, the complete
  `layout_rule_evidence_refs`, and (when present) the complete
  `rule_pack_identity` triple;
- `envelope_evidence_refs`;
- `exclusion_zone_evidence_refs`;
- (when present) `u_tube_pairing_evidence_refs`;
- `software_version`;
- `git_commit` (supplied by the calling application — provenance
  metadata, not a runtime-now value);
- `request_hash`;
- the closed `deferred_capabilities` set;

The projection **MUST NOT** contain:

- `layout_id`;
- `layout_hash`;
- the final provenance `layout_hash` entry (which is added only after
  `layout_hash` is computed, in step 5 below).

The projection **MUST NOT** contain runtime-now values: no
`timestamp-now`, no current local time, no `os.urandom()` output, no
host / process / filesystem metadata. All fields are either copied
from verified upstream input (snapshots) or filled with stable
compile-time values (schema version, design contract path, deferred
set, composite ordering constants).

The resulting object is `provenance_pre_hash` and is the value that
immediately precedes the `layout_hash` step.

#### 11.3.2 `layout_hash_payload`

The exact field set of `layout_hash_payload` is:

- `output_schema_version`: exact string `task021.tube-layout.v1`;
- `request_hash`: from §11.2;
- the canonical accepted-positions array in §7.9 order, including
  `position_id`, lattice index `(u, v)` and quantized coordinates;
- `tube_hole_count`;
- `physical_tube_count`;
- `boundary_rejection_count`;
- `exclusion_rejection_count`;
- the canonical `exclusion_audit` array in §9.2 order;
- the canonical `warnings` array in the deterministic order of §10.2.5;
- `blockers`: the canonical empty array (a valid layout has no
  blockers — this field is explicit so a bug that ever flips a valid
  layout to a blocked-after-the-fact state is impossible to hide);
- the closed `deferred_capabilities` set;
- `provenance_pre_hash`: the §11.3.1 projection **exactly**.

The payload **MUST NOT** contain:

- `layout_id`;
- `layout_hash` itself;
- any field that references or embeds the final `provenance.layout_hash`
  entry.

#### 11.3.3 Build order (six steps, all six MUST run, in this exact order)

1. **Build `provenance_pre_hash`** — the §11.3.1 projection, from
   verified snapshots and stable compile-time values only.
2. **Build `layout_hash_payload`** — the §11.3.2 payload, ending with
   `provenance_pre_hash` embedded inside.
3. **Compute `layout_hash`** = `SHA-256(canonical_json(layout_hash_payload))`
   under §11.1 canonicalization. The byte length is 32 bytes hex-encoded to
   64 lowercase hex characters.
4. **Compute `layout_id`** = `UUIDv5(UUID_NAMESPACE_URL,
   "urn:hxforge:task021:tube-layout:v1:" + layout_hash)`.
5. **Construct final `provenance`** = `provenance_pre_hash` plus the
   single new entry `layout_hash` (lowercase SHA-256 hex). Nothing else
   is added.
6. **Construct final `TubeLayout`** — the layout object of §9.3 with
   `layout_id`, `layout_hash` and the final `provenance` populated.

The kernel MUST refuse to compute `layout_hash` while any field in
`layout_hash_payload` is missing. The kernel MUST refuse to compute
`layout_id` until `layout_hash` exists. The kernel MUST refuse to add
`layout_hash` to the final provenance until step 3 has completed. The
kernel MUST refuse to assemble the final `TubeLayout` until step 5 is
complete.

A test expectation covers each of:

- `layout_hash_payload` contains no `layout_hash` element and no
  `layout_id` element;
- `layout_hash_payload["provenance_pre_hash"]` contains no `layout_hash`
  and no `layout_id`;
- the final `provenance` object contains `layout_hash` only **after**
  step 3 has completed, and never earlier.

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

### 11.5 `UTubePairingPlan.pairing_plan_hash` (canonicalized)

`UTubePairingPlan.pairing_plan_hash` is a lowercase 64-character
SHA-256 hex digest computed under §11.1 canonicalization. The hash
builds from a strict ordering pipeline; a hash mismatch or any
non-conforming input is a `STL_UTUBE_PAIRING_INVALID` blocker
(distinguished by `message_key`).

#### 11.5.1 Canonical leg

Each leg is a `LatticeIndex`. Its canonical form for hashing is:

```text
{"u": <canonical_integer>, "v": <canonical_integer>}
```

The integers MUST be present, MUST be valid `int` (no booleans), and
MUST NOT carry any extra fields.

#### 11.5.2 Canonical pair

Each `UTubePair` (after leg normalization) is canonicalized as:

1. Legs are sorted by the numeric tuple `(u, v)` in **lexicographic
   Decimal-numerical order**. The leg with the smaller numeric tuple
   becomes `leg_a`; the larger becomes `leg_b`. If both legs are equal,
   the pair is **self-pairing** and the request MUST be rejected with
   `STL_UTUBE_PAIRING_INVALID` (message_key `u_tube_pair_self`).
2. The canonical pair payload contains exactly:
   - `pair_id` (non-empty string);
   - canonical `leg_a` from §11.5.1;
   - canonical `leg_b` from §11.5.1;
   - `evidence_refs`: the pair's array, **sorted** and **duplicate-free**.
3. `pair_id` MUST be non-empty and **globally unique** across the
   whole plan. A duplicate `pair_id` blocks with `STL_UTUBE_PAIRING_INVALID`
   (message_key `u_tube_pair_duplicate_id`).

Any of the following rejection conditions also triggers
`STL_UTUBE_PAIRING_INVALID` with the listed `message_key`:

- `u_tube_pair_unknown_leg` — `leg_a` or `leg_b` references an unknown
  index (an index not in the accepted positions set);
- `u_tube_pair_leg_reused` — the same `(u, v)` leg appears in more
  than one pair after normalization, or is omitted entirely (a leg
  appears in zero pairs);
- `u_tube_pair_missing_coverage` — at least one accepted position is
  not covered by any canonical pair (the coverage test is performed
  in the normalized step that already exists, but the canonical
  coverage representation is the canonical-pairs array).

#### 11.5.3 Pair ordering (independent of input order)

Canonical pairs MUST be sorted by the lexicographic composite key:

```text
(leg_a.u, leg_a.v, leg_b.u, leg_b.v, pair_id)
```

using **Decimal-numerical** order on each numeric element and
**lexicographic** order on `pair_id`. The pipeline MUST NOT rely on
the input array order or on `hash()` / `id()` of any object.

#### 11.5.4 `pairing_plan_hash_payload`

The exact field set of `pairing_plan_hash_payload` is:

- `schema_version`: exact `task021.u-tube-pairing.v1`;
- `pairs`: the canonical-pairs array from §11.5.3;
- `plan_evidence_refs`: the `UTubePairingPlan.evidence_refs` array,
  **sorted and duplicate-free**.

The payload **MUST NOT** contain:

- `pairing_plan_hash` itself;
- any upstream hash field;
- any field outside the three above.

The hash is:

```text
pairing_plan_hash = SHA-256(canonical_json(pairing_plan_hash_payload))
```

#### 11.5.5 Validation order (binding)

The pairing-plan validator MUST run the following stages in this
order. A failure at any stage halts the pipeline and emits
`STL_UTUBE_PAIRING_INVALID` with the matching `message_key`:

1. raw shape and field-type validation (`message_key`:
   `u_tube_pair_raw_shape_invalid`);
2. leg normalization into the canonical `{u, v}` form
   (`message_key`: `u_tube_pair_leg_normalization_invalid`);
3. duplicate-`pair_id`, self-pairing, unknown-leg, leg-reuse and
   missing-coverage checks (`message_key` from the matching condition
   in §11.5.2);
4. canonical pair ordering as in §11.5.3;
5. canonical payload assembly as in §11.5.4;
6. `pairing_plan_hash` recomputation;
7. comparison of recomputed vs supplied `pairing_plan_hash`. A mismatch
   is `STL_UTUBE_PAIRING_HASH_MISMATCH` (this code is preserved as-is
   because it carries the exact semantic of "hash recomputation
   mismatch" and is **not** to be downgraded to the
   invalid-pairing code).

After the seven stages complete cleanly, the normalized pairing plan,
**including** its `pairing_plan_hash`, is then fed forward into the
normalized request hash (§11.2). The kernel MUST NOT skip a stage
because the hash matches an earlier probed value; the stages are
mandatory.

## 12. Provenance contract

The valid result provenance object contains:

- `task_id: "TASK-021"`;
- `design_contract_path`;
- `task020_configuration_id`;
- `task020_configuration_hash`;
- complete TASK-020 case authority;
- `tube_geometry_id`, `tube_geometry_revision`, `tube_geometry_record_hash`
  (the upstream record-level identity), `tube_geometry_snapshot_hash`
  (the TASK-021-recalculable identity) and the complete
  `tube_geometry.source_binding`;
- `layout_rule_profile_id`, `layout_rule_rule_id`, `layout_rule_rule_version`,
  `layout_rule_rule_artifact_canonical_hash` (the upstream
  artifact-level identity), `layout_rule_source_class`,
  `layout_rule_approval_status`, `layout_rule_snapshot_hash` (the
  TASK-021-recalculable identity), complete `provenance_edge_ids` and
  complete `evidence_refs`, and (when present) the complete
  `rule_pack_identity` triple;
- envelope evidence refs;
- exclusion-zone evidence refs;
- U-tube pairing evidence refs when present;
- `software_version`;
- `git_commit` supplied by the calling application;
- `request_hash`;
- `layout_hash`;
- warnings and deferred-capability declarations.

The provenance object records **two distinct** identity triples per
upstream artifact: the upstream record / artifact body hash
(`tube_geometry_record_hash`, `layout_rule_rule_artifact_canonical_hash`,
and (when present) `rule_pack_canonical_hash`) **and** the
TASK-021-recalculable `snapshot_hash` over the snapshot object. They
are not interchangeable; a hash recomputation failure on either side
is a different blocker code (§10.1). The TASK-021 deterministic core
recalculates only `snapshot_hash`; upstream artifact hashes are
admitted as supplied by the adapter (see §6.2, §6.4, §6.5).

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
- TASK-019 Amendment 002-K assets are not imported or mutated;
- TASK-022 through TASK-039 remain unallocated;
- the inverse-basis bound `U = ceil(abs(B_00) * d_x + abs(B_01) * d_y) + 1`,
  `V = ceil(abs(B_10) * d_x + abs(B_11) * d_y) + 1` covers every
  envelope-interior lattice point on both square and triangular bases,
  and the synthetic regression vector `(u=-57, v=115)` on a
  `TRIANGULAR` lattice with `pitch=1, rho=100` lies strictly inside
  the envelope (`x^2 + y^2 = 9919 < rho^2 = 10000`);
- `candidate_count = (2 * U + 1) * (2 * V + 1)` is computed before any
  coordinate is generated and is blocked under
  `STL_ENUMERATION_LIMIT_EXCEEDED` when it exceeds
  `maximum_candidate_positions`;
- a non-invertible basis (`det == 0`) blocks with
  `STL_BASIS_NON_INVERTIBLE` before any enumeration;
- `ApprovedTubeGeometrySnapshot.snapshot_hash` is recalculated by the
  core and verified, and any mismatch is `STL_TUBE_GEOMETRY_SNAPSHOT_HASH_MISMATCH`;
- `LayoutRuleAuthoritySnapshot.snapshot_hash` is recalculated by the
  core and verified, and any mismatch is `STL_LAYOUT_RULE_SNAPSHOT_HASH_MISMATCH`;
- TASK-021 core does **not** claim to recalculate upstream
  `record_hash` / `rule_artifact_canonical_hash` /
  `rule_pack_canonical_hash` (those are verified by the adapter);
- the `layout_hash_payload` has no self-reference: no `layout_hash`
  element, no `layout_id` element, and the embedded
  `provenance_pre_hash` has no `layout_hash` and no `layout_id`;
- the final `provenance` object receives `layout_hash` only **after**
  the `layout_hash` step completes (six-step order, §11.3.3);
- `pairing_plan_hash` is computed over the canonical payload of
  §11.5.4 only (no `pairing_plan_hash` element included in its own
  payload), pair ordering is independent of input order, legs are
  normalized, `pair_id`s are unique, self-pairing is blocked, and the
  seven-stage validation pipeline of §11.5.5 runs to completion before
  the plan enters `request_hash`;
- each closed warning of §10.2 emits under its stated trigger
  condition only, carries the exact five-field shape and exact
  field_path / message_key / sorted evidence_refs / canonical
  details specified for it, is suppressed on a `BLOCKED` result whose
  upstream evidence was not validated, and is generated before
  `layout_hash`;
- frozen design boundaries are represented in architecture tests.

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
