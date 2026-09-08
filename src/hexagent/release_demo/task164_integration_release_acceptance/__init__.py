"""TASK164 integration, demonstration, and release-acceptance boundary."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Task164ValidationResult


def validate_request(raw: object) -> "Task164ValidationResult":
    """Validate one TASK164 request through the sole public entry point."""

    from .service import validate_request as _validate_request

    return _validate_request(raw)


__all__ = ("validate_request",)
