# TASK-033 — Shell-and-Tube Shell-Side Single-Phase Heat Transfer

> Binding **proposed design contract** for the TASK-033 shell-side heat-transfer
> screening foundation.
>
> TASK-033 consumes an accepted TASK-032 shell-side flow-state authority plus
> the exact accepted TASK-032 request evidence needed to replay the frozen
> upstream value-authority graph. It produces exactly one public engineering
> semantic:
>
> `modeled_shell_side_heat_transfer_coefficient_w_m2_k`
>
> on `OUTER_TUBE_SURFACE`, using the single frozen production correlation
> `TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1`.
>
> This design does not select, substitute, or fallback a correlation; does not
> reconstruct TASK-031/TASK-032 engineering; and does not implement TASK-034
> pressure-drop physics or TASK-035 composition physics.

## 1. Authority, allocation, baseline, and status

| Field | Binding value |
|---|---|
| Repository | `xuezhiorange-png/hxforge-agent` |
| Allocation authority | Issue #180 — TASK-033 allocation |
| Source-definition authority | Issue #196 governance comment chain |
| Structural amendment | `5386867807` |
| Engineering source/correlation freeze | `5387111841` |
| Deterministic/schema freeze | `5387280137` |
| Complete source-definition freeze | `5387329709` |
| Design authoring authorization | `5387395266` |
| Authoring base | `main@f1231f29ee370e4f1d07b934b290614e89043726` |
| Design branch | `docs/task-033-shell-side-single-phase-heat-transfer-design` |
| Design file | `docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md` |
| Public profile ID | `hxforge.shell_tube.shell_side_heat_transfer.v1` |
| First-slice profile | `SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_OUTER_TUBE_SURFACE_HTC_SCREENING_V1` |
| Design status | `PROPOSED` |
| Source definition frozen | `true` |
| Design frozen | `false` |
| Implementation | `NOT AUTHORIZED` |
| Pull request | `NOT AUTHORIZED` |
| TASK-034/035/036 | `NOT AUTHORIZED` |
| Issue close | `NOT AUTHORIZED` |

```text
TASK033_SOURCE_DEFINITION_FROZEN=true
TASK033_ENGINEERING_SOURCE_CORRELATION_AUTHORITY_FROZEN=true
TASK033_DETERMINISTIC_IDENTITY_SCHEMA_FROZEN=true
TASK033_DESIGN_AUTHORIZED=true
DESIGN_AUTHORING_AUTHORIZED=true
DESIGN_FROZEN=false
IMPLEMENTATION_AUTHORIZED=false
PULL_REQUEST_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This authoring gate permits one design branch and this one design file. The
file is not approved or frozen by authoring; a separate independent review is
required.

```text
DESIGN_MAY_SELECT_ENGINEERING_CORRELATION=false
DESIGN_MAY_SUBSTITUTE_ENGINEERING_CORRELATION=false
DESIGN_MAY_FALLBACK_ENGINEERING_CORRELATION=false
DESIGN_MAY_CHANGE_FROZEN_SCHEMA_OR_IDENTITY=false
```

## 2. Exact allocation and responsibility

TASK-033 is downstream of TASK-032 and upstream of TASK-035. Its v1
responsibility is narrowly bounded:

1. accept a complete, replay-verifiable TASK-032 flow-state evidence envelope;
2. accept the exact TASK-032 request evidence that generated that flow state;
3. replay TASK-032 request/result identities and nested TASK-031,
   `PropertySnapshot`, and mass-flow authority identities without rerunning
   upstream engineering;
4. verify same-case and frozen applicability predicates;
5. evaluate the one frozen shell-side HTC correlation deterministically;
6. quantize and identity-bind the single public HTC result;
7. fail closed with no partial HTC.

TASK-033 owns no geometry reconstruction, property reevaluation, flow-state
recalculation, pressure-drop physics, overall-U calculation, duty calculation,
or exchanger rating.

## 3. Scope and explicit non-scope

### 3.1 Frozen first-slice scope

```text
PUBLIC_PROFILE_ID=hxforge.shell_tube.shell_side_heat_transfer.v1
FIRST_SLICE_PROFILE_ID=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_KHARAJI_2021_EQ58_OUTER_TUBE_SURFACE_HTC_SCREENING_V1
PUBLIC_CALCULATION_OPERATION_COUNT=1
PUBLIC_CALCULATION_OPERATION=validate_request(raw_request)
TASK033_PUBLIC_ENGINEERING_OUTPUT_COUNT=1
TASK033_PUBLIC_ENGINEERING_OUTPUT=modeled_shell_side_heat_transfer_coefficient_w_m2_k
TASK033_HEAT_TRANSFER_SURFACE=OUTER_TUBE_SURFACE
NUSSELT_PUBLIC_OUTPUT=false
NUSSELT_INTERNAL_INTERMEDIATE_REQUIRED=false
```

### 3.2 Explicit non-scope

TASK-033 v1 does not calculate or own:

```text
FLOW_REGIME_CLASSIFICATION
SHELL_SIDE_PRESSURE_DROP
MODELED_SHELL_SIDE_PRESSURE_DROP
SHELL_SIDE_FRICTION_FACTOR
NOZZLE_PRESSURE_DROP
STATIC_HEAD
ACCELERATION_PRESSURE_DROP
BELL_DELAWARE
LEAKAGE_CORRECTIONS
BYPASS_CORRECTIONS
AREA_BASIS_CONVERSION
TUBE_WALL_CONDUCTION
INSIDE_FOULING_RESISTANCE
OUTSIDE_FOULING_RESISTANCE
OVERALL_U
UA
LMTD
LMTD_CORRECTION_FACTOR
EFFECTIVENESS_NTU
HEAT_DUTY
OUTLET_TEMPERATURES
FULL_EXCHANGER_THERMAL_RATING
THERMAL_SIZING
GEOMETRY_OPTIMIZATION
WALL_TEMPERATURE_ITERATION
AUTOMATIC_WALL_VISCOSITY_ITERATION
FLOW_INDUCED_VIBRATION
NOZZLE_SIZING
MECHANICAL_ADEQUACY
MATERIAL_SELECTION
COST_OPTIMIZATION
PUBLIC_API_EXTENSION
PERSISTENCE_EXTENSION
CLI
REPORTING
TASK034_PHYSICS
TASK035_COMPOSITION_PHYSICS
```

## 4. Frozen engineering correlation and source authority

### 4.1 Correlation identity

```text
KERN_IS_METHOD_FAMILY_LABEL=true
KERN_STRING_IS_EXACT_FORMULA_IDENTITY=false
KERN_STRING_IS_PRODUCTION_CORRELATION_ID=false

