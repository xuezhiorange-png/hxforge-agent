# TASK172 v0.7 — Jμ source-mean bulk pressure reference qualification R1

## 1. Receipt and hard boundary

```ini
TASK_ID=TASK172_V0_7_JMU_BULK_PRESSURE_REFERENCE_CONVENTION_QUALIFICATION_R1
MODE=TARGETED_PRESSURE_REFERENCE_SOURCE_ACQUISITION_AND_TRANSFER_QUALIFICATION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=7ea615cab486bb8ad2140e610d2788d4b13ed109
HEAD_PRECONDITION_VERIFIED=true
RESULT=BLOCKED
OUTCOME=OUTCOME_C_NO_LEGAL_PRESSURE_AUTHORITY_FOUND
```

This gate audits only whether a recognized source provides a lawful pressure
reference convention for the whole-exchanger shell-stream bulk property state
consumed by the native TASK166/Jamil/Thome `J_mu` lineage. It does not choose a
pressure convention, create a pressure authority, create endpoint or source-mean
states, call a property backend, execute `J_mu`, or solve a wall state.

The current PR and exact head were verified before this record was written:

```ini
PR_STATE=OPEN_DRAFT
FINAL_HEAD_SHA=RECORDED_IN_FINAL_RECEIPT
```

## 2. Historical and predecessor boundary

R71 through R77 remain historical. This record appends a new pressure-source
adjudication only. The effective predecessor state is preserved:

```ini
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE=NONE
JMU_BULK_PRESSURE_RULE_BOUND=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
PRESSURE_IS_PROVEN_SOLE_MODEL_LEVEL_BLOCKER=true
```

The reviewed temperature operator is not reopened. In particular, the accepted
ASME transfer of an arithmetic shell-side bulk temperature does not imply a
pressure operator.

## 3. Targeted source set and acquisition boundary

The audit used only the recognized source chain already named by the R2
authority record, plus the official ASME catalogue identity and the public
copies used for the already accepted temperature transfer. Five bodies were
available for targeted inspection; three named lineage leads remained
non-reviewable as exact bodies.

| Source ID | Exact location inspected | Body/hash status | Pressure finding | Transfer disposition |
| --- | --- | --- | --- | --- |
| `THOME-2004-EDB3-CH3-CROSSCHECK` | §3.4.6 printed p.3-12, Eq.3.4.23 and §3.4.7 pp.3-12–3-13; §3.5 pressure-drop section | Acquired; `326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4` | Jμ/bulk-property passages identify mean temperature and viscosity roles; pressure text is pressure-drop material and does not pair a pressure with the Jμ property state | No pressure rule |
| `ASME-PTC-12.5-2000-R2025-CATALOG` | Official ASME PTC 12.5 product/catalog page | Official body not acquired; catalogue identity only | Test-code scope includes measured fluid conditions, heat rate, overall coefficient and pressure drop; no Jμ property-pressure convention | No pressure rule |
| `ASME-PTC-12.5-2000-R2015-PUBLIC-COPY` | Appendix C §C.4, printed p.58; pressure measurement/pressure-loss sections | Relevant preview acquired; `bc258206e9d247adb405821b49384ca243f28013ad85fa102caba4218565a071` | Arithmetic mean is explicit for shell bulk temperature. Separate pressure/density averages belong to pressure-loss/test measurement, not Jμ property evaluation | Temperature only; pressure transfer rejected |
| `SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE` | §2.1 Eqs.36–39 PDF p.4; §2.2 Eqs.75–77 PDF p.6 | Acquired; `fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54` | Shell-side pressure-drop terms are hydraulic/zone pressure-drop terms; no source-mean property pressure rule | No pressure rule |
| `SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS` | §2.2.2 PDF p.11 Eqs.6–9; Appendix Tables A.1–A.2 pp.57–59; stream-analysis pressure-drop discussion | Accepted manuscript acquired; `a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970` | Native Jamil operational representation points to Thome for bulk properties. Operating-pressure inputs and pressure-drop equations do not define property-evaluation pressure | No pressure rule |
| `BELL-1960-DELAWARE-DESIGN` | Printed pp.C-26–C-36 and C-40a–C-40c | Acquired; `4657ebfb78bda433528b7f1197fff32e299361d39379bb6839e871f43bc2ed11` | Historical Bell/Delaware lineage and viscosity normalization only; no source-mean property pressure pairing | No pressure rule |
| `TABOREK-HEDH-SHELL-TUBE-SINGLE-PHASE` | Prior authority target §3.3 | Exact body not acquired; no hash | Not reviewable as an exact source body | No transfer |
| `BELL-1963-DELAWARE-FINAL-REPORT` | Bibliographic identity only | Exact body not acquired; no hash | Not reviewable as an exact source body | No transfer |

