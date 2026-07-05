"""Section 18.8 — Validation and blocker separation tests."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hexagent.case_revisions import (
    CaseRevision,
    InMemoryCaseRevisionRepository,
    InvalidRevisionPayload,
    MissingRevisionAuthority,
    RestrictedContentViolation,
    RevisionHashMismatch,
    assert_revision_authority_resolves,
    scan_payload_for_restricted_content,
    validate_revision,
)

from ._factories import build_revision


def test_structural_blockers_raise_invalid_revision_payload() -> None:
    """Section 12.1 — structural blockers surface as
    ``InvalidRevisionPayload``."""
    from dataclasses import replace

    repo = InMemoryCaseRevisionRepository()
    # Empty revision_id is structurally invalid (Section 12.1).
    rev = build_revision(revision_id="placeholder-id")
    rev_empty = replace(rev, revision_id="")
    with pytest.raises(InvalidRevisionPayload):
        repo.create_revision(
            revision=rev_empty,
            actor_id="t",
            source="ci",
            occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        )


def test_hash_mismatch_raises_revision_hash_mismatch() -> None:
    """Section 12.2 — hash mismatches surface as
    ``RevisionHashMismatch``."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    from dataclasses import replace

    rev2 = build_revision(revision_id="rev-2", revision_number=2, parent_revision_id="rev-1")
    # Corrupt the payload_hash.
    rev2_bad = replace(rev2, payload_hash="0" * 64)
    with pytest.raises(RevisionHashMismatch) as ei:
        repo.create_revision(
            revision=rev2_bad, actor_id="t", source="ci", occurred_at=rev1.created_at
        )
    assert ei.value.hash_field == "payload_hash"


def test_missing_authority_raises_missing_revision_authority() -> None:
    """Section 12.3 — missing authority raises
    ``MissingRevisionAuthority``."""
    rev = build_revision(revision_id="rev-1", revision_number=1)
    # Add an authority reference to identity.
    rev_with_ref = CaseRevision(
        revision_id=rev.revision_id,
        case_id=rev.case_id,
        root_case_id=rev.root_case_id,
        revision_number=rev.revision_number,
        parent_revision_id=rev.parent_revision_id,
        parent_chain_hash=rev.parent_chain_hash,
        payload_hash=rev.payload_hash,
        domain_snapshot_hash=rev.domain_snapshot_hash,
        payload=rev.payload,
        identity={**rev.identity, "authority_references": {"property_provider": "x"}},
        provenance=rev.provenance,
        created_at=rev.created_at,
        created_by=rev.created_by,
        committed_at=rev.committed_at,
        committed_by=rev.committed_by,
        status=rev.status,
        optimistic_concurrency_token=rev.optimistic_concurrency_token,
    )

    with pytest.raises(MissingRevisionAuthority) as ei:
        assert_revision_authority_resolves(rev_with_ref)
    assert ei.value.missing_authority == "property_provider"


def test_restricted_content_raises_restricted_content_violation() -> None:
    """Section 12.4 — restricted content raises
    ``RestrictedContentViolation``."""

    with pytest.raises(RestrictedContentViolation) as ei:
        scan_payload_for_restricted_content({"description": "internal://handbook/ASME-B31-3-quote"})
    # The literal token "ASME" still triggers detection (the placeholder
    # tag is metadata; the token appearance is still restricted).
    assert ei.value.violation_kind == "standard_body"


def test_blockers_and_warnings_are_disjoint() -> None:
    """Section 12.7 — blockers and warnings live in disjoint lists."""
    rev = build_revision(
        revision_id="rev-1",
        revision_number=1,
        identity={
            "case_id": "case-1",
            "_legacy_marker": True,
            "tombstone_chain_length": 10,
        },
    )
    result = validate_revision(rev)
    blocker_paths = {b.path for b in result.blockers}
    warning_paths = {w.path for w in result.warnings}
    # Disjoint per Section 12.7.
    assert blocker_paths.isdisjoint(warning_paths)


def test_stale_expected_parent_is_not_a_warning() -> None:
    """Section 12.5 + 12.7 — stale expected_parent MUST NOT be emitted as
    a warning. Concurrency checks live at the repository layer; the
    validate_revision helper therefore MUST NOT surface this as a
    warning."""
    rev = build_revision(
        revision_id="rev-1",
        revision_number=1,
        expected_parent_revision_id="WRONG",
    )
    result = validate_revision(rev)
    # No warning about stale expected_parent.
    assert not any("expected_parent" in w.path.lower() for w in result.warnings)
