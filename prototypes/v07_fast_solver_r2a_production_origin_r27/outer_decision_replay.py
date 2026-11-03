"""Replay production outer-decision certificate fields against pinned producer trace."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256


def _replay_certificate_hash(certificate: dict[str, Any]) -> str:
    body = {key: value for key, value in certificate.items() if key != "certificate_hash"}
    return canonical_sha256(body)


def verify_outer_decision_certificate_replay(
    certificate: dict[str, Any],
    *,
    outer_trial_provenance: dict[str, Any] | None,
) -> tuple[bool, str]:
    if certificate.get("certificate_hash") != _replay_certificate_hash(certificate):
        return False, "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH"
    left_events = certificate.get("left_endpoint_event_hashes") or []
    right_events = certificate.get("right_endpoint_event_hashes") or []
    if not left_events or not right_events:
        return False, "R2A_CERTIFICATE_BRANCH_EVENT_MISSING"
    if left_events == right_events and left_events[0] == right_events[0]:
        return False, "R2A_PRODUCTION_BRANCH_EVENT_COLLAPSE"
    if outer_trial_provenance is not None:
        pinned_cert_hashes = outer_trial_provenance.get("outer_decision_certificate_hashes") or []
        if certificate.get("certificate_hash") not in pinned_cert_hashes:
            return False, "R2A_PRODUCTION_CERTIFICATE_NOT_IN_PINNED_TRACE"
        pinned_event_hashes = set(
            outer_trial_provenance.get("transient_provider_enclosure_event_hashes") or []
        )
        for ref in (*left_events, *right_events):
            if ref not in pinned_event_hashes:
                return False, "R2A_PRODUCTION_EVENT_NOT_IN_PINNED_TRACE"
    if not certificate.get("left_continuation_hash") or not certificate.get(
        "right_continuation_hash"
    ):
        return False, "R2A_CERTIFICATE_CONTINUATION_HASH_MISSING"
    if outer_trial_provenance is not None:
        action_seq = outer_trial_provenance.get("outer_decision_action_sequence") or []
        left_action = certificate.get("left_outer_action")
        right_action = certificate.get("right_outer_action")
        if left_action not in action_seq or right_action not in action_seq:
            return False, "R2A_PRODUCTION_OUTER_ACTION_NOT_IN_TRACE"
    if certificate.get("midpoint_collapse_disposition_invariant") is not True:
        return False, "R2A_CERTIFICATE_MIDPOINT_INVARIANT_MISMATCH"
    if certificate.get("left_midpoint_collapse_disposition") != certificate.get(
        "right_midpoint_collapse_disposition"
    ):
        return False, "R2A_PRODUCTION_BRANCH_INVARIANCE_MISMATCH"
    for side, events, classification in (
        ("left", left_events, certificate.get("left_outer_classification")),
        ("right", right_events, certificate.get("right_outer_classification")),
    ):
        expected = canonical_sha256(
            {
                "classification": classification,
                "mesh_result_hash": None,
                "event_hashes": events,
                "fallback_disabled_after_trigger": True,
            }
        )
        actual = certificate.get(f"{side}_continuation_hash")
        if actual != expected and classification != "VALID_TRAJECTORY":
            return False, f"R2A_PRODUCTION_{side.upper()}_CONTINUATION_HASH_MISMATCH"
        if classification == "VALID_TRAJECTORY":
            return False, "R2A_PRODUCTION_MESH_RUN_HASH_REQUIRED_FOR_CONTINUATION"
    return True, "PASS"
