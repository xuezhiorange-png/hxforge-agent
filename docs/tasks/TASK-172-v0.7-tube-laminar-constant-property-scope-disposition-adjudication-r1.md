# TASK172 R1 — laminar constant-property branch-scope disposition adjudication

## 1. Receipt and decision boundary

This is a documentation-only semantic adjudication for the unresolved
`TUBE-WALL-CORRECTION-AUTHORITY` entry blocker.  It does not acquire another
source and does not promote a correction, omission, or case-level authority.
The adjudication asks only whether the two exact native TASK026 laminar
branches can be admitted within the constant-property scope of their
reviewed source model while rejecting any variable-property extension that
lacks a separate reviewed authority.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_CONSTANT_PROPERTY_SCOPE_DISPOSITION_ADJUDICATION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=e35f1508613e129350e5af5a8290526b9b66bc7a
PREVIOUS_HEAD_SHA=e35f1508613e129350e5af5a8290526b9b66bc7a
MODE=LAMINAR_SOURCE_SCOPE_DISPOSITION_ADJUDICATION_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_WITH_BLOCKER_RETAINED
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The result is a proposed branch-scope disposition, not an external review or
an approval of a future property implementation.  The two branch candidates
remain `PROPOSED_AUTHORITY` until the separately authorized independent-review
gate is completed.

## 2. Adjudication outcome

The exact source body already acquired in
[the R1 primary-source receipt](TASK-172-v0.7-tube-laminar-primary-source-acquisition-r1.md)
is `NASA-CR-189922`, SHA-256
`46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e`.
Its Chapter 3 derivation separately gives the fully developed circular-tube
constant-wall-temperature and constant-heat-flux solutions and explicitly
uses a constant nominal property set.  The source is therefore sufficient to
define the *scope of the native analytical model*.  It is not an authority
for a variable-property wall/bulk extension, an active correction, or an
explicit claim that no correction is ever needed.

The adjudication is:

```ini
ADJUDICATION_OUTCOME=CONSTANT_PROPERTY_BRANCH_SCOPE_DISPOSITION_VALID
CWT_SOURCE_SCOPE_EXCLUDES_VARIABLE_PROPERTY_EXTENSION=true
CHF_SOURCE_SCOPE_EXCLUDES_VARIABLE_PROPERTY_EXTENSION=true
EXCLUSION_MEANING=NOT_COVERED_BY_THIS_AUTHORITY_NOT_PHYSICALLY_IMPOSSIBLE
CWT_SCOPE_AUTHORITY_CANDIDATE_COMPLETE=true
CHF_SCOPE_AUTHORITY_CANDIDATE_COMPLETE=true
```

Here `excludes` is a source-coverage statement.  It does not assert that
temperature-dependent properties are physically invalid; it says that such a
use is outside the acquired native authority and requires a separate,
compatible, reviewed extension.

## 3. Three wall-property semantics kept separate

The following meanings are not interchangeable:

* `NO_ACTIVE_WALL_CORRECTION_REQUIRED` would require a source to say that
  differing wall/bulk properties need no correction.  That evidence is not
  present and is not claimed here.
* `ACTIVE_WALL_PROPERTY_CORRECTION` would require a source-qualified equation,
  states, domain, and combination rule.  No such rule is created here.
* `VARIABLE_PROPERTY_USE_NOT_AUTHORIZED_WITHOUT_EXTENSION` means that the
  native source is constant-property-only, so any branch calculation that
  reevaluates properties with local, bulk, or wall temperature, or applies a
  property-ratio correction, is blocked until a separate extension authority
  exists.

Accordingly:

```ini
CWT_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CHF_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CWT_ACTIVE_CORRECTION_AUTHORITY=NONE
CHF_ACTIVE_CORRECTION_AUTHORITY=NONE
CWT_VARIABLE_PROPERTY_EXTENSION_AUTHORITY=ABSENT
CHF_VARIABLE_PROPERTY_EXTENSION_AUTHORITY=ABSENT
```

The native selector flag `requires_wall_viscosity=false`, the rounded values
`3.66` and `4.36`, a narrow water range, a neutral factor, or the accepted
turbulent C3 authority cannot substitute for either missing authority.

## 4. Source-bound native branch semantics

### 4.1 CWT

