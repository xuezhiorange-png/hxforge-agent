# TASK-024 — Shell-and-Tube Baffle Geometry and Spacing Foundation

> Binding design contract for the fourth M3 shell-and-tube capability.
>
> TASK-024 consumes one complete valid TASK-020 shell-and-tube configuration,
> one complete valid TASK-021 tube layout, one complete valid TASK-022
> shell-and-bundle geometry result, and explicit caller-supplied baffle-design
> authority. It produces one deterministic baffle geometry and spacing result.
>
> TASK-024 v1 does not calculate heat-transfer coefficients, flow areas,
> hydraulic diameters, Kern or Bell–Delaware corrections, pressure drop,
> vibration, mechanical adequacy, manufacturing adequacy, materials, mass,
> cost, optimization, API, persistence, CLI, reports, or engineering Goldens.

## 1. Authority, allocation, baseline, and status

| Field | Binding value |
|---|---|
| Repository | `xuezhiorange-png/hxforge-agent` |
| Authorizing Issue | Issue #155 — `[TASK-024][source-definition] Define shell-and-tube baffle geometry and spacing foundation` |
| Source-definition creation gate | `AUTHORIZE_TASK024_BAFFLE_GEOMETRY_AND_SPACING_SOURCE_DEFINITION_ISSUE_CREATION_ONLY` |
| Source-definition review gate | `AUTHORIZE_TASK024_BAFFLE_GEOMETRY_AND_SPACING_SOURCE_DEFINITION_REVIEW_ONLY` |
| Source-definition amendment | `TASK024_SOURCE_DEFINITION_AMENDMENT_001` |
| Amendment comment | Issue #155 comment `4981216325` |
| Minimal-compute decision record SHA-256 | `acd48779467828f731d5a7514d977a587cb61018821575062477ebef2ba16d28` |
| Geometry-fixup decision record SHA-256 | `baeb83a69740edfe5569181a8d9b689a8e6655c14f7452cf9aeda3d13675f757` |
| Geometry-fixup review result | `PASS` |
| One-file authoring gate | `AUTHORIZE_TASK024_MINIMAL_COMPUTE_V1_ONE_FILE_DESIGN_AUTHORING_ONLY` |
| Exact authoring base | `main@b93300b45f2cf718ab020b2203f772e9a8413a8f` |
| Design branch | `docs/task-024-baffle-geometry-spacing-design` |
| Design file | `docs/tasks/TASK-024-shell-and-tube-baffle-geometry-and-spacing.md` |
| Allowed repository mutation in this round | This file only |
| Frozen allocation | `TASK-024 = Shell-and-Tube Baffle Geometry and Spacing Foundation` |
| Design status | `PROPOSED` pending separate review and merge authorization |
| Implementation status | `NOT AUTHORIZED` |
| Draft PR status | `NOT AUTHORIZED` |
| Ready status | `NOT AUTHORIZED` |
| Merge status | `NOT AUTHORIZED` |
| Issue close | `NOT AUTHORIZED` |
| TASK-025 through TASK-039 | `UNALLOCATED` |

This design authoring gate permits one branch and this one repository design file.
It does not authorize production code, tests, fixtures, CI-manifest changes,
workflow changes, a pull request, Ready transition, merge, Issue mutation,
Issue closure, branch deletion, implementation, or later-task allocation.

## 2. Exact allocation and problem statement

TASK-024 owns the deterministic geometric boundary between an accepted
TASK-022 shell/bundle result and later shell-side thermal or hydraulic work.

TASK-020 establishes configuration identity but contains no engineering
dimensions. TASK-021 establishes immutable tube-center coordinates and approved
tube geometry but explicitly does not establish shell or baffle geometry.
TASK-022 establishes concentric shell/bundle geometry and shell inside-diameter
authority but explicitly defers baffle design.

TASK-024 therefore must:

1. validate and cross-bind complete TASK-020, TASK-021, and TASK-022 values;
2. accept explicit caller-supplied axial-span and baffle-design authority;
3. support one intentionally narrow v1 topology;
4. construct deterministic baffle center-plane positions;
5. construct deterministic baffle occupied axial intervals;
6. derive baffle diameter and baffle-hole diameter from explicit clearances;
7. construct an analytic single-segment cut chord for each baffle;
8. classify every accepted TASK-021 tube position against the complete
   baffle-hole clearance disk;
9. validate covered-region hole containment and pairwise non-overlap;
10. emit immutable geometry, hashes, blockers, warnings, deferred capabilities,
    and provenance;
11. fail closed with no partial geometry.

TASK-024 establishes geometric identity only. It does not establish thermal,
hydraulic, mechanical, manufacturing, procurement, inspection, certification,
or legal-compliance adequacy.

## 3. Scope and non-scope

### 3.1 Frozen v1 scope

```text
SUPPORTED_CONSTRUCTION_FAMILY=FIXED_TUBESHEET
SUPPORTED_SHELL_PASS_COUNT=1
SUPPORTED_BAFFLE_TYPE=SINGLE_SEGMENTAL
AXIAL_AUTHORITY_MODE=CALLER_SUPPLIED_EXPLICIT
SPACING_MODE=CENTER_PLANE_TO_CENTER_PLANE
CUT_MODE=DIAMETER_FRACTION
ORIENTATION_AUTHORITY=CALLER_SUPPLIED_EXPLICIT_SEQUENCE
WINDOW_GEOMETRY=IN_SCOPE
BAFFLE_COVERED_GEOMETRY=IN_SCOPE
CROSSFLOW_REFERENCE_GEOMETRY=IN_SCOPE_CLASSIFICATION_ONLY
TUBE_HOLE_REGION_CLASSIFICATION=IN_SCOPE
```

### 3.2 Explicitly unsupported in v1

```text
FLOATING_HEAD
U_TUBE
SHELL_PASS_COUNT_OTHER_THAN_1
BAFFLE_TYPE_OTHER_THAN_SINGLE_SEGMENTAL
AUTOMATIC_BAFFLE_SELECTION
AUTOMATIC_ORIENTATION_ALTERNATION
AUTOMATIC_SPACING_GENERATION
NOZZLE_POSITION_INFERENCE
LONGITUDINAL_BAFFLE
PASS_PARTITION
SHELL_SIDE_FLOW_ROUTING
```

Unsupported does not mean physically infeasible. It means outside this first
deterministic contract and therefore blocked.

### 3.3 Deferred downstream capabilities

