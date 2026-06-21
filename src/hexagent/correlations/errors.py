"""Domain errors for the correlation module."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class CorrelationErrorCode(StrEnum):
    """Stable error-code constants for correlation operations."""

    NOT_FOUND = "correlation_not_found"
    VERSION_NOT_FOUND = "correlation_version_not_found"
    DUPLICATE = "correlation_duplicate"
    DEPRECATED = "correlation_deprecated"
    WITHDRAWN = "correlation_withdrawn"
    GEOMETRY_INCOMPATIBLE = "correlation_geometry_incompatible"
    PHASE_INCOMPATIBLE = "correlation_phase_incompatible"
    FLOW_REGIME_INCOMPATIBLE = "correlation_flow_regime_incompatible"
    INPUT_MISSING = "correlation_input_missing"
    RECOMMENDED_RANGE_EXCEEDED = "correlation_recommended_range_exceeded"
    ABSOLUTE_RANGE_EXCEEDED = "correlation_absolute_range_exceeded"
    EXTRAPOLATION_USED = "correlation_extrapolation_used"
    SOURCE_UNVERIFIED = "correlation_source_unverified"
    HASH_MISMATCH = "correlation_hash_mismatch"
    DEFINITION_INVALID = "correlation_definition_invalid"


class CorrelationError(ValueError):
    """Base error for correlation module failures."""

    def __init__(
        self,
        code: CorrelationErrorCode,
        message: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.context = context or {}

    def as_dict(self) -> dict[str, Any]:
        return {
            "code": self.code.value,
            "message": str(self),
            "context": self.context,
        }


class CorrelationNotFoundError(CorrelationError):
    """Raised when a correlation is not found in the registry."""

    def __init__(self, correlation_id: str, version: str | None = None) -> None:
        msg = f"Correlation not found: {correlation_id}"
        if version:
            msg += f" v{version}"
        super().__init__(
            code=CorrelationErrorCode.NOT_FOUND,
            message=msg,
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationDuplicateError(CorrelationError):
    """Raised when registering a correlation with an already-registered key."""

    def __init__(self, correlation_id: str, version: str) -> None:
        super().__init__(
            code=CorrelationErrorCode.DUPLICATE,
            message=f"Duplicate correlation: {correlation_id} v{version}",
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationVersionNotFoundError(CorrelationError):
    """Raised when a specific version is not found for a correlation ID."""

    def __init__(self, correlation_id: str, version: str) -> None:
        super().__init__(
            code=CorrelationErrorCode.VERSION_NOT_FOUND,
            message=f"Version not found: {correlation_id} v{version}",
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationHashMismatchError(CorrelationError):
    """Raised when the definition_hash does not match the computed hash."""

    def __init__(self, correlation_id: str, expected: str, actual: str) -> None:
        super().__init__(
            code=CorrelationErrorCode.HASH_MISMATCH,
            message=f"Hash mismatch for {correlation_id}: expected {expected}, got {actual}",
            context={
                "correlation_id": correlation_id,
                "expected_hash": expected,
                "actual_hash": actual,
            },
        )


__all__ = [
    "CorrelationDuplicateError",
    "CorrelationError",
    "CorrelationErrorCode",
    "CorrelationHashMismatchError",
    "CorrelationNotFoundError",
    "CorrelationVersionNotFoundError",
]
