"""Verify frozen R11 full rating artifact hash parity."""

from __future__ import annotations

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import R11_RESULT_HASH
from prototypes.v07_fast_solver_rating_contract_live_bridge_r12.r11_artifact_verify import (
    verify_r11_full_rating_artifact,
)


def test_r11_stored_rating_result_hash_parity() -> None:
    report = verify_r11_full_rating_artifact()
    assert report["schema_valid"] is True
    assert report["result_hash_parity"] == "PASS"
    assert report["recomputed_result_hash"] == R11_RESULT_HASH