TASK033_PRODUCTION_CORRELATION_ID=TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1
TASK033_PRODUCTION_CORRELATION_COUNT=1
RUNTIME_CORRELATION_SELECTION=false
RUNTIME_CORRELATION_FALLBACK=false
RUNTIME_CORRELATION_SUBSTITUTION=false
```

### 4.2 Source identity

```text
SOURCE_ID=SRC-INTECHOPEN-100450-KHARAJI-2021
SOURCE_CLASS=OPEN_ACCESS_ENGINEERING_CHAPTER
SOURCE_TITLE=Heat Exchanger Design and Optimization
AUTHOR=Shahin Kharaji
PUBLICATION_YEAR=2021
DOI=10.5772/intechopen.100450
SOURCE_LOCATION=Section_4.4_Shell_diameter_Equation_58
LICENSE=CC_BY_3_0
PERMISSION_STATUS=LAWFUL_PUBLIC_ACCESS_REUSE_WITH_ATTRIBUTION
APPROVAL_STATUS=FROZEN_FOR_TASK033_ENGINEERING_SOURCE_CORRELATION_AUTHORITY
```

The superseded `Section_4.1_Kerns_method_Equation_58` location is not
binding. The corrected Section 4.4 location is the only authoritative source
location for this design.

### 4.3 Formula and surface basis

```text
FORMULA_ID=TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1
FORMULA=h_s = (0.36 * k_s / D_e) * Re_s^0.55 * Pr_s^(1/3)
FORMULA_OUTPUT_SEMANTIC=modeled_shell_side_heat_transfer_coefficient_w_m2_k
TASK033_HEAT_TRANSFER_SURFACE=OUTER_TUBE_SURFACE
AREA_BASIS_CONVERSION_REQUIRED=false
IMPLICIT_AREA_BASIS_CONVERSION=false
INNER_TO_OUTER_AREA_CONVERSION=false
OUTER_TO_INNER_AREA_CONVERSION=false
```

### 4.4 Correlation applicability and idealization

```text
CANDIDATE_A_REYNOLDS_APPLICABILITY=2e3 < Re_s < 1e6
REYNOLDS_LOWER_BOUND_EXCLUSIVE=true
REYNOLDS_UPPER_BOUND_EXCLUSIVE=true
KERN_EQ58_RE_RANGE_IS_FLOW_REGIME_CLASSIFIER=false
TASK032_FLOW_REGIME_CLASSIFICATION_AVAILABLE=false
TASK032_FLOW_REGIME_CLASSIFICATION_DEFERRED=true

IDEALIZED_SHELL_FLOW_MODEL=true
SINGLE_SHELL_STREAM_MODEL=true
BAFFLE_DRIVEN_SHELL_FLOW=true
SHELL_LEAKAGE_CORRECTION_INCLUDED=false
SHELL_BYPASS_CORRECTION_INCLUDED=false
LEAKAGE_AS_ZERO=false
BYPASS_AS_ZERO=false
UNMODELED_LEAKAGE_AS_ZERO=false
UNMODELED_BYPASS_AS_ZERO=false
```

The source-defined Reynolds domain is a strict correlation domain, not a
TASK-032 flow-regime classification. The phase/rheology ceiling remains the
accepted TASK-032 single-phase Newtonian applicability; this design does not
claim that the Kharaji source independently classifies both phase classes.

### 4.5 Wall-property discipline

```text
WALL_PROPERTY_REQUIRED=false
WALL_TEMPERATURE_REQUIRED=false
WALL_VISCOSITY_ITERATION_REQUIRED=false
EXPLICIT_WALL_PROPERTY_AUTHORITY_REQUIRED=false
IMPLICIT_WALL_TEMPERATURE=false
IMPLICIT_MU_W_EQUALS_MU=false
IMPLICIT_VISCOSITY_RATIO_EQUALS_ONE=false
HIDDEN_WALL_VISCOSITY_CORRECTION=false
```

Candidate B remains an alternate deferred source candidate only. It is not
selected, admitted, frozen, callable, or a runtime fallback.

## 5. Direct upstream and value-authority replay model

```text
TASK033_DIRECT_UPSTREAM=TASK032
TASK031_IS_TASK033_DIRECT_UPSTREAM=false
TASK026_IS_TASK033_DIRECT_UPSTREAM=false
TASK033_ACCEPTED_TASK032_SUCCESS_REQUIRED=true
TASK033_TASK032_IDENTITY_REPLAY_REQUIRED=true
TASK033_AUXILIARY_VALUE_PROOF_MODEL=REPLAY_EXACT_ACCEPTED_TASK032_REQUEST
TASK033_AUXILIARY_JOINING_AUTHORITY=TASK032_REQUEST_IDENTITY_REPLAY
TASK033_TASK032_REQUEST_REPLAY_REQUIRED=true
TASK033_TASK032_REQUEST_HASH_REPLAY_REQUIRED=true

