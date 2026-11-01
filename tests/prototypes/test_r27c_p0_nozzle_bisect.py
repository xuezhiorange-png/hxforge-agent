"""R27C P0: nozzle bisect correctness and recommendation guards."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest

from prototypes.v07_general_rating_sizing_mvp.calculation_first_automatic_sizing import (
    find_candidate_b_record,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_cooptimization_sizing import (
    _rank_candidates,
    _scenario_recommendation_eligible,
)
from prototypes.v07_general_rating_sizing_mvp.nozzle_pressure_budget_solver import (
    _bisect_feasible_nozzle_d,
    _component_dp_pa,
    _search_nozzle_d_in_velocity_band,
    _side_inlet_density_kg_m3,
    _tube_path_dp_pa_for_nozzle_d,
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


def _minimal_tube_postpass(*, friction_pa: str = "131") -> dict[str, Any]:
    return {
        "correlation_applicability_status": "APPLICABLE",
        "tube_hydraulic_recompute_status": "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
        "experimental_transitional_tube_hydraulic": {
            "tube_friction_dp_pa": friction_pa,
        },
    }


def test_bisect_selects_min_diameter_when_both_band_edges_feasible(
    r26e_case, r26e_selection
) -> None:
    """When max-velocity (min D) edge already satisfies Δp, pick min diameter."""
    baseline = find_candidate_b_record(r26e_selection)
    assert baseline is not None
    postpass = _minimal_tube_postpass(friction_pa="100")
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["low_loss_sensitivity"]
    d_min, _d_max = _search_nozzle_d_in_velocity_band(
        case=r26e_case, side="tube_side", velocity_rule=None
    )
    result = _bisect_feasible_nozzle_d(
        case=r26e_case,
        record=baseline,
        postpass=postpass,
        scenario=scenario,
        side="tube_side",
        max_dp_pa=Decimal("50000"),
        velocity_rule=None,
        tube_nozzle_d_m=None,
        shell_nozzle_d_m=None,
    )
    assert result["status"] == "FEASIBLE_WITHIN_DESIGN_BOUNDS"
    assert result["selected_inside_diameter_m"] == pytest.approx(d_min, rel=0, abs=1e-9)


def test_bisect_fails_when_max_diameter_still_exceeds_budget(r26e_case, r26e_selection) -> None:
    baseline = find_candidate_b_record(r26e_selection)
    assert baseline is not None
    postpass = _minimal_tube_postpass()
    postpass["shell_dp_components_pa"] = {
        "total": "1174.2016697779067231700668548068167977062202535808"
    }
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["mid_band"]
    shell = _bisect_feasible_nozzle_d(
        case=r26e_case,
        record=baseline,
        postpass=postpass,
        scenario=scenario,
        side="shell_side",
        max_dp_pa=Decimal("1180"),
        velocity_rule=None,
        tube_nozzle_d_m=None,
        shell_nozzle_d_m=None,
    )
    assert shell["status"] == "NO_FEASIBLE_WITHIN_DESIGN_BOUNDS"
    assert shell.get("failure_dominant_mechanism") == (
        "SHELL_BUNDLE_INTERNAL_PLUS_FIXED_TRANSITIONS_DOMINATE"
    )


def test_candidate_b_mid_band_nozzle_pair_at_vmax_exceeds_tube_limit(
    r26e_case, r26e_selection
) -> None:
    """Regression: at ~3 m/s, mid_band tube nozzle pair loss alone must exceed 1150 Pa."""
    baseline = find_candidate_b_record(r26e_selection)
    assert baseline is not None
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["mid_band"]
    rho = Decimal(str(_side_inlet_density_kg_m3(r26e_case, "tube_side")))
    m = Decimal(str(r26e_case.tube_side.mass_flow_kg_s))
    d_min, _d_max = _search_nozzle_d_in_velocity_band(
        case=r26e_case, side="tube_side", velocity_rule=None
    )
    area = nozzle_flow_area_m2(Decimal(str(d_min)))
    nozzle_pair = _component_dp_pa(
        rho=rho,
        mass_kg_s=m,
        ref_area_m2=area,
        loss_k=scenario["tube_nozzle_k"],
        multiplicity=2,
    )
    assert float(nozzle_pair) > 1150.0


def test_candidate_b_tube_side_not_feasible_at_vmax_band_edge(r26e_case, r26e_selection) -> None:
    baseline = find_candidate_b_record(r26e_selection)
    assert baseline is not None
    postpass = _minimal_tube_postpass()
    scenario = R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS["mid_band"]
    d_min, _ = _search_nozzle_d_in_velocity_band(
        case=r26e_case, side="tube_side", velocity_rule=None
    )
    total, _ = _tube_path_dp_pa_for_nozzle_d(
        case=r26e_case,
        record=baseline,
        postpass=postpass,
        scenario=scenario,
        tube_nozzle_d_m=Decimal(str(d_min)),
    )
    assert total is not None and float(total) > 1150.0
    tube = _bisect_feasible_nozzle_d(
        case=r26e_case,
        record=baseline,
        postpass=postpass,
        scenario=scenario,
        side="tube_side",
        max_dp_pa=Decimal("1150"),
        velocity_rule=None,
        tube_nozzle_d_m=None,
        shell_nozzle_d_m=None,
    )
    if tube["status"] == "FEASIBLE_WITHIN_DESIGN_BOUNDS":
        assert float(tube["selected_velocity_m_s"]) < 3.0 - 1e-6
        assert float(tube["modeled_side_total_dp_pa"]) <= 1150.0


def test_rank_excludes_duty_not_satisfied_even_if_full_path_flag_true() -> None:
    row = {
        "candidate_id": "fake",
        "rating_participation_status": "FULLY_RATED",
        "thermal_rating": {"full_rating_converged": True, "duty_w": 300000},
        "constraints": {"duty_constraint": "NOT_SATISFIED"},
        "geometry": {"task171_rated_outside_area_m2": 50.0},
        "loss_scenario_results": {
            "mid_band": {
                "full_path_feasible": True,
                "full_path_hydraulic_verification": {
                    "status": "COMPUTED",
                    "FULL_PATH_HYDRAULIC_STATUS": "SATISFIED",
                    "FULL_PATH_TUBE_CONSTRAINT_STATUS": "SATISFIED",
                    "FULL_PATH_SHELL_CONSTRAINT_STATUS": "SATISFIED",
                    "FULL_PATH_TUBE_OUTLET_DOMAIN_STATUS": "SATISFIED",
                    "FULL_PATH_SHELL_OUTLET_DOMAIN_STATUS": "SATISFIED",
                    "TUBE_FULL_PATH_DP_MARGIN_PA": "10",
                    "SHELL_FULL_PATH_DP_MARGIN_PA": "10",
                },
            }
        },
    }
    assert _scenario_recommendation_eligible(row, "mid_band") is False
    assert _rank_candidates([row]) == []
