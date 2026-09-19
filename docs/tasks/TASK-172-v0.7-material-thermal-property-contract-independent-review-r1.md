# TASK172 — scoped independent audit of the material thermal-property contract

## 1. Audit boundary

This document is an append-only independent-scope audit of the Layer B
material thermal-property contract proposed in
[`TASK-172-v0.7-material-thermal-property-authority-construction-r1.md`](TASK-172-v0.7-material-thermal-property-authority-construction-r1.md).
It does not rewrite that proposal, select a material, select a conductivity
value or curve, create a profile, promote the subject authority, or remove the
material canonical blocker.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW_R1
PR=277
PREVIOUS_HEAD_SHA=30ad92dfd3df9d8adb5984c4a9dd35da7df86ee6
MODE=INDEPENDENT_SCOPE_AUDIT_ONLY
SUBJECT_AUTHORITY_ID=V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_MODEL_LEVEL_LAYER_B_CONTRACT
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONTRACT_ONLY
REVIEW_EVIDENCE_BOUND=true
LIFECYCLE_PROMOTION_PERFORMED=false
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```
The answer to the authorized question is **YES**, but only at the model-level
contract scope: the proposed Layer B shape is sufficiently explicit to be
independently accepted or rejected while Layer A remains the upstream accepted
identity boundary, Layer C remains unchanged, no actual material or property
instance is selected, and production admission remains fail-closed. This is a
positive scope recommendation, not a lifecycle promotion. The subject remains
`PROPOSED_AUTHORITY` / independent review `PENDING` until a separate external
review decision is recorded.

## 2. Audited artifacts and lifecycle chain

The audit reads the subject proposal and its machine evidence together with the
append-only registry history:

* the [Layer B contract proposal](TASK-172-v0.7-material-thermal-property-authority-construction-r1.md);
* its [machine-readable evidence](evidence/TASK-172-material-thermal-property-authority-construction-r1.json);
* the accepted [Layer A external scoped record](TASK-172-v0.7-material-identity-external-scoped-approval-record-r1.md);
* the [Layer A evidence](evidence/TASK-172-material-identity-external-scoped-approval-record-r1.json); and
* the [append-only authority registry](TASK-172-v0.7-authority-registry-r1.json).

The relevant lifecycle remains:

```text
Layer A material identity input contract
    REVIEWED_AUTHORITY / ACCEPTED
        ↓ exact ID + hash binding
Layer B material thermal-property authority contract
    PROPOSED_AUTHORITY / PENDING
        ↓ separate external scoped acceptance required
case-bound property body and source-qualified instance
        ↓ separate Layer C qualification
