# TASK172 v0.7 — Pre-Runtime Consolidated Closeout Audit R1

```ini
TASK_ID=TASK172_V0_7_R119E_AND_PRE_RUNTIME_CONSOLIDATED_CLOSEOUT_R1
MODE=CONSOLIDATED_READ_ONLY_PRE_RUNTIME_CONTRACT_AUDIT
PR_NUMBER=283
AUDIT_HEAD=dcac4c6c9f66d866670caade37b4948499aa33ef
RESULT=PRE_RUNTIME_CONSOLIDATED_CLOSEOUT_AUDIT_COMPLETED
TASK171_STATUS=VALIDATED
TASK172_RUNTIME_API_IMPLEMENTED=false
TASK172_RUNTIME_READY_NOW=false
TASK172_RUNTIME_BLOCKER_COUNT=6
AGGREGATE_GEOMETRY_ID_REQUIRED_BEFORE_TASK172_RUNTIME=false
FLUID_IDENTITY_REQUIRED_FOR_RUNTIME=true
FLUID_IDENTITY_REQUIRED_FOR_THERMAL_SOLVE=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK172_RUNTIME=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK173=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK174=true
PRODUCTION_MESH_ADMISSION_REQUIRED_FOR_TASK172_REAL_CASE_EXECUTION=true
REFERENCE_POLICY_REQUIRED_FOR_TASK172_RUNTIME=false
REFERENCE_POLICY_RESOLUTION_REQUIRED_FOR_REAL_CASE_MESH_ADMISSION=true
PROJECT_OWNER_DECISION_COUNT=7
REMAINING_MAJOR_STAGE_COUNT=4
NEXT_GATE=PRE_RUNTIME_AUTHORITY_CLOSURE
PRODUCTION_CODE_CHANGED=false
EXISTING_TESTS_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILES_CHANGED=false
WORKFLOWS_CHANGED=false
STOP=true
```

## Audit boundary and conclusion

This is a source- and contract-based closeout audit at the R119-D final HEAD, not a TASK172 implementation or a producer run. No TASK014–TASK025 or TASK171 producer was invoked. The external R119-D independent-review decision is recorded separately in R119-E; its accepted native topology is the starting point here.

The repository contains the native TASK171 package and neighboring stream, performance, and hydraulic components, but no native TASK172, TASK173, TASK174, or TASK175 implementation/API. Therefore there is no TASK172 runtime request schema or runtime function whose exact Python fields can be asserted. The report distinguishes (1) native contracts that exist, (2) the reviewed task-ownership contracts, and (3) the separate real-case mesh-admission governance predicate. Where a TASK172/TASK173/TASK174 executable contract does not yet exist, no invented API name or field is presented as native fact.

R119-E accepts a validated, role-bound TASK171 topology and deterministic native `mesh_identity`; it does not complete the property/wall/convergence closure or production-mesh admission. TASK172 is not runtime-ready: the native runtime is absent and case-level stream/property, material/wall/correlation, execution-profile, and real-case mesh-admission inputs remain unresolved. This is not a finding that the accepted TASK171 materialization failed.

## A. Aggregate geometry identity

No native TASK172 source consumer or request model exists in this repository, so no native runtime contract was found that requires a single aggregate `GEOMETRY_ID` before TASK172 runtime construction. The TASK171 native result emits `topology_id`, `result_hash`, `mesh_identity`, and `physical_ownership_hash`; it does not emit an aggregate `GEOMETRY_ID`. R119-D explicitly records `GEOMETRY_ID=UNBOUND` and `NO_REVIEWED_NATIVE_AGGREGATE_CASE_GEOMETRY_ID_CONTRACT`.

The separate real-case mesh-admission contract does list `GEOMETRY_ID` among the records required before real-case mesh selection (contract R1, “Required case-bound prerequisites”). Its admission predicate additionally requires geometry mapping and applicable case bindings. This is a governance/admission requirement, not evidence of a TASK172 runtime API field. None of the TASK020–TASK025 IDs, `topology_id`, or `mesh_identity` may be aliased to an aggregate geometry ID. No binding is created here.

