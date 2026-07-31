"""TASK-026 Nusselt selector and Gnielinski computation.

R8 implementation. The selector dispatches on Re and Pr per R6-R7
§6 (applicability envelopes):

  LAMINAR:          Re < 2300,  Pr > 0.6
  TRANSITION:       2300 <= Re < 3000  -> BL_REGIME_NO_CORRELATION_APPLICABLE
  TURBULENT:        3000 <= Re <= 5e6,  0.5 <= Pr <= 2000

Laminar Nu_D constants (R6-R7 §5.2):
  CWT (constant wall temperature):  Nu_D = 3.66
  CHF (constant heat flux):           Nu_D = 4.36

Gnielinski (R6-R7 §5.2):
  f = (0.790 * ln(Re) - 1.64) ** (-2)   -- NOT the reciprocal
  f8 = f / 8
  Nu = (f8 * (Re - 1000) * Pr) / (1 + 12.7 * sqrt(f8) * (Pr**(2/3) - 1))

The exponent is -2 (mandatory). The friction factor is **not**
re-inverted after this step. Mandel test prevents any late
reciprocal.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_primitives import (
    decimal_ln,
    decimal_pow_2_3,
    decimal_sqrt,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    ThermalBoundaryCondition,
)

# R6-R7 §5.2 — LAMINAR constants.
LAMINAR_CWT_NU: Decimal = Decimal("3.66")
LAMINAR_CHF_NU: Decimal = Decimal("4.36")

# R6-R7 §5.2 — Gnielinski constants.
GNIELINSKI_CONST_0790: Decimal = Decimal("0.790")
GNIELINSKI_CONST_164: Decimal = Decimal("1.64")
GNIELINSKI_CONST_127: Decimal = Decimal("12.7")
GNIELINSKI_CONST_1000: Decimal = Decimal("1000")
GNIELINSKI_CONST_8: Decimal = Decimal("8")


@dataclass(frozen=True)
class ApplicabilityResult:
    """Result of the applicability selection (R6-R7 §6)."""

    flow_regime: FlowRegime
    correlation_id: str  # "" if no correlation applies
    correlation_version: str  # "1.0.0" for the 3 admitted correlations
    laminar_nu: Decimal | None  # Decimal constant for laminar; None otherwise
    pr_out_of_envelope: bool  # True if Pr is outside the selector's Pr range


def select_regime(reynolds: Decimal, prandtl: Decimal) -> tuple[FlowRegime, str, str]:
    """R6-R7 §6 — Regime selection only.

    Returns (flow_regime, correlation_id, correlation_version). When
    the regime is TRANSITION, correlation_id is "" and the caller
    must emit BL_REGIME_NO_CORRELATION_APPLICABLE.

    The Pr envelope check is performed separately by check_pr_envelope.
    """
    if not isinstance(reynolds, Decimal):
        raise ValueError("reynolds must be Decimal")
    if not isinstance(prandtl, Decimal):
        raise ValueError("prandtl must be Decimal")
    if reynolds < Decimal(2300):
        return FlowRegime.LAMINAR, "tube_laminar_cwt_or_chf", "1.0.0"
    if reynolds < Decimal(3000):
        return FlowRegime.TRANSITION, "", ""
    return FlowRegime.TURBULENT, "tube_turbulent_gnielinski", "1.0.0"


def check_pr_envelope(flow_regime: FlowRegime, prandtl: Decimal) -> bool:
    """R6-R7 §6.1 / §6.3 — Pr envelope check.

    Returns True if Pr is within the envelope, False otherwise.
    LAMINAR:  Pr > 0.6
    TURBULENT: 0.5 <= Pr <= 2000
    TRANSITION: false (no correlation)
    """
    if flow_regime == FlowRegime.LAMINAR:
        return prandtl > Decimal("0.6")
    if flow_regime == FlowRegime.TURBULENT:
        return Decimal("0.5") <= prandtl <= Decimal("2000")
    return False


def select_laminar_correlation(
    thermal_boundary: ThermalBoundaryCondition,
) -> tuple[str, str, Decimal]:
    """R6-R7 §5.2 — Laminar CWT vs CHF selection.

    Returns (correlation_id, correlation_version, laminar_nu).
    """
    if thermal_boundary == ThermalBoundaryCondition.CWT:
        return "tube_laminar_cwt", "1.0.0", LAMINAR_CWT_NU
    if thermal_boundary == ThermalBoundaryCondition.CHF:
        return "tube_laminar_chf", "1.0.0", LAMINAR_CHF_NU
    raise ValueError(
        f"thermal_boundary must be CWT or CHF; got {thermal_boundary!r}"
    )


def compute_gnielinski_nusselt(
    reynolds: Decimal,
    prandtl: Decimal,
) -> Decimal:
    """R6-R7 §5.2 — Gnielinski Nusselt number, Decimal-only.

    f = (0.790 * ln(Re) - 1.64) ** (-2)   -- NO reciprocal afterwards
    f8 = f / 8
    Nu = (f8 * (Re - 1000) * Pr) / (1 + 12.7 * sqrt(f8) * (Pr**(2/3) - 1))

    All Decimal subexpressions execute in the 200 working-precision
    context per R6-R7 §7.1.
    """
    if not isinstance(reynolds, Decimal):
        raise ValueError("reynolds must be Decimal")
    if not isinstance(prandtl, Decimal):
        raise ValueError("prandtl must be Decimal")
    ln_re = decimal_ln(reynolds)
    f_raw = (GNIELINSKI_CONST_0790 * ln_re - GNIELINSKI_CONST_164)
    # Exponent -2 (mandatory). No reciprocal afterwards.
    f = f_raw ** Decimal("-2")
    f8 = f / GNIELINSKI_CONST_8
    sqrt_f8 = decimal_sqrt(f8)
    pr_two_thirds = decimal_pow_2_3(prandtl)
    numerator = f8 * (reynolds - GNIELINSKI_CONST_1000) * prandtl
    denominator = Decimal(1) + GNIELINSKI_CONST_127 * sqrt_f8 * (pr_two_thirds - Decimal(1))
    return numerator / denominator


def compute_laminar_nusselt(thermal_boundary: ThermalBoundaryCondition) -> Decimal:
    """R6-R7 §5.2 — Laminar constant.

    Returns the verbatim Nu_D constant for the given thermal boundary.
    """
    if thermal_boundary == ThermalBoundaryCondition.CWT:
        return LAMINAR_CWT_NU
    if thermal_boundary == ThermalBoundaryCondition.CHF:
        return LAMINAR_CHF_NU
    raise ValueError(
        f"thermal_boundary must be CWT or CHF; got {thermal_boundary!r}"
    )


__all__ = [
    "LAMINAR_CWT_NU",
    "LAMINAR_CHF_NU",
    "GNIELINSKI_CONST_0790",
    "GNIELINSKI_CONST_164",
    "GNIELINSKI_CONST_127",
    "GNIELINSKI_CONST_1000",
    "GNIELINSKI_CONST_8",
    "ApplicabilityResult",
    "select_regime",
    "check_pr_envelope",
    "select_laminar_correlation",
    "compute_gnielinski_nusselt",
    "compute_laminar_nusselt",
]
