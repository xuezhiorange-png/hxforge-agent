# TASK172 v0.7 — Stage 1 Pre-Runtime Authority Bundle R1

```ini
TASK_ID=TASK172_V0_7_STAGE1_PRE_RUNTIME_AUTHORITY_CLOSURE_R1
MODE=CONSOLIDATED_PRE_RUNTIME_AUTHORITY_CLOSURE
PREDECESSOR_HEAD=c60fc5d50b1ec1bc16c3b800fc94d9d382bfacd8
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
RESULT=AWAITING_SINGLE_PROJECT_OWNER_DECISION_PACKAGE
STAGE_1_STATUS=PREPARATION_COMPLETE_AWAITING_OWNER_PACKAGE
PROJECT_OWNER_DECISION_COUNT=12
TASK171_STATUS=VALIDATED
SELECTED_VARIANT=TUBE_HOT_SHELL_COLD
CASE_STREAM_AUTHORITY_BOUND=false
PROPERTY_PACKAGE_BOUND=false
MATERIAL_WALL_CONSTITUTIVE_AUTHORITY_BOUND=false
CASE_EXECUTABLE_NUMERICAL_PROFILE_BOUND=false
GEOMETRY_ID=UNBOUND
PRODUCTION_MESH_PROFILE_AUTHORITY_BOUND=false
REFERENCE_POLICY_RESOLUTION_VALID=false
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLVED=false
REAL_CASE_MESH_ADMISSIBLE=false
TASK172_RUNTIME_READY_AFTER_STAGE1=false
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
STOP=true
```

## Scope and disposition

This is one Stage-1 closure package, not a new sequence of micro-gates. It reuses the reviewed R119-E TASK171 materialization, R119-C thermal-role selection, the R119-A/B structural ownership authorities, and reviewed model-level property, material, correlation, numerical, and reference-oracle decisions. It does not repeat producer runs, modify prior R119 evidence, bind absent operating data, implement runtime, or admit a production mesh.

The exact native code/evidence inspection found genuine case-specific gaps in the four requested owner bundles. Therefore the Stage-1 result is `AWAITING_SINGLE_PROJECT_OWNER_DECISION_PACKAGE`, not complete. All 12 missing choices are gathered in one returnable sheet at [the project-owner decision package](TASK-172-v0.7-stage1-project-owner-decision-package-r1.md). No already-resolved field is included as an owner question.

## Frozen predecessor and reused authorities

The repository HEAD was `c60fc5d50b1ec1bc16c3b800fc94d9d382bfacd8`; PR #283 was OPEN + Draft. R119-E is an externally supplied independent review PASS (`SELF_APPROVAL=false`, `CODEX_SELF_APPROVAL_CLAIMED=false`). The accepted TASK171 result is `VALIDATED`, with topology ID `urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7`, mesh identity `ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607`, and physical ownership hash `63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe`.

Reused without rewriting or cloning:

- thermal-role selection: `V07-T172-R119C-THERMAL-ROLE-SELECTION-R1`; selected Variant A, tube HOT / shell COLD;
- accepted TASK020 configuration, TASK021 layout, TASK022 bundle, TASK024 baffle, TASK025 tube-side identities and hashes;
- `V07-T172-R119A-FLOW-PATH-MAPPING-R1`, `V07-T172-R119A-PHYSICAL-COMPARTMENT-MAPPING-R1`, `V07-T172-R119A-AREA-OWNERSHIP-R1`, `V07-T172-R119A-LENGTH-OWNERSHIP-R1`, and `V07-T172-R119A-TASK171-MESH-R1`;
- TASK171's accepted canonical project-internal path directions: tube 0→6 and shell 6→0;
- model-level water/property, clean-wall, material-identity, constant-k, material-blocker-closure, tube-wall-correction branch-closure, tube C3, shell JMu, R94/R98 numerical, and R110 no-mandatory-online-oracle decisions, each limited to its reviewed scope. The reviewed water profile is conditional on pure ordinary water, HEOS/CoolProp 8.0.0, DEF reference state, stable single-phase liquid, 298.15–300 K, and 100000–101325 Pa; it is not bound to either case stream.

Reusing a model-level equation or a scoped oracle decision does not establish that the selected case fluid, state, material, correlation branch, or production mesh lies within its applicability envelope.

## Consolidated authority matrix

The machine-readable `authority_matrix` in the linked evidence file is the single field-level inventory. Each field has exactly one classification. The key findings are:

It contains 81 fields: 23 `REUSED_REVIEWED_AUTHORITY`, 9 `REUSED_REVIEWED_CASE_VALUE`, 2 `NATIVE_CONTRACT_CONSTANT`, 1 `DERIVED_FROM_REVIEWED_INPUTS`, 43 `PROJECT_OWNER_DECISION_REQUIRED`, and 3 `NOT_APPLICABLE`. The 43 unresolved fields are consolidated into the 12 owner decisions below; a field count is not a count of separate owner decisions.

