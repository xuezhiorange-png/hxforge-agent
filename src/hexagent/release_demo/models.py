"""Immutable data containers used by the TASK036 release-demo pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, TypeAlias


class ValidationStatus(StrEnum):
    VALID = "VALID"
    BLOCKED = "BLOCKED"


JsonRecord: TypeAlias = dict[str, Any]


@dataclass(frozen=True)
class Task036DemoInput:
    TASK031_RAW_REQUEST_RECORD: JsonRecord
    TASK032_PROPERTY_SNAPSHOT_RECORD: JsonRecord
    TASK032_MASS_FLOW_AUTHORITY_RECORD: JsonRecord
    TASK032_REQUEST_EVIDENCE_REFS: tuple[str, ...]
    TASK033_REQUEST_EVIDENCE_REFS: tuple[str, ...]
    TASK034_SHELL_TYPE_AUTHORITY_RECORD: JsonRecord
    TASK034_WALL_PROPERTY_AUTHORITY_RECORD: JsonRecord
    TASK034_REQUEST_EVIDENCE_REFS: tuple[str, ...]
    TASK035_EVIDENCE_REFS: tuple[str, ...]


@dataclass(frozen=True)
class Task036SuccessResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    demo_id: str
    release_version: str
    source_commit: str
    source_tree: str
    task031_status: str
    task032_status: str
    task033_status: str
    task034_status: str
    task035_status: str
    task034_request_hash: str
    task034_result_hash: str
    task034_result_id: str
    task035_request_hash: str
    task035_result_hash: str
    task035_result_id: str
    release_acceptance_ledger: JsonRecord
    upstream_evidence_ledger: JsonRecord
    determinism_evidence: JsonRecord
    artifact_manifest_digest: str
    version_metadata_digest: str
    acceptance_checklist: JsonRecord
    provenance: JsonRecord
    request_hash: str
    result_hash: str
    result_id: str
    warnings: tuple[str, ...]
    blockers: tuple[Any, ...]
    deferred_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class Task036TypedBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    demo_id: str
    release_version: str
    failure_stage: str
    source_commit: str
    source_tree: str
    task031_status: str
    task032_status: str
    task033_status: str
    task034_status: str
    task035_status: str
    task034_request_hash: str | None
    task034_result_hash: str | None
    task034_result_id: str | None
    task035_request_hash: str | None
    task035_result_hash: str | None
    task035_result_id: str | None
    request_hash: str | None
    blocked_result_hash: str
    result_id: str
    blockers: tuple[Any, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]
    upstream_evidence: JsonRecord
    provenance: JsonRecord


@dataclass(frozen=True)
class Task036RawBoundaryBlockedResult:
    schema_version: str
    profile_id: str
    implementation_software_version: str
    raw_request_projection: JsonRecord
    blocked_result_hash: str
    blockers: tuple[Any, ...]
    warnings: tuple[str, ...]
    deferred_capabilities: tuple[str, ...]


@dataclass(frozen=True)
class Task036ValidationResult:
    status: ValidationStatus
    success_result: Task036SuccessResult | None = None
    blocked_result: Task036TypedBlockedResult | None = None
    raw_boundary_blocked_result: Task036RawBoundaryBlockedResult | None = None
    stages: tuple[str, ...] = ()

    @property
    def result(
        self,
    ) -> Task036SuccessResult | Task036TypedBlockedResult | Task036RawBoundaryBlockedResult | None:
        return self.success_result or self.blocked_result or self.raw_boundary_blocked_result


@dataclass(frozen=True)
class Task036Run:
    """All internal nodes required to render the six frozen release artifacts."""

    demo_input: JsonRecord
    task031_request: JsonRecord
    task031_result: JsonRecord
    task032_request: JsonRecord
    task032_result: JsonRecord
    task033_request: JsonRecord
    task033_result: JsonRecord
    task034_request: JsonRecord
    task034_result: JsonRecord
    task035_request: JsonRecord
    task035_result: JsonRecord
    graph_evidence: JsonRecord
    upstream_evidence_ledger: JsonRecord
    blocked_cases: tuple[JsonRecord, ...]
    identity_core: JsonRecord
    cross_runtime_determinism: JsonRecord
    repeat_run_determinism: JsonRecord
    acceptance_checklist: JsonRecord
    manifest: JsonRecord
    release_acceptance_ledger: JsonRecord
    provenance: JsonRecord
    version_metadata: JsonRecord
    final_result: JsonRecord
    artifact_bytes: dict[str, bytes]


__all__ = [
    "JsonRecord",
    "Task036DemoInput",
    "Task036RawBoundaryBlockedResult",
    "Task036Run",
    "Task036SuccessResult",
    "Task036TypedBlockedResult",
    "Task036ValidationResult",
    "ValidationStatus",
]
