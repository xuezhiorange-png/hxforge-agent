"""Closed TASK039 R4 implementation constants and ordered contracts."""

from __future__ import annotations

from decimal import Decimal
from typing import Final

TASK_ID: Final = "TASK039"
PROFILE_ID: Final = "hxforge.release_demo.v0_4"
RELEASE_EVIDENCE_SCHEMA_VERSION: Final = "task039.release-demo.v1"
RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION: Final = "task039.release-acceptance-result.v1"
PROVENANCE_SCHEMA_VERSION: Final = "task039.release-provenance.v1"
PRODUCTION_GRAPH_SCHEMA_VERSION: Final = "task039.production-graph-evidence.v1"
SUCCESS_DEMO_SCHEMA_VERSION: Final = "task039.success-demo-evidence.v1"
BLOCKED_DEMO_SCHEMA_VERSION: Final = "task039.blocked-demo-evidence.v1"
HISTORICAL_AUTHORITY_SCHEMA_VERSION: Final = "task039.historical-release-authority.v1"
VERSION_METADATA_SCHEMA_VERSION: Final = "task039.version-metadata.v1"
DETERMINISM_SCHEMA_VERSION: Final = "task039.determinism-evidence.v1"
ACCEPTANCE_ITEM_SCHEMA_VERSION: Final = "task039.release-acceptance-item.v1"
ACCEPTANCE_LEDGER_SCHEMA_VERSION: Final = "task039.release-acceptance-ledger.v1"
MANIFEST_SCHEMA_VERSION: Final = "task039.release-manifest.v1"

DESIGN_ISSUE: Final = 215
DESIGN_REVISION: Final = "R4_FINAL_FROZEN"
RUNTIME_DESIGN_AUTHORITY_TOKEN: Final = DESIGN_REVISION
SOURCE_DEFINITION_ISSUE: Final = 214
SOURCE_DEFINITION_REVISION: Final = "R2_FROZEN"
ALLOCATION_ISSUE: Final = 207
ALLOCATION_REVISION: Final = "R3_FROZEN"
BASE_MAIN_SHA: Final = "ba6d29b5af70dc9c2cdd0832ae0d8de2bb2ea09e"
BASE_MAIN_TREE: Final = "ec07e31eec7d4d377ae0fdcfa9633190ad0ae060"

RELEASE_VERSION: Final = "0.4.0"
IMPLEMENTATION_SOFTWARE_VERSION: Final = "task039.release-acceptance-impl-v1"
RELEASE_CANDIDATE_ID: Final = "TASK039-V04-RC1"
RELEASE_SOFTWARE_VERSION: Final = "task039.overall-heat-transfer-conductance-release-acceptance-v1"

UUID_NAMESPACE: Final = "a0390000-0000-5000-8000-000000000039"
UUID_NAME_PREFIX: Final = "task039-release-acceptance-v1::"
RESULT_NAMESPACE: Final = "task039.release-acceptance-result.v1"
PROVENANCE_NAMESPACE: Final = PROVENANCE_SCHEMA_VERSION
RELEASE_ACCEPTANCE_RESULT_NAMESPACE: Final = RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION
PRODUCER_IDENTITY_NAMESPACE: Final = "task039.producer-identity.v1"
PRODUCER_IDENTITY_SCHEMA_VERSION: Final = PRODUCER_IDENTITY_NAMESPACE
CAPABILITY_BOUNDARY_NAMESPACE: Final = "task039.capability-boundary.v1"
CAPABILITY_BOUNDARY_SCHEMA_VERSION: Final = CAPABILITY_BOUNDARY_NAMESPACE
BLOCKER_ENTRY_NAMESPACE: Final = "task039.blocker-entry.v1"
WARNING_ENTRY_NAMESPACE: Final = "task039.warning-entry.v1"

