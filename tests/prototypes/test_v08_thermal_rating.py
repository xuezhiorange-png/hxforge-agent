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
from prototypes.v08_thermal_rating.pipeline import (
    V08ThermalCandidateRatingRow,
    run_v08_thermal_rating,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/v08_user_case_no_geometry_task174_admissible.json"
FIXTURE_ALT = REPO_ROOT / "tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json"


def _ready_handoff(path: Path) -> tuple[NormalizedUserDesignCase, V08SolverHandoffV1]:
    case = load_general_user_design_case_json(path.read_text(encoding="utf-8"))
    pipeline: V08UserCasePipelineResult = validate_and_build_solver_handoff(
        case, provider=CoolPropProvider()
    )
    return pipeline.normalized, pipeline.handoff


def _assert_full_rating_row(row: V08ThermalCandidateRatingRow) -> None:
    assert row.task174_status == "VALIDATED"
    assert row.rating_request_hash is not None
    assert row.task173_result_hash is not None
    assert row.rating_request_replay_ok is True
    assert row.mesh_n1_status == "NUMERIC_VALID"
    assert row.mesh_n2_status == "NUMERIC_VALID"
    assert row.mesh_n4_status == "NUMERIC_VALID"
    assert row.mesh_convergence_n1_n2_n4 == "PASS"
    assert row.energy_balance_status == "PASS"
    assert row.total_duty_w is not None
    assert row.tube_outlet_temperature_k is not None
    assert row.shell_outlet_temperature_k is not None
    assert row.duty_vs_target is not None
    assert row.energy_balance_residual_w is not None


@pytest.mark.timeout(7200)
def test_v08_03_closeout_engineering_acceptance_or_engineering_blocked() -> None:
    """Two distinct V08-02 geometries: full rating or fail-closed with Task173 evidence."""
    normalized, handoff = _ready_handoff(FIXTURE)
    assert handoff.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    result = run_v08_thermal_rating(
        normalized,
        handoff,
        provider=CoolPropProvider(),
    )
    assert result.task_id == "V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT"
    assert result.distinct_structural_geometries_attempted >= 2

    if result.engineering_acceptance == "PASS":
        assert result.status in {"OK", "PARTIAL"}
        assert result.blocked_reason is None
        assert result.distinct_fully_converged_rating_count >= 2
        success_rows = [
            r
            for r in result.candidates_rated
            if r.rating_outcome == "RATING_SUCCESS"
            and r.rating_request_replay_ok is True
            and r.mesh_convergence_n1_n2_n4 == "PASS"
            and r.energy_balance_status == "PASS"
        ]
        hashes = {r.geometry_projection_hash for r in success_rows if r.geometry_projection_hash}
        assert len(hashes) >= 2, success_rows
        for row in success_rows:
            _assert_full_rating_row(row)
    else:
        assert result.engineering_acceptance == "BLOCKED"
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "ENGINEERING_ACCEPTANCE_RATING"
        assert result.distinct_fully_converged_rating_count < 2
        assert result.engineering_acceptance_blockers, result.candidates_rated
        assert "INSUFFICIENT_DISTINCT_SUCCESSFUL_RATINGS" in str(
            result.engineering_acceptance_blockers
        )
        assert result.model_blockers, "expected Task173 failure codes when rating does not close"
        for row in result.candidates_rated:
            if row.rating_outcome == "RATING_BLOCKED":
                assert row.rating_blocked_code is not None


@pytest.mark.timeout(7200)
def test_v08_03_independent_case_input_delta() -> None:
    """Non-reference case: target duty and tube inlet differ; handoff carries thermal binding."""
    n1, h1 = _ready_handoff(FIXTURE)
    n2, h2 = _ready_handoff(FIXTURE_ALT)
    assert h1.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    assert h2.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    assert n1.target_duty_w != n2.target_duty_w
    assert n1.tube_side.inlet_temperature_k != n2.tube_side.inlet_temperature_k
    assert h1.normalized_input_hash != h2.normalized_input_hash
    tb1 = h1.thermal_binding or {}
    tb2 = h2.thermal_binding or {}
    assert tb1.get("tube_inlet_temperature_k") != tb2.get("tube_inlet_temperature_k")

    r2 = run_v08_thermal_rating(n2, h2, provider=CoolPropProvider())
    assert str(n2.target_duty_w) == r2.target_duty_w
    if r2.engineering_acceptance == "PASS":
        assert r2.distinct_fully_converged_rating_count >= 2
        for row in r2.candidates_rated:
            if row.rating_outcome == "RATING_SUCCESS" and row.mesh_convergence_n1_n2_n4 == "PASS":
                _assert_full_rating_row(row)
    else:
        assert r2.blocked_reason == "ENGINEERING_ACCEPTANCE_RATING"
        assert r2.model_blockers


def test_v08_03_model_blocked_without_experimental_thermal_binding() -> None:
    normalized, handoff = _ready_handoff(FIXTURE)
    handoff_only = handoff.model_copy(
        update={"downstream_readiness": "VALIDATED_INPUT_ONLY", "thermal_binding": None}
    )
    result = run_v08_thermal_rating(normalized, handoff_only, max_valid_geometry=1)
    assert result.status == "BLOCKED"
    assert result.blocked_reason == "MODEL_BLOCKED_THERMAL_BINDING"
    assert result.engineering_acceptance == "BLOCKED"
    assert not result.candidates_rated
