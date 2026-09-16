# TASK172 Q authority R2 — Jμ wall-producer heat-rate audit

## 1. Receipt and scope

This documentation/evidence-only package audits the signed heat-rate (Q)
input required by a future Jamil/Thome J_mu wall-temperature producer. It
does not choose a duty, create a duty producer, resolve preliminary films,
select material or k_wall, construct a mean-bulk producer, localize a
whole-exchanger duty, implement J_mu, execute a wall-temperature calculation,
start numerical iteration, modify TASK166, or change any dependency.

TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_Q_AUTHORITY_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=9f9ee9cc5486ea531c2a6addbaa9f439dc4401fb
MODE=JMU_QUALIFIED_SIGNED_Q_AUTHORITY_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
DOCUMENTATION_EVIDENCE_ONLY=true
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true

The authorized result is deliberately narrower than the shell-wall blocker.
Preliminary shell film, preliminary tube film, material and k_wall, mean
bulk state, global/local J_mu mapping, J_mu domains and numerical
qualification remain separate unresolved authorities.

## 2. Inherited state

The preceding Q/film audit is preserved; this R2 only refines the Q-side
classification:

QUALIFIED_Q_AUTHORITY_BOUND=false
Q_AUTHORITY_SOURCE_ID=NONE
Q_AUTHORITY_GRANULARITY=UNBOUND
TASK171_Q_OBSERVATION_INPUT_ADMISSIBLE=true
TASK171_Q_OBSERVATION_CASE_AUTHORITY_BOUND=false
INDEPENDENT_CASE_DUTY_AUTHORITY_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false

The accepted TASK171 sign convention remains:

q > 0 means HOT → COLD

It is not replaced by an unsigned duty convention.

## 3. Evidence boundary

The audit is based on the accepted repository contracts and their code paths
at the predecessor revision. The source paths below are recorded with both
repository blob identity and line-level locations so the findings can be
replayed without treating a field name as authority.

| Evidence | Revision/path and relevant location | Q finding |
| --- | --- | --- |
| TASK171 observation model | src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/models.py, blob e00218bf7f518bcec67be72ec1b33a614734f541, lines 158–173 | heat_rate_w is caller-supplied observation data; no case-duty producer |
| TASK171 bookkeeping service | src/hexagent/exchangers/shell_tube/segmented_thermal_state_topology/service.py, blob 2c19e1848387d5fde788f4524a0b88724760d9ab, lines 426–464 | supplied face/heat observations are used to compute residual bookkeeping |
| TASK032 contract | docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md, blob ac35e4d059efd1a517840b073f7a4b7f27304e53, lines 168–203 | heat duty, UA, outlet states and wall iteration are explicit non-scope |
| TASK033 contract | docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md, blob 9bca0257b8321f645c5b252d0195c3b6ee0157a8, lines 103–145 | screening HTC only; duty and wall-viscosity iteration are non-scope |
| TASK162 implementation | src/hexagent/exchangers/shell_tube/thermal_performance_closure/service.py, blob d20700eadc196cd04cb98236dcc4647f9e15558a, lines 818–847 | q_method is computed from UA, NTU, Table 7 relation, capacity rate and inlet states |
| TASK162 energy closure | same service, lines 637–702 | q hot/cold are checked/replayed from selected method duty; no independent duty input |
| TASK162 source identity | src/hexagent/exchangers/shell_tube/thermal_performance_closure/models.py, TASK162_SOURCE_DEFINITION_ID | native source identity is TASK162-SOURCE-DEFINITION-R1-ISSUE-229 |
| TASK038 UA composition | src/hexagent/exchangers/shell_tube/overall_heat_transfer_coefficient_ua/validation.py, blob 2b1e40a56f11881c49efed1a94b8f47f60895a27, lines 362–455 | UA composes tube film, shell film and wall/fouling resistance |
| TASK163 projection | src/hexagent/exchangers/shell_tube/thermal_rating_composition/service.py, blob e351b0052282efcdf30558342be7e4287e89cb52, lines 352–385 | Task163HeatDutyProjection replays TASK162 q fields |
| TASK163 source identity | src/hexagent/exchangers/shell_tube/thermal_rating_composition/models.py, TASK163_SOURCE_DEFINITION_ID | native source identity is TASK163-SOURCE-DEFINITION-R6-ISSUE-234 |
| Clean radial wall contract | docs/tasks/TASK-172-v0.7-wall-temperature-state-authority-definition-r1.md | future network requires signed local Q or Q_ts as supplied input |
| Prior Q/film audit | docs/tasks/TASK-172-v0.7-shell-wall-correction-jmu-q-and-preliminary-film-authority-r1.md | no case-duty authority or preliminary film was bound |
| Prior wall-producer closure audit | docs/tasks/TASK-172-v0.7-shell-wall-correction-jmu-wall-producer-state-mapping-closure-authority-r2.md | physical network is input-closed, not a Q producer |

