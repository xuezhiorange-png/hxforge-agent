# TASK172 v0.7 — Jμ bulk-property pressure-rule authority resolution R1

## 1. Receipt and hard boundary

```ini
TASK_ID=TASK172_V0_7_JMU_BULK_PRESSURE_RULE_AUTHORITY_RESOLUTION_R1
MODE=TARGETED_JMU_SOURCE_MEAN_PRESSURE_RULE_AUTHORITY_RESOLUTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=c7c2a9630364ad7543ba51b11a530fdbf3e9ee19
HEAD_PRECONDITION_VERIFIED=true
RESULT=BLOCKED_JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
```

This gate resolves only whether an accepted authority defines the pressure
state to pair with the whole-exchanger shell-stream source-mean bulk property
state used by the native TASK166/Jamil/Thome `J_mu` lineage. It does not
choose a pressure convention, create a pressure authority, or create any
state, property snapshot, executable, or numerical method.

The PR was verified as open and draft at the authorized predecessor head before
the append-only artifacts were written. The final head is recorded after the
append-only commit in the final receipt.

## 2. Historical and scope boundary

R71 through R81 documents, evidence, and registry extensions are historical
payloads. They are not rewritten. This record reuses their already recorded
source findings; it does not reopen broad Bell, HEDH, ASME, Thome, Jamil, or
Gonçalves searches.

The accepted state entering this gate remains:

```ini
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
SOURCE_MEAN_ENDPOINT_PAIR_PREDICATE_SATISFIED=true
SOURCE_MEAN_PROPERTY_AUTHORITY_PREDICATE_SATISFIED=true
SOURCE_MEAN_IDENTITY_PROVENANCE_PREDICATE_SATISFIED=true
SOURCE_MEAN_FAIL_CLOSED_PREDICATE_SATISFIED=true
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
PRESSURE_IS_PROVEN_SOLE_MODEL_LEVEL_BLOCKER=true
TEMPERATURE_OPERATOR_DOES_NOT_IMPLY_PRESSURE_OPERATOR=true
```

## 3. Target definition

The target pressure rule would have to state how pressure is selected or
paired when evaluating shell-side bulk properties for the whole-exchanger
source-mean state:

```text
WHOLE_EXCHANGER_SHELL_STREAM_MEAN_OF_SOURCE_INLET_AND_OUTLET_BULK_STATE
```

The following do not meet that definition by themselves: pressure-drop
equations, pressure-loss measurement conventions, mechanical/design pressure,
operating pressure listed as an input, endpoint pressure fields, an arithmetic
mean inferred by convenience, or a backend interface requirement. The accepted
temperature operator likewise does not imply a pressure operator.

## 4. Reused authority audit

The structured evidence binds the exact source identities, body hashes, rights
boundaries, locations, and transfer scopes from the earlier append-only
records. R78 reviewed five relevant acquired bodies; R79 added the exact HEDH
lineage body as a sixth reviewed body. Bell 1963 and Bell 1988 remain the
unavailable lineage targets recorded by R80 and R81. The acquired sources were
inspected only for the target pressure semantics already defined by R78 and
the subsequent lineage records; no new unled source search was performed in
this gate.

The resulting audit is:

```ini
PRESSURE_RULE_SOURCE_ACQUIRED=false
PRESSURE_RULE_SOURCE_ID=NONE
PRESSURE_RULE_BODY_SHA256=NONE
PRESSURE_RULE_EXACT_LOCATION=NONE
PRESSURE_RULE_TYPE=UNRESOLVED
PRESSURE_RULE_SEMANTICS=NO_SCOPE_COMPATIBLE_SOURCE_MEAN_PROPERTY_PRESSURE_RULE;PRESSURE_DROP_AND_TEST_MEASUREMENT_CONTEXT_NON_TRANSFERABLE
PRESSURE_RULE_TRANSFERABLE_TO_TASK172_NATIVE_JMU=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
PRESSURE_INSENSITIVITY_SOURCE_ID=NONE
PRESSURE_INSENSITIVITY_DOMAIN=NONE
PRESSURE_INSENSITIVITY_ACCEPTANCE_RULE=NONE
```

