"""R25C: scalar u wall closure profile and physical mapping."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service


def test_r25c_scalar_profile_id() -> None:
    profile = task172_service._WIDE_DELTA_T_EXPERIMENTAL_NUMERICAL_PROFILE_ID
    assert "R25" in profile


def test_wide_scalar_two_budget_constants_are_bounded() -> None:
    assert task172_service._WIDE_SCALAR_TWO_UPPER_BISECTION_MAX <= 32
    assert task172_service._WIDE_SCALAR_TWO_MAX_BRENT_ITER <= 64
    assert task172_service._WIDE_EXPERIMENTAL_CALLBACK_CAP <= 64
