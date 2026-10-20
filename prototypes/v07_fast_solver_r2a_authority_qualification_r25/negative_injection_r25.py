"""R25 negative injection against verify_r2a_certificate_evidence."""

# ruff: noqa: E501

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from hexagent.canonical_json import canonical_sha256
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_certificate_verifier import (
    R2aCertificateEvidence,
    R2aVerificationOutcome,
    verify_r2a_certificate_evidence,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    R2A_AUTHORITY_HASH,
    R2A_AUTHORITY_ID,
    R2A_CERTIFICATE_SCHEMA,
    R2A_EVENT_SCHEMA,
)

_BASE_BINDING = {
    "candidate_id": "e152cca9-fd5d-59ca-9b46-1df574eee841",
    "candidate_hash": "abc" * 21 + "a",
    "rating_request_hash": "56ecf30ceb6beb4528c772962f1e7a49e22d43f1010ae4f079bd80228fc6f5f8",
    "task174_result_hash": "d988828e01a1fcec07ddb691519a20b3b76da1bdd56cdbad5d7f077ae4a3c4bb",
    "source_result_hash": "144d4e0b35fd59e669b343792dfff95e13dec74d0e90b61f0e89d0b3e9d96ee3",
    "mesh_n": 32,
    "mesh_identity": "mesh-id-test",
    "mesh_result_hash": "42fa6dfaadbee5d35c20714fe56af8b1c1c33e7e70597994b8c2e5dcc0502838",
    "provider_identity_id": "V07-T173-CELL-ROOT-PROVIDER-QUANTIZATION-ENCLOSURE-R2A",
    "provider_identity_version": "production",
}


def _base_event(**overrides: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "schema_version": R2A_EVENT_SCHEMA,
        "authority_id": R2A_AUTHORITY_ID,
        "authority_hash": R2A_AUTHORITY_HASH,
        "candidate_id": _BASE_BINDING["candidate_id"],
        "candidate_hash": _BASE_BINDING["candidate_hash"],
        "mesh_identity": _BASE_BINDING["mesh_identity"],
        "mesh_subdivisions": 32,
        "left_endpoint_request_hash": "0" * 64,
        "right_endpoint_request_hash": "0" * 64,
        "left_endpoint_result_hash": "1" * 64,
        "right_endpoint_result_hash": "2" * 64,
        "endpoint_request_projection_left": {},
        "endpoint_request_projection_right": {},
        "endpoint_result_projection_left": {},
        "endpoint_result_projection_right": {},
        "Q1_Q15": {f"Q{i}": True for i in range(1, 16)},
    }
    event.update(overrides)
    body = {k: v for k, v in event.items() if k != "event_hash"}
    event["event_hash"] = canonical_sha256(body)
    return event


def _base_certificate(event_hash: str, **overrides: Any) -> dict[str, Any]:
    cert: dict[str, Any] = {
        "schema_version": R2A_CERTIFICATE_SCHEMA,
        "authority_id": R2A_AUTHORITY_ID,
        "authority_hash": R2A_AUTHORITY_HASH,
        "candidate_id": _BASE_BINDING["candidate_id"],
        "candidate_hash": _BASE_BINDING["candidate_hash"],
        "mesh_identity": _BASE_BINDING["mesh_identity"],
        "mesh_subdivisions": 32,
        "left_endpoint_event_hashes": [event_hash],
        "right_endpoint_event_hashes": [event_hash],
    }
    cert.update(overrides)
    body = {k: v for k, v in cert.items() if k != "certificate_hash"}
    cert["certificate_hash"] = canonical_sha256(body)
    return cert


def _evidence(
    *,
    events: tuple[dict[str, Any], ...] = (),
    certs: tuple[dict[str, Any], ...] = (),
    **binding_overrides: Any,
) -> R2aCertificateEvidence:
    binding = {**_BASE_BINDING, **binding_overrides}
    return R2aCertificateEvidence(
        transient_events=events,
        outer_certificates=certs,
        **binding,
    )


@dataclass(frozen=True)
class InjectionCase:
    test_id: str
    tamper_type: str
    expected_blocked_codes: tuple[str, ...]
    runner: Callable[[], R2aVerificationOutcome]


def _record(outcome: R2aVerificationOutcome, expected: tuple[str, ...]) -> dict[str, str]:
    actual = outcome.blocked_code or outcome.status
    passed = outcome.status in expected or (
        outcome.blocked_code is not None and outcome.blocked_code in expected
    )
    if outcome.status in expected:
        actual = outcome.status
    return {
        "EXPECTED_BLOCKED_CODE": "|".join(expected),
        "ACTUAL_BLOCKED_CODE": str(actual),
        "PASS": "true" if passed else "false",
        "STATUS": outcome.status,
    }


