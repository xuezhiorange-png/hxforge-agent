"""R27E physical model isolation and provenance."""

from __future__ import annotations

from prototypes.v07_general_rating_sizing_mvp.r27e_targeted_recovery import (
    R27D_ORIGINAL_BLOCKERS,
    R27D_RECOVERY_CANDIDATE_IDS,
)


def test_r27d_original_blockers_frozen_not_runtime_n1_codes() -> None:
    assert len(R27D_ORIGINAL_BLOCKERS) == len(R27D_RECOVERY_CANDIDATE_IDS)
    for cid in R27D_RECOVERY_CANDIDATE_IDS:
        blocker = R27D_ORIGINAL_BLOCKERS[cid]
        assert blocker != "_RuntimeFailure"
        assert not blocker.startswith("BLOCKED_N1")
