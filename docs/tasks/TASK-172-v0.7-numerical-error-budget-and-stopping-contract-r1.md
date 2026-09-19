# TASK172 v0.7 — Numerical Error-Budget and Stopping Contract R1

## 1. Scope and disposition

This document constructs the model-level numerical error-budget structure and
stopping-policy admission contract for TASK172. It does not select numerical
values, approve a solver, execute a numerical method, qualify a mesh, or close
the canonical numerical-error-budget-and-stopping-review blocker.

The reviewed numerical profile remains the governing framework:

- `NUMERICAL_PROFILE_AUTHORITY_ID=V07-T172-NUMERICAL-PROFILE-R1`.
- `EFFECTIVE_NUMERICAL_PROFILE_FRAMEWORK_STATUS=REVIEWED_MODEL_LEVEL_FRAMEWORK`.
- L2b remains `PAUSED_PENDING_REQUIRED_PHYSICAL_AUTHORITY_CLOSURE` and
  `METHOD_UNBOUND`.
- L3 remains paused pending a direct local-state producer or reviewed
  reconstruction-operator authority, and its method remains `METHOD_UNBOUND`.

The result of this gate is:

```ini
RESULT=RESOLVED
OUTCOME=OUTCOME_A_MODEL_LEVEL_ERROR_BUDGET_AND_STOPPING_CONTRACT_COMPLETE_QUANTITATIVE_ALLOCATION_UNBOUND
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANONICAL_BLOCKER_REMOVED=false
```

`RESOLVED` means that the model-level contract shape is complete. It does not
mean that any numerical tolerance, stopping threshold, resource cap, solver,
or executable stopping policy is authorized.

## 2. Error-contribution taxonomy

The contract keeps the following contributions separate:

| Component | Class | Default interpretation | Current quantitative status |
| --- | --- | --- | --- |
| `REFERENCE_DATA_ERROR` | Reference/source/data | Source precision, coverage, transcription, or reference-data limitation; not automatically stochastic | Unbound |
| `PROPERTY_FORMULATION_ERROR` | Property/model-form | Property authority, domain, formulation, or backend-reproduction distinction | Unbound |
| `CORRELATION_MODEL_FORM_ERROR` | Correlation/model-form | Correlation discrepancy and domain uncertainty; not numerical noise by default | Unbound |
| `DISCRETIZATION_ERROR` | Numerical/model representation | Spatial or support discretization contribution | Delegated to open mesh qualification |
| `ITERATION_ROOT_ERROR` | Numerical | Error from an actually reviewed iterative/root method | Unquantified because L2b/L3 methods are unbound |
| `SERIALIZATION_QUANTIZATION_ERROR` | Representation/numerical | Internal precision, canonical serialization, and display rounding effects | Unbound |

Every component record must contain an immutable component ID, class, owner,
physical-or-numerical classification, systematic-or-stochastic status,
affected observables, source authority, domain, estimation-method status,
combination eligibility, and lifecycle status. A component may not be moved
between classes merely to make a combination rule available.

### 2.1 Reference and property semantics

Reference-data precision and coverage are not automatically random samples:

```ini
REFERENCE_DATA_ERROR_CONTRACT_BOUND=true
REFERENCE_DATA_ERROR_AUTOMATICALLY_RANDOM=false
REFERENCE_DATA_ERROR_AUTOMATIC_RSS_ELIGIBLE=false
```

Property-authority/domain uncertainty is distinct from backend evaluation or
reproduction behavior:

```ini
PROPERTY_FORMULATION_ERROR_CONTRACT_BOUND=true
PROPERTY_MODEL_UNCERTAINTY_EQUALS_SOLVER_TOLERANCE=false
PROPERTY_BACKEND_REPRODUCTION_TOLERANCE_REUSABLE_AS_ROOT_TOLERANCE=false
```

No property backend is called by this gate, and no property domain is widened.

### 2.2 Correlation and discretization semantics

Correlation/model-form discrepancy is not automatically random numerical noise:

```ini
CORRELATION_MODEL_FORM_ERROR_CONTRACT_BOUND=true
CORRELATION_MODEL_FORM_ERROR_AUTOMATIC_RSS_ELIGIBLE=false
CORRELATION_DOMAIN_UNCERTAINTY_REUSABLE_AS_ITERATION_TOLERANCE=false
```

Discretization is a distinct contribution, but its estimator belongs to the
separate mesh authority:

```ini
DISCRETIZATION_ERROR_CONTRACT_BOUND=true
DISCRETIZATION_ERROR_ESTIMATOR_BOUND=false
DISCRETIZATION_ERROR_DELEGATED_TO_MESH_QUALIFICATION=true
MESH_CONVERGENCE_QUALIFICATION=OPEN
```

