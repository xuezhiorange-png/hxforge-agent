"""Frozen TASK036 v0.3 release-demo contract.

The values in this module are projections of the accepted R5 Design.  They
are deliberately closed tuples: callers cannot add a stage, artifact, test,
or identity field by convention or directory discovery.
"""

from __future__ import annotations

from typing import Final

# ruff: noqa: E501

TASK_ID: Final = "TASK036"
PUBLIC_OPERATION: Final = "run_release_demo"
DESIGN_CONTRACT_PATH: Final = "docs/tasks/TASK-036-hxforge-v0.3-shell-side-thermal-hydraulic-integration-demonstration-release-acceptance.md"
SOURCE_DEFINITION_ISSUE: Final = "203"
SOURCE_DEFINITION_REVISION: Final = "R5"
SOURCE_DEFINITION_FREEZE_COMMENT_ID: Final = "5447744882"
SOURCE_MAIN_SHA: Final = "6687170cea93486468266475e56193d57981761b"
SOURCE_MAIN_TREE: Final = "8399dcf766b1c8d98794430e810d186134234d89"

TARGET_DISTRIBUTION_VERSION: Final = "0.3.0"
RELEASE_VERSION: Final = TARGET_DISTRIBUTION_VERSION
RELEASE_VERSION_DISPLAY_LABEL: Final = "v0.3"
IMPLEMENTATION_SOFTWARE_VERSION: Final = "task036-release-demo-impl-v1"
RELEASE_CANDIDATE_ID: Final = "TASK036-V03-RC1"
RELEASE_SOFTWARE_VERSION: Final = (
    "task036.shell-side-thermal-hydraulic-integration-release-acceptance-v1"
)
PROFILE_ID: Final = "hxforge.release_demo.task020_to_task035.v0_3"
IDENTITY_VERSION: Final = "R5_IDENTITY_REPAIRED_V1"
SEMANTIC_IDENTITY_VERSION: Final = "task036.release-identity.v1"
DEMO_SUCCESS_ID: Final = "DEMO_SUCCESS_001"
BLOCKED_DEMO_IDS: Final[tuple[str, ...]] = (
    "DEMO_BLOCKED_B01",
    "DEMO_BLOCKED_B02",
    "DEMO_BLOCKED_B03",
    "DEMO_BLOCKED_B04",
    "DEMO_BLOCKED_B05",
    "DEMO_BLOCKED_B06",
)

TASK034_SHELL_TYPE_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "shell_type",
    "task020_configuration_id",
    "task020_configuration_hash",
    "authority_source_id",
    "authority_source_version",
    "authority_record_id",
    "evidence_refs",
    "authority_hash",
)
TASK034_WALL_PROPERTY_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_result_id",
    "task032_result_hash",
    "property_snapshot_hash",
    "shell_side_wall_dynamic_viscosity_pa_s",
    "source_id",
    "source_version",
    "evidence_refs",
    "wall_property_snapshot_hash",
    "wall_property_authority_hash",
)

DEMO_INPUT_SCHEMA_VERSION: Final = "task036.shell-side-thermal-hydraulic-integration-demo-input.v1"
SUCCESS_RESULT_SCHEMA_ID: Final = "task036.shell-side-thermal-hydraulic-integration-demo.v1"
TYPED_BLOCKED_RESULT_SCHEMA_ID: Final = (
    "task036.shell-side-thermal-hydraulic-integration-demo-blocked.v1"
)
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_ID: Final = (
    "task036.shell-side-thermal-hydraulic-integration-demo-raw-boundary-blocked.v1"
)
DEMO_RESULT_SCHEMA_VERSION: Final = SUCCESS_RESULT_SCHEMA_ID
SUCCESS_RESULT_SCHEMA_VERSION: Final = SUCCESS_RESULT_SCHEMA_ID
TYPED_BLOCKED_RESULT_SCHEMA_VERSION: Final = TYPED_BLOCKED_RESULT_SCHEMA_ID
RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_VERSION: Final = RAW_BOUNDARY_BLOCKED_RESULT_SCHEMA_ID

