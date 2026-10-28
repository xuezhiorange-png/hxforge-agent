"""R26D multi-candidate engineering sizing (fast + slow)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_multi_candidate_engineering_sizing import (
    run_experimental_multi_candidate_engineering_sizing,
)

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures/r26d_multi_candidate_engineering_sizing_case.json"
)


@pytest.fixture(name="r26d_case")
def _r26d_case():
    return load_general_engineering_case_json(_FIXTURE.read_text(encoding="utf-8"))


def test_r26d_task168_space_has_two_distinct_ready_geometries(r26d_case) -> None:
    selection = enumerate_experimental_rating_candidates(r26d_case)
    ready = [row for row in selection.records if row.rating_request_ready]
    distinct = {row.geometry_projection_hash for row in ready}
    assert len(distinct) >= 2
    assert len(selection.selected_candidate_ids) >= 2
    assert selection.selected_candidate_ids[0] != selection.selected_candidate_ids[1]


def test_r26d_n1_screening_independent_per_candidate(r26d_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(
        r26d_case,
        run_full_mesh_hydraulic=False,
    )
    assert report["CANDIDATE_SPACE_BLOCKER"] is None
    assert report["RATED_CANDIDATE_COUNT"] >= 2
    rated = [
        row
        for row in report["candidates"]
        if row.get("n1_thermal_numeric_status") == "EXPERIMENTAL_ENGINEERING_NUMERIC_VALID"
    ]
    assert len(rated) >= 2
    assert rated[0]["candidate_id"] != rated[1]["candidate_id"]
    assert rated[0]["n1_duty_w"] != rated[1]["n1_duty_w"]


def test_r26d_shell_eval_pressure_uses_bulk_pressure_pa_field() -> None:
    from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_hydraulic_margin import (
        _shell_eval_pressure_from_postpass,
    )

    postpass = {"property_inputs": {"shell": {"bulk_pressure_pa": "100737.9"}}}
    assert _shell_eval_pressure_from_postpass(postpass) == "100737.9"


@pytest.mark.slow
def test_r26d_full_multi_candidate_engineering_sizing_slow(r26d_case) -> None:
    report = run_experimental_multi_candidate_engineering_sizing(r26d_case, run_full_mesh_hydraulic=True)
    assert report["DISTINCT_READY_GEOMETRY_COUNT"] >= 2
    assert report["RATED_CANDIDATE_COUNT"] >= 2
    assert report["FULLY_CONVERGED_CANDIDATE_COUNT"] >= 1
    baseline = next(r for r in report["candidates"] if r["is_candidate_b_baseline_geometry"])
    assert baseline["FULL_RATING_CONVERGED"] is True
    assert report["engineering_comparison_report"]["baseline_candidate_b"]["candidate_id"] == baseline[
        "candidate_id"
    ]
    assert report["SIZING_TARGET_AUTHORITY"] == "EXPERIMENTAL_DEMONSTRATION_NOT_OWNER_APPROVED"
    for row in report["candidates"]:
        if row.get("FULL_RATING_CONVERGED"):
            assert row["ENGINEERING_SIZING_ELIGIBILITY"] == (
                "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
            )
    if report["NOMINAL_FEASIBLE_COUNT"] >= 1:
        assert report["RANKING_STATUS"] == "EXPERIMENTAL_RANKING_AVAILABLE"
        best = report["BEST_EXPERIMENTAL_CANDIDATE_ID"]
        assert best is not None
        ranked = report["ranked_candidates"]
        assert Decimal(str(ranked[0]["nominal_tube_outer_area_m2"])) <= Decimal(
            str(ranked[-1]["nominal_tube_outer_area_m2"])
        )
    else:
        assert report["RANKING_STATUS"] == "NO_NOMINAL_FEASIBLE_CANDIDATE"
