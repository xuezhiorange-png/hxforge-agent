# TASK-165 — HXForge v0.6 Shell-and-Tube Scope, Source and Acceptance Freeze

> Governance/design contract for HXForge v0.6.
>
> TASK-165 freezes the v0.6 shell-and-tube product boundary, engineering-source
> hierarchy, coarse task allocation, semantic input/output contract, Golden-case
> classes and release-acceptance policy. It performs no new engineering
> calculation and does not authorize TASK-166 implementation.

## 1. Authority and frozen baseline

| Field | Frozen value |
|---|---|
| Authorizing Issue | #253 — `[TASK-165][v0.6][AUTHORIZED] Freeze shell-and-tube scope, sources and acceptance` |
| Authorization source | explicit user authorization |
| v0.6 base main SHA | `f49eff1485f731ff2ebbab898657fa8bd52485aa` |
| v0.6 base main tree | `b5b4524589378e3939b9c7b5796f134d807ee878` |
| v0.5 post-merge CI | run `34213968384` — success |
| v0.5 fresh nightly | run `34214832561` — success |
| Version | `HXFORGE_V0_6` |
| Theme | `SHELL_AND_TUBE_SINGLE_PHASE_ENGINEERING_DESIGN_CLOSURE` |
| Model level | steady-state, single-phase, 0D / L1 sizing / L2 rating |
| TASK-165 status in this document | freeze candidate; becomes repository authority only after separate review + merge authorization |

```text
V0_6_BASE_MAIN_SHA=f49eff1485f731ff2ebbab898657fa8bd52485aa
V0_6_BASE_MAIN_TREE=b5b4524589378e3939b9c7b5796f134d807ee878
TASK165_IMPLEMENTATION_AUTHORIZED=false
TASK166_AUTHORIZED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 2. v0.6 product position

v0.6 deepens the already-delivered shell-and-tube line. It is not a new
equipment-family expansion.

The version objective is:

```text
operating/design requirements
  -> approved discrete configuration + geometry candidates
  -> tube-side thermal/hydraulic evaluation
  -> Bell–Delaware-class shell-side thermal/hydraulic evaluation
  -> overall resistance / U / UA / thermal closure
  -> tube-side and shell-side pressure-drop closure
  -> preliminary engineering screening
  -> hard-constraint filtering
  -> deterministic ranking
  -> recommended candidate + alternatives
  -> provenance-complete engineering output
