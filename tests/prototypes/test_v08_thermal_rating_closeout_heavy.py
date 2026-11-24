"""V08-03 closeout live rating (isolated CI shard; 7200s pytest timeout preserved)."""

from __future__ import annotations

import pytest

from hexagent.properties.coolprop_provider import CoolPropProvider
from prototypes.v08_thermal_rating.pipeline import run_v08_thermal_rating
from tests.prototypes.v08_thermal_rating_test_support import (
    FIXTURE,
    assert_full_rating_row,
    ready_handoff,
)

# Node migration: from tests/prototypes/test_v08_thermal_rating.py (pre-partition)


@pytest.mark.timeout(7200)
def test_v08_03_closeout_engineering_acceptance_or_engineering_blocked() -> None:
    """Two distinct V08-02 geometries: full rating or fail-closed with Task173 evidence."""
    normalized, handoff = ready_handoff(FIXTURE)
    assert handoff.downstream_readiness == "THERMAL_HYDRAULIC_PARAMETERS_READY"
    result = run_v08_thermal_rating(
        normalized,
        handoff,
        provider=CoolPropProvider(),
    )
    assert result.task_id == "V08_03_LIVE_RATING_ACCEPTANCE_CLOSEOUT"
    assert result.distinct_structural_geometries_attempted >= 2

    if result.engineering_acceptance == "PASS":
        assert result.status in {"OK", "PARTIAL"}
        assert result.blocked_reason is None
        assert result.distinct_fully_converged_rating_count >= 2
        success_rows = [
            r
            for r in result.candidates_rated
            if r.rating_outcome == "RATING_SUCCESS"
            and r.rating_request_replay_ok is True
            and r.mesh_convergence_n1_n2_n4 == "PASS"
            and r.energy_balance_status == "PASS"
        ]
        hashes = {r.geometry_projection_hash for r in success_rows if r.geometry_projection_hash}
        assert len(hashes) >= 2, success_rows
        for row in success_rows:
            assert_full_rating_row(row)
    else:
        assert result.engineering_acceptance == "BLOCKED"
        assert result.status == "BLOCKED"
        assert result.blocked_reason == "ENGINEERING_ACCEPTANCE_RATING"
        assert result.distinct_fully_converged_rating_count < 2
        assert result.engineering_acceptance_blockers, result.candidates_rated
        assert "INSUFFICIENT_DISTINCT_SUCCESSFUL_RATINGS" in str(
            result.engineering_acceptance_blockers
        )
        assert result.model_blockers, "expected Task173 failure codes when rating does not close"
        for row in result.candidates_rated:
            if row.rating_outcome == "RATING_BLOCKED":
                assert row.rating_blocked_code is not None
