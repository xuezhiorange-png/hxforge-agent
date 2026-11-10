from __future__ import annotations

import numpy as np
import pytest

from prototypes.v08_thermal_rating.joint_boundary_value_axial_solver import (
    axial_energy_slack_w,
    build_axial_enthalpies_from_q,
    solve_joint_boundary_value_mesh,
)


def test_solver_module_exposes_entrypoint() -> None:
    assert callable(solve_joint_boundary_value_mesh)


@pytest.mark.parametrize("n_cells", [1, 2, 5])
def test_enthalpy_construction_exact_energy_balance(n_cells: int) -> None:
    mt = 2.5
    ms = 3.1
    h_t0 = 200_000.0
    h_sN = 100_000.0
    q = np.linspace(50_000.0, 50_000.0 + 1000.0 * (n_cells - 1), n_cells)
    h_t, h_s = build_axial_enthalpies_from_q(
        q,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=mt,
        shell_mass_flow_kg_s=ms,
    )
    assert h_t.shape == (n_cells + 1,)
    assert h_s.shape == (n_cells + 1,)
    assert h_t[0] == pytest.approx(h_t0)
    assert h_s[-1] == pytest.approx(h_sN)
    for i in range(n_cells):
        assert h_t[i + 1] == pytest.approx(h_t[i] - q[i] / mt)
        assert h_s[i] == pytest.approx(h_s[i + 1] + q[i] / ms)
    _, tube_loss, shell_gain, slack = axial_energy_slack_w(
        q,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=mt,
        shell_mass_flow_kg_s=ms,
    )
    assert slack == pytest.approx(0.0, abs=1e-6)
    assert tube_loss == pytest.approx(shell_gain)
    assert tube_loss == pytest.approx(float(np.sum(q)))


def test_two_cell_countercurrent_face_continuity() -> None:
    q = np.asarray([40_000.0, 60_000.0])
    h_t, h_s = build_axial_enthalpies_from_q(
        q,
        h_t_inlet_j_kg=190_000.0,
        h_s_cold_inlet_j_kg=92_000.0,
        tube_mass_flow_kg_s=1.0,
        shell_mass_flow_kg_s=1.0,
    )
    assert h_s[2] - h_s[1] + q[1] == pytest.approx(0.0)
    assert h_t[0] - h_t[1] - q[0] == pytest.approx(0.0)
    assert h_t[1] > h_t[2]
    assert h_s[0] > h_s[2]


def test_five_cell_total_heat_equals_enthalpy_change() -> None:
    n = 5
    q = np.full(n, 75_000.0)
    mt = 1.7
    ms = 2.3
    h_t0 = 210_000.0
    h_sN = 88_000.0
    q_sum, tube_loss, shell_gain, slack = axial_energy_slack_w(
        q,
        h_t_inlet_j_kg=h_t0,
        h_s_cold_inlet_j_kg=h_sN,
        tube_mass_flow_kg_s=mt,
        shell_mass_flow_kg_s=ms,
    )
    assert slack < 1e-9
    assert q_sum == pytest.approx(n * 75_000.0)
    assert tube_loss == pytest.approx(shell_gain)
    assert tube_loss == pytest.approx(q_sum)


def test_build_enthalpy_rejects_nonpositive_mdot() -> None:
    with pytest.raises(ValueError):
        build_axial_enthalpies_from_q(
            [1.0],
            h_t_inlet_j_kg=1.0,
            h_s_cold_inlet_j_kg=1.0,
            tube_mass_flow_kg_s=0.0,
            shell_mass_flow_kg_s=1.0,
        )


def test_empty_mesh_returns_blocked_outcome() -> None:
    class _Ctx:
        interval_count = 0

    out = solve_joint_boundary_value_mesh(
        subdivisions=1,
        provider=object(),
        shell_authority=object(),
        candidate_ctx=_Ctx(),
    )
    assert out.status == "BLOCKED"
    assert out.energy_conserving_formulation is True