DEMO_INPUT_FIELDS: Final[tuple[str, ...]] = (
    "TASK031_RAW_REQUEST_RECORD",
    "TASK032_PROPERTY_SNAPSHOT_RECORD",
    "TASK032_MASS_FLOW_AUTHORITY_RECORD",
    "TASK032_REQUEST_EVIDENCE_REFS",
    "TASK033_REQUEST_EVIDENCE_REFS",
    "TASK034_SHELL_TYPE_AUTHORITY_RECORD",
    "TASK034_WALL_PROPERTY_AUTHORITY_RECORD",
    "TASK034_REQUEST_EVIDENCE_REFS",
    "TASK035_EVIDENCE_REFS",
)
DEMO_INPUT_FIELD_ORDER: Final = DEMO_INPUT_FIELDS
TASK031_RAW_REQUEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "tube_layout",
    "baffle_geometry_result",
    "engineering_authority",
    "evidence_refs",
)
TASK032_PROPERTY_SNAPSHOT_FIELDS: Final[tuple[str, ...]] = (
    "density_kg_m3",
    "dynamic_viscosity_pa_s",
    "thermal_conductivity_w_m_k",
    "specific_heat_capacity_j_kg_k",
    "bulk_temperature_k",
    "bulk_pressure_pa",
    "phase_region",
    "property_source_id",
    "property_source_version",
    "property_snapshot_hash",
)
TASK032_MASS_FLOW_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "authority_profile_id",
    "shell_side_case_id",
    "shell_side_stream_id",
    "shell_side_fluid_id",
    "rheology_model",
    "task020_configuration_id",
    "task020_configuration_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "property_snapshot_hash",
    "property_state_role",
    "mass_flow_rate_kg_s",
    "mass_flow_sign_convention",
    "authority_source_id",
    "authority_source_version",
    "evidence_refs",
    "authority_hash",
)

SUCCESS_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "demo_id",
    "release_version",
    "source_commit",
    "source_tree",
    "task031_status",
    "task032_status",
    "task033_status",
    "task034_status",
    "task035_status",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task035_request_hash",
    "task035_result_hash",
    "task035_result_id",
    "release_acceptance_ledger",
    "upstream_evidence_ledger",
    "determinism_evidence",
    "artifact_manifest_digest",
    "version_metadata_digest",
    "acceptance_checklist",
    "provenance",
    "request_hash",
    "result_hash",
    "result_id",
    "warnings",
    "blockers",
    "deferred_capabilities",
)
SUCCESS_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "demo_id",
    "release_version",
    "source_commit",
    "source_tree",
    "task031_status",
    "task032_status",
    "task033_status",
    "task034_status",
    "task035_status",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task035_request_hash",
    "task035_result_hash",
    "task035_result_id",
    "upstream_evidence_ledger",
    "request_hash",
    "warnings",
    "blockers",
    "deferred_capabilities",
)
SUCCESS_RESULT_LATE_BOUND_FIELDS: Final[tuple[str, ...]] = (
    "release_acceptance_ledger",
    "determinism_evidence",
    "artifact_manifest_digest",
    "version_metadata_digest",
    "acceptance_checklist",
    "provenance",
)
SUCCESS_RESULT_EXCLUDED_FROM_PREHASH: Final[tuple[str, ...]] = (
    *SUCCESS_RESULT_LATE_BOUND_FIELDS,
    "result_hash",
    "result_id",
)

TYPED_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "demo_id",
    "release_version",
    "failure_stage",
    "source_commit",
    "source_tree",
    "task031_status",
    "task032_status",
    "task033_status",
    "task034_status",
    "task035_status",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task035_request_hash",
    "task035_result_hash",
    "task035_result_id",
    "request_hash",
    "blocked_result_hash",
    "result_id",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "upstream_evidence",
    "provenance",
)
TYPED_BLOCKED_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field
    for field in TYPED_BLOCKED_RESULT_FIELDS
    if field not in {"blocked_result_hash", "result_id"}
)
RAW_BOUNDARY_BLOCKED_RESULT_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "implementation_software_version",
    "raw_request_projection",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
)
RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in RAW_BOUNDARY_BLOCKED_RESULT_FIELDS if field != "blocked_result_hash"
)

