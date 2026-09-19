# TASK172 — external review receipt for the signed-Q contract

## 1. Receipt boundary

This document records the external scoped decision for the already-defined
model-level external signed-heat-rate contract
`V07-T172-EXTERNAL-SIGNED-Q-INPUT-AUTHORITY-CONTRACT-R3`. The decision accepts
the contract shape and its ownership, binding, provenance, dependency,
canonical-identity, lifecycle, and fail-closed rules. It does not create or
approve a case-bound Q receipt.

The decision was supplied outside Codex in the authorized task instruction.
This record does not invent a GitHub reviewer, human expert, organization,
professional signature, or credential. It is not inferred from PR state and is
not a substitute for a GitHub review event.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_CONTRACT_REVIEW_RECEIPT_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=ce0f97d05817901c0cc312b3d09ffe889a306eee
MODE=EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_RECEIPT_ONLY
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_ID=V07-T172-EXTERNAL-SIGNED-Q-INPUT-AUTHORITY-CONTRACT-R3
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
EXTERNAL_Q_AUTHORITY_CONTRACT_CANDIDATE_CREATED=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_COMPLETE=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_RESULT=PASS
EXTERNAL_Q_CONTRACT_STATUS=REVIEWED_CONTRACT
EXTERNAL_Q_INSTANCE_STATUS=NONE
LIFECYCLE_PROMOTION_SCOPE=MODEL_LEVEL_EXTERNAL_Q_CONTRACT_SHAPE_ONLY
LIFECYCLE_PROMOTION_PERFORMED=true
NEW_AUTHORITY_SELF_APPROVAL=false
CODEX_INDEPENDENT_APPROVAL_CLAIMED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

`REVIEWED_CONTRACT` is deliberately not `ACCEPTED_EXTERNAL_Q_AUTHORITY`.
Only the generic contract has advanced. The actual external-Q authority
instance remains absent.

## 2. External decision provenance

```ini
EXTERNAL_REVIEW_SOURCE_TYPE=EXTERNAL_REVIEW_DECISION
EXTERNAL_REVIEW_SOURCE_ID=TASK172-EXTERNAL-REVIEW-DECISION-EXTERNAL-Q-CONTRACT-R1
EXTERNAL_REVIEW_SOURCE_DESCRIPTION=External ChatGPT decision supplied in the authorized task instruction; not a GitHub review event or human expert signature.
EXTERNAL_REVIEW_SCOPE=MODEL_LEVEL_EXTERNAL_SIGNED_Q_INPUT_AUTHORITY_CONTRACT_ONLY
REVIEW_EVIDENCE_BOUND=true
GITHUB_REVIEWER_IDENTITY_CLAIMED=false
HUMAN_EXPERT_IDENTITY_CLAIMED=false
ORGANIZATION_IDENTITY_CLAIMED=false
PROFESSIONAL_SIGNATURE_CLAIMED=false
APPROVAL_IDENTITY_DISCLOSED=false
SELF_APPROVAL=false
```

The provenance chain is:

```text
external review decision supplied in task authorization
    ↓
TASK-172-v0.7-shell-wall-correction-jmu-external-q-authority-contract-r3.md
    ↓
TASK-172-shell-wall-correction-jmu-external-q-authority-contract-r3.json
    ↓
this contract-review receipt and registry r48 overlay
```

The R3 payload, evidence, and registry history remain immutable. This receipt
adds a new lifecycle overlay only.

## 3. Accepted contract scope

The external review accepts the contract as a sufficiently complete
model-level authority-candidate shape. Its required binding includes:

* physical heat-rate meaning, `HEAT_RATE` quantity, W units, and the TASK171
  hot-to-cold sign convention;
* exact case/configuration identity and hash;
* exact TASK171 topology identity and hash;
* explicit physical support, event-bounded interval, wall interface, and
  granularity;
* source or producer identity, method, evidence references, rights and
  reviewability status;
* affirmative dependency declarations for U, tube film, shell film, J_mu,
  wall conductivity, and other dependencies;
* canonical identity and lifecycle rules; and
* fail-closed rejection of caller assertions, hidden defaults, unsigned or
  magnitude-only values, unsupported whole-to-local projections, and unknown
  dependencies.

The acceptance is specifically a contract-shape acceptance. It does not
approve any value in those fields and does not make the existing TASK171
observation input a case authority.

```ini
CONTRACT_PHYSICAL_MEANING_ACCEPTED=true
CONTRACT_UNIT_AND_SIGN_ACCEPTED=true
CONTRACT_CASE_BINDING_ACCEPTED=true
CONTRACT_TOPOLOGY_BINDING_ACCEPTED=true
CONTRACT_PHYSICAL_SUPPORT_ACCEPTED=true
CONTRACT_GRANULARITY_ACCEPTED=true
CONTRACT_SOURCE_PROVENANCE_ACCEPTED=true
CONTRACT_DEPENDENCY_DECLARATION_ACCEPTED=true
CONTRACT_CANONICAL_IDENTITY_ACCEPTED=true
CONTRACT_FAIL_CLOSED_LIFECYCLE_ACCEPTED=true
WHOLE_TO_LOCAL_MAPPING_AUTHORITY_CREATED=false
```

## 4. Contract lifecycle versus Q-instance lifecycle

Only the following model-level transition is recorded:

```text
PROPOSED_EXTERNAL_Q_AUTHORITY
    ↓ external scoped contract review: PASS
REVIEWED_CONTRACT
```

The separate instance lifecycle remains:

```text
NONE
    → real case-bound external-Q receipt required
    → receipt-instance independent review
    → accepted external-Q authority instance
```

Accordingly:

```ini
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_COMPLETE=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_RESULT=PASS
EXTERNAL_Q_CONTRACT_STATUS=REVIEWED_CONTRACT
EXTERNAL_Q_INSTANCE_STATUS=NONE
EXTERNAL_Q_INSTANCE_PRESENT=false
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
EXTERNAL_Q_RECEIPT_REVIEW_ELIGIBLE=false
REAL_CASE_BOUND_EXTERNAL_Q_RECEIPT_REQUIRED=true
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
```

There is no signed heat-rate value, case, producer result, measurement
interval, energy-balance result, or external-calculation result in this
receipt. No fake instance is created to advance the lifecycle.

## 5. Required future receipt fields

A future real receipt must satisfy the reviewed contract before its own
independent review can begin. It must bind, at minimum:

```text
EXTERNAL_Q_AUTHORITY_RECEIPT_ID
SCHEMA_VERSION
SOURCE_ID
SOURCE_REVISION
SOURCE_CLASS
SOURCE_LOCATION
CASE_CONFIGURATION_ID
CASE_CONFIGURATION_HASH
CASE_REVISION
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_SUPPORT_TYPE
PHYSICAL_SUPPORT_ID
PHYSICAL_SUPPORT_INTERVAL_ID
WALL_INTERFACE_ID
SIGNED_Q_W
Q_QUANTITY_TYPE
Q_UNIT
Q_SIGN_CONVENTION
GRANULARITY
PRODUCER_OR_MEASUREMENT_METHOD
DEPENDENCY_DECLARATION
EVIDENCE_REFERENCES
RIGHTS_STATUS
LIFECYCLE_STATUS
CANONICAL_HASH
```

This task supplies none of those instance values. An instance is blocked for
missing identity, support, source, rights, dependency, or canonical binding;
for an unreviewed lifecycle; for an identity/hash mismatch; or for a hidden
default, caller assertion, unsupported interpolation, extrapolation,
out-of-domain state, or unreported dependency.

## 6. Preserved internal-Q and wall dependencies

The best available internal path remains a legacy whole-exchanger path and is
not promoted as TASK172 Q authority:

```ini
QUALIFIED_Q_AUTHORITY_DEPENDENCY_STATUS=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_ID=TASK162_Q_METHOD
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_U=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_TUBE_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_SHELL_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_JMU_DEPENDENCY=FUTURE_REBINDING_UNDETERMINED
```

The following remain unresolved and are not silently supplied by the reviewed
contract:

```ini
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_REQUIRED=true
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

No whole-exchanger Q may be divided by cell count, tube count, area, length,
or mesh resolution, repeated per cell, or used as a local wall-interface Q
without a separate reviewed mapping authority.

## 7. Parent blocker and entry state

The contract-review receipt does not resolve the shell-wall correction
authority:

```ini
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

Reviewing the generic Q contract does not bind a wall-temperature producer,
preliminary film, material, bulk-state producer, local wall-Q mapping, J_mu,
or numerical closure.

## 8. Governance and next lifecycle event

This receipt is documentation/evidence-only. It changes no engineering rule,
equation, coefficient, property, tolerance, runtime schema, dependency, or
test physics. It does not change TASK162, TASK163, TASK166, or TASK171.

```ini
TASK162_CHANGED=false
TASK163_CHANGED=false
TASK166_CHANGED=false
TASK171_SEMANTICS_CHANGED=false
EXTERNAL_Q_RECEIPT_CREATED=false
EXTERNAL_Q_RUNTIME_INJECTION_IMPLEMENTED=false
WALL_TEMPERATURE_SOLVE_EXECUTED=false
FIXED_POINT_ITERATION_PERFORMED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The next lifecycle event is deliberately not a receipt review:

```ini
NEXT_LIFECYCLE_EVENT=REAL_CASE_BOUND_EXTERNAL_Q_RECEIPT_REQUIRED
NEXT_GATE=NONE_UNTIL_REAL_EXTERNAL_Q_RECEIPT_EXISTS
```

Once a real receipt exists, a separately authorized gate may review that
instance against this reviewed contract. No such receipt review is performed
here.

## 9. Final receipt

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_CONTRACT_REVIEW_RECEIPT_R1
RESULT=REVIEWED
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=ce0f97d05817901c0cc312b3d09ffe889a306eee
FINAL_HEAD_SHA=TO_BE_RECORDED_AFTER_COMMIT
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_ID=V07-T172-EXTERNAL-SIGNED-Q-INPUT-AUTHORITY-CONTRACT-R3
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
EXTERNAL_Q_AUTHORITY_CONTRACT_CANDIDATE_CREATED=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_COMPLETE=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_RESULT=PASS
EXTERNAL_Q_CONTRACT_STATUS=REVIEWED_CONTRACT
EXTERNAL_Q_INSTANCE_STATUS=NONE
EXTERNAL_Q_INSTANCE_PRESENT=false
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
EXTERNAL_Q_RECEIPT_REVIEW_ELIGIBLE=false
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
LOCAL_VALIDATION=TO_BE_RECORDED
EXACT_FINAL_HEAD_CI_RUN=TO_BE_RECORDED
EXACT_FINAL_HEAD_CI=TO_BE_RECORDED
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_LIFECYCLE_EVENT=REAL_CASE_BOUND_EXTERNAL_Q_RECEIPT_REQUIRED
NEXT_GATE=NONE_UNTIL_REAL_EXTERNAL_Q_RECEIPT_EXISTS
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
