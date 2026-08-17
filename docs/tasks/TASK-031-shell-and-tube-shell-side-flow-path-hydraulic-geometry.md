# TASK-031 — Shell-and-Tube Shell-Side Flow-Path Hydraulic Geometry Foundation

> Binding design contract for the fifth M3 shell-and-tube capability.
>
> TASK-031 consumes one complete accepted TASK-021 tube-layout authority and one
> complete accepted TASK-024 baffle-geometry public validation result and
> produces deterministic shell-side screening hydraulic geometry for exactly:
>
> `CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1`
>
> TASK-031 v1 computes only:
>
> - `central_crossflow_flow_area_m2`
> - `shell_side_equivalent_hydraulic_diameter_m`
>
> plus flow-region identity, upstream identity bindings, engineering authority
> identity, warnings, blockers, deferred capabilities, provenance, and
> deterministic result identity.
>
> TASK-031 v1 does not calculate mass flow, mass velocity, Reynolds number,
> Prandtl number, heat-transfer coefficients, Nusselt number, friction factor,
> pressure drop, Bell–Delaware corrections, overall U, UA, LMTD, duty, outlet
> temperatures, two-phase behavior, vibration, mechanical adequacy, materials,
> mass, cost, optimization, API, persistence, CLI, reports, or engineering
> Goldens.

## 1. Authority, allocation, baseline, and status

| Field | Binding value |
|---|---|
| Repository | `xuezhiorange-png/hxforge-agent` |
| Allocation authority | Issue #180 — TASK-031 allocation |
| Source-definition authority | Issue #181 |
| Source-definition R1 amendment comment | `5311114363` |
| Source-definition R1 freeze comment | `5311125407` |
| Engineering source/formula authority freeze comment | `5311936966` |
| TASK-024 PR | #182 |
| TASK-024 implementation commit | `bda9e8094cd69f1abd25648d32651c114a98ef8e` |
| TASK-024 merge commit | `4add89515e1efa17e8af71f670d30a8df7fc85fb` |
| TASK-024 post-merge CI | run `31992782600`, `completed/success` |
| Authoring base | `main@4add89515e1efa17e8af71f670d30a8df7fc85fb` |
| Design branch | `docs/task-031-shell-side-flow-path-hydraulic-geometry-design` |
| Design file | `docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md` |
| Frozen allocation | `TASK-031 = Shell-and-Tube Shell-Side Flow-Path Hydraulic Geometry Foundation` |
| First-slice profile | `CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1` |
| Design status | `PROPOSED` |
| Implementation status | `NOT AUTHORIZED` |
| Draft PR status | `NOT AUTHORIZED` |
| Ready status | `NOT AUTHORIZED` |
| Merge status | `NOT AUTHORIZED` |
| Issue close | `NOT AUTHORIZED` |

```text
TASK031_PREREQUISITE_A=SATISFIED_MERGED_DELIVERY
TASK031_PREREQUISITE_B=SATISFIED_ENGINEERING_SOURCE_AUTHORITY_FROZEN
TASK031_PRE_DESIGN_PREREQUISITES_SATISFIED=true
```

This design authoring gate permits one branch and this one repository design
file. Authoring this document does **not** freeze or approve the design. A
separate review gate is required.

```text
DESIGN_MAY_SELECT_ENGINEERING_FORMULA=false
DESIGN_MAY_SUBSTITUTE_ENGINEERING_FORMULA=false
DESIGN_MAY_FALLBACK_ENGINEERING_FORMULA=false
```

Engineering formulas are consumed exactly from Issue #181 comment `5311936966`.
No design-time formula selection, substitution, or fallback is permitted.

## 2. Exact allocation and problem statement

TASK-031 owns the deterministic hydraulic-geometry boundary between accepted
TASK-024 baffle geometry and later shell-side thermal or hydraulic rating work.

TASK-021 establishes immutable tube layout, pitch, pattern family, and approved
tube geometry. TASK-024 establishes baffle geometry, spacing sequence, and
public shell inside diameter and tube outside diameter on its validation
result. TASK-031 must not re-own, recompute, or reclassify any TASK-024
geometry.

TASK-031 therefore must:

1. validate and replay complete TASK-021 and TASK-024 accepted public values;
2. verify TASK-021/TASK-024 identity and cross-binding contracts;
3. extract uniform central inter-baffle spacing under frozen semantics;
4. apply frozen engineering formulas A and B from comment `5311936966`;
5. emit immutable hydraulic geometry, hashes, blockers, warnings, deferred
   capabilities, and provenance;
6. fail closed with no partial geometry.