No source file or historical evidence is changed by this record.

## 4. Requirement for a TASK172 wall-producer Q

The clean radial network requires a signed heat rate for the exact physical
support being evaluated. A qualifying Q authority therefore needs all of the
following as one source-bound contract:

Q_PHYSICAL_MEANING=SIGNED_HEAT_RATE_ACROSS_ONE_EXPLICIT_WALL_SUPPORT
Q_UNIT=W
Q_SIGN=TASK171_HOT_TO_COLD
Q_GRANULARITY=WHOLE_EXCHANGER_OR_INTERVAL_OR_CELL_OR_WALL_INTERFACE_EXPLICITLY_BOUND
Q_TOPOLOGY_BINDING=EXACT_TASK171_TOPOLOGY_ID_AND_HASH
Q_PHYSICAL_SUPPORT_BINDING=EXACT_WALL_INTERFACE_AND_EVENT_BOUNDED_SUPPORT
Q_CASE_BINDING=CASE_CONFIGURATION_ID_AND_HASH
Q_STATE_BINDING=LOCATED_UPSTREAM_DOWNSTREAM_ENTHALPY_AND_MASS_FLOW_STATES_WHERE_DERIVED
Q_SOURCE_BINDING=SOURCE_ID_REVISION_CLASS_LOCATION_RIGHTS_AND_EVIDENCE
Q_LIFECYCLE_BINDING=REVIEWED_AUTHORITY_OR_EXPLICITLY_ACCEPTED_EXTERNAL_RECEIPT
Q_DEPENDENCY_DECLARATION=U_FILMS_JMU_AND_ANY_OTHER_THERMAL_DEPENDENCY
Q_NO_HIDDEN_DEFAULT=true
Q_NO_CELL_COUNT_OR_AREA_DIVISION_UNLESS_SEPARATE_AUTHORITY=true

The current TASK171 Binding can carry syntactic authority metadata, but it
does not by itself prove all of the case, physical-support, source-lifecycle
and producer semantics above.

## 5. Candidate inventory

The following candidates were audited independently. qualified_for_task172
means suitable as the heat-rate authority for the future J_mu wall producer;
it does not invalidate an inherited source in its native task.

| Candidate | Physical meaning | Granularity | Dependency | TASK172 disposition |
| --- | --- | --- | --- | --- |
| A. Direct case/rating duty input | requested, measured or contractual duty only if case-bound and physically typed | not bound in current shell-tube contract | unknown until source is bound | absent |
| B. Tube-side enthalpy balance | m_dot*(h_in-h_out) for hot tube or corresponding signed relation | local/interval only with located states | no independent state producer in current TASK172 | absent |
| C. Shell-side enthalpy balance | m_dot*(h_out-h_in) for cold shell or corresponding signed relation | local/interval only with located states | no independent state producer in current TASK172 | absent |
| D. Reconciled two-side balance | one shared signed Q after a source-bound reconciliation rule | unknown | no two-side precedence/tolerance/reconciliation authority | absent |
| E. TASK171 HeatObservation | explicit caller-supplied wall-interface observation | local wall interface or cell-incident observation | observation itself has no calculated dependency | structural input only |
| F. TASK162 q_method | native performance-method duty | whole exchanger | UA → NTU → P → q; transitively tube/shell films and wall/fouling | legacy only; not qualified for TASK172 |
| G. TASK163 duty projection | replayed TASK162 duty fields | whole exchanger | inherits TASK162/UA dependencies | projection only; not qualified |
| H. Other shell-tube authority | no additional accepted case-duty producer found | not applicable | not applicable | absent |

The remainder of this document provides the evidence behind the rows that
control the result.

## 6. Candidate A — direct case-duty input

No current TASK172 shell-and-tube case contract binds a signed duty to the
admitted topology, physical wall support, clean radial network, and a reviewed
source receipt. required_duty_w-style values in sizing/selection metadata are
requirements or screening constraints, not a heat-rate observation across a
wall interface.

