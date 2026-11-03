# TASK172 v0.7 — Stage 1 Pre-Runtime Authority Bundle R1

```ini
TASK_ID=TASK172_V0_7_STAGE1_REAL_CASE_PRODUCTION_MESH_POLICY_CLOSURE_R1
MODE=CONSOLIDATED_OWNER_AUTHORITY_BINDING_AND_REAL_CASE_MESH_POLICY_CLOSURE
PREDECESSOR_HEAD=5905e262172a4660f1fe53823af79c090e46883f
PR_NUMBER=283
PR_STATE=OPEN_DRAFT
PREVIOUS_BLOCKER=BLOCKED_PROFILE_BINDING_SEMANTICS
PREVIOUS_BLOCKER_RESOLVED=true
RESULT=STAGE1_AUTHORITY_BUNDLE_COMPLETE_PENDING_SINGLE_INDEPENDENT_REVIEW
STAGE_1_STATUS=COMPLETE_PENDING_SINGLE_INDEPENDENT_REVIEW
PROJECT_OWNER_DECISION_PACKAGE_COMPLETE=true
PROJECT_OWNER_DECISION_COUNT=12
PROJECT_OWNER_DECISION_COUNT_REMAINING=0
PRODUCTION_MESH_PROFILE_AUTHORITY_ID=V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1
PRODUCTION_MESH_PROFILE_AUTHORITY_BOUND=true
REAL_CASE_MESH_ADMISSIBLE=false
GEOMETRY_ID=UNBOUND
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE1_SINGLE_INDEPENDENT_REVIEW
STOP=true
```

## Scope, source and lifecycle

This is one consolidated Stage-1 authority bundle. The previously accepted `BLOCKED_PROFILE_BINDING_SEMANTICS` was the one remaining mesh-policy issue. The project owner has now supplied the normalized real-case production mesh policy and all twelve A1–D4 decisions. No owner decision remains outstanding. The result is complete as a candidate bundle, pending the repository's one independent review of the entire Stage-1 package. It is not self-approved: `SELF_APPROVAL=false`, `CODEX_SELF_APPROVAL_CLAIMED=false`.

Owner decisions are source-classified as `USER_SUPPLIED_PROJECT_OWNER_ENGINEERING_DECISION` for the `PROJECT_DESIGNED_ENGINEERING_REFERENCE_CASE`. This is not a measured or as-built plant case and is not a synthetic fixture. The filled [owner decision record](TASK-172-v0.7-stage1-project-owner-decision-package-r1.md) contains the twelve decisions once, without reopening any earlier values.

The exact predecessor remains `5905e262172a4660f1fe53823af79c090e46883f`; PR #283 is OPEN + Draft. R119-E remains an externally supplied independent-review PASS. Its artifacts and R119-A/B/C/D/E records are unchanged. No TASK171 producer was called in this Stage-1 closure.

## Frozen accepted native case and reviewed structural authorities

The accepted case remains `V07-T172-PROJECT-ENGINEERING-REFERENCE-CASE-R1`, effective thermal role selection `V07-T172-R119C-THERMAL-ROLE-SELECTION-R1`, selected Variant A (`TUBE_HOT_SHELL_COLD`), tube HOT and shell COLD. Reused unchanged native IDs/hashes are:

| Native identity | ID | Hash |
| --- | --- | --- |
| TASK020 configuration | `96637b2b-3583-5fdd-8645-bb2b5526996a` | `04fbacd4037e4740328dd76b01caa0e85f22569924308d74b35bb13f0beb9125` |
| TASK021 layout | `55b3085c-6a2a-5394-8617-7102e7eb66a8` | `1dabd4362cc0c446da892bfe92b48fc6066b01ab3ca037d31ff4213e91fcc550` |
| TASK022 bundle geometry | `cbacec31-31fa-5e14-aa1b-be05e04b96dc` | `2384f3b31b279dac696951372d4b4781c58b8594c4d09091ec1a5cdaab7049f4` |
| TASK024 baffle geometry | `279ed479-378d-5ea5-b2f0-8926133bf4dd` | `68efd0e8dc69f203d49b73b2a87106863725d9a1b4a9bf1282cc1f650942d994` |
| TASK025 tube-side result | `6ff54552-d44e-50d2-bdf2-fe5b766c6ff9` | `b74a037507e525e1ec647ac6a594e3723f0de07965e916b7a2eb1bb9de4dfc2a` |
| TASK171 topology/result | `urn:hxforge:task171:98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7` | `98b4bb0ce1d209b6e19ae313330b1a8d5692b2398967586d4edc1e368e9345a7` |
| TASK171 structural mesh | `ec4a01bbfe81cd6b12ede63c6f4e4aa05372414868cee54a54fb7c98aaffd607` | — |
| TASK171 physical ownership | — | `63ea9cb1d10037dde273fc40746d6cf98604a40e41d91705f640031e5b6ec7fe` |

