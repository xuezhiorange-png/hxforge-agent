# TASK-170 — v0.7 scope, source, Golden and solver-contract freeze

## 1. Version identity and decision status

```ini
TASK_ID=TASK170_V0_7_TASK171_ENTRY_AUTHORITY_R4
VERSION=HXFORGE_V0_7
CONTRACT_ID=TASK170-V07-CONTRACT-R4
BASE_MAIN_SHA=24099402697a6bc71be3ee112cc87d31e6341a2d
PREDECESSOR_RELEASE=v0.6.0
THEME=SHELL_AND_TUBE_HIGH_FIDELITY_SINGLE_PHASE_RATING_AND_SIZING
MODEL_LEVEL=STEADY_STATE_SINGLE_PHASE_SEGMENTED_L2_L3
TASK170_DOCUMENT_STATUS=PROPOSED_TASK171_ENTRY_AUTHORITY_R4
RATING_CONTRACT_DEFINED=true
SIZING_CONTRACT_DEFINED=true
SEGMENTED_MODEL_ARCHITECTURE_DEFINED=true
SEGMENTED_COUPLING_AUTHORITY_FROZEN=false
PROPERTY_AUTHORITY_FROZEN=false
WALL_TEMPERATURE_AUTHORITY_FROZEN=false
CONVERGENCE_AUTHORITY_FROZEN=false
TUBE_DP_CONTRACT_DEFINED=true
TUBE_DP_NUMERICAL_AUTHORITY_FROZEN=false
SHELL_DP_INHERITANCE_DEFINED=true
SHELL_SEGMENT_AGGREGATION_AUTHORITY_FROZEN=false
OPERABILITY_CONTRACT_DEFINED=true
FIV_NUMERICAL_AUTHORITY_FROZEN=false
SOURCE_AUTHORITY_COMPLETE=false
SOURCE_CONFLICT_POLICY=FAIL_CLOSED
GOLDEN_CLASS_COUNT=6
GOLDEN_CLASS_DESIGNS_DEFINED=true
GOLDEN_REFERENCE_AUTHORITY_COMPLETE=false
V06_GOLDEN_REGRESSION_INHERITED=true
INHERITED_TOLERANCE_SUBSET_VERIFIED=true
V07_COMPLETE_TOLERANCE_AUTHORITY_FROZEN=false
RELEASE_GATE_COUNT=24
RELEASE_GATE_ORDER_DEFINED=true
RELEASE_GATE_AUTHORITY_FROZEN=false
TASK171_DEFINED=true
TASK172_DEFINED=true
TASK173_DEFINED=true
TASK174_DEFINED=true
TASK175_DEFINED=true
TASK171_IMPLEMENTATION_STARTED=false
NUMERIC_CONVERGENCE_PROFILE_COMPLETE=false
GOLDEN_EXPECTED_AUTHORITY_COMPLETE=false
IMPLEMENTATION_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This is a documentation-only boundary and review artifact. Scope, required
schemas, gate order and fail-closed rules below are proposed for freezing;
they are not a claim that a new solver, an approved numerical profile, or
six independently validated reference cases already exist. The unresolved
items in §24 prevent a **complete TASK170 authority freeze** and entry into
the affected production capabilities. A green documentation CI cannot close
them. No package version, dependency, equation, test or legacy result changes
are part of this task. R4 authorizes only TASK171 entry documentation/authority proposals,
commit, push on the existing PR #273 branch, Draft description update and CI. It does
not authorize a new PR, authority approval, Ready, Merge or TASK171 work.

`DEFINED` means a proposal-level contract is written and available for review.
It does not mean repository authority has been frozen. All new v0.7 normative
language below describes the proposed contract, even where phrased as a
requirement. R4 does not convert this Draft into accepted repository authority.
Historical v0.6 authorities retain their existing status. Passing documentation
checks is distinct from completing the TASK170 authority freeze.

The [R3 authority audit](TASK-170-v0.7-authority-closure-r3.md) and
[source/qualification registry](TASK-170-v0.7-authority-registry-r3.json)
extend R2 without changing its architecture or approving new numerical inputs.
They distinguish inherited reviewed sub-scopes, newly verified sources and
unapproved proposals. Task-specific entry blockers are in the audit's §10;
an open Golden gap alone does not block every architecture task.

The [R4 TASK171 entry package](TASK-170-v0.7-task171-entry-authority-r4.md)
now supplies three concrete PROPOSED_AUTHORITY records for those entry blockers.
It narrows initial admission to explicit fixed-tubesheet straight-through 1×1
countercurrent interfaces; this is not all-family thermal admission. Independent
review is pending, `TASK171_ENTRY_AUTHORITY_COMPLETE=false`, and all seven R3
gap states remain unchanged. R3 audit/registry are historical evidence, not
rewritten approvals. Full GAP-SEG closure is distinct from TASK171 entry.

## 2. Predecessor authority

The base and the remote `v0.6.0` tag both resolve to the SHA in §1. The
predecessor exact-main push CI `34567134694` is completed/success. The release
is published, not draft or prerelease. These are baseline observations, not
v0.7 acceptance evidence.

Inherit, without changing their historical meanings:

* [TASK165 scope/source/tolerance freeze](TASK-165-v0.6-shell-and-tube-scope-source-acceptance-freeze.md).
* [TASK166 Bell–Delaware](TASK-166-bell-delaware-shell-side-thermal-hydraulic-model.md).
* [TASK167 screening](TASK-167-shell-and-tube-engineering-screening.md).
* [TASK168 manufacturable candidates](TASK-168-manufacturable-candidate-generation-and-sizing.md).
* [TASK160–162 versioned thermal authority](TASK-160-161-162-v0.6-thermal-closure-authority.md).
* [TASK169 final acceptance](TASK-169-v06-release-acceptance-final.md), including
  its independent Golden registry and trusted runtime-evidence boundary.

All paths and source mappings in this document are relative to the pinned
repository version, not a promise that mutable upstream web pages are frozen.

## 3. Theme and capability sequence

Requirements and operating conditions → approved configuration/geometry →
manufacturable candidate generation → segmented rating → local properties →
wall/viscosity iteration → thermal convergence → tube and shell DP closure →
operability screening → hard filtering → deterministic ranking → recommendation
and alternatives with complete provenance.

This capability narrative is not task scheduling order; production capability
dependencies are explicitly defined in §22.

`RATING` and `SIZING` are separate public engineering modes. A successful
rating is not automatically a selected design. An evaluable candidate with
warnings retains those warnings through ranking. A calculation without full
required closure is never recommendable.

## 4. Scope and admission

Steady-state, single-phase, Newtonian shell-and-tube heat exchange; explicit
geometry; temperature-dependent properties; source-qualified local HTC and
pressure-loss relations; countercurrent boundary-value solution; discrete
sizing; preliminary operability screening.

Construction vocabulary remains `FIXED_TUBESHEET`, `U_TUBE`, `FLOATING_HEAD`.
Vocabulary membership is not proof of admissible thermal topology. Each case
must retain TASK020 configuration, TASK021 layout (including explicit U-tube
pairing), TASK022 bundle, TASK024 baffles, authoritative clearances, and their
native identities. No geometry repair, default pairing, catalog snapping, or
unbound material/roughness/fouling values is permitted.

Initial thermal-envelope target: E shell, one shell pass and one declared tube
pass, subject to an explicit physical flow-path mapping. Additional passes
are `BLOCKED_OR_DEFERRED` until their mapping and method are reviewed. A legacy
U-tube `tube_pass_count=1` token does not by itself establish the local return-leg
temperature topology. That mapping is a required authority, not an inference.

For TASK171 initial entry specifically, R4 §2 is the narrower proposed domain:
FIXED_TUBESHEET straight-through only, explicit bundle membership/area map,
opposing physical inlet boundaries and physical event ownership. U_TUBE is
`BLOCKED_PENDING_FUTURE_REVIEW`; FLOATING_HEAD remains vocabulary but deferred
for topology review. No numerical calculation is enabled by interface admission.

## 5. Non-scope

```text
CONDENSATION EVAPORATION BOILING REBOILER
TWO_PHASE_HEAT_TRANSFER TWO_PHASE_PRESSURE_DROP VOID_FRACTION
FLOW_REGIME_MAP DRYOUT CHF
CFD 2D_THERMAL_FIELD 3D_THERMAL_FIELD
TUBESHEET_STRESS_DESIGN PRESSURE_VESSEL_WALL_THICKNESS FLANGE_DESIGN
NOZZLE_REINFORCEMENT ASME_STRESS_CALCULATION
MATERIAL_OPTIMIZATION COST_OPTIMIZATION
```

Two-phase work is reserved for a separately authorized v0.8. No transient
storage model, radiation model, axial wall-conduction solver or mechanical
qualification is added by this contract. Cases requiring these effects must
be outside the selected model's validated envelope, not silently approximated.

## 6. Engineering model level

One-dimensional axial **segmented lumped** model, not a spatial field solver.
Numerical cells and physical baffle compartments are distinct concepts. A
mesh authority binds cell boundaries, physical compartment ownership, area,
length, fluid-path membership and correlation-development coordinates.
Splitting a cell must not create a new entrance, bend, baffle or leakage event.

Mesh refinement is deterministic and bounded by an approved mesh profile.
Both iteration convergence and mesh adequacy must be demonstrated. No
random/adaptive geometry changes occur during sizing. Numeric mesh refinement
does not alter manufacturable candidate dimensions.

## 7. RATING contract

Required input authorities: schema/model/source versions; case identity;
complete exchanger configuration/geometry; hot and cold fluid identities;
hot/cold inlet temperatures and mass flow rates; pressure states required by
the property backend; fouling; wall material/conductivity; mesh/topology;
local correlation profiles; numerical convergence profile; request metadata.
Every engineering snapshot binds source, revision, evidence, units, domain
and canonical hash. No caller callback, anonymous coefficient or free-form
authority assertion can replace a producer.

The caller **does not supply both outlet temperatures as known boundary
conditions**. Reference outlets belong only to the external test oracle and
must never enter solver inputs, initialization or stopping decisions.

Output: solved hot/cold outlets; duty and energy balance; effective U and UA;
tube and shell HTCs (local plus explicitly defined aggregate); decomposed and
total DPs; local states; iteration/mesh diagnostics; convergence status;
applicability, warnings, blockers and replayable identities.

Zero flow, nonfinite states, unsupported phase, absent source or insufficient
pressure/geometry authority produce a typed failure. A failed solve may expose
diagnostics marked non-authoritative, never a successful partial rating.

## 8. SIZING contract

Required duty, inlet states, mass flows, fluid authority, allowed families,
manufacturable catalog/discrete sets, allowable tube/shell DPs and thermal/
screening constraints are source-bound requirement authorities.

Reuse TASK168 deterministic enumeration, exact catalog membership and exact
TASK021 physical tube count. No approximate tube-count coefficient is needed
when exact enumeration applies. Every enumerated candidate is retained as
evaluated or blocked, with stage and reason. No continuous geometry optimizer.

A coarse diagnostic may reject only under an explicit authorized rule; it
cannot supply the final thermal result. Every recommendable candidate must
invoke the full v0.7 RATING boundary with actual producer replay. Exact hard
constraint decisions precede versioned TASK169-style ranking; objective,
weights, scales, WARN penalty, tie-break and Top-N require policy identity.
No rank-based truncation may hide a blocked or untested candidate.

## 9. Segmented state, topology and conservation contract

Each segment records:

```text
segment_id; geometric_interval; physical_compartment_id; flow_path_ids
hot_in_temperature; hot_out_temperature; cold_in_temperature; cold_out_temperature
hot_bulk_temperature; cold_bulk_temperature; hot_properties; cold_properties
tube_reynolds; tube_prandtl; tube_nusselt; tube_htc
shell_reynolds; shell_prandtl; shell_htc
wall_temperature; wall_inner_temperature; wall_outer_temperature
local_overall_u; local_ua; local_heat_duty
tube_friction_dp; tube_minor_dp; shell_local_dp_components
local_energy_residual; local_convergence_status
source_ids; native_producer_ids; property_evaluation_ids
```

`wall_temperature` is a labeled projection, not a substitute for distinct
inner/outer surfaces. Bulk/film evaluation and wall-side association are
defined by the selected correlation. Hot does not necessarily mean shell.

Two coordinate concepts are separate:

* `physical_coordinate`: the exchanger/shell geometry reference coordinate,
  used for physical locations, compartment ownership and geometry mapping.
* `fluid_path_coordinate`: a monotonic coordinate along one explicitly
  identified stream flow path, increasing in that fluid's travel direction.

Segment ordering follows each stream's `fluid_path_coordinate`, not necessarily
`physical_coordinate`. Hot/cold inlet/outlet always follow actual fluid travel,
never array index alone. A return leg may traverse decreasing physical axial
coordinate while its fluid-path coordinate continues increasing.

Countercurrent boundaries are defined by physical connections and the explicit
fluid-path mapping. The two streams are not assumed to share one monotonic
global x. Simultaneous solution or a reviewed boundary-value method must satisfy
both physical inlet conditions; an unknown boundary is never silently treated
as supplied. `COUNTERCURRENT` is required; `COCURRENT=BLOCKED_OR_DEFERRED`.

U-tube segmented topology is admitted only with explicit leg identities,
outbound/return mapping, a U-return connection, validated physical tube pairing
authority and segment-to-flow-path mapping. Pairing alone does not establish
thermal connectivity. If repository authority cannot supply all of these:
`U_TUBE_SEGMENTED_THERMAL_TOPOLOGY=BLOCKED_PENDING_GAP_SEG`. No runtime inference
of a U-return thermal path or substitution of a straight-tube path is permitted.

Pass-to-cell mapping, U-return connections and shell-compartment bulk mixing
must be explicit. A single shell bulk temperature cannot silently serve every
cell. No replacement of the inherited sectional mixing method by ideal
counterflow without a new method authority and bridge evidence.

Conservation requirements use stream enthalpy differences at the selected
pressure/state, not a silently constant inlet cp. Hot heat removed and cold
heat gained must match locally and globally under the selected no-ambient-loss
model. Pressure coupling and any neglected kinetic/potential contributions
need an applicability statement. A backend domain violation cannot be repaired
by clipping T or imposing an incorrect phase.

Aggregate `Q_total` is the sum of accepted local duties. `UA_effective` is
defined here as the sum of local conductances and `U_effective` as that sum
divided by the corresponding total reference area. These are explicitly labeled
conductance summaries, **not** a claim that Q equals this UA times a global
LMTD in every variable-property case. Report outlet states, both stream energy
totals, energy error, segment count, iteration count and convergence status.

## 10. Property authority

Reuse `hexagent.properties` and producer-specific validated snapshots; do not
create a second fluid property engine. The pinned base lock contains CoolProp
**8.0.0**; older same-backend regression labels in `properties/base.py` mention
7.6.1 and must not be mistaken for the current lock or independent reference.
This task does not upgrade or edit the lock.

The official [high-level API](https://coolprop.org/coolprop/HighLevelAPI.html)
documents state-pair evaluation, phase checking and backend version/revision.
Use a version-bound backend identity, fluid/composition/reference-state
identity, pressure, temperature, units and per-fluid validity envelope.
Evaluate rho, mu, cp, k and Pr at each required local state; also retain enthalpy
for variable-property energy accounting. Backend documentation is not an
independent exchanger Golden oracle.

Property calls and returned canonical snapshots must bind the actual backend
build/lock and phase/domain result. Caches include the entire state and backend
identity. Explicit constant-property profiles are allowed only within their
reviewed envelope; an inlet-only snapshot is not a variable-property profile.
Full fluid-specific transport/EOS limits and independent accuracy checks remain
GAP-PROP in §24. No mixture or REFPROP license is inferred from CoolProp access.

`PROPERTY_BACKEND_CAPABILITY != HXFORGE_SUPPORTED_FLUID_PROFILE`.
Only reviewed `SUPPORTED_FLUID_PROFILE` entries may enter production Rating
or Sizing. Each entry must bind:

```text
fluid_profile_id; backend_id; backend_version; fluid/composition identity
reference_state; supported phase; temperature envelope; pressure envelope
required properties; EOS/transport applicability
known uncertainty/validation evidence; source/provenance; canonical hash
review status
```

Admission verifies that exact profile and its review evidence, canonical hash,
backend/fluid identity and all local states against its permitted envelope.
Backend availability or a successful property call is insufficient. An
unregistered fluid/composition yields `PROPERTY_AUTHORITY_MISSING` or
`PROPERTY_PROFILE_UNSUPPORTED`; mixtures are not implicitly supported.
R2 did not select or approve a supported-fluid list. R3's water qualification
proposals remain unsupported for production; the GAP-PROP remainder is open.
No source, property domain or review status is invented by this addition.

## 11. Wall-temperature and viscosity authority

Reuse TASK037 cylindrical conduction and explicit inside/outside area bases,
film resistances, wall conductivity and source-bound fouling. Associate tube
and shell bulk states with the correct physical wall surface. Iterate local
properties, films, wall surfaces and local heat transfer consistently.

Wall-viscosity correction must name the exact correlation, exponent, bulk/wall
state definition, heating/cooling applicability and permitted viscosity ratio.
Do not append a remembered Sieder–Tate factor to Gnielinski or Bell–Delaware.
TASK026's accepted Gnielinski implementation does not itself authorize that
extension. A numerical coefficient occurring elsewhere is not this authority.

No single averaged wall temperature may replace two source-required wall
states. Material k(T) and fouling surface conventions require their own domains.
Missing wall-correction authority is GAP-WALL, not permission to set a neutral
correction and claim V07-G03 passes.

## 12. Convergence and numerical authority

The required immutable convergence profile contains `authority_id`, version,
source/evidence, canonical hash, max local/global iterations, temperature
absolute/relative tolerances, wall-temperature tolerance, duty-relative,
energy-relative and outlet tolerances, mesh limits, initial-state rule,
update order, arithmetic/quantization and under-relaxation policy.

All active residual tests must pass; a small update alone is insufficient.
Temperatures compare in kelvin; relative tests use declared scales and explicit
zero-reference handling. The selected profile must supply those scales, not
an anonymous epsilon. Oscillation, exhaustion, invalid properties and invalid
thermal states are not convergence. No last-iterate recommendation.

```text
CONVERGED
MAX_ITERATIONS_REACHED
PROPERTY_OUT_OF_RANGE
INVALID_THERMAL_STATE
NUMERICAL_FAILURE
```

Every non-CONVERGED state implies `RECOMMENDATION_ALLOWED=false`.
Under-relaxation is not enabled by default; if selected its fixed schedule and
factor are authority-bound. Library defaults are not engineering tolerances.
No runtime tolerance loosening, stochastic initialization or unordered updates.

Same canonical input/runtime/lock must reproduce iteration count, values,
status and result hash. Cross-Python canonical parity is a separate exact
release requirement measured by actual runtimes, not a caller claim.

Numeric iteration budgets and new temperature tolerances remain **UNBOUND**
pending numerical-profile/reference precision review (GAP-NUM). This explicitly
means the convergence schema/semantics are defined for review but the executable
convergence authority is **not complete**. TASK171/172 must not invent defaults.

## 13. Tube-side DP decomposition

Required outputs: `tube_friction_dp`, `tube_entrance_dp`, `tube_exit_dp`,
`tube_pass_dp`, `tube_bend_dp`, approved other local losses, `tube_dp_total`.
Every component has status, location, source coefficient, velocity/density
basis, multiplicity and native result identity.

The non-overlapping taxonomy uses **option B** for `tube_pass_dp`:

| Field | Exclusive ownership / reporting semantics |
| --- | --- |
| `tube_friction_dp` | Straight-flow distributed wall friction only |
| `tube_entrance_dp` | Physical exchanger/tube-flow-path entrance local loss only |
| `tube_exit_dp` | Physical exchanger/tube-flow-path exit local loss only |
| `tube_bend_dp` | Explicitly modeled bend/U-return local losses only |
| `approved_other_local_losses` | Other source-authorized physical local events not owned by any preceding category; unique pass-specific events belong here |
| `tube_pass_dp` | Derived per-pass reporting subtotal referencing already owned components; never an additional summand in total DP |

The aggregation invariant for the required loss categories is:

```text
tube_dp_total = tube_friction_dp + tube_entrance_dp + tube_exit_dp
              + tube_bend_dp + sum(approved_other_local_losses)
