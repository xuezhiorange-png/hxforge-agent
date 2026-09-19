# TASK172 — C3 preliminary tube-film role policy authority R1

## 1. Scope and result

This documentation/evidence-only record audits one remaining prerequisite of
the reviewed TASK026-to-TASK172 preliminary tube-film transfer contract: the
role of the turbulent C3/Gnielinski film during a future preliminary
wall-temperature calculation.  It does not create a case, a property
snapshot, a film instance, a wall temperature, or a numerical iteration.  It
does not change TASK026, TASK166, the reviewed transfer contract, or the
accepted C3 wall-correction authority.

```ini
TASK_ID=TASK172_V0_7_JMU_PRELIMINARY_TUBE_FILM_C3_PRELIMINARY_ROLE_POLICY_AUTHORITY_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
AUTHORIZED_PREDECESSOR_HEAD=2a864b0be7622328132ad3faccac34ef11d0cec9
MODE=C3_PRELIMINARY_ROLE_POLICY_AUTHORITY_ONLY
SUBJECT_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
RESULT=BLOCKED
OUTCOME=OUTCOME_D_SOURCE_ORDERING_AMBIGUOUS
```

The accepted C3 authority defines a wall-property correction for the native
turbulent branch.  It does not, however, say whether a future preliminary
wall-state calculation must consume the native/base C3 film, the corrected
C3 film, or another coefficient.  That missing ordering is kept as an
explicit fail-closed gap.

## 2. Accepted C3 authority and immutable predecessor

The already accepted model-level authority is inspected only for its source,
inputs, and ordering semantics:

```ini
C3_ACTIVE_CORRECTION_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
C3_ACTIVE_CORRECTION_LIFECYCLE_STATUS=REVIEWED_AUTHORITY
C3_ACTIVE_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
C3_ACTIVE_CORRECTION_SOURCE_ID=SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3
C3_ACTIVE_CORRECTION_SOURCE_LOCATION=§7.4.1.1.1 Eqs. (739)-(744), report pp. 177-179
C3_ACTIVE_CORRECTION_FORM=Nu_turb=Nu_Gnielinski*(Pr_liq/Pr_w)^0.11; h_i=Nu*k/D_h
C3_ACTIVE_CORRECTION_REQUIRED_INPUTS=TASK026_NATIVE_C3_BASE;Pr_liq;Pr_w;0.05<=Pr_liq/Pr_w<=20;wall-property-state;native-Re-and-Pr-domains;internal-circular-tube-geometry
```

The source byte identity and the accepted authority evidence remain immutable:

| Artifact | Identity | Role in this gate |
| --- | --- | --- |
| RELAP-7 Theory Manual | `INL-EXT-14-31366-R3`; source bytes SHA-256 `ff25dc788b5fbefd91e9dda2e643332c35ff2e2f9acce7f9bfcb2bc8e2d48c75` | Source of the accepted C3 branch and wall-property relation. |
| Accepted C3 authority evidence | `docs/tasks/evidence/TASK-172-tube-wall-correction-authority-independent-review-r1.json`; canonical hash `009ced2f2203bca76221bf64316f37fd914d1687da8a54e2d8a135e094ac6fdc` | Immutable source/transfer authority record audited here. |
| Reviewed transfer contract | `V07-T172-JMU-PRELIMINARY-TUBE-FILM-TRANSFER-CONTRACT-R5` | Model-level contract remains reviewed; it deliberately leaves the C3 preliminary role policy unresolved. |

The native selector and the accepted C3 authority are not re-audited for
their existence or formula.  This gate asks only whether they contain an
ordering rule for preliminary wall-state use.

## 3. Ordering evidence review

The accepted source makes the turbulent branch and its wall-property input
explicit.  The reviewed locations provide the following observations:

| Location | What is stated | What is not stated |
| --- | --- | --- |
| §7.4.1.1.1, Eqs. (739)–(741) | The source describes a liquid wall-heat-transfer model and gives a Gnielinski turbulent branch. | It does not identify which coefficient is to be used as a preliminary wall-temperature film. |
| §7.4.1.1.1, Eq. (744) | The turbulent result is multiplied by `(Pr_liq/Pr_w)^0.11`, with `Pr_w` evaluated at the wall temperature. | It does not prescribe that this corrected result must, or must not, participate in the calculation that produces that wall temperature. |
| Accepted TASK172 C3 authority | The correction is a separate source-qualified active correction with a required wall-property state. | It contains no preliminary-role, sequencing, fixed-point, or bootstrap rule. |
| R5/R54 transfer contract | C3 requires a separate preliminary-role policy. | It does not select base C3, corrected C3, or another preliminary coefficient. |

Therefore:

```ini
C3_PRELIMINARY_ORDERING_SOURCE_RULE_BOUND=false
C3_PRELIMINARY_ORDERING_SOURCE_ID=SRC-T172-RELAP7-TUBE-GNIELINSKI-WALL-R3
C3_PRELIMINARY_ORDERING_SOURCE_LOCATION=§7.4.1.1.1 Eqs. (739)-(744), report pp. 177-179; no preliminary-role ordering statement
C3_PRELIMINARY_ORDERING_RULE=UNSPECIFIED_BY_ACCEPTED_C3_SOURCE_AND_AUTHORITY
```

The source's larger branch-selection description is not treated as a
preliminary-film ordering rule.  In particular, the presence of a source
`max` branch expression cannot be used to infer a TASK172 bootstrap sequence.

## 4. Candidate role matrix

| Candidate | Preliminary film | Source-authorized? | Disposition |
| --- | --- | --- | --- |
| A | Native/base TASK026 C3 Gnielinski `h_i`, without the accepted active correction | `false` | The accepted source does not say that the base coefficient is the preliminary wall-temperature input. Choosing it only to avoid coupling would be engineering convenience. |
| B | Native C3 `h_i` with `V07-T172-TUBE-WALL-CORRECTION-R1` | `false` | The correction requires a wall-property state, but the source does not say that its corrected result must participate in producing that same wall state. |
| C | Another preliminary C3 coefficient or sequence | `false` | No other source-defined coefficient or ordering rule is bound in the accepted C3 chain. |
| D | No selected coefficient; fail closed | `true` as current disposition | Until A, B, or C is source-bound, C3 preliminary use is blocked. This is a disposition, not a neutral film value. |

The gate therefore records no `C3_CORRECTION_FACTOR=1`, no omitted-correction
authority, and no implicit preliminary coefficient.

```ini
C3_BASE_FILM_AS_PRELIMINARY_SOURCE_AUTHORIZED=false
C3_CORRECTED_FILM_AS_PRELIMINARY_SOURCE_AUTHORIZED=false
C3_OTHER_PRELIMINARY_FILM_SOURCE_AUTHORIZED=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY_BOUND=false
C3_PRELIMINARY_FILM_WALL_CORRECTION_POLICY=UNRESOLVED_BASE_OR_CORRECTED_C3_PRELIMINARY_ROLE
```

## 5. State and coupling semantics

The accepted C3 relation uses the wall-temperature-dependent `Pr_w` state.
Consequently the active correction itself depends on a wall state.  Whether
the *preliminary* film depends on that correction cannot be decided until an
ordering rule selects candidate A or B:

```ini
C3_ACTIVE_CORRECTION_DEPENDS_ON_WALL_STATE=true
C3_PRELIMINARY_FILM_DEPENDS_ON_WALL_STATE=undetermined
C3_PRELIMINARY_FILM_DEPENDS_ON_ACTIVE_CORRECTION=undetermined
C3_PRELIMINARY_FILM_CREATES_WALL_STATE_LOOP=undetermined
```

The potential dependency is not silently converted into a numerical loop:

```text
selected preliminary C3 film
  → future wall-temperature producer
  → wall property state
  → accepted active C3 correction, if selected
  → final C3 film
```