Reused governance identities remain `V07-T172-R119A-FLOW-PATH-MAPPING-R1`, `V07-T172-R119A-PHYSICAL-COMPARTMENT-MAPPING-R1`, `V07-T172-R119A-AREA-OWNERSHIP-R1`, `V07-T172-R119A-LENGTH-OWNERSHIP-R1`, and `V07-T172-R119A-TASK171-MESH-R1`. Tube direction remains `0_TO_6`, shell direction `6_TO_0`, a project-internal graph orientation only.

## A — case streams and operating point

| Side | Fluid/service | Phase/role | Inlet T | Inlet absolute P | Mass flow | Sign/direction |
| --- | --- | --- | ---: | ---: | ---: | --- |
| Tube | Pure ordinary water / HOT_WATER | Single-phase liquid / HOT | 300.000000 K | 101325 Pa | +10.000000 kg/s | Positive magnitude along reviewed tube path; no negative encoding |
| Shell | Pure ordinary water / COLD_WATER | Single-phase liquid / COLD | 298.150000 K | 101325 Pa | +20.000000 kg/s | Positive magnitude along reviewed shell path; no negative encoding |

These are project design values, not measurements; measurement uncertainty is not applicable. No outlet temperature or duty is prescribed. Tube/shell outlet temperatures, local heat rate and TASK173 exchanger duty are solve outputs; pressure drops belong to TASK174. All solved states fail closed outside the authorized phase/property domain.

## B — property source and domain

Both streams bind to the reviewed `V07-T172-WATER-PROPERTY-PROFILE-R2`: Water, pure ordinary water, HEOS, CoolProp `8.0.0`, git revision `ae81610e7d23efc57f9d051c8e70a4d66e87537f`, reference state DEF, stable single-phase liquid. Existing property-profile hash and qualification lineage are referenced, not rewritten. Provider replay confirms configuration fingerprint `8d37dea32044ee8d`; provider validation level remains same-backend `SUPPORTED_TIER_1`, not an independent physical-accuracy claim.

Admitted domain is `298.15<=T<=300.00 K`, `100000<=P<=101325 Pa`, liquid only. Extrapolation, clipping, silent backend fallback, reference-state mutation and phase-boundary crossing are prohibited. Native inlet Task026 snapshot hashes are tube `984b3e72893b357535ed500294453b5e6b1f902a71a3c93357fe1a9978947819` and shell `e48b6a28f999e9cffc3cd873eeaede338c4de6ee16c897802bb19eeb41f23c19`. The 3×3 T/P grid returned liquid in all nine native CoolProp queries. The machine-readable evidence retains the exact snapshots, provider metadata and grid observations. Local states will use this same provider and fail closed outside the case domain.

## C — material, wall and local constitutive package

The tube wall is owner-designated 316L austenitic stainless steel, linked to accepted tube OD 0.01905 m, ID 0.01575 m and wall thickness 0.00165 m. A lawful Alleima Sanmac 316/316L manufacturer data sheet was fetched and SHA-256 bound in the evidence. Its approximate 20°C and 100°C conductivity values are source evidence; the case value `k=14.0 W/(m K)` over 298.15–300 K is explicitly the owner's conservative constant-k choice, not an assertion that the manufacturer specifies a constant throughout the interval.

The surface is explicitly CLEAN: tube and shell fouling resistances are zero, with no deposit, contact resistance or extra layer. This case-only decision reuses the reviewed clean-wall network and local cylindrical mapping.