```text
CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE
WINDOW_FLOW_AREA_NOT_COMPUTABLE
MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE
HYDRAULIC_DIAMETER_NOT_COMPUTABLE
LEAKAGE_FLOW_AREA_NOT_COMPUTABLE
BYPASS_FLOW_AREA_NOT_COMPUTABLE
LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE
BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE
SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE
KERN_SCREENING_NOT_COMPUTABLE
BELL_DELAWARE_NOT_COMPUTABLE
SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE
TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE
FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE
THERMAL_EXPANSION_NOT_COMPUTABLE
MECHANICAL_ADEQUACY_NOT_COMPUTABLE
MANUFACTURING_ADEQUACY_NOT_COMPUTABLE
MATERIAL_SELECTION_NOT_COMPUTABLE
MASS_NOT_COMPUTABLE
COST_NOT_COMPUTABLE
OPTIMIZATION_NOT_COMPUTABLE
API_NOT_COMPUTABLE
PERSISTENCE_NOT_COMPUTABLE
CLI_NOT_COMPUTABLE
REPORT_NOT_COMPUTABLE
GOLDEN_VALIDATION_NOT_COMPUTABLE
```

## 4. Binding source inventory and authority disposition

### 4.1 Binding repository authority

TASK-024 is derived from:

1. `docs/MASTER_DEVELOPMENT_SPEC.md`, especially deterministic-kernel and
   first-stage shell-and-tube requirements;
2. Issue #155 and source-definition amendment comment `4981216325`;
3. the Charles-approved Minimal Compute v1 A1–A15 decision package and
   Geometry Fixup 001;
4. `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md` and
   `src/hexagent/exchangers/shell_tube/models.py`;
5. `docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md` and
   `src/hexagent/exchangers/shell_tube/tube_layout/**`;
6. `docs/tasks/TASK-022-shell-and-bundle-geometry.md` and
   `src/hexagent/exchangers/shell_tube/shell_bundle_geometry/**`;
7. TASK-002 SI and decimal discipline;
8. TASK-004 structured warning, blocker, provenance, and no-partial-result
   conventions;
9. TASK-012 source, licensing, permission, approval, and restricted-content
   governance;
10. TASK-015A deterministic test and CI ownership conventions.

### 4.2 Direct runtime dependencies

| Dependency | TASK-024 use |
|---|---|
| TASK-020 | complete immutable `ShellAndTubeConfiguration` and identity |
| TASK-021 | complete immutable `TubeLayout`, exact accepted `TubePosition` coordinates, and approved tube geometry |
| TASK-022 | complete immutable `ShellBundleGeometry`, exact shell inside diameter, and upstream cross-binding |
| TASK-002 | canonical SI decimal behavior |
| TASK-004 | messages, blockers, warnings, provenance, and fail-closed behavior |
| TASK-015A | future test/CI ownership |
| TASK-012 | anti-fabrication and future rule-source governance |

### 4.3 Caller-supplied authority is not a TASK-012 rule body

TASK-024 v1 contains no external engineering rule body. The authority mode is:

```text
CALLER_SUPPLIED_EXPLICIT
```

The request supplies values and evidence references. The result must emit:

```text
NO_STANDARD_CLAIM
NO_EXTERNAL_STANDARD_APPROVAL
NO_AUTOMATIC_SELECTION
```

`CALLER_SUPPLIED_EXPLICIT` is a TASK-024 authority mode, not a new TASK-012
`source_class`. TASK-012 source-class fields are not fabricated for caller
inputs. If a later task introduces approved rule-pack authority, that requires a
separate design amendment and adapter boundary.

### 4.4 Forbidden substitutes

The following are never valid authority:

- remembered TEMA, API, ASME, Kern, Bell–Delaware, vendor, textbook, handbook,
  or project-default dimensions;
- copied or reconstructed restricted tables, charts, figures, scans, clauses,
  or formula images;
- unpermissioned vendor content;
- test fixtures, expected outputs, or synthetic production values;
- nearest-size, first-fit, default, ranking, fallback, or heuristic selection;
- reverse derivation from desired thermal duty, pressure drop, area, cost, or
  benchmark output;
- TASK-021 placement-envelope diameter treated as baffle diameter;
- TASK-022 shell-to-bundle clearance treated as shell-to-baffle clearance;
- TASK-023 shell catalog records treated as baffle-design authority.

## 5. Complete upstream input contracts

The request carries complete upstream objects. ID-only, hash-only, or partial
projections are insufficient.

### 5.1 TASK-020 `ShellAndTubeConfiguration`

The core verifies:

- `schema_version == "task020.configuration.v1"`;
- `equipment_family == SHELL_AND_TUBE`;
- `blockers` is empty;
- the existing TASK-020 canonical payload reproduces `configuration_hash`;
- the existing TASK-020 identity helper reproduces `configuration_id`;
- `construction_family == FIXED_TUBESHEET`;
- `shell_pass_count == 1`;
- orientation is one exact existing `Orientation` token;
- case authority is accepted under the frozen TASK-020/TASK-014 contract.

TASK-024 carries `equipment_orientation` as identity-and-provenance binding only.
The value is copied from the upstream `ShellBundleGeometry.equipment_orientation`
field (§5.3) and cross-checked against `ShellAndTubeConfiguration.orientation`
(§5.1) and `TubeLayout.equipment_orientation` (§5.2). The field does not exist
on `ShellAndTubeConfiguration`. TASK-024 does not assign gravity, top/bottom
process meaning, nozzle position, baffle cut orientation, or installation
adequacy from `equipment_orientation`. The baffle cut orientation is selected
by the dedicated `BaffleOrientation` input from the caller, never by
`equipment_orientation`.

### 5.2 TASK-021 `TubeLayout`

The core verifies:

- `schema_version == "task021.tube-layout.v1"`;
- `blockers` is empty;
- `positions` is non-empty;
- the existing TASK-021 canonical payload reproduces `layout_hash`;
- the existing TASK-021 identity helper reproduces `layout_id`;
- complete `case_authority` and `provenance` remain present;
- embedded `ApprovedTubeGeometrySnapshot` remains valid;
- `task020_configuration_id` and `task020_configuration_hash` match the
  separately supplied configuration;
- construction family, orientation, shell-pass count, and tube-pass count match;
- `tube_hole_count == len(positions)` for the supported fixed-tubesheet slice;
- every `TubePosition.position_id` is unique;
- every accepted position has exact canonical `x_m` and `y_m`;
- no position is re-enumerated, rotated, mirrored, axis-swapped, renamed, or
  silently repaired.

### 5.3 TASK-022 `ShellBundleGeometry`

The core verifies:

