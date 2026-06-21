"""Design case revisions, calculation runs, and revision diffs.

DesignCaseRevision
    Immutable snapshot of a :class:`~hexagent.domain.models.DesignCase`.
    Content-addressed by SHA-256 hash of its canonical JSON payload.

CalculationRun
    Record of a calculation execution against a specific revision.
    States: PENDING -> RUNNING -> SUCCEEDED / FAILED / BLOCKED / CANCELLED.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hexagent.core.canonical import canonical_json, sha256_digest
from hexagent.domain.messages import EngineeringMessage, RunFailure
from hexagent.domain.models import DesignCase
from hexagent.domain.provenance import ProvenanceGraph

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CalculationRunStatus(StrEnum):
    """State machine for calculation runs."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"
    CANCELLED = "CANCELLED"


class CalculationRunType(StrEnum):
    """Types of calculation runs."""

    VALIDATE = "VALIDATE"
    PROPERTIES = "PROPERTIES"
    SCREEN = "SCREEN"
    SIZE = "SIZE"
    RATE = "RATE"
    OPTIMIZE = "OPTIMIZE"
    REPORT = "REPORT"


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: dict[CalculationRunStatus, set[CalculationRunStatus]] = {
    CalculationRunStatus.PENDING: {
        CalculationRunStatus.RUNNING,
        CalculationRunStatus.CANCELLED,
    },
    CalculationRunStatus.RUNNING: {
        CalculationRunStatus.SUCCEEDED,
        CalculationRunStatus.FAILED,
        CalculationRunStatus.BLOCKED,
        CalculationRunStatus.CANCELLED,
    },
}


def is_valid_transition(
    current: CalculationRunStatus, target: CalculationRunStatus,
) -> bool:
    """Return True if *current* → *target* is a legal state transition."""
    allowed = _VALID_TRANSITIONS.get(current, set())
    return target in allowed


# ---------------------------------------------------------------------------
# DesignCaseRevision — frozen dataclass
# ---------------------------------------------------------------------------

