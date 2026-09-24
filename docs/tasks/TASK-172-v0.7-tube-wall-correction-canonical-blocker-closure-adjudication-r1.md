# TASK172 — tube wall-correction canonical blocker closure adjudication R1

## Receipt and immutable boundary

```ini
TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ADJUDICATION_R1
PR_NUMBER=277
PREVIOUS_HEAD_SHA=85b576e5b95255da9ae403914bc492b928365e57
MODE=CANONICAL_BLOCKER_SEMANTIC_ADJUDICATION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
SUBJECT_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
RESULT=PASS_WITH_BLOCKER_RETAINED
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This receipt answers what the historical
`TUBE-WALL-CORRECTION-AUTHORITY` canonical entry blocker covers.  It does not
promote an authority, remove the blocker, select a material or property
instance, change TASK026, or authorize implementation.  R1–R26 records are
immutable; this is an append-only semantic adjudication.

## Adjudication result

```ini
ADJUDICATION_OUTCOME=BLOCKER_REMAINS_INCOMPLETE_TUBE_BRANCH_COVERAGE
CANONICAL_BLOCKER_SEMANTICS=MODEL_LEVEL_COMPLETE_TUBE_BRANCH_COVERAGE_AUTHORITY
SEMANTIC_CONTRACT_CORRECTION_REQUIRED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
```

The blocker is a model-level authority-coverage blocker.  It closes only when
every tube correlation path admitted by the TASK026 selector has either:

1. a source-qualified, independently reviewed active wall-property correction
   compatible with that exact native branch; or
2. an independently reviewed explicit `NO_ACTIVE_WALL_CORRECTION_REQUIRED`
   disposition for that exact branch, including its source-defined boundary
   condition and applicability domain.

The currently accepted R26 authority covers only the turbulent C3 path.  It
does not silently establish either laminar omission disposition.  Therefore
the model-level coverage condition is incomplete and the canonical blocker
must remain.

This is not Outcome C.  Case-level execution readiness is a distinct,
fail-closed admission gate already represented by the R26 case-level contract.
It is not a reason to close the model-level coverage blocker.  Historical
records mention case prerequisites while describing authority issuance, but
the records do not require a taxonomy rename once the model-level branch
coverage condition and the separate case-level gate are made explicit here.

## Historical blocker-semantic audit

The following records were read as the historical source of the blocker
meaning, rather than inferring closure semantics from R26 alone.

| Immutable record | Evidence | Adjudication implication |
| --- | --- | --- |
| `TASK-172-v0.7-entry-authority-closure-r1.md` | The tube-correction entry row requires a complete transferable equation, domain and base-correlation review; no branch is declared closed. | The initial blocker is an entry/model authority requirement, not a case result. |
| `TASK-172-v0.7-wall-numerical-proposals-r1.md` | The native TASK026 Gnielinski/laminar contract is retained and the tube correction row records both branches as `UNBOUND`. | A turbulent-only correction cannot satisfy the historical tube-side scope. |
| `TASK-172-v0.7-material-active-wall-review-r3.md` | TASK026 is recorded as separate laminar CWT/CHF and turbulent paths; the laminar constants remain separate and no active correction authority is issued. | Native branch identity remains broader than the later C3 candidate. |
| `TASK-172-v0.7-material-active-wall-review-r4.md` | The requested correction is to the TASK026 tube HTC path; no neutral factor or unqualified correction is permitted. | Omission cannot be inferred from an uncorrected implementation. |
| `TASK-172-v0.7-physical-authority-semantic-source-r5.md` | The target matrix requires exact C1/C2/C3 branch/version binding and says branch-specific applicability and mapping are incomplete. | Branch coverage is part of model-level authority completeness. |
| `TASK-172-v0.7-tube-wall-correction-authority-resolution-r1.md` | The native base lists C1/C2/C3 and records no active wall correction; missing exact base, boundary semantics and domain are blockers. | The native selector cannot be reduced to C3 by the blocker name alone. |
| `TASK-172-v0.7-tube-wall-correction-primary-transfer-acquisition-r2.md` | The acquired package is explicitly `EXACT_TASK026_C3_BASE...` and remains a proposed C3 candidate. | The package is narrower than the historical whole-selector coverage question. |
| `TASK-172-v0.7-tube-wall-correction-authority-independent-review-r1.md` | The accepted review scope is `MODEL_LEVEL_TUBE_TURBULENT_WALL_PROPERTY_CORRECTION_ONLY`; `LAMINAR_BRANCH_TRANSFERRED=false`. | Independent review did not cover C1/C2. |
| `TASK-172-v0.7-tube-wall-correction-external-scoped-approval-record-r1.md` | R26 promotes only the scoped turbulent authority and explicitly keeps production/case execution disabled. | R26 lifecycle promotion is not whole-selector blocker closure. |

The registry overlay chain corroborates this reading: R23–R26 preserve the
five-blocker ledger, while R26's authority promotion is scoped to the
turbulent branch.  No historical record contains a reviewed laminar
correction or a reviewed branch-specific omission authority.

## Native TASK026 branch coverage

The reviewed native selector exposes these three branch identities:

| Branch | Native identity | Native boundary/validity | Wall-property state | TASK172 coverage |
| --- | --- | --- | --- | --- |
| Laminar CWT | `tube_laminar_cwt@1.0.0` | Circular tube, fully developed, constant wall temperature; `Re < 2300`, `Pr > 0.6` | Native definition records `requires_wall_viscosity=false` | No reviewed active correction or TASK172 omission authority |
| Laminar CHF | `tube_laminar_chf@1.0.0` | Circular tube, fully developed, constant heat flux; `Re < 2300`, `Pr > 0.6` | Native definition records `requires_wall_viscosity=false` | No reviewed active correction or TASK172 omission authority |
| Turbulent C3 | `tube_turbulent_gnielinski@1.0.0` | Native C3 domain; R26 transfer scope uses strict `3000<Re<5000000` and `0.5<=Pr<=2000` | R26 source-qualified correction uses located bulk and fluid-facing wall states | `REVIEWED_AUTHORITY` for the scoped model-level correction |

The native `requires_wall_viscosity=false` metadata and the TASK-007
no-wall-property policy describe the existing correlation behavior.  They do
not, by themselves, constitute a TASK172 reviewed omission authority for
using a future wall-temperature/property closure without an explicit
branch-level disposition.  This adjudication therefore does not infer that
laminar active correction is required, and does not infer that it is
unnecessary:

```ini
LAMINAR_CWT_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CHF_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CWT_CORRECTION_OR_OMISSION_AUTHORITY_STATUS=NOT_ESTABLISHED
LAMINAR_CHF_CORRECTION_OR_OMISSION_AUTHORITY_STATUS=NOT_ESTABLISHED
TURBULENT_C3_CORRECTION_AUTHORITY_STATUS=REVIEWED_AUTHORITY
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
```

The next branch-specific gate must decide, using exact source evidence, for
each laminar path whether an active correction is required or an explicit
reviewed omission is valid.  It must not copy the C3 equation into C1/C2,
and it must not treat the absence of a wall-property argument as proof of a
TASK172 omission authority.

## Three-level state separation

```ini
MODEL_LEVEL_TUBE_CORRECTION_AUTHORITY_STATE=PARTIALLY_COVERED
TUBE_BRANCH_COVERAGE_STATE=INCOMPLETE_LAMINAR_DISPOSITION
CASE_LEVEL_TUBE_CORRECTION_ADMISSION_STATE=REQUIRED_NOT_PRESENT_SEPARATE_FAIL_CLOSED_GATE

