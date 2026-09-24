# TASK172 — Jμ shell inlet/outlet state-pair contract external review receipt R1

## 1. Receipt and scope

This append-only receipt records an external independent-review decision for
the already-constructed model-level shell-side inlet/outlet state-pair
transfer contract. The review decision was supplied outside Codex. This record
does not claim that Codex independently reviewed or self-approved the
contract, and it does not identify a GitHub reviewer, human expert, or
organization.

```ini
TASK_ID=TASK172_V0_7_JMU_SHELL_INLET_OUTLET_STATE_PAIR_TRANSFER_CONTRACT_INDEPENDENT_REVIEW_RECEIPT_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=72c89e73880c785c3830bac686908291a258dbe0
MODE=EXTERNAL_INDEPENDENT_REVIEW_DECISION_RECORDING_ONLY
PAIR_TRANSFER_AUTHORITY_CANDIDATE_ID=V07-T172-JMU-SHELL-INLET-OUTLET-STATE-PAIR-CONTRACT-R2
INDEPENDENT_REVIEW_RESULT=PASS
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_SHELL_ENDPOINT_STATE_PAIR_TRANSFER_CONTRACT_ONLY
RESULT=REVIEWED
```

The external decision accepts the shape, ownership, binding, provenance and
fail-closed lifecycle contract for a future pair. It does not create or
approve an inlet state, an outlet state, a real pair, a source-mean state, a
mean operator, a pressure rule, a property snapshot, or a producer instance.

## 2. External review provenance

The review source is recorded narrowly as a user-supplied external review
decision. No reviewer identity or credential is asserted.

```ini
EXTERNAL_REVIEW_SOURCE=USER_SUPPLIED_EXTERNAL_INDEPENDENT_REVIEW_DECISION
EXTERNAL_REVIEWER_IDENTITY_ASSERTED=false
GITHUB_REVIEWER_ASSERTED=false
HUMAN_EXPERT_ORGANIZATION_ASSERTED=false
PROFESSIONAL_SIGNATURE_ASSERTED=false
CODEX_INDEPENDENT_APPROVAL_CLAIMED=false
```

The reviewed construction artifact is the R2 contract at
`72c89e73880c785c3830bac686908291a258dbe0`, identified in the R2 registry
extension and its evidence JSON. Historical R2 payloads are not rewritten.

## 3. Accepted model-level contract

The review accepts the distinction:

```text
MODEL_LEVEL_ENDPOINT_STATE_PAIR_CONTRACT
    is not
REAL_CASE_BOUND_ENDPOINT_STATE_PAIR
    and is not
SOURCE_MEAN_BULK_STATE_PRODUCER
```

The model-level contract is promoted only within its own lifecycle scope:

```ini
PAIR_TRANSFER_CONTRACT_INDEPENDENT_REVIEW_COMPLETE=true
PAIR_TRANSFER_CONTRACT_INDEPENDENT_REVIEW_RESULT=PASS
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
LIFECYCLE_PROMOTION_SCOPE=MODEL_LEVEL_SHELL_ENDPOINT_STATE_PAIR_TRANSFER_CONTRACT_ONLY
LIFECYCLE_PROMOTION_PERFORMED=true
SELF_APPROVAL=false
NEW_AUTHORITY_SELF_APPROVAL=false
```

This promotion says that a future endpoint pair must satisfy the reviewed
contract. It does not promote any endpoint producer or real pair.

## 4. Accepted endpoint identity requirements

### 4.1 Inlet

The reviewed future inlet record must bind the following exact identity and
provenance fields:

```text
SHELL_INLET_STATE_ID
SHELL_INLET_STATE_HASH
TASK172_CASE_ID
TASK172_CASE_HASH
SHELL_STREAM_ID
STREAM_ROLE=SHELL_SIDE_FLUID
STATE_LOCATION=INLET
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_PATH_ID
INLET_FACE_ID
TEMPERATURE_K
PRESSURE_PA
PROPERTY_AUTHORITY_ID
PROPERTY_AUTHORITY_VERSION
PROPERTY_SNAPSHOT_ID
PROPERTY_SNAPSHOT_HASH
PROPERTY_SOURCE_ID
PROPERTY_SOURCE_REVISION_OR_HASH
PROPERTY_SOURCE_EVIDENCE_REFS
PROPERTY_SOURCE_RIGHTS_STATUS
STATE_PRODUCER_AUTHORITY_ID
STATE_PRODUCER_LIFECYCLE_STATUS
PROVENANCE_REFS
CANONICAL_HASH
```

