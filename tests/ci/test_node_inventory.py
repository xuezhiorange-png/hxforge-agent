from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from tests.ci.node_inventory import InventoryError, load_inventory, verify_per_version
from tests.ci.shard_manifest import load_manifest

pytestmark = pytest.mark.pure

_SHA = "a" * 40
_FINGERPRINT = "b" * 64


def _payload(
    *,
    scope: str,
    shard: str | None,
    files: dict[str, list[str]],
    version: str = "3.12",
    node_markers: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    node_ids = sorted(node for nodes in files.values() for node in nodes)
    markers = node_markers if node_markers is not None else {nid: [] for nid in node_ids}
    return {
        "schema_version": "1",
        "collection_scope": scope,
        "python_version": version,
        "pytest_version": "9.1.1",
        "commit_sha": _SHA,
        "track": "pr-head",
        "shard": shard,
        "run_id": "123",
        "run_attempt": 1,
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
        "node_markers": {nid: sorted(markers.get(nid, [])) for nid in node_ids},
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


# ---------------------------------------------------------------------------
# node_markers validation tests
# ---------------------------------------------------------------------------


def test_load_inventory_accepts_node_markers(tmp_path: Path) -> None:
    """Valid node_markers with sorted, unique entries are accepted."""
    markers = {
        "tests/unit/test_a.py::test_a": ["golden", "pure"],
        "tests/unit/test_b.py::test_b": ["provider"],
    }
    payload = _payload(
        scope="global",
        shard=None,
        files={
            "tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"],
            "tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"],
        },
        node_markers=markers,
    )
    inventory = load_inventory(_write_inventory(tmp_path, "ok.json", payload))
    assert inventory.node_markers == (
        ("tests/unit/test_a.py::test_a", ("golden", "pure")),
        ("tests/unit/test_b.py::test_b", ("provider",)),
    )


def test_load_inventory_backward_compat_no_node_markers(tmp_path: Path) -> None:
    """Inventories without node_markers field are still accepted."""
    payload = _payload(
        scope="global",
        shard=None,
        files={
            "tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"],
        },
    )
    del payload["node_markers"]
    inventory = load_inventory(_write_inventory(tmp_path, "no_markers.json", payload))
    assert inventory.node_markers == ()


def test_load_inventory_rejects_unsorted_node_markers(tmp_path: Path) -> None:
    """node_markers lists that are not sorted are rejected."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    # Override node_markers with unsorted list (bypass _payload's sorting)
    payload["node_markers"] = {node_id: ["pure", "golden"]}
    with pytest.raises(InventoryError, match="must be sorted and deduplicated"):
        load_inventory(_write_inventory(tmp_path, "unsorted.json", payload))


def test_load_inventory_rejects_duplicate_node_markers(tmp_path: Path) -> None:
    """node_markers lists with duplicates are rejected."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    # Override node_markers with duplicate entries
    payload["node_markers"] = {node_id: ["golden", "golden"]}
    with pytest.raises(InventoryError, match="must be sorted and deduplicated"):
        load_inventory(_write_inventory(tmp_path, "dupes.json", payload))


def test_load_inventory_rejects_missing_node_marker_entry(tmp_path: Path) -> None:
    """node_markers that do not cover every node_id are rejected."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    # Override node_markers with empty dict – coverage mismatch
    payload["node_markers"] = {}
    with pytest.raises(InventoryError, match="coverage mismatch"):
        load_inventory(_write_inventory(tmp_path, "missing.json", payload))


def test_load_inventory_rejects_extra_node_marker_entry(tmp_path: Path) -> None:
    """node_markers with entries for nonexistent nodes are rejected."""
    node_id = "tests/unit/test_a.py::test_a"
    payload = _payload(
        scope="global",
        shard=None,
        files={"tests/unit/test_a.py": [node_id]},
    )
    # Override node_markers with an extra nonexistent node
    payload["node_markers"] = {
        node_id: [],
        "tests/unit/test_a.py::test_extra": ["pure"],
    }
    with pytest.raises(InventoryError, match="coverage mismatch"):
        load_inventory(_write_inventory(tmp_path, "extra.json", payload))


def test_verify_per_version_rejects_marker_mismatch(tmp_path: Path) -> None:
    """verify_per_version raises when a node has different markers in
    global vs shard inventories."""
    repo, manifest_path = _write_manifest(tmp_path)
    manifest = load_manifest(manifest_path, repo_root=repo)
    global_inventory = load_inventory(
        _write_inventory(
            tmp_path,
            "global-m.json",
            _payload(
                scope="global",
                shard=None,
                files={
                    "tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"],
                    "tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"],
                },
                node_markers={
                    "tests/unit/test_a.py::test_a": ["golden"],
                    "tests/unit/test_b.py::test_b": ["pure"],
                },
            ),
        )
    )
    # Shard a has correct marker; shard b has a *different* marker
    shard_a = load_inventory(
        _write_inventory(
            tmp_path,
            "a-m.json",
            _payload(
                scope="shard",
                shard="shard-a",
                files={"tests/unit/test_a.py": ["tests/unit/test_a.py::test_a"]},
                node_markers={
                    "tests/unit/test_a.py::test_a": ["golden"],
                },
            ),
        )
    )
    shard_b_wrong = load_inventory(
        _write_inventory(
            tmp_path,
            "b-m.json",
            _payload(
                scope="shard",
                shard="shard-b",
                files={"tests/unit/test_b.py": ["tests/unit/test_b.py::test_b"]},
                node_markers={
                    "tests/unit/test_b.py::test_b": ["benchmark"],  # mismatch
                },
            ),
        )
    )
    with pytest.raises(InventoryError, match="marker mismatch"):
        verify_per_version(
            manifest=manifest,
            version="3.12",
            global_inventory=global_inventory,
            shard_inventories={"shard-a": shard_a, "shard-b": shard_b_wrong},
        )
