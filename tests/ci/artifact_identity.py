"""Unified exact artifact identity verifier for all CI tracks.

P0-1: Per-kind artifact policy (empty stderr OK, non-empty inventory required).
P0-2: Full behavior-environment digest recomputation + cross-fingerprint.
P0-3: pytest-outcomes schema validation + cross-validation with telemetry.
P0-5: Scope-aware — separate shard vs global bundle verification.
Fail-closed JSON parsing, symlink detection, exact file set proof.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Final, Literal, NamedTuple

# ── Shard required kinds ─────────────────────────────────────────────────────
SHARD_REQUIRED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
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

# ── Global required kinds ────────────────────────────────────────────────────
GLOBAL_REQUIRED_ARTIFACT_KINDS: Final[frozenset[str]] = frozenset(
    {
        "node-inventory",
        "node-marker-inventory",
        "behavior-environment",
        "collection-stderr",
    }
)

# Backward compat alias
REQUIRED_ARTIFACT_KINDS = SHARD_REQUIRED_ARTIFACT_KINDS

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
    "collection-stderr": {"required": True, "allow_empty": True},
}

_BUNDLE_CONTROL_FILES: Final[frozenset[str]] = frozenset({"artifact-metadata.json"})

_OUTCOME_VALID_VALUES = frozenset({"passed", "failed", "skipped", "xfailed", "xpassed"})


class ArtifactIdentity(NamedTuple):
    track: str
    commit_sha: str
    run_id: str
    run_attempt: int
    python_version: str
    collection_scope: Literal["global", "shard"]
    shard: str | None


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
    collection_scope = identity.get("collection_scope", "shard")
    shard = identity.get("shard")

    if collection_scope not in ("global", "shard"):
        raise ArtifactError(f"invalid collection_scope: {collection_scope!r}")

    required_fields = [track, commit_sha, run_id, python_version]
    if not all(required_fields):
        raise ArtifactError(f"incomplete identity: {identity}")
    if not isinstance(run_attempt, int) or run_attempt <= 0:
        raise ArtifactError(f"invalid run_attempt: {run_attempt}")

    if collection_scope == "shard":
        if not isinstance(shard, str) or not shard:
            raise ArtifactError(f"shard scope requires non-empty shard: {identity}")
    else:
        # global scope: shard must be None or absent
        if shard is not None and shard != "":
            raise ArtifactError(f"global scope must not have shard={shard!r}: {identity}")
        shard = None

    return ArtifactIdentity(
        track=track,
        commit_sha=commit_sha,
        run_id=str(run_id),
        run_attempt=run_attempt,
        python_version=python_version,
        collection_scope=collection_scope,
        shard=shard,
    )


def _is_relative_safe(path_str: str) -> bool:
    if not path_str:
        return False
    p = Path(path_str)
    if p.is_absolute():
        return False
    return ".." not in p.parts


def _read_json_strict(path: Path, label: str, context: str) -> dict[str, Any]:
    """Read a JSON file with fail-closed parsing."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ArtifactError(f"CORRUPT JSON in {label} for {context}: {exc}") from exc
    except OSError as exc:
        raise ArtifactError(f"UNREADABLE {label} for {context}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ArtifactError(f"{label} root must be a JSON object for {context}")
    return raw


def _verify_outcomes_schema(
    outcomes_data: dict[str, Any],
    context: str,
    *,
    node_inv_data: dict[str, Any] | None = None,
) -> dict[str, int]:
    """Validate pytest-outcomes.json schema. Returns aggregated counts.

    P0-3: Enforces strict set equality between outcomes keys,
    collection_complete list, and node_inventory.node_ids.
    """
    if outcomes_data.get("schema_version") != "1":
        raise ArtifactError(f"pytest-outcomes schema_version != '1' in {context}")
    outcomes_map = outcomes_data.get("outcomes")
    if not isinstance(outcomes_map, dict):
        raise ArtifactError(f"pytest-outcomes.outcomes must be object in {context}")
    total = outcomes_data.get("total")
    if not isinstance(total, int) or total != len(outcomes_map):
        raise ArtifactError(
            f"pytest-outcomes.total={total} != len(outcomes)={len(outcomes_map)} in {context}"
        )

    outcome_node_ids: set[str] = set()
    counts = {
        "tests_passed": 0,
        "tests_failed": 0,
        "tests_skipped": 0,
        "tests_xfailed": 0,
        "tests_xpassed": 0,
    }
    seen: set[str] = set()
    for node_id, outcome_val in outcomes_map.items():
        if not isinstance(node_id, str) or not node_id:
            raise ArtifactError(f"pytest-outcomes: invalid node_id in {context}")
        if node_id in seen:
            raise ArtifactError(f"pytest-outcomes: DUPLICATE node_id '{node_id}' in {context}")
        seen.add(node_id)
        outcome_node_ids.add(node_id)
        if outcome_val not in _OUTCOME_VALID_VALUES:
            raise ArtifactError(
                f"pytest-outcomes: invalid outcome '{outcome_val}' for '{node_id}' in {context}"
            )
        key = f"tests_{outcome_val}"
        counts[key] += 1

    # Validate collection_complete: list, strings only, unique, non-empty items
    cc = outcomes_data.get("collection_complete")
    if not isinstance(cc, list):
        raise ArtifactError(f"pytest-outcomes.collection_complete must be a list in {context}")
    cc_node_ids: set[str] = set()
    for i, item in enumerate(cc):
        if not isinstance(item, str) or not item:
            raise ArtifactError(
                f"pytest-outcomes.collection_complete[{i}] is not a non-empty string in {context}"
            )
        if item in cc_node_ids:
            raise ArtifactError(
                f"pytest-outcomes.collection_complete: DUPLICATE node_id '{item}' in {context}"
            )
        cc_node_ids.add(item)

    # P0-3: Exact set equality between outcomes and collection_complete
    if outcome_node_ids != cc_node_ids:
        missing_in_cc = outcome_node_ids - cc_node_ids
        extra_in_cc = cc_node_ids - outcome_node_ids
        raise ArtifactError(
            f"pytest-outcomes: outcomes/collection_complete node set mismatch in {context}: "
            f"missing_in_cc={sorted(missing_in_cc)}, extra_in_cc={sorted(extra_in_cc)}"
        )

    # P0-3: Also validate against node-inventory if provided
    if node_inv_data is not None:
        inv_node_ids = set(node_inv_data.get("node_ids", []))
        if inv_node_ids != outcome_node_ids:
            missing_in_inv = outcome_node_ids - inv_node_ids
            extra_in_inv = inv_node_ids - outcome_node_ids
            raise ArtifactError(
                f"pytest-outcomes: outcomes/node-inventory node set mismatch in {context}: "
                f"missing_in_inv={sorted(missing_in_inv)}, extra_in_inv={sorted(extra_in_inv)}"
            )

    return counts


def _verify_bundle_contents(
    meta_path: Path,
    meta: dict[str, Any],
    identity: ArtifactIdentity,
) -> None:
    """Verify exact file set + per-kind policy + fail-closed cross-validation."""
    bundle_root = meta_path.parent
    context = str(identity)
    artifacts = meta.get("artifacts", [])
    if not isinstance(artifacts, list):
        raise ArtifactError(f"artifacts must be a list in {context}")

    required_kinds = (
        GLOBAL_REQUIRED_ARTIFACT_KINDS
        if identity.collection_scope == "global"
        else SHARD_REQUIRED_ARTIFACT_KINDS
    )

    declared_kinds: dict[str, str] = {}
    declared_paths: set[str] = set()

    for entry in artifacts:
        if not isinstance(entry, dict):
            raise ArtifactError(f"artifact entry must be a dict in {context}")
        kind = entry.get("kind", "")
        path_str = entry.get("path", "")
        present = entry.get("present", False)

        if not kind:
            raise ArtifactError(f"artifact missing 'kind' in {context}")
        if kind in declared_kinds:
            raise ArtifactError(f"DUPLICATE kind '{kind}' in {context}")
        declared_kinds[kind] = path_str

        if not _is_relative_safe(path_str):
            raise ArtifactError(f"unsafe path '{path_str}' in kind '{kind}' for {context}")
        if path_str in declared_paths:
            raise ArtifactError(f"DUPLICATE path '{path_str}' in {context}")
        declared_paths.add(path_str)

        artifact_path = bundle_root / path_str

        if artifact_path.is_symlink():
            raise ArtifactError(f"SYMLINK detected: {path_str} in {context}")

        file_exists = artifact_path.is_file()
        file_size = artifact_path.stat().st_size if file_exists else 0

        if present and not file_exists:
            raise ArtifactError(
                f"DECLARED PRESENT BUT FILE ABSENT: {kind} at {path_str} in {context}"
            )
        if not present and file_exists:
            raise ArtifactError(
                f"FILE EXISTS BUT NOT DECLARED: {path_str} (kind={kind}) in {context}"
            )

        # P0-1: Per-kind empty check
        policy = ARTIFACT_KIND_POLICIES.get(kind, {"allow_empty": False})
        if present and file_size == 0 and not policy.get("allow_empty", False):
            raise ArtifactError(f"EMPTY REQUIRED FILE: {kind} at {path_str} in {context}")

    # Required kinds check
    missing_kinds = required_kinds - set(declared_kinds)
    extra_kinds = set(declared_kinds) - required_kinds
    if missing_kinds:
        raise ArtifactError(f"MISSING KINDS in {context}: {sorted(missing_kinds)}")
    if extra_kinds:
        raise ArtifactError(f"EXTRA KINDS in {context}: {sorted(extra_kinds)}")

    # Prove actual files == declared files
    actual_files: set[str] = set()
    for path in bundle_root.iterdir():
        if path.is_file():
            rel = path.relative_to(bundle_root).as_posix()
            if rel not in _BUNDLE_CONTROL_FILES:
                actual_files.add(rel)

    unexpected = actual_files - declared_paths
    if unexpected:
        raise ArtifactError(f"UNDECLARED FILES in bundle for {context}: {sorted(unexpected)}")
    missing = declared_paths - actual_files
    if missing:
        raise ArtifactError(f"DECLARED BUT ABSENT FILES for {context}: {sorted(missing)}")

    # ── Cross-validation ────────────────────────────────────────────────────
    node_inv_name = declared_kinds.get("node-inventory", "")
    node_inv_path = bundle_root / node_inv_name
    node_inv: dict[str, Any] | None = None
    if node_inv_path.is_file():
        node_inv = _read_json_strict(node_inv_path, "node-inventory.json", context)
        for field in ("track", "commit_sha", "run_id", "python_version"):
            expected_val = getattr(identity, field)
            actual_val = str(node_inv.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"node-inventory.{field} mismatch in {context}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(node_inv.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"node-inventory.run_attempt mismatch in {context}")
        scope = node_inv.get("collection_scope", "")
        shard_val = node_inv.get("shard")
        if identity.collection_scope == "global":
            if scope != "global":
                raise ArtifactError(
                    f"node-inventory: expected global scope, got {scope!r} in {context}"
                )
            if shard_val is not None:
                raise ArtifactError(
                    f"node-inventory: global scope but shard={shard_val!r} in {context}"
                )
        else:
            if scope != "shard":
                raise ArtifactError(
                    f"node-inventory: expected shard scope, got {scope!r} in {context}"
                )
            if not isinstance(shard_val, str) or not shard_val:
                raise ArtifactError(f"node-inventory: shard scope but missing shard in {context}")

    # marker-inventory
    marker_name = declared_kinds.get("node-marker-inventory", "")
    marker_path = bundle_root / marker_name
    if marker_path.is_file():
        marker_inv = _read_json_strict(marker_path, "node-marker-inventory.json", context)
        for field in ("track", "commit_sha", "run_id", "python_version"):
            expected_val = getattr(identity, field)
            actual_val = str(marker_inv.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"marker-inventory.{field} mismatch in {context}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(marker_inv.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"marker-inventory.run_attempt mismatch in {context}")
        if node_inv is not None:
            inv_nodes = set(node_inv.get("node_ids", []))
            marker_nodes = set(marker_inv.get("node_markers", {}).keys())
            if inv_nodes != marker_nodes:
                raise ArtifactError(f"marker/inventory node set mismatch in {context}")

    # P0-2: behavior-environment.json — full digest recomputation
    beh_name = declared_kinds.get("behavior-environment", "")
    beh_path = bundle_root / beh_name
    beh_fingerprint: str | None = None
    if beh_path.is_file():
        beh = _read_json_strict(beh_path, "behavior-environment.json", context)
        # Schema validation
        expected_beh_keys = {"schema_version", "payload", "canonical_json_sha256"}
        actual_beh_keys = set(beh.keys())
        if actual_beh_keys != expected_beh_keys:
            raise ArtifactError(
                f"behavior-environment schema keys mismatch in {context}: "
                f"extra={sorted(actual_beh_keys - expected_beh_keys)}, "
                f"missing={sorted(expected_beh_keys - actual_beh_keys)}"
            )
        if beh.get("schema_version") != "1":
            raise ArtifactError(f"behavior-environment schema_version must be '1' in {context}")
        payload = beh.get("payload")
        if not isinstance(payload, dict):
            raise ArtifactError(f"behavior-environment payload must be object in {context}")
        digest_stored = beh.get("canonical_json_sha256", "")
        if not digest_stored.startswith("sha256:"):
            raise ArtifactError(f"behavior-environment: invalid digest format in {context}")
        stored_hex = digest_stored[7:]
        if len(stored_hex) != 64:
            raise ArtifactError(f"behavior-environment: invalid digest length in {context}")
        # Recompute canonical digest using shared authority
        from tests.ci.behavior_environment import canonicalize_behavior_payload

        canonical = canonicalize_behavior_payload(payload)
        recomputed = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        if recomputed != stored_hex:
            raise ArtifactError(
                f"behavior-environment: digest mismatch in {context}: "
                f"recomputed={recomputed}, stored={stored_hex}"
            )
        beh_fingerprint = recomputed

    # ── pytest-outcomes.json validation (P0-3) ────────────────────────────
    outcome_counts_from_artifact: dict[str, int] | None = None
    outcomes_name = declared_kinds.get("pytest-outcomes", "")
    if outcomes_name and identity.collection_scope == "shard":
        outcomes_path = bundle_root / outcomes_name
        if outcomes_path.is_file():
            outcomes_raw = _read_json_strict(outcomes_path, "pytest-outcomes.json", context)
            outcome_counts_from_artifact = _verify_outcomes_schema(
                outcomes_raw, context, node_inv_data=node_inv
            )

    # resource-telemetry.json — P0-5: full authority check
    tel_name = declared_kinds.get("resource-telemetry", "")
    tel_path = bundle_root / tel_name
    if tel_path.is_file():
        tel = _read_json_strict(tel_path, "resource-telemetry.json", context)
        for field in ("track", "commit_sha", "run_id", "python_version"):
            expected_val = getattr(identity, field)
            actual_val = str(tel.get(field, ""))
            if actual_val != str(expected_val):
                raise ArtifactError(
                    f"resource-telemetry.{field} mismatch in {context}: "
                    f"got {actual_val!r}, expected {expected_val!r}"
                )
        if int(tel.get("run_attempt", 0)) != identity.run_attempt:
            raise ArtifactError(f"resource-telemetry.run_attempt mismatch in {context}")
        # P0-5: Strict authority checks
        exec_status = tel.get("execution_status", "")
        if exec_status != "completed":
            raise ArtifactError(
                f"resource-telemetry: execution_status={exec_status!r} "
                f"(expected 'completed') in {context}"
            )
        if tel.get("junit_parse_status") != "available":
            raise ArtifactError(f"resource-telemetry: junit_parse_status != available in {context}")
        if not tel.get("counts_authoritative"):
            raise ArtifactError(f"resource-telemetry: counts_authoritative=false in {context}")
        if tel.get("outcome_parse_status") != "available":
            raise ArtifactError(
                f"resource-telemetry: outcome_parse_status != available in {context}"
            )
        if tel.get("resource_measurement_status") != "available":
            raise ArtifactError(
                f"resource-telemetry: resource_measurement_status != available in {context}"
            )
        if int(tel.get("pytest_exit_code", -1)) != 0:
            raise ArtifactError(
                f"resource-telemetry: pytest_exit_code={tel.get('pytest_exit_code')} "
                f"(expected 0) in {context}"
            )

        # Cross-validate outcome counts with telemetry (P0-4: XPASS-safe)
        # Structured outcomes are the five-category authority.
        # JUnit parser cannot reliably distinguish XPASS from normal pass,
        # so we only check total count and that failure counts are consistent.
        if outcome_counts_from_artifact is not None:
            # Total must match: structured total == telemetry tests_collected
            structured_total = sum(outcome_counts_from_artifact.values())
            telemetry_collected = int(tel.get("tests_collected", -1))
            if structured_total != telemetry_collected:
                raise ArtifactError(
                    f"outcome/telemetry total mismatch: structured={structured_total} "
                    f"!= telemetry_collected={telemetry_collected} in {context}"
                )
            # failure count: structured >= 0, telemetry failure must be <=
            # structured (because strict XPASS adds to JUnit failure count)
            structured_failed = outcome_counts_from_artifact["tests_failed"]
            telemetry_failed = int(tel.get("tests_failed", -1))
            if telemetry_failed < 0:
                raise ArtifactError(f"resource-telemetry: tests_failed missing in {context}")
            # Structured failed can be >= telemetry failed (XPASS strict
            # adds to JUnit failures), but not less (impossible)
            if structured_failed < telemetry_failed:
                raise ArtifactError(
                    f"outcome/telemetry failure mismatch: structured_failed={structured_failed} "
                    f"< telemetry_failed={telemetry_failed} in {context}"
                )

    # P0-2: Cross-fingerprint — behavior digest == node inventory fingerprint
    if beh_fingerprint is not None and node_inv is not None:
        inv_fp = node_inv.get("behavior_fingerprint_sha256", "")
        if inv_fp != beh_fingerprint:
            raise ArtifactError(
                f"behavior/node fingerprint mismatch in {context}: "
                f"beh={beh_fingerprint}, inv={inv_fp}"
            )


def verify_shard_bundles(
    *,
    artifact_root: Path,
    manifest_path: Path,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
) -> None:
    """Verify all shard artifact identities match expected parameters."""
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
                    collection_scope="shard",
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
            "initial-parse",
        )
        identity = _parse_identity(meta)

        # Only process shard bundles
        if identity.collection_scope != "shard":
            continue

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
        raise ArtifactError(f"MISSING shard producers: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED shard producers: {sorted(extra)}")


def verify_global_bundles(
    *,
    artifact_root: Path,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    python_versions: list[str],
) -> None:
    """Verify all global collection bundle identities."""
    expected: set[ArtifactIdentity] = set()
    for py in python_versions:
        expected.add(
            ArtifactIdentity(
                track=expected_track,
                commit_sha=expected_commit_sha,
                run_id=expected_run_id,
                run_attempt=expected_run_attempt,
                python_version=py,
                collection_scope="global",
                shard=None,
            )
        )

    found: set[ArtifactIdentity] = set()
    metadata_files = sorted(artifact_root.rglob("artifact-metadata.json"))
    if not metadata_files:
        raise ArtifactError("no artifact-metadata.json files found for global bundles")

    for meta_path in metadata_files:
        meta = _read_json_strict(
            meta_path,
            "artifact-metadata.json",
            "initial-parse-global",
        )
        identity = _parse_identity(meta)

        # Only process global bundles
        if identity.collection_scope != "global":
            continue

        if identity in found:
            raise ArtifactError(f"DUPLICATE global artifact identity: {identity}")
        found.add(identity)

        if identity.track != expected_track:
            raise ArtifactError(f"global track mismatch: {identity.track!r} vs {expected_track!r}")
        if identity.commit_sha != expected_commit_sha:
            raise ArtifactError("global SHA mismatch")
        if identity.run_id != str(expected_run_id):
            raise ArtifactError("global run_id mismatch")
        if identity.run_attempt != expected_run_attempt:
            raise ArtifactError("global attempt mismatch")

        _verify_bundle_contents(meta_path, meta, identity)

    missing = expected - found
    extra = found - expected
    if missing:
        raise ArtifactError(f"MISSING global bundles: {sorted(missing)}")
    if extra:
        raise ArtifactError(f"UNEXPECTED global bundles: {sorted(extra)}")


# Backward-compatible entry point
def verify_artifacts(
    *,
    artifact_root: Path,
    manifest_path: Path,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
) -> None:
    """Verify all artifact identities (shard only, for backward compat)."""
    verify_shard_bundles(
        artifact_root=artifact_root,
        manifest_path=manifest_path,
        expected_track=expected_track,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
    )


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Verify artifact identity")
    sub = parser.add_subparsers(dest="command")

    # Shard verification
    shard_p = sub.add_parser("shard", help="Verify shard bundles")
    shard_p.add_argument("--artifact-root", required=True)
    shard_p.add_argument("--manifest", required=True)
    shard_p.add_argument("--track", required=True)
    shard_p.add_argument("--commit-sha", required=True)
    shard_p.add_argument("--run-id", required=True)
    shard_p.add_argument("--run-attempt", required=True, type=int)

    # Global verification
    global_p = sub.add_parser("global", help="Verify global bundles")
    global_p.add_argument("--artifact-root", required=True)
    global_p.add_argument("--track", required=True)
    global_p.add_argument("--commit-sha", required=True)
    global_p.add_argument("--run-id", required=True)
    global_p.add_argument("--run-attempt", required=True, type=int)
    global_p.add_argument(
        "--python-versions", required=True, nargs="+", help="Expected Python versions"
    )

    args = parser.parse_args()

    try:
        if args.command == "shard":
            verify_shard_bundles(
                artifact_root=Path(args.artifact_root),
                manifest_path=Path(args.manifest),
                expected_track=args.track,
                expected_commit_sha=args.commit_sha,
                expected_run_id=args.run_id,
                expected_run_attempt=args.run_attempt,
            )
            print(f"Shard artifact identity verification PASS: track={args.track}")
        elif args.command == "global":
            verify_global_bundles(
                artifact_root=Path(args.artifact_root),
                expected_track=args.track,
                expected_commit_sha=args.commit_sha,
                expected_run_id=args.run_id,
                expected_run_attempt=args.run_attempt,
                python_versions=args.python_versions,
            )
            print(f"Global artifact identity verification PASS: track={args.track}")
        else:
            parser.print_help()
            sys.exit(1)
    except ArtifactError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
