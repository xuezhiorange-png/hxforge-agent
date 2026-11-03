"""Mesh hash replay mismatch surfaces REPLAY_MISMATCH at physics gate."""

from __future__ import annotations

from prototypes.v07_fast_solver_live_ladder_continuation_r14.physics_gate import (
    evaluate_live_physics_gate,
)


class _FakeRun:
    subdivisions = 4
    mesh_result_hash = "aa" * 32
    cells = [object()] * 4


def test_replay_mismatch_blocked_code() -> None:
    receipt = {
        "worker_status": "TERMINAL_ACCEPTED",
        "terminal_tolerance_pass": True,
        "cell_closure_pass": True,
        "energy_balance_pass": True,
        "rating_request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
        "mesh_result_hash": "bb" * 32,
        "mesh_n": 4,
    }
    ok, code, _diag = evaluate_live_physics_gate(
        receipt,
        request=object(),  # type: ignore[arg-type]
        run=_FakeRun(),  # type: ignore[arg-type]
        expected_request_hash=receipt["rating_request_hash"],
    )
    assert not ok
    assert code == "REPLAY_MISMATCH"
