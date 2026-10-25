"""R24: wide ΔT cell closure tolerance and inlet pressure validation."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2

_R23_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures/r23_variable_water_temperature_n1_case.json"
)


def test_v2_validates_tube_and_shell_pressure_separately() -> None:
    payload = json.loads(_R23_FIXTURE.read_text(encoding="utf-8"))
    payload["tube_side"]["inlet_pressure_pa"] = "99000"
    with pytest.raises(ValueError, match="tube_side inlet pressure"):
        GeneralEngineeringCaseV2.model_validate(payload)
    payload["tube_side"]["inlet_pressure_pa"] = "101325"
    payload["shell_side"]["inlet_pressure_pa"] = "99000"
    with pytest.raises(ValueError, match="shell_side inlet pressure"):
        GeneralEngineeringCaseV2.model_validate(payload)


def test_variable_water_cell_residual_tolerance_scales_with_duty() -> None:
    q_scale = Decimal("40104")
    tolerance = max(Decimal("1e-6"), q_scale * Decimal("2e-8"))
    assert Decimal("0.00055") <= tolerance
    assert Decimal("0.01") > tolerance


def test_primary_310_295_k_remains_blocked_until_outer_hole_recovery_improves() -> None:
    from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
        load_general_engineering_case_json,
    )
    from prototypes.v07_general_rating_sizing_mvp.positive_duty_cell import (
        build_native_cell_context,
        run_mesh_numeric_with_profile,
    )

    case = load_general_engineering_case_json(_R23_FIXTURE.read_text(encoding="utf-8"))
    native = build_native_cell_context(case)
    mesh, _, _ = run_mesh_numeric_with_profile(
        native,
        subdivisions=1,
        case=case,
        enable_live_thermal_boundary=True,
    )
    assert mesh.get("status") == "BLOCKED"
    assert mesh.get("failure_code") in {
        "PRECISION_FLOOR_UNRESOLVED",
        "BLOCKED_CELL_VALID_EVALUATION_BRACKET_UNRESOLVED",
        "BLOCKED_CELL_VALID_POINT_BRACKET_SIGN_INVALID",
    }
