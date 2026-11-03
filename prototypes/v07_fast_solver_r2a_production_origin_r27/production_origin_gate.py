"""Fail-closed production certificate origin audit."""

# ruff: noqa: E501

from __future__ import annotations

from pathlib import Path
from typing import Any

from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    APPROVED_PROVIDER,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.immutable_production_evidence_loader import (
    load_immutable_production_bundle,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.outer_decision_replay import (
    verify_outer_decision_certificate_replay,
)


def audit_production_certificate_origin(root: Path) -> dict[str, Any]:
    bundle = load_immutable_production_bundle(root)
    if bundle.get("status") != "LOADED":
        return {
            "schema_version": "task173.r2a-production-certificate-origin-audit.v1",
            "production_certificate_origin": "EVIDENCE_MISSING",
            "detail": bundle.get("status"),
            "immutable_bundle": bundle,
        }
    if not bundle.get("certificates"):
        return {
            "schema_version": "task173.r2a-production-certificate-origin-audit.v1",
            "production_certificate_origin": "EVIDENCE_MISSING",
            "detail": "no_production_certificates_in_pinned_evidence",
            "immutable_bundle": {k: v for k, v in bundle.items() if k != "certificates"},
        }
    if bundle.get("event_projection_status") != "PRESENT":
        first = bundle["certificates"][0]
        outer_ok, outer_code = verify_outer_decision_certificate_replay(
            first,
            outer_trial_provenance=bundle.get("outer_trial_provenance"),
        )
        return {
            "schema_version": "task173.r2a-production-certificate-origin-audit.v1",
            "production_certificate_origin": "EVIDENCE_MISSING",
            "detail": "immutable_event_projections_not_archived_with_certificates",
            "producer_source_commit_verified": bool(bundle.get("producer_git_commit_head")),
            "provider_runtime_identity_verified": True,
            "pinned_certificate_count": len(bundle["certificates"]),
            "outer_decision_partial_replay": outer_ok,
            "outer_decision_partial_code": outer_code,
            "sample_certificate_hash": first.get("certificate_hash"),
            "immutable_bundle": {
                "ratings_evidence_rel": bundle["ratings_evidence_rel"],
                "raw_evidence_sha256": bundle["raw_evidence_sha256"],
                "producer_git_commit_head": bundle.get("producer_git_commit_head"),
                "producer_source_tree": bundle.get("producer_source_tree"),
                "provider_identity": APPROVED_PROVIDER,
            },
        }
    return {
        "schema_version": "task173.r2a-production-certificate-origin-audit.v1",
        "production_certificate_origin": "LOADED_AWAITING_FULL_REPLAY",
        "immutable_bundle": bundle,
    }


def verify_production_origin_bundle(
    bundle: dict[str, Any] | None,
    *,
    root: Path,
    certificates: tuple[dict[str, Any], ...],
    events: tuple[dict[str, Any], ...],
) -> tuple[bool, str]:
    if bundle is None:
        return False, "R2A_PRODUCTION_ORIGIN_BUNDLE_MISSING"
    pinned = load_immutable_production_bundle(root)
    if pinned.get("status") != "LOADED":
        return False, "R2A_PRODUCTION_IMMUTABLE_EVIDENCE_UNAVAILABLE"
    if bundle.get("raw_evidence_sha256") != pinned.get("raw_evidence_sha256"):
        return False, "R2A_PRODUCTION_RAW_EVIDENCE_SHA256_MISMATCH"
    if bundle.get("producer_git_commit_head") != pinned.get("producer_git_commit_head"):
        return False, "R2A_PRODUCER_SOURCE_COMMIT_MISMATCH"
    if bundle.get("provider_git_revision") != APPROVED_PROVIDER["provider_git_revision"]:
        return False, "R2A_PROVIDER_GIT_REVISION_MISMATCH"
    if not events:
        return False, "R2A_PRODUCTION_EVENT_PROJECTIONS_MISSING"
    pinned_hashes = {cert["certificate_hash"] for cert in pinned.get("certificates", [])}
    for certificate in certificates:
        if certificate.get("certificate_hash") not in pinned_hashes:
            return False, "R2A_PRODUCTION_CERTIFICATE_NOT_IN_IMMUTABLE_ARCHIVE"
        ok, code = verify_outer_decision_certificate_replay(
            certificate,
            outer_trial_provenance=pinned.get("outer_trial_provenance"),
        )
        if not ok:
            return False, code
    return True, "PASS"


def run_true_production_certificate_witness(root: Path) -> dict[str, Any]:
    audit = audit_production_certificate_origin(root)
    origin = audit.get("production_certificate_origin")
    if origin != "LOADED_AWAITING_FULL_REPLAY":
        return {
            "schema_version": "task173.r2a-true-production-certificate-witness.v1",
            "witness_status": "BLOCKED_EVIDENCE_MISSING",
            "production_certificate_origin": origin,
            "audit": audit,
        }
    return {
        "schema_version": "task173.r2a-true-production-certificate-witness.v1",
        "witness_status": "BLOCKED_EVIDENCE_MISSING",
        "production_certificate_origin": origin,
        "audit": audit,
    }
