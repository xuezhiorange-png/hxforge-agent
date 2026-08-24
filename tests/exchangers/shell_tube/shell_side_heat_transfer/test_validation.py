"""Supplemental validation stage and fail-closed checks."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.shell_side_heat_transfer import validate_request
from tests.exchangers.shell_tube.shell_side_heat_transfer.test_models import copy_request


def test_success_has_no_blockers_or_partial_htc() -> None:
    result = validate_request(copy_request())
    assert result.heat_transfer is not None
    assert result.heat_transfer.blockers == ()
    assert not hasattr(result.heat_transfer, "nusselt_number")


def test_failure_never_returns_zero_htc() -> None:
    raw = copy_request()
    raw["task032_flow_state"]["shell_side_reynolds_number"] = "1"
    result = validate_request(raw)
    assert result.heat_transfer is None
    assert result.blocked_result is not None
    assert not hasattr(result.blocked_result, "modeled_shell_side_heat_transfer_coefficient_w_m2_k")
