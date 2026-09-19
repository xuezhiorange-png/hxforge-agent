# TASK172 R1 — material identity authority input contract

## 1. Receipt and immutable boundary

This is a documentation-only authority-contract definition for Draft PR277.
It defines how a future generic TASK172 property/wall evaluation receives a
solid tube-wall material identity. It does **not** select a material, qualify a
conductivity value, define a wall-temperature state, transfer a wall
correction, implement a resolver, or start TASK172 production implementation.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_IDENTITY_AUTHORITY_INPUT_CONTRACT_R1
PR=277
PREVIOUS_HEAD_SHA=86871ca25a02b7d70e2a657f6b649f4d43bc9737
MODE=CONTROLLED_AUTHORITY_CONTRACT_DEFINITION_ONLY
DOCUMENT_STATUS=PROPOSED_AUTHORITY
AUTHORITY_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
AUTHORITY_VERSION=r1
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The contract is a new append-only overlay. It does not modify the historical
R1–R6 proposals or their hashes in the
[TASK172 authority registry](TASK-172-v0.7-authority-registry-r1.json). The
previous targeted audit remains the lineage for the missing input:
[targeted physical-source authority construction](TASK-172-v0.7-targeted-physical-source-authority-construction-r1.md).

The distinction used throughout this receipt is:

* **contract definition** — the generic input boundary and acceptance rules
  proposed here;
* **authority instance** — a case-bound material record carrying a real
  identity, source and independent approval;
* **thermal-property authority** — a later record that may qualify `k` or
  `k(T)` for the approved material identity.

Closing the first item does not create either of the latter two.

## 2. Ownership decision

The ownership review considered the four available choices.

| Option | Decision | Evidence and consequence |
| --- | --- | --- |
| A — TASK172 caller-supplied `MaterialIdentityAuthority` | **ADOPTED** | TASK172 is a generic computation boundary; its future case request must carry an explicit, source-bound material identity record. Caller transport is not caller self-approval. |
| B — existing frozen upstream configuration owns material identity | **NOT_FOUND** | TASK020–023 geometry/configuration contracts do not currently own a TASK172 tube-alloy/material-grade identity. TASK037 has typed carriers, but no complete TASK172 material-instance authority. |
| C — amend TASK020/TASK021/TASK025 | **NOT_REQUIRED** | The missing input can be added at the TASK172 boundary without changing TASK025's frozen hydraulic read set or TASK020–023 geometry semantics. |
| D — hidden/default material | **FORBIDDEN** | No grade, alloy, conductivity, fixture material or library default may be inserted by the engine. |

```ini
MATERIAL_IDENTITY_OWNER=TASK172_CASE_INPUT_AUTHORITY_BOUNDARY
MATERIAL_IDENTITY_OWNERSHIP_DECISION=OPTION_A_ADOPTED;TASK172_GENERIC_ENGINE_REQUIRES_CALLER_SUPPLIED_EXPLICIT_SOURCE_BOUND_MATERIAL_IDENTITY;NO_EXISTING_UPSTREAM_TASK020_023_OWNER_FOUND;TASK020_TASK021_TASK025_CONTRACTS_UNCHANGED
UPSTREAM_CONTRACT_AMENDMENT_REQUIRED=false
HIDDEN_DEFAULT_MATERIAL_FORBIDDEN=true
```

The word *caller-supplied* describes transport and ownership only. A record
may enter a future production gate only after its source, rights, case binding,
geometry binding, canonical hash and independent review status pass the
contract below. A caller-provided assertion, material name, or hash copied
from an unreviewed record is insufficient.

## 3. Component scope and identity schema

The component token is inherited from the reviewed TASK037 wall semantics and
the R5 physical-authority audit. The current contract covers the metal wall of
the heat-transfer tube represented by the cylindrical wall-resistance object.
It does not create a second shell-wall material object: the shell-side fluid
film meets the tube outer surface in the currently admitted clean-wall network.

