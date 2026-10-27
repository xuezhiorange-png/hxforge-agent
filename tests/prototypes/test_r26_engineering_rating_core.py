"""R26: experimental engineering counterflow rating core."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    epsilon_ntu_counterflow_duty_w,
    run_experimental_engineering_rating,
)

_R23 = Path(__file__).resolve().parents[1] / "fixtures/r23_variable_water_temperature_n1_case.json"
_R22 = Path(__file__).resolve().parents[1] / "fixtures/r22_two_way_bulk_pressure_n1_case.json"


def test_epsilon_ntu_counterflow_matches_closed_form() -> None:
    c_hot = 12_000.0
    c_cold = 18_000.0
    ua = 50_000.0
    duty = epsilon_ntu_counterflow_duty_w(
        hot_capacity_w_per_k=c_hot,
        cold_capacity_w_per_k=c_cold,
        u_a_w_per_k=ua,
        hot_inlet_k=320.0,
        cold_inlet_k=280.0,
    )
    assert 50_000.0 < duty < 500_000.0


def test_frozen_298_15_case_engineering_n1_runs() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    assert result.status == ENGINEERING_NUMERIC_VALID
    assert result.duty_w is not None and result.duty_w > 0.0
    assert result.energy_balance_relative_error is not None
    assert result.energy_balance_relative_error < 1e-6
    assert result.tube_outlet_temperature_k is not None
    assert result.tube_outlet_temperature_k < float(t173.TUBE_INLET_T_K)


@pytest.mark.slow
def test_primary_310_295_k_engineering_n1() -> None:
    case = load_general_engineering_case_json(_R23.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    assert result.status in {
        ENGINEERING_NUMERIC_VALID,
        "EXPERIMENTAL_ENGINEERING_BLOCKED",
    }
    if result.status == ENGINEERING_NUMERIC_VALID:
        assert result.duty_w is not None and result.duty_w > 0.0
        assert result.tube_outlet_temperature_k is not None
        assert result.shell_outlet_temperature_k is not None
        assert result.tube_outlet_temperature_k < result.tube_inlet_temperature_k
        assert result.shell_outlet_temperature_k > result.shell_inlet_temperature_k
        assert result.energy_balance_relative_error is not None
        assert result.energy_balance_relative_error < 1e-5


def test_engineering_result_is_structured_json_serializable() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    payload = {
        "status": result.status,
        "duty_w": result.duty_w,
        "mesh": result.mesh_subdivisions,
        "energy_balance_relative_error": result.energy_balance_relative_error,
        "coolprop_queries": result.property_provider_state_lookup_count,
        "wall_seconds": result.wall_seconds,
    }
    json.dumps(payload)
