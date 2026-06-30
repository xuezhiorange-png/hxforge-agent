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

from hexagent.api.errors import ApiError, ApiErrorCode

router = APIRouter(prefix="/v1/runs", tags=["runs"])


@router.get(
    "/{run_id}",
    operation_id="getRun",
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

    # Phase 2: return placeholder HTML
    # Full report rendering requires Phase 3 report builder
    html = (
        f"<html><head><title>Run {run_id}</title></head>"
        f"<body><h1>Run Report</h1>"
        f"<p>Run ID: {run_id}</p>"
        f"<p>Operation: {record.operation}</p>"
        f"<p>State: {record.state}</p>"
        f"</body></html>"
    )
    return HTMLResponse(content=html, status_code=200)


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
    return JSONResponse(
        status_code=501,
        content={
            "api_schema_version": "1",
            "operation": "getRunReportPdf",
            "status_code": 501,
            "error_code": ApiErrorCode.PDF_NOT_AVAILABLE,
            "error_message": "PDF rendering is not available",
            "request_digest": None,
            "details": [],
        },
    )


def _not_found(run_id: UUID) -> JSONResponse:
    return JSONResponse(
        status_code=404,
        content={
            "api_schema_version": "1",
            "operation": None,
            "status_code": 404,
            "error_code": ApiErrorCode.RUN_NOT_FOUND,
            "error_message": f"Run {run_id} not found",
            "request_digest": None,
            "details": [],
        },
    )
