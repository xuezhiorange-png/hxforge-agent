"""Rule-pack schema validation (Section 7).

Implements structural validation for:

* Rule-pack manifests (Section 7.1).
* Rule artifacts (Section 7.2).
* Provenance edges (delegated to ``provenance.py``).
* Canonical hash integrity (Section 13).

This module does NOT enforce license boundary rules — see ``license_boundary.py``.
"""

from __future__ import annotations

import re
from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.models import (
    ALLOWED_STANDARD_FAMILIES,
    CONDITIONAL_RULE_FIELDS,
    INTL_JURISDICTION,
    MANIFEST_REQUIRED_FIELDS,
    RULE_REQUIRED_FIELDS,
    SOURCE_EVIDENCE_MIRROR_FIELDS,
    SOURCE_EVIDENCE_REQUIRED_FIELDS,
    ApprovalStatus,
    SourceClass,
)

# ISO 3166-1 alpha-2: two ASCII uppercase letters.
_ISO_3166_RE = re.compile(r"^[A-Z]{2}$")

# RFC 3339 UTC with Z suffix is the canonical timestamp form (Section 13).
_RFC3339_UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$")

# Semver-compatible rule_version (Section 12).
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?$")


def validate_manifest(manifest: dict[str, Any]) -> None:
    """Validate the rule-pack manifest against Section 7.1."""
    if not isinstance(manifest, dict):
        raise RulePackValidationError(
            "manifest must be a JSON object",
            path="manifest",
        )
    for field in MANIFEST_REQUIRED_FIELDS:
        if field not in manifest:
            raise RulePackValidationError(
                f"manifest missing required field {field!r} (Section 7.1)",
                path=f"manifest.{field}",
            )
    rules = manifest["rules"]
    if not isinstance(rules, list):
        raise RulePackValidationError(
            "manifest.rules must be a list of rule_id strings",
            path="manifest.rules",
        )
    if manifest["rule_count"] != len(rules):
        raise RulePackValidationError(
            f"manifest.rule_count={manifest['rule_count']} does not match "
            f"len(rules)={len(rules)} (Section 7.1)",
            path="manifest.rule_count",
        )
    jurisdiction = manifest["target_jurisdiction"]
    if jurisdiction != INTL_JURISDICTION and not _ISO_3166_RE.match(jurisdiction):
        raise RulePackValidationError(
            f"manifest.target_jurisdiction {jurisdiction!r} must be ISO "
            f"3166-1 alpha-2 or {INTL_JURISDICTION!r} (Section 7.1)",
            path="manifest.target_jurisdiction",
        )
    family = manifest["target_standard_family"]
    if family not in ALLOWED_STANDARD_FAMILIES:
        raise RulePackValidationError(
            f"manifest.target_standard_family {family!r} not in "
            f"{sorted(ALLOWED_STANDARD_FAMILIES)} (Section 7.1)",
            path="manifest.target_standard_family",
        )
    ts = manifest["creation_timestamp_utc"]
    if not isinstance(ts, str) or not _RFC3339_UTC_RE.match(ts):
        raise RulePackValidationError(
            f"manifest.creation_timestamp_utc must be RFC 3339 UTC with Z suffix; got {ts!r}",
            path="manifest.creation_timestamp_utc",
        )


