# TASK172 R2 — targeted laminar variable-property primary-source acquisition

## 1. Scope and inherited boundary

This is a documentation-only acquisition for the unresolved
`TUBE-WALL-CORRECTION-AUTHORITY` blocker on Draft PR277.  It follows the R1
acquisition of the exact native TASK026 laminar CWT and CHF source semantics.
It does not modify TASK026, its selector, constants, domains, the accepted
turbulent C3 correction, or any production module.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_VARIABLE_PROPERTY_PRIMARY_SOURCE_ACQUISITION_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=7cf4dd6e6a2c92c210a7a3563fa924f00a84986e
PREVIOUS_HEAD_SHA=7cf4dd6e6a2c92c210a7a3563fa924f00a84986e
MODE=TARGETED_LAMINAR_VARIABLE_PROPERTY_PRIMARY_SOURCE_ACQUISITION_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_WITH_BLOCKER_RETAINED
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TURBULENT_C3_AUTHORITY_CHANGED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The acquisition asks only whether a source-qualified variable-property
wall-state disposition exists for the exact native branches
`tube_laminar_cwt@1.0.0` and `tube_laminar_chf@1.0.0`.  It does not reopen the
R1 constant-property values `Nu_D = 3.66` and `Nu_D = 4.36`.

The inherited R1 state remains:

```ini
CWT_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CHF_SOURCE_FINDING=CONSTANT_PROPERTY_MODEL_ONLY
CWT_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CHF_WALL_PROPERTY_CORRECTION_RULE_BOUND=false
CWT_OMISSION_SEMANTICS_BOUND=false
CHF_OMISSION_SEMANTICS_BOUND=false
CWT_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED
CHF_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

## 2. Acquisition decision

The acquisition obtained the complete public body of NACA TN 2410 and
reviewed it page by page.  The report is valuable primary technical-source
lineage for fully developed laminar variable-property analysis, but its
declared analytical subjects are gases and liquid metals.  It does not
establish transfer to the reviewed pure-water profile, nor does it provide a
branch-specific TASK026 combination rule for a water wall-temperature state.

The original Yang 1962 article was then pursued through the official ASME
record and its publisher PDF link.  Crossref confirms the article identity
and abstract, but the publisher PDF returned HTTP 403 access control in this
environment.  OpenAlex records the work as closed access with no repository
full text.  No lawful complete article body was acquired, so no Yang equation
or domain is transcribed.

Consequently neither branch receives an active-correction candidate or an
explicit-omission candidate in this R2.  The correct disposition is source
evidence still insufficient, while runtime variable-property use remains
fail-closed and unauthorized.

```ini
NACA_TN_2410_BODY_ACQUIRED=true
DEISSLER_TO_TASK172_WATER_TRANSFER_ESTABLISHED=false
YANG_SOURCE_BODY_ACQUIRED=false
YANG_SOURCE_STATUS=BIBLIOGRAPHIC_DISCOVERY_ONLY
NASA_SECONDARY_SUMMARY_ROLE=SOURCE_DISCOVERY_AND_CROSS_CHECK_ONLY
CWT_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
CHF_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
```

## 3. Primary source 1 — NACA TN 2410

| Field | Bound value |
| --- | --- |
| Source target | `NACA-TN-2410` |
| Record | NASA NTRS `19930088965` |
| Report number | `NACA-TN-2410` |
| Title | *Analytical Investigation of Fully Developed Laminar Flow in Tubes with Heat Transfer with Fluid Properties Variable Along the Radius* |
| Author | Robert G. Deissler |
| Issuer | National Advisory Committee for Aeronautics, Lewis Flight Propulsion Laboratory |
| Year | 1951; report date July 1951 |
| Source class | `US_GOVERNMENT_PRIMARY_TECHNICAL_REPORT` |
| NTRS record | [NASA NTRS record 19930088965](https://ntrs.nasa.gov/citations/19930088965) |
| PDF | [NTRS PDF](https://ntrs.nasa.gov/api/citations/19930088965/downloads/19930088965.pdf) |
| Full-text endpoint | [NTRS extracted text](https://ntrs.nasa.gov/api/citations/19930088965/downloads/19930088965.txt) |
| PDF bytes | SHA-256 `7bea2670ad3fb974dcbc9b761f3cbfdede7c79768be8e6909a78c4223681ef9f` |
| Extracted text bytes | SHA-256 `96f20fd5946a6783fa0410b6dd000b4e9ee0dd94d28339e01f07a9a59a02212d` |
| PDF page count | 29 |
| Body review | Rendered inspection of all 29 PDF pages; text endpoint used as a location cross-check |
| Retrieval date | `2026-09-15` |
| Rights | `GOV_PUBLIC_USE_PERMITTED_PER_NTRS_METADATA`; not vendored |
| Source lifecycle | `VERIFIED_SOURCE_NOT_TASK172_TRANSFER_AUTHORITY` |

### 3.1 Extracted source semantics

The report summary and introduction (report pp. 1–2; PDF pp. 2–3) explicitly
state that the analysis concerns fully developed laminar flow of gases and
liquid metals with properties variable along the radius, and that the
relations apply to heating and cooling.  That fluid-family statement is a
limitation, not a license to transfer the relation to ordinary water.

For gases, the assumptions and derivation (report pp. 4–10; PDF pp. 5–11)
state that the flow and temperature fields are fully developed, frictional
heating and axial conduction are neglected, viscosity, conductivity and
density vary with temperature, and specific heat and Prandtl number are held
constant.  The source uses a power-law temperature model for the viscosity and
links the conductivity variation to it under its constant-Prandtl assumption.

For liquid metals (report pp. 10–12; PDF pp. 11–13), the report changes the
assumption: only viscosity is treated as temperature-varying because density
and thermal conductivity variations are considered small for the analyzed
liquid metals.  The source therefore does not supply the CoolProp water
`rho/cp/h/mu/k` state semantics required by TASK172.

The source defines radial wall, bulk and intermediate temperatures and derives
relations for velocity/temperature distributions, Nusselt numbers and
friction parameters (report pp. 6–17; PDF pp. 7–18, including Eqs. 9–43).
The uniform-property special case gives its own classical results (report
pp. 13–14; PDF pp. 14–15).  The report does not present a TASK026-specific
branch package that binds a pure-water bulk state, a TASK172 wall state, a
source-qualified property ratio, and a combination rule for either
`tube_laminar_cwt@1.0.0` or `tube_laminar_chf@1.0.0`.

```ini
DEISSLER_FLOW_REGIME=FULLY_DEVELOPED_LAMINAR
DEISSLER_GEOMETRY=CIRCULAR_TUBE
DEISSLER_FLUID_FAMILY=GASES_AND_LIQUID_METALS
DEISSLER_HEATING_COOLING_SCOPE=BOTH_HEATING_AND_COOLING
DEISSLER_THERMAL_BOUNDARY=FULLY_DEVELOPED_RADIAL_WALL_TO_BULK_TEMPERATURE_FORMULATION;EXACT_TASK026_CWT_CHF_PAIRING_NOT_STATED
DEISSLER_PROPERTY_VARIATION_MODEL=GAS_MU_K_RHO_VARIABLE_WITH_TEMPERATURE;LIQUID_METAL_MU_ONLY
DEISSLER_PROPERTY_STATE_DEFINITIONS=WALL_TEMPERATURE_T0;BULK_TEMPERATURE_TB;INTERMEDIATE_FLUID_TEMPERATURE_TX
DEISSLER_WALL_TO_BULK_VARIABLE=BOUND_IN_SOURCE_AS_T0_OVER_TB
DEISSLER_NUSSELT_RELATION=SOURCE_RELATIONS_NU_O_NU_B_NU_X;NO_TASK026_VARIABLE_PROPERTY_COMBINATION_RULE
DEISSLER_REFERENCE_PROPERTY_TEMPERATURE_RULE=SOURCE_SPECIFIC_EVALUATION_TEMPERATURES;NOT_TRANSFERRED_TO_TASK172_WATER
DEISSLER_CWT_TRANSFERABILITY=false
DEISSLER_CHF_TRANSFERABILITY=false
DEISSLER_TO_TASK172_WATER_TRANSFER_ESTABLISHED=false
```

### 3.2 Transfer audit

| Required transfer question | Finding | Status |
| --- | --- | --- |
| Exact native CWT branch | The source is not a pure-water TASK026 CWT transfer package | `NOT_BOUND` |
| Exact native CHF branch | The source is not a pure-water TASK026 CHF transfer package | `NOT_BOUND` |
| Bulk/wall property pair | Radial source variables exist, but not the reviewed TASK172 water property profile | `NOT_BOUND` |
| Water fluid scope | Source declares gases and liquid metals; water transfer is not established | `NOT_TRANSFERABLE` |
| Heating/cooling semantics | General source statement exists, but no exact native branch combination rule | `NOT_BOUND_FOR_TASK172` |
| Correction equation | No branch-specific source-qualified TASK172 correction equation selected | `NOT_BOUND` |
| Omission rule | Absence of a correction statement is not explicit omission authority | `NOT_BOUND` |
| Candidate lifecycle | No branch authority candidate created | `NOT_CREATED` |

NACA TN 2410 is therefore recorded as a complete, reviewable source lineage
with a bounded limitation.  It is not promoted to either laminar branch
authority and is not used to infer a correction exponent or to authorize
omission.

## 4. Primary source 2 — Yang 1962

| Field | Bound value |
| --- | --- |
| Source target | `YANG-1962-VARIABLE-VISCOSITY` |
| Title | *Laminar Forced Convection of Liquids in Tubes With Variable Viscosity* |
| Author | Kwang-Tzu Yang |
| Journal | *Journal of Heat Transfer*, vol. 84, no. 4, pp. 353–361 |
| Publication date | 1962-11-01 |
| DOI | [10.1115/1.3684396](https://doi.org/10.1115/1.3684396) |
| Source class | `PEER_REVIEWED_PRIMARY_JOURNAL_ARTICLE` |
| Official publisher record | [ASME Journal of Heat Transfer record](https://asmedigitalcollection.asme.org/heattransfer/article/84/4/353/430308/Laminar-Forced-Convection-of-Liquids-in-Tubes-With) |
| Publisher PDF link attempted | `https://asmedigitalcollection.asme.org/heattransfer/article-pdf/84/4/353/5717440/353_1.pdf` |
| Metadata source | Crossref work record; response bytes SHA-256 `5efd29f0734e9dedf10f3928c2d417ec78a35756ab5d12dfdd744f3eb7ea0fe1` |
| Body bytes | `NONE` |
| Body acquisition status | `OFFICIAL_PUBLISHER_PDF_ACCESS_CONTROLLED_HTTP_403` |
| Open-access cross-check | OpenAlex reports `is_oa=false`, `oa_status=closed`, and no repository full text; cross-check only |
| Rights | No complete rights-cleared body acquired; no equation transcription |
| Source lifecycle | `BIBLIOGRAPHIC_DISCOVERY_ONLY` |

