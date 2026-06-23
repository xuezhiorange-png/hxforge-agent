"""Flow property inputs and regime classifier for convective heat transfer.

All quantities are in SI units. The regime classifier is a single source
of truth for laminar/transitional/turbulent classification.
"""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class FlowRegime(StrEnum):
    """Flow regime classification."""

    laminar = "laminar"
    transitional = "transitional"
    turbulent = "turbulent"
    invalid = "invalid"


class NusseltBasis(StrEnum):
    """Characteristic length basis for Nusselt number.

    Each correlation declares which diameter its Nu is based on.
    The service uses this to compute h = Nu * k / D_char correctly.
    """

    hydraulic_diameter = "hydraulic_diameter"
    inside_diameter = "inside_diameter"


# ---------------------------------------------------------------------------
# Regime thresholds (frozen — must match task card)
# ---------------------------------------------------------------------------
LAMINAR_UPPER_RE = 2300.0
TURBULENT_LOWER_RE = 10000.0


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


# ---------------------------------------------------------------------------
# Flow property input model
# ---------------------------------------------------------------------------


def _validate_positive_finite(value: float, name: str) -> None:
    """Validate that value is finite and positive."""
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite, got {value!r}")
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value!r}")


def _validate_optional_positive_finite(value: float | None, name: str) -> None:
    """Validate that optional value, if provided, is finite and positive."""
    if value is not None:
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite when provided, got {value!r}")
        if value <= 0:
            raise ValueError(f"{name} must be positive when provided, got {value!r}")


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
        # Mass flow must be strictly positive (zero handled by service layer)
        if self.mass_flow_kg_s < 0:
            raise ValueError(f"mass_flow_kg_s must be non-negative, got {self.mass_flow_kg_s!r}")
        # Required bulk properties
        for name in (
            "density_kg_m3",
            "dynamic_viscosity_pa_s",
            "thermal_conductivity_w_m_k",
            "specific_heat_j_kg_k",
            "bulk_temperature_k",
        ):
            _validate_positive_finite(getattr(self, name), name)

        # Optional wall properties: must be finite and positive if provided
        _validate_optional_positive_finite(self.wall_temperature_k, "wall_temperature_k")
        _validate_optional_positive_finite(self.wall_viscosity_pa_s, "wall_viscosity_pa_s")

        return self


# ---------------------------------------------------------------------------
# Dimensionless number calculations
# ---------------------------------------------------------------------------


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


def compute_heat_transfer_coefficient(nu: float, k: float, d_characteristic: float) -> float:
    """Compute local heat-transfer coefficient: h = Nu × k / D_char."""
    for name, val in [("nu", nu), ("k", k), ("d_char", d_characteristic)]:
        if not math.isfinite(val) or val <= 0:
            raise ValueError(f"{name} must be finite positive, got {val!r}")
    return nu * k / d_characteristic
