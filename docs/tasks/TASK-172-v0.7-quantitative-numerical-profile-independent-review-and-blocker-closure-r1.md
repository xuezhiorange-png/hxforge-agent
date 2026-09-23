# TASK172 v0.7 — Quantitative numerical profile independent review and blocker closure R1

## Receipt

~~~ini
TASK_ID=TASK172_V0_7_QUANTITATIVE_NUMERICAL_PROFILE_INDEPENDENT_REVIEW_AND_BLOCKER_CLOSURE_R1
MODE=INDEPENDENT_REPLAY_AND_FROZEN_HOLDOUT_REVIEW_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=d4cf5e8c58188d648fb25b50dc0f5b5ce6206622
RESULT=REVIEWED_QUANTITATIVE_NUMERICAL_PROFILE_BLOCKER_CLOSED
~~~

The R92 and R92A candidate artifacts were replayed independently from their recorded inputs and frozen settings. The predeclared H01–H08 holdout passed without changing any parameter. The review accepts the numerical profile and its explicit residual-specific project acceptance policy for the scoped model-level system, and closes `NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW`. This is not a production solver implementation or a universal output-error guarantee.

## Independent replay and frozen holdout

Before any numerical solve, the holdout input artifact was hashed as file SHA-256 `23f707ba9eb21a34a01a7da454c7a34a6923f8e9e03a6a80bd812d55eb81b5c1` and canonical hash `205268c463409502dbedf04ca97121a4364f301718fe3f1c24b5ef29df6873cf`. The unchanged input matrix hash is `a82da762b4c70ac2c7adf412d417a5e979603b37074c5cf246cce4e3c85c99f2`. All eight frozen cases passed with `C_round=0.5`; no setting or input was retuned after observing holdout results. The result-matrix canonical hash is `915a713d0775eb9a26d00032b8afab5b997346a991fb6085de6554115238de99`.

| Replay set | Cases accepted | Independent oracle | Maximum nfev | Maximum callback calls |
|---|---:|---|---:|---:|
| R92 analytic fixtures | 10 (9 nonzero; exact zero branch separately) | exact analytic equations | — | — |
| R92 nonlinear shell-Jμ subset | 4/4 | bracketed scalar oracle | 4 | 16 |
| R92 complete nonzero matrix | 13/13 | analytic/scalar oracle replay | 4 | 16 |
| R92A tube-C3 and dual-active matrix | 16/16 | independent bracketed scalar oracle | 4 | 16 |
| Frozen H01–H08 holdout | 8/8 | independent 4097-point domain/monotonicity/bracket audit and Brent oracle | 4 | 16 |

The R92A replay exercised tube-side `(Pr_bulk/Pr_wall(Twi))^0.11`, shell-side `(mu_bulk/mu_wall(Two))^0.14`, and the unchanged three physical residuals together where applicable. All reviewed property, C3, and clean-wall Jμ domains were valid. The scalar construction is validation-only; no production scalar reduction is selected.

H04 returned negative signed `q_hc` and passed the numerical residual/oracle checks without absolute-value substitution or nonnegative clamping. Its thermal applicability disposition remains unbound; this review makes no applicability ruling.

## Frozen parameter adjudication

The candidate was reviewed as recorded, not optimized anew:

~~~text
method=trf; loss=linear
ftol=1e-6; xtol=1e-12; gtol=1e-12
jacobian=2-point; diff_step=1e-5
x_scale=[abs(q_hc_seed), abs(T_tube_bulk-T_shell_bulk), abs(T_tube_bulk-T_shell_bulk)]
residual_scale=abs(q_ts_seed); exact zero duty uses the separate exact branch
max_nfev=6; residual_callback_cap=24
tr_solver=exact; tr_options={}; f_scale=1; jac_sparsity=None
~~~

