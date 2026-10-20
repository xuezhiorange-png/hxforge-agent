"""Map general engineering case fields to frozen Task173/Task172 solver bindings."""

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    SHELL_INLET_T_K,
    SHELL_MASS_FLOW_KG_S,
    TUBE_INLET_T_K,
    TUBE_MASS_FLOW_KG_S,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV1

_BINDING_SCHEMA = "hxforge.input-to-solver-binding.v1"


def build_input_to_solver_binding(case: GeneralEngineeringCaseV1) -> dict[str, Any]:
    """Produce a disclosure table for engineering review (not a solver input file)."""
    convention = case.heat_transfer_convention()
    rows: list[dict[str, Any]] = [
        {
            "user_field": "cold_side.mass_flow_kg_s",
            "user_value": str(case.cold_side.mass_flow_kg_s),
            "solver_parameter": "Task173 TUBE_MASS_FLOW_KG_S / Task172 tube_mass_flow_kg_s",
            "solver_value": str(TUBE_MASS_FLOW_KG_S),
            "participates_in_rating_kernel": case.cold_side.mass_flow_kg_s == TUBE_MASS_FLOW_KG_S,
            "notes": "Tube stream (kernel HOT role).",
        },
        {
            "user_field": "hot_side.mass_flow_kg_s",
            "user_value": str(case.hot_side.mass_flow_kg_s),
            "solver_parameter": "Task173 SHELL_MASS_FLOW_KG_S / Task172 shell_mass_flow_kg_s",
            "solver_value": str(SHELL_MASS_FLOW_KG_S),
            "participates_in_rating_kernel": case.hot_side.mass_flow_kg_s == SHELL_MASS_FLOW_KG_S,
            "notes": "Shell stream (kernel COLD role).",
        },
        {
            "user_field": "cold_side.inlet_temperature_k",
            "user_value": str(case.cold_side.inlet_temperature_k),
            "solver_parameter": "Task173 TUBE_INLET_T_K (frozen service constant)",
            "solver_value": str(TUBE_INLET_T_K),
            "participates_in_rating_kernel": False,
            "notes": "Metadata/reporting until native inlet authority is wired.",
        },
        {
            "user_field": "hot_side.inlet_temperature_k",
            "user_value": str(case.hot_side.inlet_temperature_k),
            "solver_parameter": "Task173 SHELL_INLET_T_K (frozen service constant)",
            "solver_value": str(SHELL_INLET_T_K),
            "participates_in_rating_kernel": False,
            "notes": "Metadata/reporting until native inlet authority is wired.",
        },
        {
            "user_field": "cold_side.inlet_pressure_pa",
            "user_value": str(case.cold_side.inlet_pressure_pa),
            "solver_parameter": "Task173 REFERENCE_PRESSURE_PA",
            "solver_value": "101325",
            "participates_in_rating_kernel": False,
            "notes": "Local property states use 101325 Pa absolute.",
        },
        {
            "user_field": "hot_side.inlet_pressure_pa",
            "user_value": str(case.hot_side.inlet_pressure_pa),
            "solver_parameter": "Task173 REFERENCE_PRESSURE_PA",
            "solver_value": "101325",
            "participates_in_rating_kernel": False,
            "notes": "Local property states use 101325 Pa absolute.",
        },
        {
            "user_field": "target_duty_w",
            "user_value": str(case.target_duty_w),
            "solver_parameter": "SizingRequirementAuthority.required_duty_w",
            "solver_value": str(case.target_duty_w),
            "participates_in_rating_kernel": True,
            "notes": "Sizing constraint evaluation only; mesh shooting uses kernel boundaries.",
        },
        {
            "user_field": "candidate_constraints.*",
            "user_value": case.candidate_constraints.model_dump(mode="json"),
            "solver_parameter": "Task168 discrete authorities + Task171 materialization",
            "solver_value": "native candidate chain",
            "participates_in_rating_kernel": True,
            "notes": (
                "When bind_task172_c3_reference_geometry=true, geometry matches the "
                "C3-qualified implementation-validation reference (Task025 area/Re)."
            ),
        },
    ]
    return {
        "schema_version": _BINDING_SCHEMA,
        "engineering_case_id": case.engineering_case_id,
        "physical_side_role_parity": convention["kernel_thermal_variant"],
        "actual_thermal_boundary_binding": {
            "tube_role": "HOT",
            "shell_role": "COLD",
            "tube_inlet_temperature_k": str(TUBE_INLET_T_K),
            "shell_inlet_temperature_k": str(SHELL_INLET_T_K),
            "reference_pressure_pa": "101325",
        },
        "bind_task172_c3_reference_geometry": case.bind_task172_c3_reference_geometry,
        "rows": rows,
    }


def write_input_to_solver_binding(case: GeneralEngineeringCaseV1, path: Any) -> None:
    import json
    from pathlib import Path

    target = Path(path)
    target.write_text(
        json.dumps(build_input_to_solver_binding(case), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
