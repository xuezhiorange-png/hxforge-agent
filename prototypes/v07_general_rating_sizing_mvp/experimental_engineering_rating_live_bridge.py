"""R26C: experimental engineering thermal rating + live hydraulic post-pass package."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.engineering_sizing_eligibility import (
    assess_engineering_sizing_eligibility,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_constraint_preview import (
    build_experimental_constraint_preview,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    EngineeringRatingResult,
    evaluate_mesh_convergence,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    NativeCellContext,
    build_native_cell_context,
)

_BRIDGE_SCHEMA = "hxforge.experimental-engineering-rating-live-bridge.v26c"


def _engineering_result_to_mesh_row(result: EngineeringRatingResult) -> dict[str, Any]:
    status = "NUMERIC_VALID" if result.status == ENGINEERING_NUMERIC_VALID else "BLOCKED"
    return {
        "status": status,
        "mesh_status": status,
        "total_duty_w": result.duty_w,
        "tube_outlet_temperature_k": result.tube_outlet_temperature_k,
        "shell_outlet_temperature_k": result.shell_outlet_temperature_k,
        "energy_balance_relative_error": result.energy_balance_relative_error,
        "max_cell_thermal_residual_w": result.max_cell_thermal_residual_w,
        "max_inner_wall_outer_closure_residual_w": result.max_inner_wall_outer_closure_residual_w,
    }


def _finest_valid_mesh_result(
    mesh_report: dict[str, Any],
    *,
    meshes: tuple[int, ...] = (4, 2, 1),
) -> tuple[int, EngineeringRatingResult] | None:
    results: dict[int, EngineeringRatingResult] = mesh_report["results"]
    for level in meshes:
        res = results.get(level)
        if res is not None and res.status == ENGINEERING_NUMERIC_VALID:
            return level, res
    return None


def _hydraulic_receipt_from_postpass(
    postpass: dict[str, Any], case: EngineeringCase
) -> dict[str, Any]:
    tube_dp_raw = postpass.get("recalculated_tube_dp_pa")
    shell_dp_raw = postpass.get("recalculated_shell_dp_pa")
    tube_dp = Decimal(str(tube_dp_raw)) if tube_dp_raw is not None else None
    shell_dp = Decimal(str(shell_dp_raw)) if shell_dp_raw is not None else None
    max_tube = case.max_tube_side_pressure_drop_pa
    max_shell = case.max_shell_side_pressure_drop_pa
    tube_margin = (max_tube - tube_dp) if tube_dp is not None else None
    shell_margin = (max_shell - shell_dp) if shell_dp is not None else None
    return {
        "LIVE_TUBE_DP_PA": str(tube_dp) if tube_dp is not None else None,
        "LIVE_SHELL_DP_PA": str(shell_dp) if shell_dp is not None else None,
        "TUBE_DP_MARGIN_PA": str(tube_margin) if tube_margin is not None else None,
        "SHELL_DP_MARGIN_PA": str(shell_margin) if shell_margin is not None else None,
        "TUBE_HYDRAULIC_STATUS": postpass.get("tube_dp_constraint"),
        "SHELL_HYDRAULIC_STATUS": postpass.get("shell_dp_constraint"),
        "HYDRAULIC_CONSTRAINT_STATUS": postpass.get("hydraulic_constraint_status"),
        "CORRELATION_APPLICABILITY_STATUS": postpass.get("correlation_applicability_status"),
    }


def build_experimental_engineering_rating_live_package(
    case: EngineeringCase,
    *,
    native: NativeCellContext | None = None,
    run_mesh_ladder: bool = True,
    single_mesh_subdivisions: int | None = None,
) -> dict[str, Any]:
    """Thermal mesh ladder (optional) + live hydraulic post-pass on finest valid mesh."""
    native_ctx = native or build_native_cell_context(case)
    cache: dict[int, EngineeringRatingResult] = {}
    mesh_report: dict[str, Any] | None = None
    if run_mesh_ladder:
        mesh_report = evaluate_mesh_convergence(case, native=native_ctx, mesh_result_cache=cache)
        finest = _finest_valid_mesh_result(mesh_report)
    else:
        subdivisions = single_mesh_subdivisions or 1
        result = run_experimental_engineering_rating(
            case,
            subdivisions=subdivisions,
            native=native_ctx,
            mesh_result_cache=cache,
        )
        mesh_report = {
            "results": {subdivisions: result},
            "per_mesh": {subdivisions: {"duty_w": result.duty_w}},
            "FULL_RATING_CONVERGED": result.status == ENGINEERING_NUMERIC_VALID,
            "DUTY_MESH_STABLE": False,
            "OUTLET_TEMPERATURE_MESH_STABLE": False,
            "LOCAL_CLOSURE_VALID": result.status == ENGINEERING_NUMERIC_VALID,
        }
        finest = (subdivisions, result) if result.status == ENGINEERING_NUMERIC_VALID else None

    thermal_status = "EXPERIMENTAL_ENGINEERING_THERMAL_RATING"
    mesh_row: dict[str, Any] = {}
    live_postpass: dict[str, Any] | None = None
    hydraulic_receipt: dict[str, Any] = {
        "LIVE_HYDRAULIC_IMPLEMENTED": False,
        "LIVE_TUBE_DP_PA": None,
        "LIVE_SHELL_DP_PA": None,
        "TUBE_DP_MARGIN_PA": None,
        "SHELL_DP_MARGIN_PA": None,
        "TUBE_HYDRAULIC_STATUS": "NOT_EVALUATED",
        "SHELL_HYDRAULIC_STATUS": "NOT_EVALUATED",
        "HYDRAULIC_CONSTRAINT_STATUS": "NOT_EVALUATED",
        "CORRELATION_APPLICABILITY_STATUS": "NOT_EVALUATED",
    }
    if finest is not None:
        _level, rating = finest
        mesh_row = _engineering_result_to_mesh_row(rating)
        preview = build_experimental_constraint_preview(case, mesh=mesh_row, native=native_ctx)
        live_postpass = run_live_thermal_state_hydraulic_postpass(
            case,
            candidate_id=native_ctx.candidate_id,
            tube_inlet_temperature_k=Decimal(str(rating.tube_inlet_temperature_k)),
            tube_outlet_temperature_k=Decimal(str(rating.tube_outlet_temperature_k)),
            shell_inlet_temperature_k=Decimal(str(rating.shell_inlet_temperature_k)),
            shell_outlet_temperature_k=Decimal(str(rating.shell_outlet_temperature_k)),
            tube_inlet_pressure_pa=Decimal("101325"),
            shell_inlet_pressure_pa=Decimal("101325"),
            reference_tube_dp_pa=(
                Decimal(str(preview["modeled_tube_dp_pa"]))
                if preview.get("modeled_tube_dp_pa")
                else None
            ),
            reference_shell_dp_pa=(
                Decimal(str(preview["modeled_shell_dp_pa"]))
                if preview.get("modeled_shell_dp_pa")
                else None
            ),
        )
        hydraulic_receipt = {
            "LIVE_HYDRAULIC_IMPLEMENTED": True,
            **_hydraulic_receipt_from_postpass(live_postpass, case),
        }
        mesh_row["live_thermal_state_hydraulic_postpass"] = live_postpass

    eligibility = assess_engineering_sizing_eligibility(case, mesh_row)
    total_coolprop = sum(
        r.coolprop_stats.total_calls for r in (mesh_report or {}).get("results", {}).values()
    )
    n4_wall = None
    if mesh_report and 4 in mesh_report.get("results", {}):
        n4_wall = mesh_report["results"][4].wall_seconds

    package: dict[str, Any] = {
        "schema_version": _BRIDGE_SCHEMA,
        "TASK_ID": "V07_R26C_ENGINEERING_RATING_LIVE_HYDRAULIC_BRIDGE",
        "thermal_rating_status": thermal_status,
        "task173_reference_status": "UNCHANGED",
        "Engineering_Rating": {
            "Geometry": {
                "candidate_id": native_ctx.candidate_id,
                "mesh_levels_evaluated": list((mesh_report or {}).get("results", {}).keys()),
            },
            "Tube_Shell_Inlet_State": {
                "tube_inlet_temperature_k": (
                    finest[1].tube_inlet_temperature_k if finest else None
                ),
                "shell_inlet_temperature_k": (
                    finest[1].shell_inlet_temperature_k if finest else None
                ),
            },
            "Tube_Shell_Outlet_State": {
                "tube_outlet_temperature_k": (
                    finest[1].tube_outlet_temperature_k if finest else None
                ),
                "shell_outlet_temperature_k": (
                    finest[1].shell_outlet_temperature_k if finest else None
                ),
            },
            "Duty": {"finest_valid_mesh_duty_w": finest[1].duty_w if finest else None},
            "N1_N2_N4_Mesh_Convergence": {
                k: v
                for k, v in (mesh_report or {}).items()
                if k
                not in {
                    "results",
                }
            },
            "Thermal_Residual": (mesh_report or {}).get("per_mesh"),
            "Energy_Balance": (mesh_report or {}).get("per_mesh"),
            "Live_Tube_DP": hydraulic_receipt.get("LIVE_TUBE_DP_PA"),
            "Live_Shell_DP": hydraulic_receipt.get("LIVE_SHELL_DP_PA"),
            "Hydraulic_Constraint": hydraulic_receipt,
            "Engineering_Eligibility": eligibility,
        },
        "mesh_convergence": mesh_report,
        "live_thermal_state_hydraulic_postpass": live_postpass,
        "hydraulic_receipt": hydraulic_receipt,
        "GEOMETRY_COMPLETENESS_STATUS": eligibility.get(
            "GEOMETRY_COMPLETENESS_STATUS", "ENTRANCE_ONLY_ASSUMED"
        ),
        "ENGINEERING_SIZING_ELIGIBILITY": eligibility.get("ENGINEERING_SIZING_ELIGIBILITY"),
        "PRODUCTION_SIZING_VERIFIED": False,
        "PRODUCTION_DESIGN_APPROVED": False,
        "TOTAL_COOLPROP_CALLS": total_coolprop,
        "N4_WALL_SECONDS": n4_wall,
    }
    return package


def serialize_experimental_engineering_rating_live_package(package: dict[str, Any]) -> str:
    return json.dumps(package, indent=2, sort_keys=True, default=str)
