# TASK172 v0.7 — Numerical error budget, stopping allocation and method sensitivity R1

## Receipt

~~~ini
TASK_ID=TASK172_V0_7_NUMERICAL_ERROR_BUDGET_STOPPING_QUANTITATIVE_ALLOCATION_AND_METHOD_SENSITIVITY_R1
MODE=CONTROLLED_TEST_FIXTURE_NUMERICAL_EXPERIMENT_AND_PROPOSED_PROFILE_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=dbba1624415f0ca845af46260bca08260e7b1936
HEAD_PRECONDITION_VERIFIED=true
RESULT=QUANTITATIVE_NUMERICAL_PROFILE_CANDIDATE_COMPLETED
NUMERICAL_ERROR_BUDGET_STOPPING_CANDIDATE_CREATED=true
NUMERICAL_ERROR_BUDGET_STOPPING_CANDIDATE_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
~~~

This gate ran controlled numerical fixtures and proposes a quantitative stopping/profile candidate for independent review. It did not change production equations or code, run a production solver, create a real case, perform a mesh study, or authorize implementation.

The frozen unknowns and physical residuals remain the R88 system, without modification:

~~~text
x = [q_hc, T_wall_inner, T_wall_outer]
q_ts = s_ts * q_hc

r_i = q_ts - h_i(T_wall_inner,...) A_i (T_tube_bulk - T_wall_inner)
r_w = q_ts - (T_wall_inner - T_wall_outer) / R_wall
r_o = q_ts - h_o(T_wall_outer,...) A_o (T_wall_outer - T_shell_bulk)
~~~

All physical residuals remain in W. The reviewed R91 J_mu authority is consumed only by the controlled one-support nonlinear fixture; no source, exponent, pressure rule, or fouling scope was reopened.

## Experiment design and boundaries

A deterministic test-only runner and separate result matrix cover:

- 10 exact analytic local-wall fixtures: both role orientations, signed positive/negative duty, exact zero, near-zero, and tube-film-, wall-, shell-film-dominated and balanced resistance.
- 4 one-support nonlinear J_mu fixtures: reviewed-scope HEOS ordinary-water viscosity and reviewed exponent 0.14, with synthetic HTC/area/wall-resistance parameters explicitly classified as numerical-method fixture parameters only.
- 9 failure/policy fixtures: missing state, support mismatch, property-domain excursion, nonfinite callback/residual, invalid resistance, negative duty without clamp, solver termination with unacceptable residual, and resource exhaustion.

The analytic class uses its closed-form resistance network as oracle. The J_mu class uses a separate validation-only scalar residual, a sign-changing physical bracket, and a 257-point monotonicity check before brentq; this is an oracle only, not a production scalar-method selection. Fixed support topology was used throughout. There was no randomization, network access, or production import side effect.

The numerical J_mu fixtures use the already reviewed narrow property profile: pure ordinary water, HEOS, DEF, stable single-phase liquid, 298.15–300 K and 100000–101325 Pa. The fixture pressure 101325 Pa is a located local-state input, not a new pressure rule.

## Proposed TRF profile and selection

The selected profile is explicit:

~~~ini
METHOD_CLASS=BOUND_AWARE_VECTOR_NONLINEAR_RESIDUAL_SOLVE
IMPLEMENTATION_CANDIDATE=SCIPY_OPTIMIZE_LEAST_SQUARES
SCIPY_METHOD=trf
LOSS=linear
FTOL=1e-6
XTOL=1e-12
GTOL=1e-12
JACOBIAN=2-point
DIFF_STEP=1e-5
X_SCALE=[abs(q_hc_seed), abs(T_tube_bulk-T_shell_bulk), abs(T_tube_bulk-T_shell_bulk)]
MAX_NFEV=6
TR_SOLVER=exact
TR_OPTIONS={}
F_SCALE=1.0
JAC_SPARSITY=NONE
~~~

Every SciPy control is passed explicitly; no SciPy tolerance or step default is promoted. Linear loss preserves the physical residual objective. The production profile remains a candidate, not executable authority.

