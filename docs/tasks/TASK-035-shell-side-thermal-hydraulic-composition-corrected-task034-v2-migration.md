# TASK-035 Corrected TASK-034 v2 Migration Delta

TASK=TASK035_CORRECTED_TASK034_V2_MIGRATION_DELTA_DESIGN_AUTHORING_ONLY
AUTHORIZATION=TASK035_CORRECTED_TASK034_V2_MIGRATION_DELTA_DESIGN_AUTHORING_ONLY
AUTHORIZATION_SOURCE=explicit_user_authorization

DESIGN_STATUS=AUTHORED_NOT_REVIEWED_NOT_ACCEPTED
TASK035_V2_DESIGN_AUTHORED=true
TASK035_V2_DESIGN_REVIEWED=false
TASK035_V2_DESIGN_ACCEPTED=false
TASK035_V2_MIGRATION_EXECUTION_AUTHORIZED=false

This document freezes only the TASK035-own deterministic contract delta required
when TASK035 migrates from its merged v1 producer boundary to the accepted
TASK034 corrected v2 producer contract. It does not redesign TASK035
composition engineering semantics, TASK034 engineering behavior, or TASK036.

## 1. Authority and lifecycle boundary

ORIGIN_MAIN_SHA=abd6bcc3abd0c665fd25c6a2621b0cd704e1e30d
ORIGIN_MAIN_TREE=2c0b53052ae2487630a8674f09406e6be969bacb
TASK034_DELIVERY_COMMIT=e015c31f826647b6bd842db1a4168da7f91cbfb1
TASK034_ACCEPTED_DESIGN_REVISION=R5-C1
TASK034_ACCEPTED_CONTRACT_VERSION=v2
TASK034_POST_MERGE_BYTES_VERIFIED=true

TASK035_DESIGN_AUTHORITY_PATH=docs/tasks/TASK-035-shell-side-thermal-hydraulic-composition-corrected-task034-v2-migration.md
TASK035_DESIGN_AUTHORITY_SOURCE=accepted TASK034 R5-C1 downstream compatibility boundary plus origin/main TASK035 implementation
TASK035_SEPARATE_DESIGN_IMPLEMENTATION_REVIEW_REQUIRED=true

TASK035_COMPATIBILITY_POLICY=MIGRATE_ENTIRELY_TO_CORRECTED_TASK034_V2
TASK035_V1_ACCEPTANCE_AFTER_MIGRATION=false
TASK035_DUAL_VERSION_ACCEPTANCE=false
TASK035_FIELD_SUBSET_ACCEPTANCE=false
TASK035_PRESSURE_DROP_RECOMPUTATION_ALLOWED=false
TASK035_ENGINEERING_RECOMPUTATION_ALLOWED=false
TASK035_IDENTITY_REWRITE_ALLOWED=false
TASK035_WRONG_OR_MIXED_TASK034_VERSION_BEHAVIOR=FAIL_CLOSED
TASK035_TASK034_MIGRATION_POLICY=MIGRATE_ENTIRELY_TO_CORRECTED_TASK034_V2

TASK035_V1_CONTRACT_STATUS=HISTORICAL_SUPERSEDED_AFTER_SEPARATE_V2_MIGRATION_ACCEPTANCE
TASK035_V1_IDENTIFIERS_MUST_NOT_DENOTE_V2=true
TASK035_V2_CURRENT_REMOTE_AUTHORITY=false
CURRENT_REMOTE_TASK035_CONTRACT=MERGED_V1

## 2. Migration delta scope

The current origin/main TASK035 implementation has a seven-field request,
forty-one-field success result, twenty-five-field typed-blocked result,
eight-field raw-boundary result, thirty-six-field provenance projection, and
forty-two blocker authorities across nineteen validation stages. Its nested
TASK034 contract references v1 schema tokens, v1 ordered field lists, v1
canonical namespaces, and the merged v1 TASK034 result-ID contract.

The corrected target changes the TASK035 deterministic contract because the
nested TASK034 producer projection changes. The outer TASK035 field names and
orders remain unchanged. The nested TASK034 projection, version tokens,
canonical namespaces, provenance values, and result-ID namespace change
according to this document.

TASK035_OUTER_DETERMINISTIC_CONTRACT_CHANGE=true
TASK035_OUTER_REQUEST_FIELD_MEMBERSHIP_CHANGE=false
TASK035_OUTER_SUCCESS_FIELD_MEMBERSHIP_CHANGE=false
TASK035_OUTER_TYPED_BLOCKED_FIELD_MEMBERSHIP_CHANGE=false
TASK035_OUTER_RAW_BOUNDARY_FIELD_MEMBERSHIP_CHANGE=false
TASK035_OUTER_PROVENANCE_FIELD_MEMBERSHIP_CHANGE=false
TASK035_TASK034_PRODUCER_EDGE_CONTRACT_CHANGE=true

## 3. TASK035 v2 identifiers

TASK035_TARGET_CONTRACT_VERSION=v2
TASK035_TARGET_REQUEST_SCHEMA_VERSION=task035.shell-side-thermal-hydraulic-composition-request.v2
TASK035_TARGET_SUCCESS_SCHEMA_VERSION=task035.shell-side-thermal-hydraulic-composition.v2
TASK035_TARGET_TYPED_BLOCKED_SCHEMA_VERSION=task035.shell-side-thermal-hydraulic-composition-blocked.v2
TASK035_TARGET_RAW_BOUNDARY_SCHEMA_VERSION=task035.shell-side-thermal-hydraulic-composition-raw-boundary-blocked.v2
TASK035_TARGET_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.v2
TASK035_TARGET_APPLICABILITY_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.applicability.v2
TASK035_TARGET_COMPLETENESS_PROFILE_ID=hxforge.shell_tube.shell_side_thermal_hydraulic_composition.completeness.v2
TASK035_TARGET_IMPLEMENTATION_SOFTWARE_VERSION=task035.shell-side-thermal-hydraulic-composition-impl-v2

TASK035_TARGET_REQUEST_HASH_NAMESPACE=task035.request.v2
TASK035_TARGET_SUCCESS_HASH_NAMESPACE=task035.success-result.v2
TASK035_TARGET_TYPED_BLOCKED_HASH_NAMESPACE=task035.typed-blocked-result.v2
TASK035_TARGET_RAW_BOUNDARY_HASH_NAMESPACE=task035.raw-boundary-blocked-result.v2
TASK035_TARGET_PROVENANCE_NAMESPACE=task035.provenance.v2
TASK035_TARGET_RAW_PROJECTION_NAMESPACE=task035.raw-projection.v2
TASK035_TARGET_RESULT_ID_PREFIX=task035-shell-side-thermal-hydraulic-composition-id.v2:

TASK035_V1_RESULT_ID_NAMESPACE=f4a7c7b3-100e-5f54-97e4-678c14fa4044
TASK035_V2_RESULT_ID_NAMESPACE=661c792e-9202-57f0-bee2-201575040d7f
TASK035_V2_RESULT_ID_NAMESPACE_DERIVATION=UUIDv5(uuid.NAMESPACE_URL, urn:hxforge:task035:shell-side-thermal-hydraulic-composition:v2)
TASK035_V2_RESULT_ID_NAMESPACE_IS_NOT_TASK035_V1_NAMESPACE=true

TASK035_V2_RESULT_ID_ALGORITHM=UUIDv5(TASK035_V2_RESULT_ID_NAMESPACE, TASK035_TARGET_RESULT_ID_PREFIX + result_hash)
TASK035_V2_RESULT_ID_PREIMAGE_FIELDS=(result_hash)
TASK035_V2_RESULT_ID_NAME_PREIMAGE=literal TASK035_TARGET_RESULT_ID_PREFIX followed by the lowercase hexadecimal result_hash
TASK035_V2_RESULT_ID_PREFIX_USAGE=prefix is part of the UUIDv5 name and is not hashed separately
TASK035_V2_SUCCESS_RESULT_ID_INPUT=result_hash
TASK035_V2_TYPED_BLOCKED_RESULT_ID_INPUT=blocked_result_hash
TASK035_V2_RAW_BOUNDARY_RESULT_ID=NONE; raw-boundary result has no result_id field

## 4. First-slice profile policy

The first-slice profile token identifies the composition semantic profile, not
the outer deterministic schema version. Its current semantic value remains
unchanged and is not a conditional implementation choice.

TASK035_V2_FIRST_SLICE_PROFILE_POLICY=PRESERVE_CURRENT_SEMANTIC_PROFILE_TOKEN_UNCONDITIONALLY
TASK035_V2_FIRST_SLICE_PROFILE_TOKEN=SHELL_SIDE_SINGLE_PHASE_NEWTONIAN_KERN_THERMAL_HYDRAULIC_COMPOSITION_V1
TASK035_V2_FIRST_SLICE_PROFILE_TOKEN_V1_SUFFIX_IS_NOT_TASK035_CONTRACT_VERSION=true
TASK035_V2_FIRST_SLICE_PROFILE_TOKEN_MUST_NOT_BE_RUNTIME_SELECTED=true

## 5. Outer request contract

TASK035_V2_REQUEST_FIELD_COUNT=7
TASK035_V2_REQUEST_FIELDS=(
  schema_version,
  profile_id,
  task031_result,
  task032_result,
  task033_result,
  task034_result,
  evidence_refs
)

TASK035_V2_REQUEST_FIELDS_V1_SEMANTIC_MEMBERSHIP=BYTE_FOR_BYTE_EQUIVALENT
TASK035_V2_REQUEST_VERSION_VALUE_CHANGED=true
TASK035_V2_REQUEST_HASH_NESTED_TASK034_PROJECTION_CHANGED=true
TASK035_V2_REQUEST_EXACT_FIELD_SET_REQUIRED=true
TASK035_V2_REQUEST_UNKNOWN_FIELDS_REJECTED=true
TASK035_V2_REQUEST_MISSING_FIELDS_REJECTED=true

## 6. Outer success contract

TASK035_V2_SUCCESS_FIELD_COUNT=41
TASK035_V2_SUCCESS_FIELDS=(
  schema_version,
  profile_id,
  first_slice_profile_id,
  implementation_software_version,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  task021_layout_id,
  task021_layout_hash,
  task024_geometry_id,
  task024_geometry_hash,
  task031_request_hash,
  task031_geometry_id,
  task031_geometry_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  task034_request_hash,
  task034_result_hash,
  task034_result_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task033_correlation_id,
  task034_correlation_id,
  heat_transfer_surface,
  modeled_shell_side_heat_transfer_coefficient_w_m2_k,
  modeled_shell_side_pressure_drop_pa,
  applicability_ledger,
  completeness_ledger,
  request_hash,
  result_hash,
  result_id,
  warnings,
  blockers,
  deferred_capabilities,
  provenance
)

TASK035_V2_SUCCESS_PREHASH_FIELD_COUNT=39
TASK035_V2_SUCCESS_PREHASH_FIELDS=(
  schema_version,
  profile_id,
  first_slice_profile_id,
  implementation_software_version,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  task021_layout_id,
  task021_layout_hash,
  task024_geometry_id,
  task024_geometry_hash,
  task031_request_hash,
  task031_geometry_id,
  task031_geometry_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  task034_request_hash,
  task034_result_hash,
  task034_result_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task033_correlation_id,
  task034_correlation_id,
  heat_transfer_surface,
  modeled_shell_side_heat_transfer_coefficient_w_m2_k,
  modeled_shell_side_pressure_drop_pa,
  applicability_ledger,
  completeness_ledger,
  request_hash,
  warnings,
  blockers,
  deferred_capabilities,
  provenance
)

TASK035_V2_SUCCESS_PREHASH_SELF_EXCLUDED_FIELDS=(result_hash,result_id)
TASK035_V2_SUCCESS_MEMBERSHIP_V1_SEMANTIC_RELATION=field names and order unchanged
TASK035_V2_SUCCESS_VERSION_IDENTITY_CHANGES=(schema_version,profile_id,implementation_software_version,result_hash,result_id,provenance)
TASK035_V2_SUCCESS_TASK034_EDGE_VALUE_CHANGES=(task034_request_hash,task034_result_hash,task034_result_id)
TASK035_V2_SUCCESS_PRESSURE_DROP_VALUE_POLICY=forward accepted TASK034 v2 modeled_shell_side_pressure_drop_pa unchanged

## 7. Outer typed-blocked contract

TASK035_V2_TYPED_BLOCKED_FIELD_COUNT=25
TASK035_V2_TYPED_BLOCKED_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  failure_stage,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task031_geometry_id,
  task031_geometry_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_result_hash,
  task033_result_id,
  task034_result_hash,
  task034_result_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  request_hash,
  blocked_result_hash,
  result_id,
  blockers,
  warnings,
  deferred_capabilities,
  provenance
)

