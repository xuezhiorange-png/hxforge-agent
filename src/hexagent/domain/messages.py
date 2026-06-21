from __future__ import annotations

from enum import StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Error codes (stable string constants)
# ---------------------------------------------------------------------------


class ErrorCode:
    """Stable error-code constants used across the engineering kernel."""

    INPUT_MISSING = "input_missing"
    INPUT_INCONSISTENT = "input_inconsistent"
    UNIT_INVALID = "unit_invalid"
    PROPERTY_UNAVAILABLE = "property_unavailable"
    PROPERTY_OUT_OF_RANGE = "property_out_of_range"
    CALCULATION_NOT_CONVERGED = "calculation_not_converged"
    CALCULATION_BLOCKED = "calculation_blocked"
    UNSUPPORTED_SERVICE = "unsupported_service"
    NOT_IMPLEMENTED = "not_implemented"
    PROVENANCE_INCOMPLETE = "provenance_incomplete"
    HASH_MISMATCH = "hash_mismatch"
    INVALID_STATE_TRANSITION = "invalid_state_transition"


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------


class EngineeringMessageSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# EngineeringMessage
# ---------------------------------------------------------------------------


class EngineeringMessage(BaseModel):
    """Structured engineering message (warning, error, etc.)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    code: str = Field(min_length=1)
    severity: EngineeringMessageSeverity
    message: str = Field(min_length=1)
    source_module: str = Field(default="", min_length=0)
    affected_paths: tuple[str, ...] = Field(default_factory=tuple)
    context: dict[str, Any] = Field(default_factory=dict)
    allows_continuation: bool = False

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


# ---------------------------------------------------------------------------
# RunFailure
# ---------------------------------------------------------------------------


class RunFailure(BaseModel):
    """Structured failure record attached to a :class:`CalculationRun`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    traceback: str | None = None
    context: dict[str, Any] = Field(default_factory=dict)

    # --- serialisation helpers ---

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, data: str) -> Self:
        return cls.model_validate_json(data)


__all__ = [
    "EngineeringMessage",
    "EngineeringMessageSeverity",
    "ErrorCode",
    "RunFailure",
]