No order of convergence, Richardson extrapolation, mesh-doubling rule, mesh
norm, or mesh threshold is inferred.

### 2.3 Iteration/root and serialization semantics

`ITERATION_ROOT_ERROR` may be quantified only after an actual numerical method,
residual identity, and sensitivity/acceptance authority have been reviewed:

```ini
ITERATION_ROOT_ERROR_CONTRACT_BOUND=true
ACTUAL_ITERATION_ROOT_ERROR_QUANTIFIED=false
L2B_METHOD_STATUS=METHOD_UNBOUND
L3_METHOD_STATUS=METHOD_UNBOUND
```

Serialization/quantization remains separate from physical/model-form error:

```ini
SERIALIZATION_QUANTIZATION_ERROR_CONTRACT_BOUND=true
DISPLAY_ROUNDING_EQUALS_INTERNAL_NUMERICAL_ERROR=false
CANONICAL_SERIALIZATION_PRECISION_AUTOMATICALLY_ENGINEERING_ACCEPTABLE=false
```

Source precision, internal numerical precision, canonical representation, and
display rounding must be named separately in any later estimate.

## 3. Combination policy

The model-level combination contract is complete, but no combination is
authorized. A future rule must identify every component, units, statistical or
systematic interpretation, dependency/correlation assumptions, observable,
sensitivity/propagation method, and domain.

```ini
ERROR_COMPONENT_COMBINATION_POLICY_CONTRACT_BOUND=true
AUTOMATIC_ROOT_SUM_SQUARE_ALLOWED=false
AUTOMATIC_LINEAR_SUM_ALLOWED=false
AUTOMATIC_WORST_CASE_MAX_ALLOWED=false
QUANTITATIVE_NUMERICAL_ERROR_BUDGET_BOUND=false
COMBINED_NUMERICAL_ERROR_BUDGET_BOUND=false
```

In particular, RSS is not available merely because several numbers exist; a
linear sum or worst-case maximum is not an automatic fallback. The engineering
principle is structural only:

```ini
NUMERICAL_ERROR_MUST_NOT_DOMINATE_ACCEPTED_ENGINEERING_UNCERTAINTY=true
ENGINEERING_ACCEPTANCE_BUDGET_ACTUAL_VALUE_BOUND=false
NUMERICAL_ERROR_ALLOCATION_ACTUAL_VALUE_BOUND=false
```

No percentage, absolute value, safety fraction, or Golden value is introduced.

## 4. Stopping-admission contract

Stopping is residual-specific. A heat-rate residual in W, a temperature
residual in K, property-state validity, and an enthalpy residual in W are not
collapsed into one anonymous dimensionless value:

```ini
STOPPING_POLICY_RESIDUAL_SPECIFIC=true
GENERIC_SINGLE_STOPPING_ERROR_METRIC_ALLOWED=false
```

An admissible future stop record must identify, at minimum:

1. `RESIDUAL_IDENTITY_VALID`;
2. `STATE_IDENTITY_VALID`;
3. `ALL_REQUIRED_INPUT_AUTHORITIES_VALID`;
4. `FINITE_VALUES`;
5. `DOMAIN_SAFE`;
6. `METHOD_STATUS_VALID`;
7. `RESIDUAL_CRITERION_SATISFIED`;
8. `STATE_UPDATE_CRITERION_IF_REQUIRED`;
9. `ENERGY_CLOSURE_CRITERION_IF_REQUIRED`;
10. `PROPERTY_COUPLING_CRITERION_IF_REQUIRED`;
11. `MESH_STATUS_IF_REQUIRED`; and
12. `NO_FAILURE_CLASS_ACTIVE`.

This structural schema is bound without binding any numeric predicate:

```ini
STOPPING_ADMISSION_PREDICATE_SCHEMA_BOUND=true
```

Successful iteration is not engineering acceptance, and bookkeeping closure is
not physical closure:

```ini
CONVERGED_LOCAL_ITERATION_EQUALS_ENGINEERING_ACCEPTANCE=false
ZERO_BOOKKEEPING_RESIDUAL_EQUALS_PHYSICAL_CLOSURE=false
WALL_ITERATION_STATUS_SEPARATE=true
PROPERTY_COUPLING_STATUS_SEPARATE=true
MESH_CONVERGENCE_STATUS_SEPARATE=true
ENERGY_CLOSURE_STATUS_SEPARATE=true
SEPARATE_NUMERICAL_STATUS_MODEL_PRESERVED=true
```

