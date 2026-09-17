# TASK172 — Jμ shell inlet/outlet state-pair transfer contract R2

## 1. Receipt and scope

This is a documentation/evidence-only construction of the model-level
identity contract for a future shell-side inlet/outlet thermodynamic state
pair. The pair is an upstream prerequisite for the source-mean bulk state
used by a future Jamil/Thome `J_mu` authority. This record does not define the
source mean operator, combine endpoint pressures, create endpoint values, or
produce a real pair.

```ini
TASK_ID=TASK172_V0_7_JMU_SHELL_INLET_OUTLET_STATE_PAIR_TRANSFER_CONTRACT_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=3ce65a2170c6b3dfce7d24a795f3851baf031ffd
MODE=MODEL_LEVEL_SHELL_ENDPOINT_STATE_PAIR_CONTRACT_ONLY
SUBJECT=JMU_SHELL_INLET_OUTLET_STATE_PAIR
RESULT=RESOLVED
OUTCOME=OUTCOME_A_ENDPOINT_STATE_PAIR_CONTRACT_COMPLETE_NO_INSTANCE
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_AGGREGATION_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
JMU_BULK_PRESSURE_RULE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The result `RESOLVED` is deliberately scoped: the model-level endpoint
pair-contract shape is complete. It does not mean that an inlet, an outlet, a
property snapshot, a source mean, or a J_mu case authority exists.

## 2. Accepted predecessor and non-scope

The predecessor records the source observation that shell-side bulk
properties are evaluated using a mean of the source stream inlet and outlet
bulk temperatures, while leaving the aggregation operator and pressure rule
unresolved. Those two unresolved source-rule branches remain paused here.

The accepted source and repository boundaries are:

```ini
JMU_BULK_STATE_SOURCE_RULE_BOUND=true
JMU_BULK_STATE_SOURCE_ID=THOME-2004-EDB3-CH3-CROSSCHECK
JMU_BULK_STATE_STREAM_ROLE_BOUND=true
JMU_BULK_STATE_STREAM_ROLE=SHELL_SIDE_FLUID
JMU_SOURCE_BULK_STATE_GRANULARITY_BOUND=true
JMU_SOURCE_BULK_STATE_GRANULARITY=WHOLE_EXCHANGER_SHELL_STREAM_MEAN_OF_SOURCE_INLET_AND_OUTLET_BULK_STATE
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
```

This gate does not perform literature research, mean calculation, pressure
selection, property-backend calls, TASK162 promotion, material work, wall
solving, Q work, C3 ordering, numerical work, or implementation.

## 3. Model contract versus real instance

The contract defines what a future record must contain and how its identity is
bound. It intentionally leaves every real endpoint and pair field
unpopulated.

| Layer | This gate | Meaning |
| --- | --- | --- |
| Model contract | `SHELL_INLET_STATE_CONTRACT_BOUND=true`; `SHELL_OUTLET_STATE_CONTRACT_BOUND=true`; `SHELL_INLET_OUTLET_STATE_PAIR_CONTRACT_BOUND=true` | Required identity, provenance, lifecycle and fail-closed shape is defined. |
| Real inlet | `REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false` | No case-bound shell inlet state exists. |
| Real outlet | `REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false` | No case-bound shell outlet state exists. |
| Real pair | `REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false` | No pair has been admitted for a case or source-mean producer. |
| Producer lifecycle | `SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false`; `SHELL_OUTLET_STATE_PRODUCER_AUTHORITY_BOUND=false` | No endpoint producer has been independently reviewed or promoted. |

The model-level candidate is therefore proposed, not self-approved:

```ini
JMU_SHELL_INLET_OUTLET_STATE_PAIR_CONTRACT_CANDIDATE_CREATED=true
PAIR_TRANSFER_AUTHORITY_CANDIDATE_ID=V07-T172-JMU-SHELL-INLET-OUTLET-STATE-PAIR-CONTRACT-R2
PAIR_TRANSFER_AUTHORITY_LIFECYCLE=PROPOSED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
INDEPENDENT_REVIEW=PENDING
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
```

## 4. Endpoint identity contract

### 4.1 Shell inlet

A future inlet record must carry all of the following fields. They are
requirements, not values created by this gate:

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

`STATE_LOCATION=INLET` is a semantic location, not an inference from a
temperature or array position. In the TASK171 vocabulary it is represented by
the path's explicit inlet face and the corresponding upstream-face state
location when a future state producer supplies one.

### 4.2 Shell outlet

A future outlet record must independently carry the same case, shell stream,
topology and physical-path identities, with:

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

The outlet is not derived from the inlet in this gate. A shared field name,
equal value, timestamp, or array index cannot substitute for the independent
outlet identity and producer provenance.

## 5. Pair identity and binding rules

The future pair has its own canonical identity, separate from both endpoint
identities:

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

The pair contract requires all of these relations:

```ini
INLET_OUTLET_SAME_CASE_REQUIRED=true
INLET_OUTLET_SAME_STREAM_REQUIRED=true
INLET_OUTLET_SAME_TOPOLOGY_REQUIRED=true
INLET_OUTLET_SAME_PHYSICAL_PATH_REQUIRED=true
SHELL_STATE_PAIR_PATH_DIRECTION_RULE_BOUND=true
```

The direction is the explicit TASK171 path order:

```text
shell inlet face / upstream-face state
    → one identified shell physical path
    → shell outlet face / downstream-face state
