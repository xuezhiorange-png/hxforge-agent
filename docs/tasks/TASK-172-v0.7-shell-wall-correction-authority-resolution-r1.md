# TASK172 R1 — native Bell shell-wall correction authority resolution

## 1. Receipt and boundary

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_AUTHORITY_RESOLUTION_R1
PR=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=0ac9bfd307dca82cb30928a643b71424e16063c2
MODE=SHELL_WALL_CORRECTION_NATIVE_TARGET_AND_AUTHORITY_RESOLUTION_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
PRODUCTION_CODE_CHANGED=false
TASK166_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This is an append-only authority-resolution receipt. It freezes the current
TASK-166 native Bell target, reconstructs the source roles and negative
lineage, and decides whether an existing Bell-compatible wall-property
authority is available. It does not implement or select a shell correction,
does not change TASK-166, and does not remove
`SHELL-WALL-CORRECTION-AUTHORITY`.

## 2. Exact native TASK-166 target

The native implementation is the fixed-geometry Bell–Delaware shell-side
path. Its source and implementation identities are inherited exactly:

```ini
NATIVE_SHELL_TASK_ID=TASK-166
NATIVE_SOURCE_DEFINITION_ID=TASK165_R3_BELL_DELAWARE_SOURCE_AUTHORITY_V1
NATIVE_METHOD=BELL_DELAWARE
NATIVE_IDEAL_HTC_FORM=ji*cp*G*Pr^(-2/3)
NATIVE_CORRECTED_HTC_FORM=ideal_h*Jc*Jl*Jb*Js*Jr
NATIVE_CORRECTION_FACTORS=Jc;Jl;Jb;Js;Jr
NATIVE_RE_EVALUATOR_DOMAIN=0<Re_s<=100000
```

`heat_transfer.py` obtains Reynolds, Prandtl and mass velocity from the
accepted shell-side flow state. Density and dynamic viscosity are read from
the accepted property map, but these are shell-fluid bulk property inputs;
the code contains no wall-property argument, wall-temperature state, or
bulk-to-wall property ratio. `flow_specific_heat()` likewise reads the
accepted shell property snapshot and does not evaluate a wall state.

```ini
NATIVE_WALL_VISCOSITY_INPUT_PRESENT=false
NATIVE_WALL_TEMPERATURE_INPUT_PRESENT=false
NATIVE_BULK_WALL_PROPERTY_RATIO_PRESENT=false
```

The domain above is the effective evaluator domain: the source-row selector
covers `0 <= Re_s <= 100000`, while the typed input guard rejects non-positive
and non-finite values. There is no interpolation or extrapolation across the
source Reynolds rows.

### 2.1 Factor-by-factor classification

The current corrected coefficient is a product of the following source-bound
factor roles:

| Factor | Current native role | Wall-property correction? | Native inputs |
| --- | --- | --- | --- |
| `Jc` | baffle/window pure-crossflow fraction correction | No | `Fc`, baffle geometry |
| `Jl` | shell-to-tube / shell-to-baffle leakage correction | No | `r_s`, `r_lm`, leakage geometry |
| `Jb` | bundle-to-shell bypass correction | No | `Fsbp`, source `Cbh`, bypass geometry |
| `Js` | unequal baffle-spacing correction | No | inlet/central/outlet spacing, `N_b`, Re branch |
| `Jr` | low-Reynolds crossed-row correction | No | central crossflow tube-row count `N_c`, Re branch |

The code and TASK-166 contract therefore establish:

```ini
JC_IS_ACTIVE_WALL_PROPERTY_CORRECTION=false
JL_IS_ACTIVE_WALL_PROPERTY_CORRECTION=false
JB_IS_ACTIVE_WALL_PROPERTY_CORRECTION=false
JS_IS_ACTIVE_WALL_PROPERTY_CORRECTION=false
JR_IS_ACTIVE_WALL_PROPERTY_CORRECTION=false
JR_PHYSICAL_MEANING=LOW_REYNOLDS_CROSS_FLOW_TUBE_ROW_CORRECTION
JR_USES_MU_WALL=false
JR_USES_WALL_TEMPERATURE=false
```

`Jr` is not a viscosity-ratio term merely because it acts in the low-Reynolds
branch. Its source projection records Reynolds and crossed-row count, not
`mu_wall`, wall temperature, or a wall Prandtl number.

## 3. Wall target identity and current lifecycle

The physical target requested by TASK172 is an active wall-to-bulk property
correction for the shell-side heat-transfer coefficient. Its reference
surface is the shell-fluid wall interface, not the shell bulk snapshot and
not the TASK034 pressure-drop wall state.

