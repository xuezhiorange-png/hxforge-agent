"""Audit emission helpers for TASK-014 immutable case revisions.

Implements Section 14 of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 14.1 — closed set of audit event types.
Section 14.2 — audit events are immutable / append-only.
Section 14.3 — every audit event carries ``actor_id`` and ``source``.
Section 14.4 — audit events form an append-only DAG joinable to the
TASK-004 / TASK-005 / TASK-013 provenance graph.
Section 14.5 — every state transition MUST emit an audit event.

This module provides thin convenience helpers that wrap
:func:`hexagent.case_revisions.lifecycle.transition_with_audit` /
:func:`hexagent.case_revisions.lifecycle.audit_event_for_draft_creation`
so application code can call ``emit_*`` methods without depending on the
lifecycle module directly.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from hexagent.case_revisions.errors import (
    RevisionPersistenceFailure,
)
from hexagent.case_revisions.lifecycle import (
    audit_event_for_draft_creation,
    transition_with_audit,
)
from hexagent.case_revisions.models import (
    AuditEventType,
    CaseRevision,
    CaseRevisionAuditEvent,
    RevisionStatus,
)


def emit_revision_created(
    revision: CaseRevision,
    *,
    actor_id: str,
    source: str,
    occurred_at: datetime,
    event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> CaseRevisionAuditEvent:
    """Section 14.1 — emit a ``revision_created`` audit event for a draft
    proposal.

    The repository calls this helper inside its atomic-commit block; this
    wrapper is exposed for callers that construct audit events outside
    the repository (e.g., bulk import tooling).
    """
    if not actor_id:
        raise RevisionPersistenceFailure(
            "actor_id is required for audit events (Section 14.3)",
            revision_id=revision.revision_id,
            root_case_id=revision.root_case_id,
            failure_reason="missing_actor_id",
        )
    if not source:
        raise RevisionPersistenceFailure(
            "source is required for audit events (Section 14.3)",
            revision_id=revision.revision_id,
            root_case_id=revision.root_case_id,
            failure_reason="missing_source",
        )
    return audit_event_for_draft_creation(
        revision=revision,
        actor_id=actor_id,
        source=source,
        occurred_at=occurred_at,
        event_id=event_id,
        payload=payload,
    )


def emit_transition(
    revision: CaseRevision,
    *,
    new_status: RevisionStatus,
    actor_id: str,
    source: str,
    occurred_at: datetime,
    supersede_with: CaseRevision | None = None,
    audit_payload: dict[str, Any] | None = None,
) -> tuple[CaseRevision, CaseRevisionAuditEvent]:
    """Section 14.1 + 14.5 — apply a lifecycle transition and return the
    resulting ``(revision, audit_event)``.

    Every transition emits exactly one audit event. The mapping from
    ``new_status`` to ``AuditEventType`` is implemented in
    :func:`hexagent.case_revisions.lifecycle.transition_with_audit`.
    """
    if not actor_id:
        raise RevisionPersistenceFailure(
            "actor_id is required for audit events (Section 14.3)",
            revision_id=revision.revision_id,
            root_case_id=revision.root_case_id,
            failure_reason="missing_actor_id",
        )
    if not source:
        raise RevisionPersistenceFailure(
            "source is required for audit events (Section 14.3)",
            revision_id=revision.revision_id,
            root_case_id=revision.root_case_id,
            failure_reason="missing_source",
        )
    return transition_with_audit(
        revision,
        new_status=new_status,
        actor_id=actor_id,
        source=source,
        occurred_at=occurred_at,
        supersede_with=supersede_with,
        audit_payload=audit_payload,
    )


def assert_audit_event_complete(event: CaseRevisionAuditEvent) -> None:
    """Section 14.3 — every audit event MUST carry ``actor_id`` and
    ``source``. Section 14.2 — audit events MUST carry ``event_id``,
    ``revision_id``, ``root_case_id``, ``event_type``, ``occurred_at``,
    and ``payload``."""
    missing = [
        field_name
        for field_name, value in (
            ("event_id", event.event_id),
            ("revision_id", event.revision_id),
            ("root_case_id", event.root_case_id),
            ("event_type", event.event_type),
            ("actor_id", event.actor_id),
            ("source", event.source),
            ("occurred_at", event.occurred_at),
        )
        if not value
    ]
    if missing:
        raise RevisionPersistenceFailure(
            f"audit event is missing required fields: {missing} (Section 14.2 / 14.3)",
            revision_id=event.revision_id,
            root_case_id=event.root_case_id,
            failure_reason="incomplete_audit_event",
        )


__all__ = [
    "AuditEventType",
    "assert_audit_event_complete",
    "emit_revision_created",
    "emit_transition",
]
