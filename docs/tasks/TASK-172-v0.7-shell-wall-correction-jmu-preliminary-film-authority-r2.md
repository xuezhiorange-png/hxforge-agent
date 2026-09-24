# TASK172 R2 — Jμ preliminary tube- and shell-film authority

## 1. Receipt and boundary

This documentation/evidence-only record audits the two film inputs that a
future Jamil/Thome `J_mu` wall-temperature producer would need.  It does not
create a heat-rate receipt, choose a material, select a wall conductivity,
create a source mean-bulk producer, localize a whole-bundle factor, implement
`J_mu`, execute a wall-temperature calculation, start a fixed-point
iteration, change TASK026 or TASK166, or start numerical qualification.

```ini
TASK_ID=TASK172_V0_7_SHELL_WALL_CORRECTION_JMU_PRELIMINARY_FILM_AUTHORITY_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
AUTHORIZED_PREDECESSOR_HEAD=45dcc0e8a0364c0707e664f3fe33fa8f0011cabb
MODE=JMU_PRELIMINARY_FILM_AUTHORITY_ONLY
SUBJECT_BLOCKER=SHELL-WALL-CORRECTION-AUTHORITY
DOCUMENTATION_EVIDENCE_ONLY=true
TASK162_CHANGED=false
TASK163_CHANGED=false
TASK166_CHANGED=false
TASK171_SEMANTICS_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The Q branch is intentionally frozen.  This record does not create an
external-Q instance and does not use TASK162's UA-dependent duty as a
preliminary wall calculation input.

## 2. Inherited Q and unresolved dependencies

The external-Q contract is reviewed as a model-level contract, but there is
no case instance.  Its state is carried forward without modification:

```ini
EXTERNAL_Q_INPUT_AUTHORITY_CONTRACT_BOUND=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_COMPLETE=true
EXTERNAL_Q_CONTRACT_INDEPENDENT_REVIEW_RESULT=PASS
EXTERNAL_Q_CONTRACT_STATUS=REVIEWED_CONTRACT
EXTERNAL_Q_INSTANCE_STATUS=NONE
EXTERNAL_Q_INSTANCE_PRESENT=false
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
EXTERNAL_Q_RECEIPT_REVIEW_ELIGIBLE=false
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
NEXT_LIFECYCLE_EVENT=REAL_CASE_BOUND_EXTERNAL_Q_RECEIPT_REQUIRED
GLOBAL_Q_TO_LOCAL_WALL_Q_MAPPING_BOUND=false
```

The following independent producer dependencies remain unresolved and are
not replaced by a film choice:

```ini
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

## 3. Source and repository evidence

No new external source body is acquired by this gate.  The review uses the
accepted source bodies and native repository contracts already bound in the
history:

| Evidence | Identity and exact location | Observation used here |
| --- | --- | --- |
| Jamil accepted manuscript | `SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS`, SHA-256 `a20bcda2adcc45d8d07bb27458a55f07a3c13886f4276775b214f1b7a377d970`; §2.2.2 PDF p.11 Eq.6–7, Appendix PDF pp.58–59 Table A.2 | `h_s=h_c J_C J_L J_B J_S J_R J_mu`; `h_c=j_i c_p G Pr^(-2/3)`; `J_mu` is symbolically separate. |
| Thome relevant chapter cross-check | `THOME-2004-EDB3-CH3-CROSSCHECK`, SHA-256 `326cf8a5c26d6010b701acc9459424391a59a67c08e28e0a41c699c5b9146ea4`; §3.4.6 printed p.3-12 Eq.3.4.23 and surrounding liquid paragraph | `mu_wall` uses a wall temperature obtained from a preliminary heat-transfer calculation; the acquired text does not select the coefficient used for that preliminary calculation. |
| TASK026 native selector | `R8_TASK026_SELECTOR`; `nusselt_selector.py` blob `750d92e2da2284202190afe93cf47589eb3a6bb2`; `single_phase.py` blob `90a39ab66dd3b2600f228cf513bf398c9c0cb254` | Native CWT, CHF, transition and turbulent C3 branches are explicit; the native pipeline has no Jμ wall-temperature input. |
| TASK026 semantic contract | `docs/tasks/TASK-007-tube-annulus-correlations.md`, accepted native source identity; file SHA-256 `c650cc275d05972afd0f86eb80d1c5eaf303a91cfa305b771314f731bd4130cb` | Native tube film semantics and domains are scoped to TASK026; no TASK172 preliminary-wall-producer transfer edge is defined. |
| TASK032/TASK033 boundary | `docs/tasks/TASK-032-shell-and-tube-shell-side-single-phase-flow-state.md`; `docs/tasks/TASK-033-shell-and-tube-shell-side-single-phase-heat-transfer.md` | TASK032 is a single bulk-flow snapshot and TASK033 is screening HTC; neither authorizes this preliminary wall-state calculation or automatic wall-viscosity iteration. |

