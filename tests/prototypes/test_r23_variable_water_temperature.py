"""R23: experimental variable water inlet temperature and two-way sizing fail-closed."""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2
from prototypes.v07_general_rating_sizing_mvp.experimental_candidate_eligibility import (
    constraint_satisfied_ids,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_two_way_coupling_sizing import (
    TWO_WAY_COUPLING_NOT_CONVERGED,
    apply_two_way_coupling_constraint_gate,
)
from prototypes.v07_general_rating_sizing_mvp.variable_water_temperature import (
    VARIABLE_WATER_TEMPERATURE_MAX_K,
    VARIABLE_WATER_TEMPERATURE_MIN_K,
    validate_variable_water_inlet_temperature_k,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R23_E2E = REPO_ROOT / "tests/fixtures/r23_variable_water_temperature_n1_case.json"
_R22_E2E = REPO_ROOT / "tests/fixtures/r22_two_way_bulk_pressure_n1_case.json"


def test_variable_water_temperature_envelope() -> None:
    validate_variable_water_inlet_temperature_k(Decimal("310"), label="tube_side")
    validate_variable_water_inlet_temperature_k(Decimal("295"), label="shell_side")
    with pytest.raises(ValueError, match="290"):
        validate_variable_water_inlet_temperature_k(Decimal("289"), label="tube_side")


def test_case_requires_live_postpass_for_variable_temperature() -> None:
    payload = json.loads(_R23_E2E.read_text(encoding="utf-8"))
    payload["experimental_live_thermal_hydraulic_postpass"] = False
    with pytest.raises(ValueError, match="experimental_variable_water_temperature"):
        GeneralEngineeringCaseV2.model_validate(payload)


def test_frozen_envelope_unchanged_without_opt_in() -> None:
    payload = json.loads(_R22_E2E.read_text(encoding="utf-8"))
    payload["tube_side"]["inlet_temperature_k"] = "310"
    with pytest.raises(ValueError, match="298.15"):
        GeneralEngineeringCaseV2.model_validate(payload)


def test_two_way_nonconverged_fail_closed_for_sizing() -> None:
    case = load_general_engineering_case_json(_R22_E2E.read_text(encoding="utf-8"))
    row = {
        "mesh_status": "NUMERIC_VALID",
        "experimental_two_way_bulk_pressure_feedback": {
            "COUPLED_ITERATION_STATUS": "BLOCKED_THERMAL_RATING",
        },
        "live_thermal_state_hydraulic_postpass": {
            "hydraulic_constraint_status": "SATISFIED",
            "tube_hydraulic_recompute_status": "SUCCESS",
            "shell_hydraulic_recompute_status": "SUCCESS",
        },
        "constraint_preview": {
            "duty_constraint": "SATISFIED",
            "tube_dp_constraint": "SATISFIED",
            "shell_dp_constraint": "SATISFIED",
        },
    }
    gated = apply_two_way_coupling_constraint_gate(
        case, row, "PRELIMINARY_CONSTRAINT_SATISFIED"
    )
    assert gated == TWO_WAY_COUPLING_NOT_CONVERGED
    eligibility = [
        {
            "candidate_id": "c1",
            "CONSTRAINT_STATUS": gated,
            "TWO_WAY_COUPLING_SIZING_STATUS": "BLOCKED_THERMAL_RATING",
            "engineering_sizing_eligibility": {
                "ENGINEERING_SIZING_ELIGIBILITY": (
                    "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
                ),
            },
        }
    ]
    assert constraint_satisfied_ids(eligibility) == []


def test_two_way_disabled_allows_ranking_when_constraints_satisfied() -> None:
    eligibility = [
        {
            "candidate_id": "c1",
            "CONSTRAINT_STATUS": "PRELIMINARY_CONSTRAINT_SATISFIED",
            "TWO_WAY_COUPLING_SIZING_STATUS": None,
            "engineering_sizing_eligibility": {
                "ENGINEERING_SIZING_ELIGIBILITY": "LEGACY_REFERENCE_HYDRAULIC_PATH",
            },
        }
    ]
    assert constraint_satisfied_ids(eligibility) == ["c1"]


def _run_live_cli(case_path: Path, output_dir: Path) -> dict[str, Any]:
    with subprocess.Popen(
        [
            sys.executable,
            "-m",
            "prototypes.v07_general_rating_sizing_mvp",
            "--input",
            str(case_path),
            "--output",
            str(output_dir),
            "--mode",
            "experimental-live-rating",
            "--mesh",
            "1",
        ],
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as proc:
        _, err = proc.communicate(timeout=3500)
    assert proc.returncode == 0, err[-8000:]
    return json.loads((output_dir / "RAW_RESULT.json").read_text())


@pytest.mark.timeout(600)
def test_r23_primary_310_295_k_reports_honest_outcome() -> None:
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        build_native_cell_context,
        run_mesh_numeric_with_profile,
    )

    case = load_general_engineering_case_json(_R23_E2E.read_text(encoding="utf-8"))
    native = build_native_cell_context(case)
    mesh, _, _ = run_mesh_numeric_with_profile(
        native,
        subdivisions=1,
        case=case,
        enable_live_thermal_boundary=True,
    )
    assert mesh.get("status") == "BLOCKED"
    assert mesh.get("failure_code") == "PRECISION_FLOOR_UNRESOLVED"


@pytest.mark.timeout(3600)
def test_r23_mild_variable_water_e2e_cli() -> None:
    payload = json.loads(_R23_E2E.read_text(encoding="utf-8"))
    payload["tube_side"]["inlet_temperature_k"] = "300.5"
    payload["shell_side"]["inlet_temperature_k"] = "298.5"
    case_path = Path("/tmp/r23-mild-case.json")
    case_path.write_text(json.dumps(payload), encoding="utf-8")
    raw = _run_live_cli(case_path, Path("/tmp/r23-mild-out"))
    row = raw["rating_rows"][0]
    assert row["mesh_status"] == "NUMERIC_VALID"
    assert Decimal(str(row["total_duty_w"])) > 0
    tube_out = Decimal(str(row["tube_outlet_temperature_k"]))
    shell_out = Decimal(str(row["shell_outlet_temperature_k"]))
    assert tube_out < Decimal("300.5")
    assert shell_out > Decimal("298.5")
    assert VARIABLE_WATER_TEMPERATURE_MIN_K <= tube_out <= VARIABLE_WATER_TEMPERATURE_MAX_K
    eligibility = json.loads(
        (Path("/tmp/r23-mild-out") / "EXPERIMENTAL_CANDIDATE_ELIGIBILITY.json").read_text()
    )
    cand = eligibility["candidates"][0]
    assert cand["ENGINEERING_SIZING_ELIGIBILITY"] == (
        "DEMONSTRATION_ONLY_NOT_ENGINEERING_SIZING_ELIGIBLE"
    )
