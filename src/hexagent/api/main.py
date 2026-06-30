"""TASK-010 FastAPI application factory.

Contract §5 (routes), §17 (errors), P0-5 (app factory).

Frozen API surface (6 operations):
  POST /v1/cases/validate       → validateCase
  POST /v1/double-pipe/rating   → rateDoublePipe
  POST /v1/double-pipe/sizing   → sizeDoublePipe
  GET  /v1/runs/{run_id}        → getRun
  GET  /v1/runs/{run_id}/report.html → getRunReportHtml
  GET  /v1/runs/{run_id}/report.pdf  → getRunReportPdf

No mutable module globals. All dependencies injected via create_app().
Legacy starter routes REMOVED.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hexagent.api.errors import ApiError, ApiErrorCode, ErrorDetail
from hexagent.api.repository import (
    CASCasError,
    IdempotencyConflictError,
    RepositoryStateError,
)
from hexagent.api.v1 import rating, runs, sizing, validation


class DependencyContainer:
    """Immutable container for application dependencies."""

    __slots__ = (
        "provider_registry",
        "catalog_registry",
        "run_repository",
        "sizing_service",
        "rating_service",
    )

    def __init__(
        self,
        *,
        provider_registry: Any,
        catalog_registry: Any,
        run_repository: Any,
        sizing_service: Any,
        rating_service: Any,
    ) -> None:
        self.provider_registry = provider_registry
        self.catalog_registry = catalog_registry
        self.run_repository = run_repository
        self.sizing_service = sizing_service
        self.rating_service = rating_service


def _make_error_response(
    *,
    status_code: int,
    error_code: str,
    error_message: str,
    operation: str | None = None,
    request_digest: str | None = None,
    details: tuple[ErrorDetail, ...] = (),
) -> JSONResponse:
    api_error = ApiError(
        api_schema_version="1",
        operation=operation,
        status_code=status_code,
        error_code=error_code,
        error_message=error_message,
        request_digest=request_digest,
        details=details,
    )
    return JSONResponse(
        status_code=status_code,
        content=api_error.model_dump(mode="json"),
    )


def create_app(
    *,
    provider_registry: Any,
    catalog_registry: Any,
    run_repository: Any,
    sizing_service: Any,
    rating_service: Any,
) -> FastAPI:
    """Application factory per contract P0-5.

    All dependencies MUST be provided at construction time.
    Missing dependencies → fail at construction, not at request time.
    """
    container = DependencyContainer(
        provider_registry=provider_registry,
        catalog_registry=catalog_registry,
        run_repository=run_repository,
        sizing_service=sizing_service,
        rating_service=rating_service,
    )

    app = FastAPI(
        title="Heat Exchanger Design Agent",
        version="1.0.0",
        description="TASK-010 contract API. Frozen operation set.",
    )

    # Store immutable container on app.state
    app.state.deps = container

    # Register exception handlers BEFORE including routers

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Convert FastAPI's default 422 to frozen ApiError format."""
        details = []
        for error in exc.errors():
            loc = error.get("loc", ())
            # Strip 'body' prefix from location
            path = tuple(p for p in loc if p != "body")
            details.append(
                ErrorDetail(
                    path=path,
                    code=error.get("type", "value_error"),
                    message=error.get("msg", "validation error"),
                    rejected_value_preview=_safe_preview(error.get("input")),
                )
            )
        return _make_error_response(
            status_code=422,
            error_code=ApiErrorCode.VALIDATION_FAILED,
            error_message="Request validation failed",
            details=tuple(details),
        )

    @app.exception_handler(IdempotencyConflictError)
    async def _idempotency_conflict_handler(
        request: Request, exc: IdempotencyConflictError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message=str(exc),
        )

    @app.exception_handler(RepositoryStateError)
    async def _repository_state_handler(
        request: Request, exc: RepositoryStateError
    ) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message=str(exc),
        )

    @app.exception_handler(CASCasError)
    async def _cas_handler(request: Request, exc: CASCasError) -> JSONResponse:
        return _make_error_response(
            status_code=409,
            error_code=ApiErrorCode.IDEMPOTENCY_CONFLICT,
            error_message="Concurrent modification detected",
        )

    @app.exception_handler(Exception)
    async def _generic_error_handler(request: Request, exc: Exception) -> JSONResponse:
        """Catch-all: never leak internal details."""
        return _make_error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="An internal error occurred",
        )

    # Include routers (frozen operation set)
    app.include_router(validation.router)
    app.include_router(rating.router)
    app.include_router(sizing.router)
    app.include_router(runs.router)

    return app


def _safe_preview(value: Any) -> str | None:
    """Truncate value preview to 200 chars, never leak secrets."""
    if value is None:
        return None
    s = str(value)
    if len(s) > 200:
        return s[:200]
    return s
