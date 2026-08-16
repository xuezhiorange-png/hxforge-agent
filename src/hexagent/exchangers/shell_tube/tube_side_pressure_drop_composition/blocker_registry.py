"""TASK-029 closed 43-code blocker registry, emit, and deterministic collapse.

I06 scope only: registry identity, ``emit_blocker()``, and ``collapse_blockers()``.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.enums import (
    Task029BlockerCode,
)
from hexagent.exchangers.shell_tube.tube_side_pressure_drop_composition.models import (
    Task029BlockerEntry,
)

# Frozen registry ordinal order (00..42) per design contract §13 / T029_BL_000..042.
TASK029_BLOCKER_REGISTRY: Final[tuple[Task029BlockerCode, ...]] = (
    Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD,
    Task029BlockerCode.BL_T029_RAW_INPUT_BOUNDARY_MALFORMED,
    Task029BlockerCode.BL_T029_REQUIRED_FIELD_MISSING,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RAW_BLOCKED,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPED_BLOCKED,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RAW_BLOCKED,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPED_BLOCKED,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK027_TYPE_INVALID,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK028_TYPE_INVALID,
    Task029BlockerCode.BL_T029_UPSTREAM_SCHEMA_VERSION_UNSUPPORTED,
    Task029BlockerCode.BL_T029_UPSTREAM_IDENTITY_MISMATCH,
    Task029BlockerCode.BL_T029_PROFILE_MISMATCH,
    Task029BlockerCode.BL_T029_FLOW_DIRECTION_MISMATCH,
    Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MISSING,
    Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_MALFORMED,
    Task029BlockerCode.BL_T029_COMPOSITION_AUTHORITY_HASH_MISMATCH,
    Task029BlockerCode.BL_T029_COMPOSITION_MEMBER_AUTHORITY_HASH_MISMATCH,
    Task029BlockerCode.BL_T029_REQUEST_HASH_MISMATCH,
    Task029BlockerCode.BL_T029_MODELED_PATH_BOUNDARY_INVALID,
    Task029BlockerCode.BL_T029_EMPTY_MODELED_PATH,
    Task029BlockerCode.BL_T029_EXPECTED_MEMBER_MISSING,
    Task029BlockerCode.BL_T029_UNEXPECTED_EXTRA_MEMBER,
    Task029BlockerCode.BL_T029_DUPLICATE_MEMBER,
    Task029BlockerCode.BL_T029_OUT_OF_ORDER_MEMBER,
    Task029BlockerCode.BL_T029_OVERLAPPING_PATH_SEGMENT,
    Task029BlockerCode.BL_T029_REFERENCE_PLANE_DISCONTINUITY,
    Task029BlockerCode.BL_T029_REFERENCE_PLANE_SELF_LOOP,
    Task029BlockerCode.BL_T029_PATH_CYCLE,
    Task029BlockerCode.BL_T029_PATH_FORK,
    Task029BlockerCode.BL_T029_PATH_JOIN,
    Task029BlockerCode.BL_T029_MULTIPLICITY_INCOMPATIBILITY,
    Task029BlockerCode.BL_T029_PRODUCER_CONVENTION_MISMATCH,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK027_RESULT_IDENTITY_INVALID,
    Task029BlockerCode.BL_T029_UPSTREAM_TASK028_RESULT_IDENTITY_INVALID,
    Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONFINITE,
    Task029BlockerCode.BL_T029_PRESSURE_CONTRIBUTION_NONPOSITIVE,
    Task029BlockerCode.BL_T029_PRESSURE_QUANTUM_MISMATCH,
    Task029BlockerCode.BL_T029_EXCLUSION_AUTHORITY_INVALID,
    Task029BlockerCode.BL_T029_EXCLUSION_EVIDENCE_MISSING,
    Task029BlockerCode.BL_T029_COMPLETENESS_LEDGER_INCOMPLETE,
    Task029BlockerCode.BL_T029_PARTIAL_RESULT_FORBIDDEN,
    Task029BlockerCode.BL_T029_ARITHMETIC_FAILURE,
    Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY,
)

BLOCKER_REGISTRY_COUNT: Final[int] = len(TASK029_BLOCKER_REGISTRY)

REGISTRY_INDEX_BY_CODE: Final[dict[Task029BlockerCode, int]] = {
    code: index for index, code in enumerate(TASK029_BLOCKER_REGISTRY)
}

BLOCKER_MESSAGE_MAP: Final[dict[Task029BlockerCode, str]] = {
    code: code.value for code in TASK029_BLOCKER_REGISTRY
}

assert len(Task029BlockerCode.__members__) == BLOCKER_REGISTRY_COUNT
assert len(TASK029_BLOCKER_REGISTRY) == BLOCKER_REGISTRY_COUNT
assert len(set(TASK029_BLOCKER_REGISTRY)) == BLOCKER_REGISTRY_COUNT
assert set(TASK029_BLOCKER_REGISTRY) == set(Task029BlockerCode)
assert TASK029_BLOCKER_REGISTRY[0] == Task029BlockerCode.BL_T029_REQUEST_UNKNOWN_FIELD
assert (
    TASK029_BLOCKER_REGISTRY[42] == Task029BlockerCode.BL_T029_UPSTREAM_SUCCESS_DIAGNOSTICS_NONEMPTY
)
assert all(BLOCKER_MESSAGE_MAP[code] == code.value for code in TASK029_BLOCKER_REGISTRY)


def _field_path_utf8_key(field_path: str) -> bytes:
    return field_path.encode("utf-8")


def _evidence_refs_tuple_lexical_key(evidence_refs: tuple[str, ...]) -> tuple[bytes, ...]:
    return tuple(ref.encode("utf-8") for ref in evidence_refs)


def _collapse_order_key(entry: Task029BlockerEntry) -> tuple[int, bytes, tuple[bytes, ...]]:
    return (
        REGISTRY_INDEX_BY_CODE[entry.code],
        _field_path_utf8_key(entry.field_path),
        _evidence_refs_tuple_lexical_key(entry.evidence_refs),
    )


def _dedup_key(entry: Task029BlockerEntry) -> tuple[Task029BlockerCode, str, tuple[str, ...]]:
    return (entry.code, entry.field_path, entry.evidence_refs)


def emit_blocker(
    code: Task029BlockerCode,
    field_path: str,
    evidence_refs: tuple[str, ...] | list[str] = (),
) -> Task029BlockerEntry:
    """Construct one frozen blocker entry with ``message_key == code``."""
    if not isinstance(field_path, str):
        raise TypeError("field_path must be a single exact STRING")
    if isinstance(evidence_refs, list):
        evidence_refs_tuple: tuple[str, ...] = tuple(evidence_refs)
    else:
        evidence_refs_tuple = evidence_refs
    return Task029BlockerEntry(
        code=code,
        field_path=field_path,
        message_key=BLOCKER_MESSAGE_MAP[code],
        evidence_refs=evidence_refs_tuple,
    )


def collapse_blockers(
    blockers: Sequence[Task029BlockerEntry],
) -> tuple[Task029BlockerEntry, ...]:
    """Deduplicate and order blockers by frozen registry collapse rules."""
    seen: set[tuple[Task029BlockerCode, str, tuple[str, ...]]] = set()
    unique: list[Task029BlockerEntry] = []
    for entry in blockers:
        key = _dedup_key(entry)
        if key in seen:
            continue
        seen.add(key)
        unique.append(entry)
    return tuple(sorted(unique, key=_collapse_order_key))


__all__ = [
    "TASK029_BLOCKER_REGISTRY",
    "BLOCKER_REGISTRY_COUNT",
    "REGISTRY_INDEX_BY_CODE",
    "BLOCKER_MESSAGE_MAP",
    "emit_blocker",
    "collapse_blockers",
]