| Bundle | Resolved without new choice | Still unbound | Status |
| --- | --- | --- | --- |
| Case streams and operating point | HOT/COLD roles, side identities, reviewed graph directions, accepted geometry/topology inputs | Actual fluid/service and phase; source-bound inlet/boundary states; mass-flow magnitudes and operating evidence | Owner decision required |
| Property source and case domain | Native property snapshot/provider shapes; reviewed water profile/domain as a conditional model authority | Per-side source selection, case snapshots, T/P/phase domain and provenance | Owner decision required |
| Material, wall and constitutive | Conditional clean-wall, material contract, tube C3 and shell JMu model authorities | Actual material/property body/domain, surface/fouling state and case correlation applicability | Owner decision required |
| Numerical and real-case admission | R94 controls/R98 overlay and R110 scoped `online_continuous_reference_oracle_required=false` | Case execution-profile binding, production mesh policy, case reference-policy/oracle resolution, and admission geometry-contract correction | Owner decision required |

## Reusable numerical contract and its boundary

R88 fixes the model-level local unknowns as `x=[q_hc, T_wall_inner, T_wall_outer]`, with `q_ts=s_ts*q_hc`, and three physical residuals:

```text
r_i = q_ts - h_i(T_wall_inner, located tube state, admitted tube profile)
             * A_i * (T_tube_bulk - T_wall_inner)
r_w = q_ts - (T_wall_inner - T_wall_outer) / R_wall
r_o = q_ts - h_o(T_wall_outer, located shell state, admitted shell profile)
             * A_o * (T_wall_outer - T_shell_bulk)
```

They remain physical heat-rate residuals in watts. R94’s reviewed model-level numerical profile uses bounded trust-region vector least squares (`method=trf`, linear loss), `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`, a two-point Jacobian with `diff_step=1e-5`, initialization-derived variable scaling, `abs(q_ts_seed)` residual scale (with a separate exact-zero branch), `max_nfev=6`, callback cap 24, exact trust-region solver, `tr_options={}`, `f_scale=1`, and no sparsity pattern. R98’s `C_round=1.0` overlay is retained only in its reviewed mesh-cell-scale scope; neither it nor the R103 synthetic qualification establishes real-case convergence.

The reviewed initialization is staged: I0 validates all input identities/domains/authorities before a seed; I1 may use neutral `J_mu=1.0` only as an initialization seed and a deterministic algebraic seed; I2 restores the full active physical equations before any accepted result. A neutralized seed is never the accepted physics. No separate under-relaxation or fixed-point control is specified for this simultaneous vector solve. Solver success alone is not acceptance; unacceptable residuals, cap exhaustion, invalid trials, missing properties, or domain exits fail closed, use typed failure paths, and cannot return authoritative partial output. No extrapolation, clipping, or penalty residual is allowed. The model-level signed `q_hc` permits negative values numerically, but its applicability disposition is still unbound and must be resolved from this case’s accepted state/correlation package, not clamped or inferred.

These controls may be reused unchanged only if the case package confirms the reviewed scope (clean wall, applicable reviewed tube and shell branches, and reviewed property domain). The project-specific execution-profile binding and real-case mesh/refinement/convergence/resource policies remain unbound; D1 and D2 capture that distinction.

## Geometry identity contract resolution

Disposition: `C_ADMISSION_CONTRACT_REQUIRES_CORRECTION_BECAUSE_AGGREGATE_ID_HAS_NO_NATIVE_SEMANTICS`.

No native TASK171 output or reviewed aggregate-geometry contract supplies a single aggregate `GEOMETRY_ID`. The Stage-1 audit has already established that a scalar aggregate ID is not required before TASK172 runtime. The real-case mesh-admission checklist nevertheless includes that scalar prerequisite. This bundle proposes—but does not enact—a contract correction that binds a structured, role-labelled collection of the accepted native identity references (case/configuration, layout, bundle, baffle, tube-side result, topology/result, structural mesh, and physical ownership) with their actual native identifiers/hashes. It preserves each identifier's native semantic role and creates no new scalar, hash, alias, or concatenation. Project-owner acceptance and the applicable review are still required before mesh admission. `GEOMETRY_ID` remains `UNBOUND`.

## Stage-1 readiness after this submission

Because the owner package is pending, case streams, property package, material/wall/constitutive binding, executable numerical profile, production mesh profile, and case-specific reference policy remain unbound. The reviewed online continuous reference-oracle requirement remains false for its existing scope, but the admission predicate's case-specific resolution is not complete. Real-case mesh admission remains false. TASK172 runtime readiness remains false, and this authority-only task does not authorize implementation or execution.

## Finite roadmap

The only next gate is the remainder of Stage 1: return and review the complete four-bundle owner-decision package, then bind the accepted values and resolve the admission-contract correction together. Do not split it into R119F/R119G/R119H or other micro-gates. Only after Stage 1 closes may the next major stage be considered: `STAGE_2_TASK172_RUNTIME_AND_TASK174_HYDRAULICS` (implementation authorization still required; these may proceed in parallel after their inputs are authorized). Stage 3 is TASK173 after TASK172/TASK174 closure; Stage 4 is TASK175 release acceptance.

## Change and execution boundary

No production code, tests, dependencies, workflows, lockfiles, R119-A/B/C/D/E artifacts, or reviewed engineering values were changed. No TASK172/TASK174/TASK173/TASK175 runtime/solve was executed. No production mesh was admitted. `STOP=true`.
