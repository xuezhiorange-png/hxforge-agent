"""Pure engineering computation: reference velocity, pressure loss.

§6 — Frozen local-loss physics.
"""

from __future__ import annotations

from decimal import Decimal, localcontext

from hexagent.exchangers.shell_tube.tube_side_local_loss.decimal_identity import (
    PRESSURE_LOSS_QUANTUM,
    REFERENCE_VELOCITY_QUANTUM,
    quantize_task028_decimal,
    task028_decimal_context,
)


def compute_local_loss_component(
    *,
    density_kg_m3: Decimal,
    mass_flow_rate_kg_s: Decimal,
    reference_flow_area_m2: Decimal,
    loss_coefficient: Decimal,
    multiplicity: int,
) -> tuple[Decimal, Decimal, Decimal]:
    """§18.1 — Pure local-loss engineering computation.

    All inputs must be already validated and canonicalized.

    PRESSURE_CALC_USES_QUANTIZED_REFERENCE_VELOCITY=YES
    ACTIVE_TUBE_COUNT_MULTIPLIER=NO
    TASK026_BULK_VELOCITY_IMPLICIT_REUSE=NO
    TOTAL_PRESSURE_DROP_COMPOSITION=NO

    Returns: (reference_velocity_m_s, single_occurrence_pa, component_pa)
    """
    with localcontext(task028_decimal_context()):
        reference_velocity = mass_flow_rate_kg_s / (density_kg_m3 * reference_flow_area_m2)
        reference_velocity = quantize_task028_decimal(
            reference_velocity, REFERENCE_VELOCITY_QUANTUM
        )

        single_occurrence = loss_coefficient * density_kg_m3 * reference_velocity**2 / 2
        single_occurrence = quantize_task028_decimal(single_occurrence, PRESSURE_LOSS_QUANTUM)

        component = multiplicity * single_occurrence
        component = quantize_task028_decimal(component, PRESSURE_LOSS_QUANTUM)

        return reference_velocity, single_occurrence, component


__all__ = [
    "compute_local_loss_component",
]
