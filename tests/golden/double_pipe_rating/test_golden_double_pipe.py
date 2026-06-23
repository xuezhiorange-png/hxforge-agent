"""Golden case tests for double-pipe rating kernel.

Each golden case is a JSON file in ``tests/golden/double_pipe_rating/``
containing input, expected output, and tolerances.  The test replays
the rating calculation with real CoolProp and asserts the results match
within documented tolerances.

Golden cases:
1. Counter-flow water-water
2. Parallel-flow water-water
3. Variable-property counter-flow
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexagent.exchangers.double_pipe.geometry import DoublePipeGeometry
from hexagent.exchangers.double_pipe.rating import rate_double_pipe
from hexagent.exchangers.double_pipe.result import RatingResult, RatingStatus
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


def _run_golden(golden: dict, provider: CoolPropProvider) -> RatingResult:
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

    # Assert heat duty
    if expected.get("heat_duty_w") is not None:
        assert result.heat_duty_w is not None
        assert result.heat_duty_w == pytest.approx(
            expected["heat_duty_w"], rel=tols["heat_duty_relative"]
        )

    # Assert hot outlet temperature
    if expected.get("hot_outlet_temperature_k") is not None:
        assert result.hot_outlet_temperature_k is not None
        assert result.hot_outlet_temperature_k == pytest.approx(
            expected["hot_outlet_temperature_k"],
            rel=tols["temperature_relative"],
        )

    # Assert cold outlet temperature
    if expected.get("cold_outlet_temperature_k") is not None:
        assert result.cold_outlet_temperature_k is not None
        assert result.cold_outlet_temperature_k == pytest.approx(
            expected["cold_outlet_temperature_k"],
            rel=tols["temperature_relative"],
        )

    # Assert UA
    if expected.get("UA_w_k") is not None:
        assert result.UA_w_k is not None
        assert result.UA_w_k == pytest.approx(expected["UA_w_k"], rel=tols["UA_relative"])

    # Assert LMTD
    if expected.get("LMTD_k") is not None:
        assert result.LMTD_k is not None
        assert result.LMTD_k == pytest.approx(expected["LMTD_k"], rel=tols["LMTD_relative"])

    # Energy balance check
    if result.heat_duty_w and result.heat_duty_w > 1.0 and result.energy_residual_w is not None:
        assert abs(result.energy_residual_w) < (
            tols["energy_residual_relative"] * result.heat_duty_w
        )

    # Verify hash format
    assert result.result_hash.startswith("sha256:")
    hex_part = result.result_hash[7:]
    assert len(hex_part) == 64

    # Verify provenance graph structure
    graph = result.provenance_graph
    assert len(graph.nodes) > 0
    assert len(graph.edges) > 0


def _load_golden_case(case_id: str) -> dict:
    path = _GOLDEN_DIR / f"{case_id}.json"
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Additional golden tests
# ---------------------------------------------------------------------------


class TestGoldenCounterflowDetailed:
    """Detailed assertions for the counter-flow golden case."""

    def test_counterflow_duty_reasonable(self, provider: CoolPropProvider) -> None:
        golden = _load_golden_case("case1_counterflow_water_water")
        result = _run_golden(golden, provider)
        # Duty should be between 10kW and 20kW for these conditions
        assert result.heat_duty_w is not None
        assert 10_000 < result.heat_duty_w < 20_000

    def test_counterflow_outlet_temps_reasonable(self, provider: CoolPropProvider) -> None:
        golden = _load_golden_case("case1_counterflow_water_water")
        result = _run_golden(golden, provider)
        # Hot outlet between 300 and 350 K
        assert result.hot_outlet_temperature_k is not None
        assert 300.0 < result.hot_outlet_temperature_k < 350.0
        # Cold outlet between 300 and 350 K
        assert result.cold_outlet_temperature_k is not None
        assert 300.0 < result.cold_outlet_temperature_k < 350.0


class TestGoldenParallelflowDetailed:
    """Detailed assertions for the parallel-flow golden case."""

    def test_parallel_duty_less_than_counterflow(self, provider: CoolPropProvider) -> None:
        cf_golden = _load_golden_case("case1_counterflow_water_water")
        pf_golden = _load_golden_case("case2_parallelflow_water_water")
        cf_result = _run_golden(cf_golden, provider)
        pf_result = _run_golden(pf_golden, provider)
        assert cf_result.heat_duty_w is not None
        assert pf_result.heat_duty_w is not None
        # Counter-flow duty should be >= parallel duty
        assert cf_result.heat_duty_w >= pf_result.heat_duty_w * 0.99

    def test_parallel_succeeds(self, provider: CoolPropProvider) -> None:
        golden = _load_golden_case("case2_parallelflow_water_water")
        result = _run_golden(golden, provider)
        assert result.status == RatingStatus.SUCCEEDED
        assert result.converged is True
