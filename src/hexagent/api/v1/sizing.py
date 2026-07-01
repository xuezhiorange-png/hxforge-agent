"""TASK-010 sizing endpoint.

Contract: POST /v1/double-pipe/sizing → operation_id=sizeDoublePipe
Request: SizingApiRequest
Response: SizingRunEnvelope
Idempotency required.

P0-1: prepare() runs BEFORE idempotency claim; execute() runs AFTER.
A1: SizingRunArtifacts uses fully typed fields.
A2: Authoritative verification called after build_optimization_result.
A4/A5: Bundle and envelope verifiers called.
C5: FrozenFailurePayload used for exact FAILED_REPLAY.
"""

from __future__ import annotations

import hashlib
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from hexagent.api.application import (
    SizingApplicationService,
)
from hexagent.api.artifacts import (
    SizingRunArtifacts,
    compute_sizing_artifact_bundle_digest,
)
from hexagent.api.canonical_request import (
    compute_idempotency_namespace_digest,
)
from hexagent.api.envelopes import ReportLinks, SizingRunEnvelope
from hexagent.api.errors import ApiError, ApiErrorCode
from hexagent.api.models import SizingApiRequest
from hexagent.api.repository import (
    ClaimOutcome,
    FrozenFailurePayload,
    IdempotencyConflictError,
    RunRecord,
    RunRepository,
)

router = APIRouter(prefix="/v1/double-pipe", tags=["sizing"])


def _validate_idempotency_key(key: str) -> str:
    """Validate Idempotency-Key header per contract §7.2."""
    key = key.strip()
    if not key:
        raise ValueError("Idempotency-Key must not be empty")
    if len(key) > 128:
        raise ValueError("Idempotency-Key must be ≤ 128 characters")
    for ch in key:
        if ord(ch) < 0x20 or ord(ch) > 0x7E:
            raise ValueError("Idempotency-Key must contain only printable ASCII")
    return key


