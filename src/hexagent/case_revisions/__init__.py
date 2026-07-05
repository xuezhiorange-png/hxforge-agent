"""TASK-014 immutable case revisions and persistence runtime.

Implements the frozen TASK-014 design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Public API
----------

Errors (Section 16 — structured error model):

* :class:`Task014Error` — common base.
* :class:`CaseRevisionConflict` — concurrency conflict (NOT stale-parent).
* :class:`StaleParentRevision` — expected_parent_revision_id mismatch.
* :class:`InvalidRevisionPayload` — structural validation failure.
* :class:`RevisionHashMismatch` — payload_hash / domain_snapshot_hash /
  parent_chain_hash mismatch.
* :class:`MissingRevisionAuthority` — upstream authority resolution
  failure.
* :class:`RevisionPersistenceFailure` — repository failure (with
  ``partial_state=False`` always).
* :class:`RestrictedContentViolation` — restricted-source content
  detected.

Domain models (Section 5):

* :class:`Case`, :class:`CaseRevision`, :class:`CaseRevisionAuditEvent`,
  :class:`ParentChainLink`, :class:`IdempotencyKeyRecord`.
* :class:`RevisionStatus`, :class:`AuditEventType` enums.
* :func:`is_allowed_transition`, :func:`transition_revision`,
  :func:`build_parent_chain_links`.

Canonicalization (Section 11):

* :func:`compute_payload_hash`, :func:`compute_domain_snapshot_hash`,
  :func:`compute_parent_chain_hash`.

Persistence (Section 9 + 13):

* :class:`InMemoryCaseRevisionRepository` — in-memory repository
  implementing atomic commit, idempotency dedup, expected-parent /
  token / concurrent-sibling concurrency control.

Validation (Section 12):

* :func:`validate_revision`, :func:`validate_revision_or_raise`,
  :func:`assert_revision_authority_resolves`,
* :class:`ValidationResult`, :class:`ValidationIssue`.

Restricted content (Section 12.4 + 15):

* :func:`scan_payload_for_restricted_content`.

Lifecycle (Section 7):

* :func:`transition_with_audit`, :func:`audit_event_for_draft_creation`,
  :func:`ensure_status_valid`, :func:`assert_transition_allowed`.

Audit (Section 14):

* :func:`emit_revision_created`, :func:`emit_transition`,
  :func:`assert_audit_event_complete`.

Optimistic concurrency (Section 13.2):

* :func:`mint_optimistic_concurrency_token`,
  :func:`assert_token_matches`.

Idempotency (Section 13.3):

* :func:`assert_idempotency_dedup_match`.
"""

from __future__ import annotations

from hexagent.case_revisions.audit import (
    AuditEventType,
    assert_audit_event_complete,
    emit_revision_created,
    emit_transition,
)
from hexagent.case_revisions.canonical import (
    ALL_VOLATILE_FIELDS,
    DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS,
    PAYLOAD_HASH_EXCLUDED_FIELDS,
    compute_domain_snapshot_hash,
    compute_parent_chain_hash,
    compute_payload_hash,
    hash_field_kind,
)
from hexagent.case_revisions.errors import (
    VALID_CONFLICT_REASONS,
    VALID_HASH_FIELDS,
    VALID_MISSING_AUTHORITY_KINDS,
    VALID_VIOLATION_KINDS,
    CaseRevisionConflict,
    ConflictReason,
    HashField,
    InvalidRevisionPayload,
    MissingAuthorityKind,
    MissingRevisionAuthority,
    RestrictedContentViolation,
    RevisionHashMismatch,
    RevisionPersistenceFailure,
    StaleParentRevision,
    Task014Error,
    ViolationKind,
)
from hexagent.case_revisions.idempotency import assert_idempotency_dedup_match
from hexagent.case_revisions.lifecycle import (
    VALID_REVISION_STATUSES,
    assert_transition_allowed,
    audit_event_for_draft_creation,
    ensure_status_valid,
    transition_with_audit,
)
from hexagent.case_revisions.models import (
    ALLOWED_TRANSITIONS,
    Case,
    CaseRevision,
    CaseRevisionAuditEvent,
    IdempotencyKeyRecord,
    ParentChainLink,
    RevisionStatus,
    build_parent_chain_links,
    coerce_audit_event_type,
    coerce_status,
    is_allowed_transition,
    transition_revision,
)
from hexagent.case_revisions.models import (
    AuditEventType as _AuditEventType,
)
from hexagent.case_revisions.optimistic import (
    assert_token_matches as assert_optimistic_token_matches,
)
from hexagent.case_revisions.optimistic import (
    mint_optimistic_concurrency_token,
)
from hexagent.case_revisions.persistence import InMemoryCaseRevisionRepository
from hexagent.case_revisions.restricted import scan_payload_for_restricted_content
from hexagent.case_revisions.validation import (
    ValidationIssue,
    ValidationResult,
    assert_revision_authority_resolves,
    validate_revision,
    validate_revision_or_raise,
)

# Re-export the optimistic helper under a non-shadowing name.
assert_token_matches = assert_optimistic_token_matches

__all__ = [
    # Errors
    "CaseRevisionConflict",
    "ConflictReason",
    "HashField",
    "InvalidRevisionPayload",
    "MissingAuthorityKind",
    "MissingRevisionAuthority",
    "RestrictedContentViolation",
    "RevisionHashMismatch",
    "RevisionPersistenceFailure",
    "StaleParentRevision",
    "Task014Error",
    "VALID_CONFLICT_REASONS",
    "VALID_HASH_FIELDS",
    "VALID_MISSING_AUTHORITY_KINDS",
    "VALID_VIOLATION_KINDS",
    "ViolationKind",
    # Models
    "ALLOWED_TRANSITIONS",
    "AuditEventType",
    "Case",
    "CaseRevision",
    "CaseRevisionAuditEvent",
    "IdempotencyKeyRecord",
    "ParentChainLink",
    "RevisionStatus",
    "VALID_REVISION_STATUSES",
    "build_parent_chain_links",
    "coerce_audit_event_type",
    "coerce_status",
    "is_allowed_transition",
    "transition_revision",
    # Canonical
    "ALL_VOLATILE_FIELDS",
    "DOMAIN_SNAPSHOT_HASH_EXCLUDED_FIELDS",
    "PAYLOAD_HASH_EXCLUDED_FIELDS",
    "compute_domain_snapshot_hash",
    "compute_parent_chain_hash",
    "compute_payload_hash",
    "hash_field_kind",
    # Persistence
    "InMemoryCaseRevisionRepository",
    # Validation
    "ValidationIssue",
    "ValidationResult",
    "assert_revision_authority_resolves",
    "validate_revision",
    "validate_revision_or_raise",
    # Restricted content
    "scan_payload_for_restricted_content",
    # Lifecycle
    "assert_transition_allowed",
    "audit_event_for_draft_creation",
    "ensure_status_valid",
    "transition_with_audit",
    # Audit
    "assert_audit_event_complete",
    "emit_revision_created",
    "emit_transition",
    # Optimistic
    "assert_token_matches",
    "mint_optimistic_concurrency_token",
    # Idempotency
    "assert_idempotency_dedup_match",
]


# Silence "imported but unused" lint by re-exporting the model AuditEventType
# under its canonical name once (we re-export it via ``__all__`` above).
_ = _AuditEventType
