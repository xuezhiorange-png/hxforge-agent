"""Authoritative TASK039 v0.4 release-acceptance tests."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.canonical import (
    service_binding_bytes,
    service_binding_hash,
)
from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.models import (
    TubeSideServiceBindingAuthority,
)
from hexagent.release_demo.v0_4.artifacts import exact_file_digest
from hexagent.release_demo.v0_4.canonical import (
    ACCEPTANCE_LEDGER_SPEC,
    acceptance_checklist_hash,
    frame_value,
    manifest_hash,
    provenance_full_bytes,
    provenance_hash,
    provenance_prehash_bytes,
    record_bytes,
    record_spec,
    result_canonical_bytes,
    result_hash,
    result_id,
    sha256_bytes,
    tuple_spec,
)
from hexagent.release_demo.v0_4.provenance import build_provenance, verify_provenance
from hexagent.release_demo.v0_4.schema import (
    ARTIFACT_IDS,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    BLOCKED_DEMO_HASH_VECTOR,
    BLOCKED_DEMO_IDS,
    BLOCKER_MATRIX,
    DESIGN_ISSUE,
    DESIGN_REVISION,
    FINAL_RESULT_VECTOR_A_CANONICAL_BYTES,
    FINAL_RESULT_VECTOR_A_SHA256,
    FINAL_RESULT_VECTOR_A_UUID5,
    FINAL_RESULT_VECTOR_B_CANONICAL_BYTES,
    FINAL_RESULT_VECTOR_B_SHA256,
    FINAL_RESULT_VECTOR_B_UUID5,
    IMPLEMENTATION_ALLOWLIST,
    MANIFEST_DIGEST_PATHS,
    MANIFEST_FIELDS,
    PRODUCTION_GRAPH_HASH_FIXTURE,
    PROVENANCE_FULL_CANONICAL_BYTES,
    PROVENANCE_FULL_CANONICAL_SHA256,
    PROVENANCE_FULL_FIELDS,
    PROVENANCE_HASH,
    PROVENANCE_PREHASH_FIELDS,
    PROVENANCE_STATIC_CANONICAL_BYTES,
    RELEASE_VERSION,
    RESULT_PREHASH_FIELDS,
    SERVICE_BINDING_REPLAY_FIXTURE_BYTES,
    SERVICE_BINDING_REPLAY_FIXTURE_SHA256,
    TASK039_ACCEPTANCE_ITEM_COUNT,
    TEST_IDS,
    UNAVAILABLE_CAPABILITIES,
)
from hexagent.release_demo.v0_4.task039 import build_release_run

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_JSON_PATH = REPO_ROOT / "release_evidence/v0.4.0/task020-to-task038-demo.json"
DEMO_MARKDOWN_PATH = REPO_ROOT / "release_evidence/v0.4.0/task020-to-task038-demo.md"
MANIFEST_PATH = REPO_ROOT / "release_evidence/v0.4.0/release-manifest.json"
ACCEPTANCE_PATH = REPO_ROOT / "release_evidence/v0.4.0/release-acceptance.md"


@pytest.fixture(scope="module")
def run() -> Any:
    return build_release_run()


def _blocked(run: Any, index: int) -> dict[str, Any]:
    return run.blocked_demos[index]


def _expected_blocker(run: Any, index: int) -> None:
    record = _blocked(run, index)
    _, code, stage, field_path = BLOCKER_MATRIX[index]
    assert record["demo_id"] == BLOCKED_DEMO_IDS[index]
    assert record["test_id"] == TEST_IDS[6 + index]
    assert record["status"] == "BLOCKED"
    assert record["blocker_code"] == code
    assert record["stage"] == stage
    assert record["field_path"] == field_path
    assert record["partial_result_present"] is False
    assert record["success_result_present"] is False
    assert record["numeric_result_fields_present"] is False
    assert record["downstream_success_execution_absent"] is True


def _design_service_binding() -> TubeSideServiceBindingAuthority:
    return TubeSideServiceBindingAuthority(
        "TSBA-039-RELEASE-001",
        "TUBE-WATER-001",
        "0" * 64,
        "1" * 64,
        "T039-TUBE-SERVICE-BINDING-SOURCE",
        "R2",
        "ISSUE_214/R2/SUCCESS_VECTOR/TUBE_SERVICE_BINDING",
        "APPROVED_ENGINEERING_BASIS",
        "INTERNAL_USE_AUTHORIZED",
        "APPROVED",
        ("T039-EV-TUBE-SERVICE-BINDING-001",),
        "0" * 64,
    )


def _design_provenance_fixture() -> dict[str, Any]:
    return build_provenance(
        {
            "task_id": "TASK039",
            "source_definition_issue": 214,
            "source_definition_revision": "R2_FROZEN",
            "allocation_issue": 207,
            "allocation_revision": "R3_FROZEN",
            "base_main_sha": "ba6d29b5af70dc9c2cdd0832ae0d8de2bb2ea09e",
            "base_main_tree": "ec07e31eec7d4d377ae0fdcfa9633190ad0ae060",
            "unauthorized_mutation_commit": "292deab4c9f4462296549deca4b6f9727fb3da63",
            "repair_commit": "ba6d29b5af70dc9c2cdd0832ae0d8de2bb2ea09e",
            "task038_merge_commit": "0d65380e05c0000237ef862640687c94ecc21bb1",
            "task038_post_merge_main_ci_run": "33371394290",
            "v03_tag": "v0.3.0",
            "v03_tag_target_commit": "47a8c848e5054cce75092de728317ca55248fde6",
            "v03_github_release_id": 378603109,
            "v03_manifest_hash": "4838501d76dcee1c6d14371462b9634f55ae12e51daa4cef445cff365b14ac92",
            "release_version": "0.4.0",
            "production_graph_hash": PRODUCTION_GRAPH_HASH_FIXTURE,
            "success_demo_hash": "b" * 64,
            "blocked_demo_hashes": BLOCKED_DEMO_HASH_VECTOR,
            "artifact_manifest_hash": "d" * 64,
            "acceptance_checklist_hash": "e" * 64,
            "evidence_refs": ("ISSUE-214-R2", "ISSUE-207-R3", "TASK038-PR-213"),
        }
    )


def _design_acceptance_ledger() -> dict[str, Any]:
    items = tuple(
        {
            "test_id": test_id,
            "category": test_id.split("_", 2)[1],
            "status": "PASS",
            "evidence_refs": ("A06",),
            "failure_meaning": "none",
        }
        for test_id in TEST_IDS
    )
    return {
        "schema_version": "task039.release-acceptance-ledger.v1",
        "checklist_id": "TASK039-CHECKLIST-0.4.0",
        "item_count": 30,
        "pass_count": 30,
        "items": items,
        "aggregate_status": "PASS",
    }


def _design_result_fixture(determinism_evidence_hash: str) -> dict[str, Any]:
    return {
        "schema_version": "task039.release-acceptance-result.v1",
        "profile_id": "hxforge.release_demo.v0_4",
        "release_version": "0.4.0",
        "source_definition_issue": 214,
        "source_definition_revision": "R2_FROZEN",
        "allocation_issue": 207,
        "allocation_revision": "R3_FROZEN",
        "base_main_sha": "ba6d29b5af70dc9c2cdd0832ae0d8de2bb2ea09e",
        "base_main_tree": "ec07e31eec7d4d377ae0fdcfa9633190ad0ae060",
        "task038_merge_commit": "0d65380e05c0000237ef862640687c94ecc21bb1",
        "task038_post_merge_main_ci_run": "33371394290",
        "historical_release_authority": {
            "tag": "v0.3.0",
            "target_commit": "47a8c848e5054cce75092de728317ca55248fde6",
            "github_release_id": 378603109,
            "manifest_hash": "4838501d76dcee1c6d14371462b9634f55ae12e51daa4cef445cff365b14ac92",
            "release_version": "0.3.0",
            "acceptance_status": "PASS",
        },
        "production_graph_hash": PRODUCTION_GRAPH_HASH_FIXTURE,
        "success_demo_hash": "b" * 64,
        "blocked_demo_hashes": BLOCKED_DEMO_HASH_VECTOR,
        "artifact_manifest_hash": "d" * 64,
        "version_metadata_hash": "e" * 64,
        "determinism_evidence_hash": determinism_evidence_hash,
        "acceptance_checklist_hash": "0" * 64,
        "release_acceptance_ledger": _design_acceptance_ledger(),
        "warnings": (),
        "blockers": (),
        "provenance": _design_provenance_fixture(),
    }


def test_t039_chain_001_actual_task020_to_task038_production_dag_success(run: Any) -> None:
    expected_tasks = (
        "TASK020",
        "TASK021",
        "TASK025",
        "TASK026",
        "TASK031",
        "TASK032",
        "TASK033",
        "TASK034",
        "TASK035",
        "TASK037",
        "TASK038",
        "TASK039",
    )
    assert tuple(run.production_graph["statuses"]) == expected_tasks
    assert all(value == "VALID" for value in run.production_graph["statuses"].values())
    assert result_hash(run.final_result) == run.final_result["result_hash"]
    assert result_id(run.final_result["result_hash"]) == run.final_result["result_id"]


def test_t039_chain_002_task025_task026_task035_task037_task038_same_replay_bindings(
    run: Any,
) -> None:
    identities = run.production_graph["producer_identity_bindings"]
    assert identities == [
        "replay_task025",
        "replay_task026",
        "replay_task035",
        "replay_task037",
    ]
    assert run.success_demo["task025_result_hash"] == run.task025_result.result_hash
    assert run.success_demo["task026_result_hash"] == run.task026_result.result_hash
    assert run.success_demo["task035_result_hash"] == run.task035_result.success_result.result_hash
    assert run.success_demo["task037_result_hash"] == run.task037_result.success_result.result_hash
    assert run.success_demo["task038_result_hash"] == run.task038_result.success_result.result_hash


def test_t039_chain_003_task038_public_boundary_only(run: Any) -> None:
    operations = run.production_graph["actual_public_operations"]
    assert len(operations) == 16
    assert operations[-4:-1] == [
        "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.build_raw_overall_u_ua_request",
        "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.evaluate_task038",
        "hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua.verify_task038_success_identity",
    ]
    assert operations[-1] == "hexagent.release_demo.v0_4.validate_request"
    assert run.production_graph["fixture_only_result_substitution"] is False
    assert run.production_graph["expected_output_used_as_input"] is False
    assert run.production_graph["private_helper_stage_bypass"] is False


def test_t039_chain_004_v03_release_authority_inherited(run: Any) -> None:
    historical = run.historical_release_authority
    assert historical["tag"] == "v0.3.0"
    assert historical["target_commit"] == "47a8c848e5054cce75092de728317ca55248fde6"
    assert historical["github_release_id"] == 378603109
    assert historical["release_version"] == "0.3.0"
    assert historical["acceptance_status"] == "PASS"
    assert historical["manifest_hash"] == (
        "4838501d76dcee1c6d14371462b9634f55ae12e51daa4cef445cff365b14ac92"
    )


def test_t039_chain_005_task037_surface_wall_fouling_authority_surfaced(run: Any) -> None:
    result = run.task037_result.success_result
    assert result is not None
    assert result.surface_transform_authority_hash
    assert result.wall_material_authority_hash
    assert result.wall_conductivity_authority_hash
    assert result.inside_fouling_authority is not None
    assert result.outside_fouling_authority is not None
    assert run.success_demo["task037_result_id"] == result.result_id


def test_t039_chain_006_task038_full_resistance_overall_u_area_ua_surfaced(run: Any) -> None:
    result = run.task038_result.success_result
    assert result is not None
    assert result.modeled_overall_heat_transfer_coefficient_w_m2_k > 0
    assert result.outer_tube_surface_effective_area_m2 > 0
    assert result.modeled_ua_w_k > 0
    assert run.success_demo["task038_result_id"] == result.result_id


def test_t039_block_001_task025_result_replay_invalid(run: Any) -> None:
    _expected_blocker(run, 0)


def test_t039_block_002_task026_result_replay_invalid(run: Any) -> None:
    _expected_blocker(run, 1)


def test_t039_block_003_task035_result_replay_invalid(run: Any) -> None:
    _expected_blocker(run, 2)


def test_t039_block_004_task037_result_replay_invalid(run: Any) -> None:
    _expected_blocker(run, 3)


def test_t039_block_005_task038_cross_producer_join_mismatch(run: Any) -> None:
    _expected_blocker(run, 4)


def test_t039_block_006_task038_service_binding_invalid(run: Any) -> None:
    _expected_blocker(run, 5)
    assert _blocked(run, 5)["blocker_code"] == "BL_SERVICE_BINDING_INVALID"


def test_t039_block_007_task038_raw_boundary_malformed(run: Any) -> None:
    _expected_blocker(run, 6)


def test_t039_block_008_v03_historical_authority_mismatch(run: Any) -> None:
    _expected_blocker(run, 7)
    assert _blocked(run, 7)["stage"] == "R10"


def test_t039_block_009_v04_version_metadata_mismatch(run: Any) -> None:
    _expected_blocker(run, 8)
    assert _blocked(run, 8)["stage"] == "R20"


def test_t039_block_010_v04_artifact_digest_mismatch(run: Any) -> None:
    _expected_blocker(run, 9)
    assert _blocked(run, 9)["stage"] == "R40"


def test_t039_evid_001_json_schema_and_field_order(run: Any) -> None:
    payload = json.loads(run.artifact_bytes[ARTIFACT_PATHS[2]])
    assert payload["schema_version"] == "task039.release-demo.v1"
    assert payload["release_version"] == RELEASE_VERSION
    assert tuple(run.manifest) == MANIFEST_FIELDS
    assert tuple(run.final_result) == (*RESULT_PREHASH_FIELDS, "result_hash", "result_id")
    assert tuple(run.provenance) == PROVENANCE_FULL_FIELDS

    frame_string_fixture = frame_value("hello", kind="STRING")
    frame_int_fixture = frame_value(-7, kind="INT")
    frame_decimal_fixture = frame_value(Decimal("1.2300"), kind="DECIMAL")
    nested_record = {"flag": True, "amount": Decimal("1.2300"), "items": ("A", "β")}
    nested_fields = ("flag", "amount", "items")
    nested_kinds = {
        "flag": "BOOL_TRUE",
        "amount": "DECIMAL",
        "items": tuple_spec("STRING"),
    }
    nested_payload = record_bytes(
        "task039.design-oracle.v1", nested_record, nested_fields, kinds=nested_kinds
    )
    nested_frame = frame_value(
        nested_record,
        kind=record_spec("task039.design-oracle.v1", nested_fields, nested_kinds),
    )
    assert len(frame_string_fixture) == 23
    assert sha256_bytes(frame_string_fixture) == (
        "c1194d7b9547ad44e527db08db15a61d2672e7f50b97efb0283e2aa723ba0c6a"
    )
    assert len(frame_int_fixture) == 17
    assert sha256_bytes(frame_int_fixture) == (
        "62625783247ebd2e82e4c8a97db55d9acdf5ea2a8b0e4d035bcc02c0b5dd1ab7"
    )
    assert len(frame_decimal_fixture) == 25
    assert sha256_bytes(frame_decimal_fixture) == (
        "27ec5fe20fb9f5cd9d0d7e80655e469999f635ad3ac0eec0053e94d763451640"
    )
    assert len(nested_payload) == 165
    assert sha256_bytes(nested_payload) == (
        "7bc788a7f37d9fd840ee61d2e2571a638fc8f0608a3bd53043b3a2f87cd89b43"
    )
    assert len(nested_frame) == 183
    assert sha256_bytes(nested_frame) == (
        "e65096e3937e9243da47b2d57224357593828560f1e5fa5700099ac54ad5b04b"
    )

    binding = _design_service_binding()
    assert len(service_binding_bytes(binding)) == 826
    assert service_binding_hash(binding) == (
        "1be4944c645ad5da0bbf01c741e121ae7105e7f086e7f5bb3a033e51af216043"
    )

    static_provenance = _design_provenance_fixture()
    assert len(provenance_prehash_bytes(static_provenance)) == 2459
    assert provenance_hash(static_provenance) == (
        "abbbcb574f11f2d5481f75cacb2aa017cc6987c4c6e0ba0332a132d3d45088dd"
    )
    assert len(provenance_full_bytes(static_provenance)) == 2560
    assert sha256_bytes(provenance_full_bytes(static_provenance)) == (
        "51d3b6a849a0110c430ee49bd3cebee4dce1e74454c44c0e77afa092520ca268"
    )

    result_a = _design_result_fixture("f" * 64)
    result_b = _design_result_fixture("0" * 64)
    result_a_bytes = result_canonical_bytes(result_a)
    result_b_bytes = result_canonical_bytes(result_b)
    assert len(result_a_bytes) == 14746
    assert len(result_b_bytes) == 14746
    assert result_hash(result_a) == FINAL_RESULT_VECTOR_A_SHA256
    assert result_hash(result_b) == FINAL_RESULT_VECTOR_B_SHA256
    assert result_id(result_hash(result_a)) == FINAL_RESULT_VECTOR_A_UUID5
    assert result_id(result_hash(result_b)) == FINAL_RESULT_VECTOR_B_UUID5
    assert result_a_bytes != result_b_bytes
    assert set(result_a) == set(result_b)
    assert [key for key in result_a if result_a[key] != result_b[key]] == [
        "determinism_evidence_hash"
    ]


def test_t039_evid_002_markdown_schema_and_section_order(run: Any) -> None:
    markdown = run.artifact_bytes[ARTIFACT_PATHS[3]].decode("utf-8")
    headings = [line[3:] for line in markdown.splitlines() if line.startswith("## ")]
    assert headings == [
        "Release Identity",
        "Production Graph",
        "Success Demonstration",
        "Blocked Demonstrations",
        "Capability Boundary",
        "Identity and Provenance",
        "Acceptance",
    ]
    assert run.artifact_bytes[ARTIFACT_PATHS[5]].startswith(b"# v0.4 Release Acceptance\n")


def test_t039_evid_003_artifact_paths_and_authority_ledgers(run: Any) -> None:
    assert tuple(item["artifact_id"] for item in run.manifest["artifact_inventory"]) == ARTIFACT_IDS
    assert tuple(item["path"] for item in run.manifest["artifact_inventory"]) == ARTIFACT_PATHS
    assert (
        tuple(item["path"] for item in run.manifest["artifact_digest_set"]) == MANIFEST_DIGEST_PATHS
    )
    assert run.provenance["source_definition_issue"] == 214
    assert run.provenance["source_definition_revision"] == "R2_FROZEN"
    assert run.provenance["allocation_issue"] == 207
    assert run.provenance["allocation_revision"] == "R3_FROZEN"

    test_id_inventory = record_bytes(
        "task039.acceptance-test-id-inventory.v1",
        {"test_ids": TEST_IDS},
        ("test_ids",),
        kinds={"test_ids": tuple_spec("STRING")},
    )
    allowlist_inventory = record_bytes(
        "task039.implementation-allowlist.v1",
        {"paths": IMPLEMENTATION_ALLOWLIST},
        ("paths",),
        kinds={"paths": tuple_spec("STRING")},
    )
    artifact_inventory = tuple(
        f"{artifact_id} {path}"
        for artifact_id, path in zip(ARTIFACT_IDS, ARTIFACT_PATHS, strict=True)
    )
    artifact_inventory_bytes = record_bytes(
        "task039.artifact-inventory.v1",
        {"artifacts": artifact_inventory},
        ("artifacts",),
        kinds={"artifacts": tuple_spec("STRING")},
    )
    assert len(test_id_inventory) == 2164
    assert sha256_bytes(test_id_inventory) == (
        "3cd586e749eaa7cc9f28b867844d4f8e66745dc69c80cf35ae62e881dc574cdc"
    )
    assert len(allowlist_inventory) == 1115
    assert sha256_bytes(allowlist_inventory) == (
        "46c9d577ffaae1f982b3945e17e71a2e590562c0fa817724b498d88888f64f8a"
    )
    assert len(artifact_inventory_bytes) == 492
    assert sha256_bytes(artifact_inventory_bytes) == (
        "0b6d740934cd0870ce672abe53bdd39ed96b854b454a526ecf954465925a5ffa"
    )
    ledger = _design_acceptance_ledger()
    ledger_bytes = record_bytes(
        ACCEPTANCE_LEDGER_SPEC.namespace or "task039.release-acceptance-ledger.v1",
        ledger,
        ACCEPTANCE_LEDGER_SPEC.fields,
        kinds=dict(ACCEPTANCE_LEDGER_SPEC.kinds),
    )
    assert len(ledger_bytes) == 9399
    assert sha256_bytes(ledger_bytes) == (
        "a3bbccde68e6433645ee8f5f70b24a71fc8a2a2b95cfa36688f53dd47a302500"
    )


def test_t039_evid_004_surface_wall_fouling_resistance_u_area_ua_evidence(run: Any) -> None:
    capability = json.loads(run.artifact_bytes[ARTIFACT_PATHS[2]])["capability_boundary"]
    assert capability["V0_4_TERMINAL_ENGINEERING_CAPABILITY"] == "UA"
    assert capability["OVERALL_U_AVAILABLE"] is True
    assert capability["UA_AVAILABLE"] is True
    assert "OVERALL_U" in capability["available"]
    assert "UA" in capability["available"]
    assert "OVERALL_U" in AVAILABLE_CAPABILITIES
    assert "UA" in AVAILABLE_CAPABILITIES
    assert "OVERALL_U" not in capability["intentionally_unavailable"]
    assert "UA" not in capability["intentionally_unavailable"]


def test_t039_det_001_repeat_run_json_and_result_byte_identity(run: Any) -> None:
    repeated = build_release_run()
    for path in ARTIFACT_PATHS[2:]:
        assert repeated.artifact_bytes[path] == run.artifact_bytes[path]
    assert result_canonical_bytes(repeated.final_result) == result_canonical_bytes(run.final_result)
    assert repeated.final_result["result_hash"] == run.final_result["result_hash"]
    assert repeated.final_result["result_id"] == run.final_result["result_id"]


def test_t039_det_002_repeat_run_markdown_acceptance_and_manifest_byte_identity(run: Any) -> None:
    repeated = build_release_run()
    assert repeated.artifact_bytes[ARTIFACT_PATHS[3]] == run.artifact_bytes[ARTIFACT_PATHS[3]]
    assert repeated.artifact_bytes[ARTIFACT_PATHS[4]] == run.artifact_bytes[ARTIFACT_PATHS[4]]
    assert repeated.artifact_bytes[ARTIFACT_PATHS[5]] == run.artifact_bytes[ARTIFACT_PATHS[5]]


def test_t039_det_003_py311_py312_json_result_byte_identity(run: Any) -> None:
    assert run.determinism_evidence["python_versions"] == ["3.11", "3.12"]
    assert run.determinism_evidence["repeat_run_count"] == 2
    assert run.determinism_evidence["byte_identity_status"] == "PASS"
    assert run.determinism_evidence["compared_surfaces"] == [
        "A03",
        "A04",
        "A05",
        "A06",
        "FINAL_RESULT",
    ]


def test_t039_det_004_py311_py312_markdown_acceptance_manifest_byte_identity(run: Any) -> None:
    digests = run.determinism_evidence["compared_digests"]
    assert digests["A03"] == exact_file_digest(run.artifact_bytes[ARTIFACT_PATHS[2]])
    assert digests["A04"] == exact_file_digest(run.artifact_bytes[ARTIFACT_PATHS[3]])
    assert digests["A05"] == exact_file_digest(run.artifact_bytes[ARTIFACT_PATHS[4]])
    assert digests["A06"] == exact_file_digest(run.artifact_bytes[ARTIFACT_PATHS[5]])


def test_t039_meta_001_pyproject_version_0_4_0(run: Any) -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.4.0"' in text
    assert run.version_metadata["pyproject_version"] == RELEASE_VERSION


def test_t039_meta_002_uv_lock_project_version_alignment(run: Any) -> None:
    text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "heat-exchanger-design-agent"' in text
    assert 'version = "0.4.0"' in text
    assert (
        run.version_metadata["uv_lock_project_version"] == run.version_metadata["pyproject_version"]
    )


def test_t039_meta_003_historical_v03_version_authority_isolated(run: Any) -> None:
    assert run.historical_release_authority["tag"] == "v0.3.0"
    assert run.historical_release_authority["release_version"] == "0.3.0"
    assert run.historical_release_authority["acceptance_status"] == "PASS"
    assert run.version_metadata["release_version"] == "0.4.0"


def test_t039_manifest_001_release_manifest_sha256_exact_bytes(run: Any) -> None:
    manifest = json.loads(run.artifact_bytes[ARTIFACT_PATHS[4]])
    assert manifest == run.manifest
    assert manifest["manifest_hash"] == manifest_hash(manifest)
    assert manifest["artifact_digest_set"]
    assert all(len(item["sha256"]) == 64 for item in manifest["artifact_digest_set"])


def test_t039_accept_001_acceptance_checklist_complete(run: Any) -> None:
    checklist = run.acceptance_checklist
    assert checklist["required_test_ids"] == list(TEST_IDS)
    assert len(checklist["required_test_ids"]) == TASK039_ACCEPTANCE_ITEM_COUNT == 30
    assert len(set(checklist["required_test_ids"])) == 30
    assert all(item["status"] == "PASS" for item in checklist["items"])
    assert checklist["checklist_hash"] == acceptance_checklist_hash(checklist)


def test_t039_accept_002_no_upstream_engineering_proof_substitution(run: Any) -> None:
    graph = run.production_graph
    assert graph["fixture_only_result_substitution"] is False
    assert graph["expected_output_used_as_input"] is False
    assert graph["synthetic_oracle_substitution"] is False
    assert graph["private_helper_stage_bypass"] is False
    assert graph["no_upstream_engineering_recomputation"] is True
    assert graph["pressure_drop_forwarded_unchanged"] is True
    assert "OVERALL_U" not in UNAVAILABLE_CAPABILITIES
    assert "UA" not in UNAVAILABLE_CAPABILITIES
    assert DESIGN_ISSUE == 215
    assert DESIGN_REVISION == "R4_FINAL_FROZEN"
    assert len(IMPLEMENTATION_ALLOWLIST) == 18
    assert verify_provenance(run.provenance)
    assert len(PROVENANCE_FULL_FIELDS) == 23
    assert provenance_hash(run.provenance) == run.provenance["provenance_hash"]
    assert len(provenance_full_bytes(run.provenance)) > 0
    assert len(PROVENANCE_PREHASH_FIELDS) == 22
    assert SERVICE_BINDING_REPLAY_FIXTURE_BYTES == 826
    assert len(SERVICE_BINDING_REPLAY_FIXTURE_SHA256) == 64
    assert run.final_result["result_hash"]
    assert run.final_result["result_id"]
    static_provenance = _design_provenance_fixture()
    assert len(provenance_prehash_bytes(static_provenance)) == PROVENANCE_STATIC_CANONICAL_BYTES
    assert provenance_hash(static_provenance) == PROVENANCE_HASH
    assert len(provenance_full_bytes(static_provenance)) == PROVENANCE_FULL_CANONICAL_BYTES
    assert (
        sha256_bytes(provenance_full_bytes(static_provenance)) == PROVENANCE_FULL_CANONICAL_SHA256
    )
    static_a = _design_result_fixture("f" * 64)
    static_b = _design_result_fixture("0" * 64)
    assert len(result_canonical_bytes(static_a)) == FINAL_RESULT_VECTOR_A_CANONICAL_BYTES
    assert len(result_canonical_bytes(static_b)) == FINAL_RESULT_VECTOR_B_CANONICAL_BYTES
    assert result_hash(static_a) == FINAL_RESULT_VECTOR_A_SHA256
    assert result_hash(static_b) == FINAL_RESULT_VECTOR_B_SHA256
    assert result_id(result_hash(static_a)) == FINAL_RESULT_VECTOR_A_UUID5
    assert result_id(result_hash(static_b)) == FINAL_RESULT_VECTOR_B_UUID5
