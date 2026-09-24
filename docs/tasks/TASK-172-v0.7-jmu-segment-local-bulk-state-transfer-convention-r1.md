# TASK172 v0.7 — segment-local bulk-state transfer convention for shell J_mu R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_JMU_SEGMENT_LOCAL_BULK_STATE_TRANSFER_CONVENTION_R1
MODE=PROJECT_COMPUTATIONAL_LOCALIZATION_TRANSFER_CONVENTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=91128e1e533d46944ffca4e97df9c6f8f66e29f6
HEAD_PRECONDITION_VERIFIED=true
RESULT=RESOLVED_JMU_SEGMENT_LOCAL_BULK_TRANSFER_CONVENTION
```

This append-only overlay resolves one project-computational localization
question.  It does not change the Bayram equation candidate, exponent,
Bell/Jamil lineage, pressure semantics, wall-surface scope, numerical method,
or any historical R1–R89 payload.  It does not create a local-state producer,
property snapshot, real state, executable J_mu, wall solution, numerical
experiment, or mesh result.

## 1. Historical correction boundary

R89 is immutable.  R89 correctly established the physical factor candidate,
but its statement that the candidate was already locally mapped was premature:

```ini
R89_EQUATION_CANDIDATE_ACCEPTED=true
R89_EXPONENT_CANDIDATE_ACCEPTED=true
JMU_EQUATION_TRANSFER_BOUND=true
JMU_EXPONENT_TRANSFER_BOUND=true
JMU_MULTIPLICATIVE_COMBINATION_BOUND=true
JMU_SHELL_WALL_PROPERTY_MAPPING_BOUND=true
WALL_MAPPING_SCOPE=CLEAN_SURFACE_ONLY
DOUBLE_COUNTING_REJECTED=true
R89_LOCAL_BULK_MAPPING_WAS_PREMATURE=true
R89_LOCAL_BULK_MAPPING_REQUIRES_TRANSFER_CONVENTION=true
R89_DOCUMENT_CHANGED=false
R89_EVIDENCE_CHANGED=false
R89_EXTENSION_REWRITTEN=false
```

The two R89 compatibility fields are therefore re-established here as an
effective overlay only, after the project localization predicates below are
bound.  This is not a rewrite of R89.

## 2. Source rule and project architecture are separate layers

The source physical relation remains exactly the source-observed relation:

```ini
SOURCE_BULK_PROPERTY_OPERATOR=SHELL_FLUID_DYNAMIC_VISCOSITY_AT_AVERAGE_TEMPERATURE
SOURCE_WALL_PROPERTY_OPERATOR=SHELL_FLUID_DYNAMIC_VISCOSITY_AT_WALL_TEMPERATURE
SOURCE_RULE=(mu_s/mu_s,w)^0.14
SOURCE_RULE_IS_SEGMENT_LOCAL=false
SOURCE_RULE_IS_LOCALIZATION_AUTHORITY=false
SOURCE_RULE_PROVIDES_BULK_VS_WALL_PROPERTY_DISTINCTION=true
LAYER_A_ROLE=PHYSICAL_SOURCE_RELATION
```

Bayram does not say “per segment”, “per cell”, “face mean”, “midpoint”, or
“whole-exchanger source mean” as a TASK172 runtime operator.  No such wording
is manufactured here.

The project convention is a separate layer.  For an admitted TASK171 physical
support `k`, it defines only how the already-authorized source factor is
evaluated in the frozen segmented TASK172 architecture:

```text
J_mu,k = (mu_bulk,k / mu_wall,k)^0.14

mu_bulk,k = shell-fluid viscosity from the exact admitted located local
             shell bulk property snapshot for physical support k
mu_wall,k = shell-fluid viscosity from the exact admitted located shell-fluid
             wall/interface property snapshot for physical support k
