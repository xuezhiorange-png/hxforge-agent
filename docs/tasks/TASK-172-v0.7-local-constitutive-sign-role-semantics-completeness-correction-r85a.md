# TASK172 v0.7 — local constitutive sign-role semantics completeness correction R85A

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS_COMPLETENESS_CORRECTION_R85A
MODE=R85_SIGN_SEMANTICS_COMPLETENESS_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=26214787d2b521182d28c6f00ba7bd70efc32a89
HEAD_PRECONDITION_VERIFIED=true
RESULT=CORRECTED_SIGN_ROLE_SEMANTICS_COMPLETENESS
```

This append-only overlay completes the model-level signed-heat-rate semantics
that were left implicit by the R85 receipt. It does not modify R85, R84, the
residual equations, the orientation transform, the unknown set or the
residual set. It records the signed-domain meaning of `q_hc`, the zero and
negative model-level cases, and the rule that TASK171's stream roles are
explicit immutable identity inputs during a local evaluation.

This is documentation/evidence governance only. It does not select a negative-
heat disposition, implement a producer, call a property backend, execute J_mu,
solve a wall state, select a solver or tolerance, create a case, run a
numerical experiment, qualify a mesh, Ready the PR or Merge the PR.

## 1. Historical immutability and correction boundary

The predecessor is the completed R85 commit
`26214787d2b521182d28c6f00ba7bd70efc32a89`. R85 is a frozen review input:

```ini
R85_ORIGINAL_DOCUMENT_CHANGED=false
R85_ORIGINAL_EVIDENCE_CHANGED=false
R85_EXTENSION_REWRITTEN=false
R84_ARCHITECTURE_DIRECTION_VALID=true
R84_SIGN_ROLE_CONTRADICTION_FOUND=true
R84_SIGN_ROLE_CONTRADICTION_CORRECTED=true
```

The contradiction is historical semantic ambiguity, not a change to R84's
local-closure ownership. R84's direction—local states and admitted profiles
closing local wall heat transfer—remains valid. The corrected effective
overlay prevents the primary heat-rate unknown from being read as an
implicitly nonnegative magnitude or as an absolute-value quantity.

R1–R85 documents, evidence and registry extensions remain immutable. Only this
R85A document, its structured evidence and `r86_extension` are added.

## 2. Signed `q_hc` completeness contract

R85's `q_hc` primary unknown is explicitly a signed model-level unknown in the
HOT → COLD orientation:

```ini
Q_HC_IS_SIGNED_UNKNOWN=true
Q_HC_POSITIVE_MEANS_HOT_TO_COLD=true
Q_HC_ZERO_MEANING=ZERO_LOCAL_HEAT_TRANSFER
Q_HC_NEGATIVE_ALLOWED_AT_MODEL_LEVEL=true
Q_HC_NEGATIVE_MEANING=LOCAL_HEAT_FLOW_OPPOSITE_TO_ASSIGNED_HOT_TO_COLD_ORIENTATION
Q_HC_NEGATIVE_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
Q_HC_NONNEGATIVE_CLAMP_FORBIDDEN=true
```

The negative case is admitted at the equation-contract level so that the
model-level system does not silently clamp or reinterpret a signed solution.
This overlay deliberately does not decide whether a negative value is later
`VALID`, `WARN`, `BLOCKED`, `THERMAL_CROSS` or `ROLE_INCONSISTENCY`. That is a
separate applicability/failure-policy review. No negative threshold,
acceptance rule or numerical experiment is selected here.

The zero case means zero local heat transfer. It does not authorize a role
swap, a surface swap, a temperature-role inference or a special numerical
epsilon.

## 3. Explicit and stable HOT/COLD identity

The HOT/COLD assignment is an explicit TASK171 identity input for each admitted
physical support. It is not inferred from observed temperatures, equipment
side, array position or iteration history:

```ini
HOT_COLD_ROLE_IS_EXPLICIT_TASK171_IDENTITY=true
HOT_COLD_ROLE_INFERENCE_FROM_TEMPERATURE_MAGNITUDE=false
HOT_COLD_ROLE_INFERENCE_FROM_EQUIPMENT_SIDE=false
HOT_COLD_ROLE_INFERENCE_FROM_ARRAY_INDEX=false
HOT_COLD_ROLE_REASSIGNMENT_DURING_LOCAL_ITERATION=false
```

A local temperature crossover therefore does not silently mutate TUBE/SHELL or
HOT/COLD identity. Any future crossover disposition must be separately
reviewed; this overlay only preserves the input identity and prevents an
implicit role mutation.

The R85 orientation mapping remains unchanged:

```ini
S_TS_ALLOWED_VALUES=+1;-1
S_TS_IS_KNOWN_INPUT=true
S_TS_IS_UNKNOWN=false
Q_TS_RELATION=q_ts=s_ts*q_hc
TUBE_HOT_S_TS=+1
SHELL_HOT_S_TS=-1
```

`s_ts` is known from the explicit role identity and remains outside the unknown
set. It is not recomputed from a trial temperature or from the sign of `q_hc`.

## 4. R85 local equation and DOF preservation

R85's equation system is preserved exactly; no replacement equation is
introduced by R85A:

```ini
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_UNKNOWN_COUNT=3
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_EQUATION_COUNT=3
RESIDUAL_EQUATIONS_CHANGED=false
S_TS_RELATION_CHANGED=false
UNKNOWN_COUNT_CHANGED=false
RESIDUAL_COUNT_CHANGED=false
```

The effective residuals continue to consume the unchanged derived relation
`q_ts=s_ts*q_hc` and the unchanged R85 `r_i`, `r_w`, and `r_o` definitions.
Signed `q_hc` is therefore a domain clarification of the existing three
unknowns, not a fourth variable and not a residual rewrite.

The tube-hot and shell-hot structural audits remain valid for both signs of the
primary signed unknown. A negative value is not converted to `abs(q_hc)`, and
the role assignment is not changed during a trial or accepted local iterate.

## 5. Preserved J_mu and architecture boundaries

The shell-side J_mu ownership and R84 architecture remain unchanged:

```ini
JMU_SHELL_SIDE_INTERFACE_OWNERSHIP_PRESERVED=true
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
```

J_mu remains a shell-side interface/property relation and is not a sign factor
or a role-selection mechanism. External Q, whole-exchanger mean pressure and a
real case remain outside the native model-level local closure prerequisite.

## 6. Governance and stop boundary

The four-entry TASK172 blocker ledger is unchanged:

```text
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

