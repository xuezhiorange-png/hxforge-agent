# TASK172 v0.7 — local constitutive numerical method and failure contract R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_NUMERICAL_METHOD_AND_FAILURE_CONTRACT_R1
MODE=MODEL_LEVEL_LOCAL_CONSTITUTIVE_NUMERICAL_METHOD_AND_FAILURE_CONTRACT_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=c9a9f6a664dd6f15f128f08a6e2b1325d2505088
HEAD_PRECONDITION_VERIFIED=true
RESULT=RESOLVED_LOCAL_CONSTITUTIVE_METHOD_CONTRACT
```

This append-only contract converts the already bound local constitutive
unknown/residual structure into a reviewable numerical-method and failure
boundary. It does not change the R84 architecture, the R85/R85A sign-role
semantics, or the three-unknown/three-residual equation set. It does not
execute SciPy, a property backend, J_mu, a wall solve, a production solver or
a mesh study. It does not select quantitative tolerances, a Jacobian step,
resource cap, relaxation factor or engineering acceptance rule.

## 1. Historical and ownership boundary

The frozen inputs are the R84 local-closure overlay, the R85/R85A signed heat
and role overlays, and the R87 pinned open-source architecture audit. Their
registry extensions remain immutable:

```ini
R84_EXTENSION_REWRITTEN=false
R85_EXTENSION_REWRITTEN=false
R86_EXTENSION_REWRITTEN=false
R87_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
R84_ARCHITECTURE_DIRECTION_PRESERVED=true
R85_R85A_SIGN_ROLE_SEMANTICS_PRESERVED=true
R87_REFERENCE_ARCHITECTURE_USED_AS_NON_AUTHORITY_EVIDENCE=true
```

TASK171 supplies located identity, role/orientation and local state inputs.
TASK172 owns local property, wall/interface constitutive closure and its
numerical/failure profile. TASK174 remains the detailed hydraulic owner.
TASK173 remains the full rating/sizing boundary solver. TASK175 remains the
integration/Golden/release owner. No boundary is transferred by this
contract.

## 2. Frozen local system replay

For one admissible TASK171 physical support, the primary unknown vector is:

```ini
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_UNKNOWN_COUNT=3
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_EQUATION_COUNT=3
L2B_DEGREES_OF_FREEDOM_STATUS=CLOSED_MODEL_LEVEL_THREE_UNKNOWN_THREE_RESIDUAL
```

The known orientation is `s_ts ∈ {+1,-1}` and the stream-oriented heat rate
is derived without changing the unknown set:

```text
q_ts = s_ts q_hc
```

The physical residuals are preserved exactly at contract level:

```text
r_i = q_ts
     - h_i(T_wall_inner, located tube state, admitted tube profile)
       * A_i * (T_tube_bulk - T_wall_inner)

r_w = q_ts - (T_wall_inner - T_wall_outer) / R_wall

r_o = q_ts
     - h_o(T_wall_outer, located shell state, admitted shell profile)
       * A_o * (T_wall_outer - T_shell_bulk)
