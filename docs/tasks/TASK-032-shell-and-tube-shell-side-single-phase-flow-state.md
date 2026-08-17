# TASK-032 — Shell-and-Tube Shell-Side Single-Phase Flow State

> Binding design contract for the sixth M3 shell-and-tube capability.
>
> TASK-032 consumes one complete accepted TASK-031 shell-side hydraulic
> geometry result, one caller-supplied `PropertySnapshot`, and one
> caller-supplied `ShellSideMassFlowAuthority`, and produces deterministic
> shell-side single-phase Newtonian bulk flow-state screening for exactly:
>
> `SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1`
>
> TASK-032 v1 computes only:
>
> - `shell_side_mass_flow_rate_kg_s` (preserved from mass-flow authority)
> - `shell_side_mass_velocity_kg_m2_s`
> - `shell_side_bulk_velocity_m_s`
> - `shell_side_reynolds_number`
> - `shell_side_prandtl_number`
>
> plus flow-model identity, phase-region identity, rheology identity,
> upstream identity bindings, engineering authority identity, warnings,
> blockers, deferred capabilities, provenance, and deterministic result
> identity.
>
> TASK-032 v1 does not classify flow regime, does not calculate heat-transfer
> coefficients, Nusselt number, friction factor, pressure drop, Bell–Delaware
> corrections, overall U, UA, LMTD, duty, outlet temperatures, two-phase
> behavior, non-Newtonian rheology, compressible path integration, property
> path integration, vibration, mechanical adequacy, materials, mass, cost,
> optimization, API, persistence, CLI, reports, or engineering Goldens.
> TASK-032 v1 does not implement TASK-033 or TASK-034 physics.

## 1. Authority, allocation, baseline, and status

| Field | Binding value |
|---|---|
| Repository | `xuezhiorange-png/hxforge-agent` |
| Allocation authority | Issue #180 — TASK-032 allocation |
| Source-definition authority | Issue #185 governance comment chain |
| Design independent review R1 comment | `5317687475` |
| Design correction R1 authorization comment | `5317692890` |
| Source-definition R1 proposal comment | `5316626425` |
| Engineering source/formula authority freeze comment | `5317111718` |
| Deterministic/schema freeze comment | `5317255912` |
| Complete source-definition freeze comment | `5317260370` |
| Design authoring authorization comment | `5317271091` |
| Authoring base | `main@02875eb4c6fcf5a8e7cb452f0a846f92aca946a2` |
| Design branch | `docs/task-032-shell-side-single-phase-flow-state-design` |
| Design file | `docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md` |
| Frozen allocation | `TASK-032 = Shell-and-Tube Shell-Side Single-Phase Flow-State Foundation` |
| First-slice profile | `SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1` |
| Public profile ID | `hxforge.shell_tube.shell_side_flow_state.v1` |
| Design status | `PROPOSED` |
| Source definition frozen | `true` |
| Design frozen | `false` |
| Implementation status | `NOT AUTHORIZED` |
| Pull request status | `NOT AUTHORIZED` |
| TASK-033 authorization | `NOT AUTHORIZED` |
| TASK-034 authorization | `NOT AUTHORIZED` |
| Issue close | `NOT AUTHORIZED` |

```text
TASK032_PREREQUISITE_A=SATISFIED_TASK031_DESIGN_AND_SOURCE_FREEZE
TASK032_PREREQUISITE_B=SATISFIED_GOVERNANCE_SOURCE_DEFINITION_FREEZE
TASK032_PRE_DESIGN_PREREQUISITES_SATISFIED=true
```
```text
DESIGN_DOCUMENT_STATUS=PROPOSED
SOURCE_DEFINITION_FROZEN=true
DESIGN_FROZEN=false
IMPLEMENTATION_AUTHORIZED=false
PULL_REQUEST_AUTHORIZED=false
TASK033_AUTHORIZED=false
TASK034_AUTHORIZED=false
DESIGN_AUTHORING_PUSH_AUTHORIZED_BY_5317271091=true
ORIGINAL_DESIGN_AUTHORING_PUSH_COMPLETED=true
DESIGN_CORRECTION_R1_PUSH_AUTHORIZED_BY_5317692890=true
FURTHER_PUSH_AUTHORIZED=false
```

This design authoring gate permits one branch and this one repository design
file. Authoring this document does **not** freeze or approve the design. A
separate review gate is required.
```text
DESIGN_MAY_SELECT_ENGINEERING_FORMULA=false
DESIGN_MAY_SUBSTITUTE_ENGINEERING_FORMULA=false
DESIGN_MAY_FALLBACK_ENGINEERING_FORMULA=false
```

Engineering formulas are consumed exactly from Issue #185 freeze comments
`5317111718`, `5317255912`, and `5317260370`. No design-time formula
selection, substitution, or fallback is permitted.

Governance comment chain consumed by this contract:

```text
5316626425 → 5316723014 → 5316783478 → 5317094538 → 5317111718 →
5317167637 → 5317214443 → 5317232373 → 5317243144 → 5317255912 →
5317260370 → 5317271091
```

## 2. Exact allocation and problem statement

TASK-032 owns the deterministic shell-side single-phase bulk flow-state
boundary between accepted TASK-031 screening hydraulic geometry and later
shell-side thermal or hydraulic rating work (TASK-033, TASK-034, and beyond).

TASK-031 establishes immutable central crossflow screening hydraulic
geometry: `central_crossflow_flow_area_m2` and
`shell_side_equivalent_hydraulic_diameter_m`. TASK-026 establishes the
`PropertySnapshot` reuse contract. TASK-032 must not re-own, recompute, or
reclassify any TASK-031 geometry or TASK-026 property evaluation.

TASK-032 therefore must:

1. validate and replay complete TASK-031 accepted public geometry values;
2. validate and replay `PropertySnapshot` hash without property reevaluation;
3. validate and replay `ShellSideMassFlowAuthority` hash and same-case bindings;
4. verify TASK-031 / property / mass-flow cross-binding contracts;
5. apply frozen engineering formulas F01–F04 from comment `5317260370`;
6. emit immutable flow-state quantities, hashes, blockers, warnings, deferred
   capabilities, and provenance;
7. fail closed with no partial flow-state result.

TASK-032 establishes screening bulk flow-state identity only. It does not
establish thermal, hydraulic-rating, mechanical, manufacturing, procurement,
inspection, certification, or legal-compliance adequacy.

## 3. Scope and non-scope

### 3.1 Frozen v1 first-slice scope
```text
TASK032_FIRST_SLICE_PROFILE_ID=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1
TASK032_FIRST_SLICE_FLOW_MODEL=SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING
FIRST_SLICE_PHASE_REGIONS=(SINGLE_PHASE_LIQUID,SINGLE_PHASE_GAS)
FIRST_SLICE_RHEOLOGY_MODEL=NEWTONIAN
FIRST_SLICE_FLOW_REGIME_CLASSIFICATION=DEFERRED

IN_SCOPE_ENGINEERING_QUANTITIES:
  shell_side_mass_flow_rate_kg_s
  shell_side_mass_velocity_kg_m2_s
  shell_side_bulk_velocity_m_s
  shell_side_reynolds_number
  shell_side_prandtl_number

IN_SCOPE_IDENTITY:
  shell_side_case_id
  shell_side_stream_id
  shell_side_fluid_id
  flow_model
  phase_region
  rheology_model
  upstream TASK020/TASK031 transitive identity bindings
  property_snapshot_hash
  mass_flow_authority_hash
  engineering authority identity
```

### 3.2 Explicitly deferred quantities and capabilities

Flow regime classification is deferred. No `flow_regime` field exists on the
success result. Deferral is signaled by warning
`SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED` and deferred capability token
`FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE`.

See §18 for the complete closed deferred-capability registry (17 tokens).

### 3.3 Explicitly prohibited non-scope
```text
FLOW_REGIME_CLASSIFICATION
NON_NEWTONIAN_RHEOLOGY
COMPRESSIBLE_PATH_INTEGRATION
PROPERTY_PATH_INTEGRATION
HEAT_TRANSFER_COEFFICIENT
SHELL_SIDE_NUSSELT_NUMBER
FRICTION_FACTOR
PRESSURE_DROP
BELL_DELAWARE
LEAKAGE_CORRECTIONS
BYPASS_CORRECTIONS
OVERALL_U
UA
LMTD
HEAT_DUTY
OUTLET_TEMPERATURES
FULL_EXCHANGER_RATING
TWO_PHASE
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
TASK033_PHYSICS
TASK034_PHYSICS
TASK033_IMPLEMENTATION
TASK034_IMPLEMENTATION
```

TASK-032 v1 must not import, call, or depend on any TASK-033 or TASK-034
runtime module, formula, correlation, or rating physics. Architecture tests
(`T032-ARC-001`) enforce this prohibition at implementation time.
```text
TASK033_AUTHORIZED=false
TASK034_AUTHORIZED=false
```

## 4. Frozen engineering formulas

Engineering authority is frozen by Issue #185 comments `5317111718` and
`5317260370`. The design reproduces these formulas without modification.

### 4.1 Formula F01 — shell-side mass velocity

```text
FORMULA_ID=TASK032_MASS_VELOCITY_KERN_SCREENING_INTCHOPN_EQ57_V1
PUBLIC_ENGINEERING_QUANTITY=shell_side_mass_velocity_kg_m2_s
shell_side_mass_velocity_kg_m2_s = G_s = mass_flow_rate_kg_s / A_s
PRIMARY_SOURCE=SRC-INTECHOPEN-100450-KHARAJI-2021
EXACT_SOURCE_LOCATION=§4.4 "Shell diameter", Eq. (57)
```

### 4.2 Formula F02 — shell-side Reynolds number

```text
FORMULA_ID=TASK032_REYNOLDS_KERN_SCREENING_INTCHOPN_EQ54_V1
PUBLIC_ENGINEERING_QUANTITY=shell_side_reynolds_number
shell_side_reynolds_number = Re_s = G_s * D_e / mu_s
PRIMARY_SOURCE=SRC-INTECHOPEN-100450-KHARAJI-2021
EXACT_SOURCE_LOCATION=§4.4 "Shell diameter", Eq. (54)
```

### 4.3 Formula F03 — shell-side bulk velocity

```text
FORMULA_ID=TASK032_BULK_VELOCITY_CONTINUITY_NASA_GRC_V1
PUBLIC_ENGINEERING_QUANTITY=shell_side_bulk_velocity_m_s
shell_side_bulk_velocity_m_s = V_s = mass_flow_rate_kg_s / (rho_s * A_s) = G_s / rho_s
PRIMARY_SOURCE=SRC-NASA-GRC-MASS-FLOW-RATE-EQUATIONS
EXACT_SOURCE_LOCATION=continuity relation
```