Native exact inlet replay places the tube at Re `3742.675244246214513402808173`, Pr `5.855926514898839169263267261`, turbulent Gnielinski/C3; the native Pr envelope passes. The native shell central-crossflow screening replay gives Re `2740.5066088396428172796798450599375449393604657674`, Pr `6.1358049639094794150526865914303242471116943093648`; the reviewed shell screening lower-Re bound passes. The existing shell clean-profile Jμ formula and localized bulk/wall property mappings remain in force. These are applicability checks, not a local wall solve: no wall temperature, local heat-transfer coefficient or Jμ value is created here. The accepted branch/correction and property-domain checks fail closed during runtime if local states leave the reviewed envelope.

TASK037 replay returns outside/inside area ratio `1.209523809523810`; accepted total inside area is `75.1107679584 m²`, and the native Decimal-derived outside area is `90.848262197302892909889504 m²`.

## D1 — case-executable numerical profile

Bind reviewed R94/R98 controls unchanged: TRF / linear loss; `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`; two-point Jacobian and `diff_step=1e-5`; initialization-derived x-scale; residual scale `abs(q_ts_seed)` with the reviewed zero branch; `max_nfev=6`; callback cap 24; exact trust-region solver; `f_scale=1`; no Jacobian sparsity. Reuse reviewed staged initialization, residuals, scaling, acceptance, determinism and typed fail-closed failure/domain policies. No extra under-relaxation is specified. Owner binds effective `C_round=1.0` under the existing R98 formula, limited to this case. Negative q is numerically permitted but a negative physical heat-transfer solution is BLOCKED for this hot-tube reference case; no clamp, absolute-value direction, or role swap.

## D2 — real-case production mesh profile

Authority `V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1` is scoped to this designed case and sourced from the explicit project-owner policy. Lifecycle is `PROPOSED_AUTHORITY_REVIEW_PENDING`; the existing TASK171 structural mesh is not silently promoted to a production mesh.

Five physical supports are immutable: `[0,1.2]`, `[1.2,2.4]`, `[2.4,3.6]`, `[3.6,4.8]`, `[4.8,6]` m. Every interval is 1.2 m and retains its exact inside/outside area ownership. `n` is subdivisions per physical interval per side; n=1 reproduces the 10-cell/5-wall TASK171 base. Every n-level has 5n tube cells, 5n shell cells, 10n total numerical cells and 5n wall interfaces. Refinement doubles n by deterministic midpoint bisection within each interval, preserving event boundaries, support, physical owners, flow-path owners, area and length ownership. Corresponding tube/shell cells share the exact support and wall interface.

| n | Total cells | Wall interfaces |
| ---: | ---: | ---: |
| 1 | 10 | 5 |
| 2 | 20 | 10 |
| 4 | 40 | 20 |
| 8 | 80 | 40 |
| 16 | 160 | 80 |
| 32 | 320 | 160 |
| 64 | 640 | 320 |

This sequence is new owner authority, not R103 absolute counts. No R103 secondary sequence is required. R103 absolute counts, secondary alignment, synthetic cap/reference values, and automatic thresholds are not transferred; R103 remains supporting qualification evidence.

Production observables are total wall duty (exact child-to-parent conservative sum over common physical support) and the four wall-temperature extrema (`T_wall_inner_min/max`, `T_wall_outer_min/max`) reduced over the common case wall support. No cell-index matching, interpolation, nearest-neighbor mapping, mesh-average temperature/HTC or duty-per-cell normalization is permitted. Consecutive duty pairs use a 0.01 W near-zero switch/absolute threshold and otherwise 1% relative threshold. Each of four extrema must change by at most 0.01 K. These are new owner production thresholds informed by R103, not automatically transferred from it.

Comparison precision floors reuse local R94/R98 bounds: sum local duty bounds over applicable wall supports and use the maximum local temperature bound for each extrema. A comparison passes only when difference plus floor is within threshold, fails when difference minus floor exceeds threshold, and otherwise returns `PRECISION_FLOOR_UNRESOLVED`. R102 synthetic Q-reference/UQ values are not reused.

Two consecutive passing comparison pairs and one later passing headroom level are required. The candidate remains the selected mesh; headroom is evidence. The cap is n=64 / 640 cells / 320 interfaces, reserving n=64 for headroom and making n=32 the latest possible candidate. Failure to establish a candidate by n=32 returns `MESH_RESOURCE_EXHAUSTED` / `MESH_NOT_CONVERGED`; the cap is not raised and n=64 cannot be accepted without later headroom.