TASK033_RECOMPUTE_TASK031_HYDRAULIC_GEOMETRY=false
TASK033_RECOMPUTE_TASK032_FLOW_STATE=false
TASK033_RECOMPUTE_TASK032_REYNOLDS=false
TASK033_RECOMPUTE_TASK032_PRANDTL=false
TASK033_RUNTIME_PROPERTY_LOOKUP=false
TASK033_HIDDEN_DEFAULT_INPUTS=false
```

### 5.1 TASK033-owned immutable replay envelopes

R2 supersedes the earlier exact-private-class requirement. Production design
must not import TASK-032 private `models.py` or `canonical.py` merely to prove
identity.

```text
TASK033_UPSTREAM_EVIDENCE_MODEL=TASK033_OWNED_IMMUTABLE_REPLAY_ENVELOPES
EXACT_TASK032_INTERNAL_CLASS_IDENTITY_REQUIRED=false
TASK032_SEMANTIC_IDENTITY_REPLAY_REQUIRED=true
TASK032_CANONICAL_FIELD_EQUIVALENCE_REQUIRED=true
TASK032_HASH_IDENTITY_EQUIVALENCE_REQUIRED=true
TASK032_PRIVATE_MODEL_IMPORT=false
TASK032_PRIVATE_CANONICAL_IMPORT=false
TASK033_PRIVATE_TASK032_INTERNAL_ACCESS=false
```

The two design envelopes are TASK-033-owned immutable replay representations.
They are not TASK-032 public API extensions and must not import TASK-032
private model or canonical classes.

`Task032AcceptedFlowStateEvidence` has the exact frozen TASK-032 success
canonical field order below. The complete projection is required; retaining
only the values consumed by Eq.58, such as Re_s and Pr_s, is forbidden.

```text
TASK033_FLOW_STATE_EVIDENCE_FIELD_COUNT=29
COMPLETE_TASK032_SUCCESS_CANONICAL_PROJECTION_REQUIRED=true
TASK032_FLOW_STATE_EVIDENCE_PARTIAL_PROJECTION_ALLOWED=false

TASK033_FLOW_STATE_EVIDENCE_FIELDS=(
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
  provenance,
)
```

`Task032AcceptedRequestEvidence` has the complete TASK-032 request canonical
projection, including the complete nested projections needed for replay:

```text
TASK033_REQUEST_EVIDENCE_MODEL=TASK033_OWNED_IMMUTABLE_REPLAY_ENVELOPE
TASK033_AUXILIARY_VALUE_PROOF_MODEL=REPLAY_EXACT_ACCEPTED_TASK032_REQUEST
UPSTREAM_NESTED_PROJECTION_BYTE_EQUIVALENCE_REQUIRED=true

TASK033_REQUEST_EVIDENCE_FIELDS=(
  schema_version,
  profile_id,
  complete TASK031 result projection,
  property_snapshot_hash,
  complete PropertySnapshot projection,
  complete mass-flow-authority projection,
  evidence_refs,
)

TASK031_ENGINEERING_RECOMPUTATION=false
PROPERTY_REEVALUATION=false
MASS_FLOW_RECOMPUTATION=false
```

These are TASK-033-owned replay representations. They do not redefine or
recalculate upstream engineering semantics.

### 5.2 Frozen engineering input bindings

```text
Re_s = task032_flow_state.shell_side_reynolds_number
Pr_s = task032_flow_state.shell_side_prandtl_number
k_s  = task032_request_evidence.property_snapshot.thermal_conductivity_w_m_k
D_e  = task032_request_evidence.task031_result.geometry.shell_side_equivalent_hydraulic_diameter_m
```

`D_e` is converted from the replay-verified canonical fixed-point string by
`Decimal(string)` only. `k_s` is consumed from the replay-verified property
snapshot without property reevaluation.

### 5.3 Exact TASK-032 identity replay

```text
TASK033_UPSTREAM_CANONICAL_REPLAY_IMPLEMENTATION_MODEL=TASK033_OWNED_FROZEN_PROJECTION_REPLAY_V1
TASK033_REPLAYS_TASK032_REQUEST_HASH_NAMESPACE=task032.request.v1
TASK033_TASK032_REQUEST_PROJECTION_EQUIVALENCE=BYTE_EXACT_WITH_FROZEN_TASK032_V1
TASK033_REPLAYS_TASK032_SUCCESS_RESULT_HASH_NAMESPACE=task032.success-result.v1
TASK033_TASK032_SUCCESS_PROJECTION_EQUIVALENCE=BYTE_EXACT_WITH_FROZEN_TASK032_V1
TASK032_RESULT_ID_NAMESPACE=96ab5cf6-204d-547a-9d27-8a5eff46f997
TASK032_RESULT_ID_NAME_PREFIX=task032-result-v1::
```

Required equalities:

```text
recompute_task032_request_hash_from_task033_envelope(task032_request_evidence)
== task032_flow_state.request_hash

recompute_task032_success_hash_from_task033_envelope(task032_flow_state)
== task032_flow_state.result_hash