RELEASE_ACCEPTANCE_LEDGER_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "ledger_id",
    "release_version",
    "demo_id",
    "source_commit",
    "source_tree",
    "required_available_capabilities",
    "unavailable_capabilities",
    "required_producer_statuses",
    "required_producer_identities",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task035_request_hash",
    "task035_result_hash",
    "task035_result_id",
    "upstream_evidence_refs",
    "artifact_manifest_digest",
    "determinism_evidence_digest",
    "acceptance_checklist_digest",
    "acceptance_status",
    "ledger_hash",
)
RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in RELEASE_ACCEPTANCE_LEDGER_FIELDS if field != "ledger_hash"
)

UPSTREAM_EVIDENCE_LEDGER_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "ledger_id",
    "source_definition_issue",
    "source_definition_revision",
    "source_definition_freeze_comment_id",
    "task031_producer_ref",
    "task032_producer_ref",
    "task033_producer_ref",
    "task034_producer_ref",
    "task035_pr",
    "task035_delivery_commit",
    "task035_merge_commit",
    "task035_tree",
    "task031_review_evidence",
    "task032_review_evidence",
    "task033_review_evidence",
    "task034_review_evidence",
    "task035_review_evidence",
    "task031_test_evidence",
    "task032_test_evidence",
    "task033_test_evidence",
    "task034_test_evidence",
    "task035_test_evidence",
    "task035_determinism_evidence",
    "historical_task035_evidence",
    "ledger_hash",
)
UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in UPSTREAM_EVIDENCE_LEDGER_FIELDS if field != "ledger_hash"
)

ACCEPTANCE_CHECKLIST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "checklist_id",
    "release_version",
    "success_demo_id",
    "required_available_capabilities",
    "unavailable_capabilities",
    "required_test_ids",
    "required_artifact_paths",
    "required_python_versions",
    "required_repeat_runs",
    "upstream_identity_status",
    "release_acceptance_status",
    "checklist_status",
    "checklist_hash",
)
ACCEPTANCE_CHECKLIST_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in ACCEPTANCE_CHECKLIST_FIELDS if field != "checklist_hash"
)

MANIFEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "manifest_id",
    "release_version",
    "source_commit",
    "source_tree",
    "artifact_inventory",
    "artifact_digest_set",
    "python_versions",
    "repeat_run_count",
    "upstream_evidence_ledger_ref",
    "release_acceptance_ledger_ref",
    "acceptance_checklist_ref",
    "manifest_hash",
)
MANIFEST_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in MANIFEST_FIELDS if field != "manifest_hash"
)

VERSION_METADATA_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "metadata_id",
    "release_version",
    "release_candidate_id",
    "software_version",
    "source_commit",
    "source_tree",
    "task031_authority_ref",
    "task032_authority_ref",
    "task033_authority_ref",
    "task034_authority_ref",
    "task035_authority_ref",
    "manifest_digest",
    "artifact_digest_set",
    "release_acceptance_result_id",
    "semantic_identity_version",
    "metadata_hash",
)
VERSION_METADATA_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in VERSION_METADATA_FIELDS if field != "metadata_hash"
)

PROVENANCE_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "task_id",
    "profile_id",
    "demo_id",
    "task031_request_hash",
    "task031_geometry_id",
    "task031_geometry_hash",
    "task032_request_hash",
    "task032_result_hash",
    "task032_result_id",
    "task033_request_hash",
    "task033_result_hash",
    "task033_result_id",
    "task034_request_hash",
    "task034_result_hash",
    "task034_result_id",
    "task035_request_hash",
    "task035_result_hash",
    "task035_result_id",
    "producer_edges",
    "release_evidence_ledger_hash",
    "artifact_manifest_digest",
    "acceptance_checklist_digest",
    "source_commit",
    "source_tree",
    "provenance_hash",
)
PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in PROVENANCE_FIELDS if field != "provenance_hash"
)

DETERMINISM_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "evidence_id",
    "input_hash",
    "runtime_versions",
    "repeat_run_count",
    "compared_surfaces",
    "compared_digests",
    "compared_result_ids",
    "byte_identity_status",
    "repeat_identity_status",
    "excluded_operational_fields",
    "evidence_hash",
)
DETERMINISM_EVIDENCE_PREHASH_FIELDS: Final[tuple[str, ...]] = tuple(
    field for field in DETERMINISM_EVIDENCE_FIELDS if field != "evidence_hash"
)

