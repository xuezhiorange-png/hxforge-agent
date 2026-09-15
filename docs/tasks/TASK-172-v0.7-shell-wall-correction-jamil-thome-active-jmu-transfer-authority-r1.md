# TASK172 R1 — Jamil/Thome active `J_mu` transfer authority

## 1. Receipt and non-implementation boundary

This append-only record is a targeted source-transfer review for the active
shell-side wall-viscosity factor named `J_mu` by the native Jamil operational
representation. It does not implement the factor, modify TASK166, authorize a
wall-temperature producer, or start TASK172 implementation or numerical work.

```text
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JAMIL_THOME_ACTIVE_JMU_TRANSFER_AUTHORITY_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=519a553a7b72a37adca5f81b9dd356010dcc88c1
MODE=TARGETED_JAMIL_THOME_ACTIVE_JMU_TRANSFER_AUTHORITY_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The previous coefficient-lineage resolution remains authoritative within its
scope: `TASK166_NATIVE_JAMIL_OPERATIONAL_VARIANT` uses an unnormalized `j_i`
representation, while Bell 1960's normalized-`j` factor is not transferable
to it. This record addresses only the separate Jamil/Thome `J_mu` route.

## 2. Accepted native formulation

The accepted Jamil manuscript is the direct source for the operational
equation placement used by TASK166. Its relevant locations are §2.2.2, PDF
p.11, Eqs. (6)--(9), Appendix Table A.1 on p.57, Appendix Table A.2 on
pp.58--59, and reference [9] on PDF p.50/printed p.51.

```text
JAMIL_BODY_ACQUIRED=true
JAMIL_BODY_SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
JAMIL_PUBLIC_ACCESS_PATH=https://nrl.northumbria.ac.uk/45157/1/sthx.pdf
JAMIL_JMU_SYMBOLIC_FORM_BOUND=true
JAMIL_SHELL_HTC_FORM=hs=hc*JC*JL*JB*JS*JR*Jmu
JAMIL_IDEAL_HTC_FORM=hc=ji*cp*G*Pr^(-2/3)
JAMIL_JMU_FORM=Jmu=(mu/mu_wall)^m
JAMIL_JMU_POSITION=separate_factor_after_hc_alongside_JC_JL_JB_JS_JR
JAMIL_JMU_SOURCE_REFERENCE=Jamil_Ref_9_Thome_Engineering_Data_Book_III_2004
```

This binds the symbolic factor and its combination position. It does not by
itself bind the value of `m`, a TASK172 local state producer, or a production
applicability domain.

## 3. Citation-directed Thome acquisition

### 3.1 Acquired relevant chapter

A public copy of the relevant *Engineering Data Book III*, Chapter 3,
*Single-Phase Shell-Side Flows and Heat Transfer*, was acquired for exact
chapter-level cross-checking. The downloaded body has 20 content pages and
contains the relevant §§3.4.6--3.4.7 and Table 3.1. Its chapter identity is
consistent with the official catalog description of Chapter 3, but the public
copy does not establish a transferable licence or an authenticated edition
chain to every form of the cited 2004 body.

```text
THOME_BODY_ACQUIRED=true
THOME_BODY_COMPLETE=true
THOME_RELEVANT_CHAPTER=CHAPTER_3_SINGLE_PHASE_SHELL_SIDE_FLOWS_AND_HEAT_TRANSFER
THOME_EDITION_IDENTITY_BOUND=true
THOME_EDITION_IDENTITY_SCOPE=RELEVANT_CHAPTER_CONTENT_IDENTITY_ONLY
THOME_BYTES_SHA256=326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4
THOME_ACCESS_PATH=https://files.engineering.com/files/e01daa74-5d7f-4923-a8fc-fa05132408b2/WOLVERINE_Single_Phase_Shell-Side_Flow_and_Heat_Transfer.pdf
THOME_RIGHTS_STATUS=COPY_RESTRICTED_RIGHTS_UNVERIFIED
THOME_AUTHORITY_STATUS=NOT_PROMOTED_PENDING_RIGHTS_AND_INDEPENDENT_REVIEW
THOME_SOURCE_ROLE=ACQUIRED_RELEVANT_CHAPTER_CROSS_CHECK_ONLY
```

The body observations are source observations, not a self-approved production
authority. The official publisher/catalog paths are recorded as identity
cross-checks; they do not grant access to the copyrighted body.

### 3.2 Exact Thome observations

In §3.4.6, printed p.3-12, Eq. (3.4.23), the chapter defines the wall
viscosity factor as the ratio of bulk viscosity to wall viscosity raised to
`m`:

```text
J_mu=(mu/mu_wall)^m
```

The same section states that correlations are normally evaluated using bulk
properties at the mean of inlet and outlet temperatures; for heating and
cooling of liquids the viscosity ratio corrects the property variation; and
the exponent for liquid heating and cooling is **usually set to `m=0.14`**.
It also distinguishes gas cooling and gas heating rules. That wording binds a
source rule/observation, not a universal value for every liquid or every Bell
variant.

In §3.4.7, printed pp.3-12--3-13, Eqs. (3.4.25)--(3.4.27), the ideal tube-bank
coefficient is represented as `alpha_I=j_I*c_p*G*Pr^(-2/3)`, with the `a1--a4`
table in Table 3.1 attributed to Taborek (1983). The chapter therefore
supports the same separation of ideal coefficient and `J_mu` seen in Jamil,
but it does not, in the acquired access form, supply a TASK172-approved
wall-temperature producer or a complete transfer domain for the active factor.

```text
THOME_JMU_EQUATION_BOUND=true
THOME_JMU_EXPONENT_RULE=LIQUID_HEATING_AND_COOLING_USUALLY_m_0.14_NOT_UNIVERSAL
THOME_BULK_PROPERTY_RULE=MEAN_INLET_OUTLET_BULK_TEMPERATURE
THOME_WALL_RULE=WALL_VISCOSITY_REQUIRES_WALL_TEMPERATURE_FROM_PRELIMINARY_HEAT_TRANSFER
THOME_IDEAL_BANK_FORM=alpha_I=j_I*cp*G*Pr^(-2/3)
THOME_COEFFICIENT_TABLE=Table_3.1_attributed_to_Taborek_1983
```

The `m=0.14` statement is not imported from Bell 1960. Bell 1960 remains a
separate source variant and cannot supply the Jamil/Thome exponent by
numerical coincidence.

### 3.3 Gonçalves supporting information

The official Wiley record confirms the supporting-information filename
`aic16602-sup-0001-Supinfo.docx` and describes Table S2 as the ideal-tube-bank
Bell--Delaware parameter table. The official download endpoint returned HTTP
403 during this acquisition attempt. The SI body and its table were therefore
not claimed.

```text
GONCALVES_SUPPORTING_INFORMATION_ACQUIRED=false
GONCALVES_JMU_PRESENT=undetermined
GONCALVES_COEFFICIENT_PROVENANCE_BOUND=false
```

The current TASK166 equation and its source identities remain unchanged.

## 4. Jamil/Thome transfer-contract matrix

The following status is deliberately split between a source-defined
observation and a TASK172-to-TASK166 transfer permission.

| Transfer field | Source observation | TASK172 transfer status | Evidence boundary |
| --- | --- | --- | --- |
| Equation | Jamil Eq. (6), Table A.2; Thome Eq. (3.4.23) | `JMU_EQUATION_BOUND=true` | Exact symbolic form is bound; no implementation is authorized. |
| Exponent | Thome says liquid heating/cooling exponent is usually `m=0.14` | `JMU_EXPONENT_BOUND=true` | Source rule is not a universal or silently fixed production preset. |
| Ratio | `mu/mu_wall` | `JMU_BULK_VISCOSITY_DEFINITION_BOUND=true` and `JMU_WALL_VISCOSITY_DEFINITION_BOUND=true` | State locations remain separately mapped below. |
| Bulk state | Mean inlet/outlet bulk properties in Thome | `TASK032_BULK_STATE_MAPPING_VALID=false` | No proof that TASK032's local state has the same semantics. |
| Wall state | Wall viscosity evaluated from wall temperature | `JMU_WALL_TEMPERATURE_DEFINITION_BOUND=true` | Source does not bind a TASK172 wall-interface producer. |
| Wall producer | Preliminary heat-transfer calculation is required | `JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false` | Producer authority is unresolved. |
| Heating branch | Explicit liquid heating statement | `HEATING_COOLING_SCOPE_BOUND=true`; `HEATING_BRANCH_BOUND=true` | Source scope only; no TASK166 transfer approval. |
| Cooling branch | Explicit liquid cooling statement | `COOLING_BRANCH_BOUND=true` | Source scope only; no TASK166 transfer approval. |
| Fluid scope | Liquids use viscosity ratio; gases have separate rules | `FLUID_SCOPE_BOUND=true` | TASK172 initial production scope still requires narrower, reviewed mapping. |
| Re domain | No explicit J_mu-specific interval acquired | `RE_DOMAIN_BOUND=false` | TASK166 `0<Re_s<=100000` is not reused. |
| Pr domain | No explicit J_mu-specific interval acquired | `PR_DOMAIN_BOUND=false` | No silent inheritance from the ideal-bank equation. |
| Viscosity-ratio domain | No explicit bound acquired | `VISCOSITY_RATIO_DOMAIN_BOUND=false` | No extrapolation permission. |
| Geometry/layout | Chapter context and Table 3.1 do not prove current exact mapping | `GEOMETRY_LAYOUT_DOMAIN_BOUND=false` | No TASK166 geometry transfer permission. |
| Combination | Jamil places `J_mu` separately after `h_c` | `COMBINATION_RULE_BOUND=true` | `J_mu` remains separate from `j_i`; active production placement is not authorized. |

The source-defined facts are enough to identify the intended Jamil/Thome
route, but not enough to create a transferable production authority candidate.

## 5. State mapping

### 5.1 Bulk state

The source meaning is a bulk-property evaluation at the mean of inlet and
outlet temperatures, not automatically a TASK032 local shell-bulk state. The
following mappings are therefore explicit:

```text
JMU_BULK_VISCOSITY_DEFINITION_BOUND=true
JMU_BULK_TEMPERATURE_DEFINITION=MEAN_INLET_OUTLET_BULK_TEMPERATURE
TASK032_BULK_STATE_MAPPING_VALID=false
TASK032_BULK_STATE_MAPPING_REASON=TASK032_LOCAL_STATE_SEMANTIC_EQUIVALENCE_TO_SOURCE_MEAN_BULK_NOT_PROVEN
```

No inlet/outlet averaging is added to TASK032, and no local property producer
is introduced here.

### 5.2 Wall state

The source names the viscosity at the heat-transfer wall and says that wall
temperature must be calculated from a preliminary heat-transfer calculation.
That is not sufficient to identify the producer or to prove that a metal
outer-surface temperature equals the TASK172 shell-fluid wall-interface
state. No TASK034 pressure-drop state, tube-side state, arithmetic mean, or
neutral factor is substituted.

```text
JMU_WALL_VISCOSITY_DEFINITION_BOUND=true
JMU_WALL_TEMPERATURE_DEFINITION_BOUND=true
JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false
TASK172_WALL_STATE=SHELL_FLUID_WALL_INTERFACE
TASK172_WALL_STATE_MAPPING_VALID=false
TASK172_STATE_MAPPING_REASON=SOURCE_WALL_TEMPERATURE_HAS_NO_REVIEWED_TASK172_INTERFACE_PRODUCER_OR_FLUID_SIDE_MAPPING
```

The wall-temperature producer and any coupled iteration remain a later
authority task. This record does not implement or approve either one.

## 6. Applicability and combination boundary

The native evaluator's `0<Re_s<=100000` is not promoted to the J_mu validity
domain. The acquired chapter does not bind a complete Reynolds, Prandtl,
viscosity-ratio, or temperature domain for the factor. It also does not prove
that the exact current TASK166 geometry/layout and correction-factor chain
are a transferable combination. Accordingly:

```text
RE_DOMAIN_BOUND=false
PR_DOMAIN_BOUND=false
VISCOSITY_RATIO_DOMAIN_BOUND=false
FLUID_SCOPE_BOUND=true
HEATING_COOLING_SCOPE_BOUND=true
GEOMETRY_LAYOUT_DOMAIN_BOUND=false
TASK166_GEOMETRY_TRANSFER_COMPATIBLE=false
COMBINATION_RULE_BOUND=true
JMU_COMBINATION_POSITION=SEPARATE_JMU_MULTIPLIER_AFTER_HC_WITH_JC_JL_JB_JS_JR
JMU_IS_SEPARATE_FROM_JI=true
```

`COMBINATION_RULE_BOUND=true` means the source-level product position is
identified. It does not mean the factor is permitted to be inserted into the
TASK166 production equation. No `J_mu` term is added to TASK166.

## 7. Lineage and forbidden transfers

```text
BELL_1960_FACTOR_TRANSFER_TO_NATIVE_JAMIL_VARIANT=false
TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
SECONDARY_TABOREK_TRANSFER_TO_TASK166=false
```

The Thome chapter's `m=0.14` wording is not Bell-1960 exponent transfer. It
is a source observation attached to the Jamil/Thome route and remains subject
to independent source-rights, applicability, state, and production review.

## 8. Decision

The equation and source rule are identified, but the transfer contract is not
complete. The smallest unresolved authority set is:

```text
RESULT=BLOCKED
ACQUISITION_OUTCOME=OUTCOME_B_EQUATION_AND_SOURCE_RULES_OBSERVED_TRANSFER_CONTRACT_INCOMPLETE
JAMIL_JMU_SYMBOLIC_FORM_BOUND=true
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_TRANSFER_AUTHORITY_CANDIDATE_CREATED=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

The remaining gaps are the TASK172 wall-temperature producer and source-to-
TASK032 state mapping, complete J_mu applicability domains, exact TASK166
geometry/method transferability, and an independently reviewable rights/body
chain for the cited Thome edition. The symbolic equation and the source's
`m=0.14` wording do not close those gaps.

```text
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_STATE_DOMAIN_TRANSFER_CONTRACT_R1_ONLY
```

## 9. Governance and validation boundary

No lifecycle promotion, implementation, production equation, numerical
preset, dependency, or historical-record rewrite is performed. Jamil's
existing reviewed identity, the preceding native coefficient-lineage record,
and all forbidden-transfer dispositions remain unchanged.

```text
SOURCE_ACQUISITION_AND_TRANSFER_REVIEW_ONLY=true
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
HISTORICAL_RECORDS_REWRITTEN=false
TASK166_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
BLOCKER_REMOVED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The companion machine evidence and append-only registry extension carry the
source hashes, exact locations, acquisition rights, transfer statuses, and
final canonical hashes. Validation and exact-head CI are reported there after
the final content freeze.
