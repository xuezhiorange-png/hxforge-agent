"""Tests for rule-pack schema validation (Section 7)."""

from __future__ import annotations

import pytest

from hexagent.canonical_json import canonical_sha256
from hexagent.rule_packs.errors import RulePackValidationError
from hexagent.rule_packs.schema import (
    validate_canonical_hash,
    validate_manifest,
    validate_rule,
)


def _valid_manifest() -> dict:
    m = {
        "rule_pack_id": "rp1",
        "rule_pack_version": "1.0.0",
        "rule_count": 1,
        "rules": ["r1"],
        "target_jurisdiction": "INTL",
        "target_standard_family": "INTERNAL",
        "creation_timestamp_utc": "2026-07-04T09:30:00Z",
        "review_id": "review_001",
    }
    m["canonical_hash"] = canonical_sha256(m)
    return m


def _valid_rule() -> dict:
    r = {
        "rule_id": "r1",
        "rule_version": "1.0.0",
        "rule_title": "Internal engineering rule for canonical hash",
        "source_class": "INTERNAL_ENGINEERING_RULE",
        "jurisdiction": "INTL",
        "standard_family": "INTERNAL",
        "bibliographic_reference": "internal://engineering-handbook/v1",
        "license_evidence": "project_internal_authority",
        "source_evidence": {
            "source_class": "INTERNAL_ENGINEERING_RULE",
            "source_reference": "internal://engineering-handbook/v1",
            "source_title_or_identifier": "Engineering Handbook",
            "source_locator_or_citation": "Chapter 1",
            "source_jurisdiction": "INTL",
            "license_evidence": "project_internal_authority",
        },
        "human_entered_evidence": {
            "author_identity": "eng@example.invalid",
            "author_role": "internal engineer",
            "entry_timestamp_utc": "2026-07-04T09:00:00Z",
            "review": {
                "reviewer_identity": "rev@example.invalid",
                "review_thread_reference": "review_001",
                "review_timestamp_utc": "2026-07-04T09:15:00Z",
            },
        },
        "rule_body": {"statement": "ok"},
        "forbidden_content_marker_check": [],
        "applicability_envelope": {"scope": "rp1", "units": "dimensionless"},
        "uncertainty": {"type": "structural", "note": "exact"},
        "review_status": "accepted",
        "approval_status": "approved",
        "provenance_edges": ["e1"],
    }
    r["canonical_hash"] = canonical_sha256(r)
    return r


def test_manifest_valid_passes() -> None:
    validate_manifest(_valid_manifest())


def test_manifest_rule_count_mismatch_rejected() -> None:
    m = _valid_manifest()
    m["rule_count"] = 2
    with pytest.raises(RulePackValidationError):
        validate_manifest(m)


def test_manifest_bad_jurisdiction_rejected() -> None:
    m = _valid_manifest()
    m["target_jurisdiction"] = "usa"
    # dropping canonical_hash required re-validation
    m.pop("canonical_hash", None)
    m["canonical_hash"] = canonical_sha256(m)
    with pytest.raises(RulePackValidationError):
        validate_manifest(m)


def test_manifest_unknown_standard_family_rejected() -> None:
    m = _valid_manifest()
    m["target_standard_family"] = "XYZ"
    m.pop("canonical_hash", None)
    m["canonical_hash"] = canonical_sha256(m)
    with pytest.raises(RulePackValidationError):
        validate_manifest(m)


def test_manifest_bad_timestamp_rejected() -> None:
    m = _valid_manifest()
    m["creation_timestamp_utc"] = "2026-07-04 09:30:00"
    m.pop("canonical_hash", None)
    m["canonical_hash"] = canonical_sha256(m)
    with pytest.raises(RulePackValidationError):
        validate_manifest(m)


def test_rule_valid_passes() -> None:
    validate_rule(_valid_rule())


def test_rule_unknown_source_class_rejected() -> None:
    r = _valid_rule()
    r["source_class"] = "FOO"
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_unknown_approval_status_rejected() -> None:
    r = _valid_rule()
    r["approval_status"] = "approved_v2"
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_bad_semver_rejected() -> None:
    r = _valid_rule()
    r["rule_version"] = "v1"
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_empty_provenance_edges_rejected() -> None:
    r = _valid_rule()
    r["provenance_edges"] = []
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_license_evidence_missing_rejected() -> None:
    r = _valid_rule()
    r.pop("license_evidence")
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_jurisdiction_mirror_mismatch_rejected() -> None:
    r = _valid_rule()
    r["source_evidence"]["source_jurisdiction"] = "US"
    with pytest.raises(RulePackValidationError):
        validate_rule(r)


def test_rule_canonical_hash_mismatch_rejected() -> None:
    r = _valid_rule()
    r["canonical_hash"] = "f" * 64
    with pytest.raises(RulePackValidationError):
        validate_canonical_hash(r)
