# TASK172 v0.7 — open-source reference architecture audit R1

## Receipt boundary

```ini
TASK_ID=TASK172_V0_7_OPEN_SOURCE_REFERENCE_ARCHITECTURE_AUDIT_R1
MODE=PINNED_PUBLIC_OPEN_SOURCE_ARCHITECTURE_AUDIT_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=53d4f3b7617407957b44662df1c3610720c3ca13
PREVIOUS_HEAD_SHA=53d4f3b7617407957b44662df1c3610720c3ca13
HEAD_PRECONDITION_VERIFIED=true
RESULT=COMPLETED_OPEN_SOURCE_ARCHITECTURE_AUDIT
```

This gate is a read-only architecture audit of five public repositories at
the pinned commits in the evidence file. It is not a source-authority gate,
physical-correlation transfer, numerical experiment, implementation, or
production qualification. No external code is vendored and no dependency is
added.

The external repositories are used only to answer how mature implementations
organize local heat transfer, wall state, sections, property state,
initialization, nonlinear closure, convergence and failure behavior. Their
formulas, coefficients, defaults, solver choices and tolerances are not
promoted to HXForge physical authority.

## 1. Pinned references and provenance

| Project | Pinned commit | Reviewed paths | License identity | Permitted role |
| --- | --- | --- | --- | --- |
| [IDAES/idaes-pse](https://github.com/IDAES/idaes-pse/commit/84532d7f99a9f976b05170948147afdd69cfa5f6) | `84532d7f99a9f976b05170948147afdd69cfa5f6` | `idaes/models/unit_models/shell_and_tube_1d.py`; `idaes/models/unit_models/heat_exchanger_1D.py`; `idaes/models/unit_models/tests/test_shell_and_tube_1D.py` | BSD text in `pyproject.toml` and `LICENSE.md` | Architecture, implementation pattern and test pattern reference only |
| [CalebBell/ht](https://github.com/CalebBell/ht/commit/85e0ee686ec91b35919925fd31d73d140a9de135) | `85e0ee686ec91b35919925fd31d73d140a9de135` | `ht/core.py`; `ht/conv_tube_bank.py`; `tests/test_core.py`; `tests/test_conv_tube_bank.py` | MIT in `pyproject.toml` and `LICENSE.txt` | Implementation, numerical crosscheck and test pattern reference only |
| [oemof/tespy](https://github.com/oemof/tespy/commit/18dc773f6ebbfedfc262df7087c768b1c74d2081) | `18dc773f6ebbfedfc262df7087c768b1c74d2081` | `src/tespy/components/heat_exchangers/sectioned.py`; `base.py`; `movingboundary.py`; heat-exchanger tests | MIT in `LICENSE` | Sectioned architecture, solver/test pattern reference only |
| [lbl-srg/modelica-buildings](https://github.com/lbl-srg/modelica-buildings/commit/a3cfdde4e2fa1605f351875c2199b6aafaee7fe0) | `a3cfdde4e2fa1605f351875c2199b6aafaee7fe0` | `DryCoilDiscretized.mo`; `BaseClasses/HexElementSensible.mo`; `PartialHexElement.mo`; `CoilRegister.mo`; `UsersGuide/License.mo` | Revised three-clause BSD with an additional improvements paragraph, as stated in `Buildings/UsersGuide/License.mo` | Finite-volume/state/flow-reversal architecture reference only |
| [jjgomera/pychemqt](https://github.com/jjgomera/pychemqt/commit/d34339ea62b719185baffd3cbf8b47b5cfd931a6) | `d34339ea62b719185baffd3cbf8b47b5cfd931a6` | `equipment/shellTube.py`; `LICENSE`; `setup.py` | GPL-3.0 in `LICENSE` and `setup.py` | Bell–Delaware implementation/numerical crosscheck only; code reuse forbidden |

The exact file SHA-256 values, access date, source role and rights boundary
are machine-recorded in the structured evidence. The reviewed commit pages and
source bodies were inspected from isolated temporary checkouts on
`2026-09-22`; the external bytes are not repository artifacts.

```ini
EXTERNAL_PROJECT_PHYSICAL_AUTHORITY_PROMOTION=false
DIRECT_CODE_IMPORT_AUTHORIZED=false
NEW_DEPENDENCY_AUTHORIZED=false
EXTERNAL_CODE_VENDORED=false
```

## 2. Findings by project

### 2.1 IDAES

At the pinned `shell_and_tube_1d.py`, the model declares a distributed
`temperature_wall` variable (lines 280–285) and separate hot/cold heat-transfer
constraints (lines 287–325). The hot and cold control volumes provide local
property/state fields over the length domain. Its initializer first initializes
both control volumes, fixes the wall temperature to a temporary average of the
initial hot/cold temperatures, deactivates the cold-side and heat-conservation
constraints, solves, then reactivates the constraints, unfixes the wall and
solves the full model (lines 355–422). Heat-transfer and conservation
constraints receive scaling factors (lines 448–476), and a non-optimal final
termination raises `InitializationError` (lines 416–420).

`heat_exchanger_1D.py` separately contains a fixed-duty initialization path
(lines 233–279) and explicit co-current/counter-current flow-direction setup
(lines 602–644). The generic fixed duty in that initializer is a temporary
initialization option, not evidence that a native local constitutive model must
receive an externally reviewed Q. The tests exercise both flow patterns and
explicitly test initialization failure (`test_shell_and_tube_1D.py`, around
lines 1640–1742).

This supports staged initialization, explicit local state domains, constraint
activation/deactivation, scaling and fail-before-success handling. It does not
establish HXForge's two-surface wall choice, signed negative-`q_hc` policy,
`J_mu^(0)=1`, or any physical pressure convention.

### 2.2 `ht`

`ht/core.py` separates bulk and wall properties in `wall_factor_fd` and
`wall_factor_Nu` (lines 273–400). `wall_factor` selects a property/temperature
relation and rejects missing wall inputs with `TypeError` (lines 407–498).
`is_heating_temperature` and `is_heating_property` make heating/cooling a
state relation rather than an equipment-side identity (lines 166–213). The
Bell helpers in `conv_tube_bank.py` implement and test `Jc`, `Jl`, `Jb`, `Js`
and `Jr` (roughly lines 1119–1553), while the tests provide reference-value
and missing-input behavior.

These are useful implementation and test patterns: explicit bulk/wall inputs,
fail-closed missing wall data, method selection and reference-value tests. The
empirical exponents, coefficients, defaults, clipping and helper semantics are
library choices and remain crosscheck-only. The reviewed files do not establish
HXForge stream-role identity, signed local heat-rate semantics, or a coupled
wall-temperature solve.

### 2.3 TESPy

`SectionedHeatExchanger` describes internal sectioning, section heat transfer,
section-boundary temperatures, wall conduction resistance and aggregate UA
(`sectioned.py`, lines 34–43 and 221–305). Section boundaries are explicitly
constructed (`sectioned.py`, lines 841–854 and 1034–1057); section heat and
temperature arrays are post-solve results (`base.py`, lines 1437–1466). The
base heat-exchanger energy balance is an explicit residual over both streams
(`base.py`, lines 587–641), and pressure ratios are separate connection/network
quantities (`base.py`, lines 200–208 and 555–576). Tests verify section endpoint
alignment and heat conservation (`test_heat_exchangers.py`, lines 874–952),
and exercise a negative-pinch failure path with `NaN` post-processing (lines
954–966).

TESPy therefore supports a section-local result profile and the distinction
between an input-constrained Q mode and a solved-Q/UA mode. It does not provide
the two explicit wall surface unknowns or HXForge's R85/R85A role contract in
the reviewed files.

### 2.4 Modelica Buildings

`DryCoilDiscretized.mo` composes registers and pipe segments (lines 25–37,
101–132). `CoilRegister.mo` instantiates an array of explicit elements, exposes
fluid ports and heat ports, and carries `allowFlowReversal1/2` independently
from medium identity (lines 20–25, 43–74 and 77–116). `PartialHexElement.mo`
connects two fluid-side convection elements to a shared metal heat capacitor
(lines 36–83) and documents the metal energy state and its heat capacity
(lines 94–125). The dry-coil documentation describes one metal state per
smallest pipe element and adds thermal conductance between elements to mitigate
near-zero-flow temperature separation (lines 420–467). Temperature expressions
select medium states under flow-reversal conditions without changing medium
identity (`DryCoilDiscretized.mo`, lines 264–302).

This is strong architecture evidence for finite-volume identity, explicit
fluid/solid state separation, flow reversal without hot/cold reassignment,
zero-flow mitigation and nonlinear-system organization. It does not establish
HXForge's property authority, J_mu exponent/domain, pressure rule or signed
negative-heat disposition.

### 2.5 pychemqt

`equipment/shellTube.py` makes tube and shell streams explicit in the equipment
input organization (lines 291–423). Its Bell–Delaware path computes the
correction composition and shell HTC (lines 658–889), including `Jc`, `Jl`,
`Jb`, `Js` and `Jr` (lines 701–742), with edge branches for Reynolds number and
sealing strips. It consumes the current shell-stream property object for
viscosity, Prandtl number, density and heat capacity (lines 682–686). A separate
Kern helper contains a wall-viscosity-looking expression (line 897), but it is
not evidence of a reviewed TASK172 J_mu contract. The separate cost routine
uses design pressure (lines 911–915), which is unrelated to local property
evaluation.

pychemqt is GPL-3.0. It is therefore a numerical/implementation crosscheck
only; no GPL code or formula implementation is imported into HXForge, and no
pychemqt behavior is promoted to physical authority.

## 3. Mandatory comparison matrix

`NOT_ESTABLISHED_FROM_REVIEWED_CODE` is used wherever the pinned paths did
not establish the requested property. External values are observations of
implementation structure, not HXForge requirements.

| Dimension | HXForge effective R84/R85A | IDAES | `ht` | TESPy | Modelica Buildings | pychemqt |
| --- | --- | --- | --- | --- | --- | --- |
| Local heat rate | `q_hc` signed unknown; local duty is derived/output | Heat variables constrained locally; initializer may temporarily fix a path | Not a heat-exchanger network; HTC/correction output only | Q may be specified or solved; `Q_per_section` is post-solve output | Element heat-port flow and aggregate `Q1_flow/Q2_flow` outputs | Shell HTC and pressure-drop result; local Q not established |
| Wall temperature | `T_wall_inner`, `T_wall_outer` unknowns | One distributed `temperature_wall` variable | Wall temperature/property is an explicit helper input, not a wall state | Explicit wall temperature state not established; `R_cond`/UA are present | One lumped metal state per element plus two fluid-side convection interfaces | Wall-temperature state not established in reviewed file |
| Wall/interface multiplicity | Two surfaces; add nodes only if an admitted correlation requires them | One wall field in reviewed model | Bulk/wall property pair, no metal state | No explicit surface state in reviewed paths | One metal state with two fluid interfaces | Not established |
| Bulk property state | Located TASK171 local state and property authority | Control-volume property/state fields over length domain | Bulk property and wall property are separate inputs | Connection/network thermodynamic states; section values derived | Medium volume states | Shell stream `Liquido` property object |
| Wall property state | Shell-side interface property owned by J_mu contract | Not established in reviewed paths | Explicit wall property or wall temperature relation | Not established | Solid/medium states, not a reviewed wall-viscosity property rule | Not established for Bell path |
| Pressure source | Located local shell pressure state; hydraulic owner outside TASK172 | Local control-volume state; exact wall-property pressure rule not established | Pressure not part of reviewed wall-factor API | Connection p and pressure-ratio/network equations | Fluid port/volume pressure state | Stream pressure/design pressure usages; no local mean rule |
| Hot/cold vs equipment side | Explicit TASK171 role plus `s_ts`; no inference | Explicit hot/cold blocks; flow pattern separate | No equipment-side role model in reviewed helpers | Component side 1/2 and hot-side Q convention | Medium/port identity and flow direction separate | Named tube/shell inputs; no explicit hot/cold role contract |
| Signed heat rate | Signed `q_hc`; positive HOT→COLD; no clamp; negative disposition unbound | Hot/cold signs in transfer equations; negative policy not established | Not established | Hot-side Q convention and signed section accounting; R85 semantics not established | Connector heat-flow signs; role-policy not established | Not established |
| Section/cell identity | Physical-support keyed TASK171 identity | Length-domain discretization | Not established | Configurable section boundaries and arrays | Register/pipe/segment array identity | Whole-equipment method |
| Local energy residual | `r_i`, `r_w`, `r_o` | Heat-transfer and conservation constraints | No network residual | Network energy balance plus section heat reconstruction | Equation system over fluid/metal components | Not established |
| Wall conduction | Explicit `r_w` and `R_wall` | Not established as a separate two-surface equation | Not established | `R_cond` in UA construction | Metal heat capacitor and convection connections | Not established |
| HTC coupling | Tube/shell HTC coupled to wall states and J_mu | Local HTC variables and wall-temperature constraints | Wall-factor helper wraps a base correlation | Alpha/UA and section equations | Conductance inputs/functions coupled to element states | Bell composition returns shell HTC |
| Wall-property correction | J_mu physical authority remains separate/open | Not established | Bulk/wall correction helper; crosscheck only | Not established | Not established | Separate non-authoritative wall-viscosity-looking helper only |
| Initialization | Future staged architecture; not implemented | Initialize CVs; temporary wall fix/deactivate constraints; full restore | Stateless helper calls; missing inputs reject | Two-stage design/offdesign example; network initialization | Initial conditions, dynamics and pressure initialization | Input/method validation in equipment path |
| Nonlinear-system organization | Three primary unknowns/three residuals; method unbound | Block initialization then full simultaneous model solve | Direct correlation functions | Network residuals with section post-processing | Equation-based element network; finite-volume composition | Procedural calculation path |
| Simultaneous vs staged solution | Staged initialization recommended; production solver unbound | Staged initialization then full solve | Direct function evaluation | Network solve; staged design/offdesign usage | Simultaneous equation system with dynamic/initial modes | Procedural staged calculations |
| DOF management | Explicit model-level 3/3 contract | Constraint activation/fix/unfix and control-volume structure | Function argument validation | Network parameter/input/output modes | Connector/equation balance and conditional dynamics | `isCalculable`/input checks |
| Residual scaling | Numerical profile remains open | Explicit constraint scaling | Not established | Not established in reviewed paths | Equation-system tool/runtime behavior; not established as a project field | Not established |
| Convergence/stopping | Separate TASK172 numerical profile/error-budget gate | Solver termination checked; no HXForge threshold | No nonlinear stopping | Network convergence assertion/status | Simulation initialization/dynamics; no HXForge criterion | No local convergence contract |
| Iteration failure | Fail closed by future contract | `InitializationError` on non-optimal termination | Missing wall input raises `TypeError` | Nonconvergence/invalid pinch can yield status/`NaN` | Translation/initialization/runtime failure semantics; exact policy not established | Input errors/exceptions; exact closure policy not established |
| Zero flow | Future local contract; no implementation | Not established in reviewed paths | Not established | Not established as zero-flow wall policy | Near-zero-flow diffusion conductors and flow-reversal guards | Not established |
| Reverse heat flow / flow reversal | Signed q admitted; role immutable; negative disposition open | Flow pattern explicit; reverse heat policy not established | Heating/cooling relation from state values | Hot/cold convention; reverse policy not established | `allowFlowReversal` changes flow direction, not medium identity | Not established |
| Mesh/section refinement | Mesh convergence authority remains open | Finite-element/collocation domain configuration | Not established | `num_sections` and section arrays | `nPipSeg`, registers and element arrays | Not established |
| Tests/oracles | Governance evidence only; no runtime execution here | Initialization, flow-pattern and failure tests | Reference values and missing-input tests | Section alignment, heat-sum, pinch/failure tests | Examples and equation-based model structure | Numerical Bell crosscheck path |
| Deterministic replay | Canonical identity/provenance required | Not established as HXForge-style receipt | Function inputs deterministic in reviewed paths | Network state/save/replay pattern present in examples | Parameterized equation model; exact receipt not established | Procedural input path; exact receipt not established |

## 4. Explicit TASK172 questions

### Q1 — local Q

**Finding: architecture supported.** IDAES solves heat-transfer variables from
local constraints after temporary initialization; TESPy exposes section heat as
post-solve output while also supporting a separately constrained Q mode; and
Modelica exposes element heat-port flows and aggregate heat-flow outputs. This
supports R84's `LOCAL_Q_IS_CONSTITUTIVE_UNKNOWN_OR_OUTPUT=true` and
`EXTERNAL_Q_REQUIRED_FOR_NATIVE_LOCAL_WALL_CLOSURE=false`. It does not delete
the external-Q input/validation contract for a separately admitted mode.

### Q2 — wall temperature

**Finding: explicit wall state is supported; surface multiplicity is
project-specific.** IDAES uses one distributed wall temperature. Modelica uses
a metal state connected to two fluid-side convection interfaces. TESPy uses
section resistance/UA rather than an explicit two-surface wall state in the
reviewed paths. R85A's two-surface minimal state remains a coherent HXForge
architecture. If a future admitted correlation needs a distinct fluid/fouling
interface or metal surface, it must add an explicit node and residual rather
than aliasing identities. No equation is changed by this audit.

### Q3 — initialization

**Finding: supported as software architecture.** IDAES temporarily fixes and
simplifies the coupled model, solves an initialization problem, restores the
full constraints and solves again. Modelica separates initial conditions and
dynamic/steady formulations. Therefore
`PRELIMINARY_SHELL_FILM_ROLE=NUMERICAL_INITIALIZATION_STATE_ONLY` is a
reasonable architecture pattern. This is not physical authority for a
preliminary film correlation.

### Q4 — J_mu initialization

**Finding: initialization analogy supported; `J_mu^(0)=1` is not externally
authorized.** IDAES demonstrates a temporarily neutral/simplified coupled
initialization path. The reviewed external code does not establish the exact
HXForge neutral factor, J_mu exponent, property domain or update rule. The
result is `INITIALIZATION_PATTERN_ANALOGY=SUPPORTED` only; the R84 candidate
`J_mu^(0)=1` remains a project convention candidate and is not a physical
authority or executed algorithm.

### Q5 — solver form

**Finding: review a block/staged initialization followed by a simultaneous
vector nonlinear solve; do not select it here.** IDAES and Modelica provide the
strongest architecture analogies for a coupled equation system with explicit
initialization and restoration. TESPy demonstrates a network residual solve
with section post-processing. The reviewed code does not prove a scalar
reduction for HXForge's wall/J_mu equations. Therefore scalar reduction is
`UNDETERMINED`, vector nonlinear review is recommended, and no solver,
bracket, tolerance, iteration cap or relaxation factor is selected.

### Q6 — signed heat semantics

**Finding: external implementations use explicit signs or flow-direction
conventions, but none overrides R85/R85A.** IDAES has signed hot/cold transfer
equations; TESPy uses a hot-side Q convention and signed section accounting;
Modelica uses connector heat-flow signs and independently configurable flow
reversal. The reviewed projects do not establish HXForge's negative-`q_hc`
applicability disposition or immutable TASK171 role identity. R85A therefore
remains unchanged: signed unknown, no absolute-value substitution, no
non-negative clamp, and no iterative role reassignment.

## 5. Recommendation layer

### A — adoptable architecture patterns

The following patterns are supported by reviewed code and may inform the next
TASK172 design gate:

1. staged initialization with temporary constraint simplification followed by
   restoration of the complete coupled equations;
2. explicit wall/interface state variables rather than hidden defaults;
3. physical-support/section-local state and result identity;
4. explicit DOF accounting and constraint activation/fix/unfix boundaries;
5. residual scaling or equivalent conditioning review before full solve;
6. failure-before-success: non-optimal initialization, invalid section
   temperature differences or missing wall inputs must not be reported as a
   valid local result;
7. separate flow-direction/equipment identity from hot/cold or medium identity.

These are design recommendations only.

### B — numerical or test crosscheck only

Use the pinned `ht` and pychemqt Bell correction implementations, TESPy section
profiles and IDAES/ht/TESPy reference tests only as crosschecks or test-design
patterns after HXForge source authority and scope are independently bound.
Reference values, wall-factor failure tests, section heat-sum checks and pinch
checks do not authorize a formula, coefficient, pressure convention or
production tolerance.

### C — do not import as authority

Do not import external formulas, Bell/Delaware coefficients, wall-factor
exponents, library defaults, clipping rules, solver defaults, tolerance values,
section counts, pressure conventions, Modelica medium assumptions, TESPy
offdesign conventions or pychemqt GPL code. Do not use the existence of an
implementation, a passing external test or a license-compatible repository as
an HXForge physical-authority transfer.

## 6. Recommended next design direction

```ini
TASK172_RECOMMENDED_LOCAL_SOLVER_ARCHITECTURE=BLOCK_INITIALIZATION_THEN_SIMULTANEOUS_VECTOR_NONLINEAR_REVIEW
TASK172_RECOMMENDED_INITIALIZATION_ARCHITECTURE=STAGED_INITIALIZATION_WITH_TEMPORARY_SIMPLIFICATION_AND_FULL_EQUATION_RESTORE
TASK172_RECOMMENDED_WALL_STATE_ARCHITECTURE=TWO_SURFACE_WALL_STATE_PRESERVED_INTERFACE_NODES_ONLY_IF_REQUIRED
TASK172_RECOMMENDED_SECTION_STATE_ARCHITECTURE=PHYSICAL_SUPPORT_KEYED_LOCAL_STATE_WITH_EXPLICIT_SECTION_IDENTITY
SCALAR_REDUCTION_RECOMMENDED_FOR_NEXT_GATE=UNDETERMINED
VECTOR_NONLINEAR_REVIEW_RECOMMENDED=true
STAGED_INITIALIZATION_RECOMMENDED=true
EXTERNAL_Q_DEPENDENCY_CORRECTION_SUPPORTED_BY_REFERENCE_ARCHITECTURES=true
REAL_CASE_AS_MODEL_PREREQUISITE_SUPPORTED_BY_REFERENCE_ARCHITECTURES=NOT_AS_MODEL_LEVEL_PREREQUISITE
```

These recommendations do not select a production solver. The minimal next
design gate is a separately authorized local constitutive numerical-method and
failure-contract review, with physical J_mu/wall authority gaps still
explicitly open.

## 7. Preserved ownership, semantics and blockers

The audit preserves the R84 architecture and R85/R85A sign-role semantics:

```ini
Q_HC_IS_SIGNED_UNKNOWN=true
Q_HC_POSITIVE_MEANS_HOT_TO_COLD=true
Q_HC_ZERO_MEANING=ZERO_LOCAL_HEAT_TRANSFER
Q_HC_NEGATIVE_ALLOWED_AT_MODEL_LEVEL=true
Q_HC_NEGATIVE_DISPOSITION=UNBOUND_PENDING_APPLICABILITY_AND_FAILURE_POLICY
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
Q_HC_NONNEGATIVE_CLAMP_FORBIDDEN=true
HOT_COLD_ROLE_IS_EXPLICIT_TASK171_IDENTITY=true
HOT_COLD_ROLE_REASSIGNMENT_DURING_LOCAL_ITERATION=false
S_TS_ALLOWED_VALUES=+1;-1
Q_TS_RELATION=q_ts=s_ts*q_hc
L2B_ACTUAL_UNKNOWN_SET=q_hc;T_wall_inner;T_wall_outer
L2B_UNKNOWN_COUNT=3
L2B_ACTUAL_RESIDUAL_SET=r_i;r_w;r_o
L2B_EQUATION_COUNT=3
JMU_SHELL_SIDE_INTERFACE_OWNERSHIP_PRESERVED=true
```

The four parent blockers remain open and are not closed by this audit:

```text
SHELL-WALL-CORRECTION-AUTHORITY
LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION
NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW
MESH-CONVERGENCE-QUALIFICATION
```

```ini
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
EXTERNAL_CODE_VENDORED=false
TASK172_IMPLEMENTATION_STARTED=false
PHYSICAL_AUTHORITY_PROMOTED_FROM_OPEN_SOURCE=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

## 8. Final receipt

```ini
TASK_ID=TASK172_V0_7_OPEN_SOURCE_REFERENCE_ARCHITECTURE_AUDIT_R1
RESULT=COMPLETED_OPEN_SOURCE_ARCHITECTURE_AUDIT
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=53d4f3b7617407957b44662df1c3610720c3ca13
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
IDAES_REVIEWED=true
HT_REVIEWED=true
TESPY_REVIEWED=true
MODELICA_BUILDINGS_REVIEWED=true
PYCHEMQT_REVIEWED=true
LICENSE_CLASSIFICATION_COMPLETE=true
DIRECT_CODE_IMPORT_AUTHORIZED=false
NEW_DEPENDENCY_AUTHORIZED=false
PHYSICAL_AUTHORITY_PROMOTED_FROM_OPEN_SOURCE=false
LOCAL_Q_REFERENCE_ARCHITECTURE_FINDING=SUPPORTED_AS_CONSTITUTIVE_UNKNOWN_OR_OUTPUT;EXTERNAL_Q_ONLY_OPTIONAL_INPUT_OR_VALIDATION_MODE
WALL_STATE_REFERENCE_ARCHITECTURE_FINDING=EXPLICIT_WALL_STATE_SUPPORTED;ONE_OR_MULTIPLE_SURFACES_PROJECT_SPECIFIC
INITIALIZATION_REFERENCE_ARCHITECTURE_FINDING=STAGED_TEMPORARY_SIMPLIFICATION_THEN_FULL_RESTORE
SEGMENT_STATE_REFERENCE_ARCHITECTURE_FINDING=SECTION_LOCAL_STATES_AND_POSTSOLVE_PROFILES_SUPPORTED
SIGNED_HEAT_REFERENCE_ARCHITECTURE_FINDING=EXTERNAL_SIGN_CONVENTIONS_EXIST_BUT_NO_DIRECT_R85_OVERRIDE
TASK172_RECOMMENDED_LOCAL_SOLVER_ARCHITECTURE=BLOCK_INITIALIZATION_THEN_SIMULTANEOUS_VECTOR_NONLINEAR_REVIEW
TASK172_RECOMMENDED_INITIALIZATION_ARCHITECTURE=STAGED_INITIALIZATION_WITH_TEMPORARY_SIMPLIFICATION_AND_FULL_EQUATION_RESTORE
TASK172_RECOMMENDED_WALL_STATE_ARCHITECTURE=TWO_SURFACE_WALL_STATE_PRESERVED_INTERFACE_NODES_ONLY_IF_REQUIRED
SCALAR_REDUCTION_RECOMMENDED_FOR_NEXT_GATE=UNDETERMINED
VECTOR_NONLINEAR_REVIEW_RECOMMENDED=true
STAGED_INITIALIZATION_RECOMMENDED=true
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_MINIMAL_GATE=AUTHORIZE_TASK172_LOCAL_CONSTITUTIVE_NUMERICAL_METHOD_AND_FAILURE_CONTRACT_R1_ONLY
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
EXACT_FINAL_HEAD_CI_RUN=RECORDED_IN_FINAL_RECEIPT
EXACT_FINAL_HEAD_CI=RECORDED_IN_FINAL_RECEIPT
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
