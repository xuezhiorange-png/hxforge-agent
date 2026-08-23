"""Pure Decimal evaluation of the four frozen TASK-032 formulas."""

from __future__ import annotations

import decimal
from dataclasses import dataclass
from decimal import Decimal, localcontext

from .models import (
    FORMULA_BULK_VELOCITY_ID,
    FORMULA_MASS_VELOCITY_ID,
    FORMULA_PRANDTL_ID,
    FORMULA_REYNOLDS_ID,
)

DECIMAL_PRECISION = 50
ROUNDING_MODE = decimal.ROUND_HALF_EVEN
MASS_VELOCITY_QUANTUM = Decimal("0.0000001")
BULK_VELOCITY_QUANTUM = Decimal("0.0000001")
REYNOLDS_QUANTUM = Decimal("0.0001")
PRANDTL_QUANTUM = Decimal("0.0001")


def decimal_context() -> decimal.Context:
    return decimal.Context(
        prec=DECIMAL_PRECISION,
        rounding=ROUNDING_MODE,
        Emin=-999999,
        Emax=999999,
        capitals=1,
        clamp=0,
    )


@dataclass(frozen=True)
class RawEngineeringValues:
    mass_velocity: Decimal
    bulk_velocity: Decimal
    reynolds: Decimal
    prandtl: Decimal


def evaluate_mass_velocity(mass_flow_rate: Decimal, flow_area: Decimal) -> Decimal:
    with localcontext(decimal_context()):
        return mass_flow_rate / flow_area


def evaluate_bulk_velocity(mass_velocity: Decimal, density: Decimal) -> Decimal:
    with localcontext(decimal_context()):
        return mass_velocity / density


def evaluate_reynolds(
    mass_velocity: Decimal,
    hydraulic_diameter: Decimal,
    dynamic_viscosity: Decimal,
) -> Decimal:
    with localcontext(decimal_context()):
        return mass_velocity * hydraulic_diameter / dynamic_viscosity


def evaluate_prandtl(
    dynamic_viscosity: Decimal,
    specific_heat_capacity: Decimal,
    thermal_conductivity: Decimal,
) -> Decimal:
    with localcontext(decimal_context()):
        return dynamic_viscosity * specific_heat_capacity / thermal_conductivity


def evaluate_raw(
    *,
    mass_flow_rate: Decimal,
    flow_area: Decimal,
    hydraulic_diameter: Decimal,
    density: Decimal,
    dynamic_viscosity: Decimal,
    specific_heat_capacity: Decimal,
    thermal_conductivity: Decimal,
) -> RawEngineeringValues:
    """Evaluate F01-F04 in the frozen graph order."""

    with localcontext(decimal_context()):
        mass_velocity = evaluate_mass_velocity(mass_flow_rate, flow_area)
        bulk_velocity = evaluate_bulk_velocity(mass_velocity, density)
        reynolds = evaluate_reynolds(mass_velocity, hydraulic_diameter, dynamic_viscosity)
        prandtl = evaluate_prandtl(
            dynamic_viscosity,
            specific_heat_capacity,
            thermal_conductivity,
        )
        return RawEngineeringValues(mass_velocity, bulk_velocity, reynolds, prandtl)


def _quantize(raw_value: Decimal, quantum: Decimal) -> Decimal:
    with localcontext(decimal_context()):
        value = raw_value.quantize(quantum, rounding=ROUNDING_MODE)
        return value.copy_abs() if value.is_zero() else value


def quantize_mass_velocity(raw_value: Decimal) -> Decimal:
    return _quantize(raw_value, MASS_VELOCITY_QUANTUM)


def quantize_bulk_velocity(raw_value: Decimal) -> Decimal:
    return _quantize(raw_value, BULK_VELOCITY_QUANTUM)


def quantize_reynolds(raw_value: Decimal) -> Decimal:
    return _quantize(raw_value, REYNOLDS_QUANTUM)


def quantize_prandtl(raw_value: Decimal) -> Decimal:
    return _quantize(raw_value, PRANDTL_QUANTUM)


def quantization_collision(raw_value: Decimal, quantum: Decimal) -> bool:
    return raw_value > 0 and _quantize(raw_value, quantum).is_zero()


__all__ = [
    "BULK_VELOCITY_QUANTUM",
    "DECIMAL_PRECISION",
    "FORMULA_BULK_VELOCITY_ID",
    "FORMULA_MASS_VELOCITY_ID",
    "FORMULA_PRANDTL_ID",
    "FORMULA_REYNOLDS_ID",
    "MASS_VELOCITY_QUANTUM",
    "PRANDTL_QUANTUM",
    "REYNOLDS_QUANTUM",
    "ROUNDING_MODE",
    "RawEngineeringValues",
    "decimal_context",
    "evaluate_bulk_velocity",
    "evaluate_mass_velocity",
    "evaluate_prandtl",
    "evaluate_raw",
    "evaluate_reynolds",
    "quantization_collision",
    "quantize_bulk_velocity",
    "quantize_mass_velocity",
    "quantize_prandtl",
    "quantize_reynolds",
]