```ini
AGGREGATE_GEOMETRY_ID_REQUIRED_BEFORE_TASK172_RUNTIME=false
GEOMETRY_ID_REQUIRED_BY_REAL_CASE_MESH_ADMISSION_CONTRACT=true
GEOMETRY_ID=UNBOUND
GEOMETRY_ID_UNBOUND_REASON=NO_REVIEWED_NATIVE_AGGREGATE_CASE_GEOMETRY_ID_CONTRACT
```

## B–C. Fluid and property requirements

The native TASK171 Definition represents paths, intervals, cells, walls, physical events, and states, and its validated R119-D result is available without a fluid identity or property profile. That structural fact is not sufficient to evaluate thermophysical properties or perform a thermal solve.

The implemented TASK160 stream contract makes `fluid_or_service_identity`, phase, inlet temperature, pressure when required by the property query, mass flow, and a typed property snapshot mandatory in a valid `RatingStreamInput`. The property snapshot binds the property source identity/version and evaluation context. TASK161 consumes an actual TASK160 result; TASK162 consumes TASK160/TASK161/TASK038 results and case/assumption authorities; TASK163 consumes TASK162 output plus success replay evidence. The shell-side flow-state authority separately requires a fluid ID, property snapshot/hash, and mass-flow authority; the shell pressure-drop request includes wall-viscosity source/version/evidence and property snapshot bindings.

Accordingly, fluid identity and property data are required for an executable thermal runtime/solve path and for the extant rating and hydraulic components. This conclusion is about the native property-bearing stream and flow-state contracts; the exact scalar named `PROPERTY_PROFILE_AUTHORITY_ID` is not a field in the inspected Task160–Task163 model classes. Authority is represented there by typed property snapshots, source identity/version, evaluation context, and hashes. Production mesh admission separately requires a case-bound property profile authority ID.

```ini
FLUID_IDENTITY_REQUIRED_FOR_STRUCTURAL_TOPOLOGY=false
FLUID_IDENTITY_REQUIRED_FOR_RUNTIME=true
FLUID_IDENTITY_REQUIRED_FOR_THERMAL_SOLVE=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK172_RUNTIME=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK173=true
PROPERTY_PROFILE_REQUIRED_FOR_TASK174=true
PROPERTY_PROFILE_AUTHORITY_ID=UNBOUND
```

No fluid, phase, inlet state, mass flow, property source, property snapshot, or fluid name is inferred or bound by this audit.

## D. Structural mesh versus production admission

R119-E accepts `mesh_identity=ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607` as the native TASK171 structural identity. It is a valid materialized topology/mesh interface for downstream structural binding. It is not a production mesh profile, a real-case refinement/convergence/resource policy, or a production-admission result.

The real-case mesh-admission contract is explicit that numerical mesh identity and production admission are separate. It requires a case-bound mesh profile and resolved initial-mesh, refinement, convergence, resource, mapping, and other policy slots. Its exact current consumer is the documented real-case admission predicate; no production-source function or field called `REAL_CASE_MESH_ADMISSIBLE`, `PRODUCTION_MESH_PROFILE_AUTHORITY_ID`, or `reference_policy_resolution_valid` was found under `src/hexagent`.

Thus production-mesh admission is not required to develop/import the structural TASK172 implementation or run synthetic implementation validation, but it is required before a TASK172 real-case production execution using an admitted real-case mesh. The accepted TASK171 mesh identity alone is structurally useful and is not sufficient for that production execution.

```ini
TASK171_STRUCTURAL_MESH_IDENTITY_ACCEPTED=true
PRODUCTION_MESH_PROFILE_AUTHORITY_ID=UNBOUND
REAL_CASE_MESH_ADMISSIBLE=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
PRODUCTION_MESH_ADMISSION_REQUIRED_FOR_TASK172_IMPLEMENTATION=false
PRODUCTION_MESH_ADMISSION_REQUIRED_FOR_TASK172_REAL_CASE_EXECUTION=true
```

## E. Reference-policy/oracle requirement

The repository has no runtime code consumer of `reference_policy_resolution_valid`. The documented R107 composite gate is used by the real-case mesh-admission predicate: it requires both case-applicable reference-policy resolution and production-reference-oracle requirement resolution. This must be resolved before real-case mesh admission, but it is not a native TASK172 runtime API input discovered in source code.

