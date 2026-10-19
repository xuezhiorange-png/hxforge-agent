"""Frozen second-candidate stage admission and mesh replay."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_snapshot_and_prior_stages_admit() -> None:
    frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
    scsa.verify_n4_timeout_receipt_preserved(ROOT)
    n1 = scsa.admit_second_candidate_prior_stage(ROOT, scsa.SECOND_CANDIDATE_PRIOR_PINS[0])
    n2 = scsa.admit_second_candidate_prior_stage(ROOT, scsa.SECOND_CANDIDATE_PRIOR_PINS[1])
    n4 = scsa.admit_second_candidate_prior_stage(ROOT, scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS[2])
    n8 = scsa.admit_second_candidate_prior_stage(ROOT, scsa.SECOND_CANDIDATE_ACCEPTED_PRIOR_PINS[3])
    run1 = scsa.replay_admitted_prior_mesh(frozen.request, n1, mesh_n=1)
    run2 = scsa.replay_admitted_prior_mesh(frozen.request, n2, mesh_n=2)
    run4 = scsa.replay_admitted_prior_mesh(frozen.request, n4, mesh_n=4)
    run8 = scsa.replay_admitted_prior_mesh(frozen.request, n8, mesh_n=8)
    scsa.verify_replay_physics(run1)
    scsa.verify_replay_physics(run2)
    scsa.verify_replay_physics(run4)
    scsa.verify_replay_physics(run8)
    assert run1.mesh_result_hash == n1["mesh_result_hash"]
    assert run2.mesh_result_hash == n2["mesh_result_hash"]
    assert run4.mesh_result_hash == scsa.N4_MESH_RESULT_HASH
    assert run8.mesh_result_hash == scsa.N8_MESH_RESULT_HASH
