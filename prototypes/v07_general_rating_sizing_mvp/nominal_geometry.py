"""Nominal tube outer area proxy from case + native cell context."""

from __future__ import annotations

from decimal import Decimal
from math import pi
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext


def nominal_tube_outer_area_proxy_m2(
    case: EngineeringCase,
    *,
    tube_length_m: str,
    physical_tube_count: int,
) -> dict[str, Any]:
    tube_od = case.candidate_constraints.tube_outer_diameter_m
    if case.bind_task172_c3_reference_geometry:
        tube_od = Decimal("0.01905")
    length = Decimal(tube_length_m)
    area = Decimal(str(pi)) * tube_od * length * Decimal(physical_tube_count)
    return {
        "area_kind": "NOMINAL_TUBE_OUTER_AREA_PROXY",
        "tube_outer_diameter_m": str(tube_od),
        "nominal_tube_length_m": tube_length_m,
        "physical_tube_count": physical_tube_count,
        "nominal_tube_outer_area_m2": str(area),
        "actual_effective_area_available": False,
        "disclaimer": (
            "π × tube_OD × nominal_tube_length × physical_tube_count; not verified "
            "effective heat-transfer area or manufacturing cost."
        ),
    }


def nominal_area_for_native(
    case: EngineeringCase,
    native: NativeCellContext,
    *,
    tube_length_m: str,
) -> dict[str, Any]:
    return nominal_tube_outer_area_proxy_m2(
        case,
        tube_length_m=tube_length_m,
        physical_tube_count=native.physical_tube_count,
    )
