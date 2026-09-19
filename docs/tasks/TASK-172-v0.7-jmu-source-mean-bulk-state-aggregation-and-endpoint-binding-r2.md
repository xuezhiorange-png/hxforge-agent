# TASK-172 v0.7 — J_mu source-mean bulk state aggregation and shell endpoint binding R2

## Receipt

```text
TASK_ID=TASK172_V0_7_JMU_SOURCE_MEAN_BULK_STATE_AGGREGATION_AND_SHELL_INLET_OUTLET_STATE_BINDING_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=1d63118362214379359e0436bd3c15988d200d87
MODE=TARGETED_SOURCE_ACQUISITION_AND_TRANSFER_ADJUDICATION_ONLY
```

This record audits only the source-mean bulk-fluid state consumed by the
native TASK166/Jamil/Thome shell-side `J_mu` lineage.  It does not implement
`J_mu`, call a property backend, create a case, or promote a shell-wall
correction authority.

## 1. Accepted source and endpoint boundaries

The accepted source observation remains:

```text
JMU_BULK_STATE_SOURCE_ID=THOME-2004-EDB3-CH3-CROSSCHECK
JMU_BULK_STATE_SOURCE_RULE_BOUND=true
JMU_BULK_STATE_STREAM_ROLE=SHELL_SIDE_FLUID
JMU_SOURCE_BULK_STATE_GRANULARITY=WHOLE_EXCHANGER_SHELL_STREAM_MEAN_OF_SOURCE_INLET_AND_OUTLET_BULK_STATE
```

The Thome chapter says that bulk properties are evaluated at the mean of the
inlet and outlet bulk temperatures.  In the acquired chapter copy, the word
`mean` is not itself defined as arithmetic, mass-weighted, enthalpy-equivalent,
logarithmic, or another operator.  The accepted endpoint contract is reused:

```text
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
SOURCE_MEAN_USES_REVIEWED_ENDPOINT_PAIR_CONTRACT=true
```

The endpoint contract is an admission shape, not an endpoint producer.  No
case-bound inlet, outlet, pair, or property snapshot exists in this gate.

## 2. Targeted source acquisition

| Source ID | Title / edition | Source role | Exact location | Body / rights status | Transfer scope | Conflict status |
| --- | --- | --- | --- | --- | --- | --- |
| `THOME-2004-EDB3-CH3-CROSSCHECK` | *Engineering Data Book III*, Chapter 3, *Single-Phase Shell-Side Flows and Heat Transfer*; acquired chapter copy identified as relevant to the cited 2004 lineage | Recognized engineering reference; direct J_mu cross-check | §3.4.6 printed p.3-12, Eq.3.4.23 and liquid heating/cooling paragraph; §3.4.7 printed pp.3-12–3-13 | Body acquired and complete for the relevant chapter; SHA-256 `326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4`; copy-restricted rights unverified; review-only | Native J_mu source observation; mean wording and wall-viscosity dependency | No source conflict; operator and pressure remain incomplete in this body |
| `ASME-PTC-12.5-2000-R2025-CATALOG` | ASME PTC 12.5 — Single Phase Heat Exchangers, official catalog entry, 2000 (R2025) | Primary normative test-code identity | Official ASME product page and catalog description | Official body not acquired; purchase/copyright boundary retained; no body hash | Edition identity and method-context cross-check only | No conflict |
| `ASME-PTC-12.5-2000-R2015-PUBLIC-COPY` | ASME PTC 12.5-2000, public copy labeled 2015 | Primary test-code text as observed through a public copy; not a native Jamil/Thome authority | Appendix C, §C.4, printed p.58: arithmetic-mean shell-side bulk temperature for bulk-property evaluation | Relevant public preview body acquired as a 30-page PDF, SHA-256 `bc258206e9d247adb405821b49384ca243f28013ad85fa102caba4218565a071`; relevant full-text passage also inspected in a public text mirror; rights unverified and body not vendored | Temperature-operator transfer only; no pressure pairing, test uncertainty, or PTC method transfer | No temperature conflict; pressure remains unresolved |
| `SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE` | Gonçalves, Costa & Bagajewicz, *Linear method for the design of shell and tube heat exchangers using the Bell–Delaware method*, AIChE Journal 65(8), e16602 (2019) | Primary TASK166 implementation equation authority | §2.1 Eqs.36–39, §2.2 Eqs.75–77 as mapped by TASK166 | Body acquired; SHA-256 `fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54`; copyright retained; not vendored | Bell–Delaware equation lineage and method-context compatibility audit; no source-mean operator or pressure rule found | No conflict; no new operator authority |
| `SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS` | Jamil et al., *Exergoeconomic optimization of a shell-and-tube heat exchanger*, ECM 226, 113462 (2020) | Direct native Jamil operational representation for parameter rows and J_mu placement | §2.2.2 PDF p.11 Eqs.6–9; Appendix Tables A.1–A.2, pp.57–59 | Accepted manuscript acquired; SHA-256 `a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970`; CC-BY-NC-ND boundary retained | Native J_mu formulation; source points to Thome for property-state rule | No conflict; pressure rule not supplied |
| `BELL-1960-DELAWARE-DESIGN` | K. J. Bell, *Exchanger Design Based on the Delaware Research Program* (1960) | Historical Bell/Delaware variant observation | Acquired printed pp.C-26–C-36 and C-40a–C-40c | Body acquired; SHA-256 `4657ebfb78bda433528b7f1197fff32e299361d39379bb6839e871f43bc2ed11`; public scan rights unverified; not vendored | Variant viscosity-normalization and lineage comparison only | Variant differs in factor placement; not used to define Jamil/Thome mean |
| `TABOREK-HEDH-SHELL-TUBE-SINGLE-PHASE` | Taborek, *Heat Exchanger Design Handbook*, shell-and-tube single-phase lineage | Bibliographic lineage only | HEDH §3.3 target named in prior authority records | Exact body not acquired; no hash; public repost rights and exact body not verified | No transfer | Not assessable from exact body |
| `BELL-1963-DELAWARE-FINAL-REPORT` | K. J. Bell, *Final Report of the Cooperative Research Program on Shell and Tube Heat Exchangers*, Bulletin No.5 (1963) | Historical method-origin target | Bibliographic identity only | Body not acquired; no hash; rights not assessed | No transfer | Not assessable from exact body |

