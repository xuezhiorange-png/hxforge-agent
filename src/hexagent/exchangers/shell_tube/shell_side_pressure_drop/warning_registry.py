"""Closed TASK-034 warning and deferred capability registries."""

from __future__ import annotations

from .models import DEFERRED_CAPABILITIES, WarningEntry

WARNING_CODES: tuple[str, ...] = (
    "SSPD_SCREENING_AGGREGATE_ONLY",
    "SSPD_IDEALIZED_CROSS_FLOW_MODEL",
    "SSPD_LEAKAGE_BYPASS_EXCLUDED",
    "SSPD_NON_TOTAL_PRESSURE_DROP_OUTPUT",
    "SSPD_CONSTRUCTION_FAMILY_DEFERRED",
)


def validate_warning_token(token: str) -> str:
    if type(token) is not str or token not in WARNING_CODES:
        raise ValueError("unknown TASK034 warning token")
    return token


def make_warning(code: str, *, field_path: str | None = None) -> WarningEntry:
    validate_warning_token(code)
    return WarningEntry(code=code, field_path=field_path)


def all_warnings() -> tuple[WarningEntry, ...]:
    return tuple(make_warning(code) for code in WARNING_CODES)


def validate_deferred_token(token: str) -> str:
    if type(token) is not str or token not in DEFERRED_CAPABILITIES:
        raise ValueError("unknown TASK034 deferred capability token")
    return token


__all__ = [
    "WARNING_CODES",
    "DEFERRED_CAPABILITIES",
    "all_warnings",
    "make_warning",
    "validate_deferred_token",
]
