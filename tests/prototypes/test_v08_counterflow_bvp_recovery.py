"""Unit checks for fixed-inlet BVP recovery helpers."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import numpy as np

from prototypes.v08_thermal_rating.counterflow_fixed_inlet_bvp_recovery_v08 import (
    build_n4_q_seed_from_n2_shooting_intervals,
)
from prototypes.v08_thermal_rating.mesh_level_diagnostics_v08 import (
    IsolatedMeshLevelDiagnostic,
    experimental_mesh_convergence_pass,
)


def test_n4_q_seed_splits_interval_duty_not_cell_copy() -> None:
    ctx = SimpleNamespace(interval_count=3)
    duties = (Decimal("30000"), Decimal("60000"), Decimal("90000"))
    q = build_n4_q_seed_from_n2_shooting_intervals(
        candidate_ctx=ctx,
        n2_interval_duty_w=duties,
        n4_subdivisions=4,
    )
    assert q.shape == (12,)
    assert np.isclose(q[0:4].sum(), 30000.0)
    assert np.isclose(q[4:8].sum(), 60000.0)
    assert np.allclose(q[0:4], 7500.0)


def _diag(duty: str, gate: str, roundoff: str = "0.01") -> IsolatedMeshLevelDiagnostic:
    obs = SimpleNamespace(total_duty_w=Decimal(duty), duty_roundoff_floor_w=Decimal(roundoff))
    run = SimpleNamespace(observables=obs)
    outer = SimpleNamespace(accepted_run=run)
    return IsolatedMeshLevelDiagnostic(
        subdivisions=1,
        gate=gate,
        N_OUTER_STATUS="ACCEPTED",
        N_FAILURE_CODE=None,
        N_FAILURE_DIAGNOSTICS=(),
        N_FIRST_FAILED_CELL=None,
        N_FIRST_FAILED_EQUATION=None,
        N_TERMINAL_RESIDUAL_K=None,
        N_TERMINAL_RESIDUAL_J_KG=None,
        N_TASK172_HOLES=0,
        N_SEARCH_TRACE=(),
        N_SHOOTING_BRACKET=None,
        N_ITERATIONS=0,
        N_RUN_HASH=None,
        N_SHOOTING_ENTHALPY_J_KG=None,
        outer_result=outer,
    )


def test_experimental_mesh_convergence_uses_energy_floor_not_two_percent() -> None:
    n1 = _diag("395000.0", "ACCEPTED", roundoff="0.5")
    n2 = _diag("395000.2", "ACCEPTED", roundoff="0.5")
    n4 = _diag("395000.4", "ACCEPTED", roundoff="0.5")
    ok, notes = experimental_mesh_convergence_pass(n1, n2, n4)
    assert ok is True
    assert any("NOT_PRODUCTION_TASK173_MESH_CONVERGENCE" in n for n in notes)
    assert not any("2PCT" in n for n in notes)