### 4.1 Tolerance classes and zero-duty behavior

The contract names, but does not populate, the tolerance classes:

- local heat-rate residual tolerance;
- wall-temperature residual tolerance;
- property-coupling tolerance;
- energy-closure tolerance; and
- root interval or state tolerance, if an admitted method requires one.

```ini
NUMERICAL_TOLERANCE_CLASS_SCHEMA_BOUND=true
ABSOLUTE_RELATIVE_TOLERANCE_POLICY_SCHEMA_BOUND=true
LOCAL_RESIDUAL_TOLERANCE_BOUND=false
PROPERTY_COUPLING_TOLERANCE_BOUND=false
WALL_TEMPERATURE_TOLERANCE_BOUND=false
ENERGY_CLOSURE_TOLERANCE_BOUND=false
ROOT_INTERVAL_TOLERANCE_BOUND=false
ZERO_DUTY_STOPPING_POLICY_REQUIRED=true
ZERO_DUTY_STOPPING_POLICY_BOUND=false
```

Any later tolerance must declare whether it is absolute or relative, its
reference scale, zero/near-zero behavior, and units. This gate does not choose
an absolute-only or relative-only policy and does not invent a denominator
floor or zero-duty epsilon.

### 4.2 Resource, stagnation, oscillation, and failure semantics

Resource caps are safety limits, not convergence or mesh-adequacy proofs:

```ini
RESOURCE_CAP_POLICY_CONTRACT_BOUND=true
MAX_ITER_IS_CONVERGENCE_PROOF=false
MAX_MESH_IS_MESH_ADEQUACY_PROOF=false
MAX_ITER_BOUND=false
MAX_MESH_REFINEMENT_BOUND=false
RESOURCE_CAP_REACHED_WITHOUT_CONVERGENCE=NOT_CONVERGED_BLOCKED
```

The future stagnation contract must identify a history window, progress
metric, residual/state quantity, threshold, and minimum history length. The
future oscillation contract must identify history, observable, sign/direction/
period interpretation, and threshold. Their schemas are bound without values:

```ini
STAGNATION_DETECTION_CONTRACT_SCHEMA_BOUND=true
STAGNATION_WINDOW_BOUND=false
STAGNATION_PROGRESS_METRIC_BOUND=false
STAGNATION_THRESHOLD_BOUND=false
OSCILLATION_DETECTION_CONTRACT_SCHEMA_BOUND=true
OSCILLATION_WINDOW_BOUND=false
OSCILLATION_THRESHOLD_BOUND=false
```

The failure taxonomy is structural and fail-closed:

```ini
NUMERICAL_FAILURE_TAXONOMY_BOUND=true
FAILURE_CLASSES=NONFINITE,INVALID_PROPERTY_STATE,DOMAIN_EXCURSION,NO_BRACKET,SURFACE_INCONSISTENCY,STAGNATION,OSCILLATION,RESOURCE_EXHAUSTION,NOT_CONVERGED
LAST_ITERATE_ACCEPTED_AS_VALID_RESULT=false
LAST_ITERATE_AVAILABLE_FOR_DIAGNOSTICS=true
UNDER_RELAXATION_STATUS=NOT_SELECTED
RELAXATION_FACTOR_BOUND=false
```

Resource exhaustion, stagnation, oscillation, domain failure, or nonconvergence
may expose diagnostic state/history only. None is an engineering success.

Library defaults are not authority:

```ini
LIBRARY_DEFAULT_NUMERICAL_TOLERANCE_PROMOTED=false
LIBRARY_DEFAULT_MAX_ITER_PROMOTED=false
LIBRARY_DEFAULT_STOPPING_POLICY_PROMOTED=false
```

## 5. Historical threshold inventory

The repository was audited for existing TASK172/TASK171/TASK166/TASK037/v0.6
thresholds. The following values or limits were observed, but none is promoted
to TASK172 stopping authority by this gate:

| Source/class | Observed item | Classification | TASK172 transfer disposition |
| --- | --- | --- | --- |
| TASK-170 §20 / TASK-169 v0.6 | `0.001` energy-balance and global thermal-duty acceptance ceilings | `LEGACY_ACCEPTANCE_ONLY` | Not a local solver tolerance; no transfer authority |
| TASK-170 §20 / TASK-169 v0.6 | `0.02` published shell h/DP reference comparison ceilings | `LEGACY_ACCEPTANCE_ONLY` | Reference-profile acceptance only |
| TASK-170 §20 / TASK-169 v0.6 | `0.005` direct published-equation reproduction ceiling | `SOURCE_SPECIFIC` | Equation reproduction is not root/stopping error |
| TASK-170 §20 | outlet temperature, segment duty closure, rating-duty reference, wall iteration values marked `UNBOUND` | `POTENTIALLY_TRANSFERABLE_WITH_REVIEW` only as a gap marker | No value to transfer |
| TASK-170 / TASK-169 | exact canonical replay, hard constraints, membership, and Python parity | `LEGACY_ACCEPTANCE_ONLY` | Identity/admission checks, not a residual tolerance |
| TASK-171 | bounded record/depth/string resource limits and exact Decimal bookkeeping | `RESOURCE_LIMIT_ONLY` / `UNRELATED_METHOD` | Not mesh convergence or numerical stopping authority |
| TASK-166 | source correlation branch boundaries and exact uniform-spacing `Js=1` branch | `SOURCE_SPECIFIC` | Correlation dispatch, not an iteration tolerance |
| TASK-037 | `1E-10 m²` area quantization and `ROUND_HALF_EVEN` | `SOURCE_SPECIFIC` | Geometry/serialization identity, not root tolerance |
| TASK-160/161/162 v0.6 | explicit `TOLERANCE_CHANGE=false` and no new energy tolerance | `UNRELATED_METHOD` | No TASK172 transfer authority |
| TASK-009/TASK-010 legacy solver material | `1e-3 W`, `1e-8` relative, `1e-4 K`, and `MAX_ITER=100` | `UNRELATED_METHOD` / legacy | Different method/scope; not transferable |
| Property backends | saturation/reproduction tolerances such as `1e-6` and percent-level state-point checks | `SOURCE_SPECIFIC` | Backend/domain/reproduction behavior, not root tolerance |

Therefore:

```ini
EXISTING_NUMERICAL_THRESHOLD_INVENTORY_BOUND=true
EXISTING_NUMERICAL_THRESHOLD_TRANSFER_AUTHORITY_BOUND=false
```

No existing value is silently promoted, and no library default is used.

## 6. Dependency graphs

The error-budget dependency graph is bound at model level:

```text
physical/source authority
  -> accepted engineering-uncertainty context
property/correlation authority
  -> property/model-form contribution
reviewed numerical method
  -> iteration/root contribution
reviewed mesh qualification
  -> discretization contribution
serialization contract
  -> representation contribution
all admitted contributions
  -> future quantitative error-budget allocation
```

The missing nodes remain unbound. In particular, there is no L2b/L3 method,
mesh estimator, or quantitative allocation in this gate:

```ini
NUMERICAL_ERROR_BUDGET_DEPENDENCY_GRAPH_BOUND=true
```

The stopping-policy dependency graph is also structural:

```text
actual residual identity
  + actual method
  + valid domain
  + error-budget allocation
  + residual-specific tolerance
  + state/status rules
  -> executable stopping policy
```

Because the actual method, quantitative budget, and tolerances are absent:

```ini
STOPPING_POLICY_DEPENDENCY_GRAPH_BOUND=true
EXECUTABLE_STOPPING_POLICY_BOUND=false
```

## 7. Candidate lifecycle and preserved blockers

The model-level candidate is recorded but not self-approved:

```ini
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_CANDIDATE_CREATED=true
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_ID=V07-T172-NUMERICAL-ERROR-BUDGET-STOPPING-CONTRACT-R1
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY
NUMERICAL_ERROR_BUDGET_STOPPING_INDEPENDENT_REVIEW=PENDING
NEW_AUTHORITY_SELF_APPROVAL=false
```

The physical and numerical branches remain frozen. In particular, shell-wall
correction is `BLOCKED`, J_mu executable authority is false, L2b and L3 methods
are unbound, and mesh qualification remains open. The effective entry blockers
remain exactly:

```ini
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

This candidate therefore does not remove the canonical blocker:

```ini
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANONICAL_BLOCKER_REMOVED=false
```

## 8. Governance and final receipt

Only documentation/evidence and an append-only registry extension are changed.
There is no production code, engineering calculation, numerical experiment,
mesh study, dependency, lockfile, workflow, Ready, or Merge action.

The following receipt intentionally leaves final commit/CI fields for the
external task receipt. Embedding the final commit hash in a file whose content
is itself committed would create a self-referential hash; the exact values are
reported after commit and exact-head CI.

```ini
TASK_ID=TASK172_V0_7_NUMERICAL_ERROR_BUDGET_AND_STOPPING_CONTRACT_R1
RESULT=RESOLVED
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=42a35271b791188da8215f79d044c492b6cff675
FINAL_HEAD_SHA=TO_BE_RECORDED_AFTER_COMMIT_AND_EXACT_HEAD_CI

