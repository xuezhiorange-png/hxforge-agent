"""Autonomous nozzle sizing and full-path hydraulics for HXFORGE_330KW_STRICT_DP."""

from __future__ import annotations

from decimal import Decimal

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.autonomous_nozzle_full_path_hydraulics_v08 import (
    run_autonomous_nozzle_full_path,
    scan_manufacturable_full_path_inventory,
)
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.nozzle_velocity_v08 import assess_nozzle_velocities
from tests.prototypes.test_v08_frozen_candidate_resolve import FROZEN_HASH, FROZEN_ID

_REPO_ROOT = FIXTURE_330.resolve().parents[1]


def test_frozen_candidate_four_nozzles_from_real_mass_flow() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    bindings = resolve_candidate_bindings_by_id(
        FROZEN_ID, normalized, handoff, provider, max_valid=64
    )
    assert bindings is not None
    assert bindings.geometry_projection_hash == FROZEN_HASH
    report = run_autonomous_nozzle_full_path(bindings)
    assert len(report.ports) == 4
    assert report.nozzle_design_hash
    assert report.structural_geometry_hash == FROZEN_HASH
    assert report.nozzle_size_authority == "PARAMETRIC_CALCULATED"
    assert report.full_path_dp_authority == "ASSUMPTION_BASED"
    for port in report.ports:
        assert Decimal("0.999") <= port.velocity_m_s <= Decimal("3.001")
        expected_v = port.mass_flow_kg_s / (port.density_kg_m3 * port.effective_area_m2)
        assert abs(port.velocity_m_s - expected_v) < Decimal("1e-6")
    assert report.nozzle_velocity_check == "PASS"
    nozzle_report = assess_nozzle_velocities(bindings, provider, autonomous_ports=report.ports)
    assert nozzle_report.status == "VERIFIED"
    assert len(report.scenarios) == 3
    mid = next(s for s in report.scenarios if s.scenario_key == "mid_band")
    assert mid.hydraulic_check == "BLOCKED"
    assert mid.tube_modeled_side_dp_pa is not None
    assert Decimal(mid.tube_modeled_side_dp_pa) <= Decimal("1150")


def test_manufacturable_inventory_counts_without_expanding_space() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    inv = scan_manufacturable_full_path_inventory(
        normalized, handoff, provider=provider, max_candidates=64
    )
    assert inv.manufacturable_valid_count == 3
    assert inv.task174_hydraulic_feasible_count >= 1
    assert inv.full_path_hydraulic_feasible_count < 2
