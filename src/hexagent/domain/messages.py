from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ---------------------------------------------------------------------------
# Error codes (stable string enum)
# ---------------------------------------------------------------------------


class ErrorCode(StrEnum):
    """Stable error-code constants used across the engineering kernel.

    Uses StrEnum so that ``code == "input_missing"`` works while also
    being serialisable and type-safe.  The ``EXTENSION_PREFIX`` sentinel
    allows user-defined codes with the format ``"x_<vendor>_<name>"``.
    """

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
    BLOCKER = "blocker"

    @classmethod
    def is_valid_code(cls, code: str) -> bool:
        """Return True if *code* is a known constant or a valid extension."""
        try:
            cls(code)
            return True
        except ValueError:
            return _is_valid_extension_code(code)


def _is_valid_extension_code(code: str) -> bool:
    """Extension codes must start with ``x_`` and have at least one vendor segment."""
    if not code.startswith("x_"):
        return False
    parts = code.split("_")
    return len(parts) >= 3  # x_<vendor>_<name>


# ---------------------------------------------------------------------------
# Severity
# ---------------------------------------------------------------------------


class EngineeringMessageSeverity(StrEnum):
    """Severity levels for engineering messages.

    Continuation semantics:
    - ``INFO``, ``WARNING``: calculation may continue.
    - ``ERROR``, ``BLOCKER``: calculation must stop.
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    BLOCKER = "blocker"


# ---------------------------------------------------------------------------
# EngineeringMessage
# ---------------------------------------------------------------------------


class EngineeringMessage(BaseModel):
    """Structured engineering message (warning, error, blocker, etc.).

    The ``allows_continuation`` field is derived from ``severity`` by
    the model validator — callers should not set it explicitly.
    ``context`` uses tuple-of-tuples for deep immutability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    code: ErrorCode
    severity: EngineeringMessageSeverity
    message: str = Field(min_length=1)
    source_module: str = Field(default="", min_length=0)
    affected_paths: tuple[str, ...] = Field(default_factory=tuple)
    context: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)
    allows_continuation: bool = False

    @model_validator(mode="before")
    @classmethod
    def _derive_continuation(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Set ``allows_continuation`` from severity before construction."""
        severity = data.get("severity")
        if severity:
            continuation_map = {
                "info": True,
                "warning": True,
                "error": False,
                "blocker": False,
            }
            data["allows_continuation"] = continuation_map.get(severity, False)
        return data

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
    """Structured failure record attached to a :class:`CalculationRun`.

    ``context`` uses tuple-of-tuples for deep immutability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    code: ErrorCode
    message: str = Field(min_length=1)
    traceback: str | None = None
    context: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)

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
