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

The TASK-024 identity-and-provenance binding for equipment orientation uses
three upstream fields, all of which must agree:

- `ShellAndTubeConfiguration.orientation`  (the TASK-020 field)
- `TubeLayout.equipment_orientation`         (the TASK-021 field)
- `ShellBundleGeometry.equipment_orientation` (the TASK-022 field)

The upstream field literally named `equipment_orientation` exists only on
`TubeLayout` and `ShellBundleGeometry`; it does NOT exist on
`ShellAndTubeConfiguration`. The corresponding TASK-020 field is named
`orientation`. TASK-024 cross-checks that all three values are equal.

The bound `equipment_orientation` value is used **only** for identity
binding and the provenance mapping. It must never be used to derive:

- gravity semantics (top, bottom, side);
- nozzle position;
- baffle cut orientation;
- installation adequacy.

The baffle cut orientation is selected exclusively by the dedicated
`BaffleOrientation` input from the caller (the orientation sequence over
baffles), never by `equipment_orientation`.

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
squared_coordinate_quantum_m2=0.000000000000000000000001
canonical_zero=0
```

All arithmetic uses `Decimal` under this context. `sqrt` uses the Decimal square
root under the same context. The squared-output quantum is not an independent
engineering value; it is exactly `coordinate_quantum_m * coordinate_quantum_m`.

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

### 7.6 Total raw-value projection for blocked requests

A blocked result must remain deterministic even when the ordinary validated
`request_hash` cannot be computed. TASK-024 therefore freezes one total,
non-executable diagnostic projection:

```text
RAW_BLOCKED_PROJECTION_VERSION=task024.raw-blocked-projection.v3
```

The projection is used only for `blocked_result_hash`. It never authorizes a raw
value, never repairs a request, and never enters a successful geometry. The
underlying invalid value still emits its ordinary blocker, including
`BFG_RAW_TYPE_INVALID` where applicable.

The recursive tagged-value mapping is exact:

| Python/raw value | Canonical tagged projection |
|---|---|
| `None` | `{"raw_type":"null"}` |
| `bool` | `{"raw_type":"bool","value":<JSON boolean>}` |
| exact `int` (arbitrary magnitude; `bool` excluded) | `{"raw_type":"int","sign":<0-or-1>,"magnitude_hex":<lowercase hexadecimal digits, no 0x prefix>}` |
| exact `str` | `{"raw_type":"str","code_points":[<lowercase hexadecimal ordinals>]}` preserving code-point order |
| exact finite `float` | `{"raw_type":"float","value":<lowercase float.hex()>}` |
| exact float NaN | `{"raw_type":"float","value":"nan"}` |
| exact float positive infinity | `{"raw_type":"float","value":"+infinity"}` |
| exact float negative infinity | `{"raw_type":"float","value":"-infinity"}` |
| exact `Decimal` | `{"raw_type":"decimal","sign":<0-or-1>,"digits":[<integer digit 0 through 9>,...],"exponent":<closed exponent projection>}` |
| exact `bytes` | `{"raw_type":"bytes","hex":<lowercase hex>}` |
| exact built-in `list` | `{"raw_type":"list","items":[...]}` preserving order |
| exact built-in `tuple` | `{"raw_type":"tuple","items":[...]}` preserving order |
| exact built-in `dict` | `{"raw_type":"mapping","entries":[...]}` under the ordering rule below |
| exact built-in `set` | `{"raw_type":"set","items":[...]}` under the ordering rule below |
| exact built-in `frozenset` | `{"raw_type":"frozenset","items":[...]}` under the ordering rule below |
| enum member | `{"raw_type":"enum","enum_type_token":<literal static ASCII enum token>,"member_token":<literal static ASCII member token>}` |
| recognized TASK-020/021/022/024 public dataclass | `{"raw_type":"dataclass","dataclass_type_token":<literal static ASCII dataclass token>,"fields":[...]}` in the static field-table order |
| every other object | `{"raw_type":"unsupported_object"}` |

### 7.6.1 Integer projection (arbitrary magnitude)

Only an exact `int` after `type(value) is int` projects to:

```text
{
"raw_type":"int",
"sign":<0-or-1>,
"magnitude_hex":<lowercase hexadecimal digits, no 0x prefix>
}
```

Canonical rules after that exact-type guard:

- `value == 0` → `sign=0`, `magnitude_hex="0"`.
- `value > 0` → `sign=0`, `magnitude_hex = int.__format__(value, "x")`.
- `value < 0` → `sign=1`, `magnitude_hex = int.__format__(-value, "x")`.

The frozen tokens are:

```text
RAW_INTEGER_PROJECTION_USES_BASE10_STR=FORBIDDEN
RAW_INTEGER_PROJECTION_MUTATES_INT_MAX_STR_DIGITS=FORBIDDEN
RAW_INTEGER_PROJECTION_IS_TOTAL_FOR_ARBITRARY_MAGNITUDE=REQUIRED
```

Forbidden calls in the projection path: `str(huge_int)`, `repr(huge_int)`,
`sys.set_int_max_str_digits`, and any reading of `PYTHONINTMAXSTRDIGITS`.
The magnitude-hex projection is total for arbitrary-magnitude integers
including those whose base-10 expansion exceeds any interpreter's
default int-to-str digit limit.

#### 7.6.2 Exact-type dispatch and static recognized-type tables

The raw projector is fail-closed and may inspect no runtime type metadata or
execute user code. It first obtains only:

```text
value_type = type(value)
```

Every known-type comparison uses exact identity:

```text
value_type is EXACT_KNOWN_TYPE
```

The projector must not use `isinstance`, `issubclass`,
`dataclasses.is_dataclass`, `hasattr`, `getattr` on unsupported objects, `vars`,
`object.__dict__` inspection, type-object hashing or equality dispatch, runtime
registry discovery, or runtime type metadata. It must not use an arbitrary
`value_type` as a dictionary key: a custom metaclass may control type-object hash
or equality. Static known-type tables are searched only by a bounded identity
sequence:

```text
for entry in STATIC_ENTRIES:
    if value_type is entry.type_object:
        ...
```

The exact scalar domain is closed:

```text
value is None
or type(value) is bool
or type(value) is int
or type(value) is str
or type(value) is float
or type(value) is Decimal
or type(value) is bytes
```

Scalar subclasses are never entered into scalar projection. `int`, `str`,
`float`, `bytes`, and `Decimal` subclasses—including subclasses overriding
`__abs__`, `__format__`, `__str__`, `__repr__`, `hex`, `as_tuple`, iteration,
or conversion—project directly to `{"raw_type":"unsupported_object"}` and
none of those methods may be called.

Exact `int` projection uses only the closed semantics below:

```text
if value == 0:
    sign = 0
    magnitude_hex = "0"
