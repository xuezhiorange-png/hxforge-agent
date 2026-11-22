"""Invert counterflow ε-NTU for required UA at target duty (CoolProp capacities)."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v08_thermal_rating.thermal_prescreen_v08 import _epsilon_ntu_counterflow


def required_ua_w_k_for_duty(
    *,
    target_q_w: Decimal,
    c_hot: Decimal,
    c_cold: Decimal,
    t_hot_in: Decimal,
    t_cold_in: Decimal,
) -> Decimal | None:
    c_min = min(c_hot, c_cold)
    if c_min <= 0:
        return None
    q_max = c_min * (t_hot_in - t_cold_in)
    if target_q_w <= 0 or target_q_w > q_max:
        return None
    lo = Decimal("1")
    hi = Decimal("500000")
    for _ in range(64):
        mid = (lo + hi) / 2
        q_mid, _, _, _ = _epsilon_ntu_counterflow(
            ua=mid,
            c_hot=c_hot,
            c_cold=c_cold,
            t_hot_in=t_hot_in,
            t_cold_in=t_cold_in,
        )
        if q_mid < target_q_w:
            lo = mid
        else:
            hi = mid
    return hi


__all__ = ["required_ua_w_k_for_duty"]
