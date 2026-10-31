"""R27A calculation-first automatic sizing from design conditions."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    find_candidate_b_record,
    find_middle_reference_record,
    run_calculation_first_automatic_sizing,
    write_calculation_first_sizing_reports,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _is_baseline_candidate_b,
)

_FIXTURE_R26E = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26e_multi_candidate_engineering_sizing_case.json"
)


@pytest.fixture(name="r26e_case")
def _r26e_case():
    return load_general_engineering_case_json(_FIXTURE_R26E.read_text(encoding="utf-8"))


def test_r27a_report_schema_and_unrated_not_eliminated(r26e_case) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=False,
        run_authorized_full_path_hydraulic=False,
        max_candidates=1,
    )
    assert report["TASK_ID"] == "V07_R27A_CALCULATION_FIRST_AUTOMATIC_SIZING"
    assert report["schema_version"] == "hxforge.calculation-first-automatic-sizing.v27a"
    assert report["user_design_input"]["target_duty_w"] == "330000"
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


def test_r27a_reference_geometries_in_candidate_space(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    middle = find_middle_reference_record(selection)
    baseline_b = find_candidate_b_record(selection)
    assert middle is not None
    assert middle.physical_tube_count == 313
    assert middle.shell_inside_diameter_m == "0.54"
    assert baseline_b is not None
    assert _is_baseline_candidate_b(baseline_b)


def test_r27a_writes_json_and_markdown_reports(r26e_case, tmp_path: Path) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=False,
        run_authorized_full_path_hydraulic=False,
        max_candidates=1,
    )
    json_path, md_path = write_calculation_first_sizing_reports(report, tmp_path)
    assert json_path.is_file()
    assert md_path.is_file()
    assert "330000" in md_path.read_text(encoding="utf-8")


@pytest.mark.slow
def test_r27a_r26e_end_to_end_sizing_regression_slow(r26e_case) -> None:
    report = run_calculation_first_automatic_sizing(
        r26e_case,
        run_full_mesh_hydraulic=True,
        run_authorized_full_path_hydraulic=True,
    )
    assert report["workflow_status"] == "SIZING_CALCULATION_COMPLETE"
    assert report["multi_candidate_engineering_run"]["FULLY_RATED_CANDIDATE_COUNT"] >= 3
    target = float(r26e_case.target_duty_w)
    by_id = {row["candidate_id"]: row for row in report["sizing_candidates"]}
    selection = enumerate_experimental_rating_candidates(r26e_case)
    baseline = find_candidate_b_record(selection)
    middle = find_middle_reference_record(selection)
    assert baseline and middle
    base_row = by_id[baseline.candidate_id]
    mid_row = by_id[middle.candidate_id]
    assert base_row["thermal_rating"]["full_rating_converged"] is True
    assert mid_row["geometry"]["physical_tube_count"] == 313
    assert float(base_row["thermal_rating"]["duty_w"]) >= target
    assert float(mid_row["thermal_rating"]["duty_w"]) >= target
    assert base_row["constraints"]["duty_constraint"] == "SATISFIED"
    assert mid_row["constraints"]["duty_constraint"] == "SATISFIED"
    auth_b = base_row["hydraulic_performance"]["authorized_full_path_hydraulic"]
    auth_m = mid_row["hydraulic_performance"]["authorized_full_path_hydraulic"]
    assert auth_b is not None and auth_b.get("status") == "COMPUTED"
    assert auth_m is not None and auth_m.get("status") == "COMPUTED"
    rec_id = report["recommendation"]["recommended_candidate_id"]
    assert rec_id is not None
    ranked = report["recommendation"]["ranked_feasible_candidate_ids"]
    assert rec_id in ranked
    areas = [Decimal(str(by_id[cid]["geometry"]["nominal_tube_outer_area_m2"])) for cid in ranked]
    assert areas == sorted(areas)
