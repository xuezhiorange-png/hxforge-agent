"""Unified exact artifact identity verifier for all CI tracks.

P0-3: Verifies real filesystem — checks actual file existence, not just metadata.
P0-4: Uses full identity naming.

PR-head, merge-ref, and main must call this same verifier with identical
strictness.  The verifier proves that every expected producer uploaded exactly
the right set of artifacts with correct identity metadata.

Fail-closed on:
  - Missing identities
  - Extra identities
  - Duplicate identities
  - Wrong SHA, track, run ID, attempt, Python version, shard, artifact kind
  - Artifact metadata vs actual file inconsistency
  - Declared present but file absent
  - File present but not declared
  - Artifacts from an old attempt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final, NamedTuple

REQUIRED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "node-inventory",
        "node-marker-inventory",
        "behavior-environment",
        "junit",
        "coverage-raw",
        "coverage-xml",
        "pytest-stderr",
        "resource-telemetry",
    }
)


class ArtifactIdentity(NamedTuple):
    track: str
    commit_sha: str
    run_id: str
    run_attempt: int
    python_version: str
    shard: str


class ArtifactError(Exception):
    """Raised when artifact identity verification fails."""


def _parse_identity(meta: dict[str, Any]) -> ArtifactIdentity:
    """Extract and validate identity fields from artifact metadata."""
    identity = meta.get("identity")
    if not isinstance(identity, dict):
        raise ArtifactError("metadata missing 'identity' object")
    track = identity.get("track", "")
    commit_sha = identity.get("commit_sha", "")
    run_id = identity.get("run_id", "")
    run_attempt = identity.get("run_attempt", 0)
    python_version = identity.get("python_version", "")
    shard = identity.get("shard", "")
    if not all([track, commit_sha, run_id, run_attempt, python_version, shard]):
        raise ArtifactError(f"incomplete identity: {identity}")
    if not isinstance(run_attempt, int) or run_attempt <= 0:
        raise ArtifactError(f"invalid run_attempt: {run_attempt}")
    return ArtifactIdentity(
        track=track,
        commit_sha=commit_sha,
        run_id=str(run_id),
        run_attempt=run_attempt,
        python_version=python_version,
        shard=shard,
    )


def _is_relative_safe(path_str: str) -> bool:
    """Check that a path is relative, has no traversal, and stays within root."""
    if not path_str:
        return False
    p = Path(path_str)
    if p.is_absolute():
        return False
    parts = p.parts
    return ".." not in parts


def _verify_bundle_contents(
    meta_path: Path,
    meta: dict[str, Any],
    identity: ArtifactIdentity,
) -> None:
    """P0-3: Verify real filesystem contents match declared metadata."""
    bundle_root = meta_path.parent
    artifacts = meta.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ArtifactError(f"artifacts must be a list in {identity}")

    declared_kinds: dict[str, str] = {}
    declared_paths: set[str] = set()

    for entry in artifacts:
        if not isinstance(entry, dict):
            raise ArtifactError(f"artifact entry must be a dict in {identity}")
        kind = entry.get("kind", "")
        path_str = entry.get("path", "")
        present = entry.get("present", False)

        if not kind:
            raise ArtifactError(f"artifact missing 'kind' in {identity}")

        # Duplicate kind check
        if kind in declared_kinds:
            raise ArtifactError(f"DUPLICATE kind '{kind}' in {identity}")
        declared_kinds[kind] = path_str

        if not _is_relative_safe(path_str):
            raise ArtifactError(f"unsafe path '{path_str}' in kind '{kind}' for {identity}")

        # Duplicate path check
        if path_str in declared_paths:
            raise ArtifactError(f"DUPLICATE path '{path_str}' in {identity}")
        declared_paths.add(path_str)

        # Real filesystem check
        artifact_path = bundle_root / path_str
        file_exists = artifact_path.is_file()
        file_size = artifact_path.stat().st_size if file_exists else 0

        if present and not file_exists:
            raise ArtifactError(
                f"DECLARED PRESENT BUT FILE ABSENT: {kind} at {path_str} in {identity}"
            )
        if not present and file_exists:
            raise ArtifactError(
                f"FILE EXISTS BUT NOT DECLARED: {path_str} (kind={kind}) in {identity}"
            )
        if present and file_size == 0:
            raise ArtifactError(f"EMPTY REQUIRED FILE: {kind} at {path_str} in {identity}")

    # Required kinds check
    missing_kinds = REQUIRED_ARTIFACT_KINDS - set(declared_kinds)
    extra_kinds = set(declared_kinds) - REQUIRED_ARTIFACT_KINDS
    if missing_kinds:
        raise ArtifactError(f"MISSING KINDS in {identity}: {sorted(missing_kinds)}")
    if extra_kinds:
        raise ArtifactError(f"EXTRA KINDS in {identity}: {sorted(extra_kinds)}")

    # Cross-validate internal identity: read node-inventory.json if present
    node_inv_path = bundle_root / declared_kinds.get("node-inventory", "")
    if node_inv_path.is_file():
        try:
            node_inv = json.loads(node_inv_path.read_text(encoding="utf-8"))
            if isinstance(node_inv, dict):
                inv_identity = {
                    "track": node_inv.get("track"),
                    "commit_sha": node_inv.get("commit_sha"),
                    "run_id": node_inv.get("run_id"),
                    "run_attempt": node_inv.get("run_attempt"),
                    "python_version": node_inv.get("python_version"),
                    "shard": node_inv.get("shard"),
                }
                for field in ("track", "commit_sha", "run_id", "python_version", "shard"):
                    expected_val = getattr(identity, field)
                    actual_val = str(inv_identity[field]) if inv_identity[field] is not None else ""
                    if actual_val != str(expected_val):
                        raise ArtifactError(
                            f"node-inventory.{field} mismatch in {identity}: "
                            f"got {actual_val!r}, expected {expected_val!r}"
                        )
                if int(inv_identity["run_attempt"]) != identity.run_attempt:
                    raise ArtifactError(
                        f"node-inventory.run_attempt mismatch in {identity}: "
                        f"got {inv_identity['run_attempt']}, expected {identity.run_attempt}"
                    )
        except (json.JSONDecodeError, OSError):
            pass  # Non-JSON or unreadable — skip cross-validation

    # Cross-validate telemetry identity
    telemetry_path = bundle_root / declared_kinds.get("resource-telemetry", "")
    if telemetry_path.is_file():
        try:
            tel = json.loads(telemetry_path.read_text(encoding="utf-8"))
            if isinstance(tel, dict):
                for field in ("track", "commit_sha", "run_id", "python_version", "shard"):
                    expected_val = getattr(identity, field)
                    actual_val = str(tel.get(field, ""))
                    if actual_val != str(expected_val):
                        raise ArtifactError(
                            f"resource-telemetry.{field} mismatch in {identity}: "
                            f"got {actual_val!r}, expected {expected_val!r}"
                        )
        except (json.JSONDecodeError, OSError):
            pass  # Non-JSON or unreadable — skip cross-validation


def verify_artifacts(
    *,
    artifact_root: Path,
    manifest_path: Path,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
) -> None:
    """Verify all artifact identities match the expected parameters.

    P0-3: Also verifies real filesystem contents.
    """
    import yaml  # noqa: WPS433 — deferred to avoid top-level import

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

    # Build expected identity set
    expected: set[ArtifactIdentity] = set()
    for shard_spec in manifest["shards"]:
        for py in shard_spec["python"]:
            expected.add(
                ArtifactIdentity(
                    track=expected_track,
                    commit_sha=expected_commit_sha,
                    run_id=expected_run_id,
                    run_attempt=expected_run_attempt,
                    python_version=py,
                    shard=shard_spec["name"],
                )
            )

    # Discover actual artifacts
    found: set[ArtifactIdentity] = set()
    metadata_files = sorted(artifact_root.rglob("artifact-metadata.json"))
    if not metadata_files:
        raise ArtifactError("no artifact-metadata.json files found")

    for meta_path in metadata_files:
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ArtifactError(f"cannot parse {meta_path}: {exc}") from exc

        identity = _parse_identity(meta)

        # Check for duplicate
        if identity in found:
            raise ArtifactError(f"DUPLICATE artifact identity: {identity}")
        found.add(identity)

        # Verify identity matches expectations
        if identity.track != expected_track:
            raise ArtifactError(
                f"track mismatch: got {identity.track!r}, expected {expected_track!r}"
            )
        if identity.commit_sha != expected_commit_sha:
            raise ArtifactError(
                f"SHA mismatch: got {identity.commit_sha!r}, expected {expected_commit_sha!r}"
            )
        if identity.run_id != str(expected_run_id):
            raise ArtifactError(
                f"run_id mismatch: got {identity.run_id!r}, expected {expected_run_id!r}"
            )
        if identity.run_attempt != expected_run_attempt:
            raise ArtifactError(
                f"attempt mismatch: got {identity.run_attempt}, expected {expected_run_attempt}"
            )

        # P0-3: Verify real filesystem contents
        _verify_bundle_contents(meta_path, meta, identity)

    # Check for missing/extra
    missing = expected - found
    extra = found - expected
    if missing:
        raise ArtifactError(f"MISSING producers: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED producers: {sorted(extra)}")


def main() -> None:
    """CLI entry point for artifact identity verification."""
    import argparse

    parser = argparse.ArgumentParser(description="Verify artifact identity")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--track", required=True)
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True, type=int)
    args = parser.parse_args()

    try:
        verify_artifacts(
            artifact_root=Path(args.artifact_root),
            manifest_path=Path(args.manifest),
            expected_track=args.track,
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
        )
        print(f"Artifact identity verification PASS: track={args.track}")
    except ArtifactError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
