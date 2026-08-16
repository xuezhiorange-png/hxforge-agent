# v0.2.0 TASK-020 -> TASK-029 Release Demo Evidence

## Release Identity

- schema_version: `hxforge.release-evidence.v0.2.0`
- release_version: `0.2.0`
- source_main_sha: `5f9d33371e524261fac2c05f06d1256392b19b5b`
- authority_id: `CHARLES_V0_2_TASK020_TO_TASK029_RELEASE_DEMO_AUTHORIZATION`

## Scope and Production Graph

- target_version: `v0.2.0`
- release_acceptance_is_not_engineering_correctness_proof: `True`
- self_edge_count: `0`
- actual_production_bindings_only: `True`

### Upstream Chain Bindings

- `TASK-020` -> `TASK-021`: binding=`645a241410fc80a1f495b113c0c74afc44db548b5e5dfc0a1d5d5ae02fe9667d` (downstream_field='tube_layout.task020_configuration_hash')
- `TASK-021` -> `TASK-022`: binding=`7c912e68b67efdeb947b0c3587bf1682dda0f15214d5a7c04301f06af5510cb6` (downstream_field='tube_layout.layout_hash')
- `TASK-023` -> `TASK-022`: binding=`7b956986b61c7fff1041f692f6ea5653c11865cf1bbd277257b93aa94c64b2e0` (downstream_field='shell_bundle_geometry_request.approved_shell_geometry.record_hash')
- `TASK-022` -> `TASK-024`: binding=`c308d5d62d21c3fcf44f4485ad5266e4951dc47f4560bdd3f85ad3ecb7bd95c0` (downstream_field='shell_bundle_geometry.geometry_hash')
- `TASK-024` -> `TASK-025`: binding=`0ddfeb612b43734f578830d26bfbf76add9572d4d84b6525560570e750aee8c8` (downstream_field='task024_foundation_hash')
- `TASK-025` -> `TASK-026`: binding=`9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca` (downstream_field='upstream_task025_valid_result.result_hash')
- `TASK-026` -> `TASK-027`: binding=`4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd` (downstream_field='task025_result/task026_result/property_snapshot')
- `TASK-026` -> `TASK-028`: binding=`4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd` (downstream_field='task025_result/task026_result/property_snapshot')
- `TASK-027` -> `TASK-029`: binding=`d04df51132dcc6d06c3d6fca8226c5404d33e54376624e3699137d489d9f8990` (downstream_field='task027_success_result.result_hash')
- `TASK-028` -> `TASK-029`: binding=`1fe2745f6a596dc56782d3c8f1e7e834e227abd45139fb8e0e1dfd6e0892df9d` (downstream_field='task028_success_result.result_hash')

## Success Demonstration

### TASK-027

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop.compute_task027_friction_pressure_drop`
- result_hash: `d04df51132dcc6d06c3d6fca8226c5404d33e54376624e3699137d489d9f8990`
- result_id: `182cd2f2-7bb9-5394-81b6-ff31ace74f31`

### TASK-028

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side_local_loss.pipeline.compute_task028_local_loss`
- result_hash: `1fe2745f6a596dc56782d3c8f1e7e834e227abd45139fb8e0e1dfd6e0892df9d`
- result_id: `8c44be44-19bb-5c01-934d-3a8660f3e99f`

### TASK-029

- public_entry_point: `hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.pipeline.compute_task029_composition`
- result_hash: `dc9916d3f133fe815ebfd97f5b94253263053ce54baaca35f2112d057ae36290`
- result_id: `02bc50b4-14f2-5857-8a92-adab2a7fa952`
- modeled_total_tube_side_pressure_drop_pa: `1994.294`
- completeness_ledger_hash: `71bb9a261dc023b1f041958be6b5773053355e280db54dd9c0a10995e45fbb59`
- composition_authority_hash: `6beae22f9f0be7d91ae75de2e8b916f68998e722c976e152faba807643d7a80b`

## Blocked Demonstration Matrix

### B01_EARLY_CHAIN_FAIL_CLOSED

- stage: `TASK-020`
- actual_blocker_codes: `['STC_UNKNOWN_FIELD']`
- actual_field_paths: `[]`
- blocked_result_hash: `6bc5c4ea4182f23e9aa742465dd2567f4247f7c14aad7dd31d827c0d997c9059`
- partial_result_present: `False`

### B02_TASK027_UPSTREAM_BINDING_MISMATCH

- stage: `TASK-027`
- actual_blocker_codes: `['BL_T027_UPSTREAM_IDENTITY_MISMATCH']`
- actual_field_paths: `[['upstream_geometry_hash']]`
- blocked_result_hash: `a8a10237ace9c33536fed8243e3a0c3a880f21d52d8934cb10b7b275398f0460`
- partial_result_present: `False`

### B03_TASK028_UPSTREAM_BINDING_OR_PROVENANCE_MISMATCH

- stage: `TASK-028`
- actual_blocker_codes: `['BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH']`
- actual_field_paths: `[['property_snapshot_hash']]`
- blocked_result_hash: `b73067553ce63ff2eeedb53bab7458ee72bea3a9ca9f42933dc92624aed10f7b`
- partial_result_present: `False`

### B04_TASK029_TYPED_CROSS_INPUT_MISMATCH

