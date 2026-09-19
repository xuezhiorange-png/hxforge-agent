# TASK172 — laminar tube wall-correction or omission authority adjudication R1

## Receipt and immutable boundary

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_WALL_CORRECTION_OR_OMISSION_AUTHORITY_ADJUDICATION_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=af13e174376f47981764eb8ca4654778bab4c685
PREVIOUS_HEAD_SHA=af13e174376f47981764eb8ca4654778bab4c685
MODE=LAMINAR_BRANCH_AUTHORITY_SEMANTIC_ADJUDICATION_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
RESULT=PASS_WITH_BLOCKER_RETAINED
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

This receipt performs a bounded adjudication of the two laminar branches that
the reviewed TASK026 selector can admit.  It does not acquire a new source,
select a correction, create an omission authority, change TASK026, promote an
authority, or remove the parent canonical blocker.  The preceding C3 review
and its lifecycle state remain immutable.

The source audit is limited to the reviewed repository evidence and its
recorded provenance.  It is not an assertion that a new external primary
source was acquired in this task.

## Adjudication result

```ini
ADJUDICATION_OUTCOME=LAMINAR_DISPOSITION_SOURCE_EVIDENCE_INSUFFICIENT
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
```

The native metadata says that both laminar definitions do not require a wall
viscosity input.  That fact describes the current TASK026 implementation; it
does not, by itself, answer the TASK172 authority question of whether a future
wall-temperature/property closure may omit an active wall-property correction.
No reviewed source record in the audited repository supplies the exact
branch-level omission disposition, including the source-defined property
states, boundary-condition interpretation, domain, and TASK172 combination
rule that would be required to issue such an authority.

Conversely, the audited records do not establish that an active correction is
required for either laminar branch.  It would therefore be equally
unsupported to add a remembered Sieder–Tate exponent, copy the accepted C3
extension, or introduce a neutral factor as a substitute for evidence.

The conservative and reproducible result is unresolved source evidence for
both branches.  This is not a TASK026 implementation failure; it is an
unresolved TASK172 authority disposition.

## Native branch evidence

The exact native branch identities and their current metadata were audited at
the following repository locations:

| Branch | Native identity | Repository evidence | Native facts | TASK172 disposition |
| --- | --- | --- | --- | --- |
| Laminar CWT | `tube_laminar_cwt@1.0.0` | `src/hexagent/correlations/tube.py:19-47`; `src/hexagent/exchangers/shell_tube/tube_side_thermal/nusselt_selector.py:97-108,140-149` | Circular tube; fully developed; constant wall temperature; `Re < 2300`; `Pr > 0.6`; `Nu_D=3.66`; `requires_wall_viscosity=false` | No reviewed active-correction authority and no reviewed explicit omission authority |
| Laminar CHF | `tube_laminar_chf@1.0.0` | `src/hexagent/correlations/tube.py:50-79`; `src/hexagent/exchangers/shell_tube/tube_side_thermal/nusselt_selector.py:97-108,140-149` | Circular tube; fully developed; constant heat flux; `Re < 2300`; `Pr > 0.6`; `Nu_D=4.36`; `requires_wall_viscosity=false` | No reviewed active-correction authority and no reviewed explicit omission authority |
| Turbulent C3 (inherited) | `tube_turbulent_gnielinski@1.0.0` | R26 external scoped acceptance and R27 canonical adjudication | Existing accepted model-level correction authority; not a laminar transfer authority | Unchanged; not re-adjudicated here |

The selector and correlation documentation identify the laminar constants and
their boundary conditions.  `docs/CORRELATIONS.md` and
`docs/tasks/TASK-007-tube-annulus-correlations.md` also describe the current
native no-wall-property boundary.  Those records are useful native-base
evidence, but they do not contain a reviewed TASK172 statement that a future
wall-state closure is authorized to omit wall-property correction for CWT or
CHF.  In particular, `requires_wall_viscosity=false` is not treated as a
source-qualified `NO_ACTIVE_WALL_CORRECTION_REQUIRED` record.

## Branch-by-branch decision

