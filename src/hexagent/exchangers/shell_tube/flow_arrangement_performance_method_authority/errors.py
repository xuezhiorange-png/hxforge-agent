"""Closed TASK161 diagnostics and fail-closed error construction."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from .models import FailureStage, Task161Blocker, Task161Warning


class Task161FailureCode(StrEnum):
    INVALID_TASK160_RESULT = "INVALID_TASK160_RESULT"
    TASK160_IDENTITY_REPLAY_FAILED = "TASK160_IDENTITY_REPLAY_FAILED"
    TASK160_NOT_APPLICABLE = "TASK160_NOT_APPLICABLE"
    TASK160_NOT_COMPLETE = "TASK160_NOT_COMPLETE"
    INVALID_CAPACITY_RATE = "INVALID_CAPACITY_RATE"
    INVALID_CAPACITY_RATIO = "INVALID_CAPACITY_RATIO"
    CATALOG_AUTHORITY_INVALID = "CATALOG_AUTHORITY_INVALID"
    SOURCE_REGISTER_INVALID = "SOURCE_REGISTER_INVALID"
    METHOD_AUTHORITY_INVALID = "METHOD_AUTHORITY_INVALID"
    ASSUMPTION_CONTRACT_INVALID = "ASSUMPTION_CONTRACT_INVALID"
    PROVENANCE_INVALID = "PROVENANCE_INVALID"
    IDENTITY_REPLAY_FAILED = "IDENTITY_REPLAY_FAILED"
    INTERNAL_INVARIANT_VIOLATION = "INTERNAL_INVARIANT_VIOLATION"
    INVALID_REQUEST_TYPE = "INVALID_REQUEST_TYPE"
    INVALID_REQUEST_SCHEMA = "INVALID_REQUEST_SCHEMA"
    UNSUPPORTED_TASK161_VERSION = "UNSUPPORTED_TASK161_VERSION"
    SOURCE_DEFINITION_ID_MISMATCH = "SOURCE_DEFINITION_ID_MISMATCH"
    UNSUPPORTED_RAW_VALUE = "UNSUPPORTED_RAW_VALUE"


FailureCode = Task161FailureCode
BlockerCode = Task161FailureCode


def make_blocker(
    code: Task161FailureCode | str,
    *,
    stage: FailureStage,
    field_path: str = "",
    evidence_refs: Iterable[str] = (),
    details: Iterable[tuple[str, str]] = (),
) -> Task161Blocker:
    token = code.value if isinstance(code, Task161FailureCode) else code
    return Task161Blocker(
        code=token,
        stage=stage,
        field_path=field_path,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        details=tuple(details),
    )


def blocker_sort_key(
    blocker: Task161Blocker,
) -> tuple[str, str, str, tuple[str, ...], tuple[tuple[str, str], ...]]:
    return (
        blocker.stage.value,
        blocker.code,
        blocker.field_path,
        blocker.evidence_refs,
        blocker.details,
    )


def sort_blockers(items: Iterable[Task161Blocker]) -> tuple[Task161Blocker, ...]:
    return tuple(sorted(items, key=blocker_sort_key))


def make_warning(
    code: str,
    *,
    field_path: str = "",
    evidence_refs: Iterable[str] = (),
) -> Task161Warning:
    return Task161Warning(
        code=code,
        field_path=field_path,
        evidence_refs=tuple(sorted(set(evidence_refs))),
    )


def warning_sort_key(warning: Task161Warning) -> tuple[str, str, tuple[str, ...]]:
    return (warning.code, warning.field_path, warning.evidence_refs)


def sort_warnings(items: Iterable[Task161Warning]) -> tuple[Task161Warning, ...]:
    return tuple(sorted(items, key=warning_sort_key))


__all__ = [
    "BlockerCode",
    "FailureCode",
    "Task161FailureCode",
    "blocker_sort_key",
    "make_blocker",
    "make_warning",
    "sort_blockers",
    "sort_warnings",
    "warning_sort_key",
]
