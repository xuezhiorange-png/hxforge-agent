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
- cross_version_sha256: `fff1d74469502f02769e74f0e1c4234cac03c4662328a6d8bba15dfe21a500a5`

## Upstream Chain Bindings

- `TASK-020` -> `TASK-021`: `645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d`
- `TASK-021` -> `TASK-022`: `7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6`
- `TASK-022` -> `TASK-024`: `654dff703f41dd3d7f4638f4aa85d0666697d2c146875a3412f0a80101f362ba`
- `TASK-024` -> `TASK-025`: `01abfbae521233cd73bbe49c62db62fe747a7730b8c9e97b822c52fc01b530ff`
- `TASK-025` -> `TASK-026`: `9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca`
- `TASK-026` -> `TASK-026`: `1ce2e94fb8726c58088a5c11baafd6610b4e6390187d7044100d3a50a9d72c58`

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
- input_identity: `9932c04a1c72743f231807ec16b9149a8eb49956ab75ebb8e99fc084290c60de`
- output_identity: `654dff703f41dd3d7f4638f4aa85d0666697d2c146875a3412f0a80101f362ba`
- result_hash: `654dff703f41dd3d7f4638f4aa85d0666697d2c146875a3412f0a80101f362ba`
- result_id: `4970b7d8-8a4e-58bc-b211-b691ebdd928e`
- blockers_count: `0`
- warnings_count: `6`
- upstream_identity_bindings: `{"task021_layout_hash":"7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6"}`
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
- input_identity: `885a61b81c18fd81d4bde78d1467487bce2f1c0a608ed5a1dbce42a100542098`
- output_identity: `01abfbae521233cd73bbe49c62db62fe747a7730b8c9e97b822c52fc01b530ff`
- result_hash: `01abfbae521233cd73bbe49c62db62fe747a7730b8c9e97b822c52fc01b530ff`
- result_id: `01abfbae521233cd73bbe49c62db62fe747a7730b8c9e97b822c52fc01b530ff`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{"task022_geometry_hash":"654dff703f41dd3d7f4638f4aa85d0666697d2c146875a3412f0a80101f362ba"}`
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
- upstream_identity_bindings: `{"task021_layout_hash":"7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6","task024_foundation_hash":"01abfbae521233cd73bbe49c62db62fe747a7730b8c9e97b822c52fc01b530ff"}`
- deferred_capabilities: `SHELL_DIAMETER_NOT_COMPUTABLE,BAFFLE_DESIGN_NOT_COMPUTABLE,PASS_PARTITION_ASSIGNMENT_NOT_COMPUTABLE,THERMAL_RATING_NOT_COMPUTABLE,KERN_SCREENING_NOT_COMPUTABLE,BELL_DELAWARE_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,THERMAL_EXPANSION_NOT_COMPUTABLE,MECHANICAL_BOUNDARY_NOT_COMPUTABLE,MATERIAL_SELECTION_NOT_COMPUTABLE,MASS_NOT_COMPUTABLE,COST_NOT_COMPUTABLE,OPTIMIZATION_NOT_COMPUTABLE,API_NOT_COMPUTABLE,REPORT_NOT_COMPUTABLE,GOLDEN_VALIDATION_NOT_COMPUTABLE`

### TASK-026

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side_thermal.compute_tube_side_heat_transfer_coefficient`
- schema_version: `task026-r7.schema.v1`
- input_identity: `248cfec6b6d8fe7642ffda194db5a8b5eef59cf85c8bc440bbc67ae4e207a381`
- output_identity: `1ce2e94fb8726c58088a5c11baafd6610b4e6390187d7044100d3a50a9d72c58`
- result_hash: `1ce2e94fb8726c58088a5c11baafd6610b4e6390187d7044100d3a50a9d72c58`
- result_id: `3c5e5cfa-1fe2-5dfc-ab67-d40abf2e021e`
- blockers_count: `0`
- warnings_count: `0`
- upstream_identity_bindings: `{"task025_hydraulic_authority_hash":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","task025_result_hash":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}`
- deferred_capabilities: `SHELL_SIDE_NOT_COMPUTABLE,OVERALL_U_NOT_COMPUTABLE,UA_NOT_COMPUTABLE,LMTD_NOT_COMPUTABLE,EFFECTIVENESS_NOT_COMPUTABLE,HEAT_DUTY_NOT_COMPUTABLE,OUTLET_TEMPERATURES_NOT_COMPUTABLE,PRESSURE_DROP_NOT_COMPUTABLE,TWO_PHASE_NOT_COMPUTABLE,PROPERTY_DATABASE_NOT_COMPUTABLE,NETWORK_PROPERTY_LOOKUP_NOT_COMPUTABLE,API_NOT_COMPUTABLE,CLI_NOT_COMPUTABLE,PERSISTENCE_NOT_COMPUTABLE,REPORT_GENERATION_NOT_COMPUTABLE,WALL_VISCOSITY_CORRECTION_NOT_COMPUTABLE,ITERATIVE_WALL_TEMPERATURE_NOT_COMPUTABLE`
- bulk_velocity_m_s: `0.0500898`
- reynolds_number: `499.0020`
- prandtl_number: `7.0026`
- flow_regime: `LAMINAR`
- correlation_id: `tube_laminar_cwt`
- correlation_version: `1.0.0`
- nusselt_number: `3.6600`
- tube_side_heat_transfer_coefficient_w_m2_k: `219.014400`

