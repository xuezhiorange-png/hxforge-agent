# TASK-172 v0.7 — Real-Case Mesh Admission Reference-Oracle Predicate Correction R1

Task: `TASK172_REAL_CASE_MESH_ADMISSION_REFERENCE_ORACLE_PREDICATE_CORRECTION_ONLY`
PR: #277 (`OPEN_DRAFT`)
Authorized predecessor: `92cf7d7392ace146310e387fe0a045fdf4d083d9`
Result: `REAL_CASE_MESH_ADMISSION_REFERENCE_ORACLE_PREDICATE_CORRECTION_CANDIDATE_COMPLETED`

## Scope

This append-only correction closes only the residual of `R104-PREDICATE-02`:
the existing `production_reference_oracle_required` decision was recorded as
`UNBOUND`, but was not guaranteed to block the real-case mesh predicate.
R104, R105, and R106 artifacts and registry extensions remain unchanged.

This correction does not choose `production_reference_oracle_required` as
`true` or `false`; select a reference policy; authorize or implement an online
oracle; or create any initial-mesh, refinement, convergence, headroom, resource,
wall-acceptance, `C_round`, or normalized-mesh policy.

## Explicit reviewed resolution gate

The pre-existing field remains unresolved:

```ini
PRODUCTION_REFERENCE_ORACLE_REQUIRED_VALUE=UNBOUND
```

Define `production_reference_oracle_requirement_resolution_valid` as true only
when a case/profile-applicable `REVIEWED_AUTHORITY` explicitly resolves the
existing field to a Boolean value (`true` or `false`) and supplies all of:
authority identity and canonical hash, lifecycle, exact case/profile scope,
case binding, and applicability evidence. This is a resolution contract only;
it does not select either Boolean value or prescribe the policy rationale.

`UNBOUND`, missing, null, unknown, malformed, stale, non-Boolean, non-reviewed,
unbound-to-case, or scope-mismatched decisions evaluate false. A generic
`reference_policy` `NOT_APPLICABLE` disposition does not resolve this field and
cannot substitute for its reviewed Boolean decision.

## Composite reference-policy gate

To make the dependency unambiguous, bind:

```text
reference_policy_resolution_valid =
    reference_policy_applicability_resolution_valid
    AND production_reference_oracle_requirement_resolution_valid
```

`reference_policy_applicability_resolution_valid` is the existing R106
reference-policy slot resolution under its already-bound `BOUND` /
authority-bound `NOT_APPLICABLE` semantics. It must not be treated as resolving
the separate online-oracle requirement by implication.

The real-case mesh predicate therefore includes both the explicit gate and its
composite reference-policy term:

```text
REAL_CASE_MESH_ADMISSIBLE =
    ...
    AND production_reference_oracle_requirement_resolution_valid
    AND reference_policy_resolution_valid
    ...
```

The explicit conjunct is intentionally retained even though it is part of the
composite: it makes the independently unresolved R104 field visible in the
admission expression and prevents a future implementation from accidentally
dropping it through an incomplete composite alias.

At this predecessor, the value remains `UNBOUND`, so:

```ini
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLUTION_VALID=false
REFERENCE_POLICY_RESOLUTION_VALID=false
REAL_CASE_MESH_ADMISSIBLE=false
```

No online oracle execution or production mesh admission is authorized by this
contract correction.

## Effective boundary

```ini
R104_HISTORICAL_ARTIFACTS_CHANGED=false
R105_HISTORICAL_ARTIFACTS_CHANGED=false
R106_HISTORICAL_ARTIFACTS_CHANGED=false
R1_R106_REGISTRY_EXTENSIONS_REWRITTEN=false
PRODUCTION_REFERENCE_ORACLE_REQUIRED_VALUE_SELECTED=false
REFERENCE_POLICY_CREATED=false
ONLINE_ORACLE_IMPLEMENTED=false
ALL_OTHER_REAL_CASE_MESH_POLICY_SLOTS_UNCHANGED=true
PRODUCTION_MESH_ADMISSION_ENABLED=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TASK173_SOLVE_PERFORMED=false
TASK174_SOLVE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

This correction is an append-only predicate overlay only. Any authority
promotion or selection of the Boolean decision requires its own reviewed
authority and separately authorized gate.
