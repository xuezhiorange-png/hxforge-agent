"""TASK-025 seven hydraulic geometry outputs.

§9 — Seven geometry outputs with the frozen quantums.
"""

from __future__ import annotations

import decimal as _decimal
from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side.canonical import pi_decimal
from hexagent.exchangers.shell_tube.tube_side.decimal_identity import (
    AREA_QUANTUM_M2,
    HYDRAULIC_DIAMETER_QUANTUM_M,
    PERIMETER_QUANTUM_M,
    VOLUME_QUANTUM_M3,
    local_decimal_context,
    quantize_half_even,
    validate_finite_decimal,
    with_signals_cleared,
)


def _to_decimal_str(value: str | Decimal) -> Decimal:
    if isinstance(value, Decimal):
        return validate_finite_decimal(value, "tube_inner_diameter_m")
    if isinstance(value, str):
        return validate_finite_decimal(Decimal(value), "tube_inner_diameter_m")
    raise TypeError(
        f"tube_inner_diameter_m must be Decimal or str; got {type(value).__name__}"
    )


@dataclass(frozen=True)
class HydraulicGeometryOutputs:
    """§9 — Seven quantized hydraulic geometry outputs."""

    single_tube_flow_area_m2: Decimal
    total_parallel_flow_area_m2: Decimal
    flow_cross_section_wetted_perimeter_m: Decimal
    total_flow_cross_section_wetted_perimeter_m: Decimal
    hydraulic_diameter_m: Decimal
    internal_volume_m3: Decimal
    internal_heat_transfer_surface_area_m2: Decimal


def compute_hydraulic_geometry(
    tube_inner_diameter_m: str | Decimal,
    active_tube_count: int,
    internal_flow_length_m: Decimal,
    heat_transfer_length_m: Decimal,
) -> HydraulicGeometryOutputs:
    """§9 — Compute the seven geometry outputs at precision 160 + ROUND_HALF_EVEN.

    All formulas use the exact integer count from the caller; the
    §9.2 hydraulic-diameter formula uses raw integer division so the
    result equals ``tube_inner_diameter_m`` before quantization.
    """
    if not isinstance(active_tube_count, int) or active_tube_count <= 0:
        raise ValueError(
            f"active_tube_count must be a strictly positive int; got {active_tube_count!r}"
        )
    tube_inner_diameter = _to_decimal_str(tube_inner_diameter_m)
    if tube_inner_diameter <= Decimal(0):
        raise ValueError(
            f"tube_inner_diameter_m must be strictly positive; got {tube_inner_diameter!s}"
        )

    pi = pi_decimal()._value
    n = Decimal(active_tube_count)
    flow_length = validate_finite_decimal(internal_flow_length_m, "internal_flow_length_m")
    if flow_length <= Decimal(0):
        raise ValueError("internal_flow_length_m must be strictly positive")
    heat_length = validate_finite_decimal(heat_transfer_length_m, "heat_transfer_length_m")
    if heat_length <= Decimal(0):
        raise ValueError("heat_transfer_length_m must be strictly positive")

    ctx = with_signals_cleared(local_decimal_context())

    with _decimal.localcontext(ctx):
        # §9.1 — unquantized formulas.
        unquantized_single_tube_flow_area_m2 = pi * tube_inner_diameter ** 2 / Decimal(4)
        unquantized_total_parallel_flow_area_m2 = unquantized_single_tube_flow_area_m2 * n

        unquantized_flow_cross_section_wetted_perimeter_m = pi * tube_inner_diameter
        unquantized_total_flow_cross_section_wetted_perimeter_m = (
            unquantized_flow_cross_section_wetted_perimeter_m * n
        )

        unquantized_internal_volume_m3 = (
            unquantized_single_tube_flow_area_m2 * flow_length * n
        )
        unquantized_internal_heat_transfer_surface_area_m2 = (
            unquantized_flow_cross_section_wetted_perimeter_m * heat_length * n
        )

        # §9.2 — hydraulic diameter before quantization equals tube_inner_diameter_m.
        # Validate the identity; quantize tube_inner_diameter directly.
        hydraulic_diameter_m_unquantized = (
            4 * unquantized_total_parallel_flow_area_m2
            / unquantized_total_flow_cross_section_wetted_perimeter_m
        )

    # §9.3 — public quantization map.
    single_tube_flow_area_m2 = quantize_half_even(
        unquantized_single_tube_flow_area_m2, AREA_QUANTUM_M2, "single_tube_flow_area_m2"
    )
    total_parallel_flow_area_m2 = quantize_half_even(
        unquantized_total_parallel_flow_area_m2, AREA_QUANTUM_M2, "total_parallel_flow_area_m2"
    )
    flow_cross_section_wetted_perimeter_m = quantize_half_even(
        unquantized_flow_cross_section_wetted_perimeter_m,
        PERIMETER_QUANTUM_M,
        "flow_cross_section_wetted_perimeter_m",
    )
    total_flow_cross_section_wetted_perimeter_m = quantize_half_even(
        unquantized_total_flow_cross_section_wetted_perimeter_m,
        PERIMETER_QUANTUM_M,
        "total_flow_cross_section_wetted_perimeter_m",
    )
    hydraulic_diameter_m = quantize_half_even(
        hydraulic_diameter_m_unquantized,
        HYDRAULIC_DIAMETER_QUANTUM_M,
        "hydraulic_diameter_m",
    )
    internal_volume_m3 = quantize_half_even(
        unquantized_internal_volume_m3, VOLUME_QUANTUM_M3, "internal_volume_m3"
    )
    internal_heat_transfer_surface_area_m2 = quantize_half_even(
        unquantized_internal_heat_transfer_surface_area_m2,
        AREA_QUANTUM_M2,
        "internal_heat_transfer_surface_area_m2",
    )

    return HydraulicGeometryOutputs(
        single_tube_flow_area_m2=single_tube_flow_area_m2,
        total_parallel_flow_area_m2=total_parallel_flow_area_m2,
        flow_cross_section_wetted_perimeter_m=flow_cross_section_wetted_perimeter_m,
        total_flow_cross_section_wetted_perimeter_m=total_flow_cross_section_wetted_perimeter_m,
        hydraulic_diameter_m=hydraulic_diameter_m,
        internal_volume_m3=internal_volume_m3,
        internal_heat_transfer_surface_area_m2=internal_heat_transfer_surface_area_m2,
    )


__all__ = [
    "HydraulicGeometryOutputs",
    "compute_hydraulic_geometry",
]