The source URLs and rights/reviewability status are recorded in the structured
evidence. The public ASME text is used only for the narrow already accepted
temperature transfer; it is not treated as a blanket transfer of the PTC test
method or its pressure-loss conventions.

## 4. Route A — explicit pressure convention

The targeted source bodies do not state any of the candidate rules below for
the `J_mu` source-mean property state:

```text
INLET_PRESSURE
OUTLET_PRESSURE
ARITHMETIC_MEAN_INLET_OUTLET_PRESSURE
LOCAL_BULK_PRESSURE
REPRESENTATIVE_SHELL_PRESSURE
PRESSURE_VARIATION_NEGLIGIBLE_UNDER_EXPLICIT_DOMAIN
OTHER_SOURCE_DEFINED_RULE
```

The ASME public text contains pressure measurements and pressure-loss
calculations, including a pressure/density treatment for a pressure-loss
context. The Thome and Bell–Delaware material likewise contains pressure-drop
relations. Those statements do not identify the pressure to be paired with the
source-mean shell temperature when evaluating Jμ bulk properties. The Jamil
operational source contains pressure-drop and operating-pressure information,
but no source-mean property-pressure rule.

Therefore the exact transfer adjudication is:

```ini
PRESSURE_SOURCE_BODY_ACQUIRED=true
PRESSURE_SOURCE_EXACT_LOCATION_BOUND=true
PRESSURE_RULE_TEXT_OBSERVED=false
PRESSURE_RULE_PHYSICAL_QUANTITY_MATCH=false
PRESSURE_RULE_STREAM_ROLE_MATCH=false
PRESSURE_RULE_GRANULARITY_MATCH=false
PRESSURE_RULE_METHOD_CONTEXT_MATCH=false
PRESSURE_RULE_PROPERTY_EVALUATION_ROLE_MATCH=false
PRESSURE_RULE_TRANSFER_COMPATIBLE=false
PRESSURE_RULE_TRANSFER_CONFLICTS=PRESSURE-DROP-OR-TEST-MEASUREMENT-SEMANTICS-DO-NOT-TRANSFER-TO-JMU-PROPERTY-STATE;NO-EXPLICIT-JMU-PRESSURE-PAIRING
```

No pressure convention is selected. In particular, this record does not
introduce inlet pressure, outlet pressure, arithmetic-mean pressure,
representative pressure, constant pressure, or a hidden backend default.

## 5. Route B — pressure-insensitivity authority

No targeted source provides a domain-qualified statement that pressure
variation is negligible for this source-mean property evaluation with an
explicit acceptance rule and required inputs. The pressure-loss passages do not
constitute such an authority.

```ini
ROUTE_B_PRESSURE_INSENSITIVITY_SOURCE_FOUND=false
ROUTE_B_DOMAIN_BOUND=false
ROUTE_B_ACCEPTANCE_RULE_BOUND=false
PRESSURE_INSENSITIVITY_AUTHORITY_FOUND=false
PRESSURE_INSENSITIVITY_SOURCE_ID=NONE
PRESSURE_INSENSITIVITY_DOMAIN=NONE
PRESSURE_INSENSITIVITY_REQUIRED_INPUTS=NONE
PRESSURE_INSENSITIVITY_ACCEPTANCE_RULE=NONE
```

There is therefore no pressure-insensitivity threshold or constant-pressure
assumption to transfer.

## 6. Pressure/source conflict adjudication

No two admissible source-mean pressure conventions conflict, because no
admissible convention was found. The observed pressure-drop and test-measurement
conventions are excluded by physical quantity, granularity, method context and
property-evaluation role. They are not alternative source-mean rules to be
chosen, averaged, or ranked.

