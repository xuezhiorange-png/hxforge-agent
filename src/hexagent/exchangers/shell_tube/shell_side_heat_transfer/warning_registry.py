"""Closed TASK-033 warning registry."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from .models import WarningEntry


class WarningCode(StrEnum):
    SSHT_KERN_SCREENING_MODEL_ONLY = "SSHT_KERN_SCREENING_MODEL_ONLY"
    SSHT_IDEALIZED_SHELL_FLOW_ASSUMPTION = "SSHT_IDEALIZED_SHELL_FLOW_ASSUMPTION"
    SSHT_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED = "SSHT_LEAKAGE_BYPASS_CORRECTIONS_EXCLUDED"
    SSHT_NO_FLOW_REGIME_CLASSIFICATION = "SSHT_NO_FLOW_REGIME_CLASSIFICATION"
    SSHT_NO_FULL_EXCHANGER_RATING_CLAIM = "SSHT_NO_FULL_EXCHANGER_RATING_CLAIM"


TASK033_WARNING_REGISTRY: tuple[str, ...] = tuple(code.value for code in WarningCode)
TASK033_WARNING_CODE_COUNT = 5


def make_warning(code: WarningCode | str) -> WarningEntry:
    token = code.value if isinstance(code, WarningCode) else code
    if token not in TASK033_WARNING_REGISTRY:
        raise ValueError(f"unknown TASK033 warning token: {token!r}")
    return WarningEntry(code=token, message_key=token.lower())


def sort_warnings(entries: Iterable[WarningEntry]) -> tuple[WarningEntry, ...]:
    return tuple(sorted(entries, key=lambda item: (item.code, item.field_path or "")))


def all_warnings() -> tuple[WarningEntry, ...]:
    return tuple(make_warning(code) for code in WarningCode)


__all__ = [
    "TASK033_WARNING_CODE_COUNT",
    "TASK033_WARNING_REGISTRY",
    "WarningCode",
    "all_warnings",
    "make_warning",
    "sort_warnings",
]