TASK-031 establishes screening hydraulic geometry identity only. It does not
establish thermal, hydraulic-rating, mechanical, manufacturing, procurement,
inspection, certification, or legal-compliance adequacy.

## 3. Scope and non-scope

### 3.1 Frozen v1 first-slice scope

```text
TASK031_FIRST_SLICE_PROFILE=CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1

IN_SCOPE_ENGINEERING_QUANTITIES:
  central_crossflow_flow_area_m2
  shell_side_equivalent_hydraulic_diameter_m

IN_SCOPE_IDENTITY:
  flow_region_identity=CENTRAL_CROSSFLOW_SCREENING
  upstream TASK020/TASK021/TASK022/TASK024 transitive identity bindings
  engineering authority identity

SUPPORTED_PATTERN_FAMILIES=(SQUARE, TRIANGULAR)
```

### 3.2 Explicitly deferred geometry quantities

```text
WINDOW_FLOW_AREA=DEFERRED
PER_COMPARTMENT_CROSSFLOW_AREA_SET=DEFERRED
MINIMUM_ADMITTED_FLOW_AREA=DEFERRED
INLET_REGION_FLOW_AREA=DEFERRED
OUTLET_REGION_FLOW_AREA=DEFERRED
LEAKAGE_FLOW_AREA=DEFERRED
BYPASS_FLOW_AREA=DEFERRED
MINIMUM_AREA_SELECTION=false
```

### 3.3 Explicitly prohibited non-scope

```text
MASS_FLOW
MASS_VELOCITY
BULK_VELOCITY
REYNOLDS_NUMBER
PRANDTL_NUMBER
FLOW_REGIME
HEAT_TRANSFER_COEFFICIENT
NUSSULT_NUMBER
FRICTION_FACTOR
PRESSURE_DROP
BELL_DELAWARE
OVERALL_U
UA
LMTD
HEAT_DUTY
OUTLET_TEMPERATURES
TWO_PHASE
COMPRESSIBLE_PATH_INTEGRATION
WALL_TEMPERATURE_ITERATION
VIBRATION
MECHANICAL_ADEQUACY
MATERIALS
MASS
COST
OPTIMIZATION
PUBLIC_API_EXTENSION
PERSISTENCE
CLI
REPORTING
TASK032
TASK033
TASK034
```

## 4. Frozen engineering formulas

Engineering authority is frozen by Issue #181 comment `5311936966`. The design
reproduces these formulas without modification.

### 4.1 Formula A — central crossflow flow area

```text
FORMULA_ID=TASK031_CF_AREA_KERN_SCREENING_INTCHOPN_EQ55_56_V1
PUBLIC_ENGINEERING_QUANTITY=central_crossflow_flow_area_m2

central_crossflow_flow_area_m2
=
shell_inside_diameter_m
*
central_inter_baffle_spacing_m
*
(pitch_m - tube_outside_diameter_m)
/
pitch_m

Equivalent source form:
As = (Ds/Pt) * B * Ct
Ct = Pt - do

PRIMARY_SOURCE=SRC-INTECHOPEN-100450-KHARAJI-2021
EXACT_SOURCE_LOCATION=§4.4 "Shell diameter", Eq. (55)-(56)
CROSSFLOW_AREA_DIMENSIONAL_CHECK=PASS
```

### 4.2 Formula B — shell-side equivalent hydraulic diameter

```text
FORMULA_ID=TASK031_DE_KERN_SCREENING_INTCHOPN_EQ51_BRANCH_V1
PUBLIC_ENGINEERING_QUANTITY=shell_side_equivalent_hydraulic_diameter_m

GENERAL:
De = 4 * free_flow_area_per_tube_cell / wetted_perimeter_per_tube_cell

SQUARE branch (IntechOpen Eq. 52):
De = 4 * (Pt^2 - pi*do^2/4) / (pi*do)

TRIANGULAR branch (IntechOpen Eq. 53):
De = 4 * (sqrt(3)/4*Pt^2 - pi*do^2/8) / (pi*do/2)

Equivalent exact triangular form:
De = (2*sqrt(3)*Pt^2 - pi*do^2) / (pi*do)

PRIMARY_SOURCE=SRC-INTECHOPEN-100450-KHARAJI-2021
EXACT_SOURCE_LOCATION=§4.4 "Shell diameter", Eq. (51)-(53)
EQUIVALENT_DIAMETER_DIMENSIONAL_CHECK=PASS
```

Repository authority uses exact symbolic `2*sqrt(3)`. The rounded coefficient
`3.46` from OU corroboration must not be substituted.

### 4.3 Pattern-family branch dispatch

