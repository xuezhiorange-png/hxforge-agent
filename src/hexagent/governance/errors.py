"""Structured error model for TASK-015 governance configuration.

Implements the TASK-015 frozen design contract
(docs/tasks/TASK-015-ci-security-and-release-automation.md,
Frozen Contract Authority SHA
``39135e269b014e9c9310ac403a60591393d46b2d``).

Section 8 — ``Task015Error`` common base + 7 defined error classes:

* :class:`SpecSchemaError` — ``error_code = "spec_schema_error"``,
  ``context.spec_path`` / ``context.field_path`` / ``context.reason``
  / ``context.schema_version``.
* :class:`SpecIdentifierCollision` —
  ``error_code = "spec_identifier_collision"``,
  ``context.spec_path`` / ``context.identifier`` /
  ``context.collision_with``.
* :class:`SpecDeprecatedReference` —
  ``error_code = "spec_deprecated_reference"``,
  ``context.spec_path`` / ``context.identifier`` /
  ``context.deprecated_at``.
* :class:`SpecForwardIncompatible` —
  ``error_code = "spec_forward_incompatible"``,
  ``context.spec_path`` / ``context.schema_version`` /
  ``context.expected_schema_version``.
* :class:`FailureTaxonomyError` —
  ``error_code = "failure_taxonomy_error"``,
  ``context.spec_path`` / ``context.failure_mode`` /
  ``context.known_failure_modes``.
* :class:`RestrictedContentViolation` —
  ``error_code = "restricted_content_violation"``,
  ``context.spec_path`` / ``context.violation_kind`` /
  ``context.offending_excerpt`` / ``context.path``.
* :class:`GovernanceAuthorityError` —
  ``error_code = "governance_authority_error"``,
  ``context.spec_path`` / ``context.missing_authority``.

RestrictedContentViolation.error_code is ALWAYS
``restricted_content_violation``; CI MUST NOT downgrade it to a warning
(Section 8.1 final paragraph).

Section 8.2 disambiguation rule — a failure to find a referenced frozen
contract MUST raise :class:`GovernanceAuthorityError`; it MUST NOT be
conflated with :class:`SpecIdentifierCollision`.

All errors carry a ``spec_path`` (the file that triggered them) unless
the error originates in cross-file governance (e.g., identifier
collision between two spec files). Error context MUST be JSON-
serializable (Section 8.3).
"""

from __future__ import annotations

from typing import Any, ClassVar, Literal

# ---------------------------------------------------------------------------
# Frozen-contract authority enum (Section 8.1 GovernanceAuthorityError)
# ---------------------------------------------------------------------------

GovernedFrozenContract = Literal[
    "task_011_frozen_contract",
    "task_012_frozen_contract",
    "task_013_frozen_contract",
    "task_014_frozen_contract",
    "task_015_frozen_contract",
    "task_015a_frozen_contract",
]

GOVERNED_FROZEN_CONTRACTS: frozenset[str] = frozenset(
    {
        "task_011_frozen_contract",
        "task_012_frozen_contract",
        "task_013_frozen_contract",
        "task_014_frozen_contract",
        "task_015_frozen_contract",
        "task_015a_frozen_contract",
    }
)

# ---------------------------------------------------------------------------
# Failure taxonomy enum (Section 7 + Section 4.2.4)
# ---------------------------------------------------------------------------

FailureMode = Literal["transient", "non_transient", "manual_intervention"]

FAILURE_TAXONOMY_MODES: frozenset[str] = frozenset(
    {"transient", "non_transient", "manual_intervention"}
)

# ---------------------------------------------------------------------------
# Violation kind enum (Section 8.1 RestrictedContentViolation)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Common base
# ---------------------------------------------------------------------------


class Task015Error(Exception):
    """Base class for all TASK-015 structured errors (Section 8.1).

    Carries ``error_code``, ``spec_path`` (unless cross-file governance),
    and a structured ``context`` dict. The common base is the integration
    point for the error-classification adapter: subclasses override
    ``error_code`` and append structured fields to ``context``.
    """

    error_code: ClassVar[str] = "task015_error"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.spec_path = spec_path
        self.context: dict[str, Any] = dict(context) if context else {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "spec_path": self.spec_path,
            "context": dict(self.context),
        }


# ---------------------------------------------------------------------------
# Defined errors
# ---------------------------------------------------------------------------


class SpecSchemaError(Task015Error):
    """Raised when a spec file fails schema validation (Section 8.1).

    ``context.spec_path`` / ``context.field_path`` /
    ``context.reason`` / ``context.schema_version``.
    """

    error_code: ClassVar[str] = "spec_schema_error"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str,
        field_path: str,
        reason: str,
        schema_version: int | None = None,
    ) -> None:
        super().__init__(
            message,
            spec_path=spec_path,
            context={
                "field_path": field_path,
                "reason": reason,
                "schema_version": schema_version,
            },
        )
        self.field_path = field_path
        self.reason = reason
        self.schema_version = schema_version