TASK035_V2_TYPED_BLOCKED_PREHASH_FIELD_COUNT=23
TASK035_V2_TYPED_BLOCKED_PREHASH_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  failure_stage,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task031_geometry_id,
  task031_geometry_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_result_hash,
  task033_result_id,
  task034_result_hash,
  task034_result_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  request_hash,
  blockers,
  warnings,
  deferred_capabilities,
  provenance
)

TASK035_V2_TYPED_BLOCKED_PREHASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash,result_id)
TASK035_V2_TYPED_BLOCKED_MEMBERSHIP_V1_SEMANTIC_RELATION=field names and order unchanged
TASK035_V2_TYPED_BLOCKED_TASK034_EDGE_VALUE_CHANGES=(task034_result_hash,task034_result_id)

## 8. Outer raw-boundary and raw-projection contracts

TASK035_V2_RAW_BOUNDARY_FIELD_COUNT=8
TASK035_V2_RAW_BOUNDARY_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  raw_request_projection,
  blocked_result_hash,
  blockers,
  warnings,
  deferred_capabilities
)

TASK035_V2_RAW_BOUNDARY_PREHASH_FIELD_COUNT=7
TASK035_V2_RAW_BOUNDARY_PREHASH_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  raw_request_projection,
  blockers,
  warnings,
  deferred_capabilities
)

TASK035_V2_RAW_BOUNDARY_PREHASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash)
TASK035_V2_RAW_BOUNDARY_MEMBERSHIP_V1_SEMANTIC_RELATION=field names and order unchanged
TASK035_V2_RAW_BOUNDARY_VERSION_IDENTITY_CHANGES=(schema_version,profile_id,implementation_software_version,blocked_result_hash)

TASK035_V2_RAW_PROJECTION_FIELD_COUNT=2
TASK035_V2_RAW_PROJECTION_FIELDS=(
  projection_kind,
  projection
)
TASK035_V2_RAW_PROJECTION_MEMBERSHIP_V1_SEMANTIC_RELATION=byte-for-byte field membership and order unchanged
TASK035_V2_RAW_PROJECTION_NAMESPACE_CHANGE_ONLY=true

TASK035_RAW_PROJECTION_CANONICAL_ENCODING=bounded deterministic structural projection; no repr; no object addresses; no insertion-order-selected truncation
TASK035_RAW_PROJECTION_ABSENT_TASK034_RESULT_BEHAVIOR=raw boundary blocker path; no typed producer backfill

## 9. Outer provenance contract

TASK035_V2_PROVENANCE_FIELD_COUNT=36
TASK035_V2_PROVENANCE_FIELDS=(
  task_id,
  profile_id,
  first_slice_profile_id,
  implementation_software_version,
  request_hash,
  task031_request_hash,
  task031_geometry_hash,
  task031_geometry_id,
  task021_layout_hash,
  task021_layout_id,
  task024_geometry_hash,
  task024_geometry_id,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  task033_correlation_id,
  task034_request_hash,
  task034_result_hash,
  task034_result_id,
  task034_correlation_id,
  task020_configuration_hash,
  task020_configuration_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  applicability_profile_id,
  completeness_profile_id,
  producer_edges,
  warnings,
  deferred_capabilities,
  evidence_refs,
  source_definition_issue,
  source_definition_correction_chain,
  provenance_hash
)

TASK035_V2_PROVENANCE_PREHASH_FIELD_COUNT=35
TASK035_V2_PROVENANCE_PREHASH_FIELDS=(
  task_id,
  profile_id,
  first_slice_profile_id,
  implementation_software_version,
  request_hash,
  task031_request_hash,
  task031_geometry_hash,
  task031_geometry_id,
  task021_layout_hash,
  task021_layout_id,
  task024_geometry_hash,
  task024_geometry_id,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  task033_correlation_id,
  task034_request_hash,
  task034_result_hash,
  task034_result_id,
  task034_correlation_id,
  task020_configuration_hash,
  task020_configuration_id,
  property_snapshot_hash,
  mass_flow_authority_hash,
  applicability_profile_id,
  completeness_profile_id,
  producer_edges,
  warnings,
  deferred_capabilities,
  evidence_refs,
  source_definition_issue,
  source_definition_correction_chain
)

TASK035_V2_PROVENANCE_PREHASH_SELF_EXCLUDED_FIELDS=(provenance_hash)
TASK035_V2_PROVENANCE_MEMBERSHIP_V1_SEMANTIC_RELATION=field names and order unchanged
TASK035_V2_PROVENANCE_TASK034_EDGE_VALUE_CHANGES=(task034_request_hash,task034_result_hash,task034_result_id,producer_edges)
TASK035_V2_PROVENANCE_PROFILE_VALUE_CHANGES=(profile_id,applicability_profile_id,completeness_profile_id,implementation_software_version)

## 10. Exact nested TASK034 v2 success projection

TASK034_V2_SUCCESS_PROJECTION_FIELD_COUNT=45
TASK034_V2_SUCCESS_PROJECTION_PREHASH_FIELD_COUNT=43
TASK034_V2_SUCCESS_PROJECTION_EXACT=true
TASK035_CONSUMED_TASK034_V2_SUCCESS_FIELDS=(
  schema_version,
  profile_id,
  first_slice_profile_id,
  implementation_software_version,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  shell_type,
  shell_type_authority_hash,
  shell_type_authority_record_id,
  shell_type_authority_source_id,
  shell_type_authority_source_version,
  task031_request_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  correlation_id,
  engineering_source_authority_record_id,
  source_id,
  source_version,
  source_location,
  wall_property_schema_version,
  wall_property_source_id,
  wall_property_source_version,
  wall_property_snapshot_hash,
  wall_property_authority_hash,
  modeled_shell_side_pressure_drop_pa,
  request_hash,
  result_hash,
  result_id,
  warnings,
  blockers,
  deferred_capabilities,
  applicability_context,
  physical_boundary_context,
  provenance
)
TASK035_CONSUMED_TASK034_V2_SUCCESS_PREHASH_FIELDS=TASK035_CONSUMED_TASK034_V2_SUCCESS_FIELDS excluding (result_hash,result_id), in the same order

TASK034_V2_SUCCESS_SCHEMA_VERSION=task034.shell-side-pressure-drop-success.v2
TASK034_V2_SUCCESS_PROFILE_ID=hxforge.shell_tube.shell_side_pressure_drop.v2
TASK034_V2_SUCCESS_HASH_NAMESPACE=task034.success-result.v2
TASK034_V2_SUCCESS_RESULT_ID_NAMESPACE=c8f1c1c4-a11b-596b-88ad-6e851a22b9fd
TASK034_V2_SUCCESS_RESULT_ID_PREFIX=task034-shell-side-pressure-drop-id.v2:

## 11. Exact nested TASK034 v2 typed-blocked projection

TASK034_V2_TYPED_BLOCKED_PROJECTION_FIELD_COUNT=36
TASK034_V2_TYPED_BLOCKED_PROJECTION_PREHASH_FIELD_COUNT=35
TASK034_V2_TYPED_BLOCKED_PROJECTION_EXACT=true
TASK035_CONSUMED_TASK034_V2_TYPED_BLOCKED_FIELDS=(
  schema_version,
  profile_id,
  implementation_software_version,
  failure_stage,
  shell_side_case_id,
  shell_side_stream_id,
  shell_side_fluid_id,
  task020_configuration_id,
  task020_configuration_hash,
  shell_type,
  shell_type_authority_hash,
  shell_type_authority_record_id,
  shell_type_authority_source_id,
  shell_type_authority_source_version,
  task031_request_hash,
  task031_geometry_id,
  task031_geometry_hash,
  property_snapshot_hash,
  mass_flow_authority_hash,
  task032_request_hash,
  task032_result_hash,
  task032_result_id,
  task033_request_hash,
  task033_result_hash,
  task033_result_id,
  wall_property_schema_version,
  wall_property_source_id,
  wall_property_source_version,
  wall_property_snapshot_hash,
  wall_property_authority_hash,
  request_hash,
  blocked_result_hash,
  warnings,
  blockers,
  deferred_capabilities,
  provenance
)
TASK035_CONSUMED_TASK034_V2_TYPED_BLOCKED_PREHASH_FIELDS=TASK035_CONSUMED_TASK034_V2_TYPED_BLOCKED_FIELDS excluding (blocked_result_hash), in the same order

TASK034_V2_TYPED_BLOCKED_SCHEMA_VERSION=task034.shell-side-pressure-drop-blocked.v2
TASK034_V2_TYPED_BLOCKED_HASH_NAMESPACE=task034.typed-blocked-result.v2
TASK034_V2_TYPED_BLOCKED_PREHASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash)

## 12. Exact nested TASK034 v2 raw-boundary projection

TASK034_V2_RAW_BOUNDARY_PROJECTION_FIELD_COUNT=8
TASK034_V2_RAW_BOUNDARY_PROJECTION_PREHASH_FIELD_COUNT=7
TASK034_V2_RAW_BOUNDARY_PROJECTION_EXACT=true
TASK035_CONSUMED_TASK034_V2_RAW_BOUNDARY_FIELDS=(
  schema_version,
  profile_id,
  request_hash,
  blocked_result_hash,
  blockers,
  warnings,
  deferred_capabilities,
  raw_projection
)
TASK035_CONSUMED_TASK034_V2_RAW_BOUNDARY_PREHASH_FIELDS=(
  schema_version,
  profile_id,
  request_hash,
  blockers,
  warnings,
  deferred_capabilities,
  raw_projection
)
TASK034_V2_RAW_BOUNDARY_SCHEMA_VERSION=task034.shell-side-pressure-drop-raw-boundary-blocked.v2
TASK034_V2_RAW_BOUNDARY_HASH_NAMESPACE=task034.raw-boundary-blocked-result.v2
TASK034_V2_RAW_BOUNDARY_PREHASH_SELF_EXCLUDED_FIELDS=(blocked_result_hash)

TASK034_V2_RAW_PROJECTION_FIELD_COUNT=9
TASK034_V2_RAW_PROJECTION_FIELDS=(
  top_level_type,
  sorted_top_level_keys,
  schema_version_projection,
  profile_id_projection,
  task033_upstream_evidence_type,
  task031_request_evidence_type,
  shell_type_authority_presence_and_value_projection,
  wall_property_fields_projection,
  evidence_refs_projection
)
TASK034_V2_RAW_PROJECTION_ABSENT_SHELL_TYPE_AUTHORITY=("MISSING",null)
TASK034_V2_RAW_PROJECTION_PRESENT_SHELL_TYPE_AUTHORITY=("PRESENT",projection_primitive(value))
TASK034_V2_RAW_PROJECTION_NO_REPR=true
TASK034_V2_RAW_PROJECTION_NO_OBJECT_ADDRESS=true

## 13. TASK034 branch admission

TASK034_V2_ENVELOPE_FIELDS=(status,pressure_drop,blocked_result,raw_boundary_blocked_result)
TASK034_V2_ENVELOPE_FIELD_COUNT=4

TASK034_V2_SUCCESS_BRANCH_ACCEPTED=true
TASK034_V2_SUCCESS_BRANCH_PREDICATE=status == VALID AND pressure_drop is non-null AND blocked_result is null AND raw_boundary_blocked_result is null AND pressure_drop has exactly TASK035_CONSUMED_TASK034_V2_SUCCESS_FIELDS

TASK034_V2_TYPED_BLOCKED_BRANCH_ACCEPTED=true
TASK034_V2_TYPED_BLOCKED_BRANCH_PREDICATE=status == BLOCKED AND pressure_drop is null AND blocked_result is non-null AND raw_boundary_blocked_result is null AND blocked_result has exactly TASK035_CONSUMED_TASK034_V2_TYPED_BLOCKED_FIELDS

TASK034_V2_RAW_BOUNDARY_BLOCKED_BRANCH_ACCEPTED=true
TASK034_V2_RAW_BOUNDARY_BLOCKED_BRANCH_PREDICATE=status == BLOCKED AND pressure_drop is null AND blocked_result is null AND raw_boundary_blocked_result is non-null AND raw_boundary_blocked_result has exactly TASK035_CONSUMED_TASK034_V2_RAW_BOUNDARY_FIELDS

TASK034_V2_BLOCKED_BRANCH_EXACTLY_ONE_PAYLOAD=true
TASK034_V1_BRANCH_ACCEPTED=false
TASK034_MIXED_BRANCH_ACCEPTED=false
TASK034_SUBSET_BRANCH_ACCEPTED=false
TASK034_UNKNOWN_NESTED_FIELDS_ACCEPTED=false
TASK034_MISSING_NESTED_FIELDS_ACCEPTED=false
TASK034_V2_BRANCH_DISCRIMINATION_FAILS_CLOSED=true

## 14. TASK034 v2 canonical replay