```text
pattern_family == SQUARE     -> Formula B square branch
pattern_family == TRIANGULAR -> Formula B triangular branch
any other token              -> BLOCKED
```

Formula A is common to both admitted families.

## 5. Direct upstream contract

```text
TASK031_DIRECT_UPSTREAM=TASK021,TASK024
TASK020_DIRECT_INPUT=false
TASK022_DIRECT_INPUT=false
TASK020_TRANSITIVE_IDENTITY_REQUIRED=true
TASK022_TRANSITIVE_IDENTITY_REQUIRED=true
```

TASK-031 consumes complete accepted upstream values, not ID-only projections.

### 5.1 TASK-021 accepted input

The public raw request carries a complete accepted `TubeLayout` public model
exactly as produced by TASK-021 validation. Minimum replay fields include:

- `schema_version`
- `layout_id`, `layout_hash`
- `task020_configuration_id`, `task020_configuration_hash`
- `task022_geometry_id`, `task022_geometry_hash`
- `layout_rule_authority.pattern_family`
- `layout_rule_authority.pitch_m`
- `tube_geometry.outer_diameter_m`
- `status == VALID`
- `blockers == ()`

### 5.2 TASK-024 accepted input

The public raw request carries a complete accepted
`BaffleGeometryValidationResult` public model exactly as produced by TASK-024
`validate_request`.

Acceptance requires:

```text
task024_result.status == VALID
task024_result.geometry is not None
task024_result.blockers == ()
```

No lookalike object, duck typing, or partial projection is permitted.

### 5.3 Frozen consumer bindings

```text
shell_inside_diameter_m
  <- task024_result.geometry.shell_inside_diameter_m

spacing_sequence
  <- task024_result.geometry.design_authority.spacing_sequence_m

tube_outside_diameter_m
  <- task024_result.geometry.tube_outer_diameter_m

pitch_m
  <- task021_layout.layout_rule_authority.pitch_m

pattern_family
  <- task021_layout.layout_rule_authority.pattern_family

task021_tube_outer_diameter_m
  <- task021_layout.tube_geometry.outer_diameter_m
```

Required cross-binding:

```text
task024_result.geometry.tube_outer_diameter_m
==
task021_layout.tube_geometry.outer_diameter_m
```

TASK-031 must replay existing TASK-021 and TASK-024 identity/hash contracts
using their canonical helpers. It must not create a second definition of those
upstream hashes.

### 5.4 Forbidden upstream behavior

```text
PITCH_RECONSTRUCTION_FROM_COORDINATES
LAYOUT_RECONSTRUCTION_FROM_COORDINATES
TASK024_BAFFLE_GEOMETRY_RECOMPUTATION
TASK024_WINDOW_CROSSFLOW_RECLASSIFICATION
TASK024_BAFFLE_CUT_RECOMPUTATION
TASK024_CLEARANCE_RECOMPUTATION
TASK024_BAFFLE_PLANE_REBUILD
```

## 6. Central spacing contract

```text
N = task024_result.geometry.design_authority.baffle_count
S = task024_result.geometry.design_authority.spacing_sequence_m

MINIMUM_BAFFLE_COUNT_FOR_CENTRAL_CROSSFLOW_PROFILE=2

S[0] = inlet spacing
S[1]..S[N-1] = inter-baffle spacings
S[N] = outlet spacing

CENTRAL_SPACING_INDEX_RANGE=S[1:N]

Requirements:
  N >= 2
  len(S) == N + 1
  len(S[1:N]) >= 1
  all values in S[1:N] exactly equal under unquantized Decimal comparison

central_inter_baffle_spacing_m = unique common value in S[1:N]

INLET_SPACING_USED_FOR_CENTRAL_CROSSFLOW_AREA=false
OUTLET_SPACING_USED_FOR_CENTRAL_CROSSFLOW_AREA=false
UNEQUAL_CENTRAL_INTER_BAFFLE_SPACING=BLOCKED_FOR_TASK031_V1
```

No per-compartment area set may be emitted.

## 7. Applicability domain

```text
TASK031_APPLICABILITY_DOMAIN=
INTERSECTION(
  TASK021_ACCEPTED_DOMAIN,
  TASK024_ACCEPTED_DOMAIN,
  TASK031_ADMITTED_ENGINEERING_FORMULA_DOMAIN
)
```

```text
TASK031_ADMITTED_ENGINEERING_FORMULA_DOMAIN:
  construction_family=FIXED_TUBESHEET
  shell_pass_count=1
  baffle_type=SINGLE_SEGMENTAL
  baffle_count>=2
  pattern_family in {SQUARE, TRIANGULAR}
  uniform central inter-baffle spacing required
  flow_region_identity=CENTRAL_CROSSFLOW_SCREENING
```