```ini
COMPONENT_ROLE=TUBE_WALL_METAL
COMPONENT_SCOPE=TASK037_CYLINDRICAL_TUBE_WALL_RESISTANCE_AND_TASK171_TUBE_METAL_WALL_INTERFACE
SHELL_WALL_MATERIAL_IDENTITY_CONTRACT_CREATED=false
```

Each future authority instance must contain exactly one value for each required
semantic field below. Conditional fields may be absent only when the source
explicitly establishes non-applicability and the record carries that
justification; the contract does not allow silent nulls.

| Field | Required meaning | Identity/provenance rule |
| --- | --- | --- |
| `schema_version` | Contract schema version, currently `task172.material-identity.v1` | Changes to schema are identity-affecting. |
| `authority_id` | Stable authority-record identity | Must be the record's own authority identity, not a material name. |
| `authority_version` | Version of this material record | Revision changes require a new canonical record. |
| `component_role` | Physical component role | Must equal `TUBE_WALL_METAL` for this contract. |
| `material_identity_id` | Stable material identity within the cited source system | Must not be a bare grade string or global default. |
| `material_standard_system` | Standard/specification system when one exists | Binds the interpretation of designation and grade. |
| `material_specification_or_designation` | Source designation/specification | Must be source-backed and unambiguous. |
| `material_grade_or_alloy` | Grade/alloy identity | No conventional grade may be inferred. |
| `material_condition_or_temper_if_applicable` | Condition/temper where identity depends on it | Non-applicability requires source evidence. |
| `product_form_if_material_identity_requires_it` | Tube/product form where it affects identity | Must remain tied to the cited authority. |
| `source_id` | Immutable source identity | Must resolve to a source record with rights/access metadata. |
| `source_version_or_revision` | Source revision/edition/date or immutable repository revision | Revision changes cannot be hidden behind the same instance hash. |
| `source_location` | Exact table, clause, file, page or stable URL | A bibliography-only citation is not sufficient for a future instance. |
| `source_class` | Authority class and role | Must distinguish primary/official/repository evidence. |
| `permission_status` | Rights/access/redistribution status | No license assumption is permitted. |
| `evidence_refs` | Reviewable evidence references | Must identify the evidence used for this exact identity. |
| `approval_status` | Lifecycle status | `PROPOSED_AUTHORITY` cannot enter production; independent review is required for `REVIEWED_AUTHORITY`. |
| `case_or_configuration_binding` | Exact case/request/configuration binding | See Section 5. |
| `geometry_binding` | Exact component/support geometry binding | See Section 5. |
| `authority_hash` | Canonical SHA-256 identity of the record payload | Computed with shared `hexagent.canonical_json`; the hash field is excluded from its own preimage. |

The contract does not require unrelated manufacturing data. It does require
whatever standard, condition or product-form information is necessary to make
the cited material identity unambiguous for the tube-wall component.

## 4. Explicit exclusions: identity is not thermal property

The following are not fields of `MaterialIdentityAuthority` and must be
rejected if supplied as an attempt to complete this contract:

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

The intended future authority chain is:

```text
MaterialIdentityAuthority
        ↓
MaterialThermalPropertyAuthority
        ↓
constant-k or k(T) qualification
        ↓
wall-temperature / active-correction consumers
```

This contract does not assert that the chain is currently complete. In
particular, it does not choose a conductivity value, constant-k interval,
temperature basis or material property source.

## 5. Case and geometry binding

A valid instance is never a global setting such as `material="316L"`. It must
identify the exact physical component and the exact case in which that
identity is used.

### 5.1 Case/configuration binding

`case_or_configuration_binding` must carry, at minimum:

```text
task172_case_id
task172_request_id
task172_request_hash
configuration_authority_id
configuration_authority_hash
upstream_identity_refs
binding_rule_revision
```

The upstream references must point to actual producer identities; the future
adapter must not reconstruct or replace those payloads. If a case has no
configuration authority or the referenced hash is stale, the material record
fails closed before property evaluation.

### 5.2 Geometry/component binding

`geometry_binding` must carry, at minimum:

```text
component_role
geometry_authority_id
geometry_authority_hash
physical_support_id
physical_support_hash
upstream_geometry_identity_refs
```

For this contract `component_role` is exactly `TUBE_WALL_METAL`. The support
identity must select the tube-wall physical support represented by the
TASK037 cylindrical resistance and TASK171 wall interface. A material record
for an unrelated shell, nozzle, tubesheet or double-pipe fixture cannot pass
by name similarity.

The binding rules are project interface/governance rules, not new empirical
material physics. They preserve the native geometry/provenance ownership and
make a later thermal-property record auditable.

## 6. Canonical identity and lifecycle

The authority preimage is the canonical object containing the schema/version,
component scope, material identity, source identity, case/configuration binding,
geometry binding, evidence references and approval status as defined by the
future implementation contract. The `authority_hash` is:

```text
authority_hash = canonical_sha256(canonical_payload_without_authority_hash)
```

The existing shared canonical serializer is reused; no second serialization
system is introduced. Semantically different source revisions, component
bindings, case bindings or geometry supports must produce different authority
identities. Presentation order of non-semantic mappings must not alter the
identity.

Lifecycle rules:

1. `PROPOSED_AUTHORITY` is review material only and cannot enter production
   Rating/Sizing.
2. Only an independently reviewed `REVIEWED_AUTHORITY` instance may satisfy
   a future production admission gate.
3. A missing source, rights status, case binding, geometry binding, approval or
   canonical hash is a fail-closed error.
4. A caller may transport the record, but may not promote its own record by
   setting `REVIEWED_AUTHORITY` or by supplying an observed hash as approval.
5. An authority revision, material condition change, source revision or
   component/case rebinding requires a new record and new hash.

```ini
MATERIAL_IDENTITY_SCHEMA_BOUND=true
MATERIAL_IDENTITY_COMPONENT_SCOPE_BOUND=true
MATERIAL_IDENTITY_SOURCE_PROVENANCE_RULE_BOUND=true
MATERIAL_IDENTITY_CASE_BINDING_RULE_BOUND=true
MATERIAL_IDENTITY_GEOMETRY_BINDING_RULE_BOUND=true
MATERIAL_IDENTITY_AUTHORITY_HASH_RULE_BOUND=true
MATERIAL_IDENTITY_INPUT_CONTRACT_FROZEN=true
MATERIAL_IDENTITY_OWNER_BOUND=true
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
```

`MATERIAL_IDENTITY_INPUT_CONTRACT_FROZEN=true` means the proposed contract
shape and ownership decision are fully specified in this receipt. It does not
mean the proposal has independently become a reviewed material authority.

## 7. Legacy `tube_thermal_conductivity` reconciliation

The prior targeted audit found the current-main token only in TASK026
forbidden-field boundary metadata. It is not a TASK025 upstream request/result
field, is absent from the formal seven-field hydraulic read set, and has no
complete frozen material identity or source provenance. That lineage is
retained; it is not revived.

```ini
LEGACY_TUBE_THERMAL_CONDUCTIVITY_FIELD_FOUND=true
LEGACY_FIELD_CURRENT_MAIN_PRESENT=true
LEGACY_FIELD_FROZEN_AUTHORITY=false
LEGACY_FIELD_SOURCE_PROVENANCE_COMPLETE=false
LEGACY_FIELD_REUSABLE_FOR_TASK172=false
LEGACY_TUBE_THERMAL_CONDUCTIVITY_REUSE=FORBIDDEN
LEGACY_FIELD_DISPOSITION=RETAIN_FORBIDDEN_FIELD_TOKEN_AS_TASK026_T025_BOUNDARY_METADATA;DO_NOT_TREAT_AS_MATERIAL_AUTHORITY;NO_REUSE
LEGACY_REJECTION_REASON=NO_FROZEN_MATERIAL_IDENTITY_AND_NO_COMPLETE_SOURCE_PROVENANCE
```