OWNED_BY_EXACTLY_ONE_DP_COMPONENT=true
MUST_NOT_CREATE_NEW_PHYSICAL_LOCAL_LOSS_EVENTS=true
TUBE_PASS_DP_INCLUDED_AGAIN_IN_TOTAL=false
```

Every physical loss event has an explicit identity and exactly one owner.
Pass subtotals reference those event identities; they cannot reclassify an
entrance or U-return and count it again. Numerical cell splitting cannot create
additional physical local-loss events. Missing required source coefficients
are BLOCKED, never default `K=0`. This defines bookkeeping only: it does not
close GAP-DP or add loss coefficients. Applicability of any required additional
pressure contribution remains subject to the existing GAP-DP review below;
the sum is not permission to omit a necessary hydraulic term.

Reuse TASK027 straight-tube and TASK028 local-loss authority and TASK029
composition where applicable. TASK027 currently binds constant-density and
zero-net-elevation assertions. It cannot be relabeled as a complete
variable-density pressure model without requalification. Segmentwise reuse
must account for pressure/property coupling and explicitly adjudicate any
acceleration/elevation term (GAP-DP).

Entrance/exit occur at actual boundaries, return/bend at actual connections,
not once per numerical cell. U-bend coefficients require explicit bend geometry
and source domain; TASK021 pairing alone does not supply bend loss authority.
Nonapplicable components carry `NOT_APPLICABLE` and a configuration reason;
missing required coefficients are BLOCKED, not anonymous zero.

## 14. Shell-side DP and HTC inheritance

TASK166 remains the sole Bell–Delaware physics owner. Retain ideal crossflow,
Jc/Jl/Jb/Js/Jr, central/window/end-zone DP, Rl/Rb/Rs and exact source selection.
Js is heat transfer, Rs pressure loss; no conflation. Jamil supplements only
a/b rows; Saif/Tariq only Js; Gonçalves remains primary. No Wiley S2/S3 contents
are newly claimed; psi_n is not introduced.

The future engine couples accepted local states to physical compartments.
It must not multiply a whole-exchanger correction or end-zone loss by cell
count. A source-qualified partition/aggregation ledger must explain ownership
of bypass, leakage and window flow when mesh boundaries differ from baffles.
That derivation and one-segment/refinement verification are GAP-SEG, not
already covered merely because TASK166 succeeds on a 0D state.

All inherited source envelopes remain enforced. In particular any active
TASK034 path retains its 25% baffle-cut profile; do not generalize it for a new
mesh. No silent Kern fallback labeled Bell.

## 15. Operability and vibration screening

`SCREENING_ONLY=true`; `FULL_MECHANICAL_ADEQUACY=false`.
Retain TASK167 construction, cleanability, fouling and expansion semantics.
Proposed added diagnostics: crossflow velocity, vortex-shedding frequency,
tube natural frequency, frequency ratio and fluidelastic-instability index.

Each numeric diagnostic requires its complete equation, geometry-dependent
coefficient, supports/span/material/effective mass/damping and property sources.
No universal Strouhal number, damping, added mass or Connors coefficient is
assumed. The current TASK167 public evidence does not authorize a critical
velocity coefficient; the GAP-FIV numerical-profile remainder remains open.

Status vocabulary: PASS, WARNING, BLOCKED, NOT_COMPUTABLE. A deterministic
adapter maps legacy WARN to WARNING without changing its identity. Missing
optional diagnostics remain NOT_COMPUTABLE with reason; mandatory screening
missing authority blocks recommendation. An optional NC may retain an explicit
WARNING candidate only under a reviewed requirements policy, never PASS.
No generic result implies TEMA/API/ASME compliance. Restricted numbers remain
subject to TASK012 approved-rule-pack licensing and provenance.

## 16. Source inventory and audit disposition

This table preserves the R1/R2 inventory at its stated audit date. R3's
additional full-text acquisitions and qualification decisions are recorded in
the linked authority registry and audit; they do not silently replace any
inherited implementation source or approve a new numerical extension.

Evidence classes: **INHERITED** means the pinned repository's accepted scope,
not an assertion of newly reading copyrighted source bytes; **VERIFIED-PUBLIC**
means the cited primary page was read in that audit; **CANDIDATE** is discovery
only, never production authority. Audit date: 2026-09-11. Repository paths are
exact implementation mappings, not substitutes for missing external evidence.

| Source ID | Title / author / year / exact location | Mapping and allowed use | Access/license and disposition |
| --- | --- | --- | --- |
| V07-INHERIT-T026 | Gnielinski, *New Equations for Heat and Mass Transfer in Turbulent Pipe and Channel Flow*, 1976, Int. Chem. Eng. 16(2), 359–368; Petukhov 1970; TASK026 R6–R7 §§5.2,6 | `tube_side_thermal/nusselt_selector.py`; existing turbulent Nu/Pr/Re limits only | INHERITED; full primary equation-page rights not reacquired; no new wall/entrance correction |
| V07-INHERIT-LAMINAR | Incropera et al., *Fundamentals of Heat and Mass Transfer*, 7th ed., 2011, Table 8.1; TASK026 §5.2 | Existing CWT/CHF fully developed laminar selection, not arbitrary conjugate-wall segments | INHERITED, copyrighted; segmented boundary applicability needs review |
| V07-INHERIT-T027 | TASK027 R1 §§8,9,9.1,9.2,13 | `tube_side/friction_pressure_drop.py`; Darcy, laminar and Colebrook selection/quantization | INHERITED project contract; primary bibliography/variable-density extension incomplete: GAP-DP |
| V07-INHERIT-T028 | TASK028 frozen local-loss contract §6, §18.1 | `tube_side_local_loss/computation.py`; bound K, reference area and multiplicity; TASK029 composition | INHERITED; no general entrance/return/bend coefficient catalog is established |
| SRC-BELL-1963 | K. J. Bell, *Final report of the cooperative research program on shell and tube heat exchangers*, University of Delaware, 1963 | Method origin/provenance only | INHERITED TASK165; not full equation authority |
| SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE | Gonçalves, Costa, Bagajewicz, *Linear method for the design of shell and tube heat exchangers using the Bell–Delaware method*, AIChE 65(8), e16602, 2019; DOI 10.1002/aic.16602; TASK166 §§geometry, heat transfer, DP relation ledger | `bell_delaware/geometry.py`, `heat_transfer.py`, `pressure_drop.py`; primary relations and all unchanged exact locations in TASK166 | INHERITED accepted manuscript evidence; no paper redistribution here; spatial coupling not automatically authorized |
| SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS | Jamil et al., *Exergoeconomic optimization of a shell-and-tube heat exchanger*, ECM 226, 113462, 2020; DOI 10.1016/j.enconman.2020.113462; Appendix Table A.1, manuscript p57 | a1–a4/b1–b4 layout/Re rows only | INHERITED Northumbria manuscript, CC-BY-NC-ND; hash a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970 |
| SRC-SAIF-TARIQ-2025-JMES-UNEQUAL-BAFFLE-SPACING-JS | Saif and Tariq, *The impact of baffle configuration on performance of shell and tube heat exchangers using the Bell–Delaware approach*, 2025; DOI 10.15282/jmes.19.4.2025.4.0852; §2.1.3 Eq21, p10882 | Js unequal spacing only; exact Re=100 selection and uniform limit inherited | INHERITED official PDF, CC-BY-NC4; hash 0f66f8efbb4ce071a5408bed5f938d4d659189c199231289e674b92f1d0c9571 |
| T037-S01-DOE-HDBK-1012-2-92 | US DOE, *Thermodynamics, Heat Transfer and Fluid Flow*, Vol2, June1992; HT-02 pp12/13/22, Eqs2-7/2-8/2-10 | `overall_heat_transfer_resistance/schema.py`; cylindrical wall and film surface bases; TASK038 UA | INHERITED; official public-distribution PDF independently accessible; numeric fouling/k still require case authority |
| V07-PROP-COOLPROP-8 | Bell, Wronski, Quoilin, Lemort, 2014, *Pure and Pseudo-pure Fluid Thermophysical Property Evaluation and the Open-Source Thermophysical Property Library CoolProp*, DOI10.1021/ie4033999; version8.0.0 API sections PropsSI, PhaseSI, Reference States | `properties/coolprop_provider.py`, backend identity and local-state contract | VERIFIED-PUBLIC official API and v8.0.0 MIT LICENSE; fluid-specific uncertainty/domain audit remains GAP-PROP |
| MAGAZONI_2019 | Magazoni et al., 2019, existing TASK161 source p873 Eqs1–4; p880 Table7, MODEL_2 | `flow_arrangement_performance_method_authority/service.py`; TASK162 1×1 sectional P relation and existing constant-property bridge | INHERITED CC-BY4 record; not a general variable-property segmented oracle |
| V07-CANDIDATE-MSL-BASICHX | Modelica Association, Modelica Standard Library BasicHX documentation, generated 2026-08-05 | Architecture cross-check: two fluid paths and intervening wall, direction explicit | VERIFIED-PUBLIC descriptive page; no pinned full solver/validation fixture selected; CANDIDATE only |
| V07-CANDIDATE-BRENT | R. P. Brent, *Algorithms for Minimization Without Derivatives*, 1973, ch3–4; SciPy brentq API, Parameters/Notes | Numerical root-method candidate: continuity, sign-changing bracket, stopping record | VERIFIED-PUBLIC SciPy docs; no dependency addition or default tolerance adoption; not a complete exchanger solver |
| V07-CANDIDATE-SIEDER-TATE | E. N. Sieder and G. E. Tate, *Heat Transfer and Pressure Drop of Liquids in Tubes*, 1936, 28(12),1429–1435, DOI10.1021/ie50324a027 | Candidate wall-viscosity authority | Publisher identifies purchase-only full PDF; equation/page/domain not verified here. SOURCE_AUTHORITY_MISSING; no coefficient authorized |
| V07-INHERIT-FIV | Pettigrew and Taylor, *Vibration analysis of shell-and-tube heat exchangers*, Parts1/2, JFS18,2003; DOI10.1016/S0889974603001208 and 10.1016/S088997460300121X; TASK167 §4 | Method/required-input authority only | INHERITED abstract-limited evidence; no numeric instability coefficient. OSTI candidate 6887081 retrieval failed; not authority |
| V07-PROJECT-REQ | TASK170 explicit user authorization and this versioned document §§7–9,12,18–23 | RATING/SIZING interfaces, ordering, release acceptance and required reviews | Project authority, not empirical physics, manufacturer data or independent Golden results |

Primary read-back links:
[DOE official PDF](https://www.energy.gov/sites/default/files/2026-04/DOE-HDBK-1012-92_VOL2.pdf),
[CoolProp citation](https://coolprop.org/citation.html),
[CoolProp v8 MIT license](https://raw.githubusercontent.com/CoolProp/CoolProp/v8.0.0/LICENSE),
[BasicHX](https://build.openmodelica.org/Documentation/Modelica.Fluid.Examples.HeatExchanger.BaseClasses.BasicHX.html),
[SciPy brentq](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.brentq.html),
[Sieder–Tate publisher](https://doi.org/10.1021/ie50324a027).
No search snippet, mutable page, vendor summary or same-backend test is
promoted to complete mathematical/Golden authority by this inventory.

## 17. Source conflict and admission priority

Frozen project scope and licensing boundary → accepted capability-specific
source/profile → explicitly scoped supplement → cross-check only. Different
capabilities do not silently override each other. Bell origin is not a
replacement implementation source; Jamil cannot authorize Js; Modelica cannot
replace Bell equations; numerical library defaults cannot set engineering error.

Each selected relation must carry equation/location, version/bytes identity,
variables/units/domain, coefficient row, license/evidence and source-role edges.
Conflicting applicable sources produce `SOURCE_CONFLICT` and no calculation;
no averaging, newer-wins rule or anonymous coefficient mixing. Missing full
equation evidence produces `SOURCE_AUTHORITY_MISSING`. New source admission
requires a reviewed TASK170 amendment before its production use.

## 18. V07 Golden class design proposal

All six **class purposes and test boundaries** below are defined for review.
All six fixture/reference authority states are `PROPOSED_PENDING_REFERENCE`:
none has a complete independent numeric payload in the pinned repository.
This distinction must remain visible in receipts; class definition is not
`GOLDEN_AUTHORITY_COMPLETE=true`.

| Golden | Required case and decisive evidence | Oracle/authority still required |
| --- | --- | --- |
| V07-G01 | Moderate-temperature, single-phase full geometry; multiple cells; hot/cold Tout, Q, U, tube/shell DP | Independently reviewed published measurement/reference dataset with geometry, fluids, uncertainty and all six target quantities |
| V07-G02 | Same authorized geometry/boundaries, significant property variation; controlled variable-vs-constant property comparison; property calls demonstrably differ across cells | Fluid-specific domain/accuracy and independent reference; material difference must exceed declared combined numerical/reference resolution, not merely unequal bits |
| V07-G03 | Source-applicable viscosity-sensitive case; actual wall/bulk property calls and two wall surfaces; stable converged correction | Complete wall-correction source, ratio domain, reference wall/outlet/duty and uncertainty; neutral correction cannot pass |
| V07-G04 | RATING receives inlet states/flows/geometry, no outlet targets; solves both outlets and energy closure | Independent expected outlets withheld from solver, known geometry/property/method envelope; no oracle leakage into guesses |
| V07-G05 | One real authorized discrete space, multiple candidates, ≥1 thermal or DP rejection and ≥1 feasible full segmented rating; exact ranking and reason trace | Approved project inputs/limits and independent expected classifications/order plus reviewed numerical expectations for feasible ratings |
| V07-G06 | Explicit invalid property domain, impossible thermal state or demonstrably exhausted nonconvergent profile; typed blocker and NO_RECOMMENDATION | Frozen literal negative input, independent domain/profile evidence and exact expected blocker; no fake producer result or arbitrary exception callback |

Every fixture record must contain: Golden ID/version; source ID/title/location;
redistribution/license status; normalized input hash; actual production request;
independent expected identity or approved numeric values with uncertainty;
tolerance profile; reviewer/approval evidence; source bytes/hash and provenance.
Expected values from the implementation under test are observations only, not
Golden authority. `REVIEW_STATUS=PROPOSED`, approval fields empty until an
independent reviewer acts. Full source/schema admission precedes solver replay.

Golden release execution must perform actual RATING/SIZING replay from bound
inputs, compare all applicable fields, retain failure stages and trusted
runtime outputs. Synthetic unit cases cannot make a Golden gate PASS.

## 19. v0.6 regression bridge

V06-G01–G05 and their approved expected authority remain immutable. Replay
the predecessor through the legacy path/explicit compatibility adapter;
never rewrite expected hashes to fit v0.7. Preserve all TASK020–169 authority
and canonical semantics on that path.

The one-segment bridge is conditional: constant-property profile valid,
neutral wall correction, same geometry/area/topology and the **same accepted
thermal-performance relation**. Then compare engineering values using inherited
applicable tolerances in §20. A new finite-volume approximation or ideal
counterflow relation is not automatically numerically equal to the legacy
sectional mixing model. GAP-SEG must close this equivalence before claiming it.

`N1_LEGACY_NUMERICAL_EQUIVALENCE_REQUIRED_FOR_TASK171_ENTRY=false`.
`N1_LEGACY_BRIDGE_REQUIRED_FOR_TASK175_RELEASE=true`. The R4 interface package
does not claim or relax numerical equivalence; it separates the entry and
release prerequisites.

Manufacturable membership, hard status, ranking and canonical replay are exact.
New model/source semantics may intentionally create a different v0.7 result
identity; exactness means replay of each authorized version, not reusing a
v0.6 ID for changed physics. Mesh refinement is tested separately from N=1.

## 20. Tolerance authority

Decimal values below inherit TASK165, not a newly selected numerical default.
Relative reference error is absolute difference divided by the nonzero
absolute reference value. Zero-reference comparisons require an independently
bound absolute criterion; no implicit denominator epsilon. Energy/closure
normalization must be frozen in the numerical profile before execution.

| Field | Frozen value or explicit gap | Justification / applicability |
| --- | --- | --- |
| ENERGY_BALANCE_RELATIVE_ERROR_MAX | 0.001 | Inherited TASK165 global acceptance ceiling; not a solver stopping rule |
| SEGMENT_DUTY_CLOSURE_RELATIVE_ERROR_MAX | UNBOUND — GAP-NUM | Requires discretization/error allocation and near-zero-cell handling |
| GLOBAL_DUTY_CLOSURE_RELATIVE_ERROR_MAX | 0.001 | Inherited thermal-duty closure ceiling; profile must define residual scale |
| OUTLET_TEMPERATURE_ABS_ERROR_MAX | UNBOUND K — GAP-REF/GAP-NUM | No independent v0.7 temperature resolution supplied |
| WALL_TEMPERATURE_ITERATION_ERROR_MAX | UNBOUND K — GAP-WALL/GAP-NUM | Wall/correction sensitivity and numeric precision not yet qualified |
| REFERENCE_HTC_RELATIVE_ERROR_MAX | 0.02 for inherited published shell-h profile only; other profiles UNBOUND | TASK165 published shell-h reference; not blanket tube/variable-property accuracy |
| REFERENCE_DP_RELATIVE_ERROR_MAX | 0.02 for inherited published shell-DP profile only; other profiles UNBOUND | TASK165 published shell-DP reference; not blanket detailed tube-loss accuracy |
| RATING_DUTY_REFERENCE_ERROR_MAX | UNBOUND — GAP-REF | Closure residual is not error against measured/reference duty |
| DIRECT_PUBLISHED_EQUATION_REPRODUCTION_RELATIVE_ERROR_MAX | 0.005 | Existing TASK165 relation-reproduction scope only |
| CANONICAL_IDENTITY_REPLAY | EXACT | Existing deterministic serialization/replay acceptance |
| HARD_CONSTRAINT_STATUS | EXACT | No epsilon-based near-PASS |
| RANKING_ORDER | EXACT | Versioned policy and canonical tie-break |
| PY311_PY312_CANONICAL_PARITY | EXACT | Actual same-input dual-runtime canonical bytes/IDs |

Numerical stopping thresholds must be justified below the relevant acceptance
error budget and property/reference resolution, with quantization and mesh
error included. No arbitrary 0.01 K, iteration count, relaxation factor or
library default is frozen merely to fill this table. UNBOUND blocks the
corresponding capability and means `TOLERANCE_AUTHORITY_FROZEN=false` for the
complete executable profile. No caller override of a bound tolerance is valid.

## 21. Ordered release gates

The 24 IDs and their reporting order are defined in this proposal, not yet
frozen repository release authority. Each gate records evidence hashes,
applicability and a PASS/BLOCKED decision; missing or NOT_COMPUTABLE mandatory
evidence is BLOCKED.

```ini
RELEASE_GATE_ORDER_IS_REPORTING_ORDER=true
RELEASE_GATE_ORDER_IS_EXECUTION_DEPENDENCY_ORDER=false
```

Gate order is the stable release-receipt order, not a scheduling constraint.
Actual evidence production/evaluation follows an explicit dependency DAG.
For example, Gate01 needs property, wall, energy/convergence and hydraulic
evidence; its number does not authorize execution before those prerequisites.
The producer-task DAG in §22 governs capability availability; reporting it in
01–24 order does not reverse those dependencies. A blocked required dependency
makes the downstream gate BLOCKED, never a fabricated PASS. Final receipts
always report 01–24 in the order below. Gate24 may PASS only if gates01–23
all PASS, irrespective of the order in which their evidence was collected.

| Order | Gate | Minimum evidence |
| --- | --- | --- |
| 01 | SEGMENTED_THERMAL_HYDRAULIC | Valid topology, local real producer outputs and mesh check |
| 02 | VARIABLE_PROPERTY_EVALUATION | Local state-bound backend calls, domain/phase checks |
| 03 | WALL_TEMPERATURE_ITERATION | Both surface states and converged residuals |
| 04 | VISCOSITY_CORRECTION | Source-bound non-neutral case, no coefficient mixing |
| 05 | ENERGY_BALANCE_CLOSURE | Local/global residuals under approved scales |
| 06 | FULL_RATING | Geometry/inlet-only production request replay |
| 07 | OUTLET_TEMPERATURE_SOLUTION | Two solved outlets vs withheld independent reference |
| 08 | FULL_SIZING | Multiple candidates actually rated |
| 09 | MANUFACTURABLE_CANDIDATE_BINDING | Exact catalog/discrete source identities |
| 10 | TUBE_DP_DECOMPOSITION | All applicable native components, no duplicate losses |
| 11 | SHELL_DP_CLOSURE | Bell compartment ownership and aggregate replay |
| 12 | CONVERGENCE_FAIL_CLOSED | Exhaustion/domain/invalid-state negatives never recommended |
| 13 | OPERABILITY_SCREENING | Required real diagnostics/status; NC never false PASS |
| 14 | DETERMINISTIC_REPLAY | Repeated iterations/status/IDs under pinned profile |
| 15 | PROVENANCE_COMPLETE | Source→inputs→local producers→aggregate→selection DAG, no cycles |
| 16 | PY311_PY312_PARITY | Trusted actual interpreters, same input/head/tree/lock and exact bytes |
| 17 | GOLDEN_V07_G01 | Independently approved baseline |
| 18 | GOLDEN_V07_G02 | Independently approved variable-property sensitivity |
| 19 | GOLDEN_V07_G03 | Independently approved wall-viscosity case |
| 20 | GOLDEN_V07_G04 | Independently approved full Rating |
| 21 | GOLDEN_V07_G05 | Independently approved full Sizing |
| 22 | GOLDEN_V07_G06 | Independently approved real negative |
| 23 | V06_REGRESSION | All five unchanged legacy Goldens and conditional N=1 bridge |
| 24 | END_TO_END_RELEASE_DEMO | Actual request→rating/sizing→selection; gates01–23 all PASS |

Any missing gate blocks overall release acceptance. CI matrix presence is not
trusted parity proof: reuse TASK164/169 observer pattern, actual executables,
version/HEAD/tree/lock checks and canonical comparisons. Missing, duplicate,
swapped, stale or failed runtime observation fails closed.

## 22. TASK171–TASK175 roadmap

Task numbers are identifiers, not production dependency order. The proposed
acyclic dependency contract is:

```ini
TASK171_DEPENDS_ON=TASK170
TASK172_DEPENDS_ON=TASK171
TASK174_DEPENDS_ON=TASK171
TASK173_DEPENDS_ON=TASK172,TASK174
TASK175_DEPENDS_ON=TASK173
```

```text
                 TASK170
                    |
                 TASK171
                 /     \
            TASK172   TASK174
                 \     /
                 TASK173
                    |
                 TASK175
