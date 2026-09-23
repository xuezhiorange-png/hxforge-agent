# TASK172 v0.7 — Quantitative numerical profile coverage and roundoff robustness R92A

## Receipt

~~~ini
TASK_ID=TASK172_V0_7_QUANTITATIVE_NUMERICAL_PROFILE_COVERAGE_AND_ROUNDOFF_ROBUSTNESS_R92A
MODE=TARGETED_R92_NONLINEAR_COVERAGE_AND_RESIDUAL_ACCEPTANCE_REQUALIFICATION
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=393ff58a699e1baec9e4fed83fa91aa7a09e9949
RESULT=QUANTITATIVE_NUMERICAL_PROFILE_COVERAGE_COMPLETED
~~~

R92 is unchanged and remains historical evidence. This append-only R92A extension adds active tube-side C3 coverage, simultaneous tube-C3/shell-J_mu coverage, resistance-ratio stress, residual-acceptance sensitivity and direct-seed resource-cap requalification. It does not promote a numerical authority, close a blocker, change production code, or perform a mesh study.

## Frozen equations and authority boundary

The R88 unknown vector and physical residual identities are replayed unchanged:

~~~text
x = [q_hc, T_wall_inner, T_wall_outer]
q_ts = s_ts * q_hc
r_i = q_ts - h_i(T_wall_inner,...) A_i (T_tube_bulk-T_wall_inner)
r_w = q_ts - (T_wall_inner-T_wall_outer)/R_wall
r_o = q_ts - h_o(T_wall_outer,...) A_o (T_wall_outer-T_shell_bulk)
~~~

Every fixture activates the already reviewed tube C3 wall factor
`(Pr_bulk/Pr_wall)^0.11`, within its strict Reynolds, Prandtl, ratio and water-property domains. D-series fixtures also activate the reviewed clean-profile shell factor `(mu_bulk/mu_wall)^0.14`; C-series shell correction is held at the multiplicative identity solely to isolate tube-side nonlinearity. No correlation authority was reopened. HEOS property calls use the reviewed pure ordinary-water, stable-liquid profile at the fixture's located local pressure state; that pressure value is fixture input, not a pressure rule. All HTC, area and wall-resistance values are synthetic numerical-method fixture parameters, not geometry or engineering authority.

## Extended fixed-topology fixture matrix

The deterministic matrix contains 16 one-support nonlinear fixtures:

- C01–C04 exercise tube C3 alone: tube-hot, shell-hot, near-zero nonzero duty and negative `q_hc` relative to the assigned role.
- D01–D04 exercise tube C3 and shell J_mu simultaneously for the same role/sign cases.
- C05–C08 and D05–D08 exercise tube-film-dominant, wall-dominant, shell-film-dominant and balanced resistance partitions. Dominant partitions use resistance fractions 0.90/0.05/0.05 (18:1 against either other component); balanced uses 1/3 per component.

Each smooth fixture has an independent validation-only scalar reduction. Before `brentq`, a deterministic 4097-point scan over the reviewed temperature interval verifies a contiguous valid domain, strict monotonicity and a strict sign-changing bracket; every root is then checked against the full three-residual vector system. `brentq` is only an oracle for these fixtures. Production scalar reduction remains unselected. All 16 oracle audits and all selected-profile solves passed; all final wall-temperature trials remained within the reviewed property domain.

Observed on this fixed synthetic matrix, the selected explicit TRF profile achieved 16/16 solver terminations and 16/16 independent residual acceptances. Maximum observed absolute oracle errors were `3.852473895449293e-13 W` for signed duty and `3.410605131648481e-13 K` for either wall temperature; maximum scaled residual infinity norm was `1.2049450253531765e-9`. These are fixture observations, not universal engineering bounds.

## Residual acceptance requalification

The physical residuals remain in W. Three alternatives were replayed using the actually evaluated trial-state `h_i(T_wi)A_i`, `1/R_wall`, `h_o(T_wo)A_o`, and heat-flow terms:

1. Candidate A: the R92 reference-conductance/temperature/duty ULP rule.
2. Candidate B: the same shape with the maximum active evaluated conductance.
3. Candidate C: a residual-specific arithmetic/ULP allowance for each subtraction and heat-flow evaluation, multiplied by an explicit `C_round`.

For Candidate C the tested multipliers were 0.5, 1, 2, 4 and 8. The smallest tested multiplier passing all 16 fixtures was `C_round=0.5`; Candidate C accepted 16/16. At multiplier 0.5, Candidates A and B each accepted 13/16; at multiplier 1, A, B and C each accepted 16/16. The selected Candidate C bound accounts for active inner and outer conductances and each residual's evaluated flow terms. Its status is `METHOD_SENSITIVITY_DERIVED_PROJECT_ACCEPTANCE_RULE`, not a formal floating-point theorem. Accordingly:

~~~ini
R92_ROUNDOFF_RULE_FIXTURE_VALIDATED=true
R92_ROUNDOFF_RULE_UNIVERSAL_BOUND_PROVEN=false
FORMAL_FLOATING_POINT_THEOREM_CLAIMED=false
~~~

The exact per-residual expressions and the full multiplier/pass-count matrix are in the results artifact. Independent review is still required before any proposed acceptance rule can be treated as authority.

## Sensitivity and requalified candidate profile

The enlarged matrix retained the R92 numerical settings; R92's separate residual-acceptance claim is reclassified by the R92A sensitivity evidence above. The selected solver candidate remains explicit:

~~~ini
METHOD=trf
LOSS=linear
FTOL=1e-6
XTOL=1e-12
GTOL=1e-12
JACOBIAN=2-point
DIFF_STEP=1e-5
X_SCALE=[abs(q_hc_seed),abs(T_tube_bulk-T_shell_bulk),abs(T_tube_bulk-T_shell_bulk)]
MAX_NFEV=6
RESIDUAL_SCALE=abs(q_ts_seed)
RESIDUAL_CALLBACK_CAP=24
TR_SOLVER=exact
~~~

The explicit sensitivity matrix covers ftol, xtol, gtol, 2-point versus 3-point Jacobians, diff_step, three x-scale policies, three residual-scale policies, joint tolerance anchors and max_nfev 6/8/12/16. The selected profile passed all 16. Looser xtol values 1e-6 and 1e-8 accepted only 2/16 and 5/16 respectively; gtol 1e-8 and 1e-10 accepted 5/16. Both Jacobian schemes and all x-scales passed, but 2-point required at most 16 residual callbacks versus 28 for 3-point. The selected 1e-5 difference step had the lowest observed q-oracle error among the tested steps while passing all fixtures. Seed-duty and seed-duty-with-ULP-floor residual scaling both passed; active-conductance-times-driving-temperature scaling passed only 9/16, so the simpler seed-duty scaling is retained. Exact zero remains handled by the separately reviewed zero-duty branch and is not divided by a scale.

All tested direct-seed caps 6, 8, 12 and 16 passed 16/16; maximum observed `nfev` was 4 and maximum callback count was 16. The requalified choice remains the smallest tested cap meeting the explicit headroom rule: `max_nfev=6`, two observed function evaluations of headroom, and the 2-point callback guard `6*(1+3)=24`, leaving eight observed callbacks of headroom. The cap is a resource guard, never proof of convergence. Perturbed-seed behavior is not a production requirement because only the deterministic direct algebraic seed is admitted by this candidate.

Thus:

~~~ini
R92_PROFILE_SETTINGS_PRESERVED=true
R92A_SUPERSEDING_PROFILE_CREATED=false
RESOURCE_CAP_REQUALIFIED=true
MAX_NFEV_IS_CONVERGENCE_PROOF=false
~~~

## Cross-runtime replay and scope limits

The final candidate was replayed in isolated Python 3.11 and 3.12 environments, in addition to the primary Python 3.14 run. Each runtime repeated the selected-profile fixture output byte-identically within that runtime. All three produced the same selected numeric-output matrix canonical hash. Runtime summaries and exact library versions are recorded in the structured evidence; runtime metadata/result-envelope hashes differ because versions and platform strings are intentionally part of those envelopes.

No real exchanger case, production solve, mesh refinement, external Q input, new physical authority, or production-code change was introduced. Full pytest was not run for this controlled numerical/evidence-only gate; exact-final-head GitHub CI is a separate required check.

~~~ini
NUMERICAL_ERROR_BUDGET_STOPPING_CANDIDATE_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
NUMERICAL_ERROR_BUDGET_AND_STOPPING_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=2
TASK172_ENTRY_AUTHORITY_COMPLETE=false
MESH_CONVERGENCE_QUALIFICATION=OPEN
MESH_STUDY_PERFORMED=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_QUANTITATIVE_NUMERICAL_PROFILE_INDEPENDENT_REVIEW_AND_BLOCKER_CLOSURE_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
~~~

## Validation receipts

The linked evidence JSON records source/profile replay, the fixture/oracle and residual-rule audits, all sensitivity sweeps, the two cross-runtime replays, artifact hashes and historical immutability. The complete numerical matrix is in `docs/tasks/evidence/TASK-172-quantitative-numerical-profile-coverage-results-r92a.json`; its deterministic test-only runner is adjacent. No production test suite or mesh study was executed in this gate.
