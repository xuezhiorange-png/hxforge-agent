"""Persistence adapter round-trip + migration-aware tests."""

from __future__ import annotations

import pytest

from hexagent.case_revisions import (
    AuditEventType,
    InMemoryCaseRevisionRepository,
    RevisionStatus,
)

from ._factories import build_revision


def test_round_trip_initial_revision() -> None:
    """Round-trip: create → get → fields preserved."""
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    stored, audit = repo.create_revision(
        revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at
    )
    fetched = repo.get_revision("rev-1")
    assert fetched.revision_id == rev.revision_id
    assert fetched.payload_hash == rev.payload_hash
    assert fetched.domain_snapshot_hash == rev.domain_snapshot_hash
    assert audit.event_type == AuditEventType.REVISION_COMMITTED
    assert audit.actor_id == "t"
    assert audit.source == "ci"


def test_round_trip_three_revisions() -> None:
    repo = InMemoryCaseRevisionRepository()
    base = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=base, actor_id="t", source="ci", occurred_at=base.created_at)
    rev2 = build_revision(revision_id="rev-2", revision_number=2, parent_revision_id="rev-1")
    repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=base.created_at)
    rev3 = build_revision(revision_id="rev-3", revision_number=3, parent_revision_id="rev-2")
    repo.create_revision(revision=rev3, actor_id="t", source="ci", occurred_at=base.created_at)
    chain = repo.list_revisions("case-1")
    assert [r.revision_number for r in chain] == [1, 2, 3]
    head = repo.head_revision("case-1")
    assert head is not None
    assert head.revision_id == "rev-3"


def test_deep_copy_prevents_external_mutation() -> None:
    """The repository MUST deep-copy on insert + retrieve so callers
    cannot mutate stored state through retrieved objects."""
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    fetched = repo.get_revision("rev-1")
    fetched.payload["duty_w"] = 99999.0  # type: ignore[index]
    fetched.identity["case_id"] = "MUTATED"  # type: ignore[index]
    re_fetched = repo.get_revision("rev-1")
    assert re_fetched.payload["duty_w"] == 1000.0
    assert re_fetched.identity["case_id"] == "case-1"


def test_head_revision_returns_none_for_unknown_root() -> None:
    repo = InMemoryCaseRevisionRepository()
    assert repo.head_revision("UNKNOWN") is None


def test_list_audit_events_for_revision() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(
        revision_id="rev-1",
        revision_number=1,
        status=RevisionStatus.COMMITTED,
    )
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    repo.transition_revision(
        revision=stored,
        new_status=RevisionStatus.ARCHIVED,
        actor_id="t",
        source="ci",
        occurred_at=rev.created_at,
    )
    events = repo.list_audit_events("rev-1")
    assert len(events) == 2
    types = [e.event_type for e in events]
    assert AuditEventType.REVISION_COMMITTED in types
    assert AuditEventType.REVISION_ARCHIVED in types


def test_audit_event_ids_are_unique_within_repo() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    repo.transition_revision(
        revision=stored,
        new_status=RevisionStatus.ARCHIVED,
        actor_id="t",
        source="ci",
        occurred_at=rev.created_at,
    )
    events = repo.list_audit_events("rev-1")
    ids = [e.event_id for e in events]
    assert len(ids) == len(set(ids))  # all unique


def test_audit_event_immutability_via_repository() -> None:
    """Section 14.2 — repository MUST reject duplicate audit event ids."""
    from datetime import UTC, datetime

    from hexagent.case_revisions import (
        CaseRevisionAuditEvent,
        RevisionPersistenceFailure,
    )

    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    new_rev, audit = repo.transition_revision(
        revision=stored,
        new_status=RevisionStatus.ARCHIVED,
        actor_id="t",
        source="ci",
        occurred_at=rev.created_at,
    )
    # Manually re-insert the same audit event id should fail.
    with pytest.raises(RevisionPersistenceFailure):
        repo._atomic_audit_insert(  # type: ignore[attr-defined]
            CaseRevisionAuditEvent(
                event_id=audit.event_id,  # same id!
                revision_id=audit.revision_id,
                root_case_id=audit.root_case_id,
                event_type=audit.event_type,
                actor_id=audit.actor_id,
                source=audit.source,
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )
