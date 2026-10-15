"""Evidence chain gate for R11."""

from __future__ import annotations

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import RATING_REQUEST_HASH
from prototypes.v07_fast_solver_rating_authority_admission_r11.evidence_chain import (
    verify_candidate_b_evidence_chain,
)


def test_candidate_b_evidence_chain_passes() -> None:
    chain = verify_candidate_b_evidence_chain()
    assert chain["rating_request_hash"] == RATING_REQUEST_HASH
    assert chain["r9_n32_body"]["outer_boundary_status"] == "TERMINAL_ACCEPTED"
