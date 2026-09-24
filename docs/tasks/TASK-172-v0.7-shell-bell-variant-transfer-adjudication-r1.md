# TASK172 R1 — Bell variant transfer adjudication

## 1. Receipt and decision boundary

This document records the authorized Bell/Delaware variant transfer
adjudication for the TASK172 shell-wall-correction blocker. It is an
append-only decision record. It does not alter TASK166, TASK172 production
code, equations, numerical behavior, source payloads, or dependency files.

TASK_ID=TASK172_V0_7_SHELL_BELL_VARIANT_TRANSFER_ADJUDICATION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
PREVIOUS_HEAD_SHA=7743621dce676c85e63cf30257bb86e738232295
MODE=TARGETED_BELL_VARIANT_TRANSFER_ADJUDICATION_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true

The adjudication asks whether the wall-viscosity-normalized ideal or
non-leakage tube-bank j definition observed in Bell 1960 is the same
coefficient and identity lineage as the native TASK166/Goncalves ji
correlation. A matching exponent alone is not an identity proof.

## 2. Native TASK166 comparator

The native comparator is unchanged:

NATIVE_SHELL_TASK_ID=TASK-166
NATIVE_SOURCE_DEFINITION_ID=TASK165_R3_BELL_DELAWARE_SOURCE_AUTHORITY_V1
NATIVE_METHOD=BELL_DELAWARE
NATIVE_IDEAL_HTC_FORM=ji*cp*G*Pr^(-2/3)
NATIVE_CORRECTED_HTC_FORM=ideal_h*Jc*Jl*Jb*Js*Jr
NATIVE_RE_EVALUATOR_DOMAIN=0<Re_s<=100000
GONCALVES_ACTIVE_WALL_PROPERTY_TERM_PRESENT=false
GONCALVES_WALL_TEMPERATURE_INPUT_PRESENT=false
GONCALVES_SOURCE_ID=SRC-AICHE-GONCALVES-COSTA-BAGAJEWICZ-2019-BELL-DELAWARE
GONCALVES_DOI=10.1002/aic.16602
GONCALVES_BODY_SHA256=fd39834253245f49609b42340e89ca8c652fed83f7cd7803d6c660bddfd6ca54

The native implementation obtains ji from the reviewed Jamil Table A.1
coefficient rows and the Goncalves relation. Its correction path multiplies
Jc, Jl, Jb, Js, and Jr. No native factor accepts shell wall viscosity or a
shell wall temperature. Jr remains a low-Reynolds-number crossed-row
correction and is not a wall-property correction.

## 3. Adjudication outcome

ADJUDICATION_OUTCOME=OUTCOME_C_J_FACTOR_LINEAGE_IDENTITY_NOT_PROVEN
J_FACTOR_LINEAGE_IDENTITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
SHELL_WALL_CORRECTION_TRANSFER_AUTHORITY_CANDIDATE_CREATED=false
TRANSFER_REJECTED=false

Bell 1960 proves a source-variant observation: its ideal or non-leakage
tube-bank j normalization includes a wall-viscosity ratio. It does not prove
that the current TASK166 ji coefficients are generated from that same
normalized j definition. The available Bell 1960 body does not provide a
source-bound mapping from its ideal-bank coefficient lineage to the current
Jamil Table A.1 rows. Bell 1963 and Bergelin Bulletin No. 4 bodies remain
unacquired, and the exact Taborek/HEDH body remains unavailable. Therefore
the evidence cannot distinguish a shared lineage from a later coefficient
variant that changed or omitted the normalization.

This is not a finding that the Bell 1960 and TASK166 equations are
physically incompatible. It is a finding that their identity and transfer
contract are unproven. Fail-closed behavior is required.

## 4. Bell 1960 source observation

Source target:

SOURCE_TARGET_ID=BELL-1960-DELAWARE-DESIGN
AUTHOR=Kenneth J. Bell
TITLE=Exchanger Design Based on the Delaware Research Program
PUBLICATION=Petro/Chem Engineer
VOLUME=32
ISSUE=11
YEAR=1960
PRINTED_PAGE_SEQUENCE=C-26-C-36;C-40a-C-40c
PDF_PAGE_COUNT=14
BODY_ACQUIRED=true
BODY_COMPLETE=true
BYTES_SHA256=4657ebfb78bda433528b7f1197fff32e299361d39379bb6839e871f43bc2ed11
PUBLIC_ACCESS_PATH=https://www.ing.unp.edu.ar/asignaturas/operaciones_fisicas_2/Versiones%20PDF/Exchanger%20design%20based%20on%20the%20Delaware%20research%20program-%20Kenneth%20Bell.pdf
RIGHTS_STATUS=PUBLIC_SCAN_ACCESSIBLE_RIGHTS_UNVERIFIED_NOT_VENDORED
SOURCE_REVIEW_STATUS=VERIFIED_SOURCE_FOR_VARIANT_OBSERVATION_ONLY

The acquired scan gives the following page-bound observations:

| Location | Observation | Transfer consequence |
| --- | --- | --- |
| C-28 | The non-isothermal discussion reports a factor of (mu/mu_w)^0.14 for the studied friction and j behavior; a separate Hull laminar friction refinement is also mentioned. | A wall-property factor is observed in this source variant, but this paragraph does not establish the TASK166 coefficient lineage or transfer domain. |
| C-30 | The crossflow friction discussion uses (mu/mu_w)^0.14. | Friction evidence is not heat-transfer transfer authority. |
| C-32-C-33 | The ideal/non-leakage tube-bank j normalization contains (mu_w/mu)^0.14. | The factor belongs to this source j normalization; it is not established as a post-J geometry multiplier. |
| C-36 | The procedure selects ideal-tube-bank j and then applies source geometry, leakage, and bypass steps. | Source ordering must be compared to, not assumed identical with, the native TASK166 identity. |
| C-40a | The worked example reconstructs h from j and uses the inverse coefficient-side orientation (mu/mu_w)^0.14. | The source orientation is preserved; it does not create a TASK166 transfer rule. |
| C-40c | Nomenclature defines mu as absolute viscosity and mu_w as absolute viscosity at the heat-transfer surface. | The symbols are source-bound, but the target bulk location, wall producer, and transfer domain remain unbound. |

BELL_1960_DIMENSIONLESS_J_RATIO=(mu_w/mu)^0.14
BELL_1960_COEFFICIENT_RECONSTRUCTION_RATIO=(mu/mu_w)^0.14
BELL_1960_EXPONENT=0.14
BELL_1960_MU_DEFINITION=absolute_viscosity;exact_bulk_location_not_bound
BELL_1960_MU_W_DEFINITION=absolute_viscosity_at_heat_transfer_surface
BELL_1960_WALL_TEMPERATURE_DEFINITION=not_separately_defined
BELL_1960_COMBINATION_POSITION=inside_ideal_or_non_leakage_tube_bank_j_normalization_before_source_geometry_steps

The source-level classification is:

CORRECTION_IS_PART_OF_ORIGINAL_IDEAL_BANK_BASE=true
CORRECTION_IS_OPTIONAL_ENGINEERING_EXTENSION=false
CORRECTION_IS_SOURCE_VARIANT_SPECIFIC=true

These three fields describe Bell 1960 itself. They do not authorize adding
the factor to the current TASK166 expression.

## 5. Coefficient-lineage audit

| Lineage step | Evidence status | Adjudication |
| --- | --- | --- |
| Bell/Delaware original j definition | Bell 1960 body acquired and page-bound | The normalized j observation is verified for Bell 1960. |
| Bell/Bergelin ideal-bank coefficient lineage | Bell 1960 coefficient-table identity is not mapped to the current repository coefficient rows; Bergelin body not acquired | Identity not proven. |
| Bell 1963 final report lineage | Bibliographic identity only; complete body not acquired | Cannot confirm whether the final report preserves, changes, or qualifies the normalization. |
| Later Bell-Delaware implementation lineage | Current repository uses Goncalves 2019 plus Jamil Table A.1; later source chain does not identify an exact Bell 1960 coefficient preimage | Identity not proven. |
| Goncalves ji | Exact native relation and body hash are reviewed in TASK166 | Native ji is proven as TASK166 input, but its Bell 1960 j-definition identity is not proven. |
| TASK166 ideal_h | hi=ji*Cp_s*G_s*Pr_s^(-2/3) with no wall-property term | No source-authorized reconstruction rule is available for inserting Bell 1960's factor. |

