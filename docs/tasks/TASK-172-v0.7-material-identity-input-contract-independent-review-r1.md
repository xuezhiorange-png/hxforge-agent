# TASK172 — scoped independent audit of the material-identity input contract

## 1. Receipt boundary

This document is an append-only model-level scope-audit receipt for the
material-identity input contract proposed in
[`TASK-172-v0.7-material-identity-authority-input-contract-r1.md`](TASK-172-v0.7-material-identity-authority-input-contract-r1.md).
It does not rewrite that proposal, create a material instance, promote an
authority lifecycle state, or close the material canonical blocker.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW_R1
PR=277
PREVIOUS_HEAD_SHA=f1a7a7e9722657e7a0004468c8d43df3578d34ec
MODE=INDEPENDENT_SCOPE_AUDIT_ONLY
SUBJECT_AUTHORITY_ID=V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_MODEL_LEVEL_LAYER_A_CONTRACT
INDEPENDENT_REVIEW_SCOPE=MODEL_LEVEL_MATERIAL_IDENTITY_INPUT_CONTRACT_ONLY
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

The audit answers the authorized question **YES**: the proposed contract can
be accepted as a model-level identity-input shape and ownership boundary while
no actual material is selected, Layer B remains pending, Layer C remains
unchanged, the canonical material blocker remains active, and production
admission remains fail-closed. This positive scope result is not an external
lifecycle promotion. The subject therefore remains
`PROPOSED_AUTHORITY` / independent review `PENDING` until the next external
reviewer confirms or rejects the scoped acceptance.

## 2. Scope and layer separation

The audited boundary is only Layer A:

```text
Layer A: MaterialIdentityInputContract
    identity, ownership, source/provenance, case binding, geometry binding
    ↓
Layer B: MaterialThermalPropertyContract
    conductivity/property authority (not audited or promoted here)
    ↓
Layer C: Constant-k qualification contract
    already independently accepted; unchanged by this receipt
```

The following state is intentionally preserved:

| Layer or state | Current value | Consequence |
| --- | --- | --- |
| Layer A authority | `PROPOSED_AUTHORITY` | Contract shape is audited; no production admission. |
| Layer A independent review | `PENDING` | This receipt does not perform lifecycle promotion. |
| Layer B authority | `PROPOSED_AUTHORITY` | Thermal-property contract remains pending. |
| Layer B independent review | `PENDING` | No property value or profile is approved. |
| Layer C authority | `REVIEWED_AUTHORITY` | Existing scoped acceptance remains unchanged. |
| Layer C independent review | `ACCEPTED` | It does not imply Layer A/B or material approval. |
| Material profile | `NONE` | No actual material instance is bound. |
| Material identity actual value | `false` | No grade/alloy has been selected. |
| Material constant-k status | `OPEN` | The canonical blocker remains active. |
| Material-k temperature domain | `false` | No material property domain is bound. |

This receipt does not review, alter, or promote Layer B or Layer C.

## 3. Layer A audit findings

Each finding below is a contract-shape finding against the existing R1
proposal. `PASS` means that the proposed boundary contains the required
fail-closed rule; it does not mean that a future material record has passed it.

| Check | Result | Audited contract requirement |
| --- | --- | --- |
| `A01_OWNERSHIP` | `PASS` | Owner is `TASK172_CASE_INPUT_AUTHORITY_BOUNDARY`; the contract is not delegated to TASK020, TASK021, TASK025, or a hidden default. |
| `A02_COMPONENT_ROLE` | `PASS` | `component_role` is exact `TUBE_WALL_METAL`; shell, nozzle, tubesheet, and unrelated components cannot bind through name similarity. |
| `A03_IDENTITY_PROPERTY_SEPARATION` | `PASS` | Material identity is distinct from thermal-property authority; no conductivity or `k(T)` is inferred from identity. |
| `A04_IDENTITY_DISAMBIGUATION` | `PASS` | Standard system, specification/designation, grade/alloy, condition/temper where applicable, and product form where identity requires it are required semantic fields. |
| `A05_SOURCE_BINDING` | `PASS` | `source_id`, revision, exact location, source class, permission status, and evidence references are required. |
| `A06_CALLER_TRANSPORT` | `PASS` | Caller transport is only transport; a caller assertion, copied hash, or requested status is not approval. |
| `A07_BARE_DESIGNATION_REJECTION` | `PASS` | A bare grade string, material name, or unreviewed assertion cannot satisfy the authority record. |
| `A08_HIDDEN_DEFAULT_REJECTION` | `PASS` | Hidden/default material, fixture material, library default, and silent fallback are forbidden. |
| `A09_RUNTIME_DATABASE_REJECTION` | `PASS` | Runtime material-database lookup cannot supply or silently complete material authority. |
| `A10_LEGACY_FIELD_REJECTION` | `PASS` | Legacy `tube_thermal_conductivity` remains forbidden boundary metadata and cannot be revived as material authority. |
| `A11_CASE_BINDING` | `PASS` | Request/configuration IDs, hashes, binding revision, and upstream identity references are mandatory. |
| `A12_GEOMETRY_BINDING` | `PASS` | Geometry authority/hash, physical-support identity/hash, component role, and upstream geometry references are mandatory. |
| `A13_NAME_SUBSTITUTION_REJECTION` | `PASS` | Component, geometry, and physical-support binding cannot be satisfied by similar names. |
| `A14_CANONICAL_PREIMAGE` | `PASS` | Schema/version, component scope, identity, source, case/configuration, geometry, evidence, and lifecycle status are in the canonical preimage; the hash is excluded from its own preimage. |
| `A15_REBINDING_IDENTITY` | `PASS` | Source revision, material condition, case rebinding, component/support rebinding, or geometry rebinding requires a new record and identity. |
| `A16_PROPOSED_LIFECYCLE` | `PASS` | `PROPOSED_AUTHORITY` is review material only and cannot enter production Rating/Sizing. |
| `A17_INDEPENDENT_REVIEW_GATE` | `PASS` | Independent review is required before an instance can become `REVIEWED_AUTHORITY` for production admission. |
| `A18_LAYER_A_EXCLUSIONS` | `PASS` | Layer A carries no conductivity value, constant-k, `k(T)`, wall temperature, HTC, U, correction factor, or fouling. |
| `A19_SCOPED_ACCEPTANCE` | `PASS` | Acceptance of the contract means only identity-input shape and ownership are acceptable; it does not approve a material instance. |
| `A20_BLOCKER_PRESERVATION` | `PASS` | The receipt does not implicitly approve Layer B, alter Layer C, or remove `MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN`. |

