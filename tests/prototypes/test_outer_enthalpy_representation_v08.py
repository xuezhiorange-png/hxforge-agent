"""Prototype install/uninstall for outer enthalpy representation (no mesh solve)."""

from __future__ import annotations

from decimal import Decimal

from hexagent.exchangers.shell_tube.task173_integrated_rating.service import (
    _state_from_enthalpy,
    _terminal_tolerance_pass,
    _valid_trajectory,
)
from prototypes.v08_thermal_rating.outer_enthalpy_representation_v08 import (
    outer_enthalpy_representation_scope,
)


def test_prototype_patches_restore_after_scope() -> None:
    import hexagent.exchangers.shell_tube.task173_integrated_rating.service as svc

    orig_state = svc._state_from_enthalpy
    with outer_enthalpy_representation_scope(h_cold=Decimal("83000")):
        assert svc._state_from_enthalpy is not orig_state
        assert svc._valid_trajectory is not _valid_trajectory
    assert svc._state_from_enthalpy is orig_state
    assert svc._state_from_enthalpy is _state_from_enthalpy
    assert svc._terminal_tolerance_pass is _terminal_tolerance_pass
