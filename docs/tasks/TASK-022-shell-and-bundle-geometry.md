# TASK-022 — Shell-and-Tube Shell and Bundle Geometry Foundation

> Binding design contract for the third M3 shell-and-tube capability.
> TASK-022 consumes one valid TASK-020 shell-and-tube configuration and one valid
> TASK-021 tube layout, then produces one deterministic shell-and-bundle geometry
> result with explicit diameter authority, bundle envelope, geometric clearances,
> hashes, blockers, warnings and provenance.
>
> TASK-022 does not design baffles, pass partitions, nozzles, thermal performance,
> pressure drop, mechanical adequacy, materials, mass, cost, optimization, APIs,
> reports or engineering Golden values.

## 1. Authority, allocation and current status

| Field | Value |
|---|---|
| Authorizing Issue | #143 — `[TASK-022][source-definition] Define shell and bundle geometry foundation` |
| Source-definition authorization | `AUTHORIZE_TASK022_SOURCE_DEFINITION_ONLY` |
| Allocation/design authorization | `AUTHORIZE_TASK022_ALLOCATION_FREEZE_AND_ONE_FILE_DESIGN_AUTHORING` |
| Source inventory | Issue #143 comment `4963748205` |
| Allocation decision | Issue #143 comment `4963750458` |
| Input/output boundary | Issue #143 comment `4963752790` |
| Source gaps/design skeleton | Issue #143 comment `4963755643` |
| Allocation freeze record | Issue #143 comment `4963786210` |
| Frozen task allocation | `TASK-022 = Shell-and-Tube Shell and Bundle Geometry Foundation` |
| Design branch | `docs/task-022-shell-bundle-geometry-design` |
| Design file | `docs/tasks/TASK-022-shell-and-bundle-geometry.md` |
| Allowed repository path | This design file only |
| Authoring base | `main@af5f01293b9d6abd7e0c02ae430522ba1bce1a75` |
| Verified predecessor merge SHA | `125b86661c9e49ba54aa51529cf989327fbd0a4f` |
| Verified predecessor main CI | run `29291735354`, completed / success |
| Direct predecessor | TASK-021 — Shell-and-Tube Tube Layout and Tube Count Foundation |
| Configuration predecessor | TASK-020 — Shell-and-Tube Configuration Schema Foundation |
| Licensing authority | TASK-012 — Standards rule-pack and license boundary |
| Geometry-governance authority | TASK-016 — Approved geometry catalog |
| Product authority | `docs/MASTER_DEVELOPMENT_SPEC.md`, especially §§2, 7, 8.2 and 9 |
| Design status | PROPOSED until separately reviewed and merged |
| Implementation status | NOT AUTHORIZED |
| Ready status | NOT AUTHORIZED |
| Merge status | NOT AUTHORIZED |
| Issue close | NOT AUTHORIZED |
| TASK-023 through TASK-039 | UNALLOCATED |

This authorization freezes the TASK-022 allocation and permits only this one-file
contract. It does not authorize production code, tests, fixtures, CI-manifest or
workflow changes, implementation branches, a pull request, Ready transition,
merge, Issue closure, branch deletion, review dismissal, thread resolution or
allocation of any later task.

## 2. Exact TASK-022 allocation

TASK-022 owns **Shell-and-Tube Shell and Bundle Geometry Foundation**.

It owns only the deterministic geometric boundary between a completed TASK-021
tube layout and later shell-and-tube capabilities. It must:

1. consume one complete valid TASK-020 `ShellAndTubeConfiguration`;
2. consume one complete valid TASK-021 `TubeLayout`;
3. verify that the layout is bound to the supplied TASK-020 configuration;
4. consume one explicit shell-inside-diameter authority;
5. consume one explicit shell/bundle geometry-rule authority;
6. calculate the bare-tube bundle radial envelope from accepted TASK-021 tube
   positions and the approved tube outside diameter;
7. apply one explicit bundle peripheral allowance;
8. calculate bundle outer-envelope diameter;
9. calculate shell-to-bundle radial and diametral geometric clearance;
10. compare the calculated radial clearance with one explicit required minimum;
11. preserve construction-family and equipment-orientation identity without
    claiming mechanical adequacy;
12. produce canonical serialization, deterministic hashes, warnings, blockers,
    provenance and deferred-capability declarations.

TASK-022 establishes geometry identity only. It does not establish thermal,
hydraulic, mechanical, manufacturing, procurement, inspection, certification or
legal-compliance adequacy.

## 3. Source-of-truth inventory and authority disposition

### 3.1 Binding repository authority

TASK-022 is derived from:

- `docs/MASTER_DEVELOPMENT_SPEC.md`, especially the deterministic-kernel rule and
  the first-stage shell-and-tube scope in §8.2;
- `docs/tasks/TASK-020-shell-and-tube-configuration-schema.md` and the current
  `hexagent.exchangers.shell_tube` configuration runtime;
- `docs/tasks/TASK-021-shell-and-tube-tube-layout-and-count.md` and the current
  `hexagent.exchangers.shell_tube.tube_layout` runtime;
- `docs/tasks/TASK-012-standards-rule-pack-license-boundary.md` and current
  rule-pack runtime;
- `docs/tasks/TASK-016-approved-geometry-catalog.md` and current approved-geometry
  governance runtime;
- Issue #143 and the five authority records listed in §1;
- TASK-002 SI discipline, TASK-004 warning/blocker/provenance conventions and
  TASK-015A deterministic test/CI governance.

### 3.2 Direct predecessor authority

TASK-020 supplies the complete validated shell-and-tube configuration, including:

- configuration ID and hash;
- construction family;
- equipment orientation;
- shell-pass and tube-pass counts;
- component tokens;
- case-revision authority;
- warnings, blockers and deferred capabilities.