constant-k case admission, if independently qualified
```

The accepted Layer A record does not approve a material value. The accepted
Layer C record does not promote Layer B and does not create a property value.

## 3. Scoped review result

`PASS` below means that the proposed contract contains the required model-level
boundary and fail-closed rule. It does not mean that any future property record
has passed validation.

| Check | Result | Audited contract evidence |
| --- | --- | --- |
| `B01_QUANTITY_AND_COMPONENT` | `PASS` | Quantity is exact `SOLID_THERMAL_CONDUCTIVITY`; component scope is exact `TUBE_WALL_METAL`. Fluid properties, HTC, `U`, fouling and wall temperature are outside the subject. |
| `B02_LAYER_A_EXACT_BINDING` | `PASS` | A future property record must carry the exact Layer A authority ID and matching hash; an ID-only or mismatched pair blocks. |
| `B03_IDENTITY_PROPERTY_SEPARATION` | `PASS` | Material identity fields and the thermal-property body are distinct; identity cannot infer conductivity. |
| `B04_PROPERTY_BODY_REQUIRED` | `PASS` | A complete `k_value_or_k_curve` body is required even when authority IDs and hashes are present. |
| `B05_ALLOWED_MODELS` | `PASS` | Only `FIXED_SOURCE_VALUE` and `SOURCE_BOUND_K_OF_T` are admitted by the proposed contract. |
| `B06_MODEL_EXCLUSIVITY` | `PASS` | The fixed value and curve alternatives are mutually exclusive competing representations within one authority record. |
| `B07_FIXED_VALUE_FIELDS` | `PASS` | Fixed values require a source-declared value, units, temperature basis, source-qualified temperature domain and provenance. |
| `B08_CURVE_FIELDS` | `PASS` | Curves/tables require complete points, point units, independent-variable basis, source-qualified domain, ordering and a source-defined interpolation rule when one exists. |
| `B09_NAME_DERIVATION` | `PASS` | Material name or grade cannot generate a thermal property. |
| `B10_RUNTIME_DATABASE` | `PASS` | Runtime material-database lookup is not an engineering authority or an allowed completion path. |
| `B11_HIDDEN_DEFAULT` | `PASS` | Hidden/default `k` and default material selection are explicitly forbidden. |
| `B12_LEGACY_REUSE` | `PASS` | Legacy `tube_thermal_conductivity` reuse is explicitly forbidden as a material authority. |
| `B13_SOURCE_PROVENANCE` | `PASS` | Source ID, revision, location, class, permission status and evidence references are required. |
| `B14_CASE_GEOMETRY_BINDING` | `PASS` | Case/configuration, geometry, component and physical-support identities and hashes are required. |
| `B15_BODY_HASH_INTEGRITY` | `PASS` | Missing or mismatched body/hash, including the same supplied hash over a different body, is fail-closed. |
| `B16_IDENTITY_HASH_INTEGRITY` | `PASS` | Layer A identity ID/hash mismatch is a cross-binding failure. |
| `B17_SOURCE_REVISION_INTEGRITY` | `PASS` | Source revision is identity-bearing; a changed or unbound revision cannot validate against the prior authority. |
| `B18_COMPONENT_GEOMETRY_INTEGRITY` | `PASS` | Component or support mismatch cannot be satisfied by a similar name; exact bindings are required. |
| `B19_INTERPOLATION_SOURCE_BOUND` | `PASS` | Interpolation is consumed only when an explicit source rule is carried. |
| `B20_NO_ENGINE_INTERPOLATION` | `PASS` | If the source gives no interpolation rule, the engine may not choose one silently. |
| `B21_EXTRAPOLATION` | `PASS` | Extrapolation is forbidden. |
| `B22_OUT_OF_DOMAIN` | `PASS` | Out-of-domain evaluation is `BLOCKED`, not clamped or silently extended. |
| `B23_TEMPERATURE_BASIS_DOMAIN` | `PASS` | Temperature basis and domain are source-defined; the engine may not infer them. |
| `B24_CONSTANT_K_SEPARATION` | `PASS` | Layer B does not decide whether a property may be treated as constant. |
| `B25_K_OF_T_TO_CONSTANT` | `PASS` | Converting `SOURCE_BOUND_K_OF_T` to a constant is a separate Layer C qualification decision, not automatic Layer B behavior. |
| `B26_APPROXIMATION_TOLERANCE` | `PASS` | No approximation-error tolerance is introduced by this contract. |
| `B27_NUMERICAL_TOLERANCE` | `PASS` | No solver, iteration or numerical tolerance is introduced. |
| `B28_WALL_SOLVER` | `PASS` | No wall-temperature solver is introduced; a located wall state remains a downstream dependency. |
| `B29_WALL_CORRECTION` | `PASS` | No viscosity, Prandtl or wall correction is introduced. |
| `B30_ACTUAL_INSTANCE` | `PASS` | No actual material, value, curve, profile or case instance is created. |
| `B31_PROPOSED_ADMISSION` | `PASS` | `PROPOSED_AUTHORITY` cannot enter a production Rating/Sizing gate. |
| `B32_INDEPENDENT_REVIEW` | `PASS` | Independent review is required before the subject may become reviewed authority for a future admission boundary. |
| `B33_FUTURE_CASE_BINDING` | `PASS` | A future case-level property record must remain source-bound, case-bound, geometry-bound and independently reviewed. |
| `B34_CANONICAL_PREIMAGE` | `PASS` | Schema/version, Layer A ID/hash, body, quantity/component, bindings, source/rights, domain/policies and lifecycle are in the canonical preimage. |
| `B35_REBINDING_IDENTITY` | `PASS` | Source revision, body/domain, case or geometry changes require a new canonical identity. |
| `B36_CALLER_ASSERTION` | `PASS` | Caller transport, caller status and copied hashes cannot self-approve the record. |
| `B37_ID_HASH_ONLY` | `PASS` | ID/hash-only admission without a property body is explicitly rejected. |
| `B38_LIBRARY_CAPABILITY` | `PASS` | Library/backend availability is not engineering permission or source authority. |
| `B39_ACCEPTED_LAYERS_UNCHANGED` | `PASS` | Layer A remains accepted as an identity-input contract and Layer C remains accepted as the model-level constant-k qualification contract; neither is rewritten. |
| `B40_BLOCKER_PRESERVATION` | `PASS` | The material canonical blocker remains active; this audit does not remove it. |

The proposal therefore passes the requested **model-level Layer B contract
shape** audit without passing any material or property instance.

## 4. Property model boundary

The contract admits two representations, but neither is selected here:

| Model | Required body | Required source rule | Disallowed behavior |
| --- | --- | --- | --- |
| `FIXED_SOURCE_VALUE` | Source-declared conductivity value, units, temperature basis and source-qualified domain | Source provenance and its value/domain interpretation | Turning a material name, single unqualified point or library default into a value |
| `SOURCE_BOUND_K_OF_T` | Complete source curve/table, point units, independent-variable basis, domain, ordering and source-defined interpolation if present | Source-qualified representation and explicit interpolation semantics | Filling missing points, choosing an interpolation rule, or extrapolating |

One authority instance cannot carry both alternatives as competing values. A
source that does not define interpolation cannot be made continuous by a
project default. An out-of-domain state is blocked. No value, curve, material
grade or profile is present in this audit.

## 5. Binding and canonical identity

The future property record is valid only when all of these exact relationships
are available:

```text
property authority
  → exact Layer A material-identity authority ID + hash
  → exact TASK172 case/configuration ID + hash
  → exact TUBE_WALL_METAL geometry/support ID + hash
  → exact source ID + revision + location + rights + evidence
  → complete fixed-value or k(T) property body
