"""Strict V08 handoff parameter binding (no hidden defaults)."""

from __future__ import annotations

from dataclasses import dataclass

from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_geometry_candidate_generation.errors import V08GeometryGenerationBlocked

_REQUIRED_CONSUMABLE_KEYS = (
    "tube_mass_flow_kg_s",
    "shell_mass_flow_kg_s",
    "tube_inlet_temperature_k",
    "shell_inlet_temperature_k",
    "target_duty_w",
)
_REQUIRED_PRESSURE_KEYS = (
    "max_tube_side_pressure_drop_pa",
    "max_shell_side_pressure_drop_pa",
)


@dataclass(frozen=True)
class V08BoundProcessParameters:
    tube_mass_flow_kg_s: str
    shell_mass_flow_kg_s: str
    tube_inlet_temperature_k: str
    shell_inlet_temperature_k: str
    target_duty_w: str
    max_tube_side_pressure_drop_pa: str
    max_shell_side_pressure_drop_pa: str


def bind_process_parameters(handoff: V08SolverHandoffV1) -> V08BoundProcessParameters:
    """Return handoff process parameters or raise structured block (no silent defaults)."""
    missing: list[str] = []
    params = handoff.consumable_parameters
    for key in _REQUIRED_CONSUMABLE_KEYS:
        value = params.get(key)
        if value is None or str(value).strip() == "":
            missing.append(f"consumable_parameters.{key}")
    for key in _REQUIRED_PRESSURE_KEYS:
        value = handoff.pressure_limits_pa.get(key)
        if value is None or str(value).strip() == "":
            missing.append(f"pressure_limits_pa.{key}")
    if missing:
        raise V08GeometryGenerationBlocked(
            code="BLOCKED_USER_PARAMETER_BINDING",
            message="required V08 solver handoff parameters missing or empty",
            evidence={"missing_fields": ",".join(missing)},
        )
    return V08BoundProcessParameters(
        tube_mass_flow_kg_s=str(params["tube_mass_flow_kg_s"]),
        shell_mass_flow_kg_s=str(params["shell_mass_flow_kg_s"]),
        tube_inlet_temperature_k=str(params["tube_inlet_temperature_k"]),
        shell_inlet_temperature_k=str(params["shell_inlet_temperature_k"]),
        target_duty_w=str(params["target_duty_w"]),
        max_tube_side_pressure_drop_pa=str(handoff.pressure_limits_pa["max_tube_side_pressure_drop_pa"]),
        max_shell_side_pressure_drop_pa=str(
            handoff.pressure_limits_pa["max_shell_side_pressure_drop_pa"]
        ),
    )
