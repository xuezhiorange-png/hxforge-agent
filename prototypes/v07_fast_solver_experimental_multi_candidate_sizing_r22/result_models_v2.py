"""R22A v2 experimental sizing result — production vs experimental recommendation boundary."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Literal

from pydantic import Field

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.mandatory_screening import (
    ScreeningRuleRecord,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    EXPERIMENTAL_MULTI_CANDIDATE_SIZING_R22A_AUTHORITY_ID,
    EXPERIMENTAL_SIZING_RESULT_V2_HASH_DOMAIN,
    EXPERIMENTAL_SIZING_RESULT_V2_SCHEMA,
)
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.result_models import (
    ExperimentalMultiCandidateSizingResult,
    StrictModel,
)


class ExperimentalMultiCandidateSizingResultV2(StrictModel):
    schema_version: Literal["task173.experimental-multi-candidate-sizing-result.v2"] = (
        EXPERIMENTAL_SIZING_RESULT_V2_SCHEMA
    )
    experimental_sizing_authority_id: str = EXPERIMENTAL_MULTI_CANDIDATE_SIZING_R22A_AUTHORITY_ID
    v1_result: ExperimentalMultiCandidateSizingResult
    production_recommendation_authorized: Literal[False] = False
    production_multi_candidate_sizing_verified: Literal[False] = False
    mandatory_screening_complete: Literal[False] = False
    experimental_recommended_candidate_id: str | None = None
    experimental_alternative_candidate_ids: tuple[str, ...] = ()
    mandatory_screening_gate: str
    fiv_authority_status: Literal["MISSING", "PRESENT"]
    screening_rule_records: tuple[ScreeningRuleRecord, ...] = ()
    screening_gap_codes: tuple[str, ...] = ()
    result_hash: str = Field(min_length=64, max_length=64)
    result_id: str


def experimental_multi_candidate_sizing_result_v2_hash(
    result: ExperimentalMultiCandidateSizingResultV2,
) -> str:
    body = result.model_dump(mode="json", exclude={"result_hash", "result_id"})
    body["_experimental_sizing_hash_domain"] = EXPERIMENTAL_SIZING_RESULT_V2_HASH_DOMAIN
    return canonical_sha256(body)


def experimental_multi_candidate_sizing_result_v2_id(result_hash: str) -> str:
    return f"experimental-multi-candidate-sizing-v2:{result_hash[:16]}"