The official metadata/abstract establishes that Yang studied analytical
solutions for liquids in circular tubes with temperature-dependent viscosity,
including a step change in tube-wall temperature and a step change in wall
heat flux.  That abstract is useful for identifying the two source lineages,
but it does not provide the equation body, coefficient/domain tables, state
definitions, or combination rules needed for a TASK172 authority record.

```ini
YANG_CWT_BOUNDARY=ABSTRACT_ONLY_STEP_CHANGE_TUBE_WALL_TEMPERATURE
YANG_CHF_BOUNDARY=ABSTRACT_ONLY_STEP_CHANGE_WALL_HEAT_FLUX
YANG_VARIABLE_PROPERTY_TYPE=ABSTRACT_ONLY_TEMPERATURE_DEPENDENT_VISCOSITY
YANG_VISCOSITY_TEMPERATURE_MODEL=UNBOUND_ABSTRACT_ONLY
YANG_CWT_CORRECTION_EQUATION=UNBOUND_BODY_NOT_ACQUIRED
YANG_CWT_CORRECTION_DOMAIN=UNBOUND_BODY_NOT_ACQUIRED
YANG_CWT_BULK_STATE=UNBOUND_BODY_NOT_ACQUIRED
YANG_CWT_WALL_STATE=UNBOUND_BODY_NOT_ACQUIRED
YANG_CWT_HEATING_COOLING_SCOPE=UNBOUND_BODY_NOT_ACQUIRED
YANG_CHF_CORRECTION_EQUATION=UNBOUND_BODY_NOT_ACQUIRED
YANG_CHF_CORRECTION_DOMAIN=UNBOUND_BODY_NOT_ACQUIRED
YANG_CHF_BULK_STATE=UNBOUND_BODY_NOT_ACQUIRED
YANG_CHF_WALL_STATE=UNBOUND_BODY_NOT_ACQUIRED
YANG_CHF_HEATING_COOLING_SCOPE=UNBOUND_BODY_NOT_ACQUIRED
YANG_TO_TASK172_WATER_TRANSFER_ESTABLISHED=false
```

The publisher access restriction was not bypassed.  No search result, abstract,
secondary summary, or remembered Sieder–Tate factor is treated as Yang source
body authority.

## 5. Branch-specific disposition

The CWT and CHF decisions remain separate.  NACA's general variable-property
lineage does not establish water transfer, and Yang's abstract cannot supply
the missing equation/domain body.  Therefore neither branch is classified as
an active-correction candidate or as an explicit-omission candidate.