### 4.4 Formula F04 — shell-side Prandtl number

```text
FORMULA_ID=TASK032_PRANDTL_DIMENSIONLESS_INTCHOPN_EQ35_V1
PUBLIC_ENGINEERING_QUANTITY=shell_side_prandtl_number
shell_side_prandtl_number = Pr_s = mu_s * Cp_s / k_s
PRIMARY_SOURCE=SRC-INTECHOPEN-100450-KHARAJI-2021
EXACT_SOURCE_LOCATION=§4.3 "Tube-side heat transfer coefficient", Eq. (35)
```

### 4.5 Raw calculation graph
```text
G_raw  = mass_flow_rate_kg_s / A_s
V_raw  = G_raw / density_kg_m3
Re_raw = (G_raw * D_e) / dynamic_viscosity_pa_s
Pr_raw = (dynamic_viscosity_pa_s * specific_heat_capacity_j_kg_k) / thermal_conductivity_w_m_k

A_s = Decimal(A_s_text) from TASK-031 central_crossflow_flow_area_m2 canonical string
D_e = Decimal(D_e_text) from TASK-031 shell_side_equivalent_hydraulic_diameter_m canonical string
```

Binary float conversion of `A_s_text` or `D_e_text` is forbidden.

### 4.6 Source ledger

| Source ID | Role | Citation |
|---|---|---|
| `SRC-INTECHOPEN-100450-KHARAJI-2021` | Primary formula authority (F01, F02, F04) | DOI `10.5772/intechopen.100450`; CC BY 3.0 |
| `SRC-NASA-GRC-MASS-FLOW-RATE-EQUATIONS` | Continuity relation for F03 | Public official reference; citation only |
| `SRC-IJHMT-NISHIMURA-ITOH-MIYASHITA-1993` | Flow-regime deferral corroboration only | DOI `10.1016/0017-9310(93)80031-O` |
| `SRC-CES-MANGADODDY-PRAKASH-CHHABRA-ESWARAN-2004` | Non-Newtonian rheology corroboration only | DOI `10.1016/j.ces.2004.01.054` |

## 5. Direct upstream contract
```text
TASK032_DIRECT_UPSTREAM=TASK031
TASK026_IS_TASK032_DIRECT_UPSTREAM=false
TASK026_PROPERTY_SNAPSHOT_VALUE_OBJECT_REUSED=true
TASK020_DIRECT_INPUT=false
TASK020_TRANSITIVE_IDENTITY_REQUIRED=true
PROPERTY_REEVALUATION_FORBIDDEN=true
```

TASK-026 is not a direct upstream Task. TASK-032 reuses the frozen
`PropertySnapshot` value object from
`hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot.PropertySnapshot`
without requiring TASK-026 success result or engineering output.

### 5.1 TASK-031 accepted input

The public raw request carries a complete accepted TASK-031 result binding
via `task031_result`. TASK-032 consumes the TASK-031 geometry identity and
the two hydraulic quantities required for formula evaluation.
```text
task031_result is a complete accepted TASK-031 public result binding
task031_result carries geometry with geometry_id and geometry_hash
task031_result.blockers == () on accepted path
task031_result.geometry.central_crossflow_flow_area_m2 present as canonical decimal string
task031_result.geometry.shell_side_equivalent_hydraulic_diameter_m present as canonical decimal string
all required TASK031 identity replay succeeds
```

### 5.2 TASK-031 binding subrecord (12 fields)
```text
TASK031_BINDING_FIELDS=(
  status,
  geometry_schema_version,
  geometry_id,
  geometry_hash,
  request_hash,
  task020_configuration_id,
  task020_configuration_hash,
  central_crossflow_flow_area_m2,
  shell_side_equivalent_hydraulic_diameter_m,
  engineering_authority_id,
  engineering_authority_hash,
  flow_region_identity
)
```

Supersession: replay `geometry_hash` and `geometry_id`; do not invent TASK-031
`result_hash` or `result_id`.

### 5.3 PropertySnapshot accepted input
```text
PROPERTY_SNAPSHOT_TYPE=hexagent.exchangers.shell_tube.tube_side_thermal.property_snapshot.PropertySnapshot
PROPERTY_SNAPSHOT_NAMESPACE=task026.property-snapshot.v1
PROPERTY_SNAPSHOT_HASH_PROJECTION_FIELD_COUNT=9
```
```text
density_kg_m3
dynamic_viscosity_pa_s
thermal_conductivity_w_m_k
specific_heat_capacity_j_kg_k
bulk_temperature_k
bulk_pressure_pa
phase_region
property_source_id
property_source_version
property_snapshot_hash
```
```text
recompute_property_snapshot_hash(property_snapshot)
== property_snapshot.property_snapshot_hash
== task032_request.property_snapshot_hash
```

### 5.4 Forbidden upstream behavior
```text
TASK031_GEOMETRY_RECOMPUTATION
TASK031_FORMULA_REEVALUATION
PROPERTY_PROVIDER_CALL
PROPERTY_PATH_INTEGRATION
PROPERTY_TEMPERATURE_PRESSURE_ITERATION
TOLERANCE_HASH_RECONCILIATION
CLOSEST_MATCH_ALIAS_INFERENCE
PROVENANCE_REPAIR
RHEOLOGY_INFERENCE_FROM_FLUID_NAME
RHEOLOGY_INFERENCE_FROM_VISCOSITY_SCALAR
```

## 6. ShellSideMassFlowAuthority contract
```text
SHELL_SIDE_MASS_FLOW_AUTHORITY_SCHEMA_VERSION=task032.shell-side-mass-flow-authority.v1
SHELL_SIDE_MASS_FLOW_AUTHORITY_NAMESPACE=task032.shell-side-mass-flow-authority.v1
SHELL_SIDE_MASS_FLOW_AUTHORITY_PROFILE_ID=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1
SHELL_SIDE_MASS_FLOW_AUTHORITY_HASH_SELF_EXCLUSIONS=(authority_hash,)
SHELL_SIDE_MASS_FLOW_AUTHORITY_FIELD_COUNT=18
```
```text
SHELL_SIDE_MASS_FLOW_AUTHORITY_FIELDS=(
  schema_version,
  authority_profile_id,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  rheology_model,
  task020_configuration_id,
  task020_configuration_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  property_state_role,
  mass_flow_rate_kg_s,
  mass_flow_sign_convention,
  authority_source_id,
  authority_source_version,
  evidence_refs,
  authority_hash
)
SHELL_SIDE_MASS_FLOW_AUTHORITY_KIND_TAGS=(STRING,STRING,STRING,STRING,STRING,ENUM,STRING,STRING,STRING,STRING,STRING,ENUM,DECIMAL,ENUM,STRING,STRING,TUPLE)
RHEOLOGY_MODEL=NEWTONIAN
PROPERTY_STATE_ROLE=BULK_SHELL_SIDE_STATE
MASS_FLOW_SIGN_CONVENTION=POSITIVE_ALONG_DECLARED_SHELL_SIDE_FLOW_DIRECTION
```

`mass_flow_rate_kg_s` is preserved from caller authority verbatim on success;
TASK-032 does not re-quantize it.

## 7. Applicability domain
```text
TASK032_APPLICABILITY_DOMAIN=
INTERSECTION(
  TASK031_ACCEPTED_DOMAIN,
  PROPERTY_SNAPSHOT_ACCEPTED_DOMAIN,
  MASS_FLOW_AUTHORITY_ACCEPTED_DOMAIN,
  TASK032_ADMITTED_ENGINEERING_FORMULA_DOMAIN
)

TASK032_ADMITTED_ENGINEERING_FORMULA_DOMAIN:
  flow_model=SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING
  phase_region in {SINGLE_PHASE_LIQUID, SINGLE_PHASE_GAS}
  rheology_model=NEWTONIAN
  property_state_role=BULK_SHELL_SIDE_STATE
  mass_flow_rate_kg_s finite and strictly positive
  A_s finite and strictly positive from TASK-031
  D_e finite and strictly positive from TASK-031
  rho_s, mu_s, Cp_s, k_s finite and strictly positive from PropertySnapshot
```

### 7.1 Applicability enforcement table

| Predicate | Production binding | Accepted value / domain | Blocker code | Stage |
|---|---|---|---|---|
| phase region | `property_snapshot.phase_region` | `SINGLE_PHASE_LIQUID` or `SINGLE_PHASE_GAS` | `SSFS_PHASE_UNSUPPORTED` | S06 |
| rheology model | `mass_flow_authority.rheology_model` | `NEWTONIAN` | `SSFS_RHEOLOGY_MODEL_UNSUPPORTED` | S06 |
| property state role | `mass_flow_authority.property_state_role` | `BULK_SHELL_SIDE_STATE` | `SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED` | S06 |
| flow model | frozen first-slice identity | `SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING` | `SSFS_FLOW_MODEL_UNSUPPORTED` | S06 |
| mass flow positivity | `mass_flow_authority.mass_flow_rate_kg_s` | finite `> 0` | `SSFS_MASS_FLOW_NON_POSITIVE` | S04 |
| formula domain residual | engineering inputs | finite positive denominators | `SSFS_FORMULA_DOMAIN_VIOLATION` | S06 |
| formula calculation | raw engineering outputs | finite positive raw results | `SSFS_FORMULA_CALCULATION_FAILED` | S08 |

## 8. Phase, rheology, and flow-model semantics
```text
SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY=true
PROPERTY_PATH_INTEGRATION_EXCLUDED=true
COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED=true
FLOW_REGIME_CLASSIFICATION=DEFERRED_NO_UNIVERSAL_THRESHOLD_AUTHORITY_ADMITTED
NON_NEWTONIAN_RHEOLOGY=DEFERRED
```

Liquid and gas single-phase regions are admitted under the same algebraic
screening flow model `SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING`.

## 9. Engineering authority identity
```text
ENGINEERING_AUTHORITY_SCHEMA_VERSION=task032.engineering-authority.v1
ENGINEERING_AUTHORITY_HASH_NAMESPACE=task032.engineering-authority.v1
ENGINEERING_AUTHORITY_PROFILE_ID=TASK032_SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1_FORMULA_AUTHORITY
ENGINEERING_AUTHORITY_FIELD_COUNT=14
```
```text
ENGINEERING_AUTHORITY_FIELDS=(
  schema_version,
  authority_profile_id,
  first_slice_profile_id,
  flow_model,
  formula_ids,
  source_ids,
  phase_regions,
  rheology_model,
  flow_regime_classification,
  engineering_source_formula_freeze_comment_id,
  source_definition_issue,
  evidence_refs,
  authority_hash,
  authority_id
)
authority_id = "urn:hxforge:task032:engineering-authority:v1:" + authority_hash
```