TASK-021 supplies one complete immutable tube layout, including:

- layout ID and hash;
- request hash;
- TASK-020 configuration identity;
- construction family and equipment orientation;
- approved tube geometry snapshot;
- approved layout-rule authority snapshot;
- placement envelope;
- accepted tube-center positions;
- tube-hole and physical-tube counts;
- exclusion audit;
- warnings, blockers, provenance and deferred capabilities.

TASK-022 must consume these complete values. An ID-only, hash-only or partial
projection is insufficient.

### 3.3 Runtime authority gaps

At design authoring time, runtime authority does not yet exist for:

- a shell/bundle geometry profile;
- an approved shell inside-diameter catalog;
- a shell-product selection contract;
- an approved construction-family-specific clearance rule pack;
- a repository-redistributable licensed standard table for shell clearances;
- vendor shell catalogs with confirmed repository redistribution rights.

These gaps are binding. The implementation must not fill them with remembered
TEMA/API tables, vendor dimensions, nearest-size heuristics, hidden defaults or
unreviewed engineering rules.

### 3.4 Permitted authority strategy

The deterministic core may consume only explicit immutable authority snapshots.
The closed v1 authority modes are:

```text
INTERNAL_GENERIC
APPROVED_RULE_PACK
```

for the shell/bundle geometry rule, and:

```text
CALLER_SUPPLIED_EXPLICIT
APPROVED_CATALOG_SNAPSHOT
```

for shell inside diameter.

`INTERNAL_GENERIC` may carry only generic mathematics and explicit caller
constraints. It must carry `NO_STANDARD_CLAIM`. It may not encode remembered
standard minimums or proprietary catalog knowledge.

`APPROVED_RULE_PACK` and `APPROVED_CATALOG_SNAPSHOT` remain unusable until their
upstream artifacts exist, pass TASK-012/TASK-016 governance and are converted by
separately authorized adapters.

## 4. Frozen design decisions

### 4.1 Complete TASK-020 configuration input

The request carries one complete valid `ShellAndTubeConfiguration`. The core
verifies the configuration with the existing TASK-020 identity helpers and
requires:

- `equipment_family == SHELL_AND_TUBE`;
- no TASK-020 blockers;
- canonical payload reproduces `configuration_hash`;
- UUID helper reproduces `configuration_id`;
- accepted case-revision authority;
- supported construction family and orientation.

TASK-022 performs no persistence lookup and does not reconstruct TASK-020
semantics.

### 4.2 Complete TASK-021 layout input

The request carries one complete valid TASK-021 `TubeLayout`. The core verifies:

- `schema_version == task021.tube-layout.v1`;
- `blockers` is empty;
- `positions` is non-empty;
- existing TASK-021 hash verification reproduces `layout_hash`;
- complete TASK-021 provenance remains present;
- embedded tube geometry snapshot remains valid;
- `task020_configuration_id` and `task020_configuration_hash` exactly match the
  separately supplied TASK-020 configuration;
- construction family, orientation, shell-pass count and tube-pass count match;
- no field is silently repaired or reinterpreted.

TASK-022 does not re-enumerate tube positions, recount tubes, alter exclusions,
change U-tube pairings or rebuild the TASK-021 layout.

### 4.3 Placement envelope is not bundle or shell diameter

TASK-021 `tube_center_envelope_diameter_m` remains a caller-supplied tube-center
placement constraint. TASK-022 must never copy, rename or report it as:

- bare-tube bundle diameter;
- bundle outer-envelope diameter;
- shell inside diameter;
- baffle diameter;
- shell-to-bundle clearance.

TASK-022 derives the bare-tube bundle envelope only from actual accepted tube
positions and approved tube OD.

### 4.4 Closed shell-inside-diameter authority modes

#### 4.4.1 `CALLER_SUPPLIED_EXPLICIT`

The request carries one `CallerSuppliedShellInsideDiameter` object. It must
contain an explicit positive canonical decimal diameter and non-empty evidence.
The core validates geometry only and emits a warning that no catalog selection or
standard-size claim was performed.

#### 4.4.2 `APPROVED_CATALOG_SNAPSHOT`

The request carries one complete immutable `ApprovedShellGeometrySnapshot`.
The snapshot must represent one exact approved shell record and include upstream
record hash, source binding and TASK-022 snapshot hash.

The core does not scan a catalog and does not select among alternatives. A future
adapter may construct the snapshot only by exact record ID after loading and
validating a real approved catalog.

#### 4.4.3 Mutual exclusivity

Exactly one authority object must be present and it must match the declared
mode. A missing object, extra object or mode/object mismatch blocks.

### 4.5 No shell-size selection in the deterministic core

TASK-022 v1 does not choose from a list of shell sizes. It does not:

- choose the nearest larger shell;
- choose the first fitting shell;
- choose minimum diameter;
- choose minimum cost;
- scan a shell catalog;
- test alternatives and rank them;
- round a calculated diameter to a remembered standard series.

An exact approved shell record may be selected only by a future source adapter.
Candidate generation and optimization are deferred.

### 4.6 Concentric circular geometry only

The v1 shell boundary is one circle centered at `(0, 0)`. The tube-layout origin
and shell center are identical. Eccentric bundles, oval shells, multi-compartment
shells and arbitrary shell boundaries are deferred.

The shell inside diameter is a geometric circle only. No wall thickness, shell
outside diameter, corrosion allowance, rolling tolerance, out-of-roundness,
allowable stress or pressure-vessel adequacy is inferred.

### 4.7 Bare-tube bundle envelope

For every accepted TASK-021 position `i`:

```text
center_radius_i = sqrt(x_i^2 + y_i^2)
tube_radius = tube_outer_diameter / 2
outer_extent_i = center_radius_i + tube_radius
```

Then:

```text
bare_tube_bundle_radius = max(outer_extent_i)
bare_tube_bundle_diameter = 2 * bare_tube_bundle_radius
```

The result records all `position_id` values whose canonical `outer_extent_i`
equals the maximum. These limiting position IDs are sorted in ascending Unicode
code-point order and are duplicate-free.

The calculation uses actual accepted positions only. Rejected candidates,
exclusion-zone geometry, placement-envelope diameter and physical-tube count are
not substituted into the formula.

### 4.8 Bundle peripheral allowance

The request carries one explicit non-negative canonical decimal
`bundle_peripheral_allowance_m` plus non-empty evidence references.

It is applied radially:

```text
bundle_outer_envelope_radius
    = bare_tube_bundle_radius + bundle_peripheral_allowance

bundle_outer_envelope_diameter
    = 2 * bundle_outer_envelope_radius
```

The allowance is an explicit geometric margin only. It does not assert that tie
rods, sealing strips, support devices, pass partitions, impingement protection,
U-bend pull space or floating-head hardware have been designed.

The value must be at least the minimum allowed by the supplied geometry-rule
authority snapshot. No default is permitted.

### 4.9 Required minimum radial clearance

The request carries one explicit non-negative canonical decimal
`required_minimum_radial_clearance_m` plus non-empty evidence references.

It must be at least the minimum allowed by the supplied geometry-rule authority.
The core does not invent a minimum from standards, vendors, historical projects
or heuristics.

### 4.10 Shell-to-bundle clearance

The exact formulas are:

```text
shell_radius = shell_inside_diameter / 2
shell_to_bundle_radial_clearance
    = shell_radius - bundle_outer_envelope_radius
shell_to_bundle_diametral_clearance
    = shell_inside_diameter - bundle_outer_envelope_diameter
radial_clearance_margin
    = shell_to_bundle_radial_clearance
      - required_minimum_radial_clearance
```

The shell inside diameter must be strictly larger than the bundle outer-envelope
diameter. Zero or negative geometric clearance blocks even when the requested
minimum is zero.

The calculated radial clearance must be greater than or equal to the explicit
required minimum. A deficit blocks and returns no partial geometry result.

### 4.11 Construction-family boundary

The closed accepted construction families remain:

- `FIXED_TUBESHEET`;
- `U_TUBE`;
- `FLOATING_HEAD`.

The same geometric formulas apply to all three. The result preserves the
construction family and emits family-specific deferred warnings where relevant:

- U-tube bend geometry, pull space and fabrication feasibility are deferred;
- floating-head hardware, pull clearance and sealing geometry are deferred;
- fixed-tubesheet thermal expansion and tubesheet adequacy are deferred.

TASK-022 does not claim that a geometrically fitting bundle is mechanically
removable, manufacturable or code-compliant.

### 4.12 No optimization or adequacy claim

TASK-022 evaluates one explicit request. It does not optimize shell diameter,
clearance, bundle allowance, tube layout, construction family or cost.

A valid result means only that the frozen geometric equations and authority
checks succeeded. It is not a recommendation, standard compliance statement,
procurement selection or pressure-vessel design conclusion.

## 5. Dependency contract

### 5.1 Direct dependencies

| Dependency | Use |
|---|---|
| TASK-002 | SI field discipline and canonical base-unit names |
| TASK-004 | structured warning, blocker and provenance conventions |
| TASK-012 | rule source class, approval, license and runtime governance |
| TASK-014 | case authority inherited through TASK-020 |
| TASK-015A | deterministic tests, CI and repository-boundary governance |
| TASK-016 | approved geometry-record/source-binding governance |
| TASK-020 | complete shell-and-tube configuration and identity |
| TASK-021 | complete tube layout, positions, tube geometry and identity |

### 5.2 Reference-only dependencies

TASK-007 through TASK-010 and TASK-017 through TASK-019 demonstrate deterministic
engineering patterns for double-pipe equipment. Their numerical values,
fixtures, expected outputs and cost-stack semantics are not shell-and-tube
geometry authority.

### 5.3 Explicit dependency prohibitions

TASK-022 must not:

- mutate TASK-001 through TASK-021 frozen contracts;
- copy double-pipe shell/annulus geometry into shell-and-tube geometry;
- treat TASK-021 placement envelope as shell or bundle diameter;
- treat TASK-016 hairpin records as shell records;
- import TASK-017 material or mechanical conclusions;
- import TASK-018 cost conclusions;
- import TASK-019 fixture bridges or expected-output values;
- parse restricted standard text at runtime.

## 6. Canonical value and arithmetic rules

### 6.1 Exact field sets

Every public object has an exact field set. Unknown fields block. Raw types are
validated before coercion. Booleans are never accepted as integers. Strings,
integers, arrays and mappings are not silently converted from other types.

### 6.2 Canonical JSON domain

At every public serialization and hash boundary, values may contain only:

- `null`;
- booleans;
- integers;
- canonical finite decimal strings;
- strings;
- arrays of permitted JSON values;
- objects with string keys and permitted JSON values.

Forbidden values include binary floats, `Decimal` objects at serialization,
NaN, Infinity, bytes, sets, raw tuples used as arrays, datetime values,
host-locale values and arbitrary Python objects.

### 6.3 Canonical decimal lexical form

Every public unit-bearing value is a canonical base-10 decimal string. It must:

- be finite;
- contain no exponent notation;
- contain no leading plus sign;
- contain no surrounding whitespace;
- contain no redundant leading zeroes;
- contain no redundant trailing fractional zeroes;
- normalize negative zero to `0`;
- satisfy the field-specific sign rule.

### 6.4 Frozen Decimal context

The internal arithmetic context is:

- precision: 50 significant decimal digits;
- rounding: `ROUND_HALF_EVEN`;
- traps enabled for invalid operation, division by zero and overflow;
- canonical zero: `0`.

