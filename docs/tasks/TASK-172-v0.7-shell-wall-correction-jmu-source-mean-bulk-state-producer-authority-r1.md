# TASK172 — Jμ source-mean bulk-state producer authority R1

## 1. Receipt and scope

This documentation/evidence-only record audits the source-required bulk-fluid
state used by the numerator-side viscosity in a future shell-side Jamil/Thome
`J_mu` authority. It separates the acquired source rule, a possible
model-level state/producer contract, a real case state, and a runtime
producer. It does not create or calculate any of them.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_SOURCE_MEAN_BULK_STATE_PRODUCER_AUTHORITY_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=3893e07c802d4ba91e83428dc733a90b5fbdde80
MODE=JMU_SOURCE_MEAN_BULK_STATE_PRODUCER_AUTHORITY_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The material branch is inherited and paused. The Q branch, preliminary shell
film branch, CWT/CHF real receipts, C3 ordering and all numerical work are
outside this gate and remain unchanged.

## 2. Decision summary

The acquired Thome observation says that the bulk physical properties used by
the shell-side correlation are evaluated at the mean of the source stream's
inlet and outlet bulk temperatures. The source does not operationally define
the word `mean` as arithmetic, mass-weighted, enthalpy-equivalent, caloric or
another aggregation. It also does not bind a pressure rule for evaluating a
future property snapshot.

The repository has no reviewed TASK172 shell-side inlet/outlet state pair that
can be bound to that source quantity:

* TASK032 supplies one caller-bound bulk `PropertySnapshot` for algebraic flow
  screening, not a source-mean inlet/outlet pair or mean-state producer.
* TASK160's implemented stream input carries inlet state and a caller-supplied
  property snapshot, but no outlet state and no source-mean construction.
* TASK171 supplies topology/state locations and optional observations; its
  state producer slots remain unresolved and it does not solve inlet/outlet
  thermodynamic states.
* TASK162 can expose legacy whole-exchanger outlet results, but its `q_method`
  is a UA/HTC-dependent downstream closure and is not a TASK172 source-state
  producer.

Accordingly, this gate records the source rule as observed but does not bind an
executable aggregation rule, TASK032 mapping, case producer, or real state.

```ini
RESULT=BLOCKED
OUTCOME=OUTCOME_C_SOURCE_MEAN_DEFINITION_AMBIGUOUS
PRIMARY_BLOCKING_FINDING=SOURCE_MEAN_OPERATOR_AND_PRESSURE_RULE_NOT_OPERATIONALLY_DEFINED
SECONDARY_BLOCKING_FINDING=NO_REVIEWED_TASK172_SHELL_INLET_OUTLET_STATE_PAIR_OR_MEAN_STATE_PRODUCER
```

## 3. Source-rule audit

### 3.1 Jamil/Thome source chain

The accepted Jamil body binds the operational `J_mu` placement, while the
acquired Thome Chapter 3 body is retained as relevant chapter cross-check
evidence. The latter remains unpromoted because rights and the exact cited
2004-edition chain are not complete.

```ini
JMU_BULK_STATE_SOURCE_RULE_BOUND=true
JMU_BULK_STATE_SOURCE_ID=THOME-2004-EDB3-CH3-CROSSCHECK
JMU_BULK_STATE_SOURCE_LOCATION=Section_3.4.6_printed_p3-12_liquid_bulk_property_paragraph;Section_3.4.6_printed_p3-12_Eq3.4.23_context
JMU_BULK_STATE_SOURCE_QUANTITY=SHELL_SIDE_BULK_PROPERTIES_AT_MEAN_OF_SOURCE_STREAM_INLET_AND_OUTLET_BULK_TEMPERATURES
SOURCE_BULK_TEMPERATURE_DEFINITION=MEAN_OF_SOURCE_STREAM_INLET_AND_OUTLET_BULK_TEMPERATURES
SOURCE_BULK_PROPERTY_DEFINITION=SOURCE_BULK_PHYSICAL_PROPERTIES_EVALUATED_AT_THE_SOURCE_MEAN_BULK_TEMPERATURE
SOURCE_BULK_VISCOSITY_DEFINITION=MU_BULK_AT_THE_SOURCE_MEAN_INLET_OUTLET_BULK_TEMPERATURE
```

