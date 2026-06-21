"""Tests for DesignCaseRevision creation, linking, and serialisation.

Covers: initial revision, child revisions, numbering, parent linkage,
duplicate/number/wrong-case_id rejection, hash verification, and JSON
round-trip.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from hexagent.core.canonical import sha256_digest
from hexagent.domain.models import DesignCase
from hexagent.domain.revisions import (
    DesignCaseRevision,
    DuplicateIdError,
    RevisionNumberConflictError,
)
from hexagent.repositories.memory import InMemoryDesignCaseRevisionRepository

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXED_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _canonical_payload(case: DesignCase) -> dict:
    """Deep-sort a DesignCase dump for deterministic hashing."""
    raw = case.model_dump()
    return _deep_sort(raw)


def _deep_sort(obj):
    if isinstance(obj, dict):
        return {k: _deep_sort(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_sort(item) for item in obj]
    return obj


def _make_revision(
    case: DesignCase,
    revision_id: UUID,
    *,
    revision_number: int = 1,
    parent_revision_id: UUID | None = None,
    created_by: str = "test-agent",
) -> DesignCaseRevision:
    """Build a valid DesignCaseRevision."""
    cp = _canonical_payload(case)
    h = sha256_digest(cp)
    return DesignCaseRevision(
        revision_id=revision_id,
        case_id=case.id,
        revision_number=revision_number,
        design_case=case,
        canonical_payload=cp,
        content_hash=h,
        created_at=FIXED_NOW,
        created_by=created_by,
        parent_revision_id=parent_revision_id,
        change_summary="",
        changed_fields=(),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDesignCaseRevisionCreation:
    """Basic revision creation and field validation."""

    def test_create_initial_revision(self, sample_design_case) -> None:
        rev = _make_revision(sample_design_case, UUID(int=1))
        assert rev.revision_number == 1
        assert rev.parent_revision_id is None
        assert rev.case_id == sample_design_case.id
        assert rev.schema_version == "1.0"

    def test_create_child_revision(self, sample_design_case) -> None:
        parent = _make_revision(sample_design_case, UUID(int=1))
        child = _make_revision(
            sample_design_case,
            UUID(int=2),
            revision_number=2,
            parent_revision_id=parent.revision_id,
        )
        assert child.revision_number == 2
        assert child.parent_revision_id == parent.revision_id

    def test_revision_numbers_consecutive(self, sample_design_case) -> None:
        r1 = _make_revision(sample_design_case, UUID(int=1))
        r2 = _make_revision(
            sample_design_case,
            UUID(int=2),
            revision_number=2,
            parent_revision_id=r1.revision_id,
        )
        r3 = _make_revision(
            sample_design_case,
            UUID(int=3),
            revision_number=3,
            parent_revision_id=r2.revision_id,
        )
        assert r1.revision_number == 1
        assert r2.revision_number == 2
        assert r3.revision_number == 3

    def test_parent_correct(self, sample_design_case) -> None:
        parent = _make_revision(sample_design_case, UUID(int=1))
        child = _make_revision(
            sample_design_case,
            UUID(int=2),
            revision_number=2,
            parent_revision_id=parent.revision_id,
        )
        assert child.parent_revision_id == parent.revision_id

    def test_parent_unmodified(self, sample_design_case) -> None:
        parent = _make_revision(sample_design_case, UUID(int=1))
        _make_revision(
            sample_design_case,
            UUID(int=2),
            revision_number=2,
            parent_revision_id=parent.revision_id,
        )
        # parent is a frozen dataclass — no mutation possible
        assert parent.revision_number == 1
        assert parent.parent_revision_id is None

    def test_revision_number_must_be_positive(self, sample_design_case) -> None:
        with pytest.raises(ValueError, match="revision_number must be >= 1"):
            _make_revision(sample_design_case, UUID(int=1), revision_number=0)

    def test_revision_number_1_must_have_no_parent(self, sample_design_case) -> None:
        with pytest.raises(ValueError, match="must have parent_revision_id=None"):
            DesignCaseRevision(
                revision_id=UUID(int=1),
                case_id=sample_design_case.id,
                revision_number=1,
                design_case=sample_design_case,
                canonical_payload=_canonical_payload(sample_design_case),
                content_hash=sha256_digest(_canonical_payload(sample_design_case)),
                created_at=FIXED_NOW,
                created_by="test",
                parent_revision_id=UUID(int=99),
            )

    def test_revision_number_gt1_must_have_parent(self, sample_design_case) -> None:
        with pytest.raises(ValueError, match="must have a parent_revision_id"):
            DesignCaseRevision(
                revision_id=UUID(int=2),
                case_id=sample_design_case.id,
                revision_number=2,
                design_case=sample_design_case,
                canonical_payload=_canonical_payload(sample_design_case),
                content_hash=sha256_digest(_canonical_payload(sample_design_case)),
                created_at=FIXED_NOW,
                created_by="test",
                parent_revision_id=None,
            )

    def test_created_at_must_be_timezone_aware(self, sample_design_case) -> None:
        with pytest.raises(ValueError, match="timezone-aware"):
            DesignCaseRevision(
                revision_id=UUID(int=1),
                case_id=sample_design_case.id,
                revision_number=1,
                design_case=sample_design_case,
                canonical_payload=_canonical_payload(sample_design_case),
                content_hash=sha256_digest(_canonical_payload(sample_design_case)),
                created_at=datetime(2026, 1, 1),  # naive!
                created_by="test",
            )

    def test_created_by_must_not_be_empty(self, sample_design_case) -> None:
        with pytest.raises(ValueError, match="created_by must not be empty"):
            DesignCaseRevision(
                revision_id=UUID(int=1),
                case_id=sample_design_case.id,
                revision_number=1,
                design_case=sample_design_case,
                canonical_payload=_canonical_payload(sample_design_case),
                content_hash=sha256_digest(_canonical_payload(sample_design_case)),
                created_at=FIXED_NOW,
                created_by="",
            )


class TestDesignCaseRevisionRepository:
    """Repository constraint checks: duplicates, numbering, missing parent."""

    def test_duplicate_id_rejected(self, sample_design_case) -> None:
        repo = InMemoryDesignCaseRevisionRepository()
        r1 = _make_revision(sample_design_case, UUID(int=1))
        repo.add(r1)
        r1_dup = _make_revision(sample_design_case, UUID(int=1))
        with pytest.raises(DuplicateIdError):
            repo.add(r1_dup)

    def test_duplicate_number_rejected(self, sample_design_case) -> None:
        repo = InMemoryDesignCaseRevisionRepository()
        r1 = _make_revision(sample_design_case, UUID(int=1))
        r1_dup = _make_revision(sample_design_case, UUID(int=99), revision_number=1)
        repo.add(r1)
        with pytest.raises(RevisionNumberConflictError):
            repo.add(r1_dup)

    def test_wrong_case_id_different_cases(self, sample_design_case, sample_design_case_v2) -> None:
        """Two cases can independently have revision_number=1."""
        repo = InMemoryDesignCaseRevisionRepository()
        r1_a = _make_revision(sample_design_case, UUID(int=1))
        r1_b = _make_revision(sample_design_case_v2, UUID(int=2))
        repo.add(r1_a)
        repo.add(r1_b)  # should succeed — different case_id

    def test_missing_parent_rejected(self, sample_design_case) -> None:
        repo = InMemoryDesignCaseRevisionRepository()
        child = _make_revision(
            sample_design_case,
            UUID(int=2),
            revision_number=2,
            parent_revision_id=UUID(int=999),
        )
        from hexagent.domain.revisions import MissingParentError

        with pytest.raises(MissingParentError):
            repo.add(child)


class TestHashIntegrity:
    """Content-hash verification."""

    def test_hash_matches_payload(self, sample_design_case) -> None:
        rev = _make_revision(sample_design_case, UUID(int=1))
        assert rev.content_hash == sha256_digest(rev.canonical_payload)

    def test_hash_mismatch_detected(self, sample_design_case) -> None:
        cp = _canonical_payload(sample_design_case)
        sha256_digest(cp)
        with pytest.raises(ValueError, match="content_hash mismatch"):
            DesignCaseRevision(
                revision_id=UUID(int=1),
                case_id=sample_design_case.id,
                revision_number=1,
                design_case=sample_design_case,
                canonical_payload=cp,
                content_hash="sha256:" + "f" * 64,  # wrong hash
                created_at=FIXED_NOW,
                created_by="test",
            )


class TestRevisionJsonRoundTrip:
    """Serialisation to JSON and back preserves all fields."""

    def test_round_trip(self, sample_design_case) -> None:
        rev = _make_revision(sample_design_case, UUID(int=1))
        json_str = rev.to_json()
        restored = DesignCaseRevision.from_json(json_str)
        assert restored.revision_id == rev.revision_id
        assert restored.case_id == rev.case_id
        assert restored.revision_number == rev.revision_number
        assert restored.content_hash == rev.content_hash
        assert restored.created_by == rev.created_by
        assert restored.parent_revision_id == rev.parent_revision_id
        assert restored.changed_fields == rev.changed_fields

    def test_round_trip_with_parent(self, sample_design_case) -> None:
        parent = _make_revision(sample_design_case, UUID(int=1))
        cp = _canonical_payload(sample_design_case)
        h = sha256_digest(cp)
        child = DesignCaseRevision(
            revision_id=UUID(int=2),
            case_id=sample_design_case.id,
            revision_number=2,
            design_case=sample_design_case,
            canonical_payload=cp,
            content_hash=h,
            created_at=FIXED_NOW,
            created_by="test-agent",
            parent_revision_id=parent.revision_id,
            change_summary="Updated fouling",
            changed_fields=("cold_stream",),
        )
        json_str = child.to_json()
        restored = DesignCaseRevision.from_json(json_str)
        assert restored.parent_revision_id == parent.revision_id
        assert restored.change_summary == "Updated fouling"
        assert restored.changed_fields == ("cold_stream",)

    def test_dict_round_trip(self, sample_design_case) -> None:
        rev = _make_revision(sample_design_case, UUID(int=1))
        d = rev.to_dict()
        restored = DesignCaseRevision.from_dict(d)
        assert restored.revision_id == rev.revision_id
        assert restored.design_case.id == rev.design_case.id