The older hexagent.core.heat_balance path is a double-pipe vertical slice.
Its known_duty_w is not a shell-tube TASK172 authority and is not transferred
across exchanger families. A user-entered number, field named Q, target duty,
or caller assertion cannot become engineering authority without an explicit
source, case, support, sign, units and lifecycle contract.

Q_SOURCE_ID=CASE_DUTY_OR_CALLER_ASSERTION
Q_SOURCE_LIFECYCLE=NOT_BOUND
Q_SOURCE_PHYSICAL_MEANING=UNSPECIFIED_CASE_OR_OBSERVATION_DUTY
Q_SOURCE_GRANULARITY=UNBOUND
Q_SOURCE_SIGN_CONVENTION=UNBOUND
Q_SOURCE_INPUTS=UNBOUND
Q_SOURCE_PROVENANCE_REQUIREMENTS=NOT_SATISFIED
Q_SOURCE_DEPENDS_ON_U=UNBOUND
Q_SOURCE_DEPENDS_ON_TUBE_FILM=UNBOUND
Q_SOURCE_DEPENDS_ON_SHELL_FILM=UNBOUND
Q_SOURCE_DEPENDS_ON_JMU=UNBOUND
Q_SOURCE_TASK172_SUPPORT_COMPATIBLE=UNPROVEN
Q_SOURCE_AUTHORITY_DISPOSITION=NO_TASK172_CASE_DUTY_AUTHORITY_FOUND

DIRECT_CASE_DUTY_AUTHORITY_BOUND=false
DIRECT_CASE_DUTY_SOURCE_ID=NONE
DIRECT_CASE_DUTY_SIGN_CONVENTION_BOUND=false
DIRECT_CASE_DUTY_PHYSICAL_SUPPORT_BOUND=false

## 7. Candidates B–D — enthalpy duty and reconciliation

TASK171 has a FaceObservation schema containing enthalpy and mass-flow text,
but those are caller observations. The service validates observation
coverage, requires positive equal mass flow for each cell and computes a
bookkeeping residual; it does not establish a reviewed thermal inlet/outlet
state pair, produce an outlet state, or promote the residual to a duty
authority.

The clean radial network also needs the heat rate at its physical support. No
current authority provides the complete tube-side or shell-side set of
located inlet/outlet enthalpy states, mass-flow state, case/configuration
binding and source lifecycle required to derive that local Q.

TUBE_ENTHALPY_DUTY_INPUTS_BOUND=false
TUBE_ENTHALPY_DUTY_AUTHORITY_BOUND=false
TUBE_ENTHALPY_DUTY_SOURCE_ID=NONE
TUBE_ENTHALPY_DUTY_GRANULARITY=UNBOUND
TUBE_ENTHALPY_DUTY_REASON=TASK171_FACE_OBSERVATIONS_ARE_INPUT_ONLY_AND_NO_TASK172_REVIEWED_TUBE_STATE_PRODUCER_EXISTS

SHELL_ENTHALPY_DUTY_INPUTS_BOUND=false
SHELL_ENTHALPY_DUTY_AUTHORITY_BOUND=false
SHELL_ENTHALPY_DUTY_SOURCE_ID=NONE
SHELL_ENTHALPY_DUTY_GRANULARITY=UNBOUND
SHELL_ENTHALPY_DUTY_REASON=TASK171_FACE_OBSERVATIONS_ARE_INPUT_ONLY_AND_NO_TASK172_REVIEWED_SHELL_STATE_PRODUCER_EXISTS

TWO_SIDE_DUTY_RECONCILIATION_AUTHORITY_BOUND=false
DUTY_RECONCILIATION_RULE=NONE
DUTY_RECONCILIATION_TOLERANCE=NOT_INTRODUCED

No average, preferred side, tolerance, or silent sign transform is created.
The TASK171 bookkeeping relation remains the inherited conservation
structure, not a new Q producer.

## 8. Candidate E — TASK171 structural Q input

HeatObservation is the only current TASK171-shaped location for a signed wall
heat rate. It is valid as explicit structural input when its wall_interface_id
and binding are exact. This is useful for a later producer, but it is not
itself a physical case-duty producer.

The minimum additional evidence for treating one observation as an
authority-bound wall-network input is:

TASK171_Q_OBSERVATION_REQUIRED_PROVENANCE=
  TASK171_TOPOLOGY_ID_AND_HASH;
  EXACT_WALL_INTERFACE_ID_AND_PHYSICAL_SUPPORT;
  EVENT_BOUNDED_PHYSICAL_INTERVAL_ID;
  HOT_COLD_STREAM_AND_SIDE_ASSIGNMENT;
  SIGNED_W_HEAT_RATE_UNIT_AND_TASK171_Q_SIGN;
  CASE_CONFIGURATION_ID_AND_HASH;
  UPSTREAM_FACE_STATE_IDS_AND_HASHES_WHERE_DERIVED;
  MASS_FLOW_AND_ENTHALPY_STATE_LOCATIONS;
  PRODUCER_OR_MEASUREMENT_SOURCE_ID_REVISION_CLASS_LOCATION;
  RIGHTS_PERMISSION_STATUS_AND_EVIDENCE_REFS;
  REVIEWED_AUTHORITY_OR_EXTERNAL_AUTHORITY_RECEIPT;
  NO_HIDDEN_DEFAULT_OR_UA_DERIVATION_ASSERTION
TASK171_Q_OBSERVATION_REQUIRED_SUPPORT=
  EXACT_WALL_INTERFACE;
  PHYSICAL_EVENT_BOUNDED_SUPPORT;
  INTERVAL_OWNERSHIP;
  ONE_OBSERVATION_PER_OWNED_SUPPORT;
  NO_GLOBAL_TO_LOCAL_SPLIT_WITHOUT_AUTHORITY
TASK171_Q_OBSERVATION_REQUIRED_STATE_BINDINGS=
  LOCATED_UPSTREAM_FACE_OR_DOWNSTREAM_FACE_ENTHALPY;
  POSITIVE_MASS_FLOW;
  STREAM_ROLE;
  TUBE_OR_SHELL_SIDE;
  PHYSICAL_COORDINATE_AND_SUPPORT;
  STATE_LOCATION;
  AUTHORITY_ID_REVISION_AND_HASH

The present HeatObservation/Binding shape does not enforce the complete
external case-authority contract above, and no reviewed external Q receipt is
bound in the repository:

TASK171_Q_OBSERVATION_INPUT_ADMISSIBLE=true
TASK171_Q_OBSERVATION_CASE_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
EXTERNAL_Q_AUTHORITY_CONTRACT_ID=NONE

This is QUALIFIED_STRUCTURAL_Q_INPUT, not QUALIFIED_PHYSICAL_Q_PRODUCER.

## 9. Candidate F — TASK162 legacy q_method

The native TASK162 service computes the following dependency chain:

UA
  → NTU = UA / C_min
  → p_source = Table-7 relation(NTU, r_source, baffle_count)
  → q_method = p_source * C_cold * (T_hot_in - T_cold_in)
  → TASK162 hot/cold energy closure

The exact calculation is at predecessor blob
d20700eadc196cd04cb98236dcc4647f9e15558a, lines 818–847. The energy
closure at lines 637–702 derives/checks q_hot and q_cold from q_method; it
does not make the duty independent of the selected performance method.

TASK038's accepted UA composition is the relevant dependency boundary:
_success_result consumes the native tube film, shell film, wall resistance and
fouling resistance. Thus the TASK162 duty is a whole-exchanger, UA/film-
dependent legacy result. Its current implementation does not contain active
J_mu, but that absence cannot be promoted into future independence after any
J_mu rebind.

Q_SOURCE_ID=TASK162_Q_METHOD_WHOLE_EXCHANGER_LEGACY_CLOSURE
Q_SOURCE_LIFECYCLE=INHERITED_LEGACY_IMPLEMENTED_NOT_TASK172_Q_AUTHORITY
Q_SOURCE_PHYSICAL_MEANING=WHOLE_EXCHANGER_PERFORMANCE_METHOD_DUTY
Q_SOURCE_GRANULARITY=WHOLE_EXCHANGER
Q_SOURCE_SIGN_CONVENTION=LEGACY_POSITIVE_DUTY_UNDER_HOT_INLET_GREATER_THAN_COLD_INLET
Q_SOURCE_INPUTS=TASK160_CAPACITY_AND_INLET_STATES;TASK161_METHOD;TASK038_UA;CASE_BAFFLE_COUNT
Q_SOURCE_PROVENANCE_REQUIREMENTS=TASK162_RESULT_AND_SOURCE_DEFINITION_ID
Q_SOURCE_DEPENDS_ON_U=true
Q_SOURCE_DEPENDS_ON_TUBE_FILM=true_TRANSITIVELY_THROUGH_TASK038
Q_SOURCE_DEPENDS_ON_SHELL_FILM=true_TRANSITIVELY_THROUGH_TASK038
Q_SOURCE_DEPENDS_ON_JMU=NOT_IN_CURRENT_FORM;FUTURE_REBINDING_REQUIRES_NEW_AUTHORITY
Q_SOURCE_TASK172_SUPPORT_COMPATIBLE=false_NO_LOCAL_QTS_OR_SUPPORT_PROJECTION
Q_SOURCE_AUTHORITY_DISPOSITION=LEGACY_NATIVE_SCOPE_ONLY

