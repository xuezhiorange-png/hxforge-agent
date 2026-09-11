# TASK-166 — Bell–Delaware Shell-Side Thermal-Hydraulic Model

Status: implementation contract and production implementation are delivered
together in the TASK-166 primary pull request. This document is the
Task-specific software contract; it does not amend TASK-032, TASK-033, or
TASK-034.

## 1. Boundary and authority

TASK-166 owns fixed-geometry Bell–Delaware shell-side rating for a deliberately
narrow envelope.  In v0.6, “fixed geometry” describes the shell-side geometry
projection, not a restriction to one exchanger construction family.  The
admitted construction-family set is `FIXED_TUBESHEET`, `U_TUBE`, and
`FLOATING_HEAD`; the package does not add a family-specific mechanical model.
It owns the Bell-specific geometry projection, ideal
tube-bank heat transfer and friction state, the correction-factor chains, the
crossflow/window/end-zone pressure-drop decomposition, applicability,
provenance, and deterministic identity.

It does not own tube-count sizing, candidate enumeration, preliminary
engineering screening, or release integration.

The source identity is:

```text
SOURCE_DEFINITION_ID=TASK165_R3_BELL_DELAWARE_SOURCE_AUTHORITY_V1
IMPLEMENTATION_SOFTWARE_VERSION=task166.bell-delaware-impl-v1
SOURCE_CONFLICT_POLICY=FAIL_CLOSED
```

The source hierarchy is intentionally non-blending:

| Role | Source | Scope |
|---|---|---|
| Method origin | Kenneth J. Bell, University of Delaware Engineering Experimental Station final report, 1963 | historical method origin and provenance only |
| Primary implementation | Gonçalves, Costa & Bagajewicz, AIChE Journal 65(8), e16602 (2019), DOI `10.1002/aic.16602` | primary equations and correction semantics |
| Parameter supplement | Jamil, Goraya, Shahzad & Zubair, *Energy Conversion and Management* 226, 113462 (2020), DOI `10.1016/j.enconman.2020.113462`, accepted Northumbria manuscript, Appendix A Table A.1 | `a1–a4` and `b1–b4` only |
| Unequal-spacing supplement | Saif & Tariq, JMES 19(4) (2025), DOI `10.15282/jmes.19.4.2025.4.0852`, §2.1.3 Eq. 21 | heat-transfer `Js` only |

The Gonçalves article is the selected implementation authority. Jamil and
Saif/Tariq cannot silently override it. A material conflict blocks the
affected capability with `SOURCE_CONFLICT`.

The Gonçalves PDF used for equation location is the public article copy:

<https://www.ou.edu/class/che-design/pub-papers/Linear%20method%20for%20the%20design%20of%20shell%20and%20tube%20heat%20exchangers%20using%20the%20Bell-Delaware%20Method%28Goncalves%20et%20al%29-19.pdf>

The Jamil accepted-manuscript identity is:

```text
https://researchportal.northumbria.ac.uk/files/40570913/sthx.pdf
SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
```

The formal Saif/Tariq article identity is:

```text
https://journal.ump.edu.my/jmes/article/view/12360
JS_RELATION_ID=SAIF_TARIQ_2025_JMES_EQ21
```

Wiley Supporting Information remains metadata-only in this repository:

```text
WILEY_SI_ATTACHMENT_IDENTITY_VERIFIED=true
WILEY_SI_BYTES_OBTAINED=false
WILEY_SI_TABLE_CONTENT_VERIFIED=false
PSI_N_REQUIRED_BY_TASK166=false
PSI_N_DISPOSITION=TASK168_IF_SIZING_REQUIRES_IT
```

## 2. Supported envelope

Only the following cases can return `VALID`:

```text
construction_family=FIXED_TUBESHEET | U_TUBE | FLOATING_HEAD
shell_type=TEMA_E
shell_pass_count=1
baffle_type=SINGLE_SEGMENTAL
phase=SINGLE_PHASE
rheology=NEWTONIAN
layout=LAYOUT_30_DEG | LAYOUT_45_DEG | LAYOUT_90_DEG
0 < Reynolds <= 100000
```

At least two baffles, positive central/inlet/outlet spacing, a positive shell
ID, bundle diameter, tube OD, tube pitch, tube count, shell-to-bundle
clearance, shell-to-baffle clearance, and tube-to-baffle-hole clearance are
required. `0 < Bc < 0.5` is required. All values are exact finite Decimal
inputs or strict decimal lexical values; binary floats are not admitted.

