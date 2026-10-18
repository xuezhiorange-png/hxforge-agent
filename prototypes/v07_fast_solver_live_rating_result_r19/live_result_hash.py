"""Independent hash domain for LIVE_NUMERICAL_SOLVE full rating results."""

from __future__ import annotations

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_rating_authority_admission_r11.experimental_models import (
    ExperimentalCandidateRatingResult,
)

LIVE_RATING_HASH_DOMAIN = "task173.live-numerical-solve-candidate-rating-result.v1"
LIVE_RATING_RESULT_R19_AUTHORITY_ID = "V07-FAST-SOLVER-LIVE-RATING-RESULT-R19"


def live_rating_result_hash(result: ExperimentalCandidateRatingResult) -> str:
    body = result.model_dump(mode="json", exclude={"result_hash", "result_id"})
    body["_live_rating_hash_domain"] = LIVE_RATING_HASH_DOMAIN
    return canonical_sha256(body)


def live_rating_result_id(result_hash: str) -> str:
    return f"live-candidate-rating:{result_hash[:16]}"
