"""R26/R26A: experimental engineering counterflow rating core."""

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
    constant_u_counterflow_fv_duty_w,
    epsilon_ntu_counterflow_duty_w,
    run_experimental_engineering_rating,
)

_R23 = Path(__file__).resolve().parents[1] / "fixtures/r23_variable_water_temperature_n1_case.json"
_R22 = Path(__file__).resolve().parents[1] / "fixtures/r22_two_way_bulk_pressure_n1_case.json"


def test_epsilon_ntu_matches_constant_u_fv_counterflow() -> None:
    c_hot = 12_000.0
    c_cold = 18_000.0
    ua = 80_000.0
    th_in = 320.0
    tc_in = 280.0
    duty_ntu = epsilon_ntu_counterflow_duty_w(
        hot_capacity_w_per_k=c_hot,
        cold_capacity_w_per_k=c_cold,
        u_a_w_per_k=ua,
        hot_inlet_k=th_in,
        cold_inlet_k=tc_in,
    )
    duty_fv = constant_u_counterflow_fv_duty_w(
        n_cells=32,
        hot_capacity_w_per_k=c_hot,
        cold_capacity_w_per_k=c_cold,
        u_a_total_w_per_k=ua,
        hot_inlet_k=th_in,
        cold_inlet_k=tc_in,
        duty_seed_w=duty_ntu,
    )
    rel = abs(duty_ntu - duty_fv) / duty_ntu
    assert rel < 0.02
    duty_fv_n16 = constant_u_counterflow_fv_duty_w(
        n_cells=64,
        hot_capacity_w_per_k=c_hot,
        cold_capacity_w_per_k=c_cold,
        u_a_total_w_per_k=ua,
        hot_inlet_k=th_in,
        cold_inlet_k=tc_in,
        duty_seed_w=duty_ntu,
    )
    assert abs(duty_fv_n16 - duty_fv) / duty_ntu < 0.01


def test_frozen_298_15_case_engineering_n1_runs() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    assert result.status == ENGINEERING_NUMERIC_VALID
    assert result.mesh_metadata is not None
    assert result.mesh_metadata.all_physical_supports_covered
    assert result.mesh_metadata.total_area_conservation
    assert result.duty_w is not None and result.duty_w > 0.0
    assert result.energy_balance_relative_error is not None
    assert result.energy_balance_relative_error < 1e-8
    assert result.tube_outlet_temperature_k is not None
    assert result.tube_outlet_temperature_k < float(t173.TUBE_INLET_T_K)


def test_r26a_full_topology_coverage_r23_n1() -> None:
    case = load_general_engineering_case_json(_R23.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    assert result.mesh_metadata is not None
    meta = result.mesh_metadata
    assert meta.physical_interval_count == 5
    assert meta.cell_count == 5
    assert meta.total_tube_length_m == pytest.approx(3.0, rel=1e-6)
    assert meta.task171_total_inside_area_m2 == pytest.approx(
        meta.summed_cell_inside_area_m2, rel=1e-9
    )
    assert meta.task171_total_outside_area_m2 == pytest.approx(
        meta.summed_cell_outside_area_m2, rel=1e-9
    )
    assert len({c.physical_segment_id for c in result.cells}) == 5


@pytest.mark.slow
def test_primary_310_295_k_engineering_full_device_n1() -> None:
    case = load_general_engineering_case_json(_R23.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    assert result.status == ENGINEERING_NUMERIC_VALID
    assert result.duty_w is not None and result.duty_w > 0.0
    assert result.tube_outlet_temperature_k is not None
    assert result.shell_outlet_temperature_k is not None
    assert result.tube_outlet_temperature_k < result.tube_inlet_temperature_k
    assert result.shell_outlet_temperature_k > result.shell_inlet_temperature_k
    assert result.energy_balance_relative_error is not None
    assert result.energy_balance_relative_error < 1e-5
    assert result.max_cell_thermal_residual_w is not None
    assert result.max_cell_thermal_residual_w < 1.0
    assert result.max_inner_wall_outer_closure_residual_w is not None
    for cell in result.cells:
        assert cell.closure.scalar_root_residual_w < 1e-3
        assert cell.thermal_residual_w < 1.0


def test_engineering_result_is_structured_json_serializable() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    result = run_experimental_engineering_rating(case, subdivisions=1)
    payload = {
        "status": result.status,
        "duty_w": result.duty_w,
        "mesh": result.mesh_subdivisions,
        "energy_balance_relative_error": result.energy_balance_relative_error,
        "coolprop_tp": result.coolprop_stats.tp_calls,
        "coolprop_ph": result.coolprop_stats.ph_calls,
        "wall_seconds": result.wall_seconds,
    }
    json.dumps(payload)
