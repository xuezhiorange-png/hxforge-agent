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
```text
CORRECTED_DESIGN_READY_FOR_REREVIEW=true
THIRD_CORRECTION_PARENT_SHA=41e593319bbc03ed1ab49e595dc522aa8aa7e3ae
DESIGN_DOCUMENT_STATUS=PROPOSED
PRIOR_REVIEW_REPORTED_PASS_COUNT=21/35
PRIOR_REVIEW_LITERAL_TABLE_RECOUNT=20/35
NEXT_REREVIEW_RECOUNTS_D01_D35_FROM_SCRATCH=true
PRIOR_REVIEW_ACCOUNTING_INCONSISTENCY_NOTED=true
CORRECTION_PARENT_SHA=45ef6dfe4674ddef497584522167182c6559e1e2
SECOND_CORRECTION_PARENT_SHA=a6aa0b686fbf38b2757611ab55c1dae98fb1ebd5
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

```text
TASK021_CONSUMER_TYPE=TubeLayout
TASK021_STATUS_CHECK_PRESENT=false
TASK021_BLOCKERS_EMPTY_REQUIRED=true
```

The public raw request carries a complete accepted `TubeLayout` object exactly
as produced by TASK-021 validation. TASK-031 consumes `TubeLayout` directly, not
`TubeLayoutValidationResult`. `TubeLayout` has no `status` field; `status` is
owned by the outer `TubeLayoutValidationResult` wrapper and is not part of the
TASK-031 request contract.

Frozen TASK-021 acceptance requires all of:

```text
task021_layout is a complete TubeLayout
task021_layout.schema_version == "task021.tube-layout.v1"
task021_layout.blockers == ()
task021_layout.layout_hash replay == supplied layout_hash
task021_layout.layout_id replay == supplied layout_id
all required TASK020 ancestry replay succeeds
all required TASK021 canonical invariants succeed
```

Minimum replay fields include:

- `schema_version` exact `task021.tube-layout.v1`
- `layout_id`, `layout_hash`
- `request_hash`
- `task020_configuration_id`, `task020_configuration_hash`
- `task022_geometry_id`, `task022_geometry_hash`
- `layout_rule_authority.pattern_family`
- `layout_rule_authority.pitch_m`
- `tube_geometry.outer_diameter_m`
- `blockers` exactly `[]` (empty list in serialized public shape)

TASK-031 must not fabricate a `status` property on `TubeLayout`. TASK-031 must
not require the caller to supply both `TubeLayout` and `TubeLayoutValidationResult`.

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

```text
F001_CORRECTION_APPLIED=true
```

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

### 7.1 Applicability enforcement table

Each predicate below binds to an exact production field path, exact accepted
value or domain, exact blocker code, and stage rank. `SSHG_FORMULA_DOMAIN_VIOLATION`
may cover only residual formula-domain violations not already assigned a more
specific blocker.

| Field | Production binding | Accepted value / domain | Blocker code | Stage rank |
|---|---|---|---|---|
| `construction_family` | `task024_result.geometry.construction_family` | `FIXED_TUBESHEET` | `SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED` | 6 |
| `shell_pass_count` | `task024_result.geometry.shell_pass_count` | `1` | `SSHG_SHELL_PASS_COUNT_UNSUPPORTED` | 6 |
| `baffle_type` | `task024_result.geometry.design_authority.baffle_type` | `SINGLE_SEGMENTAL` | `SSHG_BAFFLE_TYPE_UNSUPPORTED` | 6 |
| `baffle_count` | `task024_result.geometry.design_authority.baffle_count` | `>= 2` | `SSHG_BAFFLE_COUNT_INSUFFICIENT` | 6 |
| `pattern_family` | `task021_layout.layout_rule_authority.pattern_family` | `SQUARE` or `TRIANGULAR` | `SSHG_PATTERN_FAMILY_UNSUPPORTED` | 6 |
| central spacing uniformity | `task024_result.geometry.design_authority.spacing_sequence_m[S[1:N]]` | all members exactly equal | `SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM` | 6 |
| `tube_outer_diameter_m` | `task024_result.geometry.tube_outer_diameter_m` | finite `> 0` | `SSHG_TUBE_OD_INVALID` | 8 |
| `pitch_m` | `task021_layout.layout_rule_authority.pitch_m` | finite `> 0` | `SSHG_PITCH_INVALID` | 8 |
| pitch vs tube OD | cross-bind TASK-021/TASK-024 | `pitch_m > tube_outside_diameter_m` | `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD` | 8 |
| `shell_inside_diameter_m` | `task024_result.geometry.shell_inside_diameter_m` | finite `> 0` | `SSHG_SHELL_INSIDE_DIAMETER_INVALID` | 8 |
| `central_inter_baffle_spacing_m` | extracted from `S[1:N]` | finite `> 0` | `SSHG_CENTRAL_INTER_BAFFLE_SPACING_INVALID` | 8 |
| spacing sequence shape | `spacing_sequence_m`, `baffle_count` | `len(S) == N + 1`, `len(S[1:N]) >= 1` | `SSHG_SPACING_SEQUENCE_INVALID` | 6 |
| central spacing presence | `S[1:N]` | at least one member | `SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT` | 6 |
| flow region identity | frozen profile | `CENTRAL_CROSSFLOW_SCREENING` | `SSHG_FORMULA_DOMAIN_VIOLATION` | 6 |

Do not double-report the same predicate through both a specific blocker and
`SSHG_FORMULA_DOMAIN_VIOLATION` unless exact aggregation semantics explicitly
require it.

```text
F008_CORRECTION_APPLIED=true
APPLICABILITY_ENFORCEMENT_EXACT=true
```

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

```text
DECIMAL_STRING_CONSTRUCTION_IS_EXACT=true
CONSTANTS_ROUNDED_ON_LOAD=false
```

`PI_REPRESENTATION` must be created only as:

```python
PI = Decimal("3.141592653589793238462643383279502884197169399375105820974944592307816406286208628620898062808825348")
```

`SQRT3_REPRESENTATION` must be created only as:

```python
SQRT3 = Decimal("1.7320508075688772935274463415058723669428052538103806280558069794519330169088000370811461867572485756")
```

Constants are constructed from strings as immutable exact `Decimal` values
outside the narrowed calculation context. They may contain more than 50 digits.
Every engineering calculation then runs inside an explicit `localcontext` with
`prec=50` and `rounding=ROUND_HALF_EVEN`.

Forbidden:

- `math.pi`, `math.sqrt`, `cmath.sqrt`
- `float(...)`, `Decimal(float)`, `Decimal.sqrt()`

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

### 11.5.1 Exact public output quantization algorithm

```text
AREA_OUTPUT_QUANTUM=Decimal("0.000000000000000000000001")
DIAMETER_OUTPUT_QUANTUM=Decimal("0.000000000001")
TRAILING_ZERO_POLICY=PRESERVE_QUANTUM_SCALE
```

Required semantics:

1. Formula predicates operate on unquantized `Decimal` values.
2. Formula result must be finite and `> 0` before quantization.
3. Quantize only at the public-output boundary.
4. Quantize with `ROUND_HALF_EVEN`.
5. If `raw_value > 0` and public quantized value `== 0`: BLOCK.
6. Normalize any signed zero to positive zero before formatting.
7. Emit canonical fixed-point decimal strings.
8. Preserve quantum scale in output strings.

Exact algorithm:

```python
public_q = raw_value.quantize(output_quantum, rounding=ROUND_HALF_EVEN)
if raw_value > 0 and public_q.is_zero():
    emit SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION or SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION
if public_q.is_zero():
    public_q = public_q.copy_abs()
