"""Tests for the v0.2.0 TASK-020 -> TASK-029 release integration demo runner."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "release_demo" / "v0_2_task020_to_task029.py"
EVIDENCE_DIR = REPO_ROOT / "release_evidence" / "v0.2.0"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
UV_LOCK_PATH = REPO_ROOT / "uv.lock"
CI_MANIFEST_PATH = REPO_ROOT / "ci-shard-manifest.yml"

sys.path.insert(0, str(REPO_ROOT / "scripts" / "release_demo"))
from v0_2_task020_to_task029 import (  # noqa: E402
    ACCEPTANCE_ITEMS,
    MANIFEST_PEER_PATHS,
    MARKDOWN_SECTIONS,
    RELEASE_VERSION,
    build_release_evidence,
    build_release_manifest,
    render_acceptance_bytes,
    render_json_bytes,
    render_markdown_bytes,
    write_release_evidence,
)

FROZEN_TEST_IDS = (
    "T030_CHAIN_001_ACTUAL_PRODUCTION_DAG_SUCCESS",
    "T030_CHAIN_002_PRODUCER_BINDING_IDENTITY",
    "T030_CHAIN_003_NO_SELF_EDGE_OR_SYNTHETIC_SUBSTITUTION",
    "T030_BLOCK_001_EARLY_CHAIN_FAIL_CLOSED",
    "T030_BLOCK_002_TASK027_UPSTREAM_MISMATCH",
    "T030_BLOCK_003_TASK028_UPSTREAM_MISMATCH",
    "T030_BLOCK_004_TASK029_TYPED_MISMATCH",
    "T030_BLOCK_005_TASK029_RAW_BOUNDARY_REJECTION",
    "T030_EVID_001_JSON_SCHEMA",
    "T030_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER",
    "T030_EVID_003_ARTIFACT_PATHS_AND_MANIFEST_MEMBERSHIP",
    "T030_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY",
    "T030_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY",
    "T030_DET_003_PY311_PY312_JSON_BYTE_IDENTITY",
    "T030_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY",
    "T030_META_001_PYPROJECT_VERSION_0_2_0",
    "T030_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT",
    "T030_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES",
    "T030_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE",
    "T030_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION",
)


def _runner_source() -> str:
    return RUNNER_PATH.read_text(encoding="utf-8")


def _import_targets() -> list[str]:
    tree = ast.parse(_runner_source(), filename=str(RUNNER_PATH))
    targets: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.append(node.module)
    return targets


def _resolve_python(version: str) -> str | None:
    env_names = (
        f"PYTHON_{version.replace('.', '_')}_PATH",
        f"UV_PYTHON_{version.replace('.', '_')}",
    )
    for env_name in env_names:
        candidate = __import__("os").environ.get(env_name)
        if candidate and Path(candidate).is_file():
            return candidate
    uv = shutil.which("uv")
    if uv:
        proc = subprocess.run(
            [uv, "python", "find", version],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0:
            found = proc.stdout.strip().splitlines()[-1].strip()
            if found and Path(found).is_file():
                return found
    return shutil.which(f"python{version}")


def _run_runner_subprocess(python_version: str, fmt: str) -> bytes:
    uv_path = shutil.which("uv")
    assert uv_path, "uv required for cross-version TASK030 proof"
    env = {
        **__import__("os").environ,
        "PYTHONPATH": f"{REPO_ROOT / 'src'}:{REPO_ROOT / 'scripts' / 'release_demo'}",
    }
    proc = subprocess.run(
        [
            uv_path,
            "run",
            "--locked",
            "--isolated",
            "--python",
            python_version,
            str(RUNNER_PATH),
            "--format",
            fmt,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
    )
    assert proc.returncode == 0, (proc.returncode, proc.stdout, proc.stderr)
    return proc.stdout


def test_T030_CHAIN_001_ACTUAL_PRODUCTION_DAG_SUCCESS() -> None:
    evidence = build_release_evidence()
    success = evidence["success_case"]
    assert "task027" in success
    assert "task028" in success
    assert "task029" in success
    assert success["task027"]["status"] == "VALID"
    assert success["task028"]["status"] == "VALID"
    assert success["task029"]["status"] == "VALID"


def test_T030_CHAIN_002_PRODUCER_BINDING_IDENTITY() -> None:
    evidence = build_release_evidence()
    identities = evidence["producer_identities"]
    required = (
        "TASK025_HYDRAULIC_AUTHORITY_HASH",
        "TASK025_RESULT_HASH",
        "TASK026_RESULT_HASH",
        "TASK027_RESULT_HASH",
        "TASK028_RESULT_HASH",
        "TASK029_RESULT_HASH",
        "TASK029_RESULT_ID",
        "PROPERTY_SNAPSHOT_HASH",
        "TASK029_COMPLETENESS_LEDGER_HASH",
        "TASK029_COMPOSITION_AUTHORITY_HASH",
    )
    for key in required:
        assert key in identities
        assert isinstance(identities[key], str)
        assert len(identities[key]) == 64 or key == "TASK029_RESULT_ID"


def test_T030_CHAIN_003_NO_SELF_EDGE_OR_SYNTHETIC_SUBSTITUTION() -> None:
    evidence = build_release_evidence()
    graph = evidence["production_graph"]
    assert graph["self_edge_count"] == 0
    assert graph["synthetic_oracle_substitution"] is False
    assert graph["fixture_only_result_substitution"] is False
    for binding in graph["chain_bindings"]:
        if binding.get("to") is None:
            continue
        assert binding["from"] != binding["to"]
    for target in _import_targets():
        assert not target.startswith("tests")


def test_T030_BLOCK_001_EARLY_CHAIN_FAIL_CLOSED() -> None:
    evidence = build_release_evidence()
    entry = next(
        item
        for item in evidence["blocked_cases"]
        if item["case_id"] == "B01_EARLY_CHAIN_FAIL_CLOSED"
    )
    assert entry["status"] == "BLOCKED"
    assert entry["success_result_present"] is False
    assert entry["partial_result_present"] is False
    assert entry["blocked_component_as_zero"] is False
    assert entry["excluded_component_as_zero"] is False


def test_T030_BLOCK_002_TASK027_UPSTREAM_MISMATCH() -> None:
    evidence = build_release_evidence()
    entry = next(
        item
        for item in evidence["blocked_cases"]
        if item["case_id"] == "B02_TASK027_UPSTREAM_BINDING_MISMATCH"
    )
    assert "BL_T027_UPSTREAM_IDENTITY_MISMATCH" in entry["actual_blocker_codes"]
    assert entry["success_result_present"] is False


def test_T030_BLOCK_003_TASK028_UPSTREAM_MISMATCH() -> None:
    evidence = build_release_evidence()
    entry = next(
        item
        for item in evidence["blocked_cases"]
        if item["case_id"] == "B03_TASK028_UPSTREAM_BINDING_OR_PROVENANCE_MISMATCH"
    )
    assert "BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH" in entry["actual_blocker_codes"]
    assert entry["success_result_present"] is False


def test_T030_BLOCK_004_TASK029_TYPED_MISMATCH() -> None:
    evidence = build_release_evidence()
    entry = next(
        item
        for item in evidence["blocked_cases"]
        if item["case_id"] == "B04_TASK029_TYPED_CROSS_INPUT_MISMATCH"
    )
    assert entry["actual_blocker_codes"]
    assert entry["success_result_present"] is False


def test_T030_BLOCK_005_TASK029_RAW_BOUNDARY_REJECTION() -> None:
    evidence = build_release_evidence()
    entry = next(
        item
        for item in evidence["blocked_cases"]
        if item["case_id"] == "B05_TASK029_RAW_BOUNDARY_REJECTION"
    )
    assert "BL_T029_REQUEST_UNKNOWN_FIELD" in entry["actual_blocker_codes"]
    assert entry["success_result_present"] is False


def test_T030_EVID_001_JSON_SCHEMA() -> None:
    evidence = build_release_evidence()
    for key in (
        "schema_version",
        "release_version",
        "scope",
        "production_graph",
        "success_case",
        "blocked_cases",
        "producer_identities",
        "determinism",
        "version_metadata",
        "release_manifest",
        "acceptance",
    ):
        assert key in evidence


def test_T030_EVID_002_MARKDOWN_SCHEMA_AND_SECTION_ORDER() -> None:
    md = render_markdown_bytes(build_release_evidence()).decode("utf-8")
    headings = [line[3:] for line in md.splitlines() if line.startswith("## ")]
    for section in MARKDOWN_SECTIONS:
        assert section in headings
    assert headings.index("Release Identity") < headings.index("Scope and Production Graph")
    assert headings.index("Release Acceptance") < headings.index(
        "Non-Claims / Engineering-Proof Boundary"
    )


def test_T030_EVID_003_ARTIFACT_PATHS_AND_MANIFEST_MEMBERSHIP() -> None:
    assert list(MANIFEST_PEER_PATHS) == sorted(MANIFEST_PEER_PATHS)
    for rel_path in MANIFEST_PEER_PATHS:
        assert (REPO_ROOT / rel_path).is_file()


def test_T030_DET_001_REPEAT_RUN_JSON_BYTE_IDENTITY() -> None:
    e1 = render_json_bytes(build_release_evidence())
    e2 = render_json_bytes(build_release_evidence())
    assert e1 == e2


def test_T030_DET_002_REPEAT_RUN_MARKDOWN_BYTE_IDENTITY() -> None:
    e1 = render_markdown_bytes(build_release_evidence())
    e2 = render_markdown_bytes(build_release_evidence())
    assert e1 == e2


def test_T030_DET_003_PY311_PY312_JSON_BYTE_IDENTITY() -> None:
    py311 = _resolve_python("3.11")
    py312 = _resolve_python("3.12")
    if py311 is None or py312 is None:
        pytest.skip("Python 3.11 and 3.12 interpreters required for cross-version proof")
    assert _run_runner_subprocess("3.11", "json") == _run_runner_subprocess("3.12", "json")


def test_T030_DET_004_PY311_PY312_MARKDOWN_BYTE_IDENTITY() -> None:
    py311 = _resolve_python("3.11")
    py312 = _resolve_python("3.12")
    if py311 is None or py312 is None:
        pytest.skip("Python 3.11 and 3.12 interpreters required for cross-version proof")
    assert _run_runner_subprocess("3.11", "markdown") == _run_runner_subprocess("3.12", "markdown")


def test_T030_META_001_PYPROJECT_VERSION_0_2_0() -> None:
    text = PYPROJECT_PATH.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.MULTILINE)
    assert match is not None
    assert match.group(1) == RELEASE_VERSION


def test_T030_META_002_UV_LOCK_PROJECT_VERSION_ALIGNMENT() -> None:
    text = UV_LOCK_PATH.read_text(encoding="utf-8")
    assert 'name = "heat-exchanger-design-agent"' in text
    package_block = text.split('name = "heat-exchanger-design-agent"', 1)[1]
    version_line = package_block.splitlines()[1]
    assert f'version = "{RELEASE_VERSION}"' in version_line


def test_T030_MANIFEST_001_RELEASE_MANIFEST_SHA256_EXACT_BYTES() -> None:
    json_bytes = (EVIDENCE_DIR / "task020-to-task029-demo.json").read_bytes()
    md_bytes = (EVIDENCE_DIR / "task020-to-task029-demo.md").read_bytes()
    acceptance_bytes = (EVIDENCE_DIR / "release-acceptance.md").read_bytes()
    expected_manifest = build_release_manifest(
        json_bytes=json_bytes,
        markdown_bytes=md_bytes,
        acceptance_bytes=acceptance_bytes,
    )
    actual_manifest = (EVIDENCE_DIR / "release-manifest.json").read_bytes()
    assert actual_manifest == expected_manifest
    manifest = json.loads(actual_manifest.decode("utf-8"))
    assert manifest["self_digest_entry"] is False
    assert len(manifest["artifacts"]) == 3


def test_T030_ACCEPT_001_ACCEPTANCE_CHECKLIST_COMPLETE() -> None:
    evidence = build_release_evidence()
    acceptance = evidence["acceptance"]
    assert acceptance["item_count"] == 20
    assert tuple(sorted(acceptance["items"])) == ACCEPTANCE_ITEMS
    for item in ACCEPTANCE_ITEMS:
        assert acceptance["items"][item]["status"] == "PASS"


def test_T030_ACCEPT_002_NO_UPSTREAM_ENGINEERING_PROOF_SUBSTITUTION() -> None:
    evidence = build_release_evidence()
    scope = evidence["scope"]
    disclaimer = evidence["disclaimer"]
    assert scope["release_acceptance_is_not_engineering_correctness_proof"] is True
    assert disclaimer["release_acceptance_is_not_engineering_correctness_proof"] is True
    graph = evidence["production_graph"]
    assert graph["no_recomputation_of_task027_task028_task029_engineering"] is True


def test_frozen_json_matches_runner_bytes() -> None:
    evidence = build_release_evidence()
    assert (EVIDENCE_DIR / "task020-to-task029-demo.json").read_bytes() == render_json_bytes(
        evidence
    )


def test_frozen_markdown_matches_runner_bytes() -> None:
    evidence = build_release_evidence()
    assert (EVIDENCE_DIR / "task020-to-task029-demo.md").read_bytes() == render_markdown_bytes(
        evidence
    )


def test_frozen_acceptance_matches_runner_bytes() -> None:
    evidence = build_release_evidence()
    assert (EVIDENCE_DIR / "release-acceptance.md").read_bytes() == render_acceptance_bytes(
        evidence
    )


def test_ci_manifest_registers_v0_2_test_once() -> None:
    text = CI_MANIFEST_PATH.read_text(encoding="utf-8")
    target = "tests/release_demo/test_v0_2_task020_to_task029.py"
    assert text.count(target) == 1


def test_test_id_inventory_exact() -> None:
    source = Path(__file__).read_text(encoding="utf-8")
    found = [
        name.removeprefix("test_") for name in re.findall(r"def (test_T030_[A-Z0-9_]+)\(", source)
    ]
    assert len(found) == 20
    assert tuple(found) == FROZEN_TEST_IDS


def test_runner_does_not_import_tests() -> None:
    for target in _import_targets():
        assert not target.startswith("tests")


def test_write_evidence_regenerates_manifest_last() -> None:
    write_release_evidence(EVIDENCE_DIR)
    manifest = json.loads((EVIDENCE_DIR / "release-manifest.json").read_text(encoding="utf-8"))
    for artifact in manifest["artifacts"]:
        path = REPO_ROOT / artifact["path"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == artifact["sha256"]
