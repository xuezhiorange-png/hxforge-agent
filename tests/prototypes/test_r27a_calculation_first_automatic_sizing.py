"""R27A calculation-first automatic sizing from design conditions."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
    estimate_preliminary_nozzle_diameters,
    find_candidate_b_record,
    find_middle_reference_record,
    run_calculation_first_automatic_sizing,
    write_calculation_first_sizing_reports,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _is_baseline_candidate_b,
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


def test_r27a_report_schema_and_unrated_not_eliminated(r26e_case, r26e_selection) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=False,
        run_authorized_full_path_hydraulic=False,
        max_candidates=1,
        precomputed_selection=r26e_selection,
    )
    assert report["TASK_ID"] == "V07_R27A_CALCULATION_REPORT_INTEGRITY"
    assert report["schema_version"] == "hxforge.calculation-first-automatic-sizing.v27a-integrity"
    assert report["sizing_calculation_status"] == "SIZING_CALCULATION_COMPLETE"
    assert report["found_feasible_design"] in {
        "FOUND_FEASIBLE_DESIGN",
        "NO_NOMINAL_FEASIBLE_DESIGN",
    }
    assert report["user_design_input"]["target_duty_w"] == "330000"
    rated = next(
        row
        for row in report["sizing_candidates"]
        if row["rating_participation_status"] != "NOT_SELECTED_FOR_RATING"
    )
    assert rated["constraints"]["duty_constraint"] == "NOT_FORMALLY_EVALUATED"
    assert (
        "not classified as infeasible"
        in report["recommendation"]["global_optimum_disclosure"].lower()
    )
    not_rated = [
        row
        for row in report["sizing_candidates"]
        if row["rating_participation_status"] == "NOT_SELECTED_FOR_RATING"
    ]
    assert not_rated
    assert not_rated[0]["elimination_or_incomplete_reason"] is None


def test_r27a_reference_geometries_in_candidate_space(r26e_selection) -> None:
    selection = r26e_selection
    middle = find_middle_reference_record(selection)
    baseline_b = find_candidate_b_record(selection)
    assert middle is not None
    assert middle.physical_tube_count == 313
    assert middle.shell_inside_diameter_m == "0.54"
    assert baseline_b is not None
    assert _is_baseline_candidate_b(baseline_b)


def test_r27a_writes_json_and_markdown_reports(r26e_case, r26e_selection, tmp_path: Path) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=False,
        run_authorized_full_path_hydraulic=False,
        max_candidates=1,
        precomputed_selection=r26e_selection,
    )
    json_path, md_path = write_calculation_first_sizing_reports(report, tmp_path)
    assert json_path.is_file()
    assert md_path.is_file()
    md = md_path.read_text(encoding="utf-8")
    assert "330000" in md
    assert "| Duty W |" in md or "Duty W" in md
    assert "U_cf_equiv" in md


def test_r27a_preliminary_nozzle_sizing_uses_velocity_rule(r26e_case) -> None:
    nozzle = estimate_preliminary_nozzle_diameters(r26e_case)
    assert nozzle["velocity_design_rule"]["rule_id"] == NOZZLE_VELOCITY_DESIGN_RULE["rule_id"]
    tube = nozzle["sides"]["tube_side"]
    assert tube["inlet_density_kg_m3"] > 900
    assert len(tube["diameter_candidates_m"]) == 3
    assert nozzle["local_loss_coefficients"]["status"] == "NOT_SUPPLIED_AS_REAL_DESIGN"


def test_r27a_geometry_area_labels_separate_proxy_and_task171(r26e_case, r26e_selection) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=False,
        run_authorized_full_path_hydraulic=False,
        max_candidates=1,
        precomputed_selection=r26e_selection,
    )
    rated = next(
        row
        for row in report["sizing_candidates"]
        if row["rating_participation_status"] != "NOT_SELECTED_FOR_RATING"
    )
    geom = rated["geometry"]
    assert geom["nominal_tube_outer_area_proxy_m2"] is not None
    assert geom["task171_rated_outside_area_status"] == "NOT_AVAILABLE_UNTIL_FULL_RATING"
    assert geom["tube_pass_count"]["authority"] == "CASE_MANUFACTURING_SEARCH_CONSTRAINT"


@pytest.mark.slow
def test_r27a_r26e_end_to_end_sizing_regression_slow(
    r26e_case, r26e_selection, tmp_path: Path
) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=True,
        run_authorized_full_path_hydraulic=True,
        precomputed_selection=r26e_selection,
    )
    assert report["sizing_calculation_status"] == "SIZING_CALCULATION_COMPLETE"
    assert report["found_feasible_design"] == "FOUND_FEASIBLE_DESIGN"
    assert report["workflow_status"] == "SIZING_CALCULATION_COMPLETE"
    assert report["multi_candidate_engineering_run"]["FULLY_RATED_CANDIDATE_COUNT"] >= 3
    target = float(r26e_case.target_duty_w)
    by_id = {row["candidate_id"]: row for row in report["sizing_candidates"]}
    baseline = find_candidate_b_record(r26e_selection)
    middle = find_middle_reference_record(r26e_selection)
    assert baseline and middle
    base_row = by_id[baseline.candidate_id]
    mid_row = by_id[middle.candidate_id]
    assert base_row["thermal_rating"]["full_rating_converged"] is True
    assert mid_row["geometry"]["physical_tube_count"] == 313
    assert float(base_row["thermal_rating"]["duty_w"]) >= target
    assert float(mid_row["thermal_rating"]["duty_w"]) >= target
    assert base_row["constraints"]["duty_constraint"] == "SATISFIED"
    assert base_row["constraints"]["duty_constraint_basis"] == "FULL_MESH_RATING"
    assert mid_row["constraints"]["duty_constraint"] == "SATISFIED"
    assert base_row["geometry"]["task171_rated_outside_area_m2"] is not None
    assert base_row["constraints"]["tube_dp_constraint"] in {
        "SATISFIED",
        "NOT_SATISFIED",
        "BLOCKED",
    }
    auth_b = base_row["hydraulic_performance"]["authorized_full_path_hydraulic"]
    auth_m = mid_row["hydraulic_performance"]["authorized_full_path_hydraulic"]
    assert auth_b is not None and auth_b.get("status") == "COMPUTED"
    assert auth_m is not None and auth_m.get("status") == "COMPUTED"
    rec_id = report["recommendation"]["recommended_candidate_id"]
    assert rec_id is not None
    ranked = report["recommendation"]["ranked_feasible_candidate_ids"]
    assert rec_id in ranked
    assert rec_id in report["recommendation"]["formal_constraint_ranking_candidate_ids"]
    areas = [
        Decimal(str(by_id[cid]["geometry"]["nominal_tube_outer_area_proxy_m2"])) for cid in ranked
    ]
    assert areas == sorted(areas)
    _, md_path = write_calculation_first_sizing_reports(report, tmp_path)
    md = md_path.read_text(encoding="utf-8")
    assert str(int(target)) in md
    assert "counterflow equivalent" in md.lower() or "U_cf_equiv" in md
