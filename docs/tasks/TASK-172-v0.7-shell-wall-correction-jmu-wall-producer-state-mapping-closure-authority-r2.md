# TASK172 R2 — Jμ wall-producer Q, film, and state-mapping closure authority

## 1. Receipt and boundary

This documentation/evidence-only package audits the remaining closure inputs
for a future Jamil/Thome `J_mu` wall-property correction. It does not
implement `J_mu`, execute a wall-temperature calculation, start a fixed-point
iteration, change TASK166, or start general numerical qualification.

```text
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_WALL_PRODUCER_STATE_MAPPING_CLOSURE_AUTHORITY_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=709049ce69445dae05d87a48957f522fdb21a102
MODE=JMU_WALL_PRODUCER_Q_FILM_AND_STATE_MAPPING_CLOSURE_AUTHORITY_ONLY
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

The authorized questions are:

1. whether any existing repository artifact is a qualified signed heat-rate
   source for the clean radial wall network;
2. which preliminary shell and tube film inputs are actually authorized;
3. whether a case-level wall-material property profile exists;
4. whether the existing geometry and state contracts supply the required
   producer inputs;
5. whether the source whole-bundle Jμ observation can be mapped to local
   TASK171 wall states; and
6. whether the conditional circularity path is active after those source
   choices are made.

The Bell/Jamil coefficient-lineage and `m=0.14` source-rule findings are
carried forward unchanged. Jμ is not added to any formula by this record.

## 2. Canonical predecessor state

The effective predecessor overlay is inherited without rewriting any prior
record:

```ini
CLEAN_INTERFACE_TEMPERATURE_CONTINUITY_AUTHORITY_BOUND=true
SHELL_FLUID_LIMIT_EQUALS_METAL_OUTER_SURFACE_AUTHORIZED=true
WALL_STATE_MAPPING_SERVICE_SCOPE=CLEAN_ONLY
CLEAN_RADIAL_NETWORK_EQUATIONS_BOUND=true
CLEAN_RADIAL_NETWORK_PHYSICAL_CLOSURE_BOUND=true
CLEAN_RADIAL_NETWORK_RUNTIME_PRODUCER_BOUND=false
CLEAN_RADIAL_NETWORK_NUMERICAL_EXECUTION_AUTHORIZED=false
JMU_SOURCE_WALL_STATE_IDENTITY_STATUS=PARTIALLY_BOUND
JMU_SOURCE_TO_TASK172_WALL_STATE_MAPPING_BOUND=false
JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE=UNBOUND
PRELIMINARY_SHELL_FILM_DEFINITION_BOUND=false
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
SOURCE_BULK_STATE_AVAILABLE_IN_TASK172=false
SOURCE_BULK_STATE_PRODUCER_BOUND=false
LOCALIZATION_TRANSFER_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

The Thome identity semantics remain the corrected effective values from the
predecessor overlay:

```ini
THOME_EDITION_IDENTITY_BOUND=true
THOME_EDITION_IDENTITY_SCOPE=RELEVANT_CHAPTER_CONTENT_ONLY
THOME_EXACT_CITED_2004_EDITION_CHAIN_BOUND=false
THOME_RIGHTS_REVIEW_COMPLETE=false
THOME_INDEPENDENT_AUTHORITY_REVIEW_COMPLETE=false
THOME_PRODUCTION_AUTHORITY_PROMOTED=false
```

The source chapter observation remains cross-check evidence. It is not
promoted into a production authority by this package.

## 3. Evidence boundary and repository sources

This R2 does not acquire a new external formula. It audits the existing
repository contracts and their code paths at the accepted predecessor
revision. The relevant evidence is:

