"""R26E tradeoff comparison, expanded candidate space, nominal feasibility guards."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    _nominal_experimental_comparison_status,
    run_experimental_multi_candidate_engineering_sizing,
)

_FIXTURE_R26D = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26d_multi_candidate_engineering_sizing_case.json"
)
_FIXTURE_R26E = (
    Path(__file__).resolve().parents[1]
    / "fixtures/r26e_multi_candidate_engineering_sizing_case.json"
)


@pytest.fixture(name="r26e_case")
def _r26e_case():
    return load_general_engineering_case_json(_FIXTURE_R26E.read_text(encoding="utf-8"))


def test_r26e_expanded_space_at_least_three_task174_ready_geometries(r26e_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26e_case)
    ready = [row for row in selection.records if row.rating_request_ready]
    distinct = {row.geometry_projection_hash for row in ready}
    assert len(distinct) >= 3, (
        f"expected >=3 distinct Task174-ready geometries, got {len(distinct)} "
        f"(task174_ready={selection.task174_ready_count})"
    )
    assert len(selection.selected_candidate_ids) >= 3


def test_r26e_nominal_feasibility_rejects_blocked_hydraulic_despite_dp_under_limit(
    r26e_case,
) -> None:
    target = float(r26e_case.target_duty_w)
    finest = SimpleNamespace(status=ENGINEERING_NUMERIC_VALID, duty_w=target + 1000.0)
    package = {
        "mesh_convergence": {"FULL_RATING_CONVERGED": True, "results": {4: finest}},
        "hydraulic_margin": {"NOMINAL_CONSTRAINT_STATUS": "SATISFIED"},
        "hydraulic_receipt": {
            "HYDRAULIC_CONSTRAINT_STATUS": "SATISFIED",
            "LIVE_HYDRAULIC_IMPLEMENTED": True,
            "LIVE_TUBE_DP_PA": "500",
            "LIVE_SHELL_DP_PA": "900",
        },
        "live_thermal_state_hydraulic_postpass": {
            "hydraulic_constraint_status": "BLOCKED",
            "tube_dp_constraint": "SATISFIED",
            "shell_dp_constraint": "SATISFIED",
            "tube_hydraulic_recompute_status": "SUCCESS",
            "shell_hydraulic_recompute_status": "SUCCESS",
            "correlation_applicability_status": "APPLICABLE",
            "recalculated_tube_dp_pa": "500",
            "recalculated_shell_dp_pa": "900",
            "blockers": [{"code": "BLOCKED_SHELL_HYDRAULIC_RECOMPUTE"}],
        },
    }
    ok, status, reasons = _nominal_experimental_comparison_status(package, case=r26e_case)
    assert ok is False
    assert status == "NOT_NOMINAL_FEASIBLE"
    assert any("HYDRAULIC_CONSTRAINT_BLOCKED" in r or "BLOCKERS" in r for r in reasons)


def test_r26e_unrated_candidate_eligibility_not_evaluated(r26e_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(
        r26e_case, run_full_mesh_hydraulic=False, max_candidates=1
    )
    not_rated = [
        row
        for row in report["candidates"]
        if row.get("screening_n1_status") == "NOT_SELECTED_FOR_RATING"
    ]
    assert not_rated
    assert not_rated[0]["ENGINEERING_SIZING_ELIGIBILITY"] == "NOT_EVALUATED"
    assert not_rated[0]["GEOMETRY_COMPLETENESS_STATUS"] == "NOT_EVALUATED"


def test_r26d_baseline_fixture_unchanged_two_distinct_ready() -> None:
    case = load_general_engineering_case_json(_FIXTURE_R26D.read_text(encoding="utf-8"))
    selection = enumerate_experimental_rating_candidates(case)
    ready = [row for row in selection.records if row.rating_request_ready]
    assert len({r.geometry_projection_hash for r in ready}) >= 2


@pytest.mark.slow
def test_r26e_full_multi_candidate_tradeoff_and_baseline_preservation_slow(r26e_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(
        r26e_case, run_full_mesh_hydraulic=True
    )
    assert report["TASK_ID"] == "V07_R26E_ENGINEERING_TRADEOFF_AND_CANDIDATE_EXPANSION"
    assert report["TASK174_READY_COUNT"] >= 3
    assert report["FULLY_RATED_CANDIDATE_COUNT"] >= 3
    baseline = next(r for r in report["candidates"] if r["is_candidate_b_baseline_geometry"])
    assert baseline["FULL_RATING_CONVERGED"] is True
    assert baseline["GEOMETRY_COMPLETENESS_STATUS"] == "ENTRANCE_ONLY_ASSUMED"
    assert (
        baseline["ENGINEERING_SIZING_ELIGIBILITY"]
        == "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )
    tradeoff = report["experimental_tradeoff_comparison"]
    assert tradeoff["ENGINEERING_DESIGN_PREFERENCE"] == "OWNER_POLICY_REQUIRED"
    assert tradeoff["MIN_AREA_NOMINAL_CANDIDATE_ID"] is not None
    assert len(tradeoff["AREA_HYDRAULIC_MARGIN_PARETO_FRONTIER_CANDIDATE_IDS"]) >= 1
    if report["NOMINAL_FEASIBLE_COUNT"] >= 1:
        assert report["MIN_AREA_NOMINAL_CANDIDATE_ID"] == report["BEST_EXPERIMENTAL_CANDIDATE_ID"]
        ranked = report["ranked_candidates"]
        assert Decimal(str(ranked[0]["nominal_tube_outer_area_m2"])) <= Decimal(
            str(ranked[-1]["nominal_tube_outer_area_m2"])
        )


@pytest.mark.slow
def test_r26e_n1_cache_reuse_matches_screening_duty_slow(r26e_case) -> None:
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
        run_experimental_engineering_rating,
    )
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
        build_experimental_engineering_rating_live_package,
    )
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        build_native_cell_context,
    )

    selection = enumerate_experimental_rating_candidates(r26e_case)
    cid = selection.selected_candidate_ids[0]
    native = build_native_cell_context(r26e_case, selection=selection, candidate_id=cid)
    cache: dict[int, object] = {}
    n1 = run_experimental_engineering_rating(
        r26e_case, subdivisions=1, native=native, mesh_result_cache=cache
    )
    assert 1 in cache
    package = build_experimental_engineering_rating_live_package(
        r26e_case,
        native=native,
        run_mesh_ladder=True,
        run_hydraulic_sensitivity=False,
        mesh_result_cache=cache,
    )
    n1_ladder = package["mesh_convergence"]["results"][1]
    assert n1.duty_w == n1_ladder.duty_w
    assert n1.tube_outlet_temperature_k == n1_ladder.tube_outlet_temperature_k
    assert n1.shell_outlet_temperature_k == n1_ladder.shell_outlet_temperature_k