recompute_task032_result_id(task032_flow_state.result_hash)
== task032_flow_state.result_id
```

No tolerance identity matching, alias inference, hash repair, producer rerun,
or call to TASK-032 `validate_request` is permitted.

## 6. Same-case and applicability intersection

Before engineering, the replay graph must prove the same physical shell-side
case wherever represented:

```text
same task032 result identity
same shell_side_case_id
same shell_side_stream_id
same shell_side_fluid_id
same task020_configuration_id/hash
same task031_geometry_id/hash
same property_snapshot_hash
same mass_flow_authority_hash
```

Applicability is the exact intersection of:

```text
TASK032 accepted first-slice applicability
AND frozen TASK033 correlation applicability
AND frozen TASK033 value-authority replay predicates
```

TASK-032 ceiling consumed by TASK-033:

```text
phase_region in {SINGLE_PHASE_LIQUID,SINGLE_PHASE_GAS}
rheology_model=NEWTONIAN
property_state_role=BULK_SHELL_SIDE_STATE
flow_region_identity=CENTRAL_CROSSFLOW_SCREENING
positive finite admitted upstream values
```

TASK-033 further requires strict `2e3 < Re_s < 1e6` and positive finite
`Re_s`, `Pr_s`, `k_s`, and `D_e`.

## 7. Public request boundary

```text
REQUEST_TYPE=ShellSideHeatTransferRequest
REQUEST_SCHEMA_VERSION=task033.shell-side-heat-transfer-request.v1
REQUEST_FIELD_COUNT=5
REQUEST_FIELDS=(
  schema_version,
  profile_id,
  task032_flow_state,
  task032_request_evidence,
  evidence_refs
)
```

The R2 binding changes the semantic types of the two upstream fields to the
TASK-033-owned immutable replay envelopes described in §5.1. It does not
change the frozen five-field public request shape.

Top-level raw input is an exact built-in dict with those five string keys, no
aliases and no unknown fields. A `Mapping`, `MutableMapping`, dict subclass,
or other mapping-like object is not an equivalent request boundary.

```text
RAW_TOP_LEVEL_REQUEST_TYPE=EXACT_BUILTIN_DICT
```

`evidence_refs` is a non-empty deterministic tuple of strings. No correlation
selector is present.

## 8. Decimal engineering algorithm

### 8.1 Explicit Decimal context

```text
DECIMAL_CONTEXT_CONSTRUCTION=EXPLICIT_CONTEXT_V1
DECIMAL_PRECISION=50
ROUNDING_MODE=ROUND_HALF_EVEN
DECIMAL_EMIN=-999999
DECIMAL_EMAX=999999
DECIMAL_CAPITALS=1
DECIMAL_CLAMP=0
AMBIENT_DECIMAL_CONTEXT_INHERITANCE=false
AMBIENT_GETCONTEXT_DEPENDENCY=false
CONTEXT_FLAGS_CLEARED_BEFORE_ENGINEERING=true
DECIMAL_FLAGS_INITIAL=ALL_CLEAR

DECIMAL_TRAP_INVALID_OPERATION=true
DECIMAL_TRAP_DIVISION_BY_ZERO=true
DECIMAL_TRAP_OVERFLOW=true
DECIMAL_TRAP_INEXACT=false
DECIMAL_TRAP_ROUNDED=false
DECIMAL_TRAP_SUBNORMAL=false
DECIMAL_TRAP_UNDERFLOW=false
DECIMAL_TRAP_CLAMPED=false
DECIMAL_TRAP_FLOAT_OPERATION=true

FLOAT_OPERATION_SIGNAL_NOT_PERMITTED=true
BINARY_FLOAT_ENGINEERING=false
FLOAT_TO_DECIMAL_COERCION=false

DECIMAL_SIGNAL_FAILURE_MAPPING=EXISTING_FORMULA_CALCULATION_BLOCKER
DECIMAL_SIGNAL_FALLBACK=false
DECIMAL_SIGNAL_PARTIAL_RESULT=false
```

Ambient `Context()`, `DefaultContext`, process `getcontext()` state, binary
float coercion, and float transcendental operations are forbidden. Any trapped
or calculation-failure Decimal signal is fail-closed: evaluation order is not
changed, a binary-float path is not selected, no alternate formula or
correlation fallback is attempted, no partial HTC is emitted, and HTC=0 is
never returned as a substitute for failure. The existing frozen formula
calculation blocker is used; no new blocker spelling is introduced.

### 8.2 Fractional-power identity and operation order

```text
FRACTIONAL_POWER_ALGORITHM=DECIMAL_LN_EXP_RATIONAL_EXPONENT_V1
RE_EXPONENT_EXACT_RATIONAL=11/20
PR_EXPONENT_EXACT_RATIONAL=1/3
MATH_MODULE_POWER=false
BUILTIN_FLOAT_POWER=false
BINARY_FLOAT_TRANSCENDENTAL=false
```

Exact operation order:

```text
re_ln       = context.ln(Re_s)
re_exp_arg  = context.divide(context.multiply(re_ln, Decimal(11)), Decimal(20))
re_pow      = context.exp(re_exp_arg)

pr_ln       = context.ln(Pr_s)
pr_exp_arg  = context.divide(pr_ln, Decimal(3))
pr_pow      = context.exp(pr_exp_arg)