| Evidence | Exact repository location | Finding used here |
| --- | --- | --- |
| TASK171 bookkeeping model | `src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/models.py`, `HeatObservation` and `Bookkeeping` | A wall heat rate is caller-supplied observation data; no Q producer is defined |
| TASK171 bookkeeping service | `src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/service.py`, `_bookkeeping` | The service consumes supplied face enthalpies/mass flows and wall heat observations and computes residual values; it does not generate duty |
| TASK032 contract | `docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md` | One shell bulk property snapshot; heat duty, outlet temperatures and wall iteration are explicit non-scope |
| TASK033 contract | `docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md` | Screening HTC only; heat duty, wall iteration and automatic wall-viscosity iteration are explicit non-scope |
| TASK162 service | `src/hexagent/exchangers/shell_tube/thermal_performance_closure/service.py`, `_success` | `q_method` is derived from `UA`, the Table 7 relation, capacity rate and inlet temperature difference |
| TASK038 service | `src/hexagent/exchangers/shell_tube/overall_heat_transfer_coefficient_ua/validation.py`, `_success_result` | `UA` composes tube film, shell film and wall/fouling resistance inputs |
| TASK163 service | `src/hexagent/exchangers/shell_tube/thermal_rating_composition/service.py` | TASK163 projects/replays TASK162 duty; it is not an independent Q authority |
| Clean wall-state contract | `docs/tasks/TASK-172-v0.7-wall-temperature-state-authority-definition-r1.md` | The clean radial relations are algebraically defined but require supplied Q, films, k and local geometry; runtime producer is not authorized |
| Jμ state/domain review | `docs/tasks/TASK-172-v0.7-shell-wall-correction-jmu-state-domain-transfer-contract-r1.md` | Source bulk state is the source mean inlet/outlet state; source wall wording and localized use remain incomplete |
| Jμ producer audit R1 | `docs/tasks/TASK-172-v0.7-shell-wall-correction-jmu-wall-producer-and-state-mapping-authority-r1.md` | The preceding source/node and producer gaps are preserved |

The inherited implementation/source revision for the existing TASK032–TASK038
paths is the accepted main revision `git:04d7aac8adcda13edd27d6c9511019a05ee08d96`.
No source file is changed in this gate.

## 4. Q-source inventory

### 4.1 Candidate A — TASK171 HeatObservation / bookkeeping

`HeatObservation` contains `wall_interface_id`, `heat_rate_w` and a caller
binding. The bookkeeping service requires coverage for all wall interfaces,
uses the supplied signed heat rates in the cell residual calculation, and
returns a status of `COMPUTED_NOT_ASSESSED` when observations are present.
The binding proves provenance of an observation; it does not make the caller a
case-duty producer and it does not create an independent duty.

```ini
HEAT_RATE_SOURCE_ID=TASK171_BOOKKEEPING_HEAT_OBSERVATION
LIFECYCLE_STATUS=STRUCTURAL_CALLER_INPUT_ONLY
PHYSICAL_MEANING=SUPPLIED_SIGNED_WALL_INTERFACE_HEAT_OBSERVATION
GRANULARITY=LOCAL_WALL_INTERFACE_OR_CELL_INCIDENT_OBSERVATION
SIGN_CONVENTION=TASK171_Q_POSITIVE_HOT_TO_COLD
INPUTS=CALLER_SUPPLIED_LOCATED_FACE_AND_WALL_OBSERVATIONS_WITH_BINDINGS
DEPENDENCY_ON_U=false
DEPENDENCY_ON_TUBE_FILM=false
DEPENDENCY_ON_SHELL_FILM=false
DEPENDENCY_ON_JMU=false
CASE_LEVEL_OR_SOLVER_LEVEL=CALLER_OBSERVATION_LEVEL
COMPATIBLE_WITH_CLEAN_RADIAL_NETWORK=true_AS_EXPLICIT_INPUT_ONLY
QUALIFIED_Q_PRODUCER=false
```

The final line is the important boundary: an observation may be an input to a
future producer, but it is not a qualified Q authority for that producer.

### 4.2 Candidate B — TASK162 legacy thermal-performance `q_method`

The current TASK162 implementation computes the following dependency chain:

