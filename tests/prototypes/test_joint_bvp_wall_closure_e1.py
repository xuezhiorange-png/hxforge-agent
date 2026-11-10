"""Real-property checks for joint BVP wall-closure path (e1, isolated cells)."""

from __future__ import annotations

import pytest

from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _CANDIDATE_RATING_CONTEXT,
    _attempt_enthalpy_coupled_direct_trf_root,
    _build_candidate_local_support,
    _candidate_context,
    _state_at_inlet,
    _state_from_enthalpy,
    effective_shell_cold_inlet_enthalpy_j_kg,
    effective_shell_mass_flow_kg_s,
    effective_tube_inlet_temperature_k,
    effective_tube_mass_flow_kg_s,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.export_v08_03_blocked_cell_evidence import (
    _enumerate_for_fixture,
    _find_bundle,
)
from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    _per_cell_thermodynamic_q_cap_w,
    _resistance_network_q_u_seed,
    build_axial_enthalpies_from_q,
)
from prototypes.v08_thermal_rating.run_joint_bvp_proof import (
    CANDIDATES,
    _build_rating_request,
)
from prototypes.v08_thermal_rating.true_three_equation_cell_coupling import (
    build_closure_primitives,
    build_task172_request_for_q,
)


@pytest.mark.timeout(120)
def test_e1_cell0_resistance_seed_in_property_domain() -> None:
    provider = CoolPropProvider()
    normalized, _, enum, digest = _enumerate_for_fixture()
    _find_bundle(enum, CANDIDATES[0])
    ctx_rating = _build_rating_request(CANDIDATES[0], enum, digest)
    exp = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=normalized.tube_side.inlet_temperature_k,
        shell_inlet_temperature_k=normalized.shell_side.inlet_temperature_k,
        tube_mass_flow_kg_s=normalized.tube_side.mass_flow_kg_s,
        shell_mass_flow_kg_s=normalized.shell_side.mass_flow_kg_s,
        tube_property_evaluation_pressure_pa=normalized.tube_side.inlet_pressure_pa,
        shell_property_evaluation_pressure_pa=normalized.shell_side.inlet_pressure_pa,
        allow_live_variable_tube_mass_flow=True,
        allow_live_variable_shell_mass_flow=True,
        allow_variable_water_temperature=True,
    )
    tok = bind_experimental_thermal_boundary_v1(exp)
    ctx = _candidate_context(ctx_rating)
    ct = _CANDIDATE_RATING_CONTEXT.set(ctx)
    try:
        support = _build_candidate_local_support(ctx, 0, 1, 0)
        mt = float(effective_tube_mass_flow_kg_s())
        ms = float(effective_shell_mass_flow_kg_s())
        h_t0 = float(
            _state_at_inlet(
                provider, effective_tube_inlet_temperature_k(), side="TUBE"
            ).native.enthalpy_j_kg
        )
        h_sN = float(effective_shell_cold_inlet_enthalpy_j_kg())
        q0 = 80_000.0
        h_t, h_s = build_axial_enthalpies_from_q(
            [q0] * 5,
            h_t_inlet_j_kg=h_t0,
            h_s_cold_inlet_j_kg=h_sN,
            tube_mass_flow_kg_s=mt,
            shell_mass_flow_kg_s=ms,
        )
        tube_up = _state_from_enthalpy(provider, float(h_t[0]), side="TUBE")
        shell_left = _state_from_enthalpy(
            provider, float(h_s[0]), shell_search_state=True, side="SHELL"
        )
        q_cap = _per_cell_thermodynamic_q_cap_w(
            h_t_face_j_kg=float(h_t[0]),
            h_s_face_j_kg=float(h_s[0]),
            tube_mdot=mt,
            shell_mdot=ms,
        )
        seed = _resistance_network_q_u_seed(
            q_cap_w=q_cap,
            q_guess=q0,
            support=support,
            tube_up=tube_up,
            shell_left=shell_left,
            provider=provider,
            shell_authority=ctx.shell_authority,
        )
        assert seed is not None
        q_i, u1, u2 = seed
        request, _, _ = build_task172_request_for_q(
            q_i,
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=ctx.shell_authority,
        )
        prim = build_closure_primitives(request, provider)
        assert float(prim.tube_h_base) > 0.0
        assert shell_left.native.temperature_k < tube_up.native.temperature_k
        assert 0.0 <= u1 <= 1.0 and 0.0 <= u2 <= 1.0
        coupled = _attempt_enthalpy_coupled_direct_trf_root(
            support=support,
            tube_upstream=tube_up,
            shell_physical_left=shell_left,
            provider=provider,
            shell_authority=ctx.shell_authority,
            q_upper=q_cap,
            q_seed=q_i,
        )
        assert coupled is None, (
            "uniform-q axial guess is not a production closure state; coupled TRF must fail here"
        )
    finally:
        _CANDIDATE_RATING_CONTEXT.reset(ct)
        reset_experimental_thermal_boundary(tok)
