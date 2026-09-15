# TASK172 — complete tube-branch coverage closure adjudication R2

## 1. Receipt and boundary

This receipt records the authorized whole-branch semantic adjudication for
TUBE-WALL-CORRECTION-AUTHORITY. It decides whether the model-level coverage
condition is complete; it does not remove the canonical blocker, promote a
new authority, change TASK026, or authorize production execution.

TASK_ID=TASK172_V0_7_TUBE_WALL_CORRECTION_COMPLETE_BRANCH_COVERAGE_CLOSURE_ADJUDICATION_R2
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=22dc2ac2d380aad76a17e82399ced0df71eb6045
PREVIOUS_HEAD_SHA=22dc2ac2d380aad76a17e82399ced0df71eb6045
MODE=COMPLETE_TUBE_BRANCH_COVERAGE_CLOSURE_ADJUDICATION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
CANONICAL_BLOCKER_SEMANTICS=MODEL_LEVEL_COMPLETE_TUBE_BRANCH_COVERAGE_AUTHORITY

The adjudication question is:

> Does every TASK026-admitted tube correlation path now have an explicit,
> reviewed model-level disposition for wall/property treatment, including
> explicit fail-closed treatment outside its reviewed scope?

This is a model-level coverage question. It is not a claim that every
possible runtime case has the required case-level states, snapshots,
reference-state authority, material authority, or executable admission gate.

## 2. Inherited reviewed authorities

The following dispositions are inherited without changing their payloads,
equations, constants, domains, or lifecycle records:

| TASK026 path | Authority | Effective disposition | Lifecycle |
| --- | --- | --- | --- |
| Laminar CWT | V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1 | Constant-property branch admitted within native source scope; variable-property extension explicitly blocked | REVIEWED_AUTHORITY / ACCEPTED |
| Laminar CHF | V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1 | Constant-property branch admitted within native source scope; variable-property extension explicitly blocked | REVIEWED_AUTHORITY / ACCEPTED |
| Turbulent C3 | V07-T172-TUBE-WALL-CORRECTION-R1 | Source-qualified active wall-property correction within strict reviewed domain; out-of-domain use blocked | REVIEWED_AUTHORITY / ACCEPTED |

The CWT and CHF acceptance does not say that no active correction is ever
needed. It defines their admitted constant-property scope and explicitly
blocks variable-property use without a separate extension authority:

CWT_BRANCH_MODEL_LEVEL_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
CWT_CONSTANT_PROPERTY_USE=AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE
CWT_VARIABLE_PROPERTY_USE=BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY
CWT_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CWT_ACTIVE_CORRECTION_AUTHORITY=NONE
CWT_BRANCH_EXPLICIT_REVIEWED_DISPOSITION_COMPLETE=true

CHF_BRANCH_MODEL_LEVEL_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
CHF_CONSTANT_PROPERTY_USE=AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE
CHF_VARIABLE_PROPERTY_USE=BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY
CHF_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CHF_ACTIVE_CORRECTION_AUTHORITY=NONE
CHF_BRANCH_EXPLICIT_REVIEWED_DISPOSITION_COMPLETE=true

The turbulent C3 disposition remains separate and is not transferred to
either laminar branch:

TURBULENT_BRANCH_MODEL_LEVEL_DISPOSITION=ACTIVE_WALL_PROPERTY_CORRECTION_WITH_STRICT_FAIL_CLOSED_DOMAIN
TURBULENT_C3_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
TURBULENT_STATUS=REVIEWED_AUTHORITY
TURBULENT_INDEPENDENT_REVIEW=ACCEPTED
TURBULENT_NATIVE_CORRELATION_ID=tube_turbulent_gnielinski@1.0.0
TURBULENT_C3_BRANCH_EXPLICIT_REVIEWED_DISPOSITION_COMPLETE=true
TRANSFER_RE_DOMAIN=3000<Re<5000000
PROPERTY_RATIO_DOMAIN=0.05<=Pr_liq/Pr_w<=20
PROPERTY_RATIO_EXPONENT=0.11
TARGET_PR_DOMAIN=0.5<=Pr<=2000

