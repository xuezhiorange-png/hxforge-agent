"""Outer shooting binary64 enthalpy step and plateau diagnostics."""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _binary64_enthalpy_step_toward,
)


def test_binary64_enthalpy_step_toward_is_representable_and_interior() -> None:
    h_low = Decimal("120000.0")
    h_high = Decimal("122022.67196814526108")
    stepped = _binary64_enthalpy_step_toward(h_high, h_low)
    assert stepped is not None
    assert h_low < stepped < h_high
    assert stepped != h_high