TASK034_V2_REQUEST_HASH_NAMESPACE=task034.request.v2
TASK034_V2_SUCCESS_RESULT_HASH_NAMESPACE=task034.success-result.v2
TASK034_V2_TYPED_BLOCKED_RESULT_HASH_NAMESPACE=task034.typed-blocked-result.v2
TASK034_V2_RAW_BOUNDARY_BLOCKED_RESULT_HASH_NAMESPACE=task034.raw-boundary-blocked-result.v2
TASK034_V2_PROVENANCE_NAMESPACE=task034.provenance.v2
TASK034_V2_RESULT_ID_NAMESPACE=c8f1c1c4-a11b-596b-88ad-6e851a22b9fd
TASK034_V2_RESULT_ID_PREFIX=task034-shell-side-pressure-drop-id.v2:

TASK035_TASK034_REQUEST_HASH_REPLAY_REQUIRED=true
TASK035_TASK034_RESULT_HASH_REPLAY_REQUIRED=true
TASK035_TASK034_RESULT_ID_REPLAY_REQUIRED=true
TASK035_TASK034_REQUEST_HASH_SOURCE=accepted public TASK034 v2 request identity carried by the producer result/evidence contract
TASK035_TASK034_RESULT_HASH_SOURCE=exact ordered TASK034 v2 success or typed-blocked/raw-boundary prehash projection
TASK035_TASK034_RESULT_ID_SOURCE=exact TASK034 v2 result-ID namespace/prefix algorithm
TASK035_TASK034_IDENTITY_REWRITE_ALLOWED=false
TASK035_TASK034_HASH_REPAIR_ALLOWED=false
TASK035_TASK034_RESULT_ID_REPAIR_ALLOWED=false
TASK035_TASK034_PRIVATE_CANONICAL_HELPER_IMPORT_REQUIRED=false
TASK035_TASK034_ENGINEERING_RECOMPUTATION_ALLOWED=false

## 15. Canonical encoding and TASK035-own hash contracts

TASK035_V2_CANONICAL_ENCODING=SHA-256 over UTF-8 JSON bytes of [namespace,projection]
TASK035_V2_CANONICAL_JSON_OPTIONS=ensure_ascii=false;separators=(",",":");sort_keys=true;allow_nan=false
TASK035_V2_CANONICAL_DECIMAL_RULE=finite Decimal values become decimal strings
TASK035_V2_CANONICAL_FLOAT_RULE=binary floating-point values are rejected
TASK035_V2_CANONICAL_SEQUENCE_RULE=ordered sequence position is significant
TASK035_V2_CANONICAL_MAPPING_RULE=string-key mappings are canonicalized with sorted JSON keys
TASK035_V2_CANONICAL_UNORDERED_COLLECTION_RULE=sets and frozensets are rejected

TASK035_V2_REQUEST_HASH_PREIMAGE_MEMBERSHIP=(
  request.schema_version,
  request.profile_id,
  task031_envelope_projection(request.task031_result),
  task032_envelope_projection(request.task032_result),
  task033_envelope_projection(request.task033_result),
  task034_v2_envelope_projection(request.task034_result),
  request.evidence_refs
)
TASK035_V2_REQUEST_HASH_SELF_EXCLUDED_FIELDS=NONE

TASK035_V2_HASH_CONTRACT_COUNT=6
TASK035_V2_HASH_CONTRACTS=(
  REQUEST_HASH|SCHEMA_TOKEN=TASK035_TARGET_REQUEST_SCHEMA_VERSION|NAMESPACE=TASK035_TARGET_REQUEST_HASH_NAMESPACE|PREIMAGE=TASK035_V2_REQUEST_HASH_PREIMAGE_MEMBERSHIP|SELF_EXCLUDED=NONE|ENCODING=TASK035_V2_CANONICAL_ENCODING,
  SUCCESS_RESULT_HASH|SCHEMA_TOKEN=TASK035_TARGET_SUCCESS_SCHEMA_VERSION|NAMESPACE=TASK035_TARGET_SUCCESS_HASH_NAMESPACE|PREIMAGE=TASK035_V2_SUCCESS_PREHASH_FIELDS in exact order|SELF_EXCLUDED=(result_hash,result_id)|ENCODING=TASK035_V2_CANONICAL_ENCODING,
  TYPED_BLOCKED_RESULT_HASH|SCHEMA_TOKEN=TASK035_TARGET_TYPED_BLOCKED_SCHEMA_VERSION|NAMESPACE=TASK035_TARGET_TYPED_BLOCKED_HASH_NAMESPACE|PREIMAGE=TASK035_V2_TYPED_BLOCKED_PREHASH_FIELDS in exact order|SELF_EXCLUDED=(blocked_result_hash,result_id)|ENCODING=TASK035_V2_CANONICAL_ENCODING,
  RAW_BOUNDARY_BLOCKED_RESULT_HASH|SCHEMA_TOKEN=TASK035_TARGET_RAW_BOUNDARY_SCHEMA_VERSION|NAMESPACE=TASK035_TARGET_RAW_BOUNDARY_HASH_NAMESPACE|PREIMAGE=TASK035_V2_RAW_BOUNDARY_PREHASH_FIELDS in exact order|SELF_EXCLUDED=(blocked_result_hash)|ENCODING=TASK035_V2_CANONICAL_ENCODING,
  PROVENANCE_HASH|SCHEMA_TOKEN=TASK035_TARGET_PROVENANCE_NAMESPACE|NAMESPACE=TASK035_TARGET_PROVENANCE_NAMESPACE|PREIMAGE=TASK035_V2_PROVENANCE_PREHASH_FIELDS in exact order|SELF_EXCLUDED=(provenance_hash)|ENCODING=TASK035_V2_CANONICAL_ENCODING,
  RESULT_ID|SCHEMA_TOKEN=TASK035_TARGET_SUCCESS_SCHEMA_VERSION or TASK035_TARGET_TYPED_BLOCKED_SCHEMA_VERSION|NAMESPACE=TASK035_V2_RESULT_ID_NAMESPACE|PREIMAGE=TASK035_V2_RESULT_ID_PREIMAGE_FIELDS|SELF_EXCLUDED=hash field is not an input field; digest is the input|ENCODING=UUIDv5
)

TASK035_V2_SUCCESS_RESULT_HASH_ALGORITHM=hash_projection(TASK035_TARGET_SUCCESS_HASH_NAMESPACE, values in TASK035_V2_SUCCESS_PREHASH_FIELDS)
TASK035_V2_TYPED_BLOCKED_RESULT_HASH_ALGORITHM=hash_projection(TASK035_TARGET_TYPED_BLOCKED_HASH_NAMESPACE, values in TASK035_V2_TYPED_BLOCKED_PREHASH_FIELDS)
TASK035_V2_RAW_BOUNDARY_BLOCKED_RESULT_HASH_ALGORITHM=hash_projection(TASK035_TARGET_RAW_BOUNDARY_HASH_NAMESPACE, values in TASK035_V2_RAW_BOUNDARY_PREHASH_FIELDS)
TASK035_V2_PROVENANCE_HASH_ALGORITHM=hash_projection(TASK035_TARGET_PROVENANCE_NAMESPACE, values in TASK035_V2_PROVENANCE_PREHASH_FIELDS)

