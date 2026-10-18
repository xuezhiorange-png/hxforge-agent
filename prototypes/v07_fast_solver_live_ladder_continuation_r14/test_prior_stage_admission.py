"""Pinned R13 stage SHA256 admission."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import (
    DEFAULT_PRIOR_PINS,
    admit_prior_stage,
)

ROOT = Path(__file__).resolve().parents[2]


def test_r13_n1_n2_stage_sha256_admission() -> None:
    for pin in DEFAULT_PRIOR_PINS:
        receipt = admit_prior_stage(
            ROOT,
            pin,
            expected_request_hash="56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
            expected_candidate_id="e152cca9-fd5d-59ca-9b46-1df574eee841",
        )
        assert receipt["prior_stage_status"] == "VERIFIED_PRIOR_LIVE_STAGE"
        assert receipt["stage_receipt_sha256"] == pin.expected_sha256