elif value > 0:
    sign = 0
    magnitude_hex = int.__format__(value, "x")
else:
    sign = 1
    magnitude_hex = int.__format__(-value, "x")
```

The `type(value) is int` guard precedes these operations. Base-10 string
conversion and mutation of `int_max_str_digits` are forbidden; arbitrary
magnitude is total. Exact `float` uses `float.hex(value)` for finite values and
signed zero, with fixed tokens for NaN and positive/negative Infinity. Exact
`str` uses ordered lowercase hexadecimal `ord(value)` code points. Exact
`bytes` uses `bytes.hex(value)`. These are static built-in operations, never
instance-dispatch operations.

Exact `Decimal` projection is:

```text
{
  "raw_type":"decimal",
  "sign":<0-or-1>,
  "digits":[<integer digit 0 through 9>, ...],
  "exponent":<closed exponent projection>
}
```

It reads only `Decimal.as_tuple(value)`. A finite exponent is:

```text
{"kind":"integer","sign":<0-or-1>,"magnitude_hex":<lowercase hexadecimal digits>}
```

A special exponent is one of:

```text
{"kind":"special","token":"F"|"n"|"N"}
```

No `str(exponent)`, `repr(exponent)`, `str(value)`, or `repr(value)` is used.
If the exact `Decimal.as_tuple()` result is outside this closed domain, the
fixed result is `{"raw_type":"decimal_projection_unavailable"}` and no
serialization exception escapes.

Only exact built-in `list`, `tuple`, `dict`, `set`, and `frozenset` enter
container traversal. Container subclasses, custom mappings, and arbitrary
iterables directly project to `{"raw_type":"unsupported_object"}` without
iteration. Existing exact built-in ordering and cycle-collapse rules remain,
but pre-scan uses the same exact-type dispatch.

Recognized enums use a code-internal static table. Each entry contains the
exact enum type object, a literal ASCII `enum_type_token`, and ordered exact
member-object identities paired with literal ASCII `member_token` values.
Matching is only `value_type is entry.type_object`, followed by
`value is member_entry.member_object`. Output is:

```text
{
  "raw_type":"enum",
  "enum_type_token":<literal static ASCII enum token>,
  "member_token":<literal static ASCII member token>
}
```

Tokens have the frozen form `<owning-task-lowercase>:<literal-public-type-name>`
(for example `task020:Orientation`, `task021:AxisOrientation`,
`task022:ShellInsideDiameterAuthorityMode`, and `task024:BaffleOrientation`).
These are code literals and are never generated from runtime class metadata. If
a recognized enum instance matches no static member identity, output is:

```text
{"raw_type":"recognized_enum_unavailable","enum_type_token":<literal static token>}
```

Recognized dataclasses use a code-internal static table. Each entry contains the
exact class object, a literal ASCII `dataclass_type_token`, and an exact ordered
literal field-name tuple. The table is limited to §8 TASK-024 public dataclasses
and the TASK-020/021/022 complete upstream object graph explicitly named by §5;
future dataclasses are not discovered automatically. Matching uses only
`value_type is entry.type_object`. Field reads use only
`object.__getattribute__(value, literal_field_name)` for names from that static
table. Output is:

```text
{
  "raw_type":"dataclass",
  "dataclass_type_token":<literal static token>,
  "fields":[
    {"name":<literal static field name>,"value":raw_value_projection(field_value)},
    ...
  ]
}
```

A failed static field read returns
`{"raw_type":"recognized_dataclass_unavailable","dataclass_type_token":<literal static token>}`
for the whole dataclass and reads no other fields. Architecture tests prove
that every recognized field set contains no property, custom data descriptor,
or custom `__getattribute__` dependency.

All other values collapse to the fixed token
`{"raw_type":"unsupported_object"}`. Unsupported-object projection does not
include runtime type identity, state, class metadata, metaclass descriptors,
custom hash, custom equality, or custom representation. Different unsupported
types may share this diagnostic identity. This does not affect successful-result
identity because unsupported values occur only in blocked results.

The frozen dispatch tokens are:

```text
RAW_PROJECTION_DISPATCH_USES_EXACT_TYPE_IDENTITY=REQUIRED
RAW_PROJECTION_ISINSTANCE_DISPATCH=FORBIDDEN
RAW_PROJECTION_RUNTIME_TYPE_METADATA_READ=FORBIDDEN
RAW_PROJECTION_USER_CODE_EXECUTION=FORBIDDEN
RAW_SCALAR_DISPATCH_EXACT_BUILTIN_ONLY=REQUIRED
RAW_SCALAR_SUBCLASS_EXECUTION=FORBIDDEN
UNSUPPORTED_OBJECT_RUNTIME_TYPE_IDENTITY_INCLUDED=NO
UNSUPPORTED_OBJECT_STATE_INSPECTION=FORBIDDEN
UNSUPPORTED_OBJECTS_MAY_SHARE_DIAGNOSTIC_IDENTITY=YES
```

#### 7.6.3 Container and ordering rules

For an exact built-in dict, every entry is represented as:

```text
{
  "key": raw_value_projection(key),
  "value": raw_value_projection(value)
}
```

Entries sort by:

```text
(
  canonical_json_bytes(key_projection),
  canonical_json_bytes(value_projection)
)
```

Set and frozenset items sort by their canonical projection bytes. A raw string
is represented by lowercase hexadecimal Unicode code-point ordinals, so even a
Python string containing an unpaired surrogate has an ASCII-only total
projection. The projector accepts only the exact built-in container types listed
above; container subclasses and custom mappings are `unsupported_object` and
are never iterated. It never uses `repr`, `str(object)`, memory address, object
ID, hash randomization, locale, or iteration order of an unordered collection.

A pre-scan traverses only exact supported containers and recognized public
dataclass fields from the static table. If a reference cycle exists in that
traversed graph, the entire raw value component is represented by the exact token:

```text
{"raw_type":"cyclic_graph"}
```

This deliberate collapse is diagnostic only. State inside an unsupported object
is deliberately not inspected. These projections may group different invalid
programmer objects into the same diagnostic identity; they do not weaken
successful-result identity because they can occur only in a blocked result.

The complete fallback request projection is:

```text
{
  "projection_version": "task024.raw-blocked-projection.v3",
  "request": raw_value_projection(raw_request)
}
```

This function is total for the public validation boundary without invoking
user-defined iteration, conversion, representation, or serialization methods.
Float, NaN, Infinity, exact Decimal, bytes, exact built-in containers, malformed
exact containers, wrong raw types, cyclic graphs, surrogate-containing strings,
custom mappings, container subclasses, scalar subclasses, unsupported objects,
arbitrary-magnitude integers, custom type metadata, and user-defined metaclass
attributes therefore produce a deterministic blocked hash rather than a
serialization exception. No projected invalid value is coerced into a valid
engineering input.

#### 7.6.4 Required test matrix additions

The future test matrix in §19 must cover every Round 5 exact-dispatch,
no-user-code, static enum/dataclass, unsupported-collapse, Decimal special-value,
and process/hash-seed/locale/`int_max_str_digits` stability case frozen in
§19.11. Every case must produce a deterministic blocked hash without a
serialization exception.

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

### 8.5 `PhysicalTubeDiskAudit`

This audit has an exact closed field set:

| Field | Type | Rule |
|---|---|---|
| `physical_tube_radius_m` | decimal string | `tube_outer_diameter_m / 2` |
| `signed_window_distance_m` | decimal string | same quantized public `s` as the parent classification |
| `cut_boundary_margin_m` | decimal string | non-negative public quantized physical-disk margin; its unquantized source is strictly positive and public zero does not mean tangency |
| `classification` | `TubeRegionClassification` | exactly equal to the parent primary classification |

Unknown fields block. The audit is created only after the baffle-hole clearance
disk has classified successfully. Because `baffle_hole_radius_m >=
physical_tube_radius_m`, a successful primary classification guarantees the
physical tube disk is wholly in the same region. This audit never changes,
overrides, or substitutes for the baffle-hole clearance-disk authority.

### 8.6 `TubeHoleClassification`

| Field | Type | Rule |
|---|---|---|
| `position_id` | string | exact TASK-021 identity |
| `center_x_m` | decimal string | exact upstream coordinate |
| `center_y_m` | decimal string | exact upstream coordinate |
| `physical_tube_radius_m` | decimal string | tube OD / 2 |
| `baffle_hole_radius_m` | decimal string | derived hole diameter / 2 |
| `signed_window_distance_m` | decimal string | `normal·center - offset` |
| `cut_boundary_margin_m` | decimal string | non-negative public quantized margin; its unquantized source is strictly positive and public zero does not mean tangency |
| `classification` | enum | `WINDOW` or `CROSSFLOW_REFERENCE` |
| `outer_boundary_margin_squared_m2` | decimal string | non-negative canonical squared-metre decimal string; required for every successful `WINDOW` and every successful `CROSSFLOW_REFERENCE` classification; formula `(R-r_h)^2-d2` |
| `physical_tube_disk_audit` | `PhysicalTubeDiskAudit` | exact closed audit; never classification authority |

The exact field definition is:

```text
Field:
outer_boundary_margin_squared_m2
Type:
decimal string
Nullable:
NO
Required:
for every successful WINDOW classification
and
for every successful CROSSFLOW_REFERENCE classification
Formula:
(R-r_h)^2-d2
Public domain:
non-negative canonical squared-metre decimal string
```

The frozen outer-margin contract is:

```text
OUTER_BOUNDARY_MARGIN_NULLABLE=NO
OUTER_BOUNDARY_MARGIN_REQUIRED_FOR_ALL_SUCCESSFUL_PRIMARY_CLASSES=YES
BLOCKED_REQUEST_NO_PARTIAL_CLASSIFICATION_OBJECT=REQUIRED
```


The `TubeHoleClassification` object is constructed only after the position has
a successful primary classification (`WINDOW` or `CROSSFLOW_REFERENCE`) and
has passed outer-circle containment. Any blocked request returns no partial
classification object.

The complete baffle-hole clearance disk is the primary cut-classification disk.
The physical tube disk is an audit projection only.

### 8.7 `BafflePlaneGeometry`

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

### 8.8 `BaffleGeometry`

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

### 8.9 `BaffleGeometryValidationResult`

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

#### 9.7.1 Successful classification margins and physical-tube audit

All formulas in this subsection are evaluated on unquantized precision-50
Decimal values after the primary classification predicates have succeeded.
Let:

```text
r_t=physical_tube_radius_m
```

The exact primary clearance-disk cut margin is:

```text
WINDOW:
  cut_boundary_margin_m_unquantized=s-r_h

