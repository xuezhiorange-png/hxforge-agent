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
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from hexagent.core.canonical import canonical_json, sha256_digest
from hexagent.core.immutability import deep_freeze
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
    current: CalculationRunStatus,
    target: CalculationRunStatus,
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
        # Deep-freeze canonical_payload to prevent post-construction mutation
        object.__setattr__(self, "canonical_payload", deep_freeze(self.canonical_payload))

        # revision_number >= 1
        if self.revision_number < 1:
            raise ValueError(f"revision_number must be >= 1, got {self.revision_number}")

        # First revision must not have a parent
        if self.revision_number == 1 and self.parent_revision_id is not None:
            raise ValueError("First revision (revision_number=1) must have parent_revision_id=None")

        # Subsequent revisions must have a parent
        if self.revision_number > 1 and self.parent_revision_id is None:
            raise ValueError(f"Revision {self.revision_number} must have a parent_revision_id")

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

    def __deepcopy__(self, memo: dict[int, Any]) -> DesignCaseRevision:
        """Deep copy that handles deep-frozen canonical_payload (mappingproxy).

        ``copy.deepcopy`` cannot pickle ``types.MappingProxyType`` objects
        produced by :func:`~hexagent.core.immutability.deep_freeze`.  This
        method bypasses the default pickling-based deepcopy by reconstructing
        the frozen dataclass from its already-immutable field values.
        """
        return DesignCaseRevision(
            revision_id=self.revision_id,
            case_id=self.case_id,
            revision_number=self.revision_number,
            design_case=self.design_case,
            canonical_payload=self.canonical_payload,  # already deep-frozen
            content_hash=self.content_hash,
            created_at=self.created_at,
            created_by=self.created_by,
            schema_version=self.schema_version,
            parent_revision_id=self.parent_revision_id,
            change_summary=self.change_summary,
            changed_fields=self.changed_fields,
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
                str(self.parent_revision_id) if self.parent_revision_id is not None else None
            ),
            "design_case": self.design_case.model_dump(),
            "canonical_payload": self.canonical_payload,
            "content_hash": self.content_hash,
            "created_at": self.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
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
            created_at=datetime.fromisoformat(data["created_at"]).astimezone(UTC),
            created_by=data["created_by"],
            schema_version=data.get("schema_version", _SCHEMA_VERSION),
            parent_revision_id=(
                UUID(data["parent_revision_id"]) if data.get("parent_revision_id") else None
            ),
            change_summary=data.get("change_summary", ""),
            changed_fields=tuple(data.get("changed_fields", [])),
        )

    @classmethod
    def from_json(cls, data: str) -> Self:
        parsed = json.loads(data)
        return cls.from_dict(parsed)


# ---------------------------------------------------------------------------
# FieldChange — immutable diff entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FieldChange:
    """A single field-level change between two revisions.

    Immutable: ``path``, ``before`` and ``after`` cannot be reassigned
    after construction.  ``before`` and ``after`` are recursively frozen
    during construction so that nested containers are also immutable.
    """

    path: str = field()
    before: Any = field()
    after: Any = field()

    def __post_init__(self) -> None:
        object.__setattr__(self, "before", deep_freeze(self.before))
        object.__setattr__(self, "after", deep_freeze(self.after))


