"""Flow property inputs and regime classifier for convective heat transfer.

All quantities are in SI units. The regime classifier is a single source
of truth for laminar/transitional/turbulent classification.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

# ---------------------------------------------------------------------------
# Regime thresholds (frozen — must match task card)
# ---------------------------------------------------------------------------
LAMINAR_UPPER_RE = 2300.0
TURBULENT_LOWER_RE = 10000.0


class FlowRegime(StrEnum):
    """Flow regime classification."""

    laminar = "laminar"
    transitional = "transitional"
    turbulent = "turbulent"
    invalid = "invalid"


def classify_regime(reynolds_number: float) -> FlowRegime:
    """Classify flow regime from Reynolds number.

    This is the single source of truth for regime classification.
    Returns INVALID for non-finite or negative Re.
    """
    if not math.isfinite(reynolds_number) or reynolds_number < 0:
        return FlowRegime.invalid
    if reynolds_number < LAMINAR_UPPER_RE:
        return FlowRegime.laminar
    if reynolds_number > TURBULENT_LOWER_RE:
        return FlowRegime.turbulent
    return FlowRegime.transitional


class FlowPropertiesInput(BaseModel):
    """Immutable flow property inputs for correlation evaluation.

    All values in SI units. Bulk properties are required; wall properties
    are optional and correlation-dependent.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    mass_flow_kg_s: float
    density_kg_m3: float
    dynamic_viscosity_pa_s: float
    thermal_conductivity_w_m_k: float
    specific_heat_j_kg_k: float
    bulk_temperature_k: float

    # Optional wall properties
    wall_temperature_k: float | None = None
    wall_viscosity_pa_s: float | None = None

    # Direction
    heating: bool = True  # True = heating, False = cooling

    @model_validator(mode="after")
    def _validate_properties(self) -> FlowPropertiesInput:
        for name in (
            "mass_flow_kg_s",
            "density_kg_m3",
            "dynamic_viscosity_pa_s",
            "thermal_conductivity_w_m_k",
            "specific_heat_j_kg_k",
            "bulk_temperature_k",
        ):
            val = getattr(self, name)
            if not math.isfinite(val):
                raise ValueError(f"{name} must be finite, got {val!r}")
        # Physical constraints
        if self.density_kg_m3 <= 0:
            raise ValueError(f"density_kg_m3 must be positive, got {self.density_kg_m3!r}")
        if self.dynamic_viscosity_pa_s <= 0:
            raise ValueError(
                f"dynamic_viscosity_pa_s must be positive, got {self.dynamic_viscosity_pa_s!r}"
            )
        if self.thermal_conductivity_w_m_k <= 0:
            val = self.thermal_conductivity_w_m_k
            raise ValueError(f"thermal_conductivity_w_m_k must be positive, got {val!r}")
        if self.specific_heat_j_kg_k <= 0:
            raise ValueError(
                f"specific_heat_j_kg_k must be positive, got {self.specific_heat_j_kg_k!r}"
            )
        if self.bulk_temperature_k <= 0:
            raise ValueError(
                f"bulk_temperature_k must be positive (absolute), got {self.bulk_temperature_k!r}"
            )
        if self.mass_flow_kg_s < 0:
            raise ValueError(f"mass_flow_kg_s must be non-negative, got {self.mass_flow_kg_s!r}")
        if self.wall_temperature_k is not None and self.wall_temperature_k <= 0:
            raise ValueError(
                f"wall_temperature_k must be positive, got {self.wall_temperature_k!r}"
            )
        if self.wall_viscosity_pa_s is not None and self.wall_viscosity_pa_s <= 0:
            raise ValueError(
                f"wall_viscosity_pa_s must be positive, got {self.wall_viscosity_pa_s!r}"
            )
        return self


def compute_velocity(mass_flow: float, density: float, area: float) -> float:
    """Compute mean velocity: v = m_dot / (ρ × A)."""
    if area <= 0 or not math.isfinite(area):
        raise ValueError(f"area must be finite positive, got {area!r}")
    if density <= 0 or not math.isfinite(density):
        raise ValueError(f"density must be finite positive, got {density!r}")
    return mass_flow / (density * area)


def compute_reynolds(density: float, velocity: float, dh: float, viscosity: float) -> float:
    """Compute Reynolds number: Re = ρ v D_h / μ."""
    for name, val in [
        ("density", density),
        ("velocity", velocity),
        ("dh", dh),
        ("viscosity", viscosity),
    ]:
        if not math.isfinite(val) or val <= 0:
            raise ValueError(f"{name} must be finite positive, got {val!r}")
    return density * velocity * dh / viscosity


def compute_prandtl(cp: float, mu: float, k: float) -> float:
    """Compute Prandtl number: Pr = cp × μ / k."""
    for name, val in [("cp", cp), ("mu", mu), ("k", k)]:
        if not math.isfinite(val) or val <= 0:
            raise ValueError(f"{name} must be finite positive, got {val!r}")
    return cp * mu / k


def compute_heat_transfer_coefficient(nu: float, k: float, dh: float) -> float:
    """Compute local heat-transfer coefficient: h = Nu × k / D_char."""
    for name, val in [("nu", nu), ("k", k), ("dh", dh)]:
        if not math.isfinite(val) or val <= 0:
            raise ValueError(f"{name} must be finite positive, got {val!r}")
    return nu * k / dh