The source observation is not a production permission. The exact acquired
source identity and lifecycle are:

```ini
THOME_BODY_ACQUIRED=true
THOME_BODY_COMPLETE=true
THOME_BODY_SHA256=326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4
THOME_EDITION_IDENTITY_BOUND=true
THOME_EDITION_IDENTITY_SCOPE=RELEVANT_CHAPTER_CONTENT_ONLY
THOME_EXACT_CITED_2004_EDITION_CHAIN_BOUND=false
THOME_RIGHTS_REVIEW_COMPLETE=false
THOME_INDEPENDENT_AUTHORITY_REVIEW_COMPLETE=false
THOME_PRODUCTION_AUTHORITY_PROMOTED=false
THOME_SOURCE_ROLE=ACQUIRED_RELEVANT_CHAPTER_CROSS_CHECK_ONLY
JAMIL_SOURCE_ID=SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS
JAMIL_BODY_SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
JAMIL_EXACT_LOCATIONS=Section_2.2.2_PDF_p11_Eq6;Section_2.2.2_PDF_p11_Eq7;Appendix_PDF_pp58-59_Table_A2
```

### 3.2 Aggregation semantics

The acquired wording identifies the two endpoint temperatures but does not
define the aggregation operator. Therefore this record does not turn the
source word `mean` into an arithmetic equation.

```ini
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_TEMPERATURE_AGGREGATION_RULE=SOURCE_SAYS_MEAN_OF_INLET_AND_OUTLET_BULK_TEMPERATURES;OPERATOR_NOT_SPECIFIED_BY_ACQUIRED_SOURCE;ARITHMETIC_MEAN_NOT_AUTHORIZED
ARITHMETIC_MEAN_T_IN_PLUS_T_OUT_OVER_2_AUTHORIZED=false
MASS_WEIGHTED_MEAN_AUTHORIZED=false
ENTHALPY_EQUIVALENT_MEAN_AUTHORIZED=false
PROPERTY_VALUE_AVERAGING_AUTHORIZED=false
MIDPOINT_OR_LOCAL_CELL_SUBSTITUTION_AUTHORIZED=false
```

The missing operator is a semantic blocker, not a numerical tolerance. A
future source-qualified or independently reviewed rule must state the
aggregation quantity, equation, units, and any required weighting before a
mean-state producer can be admitted.

### 3.3 Property-state semantics

Within the source rule's still-unresolved mean state, the source observation
supports evaluating the shell-side bulk properties at that one source state;
it does not support averaging the property values themselves. The property
state audit is kept separate from the missing temperature aggregator:

| Quantity | Source-rule disposition | No-instance consequence |
| --- | --- | --- |
| `mu_bulk` | Bound to the source bulk state used by `J_mu` | No viscosity snapshot exists |
| `cp` | Bound as a source bulk property where the source correlation uses it | No source-bound property snapshot exists |
| `k` | Bound only as a source bulk property if required by the property backend; not independently prescribed by `J_mu` | No hidden `k` lookup |
| `rho` | Bound only as a source bulk property if required by the property backend; not independently prescribed by `J_mu` | No hidden `rho` lookup |
| `Pr` | Bound as a bulk-state correlation quantity; it must be evaluated/derived after the source state is defined | No average `Pr` is permitted |