```

The proposal correctly reuses
`hexagent.canonical_json.canonical_sha256`. Its preimage includes the schema
and authority versions, property quantity and component, property body, Layer
A pair, case/configuration binding, geometry/support binding, source/provenance,
domain and interpolation/extrapolation/out-of-domain policies, and lifecycle
status. The authority hash is excluded from its own preimage under the existing
shared canonical rule.

Consequently, each of the following requires a new identity and cannot be
silently rebound:

* property body or representation model;
* source revision, location, rights or evidence;
* temperature basis or source-qualified domain;
* Layer A identity pair;
* case/configuration binding;
* component, geometry or physical support; and
* lifecycle/approval state.

The audit found no ID/hash-only admission path, no caller-assertion promotion
path and no library-availability-as-authority path in the proposed contract.

## 6. Layer separation and effective state

The scope conclusion is deliberately narrower than a property qualification:

| State | Required effective value | Meaning |
| --- | --- | --- |
| Layer A identity-input contract | `REVIEWED_AUTHORITY` / `ACCEPTED` | Upstream identity-input shape and ownership are accepted. |
| Layer B thermal-property contract | `PROPOSED_AUTHORITY` / `PENDING` | This audit recommends scoped acceptance; it does not promote the subject. |
| Layer C constant-k qualification | `REVIEWED_AUTHORITY` / `ACCEPTED` | Existing model-level qualification contract remains unchanged. |
| Actual material identity | `false` | No grade/alloy/condition/product form is selected for a case. |
| Material property body/value | `false` | No `k` value or `k(T)` dataset is approved or bound. |
| Material profile | `NONE` | No case-level material/property profile exists. |
| Actual material case | `false` | No production case is accepted. |
| Material constant-k status | `OPEN` | The canonical blocker remains active. |
| Material-k temperature domain | `false` | No material-specific domain is approved. |
| Production admission | `FAIL_CLOSED` | A proposal or incomplete case record cannot enter production. |

The six canonical entry blockers remain exactly:

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

## 7. Review recommendation and non-scope

This receipt recommends:

```ini
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_MODEL_LEVEL_LAYER_B_CONTRACT
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=PENDING
LIFECYCLE_PROMOTION_PERFORMED=false
```

The following remain outside this audit and are not changed:

```text
actual material selection                 = NOT PERFORMED
thermal-property value/curve selection    = NOT PERFORMED
constant-k case qualification             = NOT PERFORMED
tube wall correction                      = NOT PERFORMED
shell wall correction                     = NOT PERFORMED
wall-temperature solver                   = NOT PERFORMED
numerical method/error budget/mesh        = NOT PERFORMED
production code/dependencies              = NOT CHANGED
```

No source value, material profile, conductivity curve, tolerance, empirical
coefficient, solver behavior or production permission is invented here.

The next gate is only:

```ini
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_MODEL_LEVEL_LAYER_B_ACCEPTANCE
```

That next gate is a separate lifecycle decision. It is not an authorization to
select a material, create a property instance, qualify constant `k`, start
TASK172 implementation, or work on wall corrections/numerics.

## 8. Governance and evidence

The machine-readable [audit evidence](evidence/TASK-172-material-thermal-property-contract-independent-review-r1.json)
binds this document and the audited proposal/evidence by immutable hashes. The
registry update is an append-only overlay; all prior proposal, Layer A and
Layer C payloads remain historical records.

```ini
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
LAYER_B_LIFECYCLE_PROMOTION_PERFORMED=false
MATERIAL_PROFILE_CREATED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```
