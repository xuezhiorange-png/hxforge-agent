"""Governed benchmark authority for nightly CI.

Produces ``benchmark-authority.json`` — the single source of truth for
whether benchmark execution passed, was not applicable, or failed.

Two legitimate terminal states:
  A. status=not_applicable, reason=no-benchmark-nodes, authority_valid=true
  B. status=executed, pytest_exit_code=0, producer_authoritative=true,
     authority_valid=true

Every other combination must fail-closed.

P0-1: Exact-node equality — executed artifacts only accept node_ids
       derived from validated evidence (marker inventory intersection
       with node inventory).
P0-3: Marker inventory identity binding — load_marker_inventory() enforces
       exact match on commit_sha, run_id, run_attempt, python_version.
P0-4: CLI subcommands with locked execution — collect, execute, validate.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Final

_SCHEMA_VERSION: Final = "1"
_ALLOWED_TRACKS: Final = frozenset({"pr-head", "merge-ref", "main", "nightly"})
_ALLOWED_PYTHON_VERSIONS: Final = frozenset({"3.11", "3.12"})
_VALID_STATUSES: Final = frozenset({"not_applicable", "executed"})
_VALID_REASONS: Final = frozenset({None, "no-benchmark-nodes"})
_HEX_40: Final = re.compile(r"^[0-9a-f]{40}$")


class BenchmarkAuthorityError(Exception):
    """Raised when benchmark authority validation fails."""


# ── Schema helpers ────────────────────────────────────────────────────────


def _build_not_applicable_artifact(
    *,
    commit_sha: str,
    run_id: str,
    run_attempt: int,
    python_version: str,
) -> dict[str, Any]:
    """Build the authority artifact for the zero-benchmark-node case."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "track": "nightly",
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "benchmark_node_count": 0,
        "benchmark_node_ids": [],
        "status": "not_applicable",
        "reason": "no-benchmark-nodes",
        "authority_valid": True,
        "pytest_exit_code": None,
        "producer_authoritative": None,
    }


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
    validated_evidence_node_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    """Build the authority artifact for the executed benchmark case.

    When *validated_evidence_node_ids* is provided, every element of
    *benchmark_node_ids* must appear in that set (P0-1 exact-node
    equality).  This prevents fabricated node IDs from entering the
    authority artifact.
    """
    if benchmark_node_count <= 0:
        raise BenchmarkAuthorityError("executed artifact requires positive benchmark_node_count")
    if not benchmark_node_ids:
        raise BenchmarkAuthorityError("executed artifact requires non-empty benchmark_node_ids")

    if validated_evidence_node_ids is not None:
        claimed = set(benchmark_node_ids)
        if not claimed:
            raise BenchmarkAuthorityError("executed artifact requires non-empty benchmark_node_ids")
        unknown = claimed - validated_evidence_node_ids
        if unknown:
            raise BenchmarkAuthorityError(
                f"node_ids not present in validated evidence: {sorted(unknown)}"
            )

    return {
        "schema_version": _SCHEMA_VERSION,
        "track": "nightly",
        "commit_sha": commit_sha,
        "run_id": run_id,
        "run_attempt": run_attempt,
        "python_version": python_version,
        "benchmark_node_count": benchmark_node_count,
        "benchmark_node_ids": sorted(benchmark_node_ids),
        "status": "executed",
        "reason": None,
        "authority_valid": True,
        "pytest_exit_code": pytest_exit_code,
        "producer_authoritative": producer_authoritative,
    }


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


def _validate_identity_fields(
    raw: dict[str, Any],
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
    context: str,
) -> None:
    """Validate identity fields match expected values exactly."""
    for field, expected in (
        ("commit_sha", expected_commit_sha),
        ("run_id", expected_run_id),
        ("python_version", expected_python_version),
    ):
        actual = str(raw.get(field, ""))
        if actual != str(expected):
            raise BenchmarkAuthorityError(
                f"{context}.{field} mismatch: got {actual!r}, expected {expected!r}"
            )

    actual_attempt = raw.get("run_attempt")
    if not isinstance(actual_attempt, int) or actual_attempt != expected_run_attempt:
        raise BenchmarkAuthorityError(
            f"{context}.run_attempt mismatch: got {actual_attempt}, expected {expected_run_attempt}"
        )


