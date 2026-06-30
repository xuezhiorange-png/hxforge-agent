"""TASK-010 validation endpoint.

Contract: POST /v1/cases/validate → operation_id=validateCase
Request: ValidationApiRequest
Response: ValidationRunEnvelope
No idempotency. No artifact bundle.
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from hexagent.api.canonical_request import compute_api_request_digest
from hexagent.api.envelopes import ValidationRunEnvelope
from hexagent.api.errors import ApiError, ApiErrorCode, ErrorDetail
from hexagent.api.models import ValidationApiRequest
from hexagent.api.projection import project_validation_to_design_case

router = APIRouter(prefix="/v1/cases", tags=["validation"])


@router.post(
    "/validate",
    operation_id="validateCase",
    response_model=ValidationRunEnvelope,
    responses={
        422: {"model": ApiError},
        500: {"model": ApiError},
    },
)
async def validate_case(request: Request, body: ValidationApiRequest) -> Any:
    """Validate a design case without executing a calculation."""
    try:
        project_validation_to_design_case(body)
    except (ValueError, TypeError) as exc:
        return _validation_error(str(exc))

    try:
        snapshot = _build_validation_snapshot(body)
        request_digest = compute_api_request_digest(snapshot)
    except Exception:
        raise

    import hashlib
    import json

    receipt_hash = (
        "sha256:"
        + hashlib.sha256(
            json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
    )

    return ValidationRunEnvelope(
        api_schema_version="1",
        operation="validateCase",
        run_id=uuid4(),
        request_digest=request_digest,
        result_kind="validation",
        result=None,
        validation_receipt_hash=receipt_hash,
        report_links=None,
    )


def _build_validation_snapshot(body: ValidationApiRequest) -> dict[str, Any]:
    """Build canonical snapshot for validation request."""
    from hexagent.api.canonical_request import canonicalize_api_payload

    raw = body.model_dump(mode="json")
    result: dict[str, Any] = canonicalize_api_payload(raw)
    return result


def _validation_error(message: str) -> JSONResponse:
    """Return a 422 validation error."""
    api_error = ApiError(
        api_schema_version="1",
        operation="validateCase",
        status_code=422,
        error_code=ApiErrorCode.VALIDATION_FAILED,
        error_message=message,
        request_digest=None,
        details=(
            ErrorDetail(
                path=(),
                code="validation_failed",
                message=message,
            ),
        ),
    )
    return JSONResponse(
        status_code=422,
        content=api_error.model_dump(mode="json"),
    )
