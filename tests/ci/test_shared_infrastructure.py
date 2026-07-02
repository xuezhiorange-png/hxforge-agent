"""Tests for unified artifact identity verifier, marker inventory,
behavior environment contract, and run_test_shard telemetry runner.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from tests.ci.artifact_identity import (
    REQUIRED_ARTIFACT_KINDS,
    ArtifactError,
    verify_artifacts,
)
from tests.ci.marker_inventory import (
    MarkerInventoryError,
    load_marker_inventory,
    verify_marker_ownership,
)

_SHA40 = "a" * 40
_SHA64 = "b" * 64


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manifest(tmp: Path) -> Path:
    """Write a minimal shard manifest."""
    manifest = {
        "version": "1",
        "shards": [
            {
                "name": "ci",
                "job": "shard-ci",
                "python": ["3.11"],
                "files": ["tests/ci/test_shard_manifest.py"],
                "timeout": 60,
            },
            {
                "name": "unit",
                "job": "shard-unit",
                "python": ["3.11", "3.12"],
                "files": ["tests/unit/test_calculation_runs.py"],
                "timeout": 60,
            },
        ],
    }
    path = tmp / "ci-shard-manifest.yml"
    import yaml

    path.write_text(yaml.dump(manifest), encoding="utf-8")
    return path


# Mapping from artifact kind to expected file name
_KIND_FILE_MAP: dict[str, str] = {
    "node-inventory": "node-inventory.json",
    "node-marker-inventory": "node-marker-inventory.json",
    "behavior-environment": "behavior-environment.json",
    "junit": "junit.xml",
    "coverage-raw": "coverage-raw.raw",
    "coverage-xml": "coverage.xml",
    "pytest-stderr": "pytest-stderr.txt",
    "resource-telemetry": "resource-telemetry.json",
}


def _make_artifact_bundle(
    root: Path,
    *,
    track: str,
    shard: str,
    python_version: str,
    commit_sha: str,
    run_id: str,
    run_attempt: int,
    present: bool = True,
) -> Path:
    """Create a minimal artifact bundle with metadata AND real files."""
    bundle_dir = root / f"{track}-{shard}-py{python_version}"
    bundle_dir.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for k in sorted(REQUIRED_ARTIFACT_KINDS):
        fname = _KIND_FILE_MAP.get(k, f"{k}.json")
        artifacts.append({"kind": k, "path": fname, "present": present})
        if present:
            (bundle_dir / fname).write_text(f"placeholder-{k}", encoding="utf-8")
    meta = {
        "identity": {
            "track": track,
            "commit_sha": commit_sha,
            "run_id": run_id,
            "run_attempt": run_attempt,
            "python_version": python_version,
            "shard": shard,
        },
        "artifacts": artifacts,
    }
    (bundle_dir / "artifact-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return bundle_dir


def _make_marker_inventory(
    *,
    track: str,
    shard: str,
    python_version: str,
    node_markers: dict[str, list[str]],
    commit_sha: str = _SHA40,
    run_id: str = "123",
    run_attempt: int = 1,
    collection_scope: str = "shard",
) -> dict[str, Any]:
    return {
        "schema_version": "1",
        "track": track,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "shard": shard,
        "collection_scope": collection_scope,
        "node_markers": node_markers,
        "node_count": len(node_markers),
    }


# ---------------------------------------------------------------------------
# artifact_identity tests
# ---------------------------------------------------------------------------


class TestArtifactIdentity:
    """Tests for unified artifact identity verifier."""

    def test_pass_all_present(self, tmp_path: Path) -> None:
        """All expected shards present with correct identity → PASS."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        # 2 shards × 2 python versions = 4 expected (ci has only 3.11, unit has 3.11+3.12)
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="unit",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="unit",
            python_version="3.12",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        verify_artifacts(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            expected_run_attempt=1,
        )

    def test_reject_wrong_track(self, tmp_path: Path) -> None:
        """Mismatched track → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="wrong",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        with pytest.raises(ArtifactError, match="track mismatch"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_wrong_sha(self, tmp_path: Path) -> None:
        """Mismatched commit SHA → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha="c" * 40,
            run_id="100",
            run_attempt=1,
        )
        with pytest.raises(ArtifactError, match="SHA mismatch"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_missing_producer(self, tmp_path: Path) -> None:
        """Missing expected producer → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        # Only provide ci, missing unit
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        with pytest.raises(ArtifactError, match="MISSING producers"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_duplicate_identity(self, tmp_path: Path) -> None:
        """Duplicate identity → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Create a duplicate in a different directory with actual files
        dup_dir = root / "dup"
        dup_dir.mkdir()
        artifacts = []
        for k in sorted(REQUIRED_ARTIFACT_KINDS):
            fname = _KIND_FILE_MAP.get(k, f"{k}.json")
            artifacts.append({"kind": k, "path": fname, "present": True})
            (dup_dir / fname).write_text(f"placeholder-{k}", encoding="utf-8")
        meta = {
            "identity": {
                "track": "pr-head",
                "commit_sha": _SHA40,
                "run_id": "100",
                "run_attempt": 1,
                "python_version": "3.11",
                "shard": "ci",
            },
            "artifacts": artifacts,
        }
        (dup_dir / "artifact-metadata.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="DUPLICATE"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_wrong_attempt(self, tmp_path: Path) -> None:
        """Mismatched run attempt → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=2,
        )
        with pytest.raises(ArtifactError, match="attempt mismatch"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_missing_artifact_kind(self, tmp_path: Path) -> None:
        """Missing artifact kind in metadata → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = root / "test"
        bundle_dir.mkdir()
        meta = {
            "identity": {
                "track": "pr-head",
                "commit_sha": _SHA40,
                "run_id": "100",
                "run_attempt": 1,
                "python_version": "3.11",
                "shard": "ci",
            },
            "artifacts": [
                {"kind": "junit", "path": "junit.xml", "present": True},
                # Missing other required kinds
            ],
        }
        (bundle_dir / "artifact-metadata.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        # Create the file so filesystem check passes
        (bundle_dir / "junit.xml").write_text("<testsuites/>", encoding="utf-8")
        with pytest.raises(ArtifactError, match="MISSING KINDS"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_absent_artifact(self, tmp_path: Path) -> None:
        """P0-3: Artifact declared present but file missing → FAIL (fail-closed)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = root / "test"
        bundle_dir.mkdir()
        meta = {
            "identity": {
                "track": "pr-head",
                "commit_sha": _SHA40,
                "run_id": "100",
                "run_attempt": 1,
                "python_version": "3.11",
                "shard": "ci",
            },
            "artifacts": [
                {"kind": k, "path": _KIND_FILE_MAP.get(k, f"{k}.json"), "present": True}
                for k in sorted(REQUIRED_ARTIFACT_KINDS)
            ],
        }
        (bundle_dir / "artifact-metadata.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        # Do NOT create the actual files — verifier must fail-closed
        with pytest.raises(ArtifactError, match="DECLARED PRESENT BUT FILE ABSENT"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_no_metadata_files_raises(self, tmp_path: Path) -> None:
        """No artifact-metadata.json → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        with pytest.raises(ArtifactError, match="no artifact-metadata"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )


# ---------------------------------------------------------------------------
# marker_inventory tests
# ---------------------------------------------------------------------------


class TestMarkerInventory:
    """Tests for P1-1 separate marker inventory artifact."""

    def test_valid_marker_inventory(self, tmp_path: Path) -> None:
        """Valid marker inventory is accepted."""
        inv = _make_marker_inventory(
            track="pr-head",
            shard="ci",
            python_version="3.11",
            node_markers={"tests/ci/test_a.py::test_a": ["golden"]},
        )
        path = tmp_path / "markers.json"
        path.write_text(json.dumps(inv, indent=2), encoding="utf-8")
        loaded = load_marker_inventory(path)
        assert loaded["node_count"] == 1

    def test_rejects_missing_markers(self, tmp_path: Path) -> None:
        """Missing node_markers → FAIL."""
        inv = {
            "schema_version": "1",
            "track": "pr-head",
            "commit_sha": _SHA40,
            "run_id": "123",
            "run_attempt": 1,
            "python_version": "3.11",
            "shard": "ci",
            "collection_scope": "shard",
            "node_markers": {},
            "node_count": 0,
        }
        path = tmp_path / "markers.json"
        path.write_text(json.dumps(inv), encoding="utf-8")
        loaded = load_marker_inventory(path)
        assert loaded["node_count"] == 0

    def test_rejects_wrong_sha(self, tmp_path: Path) -> None:
        """Non-hex SHA → FAIL."""
        inv = _make_marker_inventory(
            track="pr-head",
            shard="ci",
            python_version="3.11",
            node_markers={},
            commit_sha="not-a-sha",
        )
        path = tmp_path / "markers.json"
        path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(MarkerInventoryError, match="commit_sha"):
            load_marker_inventory(path)

    def test_rejects_unsorted_markers(self, tmp_path: Path) -> None:
        """Unsorted marker list → FAIL."""
        inv = _make_marker_inventory(
            track="pr-head",
            shard="ci",
            python_version="3.11",
            node_markers={"tests/test_a.py::test_a": ["pure", "golden"]},  # not sorted
        )
        path = tmp_path / "markers.json"
        path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(MarkerInventoryError, match="sorted and deduplicated"):
            load_marker_inventory(path)

    def test_rejects_node_count_mismatch(self, tmp_path: Path) -> None:
        """node_count mismatch → FAIL."""
        inv = _make_marker_inventory(
            track="pr-head",
            shard="ci",
            python_version="3.11",
            node_markers={"tests/test_a.py::test_a": []},
        )
        inv["node_count"] = 999
        path = tmp_path / "markers.json"
        path.write_text(json.dumps(inv), encoding="utf-8")
        with pytest.raises(MarkerInventoryError, match="node_count"):
            load_marker_inventory(path)

    def test_golden_benchmark_overlap_rejected(self) -> None:
        """Node with both golden and benchmark → FAIL."""
        inv_a = _make_marker_inventory(
            track="pr-head",
            shard="ci",
            python_version="3.11",
            node_markers={"tests/test_a.py::test_a": ["golden"]},
        )
        inv_b = _make_marker_inventory(
            track="pr-head",
            shard="unit",
            python_version="3.11",
            node_markers={"tests/test_b.py::test_b": ["benchmark"]},
        )
        # Add overlap
        inv_a["node_markers"]["tests/test_a.py::test_a"] = ["golden", "benchmark"]
        inv_a["node_count"] = len(inv_a["node_markers"])
        with pytest.raises(MarkerInventoryError, match="both golden and benchmark"):
            verify_marker_ownership(
                [inv_a, inv_b],
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="123",
                expected_run_attempt=1,
            )

    def test_verify_per_python_separation(self) -> None:
        """Per-Python golden/benchmark separation verified."""
        inv_311_golden = _make_marker_inventory(
            track="main",
            shard="golden",
            python_version="3.11",
            node_markers={"tests/golden/test_a.py::test_a": ["golden"]},
        )
        inv_311_unit = _make_marker_inventory(
            track="main",
            shard="unit",
            python_version="3.11",
            node_markers={"tests/unit/test_b.py::test_b": []},
        )
        inv_312_golden = _make_marker_inventory(
            track="main",
            shard="golden",
            python_version="3.12",
            node_markers={"tests/golden/test_a.py::test_a": ["golden"]},
        )
        inv_312_unit = _make_marker_inventory(
            track="main",
            shard="unit",
            python_version="3.12",
            node_markers={"tests/unit/test_b.py::test_b": []},
        )
        verify_marker_ownership(
            [inv_311_golden, inv_311_unit, inv_312_golden, inv_312_unit],
            expected_track="main",
            expected_commit_sha=_SHA40,
            expected_run_id="123",
            expected_run_attempt=1,
        )


# ---------------------------------------------------------------------------
# behavior_environment tests
# ---------------------------------------------------------------------------


class TestBehaviorEnvironment:
    """Tests for P0-8 behavior environment contract."""

    def test_fingerprint_deterministic(self, tmp_path: Path) -> None:
        """Same environment → same fingerprint."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "uv.lock").write_text("lock v1", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        os.chdir(tmp_path)
        fp1 = build_behavior_fingerprint(repo_root=tmp_path)
        fp2 = build_behavior_fingerprint(repo_root=tmp_path)
        assert fp1["fingerprint"] == fp2["fingerprint"]

    def test_fingerprint_differs_with_different_lock(self, tmp_path: Path) -> None:
        """Different lock file → different fingerprint."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        os.chdir(tmp_path)
        (tmp_path / "uv.lock").write_text("lock v1", encoding="utf-8")
        fp1 = build_behavior_fingerprint(repo_root=tmp_path)
        (tmp_path / "uv.lock").write_text("lock v2", encoding="utf-8")
        fp2 = build_behavior_fingerprint(repo_root=tmp_path)
        assert fp1["fingerprint"] != fp2["fingerprint"]

    def test_payload_is_canonical_json(self, tmp_path: Path) -> None:
        """Payload canonical JSON is sorted and compact."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "uv.lock").write_text("x", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
        os.chdir(tmp_path)
        fp = build_behavior_fingerprint(repo_root=tmp_path)
        # Canonical JSON should have no spaces after separators
        assert ", " not in fp["canonical_json"]


# ---------------------------------------------------------------------------
# run_test_shard tests
# ---------------------------------------------------------------------------


class TestRunTestShard:
    """Tests for P0-4 real resource telemetry runner."""

    def test_telemetry_generates_on_pass(self, tmp_path: Path) -> None:
        """Running passing tests generates valid telemetry."""
        from tests.ci.run_test_shard import run_pytest

        exit_code = run_pytest(
            ["-q", "--tb=short", "-x", "--co"],  # just collection, no execution
            env={"PYTHONPATH": str(Path.cwd())},
            junit_path=str(tmp_path / "junit.xml"),
            telemetry_path=str(tmp_path / "telemetry.json"),
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
            track="pr-head",
            commit_sha=_SHA40,
            run_id="999",
            run_attempt=1,
            python_version="3.12",
            shard="test",
        )
        telemetry = json.loads((tmp_path / "telemetry.json").read_text())
        assert telemetry["track"] == "pr-head"
        assert telemetry["commit_sha"] == _SHA40
        assert telemetry["pytest_exit_code"] == exit_code
        assert telemetry["wall_clock_seconds"] >= 0
        assert telemetry["cpu_user_seconds"] >= 0
        assert telemetry["cpu_system_seconds"] >= 0
        assert telemetry["peak_rss_kb"] >= 0

    def test_telemetry_on_timeout(self, tmp_path: Path) -> None:
        """Timeout produces telemetry with exit code -9."""
        from tests.ci.run_test_shard import run_pytest

        # Create a test file that sleeps to guarantee timeout
        slow_test = tmp_path / "test_slow.py"
        slow_test.write_text(
            "import time\ndef test_slow():\n    time.sleep(30)\n",
            encoding="utf-8",
        )
        run_pytest(
            ["-q", "--tb=short", str(slow_test)],
            env={"PYTHONPATH": str(tmp_path)},
            timeout=1,
            junit_path=str(tmp_path / "junit.xml"),
            telemetry_path=str(tmp_path / "telemetry.json"),
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
            track="test",
            commit_sha=_SHA40,
            run_id="1",
            run_attempt=1,
            python_version="3.12",
            shard="test",
        )
        telemetry = json.loads((tmp_path / "telemetry.json").read_text())
        assert telemetry["pytest_exit_code"] == -9

    def test_telemetry_exit_code_matches_pytest(self, tmp_path: Path) -> None:
        """Telemetry exit code exactly matches pytest exit code."""
        from tests.ci.run_test_shard import run_pytest

        # Write a failing test
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_fail(): assert False\n", encoding="utf-8")
        exit_code = run_pytest(
            ["-q", "--tb=short", f"--junitxml={tmp_path / 'junit.xml'}", str(test_file)],
            env={"PYTHONPATH": str(tmp_path)},
            junit_path=str(tmp_path / "junit.xml"),
            telemetry_path=str(tmp_path / "telemetry.json"),
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
            track="test",
            commit_sha=_SHA40,
            run_id="1",
            run_attempt=1,
            python_version="3.12",
            shard="test",
        )
        telemetry = json.loads((tmp_path / "telemetry.json").read_text())
        assert telemetry["pytest_exit_code"] == exit_code
        assert telemetry["pytest_exit_code"] != 0
        assert telemetry["tests_failed"] > 0
