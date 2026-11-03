"""R20: experimental Churchill transitional tube hydraulics (opt-in)."""

from __future__ import annotations

import json
import time
from decimal import Decimal
from pathlib import Path

import pytest

from hexagent.exchangers.shell_tube.tube_side.friction_pressure_drop import (
    LAMINAR_UPPER_RE,
    TURBULENT_LOWER_RE,
    classify_reynolds,
    compute_turbulent_friction_factor_safe,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.engineering_input import GeneralEngineeringCaseV2
from prototypes.v07_general_rating_sizing_mvp.experimental_hydraulic_constraint_decision import (
    build_hydraulic_constraint_decision,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_transitional_tube_hydraulic import (
    FRICTION_FACTOR_CONVENTION,
    churchill_1977_darcy_friction_factor,
    experimental_transitional_tube_hydraulic_enabled,
    fanning_from_darcy,
    transitional_reynolds_applicable,
)
from prototypes.v07_general_rating_sizing_mvp.live_thermal_state_hydraulic_postpass import (
    run_live_thermal_state_hydraulic_postpass,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTLETS = REPO_ROOT / "tests/fixtures/r19a_postpass_outlet_states.json"
_CANDIDATE = "39681fe8-bbde-5e5e-97ac-5341c239a776"


def test_churchill_darcy_fanning_consistency() -> None:
    re = Decimal("3325.12")
    eps_d = Decimal("0")
    f_d = churchill_1977_darcy_friction_factor(re, eps_d)
    assert f_d > Decimal("0")
    assert abs(fanning_from_darcy(f_d) * Decimal(4) - f_d) < Decimal("1e-12")


def test_transitional_envelope_matches_task027_gap() -> None:
    assert transitional_reynolds_applicable(Decimal("2500"))
    assert not transitional_reynolds_applicable(LAMINAR_UPPER_RE)
    assert not transitional_reynolds_applicable(TURBULENT_LOWER_RE)
    assert classify_reynolds(Decimal("2500")) == "gap"


def test_churchill_vs_colebrook_same_order_of_magnitude_at_high_re() -> None:
    re = Decimal("8000")
    eps_d = Decimal("0.00005")
    churchill = churchill_1977_darcy_friction_factor(re, eps_d)
    colebrook, blockers = compute_turbulent_friction_factor_safe(re, eps_d)
    assert not blockers
    assert colebrook is not None
    ratio = churchill / colebrook
    assert Decimal("0.5") < ratio < Decimal("2.0")


def _run_postpass(case_key: str, *, transitional: bool) -> dict:
    doc = json.loads(_OUTLETS.read_text(encoding="utf-8"))
    row = doc["cases"][case_key]
    case_path = REPO_ROOT / row["case_fixture"]
    case = load_general_engineering_case_json(case_path.read_text(encoding="utf-8"))
    updates: dict = {"experimental_live_thermal_hydraulic_postpass": True}
    if transitional:
        updates["experimental_transitional_tube_hydraulic"] = True
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


def test_without_r20_flag_task027_gap_stays_blocked() -> None:
    result = _run_postpass("tube_12_shell_20", transitional=False)
    assert result["tube_hydraulic_recompute_status"] == "BLOCKED"
    assert result["recalculated_tube_dp_pa"] is None


def test_r20_completes_transitional_tube_dp_for_three_cases() -> None:
    t0 = time.perf_counter()
    for key in ("tube_12_shell_20", "tube_11_shell_20", "tube_12_shell_19"):
        result = _run_postpass(key, transitional=True)
        assert result["tube_hydraulic_recompute_status"] == "EXPERIMENTAL_TRANSITIONAL_SUCCESS"
        exp = result["experimental_transitional_tube_hydraulic"]
        assert exp is not None
        assert exp["friction_factor_convention"] == FRICTION_FACTOR_CONVENTION
        assert exp["hydraulic_model_scope"] == "EXPERIMENTAL_TRANSITIONAL_TUBE_HYDRAULIC"
        assert int(exp["task028_component_count"]) > 0
        assert exp["task028_component_completeness"] == "COMPLETE"
        total = Decimal(exp["total_tube_dp_pa"])
        friction = Decimal(exp["tube_friction_dp_pa"])
        local = Decimal(exp["tube_local_loss_dp_pa"])
        assert total == friction + local
        assert result["recalculated_tube_dp_pa"] == exp["total_tube_dp_pa"]
        assert result["recalculated_shell_dp_pa"] is not None
    elapsed = time.perf_counter() - t0
    assert elapsed < 60.0


def test_r20_tube_dp_exceeds_erroneous_reference_magnitudes() -> None:
    result = _run_postpass("tube_12_shell_20", transitional=True)
    total = Decimal(result["experimental_transitional_tube_hydraulic"]["total_tube_dp_pa"])
    ref = Decimal(str(result["reference_tube_dp_pa"]))
    assert total > Decimal("50")
    assert ref < Decimal("10")


def test_r20_live_sizing_decision_uses_experimental_tube_dp() -> None:
    result = _run_postpass("tube_12_shell_20", transitional=True)
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
    case = load_general_engineering_case_json(
        (REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json").read_text()
    )
    case = case.model_copy(
        update={
            "experimental_live_thermal_hydraulic_postpass": True,
            "experimental_transitional_tube_hydraulic": True,
        }
    )
    decision = build_hydraulic_constraint_decision(case, row, rating_status="NUMERIC_VALID")
    assert decision["LIVE_HYDRAULIC_CONSTRAINT_STATUS"] in {
        "PRELIMINARY_CONSTRAINT_SATISFIED",
        "PRELIMINARY_CONSTRAINT_FAILED",
    }
    assert decision["live_recalculated_tube_dp_pa"] is not None


def test_engineering_case_flag_requires_postpass() -> None:
    case = load_general_engineering_case_json(
        (REPO_ROOT / "tests/fixtures/r16_pinned_multi_mesh_case.json").read_text()
    )
    payload = case.model_dump()
    payload["experimental_transitional_tube_hydraulic"] = True
    payload["experimental_live_thermal_hydraulic_postpass"] = False
    with pytest.raises(ValueError, match="experimental_live_thermal_hydraulic_postpass"):
        GeneralEngineeringCaseV2.model_validate(payload)
    enabled = case.model_copy(
        update={
            "experimental_transitional_tube_hydraulic": True,
            "experimental_live_thermal_hydraulic_postpass": True,
        }
    )
    assert experimental_transitional_tube_hydraulic_enabled(enabled)
