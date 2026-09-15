# TASK172 R1 — Bell-compatible shell wall-correction primary-source acquisition

## 1. Receipt and non-mutation boundary

This receipt records a targeted source acquisition for the remaining
`SHELL-WALL-CORRECTION-AUTHORITY` blocker. It audits the Bell/Delaware
lineage identified by TASK-166 and does not alter TASK-166, its equations, its
source identities, or its correction-factor semantics.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_PRIMARY_SOURCE_ACQUISITION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=37da2702c248192d75c1a038df2d8e48eefccabd
MODE=TARGETED_BELL_COMPATIBLE_PRIMARY_SOURCE_ACQUISITION_ONLY
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

The source body, source metadata, variant comparison, and transferability
disposition are append-only evidence. A public scan being readable is not a
rights clearance, and a source equation being identified is not permission to
transfer it to the native TASK-166 method.

## 2. Native TASK-166 comparator

The comparator remains the exact native Bell path already recorded at the
previous resolution:

```ini
NATIVE_SHELL_TASK_ID=TASK-166
NATIVE_SOURCE_DEFINITION_ID=TASK165_R3_BELL_DELAWARE_SOURCE_AUTHORITY_V1
NATIVE_METHOD=BELL_DELAWARE
NATIVE_IDEAL_HTC_FORM=ji*cp*G*Pr^(-2/3)
NATIVE_CORRECTED_HTC_FORM=ideal_h*Jc*Jl*Jb*Js*Jr
NATIVE_CORRECTION_FACTORS=Jc;Jl;Jb;Js;Jr
NATIVE_RE_EVALUATOR_DOMAIN=0<Re_s<=100000
GONCALVES_ACTIVE_WALL_PROPERTY_TERM_PRESENT=false
```

The selected Gonçalves implementation source is retained as the exact
comparator:

```ini
GONCALVES_SOURCE_ID=SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE
GONCALVES_DOI=10.1002/aic.16602
GONCALVES_BODY_SHA256=fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54
GONCALVES_EXACT_RELATION=hi=ji*Cp_s*G_s*Pr_s^(-2/3);hs=hi*Jc*Jl*Jb*Jr
GONCALVES_WALL_VISCOSITY_INPUT=false
GONCALVES_WALL_TEMPERATURE_INPUT=false
GONCALVES_BULK_WALL_PROPERTY_RATIO=false
```

The reviewed `Js` supplement remains a baffle-spacing correction only. No
native `Jc`, `Jl`, `Jb`, `Js`, or `Jr` input is a shell wall-viscosity or
wall-temperature state. The prior TASK-166 resolution therefore remains
unchanged.

## 3. Acquisition result

The primary acquisition found a complete public scan of Bell's 1960 article.
It establishes that Bell's 1960 correlation variant includes a non-isothermal
viscosity factor in its ideal-tube-bank `j` definition/reconstruction. It does
not establish that the factor can be inserted into the current Gonçalves
variant after `Jc`, `Jl`, `Jb`, `Js`, and `Jr`, nor does it provide every field
required by the TASK172 transfer contract.

```ini
ACQUISITION_OUTCOME=BELL_VARIANT_MISMATCH_REQUIRES_TRANSFER_ADJUDICATION
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
PRIMARY_TASK166_TRANSFER_AUTHORITY_BOUND=false
NEW_SHELL_CORRECTION_AUTHORITY_CANDIDATE_CREATED=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_BELL_VARIANT_TRANSFER_ADJUDICATION_R1_ONLY
```

This is Outcome B from the authorized acquisition choices: the source
evidence is sufficient to prove a material variant difference, but not
sufficient to authorize direct transfer. No `V07-T172-SHELL-WALL-CORRECTION-R1`
production candidate is created by this receipt.

## 4. Bell 1960 — acquired primary body