CROSSFLOW_REFERENCE:
  cut_boundary_margin_m_unquantized=-r_h-s
```

The exact physical-tube audit margin is:

```text
WINDOW:
  physical_cut_boundary_margin_m_unquantized=s-r_t

CROSSFLOW_REFERENCE:
  physical_cut_boundary_margin_m_unquantized=-r_t-s
```

Every successful **unquantized** cut margin is strictly positive. The physical
audit classification must exactly equal the primary classification. The public
`signed_window_distance_m`, primary `cut_boundary_margin_m`, physical-audit
`signed_window_distance_m`, and physical-audit `cut_boundary_margin_m` are
formatted only after these predicates and formulas complete, using
`coordinate_quantum_m`.

The public margin domain is deliberately different from the unquantized
predicate domain:

```text
UNQUANTIZED_SUCCESS_MARGIN_GT_ZERO=REQUIRED
PUBLIC_QUANTIZED_SUCCESS_MARGIN_GTE_ZERO=REQUIRED
PUBLIC_ZERO_MARGIN_DOES_NOT_IMPLY_TANGENCY=REQUIRED
```

A strictly positive unquantized margin may canonicalize to public zero under
`ROUND_HALF_EVEN` when its magnitude is below the public coordinate resolution,
including the exact half-quantum tie that rounds to canonical zero. Such a
public zero remains a successful `WINDOW` or `CROSSFLOW_REFERENCE` result.
Tangency exists only when the unquantized predicate is exactly `s==r_h` or
`s==-r_h`; it is never inferred from a quantized public margin.

For outer containment, the exact unquantized squared margin is:

```text
outer_boundary_margin_squared_m2_unquantized
=
(R-r_h)^2-d2
```

It is required to be non-negative for **both** `WINDOW` and
`CROSSFLOW_REFERENCE`, is exactly zero in the **unquantized** domain for
accepted outer tangency, and is **never `null`** on a successful
classification. Its public decimal string is formatted only after
containment classification, using `squared_coordinate_quantum_m2`. A
positive unquantized outer margin may also quantize to public zero; the
outer-tangency warning is emitted only for exact unquantized equality and
is never inferred from that public zero.

The frozen tokens for outer-margin semantics are:

```text
UNQUANTIZED_OUTER_MARGIN_GTE_ZERO=REQUIRED
PUBLIC_QUANTIZED_OUTER_MARGIN_GTE_ZERO=REQUIRED
PUBLIC_ZERO_OUTER_MARGIN_DOES_NOT_IMPLY_TANGENCY=REQUIRED
```

Every `BafflePlaneGeometry.outer_tangent_position_ids` tuple contains
the position IDs of every accepted outer tangency on that baffle, across
both `WINDOW` and `CROSSFLOW_REFERENCE` primary classifications (not
limited to `CROSSFLOW_REFERENCE`).

No margin is re-derived from a quantized coordinate, radius, signed distance, or
squared distance. These exact formulas and the unquantized classification
identity are part of each `classification_audit_hash` projection.

### 9.8 Outer-circle containment for every successful primary disk

After primary cut-boundary classification has succeeded (a position has
been classified as `WINDOW` or `CROSSFLOW_REFERENCE`), every complete
baffle-hole clearance disk must lie entirely inside the baffle disk. This
check applies to BOTH successful primary classifications; `WINDOW` disks
must lie inside the window half-plane *and* inside the baffle circle.

The frozen token is:

```text
ALL_SUCCESSFUL_PRIMARY_DISKS_INSIDE_BAFFLE_CIRCLE=REQUIRED
```

For every successful primary disk (one per `WINDOW` or
`CROSSFLOW_REFERENCE` classification):

```text
d2 = x^2 + y^2
available_radius = R - r_h
available_radius >= 0
d2 <= available_radius^2
```

with

- `R` = `baffle_radius_m`
- `r_h` = `baffle_hole_radius_m`

Result semantics:

```text
d2 < available_radius^2    -> strictly inside baffle circle (no tangency)
d2 == available_radius^2   -> accepted mathematical outer tangency
                              + BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY
d2 > available_radius^2    -> BLOCKED
                              + BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK
```

The classification identity (which primary class the disk belongs to) is
fixed by the unquantized predicate pass from §9.7; the unquantized
containment predicate here is evaluated on the same unquantized high-
precision Decimal derivations. The public `outer_boundary_margin_squared_m2`
field is formatted only after the containment decision, using
`squared_coordinate_quantum_m2`.

A `WINDOW` disk is required to lie inside the
`BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE` (the §9.7 result) and inside
the baffle circle. A `CROSSFLOW_REFERENCE` disk is required to lie inside
the `BAFFLE_DISK_MINUS_WINDOW_REGION` and inside the baffle circle.

The previous claim "`WINDOW requires no outer containment check`" is
removed. Both successful primary classes require this containment.

### 9.9 Pairwise covered-region hole non-overlap

Pairwise hole non-overlap applies **only** to `CROSSFLOW_REFERENCE`
positions. `WINDOW` positions do not require a baffle-material hole and
are explicitly excluded from this pairwise check.

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

### 9.12 Exact VALID result projection equality

When `result.status == VALID`, the projection invariants below MUST all hold
simultaneously. Any inconsistency is treated as a construction-time canonical
failure and produces `status=BLOCKED`, `geometry=null`, with
`BFG_CANONICALIZATION_FAILED`:

- `result.geometry` is not `null`.
- `result.blocked_result_hash` is `null`.
- `result.blockers == ()`.
- `result.geometry.blockers == ()`.
- `result.blockers == result.geometry.blockers`.
- `result.warnings == result.geometry.warnings`.
- `canonical_message_projections(result.warnings)` uses the exact closed
  message shape and ordering from §13, never a free-form mapping.
- `canonical_message_projections(result.warnings) == result.geometry.provenance["warnings"]`.
- `result.deferred_capabilities == result.geometry.deferred_capabilities`.
- `result.deferred_capabilities == result.geometry.provenance["deferred_capabilities"]`.

The frozen tokens are:

```text
VALID_RESULT_PROJECTION_EQUALITY=REQUIRED
VALID_RESULT_BLOCKERS_EMPTY=REQUIRED
PROVENANCE_WARNING_PROJECTION_EQUALITY=REQUIRED
PROVENANCE_DEFERRED_CAPABILITY_PROJECTION_EQUALITY=REQUIRED
```

A `VALID` result must never carry non-empty `blockers` or any
non-null `blocked_result_hash`. The three warnings/baseline/tangency
projections (`result.warnings`, `result.geometry.warnings`,
`result.geometry.provenance["warnings"]`) must be byte-identical under
`canonical_message_projections`.

When `result.status == BLOCKED`:

- `geometry == null`.
- `blocked_result_hash` is non-null.
- The VALID projection invariants above do not apply. There is no
  `geometry` to cross-check, and `provenance` equality is not required.

### 9.13 Public quantization closure on positive geometry and baffle identity

The blocker `BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION` is emitted
whenever public-output quantization would erase a strictly-positive
quantity or collapse distinct baffle identities.

The frozen set of strictly-positive public geometry fields is:

```text
PUBLIC_STRICTLY_POSITIVE_GEOMETRY_FIELDS
=
usable_baffle_span_m
baffle_diameter_m
baffle_radius_m
baffle_hole_diameter_m
baffle_hole_radius_m
cut_height_m
chord_half_length_m
```

Each field above must satisfy, in the unquantized domain AND in the
public quantized domain:

```text
unquantized_value > 0
public_quantized_value > 0
```

The implementation must not silently emit the canonical empty
decimal string `"0"` for any of these fields.

The frozen tokens for baffle-center identity are:

```text
PUBLIC_BAFFLE_CENTER_COORDINATES_STRICTLY_INCREASING=REQUIRED
PUBLIC_BAFFLE_CENTER_COORDINATES_DISTINCT=REQUIRED
```

For every `i < i+1`:

```text
quantized_public_z_i < quantized_public_z_(i+1)
```

If two distinct center planes quantize to the same public coordinate:

```text
BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION
```

The frozen occupancy rules for every baffle are:

```text
quantized_public_occupied_start_i < quantized_public_occupied_end_i
quantized_public_occupied_start_i <= quantized_public_center_i <= quantized_public_occupied_end_i
```

A zero-width public occupied interval is forbidden.

The frozen tokens for unquantized-vs-public gap / tangency semantics are:

```text
PUBLIC_ZERO_GAP_DOES_NOT_IMPLY_SOLID_TANGENCY=REQUIRED
```

A positive unquantized gap may quantize to public zero under
`ROUND_HALF_EVEN`. The solid-tangency warning is emitted **only** by
exact unquantized equality, never by a quantized zero. The
`ROUND_HALF_EVEN` quantization is monotonic, so two non-overlapping
unquantized intervals cannot quantize into overlapping public intervals
in reverse order, but a positive gap may quantize to public equality
without producing a tangency warning.

## 10. Validation stages and no-partial-result behavior

Validation runs in this exact stage order:

1. exported raw boundary and strict in-memory parsing: request schema version,
   exact field set, and raw types;
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
18. public-output quantization positivity, public center distinctness,
    and public occupied-interval non-collapse (see §9.13); any failure
    here emits `BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION` and blocks
    before any valid geometry is constructed;
19. canonical serialization, hashes, IDs, provenance, and final result.

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
BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK
BFG_BAFFLE_HOLE_DISKS_OVERLAP
BFG_POSITION_CLASSIFICATION_INCOMPLETE

BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION

BFG_CANONICALIZATION_FAILED
```

Codes are exact and cannot be aliased.

## 12. Closed warning taxonomy

```text
BFG_FIXED_TUBESHEET_ONLY_V1
BFG_GEOMETRY_NOT_FLOW_AREA
BFG_NOZZLE_POSITION_DEFERRED
BFG_THERMAL_HYDRAULIC_DEFERRED
BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM
BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY
BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY
BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY
```

Required baseline warnings on every valid v1 result, in the sole §13 global
message-sort order (validation stage rank ascending, then code ascending):

```text
BFG_FIXED_TUBESHEET_ONLY_V1
BFG_GEOMETRY_NOT_FLOW_AREA
BFG_NOZZLE_POSITION_DEFERRED
BFG_THERMAL_HYDRAULIC_DEFERRED
BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM
```

Optional warning order is also derived only by the §13 key:

```text
stage 6:
BFG_FIXED_TUBESHEET_ONLY_V1
BFG_GEOMETRY_NOT_FLOW_AREA
BFG_NOZZLE_POSITION_DEFERRED
BFG_THERMAL_HYDRAULIC_DEFERRED
stage 8:
BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM
stage 12, only if eligible:
BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY
stage 15, only if eligible:
BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY
stage 16, only if eligible:
BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY
```

Primary taxonomy display order never overrides this global message order.

### 12.1 Exact warning emission, aggregation, and ordering contract

All warnings obey:

- **at most one `MessageEntry` per warning code** in any single result;
- one aggregate `MessageEntry` per eligible warning code;
- no per-contact `MessageEntry` emission;
- every contact is represented only inside the warning code's exact closed
  details aggregation;
- no duplicate warning codes within one result;
- no implementation-selected aggregation of contacts into multiple warnings;
- no free-form `details` fields — `details` is constrained per warning
  code below.

The sole global warning ordering key is the §13 tuple:

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

All warning output uses this key. The baseline warning order and every local
warning table must match the same global message sort; a local table's displayed
order has no independent authority.

The frozen tokens are:

```text
WARNING_AGGREGATION_ONE_ENTRY_PER_CODE=REQUIRED
PER_CONTACT_MESSAGE_ENTRY_EMISSION=FORBIDDEN
DUPLICATE_WARNING_CODE_IN_ONE_RESULT=FORBIDDEN
ALL_WARNING_OUTPUT_ORDER_USES_SECTION13_SORT=REQUIRED
BASELINE_WARNING_ORDER_USES_GLOBAL_MESSAGE_SORT=REQUIRED
LOCAL_TABLE_ORDER_MUST_MATCH_GLOBAL_MESSAGE_SORT=REQUIRED
```

### 12.2 Baseline warnings on every `VALID` result

Every `VALID` v1 result emits each of these five codes exactly once, in the
§13 global message-sort order. Their stage, field path, message key, evidence
references, and details remain the frozen Round 4 values.

| Code | `eligibility_stage` | `field_path` | `message_key` | `evidence_refs` | `details` |
|---|---|---|---|---|---|
| `BFG_FIXED_TUBESHEET_ONLY_V1` | 6 | `"configuration.construction_family"` | `"fixed_tubesheet_only_v1"` | `request.evidence_refs` | `{"construction_family":"FIXED_TUBESHEET"}` |
| `BFG_GEOMETRY_NOT_FLOW_AREA` | 6 | `null` | `"geometry_not_flow_area"` | `request.evidence_refs` | `{"flow_area_calculation_performed":false}` |
| `BFG_NOZZLE_POSITION_DEFERRED` | 6 | `null` | `"nozzle_position_deferred"` | `request.evidence_refs` | `{"nozzle_position_inference_performed":false}` |
| `BFG_THERMAL_HYDRAULIC_DEFERRED` | 6 | `null` | `"thermal_hydraulic_deferred"` | `request.evidence_refs` | `{"thermal_hydraulic_calculation_performed":false}` |
| `BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM` | 8 | `"design_authority"` | `"caller_supplied_no_standard_claim"` | `design_authority.evidence_refs` | `{"authority_mode":"CALLER_SUPPLIED_EXPLICIT","standard_claim_status":"NO_STANDARD_CLAIM"}` |

### 12.3 Solid-tangency aggregate warning

`BFG_BAFFLE_SOLID_TANGENCY_NOT_MANUFACTURING_ADEQUACY`:

- `eligibility_stage` = 12
- `field_path` = `"baffle_planes"`
- `message_key` = `"baffle_solid_tangency_not_manufacturing_adequacy"`
- `evidence_refs` = `request.evidence_refs`
- `details` is exactly:

```text
{
"active_span_boundary_contacts":[...],
"adjacent_baffle_index_pairs":[...]
}
```

`active_span_boundary_contacts` is an ordered subset of
`["FIRST_BAFFLE_START", "LAST_BAFFLE_END"]`, in that order.
`adjacent_baffle_index_pairs` contains exact two-integer arrays of the
form `[i, i+1]`, sorted by first index. Both arrays are always present;
they may be empty. The warning is emitted only when at least one of
the two arrays is non-empty.

### 12.4 Outer-tangency aggregate warning

`BFG_BAFFLE_HOLE_OUTER_TANGENCY_NOT_MANUFACTURING_ADEQUACY`:

- `eligibility_stage` = 15
- `field_path` = `"baffle_planes[*].tube_hole_classifications[*].outer_boundary_margin_squared_m2"`
- `message_key` = `"baffle_hole_outer_tangency_not_manufacturing_adequacy"`
- `evidence_refs` = `request.evidence_refs`
- `details` is exactly:

```text
{
"contacts":[
{"baffle_index":<integer>, "position_id":<string>},
...
]
}
```

Contacts are sorted by `baffle_index` ascending, then `position_id`
ascending. The contacts cover both `WINDOW` and `CROSSFLOW_REFERENCE`
outer tangencies (per §9.8). Emitted only when at least one contact is
present.

### 12.5 Pair-tangency aggregate warning

`BFG_BAFFLE_HOLE_PAIR_TANGENCY_NOT_MANUFACTURING_ADEQUACY`:

- `eligibility_stage` = 16
- `field_path` = `"baffle_planes[*].pairwise_tangent_position_pairs"`
- `message_key` = `"baffle_hole_pair_tangency_not_manufacturing_adequacy"`
- `evidence_refs` = `request.evidence_refs`
- `details` is exactly:

```text
{
"contacts":[
{"baffle_index":<integer>, "lower_position_id":<string>, "higher_position_id":<string>},
...
]
}
```

Sorted by `baffle_index`, then `lower_position_id`, then
`higher_position_id`. Emitted only when at least one contact is present.

### 12.6 Blocked-result warning carry-forward

The frozen token is:

```text
BLOCKED_RESULT_WARNING_CARRY_FORWARD
=WARNINGS_FROM_FULLY_COMPLETED_PRIOR_STAGES_ONLY
```

