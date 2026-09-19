# TASK-172 v0.7 — J_mu source-mean contract instance and dependency semantics correction R2A

## Receipt

```text
TASK_ID=TASK172_V0_7_JMU_SOURCE_MEAN_CONTRACT_INSTANCE_AND_DEPENDENCY_SEMANTICS_CORRECTION_R2A
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=3701f1df08dc9a673944d76a6f0bfa7d477de60f
MODE=APPEND_ONLY_R71_SEMANTIC_CORRECTION_OVERLAY
RESULT=CORRECTED
```

This document corrects only the distinction between a model-level source-mean
producer contract and a real source-mean state instance, plus the distinction
between the temperature operator's dependencies and the dependencies of the
future endpoint-state producers.  It does not reacquire sources or alter the
R71 source adjudication.

## 1. Historical R71 immutability

R71 remains the authoritative historical record for the targeted source
acquisition and transfer decision:

```text
PREVIOUS_R71_HEAD=3701f1df08dc9a673944d76a6f0bfa7d477de60f
R71_RESULT=BLOCKED
R71_OUTCOME=OUTCOME_B_TEMPERATURE_OPERATOR_BOUND_PRESSURE_RULE_UNRESOLVED
R71_ORIGINAL_DOCUMENT_CHANGED=false
R71_ORIGINAL_EVIDENCE_CHANGED=false
R71_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
```

The accepted temperature finding is unchanged:

```text
SOURCE_MEAN_TEMPERATURE_OPERATOR_AUTHORITY_FOUND=true
SOURCE_MEAN_TEMPERATURE_OPERATOR=(T_shell_in + T_shell_out) / 2; ARITHMETIC_MEAN
SOURCE_MEAN_TEMPERATURE_OPERATOR_SOURCE_ID=ASME-PTC-12.5-2000-R2015-PUBLIC-COPY
SOURCE_MEAN_TEMPERATURE_OPERATOR_TRANSFERABLE_TO_TASK172_NATIVE_JMU=true
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=true
SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND=true
```

The pressure result is also unchanged and remains fail-closed:

```text
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE=NONE
JMU_BULK_PRESSURE_RULE_BOUND=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
```

No pressure convention is introduced by this correction.

## 2. Model-level contract versus real instance

The reviewed endpoint-pair contract is already a sufficient input-contract
shape for a future model-level source-mean producer.  It does not supply
endpoint values, endpoint producers, or a real case.

```text
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
SOURCE_MEAN_USES_REVIEWED_ENDPOINT_PAIR_CONTRACT=true

REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false
REAL_ENDPOINT_PAIR_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false

REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
REAL_ENDPOINT_PAIR_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
```

Therefore a future model-level contract may be constructed when the source
temperature operator, pressure semantics, reviewed endpoint-pair input
contract, property-authority contract, and source-mean identity/provenance
and fail-closed schemas are complete.  Actual endpoint values are not part of
that candidate-creation predicate.

At this head the model-level contract is still unbound for one reason:

```text
SOURCE_MEAN_MODEL_LEVEL_CONTRACT_PRIMARY_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
SOURCE_MEAN_REAL_INSTANCE_ADDITIONAL_BLOCKERS=REAL_REVIEWED_SHELL_INLET_PRODUCER_MISSING;REAL_REVIEWED_SHELL_OUTLET_PRODUCER_MISSING;REAL_ENDPOINT_PAIR_INSTANCE_MISSING
```

The first line blocks model-level contract construction.  The second line
describes additional requirements for a real instance.  These lifecycle layers
must not be conflated.

## 3. Real endpoint and state guards

No endpoint or source-mean instance is created:

```text
REAL_REVIEWED_SHELL_INLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_OUTLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_ENDPOINT_PAIR_PRODUCER_FOUND=false

REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
```

The existing negative findings remain in force.  TASK160 is only a
conditional inlet-input adapter; TASK162's derived outlet depends on `U`,
tube film, and shell film and is not an admitted J_mu source outlet; TASK032
contains one generic bulk snapshot representation; TASK171 supplies structural
topology vocabulary and no thermodynamic producer.

```text
TASK162_DERIVED_OUTLET_PRESENT=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_U=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_TUBE_FILM=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_SHELL_FILM=true
TASK162_DERIVED_OUTLET_ADMISSIBLE_AS_JMU_SOURCE_OUTLET=false

TASK160_TO_JMU_SHELL_INLET_STATE_CONTRACT_COMPATIBLE=true
TASK160_COMPATIBILITY_SCOPE=CONDITIONAL_INLET_INPUT_ADAPTER_ONLY
TASK160_SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false

TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_INLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_OUTLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_SOURCE_MEAN=false
TASK171_THERMODYNAMIC_STATE_PRODUCER_BOUND=false
```

## 4. Dependency-layer correction

The arithmetic temperature operator is a pure aggregation operator over the
already admitted shell endpoint states.  It does not call `J_mu`, shell film,
wall state, overall `U`, or `Q`:

```text
SOURCE_MEAN_TEMPERATURE_OPERATOR_DEPENDS_ON_JMU=false
SOURCE_MEAN_TEMPERATURE_OPERATOR_DEPENDS_ON_SHELL_FILM=false
SOURCE_MEAN_TEMPERATURE_OPERATOR_DEPENDS_ON_WALL_STATE=false
SOURCE_MEAN_TEMPERATURE_OPERATOR_DEPENDS_ON_OVERALL_U=false
SOURCE_MEAN_TEMPERATURE_OPERATOR_DEPENDS_ON_Q=false
```

The future source-mean producer is a different dependency layer.  It consumes
endpoint states whose real producer graph is not currently admitted.  Its
upstream dependencies are consequently unknown and must not be recorded as
false:

```text
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_JMU=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_SHELL_FILM=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_WALL_STATE=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_OVERALL_U=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_Q=undetermined

SOURCE_MEAN_OPERATOR_DEPENDENCY_DISTINCT_FROM_ENDPOINT_PRODUCER_DEPENDENCY=true
UPSTREAM_ENDPOINT_DEPENDENCIES_PROPAGATE_TO_SOURCE_MEAN_PRODUCER=true
UNKNOWN_UPSTREAM_DEPENDENCY_MAY_NOT_BE_RECORDED_AS_FALSE=true
```

The `undetermined` values do not authorize any of those inputs.  They record
that the endpoint producer graph cannot yet be proven independent.

## 5. Candidate and real-instance eligibility

The same source-mean authority candidate identity remains reserved but is not
created:

```text
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_ID=NONE
SOURCE_MEAN_BULK_STATE_AUTHORITY_LIFECYCLE=NONE
SOURCE_MEAN_BULK_STATE_INDEPENDENT_REVIEW=NONE
```

The model-level candidate eligibility rule is:

```text
SOURCE_MEAN_MODEL_LEVEL_AUTHORITY_CANDIDATE_ELIGIBILITY_RULE_BOUND=true
```

All of the following must be true before a future candidate is created:

```text
SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND=true
JMU_BULK_PRESSURE_RULE_BOUND=true
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID=true
SOURCE_MEAN_IDENTITY_AND_PROVENANCE_SCHEMA_BOUND=true
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND=true
```

Real endpoint instances are deliberately absent from that predicate.  A real
source-mean instance has a separate rule:

```text
REAL_SOURCE_MEAN_INSTANCE_ELIGIBILITY_RULE_BOUND=true
```

It additionally requires reviewed real inlet and outlet producers, case-bound
endpoint states, a real endpoint-pair receipt, actual application of the
pressure state/rule, an actual property snapshot, and admitted producer
lifecycle/provenance.  None of those is created here.

## 6. Granularity and shell-wall boundaries

The source remains a whole-exchanger shell-stream mean and is not localized:

```text
JMU_SOURCE_BULK_STATE_GRANULARITY=WHOLE_EXCHANGER_SHELL_STREAM_MEAN_OF_SOURCE_INLET_AND_OUTLET_BULK_STATE
WHOLE_EXCHANGER_SOURCE_STATE_LOCALIZATION_AUTHORIZED=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
WALL_TEMPERATURE_AGGREGATION_RULE_BOUND=false
```

The following branches remain frozen:

```text
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

## 7. Numerical and parent-blocker preservation

No numerical branch is reopened:

```text
L2B_BRANCH_STATUS=PAUSED_PENDING_REQUIRED_PHYSICAL_AUTHORITY_CLOSURE
L2B_METHOD_STATUS=METHOD_UNBOUND
L3_LOCAL_STATE_RECONSTRUCTION_BRANCH_STATUS=PAUSED_PENDING_DIRECT_LOCAL_STATE_PRODUCER_AUTHORITY_OR_RECONSTRUCTION_OPERATOR_AUTHORITY
L3_METHOD_STATUS=METHOD_UNBOUND
NUMERICAL_ERROR_BUDGET_STOPPING_BRANCH_STATUS=PAUSED_PENDING_ACTUAL_METHOD_SENSITIVITY_QUANTITATIVE_ERROR_ALLOCATION_AND_MESH_QUALIFICATION
MESH_CONVERGENCE_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_APPROVED_OBSERVABLES_MAPPING_METRIC_REFINEMENT_SEQUENCE_THRESHOLD_AND_ESTIMATOR
```

The four parent blockers remain exactly:

```text
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION

EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 8. Governance and decision

This is an append-only documentation/evidence correction.  No source was
reacquired, no property calculation or endpoint creation occurred, and no
production, TASK166, TASK171, dependency, lockfile, workflow, Ready, or Merge
action was performed.

```text
R71_ORIGINAL_DOCUMENT_CHANGED=false
R71_ORIGINAL_EVIDENCE_CHANGED=false
R71_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true

PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false

RESULT=CORRECTED
NEXT_GATE=AUTHORIZE_TASK172_JMU_BULK_PRESSURE_REFERENCE_CONVENTION_QUALIFICATION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
