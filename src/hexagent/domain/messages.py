from __future__ import annotations

import types
from enum import StrEnum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _freeze_context_val(val: Any) -> Any:
    """Recursively freeze a context value (used inside model_validator)."""
    if isinstance(val, dict):
        return types.MappingProxyType({k: _freeze_context_val(v) for k, v in val.items()})
    if isinstance(val, list):
        return tuple(_freeze_context_val(item) for item in val)
    if isinstance(val, (set, frozenset)):
        return tuple(
            sorted(
                (_freeze_context_val(item) for item in val),
                key=lambda x: repr(x),
            )
        )
    if isinstance(val, tuple):
        return tuple(_freeze_context_val(item) for item in val)
    return val


def _freeze_context_tuples(data: dict[str, Any], key: str) -> dict[str, Any]:
    """Freeze nested values in a tuple-of-tuples ``context`` field."""
    if key not in data:
        return data
    raw = data[key]
    frozen_pairs: list[tuple[str, Any]] = []
    for pair in raw:
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            key_val: tuple[Any, Any] = tuple(pair)
            frozen_val = _freeze_context_val(key_val[1])
            frozen_pairs.append((str(key_val[0]), frozen_val))
        else:
            frozen_pairs.append(pair)
    data[key] = tuple((k, v) for k, v in frozen_pairs)
    return data


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

    # Correlation-specific error codes
    CORRELATION_NOT_FOUND = "correlation_not_found"
    CORRELATION_VERSION_NOT_FOUND = "correlation_version_not_found"
    CORRELATION_DUPLICATE = "correlation_duplicate"
    CORRELATION_DEPRECATED = "correlation_deprecated"
    CORRELATION_WITHDRAWN = "correlation_withdrawn"
    CORRELATION_GEOMETRY_INCOMPATIBLE = "correlation_geometry_incompatible"
    CORRELATION_PHASE_INCOMPATIBLE = "correlation_phase_incompatible"
    CORRELATION_FLOW_REGIME_INCOMPATIBLE = "correlation_flow_regime_incompatible"
    CORRELATION_INPUT_MISSING = "correlation_input_missing"
    CORRELATION_RECOMMENDED_RANGE_EXCEEDED = "correlation_recommended_range_exceeded"
    CORRELATION_ABSOLUTE_RANGE_EXCEEDED = "correlation_absolute_range_exceeded"
    CORRELATION_EXTRAPOLATION_USED = "correlation_extrapolation_used"
    CORRELATION_SOURCE_UNVERIFIED = "correlation_source_unverified"
    CORRELATION_IMPLEMENTATION_UNAVAILABLE = "correlation_implementation_unavailable"

    # Double-pipe rating error codes
    INVALID_DOUBLE_PIPE_GEOMETRY = "invalid_double_pipe_geometry"
    INVALID_FLOW_SIDE_ASSIGNMENT = "invalid_flow_side_assignment"
    NON_POSITIVE_MASS_FLOW = "non_positive_mass_flow"
    PROPERTY_EVALUATION_FAILED = "property_evaluation_failed"
    PHASE_NOT_SUPPORTED = "phase_not_supported"
    TEMPERATURE_CROSSING = "temperature_crossing"
    INVALID_LMTD = "invalid_lmtd"
    SOLVER_BRACKET_NOT_FOUND = "solver_bracket_not_found"
    SOLVER_NON_CONVERGENCE = "solver_non_convergence"
    ENERGY_BALANCE_NOT_CLOSED = "energy_balance_not_closed"

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
    ``context`` uses tuple-of-tuples with recursively frozen values
    for deep immutability.
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
    def _freeze_context_and_derive(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Freeze context values and set ``allows_continuation`` from severity."""
        _freeze_context_tuples(data, "context")
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

    ``context`` uses tuple-of-tuples with recursively frozen values
    for deep immutability.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0"] = "1.0"
    code: ErrorCode
    message: str = Field(min_length=1)
    traceback: str | None = None
    context: tuple[tuple[str, Any], ...] = Field(default_factory=tuple)

    @model_validator(mode="before")
    @classmethod
    def _freeze_context(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Recursively freeze context values before construction."""
        _freeze_context_tuples(data, "context")
        return data

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
