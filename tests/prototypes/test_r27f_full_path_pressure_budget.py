"""R27F: full-path pressure budget summation, nozzle velocity band, and margin curves."""

from __future__ import annotations

from decimal import Decimal

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    NOZZLE_VELOCITY_DESIGN_RULE,
)
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _diameter_from_velocity_m,
    _search_nozzle_d_in_velocity_band,
    _side_inlet_density_kg_m3,
    _tube_path_dp_pa_for_nozzle_d,
    _velocity_bounds_m_s,
    _velocity_from_diameter_m,
)
from prototypes.v07_general_rating_sizing_mvp.r27f_full_path_pressure_budget import (
    evaluate_velocity_margin_curve,
    r27f_eight_full_mesh_candidate_ids,
)
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


def _minimal_tube_postpass(*, friction_pa: str = "700", shell_total: str = "900") -> dict:
    return {
        "correlation_applicability_status": "APPLICABLE",
        "tube_hydraulic_recompute_status": "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
        "experimental_transitional_tube_hydraulic": {"tube_friction_dp_pa": friction_pa},
        "shell_dp_components_pa": {"total": shell_total},
    }


def test_r27f_eight_candidate_id_list() -> None:
    case = shared_r26e_engineering_case()
    ids = r27f_eight_full_mesh_candidate_ids(case)
    assert len(ids) == 8
    assert ids[-1].startswith("09dac82a")


def test_nozzle_velocity_band_matches_design_rule() -> None:
    vmin, vmax = _velocity_bounds_m_s(NOZZLE_VELOCITY_DESIGN_RULE)
    assert vmin == pytest.approx(1.0)
    assert vmax == pytest.approx(3.0)


def test_nozzle_diameter_velocity_roundtrip() -> None:
    case = shared_r26e_engineering_case()
    rho = _side_inlet_density_kg_m3(case, "tube_side")
    m = float(case.tube_side.mass_flow_kg_s)
    d = _diameter_from_velocity_m(mass_flow_kg_s=m, rho=rho, velocity_m_s=2.0)
    v = _velocity_from_diameter_m(mass_flow_kg_s=m, rho=rho, diameter_m=d)
    assert v == pytest.approx(2.0, rel=1e-9)


def test_tube_path_breakdown_sums_to_modeled_total() -> None:
    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    record = next(r for r in sel.records if r.candidate_id.startswith("9aba0e5c"))
    # Minimal postpass stub with friction only — upstream bisect tests cover full postpass.
    postpass = _minimal_tube_postpass()
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["mid_band"]
    d_min, d_max = _search_nozzle_d_in_velocity_band(
        case=case, side="tube_side", velocity_rule=NOZZLE_VELOCITY_DESIGN_RULE
    )
    total, bd = _tube_path_dp_pa_for_nozzle_d(
        case=case,
        record=record,
        postpass=postpass,
        scenario=scenario,
        tube_nozzle_d_m=Decimal(str(d_max)),
    )
    assert total is not None
    parts = sum(
        float(bd[k])
        for k in (
            "tube_internal_friction_dp_pa",
            "tube_channel_head_dp_pa",
            "tube_bundle_entrance_dp_pa",
            "tube_bundle_exit_dp_pa",
            "tube_nozzle_pair_dp_pa",
        )
    )
    assert parts == pytest.approx(float(total), rel=1e-9)


def test_k_scenario_changes_nozzle_local_loss() -> None:
    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    record = next(r for r in sel.records if r.candidate_id.startswith("9aba0e5c"))
    postpass = _minimal_tube_postpass()
    mid = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["mid_band"]
    low = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["low_loss_sensitivity"]
    d = Decimal("0.12")
    _, bd_mid = _tube_path_dp_pa_for_nozzle_d(
        case=case,
        record=record,
        postpass=postpass,
        scenario=mid,
        tube_nozzle_d_m=d,
    )
    _, bd_low = _tube_path_dp_pa_for_nozzle_d(
        case=case,
        record=record,
        postpass=postpass,
        scenario=low,
        tube_nozzle_d_m=d,
    )
    assert float(bd_mid["tube_nozzle_pair_dp_pa"]) != float(bd_low["tube_nozzle_pair_dp_pa"])


@pytest.mark.slow
def test_r27f_9c4b84db_low_loss_margin_curve_best_in_band() -> None:
    """9c4b84db: verify max shell margin within 1–3 m/s via explicit velocity samples."""
    from prototypes.v07_general_rating_sizing_mvp.r27f_full_path_pressure_budget import (
        load_rating_postpass_for_candidate,
    )

    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    cid = next(c for c in sel.selected_candidate_ids if c.startswith("9c4b84db"))
    postpass, duty, err = load_rating_postpass_for_candidate(case, candidate_id=cid, selection=sel)
    assert err is None, err
    record = next(r for r in sel.records if r.candidate_id == cid)
    curve = evaluate_velocity_margin_curve(
        case=case,
        record=record,
        postpass=postpass,
        loss_scenario_key="low_loss_sensitivity",
    )
    best = curve["best_margin_in_band"]["shell_side"]
    assert best is not None
    assert best["shell_margin_pa"] is not None
    # Computed band optimum must beat min-diameter optimizer shell margin (~0.0005 Pa).
    assert float(best["shell_margin_pa"]) >= 0.0005
