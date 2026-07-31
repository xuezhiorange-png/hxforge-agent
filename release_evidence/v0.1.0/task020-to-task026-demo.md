# v0.1.0 TASK-020 -> TASK-026 Demo Evidence

- schema_version: `hxforge.release-evidence.v0.1.0`
- source_main_sha: `b11a7d46ac6a726c2bbdff85166c78e6753289a0`
- authority_id: `CHARLES_V0_1_TASK020_TO_TASK026_EXAMPLE_DEMO_AUTHORIZATION`

## Disclaimer

- data_class: `SYNTHETIC_DEMO_VALUE`
- engineering_recommendation: `False`
- vendor_specification: `False`
- standard_claim: `False`

## Summary

- valid_stage_count: `7`
- blocked_case_count: `7`
- all_valid_stages_passed: `True`
- all_blocked_cases_blocked: `True`
- all_blocked_cases_have_no_partial_result: `True`
- production_algorithm_modified: `False`
- public_contract_modified: `False`
- cross_version_bytes: `IDENTICAL`
- cross_version_sha256: `4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd`
- regression_record.r8_cross_version_sha256: `fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5`
- regression_record.r8_upstream_was_synthetic: `True`
- regression_record.r2_cross_version_sha256: `4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd`
- regression_record.r2_upstream_is_real_task025_valid_result: `True`
- actual_dependency_bindings_only: `True`
- t023_actual_downstream_binding: `True`
- self_edge_count: `0`

## Upstream Chain Bindings

- `TASK-020` -> `TASK-021`: binding=`645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d` (downstream_field='tube_layout.task020_configuration_hash')
- `TASK-021` -> `TASK-022`: binding=`7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6` (downstream_field='tube_layout.layout_hash')
- `TASK-023` -> `TASK-022`: binding=`7b956986b61c7fff1041f692f6ea5653c11865cf1bbd277257b93aa94c64b2e0` (downstream_field='shell_bundle_geometry_request.approved_shell_geometry.record_hash')
- `TASK-022` -> `TASK-024`: binding=`c308d5d62d21c3fcf44f4485ad5266e4951dc47f4560bdd3f85ad3ecb7bd95c0` (downstream_field='shell_bundle_geometry.geometry_hash')
- `TASK-024` -> `TASK-025`: binding=`0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8` (downstream_field='task024_foundation_hash')
- `TASK-025` -> `TASK-026`: binding=`9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca` (downstream_field='upstream_task025_valid_result.result_hash')

## Valid Stages

### TASK-020

