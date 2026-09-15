# TASK172 — native TASK026 base-selector parity adjudication R1

This receipt records a scoped semantic adjudication for the native
TASK026/R8 tube-side base selector.  It does not acquire or approve a
wall-property correction.  It resolves the previously recorded ambiguity by
separating the TASK026 production selector from the adjacent generic
correlation-service policy.

## 1. Gate and decision boundary

```ini
TASK_ID=TASK172_V0_7_TUBE_NATIVE_BASE_SELECTOR_PARITY_ADJUDICATION_R1
PR_NUMBER=277
PREVIOUS_HEAD_SHA=366fd35facb486dea081974b4d2332ee49c5cfad
MODE=NATIVE_BASE_AUTHORITY_SEMANTIC_ADJUDICATION_ONLY
SUBJECT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
TARGET_BASE_AUTHORITY_ID=SRC-T172-REPO-TUBE
TARGET_SELECTOR_VERSION=R8
```

The question at this gate is authority ownership, not which threshold is more
convenient.  The audit asks whether the R8 TASK026 selector is the reviewed
base for the TASK026 production path, while the 2300/10000 policy remains the
policy of the separate generic correlation-service path.

The adjudication is:

```ini
ADJUDICATION_OUTCOME=SCOPED_AUTHORITY_PRECEDENCE_VALID
NATIVE_SELECTOR_DOCUMENT_PARITY=RESOLVED_BY_SCOPE
NATIVE_BASE_BINDING_STATUS=BOUND
NATIVE_BASE_BINDING_BOUND=true
SEMANTIC_CORRECTION_REQUIRED=false
SEMANTIC_CONTRACT_CLARIFICATION_REQUIRED=false
TASK026_NATIVE_BASE_AUTHORITY=R8_TASK026_SELECTOR
GENERIC_SERVICE_POLICY_APPLIES_TO_TASK026=false
```

`RESOLVED_BY_SCOPE` does not claim that every repository document contains
the same numerical threshold.  It means that the two threshold sets belong to
different, explicitly identified consumers and that the TASK026 call graph
has an unambiguous owner.

## 2. Authority ownership map

| Concern | Authoritative owner | Evidence and scope |
| --- | --- | --- |
| TASK026 selector dispatch | `src/hexagent/exchangers/shell_tube/tube_side_thermal/nusselt_selector.py::select_regime` | R8 selector; called by the TASK026 single-phase path. It returns TASK026's local `FlowRegime` and selected base correlation identity. |
| TASK026 production orchestration | `src/hexagent/exchangers/shell_tube/tube_side_thermal/stage_pipeline.py::compute_tube_side_heat_transfer_coefficient` | S02–S15 TASK026 pipeline. It calls `compute_single_phase`, handles the local transition sentinel, and emits `BL_REGIME_NO_CORRELATION_APPLICABLE` for the R8 gap. |
| TASK026 single-phase computation | `src/hexagent/exchangers/shell_tube/tube_side_thermal/single_phase.py::compute_single_phase` | Directly imports and calls the TASK026 package's `select_regime`; it does not import the generic classifier. |
| C1/C2/C3 correlation metadata and evaluation | `src/hexagent/correlations/tube.py` | Existing correlation identities, source metadata, C3 declared `[3000, 5e6]` evaluator domain, and unchanged formula implementation. This is correlation validity metadata, not the TASK026 dispatch owner. |
| Generic regime classification | `src/hexagent/correlations/flow.py::classify_regime` | Generic `FlowRegime` (`laminar`, `transitional`, `turbulent`, `invalid`) with `2300 <= Re <= 10000` transitional and `Re > 10000` turbulent. Its module contract is the generic correlation subsystem. |
| Generic service admission and selection | `src/hexagent/correlations/service.py::compute_correlation` plus `selection.py` | TASK-007/generic service route. It classifies with `classify_regime`, blocks the generic transition interval, and then uses the generic registry/applicability machinery. It is not imported by the TASK026 stage path. |
| Historical generic documentation | `docs/tasks/TASK-007-tube-annulus-correlations.md` and `docs/CORRELATIONS.md` | Records the generic service transition policy and the C3 source/metadata ranges. These documents do not override the later, separately reviewed TASK026 R8 production selector. |

