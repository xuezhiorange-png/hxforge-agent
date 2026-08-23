"""Closed TASK-032 blocker registry and deterministic ordering."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

from .models import BlockerCode, BlockerEntry

TASK032_BLOCKER_REGISTRY: tuple[str, ...] = tuple(code.value for code in BlockerCode)
TASK032_BLOCKER_CODE_COUNT = 33
TASK032_REACHABLE_BLOCKERS: tuple[str, ...] = tuple(
    code for code in TASK032_BLOCKER_REGISTRY if code != BlockerCode.SSFS_PARTIAL_RESULT_FORBIDDEN
)
TASK032_DEFENSIVE_BLOCKERS = (BlockerCode.SSFS_PARTIAL_RESULT_FORBIDDEN.value,)
TASK032_REACHABLE_BLOCKER_COUNT = 32
TASK032_DEFENSIVE_BLOCKER_COUNT = 1

TASK032_BLOCKER_EARLIEST_STAGE: dict[str, str] = {
    "SSFS_SCHEMA_VERSION_UNSUPPORTED": "S01",
    "SSFS_PROFILE_ID_UNSUPPORTED": "S01",
    "SSFS_RAW_TYPE_INVALID": "S00",
    "SSFS_UNKNOWN_FIELD": "S01",
    "SSFS_DECIMAL_LEXICAL_INVALID": "S01",
    "SSFS_EVIDENCE_REFS_INVALID": "S01",
    "SSFS_TASK031_RESULT_MISSING": "S01",
    "SSFS_TASK031_RESULT_INVALID": "S02",
    "SSFS_TASK031_RESULT_HAS_BLOCKERS": "S02",
    "SSFS_TASK031_GEOMETRY_MISSING": "S02",
    "SSFS_TASK031_IDENTITY_MISMATCH": "S02",
    "SSFS_PROPERTY_SNAPSHOT_MISSING": "S01",
    "SSFS_PROPERTY_SNAPSHOT_INVALID": "S03",
    "SSFS_PROPERTY_SNAPSHOT_HASH_MISMATCH": "S03",
    "SSFS_MASS_FLOW_AUTHORITY_MISSING": "S01",
    "SSFS_MASS_FLOW_AUTHORITY_INVALID": "S04",
    "SSFS_MASS_FLOW_AUTHORITY_HASH_MISMATCH": "S04",
    "SSFS_SAME_CASE_BINDING_MISMATCH": "S05",
    "SSFS_PHASE_UNSUPPORTED": "S06",
    "SSFS_RHEOLOGY_MODEL_UNSUPPORTED": "S06",
    "SSFS_PROPERTY_STATE_ROLE_UNSUPPORTED": "S06",
    "SSFS_MASS_FLOW_NON_POSITIVE": "S04",
    "SSFS_FLOW_MODEL_UNSUPPORTED": "S06",
    "SSFS_ENGINEERING_AUTHORITY_IDENTITY_MISMATCH": "S07",
    "SSFS_FORMULA_DOMAIN_VIOLATION": "S06",
    "SSFS_FORMULA_CALCULATION_FAILED": "S08",
    "SSFS_PUBLIC_MASS_VELOCITY_QUANTIZATION_COLLISION": "S09",
    "SSFS_PUBLIC_BULK_VELOCITY_QUANTIZATION_COLLISION": "S09",
    "SSFS_PUBLIC_REYNOLDS_QUANTIZATION_COLLISION": "S09",
    "SSFS_PUBLIC_PRANDTL_QUANTIZATION_COLLISION": "S09",
    "SSFS_CANONICALIZATION_FAILED": "S11",
    "SSFS_RESULT_IDENTITY_FINALIZATION_FAILED": "S12",
    "SSFS_PARTIAL_RESULT_FORBIDDEN": "S10",
}


def _stage_rank(stage: str) -> int:
    try:
        return int(stage[1:])
    except (ValueError, IndexError):
        return 99


def _digest(value: Any) -> str:
    return hashlib.sha256(repr(value).encode("utf-8")).hexdigest()


def blocker_message_key(code: str) -> str:
    return code.lower()


def make_blocker(
    code: BlockerCode | str,
    *,
    stage: str | None = None,
    field_path: str | None = None,
    payload: Mapping[str, Any] | None = None,
    evidence_refs: Iterable[str] = (),
) -> BlockerEntry:
    token = code.value if isinstance(code, BlockerCode) else code
    actual_stage = stage or TASK032_BLOCKER_EARLIEST_STAGE[token]
    pairs = (
        () if payload is None else tuple((str(key), str(payload[key])) for key in sorted(payload))
    )
    return BlockerEntry(
        code=token,
        severity="hard",
        stage=actual_stage,
        field_path=field_path,
        message_key=blocker_message_key(token),
        payload=pairs,
        evidence_refs=tuple(sorted(set(evidence_refs))),
    )


def blocker_sort_key(entry: BlockerEntry) -> tuple[int, str, str, str, str, str]:
    return (
        _stage_rank(entry.stage),
        entry.code,
        entry.field_path or "",
        entry.message_key,
        _digest(entry.payload),
        _digest(entry.evidence_refs),
    )


def sort_blockers(entries: Iterable[BlockerEntry]) -> tuple[BlockerEntry, ...]:
    return tuple(sorted(entries, key=blocker_sort_key))


__all__ = [
    "TASK032_BLOCKER_CODE_COUNT",
    "TASK032_BLOCKER_EARLIEST_STAGE",
    "TASK032_BLOCKER_REGISTRY",
    "TASK032_DEFENSIVE_BLOCKER_COUNT",
    "TASK032_DEFENSIVE_BLOCKERS",
    "TASK032_REACHABLE_BLOCKER_COUNT",
    "TASK032_REACHABLE_BLOCKERS",
    "blocker_message_key",
    "blocker_sort_key",
    "make_blocker",
    "sort_blockers",
]
