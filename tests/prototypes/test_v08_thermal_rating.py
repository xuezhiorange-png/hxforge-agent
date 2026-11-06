"""V08-03 live thermal rating on enumerated geometry."""

from __future__ import annotations

from pathlib import Path

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import (
    V08UserCasePipelineResult,
    validate_and_build_solver_handoff,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/v08_user_case_no_geometry_task174_admissible.json"


def _ready_handoff() -> tuple[NormalizedUserDesignCase, V08SolverHandoffV1]:
    case = load_general_user_design_case_json(FIXTURE.read_text(encoding="utf-8"))
    pipeline: V08UserCasePipelineResult = validate_and_build_solver_handoff(
        case, provider=CoolPropProvider()
    )
    return pipeline.normalized, pipeline.handoff


@pytest.mark.timeout(7200)
def test_v08_03_rates_two_candidates_when_thermal_ready() -> None:
    """End-to-end V08-02 geometry → Task171/174 → Task173 rating attempt (thermal binding on).

    The R1 V08 discrete ladder can still yield ``TASK173_BLOCKED`` mesh outcomes; this test
    proves the bridge runs with the same mass flows and R23 thermal envelope as the solver handoff.
    """
    normalized, handoff = _ready_handoff()
    assert handoff.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    result = run_v08_thermal_rating(
        normalized,
        handoff,
        max_valid_geometry=2,
        provider=CoolPropProvider(),
    )
    assert result.blocked_reason in {None, "TASK173_BLOCKED"}, result.candidates_rated
    assert result.status in {"OK", "PARTIAL", "BLOCKED"}
    assert result.candidate_space_hash is not None
    assert result.task168_request_hash is not None
    assert len(result.candidates_rated) == 2
    for row in result.candidates_rated:
        assert row.task174_status == "VALIDATED"
        assert row.rating_request_hash is not None
        assert row.task173_result_hash is not None
        if row.rating_blocked_code is None:
            assert row.mesh_n1_status == "NUMERIC_VALID"
            assert row.total_duty_w is not None
            assert row.duty_vs_target is not None
            assert row.energy_balance_residual_w is not None


def test_v08_03_model_blocked_without_experimental_thermal_binding() -> None:
    normalized, handoff = _ready_handoff()
    # Hand-built: validated input only (no thermal binding document)
    handoff_only = handoff.model_copy(
        update={"downstream_readiness": "VALIDATED_INPUT_ONLY", "thermal_binding": None}
    )
    result = run_v08_thermal_rating(normalized, handoff_only, max_valid_geometry=1)
    assert result.status == "BLOCKED"
    assert result.blocked_reason == "MODEL_BLOCKED_THERMAL_BINDING"
    assert not result.candidates_rated
