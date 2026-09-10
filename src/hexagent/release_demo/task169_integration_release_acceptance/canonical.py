"""Canonical identity helpers for TASK-169 release acceptance."""

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

REQUEST_HASH_DOMAIN = "task169.release-acceptance.request.v1"
RESULT_HASH_DOMAIN = "task169.release-acceptance.result.v1"
BLOCKED_HASH_DOMAIN = "task169.release-acceptance.blocked.v1"

RESULT_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-000000000179")
RESULT_ID_PREFIX = "task169-release-result-v1::"
BLOCKED_ID_NAMESPACE = uuid.UUID("a1690000-0000-5000-8000-00000000017a")
BLOCKED_ID_PREFIX = "task169-release-blocked-v1::"


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
                "redistribution_status": case.redistribution_status,
                "normalized_input_identity": case.normalized_input_identity,
                "expected_result_identity": case.expected_result_identity,
                "approved_numeric_expectations": case.approved_numeric_expectations,
                "tolerance_class": case.tolerance_class,
                "reviewer_evidence_refs": case.reviewer_evidence_refs,
                "provenance_source_hash": case.provenance_source_hash,
                "selection_request_source_hash": case.selection_request.task168_result.result_hash,
                "ranking_policy_hash": case.selection_request.ranking_policy.canonical_hash,
            }
            for case in value.golden_cases
        ),
        "runtime_parity_evidence": value.runtime_parity_evidence,
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
        "overall_status": value.overall_status,
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