- `schema_version == "task022.shell-bundle-geometry.v1"`;
- `blockers` is empty;
- the existing TASK-022 canonical payload reproduces `geometry_hash`;
- the existing TASK-022 identity helper reproduces `geometry_id`;
- `task020_configuration_id/hash` match the supplied configuration;
- `task021_layout_id/hash` match the supplied layout;
- construction family, orientation, shell-pass count, and tube-pass count match;
- `tube_geometry_snapshot_hash` matches the TASK-021 snapshot;
- `position_count == len(tube_layout.positions)`;
- `shell_inside_diameter_m` is positive;
- shell radius and diameter are algebraically consistent;
- the result remains concentric in the TASK-021 transverse coordinate frame;
- all upstream warnings, authority snapshots, and provenance remain immutable.

TASK-024 does not inspect a TASK-023 catalog, select a shell record, or change
TASK-022 shell authority. It consumes the accepted TASK-022 result as-is.

## 6. Closed identities and schema versions

### 6.1 Schema constants

```text
REQUEST_SCHEMA_VERSION=task024.baffle-geometry-request.v1
AXIAL_SPAN_SCHEMA_VERSION=task024.baffle-axial-span.v1
DESIGN_AUTHORITY_SCHEMA_VERSION=task024.caller-baffle-design-authority.v1
RESULT_SCHEMA_VERSION=task024.baffle-geometry.v1
PROFILE_ID=hxforge.shell_tube.baffle_geometry.v1
DESIGN_CONTRACT_PATH=docs/tasks/TASK-024-shell-and-tube-baffle-geometry-and-spacing.md
```

### 6.2 Closed enums

```text
BaffleType:
  SINGLE_SEGMENTAL

BaffleOrientation:
  TOP
  BOTTOM
  LEFT
  RIGHT

TubeRegionClassification:
  WINDOW
  CROSSFLOW_REFERENCE

ValidationStatus:
  VALID
  BLOCKED
```

Tokens are exact and case-sensitive. Aliases are forbidden.

### 6.3 No default identity

No missing enum value receives a default. Unknown, aliased, case-normalized, or
heuristically mapped values block.

## 7. Numeric, canonical, and ordering discipline

### 7.1 Public decimal lexical domain

Every unit-bearing public value and every public dimensionless fraction is a
canonical finite base-10 decimal string.

It must:

- contain no exponent notation;
- contain no leading `+`;
- contain no surrounding whitespace;
- contain no NaN or Infinity;
- normalize negative zero to `0`;
- satisfy the field-specific sign rule.

Binary floating-point values are forbidden at all public and hash boundaries.

### 7.2 Frozen Decimal context

```text
precision=50
rounding=ROUND_HALF_EVEN
coordinate_quantum_m=0.000000000001
canonical_zero=0
```

All arithmetic uses `Decimal` under this context. `sqrt` uses the Decimal square
root under the same context.

### 7.3 Quantization ordering discipline

The classification, tangency, intersection, outer-containment, and pairwise
non-overlap decisions are bound to the following exact ordering, frozen from
Geometry Fixup 001:

```text
HIGH_PRECISION_DECIMAL_DERIVATION
AND BOUNDARY_COMPARISON
THEN
CLASSIFICATION
TANGENCY
INTERSECTION
OUTER_CONTAINMENT
PAIRWISE_NON_OVERLAP
THEN
PUBLIC_OUTPUT_QUANTIZATION
```

This binds three frozen tokens for any future implementation:

```text
CLASSIFICATION_BEFORE_PUBLIC_OUTPUT_QUANTIZATION=REQUIRED
BOUNDARY_PREDICATES_USE_UNQUANTIZED_DECIMAL_DERIVATIONS=REQUIRED
PUBLIC_OUTPUT_QUANTIZATION_MUST_NOT_CHANGE_CLASSIFICATION=REQUIRED
```

The discipline is:

1. The TASK-021 already-accepted `x_m` and `y_m` values are accepted as input
   coordinates. They are never re-quantized before TASK-024 derives geometry;
2. Every TASK-024 derived quantity — radius, chord offset, signed distance,
   squared distance, and boundary margin — is computed as a `Decimal` under the
   frozen context above (`precision=50`, `rounding=ROUND_HALF_EVEN`);
3. The following boundary predicates all execute on the unquantized
   high-precision Decimal derivations, and complete before any public output
   quantization step:

   ```text
   s > r_h
   s < -r_h
   s == r_h
   s == -r_h
   -r_h < s < r_h
   d² <= (R - r_h)²
   d²_ij >= (2 * r_h)²
   ```
4. The `coordinate_quantum_m=0.000000000001` value applies only to the public
   output canonicalization step that formats the canonical decimal string of a
   public unit-bearing field. It never applies to the boundary predicates
   above;
5. It is forbidden to first quantize `s`, `r_h`, `d²`, any boundary margin,
   or any chord geometry value and then run classification. Classification
   must operate on unquantized high-precision Decimal;
6. Quantization to the public decimal lexical form must not change a
   classification result. The seven classification outcomes
   `WINDOW`, `CROSSFLOW_REFERENCE`, `TANGENT`, `INTERSECTION`, `OUTSIDE`,
   `OVERLAP`, and any error classification must be byte-identical before and
   after the public output quantization step;
7. Every classification outcome, every warning, and every blocker is derived
   from the unquantized high-precision Decimal predicate evaluation, never
   from a quantized value;
8. Hash projections whose inputs are public geometric values use the
   post-quantization canonical decimal strings for the geometric values
   themselves, but the classification identity — which classification token
   attaches to which position — is fixed by the unquantized predicate pass.

This discipline is closed. No future implementation may reorder these steps,
shorten the precision, or insert a quantization boundary before classification.

### 7.4 Canonical JSON domain

Canonical values may contain only:

- `null`;
- booleans;
- integers;
- canonical decimal strings;
- strings;
- arrays of permitted values;
- objects with string keys and permitted values.

Forbidden values include float, live `Decimal`, bytes, sets, datetime, locale
objects, filesystem metadata, process metadata, runtime-now metadata, and
arbitrary Python objects.

Object keys are lexicographically ordered. Canonical JSON is UTF-8, compact,
and deterministic.

### 7.5 Semantic array ordering

- `spacing_sequence_m` preserves axial semantic order;
- `orientation_sequence` preserves baffle-index order;
- baffles are ordered by `baffle_index`;
- positions within classification outputs are ordered by upstream
  `TubePosition.position_id`;
- pairwise overlap audits use ordered identity pairs
  `(lower_position_id, higher_position_id)`;
- evidence-reference sets are sorted and duplicate-free;
- warnings and blockers use the frozen validation-stage order and then the
  deterministic message sort key.

Semantic arrays are not re-sorted by generic serialized representation.

## 8. Exact domain models

All models are immutable dataclasses with exact field sets. Unknown fields block.
Raw types are checked before coercion.

