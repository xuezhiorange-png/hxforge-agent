"""Preliminary flow-induced-vibration diagnostics.

Pettigrew/Taylor establish the dimensionless screening variables, but the
publicly admitted evidence here does not provide a complete exchanger- and
array-specific critical-velocity coefficient.  Consequently this module
never emits a guessed critical velocity or a numeric pass/fail limit.
"""

from __future__ import annotations

from decimal import Decimal, DecimalException, localcontext

from .authority import SOURCE_PETTIGREW_TAYLOR_PART1
from .models import FIVScreen, FIVStatus, Task167Request

_PI = Decimal("3.1415926535897932384626433832795028841971693993751")


def build_fiv_screen(request: Task167Request) -> FIVScreen:
    snapshot = request.screening_property_snapshot
    geometry = request.task166_result.bell_geometry
    if geometry is None:
        return FIVScreen(
            status=FIVStatus.WARN,
            source_id=SOURCE_PETTIGREW_TAYLOR_PART1,
            numeric_limit_authority_missing=True,
            numeric_limit_not_guessed=True,
        )
    velocity = (
        snapshot.shell_crossflow_velocity_m_s
        if snapshot.shell_crossflow_velocity_m_s is not None
        else snapshot.shell_bulk_velocity_m_s
    )
    diameter = geometry.tube_outer_diameter_m
    pitch = geometry.tube_pitch_m
    density = snapshot.fluid_density_kg_m3
    span = snapshot.tube_free_span_m
    mass = snapshot.tube_mass_per_length_kg_m
    added_mass = snapshot.added_mass_kg_m
    effective_mass = None if mass is None else mass + (added_mass or Decimal("0"))
    frequency = snapshot.natural_frequency_hz
    reduced = None
    damping_parameter = None
    if (
        velocity is not None
        and frequency is not None
        and frequency > Decimal("0")
        and diameter > Decimal("0")
    ):
        try:
            with localcontext() as context:
                context.prec = 50
                reduced = velocity / (frequency * diameter)
        except DecimalException:
            reduced = None
    if (
        snapshot.damping_ratio is not None
        and effective_mass is not None
        and density is not None
        and snapshot.damping_ratio >= Decimal("0")
        and effective_mass > Decimal("0")
        and density > Decimal("0")
        and diameter > Decimal("0")
    ):
        try:
            with localcontext() as context:
                context.prec = 50
                damping_parameter = (
                    Decimal("2")
                    * _PI
                    * snapshot.damping_ratio
                    * effective_mass
                    / (density * diameter * diameter)
                )
        except DecimalException:
            damping_parameter = None
    return FIVScreen(
        crossflow_velocity_m_s=velocity,
        tube_span_m=span,
        tube_outer_diameter_m=diameter,
        pitch_m=pitch,
        fluid_density_kg_m3=density,
        tube_mass_per_length_kg_m=mass,
        added_mass_kg_m=added_mass,
        effective_mass_kg_m=effective_mass,
        natural_frequency_hz=frequency,
        reduced_velocity=reduced,
        mass_damping_parameter=damping_parameter,
        critical_velocity_m_s=None,
        critical_velocity_ratio=None,
        status=FIVStatus.WARN,
        numeric_limit_authority_missing=True,
        numeric_limit_not_guessed=True,
        source_id=SOURCE_PETTIGREW_TAYLOR_PART1,
        evidence_refs=(SOURCE_PETTIGREW_TAYLOR_PART1, snapshot.evidence_ref),
    )


__all__ = ["build_fiv_screen"]
