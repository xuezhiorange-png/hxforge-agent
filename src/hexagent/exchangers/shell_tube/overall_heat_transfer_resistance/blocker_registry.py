"""Closed, reachable TASK-037 blocker registry."""

from __future__ import annotations

from enum import StrEnum
from typing import Final

from .models import BlockerEntry
from .schema import STAGE_RANKS


class BlockerCode(StrEnum):
    RAW_INPUT_TYPE_INVALID = "T037_RAW_INPUT_TYPE_INVALID"
    REQUEST_SCHEMA_INVALID = "T037_REQUEST_SCHEMA_INVALID"
    TASK021_TYPE_INVALID = "T037_TASK021_TYPE_INVALID"
    TASK021_INVALID = "T037_TASK021_INVALID"
    TASK025_TYPE_INVALID = "T037_TASK025_TYPE_INVALID"
    TASK025_BLOCKED = "T037_TASK025_BLOCKED"
    TASK025_INVALID = "T037_TASK025_INVALID"
    TASK025_RESULT_HASH_MISMATCH = "T037_TASK025_RESULT_HASH_MISMATCH"
    TASK025_RESULT_ID_MISMATCH = "T037_TASK025_RESULT_ID_MISMATCH"
    TASK025_PUBLIC_AREA_INVALID = "T037_TASK025_PUBLIC_AREA_INVALID"
    TASK025_PUBLIC_AREA_NONCANONICAL = "T037_TASK025_PUBLIC_AREA_NONCANONICAL"
    TASK021_TASK025_MISMATCH = "T037_TASK021_TASK025_MISMATCH"
    TASK025_HYDRAULIC_AUTHORITY_INVALID = "T037_TASK025_HYDRAULIC_AUTHORITY_INVALID"
    GEOMETRY_INVALID = "T037_GEOMETRY_INVALID"
    SURFACE_AUTHORITY_INVALID = "T037_SURFACE_AUTHORITY_INVALID"
    MATERIAL_AUTHORITY_INVALID = "T037_MATERIAL_AUTHORITY_INVALID"
    CONDUCTIVITY_AUTHORITY_INVALID = "T037_CONDUCTIVITY_AUTHORITY_INVALID"
    FOULING_AUTHORITY_INVALID = "T037_FOULING_AUTHORITY_INVALID"
    FOULING_AUTHORITY_MISSING = "T037_FOULING_AUTHORITY_MISSING"
    CANONICALIZATION_FAILED = "T037_CANONICALIZATION_FAILED"
    DECIMAL_FAILURE = "T037_DECIMAL_FAILURE"
    INTERNAL_ERROR = "T037_INTERNAL_ERROR"


_STAGE_BY_CODE: Final[dict[BlockerCode, str]] = {
    BlockerCode.RAW_INPUT_TYPE_INVALID: "S00_RAW_INPUT_BOUNDARY",
    BlockerCode.REQUEST_SCHEMA_INVALID: "S01_TYPED_REQUEST_SCHEMA_VALIDATION",
    BlockerCode.TASK021_TYPE_INVALID: "S02_TASK021_UPSTREAM_VALIDATION",
    BlockerCode.TASK021_INVALID: "S02_TASK021_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_TYPE_INVALID: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_BLOCKED: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_INVALID: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_RESULT_HASH_MISMATCH: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_RESULT_ID_MISMATCH: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_PUBLIC_AREA_INVALID: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK025_PUBLIC_AREA_NONCANONICAL: "S03_TASK025_UPSTREAM_VALIDATION",
    BlockerCode.TASK021_TASK025_MISMATCH: "S04_TASK021_TASK025_CROSS_BINDING",
    BlockerCode.TASK025_HYDRAULIC_AUTHORITY_INVALID: "S04_TASK021_TASK025_CROSS_BINDING",
    BlockerCode.GEOMETRY_INVALID: "S05_GEOMETRY_AND_SURFACE_SEMANTIC_VALIDATION",
    BlockerCode.SURFACE_AUTHORITY_INVALID: "S05_GEOMETRY_AND_SURFACE_SEMANTIC_VALIDATION",
    BlockerCode.MATERIAL_AUTHORITY_INVALID: (
        "S06_WALL_MATERIAL_AND_CONDUCTIVITY_AUTHORITY_ADMISSIBILITY_VALIDATION"
    ),
    BlockerCode.CONDUCTIVITY_AUTHORITY_INVALID: (
        "S06_WALL_MATERIAL_AND_CONDUCTIVITY_AUTHORITY_ADMISSIBILITY_VALIDATION"
    ),
    BlockerCode.FOULING_AUTHORITY_INVALID: "S07_FOULING_AUTHORITY_ADMISSIBILITY_VALIDATION",
    BlockerCode.FOULING_AUTHORITY_MISSING: "S07_FOULING_AUTHORITY_ADMISSIBILITY_VALIDATION",
    BlockerCode.CANONICALIZATION_FAILED: "S11_CANONICAL_HASH_UUID_PROVENANCE",
    BlockerCode.DECIMAL_FAILURE: "S09_CYLINDRICAL_WALL_RESISTANCE_COMPUTATION",
    BlockerCode.INTERNAL_ERROR: "S11_CANONICAL_HASH_UUID_PROVENANCE",
}

TASK037_BLOCKER_REGISTRY: Final[tuple[str, ...]] = tuple(code.value for code in BlockerCode)
BLOCKER_REGISTRY: Final[dict[str, str]] = {code.value: _STAGE_BY_CODE[code] for code in BlockerCode}
BLOCKER_CODES: Final[tuple[str, ...]] = TASK037_BLOCKER_REGISTRY
BLOCKER_COUNT: Final[int] = len(TASK037_BLOCKER_REGISTRY)
REACHABLE_BLOCKER_COUNT: Final[int] = BLOCKER_COUNT


def make_blocker(
    code: BlockerCode | str,
    field_path: str | None = None,
    message_key: str | None = None,
    details: tuple[tuple[str, str], ...] = (),
) -> BlockerEntry:
    token = code.value if isinstance(code, BlockerCode) else code
    if token not in BLOCKER_REGISTRY:
        raise ValueError(f"unregistered TASK037 blocker: {token!r}")
    return BlockerEntry(
        code=token,
        stage=BLOCKER_REGISTRY[token],
        field_path=field_path,
        message_key=message_key or token.lower(),
        details=details,
    )


def sort_blockers(
    entries: tuple[BlockerEntry, ...] | list[BlockerEntry],
) -> tuple[BlockerEntry, ...]:
    return tuple(
        sorted(
            entries,
            key=lambda item: (
                STAGE_RANKS.get(item.stage, 999),
                item.code,
                item.field_path or "",
                item.message_key,
                item.details,
            ),
        )
    )


def collapse_unregistered_codes(entries: tuple[BlockerEntry, ...]) -> tuple[BlockerEntry, ...]:
    return sort_blockers(entries)


emit_blocker = make_blocker


__all__ = [
    "BLOCKER_CODES",
    "BLOCKER_COUNT",
    "BLOCKER_REGISTRY",
    "BlockerCode",
    "REACHABLE_BLOCKER_COUNT",
    "TASK037_BLOCKER_REGISTRY",
    "collapse_unregistered_codes",
    "emit_blocker",
    "make_blocker",
    "sort_blockers",
]
