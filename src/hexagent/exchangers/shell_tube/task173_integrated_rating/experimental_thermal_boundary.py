"""Versioned experimental thermal boundary binding for MVP rating (not production authority)."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MIN_J_KG,
    REFERENCE_PRESSURE_PA,
)
from hexagent.properties.base import FluidIdentifier, PropertyProvider

TUBE_INLET_T_K = Decimal("300")
SHELL_INLET_T_K = Decimal("298.15")
TUBE_MASS_FLOW_KG_S = Decimal("12")
SHELL_MASS_FLOW_KG_S = Decimal("20")

EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA: Final = "hxforge.experimental-thermal-boundary.v1"
EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID: Final = "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R7-V1"
EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_TUBE_FLOW_AUTHORITY_ID: Final = (
    "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R18-V1"
)

_ALLOWED_FLUID = "PURE_ORDINARY_WATER"
_TUBE_HOT_SHELL_COLD = "TUBE_HOT_SHELL_COLD"


@dataclass(frozen=True)
class ExperimentalThermalBoundaryBindingV1:
    """Explicit tube/shell inlet binding for experimental Task173 mesh (MVP only)."""

    schema_version: str
    authority_id: str
    thermal_variant: str
    tube_inlet_temperature_k: Decimal
    shell_inlet_temperature_k: Decimal
    tube_mass_flow_kg_s: Decimal
    shell_mass_flow_kg_s: Decimal
    reference_pressure_pa: Decimal
    tube_inlet_enthalpy_j_kg: Decimal
    shell_inlet_enthalpy_j_kg: Decimal


_EXPERIMENTAL_THERMAL_BOUNDARY: ContextVar[ExperimentalThermalBoundaryBindingV1 | None] = (
    ContextVar("task173_experimental_thermal_boundary_v1", default=None)
)


def active_experimental_thermal_boundary() -> ExperimentalThermalBoundaryBindingV1 | None:
    return _EXPERIMENTAL_THERMAL_BOUNDARY.get()


def bind_experimental_thermal_boundary_v1(
    binding: ExperimentalThermalBoundaryBindingV1,
) -> Token[ExperimentalThermalBoundaryBindingV1 | None]:
    return _EXPERIMENTAL_THERMAL_BOUNDARY.set(binding)


def reset_experimental_thermal_boundary(
    token: Token[ExperimentalThermalBoundaryBindingV1 | None],
) -> None:
    _EXPERIMENTAL_THERMAL_BOUNDARY.reset(token)


def _enthalpy_at_tp(
    provider: PropertyProvider,
    temperature_k: Decimal,
    pressure_pa: Decimal,
) -> Decimal:
    state = provider.state_tp(
        FluidIdentifier(name="Water"),
        temperature_k=float(temperature_k),
        pressure_pa=float(pressure_pa),
    )
    return Decimal(str(state.enthalpy_j_kg))


def build_experimental_thermal_boundary_v1(
    *,
    provider: PropertyProvider,
    tube_inlet_temperature_k: Decimal,
    shell_inlet_temperature_k: Decimal,
    tube_mass_flow_kg_s: Decimal = TUBE_MASS_FLOW_KG_S,
    shell_mass_flow_kg_s: Decimal = SHELL_MASS_FLOW_KG_S,
    reference_pressure_pa: Decimal = REFERENCE_PRESSURE_PA,
    allow_live_variable_tube_mass_flow: bool = False,
) -> ExperimentalThermalBoundaryBindingV1:
    """Validate envelope and materialize inlet enthalpies for the experimental mesh path."""
    if shell_mass_flow_kg_s != SHELL_MASS_FLOW_KG_S:
        raise ValueError("experimental thermal boundary: shell mass flow must match frozen kernel")
    if not allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s != TUBE_MASS_FLOW_KG_S:
        raise ValueError("experimental thermal boundary: tube mass flow must match frozen kernel")
    if allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s <= Decimal(0):
        raise ValueError("experimental thermal boundary: tube mass flow must be positive")
    if reference_pressure_pa != REFERENCE_PRESSURE_PA:
        raise ValueError("experimental thermal boundary: reference pressure must match kernel")
    tube_h = _enthalpy_at_tp(provider, tube_inlet_temperature_k, reference_pressure_pa)
    shell_h = _enthalpy_at_tp(provider, shell_inlet_temperature_k, reference_pressure_pa)
    if shell_inlet_temperature_k == SHELL_INLET_T_K and abs(shell_h - H_MIN_J_KG) > Decimal("1e-3"):
        raise ValueError(
            "experimental thermal boundary: shell inlet enthalpy drift vs frozen H_MIN"
        )
    authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID
    if allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s != TUBE_MASS_FLOW_KG_S:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_TUBE_FLOW_AUTHORITY_ID
    return ExperimentalThermalBoundaryBindingV1(
        schema_version=EXPERIMENTAL_THERMAL_BOUNDARY_SCHEMA,
        authority_id=authority_id,
        thermal_variant=_TUBE_HOT_SHELL_COLD,
        tube_inlet_temperature_k=tube_inlet_temperature_k,
        shell_inlet_temperature_k=shell_inlet_temperature_k,
        tube_mass_flow_kg_s=tube_mass_flow_kg_s,
        shell_mass_flow_kg_s=shell_mass_flow_kg_s,
        reference_pressure_pa=reference_pressure_pa,
        tube_inlet_enthalpy_j_kg=tube_h,
        shell_inlet_enthalpy_j_kg=shell_h,
    )


def matches_frozen_reference_boundary(
    binding: ExperimentalThermalBoundaryBindingV1,
) -> bool:
    return (
        binding.tube_inlet_temperature_k == TUBE_INLET_T_K
        and binding.shell_inlet_temperature_k == SHELL_INLET_T_K
        and binding.tube_mass_flow_kg_s == TUBE_MASS_FLOW_KG_S
        and binding.shell_mass_flow_kg_s == SHELL_MASS_FLOW_KG_S
        and binding.reference_pressure_pa == REFERENCE_PRESSURE_PA
    )