The reviewed R109/R110 decision is narrowly `production_reference_oracle_required=false` for the scoped profile: an online continuous-reference oracle is not a mandatory admission prerequisite. It does not make reference comparisons universally inapplicable, nor does it resolve the case-specific policy binding. Therefore: no live reference oracle is required before TASK172 runtime implementation or validation; the governance resolution still must be valid before real-case mesh admission. This audit does not create or enable a policy.

```ini
REFERENCE_POLICY_REQUIRED_FOR_TASK172_RUNTIME=false
REFERENCE_POLICY_RESOLUTION_REQUIRED_BEFORE_REAL_CASE_MESH_ADMISSION=true
ONLINE_CONTINUOUS_REFERENCE_ORACLE_REQUIRED_FOR_REVIEWED_SCOPE=false
REFERENCE_POLICY_RESOLUTION_VALID=false
```

## F. Runtime readiness and dependency matrix

“Required for native TASK172?” is interpreted against the reviewed TASK170 responsibility and the actual existing neighboring producer contracts. Since a native TASK172 API is absent, the matrix does not pretend to validate an unimplemented TASK172 request schema. “Blocking” means blocking the named real-case runtime/solve/admission stage, not necessarily blocking code development with synthetic fixtures.

| Input / authority | Current state | Required by native TASK172 path? | Blocking? | Exact consumer or contract | Category |
| --- | --- | --- | --- | --- | --- |
| TASK171 `topology_id` | Materialized and externally reviewed | Yes, as topology identity | No | TASK171 `Result.topology_id`; future consumer not yet implemented | E |
| Effective TASK171 `Definition` | Variant A selected; role and reviewed authority IDs are bound | Yes, structural topology input | No | TASK171 `Definition`; future TASK172 interface defined by TASK170 | E |
| TASK171 `mesh_identity` | Materialized and externally reviewed | Yes for structural cell mapping; not production admission | No for structure; yes for production use until admission | TASK171 `Result.mesh_identity`; real-case mesh-admission predicate | E |
| TASK171 `physical_ownership_hash` | Materialized and externally reviewed | Yes for physical-support ownership | No | TASK171 `Result.physical_ownership_hash` and Definition mapping | E |
| TASK020 configuration identity | R118-D accepted | Yes as upstream case binding | No | TASK171 `NativeIdentity`; upstream TASK020 materialization | E |
| TASK021 layout identity | R118-D accepted | Yes as upstream tube-position binding | No | TASK171 `NativeIdentity`; upstream TASK021 materialization | E |
| TASK022 bundle geometry identity | R118-D accepted | Yes as upstream bundle geometry binding | No | TASK171 `NativeIdentity`; upstream TASK022 materialization | E |
| TASK024 baffle geometry identity | R118-D accepted | Yes as physical event/boundary source | No | TASK171 Definition and R119-D native result | E |
| TASK025 tube-side geometry identity | R118-D accepted | Yes as area/length/position source | No | TASK171 `NativeIdentity`; upstream TASK025 materialization | E |
| R119-C thermal-role selection | Variant A effective: tube HOT, shell COLD | Yes | No | Effective TASK171 Definition and R119-C authority | E |
| Fluid/service identity for topology-only structure | Not bound | No | No | TASK171 structural Definition has no fluid ID field | D |
| Fluid/service identity for thermal property evaluation | Not bound | Yes for executable thermal calculation | Yes | TASK160 `RatingStreamInput.fluid_or_service_identity`; shell flow authority fluid ID | A |
| Property source/profile snapshots for TASK172 | No case-bound property snapshots/profile | Yes for local property evaluation; exact Task172 schema absent | Yes | TASK170 TASK172 responsibility; TASK160 property snapshot; Task172 API absent | A |
| Property snapshots for TASK173 | No case-bound snapshots | Yes for rating path | Yes before TASK173 | TASK160 → TASK162 → TASK163 result chain | B |
| Property snapshots for TASK174 | No case-bound snapshots | Yes for hydraulic properties | Yes before TASK174 | Shell flow state and pressure-drop contracts; no Task174 aggregate API exists | B |
| Material identity, property body, temperature-domain coverage | Required case-level chain absent | Yes for wall/material closure | Yes | Material canonical blocker adjudication; future TASK172 fail-closed gate | A |
| Wall/fouling/material thermal authority | No case-bound instance | Yes for wall closure | Yes | TASK172 local constitutive architecture and material/wall contract | A |
| Tube/shell HTC and wall-correction applicability | Model-level review exists; case applicability is not bound | Yes for local heat-transfer closure | Yes | TASK172 responsibility; existing correlation/property contracts | A |
| Inlet temperature/pressure, phase, and thermal boundary states | No case operating record supplied | Yes for executable thermal state | Yes | TASK160 raw/typed stream input; TASK172 local state contract | A |
| Mass-flow inputs and hydraulic state | No case authority supplied | Yes for thermal/hydraulic calculation | Yes | TASK160 stream input; shell-side mass-flow authority | A |
| Aggregate `GEOMETRY_ID` for TASK172 runtime | `UNBOUND`; no reviewed aggregate contract | No native TASK172 consumer found | No direct runtime blocker | No TASK172 API exists; R119-D explicitly says no native aggregate output | D |
| Aggregate `GEOMETRY_ID` for real-case mesh admission | `UNBOUND`; admission contract lists it as prerequisite | Not a TASK172 field; required by admission contract | Yes before production mesh admission | Real-case mesh-admission contract prerequisite list | C |
| Case-specific executable numerical profile | R94 model-level profile reviewed; executable production profile not bound | Yes for deterministic numerical closure | Yes for production runtime | R94 profile state and TASK170 convergence/numerical responsibility | A |
| Real-case mesh profile/admission | Not bound; R103 is synthetic-fixture scope only | Not needed for structural implementation; needed for real-case execution | Yes before production real-case use | Real-case mesh-admission predicate | C |
| Reference-policy case applicability and requirement resolution | Unresolved | No direct runtime API consumer; required by admission predicate | Yes before production mesh admission | R107 predicate; R111/R112 binding remains unbound | C |
| Standalone native scalar `TOPOLOGY_AUTHORITY_ID` | Not emitted; reviewed authority IDs are in Definition | No, not a native TASK171 output field | No as a synthetic scalar | R119-E and TASK171 `Definition.authority_ids` | D |
| TASK174 local-loss/Bell allocation/operability/FIV authority | Not complete/materialized | No for TASK172 local closure; yes for TASK174 | Yes before TASK174 and integrated TASK173 | TASK170 §22; task-specific aggregate implementation absent | B |
| TASK173 boundary solver, constraints, ranking, alternatives | Not implemented/materialized | No for local TASK172 closure; yes for complete rating/sizing | Yes before TASK173 completion | TASK170 §22; Task163 is a lower-level composition contract | B |
| TASK175 Golden/release/parity acceptance | Not performed | No for TASK172 runtime; yes for release | Yes before release | TASK170 §22 | C |

