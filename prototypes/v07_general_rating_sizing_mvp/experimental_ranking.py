"""Experimental multi-candidate ranking (non-production)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any


def build_experimental_ranking(
    case: Any,
    rating_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    comparable = [row for row in rating_rows if row.get("mesh_status") == "NUMERIC_VALID"]
    if len(comparable) < 2:
        return {
            "schema_version": "hxforge.experimental-ranking-result.v1",
            "EXPERIMENTAL_RANKING_STATUS": "NOT_AVAILABLE",
            "EXPERIMENTAL_COMPARISON_STATUS": (
                "EXPERIMENTAL_COMPARISON_AVAILABLE" if len(comparable) == 1 else "NOT_AVAILABLE"
            ),
            "ranked_candidate_ids": [],
            "preferred_candidate_id": None,
            "ranking_policy_id": "EXPERIMENTAL_MVP_DUTY_THEN_HEADROOM",
            "trace": [],
            "production_sizing_verified": False,
            "production_design_approved": False,
        }

    target = case.target_duty_w

    def score(row: dict[str, Any]) -> tuple[int, Decimal]:
        duty = Decimal(str(row["total_duty_w"]))
        meets = 1 if duty >= target else 0
        return (meets, duty)

    ordered = sorted(comparable, key=score, reverse=True)
    trace = []
    for rank, row in enumerate(ordered, start=1):
        duty = Decimal(str(row["total_duty_w"]))
        trace.append(
            {
                "rank": rank,
                "candidate_id": row["candidate_id"],
                "total_duty_w": str(duty),
                "meets_target_duty": duty >= target,
                "mesh_result_hash": row.get("mesh_result_hash"),
            }
        )
    return {
        "schema_version": "hxforge.experimental-ranking-result.v1",
        "EXPERIMENTAL_RANKING_STATUS": "EXPERIMENTAL_RANKING_AVAILABLE",
        "EXPERIMENTAL_COMPARISON_STATUS": "EXPERIMENTAL_COMPARISON_AVAILABLE",
        "ranked_candidate_ids": [row["candidate_id"] for row in ordered],
        "preferred_candidate_id": ordered[0]["candidate_id"],
        "ranking_policy_id": "EXPERIMENTAL_MVP_DUTY_THEN_HEADROOM",
        "trace": trace,
        "production_sizing_verified": False,
        "production_design_approved": False,
    }
