"""R25C: scalar u wall closure profile and physical mapping."""

from __future__ import annotations

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service


def test_r25c_scalar_profile_id() -> None:
    profile = task172_service._WIDE_DELTA_T_EXPERIMENTAL_NUMERICAL_PROFILE_ID
    assert "R25C" in profile
    assert "SCALAR" in profile


def test_scalar_u_budget_constants_are_bounded() -> None:
    assert task172_service._WIDE_SCALAR_U_BRACKET_SAMPLES <= 8
    assert task172_service._WIDE_SCALAR_U_MAX_BRENT_ITER <= 12
    assert task172_service._WIDE_SCALAR_U_MAX_SEEDS <= 2
    assert task172_service._WIDE_EXPERIMENTAL_CALLBACK_CAP <= 32
