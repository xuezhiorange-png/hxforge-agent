from __future__ import annotations

from fastapi import FastAPI

from hexagent.domain.models import CalculationResult, DesignCase
from hexagent.exchangers.double_pipe.service import DoublePipeService

app = FastAPI(
    title="Heat Exchanger Design Agent",
    version="0.1.0",
    description="Starter API. Preliminary calculations only.",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/cases/validate")
def validate_case(case: DesignCase) -> dict[str, object]:
    return {"valid": True, "case_id": str(case.id), "name": case.name}


@app.post("/v1/design/double-pipe", response_model=CalculationResult)
def design_double_pipe(case: DesignCase) -> CalculationResult:
    return DoublePipeService().size(case)