def load_marker_inventory(
    path: Path,
    *,
    expected_commit_sha: str | None = None,
    expected_run_id: str | None = None,
    expected_run_attempt: int | None = None,
    expected_python_version: str | None = None,
) -> dict[str, Any]:
    """Load and validate a node-marker-inventory.json artifact.

    When expected identity parameters are supplied, the loaded inventory
    is checked for exact match on commit_sha, run_id, run_attempt, and
    python_version (P0-3 marker inventory identity binding).
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse marker inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("marker inventory root must be a dict")

    if raw.get("schema_version") != "1":
        raise BenchmarkAuthorityError(
            f"schema_version must be '1', got {raw.get('schema_version')!r}"
        )

    track = raw.get("track", "")
    if track not in _ALLOWED_TRACKS:
        raise BenchmarkAuthorityError(f"invalid track: {track!r}")

    python_version = raw.get("python_version", "")
    if python_version not in _ALLOWED_PYTHON_VERSIONS:
        raise BenchmarkAuthorityError(f"invalid python_version: {python_version!r}")

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

    # P0-3: enforce identity binding when expected params are given
    identity_params_supplied = any(
        v is not None
        for v in (
            expected_commit_sha,
            expected_run_id,
            expected_run_attempt,
            expected_python_version,
        )
    )
    if identity_params_supplied:
        _validate_identity_fields(
            raw,
            expected_commit_sha=expected_commit_sha or "",
            expected_run_id=expected_run_id or "",
            expected_run_attempt=expected_run_attempt or 0,
            expected_python_version=expected_python_version or "",
            context="marker_inventory",
        )

    return raw


# ── Node inventory with identity binding ──────────────────────────────────


def load_and_validate_node_inventory(
    path: Path,
    *,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> dict[str, Any]:
    """Load a node-inventory.json, validate its schema, and enforce
    identity binding against the expected commit/run/python values.

    Returns the parsed inventory dict on success.
    """
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BenchmarkAuthorityError(f"cannot parse node inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise BenchmarkAuthorityError("node inventory root must be a dict")

    if raw.get("schema_version") != "1":
        raise BenchmarkAuthorityError(
            f"node inventory schema_version must be '1', got {raw.get('schema_version')!r}"
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

    _validate_identity_fields(
        raw,
        expected_commit_sha=expected_commit_sha,
        expected_run_id=expected_run_id,
        expected_run_attempt=expected_run_attempt,
        expected_python_version=expected_python_version,
        context="node_inventory",
    )

    return raw


def validate_inventory_identity_match(
    node_inventory: dict[str, Any],
    marker_inventory: dict[str, Any],
) -> None:
    """Prove that node_inventory and marker_inventory have the same node set
    and the same identity fields (P0-1 exact-node equality across artifacts).

    Both inventories must agree on:
      - node_ids / node_markers keys (exact set equality)
      - commit_sha, run_id, run_attempt, python_version
    """
    node_ids_from_inv = set(node_inventory.get("node_ids", []))
    node_ids_from_marker = set(marker_inventory.get("node_markers", {}).keys())

    if node_ids_from_inv != node_ids_from_marker:
        missing_in_inv = node_ids_from_marker - node_ids_from_inv
        extra_in_inv = node_ids_from_inv - node_ids_from_marker
        raise BenchmarkAuthorityError(
            "node_inventory/marker_inventory node set mismatch: "
            f"missing_in_inv={sorted(missing_in_inv)}, extra_in_inv={sorted(extra_in_inv)}"
        )

    for field in ("commit_sha", "run_id", "python_version"):
        inv_val = str(node_inventory.get(field, ""))
        marker_val = str(marker_inventory.get(field, ""))
        if inv_val != marker_val:
            raise BenchmarkAuthorityError(
                f"{field} mismatch between node_inventory and marker_inventory: "
                f"inv={inv_val!r}, marker={marker_val!r}"
            )

    inv_attempt = node_inventory.get("run_attempt")
    marker_attempt = marker_inventory.get("run_attempt")
    if inv_attempt != marker_attempt:
        raise BenchmarkAuthorityError(
            f"run_attempt mismatch between node_inventory ({inv_attempt}) "
            f"and marker_inventory ({marker_attempt})"
        )


# ── Executed benchmark evidence validation ────────────────────────────────


def validate_executed_benchmark_evidence(
    *,
    marker_inventory_path: Path,
    node_inventory_path: Path | None,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
    expected_python_version: str,
) -> frozenset[str]:
    """Read and cross-validate the marker and node inventory files, then
    return the frozen set of validated benchmark node IDs.

    This function reads real files — it does **not** accept caller-supplied
    booleans.  It enforces:

    1. The marker inventory exists, is valid JSON, has matching identity
       fields (P0-3), and contains at least one benchmark node.
    2. When a node inventory is provided, its node set must exactly equal
       the marker inventory node set (P0-1 exact-node equality).
    3. All benchmark node IDs are derived from the validated marker data,
       not from external or fabricated sources.

    Returns the frozen set of benchmark node IDs suitable for
    ``_build_executed_artifact(validated_evidence_node_ids=...)``.
    """
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

    validated_set: frozenset[str] = frozenset(benchmark_nodes)

    if node_inventory_path is not None:
        node_inv = load_and_validate_node_inventory(
            node_inventory_path,
            expected_commit_sha=expected_commit_sha,
            expected_run_id=expected_run_id,
            expected_run_attempt=expected_run_attempt,
            expected_python_version=expected_python_version,
        )
        validate_inventory_identity_match(node_inv, marker_inv)
        # P0-1: every benchmark node must also appear in the node inventory
        inv_node_ids = frozenset(node_inv.get("node_ids", []))
        missing_in_inv = validated_set - inv_node_ids
        if missing_in_inv:
            raise BenchmarkAuthorityError(
                f"benchmark nodes not in node_inventory: {sorted(missing_in_inv)}"
            )

    return validated_set


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
    """
    # Schema version
    if artifact.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"schema_version must be {_SCHEMA_VERSION}, got {artifact.get('schema_version')!r}"
        )

    # Track
    if artifact.get("track") != "nightly":
        raise BenchmarkAuthorityError(f"track must be 'nightly', got {artifact.get('track')!r}")

    # Identity binding — exact match
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


