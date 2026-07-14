"""TASK-022 Slice B1 — in-memory TASK-012-compatible rule pack builders.

Pure in-memory builders for tests. NO filesystem loader is invoked; NO
production rule-pack artifact is created. Each builder returns a
``Mapping`` shape that exactly mirrors the output of
``hexagent.rule_packs.loader.load_rule_pack`` so the B1 adapter
behaves identically whether it is fed by a real loader or by these
tests.

The helpers intentionally construct a complete TASK-012 pack: every
required manifest field, every required rule field, every
provenance-edge field, and full source_evidence + canonical_hash
membership. Tests mutate a single field or rule to exercise each
specific adapter branch.

The builders follow the upstream TASK-012 schema exactly. They use
the canonical_sha256 helper from hexagent.canonical_json so the
embedded canonical_hash fields are byte-exact matches of the loader
path.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any

from hexagent.canonical_json import canonical_sha256

PROFILE_ID = "hxforge.shell_tube.shell_bundle_geometry.v1"


def _utc_now_rfc3339() -> str:
    """Return the current UTC time as RFC 3339 with a ``Z`` suffix."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rule_top_levels(rule_id: str, rule_body: dict[str, Any]) -> dict[str, Any]:
    """Helper to fill the remaining TASK-012 top-level rule fields.

    ``rule_id`` is a top-level TASK-012 field (carried directly on
    the rule artifact, NOT inside ``rule_body``), so it must be
    supplied as a separate parameter.
    """
    return {
        "rule_id": rule_id,
        "rule_version": "1.0.0",
        "rule_title": rule_id,
        "source_class": "PUBLIC_DOMAIN",
        "jurisdiction": "INTL",
        "standard_family": "INTERNAL",
        "bibliographic_reference": f"internal://test/{rule_id}",
        "license_evidence": "CC0-1.0",
        "source_evidence": {
            "source_class": "PUBLIC_DOMAIN",
            "source_reference": f"internal://test/{rule_id}",
            "source_title_or_identifier": rule_id,
            "source_locator_or_citation": "test fixture",
            "source_jurisdiction": "INTL",
            "license_evidence": "CC0-1.0",
        },
        "rule_body": rule_body,
        "forbidden_content_marker_check": [],
        "applicability_envelope": {"min": 0, "max": 100000, "units": "kW"},
        "uncertainty": {"kind": "deterministic", "value": 0.0},
        "review_status": "accepted",
        "approval_status": "approved",
        "provenance_edges": [],
    }


def _add_canonical_hash(rule: dict[str, Any]) -> dict[str, Any]:
    rule["canonical_hash"] = canonical_sha256(rule)
    return rule


def _add_provenance_edge(
    pack: dict[str, Any],
    *,
    edge_id: str,
    from_rule_id: str,
    to_rule_id: str,
    relation: str,
    evidence_ref: str,
) -> None:
    pack["provenance_edges"].append(
        {
            "edge_id": edge_id,
            "from_rule_id": from_rule_id,
            "to_rule_id": to_rule_id,
            "relation": relation,
            "evidence_ref": evidence_ref,
        }
    )


def _wrap_publisher(pack: dict[str, Any]) -> dict[str, Any]:
    """Recompute manifest.canonical_hash and add the pack as a builder."""

    def _recompute_rule_hash(rule: dict[str, Any]) -> dict[str, Any]:
        r = dict(rule)
        r["canonical_hash"] = canonical_sha256(r)
        return r

    pack["rules"] = {rule_id: _recompute_rule_hash(rule) for rule_id, rule in pack["rules"].items()}
    pack["manifest"]["canonical_hash"] = canonical_sha256(pack["manifest"])
    return pack


def make_rule_body(
    rule_id: str = "rule-public-v1",
) -> dict[str, Any]:
    """Build a minimal but complete TASK-022 rule_body projection.

    Per Issue #147 Record 3 the projection's exact field set is the
    six TASK-022 rule_body columns; the upstream ``rule_id`` is a
    top-level TASK-012 field (carried on the rule artifact directly)
    and does NOT appear inside ``rule_body``. This helper signature
    accepts ``rule_id`` as a convenience for builders that need to
    stamp the same value into several locations, but does NOT embed
    it back into ``rule_body``.
    """
    return {
        "profile_id": PROFILE_ID,
        "allowed_shell_authority_modes": [
            "CALLER_SUPPLIED_EXPLICIT",
            "APPROVED_CATALOG_SNAPSHOT",
        ],
        "minimum_bundle_peripheral_allowance_m": "0.01",
        "minimum_radial_clearance_m": "0.01",
        "maximum_position_count": 10000,
        "evidence_refs": ["ref:test:" + rule_id],
    }