## 3. Exact selector-path coverage

The TASK026 production path is the reviewed R8 selector and its stage
pipeline. The separate generic correlation service has its own classifier
and is not a TASK026 selector path; it is not silently merged into this
coverage result.

| Selector condition | Native behavior | Model-level disposition | Coverage result |
| --- | --- | --- | --- |
| Re < 2300, CWT | Selects laminar CWT; native Nu_D=3.66, Pr>0.6 | CWT constant-property scope admitted; variable-property and wall-state re-evaluation blocked | Explicitly disposed |
| Re < 2300, CHF | Selects laminar CHF; native Nu_D=4.36, Pr>0.6 | CHF constant-property scope admitted; variable-property and wall-state re-evaluation blocked | Explicitly disposed |
| 2300 <= Re < 3000 | Returns transition with no correlation identity; TASK026 emits BL_REGIME_NO_CORRELATION_APPLICABLE | Selector-level no-correlation outcome is explicitly blocked | Explicitly disposed |
| Re = 3000 | Native selector dispatches C3 | The reviewed transfer domain is strict Re>3000; endpoint correction is blocked | Explicitly disposed |
| 3000 < Re < 5000000 | Native selector dispatches C3 | Reviewed C3 correction is admitted with strict property-ratio and Pr preconditions | Explicitly disposed |
| Re = 5000000 | Repository evaluator endpoint is inclusive, but transfer authority is strict | Endpoint is outside transfer authority and fail-closed | Explicitly disposed |
| Re > 5000000 | Native selector may dispatch C3 before evaluator/domain rejection | Outside reviewed transfer domain; fail-closed, with no clamp or extrapolation | Explicitly disposed |

The endpoint distinction is intentional. The repository's inclusive evaluator
metadata does not expand the source-qualified transfer authority:

RE_3000_NATIVE_DISPATCH=C3
RE_3000_CORRECTION_AUTHORIZED=false
RE_3000_MODEL_LEVEL_DISPOSITION=EXPLICIT_FAIL_CLOSED_OUTSIDE_REVIEWED_TRANSFER_DOMAIN
RE_3000_EXPLICIT_BLOCKED_DISPOSITION_COUNTS_AS_BRANCH_COVERAGE=true

RE_5000000_CORRECTION_AUTHORIZED=false
RE_ABOVE_5000000_CORRECTION_AUTHORIZED=false
UPPER_RE_OUT_OF_AUTHORITY_DISPOSITION=EXPLICIT_FAIL_CLOSED_AT_AND_ABOVE_RE_5000000
UPPER_RE_EXPLICIT_BLOCKED_DISPOSITION_COUNTS_AS_BRANCH_COVERAGE=true

The transition interval is not a missing fourth correlation. It is an
explicit selector-level blocked state:

TRANSITION_BAND_DISPOSITION=EXPLICIT_SELECTOR_LEVEL_NO_CORRELATION_BLOCKED
TRANSITION_BAND_REQUIRES_WALL_CORRECTION_AUTHORITY=false
TRANSITION_BAND_COUNTS_AS_MISSING_BRANCH_COVERAGE=false
TRANSITION_DISPOSITION_COMPLETE=true

## 4. Laminar blocked capability versus coverage

The accepted CWT and CHF records explicitly block all of the following
without a separately reviewed laminar variable-property extension:

* temperature-driven rho, mu, k, or cp refresh;
* wall, bulk, or film property re-evaluation;
* bulk/wall property-ratio correction;
* per-iteration replacement of the frozen property snapshot;
* unauthorized distinct per-segment snapshots; and
* silent fallback to Nu=3.66 or Nu=4.36 after a variable-property request.

