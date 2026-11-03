"""Fail-closed sizing when two-way bulk pressure coupling did not converge (R23 gate)."""

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_two_way_bulk_pressure_feedback import (
    experimental_two_way_bulk_pressure_feedback_enabled,
)

TWO_WAY_COUPLING_NOT_CONVERGED = "TWO_WAY_COUPLING_NOT_CONVERGED"
COUPLED_CONVERGED = "COUPLED_CONVERGED"


def two_way_coupling_document(row: dict[str, Any]) -> dict[str, Any] | None:
    doc = row.get("experimental_two_way_bulk_pressure_feedback")
    if isinstance(doc, dict):
        return doc
    live = row.get("live_thermal_state_hydraulic_postpass")
    if isinstance(live, dict):
        nested = live.get("experimental_two_way_bulk_pressure_feedback")
        if isinstance(nested, dict):
            return nested
    return None


def two_way_coupling_status(row: dict[str, Any]) -> str | None:
    doc = two_way_coupling_document(row)
    if doc is None:
        return None
    status = doc.get("COUPLED_ITERATION_STATUS")
    return str(status) if status is not None else None


def two_way_coupling_blocks_sizing(
    case: EngineeringCase,
    row: dict[str, Any],
) -> tuple[bool, str | None]:
    if not experimental_two_way_bulk_pressure_feedback_enabled(case):
        return False, None
    status = two_way_coupling_status(row)
    if status == COUPLED_CONVERGED:
        return False, None
    return True, status or "NOT_EVALUATED"


def apply_two_way_coupling_constraint_gate(
    case: EngineeringCase,
    row: dict[str, Any],
    preliminary_constraint_status: str,
) -> str:
    blocked, reason = two_way_coupling_blocks_sizing(case, row)
    if not blocked:
        return preliminary_constraint_status
    if preliminary_constraint_status == "PRELIMINARY_CONSTRAINT_SATISFIED":
        return TWO_WAY_COUPLING_NOT_CONVERGED
    if preliminary_constraint_status == "NOT_EVALUATED":
        return TWO_WAY_COUPLING_NOT_CONVERGED
    return preliminary_constraint_status