A producer-free TASK171 schema/resource stress check validated a strict Definition shape with 5 intervals, 2 paths, 640 cells, 320 wall interfaces, 2,560 states, 19 events and 3 provenance edges; native `MAX_RECORDS=4096` and `safe_model` node/depth guards passed. This is schema capacity evidence only; it is not a native producer run or convergence/admission result. Typed failure semantics include invalid parent-child mapping/coverage, physical-boundary crossing, overlap, missing observable authority, nonfinite comparison, unresolved precision floor, insufficient sequence, resource exhaustion and nonconvergence. No failed mesh is authoritative.

## D3 — reference policy and oracle requirement

Case-bind reviewed `V07-T172-REAL-CASE-REFERENCE-POLICY-R1` and `V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-R1`. Comparison is allowed but not required or forbidden. `production_reference_oracle_required=false`, continuous online oracle=false, specific online execution=false. R102 synthetic reference values are not transferred. The owner has explicitly confirmed the reviewed no-online-oracle policy applies to this case/profile. This resolves policy applicability in the candidate bundle but implements no oracle.

## D4 — aggregate identity contract correction

Disposition is `C_ADMISSION_CONTRACT_REQUIRES_CORRECTION_BECAUSE_AGGREGATE_ID_HAS_NO_NATIVE_SEMANTICS`: remove a scalar aggregate `GEOMETRY_ID` from the real-case admission prerequisite and use a structured, role-labelled reference set for TASK020 configuration, TASK021 layout, TASK022 bundle, TASK024 baffle geometry, TASK025 result, TASK171 topology/result/mesh/physical ownership, and the reviewed flow/compartment/area/length authorities. Native meanings remain separate; no composite hash, alias, UUID or aggregate scalar is created. The correction is an append-only Stage-1 candidate overlay and leaves historical R104/R107 artifacts unchanged.

## Closure state and boundary

```ini
CASE_STREAM_AUTHORITY_BOUND=true
PROPERTY_PACKAGE_BOUND=true
MATERIAL_WALL_CONSTITUTIVE_AUTHORITY_BOUND=true
CASE_EXECUTABLE_NUMERICAL_PROFILE_BOUND=true
REAL_CASE_MESH_NORMALIZATION_BOUND=true
REAL_CASE_MESH_REFINEMENT_OPERATOR_BOUND=true
REAL_CASE_MESH_SEQUENCE_BOUND=true
REAL_CASE_MESH_MAPPING_OPERATOR_BOUND=true
REAL_CASE_MESH_METRIC_BOUND=true
REAL_CASE_MESH_THRESHOLDS_BOUND=true
REAL_CASE_MESH_CONSECUTIVE_RULE_BOUND=true
REAL_CASE_MESH_HEADROOM_RULE_BOUND=true
REAL_CASE_MESH_RESOURCE_POLICY_BOUND=true
R98_REAL_CASE_APPLICABILITY_BOUND=true
PRODUCTION_MESH_PROFILE_AUTHORITY_BOUND=true
REFERENCE_POLICY_RESOLUTION_VALID=true
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLVED=true
REAL_CASE_MESH_ADMISSION_PREREQUISITES_RESOLVED=true
REAL_CASE_MESH_ADMISSIBLE=false
GEOMETRY_ID=UNBOUND
GEOMETRY_ID_UNBOUND_REASON=NO_REVIEWED_NATIVE_AGGREGATE_CASE_GEOMETRY_ID_CONTRACT
TASK172_RUNTIME_READY_AFTER_STAGE1=false
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
PRODUCTION_CODE_CHANGED=false
EXISTING_TESTS_CHANGED=false
DEPENDENCIES_CHANGED=false
WORKFLOWS_CHANGED=false
LOCKFILES_CHANGED=false
R119A_THROUGH_R119E_ARTIFACTS_REWRITTEN=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=STAGE1_SINGLE_INDEPENDENT_REVIEW
STOP=true
```

`REAL_CASE_MESH_ADMISSIBLE=false` is intentional: the policy and admission prerequisites are bound in a review-pending authority candidate, but no production mesh convergence/admission run occurred. This submission authorizes Stage-1 inputs only. It does not implement TASK172 or execute TASK174/TASK173/TASK175. The single next gate is independent review of this complete Stage-1 bundle; do not split the policy into micro-gates.
