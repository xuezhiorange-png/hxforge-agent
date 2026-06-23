"""Concentric annulus single-phase convective heat-transfer correlations.

Implements:
- C4: annulus_laminar_inner_chf — Laminar Nu for inner wall heated, outer insulated
- C5: annulus_turbulent_gnielinski_dh — Hydraulic-diameter adaptation of Gnielinski

Sources:
- C4: Kays, W.M., Crawford, M.E., "Convective Heat and Mass Transfer,"
  3rd Edition, McGraw-Hill, 1993, Chapter 9, Table 9-1.
  NOTE: Source data pending independent verification. Correlation is
  currently metadata_only / unverified. Do NOT claim primary_source_checked.
- C5: Gnielinski (1976) adapted via hydraulic diameter per engineering
  judgment. Kays & Crawford 3rd ed. Ch. 10 citation not independently
  verified for this specific adaptation. Source verification: unverified.

All Nu values in this module are based on the annulus hydraulic diameter D_h,
per the Kays & Crawford convention for annulus Nusselt numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# C4 data status: UNVERIFIED
#
# The reviewer independently confirmed that the fully developed
# asymmetric-heating annulus solution in Kays & Crawford 3rd ed.
# is in Chapter 9, Table 9-1, and the book defines both surface
# Nusselt numbers with the annulus hydraulic diameter D_h.
#
# The previously implemented values (4.85, 5.70, 7.30, 10.10 at
# κ = 0.1, 0.25, 0.5, 0.75) referenced "Table 8-2" and claimed
# D_i basis — both are INCORRECT per the reviewer's independent check.
#
# Until an engineer provides the verified Table 9-1 values with
# correct D_h basis, C4 is marked metadata_only and computation
# is BLOCKED by the service layer.
#
# The interpolation function below is retained as a placeholder
# but the service will not call it until data is verified.
# ---------------------------------------------------------------------------

# Placeholder data — MUST BE REPLACED with verified Table 9-1 values.
# These are NOT claimed as authoritative.
_PLACEHOLDER_KAPPA: tuple[float, ...] = (0.1, 0.25, 0.5, 0.75)
_PLACEHOLDER_NU_DH: tuple[float, ...] = (0.0, 0.0, 0.0, 0.0)  # Placeholder

# Frozen range bounds for the placeholder data
_KAPPA_ABSOLUTE_MIN = 0.1
_KAPPA_ABSOLUTE_MAX = 0.75


def _interpolate_nu_laminar_inner(kappa: float) -> float:
    """Interpolate Nu from placeholder data for inner wall heated, outer insulated.

    WARNING: This function uses UNVERIFIED placeholder data.
    The service layer BLOCKS C4 computation until authoritative
    Table 9-1 values are provided by an engineer.

    kappa = D_inner / D_outer.
    Nu is based on hydraulic diameter D_h (per Kays & Crawford convention).
    """
    raise NotImplementedError(
        "C4 annulus laminar correlation data is pending source verification. "
        "Kays & Crawford 3rd ed. Chapter 9, Table 9-1 values with D_h basis "
        "must be independently verified before computation is enabled."
    )


@dataclass(frozen=True)
class AnnulusLaminarInnerCHF:
    """C4: Annulus laminar, inner wall heated, outer insulated.

    STATUS: metadata_only — source data pending verification.

    Intended source: Kays, W.M., Crawford, M.E., "Convective Heat and Mass
    Transfer," 3rd Edition, McGraw-Hill, 1993, Chapter 9, Table 9-1.

    Per the reviewer's independent check:
    - Nu is based on hydraulic diameter D_h (NOT inner diameter D_i)
    - The previously cited "Table 8-2" is incorrect for this problem
    - The κ/Nu values need re-extraction from the correct table

    Valid for: Re_h < 2300, Pr > 0.6, 0 < κ < 1 (exact bounds TBD).
    h = Nu * k / D_h (once data is verified).
    """

    correlation_id: str = "annulus_laminar_inner_chf"
    version: str = "1.0.0"
    source_title: str = "Convective Heat and Mass Transfer"
    source_authors: str = "Kays, W.M., Crawford, M.E."
    source_year: int = 1993
    source_edition: str = "3rd"
    source_reference: str = "Chapter 9, Table 9-1 (pending verification)"
    supported_geometry: str = "concentric_annulus"
    flow_regime: str = "laminar"
    boundary_condition: str = "inner_wall_heated"
    reynolds_max: float = 2300.0
    prandtl_min: float = 0.6
    prandtl_max: float = float("inf")
    diameter_ratio_min: float = 0.0  # exclusive (TBD after verification)
    diameter_ratio_max: float = 1.0  # exclusive (TBD after verification)
    requires_wall_viscosity: bool = False
    priority: int = 10
    nusselt_basis: str = "hydraulic_diameter"  # Per Kays & Crawford convention

    def evaluate(self, diameter_ratio: float) -> float:
        """Compute Nu from table interpolation.

        RAISES NotImplementedError — C4 is blocked until source data
        is independently verified.
        """
        return _interpolate_nu_laminar_inner(diameter_ratio)


@dataclass(frozen=True)
class AnnulusTurbulentGnielinskiDH:
    """C5: Annulus turbulent — hydraulic-diameter adaptation of Gnielinski.

    Nu_h = (f/8)(Re_h - 1000)Pr / [1 + 12.7(f/8)^0.5 (Pr^{2/3} - 1)]

    This is explicitly an ADAPTATION — marked as such in metadata.
    Not an original annulus correlation. Has limitation warning.

    Source status: The Kays & Crawford 3rd ed. Ch. 10 citation for
    hydraulic-diameter approximation of non-circular ducts has NOT been
    independently verified for this specific annulus adaptation.
    Source verification: unverified.
    Implementation status: implemented (not validated).

    Nu is based on hydraulic diameter D_h.
    """

    correlation_id: str = "annulus_turbulent_gnielinski_dh"
    version: str = "1.0.0"
    source_title: str = "Gnielinski correlation adapted to annulus via hydraulic diameter"
    source_authors: str = "Gnielinski, V. (adaptation per engineering judgment)"
    source_year: int = 1976
    source_edition: str = ""
    source_reference: str = (
        "Int. Chem. Eng. Vol. 16, adapted via D_h (unverified annulus applicability)"
    )
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
        "Hydraulic-diameter approximation is an engineering adaptation, "
        "NOT an original annulus correlation. Kays & Crawford Ch. 10 "
        "citation for non-circular duct DH approximation has not been "
        "independently verified for annulus geometry. May underpredict "
        "heat transfer for highly asymmetric heating in annuli with "
        "large diameter ratios."
    )
    priority: int = 5  # Lower due to adaptation/unverified status
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
