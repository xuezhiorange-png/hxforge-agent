# TASK172 R1 — material thermal-property authority contract construction

## 1. Receipt and immutable boundary

This is a documentation-only contract construction for Draft PR277. It
defines the future TASK172 input authority for a solid tube-wall thermal
property. It does not select a material, choose a conductivity value, qualify
an actual material instance, implement property evaluation, solve a wall
state, add a wall correction, or start TASK172 production implementation.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONSTRUCTION_R1
PR=277
PREVIOUS_HEAD_SHA=bd2456095258aec9e28026eb19b3e3b44670f68b
MODE=CONTROLLED_MATERIAL_PROPERTY_AUTHORITY_CONTRACT_ONLY
DOCUMENT_STATUS=PROPOSED_AUTHORITY
AUTHORITY_ID=V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1
AUTHORITY_VERSION=r1
NEW_AUTHORITY_SELF_APPROVAL=false
MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONTRACT_FROZEN=true
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

“Frozen” in this receipt means that the proposed contract shape and fail-closed
boundary are fully specified. It does not promote this proposal to
`REVIEWED_AUTHORITY`, and it does not create a usable property profile.

The preceding [material identity input contract](TASK-172-v0.7-material-identity-authority-input-contract-r1.md)
is retained as the upstream identity boundary. This receipt is an append-only
overlay and does not rewrite its payload or hash.

## 2. Dependency reconciliation

The material identity input contract is now treated as a completed dependency
boundary. That fact concerns the input contract only; no actual material
identity or thermal-property value is bound by this task.

```ini
MATERIAL_IDENTITY_AUTHORITY_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
MATERIAL_IDENTITY_INPUT_CONTRACT_FROZEN=true
MATERIAL_IDENTITY_INPUT_CONTRACT_BLOCKER_CLOSED=true
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
TASK172_ENTRY_DEPENDENCY_BLOCKERS=WALL-TEMPERATURE-STATE-AUTHORITY
TASK172_SEMANTIC_CONTRACT_CORRECTION_REQUIRED=false
```

