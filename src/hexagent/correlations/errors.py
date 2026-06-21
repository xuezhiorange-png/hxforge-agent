"""Domain errors for the correlation module."""

from __future__ import annotations

from typing import Any

from hexagent.domain.messages import ErrorCode


class CorrelationError(ValueError):
    """Base error for correlation module failures."""

    def __init__(
        self,
        code: ErrorCode,
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
            code=ErrorCode.CORRELATION_NOT_FOUND,
            message=msg,
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationVersionNotFoundError(CorrelationError):
    """Raised when a specific version is not found for a correlation ID."""

    def __init__(self, correlation_id: str, version: str) -> None:
        super().__init__(
            code=ErrorCode.CORRELATION_VERSION_NOT_FOUND,
            message=f"Version not found: {correlation_id} v{version}",
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationDuplicateError(CorrelationError):
    """Raised when registering a correlation with an already-registered key."""

    def __init__(self, correlation_id: str, version: str) -> None:
        super().__init__(
            code=ErrorCode.CORRELATION_DUPLICATE,
            message=f"Duplicate correlation: {correlation_id} v{version}",
            context={"correlation_id": correlation_id, "version": version},
        )


class CorrelationHashMismatchError(CorrelationError):
    """Raised when the definition_hash does not match the computed hash."""

    def __init__(self, correlation_id: str, expected: str, actual: str) -> None:
        super().__init__(
            code=ErrorCode.HASH_MISMATCH,
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
    "CorrelationHashMismatchError",
    "CorrelationNotFoundError",
    "CorrelationVersionNotFoundError",
]
