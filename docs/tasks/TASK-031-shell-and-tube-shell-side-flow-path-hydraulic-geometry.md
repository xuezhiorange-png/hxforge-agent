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
DESIGN_DOCUMENT_STATUS=PROPOSED
PRIOR_REVIEW_REPORTED_PASS_COUNT=21/35
PRIOR_REVIEW_LITERAL_TABLE_RECOUNT=20/35
NEXT_REREVIEW_RECOUNTS_D01_D35_FROM_SCRATCH=true
PRIOR_REVIEW_ACCOUNTING_INCONSISTENCY_NOTED=true
CORRECTION_PARENT_SHA=45ef6dfe4674ddef497584522167182c6559e1e2
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
| `engineering_authority` | yes | `dict` | authority request binding | §9.4 validator | §20.2 authority request projection |
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

| Code | field_path | message_key | eligibility predicate | prerequisite stage | VALID emission | BLOCKED emission | evidence source |
|---|---|---|---|---:|---|---|---|
| `SSHG_CENTRAL_CROSSFLOW_SCREENING_GEOMETRY_ONLY` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | frozen profile §3 |
| `SSHG_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | §8 |
| `SSHG_MINIMUM_AREA_SELECTION_DEFERRED` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | §3.2 |
| `SSHG_WINDOW_INLET_OUTLET_FLOW_AREAS_DEFERRED` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | §3.2 |
| `SSHG_FLOW_STATE_THERMAL_PRESSURE_DROP_DEFERRED` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | §3.3 |
| `SSHG_NO_FULL_EXCHANGER_RATING_CLAIM` | `null` | frozen key | always eligible after Stage 6 | 6 | always emit | emit only if Stage 6 completed before failure | §2 |
| `SSHG_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY` | `null` | frozen key | always eligible after Stage 7 | 7 | always emit | emit only if Stage 7 completed before failure | §4, §9 |

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

Ordered top-level tuple:

1. `schema_version` — exact string
2. `tube_layout` — TASK-021 `layout_hash_payload` upstream projection
3. `baffle_geometry_result` — TASK-024 request/geometry identity projection sufficient to bind consumed geometry facts
4. `engineering_authority` — authority request binding projection
5. `evidence_refs` — sorted unique string tuple

Exclusions: no engineering output values, no `geometry_hash`, no `geometry_id`,
no runtime timestamp, no ambient git state.

```text
request_hash = sha256_hex(canonical_json_bytes(request_canonical_projection))
```

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

Design-time vectors only. Expected implementation output must never be used as
formula authority. V1 and V2 use independent arithmetic from the frozen π / √3
Decimal constants and §11.8 singular runtime sequences.

```text
F009_CORRECTION_APPLIED=true
ENGINEERING_VECTORS_COMPLETE=true
```

### 23.1 Reference scalar oracle (independent SI)

```text
Ds=0.25 m
B=0.125 m
Pt=0.025 m
do=0.019 m
Ct=0.006 m

As_raw=0.00750 m^2
As_public=0.007500000000000000000000 m^2   # AREA quantum 1e-24

De_square_raw≈0.022882879761025088360232569308556411061699906773805 m
De_square_public=0.022882879761 m            # DIAMETER quantum 1e-12

