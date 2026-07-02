"""Strict structured node-inventory validation for TASK-015A.

P0-2: Frozen node inventory schema v1 does NOT include node_markers.
       Markers live exclusively in node-marker-inventory.json.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, Literal, cast

from tests.ci.shard_manifest import PythonVersion, ShardManifest

CollectionScope = Literal["global", "shard"]
Track = Literal["pr-head", "merge-ref", "main", "nightly"]
ZeroNodeReason = Literal[
    "conditional-definition",
    "module-collection-skip",
    "hook-deselection",
    "unsupported-version",
]

_ALLOWED_SCOPES: Final = {"global", "shard"}
_ALLOWED_TRACKS: Final = {"pr-head", "merge-ref", "main", "nightly"}
_ALLOWED_PYTHON_VERSIONS: Final = {"3.11", "3.12"}
_ALLOWED_ZERO_NODE_REASONS: Final = {
    "conditional-definition",
    "module-collection-skip",
    "hook-deselection",
    "unsupported-version",
}
# Frozen schema v1 keys — node_markers is NOT included
_INVENTORY_KEYS: Final = {
    "schema_version",
    "collection_scope",
    "python_version",
    "pytest_version",
    "commit_sha",
    "track",
    "shard",
    "run_id",
    "run_attempt",
    "behavior_fingerprint_sha256",
    "node_count",
    "node_ids",
    "file_records",
}
_FILE_RECORD_KEYS: Final = {
    "file",
    "node_count",
    "zero_node_reason",
    "reason_authority",
    "evidence",
}
_HEX_40 = re.compile(r"^[0-9a-f]{40}$")
_HEX_64 = re.compile(r"^[0-9a-f]{64}$")


class InventoryError(ValueError):
    """Raised when a node inventory violates the frozen schema."""


@dataclass(frozen=True, slots=True)
class FileRecord:
    file: str
    node_count: int
    zero_node_reason: ZeroNodeReason | None
    reason_authority: str | None
    evidence: str | None


@dataclass(frozen=True, slots=True)
class NodeInventory:
    schema_version: str
    collection_scope: CollectionScope
    python_version: PythonVersion
    pytest_version: str
    commit_sha: str
    track: Track
    shard: str | None
    run_id: str
    run_attempt: int
    behavior_fingerprint_sha256: str
    node_ids: tuple[str, ...]
    file_records: tuple[FileRecord, ...]

    @property
    def node_count(self) -> int:
        return len(self.node_ids)

    @property
    def node_set(self) -> frozenset[str]:
        return frozenset(self.node_ids)

    @property
    def file_set(self) -> frozenset[str]:
        return frozenset(record.file for record in self.file_records)


def _exact_keys(value: dict[str, Any], expected: set[str], context: str) -> None:
    keys = set(value)
    if keys != expected:
        raise InventoryError(
            f"{context} keys mismatch; missing={sorted(expected - keys)!r}, "
            f"unknown={sorted(keys - expected)!r}"
        )


def _non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise InventoryError(f"{context} must be a non-empty string")
    if value != value.strip():
        raise InventoryError(f"{context} must not contain surrounding whitespace")
    return value


def _positive_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise InventoryError(f"{context} must be a positive integer")
    return value


def _non_negative_int(value: Any, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise InventoryError(f"{context} must be a non-negative integer")
    return value


def _node_file(node_id: str) -> str:
    return node_id.split("::", maxsplit=1)[0]


def _parse_file_record(raw: Any, index: int) -> FileRecord:
    context = f"file_records[{index}]"
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise InventoryError(f"{context} must be an object with string keys")
    typed_raw = cast(dict[str, Any], raw)
    _exact_keys(typed_raw, _FILE_RECORD_KEYS, context)

    file_path = _non_empty_string(typed_raw["file"], f"{context}.file")
    if "\\" in file_path or not file_path.startswith("tests/"):
        raise InventoryError(f"{context}.file must be a normalized tests/ path")
    node_count = _non_negative_int(typed_raw["node_count"], f"{context}.node_count")
    reason = typed_raw["zero_node_reason"]
    authority = typed_raw["reason_authority"]
    evidence = typed_raw["evidence"]

    if node_count > 0:
        if reason is not None or authority is not None or evidence is not None:
            raise InventoryError(f"{context} non-zero record must have null zero-node metadata")
        return FileRecord(file_path, node_count, None, None, None)

    if reason not in _ALLOWED_ZERO_NODE_REASONS:
        raise InventoryError(f"{context} has an unknown zero-node reason: {reason!r}")
    authority_string = _non_empty_string(authority, f"{context}.reason_authority")
    evidence_string = _non_empty_string(evidence, f"{context}.evidence")
    return FileRecord(
        file_path,
        0,
        cast(ZeroNodeReason, reason),
        authority_string,
        evidence_string,
    )


def load_inventory(path: Path) -> NodeInventory:
    """Load and strictly validate a structured node inventory.

    Frozen schema v1 — node_markers is NOT a valid key.
    Markers live in node-marker-inventory.json.
    """

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise InventoryError(f"unable to parse node inventory: {path}") from exc
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise InventoryError("node inventory root must be an object with string keys")
    typed_raw = cast(dict[str, Any], raw)
    _exact_keys(typed_raw, _INVENTORY_KEYS, "inventory")

    if typed_raw["schema_version"] != "1":
        raise InventoryError("inventory schema_version must equal '1'")

    scope = typed_raw["collection_scope"]
    if scope not in _ALLOWED_SCOPES:
        raise InventoryError(f"unknown collection_scope: {scope!r}")
    shard = typed_raw["shard"]
    if scope == "global" and shard is not None:
        raise InventoryError("global inventory requires shard=null")
    if scope == "shard" and (not isinstance(shard, str) or not shard.strip()):
        raise InventoryError("shard inventory requires a non-empty shard name")

    python_version = typed_raw["python_version"]
    if python_version not in _ALLOWED_PYTHON_VERSIONS:
        raise InventoryError(f"unsupported python_version: {python_version!r}")
    track = typed_raw["track"]
    if track not in _ALLOWED_TRACKS:
        raise InventoryError(f"unsupported track: {track!r}")

    pytest_version = _non_empty_string(typed_raw["pytest_version"], "pytest_version")
    commit_sha = _non_empty_string(typed_raw["commit_sha"], "commit_sha")
    if _HEX_40.fullmatch(commit_sha) is None:
        raise InventoryError("commit_sha must be a lowercase 40-character hexadecimal SHA")
    run_id = _non_empty_string(typed_raw["run_id"], "run_id")
    run_attempt = _positive_int(typed_raw["run_attempt"], "run_attempt")
    fingerprint = _non_empty_string(
        typed_raw["behavior_fingerprint_sha256"], "behavior_fingerprint_sha256"
    )
    if _HEX_64.fullmatch(fingerprint) is None:
        raise InventoryError("behavior_fingerprint_sha256 must be 64 lowercase hex characters")

    raw_node_ids = typed_raw["node_ids"]
    if not isinstance(raw_node_ids, list) or not all(
        isinstance(node_id, str) and node_id for node_id in raw_node_ids
    ):
        raise InventoryError("node_ids must be a list of non-empty strings")
    node_ids = tuple(raw_node_ids)
    if any("\\" in node_id for node_id in node_ids):
        raise InventoryError("node_ids must use normalized forward slashes")
    if node_ids != tuple(sorted(node_ids)):
        raise InventoryError("node_ids must be sorted lexicographically")
    if len(node_ids) != len(set(node_ids)):
        raise InventoryError("duplicate node_ids are prohibited")
    declared_node_count = _non_negative_int(typed_raw["node_count"], "node_count")
    if declared_node_count != len(node_ids):
        raise InventoryError("node_count does not equal len(node_ids)")

    raw_records = typed_raw["file_records"]
    if not isinstance(raw_records, list):
        raise InventoryError("file_records must be a list")
    file_records = tuple(
        _parse_file_record(raw_record, index) for index, raw_record in enumerate(raw_records)
    )
    record_files = tuple(record.file for record in file_records)
    if record_files != tuple(sorted(record_files)):
        raise InventoryError("file_records must be sorted by file")
    if len(record_files) != len(set(record_files)):
        raise InventoryError("duplicate file_records are prohibited")
    if sum(record.node_count for record in file_records) != len(node_ids):
        raise InventoryError("file record node counts do not sum to node_count")

    node_counts = Counter(_node_file(node_id) for node_id in node_ids)
    record_counts = {record.file: record.node_count for record in file_records}
    if node_counts != Counter(record_counts):
        raise InventoryError("file_records do not exactly match node_id file counts")

    # P0-2: node_markers MUST NOT appear in node-inventory.json
    if "node_markers" in typed_raw:
        raise InventoryError(
            "node_markers must not appear in frozen schema v1 node-inventory.json; "
            "use node-marker-inventory.json instead"
        )

    return NodeInventory(
        schema_version="1",
        collection_scope=cast(CollectionScope, scope),
        python_version=cast(PythonVersion, python_version),
        pytest_version=pytest_version,
        commit_sha=commit_sha,
        track=cast(Track, track),
        shard=cast(str | None, shard),
        run_id=run_id,
        run_attempt=run_attempt,
        behavior_fingerprint_sha256=fingerprint,
        node_ids=node_ids,
        file_records=file_records,
    )


def verify_per_version(
    *,
    manifest: ShardManifest,
    version: PythonVersion,
    global_inventory: NodeInventory,
    shard_inventories: dict[str, NodeInventory],
) -> None:
    """Prove per-version union equality and pairwise disjointness."""

    if global_inventory.collection_scope != "global" or global_inventory.shard is not None:
        raise InventoryError("global_inventory must have global scope and shard=null")
    if global_inventory.python_version != version:
        raise InventoryError("global inventory Python version mismatch")

    applicable = manifest.applicable_shards(version)
    expected_names = {shard.name for shard in applicable}
    actual_names = set(shard_inventories)
    if actual_names != expected_names:
        raise InventoryError(
            f"shard inventory set mismatch; missing={sorted(expected_names - actual_names)!r}, "
            f"unexpected={sorted(actual_names - expected_names)!r}"
        )

    expected_global_files = frozenset(file for shard in applicable for file in shard.files)
    if global_inventory.file_set != expected_global_files:
        raise InventoryError("global inventory file set does not match applicable manifest files")

    union: set[str] = set()
    owner_by_node: dict[str, str] = {}
    for shard_spec in applicable:
        inventory = shard_inventories[shard_spec.name]
        if inventory.collection_scope != "shard" or inventory.shard != shard_spec.name:
            raise InventoryError(f"inventory scope/name mismatch for shard {shard_spec.name!r}")
        if inventory.python_version != version:
            raise InventoryError(f"Python version mismatch for shard {shard_spec.name!r}")
        if inventory.file_set != frozenset(shard_spec.files):
            raise InventoryError(f"file set mismatch for shard {shard_spec.name!r}")

        authority_fields = (
            "pytest_version",
            "commit_sha",
            "track",
            "run_id",
            "run_attempt",
            "behavior_fingerprint_sha256",
        )
        for field in authority_fields:
            if getattr(inventory, field) != getattr(global_inventory, field):
                raise InventoryError(
                    f"{field} mismatch between global and shard {shard_spec.name!r}"
                )

        for node_id in inventory.node_ids:
            previous_owner = owner_by_node.get(node_id)
            if previous_owner is not None:
                raise InventoryError(
                    f"node {node_id!r} appears in both {previous_owner!r} and {shard_spec.name!r}"
                )
            owner_by_node[node_id] = shard_spec.name
        union.update(inventory.node_ids)

    missing = sorted(global_inventory.node_set - union)
    unexpected = sorted(union - global_inventory.node_set)
    if missing or unexpected:
        raise InventoryError(
            f"per-version node union mismatch; missing={missing!r}, unexpected={unexpected!r}"
        )
