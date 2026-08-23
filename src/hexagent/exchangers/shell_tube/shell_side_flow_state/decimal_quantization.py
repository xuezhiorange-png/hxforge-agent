"""TASK-032 public Decimal quantization boundary."""

from __future__ import annotations

from decimal import Decimal

from .formulas import (
    BULK_VELOCITY_QUANTUM,
    MASS_VELOCITY_QUANTUM,
    PRANDTL_QUANTUM,
    REYNOLDS_QUANTUM,
    quantization_collision,
    quantize_bulk_velocity,
    quantize_mass_velocity,
    quantize_prandtl,
    quantize_reynolds,
)

QUANTIZATION_FIELDS: tuple[str, ...] = (
    "shell_side_mass_velocity_kg_m2_s",
    "shell_side_bulk_velocity_m_s",
    "shell_side_reynolds_number",
    "shell_side_prandtl_number",
)

QUANTIZATION_MAP: dict[str, Decimal] = {
    "shell_side_mass_velocity_kg_m2_s": MASS_VELOCITY_QUANTUM,
    "shell_side_bulk_velocity_m_s": BULK_VELOCITY_QUANTUM,
    "shell_side_reynolds_number": REYNOLDS_QUANTUM,
    "shell_side_prandtl_number": PRANDTL_QUANTUM,
}


def quantize_public(field_name: str, raw_value: Decimal) -> Decimal:
    if field_name == "shell_side_mass_velocity_kg_m2_s":
        return quantize_mass_velocity(raw_value)
    if field_name == "shell_side_bulk_velocity_m_s":
        return quantize_bulk_velocity(raw_value)
    if field_name == "shell_side_reynolds_number":
        return quantize_reynolds(raw_value)
    if field_name == "shell_side_prandtl_number":
        return quantize_prandtl(raw_value)
    raise KeyError(field_name)


__all__ = [
    "BULK_VELOCITY_QUANTUM",
    "MASS_VELOCITY_QUANTUM",
    "PRANDTL_QUANTUM",
    "QUANTIZATION_FIELDS",
    "QUANTIZATION_MAP",
    "REYNOLDS_QUANTUM",
    "quantization_collision",
    "quantize_public",
]