```

The existing v0.5 release-acceptance terminal capability is intentionally
narrow (fixed-tubesheet, current accepted rating chain). v0.6 is allowed to
extend the engineering design loop, but it must reuse the delivered
configuration, geometry, tube-side, shell-side, resistance, U/UA, thermal
closure, rating-composition and provenance authorities rather than duplicate
them.

## 3. Coarse task allocation

The v0.6 task allocation is closed at five coarse work packages.

| Task | Frozen work package | Primary responsibility |
|---|---|---|
| TASK-165 | Scope, Source and Acceptance Freeze | this document; source hierarchy; boundaries; Golden/acceptance policy |
| TASK-166 | Bell–Delaware Shell-Side Thermal-Hydraulic Model | Bell–Delaware geometry/corrections, corrected shell-side heat transfer and pressure drop |
| TASK-167 | Shell-and-Tube Engineering Screening | velocity, erosion, cleanability/fouling, thermal-expansion and preliminary vibration/configuration screening |
| TASK-168 | Manufacturable Candidate Generation and Sizing | discrete approved candidate enumeration, sizing, rating closure and feasibility |
| TASK-169 | Selection, Integration, Golden Validation and Release Acceptance | filtering/ranking, recommendation/alternatives, end-to-end Golden/replay/parity/release acceptance |

```text
TASK_COUNT=5
TASK_GRANULARITY=COARSE
ONE_PRIMARY_PR_PER_TASK=true
FORMULA_PER_TASK_SPLITTING=false
CORRECTION_PR_ALLOWED_ONLY_WHEN_A_REVIEWED_GATE_REQUIRES_IT=true
```

A factor, equation, correction term or small formula group must not become its
own Task merely to reduce implementation size.

## 4. Scope

### 4.1 In scope

v0.6 may implement and release:

1. steady-state single-phase shell-and-tube engineering design/rating;
2. `FIXED_TUBESHEET`, `U_TUBE` and `FLOATING_HEAD` as the construction
   families available to configuration/candidate logic, subject to downstream
   capability and authority checks;
3. approved discrete shell diameter, tube OD, tube wall, tube length, tube
   count, pitch, layout, tube-pass count, baffle type, baffle cut, baffle
   spacing and baffle count;
4. Bell–Delaware-class shell-side heat-transfer correction;
5. Bell–Delaware-class shell-side pressure-drop decomposition;
6. tube-side pressure-drop closure using delivered tube-side authorities;
7. overall resistance / U / UA and thermal-performance closure using delivered
   authorities;
8. preliminary engineering screening for velocity, erosion, fouling /
   cleanability, thermal expansion and flow-induced vibration risk;
9. hard feasibility against duty, area/UA and tube-/shell-side allowable
   pressure drop;
10. deterministic multi-candidate ranking and Top-N alternatives;
11. complete provenance, source identity, warnings, blockers and replay
   evidence.

### 4.2 Explicit non-scope

The following are not v0.6 capabilities:

- plate heat exchangers;
- air coolers;
- condensation;
- evaporation;
- reboilers;
- generic two-phase pressure drop;
- refrigerant distribution;
- detailed tubesheet calculation;
- detailed ASME Section VIII pressure-vessel design;
- detailed flange-strength design;
- fatigue;
- seismic or wind design;
- detailed nozzle/local-stress design;
- FEA;
- CFD;
- CAD/solid-model generation;
- proprietary vendor geometry inversion;
- a claim that HXForge output is legally certified or code compliant.

Unsupported requests must remain fail-closed or explicitly deferred; they must
not be approximated silently.

## 5. Existing repository authorities inherited by v0.6

TASK-165 does not reopen delivered v0.5 authorities.

### 5.1 Configuration identity

The canonical construction-family vocabulary remains the existing
`ConstructionFamily` set:

```text
FIXED_TUBESHEET
U_TUBE
FLOATING_HEAD
```

The existing TASK-020 authority modes remain:

```text
INTERNAL_GENERIC
APPROVED_RULE_PACK
```

A standard claim requires `APPROVED_RULE_PACK`; `INTERNAL_GENERIC` may
calculate engineering results but must not be presented as TEMA/API/ISO/ASME
compliance.

### 5.2 Kern-style shell-side inherited baseline

The existing TASK-033 preferred shell-side heat-transfer authority remains an
inherited screening/reference baseline:

```text
ENGINEERING_AUTHORITY_ID=TASK033_KERN_KHARAJI_2021_EQ58_NO_WALL_CORRECTION_V1
SOURCE_ID=SRC-INTECHOPEN-100450-KHARAJI-2021
SOURCE_DOI=10.5772/intechopen.100450
REYNOLDS_RANGE=2e3 < Re_s < 1e6
```

The existing TASK-034 shell-side pressure-drop authority remains an inherited
screening/reference baseline:

```text
CORRELATION_ID=TASK034_KERN_BAYRAM_SEVILGEN_2017_EQ15_EQ16_EQ17_WALL_VISCOSITY_CORRECTION_V1
SOURCE_ID=SRC-MDPI-ENERGIES-2017-1156-BAYRAM-SEVILGEN
SOURCE_DOI=10.3390/en1101156
SUPPORTED_PHASE=SINGLE_PHASE_LIQUID
SUPPORTED_SHELL_TYPE=E_SHELL
SUPPORTED_SHELL_PASS_COUNT=1
SUPPORTED_BAFFLE_TYPE=SINGLE_SEGMENTAL
SUPPORTED_TUBE_LAYOUT=TRIANGULAR_PITCH
SUPPORTED_BAFFLE_CUT=CONSTANT_25_PERCENT_SOURCE_PROFILE
REYNOLDS_RANGE=400 < Re_s < 1000000
```

These Kern-style authorities are not Bell–Delaware authority and must never
be relabeled as such.

## 6. v0.6 engineering-source authority

### 6.1 Source-class separation

v0.6 freezes two non-interchangeable source classes:

1. **Numeric correlation authority** — equations/coefficients used by the
   deterministic kernel, with correlation identity, bibliographic source,
   applicability envelope and provenance.
2. **Restricted standard rule authority** — licensed/copyright-restricted
   rules handled only through the existing TASK-012 rule-pack boundary.

A restricted-standard rule must not be converted into anonymous source code,
and a public correlation must not be presented as a standard requirement.

### 6.2 Bell–Delaware source set

#### Method-origin authority

```text
SOURCE_ID=SRC-UDEL-BELL-1963-FINAL-REPORT
AUTHOR=Kenneth J. Bell
TITLE=Final report of the cooperative research program on shell and tube heat exchangers
PUBLISHER=University of Delaware Engineering Experimental Station
YEAR=1963
ROLE=METHOD_ORIGIN_AND_PROVENANCE
```

Bibliographic identity is independently discoverable from WorldCat/OCLC.

#### Public implementation-equation authority

```text
SOURCE_ID=SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE
AUTHORS=Caroline de O. Goncalves; Andre L. H. Costa; Miguel J. Bagajewicz
TITLE=Linear method for the design of shell and tube heat exchangers using the Bell-Delaware method
PUBLICATION=AIChE Journal
VOLUME=65
ISSUE=8
ARTICLE=e16602
YEAR=2019
DOI=10.1002/aic.16602
ROLE=PUBLIC_IMPLEMENTATION_EQUATION_AUTHORITY
```

TASK-166 may implement the Bell–Delaware formulation only from equations and
definitions that are explicitly traceable to this frozen public source set.
If an equation, coefficient table, interpolation rule or applicability bound
cannot be verified from the authorized source set, that element is
`SOURCE_REQUIRED` / blocked; it is not guessed.

#### Independent explanatory cross-check

```text
SOURCE_ID=SRC-SERTH-2007-PROCESS-HEAT-TRANSFER-CH6
AUTHOR=Robert W. Serth
TITLE=Process Heat Transfer: Principles and Applications
LOCATION=Chapter 6 - The Delaware Method
YEAR=2007
ROLE=INDEPENDENT_METHOD_CROSSCHECK
```

The cross-check source may validate decomposition/terminology, but it must not
silently override the selected implementation-equation authority.

### 6.3 Bell–Delaware semantic output surface

TASK-166 must make the correction structure explainable. At minimum the
successful result surface must expose, where applicable:

```text
ideal_crossflow_heat_transfer_coefficient
Jc
Jl
Jb
Js
Jr
corrected_shell_heat_transfer_coefficient

