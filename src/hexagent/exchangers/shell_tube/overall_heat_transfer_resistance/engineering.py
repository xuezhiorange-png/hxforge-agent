"""Numerical authority for the TASK-037 wall and surface terms."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from .decimal_math import (
    RATIO_QUANTUM_DECIMAL,
    WALL_OUTPUT_QUANTUM_DECIMAL,
    decimal_ln,
    quantize_half_even,
    validate_positive_finite_decimal,
    working_decimal_context,
)


@dataclass(frozen=True)
class WallResistanceOutputs:
    """The two owned TASK037 wall projections."""

    outer_to_inner_area_ratio: Decimal
    wall_bundle_conduction_resistance_k_w: Decimal
    wall_resistance_outer_surface_m2_k_w: Decimal


def compute_outer_to_inner_area_ratio(
    tube_inner_diameter_m: Decimal,
    tube_outer_diameter_m: Decimal,
) -> Decimal:
    """Compute the cylindrical outer/inner area-basis ratio."""

    inner = validate_positive_finite_decimal(tube_inner_diameter_m, "tube_inner_diameter_m")
    outer = validate_positive_finite_decimal(tube_outer_diameter_m, "tube_outer_diameter_m")
    if outer <= inner:
        raise ValueError("tube_outer_diameter_m must exceed tube_inner_diameter_m")
    with working_decimal_context():
        return quantize_half_even(outer / inner, RATIO_QUANTUM_DECIMAL)


def compute_wall_resistance(
    tube_inner_diameter_m: Decimal,
    tube_outer_diameter_m: Decimal,
    wall_conductivity_w_m_k: Decimal,
    task025_internal_heat_transfer_surface_area_m2: Decimal,
) -> WallResistanceOutputs:
    """Compute the frozen cylindrical wall projections.

    The numerical bundle term uses only the public, result-hash-protected
    TASK025 area.  No heat-transfer length, active count, inverse area
    reconstruction, or upstream equation is accepted as an argument.
    """

    inner = validate_positive_finite_decimal(tube_inner_diameter_m, "tube_inner_diameter_m")
    outer = validate_positive_finite_decimal(tube_outer_diameter_m, "tube_outer_diameter_m")
    conductivity = validate_positive_finite_decimal(
        wall_conductivity_w_m_k, "wall_conductivity_w_m_k"
    )
    public_area = validate_positive_finite_decimal(
        task025_internal_heat_transfer_surface_area_m2,
        "task025_internal_heat_transfer_surface_area_m2",
    )
    if outer <= inner:
        raise ValueError("tube_outer_diameter_m must exceed tube_inner_diameter_m")
    with working_decimal_context():
        ln_ratio = decimal_ln(outer / inner)
        bundle_raw = (inner * ln_ratio) / (Decimal(2) * conductivity * public_area)
        outer_raw = (outer * ln_ratio) / (Decimal(2) * conductivity)
        return WallResistanceOutputs(
            outer_to_inner_area_ratio=quantize_half_even(outer / inner, RATIO_QUANTUM_DECIMAL),
            wall_bundle_conduction_resistance_k_w=quantize_half_even(
                bundle_raw, WALL_OUTPUT_QUANTUM_DECIMAL
            ),
            wall_resistance_outer_surface_m2_k_w=quantize_half_even(
                outer_raw, WALL_OUTPUT_QUANTUM_DECIMAL
            ),
        )


# Compatibility aliases used by earlier design vocabulary.
compute_cylindrical_wall_resistance = compute_wall_resistance
compute_area_basis_ratio = compute_outer_to_inner_area_ratio


__all__ = [
    "WallResistanceOutputs",
    "compute_area_basis_ratio",
    "compute_cylindrical_wall_resistance",
    "compute_outer_to_inner_area_ratio",
    "compute_wall_resistance",
]
