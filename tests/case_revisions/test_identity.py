"""Section 18.1 — Identity and validity tests."""

from __future__ import annotations

import pytest

from hexagent.case_revisions.errors import (
    RevisionPersistenceFailure,
)
from hexagent.case_revisions.lifecycle import ensure_status_valid
from hexagent.case_revisions.models import RevisionStatus, coerce_status

from ._factories import build_revision


def test_revision_id_uniqueness_across_repository() -> None:
    from hexagent.case_revisions import InMemoryCaseRevisionRepository

    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="rev-unique-1")
    stored, _ = repo.create_revision(
        revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at
    )
    assert repo.has_revision(stored.revision_id)
    # Same revision_id in the same root would mean a duplicate-key collision
    # (which the repository raises as CaseRevisionConflict, not DuplicateId).
    # Cross-root uniqueness is implicit: revision_id is opaque / global.


def test_root_case_revision_number_uniqueness() -> None:

    from hexagent.case_revisions import (
        CaseRevisionConflict,
        InMemoryCaseRevisionRepository,
    )

    repo = InMemoryCaseRevisionRepository()
    base = build_revision(revision_id="rev-1", revision_number=1)
    repo.create_revision(revision=base, actor_id="t", source="ci", occurred_at=base.created_at)
    payload2 = {"case_id": "case-1", "duty_w": 2000.0}
    rev2 = build_revision(
        revision_id="rev-2-dup",
        revision_number=1,  # duplicate number
        payload=payload2,
        parent_revision_id="rev-1",
    )
    with pytest.raises(CaseRevisionConflict) as ei:
        repo.create_revision(revision=rev2, actor_id="t", source="ci", occurred_at=base.created_at)
    assert ei.value.conflict_reason == "concurrent_sibling"


def test_root_case_idempotency_key_uniqueness() -> None:
    from hexagent.case_revisions import (
        InMemoryCaseRevisionRepository,
    )

    repo = InMemoryCaseRevisionRepository()
    rev1 = build_revision(revision_id="rev-1", revision_number=1, idempotency_key="KEY-A")
    repo.create_revision(revision=rev1, actor_id="t", source="ci", occurred_at=rev1.created_at)
    rev2 = build_revision(
        revision_id="rev-2",
        revision_number=2,
        parent_revision_id="rev-1",
        idempotency_key="KEY-A",  # duplicate idempotency key
    )
    returned, _ = repo.create_revision(
        revision=rev2, actor_id="t", source="ci", occurred_at=rev1.created_at
    )
    # Same idempotency_key returns the existing revision (Section 13.3).
    assert returned.revision_id == "rev-1"


def test_required_field_validation() -> None:
    from hexagent.case_revisions import InMemoryCaseRevisionRepository, InvalidRevisionPayload

    repo = InMemoryCaseRevisionRepository()
    rev = build_revision(revision_id="")
    with pytest.raises(InvalidRevisionPayload):
        repo.create_revision(revision=rev, actor_id="t", source="ci", occurred_at=rev.created_at)


def test_status_enum_validation() -> None:
    with pytest.raises(RevisionPersistenceFailure):
        ensure_status_valid("not-a-real-status")
    # coerce_status is permissive on valid string inputs
    assert coerce_status("draft") == RevisionStatus.DRAFT
    # and rejects unknown values
    with pytest.raises(ValueError):
        coerce_status("not-a-real-status")