The Jamil Table A.1 rows are a native parameter supplement for TASK166.
Their presence in the repository does not establish that they are the
Bell 1960 coefficient table, use the same normalization, or retain the same
source ordering. Source names and the common label Bell-Delaware cannot
substitute for an exact coefficient preimage.

The unavailable primary bodies are retained as unresolved lineage targets:

BELL_1963_SOURCE_TARGET_ID=BELL-1963-DELAWARE-FINAL-REPORT
BELL_1963_BODY_ACQUIRED=false
BELL_1963_BODY_COMPLETE=false
BELL_1963_BYTES_SHA256=NONE
BELL_1963_STATUS=BIBLIOGRAPHIC_PRIMARY_SOURCE_TARGET_ONLY
BELL_1963_VISCOSITY_CORRECTION_PRESENT=UNDETERMINED_BODY_NOT_ACQUIRED

BERGELIN_1958_SOURCE_TARGET_ID=BERGELIN-1958-DELAWARE-BULLETIN-4
BERGELIN_1958_BODY_ACQUIRED=false
BERGELIN_1958_BODY_COMPLETE=false
BERGELIN_1958_BYTES_SHA256=NONE
BERGELIN_1958_STATUS=BIBLIOGRAPHIC_PRIMARY_SOURCE_TARGET_ONLY
BERGELIN_1958_VISCOSITY_CORRECTION_PRESENT=UNDETERMINED_BODY_NOT_ACQUIRED
BERGELIN_1958_TRANSFER_TO_BELL_IDEAL_BANK=NOT_ASSESSED_WITHOUT_BODY

TABOREK_SOURCE_TARGET_ID=TABOREK-HEDH-SHELL-TUBE-SINGLE-PHASE
TABOREK_BODY_ACQUIRED=false
TABOREK_BODY_COMPLETE=false
TABOREK_BYTES_SHA256=NONE
TABOREK_STATUS=BIBLIOGRAPHIC_LINEAGE_ONLY
TABOREK_VISCOSITY_CORRECTION_PRESENT=UNVERIFIED_EXACT_BODY_NOT_ACQUIRED

The WorldCat Bell 1963 record is bibliographic identity only:
https://search.worldcat.org/title/final-report-of-the-cooperative-research-program-on-shell-and-tube-heat-exchangers/oclc/16107403

Secondary reposts, snippets, lecture material, and formula summaries remain
discovery or cross-check evidence only. They cannot fill a missing primary
coefficient table, source domain, or transfer rule.

## 6. Variant-difference matrix

| Dimension | TASK166/Goncalves | Bell 1960 | Bell 1963 | Bergelin 1958 | Taborek/HEDH |
| --- | --- | --- | --- | --- | --- |
| Ideal HTC base | hi=ji*Cp_s*G_s*Pr_s^(-2/3) | Source-specific ideal/non-leakage tube-bank j reconstruction | Not determined; body not acquired | Not determined; body not acquired | Not determined; exact body not acquired |
| Viscosity correction | Absent | Present in source j normalization/reconstruction | Not determined | Not determined | Not determined from exact body |
| Ratio orientation | None | j: (mu_w/mu)^0.14; coefficient reconstruction: (mu/mu_w)^0.14 | Not determined | Not determined | Not determined from exact body |
| Coefficient identity | Jamil Table A.1 rows with Goncalves relation | Source-specific ideal-bank plots/relations; exact mapping to Jamil rows not bound | Not determined | Not determined | Not determined |
| Bulk state | TASK166 shell flow state used by native evaluator | mu is named absolute viscosity; exact bulk location not bound | Not determined | Not determined | Not determined |
| Wall state | No wall input | mu_w at heat-transfer surface; complete wall-temperature state absent | Not determined | Not determined | Not determined |
| Re domain | Native evaluator 0<Re_s<=100000 | Source study/figures; strict transfer interval not bound | Not determined | Not determined | Not determined |
| Pr domain | Native input domain, not wall-factor domain | Not bound | Not determined | Not determined | Not determined |
| Fluid scope | Native TASK166 scope | Source data/example context only | Not determined | Not determined | Not determined |
| Heating/cooling scope | Native method scope | Non-isothermal discussion, no complete direction branch | Not determined | Not determined | Not determined |
| Geometry/layout | TASK166 selected Bell geometry identity | Source ideal-bank/Model 9 context; exact TASK166 mapping not bound | Not determined | Baffled/unbaffled tube-bank title only | Not determined |
| Combination position | ideal_h then Jc, Jl, Jb, Js, Jr | Within source ideal-bank j normalization before source geometry steps | Not determined | Not determined | Not determined |
| Source body complete | Yes for selected implementation source | Yes for acquired scan, rights unverified | No | No | No |