```

```ini
LAYER_B_ROLE=PROJECT_COMPUTATIONAL_LOCALIZATION_CONVENTION
SOURCE_AND_PROJECT_CONVENTION_DISTINGUISHED=true
LOCALIZATION_NOT_MISREPRESENTED_AS_SOURCE_TEXT=true
PROJECT_LOCALIZATION_CONVENTION_AUTHORITY_BASIS=FROZEN_PROJECT_SEGMENTED_ARCHITECTURE_PLUS_SOURCE_FORM_PRESERVATION
```

The project authority is the frozen TASK170/TASK171 ownership and state
boundary, combined with the already accepted R89 physical form.  It does not
claim that Bayram independently authorizes segment-local evaluation.

## 3. Frozen ownership and state-producer boundary

TASK170 assigns TASK171 the segmented topology/state/conservation interface and
TASK172 local property, wall/interface constitutive and convergence closure.
TASK174 owns detailed hydraulic pressure evolution and TASK173 owns the full
rating/sizing boundary solve.  This overlay preserves those boundaries.

The convention consumes a located local state; it cannot produce one.  The
TASK171/L3 contracts define `CELL_MEAN` as a location/schema identity, not an
implicit arithmetic operator, and no reviewed reconstruction operator is
selected here.

```ini
LOCALIZATION_CONVENTION_CONSUMES_LOCAL_STATE=true
LOCALIZATION_CONVENTION_PRODUCES_LOCAL_STATE=false
LOCAL_STATE_RECONSTRUCTION_OPERATOR_SELECTED=false
LOCAL_BULK_STATE_OPERATOR_INHERITED_FROM_ADMITTED_STATE_PRODUCER=true
LOCAL_BULK_STATE_OPERATOR_CREATED_BY_THIS_GATE=false
LOCALIZATION_REQUIRES_ADMITTED_LOCATED_LOCAL_STATE=true
LOCAL_BULK_STATE_UNAVAILABLE=FAIL_CLOSED
L3_ARITHMETIC_FACE_TEMPERATURE_MEAN_AUTHORIZED=false
L3_ARITHMETIC_FACE_PRESSURE_MEAN_AUTHORIZED=false
L3_PROPERTY_VALUE_AVERAGING_AUTHORIZED=false
```

In particular, this gate does not define any of the following:

```text
T_bulk,k = (T_face,in + T_face,out)/2
P_bulk,k = (P_face,in + P_face,out)/2
enthalpy mean -> temperature
property-value mean
geometric-midpoint temperature
whole-exchanger inlet/outlet mean
```

## 4. Local factor and Bell placement

For each admitted physical support, the localization convention evaluates the
J_mu factor once using that support's two admitted property snapshots.  It does
not localize or re-authorize every other Bell factor.

```text
h_shell,k = h_base,k
            * J_c,k * J_l,k * J_b,k * J_s,k * J_r,k * J_mu,k
