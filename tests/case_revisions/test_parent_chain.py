"""Section 18.3 — Parent-chain consistency tests."""

from __future__ import annotations

import pytest

from hexagent.case_revisions import (
    InMemoryCaseRevisionRepository,
    RevisionPersistenceFailure,
    build_parent_chain_links,
)

from ._factories import build_revision


def test_parent_revision_id_resolves_to_committed_revision() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=2,
        parent_revision_id="rev-1",
    )
    stored, _ = repo.create_revision(
        revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at
    )
    assert stored.parent_revision_id == "rev-1"
    parent = repo.get_revision("rev-1")
    assert parent.root_case_id == stored.root_case_id


def test_parent_chain_reachable_via_link_rows() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(revision_id="rev-2", revision_number=2, parent_revision_id="rev-1")
    repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at)
    links = repo._parent_links["rev-2"]  # type: ignore[attr-defined]
    assert len(links) == 1
    assert links[0].parent_revision_id == "rev-1"
    assert links[0].link_order == 0


def test_first_revision_has_parent_revision_id_none() -> None:
    """Section 9.2 — first revision of a root_case_id has parent_revision_id == None."""
    rev = build_revision(revision_id="rev-1", revision_number=1)
    assert rev.parent_revision_id is None


def test_build_parent_chain_links_for_initial_revision() -> None:
    links = build_parent_chain_links(revision_id="rev-1", parent_revision=None)
    assert links == ()


def test_build_parent_chain_links_for_subsequent_revision() -> None:
    parent = build_revision(revision_id="rev-1", revision_number=1)
    links = build_parent_chain_links(revision_id="rev-2", parent_revision=parent)
    assert len(links) == 1
    assert links[0].parent_revision_id == "rev-1"
    assert links[0].link_order == 0


def test_missing_parent_raises_revision_persistence_failure() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev2 = build_revision(revision_id="rev-2", revision_number=2, parent_revision_id="GHOST")
    with pytest.raises(RevisionPersistenceFailure):
        repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=rev2.created_at)


def test_parent_root_case_mismatch_rejected() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1, root_case_id="A")
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=2,
        parent_revision_id="rev-1",
        root_case_id="B",  # mismatched root_case_id
    )
    with pytest.raises(RevisionPersistenceFailure) as ei:
        repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at)
    assert ei.value.failure_reason == "parent_root_case_mismatch"


def test_non_monotonic_revision_number_rejected() -> None:
    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=5,  # should be 2 (parent.revision_number + 1)
        parent_revision_id="rev-1",
    )
    with pytest.raises(RevisionPersistenceFailure) as ei:
        repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at)
    assert ei.value.failure_reason == "non_monotonic_revision_number"
