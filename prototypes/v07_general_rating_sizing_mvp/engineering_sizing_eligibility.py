"""Engineering completeness vs numeric constraint satisfaction (R22 P0)."""

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_tube_local_loss_geometry import (
    experimental_engineering_tube_local_loss_enabled,
)


def assess_engineering_sizing_eligibility(
    case: EngineeringCase,
    row: dict[str, Any],
) -> dict[str, Any]:
    """Separate demonstration numeric results from engineering-complete sizing eligibility."""
    postpass = row.get("live_thermal_state_hydraulic_postpass") or {}
    eng_block = postpass.get("tube_local_loss_engineering")
    reasons: list[str] = []
    geometry_status = "NOT_APPLICABLE"
    completeness = "NOT_APPLICABLE"

    if experimental_engineering_tube_local_loss_enabled(case):
        if eng_block is None:
            reasons.append("MISSING_TUBE_LOCAL_LOSS_ENGINEERING_DISCLOSURE")
        else:
            geometry_status = str(eng_block.get("assumed_geometry_status", "UNKNOWN"))
            completeness = str(eng_block.get("engineering_geometry_completeness", "UNKNOWN"))
            if completeness == "ENTRANCE_ONLY_ASSUMED":
                reasons.append("ENTRANCE_ONLY_ASSUMED_NO_EXIT_OR_PATH_LOCAL_LOSS_MODEL")
            if geometry_status == "EXPERIMENTAL_ASSUMED_GEOMETRY_ONLY":
                reasons.append("EXPERIMENTAL_ASSUMED_GEOMETRY_NOT_DEVICE_CONFIRMED")

    if reasons:
        return {
            "ENGINEERING_SIZING_ELIGIBILITY": "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE",
            "GEOMETRY_COMPLETENESS_STATUS": completeness,
            "assumed_geometry_status": geometry_status,
            "ineligibility_reasons": reasons,
        }
    if experimental_engineering_tube_local_loss_enabled(case):
        return {
            "ENGINEERING_SIZING_ELIGIBILITY": "ENGINEERING_INPUT_COMPLETE_FOR_EXPERIMENTAL_SCOPE",
            "GEOMETRY_COMPLETENESS_STATUS": completeness,
            "assumed_geometry_status": geometry_status,
            "ineligibility_reasons": [],
        }
    return {
        "ENGINEERING_SIZING_ELIGIBILITY": "LEGACY_REFERENCE_HYDRAULIC_PATH",
        "GEOMETRY_COMPLETENESS_STATUS": completeness,
        "assumed_geometry_status": geometry_status,
        "ineligibility_reasons": [],
    }


def engineering_sizing_eligible_for_ranking(eligibility_doc: dict[str, Any]) -> bool:
    status = eligibility_doc.get("ENGINEERING_SIZING_ELIGIBILITY")
    return status in {
        "ENGINEERING_INPUT_COMPLETE_FOR_EXPERIMENTAL_SCOPE",
        "LEGACY_REFERENCE_HYDRAULIC_PATH",
    }
