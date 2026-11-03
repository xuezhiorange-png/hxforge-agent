"""R19A: live hydraulic post-pass equipment mass flow binding (fast postpass-only)."""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTLETS = REPO_ROOT / "tests/fixtures/r19a_postpass_outlet_states.json"
_CANDIDATE = "39681fe8-bbde-5e5e-97ac-5341c239a776"


def _run_postpass(case_key: str) -> dict:
    doc = json.loads(_OUTLETS.read_text(encoding="utf-8"))
    row = doc["cases"][case_key]
    case_path = REPO_ROOT / row["case_fixture"]
    case = load_general_engineering_case_json(case_path.read_text(encoding="utf-8"))
    case = case.model_copy(update={"experimental_live_thermal_hydraulic_postpass": True})
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


def test_task026_uses_equipment_total_tube_mass_flow() -> None:
    result = _run_postpass("tube_12_shell_20")
    binding = result["mass_flow_binding"]
    assert binding["tube_binding_status"] == "MATCHED_EQUIPMENT_TOTAL"
    assert binding["task026_input_mass_flow_kg_s"] == "12.000000"
    assert binding["equipment_tube_mass_flow_kg_s"] == "12.000000"
    assert Decimal(binding["historical_task026_template_mass_flow_kg_s"]) < Decimal("1")


def test_task032_uses_equipment_total_shell_mass_flow_for_19_kg_s() -> None:
    result = _run_postpass("tube_12_shell_19")
    binding = result["mass_flow_binding"]
    assert binding["shell_binding_status"] == "MATCHED_EQUIPMENT_TOTAL"
    assert binding["task032_input_mass_flow_kg_s"] == "19.000000"
    assert result["shell_hydraulic_recompute_status"] == "SUCCESS"
    assert result["recalculated_shell_dp_pa"] is not None


def test_tube_task027_blocked_in_transition_reynolds_at_12_kg_s() -> None:
    result = _run_postpass("tube_12_shell_20")
    assert result["tube_hydraulic_recompute_status"] == "BLOCKED"
    assert Decimal(result["tube_reynolds_number"]) > Decimal("3000")
    assert any(
        "BL_T027_UNSUPPORTED_REYNOLDS_REGIME" in blocker.get("code", "")
        for blocker in result["blockers"]
    )
    assert result["shell_hydraulic_recompute_status"] == "SUCCESS"
    assert result["recalculated_shell_dp_pa"] is not None


def test_tube_reynolds_scales_with_equipment_tube_flow() -> None:
    r12 = _run_postpass("tube_12_shell_20")
    r11 = _run_postpass("tube_11_shell_20")
    re12 = Decimal(r12["tube_reynolds_number"])
    re11 = Decimal(r11["tube_reynolds_number"])
    assert re11 < re12
    assert abs(re11 / re12 - Decimal("11") / Decimal("12")) < Decimal("0.01")
