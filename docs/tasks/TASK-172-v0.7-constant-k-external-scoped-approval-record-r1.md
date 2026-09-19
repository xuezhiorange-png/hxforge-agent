# TASK172 — external scoped approval record for the constant-k model contract R1

This append-only receipt records the external review decision supplied in the
authorized task instruction. It promotes only the model-level Layer C
constant-k qualification contract. It does not approve a material, a
conductivity value, a temperature domain, a material case, or production
admission.

The preceding proposal, governance correction, and internal independent-review
receipt remain immutable. This receipt is an effective lifecycle overlay, not
a rewrite of those records.

```ini
TASK_ID=TASK172_V0_7_CONSTANT_K_EXTERNAL_SCOPED_APPROVAL_RECORD_R1
PR_NUMBER=277
PREVIOUS_HEAD_SHA=b17d2f7d7f94bd73c1165611d37510cfed91d21b
MODE=EXTERNAL_REVIEW_DECISION_RECORDING_ONLY
AUTHORITY_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_MODEL_LEVEL_LAYER_C_CONTRACT
REVIEW_SCOPE=MODEL_LEVEL_CONSTANT_K_QUALIFICATION_CONTRACT_ONLY
EXTERNAL_REVIEW_EVIDENCE_BOUND=true
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 1. External review source boundary

The decision source is the external ChatGPT review decision supplied by the
task coordinator in the authorized task instruction. It is recorded as an
external review decision, not as a GitHub review event and not as a named human
expert signature. No reviewer person, organization, professional expertise,
or GitHub approval identity is inferred or fabricated.

```ini
EXTERNAL_REVIEW_SOURCE_TYPE=EXTERNAL_REVIEW_DECISION
EXTERNAL_REVIEW_SOURCE_ID=TASK172-EXTERNAL-REVIEW-DECISION-R1
EXTERNAL_REVIEW_SOURCE_DESCRIPTION=External ChatGPT review decision supplied in the authorized task instruction; not a GitHub review event or human expert signature.
GITHUB_REVIEWER_IDENTITY_CLAIMED=false
HUMAN_EXPERT_IDENTITY_CLAIMED=false
APPROVAL_EVIDENCE_BOUND=true
```

The machine companion
[`evidence/TASK-172-constant-k-external-scoped-approval-record-r1.json`](evidence/TASK-172-constant-k-external-scoped-approval-record-r1.json)
binds the decision to the preceding authority records, their immutable
identities, and this receipt. The registry records the companion's file hash
and canonical hash.

## 2. Exact scoped decision

The external decision is accepted exactly as supplied:

```ini
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_MODEL_LEVEL_LAYER_C_CONTRACT
REVIEW_SCOPE=MODEL_LEVEL_CONSTANT_K_QUALIFICATION_CONTRACT_ONLY
LAYER_C_MODEL_CONTRACT_ACCEPTED=true
```

The only lifecycle promotion made by this overlay is:

```ini
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=REVIEWED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=ACCEPTED
```

This means the Layer C contract may be used as a reviewed model-level
qualification contract in its stated scope. It does not create or qualify a
case-level material record.

## 3. Scope preserved and explicitly not promoted

The approved scope remains the existing Layer C contract:

```text
component = TUBE_WALL_METAL
quantity = SOLID_THERMAL_CONDUCTIVITY
mode = CASE_LEVEL_AUTHORITY_REQUIRED
admitted constant representation = FIXED_SOURCE_VALUE_WITH_EXPLICIT_SOURCE_DECLARED_DOMAIN
SOURCE_BOUND_K_OF_T → constant conversion = NOT_ADMITTED
required wall states = TUBE_METAL_INNER_SURFACE, TUBE_METAL_OUTER_SURFACE
wall profile = CLEAN_SURFACE_ONLY
```

The following boundaries remain unchanged:

```ini
FOULED_WALL_PROFILE_APPROVED=false
VARIABLE_K_WALL_APPROVED=false
U_TUBE_ADMITTED=false
FLOATING_HEAD_ADMITTED=false
ADDITIONAL_PASSES_ADMITTED=false
ACTIVE_WALL_CORRECTIONS_CLOSED=false
NUMERICAL_AUTHORITY_INTRODUCED=false
PRODUCTION_ADMISSION_ENABLED=false
```

Layer A and Layer B are deliberately not promoted:

```ini
MATERIAL_IDENTITY_INPUT_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW=PENDING
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=PENDING
```

No material identity, property body, conductivity value, or temperature domain
is supplied by this receipt:

```ini
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
ACTUAL_MATERIAL_CASE_ACCEPTED=false
```

## 4. Why the material blocker remains active

The exact governance reason is:

```text
Layer C model-level constant-k qualification contract is independently accepted,
but the material canonical blocker remains active because the Layer A material
identity input contract and Layer B material thermal-property contract remain
PROPOSED_AUTHORITY / independent-review PENDING.

Layer C approval does not imply Layer A/B approval and does not approve an
actual material, conductivity value, temperature domain, or production case.
```

Accordingly, the effective material state remains fail-closed:

```ini
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
```

The six canonical TASK172 entry blockers remain exactly unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN,TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=6
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

## 5. Provenance and lifecycle integrity

This overlay binds the accepted subject authority to the historical R1
proposal, the R11 governance correction, and the R12 internal review receipt.
Those records are not rewritten. The overlay is the current lifecycle source
for Layer C only; the effective material state continues to be governed by the
unpromoted Layer A/B records and the six-blocker ledger.

```ini
HISTORICAL_RECORDS_REWRITTEN=false
PROVENANCE_ACYCLIC=true
CALLER_ASSERTION_PROMOTED=false
ACTUAL_MATERIAL_SOURCE_SELECTED=false
PRODUCTION_CASE_CREATED=false
GOLDEN_APPROVED=false
```

The authority uses the shared
`hexagent.canonical_json.canonical_sha256` serializer. The new evidence and
registry overlay hashes are identities of this receipt and its bindings; they
do not alter any historical authority hash.

## 6. Governance and next gate

This is a documentation/evidence-only state transition. No engineering rule,
equation, tolerance, dependency, runtime, or implementation state changes.

```ini
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The next gate is intentionally limited to an independent review of the Layer
A material-identity input contract. It does not authorize Layer B review,
constant-k case qualification, active wall-correction research, numerical
closure, implementation, Ready, or Merge.

## 7. Receipt

```ini
RESULT=PASS_SCOPED_EXTERNAL_REVIEW_RECORDED_WITH_MATERIAL_BLOCKER_RETAINED
AUTHORITY_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=REVIEWED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=ACCEPTED
MATERIAL_IDENTITY_INPUT_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW=PENDING
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=PENDING
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
ACTUAL_MATERIAL_CASE_ACCEPTED=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=6
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
