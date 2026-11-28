"""Pareto joint optimization includes recovered 0.52 m and bounded local combos."""

# ruff: noqa: E501

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.recovered_shell_052_full_chain_v08 import (
    FROZEN_SHELL_052_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    Shell052ParetoJointReport,
)
from prototypes.v08_thermal_rating.thermal_hydraulic_joint_cooptimization_v08 import (
    run_thermal_hydraulic_joint_cooptimization,
)

pytest_plugins = ["tests.prototypes.conftest_v08_joint_pareto"]


def test_joint_pool_includes_recovered_shell_052_geometry() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_thermal_hydraulic_joint_cooptimization(
        normalized, handoff, provider=provider, max_valid=64
    )
    v2s = {r.geometry_v2 for r in report.rows}
    assert FROZEN_SHELL_052_GEOMETRY_V2 in v2s


def test_pareto_bounded_search_finds_mid_joint_or_reports_front(
    pareto_joint_report_330: Shell052ParetoJointReport,
) -> None:
    report = pareto_joint_report_330
    assert report.recovered_shell_052_included is True
    assert report.previous_experimental_count >= 5
    assert any(r.geometry_v2 == FROZEN_SHELL_052_GEOMETRY_V2 for r in report.rows)
    assert report.newly_generated_count <= 6
    if report.mid_joint_prescreen_pass_count > 0:
        assert report.design_decision == "JOINT_PRESCREEN_PASS"
        mid = [r for r in report.rows if r.mid_joint_pass]
        assert all(r.clean_thermal.status == "INDICATIVE_PASS" for r in mid)
    else:
        assert report.design_decision == "BOUNDED_SEARCH_NOT_FEASIBLE"
        assert len(report.pareto_front) >= 1