Repository applicability may narrow source applicability. Repository
applicability must never broaden frozen source authority from comment
`5311936966`.

## 8. Leakage and bypass semantics

```text
LEAKAGE_BYPASS_TREATMENT=EXCLUDED_FROM_SELECTED_SCREENING_MODEL
PSEUDO_ZERO_ASSUMPTION_PRESENT=false
LEAKAGE_AREA_PHYSICALLY_ZERO_CLAIM=false
BYPASS_AREA_PHYSICALLY_ZERO_CLAIM=false
BELL_DELAWARE_CORRECTION_GEOMETRY_ADMITTED=false
```

The selected screening model does not own leakage or bypass correction paths.
TASK-031 must not infer `leakage_area=0` or `bypass_area=0`.

## 9. Engineering authority identity

```text
ENGINEERING_AUTHORITY_RECORD_MODEL=PER_FORMULA_PLUS_AGGREGATE
FORMULA_AUTHORITY_RECORD_COUNT=2
```

### 9.1 Schema and profile

```text
ENGINEERING_AUTHORITY_SCHEMA_VERSION=task031.engineering-authority.v1
AGGREGATE_AUTHORITY_PROFILE_ID=
  TASK031_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1_FORMULA_AUTHORITY
```

### 9.2 Frozen authority package

The runtime uses one immutable frozen `EngineeringAuthoritySnapshot` derived at
build time from comment `5311936966`. It contains:

- aggregate profile ID
- Issue #181 engineering-source freeze comment ID `5311936966`
- source ledger entries for all four frozen source IDs
- formula record A: `TASK031_CF_AREA_KERN_SCREENING_INTCHOPN_EQ55_56_V1`
- formula record B: `TASK031_DE_KERN_SCREENING_INTCHOPN_EQ51_BRANCH_V1`
- supported pattern families `(SQUARE, TRIANGULAR)`
- admitted applicability envelope
- permission state `LAWFUL_PUBLIC_ACCESS_REUSE_WITH_ATTRIBUTION`
- IntechOpen license `CC BY 3.0`

### 9.3 Authority hash and ID

```text
engineering_authority_hash =
  sha256_hex(canonical_json_bytes(authority_canonical_projection))

engineering_authority_id =
  urn:hxforge:task031:engineering-authority:v1:{engineering_authority_hash}
```

`authority_canonical_projection` is a frozen key-ordered mapping containing only
canonical JSON domain values. No runtime GitHub, DOI, PDF, or network lookup is
permitted to populate or verify authority content at runtime. The snapshot is a
package constant replaying the frozen comment.

### 9.4 Request authority binding

The public raw request must carry `engineering_authority` with:

- `schema_version` exact `task031.engineering-authority-request.v1`
- `authority_profile_id` exact aggregate profile ID above
- `authority_hash` exact frozen hash above
- `evidence_refs` non-empty sorted unique tuple

Mismatch blocks with `SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH`.

## 10. Runtime source behavior

The deterministic core must not:

- perform network lookup
- read source PDFs
- read GitHub Issues
- fetch DOI content
- scan rule packs
- choose engineering sources
- choose alternate formulas

Engineering authority is design-time frozen. Runtime replays immutable package
constants only.

## 11. Numeric, Decimal, and quantization discipline

### 11.1 Forbidden numeric types

Binary floating-point is forbidden in all geometry calculations, boundary
predicates, formula evaluation, canonical projections, and hash inputs.

### 11.2 Frozen Decimal context

```text
DECIMAL_PRECISION=50
ROUNDING_MODE=ROUND_HALF_EVEN
```

All arithmetic uses `decimal.Decimal` under:

```python
decimal.Context(prec=50, rounding=decimal.ROUND_HALF_EVEN)
```

Local contexts must not weaken this contract.

### 11.3 Frozen mathematical constants

```text
PI_REPRESENTATION=
  Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208628620898062808825348")

SQRT3_REPRESENTATION=
  Decimal("1.7320508075688772935274463415058723669428052538103806280558069794519330169088000370811461867572485756")
```

`sqrt(3)` is not computed from `sqrt()` at runtime for formula authority
evaluation. The frozen `SQRT3_REPRESENTATION` constant is the sole triangular
branch coefficient source.

`pi` is not imported from `math` or `cmath`. The frozen `PI_REPRESENTATION`
constant is the sole circular-geometry coefficient source.

### 11.4 Output quanta

```text
LENGTH_OUTPUT_QUANTUM_M=0.000000000001
AREA_OUTPUT_QUANTUM_M2=0.000000000000000000000001
DIAMETER_OUTPUT_QUANTUM_M=0.000000000001
```