def _cli_collect(args: Any) -> None:
    """CLI subcommand: collect marker and node inventories, validate identity."""
    marker_inv = load_marker_inventory(
        Path(args.marker_inventory),
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )
    benchmark_nodes = extract_benchmark_nodes(marker_inv)
    print(f"Collected {len(benchmark_nodes)} benchmark nodes from {args.marker_inventory}")

    if args.node_inventory:
        node_inv = load_and_validate_node_inventory(
            Path(args.node_inventory),
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
            expected_python_version=args.python_version,
        )
        validate_inventory_identity_match(node_inv, marker_inv)
        print("Node and marker inventories identity-bound ✓")


def _cli_generate(args: Any) -> None:
    """CLI subcommand: generate benchmark-authority.json (N/A or executed).

    When benchmark nodes exist and --pytest-exit-code is provided, builds
    an executed artifact.  When zero benchmark nodes exist, builds a
    not_applicable artifact.
    """
    marker_inv = load_marker_inventory(
        Path(args.marker_inventory),
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )
    benchmark_nodes = extract_benchmark_nodes(marker_inv)

    if len(benchmark_nodes) == 0:
        artifact = _build_not_applicable_artifact(
            commit_sha=args.commit_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            python_version=args.python_version,
        )
    else:
        pytest_exit_code = args.pytest_exit_code
        if pytest_exit_code is None:
            raise BenchmarkAuthorityError("executed path requires --pytest-exit-code")
        artifact = _build_executed_artifact(
            commit_sha=args.commit_sha,
            run_id=args.run_id,
            run_attempt=args.run_attempt,
            python_version=args.python_version,
            benchmark_node_count=len(benchmark_nodes),
            benchmark_node_ids=benchmark_nodes,
            pytest_exit_code=pytest_exit_code,
            producer_authoritative=args.producer_authoritative,
        )

    save_authority_artifact(artifact, Path(args.output))
    print(
        f"Benchmark authority: status={artifact['status']}, "
        f"node_count={artifact['benchmark_node_count']}, "
        f"authority_valid={artifact['authority_valid']}"
    )


