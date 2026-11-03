"""Experimental live variable shell mass flow opt-in (R19)."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v07_general_rating_sizing_mvp.engineering_case_loader import EngineeringCase

_LEGACY_SHELL_MASS_FLOW_KG_S = Decimal("20.000000")
_VARIABLE_SHELL_FLOW_MIN_KG_S = Decimal("16.000000")
_VARIABLE_SHELL_FLOW_MAX_KG_S = Decimal("24.000000")


def experimental_live_variable_shell_mass_flow_enabled(case: EngineeringCase) -> bool:
    return bool(getattr(case, "experimental_live_variable_shell_mass_flow", False))


def validate_variable_shell_mass_flow_kg_s(mass_flow_kg_s: Decimal) -> None:
    if (
        mass_flow_kg_s < _VARIABLE_SHELL_FLOW_MIN_KG_S
        or mass_flow_kg_s > _VARIABLE_SHELL_FLOW_MAX_KG_S
    ):
        raise ValueError(
            "shell_side mass_flow_kg_s must stay within "
            f"{_VARIABLE_SHELL_FLOW_MIN_KG_S}–{_VARIABLE_SHELL_FLOW_MAX_KG_S} kg/s "
            "when experimental_live_variable_shell_mass_flow is enabled"
        )


def legacy_shell_mass_flow_kg_s() -> Decimal:
    return _LEGACY_SHELL_MASS_FLOW_KG_S
