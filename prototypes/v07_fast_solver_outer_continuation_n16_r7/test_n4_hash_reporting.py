"""Ensure R7 n=4 validation does not conflate hash parity with numerical tolerance."""

from __future__ import annotations

from decimal import Decimal

from prototypes.v07_fast_solver_outer_continuation_n16_r7.run_r7 import (
    DUTY_ABS_TOL_W,
    SHOOTING_ABS_TOL_J_KG,
)


def _hash_flags(
    *,
    obs_hash: str,
    baseline_hash: str,
    shooting_ref: str,
    shooting_actual: str,
    duty_ref: str,
    duty_actual: str,
    terminal_ok: bool,
) -> tuple[bool, bool]:
    shooting_ok = abs(Decimal(shooting_actual) - Decimal(shooting_ref)) <= SHOOTING_ABS_TOL_J_KG
    duty_delta = abs(Decimal(duty_actual) - Decimal(duty_ref))
    exact_mesh_hash_match = obs_hash == baseline_hash
    numerical_comparison_within_tolerance = (
        shooting_ok and duty_delta <= DUTY_ABS_TOL_W and terminal_ok
    )
    return exact_mesh_hash_match, numerical_comparison_within_tolerance


def test_numerical_close_but_hash_different_not_exact_match() -> None:
    exact, numerical = _hash_flags(
        obs_hash="aaa",
        baseline_hash="bbb",
        shooting_ref="107515.23962914693046195797622203826904296875",
        shooting_actual="107515.239610405252152254308542926874991962904459796845912933349609375",
        duty_ref="51902.3956510717697",
        duty_actual="51902.3956510717697",
        terminal_ok=True,
    )
    assert exact is False
    assert numerical is True


def test_exact_hash_requires_equality() -> None:
    exact, numerical = _hash_flags(
        obs_hash="same",
        baseline_hash="same",
        shooting_ref="1",
        shooting_actual="1",
        duty_ref="1",
        duty_actual="1",
        terminal_ok=True,
    )
    assert exact is True
    assert numerical is True