No iteration, relaxation, tolerance, bootstrap, fallback, or last-iterate
acceptance is authorized by this record.  If a future source rule selects the
corrected C3 coefficient in the preliminary calculation, the resulting
coupling must be handled by a separately authorized closure and numerical
authority.

## 6. Branch and transfer boundaries

The reviewed model-level transfer contract is unchanged:

```ini
TRANSFER_CONTRACT_STATUS=REVIEWED_TUBE_FILM_TRANSFER_CONTRACT
TASK026_TO_TASK172_TRANSFER_CONTRACT_BOUND=true
CWT_PRELIMINARY_TRANSFER_CONTRACT_BOUND=true
CHF_PRELIMINARY_TRANSFER_CONTRACT_BOUND=true
TRANSITION_PRELIMINARY_FILM_AVAILABLE=false
C3_PRELIMINARY_TRANSFER_CONTRACT_SHAPE_BOUND=true
C3_PRELIMINARY_ROLE_POLICY_REQUIRED=true
```

CWT and CHF remain paused pending real case-bound transfer receipts; their
constant-property scopes do not answer the C3 ordering question:

```ini
CWT_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
CHF_BRANCH_STATUS=PAUSED_PENDING_REAL_CASE_BOUND_TRANSFER_RECEIPT
C3_BRANCH_STATUS=ACTIONABLE_AUTHORITY_GAP
```

No real case or instance exists, and no branch-specific receipt is eligible:

```ini
REAL_CASE_BOUND_TUBE_FILM_TRANSFER_INSTANCE_PRESENT=false
REAL_PRELIMINARY_TUBE_FILM_INSTANCE_PRESENT=false
PRELIMINARY_TUBE_FILM_INSTANCE_AUTHORITY_BOUND=false
C3_CASE_BOUND_TRANSFER_RECEIPT_REVIEW_ELIGIBLE=false
TASK026_TO_TASK172_TUBE_BULK_STATE_MAPPING_BOUND=false
TASK026_TO_TASK172_PHYSICAL_SUPPORT_MAPPING_BOUND=false
```

This policy audit does not alter the R5/R54 case, support, area, or
property-snapshot identity requirements.

## 7. Decision and next gate

The exact C3 correction is accepted at model level, but the source chain does
not specify its preliminary role or ordering.  The correct disposition is a
blocked, narrowly scoped authority gap:

```ini
C3_PRELIMINARY_ROLE_SOURCE_RULE_BOUND=false
C3_PRELIMINARY_ROLE_TRANSFER_AUTHORITY_BOUND=false
JMU_PRELIMINARY_C3_ROLE_POLICY_AUTHORITY_CANDIDATE_CREATED=false
RESULT=BLOCKED
OUTCOME=OUTCOME_D_SOURCE_ORDERING_AMBIGUOUS
```

The shell wall correction and the effective TASK172 entry ledger remain
unchanged:

```ini
JMU_EXECUTABLE_AUTHORITY_BOUND=false
SHELL_WALL_CORRECTION_STATUS=BLOCKED
SHELL_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKERS=SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
EFFECTIVE_REMAINING_TASK172_ENTRY_BLOCKER_COUNT=4
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The smallest next authority task is to acquire or identify a source that
explicitly governs C3 preliminary-film ordering, without selecting a value
or implementing a loop:

```ini
NEXT_GATE=AUTHORIZE_TASK172_JMU_PRELIMINARY_TUBE_FILM_C3_PRELIMINARY_ROLE_ORDERING_AUTHORITY_RESOLUTION_R2_ONLY
```

## 8. Governance

Only this audit document, its machine-readable evidence, and an append-only
registry extension are in scope.  Historical payloads and hashes remain
immutable.  No production behavior is claimed:

```ini
C3_POLICY_INVENTED=false
TASK026_CHANGED=false
TASK166_CHANGED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
NUMERICAL_WORK_STARTED=false
REAL_CASE_CONSTRUCTED=false
REAL_TRANSFER_INSTANCE_CONSTRUCTED=false
FIXED_POINT_ITERATION_PERFORMED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