The ASME source is used narrowly.  Its statement is not promoted as a new
native Jamil/Thome correlation, as a pressure rule, or as permission to
transfer the full Delaware test method.

## 3. Temperature operator adjudication

The targeted ASME text states that it is usually adequate to use the
arithmetic-mean bulk shell-side fluid temperature, explicitly described as
halfway between inlet and exit temperatures, to evaluate all bulk properties
of the shell-side fluid.  It also warns that long temperature ranges or fluids
whose viscosity is very temperature-sensitive require special care, including
breaking the calculation into more limited temperature ranges.

The transfer is accepted only for the unresolved meaning of the source word
`mean`, because the following dimensions match:

1. the source quantity is a shell-side bulk temperature;
2. the endpoints are the source stream inlet and outlet/exit bulk states;
3. the accepted J_mu state is a whole-exchanger shell-stream mean;
4. the ASME statement is in its Delaware shell-side performance method, while
   the native TASK166/Jamil lineage is the Bell–Delaware shell-side context;
5. no pressure rule, property backend behavior, or local-state mapping is
   imported by this transfer.

Therefore the model-level temperature operator is bound as:

```text
SOURCE_MEAN_TEMPERATURE_OPERATOR_AUTHORITY_FOUND=true
SOURCE_MEAN_TEMPERATURE_OPERATOR=(T_shell_in + T_shell_out) / 2; ARITHMETIC_MEAN;HALFWAY_BETWEEN_SOURCE_INLET_AND_OUTLET_BULK_TEMPERATURES;WHOLE_SHELL_STREAM_OPERATOR_ONLY
SOURCE_MEAN_TEMPERATURE_OPERATOR_SOURCE_ID=ASME-PTC-12.5-2000-R2015-PUBLIC-COPY
SOURCE_MEAN_TEMPERATURE_OPERATOR_SOURCE_LOCATION=APPENDIX_C_SECTION_C.4_PRINTED_P58_DELAWARE_METHOD
SOURCE_MEAN_TEMPERATURE_OPERATOR_TRANSFERABLE_TO_TASK172_NATIVE_JMU=true
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=true
JMU_BULK_TEMPERATURE_AGGREGATION_RULE=ARITHMETIC_MEAN_OF_REVIEWED_SHELL_INLET_AND_OUTLET_BULK_TEMPERATURES;CONDITIONAL_PTC_DELAWARE_TRANSFER;NO_LOCALIZATION
```

