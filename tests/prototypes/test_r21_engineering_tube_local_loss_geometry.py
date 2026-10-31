"""R21: engineering tube local-loss geometry binding for live post-pass."""

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
from prototypes.v07_general_rating_sizing_mvp.engineering_tube_local_loss_geometry import (
    BLOCKER_CODE,
    TubeLocalLossEngineeringInput,
    demo_100mm_entrance_component,
    nozzle_flow_area_m2,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_hydraulic_constraint_decision import (
    build_hydraulic_constraint_decision,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTLETS = REPO_ROOT / "tests/fixtures/r19a_postpass_outlet_states.json"
_CANDIDATE = "39681fe8-bbde-5e5e-97ac-5341c239a776"
_R21_E2E = REPO_ROOT / "tests/fixtures/r21_engineering_local_loss_n1_case.json"


def _engineering_spec(
    *,
    nozzle_diameter_m: str,
    component_id: str = "R21-DEMO-ENTRANCE",
) -> TubeLocalLossEngineeringInput:
    return TubeLocalLossEngineeringInput(
        geometry_basis="EXPERIMENTAL_ASSUMED_DEMO",
        completeness_declaration="ENTRANCE_ONLY_ASSUMED",
        components=(
            demo_100mm_entrance_component().model_copy(
                update={
                    "component_id": component_id,
                    "nozzle_inside_diameter_m": Decimal(nozzle_diameter_m),
                }
            ),
        ),
    )


def _run_postpass(
    case_key: str,
    *,
    transitional: bool = False,
    engineering: TubeLocalLossEngineeringInput | None = None,
) -> dict:
    doc = json.loads(_OUTLETS.read_text(encoding="utf-8"))
    row = doc["cases"][case_key]
    case_path = REPO_ROOT / row["case_fixture"]
    case = load_general_engineering_case_json(case_path.read_text(encoding="utf-8"))
    updates: dict = {
        "experimental_live_thermal_hydraulic_postpass": True,
        "experimental_transitional_tube_hydraulic": transitional,
        "experimental_engineering_tube_local_loss": engineering is not None,
        "tube_local_loss_engineering": engineering,
    }
    case = case.model_copy(update=updates)
    return run_live_thermal_state_hydraulic_postpass(
        case,
        candidate_id=_CANDIDATE,
        tube_inlet_temperature_k=Decimal("299.70"),
        tube_outlet_temperature_k=Decimal(str(row["tube_outlet_temperature_k"])),
        shell_inlet_temperature_k=Decimal("298.15"),
        shell_outlet_temperature_k=Decimal(str(row["shell_outlet_temperature_k"])),
        tube_inlet_pressure_pa=Decimal("101325"),
        shell_inlet_pressure_pa=Decimal("101325"),
    )


def test_engineering_flag_without_spec_rejected_at_case_load() -> None:
    case = load_general_engineering_case_json(
        (REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json").read_text()
    )
    payload = case.model_dump()
    payload["experimental_transitional_tube_hydraulic"] = True
    payload["experimental_engineering_tube_local_loss"] = True
    payload["tube_local_loss_engineering"] = None
    with pytest.raises(ValueError, match="tube_local_loss_engineering"):
        GeneralEngineeringCaseV2.model_validate(payload)


def test_legacy_fixture_path_unchanged_without_r21_flag() -> None:
    legacy = _run_postpass("tube_12_shell_20", transitional=False)
    assert legacy["tube_hydraulic_recompute_status"] == "BLOCKED"


def test_r21_demo_100mm_reproduces_transitional_total_dp() -> None:
    r20 = _run_postpass("tube_12_shell_20", transitional=True, engineering=None)
    assert r20["tube_hydraulic_recompute_status"] == "EXPERIMENTAL_TRANSITIONAL_SUCCESS"
    r21 = _run_postpass(
        "tube_12_shell_20",
        transitional=True,
        engineering=_engineering_spec(nozzle_diameter_m="0.100"),
    )
    assert r21["tube_hydraulic_recompute_status"] == "EXPERIMENTAL_TRANSITIONAL_SUCCESS"
    eng = r21["tube_local_loss_engineering"]
    assert eng is not None
    assert eng["assumed_geometry_status"] == "EXPERIMENTAL_ASSUMED_GEOMETRY_ONLY"
    assert eng["local_component_count"] == "1"
    area = Decimal(eng["local_component_areas_m2"])
    assert abs(area - nozzle_flow_area_m2(Decimal("0.100"))) < Decimal("1e-9")
    total = Decimal(r21["experimental_transitional_tube_hydraulic"]["total_tube_dp_pa"])
    r20_total = Decimal(r20["experimental_transitional_tube_hydraulic"]["total_tube_dp_pa"])
    assert abs(total - r20_total) < Decimal("2")
    assert total > Decimal("600")
    assert total < Decimal("800")


def test_smaller_nozzle_increases_local_and_total_tube_dp() -> None:
    large = _run_postpass(
        "tube_12_shell_20",
        transitional=True,
        engineering=_engineering_spec(nozzle_diameter_m="0.100", component_id="NOZZLE-100"),
    )
    small = _run_postpass(
        "tube_12_shell_20",
        transitional=True,
        engineering=_engineering_spec(nozzle_diameter_m="0.080", component_id="NOZZLE-80"),
    )
    large_local = Decimal(
        large["experimental_transitional_tube_hydraulic"]["tube_local_loss_dp_pa"]
    )
    small_local = Decimal(
        small["experimental_transitional_tube_hydraulic"]["tube_local_loss_dp_pa"]
    )
    large_total = Decimal(large["experimental_transitional_tube_hydraulic"]["total_tube_dp_pa"])
    small_total = Decimal(small["experimental_transitional_tube_hydraulic"]["total_tube_dp_pa"])
    assert small_local > large_local
    assert small_total > large_total
    friction_large = Decimal(
        large["experimental_transitional_tube_hydraulic"]["tube_friction_dp_pa"]
    )
    friction_small = Decimal(
        small["experimental_transitional_tube_hydraulic"]["tube_friction_dp_pa"]
    )
    assert abs(friction_large - friction_small) < Decimal("1")


def test_r15_live_decision_with_engineering_geometry() -> None:
    result = _run_postpass(
        "tube_12_shell_20",
        transitional=True,
        engineering=_engineering_spec(nozzle_diameter_m="0.100"),
    )
    case = load_general_engineering_case_json(_R21_E2E.read_text(encoding="utf-8"))
    row = {
        "mesh_status": "NUMERIC_VALID",
        "total_duty_w": "32000",
        "constraint_preview": {
            "modeled_tube_dp_pa": result["reference_tube_dp_pa"],
            "modeled_shell_dp_pa": result["reference_shell_dp_pa"],
            "tube_dp_constraint": "SATISFIED",
            "shell_dp_constraint": "SATISFIED",
        },
        "live_thermal_state_hydraulic_postpass": result,
    }
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] in {
        "PRELIMINARY_CONSTRAINT_SATISFIED",
        "PRELIMINARY_CONSTRAINT_FAILED",
    }


@pytest.mark.timeout(1800)
def test_r21_n1_rating_with_engineering_local_loss_e2e() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "prototypes.v07_general_rating_sizing_mvp",
                "--input",
                str(_R21_E2E),
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
        assert proc.returncode == 0, proc.stderr[-4000:]
        rated = json.loads((out / "CANDIDATE_RATING_RESULTS.json").read_text())["candidates"]
        assert rated[0]["mesh_status"] == "NUMERIC_VALID"
        postpass = rated[0]["live_thermal_state_hydraulic_postpass"]
        assert postpass is not None
        assert postpass["tube_local_loss_engineering"] is not None
        assert postpass["tube_hydraulic_recompute_status"] == "EXPERIMENTAL_TRANSITIONAL_SUCCESS"
        assert not any(
            blocker.get("code") == BLOCKER_CODE for blocker in postpass.get("blockers", [])
        )
        sizing = json.loads((out / "LIVE_HYDRAULIC_SIZING_DECISION.json").read_text())
        assert sizing["per_candidate"][0]["live_recalculated_tube_dp_pa"] is not None