def make_rule(rule_id: str = "rule-public-v1") -> dict[str, Any]:
    """Build one complete TASK-012 rule artifact."""
    return _add_canonical_hash(_rule_top_levels(rule_id, make_rule_body(rule_id)))


def make_manifest(
    *,
    rule_pack_id: str = "rp-public-shell-bundle-v1",
    rule_pack_version: str = "1.0.0",
    rules: tuple[str, ...] = ("rule-public-v1",),
) -> dict[str, Any]:
    """Build a complete TASK-012 manifest."""
    return {
        "rule_pack_id": rule_pack_id,
        "rule_pack_version": rule_pack_version,
        "rule_count": len(rules),
        "rules": list(rules),
        "target_jurisdiction": "INTL",
        "target_standard_family": "INTERNAL",
        "creation_timestamp_utc": _utc_now_rfc3339(),
        "review_id": "review-test-" + rule_pack_id,
        "canonical_hash": "placeholder_recomputed",
    }


def make_pack(
    *,
    rule_id: str = "rule-public-v1",
    extra_rule: dict[str, Any] | None = None,
    source_class: str = "PUBLIC_DOMAIN",
    license_evidence: str = "CC0-1.0",
    approval_status: str = "approved",
    source_class_for_extra: str | None = None,
) -> dict[str, Any]:
    """Build a complete in-memory TASK-012 rule-pack mapping.

    The returned mapping has the exact shape of the
    ``hexagent.rule_packs.loader.load_rule_pack`` output, but is
    constructed entirely in memory — no filesystem paths are opened.
    """
    rule_body = make_rule_body(rule_id)
    rule = _rule_top_levels(rule_id, rule_body)
    rule["source_class"] = source_class
    rule["license_evidence"] = license_evidence
    rule["approval_status"] = approval_status
    rule["source_evidence"]["source_class"] = source_class
    rule["source_evidence"]["license_evidence"] = license_evidence
    if source_class == "VENDOR_PERMISSIONED":
        rule["human_entered_evidence"] = {
            "vendor_permission_evidence": {
                "permission_id": "vendor-test-permission",
                "permission_scope": [
                    "repository_storage",
                    "repository_redistribution",
                    "usage_scope",
                    "public_artifact_allowed",
                ],
            }
        }
    _add_canonical_hash(rule)

    rules = {rule_id: deepcopy(rule)}
    rule_ids: list[str] = [rule_id]
    if extra_rule is not None:
        extra_id = extra_rule["rule_id"]
        rule_body_extra = make_rule_body(extra_id)
        top_extra = _rule_top_levels(extra_id, rule_body_extra)
        top_extra["source_class"] = source_class_for_extra or source_class
        top_extra["license_evidence"] = license_evidence
        top_extra["approval_status"] = approval_status
        top_extra["source_evidence"]["source_class"] = top_extra["source_class"]
        top_extra["source_evidence"]["license_evidence"] = license_evidence
        _add_canonical_hash(top_extra)
        rules[extra_id] = top_extra
        rule_ids.append(extra_id)

    pack: dict[str, Any] = {
        "manifest": make_manifest(rules=tuple(rule_ids)),
        "rules": rules,
        "provenance_edges": [],
        "permission_evidence": {},
    }
    edge_id = f"e-test-{rule_id}"
    _add_provenance_edge(
        pack,
        edge_id=edge_id,
        from_rule_id="external:internal:test",
        to_rule_id=rule_id,
        relation="derived_from",
        evidence_ref="ref:test:provenance",
    )
    pack["rules"][rule_id]["provenance_edges"] = [edge_id]
    if extra_rule is not None:
        extra_id = extra_rule["rule_id"]
        edge_id_extra = f"e-test-{extra_id}"
        _add_provenance_edge(
            pack,
            edge_id=edge_id_extra,
            from_rule_id="external:internal:test",
            to_rule_id=extra_id,
            relation="derived_from",
            evidence_ref="ref:test:provenance",
        )
        pack["rules"][extra_id]["provenance_edges"] = [edge_id_extra]
    return _wrap_publisher(pack)


def mutate_rule(
    pack: dict[str, Any],
    rule_id: str,
    **mutations: Any,
) -> dict[str, Any]:
    """Return a deep-copied pack where one rule is mutated, then re-hashed."""
    new_pack = deepcopy(pack)
    if rule_id not in new_pack["rules"]:
        raise KeyError(f"rule_id {rule_id!r} not in pack")
    rule = new_pack["rules"][rule_id]
    for field, value in mutations.items():
        if field == "rule_body":
            rule["rule_body"] = {**rule["rule_body"], **value}
        else:
            rule[field] = value
    _add_canonical_hash(rule)
    new_pack["manifest"]["canonical_hash"] = canonical_sha256(new_pack["manifest"])
    return new_pack
