# v0.4 TASK020 -> TASK038 Demonstration

## Release Identity

- schema_version: `task039.release-demo.v1`
- profile_id: `hxforge.release_demo.v0_4`
- release_version: `0.4.0`
- source_definition: `Issue #214 R2_FROZEN`
- allocation_authority: `Issue #207 R3_FROZEN`
- base_main_sha: `ba6d29b5af70dc9c2cdd0832ae0d8de2bb2ea09e`
- base_main_tree: `ec07e31eec7d4d377ae0fdcfa9633190ad0ae060`

## Production Graph

- stages: `['TASK020', 'TASK021', 'TASK025', 'TASK026', 'TASK031', 'TASK032', 'TASK033', 'TASK034', 'TASK035', 'TASK037', 'TASK038', 'TASK039']`
- public_operations: `['hexagent.exchangers.shell_tube.validate_request', 'hexagent.exchangers.shell_tube.tube_layout.validate_request', 'hexagent.exchangers.shell_tube.tube_side.evaluate_task025', 'hexagent.exchangers.shell_tube.tube_side_thermal.build_raw_tube_side_request_envelope', 'hexagent.exchangers.shell_tube.tube_side_thermal.compute_tube_side_heat_transfer_coefficient', 'hexagent.exchangers.shell_tube.shell_side_hydraulic_geometry.validate_request', 'hexagent.exchangers.shell_tube.shell_side_flow_state.validate_request', 'hexagent.exchangers.shell_tube.shell_side_heat_transfer.validate_request', 'hexagent.exchangers.shell_tube.shell_side_pressure_drop.validate_request', 'hexagent.exchangers.shell_tube.shell_side_thermal_hydraulic_composition.validate_request', 'hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.validate_request', 'hexagent.exchangers.shell_tube.overall_heat_transfer_resistance.verify_task037_success_identity', 'hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.build_raw_overall_u_ua_request', 'hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.evaluate_task038', 'hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.verify_task038_success_identity', 'hexagent.release_demo.v0_4.validate_request']`
- statuses: `{'TASK020': 'VALID', 'TASK021': 'VALID', 'TASK025': 'VALID', 'TASK026': 'VALID', 'TASK031': 'VALID', 'TASK032': 'VALID', 'TASK033': 'VALID', 'TASK034': 'VALID', 'TASK035': 'VALID', 'TASK037': 'VALID', 'TASK038': 'VALID', 'TASK039': 'VALID'}`
- fixture_only_result_substitution: `False`
- expected_output_used_as_input: `False`
- private_helper_stage_bypass: `False`
- no_upstream_engineering_recomputation: `True`

## Success Demonstration

- demo_id: `DEMO_SUCCESS_001`
- status: `VALID`
- task038_result_hash: `a81922f4c86ee340019fba2fd52d24d1abdca7af69d81e88fb65bc6a77dbf91c`
- task038_result_id: `a0df48d7-1a82-5919-8fa8-bb8ea6e4b3ef`
- modeled_overall_heat_transfer_coefficient_w_m2_k: `550.759554541`
- outer_tube_surface_effective_area_m2: `2.7426103866`
- modeled_ua_w_k: `1510.518874803`

## Blocked Demonstrations

- `DEMO_BLOCKED_B01`: `BL_TASK025_RESULT_INVALID` / `S02_TASK025_RESULT_REPLAY` / `task025_result`
- `DEMO_BLOCKED_B02`: `BL_TASK026_RESULT_INVALID` / `S03_TASK026_RESULT_REPLAY` / `task026_result`
- `DEMO_BLOCKED_B03`: `BL_TASK035_RESULT_INVALID` / `S04_TASK035_RESULT_REPLAY` / `task035_result`
- `DEMO_BLOCKED_B04`: `BL_TASK037_RESULT_INVALID` / `S05_TASK037_RESULT_REPLAY` / `task037_result`
- `DEMO_BLOCKED_B05`: `BL_HYDRAULIC_AUTHORITY_MISMATCH` / `S06_HYDRAULIC_AND_TASK025_JOIN` / `cross_producer`
- `DEMO_BLOCKED_B06`: `BL_SERVICE_BINDING_INVALID` / `S01_REQUEST_AND_AUTHORITY_SCHEMA` / `tube_side_service_binding_authority`
- `DEMO_BLOCKED_B07`: `BL_RAW_INPUT_BOUNDARY_MALFORMED` / `S00_RAW_INPUT_BOUNDARY` / `raw_input`
- `DEMO_BLOCKED_B08`: `T039_HISTORICAL_RELEASE_AUTHORITY_MISMATCH` / `R10` / `historical_release_authority.v03_tag_target_commit`
- `DEMO_BLOCKED_B09`: `T039_VERSION_METADATA_MISMATCH` / `R20` / `version_metadata.pyproject_version`
- `DEMO_BLOCKED_B10`: `T039_RELEASE_ARTIFACT_DIGEST_MISMATCH` / `R40` / `artifact_digests.A03`