## Blocked Matrix

### TASK-020-BLOCKED-001

- task_id: `TASK-020`
- expected_blocker_codes: `['STC_UNKNOWN_FIELD']`
- actual_blocker_codes: `['STC_UNKNOWN_FIELD']`
- field_paths: `['']`
- stage_rank: `1`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `6bc5c4ea4182f23e9aa742465dd2567f4247f7c14aad7dd31d827c0d997c9059`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-021-BLOCKED-001

- task_id: `TASK-021`
- expected_blocker_codes: `['STL_UNKNOWN_FIELD']`
- actual_blocker_codes: `['STL_UNKNOWN_FIELD']`
- field_paths: `['request']`
- stage_rank: `1`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `d4cb17aecc39e45ef5975906676cf7586e56a7b8a941b93e9210979240b15c8d`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-022-BLOCKED-001

- task_id: `TASK-022`
- expected_blocker_codes: `['SBG_UNKNOWN_FIELD']`
- actual_blocker_codes: `['SBG_UNKNOWN_FIELD']`
- field_paths: `['not_a_real_field']`
- stage_rank: `1`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `bd6a30862873214f7be0744c1fd98c23f3822d53005a98e3a05eda1745a2234a`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-023-BLOCKED-001

- task_id: `TASK-023`
- expected_blocker_codes: `['SGC_UNKNOWN_FIELD']`
- actual_blocker_codes: `['SGC_UNKNOWN_FIELD']`
- field_paths: `['raw_catalog.unknown_field']`
- stage_rank: `1`
- stage_token: `stage-1-unknown-field-rejection`
- blocked_result_hash: `9c7cb443429b03369de4f53ab55200f08dd95d2822ccc626810c0ffdbd8543d6`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-024-BLOCKED-001

- task_id: `TASK-024`
- expected_blocker_codes: `['BFG_BAFFLE_THICKNESS_INVALID']`
- actual_blocker_codes: `['BFG_BAFFLE_THICKNESS_INVALID']`
- field_paths: `['design_authority.baffle_thickness_m']`
- stage_rank: `0`
- stage_token: `stage-9-decimal-lexical-validation`
- blocked_result_hash: `67d2fc3d4e1f927897c1c2e0e8d85e9a3bf30ff7b574a0e99ab124c4f52fc72a`
- partial_result_present: `False`
- success_identity_present: `False`
- numeric_result_fields_present: `False`

### TASK-025-BLOCKED-001

- task_id: `TASK-025`
- expected_blocker_codes: `['BL_RAW_INPUT_NOT_EXACT_DICT']`
- actual_blocker_codes: `[<BlockerCode.BL_003_BLOCKED_INPUT_REJECTED: 'BL_003_BLOCKED_INPUT_REJECTED'>]`
- field_paths: `[('raw_input',)]`
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
- field_paths: `['']`
- stage_rank: `0`
- stage_token: `stage-S00-raw-boundary`
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

