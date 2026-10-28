"""R26C-A: nominal hydraulic constraints, margin disclosure, and fixed-thermal sensitivity."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from prototypes.v07_general_rating_sizing_mvp.case_streams import shell_stream_spec
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

_SENSITIVITY_MODE = "FIXED_THERMAL_STATE_HYDRAULIC_SENSITIVITY"
_NEAR_BOUNDARY_MARGIN_PERCENT = Decimal("1.0")
_FLOW_PERTURBATION_FRACTION = Decimal("0.01")


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _shell_dp_from_postpass(postpass: dict[str, Any]) -> Decimal | None:
    return _decimal_or_none(postpass.get("recalculated_shell_dp_pa"))


def _constraint_status(dp: Decimal | None, limit: Decimal) -> str:
    if dp is None:
        return "NOT_EVALUATED"
    return "SATISFIED" if dp <= limit else "NOT_SATISFIED"


def _margin_percent(margin_pa: Decimal, limit: Decimal) -> Decimal | None:
    if limit <= 0:
        return None
    return (margin_pa / limit) * Decimal("100")


def assess_hydraulic_margin_and_robustness(
    case: EngineeringCase,
    *,
    native_candidate_id: str,
    rating_thermal_state: dict[str, Decimal],
    nominal_postpass: dict[str, Any],
    thermal_mesh_level: int | None,
    mesh_convergence: dict[str, Any] | None,
) -> dict[str, Any]:
    """Derive nominal margins and fixed-thermal hydraulic sensitivity from one nominal post-pass."""
    max_shell = case.max_shell_side_pressure_drop_pa
    max_tube = case.max_tube_side_pressure_drop_pa
    shell_dp = _shell_dp_from_postpass(nominal_postpass)
    tube_dp_raw = nominal_postpass.get("recalculated_tube_dp_pa")
    tube_dp = _decimal_or_none(tube_dp_raw)
    shell_margin = (max_shell - shell_dp) if shell_dp is not None else None
    tube_margin = (max_tube - tube_dp) if tube_dp is not None else None
    shell_margin_pct = (
        _margin_percent(shell_margin, max_shell) if shell_margin is not None else None
    )
    tube_nominal = _constraint_status(tube_dp, max_tube)
    shell_nominal = _constraint_status(shell_dp, max_shell)
    nominal_status = nominal_postpass.get("hydraulic_constraint_status", "NOT_EVALUATED")
    if tube_nominal == "NOT_SATISFIED" or shell_nominal == "NOT_SATISFIED":
        nominal_constraint = "NOT_SATISFIED"
    elif tube_nominal == "SATISFIED" and shell_nominal == "SATISFIED":
        nominal_constraint = "SATISFIED"
    else:
        nominal_constraint = "NOT_EVALUATED"

    near_boundary = (
        shell_margin_pct is not None and shell_margin_pct < _NEAR_BOUNDARY_MARGIN_PERCENT
    )

    tube_in_p = rating_thermal_state["tube_inlet_pressure_pa"]
    shell_in_p = rating_thermal_state["shell_inlet_pressure_pa"]
    base_kwargs = {
        "case": case,
        "candidate_id": native_candidate_id,
        "tube_inlet_temperature_k": rating_thermal_state["tube_inlet_temperature_k"],
        "tube_outlet_temperature_k": rating_thermal_state["tube_outlet_temperature_k"],
        "shell_inlet_temperature_k": rating_thermal_state["shell_inlet_temperature_k"],
        "shell_outlet_temperature_k": rating_thermal_state["shell_outlet_temperature_k"],
        "tube_inlet_pressure_pa": tube_in_p,
        "shell_inlet_pressure_pa": shell_in_p,
    }

    shell_base_flow = shell_stream_spec(case).mass_flow_kg_s
    flow_plus = shell_base_flow * (Decimal("1") + _FLOW_PERTURBATION_FRACTION)
    flow_minus = shell_base_flow * (Decimal("1") - _FLOW_PERTURBATION_FRACTION)
    shell_bulk_p = shell_in_p
    if shell_dp is not None:
        shell_bulk_p = shell_in_p - shell_dp / Decimal("2")

    def _sensitivity_postpass(
        *,
        shell_flow: Decimal | None = None,
        shell_eval_p: Decimal | None = None,
    ) -> dict[str, Any]:
        return run_live_thermal_state_hydraulic_postpass(
            **base_kwargs,
            equipment_shell_mass_flow_kg_s_override=shell_flow,
            shell_property_evaluation_pressure_pa=shell_eval_p,
        )

    flow_plus_pp = _sensitivity_postpass(shell_flow=flow_plus)
    flow_minus_pp = _sensitivity_postpass(shell_flow=flow_minus)
    bulk_pp = _sensitivity_postpass(shell_eval_p=shell_bulk_p)

    def _sensitivity_row(label: str, postpass: dict[str, Any]) -> dict[str, Any]:
        dp = _shell_dp_from_postpass(postpass)
        status = _constraint_status(dp, max_shell)
        return {
            "label": label,
            "shell_dp_pa": str(dp) if dp is not None else None,
            "shell_dp_constraint": status,
        }

    shell_flow_sensitivity = {
        "mode": _SENSITIVITY_MODE,
        "disclosure": (
            "±1% shell equipment mass flow rebind; numerical sensitivity example only, "
            "not an owner-approved design tolerance"
        ),
        "cases": [
            _sensitivity_row("shell_flow_plus_1_percent", flow_plus_pp),
            _sensitivity_row("shell_flow_minus_1_percent", flow_minus_pp),
        ],
    }
    shell_bulk_sensitivity = {
        "mode": _SENSITIVITY_MODE,
        "disclosure": "Shell-side bulk property evaluation pressure at inlet minus half nominal Δp",
        "cases": [_sensitivity_row("shell_bulk_pressure_correction", bulk_pp)],
    }

    sensitivity_violation = any(
        row["shell_dp_constraint"] == "NOT_SATISFIED"
        for block in (shell_flow_sensitivity, shell_bulk_sensitivity)
        for row in block["cases"]
    )

    if sensitivity_violation:
        robustness = "NOT_SATISFIED"
    elif near_boundary:
        robustness = "NEAR_CONSTRAINT_BOUNDARY"
    elif nominal_constraint == "SATISFIED":
        robustness = "SATISFIED"
    else:
        robustness = "NOT_EVALUATED"

    mesh_flags = mesh_convergence or {}
    return {
        "NOMINAL_CONSTRAINT_STATUS": nominal_constraint,
        "HYDRAULIC_NOMINAL_STATUS": nominal_status,
        "HYDRAULIC_ROBUSTNESS_STATUS": robustness,
        "SHELL_DP_MARGIN_PA": str(shell_margin) if shell_margin is not None else None,
        "SHELL_DP_MARGIN_PERCENT": (
            str(shell_margin_pct.quantize(Decimal("0.0001")))
            if shell_margin_pct is not None
            else None
        ),
        "TUBE_DP_MARGIN_PA": str(tube_margin) if tube_margin is not None else None,
        "SHELL_NEAR_CONSTRAINT_BOUNDARY": near_boundary,
        "THERMAL_MESH_LEVEL_FOR_HYDRAULICS": thermal_mesh_level,
        "MESH_CONVERGENCE_FOR_HYDRAULICS": {
            k: mesh_flags.get(k)
            for k in (
                "FULL_RATING_CONVERGED",
                "SINGLE_MESH_NUMERIC_VALID",
                "MESH_CONVERGENCE_NOT_EVALUATED",
                "DUTY_MESH_STABLE",
                "OUTLET_TEMPERATURE_MESH_STABLE",
            )
        },
        "SHELL_FLOW_SENSITIVITY": shell_flow_sensitivity,
        "SHELL_BULK_PRESSURE_SENSITIVITY": shell_bulk_sensitivity,
        "FIXED_THERMAL_STATE_HYDRAULIC_SENSITIVITY_MODE": _SENSITIVITY_MODE,
    }


def build_engineering_delivery_receipt(package: dict[str, Any]) -> dict[str, Any]:
    """Single structured receipt from one live-package run (no cross-run field stitching)."""
    mesh = package.get("mesh_convergence") or {}
    results = mesh.get("results") or {}
    per_mesh = mesh.get("per_mesh") or {}
    hydraulic = package.get("hydraulic_receipt") or {}
    margin = package.get("hydraulic_margin") or {}
    receipt: dict[str, Any] = {
        "TASK_ID": "V07_R26C_A_ENGINEERING_DELIVERY_AND_HYDRAULIC_MARGIN",
        "FULL_RATING_CONVERGED": mesh.get("FULL_RATING_CONVERGED"),
        "SINGLE_MESH_NUMERIC_VALID": mesh.get("SINGLE_MESH_NUMERIC_VALID"),
        "MESH_CONVERGENCE_NOT_EVALUATED": mesh.get("MESH_CONVERGENCE_NOT_EVALUATED"),
        "N1_DUTY_W": (per_mesh.get(1) or {}).get("duty_w"),
        "N2_DUTY_W": (per_mesh.get(2) or {}).get("duty_w"),
        "N4_DUTY_W": (per_mesh.get(4) or {}).get("duty_w"),
        "n1_n2_duty_relative_change": mesh.get("n1_n2_duty_relative_change"),
        "n2_n4_duty_relative_change": mesh.get("n2_n4_duty_relative_change"),
        "LIVE_TUBE_DP_PA": hydraulic.get("LIVE_TUBE_DP_PA"),
        "LIVE_SHELL_DP_PA": hydraulic.get("LIVE_SHELL_DP_PA"),
        "TUBE_DP_MARGIN_PA": hydraulic.get("TUBE_DP_MARGIN_PA"),
        "SHELL_DP_MARGIN_PA": margin.get("SHELL_DP_MARGIN_PA")
        or hydraulic.get("SHELL_DP_MARGIN_PA"),
        "SHELL_DP_MARGIN_PERCENT": margin.get("SHELL_DP_MARGIN_PERCENT"),
        "HYDRAULIC_NOMINAL_STATUS": margin.get("HYDRAULIC_NOMINAL_STATUS")
        or hydraulic.get("HYDRAULIC_CONSTRAINT_STATUS"),
        "HYDRAULIC_ROBUSTNESS_STATUS": margin.get("HYDRAULIC_ROBUSTNESS_STATUS"),
        "NOMINAL_CONSTRAINT_STATUS": margin.get("NOMINAL_CONSTRAINT_STATUS"),
        "SHELL_FLOW_SENSITIVITY": margin.get("SHELL_FLOW_SENSITIVITY"),
        "SHELL_BULK_PRESSURE_SENSITIVITY": margin.get("SHELL_BULK_PRESSURE_SENSITIVITY"),
        "GEOMETRY_COMPLETENESS_STATUS": package.get("GEOMETRY_COMPLETENESS_STATUS"),
        "ENGINEERING_SIZING_ELIGIBILITY": package.get("ENGINEERING_SIZING_ELIGIBILITY"),
        "THERMAL_RATING_STATUS": package.get("thermal_rating_status"),
        "N4_WALL_SECONDS": package.get("N4_WALL_SECONDS"),
        "TOTAL_COOLPROP_CALLS": package.get("TOTAL_COOLPROP_CALLS"),
        "PRODUCTION_SIZING_VERIFIED": package.get("PRODUCTION_SIZING_VERIFIED"),
        "PRODUCTION_DESIGN_APPROVED": package.get("PRODUCTION_DESIGN_APPROVED"),
    }
    if 1 in results and hasattr(results[1], "duty_w"):
        receipt["N1_DUTY_W"] = results[1].duty_w
    if 2 in results and hasattr(results[2], "duty_w"):
        receipt["N2_DUTY_W"] = results[2].duty_w
    if 4 in results and hasattr(results[4], "duty_w"):
        receipt["N4_DUTY_W"] = results[4].duty_w
    return receipt