```

The residual definitions are physical quantities. Numerical scaling, if later
bound, is a separate representation and must not alter these equations.

The following R85A semantics remain active:

```ini
Q_HC_IS_SIGNED_UNKNOWN=true
Q_HC_POSITIVE_MEANS_HOT_TO_COLD=true
Q_HC_ZERO_MEANING=ZERO_LOCAL_HEAT_TRANSFER
Q_HC_NEGATIVE_ALLOWED_AT_MODEL_LEVEL=true
Q_HC_NEGATIVE_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
Q_HC_NONNEGATIVE_CLAMP_FORBIDDEN=true
HOT_COLD_ROLE_IS_EXPLICIT_TASK171_IDENTITY=true
HOT_COLD_ROLE_REASSIGNMENT_DURING_LOCAL_ITERATION=false
S_TS_ALLOWED_VALUES=+1;-1
Q_TS_RELATION=q_ts=s_ts*q_hc
```

## 3. Method-family adjudication

The adjudication uses the R87 architecture evidence and the existing project
dependency declaration `scipy>=1.14` in `pyproject.toml`. No external code is
copied and no dependency is changed.

| Candidate | Adjudication | Reason and boundary |
| --- | --- | --- |
| `BOUND_AWARE_TRUST_REGION_VECTOR_NONLINEAR_LEAST_SQUARES` | Selected as the model-level method family | Native three-component residual, explicit variable bounds, deterministic single-seed path and termination diagnostics fit the coupled wall/J_mu structure. A nonzero residual minimum is not an accepted physical root. |
| `scipy.optimize.least_squares(method="trf", loss="linear")` | Implementation candidate only | It is a candidate mapping of the selected family. It is not executed or promoted to production authority by this gate. `loss="linear"` preserves the meaning of the physical residual vector; it is not a robustness or acceptance rule. |
| Generic root/Newton family | Not selected | It is compatible with a square residual system, but its bound, invalid-trial, branch-boundary and derivative requirements are not yet sufficiently bound for the project contract. It remains a future comparison option. |
| Fixed-point iteration | Not selected as the primary method | It may describe an outer wall-property update pattern, but by itself does not establish robust simultaneous satisfaction of `r_i`, `r_w` and `r_o`, nor does it define invalid-trial or residual acceptance semantics. |
| Scalar reduction | Not selected | Algebraic elimination is possible on a restricted smooth branch, but callback domains, wall-property dependence, J_mu coupling and branch boundaries do not establish a globally valid continuous scalar residual. |

The selected result is therefore a method family, not an executable numerical
profile:

```ini
METHOD_CLASS=BOUND_AWARE_VECTOR_NONLINEAR_RESIDUAL_SOLVE
METHOD_FAMILY_BOUND=true
IMPLEMENTATION_CANDIDATE=SCIPY_OPTIMIZE_LEAST_SQUARES
SCIPY_METHOD=trf
LOSS=linear
PRODUCTION_SOLVER_EXECUTION_AUTHORIZED=false
```

### Scalar reduction

The wall equation permits the algebraic relation
`q_ts=(T_wall_inner-T_wall_outer)/R_wall`. On a fixed, smooth, authority-valid
branch, this can reduce the number of algebraic variables and may permit a
one-dimensional construction. That observation is not a proof that the
resulting residual is continuous, single-valued or valid across property,
J_mu, correlation and phase/domain branches. The contract therefore records:

```ini
SCALAR_REDUCTION_MATHEMATICALLY_POSSIBLE=true
SCALAR_REDUCTION_ROBUSTLY_AUTHORIZED=false
SCALAR_REDUCTION_SELECTED_FOR_TASK172=false
VECTOR_METHOD_REVIEW_REQUIRED=false
```

`VECTOR_METHOD_REVIEW_REQUIRED=false` means that the model-level family is
now selected for this contract. It does not mean that the implementation,
Jacobian, quantitative profile or production admission is complete.

## 4. Deterministic staged initialization

Initialization equations and accepted production equations are separate.

### I0 — input and domain admission

Before any trial or seed is generated, the admission layer must validate:

- TASK171 tube/shell identity, HOT/COLD role and `s_ts`;
- located tube and shell states, physical support and local pressure inputs;
- areas, `R_wall` and admitted wall/material authority;
- admitted tube and shell correlation profiles;
- property authorities and their applicable domains; and
- interface/wall identity and provenance.

Any missing, invalid or out-of-scope authority produces:

```ini
INITIALIZATION_STATUS=INITIALIZATION_NOT_STARTED
FAILURE_CLASS=INPUT_AUTHORITY_MISSING
```

No default value, hidden backend state, role inference, interpolation or
property extrapolation is allowed.

### I1 — neutral/base-film initialization

The only permitted neutral value in this contract is the identity value of a
known multiplicative wall-correction factor, and only as a numerical seed:

```ini
JMU_NEUTRAL_INITIALIZATION_CANDIDATE_VALUE=1.0
JMU_NEUTRAL_INITIALIZATION_IS_PRODUCTION_PHYSICS=false
JMU_NEUTRAL_INITIALIZATION_IS_INITIALIZATION_ONLY=true
JMU_ZERO_INITIALIZATION_TERM_FORBIDDEN=true
JMU_ZERO_INITIALIZATION_VALUE_FORBIDDEN=true
FINAL_ACCEPTED_RESULT_MUST_USE_FULL_ACTIVE_JMU=true
```

This does not authorize a J_mu physical equation, exponent, domain or wall
property source. If the admitted physical J_mu authority is absent, method
construction remains possible but execution admission remains blocked.

### Direct algebraic seed

If neutral/base-film coefficients can be evaluated lawfully, a deterministic
seed may be formed without changing the accepted equation set:

```text
R_i,0 = 1 / (h_i,0 A_i)
R_o,0 = 1 / (h_o,0 A_o)

