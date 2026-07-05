"""Section 18 — Structured error model tests."""

from __future__ import annotations

import pytest

from hexagent.case_revisions import (
    VALID_CONFLICT_REASONS,
    CaseRevisionConflict,
    InvalidRevisionPayload,
    MissingRevisionAuthority,
    RestrictedContentViolation,
    RevisionHashMismatch,
    RevisionPersistenceFailure,
    StaleParentRevision,
    Task014Error,
)


def test_task014_error_is_common_base() -> None:
    """Section 16.1 — all TASK-014 errors inherit from ``Task014Error``."""
    assert issubclass(CaseRevisionConflict, Task014Error)
    assert issubclass(StaleParentRevision, Task014Error)
    assert issubclass(InvalidRevisionPayload, Task014Error)
    assert issubclass(RevisionHashMismatch, Task014Error)
    assert issubclass(MissingRevisionAuthority, Task014Error)
    assert issubclass(RevisionPersistenceFailure, Task014Error)
    assert issubclass(RestrictedContentViolation, Task014Error)


def test_error_codes_are_machine_readable() -> None:
    assert (
        CaseRevisionConflict("m", conflict_reason="concurrent_sibling").error_code
        == "case_revision_conflict"
    )
    assert StaleParentRevision("m").error_code == "stale_parent_revision"
    assert InvalidRevisionPayload("m").error_code == "invalid_revision_payload"
    assert (
        RevisionHashMismatch("m", hash_field="payload_hash").error_code == "revision_hash_mismatch"
    )
    assert (
        MissingRevisionAuthority("m", missing_authority="material").error_code
        == "missing_revision_authority"
    )
    assert RevisionPersistenceFailure("m").error_code == "revision_persistence_failure"
    assert (
        RestrictedContentViolation("m", violation_kind="standard_body").error_code
        == "restricted_content_violation"
    )


def test_case_revision_conflict_conflict_reason_enum() -> None:
    """Section 13.6 — ``conflict_reason`` MUST be one of the three values."""
    for reason in ("token_mismatch", "duplicate_idempotency_key", "concurrent_sibling"):
        err = CaseRevisionConflict("m", conflict_reason=reason)
        assert err.conflict_reason == reason
        assert err.context["conflict_reason"] == reason
    # Invalid values rejected at construction.
    with pytest.raises(ValueError):
        CaseRevisionConflict("m", conflict_reason="stale_parent")  # type: ignore[arg-type]


def test_stale_parent_revision_carries_expected_and_actual_ids() -> None:
    """Section 16.2 — StaleParentRevision carries
    expected_parent_revision_id and actual_parent_revision_id."""
    err = StaleParentRevision(
        "m",
        root_case_id="c-1",
        revision_id="r-1",
        expected_parent_revision_id="WRONG",
        actual_parent_revision_id="HEAD",
    )
    assert err.context["expected_parent_revision_id"] == "WRONG"
    assert err.context["actual_parent_revision_id"] == "HEAD"


def test_revision_persistence_failure_partial_state_always_false() -> None:
    """Section 6.8 / 13.4 — ``partial_state`` MUST be False at raise time."""
    with pytest.raises(ValueError):
        # partial_state=True is forbidden at construction.
        RevisionPersistenceFailure("m", partial_state=True)  # type: ignore[arg-type]


def test_revision_hash_mismatch_hash_field_enum() -> None:
    for field in ("payload_hash", "domain_snapshot_hash", "parent_chain_hash"):
        err = RevisionHashMismatch("m", hash_field=field)
        assert err.hash_field == field
    with pytest.raises(ValueError):
        RevisionHashMismatch("m", hash_field="unknown")  # type: ignore[arg-type]


def test_missing_revision_authority_missing_authority_enum() -> None:
    for kind in ("property_provider", "correlation", "material", "cost", "rule_pack", "benchmark"):
        err = MissingRevisionAuthority("m", missing_authority=kind)
        assert err.missing_authority == kind
    with pytest.raises(ValueError):
        MissingRevisionAuthority("m", missing_authority="unknown")  # type: ignore[arg-type]


def test_restricted_content_violation_violation_kind_enum() -> None:
    for kind in (
        "standard_body",
        "vendor_catalog_body",
        "paid_price_list",
        "restricted_property_table",
        "scanned_page",
        "formula_image",
        "copied_standard_table",
    ):
        err = RestrictedContentViolation("m", violation_kind=kind)
        assert err.violation_kind == kind
    with pytest.raises(ValueError):
        RestrictedContentViolation("m", violation_kind="unknown")  # type: ignore[arg-type]


def test_error_to_dict_is_machine_readable() -> None:
    err = CaseRevisionConflict(
        "test",
        root_case_id="c-1",
        revision_id="r-1",
        conflict_reason="concurrent_sibling",
        expected_parent_revision_id="HEAD",
        actual_parent_revision_id="OTHER",
        attempted_revision_number=2,
    )
    d = err.to_dict()
    assert d["error_code"] == "case_revision_conflict"
    assert d["root_case_id"] == "c-1"
    assert d["revision_id"] == "r-1"
    assert d["context"]["conflict_reason"] == "concurrent_sibling"


def test_stale_parent_is_not_case_revision_conflict() -> None:
    """Section 12.5 + 13.1 + 16.2 disambiguation — StaleParentRevision
    is NOT a subclass of CaseRevisionConflict."""
    assert not issubclass(StaleParentRevision, CaseRevisionConflict)
    err = StaleParentRevision("m")
    assert not isinstance(err, CaseRevisionConflict)


def test_valid_conflict_reasons_excludes_stale_parent() -> None:
    """Section 13.6 — ``stale_parent`` MUST NOT be a valid
    CaseRevisionConflict.conflict_reason enum value."""
    assert "stale_parent" not in VALID_CONFLICT_REASONS
    assert (
        frozenset({"token_mismatch", "duplicate_idempotency_key", "concurrent_sibling"})
        == VALID_CONFLICT_REASONS
    )
