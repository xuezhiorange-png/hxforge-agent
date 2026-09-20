# TASK172 v0.7 — Jμ missing-lineage source acquisition and pressure-text inspection R2

## 1. Receipt and hard boundary

```ini
TASK_ID=TASK172_V0_7_JMU_BULK_PRESSURE_MISSING_LINEAGE_SOURCE_ACQUISITION_R2
MODE=TARGETED_MISSING_PRIMARY_LINEAGE_BODY_ACQUISITION_AND_PRESSURE_TEXT_INSPECTION_ONLY
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
PREVIOUS_HEAD_SHA=a7e4baa51f406d9cc69d4e9f428fa19373c6be74
HEAD_PRECONDITION_VERIFIED=true
RESULT=BLOCKED_MISSING_LINEAGE_BODY
```

This gate acquires and inspects only the missing Bell–Delaware/Taborek lineage
material relevant to the unresolved pressure paired with the whole-exchanger
shell-stream source-mean bulk property state used by the native Jamil/Thome
`J_mu` lineage. It does not select a pressure convention, create a pressure
authority, create a source-mean or endpoint state, call a property backend,
execute `J_mu`, solve a wall state, or alter production code.

The working tree was clean before this append-only change. PR #277 was
verified open and draft at the exact predecessor head above.

## 2. Historical immutability

R71 through R78 are historical records. Their documents, evidence files, and
registry extensions were not rewritten. The new registry record binds the
predecessor registry root and the canonical hash of `r78_extension`.

```ini
R71_EXTENSION_REWRITTEN=false
R72_EXTENSION_REWRITTEN=false
R73_EXTENSION_REWRITTEN=false
R74_EXTENSION_REWRITTEN=false
R75_EXTENSION_REWRITTEN=false
R76_EXTENSION_REWRITTEN=false
R77_EXTENSION_REWRITTEN=false
R78_EXTENSION_REWRITTEN=false
HISTORICAL_PAYLOADS_IMMUTABLE=true
```

## 3. Acquisition and rights boundary

The exact HEDH body was obtained through a directly accessible public URL
without bypassing authentication, payment, or other access controls. The PDF
itself states that the work is copyrighted and that redistribution permission
is not established. It is therefore used only for private review of the
targeted section; it is not copied into the repository, vendored, or
redistributed.

The Bell 1963 bibliographic identity was verified through a library catalogue
record and through citation leads in HEDH, but no exact, reviewable body was
legally obtained. A title-matching Scribd/PDFCoffee result was not accepted as
the Bell body because the visible material was an unrelated 1995 paper rather
than the 1963 report. No access-control bypass was attempted.

The current public ASME product page provides catalogue identity and purchase
information, not the official standard body. The official body was not
acquired; its target pressure text therefore remains undetermined rather than
negative.

## 4. Target acquisition ledger

| Source | Identity and exact review scope | Body status | Pressure disposition |
| --- | --- | --- | --- |
| `BELL-1963-DELAWARE-FINAL-REPORT` | Kenneth J. Bell, *Final Report of the Cooperative Research Program on Shell and Tube Heat Exchangers*, Bulletin No. 5, University of Delaware Engineering Experimental Station, 1963; library-record identity only | Exact body not acquired; SHA-256 `NONE` | `undetermined`; no exact-body adjudication |
| `TABOREK-HEDH-SHELL-TUBE-SINGLE-PHASE` | J. Taborek, HEDH 1983, Rev. 1986 contents imprint, §3.3 shell-and-tube single-phase method; Hemisphere Publishing Corporation | Complete public PDF body obtained for private review; SHA-256 `afa94a401269ce34de5833c555ad6116d53812047d4caf9a771a262c8ce8a6e7` | Exact target-section negative: no pressure pairing for Jμ source-mean property state |
| `ASME-PTC-12.5-2000-R2025-CATALOG` | Official ASME PTC 12.5-2000 (R2025) catalogue/product identity | Official body not acquired | `undetermined`; catalogue is not the body |

The HEDH body contains the target §3.3 text and its references. The inspected
locations were §3.3.3 printed pp. 3.3.3-1–3.3.3-5, §3.3.5 printed pp.
3.3.5-14–3.3.5-17, §3.3.7 printed pp. 3.3.7-1–3.3.7-2, and the §3.3.3
reference list on printed p. 3.3.3-5.

## 5. HEDH exact-body finding

HEDH §3.3.5 states that, for its manual Bell–Delaware method, shell- and
tube-side physical properties are evaluated at the arithmetic mean of the
respective terminal temperatures. Its input-data comments and §3.3.7
correlation text likewise place shell viscosity and the shell Prandtl-number
properties at the average shell temperature, with a separate wall-temperature
viscosity correction where applicable.

This is a temperature/property-temperature statement. It does not define the
pressure to pair with that temperature for the native Jμ whole-exchanger
source-mean bulk property state. The pressure passages in the same exact body
concern pressure-drop calculations, mechanical design pressure, or operating
pressure used in mechanical sizing. They do not bind a Jμ property-pressure
operator. Therefore:

```ini
TABOREK_HEDH_BODY_ACQUIRED=true
TABOREK_HEDH_BODY_COMPLETE_FOR_PRESSURE_QUESTION=true
TABOREK_HEDH_PRESSURE_RULE_TEXT_OBSERVED=false
TABOREK_HEDH_PRESSURE_RULE_EXACT_LOCATION=NONE
TABOREK_HEDH_TEMPERATURE_OPERATOR_OBSERVED=true
TABOREK_HEDH_TEMPERATURE_OPERATOR_TRANSFERRED=false
```

The HEDH text explicitly cites Bell 1963 in the §3.3.3 references. That is a
direct lineage lead for the missing body, not evidence that Bell's pressure
text has been reviewed. The lead remains unresolved because the exact Bell
body was not acquired.

## 6. Bell 1963 and citation-chain finding

The WorldCat record verifies the Bell report's author, institution, title,
Bulletin No. 5 identity, and 1963 publication year. HEDH §3.3.3 also cites
that report as a Delaware-method source. Neither record supplies the report's
full text. The accessible title-matching pages tested did not provide an exact
Bell body: one displayed a short unrelated 1995 paper and another did not
provide a verifiable full report.

Accordingly, the Bell pressure question is explicitly undetermined:

```ini
BELL_1963_BODY_ACQUIRED=false
BELL_1963_BODY_COMPLETE_FOR_PRESSURE_QUESTION=false
BELL_1963_BODY_SHA256=NONE
BELL_1963_PRESSURE_RULE_TEXT_OBSERVED=undetermined
BELL_1963_PRESSURE_RULE_EXACT_LOCATION=NONE
CITATION_CHAIN_LEAD_COUNT=1
CITATION_CHAIN_BODY_ACQUIRED_COUNT=0
```

This is not a negative claim that Bell 1963 contains no pressure convention.
It is a retrieval boundary.

## 7. ASME official-body finding

The official ASME page confirms that PTC 12.5-2000 (R2025) remains the active
single-phase heat-exchanger standard and directs the user to a paid product.
The official current body was not acquired in this gate. The earlier public
copy remains a separate, limited review artifact in R78 and is not reopened.

```ini
ASME_OFFICIAL_BODY_ACQUIRED=false
ASME_OFFICIAL_PRESSURE_RULE_TEXT_OBSERVED=undetermined
ASME_OFFICIAL_BODY_PRESSURE_RULE=UNDETERMINED_BODY_NOT_ACQUIRED
```

## 8. Pressure-text adjudication

No exact, scope-compatible pressure rule was found in the newly reviewed HEDH
body. The Bell 1963 body remains unreviewable, so the overall missing-lineage
negative audit is not complete. No pressure-insensitivity rule was found in
the acquired HEDH body or the previously reviewed recognized sources, and no
pressure convention is selected here.

```ini
PRESSURE_RULE_SOURCE_CANDIDATE_FOUND=false
CANDIDATE_PRESSURE_RULE_TYPE=NONE
CANDIDATE_PRESSURE_RULE_SOURCE_ID=NONE
CANDIDATE_PRESSURE_RULE_EXACT_LOCATION=NONE
PRESSURE_INSENSITIVITY_SOURCE_RULE_FOUND=false
PRESSURE_SOURCE_CONFLICT_FOUND=false
MISSING_LINEAGE_BODY_GAP_CLOSED=false
UNRESOLVED_SOURCE_TARGET_COUNT=1
UNRESOLVED_SOURCE_TARGETS=BELL-1963-DELAWARE-FINAL-REPORT
```

