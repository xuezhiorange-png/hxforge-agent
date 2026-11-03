"""R27G: local shell lattice enumeration, classification, and Pareto guards."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.r27g_shell_geometry_local_pareto import (
    build_r27g_local_selection,
    classify_r27g_outcome,
    enumerate_r27g_local_search_records,
    r27g_local_rating_candidate_ids,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def test_r27g_local_lattice_record_count_and_rating_budget() -> None:
    case = shared_r26e_engineering_case()
    sel = build_r27g_local_selection(case)
    local = enumerate_r27g_local_search_records(sel)
    assert len(local) == 12
    rate_ids = r27g_local_rating_candidate_ids(sel)
    assert len(rate_ids) == 8
    assert len(sel.selected_candidate_ids) == 8


def test_r27g_primary_seed_in_local_queue() -> None:
    case = shared_r26e_engineering_case()
    sel = build_r27g_local_selection(case)
    assert any(cid.startswith("9c4b84db") for cid in sel.selected_candidate_ids)


def test_r27g_classify_structural_blocked_for_065_shell() -> None:
    case = shared_r26e_engineering_case()
    sel = build_r27g_local_selection(case)
    blocked = next(r for r in sel.records if r.shell_inside_diameter_m == "0.65")
    out = classify_r27g_outcome(
        record=blocked,
        multi_row=None,
        scenario_results={},
        target_duty_w=Decimal("330000"),
        case=case,
    )
    assert out["outcome_class"] == "STRUCTURAL_BLOCKED"


def test_r27g_discrete_search_disclosure_in_sealed_fixture() -> None:
    """Fast CI regression: frozen R27G disclosure and candidate coverage."""
    fixture_dir = Path(__file__).resolve().parents[1] / "fixtures"
    fixture = fixture_dir / "R27G_SHELL_GEOMETRY_LOCAL_PARETO.json"
    report = json.loads(fixture.read_text(encoding="utf-8"))
    assert "tube_length_m" in report["discrete_search_disclosure"]
    assert report["local_search_budget"]["max_rating_queue"] == 12
    assert len(report["local_search_budget"]["rated_candidate_ids"]) == 8
    verdict = report["engineering_verdict"]
    assert verdict["best_mid_band_candidate_id_prefix"] == "9c4b84db"


@pytest.mark.slow
def test_r27g_discrete_search_disclosure_in_report() -> None:
    case = shared_r26e_engineering_case()
    from prototypes.v07_general_rating_sizing_mvp.r27g_shell_geometry_local_pareto import (
        run_r27g_shell_geometry_local_pareto,
    )

    report = run_r27g_shell_geometry_local_pareto(
        case,
        run_full_mesh_hydraulic=False,
        precomputed_selection=build_r27g_local_selection(case),
    )
    assert "tube_length_m" in report["discrete_search_disclosure"]
    assert report["local_search_budget"]["max_rating_queue"] == 12


@pytest.mark.slow
def test_r27g_full_local_pareto_best_margin_matches_primary_seed() -> None:
    """End-to-end: eight lattice ratings; best mid_band margin at 9c4b84db (~−70 Pa)."""
    case = shared_r26e_engineering_case()
    from prototypes.v07_general_rating_sizing_mvp.r27g_shell_geometry_local_pareto import (
        run_r27g_shell_geometry_local_pareto,
    )

    report = run_r27g_shell_geometry_local_pareto(case)
    v = report["engineering_verdict"]
    assert v["best_mid_band_candidate_id_prefix"] == "9c4b84db"
    assert v["mid_band_formal_feasible_count"] == 0
    assert v["joint_shell_baffle_ladder_can_deliver_mid_band_positive_margin_at_330kw"] is False
    gap = Decimal(str(v["best_mid_band_min_margin_pa"]))
    assert gap < Decimal("0")
    assert gap > Decimal("-100")
