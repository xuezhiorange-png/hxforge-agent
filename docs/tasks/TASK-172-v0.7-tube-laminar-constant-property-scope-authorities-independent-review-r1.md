# TASK172 — laminar constant-property branch-scope authority independent review R1

## 1. Gate and review boundary

This receipt records the authorized independent-scope audit for the two
proposed TASK026 laminar branch-scope authorities.  It does not perform a
lifecycle promotion, approve an active wall correction, select a material or
property instance, or close the parent `TUBE-WALL-CORRECTION-AUTHORITY`
blocker.

```ini
TASK_ID=TASK172_V0_7_TUBE_LAMINAR_CONSTANT_PROPERTY_SCOPE_AUTHORITIES_INDEPENDENT_REVIEW_R1
PR_NUMBER=277
PR_STATE=OPEN_DRAFT
BRANCH=docs/v0-7-task172-entry-authority
EXPECTED_START_HEAD=e82b5fadec6d9de2f8b0901f775197ad0e511c32
PREVIOUS_HEAD_SHA=e82b5fadec6d9de2f8b0901f775197ad0e511c32
MODE=INDEPENDENT_BRANCH_SCOPE_AUTHORITY_REVIEW_ONLY
PARENT_BLOCKER=TUBE-WALL-CORRECTION-AUTHORITY
CWT_AUTHORITY_ID=V07-T172-TUBE-LAMINAR-CWT-PROPERTY-SCOPE-R1
CHF_AUTHORITY_ID=V07-T172-TUBE-LAMINAR-CHF-PROPERTY-SCOPE-R1
RESULT=PASS_FOR_SCOPED_LAMINAR_CONSTANT_PROPERTY_BRANCH_AUTHORITIES
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

The result is a positive independent review of the *scope candidate and its
admission semantics*.  The candidates remain `PROPOSED_AUTHORITY`, and their
independent-review lifecycle fields remain `PENDING`, until the separately
authorized external scoped-acceptance gate is completed.

## 2. Source-scope verification

The source body and source rights boundary are inherited from the completed
primary-source package:

* [TASK172 laminar primary-source acquisition R1](TASK-172-v0.7-tube-laminar-primary-source-acquisition-r1.md)
* [TASK172 constant-property scope disposition R1](TASK-172-v0.7-tube-laminar-constant-property-scope-disposition-adjudication-r1.md)

The acquired body is `NASA-CR-189922`, source-body SHA-256
`46c1af47bf173cd0a33f7b491d73e635e3335ce67277df50f4f8df2840e5cd5e`.
The exact source scope is:

| Branch | Source location | Source model scope | Native TASK026 identity |
| --- | --- | --- | --- |
| CWT | Chapter 3 §3.3.3; report pp.14–16 and 19–20; Eqs. 3.20a, 3.28, 3.47–3.51; PDF pp.28–34 | Fully developed circular tube, constant wall temperature, constant nominal properties; `Nu_D = 3.658` in Eq. 3.51 | `tube_laminar_cwt@1.0.0`, native `Nu_D = 3.66` |
| CHF | Chapter 3 §3.3.2; report pp.14–19; Eqs. 3.20a, 3.28, 3.39–3.46; PDF pp.28–33 | Fully developed circular tube, constant heat flux, constant nominal properties; `Nu_D = 4.364` in Eq. 3.46 | `tube_laminar_chf@1.0.0`, native `Nu_D = 4.36` |

The scope is sufficient for the two exact constant-property native branch
models.  It does not cover a variable-property extension, a wall/bulk
property ratio, an active correction, or an assertion that an active
correction is never required.

```ini
SOURCE_INTEGRITY=PASS
CWT_CONSTANT_PROPERTY_SOURCE_SCOPE_VALID=true
CHF_CONSTANT_PROPERTY_SOURCE_SCOPE_VALID=true
CWT_SOURCE_SCOPE_EXCLUDES_VARIABLE_PROPERTY_EXTENSION=true
CHF_SOURCE_SCOPE_EXCLUDES_VARIABLE_PROPERTY_EXTENSION=true
EXCLUSION_MEANING=NOT_COVERED_BY_THIS_AUTHORITY_NOT_PHYSICALLY_IMPOSSIBLE
```

The exclusion is therefore a source-coverage result, not a physical
impossibility claim.

## 3. Native TASK026 interaction audit

The reviewed production path is
`src/hexagent/exchangers/shell_tube/tube_side_thermal/single_phase.py::compute_single_phase`.
It consumes all of the following thermophysical inputs:

```text
density_kg_m3
dynamic_viscosity_pa_s
thermal_conductivity_w_m_k
specific_heat_capacity_j_kg_k
```

Those values participate in the existing native operations:

```text
v  = m_dot / (rho * A_total)
Re = rho * v * D_h / mu
Pr = mu * cp / k
Nu = 3.66 (CWT) or 4.36 (CHF) in the laminar branch
h_i = Nu * k / D_h
```

The branch's constant `Nu` does not make `h_i` independent of the property
snapshot.  Changing `rho`, `mu`, `cp`, or `k` can change velocity,
applicability quantities, or the resulting HTC.  In particular, changing
`k` changes `h_i` even when `Nu` remains exactly the native constant.

```ini
THERMAL_CONDUCTIVITY_REFRESH_IS_VARIABLE_PROPERTY_USE=true
UPSTREAM_TEMPERATURE_DRIVEN_PROPERTY_REFRESH_COUNTS_AS_VARIABLE_PROPERTY=true
```

The audit therefore rejects this loophole:

```text
upstream temperature -> new property values -> one snapshot per function call
-> native branch -> “constant-property” by call-local wording
```

The property values are not required to be looked up inside
`compute_single_phase` for the use to be variable-property.  A changed
temperature-driven property set supplied by an upstream caller has the same
semantic effect and is outside these branch-scope candidates.

## 4. Frozen property-snapshot contract

### 4.1 Identity and components

The candidate scope requires a property snapshot identity, not merely a
function-call payload.  The identity must cover every thermophysical input
that the native branch consumes, together with the authority and state
binding needed to show what those values mean:

```ini
PROPERTY_SNAPSHOT_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_COMPONENTS=DENSITY;DYNAMIC_VISCOSITY;THERMAL_CONDUCTIVITY;SPECIFIC_HEAT_CAPACITY;UNITS;PROPERTY_AUTHORITY_ID_AND_HASH;REFERENCE_STATE_IDENTITY
PROPERTY_SNAPSHOT_CASE_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_SEGMENT_IDENTITY_REQUIRED=true
PROPERTY_SNAPSHOT_BINDING_GRANULARITY=EXPLICIT_CASE_SCOPE_OR_EXPLICIT_PHYSICAL_SEGMENT_SCOPE;NO_UNSCOPED_CALCULATION_SCOPE
PROPERTY_SNAPSHOT_IMMUTABILITY_REQUIRED=true
```

`Pr` is a derived quantity in the existing TASK026 path; it is not an
independent property source.  The snapshot must therefore bind the source
inputs used to derive it rather than allowing `Pr` to be copied from another
temperature, backend, or table.

### 4.2 Lifetime and refresh

For a branch authority instance, the snapshot lifetime is explicit and
unambiguous:

```ini
PROPERTY_SNAPSHOT_LIFETIME=ALL_EVALUATIONS_AND_ALL_NONLINEAR_ITERATIONS_OF_THE_BOUND_AUTHORITY_INSTANCE
PROPERTY_SNAPSHOT_ITERATION_REFRESH_ALLOWED=false
PER_SEGMENT_DISTINCT_FROZEN_SNAPSHOT_POLICY=FORBIDDEN_WITHOUT_VARIABLE_PROPERTY_EXTENSION
```

The authority instance must be bound either to one complete declared case or
to one declared physical segment, with the case identity always present.  A
segment-scoped instance must carry the segment identity; a whole-case
instance must carry an explicit whole-case scope marker.  The phrase “for the
calculation” is not a valid substitute for this scope.

No iteration may replace the snapshot because `T_bulk`, `T_film`, `T_wall`,
or any other state changed.  No segment may silently receive a distinct
temperature-derived snapshot.  A future variable-property extension would
need its own reviewed authority, state mapping, domain, and canonical
identity; this review creates none of those.

### 4.3 Reference-state separation

`NASA-CR-189922` defines the constant-property analytical branch scope; it
does not select the TASK172 property reference temperature.  Therefore:

```ini
REFERENCE_STATE_SELECTION_AUTHORITY_BOUND_BY_THIS_SCOPE=false
CASE_LEVEL_REFERENCE_STATE_AUTHORITY_REQUIRED=true
```

Bulk, wall, film, inlet, mean, and backend-default temperatures are not
implicitly selected by either CWT or CHF scope authority.  A case-level
reference-state authority must be separately source-bound and reviewed.

## 5. Wall-temperature semantics

The following distinction is accepted:

```ini
WALL_TEMPERATURE_DIFFERENCE_ALONE_IMPLIES_VARIABLE_PROPERTY=false
WALL_STATE_PROPERTY_REEVALUATION_IMPLIES_VARIABLE_PROPERTY=true
```

`T_wall != T_bulk` can coexist with a constant-property laminar branch when
the branch consumes the same frozen `rho`, `mu`, `k`, and `cp` snapshot.  It
becomes variable-property use when the branch or its upstream producer
reevaluates any consumed property as a function of `T_wall`, `T_bulk`,
`T_film`, local temperature, or iteration state, or when it evaluates a
bulk/wall property ratio.

This scope authority does not authorize a wall-temperature solver, a
viscosity correction, a property-ratio correction, a shell-side transfer, or
an omission claim.  In particular:

```ini
CWT_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CHF_NO_ACTIVE_WALL_CORRECTION_REQUIRED=NOT_CLAIMED
CWT_ACTIVE_CORRECTION_AUTHORITY=NONE
CHF_ACTIVE_CORRECTION_AUTHORITY=NONE
```

## 6. Branch-scope review dispositions

The two candidates are reviewed separately; neither source is transferred
across the CWT/CHF boundary.

```ini
CWT_SCOPE_AUTHORITY_REVIEW_RESULT=PASS
CWT_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CWT_SCOPE_AUTHORITY_CANDIDATE_COMPLETE=true
CWT_STATUS=PROPOSED_AUTHORITY
CWT_INDEPENDENT_REVIEW=PENDING

