"""Acceptance contract V08_KERNEL_RATING_ACCEPTANCE_V1 — independent of Task173 N1/N2/N4."""

# ruff: noqa: E501

from __future__ import annotations

import math
from decimal import Decimal
from typing import Literal

from hexagent.properties.base import FluidIdentifier, PropertyProvider, ReferenceStatePolicy

CONTRACT_ID = "V08_KERNEL_RATING_ACCEPTANCE_V1"

# Derived from SI + CoolProp repeatability at 300 K water, not from Task173 failures.
Q_RELATIVE_TOL = Decimal("1e-6")
Q_ABSOLUTE_TOL_W = Decimal("1.0")
ENERGY_RELATIVE_TOL = Decimal("1e-4")
ENERGY_ABSOLUTE_TOL_W = Decimal("10.0")
PROPERTY_PH_DELTA_H_MAX_J_KG = 1e-6
MAX_ITERATIONS_BUDGET = 32


def analytic_parallel_flow_q(
    *,
    u_w_m2_k: float,
    area_m2: float,
    t_hot_in: float,
    t_cold_in: float,
    m_hot: float,
    m_cold: float,
    cp_hot: float,
    cp_cold: float,
) -> float:
    """Reference: true counterflow LMTD rating Q = U·A·ΔT_lm (F=1), both cp constant."""
    c_h = m_hot * cp_hot
    c_c = m_cold * cp_cold
    if c_h <= 0 or c_c <= 0:
        return 0.0
    q_max = min(c_h, c_c) * (t_hot_in - t_cold_in)
    q_hi = min(q_max, u_w_m2_k * area_m2 * (t_hot_in - t_cold_in))

    def q_at(q: float) -> tuple[float, float, float, float]:
        t_ho = t_hot_in - q / c_h
        t_co = t_cold_in + q / c_c
        d1 = t_hot_in - t_co
        d2 = t_ho - t_cold_in
        if d1 <= 0 or d2 <= 0:
            return q, -1.0, t_ho, t_co
        lm = d1 if abs(d1 - d2) < 1e-12 else (d1 - d2) / math.log(d1 / d2)
        return q, u_w_m2_k * area_m2 * lm - q, t_ho, t_co

    lo, hi = 0.0, q_hi
    for _ in range(48):
        mid = (lo + hi) / 2
        _, res, _, _ = q_at(mid)
        if res < 0:
            hi = mid
        elif res > 0:
            lo = mid
        else:
            return mid
    return (lo + hi) / 2


def property_tp_ph_roundtrip_pass(provider: PropertyProvider, *, t_k: float, p_pa: float) -> bool:
    fluid = FluidIdentifier(name="Water")
    tp = provider.state_tp(fluid, t_k, p_pa)
    ref = getattr(provider, "reference_state_policy", ReferenceStatePolicy.DEF)
    if not isinstance(ref, ReferenceStatePolicy):
        ref = ReferenceStatePolicy.DEF
    ph = provider.state_ph(fluid, p_pa, float(tp.enthalpy_j_kg), reference_state=ref)
    return abs(float(ph.enthalpy_j_kg) - float(tp.enthalpy_j_kg)) <= PROPERTY_PH_DELTA_H_MAX_J_KG


def negative_temperature_cross_blocked(
    *,
    t_tube_in: Decimal,
    t_shell_in: Decimal,
    t_tube_out: Decimal,
    t_shell_out: Decimal,
) -> bool:
    """Return True when scenario is BLOCKED (cross or no driving force)."""
    if t_tube_in <= t_shell_in:
        return True
    if t_tube_out <= t_shell_out:
        return True
    return bool(t_tube_out < t_shell_in or t_shell_out > t_tube_in)


def convergence_pass(
    *,
    q_residual_w: Decimal,
    q_mag_w: Decimal,
    energy_residual_w: Decimal,
    energy_mag_w: Decimal,
) -> bool:
    q_ok = abs(q_residual_w) <= max(Q_ABSOLUTE_TOL_W, Q_RELATIVE_TOL * max(q_mag_w, Decimal("1")))
    e_ok = abs(energy_residual_w) <= max(
        ENERGY_ABSOLUTE_TOL_W, ENERGY_RELATIVE_TOL * max(energy_mag_w, Decimal("1"))
    )
    return q_ok and e_ok


KernelAcceptanceStatus = Literal["PASS", "BLOCKED"]


def kernel_contract_pass(
    *,
    converged: bool,
    energy_balance_pass: bool,
    temperature_cross: bool,
    iterations: int,
) -> KernelAcceptanceStatus:
    if temperature_cross:
        return "BLOCKED"
    if iterations > MAX_ITERATIONS_BUDGET:
        return "BLOCKED"
    if not converged or not energy_balance_pass:
        return "BLOCKED"
    return "PASS"


__all__ = [
    "CONTRACT_ID",
    "MAX_ITERATIONS_BUDGET",
    "analytic_parallel_flow_q",
    "convergence_pass",
    "kernel_contract_pass",
    "negative_temperature_cross_blocked",
    "property_tp_ph_roundtrip_pass",
]