V03_TAG: Final = "v0.3.0"
V03_TAG_TARGET_COMMIT: Final = "47a8c848e5054cce75092de728317ca55248fde6"
V03_GITHUB_RELEASE_ID: Final = 378603109
V03_GITHUB_RELEASE_NAME: Final = "HXForge v0.3.0"
V03_RELEASE_ACCEPTANCE_ITEM_COUNT: Final = 22
V03_MANIFEST_HASH: Final = "4838501d76dcee1c6d14371462b9634f55ae12e51daa4cef445cff365b14ac92"

ARTIFACT_IDS: Final[tuple[str, ...]] = ("A01", "A02", "A03", "A04", "A05", "A06")
ARTIFACT_PATHS: Final[tuple[str, ...]] = (
    "scripts/release_demo/v0_4_task020_to_task038.py",
    "tests/release_demo/test_v0_4_task020_to_task038.py",
    "release_evidence/v0.4.0/task020-to-task038-demo.json",
    "release_evidence/v0.4.0/task020-to-task038-demo.md",
    "release_evidence/v0.4.0/release-manifest.json",
    "release_evidence/v0.4.0/release-acceptance.md",
)
MANIFEST_DIGEST_PATHS: Final[tuple[str, ...]] = ARTIFACT_PATHS[:4]
ARTIFACT_INVENTORY_COUNT: Final = 6

IMPLEMENTATION_ALLOWLIST: Final[tuple[str, ...]] = (
    "src/hexagent/release_demo/v0_4/__init__.py",
    "src/hexagent/release_demo/v0_4/schema.py",
    "src/hexagent/release_demo/v0_4/models.py",
    "src/hexagent/release_demo/v0_4/canonical.py",
    "src/hexagent/release_demo/v0_4/provenance.py",
    "src/hexagent/release_demo/v0_4/validation.py",
    "src/hexagent/release_demo/v0_4/task039.py",
    "src/hexagent/release_demo/v0_4/artifacts.py",
    "scripts/release_demo/v0_4_task020_to_task038.py",
    "tests/release_demo/test_v0_4_task020_to_task038.py",
    "tests/release_demo/test_v0_3_task020_to_task035.py",
    "release_evidence/v0.4.0/task020-to-task038-demo.json",
    "release_evidence/v0.4.0/task020-to-task038-demo.md",
    "release_evidence/v0.4.0/release-manifest.json",
    "release_evidence/v0.4.0/release-acceptance.md",
    "pyproject.toml",
    "uv.lock",
    "ci-shard-manifest.yml",
)

TEST_IDS: Final[tuple[str, ...]] = (
    "T039_CHAIN_001_ACTUAL_TASK020_TO_TASK038_PRODUCTION_DAG_SUCCESS",
    "T039_CHAIN_002_TASK025_TASK026_TASK035_TASK037_TASK038_SAME_REPLAY_BINDINGS",
    "T039_CHAIN_003_TASK038_PUBLIC_BOUNDARY_ONLY",
    "T039_CHAIN_004_V03_RELEASE_AUTHORITY_INHERITED",
    "T039_CHAIN_005_TASK037_SURFACE_WALL_FOULING_AUTHORITY_SURFACED",
    "T039_CHAIN_006_TASK038_FULL_RESISTANCE_OVERALL_U_AREA_UA_SURFACED",
    "T039_BLOCK_001_TASK025_RESULT_REPLAY_INVALID",
    "T039_BLOCK_002_TASK026_RESULT_REPLAY_INVALID",
    "T039_BLOCK_003_TASK035_RESULT_REPLAY_INVALID",
    "T039_BLOCK_004_TASK037_RESULT_REPLAY_INVALID",
    "T039_BLOCK_005_TASK038_CROSS_PRODUCER_JOIN_MISMATCH",
    "T039_BLOCK_006_TASK038_SERVICE_BINDING_INVALID",
    "T039_BLOCK_007_TASK038_RAW_BOUNDARY_MALFORMED",
    "T039_BLOCK_008_V03_HISTORICAL_AUTHORITY_MISMATCH",
    "T039_BLOCK_009_V04_VERSION_METADATA_MISMATCH",
    "T039_BLOCK_010_V04_ARTIFACT_DIGEST_MISMATCH",
    "T039_EVID_001_JSON_SCHEMA_AND_FIELD_ORDER",
    "T039_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER",
    "T039_EVID_003_ARTIFACT_PATHS_AND_AUTHORITY_LEDGERS",
    "T039_EVID_004_SURFACE_WALL_FOULING_RESISTANCE_U_AREA_UA_EVIDENCE",
    "T039_DET_001_REPEAT_RUN_JSON_AND_RESULT_BYTE_IDENTITY",
    "T039_DET_002_REPEAT_RUN_MARKDOWN_ACCEPTANCE_AND_MANIFEST_BYTE_IDENTITY",
    "T039_DET_003_PY311_PY312_JSON_RESULT_BYTE_IDENTITY",
    "T039_DET_004_PY311_PY312_MARKDOWN_ACCEPTANCE_MANIFEST_BYTE_IDENTITY",
    "T039_META_001_PYPROJECT_VERSION_0_4_0",
    "T039_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT",
    "T039_META_003_HISTORICAL_V03_VERSION_AUTHORITY_ISOLATED",
    "T039_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES",
    "T039_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE",
    "T039_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION",
)
TASK039_ACCEPTANCE_ITEM_COUNT: Final = 30
TASK039_AUTHORITATIVE_TEST_FUNCTION_COUNT: Final = 30

