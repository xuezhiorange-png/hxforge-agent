"""Pinned comparison history admission."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    admit_prior_comparison_history,
    build_rolling_state_from_admitted_history,
)

ROOT = Path(__file__).resolve().parents[2]


def test_admit_five_prior_comparisons_in_order() -> None:
    history = admit_prior_comparison_history(ROOT)
    assert len(history) == 5
    pairs = [(int(c["coarse_subdivisions"]), int(c["fine_subdivisions"])) for c in history]
    assert pairs == [(1, 2), (2, 4), (4, 8), (8, 16), (16, 32)]
    statuses = [c["overall_status"] for c in history]
    assert statuses == ["FAIL", "FAIL", "FAIL", "PASS", "PASS"]


def test_rolling_after_admitted_history_is_candidate_identified() -> None:
    history = admit_prior_comparison_history(ROOT)
    state = build_rolling_state_from_admitted_history(history)
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    assert state.runs_mesh_n[state.candidate_index] == 32
