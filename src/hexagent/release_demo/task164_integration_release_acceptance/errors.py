"""Closed TASK164 failure vocabulary and deterministic blocker ordering."""

from __future__ import annotations

from collections.abc import Iterable

from .models import (
    TASK164_FAILURE_CODE_DECLARATION_ORDER,
    TASK164_FAILURE_STAGE_ORDER,
    Task164Blocker,
    Task164FailureCode,
    Task164FailureStage,
)


def blocker(
    code: Task164FailureCode,
    stage: Task164FailureStage,
    *evidence_refs: str,
) -> Task164Blocker:
    """Construct one immutable blocker from the closed enum only."""

    if type(code) is not Task164FailureCode or type(stage) is not Task164FailureStage:
        raise TypeError("TASK164 blockers require exact stage and code enums")
    refs = tuple(sorted(set(evidence_refs), key=lambda value: value.encode("utf-8", "strict")))
    return Task164Blocker(stage=stage, code=code, evidence_refs=refs)


def normalize_blockers(values: Iterable[Task164Blocker]) -> tuple[Task164Blocker, ...]:
    """Normalize by stage, declaration order, then UTF-8 evidence references."""

    unique: dict[
        tuple[Task164FailureStage, Task164FailureCode, tuple[str, ...]], Task164Blocker
    ] = {}
    for value in values:
        if type(value) is not Task164Blocker:
            raise TypeError("blocker collection contains a non-TASK164 blocker")
        refs = tuple(sorted(set(value.evidence_refs), key=lambda item: item.encode("utf-8")))
        normalized = Task164Blocker(stage=value.stage, code=value.code, evidence_refs=refs)
        unique[(normalized.stage, normalized.code, normalized.evidence_refs)] = normalized

    stage_index = {stage: index for index, stage in enumerate(TASK164_FAILURE_STAGE_ORDER)}
    code_index = {code: index for index, code in enumerate(TASK164_FAILURE_CODE_DECLARATION_ORDER)}
    return tuple(
        sorted(
            unique.values(),
            key=lambda value: (
                stage_index.get(value.stage, len(stage_index)),
                code_index.get(value.code, len(code_index)),
                tuple(item.encode("utf-8") for item in value.evidence_refs),
            ),
        )
    )


__all__ = ["blocker", "normalize_blockers"]
