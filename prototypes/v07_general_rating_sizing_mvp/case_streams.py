"""Resolve tube/shell stream specs across engineering case schema versions."""

from __future__ import annotations

from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_input import (
    FluidSideSpec,
    GeneralEngineeringCaseV2,
)


def tube_stream_spec(case: EngineeringCase) -> FluidSideSpec:
    if isinstance(case, GeneralEngineeringCaseV2):
        return case.tube_side
    return case.cold_side


def shell_stream_spec(case: EngineeringCase) -> FluidSideSpec:
    if isinstance(case, GeneralEngineeringCaseV2):
        return case.shell_side
    return case.hot_side


def design_conditions_for_report(case: EngineeringCase) -> dict[str, Any]:
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    common: dict[str, Any] = {
        "target_duty_w": str(case.target_duty_w),
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
        "exchanger_type": case.exchanger_type,
    }
    if isinstance(case, GeneralEngineeringCaseV2):
        return {
            **common,
            "engineering_case_schema": case.schema_version,
            "tube_side": tube.model_dump(mode="json"),
            "shell_side": shell.model_dump(mode="json"),
            "heat_transfer_convention": case.heat_transfer_convention(),
        }
    return {
        **common,
        "cold_side": case.cold_side.model_dump(mode="json"),
        "hot_side": case.hot_side.model_dump(mode="json"),
        "equipment_mapping_note": (
            "v1 cold_side=tube equipment stream, hot_side=shell equipment stream "
            "(legacy field names)"
        ),
    }
