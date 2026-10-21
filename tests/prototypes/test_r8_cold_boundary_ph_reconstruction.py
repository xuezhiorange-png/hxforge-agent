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
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
    build_native_cell_context,
    run_mesh_numeric_with_profile,
)

R7_CASE = (
    __import__("pathlib").Path(__file__).resolve().parents[2]
    / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_tube_hot_shell_cold_r7.json"
)


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


def test_case_b_n1_mesh_numeric_valid() -> None:
    case = load_general_engineering_case_json(R7_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    native = build_native_cell_context(case, selection=sel)
    mesh, _profile, _obs = run_mesh_numeric_with_profile(
        native,
        subdivisions=1,
        case=case,
        enable_live_thermal_boundary=True,
        enable_ephemeral_tp_cache=False,
    )
    assert mesh["status"] == "NUMERIC_VALID"
    assert mesh["low_mesh_numeric_valid"] is True