### 8.1 `CallerSuppliedBaffleAxialSpan`

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact axial-span schema version |
| `axial_start_coordinate_m` | decimal string | finite canonical value |
| `axial_end_coordinate_m` | decimal string | strictly greater than start |
| `evidence_refs` | tuple[string, ...] | non-empty, sorted, duplicate-free |
| `authority_hash` | SHA-256 hex | recomputed from every other field |

The axial coordinate system is a TASK-024 request-local axis:

```text
positive_direction=start_plane_to_end_plane
start_plane=BAFFLE_ACTIVE_SPAN_START_PLANE
end_plane=BAFFLE_ACTIVE_SPAN_END_PLANE
```

These planes do not silently mean tubesheet faces, nozzle centerlines, shell
tangent lines, weld lines, channel faces, or any other physical feature.

### 8.2 `CallerSuppliedBaffleDesignAuthority`

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact design-authority schema version |
| `baffle_type` | `BaffleType` | exact `SINGLE_SEGMENTAL` |
| `baffle_count` | integer | `>= 1`; bool forbidden |
| `baffle_thickness_m` | decimal string | positive |
| `spacing_sequence_m` | tuple[decimal string, ...] | semantic order; every item positive |
| `baffle_cut_fraction` | decimal string | `0 < value < 1` |
| `orientation_sequence` | tuple[`BaffleOrientation`, ...] | length equals baffle count |
| `shell_to_baffle_diametral_clearance_m` | decimal string | non-negative |
| `tube_to_baffle_hole_diametral_clearance_m` | decimal string | non-negative |
| `evidence_refs` | tuple[string, ...] | non-empty, sorted, duplicate-free |
| `authority_hash` | SHA-256 hex | recomputed from every other field |

Every engineering value is caller supplied. The authority object claims no
external standard approval.

### 8.3 `BaffleGeometryRequest`

| Field | Type |
|---|---|
| `schema_version` | string |
| `configuration` | complete `ShellAndTubeConfiguration` |
| `tube_layout` | complete `TubeLayout` |
| `shell_bundle_geometry` | complete `ShellBundleGeometry` |
| `axial_span` | `CallerSuppliedBaffleAxialSpan` |
| `design_authority` | `CallerSuppliedBaffleDesignAuthority` |
| `evidence_refs` | tuple[string, ...] |

The request contains no file path, registry key, catalog query, persistence ID,
clock, locale, or environment lookup instruction.

### 8.4 `CutChordGeometry`

| Field | Type | Meaning |
|---|---|---|
| `normal_x` | integer | one of `-1, 0, 1` |
| `normal_y` | integer | one of `-1, 0, 1` |
| `half_plane_offset_m` | decimal string | `normal·point >= offset` defines window |
| `chord_half_length_m` | decimal string | non-negative |
| `endpoint_a_x_m` | decimal string | deterministic first endpoint |
| `endpoint_a_y_m` | decimal string | deterministic first endpoint |
| `endpoint_b_x_m` | decimal string | deterministic second endpoint |
| `endpoint_b_y_m` | decimal string | deterministic second endpoint |

Endpoint order is fixed:

- horizontal chord: endpoint A has negative x; endpoint B has positive x;
- vertical chord: endpoint A has negative y; endpoint B has positive y.

### 8.5 `TubeHoleClassification`

| Field | Type | Rule |
|---|---|---|
| `position_id` | string | exact TASK-021 identity |
| `center_x_m` | decimal string | exact upstream coordinate |
| `center_y_m` | decimal string | exact upstream coordinate |
| `physical_tube_radius_m` | decimal string | tube OD / 2 |
| `baffle_hole_radius_m` | decimal string | derived hole diameter / 2 |
| `signed_window_distance_m` | decimal string | `normal·center - offset` |
| `cut_boundary_margin_m` | decimal string | positive successful margin |
| `classification` | enum | `WINDOW` or `CROSSFLOW_REFERENCE` |
| `outer_boundary_margin_squared_m2` | decimal string or null | required for covered class |
| `physical_tube_disk_audit` | object | audit only; never classification authority |

The complete baffle-hole clearance disk is the primary cut-classification disk.
The physical tube disk is an audit projection only.

### 8.6 `BafflePlaneGeometry`

| Field | Type |
|---|---|
| `baffle_index` | integer, one-based |
| `center_coordinate_m` | decimal string |
| `occupied_start_coordinate_m` | decimal string |
| `occupied_end_coordinate_m` | decimal string |
| `orientation` | `BaffleOrientation` |
| `cut_chord` | `CutChordGeometry` |
| `window_region_semantics` | exact string token |
| `baffle_covered_region_semantics` | exact string token |
| `crossflow_reference_region_semantics` | exact string token |
| `tube_hole_classifications` | tuple[`TubeHoleClassification`, ...] |
| `window_position_ids` | tuple[string, ...] |
| `crossflow_reference_position_ids` | tuple[string, ...] |
| `outer_tangent_position_ids` | tuple[string, ...] |
| `pairwise_tangent_position_pairs` | tuple[tuple[string, string], ...] |
| `classification_audit_hash` | SHA-256 hex |

Required semantic tokens:

```text
window_region_semantics=BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE
baffle_covered_region_semantics=BAFFLE_DISK_MINUS_WINDOW_SEGMENT
crossflow_reference_region_semantics=CLASSIFICATION_REFERENCE_ONLY_NOT_FLOW_AREA
```

### 8.7 `BaffleGeometry`

| Field | Type |
|---|---|
| `schema_version` | string |
| `geometry_id` | UUID string |
| `geometry_hash` | SHA-256 hex |
| `request_hash` | SHA-256 hex |
| `task020_configuration_id` | string |
| `task020_configuration_hash` | SHA-256 hex |
| `task021_layout_id` | string |
| `task021_layout_hash` | SHA-256 hex |
| `task022_geometry_id` | string |
| `task022_geometry_hash` | SHA-256 hex |
| `construction_family` | exact `FIXED_TUBESHEET` |
| `equipment_orientation` | copied from `ShellBundleGeometry.equipment_orientation` and cross-checked against `ShellAndTubeConfiguration.orientation` and `TubeLayout.equipment_orientation` |
| `shell_pass_count` | exact `1` |
| `tube_pass_count` | positive integer copied upstream |
| `shell_inside_diameter_m` | decimal string |
| `tube_outer_diameter_m` | decimal string |
| `axial_span` | complete axial authority object |
| `design_authority` | complete design authority object |
| `usable_baffle_span_m` | decimal string |
| `baffle_diameter_m` | decimal string |
| `baffle_radius_m` | decimal string |
| `baffle_hole_diameter_m` | decimal string |
| `baffle_hole_radius_m` | decimal string |
| `cut_height_m` | decimal string |
| `chord_offset_from_center_m` | decimal string |
| `baffle_planes` | tuple[`BafflePlaneGeometry`, ...] |
| `position_count` | integer |
| `warnings` | tuple[`MessageEntry`, ...] |
| `blockers` | tuple[`MessageEntry`, ...] |
| `deferred_capabilities` | tuple[string, ...] |
| `provenance` | canonical frozen mapping |