That explicit blocked disposition is sufficient for model-level coverage
because the canonical blocker asks whether each admitted path has a reviewed
disposition, not whether every blocked capability has already been
implemented:

LAMINAR_VARIABLE_PROPERTY_EXPLICIT_BLOCK_COUNTS_AS_MODEL_LEVEL_COVERAGE=true
VARIABLE_PROPERTY_CAPABILITY_EXISTS=false
VARIABLE_PROPERTY_RUNTIME_ADMISSION=false

The distinction does not authorize variable-property calculation. The
variable-property outcome remains:

VARIABLE_PROPERTY_OUTCOME=BLOCKED_MISSING_LAMINAR_VARIABLE_PROPERTY_EXTENSION_AUTHORITY

## 5. Reference-state separation

The laminar branch-scope records do not choose a case-level reference state.
That missing case authority is intentionally a runtime prerequisite, not a
missing branch disposition:

REFERENCE_STATE_SELECTION_AUTHORITY_BOUND_BY_LAMINAR_SCOPE=false
CASE_LEVEL_REFERENCE_STATE_AUTHORITY_REQUIRED=true
MISSING_CASE_LEVEL_REFERENCE_STATE_PREVENTS_MODEL_LEVEL_BLOCKER_CLOSURE=false
CASE_EXECUTION_WITHOUT_REFERENCE_STATE_AUTHORITY=BLOCKED

No model-level closure result below may be interpreted as selecting an inlet,
bulk, wall, film, mean, or backend-default reference state.

## 6. Coverage decision

Every TASK026-admitted selector path is now disposed of by one of:

1. a reviewed exact-branch constant-property authority with explicit
   fail-closed variable-property treatment;
2. a reviewed exact-branch active correction with strict source-bound
   applicability and fail-closed endpoints; or
3. an explicit selector-level no-correlation/out-of-authority blocked
   disposition.

Accordingly:

CWT_BRANCH_COVERAGE_COMPLETE=true
CHF_BRANCH_COVERAGE_COMPLETE=true
TURBULENT_C3_BRANCH_COVERAGE_COMPLETE=true
TRANSITION_DISPOSITION_COMPLETE=true
ALL_TASK026_SELECTOR_PATHS_EXPLICITLY_DISPOSED=true
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=true
ADJUDICATION_OUTCOME=COMPLETE_MODEL_LEVEL_TUBE_BRANCH_COVERAGE_ESTABLISHED
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=true

This result does not claim that every runtime case is executable. The
following case-level requirements remain independently fail-closed:

CASE_LEVEL_TUBE_CORRECTION_GATE_RUNTIME_IMPLEMENTED=false
CASE_LEVEL_REFERENCE_STATE_AUTHORITY_PRESENT=false
CASE_LEVEL_PROPERTY_SNAPSHOT_PRESENT=false
CASE_LEVEL_MATERIAL_PROPERTY_AUTHORITY_PRESENT=false
CASE_LEVEL_EXECUTION_AUTHORIZED=false

The case gate still requires exact native-base identity, located bulk and
wall states, source/domain bindings, property and material authorities,
case/geometry/support binding, and matching hashes. Missing or mismatched
inputs remain blocked.

## 7. Blocker lifecycle and governance

This adjudication makes the parent blocker eligible for a separate recording
action only. It does not perform that action:

TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
LIFECYCLE_PROMOTION_PERFORMED=false

No TASK026 payload or source record is rewritten. In particular, this
adjudication does not change the native CWT/CHF constants, the R8 transition
interval, the C3 correction exponent, endpoint rules, property-ratio bounds,
or the generic correlation-service policy.

HISTORICAL_RECORDS_REWRITTEN=false
TASK026_CHANGED=false
TASK026_EQUATIONS_CHANGED=false
TASK026_CONSTANTS_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false

The next and only authorized action is:

NEXT_GATE=AUTHORIZE_TASK172_TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_RECORDING_R2_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
