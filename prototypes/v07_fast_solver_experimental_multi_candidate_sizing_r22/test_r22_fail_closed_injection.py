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
    assert result.blocked_code == "REQUIREMENT_CANDIDATE_SPACE_AUTHORITY_ID_MISMATCH"


def test_impossible_duty_blocks_ranking() -> None:
    from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.experimental_multi_candidate_sizing import (
        experimental_multi_candidate_sizing_from_admitted,
    )
    from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.rating_pair_admission import (
        admit_candidate_b_live_rating,
        admit_second_candidate_live_rating,
    )

    req = experimental_multi_candidate_sizing_requirement()
    b = admit_candidate_b_live_rating(ROOT)
    second = admit_second_candidate_live_rating(ROOT)
    full = b.full.model_copy(update={"total_duty_w": __import__("decimal").Decimal("1")})
    b = b.__class__(
        label=b.label,
        full=full,
        compact_r19=b.compact_r19,
        compact_general=b.compact_general,
        request=b.request,
        full_audit=b.full_audit,
        full_file_sha256=b.full_file_sha256,
        snapshot_rel_path=b.snapshot_rel_path,
    )
    result = experimental_multi_candidate_sizing_from_admitted(req, (b, second), evidence_root=ROOT)
    assert result.status == "BLOCKED"
    assert result.blocked_code in (
        "PINNED_FULL_STRUCTURAL_MISMATCH",
        "FULL_RESULT_HASH_REPLAY_MISMATCH",
        "COMPACT_FULL_ENGINEERING_PARITY_MISMATCH",
    )


def test_frozen_space_hash_constant() -> None:
    assert len(FROZEN_Q13_CANDIDATE_SPACE_HASH) == 64
