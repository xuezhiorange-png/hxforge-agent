# TASK-172 v0.7 — Production Reference-Oracle Requirement Authority R1

## 1. Decision and lifecycle

```ini
TASK_ID=TASK172_V0_7_PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_R1
AUTHORITY_ID=V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-R1
PR_NUMBER=279
PR_STATE=OPEN_DRAFT
BASE_MAIN_SHA=fbff0ec3db398e61fbe332bc0850f3e34dc4e4fa
MODE=PROPOSED_BOOLEAN_REQUIREMENT_AUTHORITY_CANDIDATE
RESULT=PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_CANDIDATE_COMPLETED
LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
TARGET_FIELD=production_reference_oracle_required
DECISION=false
DECISION_ORIGIN=USER_SUPPLIED_ARCHITECTURE_DECISION
CODEX_SELF_APPROVAL=false
INDEPENDENT_REVIEW_COMPLETE=false
LIFECYCLE_PROMOTION_PERFORMED=false
```

The decision candidate means only:

> An online continuous-reference oracle is **not a mandatory prerequisite** for
> TASK172 real-case mesh admission within the exact scope defined by this
> authority.

It does **not** mean that all reference comparison is inapplicable. It does not
select a reference-comparison policy, prohibit a future case-specific reference,
authorize an online oracle, or approve any quantitative real-case mesh rule.

The decision origin is the user-supplied architecture decision. The historical
authorities below are compatibility and applicability evidence; they are not
misrepresented as having already selected this Boolean value.

## 2. Authority basis and compatibility evidence

The candidate is compatible with the existing reviewed/frozen boundaries:

| Source | Bound identity | Relevance |
|---|---|---|
| TASK170 v0.7 freeze | `docs/tasks/TASK-170-v0.7-scope-source-golden-freeze.md`; SHA-256 `5fc00303e3a74a850b22f89a4c56bbad1b269f39d6a32e652b56b19402b22de0` | Production Rating requires explicit geometry/topology, mesh, and numerical-profile authorities; it does not bind an online continuous-reference oracle requirement. |
| R102 continuous reference | `SCIPY_SPECIAL_ROOTS_LEGENDRE_ORDER_1024`; correction document SHA-256 `300eee99502beb815bf72a64b57d2c66a771c8d2cf795e5fa8148ac875c5e5d8` | Reviewed synthetic qualification reference and empirical uncertainty envelope; explicitly not an online production-oracle mandate. |
| R103 final mesh qualification | R103 document SHA-256 `4ab8c5c6ae1a7f499feaa2411c701d57c0b75b5aef4533e27991c187d019d431`; extension canonical hash `331bb73c09f0b2ec00260886abb1ceec65b3a2996dcb02a17d144e252ef51ac9` | Reviewed only for six frozen synthetic fixtures/profile; no real-case generalization or online-oracle mandate. |
| R104 real-case mesh admission candidate | document SHA-256 `8154066139f6587be3f627e1d73c882d5719a53a1c828f22a3f04024de2ee73c` | Separates the R102 qualification oracle from the unbound production reference policy and records `PRODUCTION_REFERENCE_ORACLE_REQUIRED=UNBOUND`. |
| R106 correction overlay | document SHA-256 `81763418d1ba280fae30da440f31831e538b169a1fff083b99516bb16ec26e07`; evidence canonical `b101a63e74e6dcc4005d6023253472f6f66ef458d4ef21152ae11bc29954bbe3` | Requires reviewed resolution of every applicable policy slot and states that reference-policy `NOT_APPLICABLE` does not decide whether an online oracle is required. |
| R107/R108 predicate authority | R107 evidence canonical `cc0b6a4b28168a15040f909249c101a0ff5edd163db269a20e0cfe9a9edd7169`; R108 evidence canonical `f539e7eb518d8017ed7a732c8bbd69795af0009de8a666cfc4d6b954cae60696` | Reviewed fail-closed rule: the Boolean must be resolved by a case/profile-applicable reviewed authority with identity/hash, exact scope, case binding, and applicability evidence. |

These sources establish that `false` is compatible with the existing
architecture. They do not by themselves constitute the new Boolean decision.

## 3. Exact profile scope

This candidate is restricted to the TASK172 real-case mesh-admission family
already bounded by the reviewed/frozen TASK170/TASK171 structural authorities:

```text
FIXED_TUBESHEET
E_SHELL
ONE_SHELL_PASS
ONE_DECLARED_STRAIGHT_THROUGH_TUBE_PASS
EXPLICIT_COUNTERCURRENT_HOT_AND_COLD_PATHS
NATIVE_TASK020_024_ACCEPTED_GEOMETRY
EXISTING_SINGLE_SEGMENTAL_BAFFLE_AND_BELL_COMPATIBILITY_GATES
STEADY_SINGLE_PHASE_NEWTONIAN_SERVICE
```

