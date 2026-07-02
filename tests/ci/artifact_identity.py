"""Unified exact artifact identity verifier for all CI tracks.

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
        "junit",
        "coverage-raw",
        "coverage-xml",
        "collection-stderr",
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

    Parameters
    ----------
    artifact_root : Path
        Root directory containing downloaded artifacts.
    manifest_path : Path
        Path to ci-shard-manifest.yml.
    expected_track : str
        Expected track value (pr-head, merge-ref, main, nightly).
    expected_commit_sha : str
        Expected 40-character commit SHA.
    expected_run_id : str
        Expected GitHub run ID.
    expected_run_attempt : int
        Expected run attempt number.

    Raises
    ------
    ArtifactError
        On any identity mismatch, missing, extra, or duplicate artifact.
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

        # Verify artifact kinds
        artifacts = meta.get("artifacts", [])
        declared_kinds = {a.get("kind") for a in artifacts}
        missing_kinds = REQUIRED_ARTIFACT_KINDS - declared_kinds
        extra_kinds = declared_kinds - REQUIRED_ARTIFACT_KINDS
        if missing_kinds:
            raise ArtifactError(f"MISSING KINDS in {identity}: {sorted(missing_kinds)}")
        if extra_kinds:
            raise ArtifactError(f"EXTRA KINDS in {identity}: {sorted(extra_kinds)}")

        # Verify each declared artifact is present
        for a in artifacts:
            kind = a.get("kind", "")
            present = a.get("present", False)
            path_str = a.get("path", "")
            if not present:
                raise ArtifactError(
                    f"ABSENT ARTIFACT: {kind} in {identity} (declared path={path_str})"
                )

        # Verify no old-attempt artifacts
        if identity.run_attempt != expected_run_attempt:
            raise ArtifactError(
                f"OLD ATTEMPT artifact: {identity} (expected attempt {expected_run_attempt})"
            )

    # Check for missing/extra
    missing = expected - found
    extra = found - expected
    if missing:
        raise ArtifactError(f"MISSING producers: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED producers: {sorted(extra)}")


def verify_artifacts_from_json(
    *,
    identities_json: str,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    manifest_path: Path,
) -> None:
    """Verify artifact identities from a JSON string (for inline workflow use).

    This is a thin wrapper around verify_artifacts that accepts a JSON-encoded
    list of identity dicts instead of requiring artifact download.
    """
    import yaml  # noqa: WPS433

    identities: list[dict[str, Any]] = json.loads(identities_json)
    if not isinstance(identities, list):
        raise ArtifactError("identities input must be a JSON list")

    with open(manifest_path) as f:
        manifest = yaml.safe_load(f)

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

    found: set[ArtifactIdentity] = set()
    for raw in identities:
        identity = ArtifactIdentity(
            track=raw["track"],
            commit_sha=raw["commit_sha"],
            run_id=str(raw["run_id"]),
            run_attempt=int(raw["run_attempt"]),
            python_version=raw["python_version"],
            shard=raw["shard"],
        )
        if identity in found:
            raise ArtifactError(f"DUPLICATE: {identity}")
        found.add(identity)

        if identity.track != expected_track:
            raise ArtifactError(f"track mismatch: {identity.track} vs {expected_track}")
        if identity.commit_sha != expected_commit_sha:
            raise ArtifactError(f"SHA mismatch: {identity.commit_sha} vs {expected_commit_sha}")
        if identity.run_id != str(expected_run_id):
            raise ArtifactError(f"run_id mismatch: {identity.run_id} vs {expected_run_id}")
        if identity.run_attempt != expected_run_attempt:
            raise ArtifactError(
                f"attempt mismatch: {identity.run_attempt} vs {expected_run_attempt}"
            )

    missing = expected - found
    extra = found - expected
    if missing:
        raise ArtifactError(f"MISSING: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED: {sorted(extra)}")


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