```

The separate Bell-factor authorities determine which factors are support-local.
This receipt binds only the J_mu localization and preserves the existing
native Jamil placement.

```ini
JMU_LOCAL_FACTOR_EVALUATED_ONCE_PER_PHYSICAL_SUPPORT=true
GLOBAL_JMU_REUSED_FOR_EVERY_SEGMENT=false
JMU_FACTOR_AVERAGED_ACROSS_SEGMENTS=false
JMU_PROPERTY_VALUES_AVERAGED_ACROSS_SEGMENTS=false
JMU_RUNTIME_LOCAL_STATE_MAPPING_COMPATIBLE=true
SOURCE_TO_SEGMENT_LOCAL_BULK_TRANSFER_BOUND=true
PROJECT_SEGMENT_LOCAL_JMU_CONVENTION_BOUND=true
```

No global factor may be copied into every support, and no array index may
substitute for physical-support identity.

## 5. Support identity and fail-closed reuse

Every future support-local evaluation must bind the following identities before
the factor can be admitted.  This is a schema requirement; this gate creates
no values or snapshots.

```ini
PHYSICAL_SUPPORT_LOCAL_JMU_IDENTITY_FIELDS=PHYSICAL_SUPPORT_ID;PHYSICAL_SUPPORT_HASH;FLOW_PATH_ID;SHELL_STREAM_ID;SHELL_SIDE_IDENTITY;LOCAL_BULK_STATE_ID;LOCAL_BULK_STATE_HASH;LOCAL_BULK_PROPERTY_SNAPSHOT_ID;LOCAL_BULK_PROPERTY_SNAPSHOT_HASH;WALL_INTERFACE_STATE_ID;WALL_INTERFACE_STATE_HASH;WALL_PROPERTY_SNAPSHOT_ID;WALL_PROPERTY_SNAPSHOT_HASH;JMU_SOURCE_AUTHORITY_ID;JMU_SOURCE_AUTHORITY_HASH;LOCALIZATION_CONVENTION_ID;LOCALIZATION_CONVENTION_HASH
LOCALIZATION_CONVENTION_ID=V07-T172-JMU-SEGMENT-LOCAL-BULK-TRANSFER-CONVENTION-R1
SUPPORT_STATE_REUSE_ACROSS_PHYSICAL_SUPPORTS_ALLOWED=false
SUPPORT_IDENTITY_MISMATCH=REJECT
MISSING_LOCAL_BULK_STATE=REJECT
MISSING_LOCAL_BULK_PROPERTY_SNAPSHOT=REJECT
MISSING_WALL_INTERFACE_STATE=REJECT
MISSING_WALL_PROPERTY_SNAPSHOT=REJECT
```

The convention cannot turn a future direct producer or reconstructed producer
into a valid producer.  It consumes whichever producer class is later admitted
under the reviewed L3 contract, with exact case/topology/path/stream/interval/
support identity and canonical provenance.

## 6. One-support source recovery

The source-recovery statement is conditional on the local-state producer, not
on the number of array entries.  For one physical support, if the admitted
local bulk producer returns exactly the source bulk/average state and the
admitted wall producer returns exactly the source wall-property state, then:

```text
mu_bulk,1 = mu_bulk,source
mu_wall,1 = mu_wall,source
J_mu,1    = (mu_bulk,1 / mu_wall,1)^0.14
          = (mu_bulk,source / mu_wall,source)^0.14
          = J_mu,source
