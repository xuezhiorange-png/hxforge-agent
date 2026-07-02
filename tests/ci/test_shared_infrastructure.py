"""Tests for unified artifact identity verifier, marker inventory,
behavior environment contract, and run_test_shard telemetry runner.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest

from tests.ci.artifact_identity import (
    GLOBAL_REQUIRED_ARTIFACT_KINDS,
    REQUIRED_ARTIFACT_KINDS,
    SHARD_REQUIRED_ARTIFACT_KINDS,
    ArtifactError,
    verify_artifacts,
    verify_global_bundles,
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
    "pytest-outcomes": "pytest-outcomes.json",
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
    bundle_name: str | None = None,
    scope: str = "shard",
) -> Path:
    """Create a minimal artifact bundle with metadata AND real files."""
    if scope == "global":
        dir_name = bundle_name or f"{track}-global-py{python_version}"
    else:
        dir_name = bundle_name or f"{track}-{shard}-py{python_version}"
    bundle_dir = root / dir_name
    bundle_dir.mkdir(parents=True, exist_ok=True)

    node_ids = ["tests/ci/test_a.py::test_a"]
    node_markers: dict[str, list[str]] = {"tests/ci/test_a.py::test_a": []}

    # Build a valid behavior-environment.json with correct digest first,
    # so the fingerprint can be embedded in node-inventory for cross-validation.
    beh_payload: dict[str, Any] = {
        "python_version": python_version,
        "environment": {},
        "file_digests": {},
        "working_directory": "/test",
    }
    beh_canonical = json.dumps(
        beh_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    beh_digest = hashlib.sha256(beh_canonical.encode("utf-8")).hexdigest()

    if scope == "global":
        required_kinds = GLOBAL_REQUIRED_ARTIFACT_KINDS
        _json_content: dict[str, dict[str, Any] | None] = {
            "node-inventory": {
                "track": track,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "python_version": python_version,
                "shard": None,
                "collection_scope": "global",
                "node_ids": node_ids,
                "behavior_fingerprint_sha256": beh_digest,
            },
            "node-marker-inventory": {
                "track": track,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "python_version": python_version,
                "shard": None,
                "node_markers": node_markers,
            },
            "behavior-environment": {
                "schema_version": "1",
                "payload": beh_payload,
                "canonical_json_sha256": f"sha256:{beh_digest}",
            },
        }
    else:
        required_kinds = SHARD_REQUIRED_ARTIFACT_KINDS
        _json_content = {
            "node-inventory": {
                "track": track,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "python_version": python_version,
                "shard": shard,
                "collection_scope": "shard",
                "node_ids": node_ids,
                "behavior_fingerprint_sha256": beh_digest,
            },
            "node-marker-inventory": {
                "track": track,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "python_version": python_version,
                "shard": shard,
                "node_markers": node_markers,
            },
            "behavior-environment": {
                "schema_version": "1",
                "payload": beh_payload,
                "canonical_json_sha256": f"sha256:{beh_digest}",
            },
            "pytest-outcomes": {
                "schema_version": "1",
                "outcomes": {"tests/ci/test_a.py::test_a": "passed"},
                "total": 1,
                "collection_complete": ["tests/ci/test_a.py::test_a"],
            },
            "resource-telemetry": {
                "track": track,
                "commit_sha": commit_sha,
                "run_id": run_id,
                "run_attempt": run_attempt,
                "python_version": python_version,
                "shard": shard,
                "execution_status": "completed",
                "junit_parse_status": "available",
                "counts_authoritative": True,
                "resource_measurement_status": "available",
                "outcome_parse_status": "available",
                "pytest_exit_code": 0,
                "tests_passed": 1,
                "tests_failed": 0,
                "tests_skipped": 0,
                "tests_xfailed": 0,
                "tests_xpassed": 0,
            },
        }

    artifacts = []
    for k in sorted(required_kinds):
        fname = _KIND_FILE_MAP.get(k, f"{k}.json")
        artifacts.append({"kind": k, "path": fname, "present": present})
        if present:
            json_data = _json_content.get(k)
            if json_data is not None:
                (bundle_dir / fname).write_text(json.dumps(json_data, indent=2), encoding="utf-8")
            else:
                (bundle_dir / fname).write_text(f"placeholder-{k}", encoding="utf-8")

    # Build identity based on scope
    identity: dict[str, Any] = {
        "track": track,
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
    }
    if scope == "global":
        identity["collection_scope"] = "global"
        # No shard field for global
    else:
        identity["shard"] = shard
        # No collection_scope — defaults to "shard" in _parse_identity

    meta = {
        "identity": identity,
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
        with pytest.raises(ArtifactError, match="MISSING.*producers"):
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
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
            bundle_name="dup",
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

    def test_reject_symlink(self, tmp_path: Path) -> None:
        """Symlink in bundle → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Replace one file with a symlink
        target = bundle_dir / "junit.xml"
        target.unlink()
        target.symlink_to(bundle_dir / "node-inventory.json")
        with pytest.raises(ArtifactError, match="SYMLINK"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_corrupt_json(self, tmp_path: Path) -> None:
        """Corrupt JSON in artifact → FAIL (fail-closed)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Corrupt node-inventory.json
        (bundle_dir / "node-inventory.json").write_text("NOT VALID JSON {{{", encoding="utf-8")
        with pytest.raises(ArtifactError, match="CORRUPT JSON"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_undeclared_file(self, tmp_path: Path) -> None:
        """Extra undeclared file in bundle → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Add an undeclared file
        (bundle_dir / "undeclared-extra.txt").write_text("surprise!", encoding="utf-8")
        with pytest.raises(ArtifactError, match="UNDECLARED FILES"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_missing_execution_status(self, tmp_path: Path) -> None:
        """resource-telemetry.json without execution_status → FAIL."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite resource-telemetry.json without execution_status
        tel = {
            "track": "pr-head",
            "commit_sha": _SHA40,
            "run_id": "100",
            "run_attempt": 1,
            "python_version": "3.11",
            "shard": "ci",
        }
        (bundle_dir / "resource-telemetry.json").write_text(
            json.dumps(tel, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="execution_status"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    # ── Per-kind artifact policy tests (P0-1) ──────────────────────────────

    def test_accept_empty_pytest_stderr(self, tmp_path: Path) -> None:
        """Empty pytest-stderr.txt is ACCEPTED (allow_empty=True)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        # Create all expected bundles (ci/3.11, unit/3.11, unit/3.12)
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
        # Overwrite the ci bundle's pytest-stderr.txt with empty content (allowed)
        ci_dir = root / "pr-head-ci-py3.11"
        (ci_dir / "pytest-stderr.txt").write_text("", encoding="utf-8")
        # Should pass — empty stderr is allowed by allow_empty policy
        verify_artifacts(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            expected_run_attempt=1,
        )

    def test_reject_empty_node_inventory(self, tmp_path: Path) -> None:
        """Empty node-inventory.json → REJECTED (allow_empty=False)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Overwrite node-inventory.json with empty content
        (bundle_dir / "node-inventory.json").write_text("", encoding="utf-8")
        with pytest.raises(ArtifactError, match="EMPTY REQUIRED FILE"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_empty_resource_telemetry(self, tmp_path: Path) -> None:
        """Empty resource-telemetry.json → REJECTED (allow_empty=False)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Overwrite resource-telemetry.json with empty content
        (bundle_dir / "resource-telemetry.json").write_text("", encoding="utf-8")
        with pytest.raises(ArtifactError, match="EMPTY REQUIRED FILE"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_unknown_artifact_kind(self, tmp_path: Path) -> None:
        """Extra unknown artifact kind → REJECTED (EXTRA KINDS)."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Inject an extra unknown kind into metadata
        meta_path = bundle_dir / "artifact-metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["artifacts"].append(
            {"kind": "unknown-extra-kind", "path": "unknown-extra-kind.json", "present": True}
        )
        meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        # Create the file so the filesystem check passes
        (bundle_dir / "unknown-extra-kind.json").write_text("extra", encoding="utf-8")
        with pytest.raises(ArtifactError, match="EXTRA KINDS"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    # ── Behavior-environment digest recomputation tests (P0-2) ──────────────

    def test_reject_behavior_environment_digest_mismatch(self, tmp_path: Path) -> None:
        """Payload modified but digest unchanged → REJECTED."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite behavior-environment.json with tampered payload but original digest
        beh = {
            "schema_version": "1",
            "payload": {
                "python_version": "3.11",
                "environment": {"TAMPERED": "yes"},
                "file_digests": {},
                "working_directory": "/tampered",
            },
            "canonical_json_sha256": "sha256:" + "a" * 64,  # wrong digest
        }
        (bundle_dir / "behavior-environment.json").write_text(
            json.dumps(beh, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="digest mismatch"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_behavior_environment_wrong_schema_version(self, tmp_path: Path) -> None:
        """behavior-environment.json with schema_version != '1' → REJECTED."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite behavior-environment.json with wrong schema_version
        beh = {
            "schema_version": "99",
            "payload": {
                "python_version": "3.11",
                "environment": {},
                "file_digests": {},
                "working_directory": "/test",
            },
            "canonical_json_sha256": "sha256:" + "a" * 64,
        }
        (bundle_dir / "behavior-environment.json").write_text(
            json.dumps(beh, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="schema_version"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    # ── Telemetry fail-closed checks (P0-5) ────────────────────────────────

    def test_reject_telemetry_not_completed(self, tmp_path: Path) -> None:
        """resource-telemetry with execution_status != completed → REJECTED."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite resource-telemetry.json with non-completed status
        tel = {
            "track": "pr-head",
            "commit_sha": _SHA40,
            "run_id": "100",
            "run_attempt": 1,
            "python_version": "3.11",
            "shard": "ci",
            "execution_status": "timeout",
            "junit_parse_status": "available",
            "counts_authoritative": True,
            "resource_measurement_status": "available",
            "pytest_exit_code": -9,
        }
        (bundle_dir / "resource-telemetry.json").write_text(
            json.dumps(tel, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="execution_status"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_telemetry_counts_not_authoritative(self, tmp_path: Path) -> None:
        """resource-telemetry with counts_authoritative=false → REJECTED."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite resource-telemetry.json with counts_authoritative=false
        tel = {
            "track": "pr-head",
            "commit_sha": _SHA40,
            "run_id": "100",
            "run_attempt": 1,
            "python_version": "3.11",
            "shard": "ci",
            "execution_status": "completed",
            "junit_parse_status": "available",
            "counts_authoritative": False,
            "resource_measurement_status": "available",
            "pytest_exit_code": 0,
        }
        (bundle_dir / "resource-telemetry.json").write_text(
            json.dumps(tel, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="counts_authoritative"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )


# ---------------------------------------------------------------------------
# Global bundle verification tests
# ---------------------------------------------------------------------------


class TestGlobalBundleVerification:
    """Tests for global bundle verification."""

    def test_pass_global_bundles(self, tmp_path: Path) -> None:
        """Two global bundles (3.11, 3.12) with correct identity → PASS."""
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
            scope="global",
            bundle_name="pr-head-global-py3.11",
        )
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="",
            python_version="3.12",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
            scope="global",
            bundle_name="pr-head-global-py3.12",
        )
        verify_global_bundles(
            artifact_root=root,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            expected_run_attempt=1,
            python_versions=["3.11", "3.12"],
        )

    def test_reject_global_with_shard(self, tmp_path: Path) -> None:
        """Global bundle that has shard set → fail."""
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = root / "pr-head-global-py3.11"
        bundle_dir.mkdir()
        # Create a global bundle with shard set (invalid)
        meta = {
            "identity": {
                "track": "pr-head",
                "commit_sha": _SHA40,
                "run_id": "100",
                "run_attempt": 1,
                "python_version": "3.11",
                "collection_scope": "global",
                "shard": "ci",  # Invalid: global must not have shard
            },
            "artifacts": [],
        }
        (bundle_dir / "artifact-metadata.json").write_text(
            json.dumps(meta, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="global scope must not have shard"):
            verify_global_bundles(
                artifact_root=root,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
                python_versions=["3.11"],
            )

    def test_reject_shard_as_global(self, tmp_path: Path) -> None:
        """Shard bundle passed to global verifier → missing."""
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
            scope="shard",
        )
        with pytest.raises(ArtifactError, match="MISSING global bundles"):
            verify_global_bundles(
                artifact_root=root,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
                python_versions=["3.11"],
            )

    def test_reject_global_wrong_track(self, tmp_path: Path) -> None:
        """Global bundle with wrong track → fail."""
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="wrong",
            shard="",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
            scope="global",
            bundle_name="wrong-global-py3.11",
        )
        with pytest.raises(ArtifactError, match="global track mismatch"):
            verify_global_bundles(
                artifact_root=root,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
                python_versions=["3.11"],
            )


# ---------------------------------------------------------------------------
# Outcome cross-validation tests
# ---------------------------------------------------------------------------


class TestOutcomeCrossValidation:
    """Tests for pytest-outcomes cross-validation with telemetry."""

    def test_reject_mismatched_outcome_count(self, tmp_path: Path) -> None:
        """pytest-outcomes total != telemetry tests_passed → fail."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite pytest-outcomes to claim 2 passed tests
        outcomes = {
            "schema_version": "1",
            "outcomes": {
                "tests/ci/test_a.py::test_a": "passed",
                "tests/ci/test_b.py::test_b": "passed",
            },
            "total": 2,
            "collection_complete": [
                "tests/ci/test_a.py::test_a",
                "tests/ci/test_b.py::test_b",
            ],
        }
        (bundle_dir / "pytest-outcomes.json").write_text(
            json.dumps(outcomes, indent=2), encoding="utf-8"
        )
        # Telemetry still says tests_passed=1 (from original bundle creation)
        with pytest.raises(ArtifactError, match="outcome/telemetry count mismatch"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_invalid_outcome_value(self, tmp_path: Path) -> None:
        """Invalid outcome value → fail."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Rewrite pytest-outcomes with invalid value
        outcomes = {
            "schema_version": "1",
            "outcomes": {
                "tests/ci/test_a.py::test_a": "invalid_value",
            },
            "total": 1,
            "collection_complete": ["tests/ci/test_a.py::test_a"],
        }
        (bundle_dir / "pytest-outcomes.json").write_text(
            json.dumps(outcomes, indent=2), encoding="utf-8"
        )
        with pytest.raises(ArtifactError, match="invalid outcome"):
            verify_artifacts(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                expected_run_attempt=1,
            )

    def test_reject_duplicate_outcome_node(self, tmp_path: Path) -> None:
        """Duplicate node_id in outcomes → fail."""
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        bundle_dir = _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        # Write raw JSON with duplicate keys (Python json.dumps can't do this)
        raw_json = (
            '{"schema_version": "1", '
            '"outcomes": {"tests/ci/test_a.py::test_a": "passed", '
            '"tests/ci/test_a.py::test_a": "failed"}, '
            '"total": 2, '
            '"collection_complete": ["tests/ci/test_a.py::test_a"]}'
        )
        (bundle_dir / "pytest-outcomes.json").write_text(raw_json, encoding="utf-8")
        # json.loads normalizes to last key; total=2 != len(outcomes)=1 → rejected
        with pytest.raises(ArtifactError, match="total.*!= len"):
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

    def test_fingerprint_deterministic(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Same environment → same fingerprint."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "uv.lock").write_text("lock v1", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        fp1 = build_behavior_fingerprint(repo_root=tmp_path)
        fp2 = build_behavior_fingerprint(repo_root=tmp_path)
        assert fp1["fingerprint"] == fp2["fingerprint"]

    def test_fingerprint_differs_with_different_lock(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Different lock file → different fingerprint."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "pyproject.toml").write_text("[project]", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
        (tmp_path / "uv.lock").write_text("lock v1", encoding="utf-8")
        fp1 = build_behavior_fingerprint(repo_root=tmp_path)
        (tmp_path / "uv.lock").write_text("lock v2", encoding="utf-8")
        fp2 = build_behavior_fingerprint(repo_root=tmp_path)
        assert fp1["fingerprint"] != fp2["fingerprint"]

    def test_payload_is_canonical_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Payload canonical JSON is sorted and compact."""
        from tests.ci.behavior_environment import build_behavior_fingerprint

        (tmp_path / "uv.lock").write_text("x", encoding="utf-8")
        (tmp_path / "pyproject.toml").write_text("x", encoding="utf-8")
        monkeypatch.chdir(tmp_path)
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

        # Write a simple passing test so pytest actually executes
        pass_test = tmp_path / "test_pass.py"
        pass_test.write_text(
            "def test_ok():\n    assert True\n",
            encoding="utf-8",
        )
        junit_path = str(tmp_path / "junit.xml")
        exit_code = run_pytest(
            ["-q", "--tb=short", f"--junitxml={junit_path}", str(pass_test)],
            env={"PYTHONPATH": str(tmp_path)},
            junit_path=junit_path,
            telemetry_path=str(tmp_path / "telemetry.json"),
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
            outcomes_path=str(tmp_path / "outcomes.json"),
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
        assert telemetry["execution_status"] == "completed"
        assert telemetry["counts_authoritative"]
        assert telemetry["producer_authoritative"]
        assert telemetry["pytest_exit_code"] == 0
        assert telemetry["tests_passed"] > 0
        assert exit_code == 0

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
        junit_path = str(tmp_path / "junit.xml")
        exit_code = run_pytest(
            ["-q", "--tb=short", f"--junitxml={junit_path}", str(test_file)],
            env={"PYTHONPATH": str(tmp_path)},
            junit_path=junit_path,
            telemetry_path=str(tmp_path / "telemetry.json"),
            stdout_path=str(tmp_path / "stdout.txt"),
            stderr_path=str(tmp_path / "stderr.txt"),
            outcomes_path=str(tmp_path / "outcomes.json"),
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
        assert telemetry["execution_status"] == "completed"
        assert not telemetry["producer_authoritative"]
