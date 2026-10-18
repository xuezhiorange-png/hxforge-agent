"""Live full rating result and fail-closed gates."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_live_rating_result_r19 import (
    experimental_rate_candidate_live_result,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_evidence_admission import (
    LiveEvidenceAdmissionError,
    admit_full_live_mesh_evidence,
)
from prototypes.v07_fast_solver_live_rating_result_r19.live_result_hash import (
    live_rating_result_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalRatingBlocked,
)

ROOT = Path(__file__).resolve().parents[2]


def test_admit_full_live_evidence_headroom_pass() -> None:
    chain = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    assert chain.headroom_status == "PASS"
    assert len(chain.mesh_comparisons) == 6


def test_live_full_rating_result_completed() -> None:
    chain = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    outcome = experimental_rate_candidate_live_result(chain, root=ROOT)
    assert not isinstance(outcome, ExperimentalRatingBlocked)
    assert outcome.execution_mode == "LIVE_NUMERICAL_SOLVE"
    assert outcome.accepted_mesh_n == 32
    assert outcome.headroom_mesh_n == 64
    assert outcome.mesh_sequence_gate == "PASS"
    assert outcome.strict_replay_pass is True
    assert outcome.result_hash == live_rating_result_hash(outcome)


def test_tampered_mesh_hash_blocks_rating() -> None:
    chain = admit_full_live_mesh_evidence(ROOT, candidate_id=CANDIDATE_B_ID)
    stages = list(chain.mesh_stages)
    bad = dict(stages[-1])
    bad["mesh_result_hash"] = "0" * 64
    tampered = chain.__class__(
        request=chain.request,
        rating_request_hash=chain.rating_request_hash,
        snapshot_rel_path=chain.snapshot_rel_path,
        mesh_comparisons=chain.mesh_comparisons,
        mesh_stages=tuple(stages[:-1] + [bad]),
        evidence_chain_hashes=chain.evidence_chain_hashes,
        ladder_status=chain.ladder_status,
        headroom_status=chain.headroom_status,
    )
    outcome = experimental_rate_candidate_live_result(tampered, root=ROOT)
    assert isinstance(outcome, ExperimentalRatingBlocked)
    assert outcome.blocked_code == "MESH_HASH_REPLAY_MISMATCH"


def test_wrong_candidate_id_blocks_admission() -> None:
    with pytest.raises(LiveEvidenceAdmissionError):
        admit_full_live_mesh_evidence(ROOT, candidate_id="not-a-real-candidate")
