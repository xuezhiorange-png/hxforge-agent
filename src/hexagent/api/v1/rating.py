"""TASK-010 rating endpoint.

Contract: POST /v1/double-pipe/rating → operation_id=rateDoublePipe
Request: RatingApiRequest
Response: RatingRunEnvelope
Idempotency required.

P0-1: prepare() runs BEFORE idempotency claim; execute() runs AFTER.
"""

from __future__ import annotations

import dataclasses
import hashlib
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from hexagent.api.artifacts import (
    RatingRunArtifacts,
)
from hexagent.api.canonical_request import compute_idempotency_namespace_digest
from hexagent.api.envelopes import RatingRunEnvelope, ReportLinks
from hexagent.api.errors import ApiError, ApiErrorCode
from hexagent.api.models import RatingApiRequest
from hexagent.api.repository import (
    ClaimOutcome,
    FrozenFailurePayload,
    IdempotencyConflictError,
    RunRepository,
)
from hexagent.core.canonical import sha256_digest

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


def _dump_to_python(obj: Any) -> Any:
    """Serialize a domain object to its Python dict form for hashing."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="python")
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj


def _compute_bundle_digest_from_fields(
    *,
    canonical_request_snapshot: dict[str, object],
    request_identity: Any,
    geometry_snapshot: Any,
    solver_settings: Any,
    provider_identity: Any,
    result: Any,
    provenance_graph: Any,
) -> str:
    """Compute the bundle digest from raw field values without constructing RatingRunArtifacts.

    Uses the same serialization as RatingRunArtifacts.model_dump() to
    ensure the digest matches what the verifier computes.
    """

    # Use model_dump for Pydantic models, asdict for dataclasses
    def _dump(obj: Any) -> Any:
        if hasattr(obj, "model_dump"):
            return obj.model_dump(mode="python")
        import dataclasses

        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        return obj

    payload = {
        "canonical_request_snapshot": canonical_request_snapshot,
        "request_identity": _dump(request_identity),
        "geometry_snapshot": _dump(geometry_snapshot),
        "solver_settings": _dump(solver_settings),
        "provider_identity": _dump(provider_identity),
        "result": _dump(result),
        "provenance_graph": _dump(provenance_graph),
    }
    return sha256_digest(payload)


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
    """Execute a rating request with idempotency protection.

    P0-1 flow:
    1. prepare() — NO kernel, builds PreparedRatingRun
    2. Compute idempotency namespace
    3. claim()
    4. Handle replay/in-progress outcomes
    5. execute() — kernel ONLY for NEW_CLAIM / STALE_TAKEOVER
    """
    deps = request.app.state.deps
    repo: RunRepository = deps.run_repository

    # 1. Validate Idempotency-Key
    try:  # noqa: SIM105
        idempotency_key = _validate_idempotency_key(idempotency_key)
    except ValueError:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message="Invalid idempotency key",
            operation="rateDoublePipe",
        )

    # 2. Prepare — NO kernel execution (P0-1)
    try:
        prepared = deps.rating_service.prepare(body)
    except ValueError:
        return _error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message="Validation failed",
            operation="rateDoublePipe",
        )

    request_digest = prepared.request_digest

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
    except IdempotencyConflictError:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Idempotency conflict",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    record = claim.record

    # 5. Handle claim outcomes

    # COMPLETE_REPLAY → return stored envelope (200)
    if claim.outcome == ClaimOutcome.COMPLETE_REPLAY:
        return JSONResponse(
            status_code=200,
            content=record.envelope.model_dump(mode="json") if record.envelope else {},
        )

    # IN_PROGRESS → return 409
    if claim.outcome == ClaimOutcome.IN_PROGRESS:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Rating is already in progress",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    # STALE_REJECTED → return 409
    if claim.outcome == ClaimOutcome.STALE_REJECTED:
        return _error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Previous run is stale; retry with takeover=True",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    # FAILED_REPLAY → return stored failure (NOT 200)
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
            operation="rateDoublePipe",
            request_digest=request_digest,
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

    # 7. Execute rating kernel (P0-1: only runs for NEW_CLAIM / STALE_TAKEOVER)
    try:
        service_result = deps.rating_service.execute(prepared)
    except Exception:
        _failure = FrozenFailurePayload(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Rating execution failed",
            request_digest=request_digest,
            operation="rateDoublePipe",
        )
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=_failure,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Rating execution failed",
            operation="rateDoublePipe",
            request_digest=request_digest,
        )

    # 8. Build artifact bundle using prepared fields + result (P0-3)
    try:
        # Compute digest from raw fields (avoids chicken-and-egg with model_validator)
        bundle_digest = _compute_bundle_digest_from_fields(
            canonical_request_snapshot=prepared.canonical_request_snapshot,
            request_identity=service_result.result.request_identity,
            geometry_snapshot=prepared.geometry,
            solver_settings=prepared.solver_settings,
            provider_identity=prepared.resolved_provider.identity,
            result=service_result.result,
            provenance_graph=service_result.provenance,
        )

        bundle = RatingRunArtifacts(
            canonical_request_snapshot=prepared.canonical_request_snapshot,
            request_identity=service_result.result.request_identity,
            geometry_snapshot=prepared.geometry,
            solver_settings=prepared.solver_settings,
            provider_identity=prepared.resolved_provider.identity,
            result=service_result.result,
            provenance_graph=service_result.provenance,
            artifact_bundle_digest=bundle_digest,
        )
    except Exception:
        _failure = FrozenFailurePayload(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Artifact bundle construction failed",
            request_digest=request_digest,
            operation="rateDoublePipe",
        )
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=_failure,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Artifact bundle construction failed",
            operation="rateDoublePipe",
        )

    # 9. Build envelope with typed fields (P0-4)
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
            provenance_digest=service_result.result.provenance_digest,
            artifact_bundle=bundle,
            artifact_bundle_digest=bundle_digest,
            report_links=ReportLinks(html=f"/v1/runs/{record.run_id}/report.html"),
        )
    except Exception:
        _failure = FrozenFailurePayload(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            request_digest=request_digest,
            operation="rateDoublePipe",
        )
        repo.fail(
            owner_token=owner_token,
            expected_version=record.record_version,
            failure=_failure,
        )
        return _error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Envelope construction failed",
            operation="rateDoublePipe",
        )

    # 10. Complete repository — use RETURNED record, structured error on failure
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
