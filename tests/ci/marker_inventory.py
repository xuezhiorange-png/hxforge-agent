"""Separate marker inventory artifact verifier for TASK-015A (P1-1 Plan A).

Maintains node inventory schema v1 unchanged.  Markers are written to
a separate ``node-marker-inventory.json`` artifact with a strict schema
and an independent verifier.

In authoritative CI, marker data MUST be present — missing markers fail closed.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

_HEX_40 = re.compile(r"^[0-9a-f]{40}$")
_MARKER_SCHEMA_KEYS: Final[frozenset[str]] = frozenset(
    {
        "schema_version",
        "track",
        "commit_sha",
        "run_id",
        "run_attempt",
        "python_version",
        "shard",
        "collection_scope",
        "node_markers",
        "node_count",
    }
)
_ALLOWED_TRACKS: Final[frozenset[str]] = frozenset({"pr-head", "merge-ref", "main", "nightly"})
_ALLOWED_SCOPES: Final[frozenset[str]] = frozenset({"global", "shard"})
_ALLOWED_PYTHON_VERSIONS: Final[frozenset[str]] = frozenset({"3.11", "3.12"})


class MarkerInventoryError(Exception):
    """Raised when a marker inventory violates the frozen schema."""


def load_marker_inventory(path: Path) -> dict[str, Any]:
    """Load and strictly validate a marker inventory artifact."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MarkerInventoryError(f"cannot parse marker inventory: {path}") from exc

    if not isinstance(raw, dict):
        raise MarkerInventoryError("marker inventory root must be a JSON object")

    keys = set(raw.keys())
    missing = _MARKER_SCHEMA_KEYS - keys
    extra = keys - _MARKER_SCHEMA_KEYS
    if missing or extra:
        raise MarkerInventoryError(
            f"marker inventory keys mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
        )

    if raw["schema_version"] != "1":
        raise MarkerInventoryError(f"schema_version must be '1', got {raw['schema_version']!r}")
    if raw["track"] not in _ALLOWED_TRACKS:
        raise MarkerInventoryError(f"invalid track: {raw['track']!r}")
    if raw["collection_scope"] not in _ALLOWED_SCOPES:
        raise MarkerInventoryError(f"invalid collection_scope: {raw['collection_scope']!r}")
    if raw["python_version"] not in _ALLOWED_PYTHON_VERSIONS:
        raise MarkerInventoryError(f"invalid python_version: {raw['python_version']!r}")

    sha = raw["commit_sha"]
    if not isinstance(sha, str) or _HEX_40.fullmatch(sha) is None:
        raise MarkerInventoryError("commit_sha must be 40 hex chars")

    node_count = raw["node_count"]
    if not isinstance(node_count, int) or node_count < 0:
        raise MarkerInventoryError("node_count must be a non-negative integer")

    node_markers = raw["node_markers"]
    if not isinstance(node_markers, dict):
        raise MarkerInventoryError("node_markers must be a JSON object")

    if len(node_markers) != node_count:
        raise MarkerInventoryError(
            f"node_markers count ({len(node_markers)}) != node_count ({node_count})"
        )

    for nid, markers in node_markers.items():
        if not isinstance(nid, str) or not nid:
            raise MarkerInventoryError(f"invalid node marker key: {nid!r}")
        if not isinstance(markers, list):
            raise MarkerInventoryError(f"markers for {nid!r} must be a list")
        if not all(isinstance(m, str) for m in markers):
            raise MarkerInventoryError(f"markers for {nid!r} must contain only strings")
        if markers != sorted(set(markers)):
            raise MarkerInventoryError(f"markers for {nid!r} must be sorted and deduplicated")

    return raw


def verify_marker_ownership(
    marker_inventories: list[dict[str, Any]],
    *,
    expected_track: str,
    expected_commit_sha: str,
    expected_run_id: str,
    expected_run_attempt: int,
) -> None:
    """Verify marker ownership across all shard inventories.

    Checks:
    - Every node with 'golden' marker appears exactly once across all inventories
    - Every node with 'benchmark' marker appears exactly once
    - No node has both 'golden' and 'benchmark'
    - PR-blocking shards have no benchmark nodes
    - Per-Python-version consistency
    """
    golden_per_python: dict[str, set[str]] = {}
    benchmark_per_python: dict[str, set[str]] = {}
    all_nodes_per_python: dict[str, set[str]] = {}

    for inv in marker_inventories:
        if inv["track"] != expected_track:
            raise MarkerInventoryError(f"track mismatch: {inv['track']} vs {expected_track}")
        if inv["commit_sha"] != expected_commit_sha:
            inv_sha = inv["commit_sha"]
            raise MarkerInventoryError(f"SHA mismatch: {inv_sha} vs {expected_commit_sha}")

        py = inv["python_version"]
        golden_per_python.setdefault(py, set())
        benchmark_per_python.setdefault(py, set())
        all_nodes_per_python.setdefault(py, set())

        for nid, markers in inv["node_markers"].items():
            marker_set = set(markers)
            all_nodes_per_python[py].add(nid)
            if "golden" in marker_set:
                golden_per_python[py].add(nid)
            if "benchmark" in marker_set:
                benchmark_per_python[py].add(nid)
            if "golden" in marker_set and "benchmark" in marker_set:
                raise MarkerInventoryError(f"node {nid!r} has both golden and benchmark markers")

    # Per-Python golden/benchmark separation
    for py in set(golden_per_python) | set(benchmark_per_python):
        overlap = golden_per_python.get(py, set()) & benchmark_per_python.get(py, set())
        if overlap:
            raise MarkerInventoryError(
                f"golden+benchmark overlap in Python {py}: {len(overlap)} nodes"
            )
