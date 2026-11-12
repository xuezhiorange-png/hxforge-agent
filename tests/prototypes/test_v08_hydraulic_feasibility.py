"""Task174 hydraulic screen for V08-03 (no design-space expansion)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    isolated_mesh_acceptance_gate,
    load_case_bindings,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.hydraulic_feasibility_v08 import (
    run_hydraulic_feasibility_screen,
    screen_task174_hydraulic_row,
)


def test_hydraulic_screen_candidate1_shell_dp_exceeds_limit() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    assert normalized.engineering_case_id == CASE_330KW_ID
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    bindings = build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom[bundles[0].candidate.candidate_id],
    )
    assert bindings is not None
    row = screen_task174_hydraulic_row(bindings)
    assert row.tube_dp_pass is True
    assert row.shell_dp_pass is False
    assert row.hydraulic_pass is False
    assert row.shell_dp_pa > Decimal("1180")
    assert row.tube_dp_pa < Decimal("1150")
    assert row.nozzle_velocity_status == "not_in_task174_chain"


@pytest.mark.timeout(600)
def test_hydraulic_feasibility_screen_enumerates_without_expanding_limits() -> None:
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    report = run_hydraulic_feasibility_screen(
        normalized, handoff, provider=provider, max_candidates=8
    )
    assert report.candidates_screened >= 1
    assert report.case_id == CASE_330KW_ID
    for row in report.rows:
        assert row.tube_dp_limit_pa == normalized.max_tube_side_pressure_drop_pa
        assert row.shell_dp_limit_pa == normalized.max_shell_side_pressure_drop_pa


@pytest.mark.timeout(2400)
def test_isolated_gate_rejects_best_valid_without_outer_accepted() -> None:
    """ACCEPTED gate requires result.status ACCEPTED and accepted_run — not best_valid_run."""
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    space_hash, t168_digest, bundles, geom = enumerate_structural_bundles(
        normalized, handoff, max_valid=1
    )
    bindings = build_candidate_rating_bindings(
        bundles[0],
        space_hash=space_hash,
        t168_digest=t168_digest,
        normalized=normalized,
        handoff=handoff,
        provider=provider,
        geometry_projection_hash=geom[bundles[0].candidate.candidate_id],
    )
    assert bindings is not None
    n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    if n1.status != "ACCEPTED":
        assert isolated_mesh_acceptance_gate(bindings, provider, n1) == "BLOCKED"
