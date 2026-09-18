# TASK172 v0.7 — L3 Local-State Reconstruction Contract R2

This package constructs the model-level admission and identity contract for a
future TASK172 L3 constitutive fluid state.  It deliberately separates the
identity contract from a reconstruction operator, a real state instance, and
an executable numerical method.  The repository audit found no independently
reviewed face-to-cell reconstruction law in the accepted TASK171/TASK172
authority set, so no operator is selected or promoted here.

## Receipt identity and scope

```ini
TASK_ID=TASK172_V0_7_L3_LOCAL_STATE_RECONSTRUCTION_CONTRACT_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=10aeabf2a2ce0da2bc4693454d8dc74abc77934f
MODE=MODEL_LEVEL_L3_LOCAL_STATE_IDENTITY_AND_RECONSTRUCTION_ADMISSION_CONTRACT_ONLY
WALL_TEMPERATURE_STATE_AUTHORITY_ID=V07-T172-WALL-TEMPERATURE-STATE-R1
WALL_TEMPERATURE_STATE_AUTHORITY_STATUS=REVIEWED_MODEL_LEVEL_STATE_DEFINITION
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This gate does not choose an arithmetic face mean, an enthalpy mean, an
interpolation, an enthalpy inversion, a property backend call, a constitutive
solve, a tolerance, an error budget, or a mesh rule.

## TASK171 boundary and state vocabulary

The accepted TASK171 structural authority provides explicit locations for
`UPSTREAM_FACE`, `DOWNSTREAM_FACE`, `CELL_MEAN`, `COMPARTMENT_MIXED`, and wall
surfaces.  It binds faces, cells, intervals, paths, stream/side identity and
wall interfaces, but its state producer slots remain unresolved.  In
particular, the `CELL_MEAN` tag is a location/schema tag, not a reconstruction
law; `COMPARTMENT_MIXED` is not a mixing authority.

```ini
TASK171_LOCAL_STATE_STRUCTURAL_VOCABULARY_BOUND=true
TASK171_LOCAL_STATE_LOCATIONS=UPSTREAM_FACE;DOWNSTREAM_FACE;CELL_MEAN;COMPARTMENT_MIXED;WALL_INNER_SURFACE;WALL_OUTER_SURFACE
TASK171_LOCAL_THERMODYNAMIC_STATE_PRODUCER_BOUND=false
TASK171_CELL_MEAN_SCHEMA_IMPLIES_RECONSTRUCTION_RULE=false
TASK171_NO_AVERAGING_INFERRED=true
TASK171_NO_INTERPOLATION_INFERRED=true
TASK171_NO_CONSTITUTIVE_MIXING_INFERRED=true
```

The reviewed topology implementation validates structural face/cell ownership
and direction, but does not produce thermodynamic values or promote a producer
slot.  TASK172 therefore retains ownership of local property, wall, cell-mean,
reconstruction, and constitutive closure authority.

## L3 semantic roles

The contract distinguishes the two face roles from the state consumed by a
constitutive evaluation.  A constitutive state may be directly supplied by a
qualified producer or may later be produced by an independently reviewed
operator.  It is not assumed to be the `CELL_MEAN` location.

```ini
L3_UPSTREAM_FACE_STATE_ROLE_BOUND=true
L3_DOWNSTREAM_FACE_STATE_ROLE_BOUND=true
L3_CONSTITUTIVE_EVALUATION_STATE_ROLE_BOUND=true
L3_CONSTITUTIVE_EVALUATION_STATE_LOCATION=CONSTITUTIVE_EVALUATION_STATE;EXACT_LOCATION_AND_PRODUCER_REQUIRED;NOT_ASSUMED_CELL_MEAN
L3_TUBE_LOCAL_STATE_CONTRACT_BOUND=true
L3_SHELL_LOCAL_STATE_CONTRACT_BOUND=true
TUBE_SHELL_STATE_SUBSTITUTION_AUTHORIZED=false
HOT_COLD_ROLE_SUBSTITUTION_FOR_TUBE_SHELL_AUTHORIZED=false
```

`TUBE_SIDE_LOCAL_STATE` and `SHELL_SIDE_LOCAL_STATE` are separate contracts.
Hot/cold thermal role is not a replacement for tube/shell equipment-side
identity.

## Local-state identity contract

A future constitutive evaluation state must carry immutable identity and
provenance for the exact case, topology, path, stream, side, physical interval,
support, and numerical cell.  The temperature and pressure are state values;
they are not sufficient identity by themselves.

```ini
L3_LOCAL_STATE_IDENTITY_CONTRACT_BOUND=true
L3_LOCAL_STATE_REQUIRED_FIELDS=LOCAL_STATE_ID;LOCAL_STATE_HASH;TASK172_CASE_ID;TASK172_CASE_HASH;TASK171_TOPOLOGY_ID;TASK171_TOPOLOGY_HASH;FLOW_PATH_ID;STREAM_ID;EQUIPMENT_SIDE;PHYSICAL_INTERVAL_ID;PHYSICAL_SUPPORT_ID;NUMERICAL_CELL_ID;STATE_LOCATION;PHYSICAL_COORDINATE_INTERVAL;FLOW_PATH_COORDINATE_INTERVAL;TEMPERATURE_K;PRESSURE_PA;PROPERTY_AUTHORITY_ID;PROPERTY_AUTHORITY_VERSION;PROPERTY_SNAPSHOT_ID;PROPERTY_SNAPSHOT_HASH;STATE_PRODUCER_AUTHORITY_ID;STATE_PRODUCER_LIFECYCLE_STATUS;PROVENANCE_REFS;CANONICAL_HASH
L3_LOCAL_STATE_ACTUAL_VALUES_CREATED=false
```

The state identity is structural and provenance-bound.  Equal numerical
temperature or pressure, equal array position, or equal timestamp cannot
substitute for the required identity tuple.

## Face-state and support mapping contract

Upstream and downstream face states are independently identified.  A future
local constitutive state may consume them only when their structural binding
is exact:

```ini
L3_FACE_STATE_IDENTITY_CONTRACT_BOUND=true
L3_FACE_STATE_REQUIRED_FIELDS=FACE_STATE_ID;FACE_STATE_HASH;FACE_ID;STATE_LOCATION;FLOW_PATH_ID;STREAM_ID;SIDE;CASE_ID;CASE_HASH;TOPOLOGY_ID;TOPOLOGY_HASH;TEMPERATURE;PRESSURE;PROPERTY_AUTHORITY;PROPERTY_SNAPSHOT;PRODUCER_AUTHORITY;PROVENANCE
L3_FACE_TO_CELL_SAME_CASE_REQUIRED=true
L3_FACE_TO_CELL_SAME_STREAM_REQUIRED=true
L3_FACE_TO_CELL_SAME_TOPOLOGY_REQUIRED=true
L3_FACE_TO_CELL_SAME_PHYSICAL_INTERVAL_REQUIRED=true
L3_FACE_TO_LOCAL_SUPPORT_MAPPING_CONTRACT_BOUND=true
L3_ARRAY_INDEX_PAIRING_AUTHORIZED=false
L3_UNSUPPORTED_INTERPOLATION_AUTHORIZED=false
```

The local state, face states, wall state, and constitutive support must bind
the same case, topology, physical interval, and physical support.  A separate
common physical intersection map is required if stream meshes differ; no such
map is created by this receipt.

## Producer classes and operator boundary

The model-level contract supports two future producer classes:

1. `DIRECT_LOCAL_STATE_PRODUCER`, which supplies the exact local state without
   reconstruction and must itself be independently reviewed and lifecycle
   bound.
2. `RECONSTRUCTED_LOCAL_STATE_PRODUCER`, which requires a reviewed
   reconstruction-operator authority before it can produce a state.

```ini
L3_DIRECT_LOCAL_STATE_PRODUCER_CLASS_SUPPORTED=true
L3_RECONSTRUCTED_LOCAL_STATE_PRODUCER_CLASS_SUPPORTED=true
L3_RECONSTRUCTION_OPERATOR_AUTHORITY_REQUIRED=true
REAL_L3_DIRECT_LOCAL_STATE_INSTANCE_PRESENT=false
REAL_L3_RECONSTRUCTED_LOCAL_STATE_INSTANCE_PRESENT=false
```

The repository audit covered the accepted TASK171 topology definition and
implementation, TASK170 entry authority, the reviewed wall-state definition,
the numerical framework, and the local residual qualification.  These sources
define state locations and structural bindings, but none supplies a reviewed
face-to-cell temperature, pressure, enthalpy, density, property, caloric-mean,
midpoint, mass-weighted, or enthalpy-equivalent reconstruction operator.

```ini
L3_EXISTING_RECONSTRUCTION_OPERATOR_AUTHORITY_FOUND=false
L3_RECONSTRUCTION_OPERATOR_AUTHORITY_ID=NONE
L3_RECONSTRUCTION_OPERATOR_LIFECYCLE=NONE
L3_RECONSTRUCTION_OPERATOR_RULE=NONE
L3_RECONSTRUCTION_OPERATOR_DOMAIN=NONE
L3_STATE_RECONSTRUCTION_OPERATOR_BOUND=false
```

Consequently, the following convenience operators remain explicitly
unauthorized:

```ini
L3_ARITHMETIC_FACE_TEMPERATURE_MEAN_AUTHORIZED=false
L3_ARITHMETIC_FACE_PRESSURE_MEAN_AUTHORIZED=false
L3_PROPERTY_VALUE_AVERAGING_AUTHORIZED=false
L3_ENTHALPY_TO_TEMPERATURE_INVERSION_AUTHORIZED=false
```

## Enthalpy bookkeeping is not a constitutive-state producer

The TASK171 face enthalpy observation and hot/cold bookkeeping identities are
preserved as observations and conservation semantics.  They do not define a
constitutive evaluation state, a cell mean, or a property snapshot.

```ini
TASK171_BOOKKEEPING_RESIDUAL_IDENTITY_PRESERVED=true
TASK171_ZERO_BOOKKEEPING_RESIDUAL_IMPLIES_TASK172_CONSTITUTIVE_CLOSURE=false
TASK171_FACE_ENTHALPY_OBSERVATION_IS_L3_STATE_PRODUCER=false
```

## Property and wall-state admission

The future local state must bind an approved property authority and an exact
property snapshot; compatibility with the reviewed pure-water profile is a
contract condition, not a produced local property state.

```ini
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
L3_LOCAL_PROPERTY_AUTHORITY_CONTRACT_BOUND=true
REAL_L3_LOCAL_PROPERTY_SNAPSHOT_PRESENT=false
```

The reviewed wall-state authority is accepted as the identity prerequisite for
the local wall state.  It does not produce a real wall state or authorize a
same-index mapping:

```ini
L3_WALL_STATE_IDENTITY_PREREQUISITE_REVIEWED=true
L3_LOCAL_FLUID_TO_WALL_SUPPORT_MAPPING_CONTRACT_BOUND=true
L3_LOCAL_FLUID_TO_WALL_REQUIRED_BINDINGS=CASE;PHYSICAL_SUPPORT;PHYSICAL_INTERVAL;WALL_INTERFACE;TOPOLOGY;STREAM_SIDE_WHERE_APPLICABLE
```

## Different-mesh and reconstruction-receipt guards

TASK171 requires an explicit common physical intersection map for different
stream meshes.  The repository audit found no independently reviewed map for
this L3 contract.

```ini
L3_COMMON_PHYSICAL_INTERSECTION_MAPPING_AUTHORITY_BOUND=false
DIFFERENT_MESH_LOCAL_CONSTITUTIVE_MAPPING_ALLOWED=false
```

The model-level future receipt shape is nevertheless fully defined.  It binds
the case, topology, stream/side, physical support, both face states, the
constitutive evaluation state, the operator authority if one is later
approved, property authority, provenance, lifecycle, and canonical identity.
No receipt instance is created here.

```ini
L3_STATE_RECONSTRUCTION_RECEIPT_SCHEMA_BOUND=true
L3_STATE_RECONSTRUCTION_RECEIPT_REQUIRED_FIELDS=RECONSTRUCTION_RECEIPT_ID;SCHEMA_VERSION;CASE_ID;CASE_HASH;TASK171_TOPOLOGY_ID;TASK171_TOPOLOGY_HASH;FLOW_PATH_ID;STREAM_ID;SIDE;PHYSICAL_INTERVAL_ID;PHYSICAL_SUPPORT_ID;NUMERICAL_CELL_ID;UPSTREAM_FACE_STATE_ID;UPSTREAM_FACE_STATE_HASH;DOWNSTREAM_FACE_STATE_ID;DOWNSTREAM_FACE_STATE_HASH;CONSTITUTIVE_EVALUATION_STATE_ID;CONSTITUTIVE_EVALUATION_STATE_HASH;RECONSTRUCTION_OPERATOR_AUTHORITY_ID;RECONSTRUCTION_OPERATOR_AUTHORITY_HASH;PROPERTY_AUTHORITY_ID;PROPERTY_AUTHORITY_VERSION;PROVENANCE_REFS;LIFECYCLE_STATUS;CANONICAL_HASH
REAL_L3_STATE_RECONSTRUCTION_RECEIPT_PRESENT=false
```

## L3 dependency and residual boundary

The model-level dependency graph is bound without making any input instance
available:

```text
TASK171 structural state/support
  -> local fluid-state identity