- public_entry_point: `hexagent.exchangers.shell_tube.validate_request`
- schema_version: `task020.configuration.v1`
- input_identity: `dab6e6220281a04971228ee7a79bb676b20cb79896fe8115b41b5be3fd8bf519`
- output_identity: `645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d`
- result_hash: `645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d`
- result_id: `5d5ecd95-deef-5196-a1b4-e44258e2d751`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{}`
- deferred_capabilities: `TUBE_LAYOUT_NOT_COMPUTABLE,SHELL_DIAMETER_NOT_COMPUTABLE,THERMAL_RATING_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,THERMAL_EXPANSION_NOT_COMPUTABLE,MECHANICAL_BOUNDARY_NOT_COMPUTABLE,MATERIAL_SELECTION_NOT_COMPUTABLE,COST_NOT_COMPUTABLE,OPTIMIZATION_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE`

### TASK-021

- public_entry_point: `hexagent.exchangers.shell_tube.tube_layout.validate_request`
- schema_version: `task021.tube-layout.v1`
- input_identity: `3625859a6068bd7cc8aedc9cc27ecc097b97815a91ba83bb7e64582259558bba`
- output_identity: `7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6`
- result_hash: `7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6`
- result_id: `0f8dacdc-343c-5c55-9863-8c2a6012866f`
- blockers_count: `0`
- warnings_count: `3`
- upstream_identity_bindings: `{"task020_configuration_hash":"645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d"}`
- deferred_capabilities: `SHELL_DIAMETER_NOT_COMPUTABLE,BAFFLE_DESIGN_NOT_COMPUTABLE,PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE,THERMAL_RATING_NOT_COMPUTABLE,KERN_SCREENING_NOT_COMPUTABLE,BELL_DELAWARE_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,THERMAL_EXPANSION_NOT_COMPUTABLE,MECHANICAL_BOUNDARY_NOT_COMPUTABLE,MATERIAL_SELECTION_NOT_COMPUTABLE,MASS_NOT_COMPUTABLE,COST_NOT_COMPUTABLE,OPTIMIZATION_NOT_COMPUTABLE,API_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE,GOLDEN_VALIDATION_NOT_COMPUTABLE`

### TASK-022

- public_entry_point: `hexagent.exchangers.shell_tube.shell_bundle_geometry.validate_request`
- schema_version: `task022.shell-bundle-geometry.v1`
- input_identity: `e6e4ba613369e66973b2ae64701380ac8d4864ca960e67d96b4adb15684f9c22`
- output_identity: `c308d5d62d21c3fcf44f4485ad5266e4951dc47f4560bdd3f85ad3ecb7bd95c0`
- result_hash: `c308d5d62d21c3fcf44f4485ad5266e4951dc47f4560bdd3f85ad3ecb7bd95c0`
- result_id: `43220e94-2a10-591c-aa14-532794711298`
- blockers_count: `0`
- warnings_count: `5`
- upstream_identity_bindings: `{"task021_layout_hash":"7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6","task023_record_hash":"7b956986b61c7fff1041f692f6ea5653c11865cf1bbd277257b93aa94c64b2e0"}`
- deferred_capabilities: `BAFFLE_DESIGN_NOT_COMPUTABLE,PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE,NOZZLE_AND_FLOW_PATH_DESIGN_NOT_COMPUTABLE,UTUBE_BEND_GEOMETRY_NOT_COMPUTABLE,SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE,KERN_SCREENING_NOT_COMPUTABLE,BELL_DELAWARE_NOT_COMPUTABLE,SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE,TUBE_SIDE_PRESSURE_DROP_NOT_COMPUTABLE,VIBRATION_NOT_COMPUTABLE,THERMAL_EXPANSION_NOT_COMPUTABLE,MECHANICAL_BOUNDARY_NOT_COMPUTABLE,MATERIAL_SELECTION_NOT_COMPUTABLE,MASS_NOT_COMPUTABLE,COST_NOT_COMPUTABLE,OPTIMIZATION_NOT_COMPUTABLE,API_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE,GOLDEN_VALIDATION_NOT_COMPUTABLE`

### TASK-023

- public_entry_point: `hexagent.shell_geometry_catalogs.catalog.parse_shell_geometry_catalog`
- schema_version: `task023.approved-shell-geometry-catalog.v1`
- input_identity: `a296832039f3ad9898d5f6813974986b187b9817d91b44cbda143932651f23d2`
- output_identity: `7b956986b61c7fff1041f692f6ea5653c11865cf1bbd277257b93aa94c64b2e0`
- result_hash: `0f0c2126998dff2fb7e71595cb2acf03b7005586859536de207fa399b824ac82`
- result_id: `synthetic-catalog-1`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{}`
- deferred_capabilities: ``

### TASK-024

- public_entry_point: `hexagent.exchangers.shell_tube.baffle_geometry.geometry.compute_geometry_foundation`
- schema_version: `task024.baffle-geometry-foundation.v1`
- input_identity: `eccf54b5bfc72cebc8475732a997ec45246c0b519e621dc9ae9de449ee1a5dad`
- output_identity: `0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8`
- result_hash: `0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8`
- result_id: `0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{"task022_geometry_hash":"c308d5d62d21c3fcf44f4485ad5266e4951dc47f4560bdd3f85ad3ecb7bd95c0"}`
- deferred_capabilities: `CROSSFLOW_FLOW_AREA_NOT_COMPUTABLE,WINDOW_FLOW_AREA_NOT_COMPUTABLE,HYDRAULIC_DIAMETER_NOT_COMPUTABLE,SHELL_SIDE_THERMAL_RATING_NOT_COMPUTABLE,SHELL_SIDE_PRESSURE_DROP_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE`

### TASK-025

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side.evaluate_task025`
- schema_version: `task025.result.v1`
- input_identity: `7fd810cc703ce99b437bb6ab0375638e80d205b107aefa8363505a57e0a1fd2d`
- output_identity: `9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca`
- result_hash: `9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca`
- result_id: `5465cef3-7101-5196-a548-17fa268ecc22`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{"task021_layout_hash":"7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6","task024_foundation_hash":"0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8"}`
- deferred_capabilities: `SHELL_DIAMETER_NOT_COMPUTABLE,BAFFLE_DESIGN_NOT_COMPUTABLE,PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE,THERMAL_RATING_NOT_COMPUTABLE,KERN_SCREENING_NOT_COMPUTABLE,BELL_DELAWARE_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,THERMAL_EXPANSION_NOT_COMPUTABLE,MECHANICAL_BOUNDARY_NOT_COMPUTABLE,MATERIAL_SELECTION_NOT_COMPUTABLE,MASS_NOT_COMPUTABLE,COST_NOT_COMPUTABLE,OPTIMIZATION_NOT_COMPUTABLE,API_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE,GOLDEN_VALIDATION_NOT_COMPUTABLE`

