"""Compact rating linkage to frozen R11 full artifact."""

from __future__ import annotations

from pathlib import Path

from prototypes.v07_fast_solver_evidence_gate.trusted_constants import (
    R11_RATING_JSON_REL,
    R11_RATING_JSON_SHA256,
    R11_RESULT_HASH,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.compact_rating import (
    build_compact_from_full,
    compact_rating_hash,
)
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)

ROOT = Path(__file__).resolve().parents[2]


def test_compact_links_to_r11_full_hash() -> None:
    full = ExperimentalCandidateRatingResult.model_validate_json(
        (ROOT / R11_RATING_JSON_REL).read_text(encoding="utf-8"),
        strict=True,
    )
    compact = build_compact_from_full(
        full,
        trajectory_artifact_path=R11_RATING_JSON_REL,
        trajectory_file_sha256=R11_RATING_JSON_SHA256,
    )
    assert compact.full_result_hash == R11_RESULT_HASH
    assert compact.compact_result_hash == compact_rating_hash(compact)