A successful geometry has empty blockers.

### 8.8 `BaffleGeometryValidationResult`

| Field | Type |
|---|---|
| `status` | `VALID` or `BLOCKED` |
| `geometry` | `BaffleGeometry` or null |
| `warnings` | ordered tuple of messages |
| `blockers` | ordered tuple of messages |
| `deferred_capabilities` | frozen tuple |
| `blocked_result_hash` | SHA-256 hex or null |

For `VALID`, `geometry` is non-null and `blocked_result_hash` is null.
For `BLOCKED`, `geometry` is null and `blocked_result_hash` is non-null.

## 9. Deterministic geometry definitions

### 9.1 Axial-span closure

```text
usable_baffle_span_m
=
axial_end_coordinate_m
-
axial_start_coordinate_m
```

Let:

```text
N=baffle_count
S=spacing_sequence_m
```

Required cardinality:

```text
N>=1
len(S)=N+1
```

Semantic sequence:

```text
S[0]=inlet spacing
S[1]..S[N-1]=inter-baffle center-plane spacings
S[N]=outlet spacing
```

Required exact closure:

```text
sum(S)=usable_baffle_span_m
```

No tolerance, padding, truncation, repeated-last-value behavior, or default is
allowed.

### 9.2 Baffle center-plane positions

```text
z_1=axial_start_coordinate_m+S[0]
z_i=z_(i-1)+S[i-1]  for i=2..N
```

The final closure also requires:

```text
axial_end_coordinate_m-z_N=S[N]
```

Every public z coordinate is canonicalized to the coordinate quantum.

### 9.3 Uniform thickness and occupied intervals

For each baffle:

```text
occupied_start_i=z_i-baffle_thickness_m/2
occupied_end_i=z_i+baffle_thickness_m/2
```

Required:

```text
occupied_start_1>=axial_start_coordinate_m
occupied_end_N<=axial_end_coordinate_m
z_(i+1)-z_i>=baffle_thickness_m
```

Equality means mathematical solid tangency and is accepted. It does not claim
fabrication clearance or mechanical adequacy. Accepted equality emits a warning.

### 9.4 Baffle and hole diameters

```text
baffle_diameter_m
=
shell_inside_diameter_m
-
shell_to_baffle_diametral_clearance_m
```

```text
baffle_hole_diameter_m
=
tube_outer_diameter_m
+
tube_to_baffle_hole_diametral_clearance_m
```

```text
baffle_radius_m=baffle_diameter_m/2
baffle_hole_radius_m=baffle_hole_diameter_m/2
physical_tube_radius_m=tube_outer_diameter_m/2
```

Required:

```text
shell_to_baffle_diametral_clearance_m>=0
tube_to_baffle_hole_diametral_clearance_m>=0
baffle_diameter_m>0
baffle_hole_diameter_m>=tube_outer_diameter_m
```

The baffle circle is concentric with the TASK-021/TASK-022 origin `(0,0)`.

### 9.5 Single-segment cut geometry

```text
cut_height_m
=
baffle_cut_fraction*baffle_diameter_m
```

```text
chord_offset_from_center_m
=
baffle_radius_m-cut_height_m
```

Let:

```text
R=baffle_radius_m
c=chord_offset_from_center_m
h=sqrt(R^2-c^2)
```

The window is represented uniformly as:

```text
normal·point>=c
```

Orientation normals:

```text
TOP:    normal=(0, 1)
BOTTOM: normal=(0,-1)
RIGHT:  normal=(1, 0)
LEFT:   normal=(-1,0)
```

Chord endpoints:

```text
TOP/BOTTOM:
  endpoint_a=(-h, normal_y*c)
  endpoint_b=( h, normal_y*c)

LEFT/RIGHT:
  endpoint_a=(normal_x*c,-h)
  endpoint_b=(normal_x*c, h)
```

No polygon approximation, angle approximation, area integration, or
transcendental function is required in TASK-024 v1.

### 9.6 Exact transverse coordinate binding

```text
TASK024_XY_COORDINATE_FRAME=EXACT_TASK021_TUBE_LAYOUT_COORDINATE_FRAME
origin=(0,0)
rotation=NONE
mirroring=NONE
axis_swap=NONE
```

The core consumes exact TASK-021 `x_m` and `y_m`.

### 9.7 Primary cut-boundary classification

For each tube position with center `p=(x,y)`:

```text
s=normal·p-c
r_h=baffle_hole_radius_m
```

Classification is exact:

```text
s> r_h  -> WINDOW
s<-r_h  -> CROSSFLOW_REFERENCE
s==r_h  -> BLOCKED_TANGENT_TO_CUT
s==-r_h -> BLOCKED_TANGENT_TO_CUT
-r_h<s<r_h -> BLOCKED_INTERSECTS_CUT
```

There is no epsilon and no tolerance band.

### 9.8 Covered-region outer containment

Only `CROSSFLOW_REFERENCE` positions require a hole through baffle material.

Let:

```text
d2=x^2+y^2
available_radius=R-r_h
```

Required:

```text
available_radius>=0
d2<=available_radius^2
```

Equality is outer-circle tangency and is accepted as mathematical containment.
It emits a warning and makes no manufacturing claim.

A `WINDOW` position requires no baffle-hole containment check because the
selected window half-plane removes baffle material there. Its physical tube
geometry remains governed by TASK-021 and TASK-022.

### 9.9 Pairwise covered-region hole non-overlap

For every ordered pair of `CROSSFLOW_REFERENCE` positions:

```text
d2_ij=(x_i-x_j)^2+(y_i-y_j)^2
required_separation_squared=(2*r_h)^2
```

Required:

```text
d2_ij>=required_separation_squared
```

Interior overlap blocks. Equality is mathematical tangency, is accepted, emits
a warning, and does not claim manufacturability.

### 9.10 Classification completeness

For every baffle:

- every accepted TASK-021 `position_id` appears exactly once;
- every position is either `WINDOW`, `CROSSFLOW_REFERENCE`, or produces a
  blocker;
- duplicate, missing, or multiply classified identities block;
- a blocked baffle causes the entire request to block;
- no partial `BafflePlaneGeometry` tuple is returned.

### 9.11 Region semantics are not flow areas

