"""Shared helpers for V08-03 live thermal rating tests (no production imports changed)."""

from __future__ import annotations

from pathlib import Path

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_general_user_case.loader import load_general_user_design_case_json
from prototypes.v08_general_user_case.pipeline import (
    V08UserCasePipelineResult,
    validate_and_build_solver_handoff,
)
from prototypes.v08_general_user_case.solver_handoff import V08SolverHandoffV1
from prototypes.v08_general_user_case.user_design_case import NormalizedUserDesignCase
from prototypes.v08_thermal_rating.pipeline import V08ThermalCandidateRatingRow

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests/fixtures/v08_user_case_no_geometry_task174_admissible.json"
FIXTURE_ALT = REPO_ROOT / "tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json"


def ready_handoff(path: Path) -> tuple[NormalizedUserDesignCase, V08SolverHandoffV1]:
    case = load_general_user_design_case_json(path.read_text(encoding="utf-8"))
    pipeline: V08UserCasePipelineResult = validate_and_build_solver_handoff(
        case, provider=CoolPropProvider()
    )
    return pipeline.normalized, pipeline.handoff


def assert_full_rating_row(row: V08ThermalCandidateRatingRow) -> None:
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