DEMO_SUCCESS_ID: Final = "DEMO_SUCCESS_001"
BLOCKED_DEMO_IDS: Final[tuple[str, ...]] = tuple(f"DEMO_BLOCKED_B{i:02d}" for i in range(1, 11))
PYTHON_VERSIONS: Final[tuple[str, ...]] = ("3.11", "3.12")
REPEAT_RUN_COUNT: Final = 2

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
    "TASK037_SURFACE_WALL_FOULING_RESISTANCE",
    "TASK038_FULL_RESISTANCE_OVERALL_U_AREA_UA",
    "OVERALL_U",
    "OUTER_TUBE_SURFACE_EFFECTIVE_AREA",
    "UA",
)
UNAVAILABLE_CAPABILITIES: Final[tuple[str, ...]] = (
    "LMTD",
    "LMTD_CORRECTION_FACTOR",
    "EFFECTIVENESS_NTU",
    "HEAT_DUTY",
    "OUTLET_TEMPERATURES",
    "ENERGY_BALANCE_ITERATION",
    "THERMAL_RATING_ITERATION",
    "WALL_TEMPERATURE_ITERATION",
    "AUTOMATIC_WALL_VISCOSITY_ITERATION",
    "FULL_EXCHANGER_THERMAL_RATING",
    "THERMAL_SIZING",
    "GEOMETRY_OPTIMIZATION",
    "BELL_DELAWARE",
    "SHELL_TO_BAFFLE_LEAKAGE_CORRECTION",
    "TUBE_TO_BAFFLE_LEAKAGE_CORRECTION",
    "BUNDLE_BYPASS_CORRECTION",
    "UNEQUAL_BAFFLE_SPACING_CORRECTION",
    "TWO_PHASE_HEAT_TRANSFER",
    "TWO_PHASE_PRESSURE_DROP",
    "COMPRESSIBLE_PATH_INTEGRATION",
    "FLOW_INDUCED_VIBRATION",
    "NOZZLE_SIZING",
    "MECHANICAL_ADEQUACY",
    "MATERIAL_SELECTION",
    "COST_OPTIMIZATION",
    "PUBLIC_API_EXTENSION",
    "PERSISTENCE_EXTENSION",
    "UI",
    "REPORTING",
)
DEFERRED_CAPABILITIES: Final = UNAVAILABLE_CAPABILITIES
V0_4_TERMINAL_ENGINEERING_CAPABILITY: Final = "UA"
OVERALL_U_REFERENCE_SURFACE: Final = "OUTER_TUBE_SURFACE"
OUTER_TUBE_SURFACE_EFFECTIVE_AREA_AVAILABLE: Final = True
OVERALL_U_AVAILABLE: Final = True
UA_AVAILABLE: Final = True
TASK038_FULL_RESISTANCE_OVERALL_U_AREA_UA_AVAILABLE: Final = True

