"""Deterministic TASK-169 identity helpers."""

from __future__ import annotations

import uuid
from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    canonical_bytes,
    sha256_domain_hex,
)

from .models import (
    CandidateRankingRecord,
    Task169RankingPolicy,
    Task169Request,
    Task169Result,
    Task169TypedBlockedResult,
)

POLICY_HASH_DOMAIN = "task169.selection-ranking-policy.v1"
REQUEST_HASH_DOMAIN = "task169.selection-request.v1"
RANK_RECORD_HASH_DOMAIN = "task169.selection-rank-record.v1"
RESULT_HASH_DOMAIN = "task169.selection-result.v1"
BLOCKED_HASH_DOMAIN = "task169.selection-blocked.v1"

RESULT_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-000000000169")
RESULT_ID_PREFIX = "task169-selection-result-v1::"
BLOCKED_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-00000000016a")
BLOCKED_ID_PREFIX = "task169-selection-blocked-v1::"


def ranking_policy_projection(value: Task169RankingPolicy) -> dict[str, Any]:
    return {
        "policy_id": value.policy_id,
        "policy_version": value.policy_version,
        "source_definition_id": value.source_definition_id,
        "source_id": value.source_id,
        "authority_origin": value.authority_origin,
        "approval_status": value.approval_status,
        "top_n": value.top_n,
        "warning_penalty": value.warning_penalty,
        "objectives": value.objectives,
        "tie_break_rule": value.tie_break_rule,
        "evidence_refs": value.evidence_refs,
        "provenance_refs": value.provenance_refs,
    }


def ranking_policy_hash(value: Task169RankingPolicy) -> str:
    return sha256_domain_hex(POLICY_HASH_DOMAIN, ranking_policy_projection(value))


def request_projection(value: Task169Request) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "task169_version": value.task169_version,
        "source_definition_id": value.source_definition_id,
        "task168_result_hash": value.task168_result.result_hash,
        "task168_result_id": value.task168_result.result_id,
        "ranking_policy_hash": value.ranking_policy.canonical_hash,
        "request_metadata": tuple(
            sorted(
                value.request_metadata,
                key=lambda pair: (
                    pair[0].encode("utf-8", "strict"),
                    pair[1].encode("utf-8", "strict"),
                ),
            )
        ),
    }


def request_hash(value: Task169Request) -> str:
    return sha256_domain_hex(REQUEST_HASH_DOMAIN, request_projection(value))


def rank_record_projection(value: CandidateRankingRecord) -> dict[str, Any]:
    return {
        "rank": value.rank,
        "candidate_id": value.candidate_id,
        "candidate_hash": value.candidate_hash,
        "source_status": value.source_status,
        "composite_score": value.composite_score,
        "objective_values": value.objective_values,
        "warning_count": value.warning_count,
        "warning_penalty_contribution": value.warning_penalty_contribution,
        "reason_codes": value.reason_codes,
    }


def rank_record_hash(value: CandidateRankingRecord) -> str:
    return sha256_domain_hex(RANK_RECORD_HASH_DOMAIN, rank_record_projection(value))


def result_preimage(value: Task169Result) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "task169_version": value.task169_version,
        "implementation_software_version": value.implementation_software_version,
        "source_definition_id": value.source_definition_id,
        "request_hash": value.request_hash,
        "source_task168_result_hash": value.source_task168_result_hash,
        "source_task168_result_id": value.source_task168_result_id,
        "source_task168_provenance_hash": value.source_task168_provenance_hash,
        "ranking_policy_hash": value.ranking_policy_hash,
        "selection_status": value.selection_status,
        "recommendable_candidate_count": value.recommendable_candidate_count,
        "excluded_candidate_count": value.excluded_candidate_count,
        "ranked_candidates": value.ranked_candidates,
        "recommended_candidate": value.recommended_candidate,
        "alternatives": value.alternatives,
        "excluded_candidates": value.excluded_candidates,
        "provenance_semantic_inputs": value.provenance_semantic_inputs,
        "recommendation_reason_codes": value.recommendation_reason_codes,
        "alternative_reason_codes": value.alternative_reason_codes,
    }


def result_hash(value: Task169Result) -> str:
    return sha256_domain_hex(RESULT_HASH_DOMAIN, result_preimage(value))


def result_id(hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_PREFIX + hash_value))


def blocked_hash(value: Task169TypedBlockedResult) -> str:
    return sha256_domain_hex(
        BLOCKED_HASH_DOMAIN,
        {
            "schema_version": value.schema_version,
            "task169_version": value.task169_version,
            "implementation_software_version": value.implementation_software_version,
            "request_hash": value.request_hash,
            "blocker_codes": value.blocker_codes,
        },
    )


def blocked_id(hash_value: str) -> str:
    return str(uuid.uuid5(BLOCKED_ID_NAMESPACE, BLOCKED_ID_PREFIX + hash_value))


__all__ = [
    "blocked_hash",
    "blocked_id",
    "canonical_bytes",
    "rank_record_hash",
    "ranking_policy_hash",
    "request_hash",
    "result_hash",
    "result_id",
]