```text
task038.modeled_ua_w_k
  → ntu = UA / C_min
  → p_source = TASK162 Table-7 relation(ntu, r_source, baffle_count)
  → q_method = p_source * C_cold * (T_hot_in - T_cold_in)
  → TASK162 energy/outlet closure
```

TASK038 itself composes its resistance result from the native TASK026 tube
film, TASK035 shell film, TASK037 wall resistance and the two TASK037 fouling
terms. Consequently the legacy duty is whole-exchanger and HTC/UA-dependent;
it is not an independently supplied case duty and is not a local
`Q_ts,j` producer for TASK171.

```ini
HEAT_RATE_SOURCE_ID=TASK162_Q_METHOD_WHOLE_EXCHANGER_LEGACY_CLOSURE
LIFECYCLE_STATUS=INHERITED_LEGACY_IMPLEMENTED;NOT_TASK172_Q_AUTHORITY
PHYSICAL_MEANING=WHOLE_EXCHANGER_PERFORMANCE_METHOD_DUTY_MAGNITUDE
GRANULARITY=WHOLE_EXCHANGER
SIGN_CONVENTION=LEGACY_POSITIVE_DUTY_UNDER_HOT_INLET_GREATER_THAN_COLD_INLET
INPUTS=TASK160_CAPACITY_AND_INLET_STATES;TASK161_METHOD;TASK038_UA;CASE_BAFFLE_COUNT
DEPENDENCY_ON_U=true
DEPENDENCY_ON_TUBE_FILM=true_TRANSITIVELY_THROUGH_TASK038
DEPENDENCY_ON_SHELL_FILM=true_TRANSITIVELY_THROUGH_TASK038
DEPENDENCY_ON_JMU=NOT_IN_CURRENT_FORM;WOULD_BE_TRANSITIVE_IF_REBOUND_TO_ACTIVE_JMU_HTC
CASE_LEVEL_OR_SOLVER_LEVEL=LEGACY_WHOLE_EXCHANGER_CLOSURE
COMPATIBLE_WITH_CLEAN_RADIAL_NETWORK=false_NO_LOCAL_QTS_OR_MAPPING_RULE
QUALIFIED_Q_PRODUCER=false_FOR_TASK172
```

This audit does not invalidate TASK162's own legacy contract. It only refuses
to reinterpret that contract as a TASK172 local wall-state input without a
new, independently reviewed projection and coupling rule.

### 4.3 Candidate C — TASK163 heat-duty projection

TASK163 accepts and replays a TASK162 result, then constructs a
`Task163HeatDutyProjection` from the TASK162 `q_method`. It does not compute a
new independent duty and does not change the granularity or dependencies of
TASK162.

```ini
HEAT_RATE_SOURCE_ID=TASK163_TASK162_DUTY_PROJECTION
LIFECYCLE_STATUS=DOWNSTREAM_PROJECTION_ONLY
PHYSICAL_MEANING=REPLAYED_TASK162_Q_METHOD
GRANULARITY=WHOLE_EXCHANGER
SIGN_CONVENTION=INHERITED_TASK162_DUTY_SEMANTICS
INPUTS=ACCEPTED_TASK162_RESULT_AND_REPLAY_EVIDENCE
DEPENDENCY_ON_U=INHERITED_TRUE
DEPENDENCY_ON_TUBE_FILM=INHERITED_TRANSITIVE
DEPENDENCY_ON_SHELL_FILM=INHERITED_TRANSITIVE
DEPENDENCY_ON_JMU=NOT_CURRENTLY_BOUND;FUTURE_REBINDING_WOULD_REQUIRE_AUTHORITY
CASE_LEVEL_OR_SOLVER_LEVEL=DOWNSTREAM_COMPOSITION
COMPATIBLE_WITH_CLEAN_RADIAL_NETWORK=false_NO_LOCAL_PROJECTION_AUTHORITY
QUALIFIED_Q_PRODUCER=false
```

### 4.4 Candidate D — case input or observation duty

