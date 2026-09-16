# TASK172 external signed-Q authority contract R3

## 1. Receipt and scope

This documentation/evidence-only package defines the authority contract for
an external or case-bound signed heat-rate input that a future TASK172
Jamil/Thome J_mu wall-temperature producer may consume. It defines the
required receipt shape, provenance, physical support, dependency declaration,
and lifecycle. It does not create a duty, select a Q value, create a Q
producer, solve a wall state, select a preliminary film, select material or
k_wall, localize a whole-exchanger duty, implement J_mu, modify TASK162,
TASK163, TASK166, or change production code.

TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_AUTHORITY_CONTRACT_R3
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=e94d8eb5c1b236569d65196be7245de22715d461
MODE=EXTERNAL_CASE_BOUND_SIGNED_Q_AUTHORITY_CONTRACT_ONLY
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

## 2. Effective predecessor and dependency clarification

The R2 audit found no TASK172-qualified Q authority. It found only the
following native legacy path:

TASK162 Q_METHOD:
TASK038_UA -> NTU=UA/C_min -> TASK162_TABLE7_P -> q_method
-> TASK162_ENERGY_CLOSURE

This path is available in TASK162's native whole-exchanger scope, but it is
not independent of UA, tube film, shell film, or wall/fouling resistance and
does not provide a local wall-support Q. TASK163 projects TASK162 duty fields;
it is not a new Q producer.

The effective dependency semantics are therefore split as follows:

QUALIFIED_Q_AUTHORITY_DEPENDENCY_STATUS=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_ID=TASK162_Q_METHOD
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_U=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_TUBE_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_SHELL_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_JMU_DEPENDENCY=FUTURE_REBINDING_UNDETERMINED

The four fields above describe the best available legacy producer only. They
must not be read as dependency findings for a selected qualified Q, because
no such Q exists.

## 3. Contract disposition

The external-Q contract is complete as a model-level receipt contract, but
there is no external-Q instance in this task:

RESULT=RESOLVED
OUTCOME=OUTCOME_A_EXTERNAL_Q_CONTRACT_COMPLETE_NO_INSTANCE
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_ID=V07-T172-EXTERNAL-SIGNED-Q-INPUT-AUTHORITY-CONTRACT-R3
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
EXTERNAL_Q_AUTHORITY_CONTRACT_CANDIDATE_CREATED=true
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
EXTERNAL_Q_INSTANCE_PRESENT=false
LIFECYCLE_PROMOTION_PERFORMED=false

The word complete in this section applies only to the contract shape. It
does not mean that a caller's number is accepted, that an external producer
has been reviewed, or that TASK172 runtime can currently inject the value.

## 4. External Q classes and disposition

The contract evaluates external Q classes separately. A class is potentially
admissible only after a real instance supplies all required evidence and an
independent review accepts that instance. No class is accepted by this
document.

| Class | Potential use | Required condition | Current disposition |
| --- | --- | --- | --- |
| MEASURED_HEAT_RATE | measured signed heat rate over explicit support | instrument/method, calibration or status where applicable, measurement interval, case/topology/support binding, source and evidence receipt | contract defined; no instance |
| CASE_SPECIFIED_RATED_DUTY | case-specified physical duty | must be an actual signed heat-rate input for the exact case, not required duty, design target, or selection threshold | contract defined; no instance |
| INDEPENDENT_ENERGY_BALANCE | Q derived from source-bound mass and enthalpy states | located states, property authority, equation identity, sign, support, and independent review | contract defined; no instance |
| EXTERNAL_ENGINEERING_CALCULATION | imported calculation result | complete producer identity and affirmative dependency declaration; unknown dependencies fail closed | contract defined; no instance |
| CALLER_ASSERTION_WITHOUT_PROVENANCE | bare user-supplied number | none | rejected |
| UA_OR_HTC_DERIVED_EXTERNAL_CALCULATION | imported Q derived from UA or HTC | may be described as an external calculation only with declared dependencies; it is not independent Q and cannot erase the J_mu coupling question | not an independent-Q authority |

An external calculation that depends on U, either film, J_mu, wall
conductivity, or another unresolved authority may still be recorded as a
declared input candidate, but it cannot be classified as independent of that
dependency. If dependency provenance is unknown, the instance is blocked.