Mismatch blocks with `SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH` at stage S07.

## 10. Runtime source behavior

The deterministic core must not perform network lookup, read source PDFs,
read GitHub Issues, fetch DOI content, scan rule packs, choose engineering
sources, choose alternate formulas, or invoke TASK-033/TASK-034 physics.

## 11. Numeric, Decimal, and quantization discipline

### 11.1 Forbidden numeric types

Binary floating-point is forbidden in all flow-state calculations, boundary
predicates, formula evaluation, canonical projections, and hash inputs.

### 11.2 Frozen Decimal context
```text
DECIMAL_PRECISION=50
ROUNDING_MODE=ROUND_HALF_EVEN
BINARY_FLOAT_ENGINEERING=false
FLOAT_TO_DECIMAL_COERCION=false
PUBLIC_QUANTIZATION_LAST=true
NEGATIVE_ZERO_NORMALIZATION=true
TRAILING_ZERO_POLICY=PRESERVE_QUANTUM_SCALE
ENGINEERING_INTERMEDIATE_PUBLIC_QUANTIZATION=false
```

### 11.3 Output quanta
```text
MASS_VELOCITY_OUTPUT_QUANTUM=Decimal("0.0000001")
BULK_VELOCITY_OUTPUT_QUANTUM=Decimal("0.0000001")
REYNOLDS_OUTPUT_QUANTUM=Decimal("0.0001")
PRANDTL_OUTPUT_QUANTUM=Decimal("0.0001")
```

### 11.4 Python 3.11 / 3.12 byte identity

All canonical bytes, hashes, UUID derivations, blocker ordering, warning
ordering, and public quantized values must be byte-identical on Python 3.11
and Python 3.12 (`T032-XPY-001`).

## 12. Closed schema versions and identities
```text
REQUEST_TYPE=ShellSideFlowStateRequest
REQUEST_SCHEMA_VERSION=task032.shell-side-flow-state-request.v1
REQUEST_FIELD_COUNT=7
PROFILE_ID=hxforge.shell_tube.shell_side_flow_state.v1

SUCCESS_RESULT_TYPE=ShellSideFlowState
SUCCESS_RESULT_SCHEMA_VERSION=task032.shell-side-flow-state.v1
SUCCESS_RESULT_FIELD_COUNT=29

TYPED_BLOCKED_RESULT_TYPE=ShellSideFlowStateBlockedResult
TYPED_BLOCKED_RESULT_SCHEMA_VERSION=task032.shell-side-flow-state-blocked.v1
TYPED_BLOCKED_RESULT_FIELD_COUNT=15
TYPED_BLOCKED_FAILURE_STAGE_DOMAIN=(S02,S03,S04,S05,S06,S07,S08,S09,S10,S11,S12)
PARTIAL_FLOW_STATE=false

RAW_BOUNDARY_BLOCKED_RESULT_TYPE=ShellSideFlowStateRawBoundaryBlockedResult
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION=task032.shell-side-flow-state-raw-boundary-blocked.v1
RAW_BOUNDARY_BLOCKED_RESULT_FIELD_COUNT=8
RAW_BOUNDARY_PROFILE_ID=hxforge.shell_tube.shell_side_flow_state.v1
RAW_BOUNDARY_FAILURE_STAGE_DOMAIN=(S00,S01)

IMPLEMENTATION_SOFTWARE_VERSION=task032.shell-side-flow-state-impl-v1
DESIGN_CONTRACT_PATH=docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md
```

## 13. Public raw request schema
```text
PUBLIC_CALCULATION_OPERATION_COUNT=1
PUBLIC_CALCULATION_OPERATION=validate_request(raw_request)

REQUEST_TYPE=ShellSideFlowStateRequest
REQUEST_SCHEMA_VERSION=task032.shell-side-flow-state-request.v1
PROFILE_ID=hxforge.shell_tube.shell_side_flow_state.v1

RAW_REQUEST_CONTAINER_TYPE=EXACT_BUILTIN_DICT
CUSTOM_MAPPING_ACCEPTED=false
UNKNOWN_FIELDS_BLOCKED=true
ALTERNATIVE_REQUEST_SHAPES=false
REQUEST_SCHEMA_SINGULAR=true

RAW_REQUEST_FIELDS=(
  schema_version,
  profile_id,
  task031_result,
  property_snapshot_hash,
  property_snapshot,
  mass_flow_authority,
  evidence_refs
)
RAW_REQUEST_FIELD_COUNT=7
```

### 13.1 Top-level field table (count 7)

| # | Field | Required | Raw type | Normalized type |
|---:|---|---|---|---|
| 1 | `schema_version` | yes | `str` | str |
| 2 | `profile_id` | yes | `str` | str |
| 3 | `task031_result` | yes | `dict` | TASK-031 binding |
| 4 | `property_snapshot_hash` | yes | `str` | str |
| 5 | `property_snapshot` | yes | `dict` | PropertySnapshot |
| 6 | `mass_flow_authority` | yes | `dict` | ShellSideMassFlowAuthority |
| 7 | `evidence_refs` | yes | `list` | tuple[str, ...] |
```text
REQUEST_FIELDS=(
  schema_version,
  profile_id,
  task031_result,
  property_snapshot_hash,
  property_snapshot,
  mass_flow_authority,
  evidence_refs
)
REQUEST_HASH_KIND_TAGS=(STRING,STRING,RECORD,STRING,RECORD,RECORD,TUPLE)
```

### 13.2 Top-level field lexical contracts

`schema_version`:

- `raw_type=str`
- `exact_value=task032.shell-side-flow-state-request.v1`

`profile_id`:

- `raw_type=str`
- `exact_value=hxforge.shell_tube.shell_side_flow_state.v1`

`property_snapshot_hash`:

- `raw_type=str`
- `lexical_domain=LOWERCASE_64_HEX`

`evidence_refs`:

- `raw_type=EXACT_BUILTIN_LIST_OF_STRINGS`
- `empty=false`
- `duplicates=false`
- `normalized_type=tuple[str,...]`
- `canonical_order=LEXICOGRAPHIC_SORT`

Unsorted but otherwise valid raw `evidence_refs` MUST be accepted. Accepted raw
`evidence_refs` are an exact built-in list that is non-empty, duplicate-free,
and contains only non-empty strings. Normalization converts to `tuple` and
lexicographically sorts. Unsorted input alone is not a blocker.
```text
UNSORTED_BUT_VALID_RAW_EVIDENCE_REFS=ACCEPTED
UNSORTED_INPUT_ALONE_IS_NOT_A_BLOCKER=true
```

### 13.3 `task031_result` nested raw contract (count 6)
```text
TASK031_RESULT_RAW_CONTAINER_TYPE=EXACT_BUILTIN_DICT
TASK031_RESULT_RAW_FIELDS=(
  status,
  geometry,
  warnings,
  blockers,
  deferred_capabilities,
  blocked_result_hash
)
TASK031_RESULT_RAW_FIELD_COUNT=6
```

### 13.4 `task031_result.geometry` nested raw contract (count 25)
```text
TASK031_GEOMETRY_RAW_CONTAINER_TYPE=EXACT_BUILTIN_DICT_WHEN_PRESENT
TASK031_GEOMETRY_RAW_FIELDS=(
  schema_version,
  geometry_id,
  geometry_hash,
  request_hash,
  task020_configuration_id,
  task020_configuration_hash,
  task021_layout_id,
  task021_layout_hash,
  task022_geometry_id,
  task022_geometry_hash,
  task024_geometry_id,
  task024_geometry_hash,
  engineering_authority_id,
  engineering_authority_hash,
  formula_a_id,
  formula_b_id,
  pattern_family,
  flow_region_identity,
  central_inter_baffle_spacing_m,
  central_crossflow_flow_area_m2,
  shell_side_equivalent_hydraulic_diameter_m,
  warnings,
  blockers,
  deferred_capabilities,
  provenance
)
TASK031_GEOMETRY_RAW_FIELD_COUNT=25
```

### 13.5 `property_snapshot` nested raw contract (count 10)
```text
PROPERTY_SNAPSHOT_RAW_CONTAINER_TYPE=EXACT_BUILTIN_DICT
PROPERTY_SNAPSHOT_RAW_FIELDS=(
  density_kg_m3,
  dynamic_viscosity_pa_s,
  thermal_conductivity_w_m_k,
  specific_heat_capacity_j_kg_k,
  bulk_temperature_k,
  bulk_pressure_pa,
  phase_region,
  property_source_id,
  property_source_version,
  property_snapshot_hash
)
PROPERTY_SNAPSHOT_RAW_FIELD_COUNT=10
PROPERTY_SNAPSHOT_PHASE_REGION_RAW_RULE=EXACT_ADMITTED_ENUM_STRING_TOKEN
PROPERTY_SNAPSHOT_SOURCE_ID_RAW_RULE=NON_EMPTY_STRING
PROPERTY_SNAPSHOT_SOURCE_VERSION_RAW_RULE=NON_EMPTY_STRING
PROPERTY_SNAPSHOT_HASH_RAW_RULE=LOWERCASE_64_HEX
```

The six numeric `PropertySnapshot` fields must be
`CANONICAL_FINITE_BASE10_FIXED_POINT_STRING`. Forbidden: exponent notation,
leading `+`, whitespace, NaN, Infinity, `-Infinity`, binary float,
float-to-Decimal coercion.

### 13.6 `mass_flow_authority` nested raw contract (count 18)
```text
MASS_FLOW_AUTHORITY_RAW_CONTAINER_TYPE=EXACT_BUILTIN_DICT
MASS_FLOW_AUTHORITY_RAW_FIELDS=(
  schema_version,
  authority_profile_id,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  rheology_model,
  task020_configuration_id,
  task020_configuration_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  property_state_role,
  mass_flow_rate_kg_s,
  mass_flow_sign_convention,
  authority_source_id,
  authority_source_version,
  evidence_refs,
  authority_hash
)
MASS_FLOW_AUTHORITY_RAW_FIELD_COUNT=18
```

`rheology_model`:

- `EXACT_STRING_TOKEN`

`property_state_role`:

- `EXACT_STRING_TOKEN`

`mass_flow_sign_convention`:

- `EXACT_STRING_TOKEN`

`task020_configuration_hash`:

- `LOWERCASE_64_HEX`

`task031_geometry_hash`:

- `LOWERCASE_64_HEX`

`property_snapshot_hash`:

- `LOWERCASE_64_HEX`

`authority_hash`:

- `LOWERCASE_64_HEX`

`evidence_refs`:

- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_RAW_TYPE=EXACT_BUILTIN_LIST_OF_STRINGS`
- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_EMPTY=false`
- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_ENTRIES=NON_EMPTY_STRINGS`
- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_DUPLICATES=false`
- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_NORMALIZED_TYPE=tuple[str,...]`
- `MASS_FLOW_AUTHORITY_EVIDENCE_REFS_CANONICAL_ORDER=LEXICOGRAPHIC_SORT`
- `MASS_FLOW_AUTHORITY_UNSORTED_BUT_VALID_EVIDENCE_REFS=ACCEPTED`

The caller's raw `evidence_refs` list is not required to already be sorted.

`mass_flow_rate_kg_s`:

- canonical finite base-10 fixed-point string
- decoded to `Decimal`
- no exponent notation
- no leading `+`
- no whitespace
- no NaN/Infinity
- no binary float
- no float-to-Decimal coercion

### 13.7 Forbidden raw-request behavior
```text
ARBITRARY_MAPPING
CUSTOM_MAPPING
ALIASES
IMPLICIT_COERCION
REPR_BASED_UNKNOWN_OBJECT_PROJECTION
STR_BASED_UNKNOWN_OBJECT_PROJECTION
BINARY_FLOAT_INPUT
PARTIAL_TASK031_PROJECTION
TASK031_ID_ONLY_INPUT
SILENT_MISSING_FIELD_SYNTHESIS
RUNTIME_UPSTREAM_REPAIR
```

## 14. Public operation
```text
PUBLIC_CALCULATION_OPERATION_COUNT=1
```

```python
def validate_request(raw_request: Any) -> ShellSideFlowStateValidationResult:
    ...
