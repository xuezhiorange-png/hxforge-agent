# TASK172 v0.7 — local constitutive closure architecture correction R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_CLOSURE_ARCHITECTURE_CORRECTION_R1
MODE=MODEL_LEVEL_LOCAL_CONSTITUTIVE_ARCHITECTURE_CORRECTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=70dbbe1f0883b88aee415d8e48526201d40ff903
HEAD_PRECONDITION_VERIFIED=true
RESULT=CORRECTED_LOCAL_CONSTITUTIVE_ARCHITECTURE
```

This append-only overlay corrects the effective dependency classification for
native TASK172 segmented local constitutive closure. It does not rewrite the
R1–R83 documents, evidence, or registry extensions. It does not acquire a new
source, create a case, execute a property backend, solve a wall state, choose a
numerical method, or qualify a production result.

## 1. Ownership replay

The frozen TASK170 responsibility table is decisive for the layer boundary:

| Owner | Effective responsibility used by this correction |
| --- | --- |
| TASK171 | Physical/fluid-path topology, local state vocabulary, cell/compartment mapping, conservation bookkeeping and shared state/pressure interfaces. |
| TASK172 | Local property evaluation, wall/interface constitutive closure, approved wall-viscosity correction, local iteration/failure semantics and numerical-profile binding. |
| TASK174 | Detailed hydraulic pressure evolution, local-loss decomposition, shell hydraulic aggregation and operability/FIV screening. |
| TASK173 | Full exchanger rating/sizing boundary solve, outlet closure, constraints, ranking and recommendation. |
| TASK175 | Integration, approved Golden/release acceptance and replay. |

The replay is supported by `docs/tasks/TASK-170-v0.7-scope-source-golden-freeze.md`
§9–§12 and §22, and by
`docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md`
§Authority and scope, §Structural invariants, §Conservation and identity, and
§Verification and deferred work. TASK173 remains the exchanger-level boundary
owner. TASK172 must not become a full rating/sizing or detailed hydraulic
solver.

## 2. Corrected native TASK172 dependency direction

For one admissible TASK171 physical interval/support, the native local mode is
defined as a constitutive closure over located local states and admitted
profiles:

```text
located tube bulk state (T_b,t, P_b,t)
located shell bulk state (T_b,s, P_b,s)
mass-flow / hydraulic inputs required by the selected correlations
geometry, local areas, wall/fouling/material profiles and property authority
                              |
                              v
                 local properties and base h_i / h_o
                              |
                              v
             q_local, T_wall_inner, T_wall_outer
                              |
                              v
             wall-property / J_mu coupling and residuals
                              |
                              v
              local HTC, U, UA, duty and status output
```

The primary model-level unknowns are:

```ini
L2B_ACTUAL_UNKNOWN_SET=q_local;T_wall_inner;T_wall_outer
L2B_ACTUAL_UNKNOWN_SET_BOUND=true
L2B_EQUATION_COUNT=3
L2B_UNKNOWN_COUNT=3
L2B_UNKNOWN_COUNT_BOUND=true
L2B_DEGREES_OF_FREEDOM_STATUS=CLOSED_MODEL_LEVEL_THREE_PRIMARY_UNKNOWNS_THREE_PRIMARY_RESIDUALS
```

`T_wall_outer` is not an anonymous metal temperature. In the minimal three-
unknown network it denotes the explicitly identified shell-fluid heat-transfer
surface state consumed by the wall-property evaluation. If the selected source
requires a distinct metal outer surface and fluid-side interface state, that
interface becomes an explicit additional node and residual; it may not be
silently aliased.

The residual family is bound structurally, with TASK171's signed heat-event
orientation and with no hot/cold role assumption:

```text
r_i = q_local - h_i(T_wall_inner, local tube state, admitted tube profile)
             * A_i * (T_tube_bulk - T_wall_inner)

r_w = q_local - (T_wall_inner - T_wall_outer) / R_wall

r_o = q_local - h_o(T_wall_outer, local shell state, admitted shell profile)
             * A_o * (T_wall_outer - T_shell_bulk)