reviewed reconstruction/direct-state producer
  -> constitutive fluid state
reviewed property authority
  -> local property snapshot
reviewed wall-state authority
  -> local wall-state identity
qualified films/material/Q
  -> local constitutive heat-transfer evaluation
```

```ini
L3_LOCAL_CONSTITUTIVE_DEPENDENCY_GRAPH_BOUND=true
L3_SEGMENT_HEAT_TRANSFER_RESIDUAL_DEFINITION_BOUND=true
L3_HOT_COLD_ENTHALPY_RESIDUAL_DEFINITION_BOUND=true
L3_RESIDUAL_SET_BOUND=true
L3_UNKNOWN_SET_BOUND=false
L3_UNKNOWN_SET=UNRESOLVED_UNTIL_DIRECT_OR_RECONSTRUCTED_STATE_PRODUCER_AND_CONSTITUTIVE_INPUTS_ARE_BOUND
L3_METHOD_STATUS=METHOD_UNBOUND
```

The residual identities are unchanged.  A complete identity contract does not
create a numerical method or make the residual executable.

## L2b, shell J_mu, and numerical guards remain frozen

This gate does not reopen L2b or any physical shell-J_mu branch:

```ini
L2B_BRANCH_STATUS=PAUSED_PENDING_REQUIRED_PHYSICAL_AUTHORITY_CLOSURE
L2B_UNKNOWN_SET_BOUND=false
L2B_RESIDUAL_SET_BOUND=false
L2B_SCALAR_REDUCTION_BOUND=false
L2B_METHOD_STATUS=METHOD_UNBOUND
L2B_BRENT_METHOD_TRANSFER_CANDIDATE_CREATED=false
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
MESH_CONVERGENCE_QUALIFICATION=OPEN
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
PRODUCTION_NUMERICAL_METHOD_AUTHORIZED=false
TASK172_NUMERICAL_EXECUTION_AUTHORIZED=false
```

## Candidate lifecycle and decision

The identity/admission contract is structurally complete at model level, while
the operator remains unbound and the real-instance guards remain false.  The
new authority is only proposed and awaits independent review.

```ini
L3_STATE_RECONSTRUCTION_CONTRACT_BOUND=true
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_CANDIDATE_CREATED=true
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID=V07-T172-L3-LOCAL-STATE-RECONSTRUCTION-CONTRACT-R2
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY
L3_LOCAL_STATE_RECONSTRUCTION_INDEPENDENT_REVIEW=PENDING
NEW_AUTHORITY_SELF_APPROVAL=false
LOCAL_RESIDUAL_AND_METHOD_CANONICAL_BLOCKER_REMOVED=false
```

This is `OUTCOME_A_MODEL_LEVEL_L3_RECONSTRUCTION_CONTRACT_COMPLETE_OPERATOR_UNBOUND`.
It does not promote a reconstruction operator, a direct producer, a property
snapshot, a local state, or an executable L3 method.

## Real-instance and entry-authority guards

```ini
REAL_L3_UPSTREAM_FACE_STATE_PRESENT=false
REAL_L3_DOWNSTREAM_FACE_STATE_PRESENT=false
REAL_L3_CONSTITUTIVE_EVALUATION_STATE_PRESENT=false
REAL_L3_STATE_RECONSTRUCTION_RECEIPT_PRESENT=false
REAL_L3_LOCAL_PROPERTY_SNAPSHOT_PRESENT=false
REAL_L3_LOCAL_CONSTITUTIVE_INSTANCE_PRESENT=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The four effective entry blockers remain:

```ini
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

## Governance and next gate

This package is documentation/evidence-only.  No production code, state
instance, property evaluation, reconstruction, interpolation, constitutive
calculation, solver, tolerance, numerical experiment, mesh study, dependency,
lockfile, workflow, Ready action, or Merge action is authorized or performed.

```ini
TASK171_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_L3_LOCAL_STATE_RECONSTRUCTION_CONTRACT_R2_INDEPENDENT_REVIEW_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
