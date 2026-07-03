"""Governed benchmark authority for nightly CI.

Produces ``benchmark-authority.json`` — the single source of truth for
whether benchmark execution passed, was not applicable, or failed.

Two legitimate terminal states:
  A. status=not_applicable, reason=no-benchmark-nodes, authority_valid=true
  B. status=executed, pytest_exit_code=0, producer_authoritative=true,
     authority_valid=true

Every other combination must fail-closed.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Final

_SCHEMA_VERSION: Final = "1"
_ALLOWED_TRACKS: Final = frozenset({"pr-head", "merge-ref", "main", "nightly"})
_ALLOWED_PYTHON_VERSIONS: Final = frozenset({"3.11", "3.12"})
_VALID_STATUSES: Final = frozenset({"not_applicable", "executed"})
_VALID_REASONS: Final = frozenset({None, "no-benchmark-nodes"})


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
) -> dict[str, Any]:
    """Build the authority artifact for the executed benchmark case."""
    if benchmark_node_count <= 0:
        raise BenchmarkAuthorityError("executed artifact requires positive benchmark_node_count")
    if not benchmark_node_ids:
        raise BenchmarkAuthorityError("executed artifact requires non-empty benchmark_node_ids")
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


def load_marker_inventory(path: Path) -> dict[str, Any]:
    """Load and validate a node-marker-inventory.json artifact."""
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

    return raw


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
    """
    # Schema version
    if artifact.get("schema_version") != _SCHEMA_VERSION:
        raise BenchmarkAuthorityError(
            f"schema_version must be {_SCHEMA_VERSION}, got {artifact.get('schema_version')!r}"
        )

    # Track
    if artifact.get("track") != "nightly":
        raise BenchmarkAuthorityError(f"track must be 'nightly', got {artifact.get('track')!r}")

    # Identity binding
    for field, expected in (
        ("commit_sha", expected_commit_sha),
        ("run_id", expected_run_id),
        ("python_version", expected_python_version),
    ):
        actual = str(artifact.get(field, ""))
        if actual != str(expected):
            raise BenchmarkAuthorityError(
                f"{field} mismatch: got {actual!r}, expected {expected!r}"
            )

    actual_attempt = artifact.get("run_attempt")
    if not isinstance(actual_attempt, int) or actual_attempt != expected_run_attempt:
        raise BenchmarkAuthorityError(
            f"run_attempt mismatch: got {actual_attempt}, expected {expected_run_attempt}"
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


# ── CLI entry point ───────────────────────────────────────────────────────


def main() -> None:
    """CLI: generate benchmark authority artifact from marker inventory."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark-authority.json")
    parser.add_argument(
        "--marker-inventory",
        required=True,
        help="Path to node-marker-inventory.json",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for benchmark-authority.json",
    )
    parser.add_argument("--commit-sha", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--run-attempt", required=True, type=int)
    parser.add_argument("--python-version", required=True)
    parser.add_argument(
        "--pytest-exit-code",
        type=int,
        default=None,
        help="Exit code from benchmark pytest run (omit for N/A)",
    )
    parser.add_argument(
        "--producer-authoritative",
        action="store_true",
        default=None,
        dest="producer_auth_flag",
        help="Whether producer telemetry is authoritative",
    )
    args = parser.parse_args()

    try:
        marker_inv = load_marker_inventory(Path(args.marker_inventory))
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
            producer_auth = args.producer_auth_flag is True

            artifact = _build_executed_artifact(
                commit_sha=args.commit_sha,
                run_id=args.run_id,
                run_attempt=args.run_attempt,
                python_version=args.python_version,
                benchmark_node_count=len(benchmark_nodes),
                benchmark_node_ids=benchmark_nodes,
                pytest_exit_code=pytest_exit_code,
                producer_authoritative=producer_auth,
            )

        save_authority_artifact(artifact, Path(args.output))
        print(
            f"Benchmark authority: status={artifact['status']}, "
            f"node_count={artifact['benchmark_node_count']}, "
            f"authority_valid={artifact['authority_valid']}"
        )

    except BenchmarkAuthorityError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