### TASK-026

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side_thermal.compute_tube_side_heat_transfer_coefficient`
- schema_version: `task026-r7.schema.v1`
- input_identity: `248cfec6b6d8fe7642ffda194db5a8b5eef59cf85c8bc440bbc67ae4e207a381`
- output_identity: `4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd`
- result_hash: `4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd`
- result_id: `0c0f0652-cd8e-5e20-835f-f01ea34bcbec`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{"task025_flow_cross_section_wetted_perimeter_m":"0.05026548","task025_hydraulic_authority_hash":"a54efe3c83bee449d69d14697b461fb24f94adf9f2c2afecc27d2442f207293b","task025_hydraulic_diameter_m":"0.01600000","task025_internal_heat_transfer_surface_area_m2":"2.1940883093","task025_internal_volume_m3":"0.008776353237","task025_result_hash":"9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca","task025_single_tube_flow_area_m2":"0.0002010619"}`
- deferred_capabilities: `SHELL_SIDE_NOT_COMPUTABLE,OVERALL_U_NOT_COMPUTABLE,UA_NOT_COMPUTABLE,LMTD_NOT_COMPUTABLE,EFFECTIVENESS_NOT_COMPUTABLE,HEAT_DUTY_NOT_COMPUTABLE,OUTLET_TEMPERATURES_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,TWO_PHASE_NOT_COMPUTABLE,PROPERTY_DATABASE_NOT_COMPUTABLE,NETWORK_PROPERTY_LOOKUP_NOT_COMPUTABLE,API_NOT_COMPUTABLE,CLI_NOT_COMPUTABLE,PERSISTENCE_NOT_COMPUTABLE,REPORT_GENERATION_NOT_COMPUTABLE,WALL_VISCOSITY_CORRECTION_NOT_COMPUTABLE,ITERATIVE_WALL_TEMPERATURE_NOT_COMPUTABLE`
- bulk_velocity_m_s: `0.2768069`
- reynolds_number: `4412.1463`
- prandtl_number: `7.0026`
- flow_regime: `TURBULENT`
- correlation_id: `tube_turbulent_gnielinski`
- correlation_version: `1.0.0`
- nusselt_number: `35.3464`
- tube_side_heat_transfer_coefficient_w_m2_k: `1321.954257`

## Blocked Matrix

### TASK-020-BLOCKED-001

- task_id: `TASK-020`
- expected_blocker_codes: `['STC_UNKNOWN_FIELD']`
- actual_blocker_codes: `['STC_UNKNOWN_FIELD']`
- expected_field_paths: `[]`
- actual_field_paths: `[]`
- expected_stage_rank: `None`
- actual_stage_rank: `None`
- expected_stage_token: `stage-1-unknown-field-rejection`
- actual_stage_token: `stage-1-unknown-field-rejection`
- field_paths: `[]`
- stage_rank: `None`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `6bc5c4ea4182f23e9aa742465dd2567f4247f7c14aad7dd31d827c0d997c9059`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-021-BLOCKED-001

- task_id: `TASK-021`
- expected_blocker_codes: `['STL_UNKNOWN_FIELD']`
- actual_blocker_codes: `['STL_UNKNOWN_FIELD']`
- expected_field_paths: `[['request']]`
- actual_field_paths: `[['request']]`
- expected_stage_rank: `None`
- actual_stage_rank: `None`
- expected_stage_token: `stage-1-unknown-field-rejection`
- actual_stage_token: `stage-1-unknown-field-rejection`
- field_paths: `[['request']]`
- stage_rank: `None`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `d4cb17aecc39e45ef5975906676cf7586e56a7b8a941b93e9210979240b15c8d`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-022-BLOCKED-001