The caller must provide accepted identities for TASK-020 configuration,
TASK-021 tube layout, TASK-022 shell-bundle geometry, TASK-024 baffle geometry,
TASK-031 shell-side hydraulic geometry, and TASK-032 shell-side flow state.
Every accepted evidence object must carry a non-empty producer identity and
the same `physical_exchanger_case_id`. Equal numerical values do not prove
case identity. The TASK-032 Reynolds, Prandtl, mass velocity, mass flow,
density, viscosity, thermal conductivity, and specific heat values remain
producer-owned; TASK-166 does not recompute them.

TASK-032's `FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE`,
`BELL_DELAWARE_NOT_COMPUTABLE`, `LEAKAGE_CORRECTIONS_NOT_COMPUTABLE`, and
`BYPASS_CORRECTIONS_NOT_COMPUTABLE` declarations remain historical TASK-032
semantics. TASK-166 consumes the accepted Reynolds value for its own
source-defined row and Js exponent selections; it does not create a general
flow-regime classifier.

Unsupported phase, rheology, shell arrangement, baffle family, layout,
Reynolds domain, or missing geometry/property authority is `BLOCKED`. There
is no implicit Kern fallback. If a separate future consumer wants a Kern
screening result, it must remain a separate TASK-033/TASK-034 authority.

The construction-family expansion is an applicability correction only.  The
Bell equations and geometry formulas are unchanged and operate on the same
accepted shell/bundle/baffle/layout inputs for all three admitted families.
TASK-166 does not generate U-tube pairing, calculate a U-bend radius, perform
floating-head mechanical design, or infer tubesheet/pull-clearance adequacy;
those responsibilities remain with their upstream authority contracts.

## 3. Request and output surface

The public business surface is one function:

```python
validate_request(raw: object) -> Task166ValidationResult
```

The typed request has these fields:

```text
schema_version
task166_version
source_definition_id
task020_configuration
tube_layout
shell_bundle_geometry
baffle_geometry
shell_side_hydraulic_geometry
shell_side_flow_state
shell_side_flow_state_request
request_metadata
```

The nested producer records are structural public projections, not private
implementation objects. A request may not substitute raw `h`, `ΔP`, a
correction factor, or a guessed clearance for an accepted upstream identity.

The successful result exposes, at minimum:

```text
bell_geometry
ideal_crossflow_heat_transfer_coefficient
Jc Jl Jb Js Jr
corrected_shell_side_heat_transfer_coefficient
ideal_crossflow_pressure_drop
crossflow_pressure_drop
window_pressure_drop
end_zone_pressure_drop
central_crossflow_contribution
window_contribution
entrance_zone_contribution
exit_zone_contribution
Rl Rb Rs
total_shell_pressure_drop
factor_evidence
applicability
completeness
warnings
provenance
result_hash
result_id
```

Every factor evidence record carries `factor_id`, `factor_version`,
`source_id`, `source_location`, applicability, a stable input projection, and
the Decimal value. No factor is represented only by an unexplained scalar.

## 4. Bell geometry projection

The implementation evaluates Gonçalves equations 3–35 in dependency order.
The important derived quantities are `Dctl`, `Dotl`, `theta_ctl`,
`theta_Ds`, `Ntcc`, `Ntcw`, `Nc`, `Fw`, `Fc`, `Sm`, `Sw`,
`Ssb`, `Stb`, `Sb`, `rs`, `rlm`, `Fsbp`, and `Dw`. Their public
projection also contains the central, window, leakage, and bypass areas and
tube-row counts.

The admitted source relations include:

```text
Dctl = Ds - Lbb - dte
Dotl = Ds - Lbb
theta_Ds  = 2 acos(1 - 2 Bc)
theta_ctl = 2 acos((Ds / Dctl) (1 - 2 Bc))
Ntcc = Ds / Lpp (1 - 2 Bc)
Ntcw = 0.8 / Lpp (Ds Bc - (Ds - Dctl) / 2)
Nc = (Ntcc + Ntcw) (Nb + 1)
Fw = (theta_ctl - sin(theta_ctl)) / (2 pi)
Fc = 1 - 2 Fw
Sm = (Lbc (Lbb + Dctl) / ltpeff) (ltp - dte)
Sw = Swg - Swt
rs = Ssb / (Ssb + Stb)
rlm = (Ssb + Stb) / Sm
Fsbp = Sb / Sm
```

