# TASK172 — Jμ source-mean fail-closed admission-rule contract R1

## 1. Receipt and boundary

```ini
TASK_ID=TASK172_V0_7_JMU_SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_CONTRACT_R1
MODE=MODEL_LEVEL_FAIL_CLOSED_ADMISSION_CONTRACT_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=99e74b81476508e942604fccb38317e8985f5177
HEAD_PRECONDITION_VERIFIED=true
RESULT=PROPOSED_FAIL_CLOSED_CONTRACT_CREATED
```

This document constructs a model-level rejection/admission contract for a
future Jμ source-mean bulk-state authority candidate. It does not select a
pressure convention, create an endpoint state or pair, create a property
snapshot, create a producer, execute Jμ, solve a wall state, or implement a
runtime gate.

The contract has three deliberately separate layers:

```text
ENDPOINT_PAIR_FAIL_CLOSED_RULES
    → input-contract rules inherited by reference from the reviewed R59 pair
      contract;
SOURCE_MEAN_MODEL_LEVEL_FAIL_CLOSED_RULES
    → the new source-mean candidate admission/rejection matrix constructed here;
REAL_SOURCE_MEAN_INSTANCE_ADMISSION_RULES
    → a later case/instance gate, not completed by this task.
```

The endpoint-pair rules are useful evidence for input validation, but they are
not by themselves source-mean admission coverage.

```ini
ENDPOINT_PAIR_FAIL_CLOSED_RULES_REUSED_BY_REFERENCE=true
SOURCE_MEAN_SPECIFIC_FAIL_CLOSED_COVERAGE_ADDED=true
ENDPOINT_PAIR_RULES_ALONE_SUFFICIENT=false
REAL_SOURCE_MEAN_INSTANCE_ADMISSION_RULES_COMPLETED=false
```

## 2. Historical immutability

R71, R72/R2A and R73/R2A1 are historical inputs. Their documents, evidence
files and registry extensions are not rewritten.

```ini
R71_EXTENSION_REWRITTEN=false
R72_EXTENSION_REWRITTEN=false
R73_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
```

The immutable predecessor evidence includes:

| Record | Existing canonical evidence |
| --- | --- |
| R71 source-mean aggregation | `r71_extension`, `0d422248cd375bd752bd84d6aeed5cea6fbc458db40f4361aa5cb66312657008` |
| R72/R2A instance/dependency correction | `r72_extension`, `7de8acc0bf4dabc0ab01056fe696aa2dff30dae4e66fbf12831c5fcb3400f638` |
| R73/R2A1 predicate evidence closure | `r73_extension`, `652ff715630ee33c272e9ad3e63e4ba820ec9526e4a870f846fe5f8c47064ae8` |
| R59 reviewed endpoint-pair contract | `r59_extension`, `84f31d5f52d598230eb422f0fd0748c64c411bb263a04da10e192ad312823b4b` |

## 3. Default-reject admission principle

The future candidate gate is fail closed by default:

```ini
DEFAULT_ADMISSION_DECISION=REJECT
ALL_REQUIRED_MODEL_LEVEL_PREDICATES_MUST_BE_SATISFIED=true
UNKNOWN_OR_UNDETERMINED_IS_NOT_ACCEPTED=true
```

Only an explicitly satisfied, reviewed and scope-compatible predicate may
permit candidate construction to continue. Missing, unknown, undetermined,
unreviewed, incompatible, out-of-scope, mismatched or caller-asserted inputs
are rejection conditions. They may not be converted to defaults, fallback
values, inferred compatibility or a hidden backend result.

The following are never admission substitutes:

```ini
IMPLICIT_DEFAULTS_ALLOWED=false
SILENT_FALLBACK_ALLOWED=false
CALLER_ASSERTION_AS_AUTHORITY_ALLOWED=false
LEGACY_RESULT_RELABELING_ALLOWED=false
BEST_EFFORT_SUBSTITUTION_ALLOWED=false
HIDDEN_PROPERTY_LOOKUP_ALLOWED=false
PRESSURE_ASSUMPTION_ALLOWED=false
UNSUPPORTED_INTERPOLATION_ALLOWED=false
AUTHORITY_LIFECYCLE_BYPASS_ALLOWED=false
```