The repository contains caller/case input patterns in other historical
families, but no current TASK172 shell-and-tube case-bound signed duty
authority is bound to the admitted topology, physical support and clean wall
network. A caller assertion or a field named `Q` cannot become authority by
itself.

```ini
HEAT_RATE_SOURCE_ID=CASE_DUTY_OR_CALLER_ASSERTION
LIFECYCLE_STATUS=NOT_BOUND
PHYSICAL_MEANING=UNSPECIFIED_CASE_OR_OBSERVATION_DUTY
GRANULARITY=UNBOUND
SIGN_CONVENTION=UNBOUND
INPUTS=UNBOUND
DEPENDENCY_ON_U=UNBOUND
DEPENDENCY_ON_TUBE_FILM=UNBOUND
DEPENDENCY_ON_SHELL_FILM=UNBOUND
DEPENDENCY_ON_JMU=UNBOUND
CASE_LEVEL_OR_SOLVER_LEVEL=UNBOUND
COMPATIBLE_WITH_CLEAN_RADIAL_NETWORK=UNPROVEN
QUALIFIED_Q_PRODUCER=false
```

Historical double-pipe duty solvers are not transferred into the
shell-and-tube TASK172 topology. No new Q source is created here.

## 5. Q authority classification and circularity input

Because the only local TASK171 heat-rate artifact is an observation, the only
legacy calculated duty is a whole-exchanger UA-dependent output, and no
independent case duty is bound, the required classification is:

```ini
JMU_WALL_PRODUCER_HEAT_RATE_AUTHORITY_STATUS=NO_QUALIFIED_Q_AUTHORITY
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE_ID=NONE
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE=NONE;TASK171_OBSERVATION_ONLY;TASK162_TASK163_WHOLE_EXCHANGER_DUTY_NOT_LOCAL_TASK172_PRODUCER
JMU_WALL_PRODUCER_HEAT_RATE_GRANULARITY=UNBOUND
Q_DEPENDS_ON_ACTIVE_JMU=undetermined
Q_DEPENDS_ON_SHELL_FILM=undetermined
Q_DEPENDS_ON_OVERALL_U=undetermined
JMU_WALL_PRODUCER_REQUIRES_ACTIVE_JMU=undetermined
```

The three `undetermined` dependency fields do not mean that the repository
has no known dependency facts. The candidate audit establishes that TASK162's
legacy `q_method` depends on `UA` and therefore transitively on shell film,
while TASK171 has no duty producer. Since no source is selected for the
future Jμ wall producer, no one dependency graph can be promoted to the
producer contract.

The conditional graph remains identified but not classified as active:

```ini
JMU_WALL_COUPLING_CIRCULARITY_PATH_IDENTIFIED=true
JMU_WALL_COUPLING_CIRCULARITY_PATH=CONDITIONAL_SELECTED_Q_OR_PRELIMINARY_SHELL_FILM_TO_CLEAN_RADIAL_WALL_STATE_TO_MU_WALL_TO_JMU
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_WALL_COUPLING_CLOSURE_AUTHORITY_BOUND=false
```

If a future authority supplies an independent case duty and a preliminary
shell film that excludes active `J_mu`, this particular producer path may be
acyclic. If either the selected Q or preliminary shell film consumes the
active corrected shell coefficient, the cycle is real. This R2 does not pick
between those alternatives and does not authorize iteration, relaxation,
residual thresholds or last-iterate acceptance.

## 6. Preliminary shell-film authority

The acquired source wording says that wall temperature is obtained from a
preliminary heat-transfer calculation. It does not select which of the
following shell-film definitions is the preliminary input for the active
Jμ calculation:

| Candidate | Definition | R2 status |
| --- | --- | --- |
| A | ideal `h_c` only | Not source-selected |
| B | `h_c*Jc*Jl*Jb*Js*Jr`, excluding `J_mu` | Not source-selected |
| C | fully corrected film including `J_mu` | Not source-selected; would create the conditional loop |
| D | another source-defined preliminary film | No such rule bound |
| E | no preliminary film definition | Current fail-closed state |

