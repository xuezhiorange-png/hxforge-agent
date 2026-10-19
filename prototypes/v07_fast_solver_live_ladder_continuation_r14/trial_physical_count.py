"""Physical outer-trial counts (bracket establishment + narrow solve)."""

from __future__ import annotations

from typing import Any


def physical_trial_totals(
    *,
    bracket_establishment_trial_count: int,
    narrow_solve_trial_count: int,
) -> dict[str, int]:
    narrow = max(0, int(narrow_solve_trial_count))
    bracket = max(0, int(bracket_establishment_trial_count))
    return {
        "bracket_establishment_trial_count": bracket,
        "narrow_solve_trial_count": narrow,
        "total_physical_trial_count": bracket + narrow,
    }


def apply_physical_trial_fields(receipt: dict[str, Any]) -> dict[str, Any]:
    totals = physical_trial_totals(
        bracket_establishment_trial_count=int(receipt.get("bracket_establishment_trial_count", 0)),
        narrow_solve_trial_count=int(receipt.get("narrow_solve_trial_count", 0)),
    )
    out = dict(receipt)
    out.update(totals)
    out["outer_trial_count"] = totals["total_physical_trial_count"]
    return out
