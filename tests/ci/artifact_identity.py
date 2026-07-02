"""Unified exact artifact identity verifier for all CI tracks.

P0-1: Per-kind artifact policy (empty stderr OK, non-empty inventory required).
P0-2: Full behavior-environment digest recomputation + cross-fingerprint.
Fail-closed JSON parsing, symlink detection, exact file set proof.
"""

from __future__ import annotations

import hashlib
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
        "pytest-outcomes",
        "resource-telemetry",
    }
)

# P0-1: Per-kind policy
ARTIFACT_KIND_POLICIES: Final[dict[str, dict[str, bool]]] = {
    "node-inventory": {"required": True, "allow_empty": False},
    "node-marker-inventory": {"required": True, "allow_empty": False},
    "behavior-environment": {"required": True, "allow_empty": False},
    "junit": {"required": True, "allow_empty": False},
    "coverage-raw": {"required": True, "allow_empty": False},
    "coverage-xml": {"required": True, "allow_empty": False},
    "pytest-stderr": {"required": True, "allow_empty": True},
    "pytest-outcomes": {"required": True, "allow_empty": False},
    "resource-telemetry": {"required": True, "allow_empty": False},
}

_BUNDLE_CONTROL_FILES: Final[frozenset[str]] = frozenset({"artifact-metadata.json"})


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
    if not path_str:
        return False
    p = Path(path_str)
    if p.is_absolute():
        return False
    return ".." not in p.parts