class SpecIdentifierCollision(Task015Error):
    """Raised when two specs declare the same identifier (Section 8.1).

    ``context.spec_path`` / ``context.identifier`` /
    ``context.collision_with``. Per Section 8.2 this is distinct from
    :class:`GovernanceAuthorityError`: a collision is a duplicate
    identifier; a missing authority is a referenced frozen contract
    that has not been established yet.
    """

    error_code: ClassVar[str] = "spec_identifier_collision"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str | None,
        identifier: str,
        collision_with: str,
    ) -> None:
        super().__init__(
            message,
            spec_path=spec_path,
            context={"identifier": identifier, "collision_with": collision_with},
        )
        self.identifier = identifier
        self.collision_with = collision_with


class SpecDeprecatedReference(Task015Error):
    """Raised when a spec references a deprecated identifier
    (Section 8.1). Surfaces as a warning per Section 11.1 item 7
    (NOT a blocker).

    ``context.spec_path`` / ``context.identifier`` /
    ``context.deprecated_at``.
    """

    error_code: ClassVar[str] = "spec_deprecated_reference"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str,
        identifier: str,
        deprecated_at: str | None = None,
    ) -> None:
        super().__init__(
            message,
            spec_path=spec_path,
            context={"identifier": identifier, "deprecated_at": deprecated_at},
        )
        self.identifier = identifier
        self.deprecated_at = deprecated_at


class SpecForwardIncompatible(Task015Error):
    """Raised when a spec's schema_version is ahead of the validator's
    supported version (Section 8.1 + Section 11.2 item 11).

    Surfaces as a BLOCKER per Section 11.2 item 11.

    ``context.spec_path`` / ``context.schema_version`` /
    ``context.expected_schema_version``.
    """

    error_code: ClassVar[str] = "spec_forward_incompatible"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str,
        schema_version: int,
        expected_schema_version: int,
    ) -> None:
        super().__init__(
            message,
            spec_path=spec_path,
            context={
                "schema_version": schema_version,
                "expected_schema_version": expected_schema_version,
            },
        )
        self.schema_version = schema_version
        self.expected_schema_version = expected_schema_version


class FailureTaxonomyError(Task015Error):
    """Raised when a spec references an unknown failure mode
    (Section 8.1 + Section 11.1 item 4).

    ``context.spec_path`` / ``context.failure_mode`` /
    ``context.known_failure_modes``.
    """

    error_code: ClassVar[str] = "failure_taxonomy_error"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str,
        failure_mode: str,
        known_failure_modes: frozenset[str],
    ) -> None:
        super().__init__(
            message,
            spec_path=spec_path,
            context={
                "failure_mode": failure_mode,
                "known_failure_modes": sorted(known_failure_modes),
            },
        )
        self.failure_mode = failure_mode
        self.known_failure_modes = known_failure_modes


class RestrictedContentViolation(Task015Error):
    """Raised when a spec contains restricted-source content
    (Section 8.1 + Section 10).

    ``error_code`` is ALWAYS ``restricted_content_violation``; CI MUST
    NOT downgrade to a warning (Section 8.1 final paragraph).

    ``context.spec_path`` / ``context.violation_kind`` /
    ``context.offending_excerpt`` / ``context.path``.
    """

    error_code: ClassVar[str] = "restricted_content_violation"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str,
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
            spec_path=spec_path,
            context={
                "violation_kind": violation_kind,
                "offending_excerpt": offending_excerpt,
                "path": path,
            },
        )
        self.violation_kind = violation_kind
        self.offending_excerpt = offending_excerpt
        self.path = path


class GovernanceAuthorityError(Task015Error):
    """Raised when a spec attempts to reference a frozen contract that
    is not yet established (Section 8.1 + Section 8.2).

    Per Section 8.2 this is distinct from
    :class:`SpecIdentifierCollision`: a missing authority is a referenced
    frozen contract that has not been established yet, not a duplicate
    identifier.

    ``context.missing_authority`` ∈
    ``{task_011_frozen_contract, task_012_frozen_contract,
    task_013_frozen_contract, task_014_frozen_contract,
    task_015_frozen_contract, task_015a_frozen_contract}``.
    """

    error_code: ClassVar[str] = "governance_authority_error"

    def __init__(
        self,
        message: str,
        *,
        spec_path: str | None,
        missing_authority: str,
        reference: str | None = None,
    ) -> None:
        if missing_authority not in GOVERNED_FROZEN_CONTRACTS:
            raise ValueError(
                f"invalid missing_authority={missing_authority!r}; "
                f"must be one of {sorted(GOVERNED_FROZEN_CONTRACTS)}"
            )
        super().__init__(
            message,
            spec_path=spec_path,
            context={"missing_authority": missing_authority, "reference": reference},
        )
        self.missing_authority = missing_authority
        self.reference = reference


__all__ = [
    "FAILURE_TAXONOMY_MODES",
    "GOVERNED_FROZEN_CONTRACTS",
    "VALID_VIOLATION_KINDS",
    "FailureMode",
    "FailureTaxonomyError",
    "GovernanceAuthorityError",
    "GovernedFrozenContract",
    "RestrictedContentViolation",
    "SpecDeprecatedReference",
    "SpecForwardIncompatible",
    "SpecIdentifierCollision",
    "SpecSchemaError",
    "Task015Error",
    "ViolationKind",
]