- stage: `TASK-029`
- actual_blocker_codes: `['BL_T029_UPSTREAM_IDENTITY_MISMATCH', 'BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID']`
- actual_field_paths: `[['task028_success_result', 'property_snapshot_hash'], ['task028_success_result', 'result_hash']]`
- blocked_result_hash: `264053ea598a0373fdf4ee76c873053b76ace810eaade007457bd4740ed5c10e`
- partial_result_present: `False`

### B05_TASK029_RAW_BOUNDARY_REJECTION

- stage: `TASK-029`
- actual_blocker_codes: `['BL_T029_REQUEST_UNKNOWN_FIELD']`
- actual_field_paths: `[['unexpected']]`
- blocked_result_hash: `c80a0ddfa809101f44ffad48923a15ebf2376362181348d45379a7de2b526b1a`
- partial_result_present: `False`

## Producer Identity Bindings

- PROPERTY_SNAPSHOT_HASH: `0fcbeaa93fac68296b638d36c92955336d49b1208eda8055e4ab822cbc60f4f8`
- TASK025_HYDRAULIC_AUTHORITY_HASH: `a54efe3c83bee449d69d14697b461fb24f94adf9f2c2afecc27d2442f207293b`
- TASK025_RESULT_HASH: `9b98ab37192e3945854fb298246ec2fd173c65b0a39ad6f88761f80655dfdeca`
- TASK026_RESULT_HASH: `4a153c4209060a70907b28cee04f780b430052bd21584fe16da997f3170603dd`
- TASK027_RESULT_HASH: `d04df51132dcc6d06c3d6fca8226c5404d33e54376624e3699137d489d9f8990`
- TASK028_RESULT_HASH: `1fe2745f6a596dc56782d3c8f1e7e834e227abd45139fb8e0e1dfd6e0892df9d`
- TASK029_COMPLETENESS_LEDGER_HASH: `71bb9a261dc023b1f041958be6b5773053355e280db54dd9c0a10995e45fbb59`
- TASK029_COMPOSITION_AUTHORITY_HASH: `6beae22f9f0be7d91ae75de2e8b916f68998e722c976e152faba807643d7a80b`
- TASK029_RESULT_HASH: `dc9916d3f133fe815ebfd97f5b94253263053ce54baaca35f2112d057ae36290`
- TASK029_RESULT_ID: `02bc50b4-14f2-5857-8a92-adab2a7fa952`

## Determinism Evidence

- canonical_json_contract: `{'sort_keys': True, 'separators': [',', ':'], 'ensure_ascii': True, 'trailing_lf_count': 1}`
- frozen_json_match: `True`
- frozen_markdown_match: `True`
- py311_json_bytes_eq_py312_json_bytes: `True`
- py311_markdown_bytes_eq_py312_markdown_bytes: `True`
- repeat_run_json_bytes_identical: `True`
- repeat_run_markdown_bytes_identical: `True`

## Version Metadata

- pyproject_version: `0.2.0`
- target_distribution_version: `0.2.0`
- uv_lock_project_version: `0.2.0`
- version_bearing_files: `['pyproject.toml', 'uv.lock']`

## Release Manifest

- digest_algorithm: `sha256`
- digest_input: `EXACT_FILE_BYTES`
- manifest_order: `LEXICOGRAPHIC_BY_PATH`
- member_paths: `['release_evidence/v0.2.0/release-acceptance.md', 'release_evidence/v0.2.0/task020-to-task029-demo.json', 'release_evidence/v0.2.0/task020-to-task029-demo.md']`
- paths_are_repository_relative_posix: `True`
- self_digest_entry: `False`

## Release Acceptance

- item_count: `20`
- A01_ALLOCATION_IDENTITY: `PASS`
- A02_SCOPE_ISOLATION: `PASS`
- A03_TASK020_TO_TASK029_ACTUAL_GRAPH_BINDING: `PASS`
- A04_SUCCESS_DEMO_EXACTNESS: `PASS`
- A05_BLOCKED_MATRIX_EXACTNESS: `PASS`
- A06_NO_PARTIAL_RESULT_ACROSS_BLOCKED_MATRIX: `PASS`
- A07_TASK029_COMPLETENESS_LEDGER_PRESENT: `PASS`
- A08_PRODUCER_IDENTITY_BINDINGS_PRESERVED: `PASS`
- A09_PY311_PY312_CANONICAL_BYTE_IDENTITY: `PASS`
- A10_REPEAT_RUN_DETERMINISM: `PASS`
- A11_FROZEN_JSON_MATCH: `PASS`
- A12_FROZEN_MARKDOWN_MATCH: `PASS`
- A13_VERSION_METADATA_CONSISTENCY: `PASS`
- A14_RELEASE_MANIFEST_COMPLETENESS: `PASS`
- A15_CI_SHARD_REGISTRATION: `PASS`
- A16_GLOBAL_TEST_COLLECTION: `PASS`
- A17_RUFF_FORMAT_MYPY_AND_DIFF_CHECK: `PASS`
- A18_NO_UNAUTHORIZED_ENGINEERING_SCOPE: `PASS`
- A19_NO_ENGINEERING_CORRECTNESS_WAIVER: `PASS`
- A20_RELEASE_EVIDENCE_PROVENANCE_COMPLETE: `PASS`

## Non-Claims / Engineering-Proof Boundary

- data_class: `SYNTHETIC_DEMO_VALUE`
- engineering_recommendation: `False`
- release_acceptance_is_not_engineering_correctness_proof: `True`
- standard_claim: `False`
- vendor_specification: `False`

