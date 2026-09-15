# TASK172 R1 — Jamil/Thome `J_mu` state, domain and transfer contract

## 1. Receipt and scope boundary

This append-only package records the state/domain/transfer audit for the
active shell-side wall-viscosity factor in the TASK166-native Jamil
operational representation. It does not implement `J_mu`, modify TASK166,
select a material or property profile, choose a wall-temperature algorithm,
start numerical qualification, or promote the acquired Thome copy to
production authority.

```text
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_STATE_DOMAIN_TRANSFER_CONTRACT_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=6de453f73c4c6a0944b3fc960ba4c2011df6d1c9
MODE=JMU_STATE_DOMAIN_TRANSFER_CONTRACT_ONLY
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

The preceding coefficient-lineage decision remains unchanged. It established
that the native TASK166/Jamil operational variant has a separate symbolic
`J_mu` position, while Bell 1960's normalized-`j` factor is not transferable
to that native variant. This package answers the next question: whether the
source-defined bulk/wall states and domains can be mapped to the TASK172
state model without inventing semantics.

## 2. Source rule versus transfer authority

The effective source observations are deliberately split from permission to
use them in TASK172:

| Item | Source-rule observation | TASK172 transfer disposition |
| --- | --- | --- |
| Jamil Eq. (6), Table A.2 | `J_mu` is a separate factor in `h_s=h_c J_C J_L J_B J_S J_R J_mu` | Symbolic equation is identified; executable transfer is not authorized |
| Jamil Eq. (7) | `h_c=j_i c_p G Pr^(-2/3)` | Existing native ideal coefficient remains unchanged |
| Thome Eq. (3.4.23) | `J_mu=(mu/mu_wall)^m` | Source form is identified; no production factor is added |
| Thome liquid branch | Liquid heating/cooling usually uses `m=0.14` | A source rule, not an always-`0.14` preset |
| Thome bulk rule | Bulk properties at the mean of inlet and outlet temperatures | Not mapped to the TASK032 single-bulk snapshot |
| Thome wall rule | `mu_wall` requires a wall temperature from preliminary heat transfer | No reviewed TASK172 producer is bound |

The Jamil accepted manuscript is the direct source for the operational
placement. The acquired Thome Chapter 3 copy is retained only as a relevant
chapter cross-check because its rights and exact-edition chain are not
verified. A readable source body, a source observation, and a production
transfer authority are different lifecycle states.

## 3. Exact source identities and locations

### 3.1 Jamil

```text
JAMIL_SOURCE_ID=SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS
JAMIL_BODY_ACQUIRED=true
JAMIL_BODY_SHA256=a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970
JAMIL_ACCESS_PATH=https://nrl.northumbria.ac.uk/45157/1/sthx.pdf
JAMIL_EXACT_LOCATIONS=§2.2.2_PDF_p11_Eq6;§2.2.2_PDF_p11_Eq7;Appendix_p57_Table_A1;Appendix_pp58-59_Table_A2;References_p50_printed_p51_Ref9
JMU_EQUATION_SOURCE_RULE_BOUND=true
JMU_EQUATION_TRANSFER_AUTHORITY_BOUND=false
JAMIL_SHELL_HTC_FORM=hs=hc*JC*JL*JB*JS*JR*Jmu
JAMIL_IDEAL_HTC_FORM=hc=ji*cp*G*Pr^(-2/3)
JAMIL_JMU_FORM=Jmu=(mu/mu_wall)^m
JAMIL_JMU_POSITION=SEPARATE_FACTOR_AFTER_HC_ALONGSIDE_JC_JL_JB_JS_JR
JAMIL_JMU_SOURCE_REFERENCE=Jamil_Ref_9_Thome_Engineering_Data_Book_III_2004
```

Jamil's accepted body contains the symbol `m` but does not provide an
executable numeric exponent in the accepted manuscript. It therefore cannot
by itself authorize a fixed exponent, a wall-temperature producer, or a
TASK166 transfer.

### 3.2 Thome relevant chapter

```text
THOME_SOURCE_ID=THOME-2004-EDB3-CH3-CROSSCHECK
THOME_BODY_ACQUIRED=true
THOME_BODY_COMPLETE=true
THOME_BODY_SCOPE=RELEVANT_CHAPTER_COMPLETE_FOR_SECTIONS_3.4.6_AND_3.4.7
THOME_EDITION_IDENTITY_BOUND=true
THOME_EDITION_IDENTITY_SCOPE=RELEVANT_CHAPTER_CONTENT_ONLY
THOME_BYTES_SHA256=326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4
THOME_ACCESS_PATH=https://files.engineering.com/files/e01daa74-5d7f-4923-a8fc-fa05132408b2/WOLVERINE_Single_Phase_Shell-Side_Flow_and_Heat_Transfer.pdf
THOME_OFFICIAL_CATALOG_PATH=https://pennwellbooks.com/products/heat-transfer-engineering-data-iii-ebook
THOME_RIGHTS_STATUS=COPY_RESTRICTED_RIGHTS_UNVERIFIED
THOME_AUTHORITY_STATUS=NOT_PROMOTED_PENDING_RIGHTS_AND_INDEPENDENT_REVIEW
THOME_SOURCE_ROLE=ACQUIRED_RELEVANT_CHAPTER_CROSS_CHECK_ONLY
THOME_EXACT_LOCATIONS=§3.4.6_printed_p3-12_Eq3.4.23;§3.4.6_liquid_paragraph;§3.4.7_printed_pp3-12-3-13_Eqs3.4.25-3.4.27;Table_3.1_printed_p3-13
```

The chapter observations are:

* §3.4.6 Eq. (3.4.23) gives `J_mu=(mu/mu_wall)^m`.
* The liquid heating/cooling paragraph says the exponent is usually set to
  `m=0.14`; “usually” is retained and is not converted into a universal
  rule.
* The chapter states that correlations normally use bulk properties at the
  mean of inlet and outlet temperatures.
* The wall viscosity is evaluated at a wall temperature obtained from a
  preliminary heat-transfer calculation.
* Gas heating/cooling uses different source rules and is not admitted by the
  initial TASK172 liquid scope.
* §3.4.7 gives the ideal-bank form `alpha_I=j_I c_p G Pr^(-2/3)` and
  attributes Table 3.1 to Taborek; this does not supply the missing transfer
  identity or domain for TASK166.

These are source observations only. They are not a source promotion or a
license grant.

## 4. Bulk-state contract

### 4.1 Required source state

```text
SOURCE_BULK_TEMPERATURE_DEFINITION=MEAN_OF_SOURCE_STREAM_INLET_AND_OUTLET_BULK_TEMPERATURES
SOURCE_BULK_PROPERTY_DEFINITION=PHYSICAL_PROPERTIES_EVALUATED_AT_SOURCE_MEAN_BULK_FLUID_TEMPERATURE
SOURCE_BULK_VISCOSITY_DEFINITION=MU_AT_SOURCE_MEAN_INLET_OUTLET_BULK_TEMPERATURE
```

This is a mean stream state for the source shell coefficient. It is not,
without an additional rule, a local numerical-cell state, an inlet state, an
outlet state, or an arithmetic average of two unrelated cell values.

### 4.2 TASK032 comparison

```text
TASK032_BULK_STATE_ID=task032.shell-side-flow-state.v1::PROPERTY_SNAPSHOT::BULK_SHELL_SIDE_STATE
TASK032_BULK_STATE_SEMANTICS=SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING
TASK032_BULK_STATE_FIELDS=bulk_temperature_k;bulk_pressure_pa;rho;mu;cp;k;property_source_id;property_source_version
SOURCE_TO_TASK032_BULK_MAPPING_BOUND=false
SOURCE_TO_TASK032_BULK_MAPPING_RULE=REQUIRES_EXPLICIT_CASE_LEVEL_MEAN_INLET_OUTLET_BINDING_BEFORE_TASK032_REUSE
SOURCE_TO_TASK032_BULK_MAPPING_ERROR_OR_LIMITATION=TASK032_CONTRACT_HAS_ONE_BULK_SNAPSHOT_AND_NO_SOURCE_BOUND_INLET_OUTLET_PAIR_OR_MEAN_STATE_SEMANTICS
TASK032_BULK_STATE_MAPPING_VALID=false
```

TASK032 owns a deterministic single bulk-property snapshot and does not
reevaluate properties. Its `bulk_temperature_k` field is not enough to prove
that the value is the source mean of inlet and outlet temperatures. No
averaging, local-to-global substitution, or hidden property call is added by
this package. A future case-level binding may establish that equivalence, but
it is a separate authority edge.

## 5. Jμ application granularity

The acquired source describes a mean shell coefficient for the tube bundle.
The numerical architecture in TASK171 has physical intervals and numerical
cells, but that architecture does not authorize localizing an empirical
whole-bundle correction.

```text
JMU_SOURCE_APPLICATION_GRANULARITY=WHOLE_EXCHANGER_MEAN_TUBE_BUNDLE_SOURCE_OBSERVATION
JMU_APPLICATION_GRANULARITY_BOUND=false
LOCALIZATION_TRANSFER_AUTHORITY_BOUND=false
JMU_CELLWISE_REAPPLICATION_AUTHORIZED=false
WHOLE_EXCHANGER_FACTOR_DIVIDED_OR_REPEATED_BY_CELL_COUNT=false
```

The `false` status is deliberate: the source granularity is observed, but no
transfer rule selects a whole-exchanger, segment, or cell application for the
TASK172 segmented model. In particular, a cell-local `J_mu` must not be
created merely because the future solver has local states.

## 6. Wall-temperature and surface contract

### 6.1 Source requirement

The source requirement is only a wall-temperature-dependent fluid viscosity
at the heat-transfer surface. The acquired text does not bind whether the
temperature used for `mu_wall` is a shell-fluid wall/interface temperature,
the tube-metal outer surface temperature, a film temperature, or another
explicit node.

```text
JMU_WALL_VISCOSITY_DEFINITION_BOUND=true
JMU_REQUIRED_WALL_SURFACE_IDENTITY_BOUND=false
JMU_REQUIRED_WALL_SURFACE_IDENTITY=SOURCE_HEAT_TRANSFER_SURFACE_WALL_TEMPERATURE;FLUID_SIDE_VS_METAL_SURFACE_NOT_EXPLICITLY_BOUND
JMU_WALL_TEMPERATURE_DEFINITION_BOUND=true
JMU_WALL_TEMPERATURE_DEFINITION=SOURCE_WALL_TEMPERATURE_USED_TO_EVALUATE_MU_WALL
```

The source concept is therefore narrower than the TASK172 physical-surface
taxonomy. A metal outer-surface value cannot be silently renamed to a
shell-fluid wall-interface value, and a shell bulk or arithmetic wall mean
cannot be substituted.

### 6.2 Candidate repository producer audit

| Candidate | What it supplies | Status for Jμ |
| --- | --- | --- |
| `V07-T172-WALL-TEMPERATURE-STATE-R1` / `V07-T172-CLEAN-RADIAL-WALL-STATE-R1` | Proposed two-surface identity and algebraic clean radial network; supplied bulk states, films, `k_wall`, geometry and signed heat rate | Not a reviewed executable producer; no Jμ source-state mapping |
| TASK037 cylindrical wall authority | Existing area/resistance semantics | Does not provide a two-surface solved state or Jμ correction |
| TASK034 wall-property state | Pressure-drop authority only | Explicitly forbidden transfer |
| Caller-provided `wall_temperature` | Unverified observation unless fully identified | Cannot become a computed authority |

```text
CANDIDATE_WALL_PRODUCER_ID=V07-T172-WALL-TEMPERATURE-STATE-R1
PHYSICAL_SURFACE=TUBE_METAL_OUTER_SURFACE_WITH_CLEAN_PROFILE_ALIAS_TO_SHELL_FLUID_WALL_INTERFACE
TEMPERATURE_DEFINITION=LOCAL_TWO_SURFACE_CLEAN_RADIAL_STATE_CONTRACT_NOT_SOLVED_RUNTIME_STATE
INPUT_STATES=LOCATED_TUBE_BULK;LOCATED_SHELL_BULK;QUALIFIED_FILMS;QUALIFIED_K_WALL;SIGNED_LOCAL_HEAT_RATE;NATIVE_GEOMETRY
THERMAL_RESISTANCES_INCLUDED=TUBE_FILM;CYLINDRICAL_METAL_CONDUCTION;SHELL_FILM
ITERATIVE_OR_EXPLICIT=ALGEBRAIC_CONTRACT_ONLY;PRODUCER_NOT_IMPLEMENTED_OR_NUMERICALLY_AUTHORIZED
SOURCE_AUTHORITY=V07-T172-WALL-TEMPERATURE-STATE-R1_AND_V07-T172-CLEAN-WALL-SURFACE-NETWORK-R2
COMPATIBLE_WITH_JMU_SOURCE_STATE=false
JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false
TASK172_WALL_STATE_MAPPING_VALID=false
TASK172_WALL_STATE_MAPPING_REASON=SOURCE_REQUIRES_UNSPECIFIED_HEAT_TRANSFER_SURFACE_STATE_AND_EXISTING_TASK172_PRODUCER_IS_PROPOSED_NOT_EXECUTABLE_OR_INDEPENDENTLY_MAPPED
REQUIRED_WALL_PRODUCER_CONTRACT=SOURCE_IDENTIFIED_FLUID_SIDE_SURFACE;LOCATED_BULK_STATE;QUALIFIED_FILMS_AND_MATERIAL;SIGNED_HEAT_RATE;PHYSICAL_SUPPORT;EXPLICIT_STATE_IDENTITY;SOURCE_BOUND_PROPERTY_EVALUATION;INDEPENDENT_REVIEW;FAIL_CLOSED_DOMAIN_AND_COUPLING_RULE
```

The clean alias from the earlier wall-state contract is conditional on
clean-surface service. It does not by itself establish that the source's
`mu_wall` is evaluated at that alias, nor does it create a solved value.

### 6.3 Coupling circularity

For an active correction the dependency is potentially circular:

```text
J_mu → h_shell → wall state → mu_wall → J_mu
```

```text
JMU_WALL_COUPLING_CIRCULARITY_PRESENT=true
JMU_WALL_COUPLING_CLOSURE_AUTHORITY_BOUND=false
```

No fixed-point iteration, wall-temperature iteration count, relaxation,
residual threshold, or last-iterate acceptance is introduced. A future
producer must be separately authorized to close this cycle.

## 7. Heating/cooling direction and fluid scope

```text
SOURCE_HEATING_DEFINITION=SOURCE_LIQUID_HEATING_BRANCH_NAMED_BY_ACQUIRED_THOME_TEXT;EXACT_TASK172_LOCAL_DIRECTION_PREDICATE_NOT_BOUND
SOURCE_COOLING_DEFINITION=SOURCE_LIQUID_COOLING_BRANCH_NAMED_BY_ACQUIRED_THOME_TEXT;EXACT_TASK172_LOCAL_DIRECTION_PREDICATE_NOT_BOUND
JMU_EXPONENT_SOURCE_RULE_BOUND=true
JMU_EXPONENT_SOURCE_RULE=LIQUID_HEATING_AND_COOLING_USUALLY_M_0.14
JMU_EXPONENT_TRANSFER_AUTHORITY_BOUND=false
JMU_EXPONENT_TRANSFER_LIMITATION=USUALLY_DOES_NOT_DEFINE_EXCEPTION_SET_OR_TASK172_SELECTION_RULE
HEATING_COOLING_SOURCE_RULE_BOUND=true
HEATING_COOLING_TRANSFER_AUTHORITY_BOUND=false
TASK172_HEATING_COOLING_DIRECTION_MAPPING_BOUND=false
TASK172_HEATING_COOLING_DIRECTION_RULE=REQUIRES_SOURCE_QUALIFIED_DIRECTION_FROM_SIGNED_PHYSICAL_HEAT_FLOW_AND_LOCATED_SHELL_STATES;NO_LOCAL_CROSSING_OR_REVERSAL_RULE_BOUND
```

The initial target is the already reviewed narrow water profile, not every
fluid covered by a handbook chapter:

```text
TASK172_TARGET_FLUID_CLASS=PURE_ORDINARY_WATER_STABLE_SINGLE_PHASE_LIQUID_ONLY
FLUID_SCOPE_SOURCE_RULE_BOUND=true
FLUID_SCOPE_TRANSFER_AUTHORITY_BOUND=false
LIQUID_JMU_RULE_APPLICABLE=SOURCE_CLASS_OBSERVATION_ONLY
GAS_RULE_IN_SCOPE=false
```

Gas branches, two-phase behavior, non-Newtonian behavior, and unregistered
fluids remain outside this transfer contract.

## 8. Jμ-specific domain review

The acquired source observations do not provide a complete executable domain
for the active factor. Domains from `j_i`, TASK166, pressure drop, or another
correction factor are not inherited.

| Domain | Source status | TASK172 disposition |
| --- | --- | --- |
| Reynolds number | `NOT_SPECIFIED_BY_ACQUIRED_SOURCE` for Jμ-specific validity | `JMU_RE_DOMAIN_SOURCE_BOUND=false` |
| Prandtl number | `NOT_SPECIFIED_BY_ACQUIRED_SOURCE` for Jμ-specific validity | `JMU_PR_DOMAIN_SOURCE_BOUND=false` |
| Viscosity ratio | `NOT_SPECIFIED_BY_ACQUIRED_SOURCE` | `JMU_VISCOSITY_RATIO_DOMAIN_SOURCE_BOUND=false` |
| Temperature | `NOT_SPECIFIED_BY_ACQUIRED_SOURCE` as a Jμ-specific bound | `JMU_TEMPERATURE_DOMAIN_SOURCE_BOUND=false` |
| Fluid family | Liquid/gas branches are distinguished | Source bound, TASK172 transfer not bound |
| Heating/cooling | Liquid branches are named; local rule incomplete | Source bound, TASK172 transfer not bound |

```text
JMU_RE_DOMAIN_SOURCE_BOUND=false
JMU_RE_DOMAIN_SOURCE=NOT_SPECIFIED_BY_ACQUIRED_SOURCE
JMU_PR_DOMAIN_SOURCE_BOUND=false
JMU_PR_DOMAIN_SOURCE=NOT_SPECIFIED_BY_ACQUIRED_SOURCE
JMU_VISCOSITY_RATIO_DOMAIN_SOURCE_BOUND=false
JMU_VISCOSITY_RATIO_DOMAIN_SOURCE=NOT_SPECIFIED_BY_ACQUIRED_SOURCE
JMU_TEMPERATURE_DOMAIN_SOURCE_BOUND=false
JMU_TEMPERATURE_DOMAIN_SOURCE=NOT_SPECIFIED_BY_ACQUIRED_SOURCE
```

TASK166's `0<Re_s<=100000` remains the native evaluator domain. It is not
promoted to a Jμ domain, and no extrapolation permission is created.

## 9. Geometry and method transfer

The source chapter context is narrower than a generic “Bell–Delaware” label:

```text
TASK166_SOURCE_GEOMETRY_IDENTITY=TASK166_TEMA_E_SINGLE_SEGMENTAL_BAFFLE_BELL_DELAWARE_LAYOUT_30_45_90_ONE_SHELL_PASS_NATIVE_SCOPE_WITH_FIXED_TUBESHEET_UTUBE_FLOATING_HEAD_APPLICABILITY
JMU_SOURCE_GEOMETRY_IDENTITY=THOME_TABOREK_DELAWARE_SINGLE_PHASE_SHELL_SIDE_SINGLE_SEGMENTAL_BAFFLE_PRIMARILY_TEMA_E_SPECIFIED_TUBE_LAYOUT_CONTEXT
GEOMETRY_SCOPE_SOURCE_RULE_BOUND=true
GEOMETRY_SCOPE_TRANSFER_AUTHORITY_BOUND=false
TASK166_GEOMETRY_TRANSFER_COMPATIBLE=false
```

| Field | TASK166 | Acquired Jμ source | Transfer result |
| --- | --- | --- | --- |
| Shell family | TEMA E | Primarily TEMA E in chapter context | Exact identity not bound |
| Baffle family | Single segmental | Single-segmental chapter context | Potentially aligned, not source-transfer proof |
| Tube layout | 30°, 45°, 90° native rows | Specified layouts in source context | Exact row/table identity not bound for Jμ |
| Shell passes | One native shell pass | Not separately bound by the acquired Jμ extract | Unresolved |
| Construction family | Fixed-tubesheet, U-tube, floating-head applicability | No matching construction-family authority for Jμ | Unresolved; no U-tube/floating-head transfer |
| Flow regime | Single-phase Newtonian native envelope | Single-phase shell-side chapter context | Not a complete Jμ domain |
| Surface/roughness assumptions | Native geometry/source contracts | Not completely bound for Jμ | Unresolved |

The source and TASK166 may share terminology and some context, but the
field-by-field transfer is not established. No Jμ factor is merged into `j_i`
or multiplied into the native correction chain.

## 10. Rights and lifecycle

```text
THOME_SOURCE_IDENTITY_CONFIDENCE=RELEVANT_CHAPTER_CONTENT_IDENTITY_BOUND;EXACT_CITED_2004_EDITION_CHAIN_NOT_FULLY_PROVEN
THOME_RIGHTS_REVIEW_COMPLETE=false
THOME_INDEPENDENT_AUTHORITY_REVIEW_COMPLETE=false
THOME_PRODUCTION_AUTHORITY_PROMOTED=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