The joint tolerance sweep tested common ftol/xtol/gtol values from 1e-6 through 1e-15. At 1e-6, 1e-8 and 1e-10 only 11/13 nonzero fixtures passed independent physical-residual acceptance. The first all-accepted joint anchor was 1e-12 (13/13). Tighter 1e-13 through 1e-15 remained on the observed output plateau but increased maximum nfev from 4 to 5. One-at-a-time sweeps then showed ftol could be relaxed to 1e-6 while retaining the tight xtol/gtol pair; xtol at 1e-6 and gtol through 1e-10 failed at least two fixtures, while the selected 1e-12 values passed all 13. The candidate exactly matches the first all-accepted joint-anchor output.

Plateau adjacency was tested against 0.25x, 0.5x, 1x and 2x the selected profile's observed independent-oracle error envelope. All three adjacent fully accepted pairs passed at every tested multiplier; the strictest tested 0.25x was retained as the comparison policy. This multiplier is a project numerical policy, not physical authority. It was itself sensitivity-tested.

The Jacobian sweep compared 2-point and 3-point real finite differences. Both passed all 13 fixtures, but 2-point used at most 16 residual callbacks versus 28 for 3-point, and its observed q error was lower on this matrix. Complex-step is excluded because the current property/correlation callbacks require real states. The selected finite-difference step 1e-5 tied the lowest callback maximum among accepted tested steps and matched the selected error envelope; the 1e-4 step had slightly more callbacks/nfev, 1e-3 increased oracle error, and smaller tested steps did not improve the observed envelope. Analytic/autodiff Jacobians were not bound.

Variable scaling compared an all-one scale, Jacobian scale, and initialization-derived vector. All three gave the same selected fixture output on this matrix; the candidate uses the derived vector because its coordinates are duty and two temperatures with distinct units and each scale follows the deterministic seed/driving force rather than an arbitrary constant.

The selected profile accepted all 13 nonzero fixtures. Maximum observed nfev and p95 were both 4; maximum residual-callback count was 16. The resource candidate is max_nfev=6, a 1.5x ceiling over the observed worst nfev, leaving two evaluations of observed headroom. For a 3-variable 2-point Jacobian, the explicit callback guard is 6×(1+3)=24, leaving eight callbacks of observed headroom. A deterministic perturbed-seed sensitivity case exhausted its cap and was correctly rejected; the candidate's admitted initialization remains the direct algebraic seed. Hitting either cap is a typed failure, never a convergence result.

## Scaling, residual acceptance and zero duty

The physical residual vector is unchanged and retains units W. For nonzero duty, the solver representation is:

~~~text
Q_scale = abs(q_ts_seed)
r_hat_j = r_j / Q_scale
~~~

A conductance-times-driving-temperature alternative failed residual acceptance on 2/13 fixtures. A seed-duty scale with a machine floor also passed, but no floor is needed because exact zero duty has a separate branch. No arbitrary 1 W denominator is used.

The proposed absolute physical residual rule is per support:

~~~text
max(abs(r_i, r_w, r_o)) <= G_ref * ulp(T_ref) + ulp(Q_scale)   [W]

G_ref = max(h_i,0 A_i, 1/R_wall, h_o,base A_o)
T_ref = max(abs(T_tube_bulk), abs(T_shell_bulk))
Q_scale = abs(q_ts_seed)
~~~

Relative residual tolerance is NOT_USED. The bound multiplier of 1.0 passed 13/13; 0.5 passed 6/13 and 2.0 passed 13/13. The selected multiplier is the machine-roundoff-derived bound, not a fitted engineering tolerance. The values are supported as a candidate over these fixed fixtures only; they are not claimed as a universal production error bound. A final production implementation must compute the corresponding quantities from its admitted callbacks and preserve all domain/authority gates.

For the numerical fixture, when bulk temperatures are exactly equal and the clean passive network is otherwise admitted, a separate deterministic exact branch returns q_hc=q_ts=0 and both wall temperatures equal to the common bulk temperature. It invokes no nonlinear solver and uses no epsilon or deadband. This is a proposed model branch, not an engineering instance receipt. Near-zero but nonzero driving force remains a solver case; relative q error is not reported when it would be dominated by a near-zero denominator.

## Independent observables and error budget

Across the 13 nonzero selected-profile fixtures:

~~~ini
SOLVER_SUCCESS_COUNT=13
POST_RESIDUAL_ACCEPTED_COUNT=13
MAX_NFEV=4
P95_NFEV=4
MAX_RESIDUAL_CALLBACK_COUNT=16
MAX_ABS_Q_ORACLE_ERROR=8.423539643587219e-13 W
MAX_ABS_T_WALL_ORACLE_ERROR=5.684341886080802e-14 K
MAX_SCALED_RESIDUAL_INF_NORM=2.335634741170615e-11
~~~