## 4. Source-mean model-level rejection contract

The complete machine-readable matrix is in the paired evidence JSON under
`source_mean_fail_closed_admission_matrix`. Each row has a stable rule ID,
condition, layer, decision and inheritance/source basis. Every row below has
the same normative decision:

```ini
DECISION_FOR_ANY_MATRIX_MATCH=REJECT
```

### 4.1 Temperature authority rules

Reject the candidate if any of the following occurs:

```ini
REJECT_IF_TEMPERATURE_OPERATOR_AUTHORITY_MISSING=true
REJECT_IF_TEMPERATURE_OPERATOR_LIFECYCLE_INVALID=true
REJECT_IF_TEMPERATURE_OPERATOR_HASH_MISMATCH=true
REJECT_IF_TEMPERATURE_OPERATOR_SCOPE_MISMATCH=true
REJECT_IF_UNAUTHORIZED_TEMPERATURE_AGGREGATION=true
REJECT_IF_LOCAL_STATE_OPERATOR_SUBSTITUTED_FOR_WHOLE_STREAM_OPERATOR=true
REJECT_IF_PROPERTY_VALUE_AVERAGING_SUBSTITUTED_FOR_TEMPERATURE_STATE_AGGREGATION=true
```

The existing accepted temperature predicate remains unchanged:

```ini
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
```

This contract does not research or broaden the transferred arithmetic
temperature operator.

### 4.2 Pressure authority rules

Pressure remains unresolved. The contract defines rejection requirements only;
it does not define a pressure value or convention.

```ini
REJECT_IF_PRESSURE_RULE_AUTHORITY_MISSING=true
REJECT_IF_PRESSURE_RULE_LIFECYCLE_INVALID=true
REJECT_IF_PRESSURE_RULE_HASH_MISMATCH=true
REJECT_IF_PRESSURE_RULE_SCOPE_MISMATCH=true
REJECT_IF_PRESSURE_ASSUMED_BY_CALLER=true
REJECT_IF_PRESSURE_DEFAULTED_BY_BACKEND=true
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
```

No inlet pressure, outlet pressure, arithmetic-mean pressure, representative
pressure, constant-pressure assumption or pressure-insensitivity rule is
introduced here.

### 4.3 Endpoint-pair input-contract rules

R59 is reused only as the reviewed input-contract reference. A source-mean
candidate must reject:

```ini
REJECT_IF_ENDPOINT_PAIR_CONTRACT_MISSING=true
REJECT_IF_ENDPOINT_PAIR_CONTRACT_UNREVIEWED=true
REJECT_IF_ENDPOINT_PAIR_CONTRACT_HASH_MISMATCH=true
REJECT_IF_ENDPOINT_PAIR_SCOPE_MISMATCH=true
REJECT_IF_ENDPOINT_CASE_SCHEMA_INCOMPATIBLE=true
REJECT_IF_ENDPOINT_STREAM_OR_ROLE_MISMATCH=true
REJECT_IF_ENDPOINT_TOPOLOGY_OR_PATH_SEMANTICS_INCOMPATIBLE=true
REJECT_IF_ENDPOINT_IDENTITY_SCHEMA_INCOMPLETE=true
```

The source-mean model contract does not require endpoint values or a real
endpoint producer:

```ini
REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false
REAL_ENDPOINT_PAIR_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false
REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
REAL_ENDPOINT_PAIR_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
```

### 4.4 Property-authority rules

The existing narrow water authority is retained as a conditional reference;
this contract does not call a backend or expand its domain:

```ini
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
PROPERTY_SCOPE=PURE_ORDINARY_WATER;HEOS;COOLPROP_8.0.0;DEF;STABLE_SINGLE_PHASE_LIQUID;T=298.15..300_K;P=100000..101325_PA
```

Reject if any property authority or state-scope condition is invalid:

```ini
REJECT_IF_PROPERTY_AUTHORITY_MISSING=true
REJECT_IF_PROPERTY_AUTHORITY_LIFECYCLE_INVALID=true
REJECT_IF_PROPERTY_AUTHORITY_ID_VERSION_MISMATCH=true
REJECT_IF_PROPERTY_BACKEND_MISMATCH=true
REJECT_IF_PROPERTY_REFERENCE_STATE_MISMATCH=true
REJECT_IF_PROPERTY_FLUID_OR_COMPOSITION_MISMATCH=true
REJECT_IF_PROPERTY_PHASE_MISMATCH=true
REJECT_IF_PROPERTY_SCOPE_MISMATCH=true
REJECT_IF_PROPERTY_DOMAIN_VIOLATION=true
REJECT_IF_PROPERTY_EXTRAPOLATION_REQUIRED=true
REJECT_IF_PROPERTY_SNAPSHOT_SUPPLIED_AS_AUTHORITY=true
REJECT_IF_RUNTIME_LOOKUP_SUBSTITUTES_FOR_AUTHORITY=true
```

`JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID=true` remains a model-level
reference-validity finding from R73. It does not mean that a property snapshot
exists.

### 4.5 Identity and provenance rules

Reject any candidate with a missing, conflicting, non-canonical or
unproven identity/provenance element:

```ini
REJECT_IF_REQUIRED_IDENTITY_MISSING=true
REJECT_IF_REQUIRED_HASH_MISSING=true
REJECT_IF_CANONICAL_HASH_MISMATCH=true
REJECT_IF_CASE_IDENTITY_MISMATCH=true
REJECT_IF_STREAM_IDENTITY_MISMATCH=true
REJECT_IF_TOPOLOGY_IDENTITY_MISMATCH=true
REJECT_IF_PATH_OR_ENDPOINT_REFERENCE_MISSING_OR_MISMATCH=true
REJECT_IF_TEMPERATURE_AUTHORITY_ID_OR_HASH_MISSING_OR_MISMATCH=true
REJECT_IF_PRESSURE_AUTHORITY_ID_OR_HASH_MISSING_OR_MISMATCH=true
REJECT_IF_PROPERTY_AUTHORITY_ID_OR_VERSION_MISSING_OR_MISMATCH=true
REJECT_IF_STATE_PRODUCER_AUTHORITY_IDENTITY_MISSING=true
REJECT_IF_STATE_PRODUCER_LIFECYCLE_MISSING_OR_INVALID=true
REJECT_IF_PROVENANCE_MISSING=true
REJECT_IF_PROVENANCE_INCONSISTENT=true
REJECT_IF_HIDDEN_OR_DEFAULT_STATE=true
REJECT_IF_UNSUPPORTED_INTERPOLATION=true
REJECT_IF_CALLER_ASSERTION_REPLACES_AUTHORITY=true
REJECT_IF_LEGACY_RESULT_RELABELING=true
```

The future model-level schema must carry the source-mean state identity,
case/topology/stream identity, endpoint references, temperature and pressure
authority references, property authority/version, producer authority/lifecycle,
provenance and canonical hash. No values are populated here.

### 4.6 Upstream authority lifecycle rules

Only accepted upstream lifecycles may be consumed. Reject:

```ini
REJECT_IF_UPSTREAM_AUTHORITY_LIFECYCLE_NOT_ACCEPTED=true
REJECT_IF_REVIEW_EVIDENCE_MISSING=true
REJECT_IF_SELF_APPROVAL_REQUIRED=true
REJECT_IF_CALLER_DECLARED_LIFECYCLE=true
REJECT_IF_UNKNOWN_OR_NONE_LIFECYCLE=true
REJECT_IF_PROPOSED_PENDING_REJECTED_OR_BLOCKED_UPSTREAM_LIFECYCLE=true
```

`PROPOSED`, `PENDING`, `REJECTED`, `BLOCKED`, `NONE` and unknown lifecycle
values do not become acceptable merely because their field is present.

### 4.7 Unknown and cross-layer leakage rules

The following semantic shortcuts are explicit rejection conditions:

```ini
REJECT_IF_UNKNOWN_OR_UNDETERMINED_PREDICATE=true
REJECT_IF_MISSING_PREDICATE_DEFAULTED=true
REJECT_IF_ENDPOINT_PAIR_REVIEWED_IS_TREATED_AS_REAL_ENDPOINT_INSTANCE=true
REJECT_IF_PROPERTY_AUTHORITY_REVIEWED_IS_TREATED_AS_PROPERTY_SNAPSHOT=true
REJECT_IF_IDENTITY_SCHEMA_IS_TREATED_AS_IDENTITY_INSTANCE=true
REJECT_IF_FAIL_CLOSED_CONTRACT_IS_TREATED_AS_CANDIDATE_APPROVAL=true
REJECT_IF_CANDIDATE_ELIGIBILITY_IS_TREATED_AS_REAL_STATE_ADMISSION=true
```

The three layer boundaries are therefore explicit:

```ini
MODEL_CONTRACT_DOES_NOT_CREATE_REAL_INSTANCE=true
FAIL_CLOSED_CONTRACT_DOES_NOT_CREATE_AUTHORITY_CANDIDATE=true
AUTHORITY_CANDIDATE_DOES_NOT_CREATE_REAL_STATE=true
```

## 5. Positive candidate-construction rule

The only positive path is conjunctive. A future candidate may become eligible
for construction only when every model-level predicate is explicitly true:

```ini
SOURCE_MEAN_CANDIDATE_REQUIRES_ALL_MODEL_LEVEL_PREDICATES=true
PARTIAL_PREDICATE_SATISFACTION_NOT_ADMISSIBLE=true
```

The required predicates are:

```text
SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND=true
JMU_BULK_PRESSURE_RULE_BOUND=true
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID=true
SOURCE_MEAN_IDENTITY_AND_PROVENANCE_SCHEMA_BOUND=true
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND=true
```

`CANDIDATE_ELIGIBLE` is not `CANDIDATE_CREATED`, and neither state creates a
real source-mean instance. This task creates no candidate.

## 6. Contract lifecycle and current predicate status

This gate constructs a proposed contract. No existing repository precedent was
used to treat construction as external review or final binding. The safe
lifecycle is:

```ini
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_CONTRACT_CREATED=true
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_CONTRACT_ID=V07-T172-JMU-SOURCE-MEAN-FAIL-CLOSED-ADMISSION-RULE-CONTRACT-R1
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_CONTRACT_LIFECYCLE=PROPOSED
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_CONTRACT_INDEPENDENT_REVIEW=PENDING
NEW_AUTHORITY_SELF_APPROVAL=false
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND=false
SOURCE_MEAN_FAIL_CLOSED_PREDICATE_SATISFIED=undetermined
```

The other R73 predicate statuses are preserved, not recalculated into a
pressure-only conclusion:

```ini
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_ENDPOINT_PAIR_PREDICATE_SATISFIED=true
SOURCE_MEAN_PROPERTY_AUTHORITY_PREDICATE_SATISFIED=true
SOURCE_MEAN_IDENTITY_PROVENANCE_PREDICATE_SATISFIED=true
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATES=JMU_BULK_PRESSURE_RULE_BOUND;SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATE_COUNT=2
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=NOT_PROVEN
```

## 7. Real-instance guards and preserved parent state

```ini
REAL_REVIEWED_SHELL_INLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_OUTLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_ENDPOINT_PAIR_PRODUCER_FOUND=false
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_ID=NONE
SOURCE_MEAN_BULK_STATE_AUTHORITY_LIFECYCLE=NONE
SOURCE_MEAN_BULK_STATE_INDEPENDENT_REVIEW=NONE
```

The TASK172 parent ledger remains unchanged:

```ini
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No pressure qualification, endpoint creation, property evaluation, Jμ
execution, Q/film/material work, L2b/L3 numerical work, Ready, Merge or
downstream gate is performed.

## 8. Governance and next lifecycle event

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
PROPERTY_BACKEND_CALLED=false
PRESSURE_RULE_SELECTED=false
PRESSURE_AUTHORITY_CREATED=false
ENDPOINT_PRODUCER_CREATED=false
ENDPOINT_STATE_CREATED=false
SOURCE_MEAN_STATE_CREATED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
NEXT_GATE=AUTHORIZE_TASK172_JMU_SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
STOP=true
```

The companion JSON is the machine-readable source of the full rejection
matrix. The proposed contract must receive its separately authorized external
independent review before `SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND` can
be changed to `true`.