`AREA_OUTPUT_QUANTUM_M2` is exactly `LENGTH_OUTPUT_QUANTUM_M ** 2`.

### 11.5 Quantization ordering

```text
HIGH_PRECISION_DECIMAL_DERIVATION
AND BOUNDARY_PREDICATE_EVALUATION
THEN
PUBLIC_OUTPUT_QUANTIZATION
```

Boundary predicates for validity (`pitch_m > tube_outside_diameter_m`,
computed area > 0, computed diameter > 0, central spacing uniformity) execute on
unquantized Decimal values. Public output strings are produced only after
predicates pass.

If quantization of a positive unquantized value collapses to canonical zero,
the result is `SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION` or
`SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION`.

### 11.6 Public decimal lexical domain

Every public numeric field is a canonical finite base-10 decimal string:

- no exponent notation
- no leading `+`
- no surrounding whitespace
- no NaN or Infinity
- negative zero normalizes to `0`
- field-specific sign rules enforced

### 11.7 Python 3.11 / 3.12 identity

The frozen Decimal context, constant strings, quantization rules, and canonical
JSON projection must produce byte-identical public outputs on Python 3.11 and
3.12.

## 12. Closed schema versions and identities

```text
REQUEST_SCHEMA_VERSION=task031.shell-side-hydraulic-geometry-request.v1
RESULT_SCHEMA_VERSION=task031.shell-side-hydraulic-geometry.v1
ENGINEERING_AUTHORITY_SCHEMA_VERSION=task031.engineering-authority.v1
ENGINEERING_AUTHORITY_REQUEST_SCHEMA_VERSION=task031.engineering-authority-request.v1
PROFILE_ID=hxforge.shell_tube.shell_side_hydraulic_geometry.v1
DESIGN_CONTRACT_PATH=docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md
```

## 13. Public raw request schema

`ALTERNATIVE_REQUEST_SHAPES=false`

The top-level raw request is an exact built-in `dict` with string keys and
exactly this field set:

| Field | Requirement |
|---|---|
| `schema_version` | exact `task031.shell-side-hydraulic-geometry-request.v1` |
| `tube_layout` | complete accepted TASK-021 `TubeLayout` public model |
| `baffle_geometry_result` | complete accepted TASK-024 `BaffleGeometryValidationResult` |
| `engineering_authority` | exact built-in `dict` per §9.4 |
| `evidence_refs` | non-empty `list[str]`, sorted unique after validation |

Forbidden:

- unknown top-level or nested fields
- custom `Mapping` subclasses
- aliases or coercion
- binary float anywhere
- partial upstream objects
- ID-only upstream projections

## 14. Public operation

```text
PUBLIC_CALCULATION_OPERATION_COUNT=1
```

```python
def validate_request(raw_request: Any) -> ShellSideHydraulicGeometryValidationResult:
    ...
```

Non-exported helpers:

```python
def parse_request(raw_request: Any) -> ShellSideHydraulicGeometryRequest: ...
def validate_typed_request(
    request: ShellSideHydraulicGeometryRequest,
) -> ShellSideHydraulicGeometryValidationResult: ...
```

No separate public `calculate_area()`, `calculate_de()`, or pattern-specific
public calculators are permitted.

## 15. Result models

### 15.1 `ShellSideHydraulicGeometry`

Successful geometry contains exactly:

| Field | Type / rule |
|---|---|
| `schema_version` | exact `task031.shell-side-hydraulic-geometry.v1` |
| `geometry_id` | deterministic URN |
| `geometry_hash` | `sha256_hex` |
| `request_hash` | `sha256_hex` |
| `task020_configuration_id` | from TASK-021 |
| `task020_configuration_hash` | from TASK-021 |
| `task021_layout_id` | from TASK-021 |
| `task021_layout_hash` | from TASK-021 |
| `task022_geometry_id` | from TASK-021/TASK-024 transitive binding |
| `task022_geometry_hash` | from TASK-021/TASK-024 transitive binding |
| `task024_geometry_id` | from TASK-024 geometry |
| `task024_geometry_hash` | from TASK-024 geometry |
| `engineering_authority_id` | frozen authority ID |
| `engineering_authority_hash` | frozen authority hash |
| `formula_a_id` | `TASK031_CF_AREA_KERN_SCREENING_INTCHOPN_EQ55_56_V1` |
| `formula_b_id` | `TASK031_DE_KERN_SCREENING_INTCHOPN_EQ51_BRANCH_V1` |
| `pattern_family` | `SQUARE` or `TRIANGULAR` |
| `flow_region_identity` | `CENTRAL_CROSSFLOW_SCREENING` |
| `central_inter_baffle_spacing_m` | explicit retained output |
| `central_crossflow_flow_area_m2` | Formula A result |
| `shell_side_equivalent_hydraulic_diameter_m` | Formula B result |
| `warnings` | ordered tuple |
| `blockers` | empty on success |
| `deferred_capabilities` | closed tuple |
| `provenance` | canonical frozen mapping |