prefactor_1 = context.multiply(Decimal("0.36"), k_s)
prefactor   = context.divide(prefactor_1, D_e)
h_partial   = context.multiply(prefactor, re_pow)
h_raw       = context.multiply(h_partial, pr_pow)
h_public    = quantize(h_raw, Decimal("0.0001"), ROUND_HALF_EVEN)
```

```text
PUBLIC_QUANTIZATION_LAST=true
NEGATIVE_ZERO_NORMALIZATION=true
TRAILING_ZERO_POLICY=PRESERVE_QUANTUM_SCALE
HTC_OUTPUT_QUANTUM=Decimal("0.0001")
```

A positive finite `h_raw` that quantizes to zero is blocked with the frozen
quantization-collision semantics; zero is never returned as a substitute for
failed/under-resolved HTC.

## 9. Public result contract

```text
PUBLIC_WRAPPER_TYPE=ShellSideHeatTransferValidationResult
SUCCESS_PAYLOAD_FIELD=heat_transfer
TYPED_BLOCKED_PAYLOAD_FIELD=blocked_result
RAW_BOUNDARY_BLOCKED_PAYLOAD_FIELD=raw_boundary_blocked_result

SUCCESS_RESULT_TYPE=ShellSideHeatTransferResult
SUCCESS_RESULT_SCHEMA_VERSION=task033.shell-side-heat-transfer.v1
SUCCESS_RESULT_FIELD_COUNT=28
```

Exact success field order:

```text
schema_version
profile_id
first_slice_profile_id
implementation_software_version
shell_side_case_id
shell_side_stream_id
shell_side_fluid_id
task020_configuration_id
task020_configuration_hash
task031_geometry_id
task031_geometry_hash
property_snapshot_hash
mass_flow_authority_hash
task032_request_hash
task032_result_hash
task032_result_id
correlation_id
engineering_source_authority_record_id
heat_transfer_surface
modeled_shell_side_heat_transfer_coefficient_w_m2_k
request_hash
result_hash
result_id
warnings
blockers
deferred_capabilities
applicability_context
provenance
```

On success:

```text
SUCCESS_BLOCKERS_EXACTLY_EMPTY=true
PUBLIC_NUSSELT_FIELD=false
correlation_id=TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1
engineering_source_authority_record_id=5387111841
heat_transfer_surface=OUTER_TUBE_SURFACE
```

## 10. Blocked-result contracts and fail-closed behavior

### 10.1 Typed blocked result

```text
TYPED_BLOCKED_RESULT_TYPE=ShellSideHeatTransferBlockedResult
TYPED_BLOCKED_RESULT_SCHEMA_VERSION=task033.shell-side-heat-transfer-blocked.v1
TYPED_BLOCKED_RESULT_FIELD_COUNT=22
PARTIAL_HEAT_TRANSFER_RESULT=false
BLOCKED_HTC_FIELD_PRESENT=false
```

The typed-blocked result has this exact field order:

```text
TYPED_BLOCKED_RESULT_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  failure_stage,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  request_hash,
  blocked_result_hash,
  warnings,
  blockers,
  deferred_capabilities,
  provenance,
)
TYPED_BLOCKED_RESULT_FIELD_COUNT=22
PARTIAL_HEAT_TRANSFER_RESULT=false
BLOCKED_HTC_FIELD_PRESENT=false
```

Typed blocked identity fields that are not yet verified at the failure stage
are represented as explicit `str | None` tagged unions; no guessed identity
text or default identity is permitted.

### 10.2 Raw-boundary blocked result

```text
RAW_BOUNDARY_BLOCKED_RESULT_TYPE=ShellSideHeatTransferRawBoundaryBlockedResult
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION=task033.shell-side-heat-transfer-raw-boundary-blocked.v1
RAW_BOUNDARY_BLOCKED_RESULT_FIELDS=(
  schema_version,
  profile_id,
  request_hash,
  blocked_result_hash,
  blockers,
  warnings,
  deferred_capabilities,
  raw_projection
)
RAW_BOUNDARY_BLOCKED_RESULT_FIELD_COUNT=8
PARTIAL_HEAT_TRANSFER_RESULT=false
BLOCKED_HTC_FIELD_PRESENT=false
```

No blocked path may expose a plausible HTC. Specifically:

```text
PARTIAL_SUCCESS_RESULT=false
PARTIAL_HEAT_TRANSFER_RESULT=false
FAILED_HTC_AS_ZERO=false
MISSING_WALL_PROPERTY_AS_RATIO_ONE=false
UNSUPPORTED_CORRELATION_DOMAIN_AS_FALLBACK=false
```

## 11. Canonicalization and identity graph

TASK-033 uses the frozen repository primitive kind/framing discipline with
TASK-033-specific top-level namespaces:

Frozen canonical kind tags are part of the byte contract:

```text
NULL_KIND=b"n"
BOOL_KIND=b"b"
INTEGER_KIND=b"i"
STRING_KIND=b"s"
DECIMAL_KIND=b"d"
STRING_TUPLE_KIND=b"t"
STRING_MAPPING_KIND=b"m"
PROPERTY_SNAPSHOT_KIND=b"p"
MASS_FLOW_AUTHORITY_KIND=b"a"
TASK031_RESULT_KIND=b"h"
BLOCKER_TUPLE_KIND=b"k"
BLOCKER_ENTRY_KIND=b"c"
TASK032_FLOW_STATE_KIND=b"f"
TASK032_REQUEST_EVIDENCE_KIND=b"q"
PROVENANCE_KIND=b"v"
```

These are frozen canonical byte-contract values, not implementation
suggestions. Existing hash namespaces, UUID namespace, name prefix, and
self-exclusions remain unchanged.

```text
REQUEST_HASH_NAMESPACE=b"task033.request.v1"
SUCCESS_RESULT_HASH_NAMESPACE=b"task033.success-result.v1"
TYPED_BLOCKED_RESULT_HASH_NAMESPACE=b"task033.typed-blocked-result.v1"
RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=b"task033.raw-boundary-blocked-result.v1"
PROVENANCE_HASH_NAMESPACE=b"task033.provenance.v1"
RAW_PROJECTION_HASH_NAMESPACE=b"task033.raw-projection.v1"
HASH_ALGORITHM=SHA-256
```

Success ID derivation:

```text
RESULT_ID_ALGORITHM=UUID5
RESULT_ID_NAMESPACE=6d4de79e-3e04-5160-93e4-725c3f308a22
RESULT_ID_NAME_PREFIX=task033-shell-side-heat-transfer-id.v1:
RESULT_ID_NAME=RESULT_ID_NAME_PREFIX + result_hash
```

Self-exclusions:

```text
SUCCESS_RESULT_HASH_SELF_EXCLUSIONS=(result_hash,result_id)
TYPED_BLOCKED_RESULT_HASH_SELF_EXCLUSIONS=(blocked_result_hash,)
RAW_BOUNDARY_BLOCKED_RESULT_HASH_SELF_EXCLUSIONS=(blocked_result_hash,)
PROVENANCE_HASH_SELF_EXCLUSIONS=(provenance_hash,)
```

Identity finalization is acyclic: upstream replay first, request hash next,
provenance hash where applicable, result/blocked hash next, then success UUID.
Runtime clock/random identity, unordered set serialization, `repr`-based
canonicalization, locale formatting, binary floats, object-address strings,
and tolerance/hash repair are forbidden.

## 12. Provenance and raw projection

The frozen provenance record is an exact 30-field record. It is not a minimum
set: extra provenance fields are forbidden.

```text
PROVENANCE_FIELD_COUNT=30
PROVENANCE_FIELD_SET_EXACT=true
PROVENANCE_EXTRA_FIELDS_ALLOWED=false
PROVENANCE_FIELD_ORDER_CANONICAL=true

