"""Frozen TASK036 v0.3 release-demo acceptance tests (D32, 22 IDs)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from hexagent.release_demo.artifacts import exact_file_digest
from hexagent.release_demo.canonical import (
    acceptance_checklist_hash,
    manifest_hash,
    success_result_canonical_bytes,
    success_result_hash,
)
from hexagent.release_demo.provenance import verify_provenance
from hexagent.release_demo.schema import (
    ARTIFACT_IDS,
    ARTIFACT_PATHS,
    AVAILABLE_CAPABILITIES,
    DETERMINISM_SURFACES,
    MANIFEST_DIGEST_SERIALIZATION_PATHS,
    MANIFEST_FIELDS,
    PROFILE_ID,
    SUCCESS_RESULT_FIELDS,
    SUCCESS_RESULT_PREHASH_FIELDS,
    TEST_IDS,
    UNAVAILABLE_CAPABILITIES,
)
from hexagent.release_demo.task036 import build_release_run
from hexagent.release_demo.validation import verify_stage_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
DEMO_JSON_PATH = REPO_ROOT / "release_evidence/v0.3.0/task020-to-task035-demo.json"
DEMO_MARKDOWN_PATH = REPO_ROOT / "release_evidence/v0.3.0/task020-to-task035-demo.md"
MANIFEST_PATH = REPO_ROOT / "release_evidence/v0.3.0/release-manifest.json"
ACCEPTANCE_PATH = REPO_ROOT / "release_evidence/v0.3.0/release-acceptance.md"


@pytest.fixture(scope="module")
def run() -> Any:
    return build_release_run()


def _blocked(run: Any, index: int) -> dict[str, Any]:
    return run.blocked_cases[index]


def _runtime_snapshot(executable: str) -> dict[str, str]:
    code = (
        "from hexagent.release_demo.task036 import build_release_run; "
        "from hexagent.release_demo.artifacts import exact_file_digest; "
        "from hexagent.release_demo.canonical import sha256_bytes, success_result_canonical_bytes; "
        "from hexagent.release_demo.schema import ARTIFACT_PATHS; "
        "r=build_release_run(); "
        "print('|'.join(["
        "exact_file_digest(r.artifact_bytes[ARTIFACT_PATHS[2]]),"
        " "
        "exact_file_digest(r.artifact_bytes[ARTIFACT_PATHS[4]]), "
        "exact_file_digest(r.artifact_bytes[ARTIFACT_PATHS[3]]), "
        "exact_file_digest(r.artifact_bytes[ARTIFACT_PATHS[5]]), "
        "sha256_bytes(success_result_canonical_bytes(r.final_result)), "
        "r.final_result['result_hash'], r.final_result['result_id']]))"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT / "src")
    output = subprocess.check_output(
        [
            "uv",
            "run",
            "--isolated",
            "--python",
            executable,
            "--with",
            "rfc8785",
            "python",
            "-c",
            code,
        ],
        cwd=REPO_ROOT,
        env=env,
        text=True,
    )
    values = output.strip().split("|")
    return {name: value for name, value in zip(DETERMINISM_SURFACES, values, strict=False)}


def _python_executable(major: int, minor: int) -> str | None:
    if sys.version_info[:2] == (major, minor):
        return sys.executable
    return shutil.which(f"python{major}.{minor}")


def _runtime_pair() -> tuple[str, str]:
    py311 = _python_executable(3, 11)
    py312 = _python_executable(3, 12)
    if py311 is None or py312 is None:
        pytest.skip("Python 3.11 and 3.12 are both required")
    return py311, py312


def test_T036_CHAIN_001_ACTUAL_SHELL_PRODUCTION_DAG_SUCCESS(run: Any) -> None:
    assert run.graph_evidence["statuses"] == {
        "TASK031": "VALID",
        "TASK032": "VALID",
        "TASK033": "VALID",
        "TASK034": "VALID",
        "TASK035": "VALID",
    }
    assert run.final_result["result_hash"] == success_result_hash(run.final_result)
    assert run.final_result["result_id"]


def test_T036_CHAIN_002_TASK031_TO_TASK035_SAME_REPLAY_BINDINGS(run: Any) -> None:
    identities = run.final_result["release_acceptance_ledger"]["required_producer_identities"]
    for key in (
        "TASK031_RESULT_HASH",
        "TASK032_RESULT_HASH",
        "TASK033_RESULT_HASH",
        "TASK034_RESULT_HASH",
        "TASK035_RESULT_HASH",
    ):
        assert identities[key]
    assert run.final_result["task034_result_hash"] == identities["TASK034_RESULT_HASH"]
    assert run.final_result["task035_result_id"] == identities["TASK035_RESULT_ID"]


def test_T036_CHAIN_003_TASK035_PUBLIC_BOUNDARY_ONLY(run: Any) -> None:
    graph = run.graph_evidence
    assert len(graph["actual_public_operations"]) == 5
    assert graph["private_helper_bypass"] is False
    assert graph["fixture_only_result_substitution"] is False
    assert graph["expected_output_used_as_input"] is False


def test_T036_CHAIN_004_V02_TUBE_SIDE_RELEASE_AUTHORITY_INHERITED(run: Any) -> None:
    ledger = run.upstream_evidence_ledger
    assert ledger["task035_pr"] == "PR#205"
    assert ledger["task035_delivery_commit"] == "e48d83208bfe4de782ee055a99c826fb9eebb334"
    assert ledger["historical_task035_evidence"].startswith("HISTORICAL_")


def test_T036_BLOCK_001_TASK031_FAIL_CLOSED(run: Any) -> None:
    assert _blocked(run, 0)["status"] == "BLOCKED"
    assert _blocked(run, 0)["blocker_code"] == "SSHG_SCHEMA_VERSION_UNSUPPORTED"


def test_T036_BLOCK_002_TASK032_UPSTREAM_MISMATCH(run: Any) -> None:
    assert _blocked(run, 1)["status"] == "BLOCKED"
    assert _blocked(run, 1)["blocker_code"] == "SSFS_TASK031_GEOMETRY_MISSING"


def test_T036_BLOCK_003_TASK033_BLOCKED_OR_INAPPLICABLE(run: Any) -> None:
    assert _blocked(run, 2)["status"] == "BLOCKED"
    assert _blocked(run, 2)["blocker_code"] == "SSHT_TASK032_FLOW_STATE_INVALID"


def test_T036_BLOCK_004_TASK034_BLOCKED_OR_INAPPLICABLE(run: Any) -> None:
    assert _blocked(run, 3)["status"] == "BLOCKED"
    assert _blocked(run, 3)["blocker_code"] == "SSPD_UNSUPPORTED_SHELL_PASS_COUNT"
    assert _blocked(run, 3)["identity_repaired"] is False


def test_T036_BLOCK_005_TASK035_CROSS_PRODUCER_IDENTITY_MISMATCH(run: Any) -> None:
    blocked = _blocked(run, 4)
    assert blocked["status"] == "BLOCKED"
    assert blocked["blocker_code"] == "SSTHC_TASK034_IDENTITY_MISMATCH"
    assert len(blocked["blocker_field_paths"]) == 12
    assert blocked["identity_repaired"] is False


def test_T036_BLOCK_006_TASK035_RAW_BOUNDARY_REJECTION(run: Any) -> None:
    assert _blocked(run, 5)["status"] == "BLOCKED"
    assert _blocked(run, 5)["blocker_code"] == "SSTHC_RAW_TYPE_INVALID"


def test_T036_EVID_001_JSON_SCHEMA(run: Any) -> None:
    payload = json.loads(DEMO_JSON_PATH.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "task036.shell-side-thermal-hydraulic-integration-demo.v1"
    assert payload["profile_id"] == PROFILE_ID
    assert payload["success_demo"]["status"] == "VALID"
    assert tuple(run.final_result) == SUCCESS_RESULT_FIELDS
    assert len(SUCCESS_RESULT_PREHASH_FIELDS) == 23


def test_T036_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER(run: Any) -> None:
    markdown = DEMO_MARKDOWN_PATH.read_text(encoding="utf-8")
    acceptance = ACCEPTANCE_PATH.read_text(encoding="utf-8")
    headings = [line[3:] for line in markdown.splitlines() if line.startswith("## ")]
    assert headings == [
        "Release Identity",
        "Production Graph",
        "Success Demonstration",
        "Blocked Demonstrations",
        "Producer Identity Bindings",
        "Capability Boundary",
    ]
    assert acceptance.startswith("# v0.3 Release Acceptance\n")
    assert "## Acceptance Checklist" in acceptance


def test_T036_EVID_003_ARTIFACT_PATHS_AND_UPSTREAM_AUTHORITY_LEDGER(run: Any) -> None:
    assert tuple(run.manifest) == MANIFEST_FIELDS
    assert tuple(item["path"] for item in run.manifest["artifact_inventory"]) == ARTIFACT_PATHS
    assert (
        tuple(item["path"] for item in run.manifest["artifact_digest_set"])
        == MANIFEST_DIGEST_SERIALIZATION_PATHS
    )
    assert len(ARTIFACT_IDS) == 6
    assert run.upstream_evidence_ledger["source_definition_issue"] == "203"
    assert run.upstream_evidence_ledger["source_definition_revision"] == "R5"


def test_T036_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY(run: Any) -> None:
    repeated = build_release_run()
    assert repeated.artifact_bytes[ARTIFACT_PATHS[2]] == run.artifact_bytes[ARTIFACT_PATHS[2]]
    assert repeated.artifact_bytes[ARTIFACT_PATHS[4]] == run.artifact_bytes[ARTIFACT_PATHS[4]]
    assert success_result_canonical_bytes(repeated.final_result) == success_result_canonical_bytes(
        run.final_result
    )
    assert repeated.final_result["result_hash"] == run.final_result["result_hash"]
    assert repeated.final_result["result_id"] == run.final_result["result_id"]


def test_T036_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY(run: Any) -> None:
    repeated = build_release_run()
    assert repeated.artifact_bytes[ARTIFACT_PATHS[3]] == run.artifact_bytes[ARTIFACT_PATHS[3]]
    assert repeated.artifact_bytes[ARTIFACT_PATHS[5]] == run.artifact_bytes[ARTIFACT_PATHS[5]]
    assert success_result_canonical_bytes(repeated.final_result) == success_result_canonical_bytes(
        run.final_result
    )
    assert repeated.final_result["result_hash"] == run.final_result["result_hash"]
    assert repeated.final_result["result_id"] == run.final_result["result_id"]


def test_T036_DET_003_PY311_PY312_JSON_BYTE_IDENTITY(run: Any) -> None:
    py311, py312 = _runtime_pair()
    first = _runtime_snapshot(py311)
    second = _runtime_snapshot(py312)
    assert first[DETERMINISM_SURFACES[0]] == second[DETERMINISM_SURFACES[0]]
    assert first[DETERMINISM_SURFACES[1]] == second[DETERMINISM_SURFACES[1]]
    assert first["TASK036_final_result_hash"] == second["TASK036_final_result_hash"]
    assert first["TASK036_internal_result_id"] == second["TASK036_internal_result_id"]


def test_T036_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY(run: Any) -> None:
    py311, py312 = _runtime_pair()
    first = _runtime_snapshot(py311)
    second = _runtime_snapshot(py312)
    assert first[DETERMINISM_SURFACES[2]] == second[DETERMINISM_SURFACES[2]]
    assert first[DETERMINISM_SURFACES[3]] == second[DETERMINISM_SURFACES[3]]


def test_T036_META_001_PYPROJECT_VERSION_0_3_0(run: Any) -> None:
    text = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert 'version = "0.3.0"' in text


def test_T036_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT(run: Any) -> None:
    text = (REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    assert 'name = "heat-exchanger-design-agent"' in text
    assert 'version = "0.3.0"' in text


def test_T036_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES(run: Any) -> None:
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert payload == run.manifest
    assert payload["manifest_hash"] == manifest_hash(payload)
    assert exact_file_digest(MANIFEST_PATH.read_bytes())


def test_T036_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE(run: Any) -> None:
    checklist = run.acceptance_checklist
    assert checklist["required_test_ids"] == list(TEST_IDS)
    assert len(set(checklist["required_test_ids"])) == 22
    assert checklist["checklist_hash"] == acceptance_checklist_hash(checklist)
    assert checklist["checklist_status"] == "PASS"


def test_T036_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION(run: Any) -> None:
    graph = run.graph_evidence
    assert graph["no_upstream_engineering_recomputation"] is True
    assert graph["pressure_drop_forwarded_unchanged"] is True
    assert set(UNAVAILABLE_CAPABILITIES) == {
        "BELL_DELAWARE",
        "OVERALL_U",
        "UA",
        "LMTD",
        "HEAT_DUTY",
        "OUTLET_TEMPERATURES",
        "FULL_EXCHANGER_RATING",
    }
    assert set(AVAILABLE_CAPABILITIES).issuperset({"SHELL_SIDE_THERMAL_HYDRAULIC_COMPOSITION"})
    assert verify_stage_contract()["executable"] is True
    assert verify_provenance(run.provenance) is True