## 5. Physical quantity contract

Every proposed receipt must bind the physical quantity before any lifecycle
promotion:

Q_QUANTITY_TYPE=HEAT_RATE
Q_UNIT=W
Q_SIGN_CONVENTION=TASK171_HOT_TO_COLD
Q_SIGN_RULE=Q>0_MEANS_HEAT_FLOW_FROM_HOT_STREAM_TO_COLD_STREAM
EXTERNAL_Q_PHYSICAL_MEANING=SIGNED_HEAT_RATE_ACROSS_EXACT_PHYSICAL_SUPPORT

An unsigned absolute duty, magnitude-only value, or value with an unstated
orientation is rejected unless a separate reviewed sign-mapping authority
exists. No abs(Q), cell-count division, area division, length division, tube
count division, or mesh-resolution division is permitted.

The actual signed value is a field of a future instance receipt only. This
contract intentionally contains no Q value.

## 6. Case, topology, and support binding

The receipt must identify the exact computational and physical object to
which Q applies:

CASE_CONFIGURATION_ID
CASE_CONFIGURATION_HASH
CASE_REVISION
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_SUPPORT_TYPE
PHYSICAL_SUPPORT_ID
PHYSICAL_SUPPORT_INTERVAL_ID
WALL_INTERFACE_ID
PHYSICAL_SUPPORT_START
PHYSICAL_SUPPORT_END
PHYSICAL_SUPPORT_GEOMETRY_ID
STREAM_ROLE_AND_SIDE_ASSIGNMENT
HOT_COLD_ROLE_ASSIGNMENT

Allowed support types are WHOLE_EXCHANGER, PHYSICAL_INTERVAL, CELL,
WALL_INTERFACE, or another explicitly described support. A whole-exchanger
Q is not a wall-interface Q. A Q attached to one topology cannot be reused
for another physical interval or mesh decomposition. A local Q is admissible
only when the receipt itself binds the local support; this contract does not
authorize a whole-to-local mapping.

Names with similar text are not sufficient for case, topology, geometry, or
support identity. Every identity is hash-bound where a canonical identity
exists, and mismatch is fail closed.

## 7. Granularity and mapping

The receipt must declare exactly one granularity:

EXTERNAL_Q_GRANULARITY=WHOLE_EXCHANGER | PHYSICAL_INTERVAL | CELL | WALL_INTERFACE | OTHER_EXPLICIT_SUPPORT

The declared granularity must agree with the physical support. The following
are forbidden:

* treating whole-exchanger Q as local wall Q;
* dividing Q by cell count, tube count, area, length, or mesh resolution;
* repeating the same Q on every cell;
* interpolating or averaging Q over support without an independently reviewed
  mapping rule;
* crossing a native physical-event boundary.

Therefore:

GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_REQUIRED=true
LOCAL_Q_IS_ACCEPTABLE_ONLY_WITH_EXACT_SUPPORT=true

This R3 contract does not create the missing mapping authority.

## 8. Producer and source provenance

Every future receipt must bind all of the following:

EXTERNAL_Q_SOURCE_ID
EXTERNAL_Q_SOURCE_REVISION
EXTERNAL_Q_SOURCE_CLASS
EXTERNAL_Q_SOURCE_LOCATION
EXTERNAL_Q_PRODUCER_OR_MEASUREMENT_METHOD
EXTERNAL_Q_AUTHORITY_OWNER
EXTERNAL_Q_EVIDENCE_REFERENCES
EXTERNAL_Q_SOURCE_RIGHTS_STATUS
EXTERNAL_Q_EVIDENCE_REVIEW_PERMISSION_STATUS

“Provided by user”, a bare grade/name, an opaque database row, or a caller
assertion is not a source-bound producer identity. Library availability and
runtime database lookup are not engineering authority.

For measured Q, the receipt additionally records instrument or measurement
method identity, measurement interval, calibration/status where applicable,
timestamp or event binding, and any source-governed uncertainty or accuracy
metadata. This contract invents no uncertainty threshold.

For an independently calculated Q, the receipt records mass-flow identities,
located inlet/outlet enthalpy state identities, property authority identities,
the exact equation identity, sign transformation, and physical support. The
contract does not execute that balance.

## 9. Dependency and independence contract

The producer must affirmatively declare each dependency:

DEPENDS_ON_U
DEPENDS_ON_TUBE_FILM
DEPENDS_ON_SHELL_FILM
DEPENDS_ON_JMU
DEPENDS_ON_WALL_K
OTHER_DEPENDENCIES

Unknown is not equivalent to false. The receipt is blocked until a producer
or measurement method supports each declared value. A future instance may
report true, false, or a source-qualified conditional state:

EXTERNAL_Q_IS_INDEPENDENT_OF_U
EXTERNAL_Q_IS_INDEPENDENT_OF_TUBE_FILM
EXTERNAL_Q_IS_INDEPENDENT_OF_SHELL_FILM
EXTERNAL_Q_IS_INDEPENDENT_OF_JMU

Independence must be affirmative and source-supported. The absence of a
dependency field does not establish independence.

The current effective repository state remains:

Q_AUTHORITY_IS_INDEPENDENT_OF_U=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
Q_AUTHORITY_IS_INDEPENDENT_OF_TUBE_FILM=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
Q_AUTHORITY_IS_INDEPENDENT_OF_SHELL_FILM=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
Q_AUTHORITY_IS_INDEPENDENT_OF_JMU=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY

This corrects the R2 semantic ambiguity without rewriting R2.

## 10. Lifecycle and review

The contract defines the following lifecycle for an actual external Q
receipt:

PROPOSED_EXTERNAL_Q_AUTHORITY
REVIEWED_EXTERNAL_Q_AUTHORITY
ACCEPTED_EXTERNAL_Q_AUTHORITY
REJECTED_EXTERNAL_Q_AUTHORITY

Production consumption requires an accepted instance under repository
governance. Contract creation is not instance review. Codex performs no
lifecycle promotion in this task.

The required review edges are:

contract candidate
-> independent review of contract shape
-> real case-bound Q receipt
-> independent review of the receipt
-> accepted external Q authority
-> future runtime support and admission enforcement

The final edge is not implemented here:

EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false

## 11. Immutable instance receipt shape

A future instance receipt must contain at least:

EXTERNAL_Q_AUTHORITY_RECEIPT_ID
SCHEMA_VERSION
SOURCE_ID
SOURCE_REVISION
SOURCE_CLASS
SOURCE_LOCATION
CASE_CONFIGURATION_ID
CASE_CONFIGURATION_HASH
CASE_REVISION
TASK171_TOPOLOGY_ID
TASK171_TOPOLOGY_HASH
PHYSICAL_SUPPORT_TYPE
PHYSICAL_SUPPORT_ID
PHYSICAL_SUPPORT_INTERVAL_ID
WALL_INTERFACE_ID
SIGNED_Q_W
Q_QUANTITY_TYPE
Q_UNIT
Q_SIGN_CONVENTION
GRANULARITY
PRODUCER_OR_MEASUREMENT_METHOD
DEPENDENCY_DECLARATION
EVIDENCE_REFERENCES
RIGHTS_STATUS
LIFECYCLE_STATUS
CANONICAL_HASH

The contract does not create this receipt, assign an ID to an actual case,
or populate SIGNED_Q_W.

The canonical preimage must include schema/version, all case/topology/support
identities, the signed value and units, producer/source/provenance/rights,
dependency declaration, granularity, sign semantics, lifecycle fields, and
all source-bound evidence references. Any change to Q, source revision,
case/configuration, topology, physical support, granularity, dependency
declaration, or lifecycle must produce a new identity. The canonical hash
field itself is excluded only by the shared canonical_json helper.

## 12. TASK171 Binding boundary

TASK171 Binding currently carries opaque authority_id, revision,
evidence_refs, and source_hash metadata. That is sufficient to point at a
future receipt as evidence metadata, but it does not carry or validate the
complete external-Q case, topology, support, producer, dependency, or
lifecycle contract.

Therefore:

TASK171_BINDING_CAN_REFERENCE_EXTERNAL_Q_RECEIPT=false
TASK171_BINDING_REFERENCE_DISPOSITION=OPAQUE_EVIDENCE_REFERENCE_ONLY
FUTURE_IMPLEMENTATION_SCHEMA_GATE_REQUIRED=true

No TASK171 production schema or service is changed by this document.

## 13. Fail-closed admission rules

