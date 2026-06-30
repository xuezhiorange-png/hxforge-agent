"""TASK-010 v1 sizing endpoint."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from hexagent.api.errors import ApiError, ErrorDetail
from hexagent.api.models import SizingApiRequest
from hexagent.api.sizing_service import SizingService, SizingServiceResult

router = APIRouter(prefix="/v1", tags=["sizing"])


# ---------------------------------------------------------------------------
# Dependency: SizingService placeholder
# ---------------------------------------------------------------------------
# In production, inject real registries via FastAPI Depends or app state.
# For now, module-level unconfigured sentinel so the route can be mounted.

_service: SizingService | None = None


def configure_sizing_service(service: SizingService) -> None:
    """Register the global SizingService instance for the v1 sizing endpoint."""
    global _service
    _service = service


def _get_service() -> SizingService:
    """FastAPI dependency that returns the configured SizingService."""
    if _service is None:
        raise HTTPException(
            status_code=503,
            detail=ApiError(
                error_code="SERVICE_NOT_CONFIGURED",
                message="SizingService has not been configured.",
            ).model_dump(),
        )
    return _service


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/sizing/double-pipe",
    response_model=SizingServiceResult,
    responses={
        422: {"model": ApiError},
        500: {"model": ApiError},
    },
)
async def sizing_double_pipe(
    request: SizingApiRequest,
) -> SizingServiceResult:
    """Execute a sizing request through the canonical projection path.

    Returns the full projection result including:
    - design_case
    - sizing_request
    - sizing_request_identity
    - effective_solver_params
    - resolved_provider
    - resolved_catalogs
    - canonical_request_snapshot
    - request_digest
    """
    service = _get_service()
    try:
        return service.process(request)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=ApiError(
                error_code="SIZING_VALIDATION_ERROR",
                message=str(exc),
                details=(
                    ErrorDetail(
                        code="sizing_validation_failed",
                        message=str(exc),
                    ),
                ),
            ).model_dump(),
        ) from exc
