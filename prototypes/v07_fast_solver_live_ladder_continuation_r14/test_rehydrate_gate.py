"""Rehydrate return gate regression."""

from __future__ import annotations

import pytest

from prototypes.v07_fast_solver_live_ladder_continuation_r14.rehydrate_gate import (
    RehydrateGateError,
    require_bounded_rehydrate_ok,
)

REQ = "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8"
MESH = "651c8df3daf9d1a06442cc07416e141909376ef2d0259558db86c88240206e7f"


def _ok() -> dict[str, object]:
    return {
        "status": "OK",
        "subdivisions": 16,
        "mesh_result_hash": MESH,
        "terminal_tolerance_pass": True,
        "cell_closure_pass": True,
        "energy_balance_pass": True,
        "rating_request_hash": REQ,
    }


def test_require_ok_passes() -> None:
    require_bounded_rehydrate_ok(
        _ok(),
        mesh_n=16,
        expected_request_hash=REQ,
        expected_mesh_hash=MESH,
    )


def test_require_status_not_ok_raises() -> None:
    with pytest.raises(RehydrateGateError) as exc:
        require_bounded_rehydrate_ok(
            {"status": "TIMEOUT", "blocked_code": "REHYDRATE_HARD_TIMEOUT"},
            mesh_n=8,
            expected_request_hash=REQ,
            expected_mesh_hash=None,
        )
    assert exc.value.code == "REHYDRATE_HARD_TIMEOUT"


def test_require_mesh_hash_mismatch_raises() -> None:
    body = _ok()
    body["mesh_result_hash"] = "deadbeef"
    with pytest.raises(RehydrateGateError) as exc:
        require_bounded_rehydrate_ok(
            body,
            mesh_n=16,
            expected_request_hash=REQ,
            expected_mesh_hash=MESH,
        )
    assert exc.value.code == "REHYDRATE_MESH_HASH_MISMATCH"