PROVENANCE_FIELDS=(
  task_id,
  design_contract_path,
  implementation_software_version,
  request_hash,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  correlation_id,
  engineering_source_authority_record_id,
  source_id,
  source_doi,
  source_location,
  heat_transfer_surface,
  value_authority_replay_model,
  fractional_power_algorithm,
  warnings,
  deferred_capabilities,
  evidence_refs,
  source_definition_issue,
  engineering_source_correlation_freeze_comment_id,
  provenance_hash,
)

task_id=TASK033
design_contract_path=docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md
engineering_source_correlation_freeze_comment_id=5387111841
correlation_id=TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1
source_id=SRC-INTECHOPEN-100450-KHARAJI-2021
source_doi=10.5772/intechopen.100450
source_location=Section_4.4_Shell_diameter_Equation_58
heat_transfer_surface=OUTER_TUBE_SURFACE
value_authority_replay_model=REPLAY_EXACT_ACCEPTED_TASK032_REQUEST
fractional_power_algorithm=DECIMAL_LN_EXP_RATIONAL_EXPONENT_V1
```

Raw-boundary projection is bounded and deterministic. Projection values are
canonical kind/type tokens plus safely extracted lexical values only.

```text
RAW_PROJECTION_FIELDS=(
  top_level_type,
  sorted_top_level_keys,
  schema_version_projection,
  profile_id_projection,
  task032_flow_state_type,
  task032_request_evidence_type,
  evidence_refs_projection,
)
RAW_PROJECTION_FIELD_COUNT=7
```

`repr(raw_request)`, object-address serialization, arbitrary exception
messages, iteration-order-dependent representation, and unbounded recursive
serialization are forbidden. Raw projection may use only canonical kind/type
tokens and safely extracted lexical values.

## 13. Closed blocker/warning/deferred registries

### 13.1 Blockers — exact closed order, 29 codes

```text
SSHT_SCHEMA_VERSION_UNSUPPORTED
SSHT_PROFILE_ID_UNSUPPORTED
SSHT_RAW_TYPE_INVALID
SSHT_UNKNOWN_FIELD
SSHT_EVIDENCE_REFS_INVALID
SSHT_TASK032_FLOW_STATE_MISSING
SSHT_TASK032_FLOW_STATE_INVALID
SSHT_TASK032_REQUEST_EVIDENCE_MISSING
SSHT_TASK032_REQUEST_EVIDENCE_INVALID
SSHT_TASK032_REQUEST_HASH_MISMATCH
SSHT_TASK032_RESULT_HASH_MISMATCH
SSHT_TASK032_RESULT_ID_MISMATCH
SSHT_TASK031_GEOMETRY_REPLAY_MISMATCH
SSHT_PROPERTY_SNAPSHOT_HASH_MISMATCH
SSHT_MASS_FLOW_AUTHORITY_HASH_MISMATCH
SSHT_SAME_CASE_BINDING_MISMATCH
SSHT_PHASE_UNSUPPORTED
SSHT_RHEOLOGY_MODEL_UNSUPPORTED
SSHT_PROPERTY_STATE_ROLE_UNSUPPORTED
SSHT_FLOW_REGION_UNSUPPORTED
SSHT_REYNOLDS_OUTSIDE_CORRELATION_DOMAIN
SSHT_CORRELATION_AUTHORITY_IDENTITY_MISMATCH
SSHT_FORMULA_INPUT_DOMAIN_VIOLATION
SSHT_FRACTIONAL_POWER_CALCULATION_FAILED
SSHT_FORMULA_CALCULATION_FAILED
SSHT_PUBLIC_HTC_QUANTIZATION_COLLISION
SSHT_CANONICALIZATION_FAILED
SSHT_RESULT_IDENTITY_FINALIZATION_FAILED
SSHT_PARTIAL_RESULT_FORBIDDEN
```

### 13.2 Warnings — exact closed order, 5 codes

```text
SSHT_KERN_SCREENING_MODEL_ONLY
SSHT_IDEALIZED_SHELL_FLOW_ASSUMPTION
SSHT_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED
SSHT_NO_FLOW_REGIME_CLASSIFICATION
SSHT_NO_FULL_EXCHANGER_RATING_CLAIM
```

### 13.3 Deferred capabilities — exact closed order, 16 tokens

```text
FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE
SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE
SHELL_SIDE_FRICTION_FACTOR_NOT_COMPUTABLE
LEAKAGE_CORRECTIONS_NOT_COMPUTABLE
BYPASS_CORRECTIONS_NOT_COMPUTABLE
BELL_DELAWARE_NOT_COMPUTABLE
WALL_TEMPERATURE_ITERATION_NOT_COMPUTABLE
WALL_VISCOSITY_CORRECTION_NOT_COMPUTABLE
AREA_BASIS_CONVERSION_NOT_COMPUTABLE
OVERALL_U_NOT_COMPUTABLE
UA_NOT_COMPUTABLE
LMTD_NOT_COMPUTABLE
HEAT_DUTY_NOT_COMPUTABLE
OUTLET_TEMPERATURES_NOT_COMPUTABLE
FULL_EXCHANGER_RATING_NOT_COMPUTABLE
THERMAL_SIZING_NOT_COMPUTABLE
```

Registry order is semantic/canonical order. Unknown runtime tokens are
rejected rather than appended dynamically.

## 14. Validation stage order

```text
TASK033_VALIDATION_STAGE_ORDER=(
  RAW_BOUNDARY,
  REQUEST_SCHEMA,
  UPSTREAM_TYPED_BOUNDARY,
  TASK032_RESULT_IDENTITY,
  TASK032_REQUEST_REPLAY,
  TASK031_GEOMETRY_REPLAY,
  PROPERTY_SNAPSHOT_REPLAY,
  MASS_FLOW_AUTHORITY_REPLAY,
  SAME_CASE_BINDING,
  CORRELATION_AUTHORITY_AND_APPLICABILITY,
  ENGINEERING_INPUT_DOMAIN,
  HTC_EVALUATION,
  PUBLIC_QUANTIZATION,
  PROVENANCE_CANONICALIZATION,
  RESULT_IDENTITY_FINALIZATION
)
TASK033_VALIDATION_STAGE_COUNT=15
```

No downstream stage may manufacture missing identities for an earlier failed
stage. Engineering starts only after all upstream identity, same-case,
correlation-authority, applicability, and input-domain checks succeed.

## 15. Implementation architecture boundary — future gate only

This design does **not** authorize implementation. If implementation is later
separately authorized, the frozen production-source allowlist is exactly:

```text
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/__init__.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/authority.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/blocker_registry.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/canonical.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/decimal_quantization.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/engineering_authority_snapshot.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/formulas.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/models.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/provenance.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/raw_projection.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/schema.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/validation.py
src/hexagent/exchangers/shell_tube/shell_side_heat_transfer/warning_registry.py
```

```text
TASK033_PRODUCTION_SOURCE_ALLOWLIST_PATH_COUNT=13
UPSTREAM_TASK020_TASK031_TASK032_SOURCE_MUTATION_ALLOWED=false
```

Future complete implementation mutation boundary additionally includes:

```text
TASK033_TEST_ROOT=tests/exchangers/shell_tube/shell_side_heat_transfer/
TASK033_CI_MANIFEST_MUTATION_PATH=ci-shard-manifest.yml
CI_MANIFEST_MUTATION_REQUIRED=true
TASK033_TEST_FILES_MUST_BE_EXPLICITLY_ENUMERATED=true
CI_SHARD_TARGET=ci
CI_PYTHON_VERSIONS=(3.11,3.12)
GITHUB_WORKFLOW_MUTATION_REQUIRED=false
```

## 16. Required implementation test contract — future gate only

Frozen test semantics:

```text
T033-001_RAW_TYPE_INVALID
T033-002_REQUIRED_FIELD_MISSING
T033-003_UNKNOWN_FIELD_REJECTED
T033-004_SCHEMA_VERSION_MISMATCH
T033-005_PROFILE_ID_MISMATCH
T033-006_TASK032_FLOW_STATE_TYPE_INVALID
T033-007_TASK032_RESULT_HASH_MISMATCH
T033-008_TASK032_RESULT_ID_MISMATCH
T033-009_TASK032_REQUEST_EVIDENCE_MISSING
T033-010_TASK032_REQUEST_HASH_MISMATCH
T033-011_TASK031_GEOMETRY_REPLAY_MISMATCH
T033-012_PROPERTY_SNAPSHOT_HASH_MISMATCH
T033-013_MASS_FLOW_AUTHORITY_HASH_MISMATCH
T033-014_SAME_CASE_BINDING_MISMATCH
T033-015_UPSTREAM_APPLICABILITY_MISMATCH
T033-016_FLOW_REGION_MISMATCH
T033-017_REYNOLDS_LOWER_BOUND_EXCLUSIVE
T033-018_REYNOLDS_UPPER_BOUND_EXCLUSIVE
T033-019_NOMINAL_SINGLE_PHASE_LIQUID
T033-020_NOMINAL_SINGLE_PHASE_GAS
T033-021_RE_EXPONENT_11_OVER_20
T033-022_PR_EXPONENT_1_OVER_3
T033-023_FORMULA_INPUT_DOMAIN
T033-024_FRACTIONAL_POWER_FAILURE
T033-025_HTC_PUBLIC_QUANTIZATION_AND_NEGATIVE_ZERO
T033-026_SUCCESS_IDENTITY_REPEATABILITY
T033-027_TYPED_BLOCKED_IDENTITY_REPEATABILITY
T033-028_RAW_BLOCKED_PROJECTION_IDENTITY_REPEATABILITY
T033-029_PROVENANCE_IDENTITY_REPEATABILITY
T033-030_PY311_PY312_CANONICAL_BYTE_IDENTITY
TASK033_REQUIRED_TEST_ID_COUNT=30
```

The implementation test suite must cover architecture, upstream authority
replay, canonicalization, formula evaluation, models, raw boundary,
validation, registry closure, external vectors, repeat-run determinism, and
cross-version identity.

## 17. External oracle and cross-version identity contract

```text
EXTERNAL_ORACLE_VECTOR_COUNT=12
EXTERNAL_ORACLE_RUNTIME_DEPENDENCY=false
EXTERNAL_ORACLE_MINIMUM_DECIMAL_DIGITS=80
EXPECTED_OUTPUT_DERIVED_PRODUCTION_FORMULA=false
```

Engineering oracle validation (D29) is distinct from canonical identity
validation (D30).

```text
SOURCE_DEFINITION_FREEZE_REQUIRES_EXECUTED_TASK033_PRODUCTION_XPY_EVIDENCE=false
SOURCE_DEFINITION_FREEZES_XPY_TEST_CONTRACT=true
IMPLEMENTATION_ACCEPTANCE_REQUIRES_PY311_PY312_BYTE_IDENTITY=true
PR_ACCEPTANCE_REQUIRES_PY311_PY312_BYTE_IDENTITY=true
MERGE_ACCEPTANCE_REQUIRES_PY311_PY312_BYTE_IDENTITY=true