# ---------------------------------------------------------------------------
# RevisionDiff — lightweight comparison between two revisions
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RevisionDiff:
    """Record of what changed between two consecutive revisions.

    ``field_changes`` contains recursive, path-level diffs with
    before/after values, sorted by path.  Each entry is a dict with
    keys ``path``, ``before`` and ``after``.
    """

    from_revision_id: UUID = field()
    to_revision_id: UUID = field()
    content_hash_before: str = field()
    content_hash_after: str = field()
    field_changes: tuple[FieldChange, ...] = field(default_factory=tuple)

    @property
    def is_identical(self) -> bool:
        return self.content_hash_before == self.content_hash_after

    @property
    def changed_paths(self) -> tuple[str, ...]:
        """Sorted tuple of dotted paths that changed."""
        return tuple(c.path for c in self.field_changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_revision_id": str(self.from_revision_id),
            "to_revision_id": str(self.to_revision_id),
            "field_changes": [
                {"path": c.path, "before": c.before, "after": c.after} for c in self.field_changes
            ],
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
            field_changes=tuple(
                FieldChange(path=c["path"], before=c["before"], after=c["after"])
                for c in data.get("field_changes", [])
            ),
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
    """Immutable record of an engineering calculation execution.

    Model validators enforce status-dependent invariants:
    - ``SUCCEEDED`` requires a valid ``result_hash`` and no ``failure``.
    - ``FAILED`` requires a ``failure`` and no valid ``result_hash``.
    - ``BLOCKED`` requires at least one ``blocker``.
    - Terminal states require ``completed_at > started_at``.
    - Non-terminal states must not have ``completed_at``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    run_id: UUID
    case_id: UUID
    case_revision_id: UUID
    run_type: CalculationRunType
    status: CalculationRunStatus
    started_at: datetime
    completed_at: datetime | None = None
    software_version: str = Field(default="0.1.0")
    git_commit: str = Field(default="no-git")
    input_hash: str
    result_hash: str | None = None
    property_backend: dict[str, Any] | None = None
    correlation_records: tuple[dict[str, Any], ...] = Field(default_factory=tuple)
    warnings: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    blockers: tuple[EngineeringMessage, ...] = Field(default_factory=tuple)
    failure: RunFailure | None = None
    provenance_graph: ProvenanceGraph = Field(
        default_factory=lambda: ProvenanceGraph(nodes=(), edges=())
    )

    @field_validator("git_commit")
    @classmethod
    def _validate_git_commit(cls, v: str) -> str:
        """Validate git_commit is a 7–40 hex SHA or exactly 'no-git'.

        ``no-git`` is the approved sentinel for runs created outside a
        git-tracked context (e.g. scripted batch runs, API-only usage).
        """
        if v == "no-git":
            return v
        if not re.fullmatch(r"[0-9a-fA-F]{7,40}", v):
            raise ValueError(
                f"git_commit must be a 7–40 character hex SHA or exactly 'no-git', got {v!r}"
            )
        return v.lower()

    @model_validator(mode="after")
    def _validate_terminal_invariants(self) -> Self:
        # input_hash must be a valid sha256 hash
        if not _is_valid_run_hash(self.input_hash):
            raise ValueError(f"input_hash must be sha256:<64-hex>, got {self.input_hash!r}")

        status = self.status

        # SUCCEEDED: must have a valid result_hash
        if status == CalculationRunStatus.SUCCEEDED:
            if not self.result_hash or not _is_valid_run_hash(self.result_hash):
                raise ValueError(
                    f"SUCCEEDED run must have a valid result_hash (got {self.result_hash!r})"
                )
            if self.failure is not None:
                raise ValueError("SUCCEEDED run must not have a failure record")

        # FAILED: must have a failure record
        if status == CalculationRunStatus.FAILED and self.failure is None:
            raise ValueError("FAILED run must have a failure record")

        # BLOCKED: must have at least one blocker
        if status == CalculationRunStatus.BLOCKED and not self.blockers:
            raise ValueError("BLOCKED run must have at least one blocker")

        # Terminal states must have completed_at
        if status in (
            CalculationRunStatus.SUCCEEDED,
            CalculationRunStatus.FAILED,
            CalculationRunStatus.BLOCKED,
            CalculationRunStatus.CANCELLED,
        ):
            if self.completed_at is None:
                raise ValueError(f"Terminal status {status.value} requires completed_at")
            if self.completed_at <= self.started_at:
                raise ValueError(
                    f"completed_at ({self.completed_at}) must be after "
                    f"started_at ({self.started_at})"
                )

        # Non-terminal: must NOT have completed_at
        non_terminal = status in (CalculationRunStatus.PENDING, CalculationRunStatus.RUNNING)
        if non_terminal and self.completed_at is not None:
            raise ValueError(f"Non-terminal status {status.value} must not have completed_at")

        return self

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


def _is_valid_run_hash(h: str) -> bool:
    """Return True if *h* matches ``sha256:<64-hex>``."""
    if not h.startswith("sha256:"):
        return False
    hex_part = h[7:]
    if len(hex_part) != 64:
        return False
    try:
        int(hex_part, 16)
        return True
    except ValueError:
        return False


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
        super().__init__(f"Revision number {revision_number} already exists for case {case_id}")
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
        super().__init__(f"Invalid state transition: {from_state} -> {to_state}")
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
    "FieldChange",
    "RevisionDiff",
    "DuplicateIdError",
    "RevisionNumberConflictError",
    "MissingParentError",
    "RevisionOverwriteError",
    "InvalidStateTransitionError",
    "IntegrityError",
]
