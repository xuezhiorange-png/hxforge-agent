"""Idempotency-key helpers for TASK-014 immutable case revisions.

Implements Section 13.3 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

A revision create-request MAY include an ``idempotency_key``. Two
create-requests with the same ``(root_case_id, idempotency_key)`` MUST
be deduplicated: the second request returns the existing revision
without creating a duplicate. The dedup is recorded in the
``idempotency_keys`` relation (Section 9.1).

A request that lands on a pre-existing idempotency record surfaces a
:class:`CaseRevisionConflict` with
``conflict_reason="duplicate_idempotency_key"`` only when the existing
record points at a DIFFERENT ``(revision_id, revision_number)`` than
the new request would have produced. The repository's create flow
itself returns the existing revision when the caller re-submits the
SAME request — that is the canonical "second request returns existing
revision" path.
"""

from __future__ import annotations

from hexagent.case_revisions.errors import CaseRevisionConflict
from hexagent.case_revisions.models import CaseRevision


def assert_idempotency_dedup_match(
    *,
    existing_revision: CaseRevision,
    requested_revision_id: str,
    root_case_id: str | None = None,
) -> None:
    """Raise :class:`CaseRevisionConflict` with
    ``conflict_reason="duplicate_idempotency_key"`` iff the requested
    ``revision_id`` does not match the revision already stored under
    this idempotency key.

    Section 13.3 — a re-submitted request with the SAME
    ``(root_case_id, idempotency_key, revision_id)`` is the dedup happy
    path and MUST NOT raise. A different ``revision_id`` under the
    same key is a misuse and surfaces as
    ``CaseRevisionConflict``.
    """
    if existing_revision.revision_id != requested_revision_id:
        raise CaseRevisionConflict(
            "idempotency_key already bound to a different revision "
            f"(existing={existing_revision.revision_id!r}, "
            f"requested={requested_revision_id!r}); Section 13.3",
            root_case_id=root_case_id or existing_revision.root_case_id,
            revision_id=requested_revision_id,
            conflict_reason="duplicate_idempotency_key",
            expected_parent_revision_id=None,
            actual_parent_revision_id=existing_revision.revision_id,
            attempted_revision_number=existing_revision.revision_number,
        )


__all__ = ["assert_idempotency_dedup_match"]
