# TASK-172 v0.7 — Real-Case Mesh Admission Contract Correction R1

Task: `TASK172_REAL_CASE_MESH_ADMISSION_CONTRACT_CORRECTION_ONLY`
PR: #277 (`OPEN_DRAFT`)
Authorized predecessor: `74919809dcdc663719dad1da86bac4267fbd3059`
Result: `REAL_CASE_MESH_ADMISSION_CONTRACT_CORRECTION_CANDIDATE_COMPLETED`

## Scope and historical boundary

This is an append-only correction for exactly the three R105 review findings:
`R104-HASH-01`, `R104-PREDICATE-02`, and `R104-XFER-07`. R104 and R105
documents, evidence, matrices, registry extensions, and their original hash
claims remain immutable. The new evidence records effective shared-canonical
hash recomputations for the unchanged R104 payloads; it does not edit their
embedded historical declarations.

No initial cell count, split/refinement rule, convergence threshold, headroom
value, resource cap, reference selection, wall acceptance value,
`C_round` real-case transfer, or normalized mesh descriptor is selected here.
No mesh study, production implementation, rating, TASK173/TASK174 solve, Ready,
or Merge action was performed.

## R104 hash correction overlay

The independent replay uses the repository's existing
`hexagent.canonical_json.canonical_sha256` implementation. That implementation
normalizes strings to NFC, serializes with RFC 8785, rejects non-finite JSON
numbers, and excludes `canonical_hash` and `mutable_review_comments` from hash
input. No alternate canonicalization is introduced.

The original file SHA-256 bindings reproduce. The historical canonical values
do not reproduce under the shared helper; the effective recomputations below
are therefore bound by this append-only overlay:

| R104 payload | Direct file SHA-256 | Historical declared canonical hash | Shared-helper recomputation |
|---|---|---|---|
| Contract document | `8154066139f6587be3f627e1d73c882d5719a53a1c828f22a3f04024de2ee73c` | Not declared | Not applicable |
| Contract evidence | `2a9f16b7eda50e568dd627bba27fc5d137d83ac80c11baabec8f9729a53a7cc4` | `3b01d5642e0f28c440a4409902fbd916dd1ac5ada5e83653c1cc31e2cdc90d2d` | `2164dcfcdc585281238598d6bc271bbe015b72ce97fa5cc5326a888993457135` |
| Transfer matrix | `06bf948f6508a5cafa120d5d8be6928e4d35ef7f6ee1f09b34cd16f96fc53c65` | `991e4024e2bfed5f49eaff453f6a564d0a165036174ed6b06a8901038589509a` | `5b5e92f7346b22cd1de0e5c28caa0ef67e211df91febb70d3354f9ed3f94e14a` |
| `r104_extension` at R104 head | Registry payload | `da7dc27f1e0094fc2880522593697bfc4eb31ba6ff676f6125540e3f9c54e44d` | `e035372e976e1ede05482c30c59c0d8a3defd4c3bfc802c87321144ba3f1d8bc` |
| Registry root at R104 head | Registry file SHA-256 `671ed3585d9eee0050100d17a86c8c9e24439818f96a93316c66a6d1e50d2adc` | `e69689e4960bad3ddb7ba961134cf27b6532cb118af8d614c8c31ea789771887` | `00353f88e0c6c5aba94f2043403e41208014e769a05c8461ffada76169af41d7` |

The recomputed registry-root value is for the immutable R104 registry snapshot,
not the current R105 registry. The R105 extension and R105 registry root were
also independently replayed and remain unchanged. Full paths, digests, helper
identity, and linkage are in the structured correction evidence.

## Explicit fail-closed policy resolution

R104 listed each production mesh operand separately but its Boolean predicate
did not define how all those operands affect its broad profile-validity terms.
This correction makes every listed slot an explicit conjunct. It defines only
contract logic; it does not supply policy content.

For each policy slot, a resolution is valid only when either:

1. The slot is `BOUND` to an authority identity and hash whose lifecycle is
   `REVIEWED_AUTHORITY`, whose scope applies to the exact case/profile, and
   whose required case binding and applicability evidence are present; or
2. The slot is `NOT_APPLICABLE` under an equally explicit, reviewed,
   case/profile-bound applicability decision with a reason and evidence.

