# TASK-172 v0.7 — Real-Case Reference Policy Authority R1

Task: `TASK172_V0_7_REAL_CASE_REFERENCE_POLICY_AUTHORITY_R1`  
Short name: `R111`  
Authority ID: `V07-T172-REAL-CASE-REFERENCE-POLICY-R1`  
Base: `19925ba4f59fdb26bbcb8c7f43787e8e68af1304` (the current `main` at construction)  
Result: `REAL_CASE_REFERENCE_POLICY_AUTHORITY_CANDIDATE_COMPLETED`

## Decision boundary

This artifact projects the reviewed R109/R110 decision into a narrowly scoped
reference-policy candidate. It is not an independent review, lifecycle
promotion, production case binding, mesh policy, or online-reference
implementation. Its lifecycle remains `PROPOSED_AUTHORITY_REVIEW_PENDING`.

R109/R110 reviewed `production_reference_oracle_required=false` only as the
Boolean statement that an online continuous-reference oracle is not a
mandatory admission prerequisite within the exact reviewed profile. That
decision did not make all reference comparisons inapplicable, prohibit them,
or resolve a real-case policy or binding. R111 preserves those distinctions:

```ini
REFERENCE_POLICY_MODE=NON_MANDATORY_REFERENCE_COMPARISON
ONLINE_CONTINUOUS_REFERENCE_ORACLE_REQUIRED_FOR_ADMISSION=false
REFERENCE_COMPARISON_ALLOWED=true
REFERENCE_COMPARISON_MANDATORY=false
REFERENCE_COMPARISON_FORBIDDEN=false
REFERENCE_COMPARISON_CAN_BE_SEPARATELY_AUTHORIZED=true
```

Potential future policy categories are semantic roles only:
diagnostic comparison, qualification comparison, selective verification,
audit/replay reference, and case-specific reference checks. This candidate
does not create an implementation, reference producer, execution trigger,
frequency, sample count, tolerance, threshold, stopping criterion, or
acceptance role. Any actual comparison still requires its separately reviewed
producer, implementation, scope, and decision-role authority.

## Reviewed basis and exact scope

The policy basis is `REVIEWED_R109_R110_PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY`;
Codex self-approval is false. The bound requirement authority is
`V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-R1`, canonical hash
`5a302fadf7cc9fb5765f8630cf9c81ccceede66de0937b984a0af22e170350e7`, with
review receipt
`TASK172_V0_7_PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_INDEPENDENT_REVIEW_RECEIPT_R1`
(evidence canonical hash
`d6f71b0abcfdefed9f5892c91011d6066d52500522b5fc9c3faa0581c35205e3`). The
reviewed authority's effective lifecycle is `REVIEWED_AUTHORITY`; its case
binding remains absent. R111 accepts the reviewed Boolean as its policy basis
but does not resolve that binding or promote this candidate.

R111 reuses the exact profile scope
`V07-T172-PRODUCTION-REFERENCE-ORACLE-REQUIREMENT-SCOPE-R1`, without widening
it: fixed tubesheet, E-shell, one shell pass, one declared straight-through
tube pass, explicitly identified countercurrent hot/cold paths, native
TASK020–024 accepted geometry, existing single-segmental-baffle/Bell
compatibility gates, and steady single-phase Newtonian service. The canonical
scope identity, rather than this prose summary, governs applicability.
Unsupported, mismatched, and future unreviewed profiles remain invalid.

R102 remains a synthetic continuous-reference qualification authority and R103
remains a frozen synthetic mesh-qualification authority. Neither establishes
an online real-case oracle requirement, a universal real-case reference
comparison requirement, nor real-case mesh generalization. This candidate
does not promote their fixture values or numerical methods into production.

## Future case-bound policy binding contract

A future applicability resolution must bind, at minimum:

```text
CASE_ID
CONFIGURATION_ID
GEOMETRY_ID
TOPOLOGY_AUTHORITY_ID
PRODUCTION_MESH_PROFILE_AUTHORITY_ID
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_ID
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_AUTHORITY_CANONICAL_HASH
REFERENCE_POLICY_AUTHORITY_ID
REFERENCE_POLICY_AUTHORITY_CANONICAL_HASH
PROFILE_SCOPE_ID
APPLICABILITY_EVIDENCE_ID_OR_HASH
BINDING_CANONICAL_HASH
```

Every identity must be current, lifecycle-valid, scope-applicable, and bound
to the same case/profile. A caller assertion, profile label without canonical
identity, missing or stale binding, or scope mismatch cannot resolve the
policy. No actual case or case-bound reference policy is created here.

## Effective state remains fail-closed

```ini
REFERENCE_POLICY_AUTHORITY_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
CURRENT_REAL_CASE_BINDING_PRESENT=false
ACTUAL_REAL_CASE_ID_BOUND=false
CURRENT_REFERENCE_POLICY_CASE_BINDING_PRESENT=false
REFERENCE_POLICY_APPLICABILITY_RESOLUTION_VALID=false
PRODUCTION_REFERENCE_ORACLE_REQUIREMENT_RESOLUTION_VALID=false
REFERENCE_POLICY_RESOLUTION_VALID=false
EFFECTIVE_REVIEWED_BINDING=UNBOUND
REAL_CASE_MESH_ADMISSIBLE=false
PRODUCTION_MESH_ADMISSION_ENABLED=false
```

R107's composite gate remains in force:
`reference_policy_resolution_valid` requires both the case-applicable
reference-policy applicability resolution and the reviewed
production-reference-oracle requirement resolution. R111's unreviewed policy
candidate supplies neither a case binding nor a valid resolution.

## Explicitly unbound numerical and mesh policy

```ini
REFERENCE_NUMERIC_TOLERANCE_BOUND=false
REFERENCE_ERROR_THRESHOLD_BOUND=false
REFERENCE_RELATIVE_THRESHOLD_BOUND=false
REFERENCE_ABSOLUTE_THRESHOLD_BOUND=false
REFERENCE_EXECUTION_FREQUENCY_BOUND=false
REFERENCE_SAMPLE_COUNT_BOUND=false
REFERENCE_TRIGGER_RULE_BOUND=false
REFERENCE_STOPPING_ROLE_BOUND=false
REFERENCE_ACCEPTANCE_ROLE_BOUND=false
ONLINE_REFERENCE_IMPLEMENTATION_BOUND=false
ONLINE_REFERENCE_RUNTIME_BOUND=false

INITIAL_MESH_RULE_BOUND=false
REFINEMENT_RULE_BOUND=false
CONVERGENCE_RULE_BOUND=false
HEADROOM_RULE_BOUND=false
RESOURCE_POLICY_BOUND=false
WALL_ACCEPTANCE_RULE_BOUND=false
R98_C_ROUND_REAL_CASE_TRANSFER_AUTHORIZED=false
NORMALIZED_REAL_CASE_MESH_DESCRIPTOR_BOUND=false
```

No cell count, refinement ratio, threshold, headroom value, resource cap,
`C_round`, wall tolerance, or mesh stopping criterion is selected. R103's
synthetic-only scope and R104's historical hash discrepancy are left
unchanged; historical remediation is not authorized by R111.

## Governance

```ini
REFERENCE_POLICY_CREATED_AS_CANDIDATE=true
REFERENCE_POLICY_AUTHORITY_REVIEWED=false
REFERENCE_POLICY_APPLICABILITY_RESOLUTION_VALID=false
ACTUAL_REAL_CASE_BINDING_CREATION=false
REFERENCE_IMPLEMENTATION_CREATION=false
ONLINE_ORACLE_IMPLEMENTATION=false
REFERENCE_NUMERIC_POLICY_CREATION=false
QUANTITATIVE_MESH_POLICY_CREATION=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TASK173_SOLVE_PERFORMED=false
TASK174_SOLVE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
NEXT_GATE=INDEPENDENT_REVIEW_R111_ONLY
STOP=true
```