```text
WINDOW_REGION_GEOMETRY
=
BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE
```

```text
BAFFLE_COVERED_REGION_GEOMETRY
=
BAFFLE_DISK_MINUS_WINDOW_REGION_GEOMETRY
```

```text
CROSSFLOW_REFERENCE_REGION_GEOMETRY
=
BAFFLE_COVERED_REGION_GEOMETRY
```

The last name is permitted only as a classification reference for future tasks.
None of these values represents shell-side free-flow area, minimum crossflow
area, hydraulic area, Kern area, or Bell–Delaware area.

## 10. Validation stages and no-partial-result behavior

Validation runs in this exact stage order:

1. request schema version, exact field set, and raw types;
2. complete TASK-020 configuration validation;
3. complete TASK-021 layout validation;
4. complete TASK-022 geometry validation;
5. three-way upstream identity and semantic cross-binding;
6. supported v1 construction family, shell-pass count, and baffle type;
7. axial authority schema, evidence, and authority hash;
8. baffle-design authority schema, evidence, and authority hash;
9. canonical decimal parsing and sign/domain validation;
10. count, spacing, orientation cardinality, and axial closure;
11. baffle diameter, hole diameter, radius, and cut derivation;
12. axial center-plane and solid-interval construction;
13. chord construction;
14. per-baffle cut classification;
15. covered-region outer containment;
16. pairwise covered-region hole non-overlap;
17. classification completeness;
18. canonical serialization, hashes, IDs, provenance, and final result.

Each stage may accumulate every deterministic blocker in that stage. Later
geometry stages do not execute when required inputs are invalid.

Any blocker yields:

```text
status=BLOCKED
geometry=null
blocked_result_hash=<deterministic hash>
```

Warnings may coexist with a valid result. Blockers never coexist with a partial
geometry.

## 11. Closed blocker taxonomy

The v1 blocker codes are:

```text
BFG_SCHEMA_VERSION_UNSUPPORTED
BFG_UNKNOWN_FIELD
BFG_RAW_TYPE_INVALID
BFG_DECIMAL_LEXICAL_INVALID

BFG_TASK020_CONFIGURATION_MISSING
BFG_TASK020_CONFIGURATION_INVALID
BFG_TASK020_CONFIGURATION_IDENTITY_MISMATCH

BFG_TASK021_LAYOUT_MISSING
BFG_TASK021_LAYOUT_INVALID
BFG_TASK021_LAYOUT_HAS_BLOCKERS
BFG_TASK021_LAYOUT_IDENTITY_MISMATCH
BFG_TASK021_LAYOUT_HAS_NO_POSITIONS

BFG_TASK022_GEOMETRY_MISSING
BFG_TASK022_GEOMETRY_INVALID
BFG_TASK022_GEOMETRY_HAS_BLOCKERS
BFG_TASK022_GEOMETRY_IDENTITY_MISMATCH

BFG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH
BFG_UPSTREAM_LAYOUT_BINDING_MISMATCH
BFG_UPSTREAM_TUBE_GEOMETRY_BINDING_MISMATCH
BFG_UPSTREAM_CONSTRUCTION_FAMILY_MISMATCH
BFG_UPSTREAM_ORIENTATION_MISMATCH
BFG_UPSTREAM_PASS_COUNT_MISMATCH
BFG_UPSTREAM_POSITION_COUNT_MISMATCH

BFG_CONSTRUCTION_FAMILY_UNSUPPORTED
BFG_SHELL_PASS_COUNT_UNSUPPORTED
BFG_BAFFLE_TYPE_UNSUPPORTED

BFG_AXIAL_SPAN_MISSING
BFG_AXIAL_SPAN_SCHEMA_UNSUPPORTED
BFG_AXIAL_SPAN_EVIDENCE_MISSING
BFG_AXIAL_SPAN_AUTHORITY_HASH_MISMATCH
BFG_AXIAL_SPAN_INVALID

BFG_DESIGN_AUTHORITY_MISSING
BFG_DESIGN_AUTHORITY_SCHEMA_UNSUPPORTED
BFG_DESIGN_AUTHORITY_EVIDENCE_MISSING
BFG_DESIGN_AUTHORITY_HASH_MISMATCH

BFG_BAFFLE_COUNT_INVALID
BFG_BAFFLE_THICKNESS_INVALID
BFG_SPACING_SEQUENCE_CARDINALITY_MISMATCH
BFG_SPACING_VALUE_INVALID
BFG_SPACING_SEQUENCE_SPAN_MISMATCH
BFG_ORIENTATION_SEQUENCE_CARDINALITY_MISMATCH
BFG_ORIENTATION_TOKEN_INVALID
BFG_BAFFLE_CUT_INVALID
BFG_SHELL_TO_BAFFLE_CLEARANCE_INVALID
BFG_TUBE_TO_BAFFLE_HOLE_CLEARANCE_INVALID

BFG_BAFFLE_DIAMETER_INVALID
BFG_BAFFLE_HOLE_DIAMETER_INVALID
BFG_BAFFLE_THICKNESS_OUTSIDE_ACTIVE_SPAN
BFG_BAFFLE_SOLIDS_OVERLAP
BFG_CHORD_CALCULATION_FAILED

BFG_BAFFLE_HOLE_DISK_TANGENT_TO_CUT_BOUNDARY
BFG_BAFFLE_HOLE_DISK_INTERSECTS_CUT_BOUNDARY
BFG_BAFFLE_HOLE_OUTSIDE_COVERED_REGION
BFG_BAFFLE_HOLE_DISKS_OVERLAP
BFG_POSITION_CLASSIFICATION_INCOMPLETE

BFG_CANONICALIZATION_FAILED
```

Codes are exact and cannot be aliased.

## 12. Closed warning taxonomy

```text
BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM
BFG_GEOMETRY_NOT_FLOW_AREA
BFG_FIXED_TUBESHEET_ONLY_V1
BFG_NOZZLE_POSITION_DEFERRED
BFG_THERMAL_HYDRAULIC_DEFERRED
BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY
BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY
BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY
```

Required baseline warnings on every valid v1 result:

```text
BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM
BFG_GEOMETRY_NOT_FLOW_AREA
BFG_FIXED_TUBESHEET_ONLY_V1
BFG_NOZZLE_POSITION_DEFERRED
BFG_THERMAL_HYDRAULIC_DEFERRED
```

Tangency warnings are emitted only when their exact equality condition occurs.

## 13. Message ordering

Every message has:

| Field | Type |
|---|---|
| `code` | string |
| `field_path` | string or null |
| `message_key` | string |
| `evidence_refs` | tuple[string, ...] |
| `details` | canonical mapping or null |