STAGE_ORDER: Final[tuple[str, ...]] = (
    "S00_RAW_INPUT_BOUNDARY",
    "S01_REQUEST_AND_AUTHORITY_SCHEMA",
    "S02_TASK025_RESULT_REPLAY",
    "S03_TASK026_RESULT_REPLAY",
    "S04_TASK035_RESULT_REPLAY",
    "S05_TASK037_RESULT_REPLAY",
    "S06_HYDRAULIC_AND_TASK025_JOIN",
    "S07_TASK021_TASK020_ANCESTRY_JOIN",
    "S08_REFERENCE_SURFACE_JOIN",
    "S09_TUBE_SIDE_SERVICE_BINDING",
    "S10_SHELL_SIDE_SERVICE_AND_FOULING_BINDING",
    "S11_OVERALL_U_APPLICABILITY_INTERSECTION",
    "S12_FULL_RESISTANCE_COMPOSITION",
    "S13_OVERALL_U_PUBLIC_QUANTIZATION",
    "S14_OUTER_AREA_AUTHORITY_AND_TRANSFORM",
    "S15_OUTER_AREA_PUBLIC_QUANTIZATION",
    "S16_UA_COMPOSITION_AND_PUBLIC_QUANTIZATION",
    "S17_APPLICABILITY_COMPLETENESS_FINALIZATION",
    "S18_PROVENANCE_CANONICALIZATION",
    "S19_RESULT_HASH_UUID_FINALIZATION",
)

BLOCKER_MATRIX: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("B01", "BL_TASK025_RESULT_INVALID", "S02_TASK025_RESULT_REPLAY", "task025_result"),
    ("B02", "BL_TASK026_RESULT_INVALID", "S03_TASK026_RESULT_REPLAY", "task026_result"),
    ("B03", "BL_TASK035_RESULT_INVALID", "S04_TASK035_RESULT_REPLAY", "task035_result"),
    ("B04", "BL_TASK037_RESULT_INVALID", "S05_TASK037_RESULT_REPLAY", "task037_result"),
    (
        "B05",
        "BL_HYDRAULIC_AUTHORITY_MISMATCH",
        "S06_HYDRAULIC_AND_TASK025_JOIN",
        "cross_producer",
    ),
    (
        "B06",
        "BL_SERVICE_BINDING_INVALID",
        "S01_REQUEST_AND_AUTHORITY_SCHEMA",
        "tube_side_service_binding_authority",
    ),
    ("B07", "BL_RAW_INPUT_BOUNDARY_MALFORMED", "S00_RAW_INPUT_BOUNDARY", "raw_input"),
    (
        "B08",
        "T039_HISTORICAL_RELEASE_AUTHORITY_MISMATCH",
        "R10",
        "historical_release_authority.v03_tag_target_commit",
    ),
    ("B09", "T039_VERSION_METADATA_MISMATCH", "R20", "version_metadata.pyproject_version"),
    ("B10", "T039_RELEASE_ARTIFACT_DIGEST_MISMATCH", "R40", "artifact_digests.A03"),
)