CHF_SCOPE_AUTHORITY_REVIEW_RESULT=PASS
CHF_AUTHORITY_TYPE=CONSTANT_PROPERTY_BRANCH_SCOPE
CHF_SCOPE_AUTHORITY_CANDIDATE_COMPLETE=true
CHF_STATUS=PROPOSED_AUTHORITY
CHF_INDEPENDENT_REVIEW=PENDING
```

The admitted semantic is:

```ini
CWT_BRANCH_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
CHF_BRANCH_DISPOSITION=CONSTANT_PROPERTY_ONLY_VARIABLE_PROPERTY_EXTENSION_BLOCKED
VARIABLE_PROPERTY_OUTCOME=BLOCKED_MISSING_LAMINAR_VARIABLE_PROPERTY_EXTENSION_AUTHORITY
NO_SILENT_FALLBACK_TO_CWT_NU_3_66=true
NO_SILENT_FALLBACK_TO_CHF_NU_4_36=true
```

The branch candidates do not create an omission authority.  They simply
permit the exact native constant-property branch within its source scope and
fail closed when the requested use is a variable-property extension.

## 7. Fail-closed cases

The following are outside the proposed scope and must be blocked rather than
coerced into a native constant-property result:

* property lookup or refresh driven by wall, bulk, film, local, or iteration
  temperature;
* a changed property snapshot supplied on a later iteration;
* a distinct per-segment snapshot without a separately reviewed extension;
* an unbound reference-temperature rule;
* a bulk/wall property ratio;
* a hidden backend default or material/database lookup;
* a missing snapshot component, identity, source binding, or hash;
* a snapshot/body/domain/reference-state mismatch;
* a request to silently fall back to `Nu_D = 3.66` or `4.36` after variable
  properties were requested.

The native `requires_wall_viscosity=false` flag, a narrow water range,
`factor=1`, or the reviewed turbulent C3 correction cannot authorize any of
these cases.

## 8. Parent blocker and effective governance state

This review does not establish whole-branch coverage: the proposed CWT and
CHF candidates still require external scoped acceptance, and the native
laminar candidates do not provide the missing variable-property extension.

```ini
INDEPENDENT_REVIEW_RESULT=PASS_FOR_SCOPED_LAMINAR_CONSTANT_PROPERTY_BRANCH_AUTHORITIES
LIFECYCLE_PROMOTION_PERFORMED=false
ALL_ADMITTED_TUBE_BRANCHES_AUTHORITY_COVERED=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_CLOSURE_ELIGIBLE=false
TUBE_WALL_CORRECTION_CANONICAL_BLOCKER_REMOVED=false

