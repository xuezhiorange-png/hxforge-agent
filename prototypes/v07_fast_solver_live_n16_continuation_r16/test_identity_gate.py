"""Identity gate and compare stage spec fault injection."""

from __future__ import annotations

import pytest

from prototypes.v07_fast_solver_live_ladder_continuation_r14.identity_gate import (
    IdentityGateError,
    assert_compare_stage_spec,
    assert_request_hash_triple,
)


def test_request_hash_triple_mismatch() -> None:
    with pytest.raises(IdentityGateError) as exc:
        assert_request_hash_triple("a" * 64, "b" * 64, "a" * 64)
    assert exc.value.blocked_code == "LIVE_REQUEST_HASH_SNAPSHOT_MISMATCH"


def test_request_hash_reconstruct_mismatch() -> None:
    h = "a" * 64
    with pytest.raises(IdentityGateError) as exc:
        assert_request_hash_triple(h, h, "b" * 64)
    assert exc.value.blocked_code == "LIVE_REQUEST_HASH_RECONSTRUCT_MISMATCH"


def test_compare_mesh_hash_required() -> None:
    with pytest.raises(IdentityGateError) as exc:
        assert_compare_stage_spec(
            {
                "mesh_n": 8,
                "terminal_tolerance_pass": True,
                "cell_closure_pass": True,
                "energy_balance_pass": True,
            },
            label="COARSE",
        )
    assert exc.value.blocked_code == "COMPARE_COARSE_MISSING_STAGE_MESH_HASH"


def test_compare_terminal_fail() -> None:
    with pytest.raises(IdentityGateError) as exc:
        assert_compare_stage_spec(
            {
                "mesh_n": 8,
                "terminal_tolerance_pass": False,
                "cell_closure_pass": True,
                "energy_balance_pass": True,
                "expected_mesh_hash": "c" * 64,
            },
            label="FINE",
        )
    assert exc.value.blocked_code == "COMPARE_FINE_TERMINAL_NOT_ACCEPTED"
