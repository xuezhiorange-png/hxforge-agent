"""R22 experimental multi-candidate sizing — determinism and gates."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import CANDIDATE_B_ID
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    SECOND_CANDIDATE_ID,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    experimental_multi_candidate_sizing_result_hash,
)

ROOT = Path(__file__).resolve().parents[2]


def test_experimental_multi_candidate_sizing_deterministic() -> None:
    req = experimental_multi_candidate_sizing_requirement()
    a = experimental_multi_candidate_sizing(ROOT, req)
    b = experimental_multi_candidate_sizing(ROOT, req)
    assert a.status == "EXPERIMENTAL_COMPLETE"
    assert a.result_hash == b.result_hash
    assert a.result_hash == experimental_multi_candidate_sizing_result_hash(a)
    assert a.candidate_count == 2
    assert a.recommended_candidate_id == CANDIDATE_B_ID
    assert SECOND_CANDIDATE_ID in a.alternative_candidate_ids
    assert a.duty_constraint_gate == "PASS"
    assert a.ranking_trace_status == "COMPLETE"
    assert len(a.ranking_trace) == 2