## 7. Transfer-contract fields

The following values distinguish source observation from a TASK166 transfer
authority. A field is true only when it is bound for the proposed transfer,
not merely observed in Bell 1960.

| Contract field | Status | Reason |
| --- | --- | --- |
| Correction equation | false | Bell 1960's source equation is observed, but no TASK166-compatible transfer equation is authorized. |
| Property ratio | true, source syntax only | The source ratio orientation is page-bound; its target-state mapping is not. |
| Exponent | true, source syntax only | Bell 1960's 0.14 is page-bound; numerical coincidence does not prove coefficient identity. |
| Combination rule | false | No rule authorizes placing the source factor in TASK166's ideal_h or after its J factors. |
| Bulk state | false | Source mu is not mapped to TASK032 shell bulk state. |
| Wall state | false | Source mu_w is not mapped to a TASK172 shell-fluid wall-interface state produced by an approved wall closure. |
| Re domain | false | TASK166's evaluator interval is not the source wall-factor validity interval. |
| Pr domain | false | A target Pr input is not a source-qualified wall-factor domain. |
| Fluid scope | false | No complete source-qualified production fluid family is bound for transfer. |
| Heating/cooling scope | false | No direction-specific transfer contract is bound. |
| Geometry/layout domain | false | No exact transfer from source tube-bank geometry to the selected TASK166 geometry identity is bound. |

In receipt form:

CORRECTION_EQUATION_BOUND=false
PROPERTY_RATIO_BOUND=true
EXPONENT_BOUND=true
BULK_STATE_BOUND=false
WALL_STATE_BOUND=false
RE_DOMAIN_BOUND=false
PR_DOMAIN_BOUND=false
FLUID_SCOPE_BOUND=false
HEATING_COOLING_SCOPE_BOUND=false
GEOMETRY_LAYOUT_DOMAIN_BOUND=false
COMBINATION_RULE_BOUND=false

## 8. Bulk and wall state mapping

### 8.1 Bulk state

BULK_STATE_BOUND=false
BULK_STATE_SOURCE_DEFINITION=BELL_1960_MU_ABSOLUTE_VISCOSITY_EXACT_BULK_LOCATION_NOT_BOUND
TASK172_BULK_STATE=SHELL_FLUID_BULK_STATE
TASK032_BULK_STATE_MAPPING_VALID=false
TASK032_BULK_STATE_MAPPING_REASON=TASK032 shell state is not source-proven equivalent to Bell 1960's unspecified bulk-viscosity location

Bell 1960 names mu as an absolute viscosity, but the acquired source does
not bind the requested local evaluation location as a TASK172 cell bulk
state, a mean bulk state, a caloric state, an inlet/outlet average, or
another exact state. The target cannot be inferred from the symbol name.

### 8.2 Wall state

WALL_STATE_BOUND=false
WALL_STATE_SOURCE_DEFINITION=BELL_1960_MU_W_ABSOLUTE_VISCOSITY_AT_HEAT_TRANSFER_SURFACE
TASK172_WALL_STATE=SHELL_FLUID_WALL_INTERFACE
TASK172_STATE_MAPPING_ESTABLISHED=false
WALL_TEMPERATURE_PRODUCER_BOUND=false

