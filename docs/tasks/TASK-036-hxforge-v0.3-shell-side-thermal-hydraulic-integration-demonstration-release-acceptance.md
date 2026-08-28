# TASK-036 — HXForge v0.3 Shell-Side Thermal-Hydraulic Integration, Demonstration and Release Acceptance

**Status:** PLANNED
**Milestone:** M3
**Priority:** P1
**Depends on:** TASK031, TASK032, TASK033, TASK034, TASK035
**Owner:** HXForge release-integration lane

This Design Contract is a direct implementation design for the frozen TASK036
Source Definition R5. It introduces no engineering equation, changes no
upstream producer contract, and does not authorize implementation, delivery,
tagging, or release operations.

## 0. Frozen authority and authoring boundary

```text
TASK=TASK036_DESIGN_AUTHORING_ONLY
AUTHORIZATION=AUTHORIZE_TASK036_DESIGN_AUTHORING_ONLY
AUTHORIZATION_SOURCE=explicit_user_authorization

REPOSITORY=xuezhiorange-png/hxforge-agent
ALLOCATION_AUTHORITY_ISSUE=180
SOURCE_DEFINITION_ISSUE=203
CURRENT_FROZEN_SOURCE_DEFINITION_REVISION=R5
SOURCE_DEFINITION_FREEZE_COMMENT_ID=5447744882
R2_COMMENT_ID=5446987220
R3_COMMENT_ID=5447178171
R4_COMMENT_ID=5447515540
R5_COMMENT_ID=5447649044
SOURCE_DEFINITION_IMMUTABLE=true

SOURCE_DECISION_COUNT=35
SOURCE_DECISION_PASS_COUNT=35
SOURCE_DECISION_CHANGES_REQUIRED_COUNT=0
SOURCE_DECISION_BLOCKED_COUNT=0
P0_COUNT=0
P1_COUNT=0
P2_COUNT=0
FINDINGS=NONE
TASK036_SOURCE_DEFINITION_REVIEW_RESULT=PASS
TASK036_SOURCE_DEFINITION_FROZEN=true

EXPECTED_ORIGIN_MAIN_SHA=6687170cea93486468266475e56193d57981761b
EXPECTED_ORIGIN_MAIN_TREE=8399dcf766b1c8d98794430e810d186134234d89
BASELINE_REFRESH=git fetch origin --prune

SOURCE_SEMANTICS_CHANGED=false
NEW_SOURCE_DECISION_ADDED=false
SOURCE_DECISION_REINTERPRETED=false
ENGINEERING_PHYSICS_ADDED=false
TASK031_ENGINEERING_REOPENED=false
TASK032_ENGINEERING_REOPENED=false
TASK033_ENGINEERING_REOPENED=false
TASK034_ENGINEERING_REOPENED=false
TASK035_ENGINEERING_REOPENED=false
DESIGN_ONLY_MUTATION=true
ARTIFACT_BYTES_GENERATED_IN_DESIGN_GATE=false
NO_STEP_IMPLIES_THE_NEXT=true
```

The only Design artifact is this file:

```text
DESIGN_PATH=docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md
DESIGN_FILE_COUNT_CREATED=1
COMPETING_TASK036_DESIGN_FILE_COUNT=0
```

The Design diff identity is the SHA-256 of the exact UTF-8 bytes emitted by
`git diff --no-ext-diff --no-index -- /dev/null DESIGN_PATH`, run from the
repository root. This empty-file comparison is used because the new Design
file is intentionally unstaged during this authoring gate. It covers only the
path named by `DESIGN_PATH`.

## 0A. Effective correction authority

This section records the narrow correction boundary. The effective R3
correction authority is Section 27 as a closed overlay on the preserved
architecture in Sections 25.1-25.6. The narrow R4 closure is Section 29: it
amends only the active node/stage materialization labels, the active
distribution-version derivation, and the determinism-surface lineage map.
Sections 25.7-25.11, the R2 closure overlay, and the R3 authoring/lifecycle
receipt remain in this file only for traceability after being explicitly
marked historical/superseded; their old artifact, manifest, version, test,
allowlist, and lifecycle values are not current implementation authority.

```text
TASK036_DESIGN_CORRECTION_AUTHORITY=SECTION_27_EFFECTIVE_R3_CORRECTION_PLUS_SECTION_29_NARROW_R4_CLOSURE_OVER_PRESERVED_SECTIONS_25_1_THROUGH_25_6
TASK036_PRECORRECTION_CONTRACT_STATUS=HISTORICAL_SUPERSEDED
TASK036_R1_CORRECTED_CONTRACT_STATUS=PRESERVED_BASE_CONTRACT
TASK036_CORRECTION_SCOPE=(F1,F2,F3,F4,F5,F6)
TASK036_R2_CORRECTION_SCOPE=(N1,N2,N3,N4)
TASK036_R2_CORRECTION_SCOPE_ONLY=true
TASK036_R3_CORRECTION_SCOPE=(D23,D25,D26,D32)
TASK036_R3_CORRECTION_SCOPE_ONLY=true
TASK036_FROZEN_SOURCE_DEFINITION_UNCHANGED=true
TASK036_REVIEW_PASS_AREAS_PRESERVED=true
TASK036_SECTION_25_7_OLD_ARTIFACT_AUTHORITY=HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY
TASK036_SECTION_25_8_OLD_DETERMINISM_ARTIFACT_SURFACES=HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY
TASK036_SECTION_25_9_OLD_TEST_AUTHORITY=HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY
TASK036_SECTION_25_10_OLD_VERSION_CONTRACT=HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY
TASK036_SECTION_25_11_OLD_ALLOWLIST_AUTHORITY=HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY
```

```text
DESIGN_DIFF_IDENTITY_SCOPE=DESIGN_PATH_ONLY
DESIGN_DIFF_IDENTITY_BASE=EMPTY_FILE
DESIGN_DIFF_IDENTITY_ENCODING=UTF-8
DESIGN_DIFF_IDENTITY_ALGORITHM=SHA-256
```

## 1. Role and non-scope

```text
TASK036_ROLE=VERSION_LEVEL_INTEGRATION_DEMONSTRATION_AND_RELEASE_ACCEPTANCE
RELEASE_ACCEPTANCE_IS_NOT_ENGINEERING_CORRECTNESS_PROOF=true
ENGINEERING_CORRECTNESS_AUTHORITY=INDEPENDENT_UPSTREAM_TASK_REVIEWS
VERSION_INTEGRATION_ACCEPTANCE_AUTHORITY=TASK036
TASK036_NEW_ENGINEERING_FORMULA=false
TASK036_RECOMPUTES_ENGINEERING_CORRECTNESS=false
TASK036_OVERRIDES_UPSTREAM_ENGINEERING_REVIEW=false
NO_RECOMPUTATION_OF_UPSTREAM_ENGINEERING=true
TASK036_PRESSURE_DROP_RECOMPUTATION=false
TASK036_HEAT_TRANSFER_RECOMPUTATION=false
TASK036_FLOW_STATE_RECOMPUTATION=false
TASK036_GEOMETRY_RECOMPUTATION=false
PUBLIC_API_EXTENSION=false
PERSISTENCE_EXTENSION=false
```

TASK036 consumes the actual public production graph and aggregates release
evidence. It does not create a second engineering result, replace an upstream
producer result, infer a missing value, or convert a blocked engineering
quantity to zero.

## 2. Current upstream authority

The current TASK035 producer is the merged PR205 implementation on the current
main line. Historical PR202 material remains evidence history only.

```text
CURRENT_TASK035_PR=205
CURRENT_TASK035_DELIVERY_COMMIT=e48d83208bfe4de782ee055a99c826fb9eebb334
CURRENT_TASK035_MERGE_COMMIT=6687170cea93486468266475e56193d57981761b
CURRENT_TASK035_TREE=8399dcf766b1c8d98794430e810d186134234d89
CURRENT_TASK035_CONTRACT_VERSION=v2
CURRENT_TASK035_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.v2
CURRENT_TASK035_PUBLIC_PACKAGE=hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition
CURRENT_TASK035_PUBLIC_OPERATION=validate_request
CURRENT_TASK035_PUBLIC_SIGNATURE=validate_request(raw_request: Any) -> Task035ValidationResult
TASK036_RUNTIME_ENTRY=TASK035_V2_PUBLIC_VALIDATE_REQUEST
TASK036_RUNTIME_PUBLIC_PACKAGE=hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition
TASK036_RUNTIME_PUBLIC_OPERATION=validate_request
TASK036_IMPORTS_TASK035_PRIVATE_HELPERS=false
TASK036_ACCEPTS_TASK035_V1_RUNTIME_RESULT=false
TASK036_DUAL_VERSION_ACCEPTANCE=false
TASK036_FIELD_SUBSET_ACCEPTANCE=false
TASK036_HAND_BUILT_TASK035_SUCCESS_AS_RUNTIME_INPUT=false
TASK036_FIXTURE_ONLY_TASK035_SUCCESS_AS_RUNTIME_INPUT=false
TASK036_EXPECTED_OUTPUT_AS_RUNTIME_INPUT=false
TASK036_EXPECTED_HASH_AS_RUNTIME_INPUT=false
TASK036_EXPECTED_RESULT_ID_AS_RUNTIME_INPUT=false
TASK036_IDENTITY_ADAPTER_OR_REWRITE=false
TASK036_REPAIR_TASK035_HASHES=false
TASK036_REPAIR_TASK035_RESULT_IDS=false
TASK036_REPAIR_TASK035_PROVENANCE=false
```

The current upstream evidence record is explicit and separate from runtime
engineering input:

```text
CURRENT_TASK035_TARGETED_TEST_COUNT=30
CURRENT_TASK035_TARGETED_PASS_COUNT=30
CURRENT_TASK035_TARGETED_FAIL_COUNT=0
CURRENT_TASK035_PR_CI_RUN_ID=33124912058
CURRENT_TASK035_MAIN_PUSH_CI_RUN_ID=33128978266
CURRENT_TASK035_CROSS_PYTHON_RUNTIME_COUNT=2
CURRENT_TASK035_CROSS_PYTHON_DETERMINISM=PASS
CURRENT_TASK035_REPEAT_RUN_DETERMINISM=PASS
CURRENT_PUBLIC_CHAIN_TASK034_RESULT_HASH=cd5709a86333731f32ac99f15810d00d794f3a3b0bb863043fae4af76035f9ed
CURRENT_PUBLIC_CHAIN_TASK034_RESULT_ID=9f0617d9-0522-537a-beb3-3e4e78a11c99
CURRENT_PUBLIC_CHAIN_TASK035_RESULT_HASH=05ae8da40b27203d1ed05de3de196f4821760e5aa2a21da7ac4c5ce138ef1fe9
CURRENT_PUBLIC_CHAIN_TASK035_RESULT_ID=09bc8107-c134-5d92-bada-eff31332ef5a
```

```text
UPSTREAM_REVIEW_EVIDENCE_USED_AS_RUNTIME_ENGINEERING_VALUE=false
UPSTREAM_TEST_EVIDENCE_USED_AS_RUNTIME_ENGINEERING_VALUE=false
UPSTREAM_CI_EVIDENCE_USED_AS_RUNTIME_ENGINEERING_VALUE=false
UPSTREAM_DETERMINISM_EVIDENCE_USED_AS_RUNTIME_ENGINEERING_VALUE=false
```

### Exact current Task035 consumer contract

The release demonstration binds the following closed Task035 v2 contract from
the current main producer. These projections are references to the delivered
producer authority, not a second Task035 schema or an alternate release input.

```text
CURRENT_TASK035_REQUEST_SCHEMA_ID=task035.shell-side-thermal-hydraulic-composition-request.v2
CURRENT_TASK035_SUCCESS_SCHEMA_ID=task035.shell-side-thermal-hydraulic-composition.v2
CURRENT_TASK035_TYPED_BLOCKED_SCHEMA_ID=task035.shell-side-thermal-hydraulic-composition-blocked.v2
CURRENT_TASK035_RAW_BOUNDARY_SCHEMA_ID=task035.shell-side-thermal-hydraulic-composition-raw-boundary-blocked.v2
CURRENT_TASK035_APPLICABILITY_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.applicability.v2
CURRENT_TASK035_COMPLETENESS_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.completeness.v2
CURRENT_TASK035_FIRST_SLICE_PROFILE_ID=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_THERMAL_HYDRAULIC_COMPOSITION_V1
CURRENT_TASK035_IMPLEMENTATION_SOFTWARE_VERSION=task035.shell-side-thermal-hydraulic-composition-impl-v2

CURRENT_TASK035_REQUEST_FIELDS=(schema_version,profile_id,task031_result,task032_result,task033_result,task034_result,evidence_refs)
CURRENT_TASK035_SUCCESS_FIELDS=(schema_version,profile_id,first_slice_profile_id,implementation_software_version,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task020_configuration_id,task020_configuration_hash,task021_layout_id,task021_layout_hash,task024_geometry_id,task024_geometry_hash,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,property_snapshot_hash,mass_flow_authority_hash,task033_correlation_id,task034_correlation_id,heat_transfer_surface,modeled_shell_side_heat_transfer_coefficient_w_m2_k,modeled_shell_side_pressure_drop_pa,applicability_ledger,completeness_ledger,request_hash,result_hash,result_id,warnings,blockers,deferred_capabilities,provenance)
CURRENT_TASK035_SUCCESS_PREHASH_FIELDS=(schema_version,profile_id,first_slice_profile_id,implementation_software_version,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task020_configuration_id,task020_configuration_hash,task021_layout_id,task021_layout_hash,task024_geometry_id,task024_geometry_hash,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,property_snapshot_hash,mass_flow_authority_hash,task033_correlation_id,task034_correlation_id,heat_transfer_surface,modeled_shell_side_heat_transfer_coefficient_w_m2_k,modeled_shell_side_pressure_drop_pa,applicability_ledger,completeness_ledger,request_hash,warnings,blockers,deferred_capabilities,provenance)
CURRENT_TASK035_TYPED_BLOCKED_FIELDS=(schema_version,profile_id,implementation_software_version,failure_stage,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_result_hash,task033_result_id,task034_result_hash,task034_result_id,property_snapshot_hash,mass_flow_authority_hash,request_hash,blocked_result_hash,result_id,blockers,warnings,deferred_capabilities,provenance)
CURRENT_TASK035_TYPED_BLOCKED_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,failure_stage,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_result_hash,task033_result_id,task034_result_hash,task034_result_id,property_snapshot_hash,mass_flow_authority_hash,request_hash,blockers,warnings,deferred_capabilities,provenance)
CURRENT_TASK035_RAW_BOUNDARY_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blocked_result_hash,blockers,warnings,deferred_capabilities)
CURRENT_TASK035_RAW_BOUNDARY_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blockers,warnings,deferred_capabilities)
CURRENT_TASK035_RAW_PROJECTION_FIELDS=(projection_kind,projection)
CURRENT_TASK035_PROVENANCE_FIELDS=(task_id,profile_id,first_slice_profile_id,implementation_software_version,request_hash,task031_request_hash,task031_geometry_hash,task031_geometry_id,task021_layout_hash,task021_layout_id,task024_geometry_hash,task024_geometry_id,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task033_correlation_id,task034_request_hash,task034_result_hash,task034_result_id,task034_correlation_id,task020_configuration_hash,task020_configuration_id,property_snapshot_hash,mass_flow_authority_hash,applicability_profile_id,completeness_profile_id,producer_edges,warnings,deferred_capabilities,evidence_refs,source_definition_issue,source_definition_correction_chain,provenance_hash)
CURRENT_TASK035_PROVENANCE_PREHASH_FIELDS=(task_id,profile_id,first_slice_profile_id,implementation_software_version,request_hash,task031_request_hash,task031_geometry_hash,task031_geometry_id,task021_layout_hash,task021_layout_id,task024_geometry_hash,task024_geometry_id,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task033_correlation_id,task034_request_hash,task034_result_hash,task034_result_id,task034_correlation_id,task020_configuration_hash,task020_configuration_id,property_snapshot_hash,mass_flow_authority_hash,applicability_profile_id,completeness_profile_id,producer_edges,warnings,deferred_capabilities,evidence_refs,source_definition_issue,source_definition_correction_chain)
CURRENT_TASK035_REQUEST_FIELD_COUNT=7
CURRENT_TASK035_SUCCESS_FIELD_COUNT=41
CURRENT_TASK035_SUCCESS_PREHASH_FIELD_COUNT=39
CURRENT_TASK035_TYPED_BLOCKED_FIELD_COUNT=25
CURRENT_TASK035_TYPED_BLOCKED_PREHASH_FIELD_COUNT=23
CURRENT_TASK035_RAW_BOUNDARY_FIELD_COUNT=8
CURRENT_TASK035_RAW_BOUNDARY_PREHASH_FIELD_COUNT=7
CURRENT_TASK035_PROVENANCE_FIELD_COUNT=36
CURRENT_TASK035_PROVENANCE_PREHASH_FIELD_COUNT=35

CURRENT_TASK035_REQUEST_HASH_NAMESPACE=task035.request.v2
CURRENT_TASK035_SUCCESS_RESULT_HASH_NAMESPACE=task035.success-result.v2
CURRENT_TASK035_TYPED_BLOCKED_RESULT_HASH_NAMESPACE=task035.typed-blocked-result.v2
CURRENT_TASK035_RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=task035.raw-boundary-blocked-result.v2
CURRENT_TASK035_PROVENANCE_NAMESPACE=task035.provenance.v2
CURRENT_TASK035_RAW_PROJECTION_NAMESPACE=task035.raw-projection.v2
CURRENT_TASK035_CANONICAL_ENCODING=SHA-256 over UTF-8 JSON bytes of [namespace,projection] with ensure_ascii=false,separators=(",",":"),sort_keys=true,allow_nan=false
CURRENT_TASK035_RESULT_ID_NAMESPACE=661c792e-9202-57f0-bee2-201575040d7f
CURRENT_TASK035_RESULT_ID_PREFIX=task035-shell-side-thermal-hydraulic-composition-id.v2:
CURRENT_TASK035_SUCCESS_RESULT_ID_ALGORITHM=UUIDv5(CURRENT_TASK035_RESULT_ID_NAMESPACE,CURRENT_TASK035_RESULT_ID_PREFIX + lowercase hexadecimal result_hash)
CURRENT_TASK035_TYPED_BLOCKED_RESULT_ID_ALGORITHM=UUIDv5(CURRENT_TASK035_RESULT_ID_NAMESPACE,CURRENT_TASK035_RESULT_ID_PREFIX + lowercase hexadecimal blocked_result_hash)
CURRENT_TASK035_RESULT_ID_ALGORITHM=success branch uses CURRENT_TASK035_SUCCESS_RESULT_ID_ALGORITHM; typed-blocked branch uses CURRENT_TASK035_TYPED_BLOCKED_RESULT_ID_ALGORITHM
CURRENT_TASK035_SUCCESS_RESULT_ID_PREIMAGE_FIELDS=(result_hash)
CURRENT_TASK035_TYPED_BLOCKED_RESULT_ID_PREIMAGE_FIELDS=(blocked_result_hash)
CURRENT_TASK035_RESULT_ID_PREIMAGE_FIELDS=(result_hash,blocked_result_hash)
CURRENT_TASK035_RAW_BOUNDARY_RESULT_ID_PRESENT=false
CURRENT_TASK035_HASH_CONTRACT_COUNT=6
CURRENT_TASK035_APPLICABILITY_LEDGER_FIELDS=(task031_profile,task032_profile,task033_profile,task034_profile,shared_case_identity,shared_configuration_identity,shared_geometry_identity,shared_property_identity,shared_mass_flow_identity,intersection_status)
CURRENT_TASK035_COMPLETENESS_CLASSIFICATION_UNIVERSE=(DELIVERED_AND_PRESENT,DELIVERED_BUT_BLOCKED,NOT_APPLICABLE,DEFERRED_BY_V0_3_SCOPE,OUT_OF_SCOPE)
CURRENT_TASK035_DEFERRED_CAPABILITIES=(VERSION_LEVEL_INTEGRATION_DEFERRED_TO_TASK036,DEMONSTRATION_DEFERRED_TO_TASK036,RELEASE_ACCEPTANCE_DEFERRED_TO_TASK036)
CURRENT_TASK035_WARNING_REGISTRY=(SSTHC_COMPOSITION_ONLY,SSTHC_APPLICABILITY_INTERSECTION_ONLY,SSTHC_NO_UPSTREAM_ENGINEERING_RECOMPUTATION,SSTHC_NO_FULL_EXCHANGER_RATING_CLAIM,SSTHC_TASK036_RELEASE_ACCEPTANCE_DEFERRED)
CURRENT_TASK035_BLOCKER_COUNT=42
CURRENT_TASK035_VALIDATION_STAGE_COUNT=19
CURRENT_TASK035_PUBLIC_RESULT_ENVELOPE_FIELDS=(status,success_result,blocked_result,raw_boundary_blocked_result)
CURRENT_TASK035_PRESSURE_DROP_SOURCE=accepted TASK034 v2 modeled_shell_side_pressure_drop_pa
CURRENT_TASK035_PRESSURE_DROP_FORWARDING_ONLY=true
CURRENT_TASK035_PRESSURE_DROP_RECOMPUTATION_ALLOWED=false
CURRENT_TASK035_TASK034_IDENTITY_REWRITE_ALLOWED=false
CURRENT_TASK035_REQUEST_HASH_PREIMAGE_MEMBERSHIP=(request.schema_version,request.profile_id,task031_envelope_projection(request.task031_result),task032_envelope_projection(request.task032_result),task033_envelope_projection(request.task033_result),task034_v2_envelope_projection(request.task034_result),request.evidence_refs)
CURRENT_TASK035_REQUEST_HASH_SELF_EXCLUDED_FIELDS=NONE
CURRENT_TASK035_SUCCESS_HASH_SELF_EXCLUDED_FIELDS=(result_hash,result_id)
CURRENT_TASK035_TYPED_BLOCKED_HASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash,result_id)
CURRENT_TASK035_RAW_BOUNDARY_HASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash)
CURRENT_TASK035_PROVENANCE_HASH_SELF_EXCLUDED_FIELDS=(provenance_hash)
CURRENT_TASK035_RESULT_ID_INPUT_FIELDS=(result_hash,blocked_result_hash)
CURRENT_TASK035_HASH_ALGORITHM=SHA-256
CURRENT_TASK035_CANONICAL_SEQUENCE_RULE=ordered sequence position is significant
CURRENT_TASK035_CANONICAL_UNORDERED_COLLECTION_RULE=sets and frozensets are rejected
CURRENT_TASK035_BLOCKER_CODES=(SSTHC_RAW_TYPE_INVALID,SSTHC_UNKNOWN_FIELD,SSTHC_EVIDENCE_REFS_INVALID,SSTHC_SCHEMA_VERSION_UNSUPPORTED,SSTHC_PROFILE_ID_UNSUPPORTED,SSTHC_REQUIRED_FIELD_MISSING,SSTHC_TASK031_RESULT_MISSING,SSTHC_TASK031_RESULT_INVALID,SSTHC_TASK031_RESULT_BLOCKED,SSTHC_TASK031_IDENTITY_MISMATCH,SSTHC_TASK032_RESULT_MISSING,SSTHC_TASK032_RESULT_INVALID,SSTHC_TASK032_RESULT_BLOCKED,SSTHC_TASK032_IDENTITY_MISMATCH,SSTHC_TASK033_RESULT_MISSING,SSTHC_TASK033_RESULT_INVALID,SSTHC_TASK033_RESULT_BLOCKED,SSTHC_TASK033_IDENTITY_MISMATCH,SSTHC_TASK034_RESULT_MISSING,SSTHC_TASK034_RESULT_INVALID,SSTHC_TASK034_RESULT_BLOCKED,SSTHC_TASK034_IDENTITY_MISMATCH,SSTHC_CONFIGURATION_MISMATCH,SSTHC_TASK021_LAYOUT_MISMATCH,SSTHC_TASK024_GEOMETRY_MISMATCH,SSTHC_TASK031_GEOMETRY_MISMATCH,SSTHC_PROPERTY_SNAPSHOT_MISMATCH,SSTHC_MASS_FLOW_AUTHORITY_MISMATCH,SSTHC_CASE_IDENTITY_MISMATCH,SSTHC_STREAM_IDENTITY_MISMATCH,SSTHC_FLUID_IDENTITY_MISMATCH,SSTHC_PROFILE_COMPATIBILITY_MISMATCH,SSTHC_HEAT_TRANSFER_SURFACE_MISMATCH,SSTHC_CORRELATION_IDENTITY_MISMATCH,SSTHC_APPLICABILITY_INCOMPATIBLE,SSTHC_REQUIRED_CAPABILITY_MISSING,SSTHC_REQUIRED_PRODUCER_NOT_DELIVERED,SSTHC_SUCCESS_PAYLOAD_COMPOSITION_FAILED,SSTHC_PARTIAL_SUCCESS_FORBIDDEN,SSTHC_PROVENANCE_CANONICALIZATION_FAILED,SSTHC_CANONICALIZATION_FAILED,SSTHC_RESULT_IDENTITY_FINALIZATION_FAILED)
CURRENT_TASK035_VALIDATION_STAGES=(S01_RAW_BOUNDARY,S02_REQUEST_SCHEMA,S03_TASK031_PRODUCER_BOUNDARY,S04_TASK031_IDENTITY_REPLAY,S05_TASK032_PRODUCER_BOUNDARY,S06_TASK032_IDENTITY_REPLAY,S07_TASK033_PRODUCER_BOUNDARY,S08_TASK033_IDENTITY_REPLAY,S09_TASK034_PRODUCER_BOUNDARY,S10_TASK034_IDENTITY_REPLAY,S11_CROSS_PRODUCER_CONFIGURATION_AND_GEOMETRY_JOIN,S12_PROPERTY_AND_MASS_FLOW_IDENTITY_JOIN,S13_CASE_STREAM_FLUID_JOIN,S14_PROFILE_COMPATIBILITY,S15_APPLICABILITY_INTERSECTION,S16_COMPLETENESS_LEDGER,S17_SUCCESS_PAYLOAD_COMPOSITION,S18_PROVENANCE_CANONICALIZATION,S19_RESULT_IDENTITY_FINALIZATION)
```

## 3. HISTORICAL_SUPERSEDED — Actual public runtime graph

The supported success demonstration has exactly this graph:

```text
TASK036_DEMO_INPUT
  -> TASK031_PUBLIC_PRODUCTION_OPERATION
  -> TASK032_PUBLIC_PRODUCTION_OPERATION
  -> TASK033_PUBLIC_PRODUCTION_OPERATION
  -> TASK034_PUBLIC_PRODUCTION_OPERATION
  -> TASK035_PUBLIC_VALIDATE_REQUEST
  -> TASK036_RELEASE_EVIDENCE_AGGREGATION
  -> TASK036_RELEASE_ACCEPTANCE_RESULT
```

The five producer calls are the only runtime engineering operations. The two
TASK036 tail stages consume their returned public records and release-evidence
records; they do not recompute upstream engineering quantities.

```text
ACTUAL_PRODUCTION_BINDINGS_ONLY=true
NO_STAGE_BYPASS=true
FIXTURE_ONLY_RESULT_SUBSTITUTION=false
EXPECTED_OUTPUT_USED_AS_INPUT=false
SYNTHETIC_ORACLE_SUBSTITUTION=false
MONKEYPATCHED_PRODUCER_SUCCESS=false
PRIVATE_STAGE_DIRECT_CALL_AS_END_TO_END_PROOF=false
SKIPPED_PRODUCTION_STAGE=false
PROVENANCE_SELF_EDGE=false
SELF_EDGE_COUNT=0
```

### Runtime stage contract

The runtime contains exactly 17 ordered stages. A blocked producer result
terminates the current demonstration with the actual producer blocker. The
release-evidence tail is entered only for a complete public success graph.

| Ordinal | Stage ID | Public operation / owner | Input type | Output type | Blocked variants | Identity handoff | Evidence handoff | Private bypass rule |
|---:|---|---|---|---|---|---|---|---|
| 0 | `S00_RAW_DEMO_INPUT_VALIDATION` | TASK036 input boundary | `dict[str, object]` | `Task036RawDemoInputRecord` | `ST036_DEMO_INPUT_SCHEMA_INVALID` | none | raw field paths | no producer call before closed input shape |
| 1 | `S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS` | TASK036 parser | `Task036RawDemoInputRecord` | `Task036DemoInput` | `ST036_DEMO_INPUT_CANONICALIZATION_FAILED` | demo input hash projection | normalized producer-owned records | no inferred record or field |
| 2 | `S02_BUILD_TASK031_PUBLIC_REQUEST` | TASK036 request assembly | `Task036DemoInput` | Task031 raw request record | `ST036_PUBLIC_GRAPH_INVALID` | Task031 request source record | field-01 source record | no Task031 result construction |
| 3 | `S03_EXECUTE_TASK031_PUBLIC_OPERATION` | `hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validate_request` | Task031 raw request record | `Task031ValidationResult` | actual Task031 blocked branch | Task031 request hash and geometry identity | Task031 public result | no private Task031 operation |
| 4 | `S04_BUILD_TASK032_PUBLIC_REQUEST` | TASK036 request assembly | `Task031ValidationResult` + fields 02–04 | Task032 raw request record | `ST036_PUBLIC_GRAPH_INVALID` | Task031 geometry identity | Task032 request evidence | no hand-built Task031 success |
| 5 | `S05_EXECUTE_TASK032_PUBLIC_OPERATION` | `hexagent.exchangers.shell_tube.shell_side_flow_state.validate_request` | Task032 raw request record | `Task032ValidationResult` | actual Task032 blocked branch | Task032 request/result identity | Task032 public result | no private Task032 operation |
| 6 | `S06_BUILD_TASK033_PUBLIC_REQUEST` | TASK036 request assembly | `Task032ValidationResult` + field 05 | Task033 raw request record | `ST036_PUBLIC_GRAPH_INVALID` | Task032 request/result identity | Task033 request evidence | no hand-built Task032 success |
| 7 | `S07_EXECUTE_TASK033_PUBLIC_OPERATION` | `hexagent.exchangers.shell_tube.shell_side_heat_transfer.validate_request` | Task033 raw request record | `Task033ValidationResult` | actual Task033 blocked branch | Task033 request/result identity | Task033 public result | no private Task033 operation |
| 8 | `S08_BUILD_TASK034_PUBLIC_REQUEST` | TASK036 request assembly | `Task033ValidationResult` + fields 06–08 | Task034 raw request record | `ST036_PUBLIC_GRAPH_INVALID` | Task033 request/result identity plus caller authorities | Task034 request evidence | no hand-built Task033 success |
| 9 | `S09_EXECUTE_TASK034_PUBLIC_OPERATION` | `hexagent.exchangers.shell_tube.shell_side_pressure_drop.validate_request` | Task034 raw request record | `Task034ValidationResult` | actual Task034 blocked or raw branch | Task034 request/result identity | Task034 public result | no private Task034 operation |
| 10 | `S10_BUILD_TASK035_V2_PUBLIC_REQUEST` | TASK036 request assembly | Task031–Task034 public results + field 09 | Task035 v2 raw request record | `ST036_PUBLIC_GRAPH_INVALID` | all upstream producer identities | Task035 request evidence | no Task035 payload construction from expected values |
| 11 | `S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST` | `hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.validate_request` | Task035 v2 raw request record | `Task035ValidationResult` | actual Task035 typed/raw blocked branch | Task035 request/result identity | Task035 public result | no private Task035 operation |
| 12 | `S12_VALIDATE_RELEASE_PRODUCTION_GRAPH` | TASK036 graph validator | five actual public results | `Task036ProductionGraphEvidence` | `ST036_PUBLIC_GRAPH_INVALID` | ordered producer identity chain | graph evidence | no skipped stage is accepted |
| 13 | `S13_AGGREGATE_UPSTREAM_EVIDENCE` | TASK036 evidence ledger builder | graph evidence + frozen upstream records | `Task036UpstreamEvidenceLedger` | `ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING`, `ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH` | producer refs remain producer refs | reviews, tests, CI, determinism | evidence cannot become engineering input |
| 14 | `S14_BUILD_RELEASE_ACCEPTANCE_LEDGER` | TASK036 release ledger builder | upstream evidence + artifact records | `Task036ReleaseAcceptanceLedger` | release-evidence blockers 12–16, 21–22 | ledger hash and artifact digest set | manifest, checklist, capability matrix | unavailable capability is not failure |
| 15 | `S15_DETERMINISM_EVIDENCE_VALIDATION` | TASK036 determinism validator | Python 3.11/3.12 evidence | `Task036DeterminismEvidence` | `ST036_DETERMINISM_EVIDENCE_MISSING`, `ST036_CROSS_VERSION_BYTES_MISMATCH` | canonical bytes, hashes, IDs | determinism artifact | no wall-clock or runtime-random identity |
| 16 | `S16_BUILD_TASK036_RESULT_IDENTITY` | TASK036 result finalizer | acceptance ledger + provenance | Task036 public result envelope | `ST036_RESULT_CANONICALIZATION_FAILED`, `ST036_RESULT_IDENTITY_FINALIZATION_FAILED` | Task036 request/result hash and UUIDv5 ID | final result evidence | no result identity repair |

```text
RUNTIME_STAGE_COUNT=17
VALIDATION_STAGE_COUNT=17
STAGE_ORDER_FROZEN=true
STAGE_ORDER=(S00_RAW_DEMO_INPUT_VALIDATION,S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS,S02_BUILD_TASK031_PUBLIC_REQUEST,S03_EXECUTE_TASK031_PUBLIC_OPERATION,S04_BUILD_TASK032_PUBLIC_REQUEST,S05_EXECUTE_TASK032_PUBLIC_OPERATION,S06_BUILD_TASK033_PUBLIC_REQUEST,S07_EXECUTE_TASK033_PUBLIC_OPERATION,S08_BUILD_TASK034_PUBLIC_REQUEST,S09_EXECUTE_TASK034_PUBLIC_OPERATION,S10_BUILD_TASK035_V2_PUBLIC_REQUEST,S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST,S12_VALIDATE_RELEASE_PRODUCTION_GRAPH,S13_AGGREGATE_UPSTREAM_EVIDENCE,S14_BUILD_RELEASE_ACCEPTANCE_LEDGER,S15_DETERMINISM_EVIDENCE_VALIDATION,S16_BUILD_TASK036_RESULT_IDENTITY)
PUBLIC_STAGE_EDGE_COUNT=16
PRIVATE_STAGE_EDGE_COUNT=0
SKIPPED_REQUIRED_STAGE_COUNT=0
EXPECTED_OUTPUT_AS_RUNTIME_INPUT_COUNT=0
SYNTHETIC_RESULT_SUBSTITUTION_COUNT=0
FIXTURE_ONLY_RESULT_SUBSTITUTION_COUNT=0
```

For a successful run, every stage output is the input to the next stage in the
declared order. For a blocked run, the actual public producer branch is
retained in the blocked evidence record and the success branch is structurally
unavailable.

## 4. Nine-field demo input schema

```text
DEMO_INPUT_SCHEMA_ID=task036.shell-side-thermal-hydraulic-integration-demo-input.v1
DEMO_INPUT_RAW_TYPE=dict[str, object]
DEMO_INPUT_PARSED_TYPE=Task036DemoInput
DEMO_INPUT_FIELD_COUNT=9
DEMO_INPUT_FIELD_ORDER=(TASK031_RAW_REQUEST_RECORD,TASK032_PROPERTY_SNAPSHOT_RECORD,TASK032_MASS_FLOW_AUTHORITY_RECORD,TASK032_REQUEST_EVIDENCE_REFS,TASK033_REQUEST_EVIDENCE_REFS,TASK034_SHELL_TYPE_AUTHORITY_RECORD,TASK034_WALL_PROPERTY_AUTHORITY_RECORD,TASK034_REQUEST_EVIDENCE_REFS,TASK035_EVIDENCE_REFS)
DEMO_INPUT_SCHEMA_CLOSED=true
DEMO_INPUT_RUNTIME_VALUES_CALLER_OWNED=true
DEMO_INPUT_FIELDS_REQUIRED=true
DEMO_INPUT_UNKNOWN_FIELD_IS_BLOCKER=true
DEMO_INPUT_MISSING_FIELD_IS_BLOCKER=true
DEMO_INPUT_EXPECTED_OUTPUT_FIELDS_PRESENT=false
DEMO_INPUT_EXPECTED_HASH_FIELDS_PRESENT=false
DEMO_INPUT_EXPECTED_RESULT_ID_FIELDS_PRESENT=false

TASK031_RAW_REQUEST_FIELDS=(schema_version,tube_layout,baffle_geometry_result,engineering_authority,evidence_refs)
TASK032_PROPERTY_SNAPSHOT_FIELDS=(density_kg_m3,dynamic_viscosity_pa_s,thermal_conductivity_w_m_k,specific_heat_capacity_j_kg_k,bulk_temperature_k,bulk_pressure_pa,phase_region,property_source_id,property_source_version,property_snapshot_hash)
TASK032_MASS_FLOW_AUTHORITY_FIELDS=(schema_version,authority_profile_id,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,rheology_model,task020_configuration_id,task020_configuration_hash,task031_geometry_id,task031_geometry_hash,property_snapshot_hash,property_state_role,mass_flow_rate_kg_s,mass_flow_sign_convention,authority_source_id,authority_source_version,evidence_refs,authority_hash)
TASK034_SHELL_TYPE_AUTHORITY_FIELDS=(schema_version,shell_type,task020_configuration_id,task020_configuration_hash,authority_source_id,authority_source_version,authority_record_id,evidence_refs,authority_hash)
TASK034_SHELL_TYPE_AUTHORITY_PREHASH_FIELDS=(schema_version,shell_type,task020_configuration_id,task020_configuration_hash,authority_source_id,authority_source_version,authority_record_id,evidence_refs)
TASK034_WALL_PROPERTY_AUTHORITY_FIELDS=(schema_version,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task031_geometry_id,task031_geometry_hash,task032_result_id,task032_result_hash,property_snapshot_hash,shell_side_wall_dynamic_viscosity_pa_s,source_id,source_version,evidence_refs,wall_property_snapshot_hash,wall_property_authority_hash)
TASK034_WALL_PROPERTY_AUTHORITY_PREHASH_FIELDS=(schema_version,shell_side_case_id,shell_side_stream_id,shell_side_fluid_id,task031_geometry_id,task031_geometry_hash,task032_result_id,task032_result_hash,property_snapshot_hash,shell_side_wall_dynamic_viscosity_pa_s,source_id,source_version,evidence_refs,wall_property_snapshot_hash)
TASK031_RAW_REQUEST_FIELD_COUNT=5
TASK032_PROPERTY_SNAPSHOT_FIELD_COUNT=10
TASK032_MASS_FLOW_AUTHORITY_FIELD_COUNT=18
TASK034_SHELL_TYPE_AUTHORITY_FIELD_COUNT=9
TASK034_SHELL_TYPE_AUTHORITY_PREHASH_FIELD_COUNT=8
TASK034_WALL_PROPERTY_AUTHORITY_FIELD_COUNT=15
TASK034_WALL_PROPERTY_AUTHORITY_PREHASH_FIELD_COUNT=14
```

Each field is immutable for one run. The exact record types below are closed
by the named producer field lists; `dict[str, object]` denotes the concrete
raw dictionary accepted at the producer public boundary and does not grant an
open field set.

| Index | Field name | Raw input type | Parsed type | Semantic role | Source authority | Public producer / consumer | Canonicalization rule | Semantic identity | Runtime input or evidence | Validation stage | Failure behavior | Blocker owner |
|---:|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | `TASK031_RAW_REQUEST_RECORD` | `dict[str, object]` with current Task031 request fields | `dict[str, object]` producer raw record | runtime geometry request | Task031 public request contract; `TASK-031` request schema | TASK036 S02 → Task031 S03 | producer request projection; evidence refs preserve Task031 order | true | `RUNTIME_PRODUCTION_INPUT` | S00, S01, S02 | malformed record blocks at S00/S01; producer rejection remains Task031 evidence | TASK031 |
| 2 | `TASK032_PROPERTY_SNAPSHOT_RECORD` | `dict[str, object]` with the 10 current property snapshot fields | `PropertySnapshot` | property authority consumed by Task032 | Task032 property snapshot contract and `PropertySnapshot` | TASK036 S01/S04 → Task032 S05 | producer decimal, enum, and string rules; property hash is producer-owned | true | `RUNTIME_PRODUCTION_INPUT` | S00, S01, S04 | malformed record blocks before Task032 call | TASK032 |
| 3 | `TASK032_MASS_FLOW_AUTHORITY_RECORD` | `dict[str, object]` with the 18 current mass-flow authority fields | `ShellSideMassFlowAuthority` | mass-flow authority consumed by Task032 | Task032 mass-flow authority contract | TASK036 S01/S04 → Task032 S05 | refs become producer canonical tuple sorted by Python Unicode code point | true | `RUNTIME_PRODUCTION_INPUT` | S00, S01, S04 | malformed record blocks before Task032 call | TASK032 |
| 4 | `TASK032_REQUEST_EVIDENCE_REFS` | `list[str]` | `tuple[str, ...]` | Task032 request evidence | Task032 v1 request contract | TASK036 S01/S04 → Task032 S05 | raw list required; parsed tuple is `tuple(sorted(value))` | true | `RUNTIME_AND_EVIDENCE` | S00, S01, S04 | raw tuple is rejected; empty, non-string, and duplicate item is rejected | TASK032 |
| 5 | `TASK033_REQUEST_EVIDENCE_REFS` | `list[str]` | `tuple[str, ...]` | Task033 request evidence | Task033 v1 request contract and current chain assembly | TASK036 S01/S06 → Task033 S07 | raw list required; parsed tuple is `tuple(sorted(value))` | true | `RUNTIME_AND_EVIDENCE` | S00, S01, S06 | raw tuple is rejected; empty, non-string, and duplicate item is rejected | TASK033 |
| 6 | `TASK034_SHELL_TYPE_AUTHORITY_RECORD` | `dict[str, object]` with exact nine shell-authority fields | `dict[str, object]` exact Task034 authority record | caller-owned shell type authority | Task034 caller authority contract; `task034.shell-type-authority.v2` | TASK036 S01/S08 → Task034 S09 | Task034 authority hash and refs preserve supplied sequence | true | `RUNTIME_PRODUCTION_INPUT` | S00, S01, S08 | schema/type/authority mismatch is rejected by Task034 | TASK034 |
| 7 | `TASK034_WALL_PROPERTY_AUTHORITY_RECORD` | `dict[str, object]` with exact 15 wall-authority fields | `dict[str, object]` exact Task034 wall record | caller-owned wall-property authority | Task034 caller wall-property contract; `task034.wall-property.v2` | TASK036 S01/S08 → Task034 S09 | Task034 wall authority hash receives refs in supplied sequence | true | `RUNTIME_PRODUCTION_INPUT` | S00, S01, S08 | malformed authority is rejected by Task034 | TASK034 |
| 8 | `TASK034_REQUEST_EVIDENCE_REFS` | `list[str] | tuple[str, ...]` | `tuple[str, ...]` | Task034 request evidence | Task034 v2 request contract | TASK036 S01/S08 → Task034 S09 | preserve supplied sequence; no sort and no deduplication | true | `RUNTIME_AND_EVIDENCE` | S00, S01, S08 | non-string item is rejected by Task034 parser | TASK034 |
| 9 | `TASK035_EVIDENCE_REFS` | `list[str]` | `tuple[str, ...]` | Task035 request evidence and release ledger key | Task035 v2 public request contract | TASK036 S01/S10 → Task035 S11 and S13 | preserve supplied list sequence after tuple conversion; no sort | true | `RUNTIME_AND_EVIDENCE` | S00, S01, S10 | raw tuple is rejected; exact success singleton is required | TASK035 |

The demo input field order is the runtime assembly order. Producer canonical
identity order is defined by each producer and is not inferred from mapping
insertion order.

```text
RAW_INPUT_ORDER_AND_CANONICAL_IDENTITY_ORDER_ARE_DISTINCT_CONCEPTS=true
RUNTIME_INPUT_ORDER_AND_CANONICAL_IDENTITY_ORDER_ARE_DISTINCT_CONCEPTS=true
PER_FIELD_IDENTITY_PARTICIPATION_FROZEN=true
PER_FIELD_CANONICALIZATION_RULE_FROZEN=true
```

### Evidence-reference authority

| Producer field | Raw container | Parsed container | Raw acceptance | Canonical identity order | Duplicate rule | Empty rule |
|---|---|---|---|---|---|---|
| `TASK032_REQUEST_EVIDENCE_REFS` and field-03 nested refs | `list[str]` | `tuple[str, ...]` | exact list only | `tuple(sorted(value))`, ascending by Python Unicode code point | duplicates rejected at producer admission | empty rejected |
| `TASK033_REQUEST_EVIDENCE_REFS` | `list[str]` | `tuple[str, ...]` | exact list only | `tuple(sorted(value))`, ascending by Python Unicode code point | duplicates rejected at producer admission | empty rejected |
| `TASK034_SHELL_TYPE_AUTHORITY_RECORD.evidence_refs` | `list[str] | tuple[str, ...]` | `tuple[str, ...]` | list or tuple accepted by Task034 authority validation | supplied sequence order | duplicates rejected by Task034 authority validation | empty rejected by shell-authority validation |
| `TASK034_WALL_PROPERTY_AUTHORITY_RECORD.evidence_refs` | `list[str] | tuple[str, ...]` | `tuple[str, ...]` | list or tuple accepted by Task034 `_string_refs` | supplied sequence order | producer helper does not deduplicate | empty accepted by producer helper |
| `TASK034_REQUEST_EVIDENCE_REFS` | `list[str] | tuple[str, ...]` | `tuple[str, ...]` | list or tuple accepted by Task034 `_string_refs` | supplied sequence order | producer helper does not deduplicate | empty accepted by producer helper |
| `TASK035_EVIDENCE_REFS` | `list[str]` | `tuple[str, ...]` | exact list only | supplied sequence after tuple conversion | duplicates rejected by Task035 admission | empty accepted by generic Task035 parser; not accepted by the success demo |

```text
TASK032_EVIDENCE_REFS_RAW_INPUT_TYPE=list[str]
TASK032_EVIDENCE_REFS_PARSED_INTERNAL_TYPE=tuple[str,...]
TASK032_RAW_LIST_INPUT_REQUIRED=true
TASK032_RAW_TUPLE_INPUT_ACCEPTED=false
TASK032_INTERNAL_PARSED_TUPLE_IS_NOT_RAW_INPUT_AUTHORITY=true
TASK032_RAW_EVIDENCE_REFS_ACCEPTED_CONTAINER=EXACT_LIST_ONLY
TASK032_EVIDENCE_REFS_CANONICAL_ORDER_RULE=Python sorted(value) over str values, ascending by Python Unicode code point

TASK033_EVIDENCE_REFS_RAW_INPUT_TYPE=list[str]
TASK033_EVIDENCE_REFS_PARSED_INTERNAL_TYPE=tuple[str,...]
TASK033_RAW_LIST_INPUT_REQUIRED=true
TASK033_RAW_TUPLE_INPUT_ACCEPTED=false
TASK033_EVIDENCE_REFS_CANONICAL_ORDER_RULE=tuple(sorted(value)) over str values, ascending by Python Unicode code point

TASK034_EVIDENCE_REFS_CANONICAL_ORDER_RULE=preserve supplied sequence order
TASK034_EVIDENCE_REFS_SORT=false

TASK035_EVIDENCE_REFS_RAW_INPUT_TYPE=list[str]
TASK035_EVIDENCE_REFS_PARSED_INTERNAL_TYPE=tuple[str,...]
TASK035_RAW_LIST_INPUT_REQUIRED=true
TASK035_RAW_TUPLE_INPUT_ACCEPTED=false
TASK035_EVIDENCE_REFS_CANONICAL_ORDER_RULE=preserve supplied list sequence after tuple conversion

TASK036_SUCCESS_TASK035_EVIDENCE_REFS=(task035-real-public-chain)
TASK036_SUCCESS_TASK035_EVIDENCE_REFS_RAW_INPUT=["task035-real-public-chain"]
TASK036_SUCCESS_TASK035_EVIDENCE_REFS_PARSED=("task035-real-public-chain",)
TASK036_SUCCESS_TASK035_EVIDENCE_REFS_COUNT=1
TASK036_SUCCESS_TASK035_EVIDENCE_REFS_MEMBER_1=task035-real-public-chain
EVIDENCE_REFS_CLOSED=true
EVIDENCE_REFS_DESIGN_DISCRETION=false
EVIDENCE_REFS_RUNTIME_EXTENSION_ALLOWED=false
```

## 5. Supported success demonstration

There is exactly one supported success demonstration. Its input is caller-owned
and its output is produced by the five public operations.

```text
SUPPORTED_SUCCESS_DEMO_COUNT=1
SUPPORTED_SUCCESS_DEMO_IDS=(DEMO_SUCCESS_001)
DEMO_SUCCESS_001_PURPOSE=prove the delivered TASK035 v2 public composition boundary on the actual TASK031->TASK032->TASK033->TASK034->TASK035 graph
DEMO_SUCCESS_001_INPUT_SOURCE=the exact nine-field demo input record in Section 4, with the Task031 caller record derived from tests/exchangers/shell_tube/shell_side_hydraulic_geometry/test_validation.py::base_fixture_v1 and only the controlled TRIANGULAR pattern-family choice
DEMO_SUCCESS_001_RUNTIME_GRAPH=TASK031.validate_request -> TASK032.validate_request -> TASK033.validate_request -> TASK034.validate_request -> TASK035.validate_request
DEMO_SUCCESS_001_PUBLIC_CALLS=(hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validate_request,hexagent.exchangers.shell_tube.shell_side_flow_state.validate_request,hexagent.exchangers.shell_tube.shell_side_heat_transfer.validate_request,hexagent.exchangers.shell_tube.shell_side_pressure_drop.validate_request,hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.validate_request)
DEMO_SUCCESS_001_STAGE_STATUSES=(VALID,VALID,VALID,VALID,VALID)
DEMO_SUCCESS_001_FINAL_RESULT=actual Task035 corrected v2 public success result
DEMO_SUCCESS_001_TASK034_RESULT_HASH=cd5709a86333731f32ac99f15810d00d794f3a3b0bb863043fae4af76035f9ed
DEMO_SUCCESS_001_TASK034_RESULT_ID=9f0617d9-0522-537a-beb3-3e4e78a11c99
DEMO_SUCCESS_001_TASK035_RESULT_HASH=05ae8da40b27203d1ed05de3de196f4821760e5aa2a21da7ac4c5ce138ef1fe9
DEMO_SUCCESS_001_TASK035_RESULT_ID=09bc8107-c134-5d92-bada-eff31332ef5a
DEMO_SUCCESS_001_RELEASE_STATUS=ACCEPTED
DEMO_SUCCESS_001_REPEAT_RUN_PROTOCOL=two runs on Python 3.11 and two runs on Python 3.12 using the same immutable input
DEMO_SUCCESS_001_CROSS_VERSION_CANONICAL_BYTES_EQUAL=true
DEMO_SUCCESS_001_EXPECTED_VALUES_AS_INPUT=false
DEMO_SUCCESS_001_SYNTHETIC_ORACLE=false
DEMO_SUCCESS_001_BLOCKED_AS_ZERO=false
```

Task031 identity is resynchronized by the caller-owned request construction
before the Task031 public call. No downstream expected result, hash, or ID is
used as runtime input. Task032 through Task035 receive the actual public
outputs of the preceding operation.

## 6. Closed blocked demonstration inventory

```text
BLOCKED_DEMO_COUNT=6
BLOCKED_DEMO_IDS=(DEMO_BLOCKED_B01,DEMO_BLOCKED_B02,DEMO_BLOCKED_B03,DEMO_BLOCKED_B04,DEMO_BLOCKED_B05,DEMO_BLOCKED_B06)
DEMO_INVENTORY_CLOSED=true
BLOCKED_DEMO_ACTUAL_GRAPH_REQUIRED=true
BLOCKED_DEMO_EXPECTED_OUTPUT_AS_INPUT=false
BLOCKED_DEMO_SYNTHETIC_ORACLE=false
BLOCKED_DEMO_BLOCKED_AS_ZERO=false
```

| Demo ID | Purpose | Failure owner | Injection point | Actual production stage | TASK036 graph stage | Expected blocker code | Expected field path or path set | Evidence refs rule | Final status | Expected success result | Blocked engineering value as zero |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `DEMO_BLOCKED_B01` | Task031 public schema rejection | TASK031 | Task031 raw request `schema_version` | Task031 request validation | S03 | `SSHG_SCHEMA_VERSION_UNSUPPORTED` | `schema_version` | actual ordered upstream refs; no expected output/hash/ID | `TYPED_BLOCKED` | false | false |
| `DEMO_BLOCKED_B02` | Task032 public rejection when Task031 geometry is absent | TASK032 | Task032 raw request `task031_result.geometry=None` | Task032 request validation | S05 | `SSFS_TASK031_GEOMETRY_MISSING` | `task031_result.geometry` | actual constructed-request refs; no expected result/hash/ID | `TYPED_BLOCKED` | false | false |
| `DEMO_BLOCKED_B03` | Task033 public rejection when Task032 flow state is invalid | TASK033 | Task033 raw request `task032_flow_state=[]` | Task033 request validation | S07 | `SSHT_TASK032_FLOW_STATE_INVALID` | `task032_flow_state` | actual constructed-request refs; no expected result/hash/ID | `TYPED_BLOCKED` | false | false |
| `DEMO_BLOCKED_B04` | Task034 unsupported shell-pass applicability boundary | TASK034 | Task034 request `shell_pass_count` changes from supported 1 to unsupported 2 | Task034 internal S11 validation | S09 | `SSPD_UNSUPPORTED_SHELL_PASS_COUNT` | `shell_pass_count` | update only the Task034 request identity required for public admission; do not repair Task034 result hash or ID | `TYPED_BLOCKED` | false | false |
| `DEMO_BLOCKED_B05` | Task035 rejection of a Task034 identity mismatch | TASK035 | Task034 result `task033_result_id` is changed while producer identities remain stale | Task035 internal S10 identity validation | S11 | `SSTHC_TASK034_IDENTITY_MISMATCH` | `task034_result.pressure_drop.request_hash`; `task034_result.pressure_drop.result_hash`; `task034_result.pressure_drop.result_id`; `task034_result.pressure_drop.task033_request_hash`; `task034_result.pressure_drop.task033_result_hash`; `task034_result.pressure_drop.task033_result_id`; `task034_result.pressure_drop.task032_request_hash`; `task034_result.pressure_drop.task032_result_hash`; `task034_result.pressure_drop.task032_result_id`; `task034_result.pressure_drop.task031_request_hash`; `task034_result.pressure_drop.task031_geometry_id`; `task034_result.pressure_drop.task031_geometry_hash` | retain actual refs and stale producer identities; do not rebuild Task034 or repair mutated identity | `TYPED_BLOCKED` | false | false |
| `DEMO_BLOCKED_B06` | Task035 raw-boundary rejection for a non-mapping request | TASK035 | Task035 public raw request is `[]` | Task035 raw boundary S01 | S11 | `SSTHC_RAW_TYPE_INVALID` | `raw_request` | actual invalid raw value; no expected blocked output | `RAW_BOUNDARY_BLOCKED` | false | false |

For B04, the controlled request mutation is the Task034 public-request
identity update required to let the actual public Task034 validator evaluate
the unsupported shell-pass condition. The resulting blocked Task034 payload is
never repaired. For B05, the full validated path set above is retained; a
single-path summary is not a valid representation of that demo.

## 7. TASK036 blocker architecture

TASK036 distinguishes upstream engineering blocker propagation from release
evidence blockers. Propagated codes retain the owning producer's semantic
meaning. `ST036_` codes below are owned by TASK036 and apply only to input
assembly, graph/evidence integrity, deterministic identity, or release
acceptance evidence.

```text
TASK036_BLOCKER_REGISTRY_COUNT=22
TASK036_UPSTREAM_PROPAGATION_ROW_COUNT=6
TASK036_RELEASE_EVIDENCE_BLOCKER_ROW_COUNT=16
TASK036_BLOCKER_REGISTRY_CLOSED=true
TASK036_BLOCKER_CODES=(SSHG_SCHEMA_VERSION_UNSUPPORTED,SSFS_TASK031_GEOMETRY_MISSING,SSHT_TASK032_FLOW_STATE_INVALID,SSPD_UNSUPPORTED_SHELL_PASS_COUNT,SSTHC_TASK034_IDENTITY_MISMATCH,SSTHC_RAW_TYPE_INVALID,ST036_DEMO_INPUT_SCHEMA_INVALID,ST036_DEMO_INPUT_CANONICALIZATION_FAILED,ST036_PUBLIC_GRAPH_INVALID,ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING,ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH,ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID,ST036_ARTIFACT_DIGEST_MISMATCH,ST036_MANIFEST_INCOMPLETE,ST036_VERSION_METADATA_INVALID,ST036_PROVENANCE_DAG_INVALID,ST036_DETERMINISM_EVIDENCE_MISSING,ST036_CROSS_VERSION_BYTES_MISMATCH,ST036_RESULT_CANONICALIZATION_FAILED,ST036_RESULT_IDENTITY_FINALIZATION_FAILED,ST036_RELEASE_CHECKLIST_INCOMPLETE,ST036_RELEASE_ACCEPTANCE_INCOMPLETE)
TASK036_BLOCKER_ORDERING_RULE=lowest frozen source precedence slot, then corrected stage within that slot, then registry ordinal
TASK036_BLOCKER_DEDUP_KEY=(demo_id,owner_task,blocker_code,field_path_or_path_set)
TASK036_BLOCKER_EVIDENCE_REFS_ARE_NOT_RUNTIME_ENGINEERING_VALUES=true
TASK036_BLOCKER_STAGE_BINDING_COLUMN_STATUS=HISTORICAL_SUPERSEDED_BY_SECTION_26_3
TASK036_BLOCKER_STAGE_BINDING_AUTHORITY=SECTION_26_3_CURRENT_CORRECTED_BLOCKER_STAGE_BINDINGS
```

| Ordinal | Blocker code | Owner kind | Owner task / stage | Exact field path or path set | Evidence refs rule | Dedup key contribution | Terminal result |
|---:|---|---|---|---|---|---|---|
| 1 | `SSHG_SCHEMA_VERSION_UNSUPPORTED` | upstream engineering propagation | TASK031 / S03 | `schema_version` | retain Task031 actual refs | source code + path | typed blocked |
| 2 | `SSFS_TASK031_GEOMETRY_MISSING` | upstream engineering propagation | TASK032 / S05 | `task031_result.geometry` | retain Task032 actual refs | source code + path | typed blocked |
| 3 | `SSHT_TASK032_FLOW_STATE_INVALID` | upstream engineering propagation | TASK033 / S07 | `task032_flow_state` | retain Task033 actual refs | source code + path | typed blocked |
| 4 | `SSPD_UNSUPPORTED_SHELL_PASS_COUNT` | upstream engineering propagation | TASK034 / internal S11, wrapper S09 | `shell_pass_count` | retain Task034 actual refs; no repaired result identity | source code + path | typed blocked |
| 5 | `SSTHC_TASK034_IDENTITY_MISMATCH` | upstream engineering propagation | TASK035 / internal S10, wrapper S11 | B05 exact 12-path set | retain stale Task034 refs and identities | source code + ordered path set | typed blocked |
| 6 | `SSTHC_RAW_TYPE_INVALID` | upstream engineering propagation | TASK035 / internal S01, wrapper S11 | `raw_request` | retain actual invalid raw value; no expected result | source code + path | raw-boundary blocked |
| 7 | `ST036_DEMO_INPUT_SCHEMA_INVALID` | TASK036 release evidence | TASK036 / S00 | `demo_input` | tuple of actual field paths in input order | code + path | raw-boundary blocked |
| 8 | `ST036_DEMO_INPUT_CANONICALIZATION_FAILED` | TASK036 release evidence | TASK036 / S01 | `demo_input` | actual parser evidence refs only | code + path | raw-boundary blocked |
| 9 | `ST036_PUBLIC_GRAPH_INVALID` | TASK036 release evidence | TASK036 / S02, S04, S06, S08, S10, S12 | `runtime_graph` | ordered completed-stage evidence | code + stage | typed blocked |
| 10 | `ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING` | TASK036 release evidence | TASK036 / S13 | `upstream_evidence_ledger` | refs for absent required ledger entry | code + ref key | typed blocked |
| 11 | `ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH` | TASK036 release evidence | TASK036 / S13 | `producer_identity` | refs for mismatching producer record | code + identity path | typed blocked |
| 12 | `ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID` | TASK036 release evidence | TASK036 / S14 | `release_acceptance_ledger` | ledger source refs in frozen order | code + path | typed blocked |
| 13 | `ST036_ARTIFACT_DIGEST_MISMATCH` | TASK036 release evidence | TASK036 / S14 | `artifact_digest_set` | artifact ID and path refs | code + artifact ID | typed blocked |
| 14 | `ST036_MANIFEST_INCOMPLETE` | TASK036 release evidence | TASK036 / S14 | `manifest.artifact_inventory` | manifest and missing artifact refs | code + path | typed blocked |
| 15 | `ST036_VERSION_METADATA_INVALID` | TASK036 release evidence | TASK036 / S14 | `version_metadata` | metadata and source identity refs | code + field | typed blocked |
| 16 | `ST036_PROVENANCE_DAG_INVALID` | TASK036 release evidence | TASK036 / S14 | `provenance.producer_edges` | producer node/edge refs | code + edge | typed blocked |
| 17 | `ST036_DETERMINISM_EVIDENCE_MISSING` | TASK036 release evidence | TASK036 / S15 | `determinism_evidence` | runtime and repeat-run evidence refs | code + runtime | typed blocked |
| 18 | `ST036_CROSS_VERSION_BYTES_MISMATCH` | TASK036 release evidence | TASK036 / S15 | `cross_version_canonical_bytes` | both runtime evidence refs | code + surface | typed blocked |
| 19 | `ST036_RESULT_CANONICALIZATION_FAILED` | TASK036 release evidence | TASK036 / S16 | `result_preimage` | preimage source refs | code + kind | typed blocked |
| 20 | `ST036_RESULT_IDENTITY_FINALIZATION_FAILED` | TASK036 release evidence | TASK036 / S16 | `result_hash` | result identity source refs | code + kind | typed blocked |
| 21 | `ST036_RELEASE_CHECKLIST_INCOMPLETE` | TASK036 release evidence | TASK036 / S14 | `acceptance_checklist` | checklist and unmet-item refs | code + item | typed blocked |
| 22 | `ST036_RELEASE_ACCEPTANCE_INCOMPLETE` | TASK036 release evidence | TASK036 / S16 | `release_acceptance_status` | complete ledger/checklist refs | code + status | typed blocked |

The actual producer blocker is copied into the Task036 blocked evidence branch
with its producer code, stage, field path, message key, details, and source
evidence refs. TASK036 never maps a producer engineering blocker to a numeric
engineering value. Multiple records with the same dedup key retain the first
record in stage order.

The owner, code, ordinal, field-path, and dedup semantics in this registry
remain active. The `Owner task / stage` values in the table above are the
pre-R2 stage projection only and are not current stage authority; the complete
corrected stage projection is frozen in Section 26.3.

## 8. HISTORICAL_SUPERSEDED — Release result and ledger schemas

### Public Task036 result envelope

```text
TASK036_PUBLIC_RESULT_ENVELOPE_FIELDS=(status,success_result,blocked_result,raw_boundary_blocked_result)
TASK036_PUBLIC_RESULT_ENVELOPE_FIELD_COUNT=4
VALID_ENVELOPE_RULE=status=VALID, success_result is present, blocked_result is null, raw_boundary_blocked_result is null
TYPED_BLOCKED_ENVELOPE_RULE=status=BLOCKED, success_result is null, blocked_result is present, raw_boundary_blocked_result is null
RAW_BOUNDARY_ENVELOPE_RULE=status=BLOCKED, success_result is null, blocked_result is null, raw_boundary_blocked_result is present
MUTUALLY_EXCLUSIVE_RESULT_BRANCHES=true
```

### Success result

```text
TASK036_SUCCESS_SCHEMA_ID=task036.shell-side-thermal-hydraulic-integration-demo.v1
TASK036_SUCCESS_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,release_acceptance_ledger,upstream_evidence_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance,request_hash,result_hash,result_id,warnings,blockers,deferred_capabilities)
TASK036_SUCCESS_RESULT_FIELD_COUNT=31
TASK036_SUCCESS_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,release_acceptance_ledger,upstream_evidence_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance,request_hash,warnings,blockers,deferred_capabilities)
TASK036_SUCCESS_RESULT_PREHASH_FIELD_COUNT=29
TASK036_SUCCESS_RESULT_EXCLUDED_FROM_PREHASH=(result_hash,result_id)
```

`request_hash` is the hash of the nine-field demo input. `result_hash` is the
hash of the success prehash projection. `result_id` is derived only after the
result hash is verified.

### Typed blocked result

```text
TASK036_TYPED_BLOCKED_SCHEMA_ID=task036.shell-side-thermal-hydraulic-integration-demo-blocked.v1
TASK036_TYPED_BLOCKED_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,failure_stage,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,request_hash,blocked_result_hash,result_id,blockers,warnings,deferred_capabilities,upstream_evidence,provenance)
TASK036_TYPED_BLOCKED_RESULT_FIELD_COUNT=27
TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,failure_stage,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,request_hash,blockers,warnings,deferred_capabilities,upstream_evidence,provenance)
TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELD_COUNT=25
TASK036_TYPED_BLOCKED_RESULT_EXCLUDED_FROM_PREHASH=(blocked_result_hash,result_id)
TASK036_BLOCKED_ENGINEERING_VALUE_IS_ZERO=false
```

The typed blocked branch carries the identities available before failure and a
safe ordered upstream evidence projection. It never carries a success payload.

### Raw-boundary blocked result

```text
TASK036_RAW_BOUNDARY_BLOCKED_SCHEMA_ID=task036.shell-side-thermal-hydraulic-integration-demo-raw-boundary-blocked.v1
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blocked_result_hash,blockers,warnings,deferred_capabilities)
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_FIELD_COUNT=8
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blockers,warnings,deferred_capabilities)
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELD_COUNT=7
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_EXCLUDED_FROM_PREHASH=(blocked_result_hash)
TASK036_RAW_PROJECTION_FIELDS=(projection_kind,projection)
TASK036_RAW_PROJECTION_FIELD_COUNT=2
TASK036_RAW_PROJECTION_PREHASH_FIELDS=(projection_kind,projection)
TASK036_RAW_PROJECTION_PREHASH_FIELD_COUNT=2
TASK036_RAW_PROJECTION_EXCLUDED_FROM_PREHASH=()
```

### Release acceptance ledger

```text
TASK036_RELEASE_ACCEPTANCE_LEDGER_SCHEMA_ID=task036.shell-side-thermal-hydraulic-release-acceptance-ledger.v1
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELDS=(schema_version,ledger_id,release_version,demo_id,source_commit,source_tree,required_available_capabilities,unavailable_capabilities,required_producer_statuses,required_producer_identities,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,upstream_evidence_refs,artifact_manifest_digest,determinism_evidence_digest,acceptance_checklist_digest,acceptance_status,ledger_hash)
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELD_COUNT=22
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS=(schema_version,ledger_id,release_version,demo_id,source_commit,source_tree,required_available_capabilities,unavailable_capabilities,required_producer_statuses,required_producer_identities,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,upstream_evidence_refs,artifact_manifest_digest,determinism_evidence_digest,acceptance_checklist_digest,acceptance_status)
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELD_COUNT=21
TASK036_RELEASE_ACCEPTANCE_LEDGER_EXCLUDED_FROM_PREHASH=(ledger_hash)
```

The ledger contains release-scope availability and evidence status. It does not
claim engineering correctness beyond upstream producer contracts.

### Upstream evidence ledger

```text
TASK036_UPSTREAM_EVIDENCE_LEDGER_SCHEMA_ID=task036.upstream-evidence-ledger.v1
TASK036_UPSTREAM_EVIDENCE_LEDGER_FIELDS=(schema_version,ledger_id,source_definition_issue,source_definition_revision,source_definition_freeze_comment_id,task031_producer_ref,task032_producer_ref,task033_producer_ref,task034_producer_ref,task035_pr,task035_delivery_commit,task035_merge_commit,task035_tree,task031_review_evidence,task032_review_evidence,task033_review_evidence,task034_review_evidence,task035_review_evidence,task031_test_evidence,task032_test_evidence,task033_test_evidence,task034_test_evidence,task035_test_evidence,task035_determinism_evidence,historical_task035_evidence,ledger_hash)
TASK036_UPSTREAM_EVIDENCE_LEDGER_FIELD_COUNT=26
TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS=(schema_version,ledger_id,source_definition_issue,source_definition_revision,source_definition_freeze_comment_id,task031_producer_ref,task032_producer_ref,task033_producer_ref,task034_producer_ref,task035_pr,task035_delivery_commit,task035_merge_commit,task035_tree,task031_review_evidence,task032_review_evidence,task033_review_evidence,task034_review_evidence,task035_review_evidence,task031_test_evidence,task032_test_evidence,task033_test_evidence,task034_test_evidence,task035_test_evidence,task035_determinism_evidence,historical_task035_evidence)
TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELD_COUNT=25
TASK036_UPSTREAM_EVIDENCE_LEDGER_EXCLUDED_FROM_PREHASH=(ledger_hash)
```

### Acceptance checklist

```text
TASK036_ACCEPTANCE_CHECKLIST_SCHEMA_ID=task036.acceptance-checklist.v1
TASK036_ACCEPTANCE_CHECKLIST_FIELDS=(schema_version,checklist_id,release_version,success_demo_id,required_available_capabilities,unavailable_capabilities,required_test_ids,required_artifact_paths,required_python_versions,required_repeat_runs,upstream_identity_status,release_acceptance_status,checklist_status,checklist_hash)
TASK036_ACCEPTANCE_CHECKLIST_FIELD_COUNT=14
TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELDS=(schema_version,checklist_id,release_version,success_demo_id,required_available_capabilities,unavailable_capabilities,required_test_ids,required_artifact_paths,required_python_versions,required_repeat_runs,upstream_identity_status,release_acceptance_status,checklist_status)
TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELD_COUNT=13
TASK036_ACCEPTANCE_CHECKLIST_EXCLUDED_FROM_PREHASH=(checklist_hash)
```

## 9. HISTORICAL_SUPERSEDED — Canonical identity and result-ID contract

All Task036 semantic hashes use one closed frame encoding. An ordered field
projection is encoded as a list of two-item lists, so field order is explicit.

```text
TASK036_CANONICAL_FRAME=(namespace,canonical_kind_tag,ordered_field_projection)
TASK036_CANONICAL_FIELD_PROJECTION=[[field_name,normalized_value],...]
TASK036_CANONICAL_ENCODING=json.dumps(frame,ensure_ascii=False,separators=(",",":"),sort_keys=true,allow_nan=false).encode("utf-8")
TASK036_CANONICAL_HASH_ALGORITHM=SHA-256
TASK036_CANONICAL_STRING_ENCODING=UTF-8
TASK036_CANONICAL_DECIMAL_RULE=producer-owned canonical decimal string; Task036 does not recalculate engineering decimals
TASK036_CANONICAL_TUPLE_RULE=JSON array in declared producer order
TASK036_CANONICAL_MAPPING_RULE=declared field-pair list; mapping insertion order is not identity
TASK036_CANONICAL_SET_RULE=forbidden
TASK036_CANONICAL_FLOAT_RULE=forbidden in semantic input and result projections
```

```text
TASK036_DEMO_INPUT_HASH_NAMESPACE=task036.demo-input.v1
TASK036_SUCCESS_RESULT_HASH_NAMESPACE=task036.success-result.v1
TASK036_TYPED_BLOCKED_RESULT_HASH_NAMESPACE=task036.typed-blocked-result.v1
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=task036.raw-boundary-blocked-result.v1
TASK036_RELEASE_ACCEPTANCE_LEDGER_HASH_NAMESPACE=task036.release-acceptance-ledger.v1
TASK036_UPSTREAM_EVIDENCE_LEDGER_HASH_NAMESPACE=task036.upstream-evidence-ledger.v1
TASK036_ACCEPTANCE_CHECKLIST_HASH_NAMESPACE=task036.acceptance-checklist.v1
TASK036_PROVENANCE_HASH_NAMESPACE=task036.provenance.v1
TASK036_MANIFEST_HASH_NAMESPACE=task036.manifest.v1
TASK036_VERSION_METADATA_HASH_NAMESPACE=task036.version-metadata.v1
TASK036_DETERMINISM_EVIDENCE_HASH_NAMESPACE=task036.determinism-evidence.v1
TASK036_RAW_PROJECTION_NAMESPACE=task036.raw-projection.v1
```

```text
TASK036_RESULT_ID_NAMESPACE=97db5e70-af4c-58e1-8bf0-d16005aedf12
TASK036_RESULT_ID_NAMESPACE_SOURCE=uuid.uuid5(uuid.NAMESPACE_URL,"hxforge-agent/task036/shell-side-thermal-hydraulic-integration-release-acceptance/v1")
TASK036_RESULT_ID_PREFIX=task036-shell-side-thermal-hydraulic-integration-release-acceptance-id.v1:
TASK036_RESULT_ID_ALGORITHM=uuid.uuid5(TASK036_RESULT_ID_NAMESPACE,TASK036_RESULT_ID_PREFIX + result_kind_tag + ":" + result_hash.lower())
TASK036_RESULT_ID_PREIMAGE_FIELDS=(result_kind_tag,result_hash)
TASK036_RESULT_ID_RESULT_KIND_TAGS=(TASK036_SUCCESS_RESULT,TASK036_TYPED_BLOCKED_RESULT)
TASK036_RAW_BOUNDARY_RESULT_ID_PRESENT=false
TASK036_RESULT_ID_UUID_VERSION=5
```

The six primary Task036 identity contracts are exact:

| Contract | Namespace | Kind tag | Ordered prehash fields | Self-excluded field(s) | Output |
|---|---|---|---|---|---|
| demo input hash | `task036.demo-input.v1` | `TASK036_DEMO_INPUT` | `DEMO_INPUT_FIELD_ORDER` | none | `request_hash` |
| success result hash | `task036.success-result.v1` | `TASK036_SUCCESS_RESULT` | `TASK036_SUCCESS_RESULT_PREHASH_FIELDS` | `result_hash`, `result_id` | `result_hash` |
| typed blocked result hash | `task036.typed-blocked-result.v1` | `TASK036_TYPED_BLOCKED_RESULT` | `TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELDS` | `blocked_result_hash`, `result_id` | `blocked_result_hash` |
| raw boundary blocked hash | `task036.raw-boundary-blocked-result.v1` | `TASK036_RAW_BOUNDARY_BLOCKED_RESULT` | `TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS` | `blocked_result_hash` | `blocked_result_hash` |
| release ledger hash | `task036.release-acceptance-ledger.v1` | `TASK036_RELEASE_ACCEPTANCE_LEDGER` | `TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS` | `ledger_hash` | `ledger_hash` |
| provenance hash | `task036.provenance.v1` | `TASK036_PROVENANCE` | `TASK036_PROVENANCE_PREHASH_FIELDS` | `provenance_hash` | `provenance_hash` |

The remaining release evidence hashes use the same frame algorithm, their
declared schema fields, and their declared self-exclusion:

```text
TASK036_PROVENANCE_FIELDS=(schema_version,task_id,profile_id,demo_id,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,producer_edges,release_evidence_ledger_hash,artifact_manifest_digest,acceptance_checklist_digest,source_commit,source_tree,provenance_hash)
TASK036_PROVENANCE_FIELD_COUNT=26
TASK036_PROVENANCE_PREHASH_FIELDS=(schema_version,task_id,profile_id,demo_id,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,producer_edges,release_evidence_ledger_hash,artifact_manifest_digest,acceptance_checklist_digest,source_commit,source_tree)
TASK036_PROVENANCE_PREHASH_FIELD_COUNT=25
TASK036_PROVENANCE_EXCLUDED_FROM_PREHASH=(provenance_hash)

TASK036_MANIFEST_FIELDS=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref,manifest_hash)
TASK036_MANIFEST_FIELD_COUNT=13
TASK036_MANIFEST_PREHASH_FIELDS=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref)
TASK036_MANIFEST_PREHASH_FIELD_COUNT=12
TASK036_MANIFEST_EXCLUDED_FROM_PREHASH=(manifest_hash)

TASK036_VERSION_METADATA_FIELDS=(schema_version,metadata_id,release_version,release_candidate_id,software_version,source_commit,source_tree,task031_authority_ref,task032_authority_ref,task033_authority_ref,task034_authority_ref,task035_authority_ref,manifest_digest,artifact_digest_set,release_acceptance_result_id,semantic_identity_version,metadata_hash)
TASK036_VERSION_METADATA_FIELD_COUNT=17
TASK036_VERSION_METADATA_PREHASH_FIELDS=(schema_version,metadata_id,release_version,release_candidate_id,software_version,source_commit,source_tree,task031_authority_ref,task032_authority_ref,task033_authority_ref,task034_authority_ref,task035_authority_ref,manifest_digest,artifact_digest_set,release_acceptance_result_id,semantic_identity_version)
TASK036_VERSION_METADATA_PREHASH_FIELD_COUNT=16
TASK036_VERSION_METADATA_EXCLUDED_FROM_PREHASH=(metadata_hash)
```

`TASK036_RESULT_ID_NAMESPACE` is distinct from every upstream result-ID
namespace. No timestamp, process ID, temporary path, hostname, platform
string, object representation, or random UUID enters a semantic preimage.

## 10. v0.3 release acceptance ledger

The exact accepted capability set is inherited from Issue #180 and R5.

```text
TUBE_SIDE_SINGLE_PHASE_HTC_AVAILABLE=true
TUBE_SIDE_MODELED_PRESSURE_DROP_AVAILABLE=true
SHELL_SIDE_HYDRAULIC_GEOMETRY_AVAILABLE=true
SHELL_SIDE_SINGLE_PHASE_FLOW_STATE_AVAILABLE=true
SHELL_SIDE_SINGLE_PHASE_HTC_SCREENING_AVAILABLE=true
SHELL_SIDE_MODELED_DP_SCREENING_AVAILABLE=true
SHELL_SIDE_THERMAL_HYDRAULIC_COMPOSITION_AVAILABLE=true
SHELL_SIDE_APPLICABILITY_LEDGER_AVAILABLE=true
SHELL_SIDE_COMPLETENESS_LEDGER_AVAILABLE=true

BELL_DELAWARE_AVAILABLE=false
OVERALL_U_AVAILABLE=false
UA_AVAILABLE=false
LMTD_AVAILABLE=false
HEAT_DUTY_AVAILABLE=false
OUTLET_TEMPERATURES_AVAILABLE=false
FULL_EXCHANGER_RATING_AVAILABLE=false

TASK036_REQUIRED_AVAILABLE_CAPABILITIES=(TUBE_SIDE_SINGLE_PHASE_HTC,TUBE_SIDE_MODELED_PRESSURE_DROP,SHELL_SIDE_HYDRAULIC_GEOMETRY,SHELL_SIDE_SINGLE_PHASE_FLOW_STATE,SHELL_SIDE_SINGLE_PHASE_HTC_SCREENING,SHELL_SIDE_MODELED_DP_SCREENING,SHELL_SIDE_THERMAL_HYDRAULIC_COMPOSITION,SHELL_SIDE_APPLICABILITY_LEDGER,SHELL_SIDE_COMPLETENESS_LEDGER)
TASK036_INTENTIONALLY_UNAVAILABLE_CAPABILITIES=(BELL_DELAWARE,OVERALL_U,UA,LMTD,HEAT_DUTY,OUTLET_TEMPERATURES,FULL_EXCHANGER_RATING)
TASK036_UNAVAILABLE_CAPABILITY_IS_RELEASE_FAILURE=false
TASK036_UNAVAILABLE_CAPABILITY_IS_DELIVERED=false
TASK036_ACCEPTANCE_STATUS_RULE=required available capabilities present and intentionally unavailable capabilities absent from delivered claim
```

| Capability | v0.3 status | Ledger classification | Acceptance treatment |
|---|---:|---|---|
| tube-side single-phase HTC | available | `DELIVERED_AND_PRESENT` | required |
| tube-side modeled pressure drop | available | `DELIVERED_AND_PRESENT` | required |
| shell-side hydraulic geometry | available | `DELIVERED_AND_PRESENT` | required |
| shell-side single-phase flow state | available | `DELIVERED_AND_PRESENT` | required |
| shell-side single-phase HTC screening | available | `DELIVERED_AND_PRESENT` | required |
| shell-side modeled pressure-drop screening | available | `DELIVERED_AND_PRESENT` | required |
| shell-side thermal-hydraulic composition | available | `DELIVERED_AND_PRESENT` | required |
| shell-side applicability ledger | available | `DELIVERED_AND_PRESENT` | required |
| shell-side completeness ledger | available | `DELIVERED_AND_PRESENT` | required |
| Bell-Delaware | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no failure |
| overall U | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |
| UA | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |
| LMTD | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |
| heat duty | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |
| outlet temperatures | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |
| full exchanger rating | unavailable | `DEFERRED_BY_V0_3_SCOPE` | record as unavailable; no delivery claim |

## 11. HISTORICAL_SUPERSEDED — Provenance DAG and identity handoff

```text
TASK036_PROVENANCE_NODE_SET=(TASK031,TASK032,TASK033,TASK034,TASK035,TASK036_RELEASE_EVIDENCE,TASK036_ACCEPTANCE_RESULT)
TASK036_PROVENANCE_EDGE_SET=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE,TASK036_RELEASE_EVIDENCE->TASK036_ACCEPTANCE_RESULT)
TASK036_PROVENANCE_EDGE_COUNT=6
TASK036_PROVENANCE_SELF_EDGE_COUNT=0
TASK036_PROVENANCE_HIDDEN_NODE_COUNT=0
TASK036_PROVENANCE_HISTORICAL_PR202_CURRENT_PRODUCER=false
TASK036_PROVENANCE_UPSTREAM_IDENTITY_ORDER=(TASK031,TASK032,TASK033,TASK034,TASK035)
TASK036_PROVENANCE_EDGE_ORDER=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE,TASK036_RELEASE_EVIDENCE->TASK036_ACCEPTANCE_RESULT)
```

The provenance producer edge field is an ordered list of records:

```text
TASK036_PRODUCER_EDGE_FIELDS=(producer_task,consumer_task,producer_request_hash,producer_result_hash,producer_result_id,producer_status)
TASK036_PRODUCER_EDGE_FIELD_ORDER=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE,TASK036_RELEASE_EVIDENCE->TASK036_ACCEPTANCE_RESULT)
TASK036_PRODUCER_EDGE_IDENTITY_FIELDS=(producer_request_hash,producer_result_hash,producer_result_id)
TASK036_PRODUCER_EDGE_EVIDENCE_FIELDS=(producer_task,consumer_task,producer_status)
TASK036_PROVENANCE_DAG_VALIDATION=all nodes present, all six edges present in order, no self edge, current Task035 v2 identities present
```

The current Task035 v2 producer edge uses the PR205/main authority above. The
historical Task035 review record is preserved only in the evidence ledger:

```text
HISTORICAL_TASK035_REVIEW_COMMENT_ID=5420816621
HISTORICAL_TASK035_REVIEWED_HEAD_SHA=7a3d88485474713552e6d3e6c69672ada7d3a2e2
HISTORICAL_TASK035_REVIEWED_TREE_SHA=fcbbfa93495726843ca64854f2adecfc7ca6e70d
HISTORICAL_TASK035_PR=202
HISTORICAL_TASK035_PR_HEAD=97244f3af76433e8b71bb748a79cfe4c9b1278af
HISTORICAL_TASK035_MERGE_COMMIT=cbb2aaf27411a2247e843105d22a3e272e16dfe8
CURRENT_TASK035_V2_AUTHORITY_SUPERSEDES_HISTORICAL_V1=true
HISTORICAL_EVIDENCE_PARTICIPATES_IN_CURRENT_RUNTIME_RESULT_IDENTITY=false
```

## 12. HISTORICAL_SUPERSEDED — Determinism and cross-version protocol

```text
PYTHON_3_11=true
PYTHON_3_12=true
REPEAT_RUN_DETERMINISM=true
CROSS_VERSION_BYTE_IDENTITY=true
TASK036_DETERMINISM_REPEAT_RUN_COUNT_PER_RUNTIME=2
TASK036_DETERMINISM_RUNTIME_COUNT=2
TASK036_DETERMINISM_RUNTIME_ORDER=(python3.11,python3.12)
TASK036_DETERMINISM_INPUT=the same immutable DEMO_SUCCESS_001 input bytes
TASK036_DETERMINISM_NO_WALL_CLOCK=true
TASK036_DETERMINISM_NO_RANDOM_UUID=true
TASK036_DETERMINISM_NO_PROCESS_ID=true
TASK036_DETERMINISM_NO_TEMP_PATH=true
TASK036_DETERMINISM_NO_HOSTNAME=true
TASK036_DETERMINISM_NO_UNSTABLE_PLATFORM_STRING=true
TASK036_DETERMINISM_NO_UNORDERED_SERIALIZATION=true
```

The comparison surfaces are exact:

```text
TASK036_DETERMINISM_COMPARED_CANONICAL_SURFACES=(demo_input_canonical_bytes,task035_request_canonical_bytes,task035_success_canonical_bytes,task036_provenance_canonical_bytes,release_acceptance_ledger_canonical_bytes,acceptance_checklist_canonical_bytes,manifest_canonical_bytes,version_metadata_canonical_bytes)
TASK036_DETERMINISM_COMPARED_DIGESTS=(demo_input_hash,task035_request_hash,task035_result_hash,task034_result_hash,task035_result_id,task036_provenance_hash,release_acceptance_ledger_hash,manifest_hash,version_metadata_hash)
TASK036_DETERMINISM_COMPARED_RESULT_IDS=(task034_result_id,task035_result_id,task036_result_id)
TASK036_DETERMINISM_COMPARED_ARTIFACTS=(task036_demo_input.json,task036_demo_output.json,task036_blocked_cases.json,task036_canonical_identity.json,task036_cross_python_determinism.json,task036_repeat_run_determinism.json,task036_upstream_evidence_ledger.json,task036_release_acceptance_ledger.json,task036_acceptance_checklist.json,task036_manifest.json,task036_version_metadata.json)
TASK036_DETERMINISM_COMPARISON_RULE=all listed bytes, lowercase SHA-256 values, and UUIDv5 values equal across two repeats on both runtimes
TASK036_DETERMINISM_FAILURE_BLOCKER=ST036_CROSS_VERSION_BYTES_MISMATCH
TASK036_MISSING_EVIDENCE_BLOCKER=ST036_DETERMINISM_EVIDENCE_MISSING
```

The determinism evidence artifact separates runtime metadata from semantic
identity. Its exact fields are:

```text
TASK036_DETERMINISM_EVIDENCE_SCHEMA_ID=task036.determinism-evidence.v1
TASK036_DETERMINISM_EVIDENCE_FIELDS=(schema_version,evidence_id,input_hash,runtime_versions,repeat_run_count,compared_surfaces,compared_digests,compared_result_ids,byte_identity_status,repeat_identity_status,excluded_operational_fields,evidence_hash)
TASK036_DETERMINISM_EVIDENCE_FIELD_COUNT=12
TASK036_DETERMINISM_EVIDENCE_PREHASH_FIELDS=(schema_version,evidence_id,input_hash,runtime_versions,repeat_run_count,compared_surfaces,compared_digests,compared_result_ids,byte_identity_status,repeat_identity_status,excluded_operational_fields)
TASK036_DETERMINISM_EVIDENCE_PREHASH_FIELD_COUNT=11
TASK036_DETERMINISM_EVIDENCE_EXCLUDED_FROM_PREHASH=(evidence_hash)
```

## 13. HISTORICAL_SUPERSEDED — Exact artifact architecture

No artifact bytes are created by this Design gate. Future release artifacts use
the following closed inventory and no directory scan can expand it.

```text
TASK036_ARTIFACT_ROOT=artifacts/task036/v0.3
TASK036_ARTIFACT_INVENTORY_COUNT=11
TASK036_ARTIFACT_INVENTORY_CLOSED=true
TASK036_ARTIFACT_DIGEST_ALGORITHM=SHA-256
TASK036_ARTIFACT_CANONICAL_ENCODING=the Task036 canonical frame in Section 9
TASK036_ARTIFACT_BYTES_GENERATED_NOW=false
TASK036_ARTIFACT_DIRECTORY_SCAN_IS_AUTHORITY=false
```

| Artifact ID | Exact path | Schema ID | Producer | Consumer | Semantic fields | Non-semantic operational fields | Ordering | Required status | Failure behavior | Identity participation |
|---|---|---|---|---|---|---|---|---|---|---|
| `TASK036_DEMO_INPUT` | `artifacts/task036/v0.3/task036_demo_input.json` | `task036.shell-side-thermal-hydraulic-integration-demo-input.v1` | S01 | S02 and manifest | nine fields in `DEMO_INPUT_FIELD_ORDER` | `()` | field order, then producer nested order | `REQUIRED` | missing/malformed → ST036_DEMO_INPUT_SCHEMA_INVALID | request hash input |
| `TASK036_DEMO_OUTPUT` | `artifacts/task036/v0.3/task036_demo_output.json` | `task036.shell-side-thermal-hydraulic-integration-demo.v1` | S16 | release ledger and checklist | success result fields | `()` | success result order | `REQUIRED` | digest/schema mismatch → ST036_ARTIFACT_DIGEST_MISMATCH | result evidence |
| `TASK036_BLOCKED_CASES` | `artifacts/task036/v0.3/task036_blocked_cases.json` | `task036.blocked-demo-cases.v1` | S03/S05/S07/S09/S11 | checklist and manifest | B01–B06 records, actual blockers, final statuses | `()` | B01 through B06 order | `REQUIRED` | missing case or altered code → ST036_MANIFEST_INCOMPLETE | blocked-matrix evidence |
| `TASK036_CANONICAL_IDENTITY` | `artifacts/task036/v0.3/task036_canonical_identity.json` | `task036.canonical-identity.v1` | S16 | manifest and review | namespaces, kind tags, prehash projections, hashes, IDs | `()` | contract table order | `REQUIRED` | identity mismatch → ST036_ARTIFACT_DIGEST_MISMATCH | identity evidence |
| `TASK036_CROSS_PYTHON_DETERMINISM` | `artifacts/task036/v0.3/task036_cross_python_determinism.json` | `task036.determinism-evidence.v1` | S15 | acceptance ledger | two runtime byte/digest comparisons | `runtime_executable_path` | Python 3.11 then 3.12 | `REQUIRED` | byte mismatch → ST036_CROSS_VERSION_BYTES_MISMATCH | determinism evidence |
| `TASK036_REPEAT_RUN_DETERMINISM` | `artifacts/task036/v0.3/task036_repeat_run_determinism.json` | `task036.determinism-evidence.v1` | S15 | acceptance ledger | two repeats per runtime | `runtime_executable_path` | repeat 1 then repeat 2 for each runtime | `REQUIRED` | missing repeat → ST036_DETERMINISM_EVIDENCE_MISSING | determinism evidence |
| `TASK036_UPSTREAM_EVIDENCE_LEDGER` | `artifacts/task036/v0.3/task036_upstream_evidence_ledger.json` | `task036.upstream-evidence-ledger.v1` | S13 | release ledger | review, test, CI, determinism, historical records | `()` | task and evidence category order | `REQUIRED` | missing or mismatched ref → ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING or ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH | ledger hash |
| `TASK036_RELEASE_ACCEPTANCE_LEDGER` | `artifacts/task036/v0.3/task036_release_acceptance_ledger.json` | `task036.shell-side-thermal-hydraulic-release-acceptance-ledger.v1` | S14 | S16 and manifest | capability and release acceptance fields | `()` | declared ledger order | `REQUIRED` | invalid ledger → ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID | ledger hash |
| `TASK036_ACCEPTANCE_CHECKLIST` | `artifacts/task036/v0.3/task036_acceptance_checklist.json` | `task036.acceptance-checklist.v1` | S14 | release result | required tests, artifacts, runtimes, status | `()` | test ID and artifact inventory order | `REQUIRED` | unmet item → ST036_RELEASE_CHECKLIST_INCOMPLETE | checklist hash |
| `TASK036_MANIFEST` | `artifacts/task036/v0.3/task036_manifest.json` | `task036.manifest.v1` | S14 | version metadata and release result | peer artifact refs/digests, source identity, runtime evidence | `()` | peer artifact order in Section 13 | `REQUIRED` | incomplete inventory → ST036_MANIFEST_INCOMPLETE | manifest hash |
| `TASK036_VERSION_METADATA` | `artifacts/task036/v0.3/task036_version_metadata.json` | `task036.version-metadata.v1` | S14 | release result | version, source, upstream refs, manifest, artifact digest set | `()` | metadata field order | `REQUIRED` | invalid source/version identity → ST036_VERSION_METADATA_INVALID | metadata hash |

```text
TASK036_ARTIFACT_ID_ORDER=(TASK036_DEMO_INPUT,TASK036_DEMO_OUTPUT,TASK036_BLOCKED_CASES,TASK036_CANONICAL_IDENTITY,TASK036_CROSS_PYTHON_DETERMINISM,TASK036_REPEAT_RUN_DETERMINISM,TASK036_UPSTREAM_EVIDENCE_LEDGER,TASK036_RELEASE_ACCEPTANCE_LEDGER,TASK036_ACCEPTANCE_CHECKLIST,TASK036_MANIFEST,TASK036_VERSION_METADATA)
TASK036_ARTIFACT_INVENTORY=(artifacts/task036/v0.3/task036_demo_input.json,artifacts/task036/v0.3/task036_demo_output.json,artifacts/task036/v0.3/task036_blocked_cases.json,artifacts/task036/v0.3/task036_canonical_identity.json,artifacts/task036/v0.3/task036_cross_python_determinism.json,artifacts/task036/v0.3/task036_repeat_run_determinism.json,artifacts/task036/v0.3/task036_upstream_evidence_ledger.json,artifacts/task036/v0.3/task036_release_acceptance_ledger.json,artifacts/task036/v0.3/task036_acceptance_checklist.json,artifacts/task036/v0.3/task036_manifest.json,artifacts/task036/v0.3/task036_version_metadata.json)
TASK036_MANIFEST_PEER_ARTIFACT_REFERENCE_ORDER=(TASK036_DEMO_INPUT,TASK036_DEMO_OUTPUT,TASK036_BLOCKED_CASES,TASK036_CANONICAL_IDENTITY,TASK036_CROSS_PYTHON_DETERMINISM,TASK036_REPEAT_RUN_DETERMINISM,TASK036_UPSTREAM_EVIDENCE_LEDGER,TASK036_RELEASE_ACCEPTANCE_LEDGER,TASK036_ACCEPTANCE_CHECKLIST,TASK036_VERSION_METADATA)
TASK036_MANIFEST_SELF_REFERENCE=false
TASK036_VERSION_METADATA_ARTIFACT_DIGEST_SET_ORDER=TASK036_ARTIFACT_ID_ORDER excluding TASK036_VERSION_METADATA
TASK036_EXTERNAL_UNDECLARED_ARTIFACT_COUNT=0
```

Every artifact's `semantic_fields` and `non_semantic_operational_fields` are
closed by this table. Operational metadata is kept outside semantic projections
and is not required for release identity.

## 14. HISTORICAL_SUPERSEDED — Manifest and version metadata

The manifest has no dynamic discovery authority:

```text
TASK036_MANIFEST_PATH=artifacts/task036/v0.3/task036_manifest.json
TASK036_MANIFEST_SCHEMA_ID=task036.manifest.v1
TASK036_MANIFEST_FIELD_ORDER=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref,manifest_hash)
TASK036_MANIFEST_ARTIFACT_REFERENCE_COUNT=10
TASK036_MANIFEST_ARTIFACT_REFERENCE_SET=TASK036_MANIFEST_PEER_ARTIFACT_REFERENCE_ORDER
TASK036_MANIFEST_SOURCE_COMMIT_REQUIRED=true
TASK036_MANIFEST_SOURCE_TREE_REQUIRED=true
TASK036_MANIFEST_PYTHON_VERSION_EVIDENCE_REQUIRED=true
TASK036_MANIFEST_REPEAT_RUN_EVIDENCE_REQUIRED=true
TASK036_MANIFEST_UPSTREAM_LEDGER_REFERENCE_REQUIRED=true
TASK036_MANIFEST_RELEASE_LEDGER_REFERENCE_REQUIRED=true
TASK036_MANIFEST_CHECKLIST_REFERENCE_REQUIRED=true
TASK036_MANIFEST_DYNAMIC_DIRECTORY_SCAN=false
```

Version metadata is a separate semantic record:

```text
TASK036_RELEASE_VERSION=v0.3
TASK036_RELEASE_CANDIDATE_ID=TASK036-V03-RC1
TASK036_SOFTWARE_VERSION=task036.shell-side-thermal-hydraulic-integration-release-acceptance-v1
TASK036_SEMANTIC_IDENTITY_VERSION=task036.release-identity.v1
TASK036_VERSION_METADATA_SCHEMA_ID=task036.version-metadata.v1
TASK036_SEMANTIC_VERSION_METADATA_FIELDS=(release_version,release_candidate_id,software_version,source_commit,source_tree,task031_authority_ref,task032_authority_ref,task033_authority_ref,task034_authority_ref,task035_authority_ref,manifest_digest,artifact_digest_set,release_acceptance_result_id,semantic_identity_version)
TASK036_OPERATIONAL_METADATA_FIELDS=(runtime_executable_path,ci_run_url,generated_at_utc,process_id,temp_directory_path,hostname,unstable_platform_string)
TASK036_OPERATIONAL_METADATA_IN_SEMANTIC_HASH=false
TASK036_VERSION_DERIVED_FROM_WALL_CLOCK=false
TASK036_IMPLICIT_VERSION_BUMP=false
```

## 15. Task034 and Task035 engineering boundary

TASK036 consumes upstream public records exactly as delivered. The only
engineering value used by the release result is the value already carried by
the accepted upstream public result. TASK036 does not reproduce its formula.

```text
TASK034_ENGINEERING_INPUT=actual Task034 public request record
TASK034_ENGINEERING_OUTPUT=actual Task034 public result branch
TASK035_ENGINEERING_INPUT=actual Task035 v2 public request record
TASK035_ENGINEERING_OUTPUT=actual Task035 v2 public result branch
TASK036_PRESSURE_DROP_SOURCE=Task034 public result pressure_drop.modeled_shell_side_pressure_drop_pa
TASK036_PRESSURE_DROP_FORWARDING_ONLY=true
TASK036_PRESSURE_DROP_RECOMPUTATION_ALLOWED=false
TASK036_PRESSURE_DROP_NORMALIZATION_ALLOWED=false
TASK036_PRESSURE_DROP_SUBSTITUTION_ALLOWED=false
TASK036_PRESSURE_DROP_REPAIR_ALLOWED=false
TASK036_TASK035_COMPOSITION_RECOMPUTATION_ALLOWED=false
```

Shell-type and wall-property authorities are caller-owned inputs to the Task034
public call. They are consumed for the Task034 request/result identity and are
not duplicated as new Task036 engineering fields:

```text
TASK034_SHELL_TYPE_AUTHORITY_CONSUMED_FOR_PUBLIC_REPLAY=true
TASK034_SHELL_TYPE_AUTHORITY_DIRECT_TASK036_ENGINEERING_PROPAGATION=false
TASK034_WALL_PROPERTY_AUTHORITY_CONSUMED_FOR_PUBLIC_REPLAY=true
TASK034_WALL_PROPERTY_AUTHORITY_DIRECT_TASK036_ENGINEERING_PROPAGATION=false
TASK036_SHELL_AUTHORITY_TRANSITIVE_IDENTITY=(task034_request_hash,task034_result_hash,task034_result_id,producer_edge)
TASK036_WALL_AUTHORITY_TRANSITIVE_IDENTITY=(task034_request_hash,task034_result_hash,task034_result_id,producer_edge)
TASK036_PROPERTY_SNAPSHOT_HASH_CARRIER=Task032/Task034/Task035 producer identities and release provenance
TASK036_PUBLIC_RESULT_ADDS_SHELL_AUTHORITY_FIELDS=false
TASK036_PUBLIC_RESULT_ADDS_WALL_AUTHORITY_FIELDS=false
```

Same-case and ancestry equality remains strict across the graph:

```text
TASK036_REQUIRED_ANCESTRY_JOINS=(TASK020_CONFIGURATION,TASK021_LAYOUT,TASK024_GEOMETRY,TASK031_GEOMETRY,TASK032_IDENTITY,TASK033_IDENTITY,TASK034_IDENTITY,TASK035_IDENTITY)
TASK036_ANCESTRY_JOIN_RELAXATION=false
TASK036_APPLICABILITY_EXPANSION=false
TASK036_COMPLETENESS_BYPASS=false
```

## 16. HISTORICAL_SUPERSEDED — Test inventory (ID set retained by Section 25)

The future Task036 test authority is one module with a closed 30-ID inventory:

```text
TASK036_TEST_FILE=tests/release_demo/test_task036_v03.py
TEST_INVENTORY_CLOSED=true
TEST_ID_COUNT=30
UNIQUE_TEST_ID_COUNT=30
```

| Test ID | Purpose | Stage | Input authority | Expected result / blocker |
|---|---|---|---|---|
| `T036_D01_001_TASK035_V2_PUBLIC_BINDING` | exact current Task035 package, operation, and v2 profile | S11 | current main Task035 public package | pass |
| `T036_D09_001_SUCCESS_PUBLIC_GRAPH` | supported success graph | S03–S11 | DEMO_SUCCESS_001 | VALID |
| `T036_D10_B01_TASK031_SCHEMA_BLOCKED` | Task031 schema blocked demo | S03 | DEMO_BLOCKED_B01 | `SSHG_SCHEMA_VERSION_UNSUPPORTED` |
| `T036_D10_B02_TASK032_GEOMETRY_BLOCKED` | Task032 geometry missing demo | S05 | DEMO_BLOCKED_B02 | `SSFS_TASK031_GEOMETRY_MISSING` |
| `T036_D10_B03_TASK033_FLOW_BLOCKED` | Task033 flow invalid demo | S07 | DEMO_BLOCKED_B03 | `SSHT_TASK032_FLOW_STATE_INVALID` |
| `T036_D10_B04_TASK034_SHELL_PASS_BLOCKED` | Task034 shell-pass boundary | S09 | DEMO_BLOCKED_B04 | `SSPD_UNSUPPORTED_SHELL_PASS_COUNT` |
| `T036_D10_B05_TASK034_IDENTITY_BLOCKED` | Task034 identity mismatch through Task035 | S11 | DEMO_BLOCKED_B05 | `SSTHC_TASK034_IDENTITY_MISMATCH` |
| `T036_D10_B06_TASK035_RAW_BOUNDARY_BLOCKED` | Task035 raw boundary | S11 | DEMO_BLOCKED_B06 | `SSTHC_RAW_TYPE_INVALID` |
| `T036_D20_001_DEMO_INPUT_SCHEMA_EXACT` | nine-field membership and order | S00–S01 | Section 4 | pass |
| `T036_D20_002_TASK032_RAW_LIST_ONLY` | Task032 raw list/parsed tuple | S01/S04 | field 04 | tuple raw rejected |
| `T036_D20_003_TASK033_RAW_LIST_ONLY` | Task033 raw list/parsed tuple | S01/S06 | field 05 | tuple raw rejected |
| `T036_D20_004_TASK034_SEQUENCE_PRESERVED` | Task034 supplied ref order | S01/S08 | fields 06–08 | order preserved |
| `T036_D20_005_TASK035_SUCCESS_REFS_CLOSED` | Task035 singleton refs | S01/S10 | field 09 | exact singleton |
| `T036_D14_001_PUBLIC_GRAPH_NO_BYPASS` | no skipped or private stage | S02–S12 | DEMO_SUCCESS_001 trace | pass |
| `T036_D15_001_NO_UPSTREAM_RECOMPUTATION` | no upstream engineering recomputation | S12 | runtime trace | pass |
| `T036_D16_001_NO_FIXTURE_RESULT_SUBSTITUTION` | fixture is input only | S02–S12 | runtime trace | pass |
| `T036_D17_001_EXPECTED_OUTPUT_NOT_INPUT` | expected output exclusion | S00–S02 | raw input projection | pass |
| `T036_D18_001_NO_SYNTHETIC_ORACLE` | no synthetic result substitution | S02–S12 | runtime trace | pass |
| `T036_D19_001_PROVENANCE_NO_SELF_EDGE` | DAG edge and self-edge proof | S13–S16 | provenance record | self edge count 0 |
| `T036_D01_002_TASK035_WRONG_VERSION_REJECTED` | wrong Task035 version fails closed | S10–S11 | mutated Task035 request | blocked |
| `T036_D11_001_BLOCKED_NOT_ZERO` | blocked quantity is not zero | S03–S11 | B01–B06 | pass |
| `T036_D07_001_RESULT_BRANCH_EXCLUSIVITY` | result envelope branch exclusivity | S16 | all branches | pass |
| `T036_D28_001_REPEAT_RUN_DETERMINISM` | two repeats per runtime | S15 | DEMO_SUCCESS_001 | pass |
| `T036_D29_001_PYTHON_311_EXECUTION` | Python 3.11 execution | S15 | DEMO_SUCCESS_001 | pass |
| `T036_D30_001_PYTHON_312_EXECUTION` | Python 3.12 execution | S15 | DEMO_SUCCESS_001 | pass |
| `T036_D31_001_CROSS_VERSION_BYTE_IDENTITY` | cross-version byte identity | S15 | determinism artifact | pass |
| `T036_D23_001_MANIFEST_COMPLETE` | closed manifest inventory | S14 | manifest artifact | pass |
| `T036_D24_001_ARTIFACT_DIGEST_VALIDATION` | all artifact digests | S14 | artifact inventory | pass |
| `T036_D26_001_VERSION_METADATA_IDENTITY` | version metadata and source identity | S14 | metadata artifact | pass |
| `T036_D34_001_RELEASE_CHECKLIST` | v0.3 acceptance checklist | S14–S16 | checklist artifact | pass |

```text
TASK036_TEST_ID_ORDER=(T036_D01_001_TASK035_V2_PUBLIC_BINDING,T036_D09_001_SUCCESS_PUBLIC_GRAPH,T036_D10_B01_TASK031_SCHEMA_BLOCKED,T036_D10_B02_TASK032_GEOMETRY_BLOCKED,T036_D10_B03_TASK033_FLOW_BLOCKED,T036_D10_B04_TASK034_SHELL_PASS_BLOCKED,T036_D10_B05_TASK034_IDENTITY_BLOCKED,T036_D10_B06_TASK035_RAW_BOUNDARY_BLOCKED,T036_D20_001_DEMO_INPUT_SCHEMA_EXACT,T036_D20_002_TASK032_RAW_LIST_ONLY,T036_D20_003_TASK033_RAW_LIST_ONLY,T036_D20_004_TASK034_SEQUENCE_PRESERVED,T036_D20_005_TASK035_SUCCESS_REFS_CLOSED,T036_D14_001_PUBLIC_GRAPH_NO_BYPASS,T036_D15_001_NO_UPSTREAM_RECOMPUTATION,T036_D16_001_NO_FIXTURE_RESULT_SUBSTITUTION,T036_D17_001_EXPECTED_OUTPUT_NOT_INPUT,T036_D18_001_NO_SYNTHETIC_ORACLE,T036_D19_001_PROVENANCE_NO_SELF_EDGE,T036_D01_002_TASK035_WRONG_VERSION_REJECTED,T036_D11_001_BLOCKED_NOT_ZERO,T036_D07_001_RESULT_BRANCH_EXCLUSIVITY,T036_D28_001_REPEAT_RUN_DETERMINISM,T036_D29_001_PYTHON_311_EXECUTION,T036_D30_001_PYTHON_312_EXECUTION,T036_D31_001_CROSS_VERSION_BYTE_IDENTITY,T036_D23_001_MANIFEST_COMPLETE,T036_D24_001_ARTIFACT_DIGEST_VALIDATION,T036_D26_001_VERSION_METADATA_IDENTITY,T036_D34_001_RELEASE_CHECKLIST)
TASK036_TEST_ID_DUPLICATE_COUNT=0
TASK036_TEST_ID_UNMAPPED_COUNT=0
```

## 17. HISTORICAL_SUPERSEDED — CI boundary before R3 D32 correction

The current repository CI manifest is retained unchanged by this authoring
gate. Future Task036 implementation registers the single test module in the
existing `ci` shard for both required Python versions.

```text
CURRENT_CI_MANIFEST=ci-shard-manifest.yml
CURRENT_CI_MANIFEST_VERSION=1
CURRENT_CI_SHARD=ci
CURRENT_CI_JOB=shard-ci
CURRENT_CI_PYTHON_MATRIX=(3.11,3.12)
TASK036_FUTURE_CI_TEST_PATH=tests/release_demo/test_task036_v03.py
TASK036_FUTURE_CI_SHARD=ci
TASK036_FUTURE_CI_JOB=shard-ci
TASK036_FUTURE_CI_PYTHON_MATRIX=(3.11,3.12)
TASK036_CI_MANIFEST_MUTATION_REQUIRED=true
TASK036_CI_MANIFEST_MUTATION_FORM=one explicit file-list entry for tests/release_demo/test_task036_v03.py in the existing ci shard
TASK036_CI_NEW_WORKFLOW_REQUIRED=false
TASK036_CI_NEW_SHARD_REQUIRED=false
TASK036_CI_ARTIFACT_COMPARISON_JOB=the existing ci shard test module
TASK036_CI_DIRECTORY_SCAN_AUTHORITY=false
```

## 18. HISTORICAL_SUPERSEDED — Future implementation mutation allowlist before R3 correction

The future implementation scope is exact and closed. The authoring gate does
not create any of these files.

```text
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST_COUNT=8
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST=(src/hexagent/release_demo/__init__.py,src/hexagent/release_demo/task036.py,src/hexagent/release_demo/schema.py,src/hexagent/release_demo/canonical.py,src/hexagent/release_demo/models.py,src/hexagent/release_demo/validation.py,src/hexagent/release_demo/provenance.py,src/hexagent/release_demo/artifacts.py)

IMPLEMENTATION_TEST_FILE_ALLOWLIST_COUNT=1
IMPLEMENTATION_TEST_FILE_ALLOWLIST=(tests/release_demo/test_task036_v03.py)

IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST_COUNT=11
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST=(artifacts/task036/v0.3/task036_demo_input.json,artifacts/task036/v0.3/task036_demo_output.json,artifacts/task036/v0.3/task036_blocked_cases.json,artifacts/task036/v0.3/task036_canonical_identity.json,artifacts/task036/v0.3/task036_cross_python_determinism.json,artifacts/task036/v0.3/task036_repeat_run_determinism.json,artifacts/task036/v0.3/task036_upstream_evidence_ledger.json,artifacts/task036/v0.3/task036_release_acceptance_ledger.json,artifacts/task036/v0.3/task036_acceptance_checklist.json,artifacts/task036/v0.3/task036_manifest.json,artifacts/task036/v0.3/task036_version_metadata.json)

IMPLEMENTATION_CI_MANIFEST_ALLOWLIST_COUNT=1
IMPLEMENTATION_CI_MANIFEST_ALLOWLIST=(ci-shard-manifest.yml)

OTHER_ALLOWED_FILES=NONE
FORBIDDEN_FILE_PATTERNS=(TASK031,TASK032,TASK033,TASK034,TASK035,TASK037,TASK038,TASK039,blocker_registry.py,warning_registry.py,.github/workflows,release_spec.yaml,pyproject.toml,uv.lock)
```

The production package owns only Task036 release integration. Existing
TASK031–TASK035 modules, their tests, blocker registries, warning registries,
and workflow definitions are expected to remain byte-identical during future
implementation. A future implementation that requires a path outside these
allowlists blocks without scope expansion.

## 19. No hidden implementation discretion

```text
IMPLEMENTATION_MAY_NOT_CHOOSE_SCHEMA=true
IMPLEMENTATION_MAY_NOT_CHOOSE_BLOCKER_CODES=true
IMPLEMENTATION_MAY_NOT_CHOOSE_STAGE_ORDER=true
IMPLEMENTATION_MAY_NOT_CHOOSE_TEST_INVENTORY=true
IMPLEMENTATION_MAY_NOT_CHOOSE_ARTIFACT_PATHS=true
IMPLEMENTATION_MAY_NOT_CHOOSE_CANONICALIZATION=true
IMPLEMENTATION_MAY_NOT_CHOOSE_RUNTIME_ENTRY=true
IMPLEMENTATION_MAY_NOT_CHOOSE_DEMO_INVENTORY=true
IMPLEMENTATION_MAY_NOT_BROADEN_SCOPE=true
IMPLEMENTATION_MAY_NOT_CHOOSE_RESULT_ID_NAMESPACE=true
IMPLEMENTATION_MAY_NOT_CHOOSE_RESULT_ID_PREIMAGE=true
IMPLEMENTATION_MAY_NOT_CHOOSE_RELEASE_CAPABILITY_SET=true
```

## 20. Source Decision D01–D35 mapping

The following table is the complete one-to-one design mapping. Each frozen
source decision appears once in this authority table; the referenced sections
contain its direct implementation projection. For D23, D25, D26, and D32, the
effective current projection is Section 27. Sections 25.1-25.6 remain the
preserved architecture referenced by that overlay; superseded values in
Sections 25.7-25.11 are historical only.

| Source decision | Design section | Closed design authority |
|---|---:|---|
| D01 exact delivered Task035 public contract | 2 | current PR205/main v2 package, operation, schemas, profile |
| D02 Task036 runtime production graph | 25.1, 25.2 | exact 20-node graph and 23-stage graph |
| D03 Task035 runtime entry binding | 2, 25.2 | public `validate_request` only |
| D04 Task031–Task034 evidence-only bindings | 25.2, 25.6 | public producer stages plus evidence ledger separation |
| D05 upstream review evidence ledger | 2, 25.6, 25.10 | current/historical evidence fields and source refs |
| D06 upstream CI and test evidence ledger | 2, 25.6, 27.1, 27.4, 27.5 | current run records, frozen artifact/test records, CI boundary |
| D07 release acceptance result boundary | 25.3, 26.1, 27.6 | separate internal UUID identity from frozen ledger SHA-256 identity |
| D08 release acceptance is not engineering correctness proof | 1, 15 | no recomputation and authority separation |
| D09 exact supported success demo inventory | 5 | DEMO_SUCCESS_001 only |
| D10 exact blocked demo inventory | 6 | DEMO_BLOCKED_B01 through B06 |
| D11 blocked propagation semantics | 6, 7, 25.2, 25.3 | actual producer blockers, typed/raw branches, no zero |
| D12 release-level blocker registry | 7, 26.3 | 22 closed rows and corrected stage/dedup/order rule |
| D13 validation stage order | 25.2, 26.2 | S00–S22 exact corrected order plus frozen failure precedence |
| D14 no-stage-bypass proof | 25.5, 27.4 | edge counts and public graph test |
| D15 no upstream engineering recomputation proof | 1, 15, 25.5, 27.4, 27.6 | forwarding and trace assertions |
| D16 no fixture-only result substitution proof | 25.2, 27.4 | fixture input-only rule |
| D17 no expected output as input proof | 4, 5, 27.4 | forbidden semantic fields and test |
| D18 no synthetic oracle substitution proof | 25.2, 5, 27.4 | public-output-only rule and test |
| D19 provenance DAG and self-edge rule | 25.6 | seven nodes, six edges, zero self edges |
| D20 demo input schema | 4 | nine fields, exact raw/parsed types |
| D21 demo output schema | 25.3, 25.10 | success/blocked/raw exact fields |
| D22 release acceptance ledger schema | 25.3, 25.10 | exact 22-field ledger |
| D23 artifact inventory | 27.1 | exact frozen six artifact paths and roles |
| D24 artifact schema and digest contract | 27.1 | schema, producer, consumer, fields, SHA-256 |
| D25 manifest schema and path | 27.2 | exact frozen three manifest peers and no scan |
| D26 version metadata contract | 27.3 | exact 0.3.0 version and controlled version-bearing files |
| D27 release result hash/ID identity graph | 25.1, 25.3, 25.4, 25.5, 27.6 | hash frames, UUIDv5, provenance edges |
| D28 repeat-run determinism protocol | 27.6 | two runs per runtime and source-compatible comparison surfaces |
| D29 Python 3.11 execution protocol | 27.6 | required matrix entry and evidence |
| D30 Python 3.12 execution protocol | 27.6 | required matrix entry and evidence |
| D31 cross-version byte identity protocol | 27.6 | exact frozen JSON/Markdown and final identity comparison |
| D32 test-ID inventory | 27.4 | exact 22-ID list and frozen test file |
| D33 CI manifest boundary | 27.4 | existing ci shard and frozen D32 test path |
| D34 v0.3 acceptance checklist | 10, 27.2, 27.4 | capability matrix, checklist evidence, frozen test |
| D35 tag/release forward lifecycle boundary | 30; historical 22, 27.8, 29.6, 29.7 | Section 30 is the sole current R5 lifecycle authority with one R5 independent-review next gate; NO_STEP_IMPLIES_THE_NEXT=true; accept/freeze, implementation, branch, commit, push, PR, merge, CI, release evidence acceptance, tag, GitHub Release, Issue close, and TASK037+ remain separately unauthorized |

```text
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_DECISION_MAPPING_DUPLICATE_COUNT=0
```

## 21. HISTORICAL_SUPERSEDED — Consistency tables

### A. Source decision mapping

Table A is Section 20. Its ordered decision set is:

```text
SOURCE_DECISION_ORDER=(D01,D02,D03,D04,D05,D06,D07,D08,D09,D10,D11,D12,D13,D14,D15,D16,D17,D18,D19,D20,D21,D22,D23,D24,D25,D26,D27,D28,D29,D30,D31,D32,D33,D34,D35)
```

### B. Runtime stages

Table B is the Section 3 stage table. Its exact order is `S00` through `S16`
with `PUBLIC_STAGE_EDGE_COUNT=16` and `PRIVATE_STAGE_EDGE_COUNT=0`.

### C. Schema and field-count table

| Schema | Final count | Prehash count | Exclusion |
|---|---:|---:|---|
| demo input | 9 | 9 | none |
| Task036 success result | 31 | 29 | `result_hash`, `result_id` |
| Task036 typed blocked result | 27 | 25 | `blocked_result_hash`, `result_id` |
| Task036 raw-boundary blocked result | 8 | 7 | `blocked_result_hash` |
| release acceptance ledger | 22 | 21 | `ledger_hash` |
| upstream evidence ledger | 26 | 25 | `ledger_hash` |
| acceptance checklist | 14 | 13 | `checklist_hash` |
| provenance | 26 | 25 | `provenance_hash` |
| manifest | 13 | 12 | `manifest_hash` |
| version metadata | 17 | 16 | `metadata_hash` |
| determinism evidence | 12 | 11 | `evidence_hash` |
| raw projection | 2 | 2 | none |

### D. Blocker ownership

Table D is the Section 7 22-row registry. Rows 1–6 are upstream engineering
propagation; rows 7–22 are TASK036 release-evidence ownership.

### E. Demo inventory

Table E is Sections 5 and 6: one supported success demo and six blocked demos.

### F. Evidence refs

Table F is the Section 4 evidence-reference table. Raw and parsed types are
distinct, and producer-specific canonical order is preserved.

### G. Artifact inventory

Table G is the Section 13 11-row artifact inventory. Paths are exact and
manifest membership is closed.

### H. Test inventory

Table H is Section 16. It has exactly 30 unique IDs and one future test path.

### I. Implementation file allowlist

| File class | Count | Exact authority |
|---|---:|---|
| production | 8 | `IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST` |
| tests | 1 | `IMPLEMENTATION_TEST_FILE_ALLOWLIST` |
| artifacts | 11 | `IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST` |
| CI manifest | 1 | `IMPLEMENTATION_CI_MANIFEST_ALLOWLIST` |
| other | 0 | `OTHER_ALLOWED_FILES=NONE` |

### J. Deterministic identity graph

```text
DEMO_INPUT_HASH -> TASK035_REQUEST_HASH -> TASK035_RESULT_HASH -> TASK035_RESULT_ID
TASK034_RESULT_HASH -> TASK034_RESULT_ID
TASK036_PROVENANCE_HASH -> RELEASE_ACCEPTANCE_LEDGER_HASH -> MANIFEST_HASH -> VERSION_METADATA_HASH
TASK036_SUCCESS_RESULT_HASH -> TASK036_RESULT_ID
```

Every arrow is a declared producer identity or declared Task036 release
evidence identity. No arrow represents an engineering recomputation.

### K. Provenance graph

Table K is Section 11's exact seven-node, six-edge DAG. `SELF_EDGE_COUNT=0`.

### L. v0.3 capability table

Table L is Section 10. Nine capabilities are required and present; seven are
intentionally unavailable and are recorded without a release failure.

## 22. HISTORICAL_SUPERSEDED — Forward lifecycle boundary before R2

Source-definition freeze and Design authoring do not authorize any repository or
release operation.

```text
TASK036_DESIGN_AUTHORIZED=true
TASK036_DESIGN_AUTHORIZING_GATE=AUTHORIZE_TASK036_DESIGN_AUTHORING_ONLY
TASK036_DESIGN_AUTHORED=true
TASK036_DESIGN_REVIEWED=false
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_REPOSITORY_MUTATION_AUTHORIZED=false
TASK036_BRANCH_AUTHORIZED=false
TASK036_COMMIT_AUTHORIZED=false
TASK036_PUSH_AUTHORIZED=false
TASK036_PULL_REQUEST_AUTHORIZED=false
TASK036_READY_AUTHORIZED=false
TASK036_MERGE_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
TASK036_ISSUE_CLOSE_AUTHORIZED=false
TASK037_AUTHORIZED=false
TASK038_AUTHORIZED=false
TASK039_AUTHORIZED=false
```

The following block is a historical mapping snapshot. The effective current
next gate is maintained by Section 27 and does not freeze this Design or
authorize implementation:

```text
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R3_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 26. HISTORICAL_SUPERSEDED — R2 correction overlay — prior authority for N1-N4

Section 26 records the prior R2 correction overlay. It closes exactly the four
N1-N4 findings raised by the independent R1-correction rereview and preserves
all previously accepted source, contract, topology, and identity authority.
Its old artifact, test, version, allowlist, and next-gate declarations are
superseded by Section 27. Sections 22, 25.12, and 25.13 remain historical
traceability and are not active lifecycle authority.

```text
TASK036_R2_CORRECTION_AUTHORITY_STATUS=HISTORICAL_SUPERSEDED
TASK036_R2_CORRECTION_SCOPE=(N1,N2,N3,N4)
TASK036_R2_CORRECTION_SCOPE_ONLY=true
TASK036_R2_NON_FINDING_AUTHORITY_REOPENED=false
TASK036_R2_NON_FINDING_AUTHORITY_CHANGED=false
TASK036_R2_IMPLEMENTATION_AUTHORIZED=false
TASK036_R2_ARTIFACT_BYTES_GENERATED_NOW=false
TASK036_R2_TEST_EXECUTION_PERFORMED_IN_DESIGN_GATE=false
```

### 26.1 Distinct release-acceptance identity and internal result identity

The internal deterministic Task036 result identity and the frozen release
acceptance identity are separate contracts. A generic `result_id` reference in
the Task036 result, typed-blocked result, raw-boundary result, identity-core,
or final-result graph means the internal Task036 result identity unless the
field is explicitly named `release_acceptance_result_id`.

```text
TASK036_INTERNAL_RESULT_ID_NAME=TASK036_INTERNAL_RESULT_ID
TASK036_INTERNAL_RESULT_ID_MEANING=internal deterministic Task036 result object identity
TASK036_INTERNAL_RESULT_ID_PRESENT=true
TASK036_INTERNAL_RESULT_ID_ALGORITHM=UUIDv5
TASK036_INTERNAL_RESULT_ID_NAMESPACE=97db5e70-af4c-58e1-8bf0-d16005aedf12
TASK036_INTERNAL_RESULT_ID_UUID_VERSION=5
TASK036_INTERNAL_RESULT_ID_PREIMAGE_FIELDS=(result_kind_tag,result_hash)
TASK036_INTERNAL_RESULT_ID_REFERENCE_DEFAULT=TASK036_INTERNAL_RESULT_ID

RELEASE_ACCEPTANCE_RESULT_ID_NAME=RELEASE_ACCEPTANCE_RESULT_ID
RELEASE_ACCEPTANCE_RESULT_ID_MEANING=frozen release acceptance identity
RELEASE_ACCEPTANCE_RESULT_ID_PRESENT=true
RELEASE_ACCEPTANCE_RESULT_ID_ALGORITHM=SHA-256
RELEASE_ACCEPTANCE_RESULT_ID_SOURCE=CANONICAL_RELEASE_ACCEPTANCE_LEDGER_SHA256
RELEASE_ACCEPTANCE_RESULT_ID_CANONICAL_BYTES=TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_CANONICAL_BYTES
RELEASE_ACCEPTANCE_RESULT_ID_FORMAT="sha256:" + SHA256(RELEASE_ACCEPTANCE_RESULT_ID_CANONICAL_BYTES)
RELEASE_ACCEPTANCE_RESULT_ID_UUID_VERSION=NONE
RELEASE_ACCEPTANCE_RESULT_ID_UUID_NAMESPACE=NONE

TASK036_RELEASE_ACCEPTANCE_LEDGER_CANONICAL_NAMESPACE=task036.release-acceptance-ledger.v1
TASK036_RELEASE_ACCEPTANCE_LEDGER_CANONICAL_KIND_TAG=TASK036_RELEASE_ACCEPTANCE_LEDGER
TASK036_RELEASE_ACCEPTANCE_LEDGER_CANONICAL_ENCODING=canonical normalized semantic ledger encoding
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_CANONICAL_BYTES=CANONICAL_ENCODING(namespace=task036.release-acceptance-ledger.v1,canonical_kind_tag=TASK036_RELEASE_ACCEPTANCE_LEDGER,ordered_field_projection=TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS)
TASK036_RELEASE_ACCEPTANCE_LEDGER_SHA256=SHA256(TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_CANONICAL_BYTES)
TASK036_RELEASE_ACCEPTANCE_RESULT_ID="sha256:" + TASK036_RELEASE_ACCEPTANCE_LEDGER_SHA256
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_PREHASH_EXCLUDES=(ledger_hash)
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_RUNTIME_TIMESTAMPS_INCLUDED=false
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_MACHINE_LOCAL_METADATA_INCLUDED=false
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_CONTRACT_MATCHES_FROZEN_SOURCE=true

TASK036_INTERNAL_RESULT_ID_IS_RELEASE_ACCEPTANCE_RESULT_ID=false
TASK036_INTERNAL_RESULT_ID_AND_RELEASE_ACCEPTANCE_RESULT_ID_DISTINCT=true
TASK036_INTERNAL_RESULT_ID_REFERENCE_FIELDS=(N11.result_id,N19.result_id,TASK036_SUCCESS_RESULT.result_id,TASK036_TYPED_BLOCKED_RESULT.result_id,TASK036_RAW_BOUNDARY_BLOCKED_RESULT.result_id)
TASK036_INTERNAL_RESULT_ID_REFERENCE_COUNT=5
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_REFERENCE_FIELDS=(N16.ledger_hash,TASK036_VERSION_METADATA.release_acceptance_result_id,RELEASE_ACCEPTANCE_RESULT_ID)
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_REFERENCE_COUNT=3
TASK036_GENERIC_RESULT_ID_REFERENCE_DEFAULT=TASK036_INTERNAL_RESULT_ID
TASK036_AMBIGUOUS_RESULT_ID_REFERENCE_COUNT=0
TASK036_CROSS_IDENTITY_ALIAS_COUNT=0
TASK036_IDENTITY_FIELD_CLASSIFICATION_COMPLETE=true
TASK036_SCHEMA_PREHASH_IDENTITY_CLASSIFICATION_COMPLETE=true
TASK036_MANIFEST_IDENTITY_CLASSIFICATION_COMPLETE=true
TASK036_PROVENANCE_IDENTITY_CLASSIFICATION_COMPLETE=true
TASK036_ARTIFACT_IDENTITY_CLASSIFICATION_COMPLETE=true
TASK036_TEST_AUTHORITY_IDENTITY_CLASSIFICATION_COMPLETE=true
TASK036_RELEASE_ACCEPTANCE_RESULT_ID_PREHASH_CYCLE_COUNT=0
TASK036_INTERNAL_RESULT_ID_PREHASH_CYCLE_COUNT=0
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_SOURCE=N16.ledger_hash
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_FORMAT="sha256:" + N16.ledger_hash
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_PARTICIPATION=VERSION_METADATA_PREHASH
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_IS_POST_RESULT=false
```

Accordingly, the version-metadata field `release_acceptance_result_id` is the
frozen SHA-256 ledger identity with the literal `sha256:` prefix. It is not the
UUIDv5 value in `N11.result_id`, and it is not an alias for the final internal
Task036 `result_id`.

### 26.2 Frozen source failure precedence projected onto corrected runtime stages

The corrected 23-stage runtime decomposition is mechanical only. It does not
replace the frozen ten-slot release-failure precedence from the Source
Definition. Failure selection first compares the frozen source slot, then the
corrected runtime stage within that slot, then the frozen blocker registry
ordinal. A later slot or later stage cannot mask an earlier failure, and a
release with any required failure cannot be reported as partial success.

```text
TASK036_FAILURE_PRECEDENCE_PROJECTION_SOURCE=ISSUE203_R1_CORRECTION_COMMENT_5422487145
TASK036_RELEASE_FAILURE_STAGE_ORDER=(S01_PRODUCTION_REPLAY,S02_INHERITED_V02_EVIDENCE,S03_SUCCESS_DEMO,S04_BLOCKED_MATRIX,S05_PRODUCER_IDENTITY_EVIDENCE,S06_RELEASE_EVIDENCE_SCHEMA,S07_DETERMINISM,S08_VERSION_METADATA,S09_MANIFEST,S10_ACCEPTANCE)
TASK036_RELEASE_FAILURE_PRECEDENCE_SOURCE_SLOT_COUNT=10
TASK036_PRIMARY_RELEASE_FAILURE_RULE=LOWEST_STAGE_ORDER
TASK036_LOWEST_SOURCE_PRECEDENCE_SLOT_WINS=true
TASK036_LOWEST_CORRECTED_RUNTIME_STAGE_WINS_WITHIN_SOURCE_SLOT=true
TASK036_LOWEST_CORRECTED_EXECUTION_STAGE_WINS=only when consistent with the same frozen source precedence slot ordering
TASK036_LATER_STAGE_MASKING=false
TASK036_LATER_FAILURE_MASKS_EARLIER_FAILURE=false
TASK036_PARTIAL_RELEASE_SUCCESS=false
TASK036_PARTIAL_RELEASE_ACCEPTANCE_RESULT_ALLOWED=false
TASK036_FINAL_SUCCESS_REQUIRES_ALL_REQUIRED_PRECEDENCE_SLOTS_PASS=true
TASK036_FINAL_SUCCESS_EMITTED_IF_ANY_REQUIRED_STAGE_BLOCKED=false
TASK036_BLOCKED_RESULT_MAY_NOT_CARRY_SUCCESS_STATUS=true
TASK036_FAILURE_SELECTION_KEY=(source_precedence_slot,corrected_runtime_stage,registry_ordinal)
TASK036_FAILURE_SELECTION_DIRECTION=ascending
TASK036_FAILURE_DEDUP_KEY=(demo_id,owner_task,blocker_code,field_path_or_path_set)
FROZEN_FAILURE_PRECEDENCE_PROJECTION=TASK036_SOURCE_PRECEDENCE_SLOT_TO_CORRECTED_RUNTIME_STAGE_TABLE
TASK036_FAILURE_PRECEDENCE_PROJECTION_COMPLETE=true
TASK036_SOURCE_DEFINITION_FREEZES_EXACT_STAGE_COUNT=false
TASK036_SOURCE_DEFINITION_FREEZES_EXACT_STAGE_ORDER=true
TASK036_SOURCE_DEFINITION_PERMITS_MECHANICAL_STAGE_DECOMPOSITION=true
TASK036_STAGE_COUNT_CHANGE_SOURCE_COMPATIBLE=true
TASK036_STAGE_COUNT_CHANGE_IS_MECHANICAL_ONLY=true
TASK036_NEW_STAGE_SEMANTIC_AUTHORITY_COUNT=0
```

The authoritative ten-row projection is:

```text
SOURCE_PRECEDENCE_SLOT|SOURCE_SEMANTIC_STAGE|CORRECTED_STAGE_SET|FIRST_FAIL_OWNER_STAGE|BLOCKER_OWNER|TERMINAL_RULE|LATER_STAGE_MASKING_ALLOWED|PARTIAL_SUCCESS_ALLOWED
S01_PRODUCTION_REPLAY|S01_PRODUCTION_REPLAY|S00,S01,S02,S03,S04,S05,S06,S07,S08,S09,S10,S11,S12|S00|TASK031,TASK032,TASK033,TASK034,TASK035,TASK036|first failure in the slot is terminal for the release decision|false|false
S02_INHERITED_V02_EVIDENCE|S02_INHERITED_V02_EVIDENCE|S13|S13|TASK036|first missing or invalid inherited evidence is terminal for the release decision|false|false
S03_SUCCESS_DEMO|S03_SUCCESS_DEMO|S14|S14|TASK036|success-demo assembly must be complete before success can be emitted|false|false
S04_BLOCKED_MATRIX|S04_BLOCKED_MATRIX|S17|S17|TASK036|blocked matrix and checklist failure remains the selected source slot|false|false
S05_PRODUCER_IDENTITY_EVIDENCE|S05_PRODUCER_IDENTITY_EVIDENCE|S20|S20|TASK036|producer identity or provenance failure remains the selected source slot|false|false
S06_RELEASE_EVIDENCE_SCHEMA|S06_RELEASE_EVIDENCE_SCHEMA|S15,S19|S15|TASK036|the first release-evidence schema failure wins within this slot|false|false
S07_DETERMINISM|S07_DETERMINISM|S16|S16|TASK036|determinism evidence failure blocks release acceptance|false|false
S08_VERSION_METADATA|S08_VERSION_METADATA|S21|S21|TASK036|version metadata failure blocks release acceptance|false|false
S09_MANIFEST|S09_MANIFEST|S18|S18|TASK036|manifest or artifact-inventory failure blocks release acceptance|false|false
S10_ACCEPTANCE|S10_ACCEPTANCE|S22|S22|TASK036|final acceptance failure blocks release acceptance|false|false
```

The per-stage authority index makes the precedence tuple explicit for all
corrected stages. The first component is the frozen source-slot rank; the
second is the corrected stage rank within that slot. `NONE` means that the
stage is an assembly handoff whose terminal blocker is emitted by its named
downstream validation stage, not that a later stage may mask a failure.

```text
CORRECTED_STAGE|SOURCE_SLOT_RANK|FAILURE_PRECEDENCE_ORDINAL|FAILURE_OWNER|BLOCKER_SET
S00_RAW_DEMO_INPUT_VALIDATION|1|(1,S00)|TASK036|ST036_DEMO_INPUT_SCHEMA_INVALID
S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS|1|(1,S01)|TASK036|ST036_DEMO_INPUT_CANONICALIZATION_FAILED
S02_BUILD_TASK031_PUBLIC_REQUEST|1|(1,S02)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S03_EXECUTE_TASK031_PUBLIC_OPERATION|1|(1,S03)|TASK031|SSHG_SCHEMA_VERSION_UNSUPPORTED
S04_BUILD_TASK032_PUBLIC_REQUEST|1|(1,S04)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S05_EXECUTE_TASK032_PUBLIC_OPERATION|1|(1,S05)|TASK032|SSFS_TASK031_GEOMETRY_MISSING
S06_BUILD_TASK033_PUBLIC_REQUEST|1|(1,S06)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S07_EXECUTE_TASK033_PUBLIC_OPERATION|1|(1,S07)|TASK033|SSHT_TASK032_FLOW_STATE_INVALID
S08_BUILD_TASK034_PUBLIC_REQUEST|1|(1,S08)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S09_EXECUTE_TASK034_PUBLIC_OPERATION|1|(1,S09)|TASK034|SSPD_UNSUPPORTED_SHELL_PASS_COUNT
S10_BUILD_TASK035_V2_PUBLIC_REQUEST|1|(1,S10)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST|1|(1,S11)|TASK035|SSTHC_TASK034_IDENTITY_MISMATCH,SSTHC_RAW_TYPE_INVALID
S12_VALIDATE_RELEASE_PRODUCTION_GRAPH|1|(1,S12)|TASK036|ST036_PUBLIC_GRAPH_INVALID
S13_AGGREGATE_UPSTREAM_EVIDENCE_AND_BLOCKED_CASES|2|(2,S13)|TASK036|ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING
S14_BUILD_RELEASE_INPUT_BUNDLE|3|(3,S14)|TASK036|NONE (assembly-only handoff)
S15_BUILD_TASK036_SUCCESS_IDENTITY_CORE|6|(6,S15)|TASK036|ST036_RESULT_CANONICALIZATION_FAILED
S16_VALIDATE_DETERMINISM_SURFACES|7|(7,S16)|TASK036|ST036_DETERMINISM_EVIDENCE_MISSING,ST036_CROSS_VERSION_BYTES_MISMATCH
S17_BUILD_ACCEPTANCE_CHECKLIST|4|(4,S17)|TASK036|ST036_RELEASE_CHECKLIST_INCOMPLETE
S18_BUILD_ARTIFACT_MANIFEST|9|(9,S18)|TASK036|ST036_ARTIFACT_DIGEST_MISMATCH,ST036_MANIFEST_INCOMPLETE
S19_BUILD_RELEASE_ACCEPTANCE_LEDGER|6|(6,S19)|TASK036|ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID
S20_BUILD_PROVENANCE|5|(5,S20)|TASK036|ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH,ST036_PROVENANCE_DAG_INVALID
S21_BUILD_VERSION_METADATA|8|(8,S21)|TASK036|ST036_VERSION_METADATA_INVALID
S22_FINALIZE_AND_VALIDATE_TASK036_RESULT_IDENTITY|10|(10,S22)|TASK036|ST036_RESULT_IDENTITY_FINALIZATION_FAILED,ST036_RELEASE_ACCEPTANCE_INCOMPLETE
```

The following mapping assigns every corrected runtime stage to exactly one
frozen source precedence slot. The source slot names retain their frozen
meaning; the corrected stage numbers are execution decomposition labels only.

```text
CORRECTED_STAGE|SOURCE_PRECEDENCE_SLOT|SOURCE_SEMANTIC_ROLE|FAILURE_SELECTION
S00_RAW_DEMO_INPUT_VALIDATION|S01_PRODUCTION_REPLAY|production replay preflight|slot then S00 then registry ordinal
S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS|S01_PRODUCTION_REPLAY|production replay normalization|slot then S01 then registry ordinal
S02_BUILD_TASK031_PUBLIC_REQUEST|S01_PRODUCTION_REPLAY|production replay request construction|slot then S02 then registry ordinal
S03_EXECUTE_TASK031_PUBLIC_OPERATION|S01_PRODUCTION_REPLAY|production replay public operation|slot then S03 then registry ordinal
S04_BUILD_TASK032_PUBLIC_REQUEST|S01_PRODUCTION_REPLAY|production replay request construction|slot then S04 then registry ordinal
S05_EXECUTE_TASK032_PUBLIC_OPERATION|S01_PRODUCTION_REPLAY|production replay public operation|slot then S05 then registry ordinal
S06_BUILD_TASK033_PUBLIC_REQUEST|S01_PRODUCTION_REPLAY|production replay request construction|slot then S06 then registry ordinal
S07_EXECUTE_TASK033_PUBLIC_OPERATION|S01_PRODUCTION_REPLAY|production replay public operation|slot then S07 then registry ordinal
S08_BUILD_TASK034_PUBLIC_REQUEST|S01_PRODUCTION_REPLAY|production replay request construction|slot then S08 then registry ordinal
S09_EXECUTE_TASK034_PUBLIC_OPERATION|S01_PRODUCTION_REPLAY|production replay public operation|slot then S09 then registry ordinal
S10_BUILD_TASK035_V2_PUBLIC_REQUEST|S01_PRODUCTION_REPLAY|production replay request construction|slot then S10 then registry ordinal
S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST|S01_PRODUCTION_REPLAY|production replay public operation|slot then S11 then registry ordinal
S12_VALIDATE_RELEASE_PRODUCTION_GRAPH|S01_PRODUCTION_REPLAY|production replay graph validation|slot then S12 then registry ordinal
S13_AGGREGATE_UPSTREAM_EVIDENCE_AND_BLOCKED_CASES|S02_INHERITED_V02_EVIDENCE|inherited v2 evidence aggregation|slot then S13 then registry ordinal
S14_BUILD_RELEASE_INPUT_BUNDLE|S03_SUCCESS_DEMO|success-demo input assembly|slot then S14 then registry ordinal
S15_BUILD_TASK036_SUCCESS_IDENTITY_CORE|S06_RELEASE_EVIDENCE_SCHEMA|release-evidence result preimage construction|slot then S15 then registry ordinal
S16_VALIDATE_DETERMINISM_SURFACES|S07_DETERMINISM|determinism validation|slot then S16 then registry ordinal
S17_BUILD_ACCEPTANCE_CHECKLIST|S04_BLOCKED_MATRIX|blocked-matrix and checklist evidence|slot then S17 then registry ordinal
S18_BUILD_ARTIFACT_MANIFEST|S09_MANIFEST|artifact manifest evidence|slot then S18 then registry ordinal
S19_BUILD_RELEASE_ACCEPTANCE_LEDGER|S06_RELEASE_EVIDENCE_SCHEMA|release acceptance ledger schema and digest|slot then S19 then registry ordinal
S20_BUILD_PROVENANCE|S05_PRODUCER_IDENTITY_EVIDENCE|producer identity and provenance evidence|slot then S20 then registry ordinal
S21_BUILD_VERSION_METADATA|S08_VERSION_METADATA|version metadata evidence|slot then S21 then registry ordinal
S22_FINALIZE_AND_VALIDATE_TASK036_RESULT_IDENTITY|S10_ACCEPTANCE|final acceptance and result identity|slot then S22 then registry ordinal
```

```text
TASK036_CORRECTED_RUNTIME_STAGE_COUNT=23
TASK036_CORRECTED_FAILURE_CAPABLE_STAGE_COUNT=23
TASK036_CORRECTED_FAILURE_STAGE_WITH_PRECEDENCE_COUNT=23
TASK036_CORRECTED_FAILURE_STAGE_WITHOUT_PRECEDENCE_COUNT=0
TASK036_SOURCE_PRECEDENCE_SLOT_WITHOUT_RUNTIME_PROJECTION_COUNT=0
TASK036_LATE_STAGE_FAILURE_MASKING_COUNT=0
TASK036_PARTIAL_RELEASE_ACCEPTANCE_RESULT_ALLOWED=false
TASK036_NEW_FAILURE_PRECEDENCE_SEMANTIC_AUTHORITY_COUNT=0
TASK036_SOURCE_FAILURE_PRECEDENCE_PROJECTION_COMPLETE=true
```

### 26.3 Current blocker-stage bindings after the corrected decomposition

The blocker codes, owners, ordinals, field paths, terminal result kinds, and
dedup semantics remain the frozen 22-row registry. The stage column in the
earlier registry table is a historical pre-R2 projection. The table below is
the sole current stage-binding authority and also binds every blocker to the
frozen source precedence slot.

```text
BLOCKER_CODE|ORDINAL|OWNER|HISTORICAL_STAGE_BINDING|CURRENT_CORRECTED_STAGE_BINDING|SOURCE_PRECEDENCE_SLOT|FIELD_PATH_OR_PATH_SET|DEDUP_KEY
SSHG_SCHEMA_VERSION_UNSUPPORTED|1|TASK031|TASK031/S03|TASK031/S03|S01_PRODUCTION_REPLAY|schema_version|source code + path
SSFS_TASK031_GEOMETRY_MISSING|2|TASK032|TASK032/S05|TASK032/S05|S01_PRODUCTION_REPLAY|task031_result.geometry|source code + path
SSHT_TASK032_FLOW_STATE_INVALID|3|TASK033|TASK033/S07|TASK033/S07|S01_PRODUCTION_REPLAY|task032_flow_state|source code + path
SSPD_UNSUPPORTED_SHELL_PASS_COUNT|4|TASK034|TASK034/internal S11, wrapper S09|TASK034/S09|S01_PRODUCTION_REPLAY|shell_pass_count|source code + path
SSTHC_TASK034_IDENTITY_MISMATCH|5|TASK035|TASK035/internal S10, wrapper S11|TASK035/S11|S01_PRODUCTION_REPLAY|B05 exact 12-path set|source code + ordered path set
SSTHC_RAW_TYPE_INVALID|6|TASK035|TASK035/internal S01, wrapper S11|TASK035/S11|S01_PRODUCTION_REPLAY|raw_request|source code + path
ST036_DEMO_INPUT_SCHEMA_INVALID|7|TASK036|TASK036/S00|TASK036/S00|S01_PRODUCTION_REPLAY|demo_input|code + path
ST036_DEMO_INPUT_CANONICALIZATION_FAILED|8|TASK036|TASK036/S01|TASK036/S01|S01_PRODUCTION_REPLAY|demo_input|code + path
ST036_PUBLIC_GRAPH_INVALID|9|TASK036|TASK036/S02, S04, S06, S08, S10, S12|TASK036/S02, S04, S06, S08, S10, S12|S01_PRODUCTION_REPLAY|runtime_graph|code + stage
ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING|10|TASK036|TASK036/S13|TASK036/S13|S02_INHERITED_V02_EVIDENCE|upstream_evidence_ledger|code + ref key
ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH|11|TASK036|TASK036/S13|TASK036/S20|S05_PRODUCER_IDENTITY_EVIDENCE|producer_identity|code + identity path
ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID|12|TASK036|TASK036/S14|TASK036/S19|S06_RELEASE_EVIDENCE_SCHEMA|release_acceptance_ledger|code + path
ST036_ARTIFACT_DIGEST_MISMATCH|13|TASK036|TASK036/S14|TASK036/S18|S09_MANIFEST|artifact_digest_set|code + artifact ID
ST036_MANIFEST_INCOMPLETE|14|TASK036|TASK036/S14|TASK036/S18|S09_MANIFEST|manifest.artifact_inventory|code + path
ST036_VERSION_METADATA_INVALID|15|TASK036|TASK036/S14|TASK036/S21|S08_VERSION_METADATA|version_metadata|code + field
ST036_PROVENANCE_DAG_INVALID|16|TASK036|TASK036/S14|TASK036/S20|S05_PRODUCER_IDENTITY_EVIDENCE|provenance.producer_edges|code + edge
ST036_DETERMINISM_EVIDENCE_MISSING|17|TASK036|TASK036/S15|TASK036/S16|S07_DETERMINISM|determinism_evidence|code + runtime
ST036_CROSS_VERSION_BYTES_MISMATCH|18|TASK036|TASK036/S15|TASK036/S16|S07_DETERMINISM|cross_version_canonical_bytes|code + surface
ST036_RESULT_CANONICALIZATION_FAILED|19|TASK036|TASK036/S16|TASK036/S15|S06_RELEASE_EVIDENCE_SCHEMA|result_preimage|code + kind
ST036_RESULT_IDENTITY_FINALIZATION_FAILED|20|TASK036|TASK036/S16|TASK036/S22|S10_ACCEPTANCE|result_hash|code + kind
ST036_RELEASE_CHECKLIST_INCOMPLETE|21|TASK036|TASK036/S14|TASK036/S17|S04_BLOCKED_MATRIX|acceptance_checklist|code + item
ST036_RELEASE_ACCEPTANCE_INCOMPLETE|22|TASK036|TASK036/S16|TASK036/S22|S10_ACCEPTANCE|release_acceptance_status|code + status
```

```text
TASK036_BLOCKER_REGISTRY_COUNT=22
TASK036_BLOCKER_STAGE_BINDING_CURRENT_COUNT=22
TASK036_BLOCKER_STAGE_BINDING_HISTORICAL_COUNT=22
TASK036_BLOCKER_STAGE_BINDING_STALE_COUNT=0
TASK036_BLOCKER_STAGE_BINDING_UNDEFINED_COUNT=0
TASK036_COMPETING_ACTIVE_BLOCKER_STAGE_AUTHORITY_COUNT=0
TASK036_BLOCKER_OWNER_CHANGE_COUNT=0
TASK036_BLOCKER_CODE_CHANGE_COUNT=0
TASK036_BLOCKER_ORDINAL_CHANGE_COUNT=0
TASK036_BLOCKER_FIELD_PATH_SEMANTIC_CHANGE_COUNT=0
TASK036_BLOCKER_WITH_PRECEDENCE_MAPPING_COUNT=22
TASK036_BLOCKER_WITHOUT_PRECEDENCE_MAPPING_COUNT=0
TASK036_PRECEDENCE_MAPPING_WITH_UNKNOWN_BLOCKER_COUNT=0
TASK036_BLOCKER_STAGE_PRECEDENCE_CONTRADICTION_COUNT=0
TASK036_CURRENT_BLOCKER_STAGE_BINDINGS_COMPLETE=true
BLOCKER_WITH_PRECEDENCE_MAPPING_COUNT=22
BLOCKER_WITHOUT_PRECEDENCE_MAPPING_COUNT=0
PRECEDENCE_MAPPING_WITH_UNKNOWN_BLOCKER_COUNT=0
BLOCKER_STAGE_PRECEDENCE_CONTRADICTION_COUNT=0
COMPETING_BLOCKER_STAGE_AUTHORITY_COUNT=0
```

### 26.4 HISTORICAL_SUPERSEDED — R2 lifecycle and next-gate authority

These declarations record the superseded R2 lifecycle. They are not active
after the R3 correction. The current next gate is declared only in Section
27. A successful author self-check does not accept or freeze the Design and
does not authorize implementation.

```text
TASK036_LIFECYCLE_AUTHORITY=SECTION_26_4_CURRENT_R2_LIFECYCLE
TASK036_SECTION_22_NEXT_GATE_STATUS=HISTORICAL_SUPERSEDED
TASK036_SECTION_25_13_NEXT_GATE_STATUS=HISTORICAL_SUPERSEDED
TASK036_ACTIVE_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R2_INDEPENDENT_REVIEW_ONLY
CURRENT_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R2_INDEPENDENT_REVIEW_ONLY
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R2_INDEPENDENT_REVIEW_ONLY
TASK036_ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=1
TASK036_SUPERSEDED_LIFECYCLE_NEXT_GATE_COUNT=2
TASK036_COMPETING_ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=0
TASK036_DESIGN_AUTHORED=true
TASK036_DESIGN_REVIEWED=false
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
TASK036_ARTIFACT_BYTES_GENERATED_NOW=false
TASK036_TEST_EXECUTION_PERFORMED_IN_DESIGN_GATE=false
NO_STEP_IMPLIES_THE_NEXT=true
```

### 26.5 HISTORICAL_SUPERSEDED — R2 source-preservation and finding-closure assertions

The R2 overlay changes no Source Definition decision. It only makes explicit
the source identity projection, source failure precedence projection, current
blocker-stage projection, and current lifecycle boundary required to close
N1-N4.

```text
TASK036_SOURCE_DECISION_COUNT=35
TASK036_SOURCE_DECISION_MAPPED_COUNT=35
TASK036_SOURCE_DECISION_UNMAPPED_COUNT=0
TASK036_SOURCE_SEMANTIC_CHANGE_COUNT=0
TASK036_SOURCE_SEMANTIC_REINTERPRETATION_COUNT=0
TASK036_NEW_SOURCE_DECISION_COUNT=0

N1_FINDING_ID=TASK036_D07_RELEASE_ACCEPTANCE_RESULT_ID_CONTRACT_MISMATCH
N1_STATUS=RESOLVED_BY_DESIGN_R2_CORRECTION
N1_SECTION_REF=26.1
N1_CONTRACT_PROJECTION_COMPLETE=true
N2_FINDING_ID=TASK036_D13_RELEASE_FAILURE_PRECEDENCE_NOT_PROJECTED
N2_STATUS=RESOLVED_BY_DESIGN_R2_CORRECTION
N2_SECTION_REF=26.2
N2_CONTRACT_PROJECTION_COMPLETE=true
N3_FINDING_ID=TASK036_BLOCKER_STAGE_BINDINGS_STALE_AFTER_CORRECTION
N3_STATUS=RESOLVED_BY_DESIGN_R2_CORRECTION
N3_SECTION_REF=26.3
N3_CONTRACT_PROJECTION_COMPLETE=true
N4_FINDING_ID=TASK036_LIFECYCLE_NEXT_GATE_AUTHORITY_CONTRADICTION
N4_STATUS=RESOLVED_BY_DESIGN_R2_CORRECTION
N4_SECTION_REF=26.4
N4_CONTRACT_PROJECTION_COMPLETE=true

PREVIOUS_SOURCE_REINTERPRETATION_01=release_acceptance_result_id was incorrectly mapped to the internal Task036 UUIDv5 result identity
CORRECTED_BY_01=Section 26.1 separates N16.ledger_hash with the frozen sha256: format from TASK036_INTERNAL_RESULT_ID
PREVIOUS_SOURCE_REINTERPRETATION_02=frozen release-failure precedence was not projected onto the corrected 23-stage execution decomposition
CORRECTED_BY_02=Section 26.2 maps all ten frozen source precedence slots and all corrected runtime stages without changing source order
TASK036_SOURCE_REINTERPRETATION_CLOSURE_COUNT=2
TASK036_SOURCE_REINTERPRETATION_CLOSURE_COMPLETE=true

F1_STATUS=REMAINS_RESOLVED
F2_STATUS=REMAINS_RESOLVED
F3_STATUS=REMAINS_RESOLVED
F4_STATUS=REMAINS_RESOLVED
F5_STATUS=REMAINS_RESOLVED
F6_STATUS=REMAINS_RESOLVED
TASK036_R2_CLOSED_FINDING_COUNT=4
TASK036_R2_REOPENED_FINDING_COUNT=0
TASK036_R2_NEW_FINDING_COUNT=0
TASK036_R2_NEW_FINDINGS=NONE
TASK036_R2_NON_FINDING_REGRESSION_COUNT=0
```

### 26.6 HISTORICAL_SUPERSEDED — R2 deterministic author self-check

This self-check is author-side evidence only. It does not constitute an
independent review, Design acceptance, Design freeze, implementation
authorization, artifact generation, or release authorization.

```text
TASK036_R2_STAGE_COUNT=23
TASK036_R2_STAGE_PRECEDENCE_MAPPING_COUNT=23
TASK036_R2_BLOCKER_COUNT=22
TASK036_R2_CURRENT_BLOCKER_STAGE_BINDING_COUNT=22
TASK036_R2_SOURCE_PRECEDENCE_SLOT_COUNT=10
TASK036_R2_INTERNAL_RESULT_ID_CONTRACT_COUNT=1
TASK036_R2_RELEASE_ACCEPTANCE_RESULT_ID_CONTRACT_COUNT=1
TASK036_R2_IDENTITY_ALIAS_COUNT=0
TASK036_R2_FAILURE_PRECEDENCE_CONTRADICTION_COUNT=0
TASK036_R2_BLOCKER_STAGE_BINDING_CONTRADICTION_COUNT=0
TASK036_R2_LIFECYCLE_CONTRADICTION_COUNT=0
TASK036_R2_RELEASE_ACCEPTANCE_RESULT_ID_PREHASH_CYCLE_COUNT=0
TASK036_R2_INTERNAL_RESULT_ID_PREHASH_CYCLE_COUNT=0
TASK036_R2_AMBIGUOUS_AUTHORITY_TOKEN_COUNT=0
TASK036_R2_UNRESOLVED_DESIGN_AUTHORITY_COUNT=0
TASK036_R2_INTERNAL_UUID_IDENTITY_RULE_COUNT=1
TASK036_R2_RELEASE_ACCEPTANCE_SHA256_IDENTITY_RULE_COUNT=1
TASK036_R2_UNFROZEN_IDENTITY_RULE_COUNT=0
INTERNAL_UUID_IDENTITY_RULE_COUNT=1
RELEASE_ACCEPTANCE_SHA256_IDENTITY_RULE_COUNT=1
RESULT_ID_DERIVATION_VALID=true
TASK036_R2_IDENTITY_DATAFLOW_ACYCLIC=true
TASK036_R2_TOPOLOGICAL_ORDER_EXISTS=true
TASK036_R2_CIRCULAR_PREHASH_REFERENCE_COUNT=0
TASK036_R2_FORWARD_REFERENCE_COUNT=0
TASK036_R2_UNDEFINED_IDENTITY_DEPENDENCY_COUNT=0
TASK036_R2_RESULT_ID_SELF_REFERENCE_COUNT=0
TASK036_R2_RESULT_HASH_RESULT_ID_CYCLE_COUNT=0
IDENTITY_DATAFLOW_ACYCLIC=true
TOPOLOGICAL_SORT_EXISTS=true
CIRCULAR_PREHASH_REFERENCE_COUNT=0
FORWARD_REFERENCE_COUNT=0
UNDEFINED_IDENTITY_DEPENDENCY_COUNT=0
RESULT_ID_SELF_REFERENCE_COUNT=0
RESULT_HASH_RESULT_ID_CYCLE_COUNT=0
HASHED_CONTRACT_COUNT=11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT=11
MISSING_CANONICAL_KIND_TAG_COUNT=0
PROVENANCE_NODE_COUNT=7
PROVENANCE_EDGE_COUNT=6
PROVENANCE_UNBOUND_EDGE_IDENTITY_COUNT=0
ARTIFACT_COUNT=11
ARTIFACT_BACKWARD_DEPENDENCY_COUNT=0
ARTIFACT_DIGEST_CYCLE_COUNT=0
DETERMINISM_SURFACE_COUNT=9
PY311_REPEAT_SURFACE_COUNT=9
PY312_REPEAT_SURFACE_COUNT=9
CROSS_PYTHON_SURFACE_COUNT=9
SURFACE_COUNT_MISMATCH_COUNT=0
TEST_ID_COUNT=30
UNIQUE_TEST_ID_COUNT=30
TEST_COVERAGE_GAP_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0
TASK036_R2_DESIGN_INTERNAL_CONTRADICTION_COUNT=0
TASK036_R2_COUNT_CONTRADICTION_COUNT=0
TASK036_R2_CROSS_SECTION_AUTHORITY_CONTRADICTION_COUNT=0
TASK036_R2_DESIGN_CORRECTION_COMPLETE=true
TASK036_DESIGN_CORRECTION_COMPLETE=true
TASK036_DESIGN_CORRECTION_CLOSED_FINDING_COUNT=4
TASK036_DESIGN_CORRECTION_REOPENED_FINDING_COUNT=0
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_CORRECTION=true
TASK036_DESIGN_R2_CORRECTION_AUTHOR_SELF_CHECK=PASS
TASK036_DESIGN_CORRECTION_AUTHOR_SELF_CHECK=PASS
AUTHOR_SELF_CHECK_PASS_IS_NOT_INDEPENDENT_DESIGN_REVIEW=true
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_R2_AUTHORING_CHANGED_FILE_COUNT=1
TASK036_R2_AUTHORING_CHANGED_FILES=(docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md)
TASK036_R2_DESIGN_MUTATED=true
TASK036_R2_SOURCE_DEFINITION_MUTATED=false
TASK036_R2_ISSUE203_MUTATED=false
TASK036_R2_TASK036_CODE_MUTATED=false
TASK036_R2_TASK036_TESTS_MUTATED=false
TASK036_R2_TASK036_ARTIFACTS_MUTATED=false
TASK036_R2_CI_MUTATED=false
TASK036_R2_WORKFLOW_MUTATED=false
TASK036_R2_INDEX_MUTATED=false
TASK036_R2_BRANCH_CREATED=false
TASK036_R2_COMMIT_CREATED=false
TASK036_R2_PUSH_PERFORMED=false
TASK036_R2_PR_CREATED=false
TASK036_R2_MERGE_PERFORMED=false
```

```text
TASK036_DESIGN_R2_CORRECTION_IDENTITY_REPORTED_OUT_OF_BAND=true
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R2_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 23. HISTORICAL_SUPERSEDED — Pre-correction author self-check

The author-side checks are deterministic checks over this file's closed tables
and declarations. They are not independent review evidence.

```text
SOURCE_DECISION_COUNT=35
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_SEMANTIC_CHANGE_COUNT=0
DESIGN_INTERNAL_CONTRADICTION_COUNT=0
UNRESOLVED_DESIGN_DECISION_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNBOUNDED_FILE_ALLOWLIST_ENTRY_COUNT=0
UNFROZEN_SCHEMA_COUNT=0
UNFROZEN_BLOCKER_COUNT=0
UNFROZEN_STAGE_COUNT=0
UNFROZEN_TEST_ID_COUNT=0
UNFROZEN_ARTIFACT_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0
TASK036_DESIGN_AUTHOR_SELF_CHECK=PASS
AUTHOR_SELF_CHECK_PASS_IS_NOT_INDEPENDENT_DESIGN_REVIEW=true
```

## 24. Mutation boundary for this authoring gate

```text
DESIGN_FILE_CREATED=true
DESIGN_MUTATED=true
SOURCE_DEFINITION_MUTATED=false
ISSUE203_MUTATED=false
TASK036_CODE_MUTATED=false
TASK036_TESTS_MUTATED=false
TASK036_ARTIFACTS_MUTATED=false
TASK031_MUTATED=false
TASK032_MUTATED=false
TASK033_MUTATED=false
TASK034_MUTATED=false
TASK035_MUTATED=false
CI_MUTATED=false
WORKFLOW_MUTATED=false
INDEX_MUTATED=false
BRANCH_CREATED=false
COMMIT_CREATED=false
PUSH_PERFORMED=false
PR_CREATED=false
MERGE_PERFORMED=false
TAG_MUTATED=false
RELEASE_MUTATED=false
```

## 25. Preserved architecture and historical R2 contract

Sections 25.1-25.6 are the preserved six-finding corrected architecture. The
artifact, determinism-artifact, test, version, and allowlist declarations in
Sections 25.7-25.11 are the historical R2 baseline only and are explicitly
superseded by Section 27. The frozen R5 Source Definition, upstream public
producer contracts, demo inventory, blocker registry, and release scope remain
unchanged except for the direct D23/D25/D26/D32 projections in Section 27.

```text
TASK036_EFFECTIVE_CORRECTED_CONTRACT=true
TASK036_CORRECTION_SCOPE_ONLY=true
TASK036_FROZEN_SOURCE_DEFINITION_UNCHANGED=true
TASK036_UPSTREAM_PRODUCER_CONTRACTS_UNCHANGED=true
TASK036_RELEASE_SCOPE_UNCHANGED=true

F1_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F1_SECTION_REF=25.1,25.2,25.5
F2_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F2_SECTION_REF=25.4
F3_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F3_SECTION_REF=25.5,25.7
F4_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F4_SECTION_REF=25.8
F5_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F5_SECTION_REF=25.6
F6_STATUS=RESOLVED_BY_DESIGN_CORRECTION
F6_SECTION_REF=25.3
```

### 25.1 Executable dataflow nodes

The corrected graph uses one topological node order. A producer node is
complete before every consumer node starts. Upstream result identities are
owned by their public producers; Task036 hashes only the explicitly named
Task036 identity-bearing nodes. The `Release artifact authority` column is
node-local materialization status, not a second artifact inventory. It is
`NONE` for every executable graph node: the only persisted release artifacts
are the six frozen D23 paths in Section 27.1. Internal records and embedded
projections remain explicit below and are not release artifacts.

| Node | Kind | Producer stage | Inputs | Outputs | Hashed | Result ID | Release artifact authority | Canonical kind tag | Semantic identity inputs | Late-bound fields | Excluded from prehash |
|---|---|---:|---|---|---|---|---|---|---|---|---|
| `N00_RAW_DEMO_INPUT` | raw boundary input | S00 | caller-owned raw mapping | closed raw projection | no | no | `NONE` | none | raw field presence and types | none | none |
| `N01_DEMO_INPUT` | parsed demo input | S01 | N00 | nine-field demo input and request hash | yes | no | `NONE` | `TASK036_DEMO_INPUT` | `DEMO_INPUT_FIELD_ORDER` | none | none |
| `N02_TASK031_RESULT` | public Task031 result | S03 | N01 request | Task031 public result identity | producer-owned | producer-owned | `NONE` | producer-owned | Task031 public contract | none | producer-owned |
| `N03_TASK032_RESULT` | public Task032 result | S05 | N01 fields and N02 | Task032 public result identity | producer-owned | producer-owned | `NONE` | producer-owned | Task032 public contract | none | producer-owned |
| `N04_TASK033_RESULT` | public Task033 result | S07 | N03 and N01 evidence | Task033 public result identity | producer-owned | producer-owned | `NONE` | producer-owned | Task033 public contract | none | producer-owned |
| `N05_TASK034_RESULT` | public Task034 result | S09 | N04 and caller authorities | Task034 public result identity | producer-owned | producer-owned | `NONE` | producer-owned | Task034 v2 public contract | none | producer-owned |
| `N06_TASK035_RESULT` | public Task035 v2 result | S11 | N02–N05 and field 09 | Task035 public result identity | producer-owned | producer-owned | `NONE` | producer-owned | Task035 v2 public contract | none | producer-owned |
| `N07_PRODUCTION_GRAPH_EVIDENCE` | runtime graph evidence | S12 | N02–N06 | ordered producer status evidence | no | no | `NONE` | none | public producer identities | none | none |
| `N08_UPSTREAM_EVIDENCE_LEDGER` | upstream evidence ledger | S13 | N07, frozen review/test/CI records | ledger hash | yes | no | `NONE` | `TASK036_UPSTREAM_EVIDENCE_LEDGER` | declared ledger prehash fields | none | `ledger_hash` |
| `N09_BLOCKED_CASES_EVIDENCE` | blocked demo evidence | S13 | frozen B01–B06 definitions and public blocked branches | closed blocked-case evidence projection | artifact digest only | no | `NONE` | none | B01–B06 records | none | none |
| `N10_RELEASE_INPUT_BUNDLE` | release-evidence input bundle | S14 | N06, N07, N08, N09 | complete pre-result release inputs | no | no | `NONE` | none | upstream identities, capabilities, evidence refs | none | none |
| `N11_SUCCESS_IDENTITY_CORE` | Task036 success identity core | S15 | N10 and immutable source identity | success prehash bytes, result hash, result ID | yes | yes | `NONE` | `TASK036_SUCCESS_RESULT` | corrected success prehash fields | none | late-bound evidence fields, `result_hash`, `result_id` |
| `N12_CROSS_RUNTIME_DETERMINISM` | cross-Python evidence | S16 | N11 and two runtimes | cross-runtime evidence hash | yes | no | `NONE` | `TASK036_DETERMINISM_EVIDENCE` | listed canonical bytes, hashes, and IDs | runtime executable path | `evidence_hash` |
| `N13_REPEAT_RUN_DETERMINISM` | repeat-run evidence | S16 | N11 and two repeats per runtime | repeat evidence hash | yes | no | `NONE` | `TASK036_DETERMINISM_EVIDENCE` | listed canonical bytes, hashes, and IDs | runtime executable path | `evidence_hash` |
| `N14_ACCEPTANCE_CHECKLIST` | acceptance checklist | S17 | N08–N13 and closed inventories | checklist hash | yes | no | `NONE` | `TASK036_ACCEPTANCE_CHECKLIST` | checklist prehash fields | none | `checklist_hash` |
| `N15_MANIFEST` | artifact manifest | S18 | N01, N08, N09, N11–N14 | manifest hash | yes | no | `NONE` | `TASK036_MANIFEST` | manifest foundation digest set and closed path inventory | none | `manifest_hash` |
| `N16_RELEASE_ACCEPTANCE_LEDGER` | release acceptance ledger | S19 | N08, N11–N15 | ledger hash and release status | yes | no | `NONE` | `TASK036_RELEASE_ACCEPTANCE_LEDGER` | corrected ledger prehash fields | none | `ledger_hash` |
| `N17_PROVENANCE` | provenance record | S20 | N06, N08, N11, N14–N16 | provenance hash and six exact edges | yes | no | `NONE` | `TASK036_PROVENANCE` | producer identities and exact edge records | none | `provenance_hash` |
| `N18_VERSION_METADATA` | version metadata | S21 | N11, N15–N17 | metadata hash | yes | no | `NONE` | `TASK036_VERSION_METADATA` | metadata prehash fields | none | `metadata_hash` |
| `N19_FINAL_ACCEPTANCE_RESULT` | final public result envelope | S22 | N08, N11–N18 | final VALID/BLOCKED envelope and embedded release projection | result identity carried from N11 or producer branch | carried from N11 or producer branch | `NONE` | `TASK036_SUCCESS_RESULT` for success | final schema fields and verified N11 identity | late evidence fields are attached here | `result_hash`, `result_id`, and the six late-bound evidence fields are not rehashed |

```text
TASK036_EXECUTABLE_DATAFLOW_DAG=true
TASK036_DATAFLOW_NODE_COUNT=20
IDENTITY_DATAFLOW_ACYCLIC=true
DATAFLOW_TOPOLOGICAL_ORDER_EXISTS=true
IDENTITY_CONSTRUCTION_ORDER=(N00_RAW_DEMO_INPUT,N01_DEMO_INPUT,N02_TASK031_RESULT,N03_TASK032_RESULT,N04_TASK033_RESULT,N05_TASK034_RESULT,N06_TASK035_RESULT,N07_PRODUCTION_GRAPH_EVIDENCE,N08_UPSTREAM_EVIDENCE_LEDGER,N09_BLOCKED_CASES_EVIDENCE,N10_RELEASE_INPUT_BUNDLE,N11_SUCCESS_IDENTITY_CORE,N12_CROSS_RUNTIME_DETERMINISM,N13_REPEAT_RUN_DETERMINISM,N14_ACCEPTANCE_CHECKLIST,N15_MANIFEST,N16_RELEASE_ACCEPTANCE_LEDGER,N17_PROVENANCE,N18_VERSION_METADATA,N19_FINAL_ACCEPTANCE_RESULT)
CORRECTED_NODE_PRODUCTION_ORDER=IDENTITY_CONSTRUCTION_ORDER
BACKWARD_DEPENDENCY_COUNT=0
UNDEFINED_DEPENDENCY_COUNT=0
SELF_EDGE_COUNT=0
```

### 25.2 Corrected stage topology

The original S00–S16 tail is superseded by the following 23-stage topology.
The additional stages are mechanical release-evidence construction stages
needed to make the frozen release lifecycle executable; they do not add a
producer operation, a capability, or an engineering calculation.

```text
CORRECTED_RUNTIME_STAGE_COUNT=23
CORRECTED_VALIDATION_STAGE_COUNT=23
CORRECTED_STAGE_ORDER=(S00_RAW_DEMO_INPUT_VALIDATION,S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS,S02_BUILD_TASK031_PUBLIC_REQUEST,S03_EXECUTE_TASK031_PUBLIC_OPERATION,S04_BUILD_TASK032_PUBLIC_REQUEST,S05_EXECUTE_TASK032_PUBLIC_OPERATION,S06_BUILD_TASK033_PUBLIC_REQUEST,S07_EXECUTE_TASK033_PUBLIC_OPERATION,S08_BUILD_TASK034_PUBLIC_REQUEST,S09_EXECUTE_TASK034_PUBLIC_OPERATION,S10_BUILD_TASK035_V2_PUBLIC_REQUEST,S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST,S12_VALIDATE_RELEASE_PRODUCTION_GRAPH,S13_AGGREGATE_UPSTREAM_EVIDENCE_AND_BLOCKED_CASES,S14_BUILD_RELEASE_INPUT_BUNDLE,S15_BUILD_TASK036_SUCCESS_IDENTITY_CORE,S16_VALIDATE_DETERMINISM_SURFACES,S17_BUILD_ACCEPTANCE_CHECKLIST,S18_BUILD_ARTIFACT_MANIFEST,S19_BUILD_RELEASE_ACCEPTANCE_LEDGER,S20_BUILD_PROVENANCE,S21_BUILD_VERSION_METADATA,S22_FINALIZE_AND_VALIDATE_TASK036_RESULT_IDENTITY)
CORRECTED_STAGE_TOPOLOGY_EXECUTABLE=true
STAGE_PRODUCER_CONSUMER_CONTRADICTION_COUNT=0
CORRECTED_PUBLIC_PRODUCTION_OPERATION_COUNT=5
CORRECTED_PRIVATE_STAGE_COUNT=0
CORRECTED_SKIPPED_REQUIRED_STAGE_COUNT=0
CORRECTED_EXPECTED_OUTPUT_AS_INPUT_COUNT=0
CORRECTED_SYNTHETIC_RESULT_SUBSTITUTION_COUNT=0
```

Each stage has one fixed interface:

```text
S00|PURPOSE=closed raw boundary validation|INPUT=caller-owned dict[str,object]|OUTPUT=N00_RAW_DEMO_INPUT|PRODUCED=N00|CONSUMED=NONE|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_INVALID|BLOCKER_OWNER=TASK036|IDENTITY_EFFECT=raw projection only|INTERNAL_OUTPUT_EFFECT=N00_RAW_DEMO_INPUT|PERSISTED_ARTIFACT_EFFECT=NONE
S01|PURPOSE=parse and normalize frozen inputs|INPUT=N00|OUTPUT=N01_DEMO_INPUT|PRODUCED=N01|CONSUMED=N00|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036|IDENTITY_EFFECT=demo input hash|INTERNAL_OUTPUT_EFFECT=N01_DEMO_INPUT|PERSISTED_ARTIFACT_EFFECT=NONE
S02|PURPOSE=build Task031 public request|INPUT=N01|OUTPUT=Task031 raw request|PRODUCED=NONE|CONSUMED=N01|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=carry Task031 request authority|INTERNAL_OUTPUT_EFFECT=TASK031_RAW_REQUEST|PERSISTED_ARTIFACT_EFFECT=NONE
S03|PURPOSE=execute Task031 public operation|INPUT=Task031 raw request|OUTPUT=N02_TASK031_RESULT|PRODUCED=N02|CONSUMED=N01|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_BLOCKED|BLOCKER_OWNER=TASK031|IDENTITY_EFFECT=producer-owned identity|INTERNAL_OUTPUT_EFFECT=N02_TASK031_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
S04|PURPOSE=build Task032 public request|INPUT=N01 fields plus N02|OUTPUT=Task032 raw request|PRODUCED=NONE|CONSUMED=N01,N02|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=carry Task032 authority|INTERNAL_OUTPUT_EFFECT=TASK032_RAW_REQUEST|PERSISTED_ARTIFACT_EFFECT=NONE
S05|PURPOSE=execute Task032 public operation|INPUT=Task032 raw request|OUTPUT=N03_TASK032_RESULT|PRODUCED=N03|CONSUMED=N02|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_BLOCKED|BLOCKER_OWNER=TASK032|IDENTITY_EFFECT=producer-owned identity|INTERNAL_OUTPUT_EFFECT=N03_TASK032_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
S06|PURPOSE=build Task033 public request|INPUT=N01 evidence plus N03|OUTPUT=Task033 raw request|PRODUCED=NONE|CONSUMED=N01,N03|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=carry Task033 authority|INTERNAL_OUTPUT_EFFECT=TASK033_RAW_REQUEST|PERSISTED_ARTIFACT_EFFECT=NONE
S07|PURPOSE=execute Task033 public operation|INPUT=Task033 raw request|OUTPUT=N04_TASK033_RESULT|PRODUCED=N04|CONSUMED=N03|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_BLOCKED|BLOCKER_OWNER=TASK033|IDENTITY_EFFECT=producer-owned identity|INTERNAL_OUTPUT_EFFECT=N04_TASK033_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
S08|PURPOSE=build Task034 public request|INPUT=N04 plus caller authorities|OUTPUT=Task034 raw request|PRODUCED=NONE|CONSUMED=N04|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=carry caller authority|INTERNAL_OUTPUT_EFFECT=TASK034_RAW_REQUEST|PERSISTED_ARTIFACT_EFFECT=NONE
S09|PURPOSE=execute Task034 public operation|INPUT=Task034 raw request|OUTPUT=N05_TASK034_RESULT|PRODUCED=N05|CONSUMED=N04|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_BLOCKED|BLOCKER_OWNER=TASK034|IDENTITY_EFFECT=producer-owned identity|INTERNAL_OUTPUT_EFFECT=N05_TASK034_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
S10|PURPOSE=build Task035 v2 public request|INPUT=N02,N03,N04,N05 and field 09|OUTPUT=Task035 v2 raw request|PRODUCED=NONE|CONSUMED=N02,N03,N04,N05|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=carry all upstream identities|INTERNAL_OUTPUT_EFFECT=TASK035_V2_RAW_REQUEST|PERSISTED_ARTIFACT_EFFECT=NONE
S11|PURPOSE=execute Task035 v2 public validate_request|INPUT=Task035 v2 raw request|OUTPUT=N06_TASK035_RESULT|PRODUCED=N06|CONSUMED=N05|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_BLOCKED|BLOCKER_OWNER=TASK035|IDENTITY_EFFECT=producer-owned identity|INTERNAL_OUTPUT_EFFECT=N06_TASK035_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
S12|PURPOSE=validate the complete public production graph|INPUT=N02,N03,N04,N05,N06|OUTPUT=N07_PRODUCTION_GRAPH_EVIDENCE|PRODUCED=N07|CONSUMED=N02,N03,N04,N05,N06|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_VALID_TERMINAL_ON_GRAPH_FAILURE|BLOCKER_OWNER=TASK036_GRAPH|IDENTITY_EFFECT=ordered producer chain|INTERNAL_OUTPUT_EFFECT=N07_PRODUCTION_GRAPH_EVIDENCE|PERSISTED_ARTIFACT_EFFECT=NONE
S13|PURPOSE=aggregate upstream evidence and six blocked cases|INPUT=N07 plus frozen evidence records|OUTPUT=N08_UPSTREAM_EVIDENCE_LEDGER,N09_BLOCKED_CASES_EVIDENCE|PRODUCED=N08,N09|CONSUMED=N07|TERMINAL_OR_NONTERMINAL=NONTERMINAL_ON_SUCCESS_DEMO|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=upstream evidence hash|INTERNAL_OUTPUT_EFFECT=N08_UPSTREAM_EVIDENCE_LEDGER,N09_BLOCKED_CASES_EVIDENCE|PERSISTED_ARTIFACT_EFFECT=NONE
S14|PURPOSE=assemble complete release input bundle|INPUT=N06,N07,N08,N09|OUTPUT=N10_RELEASE_INPUT_BUNDLE|PRODUCED=N10|CONSUMED=N06,N07,N08,N09|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=no new hash|INTERNAL_OUTPUT_EFFECT=N10_RELEASE_INPUT_BUNDLE|PERSISTED_ARTIFACT_EFFECT=TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN
S15|PURPOSE=build success identity core|INPUT=N10 and immutable source identity|OUTPUT=N11_SUCCESS_IDENTITY_CORE|PRODUCED=N11|CONSUMED=N10|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RESULT_IDENTITY|IDENTITY_EFFECT=success canonical bytes, result_hash, result_id|INTERNAL_OUTPUT_EFFECT=N11_SUCCESS_IDENTITY_CORE|PERSISTED_ARTIFACT_EFFECT=NONE
S16|PURPOSE=validate cross-runtime and repeat-run surfaces|INPUT=N11 in Python 3.11 and 3.12|OUTPUT=N12,N13|PRODUCED=N12,N13|CONSUMED=N11|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_DETERMINISM|IDENTITY_EFFECT=determinism evidence hashes|INTERNAL_OUTPUT_EFFECT=N12_CROSS_RUNTIME_DETERMINISM,N13_REPEAT_RUN_DETERMINISM|PERSISTED_ARTIFACT_EFFECT=NONE
S17|PURPOSE=build acceptance checklist|INPUT=N08,N09,N11,N12,N13|OUTPUT=N14_ACCEPTANCE_CHECKLIST|PRODUCED=N14|CONSUMED=N08,N09,N11,N12,N13|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=checklist hash|INTERNAL_OUTPUT_EFFECT=N14_ACCEPTANCE_CHECKLIST|PERSISTED_ARTIFACT_EFFECT=TASK036_RELEASE_ACCEPTANCE_MARKDOWN
S18|PURPOSE=build closed artifact manifest|INPUT=N01,N08,N09,N11,N12,N13,N14|OUTPUT=N15_MANIFEST|PRODUCED=N15|CONSUMED=N01,N08,N09,N11,N12,N13,N14|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=manifest hash|INTERNAL_OUTPUT_EFFECT=N15_MANIFEST|PERSISTED_ARTIFACT_EFFECT=TASK036_RELEASE_MANIFEST_JSON
S19|PURPOSE=build release acceptance ledger|INPUT=N08,N11,N12,N13,N14,N15|OUTPUT=N16_RELEASE_ACCEPTANCE_LEDGER|PRODUCED=N16|CONSUMED=N08,N11,N12,N13,N14,N15|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=ledger hash and status|INTERNAL_OUTPUT_EFFECT=N16_RELEASE_ACCEPTANCE_LEDGER|PERSISTED_ARTIFACT_EFFECT=NONE
S20|PURPOSE=build six-edge provenance record|INPUT=N06,N08,N11,N14,N15,N16|OUTPUT=N17_PROVENANCE|PRODUCED=N17|CONSUMED=N06,N08,N11,N14,N15,N16|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=provenance hash and exact edges|INTERNAL_OUTPUT_EFFECT=N17_PROVENANCE|PERSISTED_ARTIFACT_EFFECT=NONE
S21|PURPOSE=build version metadata|INPUT=N11,N15,N16,N17|OUTPUT=N18_VERSION_METADATA|PRODUCED=N18|CONSUMED=N11,N15,N16,N17|TERMINAL_OR_NONTERMINAL=NONTERMINAL|BLOCKER_OWNER=TASK036_RELEASE_EVIDENCE|IDENTITY_EFFECT=metadata hash|INTERNAL_OUTPUT_EFFECT=N18_VERSION_METADATA|PERSISTED_ARTIFACT_EFFECT=NONE
S22|PURPOSE=finalize and validate Task036 result identity|INPUT=N08,N11,N12,N13,N14,N15,N16,N17,N18|OUTPUT=N19_FINAL_ACCEPTANCE_RESULT|PRODUCED=N19|CONSUMED=N08,N11,N12,N13,N14,N15,N16,N17,N18|TERMINAL_OR_NONTERMINAL=TERMINAL|BLOCKER_OWNER=TASK036_RESULT_IDENTITY|IDENTITY_EFFECT=revalidate N11 result_hash/result_id and emit final envelope|INTERNAL_OUTPUT_EFFECT=N19_FINAL_ACCEPTANCE_RESULT|PERSISTED_ARTIFACT_EFFECT=NONE
```

The 23-stage topology is a Design-level mechanical refinement of D13. The
five upstream public operations and the release lifecycle remain the same.

```text
TASK036_D13_STAGE_COUNT_CHANGE_MECHANICAL=true
TASK036_D13_SOURCE_SEMANTICS_CHANGED=false
TASK036_RELEASE_LIFECYCLE_ORDER=(RAW_INPUT,TASK031,TASK032,TASK033,TASK034,TASK035,RELEASE_EVIDENCE,RELEASE_ACCEPTANCE,DETERMINISTIC_IDENTITY_VALIDATION)
TASK036_RELEASE_EVIDENCE_STAGE_RANGE=(S13,S14,S16,S17,S18,S19,S20,S21)
TASK036_RELEASE_ACCEPTANCE_STAGE_RANGE=(S17,S18,S19)
TASK036_FINAL_DETERMINISTIC_IDENTITY_VALIDATION_STAGE=S22
TASK036_RELEASE_EVIDENCE_TAIL_COMPLETES_BEFORE_FINAL_RESULT=true
```

### 25.3 Complete final-result input projection

The final success schema remains 31 fields. Six release-evidence fields are
late-bound attachments and are excluded from the success identity core. Their
values are assembled after N11 and are verified at S22 without recomputing the
N11 result hash or result ID.

```text
TASK036_SUCCESS_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,release_acceptance_ledger,upstream_evidence_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance,request_hash,result_hash,result_id,warnings,blockers,deferred_capabilities)
TASK036_SUCCESS_RESULT_FIELD_COUNT=31
TASK036_SUCCESS_RESULT_LATE_BOUND_FIELDS=(release_acceptance_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance)
TASK036_SUCCESS_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,upstream_evidence_ledger,request_hash,warnings,blockers,deferred_capabilities)
TASK036_SUCCESS_RESULT_PREHASH_FIELD_COUNT=23
TASK036_SUCCESS_RESULT_EXCLUDED_FROM_PREHASH=(release_acceptance_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance,result_hash,result_id)
TASK036_SUCCESS_RESULT_LATE_BOUND_FIELD_COUNT=6
TASK036_SUCCESS_RESULT_PREHASH_EXCLUDED_FIELD_COUNT=8
TASK036_RESULT_HASH_PREIMAGE_EXCLUDES_RESULT_ID=true
TASK036_RESULT_HASH_RESULT_ID_CYCLE_COUNT=0
TASK036_RESULT_ID_SELF_REFERENCE_COUNT=0
```

The final-result projection is explicit and total. The declared field order
above is the schema order; the following rules bind every derived field to a
fixed producer node and stage.

```text
FINAL_RESULT_SCHEMA_FIELD_COUNT=31
FINAL_RESULT_INPUT_FIELD_COUNT=31
FINAL_RESULT_INPUT_PROJECTION=(schema_version,profile_id,implementation_software_version,demo_id,release_version,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,release_acceptance_ledger,upstream_evidence_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance,request_hash,result_hash,result_id,warnings,blockers,deferred_capabilities)
FINAL_RESULT_INPUT_TO_SCHEMA_COVERAGE_COUNT=31
FINAL_RESULT_UNBOUND_FIELD_COUNT=0
FINAL_RESULT_DERIVATION_RULE_COUNT=8
FINAL_RESULT_DERIVATION_RULES=(demo_id_from_N10,release_version_from_N10,source_identity_from_N10,statuses_from_N07,warnings_blockers_deferred_from_N10,result_hash_from_N11_prehash,result_id_from_N11_result_hash,late_evidence_fields_from_completed_N12_to_N18)
```

```text
FINAL_RESULT_DERIVATION_01|FIELD=demo_id|DERIVATION_RULE=frozen success demo identifier|DERIVATION_INPUTS=DEMO_SUCCESS_001|DERIVATION_STAGE=S14
FINAL_RESULT_DERIVATION_02|FIELD=release_version|DERIVATION_RULE=frozen TARGET_DISTRIBUTION_VERSION 0.3.0|DERIVATION_INPUTS=FROZEN_SOURCE_R5|DERIVATION_STAGE=S14
FINAL_RESULT_DERIVATION_03|FIELD=source_commit,source_tree|DERIVATION_RULE=frozen origin/main identity|DERIVATION_INPUTS=EXPECTED_ORIGIN_MAIN_SHA,EXPECTED_ORIGIN_MAIN_TREE|DERIVATION_STAGE=S14
FINAL_RESULT_DERIVATION_04|FIELD=task031_status,task032_status,task033_status,task034_status,task035_status|DERIVATION_RULE=ordered status projection from complete public graph evidence|DERIVATION_INPUTS=N07|DERIVATION_STAGE=S12
FINAL_RESULT_DERIVATION_05|FIELD=warnings,blockers,deferred_capabilities|DERIVATION_RULE=closed success projection from release input bundle|DERIVATION_INPUTS=N10|DERIVATION_STAGE=S14
FINAL_RESULT_DERIVATION_06|FIELD=result_hash|DERIVATION_RULE=SHA-256 of exact N11 success prehash canonical bytes|DERIVATION_INPUTS=N11 prehash fields|DERIVATION_STAGE=S15
FINAL_RESULT_DERIVATION_07|FIELD=result_id|DERIVATION_RULE=UUIDv5(namespace,prefix + TASK036_SUCCESS_RESULT + ":" + lowercase result_hash)|DERIVATION_INPUTS=N11.result_hash|DERIVATION_STAGE=S15
FINAL_RESULT_DERIVATION_08|FIELD=release_acceptance_ledger,determinism_evidence,artifact_manifest_digest,version_metadata_digest,acceptance_checklist,provenance|DERIVATION_RULE=direct completed-node handoff with no N11 prehash participation|DERIVATION_INPUTS=N12,N13,N14,N15,N16,N17,N18|DERIVATION_STAGE=S22
```

Each final-result field has one explicit handoff record. `PREHASH=true` means
that the field participates in the N11 success identity core; `LATE=true`
means that the field is attached only after its producer node is complete and
is excluded by the explicit N11 exclusion list.

```text
FINAL_RESULT_FIELD_01|FIELD=schema_version|SOURCE_NODE=N11|SOURCE_STAGE=S15|HANDOFF_FIELD=schema_version|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_02|FIELD=profile_id|SOURCE_NODE=N11|SOURCE_STAGE=S15|HANDOFF_FIELD=profile_id|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_03|FIELD=implementation_software_version|SOURCE_NODE=N11|SOURCE_STAGE=S15|HANDOFF_FIELD=implementation_software_version|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_04|FIELD=demo_id|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=demo_id|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_05|FIELD=release_version|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=release_version|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_06|FIELD=source_commit|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=source_commit|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_07|FIELD=source_tree|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=source_tree|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_08|FIELD=task031_status|SOURCE_NODE=N07|SOURCE_STAGE=S12|HANDOFF_FIELD=task031_status|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_09|FIELD=task032_status|SOURCE_NODE=N07|SOURCE_STAGE=S12|HANDOFF_FIELD=task032_status|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_10|FIELD=task033_status|SOURCE_NODE=N07|SOURCE_STAGE=S12|HANDOFF_FIELD=task033_status|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_11|FIELD=task034_status|SOURCE_NODE=N07|SOURCE_STAGE=S12|HANDOFF_FIELD=task034_status|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_12|FIELD=task035_status|SOURCE_NODE=N07|SOURCE_STAGE=S12|HANDOFF_FIELD=task035_status|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_13|FIELD=task034_request_hash|SOURCE_NODE=N05|SOURCE_STAGE=S09|HANDOFF_FIELD=task034_request_hash|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_14|FIELD=task034_result_hash|SOURCE_NODE=N05|SOURCE_STAGE=S09|HANDOFF_FIELD=task034_result_hash|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_15|FIELD=task034_result_id|SOURCE_NODE=N05|SOURCE_STAGE=S09|HANDOFF_FIELD=task034_result_id|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_16|FIELD=task035_request_hash|SOURCE_NODE=N06|SOURCE_STAGE=S11|HANDOFF_FIELD=task035_request_hash|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_17|FIELD=task035_result_hash|SOURCE_NODE=N06|SOURCE_STAGE=S11|HANDOFF_FIELD=task035_result_hash|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_18|FIELD=task035_result_id|SOURCE_NODE=N06|SOURCE_STAGE=S11|HANDOFF_FIELD=task035_result_id|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_19|FIELD=release_acceptance_ledger|SOURCE_NODE=N16|SOURCE_STAGE=S19|HANDOFF_FIELD=ledger_record|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_20|FIELD=upstream_evidence_ledger|SOURCE_NODE=N08|SOURCE_STAGE=S13|HANDOFF_FIELD=ledger_record|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_21|FIELD=determinism_evidence|SOURCE_NODE=N12,N13|SOURCE_STAGE=S16|HANDOFF_FIELD=evidence_records|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_22|FIELD=artifact_manifest_digest|SOURCE_NODE=N15|SOURCE_STAGE=S18|HANDOFF_FIELD=manifest_hash|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_23|FIELD=version_metadata_digest|SOURCE_NODE=N18|SOURCE_STAGE=S21|HANDOFF_FIELD=metadata_hash|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_24|FIELD=acceptance_checklist|SOURCE_NODE=N14|SOURCE_STAGE=S17|HANDOFF_FIELD=checklist_record|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_25|FIELD=provenance|SOURCE_NODE=N17|SOURCE_STAGE=S20|HANDOFF_FIELD=provenance_record|IDENTITY_PARTICIPATION=FINAL_EVIDENCE_ATTACHMENT|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=true
FINAL_RESULT_FIELD_26|FIELD=request_hash|SOURCE_NODE=N01|SOURCE_STAGE=S01|HANDOFF_FIELD=request_hash|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_27|FIELD=result_hash|SOURCE_NODE=N11|SOURCE_STAGE=S15|HANDOFF_FIELD=result_hash|IDENTITY_PARTICIPATION=OUTPUT_IDENTITY|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=false
FINAL_RESULT_FIELD_28|FIELD=result_id|SOURCE_NODE=N11|SOURCE_STAGE=S15|HANDOFF_FIELD=result_id|IDENTITY_PARTICIPATION=OUTPUT_IDENTITY|PREHASH_PARTICIPATION=false|PREHASH=false|LATE=false
FINAL_RESULT_FIELD_29|FIELD=warnings|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=warnings|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_30|FIELD=blockers|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=blockers|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_31|FIELD=deferred_capabilities|SOURCE_NODE=N10|SOURCE_STAGE=S14|HANDOFF_FIELD=deferred_capabilities|IDENTITY_PARTICIPATION=SUCCESS_PREHASH|PREHASH_PARTICIPATION=true|PREHASH=true|LATE=false
FINAL_RESULT_FIELD_COUNT=31
FINAL_RESULT_FIELD_UNIQUE_COUNT=31
FINAL_RESULT_FIELD_PREHASH_TRUE_COUNT=23
FINAL_RESULT_FIELD_PREHASH_FALSE_COUNT=8
FINAL_RESULT_FIELD_LATE_TRUE_COUNT=6
```

### 25.4 Canonical identity and release-evidence boundaries

The canonical frame remains the frozen Task036 frame. The correction only
assigns every hashed record an exact kind tag and gives each record a forward
construction boundary.

```text
TASK036_CANONICAL_FRAME=(namespace,canonical_kind_tag,ordered_field_projection)
TASK036_CANONICAL_FIELD_PROJECTION=[[field_name,normalized_value],...]
TASK036_CANONICAL_ENCODING=json.dumps(frame,ensure_ascii=False,separators=(",",":"),sort_keys=true,allow_nan=false).encode("utf-8")
TASK036_CANONICAL_HASH_ALGORITHM=SHA-256
TASK036_CANONICAL_STRING_ENCODING=UTF-8
TASK036_CANONICAL_DECIMAL_RULE=producer-owned canonical decimal string; Task036 does not recalculate engineering decimals
TASK036_CANONICAL_TUPLE_RULE=JSON array in declared producer order
TASK036_CANONICAL_MAPPING_RULE=declared field-pair list; mapping insertion order is not identity
TASK036_CANONICAL_SET_RULE=forbidden
TASK036_CANONICAL_FLOAT_RULE=forbidden in semantic input and result projections

TASK036_DEMO_INPUT_HASH_NAMESPACE=task036.demo-input.v1
TASK036_SUCCESS_RESULT_HASH_NAMESPACE=task036.success-result.v1
TASK036_TYPED_BLOCKED_RESULT_HASH_NAMESPACE=task036.typed-blocked-result.v1
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=task036.raw-boundary-blocked-result.v1
TASK036_RELEASE_ACCEPTANCE_LEDGER_HASH_NAMESPACE=task036.release-acceptance-ledger.v1
TASK036_UPSTREAM_EVIDENCE_LEDGER_HASH_NAMESPACE=task036.upstream-evidence-ledger.v1
TASK036_ACCEPTANCE_CHECKLIST_HASH_NAMESPACE=task036.acceptance-checklist.v1
TASK036_PROVENANCE_HASH_NAMESPACE=task036.provenance.v1
TASK036_MANIFEST_HASH_NAMESPACE=task036.manifest.v1
TASK036_VERSION_METADATA_HASH_NAMESPACE=task036.version-metadata.v1
TASK036_DETERMINISM_EVIDENCE_HASH_NAMESPACE=task036.determinism-evidence.v1
TASK036_RAW_PROJECTION_NAMESPACE=task036.raw-projection.v1

TASK036_RESULT_ID_NAMESPACE=97db5e70-af4c-58e1-8bf0-d16005aedf12
TASK036_RESULT_ID_NAMESPACE_SOURCE=uuid.uuid5(uuid.NAMESPACE_URL,"hxforge-agent/task036/shell-side-thermal-hydraulic-integration-release-acceptance/v1")
TASK036_RESULT_ID_PREFIX=task036-shell-side-thermal-hydraulic-integration-release-acceptance-id.v1:
TASK036_RESULT_ID_ALGORITHM=uuid.uuid5(TASK036_RESULT_ID_NAMESPACE,TASK036_RESULT_ID_PREFIX + result_kind_tag + ":" + result_hash.lower())
TASK036_RESULT_ID_PREIMAGE_FIELDS=(result_kind_tag,result_hash)
TASK036_RESULT_ID_RESULT_KIND_TAGS=(TASK036_SUCCESS_RESULT,TASK036_TYPED_BLOCKED_RESULT)
TASK036_RESULT_ID_UUID_VERSION=5
TASK036_RAW_BOUNDARY_RESULT_ID_PRESENT=false
```

The exact hashed-contract table is closed. The five kind tags absent from the
pre-correction table are derived mechanically from their schema namespace by
the existing Task036 uppercase underscore naming convention.

| Contract ID | Schema / namespace | Canonical kind tag | Prehash field order | Output hash field | Result ID namespace | Kind-tag source |
|---|---|---|---|---|---|---|
| `H01_DEMO_INPUT` | `task036.demo-input.v1` | `TASK036_DEMO_INPUT` | `DEMO_INPUT_FIELD_ORDER` | `request_hash` | none | `EXISTING_REPOSITORY_CONVENTION` |
| `H02_SUCCESS_RESULT` | `task036.success-result.v1` | `TASK036_SUCCESS_RESULT` | `TASK036_SUCCESS_RESULT_PREHASH_FIELDS` | `result_hash` | `97db5e70-af4c-58e1-8bf0-d16005aedf12` | `EXISTING_REPOSITORY_CONVENTION` |
| `H03_TYPED_BLOCKED_RESULT` | `task036.typed-blocked-result.v1` | `TASK036_TYPED_BLOCKED_RESULT` | `TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELDS` | `blocked_result_hash` | `97db5e70-af4c-58e1-8bf0-d16005aedf12` | `EXISTING_REPOSITORY_CONVENTION` |
| `H04_RAW_BOUNDARY_BLOCKED_RESULT` | `task036.raw-boundary-blocked-result.v1` | `TASK036_RAW_BOUNDARY_BLOCKED_RESULT` | `TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS` | `blocked_result_hash` | none | `EXISTING_REPOSITORY_CONVENTION` |
| `H05_RELEASE_ACCEPTANCE_LEDGER` | `task036.release-acceptance-ledger.v1` | `TASK036_RELEASE_ACCEPTANCE_LEDGER` | `TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS` | `ledger_hash` | none | `MECHANICAL_DERIVATION` |
| `H06_UPSTREAM_EVIDENCE_LEDGER` | `task036.upstream-evidence-ledger.v1` | `TASK036_UPSTREAM_EVIDENCE_LEDGER` | `TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS` | `ledger_hash` | none | `MECHANICAL_DERIVATION` |
| `H07_ACCEPTANCE_CHECKLIST` | `task036.acceptance-checklist.v1` | `TASK036_ACCEPTANCE_CHECKLIST` | `TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELDS` | `checklist_hash` | none | `MECHANICAL_DERIVATION` |
| `H08_PROVENANCE` | `task036.provenance.v1` | `TASK036_PROVENANCE` | `TASK036_PROVENANCE_PREHASH_FIELDS` | `provenance_hash` | none | `EXISTING_REPOSITORY_CONVENTION` |
| `H09_MANIFEST` | `task036.manifest.v1` | `TASK036_MANIFEST` | `TASK036_MANIFEST_PREHASH_FIELDS` | `manifest_hash` | none | `MECHANICAL_DERIVATION` |
| `H10_VERSION_METADATA` | `task036.version-metadata.v1` | `TASK036_VERSION_METADATA` | `TASK036_VERSION_METADATA_PREHASH_FIELDS` | `metadata_hash` | none | `MECHANICAL_DERIVATION` |
| `H11_DETERMINISM_EVIDENCE` | `task036.determinism-evidence.v1` | `TASK036_DETERMINISM_EVIDENCE` | `TASK036_DETERMINISM_EVIDENCE_PREHASH_FIELDS` | `evidence_hash` | none | `MECHANICAL_DERIVATION` |

```text
HASHED_CONTRACT_COUNT=11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT=11
MISSING_CANONICAL_KIND_TAG_COUNT=0
DUPLICATE_CANONICAL_KIND_TAG_COUNT=0
TASK036_RAW_PROJECTION_IS_NOT_A_HASHED_CONTRACT=true
KIND_TAG_DERIVATION_RULE=replace the schema namespace slug hyphens with underscores and uppercase it after the TASK036_ prefix
```

The release-evidence records use exact forward boundaries. A record's own
identity field is excluded from its prehash, and a field is late-bound only
when its producer is explicitly completed after the identity core being
finalized. Each exclusion is explicit and is not an implementation choice.

```text
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELDS=(schema_version,ledger_id,release_version,demo_id,source_commit,source_tree,required_available_capabilities,unavailable_capabilities,required_producer_statuses,required_producer_identities,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,upstream_evidence_refs,artifact_manifest_digest,determinism_evidence_digest,acceptance_checklist_digest,acceptance_status,ledger_hash)
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELD_COUNT=22
TASK036_RELEASE_ACCEPTANCE_LEDGER_LATE_BOUND_FIELDS=NONE
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS=(schema_version,ledger_id,release_version,demo_id,source_commit,source_tree,required_available_capabilities,unavailable_capabilities,required_producer_statuses,required_producer_identities,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,upstream_evidence_refs,artifact_manifest_digest,determinism_evidence_digest,acceptance_checklist_digest,acceptance_status)
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELD_COUNT=21
TASK036_RELEASE_ACCEPTANCE_LEDGER_EXCLUDED_FROM_PREHASH=(ledger_hash)
TASK036_RELEASE_LEDGER_PREHASH_FIELDS=TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS
TASK036_RELEASE_LEDGER_POSTHASH_FIELDS=(ledger_hash)
TASK036_RELEASE_LEDGER_CYCLE_COUNT=0

TASK036_UPSTREAM_EVIDENCE_LEDGER_FIELD_COUNT=26
TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELD_COUNT=25
TASK036_UPSTREAM_EVIDENCE_LEDGER_EXCLUDED_FROM_PREHASH=(ledger_hash)
TASK036_ACCEPTANCE_CHECKLIST_FIELD_COUNT=14
TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELD_COUNT=13
TASK036_ACCEPTANCE_CHECKLIST_EXCLUDED_FROM_PREHASH=(checklist_hash)
TASK036_MANIFEST_FIELD_COUNT=13
TASK036_MANIFEST_PREHASH_FIELD_COUNT=12
TASK036_MANIFEST_EXCLUDED_FROM_PREHASH=(manifest_hash)
TASK036_VERSION_METADATA_FIELD_COUNT=17
TASK036_VERSION_METADATA_PREHASH_FIELD_COUNT=16
TASK036_VERSION_METADATA_EXCLUDED_FROM_PREHASH=(metadata_hash)
TASK036_VERSION_METADATA_POST_RESULT_FIELDS=NONE
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_SOURCE=N16.ledger_hash
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_FORMAT="sha256:" + N16.ledger_hash
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_PARTICIPATION=VERSION_METADATA_PREHASH
TASK036_VERSION_METADATA_RELEASE_ACCEPTANCE_RESULT_ID_IS_POST_RESULT=false
TASK036_VERSION_METADATA_CYCLE_COUNT=0
TASK036_PROVENANCE_FIELD_COUNT=26
TASK036_PROVENANCE_PREHASH_FIELD_COUNT=25
TASK036_PROVENANCE_EXCLUDED_FROM_PREHASH=(provenance_hash)
```

### 25.5 Topological identity/dataflow edge contract

The following edge list is the complete corrected dataflow. Each edge names
the value transfer, the producer identity binding, and the stage at which the
consumer receives it.

```text
E01|FROM=N00_RAW_DEMO_INPUT|TO=N01_DEMO_INPUT|VALUE_OR_IDENTITY_TRANSFER=raw projection fields|PRODUCER_IDENTITY_BINDING=caller-owned raw boundary|CONSUMER_STAGE=S01
E02|FROM=N01_DEMO_INPUT|TO=N02_TASK031_RESULT|VALUE_OR_IDENTITY_TRANSFER=Task031 request record|PRODUCER_IDENTITY_BINDING=N01.request_hash|CONSUMER_STAGE=S03
E03|FROM=N01_DEMO_INPUT|TO=N03_TASK032_RESULT|VALUE_OR_IDENTITY_TRANSFER=property and mass-flow authority fields|PRODUCER_IDENTITY_BINDING=N01.request_hash|CONSUMER_STAGE=S05
E04|FROM=N02_TASK031_RESULT|TO=N03_TASK032_RESULT|VALUE_OR_IDENTITY_TRANSFER=Task031 geometry identity|PRODUCER_IDENTITY_BINDING=N02 public result identity|CONSUMER_STAGE=S05
E05|FROM=N03_TASK032_RESULT|TO=N04_TASK033_RESULT|VALUE_OR_IDENTITY_TRANSFER=Task032 result and authority identity|PRODUCER_IDENTITY_BINDING=N03 public result identity|CONSUMER_STAGE=S07
E06|FROM=N04_TASK033_RESULT|TO=N05_TASK034_RESULT|VALUE_OR_IDENTITY_TRANSFER=Task033 result and caller authority context|PRODUCER_IDENTITY_BINDING=N04 public result identity|CONSUMER_STAGE=S09
E07|FROM=N05_TASK034_RESULT|TO=N06_TASK035_RESULT|VALUE_OR_IDENTITY_TRANSFER=Task034 v2 result envelope|PRODUCER_IDENTITY_BINDING=N05 request/result identity|CONSUMER_STAGE=S11
E08|FROM=N06_TASK035_RESULT|TO=N07_PRODUCTION_GRAPH_EVIDENCE|VALUE_OR_IDENTITY_TRANSFER=Task035 public result status and identity|PRODUCER_IDENTITY_BINDING=N06 producer identity|CONSUMER_STAGE=S12
E09|FROM=N07_PRODUCTION_GRAPH_EVIDENCE|TO=N08_UPSTREAM_EVIDENCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=ordered public graph evidence|PRODUCER_IDENTITY_BINDING=N07 graph evidence|CONSUMER_STAGE=S13
E10|FROM=N07_PRODUCTION_GRAPH_EVIDENCE|TO=N09_BLOCKED_CASES_EVIDENCE|VALUE_OR_IDENTITY_TRANSFER=actual producer branch evidence|PRODUCER_IDENTITY_BINDING=N07 graph evidence|CONSUMER_STAGE=S13
E11|FROM=N06_TASK035_RESULT|TO=N08_UPSTREAM_EVIDENCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=Task035 delivery and result evidence|PRODUCER_IDENTITY_BINDING=N06 request/result identity|CONSUMER_STAGE=S13
E12|FROM=N06_TASK035_RESULT|TO=N09_BLOCKED_CASES_EVIDENCE|VALUE_OR_IDENTITY_TRANSFER=Task035 blocked branch evidence|PRODUCER_IDENTITY_BINDING=N06 producer identity|CONSUMER_STAGE=S13
E13|FROM=N06_TASK035_RESULT|TO=N10_RELEASE_INPUT_BUNDLE|VALUE_OR_IDENTITY_TRANSFER=Task035 status and identity|PRODUCER_IDENTITY_BINDING=N06 producer identity|CONSUMER_STAGE=S14
E14|FROM=N07_PRODUCTION_GRAPH_EVIDENCE|TO=N10_RELEASE_INPUT_BUNDLE|VALUE_OR_IDENTITY_TRANSFER=complete graph evidence|PRODUCER_IDENTITY_BINDING=N07 graph identity|CONSUMER_STAGE=S14
E15|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N10_RELEASE_INPUT_BUNDLE|VALUE_OR_IDENTITY_TRANSFER=upstream evidence ledger|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S14
E16|FROM=N09_BLOCKED_CASES_EVIDENCE|TO=N10_RELEASE_INPUT_BUNDLE|VALUE_OR_IDENTITY_TRANSFER=B01-B06 closed evidence|PRODUCER_IDENTITY_BINDING=N09 artifact digest|CONSUMER_STAGE=S14
E17|FROM=N10_RELEASE_INPUT_BUNDLE|TO=N11_SUCCESS_IDENTITY_CORE|VALUE_OR_IDENTITY_TRANSFER=complete pre-result input projection|PRODUCER_IDENTITY_BINDING=N10 closed bundle|CONSUMER_STAGE=S15
E18|FROM=N06_TASK035_RESULT|TO=N11_SUCCESS_IDENTITY_CORE|VALUE_OR_IDENTITY_TRANSFER=Task035 request/result identities|PRODUCER_IDENTITY_BINDING=N06 producer identity|CONSUMER_STAGE=S15
E19|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N11_SUCCESS_IDENTITY_CORE|VALUE_OR_IDENTITY_TRANSFER=upstream evidence ledger|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S15
E20|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N12_CROSS_RUNTIME_DETERMINISM|VALUE_OR_IDENTITY_TRANSFER=success canonical bytes, result_hash, result_id|PRODUCER_IDENTITY_BINDING=N11 result identity|CONSUMER_STAGE=S16
E21|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N13_REPEAT_RUN_DETERMINISM|VALUE_OR_IDENTITY_TRANSFER=success canonical bytes, result_hash, result_id|PRODUCER_IDENTITY_BINDING=N11 result identity|CONSUMER_STAGE=S16
E22|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N14_ACCEPTANCE_CHECKLIST|VALUE_OR_IDENTITY_TRANSFER=upstream evidence status|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S17
E23|FROM=N09_BLOCKED_CASES_EVIDENCE|TO=N14_ACCEPTANCE_CHECKLIST|VALUE_OR_IDENTITY_TRANSFER=blocked test inventory evidence|PRODUCER_IDENTITY_BINDING=N09 artifact digest|CONSUMER_STAGE=S17
E24|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N14_ACCEPTANCE_CHECKLIST|VALUE_OR_IDENTITY_TRANSFER=success identity and capability status|PRODUCER_IDENTITY_BINDING=N11 result identity|CONSUMER_STAGE=S17
E25|FROM=N12_CROSS_RUNTIME_DETERMINISM|TO=N14_ACCEPTANCE_CHECKLIST|VALUE_OR_IDENTITY_TRANSFER=cross-runtime evidence status|PRODUCER_IDENTITY_BINDING=N12.evidence_hash|CONSUMER_STAGE=S17
E26|FROM=N13_REPEAT_RUN_DETERMINISM|TO=N14_ACCEPTANCE_CHECKLIST|VALUE_OR_IDENTITY_TRANSFER=repeat-run evidence status|PRODUCER_IDENTITY_BINDING=N13.evidence_hash|CONSUMER_STAGE=S17
E27|FROM=N01_DEMO_INPUT|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=demo input artifact path and semantic digest|PRODUCER_IDENTITY_BINDING=N01.request_hash|CONSUMER_STAGE=S18
E28|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=upstream ledger artifact path and digest|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S18
E29|FROM=N09_BLOCKED_CASES_EVIDENCE|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=blocked-case artifact path and digest|PRODUCER_IDENTITY_BINDING=N09 artifact digest|CONSUMER_STAGE=S18
E30|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=canonical identity and success semantic digest|PRODUCER_IDENTITY_BINDING=N11.result_hash|CONSUMER_STAGE=S18
E31|FROM=N12_CROSS_RUNTIME_DETERMINISM|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=cross-runtime artifact path and digest|PRODUCER_IDENTITY_BINDING=N12.evidence_hash|CONSUMER_STAGE=S18
E32|FROM=N13_REPEAT_RUN_DETERMINISM|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=repeat artifact path and digest|PRODUCER_IDENTITY_BINDING=N13.evidence_hash|CONSUMER_STAGE=S18
E33|FROM=N14_ACCEPTANCE_CHECKLIST|TO=N15_MANIFEST|VALUE_OR_IDENTITY_TRANSFER=checklist path and digest|PRODUCER_IDENTITY_BINDING=N14.checklist_hash|CONSUMER_STAGE=S18
E34|FROM=N15_MANIFEST|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=manifest digest|PRODUCER_IDENTITY_BINDING=N15.manifest_hash|CONSUMER_STAGE=S19
E35|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=upstream ledger identity|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S19
E36|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=producer identities and success identity|PRODUCER_IDENTITY_BINDING=N11.result_hash,N11.result_id|CONSUMER_STAGE=S19
E37|FROM=N12_CROSS_RUNTIME_DETERMINISM|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=determinism evidence digest|PRODUCER_IDENTITY_BINDING=N12.evidence_hash|CONSUMER_STAGE=S19
E38|FROM=N13_REPEAT_RUN_DETERMINISM|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=repeat evidence digest|PRODUCER_IDENTITY_BINDING=N13.evidence_hash|CONSUMER_STAGE=S19
E39|FROM=N14_ACCEPTANCE_CHECKLIST|TO=N16_RELEASE_ACCEPTANCE_LEDGER|VALUE_OR_IDENTITY_TRANSFER=checklist digest|PRODUCER_IDENTITY_BINDING=N14.checklist_hash|CONSUMER_STAGE=S19
E40|FROM=N15_MANIFEST|TO=N17_PROVENANCE|VALUE_OR_IDENTITY_TRANSFER=manifest digest and closed artifact refs|PRODUCER_IDENTITY_BINDING=N15.manifest_hash|CONSUMER_STAGE=S20
E41|FROM=N16_RELEASE_ACCEPTANCE_LEDGER|TO=N17_PROVENANCE|VALUE_OR_IDENTITY_TRANSFER=release evidence ledger hash|PRODUCER_IDENTITY_BINDING=N16.ledger_hash|CONSUMER_STAGE=S20
E42|FROM=N14_ACCEPTANCE_CHECKLIST|TO=N17_PROVENANCE|VALUE_OR_IDENTITY_TRANSFER=checklist digest|PRODUCER_IDENTITY_BINDING=N14.checklist_hash|CONSUMER_STAGE=S20
E43|FROM=N06_TASK035_RESULT|TO=N17_PROVENANCE|VALUE_OR_IDENTITY_TRANSFER=Task035 producer edge identity|PRODUCER_IDENTITY_BINDING=N06 request/result identity|CONSUMER_STAGE=S20
E44|FROM=N11_SUCCESS_IDENTITY_CORE|TO=N17_PROVENANCE|VALUE_OR_IDENTITY_TRANSFER=Task036 result identity|PRODUCER_IDENTITY_BINDING=N11.result_hash,N11.result_id|CONSUMER_STAGE=S20
E45|FROM=N15_MANIFEST|TO=N18_VERSION_METADATA|VALUE_OR_IDENTITY_TRANSFER=manifest digest and artifact identity set|PRODUCER_IDENTITY_BINDING=N15.manifest_hash|CONSUMER_STAGE=S21
E46|FROM=N16_RELEASE_ACCEPTANCE_LEDGER|TO=N18_VERSION_METADATA|VALUE_OR_IDENTITY_TRANSFER=release ledger semantic digest|PRODUCER_IDENTITY_BINDING=N16.ledger_hash|CONSUMER_STAGE=S21
E47|FROM=N17_PROVENANCE|TO=N18_VERSION_METADATA|VALUE_OR_IDENTITY_TRANSFER=provenance semantic digest|PRODUCER_IDENTITY_BINDING=N17.provenance_hash|CONSUMER_STAGE=S21
E48|FROM=N16_RELEASE_ACCEPTANCE_LEDGER|TO=N18_VERSION_METADATA|VALUE_OR_IDENTITY_TRANSFER=release acceptance result ID|PRODUCER_IDENTITY_BINDING=N16.ledger_hash with frozen sha256: prefix|CONSUMER_STAGE=S21
E49|FROM=N18_VERSION_METADATA|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=version metadata digest|PRODUCER_IDENTITY_BINDING=N18.metadata_hash|CONSUMER_STAGE=S22
E50|FROM=N17_PROVENANCE|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=completed provenance record|PRODUCER_IDENTITY_BINDING=N17.provenance_hash|CONSUMER_STAGE=S22
E51|FROM=N16_RELEASE_ACCEPTANCE_LEDGER|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=completed release ledger|PRODUCER_IDENTITY_BINDING=N16.ledger_hash|CONSUMER_STAGE=S22
E52|FROM=N15_MANIFEST|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=manifest digest|PRODUCER_IDENTITY_BINDING=N15.manifest_hash|CONSUMER_STAGE=S22
E53|FROM=N14_ACCEPTANCE_CHECKLIST|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=completed checklist|PRODUCER_IDENTITY_BINDING=N14.checklist_hash|CONSUMER_STAGE=S22
E54|FROM=N12_CROSS_RUNTIME_DETERMINISM|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=cross-runtime evidence|PRODUCER_IDENTITY_BINDING=N12.evidence_hash|CONSUMER_STAGE=S22
E55|FROM=N13_REPEAT_RUN_DETERMINISM|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=repeat-run evidence|PRODUCER_IDENTITY_BINDING=N13.evidence_hash|CONSUMER_STAGE=S22
E56|FROM=N08_UPSTREAM_EVIDENCE_LEDGER|TO=N19_FINAL_ACCEPTANCE_RESULT|VALUE_OR_IDENTITY_TRANSFER=upstream evidence ledger|PRODUCER_IDENTITY_BINDING=N08.ledger_hash|CONSUMER_STAGE=S22
```

```text
TASK036_EXECUTABLE_DATAFLOW_EDGE_COUNT=56
STAGE_DATAFLOW_EDGE_COUNT=56
STAGE_DATAFLOW_FORWARD_EDGE_COUNT=56
STAGE_DATAFLOW_BACKWARD_EDGE_COUNT=0
FORWARD_REFERENCE_COUNT=0
CIRCULAR_PREHASH_REFERENCE_COUNT=0
RESULT_ID_USED_BEFORE_DERIVATION_COUNT=0
```

### 25.6 Corrected provenance tail and identity handoff

The five upstream producer edges retain the six-field producer-edge record.
The release-evidence tail is an aggregation edge, not a result-like producer.
This is the mechanically derived D19 boundary for a release ledger that has a
ledger hash but no Task036 result ID.

```text
TASK036_PROVENANCE_NODE_SET=(TASK031,TASK032,TASK033,TASK034,TASK035,TASK036_RELEASE_EVIDENCE,TASK036_ACCEPTANCE_RESULT)
TASK036_PROVENANCE_EDGE_SET=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE,TASK036_RELEASE_EVIDENCE->TASK036_ACCEPTANCE_RESULT)
TASK036_PROVENANCE_EDGE_COUNT=6
TASK036_PROVENANCE_SELF_EDGE_COUNT=0
TASK036_PROVENANCE_HIDDEN_NODE_COUNT=0
TASK036_PROVENANCE_HISTORICAL_PR202_CURRENT_PRODUCER=false
TASK036_PROVENANCE_UPSTREAM_IDENTITY_ORDER=(TASK031,TASK032,TASK033,TASK034,TASK035)
TASK036_PROVENANCE_EDGE_ORDER=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE,TASK036_RELEASE_EVIDENCE->TASK036_ACCEPTANCE_RESULT)

TASK036_UPSTREAM_PRODUCER_EDGE_FIELDS=(producer_task,consumer_task,producer_request_hash,producer_result_hash,producer_result_id,producer_status)
TASK036_UPSTREAM_PRODUCER_EDGE_FIELD_ORDER=(TASK031->TASK032,TASK032->TASK033,TASK033->TASK034,TASK034->TASK035,TASK035->TASK036_RELEASE_EVIDENCE)
TASK036_RELEASE_AGGREGATION_EDGE_FIELDS=(producer_task,consumer_task,producer_evidence_hash,producer_status)
TASK036_RELEASE_AGGREGATION_EDGE_VALUE=(TASK036_RELEASE_EVIDENCE,TASK036_ACCEPTANCE_RESULT,N16.ledger_hash,VALID)
TASK036_RELEASE_EVIDENCE_NODE_CONTRACT=NON_RESULT_AGGREGATION_EDGE
TASK036_RELEASE_EVIDENCE_IDENTITY_CONTRACT=NON_RESULT_AGGREGATION_EDGE
RELEASE_EVIDENCE_IDENTITY_CONTRACT=NON_RESULT_AGGREGATION_EDGE
TASK036_RELEASE_EVIDENCE_HAS_REQUEST_HASH=false
TASK036_RELEASE_EVIDENCE_HAS_RESULT_HASH=false
TASK036_RELEASE_EVIDENCE_HAS_RESULT_ID=false
TASK036_RELEASE_EVIDENCE_NO_FAKE_REQUEST_HASH=true
TASK036_RELEASE_EVIDENCE_NO_FAKE_RESULT_HASH=true
TASK036_RELEASE_EVIDENCE_NO_FAKE_RESULT_ID=true
TASK036_PROVENANCE_UNBOUND_EDGE_IDENTITY_COUNT=0
TASK036_CURRENT_TASK035_V2_AS_CURRENT_PRODUCER=true
TASK036_HISTORICAL_TASK035_V1_AS_CURRENT_PRODUCER=false
```

### 25.7 HISTORICAL_SUPERSEDED — R2 artifact topology and digest layers

Historical R2 authority only; this subsection is superseded by Section 27.1.
The artifact inventory in this historical snapshot remains exactly eleven paths. A manifest path reference
to a later artifact is a closed path declaration, not a content dependency.
The table distinguishes an artifact's semantic digest producer from the stage
that finalizes its output bytes. Only the eight semantic digests listed below
enter the manifest prehash; the release ledger, provenance, and version
metadata are later evidence layers.

| Artifact ID | Exact path | Producer stage | Producer node | Final bytes stage | Final bytes node | Consumer stages | Required input nodes | Hash input | Identity dependency |
|---|---|---:|---|---:|---|---|---|---|---|
| `TASK036_DEMO_INPUT` | `artifacts/task036/v0.3/task036_demo_input.json` | S01 | N01 | S01 | N01 | S02,S18 | N01 | N01.request_hash | demo input hash |
| `TASK036_DEMO_OUTPUT` | `artifacts/task036/v0.3/task036_demo_output.json` | S15 | N11 | S22 | N19 | NONE (terminal) | N11 | N11.result_hash as semantic digest | final envelope identity carried from N11 |
| `TASK036_BLOCKED_CASES` | `artifacts/task036/v0.3/task036_blocked_cases.json` | S13 | N09 | S13 | N09 | S17,S18 | N07,N06 | artifact SHA-256 | B01–B06 producer evidence |
| `TASK036_CANONICAL_IDENTITY` | `artifacts/task036/v0.3/task036_canonical_identity.json` | S15 | N11 | S15 | N11 | S16,S18 | N10,N06,N08 | N11.result_hash | success result identity core |
| `TASK036_CROSS_PYTHON_DETERMINISM` | `artifacts/task036/v0.3/task036_cross_python_determinism.json` | S16 | N12 | S16 | N12 | S18,S19,S22 | N11 | N12.evidence_hash | final canonical/hash/ID comparison |
| `TASK036_REPEAT_RUN_DETERMINISM` | `artifacts/task036/v0.3/task036_repeat_run_determinism.json` | S16 | N13 | S16 | N13 | S18,S19,S22 | N11 | N13.evidence_hash | final canonical/hash/ID comparison |
| `TASK036_UPSTREAM_EVIDENCE_LEDGER` | `artifacts/task036/v0.3/task036_upstream_evidence_ledger.json` | S13 | N08 | S13 | N08 | S14,S17,S18,S19,S22 | N07,N06 | N08.ledger_hash | upstream evidence identity |
| `TASK036_RELEASE_ACCEPTANCE_LEDGER` | `artifacts/task036/v0.3/task036_release_acceptance_ledger.json` | S19 | N16 | S19 | N16 | S20,S21,S22 | N08,N11,N12,N13,N14,N15 | N16.ledger_hash | release evidence identity |
| `TASK036_ACCEPTANCE_CHECKLIST` | `artifacts/task036/v0.3/task036_acceptance_checklist.json` | S17 | N14 | S17 | N14 | S18,S19,S22 | N08,N09,N11,N12,N13 | N14.checklist_hash | checklist identity |
| `TASK036_MANIFEST` | `artifacts/task036/v0.3/task036_manifest.json` | S18 | N15 | S18 | N15 | S19,S20,S21,S22 | N01,N08,N09,N11,N12,N13,N14 | N15.manifest_hash | closed artifact inventory identity |
| `TASK036_VERSION_METADATA` | `artifacts/task036/v0.3/task036_version_metadata.json` | S21 | N18 | S21 | N18 | S22 | N11,N15,N16,N17 | N18.metadata_hash | version metadata identity |

```text
TASK036_ARTIFACT_INVENTORY_COUNT=11
TASK036_ARTIFACT_INVENTORY_CLOSED=true
TASK036_ARTIFACT_ROOT=artifacts/task036/v0.3
TASK036_ARTIFACT_ID_ORDER=(TASK036_DEMO_INPUT,TASK036_DEMO_OUTPUT,TASK036_BLOCKED_CASES,TASK036_CANONICAL_IDENTITY,TASK036_CROSS_PYTHON_DETERMINISM,TASK036_REPEAT_RUN_DETERMINISM,TASK036_UPSTREAM_EVIDENCE_LEDGER,TASK036_RELEASE_ACCEPTANCE_LEDGER,TASK036_ACCEPTANCE_CHECKLIST,TASK036_MANIFEST,TASK036_VERSION_METADATA)
TASK036_ARTIFACT_INVENTORY=(artifacts/task036/v0.3/task036_demo_input.json,artifacts/task036/v0.3/task036_demo_output.json,artifacts/task036/v0.3/task036_blocked_cases.json,artifacts/task036/v0.3/task036_canonical_identity.json,artifacts/task036/v0.3/task036_cross_python_determinism.json,artifacts/task036/v0.3/task036_repeat_run_determinism.json,artifacts/task036/v0.3/task036_upstream_evidence_ledger.json,artifacts/task036/v0.3/task036_release_acceptance_ledger.json,artifacts/task036/v0.3/task036_acceptance_checklist.json,artifacts/task036/v0.3/task036_manifest.json,artifacts/task036/v0.3/task036_version_metadata.json)
TASK036_ARTIFACT_DIGEST_ALGORITHM=SHA-256
TASK036_ARTIFACT_CANONICAL_ENCODING=TASK036_CANONICAL_FRAME_IN_25_4
TASK036_ARTIFACT_LAYER_ORDER=(FOUNDATION,DETERMINISM,ACCEPTANCE,FINALIZATION)
TASK036_ARTIFACT_LAYER_FOUNDATION=(TASK036_DEMO_INPUT,TASK036_BLOCKED_CASES,TASK036_UPSTREAM_EVIDENCE_LEDGER,TASK036_CANONICAL_IDENTITY)
TASK036_ARTIFACT_LAYER_DETERMINISM=(TASK036_CROSS_PYTHON_DETERMINISM,TASK036_REPEAT_RUN_DETERMINISM)
TASK036_ARTIFACT_LAYER_ACCEPTANCE=(TASK036_ACCEPTANCE_CHECKLIST,TASK036_MANIFEST,TASK036_RELEASE_ACCEPTANCE_LEDGER)
TASK036_ARTIFACT_LAYER_FINALIZATION=(TASK036_VERSION_METADATA,TASK036_DEMO_OUTPUT)
TASK036_MANIFEST_ARTIFACT_REFERENCE_COUNT=10
TASK036_MANIFEST_CONTENT_DIGEST_INPUT_ORDER=(TASK036_DEMO_INPUT,TASK036_DEMO_OUTPUT,TASK036_BLOCKED_CASES,TASK036_CANONICAL_IDENTITY,TASK036_CROSS_PYTHON_DETERMINISM,TASK036_REPEAT_RUN_DETERMINISM,TASK036_UPSTREAM_EVIDENCE_LEDGER,TASK036_ACCEPTANCE_CHECKLIST)
TASK036_MANIFEST_LATE_LAYER_PATH_REFERENCE_ORDER=(TASK036_RELEASE_ACCEPTANCE_LEDGER,TASK036_VERSION_METADATA)
TASK036_MANIFEST_DEMO_OUTPUT_DIGEST_SOURCE=N11.result_hash
TASK036_MANIFEST_PATH_REFERENCE_IS_NOT_CONTENT_DEPENDENCY=true
TASK036_DEMO_OUTPUT_SEMANTIC_PRODUCER_STAGE=S15
TASK036_DEMO_OUTPUT_SEMANTIC_PRODUCER_NODE=N11
TASK036_DEMO_OUTPUT_FINAL_BYTES_PRODUCER_STAGE=S22
TASK036_DEMO_OUTPUT_FINAL_BYTES_PRODUCER_NODE=N19
TASK036_DEMO_OUTPUT_FINAL_BYTES_IS_NOT_A_HASH_INPUT=true
TASK036_DEMO_OUTPUT_SEMANTIC_DIGEST_SOURCE=N11.result_hash
TASK036_MANIFEST_AND_METADATA_CONSUME_DEMO_OUTPUT_SEMANTIC_DIGEST_ONLY=true
TASK036_MANIFEST_AND_METADATA_DO_NOT_CONSUME_N19_OUTPUT_BYTES=true
TASK036_MANIFEST_PREHASH_INPUTS=(artifact_inventory,artifact_digest_set,source_commit,source_tree,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref)
TASK036_MANIFEST_POSTHASH_REFERENCES=NONE
TASK036_MANIFEST_LATE_BOUND_NON_SEMANTIC_FIELDS=NONE
TASK036_MANIFEST_CIRCULAR_REFERENCE_COUNT=0
TASK036_VERSION_METADATA_ARTIFACT_DIGEST_SET_ORDER=TASK036_ARTIFACT_ID_ORDER excluding TASK036_VERSION_METADATA; each value is the declared artifact semantic digest
TASK036_VERSION_METADATA_DEMO_OUTPUT_DIGEST_SOURCE=N11.result_hash
TASK036_RELEASE_LEDGER_ARTIFACT_DIGEST_DEPENDENCIES=(N15.manifest_hash,N12.evidence_hash,N13.evidence_hash,N14.checklist_hash)
TASK036_RELEASE_LEDGER_CYCLE_COUNT=0
TASK036_ARTIFACT_FORWARD_DEPENDENCY_COUNT=28
TASK036_ARTIFACT_BACKWARD_DEPENDENCY_COUNT=0
TASK036_ARTIFACT_UNDEFINED_PRODUCER_COUNT=0
TASK036_ARTIFACT_UNDEFINED_CONSUMER_INPUT_COUNT=0
TASK036_ARTIFACT_DIGEST_CYCLE_COUNT=0
TASK036_ARTIFACT_PRODUCER_STAGE_BEFORE_ALL_CONSUMERS=true
TASK036_ARTIFACT_STAGE_DATAFLOW_REVIEW=PASS
```

### 25.8 HISTORICAL_SUPERSEDED — R2 determinism protocol

Historical R2 authority only; this subsection is superseded by Section 27.6.
The determinism artifacts in this historical snapshot are produced after the success identity core exists.
The final-result canonical surface means the exact UTF-8 canonical bytes of the
N11 success prehash projection, which is the byte sequence that produces
`result_hash`. The final result ID is compared from that verified hash. The
late release-evidence attachments do not participate in the N11 prehash and
therefore cannot create a self-reference.

```text
TASK036_SUCCESS_RESULT_CANONICAL_BYTES_SOURCE=N11_SUCCESS_IDENTITY_CORE_PREHASH_BYTES
TASK036_SUCCESS_RESULT_HASH_SOURCE=N11.result_hash
TASK036_SUCCESS_RESULT_ID_SOURCE=N11.result_id
TASK036_DETERMINISM_EVIDENCE_PARTICIPATES_IN_SUCCESS_RESULT_PREHASH=false
TASK036_SUCCESS_RESULT_CORE_BUILT_BEFORE_DETERMINISM=true
TASK036_FINAL_RESULT_IDENTITY_VALIDATED_AFTER_RELEASE_EVIDENCE=true

TASK036_DETERMINISM_REPEAT_RUN_COUNT_PER_RUNTIME=2
TASK036_DETERMINISM_RUNTIME_COUNT=2
TASK036_DETERMINISM_RUNTIME_ORDER=(python3.11,python3.12)
PYTHON_3_11=true
PYTHON_3_12=true
REPEAT_RUN_DETERMINISM=true
CROSS_VERSION_BYTE_IDENTITY=true
TASK036_DETERMINISM_COMPARISON_SURFACES=(DS01,DS02,DS03,DS04,DS05,DS06,DS07,DS08,DS09)
TASK036_DETERMINISM_COMPARISON_SURFACE_COUNT=9
TASK036_DETERMINISM_CORE_SURFACES=(DS01,DS02,DS03,DS09)
TASK036_DETERMINISM_POST_BUILD_SURFACES=(DS04,DS05,DS06,DS07,DS08)
TASK036_DETERMINISM_CORE_EVIDENCE_STAGE=S16
TASK036_DETERMINISM_COMPLETE_COMPARISON_STAGE=S22
TASK036_DETERMINISM_EVIDENCE_EXCLUDED_FROM_PREHASH=(evidence_hash)
DS01|SURFACE_ID=demo_input_canonical_bytes|PRODUCER=N01/S01|CANONICAL_BYTES_OR_DIGEST=N01.canonical_bytes,N01.request_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S01|FINAL_VALIDATION_STAGE=S22
DS02|SURFACE_ID=task035_request_canonical_bytes|PRODUCER=S10/TASK035_V2_PUBLIC_REQUEST|CANONICAL_BYTES_OR_DIGEST=task035.request_canonical_bytes,task035.request_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S10|FINAL_VALIDATION_STAGE=S22
DS03|SURFACE_ID=task035_success_canonical_bytes|PRODUCER=N06/S11|CANONICAL_BYTES_OR_DIGEST=task035.success_canonical_bytes,task035.result_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S11|FINAL_VALIDATION_STAGE=S22
DS04|SURFACE_ID=task036_provenance_canonical_bytes|PRODUCER=N17/S20|CANONICAL_BYTES_OR_DIGEST=N17.canonical_bytes,N17.provenance_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S20|FINAL_VALIDATION_STAGE=S22
DS05|SURFACE_ID=release_acceptance_ledger_canonical_bytes|PRODUCER=N16/S19|CANONICAL_BYTES_OR_DIGEST=N16.canonical_bytes,N16.ledger_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S19|FINAL_VALIDATION_STAGE=S22
DS06|SURFACE_ID=acceptance_checklist_canonical_bytes|PRODUCER=N14/S17|CANONICAL_BYTES_OR_DIGEST=N14.canonical_bytes,N14.checklist_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S17|FINAL_VALIDATION_STAGE=S22
DS07|SURFACE_ID=manifest_canonical_bytes|PRODUCER=N15/S18|CANONICAL_BYTES_OR_DIGEST=N15.canonical_bytes,N15.manifest_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S18|FINAL_VALIDATION_STAGE=S22
DS08|SURFACE_ID=version_metadata_canonical_bytes|PRODUCER=N18/S21|CANONICAL_BYTES_OR_DIGEST=N18.canonical_bytes,N18.metadata_hash|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S21|FINAL_VALIDATION_STAGE=S22
DS09|SURFACE_ID=task036_success_result_canonical_bytes|PRODUCER=N11/S15|CANONICAL_BYTES_OR_DIGEST=N11.prehash_canonical_bytes,N11.result_hash,N11.result_id|REPEAT_RUN_REQUIRED=true|PY311_REQUIRED=true|PY312_REQUIRED=true|CROSS_VERSION_BYTE_IDENTITY_REQUIRED=true|AVAILABLE_STAGE=S15|FINAL_VALIDATION_STAGE=S22
TASK036_DETERMINISM_COMPARED_CANONICAL_SURFACES=(demo_input_canonical_bytes,task035_request_canonical_bytes,task035_success_canonical_bytes,task036_provenance_canonical_bytes,release_acceptance_ledger_canonical_bytes,acceptance_checklist_canonical_bytes,manifest_canonical_bytes,version_metadata_canonical_bytes,task036_success_result_canonical_bytes)
TASK036_DETERMINISM_COMPARED_DIGESTS=(demo_input_hash,task035_request_hash,task035_result_hash,task034_result_hash,task035_result_id,task036_provenance_hash,release_acceptance_ledger_hash,manifest_hash,version_metadata_hash,task036_result_hash)
TASK036_DETERMINISM_COMPARED_RESULT_IDS=(task034_result_id,task035_result_id,task036_result_id)
TASK036_DETERMINISM_COMPARED_ARTIFACTS=(task036_demo_input.json,task036_demo_output.json,task036_blocked_cases.json,task036_canonical_identity.json,task036_cross_python_determinism.json,task036_repeat_run_determinism.json,task036_upstream_evidence_ledger.json,task036_release_acceptance_ledger.json,task036_acceptance_checklist.json,task036_manifest.json,task036_version_metadata.json)
TASK036_DETERMINISM_COMPARISON_RULE=all listed bytes, lowercase SHA-256 values, and UUIDv5 values equal across two repeats on both runtimes; core evidence is captured at S16 and the complete surface is validated at S22
TASK036_FINAL_RESULT_CANONICAL_BYTES_REPEAT_RUN_COMPARE=true
TASK036_FINAL_RESULT_HASH_REPEAT_RUN_COMPARE=true
TASK036_FINAL_RESULT_ID_REPEAT_RUN_COMPARE=true
TASK036_FINAL_RESULT_CANONICAL_BYTES_CROSS_PYTHON_COMPARE=true
TASK036_FINAL_RESULT_HASH_CROSS_PYTHON_COMPARE=true
TASK036_FINAL_RESULT_ID_CROSS_PYTHON_COMPARE=true
TASK036_FINAL_RESULT_CANONICAL_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_HASH_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_ID_SURFACE_INCLUDED=true
TASK036_DETERMINISM_RELEASE_AUTHORITATIVE_ARTIFACT_COUNT=11
TASK036_DETERMINISM_RELEASE_AUTHORITATIVE_ARTIFACTS_ALL_INCLUDED=true
TASK036_FINAL_ARTIFACT_BYTE_COMPARISON_STAGE=S22
TASK036_FINAL_ARTIFACT_BYTE_COMPARISON_DOES_NOT_FEED_N11=true
TASK036_DETERMINISM_PROTOCOL_CLOSED=true
TASK036_UNSTABLE_IDENTITY_INPUT_COUNT=0
```

The determinism evidence schema remains the existing 12-field schema with its
`evidence_hash` self-excluded. Its compared-surface fields now contain the
complete final-result canonical/hash/ID set above. The two determinism
artifacts are consumed only by later release-evidence stages.

### 25.9 HISTORICAL_SUPERSEDED — R2 test authority and coverage closure

Historical R2 authority only; this subsection is superseded by Section 27.4.
The superseded D32 snapshot remains exactly 30 IDs in the existing test module.
No new test ID is introduced. The existing test contracts receive the
following assertion extensions so the corrected identity and stage rules are
machine-checked without changing the test authority count.

```text
TASK036_TEST_FILE=tests/release_demo/test_task036_v03.py
TEST_INVENTORY_CLOSED=true
TEST_ID_COUNT=30
UNIQUE_TEST_ID_COUNT=30
TEST_ID_DUPLICATE_COUNT=0
TEST_ID_UNMAPPED_COUNT=0
TASK036_TEST_ID_ORDER=(T036_D01_001_TASK035_V2_PUBLIC_BINDING,T036_D09_001_SUCCESS_PUBLIC_GRAPH,T036_D10_B01_TASK031_SCHEMA_BLOCKED,T036_D10_B02_TASK032_GEOMETRY_BLOCKED,T036_D10_B03_TASK033_FLOW_BLOCKED,T036_D10_B04_TASK034_SHELL_PASS_BLOCKED,T036_D10_B05_TASK034_IDENTITY_BLOCKED,T036_D10_B06_TASK035_RAW_BOUNDARY_BLOCKED,T036_D20_001_DEMO_INPUT_SCHEMA_EXACT,T036_D20_002_TASK032_RAW_LIST_ONLY,T036_D20_003_TASK033_RAW_LIST_ONLY,T036_D20_004_TASK034_SEQUENCE_PRESERVED,T036_D20_005_TASK035_SUCCESS_REFS_CLOSED,T036_D14_001_PUBLIC_GRAPH_NO_BYPASS,T036_D15_001_NO_UPSTREAM_RECOMPUTATION,T036_D16_001_NO_FIXTURE_RESULT_SUBSTITUTION,T036_D17_001_EXPECTED_OUTPUT_NOT_INPUT,T036_D18_001_NO_SYNTHETIC_ORACLE,T036_D19_001_PROVENANCE_NO_SELF_EDGE,T036_D01_002_TASK035_WRONG_VERSION_REJECTED,T036_D11_001_BLOCKED_NOT_ZERO,T036_D07_001_RESULT_BRANCH_EXCLUSIVITY,T036_D28_001_REPEAT_RUN_DETERMINISM,T036_D29_001_PYTHON_311_EXECUTION,T036_D30_001_PYTHON_312_EXECUTION,T036_D31_001_CROSS_VERSION_BYTE_IDENTITY,T036_D23_001_MANIFEST_COMPLETE,T036_D24_001_ARTIFACT_DIGEST_VALIDATION,T036_D26_001_VERSION_METADATA_IDENTITY,T036_D34_001_RELEASE_CHECKLIST)

TEST_COVERAGE_GAP_01=acyclic identity/dataflow, zero circular prehash references, and forward stage edges -> T036_D19_001_PROVENANCE_NO_SELF_EDGE plus T036_D23_001_MANIFEST_COMPLETE
TEST_COVERAGE_GAP_02=final-result canonical bytes, result_hash, and result_id repeat/cross-runtime equality -> T036_D28_001_REPEAT_RUN_DETERMINISM plus T036_D31_001_CROSS_VERSION_BYTE_IDENTITY
TEST_COVERAGE_GAP_03=release-evidence tail edge identity and complete S22 handoff -> T036_D19_001_PROVENANCE_NO_SELF_EDGE plus T036_D34_001_RELEASE_CHECKLIST
TEST_COVERAGE_GAP_COUNT=0
TEST_COVERAGE_GAP_RESOLUTION_IS_EXISTING_ID_ASSERTION_EXTENSION=true
TEST_NEW_ID_COUNT=0
TASK036_TEST_EXECUTION_PERFORMED_IN_DESIGN_GATE=false
```

The retained ordered ID set is the frozen ID set originally enumerated in
Section 16. Its corrected assertion authority is:

```text
T036_D19_001_PROVENANCE_NO_SELF_EDGE_ASSERTS=(IDENTITY_DATAFLOW_ACYCLIC,CIRCULAR_PREHASH_REFERENCE_COUNT=0,RESULT_ID_SELF_REFERENCE_COUNT=0,PROVENANCE_UNBOUND_EDGE_IDENTITY_COUNT=0)
T036_D23_001_MANIFEST_COMPLETE_ASSERTS=(STAGE_DATAFLOW_FORWARD_EDGE_COUNT=STAGE_DATAFLOW_EDGE_COUNT,STAGE_DATAFLOW_BACKWARD_EDGE_COUNT=0,ARTIFACT_DIGEST_CYCLE_COUNT=0)
T036_D28_001_REPEAT_RUN_DETERMINISM_ASSERTS=(TASK036_FINAL_RESULT_CANONICAL_SURFACE_INCLUDED,TASK036_FINAL_RESULT_HASH_SURFACE_INCLUDED,TASK036_FINAL_RESULT_ID_SURFACE_INCLUDED)
T036_D31_001_CROSS_VERSION_BYTE_IDENTITY_ASSERTS=(TASK036_FINAL_RESULT_CANONICAL_BYTES_CROSS_PYTHON_COMPARE,TASK036_FINAL_RESULT_HASH_CROSS_PYTHON_COMPARE,TASK036_FINAL_RESULT_ID_CROSS_PYTHON_COMPARE)
T036_D34_001_RELEASE_CHECKLIST_ASSERTS=(FINAL_RESULT_INPUT_UNBOUND_FIELD_COUNT=0,PROVENANCE_UNBOUND_EDGE_IDENTITY_COUNT=0)
```

### 25.10 HISTORICAL_SUPERSEDED — R2 contract counts and preserved review-pass authority

Historical R2 authority only; this subsection is superseded by Sections 27.2,
27.3, and 27.6. The corrected schema counts are explicit. The success-result prehash boundary
is the only boundary changed by this correction. The release ledger retains all
twenty-one semantic fields in its prehash and excludes only its own
`ledger_hash`, because its digest inputs are produced before the ledger stage.

```text
SCHEMA_COUNT=12
SCHEMA_FIELD_COUNT_CONTRADICTION_COUNT=0
PREHASH_PROJECTION_CONTRADICTION_COUNT=0
DEMO_INPUT_FIELD_COUNT=9
DEMO_INPUT_PREHASH_FIELD_COUNT=9
TASK036_SUCCESS_RESULT_FIELD_COUNT=31
TASK036_SUCCESS_RESULT_PREHASH_FIELD_COUNT=23
TASK036_TYPED_BLOCKED_RESULT_FIELD_COUNT=27
TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELD_COUNT=25
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_FIELD_COUNT=8
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELD_COUNT=7
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELD_COUNT=22
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELD_COUNT=21
TASK036_UPSTREAM_EVIDENCE_LEDGER_FIELD_COUNT=26
TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELD_COUNT=25
TASK036_ACCEPTANCE_CHECKLIST_FIELD_COUNT=14
TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELD_COUNT=13
TASK036_MANIFEST_FIELD_COUNT=13
TASK036_MANIFEST_PREHASH_FIELD_COUNT=12
TASK036_VERSION_METADATA_FIELD_COUNT=17
TASK036_VERSION_METADATA_PREHASH_FIELD_COUNT=16
TASK036_PROVENANCE_FIELD_COUNT=26
TASK036_PROVENANCE_PREHASH_FIELD_COUNT=25
TASK036_DETERMINISM_EVIDENCE_FIELD_COUNT=12
TASK036_DETERMINISM_EVIDENCE_PREHASH_FIELD_COUNT=11
TASK036_RAW_PROJECTION_FIELD_COUNT=2
TASK036_RAW_PROJECTION_PREHASH_FIELD_COUNT=2

TASK036_BLOCKER_COUNT=22
TASK036_NEW_BLOCKER_COUNT=0
TASK036_CAPABILITY_TABLE_COUNT=16
TASK036_ARTIFACT_INVENTORY_COUNT=11
TASK036_SUCCESS_DEMO_COUNT=1
TASK036_BLOCKED_DEMO_COUNT=6
TASK036_DESIGN_PASS_AREAS_PRESERVED=true
TASK036_TASK035_V2_BINDING_PRESERVED=true
TASK036_TASK035_NESTED_CONTRACT_PRESERVED=true
TASK036_TASK035_PRESSURE_DROP_FORWARDING_ONLY=true
TASK036_TASK035_NO_IDENTITY_REWRITE=true
```

The unchanged branch schemas retain their exact ordered memberships:

```text
TASK036_TYPED_BLOCKED_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,failure_stage,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,request_hash,blocked_result_hash,result_id,blockers,warnings,deferred_capabilities,upstream_evidence,provenance)
TASK036_TYPED_BLOCKED_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,demo_id,release_version,failure_stage,source_commit,source_tree,task031_status,task032_status,task033_status,task034_status,task035_status,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,request_hash,blockers,warnings,deferred_capabilities,upstream_evidence,provenance)
TASK036_TYPED_BLOCKED_RESULT_EXCLUDED_FROM_PREHASH=(blocked_result_hash,result_id)
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blocked_result_hash,blockers,warnings,deferred_capabilities)
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS=(schema_version,profile_id,implementation_software_version,raw_request_projection,blockers,warnings,deferred_capabilities)
TASK036_RAW_BOUNDARY_BLOCKED_RESULT_EXCLUDED_FROM_PREHASH=(blocked_result_hash)
TASK036_RAW_PROJECTION_FIELDS=(projection_kind,projection)
TASK036_RAW_PROJECTION_PREHASH_FIELDS=(projection_kind,projection)
TASK036_RAW_PROJECTION_EXCLUDED_FROM_PREHASH=()

TASK036_UPSTREAM_EVIDENCE_LEDGER_FIELDS=(schema_version,ledger_id,source_definition_issue,source_definition_revision,source_definition_freeze_comment_id,task031_producer_ref,task032_producer_ref,task033_producer_ref,task034_producer_ref,task035_pr,task035_delivery_commit,task035_merge_commit,task035_tree,task031_review_evidence,task032_review_evidence,task033_review_evidence,task034_review_evidence,task035_review_evidence,task031_test_evidence,task032_test_evidence,task033_test_evidence,task034_test_evidence,task035_test_evidence,task035_determinism_evidence,historical_task035_evidence,ledger_hash)
TASK036_UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS=(schema_version,ledger_id,source_definition_issue,source_definition_revision,source_definition_freeze_comment_id,task031_producer_ref,task032_producer_ref,task033_producer_ref,task034_producer_ref,task035_pr,task035_delivery_commit,task035_merge_commit,task035_tree,task031_review_evidence,task032_review_evidence,task033_review_evidence,task034_review_evidence,task035_review_evidence,task031_test_evidence,task032_test_evidence,task033_test_evidence,task034_test_evidence,task035_test_evidence,task035_determinism_evidence,historical_task035_evidence)

TASK036_ACCEPTANCE_CHECKLIST_FIELDS=(schema_version,checklist_id,release_version,success_demo_id,required_available_capabilities,unavailable_capabilities,required_test_ids,required_artifact_paths,required_python_versions,required_repeat_runs,upstream_identity_status,release_acceptance_status,checklist_status,checklist_hash)
TASK036_ACCEPTANCE_CHECKLIST_PREHASH_FIELDS=(schema_version,checklist_id,release_version,success_demo_id,required_available_capabilities,unavailable_capabilities,required_test_ids,required_artifact_paths,required_python_versions,required_repeat_runs,upstream_identity_status,release_acceptance_status,checklist_status)

TASK036_MANIFEST_FIELDS=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref,manifest_hash)
TASK036_MANIFEST_PREHASH_FIELDS=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref)

TASK036_VERSION_METADATA_FIELDS=(schema_version,metadata_id,release_version,release_candidate_id,software_version,source_commit,source_tree,task031_authority_ref,task032_authority_ref,task033_authority_ref,task034_authority_ref,task035_authority_ref,manifest_digest,artifact_digest_set,release_acceptance_result_id,semantic_identity_version,metadata_hash)
TASK036_VERSION_METADATA_PREHASH_FIELDS=(schema_version,metadata_id,release_version,release_candidate_id,software_version,source_commit,source_tree,task031_authority_ref,task032_authority_ref,task033_authority_ref,task034_authority_ref,task035_authority_ref,manifest_digest,artifact_digest_set,release_acceptance_result_id,semantic_identity_version)

TASK036_PROVENANCE_FIELDS=(schema_version,task_id,profile_id,demo_id,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,producer_edges,release_evidence_ledger_hash,artifact_manifest_digest,acceptance_checklist_digest,source_commit,source_tree,provenance_hash)
TASK036_PROVENANCE_PREHASH_FIELDS=(schema_version,task_id,profile_id,demo_id,task031_request_hash,task031_geometry_id,task031_geometry_hash,task032_request_hash,task032_result_hash,task032_result_id,task033_request_hash,task033_result_hash,task033_result_id,task034_request_hash,task034_result_hash,task034_result_id,task035_request_hash,task035_result_hash,task035_result_id,producer_edges,release_evidence_ledger_hash,artifact_manifest_digest,acceptance_checklist_digest,source_commit,source_tree)

TASK036_DETERMINISM_EVIDENCE_FIELDS=(schema_version,evidence_id,input_hash,runtime_versions,repeat_run_count,compared_surfaces,compared_digests,compared_result_ids,byte_identity_status,repeat_identity_status,excluded_operational_fields,evidence_hash)
TASK036_DETERMINISM_EVIDENCE_PREHASH_FIELDS=(schema_version,evidence_id,input_hash,runtime_versions,repeat_run_count,compared_surfaces,compared_digests,compared_result_ids,byte_identity_status,repeat_identity_status,excluded_operational_fields)
```

### 25.11 HISTORICAL_SUPERSEDED — R2 implementation, artifact, CI, and scope boundaries

Historical R2 authority only; this subsection is superseded by Section 27.5.
The future implementation allowlists in this historical snapshot are unchanged and exact. The CI manifest
entry is a required one-file registration in the existing shard; it does not
authorize a new workflow or shard.

```text
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST_COUNT=8
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST=(src/hexagent/release_demo/__init__.py,src/hexagent/release_demo/task036.py,src/hexagent/release_demo/schema.py,src/hexagent/release_demo/canonical.py,src/hexagent/release_demo/models.py,src/hexagent/release_demo/validation.py,src/hexagent/release_demo/provenance.py,src/hexagent/release_demo/artifacts.py)
IMPLEMENTATION_TEST_FILE_ALLOWLIST_COUNT=1
IMPLEMENTATION_TEST_FILE_ALLOWLIST=(tests/release_demo/test_task036_v03.py)
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST_COUNT=11
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST=(artifacts/task036/v0.3/task036_demo_input.json,artifacts/task036/v0.3/task036_demo_output.json,artifacts/task036/v0.3/task036_blocked_cases.json,artifacts/task036/v0.3/task036_canonical_identity.json,artifacts/task036/v0.3/task036_cross_python_determinism.json,artifacts/task036/v0.3/task036_repeat_run_determinism.json,artifacts/task036/v0.3/task036_upstream_evidence_ledger.json,artifacts/task036/v0.3/task036_release_acceptance_ledger.json,artifacts/task036/v0.3/task036_acceptance_checklist.json,artifacts/task036/v0.3/task036_manifest.json,artifacts/task036/v0.3/task036_version_metadata.json)
IMPLEMENTATION_CI_ALLOWLIST_COUNT=1
IMPLEMENTATION_CI_ALLOWLIST=(ci-shard-manifest.yml)
IMPLEMENTATION_CI_MANIFEST_MUTATION_REQUIRED=true
IMPLEMENTATION_CI_MANIFEST_MUTATION_FORM=one explicit file-list entry for tests/release_demo/test_task036_v03.py in the existing ci shard
IMPLEMENTATION_CI_NEW_WORKFLOW_REQUIRED=false
IMPLEMENTATION_CI_NEW_SHARD_REQUIRED=false
OTHER_ALLOWED_FILES=NONE
FORBIDDEN_FILE_PATTERNS=(TASK031,TASK032,TASK033,TASK034,TASK035,TASK037,TASK038,TASK039,blocker_registry.py,warning_registry.py,.github/workflows,release_spec.yaml,pyproject.toml,uv.lock)

OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNBOUNDED_FILE_ALLOWLIST_ENTRY_COUNT=0
UNFROZEN_SCHEMA_COUNT=0
UNFROZEN_BLOCKER_COUNT=0
UNFROZEN_STAGE_COUNT=0
UNFROZEN_TEST_ID_COUNT=0
UNFROZEN_ARTIFACT_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0
```

### 25.12 HISTORICAL_SUPERSEDED — R1 correction self-check and closure

This is an author-side deterministic self-check. It is not independent review
evidence and does not accept or freeze the Design.

```text
SOURCE_DECISION_COUNT=35
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_DECISION_MAPPING_CONTRADICTION_COUNT=0
SOURCE_SEMANTIC_CHANGE_COUNT=0
SOURCE_SEMANTIC_REINTERPRETATION_COUNT=0
NEW_SOURCE_DECISION_COUNT=0

IDENTITY_DATAFLOW_ACYCLIC=true
DATAFLOW_TOPOLOGICAL_ORDER_EXISTS=true
CIRCULAR_PREHASH_REFERENCE_COUNT=0
FORWARD_REFERENCE_COUNT=0
BACKWARD_DEPENDENCY_COUNT=0
UNDEFINED_DEPENDENCY_COUNT=0
RESULT_ID_USED_BEFORE_DERIVATION_COUNT=0
RESULT_ID_DERIVATION_VALID=true
RESULT_ID_SELF_REFERENCE_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0

HASHED_CONTRACT_COUNT=11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT=11
MISSING_CANONICAL_KIND_TAG_COUNT=0
DUPLICATE_CANONICAL_KIND_TAG_COUNT=0

PROVENANCE_NODE_COUNT=7
PROVENANCE_EDGE_COUNT=6
PROVENANCE_SELF_EDGE_COUNT=0
PROVENANCE_DUPLICATE_EDGE_COUNT=0
PROVENANCE_MISSING_PRODUCER_COUNT=0
PROVENANCE_UNBOUND_EDGE_IDENTITY_COUNT=0
PROVENANCE_HISTORICAL_AUTHORITY_AS_CURRENT_PRODUCER_COUNT=0

ARTIFACT_COUNT=11
UNIQUE_ARTIFACT_ID_COUNT=11
UNIQUE_ARTIFACT_PATH_COUNT=11
UNFROZEN_ARTIFACT_COUNT=0
ARTIFACT_BACKWARD_DEPENDENCY_COUNT=0
ARTIFACT_DIGEST_CYCLE_COUNT=0
ARTIFACT_STAGE_DATAFLOW_REVIEW=PASS

TASK036_FINAL_RESULT_CANONICAL_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_HASH_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_ID_SURFACE_INCLUDED=true
PYTHON_3_11=true
PYTHON_3_12=true
REPEAT_RUN_DETERMINISM=true
CROSS_VERSION_BYTE_IDENTITY=true
TASK036_DETERMINISM_COMPARISON_SURFACE_COUNT=9
TASK036_DETERMINISM_PROTOCOL_CLOSED=true
TASK036_FINAL_RESULT_INPUT_FIELD_COUNT=31
TASK036_FINAL_RESULT_INPUT_TO_SCHEMA_COVERAGE_COUNT=31
TASK036_FINAL_RESULT_UNBOUND_FIELD_COUNT=0
TASK036_RELEASE_ACCEPTANCE_LEDGER_FIELD_COUNT=22
TASK036_RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELD_COUNT=21
TASK036_RELEASE_ACCEPTANCE_LEDGER_EXCLUDED_FROM_PREHASH=(ledger_hash)
TASK036_ARTIFACT_PRODUCER_STAGE_BEFORE_ALL_CONSUMERS=true
TEST_ID_COUNT=30
UNIQUE_TEST_ID_COUNT=30
TEST_COVERAGE_GAP_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNRESOLVED_TASK036_DESIGN_AUTHORITY_COUNT=0
AMBIGUOUS_AUTHORITY_TOKEN_COUNT=0
UNBOUNDED_FILE_ALLOWLIST_ENTRY_COUNT=0
DESIGN_INTERNAL_CONTRADICTION_COUNT=0
COUNT_CONTRADICTION_COUNT=0
CROSS_SECTION_AUTHORITY_CONTRADICTION_COUNT=0
UNFROZEN_SCHEMA_COUNT=0
UNFROZEN_BLOCKER_COUNT=0
UNFROZEN_STAGE_COUNT=0
UNFROZEN_TEST_ID_COUNT=0
UNFROZEN_ARTIFACT_COUNT=0

TASK036_DESIGN_CORRECTION_AUTHOR_SELF_CHECK=PASS
AUTHOR_SELF_CHECK_PASS_IS_NOT_INDEPENDENT_DESIGN_REVIEW=true
```

### 25.13 HISTORICAL_SUPERSEDED — R1 finding closure and next-review boundary

```text
TASK036_DESIGN_CORRECTION_COMPLETE=true
TASK036_DESIGN_CORRECTION_CLOSED_FINDING_COUNT=6
TASK036_DESIGN_CORRECTION_REOPENED_FINDING_COUNT=0
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_CORRECTION=true
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_ARTIFACT_BYTES_GENERATED_NOW=false
TASK036_TEST_EXECUTION_PERFORMED_IN_DESIGN_GATE=false
TASK036_NEXT_REVIEW_SCOPE=independent correction review of F1-F6 and regression guard
```

The corrected Design identity is reported by the authoring-gate receipt after
the file bytes are hashed. It is deliberately not embedded in the hashed
Design, so the receipt cannot self-reference its own digest.

```text
CORRECTED_DESIGN_IDENTITY_REPORTED_OUT_OF_BAND=true
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_CORRECTION_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 27. R3 correction overlay — preserved effective authority for D23, D25, D26 and D32

This is the preserved R3 authority for the four findings raised by the
independent R2 review. Section 29 is the later, narrow R4 closure for the
three R3 review findings; it does not reopen D23, D25, D26, or D32. The old
eleven-artifact, ten-peer, `v0.3`, and thirty-test values remain only in
explicitly historical sections and are not current implementation authority.

```text
TASK036_R3_CORRECTION_AUTHORITY_STATUS=EFFECTIVE
TASK036_R3_CORRECTION_SCOPE=(D23,D25,D26,D32)
TASK036_R3_CORRECTION_SCOPE_ONLY=true
TASK036_FROZEN_SOURCE_DEFINITION_REVISION=R5
TASK036_FROZEN_SOURCE_DEFINITION_UNCHANGED=true
TASK036_R3_NON_FINDING_AUTHORITY_REOPENED=false
TASK036_R3_NON_FINDING_AUTHORITY_CHANGED=false
TASK036_R3_ARTIFACT_BYTES_GENERATED_NOW=false
TASK036_R3_TEST_EXECUTION_PERFORMED_IN_DESIGN_GATE=false
```

### 27.1 Frozen D23 artifact inventory and exact artifact roles

The following six paths are the exact D23 future-artifact set from the frozen
Source Definition. The IDs are deterministic Design labels for those paths;
they do not add Source decisions. The repository runner and test module are
release-scope artifacts but are not manifest peers. The manifest itself is an
artifact but is not a peer of itself.

```text
SOURCE_D23_ARTIFACT_COUNT=6
SOURCE_D23_ARTIFACT_IDS=(TASK036_RELEASE_RUNNER,TASK036_RELEASE_TEST_MODULE,TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN,TASK036_RELEASE_MANIFEST_JSON,TASK036_RELEASE_ACCEPTANCE_MARKDOWN)
SOURCE_D23_ARTIFACT_PATHS=(scripts/release_demo/v0_3_task020_to_task035.py,tests/release_demo/test_v0_3_task020_to_task035.py,release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/release-acceptance.md)
SOURCE_D23_ARTIFACT_ROLES=(actual_public_graph_release_runner,release_authoritative_test_module,JSON_demo_evidence,Markdown_demo_evidence,release_manifest_JSON,release_acceptance_Markdown)
TASK036_FUTURE_ARTIFACTS=(scripts/release_demo/v0_3_task020_to_task035.py,tests/release_demo/test_v0_3_task020_to_task035.py,release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/release-acceptance.md)
```

| Artifact ID | Exact path | Schema ID or source role | Producer stage/node | Consumer stages | Canonicalization and digest | Identity participation | Required |
|---|---|---|---|---|---|---|---|
| `TASK036_RELEASE_RUNNER` | `scripts/release_demo/v0_3_task020_to_task035.py` | source role: actual public graph release runner | S00 / repository checkout | S02,S04,S06,S08,S10,S12,S14,S22 | exact UTF-8 source bytes, SHA-256 | upstream authority and runtime binding | REQUIRED |
| `TASK036_RELEASE_TEST_MODULE` | `tests/release_demo/test_v0_3_task020_to_task035.py` | source role: frozen D32 test module | S00 / repository checkout | S16,S17,S18,S22 and existing CI shard | exact UTF-8 source bytes, SHA-256 | test-authority evidence | REQUIRED |
| `TASK036_DEMO_JSON` | `release_evidence/v0.3.0/task020-to-task035-demo.json` | `task036.shell-side-thermal-hydraulic-integration-demo.v1` | S14 / N10 release-input bundle | S18,S19,S22 | normalized JSON, exact final bytes, SHA-256 | manifest peer digest | REQUIRED |
| `TASK036_DEMO_MARKDOWN` | `release_evidence/v0.3.0/task020-to-task035-demo.md` | `task036.release-evidence-markdown.v1` | S14 / N10 release-input bundle | S18,S19,S22 | normalized Markdown, exact final bytes, SHA-256 | manifest peer digest | REQUIRED |
| `TASK036_RELEASE_MANIFEST_JSON` | `release_evidence/v0.3.0/release-manifest.json` | `task036.manifest.v1` | S18 / N15 manifest | S19,S20,S21,S22 | canonical manifest fields, exact final bytes, SHA-256; no self entry | manifest identity | REQUIRED |
| `TASK036_RELEASE_ACCEPTANCE_MARKDOWN` | `release_evidence/v0.3.0/release-acceptance.md` | `task036.release-acceptance-markdown.v1` | S17 / N14 acceptance checklist | S18,S19,S20,S21,S22 | normalized Markdown, exact final bytes, SHA-256 | manifest peer digest and release evidence | REQUIRED |

```text
TASK036_ARTIFACT_INVENTORY_COUNT=6
TASK036_ARTIFACT_INVENTORY_CLOSED=true
TASK036_ARTIFACT_ROOT=SOURCE_D23_EXACT_PATH_SET
TASK036_RELEASE_EVIDENCE_ROOT=release_evidence/v0.3.0
TASK036_ARTIFACT_ID_ORDER=(TASK036_RELEASE_RUNNER,TASK036_RELEASE_TEST_MODULE,TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN,TASK036_RELEASE_MANIFEST_JSON,TASK036_RELEASE_ACCEPTANCE_MARKDOWN)
TASK036_ARTIFACT_INVENTORY=(scripts/release_demo/v0_3_task020_to_task035.py,tests/release_demo/test_v0_3_task020_to_task035.py,release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/release-acceptance.md)
TASK036_ARTIFACT_DIGEST_ALGORITHM=SHA-256
TASK036_ARTIFACT_DIGEST_INPUT=EXACT_FINAL_FILE_BYTES
TASK036_ARTIFACT_DIGEST_PATHS=REPOSITORY_RELATIVE_POSIX
TASK036_ACTIVE_ARTIFACT_AUTHORITY_TABLE_COUNT=1
TASK036_UNIQUE_ARTIFACT_ID_COUNT=6
TASK036_UNIQUE_ARTIFACT_PATH_COUNT=6
TASK036_EXTRA_RELEASE_AUTHORITATIVE_ARTIFACT_COUNT=0
TASK036_MISSING_FROZEN_ARTIFACT_COUNT=0
TASK036_SOURCE_D23_ARTIFACT_SET_MATCH=true
TASK036_OLD_11_ARTIFACT_INVENTORY_ACTIVE=false
TASK036_INTERNAL_NODE_MISCLASSIFIED_AS_ARTIFACT_COUNT=0
TASK036_INTERNAL_DATAFLOW_NODES_REMAIN_NON_ARTIFACTS=true
TASK036_MANIFEST_PEER_COUNT=3
TASK036_NON_MANIFEST_ARTIFACT_COUNT=3
TASK036_NON_MANIFEST_ARTIFACTS=(TASK036_RELEASE_RUNNER,TASK036_RELEASE_TEST_MODULE,TASK036_RELEASE_MANIFEST_JSON)
```

The old release-evidence records that are not members of the frozen six-path
set are now internal dataflow records or deterministic comparison surfaces
only. They are not silently recreated under another path, and no directory
scan can promote an internal node to a release artifact.

```text
TASK036_ARTIFACT_DIRECTORY_SCAN_IS_AUTHORITY=false
TASK036_RELEASE_ARTIFACT_PATH_SELECTION_BY_IMPLEMENTATION=false
TASK036_RELEASE_ARTIFACT_PATH_SELECTION_BY_DIRECTORY_SCAN=false
```

### 27.2 Frozen D25 manifest peer authority

The D25 peer set is distinct from the six-path D23 inventory. Its declaration
order is the exact frozen Source list; its digest entries are serialized in
the frozen lexicographic path order. The manifest is generated after these
three peer files and never discovers peers dynamically.

```text
SOURCE_D25_MANIFEST_PEER_COUNT=3
SOURCE_D25_MANIFEST_PEERS=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
V03_MANIFEST_PEER_PATHS=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
MANIFEST_PEER_COUNT=3
MANIFEST_PEERS=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
MANIFEST_PEER_DECLARATION_ORDER=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
MANIFEST_DIGEST_SERIALIZATION_ORDER=(release_evidence/v0.3.0/release-acceptance.md,release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md)
MANIFEST_ORDER=LEXICOGRAPHIC_BY_PATH
MANIFEST_EXTRA_PEER_COUNT=0
MANIFEST_MISSING_PEER_COUNT=0
SOURCE_D25_MANIFEST_PEER_SET_MATCH=true
ARTIFACT_SET_EQUALS_MANIFEST_PEER_SET=false
MANIFEST_SELF_DIGEST_ENTRY=false
MANIFEST_SELF_DIGEST_NOT_EMBEDDED_IN_JSON=true
MANIFEST_GENERATE_LAST=true
MANIFEST_DYNAMIC_DIRECTORY_SCAN=false
MANIFEST_FORWARD_REFERENCE_COUNT=0
MANIFEST_DIGEST_CYCLE_COUNT=0
MANIFEST_UNBOUND_REQUIRED_REFERENCE_COUNT=0
NON_MANIFEST_ARTIFACT_COUNT=3
```

```text
TASK036_MANIFEST_SCHEMA_ID=task036.manifest.v1
TASK036_MANIFEST_FIELD_ORDER=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref,manifest_hash)
TASK036_MANIFEST_FIELD_COUNT=13
TASK036_MANIFEST_PREHASH_FIELDS=(schema_version,manifest_id,release_version,source_commit,source_tree,artifact_inventory,artifact_digest_set,python_versions,repeat_run_count,upstream_evidence_ledger_ref,release_acceptance_ledger_ref,acceptance_checklist_ref)
TASK036_MANIFEST_PREHASH_FIELD_COUNT=12
TASK036_MANIFEST_EXCLUDED_FROM_PREHASH=(manifest_hash)
TASK036_MANIFEST_ARTIFACT_REFERENCE_COUNT=3
TASK036_MANIFEST_ARTIFACT_REFERENCE_SET=(TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN,TASK036_RELEASE_ACCEPTANCE_MARKDOWN)
TASK036_MANIFEST_ARTIFACT_REFERENCE_PATH_SET=SOURCE_D25_MANIFEST_PEERS
TASK036_MANIFEST_ARTIFACT_DIGESTS_EXACT_FINAL_BYTES=true
TASK036_MANIFEST_SOURCE_COMMIT_REQUIRED=true
TASK036_MANIFEST_SOURCE_TREE_REQUIRED=true
```

### 27.3 Frozen D26 version boundary and controlled version files

The distribution version is the exact frozen Source value `0.3.0`. `v0.3`
is retained only as a human display label and is not a distribution-version
authority. The two version-bearing files are controlled implementation inputs;
this Design correction does not mutate either file.

```text
SOURCE_D26_TARGET_DISTRIBUTION_VERSION=0.3.0
TARGET_DISTRIBUTION_VERSION=0.3.0
TASK036_RELEASE_VERSION=0.3.0
TASK036_RELEASE_VERSION_DISPLAY_LABEL=v0.3
DISPLAY_LABEL_ONLY=true
NOT_DISTRIBUTION_VERSION=true
VERSION_BEARING_FILES=(pyproject.toml,uv.lock)
SOURCE_D26_VERSION_BEARING_FILES=(pyproject.toml,uv.lock)
SOURCE_D26_VERSION_BOUNDARY_MATCH=true
VERSION_METADATA_CHANGE_MUST_BE_EXACTLY_SCOPED=true
DEPENDENCY_RESOLUTION_CHANGE_NOT_IMPLIED_BY_VERSION_BUMP=true
VERSION_BUMP_DEPENDENCY_RESOLUTION_CHANGE_ALLOWED=false
DEPENDENCY_RESOLUTION_CHANGE_ALLOWED=false
TAG_CREATION_NOT_PART_OF_IMPLEMENTATION=true
GITHUB_RELEASE_CREATION_NOT_PART_OF_IMPLEMENTATION=true
PYPROJECT_TOML_VERSION_UPDATE_ALLOWED_IN_IMPLEMENTATION=true
UV_LOCK_VERSION_UPDATE_ALLOWED_IN_IMPLEMENTATION=true
PYPROJECT_TOML_MUTATED_NOW=false
UV_LOCK_MUTATED_NOW=false
EXTRA_VERSION_BEARING_FILE_COUNT=0
```

### 27.4 Frozen D32 test inventory, test path, and CI projection

The following is the exact 22-member D32 inventory. Coverage assertions added
by the R2 correction are mapped into these IDs; they do not create a second
release-authoritative inventory.

```text
SOURCE_D32_TEST_ID_COUNT=22
SOURCE_D32_TEST_IDS=(T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS,T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS,T036_CHAIN_003_TASK035_PUBLIC_BOUNDARY_ONLY,T036_CHAIN_004_V02_TUBE_SIDE_RELEASE_AUTHORITY_INHERITED,T036_BLOCK_001_TASK031_FAIL_CLOSED,T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH,T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH,T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION,T036_EVID_001_JSON_SCHEMA,T036_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER,T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,T036_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY,T036_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY,T036_DET_003_PY311_PY312_JSON_BYTE_IDENTITY,T036_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY,T036_META_001_PYPROJECT_VERSION_0_3_0,T036_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT,T036_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES,T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE,T036_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION)
TASK036_TEST_IDS=(T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS,T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS,T036_CHAIN_003_TASK035_PUBLIC_BOUNDARY_ONLY,T036_CHAIN_004_V02_TUBE_SIDE_RELEASE_AUTHORITY_INHERITED,T036_BLOCK_001_TASK031_FAIL_CLOSED,T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH,T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH,T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION,T036_EVID_001_JSON_SCHEMA,T036_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER,T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,T036_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY,T036_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY,T036_DET_003_PY311_PY312_JSON_BYTE_IDENTITY,T036_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY,T036_META_001_PYPROJECT_VERSION_0_3_0,T036_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT,T036_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES,T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE,T036_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION)
TASK036_TEST_PATH=tests/release_demo/test_v0_3_task020_to_task035.py
TEST_INVENTORY_CLOSED=true
TEST_ID_COUNT=22
UNIQUE_TEST_ID_COUNT=22
TASK036_TEST_ID_ORDER=SOURCE_D32_TEST_IDS
TASK036_TEST_ID_DUPLICATE_COUNT=0
TASK036_TEST_ID_UNMAPPED_COUNT=0
OLD_30_TEST_ID_INVENTORY_ACTIVE=false
EXTRA_TEST_ID_COUNT=0
MISSING_FROZEN_TEST_ID_COUNT=0
DUPLICATE_TEST_ID_COUNT=0
TEST_COVERAGE_GAP_COUNT=0
```

```text
FROZEN_TEST_ASSERTION_COVERAGE=(
  actual_production_graph:T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS,T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS,T036_CHAIN_003_TASK035_PUBLIC_BOUNDARY_ONLY,
  success_demo:T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS,
  blocked_demos:T036_BLOCK_001_TASK031_FAIL_CLOSED,T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH,T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE,T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH,T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION,
  evidence_refs_semantics:T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS,T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,
  identity_dag_and_kind_tags:T036_EVID_001_JSON_SCHEMA,T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,
  distinct_internal_and_release_identity:T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,
  failure_precedence_and_blocker_binding:T036_BLOCK_001_TASK031_FAIL_CLOSED,T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE,
  provenance:T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,
  artifact_and_manifest_contract:T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER,T036_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES,
  final_determinism:T036_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY,T036_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY,T036_DET_003_PY311_PY312_JSON_BYTE_IDENTITY,T036_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY,
  version_0_3_0:T036_META_001_PYPROJECT_VERSION_0_3_0,T036_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT,
  release_checklist:T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE,T036_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION
)
NON_AUTHORITATIVE_SUPPORT_ASSERTIONS_ALLOWED=true
NON_AUTHORITATIVE_SUPPORT_ASSERTIONS_ARE_NOT_RELEASE_TEST_IDS=true
```

```text
TASK036_CI_OWNER=existing ci shard
TASK036_CI_MANIFEST=ci-shard-manifest.yml
TASK036_FUTURE_CI_TEST_PATH=tests/release_demo/test_v0_3_task020_to_task035.py
TASK036_FUTURE_CI_SHARD=ci
TASK036_FUTURE_CI_JOB=shard-ci
TASK036_FUTURE_CI_PYTHON_MATRIX=(3.11,3.12)
TASK036_CI_MANIFEST_MUTATION_REQUIRED=true
TASK036_CI_MANIFEST_MUTATION_FORM=one explicit file-list entry for tests/release_demo/test_v0_3_task020_to_task035.py in the existing ci shard
TASK036_CI_NEW_WORKFLOW_REQUIRED=false
TASK036_CI_NEW_SHARD_REQUIRED=false
PYTHON_3_11_REQUIRED=true
PYTHON_3_12_REQUIRED=true
PR_HEAD_REQUIRED=true
MERGE_REF_REQUIRED=true
MAIN_PUSH_REQUIRED=true
GLOBAL_COLLECTION_REQUIRED=true
RUFF_REQUIRED=true
RUFF_FORMAT_REQUIRED=true
MYPY_REQUIRED=true
PIP_AUDIT_REQUIRED=true
DIFF_CHECK_REQUIRED=true
WORKFLOW_MUTATION_REQUIRED=false
REPEAT_RUN_JSON_BYTES_IDENTICAL=true
REPEAT_RUN_MARKDOWN_BYTES_IDENTICAL=true
PY311_JSON_BYTES_EQ_PY312_JSON_BYTES=true
PY311_MARKDOWN_BYTES_EQ_PY312_MARKDOWN_BYTES=true
FROZEN_JSON_MATCH=true
FROZEN_MARKDOWN_MATCH=true
IMPLEMENTATION_CI_ALLOWLIST_COUNT=1
IMPLEMENTATION_CI_ALLOWLIST=(ci-shard-manifest.yml)
SOURCE_D33_BOUNDARY_SCOPE_MATCH=true
```

### 27.5 Source-compatible versioned implementation allowlists

The exact future mutation set is recomputed from the frozen D26 version
boundary and the D23/D32 paths. The test path intentionally appears in both
the test category and the D23 artifact category; the unique-path count is
reported separately from the category-entry count.

```text
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST_COUNT=10
IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST=(src/hexagent/release_demo/__init__.py,src/hexagent/release_demo/task036.py,src/hexagent/release_demo/schema.py,src/hexagent/release_demo/canonical.py,src/hexagent/release_demo/models.py,src/hexagent/release_demo/validation.py,src/hexagent/release_demo/provenance.py,src/hexagent/release_demo/artifacts.py,pyproject.toml,uv.lock)
IMPLEMENTATION_TEST_FILE_ALLOWLIST_COUNT=1
IMPLEMENTATION_TEST_FILE_ALLOWLIST=(tests/release_demo/test_v0_3_task020_to_task035.py)
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST_COUNT=6
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST=(scripts/release_demo/v0_3_task020_to_task035.py,tests/release_demo/test_v0_3_task020_to_task035.py,release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/release-acceptance.md)
IMPLEMENTATION_CI_MANIFEST_ALLOWLIST_COUNT=1
IMPLEMENTATION_CI_MANIFEST_ALLOWLIST=(ci-shard-manifest.yml)
PYPROJECT_TOML_IN_IMPLEMENTATION_ALLOWLIST=true
UV_LOCK_IN_IMPLEMENTATION_ALLOWLIST=true
ALLOWLIST_SCOPE_MATCHES_FROZEN_D26=true
TOTAL_IMPLEMENTATION_MUTATION_ALLOWLIST_COUNT=18
UNIQUE_IMPLEMENTATION_MUTATION_PATH_COUNT=17
OTHER_ALLOWED_FILES=NONE
EXTRA_VERSION_BEARING_FILE_COUNT=0
UNBOUNDED_FILE_ALLOWLIST_ENTRY_COUNT=0
FORBIDDEN_FILE_PATTERNS=(TASK031,TASK032,TASK033,TASK034,TASK035,TASK037,TASK038,TASK039,blocker_registry.py,warning_registry.py,.github/workflows,release_spec.yaml,package.json,setup.py,setup.cfg,VERSION,release.yaml)
```

```text
TASK036_ARTIFACT_ALLOWLIST_TO_FROZEN_D23_MATCH_COUNT=6
TASK036_ARTIFACT_ALLOWLIST_EXTRA_COUNT=0
TASK036_ARTIFACT_ALLOWLIST_MISSING_COUNT=0
TASK036_TEST_ALLOWLIST_TO_FROZEN_D32_MATCH=true
TASK036_VERSION_FILE_ALLOWLIST_TO_FROZEN_D26_MATCH=true
```

### 27.6 Determinism and identity after artifact/test contraction

The R2 identity contracts remain internal semantic contracts rather than a
second artifact inventory. The active determinism surface is derived from the
four frozen JSON/Markdown release bytes plus the three final-result identity
surfaces; the old eleven-artifact comparison list is historical.

```text
TASK036_DETERMINISM_SURFACE_COUNT=7
TASK036_DETERMINISM_SURFACE_IDS=(DS01,DS02,DS03,DS04,DS05,DS06,DS07)
TASK036_DETERMINISM_SURFACES=(task020_to_task035_demo_json_bytes,release_manifest_json_bytes,task020_to_task035_demo_markdown_bytes,release_acceptance_markdown_bytes,TASK036_final_result_canonical_bytes,TASK036_final_result_hash,TASK036_internal_result_id)
TASK036_DETERMINISM_ARTIFACT_BYTE_SURFACES=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
TASK036_FINAL_RESULT_CANONICAL_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_HASH_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_ID_SURFACE_INCLUDED=true
PYTHON_3_11=true
PYTHON_3_12=true
REPEAT_RUN_DETERMINISM=true
CROSS_VERSION_BYTE_IDENTITY=true
PY311_REPEAT_SURFACE_COUNT=7
PY312_REPEAT_SURFACE_COUNT=7
CROSS_PYTHON_SURFACE_COUNT=7
SURFACE_COUNT_MISMATCH_COUNT=0
TASK036_DETERMINISM_EVIDENCE_EXCLUDED_FROM_PREHASH=(evidence_hash)
TASK036_DETERMINISM_PROTOCOL_CLOSED=true
TASK036_FINAL_ARTIFACT_BYTE_COMPARISON_DOES_NOT_FEED_TASK036_SUCCESS_IDENTITY_CORE=true
```

```text
HASHED_CONTRACT_IDS=(H01_DEMO_INPUT,H02_SUCCESS_RESULT,H03_TYPED_BLOCKED_RESULT,H04_RAW_BOUNDARY_BLOCKED_RESULT,H05_RELEASE_ACCEPTANCE_LEDGER,H06_UPSTREAM_EVIDENCE_LEDGER,H07_ACCEPTANCE_CHECKLIST,H08_PROVENANCE,H09_MANIFEST,H10_VERSION_METADATA,H11_DETERMINISM_EVIDENCE)
HASHED_CONTRACT_COUNT=11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT=11
MISSING_CANONICAL_KIND_TAG_COUNT=0
DUPLICATE_CANONICAL_KIND_TAG_COUNT=0
HASHED_CONTRACT_SOURCE_COMPATIBLE=true
RELEASE_ARTIFACT_ONLY_HASH_CONTRACT_COUNT=0
TASK036_INTERNAL_IDENTITY_CONTRACTS_REMAIN_SEPARATE_FROM_D23_ARTIFACT_PATHS=true
TASK036_INTERNAL_RESULT_ID_ALGORITHM=UUIDv5
RELEASE_ACCEPTANCE_RESULT_ID_ALGORITHM=SHA-256
TASK036_INTERNAL_RESULT_ID_AND_RELEASE_ACCEPTANCE_RESULT_ID_DISTINCT=true
CROSS_IDENTITY_ALIAS_COUNT=0
RESULT_ID_DERIVATION_VALID=true
IDENTITY_DATAFLOW_ACYCLIC=true
UNFROZEN_IDENTITY_RULE_COUNT=0
```

### 27.7 Artifact/manifest closure and preserved release architecture

Shrinking the release artifact set does not delete the internal evidence
records required by the existing 23-stage graph. Those records remain
in-memory or embedded semantic projections. Only the six frozen D23 paths are
materialized as future release-scope artifacts, and only the three frozen D25
paths are manifest peers.

```text
ARTIFACT_COUNT=6
UNIQUE_ARTIFACT_ID_COUNT=6
UNIQUE_ARTIFACT_PATH_COUNT=6
ARTIFACT_BACKWARD_DEPENDENCY_COUNT=0
ARTIFACT_UNDEFINED_PRODUCER_COUNT=0
ARTIFACT_UNDEFINED_CONSUMER_INPUT_COUNT=0
ARTIFACT_DIGEST_CYCLE_COUNT=0
ARTIFACT_PRODUCER_STAGE_BEFORE_ALL_CONSUMERS=true
ARTIFACT_STAGE_DATAFLOW_REVIEW=PASS
MANIFEST_PEER_COUNT=3
MANIFEST_FORWARD_REFERENCE_COUNT=0
MANIFEST_DIGEST_CYCLE_COUNT=0
MANIFEST_UNBOUND_REQUIRED_REFERENCE_COUNT=0
IDENTITY_DATAFLOW_ACYCLIC=true
CORRECTED_RUNTIME_STAGE_COUNT=23
IDENTITY_NODE_COUNT=20
IDENTITY_EDGE_COUNT=56
PROVENANCE_NODE_COUNT=7
PROVENANCE_EDGE_COUNT=6
BLOCKER_REGISTRY_COUNT=22
SUCCESS_DEMO_COUNT=1
BLOCKED_DEMO_COUNT=6
```

### 27.8 HISTORICAL_SUPERSEDED — R3 closure, source mapping, self-check, and lifecycle

```text
R3_F1_ID=TASK036_R2_D23_ARTIFACT_INVENTORY_NOT_PROJECTED
R3_F1_STATUS=RESOLVED_BY_DESIGN_R3_CORRECTION
R3_F1_SECTION_REF=27.1,27.5,27.7
R3_F2_ID=TASK036_R2_D25_MANIFEST_PEER_PATHS_NOT_PROJECTED
R3_F2_STATUS=RESOLVED_BY_DESIGN_R3_CORRECTION
R3_F2_SECTION_REF=27.2,27.7
R3_F3_ID=TASK036_R2_D26_VERSION_BOUNDARY_NOT_PROJECTED
R3_F3_STATUS=RESOLVED_BY_DESIGN_R3_CORRECTION
R3_F3_SECTION_REF=27.3,27.5
R3_F4_ID=TASK036_R2_D32_TEST_INVENTORY_NOT_PROJECTED
R3_F4_STATUS=RESOLVED_BY_DESIGN_R3_CORRECTION
R3_F4_SECTION_REF=27.4,27.5

SOURCE_DECISION_COUNT=35
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_DECISION_MAPPING_CONTRADICTION_COUNT=0
SOURCE_SEMANTIC_CHANGE_COUNT=0
SOURCE_SEMANTIC_REINTERPRETATION_COUNT=0
NEW_SOURCE_DECISION_COUNT=0
D23_MATCH=true
D25_MATCH=true
D26_MATCH=true
D32_MATCH=true

N1_STATUS=REMAINS_RESOLVED
N2_STATUS=REMAINS_RESOLVED
N3_STATUS=REMAINS_RESOLVED
N4_STATUS=REMAINS_RESOLVED
F1_STATUS=REMAINS_RESOLVED
F2_STATUS=REMAINS_RESOLVED
F3_STATUS=REMAINS_RESOLVED
F4_STATUS=REMAINS_RESOLVED
F5_STATUS=REMAINS_RESOLVED
F6_STATUS=REMAINS_RESOLVED

DESIGN_INTERNAL_CONTRADICTION_COUNT=0
COUNT_CONTRADICTION_COUNT=0
CROSS_SECTION_AUTHORITY_CONTRADICTION_COUNT=0
UNRESOLVED_TASK036_DESIGN_AUTHORITY_COUNT=0
R3_NEW_INTERNAL_FINDING_COUNT=0
R3_NEW_INTERNAL_FINDINGS=NONE
TASK036_R3_AUTHOR_SELF_CHECK=PASS
AUTHOR_SELF_CHECK_PASS_IS_NOT_INDEPENDENT_DESIGN_REVIEW=true

TASK036_ACTIVE_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R3_INDEPENDENT_REVIEW_ONLY
CURRENT_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R3_INDEPENDENT_REVIEW_ONLY
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R3_INDEPENDENT_REVIEW_ONLY
ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=1
COMPETING_ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=0
TASK036_DESIGN_R3_CORRECTION_COMPLETE=true
TASK036_DESIGN_REVIEWED=false
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

## 28. HISTORICAL_SUPERSEDED — R3 authoring-gate mutation boundary and candidate identity

This R3 gate changes only the Design file. It does not create artifact bytes,
modify the frozen Source Definition, update Issue #203, or authorize any
downstream lifecycle operation.

```text
TASK036_R3_AUTHORING_CHANGED_FILE_COUNT=1
TASK036_R3_AUTHORING_CHANGED_FILES=(docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md)
TASK036_R3_DESIGN_MUTATED=true
TASK036_R3_SOURCE_DEFINITION_MUTATED=false
TASK036_R3_ISSUE203_MUTATED=false
TASK036_R3_TASK036_CODE_MUTATED=false
TASK036_R3_TASK036_TESTS_MUTATED=false
TASK036_R3_TASK036_ARTIFACTS_MUTATED=false
TASK036_R3_PYPROJECT_TOML_MUTATED_NOW=false
TASK036_R3_UV_LOCK_MUTATED_NOW=false
TASK036_R3_CI_MUTATED=false
TASK036_R3_WORKFLOW_MUTATED=false
TASK036_R3_INDEX_MUTATED=false
TASK036_R3_BRANCH_CREATED=false
TASK036_R3_COMMIT_CREATED=false
TASK036_R3_PUSH_PERFORMED=false
TASK036_R3_PR_CREATED=false
TASK036_R3_MERGE_PERFORMED=false
TASK036_R3_TAG_MUTATED=false
TASK036_R3_RELEASE_MUTATED=false

TASK036_DESIGN_R3_CORRECTION_COMPLETE=true
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_CORRECTION=true
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
```

The R3 Design-only candidate identity is reported out of band after hashing
the final UTF-8 file and the empty-file Design diff from `origin/main`. It is
not embedded in the hashed Design and therefore does not self-reference.

```text
R3_DESIGN_IDENTITY_REPORTED_OUT_OF_BAND=true
R3_DESIGN_FILE_SHA256=REPORTED_OUT_OF_BAND_AFTER_FILE_HASH
R3_DESIGN_DIFF_SHA256=REPORTED_OUT_OF_BAND_AFTER_DIFF_HASH
R3_DESIGN_LINE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_COUNT
R3_DESIGN_BYTE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_SIZE
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R3_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

## 29. R4 correction overlay — artifact, version, and determinism closure

This is the sole R4 correction overlay for review comment `5450059909`. It
closes only the three R3 findings named below. The frozen R5 Source Definition,
the D23/D25/D26/D32 projections, the 23-stage executable topology, the 20-node
identity graph, the 11 hashed contracts, the seven-node provenance graph, and
the resolved N1-N4/F1-F6 findings are preserved. This section is current
authority for the three corrected surfaces; no other design authority is
reopened.

```text
R4_CORRECTION_AUTHORITY=THIS_SECTION_29_ONLY_FOR_R4_F1_R4_F2_R4_F3
R4_REVIEW_COMMENT_ID=5450059909
R4_F1_ID=TASK036_R3_D23_ACTIVE_INTERNAL_NODE_ARTIFACT_AUTHORITY_NOT_CLOSED
R4_F2_ID=TASK036_R3_D26_ACTIVE_RELEASE_VERSION_LITERAL_AMBIGUOUS
R4_F3_ID=TASK036_R3_D28_D31_DETERMINISM_SURFACE_CONTRACTION_UNMAPPED
SOURCE_DEFINITION_ISSUE=203
SOURCE_DEFINITION_REVISION=R5
SOURCE_DEFINITION_FROZEN=true
SOURCE_DECISION_COUNT=35
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_DECISION_MAPPING_CONTRADICTION_COUNT=0
SOURCE_SEMANTIC_CHANGE_COUNT=0
SOURCE_SEMANTIC_REINTERPRETATION_COUNT=0
NEW_SOURCE_DECISION_COUNT=0
TASK036_R4_NON_FINDING_AUTHORITY_REOPENED=false
TASK036_R4_NON_FINDING_AUTHORITY_CHANGED=false
```

### 29.1 Active node materialization authority

The active node table in Section 25.1 uses `Release artifact authority` only
for node-local materialization. The explicit node contract below is complete:
all twenty executable graph nodes are internal records, in-memory
projections, upstream public-result identities, or embedded evidence. None is
itself a persisted D23 release artifact. The six D23 artifacts are the only
release-authoritative paths and remain governed by Section 27.1.

| Node ID | Node class | Release artifact | Frozen artifact ID | Frozen artifact path | Persisted to disk | Internal only |
|---|---|---|---|---|---|---|
| `N00_RAW_DEMO_INPUT` | `RAW_BOUNDARY_INPUT` | false | `NONE` | `NONE` | false | true |
| `N01_DEMO_INPUT` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N02_TASK031_RESULT` | `UPSTREAM_PUBLIC_RESULT` | false | `NONE` | `NONE` | false | true |
| `N03_TASK032_RESULT` | `UPSTREAM_PUBLIC_RESULT` | false | `NONE` | `NONE` | false | true |
| `N04_TASK033_RESULT` | `UPSTREAM_PUBLIC_RESULT` | false | `NONE` | `NONE` | false | true |
| `N05_TASK034_RESULT` | `UPSTREAM_PUBLIC_RESULT` | false | `NONE` | `NONE` | false | true |
| `N06_TASK035_RESULT` | `UPSTREAM_PUBLIC_RESULT` | false | `NONE` | `NONE` | false | true |
| `N07_PRODUCTION_GRAPH_EVIDENCE` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N08_UPSTREAM_EVIDENCE_LEDGER` | `INTERNAL_RECORD` | false | `NONE` | `NONE` | false | true |
| `N09_BLOCKED_CASES_EVIDENCE` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N10_RELEASE_INPUT_BUNDLE` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N11_SUCCESS_IDENTITY_CORE` | `INTERNAL_IDENTITY_NODE` | false | `NONE` | `NONE` | false | true |
| `N12_CROSS_RUNTIME_DETERMINISM` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N13_REPEAT_RUN_DETERMINISM` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N14_ACCEPTANCE_CHECKLIST` | `EMBEDDED_EVIDENCE` | false | `NONE` | `NONE` | false | true |
| `N15_MANIFEST` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N16_RELEASE_ACCEPTANCE_LEDGER` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N17_PROVENANCE` | `INTERNAL_RECORD` | false | `NONE` | `NONE` | false | true |
| `N18_VERSION_METADATA` | `IN_MEMORY_PROJECTION` | false | `NONE` | `NONE` | false | true |
| `N19_FINAL_ACCEPTANCE_RESULT` | `EMBEDDED_EVIDENCE` | false | `NONE` | `NONE` | false | true |

```text
R4_NODE_MATERIALIZATION_NODE_COUNT=20
R4_NODE_MATERIALIZATION_FIELD_SET=(NODE_ID,NODE_CLASS,RELEASE_ARTIFACT,FROZEN_ARTIFACT_ID,FROZEN_ARTIFACT_PATH,PERSISTED_TO_DISK,INTERNAL_ONLY)
R4_NODE_MATERIALIZATION_FIELDS=(NODE_ID,NODE_CLASS,RELEASE_ARTIFACT,FROZEN_ARTIFACT_ID,FROZEN_ARTIFACT_PATH,PERSISTED_TO_DISK,INTERNAL_ONLY)
R4_NODE_MATERIALIZATION_UNIQUE_NODE_ID_COUNT=20
R4_NODE_MATERIALIZATION_NON_D23_ARTIFACT_COUNT=0
R4_NODE_MATERIALIZATION_RELEASE_ARTIFACT_TRUE_COUNT=0
R4_NODE_MATERIALIZATION_INTERNAL_ONLY_FALSE_COUNT=0
R4_FROZEN_D23_ARTIFACT_COUNT=6
R4_FROZEN_D23_ARTIFACT_AUTHORITY_SECTION=27.1
D23_MATCH=true
ARTIFACT_COUNT=6
UNIQUE_ARTIFACT_ID_COUNT=6
UNIQUE_ARTIFACT_PATH_COUNT=6
ACTIVE_ARTIFACT_AUTHORITY_TABLE_COUNT=1
ARTIFACT_BACKWARD_DEPENDENCY_COUNT=0
ARTIFACT_UNDEFINED_PRODUCER_COUNT=0
ARTIFACT_UNDEFINED_CONSUMER_INPUT_COUNT=0
ARTIFACT_DIGEST_CYCLE_COUNT=0
ARTIFACT_STAGE_DATAFLOW_REVIEW=PASS
COMPETING_ARTIFACT_AUTHORITY_COUNT=0
UNMARKED_OLD_ARTIFACT_REFERENCE_COUNT=0
INTERNAL_NODE_MISCLASSIFIED_AS_ARTIFACT_COUNT=0
EXTRA_RELEASE_AUTHORITATIVE_ARTIFACT_COUNT=0
MISSING_FROZEN_ARTIFACT_COUNT=0
R4_COMPETING_ARTIFACT_AUTHORITY_COUNT=0
R4_UNMARKED_OLD_ARTIFACT_REFERENCE_COUNT=0
R4_INTERNAL_NODE_MISCLASSIFIED_AS_ARTIFACT_COUNT=0
R4_EXTRA_RELEASE_AUTHORITATIVE_ARTIFACT_COUNT=0
R4_MISSING_FROZEN_ARTIFACT_COUNT=0
R4_ARTIFACT_INVENTORY_CLOSED=true
```

### 29.2 Active stage materialization effects

The active stage interfaces in Section 25.2 have two distinct effects. An
`INTERNAL_OUTPUT_EFFECT` names an internal record or transient request. A
`PERSISTED_ARTIFACT_EFFECT` names only one of the six frozen D23 artifact IDs.
The S00 code/test entries are repository-checkout inputs validated at the raw
boundary; they are not created by the runtime operation and therefore have no
runtime stage effect. No internal node is promoted to an artifact by a stage
effect.

```text
R4_PERSISTED_ARTIFACT_EFFECT_ALLOWED_IDS=(TASK036_RELEASE_RUNNER,TASK036_RELEASE_TEST_MODULE,TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN,TASK036_RELEASE_MANIFEST_JSON,TASK036_RELEASE_ACCEPTANCE_MARKDOWN)
R4_PERSISTED_ARTIFACT_EFFECT_ALLOWED_COUNT=6
R4_STAGE_INTERNAL_OUTPUT_EFFECTS_COMPLETE=true
R4_STAGE_PERSISTED_ARTIFACT_EFFECTS_COMPLETE=true
R4_STAGE_ARTIFACT_EFFECT_NON_D23_REFERENCE_COUNT=0
R4_STAGE_INTERNAL_RECORD_AS_ARTIFACT_COUNT=0
R4_ARTIFACT_STAGE_DATAFLOW_REVIEW=PASS
DYNAMIC_MANIFEST_DISCOVERY_ALLOWED=false
SOURCE_D32_TEST_PATH_MATCH=true
```

The persisted effects are closed by stage:

```text
S00_PERSISTED_ARTIFACT_EFFECT=NONE
S14_PERSISTED_ARTIFACT_EFFECT=(TASK036_DEMO_JSON,TASK036_DEMO_MARKDOWN)
S17_PERSISTED_ARTIFACT_EFFECT=(TASK036_RELEASE_ACCEPTANCE_MARKDOWN)
S18_PERSISTED_ARTIFACT_EFFECT=(TASK036_RELEASE_MANIFEST_JSON)
ALL_OTHER_STAGE_PERSISTED_ARTIFACT_EFFECT=NONE
R4_REPOSITORY_CHECKOUT_ARTIFACT_AUTHORITY=(TASK036_RELEASE_RUNNER,TASK036_RELEASE_TEST_MODULE)
R4_REPOSITORY_CHECKOUT_ARTIFACT_PRODUCER=REPOSITORY_CHECKOUT
R4_REPOSITORY_CHECKOUT_ARTIFACT_RUNTIME_STAGE_EFFECT=NONE
```

The six persisted effects above are exactly the six roles and paths in
Section 27.1. N01/N08/N09/N11-N16/N18/N19 and every other non-D23 node remain
internal, embedded, or in-memory projections even when their canonical hash
contracts are retained.

### 29.3 Exact active distribution-version authority

The active final-result derivation in Section 25.3 is bound to the exact
frozen distribution version. `v0.3` may appear in a title, a frozen repository
path token, a historical heading, or a human display label, but it never acts
as a distribution-version value or identity input.

```text
ACTIVE_DISTRIBUTION_VERSION=0.3.0
TARGET_DISTRIBUTION_VERSION=0.3.0
TASK036_RELEASE_VERSION=0.3.0
FINAL_RESULT_RELEASE_VERSION_SOURCE=TARGET_DISTRIBUTION_VERSION_0.3.0
FINAL_RESULT_RELEASE_VERSION_DERIVATION_RULE=frozen TARGET_DISTRIBUTION_VERSION 0.3.0
V03_DISPLAY_LABEL_ONLY=true
V03_DISPLAY_LABEL_IS_NOT_DISTRIBUTION_VERSION=true
V03_IDENTITY_PARTICIPATION=false
V03_PREHASH_PARTICIPATION=false
V03_MANIFEST_VERSION_VALUE=false
V03_VERSION_METADATA_VALUE=false
V03_PACKAGE_VERSION_VALUE=false
AMBIGUOUS_VERSION_LITERAL_COUNT=0
WRONG_DISTRIBUTION_VERSION_REFERENCE_COUNT=0
VERSION_BEARING_FILES=(pyproject.toml,uv.lock)
PYPROJECT_TOML_VERSION_UPDATE_ALLOWED_IN_IMPLEMENTATION=true
UV_LOCK_VERSION_UPDATE_ALLOWED_IN_IMPLEMENTATION=true
VERSION_BUMP_DEPENDENCY_RESOLUTION_CHANGE_ALLOWED=false
PYPROJECT_TOML_MUTATED_NOW=false
UV_LOCK_MUTATED_NOW=false
```

The fixed `v0_3` spelling in `scripts/release_demo/v0_3_task020_to_task035.py`
and `tests/release_demo/test_v0_3_task020_to_task035.py` is a frozen path token,
not a version-bearing value. Historical R2 `v0.3` declarations remain
explicitly superseded by Sections 27.3 and 29.3.

### 29.4 Historical determinism surface map

The following is the exact R4 lineage map from the nine historical R2
surface records in Section 25.8 to the seven active R3/R4 surfaces in Section
27.6. `RETAINED` means that the historical semantic coverage is represented
by the explicitly named active release projection or final identity surface;
it does not create a second artifact path. The only removed historical
surfaces are DS02 and DS03, both standalone TASK035 internal canonical-byte
comparisons. Their producer hashes and result identities remain carried in
the frozen upstream evidence and final-result projections.

| Historical surface ID | Historical surface name | Historical producer | Historical surface type | Related artifact or internal node | R4 status | Active R4 surface ID if retained | Removal reason if removed | Frozen Source requires surface | Source authority | Related removed non-frozen artifact authority |
|---|---|---|---|---|---|---|---|---|---|---|
| `DS01` | `demo_input_canonical_bytes` | `N01/S01` | internal canonical input | `N01_DEMO_INPUT` / historical `TASK036_DEMO_INPUT` | `RETAINED` | `DS01` | `NONE` | true | D28-D31 deterministic release JSON projection | `NONE` |
| `DS02` | `task035_request_canonical_bytes` | `S10/TASK035_V2_PUBLIC_REQUEST` | internal upstream request | `TASK035_REQUEST_CANONICAL_INTERNAL` | `REMOVED` | `NONE` | not a frozen D23 persisted artifact and not a named D28-D31 JSON/Markdown surface; upstream request identity remains in the public producer evidence | false | D28-D31 enumerate release evidence bytes and final identity surfaces, not a standalone Task035 request-byte surface | `NONE` |
| `DS03` | `task035_success_canonical_bytes` | `N06/S11` | internal upstream result | `TASK035_SUCCESS_CANONICAL_INTERNAL` | `REMOVED` | `NONE` | not a frozen D23 persisted artifact and not a named D28-D31 JSON/Markdown surface; Task035 result hash and ID remain in the public producer evidence | false | D28-D31 enumerate release evidence bytes and final identity surfaces, not a standalone Task035 success-byte surface | `NONE` |
| `DS04` | `task036_provenance_canonical_bytes` | `N17/S20` | embedded provenance evidence | `N17_PROVENANCE` | `RETAINED` | `DS03` | `NONE` | true | D28-D31 release Markdown evidence plus preserved provenance contract | `NONE` |
| `DS05` | `release_acceptance_ledger_canonical_bytes` | `N16/S19` | internal acceptance evidence | `N16_RELEASE_ACCEPTANCE_LEDGER` | `RETAINED` | `DS04` | `NONE` | true | D28-D31 release acceptance Markdown evidence | `NONE` |
| `DS06` | `acceptance_checklist_canonical_bytes` | `N14/S17` | embedded acceptance evidence | `N14_ACCEPTANCE_CHECKLIST` | `RETAINED` | `DS04` | `NONE` | true | D28-D31 release acceptance Markdown evidence | `NONE` |
| `DS07` | `manifest_canonical_bytes` | `N15/S18` | persisted manifest JSON | `N15_MANIFEST` | `RETAINED` | `DS02` | `NONE` | true | D25/D28-D31 exact manifest peer bytes | `NONE` |
| `DS08` | `version_metadata_canonical_bytes` | `N18/S21` | embedded version evidence | `N18_VERSION_METADATA` | `RETAINED` | `DS03` | `NONE` | true | D26/D28-D31 version-bearing evidence projection | `NONE` |
| `DS09` | `task036_success_result_canonical_bytes` | `N11/S15` | final identity core | `N11_SUCCESS_IDENTITY_CORE` | `RETAINED` | `DS05,DS06,DS07` | `NONE` | true | preserved D31 final canonical/hash/ID correction authority | `NONE` |

```text
PRE_R3_DETERMINISM_SURFACE_MAP=TABLE_9_ROWS_DS01_THROUGH_DS09
ACTIVE_DETERMINISM_SURFACE_TABLE=TABLE_7_ROWS_DS01_THROUGH_DS07
REMOVED_SURFACE_DS02_RELATED_TO_REMOVED_NON_FROZEN_ARTIFACT=false
REMOVED_SURFACE_DS03_RELATED_TO_REMOVED_NON_FROZEN_ARTIFACT=false
REMOVED_SURFACE_DS02_RELATED_TO_REMOVED_NON_FROZEN_ARTIFACT_AUTHORITIES=NONE_DIRECT_RELATION
REMOVED_SURFACE_DS03_RELATED_TO_REMOVED_NON_FROZEN_ARTIFACT_AUTHORITIES=NONE_DIRECT_RELATION
REMOVED_SURFACE_DS02_FROZEN_D28_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS02_FROZEN_D29_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS02_FROZEN_D30_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS02_FROZEN_D31_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS02_REMOVAL_SOURCE_COMPATIBLE=true
REMOVED_SURFACE_DS03_FROZEN_D28_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS03_FROZEN_D29_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS03_FROZEN_D30_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS03_FROZEN_D31_REQUIRES_SURFACE=false
REMOVED_SURFACE_DS03_REMOVAL_SOURCE_COMPATIBLE=true
```

The active seven surface rows are frozen below. The historical-to-active
mapping is intentionally explicit where release evidence consolidates
internal records and where DS09 is represented by three final identity
surfaces; no unlisted mapping may be supplied by implementation.

| Active surface ID | Surface name | Producer | Surface type | Canonical bytes, digest, or ID | Python 3.11 repeat | Python 3.12 repeat | Cross-Python required | Source authority | Historical DS ID |
|---|---|---|---|---|---|---|---|---|---|
| `DS01` | `task020_to_task035_demo_json_bytes` | `S14/N10` | persisted JSON evidence | exact final UTF-8 JSON bytes and SHA-256 | true | true | true | D28-D31 | `DS01` |
| `DS02` | `release_manifest_json_bytes` | `S18/N15` | persisted manifest JSON | exact final UTF-8 JSON bytes and SHA-256 | true | true | true | D25/D28-D31 | `DS07` |
| `DS03` | `task020_to_task035_demo_markdown_bytes` | `S14/N10` | persisted Markdown evidence | exact normalized UTF-8 Markdown bytes and SHA-256 | true | true | true | D28-D31 | `DS04,DS08` |
| `DS04` | `release_acceptance_markdown_bytes` | `S17/N14` | persisted acceptance Markdown | exact normalized UTF-8 Markdown bytes and SHA-256 | true | true | true | D28-D31 | `DS05,DS06` |
| `DS05` | `TASK036_final_result_canonical_bytes` | `S15/N11` | final identity canonical bytes | exact N11 success prehash canonical bytes | true | true | true | preserved D31 final identity correction | `DS09` |
| `DS06` | `TASK036_final_result_hash` | `S15/N11` | final SHA-256 identity | exact lowercase N11 result hash | true | true | true | preserved D31 final identity correction | `DS09` |
| `DS07` | `TASK036_internal_result_id` | `S15/N11` | final UUIDv5 identity | exact TASK036 internal result ID, not release acceptance result ID | true | true | true | preserved D31 final identity correction | `DS09` |

```text
PRE_R3_DETERMINISM_SURFACE_COUNT=9
R4_RETAINED_DETERMINISM_SURFACE_COUNT=7
R4_REMOVED_DETERMINISM_SURFACE_COUNT=2
REMOVED_DETERMINISM_SURFACE_01=DS02 task035_request_canonical_bytes
REMOVED_DETERMINISM_SURFACE_02=DS03 task035_success_canonical_bytes
REMOVED_SURFACE_MEMBERSHIP_FROZEN=true
DETERMINISM_SURFACE_COUNT=7
TASK036_DETERMINISM_SURFACE_COUNT=7
TASK036_DETERMINISM_SURFACE_IDS=(DS01,DS02,DS03,DS04,DS05,DS06,DS07)
TASK036_DETERMINISM_SURFACES=(task020_to_task035_demo_json_bytes,release_manifest_json_bytes,task020_to_task035_demo_markdown_bytes,release_acceptance_markdown_bytes,TASK036_final_result_canonical_bytes,TASK036_final_result_hash,TASK036_internal_result_id)
TASK036_DETERMINISM_ARTIFACT_BYTE_SURFACES=(release_evidence/v0.3.0/task020-to-task035-demo.json,release_evidence/v0.3.0/release-manifest.json,release_evidence/v0.3.0/task020-to-task035-demo.md,release_evidence/v0.3.0/release-acceptance.md)
PY311_REPEAT_SURFACE_COUNT=7
PY312_REPEAT_SURFACE_COUNT=7
CROSS_PYTHON_SURFACE_COUNT=7
SURFACE_COUNT_MISMATCH_COUNT=0
DETERMINISM_SURFACE_MEMBERSHIP_UNFROZEN_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_FROM_DETERMINISM_COUNT=0
RELEASE_ACCEPTANCE_RESULT_ID_DETERMINISM_REQUIRED=false
RELEASE_ACCEPTANCE_RESULT_ID_DETERMINISM_SOURCE_AUTHORITY=D27_RELEASE_ACCEPTANCE_RESULT_ID_IS_SHA256_LEDGER_IDENTITY_AND_IS_NOT_THE_TASK036_INTERNAL_RESULT_ID_SURFACE
TASK036_FINAL_RESULT_CANONICAL_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_HASH_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_ID_SURFACE_INCLUDED=true
TASK036_FINAL_RESULT_ID_EQUALS_TASK036_INTERNAL_RESULT_ID=true
TASK036_FINAL_RESULT_ID_IS_NOT_RELEASE_ACCEPTANCE_RESULT_ID=true
DETERMINISM_EVIDENCE_HASH_PREHASH_EXCLUSION_ALLOWED=true
DETERMINISM_EVIDENCE_EXCLUSION_SOURCE_AUTHORITY=H11_DETERMINISM_EVIDENCE_OWN_evidence_hash_SELF_EXCLUSION_FROM_THE_FROZEN_SOURCE_D24_NORMALIZATION_RULE
DETERMINISM_EVIDENCE_EXCLUSION_BREAKS_REQUIRED_SEMANTIC_IDENTITY=false

PREVIOUS_OPEN_DISCRETION_01=TASK036_R3_D23_ACTIVE_INTERNAL_NODE_ARTIFACT_AUTHORITY_NOT_CLOSED
CLOSURE_01=SECTION_29.1_SECTION_29.2_R4_F1
PREVIOUS_OPEN_DISCRETION_02=TASK036_R3_D26_ACTIVE_RELEASE_VERSION_LITERAL_AMBIGUOUS
CLOSURE_02=SECTION_29.3_R4_F2
PREVIOUS_OPEN_DISCRETION_03=TASK036_R3_D28_D31_DETERMINISM_SURFACE_CONTRACTION_UNMAPPED
CLOSURE_03=SECTION_29.4_R4_F3
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
PREVIOUS_UNFROZEN_IDENTITY_RULE_COUNT=1
PREVIOUS_UNFROZEN_IDENTITY_RULE_01=TASK036_R3_D28_D31_DETERMINISM_SURFACE_CONTRACTION_UNMAPPED
CLOSURE=SECTION_29.4_PRE_R3_DS01_DS09_MAP_R4_RETAINED_7_REMOVED_2_AND_D28_D31_RATIONALE
IDENTITY_RULE_CLOSURE_COUNT=1
UNFROZEN_IDENTITY_RULE_COUNT=0
```

For the two removed surfaces, the frozen D28-D31 decisions require the
deterministic runtime protocol and the exact JSON/Markdown release bytes; they
do not require standalone canonical-byte comparison of the Task035 request or
success payload. The final Task035 request/result identities remain required
upstream evidence and are not deleted by this comparison-surface contraction.

### 29.5 Preserved graphs, contracts, test authority, and allowlists

R4 changes no graph or contract outside the three corrected projections.

```text
HASHED_CONTRACT_COUNT=11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT=11
HASH_CONTRACT_FOR_REMOVED_ARTIFACT_COUNT=0
HASH_CONTRACT_WITHOUT_SOURCE_OR_MECHANICAL_AUTHORITY_COUNT=0
IDENTITY_NODE_COUNT=20
IDENTITY_EDGE_COUNT=56
IDENTITY_DATAFLOW_ACYCLIC=true
TOPOLOGICAL_SORT_EXISTS=true
CIRCULAR_PREHASH_REFERENCE_COUNT=0
FORWARD_REFERENCE_COUNT=0
UNDEFINED_IDENTITY_DEPENDENCY_COUNT=0
RESULT_ID_SELF_REFERENCE_COUNT=0
RESULT_HASH_RESULT_ID_CYCLE_COUNT=0
CORRECTED_RUNTIME_STAGE_COUNT=23
STAGE_TOPOLOGY_EXECUTABLE=true
STAGE_BACKWARD_DEPENDENCY_COUNT=0
STAGE_PRODUCER_CONSUMER_CONTRADICTION_COUNT=0
SOURCE_D25_MANIFEST_PEER_COUNT=3
MANIFEST_PEER_COUNT=3
MANIFEST_EXTRA_PEER_COUNT=0
MANIFEST_MISSING_PEER_COUNT=0
MANIFEST_FORWARD_REFERENCE_COUNT=0
MANIFEST_DIGEST_CYCLE_COUNT=0
SOURCE_D32_TEST_ID_COUNT=22
TEST_ID_COUNT=22
UNIQUE_TEST_ID_COUNT=22
TEST_ID_MEMBERSHIP_MATCHES_FROZEN_D32=true
TEST_COVERAGE_GAP_COUNT=0
ASSERTION_WITHOUT_FROZEN_TEST_ID_COUNT=0
TASK036_BLOCKER_REGISTRY_COUNT=22
N1_STATUS=REMAINS_RESOLVED
N2_STATUS=REMAINS_RESOLVED
N3_STATUS=REMAINS_RESOLVED
N4_STATUS=REMAINS_RESOLVED
F1_STATUS=REMAINS_RESOLVED
F2_STATUS=REMAINS_RESOLVED
F3_STATUS=REMAINS_RESOLVED
F4_STATUS=REMAINS_RESOLVED
F5_STATUS=REMAINS_RESOLVED
F6_STATUS=REMAINS_RESOLVED
TASK036_INTERNAL_RESULT_ID_AND_RELEASE_ACCEPTANCE_RESULT_ID_DISTINCT=true
```

The exact six D23 paths, three D25 manifest peers, and twenty-two D32 test
IDs remain those already frozen in Sections 27.1, 27.2, and 27.4. The
cross-category implementation allowlist duplicate remains intentional:

```text
TOTAL_IMPLEMENTATION_MUTATION_ALLOWLIST_COUNT=18
UNIQUE_IMPLEMENTATION_MUTATION_PATH_COUNT=17
CROSS_CATEGORY_DUPLICATE_PATH_COUNT=1
CROSS_CATEGORY_DUPLICATE_PATHS=(tests/release_demo/test_v0_3_task020_to_task035.py)
CROSS_CATEGORY_DUPLICATE_PATH_IS_INTENTIONAL=true
CROSS_CATEGORY_DUPLICATE_PATH_CATEGORY_A=IMPLEMENTATION_TEST_FILE_ALLOWLIST
CROSS_CATEGORY_DUPLICATE_PATH_CATEGORY_B=IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST
CROSS_CATEGORY_DUPLICATE_PATH_SOURCE_AUTHORITY=D23_RELEASE_AUTHORITATIVE_TEST_MODULE_AND_D32_TEST_PATH
CROSS_CATEGORY_DUPLICATE_PATH_SEMANTIC_CONFLICT=false
```

### 29.6 HISTORICAL_SUPERSEDED — R4 finding closure and lifecycle

This subsection is a historical R4 receipt. Its lifecycle declarations and R4
next-gate values are `HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY`; the sole
current lifecycle authority is Section 30.

```text
R4_F1_STATUS=RESOLVED_BY_DESIGN_R4_CORRECTION
R4_F1_SECTION_REF=25.1,25.2,29.1,29.2
R4_F2_STATUS=RESOLVED_BY_DESIGN_R4_CORRECTION
R4_F2_SECTION_REF=25.3,27.3,29.3
R4_F3_STATUS=RESOLVED_BY_DESIGN_R4_CORRECTION
R4_F3_SECTION_REF=25.8,27.6,29.4

TASK036_R4_F1_CLOSED=true
TASK036_R4_F2_CLOSED=true
TASK036_R4_F3_CLOSED=true
TASK036_R4_CLOSED_FINDING_COUNT=3
TASK036_R4_REOPENED_NON_FINDING_COUNT=0
TASK036_R4_NEW_FINDING_COUNT=0
TASK036_R4_NEW_FINDINGS=NONE
R4_NEW_INTERNAL_FINDING_COUNT=0
R4_NEW_INTERNAL_FINDINGS=NONE
DESIGN_INTERNAL_CONTRADICTION_COUNT=0
COUNT_CONTRADICTION_COUNT=0
CROSS_SECTION_AUTHORITY_CONTRADICTION_COUNT=0
UNRESOLVED_TASK036_DESIGN_AUTHORITY_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0
```

Sections 27.8 and 28 are historical R3 receipts. This subsection records the
superseded R4 lifecycle boundary and is not current authority:

```text
TASK036_ACTIVE_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R4_INDEPENDENT_REVIEW_ONLY
CURRENT_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R4_INDEPENDENT_REVIEW_ONLY
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R4_INDEPENDENT_REVIEW_ONLY
ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=1
COMPETING_ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=0
TASK036_DESIGN_R4_CORRECTION_COMPLETE=true
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_R4_CORRECTION=true
TASK036_DESIGN_REVIEWED=false
TASK036_DESIGN_REVIEW_RESULT=PENDING_INDEPENDENT_R4_REREVIEW
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
```

### 29.7 HISTORICAL_SUPERSEDED — R4 authoring boundary and out-of-band candidate identity

This subsection is a historical R4 authoring receipt. Its lifecycle and
next-gate declarations are `HISTORICAL_SUPERSEDED_NON_CURRENT_AUTHORITY`; the
current R5 lifecycle is defined only in Section 30.

This R4 correction mutates only this Design file. It does not modify the
frozen Source Definition, Issue #203, TASK031-TASK035 authority, code, tests,
artifacts, project metadata, CI, workflow, index, branch, commit, PR, merge,
tag, release, or downstream task authorization. The R4 identity is reported
after the final UTF-8 bytes are hashed and is not embedded in the Design.

```text
TASK036_R4_AUTHORING_CHANGED_FILE_COUNT=1
TASK036_R4_AUTHORING_CHANGED_FILES=(docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md)
TASK036_R4_DESIGN_MUTATED=true
TASK036_R4_SOURCE_DEFINITION_MUTATED=false
TASK036_R4_ISSUE203_MUTATED=false
TASK036_R4_TASK036_CODE_MUTATED=false
TASK036_R4_TASK036_TESTS_MUTATED=false
TASK036_R4_TASK036_ARTIFACTS_MUTATED=false
TASK036_R4_PYPROJECT_TOML_MUTATED_NOW=false
TASK036_R4_UV_LOCK_MUTATED_NOW=false
TASK036_R4_CI_MUTATED=false
TASK036_R4_WORKFLOW_MUTATED=false
TASK036_R4_INDEX_MUTATED=false
TASK036_R4_BRANCH_CREATED=false
TASK036_R4_COMMIT_CREATED=false
TASK036_R4_PUSH_PERFORMED=false
TASK036_R4_PR_CREATED=false
TASK036_R4_MERGE_PERFORMED=false
TASK036_R4_TAG_MUTATED=false
TASK036_R4_RELEASE_MUTATED=false

TASK036_DESIGN_R4_CORRECTION_COMPLETE=true
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_CORRECTION=true
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
```

```text
R4_DESIGN_IDENTITY_REPORTED_OUT_OF_BAND=true
R4_DESIGN_FILE_SHA256=REPORTED_OUT_OF_BAND_AFTER_FILE_HASH
R4_DESIGN_DIFF_SHA256=REPORTED_OUT_OF_BAND_AFTER_DIFF_HASH
R4_DESIGN_LINE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_COUNT
R4_DESIGN_BYTE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_SIZE
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R4_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```

## 30. R5 correction overlay — active D35 lifecycle mapping

This section is the sole current lifecycle authority for the R5 corrected
Design candidate. Sections 22, 27.8, 29.6, and 29.7 are retained only as
historical audit receipts and do not participate in current authority
resolution. D35 is a lifecycle projection only; it does not authorize any
downstream repository or release mutation.

```text
TASK036_R5_CORRECTION_AUTHORITY_STATUS=EFFECTIVE
TASK036_R5_CORRECTION_SCOPE=(R5_F1)
TASK036_R5_CORRECTION_SCOPE_ONLY=true
TASK036_R5_NON_FINDING_AUTHORITY_REOPENED=false
TASK036_R5_NON_FINDING_AUTHORITY_CHANGED=false
R5_F1_ID=TASK036_R4_D35_ACTIVE_SOURCE_MAPPING_POINTS_TO_SUPERSEDED_R3_LIFECYCLE
R5_F1_STATUS=RESOLVED_BY_DESIGN_R5_CORRECTION
R5_F1_SECTION_REF=20,29.6,29.7,30

SOURCE_MAPPING_D35_STATUS=RESOLVED
SOURCE_MAPPING_D35_CURRENT_AUTHORITY=SECTION_30_R5_ACTIVE_LIFECYCLE
SOURCE_MAPPING_D35_HISTORICAL_REFERENCES=(SECTION_22,SECTION_27.8,SECTION_29.6,SECTION_29.7)
SOURCE_MAPPING_D35_HISTORICAL_REFERENCES_MARKED_SUPERSEDED=true
SOURCE_MAPPING_D35_ACTIVE_R3_GATE_REFERENCE_COUNT=0
SOURCE_MAPPING_D35_ACTIVE_R4_GATE_REFERENCE_COUNT=0
SOURCE_MAPPING_D35_ACTIVE_R5_GATE_REFERENCE_COUNT=1
SOURCE_MAPPING_D35_CONTRADICTION_COUNT=0

SOURCE_DECISION_COUNT=35
SOURCE_DECISION_MAPPED_COUNT=35
SOURCE_DECISION_UNMAPPED_COUNT=0
SOURCE_DECISION_MAPPING_CONTRADICTION_COUNT=0
SOURCE_SEMANTIC_CHANGE_COUNT=0
SOURCE_SEMANTIC_REINTERPRETATION_COUNT=0
NEW_SOURCE_DECISION_COUNT=0
D01_THROUGH_D35_ALL_MAPPED=true

TASK036_ACTIVE_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R5_INDEPENDENT_REVIEW_ONLY
CURRENT_NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R5_INDEPENDENT_REVIEW_ONLY
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R5_INDEPENDENT_REVIEW_ONLY
ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=1
COMPETING_ACTIVE_LIFECYCLE_NEXT_GATE_COUNT=0
NO_STEP_IMPLIES_THE_NEXT=true

TASK036_DESIGN_R5_CORRECTION_COMPLETE=true
TASK036_DESIGN_REVIEW_REQUIRED_AFTER_R5_CORRECTION=true
TASK036_DESIGN_AUTHORED=true
TASK036_DESIGN_REVIEWED=false
TASK036_DESIGN_REVIEW_RESULT=PENDING_INDEPENDENT_R5_REREVIEW
TASK036_DESIGN_ACCEPTED=false
TASK036_DESIGN_FROZEN=false
TASK036_IMPLEMENTATION_AUTHORIZED=false
TASK036_RELEASE_AUTHORIZED=false
TASK036_TAG_AUTHORIZED=false
TASK036_ISSUE_CLOSE_AUTHORIZED=false
TASK037_AUTHORIZED=false
TASK038_AUTHORIZED=false
TASK039_AUTHORIZED=false
NEXT_GATE_AUTHORIZED=false

UNMARKED_HISTORICAL_LIFECYCLE_REFERENCE_COUNT=0
COUNT_CONTRADICTION_COUNT=0
DESIGN_INTERNAL_CONTRADICTION_COUNT=0
CROSS_SECTION_AUTHORITY_CONTRADICTION_COUNT=0
UNRESOLVED_TASK036_DESIGN_AUTHORITY_COUNT=0
OPEN_IMPLEMENTATION_DISCRETION_COUNT=0
UNFROZEN_IDENTITY_RULE_COUNT=0
R5_NEW_INTERNAL_FINDING_COUNT=0
R5_NEW_INTERNAL_FINDINGS=NONE
```

The R5 correction changes only the active D35 mapping and its directly related
lifecycle cross-reference. It does not authorize Design acceptance or freeze,
implementation, delivery, CI, release evidence acceptance, tag, GitHub
Release, Issue close, or TASK037+.

```text
TASK036_R5_AUTHORING_CHANGED_FILE_COUNT=1
TASK036_R5_AUTHORING_CHANGED_FILES=(docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md)
TASK036_R5_DESIGN_MUTATED=true
TASK036_R5_SOURCE_DEFINITION_MUTATED=false
TASK036_R5_ISSUE203_MUTATED=false
TASK036_R5_TASK031_MUTATED=false
TASK036_R5_TASK032_MUTATED=false
TASK036_R5_TASK033_MUTATED=false
TASK036_R5_TASK034_MUTATED=false
TASK036_R5_TASK035_MUTATED=false
TASK036_R5_TASK036_CODE_MUTATED=false
TASK036_R5_TASK036_TESTS_MUTATED=false
TASK036_R5_TASK036_ARTIFACTS_MUTATED=false
TASK036_R5_PYPROJECT_TOML_MUTATED_NOW=false
TASK036_R5_UV_LOCK_MUTATED_NOW=false
TASK036_R5_CI_MUTATED=false
TASK036_R5_WORKFLOW_MUTATED=false
TASK036_R5_INDEX_MUTATED=false
TASK036_R5_BRANCH_CREATED=false
TASK036_R5_COMMIT_CREATED=false
TASK036_R5_PUSH_PERFORMED=false
TASK036_R5_PR_CREATED=false
TASK036_R5_MERGE_PERFORMED=false
TASK036_R5_TAG_MUTATED=false
TASK036_R5_RELEASE_MUTATED=false
```

```text
R5_DESIGN_IDENTITY_REPORTED_OUT_OF_BAND=true
R5_DESIGN_FILE_SHA256=REPORTED_OUT_OF_BAND_AFTER_FILE_HASH
R5_DESIGN_DIFF_SHA256=REPORTED_OUT_OF_BAND_AFTER_DIFF_HASH
R5_DESIGN_LINE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_COUNT
R5_DESIGN_BYTE_COUNT=REPORTED_OUT_OF_BAND_AFTER_FILE_SIZE
NEXT_GATE=AUTHORIZE_TASK036_DESIGN_R5_INDEPENDENT_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true
STOP=true
```
