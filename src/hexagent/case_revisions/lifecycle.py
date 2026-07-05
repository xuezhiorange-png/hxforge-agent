"""Revision lifecycle state machine for TASK-014 immutable case revisions.

Implements Section 7 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 7.1 — closed set of statuses:

    draft, validated, committed, superseded, archived, tombstoned, rejected

Section 7.2 — allowed transitions table.
Section 7.3 — forbidden transitions: each forbidden transition request is
a ``RevisionPersistenceFailure`` blocker.

Section 6.2 — every transition MUST emit an audit event (no silent
mutation). The lifecycle helpers here therefore return BOTH the new
revision and the corresponding audit event (see :mod:`audit`).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hexagent.case_revisions.errors import (
    RevisionPersistenceFailure,
)
from hexagent.case_revisions.models import (
    AuditEventType,
    CaseRevision,
    CaseRevisionAuditEvent,
    RevisionStatus,
    coerce_status,
    is_allowed_transition,
    transition_revision,
)

# --- Status-set validation --------------------------------------------------


VALID_REVISION_STATUSES: frozenset[str] = frozenset(s.value for s in RevisionStatus)


def ensure_status_valid(value: str | RevisionStatus) -> RevisionStatus:
    """Section 12.1 — invalid status enum value is a blocker.

    Returns the coerced ``RevisionStatus`` enum, or raises
    ``RevisionPersistenceFailure`` on an unknown value.
    """
    if isinstance(value, RevisionStatus):
        return value
    if isinstance(value, str) and value in VALID_REVISION_STATUSES:
        return RevisionStatus(value)
    raise RevisionPersistenceFailure(
        f"invalid revision status {value!r}; must be one of {sorted(VALID_REVISION_STATUSES)}",
        failure_reason="invalid_status_enum",
    )


# --- Transition enforcement -------------------------------------------------


def assert_transition_allowed(
    src: RevisionStatus | str,
    dst: RevisionStatus | str,
) -> None:
    """Raise ``RevisionPersistenceFailure`` iff ``src -> dst`` is forbidden
    (Section 7.3). Returns ``None`` on a legal transition.
    """
    src_e = ensure_status_valid(src)
    dst_e = ensure_status_valid(dst)
    if not is_allowed_transition(src_e, dst_e):
        raise RevisionPersistenceFailure(
            f"forbidden transition {src_e.value} -> {dst_e.value} (Section 7.3)",
            failure_reason="forbidden_transition",
        )


# --- Transition factory: returns (new_revision, audit_event) ---------------


def transition_with_audit(
    revision: CaseRevision,
    *,
    new_status: RevisionStatus | str,
    actor_id: str,
    source: str,
    occurred_at: datetime,
    supersede_with: CaseRevision | None = None,
    audit_event_id: str | None = None,
    audit_payload: dict[str, Any] | None = None,
) -> tuple[CaseRevision, CaseRevisionAuditEvent]:
    """Apply a lifecycle transition and return ``(new_revision, audit_event)``.

    Section 6.2 — every transition emits an audit event. The mapping from
    ``new_status`` to ``AuditEventType`` is:

    * ``validated`` -> ``revision_validated``
    * ``committed`` -> ``revision_committed``
    * ``superseded`` -> ``revision_superseded`` (requires ``supersede_with``
      pointing at the successor revision)
    * ``archived`` -> ``revision_archived``
    * ``tombstoned`` -> ``revision_tombstoned``
    * ``rejected`` -> ``revision_rejected``

    Section 7 — forbidden transitions raise ``RevisionPersistenceFailure``.
    """
    src = revision.status
    dst = coerce_status(new_status)
    assert_transition_allowed(src, dst)

    superseded_by: str | None = None
    archived_at: datetime | None = None
    tombstone_at: datetime | None = None
    # Section 6.7 — committed identity is written ONCE on the
    # ``validated -> committed`` transition; subsequent transitions
    # (committed -> superseded / archived / tombstoned) MUST preserve
    # the existing committed_at / committed_by. The lifecycle helper
    # below explicitly only sets these on the commit transition and
    # leaves them at ``None`` (i.e., "preserve existing") otherwise.
    committed_at: datetime | None = None
    committed_by: str | None = None
    if dst == RevisionStatus.SUPERSEDED:
        if supersede_with is None:
            raise RevisionPersistenceFailure(
                "superseded transition requires supersede_with",
                failure_reason="missing_successor_revision",
            )
        superseded_by = supersede_with.revision_id
    if dst == RevisionStatus.ARCHIVED:
        archived_at = occurred_at
    if dst == RevisionStatus.TOMBSTONED:
        tombstone_at = occurred_at
    if dst == RevisionStatus.COMMITTED:
        # Section 6.7 — set committed identity EXACTLY ONCE on the
        # validated -> committed transition. The model helper
        # (``transition_revision``) only overwrites a field when the
        # kwarg is non-None, so a ``None`` kwarg on later transitions
        # preserves the existing committed identity.
        committed_at = occurred_at
        committed_by = actor_id

    new_revision = transition_revision(
        revision,
        new_status=dst,
        superseded_by=superseded_by,
        archived_at=archived_at,
        tombstone_at=tombstone_at,
        committed_at=committed_at,
        committed_by=committed_by,
    )

    audit_type = _status_to_audit_type(dst)
    event = CaseRevisionAuditEvent(
        event_id=audit_event_id or _mint_event_id(revision.revision_id, audit_type, occurred_at),
        revision_id=revision.revision_id,
        root_case_id=revision.root_case_id,
        event_type=audit_type,
        actor_id=actor_id,
        source=source,
        occurred_at=occurred_at,
        payload=dict(audit_payload) if audit_payload else {},
    )
    return new_revision, event


def audit_event_for_draft_creation(
    *,
    revision: CaseRevision,
    actor_id: str,
    source: str,
    occurred_at: datetime,
    event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> CaseRevisionAuditEvent:
    """Section 14.1 — emit ``revision_created`` for a freshly recorded
    draft proposal."""
    if revision.status != RevisionStatus.DRAFT:
        raise RevisionPersistenceFailure(
            f"revision_created audit event requires status=draft; got {revision.status.value}",
            revision_id=revision.revision_id,
            root_case_id=revision.root_case_id,
            failure_reason="audit_status_mismatch",
        )
    return CaseRevisionAuditEvent(
        event_id=event_id
        or _mint_event_id(revision.revision_id, AuditEventType.REVISION_CREATED, occurred_at),
        revision_id=revision.revision_id,
        root_case_id=revision.root_case_id,
        event_type=AuditEventType.REVISION_CREATED,
        actor_id=actor_id,
        source=source,
        occurred_at=occurred_at,
        payload=dict(payload) if payload else {},
    )


# --- Helpers ---------------------------------------------------------------


_STATUS_TO_AUDIT: dict[RevisionStatus, AuditEventType] = {
    RevisionStatus.VALIDATED: AuditEventType.REVISION_VALIDATED,
    RevisionStatus.COMMITTED: AuditEventType.REVISION_COMMITTED,
    RevisionStatus.SUPERSEDED: AuditEventType.REVISION_SUPERSEDED,
    RevisionStatus.ARCHIVED: AuditEventType.REVISION_ARCHIVED,
    RevisionStatus.TOMBSTONED: AuditEventType.REVISION_TOMBSTONED,
    RevisionStatus.REJECTED: AuditEventType.REVISION_REJECTED,
}


def _status_to_audit_type(status: RevisionStatus) -> AuditEventType:
    try:
        return _STATUS_TO_AUDIT[status]
    except KeyError as err:
        raise RevisionPersistenceFailure(
            f"no audit event type mapping for status={status.value}",
            failure_reason="missing_audit_mapping",
        ) from err


def _mint_event_id(revision_id: str, event_type: AuditEventType, occurred_at: datetime) -> str:
    """Deterministic-ish event id derived from revision + type + occurred_at.

    Not a true UUID; chosen for determinism in tests. Format:
    ``audit:<revision_id>:<event_type>:<iso8601>``. Callsite is allowed
    to override with a real UUID via ``event_id=`` arg.
    """
    return f"audit:{revision_id}:{event_type.value}:{occurred_at.isoformat()}"


__all__ = [
    "VALID_REVISION_STATUSES",
    "assert_transition_allowed",
    "audit_event_for_draft_creation",
    "ensure_status_valid",
    "transition_with_audit",
]