- task_id: `TASK-022`
- expected_blocker_codes: `['SBG_UNKNOWN_FIELD']`
- actual_blocker_codes: `['SBG_UNKNOWN_FIELD']`
- expected_field_paths: `[['not_a_real_field']]`
- actual_field_paths: `[['not_a_real_field']]`
- expected_stage_rank: `None`
- actual_stage_rank: `None`
- expected_stage_token: `stage-1-unknown-field-rejection`
- actual_stage_token: `stage-1-unknown-field-rejection`
- field_paths: `[['not_a_real_field']]`
- stage_rank: `None`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `bd6a30862873214f7be0744c1fd98c23f3822d53005a98e3a05eda1745a2234a`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-023-BLOCKED-001

- task_id: `TASK-023`
- expected_blocker_codes: `['SGC_UNKNOWN_FIELD']`
- actual_blocker_codes: `['SGC_UNKNOWN_FIELD']`
- expected_field_paths: `[['raw_catalog', 'unknown_field']]`
- actual_field_paths: `[['raw_catalog', 'unknown_field']]`
- expected_stage_rank: `2`
- actual_stage_rank: `2`
- expected_stage_token: `stage-1-unknown-field-rejection`
- actual_stage_token: `stage-1-unknown-field-rejection`
- field_paths: `[['raw_catalog', 'unknown_field']]`
- stage_rank: `2`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `9c7cb443429b03369de4f53ab55200f08dd95d2822ccc626810c0ffdbd8543d6`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-024-BLOCKED-001

- task_id: `TASK-024`
- expected_blocker_codes: `['BFG_BAFFLE_THICKNESS_INVALID']`
- actual_blocker_codes: `['BFG_BAFFLE_THICKNESS_INVALID']`
- expected_field_paths: `[['design_authority', 'baffle_thickness_m']]`
- actual_field_paths: `[['design_authority', 'baffle_thickness_m']]`
- expected_stage_rank: `0`
- actual_stage_rank: `0`
- expected_stage_token: `stage-9-decimal-lexical-validation`
- actual_stage_token: `stage-9-decimal-lexical-validation`
- field_paths: `[['design_authority', 'baffle_thickness_m']]`
- stage_rank: `0`
- stage_token: `stage-9-decimal-lexical-validation`
- blocked_result_hash: `67d2fc3d4e1f927897c1c2e0e8d85e9a3bf30ff7b574a0e99ab124c4f52fc72a`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-025-BLOCKED-001

- task_id: `TASK-025`
- expected_blocker_codes: `['BL_003_BLOCKED_INPUT_REJECTED']`
- actual_blocker_codes: `['BL_003_BLOCKED_INPUT_REJECTED']`
- expected_field_paths: `[['raw_input']]`
- actual_field_paths: `[['raw_input']]`
- expected_stage_rank: `1`
- actual_stage_rank: `1`
- expected_stage_token: `stage-S00-raw-boundary`
- actual_stage_token: `stage-S00-raw-boundary`
- field_paths: `[['raw_input']]`
- stage_rank: `1`
- stage_token: `stage-S00-raw-boundary`
- blocked_result_hash: `1eaa3b7239267a2b51e6319a5ecde27d2a6ecf60e28009db23ebf1be1ddb0ad2`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-026-BLOCKED-001

- task_id: `TASK-026`
- expected_blocker_codes: `['BL_RAW_INPUT_BOUNDARY_MALFORMED']`
- actual_blocker_codes: `['BL_RAW_INPUT_BOUNDARY_MALFORMED']`
- expected_field_paths: `[]`
- actual_field_paths: `[]`
- expected_stage_rank: `None`
- actual_stage_rank: `None`
- expected_stage_token: `S00`
- actual_stage_token: `S00`
- field_paths: `[]`
- stage_rank: `None`
- stage_token: `S00`
- blocked_result_hash: `45d0bafd38b7bd819d31eecd94cade1a293a3d187a67cb0cbf0f9f726f7956b9`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

## Excluded Scope

- `shell_side_heat_transfer`: out of v0.1.0 scope
- `pressure_drop`: out of v0.1.0 scope
- `overall_U`: out of v0.1.0 scope
- `UA`: out of v0.1.0 scope
- `LMTD`: out of v0.1.0 scope
- `duty`: out of v0.1.0 scope
- `outlet_temperature`: out of v0.1.0 scope
- `property_database_runtime_integration`: DEFERRED — Phase B / R9+
- `production_algorithm_modification`: PROHIBITED in demo round
- `public_contract_modification`: PROHIBITED in demo round