### CWT

```ini
LAMINAR_CWT_CORRELATION_ID=tube_laminar_cwt@1.0.0
LAMINAR_CWT_NATIVE_REQUIRES_WALL_VISCOSITY=false
LAMINAR_CWT_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CWT_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CWT_OMISSION_AUTHORITY_BASIS=NO_REVIEWED_SOURCE_AUTHORITY_IDENTIFIED;NATIVE_REQUIRES_WALL_VISCOSITY_FALSE_IS_INSUFFICIENT
LAMINAR_CWT_BOUNDARY_CONDITION_COMPLETE=PARTIAL_NATIVE_DEFINITION_ONLY
LAMINAR_CWT_DISPOSITION=UNRESOLVED_SOURCE_EVIDENCE_INSUFFICIENT
LAMINAR_CWT_OMISSION_AUTHORITY_CANDIDATE_COMPLETE=false
```

The CWT native definition records a fully developed circular-tube relation
under constant wall temperature.  It does not provide a TASK172-reviewed
rule for mapping a future wall surface/property state to an allowed omission
of active correction.  The existing constant value is not reinterpreted as a
wall-temperature authority.

### CHF

```ini
LAMINAR_CHF_CORRELATION_ID=tube_laminar_chf@1.0.0
LAMINAR_CHF_NATIVE_REQUIRES_WALL_VISCOSITY=false
LAMINAR_CHF_ACTIVE_CORRECTION_REQUIRED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CHF_OMISSION_ALLOWED=UNRESOLVED_BY_REVIEWED_AUTHORITY
LAMINAR_CHF_OMISSION_AUTHORITY_BASIS=NO_REVIEWED_SOURCE_AUTHORITY_IDENTIFIED;NATIVE_REQUIRES_WALL_VISCOSITY_FALSE_IS_INSUFFICIENT
LAMINAR_CHF_BOUNDARY_CONDITION_COMPLETE=PARTIAL_NATIVE_DEFINITION_ONLY
LAMINAR_CHF_DISPOSITION=UNRESOLVED_SOURCE_EVIDENCE_INSUFFICIENT
LAMINAR_CHF_OMISSION_AUTHORITY_CANDIDATE_COMPLETE=false
```

The CHF native definition records a fully developed circular-tube relation
under constant heat flux.  It likewise does not provide a TASK172-reviewed
branch-level omission rule.  CWT and CHF are kept distinct; neither boundary
condition is silently substituted for the other.

## Historical authority and taxonomy audit

The parent blocker was not reinterpreted from the native boolean alone.  The
following immutable records were audited:

| Record | SHA-256 | Relevant conclusion |
| --- | --- | --- |
| `TASK-172-v0.7-tube-wall-correction-authority-resolution-r1.md` | `6480959ac6c8d48bf342ec208be7e4a8bf2398db5c720bb92b8264cdb165fcb1` | Native C1/C2/C3 branches are identified; exact correction, state, domain and combination authority is missing. |
| `TASK-172-v0.7-material-active-wall-review-r4.md` | `730bebfb09a2fdf6939152f3b8aab70f196eb4a8afa21d6f49667d6ced9d52c8` | Laminar and turbulent paths remain separate; neutral factors and unqualified omission are not allowed. |
| `TASK-172-v0.7-physical-authority-semantic-source-r5.md` | `9d01a10b043a9b585405dc6611bbe9109efeb0b1a2afa627568f0e7d934b3683` | Exact branch/version binding is required; branch-specific coverage is incomplete. |
| `TASK-172-v0.7-tube-wall-correction-primary-transfer-acquisition-r2.md` | `f2051a46b4fc6b6099ef2718e1f83c73d54318d13658052059e60f2c469de083` | The acquired transfer package is exact C3 scope, not a laminar package. |
| `TASK-172-v0.7-tube-wall-correction-authority-independent-review-r1.md` | `eef5302d59439c32bd3aa3b669c196a253bf043adc8be2b78edee270f6dc7eb2` | Independent acceptance is turbulent-only; laminar transfer is false. |
| `TASK-172-v0.7-tube-wall-correction-external-scoped-approval-record-r1.md` | `41dcc7abe70ad3171cad8f9f873d57a45ab4f4885543d1049e89f98157b70bd2` | External acceptance promotes only the scoped turbulent authority. |
| `TASK-172-v0.7-tube-wall-correction-canonical-blocker-closure-adjudication-r1.md` | `2845f8a15578e8ac41e597b40a3f313eb543d291302c9deb81b8b70979ac66e3` | Whole model coverage requires every admitted branch to have correction or reviewed omission disposition. |