The similarly named `FlowRegime` types are not the same runtime type: the
TASK026 package defines an uppercase local enum, while the generic module
defines a separate lowercase enum.  This is additional evidence that the
concepts are scoped to different service boundaries; it is not by itself a
source-of-physics decision.

## 3. Audited call paths

The actual TASK026 production path is:

```text
TASK026 stage_pipeline.compute_tube_side_heat_transfer_coefficient
  -> TASK026 single_phase.compute_single_phase
    -> TASK026 nusselt_selector.select_regime
      -> local TASK026 FlowRegime and C1/C2/C3 identity
```

The adjacent generic path is:

```text
generic correlations.service.compute_correlation
  -> generic correlations.flow.classify_regime
    -> generic correlations.selection / registry applicability
```

There is no import or call edge from the first path to
`correlations.flow.classify_regime` or `correlations.service.compute_correlation`.
Conversely, this receipt does not change the generic path or declare that its
10000 threshold is wrong for its own consumers.

The TASK026 stage's transition handling is also distinct: the R8 selector
returns no correlation identity for `2300 <= Re < 3000`, and the stage emits
the TASK026 `BL_REGIME_NO_CORRELATION_APPLICABLE` blocker.  This is not the
generic service's `CORRELATION_FLOW_REGIME_INCOMPATIBLE` branch.

## 4. Exact regime semantics

The audit records three different dimensions rather than one overloaded
`regime` field.

```ini
C3_SOURCE_VALIDITY_RE_DOMAIN=Gnielinski source is documented as 3000 < Re < 5000000; repository C3 metadata/evaluator declares and checks 3000 <= Re <= 5000000
TASK026_SELECTOR_DISPATCH_RE_DOMAIN=R8: Re < 2300 -> LAMINAR; 2300 <= Re < 3000 -> TRANSITION/BLOCKED; Re >= 3000 -> TASK026 C3 dispatch; select_regime itself has no upper-Re comparison, while the C3 identity/evaluator declares [3000, 5000000]
GENERIC_SERVICE_TURBULENT_RE_DOMAIN=Re > 10000
```

The native selector's lower dispatch boundary and the C3 correlation's
declared lower validity boundary are aligned for the TASK026 base identity.
The generic service's `Re > 10000` rule is a conservative service admission
boundary for that separate route.  A future wall-correction acquisition must
still bind the exact C3 upper bound and all other correlation applicability
fields; this adjudication does not widen or silently repair that domain.

The distinction is therefore:

1. **Correlation mathematical/source validity** — what the C3 source and
   registered evaluator declare for `tube_turbulent_gnielinski`.
2. **TASK026 dispatch** — the R8 selector's explicit choice of C1/C2 or C3,
   including its fail-closed transition gap.
3. **Generic service classification/admission** — the generic classifier's
   broader blocked transition interval before generic registry selection.

No conclusion is drawn that the generic service should admit `3000–10000`,
and no conclusion is drawn that TASK026 must be rewritten to use `10000`.

## 5. R8 selector provenance and review evidence

The R8 selector is not being accepted merely because the current code happens
to produce that result.  Its production status is supported by the following
governance chain:

```ini
R8_SELECTOR_AUTHORITY_SOURCE=TASK-026 source-definition Issue #163 + separately authorized TASK-026 design/implementation round; R8 commit 37f39d902143e4938f83cd7edb48231d5fabf937; R9 remediation 3b8f4143d8c1c3d88503868505f94c94eeb17631; merged PR #164
R8_SELECTOR_REVIEW_EVIDENCE=Issue #163 freeze decision and governance closeout; PR #164 final review; CI 30631066197; post-merge main CI 30638479580; authority checker 9/9 EXACT_EQUAL and cross-version canonical SHA fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5
R8_SELECTOR_ACCEPTANCE_SCOPE=TASK-026 TUBE_SIDE_HEAT_TRANSFER_COEFFICIENT_FOUNDATION_ONLY, including the reviewed R8 selector and C1/C2/C3 base identities; shell-side, pressure-drop, overall-U/UA, outlet-temperature, property-database and wall-correction capabilities remain out of scope
R8_SELECTOR_PRODUCTION_STATUS=REVIEWED_PRODUCTION_AUTHORITY_ON_PINNED_MAIN
```

