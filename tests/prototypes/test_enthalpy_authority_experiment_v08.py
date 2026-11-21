"""Smoke tests for enthalpy authority experiment typing."""

from __future__ import annotations

from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)


def test_no_mesh_run_decision_b() -> None:
    out = evaluate_n4_authority_experiment(None, provider=object(), outer_status="PRECISION_FLOOR")
    assert out.numerical_decision == "B"
    assert out.terminal_gate == "BLOCKED"