Therefore:

```ini
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_DEFINITION=NO_AUTHORIZED_SELECTION_AMONG_IDEAL_GEOMETRY_CORRECTED_OR_FULL_JMU_CORRECTED_FILM
PRELIMINARY_SHELL_FILM_SOURCE_AUTHORITY=UNBOUND_BY_ACQUIRED_JAMIL_THOME_STATE_TEXT
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
```

Selecting B only to avoid a fixed point would be engineering convenience, not
authority. Selecting C without a closure authority would silently start the
very loop this gate is forbidden to solve. The shell-film blocker therefore
remains open.

## 7. Preliminary tube-film audit

The clean radial network requires a supplied, qualified tube film as an input.
The native TASK026 result is a separate correlation authority and the earlier
tube-wall correction lifecycle remains separately governed. This gate does
not reopen that work and does not promote a TASK026 result into a preliminary
wall-producer input by naming similarity.

```ini
PRELIMINARY_TUBE_FILM_DEFINITION_BOUND=false
PRELIMINARY_TUBE_FILM_SOURCE_AUTHORITY=TASK026_NATIVE_FILM_IS_NOT_BOUND_AS_A_TASK172_PRELIMINARY_WALL_PRODUCER_INPUT
PRELIMINARY_TUBE_FILM_ACTIVE_WALL_CORRECTION_DEPENDENCY=TASK026_ACTIVE_WALL_CORRECTION_SCOPE_IS_SEPARATE;NO_NEW_REUSE_OR_TRANSFER_IN_THIS_GATE
```

This is an input dependency finding, not a new tube correction decision.

## 8. Wall conductivity and material dependency

The model-level Layer A, Layer B and Layer C contracts are accepted, but no
actual case-level material instance or property body is present in the current
state. The effective material fields remain:

```ini
MATERIAL_PROFILE_ID=NONE
MATERIAL_IDENTITY_ACTUAL_VALUE_BOUND=false
MATERIAL_PROPERTY_BODY_ACTUAL_VALUE_BOUND=false
ACTUAL_MATERIAL_CASE_ACCEPTED=false
MATERIAL_CONSTANT_K_STATUS=OPEN
MATERIAL_K_TEMPERATURE_DOMAIN_BOUND=false
```

The clean radial equations require a case-bound `k_wall`; the absence of a
profile cannot be filled by a fixture grade, a point value, a material-name
lookup or a legacy `tube_thermal_conductivity` field.

```ini
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
WALL_PRODUCER_MATERIAL_PROFILE_ID=NONE
WALL_PRODUCER_K_WALL_TEMPERATURE_DOMAIN_BOUND=false
```

This preserves the model-level canonical blocker closure already recorded. It
does not reopen that adjudication and does not claim case readiness.

## 9. Geometry authority audit

The future producer's physical geometry inputs are already represented by
source-bound upstream identities, provided that a future request carries the
exact values and hashes:

```ini
WALL_PRODUCER_GEOMETRY_AUTHORITY_BOUND=true
WALL_PRODUCER_GEOMETRY_SOURCE_ID=TASK021_TUBE_GEOMETRY_PLUS_TASK025_LENGTH_AND_AREA_PLUS_TASK037_CYLINDRICAL_MAPPING_PLUS_TASK171_PHYSICAL_SUPPORT
WALL_PRODUCER_TUBE_INNER_RADIUS_BOUND=true
WALL_PRODUCER_TUBE_OUTER_RADIUS_BOUND=true
WALL_PRODUCER_LENGTH_OR_AREA_BASIS_BOUND=true
```

This is an input-authority finding, not a producer promotion. The identities
are:

* TASK021 supplies the accepted tube geometry snapshot and native inner and
  outer diameters;
* TASK025 supplies the accepted heat-transfer length/area result;
* TASK037 supplies the reviewed cylindrical area/resistance semantics; and
* TASK171 supplies the explicit wall interface and event-bounded physical
  support.