Near-zero q error is reported absolutely; no near-zero relative error is manufactured. A solver-success flag alone is not acceptance: one failure fixture deliberately terminates successfully with residuals outside the physical acceptance rule and is classified SOLVER_TERMINATED_RESIDUAL_UNACCEPTED.

The canonical JSON float round-trip path was exercised on q, both wall temperatures and all three residuals, including negative q. All tested binary float values round-tripped exactly: quantization error was 0 W and 0 K. Display rounding was excluded.

The proposed non-mesh budget combines only:

~~~ini
ITERATION_ROOT_ERROR=observed independent-oracle envelope on this fixed matrix
SERIALIZATION_QUANTIZATION_ERROR=0 W; 0 K for tested canonical float round trips
COMBINATION_RULE=COMPONENTWISE_LINEAR_SUM
Q_HC_OBSERVED_ENVELOPE=8.423539643587219e-13 W
T_WALL_INNER_OBSERVED_ENVELOPE=5.684341886080802e-14 K
T_WALL_OUTER_OBSERVED_ENVELOPE=5.684341886080802e-14 K
~~~

This is an observed candidate envelope, not a universal engineering guarantee. Property formulation/model error, correlation model-form uncertainty, reference/experimental error, and discretization error are explicitly excluded. Discretization remains delegated to mesh qualification.

## Stopping and failure semantics

~~~ini
SOLVER_SUCCESS_IS_ENGINEERING_ACCEPTANCE=false
RESIDUAL_ACCEPTANCE_SEPARATE=true
WALL_TEMPERATURE_ITERATION_TOLERANCE_APPLICABLE=false
PROPERTY_COUPLING_TOLERANCE_APPLICABLE=false
ROOT_INTERVAL_TOLERANCE_APPLICABLE=false
CUSTOM_STAGNATION_DETECTOR_ENABLED=false
CUSTOM_OSCILLATION_DETECTOR_ENABLED=false
MAX_NFEV_IS_CONVERGENCE_PROOF=false
NEGATIVE_Q_NUMERICALLY_ALLOWED=true
NEGATIVE_Q_APPLICABILITY_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
~~~

No separate wall-temperature fixed-point or property-coupling iteration exists in this simultaneous residual solve. Wall outputs are nevertheless quantified against the oracles. A future accepted result requires admissible solver termination, physical residual acceptance, valid final domains/authorities, all active correlations evaluated, and no active failure class. Last iterates and partial outputs remain diagnostic only.

Invalid property/correlation/material/domain callbacks use typed failure paths. No sentinel penalty residual, huge residual, NaN-as-success, nearest-bound clipping, hidden default, or authoritative partial result is allowed.

## Reproducibility and validation

The selected profile was run twice in one environment; result bytes and hashes matched. The same input matrix was replayed on trusted local CPython 3.11.15 and 3.12.13 runtimes. Both produced the same selected numeric-output and result-matrix hashes as CPython 3.14.5; each runtime also repeated bit-identically within itself. Python/SciPy/NumPy/CoolProp versions, platform, runner SHA-256 and matrix hashes are recorded in the machine-readable result artifact.

The validation did not run full pytest or any mesh refinement experiment. Exact-final-head GitHub CI remains a separate final gate and is not inferred from local checks.

~~~ini
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANDIDATE_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANONICAL_BLOCKER_REMOVED=false
LOCAL_RESIDUAL_AND_METHOD_MODEL_LEVEL_COMPLETE=true
EXECUTABLE_NUMERICAL_PROFILE_BOUND=false
DISCRETIZATION_ERROR_DELEGATED_TO_MESH_QUALIFICATION=true
MESH_CONVERGENCE_QUALIFICATION=OPEN
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=2
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=true
NUMERICAL_EXPERIMENT_IS_PRODUCTION_SOLVE=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_QUANTITATIVE_NUMERICAL_PROFILE_INDEPENDENT_REVIEW_AND_BLOCKER_CLOSURE_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
~~~

The structured evidence and result matrix bind the fixture-level observables, sweep IDs, hashes, and validation status.
