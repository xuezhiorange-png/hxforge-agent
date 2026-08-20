from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tests.ci.node_inventory import (
    InventoryError,
    NodeInventory,
    load_inventory,
    verify_per_version,
)
from tests.ci.shard_manifest import ShardManifest, load_manifest

pytestmark = pytest.mark.pure

_SHA = "a" * 40
_FINGERPRINT = "b" * 64


def _payload(
    *,
    scope: str,
    shard: str | None,
    files: dict[str, list[str]],
    version: str = "3.12",
    run_attempt: int = 1,
) -> dict[str, Any]:
    node_ids = sorted(node for nodes in files.values() for node in nodes)
    return {
        "schema_version": "1",
        "collection_scope": scope,
        "python_version": version,
        "pytest_version": "9.1.1",
        "commit_sha": _SHA,
        "track": "pr-head",
        "shard": shard,
        "run_id": "123",
        "run_attempt": run_attempt,
        "behavior_fingerprint_sha256": _FINGERPRINT,
        "node_count": len(node_ids),
        "node_ids": node_ids,
        "file_records": [
            {
                "file": file_path,
                "node_count": len(nodes),
                "zero_node_reason": None if nodes else "unsupported-version",
                "reason_authority": None if nodes else "manifest",
                "evidence": None if nodes else "python contract",
            }
            for file_path, nodes in sorted(files.items())
        ],
    }


def _write_inventory(tmp_path: Path, name: str, payload: dict[str, Any]) -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return path


def _write_manifest(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    (repo / "tests" / "unit").mkdir(parents=True)
    (repo / "tests" / "unit" / "test_a.py").write_text("def test_a(): pass\n")
    (repo / "tests" / "unit" / "test_b.py").write_text("def test_b(): pass\n")
    path = repo / "manifest.yaml"
    path.write_text(
        """\
version: "1"
shards:
  - name: shard-a
    job: shard-a
    python: ["3.11", "3.12"]
    files: [tests/unit/test_a.py]
    timeout: 120
  - name: shard-b
    job: shard-b
    python: ["3.12"]
    files: [tests/unit/test_b.py]
    timeout: 120
"""
    )
    return repo, path


def test_load_inventory_accepts_exact_schema_and_unicode_node_ids(
    tmp_path: Path,
) -> None:
    payload = _payload(
        scope="shard",
        shard="shard-a",
        files={"tests/unit/test_a.py": ["tests/unit/test_a.py::test_x[空 格]"]},
    )

    inventory = load_inventory(_write_inventory(tmp_path, "inventory.json", payload))

    assert inventory.shard == "shard-a"
    assert inventory.node_ids == ("tests/unit/test_a.py::test_x[空 格]",)


@pytest.mark.parametrize(
    ("mutator", "message"),
    [
        (lambda value: value.update(shard="bad") or value, "global inventory requires"),
        (
            lambda value: value.update(node_count=99) or value,
            "node_count does not equal",
        ),
        (
            lambda value: value.update(node_ids=list(reversed(value["node_ids"]))) or value,
            "sorted lexicographically",
        ),
        (
            lambda value: value.update(behavior_fingerprint_sha256="bad") or value,
            "64 lowercase hex",
        ),
    ],
)
def test_load_inventory_rejects_schema_violations(
    tmp_path: Path, mutator: Any, message: str
) -> None:
    payload = _payload(
        scope="global",
        shard=None,
        files={
            "tests/unit/test_a.py": [
                "tests/unit/test_a.py::test_b",
                "tests/unit/test_a.py::test_a",
            ]
        },
    )
    payload["node_ids"] = sorted(payload["node_ids"])
    mutated = mutator(payload)

    with pytest.raises(InventoryError, match=message):
        load_inventory(_write_inventory(tmp_path, "invalid.json", mutated))


def test_zero_node_requires_frozen_reason_authority_and_evidence(
    tmp_path: Path,
) -> None:
    payload = _payload(
        scope="shard",
        shard="shard-a",
        files={"tests/unit/test_a.py": []},
    )
    payload["file_records"][0]["zero_node_reason"] = "unknown"

    with pytest.raises(InventoryError, match="unknown zero-node reason"):
        load_inventory(_write_inventory(tmp_path, "zero.json", payload))


def test_verify_per_version_proves_union_and_disjointness(tmp_path: Path) -> None:
    repo, manifest_path = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_path, repo_root=repo)
    global_inventory = load_inventory(
        _write_inventory(
            tmp_path,
            "global.json",
            _payload(
                scope="global",
                shard=None,
                files={
                    "tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"],
                    "tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"],
                },
            ),
        )
    )
    shard_a = load_inventory(
        _write_inventory(
            tmp_path,
            "a.json",
            _payload(
                scope="shard",
                shard="shard-a",
                files={"tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"]},
            ),
        )
    )
    shard_b = load_inventory(
        _write_inventory(
            tmp_path,
            "b.json",
            _payload(
                scope="shard",
                shard="shard-b",
                files={"tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"]},
            ),
        )
    )

    verify_per_version(
        manifest=manifest,
        version="3.12",
        global_inventory=global_inventory,
        shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
    )