ideal_crossflow_pressure_drop
crossflow_pressure_drop
window_pressure_drop
end_zone_pressure_drop
Rl
Rb
Rs
total_shell_pressure_drop
```

It must also expose the geometry/flow quantities needed to explain the
corrections (crossflow/window/leakage/bypass regions, effective tube rows,
baffle-spacing identity and related source/applicability evidence).

The exact numeric equations, coefficient data and interpolation rules belong
to TASK-166 design/implementation, but their source must be within the frozen
source set above.

### 6.4 Restricted standard authorities

Restricted standards are metadata/rule-pack authority only.

#### TEMA

For new v0.6 work, the standard metadata target is the **2026 Edition of the
TEMA Standards**, issued 2026-08-01. TEMA states that the Eleventh Edition
(2024) remains current for work in process during a six-month transition
period.

Policy:

```text
TEMA_2026_NEW_WORK_METADATA_TARGET=true
TEMA_11_2024_ALLOWED_ONLY_WHEN_EXPLICITLY_BOUND_AS_WORK_IN_PROCESS=true
SILENT_TEMA_EDITION_SUBSTITUTION=false
TEMA_RULES_REQUIRE_TASK012_APPROVED_RULE_PACK=true
TEMA_TEXT_TABLE_FIGURE_COPY_IN_REPO=false
```

#### API 660

At TASK-165 freeze time, the published API 660 source is 9th Edition (2015)
with Addendum 1 (2020). API lists Edition 10 as in development.

```text
API660_PUBLISHED_PROFILE=9TH_EDITION_2015_PLUS_ADDENDUM_1_2020
API660_EDITION_10_STATUS=IN_DEVELOPMENT_NOT_AUTHORITY
API660_RULES_REQUIRE_TASK012_APPROVED_RULE_PACK=true
```

A future published Edition 10 does not automatically change v0.6 authority.

#### ISO 16812

```text
ISO_PROFILE=ISO_16812_2019_EDITION_3
ISO_STATUS=CURRENT_CONFIRMED_2024
ISO_RULES_REQUIRE_TASK012_APPROVED_RULE_PACK=true
```

#### ASME

Detailed ASME pressure-vessel/mechanical design is non-scope for v0.6.
ASME-derived limits may only enter preliminary screening through an approved
rule pack with explicit edition/license/provenance identity. No v0.6 result
may claim ASME design compliance.

## 7. Semantic input contract

TASK-166 through TASK-169 may refine exact Python schemas, but they may not
change the following semantic input classes without reopening TASK-165.

### 7.1 Upstream accepted authorities

- accepted shell-and-tube configuration identity;
- accepted tube layout / shell-bundle / baffle geometry identities;
- accepted tube-side and shell-side upstream state identities;
- accepted v0.5 thermal/rating composition where used;
- approved rule-pack/catalog/source snapshots.

### 7.2 Thermal/process requirements

- hot-side and cold-side stream/property authority;
- required duty or an equivalent closed thermal specification;
- inlet/outlet state constraints;
- fouling/resistance inputs;
- allowable tube-side pressure drop;
- allowable shell-side pressure drop.

### 7.3 Manufacturability/design constraints

- construction-family allowlist;
- installation/orientation envelope;
- approved shell sizes;
- approved tube OD / wall / length;
- approved pitch/layout profiles;
- approved tube-pass counts;
- approved baffle type/cut/spacing/count bounds;
- material restrictions where required by the calculation/screening path;
- rule-pack identity when any external-standard claim is requested.

### 7.4 Ranking policy

Ranking objectives/weights must be explicit and versioned. A missing ranking
policy may use a frozen project default only if that default has its own
identity and provenance. Ranking must never be influenced by unordered
iteration, random seeds or presentation-only text.

## 8. Semantic output contract

Each successful candidate must expose enough information to audit why it was
generated, why it is feasible and why it was ranked.

Required semantic groups:

1. **Configuration** — construction family, orientation, shell/tube pass
   counts and component identity.
2. **Geometry** — shell diameter/ID authority, tube OD/wall/length/count,
   pitch/layout, baffle type/cut/spacing/count and approved catalog identities.
3. **Tube-side thermal/hydraulic** — velocity/Re/Nu/h and modeled pressure-drop
   decomposition from delivered authorities.
4. **Shell-side Bell–Delaware** — ideal state, correction factors, corrected
   heat-transfer coefficient and pressure-drop decomposition.
5. **Overall thermal closure** — resistance components, U, UA required/available,
   duty closure and overdesign/margin.
6. **Engineering screening** — velocity/erosion, fouling/cleanability,
   thermal-expansion, vibration and configuration suitability with
   `PASS|WARN|BLOCKED`.
7. **Constraint closure** — thermal, tube-side DP, shell-side DP and hard
   manufacturability constraint status.
8. **Selection** — deterministic score/order, recommendation reason and
   alternative-candidate reasons.
9. **Traceability** — source identities, applicability results, warnings,
   blockers, provenance graph, software version and canonical result identity.

A ranked candidate that has any hard blocker is not recommendable.

## 9. Engineering-screening boundary

TASK-167 is **preliminary screening**, not detailed mechanical design.

It may emit:

- tube velocity screen;
- shell velocity screen;
- nozzle velocity screen when the required geometry exists;
- erosion-risk screen;
- fouling/cleanability screen;
- thermal-expansion risk screen;
- construction-family suitability screen;
- preliminary flow-induced-vibration risk screen.

It must emit an aggregate:

```text
PASS
WARN
BLOCKED
```

Standard-specific numeric limits require an approved rule pack. If the
required standard authority is missing, an internal-generic calculation may
still report source-transparent diagnostic quantities, but it must not emit a
standard-compliance PASS.

## 10. Manufacturable candidate policy

TASK-168 must enumerate discrete candidates from approved authorities.

At minimum the candidate variable surface may include:

```text
construction_family
shell_diameter
tube_outer_diameter
tube_wall_thickness
tube_length
tube_count
tube_pitch
tube_layout
tube_pass_count
baffle_type
baffle_cut
baffle_spacing
baffle_count
```

Rules:

- arbitrary continuous geometry invented by an optimizer is forbidden;
- every discrete dimension must bind to an approved catalog/rule/source
  snapshot or an explicitly authorized project-defined discrete set;
- candidate generation must be deterministic for the same authoritative
  inputs;
- infeasible candidates may be retained as auditable blocked records but
  cannot enter recommendation ranking;
- no geometry may be silently repaired after rating merely to make it pass.

The candidate evaluation sequence is frozen as:

```text
Candidate
 -> Geometry
 -> Tube-side thermal/hydraulic
 -> Bell-Delaware shell-side
 -> overall resistance / U / UA
 -> thermal closure
 -> tube-side DP
 -> shell-side DP
 -> engineering screening
 -> PASS / WARN / BLOCKED