TASK035_V2_SUCCESS_RESULT_ID_ALGORITHM=UUIDv5(TASK035_V2_RESULT_ID_NAMESPACE,TASK035_TARGET_RESULT_ID_PREFIX + result_hash)
TASK035_V2_TYPED_BLOCKED_RESULT_ID_ALGORITHM=UUIDv5(TASK035_V2_RESULT_ID_NAMESPACE,TASK035_TARGET_RESULT_ID_PREFIX + blocked_result_hash)
TASK035_V2_RAW_BOUNDARY_BLOCKED_RESULT_ID_ALGORITHM=NONE

## 16. Authority consumption and propagation

TASK035_SHELL_TYPE_AUTHORITY_CONSUMED_FOR_EXACT_TASK034_REPLAY=true
TASK035_SHELL_TYPE_AUTHORITY_DIRECT_PROPAGATION_TO_TASK035_RESULT=false
TASK035_SHELL_TYPE_AUTHORITY_TRANSITIVE_IDENTITY_PATH=TASK034 shell_type and shell-type authority identity participate in exact TASK034 v2 result_hash/result_id; TASK035 provenance retains task034_result_hash/task034_result_id and the TASK034 producer edge

TASK035_WALL_PROPERTY_AUTHORITY_CONSUMED_FOR_EXACT_TASK034_REPLAY=true
TASK035_WALL_PROPERTY_AUTHORITY_DIRECT_PROPAGATION_TO_TASK035_RESULT=false
TASK035_WALL_PROPERTY_AUTHORITY_TRANSITIVE_IDENTITY_PATH=TASK034 wall-property authority fields participate in exact TASK034 v2 result_hash/result_id; TASK035 directly preserves property_snapshot_hash and retains task034_result_hash/task034_result_id and the TASK034 producer edge

TASK035_TASK034_AUTHORITY_FIELDS_CONSUMED_EXACTLY=(
  shell_type,
  shell_type_authority_hash,
  shell_type_authority_record_id,
  shell_type_authority_source_id,
  shell_type_authority_source_version,
  wall_property_schema_version,
  wall_property_source_id,
  wall_property_source_version,
  wall_property_snapshot_hash,
  wall_property_authority_hash
)
TASK035_TASK034_AUTHORITY_FIELD_SUBSTITUTION=false
TASK035_TASK034_AUTHORITY_FIELD_RECOMPUTATION=false
TASK035_TASK034_AUTHORITY_FIELD_BACKFILL=false

TASK035_PRESSURE_DROP_FORWARDING_ONLY=true
TASK035_PRESSURE_DROP_SOURCE=accepted TASK034 v2 modeled_shell_side_pressure_drop_pa
TASK035_PRESSURE_DROP_DIRECT_PROPAGATION=true
TASK035_PRESSURE_DROP_RECOMPUTATION_ALLOWED=false
TASK035_PRESSURE_DROP_NORMALIZATION_ALLOWED=false
TASK035_PRESSURE_DROP_SUBSTITUTION_ALLOWED=false
TASK035_TAMPERED_PRESSURE_DROP_WITH_STALE_IDENTITY=FAIL_CLOSED

## 17. Blocker routing

TASK035_BLOCKER_COUNT=42
TASK035_NEW_BLOCKER_REQUIRED=false
TASK035_BLOCKER_REGISTRY_MUTATION_REQUIRED=false

TASK035_S02_OUTER_SCHEMA_MISMATCH=existing SSTHC_SCHEMA_VERSION_UNSUPPORTED
TASK035_S02_OUTER_PROFILE_MISMATCH=existing SSTHC_PROFILE_ID_UNSUPPORTED
TASK035_S09_TASK034_MISSING=existing SSTHC_TASK034_RESULT_MISSING
TASK035_S09_TASK034_V1_WRONG_OR_MIXED=existing SSTHC_TASK034_RESULT_INVALID
TASK035_S09_TASK034_V2_SCHEMA_OR_BRANCH_INVALID=existing SSTHC_TASK034_RESULT_INVALID
TASK035_S09_TASK034_V2_TYPED_OR_RAW_BLOCKED=existing SSTHC_TASK034_RESULT_BLOCKED
TASK035_S10_TASK034_REQUEST_HASH_MISMATCH=existing SSTHC_TASK034_IDENTITY_MISMATCH
TASK035_S10_TASK034_RESULT_HASH_MISMATCH=existing SSTHC_TASK034_IDENTITY_MISMATCH
TASK035_S10_TASK034_RESULT_ID_MISMATCH=existing SSTHC_TASK034_IDENTITY_MISMATCH
TASK035_S11_CONFIGURATION_MISMATCH=existing SSTHC_CONFIGURATION_MISMATCH
TASK035_S11_LAYOUT_MISMATCH=existing SSTHC_TASK021_LAYOUT_MISMATCH
TASK035_S11_BAFFLE_GEOMETRY_MISMATCH=existing SSTHC_TASK024_GEOMETRY_MISMATCH
TASK035_S11_TASK031_GEOMETRY_MISMATCH=existing SSTHC_TASK031_GEOMETRY_MISMATCH
TASK035_S14_PROFILE_MISMATCH=existing SSTHC_PROFILE_COMPATIBILITY_MISMATCH
TASK035_S15_APPLICABILITY_MISMATCH=existing SSTHC_APPLICABILITY_INCOMPATIBLE

TASK035_NEW_TASK034_V2_BLOCKER_IDS=NONE
TASK035_BLOCKER_ROUTING_FAILS_CLOSED=true
TASK035_BLOCKER_ROUTING_DOES_NOT_RECOMPUTE_ENGINEERING=true
TASK035_BLOCKER_ROUTING_DOES_NOT_REWRITE_IDENTITY=true

## 18. Validation stage order

TASK035_VALIDATION_STAGE_COUNT=19
TASK035_VALIDATION_STAGES=(
  S01 RAW_BOUNDARY,
  S02 REQUEST_SCHEMA,
  S03 TASK031_PRODUCER_BOUNDARY,
  S04 TASK031_IDENTITY_REPLAY,
  S05 TASK032_PRODUCER_BOUNDARY,
  S06 TASK032_IDENTITY_REPLAY,
  S07 TASK033_PRODUCER_BOUNDARY,
  S08 TASK033_IDENTITY_REPLAY,
  S09 TASK034_PRODUCER_BOUNDARY,
  S10 TASK034_IDENTITY_REPLAY,
  S11 CROSS_PRODUCER_CONFIGURATION_AND_GEOMETRY_JOIN,
  S12 PROPERTY_AND_MASS_FLOW_IDENTITY_JOIN,
  S13 CASE_STREAM_FLUID_JOIN,
  S14 PROFILE_COMPATIBILITY,
  S15 APPLICABILITY_INTERSECTION,
  S16 COMPLETENESS_LEDGER,
  S17 SUCCESS_PAYLOAD_COMPOSITION,
  S18 PROVENANCE_CANONICALIZATION,
  S19 RESULT_IDENTITY_FINALIZATION
)

TASK035_S09_SEMANTICS=exact TASK034 v2 producer boundary
TASK035_S10_SEMANTICS=exact TASK034 v2 request/result/result-ID replay
TASK035_STAGE_REORDER_ALLOWED=false
TASK035_STAGE_COUNT_CHANGE_ALLOWED=false

## 19. Real public production-chain acceptance

ACTUAL_PUBLIC_PRODUCTION_CHAIN_REQUIRED=true
TASK035_REAL_PUBLIC_CHAIN=TASK031.validate_request -> TASK032.validate_request -> TASK033.validate_request -> TASK034.validate_request -> TASK035.validate_request
REAL_TASK034_V2_TO_TASK035_PUBLIC_CHAIN_REQUIRED=true
ACTUAL_PRODUCTION_BINDINGS_ONLY=true
HAND_BUILT_UPSTREAM_SUCCESS_FOR_ACCEPTANCE=false
FIXTURE_ONLY_RESULT_SUBSTITUTION=false
SYNTHETIC_ORACLE_SUBSTITUTION=false
EXPECTED_OUTPUT_USED_AS_INPUT=false
PRIVATE_HELPER_BYPASS=false
IDENTITY_ADAPTER_OR_REWRITE=false
CONSTRUCTION_FAMILY_E_SHELL_ACCEPTANCE_SUBSTITUTION_ALLOWED=false

The real-chain acceptance must obtain all TASK031, TASK032, TASK033, and
TASK034 producer evidence and identities from their public operations. The
TASK035 request must pass the actual TASK034 v2 public envelope unchanged.
The acceptance must reach TASK035 SUCCESS and assert the public
modeled_shell_side_pressure_drop_pa value is forwarded from TASK034 without
recomputation.

## 20. Adversarial and migration test matrix

MIGRATION_TEST_PLAN_COUNT=8
TASK035_V2_MIGRATION_TEST_IDS=(
  T035-V2-001,
  T035-V2-002,
  T035-V2-003,
  T035-V2-004,
  T035-V2-005,
  T035-V2-006,
  T035-V2-007,
  T035-V2-008
)

T035-V2-001=valid exact TASK034 v2 success branch reaches TASK035 VALID
T035-V2-002=historical TASK034 v1 branch is rejected at S09 with SSTHC_TASK034_RESULT_INVALID
T035-V2-003=wrong TASK034 schema/profile/version is rejected fail-closed
T035-V2-004=mixed v1/v2 or field-subset TASK034 branch is rejected
T035-V2-005=TASK034 result_hash tampering is rejected at S10 with SSTHC_TASK034_IDENTITY_MISMATCH
T035-V2-006=TASK034 result_id tampering is rejected at S10 with SSTHC_TASK034_IDENTITY_MISMATCH
T035-V2-007=modeled pressure-drop tampering with stale TASK034 identity is rejected at S10 without rebuilding identity
T035-V2-008=real public TASK031 -> TASK032 -> TASK033 -> TASK034 v2 -> TASK035 chain reaches TASK035 VALID

TASK035_EXISTING_TEST_ID_MAPPING=preserve existing T035-001 through T035-022 authorities; update only their v2 expectations where nested TASK034 is exercised
TASK035_V2_TEST_ID_UNIQUENESS_REQUIRED=true
TASK035_V2_TESTS_MUST_NOT_USE_HAND_BUILT_TASK034_SUCCESS_FOR_REAL_CHAIN=true
TASK035_V2_TESTS_MUST_NOT_REBUILD_TAMPERED_TASK034_IDENTITY=true
TASK035_V2_TESTS_MUST_NOT_USE_EXPECTED_HASH_OR_ID_AS_RUNTIME_INPUT=true

## 21. Cross-Python artifact contract

TASK035_V1_GOLDENS_HISTORICAL_ONLY=true
TASK035_V1_GOLDEN_REQUEST_CANONICAL_SHA256=9fc67fd05d26be188f1bb2d62d9067bbf14b3efc2b783bf7c3665aebaa37992c
TASK035_V1_GOLDEN_SUCCESS_CANONICAL_SHA256=c8ad2e7a4e452d1a10906620e39ecfa0003ab7c01629d3796407e9cd111499be
TASK035_V1_GOLDEN_PROVENANCE_CANONICAL_SHA256=8459541e706b1ad2825bb2a0d8be9774d8aa0fb4f792d8313c410c09feb9a191
TASK035_V1_GOLDENS_MUST_NOT_BE_REUSED_FOR_V2=true

TASK035_V2_GOLDENS_REGENERATE_REQUIRED=true
TASK035_V2_GOLDENS_SHA256=NOT_YET_GENERATED
TASK035_V2_GOLDENS_ACCEPTANCE_PENDING=true
TASK035_V2_GOLDENS_ACCEPTANCE=false
TASK035_V2_GOLDEN_GENERATION_METHOD=run identical ordered request;success;typed-blocked/raw-boundary;and provenance canonical projections under Python 3.11 and Python 3.12; hash exact UTF-8 canonical bytes; require byte identity before recording values
TASK035_V2_ARTIFACT_GENERATION_IN_THIS_GATE=false

## 22. Future implementation mutation boundary