```

## 15. Result models

### 15.1 `ShellSideFlowState` success result (count 29)
```text
SUCCESS_RESULT_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  engineering_authority_id,
  engineering_authority_hash,
  flow_model,
  phase_region,
  rheology_model,
  shell_side_mass_flow_rate_kg_s,
  shell_side_mass_velocity_kg_m2_s,
  shell_side_bulk_velocity_m_s,
  shell_side_reynolds_number,
  shell_side_prandtl_number,
  request_hash,
  result_hash,
  result_id,
  warnings,
  blockers,
  deferred_capabilities,
  provenance
)
```

No `flow_regime` field exists on success.

### 15.2 `ShellSideFlowStateBlockedResult` (count 15)
```text
TYPED_BLOCKED_RESULT_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  failure_stage,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  request_hash,
  result_hash,
  result_id,
  blockers,
  warnings,
  deferred_capabilities,
  provenance
)
PARTIAL_FLOW_STATE=false
```

Identity slots `str | None`: `KIND_STRING` when verified, `KIND_NONE` when unavailable.

### 15.3 `ShellSideFlowStateRawBoundaryBlockedResult` (count 8)
```text
RAW_BOUNDARY_BLOCKED_RESULT_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  raw_request_projection,
  blocked_result_hash,
  blockers,
  warnings,
  deferred_capabilities
)
```

No request hash is invented on raw-boundary paths.

## 16. Closed blocker taxonomy and message pipeline
```text
TASK032_BLOCKER_CODE_COUNT=33
TASK032_REACHABLE_BLOCKER_COUNT=32
TASK032_DEFENSIVE_BLOCKER_COUNT=1
TASK032_DEFENSIVE_BLOCKERS=(SSFS_PARTIAL_RESULT_FORBIDDEN,)
BLOCKER_SEVERITY=hard
BLOCKER_SORT_KEY=(stage_rank,code,field_path,message_key,payload_hash,evidence_hash)
```

Blocker entry contract (7 fields): `code, severity, stage, field_path, message_key, payload, evidence_refs`

| # | Code | Earliest stage | Meaning |
|---:|---|---|---|
| 1 | `SSFS_SCHEMA_VERSION_UNSUPPORTED` | S01 | unsupported request schema token |
| 2 | `SSFS_PROFILE_ID_UNSUPPORTED` | S01 | unsupported profile_id token |
| 3 | `SSFS_RAW_TYPE_INVALID` | S00 | raw value is not exact built-in dict/list/str |
| 4 | `SSFS_UNKNOWN_FIELD` | S01 | unknown field in closed schema |
| 5 | `SSFS_DECIMAL_LEXICAL_INVALID` | S01 | decimal lexical domain violation |
| 6 | `SSFS_EVIDENCE_REFS_INVALID` | S01 | evidence refs wrong type, empty, invalid entry, duplicates, or other invalid lexical/content |
| 7 | `SSFS_TASK031_RESULT_MISSING` | S01 | required task031_result absent |
| 8 | `SSFS_TASK031_RESULT_INVALID` | S02 | task031_result fails shape decode |
| 9 | `SSFS_TASK031_RESULT_HAS_BLOCKERS` | S02 | task031_result carries upstream blockers |
| 10 | `SSFS_TASK031_GEOMETRY_MISSING` | S02 | accepted geometry absent |
| 11 | `SSFS_TASK031_IDENTITY_MISMATCH` | S02 | TASK-031 geometry hash/id replay failure |
| 12 | `SSFS_PROPERTY_SNAPSHOT_MISSING` | S01 | required property_snapshot absent |
| 13 | `SSFS_PROPERTY_SNAPSHOT_INVALID` | S03 | property snapshot fails shape decode |
| 14 | `SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH` | S03 | property snapshot hash replay failure |
| 15 | `SSFS_MASS_FLOW_AUTHORITY_MISSING` | S01 | required mass_flow_authority absent |
| 16 | `SSFS_MASS_FLOW_AUTHORITY_INVALID` | S04 | mass-flow authority fails shape decode |
| 17 | `SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH` | S04 | mass-flow authority hash replay failure |
| 18 | `SSFS_SAME_CASE_BINDING_MISMATCH` | S05 | same-case cross-binding failure |
| 19 | `SSFS_PHASE_UNSUPPORTED` | S06 | phase region outside admitted set |
| 20 | `SSFS_RHEOLOGY_MODEL_UNSUPPORTED` | S06 | rheology model not NEWTONIAN |
| 21 | `SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED` | S06 | property state role not BULK_SHELL_SIDE_STATE |
| 22 | `SSFS_MASS_FLOW_NON_POSITIVE` | S04 | mass flow zero or negative |
| 23 | `SSFS_FLOW_MODEL_UNSUPPORTED` | S06 | flow model identity mismatch |
| 24 | `SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH` | S07 | authority hash/profile mismatch |
| 25 | `SSFS_FORMULA_DOMAIN_VIOLATION` | S06 | formula applicability/domain violation |
| 26 | `SSFS_FORMULA_CALCULATION_FAILED` | S08 | non-finite or non-positive raw engineering result |
| 27 | `SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION` | S09 | positive raw G_s quantizes to zero |
| 28 | `SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION` | S09 | positive raw V_s quantizes to zero |
| 29 | `SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION` | S09 | positive raw Re_s quantizes to zero |
| 30 | `SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION` | S09 | positive raw Pr_s quantizes to zero |
| 31 | `SSFS_CANONICALIZATION_FAILED` | S11 | canonical projection failure |
| 32 | `SSFS_RESULT_IDENTITY_FINALIZATION_FAILED` | S12 | result hash/id finalization failure |
| 33 | `SSFS_PARTIAL_RESULT_FORBIDDEN` | S10 | defensive only — partial flow state attempted |

## 17. Closed warning taxonomy
```text
TASK032_WARNING_CODE_COUNT=7
WARNING_SEVERITY=warning
WARNING_SORT_KEY=(prerequisite_stage_rank,code,field_path,message_key,evidence_hash)
```

Warning entry contract (6 fields): `code, severity, prerequisite_stage, field_path, message_key, evidence_refs`

| # | Code | Prerequisite stage | Meaning |
|---:|---|---|---|
| 1 | `SSFS_SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY` | S06 | single bulk snapshot screening only |
| 2 | `SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED` | S06 | flow regime classification deferred |
| 3 | `SSFS_NON_NEWTONIAN_DEFERRED` | S06 | non-Newtonian rheology deferred |
| 4 | `SSFS_COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED` | S06 | compressible path integration excluded |
| 5 | `SSFS_HEAT_TRANSFER_PRESSURE_DROP_DEFERRED` | S06 | heat transfer and pressure drop deferred |
| 6 | `SSFS_NO_FULL_EXCHANGER_RATING_CLAIM` | S06 | no full exchanger rating claim |
| 7 | `SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY` | S07 | formula authority screening model only |

## 18. Deferred capabilities
```text
TASK032_DEFERRED_CAPABILITY_COUNT=17
TASK032_DEFERRED_CAPABILITIES=(
  FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE,
  NON_NEWTONIAN_RHEOLOGY_NOT_COMPUTABLE,
  COMPRESSIBLE_PATH_INTEGRATION_NOT_COMPUTABLE,
  PROPERTY_PATH_INTEGRATION_NOT_COMPUTABLE,
  SHELL_SIDE_HEAT_TRANSFER_COEFFICIENT_NOT_COMPUTABLE,
  SHELL_SIDE_NUSSELT_NUMBER_NOT_COMPUTABLE,
  SHELL_SIDE_FRICTION_FACTOR_NOT_COMPUTABLE,
  SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE,
  BELL_DELAWARE_NOT_COMPUTABLE,
  LEAKAGE_CORRECTIONS_NOT_COMPUTABLE,
  BYPASS_CORRECTIONS_NOT_COMPUTABLE,
  OVERALL_U_NOT_COMPUTABLE,
  UA_NOT_COMPUTABLE,
  LMTD_NOT_COMPUTABLE,
  HEAT_DUTY_NOT_COMPUTABLE,
  OUTLET_TEMPERATURES_NOT_COMPUTABLE,
  FULL_EXCHANGER_RATING_NOT_COMPUTABLE
)
```

## 19. Validation stages and failure policy
```text
STAGE_COUNT=13
STAGES=(
  S00 raw_input_boundary,
  S01 request_schema_and_decode,
  S02 task031_result_validation_and_identity_replay,
  S03 property_snapshot_validation_and_hash_replay,
  S04 mass_flow_authority_validation_and_hash_replay,
  S05 same_case_cross_binding,
  S06 phase_rheology_and_applicability,
  S07 engineering_authority_identity_replay,
  S08 raw_engineering_calculation,
  S09 public_quantization,
  S10 warnings_blockers_finalization,
  S11 canonical_serialization,
  S12 hash_uuid_provenance_finalization
)
```

| Stage | Name | Scope |
|---|---|---|
| S00 | raw_input_boundary | top-level raw type gate |
| S01 | request_schema_and_decode | schema_version, profile_id, closed field set |
| S02 | task031_result_validation_and_identity_replay | TASK-031 acceptance and geometry replay |
| S03 | property_snapshot_validation_and_hash_replay | PropertySnapshot decode and hash replay |
| S04 | mass_flow_authority_validation_and_hash_replay | authority decode, positivity, hash replay |
| S05 | same_case_cross_binding | §21 same-case equalities |
| S06 | phase_rheology_and_applicability | §7.1 applicability table |
| S07 | engineering_authority_identity_replay | frozen authority replay |
| S08 | raw_engineering_calculation | unquantized F01–F04 evaluation |
| S09 | public_quantization | §11.3 output quanta |
| S10 | warnings_blockers_finalization | warning eligibility and defensive partial guard |
| S11 | canonical_serialization | canonical projections |
| S12 | hash_uuid_provenance_finalization | result_hash, result_id, provenance_hash |

### 19.1 Identity order (corrected R2)

1. S00/S01 decode normalized typed request
2. compute `request_hash`
3. replay TASK-031 geometry identity
4. replay PropertySnapshot hash
5. replay ShellSideMassFlowAuthority hash
6. same-case / applicability / engineering-authority validation
7. build provenance prehash / `provenance_hash`
8. compute success or typed-blocked `result_hash`
9. derive `result_id` from completed `result_hash`

At first failing stage: accumulate all complete blockers from that stage only,
sort by blocker sort key, do not execute later stages.

## 20. Canonical projections and hashes
```text
REQUEST_HASH_NAMESPACE=task032.request.v1
SUCCESS_RESULT_HASH_NAMESPACE=task032.success-result.v1
TYPED_BLOCKED_RESULT_HASH_NAMESPACE=task032.blocked-result.v1
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=task032.raw-boundary-blocked-result.v1
PROVENANCE_NAMESPACE=task032.provenance.v1
RAW_PROJECTION_NAMESPACE=task032.raw-projection.v1
BLOCKER_ENTRY_NAMESPACE=task032.blocker-entry.v1
WARNING_ENTRY_NAMESPACE=task032.warning-entry.v1
SHELL_SIDE_MASS_FLOW_AUTHORITY_NAMESPACE=task032.shell-side-mass-flow-authority.v1
ENGINEERING_AUTHORITY_HASH_NAMESPACE=task032.engineering-authority.v1
PROPERTY_SNAPSHOT_NAMESPACE=task026.property-snapshot.v1
```

### 20.1 Hash self-exclusions

| Projection | Field count in hash | Exclusions |
|---|---:|---|
| Request hash | 7 | none — all request fields included |
| Success result hash | 27 | excludes `result_hash`, `result_id` |
| Typed-blocked result hash | 13 | excludes `result_hash`, `result_id` |
| Raw-boundary blocked hash | 7 | excludes `blocked_result_hash` |
| Mass-flow authority hash | 17 | excludes `authority_hash` |
| Engineering authority hash | 12 | excludes `authority_hash`, `authority_id` |
| Provenance hash | 26 | excludes `provenance_hash` |

### 20.2 RESULT_ID derivation
```text
RESULT_ID_NAMESPACE=96ab5cf6-204d-547a-9d27-8a5eff46f997
RESULT_ID_NAME_PREFIX=task032-result-v1::
RESULT_ID_ALGORITHM=UUID5(RESULT_ID_NAMESPACE, RESULT_ID_NAME_PREFIX + result_hash)
```

## 21. Same-case binding and upstream replay helpers

### 21.1 Required equalities before engineering success
```text
mass_flow_authority.task031_geometry_id == task031_result.geometry.geometry_id
mass_flow_authority.task031_geometry_hash == task031_result.geometry.geometry_hash
mass_flow_authority.task020_configuration_id == task031_result.geometry.task020_configuration_id
mass_flow_authority.task020_configuration_hash == task031_result.geometry.task020_configuration_hash
mass_flow_authority.property_snapshot_hash == property_snapshot.property_snapshot_hash
recompute_property_snapshot_hash(property_snapshot) == property_snapshot.property_snapshot_hash
mass_flow_authority.property_state_role == BULK_SHELL_SIDE_STATE
mass_flow_authority.rheology_model == NEWTONIAN
```

### 21.2 Preserved identity slots
```text
shell_side_case_id
shell_side_stream_id
shell_side_fluid_id
rheology_model
task020_configuration_id/hash
task031_geometry_id/hash
property_snapshot_hash
mass_flow_authority_hash
TASK032 first-slice profile identity
TASK032 first-slice flow-model identity
```

Forbidden: tolerance matching, closest-match, hash reconciliation, inferred
aliases, provenance repair, rheology inference from fluid name or viscosity scalar.

### 21.3 Upstream replay helpers

| Upstream | Helper module | Replay function |
|---|---|---|
| TASK-031 geometry | `shell_side_hydraulic_geometry.canonical` | geometry hash/id replay |
| PropertySnapshot | `tube_side_thermal.property_snapshot` | `recompute_property_snapshot_hash` |
| Mass-flow authority | `shell_side_flow_state.canonical` | authority hash replay |

## 22. Provenance contract

Provenance must record task ID, design contract path, implementation version,
request/result hashes, upstream identities, formula IDs, source IDs, warnings,
and deferred capabilities.
```text
provenance.warnings == public_result.warnings
```

## 23. Engineering verification vectors
```text
TASK032_ENGINEERING_VECTOR_COUNT=12
TASK032_VECTOR_IDS=(
  V01_VALID_SINGLE_PHASE_LIQUID,
  V02_VALID_SINGLE_PHASE_GAS,
  V03_ZERO_MASS_FLOW_BLOCKED,
  V04_NEGATIVE_MASS_FLOW_BLOCKED,
  V05_PROPERTY_HASH_MISMATCH,
  V06_MASS_FLOW_AUTHORITY_HASH_MISMATCH,
  V07_TASK031_GEOMETRY_IDENTITY_MISMATCH,
  V08_SAME_CASE_BINDING_MISMATCH,
  V09_NON_NEWTONIAN_RHEOLOGY_BLOCKED,
  V10_UNSUPPORTED_FLOW_MODEL_BLOCKED,
  V11_PUBLIC_QUANTIZATION_COLLISION,
  V12_HIGH_PRECISION_OPERATION_ORDER
)
```

Each vector record fields:
```text
VECTOR_ID, BASE_FIXTURE_ID, MUTATIONS_IN_ORDER, EXPECTED_STATUS,
EXPECTED_FAILURE_STAGE, EXPECTED_BLOCKER_CODES_IN_ORDER,
EXPECTED_WARNING_CODES_IN_ORDER, EXPECTED_TASK031_GEOMETRY_ID_HASH,
EXPECTED_PROPERTY_SNAPSHOT_HASH, EXPECTED_MASS_FLOW_AUTHORITY_HASH,
EXPECTED_RAW_MASS_VELOCITY, EXPECTED_PUBLIC_MASS_VELOCITY,
EXPECTED_RAW_BULK_VELOCITY, EXPECTED_PUBLIC_BULK_VELOCITY,
EXPECTED_RAW_REYNOLDS, EXPECTED_PUBLIC_REYNOLDS,
EXPECTED_RAW_PRANDTL, EXPECTED_PUBLIC_PRANDTL, ORACLE_DERIVATION
```

Unreached stages: `NOT_REACHED`. Not applicable fields: `NOT_APPLICABLE`.

### 23.1 Vector registry summary

| Vector ID | Expected status | Expected failure stage | Primary blocker(s) |
|---|---|---|---|
| `V01_VALID_SINGLE_PHASE_LIQUID` | VALID | NOT_APPLICABLE | none |
| `V02_VALID_SINGLE_PHASE_GAS` | VALID | NOT_APPLICABLE | none |
| `V03_ZERO_MASS_FLOW_BLOCKED` | BLOCKED | S04 | SSFS_MASS_FLOW_NON_POSITIVE |
| `V04_NEGATIVE_MASS_FLOW_BLOCKED` | BLOCKED | S04 | SSFS_MASS_FLOW_NON_POSITIVE |
| `V05_PROPERTY_HASH_MISMATCH` | BLOCKED | S03 | SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH |
| `V06_MASS_FLOW_AUTHORITY_HASH_MISMATCH` | BLOCKED | S04 | SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH |
| `V07_TASK031_GEOMETRY_IDENTITY_MISMATCH` | BLOCKED | S02 | SSFS_TASK031_IDENTITY_MISMATCH |
| `V08_SAME_CASE_BINDING_MISMATCH` | BLOCKED | S05 | SSFS_SAME_CASE_BINDING_MISMATCH |
| `V09_NON_NEWTONIAN_RHEOLOGY_BLOCKED` | BLOCKED | S06 | SSFS_RHEOLOGY_MODEL_UNSUPPORTED |
| `V10_UNSUPPORTED_FLOW_MODEL_BLOCKED` | BLOCKED | S06 | SSFS_FLOW_MODEL_UNSUPPORTED |
| `V11_PUBLIC_QUANTIZATION_COLLISION` | BLOCKED | S09 | SSFS_PUBLIC_*_QUANTIZATION_COLLISION |
| `V12_HIGH_PRECISION_OPERATION_ORDER` | VALID | NOT_APPLICABLE | none |

### 23.2 Python 3.11/3.12 byte-identity probes (P01–P11)

| Probe | Subject |
|---|---|
| P01 | request canonical bytes/hash |
| P02 | mass-flow-authority canonical bytes/hash |
| P03 | PropertySnapshot replay |
| P04 | valid success canonical bytes/result_hash/result_id |
| P05 | typed blocked canonical bytes/result_hash/result_id |
| P06 | raw-boundary blocked canonical bytes/blocked_result_hash |
| P07 | four raw engineering values |
| P08 | four public quantized values |
| P09 | blocker/warning ordering |
| P10 | provenance bytes/hash |
| P11 | repeated-run identity |

### 23.3.01 `V01_VALID_SINGLE_PHASE_LIQUID` contract

- `EXPECTED_STATUS=VALID`
- `EXPECTED_FAILURE_STAGE=NOT_APPLICABLE`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=none`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.02 `V02_VALID_SINGLE_PHASE_GAS` contract