```

| Task | Defined responsibility | Required boundary |
| --- | --- | --- |
| TASK171 | SEGMENTED_THERMAL_STATE_AND_TOPOLOGY_ENGINE | TASK170 authority prerequisite; physical/fluid-path topology, local thermal-state schema, cell↔compartment mapping, countercurrent boundary topology, conservation framework, mesh ownership and Bell physical-compartment interface |
| TASK172 | PROPERTY_WALL_AND_CONVERGENCE_CLOSURE | TASK171 interfaces; local property evaluation/domain enforcement, inner/outer wall temperatures, approved viscosity correction, deterministic iteration/failure semantics and numerical-profile binding |
| TASK174 | DETAILED_HYDRAULIC_AND_OPERABILITY_SCREENING | TASK171 interfaces; tube entrance/exit/pass/bend/local-loss decomposition, shell compartment aggregation, variable-state hydraulic coupling, operability diagnostics and FIV screening authority |
| TASK173 | FULL_RATING_AND_SIZING_SOLVER | Both TASK172 and TASK174 authority available; complete Rating/Sizing, hard thermal/DP constraints, filtering, deterministic ranking, recommendation and alternatives |
| TASK175 | V0_7_INTEGRATION_GOLDEN_AND_RELEASE_ACCEPTANCE | TASK173 complete; six independently approved V07 fixtures, V06 bridge, trusted Python3.11/3.12 parity, deterministic replay, 24 gates and end-to-end release acceptance |

TASK171 must not claim final variable-property closure, wall-viscosity numerical
closure, a detailed tube-loss coefficient catalog, complete segmented Bell DP,
numeric FIV screening or full Rating/Sizing. Its Bell interface establishes
physical ownership; TASK174 owns hydraulic aggregation/coupling qualification.

TASK172 and TASK174 can develop against TASK171's explicit interfaces in
parallel. Their shared state/pressure interfaces must be compatible at TASK173
integration; this is not permission to fabricate property or hydraulic evidence.
Complete Rating/Sizing and any recommendation are blocked until **both**
authorities are available and all required closures pass. Convergence authority
from TASK172 includes the numerical profile consumed by the integrated solve;
TASK174 does not create a competing convergence policy.

Each task may use internal implementation slices; no one-formula-per-task
fragmentation. All five require separate implementation authorization. This
document defines responsibilities, not permission to start them or approve
their source gaps automatically.

## 23. Testing and Git policy

```ini
DEVELOPMENT_SLICE_TESTING=TARGETED_ONLY
TASK_LOCAL_REGRESSION=REQUIRED
FULL_SUITE_PER_INTERMEDIATE_COMMIT=false
ONE_PRIMARY_PR_PER_TASK=true
EXACT_HEAD_CI_REQUIRED_ONCE_PER_TASK_FINAL_HEAD=true
MAIN_POST_MERGE_CI_REQUIRED=true
FINAL_TASK_HEAD_FULL_CI=true
FINAL_TASK_HEAD_PY311_PY312_REQUIRED=true
FINAL_RELEASE_ACCEPTANCE_REQUIRED=true
```

Required future matrix: local energy/direction/area checks; boundary-value
solution without oracle leakage; local property calls and out-of-domain
negatives; wall correction active/neutral limits; exhaustion/nonfinite/zero
scale failure; mesh convergence; no duplicated minor/Bell losses; unsupported
pass topology; exact candidate retention/constraints/ranking; legacy identities;
all six real Golden replays; source/license/hash tampering; runtime evidence
tampering; canonical order/Decimal-context invariance; acyclic provenance.

TASK170 R4 changes only its main document and entry proposal. Validate headings/required fields,
relative links, source-role scope, unresolved ledger consistency, diff boundary
and whitespace. No new test/CI-manifest/workflow dependency is necessary.
Final Draft PR CI must complete on the exact PR head. Main post-merge CI remains
a future separately authorized gate; a Draft is not a merged freeze.

## 24. Fail-closed rules and complete remaining authority ledger

R2 left all seven gaps OPEN. R3 explicitly separates already reviewed
predecessor sub-scopes from missing new authority. PARTIALLY_CLOSED does not
approve a new source/profile or enable production. No gap is CLOSED; all
unresolved remainders below remain fail-closed. See the R3 audit and registry
for exact inherited scopes, evidence limitations and per-task entry blockers.

```ini
GAP_SEG_STATUS=PARTIALLY_CLOSED
GAP_PROP_STATUS=PARTIALLY_CLOSED
GAP_WALL_STATUS=PARTIALLY_CLOSED
GAP_NUM_STATUS=PARTIALLY_CLOSED
GAP_DP_STATUS=PARTIALLY_CLOSED
GAP_FIV_STATUS=PARTIALLY_CLOSED
GAP_REF_STATUS=OPEN
TASK171_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK174_ENTRY_AUTHORITY_COMPLETE=false
TASK173_ENTRY_AUTHORITY_COMPLETE=false
TASK175_RELEASE_AUTHORITY_COMPLETE=false
```

| Gap | Missing reviewed evidence | Affected capability / required closure |
| --- | --- | --- |
| GAP-SEG | Exact discretization/mixing/pass mapping, physical Bell compartment allocation and N=1 equivalence proof | TASK171 topology/interface, TASK174 shell aggregation, TASK173 integration; select complete source/derivation and independently review it; no global-correction-per-cell shortcut |
| GAP-PROP | Fluid-specific EOS/transport domains, uncertainty, pressure coupling and local snapshot qualification | TASK172; bind exact fluid/backend evidence, not general library availability |
| GAP-WALL | Complete selected wall-viscosity relation, wall locations, coefficients/domain and coupling verification | TASK172; legally accessible full authority, not a remembered exponent or purchase-page abstract |
| GAP-NUM | Numeric iteration/relaxation/mesh budgets, residual scales, temperature/segment error allocation | TASK171 mesh interfaces, TASK172 numeric-profile authority, TASK174 state-coupling interface and TASK173 integrated solve; reviewed precision/mesh justification |
| GAP-DP | Detailed entrance/exit/return/U-bend coefficient authority and variable-property friction applicability | TASK174; source-bound local-loss catalog and density/pressure assumptions |
| GAP-FIV | Complete vortex/natural-frequency/instability equations and array/support-dependent coefficients | TASK174; legal source and mechanical-property snapshots, otherwise NOT_COMPUTABLE with required-screen blocker |
| GAP-REF | Six independent fixture payloads, precision/uncertainty and reviewer-bound expectations | TASK175 and new numeric tolerances; proposal classes alone cannot authorize release |

These are gaps established by this audit, not claims that no suitable source
exists anywhere. Alternative sources may be proposed under a reviewed amendment;
none may silently replace the frozen hierarchy. Scope and schema review can
proceed while production admission remains blocked.

Proposed closed failure vocabulary: `SOURCE_AUTHORITY_MISSING`,
`SOURCE_CONFLICT`, `PROPERTY_AUTHORITY_MISSING`, `PROPERTY_PROFILE_UNSUPPORTED`,
`PROPERTY_OUT_OF_RANGE`, `TOPOLOGY_AUTHORITY_INCOMPLETE`,
`CONVERGENCE_AUTHORITY_INCOMPLETE`, `MAX_ITERATIONS_REACHED`,
`INVALID_THERMAL_STATE`, `NUMERICAL_FAILURE`, `REQUIRED_SCREEN_NOT_COMPUTABLE`,
`UPSTREAM_IDENTITY_MISMATCH`, `GOLDEN_AUTHORITY_UNAPPROVED`,
`TOLERANCE_AUTHORITY_INCOMPLETE`, `PROVENANCE_INVALID`. Exact implementation
names will follow repository typed-enum conventions without changing semantics.

No blocked stage creates a fabricated downstream result. No unsupported source
domain, property, phase, geometry, pass map or mechanical requirement is loosened
to pass a Golden. No source self-approval, observed-output promotion, caller
parity declaration or green-CI implication closes an authority gap.

Current endpoint: R4 TASK171 entry proposals prepared for independent review,
with R3 source/Golden/tolerance gaps unchanged; complete freeze remains BLOCKED by
the explicitly task-mapped remaining authority, not a blanket all-gaps switch.
TASK171–175 production work has not started. Ready/Merge remain unauthorized.
