# TASK172 v0.7 — local constitutive sign-role semantics correction R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS_CORRECTION_R1
MODE=MODEL_LEVEL_SIGN_ROLE_SEMANTICS_CORRECTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=2f66a000cf079b5d11c317466113cf2fff894766
HEAD_PRECONDITION_VERIFIED=true
RESULT=CORRECTED_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS
```

This append-only overlay corrects the effective sign and role semantics of the
R84 local constitutive system. R84 remains immutable and continues to supply
the local closure ownership, the three-primary-unknown/three-residual shape,
the local-pressure boundary, the external-Q dependency correction and the
preliminary-film initialization classification. This overlay adds the explicit
known tube-to-shell orientation required to make TASK171's positive heat-rate
meaning unambiguous in both tube-hot and shell-hot assignments.

This is documentation/evidence governance only. It does not implement a
producer, call a property backend, execute J_mu, solve a wall state, select a
numerical method or tolerance, create a case, run a numerical experiment,
qualify a mesh, Ready the PR or Merge the PR.

## 1. Immutable authority replay

The predecessor is the completed R84 commit
`2f66a000cf079b5d11c317466113cf2fff894766`. The R84 document, R84 evidence
and `r84_extension` are review inputs, not files to be repaired. R1–R84
documents, evidence and registry extensions remain historical payloads and are
not rewritten.

The sign-role correction is grounded in:

| Authority | Relevant binding |
| --- | --- |
| `docs/tasks/TASK-170-v0.7-scope-source-golden-freeze.md` | TASK172 owns local property/wall/convergence closure; TASK173 owns exchanger-level rating/sizing boundary closure. |
| `docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md` | Both tube-hot and shell-hot assignments are supported; positive signed wall heat rate means HOT → COLD. |
| `docs/tasks/TASK-172-v0.7-wall-temperature-state-authority-definition-r1.md` | TUBE/SHELL are independent from HOT/COLD; the signed tube-to-shell rate is positive for tube-hot and negative for shell-hot. |
| `docs/tasks/TASK-172-v0.7-shell-wall-correction-jmu-wall-producer-and-state-mapping-authority-r1.md` | The same signed rate is used through the inner-film, wall and outer-film branches; J_mu remains a shell-side wall-property factor. |
| R84 local constitutive overlay | The native local closure has three primary unknowns and three residuals, with no external-Q or whole-exchanger mean-pressure prerequisite. |

The existing wall-temperature authority already gives the correct physical
radial relation. R85 makes the orientation variables explicit in the local
constitutive contract instead of relying on the ambiguous name `q_local`.

## 2. Explicit heat-rate and role contract

For each admitted TASK171 physical support, the model binds a known stream-role
assignment before the local residual system is admitted:

```ini
TASK171_POSITIVE_Q_SEMANTICS=HOT_TO_COLD
TUBE_HOT_AND_SHELL_HOT_SUPPORTED=true
Q_HC_PRIMARY_UNKNOWN=true
Q_HC_SIGN=HOT_TO_COLD_ORIENTATION
Q_HC_POSITIVE_MEANS_HOT_TO_COLD=true
S_TS_ORIENTATION_BOUND=true
S_TS_IS_KNOWN_INPUT=true
S_TS_IS_UNKNOWN=false
S_TS_ALLOWED_VALUES=+1;-1
Q_TS_IS_DERIVED=true
Q_TS_RELATION=q_ts=s_ts*q_hc
```

`q_hc` is the primary local heat-rate unknown in the HOT → COLD orientation.
It is not an absolute-value replacement for a signed heat event. `s_ts` is a
known orientation derived from the admitted HOT/COLD role assignment and the
fixed TUBE/SHELL identity:

```text
s_ts = +1  when TUBE is HOT and SHELL is COLD
s_ts = -1  when SHELL is HOT and TUBE is COLD
q_ts = s_ts * q_hc
```

`q_ts` is the signed tube-to-shell rate consumed by the radial branch
equations. It is derived from the primary unknown and known orientation; it is
not a fourth unknown. Equipment-side identity must not be inferred from list
position, an array index, a presumed flow direction or a hard-coded tube-hot
branch. An absent or invalid role/orientation binding fails closed.

The effective role guards are:

```ini
REJECT_IF_ORIENTATION_MISSING=true
REJECT_IF_ORIENTATION_INVALID=true
REJECT_IF_HOT_COLD_ROLE_UNBOUND=true
REJECT_IF_EQUIPMENT_SIDE_USED_AS_HOT_COLD_AUTHORITY=true
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
TUBE_HOT_S_TS=+1
SHELL_HOT_S_TS=-1
```

These guards do not select a physical heat-transfer direction for a case. They
require the upstream state/topology authority to provide the role assignment
that the local constitutive evaluation consumes.

## 3. Corrected local residual system

The native local mode remains the R84 system for one admissible physical
support. The primary unknown coordinate is now explicit:

```ini
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_ACTUAL_UNKNOWN_SET_BOUND=true
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_ACTUAL_RESIDUAL_SET_BOUND=true
L2B_EQUATION_COUNT=3
L2B_EQUATION_COUNT_BOUND=true
L2B_UNKNOWN_COUNT=3
L2B_UNKNOWN_COUNT_BOUND=true
L2B_DEGREES_OF_FREEDOM_STATUS=CLOSED_MODEL_LEVEL_THREE_PRIMARY_UNKNOWNS_THREE_PRIMARY_RESIDUALS
```

With `q_ts=s_ts*q_hc`, the same signed tube-to-shell rate is used at all
three branches:

```text
r_i = q_ts
      - h_i(T_wall_inner, located tube state, admitted tube profile)
        * A_i * (T_tube_bulk - T_wall_inner)

