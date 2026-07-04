"""Rule-pack artifact loader.

Loads a rule-pack directory from disk into Python data structures suitable
for validation. The loader is JSON-only; rule-packs are committed as JSON
artifacts for portability and human inspectability.

Directory layout (informational):

    rule_packs/<rule_pack_id>/
        manifest.json
        rules/<rule_id>.json
        provenance/<edge_id>.json
        permissions/<permission_id>.json    # vendor permission evidence

The loader is permissive: missing directories (permissions) are skipped
unless a VENDOR_PERMISSIONED rule requires them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from hexagent.rule_packs.errors import RulePackError


def load_rule_pack(root: Path) -> dict[str, Any]:
    """Load a rule-pack directory and return its in-memory representation.

    Returns a dict with keys:

    * ``manifest`` — the loaded manifest.json (dict).
    * ``rules`` — ``{rule_id: rule_dict}``.
    * ``provenance_edges`` — list of provenance edge dicts.
    * ``permission_evidence`` — ``{permission_id: dict}`` (may be empty).

    Raises ``RulePackError`` on IO or JSON decode failures.
    """
    if not isinstance(root, Path):
        root = Path(root)
    if not root.is_dir():
        raise RulePackError(f"rule-pack root is not a directory: {root}")

    manifest_path = root / "manifest.json"
    rules_dir = root / "rules"
    provenance_dir = root / "provenance"
    permissions_dir = root / "permissions"

    try:
        manifest = _read_json(manifest_path)
    except RulePackError:
        raise
    except (OSError, json.JSONDecodeError) as exc:
        raise RulePackError(f"failed to load manifest {manifest_path}: {exc}") from exc

    rules: dict[str, dict[str, Any]] = {}
    if rules_dir.is_dir():
        for path in sorted(rules_dir.glob("*.json")):
            try:
                rule = _read_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                raise RulePackError(f"failed to load rule {path}: {exc}") from exc
            rule_id = rule.get("rule_id")
            if not isinstance(rule_id, str) or not rule_id:
                raise RulePackError(
                    f"rule at {path} missing string rule_id",
                )
            if rule_id in rules:
                raise RulePackError(
                    f"duplicate rule_id {rule_id!r} (paths: {list(rules.keys())} and {path})",
                )
            rules[rule_id] = rule

    edges: list[dict[str, Any]] = []
    if provenance_dir.is_dir():
        for path in sorted(provenance_dir.glob("*.json")):
            try:
                edges.append(_read_json(path))
            except (OSError, json.JSONDecodeError) as exc:
                raise RulePackError(f"failed to load provenance edge {path}: {exc}") from exc

    permissions: dict[str, dict[str, Any]] = {}
    if permissions_dir.is_dir():
        for path in sorted(permissions_dir.glob("*.json")):
            try:
                perm = _read_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                raise RulePackError(f"failed to load permission evidence {path}: {exc}") from exc
            permission_id = perm.get("permission_id")
            if not isinstance(permission_id, str) or not permission_id:
                raise RulePackError(
                    f"permission evidence at {path} missing permission_id",
                )
            permissions[permission_id] = perm

    return {
        "manifest": manifest,
        "rules": rules,
        "provenance_edges": edges,
        "permission_evidence": permissions,
    }


def _read_json(path: os.PathLike[str] | Path) -> Any:
    with open(path, "rb") as f:
        return json.load(f)
