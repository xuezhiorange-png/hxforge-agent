"""Top-level rule-pack validation orchestrator.

Combines schema validation, license-boundary enforcement, provenance
validation, and canonical-hash verification into a single ``validate_rule_pack``
function that returns a structured report.

This module is the entry point for the validator CLI; tests should call
``validate_rule_pack`` directly to assert behavior.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.license_boundary import enforce_full_license_boundary
from hexagent.rule_packs.loader import load_rule_pack
from hexagent.rule_packs.provenance import (
    validate_provenance_edges,
    validate_supersedes_edges,
)
from hexagent.rule_packs.schema import (
    validate_canonical_hash,
    validate_manifest,
    validate_manifest_canonical_hash,
    validate_manifest_only_references_approved_rules,
    validate_rule,
)


def validate_rule_pack(root: Path) -> dict[str, Any]:
    """Validate a rule-pack directory and return a report.

    The report is a JSON-serializable dict::

        {
          "rule_pack_path": "<absolute path>",
          "status": "ok" | "fail",
          "errors": [
             {"path": "<field path>", "message": "<error text>"},
             ...
          ],
          "manifest": {...},     # optional, present on ok
          "rule_count": <int>,   # optional, present on ok
        }

    On validation failure, ``status="fail"`` and ``errors`` is non-empty.
    The function NEVER raises on validation failure — callers (CLI, tests)
    inspect the report.
    """
    if not isinstance(root, Path):
        root = Path(root)
    errors: list[dict[str, str]] = []

    # Phase 1: load
    try:
        loaded = load_rule_pack(root)
    except RulePackValidationError as exc:
        return _fail(root, [{"path": exc.path or "loader", "message": str(exc)}])
    except Exception as exc:  # loader exceptions are non-validation errors.
        return _fail(root, [{"path": "loader", "message": str(exc)}])

    manifest = loaded["manifest"]
    rules = loaded["rules"]
    edges = loaded["provenance_edges"]

    # Phase 2: manifest schema
    try:
        validate_manifest(manifest)
    except RulePackValidationError as exc:
        errors.append({"path": exc.path, "message": str(exc)})

    # Phase 3: rule artifact schemas + license boundary + canonical hash
    for rule_id, rule in rules.items():
        rule_prefix = f"rules[{rule_id}]"
        try:
            validate_rule(rule)
        except RulePackValidationError as exc:
            errors.append({"path": f"{rule_prefix}.{exc.path}", "message": str(exc)})
            continue  # do not chain license / hash checks on a schema-broken rule
        try:
            enforce_full_license_boundary(rule)
        except RulePackValidationError as exc:
            errors.append({"path": f"{rule_prefix}.{exc.path}", "message": str(exc)})
        try:
            validate_canonical_hash(rule)
        except RulePackValidationError as exc:
            errors.append({"path": f"{rule_prefix}.{exc.path}", "message": str(exc)})

    # Phase 4: provenance graph
    try:
        validate_provenance_edges(rules, edges)
    except RulePackValidationError as exc:
        errors.append({"path": exc.path, "message": str(exc)})
    try:
        validate_supersedes_edges(rules, edges)
    except RulePackValidationError as exc:
        errors.append({"path": exc.path, "message": str(exc)})

    # Phase 5: manifest references only approved rules
    try:
        validate_manifest_only_references_approved_rules(manifest, rules)
    except RulePackValidationError as exc:
        errors.append({"path": exc.path, "message": str(exc)})

    # Phase 6: manifest canonical_hash integrity
    try:
        validate_manifest_canonical_hash(manifest)
    except RulePackValidationError as exc:
        errors.append({"path": exc.path, "message": str(exc)})

    if errors:
        return _fail(root, errors)
    return {
        "rule_pack_path": str(root.resolve()),
        "status": "ok",
        "errors": [],
        "rule_count": len(rules),
        "manifest": manifest,
    }


def _fail(root: Path, errors: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "rule_pack_path": str(root.resolve()),
        "status": "fail",
        "errors": errors,
    }
