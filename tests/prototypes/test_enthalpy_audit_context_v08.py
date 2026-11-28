"""Regression: 330 kW thermal boundary must be active for Task173 enthalpy audit."""

from __future__ import annotations

from decimal import Decimal

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    active_experimental_thermal_boundary,
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
    solve_isolated_outer_boundary,
)
from prototypes.v08_thermal_rating.case_identity_v08 import CASE_330KW_ID, FIXTURE_330
from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import (
    AUDIT_SHELL_INLET_K,
    AUDIT_TUBE_INLET_K,
    inlet_terminal_invariant,
    verify_audit_thermal_context,
)
from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"


@pytest.fixture(scope="module")
def bindings_330():
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    row = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert row is not None
    return row, provider


def test_verify_context_missing_without_binding(bindings_330) -> None:
    bindings, _provider = bindings_330
    assert active_experimental_thermal_boundary() is None
    snap = verify_audit_thermal_context(bindings)
    assert snap.status == "AUDIT_CONTEXT_MISSING"


def test_default_298_boundary_invalid_for_330kw(bindings_330) -> None:
    bindings, provider = bindings_330
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=Decimal("300"),
        shell_inlet_temperature_k=Decimal("298.15"),
        tube_mass_flow_kg_s=Decimal("12"),
        shell_mass_flow_kg_s=Decimal("20"),
        tube_property_evaluation_pressure_pa=bindings.normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=bindings.normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    token = bind_experimental_thermal_boundary_v1(exp)
    try:
        snap = verify_audit_thermal_context(bindings)
        assert snap.status == "AUDIT_CONTEXT_INVALID"
        assert "frozen_default_boundary_300_29815_active_on_330kw_case" in snap.notes
    finally:
        reset_experimental_thermal_boundary(token)
    assert active_experimental_thermal_boundary() is None


def test_n4_audit_context_lifecycle_and_invariant_b(bindings_330) -> None:
    bindings, provider = bindings_330
    iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    run = iso.accepted_run or iso.best_valid_run
    assert run is not None
    assert active_experimental_thermal_boundary() is None

    out = evaluate_n4_authority_experiment(
        run,
        bindings=bindings,
        provider=provider,
        outer_status=iso.status,
    )
    assert active_experimental_thermal_boundary() is None
    assert out.context.status == "VALID"
    assert out.context.audit_case_id == CASE_330KW_ID
    assert out.inlet_invariant is not None
    assert out.inlet_invariant.invariant_match == "PASS"
    assert (
        out.inlet_invariant.inlet_face_minus_authority_j_kg
        == out.inlet_invariant.production_terminal_residual_j_kg
    )
    assert Decimal(out.context.audit_shell_inlet_k or "0") == AUDIT_SHELL_INLET_K
    assert Decimal(out.context.audit_tube_inlet_k or "0") == AUDIT_TUBE_INLET_K


def test_invariant_b_on_mesh_run(bindings_330) -> None:
    bindings, provider = bindings_330
    from prototypes.v08_thermal_rating.enthalpy_audit_context_v08 import run_enthalpy_audit_body

    iso = solve_isolated_outer_boundary(bindings, provider, subdivisions=1)
    run = iso.accepted_run or iso.best_valid_run
    assert run is not None

    def body(_c: object, _t: object) -> object:
        return inlet_terminal_invariant(run)

    inv = run_enthalpy_audit_body(bindings, provider, subdivisions=run.subdivisions, body=body)
    assert inv.invariant_match == "PASS"
