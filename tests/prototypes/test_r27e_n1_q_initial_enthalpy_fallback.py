"""R27E: N1 Q initial guess falls back when conductance-weighted seed violates enthalpy."""

from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime.models import CandidateTask172LocalRequest
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.candidate_selection import (
    enumerate_experimental_rating_candidates,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_core import (
    ENGINEERING_NUMERIC_VALID,
    _build_global_cell_grid,
    _conductance_weighted_q_guess,
    _enthalpy_j_kg,
    _initial_q_guess,
    _q_vector_in_admitted_enthalpy_domain,
    _resolve_n1_q_initial,
    run_experimental_engineering_rating,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    native_thermal_boundary_session,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context
from tests.prototypes.r26g_r26ga_shared_setup import shared_r26e_engineering_case


@pytest.mark.slow
def test_r27e_n1_enthalpy_blocked_reference_candidates_converge_after_q_fallback() -> None:
    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    for prefix in ("9c4b84db", "7357afdf"):
        cid = next(c for c in sel.selected_candidate_ids if c.startswith(prefix))
        native = build_native_cell_context(case, selection=sel, candidate_id=cid)
        n1 = run_experimental_engineering_rating(case, subdivisions=1, native=native)
        assert n1.status == ENGINEERING_NUMERIC_VALID, (prefix, n1.failure_code, n1.diagnostics)


def test_r27e_conductance_q_guess_can_violate_enthalpy_while_legacy_initial_is_admitted() -> None:
    """A/B: conductance seed invalid at first residual; legacy uniform seed is admitted."""
    case = shared_r26e_engineering_case()
    sel = enumerate_experimental_rating_candidates(
        case, rating_selection_policy="r27d", rate_all_distinct_task174_ready=True
    )
    provider = CoolPropProvider()
    cid = next(c for c in sel.selected_candidate_ids if c.startswith("9c4b84db"))
    native = build_native_cell_context(case, selection=sel, candidate_id=cid)
    with native_thermal_boundary_session(case, provider, enable_live_binding=True):
        grid, _ = _build_global_cell_grid(native.context, subdivisions=1)
        n = len(grid)
        token = t173._CANDIDATE_RATING_CONTEXT.set(native.context)
        try:
            m_tube = float(t173.effective_tube_mass_flow_kg_s())
            m_shell = float(t173.effective_shell_mass_flow_kg_s())
            tube_t, shell_t = 310.0, 295.0
            h_t_in = _enthalpy_j_kg(provider, tube_t, 101325.0)
            h_s_in = _enthalpy_j_kg(provider, shell_t, 101325.0)
            ref_support = grid[0].support
            tube_state0 = t173._state_from_enthalpy(provider, Decimal(str(h_t_in)), side="TUBE")
            shell_staten = t173._state_from_enthalpy(provider, Decimal(str(h_s_in)), side="SHELL")
            base_request = t173._task172_request(
                ref_support, tube_state0, shell_staten, native.shell_authority
            )
            assert isinstance(base_request, CandidateTask172LocalRequest)
            q_cond = _conductance_weighted_q_guess(
                grid=grid,
                provider=provider,
                base_request=base_request,
                tube_inlet_t_k=tube_t,
                shell_inlet_t_k=shell_t,
                m_tube=m_tube,
                h_t_in=h_t_in,
                h_s_in=h_s_in,
            )
            q_legacy = _initial_q_guess(
                n,
                h_t_in=h_t_in,
                h_s_in=h_s_in,
                m_tube=m_tube,
                delta_t_in=abs(tube_t - shell_t),
                q_seed=None,
            )
            assert not _q_vector_in_admitted_enthalpy_domain(
                q_cond,
                provider=provider,
                h_t_in=h_t_in,
                h_s_in=h_s_in,
                m_tube=m_tube,
                m_shell=m_shell,
            )
            assert _q_vector_in_admitted_enthalpy_domain(
                q_legacy,
                provider=provider,
                h_t_in=h_t_in,
                h_s_in=h_s_in,
                m_tube=m_tube,
                m_shell=m_shell,
            )
            q_resolved = _resolve_n1_q_initial(
                n,
                provider=provider,
                grid=grid,
                base_request=base_request,
                tube_inlet_t_k=tube_t,
                shell_inlet_t_k=shell_t,
                m_tube=m_tube,
                m_shell=m_shell,
                h_t_in=h_t_in,
                h_s_in=h_s_in,
                q_initial=None,
            )
            assert np.allclose(q_resolved, q_legacy)
        finally:
            t173._CANDIDATE_RATING_CONTEXT.reset(token)