def test_verify_per_version_rejects_duplicate_node_ownership(tmp_path: Path) -> None:
    repo, manifest_path = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_path, repo_root=repo)
    shared_node = "tests/unit/test_a.py::test_shared"
    global_inventory = load_inventory(
        _write_inventory(
            tmp_path,
            "global-overlap.json",
            _payload(
                scope="global",
                shard=None,
                files={
                    "tests/unit/test_a.py": [shared_node],
                    "tests/unit/test_b.py": ["tests/unit/test_b.py::test_other"],
                },
            ),
        )
    )
    shard_a = load_inventory(
        _write_inventory(
            tmp_path,
            "a-overlap.json",
            _payload(
                scope="shard",
                shard="shard-a",
                files={"tests/unit/test_a.py": [shared_node]},
            ),
        )
    )
    valid_shard_b = load_inventory(
        _write_inventory(
            tmp_path,
            "b-overlap.json",
            _payload(
                scope="shard",
                shard="shard-b",
                files={"tests/unit/test_b.py": ["tests/unit/test_b.py::test_other"]},
            ),
        )
    )
    overlapping_shard_b = replace(valid_shard_b, node_ids=(shared_node,))

    with pytest.raises(InventoryError, match="appears in both"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={
                "shard-a": shard_a,
                "shard-b": overlapping_shard_b,
            },
        )


def _load_complete_inventories(
    tmp_path: Path,
    *,
    global_attempt: int = 1,
    shard_a_attempt: int = 1,
    shard_b_attempt: int = 1,
) -> tuple[ShardManifest, NodeInventory, NodeInventory, NodeInventory]:
    repo, manifest_path = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_path, repo_root=repo)
    global_inventory = load_inventory(
        _write_inventory(
            tmp_path,
            "global.json",
            _payload(
                scope="global",
                shard=None,
                run_attempt=global_attempt,
                files={
                    "tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"],
                    "tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"],
                },
            ),
        )
    )
    shard_a = load_inventory(
        _write_inventory(
            tmp_path,
            "a.json",
            _payload(
                scope="shard",
                shard="shard-a",
                run_attempt=shard_a_attempt,
                files={"tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"]},
            ),
        )
    )
    shard_b = load_inventory(
        _write_inventory(
            tmp_path,
            "b.json",
            _payload(
                scope="shard",
                shard="shard-b",
                run_attempt=shard_b_attempt,
                files={"tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"]},
            ),
        )
    )
    return manifest, global_inventory, shard_a, shard_b


def test_verify_per_version_default_strict_mode_rejects_mixed_attempt(
    tmp_path: Path,
) -> None:
    manifest, global_inventory, shard_a, shard_b = _load_complete_inventories(
        tmp_path, global_attempt=1, shard_a_attempt=2, shard_b_attempt=1
    )

    with pytest.raises(InventoryError, match="run_attempt mismatch"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
            allow_mixed_run_attempts=False,
        )


def test_verify_per_version_explicit_fallback_accepts_mixed_attempt(
    tmp_path: Path,
) -> None:
    manifest, global_inventory, shard_a, shard_b = _load_complete_inventories(
        tmp_path, global_attempt=1, shard_a_attempt=1, shard_b_attempt=2
    )

    verify_per_version(
        manifest=manifest,
        version="3.12",
        global_inventory=global_inventory,
        shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
        allow_mixed_run_attempts=True,
        consumer_run_attempt=2,
    )


def test_verify_per_version_future_attempt_rejected_in_fallback_mode(
    tmp_path: Path,
) -> None:
    manifest, global_inventory, shard_a, shard_b = _load_complete_inventories(
        tmp_path, global_attempt=1, shard_a_attempt=3, shard_b_attempt=1
    )

    with pytest.raises(InventoryError, match="outside 1..2"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
            allow_mixed_run_attempts=True,
            consumer_run_attempt=2,
        )


@pytest.mark.parametrize(
    "field",
    [
        "commit_sha",
        "track",
        "run_id",
        "pytest_version",
        "behavior_fingerprint_sha256",
    ],
)
def test_verify_per_version_non_attempt_authority_mismatch_still_rejected(
    tmp_path: Path, field: str
) -> None:
    manifest, global_inventory, shard_a, shard_b = _load_complete_inventories(
        tmp_path, global_attempt=1, shard_a_attempt=2, shard_b_attempt=1
    )
    mutated_value = {
        "commit_sha": "c" * 40,
        "track": "merge-ref",
        "run_id": "999",
        "pytest_version": "9.0.0",
        "behavior_fingerprint_sha256": "d" * 64,
    }[field]
    shard_a = replace(shard_a, **{field: mutated_value})

    with pytest.raises(InventoryError, match=f"{field} mismatch"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
            allow_mixed_run_attempts=True,
            consumer_run_attempt=2,
        )


def test_verify_per_version_fallback_requires_consumer_run_attempt(
    tmp_path: Path,
) -> None:
    manifest, global_inventory, shard_a, shard_b = _load_complete_inventories(tmp_path)

    with pytest.raises(InventoryError, match="consumer_run_attempt is required"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={"shard-a": shard_a, "shard-b": shard_b},
            allow_mixed_run_attempts=True,
        )


# ---------------------------------------------------------------------------
# node_markers rejection tests (P0-2: frozen schema v1 has no node_markers)
# ---------------------------------------------------------------------------


def test_load_inventory_rejects_node_markers_key(tmp_path: Path) -> None:
    """Inventory payloads containing a 'node_markers' key must be rejected."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    # Inject the forbidden key after payload construction
    payload["node_markers"] = {node_id: ["golden", "pure"]}
    with pytest.raises(InventoryError, match="unknown.*node_markers"):
        load_inventory(_write_inventory(tmp_path, "markers.json", payload))


def test_load_inventory_rejects_empty_node_markers_key(tmp_path: Path) -> None:
    """Even an empty node_markers dict is rejected in the frozen schema."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    payload["node_markers"] = {}
    with pytest.raises(InventoryError, match="unknown.*node_markers"):
        load_inventory(_write_inventory(tmp_path, "empty_markers.json", payload))
