"""R26C: warm start, mesh gates, and live hydraulic bridge (fast paths)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import numpy as np
import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    EngineeringAcceptanceLimits,
    EngineeringCellResult,
    EngineeringRatingResult,
    build_warm_start_q_from_parent_cells,
    compute_mesh_convergence_flags,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)

_R22 = Path(__file__).resolve().parents[1] / "fixtures/r22_two_way_bulk_pressure_n1_case.json"
_R23 = Path(__file__).resolve().parents[1] / "fixtures/r23_variable_water_temperature_n1_case.json"


def _binding(
    global_index: int,
    interval_index: int,
    subdivision_index: int,
    area: float,
) -> SimpleNamespace:
    return SimpleNamespace(
        global_index=global_index,
        interval_index=interval_index,
        subdivision_index=subdivision_index,
        support=SimpleNamespace(inside_area_m2=area),
    )


def _parent_cell(interval_index: int, subdivision_index: int, q_w: float) -> EngineeringCellResult:
    return EngineeringCellResult(
        global_index=0,
        interval_index=interval_index,
        subdivision_index=subdivision_index,
        physical_segment_id="seg",
        axial_start_m=0.0,
        axial_end_m=1.0,
        heat_rate_w=q_w,
        tube_inlet_enthalpy_j_kg=0.0,
        tube_outlet_enthalpy_j_kg=0.0,
        shell_inlet_enthalpy_j_kg=0.0,
        shell_outlet_enthalpy_j_kg=0.0,
        tube_bulk_temperature_k=300.0,
        shell_bulk_temperature_k=295.0,
        thermal_residual_w=0.0,
        inner_residual_w=0.0,
        wall_residual_w=0.0,
        outer_residual_w=0.0,
        enthalpy_residual_w=0.0,
        closure=mock.Mock(),
    )


def test_warm_start_maps_parent_subdivision_without_interval_collision() -> None:
    parent_cells = [
        _parent_cell(0, 0, 100.0),
        _parent_cell(0, 1, 200.0),
        _parent_cell(1, 0, 300.0),
        _parent_cell(1, 1, 400.0),
    ]
    grid = [
        _binding(0, 0, 0, 1.0),
        _binding(1, 0, 1, 1.0),
        _binding(2, 0, 2, 1.0),
        _binding(3, 0, 3, 1.0),
        _binding(4, 1, 0, 2.0),
        _binding(5, 1, 1, 2.0),
        _binding(6, 1, 2, 2.0),
        _binding(7, 1, 3, 2.0),
    ]
    q = build_warm_start_q_from_parent_cells(
        grid,
        parent_cells,
        child_subdivisions=4,
        parent_subdivisions=2,
    )
    assert np.isclose(q[0] + q[1], 100.0)
    assert np.isclose(q[2] + q[3], 200.0)
    assert np.isclose(q[4] + q[5], 300.0)
    assert np.isclose(q[6] + q[7], 400.0)
    assert np.isclose(q.sum(), sum(c.heat_rate_w for c in parent_cells))


def test_mesh_cache_skips_duplicate_parent_global_solve(monkeypatch: pytest.MonkeyPatch) -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    solve_calls: list[int] = []
    import prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core as core

    original = core._solve_global_q_vector

    def counting_solve(*args: object, **kwargs: object) -> tuple[list[object], int]:
        grid = args[2]
        solve_calls.append(len(grid))
        return original(*args, **kwargs)

    monkeypatch.setattr(core, "_solve_global_q_vector", counting_solve)
    cache: dict[int, object] = {}
    run_experimental_engineering_rating(case, subdivisions=1, mesh_result_cache=cache)
    run_experimental_engineering_rating(case, subdivisions=2, mesh_result_cache=cache)
    n1_cells = solve_calls[0]
    assert n1_cells in solve_calls
    assert any(c > n1_cells for c in solve_calls)
    assert solve_calls.count(n1_cells) == 1


def _synthetic_valid_result(
    *,
    subdivisions: int,
    duty_w: float,
    tube_out_k: float,
    shell_out_k: float,
) -> EngineeringRatingResult:
    cell = _parent_cell(0, 0, duty_w / subdivisions)
    cell.thermal_residual_w = 0.0
    cell.inner_residual_w = 0.0
    cell.wall_residual_w = 0.0
    cell.outer_residual_w = 0.0
    return EngineeringRatingResult(
        schema_version="test",
        status=ENGINEERING_NUMERIC_VALID,
        failure_code=None,
        diagnostics=[],
        mesh_subdivisions=subdivisions,
        candidate_id="cand",
        mesh_metadata=None,
        duty_w=duty_w,
        tube_inlet_temperature_k=310.0,
        shell_inlet_temperature_k=295.0,
        tube_outlet_temperature_k=tube_out_k,
        shell_outlet_temperature_k=shell_out_k,
        tube_inlet_enthalpy_j_kg=1.0,
        shell_inlet_enthalpy_j_kg=1.0,
        tube_outlet_enthalpy_j_kg=1.0,
        shell_outlet_enthalpy_j_kg=1.0,
        hot_side_enthalpy_duty_w=duty_w,
        cold_side_enthalpy_duty_w=duty_w,
        energy_balance_relative_error=1e-12,
        max_cell_thermal_residual_w=0.0,
        max_inner_wall_outer_closure_residual_w=0.0,
        cells=[cell] * subdivisions,
        picard_iterations=1,
        coolprop_stats=mock.Mock(total_calls=0, tp_calls=0, ph_calls=0),
        wall_seconds=0.1,
    )


def test_outlet_temperature_mesh_gate_uses_defined_tolerance() -> None:
    results = {
        1: _synthetic_valid_result(
            subdivisions=1, duty_w=1000.0, tube_out_k=300.0, shell_out_k=296.0
        ),
        2: _synthetic_valid_result(
            subdivisions=2, duty_w=999.5, tube_out_k=300.02, shell_out_k=296.01
        ),
        4: _synthetic_valid_result(
            subdivisions=4, duty_w=999.4, tube_out_k=300.03, shell_out_k=296.02
        ),
    }
    flags = compute_mesh_convergence_flags(results, limits=EngineeringAcceptanceLimits())
    assert flags["OUTLET_TEMPERATURE_MESH_STABLE"] is True
    assert flags["DUTY_MESH_STABLE"] is True
    assert flags["LOCAL_CLOSURE_VALID"] is True
    assert flags["FULL_RATING_CONVERGED"] is True
    results[4] = _synthetic_valid_result(
        subdivisions=4, duty_w=900.0, tube_out_k=301.0, shell_out_k=296.02
    )
    flags_fail = compute_mesh_convergence_flags(results, limits=EngineeringAcceptanceLimits())
    assert flags_fail["FULL_RATING_CONVERGED"] is False


def test_live_hydraulic_bridge_r22_n1() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    package = build_experimental_engineering_rating_live_package(
        case,
        run_mesh_ladder=False,
        single_mesh_subdivisions=1,
    )
    receipt = package["hydraulic_receipt"]
    assert receipt["LIVE_HYDRAULIC_IMPLEMENTED"] is True
    assert receipt["LIVE_TUBE_DP_PA"] is not None
    assert receipt["LIVE_SHELL_DP_PA"] is not None
    assert package["ENGINEERING_SIZING_ELIGIBILITY"] == (
        "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )
    assert package["GEOMETRY_COMPLETENESS_STATUS"] == "ENTRANCE_ONLY_ASSUMED"
    tube_dp = Decimal(str(receipt["LIVE_TUBE_DP_PA"]))
    shell_dp = Decimal(str(receipt["LIVE_SHELL_DP_PA"]))
    assert (
        tube_dp <= case.max_tube_side_pressure_drop_pa
        or receipt["TUBE_HYDRAULIC_STATUS"] == "NOT_SATISFIED"
    )
    assert (
        shell_dp <= case.max_shell_side_pressure_drop_pa
        or receipt["SHELL_HYDRAULIC_STATUS"] == "NOT_SATISFIED"
    )


@pytest.mark.slow
def test_r26c_primary_310_295_mesh_ladder_and_live_hydraulic() -> None:
    case = load_general_engineering_case_json(_R23.read_text(encoding="utf-8"))
    package = build_experimental_engineering_rating_live_package(case, run_mesh_ladder=True)
    mesh = package["mesh_convergence"]
    assert mesh["results"][1].status == ENGINEERING_NUMERIC_VALID
    assert mesh["results"][2].status == ENGINEERING_NUMERIC_VALID
    assert mesh["results"][4].status == ENGINEERING_NUMERIC_VALID
    receipt = package["hydraulic_receipt"]
    assert receipt["LIVE_HYDRAULIC_IMPLEMENTED"] is True
    assert package["GEOMETRY_COMPLETENESS_STATUS"] == "ENTRANCE_ONLY_ASSUMED"