Rules:

- A warning's `eligibility_stage` must have executed to completion AND
  that stage must have produced no blocker, in order for the warning to
  enter the result.
- If a blocker is produced at stage `s`:
  - retain all eligible warnings from every fully completed prior stage
    `t < s`;
  - do NOT produce any warning whose eligibility stage is `s` or any
    stage `t > s`.

A `VALID` result therefore carries:

- the five baseline warnings (each exactly once), plus
- at most one of each tangency warning that actually occurred.

The closed warning set remains exactly **8** codes.

## 13. Message ordering

Every message has:

| Field | Type |
|---|---|
| `code` | string |
| `field_path` | string or null |
| `message_key` | string |
| `evidence_refs` | tuple[string, ...] |
| `details` | canonical mapping or null |

Messages sort by the one global key:

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
reconstructed from code alone. `result.warnings`, `geometry.warnings`, and the
`canonical_message_projections` stored in provenance use the same ordered
warning tuple produced by this key. `geometry_hash` and `blocked_result_hash`
consume the §13-sorted result and must never consume local table insertion
order, discovery order, or contact traversal order.

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

The blocked-result hash covers exactly:

- `request_identity`, which is the exact validated `request_hash` when
  computable, otherwise the complete
  `task024.raw-blocked-projection.v3` projection from §7.6;
- ordered warnings;
- ordered blockers;
- deferred capabilities;
- profile ID;
- design contract path.

No raw value is passed directly to canonical JSON. The tagged fallback
projection is computed first, so every contract-defined invalid request has a
non-null deterministic blocked-result hash. Two identical invalid requests must
produce identical blocked-result hashes.

### 14.7 Acyclic hash dependency graph

The dependency graph is exact and one-directional:

```text
axial_authority_payload -> axial_span_authority_hash
baffle_authority_payload -> baffle_design_authority_hash

validated_complete_request
  including frozen upstream leaf hashes
  -> request_hash

unquantized predicates
  -> classification identities
  -> quantized public geometry values
  -> classification_audit_hashes

request_hash
+ quantized result fields
+ classification_audit_hashes
+ ordered messages
+ deferred_capabilities
+ exact closed provenance
  -> geometry_hash

geometry_hash -> geometry_id

validated request hash OR raw blocked projection
+ ordered messages
+ deferred_capabilities
+ profile identity
  -> blocked_result_hash
```

TASK-021 and TASK-022 `request_hash` values are frozen upstream leaf strings in
the complete upstream objects; TASK-024 never writes back to those objects.
TASK-024 provenance may contain TASK-024 `request_hash`, but request hashing does
not include TASK-024 result or provenance. Provenance excludes `geometry_hash`,
`geometry_id`, and `blocked_result_hash`. Therefore:

```text
HASH_DEPENDENCY_CYCLE_COUNT=0
```

## 15. Provenance contract

`BaffleGeometry.provenance` is an exact closed mapping. Additional fields are
forbidden. Field omission, field addition, or use of a non-bound source emits
`BFG_CANONICALIZATION_FAILED` and blocks result construction with no partial
geometry.

| Field | Exact source or value |
|---|---|
| `task_id` | exact `TASK-024` |
| `design_contract_path` | exact design contract path constant |
| `profile_id` | exact TASK-024 profile constant |
| `software_version` | non-empty canonical module constant; no runtime lookup |
| `git_commit` | lowercase 40-hex build constant; no runtime lookup |
| `task020_configuration_id` | validated TASK-020 value |
| `task020_configuration_hash` | validated TASK-020 value |
| `task020_case_authority` | exact detached canonical projection of validated TASK-020 case authority |
| `task021_layout_id` | validated TASK-021 value |
| `task021_layout_hash` | validated TASK-021 value |
| `task021_tube_geometry_snapshot_hash` | validated TASK-021 snapshot hash |
| `task021_layout_rule_snapshot_hash` | validated TASK-021 rule snapshot hash |
| `task022_geometry_id` | validated TASK-022 value |
| `task022_geometry_hash` | validated TASK-022 value |
| `task022_shell_authority_mode` | validated TASK-022 value |
| `task022_shell_authority_identity` | exact closed `Task022ShellAuthorityIdentity` mapping defined below |
| `task022_geometry_rule_snapshot_hash` | validated TASK-022 rule snapshot hash |
| `axial_span_authority_hash` | validated TASK-024 axial authority hash |
| `baffle_design_authority_hash` | validated TASK-024 design authority hash |
| `request_hash` | exact TASK-024 request hash |
| `source_claim_status` | exact `NO_STANDARD_CLAIM` |
| `automatic_selection_performed` | exact `false` |
| `nozzle_position_inference_performed` | exact `false` |
| `flow_area_calculation_performed` | exact `false` |
| `warnings` | exact ordered canonical projections of result warnings |
| `deferred_capabilities` | exact frozen ordered tuple from the result |

### 15.1 Exact TASK-022 shell-authority identity projection

`Task022ShellAuthorityIdentity` is an exact closed mapping with exactly these
three fields:

| Field | Type | Exact rule |
|---|---|---|
| `shell_authority_mode` | string | exact validated TASK-022 enum token |
| `caller_supplied_shell` | canonical mapping or null | complete selected TASK-022 caller object, otherwise null |
| `approved_shell_geometry` | canonical mapping or null | complete selected TASK-022 approved snapshot, otherwise null |

The projection is constructed from the validated `ShellBundleGeometry` fields:

```text
shell_bundle_geometry.shell_authority_mode
shell_bundle_geometry.caller_supplied_shell
shell_bundle_geometry.approved_shell_geometry
```

The mode-dependent projection is exact:

```text
CALLER_SUPPLIED_EXPLICIT:
  shell_authority_mode="CALLER_SUPPLIED_EXPLICIT"
  caller_supplied_shell=<complete canonical caller object>
  approved_shell_geometry=null

APPROVED_CATALOG_SNAPSHOT:
  shell_authority_mode="APPROVED_CATALOG_SNAPSHOT"
  caller_supplied_shell=null
  approved_shell_geometry=<complete canonical approved snapshot>
```

The complete caller-object field set is:

```text
schema_version
shell_inside_diameter_m
evidence_refs
authority_hash
```

The complete approved-snapshot field set is:

```text
schema_version
geometry_id
geometry_type
revision
approval_state
shell_inside_diameter_m
record_hash
source_binding
snapshot_hash
```

Its nested `source_binding` field set is exactly:

```text
source_id
source_type
source_revision
source_location
evidence_ref
approved_by
approved_at
```

No alias, reduced identity subset, free-form mapping, or additional field is
permitted. A mode/object nullability mismatch, an additional or missing nested
field, or disagreement with the validated TASK-022 result emits
`BFG_CANONICALIZATION_FAILED`. The complete closed mapping enters provenance and
therefore `geometry_hash`.

