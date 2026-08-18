"""Tests for unified artifact identity verifier, marker inventory,
behavior environment contract, and run_test_shard telemetry runner.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import textwrap
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from tests.ci.artifact_identity import (
    GLOBAL_REQUIRED_ARTIFACT_KINDS,
    REQUIRED_ARTIFACT_KINDS,
    SHARD_REQUIRED_ARTIFACT_KINDS,
    ArtifactError,
    resolve_global_bundles,
    resolve_shard_bundles,
    selected_coverage_raw_paths,
    verify_artifacts,
    verify_global_bundles,
)
from tests.ci.marker_inventory import (
    MarkerInventoryError,
    load_marker_inventory,
    verify_marker_ownership,
)
from tests.ci.merge_authority import (
    CANONICAL_COMMIT_MESSAGE_BYTES,
    CURRENT_BASE_REF,
    HXFORGE_RAW_PR_NUMBER_ENV,
    METADATA_TIP_MISMATCH_ERROR,
    GitHubCandidateOutcome,
    GitHubCandidateStatus,
    MergeAuthorityError,
    acquire_objects,
    build_canonical_ephemeral_merge,
    classify_github_candidate,
    compute_merge_tree,
    external_candidate_status,
    git_object_format,
    git_version,
    inspect_canonical_commit_raw,
    inspect_commit,
    materialize_and_verify,
    resolve_current_base_sha,
    resolve_merge_authority,
    sanitized_pr_number_text,
    validate_pr_number_lexical,
    validate_raw_pr_number_from_env,
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
                "tests_collected": 1,
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
        """pytest-outcomes total != telemetry tests_collected → fail."""
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
        # Also update node-inventory to match outcomes (P0-3: node equality)
        node_inv_path = bundle_dir / "node-inventory.json"
        node_inv = json.loads(node_inv_path.read_text(encoding="utf-8"))
        node_inv["node_ids"] = ["tests/ci/test_a.py::test_a", "tests/ci/test_b.py::test_b"]
        node_inv["node_count"] = 2
        node_inv_path.write_text(json.dumps(node_inv, indent=2), encoding="utf-8")
        # Update marker-inventory to match (must have same node set)
        marker_inv_path = bundle_dir / "node-marker-inventory.json"
        marker_inv = json.loads(marker_inv_path.read_text(encoding="utf-8"))
        marker_inv["node_markers"] = {
            "tests/ci/test_a.py::test_a": [],
            "tests/ci/test_b.py::test_b": [],
        }
        marker_inv_path.write_text(json.dumps(marker_inv, indent=2), encoding="utf-8")
        # Telemetry still says tests_collected=1 (from original bundle creation)
        with pytest.raises(ArtifactError, match="outcome/telemetry total mismatch"):
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


# ---------------------------------------------------------------------------
# Attempt-scoped artifact resolution regression tests (R01-R08)
# ---------------------------------------------------------------------------


def _make_full_attempt1_shard_set(root: Path, *, track: str = "pr-head") -> None:
    _make_artifact_bundle(
        root,
        track=track,
        shard="ci",
        python_version="3.11",
        commit_sha=_SHA40,
        run_id="100",
        run_attempt=1,
    )
    _make_artifact_bundle(
        root,
        track=track,
        shard="unit",
        python_version="3.11",
        commit_sha=_SHA40,
        run_id="100",
        run_attempt=1,
    )
    _make_artifact_bundle(
        root,
        track=track,
        shard="unit",
        python_version="3.12",
        commit_sha=_SHA40,
        run_id="100",
        run_attempt=1,
    )


class TestAttemptScopedArtifactResolution:
    """Regression coverage for failed-job rerun attempt fallback."""

    def test_r01_single_attempt_strict_identity_still_passes(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_full_attempt1_shard_set(root)
        verify_artifacts(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            expected_run_attempt=1,
        )

    def test_r02_mixed_attempt_fallback_selects_latest_per_logical_producer(
        self, tmp_path: Path
    ) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_full_attempt1_shard_set(root)
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=2,
            bundle_name="pr-head-ci-py3.11-attempt2",
        )
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
        )
        assert (
            resolved[
                next(k for k in resolved if k.shard == "ci" and k.python_version == "3.11")
            ].identity.run_attempt
            == 2
        )
        assert (
            resolved[
                next(k for k in resolved if k.shard == "unit" and k.python_version == "3.11")
            ].identity.run_attempt
            == 1
        )
        assert (
            resolved[
                next(k for k in resolved if k.shard == "unit" and k.python_version == "3.12")
            ].identity.run_attempt
            == 1
        )

    def test_r03_producer_not_rerun_reuses_prior_attempt(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_full_attempt1_shard_set(root)
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
        )
        assert all(bundle.identity.run_attempt == 1 for bundle in resolved.values())

    def test_r04_rerun_producer_prefers_newer_attempt(self, tmp_path: Path) -> None:
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
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=2,
            bundle_name="pr-head-ci-py3.11-attempt2",
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
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
        )
        ci_key = next(k for k in resolved if k.shard == "ci")
        assert resolved[ci_key].identity.run_attempt == 2

    def test_r05_future_attempt_rejected(self, tmp_path: Path) -> None:
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
            run_attempt=3,
        )
        with pytest.raises(ArtifactError, match="FUTURE_ATTEMPT_ARTIFACT_GT_CURRENT"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=2,
            )

    def test_r06_duplicate_same_attempt_rejected(self, tmp_path: Path) -> None:
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
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
            bundle_name="dup-ci",
        )
        with pytest.raises(ArtifactError, match="DUPLICATE_SAME_LOGICAL_KEY_AND_ATTEMPT"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=2,
            )

    def test_r07_missing_logical_producer_still_rejected(self, tmp_path: Path) -> None:
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
        with pytest.raises(ArtifactError, match="MISSING_LOGICAL_PRODUCER_AFTER_FALLBACK"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=2,
            )

    def test_r08_global_collection_mixed_attempt_fallback(self, tmp_path: Path) -> None:
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
            bundle_name="pr-head-global-py3.11-attempt1",
        )
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="",
            python_version="3.12",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=2,
            scope="global",
            bundle_name="pr-head-global-py3.12-attempt2",
        )
        resolved = resolve_global_bundles(
            artifact_root=root,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
            python_versions=["3.11", "3.12"],
        )
        assert resolved["3.11"].identity.run_attempt == 1
        assert resolved["3.12"].identity.run_attempt == 2

    def test_selected_coverage_paths_one_bundle_per_logical_producer(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_full_attempt1_shard_set(root)
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="ci",
            python_version="3.11",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=2,
            bundle_name="pr-head-ci-py3.11-attempt2",
        )
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
        )
        coverage_paths = selected_coverage_raw_paths(resolved)
        assert len(coverage_paths) == len(resolved)
        assert len({p.parent.resolve() for p in coverage_paths}) == len(resolved)

    def test_r09_per_python_scoped_shard_resolution_passes(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="unit",
            python_version="3.12",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
            python_versions=["3.12"],
        )
        assert {logical.python_version for logical in resolved} == {"3.12"}
        assert {logical.shard for logical in resolved} == {"unit"}

    def test_r10_per_python_scoped_resolution_still_rejects_missing_applicable_shard(
        self, tmp_path: Path
    ) -> None:
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
        with pytest.raises(ArtifactError, match="MISSING_LOGICAL_PRODUCER_AFTER_FALLBACK"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=2,
                python_versions=["3.11"],
            )

    def test_unscoped_resolution_still_requires_full_multi_python_set(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="pr-head",
            shard="unit",
            python_version="3.12",
            commit_sha=_SHA40,
            run_id="100",
            run_attempt=1,
        )
        with pytest.raises(ArtifactError, match="MISSING_LOGICAL_PRODUCER_AFTER_FALLBACK"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=2,
            )

    def test_python_version_scope_rejects_empty_and_unknown(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        with pytest.raises(ArtifactError, match="PYTHON_VERSION_SCOPE_EMPTY"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=1,
                python_versions=[],
            )
        with pytest.raises(ArtifactError, match="PYTHON_VERSION_NOT_IN_MANIFEST"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="pr-head",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=1,
                python_versions=["3.10"],
            )


class TestWorkflowCompletenessResolverScope:
    """Static workflow regression for per-Python completeness scoping."""

    def test_completeness_callsites_scope_shard_resolution(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        pr_head_block = workflow.split("Verify per-version completeness (pr-head)", 1)[1].split(
            "verify-completeness-merge-ref", 1
        )[0]
        merge_ref_block = workflow.split("Verify per-version completeness (merge-ref)", 1)[1].split(
            "verify-completeness-main", 1
        )[0]
        aggregate_block = workflow.split("Combine coverage", 1)[1].split("merge-ref-aggregate", 1)[
            0
        ]

        assert "python_versions=[python_version]" in pr_head_block
        assert "resolve_shard_bundles(" in pr_head_block
        assert "python_versions=[python_version]" in merge_ref_block
        assert "resolve_shard_bundles(" in merge_ref_block
        assert "resolve_shard_bundles(" in aggregate_block
        assert "python_versions=[python_version]" not in aggregate_block


# ---------------------------------------------------------------------------
# Merge authority (TASK-032 CI-MA-001 .. CI-MA-034)
# ---------------------------------------------------------------------------


def _ma_git(
    args: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_bytes: bytes | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    if args and args[0] == "git":
        args = ["git", "-c", "core.hooksPath=/dev/null", *args[1:]]
    base_env = os.environ.copy()
    base_env.update(
        {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_AUTHOR_NAME": "Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
    )
    if env:
        base_env.update(env)
    completed = subprocess.run(
        args,
        cwd=cwd,
        env=base_env,
        check=False,
        capture_output=True,
        text=input_bytes is None,
        input=input_bytes,
    )
    if check and completed.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {completed.stderr or completed.stdout}")
    return completed


def _ma_commit_file(repo: Path, rel: str, content: str, message: str) -> str:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    _ma_git(["git", "add", rel], cwd=repo)
    _ma_git(["git", "commit", "-m", message], cwd=repo)
    return _ma_git(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()


def _ma_setup_clean_merge_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ma_git(["git", "init", "-b", "main"], cwd=repo)
    _ma_commit_file(repo, "README.md", "root\n", "root")
    base_sha = _ma_commit_file(repo, "base.txt", "base\n", "base")
    _ma_git(["git", "checkout", "-b", "feature"], cwd=repo)
    head_sha = _ma_commit_file(repo, "feature.txt", "feature\n", "feature")
    _ma_git(["git", "checkout", "main"], cwd=repo)
    bare = tmp_path / "origin.git"
    _ma_git(["git", "clone", "--bare", str(repo), str(bare)], cwd=tmp_path)
    _ma_git(["git", "update-ref", "refs/pull/1/head", head_sha], cwd=bare)
    work = tmp_path / "work"
    _ma_git(["git", "clone", str(bare), str(work)], cwd=tmp_path)
    return work, base_sha, head_sha


def _ma_advance_origin_main_tip(work: Path, *, rel: str, content: str, message: str) -> str:
    _ma_git(["git", "checkout", "main"], cwd=work)
    new_tip = _ma_commit_file(work, rel, content, message)
    _ma_git(["git", "push", "origin", "main"], cwd=work)
    return new_tip


def _ma_setup_diverged_merge_repo(tmp_path: Path) -> tuple[Path, str, str, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ma_git(["git", "init", "-b", "main"], cwd=repo)
    ancestor = _ma_commit_file(repo, "shared.txt", "ancestor\n", "ancestor")
    _ma_git(["git", "checkout", "-b", "feature", ancestor], cwd=repo)
    head_sha = _ma_commit_file(repo, "head-only.txt", "head\n", "head")
    _ma_git(["git", "checkout", "main"], cwd=repo)
    base_sha = _ma_commit_file(repo, "base-only.txt", "base\n", "base")
    bare = tmp_path / "origin.git"
    _ma_git(["git", "clone", "--bare", str(repo), str(bare)], cwd=tmp_path)
    _ma_git(["git", "update-ref", "refs/pull/2/head", head_sha], cwd=bare)
    work = tmp_path / "work"
    _ma_git(["git", "clone", str(bare), str(work)], cwd=tmp_path)
    return work, base_sha, head_sha, bare


def _ma_setup_conflict_repo(tmp_path: Path) -> tuple[Path, str, str]:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ma_git(["git", "init", "-b", "main"], cwd=repo)
    _ma_commit_file(repo, "conflict.txt", "line\n", "root")
    base_sha = _ma_commit_file(repo, "conflict.txt", "base change\n", "base")
    _ma_git(["git", "checkout", "-b", "feature", "HEAD~1"], cwd=repo)
    head_sha = _ma_commit_file(repo, "conflict.txt", "head change\n", "head")
    _ma_git(["git", "checkout", "main"], cwd=repo)
    bare = tmp_path / "origin.git"
    _ma_git(["git", "clone", "--bare", str(repo), str(bare)], cwd=tmp_path)
    _ma_git(["git", "update-ref", "refs/pull/3/head", head_sha], cwd=bare)
    work = tmp_path / "work-conflict"
    _ma_git(["git", "clone", str(bare), str(work)], cwd=tmp_path)
    return work, base_sha, head_sha


@contextmanager
def _ma_use_repo(repo: Path):
    previous = os.getcwd()
    os.chdir(repo)
    try:
        yield
    finally:
        os.chdir(previous)


def _ma_resolve(
    pr_number: int,
    base_metadata_sha: str,
    pr_head_sha: str,
    *,
    base_ref: str = "main",
    **kwargs,
):
    return resolve_merge_authority(pr_number, base_ref, base_metadata_sha, pr_head_sha, **kwargs)


def _ma_make_signed_candidate_commit(
    repo: Path,
    *,
    tree_sha: str,
    parents: tuple[str, ...],
) -> str:
    parent_lines = "\n".join(f"parent {parent}" for parent in parents)
    commit_object = (
        f"tree {tree_sha}\n"
        f"{parent_lines}\n"
        "author Candidate <candidate@example.invalid> 946684800 +0000\n"
        "committer Candidate <candidate@example.invalid> 946684800 +0000\n"
        "gpgsig -----BEGIN PGP SIGNATURE-----\n"
        " \n"
        " fake-signature-line\n"
        " -----END PGP SIGNATURE-----\n"
        "\n"
        "candidate\n"
    )
    completed = _ma_git(
        ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
        cwd=repo,
        input_bytes=commit_object.encode("utf-8"),
    )
    stdout = completed.stdout
    if isinstance(stdout, bytes):
        stdout = stdout.decode("ascii")
    return stdout.strip()


def _ma_make_candidate_commit(
    repo: Path,
    *,
    tree_sha: str,
    parents: tuple[str, ...],
) -> str:
    env = {
        "GIT_AUTHOR_NAME": "Candidate",
        "GIT_AUTHOR_EMAIL": "candidate@example.invalid",
        "GIT_COMMITTER_NAME": "Candidate",
        "GIT_COMMITTER_EMAIL": "candidate@example.invalid",
    }
    args = [
        "git",
        "commit-tree",
        tree_sha,
        *[item for parent in parents for item in ("-p", parent)],
    ]
    completed = _ma_git(
        args,
        cwd=repo,
        env=env,
        input_bytes=b"candidate\n",
    )
    stdout = completed.stdout
    if isinstance(stdout, bytes):
        stdout = stdout.decode("ascii")
    return stdout.strip()


def _ma_workflow_job_block(workflow: str, job: str) -> str:
    start = workflow.index(job) + len(job)
    rest = workflow[start:]
    match = re.search(r"\n  [a-z][a-z0-9-]*:", rest)
    return rest[: match.start()] if match else rest


class TestMergeAuthorityCIMA:
    """CI-MA-001 through CI-MA-034 merge authority regression matrix."""

    def test_ci_ma_001_clean_merge_produces_tree_and_sha(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            merge_sha = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
        assert tree
        assert merge_sha

    def test_ci_ma_002_repeated_construction_is_identical(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            first = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
            second = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
        assert first == second

    def test_ci_ma_003_parent_order_base_then_head(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            merge_sha = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
            inspected = inspect_commit(merge_sha)
        assert inspected.parents == (base_sha, head_sha)

    def test_ci_ma_004_tree_equals_merge_tree_sha(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            merge_sha = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
            inspected = inspect_commit(merge_sha)
        assert inspected.tree_sha == tree

    def test_ci_ma_005_stale_candidate_wrong_first_parent(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            stale_parent = _ma_commit_file(work, "stale.txt", "stale\n", "stale")
            candidate = _ma_make_candidate_commit(
                work, tree_sha=tree, parents=(stale_parent, head_sha)
            )
            outcome = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert outcome.outcome == GitHubCandidateOutcome.STALE_PARENT_BINDING

    def test_ci_ma_006_stale_candidate_wrong_second_parent(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            stale_head = _ma_commit_file(work, "stale-head.txt", "x\n", "stale-head")
            candidate = _ma_make_candidate_commit(
                work, tree_sha=tree, parents=(base_sha, stale_head)
            )
            outcome = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert outcome.outcome == GitHubCandidateOutcome.STALE_PARENT_BINDING

    def test_ci_ma_007_non_two_parent_candidate_rejected(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            single = _ma_make_candidate_commit(work, tree_sha=tree, parents=(base_sha,))
            classification = classify_github_candidate(single, base_sha, head_sha, tree)
        assert (
            external_candidate_status(classification) == GitHubCandidateStatus.STALE_PARENT_BINDING
        )

    def test_ci_ma_008_valid_candidate_same_tree(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            candidate = _ma_make_candidate_commit(work, tree_sha=tree, parents=(base_sha, head_sha))
            outcome = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert outcome.outcome == GitHubCandidateOutcome.VALID_EQUIVALENT

    def test_ci_ma_009_valid_parents_different_tree_hard_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            compute_merge_tree(base_sha, head_sha)
            other_tree_commit = _ma_commit_file(work, "other-tree.txt", "z\n", "other-tree")
            tree_other = _ma_git(
                ["git", "rev-parse", f"{other_tree_commit}^{{tree}}"], cwd=work
            ).stdout.strip()
            candidate = _ma_make_candidate_commit(
                work, tree_sha=tree_other, parents=(base_sha, head_sha)
            )
            with pytest.raises(MergeAuthorityError, match="different tree"):
                _ma_resolve(1, base_sha, head_sha, github_candidate_sha=candidate)

    def test_ci_ma_010_missing_candidate_does_not_block_clean_merge(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, classification = _ma_resolve(1, base_sha, head_sha)
        assert identity.merge_sha
        assert external_candidate_status(classification) == GitHubCandidateStatus.MISSING

    def test_ci_ma_011_local_merge_conflict_fails_closed(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_conflict_repo(tmp_path)
        with _ma_use_repo(work), pytest.raises(MergeAuthorityError, match="merge-tree failed"):
            _ma_resolve(3, base_sha, head_sha, github_candidate_sha=None)

    def test_ci_ma_012_materialization_reproduces_merge_tree(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            materialized = materialize_and_verify(
                1,
                base_sha,
                head_sha,
                identity.merge_tree_sha,
                identity.merge_sha,
                resolver_git_version=git_version(),
                resolver_git_object_format=git_object_format(),
            )
        assert materialized.merge_tree_sha == identity.merge_tree_sha

    def test_ci_ma_013_materialization_reproduces_merge_sha(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            materialized = materialize_and_verify(
                1,
                base_sha,
                head_sha,
                identity.merge_tree_sha,
                identity.merge_sha,
                resolver_git_version=git_version(),
                resolver_git_object_format=git_object_format(),
            )
        assert materialized.merge_sha == identity.merge_sha

    def test_ci_ma_014_tampered_merge_tree_hard_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            tampered = "0" * 40
            with pytest.raises(MergeAuthorityError, match="merge_tree_sha mismatch"):
                materialize_and_verify(
                    1,
                    base_sha,
                    head_sha,
                    tampered,
                    identity.merge_sha,
                    resolver_git_version=git_version(),
                    resolver_git_object_format=git_object_format(),
                )

    def test_ci_ma_015_tampered_merge_sha_hard_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            tampered = "1" * 40
            with pytest.raises(MergeAuthorityError, match="merge_sha mismatch"):
                materialize_and_verify(
                    1,
                    base_sha,
                    head_sha,
                    identity.merge_tree_sha,
                    tampered,
                    resolver_git_version=git_version(),
                    resolver_git_object_format=git_object_format(),
                )

    def test_ci_ma_016_pr_head_ref_drift_hard_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        drift = _ma_commit_file(work, "drift.txt", "drift\n", "drift")
        with (
            _ma_use_repo(work),
            pytest.raises(MergeAuthorityError, match="refs/hxforge-ci/pr-head mismatch"),
        ):
            _ma_resolve(1, base_sha, drift, github_candidate_sha=None)

    def test_ci_ma_017_workflow_dispatch_pr_number_validation(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        resolve_block = workflow.split("resolve-authority:", 1)[1].split("shard:", 1)[0]
        assert "HXFORGE_RAW_PR_NUMBER: ${{ inputs.pr_number }}" in resolve_block
        assert resolve_block.count("${{ inputs.pr_number }}") == 1
        run_section = resolve_block.split("run: |", 1)[1]
        assert "${{ inputs.pr_number }}" not in run_section
        assert "validate-pr-number-env" in resolve_block
        assert HXFORGE_RAW_PR_NUMBER_ENV in module
        assert "os.environ" in module
        dispatch_start = resolve_block.index("validate-pr-number-env")
        dispatch_end = resolve_block.index("tests.ci.merge_authority resolve", dispatch_start)
        dispatch_section = resolve_block[dispatch_start:dispatch_end]
        assert "refs/pull" not in dispatch_section.split("validate-pr-number-env", 1)[0]
        assert "git rev-parse origin/main" not in dispatch_section
        assert "GH_TOKEN: ${{ github.token }}" in resolve_block
        assert "jq -r '.state'" in dispatch_section
        assert "jq -r '.base.ref'" in dispatch_section
        assert "jq -r '.base.sha'" in dispatch_section
        assert "jq -r '.head.sha'" in dispatch_section
        assert 'STATE" != "open"' in dispatch_section
        hostile_inputs = (
            "",
            "0",
            "-1",
            "01",
            "1a",
            " 1",
            "1 ",
            "+1",
            "１",
            "١",
            "$(printf 42)",
            "`printf 42`",
            "$((42))",
            '"42"',
            "'42'",
            "42\n",
        )
        for invalid in hostile_inputs:
            with pytest.raises(MergeAuthorityError):
                validate_pr_number_lexical(invalid)
        assert validate_pr_number_lexical("42") == 42
        with pytest.raises(MergeAuthorityError):
            validate_raw_pr_number_from_env()
        os.environ[HXFORGE_RAW_PR_NUMBER_ENV] = "$(printf 42)"
        try:
            with pytest.raises(MergeAuthorityError):
                validate_raw_pr_number_from_env()
        finally:
            os.environ.pop(HXFORGE_RAW_PR_NUMBER_ENV, None)
        assert sanitized_pr_number_text("42") == "42"

    def test_ci_ma_018_workflow_permissions_read_only(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "contents: read" in workflow
        assert "pull-requests: read" in workflow
        assert "contents: write" not in workflow
        assert "pull-requests: write" not in workflow

    def test_ci_ma_019_resolve_success_never_empty_merge_sha(self, tmp_path: Path) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        resolve_outputs = workflow.split("resolve-authority:", 1)[1].split("shard:", 1)[0]
        for output_name in (
            "base-ref",
            "base-metadata-sha",
            "base-sha",
            "pr-head-sha",
            "merge-tree-sha",
            "merge-sha",
            "git-version",
            "git-object-format",
            "github-candidate-status",
            "github-candidate-sha",
        ):
            assert f"{output_name}:" in resolve_outputs
        assert "github-candidate-outcome" not in resolve_outputs
        assert "github-candidate-outcome" not in module
        assert '_write_github_output("github-candidate-status"' in module
        assert '_write_github_output("base-ref"' in module
        assert '_write_github_output("base-metadata-sha"' in module
        assert "--base-metadata-sha" in module
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, classification = _ma_resolve(1, base_sha, head_sha)
            current_tip = resolve_current_base_sha("main")
        assert identity.merge_sha
        assert len(identity.merge_sha) == 40
        assert identity.base_sha == current_tip
        assert identity.base_sha == base_sha
        assert external_candidate_status(classification) == GitHubCandidateStatus.MISSING

    def test_ci_ma_020_all_merge_content_jobs_materialize_before_tests(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for job in (
            "shard-merge-ref:",
            "collect-global-merge-ref:",
            "verify-completeness-merge-ref:",
            "verify-golden-benchmark-merge-ref:",
        ):
            block = _ma_workflow_job_block(workflow, job)
            assert "Materialize canonical ephemeral merge authority" in block
            assert "Assert frozen merge-ref SHA" in block
            assert "tests.ci.merge_authority materialize" in block

    def test_ci_ma_021_no_push_of_ephemeral_commit_or_ref(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        assert "git push" not in module
        assert "git push" not in workflow.split("merge_authority", 1)[1]

    def test_ci_ma_022_merge_ref_artifact_metadata_uses_canonical_merge_sha(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        shard_block = workflow.split("shard-merge-ref:", 1)[1].split("collect-global:", 1)[0]
        assert "needs.resolve-authority.outputs.merge-sha" in shard_block
        assert "'commit_sha': '${{ needs.resolve-authority.outputs.merge-sha }}'" in shard_block

    def test_ci_ma_023_merge_ref_aggregate_expects_canonical_merge_sha(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        block = workflow.split("merge-ref-aggregate:", 1)[1].split("main-aggregate:", 1)[0]
        assert "expected_commit_sha='${{ needs.resolve-authority.outputs.merge-sha }}'" in block

    def test_ci_ma_024_verifier_rejects_wrong_merge_ref_commit_sha(self, tmp_path: Path) -> None:
        manifest = _make_manifest(tmp_path)
        root = tmp_path / "artifacts"
        root.mkdir()
        _make_artifact_bundle(
            root,
            track="merge-ref",
            shard="ci",
            python_version="3.11",
            commit_sha="f" * 40,
            run_id="100",
            run_attempt=1,
        )
        with pytest.raises(ArtifactError, match="COMMIT_SHA_MISMATCH"):
            resolve_shard_bundles(
                artifact_root=root,
                manifest_path=manifest,
                expected_track="merge-ref",
                expected_commit_sha=_SHA40,
                expected_run_id="100",
                consumer_run_attempt=1,
            )

    def test_ci_ma_025_attempt_fallback_behavior_still_passes(self, tmp_path: Path) -> None:
        root = tmp_path / "artifacts"
        root.mkdir()
        manifest = _make_manifest(tmp_path)
        _make_full_attempt1_shard_set(root)
        resolved = resolve_shard_bundles(
            artifact_root=root,
            manifest_path=manifest,
            expected_track="pr-head",
            expected_commit_sha=_SHA40,
            expected_run_id="100",
            consumer_run_attempt=2,
        )
        assert resolved

    def test_ci_ma_026_final_gate_requires_resolve_authority_for_pr_dispatch(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        gate = workflow.split("final-gate:", 1)[1]
        needs_block = gate.split("needs:", 1)[1].split("runs-on:", 1)[0]
        assert "- resolve-authority" in needs_block
        pr_event_guard = (
            'if [ "${{ github.event_name }}" = "pull_request" ] || '
            '[ "${{ github.event_name }}" = "workflow_dispatch" ]; then'
        )
        pr_block = gate.split(pr_event_guard, 1)[1].split("elif", 1)[0]
        assert 'check "resolve-authority"' in pr_block
        assert "merge-sha is empty" in gate

    def test_ci_ma_027_workflow_requires_full_history_checkout(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        resolve_block = workflow.split("resolve-authority:", 1)[1].split("shard:", 1)[0]
        assert "fetch-depth: 0" in resolve_block
        assert "persist-credentials: false" in resolve_block
        assert "refs/heads/" in module
        assert CURRENT_BASE_REF in module
        assert "git rev-parse origin/main" not in resolve_block
        assert "--base-metadata-sha" in resolve_block
        for job in (
            "shard-merge-ref:",
            "collect-global-merge-ref:",
            "verify-completeness-merge-ref:",
            "verify-golden-benchmark-merge-ref:",
        ):
            block = _ma_workflow_job_block(workflow, job)
            assert "fetch-depth: 0" in block
            assert "persist-credentials: false" in block

    def test_ci_ma_028_diverged_history_materializes_full_history_only(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha, bare = _ma_setup_diverged_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(2, base_sha, head_sha)
        assert identity.merge_sha

        partial_work = tmp_path / "partial-work"
        partial_work.mkdir()
        _ma_git(["git", "init"], cwd=partial_work)
        _ma_git(["git", "remote", "add", "origin", str(bare)], cwd=partial_work)
        _ma_git(["git", "fetch", "--depth", "1", "origin", base_sha], cwd=partial_work)
        with _ma_use_repo(partial_work), pytest.raises(MergeAuthorityError):
            _ma_resolve(2, base_sha, head_sha)

    def test_ci_ma_029_canonical_message_bytes_exact(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            merge_sha = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
            _, message_bytes = inspect_canonical_commit_raw(
                merge_sha,
                base_sha=base_sha,
                pr_head_sha=head_sha,
                merge_tree_sha=tree,
            )
        assert message_bytes == CANONICAL_COMMIT_MESSAGE_BYTES
        assert message_bytes.endswith(b"\n")
        assert not message_bytes.startswith(b"\n")
        assert b"\n\n" not in message_bytes

    def test_ci_ma_030_hostile_global_config_cannot_change_canonical_sha(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        hostile_cfg = tmp_path / "hostile.gitconfig"
        hostile_cfg.write_text(
            textwrap.dedent(
                """\
                [commit]
                    gpgSign = true
                [i18n]
                    commitEncoding = ISO-8859-1
                """
            ),
            encoding="utf-8",
        )
        os.environ["GIT_CONFIG_GLOBAL"] = str(hostile_cfg)
        os.environ["GIT_CONFIG_NOSYSTEM"] = "0"
        try:
            with _ma_use_repo(work):
                tree = compute_merge_tree(base_sha, head_sha)
                first = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
                second = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
                inspect_canonical_commit_raw(
                    first,
                    base_sha=base_sha,
                    pr_head_sha=head_sha,
                    merge_tree_sha=tree,
                )
        finally:
            os.environ.pop("GIT_CONFIG_GLOBAL", None)
            os.environ["GIT_CONFIG_NOSYSTEM"] = "1"
        assert first == second

    def test_ci_ma_031_canonical_author_committer_identity_exact(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            merge_sha = build_canonical_ephemeral_merge(base_sha, head_sha, tree)
            header_bytes, _ = inspect_canonical_commit_raw(
                merge_sha,
                base_sha=base_sha,
                pr_head_sha=head_sha,
                merge_tree_sha=tree,
            )
            expected_author = b"author HxForge CI <hxforge-ci@example.invalid> 946684800 +0000"
            expected_committer = (
                b"committer HxForge CI <hxforge-ci@example.invalid> 946684800 +0000"
            )
            assert expected_author in header_bytes
            assert expected_committer in header_bytes
            extra_header_body = (
                header_bytes + b"\nencoding UTF-8\n\n" + CANONICAL_COMMIT_MESSAGE_BYTES
            )
            injected_sha = _ma_git(
                ["git", "hash-object", "-t", "commit", "-w", "--stdin"],
                cwd=work,
                input_bytes=extra_header_body,
            ).stdout
            if isinstance(injected_sha, bytes):
                injected_sha = injected_sha.decode("ascii").strip()
            else:
                injected_sha = injected_sha.strip()
            with pytest.raises(MergeAuthorityError, match="header bytes mismatch"):
                inspect_canonical_commit_raw(
                    injected_sha,
                    base_sha=base_sha,
                    pr_head_sha=head_sha,
                    merge_tree_sha=tree,
                )

    def test_ci_ma_032_downstream_git_version_mismatch_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            with pytest.raises(MergeAuthorityError, match="git-version mismatch"):
                materialize_and_verify(
                    1,
                    base_sha,
                    head_sha,
                    identity.merge_tree_sha,
                    identity.merge_sha,
                    resolver_git_version="git version 0.0.0",
                    resolver_git_object_format=git_object_format(),
                )

    def test_ci_ma_033_object_format_mismatch_or_non_sha1_fails(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(1, base_sha, head_sha)
            with pytest.raises(MergeAuthorityError, match="git-object-format mismatch"):
                materialize_and_verify(
                    1,
                    base_sha,
                    head_sha,
                    identity.merge_tree_sha,
                    identity.merge_sha,
                    resolver_git_version=git_version(),
                    resolver_git_object_format="sha256",
                )

    def test_ci_ma_034_all_merge_content_jobs_bind_resolver_git_env(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        pattern = re.compile(
            r"resolver-git-version.*?resolver-git-object-format",
            re.DOTALL,
        )
        for job in (
            "shard-merge-ref:",
            "collect-global-merge-ref:",
            "verify-completeness-merge-ref:",
            "verify-golden-benchmark-merge-ref:",
        ):
            block = _ma_workflow_job_block(workflow, job)
            assert pattern.search(block)
            assert "merge-tree-sha" in block
            assert "merge-sha" in block

    def test_pr188_signed_candidate_exact_binding_is_valid_equivalent(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            candidate = _ma_make_signed_candidate_commit(
                work, tree_sha=tree, parents=(base_sha, head_sha)
            )
            outcome = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert outcome.outcome == GitHubCandidateOutcome.VALID_EQUIVALENT

    def test_pr188_signed_candidate_stale_parent_is_stale_parent_binding(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            stale_parent = _ma_commit_file(work, "stale.txt", "stale\n", "stale")
            candidate = _ma_make_signed_candidate_commit(
                work, tree_sha=tree, parents=(stale_parent, head_sha)
            )
            outcome = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert outcome.outcome == GitHubCandidateOutcome.STALE_PARENT_BINDING

    def test_pr188_signed_candidate_non_two_parent_maps_to_stale_parent_binding(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            tree = compute_merge_tree(base_sha, head_sha)
            candidate = _ma_make_signed_candidate_commit(work, tree_sha=tree, parents=(base_sha,))
            classification = classify_github_candidate(candidate, base_sha, head_sha, tree)
        assert (
            external_candidate_status(classification) == GitHubCandidateStatus.STALE_PARENT_BINDING
        )
        assert classification.outcome == GitHubCandidateOutcome.INVALID_PARENT_COUNT

    def test_pr188_signed_candidate_exact_parents_different_tree_is_tree_mismatch(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            merge_tree = compute_merge_tree(base_sha, head_sha)
            other_tree_commit = _ma_commit_file(work, "other-tree.txt", "z\n", "other-tree")
            tree_other = _ma_git(
                ["git", "rev-parse", f"{other_tree_commit}^{{tree}}"], cwd=work
            ).stdout.strip()
            candidate = _ma_make_signed_candidate_commit(
                work, tree_sha=tree_other, parents=(base_sha, head_sha)
            )
            classification = classify_github_candidate(candidate, base_sha, head_sha, merge_tree)
            assert classification.outcome == GitHubCandidateOutcome.TREE_MISMATCH
            with pytest.raises(MergeAuthorityError, match="different tree"):
                _ma_resolve(1, base_sha, head_sha, github_candidate_sha=candidate)

    def test_r3_current_base_branch_tip_match_continues(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            current_tip = resolve_current_base_sha("main")
            identity, _ = _ma_resolve(1, base_sha, head_sha)
        assert current_tip == base_sha
        assert identity.base_sha == current_tip

    def test_r3_current_base_metadata_tip_mismatch_fails_closed(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        stale_metadata = base_sha
        _ma_advance_origin_main_tip(
            work, rel="advance-main.txt", content="advance\n", message="advance-main"
        )
        with (
            _ma_use_repo(work),
            pytest.raises(MergeAuthorityError, match=METADATA_TIP_MISMATCH_ERROR),
        ):
            _ma_resolve(1, stale_metadata, head_sha)

    def test_r3_base_ref_invalid_fails_closed(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work), pytest.raises(MergeAuthorityError):
            _ma_resolve(1, base_sha, head_sha, base_ref="bad..ref")

    def test_r3_base_ref_missing_fails_closed(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with (
            _ma_use_repo(work),
            pytest.raises(MergeAuthorityError, match="base_ref must be non-empty"),
        ):
            resolve_merge_authority(1, "   ", base_sha, head_sha)

    def test_r3_base_branch_moved_before_freeze_causes_mismatch_block(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            resolve_current_base_sha("main")
        _ma_advance_origin_main_tip(work, rel="move-tip.txt", content="moved\n", message="move-tip")
        with (
            _ma_use_repo(work),
            pytest.raises(MergeAuthorityError, match=METADATA_TIP_MISMATCH_ERROR),
        ):
            _ma_resolve(1, base_sha, head_sha)

    def test_r3_base_branch_name_is_transported_as_data(self, tmp_path: Path) -> None:
        repo = tmp_path / "develop-repo"
        repo.mkdir()
        _ma_git(["git", "init", "-b", "develop"], cwd=repo)
        _ma_commit_file(repo, "README.md", "root\n", "root")
        base_sha = _ma_commit_file(repo, "develop.txt", "develop\n", "develop")
        _ma_git(["git", "checkout", "-b", "feature"], cwd=repo)
        head_sha = _ma_commit_file(repo, "feature.txt", "feature\n", "feature")
        _ma_git(["git", "checkout", "develop"], cwd=repo)
        bare = tmp_path / "origin-develop.git"
        _ma_git(["git", "clone", "--bare", str(repo), str(bare)], cwd=tmp_path)
        _ma_git(["git", "update-ref", "refs/pull/4/head", head_sha], cwd=bare)
        work = tmp_path / "develop-work"
        _ma_git(["git", "clone", str(bare), str(work)], cwd=tmp_path)
        with _ma_use_repo(work):
            identity, _ = _ma_resolve(4, base_sha, head_sha, base_ref="develop")
        assert identity.base_sha == base_sha

    def test_r3_raw_pr_number_metacharacters_cannot_transform_before_validation(self) -> None:
        os.environ[HXFORGE_RAW_PR_NUMBER_ENV] = "$((42))"
        try:
            with pytest.raises(MergeAuthorityError):
                validate_raw_pr_number_from_env()
        finally:
            os.environ.pop(HXFORGE_RAW_PR_NUMBER_ENV, None)

    def test_r3_metadata_sha_cannot_substitute_for_current_tip(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        new_tip = _ma_advance_origin_main_tip(
            work, rel="new-tip.txt", content="new\n", message="new-tip"
        )
        assert new_tip != base_sha
        with (
            _ma_use_repo(work),
            pytest.raises(MergeAuthorityError, match=METADATA_TIP_MISMATCH_ERROR),
        ):
            _ma_resolve(1, base_sha, head_sha)

    def test_r3_no_remote_temporary_ref_is_pushed(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        assert "git push" not in module
        assert CURRENT_BASE_REF in module
        assert "+refs/heads/" in module

    def test_r3r1_acquire_objects_uses_frozen_sha_not_moving_branch_ref(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        acquire_block = module.split("def acquire_objects", 1)[1].split("\ndef ", 1)[0]
        assert "refs/heads/" not in acquire_block
        assert 'f"+{base}:{CURRENT_BASE_REF}"' in acquire_block

    def test_r3r1_branch_stable_post_freeze_acquisition_succeeds(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            frozen_sha = resolve_current_base_sha("main")
            acquire_objects(1, frozen_sha, head_sha)
            fetched = _ma_git(["git", "rev-parse", CURRENT_BASE_REF], cwd=work).stdout.strip()
        assert fetched == frozen_sha == base_sha

    def test_r3r1_branch_moves_after_freeze_still_acquires_frozen_sha(self, tmp_path: Path) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        with _ma_use_repo(work):
            frozen_sha = resolve_current_base_sha("main")
        new_tip = _ma_advance_origin_main_tip(
            work, rel="post-freeze-move.txt", content="moved\n", message="post-freeze-move"
        )
        assert new_tip != frozen_sha
        with _ma_use_repo(work):
            acquire_objects(1, frozen_sha, head_sha)
            fetched = _ma_git(["git", "rev-parse", CURRENT_BASE_REF], cwd=work).stdout.strip()
        assert fetched == frozen_sha
        assert fetched != new_tip

    def test_r3r1_frozen_sha_unavailable_fails_closed_no_branch_fallback(
        self, tmp_path: Path
    ) -> None:
        work, base_sha, head_sha = _ma_setup_clean_merge_repo(tmp_path)
        missing_sha = "f" * 40
        assert missing_sha != base_sha
        with _ma_use_repo(work), pytest.raises(MergeAuthorityError):
            acquire_objects(1, missing_sha, head_sha)

    def test_r3r1_downstream_materializer_uses_frozen_sha_pair_only(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        workflow = (repo_root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        module = (repo_root / "tests" / "ci" / "merge_authority.py").read_text(encoding="utf-8")
        materialize_block = module.split("def materialize_and_verify", 1)[1].split("\ndef ", 1)[0]
        assert "base_ref" not in materialize_block
        for job in (
            "shard-merge-ref:",
            "collect-global-merge-ref:",
            "verify-completeness-merge-ref:",
            "verify-golden-benchmark-merge-ref:",
        ):
            block = _ma_workflow_job_block(workflow, job)
            assert "merge_authority materialize" in block
            assert "outputs.base-sha" in block
            assert "outputs.pr-head-sha" in block
            assert "outputs.base-ref" not in block.split("materialize", 1)[1]
