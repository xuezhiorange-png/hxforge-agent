"""R27D thermal–hydraulic–geometry co-optimization."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.thermal_hydraulic_geometry_cooptimization_sizing import (
    _SCHEMA,
    _TASK_ID,
    classify_r27d_search_phases,
    run_thermal_hydraulic_geometry_cooptimization,
    write_r27d_reports,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def test_r27d_schema_constants() -> None:
    assert _TASK_ID == "V07_R27D_THERMAL_HYDRAULIC_GEOMETRY_CO_OPTIMIZATION"
    assert _SCHEMA == "hxforge.thermal-hydraulic-geometry-cooptimization.v27d"


def test_r27d_selection_rate_all_task174_ready_distinct_geometries() -> None:
    case = shared_r26e_engineering_case()
    outcome = enumerate_experimental_rating_candidates(
        case,
        rating_selection_policy="r27d",
        rate_all_distinct_task174_ready=True,
    )
    distinct_ready = len(
        {r.geometry_projection_hash for r in outcome.records if r.rating_request_ready}
    )
    assert outcome.candidate_space_count == 48
    assert outcome.task174_ready_count == 12
    assert distinct_ready == 12
    assert len(outcome.selected_candidate_ids) == 12


def test_r27d_search_incomplete_when_budget_capped() -> None:
    case = shared_r26e_engineering_case()
    report = run_thermal_hydraulic_geometry_cooptimization(
        case,
        rate_all_distinct_task174_ready=False,
        max_candidates_to_rate_override=4,
        run_full_mesh_hydraulic=False,
    )
    cov = report["search_coverage"]
    assert cov["search_status"] == "SEARCH_INCOMPLETE"
    assert cov["selected_for_full_mesh_rating_count"] == 4
    assert cov["distinct_task174_ready_geometry_count"] == 12
    assert cov["search_phases"]["ready_geometry_selection"] == "PARTIAL_READY_GEOMETRY_SELECTION"


def test_r27d_search_phase_labels_full_mesh_incomplete_twelve_seven() -> None:
    phases = classify_r27d_search_phases(
        candidate_space_count=48,
        task174_ready_count=12,
        distinct_task174_ready_geometry_count=12,
        selected_for_full_mesh_rating_count=12,
        full_mesh_rating_completed_count=7,
        full_path_feasible_mid_band_among_fully_rated=0,
        solver_budget_prevented_selecting_all_ready=False,
    )
    assert phases["enumeration"] == "ENUMERATION_COMPLETE"
    assert phases["ready_geometry_selection"] == "ALL_READY_GEOMETRIES_SELECTED"
    assert phases["full_mesh_rating"] == "FULL_MESH_RATING_INCOMPLETE"
    assert (
        phases["feasibility_among_fully_rated"]
        == "NO_CONFIRMED_FEASIBLE_AMONG_EVALUATED_CANDIDATES"
    )


@pytest.mark.slow
def test_r27d_330kw_joint_search_reports_coverage_and_references(
    tmp_path: Path,
) -> None:
    case = shared_r26e_engineering_case()
    report = run_thermal_hydraulic_geometry_cooptimization(
        case,
        rate_all_distinct_task174_ready=True,
    )
    cov = report["search_coverage"]
    assert cov["search_phases"]["ready_geometry_selection"] == "ALL_READY_GEOMETRIES_SELECTED"
    assert cov["search_phases"]["full_mesh_rating"] in {
        "FULL_MESH_RATING_INCOMPLETE",
        "FULL_MESH_RATING_COMPLETE",
    }
    assert cov["enumerated_candidate_space_count"] == 48
    assert cov["task174_ready_count"] == 12
    assert cov["task174_not_ready_combination_count"] == 36
    assert cov["selected_for_full_mesh_rating_count"] == 12
    refs = report["recommendation"]["reference_candidate_ids"]
    assert "candidate_b_baseline_id" in refs
    assert "middle_3_5m_reference_id" in refs
    assert "short_reference_id" in refs
    write_r27d_reports(report, tmp_path)
    assert (tmp_path / "R27D_THERMAL_HYDRAULIC_GEOMETRY_COOPTIMIZATION.json").is_file()