The R2 network still must fail closed if any exact geometry/support hash is
missing or mismatched. Nominal-diameter substitution and geometry inferred
from an array index remain forbidden.

## 10. Bulk-state producer audit

The source Jμ observation uses properties at the mean of the source stream's
inlet and outlet bulk temperatures. TASK032 exposes one
`SINGLE_BULK_PROPERTY_SNAPSHOT_ALGEBRAIC_FLOW_STATE_SCREENING` snapshot and
does not expose a source-bound inlet/outlet pair or an equivalent mean-state
producer. TASK171's topology has path inlet/outlet structure, but its state
model does not create thermal inlet/outlet values or a property evaluation.

```ini
WALL_PRODUCER_REQUIRED_BULK_GRANULARITY=SOURCE_MEAN_INLET_OUTLET_FOR_GLOBAL_JMU;LOCATED_TUBE_AND_SHELL_BULK_FOR_LOCAL_RADIAL_NETWORK
SHELL_INLET_STATE_AUTHORITY_BOUND=false
SHELL_OUTLET_STATE_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_FORMULA_AUTHORITY_BOUND=false_FOR_TASK172_PRODUCER
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
SOURCE_BULK_STATE_AVAILABLE_IN_TASK172=false
SOURCE_BULK_STATE_PRODUCER_BOUND=false
SOURCE_TO_TASK032_BULK_MAPPING_BOUND=false
```

The source word “mean” is retained as a source semantic observation. This
record does not silently choose an arithmetic mean, a segment mean, a local
cell state, an inlet state or an outlet state as a replacement. A future
case-level rule may construct the source mean from authoritative inlet and
outlet states, but that rule is not present here and is not implemented.

## 11. Whole-bundle versus local wall state

The acquired Jμ application is a whole-exchanger/mean-tube-bundle source
observation. The clean TASK172 network is expressed for explicit local
physical supports and requires located local bulk states and a signed local
heat rate. No source-authorized projection connects those granularities.

```ini
SOURCE_JMU_WALL_STATE_GRANULARITY_BOUND=false
SOURCE_JMU_WALL_STATE_GRANULARITY=WHOLE_EXCHANGER_MEAN_TUBE_BUNDLE_SOURCE_OBSERVATION;WALL_NODE_IDENTITY_AND_AGGREGATION_RULE_UNRESOLVED
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
WALL_TEMPERATURE_AGGREGATION_RULE_BOUND=false
WHOLE_EXCHANGER_JMU_USES_WHOLE_EXCHANGER_WALL_STATE=SOURCE_GRANULARITY_OBSERVATION_ONLY_NOT_EXECUTION_RULE
LOCAL_WALL_STATE_TO_GLOBAL_JMU_MAPPING_BOUND=false
LOCALIZATION_TRANSFER_AUTHORITY_BOUND=false
```

No arithmetic, area-weighted, UA-weighted or heat-flux-weighted average of
local wall temperatures is introduced. A future local Jμ application is not
authorized merely because TASK171 is segmented, and a whole-exchanger Jμ is
not repeated or divided by numerical-cell count.

## 12. Source wall identity and clean interface

The source remains only partially specific: it requires a wall temperature at
the heat-transfer surface for `mu_wall`, but does not resolve fluid-side limit,
tube-metal outer surface, interface node, film temperature or another node.
The clean repository contract does authorize, only under the clean profile,
the physical alias:

```text
SHELL_FLUID_WALL_INTERFACE == TUBE_METAL_OUTER_SURFACE
```

That alias excludes fouling, contact resistance and an interfacial temperature
jump, but it does not prove that the source's unspecified wall node is the
metal node or the fluid limiting node. It also does not create a temperature
value.

