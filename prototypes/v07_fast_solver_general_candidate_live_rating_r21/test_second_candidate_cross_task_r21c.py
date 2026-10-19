"""R21C cross-task admission, identity, and ledger regression tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)
from prototypes.v07_fast_solver_live_ladder_continuation_r14.stage_admission import PriorStagePin

ROOT = Path(__file__).resolve().parents[2]


def test_accepted_prior_pins_n1_through_n8_admit_and_replay() -> None:
    frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
    scsa.verify_n4_timeout_receipt_preserved(ROOT)
    scsa.verify_n16_timeout_receipt_preserved(ROOT)
    for pin in scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(ROOT, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        assert run.mesh_result_hash == receipt["mesh_result_hash"]


def test_prior_stage_sha256_tamper_blocked() -> None:
    pin = scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS[2]
    bad = PriorStagePin(pin.mesh_n, pin.rel_path, "0" * 64)
    with pytest.raises(scsa.SecondCandidateAdmissionError, match="PRIOR_STAGE_SHA256_MISMATCH"):
        scsa.admit_second_candidate_prior_stage(ROOT, bad)


def test_n16_timeout_receipt_preserved() -> None:
    scsa.verify_n16_timeout_receipt_preserved(ROOT)
