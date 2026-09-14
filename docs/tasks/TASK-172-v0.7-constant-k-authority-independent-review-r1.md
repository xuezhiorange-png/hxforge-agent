# TASK172 — constant-k qualification authority independent review R1

## 1. Review boundary

This receipt records an independent-scope audit of the model-level
`ConstantKQualificationAuthority` proposal. It does not approve a material,
select a conductivity value, promote either upstream material contract, or
authorize TASK172 implementation.

The review uses the append-only governance correction as the effective
lifecycle overlay. The original constant-k proposal and its historical
evidence remain immutable records; their pre-correction `CLOSED` projection
is not the current state.

```ini
TASK_ID=TASK172_V0_7_MATERIAL_CONSTANT_K_AUTHORITY_INDEPENDENT_REVIEW_R1
PR_NUMBER=277
PREVIOUS_HEAD_SHA=d5d8aee3446e02fc1ea82f8dec4d4c433281c271
MODE=INDEPENDENT_AUTHORITY_REVIEW_ONLY
AUTHORITY_ID=V07-T172-CONSTANT-K-QUALIFICATION-R1
REVIEW_RECOMMENDATION=PASS_FOR_SCOPED_MODEL_LEVEL_CONTRACT_ONLY
EXTERNAL_APPROVAL_REQUIRED=true
LIFECYCLE_PROMOTION_PERFORMED=false
NEW_AUTHORITY_SELF_APPROVAL=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The review is deliberately not an approval identity. No reviewer approval
record is fabricated here:

```ini
APPROVED_BY=
APPROVAL_EVIDENCE=[]
```

## 2. Effective overlay and decision

The effective lifecycle source is
[`TASK-172-v0.7-constant-k-governance-state-correction-r1.md`](TASK-172-v0.7-constant-k-governance-state-correction-r1.md),
bound by the machine-readable governance evidence and the R11 registry
extension. It establishes the following current state:

```ini
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=PROPOSED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=PENDING
CONSTANT_K_QUALIFICATION_CONTRACT_FROZEN=true
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
```

The scoped review conclusion is:

```ini
MODEL_LEVEL_CONTRACT_ACCEPTANCE_LAWFUL_IF_INDEPENDENTLY_APPROVED=true
MODEL_LEVEL_CONTRACT_REVIEW_RECOMMENDATION=ACCEPT_IN_STATED_SCOPE
ACTUAL_MATERIAL_CASE_ACCEPTED=false
PRODUCTION_ADMISSION_ENABLED=false
CURRENT_CANONICAL_BLOCKER_REMOVED=false
```

The answer to the governing question is therefore **yes, but only at the
model-contract level**. An independent approval of this proposal could close
the model-level definition sub-blocker while leaving all future material
cases, Layer A/Layer B instances, and production admission fail-closed. This
receipt itself does not perform that approval, so the effective canonical
blocker remains active until an authorized independent approver records the
decision.

## 3. Reviewed scope

The proposed authority is acceptable for review only in the following scope:

```text
component = TUBE_WALL_METAL
quantity = SOLID_THERMAL_CONDUCTIVITY
mode = CASE_LEVEL_AUTHORITY_REQUIRED
admitted constant representation = FIXED_SOURCE_VALUE_WITH_EXPLICIT_SOURCE_DECLARED_DOMAIN
SOURCE_BOUND_K_OF_T → constant conversion = NOT_ADMITTED
required wall states = TUBE_METAL_INNER_SURFACE, TUBE_METAL_OUTER_SURFACE
wall profile = CLEAN_SURFACE_ONLY
```

It does not extend to a material catalog, a default alloy, shell-metal
properties, fouling/contact layers, active wall corrections, axial conduction,
property evaluation, wall solving, numerical convergence, or mesh authority.

The following topology and feature decisions remain unchanged and are not
approved by this receipt:

```ini
U_TUBE_ADMITTED=false
FLOATING_HEAD_ADMITTED=false
ADDITIONAL_PASSES_ADMITTED=false
FOULED_WALL_PROFILE_APPROVED=false
TUBE_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_STATUS=BLOCKED
NUMERICAL_METHOD_BOUND=false
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
```

## 4. Layer review

### Layer A — material identity

The proposal requires the exact ID and hash of
`V07-T172-MATERIAL-IDENTITY-INPUT-CONTRACT-R1`, plus a case-bound material
identity, component role, source, rights, evidence, geometry/support binding
and canonical hash. It rejects a grade-only name, hidden/default material,
legacy conductivity token and runtime catalog lookup.

The Layer A contract remains `PROPOSED_AUTHORITY/PENDING`. This review does not
promote it and does not create a material instance.

### Layer B — material thermal-property body

The proposal requires the exact ID and hash of
`V07-T172-MATERIAL-THERMAL-PROPERTY-AUTHORITY-CONTRACT-R1`, a complete
source-bound property body, explicit model (`FIXED_SOURCE_VALUE` or
`SOURCE_BOUND_K_OF_T`), units, absolute-temperature basis, domain,
provenance/rights and case/geometry bindings.

The Layer B contract remains `PROPOSED_AUTHORITY/PENDING`. A property body is
not supplied or approved by this review.

### Layer C — constant-k qualification

The Layer C contract is separate and requires both Layer A and Layer B by ID
and hash. For the fixed-value path, the selected value is exactly the
source-declared fixed value after a source-documented unit conversion. There
is no averaging, midpoint, nearest-row, room-temperature substitution or
unqualified conversion from `k(T)`.

This separation is sufficient for a model-level review recommendation because
the contract defines a future admission gate; it does not admit a case without
the reviewed upstream bodies and a reviewed case-level record.

## 5. Admission and wall-state review

The case record is complete enough to require, rather than infer, all of the
following:

* material identity ID/hash and property-body ID/hash;
* component, case/configuration, geometry and physical-support bindings;
* source revision, location, source class, rights and evidence;
* exact fixed source value and unit;
* qualification interval in absolute wall temperature;
* wall-temperature authority and complete inner/outer surface coverage;
* canonical authority hash and acyclic provenance.

Coverage is defined over every required
`TUBE_METAL_INNER_SURFACE` and `TUBE_METAL_OUTER_SURFACE` state for every
admitted physical support. Inlet, outlet, bulk, mean, ambient or a convenient
single surface state cannot substitute for that set. Missing or out-of-domain
states block; extrapolation is forbidden.

The review therefore finds the following rules present and unambiguous:

```ini
CASE_LEVEL_AUTHORITY_REQUIRED=true
HIDDEN_DEFAULT_K_FORBIDDEN=true
LEGACY_K_REUSE_FORBIDDEN=true
SOURCE_BOUND_K_OF_T_TO_CONSTANT_FORBIDDEN=true
FIXED_SOURCE_VALUE_MUST_DECLARE_DOMAIN=true
COMPLETE_WALL_STATE_COVERAGE_REQUIRED=true
BULK_TEMPERATURE_SUBSTITUTION_FORBIDDEN=true
INTERPOLATION_WITHOUT_SOURCE_RULE_FORBIDDEN=true
EXTRAPOLATION_FORBIDDEN=true
OUT_OF_DOMAIN_FAIL_CLOSED=true
UNREVIEWED_CASE_AUTHORITY_BLOCKS_PRODUCTION=true
```

## 6. Canonical identity and provenance review

The proposal reuses `hexagent.canonical_json.canonical_sha256` and includes
the schema/version, upstream IDs and hashes, case/configuration/geometry
bindings, property representation/value fields, qualified domain, wall-state
coverage, selection/acceptance rules, source/rights/evidence and lifecycle
fields in the preimage. The shared `canonical_hash` exclusion is the only
hash-field exclusion claimed.

The required identity behavior is explicit: changing the material identity,
source revision, wall-state authority, qualified domain, case or geometry
binding changes the identity; a body/hash mismatch blocks. The provenance
graph remains acyclic and has no fabricated producer or caller-assertion
promotion.

The historical R1 body/evidence hashes and the R11 governance overlay are
treated as distinct records. The overlay, not the historical pre-review
projection, determines the current lifecycle state.

## 7. Checklist result

| Review item | Result | Boundary finding |
| --- | --- | --- |
| Layer A → Layer B → Layer C separation | PASS | Each layer is distinct and referenced by ID/hash. |
| Case-level authority requirement | PASS | No naked `constant_k_value` can pass. |
| Hidden/default/legacy `k` rejection | PASS | Explicit fail-closed rules are present. |
| Fixed source-value admission | PASS | Source-declared value, basis and domain are required. |
| `SOURCE_BOUND_K_OF_T` handling | PASS | No automatic constant conversion is admitted. |
| Selection/method/metric/acceptance | PASS | Semantic source/domain rule; no invented numeric tolerance. |
| Complete inner/outer wall-state coverage | PASS | Physical support and both surface identities are required. |
| Bulk/inlet/outlet substitution | PASS | Explicitly forbidden. |
| Interpolation/extrapolation/domain failure | PASS | Source rule required; extrapolation and out-of-domain block. |
| Material/property/case/config/geometry binding | PASS | Required fields and hash matching are explicit. |
| Source/provenance/rights/evidence binding | PASS | Incomplete provenance blocks. |
| Canonical preimage and replay behavior | PASS | Shared serializer and identity-affecting fields are explicit. |
| Caller assertion/self-approval resistance | PASS | Caller transport is not approval; approval fields remain empty. |
| Production admission gate | PASS | Unreviewed case authority blocks production. |
| Active wall-correction interaction | PASS | Tube and shell corrections remain independent blocked authorities. |
| Numerical/solver scope | PASS | No method, tolerance, error budget or mesh rule is introduced. |
| Governance-overlay reconciliation | PASS | R11 effective state overrides the historical lifecycle projection. |
| Independent approval boundary | PASS | This receipt recommends scoped acceptance but performs no promotion. |

No `CHANGES_REQUIRED` finding was identified within the model-level contract
scope. This is not a material-case qualification and not production admission.

## 8. Current state and blockers

Because this execution cannot fabricate an approver or promote the authority,
the effective state remains:

```ini
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=PROPOSED_AUTHORITY
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=PENDING
CONSTANT_K_QUALIFICATION_CONTRACT_FROZEN=true
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
```

The six canonical TASK172 entry blockers therefore remain unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN,TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=6
TASK172_ENTRY_DEPENDENCY_BLOCKERS=NONE
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

An authorized independent approval may, in a subsequent governance action,
record the model-level closure of the first item only. It must not remove the
other five blockers or create a material profile.

## 9. Evidence and next gate

The machine-readable companion
[`evidence/TASK-172-constant-k-authority-independent-review-r1.json`](evidence/TASK-172-constant-k-authority-independent-review-r1.json)
binds this checklist to the subject authority, the R11 effective overlay,
historical proposal/evidence identities, upstream Layer A/B statuses and the
current six-blocker state. Its `review_result` is a scoped recommendation;
its approval fields are empty and its lifecycle promotion flag is false.

```ini
REVIEW_EVIDENCE_BOUND=true
REVIEW_EVIDENCE_IS_APPROVAL=false
EXTERNAL_INDEPENDENT_APPROVAL_PENDING=true
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_MODEL_LEVEL_CONSTANT_K_ACCEPTANCE
```

## 10. Receipt

```ini
RESULT=PASS_FOR_SCOPED_MODEL_LEVEL_CONTRACT_WITH_EXTERNAL_APPROVAL_PENDING
CONSTANT_K_QUALIFICATION_AUTHORITY_STATUS=PROPOSED_AUTHORITY
CONSTANT_K_QUALIFICATION_CONTRACT_FROZEN=true
CONSTANT_K_QUALIFICATION_INDEPENDENT_REVIEW=PENDING
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_CONSTANT_K_CANONICAL_BLOCKER_REMOVED=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
