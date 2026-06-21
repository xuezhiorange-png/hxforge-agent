"""Application service for managing design-case revisions.

This service encapsulates the business logic for creating, linking, and
verifying immutable :class:`DesignCaseRevision` instances.

Key invariants enforced:
- ``created_by`` is always supplied by the caller (never copied from parent).
- ``changed_fields`` is computed internally from recursive payload diff.
- Same-case parentage is verified in the repository ``add()``.
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
    RevisionDiff,
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
        created_by: str,
        change_summary: str,
        clock: Clock,
        id_gen: IdGenerator,
    ) -> DesignCaseRevision:
        """Create a child revision that evolves a design case.

        The parent is **never** modified (frozen dataclass guarantee).

        ``changed_fields`` is computed automatically from a recursive
        diff of the parent and child canonical payloads — the caller
        must not supply it.

        Parameters
        ----------
        parent:
            The existing revision to derive from.
        new_case:
            Updated design case.
        created_by:
            Identifier of the creating agent or user (**required**).
        change_summary:
            Human-readable description of what changed.
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
            If ``new_case.id`` does not match the parent's ``case_id``,
            or if the new case is identical to the parent.
        """
        # 1. Verify case_id match
        if new_case.id != parent.case_id:
            raise ValueError(
                f"New case id {new_case.id} does not match "
                f"parent case id {parent.case_id}"
            )

        # 2. Verify created_by is not empty
        if not created_by:
            raise ValueError("created_by must not be empty")

        # 3. Create canonical payload and compute hash
        canonical_payload = _canonical_payload(new_case)
        h = sha256_digest(canonical_payload)

        # 4. Reject no-op revisions (identical content)
        if h == parent.content_hash:
            raise ValueError(
                "New revision is identical to parent — "
                "no-op revisions are not allowed"
            )

        # 5. Compute changed_fields recursively (never trust caller)
        changed_fields = _compute_recursive_changed_fields(
            parent.canonical_payload, canonical_payload,
        )

        # 6. Increment revision_number
        new_revision_number = parent.revision_number + 1

        return DesignCaseRevision(
            revision_id=id_gen.new_id(),
            case_id=parent.case_id,
            revision_number=new_revision_number,
            design_case=new_case,
            canonical_payload=canonical_payload,
            content_hash=h,
            created_at=clock.utcnow(),
            created_by=created_by,
            parent_revision_id=parent.revision_id,
            change_summary=change_summary,
            changed_fields=changed_fields,
        )

    def compute_revision_diff(
        self,
        old_revision: DesignCaseRevision,
        new_revision: DesignCaseRevision,
    ) -> RevisionDiff:
        """Compute a field-level diff between two revisions.

        Returns a :class:`RevisionDiff` with stable nested paths,
        canonical before/after values, sorted deterministically.
        """
        if old_revision.case_id != new_revision.case_id:
            raise ValueError(
                "Cannot diff revisions from different cases: "
                f"{old_revision.case_id} vs {new_revision.case_id}"
            )

        field_changes = _compute_field_level_diff(
            old_revision.canonical_payload,
            new_revision.canonical_payload,
        )

        return RevisionDiff(
            from_revision_id=old_revision.revision_id,
            to_revision_id=new_revision.revision_id,
            field_changes=field_changes,
            content_hash_before=old_revision.content_hash,
            content_hash_after=new_revision.content_hash,
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
           in the repository and belongs to the same case.
        3. Verifies consecutive revision numbering in the full chain.

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

        # 2. Parent existence and same-case check
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
            # Verify consecutive numbering
            if parent.revision_number != revision.revision_number - 1:
                raise IntegrityError(
                    f"Revision {revision.revision_id} has revision_number "
                    f"{revision.revision_number} but parent has "
                    f"{parent.revision_number} (expected {revision.revision_number - 1})"
                )
        else:
            if revision.revision_number != 1:
                raise IntegrityError(
                    f"Revision {revision.revision_id} has no parent but "
                    f"revision_number is {revision.revision_number} (expected 1)"
                )

        # 3. Full chain verification
        self._verify_full_chain(revision, repo)

        return True

    def _verify_full_chain(
        self,
        revision: DesignCaseRevision,
        repo: DesignCaseRevisionRepository,
    ) -> None:
        """Walk the full parent chain and verify each link."""
        current = revision
        expected_number = revision.revision_number

        while current.parent_revision_id is not None:
            try:
                parent = repo.get(current.parent_revision_id)
            except KeyError as err:
                raise IntegrityError(
                    f"Broken chain: parent {current.parent_revision_id} "
                    f"not found for revision {current.revision_id}"
                ) from err

            if parent.case_id != current.case_id:
                raise IntegrityError(
                    f"Chain case mismatch at revision {current.revision_id}"
                )

            if parent.revision_number != expected_number - 1:
                raise IntegrityError(
                    f"Chain numbering break at revision {current.revision_id}: "
                    f"expected {expected_number - 1}, got {parent.revision_number}"
                )

            expected_number -= 1
            current = parent

        if expected_number != 1:
            raise IntegrityError(
                f"Chain does not start at revision 1 (reached {expected_number})"
            )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _canonical_payload(case: DesignCase) -> dict[str, Any]:
    """Build a deterministic dict from a DesignCase."""
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


def _compute_recursive_changed_fields(
    old: dict[str, Any],
    new: dict[str, Any],
    prefix: str = "",
) -> tuple[str, ...]:
    """Compute sorted tuple of dotted paths that differ between two dicts.

    Recursively compares nested dicts and lists.  For lists, if the
    lengths differ or elements differ, the entire list path is reported.
    """
    all_keys = sorted(set(old.keys()) | set(new.keys()))
    changed: list[str] = []

    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key)
        new_val = new.get(key)

        if key not in old or key not in new:
            changed.append(path)
        elif isinstance(old_val, dict) and isinstance(new_val, dict):
            changed.extend(
                _compute_recursive_changed_fields(old_val, new_val, path)
            )
        elif old_val != new_val:
            changed.append(path)

    return tuple(changed)


def _compute_field_level_diff(
    old: dict[str, Any],
    new: dict[str, Any],
    prefix: str = "",
) -> tuple[dict[str, Any], ...]:
    """Compute recursive diff with paths, before/after values.

    Returns a sorted tuple of change records, each containing:
    - ``path``: dotted path like ``hot_stream.inlet_temperature``
    - ``before``: canonical value from old dict (or MISSING)
    - ``after``: canonical value from new dict (or MISSING)
    """
    MISSING = "__MISSING__"
    all_keys = sorted(set(old.keys()) | set(new.keys()))
    changes: list[dict[str, Any]] = []

    for key in all_keys:
        path = f"{prefix}.{key}" if prefix else key
        old_val = old.get(key, MISSING)
        new_val = new.get(key, MISSING)

        if key not in old:
            changes.append({"path": path, "before": MISSING, "after": new_val})
        elif key not in new:
            changes.append({"path": path, "before": old_val, "after": MISSING})
        elif isinstance(old_val, dict) and isinstance(new_val, dict):
            changes.extend(
                _compute_field_level_diff(old_val, new_val, path)
            )
        elif old_val != new_val:
            changes.append({"path": path, "before": old_val, "after": new_val})

    return tuple(sorted(changes, key=lambda c: c["path"]))


__all__ = ["RevisionService"]