canonical_string = format(public_q, "f")
```

Half-quantum tie behavior follows `ROUND_HALF_EVEN` exactly. `InvalidOperation`,
overflow, and non-finite values fail closed with `SSHG_FORMULA_CALCULATION_FAILED`
or the applicable quantization blocker.

```text
F005_CORRECTION_APPLIED=true
QUANTIZATION_ALGORITHM_EXACT=true
```

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


### 11.8 Singular formula evaluation sequences

Formula A has exactly one runtime operation sequence:

```python
Ct = Pt - do
ratio = Ds / Pt
As_step = ratio * B
As_raw = As_step * Ct
```

Formula B SQUARE has exactly one runtime operation sequence:

```python
do2 = do * do
pt2 = Pt * Pt
tube_term = PI * do2 / Decimal("4")
free_area = pt2 - tube_term
numerator = Decimal("4") * free_area
denominator = PI * do
De_square_raw = numerator / denominator
```

Formula B TRIANGULAR has exactly one runtime operation sequence:

```python
do2 = do * do
pt2 = Pt * Pt
cell_term = SQRT3 * pt2 / Decimal("4")
tube_term = PI * do2 / Decimal("8")
free_area = cell_term - tube_term
numerator = Decimal("4") * free_area
denominator = PI * do / Decimal("2")
De_triangular_raw = numerator / denominator
```

The algebraic identity `(2*sqrt(3)*Pt^2 - pi*do^2)/(pi*do)` may remain as a
source note only. It must not become a second runtime evaluation path.

```text
F006_CORRECTION_APPLIED=true
PI_SQRT3_LOADING_EXACT=true
FORMULA_EVALUATION_ORDER_EXACT=true
```

### 11.9 Determinism closure (D32–D33)

Given the same normalized request and the same frozen engineering authority,
TASK-031 must produce byte-identical outputs on Python 3.11 and 3.12 for:

- `request_hash`
- `engineering_authority_hash`
- raw formula branch selection
- unquantized engineering values
- public quantized engineering strings
- ordered warnings
- ordered blockers
- provenance pre-hash and final provenance
- `geometry_hash` / `geometry_id`
- `blocked_result_hash`

Determinism is testable only through the frozen contracts in §11.3–§11.8,
§16–§17, §19, and §20: Decimal constants, operation sequence, quantization,
message ordering, canonical projections, and UUID/hash rules.

```text
PY311_PY312_BYTE_IDENTITY_CONTRACT=true
```

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

```text
REQUEST_SCHEMA_VERSION=task031.shell-side-hydraulic-geometry-request.v1
ALTERNATIVE_REQUEST_SHAPES=false
REQUEST_SCHEMA_SINGULAR=true
```

The top-level raw request is an exact built-in `dict` with string keys. No
arbitrary `Mapping`, aliases, coercion, or `float` is permitted.

### 13.1 Top-level field table

| Field | Required | Raw type | Normalized type | Parser / validator | Canonical representation |
|---|---|---|---|---|---|
| `schema_version` | yes | `str` | `str` | exact token match | exact string |
| `tube_layout` | yes | `dict` | `TubeLayout` | TASK-021 layout decoder | upstream `layout_hash_payload` projection |
| `baffle_geometry_result` | yes | `dict` | `BaffleGeometryValidationResult` | TASK-024 result decoder | upstream geometry hash projection |
| `engineering_authority` | yes | `dict` | authority request binding | §9.4 validator | §20.1.2 engineering authority request binding projection |
| `evidence_refs` | yes | `list` | `tuple[str, ...]` | non-empty, sorted unique | sorted unique string tuple |

### 13.2 Nested `tube_layout` serialized public shape

`tube_layout` is an exact built-in `dict` with the closed TASK-021 `TubeLayout`
field set. Unknown nested fields block at Stage 2.

| Field | Raw type | Encoding rule |
|---|---|---|
| `schema_version` | `str` | exact `task021.tube-layout.v1` |
| `layout_id` | `str` | URN string |
| `layout_hash` | `str` | lowercase hex SHA-256 |
| `request_hash` | `str` | lowercase hex SHA-256 |
| `task020_configuration_id` | `str` | URN string |
| `task020_configuration_hash` | `str` | lowercase hex SHA-256 |
| `case_authority` | `dict` | closed TASK-020 case authority public shape |
| `construction_family` | `str` | exact enum token |
| `equipment_orientation` | `str` | exact enum token |
| `shell_pass_count` | `int` | exact `int`, not `bool` |
| `tube_pass_count` | `int` | exact `int`, not `bool` |
| `tube_geometry` | `dict` | approved tube geometry snapshot; `outer_diameter_m` as canonical decimal string |
| `layout_rule_authority` | `dict` | `pattern_family` as string token; `pitch_m` as canonical decimal string |
| `placement_envelope` | `dict` | closed TASK-021 envelope shape |
| `origin_mode` | `str` | exact enum token |
| `axis_orientation` | `str` | exact enum token |
| `exclusion_zones` | `list` | JSON array of closed zone dicts |
| `positions` | `list` | JSON array of closed position dicts |
| `tube_hole_count` | `int` | exact `int` |
| `physical_tube_count` | `int` | exact `int` |
| `boundary_rejection_count` | `int` | exact `int` |
| `exclusion_rejection_count` | `int` | exact `int` |
| `exclusion_audit` | `list` | JSON array of closed audit dicts |
| `warnings` | `list` | JSON array of `MessageEntry` dicts per §16.1 |
| `blockers` | `list` | JSON array of `MessageEntry` dicts; must be `[]` on acceptance |
| `deferred_capabilities` | `list` | JSON array of exact capability tokens |
| `provenance` | `dict` | closed TASK-021 provenance public shape |

Reconstruction helper: `hexagent.exchangers.shell_tube.tube_layout.schema` and
`tube_layout.canonical` replay contracts. TASK-031 maps serialized dict fields
to immutable upstream dataclass fields without duplicating upstream engineering
semantics.

### 13.3 Nested `baffle_geometry_result` serialized public shape

`baffle_geometry_result` is an exact built-in `dict` with the closed TASK-024
`BaffleGeometryValidationResult` field set.

| Field | Raw type | Encoding rule |
|---|---|---|
| `status` | `str` | exact `VALID` or `BLOCKED` |
| `geometry` | `dict` or `null` | complete `BaffleGeometry` dict when `VALID`; `null` when absent |
| `warnings` | `list` | JSON array of `MessageEntry` dicts per §16.1 |
| `blockers` | `list` | JSON array of `MessageEntry` dicts; must be `[]` on acceptance |
| `deferred_capabilities` | `list` | JSON array of exact capability tokens |
| `blocked_result_hash` | `str` or `null` | lowercase hex SHA-256 or `null` on accepted valid result |

When `geometry` is present, it is an exact built-in `dict` with the closed
`BaffleGeometry` field set. TASK-031-consumed geometry fields include at minimum:

| Field | Encoding rule |
|---|---|
| `schema_version` | exact `task024.baffle-geometry.v1` |
| `geometry_id` | URN string |
| `geometry_hash` | lowercase hex SHA-256 |
| `shell_inside_diameter_m` | canonical decimal string |
| `tube_outer_diameter_m` | canonical decimal string |
| `construction_family` | exact enum token |
| `shell_pass_count` | exact `int` |
| `design_authority.baffle_type` | exact enum token |
| `design_authority.baffle_count` | exact `int` |
| `design_authority.spacing_sequence_m` | JSON array of canonical decimal strings |

Reconstruction helper: `hexagent.exchangers.shell_tube.baffle_geometry.schema`
and `baffle_geometry.canonical` replay contracts.

### 13.4 Nested `engineering_authority` serialized public shape

| Field | Raw type | Encoding rule |
|---|---|---|
| `schema_version` | `str` | exact `task031.engineering-authority-request.v1` |
| `authority_profile_id` | `str` | exact aggregate profile ID |
| `authority_hash` | `str` | lowercase hex SHA-256 |
| `evidence_refs` | `list` | non-empty JSON array of strings, sorted unique |

### 13.5 Tuple and enum encoding rules

- production tuple-valued fields are encoded as JSON arrays in field order
- enum values are encoded as exact string tokens, never integers
- `Decimal` geometry values are encoded as canonical decimal strings
- `None` is encoded only where explicitly admitted (`geometry` on blocked results)
- unknown nested fields block with `SSHG_UNKNOWN_FIELD`

```text
F002_CORRECTION_APPLIED=true
```

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

## 16. Closed blocker taxonomy and message pipeline

`BLOCKER_CODE_COUNT=36`

### 16.1 Closed `MessageEntry` shape

```python
MessageEntry(
    code: str,
    field_path: str | None,
    message_key: str,
    evidence_refs: tuple[str, ...],
    details: tuple[tuple[str, str], ...],
)
```

Field order is frozen as above. `details` is not an unconstrained generic
object. Serialized public shape:

```json
{
  "code": "...",
  "field_path": "...",
  "message_key": "...",
  "evidence_refs": ["..."],
  "details": [["key", "value"]]
}
```

```text
MESSAGE_ENTRY_SCHEMA_CLOSED=true
```

### 16.2 Global blocker sort key

```python
(
    stage_rank,
    code,
    field_path_or_empty_string,
    message_key,
    sha256(canonical_details),
    sha256(canonical_evidence_refs),
)
```

No set iteration ordering. No implementation-dependent order.

### 16.3 Complete blocker enumeration

| Code | validation_stage | stage_rank | field_path | meaning | aggregation |
|---|---|---:|---|---|---|
| `SSHG_SCHEMA_VERSION_UNSUPPORTED` | raw top-level/schema | 1 | `schema_version` | unsupported request schema token | accumulate all Stage 1 blockers |
| `SSHG_RAW_TYPE_INVALID` | raw top-level/schema | 1 | top-level or nested | raw value is not exact built-in dict/list/str/int | accumulate all Stage 1 blockers |
| `SSHG_UNKNOWN_FIELD` | raw top-level/schema | 1 | offending path | unknown field in closed schema | accumulate all Stage 1 blockers |
| `SSHG_DECIMAL_LEXICAL_INVALID` | nested public-shape decoding | 2 | decimal field path | decimal lexical domain violation | accumulate all Stage 2 blockers |
| `SSHG_EVIDENCE_REFS_INVALID` | raw top-level/schema | 1 | `evidence_refs` | evidence refs empty or not sorted unique | accumulate all Stage 1 blockers |
| `SSHG_TASK021_LAYOUT_MISSING` | nested public-shape decoding | 2 | `tube_layout` | required layout absent | accumulate all Stage 2 blockers |
| `SSHG_TASK021_LAYOUT_INVALID` | nested public-shape decoding | 2 | `tube_layout` | layout fails TASK-021 shape decode | accumulate all Stage 2 blockers |
| `SSHG_TASK021_LAYOUT_HAS_BLOCKERS` | TASK-021 validation/replay | 3 | `tube_layout.blockers` | layout carries upstream blockers | accumulate all Stage 3 blockers |
| `SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH` | TASK-021 validation/replay | 3 | `tube_layout` | layout hash/id replay failure | accumulate all Stage 3 blockers |
| `SSHG_TASK024_RESULT_MISSING` | nested public-shape decoding | 2 | `baffle_geometry_result` | required result absent | accumulate all Stage 2 blockers |
| `SSHG_TASK024_RESULT_INVALID` | nested public-shape decoding | 2 | `baffle_geometry_result` | result fails TASK-024 shape decode | accumulate all Stage 2 blockers |
| `SSHG_TASK024_RESULT_HAS_BLOCKERS` | TASK-024 validation/replay | 4 | `baffle_geometry_result.blockers` | wrapper carries upstream blockers | accumulate all Stage 4 blockers |
| `SSHG_TASK024_GEOMETRY_MISSING` | TASK-024 validation/replay | 4 | `baffle_geometry_result.geometry` | `VALID` wrapper with `geometry=null` | accumulate all Stage 4 blockers |
| `SSHG_TASK024_IDENTITY_MISMATCH` | TASK-024 validation/replay | 4 | `baffle_geometry_result` | geometry hash/id replay failure | accumulate all Stage 4 blockers |
| `SSHG_TASK021_TASK024_TUBE_OD_MISMATCH` | TASK-021/TASK-024 cross-binding | 5 | `tube_layout` / `baffle_geometry_result` | tube OD cross-bind failure | accumulate all Stage 5 blockers |
| `SSHG_UPSTREAM_CONFIGURATION_BINDING_MISMATCH` | TASK-021/TASK-024 cross-binding | 5 | upstream ids | TASK-020 configuration binding mismatch | accumulate all Stage 5 blockers |
| `SSHG_UPSTREAM_LAYOUT_BINDING_MISMATCH` | TASK-021/TASK-024 cross-binding | 5 | upstream ids | TASK-021/TASK-024 layout binding mismatch | accumulate all Stage 5 blockers |
| `SSHG_CONSTRUCTION_FAMILY_UNSUPPORTED` | applicability / central spacing | 6 | `baffle_geometry_result.geometry.construction_family` | unsupported construction family | accumulate all Stage 6 blockers |
| `SSHG_SHELL_PASS_COUNT_UNSUPPORTED` | applicability / central spacing | 6 | `baffle_geometry_result.geometry.shell_pass_count` | unsupported shell pass count | accumulate all Stage 6 blockers |
| `SSHG_BAFFLE_TYPE_UNSUPPORTED` | applicability / central spacing | 6 | `...design_authority.baffle_type` | unsupported baffle type | accumulate all Stage 6 blockers |
| `SSHG_BAFFLE_COUNT_INSUFFICIENT` | applicability / central spacing | 6 | `...design_authority.baffle_count` | baffle count below minimum | accumulate all Stage 6 blockers |
| `SSHG_SPACING_SEQUENCE_INVALID` | applicability / central spacing | 6 | `...design_authority.spacing_sequence_m` | spacing sequence shape invalid | accumulate all Stage 6 blockers |
| `SSHG_CENTRAL_INTER_BAFFLE_SPACING_ABSENT` | applicability / central spacing | 6 | `...spacing_sequence_m` | no central inter-baffle member | accumulate all Stage 6 blockers |
| `SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM` | applicability / central spacing | 6 | `...spacing_sequence_m` | unequal central spacing members | accumulate all Stage 6 blockers |
| `SSHG_PATTERN_FAMILY_UNSUPPORTED` | applicability / central spacing | 6 | `tube_layout.layout_rule_authority.pattern_family` | unsupported pattern family | accumulate all Stage 6 blockers |
| `SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH` | engineering-authority identity | 7 | `engineering_authority` | authority hash/profile mismatch | accumulate all Stage 7 blockers |
| `SSHG_PITCH_INVALID` | numeric predicates / formula evaluation | 8 | `tube_layout.layout_rule_authority.pitch_m` | pitch not finite positive | accumulate all Stage 8 blockers |
| `SSHG_TUBE_OD_INVALID` | numeric predicates / formula evaluation | 8 | tube OD binding path | tube OD not finite positive | accumulate all Stage 8 blockers |
| `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD` | numeric predicates / formula evaluation | 8 | pitch / tube OD | pitch not strictly greater than tube OD | accumulate all Stage 8 blockers |
| `SSHG_SHELL_INSIDE_DIAMETER_INVALID` | numeric predicates / formula evaluation | 8 | `...shell_inside_diameter_m` | shell ID not finite positive | accumulate all Stage 8 blockers |
| `SSHG_CENTRAL_INTER_BAFFLE_SPACING_INVALID` | numeric predicates / formula evaluation | 8 | extracted central spacing | central spacing not finite positive | accumulate all Stage 8 blockers |
| `SSHG_FORMULA_DOMAIN_VIOLATION` | numeric predicates / formula evaluation | 8 | engineering inputs | residual formula-domain violation | accumulate all Stage 8 blockers |
| `SSHG_FORMULA_CALCULATION_FAILED` | numeric predicates / formula evaluation | 8 | engineering outputs | non-finite or non-positive raw result | accumulate all Stage 8 blockers |
| `SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION` | public quantization | 9 | `central_crossflow_flow_area_m2` | positive raw area quantizes to zero | accumulate all Stage 9 blockers |
| `SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION` | public quantization | 9 | `shell_side_equivalent_hydraulic_diameter_m` | positive raw diameter quantizes to zero | accumulate all Stage 9 blockers |
| `SSHG_CANONICALIZATION_FAILED` | canonical/hash/provenance/final assembly | 10 | result assembly | canonical projection failure | accumulate all Stage 10 blockers |

Codes are exact and cannot be aliased.

```text
F003_CORRECTION_APPLIED=true
BLOCKER_PRECEDENCE_EXACT=true
```

## 17. Closed warning taxonomy

`WARNING_CODE_COUNT=7`

All seven warnings are always emitted on every `VALID`
`CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1` result. None are conditional in v1.

| warning_code | field_path | message_key | eligibility_predicate | prerequisite_stage | valid_result_emission | blocked_result_emission | evidence_binding |
|---|---|---|---|---:|---|---|---|
| `SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY` | `null` | `central_crossflow_screening_geometry_only` | always eligible after Stage 6 completes | 6 | always emit all seven warnings on `VALID` | emit only if Stage 6 completed before failure | frozen profile §3 |
| `SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED` | `null` | `leakage_bypass_corrections_excluded` | always eligible after Stage 6 completes | 6 | always emit | emit only if Stage 6 completed before failure | §8 |
| `SSHG_MINIMUM_AREA_SELECTION_DEFERRED` | `null` | `minimum_area_selection_deferred` | always eligible after Stage 6 completes | 6 | always emit | emit only if Stage 6 completed before failure | §3.2 |
| `SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED` | `null` | `window_inlet_outlet_flow_areas_deferred` | always eligible after Stage 6 completes | 6 | always emit | emit only if Stage 6 completed before failure | §3.2 |
| `SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED` | `null` | `flow_state_thermal_pressure_drop_deferred` | always eligible after Stage 6 completes | 6 | always emit | emit only if Stage 6 completed before failure | §3.3 |
| `SSHG_NO_FULL_EXCHANGER_RATING_CLAIM` | `null` | `no_full_exchanger_rating_claim` | always eligible after Stage 6 completes | 6 | always emit | emit only if Stage 6 completed before failure | §2 |
| `SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY` | `null` | `formula_authority_screening_model_only` | always eligible after Stage 7 completes | 7 | always emit | emit only if Stage 7 completed before failure | §4, §9 |

```text
WARNING_MESSAGE_KEY_LITERAL_COUNT=7
WARNING_MESSAGE_KEY_PLACEHOLDER_COUNT=0
WARNING_MESSAGE_KEYS_UNIQUE=true
NF001_SECOND_CORRECTION_APPLIED=true
```

Warning sort key (deterministic):

```python
(
    code,
    field_path_or_empty_string,
    message_key,
    sha256(canonical_details),
    sha256(canonical_evidence_refs),
)
```

Frozen projection rule:

```text
provenance.warnings == public_result.warnings
```

by exact canonical message projection.

Warnings must not be used for conditions that should block.

```text
F004_CORRECTION_APPLIED=true
WARNING_ELIGIBILITY_EXACT=true
```

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

## 19. Validation stages and failure policy

| Stage rank | validation_stage | scope |
|---:|---|---|
| 1 | raw top-level/schema | top-level dict, `schema_version`, `evidence_refs`, closed field set |
| 2 | nested public-shape decoding | `tube_layout`, `baffle_geometry_result`, `engineering_authority` decode |
| 3 | TASK-021 validation/identity replay | `TubeLayout` acceptance without `status`; `blockers == ()`; hash/id replay |
| 4 | TASK-024 validation/identity replay | `status == VALID`, `geometry is not None`, `blockers == ()`; hash/id replay |
| 5 | TASK-021/TASK-024 cross-binding | TASK-020/TASK-021/TASK-022/TASK-024 transitive bindings and tube OD match |
| 6 | applicability and central-spacing | §7.1 enforcement table and §6 central spacing extraction |
| 7 | engineering-authority identity | frozen authority hash/profile replay |
| 8 | numeric predicates/formula evaluation | unquantized Decimal predicates and Formula A/B singular sequences |
| 9 | public quantization | §11.5.1 exact quantize algorithm |
| 10 | canonical/hash/provenance/final assembly | projections §20, provenance §22, result assembly |

Failure policy:

- evaluate stages strictly in ascending `stage_rank`
- within the first failing stage, accumulate **all** complete blockers from that stage
- do not execute later engineering stages after the first failing stage
- sort blockers deterministically using §16.2 global sort key

Any stage failure blocks. No partial geometry.

## 20. Canonical projections and hashes

TASK-031 uses repository `sha256_hex` / `canonical_json_bytes` conventions. It
does not create a competing generic canonical framework. Each projection below
is an ordered field tuple. Nested upstream values delegate to verified upstream
canonical/public projections.

```text
F007_CORRECTION_APPLIED=true
CANONICAL_PROJECTIONS_EXACT=true
REQUEST_HASH_PROJECTION_EXACT=true
```

### 20.1 `REQUEST_CANONICAL_PROJECTION`

```text
REQUEST_CANONICAL_PROJECTION_FIELD_COUNT=5
REQUEST_CANONICAL_PROJECTION_PROSE_SLOT_COUNT=0
NF002_SECOND_CORRECTION_APPLIED=true
```

Ordered top-level tuple:

1. `schema_version` — exact string `task031.shell-side-hydraulic-geometry-request.v1`
2. `tube_layout` — TASK-021 `layout_hash_payload` upstream projection (delegate to `tube_layout.canonical`; no TASK-031 redefinition)
3. `task024_result_binding` — exact `TASK024_RESULT_BINDING_PROJECTION` per §20.1.1
4. `engineering_authority_request` — ordered tuple per §20.1.2
5. `evidence_refs` — sorted unique string tuple

Exclusions: no TASK-031 engineering output values, no `geometry_hash`, no
`geometry_id`, no runtime timestamp, no ambient git state.

```text
request_hash = sha256_hex(canonical_json_bytes(request_canonical_projection))
```

#### 20.1.1 `TASK024_RESULT_BINDING_PROJECTION`

```text
TASK024_RESULT_BINDING_PROJECTION_FIELD_COUNT=20
```

TASK-031 normalized binding projection only. TASK-031 must not reimplement TASK-024
geometry engineering semantics. Encoding: status and enum fields as exact string
tokens; decimal fields as canonical decimal strings; `spacing_sequence_m` as ordered
JSON array of canonical decimal strings; null forbidden for accepted geometry.

| Order | Field path | Encoding |
|---:|---|---|
| 1 | `status` | exact `VALID` or `BLOCKED` string token |
| 2 | `geometry.schema_version` | exact `task024.baffle-geometry.v1` |
| 3 | `geometry.geometry_id` | exact URN string |
| 4 | `geometry.geometry_hash` | lowercase hex SHA-256 |
| 5 | `geometry.request_hash` | lowercase hex SHA-256 |
| 6 | `geometry.task020_configuration_id` | exact URN string |
| 7 | `geometry.task020_configuration_hash` | lowercase hex SHA-256 |
| 8 | `geometry.task021_layout_id` | exact URN string |
| 9 | `geometry.task021_layout_hash` | lowercase hex SHA-256 |
| 10 | `geometry.task022_geometry_id` | exact URN string |
| 11 | `geometry.task022_geometry_hash` | lowercase hex SHA-256 |
| 12 | `geometry.construction_family` | exact enum string token |
| 13 | `geometry.shell_pass_count` | exact integer |
| 14 | `geometry.shell_inside_diameter_m` | canonical decimal string |
| 15 | `geometry.tube_outer_diameter_m` | canonical decimal string |
| 16 | `geometry.design_authority.schema_version` | exact `task024.caller-baffle-design-authority.v1` |
| 17 | `geometry.design_authority.baffle_type` | exact enum string token |
| 18 | `geometry.design_authority.baffle_count` | exact integer |
| 19 | `geometry.design_authority.spacing_sequence_m` | ordered JSON array of canonical decimal strings |
| 20 | `geometry.design_authority.authority_hash` | lowercase hex SHA-256 |

When `status=BLOCKED` and `geometry=null`, slot 3 is encoded as JSON `null` and
fields 2 and 4–20 are omitted from the binding projection.

#### 20.1.2 `ENGINEERING_AUTHORITY_REQUEST_BINDING_PROJECTION`

Ordered tuple:

1. `schema_version` — exact `task031.engineering-authority-request.v1`
2. `authority_profile_id` — exact aggregate profile ID
3. `authority_hash` — lowercase hex SHA-256
4. `evidence_refs` — sorted unique string tuple

### 20.2 `ENGINEERING_AUTHORITY_CANONICAL_PROJECTION`

Ordered tuple independent from request data:

1. `schema_version` — `task031.engineering-authority.v1`
2. `aggregate_profile_id` — `TASK031_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1_FORMULA_AUTHORITY`
3. `formula_a_id` — `TASK031_CF_AREA_KERN_SCREENING_INTCHOPN_EQ55_56_V1`
4. `formula_b_id` — `TASK031_DE_KERN_SCREENING_INTCHOPN_EQ51_BRANCH_V1`
5. `primary_source_id` — `SRC-INTECHOPEN-100450-KHARAJI-2021`
6. `exact_source_locations` — frozen tuple of §4 locations
7. `corroborating_source_ids` — frozen corroboration tuple
8. `supported_pattern_families` — `("SQUARE", "TRIANGULAR")`
9. `applicability_envelope` — frozen §7 envelope object
10. `permission_state` — `LAWFUL_PUBLIC_ACCESS_REUSE_WITH_ATTRIBUTION`
11. `issue_number` — `181`
12. `freeze_comment_id` — `5311936966`
13. `source_ledger_version` — frozen ledger version token
14. `source_ledger_count` — exact count `4`
15. `formula_authority_record_model` — `PER_FORMULA_PLUS_AGGREGATE`

Exclusions: `authority_hash` and `authority_id` must not self-contain in the
hash input.

```text
engineering_authority_hash =
  sha256_hex(canonical_json_bytes(authority_canonical_projection))