- `EXPECTED_STATUS=VALID`
- `EXPECTED_FAILURE_STAGE=NOT_APPLICABLE`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=none`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.03 `V03_ZERO_MASS_FLOW_BLOCKED` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S04`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_MASS_FLOW_NON_POSITIVE`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.04 `V04_NEGATIVE_MASS_FLOW_BLOCKED` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S04`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_MASS_FLOW_NON_POSITIVE`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.05 `V05_PROPERTY_HASH_MISMATCH` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S03`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.06 `V06_MASS_FLOW_AUTHORITY_HASH_MISMATCH` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S04`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.07 `V07_TASK031_GEOMETRY_IDENTITY_MISMATCH` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S02`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_TASK031_IDENTITY_MISMATCH`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.08 `V08_SAME_CASE_BINDING_MISMATCH` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S05`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_SAME_CASE_BINDING_MISMATCH`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.09 `V09_NON_NEWTONIAN_RHEOLOGY_BLOCKED` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S06`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_RHEOLOGY_MODEL_UNSUPPORTED`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.10 `V10_UNSUPPORTED_FLOW_MODEL_BLOCKED` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S06`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_FLOW_MODEL_UNSUPPORTED`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.11 `V11_PUBLIC_QUANTIZATION_COLLISION` contract

- `EXPECTED_STATUS=BLOCKED`
- `EXPECTED_FAILURE_STAGE=S09`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=SSFS_PUBLIC_*_QUANTIZATION_COLLISION`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

### 23.3.12 `V12_HIGH_PRECISION_OPERATION_ORDER` contract

- `EXPECTED_STATUS=VALID`
- `EXPECTED_FAILURE_STAGE=NOT_APPLICABLE`
- `EXPECTED_BLOCKER_CODES_IN_ORDER=none`
- `ORACLE_DERIVATION`: independent arithmetic from frozen Decimal constants and §4 raw graph
- Design-time vectors only; repository output is not engineering authority
- `BASE_FIXTURE_ID`: design-time shared base fixture unless mutation table specifies otherwise
- `MUTATIONS_IN_ORDER`: ordered list applied to base fixture before validation

## 24. Future implementation package boundary

Reserved future package:

```text
src/hexagent/exchangers/shell_tube/shell_side_flow_state/
```

### 24.1 Frozen production allowlist (14 paths)

- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/__init__.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/models.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/canonical.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/formulas.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/authority.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/schema.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/validation.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/engineering_authority_snapshot.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/blocker_registry.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/warning_registry.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/raw_projection.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/provenance.py`
- `src/hexagent/exchangers/shell_tube/shell_side_flow_state/decimal_quantization.py`
- `ci-shard-manifest.yml`

TASK-031 and TASK-026 production modules are read-only dependencies.

### 24.2 Module responsibility map

| Module | Responsibility |
|---|---|
| `__init__.py` | Public export surface; exactly one public `validate_request` |
| `models.py` | Frozen dataclasses, enums, constants, field tuples, profile tokens |
| `schema.py` | Raw dict decode/encode; closed-shape validation; decimal lexical rules |
| `authority.py` | Engineering authority request binding validation |
| `engineering_authority_snapshot.py` | Immutable frozen authority package constant |
| `formulas.py` | Pure F01–F04 raw engineering evaluation |
| `decimal_quantization.py` | S09 public quanta application |
| `validation.py` | Stage pipeline S00–S12 orchestration |
| `canonical.py` | Request/result/provenance canonical projections and hashes |
| `raw_projection.py` | S00/S01 raw-boundary blocked projection |
| `blocker_registry.py` | Closed blocker codes, stage map, sort key |
| `warning_registry.py` | Closed warning codes, eligibility, sort key |
| `provenance.py` | Provenance assembly and provenance_hash |

## 25. Required future test matrix
```text
TASK032_REQUIRED_TEST_ID_COUNT=32
TASK032_TEST_PATH_ALLOWLIST_COUNT=13
TASK032_PACKAGE_MARKER_COUNT=1
TASK032_PYTEST_TEST_MODULE_COUNT=12
CI_MANIFEST_TASK032_ADDED_PATH_COUNT=12
CI_MANIFEST_INCLUDES_PACKAGE_MARKER=false
CI_SHARD=ci
CI_PYTHON_VERSIONS=(3.11,3.12)
```

### 25.1 Test path allowlist (13 paths)

- `tests/exchangers/shell_tube/shell_side_flow_state/__init__.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_models.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_schema.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_authority.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_formulas.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_canonical.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_validation.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_architecture.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_property_snapshot_binding.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_mass_flow_authority.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_determinism.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_python311_python312_byte_identical.py`
- `tests/exchangers/shell_tube/shell_side_flow_state/test_external_vectors.py`

### 25.2 Test ID → module mapping (32 IDs, 12 modules)

| Module | Test IDs |
|---|---|
| `test_models.py` | `T032-MOD-001_EXACT_FIELD_TUPLES_AND_COUNTS, T032-MOD-002_PUBLIC_OUTPUT_FIELD_NAMES_MATCH_FROZEN_FORMULA_AUTHORITY, T032-CON-001_PACKAGE_CONSTANTS_AND_PROFILE_TOKENS` |
| `test_schema.py` | `T032-SCH-001_RAW_TOP_LEVEL_CLOSED_SHAPE, T032-SCH-002_NESTED_RAW_SHAPES_AND_DECIMAL_LEXICAL_DOMAIN, T032-SCH-003_PROFILE_ID_REJECTION` |
| `test_authority.py` | `T032-AUT-001_TASK031_IDENTITY_REPLAY, T032-AUT-004_SAME_CASE_BINDING, T032-AUT-005_AGGREGATE_ENGINEERING_AUTHORITY_HASH_ID_REPLAY` |
| `test_formulas.py` | `T032-FRM-001_MASS_VELOCITY_RAW_AND_PUBLIC, T032-FRM-002_BULK_VELOCITY_RAW_AND_PUBLIC, T032-FRM-003_REYNOLDS_RAW_AND_PUBLIC, T032-FRM-004_PRANDTL_RAW_AND_PUBLIC, T032-FRM-005_TASK031_CANONICAL_DECIMAL_STRING_TO_DECIMAL_BINDING` |
| `test_canonical.py` | `T032-CAN-001_REQUEST_CANONICAL_BYTES_AND_HASH, T032-CAN-002_SUCCESS_RESULT_HASH_SELF_EXCLUSION_AND_UUID, T032-CAN-003_TYPED_BLOCKED_STAGE_GATED_IDENTITY_SLOTS, T032-CAN-004_RAW_BOUNDARY_BLOCKED_PROJECTION_AND_HASH, T032-MSG-001_BLOCKER_ENTRY_CANONICALIZATION_AND_SORT, T032-MSG-002_WARNING_ENTRY_CANONICALIZATION_AND_ELIGIBILITY` |
| `test_validation.py` | `T032-VAL-001_EARLIEST_STAGE_MAP, T032-VAL-002_FIRST_FAILING_STAGE_ACCUMULATION, T032-VAL-003_S12_RESULT_IDENTITY_FAIL_CLOSED` |
| `test_architecture.py` | `T032-ARC-001_NO_TASK033_TASK034_RUNTIME_DEPENDENCY, T032-ARC-002_CI_MANIFEST_12_MODULE_PATHS_EXCLUDES_PACKAGE_MARKER` |
| `test_property_snapshot_binding.py` | `T032-AUT-002_PROPERTY_SNAPSHOT_HASH_REPLAY, T032-PRO-001_PROPERTY_SNAPSHOT_REUSE_NO_REEVALUATION` |
| `test_mass_flow_authority.py` | `T032-AUT-003_MASS_FLOW_AUTHORITY_HASH_REPLAY, T032-MFA-001_POSITIVE_FINITE_DECIMAL_MASS_FLOW_ONLY` |
| `test_determinism.py` | `T032-DET-001_REPEAT_RUN_IDENTITY` |
| `test_python311_python312_byte_identical.py` | `T032-XPY-001_PY311_PY312_BYTE_IDENTITY` |
| `test_external_vectors.py` | `T032-VEC-001_EXTERNAL_12_VECTOR_REGISTRY_AND_ORACLES` |

## 26. Architecture and forbidden I/O boundary
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
property provider invocation
TASK033 physics modules
TASK034 physics modules
```

## 27. Design-review checklist

```text
DESIGN_REVIEW_CHECK_COUNT=28
```

| ID | Item | Authoring supplies contract |
|---|---|---|
| D01 | allocation matches Issue #180 | §1 |
| D02 | source-definition freeze preserved | §1, §4 |
| D03 | TASK-031 upstream binding exact | §5 |
| D04 | PropertySnapshot reuse exact | §5.3, §21 |
| D05 | first-slice profile exact | §3 |
| D06 | Formula F01 exact | §4.1 |
| D07 | Formula F02 exact | §4.2 |
| D08 | Formula F03 exact | §4.3 |
| D09 | Formula F04 exact | §4.4 |
| D10 | source identities exact | §4.6, §9 |
| D11 | mass-flow authority exact | §6 |
| D12 | same-case binding exact | §21 |
| D13 | phase/rheology applicability exact | §7, §8 |
| D14 | flow regime deferred | §3.2, §8 |
| D15 | request schema singular | §13 |
| D16 | result shapes closed | §15 |
| D17 | blocker taxonomy closed | §16 |
| D18 | warning taxonomy closed | §17 |
| D19 | deferred capabilities complete | §18 |
| D20 | Decimal discipline exact | §11 |
| D21 | stage pipeline S00–S12 exact | §19 |
| D22 | canonical projections exact | §20 |
| D23 | provenance complete | §22 |
| D24 | engineering vectors complete | §23 |
| D25 | implementation allowlist exact | §24 |
| D26 | test matrix exact | §25 |
| D27 | TASK-033/TASK-034 non-scope explicit | §3.3, §26 |
| D28 | implementation remains unauthorized | §1, §28 |

## 28. Explicit non-authorization statement
```text
IMPLEMENTATION_AUTHORIZED=false
TEST_AUTHORING_AUTHORIZED=false
CI_MANIFEST_MUTATION_AUTHORIZED=false
WORKFLOW_MUTATION_AUTHORIZED=false
PULL_REQUEST_AUTHORIZED=false
PUSH_AUTHORIZED=false
MERGE_AUTHORIZED=false
ISSUE_MUTATION_AUTHORIZED=false
DESIGN_FROZEN=false
TASK033_AUTHORIZED=false
TASK034_AUTHORIZED=false
DESIGN_AUTHORING_PUSH_AUTHORIZED_BY_5317271091=true
ORIGINAL_DESIGN_AUTHORING_PUSH_COMPLETED=true
DESIGN_CORRECTION_R1_PUSH_AUTHORIZED_BY_5317692890=true
FURTHER_PUSH_AUTHORIZED=false
```

