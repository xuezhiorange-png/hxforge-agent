"""R21 second-candidate discovery contract."""

from __future__ import annotations

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_discovery as discovery_mod,
)


def test_second_candidate_is_not_candidate_b() -> None:
    discovery = discovery_mod.discover_second_candidate()
    assert discovery.status == "DISCOVERED"
    assert discovery.candidate_id == discovery_mod.SECOND_CANDIDATE_ID
    assert discovery.candidate_id != CANDIDATE_B_ID
    assert discovery.candidate_hash == discovery_mod.EXPECTED_SECOND_CANDIDATE_HASH
    assert discovery.rating_request_hash == discovery_mod.EXPECTED_SECOND_RATING_REQUEST_HASH
    assert all(status == "PASS" for _, status in discovery.upstream_authority_checks)
