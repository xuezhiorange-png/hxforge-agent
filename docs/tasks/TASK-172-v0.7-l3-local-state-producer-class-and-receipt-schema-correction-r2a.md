# TASK172 v0.7 — L3 Local-State Producer-Class and Receipt-Schema Correction R2A

This documentation-only correction repairs one ambiguity in the already
constructed R2 model-level L3 contract. R2 supports both a direct local-state
producer and a reconstructed local-state producer, but its single receipt shape
unconditionally required face-state and reconstruction-operator fields. That
would force a direct producer to fabricate reconstruction inputs or an operator
authority.

R2A adds an explicit producer-class discriminator and two conditional receipt
variants. It preserves the R2 authority identity, the unbound reconstruction
operator, all real-instance guards, and all physical and numerical blockers.
No operator is searched for or promoted, and no real state or receipt is
created.

## Receipt identity and scope

```ini
TASK_ID=TASK172_V0_7_L3_LOCAL_STATE_PRODUCER_CLASS_AND_RECEIPT_SCHEMA_CORRECTION_R2A
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=2ba908584ff81888ace37435d918864f3455ccac
MODE=MODEL_LEVEL_PRODUCER_CLASS_AND_RECEIPT_SCHEMA_CORRECTION_ONLY
R2_AUTHORITY_ID=V07-T172-L3-LOCAL-STATE-RECONSTRUCTION-CONTRACT-R2
R2_RESULT=RESOLVED
R2_OUTCOME=OUTCOME_A_MODEL_LEVEL_L3_RECONSTRUCTION_CONTRACT_COMPLETE_OPERATOR_UNBOUND
R2_ORIGINAL_ARTIFACTS_CHANGED=false
R63_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK171_CHANGED=false
TASK166_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This gate does not redo the R2 authority audit. It corrects only the
conditional requiredness of future producer and receipt fields.

## Defect and immutable correction boundary

The R2 receipt schema listed `UPSTREAM_FACE_STATE_ID/HASH`,
`DOWNSTREAM_FACE_STATE_ID/HASH`, and `RECONSTRUCTION_OPERATOR_AUTHORITY_ID/HASH`
as unconditional fields. Those fields are required only for the reconstructed
producer variant. A direct producer supplies the exact local constitutive state
and has no face reconstruction inputs or reconstruction operator authority.

The R2 document, R2 evidence, and r63 registry extension remain byte-immutable.
R2A records the correction as a new r64 registry extension against the same
proposed candidate authority.

## Explicit producer-class discriminator and common authority identity

Every future local constitutive state receipt must carry exactly one explicit
producer class. There is no default, inferred, or caller-only class:

```ini
L3_LOCAL_STATE_PRODUCER_CLASS_CONTRACT_BOUND=true
LOCAL_STATE_PRODUCER_CLASS_ALLOWED=DIRECT_LOCAL_STATE_PRODUCER;RECONSTRUCTED_LOCAL_STATE_PRODUCER
L3_LOCAL_STATE_PRODUCER_AUTHORITY_IDENTITY_CONTRACT_BOUND=true
```

The class name is not authority. Both variants must bind the actual producer
authority ID, hash, lifecycle status, provenance, and canonical state identity.
The common identity fields are:

```ini
COMMON_LOCAL_STATE_RECEIPT_FIELDS=LOCAL_STATE_ID;LOCAL_STATE_HASH;CASE_ID;CASE_HASH;TASK171_TOPOLOGY_ID;TASK171_TOPOLOGY_HASH;FLOW_PATH_ID;STREAM_ID;SIDE;PHYSICAL_INTERVAL_ID;PHYSICAL_SUPPORT_ID;NUMERICAL_CELL_ID;STATE_LOCATION;TEMPERATURE_K;PRESSURE_PA;PROPERTY_AUTHORITY_ID;PROPERTY_AUTHORITY_VERSION;PROPERTY_SNAPSHOT_ID;PROPERTY_SNAPSHOT_HASH;LOCAL_STATE_PRODUCER_CLASS;LOCAL_STATE_PRODUCER_AUTHORITY_ID;LOCAL_STATE_PRODUCER_AUTHORITY_HASH;LOCAL_STATE_PRODUCER_LIFECYCLE_STATUS;PROVENANCE_REFS;CANONICAL_HASH
```

No numeric equality, array index, hidden default, or producer-class name can
replace these bindings.

## Direct local-state receipt variant

For `DIRECT_LOCAL_STATE_PRODUCER`, an independently reviewed producer supplies
the exact constitutive evaluation state. Its receipt requires the common
identity fields and does not require any reconstruction input or operator field:

```ini
L3_DIRECT_LOCAL_STATE_RECEIPT_SCHEMA_BOUND=true
L3_DIRECT_LOCAL_STATE_RECEIPT_VARIANT=L3_DIRECT_LOCAL_STATE_RECEIPT
L3_DIRECT_LOCAL_STATE_REQUIRED_FIELDS=LOCAL_STATE_ID;LOCAL_STATE_HASH;CASE_ID;CASE_HASH;TASK171_TOPOLOGY_ID;TASK171_TOPOLOGY_HASH;FLOW_PATH_ID;STREAM_ID;SIDE;PHYSICAL_INTERVAL_ID;PHYSICAL_SUPPORT_ID;NUMERICAL_CELL_ID;STATE_LOCATION;TEMPERATURE_K;PRESSURE_PA;PROPERTY_AUTHORITY_ID;PROPERTY_AUTHORITY_VERSION;PROPERTY_SNAPSHOT_ID;PROPERTY_SNAPSHOT_HASH;LOCAL_STATE_PRODUCER_CLASS;LOCAL_STATE_PRODUCER_AUTHORITY_ID;LOCAL_STATE_PRODUCER_AUTHORITY_HASH;LOCAL_STATE_PRODUCER_LIFECYCLE_STATUS;PROVENANCE_REFS;CANONICAL_HASH
L3_RECONSTRUCTION_OPERATOR_AUTHORITY_REQUIRED_FOR_DIRECT_CLASS=false
UPSTREAM_FACE_RECONSTRUCTION_INPUT_REQUIRED_FOR_DIRECT_CLASS=false
DOWNSTREAM_FACE_RECONSTRUCTION_INPUT_REQUIRED_FOR_DIRECT_CLASS=false
DIRECT_VARIANT_REQUIRES_RECONSTRUCTION_OPERATOR_FIELDS=false
```

The direct variant must not populate operator fields with `NONE`, `N/A`, or any
other placeholder. Absence of those fields is the schema rule for this variant,
not an unreviewed operator identity.

## Reconstructed local-state receipt variant

For `RECONSTRUCTED_LOCAL_STATE_PRODUCER`, the receipt must bind both exact face
states and the reconstruction operator authority, in addition to the common
local-state identity and constitutive output identity:

```ini
L3_RECONSTRUCTED_LOCAL_STATE_RECEIPT_SCHEMA_BOUND=true
L3_RECONSTRUCTED_LOCAL_STATE_RECEIPT_VARIANT=L3_RECONSTRUCTED_LOCAL_STATE_RECEIPT
L3_RECONSTRUCTED_LOCAL_STATE_REQUIRED_FIELDS=LOCAL_STATE_ID;LOCAL_STATE_HASH;CASE_ID;CASE_HASH;TASK171_TOPOLOGY_ID;TASK171_TOPOLOGY_HASH;FLOW_PATH_ID;STREAM_ID;SIDE;PHYSICAL_INTERVAL_ID;PHYSICAL_SUPPORT_ID;NUMERICAL_CELL_ID;UPSTREAM_FACE_STATE_ID;UPSTREAM_FACE_STATE_HASH;DOWNSTREAM_FACE_STATE_ID;DOWNSTREAM_FACE_STATE_HASH;CONSTITUTIVE_EVALUATION_STATE_ID;CONSTITUTIVE_EVALUATION_STATE_HASH;PROPERTY_AUTHORITY_ID;PROPERTY_AUTHORITY_VERSION;PROPERTY_SNAPSHOT_ID;PROPERTY_SNAPSHOT_HASH;LOCAL_STATE_PRODUCER_CLASS;LOCAL_STATE_PRODUCER_AUTHORITY_ID;LOCAL_STATE_PRODUCER_AUTHORITY_HASH;LOCAL_STATE_PRODUCER_LIFECYCLE_STATUS;RECONSTRUCTION_OPERATOR_AUTHORITY_ID;RECONSTRUCTION_OPERATOR_AUTHORITY_HASH;RECONSTRUCTION_OPERATOR_LIFECYCLE_STATUS;PROVENANCE_REFS;CANONICAL_HASH
L3_RECONSTRUCTION_OPERATOR_AUTHORITY_REQUIRED_FOR_RECONSTRUCTED_CLASS=true
```

Because no reviewed reconstruction operator exists, no reconstructed receipt is
eligible or created:

```ini
L3_EXISTING_RECONSTRUCTION_OPERATOR_AUTHORITY_FOUND=false
L3_RECONSTRUCTION_OPERATOR_AUTHORITY_ID=NONE
L3_STATE_RECONSTRUCTION_OPERATOR_BOUND=false
REAL_L3_RECONSTRUCTED_LOCAL_STATE_RECEIPT_ELIGIBLE=false
```

`NONE` above is only the existing global audit status. It is not a permitted
value for a reconstructed receipt's operator-authority field.

## Variant and canonical-preimage rules

The two receipt variants converge to the same admitted semantic output,
`L3_CONSTITUTIVE_EVALUATION_STATE`, but have different prerequisite fields:

```ini
L3_LOCAL_STATE_RECEIPT_VARIANT_CONTRACT_BOUND=true
L3_RECEIPT_CONDITIONAL_REQUIREDNESS_RULE_BOUND=true
L3_RECEIPT_SEMANTIC_OUTPUT=L3_CONSTITUTIVE_EVALUATION_STATE
L3_LOCAL_STATE_RECEIPT_CANONICAL_PREIMAGE_RULE_BOUND=true
```

The canonical preimage always includes `LOCAL_STATE_PRODUCER_CLASS`,
`LOCAL_STATE_PRODUCER_AUTHORITY_ID`, `LOCAL_STATE_PRODUCER_AUTHORITY_HASH`, and
`LOCAL_STATE_PRODUCER_LIFECYCLE_STATUS`. A reconstructed preimage additionally
includes both face-state identities and the reconstruction-operator authority
ID, hash, and lifecycle status. Changing producer class therefore changes
receipt identity; otherwise identical direct and reconstructed numeric states
cannot share a canonical identity.

## No operator, state, or numerical promotion

R2A preserves every no-convenience rule:

```ini
L3_ARITHMETIC_FACE_TEMPERATURE_MEAN_AUTHORIZED=false
L3_ARITHMETIC_FACE_PRESSURE_MEAN_AUTHORIZED=false
L3_PROPERTY_VALUE_AVERAGING_AUTHORIZED=false
L3_ENTHALPY_TO_TEMPERATURE_INVERSION_AUTHORIZED=false
L3_MIDPOINT_OPERATOR_AUTHORIZED=false
L3_MASS_WEIGHTED_OPERATOR_AUTHORIZED=false
L3_ENTHALPY_EQUIVALENT_OPERATOR_AUTHORIZED=false
L3_CONSTITUTIVE_MIXING_OPERATOR_AUTHORIZED=false
```

No direct or reconstructed state instance is created:

```ini
REAL_L3_DIRECT_LOCAL_STATE_INSTANCE_PRESENT=false
REAL_L3_RECONSTRUCTED_LOCAL_STATE_INSTANCE_PRESENT=false
REAL_L3_UPSTREAM_FACE_STATE_PRESENT=false
REAL_L3_DOWNSTREAM_FACE_STATE_PRESENT=false
REAL_L3_CONSTITUTIVE_EVALUATION_STATE_PRESENT=false
REAL_L3_STATE_RECONSTRUCTION_RECEIPT_PRESENT=false
REAL_L3_LOCAL_PROPERTY_SNAPSHOT_PRESENT=false
REAL_L3_LOCAL_CONSTITUTIVE_INSTANCE_PRESENT=false
```

The candidate remains the same proposed R2 authority and still requires
independent review:

```ini
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_ID=V07-T172-L3-LOCAL-STATE-RECONSTRUCTION-CONTRACT-R2
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_CANDIDATE_CREATED=true
L3_LOCAL_STATE_RECONSTRUCTION_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY
L3_LOCAL_STATE_RECONSTRUCTION_INDEPENDENT_REVIEW=PENDING
NEW_AUTHORITY_SELF_APPROVAL=false
```

`L3_STATE_RECONSTRUCTION_CONTRACT_BOUND=true` remains a model-level contract
status. `L3_STATE_RECONSTRUCTION_OPERATOR_BOUND=false`,
`L3_UNKNOWN_SET_BOUND=false`, and `L3_METHOD_STATUS=METHOD_UNBOUND` remain
unchanged. L2b, the shell-Jmu physical branches, numerical blockers, and the
four effective entry blockers remain frozen.

## Outcome and next gate

```ini
RESULT=CORRECTED
L3_STATE_RECONSTRUCTION_CONTRACT_BOUND=true
L3_STATE_RECONSTRUCTION_OPERATOR_BOUND=false
L3_LOCAL_STATE_PRODUCER_CLASS_CONTRACT_BOUND=true
L3_DIRECT_LOCAL_STATE_RECEIPT_SCHEMA_BOUND=true
L3_RECONSTRUCTED_LOCAL_STATE_RECEIPT_SCHEMA_BOUND=true
L3_LOCAL_STATE_RECEIPT_VARIANT_CONTRACT_BOUND=true
L3_RECEIPT_CONDITIONAL_REQUIREDNESS_RULE_BOUND=true
L3_LOCAL_STATE_PRODUCER_AUTHORITY_IDENTITY_CONTRACT_BOUND=true
L3_LOCAL_STATE_RECEIPT_CANONICAL_PREIMAGE_RULE_BOUND=true
LOCAL_RESIDUAL_AND_METHOD_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_GATE=AUTHORIZE_TASK172_L3_LOCAL_STATE_RECONSTRUCTION_CONTRACT_R2_INDEPENDENT_REVIEW_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

This correction is documentation/evidence-only. It does not perform the next
independent review automatically.
