"""Independent hash domain for R21 general second-candidate live ratings."""

from __future__ import annotations

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)

GENERAL_LIVE_RATING_HASH_DOMAIN = (
    "task173.live-numerical-solve-general-candidate-rating-result.v1"
)
GENERAL_LIVE_RATING_R21_AUTHORITY_ID = (
    "V07-FAST-SOLVER-GENERAL-CANDIDATE-LIVE-RATING-R21"
)


def general_live_rating_result_hash(result: ExperimentalCandidateRatingResult) -> str:
    body = result.model_dump(mode="json", exclude={"result_hash", "result_id"})
    body["_live_rating_hash_domain"] = GENERAL_LIVE_RATING_HASH_DOMAIN
    return canonical_sha256(body)


def general_live_rating_result_id(result_hash: str) -> str:
    return f"general-live-candidate-rating:{result_hash[:16]}"
