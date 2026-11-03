"""Preliminary constraint checks for experimental low-mesh live rating."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import NativeCellContext


def build_experimental_constraint_preview(
    case: EngineeringCase,
    *,
    mesh: dict[str, Any],
    native: NativeCellContext,
) -> dict[str, Any]:
    status = mesh.get("status")
    if status is None:
        status = mesh.get("mesh_status")
    numeric_valid = status == "NUMERIC_VALID"
    duty_w: Decimal | None = None
    if numeric_valid and mesh.get("total_duty_w") is not None:
        duty_w = Decimal(str(mesh["total_duty_w"]))

    if duty_w is None:
        capacity_preview = "NOT_EVALUATED"
        duty_constraint = "NOT_EVALUATED"
    elif duty_w >= case.target_duty_w:
        capacity_preview = "MEETS_TARGET"
        duty_constraint = "SATISFIED"
    else:
        capacity_preview = "BELOW_TARGET"
        duty_constraint = "NOT_SATISFIED"

    tube_dp = native.modeled_tube_side_pressure_drop_pa
    shell_dp = native.modeled_shell_side_pressure_drop_pa
    if tube_dp is None or shell_dp is None:
        dp_preview = "NOT_EVALUATED"
        tube_dp_constraint = "NOT_EVALUATED"
        shell_dp_constraint = "NOT_EVALUATED"
        task174_hydraulic_status = "NOT_EVALUATED"
    else:
        task174_hydraulic_status = "HYDRAULIC_REFERENCE_MODEL_PREVIEW"
        tube_dp_dec = Decimal(tube_dp)
        shell_dp_dec = Decimal(shell_dp)
        tube_ok = tube_dp_dec <= case.max_tube_side_pressure_drop_pa
        shell_ok = shell_dp_dec <= case.max_shell_side_pressure_drop_pa
        tube_dp_constraint = "SATISFIED" if tube_ok else "NOT_SATISFIED"
        shell_dp_constraint = "SATISFIED" if shell_ok else "NOT_SATISFIED"
        dp_preview = "WITHIN_LIMITS" if tube_ok and shell_ok else "EXCEEDS_LIMIT"

    return {
        "schema_version": "hxforge.experimental-constraint-preview.v1",
        "EXPERIMENTAL_CAPACITY_PREVIEW": capacity_preview,
        "EXPERIMENTAL_DP_PREVIEW": dp_preview,
        "target_duty_w": str(case.target_duty_w),
        "rated_duty_w": str(duty_w) if duty_w is not None else None,
        "duty_constraint": duty_constraint,
        "max_tube_dp_pa": str(case.max_tube_side_pressure_drop_pa),
        "modeled_tube_dp_pa": tube_dp,
        "tube_dp_constraint": tube_dp_constraint,
        "max_shell_dp_pa": str(case.max_shell_side_pressure_drop_pa),
        "modeled_shell_dp_pa": shell_dp,
        "shell_dp_constraint": shell_dp_constraint,
        "task174_hydraulic_status": task174_hydraulic_status,
        "mesh_ladder_completed": False,
        "fiv_numeric_verified": False,
        "r2a_production_authority_verified": False,
        "task167_engineering_approval": False,
        "production_design_eligible": False,
        "full_rating_converged": False,
    }
