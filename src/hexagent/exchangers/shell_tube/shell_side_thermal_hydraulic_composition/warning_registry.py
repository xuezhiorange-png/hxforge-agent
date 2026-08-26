"""Closed TASK-035 warning and deferred-capability registries."""

from __future__ import annotations

from .models import WarningEntry
from .schema import (
    DEFERRED_CAPABILITIES,
    DEFERRED_CAPABILITY_COUNT,
    WARNING_COUNT,
    WARNING_REGISTRY,
)

WARNING_CODES = WARNING_REGISTRY
DEFERRED_CODES = DEFERRED_CAPABILITIES


def all_warnings() -> tuple[str, ...]:
    """Return the deterministic warning projection for a composition result."""

    return WARNING_CODES


def warning_entries() -> tuple[WarningEntry, ...]:
    """Return warning records for callers that need typed message entries."""

    return tuple(WarningEntry(code=code, message_key=code.lower()) for code in WARNING_CODES)


def all_deferred_capabilities() -> tuple[str, ...]:
    """Return the deterministic v0.3 deferred-capability projection."""

    return DEFERRED_CODES


assert WARNING_COUNT == 5
assert DEFERRED_CAPABILITY_COUNT == 3


__all__ = [
    "DEFERRED_CODES",
    "DEFERRED_CAPABILITIES",
    "WARNING_CODES",
    "WARNING_REGISTRY",
    "all_deferred_capabilities",
    "all_warnings",
    "warning_entries",
]
