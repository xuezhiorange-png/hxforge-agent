# TASK172 — laminar constant-property branch-scope external acceptance R1

## 1. Receipt and authority boundary

This receipt records the authorized external scoped-acceptance decision for
the two exact native TASK026 laminar constant-property branch-scope
authorities.  The acceptance is limited to model-level branch scope and
snapshot semantics.  It does not approve an active wall correction, a
variable-property extension, a case-level property snapshot, or production
implementation.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_CONSTANT_PROPERTY_SCOPE_AUTHORITIES_EXTERNAL_SCOPED_APPROVAL_RECORD_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=e4d3d189241489f26625909d6eac0e25ada3d2eb
PREVIOUS_HEAD_SHA=e4d3d189241489f26625909d6eac0e25ada3d2eb
MODE=EXTERNAL_REVIEW_DECISION_RECORDING_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
CWT_AUTHORITY_ID=V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1
CHF_AUTHORITY_ID=V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1
EXTERNAL_REVIEW_DECISION=ACCEPT_SCOPED_LAMINAR_CONSTANT_PROPERTY_BRANCH_AUTHORITIES
EXTERNAL_REVIEW_SCOPE=MODEL_LEVEL_EXACT_NATIVE_LAMINAR_CONSTANT_PROPERTY_BRANCH_SCOPE_ONLY
EXTERNAL_REVIEW_EVIDENCE_BOUND=true
CWT_EXTERNAL_SCOPED_ACCEPTANCE=true
CHF_EXTERNAL_SCOPED_ACCEPTANCE=true
LIFECYCLE_PROMOTION_PERFORMED=true
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

The external review source is recorded truthfully as the authorized ChatGPT
external-review decision supplied for this gate.  This receipt does not
invent a GitHub reviewer, human expert, organization, professional signature,
or credential, and does not use PR review API state as approval evidence.

## 2. Lifecycle promotion scope

Only the lifecycle state of the two already proposed branch-scope candidates
is promoted.  The accepted scope is:

```text
fully developed circular tube
constant nominal thermophysical-property snapshot
exact native TASK026 CWT or CHF branch
native branch domain and boundary condition
explicit case/segment snapshot binding
no temperature-driven property refresh
```

The promotion does not merge the candidates, enable a runtime path, select an
actual material or property value, or close the parent blocker.

```ini
CWT_STATUS=REVIEWED_AUTHORITY
CWT_INDEPENDENT_REVIEW=ACCEPTED
CHF_STATUS=REVIEWED_AUTHORITY
CHF_INDEPENDENT_REVIEW=ACCEPTED
```

The CWT and CHF identities remain separate:

| Authority | Component scope | Native correlation | Boundary condition |
| --- | --- | --- | --- |
| `V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1` | `TUBE_LAMINAR_CWT` | `tube_laminar_cwt@1.0.0` | `CONSTANT_WALL_TEMPERATURE` |
| `V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1` | `TUBE_LAMINAR_CHF` | `tube_laminar_chf@1.0.0` | `CONSTANT_HEAT_FLUX` |

## 3. Accepted CWT scope

```ini
CWT_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CWT_COMPONENT_SCOPE=TUBE_LAMINAR_CWT
CWT_NATIVE_CORRELATION_ID=tube_laminar_cwt@1.0.0
CWT_THERMAL_BOUNDARY=CONSTANT_WALL_TEMPERATURE
CWT_CONSTANT_PROPERTY_USE=AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE
CWT_VARIABLE_PROPERTY_USE=BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY
CWT_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CWT_ACTIVE_CORRECTION_AUTHORITY=NONE
```

The accepted source is `NASA-CR-189922`, source body SHA-256
`46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e`,
Chapter 3 §3.3.3 and the cited report/PDF pages and equations recorded in
the prior source package.  Its constant-property CWT solution is the scope
authority; it is not an authority for a variable-property extension or an
omission claim.

## 4. Accepted CHF scope

```ini
CHF_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CHF_COMPONENT_SCOPE=TUBE_LAMINAR_CHF
CHF_NATIVE_CORRELATION_ID=tube_laminar_chf@1.0.0
CHF_THERMAL_BOUNDARY=CONSTANT_HEAT_FLUX
CHF_CONSTANT_PROPERTY_USE=AUTHORIZED_WITHIN_NATIVE_SOURCE_SCOPE
CHF_VARIABLE_PROPERTY_USE=BLOCKED_WITHOUT_SEPARATE_EXTENSION_AUTHORITY
CHF_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CHF_ACTIVE_CORRECTION_AUTHORITY=NONE
```

The accepted source is the same acquired report body, but the CHF identity is
bound independently to Chapter 3 §3.3.2 and its exact cited derivation.  The
CHF source is not transferred to CWT, and CWT is not transferred to CHF.

## 5. Frozen property-snapshot contract

The external acceptance includes the property snapshot semantics reviewed in
the preceding independent-scope audit.  A native branch does not become
constant-property merely because one function call receives one set of
values.  The snapshot is an immutable authority input over the complete
bound authority instance.