The audited proposal consequently has a complete model-level contract shape for
the requested scope, subject to the lifecycle state remaining proposed/pending.

## 4. Required record shape

The future authority instance must continue to carry the complete semantic
identity set from the R1 proposal. In particular, the identity portion must
include:

```text
schema_version
authority_id
authority_version
component_role = TUBE_WALL_METAL
material_identity_id
material_standard_system
material_specification_or_designation
material_grade_or_alloy
material_condition_or_temper_if_applicable
product_form_if_material_identity_requires_it
source_id
source_version_or_revision
source_location
source_class
permission_status
evidence_refs
approval_status
case_or_configuration_binding
geometry_binding
authority_hash
```

The case binding remains required to include the TASK172 case/request identity,
configuration authority identity and hash, upstream references, and binding
rule revision. The geometry binding remains required to include the component
role, geometry authority identity and hash, physical-support identity and hash,
and upstream geometry identity references.

These are ownership and auditability rules, not new material-property physics.
They prevent an unreviewed caller payload from being mistaken for an approved
material instance.

## 5. Explicit fail-closed boundaries

The following inputs or behaviours remain rejected:

```text
bare_grade_string_as_authority              = REJECT
material_name_as_authority                 = REJECT
caller_assertion_as_approval               = REJECT
hidden_or_default_material                 = REJECT
runtime_material_database_completion       = REJECT
legacy_tube_thermal_conductivity_reuse     = REJECT
missing_source_or_permission_metadata      = REJECT
missing_case_or_configuration_binding      = REJECT
missing_geometry_or_physical_support       = REJECT
name_only_component_matching               = REJECT
PROPOSED_AUTHORITY_production_admission    = REJECT
identity_to_conductivity_inference         = REJECT
bulk_temperature_as_wall_temperature       = REJECT
```

The last rule is recorded as a dependency boundary only. This Layer A audit
does not define or solve wall temperature.

## 6. Canonical and provenance conclusion

The proposal's shared serializer remains
`hexagent.canonical_json.canonical_sha256`; no second canonical system is
introduced. A future authority hash must change when any of the following
semantics change:

* material identity, standard/designation, condition or product form;
* source identity, revision, location, permission or evidence binding;
* TASK172 case/configuration identity or binding revision;
* geometry authority, component role or physical support;
* lifecycle/approval status.

The provenance chain is therefore identity-first and acyclic: the material
identity record points to the cited source, case/configuration and geometry
producer identities; it does not replace those producers or fabricate their
results. A hash copied from an unreviewed record remains insufficient.

## 7. Effective status and next gate

The positive scoped audit does not reduce the canonical entry blocker set. The
six remaining blockers are unchanged:

```ini
MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN
TUBE-WALL-CORRECTION-AUTHORITY
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
MATERIAL_IDENTITY_INPUT_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_IDENTITY_INPUT_CONTRACT_INDEPENDENT_REVIEW=PENDING
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROFILE_ID=NONE
MATERIAL_THERMAL_PROPERTY_CONTRACT_STATUS=PROPOSED_AUTHORITY
MATERIAL_THERMAL_PROPERTY_CONTRACT_INDEPENDENT_REVIEW=PENDING
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=REVIEWED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=ACCEPTED
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=6
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

The next gate is:

```ini
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_MODEL_LEVEL_LAYER_A_ACCEPTANCE
```

That gate may confirm or reject this scoped contract audit. It is not an
authorization to select a material, construct a material profile, promote
Layer B, close the constant-k blocker, or start TASK172 implementation.

## 8. Governance and verification

This receipt is documentation/evidence-only. It introduces no equation,
coefficient, property value, tolerance, material instance, production code,
dependency, test physics, or downstream task authorization. The prior R1
proposal and all prior registry records remain immutable; this receipt is an
append-only overlay.

```ini
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
LAYER_B_REVIEWED_OR_PROMOTED=false
LAYER_C_REVIEWED_OR_PROMOTED_BY_THIS_RECEIPT=false
MATERIAL_PROFILE_CREATED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The machine-readable evidence for this receipt is
[`TASK-172-material-identity-input-contract-independent-review-r1.json`](evidence/TASK-172-material-identity-input-contract-independent-review-r1.json).