r_w = q_ts
      - (T_wall_inner - T_wall_outer) / R_wall

r_o = q_ts
      - h_o(T_wall_outer, located shell state, admitted shell profile)
        * A_o * (T_wall_outer - T_shell_bulk)
```

Equivalently, each residual contains `s_ts*q_hc`; no residual uses an
unoriented absolute heat rate. The equations preserve the TASK171 signed
heat-event semantics and the clean radial wall network:

```text
T_tube_bulk - T_shell_bulk = q_ts * R_sum
T_tube_inner_wall = T_tube_bulk - q_ts * R_i
T_tube_outer_wall = T_tube_inner_wall - q_ts * R_w
                   = T_shell_bulk + q_ts * R_o
```

For the tube-hot assignment, `s_ts=+1`, so `q_ts=q_hc` and the rate is
tube-to-shell. For the shell-hot assignment, `s_ts=-1`, so `q_ts=-q_hc`
and the same residual family represents shell-to-tube transfer. The radial
surface identities remain TUBE/SHELL identities; they are not swapped when the
hot stream changes. No tube side is hard-coded as hot and no shell side is
hard-coded as cold.

This is a sign-coordinate correction, not a numerical experiment or a claim
that the system has an admitted solver. The method boundary remains:

```ini
SCALAR_REDUCTION_BOUND=false
VECTOR_METHOD_REVIEW_REQUIRED=true
L2B_METHOD_STATUS=METHOD_UNBOUND
SOLVER_SELECTED=false
TOLERANCES_SELECTED=false
MAX_ITER_SELECTED=false
RELAXATION_FACTOR_SELECTED=false
```

## 4. Orientation audit without execution

The following structural audit is algebraic and does not instantiate a case:

| Assignment | `s_ts` | Derived rate | Radial meaning |
| --- | ---: | --- | --- |
| tube hot / shell cold | `+1` | `q_ts=q_hc` | positive tube-to-shell heat rate |
| shell hot / tube cold | `-1` | `q_ts=-q_hc` | negative tube-to-shell rate, equivalently shell-to-tube |

Both rows use the same `r_i`, `r_w`, and `r_o` definitions. Reversing the role
assignment changes the explicit sign transform and the temperature-difference
orientation; it does not change the unknown count, residual count, area basis,
surface identity or J_mu ownership.

## 5. J_mu ownership is preserved

R85 does not promote or redefine the unresolved J_mu physical authority. It
preserves the R84 classification:

```ini
JMU_RUNTIME_GRANULARITY=SEGMENT_LOCAL_CONSTITUTIVE_EVALUATION_STATE
JMU_SHELL_SIDE_INTERFACE_OWNERSHIP_PRESERVED=true
MU_BULK_SOURCE=LOCATED_LOCAL_SHELL_BULK_PROPERTY_STATE
MU_WALL_SOURCE=LOCATED_LOCAL_SHELL_FLUID_WALL_INTERFACE_PROPERTY_STATE
JMU_SIGN_ORIENTATION_FACTOR=false
JMU_PHYSICAL_TRANSFER_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

J_mu belongs in the shell-side correlation/film branch through the admitted
shell wall-property relation. It is not a sign factor, it is not a substitute
for `s_ts`, and it is not applied by changing the sign of `q_hc` or `q_ts`.
The physical relation remains observed but not promoted:
`J_mu=(mu_bulk/mu_wall)^m`. Exponent, applicability, fluid/property domain,
wall-interface mapping, shell-film authority and execution remain separate
physical authority gaps.

