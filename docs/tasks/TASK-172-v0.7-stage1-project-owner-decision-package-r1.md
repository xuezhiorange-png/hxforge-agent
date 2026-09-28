# TASK172 v0.7 — Stage 1 Project-Owner Decision Record R1

```ini
TASK_ID=TASK172_V0_7_STAGE1_OWNER_DECISION_AND_AUTHORITY_CLOSURE_R1
MODE=RECORD_COMPLETED_SINGLE_PROJECT_OWNER_DECISION_PACKAGE
RESULT=OWNER_DECISIONS_SUPPLIED_ALL_FIELDS_BOUND_IN_STAGE1_CANDIDATE
DECISION_SOURCE=USER_SUPPLIED_PROJECT_OWNER_ENGINEERING_DECISION
SOURCE_CLASS=PROJECT_OWNER_EXPLICIT_ENGINEERING_REFERENCE_CASE_DECISION
CASE_CLASS=PROJECT_DESIGNED_ENGINEERING_REFERENCE_CASE
PROJECT_OWNER_DECISION_PACKAGE_COMPLETE=true
PROJECT_OWNER_DECISION_COUNT=12
PROJECT_OWNER_DECISION_COUNT_REMAINING=0
SELF_APPROVAL=false
CODEX_SELF_APPROVAL_CLAIMED=false
EXTERNAL_AS_BUILT_CASE=false
MEASURED_PLANT_CASE=false
SYNTHETIC_TEST_FIXTURE=false
TASK171_STATUS=VALIDATED
SELECTED_VARIANT=TUBE_HOT_SHELL_COLD
GEOMETRY_ID=UNBOUND
TASK172_RUNTIME_IMPLEMENTATION=false
STOP=true
```

## Record status and scope

This document records the twelve project-owner decisions already supplied in the Stage-1 authorization, including the complete new real-case production mesh policy. It is not a request for more decisions, an independent review, a producer execution, or a production-mesh admission. The values describe a designed engineering reference case, not an installed, measured, or as-built exchanger. They remain a consolidated Stage-1 authority candidate pending the repository's single independent review.

The reviewed tube-HOT/shell-COLD roles, canonical path directions, accepted TASK020–TASK025 and TASK171 identities, and prior reviewed model authorities are reused. They are not counted as new owner decisions.

## A_CASE_STREAMS_AND_OPERATING_POINT

| # | Completed decision | Bound project value | Evidence/status |
| --- | --- | --- | --- |
| A1 | Fluid/service and phase by side | Tube: `PURE_ORDINARY_WATER`, `HOT_WATER`, `SINGLE_PHASE_LIQUID`; shell: `PURE_ORDINARY_WATER`, `COLD_WATER`, `SINGLE_PHASE_LIQUID` | Explicit project-owner reference-case decision. Thermal roles remain reviewed: tube HOT, shell COLD. |
| A2 | Inlet operating point and flow convention | Tube: 300.000000 K, 101325 Pa absolute, 10.000000 kg/s; shell: 298.150000 K, 101325 Pa absolute, 20.000000 kg/s | Project design values; measurement uncertainty not applicable. Positive mass-flow magnitudes travel along their reviewed paths; negative mass-flow encoding is false. |
| A3 | Outlet and terminal boundary intent | Tube and shell outlet temperatures, heat duty, TASK172 local heat rate and TASK173 exchanger duty are solve outputs. Tube/shell pressure drops are TASK174 outputs. | No independent outlet temperature or duty is prescribed. TASK172 must not invent one; solved states outside the admitted property/phase domain block. |

Reused path orientation is tube `0_TO_6`, shell `6_TO_0`. It is project-internal graph orientation, not plant nozzle or piping authority.

## B_PROPERTY_SOURCE_AND_CASE_DOMAIN

| # | Completed decision | Bound project value | Native replay/evidence |
| --- | --- | --- | --- |
| B1 | Property source, backend and profile | Both sides use `V07-T172-WATER-PROPERTY-PROFILE-R2`; Water, pure ordinary water, HEOS, CoolProp 8.0.0, git revision `ae81610e7d23efc57f9d051c8e70a4d66e87537f`, reference state DEF, stable single-phase liquid. | Existing reviewed water authority/profile lineage is reused; no second method, IF97 fallback, or silent reference-state mutation. Provider validation tier remains `SUPPORTED_TIER_1` (same-backend qualification, not independent physical-accuracy validation). |
| B2 | Domain and actual inlet snapshots | `T=298.15..300.00 K`; `P=100000..101325 Pa`; liquid only. No extrapolation, clipping, silent backend fallback, or phase crossing; out-of-domain result is BLOCKED. | CoolPropProvider generated and canonicalized both inlet snapshots. Native snapshot hashes: tube `984b3e72893b357535ed500294453b5e6b1f902a71a3c93357fe1a9978947819`; shell `e48b6a28f999e9cffc3cd873eeaede338c4de6ee16c897802bb19eeb41f23c19`. A 3×3 grid over the bounded T/P domain returned liquid at all nine points. Local runtime states must use the same authority and fail closed outside scope. |

