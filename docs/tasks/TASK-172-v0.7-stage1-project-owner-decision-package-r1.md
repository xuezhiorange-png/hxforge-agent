# TASK172 v0.7 — Stage 1 Project-Owner Decision Package R1

```ini
TASK_ID=TASK172_V0_7_STAGE1_PRE_RUNTIME_AUTHORITY_CLOSURE_R1
MODE=SINGLE_CONSOLIDATED_PROJECT_OWNER_DECISION_PACKAGE
RESULT=AWAITING_SINGLE_PROJECT_OWNER_DECISION_PACKAGE
DECISION_COUNT=12
PREDECESSOR_HEAD=c60fc5d50b1ec1bc16c3b800fc94d9d382bfacd8
TASK171_STATUS=VALIDATED
SELECTED_VARIANT=TUBE_HOT_SHELL_COLD
TUBE_SIDE_ROLE=HOT
SHELL_SIDE_ROLE=COLD
GEOMETRY_ID=UNBOUND
TASK172_RUNTIME_IMPLEMENTATION=false
STOP=true
```

## How to return this package

Return one completed copy of the 12 decision rows below in a single project-owner response. Supply source/evidence references with each value. A row may be answered `NOT_APPLICABLE` only with a case-specific reason and evidence. Do not send decisions one at a time. This package is not itself an authority approval; submitted values require the repository’s applicable review and binding process before runtime use.

The accepted tube-HOT/shell-COLD role, side-path orientation, TASK020–TASK025 identities, TASK171 topology and structural mesh, and the reviewed model-level authorities are already fixed and are intentionally omitted from owner questions.

## A_CASE_STREAMS_AND_OPERATING_POINT

| # | Decision | Existing evidence | Exact native consumer | Allowed/valid form | Project owner value |
| --- | --- | --- | --- | --- | --- |
| A1 | Identify the actual tube-side and shell-side fluid or service, and the phase of each stream for this case. | R119-C fixes thermal roles, not substance identities or phase; no reviewed case operating record supplies these. | `Task160RawStreamInput` / `RatingStreamInput`; shell-side flow-state authority. | Source-bound identity for each side and `SINGLE_PHASE_LIQUID` or `SINGLE_PHASE_GAS`, with evidence identifying the actual service. | **OWNER: fill both sides and evidence.** |
| A2 | Supply each side’s inlet temperature, inlet absolute pressure where applicable, mass-flow magnitude, and the sign/direction convention. | TASK171 path directions are reviewed graph orientation only; no case operating-point values are accepted. | TASK160 typed stream input; shell-side mass-flow and pressure-state contracts. | Finite positive absolute temperature; positive absolute pressure when the selected property context requires it; positive mass-flow magnitude. Direction remains bound to the reviewed side path, not encoded by a negative magnitude. Include measurement/design source, units, uncertainty/status, and evidence. | **OWNER: fill tube and shell values and evidence.** |
| A3 | State the required outlet/terminal boundary conditions and whether they are measured inputs, specified constraints, or outputs to be solved; provide any source-bound duty/endpoint data required by the selected formulation. | No independent outlet, duty, or boundary-condition record is present. TASK162-computed outlets are model outputs, not independent case evidence. | TASK172 local state/boundary closure (implementation absent); TASK160/TASK162 stream contracts where used. | Explicitly label every condition `measured_input`, `specified_boundary`, `constraint`, `solve_output`, or `NOT_APPLICABLE`, with source and units. Do not treat a calculated outlet as measured data. | **OWNER: fill conditions and evidence, or justify NOT_APPLICABLE.** |

## B_PROPERTY_SOURCE_AND_CASE_DOMAIN

| # | Decision | Existing evidence | Exact native consumer | Allowed/valid form | Project owner value |
| --- | --- | --- | --- | --- | --- |
| B1 | Select the actual property source/profile or method independently for each stream and bind its version and provenance. | The reviewed water profile is model-level and conditional: pure ordinary water, HEOS/CoolProp 8.0.0, DEF reference state, stable single-phase liquid, 298.15–300 K and 100000–101325 Pa; no case fluid selection exists. | TASK160 `Task160PropertySnapshot`; tube thermal and shell hydraulic property-state contracts. | Reuse the reviewed water source only if A1 and the case domain match exactly; otherwise submit a source-backed candidate with provider/version/license/source identity. Do not mint a profile ID without a native profile/snapshot contract. | **OWNER: specify both sides’ source/method and evidence.** |
| B2 | Bind case-domain property snapshots and the valid T/P/phase envelope for the chosen operating states. | No per-stream case snapshots or case-domain proof are bound. Native contexts include recorded snapshots and temperature-only or temperature-plus-pressure evaluation. | TASK160 requires cp, source identity/version, snapshot identity and evaluation context; tube-local and shell-flow consumers use density, viscosity, conductivity and cp. The property provider exposes enthalpy/entropy, but no current TASK172 consumer contract establishes those as universal required inputs. | Provide typed snapshot/reference-state semantics, exact state coordinates and provenance; include every property the selected native consumer requires (at least cp for TASK160 and rho/mu/k/cp for the inspected local/hydraulic contracts). Include enthalpy/other outputs only where the selected consumer contract requires them. Define T/P/phase validity and failure behavior from the selected source. | **OWNER: provide snapshots/domain and evidence for both sides.** |

## C_MATERIAL_WALL_AND_LOCAL_CONSTITUTIVE