engineering_authority_id =
  urn:hxforge:task031:engineering-authority:v1:{engineering_authority_hash}
```

### 20.3 `SUCCESS_GEOMETRY_CANONICAL_PROJECTION`

Ordered tuple with explicit sections:

**INPUT BINDINGS**

1. `schema_version`
2. `request_hash`
3. `task020_configuration_id`
4. `task020_configuration_hash`
5. `task021_layout_id`
6. `task021_layout_hash`
7. `task022_geometry_id`
8. `task022_geometry_hash`
9. `task024_geometry_id`
10. `task024_geometry_hash`
11. `pattern_family`

**ENGINEERING OUTPUTS**

12. `central_inter_baffle_spacing_m` — canonical decimal string (public evidence field)
13. `central_crossflow_flow_area_m2` — canonical decimal string
14. `shell_side_equivalent_hydraulic_diameter_m` — canonical decimal string
15. `flow_region_identity` — `CENTRAL_CROSSFLOW_SCREENING`

**AUTHORITY IDENTITY**

16. `engineering_authority_id`
17. `engineering_authority_hash`
18. `formula_a_id`
19. `formula_b_id`

**WARNINGS**

20. `warnings` — ordered `MessageEntry` projection tuple

**DEFERRED CAPABILITIES**

21. `deferred_capabilities` — ordered exact token tuple

**PROVENANCE PREHASH IDENTITY**

22. `provenance_prehash` — `PROVENANCE_PREHASH_PROJECTION` per §22.1

Exclusions: `geometry_hash` and `geometry_id` must not appear in the hash input.

```text
geometry_hash = sha256_hex(canonical_json_bytes(geometry_canonical_projection))
geometry_id = uuid5_from_hash(
  namespace=URN_NAMESPACE_HXFORGE_TASK031_SHELL_SIDE_HYDRAULIC_GEOMETRY_V1,
  name=geometry_hash,
)
```

`geometry_id` consumes the previously completed stable `geometry_hash`. No
alternate UUID construction is permitted.

### 20.4 `BLOCKED_RESULT_CANONICAL_PROJECTION`

Ordered tuple:

1. `schema_version` — `task031.shell-side-hydraulic-geometry.v1`
2. `failure_stage` — integer stage rank of first failing stage
3. `normalized_context` — normalized request context available up to failure stage
4. `raw_failing_field` — canonical snapshot of first failing raw field or `null`
5. `eligible_warnings` — warnings whose prerequisite stage completed
6. `blockers` — ordered blocker `MessageEntry` tuple
7. `deferred_capabilities` — closed deferred capability tuple

`geometry` is absent/`null` by exact schema rule. No partial
`central_crossflow_flow_area_m2` or `shell_side_equivalent_hydraulic_diameter_m`
fields may appear.

```text
blocked_result_hash = sha256_hex(canonical_json_bytes(blocked_canonical_projection))
```

`blocked_result_hash` must be stable for identical blocked input and must be
computable when `geometry=None` without self-reference.

#### 20.4.1 `BLOCKED_NORMALIZED_CONTEXT_BY_FAILURE_STAGE`

```text
BLOCKED_CONTEXT_STAGE_COUNT=10
BLOCKED_CONTEXT_ALL_STAGE_FIELD_ORDERS_EXACT=true
BLOCKED_CONTEXT_PLACEHOLDER_COUNT=0
BLOCKED_RESULT_CANONICAL_PROJECTION_EXACT=true
NF004_SECOND_CORRECTION_APPLIED=true
```

`normalized_context` is an ordered tuple of named context slices. Each slice uses
canonical encoding frozen elsewhere. Malformed raw values belong only in
`raw_failing_field`, never silently inside `normalized_context`.

| failure_stage | stage_rank | verified_context_fields_in_exact_order | raw_failing_field_semantics | eligible_warning_boundary |
|---|---:|---|---|---|
| raw top-level/schema | 1 | `()` | canonical snapshot of first failing top-level raw field, or `null` if type failure | no warnings |
| nested public-shape decoding | 2 | `(request_schema_version, evidence_refs)` | canonical snapshot of first failing nested decode field path | no warnings |
| TASK-021 validation/identity replay | 3 | `(request_schema_version, evidence_refs, engineering_authority_request_binding, tube_layout_public_projection)` | canonical snapshot of first failing TASK-021 field, or `null` | no warnings |
| TASK-024 validation/identity replay | 4 | Stage-3 tuple plus `(task024_result_binding)` per §20.1.1 | canonical snapshot of first failing TASK-024 wrapper/geometry field | no warnings |
| TASK-021/TASK-024 cross-binding | 5 | Stage-4 tuple plus `(cross_binding_projection)` where `cross_binding_projection` ordered fields are: `task020_configuration_id`, `task020_configuration_hash`, `task021_layout_id`, `task021_layout_hash`, `task022_geometry_id`, `task022_geometry_hash`, `task024_geometry_id`, `task024_geometry_hash`, `task021_tube_outer_diameter_m`, `task024_tube_outer_diameter_m` | canonical snapshot of first failing cross-bind field | no warnings |
| applicability and central-spacing | 6 | Stage-5 tuple plus `(applicability_context_projection)` ordered: `construction_family`, `shell_pass_count`, `baffle_type`, `baffle_count`, `pattern_family`, `spacing_sequence_m`, `central_inter_baffle_spacing_m` | canonical snapshot of first failing applicability field | warnings with prerequisite_stage `<= 6` eligible |
| engineering-authority identity | 7 | Stage-6 tuple plus `(engineering_authority_verified_projection)` ordered: `engineering_authority_profile_id`, `engineering_authority_hash` | canonical snapshot of first failing authority field | warnings with prerequisite_stage `<= 7` eligible |
| numeric predicates/formula evaluation | 8 | Stage-7 tuple plus `(numeric_context_projection)` ordered: `shell_inside_diameter_m`, `tube_outside_diameter_m`, `pitch_m`, `pattern_family`, `central_inter_baffle_spacing_m`, `formula_a_id`, `formula_b_id` | canonical snapshot of first failing numeric predicate field | warnings with prerequisite_stage `<= 7` eligible |
| public quantization | 9 | Stage-8 tuple plus `(engineering_raw_projection)` ordered: `central_crossflow_flow_area_raw`, `shell_side_equivalent_hydraulic_diameter_raw`, `selected_formula_b_branch` | canonical snapshot of first failing quantization input | warnings with prerequisite_stage `<= 7` eligible |
| canonical/hash/provenance/final assembly | 10 | Stage-9 tuple plus `(pre_final_assembly_projection)` ordered: `request_hash`, `engineering_authority_id`, `eligible_warnings`, `blockers` | canonical snapshot of first failing assembly field | warnings with prerequisite_stage `<= 7` eligible |

Same `failure_stage`, same verified slices, same `raw_failing_field`, same
eligible warnings, and same blockers must yield identical `blocked_result_hash`.

### 20.5 `PROVENANCE_PREHASH_PROJECTION`

Ordered tuple binding upstream and authority identity before final provenance
hash:

1. `task_id`
2. `design_contract_path`
3. `task020_configuration_id`
4. `task020_configuration_hash`
5. `task021_layout_id`
6. `task021_layout_hash`
7. `task022_geometry_id`
8. `task022_geometry_hash`
9. `task024_geometry_id`
10. `task024_geometry_hash`
11. `engineering_authority_profile_id`
12. `engineering_authority_hash`
13. `formula_a_id`
14. `formula_b_id`
15. `freeze_comment_id`
16. `source_ids`
17. `pattern_family`
18. `flow_region_identity`
19. `software_version`
20. `git_commit`
21. `request_hash`
22. `warnings`
23. `deferred_capabilities`

No `datetime.now`, no current timezone, no runtime `git rev-parse`, no
filesystem-dependent build identity.

### 20.6 `FINAL_PROVENANCE_PROJECTION`

`PROVENANCE_PREHASH_PROJECTION` plus:

24. `provenance_hash` — `sha256_hex(canonical_json_bytes(PROVENANCE_PREHASH_PROJECTION))`

Provenance hash construction must not create
`request_hash -> provenance_hash -> request_hash` cycles.

Encoding rules for all projections:

- enum tokens as exact strings
- decimals as canonical decimal strings
- messages as ordered `MessageEntry` projections
- `None` only where explicitly admitted
- sequence ordering preserved in JSON arrays

### 20.7 Software / build identity

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

Provenance is an ordered immutable schema, not an unordered generic mapping.

### 22.1 Ordered provenance fields

Final public provenance tuple order:

1. `task_id` — `TASK031`
2. `design_contract_path` — `docs/tasks/TASK-031-shell-and-tube-shell-side-flow-path-hydraulic-geometry.md`
3. `task020_configuration_id`
4. `task020_configuration_hash`
5. `task021_layout_id`
6. `task021_layout_hash`
7. `task022_geometry_id`
8. `task022_geometry_hash`
9. `task024_geometry_id`
10. `task024_geometry_hash`
11. `engineering_authority_profile_id`
12. `engineering_authority_hash`
13. `formula_a_id`
14. `formula_b_id`
15. `source_authority_freeze_issue` — `181`
16. `source_authority_freeze_comment_id` — `5311936966`
17. `source_ids` — four frozen source IDs in sorted order
18. `pattern_family`
19. `flow_region_identity` — `CENTRAL_CROSSFLOW_SCREENING`
20. `software_version`
21. `git_commit`
22. `request_hash`
23. `warnings`
24. `deferred_capabilities`
25. `provenance_hash`

Pre-hash projection is §20.5. Final projection is §20.6.

Frozen rule:

```text
provenance.warnings == public_result.warnings
```

No provenance field may claim a standard, formula, or correction model not
actually frozen.

## 23. Engineering verification vectors

```text
VECTOR_COUNT=14
ENGINEERING_VECTOR_COUNT=14
VECTOR_RECORD_FIELD_COUNT=16
VECTOR_FULL_RECORD_COUNT=14
VECTOR_INCOMPLETE_RECORD_COUNT=0
BLOCKED_VECTOR_NOT_REACHED_OMISSION_COUNT=0
VECTOR_PLACEHOLDER_COUNT=0
NF003_THIRD_CORRECTION_APPLIED=true
NF003_001_CORRECTION_APPLIED=true
NF003_002_CORRECTION_APPLIED=true
NF003_003_CORRECTION_APPLIED=true
PRIOR_VECTOR_REPLAY_COUNT_INCONSISTENCY_NOTED=true
NEXT_REREVIEW_RECOUNTS_VECTOR_IDENTITY_REPLAY_FROM_SCRATCH=true
UNSUPPORTED_PATTERN_RAW_TOKEN_REACHES_TASK031_STAGE6=false
REASON=TASK021_CLOSED_PATTERN_ENUM_BLOCKS_EARLIER
V8_SYNTHETIC_ACCEPTED_PATTERN_OBJECT_PRESENT=false
TASK024_VECTOR_FIXTURE_PUBLIC_ENTRY=hexagent.exchangers.shell_tube.baffle_geometry.geometry::compute_geometry_foundation
TASK024_VECTOR_FIXTURE_AUTHORITY_ENTRY=hexagent.exchangers.shell_tube.baffle_geometry.authority::validate_authority_foundation
TASK024_EXPORTED_VALIDATE_REQUEST_PRESENT_AT_BASELINE=false
VECTOR_REPLAY_VERIFIED_COUNT=14/14
V11_TASK024_BLOCKED_RESULT_REPLAY=PASS
V11_PINNED_BLOCKER_COUNT=1
V11_BLOCKED_RESULT_HASH_LITERAL_PRESENT=true
ENGINEERING_VECTORS_COMPLETE=true
F009_CORRECTION_APPLIED=true
```

Design-time vectors only. Expected implementation output must never be used as
formula authority. V1 and V2 use independent arithmetic from the frozen π / √3
Decimal constants and §11.8 singular runtime sequences.

At authoring baseline `main@4add89515e1efa17e8af71f670d30a8df7fc85fb`, TASK-024
exported `validate_request` is design-contract frozen but not yet present in
production. Design-time vector construction composes
`validate_authority_foundation` (Stages 2–8) and `compute_geometry_foundation`
(Stages 9–18), then serializes to the frozen `BaffleGeometryValidationResult`
public dict shape. This is consistent with TASK-024 design §6.3 composition and
does not substitute engineering authority.

Frozen engineering authority hash for all vectors unless explicitly mutated:

```text
engineering_authority_hash=1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989
authority_profile_id=TASK031_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1_FORMULA_AUTHORITY
```

Design-time helper module for base fixture generation:

```text
helper_module=tests.exchangers.shell_tube.baffle_geometry._builders
helper_functions=make_shell_and_tube_configuration, make_tube_layout, make_shell_bundle_geometry, make_axial_span, make_design_authority, make_geometry_request
canonical_helpers=hexagent.exchangers.shell_tube.tube_layout.canonical,
  hexagent.exchangers.shell_tube.baffle_geometry.authority,
  hexagent.exchangers.shell_tube.baffle_geometry.geometry