| Field | Evidence |
| --- | --- |
| Source target | `BELL-1960-DELAWARE-DESIGN` |
| Author | Kenneth J. Bell |
| Title | *Exchanger Design Based on the Delaware Research Program* |
| Publication | *Petro/Chem Engineer*, vol. 32, no. 11, October 1960 |
| Printed pages | C-26–C-36 and C-40a–C-40c |
| PDF pages | 14; the scan contains the complete printed-page sequence above |
| Public access | [public scan](https://www.ing.unp.edu.ar/asignaturas/operaciones_fisicas_2/Versiones%20PDF/Exchanger%20design%20based%20on%20the%20Delaware%20research%20program-%20Kenneth%20Bell.pdf) |
| Acquired bytes | SHA-256 `4657ebfb78bda433528b7f1197fff32e299361d39379bb6839e871f43bc2ed11` |
| Retrieval metadata | `content-type=application/pdf`, `content-length=3161457`, `etag="303d71-5dc62efc18597"`, `last-modified=Mon, 11 Apr 2022 15:52:50 GMT` |
| Rights | Publicly accessible scan; copyright/reproduction rights not verified; not vendored |
| Acquisition status | `BODY_ACQUIRED=true`, `BODY_COMPLETE=true`, `VERIFIED_SOURCE` for variant observation only |

### 4.1 Exact source observations

The following observations are page-bound to the acquired scan and are kept
separate from any proposed TASK166 transfer:

| Printed location | Observation | Authority consequence |
| --- | --- | --- |
| C-28 | The discussion of non-isothermal effects says the factor `(μ/μ_w)^0.14` is satisfactory for the studied `f` and `j` behavior; the text also mentions a Reynolds-dependent laminar friction refinement by Hull. | Establishes a wall-property factor in this source variant, but not a complete TASK166 transfer domain. |
| C-30 | The crossflow friction-factor figure and text use `(μ/μ_w)^0.14` for non-isothermal friction. | Friction evidence is not heat-transfer authority for TASK166. |
| C-32–C-33 | The ideal/non-leakage tube-bank `j` correlations are plotted using the dimensionless normalization containing `(μ_w/μ)^0.14`. | The factor is part of the source's `j` normalization; it is not a free post-`J` multiplier. |
| C-36 | The design procedure selects ideal-tube-bank `j` from a Reynolds correlation and then applies exchanger geometry/leakage/bypass steps. | The source ordering differs from the native Gonçalves identity and must not be inferred from names alone. |
| C-40a | The example reconstructs the heat-transfer coefficient from `j`, explicitly includes `(μ_w/μ)^0.14` in the `j` expression, and uses the inverse factor when reconstructing `h`. | Confirms the source's coefficient-side orientation is `(μ/μ_w)^0.14`, while preserving the source `j`-definition orientation. |
| C-40c | Nomenclature defines `μ` as absolute viscosity and `μ_w` as absolute viscosity at the heat-transfer surface; the ideal-bank `j` definition contains `(μ_w/μ)^0.14`. | Provides a wall-surface viscosity symbol, but not a complete TASK172 bulk-state location, wall-temperature algorithm, or Bell-variant transfer rule. |

The two orientations are not silently normalized away:

```ini
BELL_1960_DIMENSIONLESS_J_RATIO=(mu_w/mu)^0.14
BELL_1960_HEAT_COEFFICIENT_RECONSTRUCTION_RATIO=(mu/mu_w)^0.14
BELL_1960_VISCOSITY_RATIO_ORIENTATION=SOURCE_J_DEFINITION_MU_W_OVER_MU;COEFFICIENT_RECONSTRUCTION_MU_OVER_MU_W
BELL_1960_EXPONENT=0.14
BELL_1960_MU_DEFINITION=absolute_viscosity_mu;source does not bind a TASK172 bulk-state location
BELL_1960_MU_W_DEFINITION=absolute_viscosity_at_heat_transfer_surface
BELL_1960_WALL_TEMPERATURE_DEFINITION=not separately defined;mu_w is evaluated at heat-transfer surface
BELL_1960_IDEAL_HTC_DEFINITION=ideal-tube-bank h reconstructed from j and the source viscosity normalization
BELL_1960_COMBINATION_POSITION=inside ideal/non-leakage tube-bank j normalization;before source geometry/leakage/bypass steps
```

### 4.2 Bell 1960 field-completeness audit

The source equation and exponent are bound as observations. The following
required transfer fields are deliberately not promoted because the body does
not bind them in a form compatible with the current TASK166 contract:

| Required field | Bell 1960 disposition | Reason it does not authorize direct transfer |
| --- | --- | --- |
| Exact Bell base identity | Partial | Ideal banks and Model 9/non-leakage paths are described, but the exact native Gonçalves base identity is not the source's canonical identity. |
| Correction equation | Source-bound observation | `(μ/μ_w)^0.14` is present on the coefficient reconstruction path; a TASK166-compatible correction object is not created. |
| Ratio orientation | Bound as source notation | `j` uses `(μ_w/μ)^0.14`; coefficient reconstruction uses the inverse. |
| Bulk state | Partial/unbound | `μ` is named as absolute viscosity, but no exact TASK172 bulk-state location and evaluation rule is bound. |
| Wall state | Partial/unbound | `μ_w` is at the heat-transfer surface, but no complete wall-temperature state contract is supplied. |
| `Re` domain | Not bound for transfer | The article discusses the studied range and figures, but does not provide a complete strict wall-correction transfer interval for the current target. |
| `Pr` domain | Not bound | No complete strict Prandtl domain for the wall factor is supplied. |
| Fluid scope | Not bound | The article reports particular Delaware data/fluids and an example, not a complete production fluid-family scope. |
| Heating/cooling semantics | Not bound | Non-isothermal behavior is discussed, but no complete direction-specific state/branch contract is bound. |
| Geometry/layout | Partial only | Tube-bank layout/model context exists, but no exact transfer mapping to the selected TASK166 geometry identity is bound. |
| Bell combination rule | Not bound for TASK166 | The source factor sits in its own ideal-bank `j` normalization; no rule authorizes adding it to `ideal_h*Jc*Jl*Jb*Js*Jr`. |
| Source rights | Not cleared | The scan is accessible, but reproduction/redistribution permission is not verified. |

Accordingly:

```ini
BELL_1960_CORRECTION_EQUATION_BOUND=true
BELL_1960_PROPERTY_RATIO_BOUND=true
BELL_1960_EXPONENT_BOUND=true
BELL_1960_BULK_STATE_BOUND=false
BELL_1960_WALL_STATE_BOUND=false
BELL_1960_RE_DOMAIN_BOUND=false
BELL_1960_PR_DOMAIN_BOUND=false
BELL_1960_FLUID_SCOPE_BOUND=false
BELL_1960_HEATING_COOLING_SCOPE_BOUND=false
BELL_1960_GEOMETRY_LAYOUT_DOMAIN_BOUND=false
BELL_1960_COMBINATION_RULE_BOUND=false
BELL_1960_TRANSFERABLE_TO_TASK166=false
```

## 5. Bell 1963 Bulletin No. 5

The bibliographic primary target is confirmed, but a complete lawful body was
not acquired in this gate:

```ini
BELL_1963_SOURCE_TARGET_ID=BELL-1963-DELAWARE-FINAL-REPORT
BELL_1963_AUTHOR=Kenneth J. Bell
BELL_1963_TITLE=Final Report of the Cooperative Research Program on Shell and Tube Heat Exchangers
BELL_1963_ISSUER=University of Delaware Engineering Experimental Station
BELL_1963_REPORT=Bulletin No. 5
BELL_1963_YEAR=1963
BELL_1963_BODY_ACQUIRED=false
BELL_1963_BODY_COMPLETE=false
BELL_1963_BYTES_SHA256=NONE
BELL_1963_STATUS=BIBLIOGRAPHIC_PRIMARY_SOURCE_TARGET_ONLY
BELL_1963_VISCOSITY_CORRECTION_PRESENT=UNDETERMINED_BODY_NOT_ACQUIRED
```

The [WorldCat record](https://search.worldcat.org/title/final-report-of-the-cooperative-research-program-on-shell-and-tube-heat-exchangers/oclc/16107403)
is used only for bibliographic identity. Search results, citation lists, and
copyrighted upload listings are not used to reconstruct an equation.

## 6. Bergelin et al. 1958 Bulletin No. 4

Bulletin No. 4 is the relevant Delaware ideal-bank/viscous-flow lineage
candidate, but its complete body and rights-cleared equation pages were not
acquired:

```ini
BERGELIN_1958_SOURCE_TARGET_ID=BERGELIN-1958-DELAWARE-BULLETIN-4
BERGELIN_1958_AUTHORS=O.P.Bergelin;M.D.Leighton;W.L.Lafferty_Jr;R.L.Pigford
BERGELIN_1958_TITLE=Heat Transfer and Pressure Drop During Viscous and Turbulent Flow Across Baffled and Unbaffled Tube Banks
BERGELIN_1958_ISSUER=University of Delaware Engineering Experimental Station
BERGELIN_1958_REPORT=Bulletin No. 4
BERGELIN_1958_YEAR=1958
BERGELIN_1958_BODY_ACQUIRED=false
BERGELIN_1958_BODY_COMPLETE=false
BERGELIN_1958_BYTES_SHA256=NONE
BERGELIN_1958_STATUS=BIBLIOGRAPHIC_PRIMARY_SOURCE_TARGET_ONLY
BERGELIN_1958_VISCOSITY_CORRECTION_PRESENT=UNDETERMINED_BODY_NOT_ACQUIRED
BERGELIN_1958_CORRECTION_PHYSICAL_QUANTITY=UNDETERMINED
BERGELIN_1958_TRANSFER_TO_BELL_IDEAL_BANK_POSSIBLE=NOT_ASSESSED_WITHOUT_BODY
```

The bibliography entry exposed by a publisher reference page is discovery
evidence only; it is not used as the Bulletin's equation body. No
`(μ/μ_w)^n` observed in a secondary source is promoted into this registry.

## 7. Taborek / HEDH lineage

The exact HEDH/Taborek chapter was not acquired with verified rights and
complete identity. A publicly readable *Engineering Data Book III* repost was
reviewed only as a secondary lineage cross-check. Its OCR identifies a
`J_μ=(μ/μ_wall)^m` wall-viscosity factor and states `m=0.14` for liquid
heating/cooling, with mean bulk properties and a preliminary wall-temperature
calculation. That repost is not the HEDH chapter, its rights are not verified,
and it cannot authorize TASK166 transfer.

```ini
TABOREK_SOURCE_TARGET_ID=TABOREK-HEDH-SHELL-TUBE-SINGLE-PHASE
TABOREK_AUTHOR=J.Taborek
TABOREK_WORK=Heat Exchanger Design Handbook
TABOREK_SECTION=3.3 shell-and-tube heat exchangers / single-phase flow
TABOREK_BODY_ACQUIRED=false
TABOREK_BODY_COMPLETE=false
TABOREK_BYTES_SHA256=NONE
TABOREK_STATUS=BIBLIOGRAPHIC_LINEAGE_ONLY
TABOREK_VISCOSITY_CORRECTION_PRESENT=UNVERIFIED_EXACT_BODY_NOT_ACQUIRED
TABOREK_TRANSFER_TO_TASK166=false
```

The reposted cross-check is retained only as non-authoritative discovery
evidence: [Engineering Data Book III, chapter 3 PDF](https://www.researchgate.net/file.PostFileLoader.html?assetKey=AS%3A406014038953986%401473812699038&id=57d898db404854a1c532e703).
Its §3.4.6 and §3.4.7 text is not copied into the TASK166 source authority.

## 8. Bell-variant difference matrix

| Dimension | TASK166 / Gonçalves | Bell 1960 | Bell 1963 | Bergelin 1958 | Taborek / HEDH |
| --- | --- | --- | --- | --- | --- |
| Ideal HTC base | `h_i=j_i C_p G Pr^-2/3` in the selected 2019 implementation | Ideal/non-leakage tube-bank `j` with wall-viscosity normalization; source uses model-specific paths | Not determined; body not acquired | Not determined; body not acquired | Not determined from exact HEDH body; secondary repost indicates an ideal-bank `α_I` lineage |
| Viscosity correction | No active wall-property term | Present in source `j` definition/reconstruction | Not determined | Not determined | Only secondary cross-check indicates `J_μ`; exact target body unverified |
| Ratio orientation | None | `j`: `(μ_w/μ)^0.14`; coefficient reconstruction: `(μ/μ_w)^0.14` | Not determined | Not determined | Secondary cross-check: `μ/μ_wall` in `J_μ`, not authority |
| Exponent | None | `0.14` for the stated source non-isothermal relation; Hull laminar friction refinement differs | Not determined | Not determined | Secondary cross-check says `m=0.14`, not authority |
| Wall-state definition | No wall state | `μ_w` at heat-transfer surface; no complete TASK172 wall-state mapping | Not determined | Not determined | Secondary cross-check says `T_wall` is required, but exact HEDH body not acquired |
| Fluid scope | Native source scope and repository restrictions | Source test/example context; no complete production fluid-family scope | Not determined | Not determined | Exact scope not determined |
| Re domain | Effective native evaluator `0<Re_s<=100000` | Source figures/data discuss ranges, but no complete transfer interval bound | Not determined | Not determined | Exact scope not determined |
| Pr domain | Native implementation input | Not bound for wall factor | Not determined | Not determined | Exact scope not determined |
| Geometry | TASK166 selected Bell geometry identity | Ideal banks/Model 9 and source-specific baffled paths | Not determined | Baffled/unbaffled tube-bank title only | Exact HEDH body not acquired |
| Combination position | `ideal_h*Jc*Jl*Jb*Js*Jr` | Inside source ideal-bank `j` normalization, before source geometry steps | Not determined | Not determined | Exact combination not determined |
| Source body complete | Yes for selected 2019 implementation source | Yes for acquired 14-page scan; rights not cleared | No | No | No |

The matrix proves a source-variant difference, not a valid transfer. “Bell” is
not a sufficient identity key for equation compatibility.

## 9. Critical transfer classification

The acquired Bell 1960 source supports the following classification:

```ini
CORRECTION_IS_PART_OF_ORIGINAL_IDEAL_BANK_BASE=true
CORRECTION_IS_OPTIONAL_ENGINEERING_EXTENSION=false
CORRECTION_IS_LATER_RECOMMENDED_PRACTICE=SOURCE_TEXT_USES_RECOMMENDED_SATISFACTORY_WORDING_BUT_NO_LATER_LINEAGE_AUTHORIZED
CORRECTION_IS_SOURCE_VARIANT_SPECIFIC=true
```

The factor is part of Bell 1960's source-specific dimensionless `j`
normalization/reconstruction, not a neutral multiplier that can be appended to
the current TASK166 result. Whether Bell 1960's ideal-bank definition can be
transferred to the selected Gonçalves base is a separate adjudication and is
not decided by this acquisition.

## 10. Wall/bulk state mapping

The source-level symbols are retained without an artificial TASK172 mapping:

```ini
SOURCE_BULK_VISCOSITY_STATE=BELL_1960_MU;absolute_viscosity_mu;exact_bulk_evaluation_location_not_bound
SOURCE_WALL_VISCOSITY_STATE=BELL_1960_MU_W;absolute_viscosity_at_heat_transfer_surface
SOURCE_WALL_TEMPERATURE_LOCATION=HEAT_TRANSFER_SURFACE_SYMBOLIC_ONLY
TASK172_BULK_STATE=SHELL_FLUID_BULK_STATE
TASK172_WALL_STATE=SHELL_FLUID_WALL_INTERFACE
TASK172_STATE_MAPPING_ESTABLISHED=false
```

No tube-metal outer temperature, shell bulk temperature, arithmetic wall
average, or TASK034 pressure-drop wall state is treated as equivalent to the
source wall state. A future transfer adjudication must independently resolve
the state mapping and its wall-temperature producer.

## 11. Completeness and non-transfer ledger

The requested transfer threshold is not met:

```ini
EXACT_BELL_BASE_IDENTITY_BOUND=false
CORRECTION_EQUATION_OBSERVED=true
CORRECTION_COEFFICIENT_EXPONENT_OBSERVED=true
SOURCE_BULK_STATE_COMPLETE=false
SOURCE_WALL_STATE_COMPLETE=false
HEATING_COOLING_SCOPE_COMPLETE=false
RE_DOMAIN_COMPLETE=false
PR_DOMAIN_COMPLETE=false
PROPERTY_RATIO_DOMAIN_COMPLETE=false
GEOMETRY_LAYOUT_DOMAIN_COMPLETE=false
COMBINATION_WITH_TASK166_COMPLETE=false
SOURCE_REVISION_LOCATION_BOUND=true
SOURCE_RIGHTS_CLEARED=false
TRANSFERABLE_AUTHORITY_CANDIDATE_COMPLETE=false
```

The following transfers remain forbidden:

```ini
TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TASK034_TRANSFER_REASON=TASK034_Bayram-Sevilgen_(mu_b/mu_w)^(7/50)_is_shell_pressure-drop_phi_s_authority
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
SECONDARY_TABOREK_REPOST_TRANSFER_TO_TASK166=false
```

The Bell 1960 factor's numeric equality to any factor in another task is not
treated as identity or transfer evidence.

## 12. Effective blocker and governance state

```ini
ACQUISITION_OUTCOME=BELL_VARIANT_MISMATCH_REQUIRES_TRANSFER_ADJUDICATION
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No authority lifecycle is promoted by this receipt. The acquired Bell 1960
body is a `VERIFIED_SOURCE` for a source-variant observation; it is not a
`REVIEWED_AUTHORITY` for a TASK166-compatible correction. Bell 1963, Bergelin
1958, and Taborek/HEDH remain bibliographic or secondary discovery targets.

```ini
TASK166_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
NEW_AUTHORITY_SELF_APPROVAL=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_BELL_VARIANT_TRANSFER_ADJUDICATION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The companion JSON record is
[`TASK-172-shell-wall-correction-primary-source-acquisition-r1.json`](evidence/TASK-172-shell-wall-correction-primary-source-acquisition-r1.json).
It records source fingerprints, page-bound observations, field completeness,
variant differences, negative lineage, and the unchanged four-blocker state.