No window, minimum, inlet, outlet, leakage, or bypass area fields exist on the
successful geometry object.

### 15.2 `ShellSideHydraulicGeometryValidationResult`

| Field | Rule |
|---|---|
| `status` | `VALID` or `BLOCKED` |
| `geometry` | `ShellSideHydraulicGeometry` or `None` |
| `warnings` | ordered tuple |
| `blockers` | ordered tuple |
| `deferred_capabilities` | closed tuple |
| `blocked_result_hash` | non-null iff `BLOCKED` |

Any failure returns `status=BLOCKED`, `geometry=None`. No partial geometry.

## 16. Closed blocker taxonomy

`BLOCKER_CODE_COUNT=36`

```text
SSHG_SCHEMA_VERSION_UNSUPPORTED
SSHG_RAW_TYPE_INVALID
SSHG_UNKNOWN_FIELD
SSHG_DECIMAL_LEXICAL_INVALID
SSHG_EVIDENCE_REFS_INVALID

SSHG_TASK021_LAYOUT_MISSING
SSHG_TASK021_LAYOUT_INVALID
SSHG_TASK021_LAYOUT_HAS_BLOCKERS
SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH

SSHG_TASK024_RESULT_MISSING
SSHG_TASK024_RESULT_INVALID
SSHG_TASK024_RESULT_HAS_BLOCKERS
SSHG_TASK024_GEOMETRY_MISSING
SSHG_TASK024_IDENTITY_MISMATCH

SSHG_TASK021_TASK024_TUBE_OD_MISMATCH
SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH
SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH

SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED
SSHG_SHELL_PASS_COUNT_UNSUPPORTED
SSHG_BAFFLE_TYPE_UNSUPPORTED

SSHG_BAFFLE_COUNT_INSUFFICIENT
SSHG_SPACING_SEQUENCE_INVALID
SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT
SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM

SSHG_PATTERN_FAMILY_UNSUPPORTED

SSHG_PITCH_INVALID
SSHG_TUBE_OD_INVALID
SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD
SSHG_SHELL_INSIDE_DIAMETER_INVALID
SSHG_CENTRAL_INTER_BAFFLE_SPACING_INVALID

SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH
SSHG_FORMULA_DOMAIN_VIOLATION
SSHG_FORMULA_CALCULATION_FAILED

SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION
SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION

SSHG_CANONICALIZATION_FAILED
```

Codes are exact and cannot be aliased.

## 17. Closed warning taxonomy

`WARNING_CODE_COUNT=7`

```text
SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY
SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED
SSHG_MINIMUM_AREA_SELECTION_DEFERRED
SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED
SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED
SSHG_NO_FULL_EXCHANGER_RATING_CLAIM
SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY
```

Warnings must not be used for conditions that should block.

## 18. Deferred capabilities

`DEFERRED_CAPABILITY_COUNT=17`

```text
WINDOW_FLOW_AREA_NOT_COMPUTABLE
PER_COMPARTMENT_CROSSFLOW_AREA_SET_NOT_COMPUTABLE
MINIMUM_ADMITTED_FLOW_AREA_NOT_COMPUTABLE
INLET_REGION_FLOW_AREA_NOT_COMPUTABLE
OUTLET_REGION_FLOW_AREA_NOT_COMPUTABLE
LEAKAGE_FLOW_AREA_NOT_COMPUTABLE
BYPASS_FLOW_AREA_NOT_COMPUTABLE
SHELL_SIDE_FLOW_STATE_NOT_COMPUTABLE
SHELL_SIDE_HEAT_TRANSFER_SCREENING_NOT_COMPUTABLE
SHELL_SIDE_PRESSURE_DROP_SCREENING_NOT_COMPUTABLE
BELL_DELAWARE_NOT_COMPUTABLE
OVERALL_U_NOT_COMPUTABLE
UA_NOT_COMPUTABLE
LMTD_NOT_COMPUTABLE
HEAT_DUTY_NOT_COMPUTABLE
OUTLET_TEMPERATURES_NOT_COMPUTABLE
FULL_EXCHANGER_RATING_NOT_COMPUTABLE
```

## 19. Validation stages