No negative-`q_hc` applicability policy, solver policy, tolerance, pressure
rule, real state, property snapshot, Q receipt or downstream authority is
created by this correction.

## 7. Final receipt

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS_COMPLETENESS_CORRECTION_R85A
RESULT=CORRECTED_SIGN_ROLE_SEMANTICS_COMPLETENESS
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=26214787d2b521182d28c6f00ba7bd70efc32a89
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
R85_ORIGINAL_DOCUMENT_CHANGED=false
R85_ORIGINAL_EVIDENCE_CHANGED=false
R85_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
R84_ARCHITECTURE_DIRECTION_VALID=true
R84_SIGN_ROLE_CONTRADICTION_FOUND=true
R84_SIGN_ROLE_CONTRADICTION_CORRECTED=true
Q_HC_IS_SIGNED_UNKNOWN=true
Q_HC_POSITIVE_MEANS_HOT_TO_COLD=true
Q_HC_ZERO_MEANING=ZERO_LOCAL_HEAT_TRANSFER
Q_HC_NEGATIVE_ALLOWED_AT_MODEL_LEVEL=true
Q_HC_NEGATIVE_MEANING=LOCAL_HEAT_FLOW_OPPOSITE_TO_ASSIGNED_HOT_TO_COLD_ORIENTATION
Q_HC_NEGATIVE_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
Q_HC_NONNEGATIVE_CLAMP_FORBIDDEN=true
HOT_COLD_ROLE_IS_EXPLICIT_TASK171_IDENTITY=true
HOT_COLD_ROLE_INFERENCE_FROM_TEMPERATURE_MAGNITUDE=false
HOT_COLD_ROLE_INFERENCE_FROM_EQUIPMENT_SIDE=false
HOT_COLD_ROLE_INFERENCE_FROM_ARRAY_INDEX=false
HOT_COLD_ROLE_REASSIGNMENT_DURING_LOCAL_ITERATION=false
S_TS_ALLOWED_VALUES=+1;-1
Q_TS_RELATION=q_ts=s_ts*q_hc
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_UNKNOWN_COUNT=3
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_EQUATION_COUNT=3
RESIDUAL_EQUATIONS_CHANGED=false
UNKNOWN_COUNT_CHANGED=false
RESIDUAL_COUNT_CHANGED=false
JMU_SHELL_SIDE_INTERFACE_OWNERSHIP_PRESERVED=true
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
EXACT_FINAL_HEAD_CI_RUN=RECORDED_IN_FINAL_RECEIPT
EXACT_FINAL_HEAD_CI=RECORDED_IN_FINAL_RECEIPT
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