```

Temperature magnitude is not a direction rule. Hotter is not automatically
inlet, and colder is not automatically outlet. A pair is rejected when its
faces, state locations, stream side, topology or path order disagree even if
the numerical values happen to look plausible.

## 6. TASK171 structural mapping

The reviewed TASK171 topology authority supplies enough model-level structural
vocabulary for this contract:

* `flow_path_id`/`stream_id`/`side`/`role` identify a path and its stream;
* `inlet_face_id` and `outlet_face_id` identify the path endpoints;
* `physical_inlet_m`, `physical_outlet_m` and tube-position identities support
  physical-path binding;
* `UPSTREAM_FACE` and `DOWNSTREAM_FACE` provide location semantics;
* a `State` can carry location, owner, flow-path identity, authority and
  producer status.

Those are structural identities only. TASK171 does not produce thermodynamic
values, property snapshots, or an inlet/outlet state pair.

```ini
TASK171_SHELL_INLET_OUTLET_STRUCTURAL_MAPPING_CONTRACT_BOUND=true
TASK171_STRUCTURAL_AUTHORITY_ID=V07-T171-TOPOLOGY-R4-V1
TASK171_STRUCTURAL_SOURCE_PATH=docs/tasks/TASK-171-v0.7-segmented-thermal-state-topology-engine.md
TASK171_THERMODYNAMIC_STATE_PRODUCER_BOUND=false
TASK171_THERMODYNAMIC_STATE_PRODUCER_STATUS=UNRESOLVED
```

No thermodynamic producer is promoted by this structural mapping.

## 7. Relation to existing repository authorities

### 7.1 TASK160

TASK160 can represent a future shell inlet input condition through its
stream-bound inlet temperature, optional inlet pressure, stream side binding,
property snapshot and provenance inputs. It does not itself provide a
TASK172 endpoint producer, outlet, physical face or path identity.

Accordingly:

```ini
TASK160_TO_JMU_SHELL_INLET_STATE_CONTRACT_COMPATIBLE=true
TASK160_TO_JMU_SHELL_INLET_STATE_COMPATIBILITY_SCOPE=CONDITIONAL_INLET_INPUT_ADAPTER_ONLY
TASK160_SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false
TASK160_OUTLET_STATE_AVAILABLE=false
TASK160_PATH_AND_FACE_BINDING_AVAILABLE=false
```

The compatibility flag means that a future separately reviewed adapter may
bind an exact TASK160 inlet record into the endpoint contract. It is not a
real mapping instance and is not producer approval.

### 7.2 TASK162

TASK162 contains a legacy whole-exchanger derived outlet result. Its result is
present in the repository, but it is not admissible as the J_mu source outlet:

```ini
TASK162_DERIVED_OUTLET_PRESENT=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_U=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_TUBE_FILM=true
TASK162_DERIVED_OUTLET_DEPENDS_ON_SHELL_FILM=true
TASK162_DERIVED_OUTLET_ADMISSIBLE_AS_JMU_SOURCE_OUTLET=false
TASK162_DERIVED_OUTLET_DISPOSITION=LEGACY_WHOLE_EXCHANGER_RESULT_NOT_TASK172_ENDPOINT_AUTHORITY
```

The contract neither relabels nor reuses that result. No outlet instance is
created here.

### 7.3 TASK032

The TASK032 `PropertySnapshot` shape is compatible as a body representation
inside a future endpoint record, provided the endpoint identity, source,
location and case bindings are added by the new contract. That representation
compatibility must not relabel the existing snapshot:

```ini
TASK032_STATE_SCHEMA_REPRESENTATION_COMPATIBLE=true
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_INLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_OUTLET=false
TASK032_EXISTING_SINGLE_BULK_SNAPSHOT_IS_SOURCE_MEAN=false
TASK032_ENDPOINT_WRAPPER_REQUIRED=true
```

The current TASK032 snapshot remains a generic caller-bound bulk snapshot. It
is not an endpoint and is not a source mean.

## 8. Endpoint property, temperature and pressure requirements

The contract requires each endpoint to carry its own temperature, pressure,
property authority/version and property snapshot identity. It does not choose
how those endpoint values will later be combined.

```ini
SHELL_ENDPOINT_PROPERTY_AUTHORITY_CONTRACT_BOUND=true
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBILITY_SCOPE=REVIEWED_PURE_WATER_PROFILE_SCOPE_ONLY;NO_ENDPOINT_INSTANCE;NO_MEAN_PRODUCER
SHELL_ENDPOINT_TEMPERATURE_IDENTITY_REQUIRED=true
SHELL_ENDPOINT_PRESSURE_IDENTITY_REQUIRED=true
```

The reviewed water authority is inherited conditionally and its narrow fluid,
temperature, pressure and phase domain is not expanded. No property backend is
called and no property value is selected.

These fields remain deliberately unresolved:

```ini
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=false
JMU_BULK_TEMPERATURE_AGGREGATION_RULE=PAUSED_PENDING_CONCRETE_SOURCE_RULE
JMU_BULK_PRESSURE_RULE_BOUND=false
JMU_BULK_PRESSURE_RULE=PAUSED_PENDING_CONCRETE_SOURCE_RULE
SOURCE_MEAN_AGGREGATION_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
JMU_BULK_PRESSURE_RULE_BRANCH_STATUS=PAUSED_PENDING_CONCRETE_SOURCE_RULE
```

In particular, this record does not authorize
`T_mean=(T_in+T_out)/2`, arithmetic pressure averaging, property-value
averaging, or a source-mean producer.

## 9. Producer and provenance contract

The model-level contract defines an allowed future producer-class field but
does not approve any producer. A future endpoint must use an explicitly
reviewed producer class such as `CASE_SPECIFIED_STATE`, `MEASURED_STATE`, or
`INDEPENDENT_THERMODYNAMIC_CALCULATION`; a caller assertion alone is never
authority.

```ini
SHELL_ENDPOINT_STATE_PRODUCER_CLASS_CONTRACT_BOUND=true
SHELL_ENDPOINT_STATE_PRODUCER_CLASS_RULE=EXPLICIT_REVIEWED_PRODUCER_CLASS_REQUIRED;CALLER_ASSERTION_NOT_AUTHORITY
SHELL_ENDPOINT_STATE_PROVENANCE_CONTRACT_BOUND=true
SHELL_ENDPOINT_PROVENANCE_REQUIRED=PRODUCER_ID_AND_REVISION_OR_HASH;SOURCE_EVIDENCE;RIGHTS_OR_REVIEWABILITY;CASE_CONFIGURATION;STREAM;TOPOLOGY;PATH;FACE;PROPERTY_SNAPSHOT;CANONICAL_IDENTITY;LIFECYCLE
```

Endpoint and pair lifecycle status must be accepted by the relevant external
review process before an instance can enter any later source-mean producer.

## 10. Fail-closed admission rules

The future pair contract rejects a pair when any of the following is missing,
conflicting or unreviewed:

* case identity or case hash;
* stream identity or `SHELL_SIDE_FLUID` role;
* topology identity;
* physical-path identity;
* explicit inlet/outlet face and state-location identity;
* same-case, same-stream, same-topology or same-path relation;
* endpoint property authority/version or property snapshot hash;
* producer authority, lifecycle or provenance;
* source evidence or rights/reviewability information;
* canonical endpoint or pair hash;
* supported endpoint state location or source-defined interpolation;
* a caller-only assertion, same-index assumption or legacy-result relabeling;
* a hidden/default property or a mismatched source/case/configuration binding.

```ini
SHELL_INLET_OUTLET_STATE_PAIR_FAIL_CLOSED_RULES_BOUND=true
PAIR_MISSING_CASE_ID=BLOCKED
PAIR_CASE_MISMATCH=BLOCKED
PAIR_STREAM_OR_SIDE_MISMATCH=BLOCKED
PAIR_TOPOLOGY_OR_PATH_MISMATCH=BLOCKED
PAIR_FACE_OR_LOCATION_MISMATCH=BLOCKED
PAIR_PROPERTY_AUTHORITY_OR_SNAPSHOT_HASH_MISMATCH=BLOCKED
PAIR_MISSING_PRODUCER_OR_UNACCEPTED_LIFECYCLE=BLOCKED
PAIR_CALLER_ASSERTION_ONLY=BLOCKED
PAIR_SAME_INDEX_ASSUMPTION=BLOCKED
PAIR_LEGACY_RESULT_RELABELING=BLOCKED
PAIR_UNSUPPORTED_INTERPOLATION=BLOCKED
```

## 11. State that remains absent

This contract is not a source-mean contract. It is only the upstream identity
boundary. All actual values, endpoint IDs and producer instances remain
absent:

```ini
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
SHELL_INLET_STATE_PRODUCER_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_PRODUCER_AUTHORITY_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
```

No actual shell inlet or outlet temperature, pressure, property snapshot,
case, path, face, pair hash or J_mu numerator state is introduced.

## 12. Preserved downstream state

The following unrelated branches are inherited without promotion or payload
rewrite:

```ini
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