| # | Decision | Existing evidence | Exact native consumer | Allowed/valid form | Project owner value |
| --- | --- | --- | --- | --- | --- |
| C1 | Bind the actual tube-wall material identity, material property source/body, conductivity model, temperature domain, and linkage to the accepted TASK021/TASK025 tube geometry. | Material identity and constant-conductivity authority contracts are reviewed at model level; no case material record/body/domain is bound. | TASK172 wall/local constitutive closure; reviewed material-property contract. | Source-backed material identity plus property body/function and validity range tied to the accepted wall geometry. A test material or fixture is not valid evidence. | **OWNER: identify material/property record and evidence.** |
| C2 | Specify the case wall/surface condition and tube-/shell-side fouling or other surface resistance values, including whether any are nonzero. | The reviewed clean-wall network is conditional model authority, not a case assertion that surfaces are clean or fouling is zero. | TASK172 wall resistance network and local heat-transfer closure. | Explicit side-specific values/units, location, temperature dependence if any, source and applicability; zero requires affirmative case evidence, not omission. | **OWNER: provide wall/surface and resistance state with evidence.** |
| C3 | Bind the reviewed tube/shell heat-transfer correlations and correction branches to this case, including applicability evidence for Reynolds/Prandtl/property domains and wall corrections. | Tube C3, shell JMu, and correction authorities are model-reviewed, with finite applicability envelopes; case properties/flow and therefore case applicability are not established. | TASK172 local HTC/constitutive evaluation; tube C3 and shell JMu/correction contracts. | Identify the applicable reviewed branch/correlation per side and provide source-bound evidence that the state lies within its envelope; explicitly fail closed for transition/out-of-domain conditions. | **OWNER: supply the case applicability binding/evidence; do not select a correlation outside reviewed scope.** |

## D_NUMERICAL_AND_REAL_CASE_ADMISSION

| # | Decision | Existing evidence | Exact native consumer | Allowed/valid form | Project owner value |
| --- | --- | --- | --- | --- | --- |
| D1 | Bind a case-executable numerical profile, including the still-open signed negative-local-heat-rate applicability: confirm applicability of reviewed R94/R98 controls or submit a reviewed alternative if this case is outside scope. | R94 model profile and R98 residual-scale overlay are reviewed; R103 qualification is synthetic-scope only. R88/R94 allow signed negative heat numerically but leave case applicability unbound. | TASK172 numerical closure (not yet implemented); real-case mesh admission numerical-profile slot. | If applicable, bind unchanged reviewed method/controls and provide the state/correlation evidence resolving signed negative-q applicability without clamping or role reassignment. The reviewed profile has `trf`, linear loss, `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`, 2-point Jacobian, `diff_step=1e-5`, initialization-derived scale, `abs(q_ts_seed)` residual scale, `max_nfev=6`, callback cap 24, exact trust-region solver, and effective R98 `C_round=1.0`. No separate under-relaxation is specified. Otherwise provide a separately reviewed profile; do not copy synthetic thresholds/resource settings. | **OWNER: affirm case fit and signed-q disposition with evidence or submit alternate profile candidate.** |
| D2 | Bind the real-case production mesh/admission package: case-bound profile, initial mesh, refinement, convergence, resource, mesh-wall acceptance, and mapping policies. | TASK171 `mesh_identity` is accepted structural identity only. R103 does not transfer a real-case production profile; admission slots remain unbound. | Real-case mesh-admission predicate; production mesh profile authority. | Complete, internally consistent, source-backed policy package that respects accepted topology/ownership and exact case validity; no test fixture/default promotion. The mesh-wall acceptance slot is distinct from the physical material/wall/fouling package in C1–C2. | **OWNER: provide one complete mesh/admission candidate and evidence.** |
| D3 | Resolve case-specific reference-policy applicability and the production-reference requirement resolution for admission. | R110 already reviews online continuous oracle as not mandatory for its scoped profile; it does not make all comparisons inapplicable or resolve this case’s predicate. | R107 composite admission predicate: `reference_policy_applicability_resolution_valid AND production_reference_oracle_requirement_resolution_valid`. | Bind a case-applicable comparison/reference policy and resolve the reviewed online requirement for this case/profile without changing the reviewed `online_continuous_reference_oracle_required=false` decision or introducing an unapproved oracle. | **OWNER: provide the case/profile applicability disposition and evidence.** |
| D4 | Accept or reject the proposed correction to the real-case admission contract’s scalar aggregate `GEOMETRY_ID` prerequisite. | TASK171 natively emits topology/result/mesh/ownership identities, not aggregate `GEOMETRY_ID`; R119-D leaves it unbound. Audit confirms no aggregate ID is required before TASK172 runtime, but the separate mesh-admission checklist lists one. | Real-case mesh-admission contract prerequisite list and admission identity binding. | Proposed correction C: replace the scalar with an explicit structured, role-labelled set of already reviewed native identity references and hashes; preserve their native meanings. No concatenation, alias, or synthetic aggregate hash. Acceptance/review is required before admission. | **OWNER: accept/reject the structured-reference contract correction; provide rationale/evidence.** |

## Decision boundary

The reviewed case thermal roles and R119-E materialized topology are accepted inputs. No fluid name, stream state, mass flow, material, fouling value, case-applicable correlation, production numerical profile, mesh policy, or reference-policy applicability is inferred. The accepted `production_reference_oracle_required=false` is reused as a scoped reviewed decision; D3 is only the still-missing case/profile resolution. `GEOMETRY_ID` remains `UNBOUND` and is not a TASK172 runtime blocker.

Return the complete package once. Until its decisions are reviewed and bound, the consolidated Stage-1 authority bundle remains pending and no TASK172/TASK173/TASK174/TASK175 runtime or solve is authorized.
