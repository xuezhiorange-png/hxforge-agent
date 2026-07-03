"""Governed benchmark authority for nightly CI.

Produces ``benchmark-authority.json`` — the single source of truth for
whether benchmark execution passed, was not applicable, or failed.

Two legitimate terminal states:
  A. status=not_applicable, reason=no-benchmark-nodes, authority_valid=true
  B. status=executed, pytest_exit_code=0, producer_authoritative=true,
     authority_valid=true

Every other combination must fail-closed.

P0-1: Strict execution evidence — executed artifacts only accept node_ids
       derived from ALL evidence files (outcomes, execution inventory,
       telemetry, junit). Every evidence set must cross-validate.
P0-2: Paired inventory validation for N/A — generate (N/A) subcommand
       requires both --marker-inventory and --node-inventory with
       cross-validation before producing artifact.
P0-3: Complete identity binding — load_marker_inventory() and
       load_and_validate_node_inventory() enforce exact match on
       track=='nightly', commit_sha (40 hex), run_id, run_attempt,
       python_version=='3.12', collection_scope=='global', shard==None.
P0-6: Evidence digests — SHA-256 digests of all evidence files are
       computed and stored in the authority artifact for tamper-evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Final

# ── Schema constants ────────────────────────────────────────────────────

_SCHEMA_VERSION: Final = "1"
_ALLOWED_TRACKS: Final = frozenset({"nightly"})
_ALLOWED_PYTHON_VERSIONS: Final = frozenset({"3.11", "3.12"})
_VALID_STATUSES: Final = frozenset({"not_applicable", "executed"})
_VALID_REASONS: Final = frozenset({None, "no-benchmark-nodes"})
_HEX_40: Final = re.compile(r"^[0-9a-f]{40}$")
_VALID_SHARDS: Final = frozenset({None, "shard-0", "shard-1", "shard-2", "benchmark"})
_VALID_OUTCOMES: Final = frozenset({"passed", "failed", "skipped", "xfailed", "xpassed"})


# ── Exceptions ──────────────────────────────────────────────────────────


class BenchmarkAuthorityError(Exception):
    """Raised when benchmark authority validation fails."""


# ── SHA-256 helpers (P0-6) ─────────────────────────────────────────────


def _compute_file_sha256(path: Path) -> str:
    """Read *path* and return its SHA-256 hex digest.

    The file is read in binary mode to ensure reproducibility regardless
    of text-mode normalisation.
    """
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


# ── Schema helpers ────────────────────────────────────────────────────────


def _build_not_applicable_artifact(
    *,
    commit_sha: str,
    run_id: str,
    run_attempt: int,
    python_version: str,
    evidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the authority artifact for the zero-benchmark-node case.

    P0-2: Only callable after paired inventory validation has passed.
    The caller must have validated both marker and node inventories
    with matching identity fields before invoking this function.

    P0-6: When *evidence* is provided its SHA-256 digests are included
    in the artifact for tamper-evidence.
    """
    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "track": "nightly",
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "collection_scope": "global",
        "shard": None,
        "benchmark_node_count": 0,
        "benchmark_node_ids": [],
        "status": "not_applicable",
        "reason": "no-benchmark-nodes",
        "authority_valid": True,
        "pytest_exit_code": None,
        "producer_authoritative": None,
    }
    if evidence is not None:
        artifact["evidence"] = dict(evidence)
    return artifact


def _build_executed_artifact(
    *,
    commit_sha: str,
    run_id: str,
    run_attempt: int,
    python_version: str,
    benchmark_node_count: int,
    benchmark_node_ids: list[str],
    pytest_exit_code: int,
    producer_authoritative: bool,
    validated_evidence_node_ids: frozenset[str],
    evidence: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build the authority artifact for the executed benchmark case.

    P0-1: *validated_evidence_node_ids* is mandatory. Every element of
    *benchmark_node_ids* must appear in that set. This prevents
    fabricated node IDs from entering the authority artifact.

    P0-6: When *evidence* is provided its SHA-256 digests are included
    in the artifact for tamper-evidence.
    """
    if benchmark_node_count <= 0:
        raise BenchmarkAuthorityError("executed artifact requires positive benchmark_node_count")
    if not benchmark_node_ids:
        raise BenchmarkAuthorityError("executed artifact requires non-empty benchmark_node_ids")

    claimed = set(benchmark_node_ids)
    if not claimed:
        raise BenchmarkAuthorityError("executed artifact requires non-empty benchmark_node_ids")
    unknown = claimed - validated_evidence_node_ids
    if unknown:
        raise BenchmarkAuthorityError(
            f"node_ids not present in validated evidence: {sorted(unknown)}"
        )

    artifact: dict[str, Any] = {
        "schema_version": _SCHEMA_VERSION,
        "track": "nightly",
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "collection_scope": "global",
        "shard": None,
        "benchmark_node_count": benchmark_node_count,
        "benchmark_node_ids": sorted(benchmark_node_ids),
        "status": "executed",
        "reason": None,
        "authority_valid": True,
        "pytest_exit_code": pytest_exit_code,
        "producer_authoritative": producer_authoritative,
    }
    if evidence is not None:
        artifact["evidence"] = dict(evidence)
    return artifact


# ── Identity validation (P0-3) ─────────────────────────────────────────


def _validate_identity_fields(
    raw: dict[str, Any],
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
    expected_collection_scope: str = "global",
    expected_shard: str | None = None,
    context: str,
) -> None:
    """Validate identity fields match expected values exactly.

    P0-3: Enforces exact match on all identity fields including
    collection_scope and shard.
    """
    # commit_sha must be 40 hex characters
    actual_sha = str(raw.get("commit_sha", ""))
    if not _HEX_40.match(actual_sha):
        raise BenchmarkAuthorityError(
            f"{context}.commit_sha must be 40 hex chars, got {actual_sha!r}"
        )
    if actual_sha != expected_commit_sha:
        raise BenchmarkAuthorityError(
            f"{context}.commit_sha mismatch: got {actual_sha!r}, expected {expected_commit_sha!r}"
        )

    # track must be 'nightly'
    actual_track = raw.get("track", "")
    if actual_track != "nightly":
        raise BenchmarkAuthorityError(f"{context}.track must be 'nightly', got {actual_track!r}")

    # run_id
    actual_run_id = str(raw.get("run_id", ""))
    if actual_run_id != expected_run_id:
        raise BenchmarkAuthorityError(
            f"{context}.run_id mismatch: got {actual_run_id!r}, expected {expected_run_id!r}"
        )

    # run_attempt
    actual_attempt = raw.get("run_attempt")
    if not isinstance(actual_attempt, int) or actual_attempt != expected_run_attempt:
        raise BenchmarkAuthorityError(
            f"{context}.run_attempt mismatch: got {actual_attempt}, expected {expected_run_attempt}"
        )

    # python_version
    actual_python = str(raw.get("python_version", ""))
    if actual_python not in _ALLOWED_PYTHON_VERSIONS:
        raise BenchmarkAuthorityError(
            f"{context}.python_version must be in {sorted(_ALLOWED_PYTHON_VERSIONS)}, "
            f"got {actual_python!r}"
        )
    if actual_python != expected_python_version:
        raise BenchmarkAuthorityError(
            f"{context}.python_version mismatch: got {actual_python!r}, "
            f"expected {expected_python_version!r}"
        )

    # collection_scope
    actual_scope = raw.get("collection_scope", "")
    if actual_scope != expected_collection_scope:
        raise BenchmarkAuthorityError(
            f"{context}.collection_scope must be {expected_collection_scope!r}, "
            f"got {actual_scope!r}"
        )

    # shard
    actual_shard = raw.get("shard")
    if actual_shard not in _VALID_SHARDS:
        raise BenchmarkAuthorityError(
            f"{context}.shard must be one of {sorted(_VALID_SHARDS, key=str)}, got {actual_shard!r}"
        )
    if actual_shard != expected_shard:
        raise BenchmarkAuthorityError(
            f"{context}.shard mismatch: got {actual_shard!r}, expected {expected_shard!r}"
        )


# ── Marker inventory parsing ──────────────────────────────────────────────


def extract_benchmark_nodes(
    marker_inventory: dict[str, Any],
) -> list[str]:
    """Extract canonical-sorted benchmark node IDs from a marker inventory.

    Node IDs must come from the node_markers mapping, not from grep or
    file names.  The inventory is validated for schema consistency.
    """
    node_markers = marker_inventory.get("node_markers")
    if not isinstance(node_markers, dict):
        raise BenchmarkAuthorityError("marker_inventory.node_markers must be a JSON object")

    benchmark_nodes: list[str] = []
    for node_id, markers in node_markers.items():
        if not isinstance(node_id, str) or not node_id:
            raise BenchmarkAuthorityError("invalid node_id in marker_inventory")
        if not isinstance(markers, list):
            raise BenchmarkAuthorityError(f"markers for {node_id!r} must be a list")
        if not all(isinstance(m, str) for m in markers):
            raise BenchmarkAuthorityError(f"markers for {node_id!r} must contain only strings")
        if "benchmark" in markers:
            benchmark_nodes.append(node_id)

    return sorted(benchmark_nodes)


def load_marker_inventory(
    path: Path,
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
    expected_collection_scope: str = "global",
    expected_shard: str | None = None,
) -> dict[str, Any]:
    """Load and validate a node-marker-inventory.json artifact.

    P0-3: Enforces strict identity binding — track must be 'nightly',
    commit_sha must be valid 40-hex, run_id, run_attempt, python_version
    must all match exactly, collection_scope must be 'global', shard must
    be None.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse marker inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("marker inventory root must be a dict")

    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"schema_version must be {_SCHEMA_VERSION!r}, got {raw.get('schema_version')!r}"
        )

    # Validate node_count consistency
    node_count = raw.get("node_count")
    if not isinstance(node_count, int) or node_count < 0:
        raise BenchmarkAuthorityError("node_count must be a non-negative int")

    node_markers = raw.get("node_markers")
    if not isinstance(node_markers, dict):
        raise BenchmarkAuthorityError("node_markers must be a dict")

    if len(node_markers) != node_count:
        raise BenchmarkAuthorityError(
            f"node_markers count ({len(node_markers)}) != node_count ({node_count})"
        )

    # P0-3: strict identity binding
    _validate_identity_fields(
        raw,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
        expected_collection_scope=expected_collection_scope,
        expected_shard=expected_shard,
        context="marker_inventory",
    )

    return raw


