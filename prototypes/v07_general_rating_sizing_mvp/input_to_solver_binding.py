"""Map general engineering case fields to frozen Task173/Task172 solver bindings."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    SHELL_INLET_T_K,
    SHELL_MASS_FLOW_KG_S,
    TUBE_INLET_T_K,
    TUBE_MASS_FLOW_KG_S,
)
from prototypes.v07_general_rating_sizing_mvp.case_streams import (
    shell_stream_spec,
    tube_stream_spec,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase
from prototypes.v07_general_rating_sizing_mvp.variable_tube_mass_flow import (
    experimental_live_variable_tube_mass_flow_enabled,
)

_BINDING_SCHEMA = "hxforge.input-to-solver-binding.v2"


def build_input_to_solver_binding(case: EngineeringCase) -> dict[str, Any]:
    """Produce a disclosure table for engineering review (not a solver input file)."""
    convention = case.heat_transfer_convention()
    tube = tube_stream_spec(case)
    shell = shell_stream_spec(case)
    variable_tube_flow = experimental_live_variable_tube_mass_flow_enabled(case)
    tube_kernel_flow = str(tube.mass_flow_kg_s) if variable_tube_flow else str(TUBE_MASS_FLOW_KG_S)
    rows: list[dict[str, Any]] = [
        {
            "user_field": "tube_side.mass_flow_kg_s",
            "user_value": str(tube.mass_flow_kg_s),
            "solver_parameter": "Task173 effective_tube_mass_flow_kg_s() / Task172 tube_mass_flow_kg_s",
            "solver_value": tube_kernel_flow,
            "participates_in_rating_kernel": variable_tube_flow
            or tube.mass_flow_kg_s == TUBE_MASS_FLOW_KG_S,
            "notes": (
                "Tube equipment side carries the kernel HOT stream. "
                "R18 experimental live binding may propagate user tube mass flow when enabled."
            ),
        },
        {
            "user_field": "shell_side.mass_flow_kg_s",
            "user_value": str(shell.mass_flow_kg_s),
            "solver_parameter": "Task173 SHELL_MASS_FLOW_KG_S / Task172 shell_mass_flow_kg_s",
            "solver_value": str(SHELL_MASS_FLOW_KG_S),
            "participates_in_rating_kernel": shell.mass_flow_kg_s == SHELL_MASS_FLOW_KG_S,
            "notes": "Shell equipment side carries the kernel COLD stream.",
        },
        {
            "user_field": "tube_side.inlet_temperature_k",
            "user_value": str(tube.inlet_temperature_k),
            "solver_parameter": "Task173 effective_tube_inlet_temperature_k()",
            "solver_value": str(TUBE_INLET_T_K),
            "participates_in_rating_kernel": tube.inlet_temperature_k == TUBE_INLET_T_K,
            "notes": (
                "Frozen reference path uses TUBE_INLET_T_K=300 K. "
                "Experimental live binding (R7) may override via context when enabled in MVP runner."
            ),
        },
        {
            "user_field": "shell_side.inlet_temperature_k",
            "user_value": str(shell.inlet_temperature_k),
            "solver_parameter": "Task173 effective_shell_cold_inlet_enthalpy_j_kg()",
            "solver_value": str(SHELL_INLET_T_K),
            "participates_in_rating_kernel": shell.inlet_temperature_k == SHELL_INLET_T_K,
            "notes": (
                "Shell cold inlet enthalpy target defaults to frozen H_MIN at 298.15 K; "
                "experimental binding precomputes enthalpy when live path is enabled."
            ),
        },
        {
            "user_field": "target_duty_w",
            "user_value": str(case.target_duty_w),
            "solver_parameter": "SizingRequirementAuthority.required_duty_w",
            "solver_value": str(case.target_duty_w),
            "participates_in_rating_kernel": True,
            "notes": "Sizing constraint only.",
        },
        {
            "user_field": "candidate_constraints.*",
            "user_value": case.candidate_constraints.model_dump(mode="json"),
            "solver_parameter": "Task168 discrete authorities + Task171 materialization",
            "solver_value": "native candidate chain",
            "participates_in_rating_kernel": True,
            "notes": "C3 reference geometry when bind_task172_c3_reference_geometry=true.",
        },
    ]
    return {
        "schema_version": _BINDING_SCHEMA,
        "engineering_case_id": case.engineering_case_id,
        "engineering_case_schema": case.schema_version,
        "physical_side_role_parity": convention["kernel_thermal_variant"],
        "equipment_thermal_mapping": {
            "tube_equipment_side": "tube_side",
            "shell_equipment_side": "shell_side",
            "tube_thermal_role": "HOT",
            "shell_thermal_role": "COLD",
        },
        "actual_thermal_boundary_binding": {
            "binding_class": "FROZEN_REFERENCE_BOUNDARY",
            "tube_role": "HOT",
            "shell_role": "COLD",
            "tube_inlet_temperature_k": str(TUBE_INLET_T_K),
            "shell_inlet_temperature_k": str(SHELL_INLET_T_K),
            "reference_pressure_pa": "101325",
            "not_bound_to_solver_unless": (
                "MVP runner enables hxforge.experimental-thermal-boundary.v1 context"
            ),
        },
        "bind_task172_c3_reference_geometry": case.bind_task172_c3_reference_geometry,
        "rows": rows,
    }


def write_input_to_solver_binding(case: EngineeringCase, path: Any) -> None:
    import json
    from pathlib import Path

    target = Path(path)
    target.write_text(
        json.dumps(build_input_to_solver_binding(case), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