| Field | CWT | CHF |
| --- | --- | --- |
| Native correlation | `tube_laminar_cwt@1.0.0` | `tube_laminar_chf@1.0.0` |
| Boundary condition | `CONSTANT_WALL_TEMPERATURE` | `CONSTANT_HEAT_FLUX` |
| NACA body relevance | Variable-property lineage, non-water fluid scope | Variable-property lineage, non-water fluid scope |
| Yang body relevance | Abstract names wall-temperature case; body unavailable | Abstract names wall-heat-flux case; body unavailable |
| Variable-property use authorized | `false` | `false` |
| Active correction rule | `UNRESOLVED_BY_REVIEWED_AUTHORITY` | `UNRESOLVED_BY_REVIEWED_AUTHORITY` |
| Explicit omission rule | `UNRESOLVED_BY_REVIEWED_AUTHORITY` | `UNRESOLVED_BY_REVIEWED_AUTHORITY` |
| Exact branch disposition | `SOURCE_EVIDENCE_STILL_INSUFFICIENT` | `SOURCE_EVIDENCE_STILL_INSUFFICIENT` |
| Authority type | `NONE` | `NONE` |
| Candidate status | `NOT_CREATED` | `NOT_CREATED` |

In particular, the current result does not prove that variable-property use is
physically impossible for water.  It proves only that the acquired evidence
does not authorize it.  Production admission consequently remains
fail-closed without asserting either a correction or an omission.

```ini
CWT_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
CWT_AUTHORITY_TYPE=NONE
CWT_CORRECTION_EQUATION_BOUND=false
CWT_PROPERTY_RATIO_BOUND=false
CWT_BULK_STATE_BOUND=false
CWT_WALL_STATE_BOUND=false
CWT_HEATING_COOLING_SCOPE_BOUND=false
CWT_DOMAIN_BOUND=false
CWT_COMBINATION_RULE_BOUND=false
CWT_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED

CHF_BRANCH_DISPOSITION=SOURCE_EVIDENCE_STILL_INSUFFICIENT
CHF_AUTHORITY_TYPE=NONE
CHF_CORRECTION_EQUATION_BOUND=false
CHF_PROPERTY_RATIO_BOUND=false
CHF_BULK_STATE_BOUND=false
CHF_WALL_STATE_BOUND=false
CHF_HEATING_COOLING_SCOPE_BOUND=false
CHF_DOMAIN_BOUND=false
CHF_COMBINATION_RULE_BOUND=false
CHF_AUTHORITY_CANDIDATE_STATUS=NOT_CREATED
```

## 6. Evidence not promoted

The following evidence is retained only with its stated limitation:

| Evidence | Disposition |
| --- | --- |
| NASA NACA TN 2410 full body | `VERIFIED_SOURCE_NOT_TASK172_TRANSFER_AUTHORITY`; complete body, but gases/liquid-metals scope and no exact pure-water TASK026 combination rule |
| Yang 1962 Crossref record and abstract | `BIBLIOGRAPHIC_DISCOVERY_ONLY`; no complete publisher body acquired |
| Official ASME PDF link | `ACCESS_ATTEMPTED_NOT_ACQUIRED`; publisher access control returned HTTP 403 |
| OpenAlex OA status | `ACQUISITION_STATUS_CROSS_CHECK_ONLY`; not equation authority |
| NASA secondary reports mentioning Yang/Deissler | `SOURCE_DISCOVERY_AND_CROSS_CHECK_ONLY`; no exponent or equation copied |
| Sieder–Tate or any remembered factor | `NOT_USED` |
| Turbulent C3 correction | `NOT_TRANSFERRED` |
| Neutral factor `1.0` | `NOT_USED` |

## 7. Effective state and governance

```ini
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
TURBULENT_C3_CORRECTION_STATUS=REVIEWED_AUTHORITY
TURBULENT_C3_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false

HISTORICAL_RECORDS_REWRITTEN=false
TASK026_FILES_CHANGED=false
TASK026_EQUATIONS_CHANGED=false
TASK026_CONSTANTS_CHANGED=false
TASK026_DOMAINS_CHANGED=false
TURBULENT_C3_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

The source-body acquisition is complete for the NACA lineage and incomplete
for Yang's article.  That is enough to stop unbounded search for this gate,
but not enough to close the laminar wall-correction blocker.  The next gate is
therefore still:

```ini
NEXT_GATE=AWAIT_COMPLETE_LAMINAR_PRIMARY_SOURCE_AUTHORITY
NO_STEP_IMPLIES_THE_NEXT=true
```

The next gate must obtain a lawful complete source body or an explicitly
reviewed branch disposition for both native laminar branches.  It must not
transfer NACA's non-water result, infer omission from
`requires_wall_viscosity=false`, or change TASK026.

## 8. Receipt artifacts

The companion evidence JSON records the source hashes, rendered-body review,
rights/access findings, exact branch fields, disposition decisions and
unchanged blocker ledger.  The append-only registry adds an `r30_extension`
without rewriting R1–R29 records or their hashes.