```

The sign of `q_local` is inherited from TASK171: positive means heat transfer
from the hot stream to the cold stream. If a future correlation uses an
opposite local orientation, the producer must bind the explicit sign mapping;
the architecture does not hard-code tube-hot or shell-cold.

```ini
L2B_ACTUAL_RESIDUAL_SET=r_i; r_w; r_o
L2B_ACTUAL_RESIDUAL_SET_BOUND=true
L2B_RESIDUAL_SET_BOUND=true
SCALAR_REDUCTION_BOUND=false
VECTOR_METHOD_REVIEW_REQUIRED=true
L2B_METHOD_STATUS=METHOD_UNBOUND
```

This is a model-level equation/unknown contract only. It does not select a
solver, bracket, tolerance, relaxation factor, iteration cap, or stopping
value. The numerical-profile prerequisites remain open.

## 3. External Q dependency correction

The historical external-Q contract remains valid for a mode in which an
external signed heat-rate receipt is intentionally supplied and independently
reviewed. It is not a prerequisite for the native local constitutive mode.

```ini
HISTORICAL_EXTERNAL_Q_CONTRACT_REMAINS_VALID_FOR_EXTERNAL_Q_INPUT_MODE=true
EXTERNAL_Q_CONTRACT_IS_NOT_REQUIRED_FOR_NATIVE_LOCAL_CONSTITUTIVE_MODE=true
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
LOCAL_CONSTITUTIVE_Q_IS_UNKNOWN_OR_DERIVED_OUTPUT=true
LOCAL_Q_IS_CONSTITUTIVE_UNKNOWN_OR_OUTPUT=true
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
QUALIFIED_Q_AUTHORITY_BOUND=false
```

The external-Q contract's support, sign, units, dependency and lifecycle
requirements are not deleted. A future external-Q input mode must still obey
them, and an external Q may be used as validation/reference evidence when its
scope is independently bound. A whole-exchanger Q cannot be silently divided
into local duties or used as a local wall-interface Q.

This correction removes only the erroneous implication that the absence of an
external Q receipt prevents definition of the native local closure. It does
not create a Q producer or an external Q instance.

## 4. Real-case layer correction

R83's inventory finding remains historically valid: no qualified real TASK172
case was found in the repository. That is a production replay and validation
finding, not a prerequisite for defining the model-level local closure.

```ini
R83_NO_QUALIFIED_REAL_CASE_FINDING_REMAINS=true
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
REAL_CASE_REQUIRED_FOR_PRODUCTION_REPLAY_OR_VALIDATION=true
REAL_CASE_REQUIRED_FOR_TASK175_GOLDEN_RELEASE=true
REAL_TASK172_CASE_FOUND=false
REAL_TASK172_CASE_CREATED=false
REAL_TASK172_CASE_BINDABLE=false
```

Fixtures, examples, release-demo values, legacy fragments and synthetic test
cases remain non-Golden and cannot be promoted into a case authority. Their
absence does not block a mathematical closure definition, deterministic
synthetic tests, equation/oracle tests, or property reproduction tests, subject
to the independent authority gates for those artifacts.

## 5. Local versus whole-exchanger J_mu state

The acquired/recorded source evidence supports the symbolic physical form
`J_mu=(mu_bulk/mu_wall)^m` and its separate placement in the Bell/Jamil
representation. It does not, by itself, complete TASK172 transfer authority
for exponent, domain, geometry, wall-surface identity or execution.

The effective runtime granularity is corrected as follows:

```ini
JMU_RUNTIME_GRANULARITY=SEGMENT_LOCAL_CONSTITUTIVE_EVALUATION_STATE
LOCAL_PROPERTY_PRESSURE_IS_STATE_INPUT=true
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
TASK172_GENERATES_HYDRAULIC_PRESSURE_FIELD=false
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_PROPERTY_EVALUATION=false
WHOLE_EXCHANGER_SOURCE_MEAN_PATH_SELECTED_FOR_TASK172_RUNTIME=false
R71_R82_SOURCE_MEAN_RESEARCH_HISTORICALLY_VALID=true
R71_R82_SOURCE_MEAN_PATH_SELECTED_FOR_TASK172_RUNTIME=false
JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING_IS_NOT_TASK172_LOCAL_MODEL_BLOCKER=true
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
```

The local pressure value is an input from the located TASK171/TASK173/TASK174
integration interface. TASK172 does not invent `(P_in+P_out)/2`, inlet pressure,
outlet pressure, a representative pressure, or a detailed pressure field. A
whole-exchanger source-mean projection, if later required for reporting, is a
separate optional aggregation and cannot replace the local runtime state.

## 6. Preliminary shell film role

Existing source evidence says that a preliminary heat-transfer calculation is
needed to obtain a wall temperature, but it does not select a permanent
preliminary shell-film correlation or correction set. Therefore the previous
physical-source gap remains a physical-authority gap, while its role in the
native dependency graph is corrected:

```ini
PRELIMINARY_SHELL_FILM_ROLE=NUMERICAL_INITIALIZATION_STATE_ONLY
PRELIMINARY_SHELL_FILM_IS_NOT_PERMANENT_PHYSICAL_INPUT=true
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
JMU_NEUTRAL_INITIALIZATION_ALLOWED=true
JMU_NEUTRAL_INITIALIZATION_SCOPE=INITIALIZATION_CANDIDATE_ONLY
JMU_NEUTRAL_INITIALIZATION_EXECUTION_AUTHORIZED=false
JMU_EQUALS_ONE_IS_PHYSICAL_PRODUCTION_CORRECTION=false
JMU_EQUALS_ONE_IS_ALLOWED_ONLY_AS_INITIALIZATION_CANDIDATE=true
FINAL_ACTIVE_JMU_REQUIRED=true
```

The candidate initialization is: start with `J_mu^(0)=1`, evaluate the base
shell film using only separately admitted non-J_mu factors, construct a
diagnostic initial wall state, evaluate the wall property, and then activate
the reviewed J_mu relation for subsequent accepted iterates. This is not an
authorized implementation or numerical profile. A future numerical gate must
bind update order, failure semantics, domain safety and convergence criteria;
the final result cannot use the neutral factor as its production correction.

## 7. Coupled closure and remaining physical authority

The corrected dependency graph is:

```text
located local bulk states
        -> base properties / base HTC
        -> initialization wall estimate
        -> wall properties
        -> tube/shell wall corrections
        -> corrected h_i / h_o
        -> q_local + T_wall_inner + T_wall_outer
        -> updated wall properties
        -> repeat until a later reviewed stopping policy admits closure