The source chain therefore supplies a wall-temperature prerequisite and native
film formulas, but not a selected TASK172 preliminary-film contract.

## 4. Shell-side preliminary film review

### 4.1 Candidate matrix

The source-level Jamil/Thome representation and the four possible preliminary
choices are kept separate:

| Candidate | Candidate definition | Evidence status | Transfer disposition |
| --- | --- | --- | --- |
| A | `h_c = j_i c_p G Pr^(-2/3)` | Jamil/Thome ideal coefficient is source-bound as a component, but not identified as the preliminary wall-temperature coefficient | Not selected |
| B | `h_c J_C J_L J_B J_S J_R`, excluding `J_mu` | Geometry-correction product is source-bound as part of the final operational representation, but no preliminary-use rule is stated | Not selected; choosing it to avoid a loop would be convenience |
| C | `h_c J_C J_L J_B J_S J_R J_mu` | Final Jamil product is source-bound, but using it before `mu_wall` is known is not identified as the preliminary calculation | Not selected; would create a conditional loop |
| D | another source-defined coefficient | No citation/body in the accepted chain binds one | Not bound |
| E | no preliminary coefficient | Fail-closed disposition when A–D are not source-selected | Current governance state |

The Thome wording that wall temperature is obtained from a preliminary
heat-transfer calculation is not an equation, coefficient identity, or
combination rule.  It does not establish whether the preliminary shell film
is ideal-only, geometry-corrected without `J_mu`, fully corrected with
`J_mu`, or another source-defined quantity.  No additional source is silently
selected to fill that gap.

```ini
PRELIMINARY_SHELL_FILM_SOURCE_RULE_BOUND=false
PRELIMINARY_SHELL_FILM_SOURCE_ID=SRC-ECM-JAMIL-GORAYA-SHAHZAD-ZUBAIR-2020-BELL-DELAWARE-PARAMETERS;THOME-2004-EDB3-CH3-CROSSCHECK
PRELIMINARY_SHELL_FILM_SOURCE_LOCATION=JAMIL_EQ6_EQ7_TABLE_A2;THOME_SECTION_3.4.6_PRINTED_P3-12_EQ3.4.23_AND_PRELIMINARY_HEAT_TRANSFER_WORDING
PRELIMINARY_SHELL_FILM_DEFINITION_STATUS=UNBOUND
PRELIMINARY_SHELL_FILM_DEFINITION=SOURCE_ONLY_REQUIRES_PRELIMINARY_HEAT_TRANSFER_CALCULATION;NO_COEFFICIENT_OR_CORRECTION_SET_SELECTED
PRELIMINARY_SHELL_FILM_INCLUDES=UNRESOLVED
PRELIMINARY_SHELL_FILM_USES_JMU=undetermined
PRELIMINARY_SHELL_FILM_TRANSFER_AUTHORITY_BOUND=false
```

### 4.2 Native TASK166 comparison

The native operational identities themselves are not changed:

```ini
TASK166_NATIVE_IDEAL_FILM_IDENTITY_BOUND=true
TASK166_NATIVE_IDEAL_FILM_IDENTITY=ji*cp*G*Pr^(-2/3)
TASK166_NATIVE_GEOMETRY_CORRECTION_SET_IDENTITY_BOUND=true
TASK166_NATIVE_GEOMETRY_CORRECTION_SET=Jc*Jl*Jb*Js*Jr
PRELIMINARY_SHELL_FILM_TASK166_TRANSFER_COMPATIBLE=false
```

The last field is false because the preliminary role and its dependency on
`J_mu` are not source- or lifecycle-bound.  It is not a finding that the
native TASK166 identities are internally invalid, and it does not authorize a
new term or a change to TASK166.

## 5. Tube-side preliminary film review

### 5.1 Native branch identity

