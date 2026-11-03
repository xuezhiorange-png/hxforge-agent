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
EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_SHELL_FLOW_AUTHORITY_ID: Final = (
    "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R19-V1"
)
EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_DUAL_FLOW_AUTHORITY_ID: Final = (
    "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R18-R19-V1"
)
EXPERIMENTAL_THERMAL_BOUNDARY_BULK_PRESSURE_R22_AUTHORITY_ID: Final = (
    "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R22-BULK-PRESSURE-V1"
)
EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_WATER_TEMPERATURE_R23_AUTHORITY_ID: Final = (
    "V07-EXPERIMENTAL-THERMAL-BOUNDARY-R23-VARIABLE-WATER-TEMPERATURE-V1"
)

VARIABLE_WATER_TEMPERATURE_MIN_K: Final = Decimal("290")
VARIABLE_WATER_TEMPERATURE_MAX_K: Final = Decimal("320")

REVIEWED_MIN_PRESSURE_PA: Final = Decimal("100000")
REVIEWED_MAX_PRESSURE_PA: Final = Decimal("101325")

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
    tube_property_evaluation_pressure_pa: Decimal
    shell_property_evaluation_pressure_pa: Decimal
    variable_water_temperature_enabled: bool = False


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


def _validate_reviewed_pressure_pa(pressure_pa: Decimal, *, label: str) -> None:
    if pressure_pa < REVIEWED_MIN_PRESSURE_PA or pressure_pa > REVIEWED_MAX_PRESSURE_PA:
        raise ValueError(
            f"experimental thermal boundary: {label} pressure {pressure_pa} Pa "
            f"outside reviewed domain {REVIEWED_MIN_PRESSURE_PA}–{REVIEWED_MAX_PRESSURE_PA} Pa"
        )


def bulk_property_pressure_feedback_active(
    binding: ExperimentalThermalBoundaryBindingV1 | None,
) -> bool:
    if binding is None:
        return False
    return binding.authority_id == EXPERIMENTAL_THERMAL_BOUNDARY_BULK_PRESSURE_R22_AUTHORITY_ID


def variable_water_temperature_active(
    binding: ExperimentalThermalBoundaryBindingV1 | None,
) -> bool:
    if binding is None:
        return False
    return binding.variable_water_temperature_enabled


def admitted_bulk_temperature_min_k(
    binding: ExperimentalThermalBoundaryBindingV1 | None,
) -> Decimal:
    if variable_water_temperature_active(binding):
        return VARIABLE_WATER_TEMPERATURE_MIN_K
    from hexagent.exchangers.shell_tube.task173_integrated_rating.models import T_MIN_K

    return T_MIN_K


def admitted_bulk_temperature_max_k(
    binding: ExperimentalThermalBoundaryBindingV1 | None,
) -> Decimal:
    if variable_water_temperature_active(binding):
        return VARIABLE_WATER_TEMPERATURE_MAX_K
    from hexagent.exchangers.shell_tube.task173_integrated_rating.models import T_MAX_K

    return T_MAX_K


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
    allow_live_variable_shell_mass_flow: bool = False,
    allow_variable_water_temperature: bool = False,
    tube_property_evaluation_pressure_pa: Decimal | None = None,
    shell_property_evaluation_pressure_pa: Decimal | None = None,
) -> ExperimentalThermalBoundaryBindingV1:
    """Validate envelope and materialize inlet enthalpies for the experimental mesh path."""
    if not allow_live_variable_shell_mass_flow and shell_mass_flow_kg_s != SHELL_MASS_FLOW_KG_S:
        raise ValueError("experimental thermal boundary: shell mass flow must match frozen kernel")
    if allow_live_variable_shell_mass_flow and shell_mass_flow_kg_s <= Decimal(0):
        raise ValueError("experimental thermal boundary: shell mass flow must be positive")
    if not allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s != TUBE_MASS_FLOW_KG_S:
        raise ValueError("experimental thermal boundary: tube mass flow must match frozen kernel")
    if allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s <= Decimal(0):
        raise ValueError("experimental thermal boundary: tube mass flow must be positive")
    if reference_pressure_pa != REFERENCE_PRESSURE_PA:
        raise ValueError("experimental thermal boundary: reference pressure must match kernel")
    tube_p = tube_property_evaluation_pressure_pa or reference_pressure_pa
    shell_p = shell_property_evaluation_pressure_pa or reference_pressure_pa
    _validate_reviewed_pressure_pa(tube_p, label="tube property evaluation")
    _validate_reviewed_pressure_pa(shell_p, label="shell property evaluation")
    if allow_variable_water_temperature:
        if tube_inlet_temperature_k < VARIABLE_WATER_TEMPERATURE_MIN_K or (
            tube_inlet_temperature_k > VARIABLE_WATER_TEMPERATURE_MAX_K
        ):
            raise ValueError(
                "experimental thermal boundary: tube inlet temperature out of R23 domain"
            )
        if shell_inlet_temperature_k < VARIABLE_WATER_TEMPERATURE_MIN_K or (
            shell_inlet_temperature_k > VARIABLE_WATER_TEMPERATURE_MAX_K
        ):
            raise ValueError(
                "experimental thermal boundary: shell inlet temperature out of R23 domain"
            )
        if tube_inlet_temperature_k <= shell_inlet_temperature_k:
            raise ValueError("experimental thermal boundary: tube inlet must exceed shell inlet")
    tube_h = _enthalpy_at_tp(provider, tube_inlet_temperature_k, tube_p)
    shell_h = _enthalpy_at_tp(provider, shell_inlet_temperature_k, shell_p)
    if (
        not allow_variable_water_temperature
        and shell_inlet_temperature_k == SHELL_INLET_T_K
        and shell_p == reference_pressure_pa
        and abs(shell_h - H_MIN_J_KG) > Decimal("1e-3")
    ):
        raise ValueError(
            "experimental thermal boundary: shell inlet enthalpy drift vs frozen H_MIN"
        )
    tube_flow_variable = (
        allow_live_variable_tube_mass_flow and tube_mass_flow_kg_s != TUBE_MASS_FLOW_KG_S
    )
    shell_flow_variable = (
        allow_live_variable_shell_mass_flow and shell_mass_flow_kg_s != SHELL_MASS_FLOW_KG_S
    )
    authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_AUTHORITY_ID
    if tube_flow_variable and shell_flow_variable:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_DUAL_FLOW_AUTHORITY_ID
    elif tube_flow_variable:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_TUBE_FLOW_AUTHORITY_ID
    elif shell_flow_variable:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_SHELL_FLOW_AUTHORITY_ID
    bulk_pressure_feedback = tube_p != reference_pressure_pa or shell_p != reference_pressure_pa
    if bulk_pressure_feedback:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_BULK_PRESSURE_R22_AUTHORITY_ID
    elif allow_variable_water_temperature:
        authority_id = EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_WATER_TEMPERATURE_R23_AUTHORITY_ID
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
        tube_property_evaluation_pressure_pa=tube_p,
        shell_property_evaluation_pressure_pa=shell_p,
        variable_water_temperature_enabled=allow_variable_water_temperature,
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
