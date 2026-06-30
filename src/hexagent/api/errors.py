"""TASK-010 structured API errors."""

from __future__ import annotations

from pydantic import BaseModel


class ErrorDetail(BaseModel, frozen=True):
    """Single structured error detail."""

    path: tuple[str | int, ...] = ()
    code: str
    message: str
    rejected_value_preview: str | None = None


class ApiError(BaseModel, frozen=True):
    """Structured API error response."""

    error_code: str
    message: str
    details: tuple[ErrorDetail, ...] = ()
