"""Frozen candidate nozzle margin A/B and four-port outlet state."""

# ruff: noqa: E501

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import load_case_bindings
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.first_joint_candidate_identity_v08 import (
    FROZEN_BASELINE_SHELL_NOZZLE_ID_M,
    FROZEN_BASELINE_TUBE_NOZZLE_ID_M,
)
from prototypes.v08_thermal_rating.frozen_candidate_nozzle_margin_and_port_validation_v08 import (
    run_frozen_nozzle_margin_and_port_validation,
)


def test_shell_max_margin_reduces_mid_shell_dp() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_frozen_nozzle_margin_and_port_validation(normalized, handoff, provider=provider)
    mid_a = next(s for s in report.design_a.hydraulic.scenarios if s.scenario_key == "mid_band")
    mid_b = next(s for s in report.design_b.hydraulic.scenarios if s.scenario_key == "mid_band")
    assert mid_a.shell_full_path_dp_pa is not None
    assert mid_b.shell_full_path_dp_pa is not None
    assert Decimal(mid_b.shell_full_path_dp_pa) < Decimal(mid_a.shell_full_path_dp_pa)
    shell_b = report.design_b.hydraulic.ports[2].inside_diameter_m
    assert shell_b > FROZEN_BASELINE_SHELL_NOZZLE_ID_M
    assert report.design_b.hydraulic.ports[0].inside_diameter_m == FROZEN_BASELINE_TUBE_NOZZLE_ID_M


def test_four_port_outlet_density_differs_from_inlet_on_tube_outlet() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_frozen_nozzle_margin_and_port_validation(normalized, handoff, provider=provider)
    ports = {p.port_id: p for p in report.design_b.hydraulic.ports}
    assert ports["TUBE_OUTLET"].velocity_basis == "INDICATIVE_THERMAL_PRESCREEN_OUTLET"
    assert ports["TUBE_INLET"].density_kg_m3 != ports["TUBE_OUTLET"].density_kg_m3
    shell_ports = [p for p in report.design_b.hydraulic.ports if "SHELL" in p.port_id]
    for p in shell_ports:
        assert Decimal("1") <= p.velocity_m_s <= Decimal("3")
    assert report.four_port_density_and_velocity_check == "BLOCKED"
    assert report.high_tube_infeasible_note is not None
