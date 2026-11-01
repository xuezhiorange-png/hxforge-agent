"""R27B full-path constraint-aware calculation-first sizing."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    find_candidate_b_record,
    find_middle_reference_record,
    run_calculation_first_automatic_sizing,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    build_r26g_demonstration_hydraulic_path_input_v1,
    build_r27b_assumption_based_hydraulic_path_input_v1,
)
from prototypes.v07_general_rating_sizing_mvp.full_path_constraint_aware_sizing import (
    find_short_reference_record,
    run_full_path_constraint_aware_sizing,
    write_full_path_constraint_aware_sizing_reports,
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


def test_r27b_path_input_uses_preliminary_nozzle_not_demo_fixed_diameter(
    r26e_case, r26e_selection
) -> None:
    from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
        estimate_preliminary_nozzle_diameters,
    )

    baseline = find_candidate_b_record(r26e_selection)
    assert baseline is not None
    prelim = estimate_preliminary_nozzle_diameters(r26e_case)
    path = build_r27b_assumption_based_hydraulic_path_input_v1(
        case=r26e_case,
        record=baseline,
        preliminary_nozzle_sizing=prelim,
    )
    demo = build_r26g_demonstration_hydraulic_path_input_v1(case=r26e_case, record=baseline)
    tube_in = path.tube_side_components[0]
    assert tube_in.engineering_input_status == "ASSUMPTION_BASED"
    assert tube_in.nozzle_inside_diameter_m is not None
    assert tube_in.nozzle_inside_diameter_m != Decimal("0.100")
    demo_in = demo.tube_side_components[0]
    assert demo_in.nozzle_inside_diameter_m == Decimal("0.100")
    bundle = next(c for c in path.tube_side_components if c.component_type == "ENTRANCE")
    assert bundle.reference_flow_area_m2 == Decimal(
        str(baseline.task025_total_parallel_flow_area_m2)
    )


@pytest.mark.slow
def test_r27b_330kw_reference_candidates_regression_slow(
    r26e_case, r26e_selection, tmp_path: Path
) -> None:
    report = run_full_path_constraint_aware_sizing(
        r26e_case,
        precomputed_selection=r26e_selection,
    )
    assert report["TASK_ID"] == "V07_R27B_FULL_PATH_CONSTRAINT_AWARE_SIZING"
    assert report["schema_version"] == "hxforge.full-path-constraint-aware-sizing.v27b"
    assert report["assumption_loss_coefficient_policy"]["input_authority"] == "ASSUMPTION_BASED"
    assert report["found_feasible_design"] in {
        "FOUND_FULL_PATH_FEASIBLE_DESIGN",
        "NO_FULL_PATH_FEASIBLE_CANDIDATE",
    }

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
        assert row["thermal_rating"]["full_rating_converged"] is True
        duty = float(row["thermal_rating"]["duty_w"])
        duty_a = float(a_row["thermal_rating"]["duty_w"])
        assert duty == pytest.approx(duty_a, rel=0, abs=0.01)
        assert (
            row["hydraulic_performance"]["live_tube_dp_pa"]
            == a_row["hydraulic_performance"]["live_tube_dp_pa"]
        )
        assert (
            row["hydraulic_performance"]["live_shell_dp_pa"]
            == a_row["hydraulic_performance"]["live_shell_dp_pa"]
        )
        fp = row["hydraulic_performance"]["full_path_hydraulic"]
        demo_fp = a_row["hydraulic_performance"]["authorized_full_path_hydraulic"]
        assert fp is not None and demo_fp is not None
        assert fp.get("TUBE_FULL_PATH_TOTAL_DP_PA") != demo_fp.get("TUBE_FULL_PATH_TOTAL_DP_PA")
        nozzle = row["hydraulic_performance"]["nozzle_geometry_used_in_full_path"]["sides"][
            "tube_side"
        ]["inside_diameter_m"]
        assert nozzle != 0.1

    base_row = by_id[baseline.candidate_id]
    assert float(base_row["thermal_rating"]["duty_w"]) >= target
    assert base_row["constraints"]["duty_constraint"] == "SATISFIED"

    assert report["recommendation"]["ranking_disclosure"]
    if report["found_feasible_design"] == "NO_FULL_PATH_FEASIBLE_CANDIDATE":
        assert report["recommendation"]["recommended_candidate_id"] is None
        assert report["recommendation"]["infeasible_full_path_details"]
    else:
        assert report["recommendation"]["recommended_candidate_id"] is not None
        rec = by_id[report["recommendation"]["recommended_candidate_id"]]
        assert rec["full_path_constraint_ranking"]["feasible"] is True

    json_path, md_path = write_full_path_constraint_aware_sizing_reports(report, tmp_path)
    assert json_path.is_file()
    assert md_path.is_file()
    assert "330000" in md_path.read_text(encoding="utf-8")