Exactly six current real-case TASK172 runtime blockers are tracked as bundles:

1. Native TASK172 runtime/API implementation is absent.
2. Case stream identities, phase, inlet/boundary state, mass flows, and valid property snapshots are absent.
3. Case-bound material identity/property body and temperature-domain coverage are absent.
4. Case-bound wall/fouling/HTC/correction applicability is absent.
5. A production-executable numerical profile is not bound to this case; the R94 reviewed profile is model-level and explicitly not an executable production profile.
6. Real-case mesh/admission is unresolved: production mesh profile and policies are unbound, reference-policy resolution is false, and the admission contract's aggregate-geometry prerequisite has no reviewed identity contract.

The following are not additional TASK172 blockers: the accepted R118-D native identities and selected thermal role; a fabricated aggregate geometry ID; a live continuous-reference oracle for the scoped profile; or TASK174/TASK173/TASK175 results before TASK172 runtime construction. Those later tasks have their own ordered prerequisites.

## Required project-owner decision bundles

All presently identifiable project-owner choices and authority/data submissions are collected here; this audit does not ask them one at a time and does not choose values.

1. **Case streams and operating point:** identify the actual tube- and shell-side fluid/service and phase; provide source-bound inlet temperatures and pressures, mass-flow values/sign conventions, and the relevant local/terminal boundary-condition data.
2. **Property package:** select the reviewed property-source/profile and provide case-domain snapshots with source/version/evaluation context for both streams; no runtime lookup/default is substituted.
3. **Material and local constitutive package:** provide reviewed material identity/property body/domain, wall and fouling assumptions, tube/shell HTC correlation applicability, wall corrections, and required source/license/evidence bindings.
4. **Numerical and real-case admission package:** bind the case-executable residual/iteration/failure profile and initial/refinement/convergence/resource/wall policies; resolve the case-applicable reference-policy and production-reference-requirement slots; determine whether the admission contract's `GEOMETRY_ID` prerequisite can be met by a separately reviewed aggregate identity contract or needs a separately authorized contract correction. No geometry ID is fabricated here.
5. **TASK174 hydraulic/operability package:** decide/submit source-bound tube loss, shell aggregation, variable-property pressure coupling, and FIV requirement/applicability evidence as one reviewed authority bundle.
6. **TASK173 rating/sizing package:** provide the approved thermal/DP constraints, candidate filtering, ranking/recommendation and alternative-selection requirements as one reviewed solver authority bundle.
7. **TASK175 release package:** bind the approved Golden set, V06 bridge scope, trusted cross-runtime parity matrix and release gate acceptance inputs together; TASK170 currently calls for six independently approved V07 fixtures, parity, 24 gates and end-to-end acceptance.