```ini
SHELL_WALL_CORRECTION_PHYSICAL_TYPE=WALL_VISCOSITY_CORRECTION
SHELL_WALL_CORRECTION_REFERENCE_SURFACE=SHELL_FLUID_WALL_INTERFACE
WALL_TEMPERATURE_STATE_AUTHORITY_ID=V07-T172-WALL-TEMPERATURE-STATE-R1
WALL_TEMPERATURE_STATE_LIFECYCLE=PROPOSED_AUTHORITY
SHELL_FLUID_WALL_INTERFACE_IDENTITY_DEFINED=true
SHELL_FLUID_WALL_INTERFACE_RUNTIME_AVAILABLE=false
```

The wall-state definition names `SHELL_FLUID_WALL_INTERFACE` and binds it to
physical support and the clean-surface alias
`TUBE_METAL_OUTER_SURFACE`. The definition is not a solved runtime state: its
authority lifecycle remains `PROPOSED_AUTHORITY`, and no implementation is
available at this head. A defined target therefore cannot be treated as a
supplied shell wall temperature.

The current TASK172 admitted target is the initial fixed-tubesheet scope:

```ini
TASK166_NATIVE_CONSTRUCTION_FAMILIES=FIXED_TUBESHEET,U_TUBE,FLOATING_HEAD
TASK172_CURRENT_ADMITTED_CONSTRUCTION_FAMILY=FIXED_TUBESHEET
TASK166_NATIVE_APPLICABILITY_TO_TASK172_TARGET=TASK166_BELL_FIXED_GEOMETRY_SHELL_PATH_FOR_FIXED_TUBESHEET_E_SHELL_SINGLE_SEGMENTAL_SINGLE_PHASE_NEWTONIAN_ONE_SHELL_PASS_LAYOUT_30_DEG_OR_45_DEG_OR_90_DEG_0<RE_S<=100000;NO_WALL_CORRECTION_AUTHORITY
```

The v0.6 construction-family applicability correction does not add a
family-specific mechanical or wall-property model. It does not change the
need for an exact wall-correction authority if TASK172 activates one.

## 4. Source-role reconstruction and body availability

The source hierarchy is deliberately non-blending. “Body available” below
means that the exact source body was available for the stated audit role; it
does not mean that the body is vendored or that every source role is
transferable.

| Source ID | Role in TASK-166 | Body/evidence status | Exact authority boundary |
| --- | --- | --- | --- |
| `SRC-UDEL-BELL-1963-FINAL-REPORT` | Bell method origin and provenance | Metadata-only in the effective repository authority; no report body/hash is bound for equation review | Historical origin only; not an active correction authority |
| `SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE` | Selected primary implementation source | Public article body was available and the cited sections were reviewed; copyrighted copy is not vendored; source identity/hash is `fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54` | Bell geometry, ideal bank/heat-transfer relations, correction semantics and DP relations at the selected locations |
| `SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS` | Parameter supplement | Accepted-manuscript bytes are identified by the existing hash | `a1–a4` and `b1–b4` table rows only |
| `SRC-SAIF-TARIQ-2025-JMES-UNEQUAL-BAFFLE-SPACING-JS` | Unequal-spacing supplement | Existing source identity/hash is retained | Heat-transfer `Js` only |
| `TASK032_ACCEPTED_SHELL_SIDE_FLOW_STATE` | Upstream shell-side flow-state producer | Reviewed repository contract | Accepted Re, Pr, mass velocity and bulk property snapshot; no wall state |
| `REPO-BELL` | Native implementation contract | Reviewed repository authority | Current TASK-166 source identifiers and `heat_transfer.py`; no wall-property extension |
| `V07-T172-WALL-TEMPERATURE-STATE-R1` | TASK172 wall-state target | Definition-level proposal only | Surface identity and future state binding; no solved runtime state |

The machine-readable record reports this distinction explicitly:

```ini
BELL_ORIGIN_BODY_AVAILABLE=false
BELL_ORIGIN_WALL_PROPERTY_CORRECTION_PRESENT=false
BELL_ORIGIN_WALL_PROPERTY_CORRECTION_COMPLETE=false
GONCALVES_BODY_AVAILABLE=true
GONCALVES_SHELL_HEAT_TRANSFER_WALL_PROPERTY_CORRECTION_PRESENT=false
GONCALVES_WALL_PROPERTY_CORRECTION_COMPLETE=false
```

For Bell's 1963 origin, `false` means that the current authority contains
only the method-origin metadata and cannot support an equation-level finding;
it is not a claim about every page of the historical report. For Gonçalves,
the cited body is available, and the selected Bell ideal/correction locations
do not provide a complete active shell wall-property multiplier with the
required state definitions and transfer rule.

The exact selected locations are:

* TASK-166 §5, Gonçalves Eqs. 37–43: ideal shell-side heat transfer and
  `Jc/Jl/Jb/Jr` correction relations;
* TASK-166 §5, Saif/Tariq Eq. 21 supplement: `Js` unequal-spacing relation;
* TASK-166 §8: variable-property iteration and wall-temperature iteration are
  outside the native TASK-166 implementation;
* TASK172 wall-state definition §8: the future shell correction target is
  `SHELL_FLUID_WALL_INTERFACE`, with no source-bound correction yet.