De_triangular_raw≈0.017271637856696845362587269625853252723512268445175 m
De_triangular_public=0.017271637857 m        # DIAMETER quantum 1e-12
```

### 23.2 Vector definitions

Each vector specifies: `VECTOR_ID`, purpose, exact raw/normalized inputs,
TASK-021 identity/binding setup, TASK-024 identity/binding setup, pattern
family, baffle count, spacing sequence, `Ds`, `Pt`, `do`, engineering authority
identity/profile, expected status, expected branch, expected public warnings,
expected blocker(s), expected raw engineering values, expected quantized values,
and oracle derivation.

**V1 — valid SQUARE**

- purpose: baseline valid SQUARE central-crossflow screening
- inputs: reference scalar oracle with `pattern_family=SQUARE`, `N=2`, uniform
  central spacing `B=0.125 m`, inlet/outlet equal to central for simplicity
- expected status: `VALID`
- expected branch: Formula B square
- expected warnings: all 7 baseline warnings
- expected raw: `As_raw=0.00750`, `De_square_raw` per §23.1
- expected public: `0.007500000000000000000000`, `0.022882879761`
- oracle: independent Decimal evaluation per §11.8

**V2 — valid TRIANGULAR**

- same as V1 except `pattern_family=TRIANGULAR`
- expected branch: Formula B triangular
- expected raw: `As_raw=0.00750`, `De_triangular_raw` per §23.1
- expected public: `0.007500000000000000000000`, `0.017271637857`
- oracle: independent Decimal evaluation per §11.8; do not use prior review typo
  `0.017271637856696855`

**V3 — minimum topology N=2**

- exact `N=2`, `len(S)=3`, one central inter-baffle value
- expected status: `VALID`

**V4 — inlet/outlet differ, central uniform**

- `S[0] != S[1] == S[2] != S[3]` with uniform central members
- expected status: `VALID`

**V5 — nonuniform central spacing**

- two or more unequal members in `S[1:N]`
- expected status: `BLOCKED`
- expected blocker: `SSHG_CENTRAL_INTER_BAFFLE_SPACING_NONUNIFORM`

**V6 — pitch equals tube OD**

- mutate `pitch_m == tube_outside_diameter_m` from valid V1 base
- expected status: `BLOCKED`
- expected blocker: `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD`

**V7 — pitch less than tube OD**

- mutate `pitch_m < tube_outside_diameter_m` from valid V1 base
- expected status: `BLOCKED`
- expected blocker: `SSHG_PITCH_NOT_GREATER_THAN_TUBE_OD`

**V8 — unsupported pattern token**

- mutate `pattern_family` to unsupported token from valid V1 base
- expected status: `BLOCKED`
- expected blocker: `SSHG_PATTERN_FAMILY_UNSUPPORTED`

**V9 — TASK-021/TASK-024 tube OD mismatch**

- single-field mutation: `task024_result.geometry.tube_outer_diameter_m` !=
  `task021_layout.tube_geometry.outer_diameter_m`
- expected status: `BLOCKED`
- expected blocker: `SSHG_TASK021_TASK024_TUBE_OD_MISMATCH`

**V10 — upstream identity mismatch**

- single-field mutation to `layout_hash`, `geometry_hash`, or transitive binding
  id/hash from valid V1 base
- expected status: `BLOCKED`
- expected blocker: `SSHG_TASK021_LAYOUT_IDENTITY_MISMATCH` or
  `SSHG_TASK024_IDENTITY_MISMATCH` or upstream binding mismatch code as applicable

**V11 — TASK-024 status BLOCKED**

- `task024_result.status=BLOCKED`, `geometry=null`
- expected status: `BLOCKED`
- expected blocker: `SSHG_TASK024_RESULT_HAS_BLOCKERS` or `SSHG_TASK024_GEOMETRY_MISSING`

**V12 — VALID wrapper, geometry missing**

- `task024_result.status=VALID`, `geometry=null`
- expected status: `BLOCKED`
- expected blocker: `SSHG_TASK024_GEOMETRY_MISSING`

**V13 — quantization collapse**

- construct exact positive raw quantity below half public quantum so quantized
  public value becomes zero
- expected status: `BLOCKED`
- expected blocker: `SSHG_PUBLIC_AREA_QUANTIZATION_COLLISION` or
  `SSHG_PUBLIC_DIAMETER_QUANTIZATION_COLLISION`

**V14 — engineering authority identity mismatch**

- single-field mutation to `engineering_authority.authority_hash` or
  `authority_profile_id` from valid V1 base
- expected status: `BLOCKED`
- expected blocker: `SSHG_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH`

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