```

The following authority gaps remain and are not silently promoted:

```ini
JMU_PHYSICAL_AUTHORITY_GAPS_REMAINING=JMU_EQUATION_TRANSFER;JMU_EXPONENT_AND_APPLICABILITY_TRANSFER;JMU_FLUID_AND_PROPERTY_DOMAIN_TRANSFER;WALL_INTERFACE_STATE_MAPPING;K_WALL_AUTHORITY;BASE_SHELL_FILM_AUTHORITY
```

In particular, the source observation of `m usually 0.14` is not a TASK172
numeric selection, and the source-symbolic equation is not a reviewed
production transfer. The wall, property, film and pressure-state producers
must still bind exact identities, domains, lifecycle and provenance.

## 8. Recomputed entry blockers

The blocker ledger was recomputed from ownership and authority requirements,
not copied from the R83 real-case inventory. The count remains four, but the
reasoning is now explicit:

| Blocker | Effective classification | Current reason |
| --- | --- | --- |
| `SHELL-WALL-CORRECTION-AUTHORITY` | Model/design entry blocker | J_mu transfer/domain, wall-interface mapping, k_wall and shell-film authority remain incomplete. It is not blocked by external Q or by absence of a real case. |
| `LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION` | Model/design and execution-admission blocker | The unknown/residual structure is now bound, but scalar reduction, vector method, domain/trial policy, tolerances and stopping remain unbound. |
| `NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW` | Execution-admission blocker | Quantitative allocation and executable stopping policy remain unbound. |
| `MESH-CONVERGENCE-QUALIFICATION` | Production-validation/release blocker | Actual refinement sequence, metric, threshold, mapping and estimator remain unbound. |

```ini
TASK172_ENTRY_BLOCKERS_RECOMPUTED=true
REAL_CASE_AND_EXTERNAL_Q_NOT_NATIVE_MODEL_BLOCKERS=true
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The four blockers remain:

```text
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

Other ownership boundaries remain frozen:

```ini
TASK173_BOUNDARY_PRESERVED=true
TASK174_BOUNDARY_PRESERVED=true
TASK175_BOUNDARY_PRESERVED=true
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
MESH_CONVERGENCE_QUALIFICATION=OPEN
```

## 9. Preserved historical and governance state

R1–R83 are immutable. R78–R82 source research remains historical evidence;
R83 remains the repository real-case inventory. This overlay does not rewrite
their pressure, source-mean, external-Q or real-case conclusions. It changes
only the effective dependency classification for the native segmented local
closure mode.

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
REAL_L3_DIRECT_LOCAL_STATE_INSTANCE_PRESENT=false
REAL_L3_RECONSTRUCTED_LOCAL_STATE_INSTANCE_PRESENT=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

`TASK172_MODEL_LEVEL_GAPS_REMAINING` are the unbound physical transfer,
material/film/interface, numerical-method and quantitative qualification
authorities listed above. `TASK172_RELEASE_VALIDATION_GAPS` remain
case-bound replay/validation evidence, approved Golden/release fixtures,
mesh evidence and TASK173 integration; these are not substituted by fixtures
or by the architecture overlay.

## 10. Final receipt

```ini
TASK_ID=TASK172_V0_7_LOCAL_CONSTITUTIVE_CLOSURE_ARCHITECTURE_CORRECTION_R1
RESULT=CORRECTED_LOCAL_CONSTITUTIVE_ARCHITECTURE
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=70dbbe1f0883b88aee415d8e48526201d40ff903
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
TASK170_TASK172_OWNER_REPLAY=PASS
TASK173_BOUNDARY_PRESERVED=true
REAL_CASE_REQUIRED_FOR_MODEL_LEVEL_TASK172_CLOSURE=false
REAL_CASE_REQUIRED_FOR_RELEASE_VALIDATION=true
EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false
LOCAL_Q_IS_CONSTITUTIVE_UNKNOWN_OR_OUTPUT=true
JMU_RUNTIME_GRANULARITY=SEGMENT_LOCAL_CONSTITUTIVE_EVALUATION_STATE
WHOLE_EXCHANGER_SOURCE_MEAN_PATH_SELECTED=false
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_RUNTIME=false
PRELIMINARY_SHELL_FILM_ROLE=NUMERICAL_INITIALIZATION_STATE_ONLY
JMU_NEUTRAL_INITIALIZATION_ALLOWED=true
FINAL_ACTIVE_JMU_REQUIRED=true
L2B_ACTUAL_UNKNOWN_SET_BOUND=true
L2B_ACTUAL_UNKNOWN_SET=q_local;T_wall_inner;T_wall_outer
L2B_ACTUAL_RESIDUAL_SET_BOUND=true
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_DEGREES_OF_FREEDOM_STATUS=CLOSED_MODEL_LEVEL_THREE_UNKNOWN_THREE_RESIDUAL_EXECUTABLE_METHOD_UNBOUND
JMU_PHYSICAL_AUTHORITY_GAPS_REMAINING=JMU_EQUATION_TRANSFER;JMU_EXPONENT_AND_APPLICABILITY_TRANSFER;JMU_FLUID_AND_PROPERTY_DOMAIN_TRANSFER;WALL_INTERFACE_STATE_MAPPING;K_WALL_AUTHORITY;BASE_SHELL_FILM_AUTHORITY
TASK172_MODEL_LEVEL_GAPS_REMAINING=JMU_PHYSICAL_TRANSFER;WALL_INTERFACE_AND_K_WALL;BASE_SHELL_FILM;LOCAL_RESIDUAL_METHOD;QUANTITATIVE_NUMERICAL_ALLOCATION;MESH_QUALIFICATION
TASK172_RELEASE_VALIDATION_GAPS=REAL_CASE_REPLAY;APPROVED_GOLDEN_RELEASE_FIXTURES;MESH_EVIDENCE;TASK173_INTEGRATION
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
