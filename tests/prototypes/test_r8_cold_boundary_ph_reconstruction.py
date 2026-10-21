"""R8: cold-end PH reconstruction uses TP on isothermal T_MIN interval."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import H_MIN_J_KG
from hexagent.properties.coolprop_provider import CoolPropProvider


def test_ph_below_tmin_on_cold_isotherm_rematerializes_tp() -> None:
    provider = CoolPropProvider()
    binding = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=Decimal("299.80"),
        shell_inlet_temperature_k=Decimal("298.15"),
    )
    mid_h = (H_MIN_J_KG + binding.shell_inlet_enthalpy_j_kg) / Decimal(2)
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        state = t173._state_from_enthalpy(provider, mid_h)
    finally:
        reset_experimental_thermal_boundary(token)
    assert state.snapshot.query_type == "TP"


def test_sub_min_enthalpy_still_blocked() -> None:
    provider = CoolPropProvider()
    with pytest.raises(t173._Stage3Failure) as exc_info:
        t173._state_from_enthalpy(provider, H_MIN_J_KG - Decimal("1"))
    assert exc_info.value.code == "BLOCKED_LOCAL_STATE_RECONSTRUCTION_DOMAIN_EXIT"


def test_cold_ph_rematerialization_rejects_large_temperature_deficit() -> None:
    provider = CoolPropProvider()
    binding = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=Decimal("299.80"),
        shell_inlet_temperature_k=Decimal("298.15"),
    )
    mid_h = (H_MIN_J_KG + binding.shell_inlet_enthalpy_j_kg) / Decimal(2)
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        allowed = t173._cold_ph_rematerialization_allowed(
            shooting_enthalpy_j_kg=mid_h,
            ph_temperature_k=Decimal("298.10"),
            ph_enthalpy_j_kg=mid_h,
            cold_h=binding.shell_inlet_enthalpy_j_kg,
            cold_t=Decimal("298.15"),
        )
    finally:
        reset_experimental_thermal_boundary(token)
    assert allowed is False