Square root uses `Decimal.sqrt()` inside this context. Public computed decimal
strings are normalized from the context result without exponent notation.

### 6.5 Array normalization and duplicates

Arrays declared sorted and duplicate-free are processed in this order:

1. validate raw element types;
2. construct canonical element representations;
3. detect duplicates on canonical representation;
4. block on duplicates;
5. sort by the field-specific ordering.

The implementation must not silently discard duplicates. Position order from the
verified TASK-021 layout remains semantically frozen and is not generically
re-sorted. Derived `limiting_position_ids` is sorted by Unicode code point.

## 7. Frozen domain model

### 7.1 Schema and profile constants

```text
REQUEST_SCHEMA_VERSION = task022.shell-bundle-geometry-request.v1
CALLER_SHELL_SCHEMA_VERSION = task022.caller-shell-diameter.v1
SHELL_SNAPSHOT_SCHEMA_VERSION = task022.approved-shell-geometry.v1
RULE_SNAPSHOT_SCHEMA_VERSION = task022.shell-bundle-rule-authority.v1
RESULT_SCHEMA_VERSION = task022.shell-bundle-geometry.v1
PROFILE_ID = hxforge.shell_tube.shell_bundle_geometry.v1
DESIGN_CONTRACT_PATH = docs/tasks/TASK-022-shell-and-bundle-geometry.md
```

### 7.2 `ShellInsideDiameterAuthorityMode`

Closed values:

```text
CALLER_SUPPLIED_EXPLICIT
APPROVED_CATALOG_SNAPSHOT
```

### 7.3 `RuleAuthorityMode`

Closed values:

```text
INTERNAL_GENERIC
APPROVED_RULE_PACK
```

### 7.4 `SourceBindingSnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `source_id` | string | non-empty |
| `source_type` | string | non-empty |
| `source_revision` | string | non-empty |
| `source_location` | string | non-empty |
| `evidence_ref` | string | non-empty |
| `approved_by` | string | non-empty |
| `approved_at` | string | explicit recorded value, not runtime-now |

### 7.5 `RulePackIdentitySnapshot`

Exact fields:

| Field | Type |
|---|---|
| `rule_pack_id` | non-empty string |
| `rule_pack_version` | non-empty string |
| `rule_pack_canonical_hash` | lowercase 64-character SHA-256 hex |

### 7.6 `ShellBundleGeometryRuleAuthoritySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact rule snapshot version |
| `profile_id` | string | exact TASK-022 profile |
| `authority_mode` | enum | internal generic or approved rule pack |
| `rule_id` | string | non-empty |
| `rule_version` | string | non-empty |
| `rule_artifact_canonical_hash` | string | lowercase SHA-256 hex |
| `source_class` | string | TASK-012 governed |
| `license_evidence` | canonical JSON value | deep-frozen |
| `approval_status` | string | exact `approved` |
| `provenance_edge_ids` | tuple[string] | sorted, unique, non-empty where required |
| `evidence_refs` | tuple[string] | sorted, unique, non-empty |
| `rule_pack_identity` | object or null | required for approved-rule-pack mode |
| `allowed_shell_authority_modes` | tuple[enum] | sorted, unique, non-empty |
| `minimum_bundle_peripheral_allowance_m` | decimal string | non-negative |
| `minimum_radial_clearance_m` | decimal string | non-negative |
| `maximum_position_count` | integer | positive, bool rejected |
| `snapshot_hash` | string | TASK-022 recomputable hash |

For `INTERNAL_GENERIC`:

- `source_class` must equal `INTERNAL_ENGINEERING_RULE`;
- license evidence must carry `NO_STANDARD_CLAIM`;
- `rule_pack_identity` must be null;
- numerical minima must be explicit and may not be copied from restricted or
  proprietary sources.

For `APPROVED_RULE_PACK`:

- `rule_pack_identity` is mandatory;
- TASK-012 approval, license, runtime scope and provenance must pass;
- restricted-standard source classes remain runtime-forbidden;
- vendor-permissioned content requires every required permission token.

### 7.7 `CallerSuppliedShellInsideDiameter`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact caller-shell schema |
| `shell_inside_diameter_m` | decimal string | positive |
| `evidence_refs` | tuple[string] | sorted, unique, non-empty |
| `authority_hash` | string | hash of every other field |

The authority hash proves request identity only. It is not an approval or catalog
record hash.

### 7.8 `ApprovedShellGeometrySnapshot`

Exact fields:

| Field | Type | Rule |
|---|---|---|
| `schema_version` | string | exact shell snapshot schema |
| `geometry_id` | string | non-empty stable record ID |
| `geometry_type` | string | exact `shell` |
| `revision` | string | non-empty |
| `approval_state` | string | exact `approved` |
| `shell_inside_diameter_m` | decimal string | positive |
| `record_hash` | string | upstream lowercase SHA-256 hex |
| `source_binding` | object | complete source snapshot |
| `snapshot_hash` | string | TASK-022 recomputable hash |

The snapshot intentionally contains no wall thickness, material, allowable
stress, corrosion allowance, nominal pipe designation, pressure rating, outside
diameter, tolerance or cost.

### 7.9 `ShellBundleGeometryRequest`

Exact fields:

| Field | Type |
|---|---|
| `schema_version` | string |
| `configuration` | complete TASK-020 `ShellAndTubeConfiguration` |
| `tube_layout` | complete TASK-021 `TubeLayout` |
| `geometry_rule_authority` | `ShellBundleGeometryRuleAuthoritySnapshot` |
| `shell_authority_mode` | `ShellInsideDiameterAuthorityMode` |
| `caller_supplied_shell` | `CallerSuppliedShellInsideDiameter` or null |
| `approved_shell_geometry` | `ApprovedShellGeometrySnapshot` or null |
| `bundle_peripheral_allowance_m` | canonical non-negative decimal string |
| `bundle_peripheral_allowance_evidence_refs` | sorted unique tuple[string] |
| `required_minimum_radial_clearance_m` | canonical non-negative decimal string |
| `minimum_clearance_evidence_refs` | sorted unique tuple[string] |
| `evidence_refs` | sorted unique tuple[string] |