The six canonical TASK172 entry blockers remain unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN;TUBE-WALL-CORRECTION-AUTHORITY;SHELL-WALL-CORRECTION-AUTHORITY;LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION;NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW;MESH-CONVERGENCE-QUALIFICATION
```

Removing `MATERIAL-IDENTITY-INPUT-CONTRACT` from the dependency list does not
close `MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN`. A source-qualified `k` or
`k(T)` instance is still absent.

## 3. Owner and admission boundary

The property authority is owned at the TASK172 case-input boundary. The
caller transports a complete source-bound record; transport is not approval.
TASK020–023 and the legacy `tube_thermal_conductivity` token do not become
property authorities through this overlay.

```ini
MATERIAL_PROPERTY_OWNER=TASK172_CASE_INPUT_AUTHORITY_BOUNDARY
MATERIAL_PROPERTY_OWNERSHIP_DECISION=OPTION_A_ADOPTED_EXPLICIT_SOURCE_BOUND_MATERIAL_THERMAL_PROPERTY_BODY
MATERIAL_PROPERTY_BODY_REQUIRED=true
CALLER_TRANSPORT_IS_SELF_APPROVAL=false
IDENTITY_OR_HASH_WITHOUT_BODY_ALLOWED=false
PSEUDO_PROPERTY_FROM_MATERIAL_ID_ONLY=FORBIDDEN
HIDDEN_DEFAULT_K_FORBIDDEN=true
RUNTIME_MATERIAL_DATABASE_LOOKUP=FORBIDDEN
DEFAULT_MATERIAL_SELECTION=FORBIDDEN
LEGACY_TUBE_THERMAL_CONDUCTIVITY_REUSE=FORBIDDEN
```

Only a record with an independently reviewed lifecycle status may enter a
future production gate. A caller cannot make a record authoritative by
setting `REVIEWED_AUTHORITY`, copying an observed hash, or omitting the body.

## 4. MaterialThermalPropertyAuthority schema

The proposed schema version is `task172.material-thermal-property.v1`. A
future authority instance must contain one complete property body and all
identity, binding and provenance fields below. Conditional alternatives are
allowed only where the selected source explicitly makes the alternative
non-applicable and the record carries that source-backed reason.

### 4.1 Required record fields

```text
schema_version
authority_id
authority_version
review_status
property_quantity_kind
material_identity_authority_id
material_identity_authority_hash
component_scope
case_or_configuration_binding
geometry_binding
property_model
k_value_or_k_curve
property_units
temperature_basis
temperature_domain
source_provenance
interpolation_policy
extrapolation_policy
out_of_domain_policy
constant_k_policy
evidence_refs
authority_hash
```

The exact quantity kind for this contract is:

```ini
PROPERTY_QUANTITY_KIND=SOLID_THERMAL_CONDUCTIVITY
COMPONENT_SCOPE=TUBE_WALL_METAL
PROPERTY_UNITS=W_PER_M_K
```

This is not a fluid thermal-conductivity, viscosity, Prandtl, HTC, `U`,
fouling, or wall-temperature authority. A future implementation must reject a
body whose quantity kind is not exactly `SOLID_THERMAL_CONDUCTIVITY`.

### 4.2 Property body

`property_model` must declare the source representation. The proposed
contract permits only the following semantic forms:

```text
FIXED_SOURCE_VALUE
SOURCE_BOUND_K_OF_T
```

For `FIXED_SOURCE_VALUE`, the body must carry the source value, units,
temperature basis and source-qualified applicability domain. For
`SOURCE_BOUND_K_OF_T`, it must carry the complete source-bound curve/table,
point units, independent variable basis, domain, ordering rule and source
interpolation rule if one exists. The record must not carry both alternatives
as competing values.

Neither form is selected in this task. No material grade, `k` value, curve,
material profile ID, or constant-k interval is an actual instance here.

### 4.3 Identity and binding fields

`material_identity_authority_id` and
`material_identity_authority_hash` must refer to the exact upstream
`V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1` instance used for the component.
An ID without its matching hash, or a hash copied from a different identity,
fails closed.

`case_or_configuration_binding` must include at least:

```text
task172_case_id
task172_request_id
task172_request_hash
configuration_authority_id
configuration_authority_hash
upstream_identity_refs
binding_rule_revision
```

`geometry_binding` must include at least:

```text
component_role
geometry_authority_id
geometry_authority_hash
physical_support_id
physical_support_hash
upstream_geometry_identity_refs
```

For this contract `component_role` is exactly `TUBE_WALL_METAL`, and the
physical support is the tube-metal support represented by the reviewed TASK037
cylindrical wall resistance and TASK171 wall interface. A material property
for a shell, tubesheet, nozzle or unrelated fixture cannot pass by name
similarity.

## 5. Source/provenance and canonical identity

`source_provenance` must bind, at minimum:

```text
source_id
source_version_or_revision
source_location
source_class
permission_status
evidence_refs
```

The source record must state whether it supplies a fixed value or a `k(T)`
representation, the material/component interpretation, the temperature basis
and the applicable domain. A bibliography-only citation, a library default or
an unread source is insufficient. Rights are not inferred from public
availability.

The authority identity is computed with the existing shared serializer:

```text
authority_hash = hexagent.canonical_json.canonical_sha256(
    complete_record_without_authority_hash
)
```

The preimage includes the property body, material identity ID/hash,
component/case/geometry bindings, source/provenance, domain and lifecycle
fields. `authority_hash` is excluded from its own preimage by the existing
TASK012 canonical rule. A body change must therefore change the recomputed
hash; a caller-supplied hash does not make an altered body valid.

The future validator must reject all of the following before property
evaluation:

| Condition | Required result |
| --- | --- |
| Missing property body | `BLOCKED` — `MATERIAL_PROPERTY_BODY_REQUIRED` |
| Material identity ID/hash mismatch | `BLOCKED` — cross-binding failure |
| Authority hash mismatch | `BLOCKED` — canonical identity failure |
| Same supplied hash with a different body | `BLOCKED` — body/hash mismatch |
| Missing source, rights or evidence binding | `BLOCKED` — provenance incomplete |
| Unreviewed lifecycle status at production boundary | `BLOCKED` — authority not reviewed |
| Property outside its declared domain | `BLOCKED` — `OUT_OF_DOMAIN_POLICY` |

Identity and hash are necessary integrity evidence, but never substitute for
the source-bound property body.

## 6. Interpolation, extrapolation and domain policy

The future evaluator must consume the policy carried by the authority record;
it may not silently select a numerical method.

```ini
INTERPOLATION_POLICY=EXPLICIT_SOURCE_RULE_REQUIRED
INTERPOLATION_WITHOUT_SOURCE_RULE=FORBIDDEN
EXTRAPOLATION_POLICY=FORBIDDEN
OUT_OF_DOMAIN_POLICY=BLOCKED
```

If the source specifies interpolation, the record must reproduce that rule,
including independent-variable basis, allowed interval and any source-defined
unit/rounding semantics. If it does not, interpolation is forbidden and the
source representation must be consumed only in the manner it explicitly
supports. Extrapolation is never inferred from a curve endpoint.

`temperature_basis` must distinguish absolute material/property temperature
from any source-specific reference or reporting basis. `temperature_domain`
must be source-bound; no domain is chosen by this contract.

## 7. Layer A versus Layer B

This contract keeps two decisions separate:

### Layer A — property-source authority

Layer A identifies a qualified material property source and its representation:
a source fixed value or a source-bound `k(T)` body. It binds units, temperature
basis, domain, source identity, provenance and interpolation policy.

### Layer B — constant-k qualification

Layer B is a later case/profile decision that may permit a fixed value to be
used over a particular wall-temperature hull. It must separately bind the
selected material identity, source value, evaluation basis, temperature range,
allowed variation/qualification rule and review evidence. It cannot be inferred
from a material name, one unqualified point, or a generic engineering default.

No Layer A source and no Layer B qualification is selected in this task:

```ini
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
MATERIAL_K_SOURCE_AUTHORITY_STATUS=BLOCKED
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
```

Accordingly, this task constructs the contract but does not enable a material
property in production.

## 8. Wall-temperature dependency and explicit non-scope

The property temperature for a future `k(T)` evaluation is the explicitly
located wall/material state required by the wall-temperature authority. A bulk,
mean, ambient or caller-arbitrary temperature is not an allowed substitute.

```ini
WALL_TEMPERATURE_STATE_REQUIRED=true
WALL_TEMPERATURE_STATE_AUTHORITY_BOUND=false
BULK_TEMPERATURE_SUBSTITUTION_ALLOWED=false
WALL_TEMPERATURE_SOLVER_IMPLEMENTED=false
```

This task does not create a property runtime adapter, lookup database, cache,
constant-k material profile, wall-temperature solver, viscosity/Prandtl
correction, numerical profile, tolerance, mesh rule or new dependency. It does
not modify the legacy TASK037 wall resistance or the prior material identity
contract. Synthetic fixtures may exercise schema rejection only; they are not
engineering authority and cannot become production defaults.

```ini
SYNTHETIC_FIXTURE_IS_ENGINEERING_AUTHORITY=false
SYNTHETIC_FIXTURE_NOT_PRODUCTION_DEFAULT=true
TUBE_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_STATUS=BLOCKED
NUMERICAL_PROFILE_STATUS=PARTIALLY_CLOSED
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
```

## 9. Review status and next gate

The new record remains a proposal. Codex does not promote it to
`REVIEWED_AUTHORITY`, and no reviewer identity is invented.

```ini
TASK172_MATERIAL_THERMAL_PROPERTY_AUTHORITY_PROPOSED=true
MATERIAL_THERMAL_PROPERTY_AUTHORITY_CONTRACT_FROZEN=true
MATERIAL_THERMAL_PROPERTY_AUTHORITY_REVIEW_STATUS=PROPOSED_AUTHORITY
APPROVED_BY=
APPROVAL_EVIDENCE=[]
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

The next authorized slice, if separately approved, is:

```ini
NEXT_GATE=AUTHORIZE_TASK172_WALL_TEMPERATURE_STATE_AUTHORITY_DEFINITION_R1_ONLY
```

That next gate does not authorize a material selection, wall correction,
solver, numerical preset or TASK172 implementation.

## 10. Verification receipt

The [machine-readable evidence record](evidence/TASK-172-material-thermal-property-authority-construction-r1.json)
and [append-only authority registry](TASK-172-v0.7-authority-registry-r1.json)
bind this document by SHA-256 after the final documentation-only edit. The
local checks must confirm JSON validity,
canonical hashes, unique authority IDs, complete source/binding field lists,
relative links, diff allowlist and whitespace. No production source, test
semantics, dependency, TASK170/TASK171 historical fact or Golden expectation
changes in this task.

```ini
RESULT=PASS
MATERIAL_PROPERTY_CONTRACT_DEFINITION_COMPLETE=true
MATERIAL_PROPERTY_BODY_REQUIRED=true
MATERIAL_IDENTITY_INPUT_CONTRACT_BLOCKER_CLOSED=true
TASK172_ENTRY_DEPENDENCY_BLOCKERS=WALL-TEMPERATURE-STATE-AUTHORITY
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
