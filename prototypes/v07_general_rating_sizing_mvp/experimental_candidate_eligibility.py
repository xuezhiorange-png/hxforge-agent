"""Per-candidate structural / rating / constraint eligibility (experimental)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    CandidateSelectionOutcome,
    CandidateSelectionRecord,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase


def _structural_status(record: CandidateSelectionRecord) -> str:
    if not record.structural_admitted:
        return "BLOCKED_STRUCTURAL"
    if record.task168_chain_status == "BLOCKED_DOWNSTREAM":
        return "BLOCKED_DOWNSTREAM"
    if record.task168_chain_status == "CHAIN_COMPLETE":
        return "ADMITTED"
    return record.task168_chain_status


def _task174_status(record: CandidateSelectionRecord) -> str:
    if record.task174_status == "VALIDATED":
        return "VALIDATED"
    if record.task174_status == "BLOCKED":
        return "BLOCKED"
    return "NOT_RUN"


def _rating_status(mesh_status: str | None) -> str:
    if mesh_status == "NUMERIC_VALID":
        return "NUMERIC_VALID"
    if mesh_status in {None, "NOT_RUN"}:
        return "NOT_EVALUATED"
    if mesh_status == "BUDGET_STOP":
        return "NOT_EVALUATED"
    return "BLOCKED"


def _constraint_status(
    case: EngineeringCase,
    *,
    rating_status: str,
    constraint_preview: dict[str, Any] | None,
) -> str:
    if rating_status != "NUMERIC_VALID":
        return "NOT_EVALUATED"
    if constraint_preview is None:
        return "NOT_EVALUATED"
    duty = constraint_preview.get("duty_constraint")
    tube_dp = constraint_preview.get("tube_dp_constraint")
    shell_dp = constraint_preview.get("shell_dp_constraint")
    if duty == "NOT_EVALUATED" or tube_dp == "NOT_EVALUATED" or shell_dp == "NOT_EVALUATED":
        return "NOT_EVALUATED"
    if duty == "SATISFIED" and tube_dp == "SATISFIED" and shell_dp == "SATISFIED":
        return "PRELIMINARY_CONSTRAINT_SATISFIED"
    return "PRELIMINARY_CONSTRAINT_FAILED"


def build_candidate_eligibility(
    case: EngineeringCase,
    selection: CandidateSelectionOutcome,
    rating_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rating_by_id = {row["candidate_id"]: row for row in rating_rows}
    records_by_id = {rec.candidate_id: rec for rec in selection.records}
    entries: list[dict[str, Any]] = []
    for candidate_id in selection.selected_candidate_ids:
        record = records_by_id[candidate_id]
        row = rating_by_id.get(candidate_id, {})
        mesh_status = row.get("mesh_status") or row.get("status")
        preview = row.get("constraint_preview")
        rating_status = _rating_status(mesh_status)
        constraint_status = _constraint_status(
            case,
            rating_status=rating_status,
            constraint_preview=preview,
        )
        entries.append(
            {
                "candidate_id": candidate_id,
                "candidate_hash": record.candidate_hash,
                "tube_length_m": record.tube_length_m,
                "baffle_spacing_m": record.baffle_spacing_m,
                "STRUCTURAL_STATUS": _structural_status(record),
                "TASK174_STATUS": _task174_status(record),
                "RATING_STATUS": rating_status,
                "CONSTRAINT_STATUS": constraint_status,
                "PRODUCTION_QUALIFICATION": "PRODUCTION_NOT_QUALIFIED",
                "task168_blocked_codes": list(record.task168_blocked_codes),
                "nominal_geometry": row.get("nominal_geometry"),
            }
        )
    return entries


def constraint_satisfied_ids(eligibility: list[dict[str, Any]]) -> list[str]:
    return [
        item["candidate_id"]
        for item in eligibility
        if item["CONSTRAINT_STATUS"] == "PRELIMINARY_CONSTRAINT_SATISFIED"
    ]


def reevaluate_constraint_for_target(
    case: EngineeringCase,
    row: dict[str, Any],
    target_duty_w: Decimal,
) -> str:
    if row.get("mesh_status") != "NUMERIC_VALID" and row.get("status") != "NUMERIC_VALID":
        return "NOT_EVALUATED"
    preview = row.get("constraint_preview") or {}
    duty_w = Decimal(str(row.get("total_duty_w")))
    if duty_w < target_duty_w:
        return "PRELIMINARY_CONSTRAINT_FAILED"
    tube_dp = preview.get("tube_dp_constraint")
    shell_dp = preview.get("shell_dp_constraint")
    if tube_dp != "SATISFIED" or shell_dp != "SATISFIED":
        return "PRELIMINARY_CONSTRAINT_FAILED"
    return "PRELIMINARY_CONSTRAINT_SATISFIED"
