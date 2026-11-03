"""Regression tests for production-aligned rolling mesh selector."""

from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

from prototypes.v07_fast_solver_outer_continuation_n16_r7.rolling_mesh_selector import (
    evaluate_rolling_mesh_convergence,
)


def _comparison(overall: str) -> SimpleNamespace:
    return SimpleNamespace(
        duty_status=overall,
        wall_status=overall,
        overall_status=overall,
        duty_metric=Decimal("0"),
        duty_difference_w=Decimal("0"),
    )


def test_early_failures_do_not_block_later_consecutive_pass() -> None:
    seq = [1, 2, 4, 8, 16]
    comparisons = [
        _comparison("FAIL"),
        _comparison("PASS"),
        _comparison("PASS"),
        _comparison("PASS"),
    ]
    result = evaluate_rolling_mesh_convergence(seq, comparisons)
    assert result.candidate_subdivisions == 8
    assert result.headroom_subdivisions == 16
    assert result.mesh_candidate_identified is True
    assert result.headroom_status == "PASS"
    assert result.comparison_history[0]["overall_status"] == "FAIL"


def test_headroom_fail_marks_not_identified() -> None:
    seq = [1, 2, 4, 8, 16]
    comparisons = [
        _comparison("FAIL"),
        _comparison("PASS"),
        _comparison("PASS"),
        _comparison("FAIL"),
    ]
    result = evaluate_rolling_mesh_convergence(seq, comparisons)
    assert result.candidate_subdivisions == 8
    assert result.headroom_subdivisions is None
    assert result.mesh_candidate_identified is False
    assert result.headroom_status == "FAIL"


def test_no_consecutive_pass_yields_no_candidate() -> None:
    seq = [1, 2, 4, 8]
    comparisons = [_comparison("FAIL"), _comparison("PASS"), _comparison("FAIL")]
    result = evaluate_rolling_mesh_convergence(seq, comparisons)
    assert result.mesh_candidate_identified is False
    assert result.candidate_subdivisions is None
