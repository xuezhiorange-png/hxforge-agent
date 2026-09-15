# TASK172 R4 — controlled material and active wall-correction remediation

## 1. Receipt and boundary

```ini
TASK_ID=TASK172_V0_7_MATERIAL_AND_ACTIVE_WALL_CORRECTION_R4
PR=277
PREVIOUS_HEAD_SHA=f2c87be7aaec1eaaf59fafbbb8e667257a0eb07d
MODE=CONTROLLED_AUTHORITY_REMEDIATION_ONLY
TASK172_IMPLEMENTATION_STARTED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
NUMERICAL_QUALIFICATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This is a bounded documentation/evidence audit of exactly three physical
authority blockers. It does not reopen the approved R2 water or clean-wall
network packages, and it does not research the three numerical blockers. The
structured evidence is recorded in
[`TASK-172-material-active-wall-review-r4.json`](evidence/TASK-172-material-active-wall-review-r4.json).

Planned repository allowlist before editing:

```ini
PLANNED_CHANGED_FILE_COUNT=3
PLANNED_CHANGED_FILES=docs/tasks/TASK-172-v0.7-material-active-wall-review-r4.md,docs/tasks/evidence/TASK-172-material-active-wall-review-r4.json,docs/tasks/TASK-172-v0.7-authority-registry-r1.json
PRODUCTION_PATH_COUNT=0
DEPENDENCY_FILE_COUNT=0
```

## 2. Inherited reviewed scope

The R3 receipt remains the historical source of the following effective
reviewed authorities; this R4 receipt does not rewrite their payloads:

| Authority | Hash | R4 treatment |
| --- | --- | --- |
| `V07-T172-WATER-PROPERTY-PROFILE-R2` | `8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de` | `REVIEWED_AUTHORITY`, unchanged |
| `V07-T172-WATER-DOMAIN-PROOF-R2` | `0111a6353000159977ae7271a9f397d280ca88e25ece3714b6d2d5c9bd530d53` | `REVIEWED_AUTHORITY`, unchanged |
| `V07-T172-WATER-BACKEND-QUALIFICATION-R2` | `4cccb3122a6ae03badd1bc814523338435977c8324333c804fc1c96b8de10884` | `REVIEWED_AUTHORITY`, unchanged |
| `V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2` | `e493999a1a6f8e83140e62ed71755af877a451bb9525f1e0791cddf174150b29` | `REVIEWED_AUTHORITY`, unchanged |
| `V07-T172-LOCAL-CYLINDRICAL-MAPPING-R2` | `49f902ce096f57381057a6d3631ef4b30355526dae8187112ae04fa703dda63c` | `REVIEWED_AUTHORITY`, unchanged |

The approved water scope is only pure ordinary water / HEOS / CoolProp 8.0.0 /
DEF / stable single-phase liquid / 298.15–300 K / 100000–101325 Pa. It does not
select a wall material, activate a wall correction, or close numerical
qualification.

## 3. Material constant-k audit

### 3.1 Repository authority boundary

The audit checked the TASK020–023 contracts and their production value objects:

* `ShellAndTubeConfigurationRequest` and `ShellAndTubeConfiguration` carry
  configuration identity, construction family, orientation, pass counts, tokens
  and authority bindings, but no tube material grade or conductivity profile.
* TASK021 explicitly keeps material, mechanical adequacy and material selection
  out of its tube-layout snapshot. TASK022 keeps material and wall thickness out
  of its bundle-geometry snapshot. TASK023 is a shell geometry catalog and does
  not bind a tube alloy.
* TASK037 defines typed `TubeWallMaterialAuthority` and
  `TubeWallThermalConductivityAuthority` carriers. Its validator checks identity,
  metadata, positive finite point values and hash fields; it does not establish a
  temperature interval over which a point conductivity is authorized as constant.
* The actual TASK037 release-demo and test constructors use
  `T039-MAT-001` / `FIXTURE-GRADE` and a fixed-release-demo conductivity value at
  300 K. These are fixture/demo authorities and their historical identities are
  preserved. They are not a physical tube-grade selection for TASK172.
* TASK017/TASK013 material governance is a separate, double-pipe preliminary
  material/mass consumer. Its generic test records, including `SA-106-B`, are
  not bound to a TASK020–023 shell-and-tube configuration and cannot be silently
  promoted across task boundaries.

No authoritative TASK172 tube material identity is therefore bound. No grade,
family, source table, or material form may be selected by convention.

```ini
MATERIAL_PROFILE_ID=NONE
MATERIAL_PROFILE_STATUS=BLOCKED
BLOCKER=MATERIAL_IDENTITY_NOT_BOUND
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
MATERIAL_K_CONSTANT_MODEL_AUTHORIZED=false
```

The missing evidence is an authorized tube material identity plus a source-bound
conductivity definition and temperature-domain rule covering the reviewed wall
temperature hull. A point value, `FIXTURE-GRADE`, a common stainless grade, or a
generic TASK017 record is not sufficient. No
`V07-T172-WALL-MATERIAL-CONSTANT-K-R4` authority is issued.

## 4. Tube active wall-correction audit

The actual TASK026 base is the native selector in
`tube_side_thermal/nusselt_selector.py` and `single_phase.py`:

* turbulent `tube_turbulent_gnielinski`, with the inherited TASK026 Re/Pr
  envelope and Petukhov friction relation;
* separate laminar CWT/CHF branches; transition is not admitted;
* no wall-property argument or hidden wall-temperature input.

The TASK007 frozen policy explicitly states that the turbulent Gnielinski
correlation has no viscosity correction implemented and that missing wall
property must block rather than default to a neutral correction. This is an
inherited scope statement, not authority to add a new correction.

The public Gonçalves source already bound in the repository was checked at the
source-defined locations used by TASK170/TASK172. Section 2.2 Eq.75 is its
Gnielinski tube relation and does not provide the requested active wall-property
multiplier. Eq.77 is a separate laminar Sieder–Tate relation in that source's
alternative regime model; it is not a transfer rule for the native TASK026
turbulent selector. Its source-defined regime choices also differ from TASK026.

The Sieder–Tate publisher record is bibliographically identified, but the exact
equation, coefficient/exponent, state definitions, complete domain and lawful
full-text review were not obtained. `SIEDER_TATE_TRANSFER_AUTHORITY=UNAVAILABLE`.
No remembered viscosity exponent, search snippet, library default or secondary
formula is transcribed.

The physical categories remain separate:

| Category | R4 result |
| --- | --- |
| cylindrical conduction / area conversion | inherited reviewed R2 local mapping |
| wall-temperature state | not implemented; numerical/wall closure remains later scope |
| viscosity/property correction to TASK026 HTC | no transferable authority |
| fouling resistance | not activated by the clean-surface profile |
| numerical stabilization | not an engineering correction authority |

```ini
TUBE_WALL_CORRECTION_ID=NONE
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_TYPE=TASK026_ACTIVE_WALL_PROPERTY_CORRECTION_NOT_QUALIFIED
TUBE_WALL_CORRECTION_SOURCE_BOUND=false
TUBE_WALL_CORRECTION_APPLICABILITY_BOUND=false
TUBE_WALL_CORRECTION_MATERIAL_PROFILE_BOUND=false
TUBE_WALL_CORRECTION_GEOMETRY_MAPPING_BOUND=false
TUBE_WALL_CORRECTION_SURFACE_BASIS_BOUND=false
TUBE_WALL_CORRECTION_CROSS_BINDING_PASS=false
TUBE_WALL_CORRECTION_HASH=NONE
```

Required missing evidence is a legally reviewable primary equation explicitly
compatible with the exact TASK026 base, including property ratio, bulk/wall
definitions, heating/cooling semantics, Re/Pr/ratio/geometry/development domain,
and combination rule. No tube correction authority is issued.

## 5. Shell active wall-correction audit

The target shell heat-transfer base is TASK166 Bell–Delaware. Its frozen
`SOURCE_ROLE_BY_ID` separates Bell method origin, Gonçalves primary equations,
Jamil parameter tables and the Saif/Tariq Js supplement. The Bell heat-transfer
relation and its geometry corrections do not supply a new active wall-property
multiplier with a complete compatible domain. The already reviewed Gonçalves
section 2.1 ideal-bank/Bell relations likewise does not close that gap.

TASK034 is not a hidden Bell wall authority. Its R5 contract does contain an
explicit `(mu_b / mu_w)^(7/50)` term from the Bayram–Sevilgen modeled shell-side
pressure-drop correlation. That term is part of TASK034 pressure-drop equation
15, with TASK034's own source, Re envelope and wall-property replay schema. It is
not a heat-transfer correction for TASK166 `h_s`; transplanting it would mix
pressure-drop and heat-transfer methods and violate source/combination binding.
Likewise, TASK033 explicitly identifies its Kharaji shell relation as
`...NO_WALL_CORRECTION...`; it is an alternate Kern shell model, not a Bell
supplement.

The Martin/Gnielinski crossflow source remains a descriptive crossflow
normalization candidate and does not authorize transfer to Bell–Delaware shell
heat transfer. No external correction is copied merely because it uses the words
wall, viscosity or crossflow.

```ini
SHELL_WALL_CORRECTION_ID=NONE
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_TYPE=TASK166_BELL_ACTIVE_WALL_PROPERTY_CORRECTION_NOT_QUALIFIED
SHELL_WALL_CORRECTION_SOURCE_BOUND=false
SHELL_WALL_CORRECTION_APPLICABILITY_BOUND=false
SHELL_WALL_CORRECTION_MATERIAL_PROFILE_BOUND=false
SHELL_WALL_CORRECTION_GEOMETRY_MAPPING_BOUND=false
SHELL_WALL_CORRECTION_SURFACE_BASIS_BOUND=false
SHELL_WALL_CORRECTION_CROSS_BINDING_PASS=false
SHELL_WALL_CORRECTION_HASH=NONE
```

Required missing evidence is a lawful Bell-compatible primary equation or
explicitly transferable supplement with exact property states, surface basis,
geometry/layout, Re/Pr/ratio domain and combination rule. TASK034's pressure
drop correction cannot satisfy that requirement.

## 6. Cross-binding result

| Binding | Result | Reason |
| --- | --- | --- |
| material identity → k authority | BLOCKED | no TASK020–023-bound physical grade |
| k authority → local cylindrical network | BLOCKED | reviewed network is conditional on qualified k |
| material/k → tube active correction | BLOCKED | no material profile and no transferable TASK026 extension |
| material/k → shell active correction | BLOCKED | no material profile and no Bell-compatible extension |
| water profile → clean network | REVIEWED, conditional | R2 scope remains narrow and unchanged |
| TASK034 wall-property replay → TASK166 HTC | FORBIDDEN | separate pressure-drop method and identity |
| TASK033 no-wall-correction model → TASK166 | FORBIDDEN | different shell method family |

There is no approved competing material or correction authority, no silent
fallback, and no unit or surface-basis substitution. The cross-binding gate
therefore fails closed.

## 7. Numerical boundary and final status

The following are deliberately untouched:

```ini
LOCAL_RESIDUAL_AND_METHOD_QUALIFICATION=OPEN
NUMERICAL_ERROR_BUDGET_AND_STOPPING_REVIEW=OPEN
MESH_CONVERGENCE_QUALIFICATION=OPEN
NUMERICAL_PROFILE_STATUS=PARTIALLY_CLOSED
NUMERICAL_TOLERANCES_BOUND=false
MESH_CONVERGENCE_RULE_BOUND=false
```

Effective remaining TASK172 entry blockers:

1. `MATERIAL-CONSTANT-K-TEMPERATURE-DOMAIN`
2. `TUBE-WALL-CORRECTION-AUTHORITY`
3. `SHELL-WALL-CORRECTION-AUTHORITY`
4. `LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION`
5. `NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW`
6. `MESH-CONVERGENCE-QUALIFICATION`

```ini
PHYSICAL_AUTHORITY_PORTION_CLOSED=false
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_IMPLEMENTATION_STARTED=false
NEXT_GATE=BLOCKED_PENDING_TASK172_PHYSICAL_AUTHORITY_REMEDIATION
```

R4 introduces no production implementation, engineering calculation, dependency,
material profile, active correction or numerical preset. The result is BLOCKED
because the required evidence is absent, not because validation or CI failed.
Ready and Merge remain unauthorized.
