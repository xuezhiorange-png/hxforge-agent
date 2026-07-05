"""Section 18.5 — Concurrency tests."""

from __future__ import annotations

import pytest

from hexagent.case_revisions import (
    CaseRevisionConflict,
    InMemoryCaseRevisionRepository,
    StaleParentRevision,
)
from hexagent.case_revisions.optimistic import (
    assert_token_matches,
    mint_optimistic_concurrency_token,
)

from ._factories import build_revision


def test_concurrent_create_requests_only_one_succeeds() -> None:
    """Section 13.5 — two concurrent create-requests on the same
    root_case_id that both compute revision_number = N+1 MUST NOT both
    succeed."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)

    rev2_a = build_revision(revision_id="rev-2-a", revision_number=2, parent_revision_id="rev-1")
    rev2_b = build_revision(revision_id="rev-2-b", revision_number=2, parent_revision_id="rev-1")
    repo.create_revision(revision=rev2_a, actor_id="t", source="ci", occurred_at=rev1.created_at)
    with pytest.raises(CaseRevisionConflict) as ei:
        repo.create_revision(
            revision=rev2_b, actor_id="t", source="ci", occurred_at=rev1.created_at
        )
    assert ei.value.conflict_reason == "concurrent_sibling"


def test_expected_parent_revision_id_mismatch_raises_stale_parent() -> None:
    """Section 13.1 — stale expected_parent_revision_id MUST raise
    ``StaleParentRevision`` (NOT ``CaseRevisionConflict``)."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=2,
        parent_revision_id="rev-1",
        expected_parent_revision_id="rev-WRONG",
    )
    with pytest.raises(StaleParentRevision) as ei:
        repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at)
    assert ei.value.error_code == "stale_parent_revision"
    # Critical: it MUST NOT be CaseRevisionConflict.
    assert not isinstance(ei.value, CaseRevisionConflict)


def test_expected_parent_revision_id_match_succeeds() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=2,
        parent_revision_id="rev-1",
        expected_parent_revision_id="rev-1",  # correct head
    )
    stored, _ = repo.create_revision(
        revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at
    )
    assert stored.revision_id == "rev-2"


def test_optimistic_concurrency_token_mismatch_raises_case_revision_conflict() -> None:
    """Section 13.2 — token mismatch surfaces as
    ``CaseRevisionConflict`` with ``conflict_reason="token_mismatch"``."""
    expected_token = mint_optimistic_concurrency_token(
        revision_id="rev-1", created_at_iso="2026-01-01T00:00:00+00:00"
    )
    with pytest.raises(CaseRevisionConflict) as ei:
        assert_token_matches(
            revision_id="rev-1",
            expected_token=expected_token,
            actual_token="DIFFERENT-TOKEN",
        )
    assert ei.value.conflict_reason == "token_mismatch"
    assert ei.value.error_code == "case_revision_conflict"


def test_optimistic_concurrency_token_match_succeeds() -> None:
    token = mint_optimistic_concurrency_token(
        revision_id="rev-1", created_at_iso="2026-01-01T00:00:00+00:00"
    )
    # Should not raise.
    assert_token_matches(
        revision_id="rev-1",
        expected_token=token,
        actual_token=token,
    )


def test_idempotent_create_request_returns_existing_revision() -> None:
    """Section 13.3 — second create-request with the same
    ``(root_case_id, idempotency_key)`` returns the existing revision
    without creating a duplicate."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1, idempotency_key="KEY-A")
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev1_retry = build_revision(revision_id="rev-1", revision_number=1, idempotency_key="KEY-A")
    returned, audit = repo.create_revision(
        revision=rev1_retry, actor_id="t", source="ci", occurred_at=rev1.created_at
    )
    assert returned.revision_id == "rev-1"
    assert audit.payload.get("dedup") is True


def test_stale_parent_is_not_case_revision_conflict() -> None:
    """Section 12.5 / 13.1 / 16.2 — stale parent MUST be a
    ``StaleParentRevision``, not a ``CaseRevisionConflict``.
    Furthermore, ``conflict_reason="stale_parent"`` MUST NOT be a valid
    enum member of ``CaseRevisionConflict``."""
    from hexagent.case_revisions.errors import VALID_CONFLICT_REASONS

    assert "stale_parent" not in VALID_CONFLICT_REASONS
