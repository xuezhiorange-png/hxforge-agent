"""Fail-closed TASK039 release-level validation entry point."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.overall_heat_transfer_coefficient_ua import (
    verify_task038_success_identity,
)

from .canonical import sha256_bytes
from .models import (
    Task039RawBoundaryBlockedResult,
    Task039Request,
    Task039SuccessResult,
    Task039TypedBlockedResult,
    Task039ValidationResult,
    ValidationStatus,
)
from .schema import (
    PROFILE_ID,
    RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION,
    RELEASE_EVIDENCE_SCHEMA_VERSION,
    RELEASE_VERSION,
)


def _blocked_hash(code: str, stage: str, field_path: str, reason: str) -> str:
    return sha256_bytes("|".join((code, stage, field_path, reason)).encode("utf-8"))


def _typed_blocked(code: str, stage: str, field_path: str, reason: str) -> Task039ValidationResult:
    blocked_hash = _blocked_hash(code, stage, field_path, reason)
    result = Task039TypedBlockedResult(
        schema_version="task039.typed-blocked-result.v1",
        profile_id=PROFILE_ID,
        release_version=RELEASE_VERSION,
        failure_stage=stage,
        blocker_code=code,
        field_path=field_path,
        reason=reason,
        blocked_result_hash=blocked_hash,
        result_id=blocked_hash,
        blockers=(
            {
                "code": code,
                "stage": stage,
                "field_path": field_path,
                "reason": reason,
            },
        ),
    )
    return Task039ValidationResult(
        status=ValidationStatus.BLOCKED,
        blocked_result=result,
        stages=(stage,),
    )


def _raw_boundary_blocked(raw: object) -> Task039ValidationResult:
    projection = {"type": type(raw).__name__}
    blocked_hash = _blocked_hash(
        "BL_RAW_INPUT_BOUNDARY_MALFORMED", "S00_RAW_INPUT_BOUNDARY", "raw_input", type(raw).__name__
    )
    result = Task039RawBoundaryBlockedResult(
        schema_version="task039.raw-boundary-blocked-result.v1",
        profile_id=PROFILE_ID,
        raw_request_projection=projection,
        blocker_code="BL_RAW_INPUT_BOUNDARY_MALFORMED",
        field_path="raw_input",
        blocked_result_hash=blocked_hash,
        result_id=blocked_hash,
    )
    return Task039ValidationResult(
        status=ValidationStatus.BLOCKED,
        raw_boundary_blocked_result=result,
        stages=("S00_RAW_INPUT_BOUNDARY",),
    )


def validate_request(raw_request: Any) -> Task039ValidationResult:
    """Validate one typed Task039 request and run the real release graph."""

    if type(raw_request) is not Task039Request:
        return _raw_boundary_blocked(raw_request)
    if (
        raw_request.schema_version != RELEASE_EVIDENCE_SCHEMA_VERSION
        or raw_request.profile_id != PROFILE_ID
        or type(raw_request.evidence_refs) is not tuple
        or not all(type(item) is str and item for item in raw_request.evidence_refs)
    ):
        return _typed_blocked(
            "T039_REQUEST_SCHEMA_INVALID",
            "S01_REQUEST_AND_AUTHORITY_SCHEMA",
            "request",
            "request_schema_invalid",
        )
    if not verify_task038_success_identity(raw_request.task038_result):
        return _typed_blocked(
            "BL_TASK038_RESULT_INVALID",
            "S01_REQUEST_AND_AUTHORITY_SCHEMA",
            "task038_result",
            "task038_result_identity_invalid",
        )
    try:
        from .task039 import build_release_run

        run = build_release_run()
        if not verify_task038_success_identity(run.task038_result.success_result):
            return _typed_blocked(
                "BL_TASK038_RESULT_INVALID",
                "S03_TASK038_RESULT_REPLAY",
                "task038_result",
                "actual_task038_replay_invalid",
            )
        result_record = run.final_result
        success = Task039SuccessResult(
            schema_version=str(result_record["schema_version"]),
            profile_id=str(result_record["profile_id"]),
            release_version=str(result_record["release_version"]),
            source_definition_issue=int(result_record["source_definition_issue"]),
            source_definition_revision=str(result_record["source_definition_revision"]),
            allocation_issue=int(result_record["allocation_issue"]),
            allocation_revision=str(result_record["allocation_revision"]),
            base_main_sha=str(result_record["base_main_sha"]),
            base_main_tree=str(result_record["base_main_tree"]),
            task038_merge_commit=str(result_record["task038_merge_commit"]),
            task038_post_merge_main_ci_run=str(result_record["task038_post_merge_main_ci_run"]),
            historical_release_authority=dict(result_record["historical_release_authority"]),
            production_graph_hash=str(result_record["production_graph_hash"]),
            success_demo_hash=str(result_record["success_demo_hash"]),
            blocked_demo_hashes=tuple(result_record["blocked_demo_hashes"]),
            artifact_manifest_hash=str(result_record["artifact_manifest_hash"]),
            version_metadata_hash=str(result_record["version_metadata_hash"]),
            determinism_evidence_hash=str(result_record["determinism_evidence_hash"]),
            acceptance_checklist_hash=str(result_record["acceptance_checklist_hash"]),
            release_acceptance_ledger=dict(result_record["release_acceptance_ledger"]),
            warnings=tuple(result_record["warnings"]),
            blockers=tuple(result_record["blockers"]),
            provenance=dict(result_record["provenance"]),
            result_hash=str(result_record["result_hash"]),
            result_id=str(result_record["result_id"]),
        )
        return Task039ValidationResult(
            status=ValidationStatus.VALID,
            success_result=success,
            stages=(
                "S00_RAW_INPUT_BOUNDARY",
                "S01_REQUEST_AND_AUTHORITY_SCHEMA",
                "S19_RESULT_HASH_UUID_FINALIZATION",
            ),
        )
    except Exception as exc:
        return _typed_blocked(
            "T039_IMPLEMENTATION_FAILURE",
            "S19_RESULT_HASH_UUID_FINALIZATION",
            "release_evidence",
            f"{type(exc).__name__}:{exc}",
        )


def verify_release_identity(record: Any) -> bool:
    if not isinstance(record, Task039SuccessResult):
        return False
    if record.schema_version != RELEASE_ACCEPTANCE_RESULT_SCHEMA_VERSION:
        return False
    return bool(record.result_hash and record.result_id)


__all__ = ["validate_request", "verify_release_identity"]