Messages sort by:

```text
(
  validation_stage_rank,
  code,
  field_path_or_empty,
  message_key,
  sha256(canonical_details),
  sha256(canonical_evidence_refs)
)
```

Stage rank is bound to the occurrence when the message is created. It is not
reconstructed from code alone.

## 14. Hashes, UUID identity, and canonical projections

### 14.1 Authority hashes

`authority_hash` for each caller authority is SHA-256 of canonical JSON
containing every field except `authority_hash`.

### 14.2 Request hash

`request_hash` is SHA-256 of the canonical complete request, including:

- the complete validated TASK-020 configuration;
- the complete validated TASK-021 layout;
- the complete validated TASK-022 geometry;
- complete axial-span authority;
- complete baffle-design authority;
- request evidence references.

No runtime metadata is included.

### 14.3 Classification audit hash

Each `classification_audit_hash` covers:

- baffle index and orientation;
- chord geometry;
- every `TubeHoleClassification` in deterministic position order;
- window and crossflow-reference identity arrays;
- outer tangency identities;
- pairwise tangency identity pairs.

### 14.4 Geometry hash

`geometry_hash` is SHA-256 of canonical JSON containing every `BaffleGeometry`
field except:

```text
geometry_id
geometry_hash
```

Warnings, blockers, deferred capabilities, complete authority objects, upstream
identity fields, baffle planes, and provenance are included.

### 14.5 Geometry UUID

```text
UUID_NAMESPACE=uuid.NAMESPACE_URL
GEOMETRY_URN_PREFIX=urn:hxforge:task024:baffle-geometry:v1:
geometry_id=uuid5(UUID_NAMESPACE, GEOMETRY_URN_PREFIX+geometry_hash)
```

### 14.6 Blocked result hash

The blocked-result hash covers:

- exact request hash when computable;
- otherwise the canonical raw request projection;
- ordered warnings;
- ordered blockers;
- deferred capabilities;
- profile ID and design contract path.

Two identical invalid requests must produce identical blocked-result hashes.

## 15. Provenance contract

A valid result provenance mapping includes at least:

```text
task_id
design_contract_path
profile_id
software_version
git_commit

task020_configuration_id
task020_configuration_hash
task020_case_authority

task021_layout_id
task021_layout_hash
task021_tube_geometry_snapshot_hash
task021_layout_rule_snapshot_hash

task022_geometry_id
task022_geometry_hash
task022_shell_authority_mode
task022_shell_authority_identity
task022_geometry_rule_snapshot_hash

axial_span_authority_hash
baffle_design_authority_hash
request_hash

source_claim_status=NO_STANDARD_CLAIM
automatic_selection_performed=false
nozzle_position_inference_performed=false
flow_area_calculation_performed=false

warnings
deferred_capabilities
```

Provenance is a detached immutable canonical snapshot. Caller mutation after
construction cannot alter any hash or result.

## 16. Public operation

The future core exposes one public calculation operation:

```python
validate_request(
    request: BaffleGeometryRequest,
) -> BaffleGeometryValidationResult
```

This operation:

- is pure and in-memory;
- performs no lookup;
- performs no catalog scan;
- performs no alternative ranking;
- mutates no input;
- returns no exception for ordinary invalid engineering input;
- converts expected validation failures to structured blockers;
- returns no partial geometry.

Programmer misuse and impossible internal invariants may raise narrow internal
exceptions, but the public boundary converts all contract-defined failures into
the closed blocker taxonomy.

No loader, path-based parser, database adapter, registry, persistence service,
CLI, report renderer, API endpoint, optimizer, or rule-pack adapter is part of
TASK-024 v1.

## 17. Architecture and forbidden I/O boundary

The future package must be deterministic under process, host, locale, and clock
variation.

Forbidden in the calculation path:

```text
filesystem reads or writes
network access
database access
environment-variable access
registry access
system clock or current date
host locale
randomness
process ID
thread scheduling as semantic input
dynamic import
plugin discovery
eval or exec
pickle or executable deserialization
subprocess
new third-party geometry dependency
binary floating-point geometry
```

Only immutable supplied objects and standard-library deterministic math are
permitted.

No Shapely or other computational-geometry dependency is required. The v1
geometry uses circles, half-planes, squared-distance comparisons, and Decimal
square root only.

## 18. Future implementation repository allowlist

A later separate implementation authorization may modify only:

```text
src/hexagent/exchangers/shell_tube/baffle_geometry/__init__.py
src/hexagent/exchangers/shell_tube/baffle_geometry/models.py
src/hexagent/exchangers/shell_tube/baffle_geometry/canonical.py
src/hexagent/exchangers/shell_tube/baffle_geometry/schema.py
src/hexagent/exchangers/shell_tube/baffle_geometry/authority.py
src/hexagent/exchangers/shell_tube/baffle_geometry/geometry.py
src/hexagent/exchangers/shell_tube/baffle_geometry/validation.py

tests/exchangers/shell_tube/baffle_geometry/_builders.py
tests/exchangers/shell_tube/baffle_geometry/test_models.py
tests/exchangers/shell_tube/baffle_geometry/test_schema.py
tests/exchangers/shell_tube/baffle_geometry/test_authority.py
tests/exchangers/shell_tube/baffle_geometry/test_geometry.py
tests/exchangers/shell_tube/baffle_geometry/test_validation.py
tests/exchangers/shell_tube/baffle_geometry/test_architecture.py

ci-shard-manifest.yml
```

The future CI-manifest amendment is limited to exactly six test-module entries:

```text
test_models.py
test_schema.py
test_authority.py
test_geometry.py
test_validation.py
test_architecture.py
```

Required manifest delta:

```text
+6 insertions
-0 deletions
```

`_builders.py` is support code and receives no manifest entry.

This allowlist does not itself authorize implementation.

## 19. Required future test matrix

### 19.1 Happy paths

At minimum:

1. one fixed-tubesheet, one-shell-pass, one-baffle request;
2. multiple baffles with exact axial closure;
3. every orientation token;
4. cut fraction below, equal to, and above `0.5` while remaining in domain;
5. all tubes in window;
6. all tubes in crossflow reference;
7. mixed classifications;
8. accepted outer-circle tangency;
9. accepted pairwise hole tangency;
10. accepted axial solid tangency;
11. deterministic rerun equality;
12. input mutation after construction cannot alter result.

### 19.2 Schema and raw-type negatives

- unknown fields at every public layer;
- wrong schema versions;
- bool supplied as integer;
- float supplied as decimal;
- exponent notation;
- NaN/Infinity;
- tuple/list shape mismatches;
- duplicate evidence refs;
- missing authority objects;
- malformed hashes.