PROVENANCE_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "source_definition_issue",
    "source_definition_revision",
    "allocation_issue",
    "allocation_revision",
    "base_main_sha",
    "base_main_tree",
    "unauthorized_mutation_commit",
    "repair_commit",
    "task038_merge_commit",
    "task038_post_merge_main_ci_run",
    "v03_tag",
    "v03_tag_target_commit",
    "v03_github_release_id",
    "v03_manifest_hash",
    "release_version",
    "production_graph_hash",
    "success_demo_hash",
    "blocked_demo_hashes",
    "artifact_manifest_hash",
    "acceptance_checklist_hash",
    "evidence_refs",
)
PROVENANCE_FULL_FIELDS: Final[tuple[str, ...]] = (*PROVENANCE_PREHASH_FIELDS, "provenance_hash")
PROVENANCE_PREHASH_FIELD_COUNT: Final = 22
PROVENANCE_FULL_FIELD_COUNT: Final = 23
PROVENANCE_HASH_APPEND_COUNT: Final = 1
PROVENANCE_EDGE_COUNT: Final = 13
PROVENANCE_EDGES: Final[tuple[tuple[str, str, str], ...]] = (
    ("TASK020", "TASK021", "configuration_identity"),
    ("TASK021", "TASK025", "layout_identity"),
    ("TASK021", "TASK031", "layout_identity"),
    ("TASK025", "TASK026", "task025_result_identity"),
    ("TASK025", "TASK037", "task025_result_identity"),
    ("TASK031", "TASK032", "geometry_result"),
    ("TASK032", "TASK033", "flow_state_result"),
    ("TASK033", "TASK034", "heat_transfer_result"),
    ("TASK034", "TASK035", "pressure_drop_result"),
    ("TASK026", "TASK038", "task026_result_identity"),
    ("TASK035", "TASK038", "task035_result_identity"),
    ("TASK037", "TASK038", "task037_result_identity"),
    ("TASK038", "TASK039", "task038_result_identity"),
)
SELF_EDGE_COUNT: Final = 0

RESULT_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "profile_id",
    "release_version",
    "source_definition_issue",
    "source_definition_revision",
    "allocation_issue",
    "allocation_revision",
    "base_main_sha",
    "base_main_tree",
    "task038_merge_commit",
    "task038_post_merge_main_ci_run",
    "historical_release_authority",
    "production_graph_hash",
    "success_demo_hash",
    "blocked_demo_hashes",
    "artifact_manifest_hash",
    "version_metadata_hash",
    "determinism_evidence_hash",
    "acceptance_checklist_hash",
    "release_acceptance_ledger",
    "warnings",
    "blockers",
    "provenance",
)
RESULT_PREHASH_FIELD_COUNT: Final = 23

ACCEPTANCE_CHECKLIST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "checklist_id",
    "release_version",
    "required_test_ids",
    "required_artifact_paths",
    "required_python_versions",
    "repeat_run_count",
    "checklist_status",
    "checklist_hash",
)
ACCEPTANCE_LEDGER_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "checklist_id",
    "item_count",
    "pass_count",
    "items",
    "aggregate_status",
)
MANIFEST_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "manifest_id",
    "release_version",
    "artifact_inventory",
    "artifact_digest_set",
    "python_versions",
    "repeat_run_count",
    "upstream_evidence_ledger_ref",
    "release_acceptance_ledger_ref",
    "acceptance_checklist_ref",
    "manifest_hash",
)
# Backward-compatible name for the operational A05 JSON field order.  The
# frozen identity projection is declared below as MANIFEST_PREHASH_FIELDS.
MANIFEST_RUNTIME_FIELDS: Final[tuple[str, ...]] = MANIFEST_FIELDS