```

## 11. Golden-case classes

TASK-169 must materialize five versioned Golden classes from reviewed,
redistributable or metadata-safe sources. TASK-165 freezes the class purpose,
not yet the final numeric fixture payload.

| Golden ID | Required purpose |
|---|---|
| `V06-G01` | fixed-tubesheet, E-shell, steady single-phase success; complete Bell–Delaware thermal + DP + thermal closure |
| `V06-G02` | U-tube success; thermal-expansion/configuration screening is materially exercised |
| `V06-G03` | floating-head success; fouling/cleanability/configuration screening is materially exercised |
| `V06-G04` | pressure-drop-constrained multi-candidate case; at least one candidate rejected by tube/shell DP and deterministic ranking selects a feasible alternative |
| `V06-G05` | negative fail-closed case; unsupported two-phase or missing required source/license authority must not yield a recommendation |

Each Golden fixture must record:

- source ID and source location;
- redistribution/license status;
- normalized input identity;
- expected result identity or approved numeric expectation;
- tolerance class;
- reviewer/approval evidence;
- provenance/source hash.

## 12. Numeric tolerance policy

Tolerance is part of Golden authority and may not be loosened ad hoc to make a
test pass.

```text
ENERGY_BALANCE_RELATIVE_ERROR_MAX=0.001
THERMAL_DUTY_CLOSURE_RELATIVE_ERROR_MAX=0.001
DIRECT_PUBLISHED_EQUATION_REPRODUCTION_RELATIVE_ERROR_MAX=0.005
PUBLISHED_REFERENCE_SHELL_H_RELATIVE_ERROR_MAX=0.02
PUBLISHED_REFERENCE_SHELL_DP_RELATIVE_ERROR_MAX=0.02
MANUFACTURABLE_CATALOG_MEMBERSHIP=EXACT
HARD_CONSTRAINT_STATUS=EXACT
RANKING_ORDER=EXACT
CANONICAL_IDENTITY_REPLAY=EXACT
PY311_PY312_CANONICAL_PARITY=EXACT
```

A published case whose rounding, missing data or ambiguity cannot support the
frozen tolerance must not be promoted to Golden authority. It must be replaced
or remain non-authoritative; the tolerance is not widened silently.

## 13. Acceptance gates

v0.6 release acceptance requires all of the following:

```text
SHELL_TUBE_FIXED_GEOMETRY_RATING=PASS

