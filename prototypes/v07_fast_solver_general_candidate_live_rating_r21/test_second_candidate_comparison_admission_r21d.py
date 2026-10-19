"""R21D pinned comparison admission tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_comparison_admission as scca,
)
from prototypes.v07_fast_solver_general_candidate_live_rating_r21 import (
    second_candidate_stage_admission as scsa,
)

ROOT = Path(__file__).resolve().parents[2]


def test_r21c_historical_comparison_admission_fail_fail_fail_pass() -> None:
    frozen = scsa.admit_frozen_second_candidate_snapshot(ROOT)
    stages_by_mesh: dict[int, dict] = {}
    for pin in scsa.SECOND_CANDIDATE_R21D_PRIOR_PINS:
        receipt = scsa.admit_second_candidate_prior_stage(ROOT, pin)
        run = scsa.replay_admitted_prior_mesh(frozen.request, receipt, mesh_n=pin.mesh_n)
        scsa.verify_replay_physics(run)
        stages_by_mesh[pin.mesh_n] = receipt
    comparisons, _rolling = scca.admit_r21c_historical_comparisons(
        ROOT,
        stages_by_mesh=stages_by_mesh,
    )
    assert [c["overall_status"] for c in comparisons] == ["FAIL", "FAIL", "FAIL", "PASS"]


def test_comparison_file_tamper_blocked() -> None:
    stages_by_mesh = {}
    for pin in scsa.SECOND_CANDIDATE_R21D_PRIOR_PINS:
        stages_by_mesh[pin.mesh_n] = scsa.admit_second_candidate_prior_stage(ROOT, pin)
    pin = scca.R21C_HISTORICAL_COMPARISON_PINS[0]
    bad = scca.ComparisonAdmissionPin(
        pin.coarse_mesh_n,
        pin.fine_mesh_n,
        pin.rel_path,
        "0" * 64,
        pin.comparison_canonical_sha256,
        pin.expected_overall_status,
    )
    with pytest.raises(scca.ComparisonAdmissionError, match="COMPARISON_FILE_SHA256_MISMATCH"):
        scca.admit_pinned_comparison(ROOT, bad, stages_by_mesh=stages_by_mesh)
