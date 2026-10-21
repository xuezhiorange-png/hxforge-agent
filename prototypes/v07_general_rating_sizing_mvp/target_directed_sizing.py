"""Target-directed experimental sizing decision (evaluated candidates only)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import CandidateSelectionOutcome
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    build_candidate_eligibility,
    constraint_satisfied_ids,
)
from prototypes.v07_general_rating_sizing_mvp.r10_frozen_baseline import (
    R10_CANDIDATE_A_REFERENCE,
    r10_reference_a_nominal_area_m2,
)


def build_target_directed_sizing_decision(
    case: EngineeringCase,
    selection: CandidateSelectionOutcome,
    rating_rows: list[dict[str, Any]],
    *,
    selection_reason: str,
) -> dict[str, Any]:
    eligibility = build_candidate_eligibility(case, selection, rating_rows)
    feasible = constraint_satisfied_ids(eligibility)
    rated_rows = [row for row in rating_rows if row.get("mesh_status") == "NUMERIC_VALID"]
    feasible_rows = [row for row in rated_rows if row["candidate_id"] in feasible]

    best_row: dict[str, Any] | None = None
    if feasible_rows:
        best_row = min(
            feasible_rows,
            key=lambda row: Decimal(
                (row.get("nominal_geometry") or {}).get("nominal_tube_outer_area_m2", "Infinity")
            ),
        )

    r10_area = r10_reference_a_nominal_area_m2()
    area_reduction_percent: str | None = None
    if best_row is not None:
        best_area = Decimal(
            str((best_row.get("nominal_geometry") or {}).get("nominal_tube_outer_area_m2"))
        )
        if r10_area > 0:
            reduction = (r10_area - best_area) / r10_area * Decimal("100")
            area_reduction_percent = str(reduction)

    target_status = "NO_FEASIBLE_EVALUATED_CANDIDATE"
    if feasible_rows:
        target_status = "PRELIMINARY_CONSTRAINT_SATISFIED_IN_EVALUATED_SET"
    elif rated_rows:
        target_status = "PRELIMINARY_CONSTRAINT_FAILED_IN_EVALUATED_SET"

    duty_w = best_row.get("total_duty_w") if best_row else None
    overshoot_ratio: str | None = None
    if duty_w is not None:
        overshoot_ratio = str(Decimal(str(duty_w)) / case.target_duty_w)

    return {
        "schema_version": "hxforge.target-directed-sizing-decision.v1",
        "selection_reason": selection_reason,
        "scope_disclaimer": (
            "Preference among live-rated candidates in this run only; "
            "not a global optimum over the full discrete candidate space."
        ),
        "TARGET_CONSTRAINT_STATUS": target_status,
        "BEST_EVALUATED_CANDIDATE_ID": best_row.get("candidate_id") if best_row else None,
        "BEST_EVALUATED_DUTY_W": duty_w,
        "BEST_EVALUATED_NOMINAL_AREA_M2": (
            (best_row.get("nominal_geometry") or {}).get("nominal_tube_outer_area_m2")
            if best_row
            else None
        ),
        "AREA_REDUCTION_VS_R10_A_PERCENT": area_reduction_percent,
        "TARGET_DUTY_W": str(case.target_duty_w),
        "DUTY_OVERSHOOT_RATIO_VS_TARGET": overshoot_ratio,
        "R10_BASELINE_CANDIDATE_A": R10_CANDIDATE_A_REFERENCE,
        "HYDRAULIC_MODEL_SCOPE": "HYDRAULIC_REFERENCE_MODEL_PREVIEW",
        "full_rating_converged": False,
        "production_sizing_verified": False,
        "production_design_approved": False,
        "feasible_evaluated_candidate_ids": feasible,
        "rated_candidate_ids": [row["candidate_id"] for row in rated_rows],
    }
