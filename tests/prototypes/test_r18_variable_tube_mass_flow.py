"""R18: experimental live variable tube mass flow binding and scope."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    bind_experimental_thermal_boundary_v1,
    build_experimental_thermal_boundary_v1,
    reset_experimental_thermal_boundary,
)
from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import (
    load_general_engineering_case_json,
)
from prototypes.v07_general_rating_sizing_mvp.experimental_live_scope import (
    check_experimental_live_rating_scope,
)
from prototypes.v07_general_rating_sizing_mvp.input_to_solver_binding import (
    build_input_to_solver_binding,
)
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R18_CASE = REPO_ROOT / "tests/fixtures/r18_variable_tube_flow_case.json"


def test_scope_allows_11_kg_s_when_opt_in_flag_set() -> None:
    case = load_general_engineering_case_json(_R18_CASE.read_text(encoding="utf-8"))
    code, detail = check_experimental_live_rating_scope(case)
    assert code == "IN_SCOPE", detail


def test_scope_rejects_variable_flow_without_flag() -> None:
    case = load_general_engineering_case_json(_R18_CASE.read_text(encoding="utf-8"))
    case = case.model_copy(
        update={"experimental_live_variable_tube_mass_flow": False},
    )
    code, detail = check_experimental_live_rating_scope(case)
    assert code == "INPUT_OUT_OF_SUPPORTED_SCOPE"
    assert detail is not None and "12.000000" in detail


def test_effective_tube_mass_flow_follows_experimental_binding() -> None:
    provider = CoolPropProvider()
    binding = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=Decimal("299.70"),
        shell_inlet_temperature_k=Decimal("298.15"),
        tube_mass_flow_kg_s=Decimal("10"),
        allow_live_variable_tube_mass_flow=True,
    )
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        assert t173.effective_tube_mass_flow_kg_s() == Decimal("10")
        assert t173.effective_shell_mass_flow_kg_s() == Decimal("20")
    finally:
        reset_experimental_thermal_boundary(token)
    assert t173.effective_tube_mass_flow_kg_s() == t173.TUBE_MASS_FLOW_KG_S


def test_native_binding_materializes_user_tube_flow_when_opt_in() -> None:
    case = load_general_engineering_case_json(_R18_CASE.read_text(encoding="utf-8"))
    binding = build_native_thermal_boundary_from_case(case, CoolPropProvider())
    assert binding.tube_mass_flow_kg_s == Decimal("11.000000")
    assert binding.shell_mass_flow_kg_s == Decimal("20")


def test_input_to_solver_binding_marks_tube_flow_participating_when_opt_in() -> None:
    case = load_general_engineering_case_json(_R18_CASE.read_text(encoding="utf-8"))
    doc = build_input_to_solver_binding(case)
    tube_row = next(row for row in doc["rows"] if row["user_field"] == "tube_side.mass_flow_kg_s")
    assert tube_row["participates_in_rating_kernel"] is True
    assert tube_row["solver_value"] == "11.000000"
