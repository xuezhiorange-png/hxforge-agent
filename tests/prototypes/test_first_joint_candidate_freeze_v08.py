"""First joint candidate freeze and pareto user-constraint handling."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_freeze_v08 import (
    run_first_joint_candidate_freeze,
)
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_FIRST_JOINT_CANDIDATE_ID,
    FROZEN_FIRST_JOINT_GEOMETRY_V2,
)
from prototypes.v08_thermal_rating.recovered_shell_052_pareto_joint_v08 import (
    PARETO_METRIC_UNAVAILABLE,
    run_recovered_shell_052_pareto_joint_optimization,
    select_first_joint_frozen_row,
)


def test_pareto_reads_user_target_duty_not_hardcoded() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_250, provider=provider)
    report = run_recovered_shell_052_pareto_joint_optimization(
        normalized, handoff, provider=provider
    )
    target = Decimal(str(normalized.target_duty_w))
    for row in report.rows:
        if row.q_deficit_w == PARETO_METRIC_UNAVAILABLE:
            continue
        if row.clean_thermal.epsilon_ntu_q_w is None:
            continue
        q = Decimal(row.clean_thermal.epsilon_ntu_q_w)
        expected = max(Decimal("0"), target - q).quantize(Decimal("0.1"))
        assert Decimal(row.q_deficit_w) == expected


def test_pareto_front_excludes_incomplete_rows() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_recovered_shell_052_pareto_joint_optimization(
        normalized, handoff, provider=provider
    )
    for row in report.pareto_front:
        assert row.q_deficit_w != PARETO_METRIC_UNAVAILABLE
        assert row.tube_dp_excess_pa != PARETO_METRIC_UNAVAILABLE
        assert row.shell_dp_excess_pa != PARETO_METRIC_UNAVAILABLE
        assert row.hydraulic is not None


def test_first_joint_freeze_replay_identity_and_spec() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    freeze = run_first_joint_candidate_freeze(normalized, handoff, provider=provider)
    assert freeze.candidate_id == FROZEN_FIRST_JOINT_CANDIDATE_ID
    assert freeze.geometry_v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert freeze.structure_spec_complete is True
    assert freeze.geometry_identity_replay == "PASS"
    spec = freeze.design_spec
    assert spec["candidate_id"] == FROZEN_FIRST_JOINT_CANDIDATE_ID
    assert freeze.structure_spec_validation in ("PASS", "BLOCKED", "NOT_EVALUATED")
    assert freeze.generic_user_constraints in ("PASS", "BLOCKED", "NOT_EVALUATED")
    assert spec["geometry_identity_v2"] == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert "placement_envelope_scale" in spec["geometry"]
    mid = next(s for s in freeze.hydraulic.scenarios if s.scenario_key == "mid_band")
    assert mid.hydraulic_check == "PASS"
    high = next(s for s in freeze.hydraulic.scenarios if s.scenario_key == "high_loss_sensitivity")
    assert high.hydraulic_check != "PASS"


def test_select_first_joint_frozen_row_matches_geometry() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_recovered_shell_052_pareto_joint_optimization(
        normalized, handoff, provider=provider
    )
    row = select_first_joint_frozen_row(report)
    assert row is not None
    assert row.geometry_v2 == FROZEN_FIRST_JOINT_GEOMETRY_V2
    assert row.mid_joint_pass is True