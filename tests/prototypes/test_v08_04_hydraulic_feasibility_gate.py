"""V08-04: full-path budgets, nozzle co-selection, K scenarios, hard gates (targeted)."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_hydraulic_path_input_v1 import (
    R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import (
    CASE_330KW_ID,
    FIXTURE_250,
    FIXTURE_330,
    build_case_identity_bundle,
)
from prototypes.v08_thermal_rating.v08_04_hydraulic_feasibility_gate import (
    DESIGN_FEASIBLE_CLASS,
    FROZEN_R0_CANDIDATE_ID,
    FROZEN_R0_GEOMETRY_HASH,
    TASK_ID,
    V08_03_ENGINEERING_ACCEPTANCE,
    _first_task174_ready_bindings,
    _tube_breakdown_sum_ok,
    evaluate_v08_04_candidate_hydraulics,
    run_shortlist_layout_hydraulic_matrix,
    run_v08_04_acceptance_bundle,
    run_v08_04_gate_completion_bundle,
)
from prototypes.v08_thermal_rating.v08_r27_hydraulic_bridge import (
    task174_hydraulic_postpass_from_bindings,
)

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def provider() -> CoolPropProvider:
    return CoolPropProvider()


def test_v08_04_task_id_and_v08_03_still_blocked() -> None:
    assert TASK_ID == "V08-04"
    assert V08_03_ENGINEERING_ACCEPTANCE == "BLOCKED"


def test_r0_frozen_candidate_full_path_budget_and_no_design_feasible(
    provider: CoolPropProvider,
) -> None:
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_R0_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    assert bindings.geometry_projection_hash == FROZEN_R0_GEOMETRY_HASH
    rec = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
    assert rec.hard_gate.design_feasible == DESIGN_FEASIBLE_CLASS
    assert len(rec.ports) == 4
    assert len(rec.k_scenarios) == 3
    for p in rec.ports:
        v = Decimal(p["velocity_m_s"])
        assert Decimal("1") <= v <= Decimal("3")
    mid = next(s for s in rec.k_scenarios if s.scenario_key == "mid_band")
    assert mid.k_values_source == "R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS"
    assert mid.tube_total_dp_pa is not None
    assert mid.shell_total_dp_pa is not None
    postpass = task174_hydraulic_postpass_from_bindings(bindings)
    exp = postpass.get("experimental_transitional_tube_hydraulic") or {}
    friction_raw = postpass.get("task027_straight_tube_friction_pressure_drop_pa") or exp.get(
        "tube_friction_dp_pa"
    )
    assert friction_raw is not None
    assert _tube_breakdown_sum_ok(
        mid.tube_breakdown,
        mid.tube_total_dp_pa,
        internal_friction_pa=Decimal(str(friction_raw)),
    )
    keys = {k.scenario_key for k in rec.k_scenarios}
    assert keys == frozenset(R27B_ASSUMPTION_LOSS_COEFFICIENT_SCENARIOS.keys())


def test_250kw_independent_case_hydraulics(provider: CoolPropProvider) -> None:
    bundle = build_case_identity_bundle()
    assert bundle["CASE_CROSS_CONTAMINATION"] is False
    bindings = _first_task174_ready_bindings(FIXTURE_250, provider)
    assert bindings is not None
    assert bindings.engineering_case_id != CASE_330KW_ID
    rec = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
    assert rec.hard_gate.design_feasible == DESIGN_FEASIBLE_CLASS
    assert rec.nozzle_design_hash


def test_acceptance_bundle_determinism_and_variable_mdot(provider: CoolPropProvider) -> None:
    payload = run_v08_04_acceptance_bundle(provider=provider)
    assert payload["V08_03_ENGINEERING_ACCEPTANCE"] == "BLOCKED"
    assert payload["PRODUCTION_RATING_VALIDATED"] is False
    assert payload["V08_04_FORMAL_ACCEPTANCE"] is False
    assert payload["DETERMINISM_STATUS"] is True
    assert payload["INDEPENDENT_CASE_STATUS"] is True
    assert payload["R0"]["tube_budget_summation_ok"] is True
    assert payload["VARIABLE_MDOT_REPLAY"]["fixed_geometry_identity_pass"] is True


def test_infeasible_fixture_reports_no_structures(provider: CoolPropProvider) -> None:
    payload = run_v08_04_acceptance_bundle(provider=provider)
    n2 = payload["INFEASIBLE_N2"]
    assert n2["no_feasible_geometry"] is True


def test_r0_shell_search_infeasible_still_computes_over_dp(provider: CoolPropProvider) -> None:
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_R0_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    rec = evaluate_v08_04_candidate_hydraulics(bindings, provider=provider)
    assert rec.hard_gate.shell_full_path == "OVER_DP"
    assert rec.hard_gate.tube_full_path in ("PASS", "OVER_DP", "SCENARIO_DEPENDENT")
    assert "SHELL_NOZZLE_SEARCH_NO_FEASIBLE_POINT_IN_VELOCITY_BAND" in (
        rec.hard_gate.nozzle_search_notes
    )


def test_shortlist_four_layouts_baseline_replay(provider: CoolPropProvider) -> None:
    rows = run_shortlist_layout_hydraulic_matrix(provider=provider)
    keys = {r["shortlist_key"] for r in rows}
    assert keys == {"T235_L5.5", "T235_L6.0", "T241_L5.5", "T241_L6.0"}
    assert all(r["mid_band"] is not None for r in rows if r["outcome"] == "COMPUTED")
    assert sum(1 for r in rows if r["outcome"] == "COMPUTED") >= 1


def test_gate_completion_bundle_false_blocked_zero(provider: CoolPropProvider) -> None:
    payload = run_v08_04_gate_completion_bundle(provider=provider)
    assert payload["FALSE_BLOCKED_COUNT"] == 0
    assert payload["FULL_PATH_DP_CALCULATION_STATUS"] == "COMPUTED_ALL_K_TIERS"
    assert (
        payload["NOZZLE_SEARCH_CORRECTION_STATUS"]
        == "BISECT_NO_FEASIBLE_DECOUPLED_FROM_FULL_PATH_COMPUTE"
    )
