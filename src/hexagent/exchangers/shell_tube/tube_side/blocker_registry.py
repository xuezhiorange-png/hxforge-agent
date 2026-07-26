"""TASK-025 30-code blocker registry.

§13 — Closed 30-code BlockerCode registry and the unique
       ``emit_blocker`` entry point.
§13.2 — Extended BL_001 semantics.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Final

# §13.1 — Closed 30-code BlockerCode registry.


class BlockerCode(enum.StrEnum):
    """§13.1 — Closed 30-code registry.

    Members are sorted alphabetically by lexical name; the textual
    ordering is part of the contract.
    """

    BL_001_ACTIVE_PARTICIPATION_MISSING = "BL_001_ACTIVE_PARTICIPATION_MISSING"
    BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET = "BL_002_AUTHORITY_MODE_NOT_IN_TASK025_SET"
    BL_003_BLOCKED_INPUT_REJECTED = "BL_003_BLOCKED_INPUT_REJECTED"
    BL_004_CROSS_PAIR_REFERENCE_PLANE = "BL_004_CROSS_PAIR_REFERENCE_PLANE"
    BL_005_DECIMAL_STRUCTURED_IDENTITY_COLLISION = "BL_005_DECIMAL_STRUCTURAL_IDENTITY_COLLISION"
    BL_006_DUPLICATE_AUTHORITY = "BL_006_DUPLICATE_AUTHORITY"
    BL_007_EMPTY_ACTIVE_SET = "BL_007_EMPTY_ACTIVE_SET"
    BL_008_FINALIZATION_INTERNAL_GUARD = "BL_008_FINALIZATION_INTERNAL_GUARD"
    BL_009_FLOW_LENGTH_NON_DETERMINISTIC = "BL_009_FLOW_LENGTH_NON_DETERMINISTIC"
    BL_010_HEAT_LENGTH_NON_DETERMINISTIC = "BL_010_HEAT_LENGTH_NON_DETERMINISTIC"
    BL_011_INVALID_AUTHORITY_HASH = "BL_011_INVALID_AUTHORITY_HASH"
    BL_012_INVALID_REQUEST_HASH = "BL_012_INVALID_REQUEST_HASH"
    BL_013_INVALID_TASK020_CONFIGURATION = "BL_013_INVALID_TASK020_CONFIGURATION"
    BL_014_INVALID_TASK021_LAYOUT = "BL_014_INVALID_TASK021_LAYOUT"
    BL_015_MISSING_PROFILE_IDENTITY = "BL_015_MISSING_PROFILE_IDENTITY"
    BL_016_NON_FROZEN_INPUT = "BL_016_NON_FROZEN_INPUT"
    BL_017_NON_TASK025_OWNED_ENUM = "BL_017_NON_TASK025_OWNED_ENUM"
    BL_018_PROFILE_SCHEMA_VERSION_INCOMPATIBLE = "BL_018_PROFILE_SCHEMA_VERSION_INCOMPATIBLE"
    BL_019_RAW_PROJECTION_UNSUPPORTED = "BL_019_RAW_PROJECTION_UNSUPPORTED"
    BL_020_REFERENCE_PLANE_KIND_MISMATCH = "BL_020_REFERENCE_PLANE_KIND_MISMATCH"
    BL_021_REFERENCE_PLANE_TOKEN_UNKNOWN = "BL_021_REFERENCE_PLANE_TOKEN_UNKNOWN"
    BL_022_REQUEST_HASH_NOT_AVAILABLE = "BL_022_REQUEST_HASH_NOT_AVAILABLE"
    BL_023_RESULT_HASH_COLLISION = "BL_023_RESULT_HASH_COLLISION"
    BL_024_TASK020_IDENTITY_MISMATCH = "BL_024_TASK020_IDENTITY_MISMATCH"
    BL_025_TASK021_IDENTITY_MISMATCH = "BL_025_TASK021_IDENTITY_MISMATCH"
    BL_026_TUBE_GEOMETRY_MISSING = "BL_026_TUBE_GEOMETRY_MISSING"
    BL_027_UNREGISTERED_BLOCKER_CODE = "BL_027_UNREGISTERED_BLOCKER_CODE"
    BL_028_UNSUPPORTED_PROFILE = "BL_028_UNSUPPORTED_PROFILE"
    BL_029_UNSUPPORTED_SCHEMA = "BL_029_UNSUPPORTED_SCHEMA"
    BL_030_UNSUPPORTED_VERSION = "BL_030_UNSUPPORTED_VERSION"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


# §13.1 — Exact member count must remain 30.
_BLOCKER_CODE_COUNT: Final[int] = 30
assert len(BlockerCode.__members__) == _BLOCKER_CODE_COUNT, (
    f"BlockerCode must have exactly {_BLOCKER_CODE_COUNT} members"
)


# §13 — Task025BlockerEntry is a (code, field_path, message_key, evidence_refs)
# record. It is the unique blocker entry shape carried in blocked results.


@dataclass(frozen=True)
class Task025BlockerEntry:
    """§6.3 — Task025BlockerEntry used in the blocked result.

    The order of fields is fixed. ``field_path`` and ``evidence_refs``
    use canonical tuple ordering.
    """

    code: BlockerCode
    field_path: tuple[str, ...]
    message_key: str
    evidence_refs: tuple[str, ...]


# §13 / §A07 — emit_blocker is the unique entry. Unregistered codes
# collapse to BL_027_UNREGISTERED_BLOCKER_CODE.


def emit_blocker(
    code: Any,
    field_path: tuple[str, ...] | list[str] | str,
    message_key: str,
    evidence_refs: tuple[str, ...] | list[str] = (),
) -> Task025BlockerEntry:
    """§13 / §A07 — emit one blocker entry; collapse unknown codes."""
    if isinstance(field_path, str):
        field_path_tuple: tuple[str, ...] = (field_path,)
    else:
        field_path_tuple = tuple(field_path)
    if not all(isinstance(p, str) and p for p in field_path_tuple):
        raise ValueError(f"field_path entries must be non-empty str: {field_path_tuple!r}")
    if isinstance(evidence_refs, (list, tuple)):
        evidence_refs_tuple: tuple[str, ...] = tuple(evidence_refs)
    else:
        raise TypeError(f"evidence_refs must be tuple/list of str: {type(evidence_refs).__name__}")
    if not all(isinstance(r, str) and r for r in evidence_refs_tuple):
        raise ValueError(f"evidence_refs entries must be non-empty str: {evidence_refs_tuple!r}")
    if not isinstance(code, BlockerCode):
        return Task025BlockerEntry(
            code=BlockerCode.BL_027_UNREGISTERED_BLOCKER_CODE,
            field_path=field_path_tuple,
            message_key=message_key,
            evidence_refs=evidence_refs_tuple,
        )
    return Task025BlockerEntry(
        code=code,
        field_path=field_path_tuple,
        message_key=message_key,
        evidence_refs=evidence_refs_tuple,
    )


def collapse_unregistered_codes(
    entries: list[Task025BlockerEntry],
) -> tuple[Task025BlockerEntry, ...]:
    """§A12 / §12 — Sort and deduplicate entries by code; return tuple."""
    seen_codes: set[BlockerCode] = set()
    unique: list[Task025BlockerEntry] = []
    for entry in sorted(entries, key=lambda e: e.code.canonical_utf8_bytes):
        if entry.code in seen_codes:
            continue
        seen_codes.add(entry.code)
        unique.append(entry)
    return tuple(unique)


__all__ = [
    "BlockerCode",
    "Task025BlockerEntry",
    "emit_blocker",
    "collapse_unregistered_codes",
]