```ini
PROPERTY_SNAPSHOT_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_COMPONENTS=DENSITY;DYNAMIC_VISCOSITY;THERMAL_CONDUCTIVITY;SPECIFIC_HEAT_CAPACITY;UNITS;PROPERTY_AUTHORITY_ID_AND_HASH;REFERENCE_STATE_IDENTITY
PROPERTY_SNAPSHOT_BINDING_GRANULARITY=EXPLICIT_CASE_SCOPE_OR_EXPLICIT_PHYSICAL_SEGMENT_SCOPE;NO_UNSCOPED_CALCULATION_SCOPE
PROPERTY_SNAPSHOT_CASE_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_SEGMENT_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_IMMUTABILITY_REQUIRED=true
PROPERTY_SNAPSHOT_LIFETIME=ALL_EVALUATIONS_AND_ALL_NONLINEAR_ITERATIONS_OF_THE_BOUND_AUTHORITY_INSTANCE
PROPERTY_SNAPSHOT_ITERATION_REFRESH_ALLOWED=false
PER_SEGMENT_DISTINCT_FROZEN_SNAPSHOT_POLICY=FORBIDDEN_WITHOUT_VARIABLE_PROPERTY_EXTENSION
```

The native TASK026 path consumes `rho`, `mu`, `k`, and `cp`; it derives
velocity, Reynolds number, and Prandtl number and computes
`h_i = Nu * k / D_h`.  Consequently, a temperature-driven change in any
consumed property is variable-property use even when the laminar `Nu` value
remains `3.66` or `4.36`.

```ini
UPSTREAM_TEMPERATURE_DRIVEN_PROPERTY_REFRESH_COUNTS_AS_VARIABLE_PROPERTY=true
THERMAL_CONDUCTIVITY_REFRESH_IS_VARIABLE_PROPERTY_USE=true
```

The following remain outside this accepted scope and must fail closed:

* wall-, bulk-, film-, local-, or iteration-temperature property refresh;
* per-iteration replacement of a frozen snapshot;
* unauthorized distinct per-segment snapshots;
* bulk/wall property-ratio evaluation;
* hidden backend defaults or unbound database lookup;
* missing snapshot identity, source binding, body, or hash;
* silent fallback to the native constant after variable-property use is
  requested.

## 6. Reference-state separation

The branch-scope authorities do not choose the case-level reference state.
No inlet, bulk, wall, film, mean, or backend-default temperature is implied
by this acceptance.

```ini
REFERENCE_STATE_SELECTION_AUTHORITY_BOUND_BY_THIS_SCOPE=false
CASE_LEVEL_REFERENCE_STATE_AUTHORITY_REQUIRED=true
```

The case-level reference-state authority and any future property snapshot
must be separately source-bound, case-bound, and reviewed.  This acceptance
does not approve a material, a conductivity value, a `k(T)` table, or a
production property instance.

## 7. Wall-temperature semantics and non-transfer

```ini
WALL_TEMPERATURE_DIFFERENCE_ALONE_IMPLIES_VARIABLE_PROPERTY=false
WALL_STATE_PROPERTY_REEVALUATION_IMPLIES_VARIABLE_PROPERTY=true
VARIABLE_PROPERTY_OUTCOME=BLOCKED_MISSING_LAMINAR_VARIABLE_PROPERTY_EXTENSION_AUTHORITY
```

`T_wall != T_bulk` may coexist with a non-isothermal wall field while the
laminar branch consumes the same frozen snapshot.  Reevaluating `rho`, `mu`,
`k`, or `cp` from any wall/bulk/film/local/iteration temperature is instead a
variable-property extension and is not covered by either accepted authority.

This record does not create either an omission authority or an active
correction:

```ini
CWT_OMISSION_AUTHORITY_CREATED=false
CHF_OMISSION_AUTHORITY_CREATED=false
CWT_ACTIVE_CORRECTION_CREATED=false
CHF_ACTIVE_CORRECTION_CREATED=false
CWT_ACTIVE_CORRECTION_AUTHORITY=NONE
CHF_ACTIVE_CORRECTION_AUTHORITY=NONE
```

The separately accepted turbulent C3 correction remains unchanged and is not
transferred to the laminar branches:

```ini
TURBULENT_C3_AUTHORITY_ID=V07-T172-TUBE-WALL-CORRECTION-R1
TURBULENT_C3_CORRECTION_STATUS=REVIEWED_AUTHORITY
TURBULENT_C3_CORRECTION_INDEPENDENT_REVIEW=ACCEPTED
TURBULENT_C3_SCOPE_NOT_TRANSFERRED_TO_LAMINAR=true
```

## 8. Parent blocker and effective state

The external acceptance does not answer whole-branch coverage.  The parent
`TUBE-WALL-CORRECTION-AUTHORITY` blocker remains because variable-property
extension authority is still absent and the next whole-branch coverage
adjudication has not occurred.

```ini
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false
REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The lifecycle promotion must not be read as production admission.  No case
has an approved material/property instance merely because both branch-scope
identities are now `REVIEWED_AUTHORITY`.

## 9. Governance and next gate

```ini
HISTORICAL_RECORDS_REWRITTEN=false
NATIVE_CWT_IDENTITY_CHANGED=false
NATIVE_CHF_IDENTITY_CHANGED=false
NATIVE_CWT_CONSTANT_CHANGED=false
NATIVE_CHF_CONSTANT_CHANGED=false
TASK026_FILES_CHANGED=false
TASK026_EQUATIONS_CHANGED=false
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
LIFECYCLE_PROMOTION_PERFORMED=true
```

The next gate is deliberately separate and limited to whole-branch coverage
closure adjudication:

```ini
NEXT_GATE=AUTHORIZE_TASK172_TUBE_WALL_CORRECTION_COMPLETE_BRANCH_COVERAGE_CLOSURE_ADJUDICATION_R2_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
```

The machine-readable evidence for this receipt is recorded in
[the external scoped-approval evidence](evidence/TASK-172-tube-laminar-constant-property-scope-authorities-external-scoped-approval-record-r1.json).