FIXTURE_USED_AS_ENGINEERING_AUTHORITY=false
EXPECTED_REPOSITORY_OUTPUT_USED_AS_ENGINEERING_AUTHORITY=false
ENGINEERING_FORMULA_AUTHORITY_FROM_FIXTURE=false
```

### 23.1 Reference scalar oracle (independent SI)

```text
Ds=0.25 m
B=0.125 m
Pt=0.025 m
do=0.019 m
Ct=0.006 m

As_raw=0.00750 m^2
As_public=0.007500000000000000000000 m^2

De_square_raw≈0.022882879761025088360232569308556411061699906773805 m
De_square_public=0.022882879761 m

De_triangular_raw≈0.017271637856696845362587269625853252723512268445175 m
De_triangular_public=0.017271637857 m
```

Historical non-authoritative typo (do not use as oracle):
`0.017271637856696855`

### 23.2 `TASK031_VECTOR_BASE_FIXTURE_V1`

Complete exact serializable raw request. Pinned upstream identity literals:

```text
BASE_FIXTURE_ID=TASK031_VECTOR_BASE_FIXTURE_V1
task021_layout_id=c79cb4d3-824b-52c0-a7b2-81e926fb3849
task021_layout_hash=97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f
task024_geometry_id=f701890c-8848-517b-ab72-48f8f78c4b0a
task024_geometry_hash=8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f
pattern_family=SQUARE
baffle_count=2
spacing_sequence_m=["0.125000000000","0.125000000000","0.125000000000"]
shell_inside_diameter_m=0.250000000000
tube_outer_diameter_m=0.019000000000
pitch_m=0.025000000000
```

```json
{
  "schema_version": "task031.shell-side-hydraulic-geometry-request.v1",
  "tube_layout": {
    "schema_version": "task021.tube-layout.v1",
    "layout_id": "c79cb4d3-824b-52c0-a7b2-81e926fb3849",
    "layout_hash": "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f",
    "request_hash": "93f3ea2badfa489da56dadadcb13f296b85f4b2efd7dc82311827acf707dd0ce",
    "task020_configuration_id": "050a7064-af75-5990-82a1-51f0eb0a3a6b",
    "task020_configuration_hash": "b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9",
    "case_authority": {
      "domain_snapshot_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
      "payload_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "revision_id": "rev-task024-001",
      "revision_status": "committed"
    },
    "construction_family": "FIXED_TUBESHEET",
    "equipment_orientation": "HORIZONTAL",
    "shell_pass_count": 1,
    "tube_pass_count": 2,
    "tube_geometry": {
      "geometry_id": "task031-vector-tube-od-19mm",
      "geometry_type": "tube",
      "revision": "1",
      "approval_state": "approved",
      "outer_diameter_m": "0.019000000000",
      "inner_diameter_m": "0.016000000000",
      "wall_thickness_m": "0.001500000000",
      "record_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "snapshot_hash": "5e684672eb15a7173e0154bf43643958c36f58ed1eb4d0a497a2a37db0ad273d",
      "source_binding": {
        "source_id": "task031-vector-tube-geometry-source",
        "source_type": "approved-record",
        "source_revision": "1",
        "source_location": "memory://task031/design-vector",
        "evidence_ref": "task031-vector-tube-geometry-evidence",
        "approved_by": "design-vector-authority",
        "approved_at": "2026-08-17T00:00:00Z"
      }
    },
    "layout_rule_authority": {
      "profile_id": "hxforge.shell_tube.tube_layout.v1",
      "authority_mode": "INTERNAL_GENERIC",
      "rule_id": "task031-vector-layout-rule",
      "rule_version": "1",
      "rule_artifact_canonical_hash": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "source_class": "INTERNAL_ENGINEERING_RULE",
      "license_evidence": {
        "status": "NO_STANDARD_CLAIM"
      },
      "approval_status": "approved",
      "provenance_edge_ids": [
        "edge-task031-vector-1"
      ],
      "evidence_refs": [
        "task031-vector-layout-rule-evidence"
      ],
      "rule_pack_identity": null,
      "pattern_family": "SQUARE",
      "pitch_m": "0.025000000000",
      "edge_clearance_m": "0",
      "allowed_origin_modes": [
        "CENTER_ON_LATTICE_POINT"
      ],
      "allowed_axis_orientations": [
        "PRIMARY_AXIS_X"
      ],
      "allowed_exclusion_zone_types": [
        "AXIS_ALIGNED_RECTANGLE",
        "CIRCLE"
      ],
      "maximum_candidate_positions": 100000,
      "snapshot_hash": "aabb892634de529b39d6e238ab508dd66836a82e94e4e6dbb97f52b9d4b6a1c2"
    },
    "placement_envelope": {
      "schema_version": "task021.circular-envelope.v1",
      "tube_center_envelope_diameter_m": "0.500000000000",
      "evidence_refs": [
        "task031-vector-envelope-evidence"
      ]
    },
    "origin_mode": "CENTER_ON_LATTICE_POINT",
    "axis_orientation": "PRIMARY_AXIS_X",
    "exclusion_zones": [],
    "positions": [
      {
        "position_id": "9e8c208f4b01dad56d1db5c21edec68a04ec61442b729140c88580e26ad61f44",
        "u": 0,
        "v": 0,
        "x_m": "0.010000000000",
        "y_m": "0.000000000000"
      }
    ],
    "tube_hole_count": 1,
    "physical_tube_count": 1,
    "boundary_rejection_count": 0,
    "exclusion_rejection_count": 0,
    "exclusion_audit": [],
    "warnings": [],
    "blockers": [],
    "deferred_capabilities": [],
    "provenance": {
      "approval_status": "approved",
      "deferred_capabilities": [],
      "design_contract_path": "docs/tasks/TASK-021-shell-and-tube-tube-layout.md",
      "envelope_evidence_refs": [
        "task024-envelope-evidence"
      ],
      "exclusion_zone_evidence_refs": [],
      "geometry_id": "task031-vector-tube-od-19mm",
      "geometry_record_hash": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
      "geometry_revision": "1",
      "geometry_source_binding": {
        "approved_at": "2026-08-17T00:00:00Z",
        "approved_by": "design-vector-authority",
        "evidence_ref": "task031-vector-tube-geometry-evidence",
        "source_id": "task031-vector-tube-geometry-source",
        "source_location": "memory://task031/design-vector",
        "source_revision": "1",
        "source_type": "approved-record"
      },
      "git_commit": "test-only",
      "layout_rule_evidence_refs": [
        "task031-vector-layout-rule-evidence"
      ],
      "layout_rule_id": "task031-vector-layout-rule",
      "layout_rule_profile_id": "hxforge.shell_tube.tube_layout.v1",
      "layout_rule_snapshot_hash": "aabb892634de529b39d6e238ab508dd66836a82e94e4e6dbb97f52b9d4b6a1c2",
      "layout_rule_version": "1",
      "provenance_edge_ids": [
        "edge-task031-vector-1"
      ],
      "request_hash": "93f3ea2badfa489da56dadadcb13f296b85f4b2efd7dc82311827acf707dd0ce",
      "rule_artifact_canonical_hash": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd",
      "rule_pack_identity": null,
      "software_version": "task024-test",
      "source_class": "INTERNAL_ENGINEERING_RULE",
      "task020_case_authority": {
        "domain_snapshot_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        "payload_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "revision_id": "rev-task024-001",
        "revision_status": "committed"
      },
      "task020_configuration_hash": "b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9",
      "task020_configuration_id": "050a7064-af75-5990-82a1-51f0eb0a3a6b",
      "task_id": "task021",
      "tube_geometry_snapshot_hash": "5e684672eb15a7173e0154bf43643958c36f58ed1eb4d0a497a2a37db0ad273d",
      "u_tube_pairing_evidence_refs": null,
      "warnings": []
    }
  },
  "baffle_geometry_result": {
    "status": "VALID",
    "geometry": {
      "schema_version": "task024.baffle-geometry.v1",
      "geometry_id": "f701890c-8848-517b-ab72-48f8f78c4b0a",
      "geometry_hash": "8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f",
      "request_hash": "864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab",
      "task020_configuration_id": "050a7064-af75-5990-82a1-51f0eb0a3a6b",
      "task020_configuration_hash": "b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9",
      "task021_layout_id": "c79cb4d3-824b-52c0-a7b2-81e926fb3849",
      "task021_layout_hash": "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f",
      "task022_geometry_id": "d107c851-1d8d-5967-b124-d941d2bd0055",
      "task022_geometry_hash": "60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f",
      "construction_family": "FIXED_TUBESHEET",
      "equipment_orientation": "HORIZONTAL",
      "shell_pass_count": 1,
      "tube_pass_count": 2,
      "shell_inside_diameter_m": "0.250000000000",
      "tube_outer_diameter_m": "0.019000000000",
      "axial_span": {
        "schema_version": "task024.baffle-axial-span.v1",
        "axial_start_coordinate_m": "0.0",
        "axial_end_coordinate_m": "0.375000000000",
        "evidence_refs": [
          "task024-axial-evidence"
        ],
        "authority_hash": "32cf6d50431010f1d5366b9bbdb5bf1c41da7cbd2926e9ae169cf613e38f9af2"
      },
      "design_authority": {
        "schema_version": "task024.caller-baffle-design-authority.v1",
        "baffle_type": "SINGLE_SEGMENTAL",
        "baffle_count": 2,
        "baffle_thickness_m": "0.01",
        "spacing_sequence_m": [
          "0.125000000000",
          "0.125000000000",
          "0.125000000000"
        ],
        "baffle_cut_fraction": "0.25",
        "orientation_sequence": [
          "TOP",
          "TOP"
        ],
        "shell_to_baffle_diametral_clearance_m": "0.001",
        "tube_to_baffle_hole_diametral_clearance_m": "0.001",
        "evidence_refs": [
          "task024-design-evidence"
        ],
        "authority_hash": "1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188"
      },
      "usable_baffle_span_m": "0.375000000000",
      "baffle_diameter_m": "0.249000000000",
      "baffle_radius_m": "0.124500000000",
      "baffle_hole_diameter_m": "0.020000000000",
      "baffle_hole_radius_m": "0.010000000000",
      "cut_height_m": "0.062250000000",
      "chord_offset_from_center_m": "0.062250000000",
      "baffle_planes": [
        {
          "baffle_index": 0,
          "center_coordinate_m": "0.125000000000",
          "occupied_start_coordinate_m": "0.120000000000",
          "occupied_end_coordinate_m": "0.130000000000",
          "orientation": "TOP",
          "cut_chord": {
            "normal_x": 0,
            "normal_y": 1,
            "half_plane_offset_m": "0.062250000000",
            "chord_half_length_m": "0.107820162771",
            "endpoint_a_x_m": "-0.107820162771",
            "endpoint_a_y_m": "0.062250000000",
            "endpoint_b_x_m": "0.107820162771",
            "endpoint_b_y_m": "0.062250000000"
          },
          "window_region_semantics": "BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE",
          "baffle_covered_region_semantics": "BAFFLE_DISK_MINUS_WINDOW_SEGMENT",
          "crossflow_reference_region_semantics": "CLASSIFICATION_REFERENCE_ONLY_NOT_FLOW_AREA",
          "tube_hole_classifications": [
            {
              "position_id": "9e8c208f4b01dad56d1db5c21edec68a04ec61442b729140c88580e26ad61f44",
              "center_x_m": "0.010000000000",
              "center_y_m": "0",
              "physical_tube_radius_m": "0.009500000000",
              "baffle_hole_radius_m": "0.010000000000",
              "signed_window_distance_m": "-0.06225000000000",
              "cut_boundary_margin_m": "-0.07225000000000",
              "classification": "CROSSFLOW_REFERENCE",
              "outer_boundary_margin_squared_m2": "0.013010250000000000000000",
              "physical_tube_disk_audit": {
                "physical_tube_radius_m": "0.009500000000",
                "signed_window_distance_m": "-0.06225000000000",
                "cut_boundary_margin_m": "-0.07225000000000",
                "classification": "CROSSFLOW_REFERENCE"
              }
            }
          ],
          "window_position_ids": [],
          "crossflow_reference_position_ids": [
            "9e8c208f4b01dad56d1db5c21edec68a04ec61442b729140c88580e26ad61f44"
          ],
          "outer_tangent_position_ids": [],
          "pairwise_tangent_position_pairs": [],
          "classification_audit_hash": "718955d830fe25526fc5b232252940bd72879c22d2c6295815bda22ea09acacc"
        },
        {
          "baffle_index": 1,
          "center_coordinate_m": "0.250000000000",
          "occupied_start_coordinate_m": "0.245000000000",
          "occupied_end_coordinate_m": "0.255000000000",
          "orientation": "TOP",
          "cut_chord": {
            "normal_x": 0,
            "normal_y": 1,
            "half_plane_offset_m": "0.062250000000",
            "chord_half_length_m": "0.107820162771",
            "endpoint_a_x_m": "-0.107820162771",
            "endpoint_a_y_m": "0.062250000000",
            "endpoint_b_x_m": "0.107820162771",
            "endpoint_b_y_m": "0.062250000000"
          },
          "window_region_semantics": "BAFFLE_DISK_INTERSECTION_WINDOW_HALF_PLANE",
          "baffle_covered_region_semantics": "BAFFLE_DISK_MINUS_WINDOW_SEGMENT",
          "crossflow_reference_region_semantics": "CLASSIFICATION_REFERENCE_ONLY_NOT_FLOW_AREA",
          "tube_hole_classifications": [
            {
              "position_id": "9e8c208f4b01dad56d1db5c21edec68a04ec61442b729140c88580e26ad61f44",
              "center_x_m": "0.010000000000",
              "center_y_m": "0",
              "physical_tube_radius_m": "0.009500000000",
              "baffle_hole_radius_m": "0.010000000000",
              "signed_window_distance_m": "-0.06225000000000",
              "cut_boundary_margin_m": "-0.07225000000000",
              "classification": "CROSSFLOW_REFERENCE",
              "outer_boundary_margin_squared_m2": "0.013010250000000000000000",
              "physical_tube_disk_audit": {
                "physical_tube_radius_m": "0.009500000000",
                "signed_window_distance_m": "-0.06225000000000",
                "cut_boundary_margin_m": "-0.07225000000000",
                "classification": "CROSSFLOW_REFERENCE"
              }
            }
          ],
          "window_position_ids": [],
          "crossflow_reference_position_ids": [
            "9e8c208f4b01dad56d1db5c21edec68a04ec61442b729140c88580e26ad61f44"
          ],
          "outer_tangent_position_ids": [],
          "pairwise_tangent_position_pairs": [],
          "classification_audit_hash": "0b493917e7a1fac368487d541aaf6150ebfed338ecf4914455c2d85b8a1f68b6"
        }
      ],
      "position_count": 1,
      "warnings": [
        {
          "code": "BFG_FIXED_TUBESHEET_ONLY_V1",
          "field_path": "configuration.construction_family",
          "message_key": "fixed_tubesheet_only_v1",
          "evidence_refs": [
            "task031-vector-baffle-evidence"
          ],
          "details": [
            [
              "construction_family",
              "FIXED_TUBESHEET"
            ]
          ]
        },
        {
          "code": "BFG_GEOMETRY_NOT_FLOW_AREA",
          "field_path": null,
          "message_key": "geometry_not_flow_area",
          "evidence_refs": [
            "task031-vector-baffle-evidence"
          ],
          "details": [
            [
              "flow_area_calculation_performed",
              "false"
            ]
          ]
        },
        {
          "code": "BFG_NOZZLE_POSITION_DEFERRED",
          "field_path": null,
          "message_key": "nozzle_position_deferred",
          "evidence_refs": [
            "task031-vector-baffle-evidence"
          ],
          "details": [
            [
              "nozzle_position_inference_performed",
              "false"
            ]
          ]
        },
        {
          "code": "BFG_THERMAL_HYDRAULIC_DEFERRED",
          "field_path": null,
          "message_key": "thermal_hydraulic_deferred",
          "evidence_refs": [
            "task031-vector-baffle-evidence"
          ],
          "details": [
            [
              "thermal_hydraulic_calculation_performed",
              "false"
            ]
          ]
        },
        {
          "code": "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
          "field_path": "design_authority",
          "message_key": "caller_supplied_no_standard_claim",
          "evidence_refs": [
            "task024-design-evidence"
          ],
          "details": [
            [
              "authority_mode",
              "CALLER_SUPPLIED_EXPLICIT"
            ],
            [
              "standard_claim_status",
              "NO_STANDARD_CLAIM"
            ]
          ]
        }
      ],
      "blockers": [],
      "deferred_capabilities": [
        "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
        "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
        "MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE",
        "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
        "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
        "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
        "LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE",
        "BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE",
        "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
        "KERN_SCREENING_NOT_COMPUTABLE",
        "BELL_DELAWARE_NOT_COMPUTABLE",
        "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
        "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
        "FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE",
        "THERMAL_EXPANSION_NOT_COMPUTABLE",
        "MECHANICAL_ADEQUACY_NOT_COMPUTABLE",
        "MANUFACTURING_ADEQUACY_NOT_COMPUTABLE",
        "MATERIAL_SELECTION_NOT_COMPUTABLE",
        "MASS_NOT_COMPUTABLE",
        "COST_NOT_COMPUTABLE",
        "OPTIMIZATION_NOT_COMPUTABLE",
        "API_NOT_COMPUTABLE",
        "PERSISTENCE_NOT_COMPUTABLE",
        "CLI_NOT_COMPUTABLE",
        "REPORT_NOT_COMPUTABLE",
        "GOLDEN_VALIDATION_NOT_COMPUTABLE"
      ],
      "provenance": [
        [
          "task_id",
          "TASK-024"
        ],
        [
          "design_contract_path",
          "docs/tasks/TASK-024-shell-and-tube-baffle-geometry-and-spacing.md"
        ],
        [
          "profile_id",
          "hxforge.shell_tube.baffle_geometry.v1"
        ],
        [
          "software_version",
          "task024.minimal-compute-v1"
        ],
        [
          "git_commit",
          "82ce66fa1e479c5affd64f08c98496425d8bc09b"
        ],
        [
          "task020_configuration_id",
          "050a7064-af75-5990-82a1-51f0eb0a3a6b"
        ],
        [
          "task020_configuration_hash",
          "b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9"
        ],
        [
          "task020_case_authority",
          {
            "revision_id": "rev-task024-001",
            "payload_hash": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            "domain_snapshot_hash": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
            "revision_status": "COMMITTED"
          }
        ],
        [
          "task021_layout_id",
          "c79cb4d3-824b-52c0-a7b2-81e926fb3849"
        ],
        [
          "task021_layout_hash",
          "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f"
        ],
        [
          "task021_tube_geometry_snapshot_hash",
          "5e684672eb15a7173e0154bf43643958c36f58ed1eb4d0a497a2a37db0ad273d"
        ],
        [
          "task021_layout_rule_snapshot_hash",
          "aabb892634de529b39d6e238ab508dd66836a82e94e4e6dbb97f52b9d4b6a1c2"
        ],
        [
          "task022_geometry_id",
          "d107c851-1d8d-5967-b124-d941d2bd0055"
        ],
        [
          "task022_geometry_hash",
          "60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f"
        ],
        [
          "task022_shell_authority_mode",
          "CALLER_SUPPLIED_EXPLICIT"
        ],
        [
          "task022_shell_authority_identity",
          {
            "shell_authority_mode": "CALLER_SUPPLIED_EXPLICIT",
            "caller_supplied_shell": null,
            "approved_shell_geometry": null
          }
        ],
        [
          "task022_geometry_rule_snapshot_hash",
          "815b9c91935ff319bf00c40c26993a8cc8c941e7ed0eb7fc98774a8a9e26ecce"
        ],
        [
          "axial_span_authority_hash",
          "32cf6d50431010f1d5366b9bbdb5bf1c41da7cbd2926e9ae169cf613e38f9af2"
        ],
        [
          "baffle_design_authority_hash",
          "1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188"
        ],
        [
          "request_hash",
          "864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab"
        ],
        [
          "source_claim_status",
          "NO_STANDARD_CLAIM"
        ],
        [
          "automatic_selection_performed",
          false
        ],
        [
          "nozzle_position_inference_performed",
          false
        ],
        [
          "flow_area_calculation_performed",
          false
        ],
        [
          "warnings",
          [
            {
              "code": "BFG_FIXED_TUBESHEET_ONLY_V1",
              "field_path": "configuration.construction_family",
              "message_key": "fixed_tubesheet_only_v1",
              "evidence_refs": [
                "task031-vector-baffle-evidence"
              ],
              "details": [
                [
                  "construction_family",
                  "FIXED_TUBESHEET"
                ]
              ]
            },
            {
              "code": "BFG_GEOMETRY_NOT_FLOW_AREA",
              "field_path": null,
              "message_key": "geometry_not_flow_area",
              "evidence_refs": [
                "task031-vector-baffle-evidence"
              ],
              "details": [
                [
                  "flow_area_calculation_performed",
                  "false"
                ]
              ]
            },
            {
              "code": "BFG_NOZZLE_POSITION_DEFERRED",
              "field_path": null,
              "message_key": "nozzle_position_deferred",
              "evidence_refs": [
                "task031-vector-baffle-evidence"
              ],
              "details": [
                [
                  "nozzle_position_inference_performed",
                  "false"
                ]
              ]
            },
            {
              "code": "BFG_THERMAL_HYDRAULIC_DEFERRED",
              "field_path": null,
              "message_key": "thermal_hydraulic_deferred",
              "evidence_refs": [
                "task031-vector-baffle-evidence"
              ],
              "details": [
                [
                  "thermal_hydraulic_calculation_performed",
                  "false"
                ]
              ]
            },
            {
              "code": "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
              "field_path": "design_authority",
              "message_key": "caller_supplied_no_standard_claim",
              "evidence_refs": [
                "task024-design-evidence"
              ],
              "details": [
                [
                  "authority_mode",
                  "CALLER_SUPPLIED_EXPLICIT"
                ],
                [
                  "standard_claim_status",
                  "NO_STANDARD_CLAIM"
                ]
              ]
            }
          ]
        ],
        [
          "deferred_capabilities",
          [
            "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
            "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
            "MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE",
            "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
            "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
            "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
            "LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE",
            "BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE",
            "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
            "KERN_SCREENING_NOT_COMPUTABLE",
            "BELL_DELAWARE_NOT_COMPUTABLE",
            "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
            "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
            "FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE",
            "THERMAL_EXPANSION_NOT_COMPUTABLE",
            "MECHANICAL_ADEQUACY_NOT_COMPUTABLE",
            "MANUFACTURING_ADEQUACY_NOT_COMPUTABLE",
            "MATERIAL_SELECTION_NOT_COMPUTABLE",
            "MASS_NOT_COMPUTABLE",
            "COST_NOT_COMPUTABLE",
            "OPTIMIZATION_NOT_COMPUTABLE",
            "API_NOT_COMPUTABLE",
            "PERSISTENCE_NOT_COMPUTABLE",
            "CLI_NOT_COMPUTABLE",
            "REPORT_NOT_COMPUTABLE",
            "GOLDEN_VALIDATION_NOT_COMPUTABLE"
          ]
        ]
      ]
    },
    "warnings": [
      {
        "code": "BFG_FIXED_TUBESHEET_ONLY_V1",
        "field_path": "configuration.construction_family",
        "message_key": "fixed_tubesheet_only_v1",
        "evidence_refs": [
          "task031-vector-baffle-evidence"
        ],
        "details": [
          [
            "construction_family",
            "FIXED_TUBESHEET"
          ]
        ]
      },
      {
        "code": "BFG_GEOMETRY_NOT_FLOW_AREA",
        "field_path": null,
        "message_key": "geometry_not_flow_area",
        "evidence_refs": [
          "task031-vector-baffle-evidence"
        ],
        "details": [
          [
            "flow_area_calculation_performed",
            "false"
          ]
        ]
      },
      {
        "code": "BFG_NOZZLE_POSITION_DEFERRED",
        "field_path": null,
        "message_key": "nozzle_position_deferred",
        "evidence_refs": [
          "task031-vector-baffle-evidence"
        ],
        "details": [
          [
            "nozzle_position_inference_performed",
            "false"
          ]
        ]
      },
      {
        "code": "BFG_THERMAL_HYDRAULIC_DEFERRED",
        "field_path": null,
        "message_key": "thermal_hydraulic_deferred",
        "evidence_refs": [
          "task031-vector-baffle-evidence"
        ],
        "details": [
          [
            "thermal_hydraulic_calculation_performed",
            "false"
          ]
        ]
      },
      {
        "code": "BFG_CALLER_SUPPLIED_NO_STANDARD_CLAIM",
        "field_path": "design_authority",
        "message_key": "caller_supplied_no_standard_claim",
        "evidence_refs": [
          "task024-design-evidence"
        ],
        "details": [
          [
            "authority_mode",
            "CALLER_SUPPLIED_EXPLICIT"
          ],
          [
            "standard_claim_status",
            "NO_STANDARD_CLAIM"
          ]
        ]
      }
    ],
    "blockers": [],
    "deferred_capabilities": [
      "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
      "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
      "MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE",
      "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
      "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
      "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
      "LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE",
      "BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE",
      "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
      "KERN_SCREENING_NOT_COMPUTABLE",
      "BELL_DELAWARE_NOT_COMPUTABLE",
      "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
      "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
      "FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE",
      "THERMAL_EXPANSION_NOT_COMPUTABLE",
      "MECHANICAL_ADEQUACY_NOT_COMPUTABLE",
      "MANUFACTURING_ADEQUACY_NOT_COMPUTABLE",
      "MATERIAL_SELECTION_NOT_COMPUTABLE",
      "MASS_NOT_COMPUTABLE",
      "COST_NOT_COMPUTABLE",
      "OPTIMIZATION_NOT_COMPUTABLE",
      "API_NOT_COMPUTABLE",
      "PERSISTENCE_NOT_COMPUTABLE",
      "CLI_NOT_COMPUTABLE",
      "REPORT_NOT_COMPUTABLE",
      "GOLDEN_VALIDATION_NOT_COMPUTABLE"
    ],
    "blocked_result_hash": null
  },
  "engineering_authority": {
    "schema_version": "task031.engineering-authority-request.v1",
    "authority_profile_id": "TASK031_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_V1_FORMULA_AUTHORITY",
    "authority_hash": "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989",
    "evidence_refs": [
      "task031-design-vector-evidence-001"
    ]
  },
  "evidence_refs": [
    "task031-design-vector-evidence-001"
  ]
}
```

### 23.2.1 Frozen vector-record schema

Every engineering vector record contains exactly these 16 semantic fields:

```text
VECTOR_RECORD_FIELD_COUNT=16
```

1. `VECTOR_ID`
2. `BASE_FIXTURE_ID`
3. `MUTATION_COUNT`
4. `MUTATIONS_IN_ORDER`
5. `FINAL_CHANGED_FIELDS`
6. `FINAL_EXPECTED_UPSTREAM_IDS_HASHES`
7. `EXPECTED_STATUS`
8. `EXPECTED_FAILURE_STAGE`
9. `EXPECTED_BLOCKER_CODES_IN_ORDER`
10. `EXPECTED_WARNING_CODES_IN_ORDER`
11. `EXPECTED_FORMULA_BRANCH`
12. `EXPECTED_RAW_AS`
13. `EXPECTED_PUBLIC_AS`
14. `EXPECTED_RAW_DE`
15. `EXPECTED_PUBLIC_DE`
16. `ORACLE_DERIVATION`

Unreachable fields on blocked vectors use literal token `NOT_REACHED`.
Semantically non-applicable but reached fields use `NOT_APPLICABLE`.

Mutation records use exact tuple form
`(sequence_number, json_pointer_or_exact_field_path, old_literal, new_literal)`.

`VECTOR_IDENTITY_REPLAY_PASS` definition for next rereview:

- (A) all non-intentionally-corrupted upstream objects replay to pinned IDs/hashes
  before the expected failure stage;
- (B) intentional mismatch vectors reproduce exactly one declared mismatch;
- (C) the vector reaches its intended failure/validity stage without accidental
  stale identity failure.

Pure formula/oracle arithmetic alone is not identity replay.

### 23.3 Vector registry

Mutation discipline: each vector lists exact JSON-pointer mutation records against
`TASK031_VECTOR_BASE_FIXTURE_V1` unless a complete replacement raw request fragment
is pinned. Any mutation that changes upstream identity pins the resulting IDs/hashes
in `FINAL_EXPECTED_UPSTREAM_IDS_HASHES`.

#### V1 — valid SQUARE (equals base fixture)

| Field | Value |
|---|---|
| VECTOR_ID | V1 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 0 |
| MUTATIONS_IN_ORDER | () |
| FINAL_CHANGED_FIELDS | () |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | VALID |
| EXPECTED_FAILURE_STAGE | NOT_REACHED |
| EXPECTED_BLOCKER_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | Formula B square |
| EXPECTED_RAW_AS | 0.00750 |
| EXPECTED_PUBLIC_AS | 0.007500000000000000000000 |
| EXPECTED_RAW_DE | 0.022882879761025088360232569308556411061699906773805 |
| EXPECTED_PUBLIC_DE | 0.022882879761 |
| ORACLE_DERIVATION | §11.8 independent Decimal evaluation |

#### V2 — valid TRIANGULAR

| Field | Value |
|---|---|
| VECTOR_ID | V2 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /tube_layout/layout_rule_authority/pattern_family, "SQUARE", "TRIANGULAR")) |
| FINAL_CHANGED_FIELDS | (tube_layout.layout_rule_authority.pattern_family, tube_layout.layout_id, tube_layout.layout_hash, baffle_geometry_result.geometry.task021_layout_id, baffle_geometry_result.geometry.task021_layout_hash, baffle_geometry_result.geometry.geometry_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="117e8aeb-7bfb-50cb-b37c-532f716d345e", task021_layout_hash="3cd748e4ff1de456e7e0ccbba632d2590495ed0348be855ac07e6b964756bc59", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="c03ef2c02ab56daa1786f25d2a2e380803ba89edebf67acaf3bed2a525dfc249", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | VALID |
| EXPECTED_FAILURE_STAGE | NOT_REACHED |
| EXPECTED_BLOCKER_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | Formula B triangular |
| EXPECTED_RAW_AS | 0.00750 |
| EXPECTED_PUBLIC_AS | 0.007500000000000000000000 |
| EXPECTED_RAW_DE | 0.017271637856696845362587269625853252723512268445175 |
| EXPECTED_PUBLIC_DE | 0.017271637857 |
| ORACLE_DERIVATION | §11.8 independent Decimal evaluation |

#### V3 — minimum topology N=2

| Field | Value |
|---|---|
| VECTOR_ID | V3 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 3 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/design_authority/spacing_sequence_m, ["0.125000000000", "0.125000000000", "0.125000000000"], ["0.100000000000", "0.125000000000", "0.130000000000"]), (2, /baffle_geometry_result/geometry/design_authority/authority_hash, "1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188", "a6ff07c6ebbd3853cb70f1c327b900bc04f4d781d0d79d276ab1540b2bbf768a"), (3, /baffle_geometry_result/geometry/geometry_hash, "8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", "a37700417d2183ce7708a37d7c3d068faad1b58d6c338c58533bd2b99215e1d1")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.design_authority.spacing_sequence_m, baffle_geometry_result.geometry.design_authority.authority_hash, baffle_geometry_result.geometry.geometry_hash, baffle_geometry_result.geometry.axial_span.axial_end_coordinate_m) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="a37700417d2183ce7708a37d7c3d068faad1b58d6c338c58533bd2b99215e1d1", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="a6ff07c6ebbd3853cb70f1c327b900bc04f4d781d0d79d276ab1540b2bbf768a") |
| EXPECTED_STATUS | VALID |
| EXPECTED_FAILURE_STAGE | NOT_REACHED |
| EXPECTED_BLOCKER_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | Formula B square |
| EXPECTED_RAW_AS | 0.00750 |
| EXPECTED_PUBLIC_AS | 0.007500000000000000000000 |
| EXPECTED_RAW_DE | NOT_APPLICABLE |
| EXPECTED_PUBLIC_DE | NOT_APPLICABLE |
| ORACLE_DERIVATION | §11.8 with B=0.125000000000 |

#### V4 — inlet/outlet differ, central uniform

| Field | Value |
|---|---|
| VECTOR_ID | V4 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 4 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/design_authority/baffle_count, 2, 3), (2, /baffle_geometry_result/geometry/design_authority/spacing_sequence_m, ["0.125000000000", "0.125000000000", "0.125000000000"], ["0.100000000000", "0.125000000000", "0.125000000000", "0.140000000000"]), (3, /baffle_geometry_result/geometry/design_authority/authority_hash, "1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188", "cf6ba663d93364fefea2d44dc892eb529d33da766999661d3b5b56899e9e0bff"), (4, /baffle_geometry_result/geometry/geometry_hash, "8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", "317f36c472838da562466c8c8e2b559aeee59799d181b28898be99fab5b34a21")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.design_authority.baffle_count, baffle_geometry_result.geometry.design_authority.spacing_sequence_m, baffle_geometry_result.geometry.design_authority.authority_hash, baffle_geometry_result.geometry.geometry_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="317f36c472838da562466c8c8e2b559aeee59799d181b28898be99fab5b34a21", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="cf6ba663d93364fefea2d44dc892eb529d33da766999661d3b5b56899e9e0bff") |
| EXPECTED_STATUS | VALID |
| EXPECTED_FAILURE_STAGE | NOT_REACHED |
| EXPECTED_BLOCKER_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | Formula B square |
| EXPECTED_RAW_AS | 0.00750 |
| EXPECTED_PUBLIC_AS | 0.007500000000000000000000 |
| EXPECTED_RAW_DE | NOT_APPLICABLE |
| EXPECTED_PUBLIC_DE | NOT_APPLICABLE |
| ORACLE_DERIVATION | §11.8 with B=0.125000000000 |

#### V5 — nonuniform central spacing

| Field | Value |
|---|---|
| VECTOR_ID | V5 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 4 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/design_authority/baffle_count, 2, 3), (2, /baffle_geometry_result/geometry/design_authority/spacing_sequence_m, ["0.125000000000", "0.125000000000", "0.125000000000"], ["0.100000000000", "0.125000000000", "0.130000000000", "0.140000000000"]), (3, /baffle_geometry_result/geometry/design_authority/authority_hash, "1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188", "8283c50b01611e5ebab8e86d188be4cc558e500fa24d5d8235490acb23f8d391"), (4, /baffle_geometry_result/geometry/geometry_hash, "8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", "d53ca543989ba9ce2bb02c89376d443518b259852fd043d54dbc5be6aad4cf72")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.design_authority.baffle_count, baffle_geometry_result.geometry.design_authority.spacing_sequence_m, baffle_geometry_result.geometry.design_authority.authority_hash, baffle_geometry_result.geometry.geometry_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="d53ca543989ba9ce2bb02c89376d443518b259852fd043d54dbc5be6aad4cf72", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="8283c50b01611e5ebab8e86d188be4cc558e500fa24d5d8235490acb23f8d391") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 6 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM) |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V6 — pitch equals tube OD

| Field | Value |
|---|---|
| VECTOR_ID | V6 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 2 |
| MUTATIONS_IN_ORDER | ((1, /tube_layout/layout_rule_authority/pitch_m, "0.025000000000", "0.019000000000"), (2, /tube_layout/tube_geometry/outer_diameter_m, "0.019000000000", "0.019000000000")) |
| FINAL_CHANGED_FIELDS | (tube_layout.layout_rule_authority.pitch_m, tube_layout.tube_geometry.outer_diameter_m) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 8 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD) |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V7 — pitch less than tube OD

| Field | Value |
|---|---|
| VECTOR_ID | V7 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 2 |
| MUTATIONS_IN_ORDER | ((1, /tube_layout/layout_rule_authority/pitch_m, "0.025000000000", "0.018000000000"), (2, /tube_layout/tube_geometry/outer_diameter_m, "0.019000000000", "0.019000000000")) |
| FINAL_CHANGED_FIELDS | (tube_layout.layout_rule_authority.pitch_m) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 8 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD) |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V8 — unsupported pattern token at TASK-021 nested decode boundary

| Field | Value |
|---|---|
| VECTOR_ID | V8 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /tube_layout/layout_rule_authority/pattern_family, "SQUARE", "ROSETTE")) |
| FINAL_CHANGED_FIELDS | (tube_layout.layout_rule_authority.pattern_family) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 2 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_TASK021_LAYOUT_INVALID) |
| EXPECTED_WARNING_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V9 — TASK-021/TASK-024 tube OD mismatch

| Field | Value |
|---|---|
| VECTOR_ID | V9 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/tube_outer_diameter_m, "0.019000000000", "0.020000000000")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.tube_outer_diameter_m) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 5 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_TASK021_TASK024_TUBE_OD_MISMATCH) |
| EXPECTED_WARNING_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V10 — TASK-024 identity mismatch (single field)

| Field | Value |
|---|---|
| VECTOR_ID | V10 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/task021_layout_hash, "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", "97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb90")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.task021_layout_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f EXPECTED_LITERAL=97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb90 IDENTITY_EXPECTATION=INTENTIONAL_MISMATCH", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 4 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_TASK024_IDENTITY_MISMATCH) |
| EXPECTED_WARNING_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V11 — TASK-024 producer BLOCKED

| Field | Value |
|---|---|
| VECTOR_ID | V11 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 4 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/status, "VALID", "BLOCKED"), (2, /baffle_geometry_result/geometry, "VALID_GEOMETRY_OBJECT", null), (3, /baffle_geometry_result/blockers, [], [{"code": "BFG_BAFFLE_THICKNESS_INVALID", "field_path": "design_authority.baffle_thickness_m", "message_key": "baffle_thickness_non_positive", "evidence_refs": [], "details": [["baffle_thickness_m", "0"]]}]), (4, /baffle_geometry_result/blocked_result_hash, null, "0307b72479e2df79b5caaaac271904b64d20f9f32116627f6a2d06dbdfcaf6e0")) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.status, baffle_geometry_result.geometry, baffle_geometry_result.blockers, baffle_geometry_result.blocked_result_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 4 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_TASK024_RESULT_HAS_BLOCKERS) |
| EXPECTED_WARNING_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V12 — TASK-024 VALID with geometry null

| Field | Value |
|---|---|
| VECTOR_ID | V12 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry, "VALID_GEOMETRY_OBJECT", null)) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 4 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_TASK024_GEOMETRY_MISSING) |
| EXPECTED_WARNING_CODES_IN_ORDER | NOT_REACHED |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V13 — area quantization collapse

| Field | Value |
|---|---|
| VECTOR_ID | V13 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 2 |
| MUTATIONS_IN_ORDER | ((1, /baffle_geometry_result/geometry/shell_inside_diameter_m, "0.250000000000", "0.000000000001"), (2, /baffle_geometry_result/geometry/design_authority/spacing_sequence_m, ["0.125000000000", "0.125000000000", "0.125000000000"], ["0.000000000001", "0.000000000001", "0.000000000001"])) |
| FINAL_CHANGED_FIELDS | (baffle_geometry_result.geometry.shell_inside_diameter_m, baffle_geometry_result.geometry.design_authority.spacing_sequence_m) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 9 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION) |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | 2.4e-25 |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | independent Decimal: Ds=1e-12, B=1e-12, Pt=0.025, do=0.019 |

#### V14 — engineering authority identity mismatch

| Field | Value |
|---|---|
| VECTOR_ID | V14 |
| BASE_FIXTURE_ID | TASK031_VECTOR_BASE_FIXTURE_V1 |
| MUTATION_COUNT | 1 |
| MUTATIONS_IN_ORDER | ((1, /engineering_authority/authority_hash, "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989", "1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837980")) |
| FINAL_CHANGED_FIELDS | (engineering_authority.authority_hash) |
| FINAL_EXPECTED_UPSTREAM_IDS_HASHES | (task020_configuration_id="050a7064-af75-5990-82a1-51f0eb0a3a6b", task020_configuration_hash="b6d726e966096d77b318ca70509994f4752aaa8f2ddb2c158aebd7ca472bebf9", task021_layout_id="c79cb4d3-824b-52c0-a7b2-81e926fb3849", task021_layout_hash="97d1200527c15fe8fe9b3e778f1054cea32bf4d575ff96250eb2ceeb6666fb9f", task022_geometry_id="d107c851-1d8d-5967-b124-d941d2bd0055", task022_geometry_hash="60a58066f8b0df81af79fbe29d720db0d9e902f4c1c3dd5e78fa51ff36319c9f", task024_geometry_id="f701890c-8848-517b-ab72-48f8f78c4b0a", task024_geometry_hash="8c50949b859c55616cff83ec28e2c03ab7940532030298e8428ac8ee8b264a9f", task024_request_hash="864300a3693b16e14c96393d222d660d0c427f4e5d5309629489db765d34b9ab", task024_design_authority_hash="1904045091c5341689ab919718a6147a983cb112e6ffd0340ad76abc18e04188", engineering_authority_hash="1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837989 EXPECTED_LITERAL=1cb5cf1ff9f28fb2dec074f6458473e60d0866c744fbd97501e41d68b5837980 IDENTITY_EXPECTATION=INTENTIONAL_MISMATCH") |
| EXPECTED_STATUS | BLOCKED |
| EXPECTED_FAILURE_STAGE | 7 |
| EXPECTED_BLOCKER_CODES_IN_ORDER | (SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH) |
| EXPECTED_WARNING_CODES_IN_ORDER | (SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY, SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED, SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED, SSHG_MINIMUM_AREA_SELECTION_DEFERRED, SSHG_NO_FULL_EXCHANGER_RATING_CLAIM, SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED) |
| EXPECTED_FORMULA_BRANCH | NOT_REACHED |
| EXPECTED_RAW_AS | NOT_REACHED |
| EXPECTED_PUBLIC_AS | NOT_REACHED |
| EXPECTED_RAW_DE | NOT_REACHED |
| EXPECTED_PUBLIC_DE | NOT_REACHED |
| ORACLE_DERIVATION | NOT_REACHED |

#### V11 pinned `TASK024_BLOCKED_RESULT_FRAGMENT`

Design-time construction route:
`hexagent.exchangers.shell_tube.baffle_geometry.geometry::compute_geometry_foundation`
with `design_authority.baffle_thickness_m="0"` on the oracle TASK-024 request.
`blocked_result_hash` is `sha256_hex(raw_blocked_projection(request))` per TASK-024 §14.6.

```json
{
  "status": "BLOCKED",
  "geometry": null,
  "warnings": [],
  "blockers": [
    {
      "code": "BFG_BAFFLE_THICKNESS_INVALID",
      "field_path": "design_authority.baffle_thickness_m",
      "message_key": "baffle_thickness_non_positive",
      "evidence_refs": [],
      "details": [
        [
          "baffle_thickness_m",
          "0"
        ]
      ]
    }
  ],
  "deferred_capabilities": [
    "CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE",
    "WINDOW_FLOW_AREA_NOT_COMPUTABLE",
    "MINIMUM_CROSSFLOW_AREA_NOT_COMPUTABLE",
    "HYDRAULIC_DIAMETER_NOT_COMPUTABLE",
    "LEAKAGE_FLOW_AREA_NOT_COMPUTABLE",
    "BYPASS_FLOW_AREA_NOT_COMPUTABLE",
    "LEAKAGE_CORRECTION_FACTOR_NOT_COMPUTABLE",
    "BYPASS_CORRECTION_FACTOR_NOT_COMPUTABLE",
    "SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE",
    "KERN_SCREENING_NOT_COMPUTABLE",
    "BELL_DELAWARE_NOT_COMPUTABLE",
    "SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE",
    "FLOW_INDUCED_VIBRATION_NOT_COMPUTABLE",
    "THERMAL_EXPANSION_NOT_COMPUTABLE",
    "MECHANICAL_ADEQUACY_NOT_COMPUTABLE",
    "MANUFACTURING_ADEQUACY_NOT_COMPUTABLE",
    "MATERIAL_SELECTION_NOT_COMPUTABLE",
    "MASS_NOT_COMPUTABLE",
    "COST_NOT_COMPUTABLE",
    "OPTIMIZATION_NOT_COMPUTABLE",
    "API_NOT_COMPUTABLE",
    "PERSISTENCE_NOT_COMPUTABLE",
    "CLI_NOT_COMPUTABLE",
    "REPORT_NOT_COMPUTABLE",
    "GOLDEN_VALIDATION_NOT_COMPUTABLE"
  ],
  "blocked_result_hash": "0307b72479e2df79b5caaaac271904b64d20f9f32116627f6a2d06dbdfcaf6e0"
}
```

### 23.3.1 Vector fixture derivation annex

Design-time derivation inputs for vectors whose upstream identities change beyond
the embedded base fixture. Each entry is replayable from the accepted baseline
using the helpers in §23.

| VECTOR_ID | VECTOR_FIXTURE_DERIVATION_INPUT | VECTOR_FIXTURE_DERIVATION_ENTRY | EXPECTED_PRODUCER_OUTPUT_ID | EXPECTED_PRODUCER_OUTPUT_HASH |
|---|---|---|---|---|
| V2 | `TASK031_VECTOR_BASE_FIXTURE_V1` + mutation `(1, /tube_layout/layout_rule_authority/pattern_family, "SQUARE", "TRIANGULAR")` + TASK-024 composition rebuild | `tests.exchangers.shell_tube.baffle_geometry._builders` + `hexagent.exchangers.shell_tube.tube_layout.canonical` + `hexagent.exchangers.shell_tube.baffle_geometry.authority::validate_authority_foundation` + `hexagent.exchangers.shell_tube.baffle_geometry.geometry::compute_geometry_foundation` | `117e8aeb-7bfb-50cb-b37c-532f716d345e` | `task021_layout_hash=3cd748e4ff1de456e7e0ccbba632d2590495ed0348be855ac07e6b964756bc59`; `task024_geometry_hash=c03ef2c02ab56daa1786f25d2a2e380803ba89edebf67acaf3bed2a525dfc249` |
| V3 | base + `spacing_sequence_m=["0.100000000000","0.125000000000","0.130000000000"]`, `baffle_count=2` | same TASK-024 composition route as V2 | unchanged `task021_layout_id` | `task024_geometry_hash=a37700417d2183ce7708a37d7c3d068faad1b58d6c338c58533bd2b99215e1d1`; `task024_design_authority_hash=a6ff07c6ebbd3853cb70f1c327b900bc04f4d781d0d79d276ab1540b2bbf768a` |
| V4 | base + `baffle_count=3`, `spacing_sequence_m=["0.100000000000","0.125000000000","0.125000000000","0.140000000000"]` | same TASK-024 composition route as V2 | unchanged `task021_layout_id` | `task024_geometry_hash=317f36c472838da562466c8c8e2b559aeee59799d181b28898be99fab5b34a21`; `task024_design_authority_hash=cf6ba663d93364fefea2d44dc892eb529d33da766999661d3b5b56899e9e0bff` |
| V5 | base + `baffle_count=3`, `spacing_sequence_m=["0.100000000000","0.125000000000","0.130000000000","0.140000000000"]` | same TASK-024 composition route as V2; TASK-024 authority+geometry foundation pass before TASK-031 Stage 6 | unchanged `task021_layout_id` | `task024_geometry_hash=d53ca543989ba9ce2bb02c89376d443518b259852fd043d54dbc5be6aad4cf72`; `task024_design_authority_hash=8283c50b01611e5ebab8e86d188be4cc558e500fa24d5d8235490acb23f8d391` |

Vectors V6–V14 derive from `TASK031_VECTOR_BASE_FIXTURE_V1` using only the exact
`MUTATIONS_IN_ORDER` records in §23.3. V11 additionally pins the exact
`TASK024_BLOCKED_RESULT_FRAGMENT` JSON above.

### 23.4 Vector identity replay ledger

| VECTOR_ID | UPSTREAM_FIXTURE_COMPLETE | TASK021_IDENTITY_REPLAY | TASK024_IDENTITY_REPLAY | INTENTIONAL_MISMATCH_PRESENT | INTENTIONAL_MISMATCH_EXACT | EARLIEST_EXPECTED_FAILURE_STAGE | ACCIDENTAL_EARLIER_FAILURE_PRESENT | VECTOR_IDENTITY_REPLAY_STATUS |
|---|---|---|---|---|---|---|---|---|
| V1 | true | PASS | PASS | false | NOT_APPLICABLE | NOT_REACHED | false | PASS |
| V2 | true | PASS | PASS | false | NOT_APPLICABLE | NOT_REACHED | false | PASS |
| V3 | true | PASS | PASS | false | NOT_APPLICABLE | NOT_REACHED | false | PASS |
| V4 | true | PASS | PASS | false | NOT_APPLICABLE | NOT_REACHED | false | PASS |
| V5 | true | PASS | PASS | false | NOT_APPLICABLE | 6 | false | PASS |
| V6 | true | PASS | PASS | false | NOT_APPLICABLE | 8 | false | PASS |
| V7 | true | PASS | PASS | false | NOT_APPLICABLE | 8 | false | PASS |
| V8 | true | FAIL | NOT_REACHED | false | NOT_APPLICABLE | 2 | false | PASS |
| V9 | true | PASS | PASS | false | NOT_APPLICABLE | 5 | false | PASS |
| V10 | true | PASS | PASS | true | true | 4 | false | PASS |
| V11 | true | PASS | PASS | false | NOT_APPLICABLE | 4 | false | PASS |
| V12 | true | PASS | PASS | false | NOT_APPLICABLE | 4 | false | PASS |
| V13 | true | PASS | PASS | false | NOT_APPLICABLE | 9 | false | PASS |
| V14 | true | PASS | NOT_REACHED | true | true | 7 | false | PASS |

```text
EXTERNAL_ORACLE_SOURCE_INDEPENDENT=true
EXPECTED_REPOSITORY_OUTPUT_USED_AS_AUTHORITY=false
FIXTURE_USED_AS_ENGINEERING_AUTHORITY=false
NPTEL_EXACT_ORACLE_INCLUDED=false
AUTHORITATIVE_VECTOR_PLACEHOLDER_COUNT=0
THIRD_CORRECTION_READY_FOR_REREVIEW=true
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

The prior design-contract review reported `21/35` PASS, but a literal D01–D35
table recount yields `20/35` PASS and `15/35` CHANGES_REQUIRED. F-008 is a MAJOR
finding against D15 applicability enforcement; D15 must not inherit a prior PASS
token. The next rereview must recount D01–D35 from scratch:

```text
NEXT_REREVIEW_RECOUNTS_D01_D35_FROM_SCRATCH=true
PRIOR_REVIEW_ACCOUNTING_INCONSISTENCY_NOTED=true
```

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