@router.post(
    "/sizing",
    operation_id="sizeDoublePipe",
    response_model=SizingRunEnvelope,
    responses={
        422: {"model": ApiError},
        409: {"model": ApiError},
        500: {"model": ApiError},
    },
)
async def size_double_pipe(
    request: Request,
    body: SizingApiRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> Any:
    """Execute a sizing request with idempotency protection.

    Execution chain per contract §4.3:
    1. Validate public DTO
    2-5. prepare() → projection (provider, catalogs, identity, digest)
    6. Claim idempotency namespace
    7. execute() → full optimization pipeline (A2: with verification)
    8. Build typed SizingRunArtifacts (A1)
    9. Build typed SizingRunEnvelope (A5)
    10. Repository complete (C4: full parity)
    """
    deps = request.app.state.deps
    repo: RunRepository = deps.run_repository
    sizing_app: SizingApplicationService = deps.sizing_application_service

    # 1. Validate Idempotency-Key
    try:  # noqa: SIM105
        idempotency_key = _validate_idempotency_key(idempotency_key)
    except ValueError:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message="Invalid idempotency key",
            operation="sizeDoublePipe",
        )

    # 2-5. Full projection via prepare
    try:  # noqa: SIM105
        prepared = sizing_app.prepare(body)
    except ValueError:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message="Validation failed",
            operation="sizeDoublePipe",
        )

    service_result = prepared.service_result
    request_digest = service_result.request_digest

    # 6. Compute idempotency namespace
    key_digest = hashlib.sha256(idempotency_key.encode("ascii")).hexdigest()
    namespace_digest = compute_idempotency_namespace_digest(
        api_schema_version="1",
        operation_id="sizeDoublePipe",
        idempotency_key_digest=key_digest,
    )

    # 7. Claim idempotency namespace
    try:  # noqa: SIM105
        claim = repo.claim(
            namespace_digest=namespace_digest,
            request_digest=request_digest,
            operation="sizeDoublePipe",
        )
    except IdempotencyConflictError:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Idempotency conflict",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    record = claim.record

    # 8. Handle claim outcomes
    if claim.outcome == ClaimOutcome.COMPLETE_REPLAY:
        return JSONResponse(
            status_code=200,
            content=record.envelope.model_dump(mode="json") if record.envelope else {},
        )

    if claim.outcome == ClaimOutcome.IN_PROGRESS:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Sizing is already in progress",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    if claim.outcome == ClaimOutcome.STALE_REJECTED:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Previous run is stale",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    if claim.outcome == ClaimOutcome.FAILED_REPLAY:
        # C5: Return the exact stored failure — NOT 200
        if record.failure is not None and isinstance(record.failure, FrozenFailurePayload):
            return _error_response(
                status_code=record.failure.status_code,
                error_code=record.failure.error_code,
                error_message=record.failure.error_message,
                operation=record.failure.operation,
                request_digest=record.failure.request_digest,
            )
        # Fallback: return 500 with stable message
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Previous execution failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    # NEW_CLAIM or STALE_TAKEOVER → execute
    owner_token = record.owner_token

    # 9. Start run
    try:
        record = repo.start(
            owner_token=owner_token,
            expected_version=record.record_version,
        )
    except Exception:
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Failed to start run",
            operation="sizeDoublePipe",
        )

    # 10. Execute sizing optimization (A2: includes verification)
    try:
        exec_result = sizing_app.execute(prepared)
    except Exception:
        _store_failure(
            repo,
            owner_token,
            record,
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Sizing execution failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Sizing execution failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    # 11. Build typed artifact bundle (A1)
    try:
        # First pass: model_construct bypasses validators to compute digest
        _bundle_fields = dict(
            canonical_request_snapshot=service_result.canonical_request_snapshot,
            sizing_request=service_result.sizing_request,
            evaluation_input=exec_result.evaluation_input,
            phase3_authoritative_artifacts=exec_result.phase3_authoritative_artifacts,
            dispositions=exec_result.dispositions,
            ranked_records=exec_result.ranked_records,
            top_n_records=exec_result.top_n_records,
            optimization_result=exec_result.optimization_result,
            provenance_graph=exec_result.provenance,
            artifact_bundle_digest="",
        )
        _draft = SizingRunArtifacts.model_construct(**_bundle_fields)  # type: ignore[arg-type]
        bundle_digest = compute_sizing_artifact_bundle_digest(_draft)

        bundle = SizingRunArtifacts(
            **{**_bundle_fields, "artifact_bundle_digest": bundle_digest},  # type: ignore[arg-type]
        )
    except Exception:
        _store_failure(
            repo,
            owner_token,
            record,
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Artifact bundle construction failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Artifact bundle construction failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    # 12. Build typed envelope (A5)
    try:
        envelope = SizingRunEnvelope(
            api_schema_version="1",
            operation="sizeDoublePipe",
            run_id=record.run_id,
            idempotency_key_digest=key_digest,
            request_digest=request_digest,
            result_kind="sizing",
            result=exec_result.optimization_result,
            result_hash=exec_result.optimization_result.result_hash,
            # A3: real warnings/blockers from evaluation records
            warnings=exec_result.warnings,
            blockers=exec_result.blockers,
            failure=None,
            provenance=exec_result.provenance,
            # C2: single provenance digest authority
            provenance_digest=exec_result.optimization_result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle_digest,
            report_links=ReportLinks(html=f"/v1/runs/{record.run_id}/report.html"),
        )
    except Exception:
        _store_failure(
            repo,
            owner_token,
            record,
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    # 13. Repository complete (C4: full parity)
    try:
        record = repo.complete(
            owner_token=owner_token,
            expected_version=record.record_version,
            envelope=envelope,
            artifact_bundle=bundle,
        )
    except Exception:
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Repository completion failed",
            operation="sizeDoublePipe",
            request_digest=request_digest,
        )

    return JSONResponse(
        status_code=200,
        content=envelope.model_dump(mode="json"),
    )


def _store_failure(
    repo: RunRepository,
    owner_token: UUID,
    record: RunRecord,
    *,
    status_code: int,
    error_code: str,
    error_message: str,
    operation: str,
    request_digest: str | None,
) -> None:
    """Store exact failure payload for FAILED_REPLAY (C5)."""
    import contextlib

    with contextlib.suppress(Exception):
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=FrozenFailurePayload(
                status_code=status_code,
                error_code=error_code,
                error_message=error_message,
                request_digest=request_digest,
                operation=operation,
            ),
        )


def _error_response(
    *,
    status_code: int,
    error_code: str,
    error_message: str,
    operation: str,
    request_digest: str | None = None,
) -> JSONResponse:
    api_error = ApiError(
        api_schema_version="1",
        operation=operation,
        status_code=status_code,
        error_code=error_code,
        error_message=error_message,
        request_digest=request_digest,
        details=(),
    )
    return JSONResponse(
        status_code=status_code,
        content=api_error.model_dump(mode="json"),
    )
