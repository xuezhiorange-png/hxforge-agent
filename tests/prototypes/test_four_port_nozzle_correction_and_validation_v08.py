"""Four-port strict velocity trials and outlet-state hydraulics."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.four_port_nozzle_correction_and_validation_v08 import (
    run_four_port_nozzle_correction_and_validation,
)


def test_grid_trials_pass_strict_velocity_and_mid_joint() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_four_port_nozzle_correction_and_validation(normalized, handoff, provider=provider)
    grid = [t for t in report.trials if t.grid_trial]
    assert len(grid) == 4
    assert all(t.strict_velocity == "PASS" for t in grid)
    assert all(t.mid_joint_prescreen == "PASS" for t in grid)
    assert report.selected_trial is not None
    assert report.selected_trial.grid_trial is True
    assert report.four_port_strict_velocity_check == "PASS"
    assert Decimal(report.selected_tube_id_mm or "0") <= Decimal("123.80")
    for p in report.selected_trial.port_records:
        assert Decimal("1") <= p.velocity_m_s <= Decimal("3")


def test_tube_outlet_d_max_below_legacy_124_02() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_four_port_nozzle_correction_and_validation(normalized, handoff, provider=provider)
    tube = report.diameter_bounds[0]
    assert tube.feasible_interval_nonempty
    legacy = Decimal("0.12402")
    assert tube.d_max_at_v_lo_m_outlet < legacy
    assert report.outlet_property_consistency == "PASS"
