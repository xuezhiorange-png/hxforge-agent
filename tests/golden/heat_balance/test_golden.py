"""Golden case tests for heat-balance kernel.

Each golden case is a JSON file in ``tests/golden/heat_balance/``
containing input, expected output, and tolerances.  The test replays
the calculation with real CoolProp and asserts the results match
within documented tolerances.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexagent.core.heat_balance import (
    FlowArrangement,
    HeatBalanceInput,
    SolverParams,
    StreamState,
    solve_heat_balance,
)
from hexagent.properties import CoolPropProvider
from hexagent.properties.base import FluidIdentifier

_GOLDEN_DIR = Path(__file__).parent


def _load_golden_cases() -> list[dict]:
    cases = []
    for p in sorted(_GOLDEN_DIR.glob("*.json")):
        with open(p) as f:
            cases.append(json.load(f))
    return cases


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider(cache_size=64)


@pytest.mark.parametrize(
    "case",
    _load_golden_cases(),
    ids=[c["case_id"] for c in _load_golden_cases()],
)
def test_golden_case(case: dict, provider: CoolPropProvider) -> None:
    """Replay a golden case and assert results within tolerances."""
    inp_data = case["input"]
    expected = case["expected"]
    tols = case.get("tolerances", {})

    hot_fluid = inp_data.get("hot_fluid", "Water")
    cold_fluid = inp_data.get("cold_fluid", "Water")

    hot = StreamState(
        fluid_identifier=FluidIdentifier(name=hot_fluid),
        mass_flow_kg_s=inp_data["hot_mass_flow"],
        inlet_temperature_k=inp_data["hot_inlet_t"],
        inlet_pressure_pa=inp_data.get("hot_pressure", 200_000.0),
        outlet_temperature_k=inp_data.get("hot_outlet_t"),
    )

    cold = StreamState(
        fluid_identifier=FluidIdentifier(name=cold_fluid),
        mass_flow_kg_s=inp_data["cold_mass_flow"],
        inlet_temperature_k=inp_data["cold_inlet_t"],
        inlet_pressure_pa=inp_data.get("cold_pressure", 150_000.0),
        outlet_temperature_k=inp_data.get("cold_outlet_t"),
    )

    params = SolverParams(
        temperature_tolerance=1e-4,
        energy_tolerance=1e-3,
        max_iterations=200,
    )

    inp = HeatBalanceInput(
        hot=hot,
        cold=cold,
        known_duty_w=inp_data.get("duty_w"),
        solver_params=params,
        flow_arrangement=FlowArrangement.COUNTERFLOW,
    )

    result = solve_heat_balance(inp, provider)

    # Assert specification mode
    assert result.specification_mode.value == expected["specification_mode"]

    # Assert status
    if "status" in expected:
        assert result.status.value == expected["status"]

    # Assert duty
    if "duty_w" in expected:
        assert result.duty_w == pytest.approx(expected["duty_w"], abs=10.0)

    # Assert temperatures (FluidStateModel attribute access)
    temp_tol = tols.get("temperature_k", 0.5)
    if "hot_outlet_t" in expected:
        assert result.hot_outlet_state.temperature_k == pytest.approx(
            expected["hot_outlet_t"], abs=temp_tol
        )
    if "cold_outlet_t" in expected:
        assert result.cold_outlet_state.temperature_k == pytest.approx(
            expected["cold_outlet_t"], abs=temp_tol
        )

    # Assert q_hot_w / q_cold_w
    if "q_hot_w" in expected:
        assert result.q_hot_w == pytest.approx(expected["q_hot_w"], abs=10.0)
    if "q_cold_w" in expected:
        assert result.q_cold_w == pytest.approx(expected["q_cold_w"], abs=10.0)

    # Assert residual
    if "residual_w" in expected:
        assert result.residual_w == pytest.approx(expected["residual_w"], abs=10.0)

    # Assert relative imbalance
    imb_tol = tols.get("relative_imbalance_max", 0.001)
    assert result.relative_imbalance < imb_tol

    # Assert energy_balance_accepted
    if "energy_balance_accepted" in expected:
        assert result.energy_balance_accepted == expected["energy_balance_accepted"]

    # Assert convergence
    if "solver_converged" in expected:
        assert result.solver_converged == expected["solver_converged"]

    # Assert hash (if present)
    if "result_hash" in expected:
        assert result.result_hash == expected["result_hash"]