`software_version` and `git_commit` are immutable code/build constants supplied
without filesystem, environment, subprocess, network, registry, or clock access
in the calculation path. They are not caller engineering inputs and are not
looked up dynamically.

The nested upstream authority projections are the exact canonical projections
already validated under their owning task contracts. TASK-024 does not add
fields to them and does not substitute a free-form mapping.

The provenance mapping contains neither `geometry_hash`, `geometry_id`, nor
`blocked_result_hash`. It is detached and immutable. Caller mutation after
construction cannot alter any provenance value, hash, or result. The complete
closed provenance mapping is included in `geometry_hash`; an implementation may
not append diagnostic, host, timestamp, environment, or extension fields.

## 16. Public raw-schema and calculation operation

The future core exposes exactly one public operation:

```python
validate_request(
    raw_request: Any,
) -> BaffleGeometryValidationResult
```

`BaffleGeometryRequest` is the immutable typed representation produced only
after strict in-memory parsing. It is not the raw public boundary type.

The public successful-input shape is exact:

- the top-level value is an exact built-in `dict` with string keys;
- its field set is exactly the §8.3 `BaffleGeometryRequest` field set;
- nested TASK-024 authority structures are exact built-in `dict` values with
  their frozen field sets;
- raw array fields are exact built-in `list` values and are converted to frozen
  tuples only after validation;
- `configuration`, `tube_layout`, and `shell_bundle_geometry` are complete exact
  instances of their TASK-020, TASK-021, and TASK-022 public models;
- custom mappings, mapping subclasses, container subclasses, aliases, and
  coercion are forbidden.

The implementation has two non-exported helpers with exact responsibilities:

```python
parse_request(
    raw_request: Any,
) -> BaffleGeometryRequest

validate_typed_request(
    request: BaffleGeometryRequest,
) -> BaffleGeometryValidationResult
```

`parse_request` may raise only an internal `BaffleGeometrySchemaFailure`
containing the validation-stage rank, ordered structured blockers, the raw
failing component, and any already validated context. It performs no geometry
and no external I/O.

The exported `validate_request` owns the full public no-exception boundary:

1. preserve the complete `raw_request` solely for deterministic blocked hashing;
2. call `parse_request`;
3. catch every contract-defined `BaffleGeometrySchemaFailure`;
4. return `status=BLOCKED`, `geometry=null`, the ordered schema blockers, allowed
   prior-stage warnings, exact deferred capabilities, and a non-null
   `blocked_result_hash` based on the complete §7.6 raw projection;
5. call `validate_typed_request` only after parsing succeeds;
6. convert every later contract-defined validation failure into the same
   structured blocked-result contract.

Unknown fields, wrong top-level raw types, malformed nested structures, wrong
schema versions, and all other stage-1 raw failures are therefore reachable
through the exported operation. No caller must construct a dataclass before
receiving a structured blocker.

The operation:

- is pure and in-memory;
- performs no lookup;
- performs no catalog scan;
- performs no alternative ranking;
- mutates no input;
- returns no exception for ordinary invalid engineering or schema input;
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

- non-mapping top-level raw request returns `BLOCKED` with a non-null stable
  `blocked_result_hash`;
- custom mapping and mapping-subclass top-level values block without invoking
  user-defined iteration;
- unknown fields at every public layer;
- wrong schema versions;
- bool supplied as integer;
- float supplied as decimal;
- exponent notation;
- NaN/Infinity;
- tuple/list shape mismatches;
- duplicate evidence refs;
- missing authority objects;
- malformed hashes;
- the public raw mapping is parsed to exactly one immutable
  `BaffleGeometryRequest` before typed validation;
- parser failures are converted by the exported `validate_request` operation
  into structured blockers without leaking `BaffleGeometrySchemaFailure`.

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
- successful WINDOW disk outside baffle disk;
- successful CROSSFLOW_REFERENCE disk outside baffle disk;
- both produce `BFG_BAFFLE_HOLE_OUTSIDE_BAFFLE_DISK`;
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
   fails the test;
7. a strictly positive primary or physical-tube cut margin below public
   coordinate resolution may quantize to canonical public zero while retaining
   its successful `WINDOW` or `CROSSFLOW_REFERENCE` identity;
8. a positive outer-containment squared margin below public squared resolution
   may quantize to public zero without emitting the outer-tangency warning;
9. public zero margin never causes tangency, intersection, containment, or
   overlap to be reclassified.

### 19.9 Closed result and failure-projection tests

At minimum:

1. `PhysicalTubeDiskAudit` accepts exactly four fields, rejects unknown fields,
   and always matches the successful primary region classification;
2. `WINDOW` primary margin equals `s-r_h`, crossflow-reference primary margin
   equals `-r_h-s`, and the physical audit uses the same formulas with `r_t`;
3. `outer_boundary_margin_squared_m2` is non-null for every successful
   `WINDOW` and every successful `CROSSFLOW_REFERENCE`; it equals the public
   quantization of the unquantized formula `(R-r_h)^2-d2`; it is public zero
   at exact accepted outer tangency; a strictly positive unquantized outer
   margin may also quantize to public zero without emitting a tangency warning;
4. `WINDOW` exact accepted outer tangency emits public zero;
5. a positive sub-quantum `WINDOW` outer margin emits public zero without a
   tangency warning;
6. no test expects an absent outer-boundary margin for `WINDOW`;
7. margin predicates are evaluated before formatting; metre margins use
   `coordinate_quantum_m` and squared margins use the exactly derived
   `squared_coordinate_quantum_m2`;
8. fallback blocked hashing is stable for finite float, signed zero float, NaN,
   positive/negative Infinity, exact Decimal, bytes, surrogate-containing string,
   exact built-in list, tuple, dict, set, frozenset, recognized enum, recognized
   dataclass, cyclic graph, custom mapping, container subclass, and unsupported
   object;
9. mapping and unordered-collection projections are stable under insertion or
   iteration-order changes;
10. raw fallback projection never validates or coerces an invalid engineering
    value;
11. provenance accepts exactly the closed field set in §15 and rejects one
    missing field or one additional field;
12. `Task022ShellAuthorityIdentity` is exact for both
    `CALLER_SUPPLIED_EXPLICIT` and `APPROVED_CATALOG_SNAPSHOT`, rejects the wrong
    null/non-null pairing, and changes `geometry_hash` when any selected nested
    identity field changes;
13. module/build provenance constants require no forbidden I/O;
14. request, audit, geometry, UUID, provenance, and blocked-result dependency
    tests prove `HASH_DEPENDENCY_CYCLE_COUNT=0`;
15. changing an exact physical-audit field, public margin, raw projection tag,
    or provenance field changes the owning hash deterministically.