No material, Q, tube-film instance, shell film, wall correction or numerical
authority is created by this task.

## 13. Decision and next gate

The complete model-level identity/provenance/lifecycle shape is definable from
the reviewed TASK171 structural vocabulary plus explicit endpoint wrappers.
This permits a proposed contract candidate, but no real pair and no source
mean calculation.

```ini
RESULT=RESOLVED
OUTCOME=OUTCOME_A_ENDPOINT_STATE_PAIR_CONTRACT_COMPLETE_NO_INSTANCE
SHELL_INLET_STATE_CONTRACT_BOUND=true
SHELL_OUTLET_STATE_CONTRACT_BOUND=true
SHELL_INLET_OUTLET_STATE_PAIR_CONTRACT_BOUND=true
JMU_SHELL_INLET_OUTLET_STATE_PAIR_CONTRACT_CANDIDATE_CREATED=true
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
PRODUCTION_ADMISSION=BLOCKED_FAIL_CLOSED
NEXT_GATE=AUTHORIZE_TASK172_JMU_SHELL_INLET_OUTLET_STATE_PAIR_TRANSFER_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
```

The next gate is independent review of this model-level contract only. It does
not imply endpoint instance creation, source-mean rule selection, pressure
combination, production admission, implementation, Ready or Merge.

## 14. Validation and immutability

The companion machine evidence records the source/document identities,
required fields, preserved false instance guards, and append-only registry
binding. The registry extension is appended after `r57_extension`; prior
payloads and hashes are not rewritten. The canonical hashes use the repository
`hexagent.canonical_json.canonical_sha256` rule.

Validation is limited to this documentation/evidence change: JSON parsing and
canonical-hash checks, registry/history integrity, reference and source-hash
consistency, diff allowlist, whitespace, Ruff, formatting, mypy, manifest and
lock checks as applicable. No property calculation, endpoint construction,
mean operation or numerical execution is performed.

```ini
INTERMEDIATE_GITHUB_CI_RUNS=0
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
