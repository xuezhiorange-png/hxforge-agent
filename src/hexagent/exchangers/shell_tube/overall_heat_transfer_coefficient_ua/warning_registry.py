"""Frozen TASK-038 warning vocabulary."""

from __future__ import annotations

from .models import WarningEntry

WARNING_CODES: tuple[str, ...] = (
    "WARN_TASK025_PRECISION_LIMITATION_DISCLOSED",
    "WARN_TASK039_FORWARD_CONSUMER_DEFERRED",
)


def warning(code: str, field_path: str | None = None, message_key: str = "") -> WarningEntry:
    return WarningEntry(code, field_path, message_key)


__all__ = ["WARNING_CODES", "warning"]
