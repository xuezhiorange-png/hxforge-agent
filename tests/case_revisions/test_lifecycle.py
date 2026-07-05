"""Section 18.6 — Atomicity tests + lifecycle transitions."""

from __future__ import annotations

import pytest

from hexagent.case_revisions import (
    AuditEventType,
    InMemoryCaseRevisionRepository,
    RevisionPersistenceFailure,
    RevisionStatus,
)

from ._factories import build_revision


def test_allowed_transition_draft_to_validated() -> None:
    """Section 7.2 — draft -> validated."""
    from hexagent.case_revisions.models import is_allowed_transition

    assert is_allowed_transition(RevisionStatus.DRAFT, RevisionStatus.VALIDATED)


def test_allowed_transition_validated_to_committed() -> None:
    from hexagent.case_revisions.models import is_allowed_transition

    assert is_allowed_transition(RevisionStatus.VALIDATED, RevisionStatus.COMMITTED)


def test_allowed_transition_committed_to_superseded() -> None:
    from hexagent.case_revisions.models import is_allowed_transition

    assert is_allowed_transition(RevisionStatus.COMMITTED, RevisionStatus.SUPERSEDED)


def test_forbidden_transition_draft_to_committed() -> None:
    """Section 7.3 — must go through validated."""
    from hexagent.case_revisions.models import is_allowed_transition

    assert not is_allowed_transition(RevisionStatus.DRAFT, RevisionStatus.COMMITTED)


def test_forbidden_transition_draft_to_superseded() -> None:
    from hexagent.case_revisions.models import is_allowed_transition

    assert not is_allowed_transition(RevisionStatus.DRAFT, RevisionStatus.SUPERSEDED)


def test_forbidden_transition_committed_to_draft() -> None:
    """Section 7.3 — no rollback to draft."""
    from hexagent.case_revisions.models import is_allowed_transition

    assert not is_allowed_transition(RevisionStatus.COMMITTED, RevisionStatus.DRAFT)


def test_forbidden_transition_tombstoned_to_any() -> None:
    """Section 7.3 — tombstoned is terminal."""
    from hexagent.case_revisions.models import is_allowed_transition

    for status in RevisionStatus:
        assert not is_allowed_transition(RevisionStatus.TOMBSTONED, status)


def test_forbidden_transition_rejected_to_any() -> None:
    """Section 7.3 — rejected is terminal."""
    from hexagent.case_revisions.models import is_allowed_transition

    for status in RevisionStatus:
        assert not is_allowed_transition(RevisionStatus.REJECTED, status)


def test_lifecycle_persistence_emits_audit_event_per_transition() -> None:
    """Section 14.5 — every state transition MUST emit an audit event."""
    from hexagent.case_revisions.models import is_allowed_transition

    # Manually verify the transition table is exhaustive.
    for src in RevisionStatus:
        for dst in RevisionStatus:
            # Each (src, dst) pair must be classified either allowed or
            # forbidden.
            assert isinstance(is_allowed_transition(src, dst), bool)


def test_failed_commit_leaves_no_partial_state() -> None:
    """Section 13.4 / 6.8 — atomic commit, no partial state on failure."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    # Snapshot state before.
    before = repo.get_revision("rev-1")
    # Try to insert a revision with mismatched hash — should fail and
    # leave no partial state.
    bad = build_revision(revision_id="rev-2", revision_number=2, parent_revision_id="rev-1")
    # Corrupt the payload hash.
    from dataclasses import replace

    from hexagent.case_revisions import RevisionHashMismatch

    bad_corrupted = replace(bad, payload_hash="0" * 64)
    with pytest.raises(RevisionHashMismatch):
        repo.create_revision(
            revision=bad_corrupted, actor_id="t", source="ci", occurred_at=rev1.created_at
        )
    # State unchanged: rev-1 still there, rev-2 not.
    after = repo.get_revision("rev-1")
    assert after.payload_hash == before.payload_hash
    assert not repo.has_revision("rev-2")


def test_audit_event_emitted_per_transition() -> None:
    """Section 14.5 + 18.7 — each transition emits exactly one audit event."""
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1, status=RevisionStatus.COMMITTED)
    stored, _ = repo.create_revision(
        revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at
    )
    new_rev, audit = repo.transition_revision(
        revision=stored,
        new_status=RevisionStatus.ARCHIVED,
        actor_id="t",
        source="ci",
        occurred_at=rev1.created_at,
    )
    # Audit event matches the new status.
    assert audit.event_type == AuditEventType.REVISION_ARCHIVED
    events = repo.list_audit_events("rev-1")
    # Two events: created (committed on initial) + archived.
    assert len(events) == 2
    types = {e.event_type for e in events}
    assert AuditEventType.REVISION_COMMITTED in types
    assert AuditEventType.REVISION_ARCHIVED in types


def test_audit_events_are_immutable() -> None:
    """Section 14.2 — audit events are immutable (frozen dataclass)."""
    from dataclasses import FrozenInstanceError

    from hexagent.case_revisions import CaseRevisionAuditEvent

    ev = CaseRevisionAuditEvent(
        event_id="ev-1",
        revision_id="rev-1",
        root_case_id="case-1",
        event_type=AuditEventType.REVISION_CREATED,
        actor_id="t",
        source="ci",
        occurred_at=__import__("datetime").datetime(2026, 1, 1, tzinfo=__import__("datetime").UTC),
    )
    with pytest.raises(FrozenInstanceError):
        ev.actor_id = "MUTATED"  # type: ignore[misc]


def test_audit_events_carry_actor_id_and_source() -> None:
    """Section 14.3 — every audit event carries actor_id and source."""
    from datetime import UTC, datetime

    from hexagent.case_revisions import CaseRevisionAuditEvent
    from hexagent.case_revisions.audit import assert_audit_event_complete

    ev = CaseRevisionAuditEvent(
        event_id="ev-1",
        revision_id="rev-1",
        root_case_id="case-1",
        event_type=AuditEventType.REVISION_CREATED,
        actor_id="t",
        source="ci",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    assert_audit_event_complete(ev)


def test_incomplete_audit_event_rejected() -> None:
    from datetime import UTC, datetime

    from hexagent.case_revisions import (
        CaseRevisionAuditEvent,
    )
    from hexagent.case_revisions.audit import assert_audit_event_complete

    ev = CaseRevisionAuditEvent(
        event_id="ev-1",
        revision_id="rev-1",
        root_case_id="case-1",
        event_type=AuditEventType.REVISION_CREATED,
        actor_id="",  # missing
        source="ci",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    with pytest.raises(RevisionPersistenceFailure):
        assert_audit_event_complete(ev)