The following non-transfers remain explicit:

```ini
TEMPERATURE_OPERATOR_DOES_NOT_IMPLY_PRESSURE_OPERATOR=true
ENDPOINT_PRESSURE_IDENTITIES_DO_NOT_DEFINE_SOURCE_MEAN_PRESSURE_CONVENTION=true
BACKEND_REQUIREMENT_DOES_NOT_DEFINE_PHYSICAL_PRESSURE_RULE=true
PRESSURE_RULE_SELECTED=false
PRESSURE_AUTHORITY_CREATED=false
```

## 9. Preserved model-level state

```ini
JMU_BULK_PRESSURE_RULE_AUTHORITY_FOUND=false
JMU_BULK_PRESSURE_RULE_BOUND=false
SOURCE_MEAN_PRESSURE_PREDICATE_SATISFIED=false
SOURCE_MEAN_TEMPERATURE_PREDICATE_SATISFIED=true
SOURCE_MEAN_ENDPOINT_PAIR_PREDICATE_SATISFIED=true
SOURCE_MEAN_PROPERTY_AUTHORITY_PREDICATE_SATISFIED=true
SOURCE_MEAN_IDENTITY_PROVENANCE_PREDICATE_SATISFIED=true
SOURCE_MEAN_FAIL_CLOSED_PREDICATE_SATISFIED=true
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATES=JMU_BULK_PRESSURE_RULE_BOUND
SOURCE_MEAN_MODEL_LEVEL_UNSATISFIED_OR_UNDETERMINED_PREDICATE_COUNT=1
SOURCE_MEAN_MODEL_LEVEL_SOLE_BLOCKER=JMU_BULK_PRESSURE_RULE_AUTHORITY_MISSING
PRESSURE_IS_PROVEN_SOLE_MODEL_LEVEL_BLOCKER=true
SOURCE_MEAN_MODEL_LEVEL_AUTHORITY_CANDIDATE_ELIGIBLE=false
SOURCE_MEAN_BULK_STATE_AUTHORITY_CANDIDATE_CREATED=false
```

The sole-blocker statement describes the current model-level predicate matrix;
it does not claim that the missing Bell body has been negatively adjudicated.
The source-review gap remains a separate acquisition limitation.

## 10. Real-instance and parent-blocker guards

```ini
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
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

No downstream Q, film, wall, Jμ, L2B, L3, numerical-error-budget, or mesh
work is authorized by this source-acquisition receipt.

## 11. Governance and final receipt

```ini
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_EXPERIMENT_PERFORMED=false
MESH_STUDY_PERFORMED=false
PROPERTY_BACKEND_CALLED=false
JMU_EXECUTED=false
WALL_STATE_SOLVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=NONE_UNTIL_SEPARATELY_AUTHORIZED
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The exact final head, CI run, and final artifact hashes are recorded in the
append-only registry and final receipt after validation. This gate stops with
`BLOCKED_MISSING_LINEAGE_BODY`: HEDH has an exact negative finding for the
target pressure role, but Bell 1963 remains an unresolved exact-body target.

## 12. Source review references

* [HEDH public body used only for targeted private review](https://kostmash.ru/assets/1schlunder_e_u_heat_exchanger_design_handbook.pdf)
* [HEDH bibliographic record](https://books.google.ca/books?id=kOBSAAAAMAAJ)
* [Bell 1963 library record](https://search.worldcat.org/title/Final-report-of-the-cooperative-research-program-on-shell-and-tube-heat-exchangers/oclc/16107403)
* [ASME PTC 12.5 official catalogue identity](https://www.asme.org/codes-standards/find-codes-standards/single-phase-heat-exchangers)

These links identify the acquisition/review paths; they do not create a new
pressure authority or authorize redistribution of copyrighted source bodies.