Authoring this `PROPOSED` design contract does not authorize implementation,
tests, fixtures, CI changes, pull request creation, merge, or Issue mutation.
The original design authoring push was authorized by comment `5317271091`.
Design correction R1 push is authorized by comment `5317692890`. No further
push is authorized unless another explicit authorization is recorded.

---

## Appendix A — Supersession notes

| Earlier | Superseded by | Change |
|---|---|---|
| D02_TASK031_RESULT_HASH_AND_RESULT_ID_REPLAY | D02_TASK031_GEOMETRY_HASH_AND_GEOMETRY_ID_REPLAY | Use geometry_hash/geometry_id |
| 17-field ShellSideMassFlowAuthority | 18-field with rheology_model | Field count 17 → 18 |
| INCOMPRESSIBLE_CONSTANT_PROPERTY_BULK_STATE_SCREENING | SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING | Corrected flow-model identity |
| R1 typed-blocked count 14 | R2 count 15 | Added failure_stage |
| R1 blocker count 31 | R2 count 32 | Added SSFS_PROFILE_ID_UNSUPPORTED |
| R2 blocker count 32 | R3 count 33 | Added SSFS_RESULT_IDENTITY_FINALIZATION_FAILED |
| Generic success field names | shell_side_* prefixed names | Align with frozen formula public quantities |
| R2 test ID count 26 | R4 count 32 | Added closure and correction test IDs |
| D14 flow regime thresholds | DEFERRED_NO_UNIVERSAL_THRESHOLD_AUTHORITY_ADMITTED | No universal Reynolds classifier |
| Mass-flow blocker Issue #180 attribution | TASK-032 R1 proposals | MISSING/ZERO/NEGATIVE=BLOCKED are TASK-032 |
| R1 identity order | R2 corrected order | request_hash after S00/S01 decode |
| Earlier proposal text | 5317255912 deterministic/schema freeze | D15–D28 frozen as corrected |
| All prior amendments | 5317260370 complete source-definition freeze | D01–D28 frozen |
| — | 5317271091 design authoring authorization | Design doc only; no implementation |
| — | 5317687475 design independent review R1 | Eight review findings |
| — | 5317692890 design correction R1 authorization | Design doc correction only |

## Appendix B — Package constants
```text
TASK_ID=TASK-032
PUBLIC_PROFILE_ID=hxforge.shell_tube.shell_side_flow_state.v1
FIRST_SLICE_PROFILE_ID=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_BULK_FLOW_STATE_SCREENING_V1
IMPLEMENTATION_SOFTWARE_VERSION=task032.shell-side-flow-state-impl-v1
DESIGN_CONTRACT_PATH=docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md
TASK032_FIRST_SLICE_FLOW_MODEL=SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING
FIRST_SLICE_PHASE_REGIONS=(SINGLE_PHASE_LIQUID,SINGLE_PHASE_GAS)
FIRST_SLICE_RHEOLOGY_MODEL=NEWTONIAN
FIRST_SLICE_FLOW_REGIME_CLASSIFICATION=DEFERRED
```

## Appendix C — Blocker message_key binding contract

### C.1 `SSFS_SCHEMA_VERSION_UNSUPPORTED`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_schema_version_unsupported`
- Meaning: unsupported request schema token
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.2 `SSFS_PROFILE_ID_UNSUPPORTED`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_profile_id_unsupported`
- Meaning: unsupported profile_id token
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.3 `SSFS_RAW_TYPE_INVALID`

- `stage=S00`
- `severity=hard`
- `message_key=ssfs_raw_type_invalid`
- Meaning: raw value is not exact built-in dict/list/str
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.4 `SSFS_UNKNOWN_FIELD`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_unknown_field`
- Meaning: unknown field in closed schema
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.5 `SSFS_DECIMAL_LEXICAL_INVALID`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_decimal_lexical_invalid`
- Meaning: decimal lexical domain violation
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.6 `SSFS_EVIDENCE_REFS_INVALID`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_evidence_refs_invalid`
- Meaning: evidence refs wrong type, empty list, empty/invalid entry, duplicates, or other invalid lexical/content cases; unsorted but otherwise valid input is accepted and normalized
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.7 `SSFS_TASK031_RESULT_MISSING`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_task031_result_missing`
- Meaning: required task031_result absent
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.8 `SSFS_TASK031_RESULT_INVALID`

- `stage=S02`
- `severity=hard`
- `message_key=ssfs_task031_result_invalid`
- Meaning: task031_result fails shape decode
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.9 `SSFS_TASK031_RESULT_HAS_BLOCKERS`

- `stage=S02`
- `severity=hard`
- `message_key=ssfs_task031_result_has_blockers`
- Meaning: task031_result carries upstream blockers
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.10 `SSFS_TASK031_GEOMETRY_MISSING`

- `stage=S02`
- `severity=hard`
- `message_key=ssfs_task031_geometry_missing`
- Meaning: accepted geometry absent
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.11 `SSFS_TASK031_IDENTITY_MISMATCH`

- `stage=S02`
- `severity=hard`
- `message_key=ssfs_task031_identity_mismatch`
- Meaning: TASK-031 geometry hash/id replay failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.12 `SSFS_PROPERTY_SNAPSHOT_MISSING`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_property_snapshot_missing`
- Meaning: required property_snapshot absent
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.13 `SSFS_PROPERTY_SNAPSHOT_INVALID`

- `stage=S03`
- `severity=hard`
- `message_key=ssfs_property_snapshot_invalid`
- Meaning: property snapshot fails shape decode
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.14 `SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH`

- `stage=S03`
- `severity=hard`
- `message_key=ssfs_property_snapshot_hash_mismatch`
- Meaning: property snapshot hash replay failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.15 `SSFS_MASS_FLOW_AUTHORITY_MISSING`

- `stage=S01`
- `severity=hard`
- `message_key=ssfs_mass_flow_authority_missing`
- Meaning: required mass_flow_authority absent
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.16 `SSFS_MASS_FLOW_AUTHORITY_INVALID`

- `stage=S04`
- `severity=hard`
- `message_key=ssfs_mass_flow_authority_invalid`
- Meaning: mass-flow authority fails shape decode
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.17 `SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH`

- `stage=S04`
- `severity=hard`
- `message_key=ssfs_mass_flow_authority_hash_mismatch`
- Meaning: mass-flow authority hash replay failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.18 `SSFS_SAME_CASE_BINDING_MISMATCH`

- `stage=S05`
- `severity=hard`
- `message_key=ssfs_same_case_binding_mismatch`
- Meaning: same-case cross-binding failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.19 `SSFS_PHASE_UNSUPPORTED`

- `stage=S06`
- `severity=hard`
- `message_key=ssfs_phase_unsupported`
- Meaning: phase region outside admitted set
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.20 `SSFS_RHEOLOGY_MODEL_UNSUPPORTED`

- `stage=S06`
- `severity=hard`
- `message_key=ssfs_rheology_model_unsupported`
- Meaning: rheology model not NEWTONIAN
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.21 `SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED`

- `stage=S06`
- `severity=hard`
- `message_key=ssfs_property_state_role_unsupported`
- Meaning: property state role not BULK_SHELL_SIDE_STATE
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.22 `SSFS_MASS_FLOW_NON_POSITIVE`

- `stage=S04`
- `severity=hard`
- `message_key=ssfs_mass_flow_non_positive`
- Meaning: mass flow zero or negative
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.23 `SSFS_FLOW_MODEL_UNSUPPORTED`

- `stage=S06`
- `severity=hard`
- `message_key=ssfs_flow_model_unsupported`
- Meaning: flow model identity mismatch
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.24 `SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH`

- `stage=S07`
- `severity=hard`
- `message_key=ssfs_engineering_authority_identity_mismatch`
- Meaning: authority hash/profile mismatch
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.25 `SSFS_FORMULA_DOMAIN_VIOLATION`

- `stage=S06`
- `severity=hard`
- `message_key=ssfs_formula_domain_violation`
- Meaning: formula applicability/domain violation
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.26 `SSFS_FORMULA_CALCULATION_FAILED`

- `stage=S08`
- `severity=hard`
- `message_key=ssfs_formula_calculation_failed`
- Meaning: non-finite or non-positive raw engineering result
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.27 `SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION`

- `stage=S09`
- `severity=hard`
- `message_key=ssfs_public_mass_velocity_quantization_collision`
- Meaning: positive raw G_s quantizes to zero
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.28 `SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION`

- `stage=S09`
- `severity=hard`
- `message_key=ssfs_public_bulk_velocity_quantization_collision`
- Meaning: positive raw V_s quantizes to zero
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.29 `SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION`

- `stage=S09`
- `severity=hard`
- `message_key=ssfs_public_reynolds_quantization_collision`
- Meaning: positive raw Re_s quantizes to zero
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.30 `SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION`

- `stage=S09`
- `severity=hard`
- `message_key=ssfs_public_prandtl_quantization_collision`
- Meaning: positive raw Pr_s quantizes to zero
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.31 `SSFS_CANONICALIZATION_FAILED`

- `stage=S11`
- `severity=hard`
- `message_key=ssfs_canonicalization_failed`
- Meaning: canonical projection failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.32 `SSFS_RESULT_IDENTITY_FINALIZATION_FAILED`

- `stage=S12`
- `severity=hard`
- `message_key=ssfs_result_identity_finalization_failed`
- Meaning: result hash/id finalization failure
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding

### C.33 `SSFS_PARTIAL_RESULT_FORBIDDEN`

- `stage=S10`
- `severity=hard`
- `message_key=ssfs_partial_result_forbidden`
- Meaning: defensive only — partial flow state attempted
- `payload`: canonical key-value tuple when required by stage
- `evidence_refs`: sorted unique non-empty when stage requires evidence binding


## Appendix D — Warning message_key binding contract

### D.1 `SSFS_SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_single_bulk_property_snapshot_screening_only`
- Meaning: single bulk snapshot screening only

### D.2 `SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_flow_regime_classification_deferred`
- Meaning: flow regime classification deferred

### D.3 `SSFS_NON_NEWTONIAN_DEFERRED`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_non_newtonian_deferred`
- Meaning: non-Newtonian rheology deferred

### D.4 `SSFS_COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_compressible_path_integration_excluded`
- Meaning: compressible path integration excluded

