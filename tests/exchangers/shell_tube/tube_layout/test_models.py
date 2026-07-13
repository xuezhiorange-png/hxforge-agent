from __future__ import annotations

import dataclasses

import pytest

from hexagent.exchangers.shell_tube.tube_layout.models import DEFERRED_CAPABILITIES, AxisOrientation, LatticeIndex, OriginMode


def test_value_objects_are_frozen() -> None:
    index = LatticeIndex(1, 2)
    with pytest.raises(dataclasses.FrozenInstanceError):
        index.u = 3  # type: ignore[misc]


def test_closed_enum_order_and_deferred_order() -> None:
    assert [item.value for item in OriginMode] == ["CENTER_ON_LATTICE_POINT", "CENTER_ON_PRIMITIVE_CELL"]
    assert [item.value for item in AxisOrientation] == ["PRIMARY_AXIS_X", "PRIMARY_AXIS_Y"]
    assert DEFERRED_CAPABILITIES[0] == "SHELL_DIAMETER_NOT_COMPUTABLE"
    assert DEFERRED_CAPABILITIES[-1] == "GOLDEN_VALIDATION_NOT_COMPUTABLE"
