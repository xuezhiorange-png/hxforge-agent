"""TASK-009 optimization-specific domain errors."""

from __future__ import annotations

from typing import Any

from hexagent.domain.messages import ErrorCode


class OptimizationError(ValueError):
    """Base error for TASK-009 optimization module failures."""

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


class InvalidLengthQuantum(OptimizationError):
    """Raised when length_quantum_m is not a valid power-of-10 Decimal."""

    def __init__(self, value: str, *, detail: str = "") -> None:
        msg = f"Invalid length quantum: {value!r}"
        if detail:
            msg += f" — {detail}"
        super().__init__(
            code=ErrorCode.CATALOG_INVALID,
            message=msg,
            context={"value": value, "detail": detail},
        )


class InvalidLengthError(OptimizationError):
    """Raised when a length value fails validation during tick conversion."""

    def __init__(self, value: str, quantum: str, *, detail: str = "") -> None:
        msg = f"Invalid length {value!r} for quantum {quantum!r}"
        if detail:
            msg += f" — {detail}"
        super().__init__(
            code=ErrorCode.CATALOG_INVALID,
            message=msg,
            context={"value": value, "quantum": quantum, "detail": detail},
        )


class CatalogInvalid(OptimizationError):
    """Raised when catalog data fails structural validation."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.CATALOG_INVALID,
            message=message,
            context=context,
        )


class InvalidRequestBounds(OptimizationError):
    """Raised when request bounds are invalid or exceed catalog interval."""

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(
            code=ErrorCode.INVALID_SIZING_REQUEST,
            message=message,
            context=context,
        )


class CapExceeded(OptimizationError):
    """Raised when the raw combination count exceeds the effective cap.

    Callers should check the cap *before* materialization and handle this
    exception to return a BLOCKED result without touching the evaluator.
    """

    def __init__(
        self,
        raw_count: int,
        effective_cap: int,
        *,
        context: dict[str, Any] | None = None,
    ) -> None:
        msg = f"Raw combination count {raw_count} exceeds effective cap {effective_cap}"
        ctx = {"raw_count": raw_count, "effective_cap": effective_cap}
        if context:
            ctx.update(context)
        super().__init__(
            code=ErrorCode.CALCULATION_BLOCKED,
            message=msg,
            context=ctx,
        )


__all__ = [
    "CapExceeded",
    "CatalogInvalid",
    "InvalidLengthError",
    "InvalidLengthQuantum",
    "InvalidRequestBounds",
    "OptimizationError",
]