### 7.10 `MessageEntry`

Every warning and blocker uses the exact five-field shape:

```text
code
field_path
message_key
evidence_refs
details
```

`details` is a deep-frozen canonical JSON object or null.

### 7.11 `ShellBundleGeometry`

Exact fields:

| Field | Type |
|---|---|
| `schema_version` | string |
| `geometry_id` | UUID string |
| `geometry_hash` | lowercase SHA-256 hex |
| `request_hash` | lowercase SHA-256 hex |
| `task020_configuration_id` | string |
| `task020_configuration_hash` | string |
| `task021_layout_id` | string |
| `task021_layout_hash` | string |
| `construction_family` | string |
| `equipment_orientation` | TASK-020 orientation enum |
| `shell_pass_count` | integer |
| `tube_pass_count` | integer |
| `tube_geometry_snapshot_hash` | string |
| `geometry_rule_authority` | complete rule snapshot |
| `shell_authority_mode` | enum |
| `caller_supplied_shell` | object or null |
| `approved_shell_geometry` | object or null |
| `shell_inside_diameter_m` | decimal string |
| `shell_radius_m` | decimal string |
| `bare_tube_bundle_radius_m` | decimal string |
| `bare_tube_bundle_diameter_m` | decimal string |
| `bundle_peripheral_allowance_m` | decimal string |
| `bundle_outer_envelope_radius_m` | decimal string |
| `bundle_outer_envelope_diameter_m` | decimal string |
| `shell_to_bundle_radial_clearance_m` | decimal string |
| `shell_to_bundle_diametral_clearance_m` | decimal string |
| `required_minimum_radial_clearance_m` | decimal string |
| `radial_clearance_margin_m` | decimal string |
| `limiting_position_ids` | sorted unique tuple[string] |
| `position_count` | integer |
| `warnings` | tuple[`MessageEntry`] |
| `blockers` | empty tuple for valid result |
| `deferred_capabilities` | exact tuple[string] |
| `provenance` | deep-frozen canonical object |

### 7.12 `ShellBundleGeometryValidationResult`

Exact fields:

```text
status
geometry
warnings
blockers
deferred_capabilities
blocked_result_hash
```

For a valid result:

- `status == VALID`;
- `geometry` is complete;
- `blockers` is empty;
- `blocked_result_hash` is null.

For a blocked result:

- `status == BLOCKED`;
- `geometry` is null;
- blockers is non-empty;
- no partial dimensions or clearances are returned;
- `blocked_result_hash` is present.

## 8. Validation and computation pipeline

The implementation must use this stage order:

1. raw top-level type and exact-field validation;
2. schema-version validation;
3. raw nested type validation;
4. TASK-020 configuration verification;
5. TASK-021 layout verification;
6. TASK-020/TASK-021 cross-binding verification;
7. geometry-rule authority verification;
8. shell-diameter authority-mode and object verification;
9. explicit allowance and minimum-clearance validation;
10. position-count capacity guard;
11. bare bundle-envelope calculation;
12. shell/bundle clearance calculation;
13. minimum-clearance comparison;
14. warning derivation;
15. canonical request assembly and request hash;
16. provenance pre-hash assembly;
17. geometry payload assembly and geometry hash;
18. deterministic geometry UUID construction;
19. final invariant verification.

All independent defects within the same stage are accumulated. Later dependent
stages do not execute when their prerequisite stage is blocked. The system must
not return the first error only and must not return a partial geometry result.

## 9. Geometry-rule authority verification

The core verifies:

- exact profile ID;
- exact schema version;
- approval status;
- closed authority mode;
- closed shell authority-mode allowlist;
- canonical hash of the complete snapshot excluding `snapshot_hash`;
- source-class/runtime compatibility;
- license evidence;
- provenance edge IDs;
- rule-pack identity presence or absence by mode;
- finite non-negative minima;
- positive maximum position count.

The core does not load a rule pack, inspect a filesystem path, query a database or
call a network service.

## 10. Shell-geometry authority verification

### 10.1 Caller-supplied authority

The core verifies:

- exact schema version;
- positive canonical shell ID;
- non-empty sorted unique evidence refs;
- authority hash recomputation;
- absence of approved catalog snapshot;
- rule authority permits caller-supplied mode.

### 10.2 Approved catalog snapshot

The core verifies:

- exact snapshot schema version;
- `geometry_type == shell`;
- approval state;
- positive canonical shell ID;
- complete source binding;
- upstream record hash lexical shape;
- TASK-022 snapshot hash recomputation;
- absence of caller-supplied authority;
- rule authority permits approved-catalog mode.

The core preserves but does not recompute the upstream `record_hash`, because the
upstream record body is not part of the TASK-022 core input. A future adapter must
verify that hash before constructing the snapshot.

## 11. Closed blocker set

The v1 blocker codes are exactly:

```text
SBG_SCHEMA_VERSION_UNSUPPORTED
SBG_UNKNOWN_FIELD
SBG_RAW_TYPE_INVALID
SBG_DECIMAL_LEXICAL_INVALID
SBG_TASK020_CONFIGURATION_MISSING
SBG_TASK020_CONFIGURATION_INVALID
SBG_TASK020_CONFIGURATION_IDENTITY_MISMATCH
SBG_TASK021_LAYOUT_MISSING
SBG_TASK021_LAYOUT_INVALID
SBG_TASK021_LAYOUT_HAS_BLOCKERS
SBG_TASK021_LAYOUT_IDENTITY_MISMATCH
SBG_LAYOUT_CONFIGURATION_BINDING_MISMATCH
SBG_LAYOUT_HAS_NO_POSITIONS
SBG_LAYOUT_POSITION_COUNT_EXCEEDED
SBG_TUBE_GEOMETRY_SNAPSHOT_INVALID
SBG_RULE_AUTHORITY_MISSING
SBG_RULE_PROFILE_UNSUPPORTED
SBG_RULE_AUTHORITY_MODE_INVALID
SBG_RULE_UNAPPROVED
SBG_RULE_SNAPSHOT_HASH_MISMATCH
SBG_RULE_LICENSE_BLOCKED
SBG_RULE_PROVENANCE_INCOMPLETE
SBG_SHELL_AUTHORITY_MODE_INVALID
SBG_SHELL_AUTHORITY_MODE_NOT_ALLOWED
SBG_CALLER_SHELL_DIAMETER_MISSING
SBG_CALLER_SHELL_DIAMETER_NOT_EXPECTED
SBG_CALLER_SHELL_AUTHORITY_HASH_MISMATCH
SBG_APPROVED_SHELL_GEOMETRY_MISSING
SBG_APPROVED_SHELL_GEOMETRY_NOT_EXPECTED
SBG_APPROVED_SHELL_GEOMETRY_TYPE_INVALID
SBG_APPROVED_SHELL_GEOMETRY_UNAPPROVED
SBG_APPROVED_SHELL_SOURCE_INCOMPLETE
SBG_APPROVED_SHELL_SNAPSHOT_HASH_MISMATCH
SBG_SHELL_INSIDE_DIAMETER_INVALID
SBG_BUNDLE_PERIPHERAL_ALLOWANCE_INVALID
SBG_BUNDLE_PERIPHERAL_ALLOWANCE_BELOW_RULE_MINIMUM
SBG_REQUIRED_MINIMUM_CLEARANCE_INVALID
SBG_REQUIRED_MINIMUM_CLEARANCE_BELOW_RULE_MINIMUM
SBG_BUNDLE_ENVELOPE_CALCULATION_FAILED
SBG_SHELL_NOT_LARGER_THAN_BUNDLE
SBG_RADIAL_CLEARANCE_BELOW_REQUIRED_MINIMUM
SBG_CANONICALIZATION_FAILED
```

No implementation may emit an undeclared blocker or repurpose a code for a
second semantic. Reserved aliases are forbidden.

### 11.1 Blocker payload rules

Each blocker must contain:

- exact code;
- exact field path or null;
- stable message key;
- sorted unique evidence refs;
- complete canonical details required to reproduce the decision.

String-only exceptions, three-field blockers and message-text parsing are
forbidden.

### 11.2 Deterministic blocker ordering

Blockers are sorted by:

```text
(
  validation_stage_rank,
  code,
  field_path or "",
  message_key,
  sha256(canonical_json(details)),
  sha256(canonical_json(evidence_refs))
)
```

## 12. Closed warning set

The v1 warning codes are exactly:

```text
SBG_INTERNAL_GENERIC_NO_STANDARD_CLAIM
SBG_CALLER_SUPPLIED_SHELL_DIAMETER_NO_CATALOG_SELECTION
SBG_ZERO_BUNDLE_PERIPHERAL_ALLOWANCE
SBG_ZERO_REQUIRED_MINIMUM_RADIAL_CLEARANCE
SBG_GEOMETRIC_CLEARANCE_NOT_MECHANICAL_ADEQUACY
SBG_FIXED_TUBESHEET_THERMAL_EXPANSION_DEFERRED
SBG_UTUBE_BEND_AND_PULL_CLEARANCE_DEFERRED
SBG_FLOATING_HEAD_HARDWARE_AND_PULL_CLEARANCE_DEFERRED
SBG_BAFFLE_GEOMETRY_DEFERRED
SBG_PASS_PARTITION_ASSIGNMENT_DEFERRED
```

Warnings use the same five-field `MessageEntry` shape. They are derived only after
all blocker stages succeed. Blocked results suppress calculation-dependent
warnings.

Warning ordering is:

```text
(code, field_path or "", message_key,
 sha256(canonical_json(details)),
 sha256(canonical_json(evidence_refs)))
```

## 13. Deferred capabilities

Every valid or blocked validation result carries this exact ordered tuple:

```text
BAFFLE_DESIGN_NOT_COMPUTABLE
PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE
NOZZLE_AND_FLOW_PATH_DESIGN_NOT_COMPUTABLE
UTUBE_BEND_GEOMETRY_NOT_COMPUTABLE
SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE
KERN_SCREENING_NOT_COMPUTABLE
BELL_DELAWARE_NOT_COMPUTABLE
SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE
TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE
VIBRATION_NOT_COMPUTABLE
THERMAL_EXPANSION_NOT_COMPUTABLE
MECHANICAL_BOUNDARY_NOT_COMPUTABLE
MATERIAL_SELECTION_NOT_COMPUTABLE
MASS_NOT_COMPUTABLE
COST_NOT_COMPUTABLE
OPTIMIZATION_NOT_COMPUTABLE
API_NOT_COMPUTABLE
REPORT_NOT_COMPUTABLE
GOLDEN_VALIDATION_NOT_COMPUTABLE
```

TASK-022 must not remove a deferred marker merely because enough data appears to
permit an informal estimate.

## 14. Canonical identities and hash pipeline

### 14.1 Snapshot hashes

Each TASK-022 authority snapshot hash is SHA-256 over canonical JSON containing
every field except the hash field itself.

Upstream TASK-016 record hashes, TASK-012 rule artifact hashes, TASK-020
configuration hashes, TASK-021 layout hashes and TASK-022 snapshot hashes are
distinct identities and must not be substituted for one another.