Any missing or inconsistent item blocks the future receipt:

* missing physical meaning, unit, sign, or granularity;
* missing case/configuration identity or hash;
* missing exact TASK171 topology identity or hash;
* missing exact physical support, interval, or wall interface;
* whole-to-local use without a separate reviewed mapping;
* missing source/producer identity or evidence;
* missing rights/review permission status where required;
* unknown producer dependency;
* caller assertion, hidden/default Q, or runtime database lookup;
* source, case, topology, geometry, support, or hash mismatch;
* unsupported interpolation, extrapolation, or support averaging;
* unreviewed lifecycle state;
* unsigned or absolute-only duty.

The gate must report BLOCKED rather than returning the last available value
or silently choosing a fallback.

## 14. Preserved TASK172 scope

This contract changes none of the following:

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

No Q instance is available, so the contract cannot decide whether a future
wall producer is independent of active J_mu. It defines the information
needed to make that decision later.

## 15. Effective entry state and governance

The canonical TASK172 entry blockers remain exactly:

REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false

HISTORICAL_RECORDS_REWRITTEN=false
ENGINEERING_RULES_CHANGED=false
TASK162_CHANGED=false
TASK163_CHANGED=false
TASK166_CHANGED=false
TASK171_SEMANTICS_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
WALL_TEMPERATURE_SOLVE_EXECUTED=false
FIXED_POINT_ITERATION_PERFORMED=false
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true

## 16. Decision and next gate

The model-level receipt contract is complete, but no actual external Q
authority exists. The shell-wall blocker therefore remains open/blocked.

RESULT=RESOLVED
OUTCOME=OUTCOME_A_EXTERNAL_Q_CONTRACT_COMPLETE_NO_INSTANCE
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
QUALIFIED_Q_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_CONTRACT_CANDIDATE_CREATED=true
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_RECEIPT_INDEPENDENT_REVIEW_R1_ONLY

The next gate is limited to independent review of a real, case-bound
external-Q receipt when one exists. It must not be interpreted as permission
to create a Q, implement injection, choose films or materials, solve a wall
state, or perform numerical work.

## 17. Final receipt

TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_AUTHORITY_CONTRACT_R3
RESULT=RESOLVED
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=e94d8eb5c1b236569d65196be7245de22715d461
FINAL_HEAD_SHA=TO_BE_RECORDED_AFTER_COMMIT
QUALIFIED_Q_AUTHORITY_BOUND=false
QUALIFIED_Q_AUTHORITY_DEPENDENCY_STATUS=NOT_APPLICABLE_NO_QUALIFIED_Q_AUTHORITY
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_ID=TASK162_Q_METHOD
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_U=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_TUBE_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_DEPENDS_ON_SHELL_FILM=true
BEST_AVAILABLE_INTERNAL_Q_PRODUCER_JMU_DEPENDENCY=FUTURE_REBINDING_UNDETERMINED
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
EXTERNAL_Q_PHYSICAL_MEANING_BOUND=true
EXTERNAL_Q_UNIT_BOUND=true
EXTERNAL_Q_SIGN_CONVENTION_BOUND=true
EXTERNAL_Q_CASE_IDENTITY_BOUND=true
EXTERNAL_Q_TOPOLOGY_IDENTITY_BOUND=true
EXTERNAL_Q_PHYSICAL_SUPPORT_BOUND=true
EXTERNAL_Q_GRANULARITY_BOUND=true
EXTERNAL_Q_SOURCE_IDENTITY_BOUND=true
EXTERNAL_Q_PRODUCER_METHOD_BOUND=true
EXTERNAL_Q_DEPENDENCY_DECLARATION_BOUND=true
EXTERNAL_Q_AUTHORITY_LIFECYCLE_BOUND=true
MEASURED_Q_AUTHORITY_CONTRACT_COMPLETE=true
EXTERNAL_ENERGY_BALANCE_Q_CONTRACT_COMPLETE=true
TASK171_BINDING_CAN_REFERENCE_EXTERNAL_Q_RECEIPT=false
EXTERNAL_Q_AUTHORITY_CONTRACT_CANDIDATE_CREATED=true
EXTERNAL_Q_INSTANCE_PRESENT=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
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
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_EXTERNAL_Q_RECEIPT_INDEPENDENT_REVIEW_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
