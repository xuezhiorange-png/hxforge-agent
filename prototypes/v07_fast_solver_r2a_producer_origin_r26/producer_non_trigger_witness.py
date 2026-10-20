"""Requirements for NO_TRIGGER_PROVEN — never inferred from missing R2A artifacts."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256

REQUIRED_NON_TRIGGER_FIELDS: tuple[str, ...] = (
    "candidate_id",
    "rating_request_hash",
    "mesh_n",
    "mesh_identity",
    "producer_authority_id",
    "producer_software_version",
    "provider_identity_id",
    "provider_identity_version",
    "trigger_detection_path_executed",
    "outer_trial_identity",
    "outer_trial_count",
    "outer_trial_coverage_complete",
    "archived_trigger_event_absent",
    "raw_evidence_sha256",
)


def evaluate_no_trigger_producer_witness(
    witness: dict[str, Any] | None,
) -> tuple[str, str]:
    """Return (status, detail). Only returns NO_TRIGGER_PROVEN with a complete witness."""
    if witness is None:
        return (
            "FROZEN_EVIDENCE_INSUFFICIENT",
            "no_producer_non_trigger_witness_supplied",
        )
    missing = [key for key in REQUIRED_NON_TRIGGER_FIELDS if not witness.get(key)]
    if missing:
        return (
            "FROZEN_EVIDENCE_INSUFFICIENT",
            f"non_trigger_witness_incomplete:{','.join(missing)}",
        )
    if witness.get("archived_trigger_event_absent") is not True:
        return (
            "FROZEN_EVIDENCE_INSUFFICIENT",
            "archived_trigger_event_absent_not_proven",
        )
    if witness.get("outer_trial_coverage_complete") is not True:
        return (
            "FROZEN_EVIDENCE_INSUFFICIENT",
            "outer_trial_coverage_not_proven",
        )
    if witness.get("trigger_detection_path_executed") is not True:
        return (
            "FROZEN_EVIDENCE_INSUFFICIENT",
            "trigger_detection_path_not_proven",
        )
    digest = canonical_sha256(
        {key: witness[key] for key in REQUIRED_NON_TRIGGER_FIELDS if key in witness}
    )
    if witness.get("witness_canonical_hash") and witness["witness_canonical_hash"] != digest:
        return ("BLOCKED", "NON_TRIGGER_WITNESS_HASH_MISMATCH")
    return ("NO_TRIGGER_PROVEN", "producer_trace_documents_no_trigger")
