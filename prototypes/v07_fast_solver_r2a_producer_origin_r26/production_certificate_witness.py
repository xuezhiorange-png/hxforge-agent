"""Build production-schema outer decision certificates from captured producer events."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_HASH,
    R2A_AUTHORITY_ID,
    R2A_CERTIFICATE_SCHEMA,
)


def build_production_certificate_from_captured_event(
    event: dict[str, Any],
    *,
    left_event_hash: str | None = None,
    right_event_hash: str | None = None,
) -> dict[str, Any]:
    """Project a minimal production certificate bound to one or two branch events."""
    left_hash = left_event_hash or str(event["event_hash"])
    right_hash = right_event_hash or str(event["event_hash"])
    certificate: dict[str, Any] = {
        "schema_version": R2A_CERTIFICATE_SCHEMA,
        "authority_id": R2A_AUTHORITY_ID,
        "authority_hash": R2A_AUTHORITY_HASH,
        "candidate_id": event["candidate_id"],
        "candidate_hash": event["candidate_hash"],
        "mesh_identity": event["mesh_identity"],
        "mesh_subdivisions": event["mesh_subdivisions"],
        "shooting_enthalpy_j_kg": event["shooting_enthalpy_j_kg"],
        "outer_iteration": event["outer_iteration"],
        "trigger_support_id": event["physical_support_id"],
        "left_endpoint_event_hashes": [left_hash],
        "right_endpoint_event_hashes": [right_hash],
        "left_branch_used_endpoint_request_hash": event["left_endpoint_request_hash"],
        "left_branch_used_endpoint_result_hash": event["left_endpoint_result_hash"],
        "right_branch_used_endpoint_request_hash": event["right_endpoint_request_hash"],
        "right_branch_used_endpoint_result_hash": event["right_endpoint_result_hash"],
        "left_event_left_endpoint_request_hash": event["left_endpoint_request_hash"],
        "left_event_right_endpoint_request_hash": event["right_endpoint_request_hash"],
        "right_event_left_endpoint_request_hash": event["left_endpoint_request_hash"],
        "right_event_right_endpoint_request_hash": event["right_endpoint_request_hash"],
        "left_event_left_endpoint_result_hash": event["left_endpoint_result_hash"],
        "left_event_right_endpoint_result_hash": event["right_endpoint_result_hash"],
        "right_event_left_endpoint_result_hash": event["left_endpoint_result_hash"],
        "right_event_right_endpoint_result_hash": event["right_endpoint_result_hash"],
        "left_continuation_hash": canonical_sha256(
            {"branch": "left", "event_hash": left_hash}
        ),
        "right_continuation_hash": canonical_sha256(
            {"branch": "right", "event_hash": right_hash}
        ),
        "left_outer_classification": "VALID_CELL_EVALUATION",
        "right_outer_classification": "VALID_CELL_EVALUATION",
        "left_terminal_residual_k": "0",
        "right_terminal_residual_k": "0",
        "left_outer_action": "CONTINUE_OUTER_SEARCH",
        "right_outer_action": "CONTINUE_OUTER_SEARCH",
        "left_midpoint_collapse_disposition": "UNCHANGED",
        "right_midpoint_collapse_disposition": "UNCHANGED",
        "midpoint_collapse_disposition_invariant": True,
        "representative_branch_used_to_decide_outer_action": False,
        "representative_endpoint_after_invariance": event.get("representative_endpoint", "LEFT"),
    }
    certificate["certificate_hash"] = canonical_sha256(certificate)
    return certificate