The authority is not applicable to an unsupported topology/profile, alternate
shell/baffle family, U-tube/floating-head case, additional or split tube passes,
cocurrent/branching/reversing paths, two-phase/transient service, or any case
requiring excluded physics.

```ini
EXACT_PROFILE_SCOPE_BOUND=true
PROFILE_SCOPE_ID=V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-SCOPE-R1
UNSUPPORTED_OR_SCOPE_MISMATCHED_CASE_RESOLUTION_VALID=false
```

## 4. Case-binding contract

R107 requires case binding. This candidate defines the required binding but does
not fabricate a real case instance.

A future case can consume this decision only when its admission record binds:

```text
CASE_ID
CONFIGURATION_ID
GEOMETRY_ID
TOPOLOGY_AUTHORITY_ID
FLOW_PATH_MAPPING_ID
PRODUCTION_MESH_PROFILE_AUTHORITY_ID
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_ID
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_CANONICAL_HASH
PROFILE_SCOPE_ID
APPLICABILITY_EVIDENCE_ID_OR_HASH
```

and all bound identities are exact, lifecycle-valid, mutually consistent, and
applicable to that case.

```ini
CASE_BINDING_REQUIRED=true
CURRENT_REAL_CASE_BINDING_PRESENT=false
CALLER_BOOLEAN_ASSERTION_IS_AUTHORITY=false
PROFILE_NAME_WITHOUT_CANONICAL_IDENTITY_IS_AUTHORITY=false
```

Because this R109A task creates no actual case binding, it does not make the
current effective R107 resolution valid.

## 5. Applicability semantics of DECISION=false

`false` has the narrow semantic meaning:

```ini
ONLINE_CONTINUOUS_REFERENCE_ORACLE_IS_MANDATORY_ADMISSION_PREREQUISITE=false
ALL_REFERENCE_COMPARISON_IS_NOT_APPLICABLE=false
REFERENCE_COMPARISON_FORBIDDEN=false
CASE_SPECIFIC_REFERENCE_AUTHORITY_FORBIDDEN=false
OFFLINE_QUALIFICATION_REFERENCE_FORBIDDEN=false
PERIODIC_VALIDATION_REFERENCE_FORBIDDEN=false
```

A future reference policy remains a separate authority question. It may resolve
to a bound comparison policy or to reviewed case/profile-bound
`NOT_APPLICABLE` semantics. This Boolean authority does not choose between
those possibilities.

No accuracy, convergence, safety, performance, or resource claim is inferred
from `false`. It merely removes online continuous-reference execution as a
mandatory universal prerequisite if and when this authority is independently
reviewed and validly case-bound.

## 6. Current effective state

This is a proposed authority candidate, not a reviewed authority receipt.

```ini
PRODUCTION_REFERENCE_ORACLE_REQUIRED_CANDIDATE=false
PRODUCTION_REFERENCE_ORACLE_REQUIRED_EFFECTIVE=UNBOUND
EFFECTIVE_REVIEWED_BINDING=UNBOUND
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLUTION_VALID=false
REFERENCE_POLICY_RESOLUTION_VALID=false
REAL_CASE_MESH_ADMISSIBLE=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
```

Independent review and case applicability/binding remain mandatory under R107.

## 7. Explicit non-creation boundary

```ini
REFERENCE_POLICY_CREATED=false
ONLINE_ORACLE_IMPLEMENTED=false
ONLINE_ORACLE_EXECUTION_AUTHORIZED=false
INITIAL_MESH_POLICY_CREATED=false
REFINEMENT_POLICY_CREATED=false
CONVERGENCE_THRESHOLD_CREATED=false
HEADROOM_POLICY_CREATED=false
RESOURCE_POLICY_CREATED=false
WALL_ACCEPTANCE_POLICY_CREATED=false
R98_C_ROUND_REAL_CASE_TRANSFER_AUTHORIZED=false
NORMALIZED_MESH_DESCRIPTOR_CREATED=false
OTHER_QUANTITATIVE_MESH_POLICY_CREATED=false
PRODUCTION_CODE_CHANGED=false
ENGINEERING_CALCULATION_CHANGED=false
DEPENDENCY_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TASK173_SOLVE_PERFORMED=false
TASK174_SOLVE_PERFORMED=false
```

## 8. Governance and next gate

```ini
INDEPENDENT_REVIEW_REQUIRED=true
LIFECYCLE_PROMOTION_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NEXT_GATE=AUTHORIZE_TASK172_PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_INDEPENDENT_REVIEW_ONLY
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The next gate may review this exact authority identity, decision semantics,
scope, case-binding contract, applicability basis, and canonical hash. It must
not silently create a reference policy or quantitative mesh policy.