| Field | Bound source semantics |
| --- | --- |
| Authority candidate | `V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1` |
| Authority type | `CONSTANT_PROPERTY_BRANCH_SCOPE` |
| Component scope | `TUBE_LAMINAR_CWT` |
| Native identity | `tube_laminar_cwt@1.0.0` |
| Boundary condition | `CONSTANT_WALL_TEMPERATURE` |
| Source body | `NASA-CR-189922`, `SRC-T172-NASA-CR-189922-CWT-R1` |
| Exact location | Chapter 3 §3.3.3; report pp.14–16 and 19–20; Eqs.3.20a, 3.28, 3.47–3.51; PDF pp.28–34 (1-indexed) |
| Source equation | `Nu_D = 3.658` (Eq.3.51), carried by native TASK026 as `Nu_D = 3.66` |
| Property model | `CONSTANT_NOMINAL_PROPERTIES_IN_ANALYTICAL_MODEL` |
| Constant-property use | `AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE` |
| Variable-property use | `BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY` |
| Active correction | `NOT_DEFINED_BY_THIS_AUTHORITY` |
| Omission claim | `NOT_CLAIMED` |
| Candidate lifecycle | `PROPOSED_AUTHORITY` |

### 4.2 CHF

| Field | Bound source semantics |
| --- | --- |
| Authority candidate | `V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1` |
| Authority type | `CONSTANT_PROPERTY_BRANCH_SCOPE` |
| Component scope | `TUBE_LAMINAR_CHF` |
| Native identity | `tube_laminar_chf@1.0.0` |
| Boundary condition | `CONSTANT_HEAT_FLUX` |
| Source body | `NASA-CR-189922`, `SRC-T172-NASA-CR-189922-CHF-R1` |
| Exact location | Chapter 3 §3.3.2; report pp.14–19; Eqs.3.20a, 3.28, 3.39–3.46; PDF pp.28–33 (1-indexed) |
| Source equation | `Nu_D = 4.364` (Eq.3.46), carried by native TASK026 as `Nu_D = 4.36` |
| Property model | `CONSTANT_NOMINAL_PROPERTIES_IN_ANALYTICAL_MODEL` |
| Constant-property use | `AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE` |
| Variable-property use | `BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY` |
| Active correction | `NOT_DEFINED_BY_THIS_AUTHORITY` |
| Omission claim | `NOT_CLAIMED` |
| Candidate lifecycle | `PROPOSED_AUTHORITY` |

CWT and CHF remain separate identities.  The CWT source is not transferred to
CHF, and the CHF source is not transferred to CWT.

## 5. Constant-property case definition

For either exact native branch, a `CONSTANT_PROPERTY_CASE` is a case in which
all of the following are true:

1. The branch receives one approved, frozen property snapshot for the
   calculation, rather than a sequence of properties reevaluated from local,
   bulk, film, or wall temperature.
2. The branch does not consume a wall-state-dependent property pair.
3. No bulk/wall property ratio is evaluated or applied.
4. No variable-property correction or replacement relation is claimed.
5. The exact native branch identity, its existing domain, its circular-tube
   basis, its fully developed assumptions, and its own thermal boundary
   condition remain satisfied.

The snapshot may be carried as an explicit upstream input; it is not inferred
from a material name, a backend default, or a hidden database lookup.  This
definition describes branch consumption semantics, not a new property source
or a new numerical tolerance.

```ini
CONSTANT_PROPERTY_CASE_DEFINITION=ONE_FROZEN_PROPERTY_SNAPSHOT;NO_WALL_OR_BULK_PROPERTY_REEVALUATION;NO_PROPERTY_RATIO;NO_VARIABLE_PROPERTY_CORRECTION_OR_REPLACEMENT;EXACT_NATIVE_BRANCH_DOMAIN_AND_BOUNDARY_REQUIRED
```

## 6. Relation to a future wall-temperature field

`T_wall != T_bulk` alone does not imply variable-property use by the laminar
branch.  A future TASK172 wall model may expose temperatures for a surface
network while a native branch still consumes one frozen property snapshot.  In
that case the temperature field is non-isothermal, but the branch remains a
constant-property model under the definition above.

Variable-property use exists when the branch calculation itself evaluates or
changes fluid properties as functions of a local, bulk, film, or wall
temperature, or applies a property-ratio correction/replacement.  That use is
outside both candidates and must fail closed.

