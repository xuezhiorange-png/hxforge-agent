"""Structured error model for TASK-014 immutable case revisions.

Implements the TASK-014 frozen design contract
(docs/tasks/TASK-014-immutable-case-revisions-persistence.md,
Frozen Contract Authority SHA
``6f337a6e81a8c2a7ba8059285aeef39bba59c7cb``).

Section 16 — ``Task014Error`` common base + 7 defined error classes:

* ``CaseRevisionConflict`` — ``error_code = "case_revision_conflict"``,
  ``context.conflict_reason`` ∈ ``{token_mismatch, duplicate_idempotency_key,
  concurrent_sibling}``. **Stale expected-parent is NOT represented here
  (Section 13.6) — stale parent uses ``StaleParentRevision`` exclusively.**
* ``StaleParentRevision`` — ``error_code = "stale_parent_revision"``,
  raised when ``expected_parent_revision_id`` does not equal current head
  (Section 12.5 / 13.1).
* ``InvalidRevisionPayload`` — ``error_code = "invalid_revision_payload"``,
  ``context.path`` + ``context.reason``.
* ``RevisionHashMismatch`` — ``error_code = "revision_hash_mismatch"``,
  ``context.expected_payload_hash`` / ``context.actual_payload_hash`` /
  ``context.hash_field`` ∈ ``{payload_hash, domain_snapshot_hash,
  parent_chain_hash}``.
* ``MissingRevisionAuthority`` — ``error_code = "missing_revision_authority"``,
  ``context.missing_authority`` ∈ ``{property_provider, correlation,
  material, cost, rule_pack, benchmark}``.
* ``RevisionPersistenceFailure`` — ``error_code = "revision_persistence_failure"``,
  ``context.failure_reason`` + ``context.partial_state`` (always False at
  raise time per Section 6.8).
* ``RestrictedContentViolation`` — ``error_code = "restricted_content_violation"``,
  ``context.violation_kind`` ∈ ``{standard_body, vendor_catalog_body,
  paid_price_list, restricted_property_table, scanned_page, formula_image,
  copied_standard_table}``.

All TASK-014 errors carry ``root_case_id``, ``revision_id`` (if applicable),
and a structured ``context`` dict. CI MUST NOT downgrade these errors to
warnings (Section 16 final paragraph).
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

# --- Conflict reason enum (Section 13.6) ------------------------------------

# NOTE: ``stale_parent`` is intentionally NOT a member here. A stale
# expected-parent condition MUST raise ``StaleParentRevision`` (Section 12.5
# / 13.1 / 16.2 disambiguation rule), NOT ``CaseRevisionConflict``.
ConflictReason = Literal["token_mismatch", "duplicate_idempotency_key", "concurrent_sibling"]

VALID_CONFLICT_REASONS: frozenset[str] = frozenset(
    {"token_mismatch", "duplicate_idempotency_key", "concurrent_sibling"}
)

# --- Missing authority enum (Section 16.2 MissingRevisionAuthority) -------

MissingAuthorityKind = Literal[
    "property_provider",
    "correlation",
    "material",
    "cost",
    "rule_pack",
    "benchmark",
]

VALID_MISSING_AUTHORITY_KINDS: frozenset[str] = frozenset(
    {"property_provider", "correlation", "material", "cost", "rule_pack", "benchmark"}
)

# --- Hash field enum (Section 16.2 RevisionHashMismatch) ------------------

HashField = Literal["payload_hash", "domain_snapshot_hash", "parent_chain_hash"]

VALID_HASH_FIELDS: frozenset[str] = frozenset(
    {"payload_hash", "domain_snapshot_hash", "parent_chain_hash"}
)

# --- Violation kind enum (Section 16.2 RestrictedContentViolation) --------

ViolationKind = Literal[
    "standard_body",
    "vendor_catalog_body",
    "paid_price_list",
    "restricted_property_table",
    "scanned_page",
    "formula_image",
    "copied_standard_table",
]

VALID_VIOLATION_KINDS: frozenset[str] = frozenset(
    {
        "standard_body",
        "vendor_catalog_body",
        "paid_price_list",
        "restricted_property_table",
        "scanned_page",
        "formula_image",
        "copied_standard_table",
    }
)


# --- Common base -------------------------------------------------------------


class Task014Error(Exception):
    """Base class for all TASK-014 structured errors (Section 16.1).

    Carries ``error_code``, ``root_case_id``, ``revision_id`` (when
    applicable), and a structured ``context`` dict.

    The common base is the integration point for the error-classification
    adapter: subclasses override ``error_code`` and append structured
    fields to ``context``.
    """

    error_code: ClassVar[str] = "task014_error"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.root_case_id = root_case_id
        self.revision_id = revision_id
        self.context: dict[str, Any] = dict(context) if context else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "root_case_id": self.root_case_id,
            "revision_id": self.revision_id,
            "context": dict(self.context),
        }


# --- Defined errors ----------------------------------------------------------


class CaseRevisionConflict(Task014Error):
    """Raised when a non-parent-related concurrency conflict occurs.

    Section 13.6 — ``conflict_reason`` ∈
    ``{token_mismatch, duplicate_idempotency_key, concurrent_sibling}``.

    A stale expected-parent condition is NOT represented here; it raises
    :class:`StaleParentRevision` exclusively.
    """

    error_code: ClassVar[str] = "case_revision_conflict"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        conflict_reason: str,
        expected_parent_revision_id: str | None = None,
        actual_parent_revision_id: str | None = None,
        attempted_revision_number: int | None = None,
    ) -> None:
        if conflict_reason not in VALID_CONFLICT_REASONS:
            raise ValueError(
                f"invalid conflict_reason={conflict_reason!r}; "
                f"must be one of {sorted(VALID_CONFLICT_REASONS)}; "
                "stale_parent MUST use StaleParentRevision instead"
            )
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={
                "conflict_reason": conflict_reason,
                "expected_parent_revision_id": expected_parent_revision_id,
                "actual_parent_revision_id": actual_parent_revision_id,
                "attempted_revision_number": attempted_revision_number,
            },
        )
        self.conflict_reason = conflict_reason
        self.expected_parent_revision_id = expected_parent_revision_id
        self.actual_parent_revision_id = actual_parent_revision_id
        self.attempted_revision_number = attempted_revision_number


class StaleParentRevision(Task014Error):
    """Raised when ``expected_parent_revision_id`` does not equal the
    current head revision of the same ``root_case_id``.

    Section 12.5 / 13.1 / 16.2 — MUST be treated as a hard rejection, MUST
    NOT appear in warnings, MUST NOT be represented as
    ``CaseRevisionConflict``.
    """

    error_code: ClassVar[str] = "stale_parent_revision"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        expected_parent_revision_id: str | None = None,
        actual_parent_revision_id: str | None = None,
    ) -> None:
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={
                "expected_parent_revision_id": expected_parent_revision_id,
                "actual_parent_revision_id": actual_parent_revision_id,
            },
        )
        self.expected_parent_revision_id = expected_parent_revision_id
        self.actual_parent_revision_id = actual_parent_revision_id


class InvalidRevisionPayload(Task014Error):
    """Raised when a payload fails structural validation (Section 12.1).

    ``context.path`` identifies the offending JSON path inside the payload;
    ``context.reason`` is a free-text description.
    """

    error_code: ClassVar[str] = "invalid_revision_payload"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        path: str = "",
        reason: str = "",
    ) -> None:
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={"path": path, "reason": reason},
        )
        self.path = path
        self.reason = reason


class RevisionHashMismatch(Task014Error):
    """Raised when a revision's stored hash does not match the recomputed
    canonical hash (Section 12.2).

    ``context.hash_field`` ∈ ``{payload_hash, domain_snapshot_hash,
    parent_chain_hash}``.
    """

    error_code: ClassVar[str] = "revision_hash_mismatch"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        expected_payload_hash: str | None = None,
        actual_payload_hash: str | None = None,
        hash_field: str = "payload_hash",
    ) -> None:
        if hash_field not in VALID_HASH_FIELDS:
            raise ValueError(
                f"invalid hash_field={hash_field!r}; must be one of {sorted(VALID_HASH_FIELDS)}"
            )
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={
                "expected_payload_hash": expected_payload_hash,
                "actual_payload_hash": actual_payload_hash,
                "hash_field": hash_field,
            },
        )
        self.expected_payload_hash = expected_payload_hash
        self.actual_payload_hash = actual_payload_hash
        self.hash_field = hash_field


class MissingRevisionAuthority(Task014Error):
    """Raised when a referenced upstream authority cannot be resolved
    (Section 12.3).

    ``context.missing_authority`` ∈
    ``{property_provider, correlation, material, cost, rule_pack, benchmark}``.
    """

    error_code: ClassVar[str] = "missing_revision_authority"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        missing_authority: str,
        reference: str | None = None,
    ) -> None:
        if missing_authority not in VALID_MISSING_AUTHORITY_KINDS:
            raise ValueError(
                f"invalid missing_authority={missing_authority!r}; "
                f"must be one of {sorted(VALID_MISSING_AUTHORITY_KINDS)}"
            )
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={"missing_authority": missing_authority, "reference": reference},
        )
        self.missing_authority = missing_authority
        self.reference = reference


class RevisionPersistenceFailure(Task014Error):
    """Raised when a persistence operation cannot complete cleanly.

    Per Section 6.8 / 13.4 there is NO partial commit; ``partial_state`` is
    always ``False`` at raise time. The ``partial_state`` context field is
    explicit so downstream tooling cannot mistake a clean rollback for a
    half-applied state.
    """

    error_code: ClassVar[str] = "revision_persistence_failure"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        failure_reason: str = "",
        partial_state: bool = False,
    ) -> None:
        if partial_state is True:
            raise ValueError("partial_state MUST be False at raise time (Section 6.8 / 13.4)")
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={
                "failure_reason": failure_reason,
                "partial_state": partial_state,
            },
        )
        self.failure_reason = failure_reason
        self.partial_state = partial_state


class RestrictedContentViolation(Task014Error):
    """Raised when a payload contains restricted content
    (Section 12.4 / 15).

    ``context.violation_kind`` ∈
    ``{standard_body, vendor_catalog_body, paid_price_list,
    restricted_property_table, scanned_page, formula_image,
    copied_standard_table}``.
    """

    error_code: ClassVar[str] = "restricted_content_violation"

    def __init__(
        self,
        message: str,
        *,
        root_case_id: str | None = None,
        revision_id: str | None = None,
        violation_kind: str,
        offending_excerpt: str | None = None,
        path: str = "",
    ) -> None:
        if violation_kind not in VALID_VIOLATION_KINDS:
            raise ValueError(
                f"invalid violation_kind={violation_kind!r}; "
                f"must be one of {sorted(VALID_VIOLATION_KINDS)}"
            )
        super().__init__(
            message,
            root_case_id=root_case_id,
            revision_id=revision_id,
            context={
                "violation_kind": violation_kind,
                "offending_excerpt": offending_excerpt,
                "path": path,
            },
        )
        self.violation_kind = violation_kind
        self.offending_excerpt = offending_excerpt
        self.path = path


__all__ = [
    "VALID_CONFLICT_REASONS",
    "VALID_HASH_FIELDS",
    "VALID_MISSING_AUTHORITY_KINDS",
    "VALID_VIOLATION_KINDS",
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
    "ViolationKind",
]
