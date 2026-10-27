"""R25A: SciPy relative diff_step and wall-network wide-ΔT closure."""

from __future__ import annotations

import math
import sys

import pytest

from hexagent.exchangers.shell_tube.task172_local_runtime import service as task172_service


def test_scipy_diff_step_is_relative_not_absolute() -> None:
    values = (50_000.0, 305.0, 298.0)
    relative = task172_service._relative_diff_step_vector(wide_experimental=True)
    perturbations = task172_service._actual_jacobian_perturbations(values, relative)
    assert perturbations[0] == abs(values[0]) * _q_step(relative)
    assert perturbations[1] == abs(values[1]) * _temp_step(relative)
    assert perturbations[0] == pytest.approx(5.0)
    assert perturbations[1] == pytest.approx(0.00305)
    assert perturbations[2] == pytest.approx(0.00298)
    frozen = task172_service._relative_diff_step_vector(wide_experimental=False)
    assert type(frozen) is float
    frozen_h = task172_service._actual_jacobian_perturbations(values, frozen)
    assert frozen_h[0] == abs(values[0]) * frozen


def _q_step(relative: tuple[float, float, float]) -> float:
    return relative[0]


def _temp_step(relative: tuple[float, float, float]) -> float:
    return relative[1]


def test_wide_profile_uses_wall_network_not_dimensionally_invalid_relaxation() -> None:
    assert not hasattr(task172_service, "_wide_relax_to_acceptance")
    profile = task172_service._WIDE_DELTA_T_EXPERIMENTAL_NUMERICAL_PROFILE_ID
    assert "R25D" in profile
    assert "PHYSICAL-TWO-SCALAR-BRACKET" in profile


def test_zero_state_uses_machine_epsilon_perturbation_floor() -> None:
    perturbations = task172_service._actual_jacobian_perturbations(
        (0.0, 300.0, 298.0),
        task172_service._FROZEN_RELATIVE_DIFF_STEP,
    )
    assert perturbations[0] == math.sqrt(sys.float_info.epsilon)
