"""Immutable public models for the TASK039 release boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeAlias


class ValidationStatus(StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


JsonRecord: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class Task039Request:
    """Typed TASK039 request carrying the actual TASK038 success result."""

    schema_version: str
    profile_id: str
    task038_result: Any
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class Task039SuccessResult:
    schema_version: str
    profile_id: str
    release_version: str
    source_definition_issue: int
    source_definition_revision: str
    allocation_issue: int
    allocation_revision: str
    base_main_sha: str
    base_main_tree: str
    task038_merge_commit: str
    task038_post_merge_main_ci_run: str
    historical_release_authority: JsonRecord
    production_graph_hash: str
    success_demo_hash: str
    blocked_demo_hashes: tuple[str, ...]
    artifact_manifest_hash: str
    version_metadata_hash: str
    determinism_evidence_hash: str
    acceptance_checklist_hash: str
    release_acceptance_ledger: JsonRecord
    warnings: tuple[Any, ...]
    blockers: tuple[Any, ...]
    provenance: JsonRecord
    result_hash: str
    result_id: str


@dataclass(frozen=True)
class Task039TypedBlockedResult:
    schema_version: str
    profile_id: str
    release_version: str
    failure_stage: str
    blocker_code: str
    field_path: str
    reason: str
    blocked_result_hash: str
    result_id: str
    warnings: tuple[Any, ...] = ()
    blockers: tuple[Any, ...] = ()
    provenance: JsonRecord | None = None


@dataclass(frozen=True)
class Task039RawBoundaryBlockedResult:
    schema_version: str
    profile_id: str
    raw_request_projection: Any
    blocker_code: str
    field_path: str
    blocked_result_hash: str
    result_id: str


@dataclass(frozen=True)
class Task039ValidationResult:
    status: ValidationStatus
    success_result: Task039SuccessResult | None = None
    blocked_result: Task039TypedBlockedResult | None = None
    raw_boundary_blocked_result: Task039RawBoundaryBlockedResult | None = None
    stages: tuple[str, ...] = ()

    @property
    def result(
        self,
    ) -> Task039SuccessResult | Task039TypedBlockedResult | Task039RawBoundaryBlockedResult | None:
        return self.success_result or self.blocked_result or self.raw_boundary_blocked_result

    @property
    def blockers(self) -> tuple[Any, ...]:
        result = self.result
        if result is None:
            return ()
        return tuple(getattr(result, "blockers", ()))


@dataclass(frozen=True)
class Task039Run:
    """Complete deterministic release-evidence graph and its six artifacts."""

    task020_result: Any
    task021_result: Any
    task025_result: Any
    task026_result: Any
    task031_result: Any
    task032_result: Any
    task033_result: Any
    task034_result: Any
    task035_result: Any
    task037_result: Any
    task038_request: Any
    task038_result: Any
    production_graph: JsonRecord
    success_demo: JsonRecord
    blocked_demos: tuple[JsonRecord, ...]
    historical_release_authority: JsonRecord
    version_metadata: JsonRecord
    determinism_evidence: JsonRecord
    acceptance_checklist: JsonRecord
    release_acceptance_ledger: JsonRecord
    provenance: JsonRecord
    manifest: JsonRecord
    final_result: JsonRecord
    artifact_bytes: dict[str, bytes] = field(default_factory=dict)


__all__ = [
    "JsonRecord",
    "Task039RawBoundaryBlockedResult",
    "Task039Request",
    "Task039Run",
    "Task039SuccessResult",
    "Task039TypedBlockedResult",
    "Task039ValidationResult",
    "ValidationStatus",
]