CROSS_VERSION_COMPARISON_MODEL=SHARED_FROZEN_EXPECTED_CANONICAL_VECTOR_BYTES_V1
PY311_OUTPUT_MUST_EQUAL_FROZEN_EXPECTED=true
PY312_OUTPUT_MUST_EQUAL_FROZEN_EXPECTED=true
PY311_OUTPUT_MUST_EQUAL_PY312_OUTPUT=true
PY_VERSION_IDENTITY_PROBE_COUNT=12
D30_TOLERANCE_ACCEPTANCE=false
CANONICAL_BYTE_TOLERANCE=false
HASH_TOLERANCE=false
UUID_TOLERANCE=false
```

A same-interpreter repeat run is necessary but is not cross-version proof.
Python 3.11 and Python 3.12 must independently produce the same frozen probe
outputs and each must equal the shared expected canonical artifact.

## 18. Design invariants

Any conforming implementation must preserve all of the following:

```text
ONE_PRODUCTION_CORRELATION_ONLY=true
NO_RUNTIME_CORRELATION_SELECTION=true
NO_RUNTIME_FALLBACK=true
NO_WALL_PROPERTY_REQUIRED=true
NO_IMPLICIT_WALL_DEFAULTS=true
OUTER_TUBE_SURFACE_ONLY=true
NO_AREA_BASIS_CONVERSION=true
DIRECT_UPSTREAM_TASK032_ONLY=true
NO_TASK031_OR_TASK032_ENGINEERING_RECOMPUTATION=true
TASK032_REQUEST_REPLAY_REQUIRED=true
TASK032_RESULT_IDENTITY_REPLAY_REQUIRED=true
NO_TASK032_PRIVATE_IMPORT_DEPENDENCY=true
DECIMAL_ONLY_ENGINEERING=true
PUBLIC_QUANTIZATION_LAST=true
NO_PARTIAL_HTC=true
NO_FAILED_HTC_AS_ZERO=true
STRICT_REYNOLDS_BOUNDS=true
NO_FLOW_REGIME_CLASSIFICATION=true
NO_TASK034_PRESSURE_DROP_PHYSICS=true
NO_TASK035_COMPOSITION_PHYSICS=true
```

## 19. Lifecycle stop and next independent gate

The R2 correction is recorded, and the design remains unfrozen pending the
next independent R3 review.

```text
TASK033_SOURCE_DEFINITION_FROZEN=true
TASK033_DESIGN_AUTHORIZED=true
TASK033_DESIGN_DOCUMENT_AUTHORED=true
TASK033_DESIGN_CORRECTION_R2_RECORDED=true
TASK033_DESIGN_FROZEN=false
TASK033_IMPLEMENTATION_AUTHORIZED=false
REPOSITORY_PRODUCTION_CODE_MUTATION_AUTHORIZED=false
PULL_REQUEST_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
ISSUE_CLOSE_AUTHORIZED=false
TASK034_AUTHORIZED=false
TASK035_AUTHORIZED=false
TASK036_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK033_DESIGN_INDEPENDENT_REVIEW_R3_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

Recommended next independent gate after this correction:

```text
AUTHORIZE_TASK033_DESIGN_INDEPENDENT_REVIEW_R3_ONLY
```

That future gate is review-only. It must not modify this design, freeze the
design, authorize implementation, create a PR, or advance TASK-034 without a
separate explicit authorization. `NEXT_GATE_AUTHORIZED=false`.