def _cli_execute(args: Any) -> None:
    """CLI subcommand: read evidence files and build executed artifact."""
    validated_nodes = validate_executed_benchmark_evidence(
        marker_inventory_path=Path(args.marker_inventory),
        node_inventory_path=Path(args.node_inventory) if args.node_inventory else None,
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    if not validated_nodes:
        raise BenchmarkAuthorityError("executed path requires benchmark nodes in evidence")

    artifact = _build_executed_artifact(
        commit_sha=args.commit_sha,
        run_id=args.run_id,
        run_attempt=args.run_attempt,
        python_version=args.python_version,
        benchmark_node_count=len(validated_nodes),
        benchmark_node_ids=sorted(validated_nodes),
        pytest_exit_code=args.pytest_exit_code,
        producer_authoritative=args.producer_authoritative,
        validated_evidence_node_ids=validated_nodes,
    )

    save_authority_artifact(artifact, Path(args.output))
    print(
        f"Benchmark authority: status={artifact['status']}, "
        f"node_count={artifact['benchmark_node_count']}, "
        f"authority_valid={artifact['authority_valid']}"
    )


def _cli_validate(args: Any) -> None:
    """CLI subcommand: validate a benchmark-authority.json artifact."""
    artifact = load_authority_artifact(Path(args.artifact))

    validate_authority_artifact(
        artifact,
        expected_commit_sha=args.commit_sha,
        expected_run_id=args.run_id,
        expected_run_attempt=args.run_attempt,
        expected_python_version=args.python_version,
    )

    # Optional: cross-validate against evidence files
    if args.marker_inventory and args.node_inventory:
        validate_executed_benchmark_evidence(
            marker_inventory_path=Path(args.marker_inventory),
            node_inventory_path=Path(args.node_inventory),
            expected_commit_sha=args.commit_sha,
            expected_run_id=args.run_id,
            expected_run_attempt=args.run_attempt,
            expected_python_version=args.python_version,
        )
        print("Evidence cross-validation passed ✓")

    print(
        f"Authority artifact validation PASS: "
        f"status={artifact.get('status')}, "
        f"authority_valid={artifact.get('authority_valid')}"
    )


def main() -> None:
    """CLI: generate or validate benchmark authority artifacts.

    Subcommands (P0-4 locked execution):
      collect   — Read and validate marker/node inventory identity binding
      execute   — Read evidence files and build the executed artifact
      validate  — Validate an existing authority artifact
    """
    import argparse

    parser = argparse.ArgumentParser(description="Benchmark authority tooling for nightly CI")
    sub = parser.add_subparsers(dest="command")

    # ── Shared identity arguments ────────────────────────────────────────
    def _add_identity_args(p: argparse.ArgumentParser) -> None:
        p.add_argument("--commit-sha", required=True)
        p.add_argument("--run-id", required=True)
        p.add_argument("--run-attempt", required=True, type=int)
        p.add_argument("--python-version", required=True)

    # ── collect ──────────────────────────────────────────────────────────
    collect_p = sub.add_parser(
        "collect",
        help="Validate marker and node inventory identity binding",
    )
    collect_p.add_argument(
        "--marker-inventory",
        required=True,
        help="Path to node-marker-inventory.json",
    )
    collect_p.add_argument(
        "--node-inventory",
        default=None,
        help="Path to node-inventory.json (optional, for cross-validation)",
    )
    _add_identity_args(collect_p)

    # ── execute ──────────────────────────────────────────────────────────
    execute_p = sub.add_parser("execute", help="Build executed authority artifact from evidence")
    execute_p.add_argument(
        "--marker-inventory",
        required=True,
        help="Path to node-marker-inventory.json",
    )
    execute_p.add_argument(
        "--node-inventory",
        default=None,
        help="Path to node-inventory.json (optional, for cross-validation)",
    )
    execute_p.add_argument(
        "--output",
        required=True,
        help="Output path for benchmark-authority.json",
    )
    execute_p.add_argument("--pytest-exit-code", required=True, type=int)
    execute_p.add_argument(
        "--producer-authoritative",
        action="store_true",
        default=False,
        dest="producer_authoritative",
    )
    _add_identity_args(execute_p)

    # ── validate ─────────────────────────────────────────────────────────
    validate_p = sub.add_parser("validate", help="Validate an authority artifact")
    validate_p.add_argument(
        "--artifact",
        required=True,
        help="Path to benchmark-authority.json",
    )
    validate_p.add_argument(
        "--marker-inventory",
        default=None,
        help="Optional path to marker inventory for cross-validation",
    )
    validate_p.add_argument(
        "--node-inventory",
        default=None,
        help="Optional path to node inventory for cross-validation",
    )
    _add_identity_args(validate_p)

    # ── generate (N/A or executed) ──────────────────────────────────────
    gen_p = sub.add_parser(
        "generate",
        help="Generate benchmark-authority.json (N/A or executed)",
    )
    gen_p.add_argument(
        "--marker-inventory",
        required=True,
        help="Path to node-marker-inventory.json",
    )
    gen_p.add_argument(
        "--output",
        required=True,
        help="Output path for benchmark-authority.json",
    )
    gen_p.add_argument("--pytest-exit-code", type=int, default=None)
    gen_p.add_argument(
        "--producer-authoritative",
        action="store_true",
        default=False,
        dest="producer_authoritative",
    )
    _add_identity_args(gen_p)

    args = parser.parse_args()

    try:
        if args.command == "collect":
            _cli_collect(args)
        elif args.command == "execute":
            _cli_execute(args)
        elif args.command == "validate":
            _cli_validate(args)
        elif args.command == "generate":
            _cli_generate(args)
        else:
            parser.print_help()
            sys.exit(1)
    except BenchmarkAuthorityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