BELL_DELAWARE_HEAT_TRANSFER=PASS
BELL_DELAWARE_PRESSURE_DROP=PASS
BELL_DELAWARE_PROVENANCE_COMPLETE=PASS

SHELL_TUBE_ENGINEERING_SCREENING=PASS
THERMAL_EXPANSION_SCREENING=PASS
VIBRATION_SCREENING=PASS

SHELL_TUBE_CANDIDATE_GENERATION=PASS
SHELL_TUBE_SIZING=PASS
SHELL_TUBE_MULTI_CANDIDATE_RANKING=PASS

TUBE_DP_CONSTRAINT_CLOSURE=PASS
SHELL_DP_CONSTRAINT_CLOSURE=PASS
THERMAL_DUTY_CLOSURE=PASS

DETERMINISTIC_REPLAY=PASS
PROVENANCE_COMPLETE=PASS
PY311_PY312_PARITY=PASS

GOLDEN_V06_G01=PASS
GOLDEN_V06_G02=PASS
GOLDEN_V06_G03=PASS
GOLDEN_V06_G04=PASS
GOLDEN_V06_G05=PASS

END_TO_END_RELEASE_DEMO=PASS
```

No single Golden success may substitute for the full acceptance set.

## 14. Testing/governance strategy

The user-approved coarse-task strategy is binding:

```text
DEVELOPMENT_SLICE_TESTING=TARGETED_ONLY
TASK_LOCAL_REGRESSION=REQUIRED
FULL_SUITE_PER_INTERMEDIATE_COMMIT=false

ONE_PRIMARY_PR_PER_TASK=true
EXACT_HEAD_CI_REQUIRED_ONCE_PER_TASK_FINAL_HEAD=true
MAIN_POST_MERGE_CI_REQUIRED=true

FINAL_TASK_HEAD_FULL_CI=true
FINAL_TASK_HEAD_PY311_PY312_REQUIRED=true
FINAL_RELEASE_ACCEPTANCE_NIGHTLY_REQUIRED=true
```

Intermediate implementation slices may use targeted tests. Full repository CI
is a task-final gate, not a reason to create one Task/PR for each Bell factor
or screening formula.

## 15. Source/conflict/fail-closed policy

1. Every numeric correlation must name one selected implementation authority.
2. Historical-origin, implementation-equation and cross-check sources remain
   distinct provenance roles.
3. Conflicting source equations are never averaged.
4. A source conflict blocks the affected output until reviewed.
5. Standard-derived constraints require approved rule-pack evidence.
6. Missing licensed standard content does not block internal-generic
   calculations that do not need the rule, but it blocks the corresponding
   external-standard claim.
7. No extrapolation is silent.
8. No unsupported family/regime is coerced into a supported one.
9. No caller claim is accepted as engineering authority without replay or
   source binding.
10. No downstream task changes TASK-165 scope/source/acceptance semantics
    without a separately authorized TASK-165 amendment.

## 16. External metadata references

These references establish bibliographic/current-version metadata only; they
do not authorize copying protected content into the repository.

- Bell, K. J. (1963), *Final report of the cooperative research program on
  shell and tube heat exchangers*, University of Delaware Engineering
  Experimental Station. WorldCat:
  https://search.worldcat.org/title/16107403
- Goncalves, C. de O.; Costa, A. L. H.; Bagajewicz, M. J. (2019),
  *Linear method for the design of shell and tube heat exchangers using the
  Bell-Delaware method*, AIChE Journal 65(8), e16602,
  DOI 10.1002/aic.16602:
  https://doi.org/10.1002/aic.16602
- TEMA Standards metadata/current edition:
  https://tema.org/standards/
- TEMA edition transition metadata:
  https://support.tema.org/
- API standards catalog/plan:
  https://www.api.org/products-and-services/standards/standards-plan
- ISO 16812:2019:
  https://www.iso.org/standard/74317.html

## 17. Lifecycle stop gate

This document being authored and pushed does not make it frozen authority.

```text
TASK165_FREEZE_CANDIDATE_AUTHORED=true
TASK165_FREEZE_REVIEW_REQUIRED=true
TASK165_READY_AUTHORIZED=false
TASK165_MERGE_AUTHORIZED=false
TASK166_AUTHORIZED=false
TASK166_STARTED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The next gate after Draft PR + exact-head CI is an independent TASK-165
freeze-candidate review. Ready/merge and TASK-166 each require later explicit
authorization.

## 18. Source Authority Amendment R3 — complete Bell–Delaware `Js` authority

This section is the R3 amendment proposal authorized by Issue #258. It is a
documentation-only source correction and remains a freeze candidate until its
independent review and merge gate complete. It does not authorize TASK-166
implementation.