HASHED_CONTRACTS: Final[tuple[tuple[str, str, str, tuple[str, ...], str], ...]] = (
    (
        "H01_DEMO_INPUT",
        "task036.demo-input.v1",
        "TASK036_DEMO_INPUT",
        DEMO_INPUT_FIELDS,
        "request_hash",
    ),
    (
        "H02_SUCCESS_RESULT",
        "task036.success-result.v1",
        "TASK036_SUCCESS_RESULT",
        SUCCESS_RESULT_PREHASH_FIELDS,
        "result_hash",
    ),
    (
        "H03_TYPED_BLOCKED_RESULT",
        "task036.typed-blocked-result.v1",
        "TASK036_TYPED_BLOCKED_RESULT",
        TYPED_BLOCKED_RESULT_PREHASH_FIELDS,
        "blocked_result_hash",
    ),
    (
        "H04_RAW_BOUNDARY_BLOCKED_RESULT",
        "task036.raw-boundary-blocked-result.v1",
        "TASK036_RAW_BOUNDARY_BLOCKED_RESULT",
        RAW_BOUNDARY_BLOCKED_RESULT_PREHASH_FIELDS,
        "blocked_result_hash",
    ),
    (
        "H05_RELEASE_ACCEPTANCE_LEDGER",
        "task036.release-acceptance-ledger.v1",
        "TASK036_RELEASE_ACCEPTANCE_LEDGER",
        RELEASE_ACCEPTANCE_LEDGER_PREHASH_FIELDS,
        "ledger_hash",
    ),
    (
        "H06_UPSTREAM_EVIDENCE_LEDGER",
        "task036.upstream-evidence-ledger.v1",
        "TASK036_UPSTREAM_EVIDENCE_LEDGER",
        UPSTREAM_EVIDENCE_LEDGER_PREHASH_FIELDS,
        "ledger_hash",
    ),
    (
        "H07_ACCEPTANCE_CHECKLIST",
        "task036.acceptance-checklist.v1",
        "TASK036_ACCEPTANCE_CHECKLIST",
        ACCEPTANCE_CHECKLIST_PREHASH_FIELDS,
        "checklist_hash",
    ),
    (
        "H08_PROVENANCE",
        "task036.provenance.v1",
        "TASK036_PROVENANCE",
        PROVENANCE_PREHASH_FIELDS,
        "provenance_hash",
    ),
    (
        "H09_MANIFEST",
        "task036.manifest.v1",
        "TASK036_MANIFEST",
        MANIFEST_PREHASH_FIELDS,
        "manifest_hash",
    ),
    (
        "H10_VERSION_METADATA",
        "task036.version-metadata.v1",
        "TASK036_VERSION_METADATA",
        VERSION_METADATA_PREHASH_FIELDS,
        "metadata_hash",
    ),
    (
        "H11_DETERMINISM_EVIDENCE",
        "task036.determinism-evidence.v1",
        "TASK036_DETERMINISM_EVIDENCE",
        DETERMINISM_EVIDENCE_PREHASH_FIELDS,
        "evidence_hash",
    ),
)

HASHED_CONTRACT_COUNT: Final = 11
HASHED_CONTRACT_WITH_KIND_TAG_COUNT: Final = 11
RESULT_ID_NAMESPACE: Final = "97db5e70-af4c-58e1-8bf0-d16005aedf12"
RESULT_ID_PREFIX: Final = (
    "task036-shell-side-thermal-hydraulic-integration-release-acceptance-id.v1:"
)
SUCCESS_RESULT_KIND_TAG: Final = "TASK036_SUCCESS_RESULT"
TYPED_BLOCKED_RESULT_KIND_TAG: Final = "TASK036_TYPED_BLOCKED_RESULT"
RAW_BOUNDARY_RESULT_ID_PRESENT: Final = False