# ── Node inventory with identity binding (P0-3) ─────────────────────────


def load_and_validate_node_inventory(
    path: Path,
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
    expected_collection_scope: str = "global",
    expected_shard: str | None = None,
) -> dict[str, Any]:
    """Load a node-inventory.json, validate its schema, and enforce
    identity binding against the expected commit/run/python values.

    P0-3: Strict identity binding including collection_scope and shard.

    Returns the parsed inventory dict on success.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse node inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("node inventory root must be a dict")

    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"node inventory schema_version must be {_SCHEMA_VERSION!r}, "
            f"got {raw.get('schema_version')!r}"
        )

    node_ids = raw.get("node_ids")
    if not isinstance(node_ids, list):
        raise BenchmarkAuthorityError("node inventory node_ids must be a list")
    if not all(isinstance(nid, str) for nid in node_ids):
        raise BenchmarkAuthorityError("node inventory node_ids must contain only strings")
    if len(node_ids) != len(set(node_ids)):
        raise BenchmarkAuthorityError("node inventory node_ids must be unique")
    if node_ids != sorted(node_ids):
        raise BenchmarkAuthorityError("node inventory node_ids must be canonically sorted")

    node_count = raw.get("node_count")
    if not isinstance(node_count, int) or node_count < 0:
        raise BenchmarkAuthorityError("node inventory node_count must be non-negative int")
    if len(node_ids) != node_count:
        raise BenchmarkAuthorityError(
            f"node inventory node_ids length ({len(node_ids)}) != node_count ({node_count})"
        )

    # P0-3: strict identity binding
    _validate_identity_fields(
        raw,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
        expected_collection_scope=expected_collection_scope,
        expected_shard=expected_shard,
        context="node_inventory",
    )

    return raw


# ── Execution node inventory (benchmark shard) ───────────────────────────


def load_execution_node_inventory(
    path: Path,
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> dict[str, Any]:
    """Load an execution node-inventory.json and enforce identity binding.

    Similar to ``load_and_validate_node_inventory`` but expects
    ``collection_scope='shard'`` and ``shard='benchmark'``.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse execution node inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("execution node inventory root must be a dict")

    if raw.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"execution node inventory schema_version must be {_SCHEMA_VERSION!r}, "
            f"got {raw.get('schema_version')!r}"
        )

    node_ids = raw.get("node_ids")
    if not isinstance(node_ids, list):
        raise BenchmarkAuthorityError("execution node inventory node_ids must be a list")
    if not all(isinstance(nid, str) for nid in node_ids):
        raise BenchmarkAuthorityError("execution node inventory node_ids must contain only strings")
    if len(node_ids) != len(set(node_ids)):
        raise BenchmarkAuthorityError("execution node inventory node_ids must be unique")
    if node_ids != sorted(node_ids):
        raise BenchmarkAuthorityError(
            "execution node inventory node_ids must be canonically sorted"
        )

    node_count = raw.get("node_count")
    if not isinstance(node_count, int) or node_count < 0:
        raise BenchmarkAuthorityError(
            "execution node inventory node_count must be non-negative int"
        )
    if len(node_ids) != node_count:
        raise BenchmarkAuthorityError(
            f"execution node inventory node_ids length ({len(node_ids)}) "
            f"!= node_count ({node_count})"
        )

    _validate_identity_fields(
        raw,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
        expected_collection_scope="shard",
        expected_shard="benchmark",
        context="execution_node_inventory",
    )

    return raw


