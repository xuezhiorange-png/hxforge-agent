"""TASK-028 31-code blocker registry.

§27 — Closed 31-code BlockerCode registry and the unique
       ``emit_blocker`` entry point.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Final


# §12.1 — Closed 31-code BlockerCode registry.
class Task028BlockerCode(enum.StrEnum):
    """§12.2 — Closed 31-code registry.

    Members are sorted alphabetically by lexical name; the textual
    ordering is part of the contract.
    """

    BL_T028_APPLICABILITY_ASSERTION_FALSE = "BL_T028_APPLICABILITY_ASSERTION_FALSE"
    BL_T028_APPLICABILITY_ASSERTION_MISSING = "BL_T028_APPLICABILITY_ASSERTION_MISSING"
    BL_T028_AUTHORITY_HASH_MISMATCH = "BL_T028_AUTHORITY_HASH_MISMATCH"
    BL_T028_COMPONENT_AUTHORITY_SET_INVALID = "BL_T028_COMPONENT_AUTHORITY_SET_INVALID"
    BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH = "BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH"
    BL_T028_COMPONENT_ID_DUPLICATE = "BL_T028_COMPONENT_ID_DUPLICATE"
    BL_T028_COMPONENT_TYPE_UNSUPPORTED = "BL_T028_COMPONENT_TYPE_UNSUPPORTED"
    BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED = "BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED"
    BL_T028_COEFFICIENT_SOURCE_ID_MISSING = "BL_T028_COEFFICIENT_SOURCE_ID_MISSING"
    BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING = "BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING"
    BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING = "BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING"
    BL_T028_FLOW_DIRECTION_UNSUPPORTED = "BL_T028_FLOW_DIRECTION_UNSUPPORTED"
    BL_T028_GEOMETRY_EVIDENCE_MISSING = "BL_T028_GEOMETRY_EVIDENCE_MISSING"
    BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED = (
        "BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED"
    )
    BL_T028_LOSS_COEFFICIENT_NEGATIVE = "BL_T028_LOSS_COEFFICIENT_NEGATIVE"
    BL_T028_LOSS_COEFFICIENT_NONFINITE = "BL_T028_LOSS_COEFFICIENT_NONFINITE"
    BL_T028_MULTIPLICITY_INVALID = "BL_T028_MULTIPLICITY_INVALID"
    BL_T028_PARTIAL_RESULT_FORBIDDEN = "BL_T028_PARTIAL_RESULT_FORBIDDEN"
    BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE = "BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE"
    BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH = "BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH"
    BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN = "BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN"
    BL_T028_RAW_INPUT_BOUNDARY_MALFORMED = "BL_T028_RAW_INPUT_BOUNDARY_MALFORMED"
    BL_T028_REFERENCE_FLOW_AREA_INVALID = "BL_T028_REFERENCE_FLOW_AREA_INVALID"
    BL_T028_REFERENCE_PLANE_INVALID = "BL_T028_REFERENCE_PLANE_INVALID"
    BL_T028_REQUEST_UNKNOWN_FIELD = "BL_T028_REQUEST_UNKNOWN_FIELD"
    BL_T028_SERIAL_GROUP_EVIDENCE_INSUFFICIENT = "BL_T028_SERIAL_GROUP_EVIDENCE_INSUFFICIENT"
    BL_T028_SOURCE_AUTHORITY_INVALID = "BL_T028_SOURCE_AUTHORITY_INVALID"
    BL_T028_UPSTREAM_IDENTITY_MISMATCH = "BL_T028_UPSTREAM_IDENTITY_MISMATCH"
    BL_T028_UPSTREAM_TASK025_BLOCKED = "BL_T028_UPSTREAM_TASK025_BLOCKED"
    BL_T028_UPSTREAM_TASK026_RAW_BLOCKED = "BL_T028_UPSTREAM_TASK026_RAW_BLOCKED"
    BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED = "BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED"

    @property
    def canonical_utf8_bytes(self) -> bytes:
        return self.value.encode("ascii")


# §12.1 — Exact member count must remain 31.
_BLOCKER_CODE_COUNT: Final[int] = 31
assert len(Task028BlockerCode.__members__) == _BLOCKER_CODE_COUNT, (
    f"Task028BlockerCode must have exactly {_BLOCKER_CODE_COUNT} members"
)


# §12.3 — Ordering key mapping (frozen ordinal)
_BLOCKER_REGISTRY: Final[dict[Task028BlockerCode, int]] = {
    Task028BlockerCode.BL_T028_REQUEST_UNKNOWN_FIELD: 0,
    Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED: 1,
    Task028BlockerCode.BL_T028_UPSTREAM_TASK025_BLOCKED: 2,
    Task028BlockerCode.BL_T028_UPSTREAM_TASK026_RAW_BLOCKED: 3,
    Task028BlockerCode.BL_T028_UPSTREAM_TASK026_TYPED_BLOCKED: 4,
    Task028BlockerCode.BL_T028_UPSTREAM_IDENTITY_MISMATCH: 5,
    Task028BlockerCode.BL_T028_PROPERTY_SNAPSHOT_HASH_MISMATCH: 6,
    Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_MISSING: 7,
    Task028BlockerCode.BL_T028_APPLICABILITY_ASSERTION_FALSE: 8,
    Task028BlockerCode.BL_T028_FLOW_DIRECTION_UNSUPPORTED: 9,
    Task028BlockerCode.BL_T028_COMPONENT_AUTHORITY_SET_INVALID: 10,
    Task028BlockerCode.BL_T028_COMPONENT_ID_DUPLICATE: 11,
    Task028BlockerCode.BL_T028_PATH_SEQUENCE_INDEX_DUPLICATE: 12,
    Task028BlockerCode.BL_T028_COMPONENT_TYPE_UNSUPPORTED: 13,
    Task028BlockerCode.BL_T028_COMPONENT_FLOW_DIRECTION_MISMATCH: 14,
    Task028BlockerCode.BL_T028_REFERENCE_PLANE_INVALID: 15,
    Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NONFINITE: 16,
    Task028BlockerCode.BL_T028_PSEUDO_ZERO_COMPONENT_FORBIDDEN: 17,
    Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_NEGATIVE: 18,
    Task028BlockerCode.BL_T028_LOSS_COEFFICIENT_CONVENTION_UNSUPPORTED: 19,
    Task028BlockerCode.BL_T028_REFERENCE_FLOW_AREA_INVALID: 20,
    Task028BlockerCode.BL_T028_MULTIPLICITY_INVALID: 21,
    Task028BlockerCode.BL_T028_SERIAL_GROUP_EVIDENCE_INSUFFICIENT: 22,
    Task028BlockerCode.BL_T028_GEOMETRY_EVIDENCE_MISSING: 23,
    Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_ID_MISSING: 24,
    Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_VERSION_MISSING: 25,
    Task028BlockerCode.BL_T028_COEFFICIENT_SOURCE_LOCATION_MISSING: 26,
    Task028BlockerCode.BL_T028_COEFFICIENT_PERMISSION_NOT_ADMITTED: 27,
    Task028BlockerCode.BL_T028_AUTHORITY_HASH_MISMATCH: 28,
    Task028BlockerCode.BL_T028_PARTIAL_RESULT_FORBIDDEN: 29,
    Task028BlockerCode.BL_T028_SOURCE_AUTHORITY_INVALID: 30,
}

BLOCKER_REGISTRY_COUNT: Final[int] = 31


# §12 — Task028BlockerEntry (4-field record)
@dataclass(frozen=True)
class Task028BlockerEntry:
    """§12 — Task028BlockerEntry: code + field_path + message_key + evidence_refs."""

    code: Task028BlockerCode
    field_path: tuple[str, ...]
    message_key: str
    evidence_refs: tuple[str, ...]


# §12.2 — Internal carrier for dedup/order
@dataclass(frozen=True)
class _Task028PendingBlocker:
    """Internal-only carrier. NOT serialized in public blocker entry."""

    entry: Task028BlockerEntry
    component_id_tiebreaker: str  # "" for top-level blockers


# §12 — emit_blocker is the unique entry point
def emit_blocker(
    code: Task028BlockerCode,
    field_path: tuple[str, ...] | list[str] | str,
    message_key: str,
    evidence_refs: tuple[str, ...] | list[str] = (),
    component_id_tiebreaker: str = "",
) -> _Task028PendingBlocker:
    """Emit one blocker entry; collapse unknown codes."""
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
    if not isinstance(code, Task028BlockerCode):
        code = Task028BlockerCode.BL_T028_RAW_INPUT_BOUNDARY_MALFORMED
    entry = Task028BlockerEntry(
        code=code,
        field_path=field_path_tuple,
        message_key=message_key,
        evidence_refs=evidence_refs_tuple,
    )
    return _Task028PendingBlocker(entry=entry, component_id_tiebreaker=component_id_tiebreaker)


def collapse_blockers(
    pending: list[_Task028PendingBlocker],
) -> tuple[Task028BlockerEntry, ...]:
    """§12 — Sort and deduplicate pending blockers by (registry ordinal, field_path, component_id_tiebreaker)."""

    def _ordering_key(p: _Task028PendingBlocker) -> tuple[int, tuple[str, ...], str]:
        ordinal = _BLOCKER_REGISTRY.get(p.entry.code, 999)
        return (ordinal, p.entry.field_path, p.component_id_tiebreaker)

    sorted_pending = sorted(pending, key=_ordering_key)
    seen: set[tuple[Task028BlockerCode, tuple[str, ...], str]] = set()
    unique: list[Task028BlockerEntry] = []
    for p in sorted_pending:
        dedup_key = (p.entry.code, p.entry.field_path, p.component_id_tiebreaker)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        unique.append(p.entry)
    return tuple(unique)


__all__ = [
    "Task028BlockerCode",
    "Task028BlockerEntry",
    "_Task028PendingBlocker",
    "emit_blocker",
    "collapse_blockers",
    "BLOCKER_REGISTRY_COUNT",
    "BLOCKER_REGISTRY",
]
