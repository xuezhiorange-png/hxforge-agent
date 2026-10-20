"""Full verifier path: production event + certificate + Q1-Q15 independent replay."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_certificate_verifier import (
    R2aCertificateEvidence,
    verify_r2a_certificate_evidence,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_ID,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.captured_producer_fixture import (
    build_captured_candidate_b_producer_arguments,
    emit_production_r2a_event,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_origin_verification import (
    build_runtime_producer_origin,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.production_certificate_witness import (
    build_production_certificate_from_captured_event,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    APPROVED_PROVIDER,
)


def build_captured_certificate_evidence(root: Path) -> tuple[R2aCertificateEvidence, dict[str, Any]]:
    args = build_captured_candidate_b_producer_arguments(root)
    event = emit_production_r2a_event(root)
    certificate = build_production_certificate_from_captured_event(event)
    captured = args["captured"]
    evidence = R2aCertificateEvidence(
        candidate_id=str(captured["candidate_id"]),
        candidate_hash=str(captured["candidate_hash"]),
        rating_request_hash="CAPTURED_PRECISION_FLOOR_RATING_REQUEST_NOT_PINNED",
        task174_result_hash="CAPTURED_PRECISION_FLOOR_TASK174_NOT_PINNED",
        source_result_hash="CAPTURED_PRECISION_FLOOR_SOURCE_NOT_PINNED",
        mesh_n=int(event["mesh_subdivisions"]),
        mesh_identity=str(event["mesh_identity"]),
        mesh_result_hash=str(event["mesh_identity"]),
        provider_identity_id=R2A_AUTHORITY_ID,
        provider_identity_version=APPROVED_PROVIDER["provider_version"],
        transient_events=(event,),
        outer_certificates=(certificate,),
        producer_replay_arguments=args,
        producer_origin=build_runtime_producer_origin(root),
    )
    return evidence, {"event": event, "certificate": certificate, "producer_arguments": args}


def run_full_certificate_positive_witness(root: Path) -> dict[str, Any]:
    evidence, bundle = build_captured_certificate_evidence(root)
    outcome = verify_r2a_certificate_evidence(evidence)
    return {
        "schema_version": "task173.r2a-certificate-positive-witness.v1",
        "source_evidence_rel": bundle["producer_arguments"]["evidence_rel"],
        "verifier_status": outcome.status,
        "blocked_code": outcome.blocked_code,
        "q_predicate_gate": outcome.q_predicate_gate,
        "certificate_hash_replay": outcome.certificate_hash_replay,
        "provider_identity_binding": outcome.provider_identity_binding,
        "event_hash": bundle["event"]["event_hash"],
        "certificate_hash": bundle["certificate"]["certificate_hash"],
        "witness_status": "PASS" if outcome.status == "CERTIFICATE_PRESENT_VERIFIED" else "BLOCKED",
        "result_hash": outcome.result_hash,
    }