Items 1–4 are the pre-runtime authority-closure intake for a real case. Items 5–7 are grouped future-stage decisions and do not block implementation-only work beyond their respective stages.

## G. Finite consolidated roadmap

The repository's frozen dependency order is `TASK171 → (TASK172 || TASK174) → TASK173 → TASK175`; TASK172 and TASK174 may develop in parallel, and TASK173 requires both closures. The roadmap groups those responsibilities into four finite major stages, not a chain of micro-gates:

| Major stage | Scope and exit | Remaining owner bundle |
| --- | --- | --- |
| **STAGE 1 — PRE_RUNTIME_AUTHORITY_CLOSURE** | Close the grouped case streams/property/material/wall/correlation/numerical/mesh-admission bindings and any necessary aggregate-identity contract decision; independent review the consolidated bundle. | Owner bundles 1–4 above. This is the single next gate. |
| **STAGE 2 — TASK172_RUNTIME_AND_TASK174_HYDRAULICS** | Implement and validate TASK172 local property/wall/convergence closure and TASK174 detailed hydraulics/operability against TASK171; they may proceed in parallel after their inputs are authorized. | Owner bundle 5 and implementation authorization. |
| **STAGE 3 — TASK173_RATING_SIZING_INTEGRATION** | Integrate the completed TASK172 and TASK174 outputs, solve the exchanger boundary problem, apply approved constraints/ranking, and replay deterministically. | Owner bundle 6. |
| **STAGE 4 — TASK175_GOLDEN_AND_RELEASE_ACCEPTANCE** | Bind and pass approved Golden/V06 bridge, cross-runtime parity, required release gates and end-to-end acceptance. | Owner bundle 7. |

```ini
REMAINING_MAJOR_STAGE_COUNT=4
STAGE_1=PRE_RUNTIME_AUTHORITY_CLOSURE
STAGE_2=TASK172_RUNTIME_AND_TASK174_HYDRAULICS
STAGE_3=TASK173_RATING_SIZING_INTEGRATION
STAGE_4=TASK175_GOLDEN_AND_RELEASE_ACCEPTANCE
NEXT_GATE=PRE_RUNTIME_AUTHORITY_CLOSURE
```

This is the one consolidated roadmap recommendation. It does not authorize any stage to begin automatically.

## Governance and change boundary

```ini
R119E_REVIEW_SOURCE=USER_SUPPLIED_EXTERNAL_INDEPENDENT_REVIEW_DECISION
R119E_SELF_APPROVAL=false
TASK171_NATIVE_PRODUCER_INVOCATION_COUNT=0
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
GEOMETRY_ID=UNBOUND
FLUID_IDENTITY_BOUND=false
PROPERTY_PROFILE_AUTHORITY_ID=UNBOUND
PRODUCTION_MESH_PROFILE_AUTHORITY_ID=UNBOUND
REAL_CASE_MESH_ADMISSIBLE=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
PRODUCTION_CODE_CHANGED=false
EXISTING_TESTS_CHANGED=false
DEPENDENCIES_CHANGED=false
LOCKFILES_CHANGED=false
WORKFLOWS_CHANGED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
STOP=true
```