No source statement was found that pairs inlet pressure, outlet pressure,
arithmetic-mean pressure, local bulk pressure, representative shell pressure,
or another pressure value with the Jμ source-mean property state. No source
provides a domain-qualified pressure-insensitivity rule with an acceptance
boundary. No backend was called and no pressure response was inferred.

## 5. Rejected candidate ledger

The rejection ledger is explicit so that an engineering default cannot be
silently promoted:

| Candidate | Disposition | Reason |
| --- | --- | --- |
| Pressure-drop or test-measurement pressure | Rejected | The reviewed statements describe hydraulic/test quantities, not pressure paired with Jμ bulk-property evaluation. |
| Operating/design pressure | Rejected | An input or design quantity is not a source-defined property-evaluation convention. |
| Inlet pressure | Rejected | No reviewed source assigns it to the whole-exchanger source-mean property state. |
| Outlet pressure | Rejected | No reviewed source assigns it to the whole-exchanger source-mean property state. |
| Arithmetic mean of endpoint pressures | Rejected | It would be an unsupported construction; no source authority was found. |
| Representative or constant shell pressure | Rejected | No exact source rule and no domain-qualified acceptance rule were found. |
| Pressure-insensitivity from small expected property variation | Rejected | No source-backed domain, property set, approximation boundary, or acceptance rule; no property backend was called. |
| Bell 1963 / Bell 1988 body-derived rule | Not accepted as authority | The exact bodies remain unavailable in R80/R81, so no rule text can be reviewed or transferred. |
| HEDH §3.3 lineage rule | Not accepted as authority | R79 records no pressure pairing in the acquired target body; it remains a temperature-text-only lineage finding. |

These are not competing pressure conventions. They are non-authoritative or
out-of-scope candidates, so no source conflict exists to adjudicate.

## 6. Pressure-insensitivity route

The property authority `V07-T172-WATER-PROPERTY-PROFILE-R2` remains a narrow
reviewed compatibility authority with scope
`PURE_ORDINARY_WATER;HEOS;CoolProp 8.0.0;DEF;STABLE_SINGLE_PHASE_LIQUID` and
domain `T=298.15..300 K;P=100000..101325 Pa`. It does not define a source-mean
pressure rule. Its existence cannot be converted into pressure insensitivity,
and it does not authorize a property snapshot or backend call.

## 7. Predicate and lifecycle disposition

No lawful direct pressure rule or pressure-insensitivity rule was found. The
model-level pressure predicate therefore remains the sole blocker, while no
pressure authority candidate is created:

```ini
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
PRESSURE_IS_PROVEN_SOLE_MODEL_LEVEL_BLOCKER=true
SOURCE_MEAN_MODEL_LEVEL_AUTHORITY_CANDIDATE_ELIGIBLE=false
JMU_BULK_PRESSURE_RULE_AUTHORITY_CANDIDATE_CREATED=false
JMU_BULK_PRESSURE_RULE_AUTHORITY_ID=NONE
JMU_BULK_PRESSURE_RULE_AUTHORITY_LIFECYCLE=NONE
JMU_BULK_PRESSURE_RULE_INDEPENDENT_REVIEW=NONE
```

This conclusion is `NO_ACCEPTABLE_AUTHORITY_FOUND`; it does not claim that
pressure is irrelevant and does not select a default. A future authority
resolution gate may separately inspect a newly authorized direct source lead.

## 8. Real-instance and downstream guards

No model-level pressure finding creates a real state or advances a downstream
branch:

```ini
SOURCE_MEAN_MODEL_LEVEL_AUTHORITY_CANDIDATE_ELIGIBLE=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
REAL_REVIEWED_SHELL_INLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_OUTLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_ENDPOINT_PAIR_PRODUCER_FOUND=false
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No endpoint state, source-mean state, property snapshot, Q authority, film
authority, wall producer, Jμ executable, numerical method, or mesh study is
created or authorized.

## 9. Governance and stop

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
PRESSURE_RULE_SELECTED=false
PRESSURE_AUTHORITY_CREATED=false
PROPERTY_BACKEND_CALLED=false
JMU_EXECUTED=false
WALL_STATE_SOLVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The exact source records, hashes, rights boundaries, rejected candidates, and
validation result are machine-readable in the companion evidence artifact.