PRODUCTION_GRAPH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "stages",
    "actual_public_operations",
    "statuses",
    "producer_identity_bindings",
    "fixture_only_result_substitution",
    "expected_output_used_as_input",
    "synthetic_oracle_substitution",
    "private_helper_stage_bypass",
    "no_upstream_engineering_recomputation",
    "pressure_drop_forwarded_unchanged",
)
SUCCESS_DEMO_FIELDS: Final[tuple[str, ...]] = (
    "demo_id",
    "status",
    "task038_result_hash",
    "task038_result_id",
    "modeled_overall_heat_transfer_coefficient_w_m2_k",
    "outer_tube_surface_effective_area_m2",
    "modeled_ua_w_k",
)
BLOCKED_DEMO_FIELDS: Final[tuple[str, ...]] = (
    "demo_id",
    "test_id",
    "stage",
    "status",
    "public_operation",
    "blocker_code",
    "blocker_field_path",
    "blocked_result_hash",
    "partial_result_present",
    "success_result_present",
    "numeric_result_fields_present",
    "downstream_success_execution_absent",
)
HISTORICAL_AUTHORITY_FIELDS: Final[tuple[str, ...]] = (
    "tag",
    "target_commit",
    "github_release_id",
    "manifest_hash",
    "release_version",
    "acceptance_status",
)
VERSION_METADATA_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "metadata_id",
    "release_version",
    "pyproject_version",
    "uv_lock_project_version",
    "dependency_graph_change_authorized",
    "transitive_dependency_version_change_authorized",
)
DETERMINISM_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "evidence_id",
    "python_versions",
    "repeat_run_count",
    "compared_surfaces",
    "compared_digests",
    "result_hash",
    "result_id",
    "byte_identity_status",
)
ACCEPTANCE_ITEM_FIELDS: Final[tuple[str, ...]] = (
    "test_id",
    "category",
    "status",
    "evidence_refs",
    "failure_meaning",
)
BLOCKER_ENTRY_FIELDS: Final[tuple[str, ...]] = (
    "code",
    "stage",
    "field_path",
    "reason",
    "producer_or_owner",
)
WARNING_ENTRY_FIELDS: Final[tuple[str, ...]] = ("code", "stage", "field_path")

# Closed identity projections.  These tuples are the implementation-facing
# counterpart of the R4 field/kind tables; the order is authoritative.
PRODUCER_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "task_id",
    "result_hash",
    "result_id",
    "status",
    "source_revision",
)
CAPABILITY_BOUNDARY_FIELDS: Final[tuple[str, ...]] = (
    "capability_id",
    "availability",
    "authority",
    "reason",
)
PRODUCTION_GRAPH_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "stage_ids",
    "stage_count",
    "edge_count",
    "public_operation_refs",
    "producer_result_identities",
    "same_replay_bindings",
    "blocked_propagation_rule",
)
SUCCESS_DEMO_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "demo_id",
    "status",
    "input_hash",
    "stage_ids",
    "producer_result_ids",
    "task037_result_hash",
    "task038_result_hash",
    "task039_result_hash",
    "task039_result_id",
    "evidence_refs",
    "capability_boundary",
)
BLOCKED_DEMO_EVIDENCE_FIELDS: Final[tuple[str, ...]] = (
    "demo_id",
    "status",
    "source_object",
    "mutation_operation",
    "blocker_code",
    "blocker_stage",
    "blocker_field_path",
    "producer_or_owner",
    "precedence_rank",
    "evidence_refs",
    "capability_boundary",
)
VERSION_METADATA_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "release_version",
    "pyproject_version",
    "uv_lock_project_version",
    "dependency_graph_hash",
)
DETERMINISM_EVIDENCE_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "repeat_run_count",
    "python_versions",
    "artifact_paths",
    "canonical_byte_hashes",
    "result_hash",
    "result_id",
)
ACCEPTANCE_TEST_ID_INVENTORY_FIELDS: Final[tuple[str, ...]] = ("test_ids",)
ARTIFACT_INVENTORY_FIELDS: Final[tuple[str, ...]] = ("artifacts",)

# The release-manifest document contains a richer operational projection for
# A01-A04 digests.  Its identity projection is kept separate so no digest
# field can form a self- or A06-dependent cycle.
MANIFEST_PREHASH_FIELDS: Final[tuple[str, ...]] = (
    "schema_version",
    "release_version",
    "artifact_inventory",
    "digested_peer_artifacts",
    "self_digest_entry",
    "digest_algorithm",
    "exact_byte_digest",
)
MANIFEST_POSTHASH_METADATA_FIELDS: Final[tuple[str, ...]] = (
    "manifest_hash",
    "acceptance_ref",
)
MANIFEST_IDENTITY_PREHASH_FIELD_COUNT: Final = 7
MANIFEST_POSTHASH_METADATA_FIELD_COUNT: Final = 2
MANIFEST_SELF_DIGEST_ENTRY: Final = False
A05_SELF_DIGEST_ENTRY: Final = False
A05_DIGESTS_A06: Final = False
POST_MANIFEST_ACCEPTANCE_CONSUMER: Final = "A06"
MANIFEST_ACCEPTANCE_DIGEST_CYCLE: Final = False

