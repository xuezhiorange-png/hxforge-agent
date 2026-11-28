"""Production validate_candidate_rating diagnostics (no isolated hole inference)."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from prototypes.v08_thermal_rating.axial_rating_engine_v1 import ProductionCulpReport


@dataclass(frozen=True)
class ProductionRatingDiagnostic:
    PRODUCTION_TASK172_GATE: Literal["PASS", "BLOCKED", "NOT_RUN"]
    PRODUCTION_TASK173_STATUS: str
    PRODUCTION_FIRST_BLOCKER: str | None
    PRODUCTION_FAILED_MESH: str | None
    PRODUCTION_RESULT_HASH: str | None


def _failed_mesh(row: ProductionCulpReport) -> str | None:
    if row.row is None:
        return None
    for subdiv, attr in ((1, "mesh_n1_status"), (2, "mesh_n2_status"), (4, "mesh_n4_status")):
        status = getattr(row.row, attr)
        if status not in ("NUMERIC_VALID",):
            return f"N{subdiv}:{status}"
    return None


def build_production_rating_diagnostic(prod: ProductionCulpReport) -> ProductionRatingDiagnostic:
    if prod.outcome == "NOT_ATTEMPTED":
        return ProductionRatingDiagnostic(
            PRODUCTION_TASK172_GATE="NOT_RUN",
            PRODUCTION_TASK173_STATUS="NOT_ATTEMPTED",
            PRODUCTION_FIRST_BLOCKER=None,
            PRODUCTION_FAILED_MESH=None,
            PRODUCTION_RESULT_HASH=None,
        )
    code = prod.failure_code or ""
    task172 = (
        "BLOCKED"
        if prod.outcome != "RATING_SUCCESS"
        and ("TASK172" in code or "CELL_TASK172" in code or "LOCAL_TASK172" in code)
        else ("PASS" if prod.outcome == "RATING_SUCCESS" else "BLOCKED")
    )
    status = "VALIDATED" if prod.outcome == "RATING_SUCCESS" else "BLOCKED"
    return ProductionRatingDiagnostic(
        PRODUCTION_TASK172_GATE=task172,
        PRODUCTION_TASK173_STATUS=status,
        PRODUCTION_FIRST_BLOCKER=code if prod.outcome != "RATING_SUCCESS" else None,
        PRODUCTION_FAILED_MESH=_failed_mesh(prod),
        PRODUCTION_RESULT_HASH=prod.row.task173_result_hash if prod.row else None,
    )


__all__ = ["ProductionRatingDiagnostic", "build_production_rating_diagnostic"]