### 14.2 Request hash

`request_hash` covers every computation-authority field:

- complete TASK-020 configuration canonical payload;
- complete TASK-021 layout canonical payload;
- complete geometry-rule authority snapshot;
- shell authority mode;
- complete selected shell authority object;
- explicit bundle allowance and evidence;
- explicit minimum radial clearance and evidence;
- request evidence refs;
- schema version.

It excludes runtime-now, hostname, process ID, filesystem path and environment.

### 14.3 Provenance pre-hash

The provenance pre-hash projection contains:

- task ID and design-contract path;
- TASK-020 configuration ID/hash and case authority;
- TASK-021 layout ID/hash and embedded tube-geometry snapshot hash;
- shell/bundle rule identity and snapshot hash;
- shell authority mode and selected authority identity/hash;
- evidence refs;
- request hash;
- software version and Git commit supplied explicitly by the caller;
- canonical warnings;
- exact deferred-capability tuple.

It excludes geometry ID and geometry hash.

### 14.4 Geometry hash

`geometry_hash` is SHA-256 over canonical JSON containing every final result field
except:

- `geometry_id`;
- `geometry_hash`;
- `blockers`, which is always empty for a valid result.

The hash includes request hash, all dimensions, all clearances, limiting position
IDs, complete authorities, warnings, deferred capabilities and final provenance.

### 14.5 Geometry UUID

`geometry_id` is deterministic UUIDv5 under a TASK-022 namespace and uses the
lowercase `geometry_hash` hex string as the name input.

### 14.6 Blocked-result hash

A blocked-result hash covers:

- canonical raw request projection to the last successfully parsed stage;
- complete ordered blockers, including details and evidence;
- warnings permitted before the blocking stage;
- exact deferred capabilities;
- design-contract path and task ID.

No partial geometry dimensions enter a blocked result.

## 15. Provenance contract

The final provenance object equals the pre-hash projection plus only:

```text
geometry_hash
```

It records the deterministic transformation performed and preserves all upstream
identities as separate fields. It creates no new source claim.

The result must not record runtime-current timestamps, local file paths, hostnames
or process IDs. Any time or approval value must come from explicit upstream
source evidence.

## 16. Standards, licensing and restricted-content boundary

TASK-022 inherits TASK-012 without modification.

Permitted repository content is limited to:

- generic circle and distance mathematics;
- explicit caller constraints;
- source pointers and evidence references;
- approved evaluated rule artifacts;
- approved geometry snapshots;
- internal generic rules carrying `NO_STANDARD_CLAIM`.

The repository and public artifacts must not contain copied restricted standard
tables, shell-size series, clearance tables, clauses, figures, formula images,
vendor-proprietary catalogs or customer data.

TASK-022 validity is not certification or legal compliance.

## 17. Future implementation architecture

A separately authorized implementation may use:

```text
src/hexagent/exchangers/shell_tube/shell_bundle_geometry/
```

Maximum initial core modules:

- `models.py`;
- `schema.py`;
- `authority.py`;
- `geometry.py`;
- `canonical.py`;
- `validation.py`;
- `__init__.py`.

Later separately authorized adapters may add:

- `shell_geometry_adapter.py`;
- `rule_pack_adapter.py`.

The deterministic core remains pure and performs no filesystem, database,
network, environment, clock, locale, directory-scan or global-registry I/O.

## 18. Implementation slicing

### 18.1 Slice A — deterministic core

A future Slice A may implement only:

- exact immutable models and schemas;
- TASK-020 configuration identity verification;
- TASK-021 layout identity and cross-binding verification;
- authority snapshot validation and hashes;
- Decimal bundle-envelope mathematics;
- explicit shell/bundle clearance calculation;
- canonical request/result/blocked identities;
- deterministic warnings, blockers, provenance and deferred capabilities;
- synthetic mathematical tests.

### 18.2 Slice B — source adapters

A future Slice B may implement approved source adapters only after Slice A merge
and runtime authority reverification.

The shell adapter may exact-select one approved shell record by explicit ID. The
rule adapter may consume one real loaded and validated TASK-012 rule pack. Neither
adapter may introduce hidden defaults, nearest-size selection or copied
restricted content.

### 18.3 Excluded slices

Baffles, pass assignment, nozzles, thermal rating, Kern, Bell-Delaware, pressure
drop, vibration, thermal expansion, pressure-vessel adequacy, materials, mass,
cost, optimization, API, report and Golden integration are not TASK-022 slices.

## 19. Maximum future repository allowlist

A later implementation authorization may name an exact subset of:

```text
src/hexagent/exchangers/shell_tube/shell_bundle_geometry/**
tests/exchangers/shell_tube/shell_bundle_geometry/**
tests/fixtures/task022/**
ci-shard-manifest.yml
```

TASK-020 and TASK-021 production/test files, parent package `__init__.py`,
workflows, dependencies, lockfiles and existing fixtures are excluded unless a
later explicit amendment names exact files and source authority.

## 20. Frozen future test expectations

A future implementation must prove at least:

1. exact top-level and nested field sets;
2. unknown fields block;
3. raw types are checked before coercion;
4. booleans are rejected for integer fields;
5. canonical JSON-domain rejection is fail-closed;
6. decimal lexical rules are exact;
7. duplicate arrays block rather than silently deduplicate;
8. complete TASK-020 identity verification;
9. complete TASK-021 identity verification;
10. TASK-020/TASK-021 cross-binding mismatch blocks;
11. blocked TASK-021 layouts are rejected;
12. empty position arrays block;
13. placement-envelope diameter is never used as shell or bundle diameter;
14. bare bundle envelope is derived from accepted positions and tube OD only;
15. limiting position IDs are stable and sorted;
16. multiple equal limiting positions are retained;
17. negative coordinates produce the same radial extent as their symmetric peers;
18. Decimal square-root behavior is deterministic;
19. shell authority modes are closed;
20. exactly one shell authority object is present;
21. caller-supplied authority hash is recomputed;
22. approved shell snapshot hash is recomputed;
23. upstream shell record hash remains separate and is not fabricated;
24. approved shell snapshot requires complete source binding;
25. exact shell catalog selection is adapter-only;
26. nearest-size and first-fit selection are absent;
27. rule profile ID is exact;
28. rule snapshot hash is recomputed;
29. internal generic mode carries `NO_STANDARD_CLAIM`;
30. approved-rule-pack mode requires rule-pack identity;
31. restricted source classes are runtime-forbidden;
32. vendor permission scope is enforced;
33. bundle peripheral allowance is explicit;
34. zero allowance emits the exact warning;
35. allowance below rule minimum blocks;
36. minimum radial clearance is explicit;
37. zero minimum emits the exact warning;
38. minimum below rule minimum blocks;
39. bundle outer envelope equals bare radius plus allowance;
40. shell radius equals shell ID divided by two;
41. radial and diametral clearance formulas are exact;
42. zero shell-to-bundle clearance blocks;
43. negative shell-to-bundle clearance blocks;
44. clearance below explicit minimum blocks;
45. clearance equality with explicit minimum is accepted;
46. radial clearance margin is exact;
47. fixed-tubesheet deferred warning is exact;
48. U-tube deferred warning is exact;
49. floating-head deferred warning is exact;
50. no baffle output exists;
51. no pass-partition output exists;
52. no shell-side flow area or hydraulic diameter exists;
53. no thermal coefficient or pressure drop exists;
54. no mechanical thickness or material output exists;
55. request hash covers every computation-authority field;
56. evidence order normalization is deterministic;
57. warnings use exact five-field payloads;
58. blockers use exact five-field payloads;
59. same-stage multi-blocker accumulation is complete;
60. blocker ordering is stable;
61. blocked-result hash retains blocker details and evidence;
62. valid result has empty blockers and null blocked hash;
63. blocked result contains no partial geometry;
64. provenance pre-hash excludes geometry ID/hash;
65. geometry hash excludes geometry ID/hash;
66. final provenance equals pre-hash projection plus only geometry hash;
67. geometry UUID is stable;
68. host, locale and process changes do not affect identities;
69. no filesystem, database, network, environment or clock call occurs in core;
70. restricted standard/vendor content is absent;
71. TASK-019 cost-stack authority remains separate;
72. TASK-023 through TASK-039 remain unallocated.

Synthetic geometry fixtures are mathematical contract tests, not engineering
Goldens or standard-size recommendations.

## 21. CI expectations

A future implementation PR must pass:

- Ruff lint;
- Ruff format check;
- mypy;
- focused TASK-022 tests;
- existing TASK-020 tests unchanged;
- existing TASK-021 tests unchanged;
- TASK-012/TASK-016 regressions where adapters are involved;
- architecture tests;
- global collection for supported Python versions;
- merge-ref collection;
- manifest verification;
- complete exact-head CI.

This design branch itself must preserve exactly one changed repository file before
any later PR authorization can be considered.

## 22. Explicit non-actions

This design contract does not authorize:

- production code, tests, fixtures, CI manifest, workflows, dependencies or
  lockfile mutation;
- implementation Issue, implementation branch, commit or PR;
- shell-size catalog creation;
- remembered or copied shell-size tables;
- baffle count, spacing, cut, orientation, window or diameter;
- pass partitioning, nozzles or flow paths;
- shell-side or tube-side heat-transfer coefficients;
- Kern, Bell-Delaware, leakage or bypass correction;
- pressure-drop decomposition;
- vibration or thermal-expansion calculation;
- shell wall thickness, allowable stress, pressure rating, tubesheet, flange,
  support or pressure-vessel design;
- materials, mass, cost or optimization;
- API, persistence, CLI, report or Golden integration;
- mutation of TASK-001 through TASK-021;
- import of TASK-019 Amendment 002-K cost-stack scope;
- allocation of TASK-023 through TASK-039;
- Ready, merge, Issue closure, review dismissal, thread resolution or branch
  deletion without separate Charles authorization.

## 23. Personal review acceptance criteria

The design is eligible for Charles personal review only when:

- exactly this file is changed;
- the branch is based on the frozen authoring base;
- the allocation is stated exactly;
- complete TASK-020 and TASK-021 inputs are required;
- placement envelope, bare bundle diameter and shell ID remain distinct;
- shell authority modes are closed and mutually exclusive;
- core shell-size selection is forbidden;
- generic bundle-envelope mathematics is exact;
- allowance and minimum-clearance inputs are explicit;
- no hidden standard/vendor default exists;
- warning and blocker closed sets are complete;
- no partial result is permitted;
- hash and provenance pipelines are constructible;
- source gaps fail closed;
- restricted content is absent;
- all excluded capabilities remain deferred;
- TASK-023 through TASK-039 remain unallocated.

CI success alone does not authorize Ready or merge.

## 24. Closeout and next gate

Issue #143 remains open while the design is unreviewed or unmerged. The design
branch must not be deleted without separate authorization.

After this one-file authoring is audited, Charles may separately authorize Draft
PR creation. Ready, merge, Issue closure and every implementation slice require
independent authority.

```text
TASK022_ALLOCATION_FROZEN
TASK022_ONE_FILE_DESIGN_AUTHORED
IMPLEMENTATION_NOT_AUTHORIZED
PR_NOT_AUTHORIZED
READY_NOT_AUTHORIZED
MERGE_NOT_AUTHORIZED
ISSUE_143_OPEN
TASK023_THROUGH_TASK039_UNALLOCATED
```
