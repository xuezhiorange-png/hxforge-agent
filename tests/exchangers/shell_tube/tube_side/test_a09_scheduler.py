"""§A09 — Scheduler tests."""

from __future__ import annotations

import hexagent.exchangers.shell_tube.tube_side as ts


def test_a09_stage_ranks_constant() -> None:
    assert ts.STAGE_RANKS == 9


def test_a09_top_level_non_dict_returns_blocked() -> None:
    """§4.2 — non-dict branch returns Task025BlockedResult with stage_rank=1."""
    result = ts.evaluate_task025("not-a-dict")
    assert isinstance(result, ts.Task025BlockedResult)
    assert result.stage_rank == 1
    assert result.blockers and result.blockers[0].code is ts.BlockerCode.BL_003_BLOCKED_INPUT_REJECTED


def test_a09_top_level_none_returns_blocked() -> None:
    result = ts.evaluate_task025(None)
    assert isinstance(result, ts.Task025BlockedResult)


def test_a09_top_level_int_returns_blocked() -> None:
    result = ts.evaluate_task025(42)
    assert isinstance(result, ts.Task025BlockedResult)


def test_a09_blocked_result_has_stable_hash() -> None:
    """§6.4 — blocked_result_hash is 64-hex."""
    result1 = ts.evaluate_task025(None)
    result2 = ts.evaluate_task025("xyz")
    # Both are blocked results.
    assert isinstance(result1, ts.Task025BlockedResult)
    assert isinstance(result2, ts.Task025BlockedResult)
    # Both hashes are 64-lowercase-hex.
    assert len(result1.blocked_result_hash) == 64
    assert len(result2.blocked_result_hash) == 64
    assert all(c in "0123456789abcdef" for c in result1.blocked_result_hash)
    assert all(c in "0123456789abcdef" for c in result2.blocked_result_hash)

# ruff: noqa: E501