q_ts,0 = (T_tube_bulk - T_shell_bulk)
         / (R_i,0 + R_wall + R_o,0)

T_wall_inner,0 = T_tube_bulk - q_ts,0 R_i,0
T_wall_outer,0 = T_shell_bulk + q_ts,0 R_o,0
q_hc,0 = s_ts q_ts,0
```

The seed is valid only after finite, domain and identity checks. It supports
tube-hot, shell-hot, zero heat transfer and a signed negative `q_hc`; it never
uses `abs(q)`, `max(q, 0)`, a nonnegative clamp, role swapping or temperature-
based role reassignment. If either base coefficient cannot be lawfully
computed:

```ini
INITIALIZATION_BASE_FILM_STATUS=BLOCKED
FAILURE_CLASS=INITIALIZATION_BASE_FILM_UNAVAILABLE
```

### I2 — complete-model restoration

After a valid seed, the solver adapter must restore all admitted physical
callbacks and the complete residual family. The temporary neutralization is
not part of the final residual:

```ini
TEMPORARY_SIMPLIFICATION_PRESENT_IN_FINAL_RESIDUAL=false
FINAL_ACTIVE_JMU_REQUIRED=true
FINAL_RESIDUAL_FAMILY=r_i;r_w;r_o
NO_INITIALIZATION_EQUATION_AS_FINAL=true
```

The production result is not accepted from the initialization equations.

## 5. Domain and trial-state policy

Bounds are authority-derived intersections, not convenience bounds.

```ini
Q_HC_DOMAIN=SIGNED
Q_HC_NONNEGATIVE_BOUND=false
Q_HC_NUMERIC_LOWER_BOUND=UNBOUND
Q_HC_NUMERIC_UPPER_BOUND=UNBOUND
WALL_TEMPERATURE_BOUNDS=INTERSECTION_OF_PROPERTY_MATERIAL_CORRELATION_INTERFACE_AND_STABLE_PHASE_DOMAINS
AUTOMATIC_BULK_TEMPERATURE_MIN_MAX_WALL_CLAMP=false
NEAREST_BOUND_CLIPPING=false
PROPERTY_EXTRAPOLATION=false
SILENT_PRESSURE_SUBSTITUTION=false
DEFAULT_MATERIAL=false
DEFAULT_FILM_COEFFICIENT=false
EMPTY_TRIAL_DOMAIN=NO_VALID_TRIAL_DOMAIN
DOMAIN_POLICY_BOUND=true
```

The solver may not force wall temperatures between the two bulk temperatures
unless a separate physical authority binds that restriction. Every trial must
pass finite, property-domain, correlation-domain, material-domain and
wall/interface identity checks.

Invalid trials are typed control-flow failures, not artificial optimization
objectives:

```ini
INVALID_TRIAL_TYPED_FAILURE_PATH=true
FAKE_PENALTY_RESIDUAL_ALLOWED=false
HUGE_SENTINEL_RESIDUAL_ALLOWED=false
NAN_AS_SUCCESS_ALLOWED=false
INVALID_TRIAL_MAY_BE_REPORTED_AS_NORMAL_RESIDUAL=false
```

The adapter may terminate the method with a typed failure and retain the
last iterate for diagnostics only. It may not manufacture `1e20`, `NaN` or a
hidden penalty to make an invalid physical state look optimizable.

## 6. Solver status versus physical acceptance

`least_squares` termination, if later implemented, is only one status. The
following statuses remain independent:

```ini
SOLVER_TERMINATION_STATUS=SEPARATE
RESIDUAL_ACCEPTANCE_STATUS=SEPARATE
PHYSICAL_APPLICABILITY_STATUS=SEPARATE
AUTHORITY_ADMISSION_STATUS=SEPARATE
SOLVER_SUCCESS_IS_ENGINEERING_ACCEPTANCE=false
RESIDUAL_ACCEPTANCE_SEPARATE=true
```

A future accepted local result requires all of the following, with values and
thresholds bound by later authority:

1. solver termination is admissible;
2. all physical residual criteria are satisfied;
3. final and trial states are finite and authority-valid;
4. physical applicability, including negative-heat disposition, is accepted;
5. all active correlations, wall mappings and J_mu relations are evaluated;
6. no failure class is active.

No final result is admitted solely because a solver reports success or because
the last iterate is available.

## 7. Unbound numerical profile

This contract intentionally leaves quantitative profile values unbound:

```ini
RESIDUAL_ABSOLUTE_TOLERANCE=UNBOUND
RESIDUAL_RELATIVE_TOLERANCE=UNBOUND
XTOL=UNBOUND
FTOL=UNBOUND
GTOL=UNBOUND
MAX_NFEV=UNBOUND
DIFF_STEP=UNBOUND
X_SCALE=UNBOUND
JACOBIAN_STRATEGY=UNBOUND_PENDING_NUMERICAL_PROFILE
STAGNATION_WINDOW=UNBOUND
STAGNATION_PROGRESS_THRESHOLD=UNBOUND
OSCILLATION_WINDOW=UNBOUND
OSCILLATION_THRESHOLD=UNBOUND
RESOURCE_CAP=UNBOUND
```

SciPy defaults are not HXForge authority. A later numerical-profile and
error-budget gate must bind tolerances, derivative strategy, scaling, stopping
and resource semantics before executable production admission.

Residual scaling is required for review because `r_i`, `r_w` and `r_o` can
have different conditioning even though the physical residuals are retained:

```ini
RESIDUAL_SCALING_REQUIRED_FOR_REVIEW=true
PHYSICAL_RESIDUAL_REPRESENTATION=PHYSICAL_UNSCALED_RESIDUALS
NUMERICAL_SCALED_RESIDUAL_REPRESENTATION=DIMENSIONLESS_OR_AUTHORITY_NORMALIZED
RESIDUAL_SCALING_CHANGES_PHYSICAL_EQUATIONS=false
RESIDUAL_SCALING_POLICY_STATUS=CONTRACT_SHAPE_BOUND_QUANTITATIVE_SCALE_UNBOUND
```

## 8. Failure taxonomy and signed negative heat

The following distinct typed outcomes are bound. None may return an
authoritative partial result:

```text
INPUT_AUTHORITY_MISSING
ROLE_ORIENTATION_UNBOUND
NO_VALID_TRIAL_DOMAIN
INITIALIZATION_BASE_FILM_UNAVAILABLE
INITIALIZATION_STATE_OUT_OF_DOMAIN
INITIALIZATION_FAILURE
PROPERTY_EVALUATION_FAILURE
CORRELATION_EVALUATION_FAILURE
MATERIAL_EVALUATION_FAILURE
NONFINITE_TRIAL
TRIAL_DOMAIN_EXCURSION
SINGULAR_OR_INVALID_RESISTANCE
SOLVER_NUMERICAL_FAILURE
SOLVER_RESOURCE_EXHAUSTION
SOLVER_TERMINATED_RESIDUAL_UNACCEPTED
FINAL_ACTIVE_JMU_UNAVAILABLE
FINAL_STATE_DOMAIN_INVALID
NEGATIVE_Q_APPLICABILITY_UNBOUND
NOT_CONVERGED
```

```ini
FAILURE_TAXONOMY_BOUND=true
FAILURE_MAY_RETURN_AUTHORITATIVE_PARTIAL_RESULT=false
LAST_ITERATE_ACCEPTED_AS_VALID_RESULT=false
LAST_ITERATE_AVAILABLE_FOR_DIAGNOSTICS=true
Q_HC_NEGATIVE_ALLOWED_AT_MODEL_LEVEL=true
NEGATIVE_Q_NUMERICALLY_ALLOWED=true
NEGATIVE_Q_APPLICABILITY_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
NEGATIVE_Q_IS_NUMERICAL_FAILURE=false
```

Stagnation, oscillation and resource-exhaustion names are structural states;
their windows, progress definitions, thresholds and caps remain delegated to
the numerical error/stopping authority.

## 9. Method-blocker adjudication and ledger

The following model-level contract dimensions are now bound:

```ini
LOCAL_RESIDUAL_STRUCTURE_BOUND=true
METHOD_FAMILY_BOUND=true
INITIALIZATION_ARCHITECTURE_BOUND=true
DOMAIN_POLICY_BOUND=true
FAILURE_TAXONOMY_BOUND=true
LOCAL_RESIDUAL_AND_METHOD_MODEL_LEVEL_COMPLETE=true
EXECUTABLE_NUMERICAL_PROFILE_BOUND=false
```

This closes the structural method gap only. It does not authorize a
production solver. The parent ledger is recomputed as:

```text
SHELL-WALL-CORRECTION-AUTHORITY
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=3
TASK172_ENTRY_AUTHORITY_COMPLETE=false
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=RESOLVED_MODEL_LEVEL_EXECUTABLE_PROFILE_UNBOUND
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
SHELL_WALL_CORRECTION_STATUS=BLOCKED
MESH_CONVERGENCE_QUALIFICATION=OPEN
```

The method contract itself is not an engineering acceptance, a physical J_mu
authority, a case receipt or an executable solver admission.

## 10. Open-source and governance boundary

R87's IDAES staged initializer, constraint restoration, scaling and failure
patterns are architecture evidence only. TESPy section residual organization
and Modelica equation-system patterns are likewise design references. No
open-source formula, default, tolerance, Jacobian step, resource limit or
solver behavior is promoted to HXForge authority.

```ini
OPEN_SOURCE_PHYSICAL_AUTHORITY_PROMOTED=false
OPEN_SOURCE_SOLVER_DEFAULTS_PROMOTED=false
OPEN_SOURCE_TOLERANCES_PROMOTED=false
DIRECT_CODE_IMPORT_AUTHORIZED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
LOCKFILE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
PRODUCTION_SOLVER_EXECUTION_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 11. Final receipt

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_NUMERICAL_METHOD_AND_FAILURE_CONTRACT_R1
RESULT=RESOLVED_LOCAL_CONSTITUTIVE_METHOD_CONTRACT
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=c9a9f6a664dd6f15f128f08a6e2b1325d2505088
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
SCALAR_REDUCTION_MATHEMATICALLY_POSSIBLE=true
SCALAR_REDUCTION_ROBUSTLY_AUTHORIZED=false
SCALAR_REDUCTION_SELECTED_FOR_TASK172=false
METHOD_CLASS=BOUND_AWARE_VECTOR_NONLINEAR_RESIDUAL_SOLVE
IMPLEMENTATION_CANDIDATE=SCIPY_OPTIMIZE_LEAST_SQUARES
SCIPY_METHOD=trf
LOSS=linear
INITIALIZATION_ARCHITECTURE_BOUND=true
INITIALIZATION_BASE_FILM_RULE=NEUTRAL_IDENTITY_FACTOR_ONLY_AS_INITIALIZATION_SEED;BASE_FILM_MUST_BE_AUTHORITY_VALID
JMU_NEUTRAL_INITIALIZATION_CANDIDATE_VALUE=1.0
JMU_ZERO_INITIALIZATION_FORBIDDEN=true
FULL_EQUATION_RESTORE_REQUIRED=true
Q_HC_SIGNED_UNKNOWN_PRESERVED=true
NEGATIVE_Q_NUMERICALLY_ALLOWED=true
NEGATIVE_Q_APPLICABILITY_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
DOMAIN_POLICY_BOUND=true
INVALID_TRIAL_POLICY=TYPED_FAIL_CLOSED_INVALID_TRIAL_PATH_NO_SENTINEL_PENALTY
FAKE_PENALTY_RESIDUAL_ALLOWED=false
SOLVER_SUCCESS_IS_ENGINEERING_ACCEPTANCE=false
RESIDUAL_ACCEPTANCE_SEPARATE=true
JACOBIAN_STRATEGY=UNBOUND_PENDING_NUMERICAL_PROFILE
RESIDUAL_SCALING_POLICY_STATUS=CONTRACT_SHAPE_BOUND_QUANTITATIVE_SCALE_UNBOUND
FAILURE_TAXONOMY_BOUND=true
LOCAL_RESIDUAL_STRUCTURE_BOUND=true
METHOD_FAMILY_BOUND=true
LOCAL_RESIDUAL_AND_METHOD_MODEL_LEVEL_COMPLETE=true
EXECUTABLE_NUMERICAL_PROFILE_BOUND=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=3
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_MINIMAL_GATE=AUTHORIZE_TASK172_NUMERICAL_ERROR_BUDGET_STOPPING_QUANTITATIVE_ALLOCATION_AND_METHOD_SENSITIVITY_R1_ONLY
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
PRODUCTION_SOLVER_EXECUTION_AUTHORIZED=false
EXACT_FINAL_HEAD_CI_RUN=RECORDED_IN_FINAL_RECEIPT
EXACT_FINAL_HEAD_CI=RECORDED_IN_FINAL_RECEIPT
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
