# TASK172 — external scoped acceptance of the material-identity input contract

## 1. Approval-record boundary

This is an append-only record of the external scoped decision supplied for
`V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1`. It records a lifecycle
promotion for the model-level Layer A input contract only. It does not select
or approve a material instance, create a material profile, qualify a
conductivity value, promote Layer B, or remove the material canonical blocker.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_IDENTITY_EXTERNAL_SCOPED_APPROVAL_RECORD_R1
PR=277
PREVIOUS_HEAD_SHA=60891ff1a989a1e5a75f45ddf8bddaf48a76ecd3
MODE=EXTERNAL_REVIEW_DECISION_RECORDING_ONLY
AUTHORITY_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_MODEL_LEVEL_LAYER_A_CONTRACT
EXTERNAL_REVIEW_SCOPE=MODEL_LEVEL_MATERIAL_IDENTITY_INPUT_CONTRACT_ONLY
LAYER_A_MODEL_CONTRACT_ACCEPTED=true
MATERIAL_IDENTITY_INPUT_CONTRACT_STATUS=REVIEWED_AUTHORITY
MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW=ACCEPTED
LIFECYCLE_PROMOTION_SCOPE=MODEL_LEVEL_CONTRACT_SHAPE_OWNERSHIP_PROVENANCE_BINDING_ONLY
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
ACTUAL_MATERIAL_CASE_ACCEPTED=false
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The external decision is recorded as a scoped acceptance of the contract
shape, ownership, source/provenance requirements, case/configuration binding,
geometry/support binding, canonical identity rules, and fail-closed lifecycle
semantics. It is not an approval of any value carried by a future material
record.

## 2. External decision provenance

The review decision is the external ChatGPT review decision supplied in the
authorized task instruction. This record does not invent a person, GitHub
reviewer, organization, professional signature, or expert credential. It is
not inferred from the PR API state and is not a replacement for a GitHub review
event.

```ini
EXTERNAL_REVIEW_SOURCE_TYPE=EXTERNAL_REVIEW_DECISION
EXTERNAL_REVIEW_SOURCE_ID=TASK172-EXTERNAL-REVIEW-DECISION-LAYER-A-R1
EXTERNAL_REVIEW_SOURCE_DESCRIPTION=External ChatGPT decision supplied in the authorized task instruction; not a GitHub review event or human expert signature.
GITHUB_REVIEWER_IDENTITY_CLAIMED=false
HUMAN_EXPERT_IDENTITY_CLAIMED=false
ORGANIZATION_IDENTITY_CLAIMED=false
APPROVAL_IDENTITY_DISCLOSED=false
SELF_APPROVAL=false
REVIEW_EVIDENCE_BOUND=true
```

The evidence chain is:

```text
external scoped decision
    ↓
TASK-172-v0.7-material-identity-input-contract-independent-review-r1.md
    ↓
TASK-172-material-identity-input-contract-independent-review-r1.json
    ↓
this approval receipt and registry r15 overlay
```

The prior Layer A proposal and the independent-scope audit receipt remain
immutable. The registry overlay records the new lifecycle state without
rewriting either historical payload or hash.

## 3. Exact promotion scope

Only this state transition is authorized:

```text
V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
    PROPOSED_AUTHORITY / PENDING
        ↓ scoped external acceptance
    REVIEWED_AUTHORITY / ACCEPTED
```

The promotion means that the generic model-level input boundary is accepted as
the required shape for future case-bound records. It covers:

* `TASK172_CASE_INPUT_AUTHORITY_BOUNDARY` ownership;
* exact `TUBE_WALL_METAL` component scope;
* material identity disambiguation fields;
* source identity, revision, exact location, source class, permission status
  and evidence references;
* explicit case/configuration and geometry/physical-support bindings;
* shared canonical identity and lifecycle rules;
* caller transport not being approval; and
* fail-closed rejection of defaults, assertions, name-only bindings and
  incomplete provenance.

It does not authorize any particular value for those fields. A future record
must still be independently reviewed and case-bound before it can satisfy a
production admission gate.

## 4. Explicit non-promotion boundaries

The following are deliberately not changed by this record:

| Boundary | State | Meaning |
| --- | --- | --- |
| Actual material identity | `false` | No grade, alloy, standard/condition or product form is selected. |
| Material profile | `NONE` | No case-level material profile exists. |
| Actual material case | `false` | No material instance is accepted for a production case. |
| Layer B authority | `PROPOSED_AUTHORITY` / `PENDING` | Thermal-property contract remains independently unresolved. |
| Layer C authority | `REVIEWED_AUTHORITY` / `ACCEPTED` | Existing model-level constant-k contract remains unchanged. |
| Constant-k status | `OPEN` | No material-specific `k` or `k(T)` is bound. |
| Material-k temperature domain | `false` | No property domain is approved. |
| Production admission | `FAIL_CLOSED` | Layer A contract acceptance alone cannot admit production. |

In particular, this record does not make the following fields valid:

```text
thermal_conductivity_w_m_k
constant_k
k_at_temperature
wall_temperature
tube_wall_resistance
correction_factor
HTC
U
fouling
```

Those remain outside Layer A and are not silently inferred from an accepted
identity-input contract.

## 5. Layer B and Layer C separation

Layer B remains the separate material thermal-property contract:

```ini
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=PENDING
```

Layer C remains the already accepted model-level qualification contract:

```ini
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=REVIEWED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=ACCEPTED
```

Layer C acceptance does not bind an actual material, and Layer A acceptance
does not promote Layer B. The lifecycle order remains:

```text
accepted Layer A identity-input contract
    → separately reviewed Layer B property authority
    → case-bound material identity and property record
    → Layer C qualification applied to that approved case
```

No part of this receipt changes the Layer C contract, its scope, its evidence,
or its existing external decision record.

## 6. Canonical blocker and entry state

The canonical material blocker remains active because there is still no actual
material identity/property instance and no material-specific temperature
domain:

```ini
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
```

The six canonical TASK172 entry blockers remain exactly:

```ini
MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN
TUBE-WALL-CORRECTION-AUTHORITY
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=6
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

Promoting the model-level identity-input contract does not make a material
profile available and does not satisfy the material constant-k temperature
domain blocker.

## 7. Governance

This receipt is documentation/evidence-only. No engineering rule, empirical
formula, coefficient, property value, tolerance, runtime behavior, dependency
or test physics is changed.

```ini
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TUBE_WALL_CORRECTION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
MATERIAL_PROFILE_CREATED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The next separately authorized gate is only:

```ini
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW_R1_ONLY
```

That gate must not be interpreted as automatic implementation authorization.
