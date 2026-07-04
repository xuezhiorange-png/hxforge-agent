"""Tests for license boundary enforcement (Section 4.1 / 4.2 / 5 / 6 / 16)."""

from __future__ import annotations

import pytest

from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.license_boundary import (
    PROJECT_INTERNAL_AUTHORITY,
    enforce_full_license_boundary,
    enforce_internal_authority_for_internal_sources,
    enforce_license_evidence_required,
    enforce_metadata_only,
    enforce_no_forbidden_marker,
    enforce_non_redistribution,
    enforce_vendor_permission_scope,
)


def _base_rule() -> dict:
    """Return a minimal INTERNAL_ENGINEERING_RULE that satisfies the boundary."""
    return {
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "license_evidence": PROJECT_INTERNAL_AUTHORITY,
        "forbidden_content_marker_check": [],
        "rule_body": {"statement": "ok"},
    }


def test_license_evidence_required_present() -> None:
    enforce_license_evidence_required(_base_rule())


def test_license_evidence_required_missing_rejected() -> None:
    rule = _base_rule()
    rule.pop("license_evidence")
    with pytest.raises(RulePackValidationError) as exc:
        enforce_license_evidence_required(rule)
    assert exc.value.path == "license_evidence"


def test_internal_authority_enforced_for_internal() -> None:
    rule = _base_rule()
    enforce_internal_authority_for_internal_sources(rule)


def test_internal_authority_required_for_internal_rejected() -> None:
    rule = _base_rule()
    rule["license_evidence"] = "Apache-2.0"
    with pytest.raises(RulePackValidationError):
        enforce_internal_authority_for_internal_sources(rule)


def test_internal_authority_required_for_derived_rejected() -> None:
    rule = _base_rule()
    rule["source_class"] = "DERIVED_ENGINEERING_RULE"
    rule["license_evidence"] = "CC-BY-4.0"
    with pytest.raises(RulePackValidationError):
        enforce_internal_authority_for_internal_sources(rule)


def test_forbidden_marker_empty_passes() -> None:
    enforce_no_forbidden_marker(_base_rule())


def test_forbidden_marker_nonempty_rejected() -> None:
    rule = _base_rule()
    rule["forbidden_content_marker_check"] = ["standard_full_text"]
    with pytest.raises(RulePackValidationError) as exc:
        enforce_no_forbidden_marker(rule)
    assert exc.value.path == "forbidden_content_marker_check"


def test_forbidden_marker_unknown_rejected() -> None:
    rule = _base_rule()
    rule["forbidden_content_marker_check"] = ["unknown_marker"]
    with pytest.raises(RulePackValidationError):
        enforce_no_forbidden_marker(rule)


def test_reference_only_restricted_body_metadata_passes() -> None:
    rule = {
        "source_class": "REFERENCE_ONLY_RESTRICTED_STANDARD",
        "license_evidence": "SPDX-License-Identifier",
        "forbidden_content_marker_check": [],
        "rule_body": {
            "bibliographic_metadata": {"standard": "ISO 12345"},
            "citation": "section 4.2",
        },
    }
    enforce_metadata_only(rule)


def test_reference_only_restricted_body_engineering_rejected() -> None:
    rule = {
        "source_class": "REFERENCE_ONLY_RESTRICTED_STANDARD",
        "license_evidence": "SPDX-License-Identifier",
        "forbidden_content_marker_check": [],
        "rule_body": {"calculation": "Q = m * c * dT"},
    }
    with pytest.raises(RulePackValidationError):
        enforce_metadata_only(rule)


def test_vendor_permission_scope_repository_storage_present_passes() -> None:
    rule = {
        "source_class": "VENDOR_PERMISSIONED",
        "license_evidence": "permission-evidence://vendor/foo",
        "forbidden_content_marker_check": [],
        "rule_body": {"statement": "x"},
        "human_entered_evidence": {
            "vendor_permission_evidence": {
                "permission_scope": ["repository_storage", "repository_redistribution"]
            }
        },
    }
    enforce_vendor_permission_scope(rule, operation="repository_storage")


def test_vendor_permission_scope_repository_storage_missing_rejected() -> None:
    rule = {
        "source_class": "VENDOR_PERMISSIONED",
        "license_evidence": "permission-evidence://vendor/foo",
        "forbidden_content_marker_check": [],
        "rule_body": {"statement": "x"},
        "human_entered_evidence": {
            "vendor_permission_evidence": {"permission_scope": ["usage_scope"]}
        },
    }
    with pytest.raises(RulePackValidationError):
        enforce_vendor_permission_scope(rule, operation="repository_storage")


def test_vendor_permission_scope_redistribution_missing_rejected() -> None:
    rule = {
        "source_class": "VENDOR_PERMISSIONED",
        "license_evidence": "permission-evidence://vendor/foo",
        "forbidden_content_marker_check": [],
        "rule_body": {"statement": "x"},
        "human_entered_evidence": {
            "vendor_permission_evidence": {"permission_scope": ["repository_storage"]}
        },
    }
    with pytest.raises(RulePackValidationError):
        enforce_vendor_permission_scope(rule, operation="repository_redistribution")


def test_full_license_boundary_internal_passes() -> None:
    enforce_full_license_boundary(_base_rule())


def test_non_redistribution_rejects_redistribute_marker() -> None:
    rule = {
        "source_class": "USER_PROVIDED_LICENSED_SUMMARY",
        "license_evidence": "permission-evidence://user/foo",
        "forbidden_content_marker_check": [],
        "rule_body": {"redistribute": True},
    }
    with pytest.raises(RulePackValidationError):
        enforce_non_redistribution(rule)


def test_non_redistribution_allows_metadata_only_body() -> None:
    rule = {
        "source_class": "USER_PROVIDED_LICENSED_SUMMARY",
        "license_evidence": "permission-evidence://user/foo",
        "forbidden_content_marker_check": [],
        "rule_body": {"summary": "user summary text"},
    }
    enforce_non_redistribution(rule)
