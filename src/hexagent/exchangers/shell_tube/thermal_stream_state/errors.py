"""TASK160 closed diagnostics and fail-closed error boundaries."""

from __future__ import annotations

from collections.abc import Iterable
from enum import StrEnum

from .models import FailureStage, Task160Blocker, Task160Warning


class BlockerCode(StrEnum):
    B001 = "B001"
    B002 = "B002"
    B003 = "B003"
    B004 = "B004"
    B005 = "B005"
    B006 = "B006"
    B007 = "B007"
    B008 = "B008"
    B009 = "B009"
    B010 = "B010"
    B011 = "B011"
    B012 = "B012"
    B013 = "B013"
    B014 = "B014"
    B015 = "B015"
    B016 = "B016"
    B017 = "B017"
    B018 = "B018"
    B019 = "B019"
    B020 = "B020"
    B021 = "B021"
    B022 = "B022"
    B023 = "B023"
    B025 = "B025"
    B026 = "B026"
    B027 = "B027"
    B028 = "B028"
    B029 = "B029"
    B030 = "B030"

    STREAM_COUNT_INVALID = "B001"
    DUPLICATE_TUBE_SIDE = "B002"
    DUPLICATE_SHELL_SIDE = "B003"
    SIDE_MISSING_OR_UNSUPPORTED = "B004"
    STREAM_ID_MISSING = "B005"
    FLUID_IDENTITY_MISSING = "B006"
    PHASE_AUTHORITY_MISSING = "B007"
    PHASE_UNSUPPORTED = "B008"
    INLET_TEMPERATURE_INVALID = "B009"
    EQUAL_INLET_TEMPERATURE = "B010"
    MASS_FLOW_INVALID = "B011"
    CP_INVALID = "B012"
    PROPERTY_SOURCE_IDENTITY_MISSING = "B013"
    PROPERTY_SOURCE_VERSION_MISSING = "B014"
    SNAPSHOT_IDENTITY_INVALID = "B015"
    PROPERTY_CONTEXT_INVALID = "B016"
    PRESSURE_INVALID_OR_MISSING = "B017"
    PROVENANCE_INCOMPLETE = "B018"
    ADAPTER_MAPPING_UNPROVEN_OR_FORBIDDEN = "B019"
    ADAPTER_VALUE_CONFLICT = "B020"
    ENVELOPE_MISSING_OR_MALFORMED = "B021"
    ENVELOPE_UNSUPPORTED = "B022"
    UNIT_UNSUPPORTED = "B023"
    ADAPTER_EVIDENCE_INVALID = "B025"
    SNAPSHOT_CROSS_BINDING_MISMATCH = "B026"
    PROVENANCE_REFERENCE_INVALID = "B027"
    PROVENANCE_HASH_INVALID = "B028"
    COMPLETENESS_CDOT_MISSING = "B029"
    COMPLETENESS_FIELD_MISSING = "B030"


ACTIVE_BLOCKER_CODES: tuple[str, ...] = tuple(
    code.value for code in BlockerCode if code.name.startswith("B") and code.value != "B024"
)
RETIRED_BLOCKER_CODES: tuple[str, ...] = ("B024",)
DEFENSIVE_BLOCKER_CODES: tuple[str, ...] = ("B029", "B030")


class InternalGuardCode(StrEnum):
    I031_CANONICALIZATION_FAILURE = "I031_CANONICALIZATION_FAILURE"
    I032_IDENTITY_FINALIZATION_FAILURE = "I032_IDENTITY_FINALIZATION_FAILURE"
    I033_PROVENANCE_FINALIZATION_FAILURE = "I033_PROVENANCE_FINALIZATION_FAILURE"
    I034_PARTIAL_RESULT_FORBIDDEN = "I034_PARTIAL_RESULT_FORBIDDEN"
    I035_TASK161_FIELD_LEAK = "I035_TASK161_FIELD_LEAK"


WARNING_CODE_COUNT = 0
WARNINGS_ALWAYS_EMPTY = True


def make_blocker(
    code: BlockerCode | str,
    *,
    stage: FailureStage,
    field_path: str = "",
    evidence_refs: Iterable[str] = (),
    details: Iterable[tuple[str, str]] = (),
) -> Task160Blocker:
    token = code.value if isinstance(code, BlockerCode) else str(code)
    return Task160Blocker(
        code=token,
        stage=stage,
        field_path=field_path,
        evidence_refs=tuple(sorted(set(evidence_refs))),
        details=tuple((str(key), str(value)) for key, value in details),
    )


def blocker_sort_key(item: Task160Blocker) -> tuple[int, str, str, tuple[tuple[str, str], ...]]:
    try:
        code_rank = int(item.code[1:])
    except (ValueError, IndexError):
        code_rank = 999
    stage_rank = {
        FailureStage.RAW_BOUNDARY: 0,
        FailureStage.STRICT_VALIDATION: 1,
        FailureStage.APPLICABILITY: 2,
        FailureStage.COMPLETENESS: 3,
        FailureStage.IDENTITY: 4,
        FailureStage.PROVENANCE: 5,
    }[item.stage]
    return (stage_rank * 1000 + code_rank, item.field_path, item.code, item.details)


def sort_blockers(items: Iterable[Task160Blocker]) -> tuple[Task160Blocker, ...]:
    return tuple(sorted(items, key=blocker_sort_key))


def warning_sort_key(item: Task160Warning) -> tuple[str, str, tuple[str, ...]]:
    return (item.code, item.field_path, item.evidence_refs)


def sort_warnings(items: Iterable[Task160Warning]) -> tuple[Task160Warning, ...]:
    return tuple(sorted(items, key=warning_sort_key))


__all__ = [
    "ACTIVE_BLOCKER_CODES",
    "BlockerCode",
    "DEFENSIVE_BLOCKER_CODES",
    "InternalGuardCode",
    "RETIRED_BLOCKER_CODES",
    "WARNING_CODE_COUNT",
    "WARNINGS_ALWAYS_EMPTY",
    "blocker_sort_key",
    "make_blocker",
    "sort_blockers",
    "sort_warnings",
    "warning_sort_key",
]