```text
TASK165_R3_AUTHORITY_ISSUE=258
TASK165_R3_STATUS=PROPOSED_PENDING_INDEPENDENT_REVIEW_AND_MERGE
R1_HISTORY_PRESERVED=true
R1_RESULT=BLOCKED_SOURCE_AUTHORITY_STILL_INCOMPLETE
R2_HISTORY_PRESERVED=true
R2_RESULT=BLOCKED_JAMIL_JS_AUTHORITY_INCOMPLETE
TASK166_IMPLEMENTATION_RESUME_AUTHORIZED=false
TASK167_AUTHORIZED=false
```

### 18.1 Reconciled `psi_n` task boundary

The primary Gonçalves/Costa/Bagajewicz article distinguishes the tube-count
relation from the fixed-geometry shell-side rating relations. In its tube
count equations (7)--(9), `psi_n` represents omitted tubes caused by multiple
tube passes and is selected as a function of tube passes and shell diameter.
The Bell--Delaware fixed-geometry rating equations begin later with the
ideal/corrected shell-side heat-transfer and pressure-drop relations. The
article's rating model explicitly assumes uniformly distributed baffles for
that presentation.

Accordingly, the R3 task-boundary correction is:

```text
PSI_N_TASK_BOUNDARY_VERIFIED=true
PSI_N_REQUIRED_BY_TASK166=false
PSI_N_DISPOSITION=TASK168_IF_SIZING_REQUIRES_IT
PSI_N_CAPABILITY_DELETED=false
PSI_N_TASK166_FIXED_GEOMETRY_RATING_INPUT=false
```

`psi_n` is therefore re-homed as a possible TASK-168 tube-count / multi-pass
sizing prerequisite within the already frozen sizing scope. This does not
remove the capability, add a task, or change any TASK-165 product semantics.
It is not an input to TASK-166 fixed-geometry `Jc`, `Jl`, `Jb`, `Js`, `Jr`,
`Rl`, `Rb`, `Rs`, shell-side heat-transfer, or shell-side pressure-drop
rating.

### 18.2 Independently admitted Jamil supplemental authority

The accepted author manuscript for the following peer-reviewed article was
independently retrieved from the Northumbria University Research Portal and
read through its Bell--Delaware section and Appendix A:

```text
SOURCE_ID=SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS
AUTHORS=Muhammad Ahmad Jamil; Talha S. Goraya; Muhammad Wakil Shahzad; Syed M. Zubair
TITLE=Exergoeconomic optimization of a shell-and-tube heat exchanger
PUBLICATION=Energy Conversion and Management
VOLUME=226
ARTICLE=113462
YEAR=2020
DOI=10.1016/j.enconman.2020.113462
SOURCE_CLASS=PEER_REVIEWED_JOURNAL_ARTICLE
SOURCE_ARTIFACT=Northumbria University accepted author manuscript
SOURCE_ARTIFACT_LOCATION=https://researchportal.northumbria.ac.uk/ws/files/40570913/sthx.pdf
SOURCE_ARTIFACT_SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
SOURCE_ARTIFACT_LICENSE=CC-BY-NC-ND
EXACT_LOCATION=Appendix, Table A.1, manuscript p.57
SOURCE_ROLE=SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY
```

Table A.1 supplies complete layout/Re-regime rows containing `a1`, `a2`,
`a3`, `a4` for the ideal tube-bank heat-transfer parameterization and `b1`,
`b2`, `b3`, `b4` for the ideal tube-bank friction-factor parameterization.
The rows provide the selection dimensions needed by the Bell--Delaware ideal
tube-bank correlations. The accepted manuscript is admitted only for these
two parameter families:

```text
JAMIL_A1_A4_AUTHORITY_VERIFIED=true
JAMIL_B1_B4_AUTHORITY_VERIFIED=true
JAMIL_SCOPE=a1_a4,b1_b4
JAMIL_AUTHORIZED_FOR_IDEAL_TUBE_BANK_HEAT_TRANSFER_PARAMETERS=true
JAMIL_AUTHORIZED_FOR_IDEAL_TUBE_BANK_FRICTION_PARAMETERS=true
JAMIL_AUTHORIZED_FOR_JS=false
```

The same manuscript's Table A.2 contains a `Js`-labelled expression, but R2
correctly found that it does not close the exponent selection and complete
applicability contract required by TASK-166. It remains non-authoritative for
`Js`; it is not silently promoted by this amendment.

### 18.3 Formal `Js` source verification

The following is the formal journal source for the previously open unequal
baffle-spacing heat-transfer correction gap:

```text
SOURCE_ID=SRC-SAIF-TARIQ-2025-JMES-UNEQUAL-BAFFLE-SPACING-JS
AUTHORS=Mohd Saif Sonu; Mohammad Tariq
TITLE=The impact of baffle configuration on the performance of a shell-and-tube heat exchanger using the Bell-Delaware approach
PUBLICATION=Journal of Mechanical Engineering and Sciences
VOLUME=19
ISSUE=4
PAGES=10877-10888
YEAR=2025
DOI=10.15282/jmes.19.4.2025.4.0852
SOURCE_ARTICLE_LOCATION=https://journal.ump.edu.my/jmes/article/view/12360
SOURCE_PDF_LOCATION=https://journal.ump.edu.my/jmes/article/download/12360/3856/55250
SOURCE_PDF_SHA256=0f66f8efbb4ce071a5408bed5f938d4d659189c199231289e674b92f1d0c9571
SOURCE_PDF_BYTES=1361143
SOURCE_LICENSE=CC-BY-NC-4.0
SOURCE_ROLE=SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY_FOR_JS_ONLY
EXACT_LOCATION=Section 2.1.3, printed p.10882, Eq.(21), with spacing labels/definitions in the adjoining baffle-spacing figure and text
```

The formal article presents the Bell--Delaware shell-side heat-transfer
correction as `h_s = h_id J_c J_l J_b J_s J_r` in Eq. (17). Its Eq. (21)
defines the unequal-inlet/outlet-spacing heat-transfer correction as:

```text
Js = ((Nb - 1) + (Lbi/Lbc)^(1-n1) + (Lbo/Lbc)^(1-n1))
     / ((Nb - 1) + (Lbi/Lbc) + (Lbo/Lbc))
```

The R3 amendment records the source semantics as follows:

```text
JS_CORRECTION_FAMILY=UNEQUAL_BAFFLE_SPACING_HEAT_TRANSFER
JS_RELATION_ID=SAIF_TARIQ_2025_JMES_EQ21
JS_EQUATION_VERIFIED=true
JS_VARIABLE_SEMANTICS_VERIFIED=true
JS_NB_SEMANTIC=number_of_baffles
JS_LBI_SEMANTIC=inlet_baffle_spacing
JS_LBC_SEMANTIC=central_baffle_spacing
JS_LBO_SEMANTIC=outlet_baffle_spacing
JS_N1_SEMANTIC=Reynolds_selected_spacing_exponent
JS_NUMERATOR_SEMANTICS=(Nb-1)_plus_inlet_and_outlet_spacing_ratios_to_(1-n1)
JS_DENOMINATOR_SEMANTICS=(Nb-1)_plus_unpowered_inlet_and_outlet_spacing_ratios
JS_REYNOLDS_BOUNDARY_VERIFIED=true
JS_RE_GE_100_N1=0.6
JS_RE_LT_100_N1=1/3
JS_RE_BOUNDARY_INCLUSIVE_SIDE=RE_GE_100
JS_UNIFORM_SPACING_LIMIT_VERIFIED=true
JS_LIMITING_RULE_VERIFIED=true
JS_UNIFORM_SPACING_CONDITION=Lbi=Lbc=Lbo
JS_UNIFORM_SPACING_VALUE=1
JS_BAFFLE_COUNT_TERMS_VERIFIED=true
JS_PHYSICAL_DENOMINATOR_DOMAIN=Nb_is_a_positive_physical_count_and_Lbi,Lbc,Lbo_are_finite_positive_spacings
JS_PHYSICAL_DENOMINATOR_DOMAIN_IS_INPUT_PRECONDITION=true
JS_INVALID_DOMAIN_ACTION=SOURCE_REQUIRED_OR_BLOCKED
```

The source's exact threshold is inclusive at `Re = 100`: `n1 = 0.6` for
`Re >= 100`, and `n1 = 1/3` for `Re < 100`. The source explicitly assigns
`Js = 1` when all baffle spacings are uniform. The implementation must retain
that explicit limiting branch and must reject a non-finite or non-positive
physical spacing, an invalid baffle count, or a non-positive/non-finite
formula denominator rather than extrapolating.

The article's evaluated Bell--Delaware model is a single-phase, segmental-
baffle shell-and-tube model with a TEMA E-type, one shell pass and a single-
pass fixed-tube-sheet case. The `Js` authority is therefore admitted only for
current cases whose geometry authority supplies the source variables and
whose model is within the verified segmental-baffle/source envelope. This
source does not authorize silent extension to another baffle family,
multi-shell-pass arrangement, two-phase service, or an unverified geometry
representation.

The article also confirms that `Rs` is a pressure-drop end-zone correction;
that pressure-drop quantity is not the heat-transfer `Js` relation. No
pressure-drop authority is transferred by this amendment.

The resulting closure assertions are:

```text
JS_SOURCE_IDENTITY_VERIFIED=true
JS_EQUATION_VERIFIED=true
JS_VARIABLE_SEMANTICS_VERIFIED=true
JS_EXPONENT_SELECTION_VERIFIED=true
JS_REYNOLDS_BOUNDARY_VERIFIED=true
JS_UNIFORM_SPACING_LIMIT_VERIFIED=true
JS_APPLICABILITY_VERIFIED=true
JS_COMPLETE_IMPLEMENTATION_AUTHORITY_VERIFIED=true
```

### 18.4 Effective source hierarchy after R3