NUMERICAL_ERROR_BUDGET_COMPONENT_TAXONOMY_BOUND=true
NUMERICAL_ERROR_COMPONENT_SCHEMA_BOUND=true
REFERENCE_DATA_ERROR_CONTRACT_BOUND=true
PROPERTY_FORMULATION_ERROR_CONTRACT_BOUND=true
CORRELATION_MODEL_FORM_ERROR_CONTRACT_BOUND=true
DISCRETIZATION_ERROR_CONTRACT_BOUND=true
ITERATION_ROOT_ERROR_CONTRACT_BOUND=true
SERIALIZATION_QUANTIZATION_ERROR_CONTRACT_BOUND=true
ERROR_COMPONENT_COMBINATION_POLICY_CONTRACT_BOUND=true
AUTOMATIC_ROOT_SUM_SQUARE_ALLOWED=false
AUTOMATIC_LINEAR_SUM_ALLOWED=false
AUTOMATIC_WORST_CASE_MAX_ALLOWED=false
QUANTITATIVE_NUMERICAL_ERROR_BUDGET_BOUND=false
COMBINED_NUMERICAL_ERROR_BUDGET_BOUND=false
STOPPING_ADMISSION_PREDICATE_SCHEMA_BOUND=true
NUMERICAL_TOLERANCE_CLASS_SCHEMA_BOUND=true
ABSOLUTE_RELATIVE_TOLERANCE_POLICY_SCHEMA_BOUND=true
ZERO_DUTY_STOPPING_POLICY_REQUIRED=true
ZERO_DUTY_STOPPING_POLICY_BOUND=false
RESOURCE_CAP_POLICY_CONTRACT_BOUND=true
MAX_ITER_BOUND=false
MAX_MESH_REFINEMENT_BOUND=false
STAGNATION_DETECTION_CONTRACT_SCHEMA_BOUND=true
STAGNATION_WINDOW_BOUND=false
STAGNATION_PROGRESS_METRIC_BOUND=false
STAGNATION_THRESHOLD_BOUND=false
OSCILLATION_DETECTION_CONTRACT_SCHEMA_BOUND=true
OSCILLATION_WINDOW_BOUND=false
OSCILLATION_THRESHOLD_BOUND=false
LAST_ITERATE_ACCEPTED_AS_VALID_RESULT=false
NUMERICAL_FAILURE_TAXONOMY_BOUND=true
RELAXATION_FACTOR_BOUND=false
EXISTING_NUMERICAL_THRESHOLD_INVENTORY_BOUND=true
EXISTING_NUMERICAL_THRESHOLD_TRANSFER_AUTHORITY_BOUND=false
NUMERICAL_ERROR_BUDGET_DEPENDENCY_GRAPH_BOUND=true
STOPPING_POLICY_DEPENDENCY_GRAPH_BOUND=true
EXECUTABLE_STOPPING_POLICY_BOUND=false
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_CANDIDATE_CREATED=true
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_ID=V07-T172-NUMERICAL-ERROR-BUDGET-STOPPING-CONTRACT-R1
NUMERICAL_ERROR_BUDGET_STOPPING_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY
NUMERICAL_ERROR_BUDGET_STOPPING_INDEPENDENT_REVIEW=PENDING
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANONICAL_BLOCKER_REMOVED=false
NUMERICAL_TOLERANCES_BOUND=false
LOCAL_RESIDUAL_TOLERANCE_BOUND=false
PROPERTY_COUPLING_TOLERANCE_BOUND=false
WALL_TEMPERATURE_TOLERANCE_BOUND=false
ENERGY_CLOSURE_TOLERANCE_BOUND=false
ROOT_INTERVAL_TOLERANCE_BOUND=false
MESH_CONVERGENCE_QUALIFICATION=OPEN
MESH_CONVERGENCE_RULE_BOUND=false
L2B_METHOD_STATUS=METHOD_UNBOUND
L3_METHOD_STATUS=METHOD_UNBOUND
PRODUCTION_NUMERICAL_METHOD_AUTHORIZED=false
TASK172_NUMERICAL_EXECUTION_AUTHORIZED=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
JMU_EXECUTABLE_AUTHORITY_BOUND=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
LOCAL_VALIDATION=TO_BE_RECORDED_AFTER_ARTIFACT_VALIDATION
INTERMEDIATE_GITHUB_CI_RUNS=
EXACT_FINAL_HEAD_CI_RUN=TO_BE_RECORDED
EXACT_FINAL_HEAD_CI=TO_BE_RECORDED
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_NUMERICAL_ERROR_BUDGET_STOPPING_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
