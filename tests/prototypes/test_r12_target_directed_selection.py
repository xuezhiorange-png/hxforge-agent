"""R12 target-directed candidate selection (no mesh)."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection_policy import MIN_AREA_POLICY
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)

REPO = Path(__file__).resolve().parents[2]
R12_CASE = REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_target_directed_r12.json"
R10_CASE = REPO / "prototypes/v07_general_rating_sizing_mvp/cases/mvp_multi_candidate_r10.json"


def test_r12_min_area_search_not_first_enumeration_order() -> None:
    case = load_general_engineering_case_json(R12_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    assert sel.selection_reason == MIN_AREA_POLICY
    assert len(sel.selected_candidate_ids) == 2
    baseline = {("4.85", "0.97"), ("4.90", "0.98")}
    pool = [
        r
        for r in sel.records
        if r.rating_request_ready and (r.tube_length_m, r.baffle_spacing_m) not in baseline
    ]
    expected_ids = [
        r.candidate_id
        for r in sorted(
            pool,
            key=lambda row: Decimal(row.nominal_tube_outer_area_proxy_m2 or "Infinity"),
        )[:2]
    ]
    assert list(sel.selected_candidate_ids) == expected_ids
    assert sel.selection_reason != "FIRST_N_DISTINCT_GEOMETRY_TASK174_READY_UNDER_SOLVER_BUDGET"


def test_r12_excludes_r10_baseline_geometries_from_live_selection() -> None:
    case = load_general_engineering_case_json(R12_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    selected = {r.candidate_id: r for r in sel.records if r.selected_for_rating}
    for row in selected.values():
        assert (row.tube_length_m, row.baffle_spacing_m) not in {
            ("4.85", "0.97"),
            ("4.90", "0.98"),
        }


def test_r10_still_uses_first_n_selection_policy() -> None:
    case = load_general_engineering_case_json(R10_CASE.read_text(encoding="utf-8"))
    sel = enumerate_experimental_rating_candidates(case)
    assert "FIRST_N" in (sel.selection_reason or "")
