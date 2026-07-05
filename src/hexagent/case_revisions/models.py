"""Domain models for TASK-014 immutable case revisions.

Implements the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Sections covered:

* Section 5 — core entities and identities (``Case``, ``CaseRevision``,
  ``CaseRevisionAuditEvent``) with opaque stable identifiers, append-only
  revisions, immutable identity fields, and uniqueness invariants.
* Section 6 — immutable revision contract (8 rules).
* Section 7 — revision lifecycle states + allowed / forbidden transition
  table.
* Section 14 — audit event types and immutability.

All entities are immutable dataclasses; transitions create new objects
(append-only). Audit events are append-only and never mutated.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any

# --- Lifecycle states (Section 7) ------------------------------------------


class RevisionStatus(str, enum.Enum):  # noqa: UP042
    """Section 7.1 — closed set of allowed revision statuses."""

    DRAFT = "draft"
    VALIDATED = "validated"
    COMMITTED = "committed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"
    TOMBSTONED = "tombstoned"
    REJECTED = "rejected"


# Section 7.2 — allowed transitions
ALLOWED_TRANSITIONS: dict[RevisionStatus, frozenset[RevisionStatus]] = {
    RevisionStatus.DRAFT: frozenset({RevisionStatus.VALIDATED, RevisionStatus.REJECTED}),
    RevisionStatus.VALIDATED: frozenset({RevisionStatus.COMMITTED, RevisionStatus.REJECTED}),
    RevisionStatus.COMMITTED: frozenset(
        {
            RevisionStatus.SUPERSEDED,
            RevisionStatus.ARCHIVED,
            RevisionStatus.TOMBSTONED,
        }
    ),
    RevisionStatus.SUPERSEDED: frozenset({RevisionStatus.ARCHIVED, RevisionStatus.TOMBSTONED}),
    RevisionStatus.ARCHIVED: frozenset({RevisionStatus.TOMBSTONED}),
    RevisionStatus.TOMBSTONED: frozenset(),  # terminal
    RevisionStatus.REJECTED: frozenset(),  # terminal
}


def is_allowed_transition(src: RevisionStatus, dst: RevisionStatus) -> bool:
    """Return True iff ``src -> dst`` is an allowed transition
    (Section 7.2)."""
    return dst in ALLOWED_TRANSITIONS.get(src, frozenset())


# --- Audit event types (Section 14.1) -------------------------------------


class AuditEventType(str, enum.Enum):  # noqa: UP042
    """Section 14.1 — closed set of audit event types."""

    REVISION_CREATED = "revision_created"
    REVISION_VALIDATED = "revision_validated"
    REVISION_COMMITTED = "revision_committed"
    REVISION_SUPERSEDED = "revision_superseded"
    REVISION_ARCHIVED = "revision_archived"
    REVISION_TOMBSTONED = "revision_tombstoned"
    REVISION_REJECTED = "revision_rejected"


# --- Case entity (Section 5) -----------------------------------------------


@dataclass(frozen=True)
class Case:
    """Section 5 — Case envelope.

    A ``Case`` is the project-wide stable identifier for a logical design
    problem. The first ``CaseRevision`` carries ``case_id == root_case_id``.
    """

    case_id: str
    root_case_id: str
    first_revision_id: str
    status: str  # one of {active, archived, tombstoned}
    created_at: datetime
    created_by: str
    archived_at: datetime | None = None
    tombstone_at: datetime | None = None


# --- CaseRevision entity (Section 5) ---------------------------------------


@dataclass(frozen=True)
class CaseRevision:
    """Section 5 — CaseRevision record.

    Append-only: every transition produces a new immutable record. There
    is no in-place update operation (Section 6 rules #1, #2).
    """

    revision_id: str
    case_id: str
    root_case_id: str
    revision_number: int
    parent_revision_id: str | None
    parent_chain_hash: str | None
    payload_hash: str
    domain_snapshot_hash: str
    payload: dict[str, Any]
    identity: dict[str, Any]
    provenance: dict[str, Any]
    created_at: datetime
    created_by: str
    committed_at: datetime | None
    committed_by: str | None
    status: RevisionStatus
    superseded_by: str | None = None
    archived_at: datetime | None = None
    tombstone_at: datetime | None = None
    expected_parent_revision_id: str | None = None
    idempotency_key: str | None = None
    optimistic_concurrency_token: str | None = None

    # -- Section 6.5 / 6.6 identity immutability checks ---------------------

    def __post_init__(self) -> None:
        # Section 9.2 — revision_number >= 1
        if not isinstance(self.revision_number, int) or self.revision_number < 1:
            raise ValueError(f"revision_number must be int >= 1; got {self.revision_number!r}")
        # payload_hash and domain_snapshot_hash are 64-hex (sha256)
        if not _is_sha256_hex(self.payload_hash):
            raise ValueError(f"payload_hash must be 64-hex SHA-256; got {self.payload_hash!r}")
        if not _is_sha256_hex(self.domain_snapshot_hash):
            raise ValueError(
                f"domain_snapshot_hash must be 64-hex SHA-256; got {self.domain_snapshot_hash!r}"
            )
        # parent_chain_hash, when present, must be 64-hex
        if self.parent_chain_hash is not None and not _is_sha256_hex(self.parent_chain_hash):
            raise ValueError(
                f"parent_chain_hash, when present, must be 64-hex SHA-256; "
                f"got {self.parent_chain_hash!r}"
            )
        # Section 5 — first revision has parent_revision_id == None iff
        # revision_number == 1; this is enforced at commit time (see
        # persistence.commit_revision), not here, to keep models purely
        # structural.


def _is_sha256_hex(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
        return True
    except ValueError:
        return False


# --- CaseRevisionAuditEvent entity (Section 5 + 14) -----------------------


@dataclass(frozen=True)
class CaseRevisionAuditEvent:
    """Section 5 + 14 — CaseRevisionAuditEvent.

    Append-only. Once inserted, an audit event MUST NOT be updated or
    deleted (Section 14.2).
    """

    event_id: str
    revision_id: str
    root_case_id: str
    event_type: AuditEventType
    actor_id: str
    source: str
    occurred_at: datetime
    payload: dict[str, Any] = field(default_factory=dict)


# --- Parent-chain link (Section 9.1 case_revision_parents) ----------------


@dataclass(frozen=True)
class ParentChainLink:
    """Section 9.1 — one row of ``case_revision_parents``.

    Stores a (parent_revision_id, link_order) tuple for a single revision.
    The first entry (link_order == 0) is the immediate parent; subsequent
    entries walk the ancestry chain in order. For revision_number == 1,
    the parent chain is empty (no links).
    """

    revision_id: str
    parent_revision_id: str
    link_order: int

    def __post_init__(self) -> None:
        if not isinstance(self.link_order, int) or self.link_order < 0:
            raise ValueError(f"link_order must be int >= 0; got {self.link_order!r}")


# --- Idempotency-key record (Section 9.1 idempotency_keys) ----------------


@dataclass(frozen=True)
class IdempotencyKeyRecord:
    """Section 9.1 — ``idempotency_keys`` row."""

    root_case_id: str
    idempotency_key: str
    revision_id: str
    created_at: datetime


# --- Parent-chain row collection helpers ----------------------------------


def build_parent_chain_links(
    *,
    revision_id: str,
    parent_revision: CaseRevision | None,
) -> tuple[ParentChainLink, ...]:
    """Construct the parent-chain link rows for a new revision.

    For the initial revision (parent_revision is None), the chain is
    empty. For non-initial revisions, the chain begins with the immediate
    parent (link_order == 0). Subsequent links walk back through
    ``parent_revision.parent_revision_id`` in 1 step; future implementations
    that record full ancestry can extend this helper.
    """
    if parent_revision is None:
        return ()
    # Section 9.1 — link_order starts at 0 for the immediate parent.
    return (
        ParentChainLink(
            revision_id=revision_id,
            parent_revision_id=parent_revision.revision_id,
            link_order=0,
        ),
    )


# --- Equality / hashing -----------------------------------------------------

# All entities are frozen dataclasses; Python's default ``__hash__`` /
# ``__eq__`` works correctly. Two records with the same fields compare
# equal regardless of insertion order.


# --- Status mapping helpers -----------------------------------------------


def coerce_status(value: str | RevisionStatus) -> RevisionStatus:
    """Return a ``RevisionStatus`` enum for a ``str`` or ``RevisionStatus``
    input. Raises ``ValueError`` on unknown values (Section 12.1 invalid
    status enum value)."""
    if isinstance(value, RevisionStatus):
        return value
    try:
        return RevisionStatus(value)
    except ValueError as err:
        raise ValueError(
            f"unknown RevisionStatus {value!r}; must be one of {[s.value for s in RevisionStatus]}"
        ) from err


def coerce_audit_event_type(value: str | AuditEventType) -> AuditEventType:
    """Return an ``AuditEventType`` enum for a ``str`` or ``AuditEventType``
    input. Raises ``ValueError`` on unknown values (Section 12.1)."""
    if isinstance(value, AuditEventType):
        return value
    try:
        return AuditEventType(value)
    except ValueError as err:
        raise ValueError(
            f"unknown AuditEventType {value!r}; must be one of {[e.value for e in AuditEventType]}"
        ) from err


# --- Append-only transition helpers ---------------------------------------


def transition_revision(
    revision: CaseRevision,
    *,
    new_status: RevisionStatus,
    superseded_by: str | None = None,
    archived_at: datetime | None = None,
    tombstone_at: datetime | None = None,
) -> CaseRevision:
    """Return a new ``CaseRevision`` transitioned to ``new_status``.

    Section 7.2 — raises ``ValueError`` (caller decides whether to map
    to ``RevisionPersistenceFailure``) on a forbidden transition.
    ``Section 6.5`` — payload / identity / hashes remain unchanged; only
    status and metadata-transition fields are updated.
    """
    if not is_allowed_transition(revision.status, new_status):
        raise ValueError(
            f"forbidden transition {revision.status.value} -> {new_status.value} (Section 7.3)"
        )
    return replace(
        revision,
        status=new_status,
        superseded_by=superseded_by,
        archived_at=archived_at,
        tombstone_at=tombstone_at,
    )


__all__ = [
    "ALLOWED_TRANSITIONS",
    "AuditEventType",
    "Case",
    "CaseRevision",
    "CaseRevisionAuditEvent",
    "IdempotencyKeyRecord",
    "ParentChainLink",
    "RevisionStatus",
    "build_parent_chain_links",
    "coerce_audit_event_type",
    "coerce_status",
    "is_allowed_transition",
    "transition_revision",
]