STAGE_ORDER: Final[tuple[str, ...]] = (
    "S00_RAW_DEMO_INPUT_VALIDATION",
    "S01_PARSE_AND_NORMALIZE_FROZEN_INPUTS",
    "S02_BUILD_TASK031_PUBLIC_REQUEST",
    "S03_EXECUTE_TASK031_PUBLIC_OPERATION",
    "S04_BUILD_TASK032_PUBLIC_REQUEST",
    "S05_EXECUTE_TASK032_PUBLIC_OPERATION",
    "S06_BUILD_TASK033_PUBLIC_REQUEST",
    "S07_EXECUTE_TASK033_PUBLIC_OPERATION",
    "S08_BUILD_TASK034_PUBLIC_REQUEST",
    "S09_EXECUTE_TASK034_PUBLIC_OPERATION",
    "S10_BUILD_TASK035_V2_PUBLIC_REQUEST",
    "S11_EXECUTE_TASK035_V2_VALIDATE_REQUEST",
    "S12_VALIDATE_RELEASE_PRODUCTION_GRAPH",
    "S13_AGGREGATE_UPSTREAM_EVIDENCE_AND_BLOCKED_CASES",
    "S14_BUILD_RELEASE_INPUT_BUNDLE",
    "S15_BUILD_TASK036_SUCCESS_IDENTITY_CORE",
    "S16_VALIDATE_DETERMINISM_SURFACES",
    "S17_BUILD_ACCEPTANCE_CHECKLIST",
    "S18_BUILD_ARTIFACT_MANIFEST",
    "S19_BUILD_RELEASE_ACCEPTANCE_LEDGER",
    "S20_BUILD_PROVENANCE",
    "S21_BUILD_VERSION_METADATA",
    "S22_FINALIZE_AND_VALIDATE_TASK036_RESULT_IDENTITY",
)
CORRECTED_RUNTIME_STAGE_COUNT: Final = 23

IDENTITY_NODES: Final[tuple[str, ...]] = (
    "N00_RAW_DEMO_INPUT",
    "N01_DEMO_INPUT",
    "N02_TASK031_RESULT",
    "N03_TASK032_RESULT",
    "N04_TASK033_RESULT",
    "N05_TASK034_RESULT",
    "N06_TASK035_RESULT",
    "N07_PRODUCTION_GRAPH_EVIDENCE",
    "N08_UPSTREAM_EVIDENCE_LEDGER",
    "N09_BLOCKED_CASES_EVIDENCE",
    "N10_RELEASE_INPUT_BUNDLE",
    "N11_SUCCESS_IDENTITY_CORE",
    "N12_CROSS_RUNTIME_DETERMINISM",
    "N13_REPEAT_RUN_DETERMINISM",
    "N14_ACCEPTANCE_CHECKLIST",
    "N15_MANIFEST",
    "N16_RELEASE_ACCEPTANCE_LEDGER",
    "N17_PROVENANCE",
    "N18_VERSION_METADATA",
    "N19_FINAL_ACCEPTANCE_RESULT",
)

