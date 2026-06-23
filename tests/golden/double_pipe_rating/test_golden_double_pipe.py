"""Golden case tests for double-pipe rating kernel.

Each golden case is a JSON file in ``tests/golden/double_pipe_rating/``
containing input, expected output, and tolerances.  The test replays
the rating calculation with real CoolProp and asserts the results match
within documented tolerances.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingStatus
from hexagent.exchangers.double_pipe.solver import SolverParams
from hexagent.exchangers.double_pipe.thermal import FlowArrangement
from hexagent.properties.base import FluidIdentifier
from hexagent.properties.coolprop_provider import CoolPropProvider

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


def _run_golden(golden: dict, provider: CoolPropProvider):  # noqa: ANN202
    """Build geometry, fluids, and call rate_double_pipe for a golden case."""
    geo_data = golden["geometry"]
    geometry = DoublePipeGeometry(**geo_data)

    hot_fluid = FluidIdentifier(name=golden["hot_fluid"])
    cold_fluid = FluidIdentifier(name=golden["cold_fluid"])

    flow_arrangement = FlowArrangement(golden["flow_arrangement"])

    result = rate_double_pipe(
        geometry=geometry,
        hot_fluid=hot_fluid,
        cold_fluid=cold_fluid,
        hot_mass_flow_kg_s=golden["hot_mass_flow_kg_s"],
        cold_mass_flow_kg_s=golden["cold_mass_flow_kg_s"],
        hot_inlet_temperature_k=golden["hot_inlet_temperature_k"],
        cold_inlet_temperature_k=golden["cold_inlet_temperature_k"],
        hot_inlet_pressure_pa=golden["hot_inlet_pressure_pa"],
        cold_inlet_pressure_pa=golden["cold_inlet_pressure_pa"],
        tube_in_hot=golden["tube_in_hot"],
        flow_arrangement=flow_arrangement,
        provider=provider,
        solver_params=SolverParams(),
    )
    return result


@pytest.mark.parametrize(
    "golden_file",
    [
        "case1_counterflow_water_water",
        "case2_parallelflow_water_water",
        "case3_variable_property",
    ],
)
def test_golden_case(golden_file: str, provider: CoolPropProvider) -> None:
    """Replay a golden case and assert results within tolerances."""
    golden = _load_golden_case(golden_file)
    result = _run_golden(golden, provider)
    expected = golden["expected"]
    tols = golden["tolerances"]

    # Assert status
    assert result.status == RatingStatus(expected["status"])

    # Assert convergence
    assert result.converged == expected["converged"]

    # Assert heat duty bounds
    if expected.get("heat_duty_w_min") is not None:
        assert result.heat_duty_w is not None
        assert result.heat_duty_w >= expected["heat_duty_w_min"] * (1 - tols["heat_duty_relative"])
    if expected.get("heat_duty_w_max") is not None:
        assert result.heat_duty_w is not None
        assert result.heat_duty_w <= expected["heat_duty_w_max"] * (1 + tols["heat_duty_relative"])

    # Assert outlet temperature bounds
    if expected.get("hot_outlet_temperature_k_max") is not None:
        assert result.hot_outlet_temperature_k is not None
        assert (
            result.hot_outlet_temperature_k
            <= expected["hot_outlet_temperature_k_max"] + tols["temperature_absolute_k"]
        )
    if expected.get("cold_outlet_temperature_k_min") is not None:
        assert result.cold_outlet_temperature_k is not None
        assert (
            result.cold_outlet_temperature_k
            >= expected["cold_outlet_temperature_k_min"] - tols["temperature_absolute_k"]
        )

    # Energy balance check
    if result.heat_duty_w and result.heat_duty_w > 1.0 and result.energy_residual_w is not None:
        assert abs(result.energy_residual_w) < (
            tols["energy_residual_relative"] * result.heat_duty_w
        )


def _load_golden_case(case_id: str) -> dict:
    path = _GOLDEN_DIR / f"{case_id}.json"
    with open(path) as f:
        return json.load(f)
