"""Closed TASK-032 warning registry and eligibility rules."""

from __future__ import annotations

from collections.abc import Iterable

from .models import WarningCode, WarningEntry

TASK032_WARNING_REGISTRY: tuple[str, ...] = tuple(code.value for code in WarningCode)
TASK032_WARNING_CODE_COUNT = 7


def make_warning(
    code: WarningCode | str,
    *,
    field_path: str | None = None,
    evidence_refs: Iterable[str] = (),
) -> WarningEntry:
    token = code.value if isinstance(code, WarningCode) else code
    prerequisite_stage = (
        "S07" if token == WarningCode.SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY else "S06"
    )
    return WarningEntry(
        code=token,
        severity="warning",
        prerequisite_stage=prerequisite_stage,
        field_path=field_path,
        message_key=token.lower(),
        evidence_refs=tuple(sorted(set(evidence_refs))),
    )


def warning_sort_key(entry: WarningEntry) -> tuple[str, str, str, tuple[str, ...]]:
    return (entry.code, entry.field_path or "", entry.message_key, entry.evidence_refs)


def sort_warnings(entries: Iterable[WarningEntry]) -> tuple[WarningEntry, ...]:
    return tuple(sorted(entries, key=warning_sort_key))


def eligible_warnings(*, completed_stage: int) -> tuple[WarningEntry, ...]:
    if completed_stage < 6:
        return ()
    codes = [
        WarningCode.SSFS_SINGLE_BULK_PROPERTY_SNAPSHOT_SCREENING_ONLY,
        WarningCode.SSFS_FLOW_REGIME_CLASSIFICATION_DEFERRED,
        WarningCode.SSFS_NON_NEWTONIAN_DEFERRED,
        WarningCode.SSFS_COMPRESSIBLE_PATH_INTEGRATION_EXCLUDED,
        WarningCode.SSFS_HEAT_TRANSFER_PRESSURE_DROP_DEFERRED,
        WarningCode.SSFS_NO_FULL_EXCHANGER_RATING_CLAIM,
    ]
    if completed_stage >= 7:
        codes.append(WarningCode.SSFS_FORMULA_AUTHORITY_SCREENING_MODEL_ONLY)
    return sort_warnings(make_warning(code) for code in codes)


__all__ = [
    "TASK032_WARNING_CODE_COUNT",
    "TASK032_WARNING_REGISTRY",
    "eligible_warnings",
    "make_warning",
    "sort_warnings",
    "warning_sort_key",
]
