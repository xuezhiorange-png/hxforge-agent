"""Independently recompute R2A Q1-Q15 using production Task173 producer code."""

# ruff: noqa: E501

from __future__ import annotations

from typing import Any

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task173_integrated_rating import service as t173
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    Q_PREDICATE_KEYS,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.captured_producer_fixture import (
    build_captured_candidate_b_producer_arguments,
    emit_production_r2a_event,
)

APPROVED_PROVIDER = {
    "provider": "CoolProp",
    "provider_version": "8.0.0",
    "provider_git_revision": "ae81610e7d23efc57f9d051c8e70a4d66e87537f",
}


def recompute_q1_q15_from_producer_arguments(args: dict[str, Any]) -> dict[str, bool] | None:
    event = t173._candidate_provider_enclosure_event(
        context=args["context"],
        control=args["control"],
        support=args["support"],
        left=args["left"],
        right=args["right"],
        trials=args["trials"],
    )
    if event is None:
        return None
    q = event.get("Q1_Q15")
    if not isinstance(q, dict):
        return None
    return {key: bool(q.get(key)) for key in Q_PREDICATE_KEYS}


def verify_event_q_independent_replay(
    event: dict[str, Any],
    *,
    producer_arguments: dict[str, Any] | None,
) -> tuple[bool, str, dict[str, bool] | None]:
    if producer_arguments is None:
        return False, "R2A_PREDICATE_SOURCE_EVIDENCE_INSUFFICIENT", None
    fresh = recompute_q1_q15_from_producer_arguments(producer_arguments)
    if fresh is None:
        return False, "R2A_Q_RECOMPUTE_PRODUCER_RETURNED_NONE", None
    declared = event.get("Q1_Q15")
    if not isinstance(declared, dict):
        return False, "R2A_Q_PREDICATES_MISSING", fresh
    for key in Q_PREDICATE_KEYS:
        if declared.get(key) is True and not fresh.get(key):
            return False, f"R2A_FORGED_{key}_PASS", fresh
        if declared.get(key) is False and fresh.get(key):
            return False, f"R2A_{key}_PREDICATE_MISMATCH", fresh
    if not all(fresh.values()):
        return False, "R2A_Q_RECOMPUTE_NOT_ALL_PASS", fresh
    return True, "PASS", fresh


def verify_producer_provider_identity(event: dict[str, Any]) -> tuple[bool, str]:
    for side in ("left", "right"):
        if not isinstance(event.get(f"endpoint_request_projection_{side}"), dict):
            return False, "R2A_ENDPOINT_PROJECTION_MISSING"
        if not isinstance(event.get(f"endpoint_result_projection_{side}"), dict):
            return False, "R2A_ENDPOINT_PROJECTION_MISSING"
    coords = event.get("provider_coordinates")
    if not isinstance(coords, list) or not coords:
        return False, "R2A_PROVIDER_COORDINATES_MISSING"
    return True, "PASS"


def run_captured_positive_witness(root: Any) -> dict[str, Any]:
    from pathlib import Path

    root_path = Path(root)
    args = build_captured_candidate_b_producer_arguments(root_path)
    event = emit_production_r2a_event(root_path)
    ok, code, recomputed = verify_event_q_independent_replay(
        event, producer_arguments=args
    )
    event_hash_replay = event["event_hash"] == canonical_sha256(
        {k: v for k, v in event.items() if k != "event_hash"}
    )
    tampered = dict(event)
    tampered_q = dict(tampered["Q1_Q15"])
    tampered_q["Q2"] = False
    tampered["Q1_Q15"] = tampered_q
    tamper_ok, tamper_code, _ = verify_event_q_independent_replay(
        tampered, producer_arguments=args
    )
    return {
        "schema_version": "task173.r2a-positive-producer-witness.v1",
        "source_evidence_rel": args["evidence_rel"],
        "event_hash_replay": event_hash_replay,
        "q_independent_replay": ok,
        "q_independent_replay_code": code,
        "recomputed_q_predicates": recomputed,
        "declared_q_predicates": event.get("Q1_Q15"),
        "tamper_q2_blocked": not tamper_ok
        and tamper_code in {"R2A_Q2_PREDICATE_MISMATCH", "R2A_FORGED_Q2_PASS"},
        "tamper_blocked_code": tamper_code if not tamper_ok else None,
        "producer_provider_identity": args["provider_identity"],
        "witness_status": "PASS" if ok and event_hash_replay and not tamper_ok else "BLOCKED",
    }
