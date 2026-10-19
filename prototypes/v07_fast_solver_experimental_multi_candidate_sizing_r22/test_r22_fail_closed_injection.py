"""R22 negative injection tests."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
    experimental_multi_candidate_sizing,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_sizing_requirement import (
    experimental_multi_candidate_sizing_requirement,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    FROZEN_Q13_CANDIDATE_SPACE_HASH,
)

ROOT = Path(__file__).resolve().parents[2]


def test_requirement_hash_tamper_blocked() -> None:
    req = experimental_multi_candidate_sizing_requirement()
    bad = req.model_copy(update={"canonical_hash": "0" * 64})
    result = experimental_multi_candidate_sizing(ROOT, bad)
    assert result.status == "BLOCKED"
    assert result.blocked_code == "SIZING_REQUIREMENT_CANONICAL_HASH_MISMATCH"


def test_candidate_space_requirement_mismatch_blocked() -> None:
    req = experimental_multi_candidate_sizing_requirement()
    projection = req.model_dump(mode="json", exclude={"canonical_hash"})
    projection["discrete_candidate_authority_ids_and_hashes"] = [["FAKE", "0" * 64]]
    tampered = req.model_copy(
        update={
            "discrete_candidate_authority_ids_and_hashes": (("FAKE", "0" * 64),),
            "canonical_hash": canonical_sha256(projection),
        }
    )
    result = experimental_multi_candidate_sizing(ROOT, tampered)
    assert result.status == "BLOCKED"
    assert result.blocked_code == "REQUIREMENT_CANDIDATE_SPACE_HASH_MISMATCH"


def test_impossible_duty_blocks_ranking() -> None:
    req = experimental_multi_candidate_sizing_requirement(required_duty_w="999999999")
    result = experimental_multi_candidate_sizing(ROOT, req)
    assert result.status == "RANKING_BLOCKED"
    assert result.ranking_trace_status == "RANKING_BLOCKED"


def test_frozen_space_hash_constant() -> None:
    assert len(FROZEN_Q13_CANDIDATE_SPACE_HASH) == 64
