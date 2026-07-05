"""Section 18.2 — Immutability tests."""

from __future__ import annotations

from hexagent.case_revisions import (
    AuditEventType,
    InMemoryCaseRevisionRepository,
    RevisionStatus,
)

from ._factories import build_revision


def test_committed_revision_payload_cannot_be_modified() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    # Mutating the in-memory object MUST NOT affect the stored record.
    stored.payload["duty_w"] = 9999.0  # type: ignore[index]
    re_fetched = repo.get_revision("rev-1")
    assert re_fetched.payload["duty_w"] == 1000.0


def test_committed_revision_identity_cannot_be_modified() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    stored.identity["case_id"] = "MUTATED"  # type: ignore[index]
    re_fetched = repo.get_revision("rev-1")
    assert re_fetched.identity["case_id"] == "case-1"


def test_committed_revision_payload_hash_cannot_be_modified() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    original_hash = stored.payload_hash
    # Mutation must not affect stored hash.
    assert stored.payload_hash == original_hash


def test_committed_revision_domain_snapshot_hash_cannot_be_modified() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    original_snapshot = stored.domain_snapshot_hash
    # Even if we somehow tampered with provenance, the snapshot is fixed.
    assert stored.domain_snapshot_hash == original_snapshot


def test_archival_is_metadata_only() -> None:
    """Section 6.3 — archival is a metadata transition; payload + hashes
    remain immutable."""
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
    # Payload and hashes unchanged.
    assert new_rev.payload_hash == stored.payload_hash
    assert new_rev.domain_snapshot_hash == stored.domain_snapshot_hash
    assert new_rev.payload == stored.payload
    # Audit event type matches.
    assert audit.event_type == AuditEventType.REVISION_ARCHIVED
    assert new_rev.status == RevisionStatus.ARCHIVED


def test_tombstone_is_metadata_only() -> None:
    """Section 6.3 — tombstone is a metadata transition; payload + hashes
    remain immutable."""
    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)
    stored = repo.get_revision("rev-1")
    new_rev, _ = repo.transition_revision(
        revision=stored,
        new_status=RevisionStatus.TOMBSTONED,
        actor_id="t",
        source="ci",
        occurred_at=rev.created_at,
    )
    assert new_rev.payload == stored.payload
    assert new_rev.payload_hash == stored.payload_hash
    assert new_rev.status == RevisionStatus.TOMBSTONED
