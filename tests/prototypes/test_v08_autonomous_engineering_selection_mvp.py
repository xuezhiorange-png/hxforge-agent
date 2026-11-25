"""Tests for V08_AUTONOMOUS_ENGINEERING_SELECTION_MVP."""

# ruff: noqa: E501

from __future__ import annotations

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.v08_autonomous_engineering_selection_mvp import (
    ENGINEERING_DESIGN_STATUS,
    run_autonomous_engineering_selection,
)


def test_joint_pass_stricter_than_hydraulic_tiers_computed() -> None:
    report = run_autonomous_engineering_selection(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=CoolPropProvider(),
    )
    hydraulic_only = [
        v
        for v in report.scenario_verdicts
        if v.hydraulic_all_tiers_pass and not v.engineering_joint_pass
    ]
    assert hydraulic_only, "expected scenarios with hydraulic pass but joint fail"
    assert all(
        "THERMAL_Q_BELOW_TARGET" in v.joint_block_reasons
        or "NOZZLE_VELOCITY_OUT_OF_1_3_M_S" in v.joint_block_reasons
        for v in hydraulic_only
    )


def test_t235_l5p5_three_sweeps_below_330kw_target() -> None:
    report = run_autonomous_engineering_selection(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=CoolPropProvider(),
    )
    audit = report.t235_l5p5_thermal_audit
    assert audit["scenarios_below_target_count"] == 3
    keys = {row["scenario_key"] for row in audit["below_target_rows"]}
    assert keys == {
        "tube_mdot_minus_1pct",
        "tube_mdot_minus_3pct",
        "shell_mdot_minus_3pct",
    }


def test_robust_exploration_null_on_330kw() -> None:
    report = run_autonomous_engineering_selection(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=CoolPropProvider(),
    )
    assert report.rankings.robust_exploration is None


def test_independent_250kw_changes_hydraulic_ranking() -> None:
    provider = CoolPropProvider()
    r330 = run_autonomous_engineering_selection(
        FIXTURE_330.read_text(encoding="utf-8"), provider=provider
    )
    r250 = run_autonomous_engineering_selection(
        FIXTURE_250.read_text(encoding="utf-8"), provider=provider
    )
    assert r330.engineering_case_id != r250.engineering_case_id
    assert r330.target_duty_w != r250.target_duty_w
    assert r330.rankings.hydraulic_margin_best != r250.rankings.hydraulic_margin_best
    assert r330.engineering_design_status == ENGINEERING_DESIGN_STATUS


def test_selected_design_spec_has_required_fields() -> None:
    report = run_autonomous_engineering_selection(
        FIXTURE_330.read_text(encoding="utf-8"),
        provider=CoolPropProvider(),
    )
    spec = report.selected_design_spec
    assert spec is not None
    g = spec["geometry"]
    for key in (
        "shell_inside_diameter_m",
        "tube_outer_diameter_m",
        "physical_tube_count",
        "tube_length_m",
        "baffle_count",
        "baffle_spacing_m",
        "baffle_cut_fraction",
    ):
        assert key in g
    assert len(spec["nozzles_four_port"]) == 4
    assert spec["thermal_experimental_prescreen"]["clean_q_w"] is not None