The relevant immutable governance identifiers are:

| Artifact | Identity |
| --- | --- |
| TASK026 source-definition Issue body | SHA-256 `11a542048d666cd2022ca7f965462d558e128fd73f7b94d867ee087718cd9102` |
| TASK026 source-review package | SHA-256 `384f1b829cc834dc0d1119d0451b9028bd988224b2c031786d281bca7220bf06` |
| TASK026 design contract | SHA-256 `238786b68250832ba083a56f0d6ba35dffa627a237b5fead80a6ee322de69f58` |
| R8 implementation | Commit `37f39d902143e4938f83cd7edb48231d5fabf937` |
| R9 CI remediation | Commit `3b8f4143d8c1c3d88503868505f94c94eeb17631` |
| Final merged PR | #164, merge commit `b11a7d46ac6a726c2bbdff85166c78e6753289a0` |
| Accepted pre-merge CI | Run `30631066197`, success |
| Accepted post-merge main CI | Run `30638479580`, success |

The historical design contract is referenced by the TASK026 governance
records but is not a source file in the current repository tree.  It is not
silently recreated or promoted by this receipt.  The current pinned source
files and their hashes are recorded in the R21 evidence and are re-bound by
the R22 machine evidence.

## 6. Adjudication conditions and limits

Outcome A is valid because all of the following are true:

* R8 is a separately named TASK026 selector authority, not an incidental
  branch inside the generic service.
* TASK026's actual production call graph reaches that selector directly.
* TASK026's scope and final review evidence identify the tube-side foundation
  as the admitted implementation boundary.
* The generic classifier and generic service own a separate call path and
  retain their own conservative transition policy.
* No formula, coefficient, correlation identity, legacy result, or generic
  threshold is changed here.

This is a scoped precedence statement, not a new empirical authority.  It
does not authorize any of the following:

```ini
NATIVE_TUBE_CORRELATION_CHANGED=false
LEGACY_TUBE_RESULT_SEMANTICS_CHANGED=false
CORRECTION_EQUATION_BOUND=false
PRIMARY_SOURCE_BOUND=false
TRANSFERABILITY_ESTABLISHED=false
```

The TASK026 C3 upper validity bound and its enforcement are still required
inputs to any future correction transfer package.  The R8 selector's
dispatch function does not itself compare the upper bound; the C3 evaluator
and correlation metadata declare that bound.  This receipt does not decide
whether an additional TASK026 upper-bound admission check is required, and
does not widen the declared domain.  A future implementation must fail
closed if a wall-correction source, C3 applicability field, or
source-defined combination rule is missing.  This receipt only removes the
semantic ambiguity that previously prevented binding the native base owner.

## 7. Effective TASK172 state after this adjudication

The wall-correction authority is still blocked.  No primary correction source
is selected and the existing Sandia, Sieder–Tate, Goncalves, Martin and
native-base dispositions remain unchanged.

```ini
SELECTED_PRIMARY_SOURCE_ID=NONE
PRIMARY_SOURCE_BOUND=false
CORRECTION_EQUATION_BOUND=false
TRANSFERABILITY_ESTABLISHED=false
TUBE_WALL_CORRECTION_STATUS=BLOCKED
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
TUBE_WALL_CORRECTION_INDEPENDENT_REVIEW=PENDING

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The prior material model-level closure and the separate case-level
fail-closed material admission state are inherited without change.

## 8. Governance and next gate

```ini
NATIVE_BASE_CORRECTION_PERFORMED=false
TASK026_FILES_CHANGED=false
TASK007_FILES_CHANGED=false
GENERIC_SERVICE_POLICY_CHANGED=false
ENGINEERING_RULES_CHANGED=false
PRODUCTION_CODE_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
SHELL_WALL_CORRECTION_STARTED=false
NUMERICAL_WORK_STARTED=false
GOLDEN_APPROVED=false
NEW_AUTHORITY_SELF_APPROVAL=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_TUBE_WALL_CORRECTION_PRIMARY_TRANSFER_AUTHORITY_ACQUISITION_R2_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```

Only documentation, machine evidence and the append-only registry overlay
are changed by this gate.  The next gate must separately acquire and review a
complete wall-correction transfer authority against the now-bound TASK026
base; it is not executed by this receipt.