R3 does not blend authorities. The effective hierarchy for TASK-166 is:

```text
Bell 1963
  = METHOD_ORIGIN_AND_PROVENANCE

Gonçalves / Costa / Bagajewicz 2019
  = PRIMARY_IMPLEMENTATION_EQUATION_AUTHORITY

Jamil / Goraya / Shahzad / Zubair 2020
  = SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY_FOR_a1_a4_AND_b1_b4

Saif / Tariq 2025
  = SUPPLEMENTAL_IMPLEMENTATION_AUTHORITY_FOR_JS_UNEQUAL_BAFFLE_SPACING_ONLY
```

```text
GONCALVES_PRIMARY_IMPLEMENTATION_AUTHORITY=true
GONCALVES_PRIMARY=true
JAMIL_SCOPE_CLOSED=true
JAMIL_AUTHORIZED_FOR_JS=false
SAIF_TARIQ_SCOPE=Js_ONLY
SAIF_TARIQ_SCOPE_CLOSED=true
SUPPLEMENTAL_AUTHORITY_SCOPE_CLOSED=true
SUPPLEMENTAL_MAY_SILENTLY_OVERRIDE_PRIMARY=false
SERTH_REMAINS_CROSSCHECK_ONLY=true
SOURCE_CONFLICT_POLICY=FAIL_CLOSED
IMPLEMENTATION_SOURCE_CONFLICT=false
```

Saif/Tariq is not authorized for `Jc`, `Jl`, `Jb`, `Jr`, `Rl`, `Rb`, `Rs`,
the ideal heat-transfer relation generally, or the ideal pressure-drop
relation generally. Jamil is not authorized for `Js`. If a supplemental
source conflicts materially with the selected primary relation or with
another authorized source on an overlapping surface, the affected output is
blocked; the sources are never averaged, arbitrarily selected, or silently
overridden.

### 18.5 Wiley Supporting Information and TASK-032 disposition

The official Wiley article record confirms the attachment identity
`aic16602-sup-0001-Supinfo.docx` under DOI `10.1002/aic.16602`, but the
attachment bytes were not obtained in this amendment. Its content is not
represented as verified:

```text
WILEY_SI_ATTACHMENT_IDENTITY_VERIFIED=true
WILEY_SI_BYTES_OBTAINED=false
WILEY_SI_TABLE_CONTENT_VERIFIED=false
WILEY_SI_TABLE_S2_S3_REQUIRED_AS_EXCLUSIVE_TASK166_PREREQUISITE=false
```

The Jamil Table A.1 evidence closes the `a1`--`a4` and `b1`--`b4`
supplemental parameter requirement without claiming Wiley Table S2/S3
content. Table S1 / `psi_n` is now a possible TASK-168 sizing prerequisite,
not a TASK-166 fixed-geometry rating prerequisite.

The current TASK-032 authority explicitly records that its flow-regime
classification is not computable. TASK-166 must not cite TASK-032 as a
general laminar/turbulent classifier for `Js`. For the `Js` branch only, the
implementation may use an authoritative shell-side Reynolds value and the
closed threshold above; this does not create a general TASK-032 regime
authority.

```text
TASK032_FLOW_REGIME_CLASSIFICATION_AUTHORITY_PRESENT=false
TASK032_FLOW_REGIME_CLASSIFICATION_NOT_COMPUTABLE=true
TASK166_JS_REYNOLDS_SELECTION_REUSES_TASK032_REGIME_AUTHORITY=false
TASK166_JS_REYNOLDS_SELECTION_USES_AUTHORIZED_RE_VALUE=true
```

### 18.6 R3 scope and completion audit

This amendment changes only the source-authority completeness path. It does
not change the product boundary or any coarse work package:

```text
VERSION=HXFORGE_V0_6
TASK_COUNT=5
TASK165_SCOPE_CHANGED=false
TASK_COUNT_CHANGED=false
TASK166_SCOPE_CHANGED=false
TASK166_WORK_PACKAGE_CHANGED=false
TASK167_SCOPE_CHANGED=false
TASK168_CORE_SCOPE_CHANGED=false
TASK169_SCOPE_CHANGED=false
GOLDEN_CLASSES_CHANGED=false
NUMERIC_TOLERANCE_POLICY_CHANGED=false
NON_SCOPE_CHANGED=false
PRODUCTION_FILES_CHANGED=false
TEST_FILES_CHANGED=false
WORKFLOW_FILES_CHANGED=false
DEPENDENCIES_CHANGED=false
TASK166_SOURCE_AUTHORITY_COMPLETE=true
TASK165_R3_AMENDMENT_AUTHORED=true
TASK166_IMPLEMENTATION_RESUME_AUTHORIZED=false
TASK167_STARTED=false
```

No Bell--Delaware formula, coefficient table, implementation package, test,
workflow, or dependency is added by R3. The next gate remains independent
review of this TASK-165 amendment, followed by separately authorized
Ready/merge and TASK-166 implementation gates.