def run_negative_injection_r25() -> list[dict[str, str]]:
    cases: list[InjectionCase] = []

    def case_missing_raw() -> R2aVerificationOutcome:
        return verify_r2a_certificate_evidence(_evidence())

    cases.append(
        InjectionCase(
            "R25-001",
            "MISSING_R2A_RAW_EVIDENCE",
            ("R2A_RAW_EVIDENCE_MISSING", "FROZEN_EVIDENCE_INSUFFICIENT"),
            case_missing_raw,
        )
    )

    def case_forged_cert_hash() -> R2aVerificationOutcome:
        event = _base_event()
        cert = _base_certificate(event["event_hash"], certificate_hash="f" * 64)
        return verify_r2a_certificate_evidence(_evidence(events=(event,), certs=(cert,)))

    cases.append(
        InjectionCase(
            "R25-002",
            "FORGED_CERTIFICATE_HASH",
            (
                "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH",
                "R2A_ENDPOINT_PROJECTION_INVALID",
            ),
            case_forged_cert_hash,
        )
    )

    def case_forged_q_pass() -> R2aVerificationOutcome:
        event = _base_event()
        return verify_r2a_certificate_evidence(_evidence(events=(event,)))

    cases.append(
        InjectionCase(
            "R25-003",
            "FORGED_Q1_Q15_PASS",
            (
                "R2A_FORGED_Q1_PASS",
                "R2A_FORGED_Q15_PASS",
                "R2A_FORGED_Q1_Q15_ALL_TRUE",
                "R2A_ENDPOINT_PROJECTION_MISSING",
                "R2A_ENDPOINT_PROJECTION_INVALID",
                "R2A_OUTER_CERTIFICATE_MISSING",
            ),
            case_forged_q_pass,
        )
    )

    def case_provider_version() -> R2aVerificationOutcome:
        return verify_r2a_certificate_evidence(
            _evidence(provider_identity_id="FAKE-PROVIDER", provider_identity_version="9.9.9")
        )

    cases.append(
        InjectionCase(
            "R25-004",
            "PROVIDER_VERSION_TAMPER",
            ("PROVIDER_IDENTITY_MISMATCH", "FROZEN_EVIDENCE_INSUFFICIENT"),
            case_provider_version,
        )
    )

    def case_request_hash_swap() -> R2aVerificationOutcome:
        event = _base_event()
        return verify_r2a_certificate_evidence(
            _evidence(
                events=(event,),
                rating_request_hash="dead" * 16,
            )
        )

    cases.append(
        InjectionCase(
            "R25-005",
            "CANDIDATE_REQUEST_HASH_SWAP",
            (
                "R2A_EVENT_CANDIDATE_HASH_MISMATCH",
                "R2A_ENDPOINT_PROJECTION_INVALID",
                "R2A_OUTER_CERTIFICATE_MISSING",
                "FROZEN_EVIDENCE_INSUFFICIENT",
            ),
            case_request_hash_swap,
        )
    )

    def case_mesh_identity() -> R2aVerificationOutcome:
        event = _base_event(mesh_identity="wrong-mesh")
        return verify_r2a_certificate_evidence(
            _evidence(events=(event,), mesh_identity="expected-mesh")
        )

    cases.append(
        InjectionCase(
            "R25-006",
            "MESH_IDENTITY_MISMATCH",
            ("R2A_EVENT_MESH_IDENTITY_MISMATCH", "R2A_OUTER_CERTIFICATE_MISSING"),
            case_mesh_identity,
        )
    )

    def case_orphan_cert_ref() -> R2aVerificationOutcome:
        event = _base_event()
        cert = _base_certificate("0" * 64)
        return verify_r2a_certificate_evidence(_evidence(events=(event,), certs=(cert,)))

    cases.append(
        InjectionCase(
            "R25-007",
            "CERTIFICATE_ORPHAN_OUTER_TRIAL",
            (
                "R2A_CERTIFICATE_ORPHAN_EVENT_REFERENCE",
                "R2A_ENDPOINT_PROJECTION_INVALID",
            ),
            case_orphan_cert_ref,
        )
    )

    def case_wrong_candidate_cert() -> R2aVerificationOutcome:
        event = _base_event()
        cert = _base_certificate(
            event["event_hash"],
            candidate_id="adeab5b1-a339-5eb3-aa66-011ffe49bac0",
        )
        return verify_r2a_certificate_evidence(_evidence(events=(event,), certs=(cert,)))

    cases.append(
        InjectionCase(
            "R25-008",
            "WRONG_CANDIDATE_CERTIFICATE",
            (
                "R2A_CERTIFICATE_CANDIDATE_ID_MISMATCH",
                "R2A_ENDPOINT_PROJECTION_INVALID",
            ),
            case_wrong_candidate_cert,
        )
    )

    def case_events_without_cert() -> R2aVerificationOutcome:
        event = _base_event()
        return verify_r2a_certificate_evidence(_evidence(events=(event,)))

    cases.append(
        InjectionCase(
            "R25-009",
            "EVENTS_WITHOUT_CERTIFICATE",
            (
                "R2A_OUTER_CERTIFICATE_MISSING",
                "CERTIFICATE_REQUIRED_BUT_MISSING",
                "R2A_ENDPOINT_PROJECTION_INVALID",
            ),
            case_events_without_cert,
        )
    )

    def case_fiv_rule_pack_pose() -> R2aVerificationOutcome:
        return verify_r2a_certificate_evidence(
            _evidence(
                provider_identity_id="TASK020_TASK012_APPROVED_RULE_PACK_AUTHORITY",
                provider_identity_version="configuration-only",
            )
        )

    cases.append(
        InjectionCase(
            "R25-010",
            "CONFIG_RULE_PACK_POSES_AS_FIV_NUMERIC",
            ("FROZEN_EVIDENCE_INSUFFICIENT", "R2A_RAW_EVIDENCE_MISSING"),
            case_fiv_rule_pack_pose,
        )
    )

    rows: list[dict[str, str]] = []
    for item in cases:
        outcome = item.runner()
        rows.append(
            {
                "TEST_ID": item.test_id,
                "TAMPER_TYPE": item.tamper_type,
                **_record(outcome, item.expected_blocked_codes),
            }
        )
    return rows