Neither the Jamil parameter supplement nor the Saif/Tariq `Js` supplement
adds a shell wall-property correction. The fact that TASK-166 reads bulk
`rho`, `mu`, `cp` and `Pr` is not evidence for a wall-property ratio.

## 5. Required correction fields versus observed native fields

An admissible TASK172 shell correction would have to bind all of the
following without borrowing from another method:

```text
exact base correlation identity and version
complete correction equation and every coefficient/exponent
bulk state location and wall-fluid state location
property ratio and property evaluation basis
heating/cooling or heat-direction semantics
Re, Pr, ratio and geometry/layout/roughness domains
thermal boundary and developing-flow assumptions
combination rule with native Bell h_s and J factors
surface/area basis and physical support
source body, revision, rights and evidence
```

The native target supplies none of the wall-specific fields:

| Required field | Native TASK-166 evidence | Resolution |
| --- | --- | --- |
| shell bulk state | TASK-032 bulk property snapshot and Re/Pr inputs | Existing upstream input; not wall authority |
| shell wall state | No TASK-166 field; TASK172 definition is not runtime | Missing |
| `mu_b/mu_w` or equivalent | No wall-property ratio | Missing |
| correction equation/domain | `Jc/Jl/Jb/Js/Jr` are not wall corrections | Missing |
| Bell combination rule | No active wall factor is specified | Missing |
| case-level shell property/wall snapshot | No TASK172 implementation | Missing and fail-closed |

## 6. Negative lineage and non-transfer decisions

The following transfers are explicitly rejected:

```ini
TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TASK033_KERN_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
```

* TASK034's Bayram–Sevilgen `(mu_b/mu_w)^(7/50)` term is a shell pressure-drop
  `phi_s` term with its own method, output, Reynolds domain and identity. It
  cannot be multiplied onto Bell `h_s`.
* TASK033's Kern relation is a separate shell heat-transfer method explicitly
  identified as `NO_WALL_CORRECTION`; it is not a Bell supplement.
* Martin/Gnielinski is an external crossflow-bundle normalization source. It
  does not demonstrate transfer to an internal pipe correlation or to Bell.
* The TASK026/RELAP tube correction lineage is tube-side and cannot be
  transferred to the shell-side Bell method.

These are source/identity decisions, not claims that the rejected sources are
scientifically useless in their own domains.

## 7. Resolution outcome

The three possible reuse dispositions do not close the blocker:

* **Outcome A is unavailable:** no existing Bell-compatible active wall
  correction candidate has a complete equation, state definitions, domain and
  combination rule.
* **Outcome B is not established:** absence of a wall factor in the selected
  implementation equations is not an explicit reviewed authority that TASK172
  may omit a required active wall-property correction. The TASK-166
  non-scope is not an omission qualification for the new capability.
* **Outcome C is not established:** no source-bound, independently reviewed
  “no extension required” disposition exists for the Bell target.

Therefore the fail-closed resolution is:

```ini
RESOLUTION_OUTCOME=NEW_BELL_COMPATIBLE_PRIMARY_SOURCE_AUTHORITY_REQUIRED
SHELL_WALL_CORRECTION_SOURCE_BOUND=false
SHELL_WALL_CORRECTION_BASE_COMPATIBILITY_BOUND=false
SHELL_WALL_CORRECTION_APPLICABILITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
```

The next authorized activity is limited to acquiring and reviewing a lawful
Bell-compatible primary source. It must not start by copying a generic
viscosity factor, and it must not alter TASK-166 equations or source roles.

## 8. Case-level and governance state

No case-level shell correction can execute at this head:

```ini
CASE_LEVEL_SHELL_CORRECTION_AUTHORITY_PRESENT=false
CASE_LEVEL_SHELL_BULK_STATE_PRESENT=false
CASE_LEVEL_SHELL_WALL_STATE_PRESENT=false
CASE_LEVEL_SHELL_PROPERTY_SNAPSHOT_PRESENT=false
CASE_LEVEL_SHELL_EXECUTION_AUTHORIZED=false
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

The effective TASK172 entry state remains:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

This resolution does not make the wall-state proposal reviewed, does not
create a material or property instance, and does not authorize numerical
work. Historical R1–R36 registry records remain immutable.

## 9. Change and verification boundary

```ini
ENGINEERING_RULES_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The companion machine record is
[`TASK-172-shell-wall-correction-authority-resolution-r1.json`](evidence/TASK-172-shell-wall-correction-authority-resolution-r1.json).
It records the source/file identities, exact native target, negative lineage,
resolution and effective blocker state without embedding any new equation or
numeric correction parameter.

```ini
LOCAL_VALIDATION=DOCUMENT_AND_EVIDENCE_VALIDATION_REQUIRED
EXACT_FINAL_HEAD_CI=REQUIRED_AFTER_FINAL_PUSH
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_PRIMARY_SOURCE_ACQUISITION_R1_ONLY
STOP=true
```