No division by cell count, tube count, length, area, or numerical resolution
is authorized. That would manufacture a local Q and would change the
physical meaning of the legacy result.

## 10. Candidate G — TASK163 duty projection

TASK163 constructs Task163HeatDutyProjection by copying q_max, q_method,
q_hot and q_cold from the accepted TASK162 result at
e351b0052282efcdf30558342be7e4287e89cb52, lines 352–385. It does not
produce a new duty, change the whole-exchanger granularity, or remove the
TASK038 UA/film dependency.

Q_SOURCE_ID=TASK163_TASK162_DUTY_PROJECTION
Q_SOURCE_LIFECYCLE=DOWNSTREAM_PROJECTION_ONLY
Q_SOURCE_PHYSICAL_MEANING=REPLAYED_TASK162_WHOLE_EXCHANGER_DUTY
Q_SOURCE_GRANULARITY=WHOLE_EXCHANGER
Q_SOURCE_SIGN_CONVENTION=INHERITED_TASK162_DUTY_SEMANTICS
Q_SOURCE_INPUTS=ACCEPTED_TASK162_RESULT_AND_REPLAY_EVIDENCE
Q_SOURCE_PROVENANCE_REQUIREMENTS=TASK163_RESULT_AND_TASK162_IDENTITY
Q_SOURCE_DEPENDS_ON_U=true_INHERITED
Q_SOURCE_DEPENDS_ON_TUBE_FILM=true_TRANSITIVELY
Q_SOURCE_DEPENDS_ON_SHELL_FILM=true_TRANSITIVELY
Q_SOURCE_DEPENDS_ON_JMU=NOT_CURRENTLY_BOUND;FUTURE_REBINDING_WOULD_REQUIRE_AUTHORITY
Q_SOURCE_TASK172_SUPPORT_COMPATIBLE=false_NO_LOCAL_PROJECTION_AUTHORITY
Q_SOURCE_AUTHORITY_DISPOSITION=PROJECTION_ONLY_NOT_INDEPENDENT_Q

## 11. Candidate H and excluded families

No other accepted shell-and-tube TASK172 case-duty, measured-duty or
independent enthalpy producer was found in the current repository. The
following are explicitly not transferred:

DOUBLE_PIPE_CORE_HEAT_BALANCE_TO_TASK172_SHELL_TUBE=false
TASK169_REQUIRED_DUTY_TO_PHYSICAL_Q=false
TASK034_HEAT_DUTY_NOT_COMPUTABLE_TO_Q_PRODUCER=false
TASK033_HEAT_DUTY_NOT_COMPUTABLE_TO_Q_PRODUCER=false
TASK162_Q_METHOD_TO_LOCAL_QTS_WITHOUT_MAPPING=false
TASK163_Q_PROJECTION_TO_LOCAL_QTS_WITHOUT_MAPPING=false
CALLER_FIELD_NAME_Q_TO_AUTHORITY=false

These dispositions protect the family boundary and do not alter the native
contracts.

## 12. Q authority classification

The only calculated shell-tube duty available is TASK162's whole-exchanger
UA-dependent q_method, replayed by TASK163. TASK171 provides an admissible
structural observation slot but no physical case-duty producer, and no
independent case-duty or external-authority injection contract is bound.

To avoid conflating “legacy Q exists” with “TASK172 Q is qualified”, this
record uses two levels:

LEGACY_AVAILABLE_Q_AUTHORITY_BOUND=true_NATIVE_TASK162_SCOPE_ONLY
LEGACY_AVAILABLE_Q_SOURCE_IDS=TASK162_Q_METHOD_WHOLE_EXCHANGER_LEGACY_CLOSURE,TASK163_TASK162_DUTY_PROJECTION
LEGACY_AVAILABLE_Q_GRANULARITY=WHOLE_EXCHANGER
LEGACY_AVAILABLE_Q_IS_INDEPENDENT_OF_U=false
LEGACY_AVAILABLE_Q_IS_INDEPENDENT_OF_TUBE_FILM=false
LEGACY_AVAILABLE_Q_IS_INDEPENDENT_OF_SHELL_FILM=false
LEGACY_AVAILABLE_Q_IS_INDEPENDENT_OF_JMU=undetermined_FUTURE_REBINDING_NOT_SELECTED

QUALIFIED_Q_AUTHORITY_BOUND=false
Q_AUTHORITY_SOURCE_ID=NONE
Q_AUTHORITY_GRANULARITY=UNBOUND
Q_AUTHORITY_SIGN_CONVENTION_BOUND=false
Q_AUTHORITY_PHYSICAL_SUPPORT_BOUND=false
JMU_WALL_PRODUCER_HEAT_RATE_AUTHORITY_STATUS=ONLY_UA_DEPENDENT_LEGACY_Q_AVAILABLE_NOT_TASK172_QUALIFIED
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE_ID=NONE
JMU_WALL_PRODUCER_HEAT_RATE_SOURCE=TASK162_TASK163_WHOLE_EXCHANGER_UA_DEPENDENT_LEGACY_ONLY;NO_INDEPENDENT_OR_EXTERNAL_CASE_DUTY_BOUND
JMU_WALL_PRODUCER_HEAT_RATE_GRANULARITY=UNBOUND
DIRECT_CASE_DUTY_AUTHORITY_BOUND=false

The required outcome class is therefore:

OUTCOME=OUTCOME_D_ONLY_UA_DEPENDENT_Q_AVAILABLE
RESULT=BLOCKED

This does not invalidate TASK162 or TASK163. It records that their native
whole-exchanger duty cannot serve as the future J_mu radial-network Q without
a new authority for physical support, dependency and any projection.

## 13. Whole-exchanger versus local Q

The clean radial network requires a signed Q for its explicit local physical
support. A whole-exchanger legacy duty is not local. The following remain
false:

LOCAL_WALL_Q_REQUIRED_BY_RADIAL_NETWORK=true
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_REQUIRED=true
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_RULE=NONE
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_GRANULARITY=UNBOUND
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_DEPENDS_ON_PHYSICAL_SUPPORT=true
WHOLE_EXCHANGER_Q_DIVISION_BY_CELL_COUNT=false
WHOLE_EXCHANGER_Q_DIVISION_BY_AREA_OR_LENGTH=false
WHOLE_EXCHANGER_Q_REPEATED_PER_CELL=false

No local Q is fabricated from whole-exchanger duty. No cell, interval, area,
length, tube-count, baffle-count or mesh-resolution weighting is silently
chosen.

## 14. Dependency and circularity contribution

The Q-side audit yields these facts:

Q_AUTHORITY_IS_INDEPENDENT_OF_U=false
Q_AUTHORITY_IS_INDEPENDENT_OF_TUBE_FILM=false
Q_AUTHORITY_IS_INDEPENDENT_OF_SHELL_FILM=false
Q_AUTHORITY_IS_INDEPENDENT_OF_JMU=undetermined
Q_SIDE_CREATES_JMU_COUPLING=undetermined

The first three false values describe the only available calculated legacy Q
path (TASK162/TASK163), not a selected TASK172 authority. The final
undetermined values are required because no Q has been selected for the future
producer and the preliminary shell-film choice remains out of scope.

The overall conditional graph is preserved without execution:

selected Q or preliminary shell film
  → clean radial wall state
  → shell-fluid wall viscosity
  → J_mu
  → corrected shell film or downstream duty

JMU_WALL_COUPLING_CIRCULARITY_PATH_IDENTIFIED=true
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
JMU_WALL_COUPLING_CLOSURE_AUTHORITY_BOUND=false
JMU_WALL_COUPLING_ITERATION_AUTHORIZED=false

The legacy UA dependency demonstrates a possible Q-side coupling path, but
does not by itself prove that a future preliminary film or active J_mu closure
must use it.

## 15. Preserved out-of-scope state