This is an operator-transfer decision, not a real calculation.  It does not
authorize averaging property values, averaging pressures, or using an
arithmetic mean at a local cell or wall support.

For the source phrase “all bulk properties,” the temperature state anchor is
therefore applicable to `mu_bulk`, `cp`, `k`, `rho`, and `Pr` where the reviewed
property profile domain is otherwise satisfied.  It does not complete the
thermodynamic state until the pressure semantics and a case-bound property
snapshot are supplied.

## 4. ASME PTC 12.5 transfer boundary

```text
ASME_PTC125_BODY_AUTHORITY_ACQUIRED=true
ASME_PTC125_EXACT_LOCATION_BOUND=true
ASME_PTC125_ARITHMETIC_MEAN_RULE_OBSERVED=true
ASME_PTC125_RULE_SCOPE=USUALLY_ADEQUATE_ARITHMETIC_MEAN_HALF-WAY_BETWEEN_SHELL_INLET_AND_EXIT_TEMPERATURES_FOR_ALL_SHELL_BULK_PROPERTIES;LONG_RANGE_OR_HIGH_VISCOSITY_SENSITIVITY_REQUIRES_SPECIAL_CARE
ASME_PTC125_NATIVE_METHOD_CONTEXT=APPENDIX_C_DELAWARE_METHOD_WITHIN_SINGLE_PHASE_HEAT_EXCHANGER_PERFORMANCE_TEST_CODE
ASME_PTC125_TRANSFER_COMPATIBLE_WITH_JAMIL_THOME_JMU=true
```

`ASME_PTC125_TRANSFER_COMPATIBLE_WITH_JAMIL_THOME_JMU=true` is scoped to the
temperature aggregation operator only.  The transfer does not include the
PTC test plan, measurement uncertainty, pressure-loss calculation, density
handling for flow metering, or any default property pressure.

The public PTC text separately discusses pressure measurement and pressure
loss, and uses pressure/density quantities in pressure-loss calculations.  It
does not state which pressure must accompany the shell-side arithmetic-mean
temperature for J_mu property evaluation.  That is not a pressure rule for
this gate.

```text
ASME_PTC125_TRANSFER_CONFLICTS=PTC_DELAWARE_TEST-CODE_TEMPERATURE_CONVENTION_DOES_NOT_DEFINE_JAMIL_THOME_JMU_PROPERTY_PRESSURE;DOES_NOT_PROMOTE_CURRENT_PTC_2000_R2025_BODY_AS_ACQUIRED;DOES_NOT_TRANSFER_FULL_TEST_METHOD_OR_UNCERTAINTY_RULES
```

## 5. Pressure adjudication

No reviewed source in the targeted chain binds one of:

```text
INLET_PRESSURE
OUTLET_PRESSURE
ARITHMETIC_MEAN_INLET_OUTLET_PRESSURE
LOCAL_BULK_PRESSURE
REPRESENTATIVE_SHELL_PRESSURE
PRESSURE_VARIATION_NEGLIGIBLE_UNDER_EXPLICIT_DOMAIN
```

ASME PTC 12.5 requires pressure measurements for test work and uses pressure
and density in pressure-loss calculations, but that is not an instruction to
pair J_mu properties with inlet pressure, outlet pressure, arithmetic-mean
pressure, or a constant pressure.  The small-density-variation treatment in
the pressure-loss appendix is not a source-mean property pressure rule.

Accordingly:

```text
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE=NONE
JMU_BULK_PRESSURE_RULE_SOURCE_ID=NONE
JMU_BULK_PRESSURE_RULE_SOURCE_LOCATION=NONE
JMU_BULK_PRESSURE_RULE_BOUND=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
PRESSURE_INSENSITIVITY_SOURCE_ID=NONE
PRESSURE_INSENSITIVITY_DOMAIN=NONE
PRESSURE_INSENSITIVITY_REQUIRED_INPUTS=NONE
PRESSURE_INSENSITIVITY_ACCEPTANCE_RULE=NONE
```

No arithmetic mean pressure, constant-pressure assumption, or pressure
insensitivity threshold is created.

## 6. Endpoint producer audit

The reviewed endpoint-pair contract is consumed but not recreated.  The
repository audit remains negative for real producers:

| Candidate | Finding | Admission |
| --- | --- | --- |
| TASK160 | Conditional representation compatibility for a future shell inlet adapter only | Not a reviewed real producer |
| TASK162 | Derived outlet is coupled to `U`, tube film, and shell film; it is a legacy performance result | Not admissible as J_mu source outlet |
| TASK032 | One generic shell bulk `PropertySnapshot` representation | Not an inlet, outlet, or source-mean producer |
| TASK171 | Topology, face, path, interval and state-location vocabulary | No thermodynamic producer |
| TASK172 reviewed authorities | Endpoint pair contract is reviewed; no case-bound endpoint producer or snapshot exists | No real pair |

```text
REAL_REVIEWED_SHELL_INLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_OUTLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_ENDPOINT_PAIR_PRODUCER_FOUND=false
```

## 7. Producer-contract disposition

The temperature operator is now a model-level source-backed contract.  The
full source-mean producer is not complete because its pressure rule is absent
and neither endpoint has a real producer.  The future producer shape remains
conditional on the reviewed endpoint pair and requires, at minimum:

```text
SOURCE_MEAN_STATE_ID/HASH
TASK172_CASE_ID/HASH
TASK171_TOPOLOGY_ID/HASH
SHELL_STREAM_ID
SOURCE_INLET_STATE_ID/HASH
SOURCE_OUTLET_STATE_ID/HASH
TEMPERATURE_AGGREGATION_AUTHORITY_ID/HASH
PRESSURE_RULE_AUTHORITY_ID/HASH
PROPERTY_AUTHORITY_ID/VERSION
PROPERTY_SNAPSHOT_ID/HASH
STATE_PRODUCER_AUTHORITY_ID
STATE_PRODUCER_LIFECYCLE_STATUS
PROVENANCE_REFS
CANONICAL_HASH
```

Because `PRESSURE_RULE_AUTHORITY_ID/HASH` cannot be populated from an admitted
source, no source-mean producer candidate is created:

```text
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND=true
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
```

The reviewed water property authority remains conditional and is not called:

```text
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
```

The source mean remains whole-stream only:

```text
WHOLE_EXCHANGER_SOURCE_STATE_LOCALIZATION_AUTHORIZED=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
WALL_TEMPERATURE_AGGREGATION_RULE_BOUND=false
```

## 8. Dependency classification and circularity

The model-level operator consumes reviewed endpoint states; it does not call
`J_mu`.  The provenance of a future outlet state is not admitted, so possible
upstream dependence through a future calculation cannot be silently declared
independent:

```text
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_JMU=false
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_SHELL_FILM=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_WALL_STATE=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_OVERALL_U=undetermined
JMU_BULK_STATE_PRODUCER_DEPENDS_ON_Q=undetermined
```

The `undetermined` values mean that no endpoint producer exists from which a
dependency graph could be proven.  They do not authorize any of those inputs.

## 9. Preserved blockers and governance

```text
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false

QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED

L2B_BRANCH_STATUS=PAUSED_PENDING_REQUIRED_PHYSICAL_AUTHORITY_CLOSURE
L2B_METHOD_STATUS=METHOD_UNBOUND
L3_LOCAL_STATE_RECONSTRUCTION_BRANCH_STATUS=PAUSED_PENDING_DIRECT_LOCAL_STATE_PRODUCER_AUTHORITY_OR_RECONSTRUCTION_OPERATOR_AUTHORITY
L3_METHOD_STATUS=METHOD_UNBOUND
NUMERICAL_ERROR_BUDGET_STOPPING_BRANCH_STATUS=PAUSED_PENDING_ACTUAL_METHOD_SENSITIVITY_QUANTITATIVE_ERROR_ALLOCATION_AND_MESH_QUALIFICATION
MESH_CONVERGENCE_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_APPROVED_OBSERVABLES_MAPPING_METRIC_REFINEMENT_SEQUENCE_THRESHOLD_AND_ESTIMATOR

EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

This is documentation/evidence only.  No production code, TASK166/TASK171
file, property backend, state instance, wall solve, Q work, numerical work,
dependency, lockfile, workflow, Ready, or Merge action is authorized.

## 10. Decision

```text
RESULT=BLOCKED
OUTCOME=OUTCOME_B_TEMPERATURE_OPERATOR_BOUND_PRESSURE_RULE_UNRESOLVED
PRODUCTION_ADMISSION=BLOCKED_FAIL_CLOSED
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
STOP=true
```

