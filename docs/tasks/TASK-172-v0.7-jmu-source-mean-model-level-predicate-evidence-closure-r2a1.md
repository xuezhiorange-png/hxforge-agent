# TASK172 — Jμ source-mean model-level predicate evidence closure R2A1

## 1. Receipt

```ini
TASK_ID=TASK172_V0_7_JMU_SOURCE_MEAN_MODEL_LEVEL_PREDICATE_EVIDENCE_CLOSURE_R2A1
MODE=APPEND_ONLY_MACHINE_EVIDENCE_CLOSURE_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=106878ad0e711443459f12059ce666d6c1206622
HEAD_PRECONDITION_VERIFIED=true
HISTORICAL_PAYLOADS_IMMUTABLE=true
```

This receipt audits the six model-level candidate predicates declared by the
R2A correction. It does not create a source-mean authority candidate, an
endpoint producer, an endpoint state, a property snapshot, or a real source
mean. It does not acquire or select a pressure convention.

The audit uses only repository records already present at the predecessor
head. A predicate is not treated as proven merely because the R2A required
predicate list contains the corresponding string.

## 2. Historical immutability

The following historical payloads are inputs to this closure and were not
rewritten:

| Record | Existing evidence |
| --- | --- |
| R71 source-mean aggregation record | `r71_extension`, canonical `0d422248cd375bd752bd84d6aeed5cea6fbc458db40f4361aa5cb66312657008` |
| R2A instance/dependency correction | `r72_extension`, canonical `7de8acc0bf4dabc0ab01056fe696aa2dff30dae4e66fbf12831c5fcb3400f638` |
| Reviewed shell endpoint-pair contract | `r59_extension`, canonical `84f31d5f52d598230eb422f0fd0748c64c411bb263a04da10e192ad312823b4b` |
| Reviewed water property profile | R3 independent-review receipt, canonical `fc72a78ac15a4a5700d395b6cb568fa3288f311174e0b0b52e399ab8612c0699` |

```ini
R71_ORIGINAL_DOCUMENT_CHANGED=false
R71_ORIGINAL_EVIDENCE_CHANGED=false
R71_EXTENSION_REWRITTEN=false
R2A_ORIGINAL_DOCUMENT_CHANGED=false
R2A_ORIGINAL_EVIDENCE_CHANGED=false
R72_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
```

## 3. Predicate adjudication

The machine-readable matrix is in the paired evidence JSON. The decisive
results are:

| Predicate | Satisfied | Adjudication |
| --- | --- | --- |
| `SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND` | `true` | R71 binds the transferred arithmetic temperature operator and its source location; R72 preserves it. |
| `JMU_BULK_PRESSURE_RULE_BOUND` | `false` | R71 and R72 explicitly retain no pressure rule and no pressure-insensitivity authority. |
| `PAIR_TRANSFER_CONTRACT_STATUS` | `true` | R59 independently promotes the model-level endpoint-pair contract to `REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT`; no real pair is implied. |
| `JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID` | `true` | The water profile has reviewed lifecycle, exact reviewed payload hash, backend/version/reference/phase/domain scope, and R71/R59 bind it only as a conditional narrow-scope property authority. No snapshot is created. |
| `SOURCE_MEAN_IDENTITY_AND_PROVENANCE_SCHEMA_BOUND` | `true` | R71's future producer shape explicitly enumerates the required identity, endpoint-reference, property, producer-lifecycle, provenance, and canonical-hash fields. This is schema-level evidence only; the full producer contract remains false. |
| `SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND` | `undetermined` | R59 enumerates fail-closed rules for the endpoint-pair input, while R57/R71 name a future `FAIL_CLOSED_RULES` field without defining source-mean candidate coverage. No existing record maps the endpoint rules to every source-mean admission failure listed by this gate. |

Therefore the pressure rule is not proven to be the sole unmet predicate.
The source-mean fail-closed predicate is an additional model-level gap.

## 4. Temperature predicate

The R71 source adjudication records:

```ini
SOURCE_MEAN_TEMPERATURE_OPERATOR_AUTHORITY_FOUND=true
SOURCE_MEAN_TEMPERATURE_OPERATOR=(T_shell_in + T_shell_out) / 2; ARITHMETIC_MEAN
SOURCE_MEAN_TEMPERATURE_OPERATOR_SOURCE_ID=ASME-PTC-12.5-2000-R2015-PUBLIC-COPY
SOURCE_MEAN_TEMPERATURE_OPERATOR_TRANSFERABLE_TO_TASK172_NATIVE_JMU=true
JMU_BULK_TEMPERATURE_AGGREGATION_RULE_BOUND=true
SOURCE_MEAN_BULK_TEMPERATURE_OPERATOR_CONTRACT_BOUND=true
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
```

This receipt does not re-research or broaden that transfer. The evidence is
the existing R71 source adjudication in
`docs/tasks/TASK-172-v0.7-authority-registry-r1.json` at
`r71_extension.source_adjudication`, canonical
`0d422248cd375bd752bd84d6aeed5cea6fbc458db40f4361aa5cb66312657008`, and the
R71 evidence object at
`evidence/TASK-172-jmu-source-mean-bulk-state-aggregation-and-endpoint-binding-r2.json#/temperature_operator_adjudication`.

## 5. Pressure predicate

The current source records explicitly preserve the missing pressure authority:

```ini
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE=NONE
JMU_BULK_PRESSURE_RULE_BOUND=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
```

No pressure convention is selected or inferred here. In particular, this
receipt does not introduce inlet pressure, outlet pressure, arithmetic-mean
pressure, representative pressure, constant-pressure treatment, pressure
insensitivity, or a backend default.

Evidence is R71 `source_adjudication` and R72 `pressure_state`, with the
canonical hashes recorded in the matrix.

## 6. Reviewed endpoint-pair predicate

The endpoint input contract is a model-level reviewed contract, not a real
state pair:

```ini
PAIR_TRANSFER_CONTRACT_STATUS=REVIEWED_JMU_SHELL_ENDPOINT_STATE_PAIR_CONTRACT
SOURCE_MEAN_USES_REVIEWED_ENDPOINT_PAIR_CONTRACT=true
SOURCE_MEAN_ENDPOINT_PAIR_PREDICATE_SATISFIED=true
REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false
REAL_ENDPOINT_PAIR_REQUIRED_FOR_MODEL_LEVEL_SOURCE_MEAN_CONTRACT=false
REAL_ENDPOINT_PRODUCER_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
REAL_ENDPOINT_PAIR_REQUIRED_FOR_REAL_SOURCE_MEAN_INSTANCE=true
```

The R59 independent-review receipt explicitly promotes only the model-level
pair contract. Its pair fields bind case, stream, topology, path, endpoint
identity, property authority/snapshot, producer lifecycle, provenance, and
canonical identity. Its real-instance guards remain false. No endpoint value
is created by this closure.

## 7. Property-authority predicate

`JMU_BULK_PROPERTY_AUTHORITY_COMPATIBLE=true` is not used as the sole basis for
this finding. The existing evidence chain also contains:

* proposal payload `V07-T172-WATER-PROPERTY-PROFILE-R2`, canonical
  `8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de`;
* R3 independent-review decision for that exact payload,
  `effective_review_status=REVIEWED_AUTHORITY`, with receipt canonical
  `fc72a78ac15a4a5700d395b6cb568fa3288f311174e0b0b52e399ab8612c0699`;
* exact reviewed scope: pure ordinary water, HEOS, CoolProp 8.0.0, DEF,
  stable single-phase liquid, `T=298.15..300 K`,
  `P=100000..101325 Pa`, with no general-water, glycol, fouled-wall,
  variable-k, or executable-material expansion;
* R71 `property_and_granularity` and R59 endpoint contract bind the same
  profile ID only conditionally within that reviewed scope and distinguish
  authority compatibility from the absent real property snapshot.

Accordingly:

```ini
JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID=true
SOURCE_MEAN_PROPERTY_AUTHORITY_PREDICATE_SATISFIED=true
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
```

This is a model-level reference-validity finding. It does not admit a state
outside the reviewed domain and does not call the property backend.

## 8. Identity/provenance schema predicate

R71's source-mean producer shape explicitly requires, at minimum:

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

