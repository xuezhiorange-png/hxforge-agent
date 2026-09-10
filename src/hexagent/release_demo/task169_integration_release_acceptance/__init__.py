"""TASK-169 HXForge v0.6 integration and release acceptance."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Task169ReleaseValidationResult


def validate_request(raw: object) -> "Task169ReleaseValidationResult":
    """Validate one release request through the sole public entry point."""

    from .service import validate_request as _validate_request

    return _validate_request(raw)


__all__ = ("validate_request",)
