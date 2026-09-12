# TASK170 R3 — authority audit, qualification proposals and entry gates

## 1. Decision and evidence boundary

```ini
TASK_ID=TASK170_V0_7_AUTHORITY_CLOSURE_R3
DOCUMENT_STATUS=PROPOSED_AUTHORITY_CLOSURE_R3
BASE_MAIN_SHA=24099402697a6bc71be3ee112cc87d31e6341a2d
PREVIOUS_HEAD_SHA=55fd1bc209fe5d71801262d3648b3e801df61d76
PR_NUMBER=273
NEW_AUTHORITY_SELF_APPROVAL=false
SOURCE_AUTHORITY_COMPLETE=false
TASK170_COMPLETE_FREEZE_ELIGIBLE=false
PRODUCTION_IMPLEMENTATION_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

Audit date: 2026-09-12. This is a bounded audit of all seven requested gaps,
not a claim to have exhausted all literature. The accompanying
[machine-readable registry](TASK-170-v0.7-authority-registry-r3.json) records
source locations, retrieved-byte SHA256 or immutable revisions, rights,
scope, limitations and review status. Neither this document nor that registry
is a production authority input. No code reads them to enable a capability.

`REVIEWED_AUTHORITY` is reserved for the **already accepted predecessor scope**
at the pinned base. Its review evidence is inherited, not created by this run.
`VERIFIED_SOURCE` means the actual indicated source was read; it is not an
HXForge applicability approval. New qualification designs are
`PROPOSED_AUTHORITY`, unapproved, with empty approval evidence. Discovery-only
records remain `CANDIDATE`; an unsuitable proposed use may be `REJECTED`
without rejecting the underlying publication. No new item is promoted to
`REVIEWED_AUTHORITY`.

`PARTIALLY_CLOSED` below identifies an explicitly inherited, reviewed sub-scope;
it does **not** mean that newly retrieved sources have closed an executable
v0.7 capability. The unresolved remainder stays fail-closed. `OPEN` means no
complete reviewed sub-capability of the requested kind was established.
No gap is CLOSED. Literature-access failure is distinct from an engineering
disproof; lack of a transferable domain is distinct from an incorrect paper.

R2's six Golden class purposes, 24 release gate IDs/reporting order, coordinate
separation, non-overlapping DP taxonomy and task DAG are unchanged. This audit
does not add a numerical tolerance, coefficient catalog, iteration preset,
fluid approval, Golden expected output or production dependency.

## 2. Registry and source handling

The JSON registry is the field-complete inventory. Its keys correspond to
AUTHORITY_ID, CAPABILITY, SOURCE_ID, SOURCE_ROLE, SOURCE_TITLE, AUTHOR, YEAR,
EXACT_LOCATION, ACCESS_PATH, LICENSE, HASH_OR_REVISION, DOMAIN,
EQUATION_OR_DATASET_SCOPE, LIMITATIONS, REVIEW_STATUS and DEPENDENT_GAP.
Artifact hashes identify the bytes read, not approval. For inaccessible full
texts, a DOI is bibliographic revision evidence, **not** a claim of byte access.
The evidence manifest distinguishes those cases. Public access does not imply
public-domain or redistribution rights. No downloaded publication is vendored.

New-source priority remains official/author/primary sources. A textbook
mentioned in another paper has not thereby been read. The pinned repository
retains its exact accepted source selection; a new source cannot replace it
silently. Rights requiring further permission remain a production-admission
blocker. Source conflict remains FAIL_CLOSED; no averaging or convenient
coefficient selection. Reading a legal public copy does not grant rights to
redistribute its tables or produce a restricted rule pack.

PDF text extraction was checked against rendered pages for the liquid-water
domain/uncertainty (§2.3, §3.3, §4.3) and Martin/Gnielinski Appendix9.2. No
garbled PDF coefficient transcription is used as an implementation artifact.
Other sources are located by section/equation and retained as source pointers;
their coefficient arrays have not been copied into a runnable profile.

## 3. GAP-SEG — model, topology and physical ownership

### 3.1 Coverage matrix

| Required relation | Evidence actually read | Disposition and missing qualification |
| --- | --- | --- |
| Local conservation | MSL4.1.0 `Interfaces.mo`, `PartialDistributedVolume`, lines852–903: per-volume medium state, steady mass and energy balances; `Pipes.mo` lines471–490 enthalpy flux differences/upwind states | VERIFIED_SOURCE; candidate steady enthalpy balance framework, not an approved HXForge discretization |
| Local conductance | `HeatExchanger.mo` `BasicHX` and `WallConstProps`, lines328–350/441–450; inherited TASK037 cylindrical resistance | MSL wall is lumped through thickness, not the exact TASK037 cylinder. A reviewed interface must preserve both area bases; do not import its planar conductance as a cylindrical equation |
| Countercurrent coupling | `BasicHX` explicitly connects the second pipe's reversed heat-port sequence to the wall; flow direction is defined by actual ports | Supports explicit two-path coupling. Does not establish U-return mapping, shell mixing or an HXForge shooting/bracketing algorithm |
| Variable properties | Each MSL control volume has its own `Medium.BaseProperties`; enthalpy advection uses neighboring states | Architecture evidence only; HXForge fluid/domain profiles belong to GAP-PROP |
| Boundary-value problem | Two inlet ports on opposing paths; no requirement to know both outlet targets | Proposed two-boundary problem, not proof that a scalar residual is continuous, bracketed or unique for every admitted case |
| Mesh meaning | `DynamicPipe` finite-volume balances and staggered momentum discretization, `nNodes`/modelStructure | Cell count changes numerical approximation, not hardware. Library defaults are not mesh authority; no selected refinement order/error bound |
| Physical geometry | R3-INHERIT-GEOMETRY: TASK020–024 native authorities and explicit pairing | Reviewed geometry sub-scope only. Pairing proves legs/coverage, not thermal return topology |

Source is pinned to Modelica Standard Library commit
`8ae3d35c24e519cb2996cab20f3b13daf2b0c50a` (v4.1.0), not the mutable generated
documentation. BSD-3-Clause was read. The repository's default dynamics,
wall approximation, node count and fluid models are **not** adopted.

Proposed authority ID: `V07-SEG-INTERFACE-PROPOSAL-R3`. It requires a versioned
cell/physical-compartment ownership table, explicit stream connections,
area/length sums and conservation interfaces. It is not an approved numerical
scheme. A review must specify whether a local state is a cell mean, face state
or mixed compartment state, and prove consistent transfer between them.

### 3.2 Bell spatial allocation

R3-GONCALVES §2.1, Eqs36–73 supplies the predecessor's scoped whole-state
relations. Eqs55–57 count central intervals, Eqs68/70 count windows and
Eqs72–73 account for end zones. They are physical occurrences, not mesh cells.
Jr depends on the source's crossed-row count; leakage/bypass ratios depend on
physical geometry. Jamil supplies only selected coefficient rows and the
Saif/Tariq supplement only Js, exactly as TASK166 already records.

```ini
GAP_SEG_BELL_ALLOCATION=CANNOT_CLOSE_FROM_TASK166_ALONE
ARBITRARY_CELL_DP_DIVISION_AUTHORIZED=false
WHOLE_EXCHANGER_J_FACTOR_REPETITION_AUTHORIZED=false
END_ZONE_LOSS_PER_NUMERICAL_CELL_AUTHORIZED=false
```

A reviewed derivation must define the central/window/inlet/outlet ownership,
mass/enthalpy carried by leakage and bypass, property-evaluation location and
how numerical subcells aggregate without recounting physical rows or local
events. A physical interval may contain several cells; splitting it cannot
duplicate its window, end zone or global correction. MSL's two-pipe example
does not supply this Bell mixing model. Interface definition is a TASK171
entry prerequisite; executable hydraulic aggregation belongs to TASK174.

### 3.3 N=1 and U-tube limits

MSL finite-volume mixing with one cell is not automatically the Magazoni
MODEL_2 sectional performance relation admitted by TASK160–162. A bridge
requires an independently reviewed equality/approximation argument covering
governing relation, flow arrangement, constant-property validity, area basis,
boundary conditions and mixing. The legacy relation's successful replay does
not prove the new model's N=1 limit. Bridge status: UNPROVEN, not a loose
comparison obtained by adjusting tolerance.

Physical coordinates and fluid-travel coordinates remain distinct. U-tube
admission requires explicit leg identities, pairing, return connection,
pass direction and both stream-to-cell maps. No reviewed mapping of the new
thermal mesh to that topology was found. Therefore
`U_TUBE_SEGMENTED_THERMAL_TOPOLOGY=BLOCKED_PENDING_GAP_SEG` remains in force.

**Conclusion: PARTIALLY_CLOSED**, limited to native predecessor geometry and
existing Bell physical-region identities. New coupling, topology qualification,
N=1 proof and mesh adequacy are unresolved. TASK171 entry remains blocked by
those specific interfaces, not by the absence of six Golden measurements.

## 4. GAP-PROP — water qualification, not backend-wide admission

### 4.1 Sources and discrepancy checks

CoolProp v8.0.0 resolves to commit
`ae81610e7d23efc57f9d051c8e70a4d66e87537f`.
`Water.json` names Wagner/Pruß2002 for EOS and Huber2009/2012 for viscosity
and conductivity. IAPWS releases provide legal full formulation locations,
domains and uncertainty maps. The software's declared 2000 K ceiling is not
the IAPWS-95 stable-fluid validity ceiling (1273 K); backend success is not
source applicability. Transport validity is piecewise and differs between μ
and k. An admissible state is the **intersection** of EOS, both transport
domains and stable-liquid phase, not a rectangle from backend maxima.

IAPWS95 §6 does not assign statistical significance to its uncertainty maps;
transport releases describe coverage-factor-based uncertainty. AN1 distinguishes
absolute enthalpy uncertainty from uncertainty of a particular enthalpy
difference. These cannot be combined indiscriminately into a universal RSS
number or a duty tolerance. Near-critical cautions, phase boundaries and the
selected backend implementation must be qualified separately.

### 4.2 Proposed profile records

| Field | `V07-WATER-HEOS8-QUALIFICATION-R3` |
| --- | --- |
| Review / supported | PROPOSED_AUTHORITY; `SUPPORTED_FLUID_PROFILE=false`; no production admission |
| Backend/version | CoolProp HEOS / 8.0.0, commit above; locked dependency unchanged |
| Fluid/composition | Pure ordinary Water; no dissolved glycol or other mixture implied |
| Reference state | Existing DEF policy, with native reference fingerprint; IAPWS reference convention must replay, no offset mutation |
| Phase | Stable single-phase liquid only; not metastable, saturated, two-phase or critical-region extrapolation |
| T_min / T_max | Production numeric bounds UNBOUND pending reviewed intersection; EOS melting boundary and §5 upper bound, transport Eq9/Eq14, and local phase boundary all constrain it |
| P_min / P_max | Production numeric bounds UNBOUND; same state-dependent intersection, not an arbitrary pressure rectangle |
| rho / cp / h | R3-IAPWS95 §3–4; h and Δh uncertainty additionally R3-IAPWS-H |
| μ | R3-IAPWS-MU §§2.4–2.8 and CoolProp Water transport binding |
| k | R3-IAPWS-K §§2.4–2.8 and CoolProp Water transport binding |
| Pr | Derived only from the consistently bound cp, μ, k state; not a separate anonymous property |
| Validation | IAPWS check tables validate formulation reproduction; do not constitute independent whole-exchanger data |
| Uncertainty | State-specific source maps plus implementation verification; no single global software-accuracy claim |
| Identity | Literal proposal record in JSON; canonical metadata identity is distinct from an approved production profile hash |
| Required review | Select actual application domain, phase-boundary exclusion policy, joint uncertainty treatment and backend verification evidence |

`V07-WATER-POINT1MPA-CHECK-R3` is a **property-only reference proposal**, not a
Rating profile. It binds SR6-08(2011), P_min=P_max=0.1 MPa and the recommended
all-property interval intersection 273.15–383.15 K, additionally restricted
to stable liquid. Thus the numerical interval does not admit the metastable
upper portion. The source's approximate melting/boiling descriptions must
not be implemented as exact phase tolerances. The report gives stable-liquid
relative uncertainties of 0.0001% for density and 0.1% for cp (§2.3), 1% for μ
(§3.3), 1.5% for k (§4.3), under its stated convention. These are source
observations, **not v0.7 acceptance values**. Enthalpy-difference uncertainty
still needs AN1's path/state treatment. A single reference pressure cannot
authorize the pressure evolution of a full exchanger.

`V07-GLYCOL-WATER-QUALIFICATION-R3` remains CANDIDATE and unsupported. No
reviewed glycol species, concentration/basis, full property/transport
uncertainty and valid joint envelope was established. CoolProp's INCOMP
documentation explicitly distinguishes mass/volume composition and
composition-dependent enthalpy reference behavior; the existing HXForge HEOS
path does not become an INCOMP implementation by citation. No other fluid is
admitted. Missing fields remain UNBOUND, not inferred from library output.

**Conclusion: PARTIALLY_CLOSED**, for inherited backend/reference/snapshot
semantics only. Verified water sources materially reduce discovery work but
neither new profile is REVIEWED_AUTHORITY. TASK172 fluid admission remains
blocked. No blanket CoolProp accuracy or license assumption is made.

## 5. GAP-WALL — separate resistance, wall states and HTC correction

| Surface | Complete evidence / gap | Decision |
| --- | --- | --- |
| Cylindrical conduction | TASK037 native inner/outer surface transform, wall bundle R and outer-area resistance; DOE Vol2 Eqs2-7/2-8/2-10 | Inherit R3-INHERIT-WALL unchanged |
| Inner/outer wall temperatures | TASK037 outputs resistances, not both wall temperatures or a conjugate thermal solution | Needs reviewed surface-temperature derivation, sign/area/fouling conventions and conductivity evaluation location |
| Tube-side Gnielinski extension | TASK026 existing Nu domain retained. Gonçalves Eq75 has no wall-viscosity multiplier; Eq77's alternative laminar relation is not an extension of Eq75 | `GNIELINSKI_WALL_VISCOSITY_EXTENSION=BLOCKED` |
| Sieder/Tate replacement | ACS DOI10.1021/ie50324a027 identifies purchase-only full text; no licensed full equation/domain acquired | Coefficients, Re/Pr, ratio and heating/cooling domains UNBOUND; no remembered exponent, no replacement selection |
| Crossflow property correction | Martin/Gnielinski2000 Appendix9.2 p1160 is readable and explicit, but treats normalization of crossflow experimental HTC | VERIFIED_SOURCE, not tube-inside or Bell supplement authority |
| Bell wall correction | TASK166/Gonçalves Eqs36–39 do not supply the requested new wall-property factor; existing supplements have narrower roles | `BELL_WALL_VISCOSITY_EXTENSION=BLOCKED` |

Martin/Gnielinski defines fluid properties at arithmetic mean inlet/outlet
temperature and wall Prandtl number at the outer tube surface; its EqA13
normalizes experimental HTC using a liquid Pr/Pr_wall correction with separate
ratio branches. This is **not** a generic μ/μ_wall correction. Although the
page exposes branch exponents, the complete transferable Re/Pr/ratio envelope,
thermal-boundary assumptions and combination with HXForge's base correlation
have not been reviewed. No branch numbers are imported. The publication is
copyrighted; legal reading of the KIT copy is not table-redistribution approval.

Proposed `V07-WALL-SURFACE-INTERFACE-R3` must explicitly name bulk fluid,
fluid/fouling interface and metal inner/outer surfaces. With fouling, a
correlation's wall temperature cannot silently be replaced by the metal
temperature. Material k and fouling remain separate source-bound inputs.
Heating/cooling direction, fluid, Re/Pr and ratio domain, surface basis and
base-correlation combination are mandatory fields. Missing any one blocks
the numerical correction; a neutral correction is not an active-wall Golden.

**Conclusion: PARTIALLY_CLOSED**, cylindrical resistance only. No complete
wall-viscosity correlation/profile was approved, and no new wall-temperature
iteration is authorized.

## 6. GAP-NUM — proposed reviewable profile, no numerical defaults

`V07-NUMERICAL-PROFILE-PROPOSAL-R3` is PROPOSED_AUTHORITY, not executable.
The official version-pinned SciPy brentq documentation verifies a scalar
bracketing method's prerequisites and failure reporting. It does not prove
the exchanger residual has a root or establish an engineering error budget.
No SciPy dependency is introduced; Brent is a method candidate, not a chosen
whole-system nonlinear solver.

| Profile field | Proposed rule / unresolved value |
| --- | --- |
| Root/nonlinear method | Bracket-preserving scalar solve only if a reviewed reduction proves continuity and sign change; otherwise method UNBOUND, no fallback to a last iterate |
| Initialization | Deterministic construction from physical inlet/domain authorities only; exact rule UNBOUND; no reference outlet leakage |
| Bracketing | Both endpoints must be source-domain-valid; no property extrapolation to discover a sign change; failed bracket is typed failure |
| Local/global iteration budgets | UNBOUND; derive from selected algorithm, bracket/precision and declared resource budget, not library maxiter |
| Temperature/wall/outlet residual | Named dimensional residual, units, norm and absolute/relative scaling required; all new numeric thresholds UNBOUND |
| Energy/duty residual | Local and global conservation plus reference-error checks kept distinct; scale and zero-duty handling reviewed before use |
| Mesh refinement/max mesh | Same physical geometry and event ownership at each refinement; error estimator, expected order, termination/max count UNBOUND |
| Under-relaxation | No default factor. Activation rule, factor, update order and convergence evidence UNBOUND |
| Oscillation/stagnation | Detection rule/window/threshold must be profile-bound, deterministic and reviewed; currently UNBOUND |
| Failure | Nonfinite, invalid state, property range, absent bracket, exhaustion or failed mesh check prevent recommendation; diagnostics not a successful result |
| Serialization | Existing canonical/version/quantization boundaries inherited; quantify new rounding propagation before selecting stopping criteria |

### Error-budget ledger

| Budget contribution | Evidence available | Still required |
| --- | --- | --- |
| Reference uncertainty | Individual sources, no complete six-case V07 reference set | Per-output reference precision, covariance/coverage convention and approved expectation |
| Property uncertainty | IAPWS state-specific EOS/transport/Δh evidence | Application-domain propagation, backend validation, composition/pressure effects |
| Correlation uncertainty | Existing narrow reference-reproduction tolerances | Qualified variable-state/wall profile and correlation uncertainty in the actual domain |
| Discretization | Finite-volume meaning established as source evidence | Model-specific convergence order and reviewed refinement bound |
| Iteration | Bracketed-method prerequisites available | Residual-to-output sensitivity and numerical budget allocation |
| Serialization/quantization | Predecessor deterministic identities | New state/error propagation, rounding floor and representation choice |

A proposed stopping budget must be demonstrably smaller than the relevant
engineering acceptance resolution after sensitivity propagation; the margin
itself needs review. Correlation error is not permission for coarse iteration.
Do not combine statistical and nonstatistical error bounds as independent
random errors without evidence. No common numerical fraction is frozen here.
Inherited 0.001 closure and scoped 0.02 shell-reference ceilings remain exactly
as in the main contract; they are not Newton/Brent stopping tolerances.

**Conclusion: PARTIALLY_CLOSED**, inherited acceptance/canonical sub-scope
only. Complete numerical profile, convergence and mesh authority remain absent.

## 7. GAP-DP — event-specific losses and state coupling

| Event | Existing evidence | Missing v0.7 authority |
| --- | --- | --- |
| Straight friction | TASK027 Darcy convention, laminar/Colebrook selection, explicit roughness/domain and fixed density/elevation assertions | Local-state pressure coupling and applicability of integration along heated path |
| Entrance | TASK028 bound irreversible K with explicit flow area, direction, planes and multiplicity | Geometry-qualified entrance coefficient/profile, reference velocity and Re domain |
| Exit | Same component authority mechanism | Downstream recovery/reference-plane and actual exit geometry coefficient |
| Pass turnaround | Source-bound unique event can be modeled only once | Header/pass geometry and independent K; pass subtotal cannot add it twice |
| U-bend/return | Pairing establishes connectivity only | Bend radius/D, angle, length, Re, coefficient definition and whether bend friction is included |
| Other local loss | Explicit source/permission/geometry authority required | No anonymous catch-all K or omitted physical term |
| Variable density | MSL distributed momentum distinguishes convective momentum from wall friction | Reviewed steady HX pressure formulation, local rho/mu/Re, acceleration/elevation and pressure iteration assumptions |

TASK028 `models.py` declares USACE2024.1 §6.2.1. The public source obtained
in this audit is **HEC-RAS7.0 Pipe Minor Losses**, not that exact revision.
It confirms local velocity-head/direction semantics, not an exchanger bend
catalog. The mismatch is recorded, not silently repaired: existing TASK028
authority remains unchanged; any new external-source claim must reconcile
the exact version/location before approval. Pipe-junction/culvert coefficients
cannot be transferred to a tube head solely because both use a K symbol.

TASK027 names IAEA2024/NETL2022 in its selection contract. Its existing
reviewed domain may be replayed; this audit does not pretend to have recovered
every underlying edition's equation/license bytes or expand that scope.
Gonçalves Eq78 is an aggregate head-loss convention, not the disjoint
entrance/exit/U-return event catalog requested here. Its coefficients are not
substituted into TASK028. TASK029 reference-plane completeness remains required.

Local friction proposals must bind local rho, mu, Re, area and flow, and state
whether pressure affects property evaluation. Acceleration and elevation are
not irreversible friction/local K events. They require their own signed
momentum accounting if applicable; no unsupported zero and no silent addition
to R2's loss subtotal. MSL's momentum option is evidence that the terms are
distinct, not authority to adopt its default. No new total-pressure equation
is frozen until that distinction and the actual reference planes are reviewed.

`tube_pass_dp` remains a derived reporting subtotal; every physical event
belongs to one component, and cell subdivision creates no new entrance,
bend, exit or baffle event. Missing required coefficients block, not K=0.

**Conclusion: PARTIALLY_CLOSED**, predecessor straight loss, component schema
and composition only. Detailed coefficients and variable-state closure remain
entry blockers for TASK174.

## 8. GAP-FIV — diagnostics versus transferable numerical limits

The full UCLA/DOE report (OSTI827838, award DE-FG03-00SF22169) was obtained.
This is additional evidence, not the previously inaccessible OSTI6887081
record. Its single-phase sections were inspected; two-phase findings are not
admitted. Printed pages differ from PDF index by three pages.

| Quantity | Exact evidence / remaining limit |
| --- | --- |
| Vortex frequency | §3.1.2.3 printedp54 Eq3.1 defines Strouhal from measured frequency and pitch velocity; observed array values are not a universal design coefficient |
| Natural frequency/support span | §2.1.2 pp19–24 uses wire-supported test tubes, adjustable frequency and specified arrays; not a general baffle-supported beam solution |
| Effective/added mass | §1.1–1.2 distinguishes mass/damping definitions across studies; no case-qualified HX added-mass law selected |
| Damping | Vacuum/air/water conventions differ; cannot interchange a damping ratio and logarithmic decrement without a bound conversion and medium |
| Fluidelastic critical velocity | Eq1.1 exposes a fitted relation; §1.2 and §3.1.2.4 show array/support dependence; no universally transferable K or exponent |
| Frequency/reduced-velocity ratios | Inherited TASK167 diagnostics require correct bound frequency, mass/density and velocity; no critical acceptance threshold follows |

TASK167 `vibration.py` exposes reduced velocity/mass-damping diagnostics and
leaves critical velocity absent. Its use of bulk velocity when crossflow is
unavailable, and optional added-mass handling, must **not** be promoted into
new physical assumptions. A v0.7 numerical profile needs explicit velocity
basis and explicit mass/medium authority; absent added mass is not proof it
is zero. This is an inheritance limitation, not a production change in R3.

```ini
FIV_BASIC_DIAGNOSTICS_AUTHORIZED=INHERITED_TASK167_SCOPE_ONLY
FLUIDELASTIC_NUMERICAL_SCREEN=BLOCKED
VORTEX_COEFFICIENT_PROFILE=UNBOUND
NATURAL_FREQUENCY_SUPPORT_PROFILE=UNBOUND
SCREENING_ONLY=true
FULL_MECHANICAL_ADEQUACY=false
```

Missing mandatory FIV evidence prevents candidate PASS and, where required
for recommendation, blocks recommendation. Optional NOT_COMPUTABLE can only
remain an explicit warning under a reviewed requirement policy; never false
PASS. No TEMA/API/ASME claim is added.

**Conclusion: PARTIALLY_CLOSED**, inherited source-transparent diagnostics
only. Public fitted data do not close an unqualified mechanical-input/domain
gap. `V07-FIV-QUALIFICATION-R3` remains PROPOSED_AUTHORITY.

## 9. GAP-REF — six candidate records, zero new Golden approvals

The candidate records below are screening outcomes, **not six admitted
fixtures**. Each JSON record identifies available source bytes/revision,
rights, geometry/fluid/operation coverage, output/uncertainty gaps and empty
approval fields. No normalized executable fixture hash or expected output is
invented when the fixture is absent. Missing values are explicitly null.

| Candidate ID / target | Evidence inspected | Why not a reviewed V07 Golden |
| --- | --- | --- |
| `V07-G01-CANDIDATE-R3` | Gonçalves2019 §5/Table1 and §6/Tables2–6: independent published model/design reference; geometry/stream values and shell h/DP results | Not a measured variable-state segmented exchanger oracle; upstream reference precision/source permissions and full target set need qualification. The paper's own revised numerical results cannot be relabeled experiment |
| `V07-G02-CANDIDATE-R3` | IAPWS SR6 property reference plus the published water-water experimental pool | Property sensitivity alone is not complete exchanger sensitivity. No matched variable/constant-property independent exchanger outputs or reviewed materiality threshold |
| `V07-G03-CANDIDATE-R3` | Sieder/Tate1936 publisher record; Martin/Gnielinski Appendix9.2 | First lacks accessible full data/domain; second normalizes crossflow HTC, not a full wall-iteration case with measured surfaces/outlets/duty. No active-wall oracle |
| `V07-G04-CANDIDATE-R3` | Prończuk/Krzanowska2021 full experimental paper §2.1, Fig1 and data reduction; CC-BY4 | Geometry is explicitly unbaffled minichannel, incompatible with full Bell path. REJECTED for this Golden use, not evidence to relax Bell; measured outputs cannot be fed back as solver inputs |
| `V07-G05-CANDIDATE-R3` | Existing TASK168 discrete authority and TASK169 ranking contracts; Gonçalves design comparison is a discovery cross-check | No independently reviewed V07 segmented candidate classifications/order/limits. No same-code expected result; no cost optimization imported |
| `V07-G06-CANDIDATE-R3` | IAPWS phase/domain boundaries and existing single-phase fail-closed boundary | Real domain-violation class is supportable, but exact future request/profile and blocker oracle have not been frozen/reviewed. No callback-induced exception or invented exhausted-iteration preset |

The minichannel experiment has real geometry and measurements, but no
segmental baffles; it therefore cannot close G01/G04 merely because its title
says shell-and-tube. Modelica BasicHX provides independent software architecture,
not a trusted full Bell experimental dataset. Existing V06 Goldens are immutable
regression authorities, not newly approved V07 wall/property references.

No complete six-Golden authority was obtained: **GAP-REF=OPEN**. Needed next:
legally reproducible in-envelope data with all required outputs, source
uncertainty and immutable payload, then independent review. G05 needs an
independent classification/ranking oracle; G06 needs a literal real-domain
negative and reviewed expected blocker after its profile is defined.

## 10. Closure and task-specific entry decisions

| Gap | Status | Only inherited reviewed sub-scope | Unresolved production remainder |
| --- | --- | --- | --- |
| SEG | PARTIALLY_CLOSED | Native geometry and Bell physical-region identities | Reviewed thermal path/cell mapping, Bell interface, discretization and N=1/mesh qualification |
| PROP | PARTIALLY_CLOSED | Backend/reference/snapshot semantics | Reviewed joint fluid profile, implementation verification and local-state domain |
| WALL | PARTIALLY_CLOSED | Cylindrical resistance/area conventions | Two surface states and source-complete wall correction/coupling |
| NUM | PARTIALLY_CLOSED | Existing scoped acceptance ceilings and replay | Numerical residual/budget/mesh/iteration profile |
| DP | PARTIALLY_CLOSED | Existing straight/component/composition scope | Event coefficients, geometry and variable-state pressure closure |
| FIV | PARTIALLY_CLOSED | Existing preliminary diagnostics | Support/mass/damping/array-qualified numerical profile |
| REF | OPEN | V06 regression retained, not a V07 sub-fixture | Six independently reviewed complete V07 fixtures |

| Task | Entry authority complete | Exact entry blockers | Not a prerequisite merely because it remains open |
| --- | --- | --- | --- |
| TASK171 | false | SEG-TOPOLOGY-REVIEW; SEG-CELL-COMPARTMENT-INTERFACE; SEG-CONSERVATION-DISCRETIZATION-REVIEW | Six approved Golden payloads, final FIV coefficients and final loss catalog do not by themselves block topology architecture; no numerical solver slice before its method qualification |
| TASK172 | false | TASK171-INTERFACE; PROP-PROFILE-REVIEW; WALL-CORRELATION-AND-SURFACES; NUM-PROFILE-REVIEW | Full six-Golden registry not intrinsically an entry gate; adequate profile-specific validation/error evidence still is |
| TASK174 | false | TASK171-INTERFACE; SEG-BELL-AGGREGATION; DP-EVENT-AND-STATE-AUTHORITY; FIV-REQUIRED-PROFILE | Optional diagnostic NC does not demand complete mechanical design; mandatory FIV must follow actual requirement policy |
| TASK173 | false | TASK172-CLOSURE; TASK174-CLOSURE; NUM-INTEGRATED-PROFILE | Cannot substitute a surrogate or last iterate for either prerequisite |
| TASK175 | false | TASK173-CLOSURE; REF-G01-THROUGH-G06; SEG-LEGACY-BRIDGE; V07-TOLERANCE-REVIEW; TRUSTED-PARITY-AND-24-GATES | Documentation CI is not release evidence |

The DAG remains 170 → 171 → {172,174} → 173 → 175. These booleans assess
authority readiness, not implementation or permission. Even a future true
entry decision needs separate user authorization. GAP-REF alone does not
block TASK171, but the specific missing SEG entry interface does. Conversely,
completed task-local entry evidence cannot authorize release with missing
Golden/precision evidence.

## 11. Review receipt and remaining action

```ini
AUTHORITY_REGISTRY_CREATED=true
SOURCE_REVIEW_COMPLETE=true
SOURCE_REVIEW_COMPLETE_MEANS=ALL_SEVEN_GAPS_AUDITED_NOT_ALL_AUTHORITY_OBTAINED
NEW_REVIEWED_AUTHORITY_COUNT=0
NEW_SUPPORTED_PRODUCTION_FLUID_COUNT=0
NEW_APPROVED_GOLDEN_COUNT=0
TASK171_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK174_ENTRY_AUTHORITY_COMPLETE=false
TASK173_ENTRY_AUTHORITY_COMPLETE=false
TASK175_RELEASE_AUTHORITY_COMPLETE=false
COMPLETE_AUTHORITY_FREEZE=BLOCKED
```

Independent review must resolve the listed source/domain/derivation/profile
and reference deficits. The research artifact is ready to be examined, but
is not self-approved. Legal full-text unavailability and unresolved scope
transfer remain explicit. No new formula, temperature tolerance, empirical
coefficient, mesh maximum or iteration count is supplied to conceal a gap.

Validation for this change: documentation/evidence allowlist, JSON identities,
source metadata consistency, relative links, seven gap states, per-task gates,
unchanged 24-gate and six-class definitions, whitespace, exact-head full CI.
CI is recorded on PR273 after the commit; embedding the final commit hash in
its own content is not required and would be circular. Successful CI validates
the documentation change, not the missing engineering authority. Stop at Draft.