# Public service-binding oracle from TASK038 R4.
SERVICE_BINDING_REPLAY_FIXTURE_BYTES: Final = 826
SERVICE_BINDING_REPLAY_FIXTURE_SHA256: Final = (
    "1be4944c645ad5da0bbf01c741e121ae7105e7f086e7f5bb3a033e51af216043"
)
SERVICE_BINDING_STRING_FIELDS: Final[tuple[str, ...]] = (
    "authority_id",
    "tube_side_fluid_service_id",
    "task026_result_hash",
    "task026_property_snapshot_hash",
    "source_id",
    "source_version",
    "source_location",
)
SERVICE_BINDING_ENUM_FIELDS: Final[tuple[str, ...]] = (
    "source_class",
    "permission_status",
    "approval_status",
)
SERVICE_BINDING_TUPLE_FIELDS: Final[tuple[str, ...]] = ("evidence_refs",)

PRODUCTION_GRAPH_HASH_FIXTURE: Final = "a" * 64
BLOCKED_DEMO_HASH_FIXTURE: Final = "c" * 64
BLOCKED_DEMO_HASH_VECTOR: Final[tuple[str, ...]] = (BLOCKED_DEMO_HASH_FIXTURE,) * 10

PROVENANCE_STATIC_CANONICAL_BYTES: Final = 2459
PROVENANCE_HASH: Final = "abbbcb574f11f2d5481f75cacb2aa017cc6987c4c6e0ba0332a132d3d45088dd"
PROVENANCE_FULL_CANONICAL_BYTES: Final = 2560
PROVENANCE_FULL_CANONICAL_SHA256: Final = (
    "51d3b6a849a0110c430ee49bd3cebee4dce1e74454c44c0e77afa092520ca268"
)
FINAL_RESULT_VECTOR_A_CANONICAL_BYTES: Final = 14746
FINAL_RESULT_VECTOR_A_SHA256: Final = (
    "5981db415cca97e51961789fb710f21605dacf3f5ef85c4caa74ad85bc2d42d9"
)
FINAL_RESULT_VECTOR_A_UUID5: Final = "65bef913-efd1-5ffa-9eb5-afc7dbc1b7bc"
FINAL_RESULT_VECTOR_B_CANONICAL_BYTES: Final = 14746
FINAL_RESULT_VECTOR_B_SHA256: Final = (
    "0e19eedb15ac2f1402b09b9d4a3809abe468f004d56770ee261a4527c077fcc8"
)
FINAL_RESULT_VECTOR_B_UUID5: Final = "c0beadbe-e5e1-59cd-8b3a-59fa282ce702"
FINAL_RESULT_VECTOR_DELTA_FIELD: Final = "determinism_evidence_hash"

TASK025_AREA_QUANTUM_M2: Final = Decimal("1E-10")
TASK025_AREA_ROUNDING_MODE: Final = "ROUND_HALF_EVEN"
TASK025_PRODUCER_AREA_PRECISION_POLICY_ID: Final = (
    "task037.task025-public-area-authority.accept-positive-v1"
)
TASK025_PRODUCER_AREA_PRECISION_POLICY_HASH: Final = (
    "e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5e5"
)

DESIGN_DECISION_COUNT: Final = 60
DESIGN_RESOLVED_COUNT: Final = 60
DESIGN_UNRESOLVED_COUNT: Final = 0
CI_SHARD_MANIFEST_BASELINE_REGISTERED_FILE_COUNT: Final = 238
CI_SHARD_MANIFEST_TARGET_REGISTERED_FILE_COUNT: Final = 239

__all__ = [name for name in globals() if name.isupper()]