TASK026 provides a real native film family, but the current gate has no
case-bound branch, thermal-boundary condition, or preliminary transfer edge.
The exact native branch family is recorded for audit rather than selected as
a new wall-producer authority:

```ini
PRELIMINARY_TUBE_FILM_SOURCE_RULE_BOUND=true
PRELIMINARY_TUBE_FILM_SOURCE_ID=R8_TASK026_SELECTOR;SRC-T172-REPO-TUBE
PRELIMINARY_TUBE_FILM_DEFINITION_STATUS=PARTIALLY_BOUND
PRELIMINARY_TUBE_FILM_DEFINITION=CASE_SELECTED_EXACT_TASK026_R8_BRANCH_REQUIRED;LAMINAR_CWT_OR_LAMINAR_CHF_OR_TURBULENT_C3;NO_SINGLE_BRANCH_SELECTED
TASK026_PRELIMINARY_FILM_BRANCH_ID=TASK026_NATIVE_BRANCH_SELECTED_BY_CASE
TASK026_PRELIMINARY_FILM_METHOD=TASK026_R8_SINGLE_PHASE_TUBE_THERMAL_PIPELINE
TASK026_PRELIMINARY_FILM_STATE_BASIS=CALLER_SUPPLIED_SINGLE_PROPERTY_SNAPSHOT_RHO_MU_K_CP;NATIVE_BRANCH_HAS_NO_JMU_WALL_STATE_INPUT
TASK026_PRELIMINARY_FILM_AREA_BASIS=TOTAL_PARALLEL_FLOW_AREA_FOR_VELOCITY_AND_HYDRAULIC_DIAMETER_FOR_HI;LOCAL_WALL_AREA_MAPPING_NOT_DEFINED_HERE
TASK026_PRELIMINARY_FILM_SOURCE_ID=R8_TASK026_SELECTOR
TASK026_PRELIMINARY_FILM_ACTIVE_WALL_CORRECTION_REQUIRED=undetermined
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
```

The native equations are preserved exactly for identity purposes:

* CWT: `Nu_D=3.66`, `h_i=Nu_D k/D_h`, with native `Re<2300` and `Pr>0.6`;
* CHF: `Nu_D=4.36`, `h_i=Nu_D k/D_h`, with the same native laminar envelope;
* transition: `2300<=Re<3000`, no correlation is applicable;
* turbulent C3: `f=(0.790 ln(Re)-1.64)^(-2)` followed by the native
  Gnielinski relation and `h_i=Nu k/D_h`, with native evaluator envelope
  `3000<=Re<=5000000` and `0.5<=Pr<=2000`.

The reviewed TASK026 branch dispositions do not provide one universal
preliminary film.  CWT and CHF are constant-property scopes and explicitly do
not create a variable-property wall correction.  The reviewed C3 correction
is a separate case-level path requiring its own located wall state and source
preconditions.  Therefore this record does not decide whether a future
preliminary calculation may use an uncorrected native C3 film, a C3 active
correction, or a laminar constant-property branch.  A neutral factor or
silent omission is not introduced.

### 5.2 Source versus TASK172 transfer

`PRELIMINARY_TUBE_FILM_SOURCE_RULE_BOUND=true` means that TASK026's native
branch definitions exist in their native task scope.  It does not mean that
TASK026 has been selected as the film input to a future Jμ wall producer.
That separate transfer would need an exact branch, located state and area
basis, preliminary-use rule, branch/dependency policy and case binding.

```ini
PRELIMINARY_TUBE_FILM_SOURCE_RULE_BOUND=true
PRELIMINARY_TUBE_FILM_TRANSFER_AUTHORITY_BOUND=false
PRELIMINARY_TUBE_FILM_TRANSFER_LIMITATION=TASK026_NATIVE_SCOPE_DOES_NOT_DEFINE_TASK172_PRELIMINARY_WALL_PRODUCER_ROLE_OR_BRANCH_SELECTION
```

## 6. Film dependency graph

Only film-side dependencies are classified here.  Q remains an external
unresolved input and is intentionally not used to select a film.

```text
candidate preliminary shell film
  → clean radial wall state
  → shell-fluid wall viscosity
  → J_mu
  → corrected shell film or downstream thermal path

candidate preliminary tube film
  → clean radial wall state
  → (possibly) tube wall-state-dependent correction
```

Because no preliminary shell choice has been authorized, and because the
native TASK026 branch is not selected for this producer, the dependency
classification remains:

```ini
SHELL_FILM_DEPENDS_ON_JMU=undetermined
TUBE_FILM_DEPENDS_ON_WALL_STATE=undetermined
TUBE_FILM_DEPENDS_ON_ACTIVE_WALL_CORRECTION=undetermined
SHELL_FILM_CREATES_JMU_FIXED_POINT=undetermined
JMU_WALL_COUPLING_CIRCULARITY_ACTIVE=undetermined
```

The conditional path is identified, but it is not an active numerical loop.
Selecting C would make the film-side contribution active; selecting an
authorized source-defined film that excludes `J_mu` could make that
contribution inactive.  This record chooses neither and performs no
iteration.

## 7. Preserved non-film boundaries

The following fields are carried forward exactly and are not resolved here:

```ini
EXTERNAL_Q_INSTANCE_PRESENT=false
REAL_EXTERNAL_Q_RECEIPT_CREATED=false
EXTERNAL_Q_RECEIPT_REVIEW_ELIGIBLE=false
QUALIFIED_Q_AUTHORITY_BOUND=false
Q_INPUT_AUTHORITY_BOUND=false
Q_PRODUCER_AUTHORITY_BOUND=false
WALL_PRODUCER_K_WALL_AUTHORITY_BOUND=false
SOURCE_MEAN_BULK_TEMPERATURE_PRODUCER_BOUND=false
LOCAL_RADIAL_WALL_STATE_TO_SOURCE_JMU_MAPPING_BOUND=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
```

No material, `k_wall`, bulk-state producer, global/local wall-temperature
aggregation, wall-temperature node mapping, Jμ implementation, tolerance,
solver or mesh rule is added.  TASK034 wall state, TASK162 `q_method`,
TASK163 projection and any caller-supplied field named `Q` remain excluded as
preliminary-film authority.

## 8. Decision

The smallest direct finding is source ambiguity for the shell preliminary
film, plus a missing TASK172 transfer edge and branch selection for the tube
preliminary film.  The source-rule observations are not promoted into a
producer authority.

```ini
RESULT=BLOCKED
OUTCOME=OUTCOME_F_SOURCE_AMBIGUITY_REMAINS
JMU_PRELIMINARY_FILM_AUTHORITY_CANDIDATE_CREATED=false
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

This is a correct fail-closed result.  It does not say that native shell or
tube HTC calculations are unavailable; it says that their use as the
preliminary inputs of a future Jμ wall-temperature producer has not been
source- and transfer-authorized.

## 9. Effective TASK172 state and governance

The four entry blockers remain exactly unchanged:

```ini
REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
TASK172_ENTRY_REVIEW_PENDING=true
```

This is an evidence-only append.  Historical R1/R2 source and authority
records are immutable:

```ini
HISTORICAL_RECORDS_REWRITTEN=false
LIFECYCLE_PROMOTION_PERFORMED=false
NEW_AUTHORITY_SELF_APPROVAL=false
ENGINEERING_RULES_CHANGED=false
TASK162_CHANGED=false
TASK163_CHANGED=false
TASK166_CHANGED=false
TASK171_SEMANTICS_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
Q_RECEIPT_CREATED=false
EXTERNAL_Q_AUTHORITY_INJECTION_SUPPORTED=false
WALL_TEMPERATURE_SOLVE_EXECUTED=false
FIXED_POINT_ITERATION_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 10. Next gate and final receipt

The direct film gap remains independently visible.  The next gate below is
only a suggested, separately authorized source/transfer resolution; this
record does not execute it.  A material or source-mean gate may be authorized
separately, but must not silently close the film gap.

```ini
EVIDENCE_PATH=docs/tasks/evidence/TASK-172-shell-wall-correction-jmu-preliminary-film-authority-r2.json
REGISTRY_PATH=docs/tasks/TASK-172-v0.7-authority-registry-r1.json
JMU_PRELIMINARY_FILM_AUTHORITY_CANDIDATE_CREATED=false
RUNTIME_PRODUCER_CREATED=false
NUMERICAL_EXECUTION_PERFORMED=false
NEXT_GATE=AUTHORIZE_TASK172_SHELL_WALL_CORRECTION_JMU_PRELIMINARY_FILM_SOURCE_AND_TRANSFER_RESOLUTION_R3_ONLY
STOP=true
```

The final head, validation and CI identifiers are completed in the companion
evidence/registry overlay and final task response after the controlled commit.