For layout selection, the source defines `Lpp` as `0.866 ltp` for 30°,
`ltp` for 90°, and `0.707 ltp` for 45°. `ltpeff` is `ltp` for 30°/90°
and `0.707 ltp` for 45°. Equation 26 uses `Lpl=0` because the admitted
model explicitly dismisses the tube-lane partition bypass gap. It is not an
unannounced geometry default.

The source-provided shell-to-bundle and shell-to-baffle clearances must be
present in the accepted geometry evidence. TASK-166 does not manufacture a
TEMA clearance from a protected standard table. Missing or inconsistent
Bell-specific geometry blocks with `GEOMETRY_AUTHORITY_INCOMPLETE` or
`INVALID_GEOMETRY_DOMAIN`.

## 5. Ideal heat-transfer and corrections

`a1–a4` are selected from Jamil Table A.1 by the explicit 30°/45°/90° layout
and the five source Reynolds rows: `<10`, `10–<100`, `100–<1000`,
`1000–<10000`, and `10000–100000`. No nearest-row selection,
interpolation, or extrapolation is allowed.

Gonçalves equations 37–43 define:

```text
hi = ji Cps Gs Prs^(-2/3)
ji = a1 (1.33 / rp)^a Res^a2
a  = a3 / (1 + 0.14 Res^a4)
```

The primary correction equations are:

```text
Jc = 0.55 + 0.72 Fc
Jl = 0.44(1-rs) + (1 - 0.44(1-rs)) exp(-2.2 rlm)
Jb = exp(-Cbh Fsbp)
Jr = 10 / Nc^0.18                         for Re <= 20
Jr = Jr1 + (20-Re)/80 (Jr1-1)              for 20 < Re <= 100
Jr = 1                                     for Re > 100
```

`Cbh=1.35` for `Re<=100` and `1.25` otherwise. The admitted Saif/Tariq
supplement supplies the unequal-spacing heat-transfer correction only:

```text
Js = ((Nb-1) + (Lbi/Lbc)^(1-n1) + (Lbo/Lbc)^(1-n1))
     / ((Nb-1) + (Lbi/Lbc) + (Lbo/Lbc))
n1 = 1/3 for Re < 100
n1 = 0.6 for Re >= 100
```

When all three spacings are exactly equal, the implementation takes the
source-defined explicit branch `Js=1`; it does not use a tolerance. The
corrected coefficient is the deterministic product
`hs=hi*Jc*Jl*Jb*Js*Jr`.

## 6. Pressure-drop decomposition

`b1–b4` use the same explicit source row selection. Gonçalves equations
55–73 are implemented as separate named operations:

```text
fs = b1 (1.33/rp)^b Res^b2
b  = b3 / (1 + 0.14 Res^b4)
ΔPbi = 2 fs Ntcc Gs^2 / rho_s
ΔPc  = ΔPbi (Nb-1) Rb Rl
Rb   = exp(-Cbp Fsbp)
Rl   = exp(-1.33 (1+rs) rlm^p)
p    = -0.15(1+rs) + 0.8
ΔPs  = ΔPc + ΔPw + ΔPe
ΔPe  = ΔPe,in + ΔPe,out
ΔPe,in  = ΔPbi (1 + Ntcw/Ntcc) Rb (Lbc/Lbi)^(2-n)
ΔPe,out = ΔPbi (1 + Ntcw/Ntcc) Rb (Lbc/Lbo)^(2-n)
Rs   = (Lbc/Lbo)^(2-n) + (Lbc/Lbi)^(2-n)
```

`Cbp=4.5` for `Re<=100` and `3.7` otherwise. For the window term, the
source uses `Gw=mc/sqrt(Sm Sw)`, the laminar equation for `Re<100`, and the
turbulent equation for `Re>=100`. The result retains central crossflow,
window, entrance, exit, end-zone, and total contributions for pressure-drop
decomposition. The entrance and exit fields are the two source terms above,
rather than an assumed equal split. Heat-transfer `Jl/Jb/Js` are never reused
as pressure-drop `Rl/Rb/Rs`; their source identities remain distinct.

## 7. Validation, identity, and provenance

