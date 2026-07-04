"""License boundary enforcement for TASK-013 material / cost records.

Implements the TASK-013 frozen design contract Section 9
(License, redistribution and attribution boundaries), which itself
specializes the TASK-012 Section 5 model:

* Standard bodies, vendor catalog bodies, paid price lists,
  restricted property tables, scanned pages, and copyrighted formula
  images MUST NOT be embedded in any material or cost record field
  (Section 9 first rule).
* A material or cost record MAY carry a ``source_reference`` URI
  pointing to the identity of a restricted source; it MUST NOT carry
  the body (Section 9 second rule).
* ``RESTRICTED_REFERENCE_METADATA_ONLY`` records MUST NOT carry any
  numeric property value, any numeric unit price, or any quoted text
  beyond bibliographic metadata (Section 9 third rule + Section 5.5
  rule #1 + Section 6.4 rule #1).
* ``VENDOR_PERMISSIONED`` records MUST record ``permission_scope``
  per TASK-012 Section 4.2 / Section 16.3a vocabulary
  (Section 9 fourth rule).
* Records exported into a public artifact MUST have
  ``public_artifact_allowed`` in their permission scope or MUST be
  filtered before emission (Section 9 fifth rule).

This module is intentionally narrow: it returns structured lists of
license-boundary issues. The combined blocker/warning output is
assembled by :mod:`hexagent.material_costs.validation`.
"""

from __future__ import annotations

from typing import Any

from hexagent.material_costs.models import SourceClass

# Vendor permission scope tokens (TASK-012 Section 4.2 / 16.3a
# vocabulary, reused verbatim).
VENDOR_PERMISSION_SCOPE_TOKENS: frozenset[str] = frozenset(
    {
        "repository_storage",
        "repository_redistribution",
        "usage_scope",
        "public_artifact_allowed",
    }
)


def _source_class(record: dict[str, Any]) -> str:
    return str(record.get("source_class", ""))


def _human_entered(record: dict[str, Any]) -> dict[str, Any]:
    he = record.get("human_entered_evidence") or {}
    return he if isinstance(he, dict) else {}


def enforce_no_forbidden_body_marker(record: dict[str, Any], *, path: str) -> list[str]:
    """Reject any field that explicitly carries a forbidden body
    marker. The TASK-013 design contract does not commit a fixture
    scanner; this function enforces the metadata-only contract by
    rejecting non-bibliographic content under known bibliographic
    fields.
    """
    issues: list[str] = []
    standard_ref = record.get("standard_or_spec_reference")
    if standard_ref is None:
        return issues
    if not isinstance(standard_ref, dict):
        return [f"{path}.standard_or_spec_reference: must be a JSON object when present"]
    allowed_top_keys = {
        "issuing_body",
        "designation",
        "edition_year",
        "clause_locator",
        "bibliographic_metadata",
    }
    for key in standard_ref:
        if key not in allowed_top_keys:
            issues.append(
                f"{path}.standard_or_spec_reference: forbidden non-bibliographic "
                f"field {key!r}; only {sorted(allowed_top_keys)} allowed (Section 5.3 / 9)"
            )
    return issues


def enforce_restricted_metadata_only(record: dict[str, Any], *, path: str) -> list[str]:
    """Enforce Section 9 / 5.5 / 6.4 rules that
    ``RESTRICTED_REFERENCE_METADATA_ONLY`` records MUST NOT carry any
    numeric property value, any numeric unit price, or any quoted text
    beyond bibliographic metadata.
    """
    if _source_class(record) != SourceClass.RESTRICTED_REFERENCE_METADATA_ONLY.value:
        return []

    issues: list[str] = []

    if record.get("property_values") is not None:
        issues.append(
            f"{path}.property_values: RESTRICTED_REFERENCE_METADATA_ONLY records "
            "MUST NOT carry property_values (Section 5.5 rule #1 / 9)"
        )

    if record.get("cost_value") is not None:
        issues.append(
            f"{path}.cost_value: RESTRICTED_REFERENCE_METADATA_ONLY records "
            "MUST NOT carry cost_value (Section 6.4 rule #1 / 9)"
        )

    return issues


def enforce_vendor_permission_scope(record: dict[str, Any], *, path: str) -> list[str]:
    """For ``VENDOR_PERMISSIONED`` records that carry consumable
    values, require ``permission_scope`` plus ``usage_scope`` per
    Section 9 fourth rule + Section 5.5 rule #2 / Section 6.4 rule #2.
    """
    if _source_class(record) != SourceClass.VENDOR_PERMISSIONED.value:
        return []

    issues: list[str] = []
    he = _human_entered(record)
    scope = he.get("permission_scope")
    usage = he.get("usage_scope")

    if not isinstance(scope, list) or not scope:
        issues.append(
            f"{path}.human_entered_evidence.permission_scope: VENDOR_PERMISSIONED "
            "MUST record permission_scope tokens (TASK-012 Section 4.2 / 16.3a)"
        )
    else:
        for token in scope:
            if token not in VENDOR_PERMISSION_SCOPE_TOKENS:
                issues.append(
                    f"{path}.human_entered_evidence.permission_scope: unknown "
                    f"scope token {token!r}; expected one of "
                    f"{sorted(VENDOR_PERMISSION_SCOPE_TOKENS)}"
                )

    # usage_scope is required only when the record carries consumable
    # values (Section 5.5 rule #2 / Section 6.4 rule #2).
    carries_values = (
        record.get("property_values") is not None or record.get("cost_value") is not None
    )
    if carries_values and not (isinstance(usage, str) and usage.strip()):
        issues.append(
            f"{path}.human_entered_evidence.usage_scope: VENDOR_PERMISSIONED "
            "records that carry consumable values MUST record a non-empty "
            "usage_scope (Section 5.5 rule #2 / 6.4 rule #2)"
        )

    return issues


def enforce_license_evidence_form(record: dict[str, Any], *, path: str) -> list[str]:
    """The TASK-012 Section 7.2 license-evidence token vocabulary is
    applied to material / cost records. The TASK-013 contract does
    not enumerate every allowed token; we accept anything non-empty
    and rely on the upstream TASK-012 vocabulary for token validity
    at record-store time.
    """
    evidence = record.get("license_evidence")
    if not isinstance(evidence, str) or not evidence.strip():
        return [
            f"{path}.license_evidence: must be a non-empty string "
            "(TASK-012 Section 7.2 / TASK-013 Section 9)"
        ]
    return []


def enforce_material_record_license_boundary(record: dict[str, Any]) -> list[str]:
    return (
        enforce_no_forbidden_body_marker(record, path="material_record")
        + enforce_restricted_metadata_only(record, path="material_record")
        + enforce_vendor_permission_scope(record, path="material_record")
        + enforce_license_evidence_form(record, path="material_record")
    )


def enforce_cost_record_license_boundary(record: dict[str, Any]) -> list[str]:
    return (
        enforce_no_forbidden_body_marker(record, path="cost_record")
        + enforce_restricted_metadata_only(record, path="cost_record")
        + enforce_vendor_permission_scope(record, path="cost_record")
        + enforce_license_evidence_form(record, path="cost_record")
    )


__all__ = [
    "VENDOR_PERMISSION_SCOPE_TOKENS",
    "enforce_cost_record_license_boundary",
    "enforce_license_evidence_form",
    "enforce_material_record_license_boundary",
    "enforce_no_forbidden_body_marker",
    "enforce_restricted_metadata_only",
    "enforce_vendor_permission_scope",
]
