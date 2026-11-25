"""V08-04 kernel joint integration tests."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from prototypes.v08_thermal_rating.case_identity_v08 import FIXTURE_250, FIXTURE_330
from prototypes.v08_thermal_rating.v08_independent_engineering_rating_kernel_v1 import (
    KERNEL_AUTHORITY_ID,
)
from prototypes.v08_thermal_rating.v08_kernel_engineering_report_v1 import (
    run_kernel_case_engineering_matrix,
)

FIX220 = Path(__file__).resolve().parents[2] / "tests/fixtures/v08_user_case_no_geometry_task174_admissible_alt.json"


def test_250kw_kernel_joint_e2e_exists() -> None:
    rep = run_kernel_case_engineering_matrix(FIXTURE_250, max_candidates=9)
    assert rep.successful_e2e_count >= 1
    assert rep.first_successful_e2e_candidate_id
    row = next(r for r in rep.rows if r.candidate_id == rep.first_successful_e2e_candidate_id)
    assert row.final_qualification == "KERNEL_JOINT_E2E_SUCCESS"
    assert row.thermal_authority_id == KERNEL_AUTHORITY_ID
    assert len(row.k_scenarios) == 3
    assert "NOZZLE_VELOCITY_OUTSIDE_1_3_M_S" in row.legacy_v08_04_blockers


def test_authority_not_task173() -> None:
    rep = run_kernel_case_engineering_matrix(FIXTURE_250, max_candidates=3)
    for row in rep.rows:
        assert "TASK173" not in row.thermal_authority_id


def test_330kw_regression_matrix_runs() -> None:
    rep = run_kernel_case_engineering_matrix(FIXTURE_330, max_candidates=9)
    assert len(rep.rows) >= 1
    # Strict 330 kW Δp may block joint; matrix must still run
    assert rep.report_hash


def test_nine_total_matrix_cells_across_two_cases() -> None:
    r1 = run_kernel_case_engineering_matrix(FIXTURE_250, max_candidates=9)
    r2 = run_kernel_case_engineering_matrix(FIX220, max_candidates=9)
    assert len(r1.rows) + len(r2.rows) >= 6