def _read_json_strict(path: Path, label: str, identity: ArtifactIdentity) -> dict[str, Any]:
    """Read a JSON file with fail-closed parsing."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"CORRUPT JSON in {label} for {identity}: {exc}") from exc
    except OSError as exc:
        raise ArtifactError(f"UNREADABLE {label} for {identity}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ArtifactError(f"{label} root must be a JSON object for {identity}")
    return raw


def _verify_bundle_contents(
    meta_path: Path,
    meta: dict[str, Any],
    identity: ArtifactIdentity,
) -> None:
    """Verify exact file set + per-kind policy + fail-closed cross-validation."""
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
        if kind in declared_kinds:
            raise ArtifactError(f"DUPLICATE kind '{kind}' in {identity}")
        declared_kinds[kind] = path_str

        if not _is_relative_safe(path_str):
            raise ArtifactError(f"unsafe path '{path_str}' in kind '{kind}' for {identity}")
        if path_str in declared_paths:
            raise ArtifactError(f"DUPLICATE path '{path_str}' in {identity}")
        declared_paths.add(path_str)

        artifact_path = bundle_root / path_str

        if artifact_path.is_symlink():
            raise ArtifactError(f"SYMLINK detected: {path_str} in {identity}")

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

        # P0-1: Per-kind empty check
        policy = ARTIFACT_KIND_POLICIES.get(kind, {"allow_empty": False})
        if present and file_size == 0 and not policy.get("allow_empty", False):
            raise ArtifactError(f"EMPTY REQUIRED FILE: {kind} at {path_str} in {identity}")

    # Required kinds check
    missing_kinds = REQUIRED_ARTIFACT_KINDS - set(declared_kinds)
    extra_kinds = set(declared_kinds) - REQUIRED_ARTIFACT_KINDS
    if missing_kinds:
        raise ArtifactError(f"MISSING KINDS in {identity}: {sorted(missing_kinds)}")
    if extra_kinds:
        raise ArtifactError(f"EXTRA KINDS in {identity}: {sorted(extra_kinds)}")

    # Prove actual files == declared files
    actual_files: set[str] = set()
    for path in bundle_root.iterdir():
        if path.is_file():
            rel = path.relative_to(bundle_root).as_posix()
            if rel not in _BUNDLE_CONTROL_FILES:
                actual_files.add(rel)

    unexpected = actual_files - declared_paths
    if unexpected:
        raise ArtifactError(f"UNDECLARED FILES in bundle for {identity}: {sorted(unexpected)}")
    missing = declared_paths - actual_files
    if missing:
        raise ArtifactError(f"DECLARED BUT ABSENT FILES for {identity}: {sorted(missing)}")

    # ── Cross-validation ────────────────────────────────────────────────────
    node_inv_name = declared_kinds.get("node-inventory", "")
    node_inv_path = bundle_root / node_inv_name
    node_inv: dict[str, Any] | None = None
    if node_inv_path.is_file():
        node_inv = _read_json_strict(node_inv_path, "node-inventory.json", identity)
        for field in ("track", "commit_sha", "run_id", "python_version", "shard"):
            expected_val = getattr(identity, field)
            actual_val = str(node_inv.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"node-inventory.{field} mismatch in {identity}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(node_inv.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"node-inventory.run_attempt mismatch in {identity}")
        scope = node_inv.get("collection_scope", "")
        shard_val = node_inv.get("shard")
        if scope == "global" and shard_val is not None:
            raise ArtifactError(
                f"node-inventory: global scope but shard={shard_val!r} in {identity}"
            )
        if scope == "shard" and (not isinstance(shard_val, str) or not shard_val):
            raise ArtifactError(f"node-inventory: shard scope but missing shard in {identity}")

    # marker-inventory
    marker_name = declared_kinds.get("node-marker-inventory", "")
    marker_path = bundle_root / marker_name
    if marker_path.is_file():
        marker_inv = _read_json_strict(marker_path, "node-marker-inventory.json", identity)
        for field in ("track", "commit_sha", "run_id", "python_version", "shard"):
            expected_val = getattr(identity, field)
            actual_val = str(marker_inv.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"marker-inventory.{field} mismatch in {identity}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(marker_inv.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"marker-inventory.run_attempt mismatch in {identity}")
        if node_inv is not None:
            inv_nodes = set(node_inv.get("node_ids", []))
            marker_nodes = set(marker_inv.get("node_markers", {}).keys())
            if inv_nodes != marker_nodes:
                raise ArtifactError(f"marker/inventory node set mismatch in {identity}")

    # P0-2: behavior-environment.json — full digest recomputation
    beh_name = declared_kinds.get("behavior-environment", "")
    beh_path = bundle_root / beh_name
    beh_fingerprint: str | None = None
    if beh_path.is_file():
        beh = _read_json_strict(beh_path, "behavior-environment.json", identity)
        # Schema validation
        expected_beh_keys = {"schema_version", "payload", "canonical_json_sha256"}
        actual_beh_keys = set(beh.keys())
        if actual_beh_keys != expected_beh_keys:
            raise ArtifactError(
                f"behavior-environment schema keys mismatch in {identity}: "
                f"extra={sorted(actual_beh_keys - expected_beh_keys)}, "
                f"missing={sorted(expected_beh_keys - actual_beh_keys)}"
            )
        if beh.get("schema_version") != "1":
            raise ArtifactError(f"behavior-environment schema_version must be '1' in {identity}")
        payload = beh.get("payload")
        if not isinstance(payload, dict):
            raise ArtifactError(f"behavior-environment payload must be object in {identity}")
        digest_stored = beh.get("canonical_json_sha256", "")
        if not digest_stored.startswith("sha256:"):
            raise ArtifactError(f"behavior-environment: invalid digest format in {identity}")
        stored_hex = digest_stored[7:]
        if len(stored_hex) != 64:
            raise ArtifactError(f"behavior-environment: invalid digest length in {identity}")
        # Recompute canonical digest
        from tests.ci.behavior_environment import canonicalize_behavior_payload

        canonical = canonicalize_behavior_payload(payload)
        recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if recomputed != stored_hex:
            raise ArtifactError(
                f"behavior-environment: digest mismatch in {identity}: "
                f"recomputed={recomputed}, stored={stored_hex}"
            )
        beh_fingerprint = recomputed

    # resource-telemetry.json — P0-5: full authority check
    tel_name = declared_kinds.get("resource-telemetry", "")
    tel_path = bundle_root / tel_name
    if tel_path.is_file():
        tel = _read_json_strict(tel_path, "resource-telemetry.json", identity)
        for field in ("track", "commit_sha", "run_id", "python_version", "shard"):
            expected_val = getattr(identity, field)
            actual_val = str(tel.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"resource-telemetry.{field} mismatch in {identity}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(tel.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"resource-telemetry.run_attempt mismatch in {identity}")
        # P0-5: Strict authority checks
        exec_status = tel.get("execution_status", "")
        if exec_status != "completed":
            raise ArtifactError(
                f"resource-telemetry: execution_status={exec_status!r} "
                f"(expected 'completed') in {identity}"
            )
        if tel.get("junit_parse_status") != "available":
            raise ArtifactError(
                f"resource-telemetry: junit_parse_status != available in {identity}"
            )
        if not tel.get("counts_authoritative"):
            raise ArtifactError(f"resource-telemetry: counts_authoritative=false in {identity}")
        if tel.get("resource_measurement_status") != "available":
            raise ArtifactError(
                f"resource-telemetry: resource_measurement_status != available in {identity}"
            )
        if int(tel.get("pytest_exit_code", -1)) != 0:
            raise ArtifactError(
                f"resource-telemetry: pytest_exit_code={tel.get('pytest_exit_code')} "
                f"(expected 0) in {identity}"
            )

    # P0-2: Cross-fingerprint — behavior digest == node inventory fingerprint
    if beh_fingerprint is not None and node_inv is not None:
        inv_fp = node_inv.get("behavior_fingerprint_sha256", "")
        if inv_fp != beh_fingerprint:
            raise ArtifactError(
                f"behavior/node fingerprint mismatch in {identity}: "
                f"beh={beh_fingerprint}, inv={inv_fp}"
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
    """Verify all artifact identities match the expected parameters."""
    import yaml  # noqa: WPS433

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
    metadata_files = sorted(artifact_root.rglob("artifact-metadata.json"))
    if not metadata_files:
        raise ArtifactError("no artifact-metadata.json files found")

    for meta_path in metadata_files:
        meta = _read_json_strict(
            meta_path,
            "artifact-metadata.json",
            ArtifactIdentity("", "", "", 0, "", ""),
        )
        identity = _parse_identity(meta)

        if identity in found:
            raise ArtifactError(f"DUPLICATE artifact identity: {identity}")
        found.add(identity)

        if identity.track != expected_track:
            raise ArtifactError(f"track mismatch: {identity.track!r} vs {expected_track!r}")
        if identity.commit_sha != expected_commit_sha:
            raise ArtifactError(f"SHA mismatch: {identity.commit_sha!r} vs {expected_commit_sha!r}")
        if identity.run_id != str(expected_run_id):
            raise ArtifactError(f"run_id mismatch: {identity.run_id!r} vs {expected_run_id!r}")
        if identity.run_attempt != expected_run_attempt:
            raise ArtifactError(
                f"attempt mismatch: {identity.run_attempt} vs {expected_run_attempt}"
            )

        _verify_bundle_contents(meta_path, meta, identity)

    missing = expected - found
    extra = found - expected
    if missing:
        raise ArtifactError(f"MISSING producers: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED producers: {sorted(extra)}")


def main() -> None:
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
