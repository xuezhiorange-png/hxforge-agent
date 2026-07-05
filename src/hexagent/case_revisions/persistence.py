"""In-memory persistence adapter for TASK-014 immutable case revisions.

Implements Sections 9 (logical schema) + 13 (concurrency + atomic commit)
of the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

This module is the TASK-014 equivalent of
:mod:`hexagent.repositories.memory.InMemoryDesignCaseRevisionRepository`,
extended with:

* Immutable commit semantics (Section 6 — append-only, no in-place fix,
  no destructive delete).
* Expected-parent concurrency check (Section 13.1) — raises
  :class:`StaleParentRevision`.
* Optimistic concurrency token check (Section 13.2) — raises
  :class:`CaseRevisionConflict` with ``conflict_reason="token_mismatch"``.
* Idempotency-key deduplication (Section 13.3) — second request returns
  the existing revision.
* Atomic commit (Section 13.4) — revision row + parent-chain links +
  audit event + idempotency-key row are written in a single
  ``_atomic_commit`` call that rolls back on any failure.
* Concurrent sibling creation handling (Section 13.5) — duplicate
  ``(root_case_id, revision_number)`` raises
  :class:`CaseRevisionConflict` with ``conflict_reason="concurrent_sibling"``.

The repository is intentionally in-memory for the implementation PR; the
logical schema in Section 9 is storage-neutral and a future PR can swap
this for a DB-specific adapter. The interface mirrors what a SQL-backed
adapter would expose.
"""

from __future__ import annotations

import copy
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from hexagent.case_revisions.canonical import (
    compute_domain_snapshot_hash,
    compute_payload_hash,
)
from hexagent.case_revisions.errors import (
    CaseRevisionConflict,
    InvalidRevisionPayload,
    RevisionHashMismatch,
    RevisionPersistenceFailure,
    StaleParentRevision,
)
from hexagent.case_revisions.lifecycle import (
    audit_event_for_draft_creation,
    ensure_status_valid,
    transition_with_audit,
)
from hexagent.case_revisions.models import (
    AuditEventType,
    CaseRevision,
    CaseRevisionAuditEvent,
    IdempotencyKeyRecord,
    ParentChainLink,
    RevisionStatus,
    build_parent_chain_links,
)

# Re-export for type-hint completeness.
_ = IdempotencyKeyRecord


# --- Repository protocol-style class (in-memory) ---------------------------


