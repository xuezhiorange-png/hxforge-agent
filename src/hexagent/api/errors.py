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

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):  # type: ignore[no-redef]  # noqa: UP042
        """Backport of StrEnum for Python < 3.11."""

        def __str__(self) -> str:
            return self.value


class ApiErrorCode(StrEnum):
    """Frozen error codes per contract §17."""

    VALIDATION_FAILED = "validation_failed"
    IDEMPOTENCY_CONFLICT = "idempotency_conflict"
    RUN_NOT_FOUND = "run_not_found"
    PDF_NOT_AVAILABLE = "pdf_not_available"
    INTERNAL_ERROR = "internal_error"


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


def _error_path_sort_key(
    path: tuple[str | int, ...],
) -> tuple[tuple[int, str], ...]:
    """Normalize mixed str/int path elements for deterministic sorting.

    Strings sort before ints (0 < 1), both compared as str within their group.
    """
    return tuple((0, str(part)) if isinstance(part, str) else (1, str(part)) for part in path)


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
        """Deterministic ordering by (path, code).

        Uses _error_path_sort_key to handle mixed str/int path elements.
        """
        return tuple(sorted(value, key=lambda d: (_error_path_sort_key(d.path), d.code)))