`UNBOUND`, missing, null, unknown, malformed, stale, scope-mismatched, or
non-reviewed values are false. Absence is never equivalent to
`NOT_APPLICABLE`. These are contract-resolution states, not newly created
runtime error enums. A reference-policy `NOT_APPLICABLE` decision does not
select whether an online oracle is required; that decision still needs its own
reviewed case/profile authority. Likewise, no `C_round` value or real-case
rounding rule is selected.

The explicit candidate predicate is:

```text
REAL_CASE_MESH_ADMISSIBLE =
    topology_authority_valid
    AND geometry_mapping_valid
    AND mesh_identity_contract_valid
    AND case_scope_supported
    AND required_case_bindings_complete
    AND initial_mesh_rule_resolution_valid
    AND refinement_rule_resolution_valid
    AND convergence_rule_resolution_valid
    AND headroom_slot_resolution_valid
    AND resource_policy_resolution_valid
    AND reference_policy_resolution_valid
    AND wall_acceptance_policy_resolution_valid
    AND rounding_policy_resolution_valid
    AND normalized_mesh_descriptor_resolution_valid
    AND deterministic_mapping_valid
    AND shared_canonicalization_valid
```

`headroom_slot_resolution_valid` represents only the headroom slot proposed by
R104. It is not an inherited TASK172 requirement. If that candidate slot is
retained, it must resolve through reviewed applicability evidence; the
predicate does not require any particular headroom value.

All policy slots remain unresolved at this predecessor. Therefore the
effective evaluation is `REAL_CASE_MESH_ADMISSIBLE=false`. A mesh-admission
contract decision remains distinct from case production admission; every
upstream case-level authority gate continues to apply.

## Corrected headroom attribution

R104's `one_later_headroom_level` disposition remains
`ADDITIONAL_AUTHORITY_REQUIRED`; the synthetic one-level value remains
validation-only. Its transfer basis is corrected by this overlay:

```ini
TASK172_REQUIRES_HEADROOM_RULE=false
R104_HEADROOM_SLOT_ORIGIN=R104_PROPOSED_PROJECT_CONTRACT_SLOT
R103_HEADROOM_VALUE_TRANSFERRED=false
REAL_CASE_HEADROOM_RULE_BOUND=false
HEADROOM_AUTHORITY_ABSENCE_FAILS_CLOSED=true
```

TASK172 mesh contract §11 requires a future convergence criterion to bind its
observable set, comparison metric, refinement sequence, physical-support
mapping, precision floor, acceptance threshold, required consecutive evidence,
and failure disposition. It does not require a headroom rule. R104 may retain
headroom as a proposed slot, but it must not attribute that slot to TASK172 or
transfer R103's numeric value.

## Effective lifecycle and stop boundary

```ini
R104_HISTORICAL_ARTIFACTS_CHANGED=false
R105_HISTORICAL_ARTIFACTS_CHANGED=false
R1_R105_REGISTRY_EXTENSIONS_REWRITTEN=false
R104_EFFECTIVE_HASH_REBINDING_RECORDED=true
R104_FAIL_CLOSED_PREDICATE_CORRECTION_CANDIDATE=true
R104_HEADROOM_ATTRIBUTION_CORRECTION_CANDIDATE=true
R106_CORRECTION_LIFECYCLE=PROPOSED_AUTHORITY_REVIEW_PENDING
INDEPENDENT_REVIEW_REQUIRED=true
INITIAL_MESH_VALUE_CREATED=false
REFINEMENT_RULE_CREATED=false
CONVERGENCE_THRESHOLD_CREATED=false
HEADROOM_VALUE_CREATED=false
RESOURCE_CAP_CREATED=false
REFERENCE_POLICY_SELECTED=false
WALL_ACCEPTANCE_VALUE_CREATED=false
R98_C_ROUND_REAL_CASE_TRANSFER_AUTHORIZED=false
NORMALIZED_MESH_DESCRIPTOR_CREATED=false
PRODUCTION_CODE_CHANGED=false
TASK172_IMPLEMENTATION_STARTED=false
TASK173_SOLVE_PERFORMED=false
TASK174_SOLVE_PERFORMED=false
READY_AUTHORIZED=false
MERGE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

The correction is ready for a separate independent review only. It does not
promote the R104 contract or enable production mesh admission.