### 19.10 Round 5 outer-containment, projection-equality, warning-emission, projection-v3, and quantization-closure tests

In addition to the prior test matrix, the future implementation must cover
at minimum:

1. `WINDOW` disk strictly inside the baffle circle;
2. `WINDOW` disk accepted outer tangent;
3. `WINDOW` disk partially outside the baffle circle → `BLOCKED`;
4. `WINDOW` disk wholly outside the baffle circle → `BLOCKED`;
5. `CROSSFLOW_REFERENCE` disk outside the baffle circle → `BLOCKED`;
6. `outer_boundary_margin_squared_m2` is non-null for every successful
   `WINDOW` and every successful `CROSSFLOW_REFERENCE`;
7. `outer_tangent_position_ids` covers both `WINDOW` and
   `CROSSFLOW_REFERENCE` outer tangencies;
8. VALID result warnings equal `geometry.warnings` and equal
   `provenance["warnings"]` under `canonical_message_projections`;
9. VALID result `deferred_capabilities` equals
   `geometry.deferred_capabilities` and equals
   `provenance["deferred_capabilities"]`;
10. VALID result `blockers` is empty at both result and geometry levels;
11. VALID result projection mismatch yields `BFG_CANONICALIZATION_FAILED`
    with `status=BLOCKED` and `geometry=null`;
12. exactly one warning per warning code is emitted;
13. solid-tangency aggregation merges contacts into one warning with
    `active_span_boundary_contacts` and `adjacent_baffle_index_pairs`;
14. outer-tangency aggregation merges contacts into one warning covering
    `WINDOW` and `CROSSFLOW_REFERENCE`;
15. pair-tangency aggregation merges contacts into one warning;
16. blocked warning carry-forward retains only fully completed prior-stage
    warnings when a stage produces a blocker;
17. raw blocked projection v3 total for huge integers, negative huge
    integers, huge-int zero, huge integers nested in collections, exact
    scalar and container subclass override traps, custom-metaclass metadata
    traps, recognized enum/dataclass static tables, Decimal finite/Infinity/
    qNaN/sNaN, and unsupported-object fixed collapse;
18. positive unquantized derived field becoming public zero →
    `BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION`;
19. two distinct center planes colliding after quantization →
    `BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION`;
20. occupied interval collapsing after quantization →
    `BFG_PUBLIC_GEOMETRY_QUANTIZATION_COLLISION`;
21. positive unquantized gap becoming public zero does NOT emit a
    solid-tangency warning;
22. five baseline warnings exactly match the §13 sorted order;
23. eligible stage-12, stage-15, and stage-16 optional warnings appear after
    baseline stages in the same §13 order;
24. local table order and serialized warning order are identical;
25. each eligible warning code produces one aggregate `MessageEntry` and
    multiple contacts never create duplicate warning codes;
26. result, geometry, provenance, `geometry_hash`, and `blocked_result_hash`
    consume the same §13-sorted warning tuple.

### 19.11 Raw-blocked projection v3 exact-dispatch and no-user-code tests

Required by §7.6.4 and frozen here for completeness:

1. exact int with more than 4300 decimal digits;
2. negative exact huge int;
3. exact int nested in exact built-in list, tuple, dict, set, and frozenset;
4. int subclass overriding `__abs__`, `__format__`, `__str__`, and `__repr__`
   is projected as `{"raw_type":"unsupported_object"}` without method calls;
5. str subclass overriding iteration/conversion, float subclass overriding
   hex/representation, bytes subclass overriding conversion, and Decimal
   subclass overriding `as_tuple`/representation are not executed;
6. exact built-in scalar paths never execute scalar-subclass methods and all
   scalar subclasses collapse to `{"raw_type":"unsupported_object"}`;
7. custom metaclasses that define or raise from `__getattribute__`, `__hash__`,
   `__eq__`, `__module__`, or `__qualname__` produce the fixed unsupported token
   with zero user-code call count;
8. recognized enum uses static type/member tokens and never reads `.name`,
   `__module__`, or `__qualname__`;
9. recognized dataclass uses the static field table; a missing field produces
   `recognized_dataclass_unavailable`; unrecognized dataclasses collapse to
   `unsupported_object`;
10. custom mapping/container subclasses are not iterated and runtime type
    metadata is never read;
11. finite Decimal, Decimal Infinity, qNaN, and sNaN produce the closed Decimal
    projection without exception;
12. projection v3 is stable across process, hash seed, locale,
    `int_max_str_digits`, and custom type metadata.

All of the above must produce a deterministic blocked hash and must not raise a
serialization exception.

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
    form. `coordinate_quantum_m=0.000000000001` applies only to that step;
19. `PhysicalTubeDiskAudit` and every public margin have exact closed schemas
    and formulas;
20. blocked-result hashing is total for the frozen raw-value projection and
    performs no executable or host-dependent serialization;
21. provenance has an exact closed field set and deterministic field sources;
22. the complete hash dependency graph is acyclic;
23. the exported public operation accepts raw in-memory input, owns strict schema
    parsing, and converts every contract-defined parser failure into a structured
    blocked result;
24. positive unquantized margins may quantize to public zero without changing
    classification or creating a tangency warning;
25. `Task022ShellAuthorityIdentity` is an exact mode-dependent closed projection
    of the actual TASK-022 authority fields;
26. every successful primary disk (both `WINDOW` and `CROSSFLOW_REFERENCE`)
    is fully inside the baffle circle, with no exception for `WINDOW`;
27. VALID result, `geometry`, and `provenance` duplicate projections are
    exact under `canonical_message_projections` for warnings and
    `deferred_capabilities`, and blockers are empty at both levels;
28. warning emission and blocked carry-forward are deterministic: at most
    one `MessageEntry` per warning code, and warnings come only from
    fully completed prior stages;
29. raw blocked projection v3 is total for arbitrary-size exact integers and
    dispatches only by exact type identity; it executes no scalar-subclass,
    container-subclass, object, metaclass, descriptor, hash, equality,
    representation, or runtime type-metadata code;
30. public quantization cannot erase a strictly-positive geometry value
    or collapse baffle identity; distinct center planes must remain
    distinct after quantization;
31. `outer_boundary_margin_squared_m2` is non-null for every successful
    `WINDOW` and `CROSSFLOW_REFERENCE` classification in model, formula,
    provenance-owning projection, and tests;
32. all warnings use the sole §13 ordering key, and every local warning
    table is written in that same order;
33. raw blocked projection v3 dispatches only by exact type identity,
    executes no scalar-subclass, container-subclass, object, metaclass,
    descriptor, hash, equality, representation, or runtime type-metadata code;
34. recognized enum and dataclass identities come only from static closed
    code tables; all unsupported objects collapse to a fixed diagnostic token.

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