The raw boundary is bounded at depth 16, 512 nodes, and 16,384 UTF-8 scalar
bytes. It is total and never invokes arbitrary-object `repr`, `str`, `id`,
`hash`, memory addresses, or user hooks. Record insertion order is
non-semantic. Raw-boundary failure has a dedicated deterministic blocked
identity and never falls through to typed validation.

Validation is fail-closed: producer evidence, configuration, geometry,
properties, source row, heat transfer, pressure drop, applicability, result
identity, and provenance must all succeed. `Task166ValidationResult` has one
and only one populated branch: `RAW_BOUNDARY_BLOCKED`, `TYPED_BLOCKED`, or
`VALID`.

Canonical identity reuses the repository TASK-021 canonical JSON primitive
with TASK-166-specific domains. Decimal values remain exact lexical strings;
binary floats, unordered mappings, random values, and clock data are not
identity inputs. Result identity is SHA-256 content identity followed by the
TASK-166 UUID-v5 namespace.

The success provenance graph is acyclic and contains source-authority,
configuration, layout, bundle, baffle, TASK-032 flow, Gonçalves, Jamil,
Saif/Tariq, calculation-run, and result nodes. All source and input nodes
feed the calculation-run node; the calculation-run produces the result node.
The result hash is not used to construct its own preimage or a provenance
payload hash needed by that preimage. The graph must report zero self edges
and zero cycles.

## 8. Blockers and explicit non-scope

The closed implementation blocker vocabulary includes raw boundary failures,
source-required/conflict, upstream identity/authority errors, unsupported
configuration/phase/rheology/layout/baffle/Re, geometry/property/domain
errors, invalid factors/parameters, numerical/nonfinite values, pressure-drop
decomposition failure, provenance failure, identity replay failure, and
internal invariant failure. No zero/NaN/Inf fallback is permitted.

The following are outside TASK-166:

- `psi_n` and tube-count estimation (TASK-168 if required);
- variable-property iteration, two-phase behavior, wall-temperature iteration;
- Bell–Delaware source reconstruction from an unavailable Wiley SI;
- TASK-033/TASK-034 Kern semantic changes or hidden fallback;
- TASK-167 velocity/erosion/fouling/cleanability/expansion/vibration screening;
- TASK-168 catalog enumeration, manufacturable candidate generation, and sizing;
- TASK-169 ranking, Golden release integration, and release acceptance;
- LMTD, LMTD correction factor, F-factor, and overall-U/UA recomputation;
- detailed TEMA/API/ASME compliance, mechanical design, FEA, CFD, CAD, and
  proprietary vendor geometry inversion.

## 9. Construction-family applicability correction

The v0.6 Golden replay gates exposed that the former fixed-tubesheet check was
a repository applicability restriction rather than a dependency of any
Bell–Delaware equation in this package.  The correction is deliberately
narrow:

```text
TASK166_FORMULA_CHANGE=false
TASK166_PHYSICS_CHANGE=false
TASK166_TOLERANCE_CHANGE=false
TASK166_IDENTITY_CONTRACT_CHANGE=false
TASK166_APPLICABILITY_CONTRACT_CHANGED=true
TASK166_SUPPORTED_FAMILY_SET_CHANGED=true
TASK166_SUPPORTED_CONSTRUCTION_FAMILIES=FIXED_TUBESHEET,U_TUBE,FLOATING_HEAD
UTUBE_PAIRING_INFERENCE_ADDED=false
UTUBE_BEND_GEOMETRY_MODEL_ADDED=false
FLOATING_HEAD_MECHANICAL_MODEL_ADDED=false
PULL_CLEARANCE_MODEL_ADDED=false
```

TASK-021 still owns and validates an explicit `UTubePairingPlan` before a
layout is consumed by TASK-166.  TASK-166 only consumes the resulting accepted
layout and shell-side geometry.  A construction-family applicability PASS is
not a mechanical-design or fabrication-feasibility PASS.

## 10. Test contract

The implementation test module covers source identity and conflict behavior,
all geometry zones and invalid domains, all five J and three R factors, all
five parameter rows and three layouts, Js threshold and exact uniform spacing,
pressure-drop replay decomposition, missing authority, unsupported envelopes,
Decimal-only deterministic identity, raw boundary totality and limits,
provenance cycle checks, and regression that TASK-033/TASK-034 authority
remains unchanged. Numeric examples are used only when their source identity
and applicability are recorded; source rounding is never used to loosen an
acceptance ceiling.

TASK-167 is not authorized or started by this document or implementation.