```ini
JMU_BULK_VISCOSITY_STATE_RULE_BOUND=true
JMU_BULK_VISCOSITY_STATE_RULE=MU_BULK_EVALUATED_AT_SOURCE_MEAN_BULK_TEMPERATURE;MEAN_OPERATOR_STILL_UNBOUND
JMU_BULK_PRANDTL_STATE_RULE_BOUND=true
JMU_BULK_PRANDTL_STATE_RULE=PR_BULK_EVALUATED_OR_DERIVED_AT_THE_SAME_SOURCE_BULK_STATE;NO_PROPERTY_VALUE_AVERAGING
JMU_BULK_PROPERTY_EVALUATION_ORDER=DEFINE_SOURCE_BULK_STATE_THEN_EVALUATE_OR_DERIVE_REQUIRED_PROPERTIES
```

No property provider call is introduced by this record. The reviewed water
profile is compatible only as a conditional property backend for its already
approved narrow scope:

```ini
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBILITY_SCOPE=REVIEWED_PURE_WATER_PROFILE_SCOPE_ONLY;DOES_NOT_PRODUCE_MEAN_STATE
```

## 4. Stream and granularity identity

The source rule is for the shell-side coefficient. It cannot reuse the
tube-side bulk state, and it cannot be localized merely because TASK171 is
segmented.

```ini
JMU_BULK_STATE_STREAM_ROLE_BOUND=true
JMU_BULK_STATE_STREAM_ROLE=SHELL_SIDE_FLUID
JMU_SOURCE_BULK_STATE_GRANULARITY_BOUND=true
JMU_SOURCE_BULK_STATE_GRANULARITY=WHOLE_EXCHANGER_SHELL_STREAM_MEAN_OF_SOURCE_INLET_AND_OUTLET_BULK_STATE
WHOLE_EXCHANGER_SOURCE_STATE_LOCALIZATION_AUTHORIZED=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
```

The source granularity observation is not a TASK172 localization rule. No
local-cell, physical-interval, arithmetic wall-state or mesh average is
created.

## 5. Existing repository state-authority audit

### 5.1 TASK032

The native TASK032 state authority has a deterministic one-snapshot shape:

```ini
TASK032_BULK_STATE_ID=task032.shell-side-flow-state.v1::PROPERTY_SNAPSHOT::BULK_SHELL_SIDE_STATE
TASK032_BULK_STATE_SEMANTICS=SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING
TASK032_BULK_STATE_GRANULARITY=ONE_BULK_SHELL_SIDE_PROPERTY_SNAPSHOT
TASK032_INLET_STATE_AVAILABLE=false
TASK032_OUTLET_STATE_AVAILABLE=false
TASK032_SOURCE_MEAN_PRODUCER_AVAILABLE=false
TASK032_PROPERTY_SNAPSHOT_AVAILABLE=true_CALLER_BOUND_SNAPSHOT_ONLY
TASK032_HEAT_DUTY_AND_OUTLET_SOLVE_IN_SCOPE=false
```

Its snapshot contains `bulk_temperature_k` and `bulk_pressure_pa`, but the
field names do not establish that the values are the source mean of inlet and
outlet states. TASK032 also deliberately does not perform source lookup,
property-path integration, outlet solving or wall iteration.

### 5.2 TASK160 thermal-stream state

`thermal_stream_state` is an implemented TASK160 ingress/validation boundary,
not a TASK172 source-mean producer. `RatingStreamInput` carries a stream ID,
side binding, inlet temperature, optional inlet pressure, mass flow and a
caller-supplied property snapshot. `ValidatedRatingStreamState` only wraps
that input. It provides no outlet state and no source-defined mean-state
operator.

```ini
AUTHORITY_ID=TASK160_THERMAL_STREAM_STATE_V1
LIFECYCLE_STATUS=IMPLEMENTED_TASK160_INPUT_CONTRACT_NOT_TASK172_PRODUCER
STATE_ROLE=TWO_STREAM_RATING_INPUT
GRANULARITY=STREAM_INLET_INPUT
CASE_BOUND=TASK160_REQUEST_BOUND_ONLY
INLET_STATE_AVAILABLE=true
OUTLET_STATE_AVAILABLE=false
PHYSICAL_SUPPORT_IDENTITY_AVAILABLE=false
PROPERTY_AUTHORITY_AVAILABLE=PARTIAL_CALLER_SNAPSHOT;NOT_SOURCE_MEAN_JMU_AUTHORITY
```