### 19.3 Upstream binding negatives

- invalid TASK-020 hash or ID;
- invalid TASK-021 hash or ID;
- invalid TASK-022 hash or ID;
- upstream blockers;
- mismatched configuration binding;
- mismatched layout binding;
- mismatched tube geometry snapshot;
- mismatched construction family;
- mismatched orientation;
- mismatched shell or tube pass count;
- mismatched position count.

### 19.4 Supported-slice negatives

- floating-head configuration;
- U-tube configuration;
- shell-pass count other than one;
- unknown baffle type;
- alias or lowercase enum tokens.

### 19.5 Axial and spacing negatives

- zero baffle count;
- negative count;
- wrong sequence cardinality;
- zero or negative spacing;
- sum below span;
- sum above span;
- first or last solid outside active span;
- overlapping baffle solids;
- invalid thickness.

### 19.6 Transverse geometry negatives

- invalid shell-to-baffle clearance;
- invalid tube-to-hole clearance;
- non-positive derived baffle diameter;
- invalid cut fraction;
- hole disk tangent to cut line;
- hole disk intersects cut line;
- covered hole outside baffle disk;
- covered holes overlap;
- incomplete or duplicate classification.

### 19.7 Canonical and architecture tests

- stable request, authority, audit, geometry, and blocked hashes;
- stable UUIDv5 geometry ID;
- canonical zero behavior;
- exact message ordering;
- no float in public projections;
- no filesystem, network, DB, environment, clock, locale, random, subprocess,
  dynamic import, or third-party geometry dependency;
- exact implementation path allowlist;
- exact CI-manifest delta;
- global collection and merge-ref collection.

### 19.8 Quantization-discipline tests

At minimum, the future implementation must demonstrate the following design
tests pass. The values used in these tests are design-only synthetic values;
they are not engineering recommendations.

1. value just above cut tangency before quantization remains `WINDOW` after
   the public output quantization step;
2. value just below cut tangency before quantization remains `INTERSECTION`
   or `CROSSFLOW_REFERENCE` as mathematically applicable after the public
   output quantization step;
3. public quantization collision cannot alter classification — the seven
   classification outcomes
   `WINDOW`, `CROSSFLOW_REFERENCE`, `TANGENT`, `INTERSECTION`, `OUTSIDE`,
   `OVERLAP`, and any error classification must be byte-identical before
   and after the public output quantization step;
4. outer-containment decision occurs before public quantization — the
   `d² <= (R - r_h)²` predicate is evaluated on the unquantized Decimal
   derivation, and the resulting containment token is not re-derived from
   any quantized value;
5. pairwise-overlap decision occurs before public quantization — the
   `d²_ij >= (2 * r_h)²` predicate is evaluated on the unquantized Decimal
   derivation, and the resulting overlap token is not re-derived from any
   quantized value;
6. binary float remains forbidden — every input coordinate, every derived
   radius, every chord offset, every signed distance, every squared
   distance, and every boundary margin that participates in any predicate
   above is a `Decimal` under the frozen context (`precision=50`,
   `rounding=ROUND_HALF_EVEN`). A `float` value at any of these positions
   fails the test.

## 20. Future implementation acceptance gates

A future implementation is acceptable only if:

```text
EXACT_BASE_MAIN_BOUND
EXACT_ALLOWLIST_ONLY
NO_UPSTREAM_CONTRACT_MUTATION
NO_NEW_DEPENDENCY
NO_STANDARD_OR_VENDOR_TABLE_CONTENT
NO_HIDDEN_DEFAULTS
NO_PARTIAL_RESULT
ALL_FOCUSED_TESTS_PASS
ALL_ARCHITECTURE_TESTS_PASS
CI_MANIFEST_DELTA_EXACT
GLOBAL_COLLECTION_PASS
RUFF_PASS
FORMAT_CHECK_PASS
MYPY_PASS
GIT_DIFF_CHECK_PASS
PR_HEAD_CI_SUCCESS
```

Implementation, Draft PR, Ready transition, merge, Issue close, and branch
deletion each require separate Charles authorization.

## 21. Design-review checklist

A design reviewer must verify:

1. exact base and single-file scope;
2. complete upstream value-object consumption;
3. no reopening of TASK-020, TASK-021, TASK-022, or TASK-023;
4. caller authority is not mislabeled as a TASK-012 source class;
5. v1 closed sets are exact;
6. spacing cardinality and axial closure are unambiguous;
7. complete hole-clearance disk is the primary cut classifier;
8. window/covered/reference region names do not claim flow area;
9. outer containment and pairwise non-overlap are exact;
10. tangency semantics are explicit and non-mechanical;
11. no nozzle inference;
12. no thermal/hydraulic scope leakage;
13. blocker and warning taxonomies are closed;
14. hashes and UUID projections are exact;
15. architecture forbids external state and third-party geometry;
16. future implementation allowlist and CI delta are exact;
17. TASK-025 through TASK-039 remain unallocated;
18. quantization ordering discipline is closed: classification, tangency,
    intersection, outer-containment, and pairwise non-overlap all execute on
    unquantized high-precision Decimal derivations, and only the public
    output canonicalization step quantizes to the public decimal lexical
    form. `coordinate_quantum_m=0.000000000001` applies only to that step.

## 22. Explicit non-authorization statement

This design contract does not authorize:

```text
IMPLEMENTATION
PRODUCTION_CODE
TEST_CODE
FIXTURES
CI_MANIFEST_MUTATION
WORKFLOW_MUTATION
DEPENDENCY_MUTATION
LOCKFILE_MUTATION
DRAFT_PR
READY_FOR_REVIEW
MERGE
ISSUE_155_MUTATION
ISSUE_155_CLOSE
BRANCH_DELETION

PRODUCTION_BAFFLE_DATA
STANDARD_TABLE_CONTENT
VENDOR_TABLE_CONTENT
AUTOMATIC_BAFFLE_SELECTION
FLOW_AREA_CALCULATION
THERMAL_RATING
KERN
BELL_DELAWARE
PRESSURE_DROP
VIBRATION
MECHANICAL_DESIGN
MANUFACTURING_ADEQUACY
MATERIAL_SELECTION
MASS
COST
OPTIMIZATION
API
PERSISTENCE
CLI
REPORT
GOLDEN_INTEGRATION

TASK025_THROUGH_TASK039_ALLOCATION
```

The next independent gate after one-file authoring completion is:

```text
AUTHORIZE_TASK024_MINIMAL_COMPUTE_V1_DESIGN_REVIEW_ONLY
```

That gate may review this design branch and this file only. It must not create a
pull request, modify the design file, start implementation, mutate Issue #155,
or allocate a later task.
