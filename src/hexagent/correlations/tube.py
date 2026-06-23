"""Circular tube single-phase convective heat-transfer correlations.

Implements:
- C1: tube_laminar_cwt — Nu = 3.66 (fully developed, constant wall temperature)
- C2: tube_laminar_chf — Nu = 4.36 (fully developed, constant heat flux)
- C3: tube_turbulent_gnielinski — Gnielinski correlation with Petukhov friction factor

All equations reference Incropera, DeWitt, Bergman, Lavine,
"Fundamentals of Heat and Mass Transfer," 7th Edition, Wiley, 2011.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class TubeLaminarCWT:
    """C1: Tube laminar, constant wall temperature.

    Nu_D = 3.66
    Source: Incropera et al., 7th ed., Table 8.1
    Valid for: Re < 2300, Pr > 0.6, fully developed flow and thermal fields.
    Nu is based on tube inside diameter (= hydraulic diameter).
    """

    correlation_id: str = "tube_laminar_cwt"
    version: str = "1.0.0"
    source_title: str = "Fundamentals of Heat and Mass Transfer"
    source_authors: str = "Incropera, F.P., DeWitt, D.P., Bergman, T.L., Lavine, A.S."
    source_year: int = 2011
    source_edition: str = "7th"
    source_reference: str = "Table 8.1"
    supported_geometry: str = "circular_tube"
    flow_regime: str = "laminar"
    boundary_condition: str = "constant_wall_temperature"
    reynolds_max: float = 2300.0
    prandtl_min: float = 0.6
    prandtl_max: float = float("inf")
    requires_wall_viscosity: bool = False
    priority: int = 10
    nusselt_basis: str = "inside_diameter"

    def evaluate(self) -> float:
        """Return Nu_D = 3.66."""
        return 3.66


@dataclass(frozen=True)
class TubeLaminarCHF:
    """C2: Tube laminar, constant heat flux.

    Nu_D = 4.36
    Source: Incropera et al., 7th ed., Table 8.1
    Valid for: Re < 2300, Pr > 0.6, fully developed flow and thermal fields.
    Nu is based on tube inside diameter (= hydraulic diameter).
    """

    correlation_id: str = "tube_laminar_chf"
    version: str = "1.0.0"
    source_title: str = "Fundamentals of Heat and Mass Transfer"
    source_authors: str = "Incropera, F.P., DeWitt, D.P., Bergman, T.L., Lavine, A.S."
    source_year: int = 2011
    source_edition: str = "7th"
    source_reference: str = "Table 8.1"
    supported_geometry: str = "circular_tube"
    flow_regime: str = "laminar"
    boundary_condition: str = "constant_heat_flux"
    reynolds_max: float = 2300.0
    prandtl_min: float = 0.6
    prandtl_max: float = float("inf")
    requires_wall_viscosity: bool = False
    priority: int = 10
    nusselt_basis: str = "inside_diameter"

    def evaluate(self) -> float:
        """Return Nu_D = 4.36."""
        return 4.36


@dataclass(frozen=True)
class TubeTurbulentGnielinski:
    """C3: Tube turbulent, Gnielinski correlation.

    Nu_D = (f/8)(Re_D - 1000)Pr / [1 + 12.7(f/8)^0.5 (Pr^{2/3} - 1)]

    Friction factor (Petukhov):
    f = (0.790 ln(Re) - 1.64)^{-2}

    Source: Gnielinski, V., Int. Chem. Eng., Vol. 16, No. 2, pp. 359-368, 1976.
    Friction factor source: Petukhov, B.S., Advances in Heat Transfer, Vol. 6, 1970.
    Nu is based on tube inside diameter (= hydraulic diameter).
    """

    correlation_id: str = "tube_turbulent_gnielinski"
    version: str = "1.0.0"
    source_title: str = (
        "New Equations for Heat and Mass Transfer in Turbulent Pipe and Channel Flow"
    )
    source_authors: str = "Gnielinski, V."
    source_year: int = 1976
    source_edition: str = ""
    source_reference: str = "Int. Chem. Eng., Vol. 16, No. 2, pp. 359-368"
    supported_geometry: str = "circular_tube"
    flow_regime: str = "turbulent"
    boundary_condition: str = "both"
    reynolds_min: float = 3000.0
    reynolds_max: float = 5e6
    prandtl_min: float = 0.5
    prandtl_max: float = 2000.0
    requires_wall_viscosity: bool = False
    priority: int = 10
    nusselt_basis: str = "inside_diameter"

    def petukhov_friction_factor(self, reynolds: float) -> float:
        """Petukhov friction factor: f = (0.790 ln(Re) - 1.64)^{-2}."""
        if reynolds <= 0 or not math.isfinite(reynolds):
            raise ValueError(f"Reynolds must be finite positive, got {reynolds!r}")
        return (0.790 * math.log(reynolds) - 1.64) ** (-2)

    def evaluate(self, reynolds: float, prandtl: float) -> float:
        """Compute Nu_D using Gnielinski correlation."""
        if reynolds < self.reynolds_min or reynolds > self.reynolds_max:
            raise ValueError(
                f"Reynolds {reynolds} outside valid range "
                f"[{self.reynolds_min}, {self.reynolds_max}]"
            )
        if prandtl < self.prandtl_min or prandtl > self.prandtl_max:
            raise ValueError(
                f"Prandtl {prandtl} outside valid range [{self.prandtl_min}, {self.prandtl_max}]"
            )
        f = self.petukhov_friction_factor(reynolds)
        f8 = f / 8.0
        numerator = f8 * (reynolds - 1000.0) * prandtl
        denominator = 1.0 + 12.7 * math.sqrt(f8) * (prandtl ** (2.0 / 3.0) - 1.0)
        result: float = numerator / denominator
        return result


# ---------------------------------------------------------------------------
# Registry of all tube correlations
# ---------------------------------------------------------------------------
TUBE_CORRELATIONS = {
    "tube_laminar_cwt": TubeLaminarCWT,
    "tube_laminar_chf": TubeLaminarCHF,
    "tube_turbulent_gnielinski": TubeTurbulentGnielinski,
}