The explicit contract is therefore new TASK172 input ownership, not a
cross-task reactivation of the legacy token and not an amendment to TASK025.

## 8. Wall-temperature dependency is recorded, not solved

Material identity is a prerequisite for a future thermal-property authority,
but it does not supply a wall temperature. The current dependency remains:

```text
MaterialIdentityAuthority
        ↓
MaterialThermalPropertyAuthority
        ↓
thermal/wall-state calculation

WallTemperatureStateAuthority
        ↓
temperature-dependent wall property and active wall-correction consumers
```

The following substitutions are forbidden by this contract:

```text
wall_temperature = bulk_temperature
wall_temperature = mean fluid temperature
wall_temperature = caller arbitrary temperature
```

No wall-temperature iteration, film solve, viscosity correction, numerical
residual or stopping rule is defined here.

```ini
WALL_TEMPERATURE_STATE_REQUIRED=true
WALL_TEMPERATURE_STATE_AUTHORITY_BOUND=false
```

## 9. Dependency and blocker accounting

The six canonical TASK172 entry blockers remain unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN;TUBE-WALL-CORRECTION-AUTHORITY;SHELL-WALL-CORRECTION-AUTHORITY;LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION;NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW;MESH-CONVERGENCE-QUALIFICATION
```

This contract also records causal dependencies without changing that canonical
taxonomy:

```ini
TASK172_ENTRY_DEPENDENCY_BLOCKERS=MATERIAL-IDENTITY-INPUT-CONTRACT;WALL-TEMPERATURE-STATE-AUTHORITY
TASK172_SEMANTIC_CONTRACT_CORRECTION_REQUIRED=false
MATERIAL_K_SOURCE_AUTHORITY_STATUS=BLOCKED
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
TUBE_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_STATUS=BLOCKED
```

The material identity contract can be complete as a generic input boundary
while an actual instance, conductivity authority, wall state and active
corrections remain unresolved.

## 10. Review boundary and next gate

This receipt proposes the ownership and schema boundary; it does not promote
the proposal to `REVIEWED_AUTHORITY` and does not bind a real material value.
An independent reviewer should verify the owner, component scope, required
source/provenance fields, canonical preimage, no-default rule, legacy-field
rejection and unchanged TASK020/TASK021/TASK025 boundaries.

```ini
TASK172_MATERIAL_IDENTITY_INPUT_CONTRACT_PROPOSED=true
TASK172_PROPERTY_AUTHORITY_PROPOSED=false
TASK172_WALL_AUTHORITY_PROPOSED=false
TASK172_NUMERICAL_AUTHORITY_PROPOSED=false
MATERIAL_IDENTITY_INPUT_CONTRACT_REVIEW_PENDING=true
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

If the contract is independently accepted, the next separately authorized
work item is:

```ini
NEXT_GATE=AUTHORIZE_TASK172_MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONSTRUCTION_R1_ONLY
```

That next gate may address a material-specific `k`/`k(T)` source, temperature
domain, reference basis and out-of-domain behavior. It does not authorize a
wall solver, active correction, numerical profile or TASK172 implementation.

## 11. Verification checklist

* Only this contract, its evidence record and the append-only registry overlay
  are allowed to change for this task.
* No material grade, alloy, conductivity value or material property source is
  selected.
* No `tube_thermal_conductivity` legacy token is reused.
* No thermal-property field is part of the identity schema.
* Component scope is `TUBE_WALL_METAL`; no unsupported shell-wall material
  scope is invented.
* Case/configuration and geometry bindings are mandatory and hash-bound.
* Caller transport is separated from independent authority approval.
* Existing TASK020–023/TASK025/TASK037/TASK171 semantics are preserved.
* The six canonical blockers and wall-temperature dependency remain open.
* No production code, engineering calculation, dependency, solver, tolerance,
  wall iteration or Ready/Merge action is implied.

```ini
RESULT=PASS
MATERIAL_IDENTITY_CONTRACT_DEFINITION_COMPLETE=true
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