Each selected setting passes its separate review. R92A sensitivity supports the selected tolerance/Jacobian/scaling choices on the expanded matrix; the 3-point Jacobian exceeded the 24-call callback cap, while the selected 2-point strategy did not. The selected `diff_step=1e-5` passed; the tested `1e-6` alternative failed Candidate-C residual acceptance for two fixtures. Initialization-derived variable scaling passed and preserves the dimensional scales of duty and wall temperatures. The selected resource caps retain two nfev and eight callback calls of headroom over the maximum observed across the 37 nonzero R92/R92A/holdout solves. A cap hit remains a typed non-authoritative failure, never convergence evidence.

## Residual acceptance, stopping, and error-budget scope

The reviewed residual criterion is `C_RESIDUAL_SPECIFIC_ULP_OPERATION_BOUND`, with `C_round=0.5`, classified as `METHOD_SENSITIVITY_DERIVED_PROJECT_ACCEPTANCE_RULE`. It passed the R92A fixed matrix and the independent holdout. `C_round` was frozen before holdout execution and was not re-estimated from holdout. The criterion is a versioned project acceptance policy, **not** a formal or universal IEEE-754 error theorem.

Exact zero duty is handled only for the admitted passive clean network: equal bulk temperatures produce `q_hc=q_ts=0` and both wall temperatures equal the common bulk temperature, with no epsilon/deadband and no nonlinear solver invocation. Near-zero nonzero duty remains a nonlinear solve.

Solver termination and physical acceptance remain separate. A recorded solver-success fixture with unacceptable physical residuals is rejected. The final state still requires valid domains, evaluated active callbacks, acceptable physical residuals, admissible termination, and no active typed failure.

Canonical serialization round-tripped `q_hc`, both wall temperatures, and all three residual values bit-for-bit in the tested payload; observed quantization error was zero for those values. This is a measured serialization-path result, not a claim about every possible value or display formatting.

The combined observed validation envelope over 37 nonzero solver fixtures is:

~~~ini
COMPOSITE_MAX_Q_ORACLE_ERROR_W=2.9345414986892138e-12
COMPOSITE_MAX_TWI_ORACLE_ERROR_K=3.410605131648481e-13
COMPOSITE_MAX_TWO_ORACLE_ERROR_K=5.684341886080802e-14
ORACLE_ERROR_ENVELOPE_CLASSIFICATION=VALIDATION_ENVELOPE_ONLY
ORACLE_ERROR_ENVELOPE_IS_UNIVERSAL_PRODUCTION_BOUND=false
~~~

Only `ITERATION_ROOT_ERROR` and `SERIALIZATION_QUANTIZATION_ERROR` belong to this numerical budget. Property formulation, correlation model form, reference data, experimental uncertainty, and discretization error are not absorbed; discretization remains with mesh qualification. The observed envelope is not the residual stopping threshold and is not a universal runtime output-error guarantee.

## Reproducibility and lifecycle

The independent runner reproduced identical numerical-result matrix hashes across CPython 3.11.15 / SciPy 1.17.1 / NumPy 2.4.6, CPython 3.12.13 / SciPy 1.18.0 / NumPy 2.5.0, and CPython 3.14.5 / SciPy 1.18.0 / NumPy 2.5.0, each with CoolProp 8.0.0. Two same-environment raw-output replays matched byte-for-byte for each runtime. The holdout matrix, R92/R92A result matrix hashes, and replay records are bound in the structured evidence.

Effective numerical profile lifecycle is `REVIEWED_AUTHORITY` for the current scoped model-level profile: clean wall, reviewed tube branches, reviewed shell Jμ, pure ordinary water property profile where active wall-property callbacks require it, signed heat-rate semantics, deterministic direct initialization, and the R88 three-unknown/three-residual system. This review does not extend to fouled walls, new fluids or correlations, alternate residual systems, or other initialization architectures.

Accordingly, the numerical canonical blocker is removed. `MESH-CONVERGENCE-QUALIFICATION` remains the sole parent blocker. Entry authority is not complete; no mesh study, production implementation, production solve, Ready, or Merge is authorized by this receipt.
