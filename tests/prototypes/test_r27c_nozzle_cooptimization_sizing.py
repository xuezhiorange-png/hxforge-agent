"""R27C nozzle pressure-budget co-optimization."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    find_candidate_b_record,
    find_middle_reference_record,
    run_calculation_first_automatic_sizing,
)
from prototypes.v07_general_rating_sizing_mvp.full_path_constraint_aware_sizing import (
    find_short_reference_record,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    _SCHEMA,
    _TASK_ID,
    LOSS_SCENARIO_KEYS,
    run_nozzle_pressure_budget_cooptimization,
    write_nozzle_cooptimization_reports,
)
from tests.prototypes.r26g_r26ga_shared_setup import (
    shared_r26e_engineering_case,
    shared_r26e_experimental_rating_selection,
)


@pytest.fixture(name="r26e_case")
def _r26e_case():
    return shared_r26e_engineering_case()


@pytest.fixture(name="r26e_selection")
def _r26e_selection():
    return shared_r26e_experimental_rating_selection()


def test_r27c_schema_constants() -> None:

    assert _TASK_ID == "V07_R27C_NOZZLE_PRESSURE_BUDGET_CO_OPTIMIZATION"
    assert _SCHEMA == "hxforge.nozzle-pressure-budget-cooptimization.v27c"
    assert len(LOSS_SCENARIO_KEYS) == 3


@pytest.mark.slow
def test_r27c_330kw_regression_and_candidate_b_not_false_feasible(
    r26e_case, r26e_selection, tmp_path: Path
) -> None:
    report = run_nozzle_pressure_budget_cooptimization(
        r26e_case,
        precomputed_selection=r26e_selection,
    )
    r27a = run_calculation_first_automatic_sizing(
        r26e_case,
        precomputed_selection=r26e_selection,
    )
    by_id = {row["candidate_id"]: row for row in report["sizing_candidates"]}
    r27a_by_id = {row["candidate_id"]: row for row in r27a["sizing_candidates"]}
    baseline = find_candidate_b_record(r26e_selection)
    middle = find_middle_reference_record(r26e_selection)
    short = find_short_reference_record(r26e_selection)
    assert baseline and middle and short
    target = float(r26e_case.target_duty_w)

    for ref in (baseline, middle, short):
        row = by_id[ref.candidate_id]
        a_row = r27a_by_id[ref.candidate_id]
        duty = float(row["thermal_rating"]["duty_w"])
        assert duty == pytest.approx(float(a_row["thermal_rating"]["duty_w"]), abs=0.01)
        hyd = row["hydraulic_performance"]
        ah = a_row["hydraulic_performance"]
        assert hyd["live_tube_dp_pa"] == ah["live_tube_dp_pa"]
        assert hyd["live_shell_dp_pa"] == ah["live_shell_dp_pa"]

    base = by_id[baseline.candidate_id]
    assert float(base["thermal_rating"]["duty_w"]) >= target
    for scenario_key in ("mid_band", "low_loss_sensitivity", "high_loss_sensitivity"):
        sc = base["loss_scenario_results"][scenario_key]
        assert sc["full_path_feasible"] is False
        assert sc["overall_scenario_status"] != "FEASIBLE_FULL_PATH_VERIFIED"
        shell_solve = sc["shell_nozzle_solve"]
        assert shell_solve["status"] == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS"
        tube_solve = sc["tube_nozzle_solve"]
        if tube_solve.get("status") == "FEASIBLE_WITHIN_DESIGN_BOUNDS":
            assert float(tube_solve["modeled_side_total_dp_pa"]) <= 1150.0
            assert float(tube_solve["selected_velocity_m_s"]) < 3.0 - 1e-6

    assert report["found_feasible_design"] == "NO_FULL_PATH_FEASIBLE_CANDIDATE"
    assert report["recommendation"]["recommended_candidate_id"] is None

    mid_row = by_id[middle.candidate_id]
    mid_mid = mid_row["loss_scenario_results"]["mid_band"]
    tube_solve = mid_mid["tube_nozzle_solve"]
    if tube_solve.get("status") == "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        v = float(tube_solve["selected_velocity_m_s"])
        assert 1.0 <= v <= 3.0 + 1e-6

    write_nozzle_cooptimization_reports(report, tmp_path)