Provider observations replayed at the inlet states:

| Side/state | rho kg/m³ | cp J/(kg K) | mu Pa·s | k W/(m K) | h J/kg | Pr |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tube 300 K / 101325 Pa | 996.556935265198 | 4180.635776556238 | 0.0008537424862859429 | 0.6094998584856292 | 112654.89965462626 | 5.855926514898839 |
| Shell 298.15 K / 101325 Pa | 997.047636760353 | 4181.31499077066 | 0.0008900224890776955 | 0.6065160802198025 | 104920.11980926784 | 6.13580496390948 |

The values above are provider replay observations, not separately promoted scalar authorities. Snapshot source identity is `CoolProp:HEOS:Water`, version `8.0.0+ae81610e7d23efc57f9d051c8e70a4d66e87537f;reference=DEF`. Existing reviewed domain-proof and backend-qualification hashes are retained unchanged.

## C_MATERIAL_WALL_AND_LOCAL_CONSTITUTIVE

| # | Completed decision | Bound project value | Scope/evidence |
| --- | --- | --- | --- |
| C1 | Tube-wall material and k model | 316L austenitic stainless steel, tube-wall metal; accepted geometry OD 0.01905 m, ID 0.01575 m, thickness 0.00165 m. Owner-selected conservative constant `k=14.0 W/(m K)` over 298.15–300 K. | Lawful manufacturer source: Alleima Sanmac 316/316L data sheet, source PDF SHA-256 `eda6e84f95c4cc2a46bb8c902cf066c4f51b9108d951d5490222cb365219ac48`, official source URL recorded in Stage-1 evidence. The source reports approximately 14 W/(m K) at 20°C and 15 W/(m K) at 100°C; it does not specify a constant 14 across the entire case interval. This is explicitly a project-owner conservative case value, not a manufacturer/ASTM constant claim. |
| C2 | Surface and fouling | `CLEAN`; tube and shell fouling resistance both 0 m² K/W; no deposit, contact resistance, or extra interface layer. | Explicit clean-reference-case decision only. Reuses `V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2` and `V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2`; zero is not generalized to other cases. |
| C3 | HTC and correction applicability | Tube uses reviewed turbulent Gnielinski/C3 branch and reviewed wall correction. Shell uses reviewed clean-profile Jμ authority, `J_mu=(mu_bulk/mu_wall)^0.14`, with located local bulk and fluid-wall property states. | Native exact inlet screening replay: tube Re `3742.675244246214513402808173`, Pr `5.855926514898839169263267261`, TURBULENT, Pr envelope PASS, Gnielinski Nu `27.61898513931272019827155622`; shell central-crossflow Re `2740.5066088396428172796798450599375449393604657674`, Pr `6.1358049639094794150526865914303242471116943093648`. Both case screening envelopes pass. No wall temperature, local HTC, or Jμ coefficient was solved here; runtime wall/local states are evaluated natively and fail closed if out of profile. No correlation switching or fouled-profile extension is authorized. |

The shell-side screening geometry replay uses the existing TASK031 formulas: central crossflow area 0.150000000000000000000000 m² and equivalent hydraulic diameter 0.018293343850 m after the native public quantization. TASK037 independently returns the exact outer/inner area ratio `1.209523809523810`; accepted inside area is `75.1107679584 m²`, and Decimal multiplication yields outside area `90.848262197302892909889504 m²`.

## D_NUMERICAL_AND_REAL_CASE_ADMISSION

### D1 — executable numerical profile

Bind the reviewed R94/R98 controls unchanged for this case: `trf`, linear loss, `ftol=1e-6`, `xtol=1e-12`, `gtol=1e-12`, two-point Jacobian, `diff_step=1e-5`, initialization-derived x scale, residual scale `abs(q_ts_seed)` with its reviewed exact-zero branch, `max_nfev=6`, residual callback cap 24, exact trust-region solver, empty `tr_options`, `f_scale=1`, and no Jacobian sparsity. Reuse the reviewed I0/I1/I2 initialization, physical residual definitions, residual acceptance, deterministic behavior, typed failure, property-failure and domain-exit policies. No separate under-relaxation is specified.

