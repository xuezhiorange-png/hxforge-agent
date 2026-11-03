"""Rolling mesh convergence regression (production-aligned)."""

from __future__ import annotations

from prototypes.v07_fast_solver_live_ladder_continuation_r14.rolling_mesh_sequence import (
    RollingMeshState,
)


def _cmp(status: str) -> dict[str, str]:
    return {"overall_status": status}


def test_fail_fail_pass_pass_headroom_pass() -> None:
    state = RollingMeshState()
    steps: list[tuple[int, str | None]] = [
        (1, None),
        (2, "FAIL"),
        (3, "FAIL"),
        (4, "PASS"),
        (8, "PASS"),
    ]
    for mesh_n, status in steps:
        state.record_mesh_accepted(mesh_n)
        if status is not None:
            state.record_comparison(_cmp(status))
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    state.record_mesh_accepted(16)
    state.record_comparison(_cmp("PASS"))
    state.check_headroom_after_new_mesh(16)
    assert state.ladder_status == "HEADROOM_PASS"


def test_fail_pass_pass_headroom_fail() -> None:
    state = RollingMeshState()
    for n in (1, 2, 4):
        state.record_mesh_accepted(n)
    for status in ("FAIL", "PASS", "PASS"):
        state.record_comparison(_cmp(status))
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    state.record_mesh_accepted(8)
    state.record_comparison(_cmp("FAIL"))
    state.check_headroom_after_new_mesh(8)
    assert state.ladder_status == "BLOCKED"
    assert state.blocked_code == "MESH_NOT_CONVERGED"


def test_no_consecutive_pass_pair() -> None:
    state = RollingMeshState()
    state.record_mesh_accepted(1)
    state.record_mesh_accepted(2)
    state.record_comparison(_cmp("FAIL"))
    state.record_mesh_accepted(4)
    state.record_comparison(_cmp("PASS"))
    assert state.candidate_index is None
    assert state.ladder_status == "MESH_COMPARISON_PASS"


def test_fail_fail_fail_pass_then_pass_identifies_candidate_n32() -> None:
    state = RollingMeshState()
    for mesh_n in (1, 2, 4, 8, 16):
        state.record_mesh_accepted(mesh_n)
    for status in ("FAIL", "FAIL", "FAIL", "PASS"):
        state.record_comparison(_cmp(status))
    assert state.ladder_status == "MESH_COMPARISON_PASS"
    assert state.candidate_index is None
    state.record_mesh_accepted(32)
    state.record_comparison(_cmp("PASS"))
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    assert state.runs_mesh_n[state.candidate_index] == 32


def test_candidate_then_headroom_fail_blocks() -> None:
    state = RollingMeshState()
    for mesh_n in (1, 2, 4, 8, 16, 32):
        state.record_mesh_accepted(mesh_n)
    for status in ("FAIL", "FAIL", "FAIL", "PASS", "PASS"):
        state.record_comparison(_cmp(status))
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    state.record_mesh_accepted(64)
    state.record_comparison(_cmp("FAIL"))
    state.check_headroom_after_new_mesh(64)
    assert state.ladder_status == "BLOCKED"
    assert state.blocked_code == "MESH_NOT_CONVERGED"


def test_terminal_boundary_failed() -> None:
    state = RollingMeshState()
    state.terminal_boundary_failed()
    assert state.ladder_status == "BLOCKED"
    assert state.blocked_code == "MESH_TERMINAL_BOUNDARY_FAILED"


def test_budget_exhausted() -> None:
    state = RollingMeshState()
    state.budget_exhausted()
    assert state.ladder_status == "TIMEOUT"
    assert state.blocked_code == "NUMERICAL_BUDGET_EXHAUSTED"
