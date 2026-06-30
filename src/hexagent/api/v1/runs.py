"""TASK-010 run and report retrieval endpoints.

Contract §5:
  GET /v1/runs/{run_id}                → getRun (200/404)
  GET /v1/runs/{run_id}/report.html    → getRunReportHtml (200/404/500)
  GET /v1/runs/{run_id}/report.pdf     → getRunReportPdf (200/501)
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

from hexagent.api.envelopes import AnyRunEnvelope
from hexagent.api.errors import ApiError, ApiErrorCode

router = APIRouter(prefix="/v1/runs", tags=["runs"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_error_response(
    *,
    status_code: int,
    error_code: str,
    error_message: str,
    operation: str | None = None,
) -> JSONResponse:
    api_error = ApiError(
        api_schema_version="1",
        operation=operation,
        status_code=status_code,
        error_code=error_code,
        error_message=error_message,
        request_digest=None,
        details=(),
    )
    return JSONResponse(
        status_code=status_code,
        content=api_error.model_dump(mode="json"),
    )


def _not_found(run_id: UUID) -> JSONResponse:
    return _make_error_response(
        status_code=404,
        error_code=ApiErrorCode.RUN_NOT_FOUND,
        error_message=f"Run {run_id} not found",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/{run_id}",
    operation_id="getRun",
    response_model=AnyRunEnvelope,
    responses={
        200: {"description": "Run envelope"},
        404: {"model": ApiError},
    },
)
async def get_run(request: Request, run_id: UUID) -> Any:
    """Retrieve a stored run envelope by run_id."""
    repo = request.app.state.deps.run_repository
    record = repo.get_by_run_id(run_id)

    if record is None or record.envelope is None:
        return _not_found(run_id)

    return JSONResponse(
        status_code=200,
        content=record.envelope.model_dump(mode="json"),
    )


@router.get(
    "/{run_id}/report.html",
    operation_id="getRunReportHtml",
    responses={
        200: {"content": {"text/html": {}}},
        404: {"model": ApiError},
        500: {"model": ApiError},
    },
)
async def get_run_report_html(request: Request, run_id: UUID) -> Any:
    """Retrieve the HTML report for a run.

    Validation runs return 404 (no report).
    Rating/Sizing runs: 200 text/html or 500 on render failure.
    """
    repo = request.app.state.deps.run_repository
    record = repo.get_by_run_id(run_id)

    if record is None or record.envelope is None:
        return _not_found(run_id)

    # Validation runs have no report
    if record.operation == "validateCase":
        return _not_found(run_id)

    # Attempt to render a real report via hexagent.reporting.
    # If the module is not yet implemented, return a structured 500.
    try:
        from hexagent.reporting import build_report_html  # noqa: F811

        html = build_report_html(record)
        return HTMLResponse(content=html, status_code=200)
    except ImportError:
        return _make_error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Report rendering is not available",
            operation=record.operation,
        )
    except Exception:
        return _make_error_response(
            status_code=500,
            error_code=ApiErrorCode.INTERNAL_ERROR,
            error_message="Report rendering failed",
            operation=record.operation,
        )


@router.get(
    "/{run_id}/report.pdf",
    operation_id="getRunReportPdf",
    responses={
        200: {"content": {"application/pdf": {}}},
        404: {"model": ApiError},
        501: {"model": ApiError},
    },
)
async def get_run_report_pdf(request: Request, run_id: UUID) -> Any:
    """Retrieve the PDF report for a run.

    No PDF adapter configured → 501 pdf_not_available.
    """
    return _make_error_response(
        status_code=501,
        error_code=ApiErrorCode.PDF_NOT_AVAILABLE,
        error_message="PDF rendering is not available",
        operation="getRunReportPdf",
    )