## Capability Boundary

- available: `TUBE_SIDE_SINGLE_PHASE_HTC, TUBE_SIDE_MODELED_PRESSURE_DROP, SHELL_SIDE_HYDRAULIC_GEOMETRY, SHELL_SIDE_SINGLE_PHASE_FLOW_STATE, SHELL_SIDE_SINGLE_PHASE_HTC_SCREENING, SHELL_SIDE_MODELED_DP_SCREENING, SHELL_SIDE_THERMAL_HYDRAULIC_COMPOSITION, SHELL_SIDE_APPLICABILITY_LEDGER, SHELL_SIDE_COMPLETENESS_LEDGER, TASK037_SURFACE_WALL_FOULING_RESISTANCE, TASK038_FULL_RESISTANCE_OVERALL_U_AREA_UA, OVERALL_U, OUTER_TUBE_SURFACE_EFFECTIVE_AREA, UA`
- intentionally_unavailable: `LMTD, LMTD_CORRECTION_FACTOR, EFFECTIVENESS_NTU, HEAT_DUTY, OUTLET_TEMPERATURES, ENERGY_BALANCE_ITERATION, THERMAL_RATING_ITERATION, WALL_TEMPERATURE_ITERATION, AUTOMATIC_WALL_VISCOSITY_ITERATION, FULL_EXCHANGER_THERMAL_RATING, THERMAL_SIZING, GEOMETRY_OPTIMIZATION, BELL_DELAWARE, SHELL_TO_BAFFLE_LEAKAGE_CORRECTION, TUBE_TO_BAFFLE_LEAKAGE_CORRECTION, BUNDLE_BYPASS_CORRECTION, UNEQUAL_BAFFLE_SPACING_CORRECTION, TWO_PHASE_HEAT_TRANSFER, TWO_PHASE_PRESSURE_DROP, COMPRESSIBLE_PATH_INTEGRATION, FLOW_INDUCED_VIBRATION, NOZZLE_SIZING, MECHANICAL_ADEQUACY, MATERIAL_SELECTION, COST_OPTIMIZATION, PUBLIC_API_EXTENSION, PERSISTENCE_EXTENSION, UI, REPORTING`
- release_acceptance_is_not_engineering_correctness_proof: `true`

## Identity and Provenance

- TASK020_CONFIGURATION_ID: `559ce83b-4e4e-55ab-a913-8be103736600`
- TASK020_CONFIGURATION_HASH: `95f40b04da37bde23a2d9b2f8294b0236d3771a66ca3e274dd387db839c71298`
- TASK021_LAYOUT_ID: `73e2dfe2-a1e2-5ad4-a128-cbdb1e06f5c0`
- TASK021_LAYOUT_HASH: `364fe71d7ce7c99e2db88462b541769ec10ed4e7d7531074e1081c5984631033`
- TASK025_RESULT_HASH: `aeaaf58c762cd16c8542df8a67866c20f6ca643876f02a54ee2fcc948bb96495`
- TASK025_RESULT_ID: `bd85f929-57e4-5e99-9f70-2b8cdb5b4699`
- TASK026_RESULT_HASH: `0a81382bf58d388dbeb4b0ff7f32ffed990350ec788f53edaa5dc7c505e95a2a`
- TASK026_RESULT_ID: `4607659f-1aff-58db-ade7-978cf22647bc`
- TASK035_RESULT_HASH: `6cf6a807c77fbd3c5a2d72afd124f1811f956edc4c87d240a685d31a5468ba45`
- TASK035_RESULT_ID: `dadef150-3b20-53ff-812d-5c4f736444bd`
- TASK037_RESULT_HASH: `f815306d194c737ae6aff78cf8d7ef4ea5afbef1bf43d80ccb5c4639264a77d6`
- TASK037_RESULT_ID: `4aca6ce4-50c1-548f-bac5-9aa53b86f625`
- TASK038_RESULT_HASH: `a81922f4c86ee340019fba2fd52d24d1abdca7af69d81e88fb65bc6a77dbf91c`
- TASK038_RESULT_ID: `a0df48d7-1a82-5919-8fa8-bb8ea6e4b3ef`

## Acceptance

- acceptance_item_count: `30`
- status: `PASS`
