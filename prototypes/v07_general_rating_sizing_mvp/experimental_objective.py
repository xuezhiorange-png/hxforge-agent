"""Experimental sizing objective resolution (non-production)."""

from __future__ import annotations

from typing import Literal

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2

ExperimentalSizingObjective = Literal[
    "PARETO_ONLY",
    "MIN_NOMINAL_TUBE_AREA",
    "MAX_DUTY",
    "MIN_SHELL_DP_PREVIEW",
]

DEFAULT_OBJECTIVE: ExperimentalSizingObjective = "PARETO_ONLY"


def resolve_experimental_sizing_objective(
    case: EngineeringCase,
    *,
    cli_override: str | None = None,
) -> ExperimentalSizingObjective:
    if cli_override is not None:
        return _parse_objective(cli_override)
    if isinstance(case, GeneralEngineeringCaseV2):
        return _parse_objective(case.experimental_sizing_objective)
    return DEFAULT_OBJECTIVE


def _parse_objective(value: str) -> ExperimentalSizingObjective:
    allowed = {
        "PARETO_ONLY",
        "MIN_NOMINAL_TUBE_AREA",
        "MAX_DUTY",
        "MIN_SHELL_DP_PREVIEW",
    }
    if value not in allowed:
        raise ValueError(f"unsupported experimental_sizing_objective: {value}")
    return value  # type: ignore[return-value]