The same source-mean schema is represented in the R71 evidence
`producer_contract.required_future_fields`. The older R57 source-mean record
also records the producer contract's required identity/provenance shape. This
supports the schema predicate at the model-definition layer:

```ini
SOURCE_MEAN_IDENTITY_AND_PROVENANCE_SCHEMA_BOUND=true
SOURCE_MEAN_IDENTITY_PROVENANCE_PREDICATE_SATISFIED=true
```

This finding must not be confused with a bound producer. The records continue
to say:

```ini
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
```

No ID, hash, endpoint state, snapshot, or producer instance is populated by
this receipt.

## 9. Fail-closed predicate

The reviewed R59 endpoint-pair contract rejects missing or mismatched case,
stream/side, topology/path, face/location, property authority/snapshot,
producer/lifecycle, provenance/rights, unsupported interpolation,
caller-only assertions, same-index assumptions, legacy relabeling, and
hidden/default state. That is valid evidence for the endpoint input contract.

However, the existing source-mean records do not define a source-mean-level
failure rule that explicitly maps all required conditions in this gate:

* R57 and R71 list a future `FAIL_CLOSED_RULES`/fail-closed requirement but do
  not enumerate or bind its source-mean admission coverage;
* R72 lists candidate predicates, but its list is the unverified predicate
  under audit, not an independent fail-closed receipt;
* R59's fail-closed list is expressly scoped to the endpoint-pair contract.

Therefore the strict result is:

```ini
SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND=undetermined
SOURCE_MEAN_FAIL_CLOSED_PREDICATE_SATISFIED=undetermined
```

The source-mean candidate must not be promoted until a separate authority
binds the source-mean admission/failure mapping.

## 10. Model-level versus real-instance layers

The model-level predicate audit does not change real-instance absence:

```ini
REAL_REVIEWED_SHELL_INLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_OUTLET_PRODUCER_FOUND=false
REAL_REVIEWED_SHELL_ENDPOINT_PAIR_PRODUCER_FOUND=false
REAL_SHELL_INLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_OUTLET_STATE_INSTANCE_PRESENT=false
REAL_SHELL_INLET_OUTLET_STATE_PAIR_BOUND=false
REAL_JMU_BULK_STATE_INSTANCE_PRESENT=false
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
```

The primary real-instance endpoint blockers remain:

```ini
SOURCE_MEAN_REAL_INSTANCE_PRIMARY_ENDPOINT_BLOCKERS=REAL_REVIEWED_SHELL_INLET_PRODUCER_MISSING;REAL_REVIEWED_SHELL_OUTLET_PRODUCER_MISSING;REAL_ENDPOINT_PAIR_INSTANCE_MISSING
```

Complete real-instance eligibility additionally requires case-bound endpoint
states, actual pressure-rule application, an actual property snapshot, and an
admitted producer lifecycle/provenance. These are not created here.

## 11. Final adjudication

The matrix contains one `false` predicate and one `undetermined` predicate:

```ini
SOURCE_MEAN_MODEL_LEVEL_PREDICATE_STATUS_BOUND=false
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATES=JMU_BULK_PRESSURE_RULE_BOUND;SOURCE_MEAN_FAIL_CLOSED_ADMISSION_RULE_BOUND
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_PREDICATE_COUNT=2
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=NOT_PROVEN
```

The pressure rule is still the only explicit `false` predicate, but it is not
lawful to call it the sole model-level blocker while source-mean fail-closed
coverage remains undetermined.

```ini
RESULT=CORRECTED_ADDITIONAL_MODEL_LEVEL_GAPS_FOUND
SOURCE_MEAN_BULK_STATE_PRODUCER_CONTRACT_BOUND=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_ID=NONE
SOURCE_MEAN_BULK_STATE_AUTHORITY_LIFECYCLE=NONE
SOURCE_MEAN_BULK_STATE_INDEPENDENT_REVIEW=NONE
NEXT_GATE=NONE_UNTIL_ADDITIONAL_MODEL_LEVEL_GAPS_ARE_SEPARATELY_ADJUDICATED
```

## 12. Preserved parent state and governance

```ini
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

This is documentation/evidence only. No source was acquired, no pressure
rule was selected, no backend was called, no state or producer was created, and
no downstream gate was executed.
