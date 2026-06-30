"""TASK-010 rating endpoint.

Contract: POST /v1/double-pipe/rating → operation_id=rateDoublePipe
Request: RatingApiRequest
Response: RatingRunEnvelope
Idempotency required.
"""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from hexagent.api.artifacts import RatingRunArtifacts, compute_bundle_hash
from hexagent.api.canonical_request import compute_idempotency_namespace_digest
from hexagent.api.envelopes import RatingRunEnvelope, ReportLinks
from hexagent.api.errors import ApiError, ApiErrorCode
from hexagent.api.models import RatingApiRequest
from hexagent.api.repository import (
    ClaimOutcome,
    IdempotencyConflictError,
    RunRepository,
)

router = APIRouter(prefix="/v1/double-pipe", tags=["rating"])


def _validate_idempotency_key(key: str) -> str:
    """Validate Idempotency-Key header per contract §7.2."""
    key = key.strip()
    if not key:
        raise ValueError("Idempotency-Key must not be empty")
    if len(key) > 128:
        raise ValueError("Idempotency-Key must be ≤ 128 characters")
    # Check printable ASCII
    for ch in key:
        if ord(ch) < 0x20 or ord(ch) > 0x7E:
            raise ValueError("Idempotency-Key must contain only printable ASCII")
    return key


@router.post(
    "/rating",
    operation_id="rateDoublePipe",
    response_model=RatingRunEnvelope,
    responses={
        422: {"model": ApiError},
        409: {"model": ApiError},
        500: {"model": ApiError},
    },
)
async def rate_double_pipe(
    request: Request,
    body: RatingApiRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
) -> Any:
    """Execute a rating request with idempotency protection."""
    deps = request.app.state.deps
    repo: RunRepository = deps.run_repository

    # 1. Validate Idempotency-Key
    try:  # noqa: SIM105
        idempotency_key = _validate_idempotency_key(idempotency_key)
    except ValueError as exc:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message=str(exc),
            operation="rateDoublePipe",
        )

    # 2. Execute rating via application service (resolves provider,
    #    builds canonical context, executes rating kernel)
    try:
        service_result = deps.rating_service.rate(body)
    except ValueError as exc:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message=str(exc),
            operation="rateDoublePipe",
        )

    request_digest = service_result.request_digest

    # 3. Compute idempotency namespace
    key_digest = hashlib.sha256(idempotency_key.encode("ascii")).hexdigest()
    namespace_digest = compute_idempotency_namespace_digest(
        api_schema_version="1",
        operation_id="rateDoublePipe",
        idempotency_key_digest=key_digest,
    )

    # 4. Claim idempotency namespace
    try:  # noqa: SIM105
        claim = repo.claim(
            namespace_digest=namespace_digest,
            request_digest=request_digest,
            operation="rateDoublePipe",
        )
    except IdempotencyConflictError as exc:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message=str(exc),
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    record = claim.record

    # 5. Handle claim outcomes
    if claim.outcome == ClaimOutcome.COMPLETE_REPLAY:
        return JSONResponse(
            status_code=200,
            content=record.envelope.model_dump(mode="json") if record.envelope else {},
        )

    if claim.outcome == ClaimOutcome.IN_PROGRESS:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Rating is already in progress",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    if claim.outcome == ClaimOutcome.STALE_REJECTED:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Previous run is stale; retry with takeover=True",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    if claim.outcome == ClaimOutcome.FAILED_REPLAY:
        return JSONResponse(
            status_code=200,
            content=record.envelope.model_dump(mode="json") if record.envelope else {},
        )

    # NEW_CLAIM or STALE_TAKEOVER → execute
    owner_token = record.owner_token

    # 6. Start run — use RETURNED record's version
    try:
        record = repo.start(owner_token=owner_token, expected_version=record.record_version)
    except Exception:
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Failed to start run",
            operation="rateDoublePipe",
        )

    # 7. Build artifact bundle
    try:
        bundle_dict = {
            "canonical_request_snapshot": service_result.canonical_request_snapshot,
            "resolved_provider": service_result.resolved_provider.model_dump(mode="json"),
            "geometry_artifact": service_result.geometry_artifact,
            "solver_artifact": service_result.solver_artifact,
            "rating_result": service_result.result.model_dump(mode="python"),
            "result_hash": service_result.result.result_hash,
            "provenance_graph": service_result.provenance.model_dump(mode="python"),
            "provenance_digest": service_result.provenance.compute_hash(),
        }
        bundle_hash = compute_bundle_hash(bundle_dict)

        bundle = RatingRunArtifacts(
            canonical_request_snapshot=service_result.canonical_request_snapshot,
            resolved_provider=service_result.resolved_provider,
            geometry_artifact=service_result.geometry_artifact,
            solver_artifact=service_result.solver_artifact,
            rating_result=service_result.result,
            result_hash=service_result.result.result_hash,
            provenance_graph=service_result.provenance,
            provenance_digest=service_result.provenance.compute_hash(),
            bundle_hash=bundle_hash,
        )
    except Exception as exc:
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=str(exc),
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Artifact bundle construction failed",
            operation="rateDoublePipe",
        )

    # 8. Build envelope with typed fields
    try:
        envelope = RatingRunEnvelope(
            api_schema_version="1",
            operation="rateDoublePipe",
            run_id=record.run_id,
            idempotency_key_digest=key_digest,
            request_digest=request_digest,
            result_kind="rating",
            result=service_result.result,
            result_hash=service_result.result.result_hash,
            warnings=service_result.result.warnings,
            blockers=service_result.result.blockers,
            failure=service_result.result.failure,
            provenance=service_result.provenance,
            provenance_digest=service_result.provenance.compute_hash(),
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle_hash,
            report_links=ReportLinks(html=f"/v1/runs/{record.run_id}/report.html"),
        )
    except Exception as exc:
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=str(exc),
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            operation="rateDoublePipe",
        )

    # 9. Complete repository — use RETURNED record, structured error on failure
    try:
        record = repo.complete(
            owner_token=owner_token,
            expected_version=record.record_version,
            envelope=envelope,
            artifact_bundle=bundle,
        )
    except Exception as exc:
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message=f"Repository completion failed: {exc}",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    return JSONResponse(
        status_code=200,
        content=envelope.model_dump(mode="json"),
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