```

```ini
ONE_SEGMENT_SOURCE_RECOVERY_CONDITION_BOUND=true
ONE_SEGMENT_SOURCE_RECOVERY_IS_CONDITIONAL=true
ONE_SEGMENT_AUTOMATIC_SOURCE_MEAN_EQUIVALENCE_CLAIMED=false
```

This is a mathematical identity under the stated producer condition.  It is
not a claim that every N=1 model has a valid local-state producer.

## 7. Invariance and variable-property semantics

The convention preserves the dimensionless ratio, orientation, exponent and
multiplicative placement:

```ini
CONSTANT_PROPERTY_LOCALIZATION_INVARIANCE=true
DIMENSIONLESS_RATIO_PRESERVED=true
EXPONENT_PRESERVED=true
RATIO_ORIENTATION_PRESERVED=true
MULTIPLICATIVE_PLACEMENT_PRESERVED=true
JMU_EXPONENT=0.14
JMU_RATIO_ORIENTATION=BULK_OVER_WALL
```

If `mu_bulk,k` and `mu_wall,k` are constant over all supports, every `J_mu,k`
is the same constant.  Under variable properties, however,

```text
J_mu(source mean) != mean(J_mu,k)
J_mu(global bulk state) != J_mu,k
```

in general.  The project is changing evaluation granularity, not the physical
form:

```ini
GLOBAL_AND_LOCAL_JMU_NUMERIC_EQUIVALENCE_REQUIRED=false
LOCALIZATION_CHANGES_EVALUATION_GRANULARITY=true
LOCALIZATION_CHANGES_PHYSICAL_FORM=false
```

No refit, segment-size-dependent exponent, new coefficient, or source-domain
broadening is introduced.

## 8. Wall, pressure and historical source-mean boundaries

The R89 clean-surface mapping is preserved.  `mu_wall,k` means the shell-fluid
property at the admitted local shell-fluid wall/interface state.  It is not a
metal centerline temperature, tube-side wall temperature, or averaged wall
temperature.

```ini
WALL_MAPPING_SCOPE=CLEAN_SURFACE_ONLY
FOULED_INTERFACE_TRANSFER=BLOCKED_PENDING_SEPARATE_WALL_LOCATION_AUTHORITY
LOCAL_PROPERTY_PRESSURE_SOURCE=LOCATED_LOCAL_SHELL_PRESSURE_STATE
TASK172_GENERATES_HYDRAULIC_PRESSURE_FIELD=false
MEAN_PRESSURE_RULE_REQUIRED_FOR_LOCAL_RUNTIME=false
PRESSURE_RULE_CREATED=false
```

R71–R82 whole-exchanger source-mean research remains immutable historical
evidence.  It is retained as source-form reference, conditional one-support
recovery reference, or an optional later comparison projection only:

```ini
SOURCE_MEAN_PATH_RETAINED_AS_REFERENCE_ONLY=true
SOURCE_MEAN_PATH_REACTIVATED_AS_RUNTIME=false
WHOLE_EXCHANGER_SOURCE_MEAN_PATH_SELECTED_FOR_TASK172_RUNTIME=false
```

No inlet, outlet, arithmetic-mean, representative, constant, or
pressure-insensitivity convention is introduced.

## 9. Mesh and numerical relationship

This convention does not qualify mesh independence.  Changing segmentation can
change local bulk states, wall states, the `J_mu,k` distribution and local
duties; those effects remain subject to the mesh convergence gate.

```ini
LOCALIZATION_REQUIRES_LATER_MESH_QUALIFICATION=true
MESH_THRESHOLD_SELECTED=false
MESH_STUDY_PERFORMED=false
METHOD_CLASS=BOUND_AWARE_VECTOR_NONLINEAR_RESIDUAL_SOLVE
IMPLEMENTATION_CANDIDATE=SCIPY_OPTIMIZE_LEAST_SQUARES
SCIPY_METHOD=trf
LOSS=linear
EXECUTABLE_NUMERICAL_PROFILE_BOUND=false
```

R88's method contract is replayed without selecting tolerances, Jacobian
policy, resource caps, or an executable numerical profile.

## 10. Effective candidate state and decision

The project-level localization convention is now complete for the narrow
clean-surface J_mu transfer.  It completes the R89 candidate at the
model-contract level, but it does not promote the candidate to reviewed
authority or remove the shell-wall blocker.

```ini
R89_TRANSFER_CANDIDATE_COMPLETED_BY_LOCALIZATION_OVERLAY=true
SHELL_JMU_TRANSFER_CANDIDATE_READY_FOR_INDEPENDENT_REVIEW=true
SHELL_JMU_TRANSFER_CANDIDATE_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
JMU_EXECUTABLE_AUTHORITY_BOUND=false
NEW_AUTHORITY_SELF_APPROVAL=false
SHELL_WALL_CORRECTION_STATUS=PROPOSED_AUTHORITY_REVIEW_PENDING
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

The remaining parent blockers remain:

1. `SHELL-WALL-CORRECTION-AUTHORITY` — the R89 candidate plus this
   localization overlay awaits independent review and blocker-closure
   adjudication;
2. `NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW`;
3. `MESH-CONVERGENCE-QUALIFICATION`.

No real case, endpoint state, property snapshot, pressure authority, Q
receipt, J_mu execution, wall solution, numerical experiment, or mesh study is
created by this gate.

## 11. Governance and final receipt

```ini
TASK170_TASK172_OWNER_REPLAY=PASS
TASK171_LOCATION_IDENTITY_REPLAY=PASS
L3_STATE_PRODUCER_BOUNDARY_REPLAY=PASS
R1_R89_HISTORICAL_PAYLOADS_IMMUTABLE=true
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
LOCKFILE_CHANGED=false
TASK166_CHANGED=false
TASK171_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
PROPERTY_BACKEND_CALLED=false
JMU_EXECUTED=false
WALL_STATE_SOLVED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_MINIMAL_GATE=AUTHORIZE_TASK172_SHELL_JMU_TRANSFER_CANDIDATE_INDEPENDENT_REVIEW_AND_BLOCKER_CLOSURE_ADJUDICATION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The document, evidence, extension and registry-root hashes are recorded in the
R90 evidence payload and append-only registry extension after validation.