CASE_LEVEL_TUBE_CORRECTION_AUTHORITY_REQUIRED=true
CASE_LEVEL_TUBE_CORRECTION_AUTHORITY_PRESENT=false
CASE_LEVEL_TUBE_CORRECTION_FAIL_CLOSED_GATE_ID=TASK172-CASE-LEVEL-TUBE-WALL-CORRECTION-ADMISSION
CASE_LEVEL_TUBE_CORRECTION_GATE_STATUS=DEFINED_ACTIVE_FAIL_CLOSED_IMPLEMENTATION_PENDING
CASE_LEVEL_TUBE_CORRECTION_GATE_RUNTIME_IMPLEMENTED=false
PRODUCTION_WITHOUT_REQUIRED_CASE_LEVEL_TUBE_CORRECTION_AUTHORITY=BLOCKED
```

The model-level state answers whether TASK172 has authority for the tube
correction model and all admitted native branches.  The branch state answers
whether each C1/C2/C3 path has an active or explicit omission disposition.
The case-level state answers whether a particular runtime case has all
required authority instances, located states, exact identities and domain
bindings.  They must not be represented by one `CLOSED` field.

The case-level gate remains fail-closed for missing or unreviewed required
authority, wrong native base identity/version/hash, missing bulk or
fluid-facing wall state, source revision/bytes mismatch, domain excursion,
extrapolation, unsupported geometry or phase, and case/configuration/
geometry/support mismatch.  `DEFINED_ACTIVE_FAIL_CLOSED_IMPLEMENTATION_PENDING`
is a governance contract state; it does not claim runtime enforcement exists.

## Why the other outcomes do not apply

### Not Outcome A

The condition “one reviewed turbulent correction exists” is insufficient:
the native selector also exposes C1 and C2.  R24 and R26 explicitly limit
their accepted scope to turbulent C3, and neither supplies a branch-level
laminar correction nor a reviewed omission record.

### Not Outcome C

Actual wall states, material/property instances, segment bindings and runtime
execution are case-level concerns.  R26 already records them as a separate
fail-closed gate and leaves runtime implementation disabled.  Closing the
model-level blocker cannot authorize a case.

### Why no semantic split is required

The historical wording is broad but can be made unambiguous without a silent
rename: the canonical blocker is model-level complete branch coverage, while
case-level admission is a separate gate.  The current failure is incomplete
C1/C2 disposition, not an unresolved taxonomy identity.

## Effective ledger and governance

```ini
TUBE_WALL_CORRECTION_STATUS=REVIEWED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false

SOURCE_STATUS=VERIFIED_SOURCE
SOURCE_AUTHOR_LAST=J.E. Hansel
TRANSFER_RE_DOMAIN=3000<Re<5000000
PROPERTY_RATIO_DOMAIN=0.05<=Pr_liq/Pr_w<=20
PROPERTY_RATIO_EXPONENT=0.11
COMBINATION_MODE=MULTIPLICATIVE_CORRECTION

HISTORICAL_RECORDS_REWRITTEN=false
TASK026_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

The deterministic next gate is:

```ini
NEXT_GATE=AUTHORIZE_TASK172_TUBE_LAMINAR_WALL_CORRECTION_OR_OMISSION_AUTHORITY_ADJUDICATION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```

That gate must establish reviewed branch-specific coverage for both laminar
paths or document an evidence-backed reason that those paths are outside the
admitted TASK172 correction model.  It must not remove this blocker merely
because C3 was accepted.
