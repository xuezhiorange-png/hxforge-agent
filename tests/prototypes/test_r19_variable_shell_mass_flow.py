"""R19: experimental live variable shell mass flow binding and scope."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from hexagent.exchangers.shell_tube.task173_integrated_rating.experimental_thermal_boundary import (
    EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_SHELL_FLOW_AUTHORITY_ID,
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
from prototypes.v07_general_rating_sizing_mvp.native_thermal_boundary_binding import (
    build_native_thermal_boundary_from_case,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
_R19_CASE = REPO_ROOT / "tests/fixtures/r19_variable_shell_flow_case.json"


def test_scope_allows_19_kg_s_shell_when_opt_in() -> None:
    case = load_general_engineering_case_json(_R19_CASE.read_text(encoding="utf-8"))
    code, detail = check_experimental_live_rating_scope(case)
    assert code == "IN_SCOPE", detail


def test_effective_shell_mass_flow_follows_binding() -> None:
    provider = CoolPropProvider()
    binding = build_experimental_thermal_boundary_v1(
        provider=provider,
        tube_inlet_temperature_k=Decimal("299.70"),
        shell_inlet_temperature_k=Decimal("298.15"),
        shell_mass_flow_kg_s=Decimal("19"),
        allow_live_variable_shell_mass_flow=True,
    )
    assert binding.authority_id == EXPERIMENTAL_THERMAL_BOUNDARY_VARIABLE_SHELL_FLOW_AUTHORITY_ID
    token = bind_experimental_thermal_boundary_v1(binding)
    try:
        assert t173.effective_shell_mass_flow_kg_s() == Decimal("19")
        assert t173.effective_tube_mass_flow_kg_s() == Decimal("12")
    finally:
        reset_experimental_thermal_boundary(token)


def test_native_binding_materializes_user_shell_flow() -> None:
    case = load_general_engineering_case_json(_R19_CASE.read_text(encoding="utf-8"))
    binding = build_native_thermal_boundary_from_case(case, CoolPropProvider())
    assert binding.shell_mass_flow_kg_s == Decimal("19.000000")
    assert binding.tube_mass_flow_kg_s == Decimal("12.000000")