def validate_rule(rule: dict[str, Any]) -> None:
    """Validate a single rule artifact against Section 7.2."""
    if not isinstance(rule, dict):
        raise RulePackValidationError(
            "rule must be a JSON object",
            path="rule",
        )
    for field in RULE_REQUIRED_FIELDS:
        if field not in rule:
            raise RulePackValidationError(
                f"rule missing required field {field!r} (Section 7.2)",
                path=f"rule.{field}",
            )
    # rule_version semver-compatible
    rv = rule["rule_version"]
    if not isinstance(rv, str) or not _SEMVER_RE.match(rv):
        raise RulePackValidationError(
            f"rule.rule_version {rv!r} must be semver-compatible (Section 12)",
            path="rule.rule_version",
        )
    # jurisdiction
    j = rule["jurisdiction"]
    if j != INTL_JURISDICTION and not _ISO_3166_RE.match(j):
        raise RulePackValidationError(
            f"rule.jurisdiction {j!r} must be ISO 3166-1 alpha-2 or "
            f"{INTL_JURISDICTION!r} (Section 7.2)",
            path="rule.jurisdiction",
        )
    # standard_family
    sf = rule["standard_family"]
    if sf not in ALLOWED_STANDARD_FAMILIES:
        raise RulePackValidationError(
            f"rule.standard_family {sf!r} not in {sorted(ALLOWED_STANDARD_FAMILIES)} (Section 7.2)",
            path="rule.standard_family",
        )
    # source_class is one of the frozen enum
    try:
        source_class = SourceClass(rule["source_class"])
    except ValueError as exc:
        raise RulePackValidationError(
            f"rule.source_class {rule['source_class']!r} not in frozen "
            "set (Section 4 / Section 7.2)",
            path="rule.source_class",
        ) from exc
    # approval_status is one of the frozen enum
    try:
        ApprovalStatus(rule["approval_status"])
    except ValueError as exc:
        raise RulePackValidationError(
            f"rule.approval_status {rule['approval_status']!r} not in "
            "frozen set (Section 7.2 / Section 14)",
            path="rule.approval_status",
        ) from exc
    # review_status
    rs = rule["review_status"]
    allowed_rs = {"pending", "accepted", "accepted_with_caveats", "rejected"}
    if rs not in allowed_rs:
        raise RulePackValidationError(
            f"rule.review_status {rs!r} not in {sorted(allowed_rs)} (Section 7.2)",
            path="rule.review_status",
        )
    # provenance_edges non-empty list of strings
    pe = rule["provenance_edges"]
    if not isinstance(pe, list) or not pe:
        raise RulePackValidationError(
            "rule.provenance_edges must be a non-empty list of edge ids "
            "(Section 7.2 + Section 11.1)",
            path="rule.provenance_edges",
        )
    for edge_id in pe:
        if not isinstance(edge_id, str) or not edge_id:
            raise RulePackValidationError(
                f"rule.provenance_edges contains non-string id {edge_id!r}",
                path="rule.provenance_edges",
            )
    # forbidden_content_marker_check must be a list (empty or not, validated
    # later in license_boundary)
    fcm = rule["forbidden_content_marker_check"]
    if not isinstance(fcm, list):
        raise RulePackValidationError(
            "rule.forbidden_content_marker_check must be a list",
            path="rule.forbidden_content_marker_check",
        )
    # source_evidence mandatory fields (Section 10)
    src_ev = rule["source_evidence"]
    if not isinstance(src_ev, dict):
        raise RulePackValidationError(
            "rule.source_evidence must be a JSON object (Section 7.2)",
            path="rule.source_evidence",
        )
    for field in SOURCE_EVIDENCE_REQUIRED_FIELDS:
        if field not in src_ev:
            raise RulePackValidationError(
                f"rule.source_evidence missing required field {field!r} (Section 10)",
                path=f"rule.source_evidence.{field}",
            )
    # source_evidence mirror consistency (Section 7.2 direct-field policy):
    # rule identity fields MUST be byte-equal to their source_evidence counterparts.
    for rule_field, source_field in SOURCE_EVIDENCE_MIRROR_FIELDS.items():
        if rule[rule_field] != src_ev[source_field]:
            raise RulePackValidationError(
                f"rule.{rule_field}={rule[rule_field]!r} does not match "
                f"source_evidence.{source_field}={src_ev[source_field]!r} "
                "(Section 7.2 direct-field policy)",
                path=f"rule.{rule_field}",
            )
    # Conditional fields per source_class (Section 7.2 + Section 8 + Section 9).
    required = CONDITIONAL_RULE_FIELDS.get(source_class, frozenset())
    for field in required:
        if field not in rule:
            raise RulePackValidationError(
                f"source_class={source_class.value} requires field "
                f"{field!r} (Section 8 / Section 9)",
                path=f"rule.{field}",
            )


def validate_canonical_hash(rule: dict[str, Any]) -> None:
    """Verify the rule's recorded canonical_hash matches recomputation."""
    expected = rule["canonical_hash"]
    actual = canonical_sha256(rule)
    if expected != actual:
        raise RulePackValidationError(
            f"rule.canonical_hash mismatch: recorded={expected!r} computed={actual!r} (Section 13)",
            path="rule.canonical_hash",
        )


def validate_manifest_canonical_hash(manifest: dict[str, Any]) -> None:
    """Verify the rule-pack manifest's canonical_hash matches."""
    expected = manifest["canonical_hash"]
    actual = canonical_sha256(manifest)
    if expected != actual:
        raise RulePackValidationError(
            f"manifest.canonical_hash mismatch: recorded={expected!r} "
            f"computed={actual!r} (Section 13)",
            path="manifest.canonical_hash",
        )


def validate_manifest_only_references_approved_rules(
    manifest: dict[str, Any],
    rules: dict[str, dict[str, Any]],
) -> None:
    """Enforce Section 15.6: only approved rules in an approved manifest.

    Every rule id listed in ``manifest.rules`` MUST have
    ``approval_status == approved``. This is a structural check; the
    manifest's own ``approval_status`` is recorded separately on the
    manifest.
    """
    for rule_id in manifest.get("rules", []):
        rule = rules.get(rule_id)
        if rule is None:
            raise RulePackValidationError(
                f"manifest references rule_id {rule_id!r} but no rule artifact with that id exists",
                path=f"manifest.rules[{rule_id!r}]",
            )
        if rule.get("approval_status") != ApprovalStatus.APPROVED.value:
            raise RulePackValidationError(
                f"manifest references rule_id {rule_id!r} but rule's "
                "approval_status is "
                f"{rule.get('approval_status')!r} (Section 15.6)",
                path=f"manifest.rules[{rule_id!r}]",
            )