The source surface wording is compatible in concept with a fluid-side
heat-transfer surface, but the TASK172 wall producer and property-evaluation
state are not yet bound for the native shell path. A tube-metal outer
surface, shell bulk temperature, arithmetic wall mean, TASK034 pressure-drop
state, or an unqualified neutral factor cannot be substituted.

No film/contact-temperature approximation is authorized by this record.

## 9. Explicitly forbidden transfers

TASK034_WALL_AUTHORITY_REUSE=NO
TASK034_TRANSFER_TO_TASK166_HEAT_TRANSFER=false
TUBE_RELAP_CORRECTION_TRANSFER_TO_TASK166=false
MARTIN_GNIELINSKI_CROSSFLOW_TRANSFER_TO_TASK166=false
SECONDARY_TABOREK_TRANSFER_TO_TASK166=false

TASK034's (mu_b/mu_w)^(7/50) belongs to its shell pressure-drop phi_s
authority. Equal exponent numerics do not establish equal physical quantity,
state definitions, source domain, or model identity. The tube RELAP and
Martin/Gnielinski paths are different model authorities and remain excluded.

## 10. Final governance state

SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false

This adjudication creates no shell correction authority candidate and does
not promote any source or payload. The current native TASK166 equation
remains the sole production equation. The shell wall-correction blocker
remains active because the coefficient-lineage identity and every required
transfer field are not proved.

The next authorized gate is:

NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_COEFFICIENT_LINEAGE_RESOLUTION_R1_ONLY

That gate must resolve the missing coefficient-table lineage and may not
silently add Bell 1960's factor to TASK166.

## 11. Artifact and review ledger

SOURCE_ARTIFACT_HASHES:

bell_delaware_authority_py=6ba2fea3eb6008a9e92e025efad924bf956c60ee67da3a0436bc1c3a965f75b5
bell_delaware_heat_transfer_py=bc442493dbdc52ca0a8c52361276becc2e2e73a246ea5e7f6ab3cecb0306c2ad
bell_delaware_models_py=bcc7f850a8a33d7d2a3ef540d7d123d88d4bbb09cce36511caeb3f9cea08f668
bell_delaware_geometry_py=785e757e7b589c25e31a399d0a35e145cbebde2ba6b17912a598d62935a2d7ba
bell_delaware_validation_py=1c1e14e9d84e8f858fcbd8cc249f97c92851728c22849ac500acb8be84a3721d
bell_delaware_service_py=e576e925118933756205279c8ed248f769c496453073eb5dca8265b971cba017
bell_delaware_schema_py=b428b66484ccecc6e922358667e3a34483c9a398126e3d9ef7929c706cabb193
bell_delaware_provenance_py=03d1250b5c619e2c26e10f8a0df904a33d98778a09ee7075db6a0c996223ed57
task166_doc=fe61dcd297a28400756e52f7f5a52800e080c8dae5ef71ec5d4e3731f2f70926
task032_doc=750f95ab3869f2024ed57639e5754d9d36b9382e573c0a32b8899145f054d188
task172_wall_state_doc=1ab84d797a53e7171714b79305087c6dfe4965a578d4d1e5825b8a491bea2cf9

REVIEW_STATUS=PROPOSED_DECISION_RECORD_FAIL_CLOSED_PENDING_FUTURE_LINEAGE_RESOLUTION
LIFECYCLE_PROMOTION_PERFORMED=false
HISTORICAL_RECORDS_REWRITTEN=false
GOLDEN_APPROVED=false
LOCAL_VALIDATION_REQUIRED=true
EXACT_FINAL_HEAD_CI_REQUIRED=true

The companion machine-readable evidence is:

docs/tasks/evidence/TASK-172-shell-bell-variant-transfer-adjudication-r1.json

The registry update is append-only in:

docs/tasks/TASK-172-v0.7-authority-registry-r1.json