class InMemoryCaseRevisionRepository:
    """In-memory implementation of the TASK-014 persistence boundary.

    All ``add_revision`` / ``add_audit_event`` / ``record_idempotency_key``
    calls are routed through a single ``_atomic_commit`` block so that a
    failure at any step rolls back the partial write (Section 13.4).

    Every stored record is deep-copied on insert and on retrieval, so
    callers cannot mutate repository state through retrieved objects.
    """

    def __init__(self) -> None:
        self._revisions_by_id: dict[str, CaseRevision] = {}
        self._revisions_by_root: dict[str, dict[int, CaseRevision]] = {}
        self._audit_by_id: dict[str, CaseRevisionAuditEvent] = {}
        self._parent_links: dict[str, tuple[ParentChainLink, ...]] = {}
        self._idempotency: dict[tuple[str, str], IdempotencyKeyRecord] = {}
        self._token_to_revision: dict[str, str] = {}  # token -> revision_id

    # -- Read API ------------------------------------------------------------

    def get_revision(self, revision_id: str) -> CaseRevision:
        try:
            return copy.deepcopy(self._revisions_by_id[revision_id])
        except KeyError as err:
            raise KeyError(f"CaseRevision not found: {revision_id}") from err

    def has_revision(self, revision_id: str) -> bool:
        return revision_id in self._revisions_by_id

    def head_revision(self, root_case_id: str) -> CaseRevision | None:
        rev_map = self._revisions_by_root.get(root_case_id)
        if not rev_map:
            return None
        latest_number = max(rev_map)
        return copy.deepcopy(rev_map[latest_number])

    def list_revisions(self, root_case_id: str) -> tuple[CaseRevision, ...]:
        rev_map = self._revisions_by_root.get(root_case_id)
        if not rev_map:
            return ()
        return tuple(copy.deepcopy(rev_map[n]) for n in sorted(rev_map))

    def list_audit_events(self, revision_id: str) -> tuple[CaseRevisionAuditEvent, ...]:
        return tuple(ev for ev in self._audit_by_id.values() if ev.revision_id == revision_id)

    def lookup_idempotency(
        self, root_case_id: str, idempotency_key: str
    ) -> IdempotencyKeyRecord | None:
        return copy.deepcopy(self._idempotency.get((root_case_id, idempotency_key)))

    # -- Write API -----------------------------------------------------------

    def create_revision(
        self,
        *,
        revision: CaseRevision,
        actor_id: str,
        source: str,
        occurred_at: datetime,
        audit_event_id: str | None = None,
        audit_payload: dict[str, Any] | None = None,
    ) -> tuple[CaseRevision, CaseRevisionAuditEvent]:
        """Record a draft revision. Returns ``(revision, audit_event)``.

        Validates:

        * Section 12.1 — identity, status enum, required fields.
        * Section 12.2 — payload_hash, domain_snapshot_hash, parent_chain_hash.
        * Section 12.5 — expected_parent_revision_id (raises
          :class:`StaleParentRevision` on mismatch).
        * Section 13.3 — idempotency_key deduplication (returns existing
          revision + a synthetic audit event noting dedup).
        * Section 13.5 — duplicate ``(root_case_id, revision_number)`` raises
          :class:`CaseRevisionConflict` with
          ``conflict_reason="concurrent_sibling"``.
        """
        self._validate_revision_payload(revision)

        # Section 12.5 / 13.1 — expected_parent check.
        actual_head = self.head_revision(revision.root_case_id)
        if revision.expected_parent_revision_id is not None:
            actual_head_id = actual_head.revision_id if actual_head else None
            if revision.expected_parent_revision_id != actual_head_id:
                raise StaleParentRevision(
                    "expected_parent_revision_id does not equal current head "
                    f"of root_case_id={revision.root_case_id!r}",
                    root_case_id=revision.root_case_id,
                    revision_id=revision.revision_id,
                    expected_parent_revision_id=revision.expected_parent_revision_id,
                    actual_parent_revision_id=actual_head_id,
                )

        # Section 13.3 — idempotency-key deduplication.
        if revision.idempotency_key is not None:
            existing = self.lookup_idempotency(revision.root_case_id, revision.idempotency_key)
            if existing is not None:
                # Return the existing revision without creating a duplicate.
                existing_rev = self.get_revision(existing.revision_id)
                dedup_audit = CaseRevisionAuditEvent(
                    event_id=audit_event_id
                    or _mint_event_id(
                        existing.revision_id,
                        _NO_NEW_AUDIT,
                        occurred_at,
                    ),
                    revision_id=existing.revision_id,
                    root_case_id=revision.root_case_id,
                    event_type=_NO_NEW_AUDIT,
                    actor_id=actor_id,
                    source=source,
                    occurred_at=occurred_at,
                    payload={
                        "dedup": True,
                        "requested_revision_id": revision.revision_id,
                    },
                )
                return existing_rev, dedup_audit

        # Section 13.5 — duplicate (root_case_id, revision_number).
        rev_map = self._revisions_by_root.setdefault(revision.root_case_id, {})
        if revision.revision_number in rev_map:
            actual = rev_map[revision.revision_number]
            raise CaseRevisionConflict(
                f"duplicate (root_case_id={revision.root_case_id!r}, "
                f"revision_number={revision.revision_number}); "
                "concurrent sibling creation not allowed (Section 13.5)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                conflict_reason="concurrent_sibling",
                expected_parent_revision_id=revision.expected_parent_revision_id,
                actual_parent_revision_id=actual.revision_id,
                attempted_revision_number=revision.revision_number,
            )

        # Section 13.2 — optimistic_concurrency_token must be unique.
        if (
            revision.optimistic_concurrency_token is not None
            and revision.optimistic_concurrency_token in self._token_to_revision
        ):
            conflicting = self._token_to_revision[revision.optimistic_concurrency_token]
            raise CaseRevisionConflict(
                "optimistic_concurrency_token already in use (Section 13.2)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                conflict_reason="token_mismatch",
                expected_parent_revision_id=revision.expected_parent_revision_id,
                actual_parent_revision_id=conflicting,
                attempted_revision_number=revision.revision_number,
            )

        # Build parent-chain links.
        parent_rev: CaseRevision | None
        if revision.parent_revision_id is None:
            if revision.revision_number != 1:
                raise InvalidRevisionPayload(
                    "first revision of root_case_id must have revision_number=1 (Section 9.2)",
                    root_case_id=revision.root_case_id,
                    revision_id=revision.revision_id,
                    path="revision_number",
                    reason="first_revision_requires_revision_number_1",
                )
            parent_rev = None
        else:
            try:
                parent_rev = self.get_revision(revision.parent_revision_id)
            except KeyError as err:
                raise RevisionPersistenceFailure(
                    f"parent_revision_id={revision.parent_revision_id!r} not found (Section 12.1)",
                    root_case_id=revision.root_case_id,
                    revision_id=revision.revision_id,
                    failure_reason="missing_parent",
                ) from err
            if parent_rev.root_case_id != revision.root_case_id:
                raise RevisionPersistenceFailure(
                    f"parent_revision_id={revision.parent_revision_id!r} "
                    f"belongs to root_case_id={parent_rev.root_case_id!r}; "
                    f"expected same root (Section 9.2)",
                    root_case_id=revision.root_case_id,
                    revision_id=revision.revision_id,
                    failure_reason="parent_root_case_mismatch",
                )
            expected_number = parent_rev.revision_number + 1
            if revision.revision_number != expected_number:
                raise RevisionPersistenceFailure(
                    f"revision_number={revision.revision_number} is not "
                    f"parent.revision_number + 1 (expected "
                    f"{expected_number}; Section 9.2)",
                    root_case_id=revision.root_case_id,
                    revision_id=revision.revision_id,
                    failure_reason="non_monotonic_revision_number",
                )
        links = build_parent_chain_links(
            revision_id=revision.revision_id, parent_revision=parent_rev
        )

        # Section 9.1 — idempotency_key row is part of the atomic commit.
        idem_record: IdempotencyKeyRecord | None = None
        if revision.idempotency_key is not None:
            idem_record = IdempotencyKeyRecord(
                root_case_id=revision.root_case_id,
                idempotency_key=revision.idempotency_key,
                revision_id=revision.revision_id,
                created_at=occurred_at,
            )

        # Audit event (Section 14.1). The first audit event type depends
        # on the initial status: a draft emits ``revision_created``;
        # any other initial status (e.g., a directly-committed
        # bootstrap revision) emits the corresponding lifecycle event.
        audit = _initial_audit_event(
            revision=revision,
            actor_id=actor_id,
            source=source,
            occurred_at=occurred_at,
            event_id=audit_event_id,
            payload=audit_payload,
        )

        # Section 13.4 — atomic commit.
        self._atomic_commit(
            revision=revision,
            audit_event=audit,
            parent_links=links,
            idempotency_record=idem_record,
        )
        return revision, audit

    def transition_revision(
        self,
        *,
        revision: CaseRevision,
        new_status: RevisionStatus,
        actor_id: str,
        source: str,
        occurred_at: datetime,
        supersede_with: CaseRevision | None = None,
        audit_payload: dict[str, Any] | None = None,
    ) -> tuple[CaseRevision, CaseRevisionAuditEvent]:
        """Apply a lifecycle transition. Section 6.2 — every transition
        emits an audit event. Section 13.4 — atomic commit."""
        # The incoming ``revision`` may be a deep-copied snapshot; we
        # work against the stored record so we update the latest version.
        if not self.has_revision(revision.revision_id):
            raise RevisionPersistenceFailure(
                f"revision {revision.revision_id!r} not found in repository",
                revision_id=revision.revision_id,
                root_case_id=revision.root_case_id,
                failure_reason="missing_revision",
            )
        stored = self.get_revision(revision.revision_id)
        new_revision, audit = transition_with_audit(
            stored,
            new_status=new_status,
            actor_id=actor_id,
            source=source,
            occurred_at=occurred_at,
            supersede_with=supersede_with,
            audit_payload=audit_payload,
        )
        # Replace the stored revision (Section 6.1 — append-only at the
        # repository level: each transition stores a new immutable record
        # keyed by the same revision_id; the old record is overwritten
        # because the immutable identity fields (revision_id, payload,
        # hashes) are unchanged, only status metadata evolved).
        self._revisions_by_id[new_revision.revision_id] = copy.deepcopy(new_revision)
        self._revisions_by_root[new_revision.root_case_id][new_revision.revision_number] = (
            copy.deepcopy(new_revision)
        )
        self._atomic_audit_insert(audit)
        return new_revision, audit

    def assert_token_matches(self, *, revision_id: str, expected_token: str) -> None:
        """Section 13.2 — present token must match the stored token.

        Raises :class:`CaseRevisionConflict` with
        ``conflict_reason="token_mismatch"`` on mismatch.
        """
        stored = self.get_revision(revision_id)
        if stored.optimistic_concurrency_token != expected_token:
            raise CaseRevisionConflict(
                f"optimistic_concurrency_token mismatch for revision_id={revision_id!r}",
                root_case_id=stored.root_case_id,
                revision_id=revision_id,
                conflict_reason="token_mismatch",
                expected_parent_revision_id=None,
                actual_parent_revision_id=None,
                attempted_revision_number=stored.revision_number,
            )

    # -- Validation helpers --------------------------------------------------

    def _validate_revision_payload(self, revision: CaseRevision) -> None:
        # Section 12.1 — required identity fields.
        if not revision.revision_id:
            raise InvalidRevisionPayload(
                "missing required field: revision_id",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                path="revision_id",
                reason="missing_required_field",
            )
        if not revision.root_case_id:
            raise InvalidRevisionPayload(
                "missing required field: root_case_id",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                path="root_case_id",
                reason="missing_required_field",
            )
        # Section 12.1 — status enum validation.
        ensure_status_valid(revision.status)

        # Section 12.2 — recompute hashes and compare to stored.
        actual_payload_hash = compute_payload_hash(revision.payload)
        if actual_payload_hash != revision.payload_hash:
            raise RevisionHashMismatch(
                "payload_hash does not match canonicalized payload (Section 12.2)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                expected_payload_hash=revision.payload_hash,
                actual_payload_hash=actual_payload_hash,
                hash_field="payload_hash",
            )
        parent_chain_for_hash: tuple[dict[str, Any], ...] = (
            self._parent_chain_rows_for_revision(revision.revision_id)
            if revision.revision_id in self._parent_links
            else ()
        )
        actual_snapshot_hash = compute_domain_snapshot_hash(
            identity=revision.identity,
            payload=revision.payload,
            provenance=revision.provenance,
            parent_chain=parent_chain_for_hash,
        )
        if actual_snapshot_hash != revision.domain_snapshot_hash:
            raise RevisionHashMismatch(
                "domain_snapshot_hash does not match canonicalized domain snapshot (Section 12.2)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                expected_payload_hash=revision.domain_snapshot_hash,
                actual_payload_hash=actual_snapshot_hash,
                hash_field="domain_snapshot_hash",
            )

    def _parent_chain_rows_for_revision(self, revision_id: str) -> tuple[dict[str, Any], ...]:
        links = self._parent_links.get(revision_id, ())
        return tuple(
            {
                "revision_id": link.revision_id,
                "parent_revision_id": link.parent_revision_id,
                "link_order": link.link_order,
            }
            for link in sorted(links, key=lambda link: link.link_order)
        )

    # -- Atomic commit -------------------------------------------------------

    def _atomic_commit(
        self,
        *,
        revision: CaseRevision,
        audit_event: CaseRevisionAuditEvent,
        parent_links: Iterable[ParentChainLink],
        idempotency_record: IdempotencyKeyRecord | None,
    ) -> None:
        """Section 13.4 — write revision + parent-links + audit + idempotency
        in a single atomic block. On any failure, NO partial state is
        persisted (``RevisionPersistenceFailure.partial_state = False``).
        """
        snapshot_revisions = copy.deepcopy(self._revisions_by_id)
        snapshot_root = copy.deepcopy(self._revisions_by_root)
        snapshot_audit = copy.deepcopy(self._audit_by_id)
        snapshot_links = copy.deepcopy(self._parent_links)
        snapshot_idem = copy.deepcopy(self._idempotency)
        snapshot_tokens = copy.deepcopy(self._token_to_revision)

        try:
            self._revisions_by_id[revision.revision_id] = copy.deepcopy(revision)
            self._revisions_by_root.setdefault(revision.root_case_id, {})[
                revision.revision_number
            ] = copy.deepcopy(revision)
            self._parent_links[revision.revision_id] = tuple(parent_links)
            if revision.optimistic_concurrency_token is not None:
                self._token_to_revision[revision.optimistic_concurrency_token] = (
                    revision.revision_id
                )
            if idempotency_record is not None:
                self._idempotency[
                    (idempotency_record.root_case_id, idempotency_record.idempotency_key)
                ] = copy.deepcopy(idempotency_record)
            # Audit is written LAST inside the atomic block so any
            # previous failure rolls back the audit too. A separate
            # ``_atomic_audit_insert`` helper is used for transitions
            # that emit only an audit event.
            self._atomic_audit_insert(audit_event)
        except Exception as err:
            # Section 6.8 — no partial state.
            self._revisions_by_id = snapshot_revisions
            self._revisions_by_root = snapshot_root
            self._audit_by_id = snapshot_audit
            self._parent_links = snapshot_links
            self._idempotency = snapshot_idem
            self._token_to_revision = snapshot_tokens
            raise RevisionPersistenceFailure(
                f"atomic commit failed for revision_id={revision.revision_id!r}; "
                f"rolled back; partial_state=False (Section 6.8)",
                root_case_id=revision.root_case_id,
                revision_id=revision.revision_id,
                failure_reason=type(err).__name__,
                partial_state=False,
            ) from err

    def _atomic_audit_insert(self, audit_event: CaseRevisionAuditEvent) -> None:
        # Section 14.2 — audit events are append-only; never overwritten.
        if audit_event.event_id in self._audit_by_id:
            raise RevisionPersistenceFailure(
                f"duplicate audit event_id={audit_event.event_id!r}; "
                "audit events are append-only (Section 14.2)",
                root_case_id=audit_event.root_case_id,
                revision_id=audit_event.revision_id,
                failure_reason="duplicate_audit_event",
            )
        self._audit_by_id[audit_event.event_id] = copy.deepcopy(audit_event)