### 5.3 TASK171 topology/state vocabulary

TASK171 carries explicit path inlet/outlet topology, face and physical-interval
identities, and state-location vocabulary. Its state records retain
`producer_status=UNRESOLVED`; its bookkeeping accepts optional face enthalpy,
mass-flow and signed wall-heat observations. It does not produce thermodynamic
inlet/outlet states, evaluate properties or construct a source mean.

```ini
AUTHORITY_ID=V07-T171-TOPOLOGY-R4-V1
LIFECYCLE_STATUS=REVIEWED_STRUCTURAL_TOPOLOGY_ONLY
STATE_ROLE=TOPOLOGY_AND_STATE_LOCATION_VOCABULARY
GRANULARITY=PATH_FACE_CELL_MEAN_COMPARTMENT_WALL_LOCATION_VOCABULARY
CASE_BOUND=TOPOLOGY_REQUEST_BOUND
INLET_STATE_AVAILABLE=STRUCTURAL_FACE_ID_ONLY
OUTLET_STATE_AVAILABLE=STRUCTURAL_FACE_ID_ONLY
PHYSICAL_SUPPORT_IDENTITY_AVAILABLE=true_STRUCTURAL_ONLY
PROPERTY_AUTHORITY_AVAILABLE=false
STATE_PRODUCER_AVAILABLE=false
```

### 5.4 TASK162 legacy closure

TASK162 exposes legacy whole-exchanger input and output temperatures and a
`q_method`, but this is not a source-state producer for the active J_mu path.
The duty is derived through UA/NTU/Table-7/capacity-rate relations; TASK038
UA itself depends on film and wall/fouling inputs. Reusing its outlet result
would therefore require a separately reviewed case, stream, geometry,
property-snapshot and dependency mapping that does not exist here.

```ini
AUTHORITY_ID=TASK162_THERMAL_PERFORMANCE_CLOSURE
LIFECYCLE_STATUS=IMPLEMENTED_LEGACY_WHOLE_EXCHANGER_CLOSURE
STATE_ROLE=LEGACY_PERFORMANCE_INPUT_AND_DERIVED_OUTPUT
GRANULARITY=WHOLE_EXCHANGER
CASE_BOUND=LEGACY_TASK162_CASE_BOUND
INLET_STATE_AVAILABLE=true_INHERITED_TASK160_INPUT
OUTLET_STATE_AVAILABLE=true_DERIVED_LEGACY_RESULT
PHYSICAL_SUPPORT_IDENTITY_AVAILABLE=false_TASK172_SUPPORT_MAPPING
PROPERTY_AUTHORITY_AVAILABLE=INHERITED_NOT_SOURCE_MEAN_JMU_PRODUCER
SOURCE_MEAN_PRODUCER_AVAILABLE=false
```

The audit does not invalidate TASK160, TASK032, TASK171 or TASK162 within
their own scopes. It rejects only an unreviewed cross-task reinterpretation as
the TASK172 source-mean producer.

## 6. TASK032 mapping and producer contract

The only defensible future mapping is an exact, case-bound mapping from a
source-qualified shell inlet/outlet pair to a property snapshot whose
temperature/pressure semantics are explicitly recorded. Numerical equality
with the existing TASK032 `bulk_temperature_k` is insufficient.

