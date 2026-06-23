"""Concentric annulus single-phase convective heat-transfer correlations.

Implements:
- C4: annulus_laminar_inner_chf — Laminar Nu for inner wall heated, outer insulated
- C5: annulus_turbulent_gnielinski_dh — Hydraulic-diameter adaptation of Gnielinski

Sources:
- C4: Kays, W.M., Crawford, M.E., "Convective Heat and Mass Transfer,"
  3rd Edition, McGraw-Hill, 1993, Table 8-2.
- C5: Kays & Crawford, Ch. 10; Gnielinski (1976) adapted with D_h.

C4 Nu_i is based on inner tube outside diameter D_i.
C5 Nu_h is based on hydraulic diameter D_h.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Kays & Crawford Table 8-2: Laminar Nu for annulus, inner wall heated,
# outer insulated. Values are Nu_i based on inner tube outside diameter.
# Diameter ratio κ = D_inner / D_outer
#
# VERIFIED data points only (finite values):
#   κ = 0.1   → Nu_i = 4.85
#   κ = 0.25  → Nu_i = 5.70
#   κ = 0.5   → Nu_i = 7.30
#   κ = 0.75  → Nu_i = 10.10
#
# κ < 0.1 and κ > 0.75 are OUTSIDE the verified range.
# No extrapolation is performed; these are BLOCKED.
# ---------------------------------------------------------------------------
_KAYS_TABLE_KAPPA: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75)
_KAYS_TABLE_NU_I: tuple[float, ...] = (4.85, 5.70, 7.30, 10.10)

# Verified range bounds (frozen)
_KAPPA_ABSOLUTE_MIN = 0.1
_KAPPA_ABSOLUTE_MAX = 0.75


def _interpolate_nu_laminar_inner(kappa: float) -> float:
    """Interpolate Nu_i from Kays Table 8-2 for inner wall heated, outer insulated.

    kappa = D_inner / D_outer.
    Valid range: [0.1, 0.75] inclusive (verified data points only).
    Linear interpolation between verified data points.
    No extrapolation outside verified range.
    A small tolerance (1e-9) is applied for floating-point boundary comparison.
    """
    # Tolerance for floating-point boundary comparison
    _TOL = 1e-9
    if kappa < _KAPPA_ABSOLUTE_MIN - _TOL or kappa > _KAPPA_ABSOLUTE_MAX + _TOL:
        raise ValueError(
            f"kappa={kappa!r} is outside verified table range "
            f"[{_KAPPA_ABSOLUTE_MIN}, {_KAPPA_ABSOLUTE_MAX}]. "
            f"No extrapolation is permitted."
        )
    # Clamp to table range to handle floating-point edge cases
    kappa_clamped = max(_KAPPA_ABSOLUTE_MIN, min(_KAPPA_ABSOLUTE_MAX, kappa))

    # Linear interpolation between verified data points
    for i in range(len(_KAYS_TABLE_KAPPA) - 1):
        k0 = _KAYS_TABLE_KAPPA[i]
        nu0 = _KAYS_TABLE_NU_I[i]
        k1 = _KAYS_TABLE_KAPPA[i + 1]
        nu1 = _KAYS_TABLE_NU_I[i + 1]
        if k0 <= kappa_clamped <= k1:
            t = (kappa_clamped - k0) / (k1 - k0)
            return nu0 + t * (nu1 - nu0)

    raise ValueError(f"Interpolation failed for kappa={kappa!r}")


@dataclass(frozen=True)
class AnnulusLaminarInnerCHF:
    """C4: Annulus laminar, inner wall heated, outer insulated.

    Nu_i interpolated from Kays & Crawford Table 8-2.
    Based on inner tube outside diameter D_i.
    Valid for: Re_h < 2300, Pr > 0.6, 0.1 <= κ <= 0.75.
    h_i = Nu_i * k / D_i  (NOT D_h).
    """

    correlation_id: str = "annulus_laminar_inner_chf"
    version: str = "1.0.0"
    source_title: str = "Convective Heat and Mass Transfer"
    source_authors: str = "Kays, W.M., Crawford, M.E."
    source_year: int = 1993
    source_edition: str = "3rd"
    source_reference: str = "Table 8-2"
    supported_geometry: str = "concentric_annulus"
    flow_regime: str = "laminar"
    boundary_condition: str = "inner_wall_heated"
    reynolds_max: float = 2300.0
    prandtl_min: float = 0.6
    prandtl_max: float = float("inf")
    diameter_ratio_min: float = _KAPPA_ABSOLUTE_MIN  # inclusive
    diameter_ratio_max: float = _KAPPA_ABSOLUTE_MAX  # inclusive
    requires_wall_viscosity: bool = False
    priority: int = 10
    nusselt_basis: str = "inside_diameter"  # D_i, inner tube OD

    def evaluate(self, diameter_ratio: float) -> float:
        """Compute Nu_i from Kays table interpolation."""
        return _interpolate_nu_laminar_inner(diameter_ratio)


@dataclass(frozen=True)
class AnnulusTurbulentGnielinskiDH:
    """C5: Annulus turbulent — hydraulic-diameter adaptation of Gnielinski.

    Nu_h = (f/8)(Re_h - 1000)Pr / [1 + 12.7(f/8)^0.5 (Pr^{2/3} - 1)]

    This is explicitly an ADAPTATION — marked as such in metadata.
    Not an original annulus correlation. Has limitation warning.

    Source: Kays & Crawford, Ch. 10 (hydraulic diameter approximation);
    Gnielinski (1976) for the Nusselt equation.
    Nu is based on hydraulic diameter D_h.
    """

    correlation_id: str = "annulus_turbulent_gnielinski_dh"
    version: str = "1.0.0"
    source_title: str = "Gnielinski correlation adapted to annulus via hydraulic diameter"
    source_authors: str = "Gnielinski, V. (adapted per Kays & Crawford Ch. 10)"
    source_year: int = 1976
    source_edition: str = ""
    source_reference: str = "Int. Chem. Eng. Vol. 16, adapted per Kays & Crawford 3rd ed. Ch. 10"
    supported_geometry: str = "concentric_annulus"
    flow_regime: str = "turbulent"
    boundary_condition: str = "both"
    reynolds_min: float = 3000.0
    reynolds_max: float = 5e6
    prandtl_min: float = 0.5
    prandtl_max: float = 2000.0
    diameter_ratio_min: float = 0.0
    diameter_ratio_max: float = 1.0
    requires_wall_viscosity: bool = False
    is_adaptation: bool = True
    adaptation_limitation: str = (
        "Hydraulic-diameter approximation may underpredict heat transfer "
        "for highly asymmetric heating in annuli with large diameter ratios. "
        "Consult Kays & Crawford for corrections."
    )
    priority: int = 5  # Lower due to adaptation status
    nusselt_basis: str = "hydraulic_diameter"

    def petukhov_friction_factor(self, reynolds: float) -> float:
        """Petukhov friction factor: f = (0.790 ln(Re) - 1.64)^{-2}."""
        if reynolds <= 0 or not math.isfinite(reynolds):
            raise ValueError(f"Reynolds must be finite positive, got {reynolds!r}")
        return (0.790 * math.log(reynolds) - 1.64) ** (-2)

    def evaluate(self, reynolds_h: float, prandtl: float) -> float:
        """Compute Nu_h using hydraulic-diameter adapted Gnielinski."""
        if reynolds_h < self.reynolds_min or reynolds_h > self.reynolds_max:
            raise ValueError(
                f"Reynolds_h {reynolds_h} outside valid range "
                f"[{self.reynolds_min}, {self.reynolds_max}]"
            )
        if prandtl < self.prandtl_min or prandtl > self.prandtl_max:
            raise ValueError(
                f"Prandtl {prandtl} outside valid range [{self.prandtl_min}, {self.prandtl_max}]"
            )
        f = self.petukhov_friction_factor(reynolds_h)
        f8 = f / 8.0
        numerator = f8 * (reynolds_h - 1000.0) * prandtl
        denominator = 1.0 + 12.7 * math.sqrt(f8) * (prandtl ** (2.0 / 3.0) - 1.0)
        result: float = numerator / denominator
        return result


# ---------------------------------------------------------------------------
# Registry of all annulus correlations
# ---------------------------------------------------------------------------
ANNULUS_CORRELATIONS = {
    "annulus_laminar_inner_chf": AnnulusLaminarInnerCHF,
    "annulus_turbulent_gnielinski_dh": AnnulusTurbulentGnielinskiDH,
}