# --- Internal helpers ------------------------------------------------------


_NO_NEW_AUDIT = AuditEventType.REVISION_CREATED  # placeholder; dedup
# synthetic events reuse this event_type so the enum stays closed but the
# payload explicitly flags ``dedup=True``. Callers MUST NOT treat the
# event_type of a dedup audit as authoritative.


def _mint_event_id(revision_id: str, event_type: Any, occurred_at: datetime) -> str:
    """Deterministic event id helper for synthetic dedup audit events."""
    return f"audit:{revision_id}:dedup:{occurred_at.isoformat()}"


def _initial_audit_event(
    *,
    revision: CaseRevision,
    actor_id: str,
    source: str,
    occurred_at: datetime,
    event_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> CaseRevisionAuditEvent:
    """Return the audit event for the initial insert of a revision.

    Section 14.1 — the initial event type depends on the initial status:

    * ``draft`` -> ``revision_created``
    * ``validated`` -> ``revision_validated``
    * ``committed`` -> ``revision_committed``
    * ``superseded`` -> ``revision_superseded`` (unusual on first insert)
    * ``archived`` -> ``revision_archived``
    * ``tombstoned`` -> ``revision_tombstoned``
    * ``rejected`` -> ``revision_rejected``

    For non-draft initial statuses (e.g., a bootstrap revision created
    directly in the ``committed`` state), the corresponding lifecycle
    audit event is emitted; subsequent transitions emit the next event
    in the chain.
    """
    from hexagent.case_revisions.lifecycle import (
        _status_to_audit_type,
    )

    if revision.status == RevisionStatus.DRAFT:
        return audit_event_for_draft_creation(
            revision=revision,
            actor_id=actor_id,
            source=source,
            occurred_at=occurred_at,
            event_id=event_id,
            payload=payload,
        )
    # For any other initial status, build the corresponding lifecycle event.
    audit_type = _status_to_audit_type(revision.status)
    return CaseRevisionAuditEvent(
        event_id=event_id
        or f"audit:{revision.revision_id}:{audit_type.value}:{occurred_at.isoformat()}",
        revision_id=revision.revision_id,
        root_case_id=revision.root_case_id,
        event_type=audit_type,
        actor_id=actor_id,
        source=source,
        occurred_at=occurred_at,
        payload=dict(payload) if payload else {},
    )


__all__ = [
    "InMemoryCaseRevisionRepository",
]
