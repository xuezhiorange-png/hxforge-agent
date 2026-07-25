"""TASK-025 blocked result schema.

§6.3 — Task025BlockedResult exact public field tuple and types.
§6.4 — Unique blocked_result_hash projection.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hexagent.exchangers.shell_tube.tube_side.blocker_registry import Task025BlockerEntry
from hexagent.exchangers.shell_tube.tube_side.provenance import (
    FrozenIdentity,
    FrozenProvenance,
    FrozenRawProjection,
)

# §6.3 — TASK025_BLOCKED_RESULT_FIELDS tuple.
TASK025_BLOCKED_RESULT_FIELDS: tuple[str, ...] = (
    "schema_version",
    "implementation_software_version",
    "resolved_profile_id",
    "raw_profile_id_projection",
    "raw_request_projection",
    "request_hash",
    "blocked_result_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "stage_rank",
    "task020_identity",
    "task021_identity",
    "provenance",
)


# §6.4 — BLOCKED_RESULT_HASH_FIELDS projection.
BLOCKED_RESULT_HASH_FIELDS: tuple[str, ...] = (
    "schema_version",
    "implementation_software_version",
    "resolved_profile_id",
    "raw_profile_id_projection",
    "raw_request_projection",
    "request_hash",
    "blockers",
    "warnings",
    "deferred_capabilities",
    "stage_rank",
    "task020_identity",
    "task021_identity",
)


_HEX_DIGITS: frozenset[str] = frozenset("0123456789abcdef")


def _validate_hash(value: Any, field_path: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field_path} must be a 64-character string")
    if any(c not in _HEX_DIGITS for c in value):
        raise ValueError(f"{field_path} must be lowercase hexadecimal")


@dataclass(frozen=True)
class Task025BlockedResult:
    """§6.3 — TASK-025 unique blocked-result value object."""

    schema_version: str
    implementation_software_version: str
    resolved_profile_id: str | None
    raw_profile_id_projection: FrozenRawProjection
    raw_request_projection: FrozenRawProjection
    request_hash: str | None
    blocked_result_hash: str
    blockers: tuple[Task025BlockerEntry, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    stage_rank: int
    task020_identity: FrozenIdentity | None
    task021_identity: FrozenIdentity | None
    provenance: FrozenProvenance

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or self.schema_version != "task025.blocked-result.v1":
            raise ValueError(
                f"schema_version must be 'task025.blocked-result.v1'; got {self.schema_version!r}"
            )
        if not isinstance(self.implementation_software_version, str):
            raise ValueError("implementation_software_version must be str")
        if not isinstance(self.resolved_profile_id, (str, type(None))):
            raise ValueError("resolved_profile_id must be str or None")
        if not isinstance(self.raw_profile_id_projection, FrozenRawProjection):
            raise ValueError("raw_profile_id_projection must be FrozenRawProjection")
        if not isinstance(self.raw_request_projection, FrozenRawProjection):
            raise ValueError("raw_request_projection must be FrozenRawProjection")
        if not isinstance(self.request_hash, (str, type(None))):
            raise ValueError("request_hash must be str or None")
        elif isinstance(self.request_hash, str):
            _validate_hash(self.request_hash, "request_hash")
        _validate_hash(self.blocked_result_hash, "blocked_result_hash")
        if not isinstance(self.blockers, tuple):
            raise ValueError("blockers must be a tuple of Task025BlockerEntry")
        for entry in self.blockers:
            if not isinstance(entry, Task025BlockerEntry):
                raise ValueError(
                    f"blockers entries must be Task025BlockerEntry; got {type(entry).__name__}"
                )
        if not isinstance(self.warnings, tuple) or self.warnings != ():
            raise ValueError("v1 blocked result warnings must be ()")
        if not isinstance(self.deferred_capabilities, tuple):
            raise ValueError("deferred_capabilities must be tuple of str")
        if not isinstance(self.stage_rank, int):
            raise ValueError("stage_rank must be int")
        if not isinstance(self.task020_identity, (FrozenIdentity, type(None))):
            raise ValueError("task020_identity must be FrozenIdentity or None")
        if not isinstance(self.task021_identity, (FrozenIdentity, type(None))):
            raise ValueError("task021_identity must be FrozenIdentity or None")
        if not isinstance(self.provenance, FrozenProvenance):
            raise ValueError("provenance must be FrozenProvenance")


__all__ = [
    "Task025BlockedResult",
    "TASK025_BLOCKED_RESULT_FIELDS",
    "BLOCKED_RESULT_HASH_FIELDS",
]

# ruff: noqa: E501