The official catalog is used only to corroborate book/chapter identity. The
acquired copy is not vendored and is not promoted from cross-check evidence.
The Jamil/Thome route therefore still needs an independently reviewable
rights/source lifecycle decision before production use.

## 11. Combination semantics

The source-level combination position is identified:

```text
COMBINATION_RULE_SOURCE_BOUND=true
COMBINATION_RULE_TRANSFER_AUTHORITY_BOUND=false
JMU_COMBINATION_POSITION=SEPARATE_JMU_MULTIPLIER_AFTER_HC_WITH_JC_JL_JB_JS_JR
JMU_SEPARATE_FROM_JI=true
```

This does not authorize the following production expression:

```text
h_shell = h_ideal * Jc * Jl * Jb * Js * Jr * J_mu
```

until state, domain, geometry, rights and coupling authority are separately
reviewed. In particular, Jμ is not Bell 1960's normalized-`j` reconstruction,
not a new geometry factor, and not a TASK034 pressure-drop term.

## 12. Decision and remaining blockers

The source equation and several source rules are identifiable, but the
transfer contract is incomplete. The result is a correct fail-closed block:

```text
RESULT=BLOCKED
ACQUISITION_OUTCOME=OUTCOME_B_STATE_DOMAIN_TRANSFER_CONTRACT_INCOMPLETE_WITH_WALL_CLOSURE_DEPENDENCY
JMU_EQUATION_SOURCE_RULE_BOUND=true
JMU_EQUATION_TRANSFER_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_TRANSFER_AUTHORITY_CANDIDATE_CREATED=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

The smallest unresolved authority set is:

```text
JMU_WALL_TEMPERATURE_PRODUCER
JMU_REQUIRED_WALL_SURFACE_IDENTITY_AND_FLUID_SIDE_MAPPING
SOURCE_TO_TASK032_BULK_STATE_MAPPING
JMU_APPLICATION_GRANULARITY_AND_LOCALIZATION_RULE
JMU_RE_DOMAIN
JMU_PR_DOMAIN
JMU_VISCOSITY_RATIO_DOMAIN
JMU_TEMPERATURE_DOMAIN
TASK166_GEOMETRY_AND_METHOD_TRANSFERABILITY
THOME_RIGHTS_AND_INDEPENDENT_AUTHORITY_REVIEW
JMU_WALL_COUPLING_CLOSURE_AUTHORITY
```

The canonical TASK172 entry ledger is unchanged:

```text
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The next gate is intentionally targeted at the missing physical state
producer and bulk-state mapping. It does not authorize iteration or
implementation:

```text
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_WALL_PRODUCER_AND_STATE_MAPPING_AUTHORITY_R1_ONLY
```

## 13. Forbidden transfers and governance

```text
BELL_1960_FACTOR_TRANSFER_TO_NATIVE_JAMIL_VARIANT=false
TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
SECONDARY_TABOREK_TRANSFER_TO_TASK166=false
JMU_MERGED_INTO_JI=false
EQUAL_EXPONENT_TRANSFER=false
```

This package performs no lifecycle promotion, material selection, case
qualification, formula change, property backend change, wall correction,
solver work, numerical qualification, dependency change, or historical
record rewrite.

```text
SOURCE_RULE_OBSERVATIONS_ONLY=true
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
HISTORICAL_RECORDS_REWRITTEN=false
ENGINEERING_RULES_CHANGED=false
TASK166_CHANGED=false
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

The companion evidence and registry extension carry the machine-readable
state split, source hashes, missing-authority list and canonical hashes.