## 6. R84 architecture preserved

The sign correction does not reopen the dependency classifications recorded by
R84:

```ini
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
LOCAL_CONSTITUTIVE_Q_IS_UNKNOWN_OR_DERIVED_OUTPUT=true
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
REAL_CASE_REQUIRED_FOR_PRODUCTION_REPLAY_OR_VALIDATION=true
REAL_CASE_REQUIRED_FOR_TASK175_GOLDEN_RELEASE=true
WHOLE_EXCHANGER_SOURCE_MEAN_PATH_SELECTED_FOR_TASK172_RUNTIME=false
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_RUNTIME=false
TASK172_GENERATES_HYDRAULIC_PRESSURE_FIELD=false
PRELIMINARY_SHELL_FILM_ROLE=NUMERICAL_INITIALIZATION_STATE_ONLY
JMU_NEUTRAL_INITIALIZATION_ALLOWED=true
JMU_NEUTRAL_INITIALIZATION_EXECUTION_AUTHORIZED=false
JMU_EQUALS_ONE_IS_PHYSICAL_PRODUCTION_CORRECTION=false
FINAL_ACTIVE_JMU_REQUIRED=true
```

The external-Q contract remains valid for an explicitly authorized external-Q
input/validation mode, but no external Q is required by this native local
constitutive unknown set. A whole-exchanger source-mean pressure is not
required for a segment-local property evaluation; TASK172 consumes an
admissible located local pressure state and does not create a hydraulic field.

## 7. Preserved authority gaps and blocker ledger

R85 does not close the shell-wall authority, numerical, error-budget or mesh
gates. The four-entry TASK172 ledger remains:

```text
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
MESH_CONVERGENCE_QUALIFICATION=OPEN
JMU_BULK_PRESSURE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
QUALIFIED_Q_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
```

The R84 physical gaps remain, including J_mu equation transfer, exponent and
applicability transfer, fluid/property domain transfer, wall-interface state
mapping, k_wall authority and base shell-film authority. No pressure rule is
selected by this overlay.

## 8. Governance and stop boundary

Only the new R85 document, its structured evidence and `r85_extension` are
added. The following remain false:

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
REAL_TASK172_CASE_CREATED=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
JMU_EXECUTED=false
WALL_STATE_SOLVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

## 9. Final receipt

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS_CORRECTION_R1
RESULT=CORRECTED_LOCAL_CONSTITUTIVE_SIGN_ROLE_SEMANTICS
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=2f66a000cf079b5d11c317466113cf2fff894766
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
R84_ARCHITECTURE_PRESERVED=true
R84_ORIGINAL_DOCUMENT_CHANGED=false
R84_ORIGINAL_EVIDENCE_CHANGED=false
R84_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
TASK171_POSITIVE_Q_SEMANTICS=HOT_TO_COLD
TUBE_HOT_AND_SHELL_HOT_SUPPORTED=true
S_TS_ORIENTATION_BOUND=true
S_TS_ALLOWED_VALUES=+1;-1
S_TS_IS_KNOWN_INPUT=true
Q_HC_PRIMARY_UNKNOWN=true
Q_TS_RELATION=q_ts=s_ts*q_hc
TUBE_HOT_S_TS=+1
SHELL_HOT_S_TS=-1
L2B_ACTUAL_UNKNOWN_SET_BOUND=true
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_ACTUAL_RESIDUAL_SET_BOUND=true
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_EQUATION_COUNT=3
L2B_UNKNOWN_COUNT=3
L2B_DEGREES_OF_FREEDOM_STATUS=CLOSED_MODEL_LEVEL_THREE_PRIMARY_UNKNOWNS_THREE_PRIMARY_RESIDUALS
TUBE_HOT_RESIDUAL_ORIENTATION_CONSISTENT=true
SHELL_HOT_RESIDUAL_ORIENTATION_CONSISTENT=true
JMU_SHELL_SIDE_INTERFACE_OWNERSHIP_PRESERVED=true
JMU_PHYSICAL_TRANSFER_BOUND=false
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_RUNTIME=false
PRELIMINARY_SHELL_FILM_ROLE=NUMERICAL_INITIALIZATION_STATE_ONLY
JMU_NEUTRAL_INITIALIZATION_ALLOWED=true
JMU_NEUTRAL_INITIALIZATION_EXECUTION_AUTHORIZED=false
FINAL_ACTIVE_JMU_REQUIRED=true
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
EXACT_FINAL_HEAD_CI_RUN=RECORDED_IN_FINAL_RECEIPT
EXACT_FINAL_HEAD_CI=RECORDED_IN_FINAL_RECEIPT
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
