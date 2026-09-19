# TASK172 — model-level constant-k qualification authority R1

## 1. Receipt and immutable boundary

This is a documentation-only authority package for Draft PR277. It closes a
model-level contract gap without selecting a real material, assigning a
conductivity value to a project case, implementing a property evaluator, or
starting TASK172 production implementation.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_CONSTANT_K_QUALIFICATION_R1
PR=277
PREVIOUS_HEAD_SHA=02674fd897f5d688910babf51ea1ff541c48c63d
MODE=CONTROLLED_CONSTANT_K_AUTHORITY_QUALIFICATION_ONLY
DOCUMENT_STATUS=PROPOSED_AUTHORITY
AUTHORITY_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
AUTHORITY_VERSION=r1
CONSTANT_K_QUALIFICATION_MODE=CASE_LEVEL_AUTHORITY_REQUIRED
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The package separates three layers:

```text
MaterialIdentityAuthority
        → MaterialThermalPropertyAuthority
        → ConstantKQualificationAuthority
```

`MATERIAL_PROFILE_ID=NONE` remains correct. This proposal defines the
requirements for a future case-level authority; it is not a material
instance and is not production approval. `PROPOSED_AUTHORITY` is retained
until an independent reviewer evaluates this package.

The historical material-identity contract, material-property contract, and
reviewed wall-temperature-state contract are append-only upstream inputs.
Their identities and meanings are not rewritten here.

## 2. Scope and authority decision

The generic TASK172 kernel may admit a constant wall conductivity only when a
case transports a complete, source-bound qualification record. The kernel
does not own a material catalog and does not infer a material from a grade,
geometry, legacy field, or library availability.

The initial decision is deliberately the strict case-level mode:

```ini
CONSTANT_K_QUALIFICATION_MODE=CASE_LEVEL_AUTHORITY_REQUIRED
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_CONSTANT_K_STATUS=CLOSED
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=true
CONSTANT_K_MODEL_AUTHORIZED=true
PRODUCTION_ADMISSION_WITHOUT_CASE_AUTHORITY=false
```

`CLOSED` here means that the model-level admission contract is complete. It
does not mean that any case material is approved or that the wall state has
been solved. A future case without the required authority remains blocked.

The contract applies only to the solid tube wall metal quantity:

```ini
PROPERTY_QUANTITY_KIND=SOLID_THERMAL_CONDUCTIVITY
COMPONENT_SCOPE=TUBE_WALL_METAL
PROPERTY_UNITS=W_PER_M_K
WALL_TEMPERATURE_STATE_MODEL_ID=V07-T172-CLEAN-RADIAL-WALL-STATE-R1
```

This package does not create a shell-metal material contract, a fouling
property, a fluid property, an HTC, a viscosity correction, or a numerical
tolerance.

## 3. Required authority layers

### 3.1 Layer A — material identity

Every case must bind the reviewed input contract
`V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1` by both ID and hash. The
identity record must identify the component material and its source. A grade
name alone is not a thermal property.

The following remain forbidden:

```ini
HIDDEN_DEFAULT_MATERIAL_FORBIDDEN=true
LEGACY_K_REUSE_FORBIDDEN=true
MATERIAL_ID_ONLY_AS_PROPERTY_FORBIDDEN=true
RUNTIME_MATERIAL_DATABASE_LOOKUP=FORBIDDEN
```

No material grade is selected by this task. In particular, no stainless
steel, carbon steel, copper, titanium, or other customary material is a
default.

### 3.2 Layer B — material thermal-property body

Every case must bind
`V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1` by the exact
authority identity and hash. The property body must be present and must
declare:

```text
property_quantity_kind = SOLID_THERMAL_CONDUCTIVITY
component_scope = TUBE_WALL_METAL
property_model = FIXED_SOURCE_VALUE or SOURCE_BOUND_K_OF_T
value or complete source curve/table
units and absolute temperature basis
source-qualified temperature domain
source/provenance and rights
case/configuration and physical-support binding
interpolation/extrapolation/out-of-domain policy
```

The body, source revision, case binding, geometry binding and evidence are
part of the authority identity. Transporting this body through a caller
request is not approval.

### 3.3 Layer C — constant-k qualification

The new authority is the model-level contract for a separate
`ConstantKQualificationAuthority`. It may authorize a constant value only
through an explicit case record containing the fields in §4. The case record
must reference both Layer A and Layer B; a naked `constant_k_value` is
invalid.

The initial contract authorizes only these two semantically distinct cases:

1. A `FIXED_SOURCE_VALUE` body whose source explicitly declares the value,
   its basis, and its applicable temperature domain. The selected constant is
   exactly that source-declared value after an explicit unit conversion.
2. A separately reviewed future authority that explicitly defines a
   source-backed constant representation and its qualification rule. That
   future authority is not created here.

For a `SOURCE_BOUND_K_OF_T` body, this R1 contract does **not** average,
sample, interpolate, use a midpoint, use a room-temperature point, or select
the nearest table row. Conversion from `k(T)` to a constant approximation is
not admitted by this package and requires a separate authority with an
explicit approximation-error rule.

## 4. ConstantKQualificationAuthority record

The following is the required case-level record. Fields marked
`CASE_REQUIRED` are intentionally absent from this generic proposal; null or
absent values at runtime are blocking, not defaults.

```text
schema_version
authority_id
authority_version
review_status

material_identity_authority_id
material_identity_authority_hash
material_thermal_property_authority_id
material_thermal_property_authority_hash

component_scope
case_or_configuration_binding
geometry_binding
property_quantity_kind
source_property_model
source_temperature_domain

constant_k_model_authorized
constant_k_value                  CASE_REQUIRED
constant_k_unit                   CASE_REQUIRED
qualification_temperature_min_K  CASE_REQUIRED
qualification_temperature_max_K  CASE_REQUIRED

evaluation_or_selection_rule
qualification_method
qualification_metric
qualification_acceptance_rule

interpolation_policy
extrapolation_policy
out_of_domain_policy

wall_temperature_state_authority_id
wall_temperature_state_coverage
source_provenance
evidence_refs
authority_hash
```

The required bindings are:

```text
component_scope:
  exact value TUBE_WALL_METAL

case_or_configuration_binding:
  task172_case_id
  task172_request_id
  task172_request_hash
  configuration_authority_id
  configuration_authority_hash
  upstream_identity_refs
  binding_rule_revision

geometry_binding:
  component_role
  geometry_authority_id
  geometry_authority_hash
  physical_support_id
  physical_support_hash
  upstream_geometry_identity_refs

source_provenance:
  source_id
  source_version_or_revision
  source_location
  source_class
  permission_status
  evidence_refs
```

`constant_k_value` is in `W_PER_M_K`. It is a required case field, never a
repository default. The qualification interval is an absolute material-wall
temperature interval in kelvin, not a bulk-temperature interval.

## 5. Wall-temperature domain binding

The effective qualified interval must cover every material-wall state used by
the reviewed clean radial wall model. The relevant coverage set is:

```text
TUBE_METAL_INNER_SURFACE for every admitted physical support/segment
TUBE_METAL_OUTER_SURFACE for every admitted physical support/segment
```

For a case with wall-state temperatures `T_wall,s`, admission requires, for
every required state `s`:

```text
qualification_temperature_min_K <= T_wall,s
T_wall,s <= qualification_temperature_max_K
```

Equivalently, when all required states are finite and present, the interval
must cover the minimum and maximum of the complete state set. Coverage must
be checked against the wall-temperature state identity and physical support;
it may not be checked against only an inlet, outlet, bulk, mean, ambient, or
convenient surface temperature.

```ini
CONSTANT_K_DOMAIN_COVERAGE_REQUIRED=true
BULK_TEMPERATURE_SUBSTITUTION_FORBIDDEN=true
WALL_STATE_COVERAGE_SET_COMPLETE_REQUIRED=true
CONSTANT_K_OUT_OF_DOMAIN_POLICY=BLOCKED
```

No extrapolation is admitted. A future coupled wall/property iteration that
would leave this interval must fail closed. It must not continue with the
last in-domain value or silently widen the interval.

The binding is to the reviewed wall-state authority
`V07-T172-CLEAN-RADIAL-WALL-STATE-R1`, whose clean initial scope has two
distinct surface states. The inner and outer states cannot be collapsed into
one scalar for coverage purposes.

## 6. Source model and qualification rules

### 6.1 Exact fixed source value

The only constant representation admitted by this R1 package is an exact
source-declared fixed value. The source property body must say that the value
applies to the component and the declared temperature domain. The selection
rule is:

```text
selected constant k = source-declared fixed k value
```

after a source-documented unit conversion, if one is explicitly required.
There is no averaging, rounding beyond the source representation, or
substitution from another source.

The model-level acceptance rule is therefore semantic and source-bound, not a
new numerical tolerance:

```text
ACCEPT iff
  the reviewed property body is FIXED_SOURCE_VALUE
  AND the source explicitly qualifies the value for the complete declared
      wall-temperature domain
  AND material identity, component, geometry, case, provenance and hashes
      all match
  AND every required wall state is within that domain.
```

Otherwise the case is `BLOCKED`.

### 6.2 k(T) source body

`SOURCE_BOUND_K_OF_T` remains a valid Layer B property representation, but it
is not converted into constant k by this authority. A source curve endpoint,
midpoint, average, nearest row, or one room-temperature checkpoint cannot be
called a constant qualification. Such a conversion requires a new,
independently reviewed case authority that binds its own source-defined
selection and approximation acceptance rule.

```ini
K_OF_T_TO_CONSTANT_CONVERSION=NOT_ADMITTED_BY_R1
CONSTANT_APPROXIMATION_ERROR_AUTHORITY=NOT_CREATED
```

### 6.3 Qualification method and metric

The method is `SOURCE_EXPLICIT_FIXED_VALUE_DOMAIN_COVERAGE`. The metric is the
exact boolean coverage of the complete wall-state set by the source-declared
interval, together with exact source-value identity. It is not a fabricated
percentage error, an RSS uncertainty, a solver tolerance, or a correlation
acceptance band.

```ini
CONSTANT_K_QUALIFICATION_METHOD_BOUND=true
CONSTANT_K_QUALIFICATION_METRIC_BOUND=true
CONSTANT_K_QUALIFICATION_ACCEPTANCE_RULE_BOUND=true
CONSTANT_K_SELECTION_RULE_BOUND=true
```

No numerical error budget is introduced. Physical property uncertainty,
model approximation error and numerical convergence error remain separate
future authorities.

## 7. Interpolation, extrapolation and fail-closed rules

```ini
CONSTANT_K_INTERPOLATION_POLICY_BOUND=true
CONSTANT_K_INTERPOLATION_POLICY=EXPLICIT_SOURCE_RULE_REQUIRED
CONSTANT_K_EXTRAPOLATION_POLICY_BOUND=true
CONSTANT_K_EXTRAPOLATION_POLICY=FORBIDDEN
CONSTANT_K_OUT_OF_DOMAIN_POLICY=BLOCKED
```

For the exact fixed-value path, no interpolation is needed. If a source
explicitly defines a permitted representation operation, the case record
must reproduce that operation and its source domain. Without that source
rule, the operation is forbidden. The R1 contract never treats a backend or a
property library as an engineering permission.

Future admission must reject all of the following:

| Condition | Required result |
| --- | --- |
| missing material identity authority or hash | `BLOCKED / REQUIRED_AUTHORITY_MISSING` |
| missing material property body | `BLOCKED / MATERIAL_PROPERTY_BODY_REQUIRED` |
| missing constant-k qualification record | `BLOCKED / CONSTANT_K_AUTHORITY_MISSING` |
| identity/hash mismatch at any layer | `BLOCKED / UPSTREAM_IDENTITY_MISMATCH` |
| component or physical-support mismatch | `BLOCKED / INVALID_MATERIAL_BINDING` |
| source, rights or evidence incomplete | `BLOCKED / PROVENANCE_INVALID` |
| unreviewed case authority at production boundary | `BLOCKED / AUTHORITY_NOT_REVIEWED` |
| `SOURCE_BOUND_K_OF_T` without a separate constant authority | `BLOCKED / CONSTANT_K_MODEL_NOT_AUTHORIZED` |
| incomplete inner/outer wall-state coverage | `BLOCKED / WALL_STATE_COVERAGE_INCOMPLETE` |
| wall state outside qualified interval | `BLOCKED / CONSTANT_K_OUT_OF_DOMAIN` |
| attempted extrapolation | `BLOCKED / CONSTANT_K_EXTRAPOLATION_FORBIDDEN` |
| legacy conductivity token or hidden material default | `BLOCKED / LEGACY_K_REUSE_FORBIDDEN` |
```

No condition returns a valid constant k from a caller assertion, a missing
field, or a last numerical iterate.

## 8. Canonical identity and provenance

The authority uses the existing shared serializer
`hexagent.canonical_json.canonical_sha256`. The hash preimage excludes only
the shared `canonical_hash` field and includes the complete model/case
contract:

```text
schema and authority version
Layer A and Layer B IDs and hashes
component, case, configuration and geometry bindings
property model and constant value/unit fields
qualified temperature bounds
wall-temperature authority and complete coverage rule
selection/method/metric/acceptance rules
interpolation/extrapolation/out-of-domain policy
source, rights, evidence and provenance identities
review and production-admission fields
```

The following must change the recomputed identity:

```ini
SAME_HASH_DIFFERENT_CONSTANT_K_BODY=BLOCKED
CONSTANT_K_BODY_HASH_MISMATCH=BLOCKED
MATERIAL_IDENTITY_HASH_CHANGE_CHANGES_IDENTITY=true
SOURCE_REVISION_CHANGE_CHANGES_IDENTITY=true
WALL_STATE_AUTHORITY_CHANGE_CHANGES_IDENTITY=true
QUALIFIED_DOMAIN_CHANGE_CHANGES_IDENTITY=true
CASE_OR_GEOMETRY_REBIND_CHANGES_IDENTITY=true
```

The provenance graph is acyclic:

```text
reviewed TASK170/TASK171 and material input contracts
    → case material identity
    → case material property body
    → reviewed wall-temperature state authority
    → case-level constant-k qualification
    → future property/wall consumer