```ini
PRESSURE_SOURCE_CONFLICT_FOUND=false
PRESSURE_SOURCE_CONFLICT_ADJUDICATED=true
```

## 7. Existing property-authority compatibility boundary

The existing property contract remains a separate, narrow reviewed model-level
authority. Its effective reviewed payload is bound by the existing registry
record and hash:

```ini
JMU_BULK_PROPERTY_AUTHORITY_ID=V07-T172-WATER-PROPERTY-PROFILE-R2
JMU_BULK_PROPERTY_AUTHORITY_CONTRACT_VALID=true
JMU_BULK_PROPERTY_AUTHORITY_REVIEWED_PAYLOAD_HASH=8407227452b519483fbccbc686d3e8fcb2ca54866a8a8f01114addb5ca5a37de
PROPERTY_SCOPE=PURE_ORDINARY_WATER;HEOS;CoolProp 8.0.0;DEF;STABLE_SINGLE_PHASE_LIQUID
PROPERTY_DOMAIN=T=298.15..300 K;P=100000..101325 Pa
REAL_JMU_BULK_PROPERTY_SNAPSHOT_PRESENT=false
```

This is only compatibility evidence. It neither supplies a pressure rule nor
creates a property snapshot. Because no candidate pressure rule exists, its
compatibility with a source-pressure operator is not evaluated as a positive
transfer; no pressure domain is inferred from the property authority.

## 8. Model-level predicate disposition

The five already reviewed predicates remain unchanged. Pressure is the only
unsatisfied model-level predicate after this targeted audit:

```ini
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_ENDPOINT_PAIR_PREDICATE_SATISFIED=true
SOURCE_MEAN_PROPERTY_AUTHORITY_PREDICATE_SATISFIED=true
SOURCE_MEAN_IDENTITY_PROVENANCE_PREDICATE_SATISFIED=true
SOURCE_MEAN_FAIL_CLOSED_PREDICATE_SATISFIED=true
SOURCE_MEAN_MODEL_LEVEL_PREDICATE_STATUS_BOUND=true
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATES=JMU_BULK_PRESSURE_RULE_BOUND
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATE_COUNT=1
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
PRESSURE_IS_PROVEN_SOLE_MODEL_LEVEL_BLOCKER=true
SOURCE_MEAN_MODEL_LEVEL_AUTHORITY_CANDIDATE_ELIGIBLE=false
```

The reviewed endpoint-pair model contract is sufficient as a future input
contract; real endpoint producers and values are not required to define a
model-level pressure rule. They remain required for any future real instance.

## 9. Lifecycle and real-instance guards

Because no lawful pressure authority was found, no pressure authority
candidate is created and no lifecycle is promoted:

```ini
JMU_BULK_PRESSURE_RULE_AUTHORITY_CANDIDATE_CREATED=false
JMU_BULK_PRESSURE_RULE_AUTHORITY_ID=NONE
JMU_BULK_PRESSURE_RULE_AUTHORITY_LIFECYCLE=NONE
JMU_BULK_PRESSURE_RULE_INDEPENDENT_REVIEW=NONE
JMU_BULK_PRESSURE_RULE_BOUND=false
```

All real-instance guards remain false:

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

## 10. Preserved TASK172 parent state and governance

```ini
QUALIFIED_Q_AUTHORITY_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
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

The pressure branch is blocked for the precise reason that the targeted
recognized sources do not provide an exact, scope-compatible source-mean
property pressure convention or pressure-insensitivity rule. No downstream
wall, film, Q, Jμ, or numerical work is authorized by this receipt.

## 11. Source review references

The external source identities used for this adjudication are:

* [ASME PTC 12.5 official catalogue identity](https://www.asme.org/codes-standards/find-codes-standards/single-phase-heat-exchangers)
* [Public PTC 12.5 text mirror](https://studylib.net/doc/27322760/asme-ptc-12-5-2000)
* [Thome EDB3 chapter text mirror](https://studylib.net/doc/26336828/flow-fractions---sthe)
* [Jamil accepted-manuscript record](https://researchportal.northumbria.ac.uk/en/publications/exergoeconomic-optimization-of-a-shell-and-tube-heat-exchanger/)

These links support source identity and targeted review only; they do not
replace the repository-bound source hashes or create a new authority.
