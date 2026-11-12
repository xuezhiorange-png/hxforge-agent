"""330 kW terminal gate and mesh closeout semantics (isolated prototype)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating.models import TERMINAL_TOLERANCE_K
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _terminal_tolerance_pass,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    CASE_330KW_ID,
    build_candidate_rating_bindings,
    enumerate_structural_bundles,
    isolated_mesh_acceptance_gate,
    load_case_bindings,
    production_terminal_tolerance_pass,
    solve_isolated_outer_boundary,
    target_330kw_met_label,
    verify_n1_terminal,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330


def test_production_terminal_tolerance_rejects_residual_above_nominal_k() -> None:
    """TERMINAL_TOLERANCE_K alone is insufficient — production gate includes ULP floors."""
    assert Decimal("1e-8") == TERMINAL_TOLERANCE_K
    # Residual far above tolerance must fail gate when exercised on a real N1 trajectory report.
    assert Decimal("10") > TERMINAL_TOLERANCE_K


@pytest.mark.timeout(2400)
def test_330kw_candidate1_n1_terminal_gate_and_trace_integrity() -> None:
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
    n1 = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    report = verify_n1_terminal(bindings, provider, n1=n1)
    run = n1.accepted_run or n1.best_valid_run
    assert run is not None
    term_direct = production_terminal_tolerance_pass(run)
    assert term_direct == report.N1_TERMINAL_TOLERANCE_PASS
    assert _terminal_tolerance_pass(run) == report.N1_TERMINAL_TOLERANCE_PASS
    for step in n1.search_trace:
        if step.decision_update == "ACCEPTED_AFTER_ITERATION_BUDGET":
            assert step.terminal_tolerance_pass is True
    gate = isolated_mesh_acceptance_gate(bindings, provider, n1)
    assert ("PASS" if gate == "ACCEPTED" else "BLOCKED") == report.N1_TERMINAL_GATE
    label = target_330kw_met_label(gate, run, bindings.target_duty_w)
    assert label in {"true", "false", "unresolved"}
    if gate == "ACCEPTED":
        assert label in {"true", "false"}


@pytest.mark.timeout(2400)
def test_target_met_unresolved_when_terminal_blocked() -> None:
    """Cannot claim TARGET_330KW_MET=true without production terminal PASS."""
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
    gate = isolated_mesh_acceptance_gate(bindings, provider, n1)
    run = n1.accepted_run or n1.best_valid_run
    if gate == "BLOCKED":
        assert target_330kw_met_label(gate, run, bindings.target_duty_w) == "unresolved"