_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class DesignCaseRevision:
    """Immutable snapshot of a :class:`DesignCase` at a point in time.

    The first revision in a chain has ``parent_revision_id=None``;
    subsequent revisions must reference their immediate predecessor.

    ``case_id`` must remain constant across the entire revision chain.
    """

    # Required fields (no defaults) — must come first
    revision_id: UUID = field()
    case_id: UUID = field()
    revision_number: int = field()
    design_case: DesignCase = field()
    canonical_payload: dict[str, Any] = field()
    content_hash: str = field()
    created_at: datetime = field()
    created_by: str = field()
    # Optional fields (with defaults) — must come last
    schema_version: str = field(default=_SCHEMA_VERSION)
    parent_revision_id: UUID | None = field(default=None)
    change_summary: str = field(default="")
    changed_fields: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        # revision_number >= 1
        if self.revision_number < 1:
            raise ValueError(
                f"revision_number must be >= 1, got {self.revision_number}"
            )

        # First revision must not have a parent
        if self.revision_number == 1 and self.parent_revision_id is not None:
            raise ValueError(
                "First revision (revision_number=1) must have parent_revision_id=None"
            )

        # Subsequent revisions must have a parent
        if self.revision_number > 1 and self.parent_revision_id is None:
            raise ValueError(
                f"Revision {self.revision_number} must have a parent_revision_id"
            )

        # created_at must be UTC
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware (use UTC)")

        # created_by must not be empty
        if not self.created_by:
            raise ValueError("created_by must not be empty")

        # Verify content_hash matches canonical payload
        expected_hash = sha256_digest(self.canonical_payload)
        if self.content_hash != expected_hash:
            raise ValueError(
                f"content_hash mismatch: expected {expected_hash}, got {self.content_hash}"
            )

    # --- serialisation helpers ---

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict."""
        return {
            "schema_version": self.schema_version,
            "revision_id": str(self.revision_id),
            "case_id": str(self.case_id),
            "revision_number": self.revision_number,
            "parent_revision_id": (
                str(self.parent_revision_id)
                if self.parent_revision_id is not None
                else None
            ),
            "design_case": self.design_case.model_dump(),
            "canonical_payload": self.canonical_payload,
            "content_hash": self.content_hash,
            "created_at": self.created_at.astimezone(UTC).strftime(
                "%Y-%m-%dT%H:%M:%S.%fZ"
            ),
            "created_by": self.created_by,
            "change_summary": self.change_summary,
            "changed_fields": list(self.changed_fields),
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        """Deserialise from a dict, re-parsing nested models."""
        return cls(
            revision_id=UUID(data["revision_id"]),
            case_id=UUID(data["case_id"]),
            revision_number=int(data["revision_number"]),
            design_case=DesignCase.model_validate(data["design_case"]),
            canonical_payload=data["canonical_payload"],
            content_hash=data["content_hash"],
            created_at=datetime.fromisoformat(data["created_at"]).astimezone(
                UTC
            ),
            created_by=data["created_by"],
            schema_version=data.get("schema_version", _SCHEMA_VERSION),
            parent_revision_id=(
                UUID(data["parent_revision_id"])
                if data.get("parent_revision_id")
                else None
            ),
            change_summary=data.get("change_summary", ""),
            changed_fields=tuple(data.get("changed_fields", [])),
        )

    @classmethod
    def from_json(cls, data: str) -> Self:
        parsed = json.loads(data)
        return cls.from_dict(parsed)


# ---------------------------------------------------------------------------
# RevisionDiff — lightweight comparison between two revisions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RevisionDiff:
    """Record of what changed between two consecutive revisions."""

    from_revision_id: UUID = field()
    to_revision_id: UUID = field()
    changed_fields: tuple[str, ...] = field()
    content_hash_before: str = field()
    content_hash_after: str = field()

    @property
    def is_identical(self) -> bool:
        return self.content_hash_before == self.content_hash_after

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_revision_id": str(self.from_revision_id),
            "to_revision_id": str(self.to_revision_id),
            "changed_fields": list(self.changed_fields),
            "content_hash_before": self.content_hash_before,
            "content_hash_after": self.content_hash_after,
        }

    def to_json(self) -> str:
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Self:
        return cls(
            from_revision_id=UUID(data["from_revision_id"]),
            to_revision_id=UUID(data["to_revision_id"]),
            changed_fields=tuple(data["changed_fields"]),
            content_hash_before=data["content_hash_before"],
            content_hash_after=data["content_hash_after"],
        )

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.from_dict(json.loads(data))


# ---------------------------------------------------------------------------
# CalculationRun — frozen Pydantic model
# ---------------------------------------------------------------------------


class CalculationRun(BaseModel):
    """Immutable record of an engineering calculation execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    run_id: UUID
    case_id: UUID
    case_revision_id: UUID
    run_type: CalculationRunType
    status: CalculationRunStatus
    started_at: datetime
    completed_at: datetime | None = None
    software_version: str = Field(default="0.1.0")
    git_commit: str = Field(default="")
    input_hash: str = Field(default="sha256:" + "0" * 64)
    result_hash: str = Field(default="sha256:" + "0" * 64)
    property_backend: dict[str, Any] | None = None
    correlation_records: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    warnings: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    blockers: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    failure: RunFailure | None = None
    provenance_graph: ProvenanceGraph = Field(
        default_factory=lambda: ProvenanceGraph(nodes=[], edges=[])
    )

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# Repository errors
# ---------------------------------------------------------------------------


class DuplicateIdError(ValueError):
    """Raised when attempting to add an entity with a duplicate ID."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        super().__init__(f"Duplicate {entity_type} ID: {entity_id}")
        self.entity_type = entity_type
        self.entity_id = entity_id


class RevisionNumberConflictError(ValueError):
    """Raised when a revision number already exists for a case."""

    def __init__(self, case_id: UUID, revision_number: int) -> None:
        super().__init__(
            f"Revision number {revision_number} already exists "
            f"for case {case_id}"
        )
        self.case_id = case_id
        self.revision_number = revision_number


class MissingParentError(ValueError):
    """Raised when a parent revision does not exist."""

    def __init__(self, parent_id: str) -> None:
        super().__init__(f"Parent revision not found: {parent_id}")
        self.parent_id = parent_id


class RevisionOverwriteError(ValueError):
    """Raised when attempting to overwrite an existing revision."""

    def __init__(self, revision_id: UUID) -> None:
        super().__init__(f"Cannot overwrite existing revision: {revision_id}")
        self.revision_id = revision_id


class InvalidStateTransitionError(ValueError):
    """Raised when a run state transition is not allowed."""

    def __init__(self, from_state: str, to_state: str) -> None:
        super().__init__(
            f"Invalid state transition: {from_state} -> {to_state}"
        )
        self.from_state = from_state
        self.to_state = to_state


class IntegrityError(ValueError):
    """Raised when an integrity check fails."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


__all__ = [
    "CalculationRun",
    "CalculationRunStatus",
    "CalculationRunType",
    "DesignCaseRevision",
    "RevisionDiff",
    "DuplicateIdError",
    "RevisionNumberConflictError",
    "MissingParentError",
    "RevisionOverwriteError",
    "InvalidStateTransitionError",
    "IntegrityError",
]