This Q-only gate does not alter the following:

PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
WALL_PRODUCER_MATERIAL_PROFILE_ID=NONE
WALL_PRODUCER_K_WALL_TEMPERATURE_DOMAIN_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
SOURCE_BULK_STATE_AVAILABLE_IN_TASK172=false
SOURCE_BULK_STATE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_RE_DOMAIN_SOURCE_BOUND=false
JMU_PR_DOMAIN_SOURCE_BOUND=false
JMU_VISCOSITY_RATIO_DOMAIN_SOURCE_BOUND=false
JMU_TEMPERATURE_DOMAIN_SOURCE_BOUND=false

The inherited TASK171 sign convention remains usable as a structural input
contract, but it is not a case-duty source:

TASK171_Q_OBSERVATION_INPUT_ADMISSIBLE=true
TASK171_Q_OBSERVATION_CASE_AUTHORITY_BOUND=false

## 16. Decision and next gate

The result is correctly blocked because the repository has no
TASK172-qualified signed Q. It has one UA-dependent legacy whole-exchanger
producer and one structural caller-observation slot, neither of which can be
reinterpreted as a local wall-network Q.

RESULT=BLOCKED
OUTCOME=OUTCOME_D_ONLY_UA_DEPENDENT_Q_AVAILABLE
JMU_Q_AUTHORITY_CANDIDATE_CREATED=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_IMMEDIATE_Q_GAP=EXPLICIT_EXTERNAL_OR_CASE_BOUND_SIGNED_Q_AUTHORITY
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_AUTHORITY_CONTRACT_R3_ONLY

The next gate must define and independently review only an external/case-bound
Q contract (or a source-backed Q producer), including its physical support,
granularity, sign, provenance, and dependency. It must not use the next gate
to select a preliminary film, solve a fixed point, or implement a wall
temperature.

The four effective TASK172 entry blockers remain unchanged:

REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false

## 17. Governance and immutable boundaries

HISTORICAL_RECORDS_REWRITTEN=false
ENGINEERING_RULES_CHANGED=false
TASK166_CHANGED=false
TASK171_SEMANTICS_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
WALL_TEMPERATURE_SOLVE_EXECUTED=false
FIXED_POINT_ITERATION_PERFORMED=false
BLOCKER_REMOVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true

Only this document, its machine-readable evidence and one append-only registry
extension are in scope.

## 18. Final receipt

TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_Q_AUTHORITY_R2
RESULT=BLOCKED
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=9f9ee9cc5486ea531c2a6addbaa9f439dc4401fb
FINAL_HEAD_SHA=TO_BE_RECORDED_AFTER_COMMIT
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
Q_AUTHORITY_SOURCE_ID=NONE
QUALIFIED_Q_AUTHORITY_GRANULARITY=UNBOUND
Q_AUTHORITY_SIGN_CONVENTION_BOUND=false
Q_AUTHORITY_PHYSICAL_SUPPORT_BOUND=false
DIRECT_CASE_DUTY_AUTHORITY_BOUND=false
TUBE_ENTHALPY_DUTY_INPUTS_BOUND=false
TUBE_ENTHALPY_DUTY_AUTHORITY_BOUND=false
SHELL_ENTHALPY_DUTY_INPUTS_BOUND=false
SHELL_ENTHALPY_DUTY_AUTHORITY_BOUND=false
TWO_SIDE_DUTY_RECONCILIATION_AUTHORITY_BOUND=false
TASK171_Q_OBSERVATION_INPUT_ADMISSIBLE=true
TASK171_Q_OBSERVATION_CASE_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_REQUIRED=true
Q_AUTHORITY_IS_INDEPENDENT_OF_U=false
Q_AUTHORITY_IS_INDEPENDENT_OF_TUBE_FILM=false
Q_AUTHORITY_IS_INDEPENDENT_OF_SHELL_FILM=false
Q_AUTHORITY_IS_INDEPENDENT_OF_JMU=undetermined
Q_SIDE_CREATES_JMU_COUPLING=undetermined
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_Q_AUTHORITY_CANDIDATE_CREATED=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
LOCAL_VALIDATION=TO_BE_RECORDED
EXACT_FINAL_HEAD_CI_RUN=TO_BE_RECORDED
EXACT_FINAL_HEAD_CI=TO_BE_RECORDED
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_AUTHORITY_CONTRACT_R3_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