### D.5 `SSFS_HEAT_TRANSFER_PRESSURE_DROP_DEFERRED`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_heat_transfer_pressure_drop_deferred`
- Meaning: heat transfer and pressure drop deferred

### D.6 `SSFS_NO_FULL_EXCHANGER_RATING_CLAIM`

- `prerequisite_stage=S06`
- `severity=warning`
- `message_key=ssfs_no_full_exchanger_rating_claim`
- Meaning: no full exchanger rating claim

### D.7 `SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY`

- `prerequisite_stage=S07`
- `severity=warning`
- `message_key=ssfs_formula_authority_screening_model_only`
- Meaning: formula authority screening model only


## Appendix E — Per-stage execution contract

### E.S00 `raw_input_boundary`

Scope: top-level raw type gate
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S01 `request_schema_and_decode`

Scope: schema_version, profile_id, closed field set
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S02 `task031_result_validation_and_identity_replay`

Scope: TASK-031 acceptance and geometry replay
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S03 `property_snapshot_validation_and_hash_replay`

Scope: PropertySnapshot decode and hash replay
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S04 `mass_flow_authority_validation_and_hash_replay`

Scope: authority decode, positivity, hash replay
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S05 `same_case_cross_binding`

Scope: §21 same-case equalities
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S06 `phase_rheology_and_applicability`

Scope: §7.1 applicability table
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S07 `engineering_authority_identity_replay`

Scope: frozen authority replay
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S08 `raw_engineering_calculation`

Scope: unquantized F01–F04 evaluation
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S09 `public_quantization`

Scope: §11.3 output quanta
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S10 `warnings_blockers_finalization`

Scope: warning eligibility and defensive partial guard
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S11 `canonical_serialization`

Scope: canonical projections
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.

### E.S12 `hash_uuid_provenance_finalization`

Scope: result_hash, result_id, provenance_hash
- Accumulate all complete blockers from this stage before deciding whether to halt.
- Do not execute later stages after the first failing stage.
- Warning eligibility begins only after prerequisite stages complete.


## Appendix F — Singular formula evaluation sequences

### F.TASK032_MASS_VELOCITY_KERN_SCREENING_INTCHOPN_EQ57_V1

- Public quantity: `shell_side_mass_velocity_kg_m2_s`
- Formula: `G_s = m_dot_s / A_s`
- Source: `SRC-INTECHOPEN-100450-KHARAJI-2021`
- Evaluation: unquantized Decimal through stage S08; public quantum at S09
- Domain: finite strictly positive denominators required

### F.TASK032_REYNOLDS_KERN_SCREENING_INTCHOPN_EQ54_V1

- Public quantity: `shell_side_reynolds_number`
- Formula: `Re_s = G_s * D_e / mu_s`
- Source: `SRC-INTECHOPEN-100450-KHARAJI-2021`
- Evaluation: unquantized Decimal through stage S08; public quantum at S09
- Domain: finite strictly positive denominators required

### F.TASK032_BULK_VELOCITY_CONTINUITY_NASA_GRC_V1

- Public quantity: `shell_side_bulk_velocity_m_s`
- Formula: `V_s = m_dot_s/(rho_s*A_s)`
- Source: `SRC-NASA-GRC-MASS-FLOW-RATE-EQUATIONS`
- Evaluation: unquantized Decimal through stage S08; public quantum at S09
- Domain: finite strictly positive denominators required

### F.TASK032_PRANDTL_DIMENSIONLESS_INTCHOPN_EQ35_V1

- Public quantity: `shell_side_prandtl_number`
- Formula: `Pr_s = mu_s*Cp_s/k_s`
- Source: `SRC-INTECHOPEN-100450-KHARAJI-2021`
- Evaluation: unquantized Decimal through stage S08; public quantum at S09
- Domain: finite strictly positive denominators required


## Appendix G — Nested request subrecord closed shapes

### G.1 `task031_result` minimum consumed geometry fields

| Field path | Encoding |
|---|---|
| `status` | exact VALID |
| `geometry.geometry_id` | URN string |
| `geometry.geometry_hash` | lowercase hex SHA-256 |
| `geometry.task020_configuration_id` | URN string |
| `geometry.task020_configuration_hash` | lowercase hex SHA-256 |
| `geometry.central_crossflow_flow_area_m2` | canonical decimal string |
| `geometry.shell_side_equivalent_hydraulic_diameter_m` | canonical decimal string |
| `geometry.engineering_authority_id` | frozen URN |
| `geometry.engineering_authority_hash` | lowercase hex SHA-256 |
| `geometry.flow_region_identity` | exact CENTRAL_CROSSFLOW_SCREENING |
| `blockers` | empty list on acceptance |

### G.2 `property_snapshot` closed fields (count 10)

- `density_kg_m3`
- `dynamic_viscosity_pa_s`
- `thermal_conductivity_w_m_k`
- `specific_heat_capacity_j_kg_k`
- `bulk_temperature_k`
- `bulk_pressure_pa`
- `phase_region`
- `property_source_id`
- `property_source_version`
- `property_snapshot_hash`

### G.3 `mass_flow_authority` closed fields (count 18)

- `schema_version`
- `authority_profile_id`
- `shell_side_case_id`
- `shell_side_stream_id`
- `shell_side_fluid_id`
- `rheology_model`
- `task020_configuration_id`
- `task020_configuration_hash`
- `task031_geometry_id`
- `task031_geometry_hash`
- `property_snapshot_hash`
- `property_state_role`
- `mass_flow_rate_kg_s`
- `mass_flow_sign_convention`
- `authority_source_id`
- `authority_source_version`
- `evidence_refs`
- `authority_hash`

## Appendix H — Canonical JSON byte rules

1. Object keys sorted lexicographically at every nesting level.
2. No insignificant whitespace in canonical bytes.
3. Decimal values encoded as canonical decimal strings, never binary floats.
4. Enum values encoded as exact string tokens.
5. Tuples encoded as JSON arrays preserving field order.
6. Null encoded only where explicitly admitted by the relevant projection.
7. Unknown fields are schema violations, not canonicalization omissions.
8. Hash inputs use namespace prefix concatenation per repository convention.
9. Self-excluded hash fields must be absent from the hash projection, not null-sentinel encoded.
10. UUID5 result_id derivation uses lowercase hex result_hash without prefix.

## Appendix I — TASK-033 / TASK-034 explicit physics prohibition

- shell-side heat-transfer coefficient correlations
- shell-side Nusselt number correlations
- shell-side friction factor correlations
- shell-side pressure-drop integration
- Bell–Delaware correction factors
- leakage and bypass correction models
- overall heat-transfer coefficient U
- UA product rating
- LMTD duty closure
- heat duty and outlet temperature solvers
- full exchanger rating orchestration
- flow-regime threshold classifiers beyond deferral warnings
- non-Newtonian rheology models
- compressible property-path integration
- axial property-path integration

Architecture test `T032-ARC-001_NO_TASK033_TASK034_RUNTIME_DEPENDENCY` must fail
closed if any TASK-033 or TASK-034 module import appears in the production
allowlist package graph.

## Appendix J — Per-test-ID binding contracts (32 IDs)

### J.1 `T032-MOD-001_EXACT_FIELD_TUPLES_AND_COUNTS`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.2 `T032-MOD-002_PUBLIC_OUTPUT_FIELD_NAMES_MATCH_FROZEN_FORMULA_AUTHORITY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.3 `T032-CON-001_PACKAGE_CONSTANTS_AND_PROFILE_TOKENS`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.4 `T032-SCH-001_RAW_TOP_LEVEL_CLOSED_SHAPE`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.5 `T032-SCH-002_NESTED_RAW_SHAPES_AND_DECIMAL_LEXICAL_DOMAIN`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.6 `T032-SCH-003_PROFILE_ID_REJECTION`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.7 `T032-AUT-001_TASK031_IDENTITY_REPLAY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.8 `T032-AUT-002_PROPERTY_SNAPSHOT_HASH_REPLAY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.9 `T032-AUT-003_MASS_FLOW_AUTHORITY_HASH_REPLAY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.10 `T032-AUT-004_SAME_CASE_BINDING`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.11 `T032-AUT-005_AGGREGATE_ENGINEERING_AUTHORITY_HASH_ID_REPLAY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.12 `T032-FRM-001_MASS_VELOCITY_RAW_AND_PUBLIC`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.13 `T032-FRM-002_BULK_VELOCITY_RAW_AND_PUBLIC`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.14 `T032-FRM-003_REYNOLDS_RAW_AND_PUBLIC`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.15 `T032-FRM-004_PRANDTL_RAW_AND_PUBLIC`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.16 `T032-FRM-005_TASK031_CANONICAL_DECIMAL_STRING_TO_DECIMAL_BINDING`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.17 `T032-CAN-001_REQUEST_CANONICAL_BYTES_AND_HASH`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.18 `T032-CAN-002_SUCCESS_RESULT_HASH_SELF_EXCLUSION_AND_UUID`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.19 `T032-CAN-003_TYPED_BLOCKED_STAGE_GATED_IDENTITY_SLOTS`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.20 `T032-CAN-004_RAW_BOUNDARY_BLOCKED_PROJECTION_AND_HASH`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.21 `T032-MSG-001_BLOCKER_ENTRY_CANONICALIZATION_AND_SORT`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.22 `T032-MSG-002_WARNING_ENTRY_CANONICALIZATION_AND_ELIGIBILITY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.23 `T032-VAL-001_EARLIEST_STAGE_MAP`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.24 `T032-VAL-002_FIRST_FAILING_STAGE_ACCUMULATION`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.25 `T032-VAL-003_S12_RESULT_IDENTITY_FAIL_CLOSED`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.26 `T032-ARC-001_NO_TASK033_TASK034_RUNTIME_DEPENDENCY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.27 `T032-ARC-002_CI_MANIFEST_12_MODULE_PATHS_EXCLUDES_PACKAGE_MARKER`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.28 `T032-PRO-001_PROPERTY_SNAPSHOT_REUSE_NO_REEVALUATION`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.29 `T032-MFA-001_POSITIVE_FINITE_DECIMAL_MASS_FLOW_ONLY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.30 `T032-DET-001_REPEAT_RUN_IDENTITY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.31 `T032-XPY-001_PY311_PY312_BYTE_IDENTITY`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.

### J.32 `T032-VEC-001_EXTERNAL_12_VECTOR_REGISTRY_AND_ORACLES`

- Test ID is frozen and must not be renamed.
- Must assert exact frozen contract behavior from the referenced design sections.
- Must not use repository implementation output as engineering oracle authority.
- Must fail closed on any contract drift from Issue #185 freeze `5317260370`.
