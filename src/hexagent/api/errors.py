"""TASK-010 frozen error contract.

Matches frozen contract §17 exactly:
- ApiErrorCode enum (5 values)
- ErrorDetail with preview limit validator
- ApiError with all frozen fields
- deterministic (path, code) ordering for details
"""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import field_validator

from hexagent.domain.models import StrictBaseModel


class ApiErrorCode(str):  # noqa: SLOT000 — StrEnum alternative for 3.10 compat
    """Frozen error codes per contract §17."""

    VALIDATION_FAILED = "validation_failed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RUN_NOT_FOUND = "run_not_found"
    PDF_NOT_AVAILABLE = "pdf_not_available"
    INTERNAL_ERROR = "internal_error"

    # Allow comparison as string
    def __eq__(self, other: object) -> bool:
        if isinstance(other, str):
            return str(self) == other
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(str(self))


# Canonical set of valid error codes for assertion
VALID_ERROR_CODES: frozenset[str] = frozenset(
    {
        ApiErrorCode.VALIDATION_FAILED,
        ApiErrorCode.IDEMPOTENCY_CONFLICT,
        ApiErrorCode.RUN_NOT_FOUND,
        ApiErrorCode.PDF_NOT_AVAILABLE,
        ApiErrorCode.INTERNAL_ERROR,
    }
)


class ErrorDetail(StrictBaseModel):
    """Single validation detail with path, code, message and optional preview."""

    model_config = {"frozen": True, "extra": "forbid"}

    path: tuple[str | int, ...]
    code: str
    message: str
    rejected_value_preview: str | None = None

    @field_validator("rejected_value_preview")
    @classmethod
    def limit_preview(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 200:
            return value[:200]
        return value


class ApiError(StrictBaseModel):
    """Frozen top-level API error response per contract §17.

    All public error responses MUST serialize to exactly these fields
    at the top level — no 'detail' wrapper.
    """

    model_config = {"frozen": True, "extra": "forbid"}

    api_schema_version: Literal["1"]
    operation: str | None
    status_code: int
    error_code: str  # must be a valid ApiErrorCode value
    error_message: str
    request_digest: str | None
    details: tuple[ErrorDetail, ...]

    MAX_DISPLAYED_VALUE_LENGTH: ClassVar[int] = 200

    @field_validator("error_code")
    @classmethod
    def validate_error_code(cls, value: str) -> str:
        if value not in VALID_ERROR_CODES:
            raise ValueError(
                f"error_code must be one of {sorted(VALID_ERROR_CODES)}, got {value!r}"
            )
        return value

    @field_validator("details")
    @classmethod
    def sort_details(cls, value: tuple[ErrorDetail, ...]) -> tuple[ErrorDetail, ...]:
        """Deterministic ordering by (path, code)."""
        return tuple(sorted(value, key=lambda d: (d.path, d.code)))