```ini
WALL_TEMPERATURE_DIFFERENCE_ALONE_IMPLIES_VARIABLE_PROPERTY=false
WALL_STATE_PROPERTY_REEVALUATION_IMPLIES_VARIABLE_PROPERTY=true
WALL_STATE_REEVALUATION_RULE=TRUE_ONLY_WHEN_THE_LAMINAR_BRANCH_CONSUMES_OR_RECOMPUTES_PROPERTIES_AS_A_FUNCTION_OF_LOCAL_BULK_FILM_OR_WALL_TEMPERATURE
```

This distinction does not authorize a wall solver, a viscosity correction, a
property backend, or a hidden conversion from a variable-property state to a
constant snapshot.

## 7. Branch admission and fail-closed rule

The proposed scope candidates admit only the source-qualified native use:

```ini
CWT_BRANCH_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
CWT_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CWT_SCOPE_AUTHORITY_CANDIDATE_STATUS=PROPOSED_AUTHORITY

CHF_BRANCH_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
CHF_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CHF_SCOPE_AUTHORITY_CANDIDATE_STATUS=PROPOSED_AUTHORITY
```

Any of the following is outside the candidate scope and must produce the
typed fail-closed disposition below:

* variable-property evaluation;
* wall-property or bulk-property reevaluation inside the branch;
* a bulk/wall property ratio;
* a correction or replacement equation not contained in the native authority;
* a reference-temperature extension not contained in the native authority.

```ini
VARIABLE_PROPERTY_OUTCOME=BLOCKED_MISSING_LAMINAR_VARIABLE_PROPERTY_EXTENSION_AUTHORITY
NO_SILENT_FALLBACK_TO_CWT_NU_3_66=true
NO_SILENT_FALLBACK_TO_CHF_NU_4_36=true
```

This is a branch-level scope restriction, not an omission approval.  It does
not claim that the native branch is suitable for every future TASK172 case.

## 8. Parent blocker and effective state

Both candidates must pass their own independent-review gate before they can be
used in a whole-branch closure adjudication.  Therefore this task does not
close the parent blocker:

```ini
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The previously accepted turbulent correction remains independent and
unchanged:

```ini
TURBULENT_C3_CORRECTION_STATUS=REVIEWED_AUTHORITY
TURBULENT_C3_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
TURBULENT_C3_SCOPE_NOT_TRANSFERRED_TO_LAMINAR=true
```

## 9. Source and historical evidence boundary

The following existing records are inherited without rewriting:

* [TASK172 laminar source acquisition R1](TASK-172-v0.7-tube-laminar-primary-source-acquisition-r1.md)
  — complete NASA-CR-189922 body and exact CWT/CHF constant-property
  derivation locations.
* [TASK172 exact-boundary acquisition R3](TASK-172-v0.7-tube-laminar-exact-boundary-variable-property-source-acquisition-r3.md)
  — Herwig 1985/1989 and Koppel/Smith bodies were not lawfully acquired, so
  no variable-property equation was transcribed.
* [TASK172 laminar correction/omission adjudication](TASK-172-v0.7-tube-laminar-wall-correction-or-omission-authority-adjudication-r1.md)
  — the native `requires_wall_viscosity=false` flag is not an omission
  authority.

The source-body hash, source locations, and rights status come from the
existing R1 source package.  No search snippet, abstract, remembered
Sieder–Tate exponent, NACA non-water result, neutral factor, or library result
is used as authority.

## 10. Governance disposition

```ini
HISTORICAL_RECORDS_REWRITTEN=false
NATIVE_CWT_IDENTITY_CHANGED=false
NATIVE_CHF_IDENTITY_CHANGED=false
NATIVE_CWT_CONSTANT_CHANGED=false
NATIVE_CHF_CONSTANT_CHANGED=false
TASK026_CHANGED=false
TURBULENT_C3_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
NEW_AUTHORITY_SELF_APPROVAL=false
LIFECYCLE_PROMOTION_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

The next gate is intentionally limited to independent review of these two
proposed branch-scope authorities:

```ini
NEXT_GATE=AUTHORIZE_TASK172_TUBE_LAMINAR_CONSTANT_PROPERTY_SCOPE_AUTHORITIES_INDEPENDENT_REVIEW_R1_ONLY
```

That review may accept or reject the model-level scope candidates.  It must
not be treated as approval of an actual material case, an active wall
correction, a variable-property solver, or production readiness.