```ini
JMU_SOURCE_WALL_STATE_IDENTITY_STATUS=PARTIALLY_BOUND
JMU_SOURCE_WALL_STATE_IDENTITY=HEAT_TRANSFER_SURFACE_WALL_TEMPERATURE;SOURCE_DOES_NOT_SELECT_SHELL_FLUID_LIMIT_METAL_OUTER_SURFACE_INTERFACE_OR_FILM_NODE
JMU_SOURCE_WALL_PROPERTY_SIDE=UNRESOLVED
JMU_REQUIRED_WALL_SURFACE_IDENTITY_BOUND=false
JMU_REQUIRED_WALL_SURFACE_IDENTITY=SOURCE_HEAT_TRANSFER_SURFACE_WALL_TEMPERATURE_WITH_FLUID_SIDE_UNRESOLVED
CLEAN_INTERFACE_TEMPERATURE_CONTINUITY_AUTHORITY_BOUND=true
CLEAN_INTERFACE_CONTACT_RESISTANCE_INCLUDED=false
CLEAN_INTERFACE_FOULING_INCLUDED=false
SHELL_FLUID_LIMIT_EQUALS_METAL_OUTER_SURFACE_AUTHORIZED=true_CLEAN_ONLY
TASK172_WALL_STATE_MAPPING_VALID=false
```

Accordingly, physical continuity is accepted for the clean network, while
source-to-TASK172 Jμ mapping remains unbound.

## 13. Clean radial network closure audit

The inherited equations remain exactly those already reviewed:

```text
R_i,j   = 1 / (h_i A_i,j)
R_w,j   = d_i ln(d_o / d_i) / (2 k_wall A_i,j)
R_o,j   = 1 / (h_o A_o,j)
R_sum,j = R_i,j + R_w,j + R_o,j

Q_ts,j = +q_j when tube is HOT
Q_ts,j = -q_j when shell is HOT

T_tube_bulk,j - T_shell_bulk,j = Q_ts,j R_sum,j
T_tube_inner,j = T_tube_bulk,j - Q_ts,j R_i,j
T_tube_outer,j = T_tube_inner,j - Q_ts,j R_w,j
T_tube_outer,j = T_shell_bulk,j + Q_ts,j R_o,j
```

These equations are physically closed when all required inputs are supplied.
They do not themselves choose Q, film coefficients, `k_wall`, bulk states or
a source-compatible whole-bundle aggregation. No equation is added here and
no numeric evaluation is performed.

```ini
CLEAN_RADIAL_NETWORK_EQUATIONS_BOUND=true
CLEAN_RADIAL_NETWORK_PHYSICAL_CLOSURE_BOUND=true
CLEAN_RADIAL_NETWORK_RUNTIME_PRODUCER_BOUND=false
CLEAN_RADIAL_NETWORK_NUMERICAL_EXECUTION_AUTHORIZED=false
JMU_WALL_TEMPERATURE_PRODUCER_PHYSICAL_AUTHORITY_BOUND=false
JMU_WALL_TEMPERATURE_PRODUCER_RUNTIME_AUTHORITY_BOUND=false
```

## 14. Signed heat-rate direction

The sign convention is inherited from TASK171 and is not modified:

```ini
SIGNED_HEAT_RATE_DIRECTION_AUTHORITY_BOUND=true
SHELL_FLUID_HEATING_WHEN_Q_SIGN=Q_GT_0_WHEN_SHELL_IS_COLD;Q_TS_GT_0_WHEN_TUBE_IS_HOT
SHELL_FLUID_COOLING_WHEN_Q_SIGN=Q_GT_0_WHEN_SHELL_IS_HOT;Q_TS_LT_0_UNDER_TUBE_TO_SHELL_ORIENTATION
ABSOLUTE_HEAT_RATE_SUBSTITUTION_FORBIDDEN=true
```

A positive passive-resistance ordering and zero-duty behavior remain governed
by the accepted clean network. This record does not create a heat-rate source
or choose an active Jμ direction branch.

## 15. Circularity re-evaluation

The possible path is identified as:

```text
selected Q or preliminary shell film
  → clean radial wall state
  → shell-fluid wall viscosity
  → J_mu
  → corrected shell film or downstream duty
```

The state after this audit is:

```ini
JMU_WALL_COUPLING_CIRCULARITY_PATH_IDENTIFIED=true
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_WALL_COUPLING_CLOSURE_AUTHORITY_BOUND=false
```

The active status is intentionally not `true`: no Q or preliminary film has
been selected. It is also not `false`: TASK162 demonstrates that one existing
legacy duty path is UA/film dependent, and the source permits a preliminary
heat-transfer calculation without selecting its form. No hidden solver or
fixed-point policy is introduced.

## 16. Producer classification and outcome

The exact producer classification is:

```ini
JMU_WALL_PRODUCER_CLASSIFICATION=OUTCOME_G_MULTIPLE_BLOCKERS_REMAIN
```

The remaining direct producer gaps are:

1. no qualified signed Q authority for the TASK172 wall producer;
2. no source-authorized preliminary shell film definition or Jμ dependency;
3. no preliminary tube-film input contract for this wall producer;
4. no case-level material/k wall profile or temperature-domain coverage;
5. no source mean inlet/outlet state producer and no TASK032 mapping;
6. no source-compatible whole-bundle wall-state aggregation/localization rule;
7. no source-selected physical wall node mapping; and
8. no closure authority if the eventual Q/film choice activates the loop.

The outcome is therefore:

```ini
RESULT=BLOCKED
ADJUDICATION_OUTCOME=OUTCOME_G_MULTIPLE_BLOCKERS_REMAIN
JMU_SOURCE_TO_TASK172_WALL_STATE_MAPPING_BOUND=false
JMU_WALL_TEMPERATURE_PRODUCER_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
JMU_WALL_PRODUCER_AUTHORITY_CANDIDATE_CREATED=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

This is a correct blocked state, not a failure of the inherited clean radial
equations. The smallest next authority should bind the Q source and
preliminary film together, with an explicit decision on whether the selected
wall producer is global or local. It must not choose a convenient film solely
to avoid circularity.

## 17. Unrelated scope carried forward

The following are deliberately unchanged and not resolved by this gate:

```ini
JMU_RE_DOMAIN_SOURCE_BOUND=false
JMU_PR_DOMAIN_SOURCE_BOUND=false
JMU_VISCOSITY_RATIO_DOMAIN_SOURCE_BOUND=false
JMU_TEMPERATURE_DOMAIN_SOURCE_BOUND=false
GEOMETRY_SCOPE_TRANSFER_AUTHORITY_BOUND=false
TASK166_GEOMETRY_TRANSFER_COMPATIBLE=false
THOME_RIGHTS_REVIEW_COMPLETE=false
THOME_INDEPENDENT_AUTHORITY_REVIEW_COMPLETE=false
THOME_PRODUCTION_AUTHORITY_PROMOTED=false
JMU_EXPONENT_TRANSFER_AUTHORITY_BOUND=false
LOCALIZATION_TRANSFER_AUTHORITY_BOUND=false
```

The four effective TASK172 entry blockers remain exactly:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No numerical thresholds, mesh rules, solver methods or implementation
authority are added.

## 18. Governance and history

```ini
DOCUMENTATION_EVIDENCE_ONLY=true
SOURCE_STATE_AUDIT_ONLY=true
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
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

Only this R2 document, its machine evidence and the append-only registry
extension are in scope. Existing R1/R2 source and authority records remain
immutable. No copyrighted source body is vendored.

## 19. Next gate and verification receipt

```ini
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_Q_AND_PRELIMINARY_FILM_AUTHORITY_R1_ONLY
RUNTIME_PRODUCER_CREATED=false
NUMERICAL_EXECUTION_PERFORMED=false
FIXED_POINT_ITERATION_PERFORMED=false
```

The next gate is not executed by this package. Local validation and the
exact-final-head CI result are recorded in the companion evidence and final
task receipt after the append-only artifacts are committed.