TASK035_FUTURE_PRODUCTION_MUTATION_ALLOWLIST=(
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/schema.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/canonical.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/validation.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/models.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/provenance.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/raw_projection.py
)
TASK035_FUTURE_PRODUCTION_NO_CHANGE_EXPECTED=(
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/__init__.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/blocker_registry.py,
  src/hexagent/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/warning_registry.py,
  ci-shard-manifest.yml
)
TASK035_FUTURE_TEST_MUTATION_ALLOWLIST=(
  tests/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/test_task035_contract.py
)
TASK035_V2_ARTIFACT_LOCATION_POLICY=INLINE_ONLY
TASK035_V2_ARTIFACT_LOCATION=tests/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/test_task035_contract.py
TASK035_V2_EXTERNAL_ARTIFACT_FILE_ALLOWED=false
TASK035_V2_ALTERNATIVE_ARTIFACT_LOCATION_ALLOWED=false
TASK035_V2_ARTIFACT_MUTATION_ALLOWLIST=(
  tests/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/test_task035_contract.py
)
Corrected TASK035 v2 canonical/cross-Python goldens MUST be stored inline only in:
tests/exchangers/shell_tube/shell_side_thermal_hydraulic_composition/test_task035_contract.py
No external artifact location is permitted under this migration contract.
No standalone artifact file is permitted under this migration contract.
No repository-standard artifact location is permitted under this migration contract.
No alternate artifact location is permitted under this migration contract.
No separately selected artifact location is permitted under this migration contract.
TASK035_FUTURE_CI_MUTATION_ALLOWLIST=NONE_EXPECTED; existing ci-shard-manifest.yml entry already registers test_task035_contract.py

TASK035_FORBIDDEN_FUTURE_MUTATION=TASK034;TASK031;TASK032;TASK033;TASK036;other production packages;blocker_registry.py;warning_registry.py;CI manifest;workflow;dependency files
TASK035_FUTURE_ALLOWLIST_EXPANSION_REQUIRES_SEPARATE_AUTHORIZATION=true
TASK035_FUTURE_IMPLEMENTATION_MUST_BLOCK_ON_ALLOWLIST_EXPANSION=true

## 23. One-shot implementation strategy

IMPLEMENTATION_STRATEGY=ONE_SHOT
IMPLEMENTATION_SLICE_COUNT=5
IMPLEMENTATION_SLICES=(
  S1 freeze Task035 v2 identifiers, profile values, and exact nested TASK034 v2 projections,
  S2 update canonical/hash/result-ID replay and S09/S10 validation routing,
  S3 preserve configuration/applicability/composition/provenance semantics and forward pressure drop,
  S4 update unit tests and add the actual public TASK031 -> TASK032 -> TASK033 -> TASK034 -> TASK035 regression,
  S5 regenerate v2 cross-Python artifacts and execute all required verification
)

ONE_SHOT_RATIONALE=outer Task035 canonical identities depend on nested TASK034 v2 projection and must not pass through an intermediate mixed v1/v2 state
ONE_IMPLEMENTATION_AUTHORIZATION_FOR_ALL_SLICES=true
SLICE_BY_SLICE_GOVERNANCE_LOOP_ALLOWED=false

## 24. Engineering and ownership invariants

TASK035_COMPOSITION_ENGINEERING_SEMANTICS_CHANGED=false
TASK035_PRESSURE_DROP_RECOMPUTATION_ALLOWED=false
TASK035_TASK034_PRESSURE_DROP_FORWARDING_ONLY=true
TASK035_UPSTREAM_ENGINEERING_RECOMPUTATION_OR_MUTATION_ALLOWED=false
TASK035_APPLICABILITY_BROADENING_ALLOWED=false
TASK035_CORRELATION_REDEFINITION_ALLOWED=false
TASK035_RESULT_QUANTITY_REDEFINITION_ALLOWED=false
TASK035_IDENTITY_REWRITE_ALLOWED=false
TASK035_HASH_REPAIR_ALLOWED=false
TASK035_IDENTITY_BACKFILL_ALLOWED=false
TASK035_FIXTURE_SUBSTITUTION_ALLOWED=false

TASK031_MUTATED=false
TASK032_MUTATED=false
TASK033_MUTATED=false
TASK034_MUTATED=false
TASK035_CODE_MUTATED=false
TASK035_TESTS_MUTATED=false
TASK035_ARTIFACTS_MUTATED=false
TASK036_MUTATED=false

## 25. Deterministic author self-check

TASK035_V2_DESIGN_AUTHOR_SELF_CHECK_REQUIREMENTS=(
  exact outer field counts and ordered membership,
  exact prehash self-exclusions,
  exact v2 namespaces and schema identifiers,
  exact UUIDv5 namespace and result-ID preimages,
  exact nested TASK034 v2 success/typed-blocked/raw-boundary projections,
  exact branch predicates and fail-closed routing,
  blocker count 42,
  validation stage count 19,
  migration test plan count 8,
  no dual-version acceptance,
  no subset acceptance,
  no pressure-drop recomputation,
  no identity rewrite,
  mutation allowlist enforcement
)
TASK035_V2_DESIGN_AUTHOR_SELF_CHECK=PASS
TASK035_V2_DESIGN_AUTHOR_SELF_CHECK_IS_INDEPENDENT_REVIEW=false
TASK035_V2_DESIGN_REVIEW_REQUIRED=true
TASK035_V2_DESIGN_ACCEPTANCE_REQUIRED=true
AMBIGUOUS_AUTHORITY_TOKEN_COUNT=0
UNRESOLVED_TASK035_V2_DESIGN_AUTHORITY_COUNT=0
UNRESOLVED_TASK035_V2_DESIGN_AUTHORITY_ITEMS=NONE_FOR_VERSIONING_RESULT_ID_PROFILE_FIELD_MEMBERSHIP_HASH_BRANCH_BLOCKER_STAGE_TEST_OR_MUTATION_POLICY

## 26. Lifecycle and next gate

TASK035_V2_DESIGN_AUTHORED=true
TASK035_V2_DESIGN_REVIEWED=false
TASK035_V2_DESIGN_ACCEPTED=false
TASK035_V2_MIGRATION_EXECUTION_AUTHORIZED=false
TASK035_MUTATION_AUTHORIZED=false
TASK036_BLOCKED=true
TASK036_MUTATION_AUTHORIZED=false

TASK035_DESIGN_FILE_SHA256=COMPUTE_AFTER_AUTHORING
TASK035_DESIGN_DIFF_SHA256=COMPUTE_FROM_ORIGIN_MAIN_AFTER_AUTHORING

NEXT_GATE=AUTHORIZE_TASK035_CORRECTED_TASK034_V2_MIGRATION_DELTA_DESIGN_REVIEW_ONLY
NEXT_GATE_AUTHORIZED=false
NO_STEP_IMPLIES_THE_NEXT=true

This Design does not authorize implementation, artifact regeneration, CI
changes, TASK035 acceptance, TASK036, or any remote repository lifecycle
operation.
