"""Canonical identities for TASK-169 release acceptance."""

from __future__ import annotations

import uuid
from typing import Any

from hexagent.exchangers.shell_tube.manufacturable_candidates.canonical import (
    sha256_domain_hex,
)

from .models import (
    Task169ReleaseBlockedResult,
    Task169ReleaseRequest,
    Task169ReleaseResult,
)

REQUEST_HASH_DOMAIN = "task169.release-acceptance.request.v2"
RESULT_HASH_DOMAIN = "task169.release-acceptance.result.v2"
BLOCKED_HASH_DOMAIN = "task169.release-acceptance.blocked.v2"

RESULT_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-000000000179")
RESULT_ID_PREFIX = "task169-release-result-v2::"
BLOCKED_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-00000000017a")
BLOCKED_ID_PREFIX = "task169-release-blocked-v2::"


def request_projection(value: Task169ReleaseRequest) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "release_version": value.release_version,
        "source_definition_id": value.source_definition_id,
        "golden_cases": tuple(
            {
                "golden_id": case.golden_id,
                "source_id": case.source_id,
                "source_location": case.source_location,
                "source_class": case.source_class,
                "redistribution_status": case.redistribution_status,
                "normalized_input_identity": case.normalized_input_identity,
                "task168_request_hash": case.task168_request_hash,
                "expected_task168_result_hash": case.expected_task168_result_hash,
                "expected_task168_result_id": case.expected_task168_result_id,
                "expected_task168_result_status": case.expected_task168_result_status,
                "ranking_policy_hash": case.ranking_policy.canonical_hash,
                "expected_task169_result_hash": case.expected_task169_result_hash,
                "expected_task169_result_id": case.expected_task169_result_id,
                "approved_numeric_expectations": case.approved_numeric_expectations,
                "tolerance_class": case.tolerance_class,
                "provenance_source_hash": case.provenance_source_hash,
                "reviewer_evidence_refs": case.reviewer_evidence_refs,
                "review_status": case.review_status,
                "approved_by": case.approved_by,
                "approval_evidence": case.approval_evidence,
                "expected_identity_status": case.expected_identity_status,
                "negative_class": case.negative_class,
                "expected_blocker_code": case.expected_blocker_code,
                "expected_blocker_owner": case.expected_blocker_owner,
                "no_recommendation_required": case.no_recommendation_required,
            }
            for case in value.golden_cases
        ),
        "frozen_tolerance_ledger": value.frozen_tolerance_ledger,
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


def request_hash(value: Task169ReleaseRequest) -> str:
    return sha256_domain_hex(REQUEST_HASH_DOMAIN, request_projection(value))


def result_preimage(value: Task169ReleaseResult) -> dict[str, Any]:
    return {
        "schema_version": value.schema_version,
        "release_version": value.release_version,
        "implementation_software_version": value.implementation_software_version,
        "source_definition_id": value.source_definition_id,
        "request_hash": value.request_hash,
        "frozen_tolerance_ledger": value.frozen_tolerance_ledger,
        "golden_records": value.golden_records,
        "acceptance_gates": value.acceptance_gates,
        "trusted_runtime_observation_hash": value.trusted_runtime_observation_hash,
        "trusted_runtime_status": value.trusted_runtime_status,
        "overall_status": value.overall_status,
        "blocker_codes": value.blocker_codes,
    }


def result_hash(value: Task169ReleaseResult) -> str:
    return sha256_domain_hex(RESULT_HASH_DOMAIN, result_preimage(value))


def result_id(hash_value: str) -> str:
    return str(uuid.uuid5(RESULT_ID_NAMESPACE, RESULT_ID_PREFIX + hash_value))


def blocked_hash(value: Task169ReleaseBlockedResult) -> str:
    return sha256_domain_hex(
        BLOCKED_HASH_DOMAIN,
        {
            "schema_version": value.schema_version,
            "release_version": value.release_version,
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
    "request_hash",
    "result_hash",
    "result_id",
]
