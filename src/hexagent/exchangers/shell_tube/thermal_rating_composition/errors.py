"""Closed TASK163 failure vocabulary and deterministic blocker ordering."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    Task163Blocker,
    Task163FailureCode,
    Task163FailureStage,
    Task163Warning,
)

FAILURE_CODE_ORDER: tuple[Task163FailureCode, ...] = tuple(Task163FailureCode)
FAILURE_STAGE_ORDER: tuple[Task163FailureStage, ...] = tuple(Task163FailureStage)
FAILURE_CODE_VOCABULARY_COUNT = len(FAILURE_CODE_ORDER)
FAILURE_CODE_VOCABULARY_CLOSED = FAILURE_CODE_VOCABULARY_COUNT == 21
UNLISTED_FAILURE_CODE_ALLOWED = False
FAILURE_CODE_ALIAS_ALLOWED = False


def blocker(
    code: Task163FailureCode,
    stage: Task163FailureStage,
    *evidence_refs: str,
) -> Task163Blocker:
    return Task163Blocker(
        code=code,
        stage=stage,
        evidence_refs=tuple(sorted(set(evidence_refs), key=lambda value: value.encode("utf-8"))),
    )


def normalize_blockers(values: Iterable[Task163Blocker]) -> tuple[Task163Blocker, ...]:
    stage_order = {value: index for index, value in enumerate(FAILURE_STAGE_ORDER)}
    code_order = {value: index for index, value in enumerate(FAILURE_CODE_ORDER)}
    normalized = [
        Task163Blocker(
            code=value.code,
            stage=value.stage,
            evidence_refs=tuple(
                sorted(set(value.evidence_refs), key=lambda item: item.encode("utf-8"))
            ),
        )
        for value in values
    ]
    unique: dict[
        tuple[Task163FailureStage, Task163FailureCode, tuple[str, ...]], Task163Blocker
    ] = {}
    for value in normalized:
        unique[(value.stage, value.code, value.evidence_refs)] = value
    return tuple(
        sorted(
            unique.values(),
            key=lambda value: (
                stage_order[value.stage],
                code_order[value.code],
                tuple(item.encode("utf-8") for item in value.evidence_refs),
            ),
        )
    )


def normalize_warnings(values: Iterable[Task163Warning]) -> tuple[Task163Warning, ...]:
    return tuple(
        sorted(
            values,
            key=lambda value: (
                value.code.encode("utf-8"),
                tuple(item.encode("utf-8") for item in value.evidence_refs),
            ),
        )
    )


__all__ = [
    "FAILURE_CODE_ALIAS_ALLOWED",
    "FAILURE_CODE_ORDER",
    "FAILURE_CODE_VOCABULARY_CLOSED",
    "FAILURE_CODE_VOCABULARY_COUNT",
    "FAILURE_STAGE_ORDER",
    "UNLISTED_FAILURE_CODE_ALLOWED",
    "blocker",
    "normalize_blockers",
    "normalize_warnings",
]
