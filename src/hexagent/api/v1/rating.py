"""TASK-010 rating endpoint.

Contract: POST /v1/double-pipe/rating → operation_id=rateDoublePipe
Request: RatingApiRequest
Response: RatingRunEnvelope
Idempotency required.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from hexagent.api.canonical_request import (
    build_rating_canonical_request_context,
    compute_idempotency_namespace_digest,
)
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
    rating_service = deps.rating_service

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

    # 2. Resolve provider (before claim)
    try:  # noqa: SIM105
        provider_authority = deps.provider_registry.resolve(body.provider_ref)
    except ValueError as exc:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message=f"Provider resolution failed: {exc}",
            operation="rateDoublePipe",
        )

    # 3. Build canonical request context
    try:  # noqa: SIM105
        context = build_rating_canonical_request_context(
            request=body,
            resolved_provider=provider_authority,
        )
        request_digest = context["request_digest"]
        context["canonical_request_snapshot"]
    except Exception as exc:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message=f"Canonical request failed: {exc}",
            operation="rateDoublePipe",
        )

    # 4. Compute idempotency namespace
    key_digest = hashlib.sha256(idempotency_key.encode("ascii")).hexdigest()
    namespace_digest = compute_idempotency_namespace_digest(
        api_schema_version="1",
        operation_id="rateDoublePipe",
        idempotency_key_digest=key_digest,
    )

    # 5. Claim idempotency namespace
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

    # 6. Handle claim outcomes
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
    version = record.record_version

    try:  # noqa: SIM105
        repo.start(owner_token=owner_token, expected_version=version)
        version += 1
    except Exception:
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Failed to start run",
            operation="rateDoublePipe",
        )

    # 7. Execute rating
    try:  # noqa: SIM105
        rating_result = rating_service.rate(body)
    except Exception as exc:
        repo.fail(
            owner_token=owner_token,
            expected_version=version,
            failure=str(exc),
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Rating execution failed",
            operation="rateDoublePipe",
        )

    # 8. Build envelope (simplified — production builds full artifacts)
    try:  # noqa: SIM105
        envelope = _build_rating_envelope(
            run_id=record.run_id,
            idempotency_key_digest=key_digest,
            request_digest=request_digest,
            result=rating_result,
            provenance=rating_result.provenance,
        )
    except Exception as exc:
        repo.fail(
            owner_token=owner_token,
            expected_version=version,
            failure=str(exc),
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            operation="rateDoublePipe",
        )

    # 9. Complete repository
    try:  # noqa: SIM105
        repo.complete(
            owner_token=owner_token,
            expected_version=version,
            envelope=envelope,
            artifact_bundle=None,  # Phase 2: simplified
        )
    except Exception:  # noqa: BLE001
        pass  # envelope already built; response will be sent

    return JSONResponse(
        status_code=200,
        content=envelope.model_dump(mode="json"),
    )


def _build_rating_envelope(
    *,
    run_id: UUID,
    idempotency_key_digest: str,
    request_digest: str,
    result: Any,
    provenance: Any,
) -> RatingRunEnvelope:
    """Build a RatingRunEnvelope from rating result."""
    from hexagent.core.canonical import sha256_digest

    result_hash = sha256_digest(
        json.dumps(
            result.model_dump() if hasattr(result, "model_dump") else str(result),
            sort_keys=True,
            default=str,
        ).encode()
    )
    provenance_digest = provenance.compute_hash()

    return RatingRunEnvelope(
        api_schema_version="1",
        operation="rateDoublePipe",
        run_id=run_id,
        idempotency_key_digest=idempotency_key_digest,
        request_digest=request_digest,
        result_kind="rating",
        result=result,
        result_hash=result_hash,
        warnings=(),
        blockers=(),
        failure=None,
        provenance=provenance,
        provenance_digest=provenance_digest,
        artifact_bundle=None,
        artifact_bundle_digest="",
        report_links=ReportLinks(html=f"/v1/runs/{run_id}/report.html"),
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