```

This package creates no producer, does not promote a caller assertion, and
does not replace an absent material authority.

## 9. Interaction with wall state and active corrections

The wall-state authority is already reviewed for TASK172 entry, but its
actual state is not solved. The constant-k contract therefore binds the
future state identity without defining a solver:

```ini
WALL_TEMPERATURE_STATE_AUTHORITY_ID=V07-T172-WALL-TEMPERATURE-STATE-R1
WALL_TEMPERATURE_STATE_ACTUAL_SOLVED=false
WALL_TEMPERATURE_STATE_COVERAGE_REQUIRED=true
```

The clean radial network remains conditional on a qualified material body and
qualified films. No fouling/contact layer, axial conduction model, wall
correction, property adapter, or iteration method is introduced here.

Both active wall corrections remain independent blockers. Material k is a
prerequisite for the radial wall resistance used by both consumers, but this
task neither authorizes nor implements either correction:

```ini
TUBE_WALL_CORRECTION_MATERIAL_K_PREREQUISITE=true
SHELL_WALL_CORRECTION_MATERIAL_K_PREREQUISITE=true
TUBE_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_STATUS=BLOCKED
```

The existing coupled-cycle classification is preserved. This package does
not select Newton, Picard, fixed-point, Brent, bisection, relaxation,
initialization, residual thresholds, iteration limits, mesh rules, or
numerical tolerances.

## 10. Review boundary and remaining gates

The authority status is intentionally still a proposal:

```ini
TASK172_MATERIAL_CONSTANT_K_QUALIFICATION_PROPOSED=true
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=PROPOSED_AUTHORITY
APPROVED_BY=
APPROVAL_EVIDENCE=[]
NEW_AUTHORITY_SELF_APPROVAL=false
```

If an independent reviewer accepts the model-level contract, the canonical
material blocker can be removed even though `MATERIAL_PROFILE_ID=NONE`:

```ini
MATERIAL_CONSTANT_K_STATUS=CLOSED
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=true
```

That review would not approve any future material case. The five remaining
TASK172 entry blockers are:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
TASK172_ENTRY_DEPENDENCY_BLOCKERS=NONE
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

The next gate is an independent review of this model-level contract, not
material selection and not implementation:

```ini
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_CONSTANT_K_AUTHORITY_INDEPENDENT_REVIEW_R1_ONLY
```

## 11. Verification receipt

The machine-readable evidence file
`evidence/TASK-172-constant-k-qualification-r1.json` records the same
contract, its canonical authority hash, source/contract bindings, fail-closed
cases and the absence of an actual material instance. The append-only
registry extension binds this document and evidence file by SHA-256 without
rewriting earlier R1–R9 records.

```ini
RESULT=PASS_WITH_REMAINING_GAPS
CONSTANT_K_QUALIFICATION_CONTRACT_FROZEN=true
CONSTANT_K_SOURCE_BINDING_RULE_BOUND=true
CONSTANT_K_SELECTION_RULE_BOUND=true
CONSTANT_K_TEMPERATURE_DOMAIN_RULE_BOUND=true
CONSTANT_K_WALL_STATE_BINDING_RULE_BOUND=true
CONSTANT_K_DOMAIN_COVERAGE_RULE_BOUND=true
CONSTANT_K_AUTHORITY_HASH_RULE_BOUND=true
HIDDEN_DEFAULT_K_FORBIDDEN=true
LEGACY_K_REUSE_FORBIDDEN=true
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_CONSTANT_K_STATUS=CLOSED
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=true
TUBE_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_STATUS=BLOCKED
NUMERICAL_METHOD_BOUND=false
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
