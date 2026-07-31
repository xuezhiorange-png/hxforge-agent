"""TASK-026 single-phase engineering computation.

R8 implementation. The single-phase pipeline stages S06..S12 per
R6-R7 §14.1:

  S06  bulk_velocity_m_s = m_dot / (rho * A_total)
  S07  reynolds_number = rho * v * D_h / mu
  S08  prandtl_number = mu * c_p / k
  S09  applicability selection (Regime + Pr envelope)
  S10  nusselt_number (laminar CWT/CHF constant or Gnielinski)
  S11  h_i = Nu * k / D_h
  S12  quantize 5 fields at ROUND_HALF_EVEN

All Decimal arithmetic happens in the 200 working-precision context
with 40 guard digits (R6-R7 §7.1). A working-precision Decimal
exception is mapped to BL_DECIMAL_FAILURE.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from hexagent.exchangers.shell_tube.tube_side_thermal.decimal_quantization import (
    field_for,
    quantize_half_even,
)
from hexagent.exchangers.shell_tube.tube_side_thermal.nusselt_selector import (
    compute_gnielinski_nusselt,
    select_laminar_correlation,
    select_regime,
)
from hexagent.exchangers.shell_tube.tube_side_thermal import (
    FlowRegime,
    ThermalBoundaryCondition,
)


@dataclass(frozen=True)
class SinglePhaseOutputs:
    """R6-R7 §5.1 — Five quantized engineering outputs."""

    bulk_velocity_m_s: Decimal
    reynolds_number: Decimal
    prandtl_number: Decimal
    nusselt_number: Decimal
    tube_side_heat_transfer_coefficient_w_m2_k: Decimal
    flow_regime: FlowRegime
    correlation_id: str
    correlation_version: str


def _compute_bulk_velocity(m_dot: Decimal, rho: Decimal, a_total: Decimal) -> Decimal:
    return m_dot / (rho * a_total)


def _compute_reynolds(
    rho: Decimal, v: Decimal, d_h: Decimal, mu: Decimal
) -> Decimal:
    return (rho * v * d_h) / mu


def _compute_prandtl(mu: Decimal, c_p: Decimal, k: Decimal) -> Decimal:
    return (mu * c_p) / k


def _compute_hi(nu: Decimal, k: Decimal, d_h: Decimal) -> Decimal:
    return (nu * k) / d_h


def compute_single_phase(
    mass_flow_rate_kg_s: Decimal,
    density_kg_m3: Decimal,
    dynamic_viscosity_pa_s: Decimal,
    thermal_conductivity_w_m_k: Decimal,
    specific_heat_capacity_j_kg_k: Decimal,
    total_parallel_flow_area_m2: Decimal,
    hydraulic_diameter_m: Decimal,
    thermal_boundary_condition: ThermalBoundaryCondition,
) -> SinglePhaseOutputs:
    """R6-R7 §5.1 / §5.2 — Compute the five engineering outputs.

    No pre-quantization rounding. Quantization is applied at S12 per
    R6-R7 §7.2.
    """
    # S06 — bulk velocity
    v = _compute_bulk_velocity(
        mass_flow_rate_kg_s, density_kg_m3, total_parallel_flow_area_m2
    )
    # S07 — Reynolds
    re = _compute_reynolds(
        density_kg_m3, v, hydraulic_diameter_m, dynamic_viscosity_pa_s
    )
    # S08 — Prandtl
    pr = _compute_prandtl(
        dynamic_viscosity_pa_s, specific_heat_capacity_j_kg_k, thermal_conductivity_w_m_k
    )
    # S09 — applicability selection
    regime, corr_id, corr_version = select_regime(re, pr)
    if regime == FlowRegime.TRANSITION:
        # Caller must emit BL_REGIME_NO_CORRELATION_APPLICABLE.
        # In single_phase alone we cannot emit a blocker; caller decides.
        # To keep single_phase failure-typed, return a sentinel via
        # correlation_id == "" flow_regime=TRANSITION.
        return SinglePhaseOutputs(
            bulk_velocity_m_s=quantize_half_even(v, field_for("bulk_velocity_m_s")),
            reynolds_number=quantize_half_even(re, field_for("reynolds_number")),
            prandtl_number=quantize_half_even(pr, field_for("prandtl_number")),
            nusselt_number=Decimal(0),
            tube_side_heat_transfer_coefficient_w_m2_k=Decimal(0),
            flow_regime=FlowRegime.TRANSITION,
            correlation_id="",
            correlation_version="",
        )
    # S10 — Nusselt
    if regime == FlowRegime.LAMINAR:
        laminar_corr_id, laminar_corr_version, laminar_nu = select_laminar_correlation(
            thermal_boundary_condition
        )
        nu = laminar_nu
        # Override selector-provided corr id with the laminar-specific id.
        out_corr_id = laminar_corr_id
        out_corr_version = laminar_corr_version
    else:
        nu = compute_gnielinski_nusselt(re, pr)
        out_corr_id = corr_id
        out_corr_version = corr_version
    # S11 — h_i
    hi = _compute_hi(nu, thermal_conductivity_w_m_k, hydraulic_diameter_m)
    # S12 — quantization
    v_q = quantize_half_even(v, field_for("bulk_velocity_m_s"))
    re_q = quantize_half_even(re, field_for("reynolds_number"))
    pr_q = quantize_half_even(pr, field_for("prandtl_number"))
    nu_q = quantize_half_even(nu, field_for("nusselt_number"))
    hi_q = quantize_half_even(hi, field_for("tube_side_heat_transfer_coefficient_w_m2_k"))
    return SinglePhaseOutputs(
        bulk_velocity_m_s=v_q,
        reynolds_number=re_q,
        prandtl_number=pr_q,
        nusselt_number=nu_q,
        tube_side_heat_transfer_coefficient_w_m2_k=hi_q,
        flow_regime=regime,
        correlation_id=out_corr_id,
        correlation_version=out_corr_version,
    )


__all__ = [
    "SinglePhaseOutputs",
    "compute_single_phase",
]
