"""Smoke test: coupled mesh march completes for Candidate B n=1."""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.models import (
    H_MAX_J_KG,
    H_MIN_J_KG,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_fast_solver_architecture_r1.benchmark import _load_candidate_b_context
from prototypes.v07_fast_solver_architecture_r1.mesh_march import fast_valid_trajectory


def test_fast_mesh_march_n1_nonzero_duty() -> None:
    _load_candidate_b_context()
    _, context = _load_candidate_b_context()
    token = t173._CANDIDATE_RATING_CONTEXT.set(context)
    shooting = H_MIN_J_KG + (H_MAX_J_KG - H_MIN_J_KG) * Decimal("0.5")
    provider = CoolPropProvider(cache_size=512)
    try:
        run, stats = fast_valid_trajectory(1, shooting, provider, context.shell_authority, 0)
    finally:
        t173._CANDIDATE_RATING_CONTEXT.reset(token)
    assert stats.cell_count == 5
    assert run.observables.total_duty_w > 0
