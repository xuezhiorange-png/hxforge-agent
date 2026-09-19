# TASK172 — external scoped acceptance of the material thermal-property contract

## 1. Approval-record boundary

This document records the external scoped decision for the model-level Layer B
material thermal-property authority contract proposed in
[`TASK-172-v0.7-material-thermal-property-authority-construction-r1.md`](TASK-172-v0.7-material-thermal-property-authority-construction-r1.md)
and audited in the [independent-scope review](TASK-172-v0.7-material-thermal-property-contract-independent-review-r1.md).
It records only the authorized lifecycle promotion of the generic contract
shape. It does not select a material, bind a property value or curve, create a
profile, qualify constant `k`, or enable production admission.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_THERMAL_PROPERTY_EXTERNAL_SCOPED_APPROVAL_RECORD_R1
PR=277
PREVIOUS_HEAD_SHA=783721fe755a6598166602e1bd9314f184d17f25
MODE=EXTERNAL_REVIEW_DECISION_RECORDING_ONLY
AUTHORITY_ID=V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_MODEL_LEVEL_LAYER_B_CONTRACT
EXTERNAL_REVIEW_SCOPE=MODEL_LEVEL_MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONTRACT_ONLY
LAYER_B_MODEL_CONTRACT_ACCEPTED=true
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=REVIEWED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=ACCEPTED
LIFECYCLE_PROMOTION_SCOPE=MODEL_LEVEL_CONTRACT_SHAPE_AND_FAIL_CLOSED_BOUNDARY_ONLY
MATERIAL_PROPERTY_BODY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
ACTUAL_MATERIAL_CASE_ACCEPTED=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The external decision accepts the generic Layer B contract for source-bound
solid thermal-conductivity records. It does not approve an actual property
record or any value carried by a future record.

## 2. External decision provenance

The decision source is the external ChatGPT review decision supplied in the
authorized task instruction. This repository record does not invent a person,
GitHub reviewer, organization, professional signature, or expert credential.
It is not inferred from the PR API state and is not a substitute for a GitHub
review event.

```ini
EXTERNAL_REVIEW_SOURCE_TYPE=EXTERNAL_REVIEW_DECISION
EXTERNAL_REVIEW_SOURCE_ID=TASK172-EXTERNAL-REVIEW-DECISION-LAYER-B-R1
EXTERNAL_REVIEW_SOURCE_DESCRIPTION=External ChatGPT decision supplied in the authorized task instruction; not a GitHub review event or human expert signature.
GITHUB_REVIEWER_IDENTITY_CLAIMED=false
HUMAN_EXPERT_IDENTITY_CLAIMED=false
ORGANIZATION_IDENTITY_CLAIMED=false
PROFESSIONAL_SIGNATURE_CLAIMED=false
APPROVAL_IDENTITY_DISCLOSED=false
REVIEW_EVIDENCE_BOUND=true
SELF_APPROVAL=false
```

The evidence chain is:

```text
external scoped Layer B decision
    ↓
TASK-172-v0.7-material-thermal-property-contract-independent-review-r1.md
    ↓
TASK-172-material-thermal-property-contract-independent-review-r1.json
    ↓
this approval receipt and registry r17 overlay
```

## 3. Exact promotion scope

Only this state transition is authorized:

```text
V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1
    PROPOSED_AUTHORITY / PENDING
        ↓ external scoped acceptance
    REVIEWED_AUTHORITY / ACCEPTED
```

The accepted model-level contract covers:

* exact quantity `SOLID_THERMAL_CONDUCTIVITY`;
* exact component scope `TUBE_WALL_METAL`;
* exact Layer A material-identity authority ID and hash binding;
* a complete property body rather than ID/hash-only transport;
* the mutually exclusive `FIXED_SOURCE_VALUE` and `SOURCE_BOUND_K_OF_T`
  representations;
* source provenance, rights and evidence requirements;
* case/configuration, geometry and physical-support bindings;
* source-bound interpolation, forbidden extrapolation and blocked
  out-of-domain behavior;
* canonical identity and rebinding rules; and
* independent-review and production fail-closed lifecycle rules.

This is contract-shape and ownership acceptance only. It does not make a
future record valid without its complete source-bound body and exact bindings.

## 4. Explicit non-promotion boundaries

The following are deliberately not changed by this approval record:

| Boundary | State | Meaning |
| --- | --- | --- |
| Actual material identity | `false` | No grade, alloy, standard, condition or product form is selected for a case. |
| Thermal-property body | `false` | No fixed conductivity value or `k(T)` curve/table is introduced or approved. |
| Material profile | `NONE` | No case-level material/property profile exists. |
| Actual material case | `false` | No production case is accepted. |
| Material-specific temperature domain | `false` | No case-level property domain is bound. |
| Layer A identity contract | `REVIEWED_AUTHORITY` / `ACCEPTED` | Existing accepted model-level identity boundary remains unchanged. |
| Layer C constant-k contract | `REVIEWED_AUTHORITY` / `ACCEPTED` | Existing accepted model-level qualification boundary remains unchanged. |
| Production admission | `FAIL_CLOSED` | A reviewed contract without an actual case-bound record cannot enter production. |

This record therefore does not make any of the following an approved instance:

```text
material grade or alloy
thermal_conductivity_w_m_k
constant_k
k_of_T curve/table
material-specific temperature domain
wall temperature
wall resistance
HTC or U
correction factor
fouling
```

## 5. Layer state after this scoped acceptance

All three model-level contracts may now have reviewed lifecycle state while
the case-level material/property authority remains absent:

| Layer | Effective state | Scope |
| --- | --- | --- |
| Layer A — material identity input | `REVIEWED_AUTHORITY` / `ACCEPTED` | Identity-input shape, ownership, provenance and bindings only. |
| Layer B — material thermal property | `REVIEWED_AUTHORITY` / `ACCEPTED` | Generic source-bound property-contract shape only; no value or instance. |
| Layer C — constant-k qualification | `REVIEWED_AUTHORITY` / `ACCEPTED` | Existing model-level qualification contract only; no actual material case. |

The separation remains:

```text
accepted Layer A identity contract
    → accepted Layer B property-contract shape
    → actual case-bound material identity + property body (absent)
    → separately applied Layer C qualification (not executable here)
```

No part of this record creates the missing case-bound material/property
instance.

## 6. Canonical blocker and entry state

The material canonical blocker remains active. Model-level approval of the
Layer B contract does not answer whether a case-less repository may close the
blocker; that question is intentionally delegated to the next adjudication
gate.

```ini
MATERIAL_PROPERTY_BODY_ACTUAL_VALUE_BOUND=false
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
ACTUAL_MATERIAL_CASE_ACCEPTED=false
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
```

The next gate is only:

```ini
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_CANONICAL_BLOCKER_CLOSURE_ADJUDICATION_R1_ONLY
```

That adjudication must separately determine whether the
`MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN` label is a model-level entry blocker
that can close after all three model-level contracts are accepted, or whether
it must remain active until an actual case-bound identity/property/qualification
instance exists. If model-level closure is allowed, the adjudication must name
the separate fail-closed gate for missing case-level material/property
authority. This approval record makes none of those decisions.

## 7. Governance

This is an external review decision record plus machine evidence and an
append-only registry overlay. It introduces no equation, coefficient, property
value, temperature domain, tolerance, solver behavior, production permission,
dependency or implementation.

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

The prior Layer B proposal, Layer B independent-scope audit, Layer A accepted
record and Layer C accepted record remain immutable. This record changes only
the subject Layer B model-contract lifecycle state authorized above.