# The complete 56-edge frozen identity/dataflow graph.
DATAFLOW_EDGES: Final[tuple[tuple[str, str], ...]] = (
    ("N00_RAW_DEMO_INPUT", "N01_DEMO_INPUT"),
    ("N01_DEMO_INPUT", "N02_TASK031_RESULT"),
    ("N01_DEMO_INPUT", "N03_TASK032_RESULT"),
    ("N02_TASK031_RESULT", "N03_TASK032_RESULT"),
    ("N03_TASK032_RESULT", "N04_TASK033_RESULT"),
    ("N04_TASK033_RESULT", "N05_TASK034_RESULT"),
    ("N05_TASK034_RESULT", "N06_TASK035_RESULT"),
    ("N06_TASK035_RESULT", "N07_PRODUCTION_GRAPH_EVIDENCE"),
    ("N07_PRODUCTION_GRAPH_EVIDENCE", "N08_UPSTREAM_EVIDENCE_LEDGER"),
    ("N07_PRODUCTION_GRAPH_EVIDENCE", "N09_BLOCKED_CASES_EVIDENCE"),
    ("N06_TASK035_RESULT", "N08_UPSTREAM_EVIDENCE_LEDGER"),
    ("N06_TASK035_RESULT", "N09_BLOCKED_CASES_EVIDENCE"),
    ("N06_TASK035_RESULT", "N10_RELEASE_INPUT_BUNDLE"),
    ("N07_PRODUCTION_GRAPH_EVIDENCE", "N10_RELEASE_INPUT_BUNDLE"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N10_RELEASE_INPUT_BUNDLE"),
    ("N09_BLOCKED_CASES_EVIDENCE", "N10_RELEASE_INPUT_BUNDLE"),
    ("N10_RELEASE_INPUT_BUNDLE", "N11_SUCCESS_IDENTITY_CORE"),
    ("N06_TASK035_RESULT", "N11_SUCCESS_IDENTITY_CORE"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N11_SUCCESS_IDENTITY_CORE"),
    ("N11_SUCCESS_IDENTITY_CORE", "N12_CROSS_RUNTIME_DETERMINISM"),
    ("N11_SUCCESS_IDENTITY_CORE", "N13_REPEAT_RUN_DETERMINISM"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N14_ACCEPTANCE_CHECKLIST"),
    ("N09_BLOCKED_CASES_EVIDENCE", "N14_ACCEPTANCE_CHECKLIST"),
    ("N11_SUCCESS_IDENTITY_CORE", "N14_ACCEPTANCE_CHECKLIST"),
    ("N12_CROSS_RUNTIME_DETERMINISM", "N14_ACCEPTANCE_CHECKLIST"),
    ("N13_REPEAT_RUN_DETERMINISM", "N14_ACCEPTANCE_CHECKLIST"),
    ("N01_DEMO_INPUT", "N15_MANIFEST"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N15_MANIFEST"),
    ("N09_BLOCKED_CASES_EVIDENCE", "N15_MANIFEST"),
    ("N11_SUCCESS_IDENTITY_CORE", "N15_MANIFEST"),
    ("N12_CROSS_RUNTIME_DETERMINISM", "N15_MANIFEST"),
    ("N13_REPEAT_RUN_DETERMINISM", "N15_MANIFEST"),
    ("N14_ACCEPTANCE_CHECKLIST", "N15_MANIFEST"),
    ("N15_MANIFEST", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N11_SUCCESS_IDENTITY_CORE", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N12_CROSS_RUNTIME_DETERMINISM", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N13_REPEAT_RUN_DETERMINISM", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N14_ACCEPTANCE_CHECKLIST", "N16_RELEASE_ACCEPTANCE_LEDGER"),
    ("N15_MANIFEST", "N17_PROVENANCE"),
    ("N16_RELEASE_ACCEPTANCE_LEDGER", "N17_PROVENANCE"),
    ("N14_ACCEPTANCE_CHECKLIST", "N17_PROVENANCE"),
    ("N06_TASK035_RESULT", "N17_PROVENANCE"),
    ("N11_SUCCESS_IDENTITY_CORE", "N17_PROVENANCE"),
    ("N15_MANIFEST", "N18_VERSION_METADATA"),
    ("N16_RELEASE_ACCEPTANCE_LEDGER", "N18_VERSION_METADATA"),
    ("N17_PROVENANCE", "N18_VERSION_METADATA"),
    ("N16_RELEASE_ACCEPTANCE_LEDGER", "N18_VERSION_METADATA"),
    ("N18_VERSION_METADATA", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N17_PROVENANCE", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N16_RELEASE_ACCEPTANCE_LEDGER", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N15_MANIFEST", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N14_ACCEPTANCE_CHECKLIST", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N12_CROSS_RUNTIME_DETERMINISM", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N13_REPEAT_RUN_DETERMINISM", "N19_FINAL_ACCEPTANCE_RESULT"),
    ("N08_UPSTREAM_EVIDENCE_LEDGER", "N19_FINAL_ACCEPTANCE_RESULT"),
)
IDENTITY_EDGES: Final = DATAFLOW_EDGES
STAGE_DATAFLOW_EDGE_COUNT: Final = 56

PROVENANCE_NODES: Final[tuple[str, ...]] = (
    "TASK031",
    "TASK032",
    "TASK033",
    "TASK034",
    "TASK035",
    "TASK036_RELEASE_EVIDENCE",
    "TASK036_ACCEPTANCE_RESULT",
)
PROVENANCE_EDGES: Final[tuple[tuple[str, str], ...]] = (
    ("TASK031", "TASK032"),
    ("TASK032", "TASK033"),
    ("TASK033", "TASK034"),
    ("TASK034", "TASK035"),
    ("TASK035", "TASK036_RELEASE_EVIDENCE"),
    ("TASK036_RELEASE_EVIDENCE", "TASK036_ACCEPTANCE_RESULT"),
)

ARTIFACT_IDS: Final[tuple[str, ...]] = (
    "TASK036_RELEASE_RUNNER",
    "TASK036_RELEASE_TEST_MODULE",
    "TASK036_DEMO_JSON",
    "TASK036_DEMO_MARKDOWN",
    "TASK036_RELEASE_MANIFEST_JSON",
    "TASK036_RELEASE_ACCEPTANCE_MARKDOWN",
)
ARTIFACT_PATHS: Final[tuple[str, ...]] = (
    "scripts/release_demo/v0_3_task020_to_task035.py",
    "tests/release_demo/test_v0_3_task020_to_task035.py",
    "release_evidence/v0.3.0/task020-to-task035-demo.json",
    "release_evidence/v0.3.0/task020-to-task035-demo.md",
    "release_evidence/v0.3.0/release-manifest.json",
    "release_evidence/v0.3.0/release-acceptance.md",
)
ARTIFACT_COUNT: Final = 6
MANIFEST_PEER_PATHS: Final[tuple[str, ...]] = (
    "release_evidence/v0.3.0/task020-to-task035-demo.json",
    "release_evidence/v0.3.0/task020-to-task035-demo.md",
    "release_evidence/v0.3.0/release-acceptance.md",
)
MANIFEST_DIGEST_SERIALIZATION_PATHS: Final[tuple[str, ...]] = tuple(sorted(MANIFEST_PEER_PATHS))

TEST_IDS: Final[tuple[str, ...]] = (
    "T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS",
    "T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS",
    "T036_CHAIN_003_TASK035_PUBLIC_BOUNDARY_ONLY",
    "T036_CHAIN_004_V02_TUBE_SIDE_RELEASE_AUTHORITY_INHERITED",
    "T036_BLOCK_001_TASK031_FAIL_CLOSED",
    "T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH",
    "T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE",
    "T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE",
    "T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH",
    "T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION",
    "T036_EVID_001_JSON_SCHEMA",
    "T036_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER",
    "T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER",
    "T036_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY",
    "T036_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY",
    "T036_DET_003_PY311_PY312_JSON_BYTE_IDENTITY",
    "T036_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY",
    "T036_META_001_PYPROJECT_VERSION_0_3_0",
    "T036_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT",
    "T036_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES",
    "T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE",
    "T036_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION",
)
TEST_ID_COUNT: Final = 22
TEST_PATH: Final = "tests/release_demo/test_v0_3_task020_to_task035.py"

AVAILABLE_CAPABILITIES: Final[tuple[str, ...]] = (
    "TUBE_SIDE_SINGLE_PHASE_HTC",
    "TUBE_SIDE_MODELED_PRESSURE_DROP",
    "SHELL_SIDE_HYDRAULIC_GEOMETRY",
    "SHELL_SIDE_SINGLE_PHASE_FLOW_STATE",
    "SHELL_SIDE_SINGLE_PHASE_HTC_SCREENING",
    "SHELL_SIDE_MODELED_DP_SCREENING",
    "SHELL_SIDE_THERMAL_HYDRAULIC_COMPOSITION",
    "SHELL_SIDE_APPLICABILITY_LEDGER",
    "SHELL_SIDE_COMPLETENESS_LEDGER",
)
UNAVAILABLE_CAPABILITIES: Final[tuple[str, ...]] = (
    "BELL_DELAWARE",
    "OVERALL_U",
    "UA",
    "LMTD",
    "HEAT_DUTY",
    "OUTLET_TEMPERATURES",
    "FULL_EXCHANGER_RATING",
)

BLOCKER_CODES: Final[tuple[str, ...]] = (
    "SSHG_SCHEMA_VERSION_UNSUPPORTED",
    "SSFS_TASK031_GEOMETRY_MISSING",
    "SSHT_TASK032_FLOW_STATE_INVALID",
    "SSPD_UNSUPPORTED_SHELL_PASS_COUNT",
    "SSTHC_TASK034_IDENTITY_MISMATCH",
    "SSTHC_RAW_TYPE_INVALID",
    "ST036_DEMO_INPUT_SCHEMA_INVALID",
    "ST036_DEMO_INPUT_CANONICALIZATION_FAILED",
    "ST036_PUBLIC_GRAPH_INVALID",
    "ST036_REQUIRED_UPSTREAM_EVIDENCE_MISSING",
    "ST036_UPSTREAM_EVIDENCE_IDENTITY_MISMATCH",
    "ST036_RELEASE_ACCEPTANCE_LEDGER_INVALID",
    "ST036_ARTIFACT_DIGEST_MISMATCH",
    "ST036_MANIFEST_INCOMPLETE",
    "ST036_VERSION_METADATA_INVALID",
    "ST036_PROVENANCE_DAG_INVALID",
    "ST036_DETERMINISM_EVIDENCE_MISSING",
    "ST036_CROSS_VERSION_BYTES_MISMATCH",
    "ST036_RESULT_CANONICALIZATION_FAILED",
    "ST036_RESULT_IDENTITY_FINALIZATION_FAILED",
    "ST036_RELEASE_CHECKLIST_INCOMPLETE",
    "ST036_RELEASE_ACCEPTANCE_INCOMPLETE",
)
BLOCKER_REGISTRY_COUNT: Final = 22

PYTHON_VERSIONS: Final[tuple[str, ...]] = ("3.11", "3.12")
DETERMINISM_SURFACE_IDS: Final[tuple[str, ...]] = (
    "DS01",
    "DS02",
    "DS03",
    "DS04",
    "DS05",
    "DS06",
    "DS07",
)
DETERMINISM_SURFACES: Final[tuple[str, ...]] = (
    "task020_to_task035_demo_json_bytes",
    "release_manifest_json_bytes",
    "task020_to_task035_demo_markdown_bytes",
    "release_acceptance_markdown_bytes",
    "TASK036_final_result_canonical_bytes",
    "TASK036_final_result_hash",
    "TASK036_internal_result_id",
)
DETERMINISM_SURFACE_COUNT: Final = 7
REMOVED_DETERMINISM_SURFACES: Final[tuple[str, ...]] = (
    "DS02 task035_request_canonical_bytes",
    "DS03 task035_success_canonical_bytes",
)

SOURCE_DECISION_COUNT: Final = 35
NO_NEW_PHYSICS: Final = True
NO_RECOMPUTATION_OF_UPSTREAM_ENGINEERING: Final = True
ACTUAL_PRODUCTION_BINDINGS_ONLY: Final = True
FIXTURE_ONLY_RESULT_SUBSTITUTION: Final = False
EXPECTED_OUTPUT_USED_AS_INPUT: Final = False
SYNTHETIC_ORACLE_SUBSTITUTION: Final = False
RELEASE_ACCEPTANCE_IS_NOT_ENGINEERING_CORRECTNESS_PROOF: Final = True
RELEASE_EVIDENCE_IDENTITY_CONTRACT: Final = "NON_RESULT_AGGREGATION_EDGE"
RELEASE_ACCEPTANCE_RESULT_ID_DETERMINISM_REQUIRED: Final = False

IMPLEMENTATION_PRODUCTION_FILE_ALLOWLIST: Final[tuple[str, ...]] = (
    "src/hexagent/release_demo/__init__.py",
    "src/hexagent/release_demo/task036.py",
    "src/hexagent/release_demo/schema.py",
    "src/hexagent/release_demo/canonical.py",
    "src/hexagent/release_demo/models.py",
    "src/hexagent/release_demo/validation.py",
    "src/hexagent/release_demo/provenance.py",
    "src/hexagent/release_demo/artifacts.py",
    "pyproject.toml",
    "uv.lock",
)
IMPLEMENTATION_TEST_FILE_ALLOWLIST: Final[tuple[str, ...]] = (TEST_PATH,)
IMPLEMENTATION_ARTIFACT_FILE_ALLOWLIST: Final[tuple[str, ...]] = ARTIFACT_PATHS
IMPLEMENTATION_CI_ALLOWLIST: Final[tuple[str, ...]] = ("ci-shard-manifest.yml",)