The historical taxonomy is therefore interpreted as
`MODEL_LEVEL_COMPLETE_TUBE_BRANCH_COVERAGE_WITH_SEPARATE_CASE_LEVEL_ADMISSION`.
The parent blocker can close only after the C1/C2 branch dispositions are
reviewed, not merely because C3 is reviewed.  This task does not rename or
rewrite that taxonomy.

## Why no disposition is promoted

The two native boundary conditions are not enough to select one of the
following without additional source evidence:

* an active correction equation compatible with the exact CWT or CHF base;
* an explicit source-qualified `NO_ACTIVE_WALL_CORRECTION_REQUIRED`
  disposition for the exact branch;
* a branch-specific exclusion from the admitted TASK172 wall-correction
  model.

The following are expressly not authority:

* `requires_wall_viscosity=false` in the native dataclass;
* a documentation statement that the current implementation has no wall
  property input;
* the C3 turbulent correction package;
* a remembered Sieder–Tate exponent or generic viscosity ratio;
* `factor=1` or omission justified only by the narrow water profile;
* a library or backend result.

Because the current selector admits both laminar branches, Outcome D
(`BRANCH_OUTSIDE_ADMITTED_SCOPE`) is not applicable.  Because no source proves
that active correction is required, Outcome B is not established.  Because no
source proves that omission is allowed, Outcome A is not established.  The
only supported result is the source-evidence-insufficient disposition recorded
above.

## Separate case-level fail-closed state

The model-level branch coverage result remains distinct from case execution
readiness.  The existing case-level gate remains active and unimplemented:

```ini
CASE_LEVEL_TUBE_CORRECTION_AUTHORITY_REQUIRED=true
CASE_LEVEL_TUBE_CORRECTION_AUTHORITY_PRESENT=false
CASE_LEVEL_TUBE_CORRECTION_FAIL_CLOSED_GATE_ID=TASK172-CASE-LEVEL-TUBE-WALL-CORRECTION-ADMISSION
CASE_LEVEL_TUBE_CORRECTION_GATE_STATUS=DEFINED_ACTIVE_FAIL_CLOSED_IMPLEMENTATION_PENDING
CASE_LEVEL_TUBE_CORRECTION_GATE_RUNTIME_IMPLEMENTED=false
PRODUCTION_WITHOUT_REQUIRED_CASE_LEVEL_TUBE_CORRECTION_AUTHORITY=BLOCKED
```

This gate still requires the reviewed branch correction or omission authority,
the exact native-base identity, located bulk and fluid-facing wall states,
source and domain bindings, case/geometry/support binding, and all required
material/property authority.  Its governance state does not claim runtime
enforcement.

## Effective state and governance

```ini
TUBE_WALL_CORRECTION_STATUS=REVIEWED_AUTHORITY
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false

HISTORICAL_RECORDS_REWRITTEN=false
TUBE_WALL_CORRECTION_C3_UNCHANGED=true
SOURCE_SEARCH_SCOPE=REPOSITORY_REVIEWED_EVIDENCE_ONLY
ENGINEERING_RULES_CHANGED=false
TASK026_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
```

The next and only authorized gate is:

```ini
NEXT_GATE=AUTHORIZE_TASK172_TUBE_LAMINAR_PRIMARY_SOURCE_ACQUISITION_R1_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```

That gate may acquire and review branch-specific primary evidence.  It must
not infer omission from the native flag, transfer C3 into C1/C2, or remove the
parent blocker without complete reviewed coverage.
