"""Experimental multi-candidate sizing result schema and hash replay."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_sizing.models import RankingTraceEntry
from prototypes.v07_fast_solver_experimental_multi_candidate_sizing_r22.r22_pinned_identity import (
    EXPERIMENTAL_MULTI_CANDIDATE_SIZING_AUTHORITY_ID,
    EXPERIMENTAL_SIZING_RESULT_HASH_DOMAIN,
    EXPERIMENTAL_SIZING_RESULT_SCHEMA,
)


class StrictModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class ExperimentalCandidateSizingRecord(StrictModel):
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    full_result_hash: str
    compact_result_hash: str
    experimental_rating_authority_id: str
    rated_duty_w: Decimal
    tube_dp_pa: Decimal
    shell_dp_pa: Decimal
    duty_constraint: Literal["PASS", "BLOCKED"]
    tube_dp_constraint: Literal["PASS", "BLOCKED"]
    shell_dp_constraint: Literal["PASS", "BLOCKED"]
    screening_status: Literal["WARN", "BLOCKED"]
    status: Literal["PASS", "WARN", "BLOCKED"]
    warnings: tuple[str, ...]
    blockers: tuple[str, ...]
    ranking_score: Decimal | None = None
    rank: int | None = None


class ExperimentalMultiCandidateSizingResult(StrictModel):
    schema_version: Literal["task173.experimental-multi-candidate-sizing-result.v1"] = (
        EXPERIMENTAL_SIZING_RESULT_SCHEMA
    )
    status: Literal["EXPERIMENTAL_COMPLETE", "BLOCKED", "RANKING_BLOCKED"]
    numerical_authority_status: Literal["CANDIDATE"]
    production_integration: Literal[False] = False
    experimental_sizing_authority_id: str = EXPERIMENTAL_MULTI_CANDIDATE_SIZING_AUTHORITY_ID
    sizing_requirement_hash: str
    candidate_space_hash: str
    candidate_space_authority_id: str
    candidate_count: int
    candidate_records: tuple[ExperimentalCandidateSizingRecord, ...]
    ranking_trace: tuple[RankingTraceEntry, ...] = ()
    ranking_trace_status: Literal["COMPLETE", "RANKING_BLOCKED", "NOT_APPLICABLE"]
    recommended_candidate_id: str | None = None
    alternative_candidate_ids: tuple[str, ...] = ()
    mandatory_screening_gate: str
    duty_constraint_gate: Literal["PASS", "BLOCKED"]
    tube_dp_constraint_gate: Literal["PASS", "BLOCKED"]
    shell_dp_constraint_gate: Literal["PASS", "BLOCKED"]
    candidate_identity_gate: Literal["PASS", "BLOCKED"]
    blocked_code: str | None = None
    blocked_diagnostics: tuple[str, ...] = ()
    result_provenance: tuple[tuple[str, str], ...]
    result_hash: str = Field(min_length=64, max_length=64)
    result_id: str


def experimental_multi_candidate_sizing_result_hash(
    result: ExperimentalMultiCandidateSizingResult,
) -> str:
    body = result.model_dump(mode="json", exclude={"result_hash", "result_id"})
    body["_experimental_sizing_hash_domain"] = EXPERIMENTAL_SIZING_RESULT_HASH_DOMAIN
    return canonical_sha256(body)


def experimental_multi_candidate_sizing_result_id(result_hash: str) -> str:
    return f"experimental-multi-candidate-sizing:{result_hash[:16]}"
