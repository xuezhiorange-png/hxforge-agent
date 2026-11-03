"""R27 negative injection for production certificate origin fail-closed gates."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_certificate_verifier import (
    R2aCertificateEvidence,
    R2aVerificationOutcome,
    verify_r2a_certificate_evidence,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.full_certificate_positive_witness import (
    build_captured_certificate_evidence,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_non_trigger_witness import (
    evaluate_no_trigger_producer_witness,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_origin_verification import (
    build_runtime_producer_origin,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.production_certificate_witness import (
    build_contract_fixture_certificate_from_captured_event,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.certificate_origin import (
    FIXTURE_ORIGIN_MARK,
    PRODUCTION_ORIGIN_MARK,
)
from prototypes.v07_fast_solver_r2a_production_origin_r27.immutable_production_evidence_loader import (
    load_immutable_production_bundle,
)

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class InjectionCase:
    test_id: str
    tamper_type: str
    expected_blocked_code: str
    runner: Callable[[], Any]


def _record(actual: Any, expected: str) -> dict[str, str]:
    if isinstance(actual, tuple):
        code = actual[1] if actual[0] != "BLOCKED" else actual[1]
        if actual[0] in {"FROZEN_EVIDENCE_INSUFFICIENT", "NO_TRIGGER_PROVEN"}:
            code = actual[0]
        passed = code == expected or actual[0] == expected
        return {
            "EXPECTED_BLOCKED_CODE": expected,
            "ACTUAL_BLOCKED_CODE": str(code),
            "PASS": "true" if passed else "false",
            "STATUS": str(actual[0]),
        }
    blocked = actual.blocked_code or actual.status
    passed = blocked == expected
    return {
        "EXPECTED_BLOCKED_CODE": expected,
        "ACTUAL_BLOCKED_CODE": str(blocked),
        "PASS": "true" if passed else "false",
        "STATUS": actual.status,
    }


def run_negative_injection_r27() -> list[dict[str, str]]:
    cases: list[InjectionCase] = []

    def caller_rehashed_certificate() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert.pop("certificate_origin_class", None)
        cert.pop("contract_fixture_reconstruction", None)
        cert["left_outer_action"] = "TAMPERED"
        body = {k: v for k, v in cert.items() if k != "certificate_hash"}
        cert["certificate_hash"] = canonical_sha256(body)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "outer_certificates": (cert,),
                    "certificate_provenance": None,
                }
            )
        )

    cases.append(
        InjectionCase(
            "R27-001",
            "CALLER_REHASHED_CERTIFICATE",
            "R2A_PRODUCTION_CERTIFICATE_ORIGIN_MISSING",
            caller_rehashed_certificate,
        )
    )

    def collapsed_branch_events() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        event = bundle["event"]
        cert = build_contract_fixture_certificate_from_captured_event(event)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "outer_certificates": (cert,),
                    "certificate_provenance": FIXTURE_ORIGIN_MARK,
                }
            )
        )

    cases.append(
        InjectionCase(
            "R27-002",
            "COLLAPSED_BRANCH_EVENTS",
            "CONTRACT_FIXTURE_PASS",
            collapsed_branch_events,
        )
    )

    def tamper_action_rehash() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["left_outer_action"] = "TAMPERED_ACTION"
        body = {k: v for k, v in cert.items() if k != "certificate_hash"}
        cert["certificate_hash"] = canonical_sha256(body)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R27-003",
            "OUTER_ACTION_TAMPER_REHASH",
            "CONTRACT_FIXTURE_PASS",
            tamper_action_rehash,
        )
    )

    def stale_certificate_hash() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["right_continuation_hash"] = "f" * 64
        cert["certificate_hash"] = bundle["certificate"]["certificate_hash"]
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R27-004",
            "JOINT_CERTIFICATE_REHASH_TAMPER",
            "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH",
            stale_certificate_hash,
        )
    )

    def forged_continuation() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["left_continuation_hash"] = "0" * 64
        body = {k: v for k, v in cert.items() if k != "certificate_hash"}
        cert["certificate_hash"] = canonical_sha256(body)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R27-005",
            "FORGED_CONTINUATION_HASH",
            "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH",
            forged_continuation,
        )
    )

    def forged_terminal_residual() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["left_terminal_residual_k"] = "999"
        body = {k: v for k, v in cert.items() if k != "certificate_hash"}
        cert["certificate_hash"] = canonical_sha256(body)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R27-006",
            "FORGED_TERMINAL_RESIDUAL",
            "CONTRACT_FIXTURE_PASS",
            forged_terminal_residual,
        )
    )

    def producer_commit_swap() -> tuple[bool, str]:
        origin = build_runtime_producer_origin(ROOT)
        origin["git_commit_head"] = "0" * 40
        from prototypes.v07_fast_solver_r2a_producer_origin_r26.producer_origin_verification import (
            verify_producer_origin_record,
        )

        return verify_producer_origin_record(origin, root=ROOT)

    cases.append(
        InjectionCase(
            "R27-007",
            "PRODUCER_COMMIT_SWAP",
            "R2A_PRODUCER_GIT_HEAD_RUNTIME_MISMATCH",
            producer_commit_swap,
        )
    )

    def provider_revision_swap() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        args = dict(bundle["producer_arguments"])
        args["provider_identity"] = {
            **args["provider_identity"],
            "provider_git_revision": "0" * 40,
        }
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(**{**evidence.__dict__, "producer_replay_arguments": args})
        )

    cases.append(
        InjectionCase(
            "R27-008",
            "PROVIDER_GIT_REVISION_SWAP",
            "R2A_PROVIDER_GIT_REVISION_MISMATCH",
            provider_revision_swap,
        )
    )

    def raw_sha_mismatch() -> tuple[bool, str]:
        pinned = load_immutable_production_bundle(ROOT)
        bundle = {
            "raw_evidence_sha256": "f" * 64,
            "producer_git_commit_head": pinned.get("producer_git_commit_head"),
            "provider_git_revision": "ae81610e7d23efc57f9d051c8e70a4d66e87537f",
        }
        from prototypes.v07_fast_solver_r2a_production_origin_r27.production_origin_gate import (
            verify_production_origin_bundle,
        )

        _, b = build_captured_certificate_evidence(ROOT)
        return verify_production_origin_bundle(
            bundle,
            root=ROOT,
            certificates=(b["certificate"],),
            events=(b["event"],),
        )

    cases.append(
        InjectionCase(
            "R27-009",
            "RAW_EVIDENCE_SHA256_MISMATCH",
            "R2A_PRODUCTION_RAW_EVIDENCE_SHA256_MISMATCH",
            raw_sha_mismatch,
        )
    )

    def forged_no_trigger() -> tuple[str, str]:
        return evaluate_no_trigger_producer_witness(
            {
                "candidate_id": "x",
                "rating_request_hash": "y",
                "mesh_n": 32,
                "mesh_identity": "m",
                "producer_authority_id": "a",
                "producer_software_version": "1",
                "provider_identity_id": "p",
                "provider_identity_version": "8.0.0",
                "trigger_detection_path_executed": True,
                "outer_trial_identity": "t",
                "outer_trial_count": 1,
                "outer_trial_coverage_complete": True,
                "archived_trigger_event_absent": True,
                "raw_evidence_rel": "missing.json",
                "raw_evidence_sha256": "0" * 64,
                "producer_git_commit_head": "0" * 40,
                "producer_source_tree": "0" * 40,
                "producer_trace_archive_sha256": "0" * 64,
                "witness_canonical_hash": "0" * 64,
            },
            root=ROOT,
        )

    cases.append(
        InjectionCase(
            "R27-010",
            "FORGED_NO_TRIGGER_WITNESS",
            "FROZEN_EVIDENCE_INSUFFICIENT",
            forged_no_trigger,
        )
    )

    def claims_production_without_bundle() -> R2aVerificationOutcome:
        evidence, _ = build_captured_certificate_evidence(ROOT)
        return verify_r2a_certificate_evidence(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "certificate_provenance": PRODUCTION_ORIGIN_MARK,
                    "production_origin_bundle": None,
                }
            )
        )

    cases.append(
        InjectionCase(
            "R27-011",
            "PRODUCTION_CLAIM_WITHOUT_ORIGIN_BUNDLE",
            "R2A_PRODUCTION_ORIGIN_BUNDLE_MISSING",
            claims_production_without_bundle,
        )
    )

    rows: list[dict[str, str]] = []
    for item in cases:
        outcome = item.runner()
        rows.append(
            {
                "TEST_ID": item.test_id,
                "TAMPER_TYPE": item.tamper_type,
                **_record(outcome, item.expected_blocked_code),
            }
        )
    return rows
