"""Outer shooting binary64 enthalpy refine when Decimal bisection collapses."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _MeshRun,
    _outer_shooting_float_refine_valid_high,
    _OuterTrial,
)


def _run(residual_k: Decimal) -> _MeshRun:
    return SimpleNamespace(  # type: ignore[return-value]
        observables=SimpleNamespace(
            terminal_boundary_residual_k=residual_k,
            terminal_boundary_residual_j_kg=Decimal("0"),
        ),
        faces_shell=[SimpleNamespace(property_snapshot=SimpleNamespace(cp_j_kg_k=4180.0))],
    )


def test_outer_float_refine_returns_improving_valid_trial() -> None:
    h_low = Decimal("120000")
    h_high = Decimal("122022.67196814526")
    best = _run(Decimal("3.5e-8"))

    def trial_at(enthalpy: Decimal, iteration: int) -> _OuterTrial:
        # Lower enthalpy probe improves terminal residual below tolerance.
        residual = Decimal("5e-9") if enthalpy < h_high else Decimal("3.5e-8")
        return _OuterTrial("VALID_TRAJECTORY", enthalpy, mesh_run=_run(residual))

    refined = _outer_shooting_float_refine_valid_high(h_low, h_high, best, trial_at, 44)
    assert refined is not None
    assert refined.observables.terminal_boundary_residual_k == Decimal("5e-9")