```ini
SOURCE_TO_TASK032_BULK_MAPPING_CONTRACT_BOUND=false
SOURCE_TO_TASK032_BULK_MAPPING_RULE=REQUIRES_SOURCE_DEFINED_MEAN_OPERATOR;SOURCE_DEFINED_PRESSURE_RULE;EXACT_SHELL_STREAM_CASE_BINDING;EXACT_PROPERTY_SNAPSHOT_ID_AND_HASH;REVIEWED_LIFECYCLE
REAL_SOURCE_TO_TASK032_BULK_MAPPING_BOUND=false
TASK032_BULK_STATE_MAPPING_VALID=false
TASK032_BULK_STATE_MAPPING_REASON=ONE_SCREENING_SNAPSHOT_WITHOUT_SOURCE_MEAN_INLET_OUTLET_SEMANTICS_OR_SOURCE_PRESSURE_RULE
```

The model-level producer contract cannot yet be complete because both the
source aggregator and the source-required pressure treatment are unresolved.
No placeholder `T_mean`, arithmetic mean pressure, property average, hidden
database lookup or caller assertion is admitted.

## 7. Inlet/outlet producer authority

No current repository authority supplies both shell-side inlet and outlet
thermodynamic states with all of the following simultaneously: exact stream
role, case/configuration identity, temperature, pressure semantics, reviewed
property authority, provenance, and lifecycle. The required state pair is
therefore absent rather than synthesized from legacy outputs.

```ini
SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SHELL_INLET_STATE_ID=NONE
SHELL_OUTLET_STATE_ID=NONE
SHELL_INLET_STATE_PROPERTY_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_PROPERTY_AUTHORITY_BOUND=false
SHELL_INLET_STATE_CASE_BINDING_BOUND=false
SHELL_OUTLET_STATE_CASE_BINDING_BOUND=false
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_REQUIRED_FIELDS=SOURCE_MEAN_OPERATOR;SOURCE_PRESSURE_RULE;SHELL_INLET_STATE_ID_AND_HASH;SHELL_OUTLET_STATE_ID_AND_HASH;SHELL_STREAM_ROLE;CASE_CONFIGURATION_ID_AND_HASH;PROPERTY_AUTHORITY_ID_AND_VERSION;PROPERTY_SNAPSHOT_HASH;PROVENANCE;FAIL_CLOSED_RULES
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
SOURCE_BULK_STATE_AVAILABLE_IN_TASK172=false
SOURCE_BULK_STATE_PRODUCER_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
```

This is the central producer finding. It is not repaired by selecting a
historical TASK162 outlet, a TASK032 snapshot, a TASK171 face, or an arithmetic
midpoint.

## 8. Pressure and property backend semantics

The acquired source observation does not bind whether the pressure paired with
the source mean temperature is inlet pressure, outlet pressure, mean pressure,
local pressure, or another reference pressure. The reviewed water profile
requires a bound state within its own narrow `T/P` window, but it does not
choose this J_mu source pressure rule.

```ini
JMU_BULK_PRESSURE_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE=NOT_SPECIFIED_BY_ACQUIRED_JMU_SOURCE;DO_NOT_INVENT_INLET_OUTLET_OR_ARITHMETIC_MEAN_PRESSURE
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true_CONDITIONAL_ON_EXACT_REVIEWED_WATER_STATE_BINDING
PROPERTY_BACKEND_LOOKUP_AS_AUTHORITY=false
```

Before a future state producer may evaluate `mu_bulk`, `cp`, `k`, `rho` or
`Pr`, it must first bind the source temperature aggregation and pressure
semantics, then use the exact reviewed property authority. It may not average
already-evaluated properties or silently ask a runtime database for a value.

## 9. Granularity and localization guard

The source state is a whole shell-stream/tube-bundle mean observation. TASK171
physical intervals and local cells are structural support vocabulary only. No
source authority connects a global source mean to a local state, and no local
wall or bulk values may be averaged into the source mean.

```ini
JMU_SOURCE_BULK_STATE_GRANULARITY_BOUND=true
JMU_SOURCE_BULK_STATE_GRANULARITY=WHOLE_EXCHANGER_SHELL_STREAM_MEAN_INLET_OUTLET_STATE
WALL_PRODUCER_REQUIRED_BULK_GRANULARITY=SOURCE_WHOLE_SHELL_STREAM_MEAN_FOR_GLOBAL_JMU
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
LOCAL_WALL_STATE_TO_GLOBAL_JMU_MAPPING_BOUND=false
LOCALIZATION_TRANSFER_AUTHORITY_BOUND=false
WALL_TEMPERATURE_AGGREGATION_RULE_BOUND=false
```

`SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND` must not become true until
the global source operator, pressure rule and exact state pair are all bound.
Even after that, a real producer instance would remain a separate lifecycle
step.

## 10. Circularity status

No producer has been selected, so this gate cannot truthfully classify whether
the eventual source mean state depends on `J_mu`, shell film, wall state,
overall `U`, or `Q`. The potential dependency is preserved as a conditional
graph, not promoted to an active numerical loop.

```ini
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_JMU=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_SHELL_FILM=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_WALL_STATE=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_OVERALL_U=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_Q=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDENCY_REASON=NO_SOURCE_MEAN_PRODUCER_OR_CASE_INLET_OUTLET_PAIR_SELECTED
JMU_WALL_COUPLING_CIRCULARITY_PATH_IDENTIFIED=true
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_WALL_COUPLING_CLOSURE_AUTHORITY_BOUND=false
```

No iteration, tolerance, relaxation, wall solve or numerical closure is
introduced.

## 11. Preserved effective state

```ini
MATERIAL_K_WALL_TRANSFER_CONTRACT_BOUND=true
REAL_CASE_MATERIAL_IDENTITY_BOUND=false
REAL_CASE_K_WALL_PROFILE_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
MATERIAL_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_MATERIAL_AND_K_WALL_EVIDENCE
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
TRANSFER_CONTRACT_STATUS=REVIEWED_TUBE_FILM_TRANSFER_CONTRACT
CWT_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
CHF_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
C3_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_ORDERING_SOURCE_LEAD
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The source-mean producer finding does not alter the shell blocker taxonomy or
the other three effective blockers.

## 12. Smallest next gate

The next gate should acquire or independently establish only the missing
operational source-mean semantics and the corresponding exact shell inlet /
outlet state-authority binding. It must not create a real state by assumption
and must not proceed to wall production or implementation.

```ini
NEXT_GATE=AUTHORIZE_TASK172_JMU_SOURCE_MEAN_BULK_STATE_AGGREGATION_AND_SHELL_INLET_OUTLET_STATE_BINDING_R2_ONLY
```

The next gate must answer, with source-backed authority:

1. what `mean` means and its exact equation/weighting;
2. which pressure is paired with the resulting state;
3. which reviewed shell inlet/outlet state producer supplies the two states;
4. whether the result is a whole-shell-stream state or another explicitly
   authorized granularity; and
5. whether the future producer has any dependency on `J_mu`, shell film, wall
   state, `U` or `Q`.

## 13. Governance receipt

```ini
SOURCE_RULE_AUDIT_ONLY=true
MODEL_LEVEL_PRODUCER_CONTRACT_CREATED=false
REAL_STATE_INSTANCE_CREATED=false
RUNTIME_PRODUCER_CREATED=false
ARITHMETIC_MEAN_ASSUMED=false
PROPERTY_VALUE_AVERAGING_PERFORMED=false
HIDDEN_PROPERTY_LOOKUP_USED=false
CALLER_ASSERTION_USED_AS_AUTHORITY=false
MATERIAL_INSTANCE_CREATED=false
K_WALL_INSTANCE_CREATED=false
WALL_SOLVE_EXECUTED=false
JMU_IMPLEMENTED=false
NUMERICAL_WORK_STARTED=false
HISTORICAL_RECORDS_REWRITTEN=false
NEW_AUTHORITY_SELF_APPROVAL=false
INTERMEDIATE_GITHUB_CI_RUNS=0
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The source rule is recorded, but the production admission remains fail-closed
because no source-defined operational mean-state producer and no real
case-bound shell bulk state are present.
