"""R26 negative injection with production captured fixture and exact error codes."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

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
from prototypes.v07_fast_solver_r2a_producer_origin_r26.production_certificate_witness import (
    build_production_certificate_from_captured_event,
)
from prototypes.v07_fast_solver_r2a_producer_origin_r26.q_predicate_independent_replay import (
    APPROVED_PROVIDER,
)

ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class InjectionCase:
    test_id: str
    tamper_type: str
    code_path: str
    expected_blocked_code: str
    runner: Callable[[], R2aVerificationOutcome | tuple[str, str]]


def _outcome_from_verify(evidence: R2aCertificateEvidence) -> R2aVerificationOutcome:
    return verify_r2a_certificate_evidence(evidence)


def _base_evidence() -> R2aCertificateEvidence:
    evidence, _ = build_captured_certificate_evidence(ROOT)
    return evidence


def _record(outcome: R2aVerificationOutcome | tuple[str, str], expected: str) -> dict[str, str]:
    if isinstance(outcome, tuple):
        status, detail = outcome
        actual = status if status != "BLOCKED" else detail
        passed = actual == expected or status == expected
        return {
            "EXPECTED_BLOCKED_CODE": expected,
            "ACTUAL_BLOCKED_CODE": str(actual),
            "PASS": "true" if passed else "false",
            "STATUS": status,
        }
    actual = outcome.blocked_code or outcome.status
    passed = actual == expected
    return {
        "EXPECTED_BLOCKED_CODE": expected,
        "ACTUAL_BLOCKED_CODE": str(actual),
        "PASS": "true" if passed else "false",
        "STATUS": outcome.status,
    }


def run_negative_injection_r26() -> list[dict[str, str]]:
    cases: list[InjectionCase] = []

    def forged_q7() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        event = dict(bundle["event"])
        q = dict(event["Q1_Q15"])
        q["Q7"] = False
        event["Q1_Q15"] = q
        body = {k: v for k, v in event.items() if k != "event_hash"}
        event["event_hash"] = canonical_sha256(body)
        cert = build_production_certificate_from_captured_event(event)
        return _outcome_from_verify(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "transient_events": (event,),
                    "outer_certificates": (cert,),
                }
            )
        )

    cases.append(
        InjectionCase(
            "R26-001",
            "FORGED_Q7_BOOLEAN",
            "verify_event_q_independent_replay",
            "R2A_Q7_PREDICATE_MISMATCH",
            forged_q7,
        )
    )

    def cert_hash_tamper() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["certificate_hash"] = "f" * 64
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R26-002",
            "CERTIFICATE_HASH_TAMPER",
            "_verify_certificate",
            "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH",
            cert_hash_tamper,
        )
    )

    def provider_version() -> R2aVerificationOutcome:
        evidence = _base_evidence()
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "provider_identity_version": "9.9.9"})
        )

    cases.append(
        InjectionCase(
            "R26-003",
            "PROVIDER_VERSION_TAMPER",
            "_verify_producer_identity",
            "R2A_PROVIDER_VERSION_MISMATCH",
            provider_version,
        )
    )

    def provider_identity_swap() -> R2aVerificationOutcome:
        evidence = _base_evidence()
        return _outcome_from_verify(
            R2aCertificateEvidence(
                **{**evidence.__dict__, "provider_identity_id": "FAKE-R2A-AUTHORITY"}
            )
        )

    cases.append(
        InjectionCase(
            "R26-004",
            "PROVIDER_IDENTITY_SWAP",
            "_verify_producer_identity",
            "R2A_PRODUCER_AUTHORITY_MISMATCH",
            provider_identity_swap,
        )
    )

    def endpoint_hash_mismatch() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        event = dict(bundle["event"])
        event["left_endpoint_request_hash"] = "dead" * 16
        body = {k: v for k, v in event.items() if k != "event_hash"}
        event["event_hash"] = canonical_sha256(body)
        cert = build_production_certificate_from_captured_event(event)
        return _outcome_from_verify(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "transient_events": (event,),
                    "outer_certificates": (cert,),
                }
            )
        )

    cases.append(
        InjectionCase(
            "R26-005",
            "ENDPOINT_REQUEST_HASH_MISMATCH",
            "_verify_endpoint_hashes",
            "R2A_LEFT_ENDPOINT_REQUEST_HASH_MISMATCH",
            endpoint_hash_mismatch,
        )
    )

    def branch_inconsistent() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["right_branch_used_endpoint_result_hash"] = "0" * 64
        body = {k: v for k, v in cert.items() if k != "certificate_hash"}
        cert["certificate_hash"] = canonical_sha256(body)
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R26-006",
            "BRANCH_ENDPOINT_BINDING_INCONSISTENT",
            "_verify_certificate",
            "R2A_CERTIFICATE_RIGHT_BRANCH_RESULT_MISMATCH",
            branch_inconsistent,
        )
    )

    def orphan_outer_trial() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = build_production_certificate_from_captured_event(
            bundle["event"], right_event_hash="0" * 64
        )
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R26-007",
            "OUTER_TRIAL_EVENT_REFERENCE_MISSING",
            "_verify_certificate",
            "R2A_CERTIFICATE_ORPHAN_EVENT_REFERENCE",
            orphan_outer_trial,
        )
    )

    def candidate_swap() -> R2aVerificationOutcome:
        evidence = _base_evidence()
        return _outcome_from_verify(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "candidate_id": "adeab5b1-a339-5eb3-aa66-011ffe49bac0",
                }
            )
        )

    cases.append(
        InjectionCase(
            "R26-008",
            "CANDIDATE_ID_SWAP",
            "_verify_event",
            "R2A_EVENT_CANDIDATE_ID_MISMATCH",
            candidate_swap,
        )
    )

    def mesh_mismatch() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        event = dict(bundle["event"])
        event["mesh_identity"] = "wrong-mesh-identity"
        body = {k: v for k, v in event.items() if k != "event_hash"}
        event["event_hash"] = canonical_sha256(body)
        cert = build_production_certificate_from_captured_event(event)
        return _outcome_from_verify(
            R2aCertificateEvidence(
                **{
                    **evidence.__dict__,
                    "mesh_identity": "expected-mesh",
                    "transient_events": (event,),
                    "outer_certificates": (cert,),
                }
            )
        )

    cases.append(
        InjectionCase(
            "R26-009",
            "MESH_IDENTITY_MISMATCH",
            "_verify_event",
            "R2A_EVENT_MESH_IDENTITY_MISMATCH",
            mesh_mismatch,
        )
    )

    def joint_cert_rehash() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        cert = dict(bundle["certificate"])
        cert["left_continuation_hash"] = "f" * 64
        cert["certificate_hash"] = bundle["certificate"]["certificate_hash"]
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "outer_certificates": (cert,)})
        )

    cases.append(
        InjectionCase(
            "R26-010",
            "JOINT_CERTIFICATE_REHASH_TAMPER",
            "_verify_certificate",
            "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH",
            joint_cert_rehash,
        )
    )

    def no_trigger_without_witness() -> tuple[str, str]:
        return evaluate_no_trigger_producer_witness(None, root=ROOT)

    cases.append(
        InjectionCase(
            "R26-011",
            "NO_TRIGGER_WITHOUT_PRODUCER_WITNESS",
            "evaluate_no_trigger_producer_witness",
            "FROZEN_EVIDENCE_INSUFFICIENT",
            no_trigger_without_witness,
        )
    )

    def missing_predicate_source() -> R2aVerificationOutcome:
        evidence = _base_evidence()
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "producer_replay_arguments": None})
        )

    cases.append(
        InjectionCase(
            "R26-012",
            "Q_REPLAY_WITHOUT_PRODUCER_ARGUMENTS",
            "verify_event_q_independent_replay",
            "R2A_PREDICATE_SOURCE_EVIDENCE_INSUFFICIENT",
            missing_predicate_source,
        )
    )

    def producer_args_provider_tamper() -> R2aVerificationOutcome:
        evidence, bundle = build_captured_certificate_evidence(ROOT)
        args = dict(bundle["producer_arguments"])
        args["provider_identity"] = {
            **APPROVED_PROVIDER,
            "provider_version": "7.0.0",
        }
        return _outcome_from_verify(
            R2aCertificateEvidence(**{**evidence.__dict__, "producer_replay_arguments": args})
        )

    cases.append(
        InjectionCase(
            "R26-013",
            "PRODUCER_ARGUMENT_PROVIDER_VERSION_TAMPER",
            "_verify_event",
            "R2A_PROVIDER_VERSION_MISMATCH",
            producer_args_provider_tamper,
        )
    )

    rows: list[dict[str, str]] = []
    for item in cases:
        outcome = item.runner()
        rows.append(
            {
                "TEST_ID": item.test_id,
                "TAMPER_TYPE": item.tamper_type,
                "CODE_PATH": item.code_path,
                **_record(outcome, item.expected_blocked_code),
            }
        )
    return rows