Effective `C_round=1.0` is bound under the existing R98 formula/semantics by explicit project-owner case-applicability decision; this is not a universal floating-point theorem. Signed negative q remains a permitted numerical unknown, but an otherwise converged negative physical heat-transfer result for this tube-hot/hotter-than-shell inlet case returns a typed BLOCKED applicability result. Do not clamp q, take its absolute value, or swap roles. Nonconvergence, resource/domain failure, and property errors produce no authoritative partial result.

### D2 — consolidated real-case production mesh policy

The single new owner authority is `V07-T172-REAL-CASE-PRODUCTION-MESH-PROFILE-R1`, scoped to `PROJECT_DESIGNED_ENGINEERING_REFERENCE_CASE`. Its lifecycle is `PROPOSED_AUTHORITY_REVIEW_PENDING` until the one consolidated Stage-1 independent review. This policy is new project production authority, not transfer of synthetic R103 cell counts.

**Fixed physical support and normalized mesh count**

The five immutable axial supports are `[0,1.2]`, `[1.2,2.4]`, `[2.4,3.6]`, `[3.6,4.8]`, `[4.8,6]` m. Each has length 1.2 m, inside area `15.02215359168 m²`, and outside area `18.1696524394605785819779008 m²`. There are two numerical sides, TUBE and SHELL. `n` means `SUBDIVISIONS_PER_PHYSICAL_INTERVAL_PER_SIDE`, not global cell count. Each physical interval receives exactly `n` axial cells on each side; totals are TUBE `5n`, SHELL `5n`, all cells `10n`, and wall interfaces `5n`. `n=1` is exactly the accepted TASK171 base topology: 10 cells and 5 interfaces with unchanged ownership.

**Refinement and sequence**

Each `n -> 2n` step bisects every parent cell at its midpoint independently inside each existing physical interval on both sides. Corresponding tube/shell children share exact axial support and wall-interface support. Physical/event boundaries, intervals, event inventory, paths, support owners, area ownership, and length ownership do not move, merge, split across events, appear, disappear, or change owner.

| n | Tube cells | Shell cells | Total cells | Wall interfaces |
| ---: | ---: | ---: | ---: | ---: |
| 1 | 5 | 5 | 10 | 5 |
| 2 | 10 | 10 | 20 | 10 |
| 4 | 20 | 20 | 40 | 20 |
| 8 | 40 | 40 | 80 | 40 |
| 16 | 80 | 80 | 160 | 80 |
| 32 | 160 | 160 | 320 | 160 |
| 64 | 320 | 320 | 640 | 320 |

The primary n sequence `1,2,4,8,16,32,64` is new project-owner authority. R103 primary absolute counts, R103 secondary sequence `3,6,12,24,48,96`, synthetic cap, synthetic references and automatic threshold transfer are all false. No secondary production sequence is required; R103 is supporting qualification evidence only.

**Observables, support mapping, and comparison**

The extensive observable is `TOTAL_WALL_DUTY`, conservatively summed from children to each common physical interval and then across the five intervals. The four intensive observables are `T_wall_inner_min`, `T_wall_inner_max`, `T_wall_outer_min`, and `T_wall_outer_max` reduced over the exact case wall-support set. Extensive mapping is `EXACT_CHILD_TO_PARENT_CONSERVATIVE_SUM`; intensive extrema mapping is `COMMON_PHYSICAL_SUPPORT_EXTREMA_REDUCTION`. No index/position pairing, interpolation, nearest-neighbor mapping, cross-mesh HTC or temperature average, or dividing total duty by cell count is allowed.

For consecutive coarse `c` and fine `f` duty values, let `D=max(|Q_c|,|Q_f|)`. If `D<=0.01 W`, pass only if `|Q_f-Q_c|<=0.01 W`; otherwise pass only if `|Q_f-Q_c|/D<=0.01`. No zero division is allowed. Each of the four wall extrema must independently satisfy `|T_f-T_c|<=0.01 K`. These thresholds are new owner policy informed by R103, not automatically transferred from R103.

Numerical uncertainty is part of the comparison: sum the applicable R94/R98 local wall-duty error/roundoff bounds over the wall supports for total duty, and take the maximum applicable local wall-temperature bound for each extrema comparison. Compare `observed_difference + floor <= threshold` as PASS, `observed_difference - floor > threshold` as FAIL, otherwise return `PRECISION_FLOOR_UNRESOLVED`. Do not use R102 synthetic `Q_ref` or `U_Q` values.