1. raw schema parse and closed-field validation
2. engineering authority identity replay
3. TASK-021 completeness, validity, and identity replay
4. TASK-024 completeness, validity, and identity replay
5. TASK-021/TASK-024 cross-binding verification
6. applicability-domain verification
7. central spacing extraction
8. numeric validity predicates on unquantized Decimal inputs
9. Formula A evaluation
10. Formula B branch dispatch and evaluation
11. public output quantization
12. canonical serialization, hashes, IDs, provenance, final result

Any stage failure blocks. No partial geometry.

## 20. Canonical projections and hashes

TASK-031 uses repository `sha256_canonical` / frozen JSON conventions. It does
not create a competing generic canonical framework.

### 20.1 Request hash

```text
request_hash = sha256_hex(canonical_json_bytes(request_canonical_projection))
```

`request_canonical_projection` includes schema version, complete upstream
canonical projections, engineering authority binding, and evidence refs.

### 20.2 Geometry hash and ID

```text
geometry_hash = sha256_hex(canonical_json_bytes(geometry_canonical_projection))
geometry_id = urn:hxforge:task031:shell-side-hydraulic-geometry:v1:{geometry_hash}
```

### 20.3 Blocked result hash

```text
blocked_result_hash = sha256_hex(canonical_json_bytes(blocked_canonical_projection))
```

Blocked projection uses the complete raw request plus ordered blockers and
allowed prior-stage warnings.

### 20.4 Software / build identity

```text
IMPLEMENTATION_SOFTWARE_VERSION=task031.minimal-compute-v1
GIT_COMMIT=<frozen build constant pinned at implementation authorization>
```

No runtime `git` lookup. Ambient working-tree state must not affect identity.

## 21. Upstream replay helpers

TASK-031 must call existing upstream canonical/hash helpers for replay:

- TASK-021 layout hash and identity verification via `tube_layout.canonical`
- TASK-024 geometry hash and identity verification via `baffle_geometry.canonical`

TASK-031 must not duplicate upstream serializers.

## 22. Provenance contract

Provenance must retain at minimum:

```text
task_id=TASK031
design_contract_path
task020_configuration_id
task020_configuration_hash
task021_layout_id
task021_layout_hash
task022_geometry_id
task022_geometry_hash
task024_geometry_id
task024_geometry_hash
engineering_authority_profile_id
engineering_authority_hash
formula_a_id
formula_b_id
source_authority_freeze_issue=181
source_authority_freeze_comment_id=5311936966
source_ids=(four frozen IDs)
pattern_family
flow_region_identity=CENTRAL_CROSSFLOW_SCREENING
software_version
git_commit
request_hash
warnings
deferred_capabilities
```

No provenance field may claim a standard, formula, or correction model not
actually frozen.

## 23. Engineering verification vectors

Design-time vectors only. Expected implementation output must never be used as
formula authority.

| ID | Scenario | Expected |
|---|---|---|
| V1 | valid SQUARE | PASS; positive area and diameter |
| V2 | valid TRIANGULAR | PASS; positive area and diameter |
| V3 | minimum topology `N=2` | PASS |
| V4 | inlet/outlet differ, central uniform | PASS |
| V5 | unequal central spacing | `SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM` |
| V6 | `pitch_m == tube_outside_diameter_m` | `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD` |
| V7 | `pitch_m < tube_outside_diameter_m` | `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD` |
| V8 | unsupported pattern token | `SSHG_PATTERN_FAMILY_UNSUPPORTED` |
| V9 | TASK-021/TASK-024 tube OD mismatch | `SSHG_TASK021_TASK024_TUBE_OD_MISMATCH` |
| V10 | TASK-021 or TASK-024 identity mismatch | respective identity blocker |
| V11 | blocked TASK-024 producer | `SSHG_TASK024_RESULT_HAS_BLOCKERS` |
| V12 | VALID wrapper but `geometry=None` | `SSHG_TASK024_GEOMETRY_MISSING` |
| V13 | quantization collapse | area/diameter quantization blocker |
| V14 | authority identity mismatch | `SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH` |

### 23.1 Manual formula verification vector (independent SI oracle)

```text
Ds=0.25 m
B=0.125 m
Pt=0.025 m
do=0.019 m
pattern_family=SQUARE

As = 0.00750 m^2
De_square = 0.0228828797610251 m
De_triangular = 0.017271637856696855 m
```

```text
EXTERNAL_ORACLE_SOURCE_INDEPENDENT=true
EXPECTED_REPOSITORY_OUTPUT_USED_AS_AUTHORITY=false
FIXTURE_USED_AS_ENGINEERING_AUTHORITY=false
NPTEL_EXACT_ORACLE_INCLUDED=false
```

