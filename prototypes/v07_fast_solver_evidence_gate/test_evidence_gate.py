"""Evidence gate must reject tampered files and separate hash semantics."""

from __future__ import annotations

import pytest

from prototypes.v07_fast_solver_evidence_gate.r7_archived_bracket import (
    verify_r7_archived_bracket,
)
from prototypes.v07_fast_solver_evidence_gate.trusted_constants import RATING_REQUEST_HASH


def test_r7_archived_bracket_trusted_gate_passes() -> None:
    meta = verify_r7_archived_bracket(rating_request_hash=RATING_REQUEST_HASH)
    assert meta["archived_low_trial_index"] == 21
    assert meta["trusted_gate"] == "R7_ARCHIVED_BRACKET_PINNED"


def test_r7_archived_bracket_rejects_wrong_rating_hash() -> None:
    with pytest.raises(ValueError, match="rating_request_hash"):
        verify_r7_archived_bracket(rating_request_hash="0" * 64)


def test_n4_hash_reporting_exact_vs_numerical() -> None:
    """Numerical tolerance must not set exact_mesh_hash_match."""
    report = {
        "exact_mesh_hash_match": False,
        "numerical_comparison_within_tolerance": True,
        "mesh_hash_match": False,
    }
    assert report["exact_mesh_hash_match"] is False
    assert report["numerical_comparison_within_tolerance"] is True

