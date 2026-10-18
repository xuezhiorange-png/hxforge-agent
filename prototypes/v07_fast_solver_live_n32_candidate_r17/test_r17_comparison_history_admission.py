"""Pinned comparison history admission."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_live_ladder_continuation_r14.comparison_history_admission import (
    admit_prior_comparison_history,
    build_rolling_state_from_admitted_history,
)

ROOT = Path(__file__).resolve().parents[2]


def test_admit_six_prior_comparisons_in_order() -> None:
    history = admit_prior_comparison_history(ROOT)
    assert len(history) == 6
    pairs = [(int(c["coarse_subdivisions"]), int(c["fine_subdivisions"])) for c in history]
    assert pairs[-1] == (32, 64)


def test_rolling_after_r17_slice_is_candidate_identified() -> None:
    history = admit_prior_comparison_history(ROOT)
    state = build_rolling_state_from_admitted_history(history[:5])
    assert state.ladder_status == "MESH_CANDIDATE_IDENTIFIED"
    assert state.runs_mesh_n[state.candidate_index] == 32