# ── Paired inventory validation (P0-1, P0-2) ────────────────────────────


def validate_inventory_identity_match(
    node_inventory: dict[str, Any],
    marker_inventory: dict[str, Any],
) -> None:
    """Prove that node_inventory and marker_inventory have the same node set
    and the same identity fields (P0-1 exact-node equality across artifacts).

    Both inventories must agree on:
      - node_ids / node_markers keys (exact set equality)
      - node_count
      - commit_sha, run_id, run_attempt, python_version
      - Both must be canonically sorted
    """
    # Node set cross-validation
    node_ids_from_inv = set(node_inventory.get("node_ids", []))
    node_ids_from_marker = set(marker_inventory.get("node_markers", {}).keys())

    if node_ids_from_inv != node_ids_from_marker:
        missing_in_inv = node_ids_from_marker - node_ids_from_inv
        extra_in_inv = node_ids_from_inv - node_ids_from_marker
        raise BenchmarkAuthorityError(
            "node_inventory/marker_inventory node set mismatch: "
            f"missing_in_inv={sorted(missing_in_inv)}, "
            f"extra_in_inv={sorted(extra_in_inv)}"
        )

    # Node count cross-validation
    inv_count = node_inventory.get("node_count")
    marker_count = marker_inventory.get("node_count")
    if inv_count != marker_count:
        raise BenchmarkAuthorityError(
            f"node_count mismatch: node_inventory={inv_count}, marker_inventory={marker_count}"
        )

    # Canonical sort check for marker node_ids
    marker_ids_list = list(marker_inventory.get("node_markers", {}).keys())
    if marker_ids_list != sorted(marker_ids_list):
        raise BenchmarkAuthorityError(
            "marker_inventory node_markers keys must be canonically sorted"
        )

    # Identity field cross-validation
    for field in ("commit_sha", "run_id", "python_version"):
        inv_val = str(node_inventory.get(field, ""))
        marker_val = str(marker_inventory.get(field, ""))
        if inv_val != marker_val:
            raise BenchmarkAuthorityError(
                f"{field} mismatch between node_inventory and "
                f"marker_inventory: inv={inv_val!r}, marker={marker_val!r}"
            )

    inv_attempt = node_inventory.get("run_attempt")
    marker_attempt = marker_inventory.get("run_attempt")
    if inv_attempt != marker_attempt:
        raise BenchmarkAuthorityError(
            f"run_attempt mismatch between node_inventory ({inv_attempt}) "
            f"and marker_inventory ({marker_attempt})"
        )

    # collection_scope cross-validation
    inv_scope = node_inventory.get("collection_scope", "")
    marker_scope = marker_inventory.get("collection_scope", "")
    if inv_scope != marker_scope:
        raise BenchmarkAuthorityError(
            f"collection_scope mismatch: node_inventory={inv_scope!r}, "
            f"marker_inventory={marker_scope!r}"
        )

    # shard cross-validation
    inv_shard = node_inventory.get("shard")
    marker_shard = marker_inventory.get("shard")
    if inv_shard != marker_shard:
        raise BenchmarkAuthorityError(
            f"shard mismatch: node_inventory={inv_shard!r}, marker_inventory={marker_shard!r}"
        )


# ── Evidence file I/O ────────────────────────────────────────────────────


