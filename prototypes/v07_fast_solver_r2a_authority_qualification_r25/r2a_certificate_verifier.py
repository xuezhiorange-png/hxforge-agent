"""Verify production R2A transient events and outer decision certificates."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from hexagent.canonical_json import canonical_sha256
from hexagent.exchangers.shell_tube.task172_local_runtime.models import (
    CandidateTask172LocalRequest,
    Task172LocalResult,
)
from hexagent.exchangers.shell_tube.task172_local_runtime.service import (
    recompute_task172_request_hash,
    recompute_task172_result_hash,
)
from prototypes.v07_fast_solver_r2a_authority_qualification_r25.r2a_contract import (
    Q_PREDICATE_KEYS,
    R2A_AUTHORITY_HASH,
    R2A_AUTHORITY_ID,
    R2A_CERTIFICATE_SCHEMA,
    R2A_EVENT_SCHEMA,
)

R2aAdmissionStatus = Literal[
    "CERTIFICATE_PRESENT_VERIFIED",
    "NO_TRIGGER_PROVEN",
    "CERTIFICATE_REQUIRED_BUT_MISSING",
    "FROZEN_EVIDENCE_INSUFFICIENT",
    "PROVIDER_IDENTITY_MISMATCH",
    "BLOCKED",
]


@dataclass(frozen=True)
class R2aCertificateEvidence:
    candidate_id: str
    candidate_hash: str
    rating_request_hash: str
    task174_result_hash: str
    source_result_hash: str
    mesh_n: int
    mesh_identity: str
    mesh_result_hash: str
    provider_identity_id: str
    provider_identity_version: str
    transient_events: tuple[dict[str, Any], ...]
    outer_certificates: tuple[dict[str, Any], ...]
    outer_trial_record_hashes: tuple[str, ...] = ()


@dataclass(frozen=True)
class R2aVerificationOutcome:
    status: R2aAdmissionStatus
    blocked_code: str | None
    diagnostics: tuple[str, ...]
    q_predicate_gate: str
    certificate_hash_replay: bool
    provider_identity_binding: bool
    result_hash: str


def _fail(code: str, *diag: str) -> R2aVerificationOutcome:
    return R2aVerificationOutcome(
        status="BLOCKED",
        blocked_code=code,
        diagnostics=diag,
        q_predicate_gate="BLOCKED",
        certificate_hash_replay=False,
        provider_identity_binding=False,
        result_hash=canonical_sha256({"blocked_code": code, "diagnostics": diag}),
    )


def _replay_event_hash(event: dict[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key != "event_hash"}
    return canonical_sha256(body)


def _replay_certificate_hash(certificate: dict[str, Any]) -> str:
    body = {key: value for key, value in certificate.items() if key != "certificate_hash"}
    return canonical_sha256(body)


def _verify_q_predicates_from_endpoints(event: dict[str, Any]) -> tuple[bool, str]:
    q = event.get("Q1_Q15")
    if not isinstance(q, dict):
        return False, "R2A_Q_PREDICATES_MISSING"
    if set(q.keys()) != set(Q_PREDICATE_KEYS):
        return False, "R2A_Q_PREDICATE_KEY_SET_MISMATCH"
    if not all(isinstance(q[key], bool) for key in Q_PREDICATE_KEYS):
        return False, "R2A_Q_PREDICATE_TYPE_INVALID"

    left_req_raw = event.get("endpoint_request_projection_left")
    right_req_raw = event.get("endpoint_request_projection_right")
    left_res_raw = event.get("endpoint_result_projection_left")
    right_res_raw = event.get("endpoint_result_projection_right")
    if not all(
        isinstance(item, dict)
        for item in (left_req_raw, right_req_raw, left_res_raw, right_res_raw)
    ):
        return False, "R2A_ENDPOINT_PROJECTION_MISSING"

    try:
        left_req = CandidateTask172LocalRequest.model_validate(left_req_raw)
        right_req = CandidateTask172LocalRequest.model_validate(right_req_raw)
        left_res = Task172LocalResult.model_validate(left_res_raw)
        right_res = Task172LocalResult.model_validate(right_res_raw)
    except Exception:  # noqa: BLE001
        return False, "R2A_ENDPOINT_PROJECTION_INVALID"

    replay_checks = {
        "Q1": left_res.status == right_res.status == "VALIDATED"
        and not left_res.blockers
        and not right_res.blockers,
        "Q15": (
            recompute_task172_request_hash(left_req) == left_res.request_hash
            and recompute_task172_request_hash(right_req) == right_res.request_hash
            and recompute_task172_result_hash(left_res) == left_res.result_hash
            and recompute_task172_result_hash(right_res) == right_res.result_hash
            and event.get("left_endpoint_request_hash") == left_res.request_hash
            and event.get("right_endpoint_request_hash") == right_res.request_hash
            and event.get("left_endpoint_result_hash") == left_res.result_hash
            and event.get("right_endpoint_result_hash") == right_res.result_hash
        ),
    }
    for key, expected in replay_checks.items():
        if q.get(key) is True and not expected:
            return False, f"R2A_FORGED_{key}_PASS"
        if q.get(key) is False and expected:
            return False, f"R2A_{key}_PREDICATE_MISMATCH"
    if all(q.values()) and not all(replay_checks.values()):
        return False, "R2A_FORGED_Q1_Q15_ALL_TRUE"
    return True, "PASS"


def _verify_event(event: dict[str, Any], evidence: R2aCertificateEvidence) -> tuple[bool, str]:
    if event.get("schema_version") != R2A_EVENT_SCHEMA:
        return False, "R2A_EVENT_SCHEMA_MISMATCH"
    if event.get("authority_id") != R2A_AUTHORITY_ID:
        return False, "R2A_AUTHORITY_ID_MISMATCH"
    if event.get("authority_hash") != R2A_AUTHORITY_HASH:
        return False, "R2A_AUTHORITY_HASH_MISMATCH"
    declared = event.get("event_hash")
    if not isinstance(declared, str) or declared != _replay_event_hash(event):
        return False, "R2A_EVENT_HASH_REPLAY_MISMATCH"
    if event.get("candidate_id") != evidence.candidate_id:
        return False, "R2A_EVENT_CANDIDATE_ID_MISMATCH"
    if event.get("candidate_hash") != evidence.candidate_hash:
        return False, "R2A_EVENT_CANDIDATE_HASH_MISMATCH"
    if event.get("mesh_identity") != evidence.mesh_identity:
        return False, "R2A_EVENT_MESH_IDENTITY_MISMATCH"
    if int(event.get("mesh_subdivisions", -1)) != evidence.mesh_n:
        return False, "R2A_EVENT_MESH_N_MISMATCH"
    ok, code = _verify_q_predicates_from_endpoints(event)
    if not ok:
        return False, code
    return True, "PASS"


def _verify_certificate(
    certificate: dict[str, Any],
    evidence: R2aCertificateEvidence,
    event_hashes: set[str],
) -> tuple[bool, str]:
    if certificate.get("schema_version") != R2A_CERTIFICATE_SCHEMA:
        return False, "R2A_CERTIFICATE_SCHEMA_MISMATCH"
    if certificate.get("authority_id") != R2A_AUTHORITY_ID:
        return False, "R2A_CERTIFICATE_AUTHORITY_ID_MISMATCH"
    if certificate.get("authority_hash") != R2A_AUTHORITY_HASH:
        return False, "R2A_CERTIFICATE_AUTHORITY_HASH_MISMATCH"
    declared = certificate.get("certificate_hash")
    if not isinstance(declared, str) or declared != _replay_certificate_hash(certificate):
        return False, "R2A_CERTIFICATE_HASH_REPLAY_MISMATCH"
    if certificate.get("candidate_id") != evidence.candidate_id:
        return False, "R2A_CERTIFICATE_CANDIDATE_ID_MISMATCH"
    if certificate.get("candidate_hash") != evidence.candidate_hash:
        return False, "R2A_CERTIFICATE_CANDIDATE_HASH_MISMATCH"
    if certificate.get("mesh_identity") != evidence.mesh_identity:
        return False, "R2A_CERTIFICATE_MESH_IDENTITY_MISMATCH"
    if int(certificate.get("mesh_subdivisions", -1)) != evidence.mesh_n:
        return False, "R2A_CERTIFICATE_MESH_N_MISMATCH"
    left_events = certificate.get("left_endpoint_event_hashes") or []
    right_events = certificate.get("right_endpoint_event_hashes") or []
    for ref in (*left_events, *right_events):
        if ref not in event_hashes:
            return False, "R2A_CERTIFICATE_ORPHAN_EVENT_REFERENCE"
    return True, "PASS"


def verify_r2a_certificate_evidence(evidence: R2aCertificateEvidence) -> R2aVerificationOutcome:
    if not evidence.candidate_id or not evidence.rating_request_hash:
        return _fail("R2A_BINDING_INCOMPLETE", "candidate_or_request_missing")
    provider_ok = bool(evidence.provider_identity_id and evidence.provider_identity_version)
    if not provider_ok:
        return _fail("PROVIDER_IDENTITY_MISMATCH", "provider_identity_missing")

    has_events = bool(evidence.transient_events)
    has_certs = bool(evidence.outer_certificates)
    if not has_events and not has_certs:
        return R2aVerificationOutcome(
            status="FROZEN_EVIDENCE_INSUFFICIENT",
            blocked_code="R2A_RAW_EVIDENCE_MISSING",
            diagnostics=(
                "No transient_provider_enclosure_event_hashes or "
                "outer_decision_certificate_hashes supplied.",
            ),
            q_predicate_gate="NOT_EVALUATED",
            certificate_hash_replay=False,
            provider_identity_binding=provider_ok,
            result_hash=canonical_sha256(
                {
                    "status": "FROZEN_EVIDENCE_INSUFFICIENT",
                    "candidate_id": evidence.candidate_id,
                    "mesh_n": evidence.mesh_n,
                    "mesh_result_hash": evidence.mesh_result_hash,
                }
            ),
        )

    event_hashes: set[str] = set()
    for event in evidence.transient_events:
        ok, code = _verify_event(event, evidence)
        if not ok:
            return _fail(code)
        event_hashes.add(str(event["event_hash"]))

    if has_events and not has_certs:
        return R2aVerificationOutcome(
            status="CERTIFICATE_REQUIRED_BUT_MISSING",
            blocked_code="R2A_OUTER_CERTIFICATE_MISSING",
            diagnostics=("R2A events present without outer decision certificates.",),
            q_predicate_gate="PASS",
            certificate_hash_replay=False,
            provider_identity_binding=provider_ok,
            result_hash=canonical_sha256(
                {
                    "status": "CERTIFICATE_REQUIRED_BUT_MISSING",
                    "candidate_id": evidence.candidate_id,
                    "mesh_n": evidence.mesh_n,
                }
            ),
        )

    for certificate in evidence.outer_certificates:
        ok, code = _verify_certificate(certificate, evidence, event_hashes)
        if not ok:
            return _fail(code)

    return R2aVerificationOutcome(
        status="CERTIFICATE_PRESENT_VERIFIED",
        blocked_code=None,
        diagnostics=(),
        q_predicate_gate="PASS",
        certificate_hash_replay=True,
        provider_identity_binding=True,
        result_hash=canonical_sha256(
            {
                "status": "CERTIFICATE_PRESENT_VERIFIED",
                "candidate_id": evidence.candidate_id,
                "mesh_n": evidence.mesh_n,
                "mesh_result_hash": evidence.mesh_result_hash,
                "event_hashes": sorted(event_hashes),
                "certificate_hashes": sorted(
                    cert["certificate_hash"] for cert in evidence.outer_certificates
                ),
            }
        ),
    )
