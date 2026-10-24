"""R22/R22A: two-way bulk pressure feedback, Task172 binding, and sizing eligibility."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2
from prototypes.v07_general_rating_sizing_mvp.engineering_sizing_eligibility import (
    assess_engineering_sizing_eligibility,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    constraint_satisfied_ids,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_two_way_bulk_pressure_feedback import (
    iteration_satisfies_convergence_gates,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R21_E2E = REPO_ROOT / "tests/fixtures/r21_engineering_local_loss_n1_case.json"
_R22_E2E = REPO_ROOT / "tests/fixtures/r22_two_way_bulk_pressure_n1_case.json"
_R16 = REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json"


def test_two_way_flag_requires_live_postpass() -> None:
    case = load_general_engineering_case_json(_R16.read_text(encoding="utf-8"))
    payload = case.model_dump()
    payload["experimental_two_way_bulk_pressure_feedback"] = True
    payload["experimental_live_thermal_hydraulic_postpass"] = False
    with pytest.raises(ValueError, match="experimental_two_way_bulk_pressure_feedback"):
        GeneralEngineeringCaseV2.model_validate(payload)


def test_r21_demo_not_engineering_sizing_eligible() -> None:
    case = load_general_engineering_case_json(_R21_E2E.read_text(encoding="utf-8"))
    row = {
        "mesh_status": "NUMERIC_VALID",
        "live_thermal_state_hydraulic_postpass": {
            "tube_local_loss_engineering": {
                "engineering_geometry_completeness": "ENTRANCE_ONLY_ASSUMED",
                "assumed_geometry_status": "EXPERIMENTAL_ASSUMED_GEOMETRY_ONLY",
            }
        },
    }
    doc = assess_engineering_sizing_eligibility(case, row)
    assert doc["ENGINEERING_SIZING_ELIGIBILITY"] == (
        "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )
    assert any("ENTRANCE_ONLY" in reason for reason in doc["ineligibility_reasons"])


def test_constraint_satisfied_excludes_incomplete_geometry() -> None:
    case = load_general_engineering_case_json(_R21_E2E.read_text(encoding="utf-8"))
    eligibility = [
        {
            "candidate_id": "c1",
            "CONSTRAINT_STATUS": "PRELIMINARY_CONSTRAINT_SATISFIED",
            "engineering_sizing_eligibility": assess_engineering_sizing_eligibility(
                case,
                {
                    "live_thermal_state_hydraulic_postpass": {
                        "tube_local_loss_engineering": {
                            "engineering_geometry_completeness": "ENTRANCE_ONLY_ASSUMED",
                            "assumed_geometry_status": "EXPERIMENTAL_ASSUMED_GEOMETRY_ONLY",
                        }
                    }
                },
            ),
        }
    ]
    assert constraint_satisfied_ids(eligibility) == []


def test_convergence_gates_require_bulk_pressure_fixed_point() -> None:
    mesh = {
        "status": "NUMERIC_VALID",
        "total_duty_w": "1000",
        "energy_balance_residual_w": "0",
    }
    postpass = {
        "hydraulic_constraint_status": "SATISFIED",
        "tube_hydraulic_recompute_status": "EXPERIMENTAL_TRANSITIONAL_SUCCESS",
        "shell_hydraulic_recompute_status": "SUCCESS",
        "task174_style_outlet_pressure_window_pass": True,
        "recalculated_tube_dp_pa": "100",
        "recalculated_shell_dp_pa": "200",
        "tube_outlet_pressure_pa": "101200",
        "shell_outlet_pressure_pa": "101150",
    }
    obs = [
        {
            "task173_tube_thermo_pressure_pa": "101262.5",
            "task172_tube_local_pressure_pa": "101262.5",
            "task173_tube_property_evaluation_pressure_pa": "101262.5",
            "task173_shell_thermo_pressure_pa": "101237.5",
            "task172_shell_local_pressure_pa": "101237.5",
            "task173_shell_property_evaluation_pressure_pa": "101237.5",
        }
    ]
    ok, status, _ = iteration_satisfies_convergence_gates(
        mesh_row=mesh,
        postpass=postpass,
        tube_bulk_pa=Decimal("101262.5"),
        shell_bulk_pa=Decimal("101237.5"),
        inlet_pa=Decimal("101325"),
        prev_duty=Decimal("1000"),
        prev_tube_dp=Decimal("100"),
        prev_shell_dp=Decimal("200"),
        task172_observations=obs,
    )
    assert ok
    assert status == "COUPLED_FIXED_POINT_SATISFIED"

    ok2, status2, _ = iteration_satisfies_convergence_gates(
        mesh_row=mesh,
        postpass=postpass,
        tube_bulk_pa=Decimal("101325"),
        shell_bulk_pa=Decimal("101325"),
        inlet_pa=Decimal("101325"),
        prev_duty=Decimal("1000"),
        prev_tube_dp=Decimal("100"),
        prev_shell_dp=Decimal("200"),
        task172_observations=obs,
    )
    assert not ok2
    assert status2 == "BULK_PRESSURE_FIXED_POINT_NOT_SATISFIED"


def test_convergence_gates_reject_mismatched_task172_pressure() -> None:
    mesh = {"status": "NUMERIC_VALID", "total_duty_w": "1000", "energy_balance_residual_w": "0"}
    postpass = {
        "hydraulic_constraint_status": "SATISFIED",
        "tube_hydraulic_recompute_status": "SUCCESS",
        "shell_hydraulic_recompute_status": "SUCCESS",
        "task174_style_outlet_pressure_window_pass": True,
        "recalculated_tube_dp_pa": "100",
        "recalculated_shell_dp_pa": "200",
        "tube_outlet_pressure_pa": "101200",
        "shell_outlet_pressure_pa": "101150",
    }
    obs = [
        {
            "task173_tube_thermo_pressure_pa": "101262.5",
            "task172_tube_local_pressure_pa": "101325",
            "task173_tube_property_evaluation_pressure_pa": "101262.5",
            "task173_shell_thermo_pressure_pa": "101237.5",
            "task172_shell_local_pressure_pa": "101237.5",
            "task173_shell_property_evaluation_pressure_pa": "101237.5",
        }
    ]
    ok, status, _ = iteration_satisfies_convergence_gates(
        mesh_row=mesh,
        postpass=postpass,
        tube_bulk_pa=Decimal("101262.5"),
        shell_bulk_pa=Decimal("101237.5"),
        inlet_pa=Decimal("101325"),
        prev_duty=Decimal("999"),
        prev_tube_dp=Decimal("100"),
        prev_shell_dp=Decimal("200"),
        task172_observations=obs,
    )
    assert not ok
    assert status == "TASK172_PRESSURE_BINDING_FAILED"


@pytest.mark.timeout(3600)
def test_r22_two_way_e2e_cli_with_task172_pressure_binding() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(_R22_E2E),
                "--output",
                str(out),
                "--mode",
                "experimental-live-rating",
                "--mesh",
                "1",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert proc.returncode == 0, proc.stderr[-5000:]
        two_way = json.loads((out / "EXPERIMENTAL_TWO_WAY_BULK_PRESSURE_FEEDBACK.json").read_text())
        assert two_way["REAL_THERMAL_ITERATION_COUNT"] >= 2
        assert two_way["TASK172_PROPERTY_PRESSURE_CONSISTENCY"] == (
            "TASK172_PROPERTY_PRESSURE_CONSISTENT"
        )
        assert two_way["COUPLED_ITERATION_STATUS"] == "COUPLED_CONVERGED"
        second = two_way["iteration_history"][1]
        obs = second["task172_pressure_observations"]
        assert obs, "expected captured Task172 bulk pressure observations"
        sample = obs[-1]
        assert sample["task173_tube_thermo_pressure_pa"] == sample["task172_tube_local_pressure_pa"]
        assert sample["task173_shell_thermo_pressure_pa"] == sample["task172_shell_local_pressure_pa"]
        assert (
            sample["task173_tube_thermo_pressure_pa"]
            == sample["task173_tube_property_evaluation_pressure_pa"]
        )
        assert Decimal(sample["task173_tube_thermo_pressure_pa"]) < Decimal("101325")
        eligibility = json.loads((out / "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json").read_text())
        cand = eligibility["candidates"][0]
        assert cand["ENGINEERING_SIZING_ELIGIBILITY"] == (
            "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
        )
        assert constraint_satisfied_ids(eligibility["candidates"]) == []