Two consecutive passing comparison pairs are required. After the candidate first has two passing pairs, one later level `2n` must also pass against that candidate; that headroom mesh is evidence only and the candidate remains the selected mesh. The n=64 level is reserved as headroom, so the latest possible accepted candidate is n=32 (320 total cells, 160 interfaces). If there is no eligible candidate by n=32, return `MESH_RESOURCE_EXHAUSTED` / `MESH_NOT_CONVERGED`; do not accept n=64 without its headroom level and do not raise the cap.

Resource limits are `n<=64`, 640 numerical cells and 320 wall interfaces. A producer-free native schema/resource stress check strict-validated a typed Definition with 5 intervals, 2 paths, 640 cells, 320 walls, 2,560 structural state/provenance records, 19 events and 3 provenance edges; TASK171's existing `MAX_RECORDS=4096`, tuple bound and 262,144-node/16-depth `safe_model` guard passed. This proves record-shape capacity only, not a mesh convergence result or TASK171 producer execution.

Typed fail-closed outcomes include `INVALID_PARENT_CHILD_RELATION`, `PHYSICAL_BOUNDARY_CROSSED`, `INCOMPLETE_PARENT_COVERAGE`, `OVERLAPPING_CHILDREN`, `INVALID_COMMON_SUPPORT_MAPPING`, `MISSING_OBSERVABLE_AUTHORITY`, `NONFINITE_COMPARISON`, `PRECISION_FLOOR_UNRESOLVED`, `REFINEMENT_SEQUENCE_INSUFFICIENT`, `RESOURCE_EXHAUSTION`, and `MESH_NOT_CONVERGED`. A failed/last mesh is diagnostic only, never production authority.

R103 transfer flags: supporting qualification evidence=true; absolute cell count, secondary sequence, synthetic resource cap, synthetic reference values and automatic threshold values transferred=false. `REAL_CASE_POLICY_VALUES_SELECTED_BY_PROJECT_OWNER=true`.

### D3 — case reference policy

Bind the already reviewed `V07-T172-REAL-CASE-REFERENCE-POLICY-R1` and `V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-R1` to this exact case/profile. Comparison is allowed, not mandatory or forbidden. `production_reference_oracle_required=false`, online continuous oracle required=false, specific online execution required=false, and R102 synthetic Q-reference/UQ values are not transferred. The owner decision resolves case applicability and the oracle slot; it does not implement an online oracle.

### D4 — structured native identity admission reference

Apply disposition `C_ADMISSION_CONTRACT_REQUIRES_CORRECTION_BECAUSE_AGGREGATE_ID_HAS_NO_NATIVE_SEMANTICS`: remove the admission predicate's scalar `GEOMETRY_ID` prerequisite and replace it with a role-labelled structured bundle of the existing TASK020 configuration, TASK021 layout, TASK022 bundle, TASK024 baffle geometry, TASK025 result, TASK171 topology/result/mesh/physical ownership, and reviewed path/compartment/area/length mapping identities and hashes. Keep every native identity in its own field and role. No concatenated digest, alias, UUID, or aggregate identity is created. This Stage-1 overlay is candidate contract correction pending the single independent review; it does not edit or rewrite historical R104/R107 contract records.

## Consolidated Stage-1 result and lifecycle

```ini
PROJECT_OWNER_DECISION_PACKAGE_COMPLETE=true
PROJECT_OWNER_DECISION_COUNT=12
PROJECT_OWNER_DECISION_COUNT_REMAINING=0
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
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLVED=true
REFERENCE_POLICY_RESOLUTION_VALID=true
REAL_CASE_MESH_ADMISSION_PREREQUISITES_RESOLVED=true
REAL_CASE_MESH_ADMISSIBLE=false
TASK172_RUNTIME_IMPLEMENTATION=false
TASK174_SOLVE_PERFORMED=false
TASK173_SOLVE_PERFORMED=false
TASK175_RELEASE_ACCEPTANCE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
SELF_APPROVAL=false
CODEX_SELF_APPROVAL_CLAIMED=false
NEXT_GATE=STAGE1_SINGLE_INDEPENDENT_REVIEW
STOP=true
```

The policy authority and all Stage-1 bindings are complete as a candidate bundle, but their effective reviewed lifecycle remains pending one consolidated independent review. No actual production mesh convergence sequence was run, so `REAL_CASE_MESH_ADMISSIBLE=false`. TASK172 runtime and every downstream solve remain unstarted. No R119F/R119G/R119H or other micro-gates are introduced.
