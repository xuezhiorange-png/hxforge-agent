"""Smoke tests for enthalpy authority experiment typing."""

from __future__ import annotations

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.axial_rating_engine_v1 import (
    load_case_bindings,
    resolve_candidate_bindings_by_id,
)
from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_330
from prototypes.v08_thermal_rating.enthalpy_authority_experiment_v08 import (
    evaluate_n4_authority_experiment,
)

FROZEN_CANDIDATE_ID = "9277ebb8-5b05-5130-8b90-92ee4768606b"


@pytest.fixture
def bindings_330():
    provider = CoolPropProvider()
    normalized, handoff, _ = load_case_bindings(FIXTURE_330, provider=provider)
    row = resolve_candidate_bindings_by_id(
        FROZEN_CANDIDATE_ID, normalized, handoff, provider, max_valid=64
    )
    assert row is not None
    return row, provider


def test_no_mesh_run_decision_b(bindings_330) -> None:
    bindings, provider = bindings_330
    out = evaluate_n4_authority_experiment(
        None, bindings=bindings, provider=provider, outer_status="PRECISION_FLOOR"
    )
    assert out.numerical_decision == "B"
    assert out.terminal_gate == "BLOCKED"
    assert out.enthalpy_propagation_defect_confirmed == "unresolved"