No inlet field is populated by this receipt.

### 4.2 Outlet

The reviewed future outlet record must independently bind the corresponding
case, shell stream, topology, physical path, outlet face, temperature,
pressure, property authority/snapshot, producer and provenance identities:

```text
SHELL_OUTLET_STATE_ID
SHELL_OUTLET_STATE_HASH
TASK172_CASE_ID
TASK172_CASE_HASH
SHELL_STREAM_ID
STREAM_ROLE=SHELL_SIDE_FLUID
STATE_LOCATION=OUTLET
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_PATH_ID
OUTLET_FACE_ID
TEMPERATURE_K
PRESSURE_PA
PROPERTY_AUTHORITY_ID
PROPERTY_AUTHORITY_VERSION
PROPERTY_SNAPSHOT_ID
PROPERTY_SNAPSHOT_HASH
PROPERTY_SOURCE_ID
PROPERTY_SOURCE_REVISION_OR_HASH
PROPERTY_SOURCE_EVIDENCE_REFS
PROPERTY_SOURCE_RIGHTS_STATUS
STATE_PRODUCER_AUTHORITY_ID
STATE_PRODUCER_LIFECYCLE_STATUS
PROVENANCE_REFS
CANONICAL_HASH
```

The outlet cannot be inferred from the inlet or relabeled from a legacy
performance result. No outlet field is populated by this receipt.

## 5. Accepted pair identity and direction

The reviewed pair has an identity separate from both endpoint identities:

```text
SHELL_INLET_OUTLET_STATE_PAIR_ID
STATE_PAIR_SCHEMA_VERSION
TASK172_CASE_ID
TASK172_CASE_HASH
SHELL_STREAM_ID
SHELL_INLET_STATE_ID
SHELL_INLET_STATE_HASH
SHELL_OUTLET_STATE_ID
SHELL_OUTLET_STATE_HASH
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_PATH_ID
PAIR_AUTHORITY_ID
PAIR_LIFECYCLE_STATUS
CANONICAL_HASH
```

The review accepts all same-identity requirements:

```ini
INLET_OUTLET_SAME_CASE_REQUIRED=true
INLET_OUTLET_SAME_STREAM_REQUIRED=true
INLET_OUTLET_SAME_TOPOLOGY_REQUIRED=true
INLET_OUTLET_SAME_PHYSICAL_PATH_REQUIRED=true
SHELL_STATE_PAIR_PATH_DIRECTION_RULE_BOUND=true
```

Direction is determined by explicit TASK171 topology:

```text
shell inlet face / upstream-face state
    → identified shell physical path
    → shell outlet face / downstream-face state
```

Temperature magnitude, hot/cold ordering, array position, timestamps or
similar names are not direction or pairing authority.

## 6. Structural and representation dispositions

The external review accepts TASK171 as structural vocabulary only:

```ini
TASK171_SHELL_INLET_OUTLET_STRUCTURAL_MAPPING_CONTRACT_BOUND=true
TASK171_THERMODYNAMIC_STATE_PRODUCER_BOUND=false
```

It also accepts the scoped relationships to existing components:

```ini
TASK160_TO_JMU_SHELL_INLET_STATE_CONTRACT_COMPATIBLE=true
TASK160_COMPATIBILITY_SCOPE=CONDITIONAL_INLET_INPUT_ADAPTER_ONLY
TASK160_SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false

TASK162_DERIVED_OUTLET_PRESENT=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_U=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_TUBE_FILM=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_SHELL_FILM=true
TASK162_DERIVED_OUTLET_ADMISSIBLE_AS_JMU_SOURCE_OUTLET=false

TASK032_STATE_SCHEMA_REPRESENTATION_COMPATIBLE=true
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_INLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_OUTLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_SOURCE_MEAN=false
```

TASK160 compatibility is only a possible future input adapter. TASK171 does
not produce thermodynamic endpoint values. TASK162 remains a legacy derived
whole-exchanger result and cannot be admitted as the J_mu outlet. TASK032 is
only a possible body representation wrapped by endpoint identity; the current
single snapshot is not relabeled.

## 7. Property, temperature, pressure and producer contracts

The review accepts the requirement that each future endpoint carries its own
temperature and pressure identity and an exact, scoped property authority and
snapshot. The inherited water authority is not broadened:

```ini
SHELL_ENDPOINT_PROPERTY_AUTHORITY_CONTRACT_BOUND=true
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true
SHELL_ENDPOINT_TEMPERATURE_IDENTITY_REQUIRED=true
SHELL_ENDPOINT_PRESSURE_IDENTITY_REQUIRED=true
SHELL_ENDPOINT_STATE_PRODUCER_CLASS_CONTRACT_BOUND=true
SHELL_ENDPOINT_STATE_PROVENANCE_CONTRACT_BOUND=true
```

Producer classes such as `CASE_SPECIFIED_STATE`, `MEASURED_STATE`,
`INDEPENDENT_THERMODYNAMIC_CALCULATION` and another explicitly reviewed state
producer are contract vocabulary only. Each actual producer still requires
its own authority, provenance, lifecycle and case binding. Caller assertion
alone is not a producer authority.

The review does not define the later source-mean operation or pressure rule:

```ini
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_AGGREGATION_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
JMU_BULK_PRESSURE_RULE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
```

No arithmetic mean, pressure averaging, property-value averaging or property
backend call is authorized by this receipt.

## 8. Fail-closed pair admission

The accepted contract rejects a future pair for missing or conflicting case,
stream, side, topology, path, face, location, property snapshot, producer,
provenance, lifecycle or canonical identity. It also rejects unsupported
interpolation, caller-only assertion, same-index pairing, hidden/default
state and legacy-result relabeling.

```ini
SHELL_INLET_OUTLET_STATE_PAIR_FAIL_CLOSED_RULES_BOUND=true
PAIR_MISSING_CASE_ID=BLOCKED
PAIR_CASE_MISMATCH=BLOCKED
PAIR_STREAM_OR_SIDE_MISMATCH=BLOCKED
PAIR_TOPOLOGY_OR_PATH_MISMATCH=BLOCKED
PAIR_FACE_OR_LOCATION_MISMATCH=BLOCKED
PAIR_PROPERTY_AUTHORITY_OR_SNAPSHOT_MISMATCH=BLOCKED
PAIR_MISSING_PRODUCER_OR_UNACCEPTED_LIFECYCLE=BLOCKED
PAIR_MISSING_PROVENANCE_OR_RIGHTS_EVIDENCE=BLOCKED
PAIR_UNSUPPORTED_INTERPOLATION=BLOCKED
PAIR_CALLER_ASSERTION_ONLY=BLOCKED
PAIR_SAME_INDEX_ASSUMPTION=BLOCKED
PAIR_LEGACY_RESULT_RELABELING=BLOCKED
PAIR_HIDDEN_OR_DEFAULT_STATE=BLOCKED
```

## 9. Real-instance guards

The external acceptance is strictly model-level. All real endpoint and pair
guards remain false, as do endpoint producer authority fields:

```ini
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_PRODUCER_AUTHORITY_BOUND=false
REAL_SHELL_ENDPOINT_PAIR_RECEIPT_PRESENT=false
REAL_SHELL_ENDPOINT_PAIR_RECEIPT_REVIEW_ELIGIBLE=false
NEXT_ENDPOINT_PAIR_LIFECYCLE_EVENT=REAL_CASE_BOUND_SHELL_INLET_OUTLET_STATE_PAIR_RECEIPT_REQUIRED
```

No real case ID, state ID, endpoint value, property snapshot, producer record,
path/face observation or pair hash is created here.

## 10. Preserved TASK172 branches and blocker

The external review does not change any downstream authority or blocker:

```ini
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false

MATERIAL_K_WALL_TRANSFER_CONTRACT_BOUND=true
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
MATERIAL_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_MATERIAL_AND_K_WALL_EVIDENCE
TRANSFER_CONTRACT_STATUS=REVIEWED_TUBE_FILM_TRANSFER_CONTRACT
CWT_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
CHF_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
C3_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_ORDERING_SOURCE_LEAD
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

Reviewing the model-level pair contract does not make the shell wall
correction executable and does not remove its canonical blocker.

## 11. Governance and next event

Only the external review receipt, machine evidence and a new append-only
registry extension are added. Prior R1–R58 payloads and hashes remain
immutable. The next event is not executed by this task:

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
PROPERTY_CALCULATION_EXECUTED=false
MEAN_CALCULATION_EXECUTED=false
PRESSURE_COMBINATION_EXECUTED=false
TASK162_OUTLET_PROMOTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The next endpoint lifecycle event requires a real, case-bound, independently
sourced and reviewed shell inlet/outlet pair receipt. It is outside this
receipt.
