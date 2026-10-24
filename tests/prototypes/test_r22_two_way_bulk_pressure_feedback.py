"""R22: experimental two-way bulk pressure feedback and engineering sizing eligibility."""

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
    COUPLING_SCOPE,
    experimental_two_way_bulk_pressure_feedback_enabled,
    run_two_way_bulk_pressure_coupled_rating,
)
from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import build_native_cell_context

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


def test_coupled_rating_uses_distinct_bulk_pressures_across_iterations() -> None:
    case = load_general_engineering_case_json(_R22_E2E.read_text(encoding="utf-8"))
    assert experimental_two_way_bulk_pressure_feedback_enabled(case)
    native = build_native_cell_context(case)
    result = run_two_way_bulk_pressure_coupled_rating(case, native, mesh_level=1)
    assert result["coupling_scope"] == COUPLING_SCOPE
    history = result["iteration_history"]
    assert len(history) >= 2
    p0_tube = Decimal(history[0]["tube_bulk_property_pressure_pa"])
    p1_tube = Decimal(history[1]["tube_bulk_property_pressure_pa"])
    assert p0_tube == Decimal("101325")
    assert p1_tube < p0_tube
    assert history[0]["total_duty_w"] is not None
    assert history[-1]["total_duty_w"] is not None
    assert result["COUPLED_ITERATION_STATUS"] in {
        "COUPLED_CONVERGED",
        "COUPLED_NOT_CONVERGED_WITHIN_ITERATION_BUDGET",
    }


@pytest.mark.timeout(3600)
def test_r22_two_way_e2e_cli() -> None:
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
        eligibility = json.loads((out / "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json").read_text())
        cand = eligibility["candidates"][0]
        assert cand["ENGINEERING_SIZING_ELIGIBILITY"] == (
            "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
        )
        assert constraint_satisfied_ids(eligibility["candidates"]) == []