REMAINING_TASK172_ENTRY_BLOCKERS=TUBE-WALL-CORRECTION-AUTHORITY,SHELL-WALL-CORRECTION-AUTHORITY,LOCAL-RESIDUAL-AND-METHOD-QUALIFICATION,NUMERICAL-ERROR-BUDGET-AND-STOPPING-REVIEW,MESH-CONVERGENCE-QUALIFICATION
REMAINING_TASK172_ENTRY_BLOCKER_COUNT=5
TASK172_ENTRY_AUTHORITY_COMPLETE=false
```

The accepted turbulent C3 correction remains independent and is not
transferred to either laminar branch.  No historical payload or hash is
rewritten.

## 9. Governance and next gate

```ini
CWT_OMISSION_AUTHORITY_CREATED=false
CHF_OMISSION_AUTHORITY_CREATED=false
CWT_ACTIVE_CORRECTION_CREATED=false
CHF_ACTIVE_CORRECTION_CREATED=false
NATIVE_CWT_IDENTITY_CHANGED=false
NATIVE_CHF_IDENTITY_CHANGED=false
NATIVE_CWT_CONSTANT_CHANGED=false
NATIVE_CHF_CONSTANT_CHANGED=false
TASK026_FILES_CHANGED=false
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
```

The next gate is limited to external confirmation or rejection of these two
scoped candidates:

```ini
NEXT_GATE=EXTERNAL_INDEPENDENT_REVIEWER_CONFIRM_OR_REJECT_SCOPED_LAMINAR_CONSTANT_PROPERTY_BRANCH_AUTHORITIES
NO_STEP_IMPLIES_THE_NEXT=true
```

Evidence for this receipt is recorded in
[the machine-readable review record](evidence/TASK-172-tube-laminar-constant-property-scope-authorities-independent-review-r1.json).
