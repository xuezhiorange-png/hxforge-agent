"""Application service for managing design-case revisions.

This service encapsulates the business logic for creating, linking, and
verifying immutable :class:`DesignCaseRevision` instances.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from hexagent.core.canonical import sha256_digest
from hexagent.core.time import Clock, IdGenerator
from hexagent.domain.models import DesignCase
from hexagent.domain.revisions import (
    DesignCaseRevision,
    IntegrityError,
)
from hexagent.repositories.base import DesignCaseRevisionRepository


class RevisionService:
    """Stateless service for design-case revision management."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_initial_revision(
        self,
        case: DesignCase,
        created_by: str,
        clock: Clock,
        id_gen: IdGenerator,
    ) -> DesignCaseRevision:
        """Create the very first revision for a design case.

        Parameters
        ----------
        case:
            The design case to snapshot.
        created_by:
            Identifier of the creating agent or user.
        clock:
            Provides the creation timestamp via ``utcnow()``.
        id_gen:
            Provides the revision id via ``new_id()``.

        Returns
        -------
        DesignCaseRevision
            A new, fully-hashed revision with ``revision_number == 1``
            and ``parent_revision_id is None``.
        """
        canonical_payload = _canonical_payload(case)
        h = sha256_digest(canonical_payload)
        return DesignCaseRevision(
            revision_id=id_gen.new_id(),
            case_id=case.id,
            revision_number=1,
            design_case=case,
            canonical_payload=canonical_payload,
            content_hash=h,
            created_at=clock.utcnow(),
            created_by=created_by,
            parent_revision_id=None,
            change_summary="Initial revision",
            changed_fields=(),
        )

    def create_revision_from_parent(
        self,
        parent: DesignCaseRevision,
        new_case: DesignCase,
        change_summary: str,
        changed_fields: tuple[str, ...],
        clock: Clock,
        id_gen: IdGenerator,
    ) -> DesignCaseRevision:
        """Create a child revision that evolves a design case.

        The parent is **never** modified (frozen dataclass guarantee).

        Parameters
        ----------
        parent:
            The existing revision to derive from.
        new_case:
            Updated design case.
        change_summary:
            Human-readable description of what changed.
        changed_fields:
            Field names that differ from the parent payload.
        clock:
            Provides the creation timestamp via ``utcnow()``.
        id_gen:
            Provides the revision id via ``new_id()``.

        Returns
        -------
        DesignCaseRevision
            A new revision with incremented ``revision_number``.

        Raises
        ------
        ValueError
            If ``new_case.id`` does not match the parent's ``case_id``.
        """
        # 1. Verify case_id match
        if new_case.id != parent.case_id:
            raise ValueError(
                f"New case id {new_case.id} does not match "
                f"parent case id {parent.case_id}"
            )

        # 2. Create canonical payload and compute hash
        canonical_payload = _canonical_payload(new_case)
        h = sha256_digest(canonical_payload)

        # 3. Compute changed_fields from parent payload if not provided
        if not changed_fields:
            changed_fields = _compute_changed_fields(
                parent.canonical_payload, canonical_payload,
            )

        # 4. Increment revision_number
        new_revision_number = parent.revision_number + 1

        return DesignCaseRevision(
            revision_id=id_gen.new_id(),
            case_id=parent.case_id,
            revision_number=new_revision_number,
            design_case=new_case,
            canonical_payload=canonical_payload,
            content_hash=h,
            created_at=clock.utcnow(),
            created_by=parent.created_by,
            parent_revision_id=parent.revision_id,
            change_summary=change_summary,
            changed_fields=changed_fields,
        )

    def get_revision_history(
        self,
        case_id: UUID,
        repo: DesignCaseRevisionRepository,
    ) -> tuple[DesignCaseRevision, ...]:
        """Return the full ordered revision history for *case_id*.

        Returns
        -------
        tuple[DesignCaseRevision, …]
            Ordered from ``revision_number == 1`` upward.
        """
        return repo.list_by_case(case_id)

    def verify_revision_integrity(
        self,
        revision: DesignCaseRevision,
        repo: DesignCaseRevisionRepository,
    ) -> bool:
        """Verify that *revision* has not been tampered with.

        Checks
        ------
        1. Recomputes the content hash from ``revision.canonical_payload``
           and compares it to ``revision.content_hash``.
        2. If ``parent_revision_id`` is set, verifies the parent exists
           in the repository.
        3. If ``parent_revision_id`` is ``None``, the revision must have
           ``revision_number == 1``.

        Raises
        ------
        IntegrityError
            If any check fails.

        Returns
        -------
        bool
            ``True`` if all checks pass.
        """
        # 1. Hash verification
        recomputed = sha256_digest(revision.canonical_payload)
        if recomputed != revision.content_hash:
            raise IntegrityError(
                f"Content hash mismatch for revision {revision.revision_id}: "
                f"expected {recomputed}, got {revision.content_hash}"
            )

        # 2. Parent existence check
        if revision.parent_revision_id is not None:
            try:
                parent = repo.get(revision.parent_revision_id)
            except KeyError as err:
                raise IntegrityError(
                    f"Parent revision {revision.parent_revision_id} not found "
                    f"for revision {revision.revision_id}"
                ) from err
            # Verify the parent belongs to the same case
            if parent.case_id != revision.case_id:
                raise IntegrityError(
                    f"Parent revision {revision.parent_revision_id} belongs to "
                    f"case {parent.case_id}, expected {revision.case_id}"
                )
        else:
            if revision.revision_number != 1:
                raise IntegrityError(
                    f"Revision {revision.revision_id} has no parent but "
                    f"revision_number is {revision.revision_number} (expected 1)"
                )

        return True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_payload(case: DesignCase) -> dict[str, Any]:
    """Build a deterministic dict from a DesignCase.

    Serialises the case to a dict using ``model_dump()``, then applies
    recursive key-sorting so that the output is insertion-order
    independent.
    """
    raw = case.model_dump()
    result: dict[str, Any] = _deep_sort(raw)
    return result


def _deep_sort(obj: Any) -> Any:
    """Recursively sort dicts so that canonical JSON is deterministic."""
    if isinstance(obj, dict):
        return {k: _deep_sort(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_sort(item) for item in obj]
    return obj


def _compute_changed_fields(
    old: dict[str, Any],
    new: dict[str, Any],
) -> tuple[str, ...]:
    """Return a sorted tuple of field names that differ between two dicts."""
    old_keys = set(old.keys())
    new_keys = set(new.keys())
    all_keys = old_keys | new_keys
    changed = [
        k for k in sorted(all_keys)
        if old.get(k) != new.get(k)
    ]
    return tuple(changed)


__all__ = ["RevisionService"]