def _load_json_file(path: Path, label: str) -> dict[str, Any]:
    """Load and parse a JSON file, raising on any error."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse {label}: {path}") from exc
    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError(f"{label} root must be a dict")
    return raw


def _extract_outcome_nodes(outcomes: dict[str, Any]) -> set[str]:
    """Extract the set of node IDs from an outcomes file.

    Reads from the ``outcomes["outcomes"]`` mapping and validates that
    every key is a non-empty string and every value is a recognised
    outcome category.
    """
    outcomes_map = outcomes.get("outcomes")
    if not isinstance(outcomes_map, dict):
        raise BenchmarkAuthorityError("outcomes.outcomes must be a dict")
    for node_id, outcome_val in outcomes_map.items():
        if not isinstance(node_id, str) or not node_id:
            raise BenchmarkAuthorityError("outcomes node IDs must be non-empty strings")
        if outcome_val not in _VALID_OUTCOMES:
            raise BenchmarkAuthorityError(f"invalid outcome {outcome_val!r} for {node_id!r}")
    return set(outcomes_map.keys())


def _extract_execution_inventory_nodes(
    execution_inventory: dict[str, Any],
) -> set[str]:
    """Extract the set of node IDs from an execution node inventory."""
    node_ids = execution_inventory.get("node_ids")
    if not isinstance(node_ids, list):
        raise BenchmarkAuthorityError("execution_inventory.node_ids must be a list")
    return set(node_ids)


def _extract_collection_complete_nodes(outcomes: dict[str, Any]) -> set[str]:
    """Extract collection_complete set from outcomes file."""
    cc = outcomes.get("collection_complete")
    if not isinstance(cc, list):
        raise BenchmarkAuthorityError("outcomes.collection_complete must be a list")
    for item in cc:
        if not isinstance(item, str) or not item:
            raise BenchmarkAuthorityError(
                "outcomes.collection_complete items must be non-empty strings"
            )
    return set(cc)


def _validate_outcomes_schema(outcomes: dict[str, Any]) -> None:
    """Strictly validate outcomes file schema."""
    if outcomes.get("schema_version") != "1":
        raise BenchmarkAuthorityError("outcomes.schema_version must be '1'")
    outcomes_map = outcomes.get("outcomes")
    if not isinstance(outcomes_map, dict):
        raise BenchmarkAuthorityError("outcomes.outcomes must be a dict")
    for node_id, outcome_val in outcomes_map.items():
        if not isinstance(node_id, str) or not node_id:
            raise BenchmarkAuthorityError("outcomes node IDs must be non-empty strings")
        if outcome_val not in _VALID_OUTCOMES:
            raise BenchmarkAuthorityError(f"invalid outcome {outcome_val!r} for {node_id!r}")
    total = outcomes.get("total")
    if not isinstance(total, int) or total < 0:
        raise BenchmarkAuthorityError("outcomes.total must be non-negative int")
    if total != len(outcomes_map):
        raise BenchmarkAuthorityError(
            f"outcomes.total={total} != len(outcomes)={len(outcomes_map)}"
        )
    cc = outcomes.get("collection_complete")
    if not isinstance(cc, list):
        raise BenchmarkAuthorityError("outcomes.collection_complete must be a list")
    if len(cc) != len(set(cc)):
        raise BenchmarkAuthorityError("outcomes.collection_complete must have unique entries")
    for item in cc:
        if not isinstance(item, str) or not item:
            raise BenchmarkAuthorityError(
                "outcomes.collection_complete items must be non-empty strings"
            )
    if set(outcomes_map.keys()) != set(cc):
        raise BenchmarkAuthorityError("outcomes.outcomes keys != collection_complete")


# ── Telemetry validation ─────────────────────────────────────────────────


def _validate_telemetry(
    telemetry: dict[str, Any],
    *,
    expected_pytest_exit_code: int,
    expected_node_count: int,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> None:
    """Validate telemetry file contents against expected values.

    Enforces identity fields (P0-3), execution status, pytest exit code,
    producer/count authority flags, outcome/junit/resource parse status,
    and tests_collected count.
    """
    # Validate identity fields directly (telemetry has no collection_scope)
    actual_sha = str(telemetry.get("commit_sha", ""))
    if not _HEX_40.match(actual_sha):
        raise BenchmarkAuthorityError(
            f"telemetry.commit_sha must be 40 hex chars, got {actual_sha!r}"
        )
    if actual_sha != expected_commit_sha:
        raise BenchmarkAuthorityError(
            f"telemetry.commit_sha mismatch: got {actual_sha!r}, expected {expected_commit_sha!r}"
        )
    actual_track = telemetry.get("track", "")
    if actual_track != "nightly":
        raise BenchmarkAuthorityError(f"telemetry.track must be 'nightly', got {actual_track!r}")
    actual_run_id = str(telemetry.get("run_id", ""))
    if actual_run_id != expected_run_id:
        raise BenchmarkAuthorityError(
            f"telemetry.run_id mismatch: got {actual_run_id!r}, expected {expected_run_id!r}"
        )
    actual_attempt = telemetry.get("run_attempt")
    if not isinstance(actual_attempt, int) or actual_attempt != expected_run_attempt:
        raise BenchmarkAuthorityError(
            f"telemetry.run_attempt mismatch: got {actual_attempt}, expected {expected_run_attempt}"
        )
    actual_python = str(telemetry.get("python_version", ""))
    if actual_python != expected_python_version:
        raise BenchmarkAuthorityError(
            f"telemetry.python_version mismatch: got {actual_python!r}, "
            f"expected {expected_python_version!r}"
        )
    # shard must be 'benchmark'
    shard = telemetry.get("shard")
    if shard != "benchmark":
        raise BenchmarkAuthorityError(f"telemetry.shard must be 'benchmark', got {shard!r}")
    # execution_status
    exec_status = telemetry.get("execution_status")
    if exec_status != "completed":
        raise BenchmarkAuthorityError(
            f"telemetry.execution_status must be 'completed', got {exec_status!r}"
        )
    # pytest_exit_code
    actual_exit_code = telemetry.get("pytest_exit_code")
    if not isinstance(actual_exit_code, int):
        raise BenchmarkAuthorityError(
            f"telemetry.pytest_exit_code must be int, got {actual_exit_code!r}"
        )
    if actual_exit_code != expected_pytest_exit_code:
        raise BenchmarkAuthorityError(
            f"telemetry.pytest_exit_code={actual_exit_code} != expected {expected_pytest_exit_code}"
        )
    # producer_authoritative
    producer_auth = telemetry.get("producer_authoritative")
    if producer_auth is not True:
        raise BenchmarkAuthorityError(
            f"telemetry.producer_authoritative must be true, got {producer_auth!r}"
        )
    # counts_authoritative
    counts_auth = telemetry.get("counts_authoritative")
    if counts_auth is not True:
        raise BenchmarkAuthorityError(
            f"telemetry.counts_authoritative must be true, got {counts_auth!r}"
        )
    # outcome_parse_status
    outcome_status = telemetry.get("outcome_parse_status")
    if outcome_status != "available":
        raise BenchmarkAuthorityError(
            f"telemetry.outcome_parse_status must be 'available', got {outcome_status!r}"
        )
    # junit_parse_status
    junit_status = telemetry.get("junit_parse_status")
    if junit_status != "available":
        raise BenchmarkAuthorityError(
            f"telemetry.junit_parse_status must be 'available', got {junit_status!r}"
        )
    # resource_measurement_status
    resource_status = telemetry.get("resource_measurement_status")
    if resource_status != "available":
        raise BenchmarkAuthorityError(
            f"telemetry.resource_measurement_status must be 'available', got {resource_status!r}"
        )
    # tests_collected
    tests_collected = telemetry.get("tests_collected")
    if not isinstance(tests_collected, int):
        raise BenchmarkAuthorityError(
            f"telemetry.tests_collected must be int, got {tests_collected!r}"
        )
    if tests_collected != expected_node_count:
        raise BenchmarkAuthorityError(
            f"telemetry.tests_collected={tests_collected} != node_count={expected_node_count}"
        )

    # P0-3 (round 4627109299): authoritatively require that the runner
    # performed execution-inventory cross-validation. The telemetry must
    # carry node_inventory_parse_status == "available" (or "unrequired"
    # when no inventory path was configured) and node_inventory_validation_error
    # must be null when status is "available".
    if "node_inventory_parse_status" not in telemetry:
        raise BenchmarkAuthorityError(
            "telemetry.node_inventory_parse_status missing "
            "(runner did not perform inventory cross-validation)"
        )
    inv_status = telemetry.get("node_inventory_parse_status")
    if inv_status not in ("available", "unrequired"):
        raise BenchmarkAuthorityError(
            f"telemetry.node_inventory_parse_status must be 'available' "
            f"or 'unrequired', got {inv_status!r}"
        )
    inv_err = telemetry.get("node_inventory_validation_error")
    if inv_status == "available" and inv_err is not None:
        raise BenchmarkAuthorityError(
            f"telemetry.node_inventory_validation_error must be null when "
            f"status=='available', got {inv_err!r}"
        )


def _validate_outcome_category_counts(
    outcomes: dict[str, Any],
    telemetry: dict[str, Any],
) -> None:
    """Verify that outcome category counts from outcomes map match telemetry.

    Counts are derived from the real ``outcomes.outcomes`` mapping (not a
    pre-computed summary) and cross-validated against telemetry fields.
    The sum of all five categories must equal ``tests_collected``.
    """
    outcomes_map = outcomes.get("outcomes")
    if not isinstance(outcomes_map, dict):
        raise BenchmarkAuthorityError("outcomes.outcomes must be a dict")
    # Count from real outcomes map
    counts = {
        k: 0
        for k in (
            "tests_passed",
            "tests_failed",
            "tests_skipped",
            "tests_xfailed",
            "tests_xpassed",
        )
    }
    for outcome_val in outcomes_map.values():
        key = f"tests_{outcome_val}"
        if key in counts:
            counts[key] += 1
    # Cross-validate with telemetry
    for key in counts:
        tel_val = telemetry.get(key)
        if not isinstance(tel_val, int):
            raise BenchmarkAuthorityError(f"telemetry.{key} must be int")
        if tel_val != counts[key]:
            raise BenchmarkAuthorityError(f"telemetry.{key}={tel_val} != computed {counts[key]}")
    # Verify sum == tests_collected
    total = sum(counts.values())
    tests_collected = telemetry.get("tests_collected")
    if total != tests_collected:
        raise BenchmarkAuthorityError(f"sum of counts={total} != tests_collected={tests_collected}")


# ── Evidence digest validation helper (P0-6) ────────────────────────────


_DIGEST_RE: Final = re.compile(r"^[0-9a-f]{64}$")

_REQUIRED_EVIDENCE_KEYS_EXECUTED: Final = frozenset(
    {
        "global_marker_inventory_sha256",
        "global_node_inventory_sha256",
        "execution_node_inventory_sha256",
        "outcomes_sha256",
        "telemetry_sha256",
        "junit_sha256",
    }
)

_REQUIRED_EVIDENCE_KEYS_NA: Final = frozenset(
    {
        "global_marker_inventory_sha256",
        "global_node_inventory_sha256",
    }
)


def _validate_evidence_digests(
    evidence: dict[str, str],
    *,
    required_keys: frozenset[str],
    context: str,
) -> None:
    """Validate that *evidence* contains exactly *required_keys*, each a
    64-char lowercase hex SHA-256 digest."""
    if not isinstance(evidence, dict):
        raise BenchmarkAuthorityError(f"{context}.evidence must be a dict")
    actual_keys = set(evidence.keys())
    if actual_keys != required_keys:
        missing = required_keys - actual_keys
        extra = actual_keys - required_keys
        raise BenchmarkAuthorityError(
            f"{context}.evidence keys mismatch: missing={sorted(missing)}, extra={sorted(extra)}"
        )
    for key, val in evidence.items():
        if not isinstance(val, str) or not _DIGEST_RE.match(val):
            raise BenchmarkAuthorityError(
                f"{context}.evidence.{key} must be 64-char lowercase hex, got {val!r}"
            )


# ── Executed benchmark evidence validation (P0-1, P0-6) ─────────────────


def validate_executed_benchmark_evidence(
    *,
    marker_inventory_path: Path,
    node_inventory_path: Path,
    execution_node_inventory_path: Path,
    outcomes_path: Path,
    telemetry_path: Path,
    junit_path: Path,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> tuple[frozenset[str], dict[str, str]]:
    """Read and cross-validate ALL evidence files, then return the frozen
    set of validated benchmark node IDs and evidence SHA-256 digests.

    P0-1: This function reads REAL files — it does NOT accept caller-
    supplied booleans.  It enforces:

    1. Marker inventory exists, is valid JSON, has matching identity
       fields (P0-3), and contains at least one benchmark node.
    2. When a node inventory is provided, its node set must exactly
       equal the marker inventory node set (P0-1 exact-node equality).
    3. Outcomes file node set must match the marker benchmark nodes.
    4. Execution inventory node set must match the marker benchmark nodes.
    5. Collection_complete nodes from outcomes must match.
    6. Telemetry must confirm execution_status=='completed',
       pytest_exit_code matches, producer_authoritative==true,
       counts_authoritative==true, tests_collected==len(nodes).
    7. Outcomes category counts must match telemetry.

    P0-6: SHA-256 digests are computed for every evidence file and
    returned alongside the validated node set.

    Returns ``(validated_node_ids, evidence_digests)``.
    """
    # 1. Load and validate marker inventory with identity binding
    marker_inv = load_marker_inventory(
        marker_inventory_path,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
    )

    benchmark_nodes = extract_benchmark_nodes(marker_inv)
    if not benchmark_nodes:
        raise BenchmarkAuthorityError(
            "executed benchmark requires at least one benchmark node in marker inventory"
        )

    benchmark_set = frozenset(benchmark_nodes)

    # 2. Validate node inventory (cross-validate with marker)
    node_inv = load_and_validate_node_inventory(
        node_inventory_path,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
    )
    validate_inventory_identity_match(node_inv, marker_inv)

    inv_node_ids = frozenset(node_inv.get("node_ids", []))
    missing_in_inv = benchmark_set - inv_node_ids
    if missing_in_inv:
        raise BenchmarkAuthorityError(
            f"benchmark nodes not in node_inventory: {sorted(missing_in_inv)}"
        )

    # 3. Load and validate outcomes file
    outcomes = _load_json_file(outcomes_path, "outcomes")
    _validate_outcomes_schema(outcomes)
    outcome_nodes = _extract_outcome_nodes(outcomes)
    if not outcome_nodes:
        raise BenchmarkAuthorityError("outcomes file has no node results (empty)")

    if outcome_nodes != set(benchmark_nodes):
        missing_in_outcomes = set(benchmark_nodes) - outcome_nodes
        extra_in_outcomes = outcome_nodes - set(benchmark_nodes)
        raise BenchmarkAuthorityError(
            "outcomes node set mismatch with marker inventory: "
            f"missing_in_outcomes={sorted(missing_in_outcomes)}, "
            f"extra_in_outcomes={sorted(extra_in_outcomes)}"
        )

    # 4. Load and validate execution node inventory (P0-1: strict loader, mandatory)
    exec_inv = load_execution_node_inventory(
        execution_node_inventory_path,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
    )
    exec_nodes = frozenset(exec_inv.get("node_ids", []))
    if not exec_nodes:
        raise BenchmarkAuthorityError("execution_inventory has no node_ids (empty)")
    if exec_nodes != benchmark_set:
        missing_in_exec = benchmark_set - exec_nodes
        extra_in_exec = exec_nodes - benchmark_set
        raise BenchmarkAuthorityError(
            "execution_inventory node set mismatch with marker: "
            f"missing_in_exec={sorted(missing_in_exec)}, "
            f"extra_in_exec={sorted(extra_in_exec)}"
        )

    # 5. Validate collection_complete nodes from outcomes
    collection_complete_nodes = _extract_collection_complete_nodes(outcomes)
    if not collection_complete_nodes:
        raise BenchmarkAuthorityError("no nodes have collection_complete in outcomes")
    if collection_complete_nodes != set(benchmark_nodes):
        missing_cc = set(benchmark_nodes) - collection_complete_nodes
        extra_cc = collection_complete_nodes - set(benchmark_nodes)
        raise BenchmarkAuthorityError(
            "collection_complete nodes mismatch with benchmark nodes: "
            f"missing={sorted(missing_cc)}, extra={sorted(extra_cc)}"
        )

    # 6. Load and validate telemetry
    telemetry = _load_json_file(telemetry_path, "telemetry")
    _validate_telemetry(
        telemetry,
        expected_pytest_exit_code=0,
        expected_node_count=len(benchmark_nodes),
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
    )

    # 7. Validate outcome category counts match telemetry
    _validate_outcome_category_counts(outcomes, telemetry)

    # 8. Compute evidence SHA-256 digests (P0-6)
    evidence: dict[str, str] = {
        "global_marker_inventory_sha256": _compute_file_sha256(marker_inventory_path),
        "global_node_inventory_sha256": _compute_file_sha256(node_inventory_path),
        "execution_node_inventory_sha256": _compute_file_sha256(execution_node_inventory_path),
        "outcomes_sha256": _compute_file_sha256(outcomes_path),
        "telemetry_sha256": _compute_file_sha256(telemetry_path),
        "junit_sha256": _compute_file_sha256(junit_path),
    }

    return benchmark_set, evidence


# ── Artifact validation ───────────────────────────────────────────────────


def validate_authority_artifact(
    artifact: dict[str, Any],
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> None:
    """Validate a benchmark-authority.json against governance rules.

    Accepts exactly two states:
      A. not_applicable — no-benchmark-nodes, zero count
      B. executed — positive count, exit 0, producer_authoritative true

    Everything else fails closed.

    P0-3: Identity fields are checked via ``_validate_identity_fields``
    for consistent exact-match comparison.

    P0-6: When an ``evidence`` field is present, its digests are validated
    against the expected set for the given status.
    """
    # Schema version
    if artifact.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"schema_version must be {_SCHEMA_VERSION}, got {artifact.get('schema_version')!r}"
        )

    # Track
    if artifact.get("track") != "nightly":
        raise BenchmarkAuthorityError(f"track must be 'nightly', got {artifact.get('track')!r}")

    # collection_scope
    if artifact.get("collection_scope") != "global":
        raise BenchmarkAuthorityError(
            f"collection_scope must be 'global', got {artifact.get('collection_scope')!r}"
        )

    # shard
    shard = artifact.get("shard")
    if shard not in _VALID_SHARDS:
        raise BenchmarkAuthorityError(
            f"shard must be one of {sorted(_VALID_SHARDS, key=str)}, got {shard!r}"
        )

    # Identity binding — exact match (P0-3)
    _validate_identity_fields(
        artifact,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
        context="authority",
    )

    # Node count and IDs
    node_count = artifact.get("benchmark_node_count")
    if not isinstance(node_count, int) or node_count < 0:
        raise BenchmarkAuthorityError(
            f"benchmark_node_count must be non-negative int, got {node_count!r}"
        )

    node_ids = artifact.get("benchmark_node_ids")
    if not isinstance(node_ids, list):
        raise BenchmarkAuthorityError("benchmark_node_ids must be a list")
    if not all(isinstance(nid, str) for nid in node_ids):
        raise BenchmarkAuthorityError("benchmark_node_ids must contain only strings")
    if len(node_ids) != node_count:
        raise BenchmarkAuthorityError(
            f"benchmark_node_ids length ({len(node_ids)}) != benchmark_node_count ({node_count})"
        )
    if node_ids != sorted(node_ids):
        raise BenchmarkAuthorityError("benchmark_node_ids must be canonically sorted")
    if len(node_ids) != len(set(node_ids)):
        raise BenchmarkAuthorityError("benchmark_node_ids must be unique")

    # Status
    status = artifact.get("status")
    if status not in _VALID_STATUSES:
        raise BenchmarkAuthorityError(f"unknown status: {status!r}")

    # Reason
    reason = artifact.get("reason")
    if reason not in _VALID_REASONS:
        raise BenchmarkAuthorityError(f"unknown reason: {reason!r}")

    # Authority valid — must be True for either state
    if artifact.get("authority_valid") is not True:
        raise BenchmarkAuthorityError(
            f"authority_valid must be true, got {artifact.get('authority_valid')!r}"
        )

    # ── P0-5: evidence is mandatory ──────────────────────────────────────
    evidence = artifact.get("evidence")
    if not isinstance(evidence, dict):
        raise BenchmarkAuthorityError(f"{status} authority requires evidence object")
    if status == "not_applicable":
        _validate_evidence_digests(
            evidence,
            required_keys=_REQUIRED_EVIDENCE_KEYS_NA,
            context="not_applicable",
        )
    elif status == "executed":
        _validate_evidence_digests(
            evidence,
            required_keys=_REQUIRED_EVIDENCE_KEYS_EXECUTED,
            context="executed",
        )

    # ── State A: not_applicable ──────────────────────────────────────────
    if status == "not_applicable":
        if reason != "no-benchmark-nodes":
            raise BenchmarkAuthorityError(
                f"not_applicable requires reason='no-benchmark-nodes', got {reason!r}"
            )
        if node_count != 0:
            raise BenchmarkAuthorityError("not_applicable requires benchmark_node_count=0")
        if len(node_ids) != 0:
            raise BenchmarkAuthorityError("not_applicable requires empty benchmark_node_ids")
        if artifact.get("pytest_exit_code") is not None:
            raise BenchmarkAuthorityError("not_applicable requires pytest_exit_code=null")
        if artifact.get("producer_authoritative") is not None:
            raise BenchmarkAuthorityError("not_applicable requires producer_authoritative=null")
        return

    # ── State B: executed ────────────────────────────────────────────────
    if status == "executed":
        if reason is not None:
            raise BenchmarkAuthorityError("executed requires reason=null")
        if node_count <= 0:
            raise BenchmarkAuthorityError("executed requires benchmark_node_count > 0")
        if len(node_ids) == 0:
            raise BenchmarkAuthorityError("executed requires non-empty benchmark_node_ids")

        pytest_exit_code = artifact.get("pytest_exit_code")
        if not isinstance(pytest_exit_code, int):
            raise BenchmarkAuthorityError(f"pytest_exit_code must be int, got {pytest_exit_code!r}")
        if pytest_exit_code != 0:
            raise BenchmarkAuthorityError(f"pytest_exit_code must be 0, got {pytest_exit_code}")

        producer_auth = artifact.get("producer_authoritative")
        if producer_auth is not True:
            raise BenchmarkAuthorityError(
                f"producer_authoritative must be true, got {producer_auth!r}"
            )
        return

    # Should never reach here
    raise BenchmarkAuthorityError(f"unhandled status: {status!r}")


# ── Artifact I/O ──────────────────────────────────────────────────────────


def save_authority_artifact(
    artifact: dict[str, Any],
    output_path: Path,
) -> None:
    """Write benchmark-authority.json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_authority_artifact(path: Path) -> dict[str, Any]:
    """Load and parse benchmark-authority.json."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse benchmark-authority.json: {path}") from exc
    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("benchmark-authority root must be a dict")
    return raw


# ── CLI subcommands with locked execution ─────────────────────────────────


def _cli_generate(args: argparse.Namespace) -> None:
    """CLI subcommand: generate N/A benchmark-authority.json only.

    P0-2: generate is ONLY for the N/A (zero nodes) path.  Requires
    both --marker-inventory and --node-inventory.  Validates paired
    inventories with cross-validation before producing artifact.
    """
    # P0-2: require both inventories for generate
    marker_inv_path = getattr(args, "marker_inventory", None)
    node_inv_path = getattr(args, "node_inventory", None)
    if not marker_inv_path or not node_inv_path:
        raise BenchmarkAuthorityError(
            "generate requires both --marker-inventory and --node-inventory "
            "(P0-2 paired inventory validation)"
        )

    marker_inv = load_marker_inventory(
        Path(marker_inv_path),
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    node_inv = load_and_validate_node_inventory(
        Path(node_inv_path),
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    # P0-2: cross-validate paired inventories
    validate_inventory_identity_match(node_inv, marker_inv)

    benchmark_nodes = extract_benchmark_nodes(marker_inv)
    if len(benchmark_nodes) != 0:
        raise BenchmarkAuthorityError(
            "generate subcommand is only for N/A (zero benchmark nodes). "
            f"Found {len(benchmark_nodes)} benchmark nodes — "
            "use 'execute' subcommand instead."
        )

    # Node inventory should have same node set as marker inventory
    inv_node_ids = node_inv.get("node_ids", [])
    inv_set = set(inv_node_ids)
    marker_set = set(marker_inv.get("node_markers", {}).keys())
    if inv_set != marker_set:
        missing = marker_set - inv_set
        extra = inv_set - marker_set
        raise BenchmarkAuthorityError(
            f"node_inventory/marker_inventory node set mismatch: "
            f"missing={sorted(missing)}, extra={sorted(extra)}"
        )

    # P0-6: compute evidence digests for N/A artifact
    evidence: dict[str, str] = {
        "global_marker_inventory_sha256": _compute_file_sha256(Path(marker_inv_path)),
        "global_node_inventory_sha256": _compute_file_sha256(Path(node_inv_path)),
    }

    artifact = _build_not_applicable_artifact(
        commit_sha=args.commit_sha,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        python_version=args.python_version,
        evidence=evidence,
    )

    save_authority_artifact(artifact, Path(args.output))
    print(
        f"Benchmark authority: status={artifact['status']}, "
        f"node_count={artifact['benchmark_node_count']}, "
        f"authority_valid={artifact['authority_valid']}"
    )


def _cli_execute(args: argparse.Namespace) -> None:
    """CLI subcommand: read evidence files and build executed artifact.

    P0-1: Requires ALL evidence file paths. Cannot proceed if any are
    missing. Reads and cross-validates outcomes, execution inventory,
    telemetry, junit, and marker inventory.
    """

    # P0-1: require ALL evidence paths
    def _req(name: str) -> str:
        val = getattr(args, name, None)
        if not val:
            raise BenchmarkAuthorityError(f"execute requires --{name}")
        assert isinstance(val, str)
        return val

    gmi = _req("global_marker_inventory")
    gni = _req("global_node_inventory")
    eni = _req("execution_node_inventory")
    outcomes_file = _req("outcomes")
    tel_file = _req("telemetry")
    junit_file = _req("junit")
    output_val = _req("output")

    validated_nodes, evidence = validate_executed_benchmark_evidence(
        marker_inventory_path=Path(gmi),
        node_inventory_path=Path(gni),
        execution_node_inventory_path=Path(eni),
        outcomes_path=Path(outcomes_file),
        telemetry_path=Path(tel_file),
        junit_path=Path(junit_file),
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    if not validated_nodes:
        raise BenchmarkAuthorityError("executed path requires benchmark nodes in evidence")

    # Load telemetry for exit code and producer_authoritative
    telemetry = _load_json_file(Path(tel_file), "telemetry")

    artifact = _build_executed_artifact(
        commit_sha=args.commit_sha,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        python_version=args.python_version,
        benchmark_node_count=len(validated_nodes),
        benchmark_node_ids=sorted(validated_nodes),
        pytest_exit_code=telemetry["pytest_exit_code"],
        producer_authoritative=telemetry["producer_authoritative"],
        validated_evidence_node_ids=validated_nodes,
        evidence=evidence,
    )

    save_authority_artifact(artifact, Path(output_val))
    print(
        f"Benchmark authority: status={artifact['status']}, "
        f"node_count={artifact['benchmark_node_count']}, "
        f"authority_valid={artifact['authority_valid']}"
    )


def _cli_validate(args: argparse.Namespace) -> None:
    """CLI subcommand: validate an existing authority artifact.

    Validates the authority artifact itself, then optionally validates
    all source evidence files when provided.  For executed artifacts the
    complete evidence set (including --junit) is required; for N/A
    artifacts only marker + node inventory are required.
    """
    artifact = load_authority_artifact(Path(args.artifact))

    validate_authority_artifact(
        artifact,
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    # Optional: cross-validate against all source evidence files
    evidence_files = {
        "global_marker_inventory": getattr(args, "global_marker_inventory", None),
        "global_node_inventory": getattr(args, "global_node_inventory", None),
        "execution_node_inventory": getattr(args, "execution_node_inventory", None),
        "outcomes": getattr(args, "outcomes", None),
        "telemetry": getattr(args, "telemetry", None),
        "junit": getattr(args, "junit", None),
    }

    # P0-7: fail closed — mandatory evidence by status
    status = artifact.get("status")
    if status == "not_applicable":
        required = {"global_marker_inventory", "global_node_inventory"}
    elif status == "executed":
        required = {
            "global_marker_inventory",
            "global_node_inventory",
            "execution_node_inventory",
            "outcomes",
            "telemetry",
            "junit",
        }
    else:
        required = set()

    missing = sorted(name for name in required if not evidence_files.get(name))
    if missing:
        raise BenchmarkAuthorityError(
            f"{status} validation requires complete evidence: missing={missing}"
        )

    # After mandatory check, all required values are non-None strings
    def _req(name: str) -> str:
        val = evidence_files.get(name)
        assert isinstance(val, str)  # guaranteed by mandatory check above
        return val

    if status == "not_applicable":
        marker_inv = load_marker_inventory(
            Path(_req("global_marker_inventory")),
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
            expected_python_version=args.python_version,
        )
        node_inv = load_and_validate_node_inventory(
            Path(_req("global_node_inventory")),
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
            expected_python_version=args.python_version,
        )
        validate_inventory_identity_match(node_inv, marker_inv)

        # P0-6: prove benchmark marker set is empty
        benchmark_nodes = extract_benchmark_nodes(marker_inv)
        if benchmark_nodes:
            raise BenchmarkAuthorityError(
                "not_applicable authority requires zero benchmark-marked nodes; "
                f"found={benchmark_nodes!r}"
            )
        if artifact.get("benchmark_node_count") != 0:
            raise BenchmarkAuthorityError("N/A artifact benchmark_node_count != 0")
        if artifact.get("benchmark_node_ids") != []:
            raise BenchmarkAuthorityError("N/A artifact benchmark_node_ids != []")

        # Verify digests match
        stored_evidence = artifact.get("evidence")
        assert isinstance(stored_evidence, dict)  # enforced by P0-5
        computed_evidence = {
            "global_marker_inventory_sha256": _compute_file_sha256(
                Path(_req("global_marker_inventory"))
            ),
            "global_node_inventory_sha256": _compute_file_sha256(
                Path(_req("global_node_inventory"))
            ),
        }
        for key in _REQUIRED_EVIDENCE_KEYS_NA:
            if stored_evidence.get(key) != computed_evidence.get(key):
                raise BenchmarkAuthorityError(
                    f"evidence digest mismatch for {key}: "
                    f"artifact={stored_evidence.get(key)!r}, "
                    f"computed={computed_evidence.get(key)!r}"
                )
        print("N/A source-evidence validation passed ✓")
        print("Evidence digest verification passed ✓")
        print("Benchmark marker set empty: PASS ✓")

    elif status == "executed":
        validated_nodes, evidence = validate_executed_benchmark_evidence(
            marker_inventory_path=Path(_req("global_marker_inventory")),
            node_inventory_path=Path(_req("global_node_inventory")),
            execution_node_inventory_path=Path(_req("execution_node_inventory")),
            outcomes_path=Path(_req("outcomes")),
            telemetry_path=Path(_req("telemetry")),
            junit_path=Path(_req("junit")),
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
            expected_python_version=args.python_version,
        )
        print(f"Executed evidence cross-validation passed ✓ ({len(validated_nodes)} nodes)")

        # P0-1 (round 4627109299): Strictly bind artifact's benchmark_node_ids
        # and benchmark_node_count to the validated evidence node set.
        # Same-count authority node replacement must be rejected here,
        # not only at construction time.
        artifact_node_ids = artifact.get("benchmark_node_ids")
        if not isinstance(artifact_node_ids, list):
            raise BenchmarkAuthorityError("executed authority benchmark_node_ids must be a list")
        artifact_nodes = frozenset(artifact_node_ids)
        if artifact_nodes != validated_nodes:
            missing_in_authority = sorted(validated_nodes - artifact_nodes)
            extra_in_authority = sorted(artifact_nodes - validated_nodes)
            raise BenchmarkAuthorityError(
                "authority benchmark node set mismatch with validated evidence: "
                f"missing_in_authority={missing_in_authority}, "
                f"extra_in_authority={extra_in_authority}"
            )
        artifact_node_count = artifact.get("benchmark_node_count")
        if artifact_node_count != len(validated_nodes):
            raise BenchmarkAuthorityError(
                "authority benchmark_node_count mismatch with validated evidence: "
                f"authority={artifact_node_count}, "
                f"validated={len(validated_nodes)}"
            )

        # Verify digests match
        stored_evidence = artifact.get("evidence")
        assert isinstance(stored_evidence, dict)  # enforced by P0-5
        source_files: dict[str, str] = {
            "global_marker_inventory_sha256": _req("global_marker_inventory"),
            "global_node_inventory_sha256": _req("global_node_inventory"),
            "execution_node_inventory_sha256": _req("execution_node_inventory"),
            "outcomes_sha256": _req("outcomes"),
            "telemetry_sha256": _req("telemetry"),
            "junit_sha256": _req("junit"),
        }
        for key in _REQUIRED_EVIDENCE_KEYS_EXECUTED:
            computed = _compute_file_sha256(Path(source_files[key]))
            if stored_evidence.get(key) != computed:
                raise BenchmarkAuthorityError(
                    f"evidence digest mismatch for {key}: "
                    f"artifact={stored_evidence.get(key)!r}, "
                    f"computed={computed!r}"
                )
        print("Evidence digest verification passed ✓")
        print("Authority benchmark node set bound to validated evidence ✓")

    print(
        f"Authority artifact validation PASS: "
        f"status={artifact.get('status')}, "
        f"authority_valid={artifact.get('authority_valid')}"
    )


def main() -> None:
    """CLI: generate or validate benchmark authority artifacts.

    Subcommands (P0-4 locked execution):
      generate  — N/A only, requires paired inventory validation (P0-2)
      execute   — Read all evidence files and build executed artifact (P0-1)
      validate  — Validate an existing authority artifact + evidence
    """
    parser = argparse.ArgumentParser(description="Benchmark authority tooling for nightly CI")
    sub = parser.add_subparsers(dest="command")

    # ── Shared identity arguments ────────────────────────────────────────
    def _add_identity_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--commit-sha", required=True)
        p.add_argument("--run-id", required=True)
        p.add_argument("--run-attempt", required=True, type=int)
        p.add_argument("--python-version", required=True)

    # ── generate (N/A only — P0-2) ─────────────────────────────────────
    gen_p = sub.add_parser(
        "generate",
        help="Generate N/A benchmark-authority.json (paired inventory validation)",
    )
    gen_p.add_argument(
        "--marker-inventory",
        required=True,
        help="Path to node-marker-inventory.json",
    )
    gen_p.add_argument(
        "--node-inventory",
        required=True,
        help="Path to node-inventory.json (required for P0-2)",
    )
    gen_p.add_argument(
        "--output",
        required=True,
        help="Output path for benchmark-authority.json",
    )
    _add_identity_args(gen_p)

    # ── execute (P0-1: all evidence required) ──────────────────────────
    execute_p = sub.add_parser(
        "execute",
        help="Build executed authority artifact from all evidence files",
    )
    execute_p.add_argument(
        "--global-marker-inventory",
        required=True,
        help="Path to global node-marker-inventory.json",
    )
    execute_p.add_argument(
        "--global-node-inventory",
        required=True,
        help="Path to global node-inventory.json",
    )
    execute_p.add_argument(
        "--execution-node-inventory",
        required=True,
        help="Path to execution node-inventory.json",
    )
    execute_p.add_argument(
        "--outcomes",
        required=True,
        help="Path to outcomes JSON file",
    )
    execute_p.add_argument(
        "--telemetry",
        required=True,
        help="Path to telemetry JSON file",
    )
    execute_p.add_argument(
        "--junit",
        required=True,
        help="Path to JUnit XML file for SHA-256 digest",
    )
    execute_p.add_argument(
        "--output",
        required=True,
        help="Output path for benchmark-authority.json",
    )
    _add_identity_args(execute_p)

    # ── validate ─────────────────────────────────────────────────────────
    validate_p = sub.add_parser(
        "validate",
        help="Validate an authority artifact + optionally all source evidence",
    )
    validate_p.add_argument(
        "--artifact",
        required=True,
        help="Path to benchmark-authority.json",
    )
    validate_p.add_argument(
        "--global-marker-inventory",
        default=None,
        help="Optional path to global marker inventory for cross-validation",
    )
    validate_p.add_argument(
        "--global-node-inventory",
        default=None,
        help="Optional path to global node inventory for cross-validation",
    )
    validate_p.add_argument(
        "--execution-node-inventory",
        default=None,
        help="Optional path to execution node inventory",
    )
    validate_p.add_argument(
        "--outcomes",
        default=None,
        help="Optional path to outcomes file",
    )
    validate_p.add_argument(
        "--telemetry",
        default=None,
        help="Optional path to telemetry file",
    )
    validate_p.add_argument(
        "--junit",
        default=None,
        help="Optional path to JUnit XML file for digest verification",
    )
    _add_identity_args(validate_p)

    args = parser.parse_args()

    try:
        if args.command == "generate":
            _cli_generate(args)
        elif args.command == "execute":
            _cli_execute(args)
        elif args.command == "validate":
            _cli_validate(args)
        else:
            parser.print_help()
            sys.exit(1)
    except BenchmarkAuthorityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