## 24. Future implementation package boundary

Reserved future package:

```text
src/hexagent/exchangers/shell_tube/shell_side_hydraulic_geometry/
```

This gate does not create production or test directories.

### 24.1 Proposed production allowlist

```text
models.py
schema.py
authority.py
formulas.py
validation.py
canonical.py
engineering_authority_snapshot.py
__init__.py
```

### 24.2 Proposed test allowlist

```text
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_models.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_schema.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_authority.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_formulas.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_validation.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_canonical.py
tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_architecture.py
```

Proposal is not implementation authorization.

## 25. Required future test matrix

Future tests must cover:

- model tests
- schema tests
- authority tests
- formula tests
- validation tests
- canonical/hash/UUID tests
- provenance tests
- architecture tests
- determinism tests
- independent engineering-oracle tests
- Python 3.11/3.12 compatibility tests

Required architecture assertions:

```text
NO_BINARY_FLOAT_GEOMETRY
NO_RUNTIME_NETWORK_OR_SOURCE_LOOKUP
NO_SECOND_ENGINEERING_FORMULA
NO_BELL_DELAWARE_IMPORT
NO_UPSTREAM_SERIALIZER_DUPLICATION
NO_TASK024_GEOMETRY_RECOMPUTATION
NO_COORDINATE_DERIVED_PITCH_OR_LAYOUT
EXACTLY_ONE_PUBLIC_CALCULATION_OPERATION
ONLY_SQUARE_AND_TRIANGULAR_ADMITTED
DEFERRED_AREAS_ABSENT_FROM_SUCCESS_RESULT
```

## 26. Architecture and forbidden I/O boundary

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
process-hash seeding
runtime git lookup
source PDF / Issue / DOI lookup
rule-pack scan
engineering-formula selection
```

## 27. Design-review checklist

`DESIGN_REVIEW_CHECK_COUNT=35`

| ID | Item | Authoring supplies contract |
|---|---|---|
| D01 | allocation matches Issue #180 | §1 |
| D02 | source-definition R1 preserved | §1, §4 |
| D03 | prerequisite A satisfied | §1 |
| D04 | prerequisite B frozen | §1, §4, §9 |
| D05 | first-slice profile exact | §3 |
| D06 | Formula A exact | §4.1 |
| D07 | Formula B exact | §4.2 |
| D08 | source identities exact | §4, §9 |
| D09 | source locations exact | §4 |
| D10 | pattern set exact | §3, §4.3 |
| D11 | TASK-021 direct binding exact | §5.1, §5.3 |
| D12 | TASK-024 public producer exact | §5.2, §5.3 |
| D13 | central spacing semantics exact | §6 |
| D14 | no inlet/outlet spacing use | §6 |
| D15 | applicability intersection exact | §7 |
| D16 | leakage/bypass semantics exact | §8 |
| D17 | deferred geometry complete | §3.2, §18 |
| D18 | request schema singular | §13 |
| D19 | result shape closed | §15 |
| D20 | blocker taxonomy closed | §16 |
| D21 | warning taxonomy closed | §17 |
| D22 | Decimal/pi/sqrt3 discipline exact | §11 |
| D23 | no binary float | §11.1 |
| D24 | canonical projections exact | §20 |
| D25 | request hash exact | §20.1 |
| D26 | authority hash exact | §9.3 |
| D27 | result hash/ID exact | §20.2 |
| D28 | blocked-result hash exact | §20.3 |
| D29 | provenance complete | §22 |
| D30 | no upstream reownership | §5.4, §21 |
| D31 | independent engineering vectors complete | §23 |
| D32 | determinism policy exact | §11, §20, §26 |
| D33 | Python 3.11/3.12 identity requirement | §11.7 |
| D34 | implementation allowlist only proposed | §24 |
| D35 | implementation remains unauthorized | §1, §24 |

This authoring gate does not mark checklist items PASS. Independent review is
required.

## 28. Explicit non-authorization statement

```text
IMPLEMENTATION_AUTHORIZED=false
TEST_AUTHORING_AUTHORIZED=false
CI_MANIFEST_MUTATION_AUTHORIZED=false
WORKFLOW_MUTATION_AUTHORIZED=false
PR_CREATION_AUTHORIZED=false
PUSH_AUTHORIZED=false
MERGE_AUTHORIZED=false
ISSUE_MUTATION_AUTHORIZED=false
TASK032_AUTHORIZED=false
TASK033_AUTHORIZED=false
TASK034_AUTHORIZED=false
```

Authoring this `PROPOSED` design contract does not authorize implementation,
tests, fixtures, CI changes, pull request creation, push, merge, or Issue
mutation.
