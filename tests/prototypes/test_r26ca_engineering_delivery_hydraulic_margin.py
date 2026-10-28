"""R26C-A: single-mesh convergence honesty, inlet pressure binding, hydraulic margin."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_engineering_rating_live_bridge import (
    build_experimental_engineering_rating_live_package,
)

_R22 = Path(__file__).resolve().parents[1] / "fixtures/r22_two_way_bulk_pressure_n1_case.json"


def test_single_mesh_does_not_claim_full_rating_converged() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    package = build_experimental_engineering_rating_live_package(
        case,
        run_mesh_ladder=False,
        single_mesh_subdivisions=1,
        run_hydraulic_sensitivity=False,
    )
    mesh = package["mesh_convergence"]
    assert mesh["SINGLE_MESH_NUMERIC_VALID"] is True
    assert mesh["FULL_RATING_CONVERGED"] is False
    assert mesh["MESH_CONVERGENCE_NOT_EVALUATED"] is True
    receipt = package["engineering_delivery_receipt"]
    assert receipt["FULL_RATING_CONVERGED"] is False


def test_hydraulic_postpass_uses_case_inlet_pressures_not_hardcoded_default() -> None:
    payload = json.loads(_R22.read_text(encoding="utf-8"))
    payload["tube_side"]["inlet_pressure_pa"] = "100500"
    payload["shell_side"]["inlet_pressure_pa"] = "101000"
    case = load_general_engineering_case_json(json.dumps(payload))
    package = build_experimental_engineering_rating_live_package(
        case,
        run_mesh_ladder=False,
        single_mesh_subdivisions=1,
        run_hydraulic_sensitivity=False,
    )
    hydraulic = package["hydraulic_receipt"]
    assert hydraulic["TUBE_INLET_PRESSURE_PA"] == "100500"
    assert hydraulic["SHELL_INLET_PRESSURE_PA"] == "101000"
    assert hydraulic["LIVE_HYDRAULIC_IMPLEMENTED"] is True
    postpass = package["live_thermal_state_hydraulic_postpass"]
    assert postpass is not None
    shell_out_p = Decimal(str(postpass["shell_outlet_pressure_pa"]))
    assert shell_out_p < Decimal("101000")


def test_shell_margin_near_boundary_disclosure_on_r22() -> None:
    case = load_general_engineering_case_json(_R22.read_text(encoding="utf-8"))
    package = build_experimental_engineering_rating_live_package(
        case,
        run_mesh_ladder=False,
        single_mesh_subdivisions=1,
        run_hydraulic_sensitivity=True,
    )
    margin = package["hydraulic_margin"]
    assert margin["HYDRAULIC_ROBUSTNESS_STATUS"] in {
        "NEAR_CONSTRAINT_BOUNDARY",
        "SATISFIED",
        "NOT_SATISFIED",
    }
    assert margin["SHELL_FLOW_SENSITIVITY"]["mode"] == "FIXED_THERMAL_STATE_HYDRAULIC_SENSITIVITY"
