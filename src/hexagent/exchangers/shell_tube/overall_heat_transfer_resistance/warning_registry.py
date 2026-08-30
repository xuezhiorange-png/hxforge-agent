"""Closed TASK-037 warning registry.

The Source R3 producer-precision limitation is disclosed by authority fields,
not emitted as a runtime warning.  Therefore the valid path has no warnings.
"""

from __future__ import annotations

from enum import StrEnum

from .models import WarningEntry


class WarningCode(StrEnum):
    pass


TASK037_WARNING_REGISTRY: tuple[str, ...] = ()
TASK037_WARNING_CODE_COUNT = 0


def make_warning(code: str | WarningCode) -> WarningEntry:
    token = code.value if isinstance(code, WarningCode) else code
    if token not in TASK037_WARNING_REGISTRY:
        raise ValueError(f"unregistered TASK037 warning: {token!r}")
    return WarningEntry(code=token, message_key=token.lower())


def sort_warnings(
    entries: tuple[WarningEntry, ...] | list[WarningEntry],
) -> tuple[WarningEntry, ...]:
    return tuple(sorted(entries, key=lambda item: (item.code, item.field_path or "")))


def all_warnings() -> tuple[WarningEntry, ...]:
    return ()


__all__ = [
    "TASK037_WARNING_CODE_COUNT",
    "TASK037_WARNING_REGISTRY",
    "WarningCode",
    "all_warnings",
    "make_warning",
    "sort_warnings",
]
